"""L7 gate "lossless round-trip of any deck the library produced".

For every deck of the corpus: build A.pptx -> import to text T -> build B.pptx, then compare A and B per slide:
  text      ordered paragraph texts (whitespace-normalised) of text frames and table cells
  objects   kinds and counts: text frames, tables (+ cell texts), charts (+ kind, categories, series values,
            options), pictures / media, connectors, plain shapes (prst)
  geometry  every matched item within 0.05 in
  style     bold / italic / colour / badge runs, list markers and levels
  slide     notes, hidden, transition, build animation targets, section names
A deck is "lossless" when nothing differs.

Usage: python bench/roundtrip.py [--record] [--verbose] [--only SUBSTR] [--keep DIR]
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import subprocess
import sys
import tempfile
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

TOL = 45720  # 0.05 in
CORPUS = ("examples", "bench/answers/run-5-sonnet", "bench/answers/run-4-sonnet")


# --------------------------------------------------------------------------- extraction


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


def _link(rpr, part, slides) -> str | None:
    """Target of a run's hyperlink: the URL, or ``#n`` for a jump to slide n."""
    from pptx.oxml.ns import qn

    h = rpr.find(qn("a:hlinkClick")) if rpr is not None else None
    if h is None:
        return None
    try:
        rel = part.rels[h.get(qn("r:id"))]
        if rel.is_external:
            return rel.target_ref
        return f"#{slides.get(rel.target_part, '?')}"
    except Exception:
        return "?"


def _run_fmt(rpr, part=None, slides=None) -> tuple:
    from pptx.oxml.ns import qn

    if rpr is None:
        return (False, False, None, None, None)
    fill = rpr.find(qn("a:solidFill"))
    col = None
    if fill is not None:
        c = fill.find(qn("a:srgbClr"))
        col = c.get("val").upper() if c is not None and c.get("val") else "theme"
    hl = rpr.find(qn("a:highlight"))
    hlc = None
    if hl is not None:
        c = hl.find(qn("a:srgbClr"))
        hlc = c.get("val").upper() if c is not None and c.get("val") else "x"
    return (rpr.get("b") in ("1", "true"), rpr.get("i") in ("1", "true"), col, hlc, _link(rpr, part, slides or {}))


def _paras(txbody, part=None, slides=None) -> list[dict]:
    """[{text, marker, lvl, runs: [(text, fmt)], size}] for a txBody (empty paragraphs kept out)."""
    from lxml import etree
    from pptx.oxml.ns import qn

    out = []
    if txbody is None:
        return out
    for p in txbody.findall(qn("a:p")):
        runs: list[list] = []
        for ch in p:
            tag = etree.QName(ch).localname
            if tag in ("r", "fld"):
                t = ch.find(qn("a:t"))
                text = (t.text or "") if t is not None else ""
                fmt = _run_fmt(ch.find(qn("a:rPr")), part, slides)
            elif tag == "br":
                text, fmt = "\n", (False, False, None, None, None)
            else:
                continue
            if fmt[3]:
                text = text.strip("　")
            if runs and runs[-1][1] == fmt:
                runs[-1][0] += text
            else:
                runs.append([text, fmt])
        text = _norm("".join(r[0] for r in runs))
        if not text:
            continue
        runs = [(_norm(r[0]) if i else r[0].lstrip(), r[1]) for i, r in enumerate(runs)]
        ppr = p.find(qn("a:pPr"))
        marker = None
        lvl = 0
        if ppr is not None:
            if ppr.find(qn("a:buAutoNum")) is not None:
                marker = "number"
            elif ppr.find(qn("a:buChar")) is not None:
                marker = "bullet"
            lvl = int(ppr.get("lvl") or 0)
        size = None
        for r in p.iter(qn("a:rPr")):
            if r.get("sz", "").isdigit():
                size = int(r.get("sz")) / 100
                break
        algn = ppr.get("algn") if ppr is not None else None
        out.append(
            {"text": text, "marker": marker, "lvl": lvl, "runs": _merge_style(runs), "size": size, "algn": algn}
        )
    return out


def _merge_style(runs: list) -> list:
    """Style signature: formatted spans only (plain text carries no information)."""
    sig = []
    for text, fmt in runs:
        if not text.strip():
            continue
        if sig and sig[-1][1] == fmt:
            sig[-1] = (sig[-1][0] + text, fmt)
        else:
            sig.append((text, fmt))
    return [(t.strip(), f) for t, f in sig]


def _cell_fill(tc) -> str | None:
    from pptx.oxml.ns import qn

    pr = tc.find(qn("a:tcPr"))
    c = pr.find(qn("a:solidFill") + "/" + qn("a:srgbClr")) if pr is not None else None
    return c.get("val").upper() if c is not None else None


def slide_facts(slide, ctx_slide_index: dict) -> dict:
    from lxml import etree
    from pptx.oxml.ns import qn

    from slidemark.importer.read import ReadCtx, Tf, read_chart

    items: list[dict] = []
    ctx = ReadCtx(accent="")

    def walk(shapes, tf):
        for sh in shapes:
            try:
                one(sh, tf)
            except Exception as e:  # keep going; recorded as an item so it shows up as a difference
                items.append({"kind": "unreadable", "key": type(e).__name__, "box": (0, 0, 0, 0)})

    def one(sh, tf):
        el = sh._element
        tag = etree.QName(el).localname
        if tag == "grpSp":
            walk(sh.shapes, tf.child(el))
            return
        box = tf.box(sh.left or 0, sh.top or 0, sh.width or 0, sh.height or 0)
        if tag == "cxnSp":
            ln = el.find(qn("p:spPr") + "/" + qn("a:ln"))
            tail = ln.find(qn("a:tailEnd")) if ln is not None else None
            head = ln.find(qn("a:headEnd")) if ln is not None else None
            g = el.find(qn("p:spPr") + "/" + qn("a:prstGeom"))
            items.append(
                {
                    "kind": "connector",
                    "key": g.get("prst") if g is not None else "?",
                    "box": box,
                    "arrow": (
                        tail is not None and tail.get("type") not in (None, "none"),
                        head is not None and head.get("type") not in (None, "none"),
                    ),
                }
            )
        elif tag == "pic":
            media = bool(el.xpath(".//*[local-name()='videoFile' or local-name()='audioFile']"))
            items.append({"kind": "media" if media else "picture", "key": "", "box": box})
        elif tag == "graphicFrame":
            if sh.has_table:
                rows = []
                for tr in sh.table._tbl.tr_lst:
                    rows.append(
                        [
                            (
                                tc.get("hMerge") in ("1", "true"),
                                tc.get("vMerge") in ("1", "true"),
                                tc.get("gridSpan"),
                                tc.get("rowSpan"),
                                _paras(tc.find(qn("a:txBody")), slide.part, ctx_slide_index),
                                _cell_fill(tc),
                            )
                            for tc in tr.tc_lst
                        ]
                    )
                cols = [round(c.width / TOL) for c in sh.table.columns]
                items.append(
                    {
                        "kind": "table",
                        "key": "|".join(_norm(" ".join(p["text"] for p in c[4])) for r in rows for c in r),
                        "box": box,
                        "rows": rows,
                        "cols": cols,
                    }
                )
            elif sh.has_chart:
                ch = read_chart(sh, ctx)
                if ch is None:
                    items.append({"kind": "chart", "key": "?", "box": box, "chart": None})
                else:
                    items.append(
                        {
                            "kind": "chart",
                            "key": ch.kind + ":" + _norm(ch.title or ""),
                            "box": box,
                            "chart": (ch.kind, ch.title, ch.categories, ch.series, sorted(ch.options.items())),
                        }
                    )
            else:
                items.append({"kind": "object", "key": "", "box": box})
        elif tag == "sp" and el.xpath(".//*[local-name()='oMath']"):
            from slidemark.importer.mathml import _canon

            eq = el.xpath(".//*[local-name()='oMathPara']")
            items.append({"kind": "math", "key": _canon(eq[0]) if eq else "?", "box": box})
        elif tag == "sp":
            paras = _paras(el.find(qn("p:txBody")), slide.part, ctx_slide_index)
            g = el.find(qn("p:spPr") + "/" + qn("a:prstGeom"))
            prst = g.get("prst") if g is not None else ("custom" if el.find(qn("p:spPr") + "/" + qn("a:custGeom")) is not None else "?")
            sp = el.find(qn("p:spPr"))
            fill = None
            if sp is not None and sp.find(qn("a:solidFill")) is not None:
                c = sp.find(qn("a:solidFill") + "/" + qn("a:srgbClr"))
                fill = c.get("val").upper() if c is not None else "x"
            ph = el.find(qn("p:nvSpPr") + "/" + qn("p:nvPr") + "/" + qn("p:ph"))
            if paras:
                items.append(
                    {
                        "kind": "text",
                        "key": "\n".join(p["text"] for p in paras),
                        "box": box,
                        "paras": paras,
                        "shape": (prst, fill),
                        "ph": ph.get("type") if ph is not None else None,
                    }
                )
            elif ph is None:
                items.append({"kind": "shape", "key": prst, "box": box, "shape": (prst, fill)})

    walk(slide.shapes, Tf())
    try:
        notes = _norm(slide.notes_slide.notes_text_frame.text) if slide.has_notes_slide else ""
    except Exception:
        notes = ""
    root = slide._element
    trans = []
    for t in root.iter():
        if not isinstance(t.tag, str):
            continue
        if etree.QName(t).localname == "transition":
            trans.append(
                (
                    sorted((etree.QName(c).localname, tuple(sorted(c.attrib.items()))) for c in t.iter() if c is not t),
                    t.get("spd"),
                    t.get("{http://schemas.microsoft.com/office/powerpoint/2010/main}dur"),
                )
            )
            break
    timing_tgts = len(root.xpath(".//*[local-name()='spTgt']"))
    return {
        "items": items,
        "notes": notes,
        "hidden": root.get("show") in ("0", "false"),
        "transition": trans[0] if trans else None,
        "timing": timing_tgts,
    }


def deck_facts(path: Path) -> dict:
    from pptx import Presentation

    prs = Presentation(str(path))
    sections = [s.get("name") for s in prs._element.iter() if isinstance(s.tag, str) and s.tag.endswith("}section")]
    idx = {s.part: i for i, s in enumerate(prs.slides, 1)}
    return {"size": (int(prs.slide_width), int(prs.slide_height)), "sections": sections, "slides": [slide_facts(s, idx) for s in prs.slides]}


# --------------------------------------------------------------------------- comparison


def _center_dist(a, b) -> float:
    ax, ay, aw, ah = a
    bx, by, bw, bh = b
    return max(abs(ax - bx), abs(ay - by), abs(aw - bw), abs(ah - bh))


def _match(a_items: list[dict], b_items: list[dict]):
    """Pair items with the same (kind, key) by smallest box distance; yields (a, b) pairs and leftovers."""
    groups_a: dict = defaultdict(list)
    groups_b: dict = defaultdict(list)
    for it in a_items:
        groups_a[(it["kind"], it["key"])].append(it)
    for it in b_items:
        groups_b[(it["kind"], it["key"])].append(it)
    pairs, miss_a, miss_b = [], [], []
    for k in set(groups_a) | set(groups_b):
        la, lb = list(groups_a.get(k, [])), list(groups_b.get(k, []))
        cand = sorted(
            ((_center_dist(x["box"], y["box"]), i, j) for i, x in enumerate(la) for j, y in enumerate(lb)),
        )
        ua, ub = set(), set()
        for d, i, j in cand:
            if i in ua or j in ub:
                continue
            ua.add(i)
            ub.add(j)
            pairs.append((la[i], lb[j]))
        miss_a += [x for i, x in enumerate(la) if i not in ua]
        miss_b += [y for j, y in enumerate(lb) if j not in ub]
    return pairs, miss_a, miss_b


def _texts(items: list[dict]) -> list[str]:
    out = []
    for it in items:
        if it["kind"] == "text":
            out += [p["text"] for p in it["paras"]]
        elif it["kind"] == "table":
            for r in it["rows"]:
                for c in r:
                    out += [p["text"] for p in c[4]]
    return out


def compare_decks(a: Path, b: Path) -> list[tuple[str, str]]:
    """List of (kind, detail) differences between two .pptx files; empty = lossless."""
    fa, fb = deck_facts(a), deck_facts(b)
    return compare_facts(fa, fb)


def compare_facts(fa: dict, fb: dict) -> list[tuple[str, str]]:
    diffs: list[tuple[str, str]] = []
    if len(fa["slides"]) != len(fb["slides"]):
        diffs.append(("slides", f"{len(fa['slides'])} slides vs {len(fb['slides'])}"))
    if fa["sections"] != fb["sections"]:
        diffs.append(("section", f"{fa['sections']} vs {fb['sections']}"))
    for n, (sa, sb) in enumerate(zip(fa["slides"], fb["slides"], strict=False), 1):
        ta, tb = _texts(sa["items"]), _texts(sb["items"])
        if ta != tb:
            kind = "text-order" if Counter(ta) == Counter(tb) else "text"
            only_a = list((Counter(ta) - Counter(tb)).elements())[:2]
            only_b = list((Counter(tb) - Counter(ta)).elements())[:2]
            diffs.append((kind, f"s{n}: lost {only_a!r} gained {only_b!r}"))
        ka = Counter(i["kind"] for i in sa["items"])
        kb = Counter(i["kind"] for i in sb["items"])
        if ka != kb:
            diffs.append(("objects", f"s{n}: {dict(ka - kb)} lost, {dict(kb - ka)} gained"))
        pairs, miss_a, miss_b = _match(sa["items"], sb["items"])
        for m in miss_a:
            if m["kind"] != "text":
                diffs.append((m["kind"], f"s{n}: {m['kind']} {m['key'][:40]!r} not reproduced"))
        for m in miss_b:
            if m["kind"] != "text":
                diffs.append((m["kind"], f"s{n}: extra {m['kind']} {m['key'][:40]!r}"))
        for x, y in pairs:
            d = _center_dist(x["box"], y["box"])
            if d > TOL:
                diffs.append(("geometry", f"s{n}: {x['kind']} {x['key'][:30]!r} off by {d / 914400:.2f} in"))
            _compare_pair(n, x, y, diffs)
        for what in ("notes", "hidden", "transition", "timing"):
            if sa[what] != sb[what]:
                diffs.append((what if what != "timing" else "build", f"s{n}: {sa[what]!r} vs {sb[what]!r}"))
    return diffs


def _size_differs(a, b) -> bool:
    return a is not None and b is not None and abs(a - b) > 0.6


def _compare_pair(n, x, y, diffs) -> None:
    k = x["kind"]
    if k == "text":
        if x["shape"] != y["shape"]:
            diffs.append(("style", f"s{n}: shape {x['shape']} vs {y['shape']} for {x['key'][:30]!r}"))
        for pa, pb in zip(x["paras"], y["paras"], strict=False):
            if (pa["marker"], pa["lvl"]) != (pb["marker"], pb["lvl"]):
                diffs.append(("marker", f"s{n}: {pa['text'][:30]!r} {pa['marker']}/{pa['lvl']} vs {pb['marker']}/{pb['lvl']}"))
            elif pa["runs"] != pb["runs"]:
                diffs.append(("style", f"s{n}: runs of {pa['text'][:30]!r}: {pa['runs']} vs {pb['runs']}"))
            elif (pa["algn"] or "l") != (pb["algn"] or "l"):
                diffs.append(("style", f"s{n}: align of {pa['text'][:30]!r}: {pa['algn']} vs {pb['algn']}"))
            elif _size_differs(pa["size"], pb["size"]):
                diffs.append(("size", f"s{n}: size of {pa['text'][:30]!r}: {pa['size']} vs {pb['size']}"))
    elif k == "table":
        if len(x["rows"]) != len(y["rows"]) or any(len(r) != len(s) for r, s in zip(x["rows"], y["rows"], strict=False)):
            diffs.append(("table", f"s{n}: table shape differs"))
            return
        for r, s in zip(x["rows"], y["rows"], strict=True):
            for c, d in zip(r, s, strict=True):
                if c[:4] != d[:4]:
                    diffs.append(("table", f"s{n}: merge/span differs"))
                    return
                if c[5] != d[5]:
                    diffs.append(("style", f"s{n}: cell fill {c[5]} vs {d[5]}"))
                    return
                for pa, pb in zip(c[4], d[4], strict=False):
                    if pa["runs"] != pb["runs"] or pa["marker"] != pb["marker"]:
                        diffs.append(("style", f"s{n}: cell {pa['text'][:30]!r} runs differ"))
                        return
                    if (pa["algn"] or "l") != (pb["algn"] or "l"):
                        diffs.append(("style", f"s{n}: cell {pa['text'][:30]!r} align {pa['algn']} vs {pb['algn']}"))
                        return
                    if _size_differs(pa["size"], pb["size"]):
                        diffs.append(("size", f"s{n}: cell {pa['text'][:30]!r} size {pa['size']} vs {pb['size']}"))
                        return
        if x["cols"] != y["cols"] and any(abs(p - q) > 1 for p, q in zip(x["cols"], y["cols"], strict=False)):
            diffs.append(("table", f"s{n}: column widths {x['cols']} vs {y['cols']}"))
    elif k == "chart":
        if x["chart"] != y["chart"]:
            ca, cb = x["chart"], y["chart"]
            what = "options"
            if ca and cb:
                if ca[2] != cb[2] or ca[3] != cb[3]:
                    what = "data"
                elif ca[4] != cb[4]:
                    what = f"options {dict(ca[4])} vs {dict(cb[4])}"
            diffs.append(("chart", f"s{n}: chart {x['key'][:30]!r} {what}"))
    elif k == "connector":
        if x["arrow"] != y["arrow"]:
            diffs.append(("connector", f"s{n}: arrowheads {x['arrow']} vs {y['arrow']}"))
    elif k == "shape":
        if x["shape"] != y["shape"]:
            diffs.append(("style", f"s{n}: shape {x['shape']} vs {y['shape']}"))


# --------------------------------------------------------------------------- driver


def corpus() -> list[Path]:
    out = []
    for d in CORPUS:
        out += sorted((ROOT / d).glob("*.md"))
    return out


def roundtrip_text(text: str, work: Path, base_dir: Path | None = None) -> tuple[list[tuple[str, str]], str, Path, Path]:
    """Build text -> A, import -> T, build T -> B; returns (diffs, T, A, B)."""
    from slidemark.build import build
    from slidemark.importer import import_pptx

    a = work / "A.pptx"
    b = work / "B.pptx"
    build(text, a, base_dir=base_dir or work)
    t, _ = import_pptx(a, work)
    if not t.strip():
        return [("import", "empty import")], t, a, b
    build(t, b, base_dir=work)
    return compare_decks(a, b), t, a, b


def count_tokens(text: str) -> int:
    import tiktoken

    return len(tiktoken.get_encoding("o200k_base").encode(text))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--record", action="store_true")
    ap.add_argument("--verbose", action="store_true", help="print every difference, not only the first")
    ap.add_argument("--only", help="substring of the deck path")
    ap.add_argument("--keep", help="directory to keep A/B/T per deck")
    args = ap.parse_args()
    rows = []
    kinds: Counter = Counter()
    tok_src = tok_imp = 0
    with tempfile.TemporaryDirectory() as td:
        base = Path(args.keep) if args.keep else Path(td)
        for src in corpus():
            if args.only and args.only not in str(src):
                continue
            name = f"{src.parent.name}/{src.stem}"
            work = base / f"{src.parent.name}-{src.stem}"
            work.mkdir(parents=True, exist_ok=True)
            text = src.read_text(encoding="utf-8")
            try:
                diffs, t, _, _ = roundtrip_text(text, work, src.parent)
                (work / "T.md").write_text(t, encoding="utf-8")
                tok_src += count_tokens(text)
                tok_imp += count_tokens(t)
            except Exception as e:
                diffs = [("crash", f"{type(e).__name__}: {e}")]
            rows.append((name, diffs))
            for k in {k for k, _ in diffs}:
                kinds[k] += 1
            if diffs:
                print(f"DIFF {name}: {diffs[0][0]}: {diffs[0][1]}  (+{len(diffs) - 1})")
                if args.verbose:
                    for k, d in diffs[1:]:
                        print(f"       {k}: {d}")
            else:
                print(f"ok   {name}")
    n = len(rows)
    good = sum(1 for _, d in rows if not d)
    share = good / n if n else 0.0
    ratio = tok_imp / tok_src if tok_src else 0.0
    print(f"\nlossless {good}/{n} = {share:.1%}; imported/source tokens {ratio:.2f}")
    print("decks affected per kind:", dict(kinds.most_common()))
    if args.record:
        sha = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True, cwd=ROOT)
        row = {
            "date": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
            "commit": sha.stdout.strip(),
            "metric": "roundtrip",
            "roundtrip": round(share, 3),
            "value": round(share, 3),
            "decks": n,
            "lossless": good,
            "token_ratio": round(ratio, 3),
            "failures": dict(kinds.most_common()),
        }
        with (ROOT / "bench" / "history.jsonl").open("a", encoding="utf-8") as f:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

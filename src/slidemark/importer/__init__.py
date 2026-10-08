"""``.pptx`` -> SlideMark text (the reverse of ``build``). Never raises: problems become diagnostics."""

from __future__ import annotations

import copy
import math
import re
from collections import Counter
from dataclasses import replace
from pathlib import Path

from ..ir import Diagnostic
from ..render.design_part import read_design_part
from ..theme import DEFAULT, JP_BUSINESS, MIDNIGHT, Theme
from . import diet, emit, icondisc, recognise2
from .design import (
    claim_fences,
    css_fence,
    design_header,
    design_rules,
    edited,
    edited_diag,
    heading_sized,
    html_slide_lines,
    implied_style,
    insert_fences,
    is_template_path,
    match_slide,
    tag_boxes,
    token_lines,
)
from .look import _keep_valid, color_similarity, derive_tokens
from .read import ReadCtx, SlideData, read_sections, read_slide
from .runs import is_slidemark_deck
from .shadows import card_shadow
from .structure import DeckInfo, build_slide, notes_lines

__all__ = ["import_pptx"]

_THEMES = (JP_BUSINESS, MIDNIGHT)
_JA = re.compile(r"[぀-ヿ㐀-鿿]")
_LATIN = re.compile(r"[A-Za-z]")


def detect_theme(prs) -> Theme:
    """A SlideMark theme when its signature colors appear in the slides, else the default."""
    blob = ""
    for s in prs.slides:
        try:
            blob += s.part.blob.decode("utf-8", "ignore").upper()
        except Exception:
            continue
    for th in _THEMES:
        sig = {th.colors["primary"].lstrip("#").upper()}
        if th.name == "midnight":
            sig.add(th.colors["bg"].lstrip("#").upper())
        if all(f'"{c}"' in blob for c in sig):
            return th
    return DEFAULT


def _custom_theme(prs) -> bool:
    """True when the slide master's color scheme is not the stock Office one (a template-based deck)."""
    try:
        from pptx.opc.constants import RELATIONSHIP_TYPE as RT

        blob = prs.slide_masters[0].part.part_related_by(RT.THEME).blob.decode("utf-8", "ignore")
        got = re.findall(r'<a:(accent[123])>\s*<a:srgbClr val="(\w+)"', blob)
        return bool(got) and dict(got) != {"accent1": "4F81BD", "accent2": "C0504D", "accent3": "9BBB59"}
    except Exception:
        return False


def _size_token(w: int, h: int) -> str | None:
    r = w / h if h else 16 / 9
    if abs(r - 16 / 9) < 0.01:
        return None
    for name, ratio in (("4:3", 4 / 3), ("16:10", 16 / 10), ("A4", 297 / 210)):
        if abs(r - ratio) < 0.01:
            return name
    return f"{round(w / 914400, 2):g}inx{round(h / 914400, 2):g}in"


def _footers(slides: list[SlideData], H: int) -> tuple[str | None, set[str]]:
    n = len(slides)
    raw: dict[str, str] = {}
    named: Counter[str] = Counter()
    bottom: Counter[str] = Counter()
    for sd in slides:
        seen_named, seen_bottom = set(), set()
        for it in sd.items:
            if it.kind != "text":
                continue
            txt = re.sub(r"\s+", " ", it.text).strip()
            raw[txt] = it.text.strip()
            if it.ph == "ftr" or it.name.lower() == "footer":
                seen_named.add(txt)
            elif it.ph is None and it.y >= 0.9 * H and it.h <= 0.08 * H:
                seen_bottom.add(txt)
        named.update(seen_named)
        bottom.update(seen_bottom)
    need = max(1, math.ceil(n / 2))
    texts = {t for t, c in named.items() if c >= need and t}
    texts |= {t for t, c in bottom.items() if c >= max(2, need) and t}
    if not texts:
        return None, set()
    best = max(texts, key=lambda t: (named[t] + bottom[t], -len(t)))
    return raw.get(best, best), {best}


def _lang(slides: list[SlideData]) -> str | None:
    ja = lat = 0
    for sd in slides:
        for it in sd.items:
            for p in it.paras:
                ja += len(_JA.findall(p.plain))
                lat += len(_LATIN.findall(p.plain))
            for row in it.rows:
                for c in row:
                    for p in c.paras:
                        ja += len(_JA.findall(p.plain))
                        lat += len(_LATIN.findall(p.plain))
    return "ja" if ja and ja >= 0.3 * (ja + lat) else None


def import_pptx(
    path: str | Path, out_dir: str | Path | None = None, slim: bool = False
) -> tuple[str, list[Diagnostic]]:
    """Read ``path`` and return (SlideMark text, diagnostics).

    With ``out_dir`` the pictures are written to ``out_dir/images/`` and referenced as
    ``images/<slide>-<n>.<ext>``; without it only the names are referenced (info diagnostic ``import-image``).
    ``slim`` (the CLI's default): the text of a deck made elsewhere goes through the token diet
    (``importer/diet.py``): colour names, hoisted tokens, nothing the build does not reproduce; it costs a few
    builds of the result.
    """
    diags: list[Diagnostic] = []
    try:
        from pptx import Presentation

        prs = Presentation(str(path))
    except Exception as e:
        diags.append(
            Diagnostic(
                level="error",
                message=f"cannot read {path}: {type(e).__name__}: {e}",
                rule="import-unreadable",
                hint="pass a valid .pptx (not .ppt or .key)",
            )
        )
        return "", diags
    try:
        info: dict = {}
        text, diags = _import(prs, out_dir, diags, Path(path).name, info)
        if slim and text and info.get("foreign"):  # a deck made elsewhere: shorter text, the same slides
            text = diet.slim(text, out_dir)
        return text, diags
    except Exception as e:  # last-resort guard
        diags.append(
            Diagnostic(
                level="error",
                message=f"import failed: {type(e).__name__}: {e}",
                rule="import-internal",
                hint="report this deck as a bug",
            )
        )
        return "", diags


def _color_score(prs, text: str, out_dir) -> float:
    """How closely the colors of ``text`` rebuilt match ``prs`` (trial build; -1 when it fails)."""
    import tempfile

    from pptx import Presentation

    from ..build import build

    try:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "t.pptx"
            build(text, path, base_dir=out_dir or tmp)
            return color_similarity(prs, Presentation(str(path)))
    except Exception:
        return -1.0


def _import(
    prs, out_dir, diags: list[Diagnostic], src_name: str = "", info: dict | None = None
) -> tuple[str, list[Diagnostic]]:
    """A foreign deck keeps its look as tokens when a trial build shows the colors match better."""
    theme = detect_theme(prs)
    if read_design_part(prs) or (src_name and _custom_theme(prs)):
        return _import_with(prs, out_dir, diags, src_name, {}, info)
    tokens = derive_tokens(prs, theme)
    if not tokens:
        return _import_with(prs, out_dir, diags, src_name, {}, info)
    base_diags: list[Diagnostic] = []
    best_text, _ = _import_with(prs, out_dir, base_diags, src_name, {}, info)
    best = (_color_score(prs, best_text, out_dir), best_text, base_diags)
    keep_text = {k: v for k, v in tokens.items() if k not in ("colors.fg", "colors.muted")}
    for cand in (tokens, keep_text):
        if not cand or (cand is keep_text and cand == tokens):
            continue
        cand_diags: list[Diagnostic] = []
        text, _ = _import_with(prs, out_dir, cand_diags, src_name, cand, info)
        score = _color_score(prs, text, out_dir)
        if score > best[0] + 0.01:
            best = (score, text, cand_diags)
        if cand is tokens and score > best[0] - 0.01 and best[1] is text:
            break  # the full look wins: no need to try the variant
    diags.extend(best[2])
    return best[1], diags


def _token_disc(tokens: dict, colors: dict[str, str]) -> str | None:
    """RRGGBB of the deck's own ``icon.disc`` token (a colour name of the deck, or a hex), else ``None``."""
    v = tokens.get("icon_disc")
    if not isinstance(v, str):
        return None
    v = v.strip()
    if v in colors:
        return colors[v].lstrip("#").upper()
    return v.lstrip("#").upper() if re.fullmatch(r"#?[0-9A-Fa-f]{6}", v) else None


def _drawn_accent(theme, tokens: dict, accent: str) -> str:
    """RRGGBB a ``==mark==`` run is drawn in: the accent made legible on bg / surface (``Theme.legible``)."""
    try:
        from ..theme import apply_tokens

        th, _ = apply_tokens(theme, {k: str(v) for k, v in tokens.items()})
        # the legible shade depends on the text size (large text needs only 3:1): accept every variant
        shades = [th.hexval(th.legible("accent", size)) for size in (None, 100.0)]
        got = [s.lstrip("#").upper() for s in dict.fromkeys(shades) if s]
        return "|".join(got) if got else accent
    except Exception:  # never raise on a foreign deck: fall back to the plain accent
        return accent


def _default_palette(theme, tokens: dict) -> list[str]:
    """RRGGBB colours the build draws chart series with when the deck states none (never raises)."""
    try:
        from ..theme import apply_tokens

        th, _ = apply_tokens(theme, {k: str(v) for k, v in tokens.items()})
        return [c.lstrip("#").upper() for c in th.chart_palette()]
    except Exception:
        return []


def _import_with(
    prs, out_dir, diags: list[Diagnostic], src_name: str, own_tokens: dict[str, str], info: dict | None = None
) -> tuple[str, list[Diagnostic]]:
    W, H = int(prs.slide_width), int(prs.slide_height)
    theme = detect_theme(prs)
    design = read_design_part(prs) or {}
    tok_colors = {  # the deck's own palette (tokens) replaces the stock theme's for badge/class detection
        k.split(".", 1)[1]: v.lstrip("#").upper()
        for k, v in {**(design.get("tokens") or {}), **own_tokens}.items()
        if k.startswith("colors.") and re.fullmatch(r"#[0-9A-Fa-f]{6}", str(v))
    }
    accent = tok_colors.get("accent") or theme.colors["accent"].lstrip("#").upper()
    ctx = ReadCtx(accent=accent)
    for i, s in enumerate(prs.slides, 1):
        ctx.slide_index[s.part] = i
    datas: list[SlideData] = []
    slide_ids = [getattr(s, "slide_id", None) for s in prs.slides]
    for i, s in enumerate(prs.slides, 1):
        ctx.slide_no = i
        try:
            datas.append(read_slide(s, ctx))
        except Exception as e:
            datas.append(SlideData())
            ctx.skip(f"slide ({type(e).__name__}: {e})")
    diags.extend(ctx.diags)
    footer, footers = _footers(datas, H)
    colors = {**{k: v.lstrip("#").upper() for k, v in theme.colors.items()}, **tok_colors}
    from ..units import to_emu

    deck = DeckInfo(
        width=W,
        height=H,
        accent=_drawn_accent(theme, {**(design.get("tokens") or {}), **own_tokens}, accent),
        colors=colors,
        footers=footers,
        sections=read_sections(prs),
        margin_x=to_emu(theme.margin_x),
        margin_y=to_emu(theme.margin_y),
        gap=to_emu(theme.gap),
        foreign=not design and not is_slidemark_deck(datas),
        palette=_default_palette(theme, {**(design.get("tokens") or {}), **own_tokens}),
    )
    if info is not None:
        info["foreign"] = deck.foreign
    disc_shape: str | None = None
    for sd in datas:
        icondisc.fold(sd)  # (before the deck-wide disc is read; ``build_slide`` folds again on its copies)
    if deck.foreign:
        deck.ink = recognise2.deck_ink(datas, colors.get("bg", "FFFFFF"), H)
        deck.card_shadow = card_shadow(datas, W, H)
        deck.icon_disc, disc_shape = icondisc.deck_disc(datas)
    else:
        deck.icon_disc = _token_disc({**(design.get("tokens") or {}), **own_tokens}, colors)
    emit.set_palette(colors)
    rules = design_rules(design)
    deck.implied = {r: implied_style(rules, r, colors) for r in ("lead", "conclusion", "footnote")}
    deck.css_heading = heading_sized(rules)
    classes = {}
    for cname in ("success", "danger", "muted", "accent"):
        classes.setdefault(colors[cname], cname)
    out_path = Path(out_dir) if out_dir else None

    def save_image(slide_no: int, k: int, blob: bytes, ext: str) -> str:
        ext = {"jpeg": "jpg"}.get(ext.lower(), ext.lower())
        ref = f"images/{slide_no}-{k}.{ext}"
        if out_path is None:
            diags.append(
                Diagnostic(
                    level="info",
                    message=f"picture referenced as {ref} but not exported",
                    slide=slide_no,
                    rule="import-image",
                    hint="use -o to write the image files next to the output",
                )
            )
            return ref
        try:
            target = out_path / ref
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(blob)
        except OSError as e:
            diags.append(
                Diagnostic(
                    level="warning",
                    message=f"cannot write {ref}: {e}",
                    slide=slide_no,
                    rule="import-image",
                    hint="check the output directory",
                )
            )
        return ref

    header: list[str] = []
    css_head: list[str] = []
    if design:
        own = bool(src_name) and is_template_path(design.get("theme")) and _custom_theme(prs)
        head_lines, css_head = design_header(design, src_name if own else "")
        header.extend(head_lines)
        if own:
            diags.append(
                Diagnostic(
                    level="info",
                    message=f"built on a template; 'theme: {src_name}' reuses this file as one",
                    rule="import-template",
                    hint="keep the .pptx next to the .md (or change the theme: path)",
                )
            )
    elif theme is not DEFAULT:
        header.append(f"theme: {theme.name}")
        header.extend(token_lines(own_tokens))
    elif src_name and _custom_theme(prs):
        header.append(f"theme: {src_name}")  # its own masters and colors: the source deck is the template
        diags.append(
            Diagnostic(
                level="info",
                message=f"the deck has its own theme; 'theme: {src_name}' reuses it as a template",
                rule="import-template",
                hint="keep the .pptx next to the .md (or change the theme: path)",
            )
        )
    elif own_tokens:
        header.extend(token_lines(own_tokens))
    if deck.foreign:  # DL3d: chrome drawn with loose shapes (cover bars, edge strips, title rule) -> tokens
        header.extend(token_lines(_keep_valid(recognise2.deck_tokens(datas, deck))))
        if deck.card_shadow:  # most cards share one shadow: `card.shadow=`; the others say `{shadow=}`
            header.extend(token_lines(_keep_valid({"classes.card.shadow": deck.card_shadow})))
        if deck.icon_disc:  # most icons sit on one disc: `icon.disc=`; the others say `{disc=}`
            disc_tokens = {"icon_disc": icondisc.color_token(deck.icon_disc, colors)}
            if disc_shape and disc_shape != "circle":
                disc_tokens["icon_disc_shape"] = disc_shape
            header.extend(token_lines(_keep_valid(disc_tokens)))
    size = _size_token(W, H)
    if size:
        header.append(f"size: {size}")
    lang = _lang(datas)
    if lang:
        header.append(f"lang: {lang}")
    if footer:
        header.append(f"footer: {footer}")
    if any(
        sd.num_field or any(i.ph == "sldNum" or i.name.lower() == "slide number" for i in sd.items)
        for sd in datas
    ) or (deck.foreign and recognise2.has_page_numbers(datas, W, H)):
        header.append("num: on")
    # pass 1: which slides need ``dense`` (on a copy: building a slide edits its data)
    flags: dict[int, bool] = {}
    for n, sd in enumerate(datas, 1):
        ent = match_slide(design, n, slide_ids[n - 1]) if design else None
        if ent and ent.get("html") is not None and not edited(ent, sd):
            continue  # restored from the stored HTML: no shapes to arrange
        try:
            sdc = copy.deepcopy(sd)
            claim_fences(ent, sdc, n, [])
            info: dict = {}
            lines = build_slide(n, sdc, deck, [], lambda *a: "", classes, info)
            lines = tag_boxes(lines, ent)
            if any(i.kind == "table" for i in sdc.items):  # pinned rows must not look like a density clue
                lines = _table_widths(lines, sdc, _trial_head(header, css_head))
            tried, dense = _dense_decision(lines, info, sdc, deck, _trial_head(header, css_head), theme)
            if tried:
                flags[n] = dense
        except Exception:
            continue
    n_dense = sum(flags.values())
    deck_dense = n_dense >= 2 and n_dense >= 0.5 * len(flags)
    if deck_dense:
        header.append("density: dense")
    chunks: list[list[str]] = []
    solo_titles = False
    for n, sd in enumerate(datas, 1):
        try:
            sdiags: list[Diagnostic] = []
            info = {}
            ent = match_slide(design, n, slide_ids[n - 1]) if design else None
            won = [] if (ent and ent.get("html") is not None) else claim_fences(ent, sd, n, diags)
            lines = build_slide(n, sd, deck, sdiags, save_image, classes, info)
            diags.extend(sdiags)
            if won:
                info["title_only"] = False  # the html block is the body: not a section divider
            solo_titles = solo_titles or (n > 1 and bool(info.get("title_only")))
            ent = match_slide(design, n, slide_ids[n - 1]) if design else None
            lines = tag_boxes(lines, ent)
            html_slide = False
            if ent and ent.get("html") is not None:
                if edited(ent, sd):
                    diags.append(edited_diag(n))
                else:
                    lines = html_slide_lines(ent, sd, notes_lines(sd.notes))
                    html_slide = True
            if not html_slide:
                if flags.get(n) and not deck_dense:
                    lines = _add_dense(lines, info)
                lines = _shorten(lines, info, sd, deck, classes, _trial_head(header, css_head))
                lines = _table_widths(lines, sd, _trial_head(header, css_head))
                lines = insert_fences(_drop_section(lines) if won else lines, won, len(notes_lines(sd.notes)))
                if ent and ent.get("dec"):
                    lines = _add_decisions(lines, info, ent["dec"])
            if ent and ent.get("css"):
                k = len(lines) - len(notes_lines(sd.notes))
                lines = [*lines[:k], *css_fence(ent["css"]), *lines[k:]]
        except Exception as e:
            diags.append(
                Diagnostic(
                    level="warning",
                    message=f"slide could not be imported: {type(e).__name__}: {e}",
                    slide=n,
                    rule="import-skipped",
                    hint="the slide was left out; rebuild it by hand",
                )
            )
            lines = ["---"]
        chunks.append(lines)
    if solo_titles and not deck.sections:
        header.append("sections: off")
    body = "\n\n".join("\n".join(c) for c in chunks)
    top = [*header, *([""] if header and css_head else []), *css_head]
    text = ("\n".join(top) + "\n\n" if top else "") + body + "\n"
    return text, diags


def _drop_section(lines: list[str]) -> list[str]:
    """Remove the ``section`` / ``cover`` token (and an ``@`` line it leaves empty) after the heading."""
    out: list[str] = []
    for k, ln in enumerate(lines):
        if k and ln.startswith("@") and {"section", "cover"} & set(ln[1:].split()):
            rest = [t for t in ln[1:].split() if t not in ("section", "cover")]
            if rest:
                out.append("@" + " ".join(rest))
            continue
        out.append(ln)
    return out


def _trial_head(header: list[str], css_head: list[str]) -> list[str]:
    """Header lines for trial builds: the real design (tokens and css fence) must be in effect."""
    return [*header, *([""] if css_head else []), *css_head]


def _variants(tokens: list[str]) -> list[list[str]]:
    """Shorter ``@`` lines to try, shortest first: none, only the flow/chevron word, the full line."""
    words = [t for t in tokens if t in ("chevron", "flow")]
    out: list[list[str]] = [[]]
    if words:
        out.append(words)
    return out


def _shorten(lines, info, sd, deck, classes, header) -> list[str]:
    """Drop ``@`` tokens the auto-arrangement reproduces: build a trial slide and compare its grid."""
    tokens, at = info.get("tokens") or [], info.get("at")
    if at is None or not tokens or tokens == ["blank"]:
        return lines
    hidden = info.get("extra", [])
    head = ("\n".join(header) + "\n\n") if header else ""
    try:
        base_err = _geom_err(sd, _read_trial(head + "\n".join(lines) + "\n", deck))
        for var in _variants(tokens):
            new = [*var, *info.get("links", []), *hidden]
            trial = [*lines[:at], *(["@" + " ".join(new)] if new else []), *lines[at + 1 :]]
            tsd = _read_trial(head + "\n".join(trial) + "\n", deck)
            got: dict = {}
            build_slide(
                1, tsd, replace(deck, foreign=False), [], lambda *a: "", classes, got
            )  # (built shapes)
            # the shorter line must give the same grid and (nearly) the same boxes as the full one
            if got.get("tokens") == tokens and _geom_err(sd, tsd) <= base_err + 0.08:
                return trial
    except Exception:
        return lines
    return lines


def _table_widths(lines: list[str], sd: SlideData, header: list[str]) -> list[str]:
    """``{rowh=...}`` first (pinned rows change the text size and so the widths), then ``{widths=...}``, then
    ``rowh`` again: the rows of a table read with its automatic (hugging) widths are not the rows it has with
    the stated widths (a narrow column wraps, its row grows to twice the original's)."""
    first = _table_options(lines, sd, header, "rowh")
    return _table_options(_table_options(first, sd, header, "widths"), sd, header, "rowh")


def _table_options(lines: list[str], sd: SlideData, header: list[str], what: str) -> list[str]:
    """Add ``{widths=a:b:c}`` (or ``{rowh=...}``) to the tables whose rebuilt column widths (row heights)
    differ from the original's.

    The automatic widths follow the text and hug numeric tables; explicit ``widths`` (or a CSS-free
    hand-sized table) are not stored in the .pptx except as the finished column widths.
    """
    from .structure import _units

    tables = sorted((i for i in sd.items if i.kind == "table" and len(i.col_w) > 1), key=lambda i: (i.y, i.x))
    if not tables:
        return lines
    try:
        head = ("\n".join(header) + "\n\n") if header else ""
        trial = _read_trial(head + "\n".join(lines) + "\n", None)  # type: ignore[arg-type]
        got = sorted(
            (i for i in trial.items if i.kind == "table" and len(i.col_w) > 1), key=lambda i: (i.y, i.x)
        )
        if len(got) != len(tables):
            return lines
        bad: dict[int, list[str]] = {}
        for k, (a, b) in enumerate(zip(tables, got, strict=True)):
            if len(a.col_w) != len(b.col_w):
                continue
            ta, tb = sum(a.col_w), sum(b.col_w)
            if what == "widths" and (
                abs(ta - tb) > 0.03 * ta
                or any(abs(x / ta - y / tb) > 0.04 for x, y in zip(a.col_w, b.col_w, strict=True))
            ):
                bad.setdefault(k, []).append("widths=" + ":".join(map(str, _units(list(a.col_w)))))
            if what == "rowh" and (rowh := _row_pins(a.row_h, b.row_h)):
                bad.setdefault(k, []).append(rowh)
        if not bad:
            return lines
        out: list[str] = []
        k = -1
        in_fence = False
        for ln in lines:
            if ln.startswith(("```", "~~~")):
                in_fence = not in_fence
            starts = not in_fence and ln.startswith("|") and not (out and out[-1].startswith("|"))
            if starts:
                k += 1
                if k in bad:
                    w = " ".join(bad[k])
                    if what == "rowh" and out and out[-1].startswith("{") and "rowh=" in out[-1]:
                        out.append(ln)  # (pinned by an earlier pass: the trial still differs, do not repeat)
                        continue
                    if out and out[-1].startswith("{") and out[-1].endswith("}"):
                        out[-1] = out[-1][:-1] + " " + w + "}"
                    else:
                        out.append("{" + w + "}")
            out.append(ln)
        return out
    except Exception:
        return lines


def _row_pins(orig: list[int], trial: list[int]) -> str | None:
    """``rowh=...`` when the rebuilt row heights differ from the original's (a pinned table): equal rows give
    one value, a header that differs from equal body rows two, anything else one value per row."""
    if len(orig) != len(trial) or not orig or sum(orig) <= 0:
        return None
    if all(abs(x - y) <= max(0.12 * max(x, y), 0.06 * 914400) for x, y in zip(orig, trial, strict=True)):
        return None  # (the automatic layout differs a little between a trial slide and the real deck)

    def inch(v: int) -> str:
        return f"{max(round(v / 914400, 2), 0.15):g}in"

    body = orig[1:] or orig
    if all(abs(h - body[0]) <= 0.03 * body[0] for h in body):
        vals = (
            [inch(sum(orig) / len(orig))]
            if len(orig) < 2 or abs(orig[0] - body[0]) <= 0.03 * body[0]
            else [inch(orig[0]), inch(body[0])]
        )
    else:
        vals = [inch(h) for h in orig]
    return "rowh=" + ",".join(vals)


# --------------------------------------------------------------------------- density


def _drop_token(lines: list[str], tok: str) -> list[str]:
    out = []
    for ln in lines:
        if ln.startswith("@") and tok in ln[1:].split():
            rest = [t for t in ln[1:].split() if t != tok]
            if not rest:
                continue
            ln = "@" + " ".join(rest)
        out.append(ln)
    return out


def _read_trial(text: str, deck: DeckInfo | None) -> SlideData:
    import tempfile

    from pptx import Presentation

    from ..build import build

    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "t.pptx"
        build(text, path)
        prs = Presentation(str(path))
        ctx = ReadCtx(accent=(deck.accent if deck else None) or "")
        ctx.slide_index[prs.slides[0].part] = 1
        return read_slide(prs.slides[0], ctx)


def _geom_key(it) -> str | None:
    if it.kind == "text" and it.text:
        return re.sub(r"\s+", " ", it.text).strip()
    if it.kind == "table":
        return "|".join(re.sub(r"\s+", " ", p.plain).strip() for r in it.rows for c in r for p in c.paras)
    return None


def _geom_err(orig: SlideData, trial: SlideData) -> float:
    """Sum over the original's texts and tables of the distance (in) to the trial's same-text item."""
    pool: dict[str, list] = {}
    for it in trial.items:
        if (k := _geom_key(it)) is not None:
            pool.setdefault(k, []).append(it)
    err = 0.0
    for it in orig.items:
        k = _geom_key(it)
        if k is None:
            continue
        cand = pool.get(k)
        if not cand:
            err += 3.0
            continue
        best = min(
            cand, key=lambda c: max(abs(c.x - it.x), abs(c.y - it.y), abs(c.w - it.w), abs(c.h - it.h))
        )
        cand.remove(best)
        err += min(
            3.0, max(abs(best.x - it.x), abs(best.y - it.y), abs(best.w - it.w), abs(best.h - it.h)) / 914400
        )
    return err


def _add_dense(lines: list[str], info: dict) -> list[str]:
    """``lines`` with the ``dense`` class on the slide's ``@`` line (a new one when there is none)."""
    at = info.get("at")
    extra = info.get("extra") or []
    if at is not None:
        out = [*lines[:at], lines[at] + " dense", *lines[at + 1 :]]
    else:
        at = info.get("pos", 1)
        out = [*lines[:at], "@dense", *lines[at:]]
    info["extra"] = [*extra, "dense"]
    info["at"] = at
    return out


def _add_decisions(lines: list[str], info: dict, words: list[str]) -> list[str]:
    """``@noemph`` / ``@defaults`` (stored in the design part: they leave no trace in the shapes) on the
    slide's ``@`` line, a new one right under the heading when there is none."""
    pos = info.get("pos", 1)
    words = [w for w in words if w in ("noemph", "defaults")]
    if not words or pos > len(lines):
        return lines
    if pos < len(lines) and lines[pos].startswith("@") and not lines[pos].startswith("@end"):
        return [*lines[:pos], " ".join([lines[pos], *words]), *lines[pos + 1 :]]
    return [*lines[:pos], "@" + " ".join(words), *lines[pos:]]


def _dense_decision(lines, info, sd, deck, header, theme) -> tuple[bool, bool]:
    """(tried, dense): a trial build with the ``dense`` class fits the original's text boxes much better."""
    extra = info.get("extra")
    if extra is None or info.get("title_only") or info.get("form") or "dense" in extra:
        return False, False
    body = theme.sizes.get("body", 18)
    sizes = sorted(
        p.size
        for it in sd.items
        if it.role is None and it.kind in ("text", "table")
        for p in (it.paras if it.kind == "text" else [q for r in it.rows for c in r for q in c.paras])
        if p.size
    )
    if not sizes or sizes[0] > 1.5 * body:  # only big type: dense cannot be what shrank it
        return False, False
    try:
        head = ("\n".join(header) + "\n\n") if header else ""
        dense_lines = _add_dense(lines, dict(info))
        e0 = _geom_err(sd, _read_trial(head + "\n".join(lines) + "\n", deck))
        e1 = _geom_err(sd, _read_trial(head + "\n".join(dense_lines) + "\n", deck))
    except Exception:
        return False, False
    return True, e0 > 0.3 and e1 < 0.7 * e0

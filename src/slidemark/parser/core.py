"""Deck/slide structure: header, slide splitting, boxes, lead/conclusion/footnotes, cover inference."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

import yaml

from ..ir import Chart, Container, Deck, Link, Paragraph, Run, Slide, Table, Text
from .attrs import (
    STANDALONE,
    AtSpec,
    Attrs,
    RawLink,
    apply_attrs,
    check_transition,
    parse_at,
    parse_attr_body,
    split_trailing_attrs,
)
from .blocks import convert
from .ctx import Ctx, closest
from .inline import inline_runs
from .lenient import Rec, normalize

FENCE_RE = re.compile(r"^[ \t]*(`{3,}|~{3,})(.*)$")
H1_RE = re.compile(r"^#(?:[ \t]+(.*?))?(?:[ \t]+#+)?[ \t]*$")
HN_RE = re.compile(r"^(#{2,3})(?:[ \t]+(.*?))?(?:[ \t]+#+)?[ \t]*$")
HR_RE = re.compile(r"^-{3,}[ \t]*$")
KV_RE = re.compile(r"^([A-Za-z_][\w-]*)[ \t]*:[ \t]*(.*?)[ \t]*$")
HEADER_KEYS = ("theme", "size", "lang", "title", "author", "footer", "num", "density", "sections")
SHORT_LINE = 60
MARP_IGNORED = (
    "header",
    "style",
    "headingdivider",
    "backgroundcolor",
    "backgroundimage",
    "color",
    "math",
    "class",
)


# --------------------------------------------------------------------------- lines and fences


def fence_map(lines: list[str]) -> tuple[list[bool], int | None]:
    """Per line: is it part of a code fence. Second value: index of an unclosed opening fence."""
    inside = [False] * len(lines)
    marker: str | None = None
    open_idx: int | None = None
    for i, line in enumerate(lines):
        m = FENCE_RE.match(line)
        if marker is None:
            if m and not (m.group(1)[0] == "`" and "`" in m.group(2)):
                marker, open_idx = m.group(1), i
                inside[i] = True
        else:
            inside[i] = True
            if m and m.group(1)[0] == marker[0] and len(m.group(1)) >= len(marker) and not m.group(2).strip():
                marker = None
    return inside, (open_idx if marker is not None else None)


class _PlainLoader(yaml.SafeLoader):
    """YAML loader that keeps every scalar a string (``16:9`` and ``on`` must not become numbers/bools)."""


for _tag in ("int", "float", "bool", "timestamp", "null"):
    _PlainLoader.yaml_implicit_resolvers = {
        k: [(t, r) for t, r in v if not t.endswith(_tag)]
        for k, v in _PlainLoader.yaml_implicit_resolvers.items()
    }


def _set_header(deck: Deck, key: str, value: str, ctx: Ctx, line: int) -> None:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
        value = value[1:-1]
    k = key.lower()
    if k == "theme":
        deck.theme = value or "default"
    elif k == "size":
        deck.size = value or "16:9"
    elif k == "lang":
        deck.lang = value or None
    elif k == "title":
        deck.title = value or None
    elif k == "author":
        deck.author = value or None
    elif k == "footer":
        deck.footer = value or None
    elif k in ("num", "slide_number"):
        v = value.lower()
        if v in ("on", "true", "yes", "1"):
            deck.slide_number = True
        elif v in ("off", "false", "no", "0", ""):
            deck.slide_number = False
        else:
            ctx.warn(f"bad num '{value}'", line, "bad-header", "use num: on or num: off")
    elif k == "density":
        if value in ("normal", "dense"):
            deck.density = value  # type: ignore[assignment]
        else:
            ctx.warn(f"bad density '{value}'", line, "bad-header", "use density: normal or density: dense")
    elif k == "sections":
        v = value.lower()
        if v in ("on", "true", "yes", "1", ""):
            deck.attrs["sections"] = "on"
        elif v in ("off", "false", "no", "0"):
            deck.attrs["sections"] = "off"
        else:
            ctx.warn(f"bad sections '{value}'", line, "bad-header", "use sections: on or sections: off")
    elif k == "marp":
        ctx.warn(
            "Marp header 'marp: true' ignored",
            line,
            "marp-syntax",
            "remove it; SlideMark needs no mode switch",
        )
    elif k == "paginate":
        deck.slide_number = value.lower() in ("on", "true", "yes", "1")
        ctx.warn("Marp 'paginate' header", line, "marp-syntax", "use 'num: on'")
    elif k in MARP_IGNORED:
        ctx.warn(
            f"Marp header '{key}' ignored",
            line,
            "marp-syntax",
            "set theme and slide classes with 'theme:' and '@' lines",
        )
    else:
        deck.attrs[key] = value
        near = closest(key, HEADER_KEYS)
        hint = f"did you mean '{near}'? " if near else ""
        ctx.warn(
            f"unknown header key '{key}'",
            line,
            "unknown-header",
            f"{hint}known keys: {', '.join(HEADER_KEYS)}; kept in deck.attrs",
        )


def parse_header(lines: list[str], inside: list[bool], deck: Deck, ctx: Ctx) -> int:
    """Read the deck header; returns the index of the first line after it."""
    n = len(lines)
    i = 0
    while i < n and not lines[i].strip():
        i += 1
    if i < n and HR_RE.match(lines[i]) and lines[i].strip() == "---" and not inside[i]:
        j = i + 1
        while j < n and not (lines[j].strip() == "---" and not inside[j]):
            j += 1
        if j < n:
            try:
                data = yaml.load("\n".join(lines[i + 1 : j]), Loader=_PlainLoader)  # noqa: S506
            except yaml.YAMLError:
                data = None
            if isinstance(data, dict) and data:
                for k, v in data.items():
                    _set_header(deck, str(k), "" if v is None else str(v), ctx, i + 1)
                i = j + 1
    while i < n:
        line = lines[i]
        if not line.strip():
            i += 1
            continue
        m = KV_RE.match(line)
        if m and not inside[i] and not line.startswith(("#", "@", "※", "^")):
            _set_header(deck, m.group(1), m.group(2), ctx, i + 1)
            i += 1
            continue
        break
    return i


@dataclass
class Chunk:
    title_idx: int | None
    title_text: str
    start: int  # first body line index
    end: int  # exclusive


def split_slides(lines: list[str], inside: list[bool], start: int) -> list[Chunk]:
    chunks: list[Chunk] = []
    cur: Chunk | None = None
    for i in range(start, len(lines)):
        if inside[i]:
            continue
        line = lines[i]
        m = H1_RE.match(line)
        if m:
            if cur:
                cur.end = i
                chunks.append(cur)
            cur = Chunk(i, m.group(1) or "", i + 1, len(lines))
        elif HR_RE.match(line):
            if cur:
                cur.end = i
                chunks.append(cur)
            cur = Chunk(None, "", i + 1, len(lines))
        elif cur is None and line.strip():
            cur = Chunk(None, "", i, len(lines))
    if cur:
        chunks.append(cur)
    out = []
    for c in chunks:
        blank_body = not any(lines[k].strip() for k in range(c.start, c.end))
        if c.title_idx is None and blank_body:
            continue
        out.append(c)
    return out


# --------------------------------------------------------------------------- slide body


@dataclass
class Item:
    kind: str  # md | at | end | h2 | h3 | foot
    line: int
    text: str = ""
    lines: list[str] = field(default_factory=list)
    pending: Attrs | None = None


def _scan_body(lines: list[str], inside: list[bool], c: Chunk, ctx: Ctx) -> tuple[list[Item], str | None]:
    items: list[Item] = []
    buf: list[str] = []
    buf_line = c.start + 1
    pending: Attrs | None = None
    notes: str | None = None

    def flush() -> None:
        nonlocal buf, pending
        if buf and any(s.strip() for s in buf):
            items.append(Item("md", buf_line, lines=buf, pending=pending))
            pending = None
        buf = []

    for i in range(c.start, c.end):
        text = lines[i]
        if inside[i]:
            if not buf:
                buf_line = i + 1
            buf.append(text)
            continue
        if text.startswith("???"):
            flush()
            rest = [text[3:].strip()] + lines[i + 1 : c.end]
            notes = "\n".join(rest).strip()
            break
        if text.strip().lower() == "@end":
            flush()
            items.append(Item("end", i + 1))
            continue
        if text.startswith("@"):
            flush()
            items.append(Item("at", i + 1, text=text[1:].strip()))
            continue
        if text.startswith("※") or re.match(r"^\^[ \t]", text):
            flush()
            items.append(Item("foot", i + 1, text=text[1:].strip()))
            continue
        m = HN_RE.match(text)
        if m:
            flush()
            items.append(
                Item("h2" if len(m.group(1)) == 2 else "h3", i + 1, text=m.group(2) or "", pending=pending)
            )
            pending = None
            continue
        sm = STANDALONE.match(text)
        if sm:
            a = parse_attr_body(sm.group(1))
            if a is not None:
                flush()
                pending = a
                continue
        if buf and buf[-1].strip() and text.strip() and text.startswith(">") != buf[-1].startswith(">"):
            flush()  # no lazy continuation into or out of a `>` quote
        if text.startswith("|") and buf and buf[-1].strip() and not buf[-1].startswith("|"):
            flush()  # a table right under a list/paragraph would be swallowed as lazy continuation
        if not buf:
            buf_line = i + 1
        buf.append(text)
    flush()
    if pending is not None:
        ctx.warn(
            "attribute line has no block after it", None, "dangling-attrs", "put {…} directly before a block"
        )
    return items, notes


def _heading_text(text: str, line: int, ctx: Ctx) -> tuple[Text, Attrs | None]:
    body, attrs = split_trailing_attrs(text)
    t = Text(role="heading", paragraphs=[Paragraph(runs=inline_runs(body.strip()))], line=line)
    return t, attrs


def _kpi_text(els: list[Any]) -> list[Any]:
    """Merge adjacent body texts into one Text (one paragraph per source line, no list markers)."""
    out: list[Any] = []
    for el in els:
        if isinstance(el, Text) and el.role == "body":
            for p in el.paragraphs:
                p.marker = None
            if out and isinstance(out[-1], Text) and out[-1].role == "body":
                out[-1].paragraphs.extend(el.paragraphs)
                continue
        out.append(el)
    return out


def _build_flat(items: list[Item], ctx: Ctx, kpi: bool = False) -> list[Any]:
    out: list[Any] = []
    carry: Attrs | None = None
    for it in items:
        if it.kind == "md":
            if kpi and not any(FENCE_RE.match(x) for x in it.lines):
                pend = it.pending or carry
                for k, x in enumerate(it.lines):
                    els, pend = convert([x], it.line + k, ctx, pend)
                    out.extend(els)
                carry = pend
            else:
                els, carry = convert(it.lines, it.line, ctx, it.pending or carry)
                out.extend(els)
        elif it.kind == "h3":
            t, attrs = _heading_text(it.text, it.line, ctx)
            for a in (it.pending or carry, attrs):
                if a is not None:
                    apply_attrs(t, a, ctx, it.line)
            carry = None
            out.append(t)
    return _kpi_text(out) if kpi else out


def _apply_at_container(box: Container, spec: AtSpec) -> None:
    if spec.grid is not None:
        box.grid = spec.grid
    if spec.gap is not None:
        box.gap = spec.gap
    if spec.id:
        box.id = spec.id
    for c in spec.classes:
        if c not in box.classes:
            box.classes.append(c)
    box.attrs.update(spec.attrs)


def _merge_specs(specs: list[AtSpec], ctx: Ctx, lines: list[int]) -> AtSpec:
    out = AtSpec()
    for s, ln in zip(specs, lines, strict=True):
        if s.grid is not None:
            if out.grid is not None:
                ctx.warn("second grid ignored", ln, "bad-grid", "use one grid per slide or box")
            else:
                out.grid = s.grid
        out.gap = s.gap if s.gap is not None else out.gap
        out.layout = s.layout or out.layout
        out.classes += [c for c in s.classes if c not in out.classes]
        out.attrs.update(s.attrs)
        out.id = s.id or out.id
        out.background = s.background or out.background
        out.transition = s.transition or out.transition
        out.hidden = out.hidden or s.hidden
        out.links += s.links
    return out


def _build_box(h2: Item, content: list[Item], ats: list[Item], ctx: Ctx) -> Container:
    title, attrs = _heading_text(h2.text, h2.line, ctx)
    box = Container(title=title if h2.text.strip() else None, line=h2.line)
    if attrs is not None:
        apply_attrs(box, attrs, ctx, h2.line)
    if h2.pending is not None:
        apply_attrs(box, h2.pending, ctx, h2.line)
    kpi = "kpi" in box.classes
    if ats:
        spec = _merge_specs([parse_at(a.text, ctx, a.line) for a in ats], ctx, [a.line for a in ats])
        _apply_at_container(box, spec)
        if spec.links:
            ctx.box_links.append((box, spec.links))
        pre: list[Item] = []
        groups: list[tuple[Item, list[Item]]] = []
        for it in content:
            if it.kind == "h3":
                groups.append((it, []))
            elif groups:
                groups[-1][1].append(it)
            else:
                pre.append(it)
        box.children.extend(_build_flat(pre, ctx, kpi))
        for h3, sub in groups:
            st, sattrs = _heading_text(h3.text, h3.line, ctx)
            nested = Container(title=st if h3.text.strip() else None, line=h3.line)
            for a in (sattrs, h3.pending):
                if a is not None:
                    apply_attrs(nested, a, ctx, h3.line)
            nested.children.extend(_build_flat(sub, ctx))
            box.children.append(nested)
    else:
        box.children.extend(_build_flat(content, ctx, kpi))
    return box


def _is_quote(el: Any) -> bool:
    return isinstance(el, Text) and el.role == "quote"


def _plain_len(t: Text) -> int:
    return sum(len(p.plain) for p in t.paragraphs)


def _merge_text(blocks: list[Text], role: str) -> Text:
    paras: list[Paragraph] = []
    for b in blocks:
        paras.extend(b.paragraphs)
    first = blocks[0]
    return Text(role=role, paragraphs=paras, line=first.line, style=first.style, classes=first.classes)  # type: ignore[arg-type]


def parse_slide(
    chunk: Chunk, lines: list[str], inside: list[bool], ctx: Ctx, index: int, recs: list[Rec] | None = None
) -> Slide:
    ctx.box_links = []
    slide = Slide(line=(chunk.title_idx if chunk.title_idx is not None else chunk.start) + 1)
    title_attrs: Attrs | None = None
    if chunk.title_idx is not None:
        body, title_attrs = split_trailing_attrs(chunk.title_text)
        if body.strip():
            slide.title = Text(
                role="title",
                paragraphs=[Paragraph(runs=inline_runs(body.strip()))],
                line=chunk.title_idx + 1,
            )
        else:
            ctx.warn("empty slide title", chunk.title_idx + 1, "empty-title", "write '# Title' with text")
    extra_notes: list[str] = []
    lead_ats: list[Item] = []
    for r in recs or []:
        if r.kind == "diag":
            ctx.add(r.level, r.value, r.idx + 1, r.rule, r.hint)
        elif r.kind == "note":
            extra_notes.append(r.value)
        elif r.kind == "at":
            lead_ats.append(Item("at", r.idx + 1, text=r.value))
    items, notes = _scan_body(lines, inside, chunk, ctx)
    items = lead_ats + items
    slide.notes = "\n".join([*extra_notes, *([notes] if notes else [])]) or None

    slide_links: list[RawLink] = []
    top_ats: list[Item] = []
    top: list[Item] = []
    boxes: list[tuple[Item, list[Item], list[Item]]] = []  # h2, content, at lines
    order: list[Any] = []  # ("top", [items]) | ("box", idx) in source order
    in_box = False
    for it in items:
        if it.kind == "foot":
            ft = Text(role="footnote", paragraphs=[Paragraph(runs=inline_runs(it.text))], line=it.line)
            slide.footnotes.append(ft)
        elif it.kind == "h2":
            boxes.append((it, [], []))
            order.append(("box", len(boxes) - 1))
            in_box = True
        elif it.kind == "end":
            if in_box:
                in_box = False
            else:
                ctx.add(
                    "info",
                    "'@end' outside a box",
                    it.line,
                    "end-outside-box",
                    "remove it, or put it after the '## ' box it closes",
                )
        elif it.kind == "at":
            (boxes[-1][2] if in_box else top_ats).append(it)
        else:
            if not in_box:
                top.append(it)
                if not order or order[-1][0] != "top":
                    order.append(("top", []))
                order[-1][1].append(it)
            else:
                boxes[-1][1].append(it)

    # elements in source order: top-level runs and boxes interleave (items before the first box, only)
    for kind, val in order:
        if kind == "top":
            slide.elements.extend(_build_flat(val, ctx))
        else:
            h2, content, ats = boxes[val]
            slide.elements.append(_build_box(h2, content, ats, ctx))

    _hint_missing_end(slide, boxes, order, ctx)

    # slide-level `@` line and heading attributes
    if top_ats:
        spec = _merge_specs([parse_at(a.text, ctx, a.line) for a in top_ats], ctx, [a.line for a in top_ats])
        slide.grid = spec.grid
        slide.layout = spec.layout
        slide.classes += [c for c in spec.classes if c not in slide.classes]
        slide.attrs.update(spec.attrs)
        if spec.gap is not None:
            slide.attrs["gap"] = spec.gap
        slide.id = spec.id or slide.id
        slide.background = spec.background
        slide.transition = spec.transition
        slide.hidden = spec.hidden
        slide_links = spec.links
    if title_attrs is not None:
        kv = dict(title_attrs.kv)
        for key, attr in (("bg", "background"), ("t", "transition")):
            if key in kv:
                val = kv.pop(key)
                if key == "t":
                    val = check_transition(val, ctx, slide.line)
                setattr(slide, attr, val)
        if "hidden" in kv:
            slide.hidden = kv.pop("hidden") not in ("false", "0", "no", "off")
        slide.id = title_attrs.id or slide.id
        slide.classes += [c for c in title_attrs.classes if c not in slide.classes]
        if slide.title is not None:
            apply_attrs(slide.title, Attrs([], None, kv), ctx, slide.title.line)
        else:
            slide.attrs.update(kv)

    _lead_and_conclusion(slide)
    _infer_cover(slide, index)
    slide.links = _resolve_links(slide_links, len(slide.elements), "slide", ctx, "flow" in slide.classes)
    for box, raw in ctx.box_links:
        box.links = _resolve_links(raw, len(box.children), "box", ctx, "flow" in box.classes)
    ctx.box_links = []
    return slide


def _hint_missing_end(slide: Slide, boxes: list, order: list, ctx: Ctx) -> None:
    """Info when the last `##` box seems to swallow slide-level content (a forgotten `@end`).

    A closing `>` needs no `@end`: it becomes the conclusion anyway (``_lead_and_conclusion``)."""
    if len(boxes) < 2 or not order or order[-1][0] != "box":
        return
    box_els = [e for e in slide.elements if isinstance(e, Container)]
    if len(box_els) != len(boxes):
        return
    *rest, last = box_els

    def visual(e: Any) -> bool:
        return isinstance(e, (Table, Chart)) or (isinstance(e, Text) and "callout" in e.classes)

    odd = next((e for e in last.children if visual(e)), None)
    if odd is None or any(visual(c) for b in rest for c in b.children):
        return
    what = "a callout" if isinstance(odd, Text) else f"a {odd.type}"
    ctx.add(
        "info",
        f"the last box '{_box_title(last)}' holds {what} that its sibling boxes do not",
        getattr(odd, "line", None) or last.line,
        "missing-end",
        "if it belongs to the slide, put a line '@end' before it",
    )


def _box_title(c: Container) -> str:
    return c.title.paragraphs[0].plain[:20] if c.title and c.title.paragraphs else "box"


def _resolve_links(raw: list[RawLink], n: int, owner: str, ctx: Ctx, flow: bool = False) -> list[Link]:
    """Keep the connectors whose ends are existing, distinct blocks; warn about the rest."""
    out: list[Link] = []
    for r in raw:
        if flow and r.dst == r.src + 1:
            ctx.add(
                "info",
                f"connector '{r.token}' repeats a flow arrow",
                r.line,
                "duplicate-link",
                "flow already draws arrows between neighbours: keep only the other links",
            )
        elif r.src == r.dst:
            ctx.warn(
                f"connector '{r.token}' joins a block to itself",
                r.line,
                "bad-link",
                "link two different blocks, e.g. a>b",
            )
        elif not (0 <= r.src < n and 0 <= r.dst < n):
            use = f"use letters a..{chr(96 + min(n, 26))}" if n else "add blocks before linking"
            ctx.warn(
                f"connector '{r.token}' points outside the {owner}",
                r.line,
                "bad-link",
                f"{owner} has {n} block{'s' if n != 1 else ''}: {use}",
            )
        else:
            out.append(Link(src=r.src, dst=r.dst, arrow=r.arrow))
    return out


def _lead_and_conclusion(slide: Slide) -> None:
    els = slide.elements
    if els and _is_quote(els[0]):
        q = els.pop(0)
        slide.lead = _as_role(q, "lead")
    if els and _is_quote(els[-1]):
        slide.conclusion = _as_role(els.pop(), "conclusion")
    elif (
        els
        and isinstance(els[-1], Container)
        and len(els[-1].children) > 1
        and _is_quote(els[-1].children[-1])
    ):
        slide.conclusion = _as_role(els[-1].children.pop(), "conclusion")


def _as_role(t: Text, role: str) -> Text:
    t.role = role  # type: ignore[assignment]
    return t


def _infer_cover(slide: Slide, index: int) -> None:
    if slide.title is None or slide.layout in ("blank", "center"):
        return
    els = slide.elements
    if not els or not all(
        isinstance(e, Text) and e.role == "body" and "callout" not in e.classes for e in els
    ):
        return
    texts: list[Text] = els  # type: ignore[assignment]
    paras = [p for t in texts for p in t.paragraphs]
    explicit = slide.layout in ("cover", "section")
    if not explicit:
        short = (
            len(paras) <= 2
            and all(p.marker is None and len(p.plain) <= SHORT_LINE for p in paras)
            and slide.lead is None
            and slide.conclusion is None
            and slide.grid is None
        )
        if not short:
            return
    slide.subtitle = _merge_text(texts, "subtitle")
    slide.elements = []
    if slide.layout is None:
        slide.layout = "cover" if index == 0 else "section"


# --------------------------------------------------------------------------- entry


def split_lines(text: str) -> list[str]:
    return re.split(r"\r\n|\r|\n", text.lstrip("﻿"))


def parse_deck(text: str) -> Deck:
    deck = Deck()
    ctx = Ctx(deck.diagnostics)
    lines = split_lines(text)
    for _ in range(20):
        inside, unclosed = fence_map(lines)
        if unclosed is None:
            break
        ctx.warn(
            "code fence is never closed",
            unclosed + 1,
            "unclosed-fence",
            "close it with a line containing only ```; the fence line is treated as plain text",
        )
        lines[unclosed] = "\\" + lines[unclosed]
    else:
        inside, _ = fence_map(lines)
    start = parse_header(lines, inside, deck, ctx)
    recs = normalize(lines, inside, start, deck)
    chunks = split_slides(lines, inside, start)
    if not chunks:
        ctx.warn("no slides found", None, "no-slides", "start a slide with '# Title'")
    by_chunk: dict[int, list[Rec]] = {}
    for r in recs:
        # a record belongs to the first slide that ends after its line (blank separator slides are dropped)
        k = next((ci for ci, c in enumerate(chunks) if c.end > r.idx), len(chunks) - 1)
        if k >= 0:
            by_chunk.setdefault(k, []).append(r)
        elif r.kind == "diag":
            ctx.add(r.level, r.value, r.idx + 1, r.rule, r.hint)
    for idx, chunk in enumerate(chunks):
        ctx.slide = idx + 1
        try:
            deck.slides.append(parse_slide(chunk, lines, inside, ctx, idx, by_chunk.get(idx)))
        except Exception as e:  # never raise on bad input
            ctx.error(
                f"internal error: {type(e).__name__}: {e}",
                chunk.start + 1,
                "internal",
                "simplify this slide or report the input as a parser bug",
            )
            deck.slides.append(Slide(line=chunk.start + 1))
    ctx.slide = None
    if deck.title is None and deck.slides and deck.slides[0].title is not None:
        deck.title = deck.slides[0].title.paragraphs[0].plain if deck.slides[0].title.paragraphs else None
    return deck


__all__ = ["parse_deck", "Run"]

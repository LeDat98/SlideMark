"""Deck/slide structure: header, slide splitting, boxes, lead/conclusion/footnotes, cover inference."""

from __future__ import annotations

import re
from dataclasses import dataclass, field, replace
from typing import Any

import yaml

from .. import forms, forms2
from ..ir import Chart, Container, Deck, Link, Paragraph, Run, Slide, Style, Table, Text
from .attrs import (
    FLAGS,
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
from .css import extract_fences, parse_css
from .ctx import Ctx, closest
from .inline import inline_runs
from .lenient import Rec, normalize
from .tokens import (
    THEME_MAPS,
    TOKEN_GROUPS,
    finish_tokens,
    note_stated,
    parse_token_line,
    parse_token_map,
    slide_tokens,
    style_css_rules,
    take_slide_tokens,
)

FENCE_RE = re.compile(r"^[ \t]*(`{3,}|~{3,})(.*)$")
H1_RE = re.compile(r"^#(?:[ \t]+(.*?))?(?:[ \t]+#+)?[ \t]*$")
HN_RE = re.compile(r"^(#{2,3})(?:[ \t]+(.*?))?(?:[ \t]+#+)?[ \t]*$")
HR_RE = re.compile(r"^-{3,}[ \t]*$")
KV_RE = re.compile(r"^([A-Za-z_][\w-]*)[ \t]*:[ \t]*(.*?)[ \t]*$")
HEADER_KEYS = (
    "theme",
    "size",
    "lang",
    "title",
    "author",
    "footer",
    "num",
    "density",
    "sections",
    "fit",
    "colors",
    "fonts",
    "sizes",
    "style",
)
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
    if k in TOKEN_GROUPS and not (
        k == "style" and value[:1] in ("|", ">")
    ):  # Marp `style: |` CSS is ignored below
        parse_token_line(deck, k, value, ctx, line)
    elif k == "theme":
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
    elif k == "fit":  # `fit: off` drops the per-slide fit map from the build output
        v = value.lower()
        if v in ("on", "true", "yes", "1", ""):
            deck.attrs["fit"] = "on"
        elif v in ("off", "false", "no", "0"):
            deck.attrs["fit"] = "off"
        else:
            ctx.warn(f"bad fit '{value}'", line, "bad-header", "use fit: on or fit: off")
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
                    kl = str(k).lower()
                    if isinstance(v, dict) and (kl in TOKEN_GROUPS or kl in THEME_MAPS):
                        parse_token_map(deck, kl, v, ctx, i + 1)
                        continue
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


IMAGE_LINE = re.compile(r"^\s*!\[[^\]]*\]\([^)]*\)(\{[^}]*\})?\s*$")


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
            # `※` is part of a Japanese footnote's text (agents copy it from the brief); `^ ` is only a marker
            items.append(Item("foot", i + 1, text=text.strip() if text.startswith("※") else text[1:].strip()))
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
        if buf and buf[-1].strip() and (IMAGE_LINE.match(text) or IMAGE_LINE.match(buf[-1])):
            flush()  # an image/media line is its own block, never a lazy continuation (in or out)
        if not buf:
            buf_line = i + 1
        buf.append(text)
    flush()
    if pending is not None:
        ctx.warn(
            "attribute line has no block after it", None, "dangling-attrs", "put {…} directly before a block"
        )
    return items, notes


AT_HTML = re.compile(r"(?:^|\s)html(?:\s|$)")
HTML_FENCE = re.compile(r"^[ \t]*(`{3,}|~{3,})[ \t]*html\b")


def _take_html_fence(items: list[Item], ctx: Ctx) -> tuple[list[Item], str | None]:
    """For an ``@html`` slide: cut the first ```html fence out of the body items and return its text."""
    line = next(it.line for it in items if it.kind == "at" and AT_HTML.search(it.text))
    for n, it in enumerate(items):
        if it.kind != "md":
            continue
        for i, text in enumerate(it.lines):
            m = HTML_FENCE.match(text)
            if not m:
                continue
            fence = m.group(1)
            close = next(
                (
                    j
                    for j in range(i + 1, len(it.lines))
                    if re.match(rf"^[ \t]*{fence[0]}{{{len(fence)},}}[ \t]*$", it.lines[j])
                ),
                len(it.lines),
            )
            body = "\n".join(it.lines[i + 1 : close])
            rest = it.lines[:i] + it.lines[close + 1 :]
            new = list(items)
            if any(t.strip() for t in rest):
                new[n] = replace(it, lines=rest)
            else:
                del new[n]
            return new, body
    ctx.warn(
        "'@html' slide has no ```html fence",
        line,
        "html-slide-empty",
        "write the slide's HTML in one ```html fence under the title",
    )
    return items, None


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


def _build_box(h2: Item, content: list[Item], ats: list[Item], ctx: Ctx, kpi_all: bool = False) -> Container:
    title, attrs = _heading_text(h2.text, h2.line, ctx)
    box = Container(title=title if h2.text.strip() else None, line=h2.line)
    if attrs is not None:
        apply_attrs(box, attrs, ctx, h2.line)
    if h2.pending is not None:
        apply_attrs(box, h2.pending, ctx, h2.line)
    if kpi_all and "kpi" not in box.classes:  # `@kpi` on the slide: every box is a KPI card
        box.classes.append("kpi")
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
        if box.grid is not None and len(box.children) < 2:
            n = len(box.children)
            ctx.add(
                "info",
                f"grid '{box.grid}' on a box with {n} block{'s' if n != 1 else ''} ignored",
                ats[0].line,
                "box-grid-unused",
                "put the '@' line right after the '#' title for the slide",
            )
            box.grid = None
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
    return Text(
        role=role,  # type: ignore[arg-type]
        paragraphs=paras,
        line=first.line,
        style=first.style,
        classes=first.classes,
        box=first.box,
    )


def _at_has_word(items: list[Item], word: str) -> bool:
    """True when a slide-level `@` line (not one inside a `##` box) holds ``word``."""
    in_box = False
    for it in items:
        if it.kind == "h2":
            in_box = True
        elif it.kind == "end":
            in_box = False
        elif it.kind == "at" and not in_box and word in it.text.split():
            return True
    return False


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
    html_src: str | None = None
    if any(it.kind == "at" and AT_HTML.search(it.text) for it in items):
        items, html_src = _take_html_fence(items, ctx)
    slide.notes = "\n".join([*extra_notes, *([notes] if notes else [])]) or None

    slide_links: list[RawLink] = []
    kpi_all = _at_has_word(items, "kpi")
    boxes: list[tuple[Item, list[Item], list[Item]]] = []  # h2, content, at lines
    order: list[Any] = []  # ("top", [items], section) | ("box", idx, section) in source order
    sec_ats: list[list[Item]] = [[]]  # slide-level `@` lines per row-group section
    sec = 0
    in_box = False
    pending_end = False  # an `@end` was seen since the last slide-level `@` line
    for it in items:
        if it.kind == "foot":
            ft = Text(role="footnote", paragraphs=[Paragraph(runs=inline_runs(it.text))], line=it.line)
            slide.footnotes.append(ft)
        elif it.kind == "h2":
            boxes.append((it, [], []))
            order.append(("box", len(boxes) - 1, sec))
            in_box = True
        elif it.kind == "end":
            pending_end = True
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
            if in_box:
                boxes[-1][2].append(it)
            else:
                if pending_end and sec_ats[sec]:
                    sec += 1  # row group: a new `@` line after `@end` starts the next section
                    sec_ats.append([])
                pending_end = False
                sec_ats[sec].append(it)
        else:
            if not in_box:
                if not order or order[-1][0] != "top" or order[-1][2] != sec:
                    order.append(("top", [], sec))
                order[-1][1].append(it)
            else:
                boxes[-1][1].append(it)

    # `@chevron` written at the very end of the slide lands in the last box; when that box has no `###`
    # sub-boxes to lay out and the slide has no `@` line of its own, it was meant for the slide
    trail: int | None = None
    if boxes and not any(sec_ats):
        h2, content, ats = boxes[-1]
        last = max([h2.line, *(c.line for c in content)])
        if ats and all(a.line > last for a in ats) and not any(c.kind == "h3" for c in content):
            sec_ats[sec].extend(ats)
            ats.clear()
            trail = _trailing_para(boxes)
            ctx.add(
                "info",
                "'@' line after the last box applies to the slide",
                sec_ats[sec][0].line,
                "at-hoisted",
                "put the '@' line right after the title to make this explicit",
            )

    # elements in source order: top-level runs and boxes interleave (items before the first box, only)
    sec_count = [0] * len(sec_ats)
    sec_boxes: list[list[Container]] = [[] for _ in sec_ats]
    sec_last_box = [False] * len(sec_ats)
    for kind, val, sc in order:
        if kind == "top":
            built = _build_flat(val, ctx)
            slide.elements.extend(built)
            sec_count[sc] += len(built)
            sec_last_box[sc] = False
        else:
            h2, content, ats = boxes[val]
            box = _build_box(h2, content, ats, ctx, kpi_all)
            slide.elements.append(box)
            sec_count[sc] += 1
            sec_boxes[sc].append(box)
            sec_last_box[sc] = True

    for sc in range(len(sec_ats)):
        if sec_last_box[sc]:
            _hint_missing_end(sec_boxes[sc], ctx, trail)

    # slide-level `@` lines (one per row-group section) and heading attributes
    specs = [
        _merge_specs([parse_at(a.text, ctx, a.line) for a in ats], ctx, [a.line for a in ats])
        for ats in sec_ats
    ]
    lead_popped, concl_popped = _lead_and_conclusion(slide)
    if lead_popped:
        sec_count[next((i for i, c in enumerate(sec_count) if c), 0)] -= 1
    if concl_popped:
        sec_count[max((i for i, c in enumerate(sec_count) if c), default=0)] -= 1
    groups: list[tuple[AtSpec, list[Any]]] = []
    pos = 0
    for sc, spec in enumerate(specs):
        groups.append((spec, slide.elements[pos : pos + sec_count[sc]]))
        pos += sec_count[sc]
    used = [g for g in groups if g[1]]
    if len(specs) > 1 and len(used) > 1:
        slide_spec = AtSpec()
        slide_els: list[Any] = []
        for spec, els in groups:
            flags = [c for c in spec.classes if c in FLAGS]
            slide_spec.layout = spec.layout or slide_spec.layout
            slide_spec.classes += [c for c in spec.classes if c not in FLAGS and c not in slide_spec.classes]
            slide_spec.attrs.update(spec.attrs)
            slide_spec.id = spec.id or slide_spec.id
            slide_spec.background = spec.background or slide_spec.background
            slide_spec.transition = spec.transition or slide_spec.transition
            slide_spec.hidden = slide_spec.hidden or spec.hidden
            if not els:
                continue
            if len(els) == 1:
                slide_els.extend(els)
                continue
            if "steps" in flags and not _all_steps(els):
                ctx.add(
                    "warning",
                    "'@steps' needs a row of two or more '##' steps and nothing else",
                    getattr(els[0], "line", None),
                    "steps-few",
                    "put other blocks after '@end' and an '@' line of their own, or drop 'steps'",
                )
                flags = [f for f in flags if f != "steps"]
            g = Container(
                classes=["plain", "group", *flags], grid=spec.grid, line=getattr(els[0], "line", None)
            )
            if spec.gap is not None:
                g.gap = spec.gap
            g.children = els
            g.links = _resolve_links(spec.links, len(els), "group", ctx, g, els)
            slide_els.append(g)
        slide.elements = slide_els
        slide.grid = f"1x{len(slide_els)}"
        spec = slide_spec
        slide.layout = spec.layout
        slide.classes += [c for c in spec.classes if c not in slide.classes]
        slide.attrs.update(spec.attrs)
        slide.id = spec.id or slide.id
        slide.background = spec.background
        slide.transition = spec.transition
        slide.hidden = spec.hidden
        slide_links = []
    elif any(sa for sa in sec_ats):
        keep = specs.index(used[0][0]) if used else 0
        spec = _merge_specs(
            [replace(s, grid=None) if i != keep else s for i, s in enumerate(specs)],
            ctx,
            [0] * len(specs),
        )
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

    if "html" in slide.classes:
        slide.classes.remove("html")
    if kpi_all and "kpi" in slide.classes:
        slide.classes.remove("kpi")  # the word styled the boxes; the slide itself is no KPI card
    if html_src is not None:
        if slide.elements or slide.lead or slide.conclusion or slide.footnotes:
            ctx.add(
                "warning",
                "'@html' slide ignores its other blocks",
                slide.line,
                "dropped-content",
                "put everything inside the ```html fence, or remove '@html'",
            )
        slide.elements, slide.lead, slide.conclusion, slide.footnotes = [], None, None, []
        slide.grid, slide_links = None, []
        slide.layout = slide.layout or "blank"
        slide.html = html_src
    _check_form(slide, ctx)
    _infer_cover(slide, index, ctx)
    if "grid" in slide.classes and slide.layout != "free":
        slide.classes.remove("grid")
        ctx.add(
            "warning",
            "'@grid' needs a @free slide",
            slide.line,
            "unknown-token",
            "write `@free grid`: x y w h then snap to 12 columns and 12 rows (x=3c w=4c)",
        )
    slide.links = _resolve_links(slide_links, len(slide.elements), "slide", ctx, slide, slide.elements)
    for box, raw in ctx.box_links:
        box.links = _resolve_links(raw, len(box.children), "box", ctx, box, box.children)
    ctx.box_links = []
    _expand_steps(slide, ctx)
    return slide


def _all_steps(els: list[Any]) -> bool:
    return len(els) >= 2 and all(isinstance(e, Container) and e.title is not None for e in els)


def _expand_steps(slide: Slide, ctx: Ctx) -> None:
    """``@steps``: the slide's ``##`` steps become one ``steps`` group (arrows over cards, by the layout).

    The group takes the slide grid (``@4 steps`` / ``@1:2:1 steps``: one column per step; anything else is
    one equal column per step). Blocks that are not ``##`` steps stay full width below it. Fewer than two
    steps: a hint, and the slide is left as written.
    """
    if "steps" not in slide.classes:
        return
    slide.classes = [c for c in slide.classes if c not in ("steps", "chevron")]  # arrows are the steps' own
    steps = [e for e in slide.elements if isinstance(e, Container) and e.title is not None]
    if len(steps) < 2:
        ctx.add(
            "warning",
            f"'@steps' needs two or more '##' steps, found {len(steps)}",
            slide.line,
            "steps-few",
            "write one '## Heading' per step with its bullets under it, or drop '@steps'",
        )
        return
    n = len(steps)
    g = (slide.grid or "").strip()
    ok = steps_grid_ok(g, n)
    if g and not ok:
        ctx.add(
            "info",
            f"grid '{g}' replaced by {n} equal columns for '@steps'",
            slide.line,
            "steps-grid",
            f"use @{n} steps, or ratios such as @{':'.join(['1'] * n)} steps",
        )
    if slide.links:
        ctx.add(
            "info", "slide connectors are ignored with '@steps'", slide.line, "steps-links", "remove them"
        )
    group_steps(slide, steps, g if ok else str(n))


def steps_grid_ok(grid: str, n: int) -> bool:
    """A slide grid that gives each of ``n`` steps its own column (``4``, ``1:2:1``)."""
    return (grid.isdigit() and int(grid) >= n) or (
        ":" in grid and grid.count(":") + 1 >= n and "/" not in grid
    )


def group_steps(slide: Slide, steps: list[Any], grid: str) -> None:
    """The ``##`` ``steps`` of ``slide`` become one ``steps`` group (arrows over cards, by the layout)."""
    group = Container(classes=["plain", "group", "steps"], grid=grid, children=steps, line=steps[0].line)
    rest = [e for e in slide.elements if all(e is not b for b in steps)]
    slide.elements = [group, *rest]
    slide.links = []
    slide.grid = f"1x{len(slide.elements)}" if rest else None


def _hint_missing_end(box_els: list[Container], ctx: Ctx, trail: int | None = None) -> None:
    """Info when the last `##` box seems to swallow slide-level content (a forgotten `@end`).

    Runs per row-group section. A closing `>` needs no `@end`: it becomes the conclusion anyway.
    ``trail`` is the line of a plain paragraph after the last box's list (see ``_trailing_para``)."""
    if len(box_els) < 2:
        return
    *rest, last = box_els

    def visual(e: Any) -> bool:
        return isinstance(e, (Table, Chart)) or (isinstance(e, Text) and "callout" in e.classes)

    odd = next((e for e in last.children if visual(e)), None)
    if odd is None and trail is not None:
        what, line = "a paragraph", trail
    elif odd is None or any(visual(c) for b in rest for c in b.children):
        return
    else:
        what = "a callout" if isinstance(odd, Text) else f"a {odd.type}"
        line = getattr(odd, "line", None) or last.line
    ctx.add(
        "info",
        f"the last box '{_box_title(last)}' holds {what} that its sibling boxes do not",
        line,
        "missing-end",
        "if it belongs to the slide, put a line '@end' before it",
    )


LIST_LINE = re.compile(r"^\s*([-*+]|\d+[.)])\s")


def _trailing_para(boxes: list[tuple[Item, list[Item], list[Item]]]) -> int | None:
    """Line of a plain paragraph after the last box's list while every sibling box ends with a list."""
    if len(boxes) < 2:
        return None
    content = boxes[-1][1]
    if not content or content[-1].kind != "md":
        return None
    it = content[-1]
    ls = list(it.lines)
    while ls and not ls[-1].strip():
        ls.pop()
    j = max((k for k, x in enumerate(ls) if not x.strip()), default=-1)
    before = [x for x in ls[:j] if x.strip()]
    if j < 1 or not before or not LIST_LINE.match(before[0]):
        return None
    first = ls[j + 1]
    if LIST_LINE.match(first) or first.startswith((">", "|", "!", "{")):
        return None
    for _h2, sib, _ats in boxes[:-1]:
        if not sib or sib[-1].kind != "md":
            return None
        last = [x for x in sib[-1].lines if x.strip()]
        if not last or not LIST_LINE.match(last[-1]):
            return None
    return it.line + j + 1


def _box_title(c: Container) -> str:
    return c.title.paragraphs[0].plain[:20] if c.title and c.title.paragraphs else "box"


def _resolve_links(
    raw: list[RawLink], n: int, owner: str, ctx: Ctx, obj: Any = None, kids: list[Any] | None = None
) -> list[Link]:
    """Keep the connectors whose ends are existing, distinct blocks; warn about the rest.

    With ``flow`` on ``obj``, explicit links replace the flow arrows: the flag is dropped and the one-row
    grid it implied is written out (one column per leading box), so only the links are drawn."""
    out: list[Link] = []
    for r in raw:
        if r.src == r.dst:
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
    if out and obj is not None and "flow" in obj.classes:
        obj.classes.remove("flow")
        if getattr(obj, "grid", None) is None:
            k = 0
            while k < len(kids or []) and isinstance((kids or [])[k], Container):
                k += 1
            if k >= 2:
                obj.grid = str(k)
        ctx.add(
            "info",
            "explicit connectors replace the flow arrows",
            raw[0].line,
            "flow-links",
            "use either 'flow' or a>b links; only the links are drawn",
        )
    return out


def _lead_and_conclusion(slide: Slide) -> tuple[bool, bool]:
    """Take the lead and conclusion; returns whether each was removed from the flat element list."""
    els = slide.elements
    lead = concl = False
    if els and _is_quote(els[0]):
        q = els.pop(0)
        slide.lead = _as_role(q, "lead")
        lead = True
    if els and _is_quote(els[-1]):
        slide.conclusion = _as_role(els.pop(), "conclusion")
        concl = True
    elif (
        els
        and isinstance(els[-1], Container)
        and len(els[-1].children) > 1
        and _is_quote(els[-1].children[-1])
    ):
        slide.conclusion = _as_role(els[-1].children.pop(), "conclusion")
    return lead, concl


def _as_role(t: Text, role: str) -> Text:
    t.role = role  # type: ignore[assignment]
    return t


def _cover_lines(els: list[Any]) -> tuple[list[Text], list[Container]] | None:
    """Body texts of a cover with every plain-text ``##`` box flattened into subtitle lines.

    ``None`` when some block is neither body text nor a ``##`` box that holds only body text.
    """
    out: list[Text] = []
    boxes: list[Container] = []
    for e in els:
        if isinstance(e, Text) and e.role == "body" and "callout" not in e.classes:
            out.append(e)
        elif (
            isinstance(e, Container)
            and e.title is not None
            and e.grid is None
            and not e.links
            and not {"kpi", "flow", "chevron", "diagram"} & set(e.classes)
            and all(
                isinstance(c, Text) and c.role == "body" and "callout" not in c.classes for c in e.children
            )
        ):
            boxes.append(e)
            out.append(e.title)
            out.extend(e.children)  # type: ignore[arg-type]
        else:
            return None
    return out, boxes


def _check_form(slide: Slide, ctx: Ctx) -> None:
    """DL3b forms (`@timeline` ...): one per slide, keys and values valid, the blocks the form needs."""
    found = [c for c in slide.classes if c in forms.FORMS]
    line = slide.line
    if len(found) > 1:
        ctx.add(
            "warning",
            f"two forms on one slide: @{found[0]} and @{found[1]}",
            line,
            "form-conflict",
            f"keep one: @{found[0]} is used",
        )
    form = found[0] if found else forms.form_of(slide)  # (`@flow disc` is the pseudo form `flowdisc`)
    if "disc" in slide.classes and "flow" not in slide.classes:
        ctx.add(
            "warning",
            "@disc is a word of @flow",
            line,
            "attr-ignored",
            "write `@flow disc` (a row of icon discs joined by lines)",
        )
    if form or not forms2.word_of(
        slide.classes
    ):  # an @quote / @split ... slide: ``forms2.check_at`` owns its keys
        for rule, msg, hint in forms.check_attrs(form, slide.attrs):
            ctx.add("warning", msg, line, rule, hint)
    if form and (why := forms.fits(form, slide)):
        rule = "flow-skipped" if form == "flowdisc" else f"{form}-skipped"
        ctx.add(
            "warning",
            why,
            line,
            rule,
            "the slide is laid out as ordinary blocks; " + forms.EXAMPLE[form],
        )


def _infer_cover(slide: Slide, index: int, ctx: Ctx | None = None) -> None:
    if slide.title is None or slide.layout in ("blank", "center", "free") or forms.form_of(slide):
        return
    els = slide.elements
    if not els:
        return
    got = _cover_lines(els)
    if got is None:
        return
    texts, boxes = got
    explicit = slide.layout in ("cover", "section")
    if not explicit:
        paras = [p for t in texts for p in t.paragraphs]
        limit = SHORT_LINE * (2 if index == 0 else 1)  # first-slide subtitles are often a long tagline
        short = (
            len(paras) <= 2
            and all(p.marker is None and len(p.plain) <= limit for p in paras)
            and slide.lead is None
            and slide.conclusion is None
            and slide.grid is None
            # a lone `## x` with body text stays a card; bare `## x` lines (no body) are the subtitle
            and (not boxes or any(isinstance(e, Text) for e in els) or not any(b.children for b in boxes))
        )
        if not short:
            return
    if boxes and ctx is not None and any(b.children for b in boxes):
        ctx.add(
            "info",
            "'## ' on a cover or section slide is a subtitle line, not a box",
            boxes[0].line,
            "cover-heading",
            "write the line without '## ' (use '## ' boxes on content slides)",
        )
    slide.subtitle = _merge_text(texts, "subtitle")
    if boxes:  # `## sub {x= y= size=}`: the box's own attributes style and place the subtitle
        b = boxes[0]
        slide.subtitle.box = slide.subtitle.box or b.box
        if b.style is not None:
            slide.subtitle.style = (slide.subtitle.style or Style()).merged(b.style)
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
    css_fences = extract_fences(lines)  # css fences are consumed here: never code blocks, never drawn
    if css_fences:
        inside, _ = fence_map(lines)
    start = parse_header(lines, inside, deck, ctx)
    ctx.lang = deck.lang
    ctx.colors = {k.split(".", 1)[1] for k in deck.tokens if k.startswith("colors.")}
    recs = normalize(lines, inside, start, deck)
    chunks = split_slides(lines, inside, start)
    if not chunks:
        ctx.warn("no slides found", None, "no-slides", "start a slide with '# Title'")
    by_chunk: dict[int, list[Rec]] = {}
    first_line = (
        min((c.title_idx if c.title_idx is not None else c.start) for c in chunks) if chunks else None
    )
    deck.css += style_css_rules(deck, ctx)  # before header fences: a fence wins
    slide_css: dict[int, list[tuple[int, str]]] = {}
    for fi, body in css_fences:
        if first_line is None or fi < first_line:
            deck.css += parse_css(body, fi + 2, ctx, deck, header=True)
            note_stated(deck, "css")
        else:
            # the slide whose chunk starts last before the fence (blank separator slides are dropped)
            k = max(
                (
                    ci
                    for ci, c in enumerate(chunks)
                    if (c.title_idx if c.title_idx is not None else c.start) <= fi
                ),
                default=0,
            )
            slide_css.setdefault(k, []).append((fi, body))
    finish_tokens(deck, ctx)
    slide_tok = {  # `sizes:` / `style:` lines inside a slide: that slide only
        ci: found
        for ci, c in enumerate(chunks)
        if (found := take_slide_tokens(lines, inside, c.start, c.end))
    }
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
            slide = parse_slide(chunk, lines, inside, ctx, idx, by_chunk.get(idx))
            if idx in slide_tok:
                slide.tokens, rules = slide_tokens(deck, slide_tok[idx], ctx)
                slide.css += rules
                note_stated(deck, "style")
            for fi, body in slide_css.get(idx, []):
                slide.css += parse_css(body, fi + 2, ctx, deck)
            deck.slides.append(slide)
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

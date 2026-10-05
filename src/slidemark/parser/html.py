"""HTML (structural subset) -> the same IR as the Markdown form.

``parse_html(text)`` reads a whole ``.html`` file (``<section class="slide">`` = slide);
``html_blocks(text, ctx, line)`` converts the body of a ```html fence inside a Markdown slide.
Only the stdlib ``html.parser`` is used. Never raises: unknown elements stay ``Raw(kind="html")`` plus an
info diagnostic ``html-fallback``.
"""

from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass, field, replace
from html.parser import HTMLParser
from typing import Any

from ..ir import (
    Cell,
    Chart,
    Code,
    Container,
    Deck,
    Image,
    Link,
    Media,
    Paragraph,
    Raw,
    Run,
    Series,
    Slide,
    Style,
    Table,
    Text,
)
from .attrs import media_kind
from .ctx import Ctx
from .inline import BADGE_COLORS, _finish
from .mermaid import build_mermaid

MAX_DEPTH = 120
MAX_AREAS = 26
VOID = {"br", "hr", "img", "meta", "link", "input", "col", "area", "base", "wbr", "source", "param", "embed"}
SKIP = {"script", "style", "template", "noscript"}
INLINE = {
    "a", "b", "strong", "i", "em", "u", "s", "del", "strike", "code", "kbd", "samp", "sub", "sup",
    "mark", "span", "small", "big", "abbr", "cite", "q", "time", "label", "font", "br", "wbr", "var",
    "ins", "tt", "bdi", "bdo",
}  # fmt: skip
TRANSPARENT = {
    "div",
    "section",
    "article",
    "main",
    "header",
    "footer",
    "aside",
    "body",
    "html",
    "figure",
    "nav",
}
RAW_TAGS = {
    "svg", "iframe", "canvas", "video", "audio", "object", "embed", "form", "input", "button", "select",
    "textarea", "math", "picture", "details",
}  # fmt: skip
HEADS = {"h1", "h2", "h3", "h4", "h5", "h6"}
P_CLOSERS = {"div", "p", "ul", "ol", "table", "section", "header", "footer", "blockquote", "pre", *HEADS}
BOX_CLASSES = {"card", "kpi", "chevron", "box"}
KEEP_CLASSES = {"kpi", "dense", "muted", "zebra"}
LAYOUT_WORDS = {"cover", "section", "blank", "center", "free"}
CALLOUTS = {
    "note": "note", "info": "note", "tip": "tip", "success": "tip", "warn": "warn", "warning": "warn",
    "caution": "caution", "danger": "caution", "important": "note",
}  # fmt: skip
CHART_KINDS = (
    "bar", "column", "stacked-bar", "stacked-column", "line", "area", "pie", "doughnut", "scatter", "radar",
)  # fmt: skip
WS = re.compile(r"\s+")
HINT = "kept as raw HTML (an image when rendering is available); use section.slide, h1, h2 cards, ul, table for editable shapes"  # noqa: E501


# --------------------------------------------------------------------------- tree


class Node:
    __slots__ = ("tag", "attrs", "children", "line", "start", "end")

    def __init__(self, tag: str, attrs: dict[str, str], line: int):
        self.tag, self.attrs, self.line = tag, attrs, line
        self.start: int | None = None  # source offsets of the element (``outer_html``)
        self.end: int | None = None
        self.children: list[Node | str] = []

    @property
    def classes(self) -> list[str]:
        return self.attrs.get("class", "").lower().split()

    def style(self) -> dict[str, str]:
        out: dict[str, str] = {}
        for part in self.attrs.get("style", "").split(";"):
            if ":" in part:
                k, v = part.split(":", 1)
                out[k.strip().lower()] = v.strip().lower()
        return out

    def elements(self) -> list[Node]:
        return [c for c in self.children if isinstance(c, Node)]


class _Builder(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.root = Node("#root", {}, 0)
        self.stack: list[Node] = [self.root]
        self.skip: str | None = None
        self.src = ""
        self.starts: list[int] = [0]

    def _offset(self) -> int:
        line, col = self.getpos()
        return self.starts[min(line - 1, len(self.starts) - 1)] + col

    def _close_to(self, names: set[str], stop: set[str]) -> None:
        for i in range(len(self.stack) - 1, 0, -1):
            t = self.stack[i].tag
            if t in names:
                del self.stack[i:]
                return
            if t in stop:
                return

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if self.skip:
            return
        tag = tag.lower()
        if tag in SKIP:
            self.skip = tag
            return
        if tag == "li":
            self._close_to({"li"}, {"ul", "ol"})
        elif tag in ("td", "th"):
            self._close_to({"td", "th"}, {"tr", "table"})
        elif tag == "tr":
            self._close_to({"tr"}, {"table", "thead", "tbody", "tfoot"})
        elif tag in ("thead", "tbody", "tfoot"):
            self._close_to({"thead", "tbody", "tfoot"}, {"table"})
        elif tag in P_CLOSERS and self.stack[-1].tag == "p":
            self.stack.pop()
        node = Node(tag, {k.lower(): (v or "") for k, v in attrs}, self.getpos()[0])
        node.start = self._offset()
        self.stack[-1].children.append(node)
        if tag not in VOID and len(self.stack) < MAX_DEPTH:
            self.stack.append(node)

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if self.skip:
            if tag == self.skip:
                self.skip = None
            return
        for i in range(len(self.stack) - 1, 0, -1):
            if self.stack[i].tag == tag:
                close = self.src.find(">", self._offset())
                self.stack[i].end = close + 1 if close >= 0 else None
                del self.stack[i:]
                return

    def handle_data(self, data: str) -> None:
        if self.skip or not data:
            return
        kids = self.stack[-1].children
        if kids and isinstance(kids[-1], str):
            kids[-1] += data
        else:
            kids.append(data)


def build_tree(text: str) -> Node:
    b = _Builder()
    b.src = text
    for m in re.finditer("\n", text):
        b.starts.append(m.end())
    try:
        b.feed(text)
        b.close()
    except Exception:  # html.parser is lenient, but never let it escape
        pass
    return b.root


def raw_text(n: Node | str) -> str:
    if isinstance(n, str):
        return n
    return "".join(raw_text(c) for c in n.children)


def to_html(n: Node | str, depth: int = 0) -> str:
    if isinstance(n, str):
        return n.replace("&", "&amp;").replace("<", "&lt;")
    attrs = "".join(f' {k}="{v}"' for k, v in n.attrs.items())
    if n.tag in VOID:
        return f"<{n.tag}{attrs}>"
    inner = "" if depth > 60 else "".join(to_html(c, depth + 1) for c in n.children)
    return f"<{n.tag}{attrs}>{inner}</{n.tag}>"


def find_all(n: Node, pred: Any, stop_at_match: bool = True) -> list[Node]:
    out: list[Node] = []
    for c in n.elements():
        if pred(c):
            out.append(c)
            if stop_at_match:
                continue
        out.extend(find_all(c, pred, stop_at_match))
    return out


# --------------------------------------------------------------------------- inline


@dataclass(frozen=True)
class _Fmt:
    bold: bool = False
    italic: bool = False
    underline: bool = False
    strike: bool = False
    code: bool = False
    sup: bool = False
    sub: bool = False
    color: str | None = None
    highlight: str | None = None
    link: str | None = None


def _color_of(n: Node) -> str | None:
    c = n.style().get("color")
    if c and re.fullmatch(r"#[0-9a-f]{3}|#[0-9a-f]{6}", c):
        return c
    return next((k for k in n.classes if k in BADGE_COLORS), None)


def _inline(nodes: list[Node | str], f: _Fmt, out: list[Run]) -> None:
    for n in nodes:
        if isinstance(n, str):
            t = WS.sub(" ", n)
            if t:
                out.append(Run(text=t, **f.__dict__))
            continue
        tag = n.tag
        if tag == "br":
            out.append(Run(text="\n"))
            continue
        g = f
        if tag in ("b", "strong") or tag in HEADS:
            g = replace(g, bold=True)
        elif tag in ("i", "em", "cite", "var"):
            g = replace(g, italic=True)
        elif tag in ("u", "ins"):
            g = replace(g, underline=True)
        elif tag in ("s", "del", "strike"):
            g = replace(g, strike=True)
        elif tag in ("code", "kbd", "samp", "tt"):
            g = replace(g, code=True)
        elif tag == "sub":
            g = replace(g, sub=True)
        elif tag == "sup":
            g = replace(g, sup=True)
        elif tag == "mark":
            g = replace(g, color="accent")
        elif tag == "a" and n.attrs.get("href"):
            g = replace(g, link=n.attrs["href"])
        elif tag == "span" or tag == "font":
            if "badge" in n.classes:
                col = next((k for k in n.classes if k in BADGE_COLORS), "primary")
                g = replace(g, highlight=col, color="bg", bold=True)
            else:
                col = _color_of(n)
                if col:
                    g = replace(g, color=col)
        _inline(n.children, g, out)


def _tidy(runs: list[Run]) -> list[Run]:
    for i, r in enumerate(runs):
        if r.text == "\n":
            continue
        if i == 0 or runs[i - 1].text == "\n":
            r.text = r.text.lstrip(" ")
        if i == len(runs) - 1 or runs[i + 1].text == "\n":
            r.text = r.text.rstrip(" ")
    while runs and runs[-1].text == "\n":
        runs.pop()
    while runs and runs[0].text == "\n":
        runs.pop(0)
    return _finish([r for r in runs if r.text])


def inline_runs(nodes: list[Node | str]) -> list[Run]:
    out: list[Run] = []
    _inline(nodes, _Fmt(), out)
    return _tidy(out)


def _paras(nodes: list[Node | str], level: int = 0, list_level: int = 0) -> list[Paragraph]:
    """Paragraphs from block/inline children: lists become marked paragraphs, blocks start a new one."""
    out: list[Paragraph] = []
    buf: list[Node | str] = []

    def flush(bold: bool = False) -> None:
        runs = inline_runs(buf)
        buf.clear()
        if runs:
            if bold:
                for r in runs:
                    r.bold = True
            out.append(Paragraph(runs=runs, level=level))

    for n in nodes:
        if isinstance(n, str) or n.tag in INLINE:
            buf.append(n)
        elif n.tag in ("ul", "ol"):
            flush()
            out.extend(_list(n, list_level))
        elif n.tag in HEADS:
            flush()
            runs = inline_runs(n.children)
            for r in runs:
                r.bold = True
            if runs:
                out.append(Paragraph(runs=runs, level=level))
        elif n.tag == "pre":
            flush()
            out.append(Paragraph(runs=[Run(text=raw_text(n).strip("\n"), code=True)], level=level))
        elif n.tag in SKIP:
            continue
        else:
            flush()
            out.extend(_paras(n.children, level, list_level))
    flush()
    return out


def _list(n: Node, level: int) -> list[Paragraph]:
    marker = "number" if n.tag == "ol" else "bullet"
    out: list[Paragraph] = []
    for li in n.elements():
        if li.tag != "li":
            out.extend(_paras([li], level, level))
            continue
        ps = _paras(li.children, level, level + 1)
        if ps and ps[0].marker is None:
            ps[0].marker = marker  # type: ignore[assignment]
        out.extend(ps)
    return out


# --------------------------------------------------------------------------- grid


def _tracks(value: str | None, n_items: int) -> list[float]:
    if not value:
        return []
    toks: list[str] = []
    depth, cur = 0, ""
    for ch in value:
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth = max(depth - 1, 0)
        if ch.isspace() and depth == 0:
            if cur:
                toks.append(cur)
            cur = ""
        else:
            cur += ch
    if cur:
        toks.append(cur)
    out: list[float] = []
    for t in toks:
        m = re.fullmatch(r"repeat\(\s*([\w-]+)\s*,\s*(.+)\)", t)
        if m:
            cnt = int(m.group(1)) if m.group(1).isdigit() else min(max(n_items, 1), 4)
            inner = _tracks(m.group(2), n_items)
            out.extend(inner * min(cnt, MAX_AREAS))
        else:
            fr = re.fullmatch(r"(\d+(?:\.\d+)?)fr", t)
            out.append(float(fr.group(1)) if fr and float(fr.group(1)) > 0 else 1.0)
        if len(out) > MAX_AREAS:
            return out[:MAX_AREAS]
    return out


def _span(value: str | None) -> int:
    if not value:
        return 1
    v = value.replace("!important", "").strip()
    m = re.search(r"span\s+(\d+)", v)
    if m:
        return max(1, min(int(m.group(1)), MAX_AREAS))
    m = re.fullmatch(r"(\d+)\s*/\s*(\d+)", v)
    if m:
        return max(1, min(int(m.group(2)) - int(m.group(1)), MAX_AREAS))
    return 1


def _fmt_num(x: float) -> str:
    return str(int(x)) if float(x).is_integer() else str(x)


def _units(weights: list[float]) -> list[int]:
    """Whole-number unit widths for fr weights (``2fr 1fr`` -> [2, 1]); equal widths when not possible."""
    if not weights or any(abs(w - round(w)) > 1e-9 for w in weights):
        return [1] * len(weights)
    ints = [int(round(w)) for w in weights]
    g = math.gcd(*ints) if len(ints) > 1 else ints[0]
    ints = [i // g for i in ints]
    return ints if sum(ints) <= 12 else [1] * len(weights)


def grid_spec(
    style: dict[str, str], spans: list[tuple[int, int]], n_items: int
) -> tuple[str | None, str | None]:
    """The ``@`` grid spec (and gap) for a CSS grid/flex container and its children's spans."""
    cols = _tracks(style.get("grid-template-columns"), n_items)
    rows = _tracks(style.get("grid-template-rows"), n_items)
    if not cols:
        if style.get("display") == "flex" and "column" not in style.get("flex-direction", ""):
            cols = [1.0] * max(min(n_items, MAX_AREAS), 1)
        else:
            cols = [1.0]
    gap = style.get("gap") or style.get("grid-gap")
    gap = gap.split()[0] if gap else None
    ncols = len(cols)
    spans = [(min(cs, ncols), rs) for cs, rs in spans]
    if not any(cs > 1 or rs > 1 for cs, rs in spans) or n_items > MAX_AREAS:
        if ncols == 1 or len(set(cols)) == 1:
            return str(ncols), gap
        return ":".join(_fmt_num(c) for c in cols), gap
    occ: set[tuple[int, int]] = set()
    place: list[tuple[int, int, int, int]] = []
    r = c = 0
    for cs, rs in spans:
        while True:
            if c + cs > ncols:
                r, c = r + 1, 0
            if all((rr, cc) not in occ for rr in range(r, r + rs) for cc in range(c, c + cs)):
                break
            c += 1
        for rr in range(r, r + rs):
            for cc in range(c, c + cs):
                occ.add((rr, cc))
        place.append((r, c, cs, rs))
    nrows = max(p[0] + p[3] for p in place)
    cu = _units(cols)
    ru = _units(rows[:nrows]) if len(rows) >= nrows else [1] * nrows
    cstart = [sum(cu[:i]) for i in range(ncols + 1)]
    rstart = [sum(ru[:i]) for i in range(nrows + 1)]
    grid = [["."] * cstart[-1] for _ in range(rstart[-1])]
    for i, (pr, pc, cs, rs) in enumerate(place):
        for y in range(rstart[pr], rstart[min(pr + rs, nrows)]):
            for x in range(cstart[pc], cstart[min(pc + cs, ncols)]):
                grid[y][x] = chr(97 + i)
    return "/".join("".join(row) for row in grid), gap


# --------------------------------------------------------------------------- conversion


@dataclass
class _Sink:
    elements: list[Any] = field(default_factory=list)
    cur: Text | None = None
    grid: str | None = None
    gap: str | None = None
    classes: list[str] = field(default_factory=list)


class _Conv:
    def __init__(self, ctx: Ctx, base_line: int = 0, slide_grid: bool = True):
        self.ctx = ctx
        self.base = base_line
        self.slide_grid = slide_grid
        self.title: Text | None = None
        self.lead: Text | None = None
        self.conclusion: Text | None = None
        self.footnotes: list[Text] = []
        self.arrows: list[tuple[str, str, int]] = []
        self.notes: list[str] = []

    # -- helpers
    def at(self, n: Node) -> int | None:
        return self.base + n.line if n.line else None

    def fallback(self, n: Node, sink: _Sink, why: str) -> None:
        self.flush(sink)
        self.ctx.add("info", f"<{n.tag}> {why}", self.at(n), "html-fallback", HINT)
        sink.elements.append(Raw(kind="html", source=to_html(n)[:4000], line=self.at(n)))

    def flush(self, sink: _Sink) -> None:
        if sink.cur is not None and sink.cur.paragraphs:
            sink.elements.append(sink.cur)
        sink.cur = None

    def add_paras(self, sink: _Sink, paras: list[Paragraph]) -> None:
        if not paras:
            return
        if sink.cur is None:
            sink.cur = Text(role="body")
        sink.cur.paragraphs.extend(paras)

    def text_of(self, n: Node, role: str, classes: list[str] | None = None) -> Text:
        return Text(
            role=role,  # type: ignore[arg-type]
            paragraphs=_paras(n.children),
            classes=classes or [],
            id=n.attrs.get("id") or None,
            line=self.at(n),
        )

    def footnote(self, n: Node) -> None:
        t = self.text_of(n, "footnote")
        if t.paragraphs and t.paragraphs[0].runs:
            r = t.paragraphs[0].runs[0]
            r.text = r.text.lstrip("※ 　")
        if t.paragraphs:
            self.footnotes.append(t)

    # -- walk
    def walk(self, nodes: list[Node | str], sink: _Sink) -> None:
        inl: list[Node | str] = []

        def flush_inline() -> None:
            if inl:
                self.add_paras(sink, _paras(inl))
                inl.clear()

        for n in nodes:
            if isinstance(n, str) or n.tag in INLINE:
                inl.append(n)
                continue
            flush_inline()
            self.block(n, sink)
        flush_inline()

    def block(self, n: Node, sink: _Sink) -> None:
        tag, cls = n.tag, n.classes
        if tag in ("head", "title", "meta", "link", "hr", "br") or tag in SKIP:
            return
        if tag == "h1" and self.title is None:
            self.title = Text(
                role="title", paragraphs=[Paragraph(runs=inline_runs(n.children))], line=self.at(n)
            )
            return
        if tag in ("p", "figcaption") or (tag in TRANSPARENT and ("lead" in cls or "conclusion" in cls)):
            plain = raw_text(n).strip()
            if "lead" in cls and self.lead is None:
                self.lead = self.text_of(n, "lead")
            elif "conclusion" in cls and self.conclusion is None:
                self.conclusion = self.text_of(n, "conclusion")
            elif "note" in cls or plain.startswith("※"):
                self.footnote(n)
            else:
                self.add_paras(sink, _paras([n]))
            return
        if tag in ("ul", "ol") or tag in HEADS:
            self.add_paras(sink, _paras([n]))
            return
        if tag == "table":
            self.flush(sink)
            sink.elements.append(self.table(n))
            return
        if tag == "blockquote":
            self.flush(sink)
            sink.elements.append(self.text_of(n, "quote"))
            return
        if tag == "pre":
            self.pre(n, sink)
            return
        if tag == "img":
            src = n.attrs.get("src", "")
            if not src:
                self.fallback(n, sink, "image without src")
                return
            self.flush(sink)
            sink.elements.append(
                Image(src=src, alt=n.attrs.get("alt", ""), id=n.attrs.get("id") or None, line=self.at(n))
            )
            return
        if tag in ("video", "audio"):
            src = n.attrs.get("src") or next(
                (c.attrs["src"] for c in n.elements() if c.tag == "source" and c.attrs.get("src")), ""
            )
            kind = media_kind(src)
            if kind:
                self.flush(sink)
                media = Media(
                    kind=kind,  # type: ignore[arg-type]
                    src=src,
                    alt=n.attrs.get("aria-label") or n.attrs.get("title") or n.attrs.get("alt", ""),
                    poster=n.attrs.get("poster") or None,
                    autoplay="autoplay" in n.attrs,
                    loop="loop" in n.attrs,
                    id=n.attrs.get("id") or None,
                    line=self.at(n),
                )
                sink.elements.append(media)
                return
        if tag in RAW_TAGS:
            self.fallback(n, sink, "is not converted")
            return
        if "mermaid" in cls:
            self.flush(sink)
            sink.elements.append(build_mermaid(raw_text(n), self.ctx, self.at(n)))
            return
        if "arrow" in cls and n.attrs.get("data-from") and n.attrs.get("data-to"):
            self.arrows.append((n.attrs["data-from"], n.attrs["data-to"], n.line))
            return
        if "chart" in cls and any(k.startswith("data-") for k in n.attrs):
            self.flush(sink)
            sink.elements.append(self.chart(n))
            return
        if "callout" in cls:
            self.flush(sink)
            kind = next((CALLOUTS[k] for k in cls if k in CALLOUTS), "note")
            sink.elements.append(self.text_of(n, "body", ["callout", kind]))
            return
        inline_only = all(isinstance(c, str) or c.tag in INLINE for c in n.children)
        if "note" in cls or (tag == "footer" and inline_only and raw_text(n).strip().startswith("※")):
            self.footnote(n)
            return
        if "notes" in cls and tag in ("aside", "div"):
            self.notes.append(raw_text(n).strip())
            return
        if self.is_box(n):
            self.box(n, sink)
            return
        if self.is_grid(n):
            self.emit_grid(n, n.children, sink)
            return
        if tag in TRANSPARENT or tag in ("dl", "dt", "dd", "li", "tr", "td", "th", "tbody", "thead", "tfoot"):
            self.walk(n.children, sink)
            return
        self.walk(n.children, sink)  # unknown custom tag: keep its content

    def is_grid(self, n: Node) -> bool:
        return n.style().get("display") in ("grid", "flex", "inline-grid", "inline-flex")

    def is_box(self, n: Node) -> bool:
        if n.tag not in ("div", "section", "article", "aside", "figure"):
            return False
        if set(n.classes) & BOX_CLASSES:
            return True
        return any(c.tag in ("h2", "h3") for c in n.elements())

    # -- boxes and grids
    def box(self, n: Node, sink: _Sink) -> None:
        self.flush(sink)
        kids = list(n.children)
        title = next((c for c in kids if isinstance(c, Node) and c.tag in ("h2", "h3")), None)
        if title is not None:
            kids.remove(title)
        cls = n.classes
        c = Container(
            id=n.attrs.get("id") or None,
            classes=[k for k in cls if k in KEEP_CLASSES],
            line=self.at(n),
        )
        if title is not None:
            c.title = Text(role="heading", paragraphs=[Paragraph(runs=inline_runs(title.children))])
        if "kpi" in cls:
            paras: list[Paragraph] = []
            for p in _paras(kids):
                p.marker = None
                runs: list[Run] = []
                for r in [*p.runs, Run(text="\n")]:
                    if r.text == "\n":
                        if runs:
                            paras.append(Paragraph(runs=runs))
                        runs = []
                    else:
                        runs.append(r)
            if paras:
                c.children.append(Text(role="body", paragraphs=paras))
        else:
            sub = _Sink()
            if self.is_grid(n):
                self.emit_grid(n, kids, sub, force_container=False)
            else:
                self.walk(kids, sub)
            self.flush(sub)
            c.children = sub.elements
            if sub.grid:
                c.grid = sub.grid
            if sub.gap:
                c.gap = sub.gap
            c.classes += [k for k in sub.classes if k not in c.classes]
        sink.elements.append(c)

    def emit_grid(self, n: Node, kids: list[Node | str], sink: _Sink, force_container: bool = True) -> None:
        items: list[tuple[Any, int, int]] = []
        chevron = bool(set(n.classes) & {"chevron", "flow"})
        classes = [k for k in n.classes if k in ("chevron", "flow")]
        for c in kids:
            if isinstance(c, str) and not c.strip():
                continue
            sub = _Sink()
            self.walk([c], sub)
            self.flush(sub)
            if not sub.elements:
                continue
            el = sub.elements[0] if len(sub.elements) == 1 else Container(children=sub.elements)
            st = c.style() if isinstance(c, Node) else {}
            area = st.get("grid-area", "")
            cs = _span(
                st.get("grid-column") or st.get("grid-column-end") or (area if "span" in area else None)
            )
            rs = _span(st.get("grid-row") or st.get("grid-row-end"))
            if isinstance(c, Node) and "chevron" in c.classes:
                chevron = True
                if "chevron" not in classes:
                    classes.append("chevron")
            items.append((el, cs, rs))
        if not items:
            return
        grid, gap = grid_spec(n.style(), [(cs, rs) for _, cs, rs in items], len(items))
        els = [el for el, _, _ in items]
        top = self.slide_grid and not sink.elements and sink.cur is None and sink.grid is None
        if top:
            sink.grid, sink.gap = grid, gap
            sink.classes += [k for k in classes if k not in sink.classes]
            sink.elements.extend(els)
        elif not force_container and sink.grid is None and not sink.elements:
            sink.grid, sink.gap = grid, gap
            sink.classes += [k for k in classes if k not in sink.classes]
            sink.elements.extend(els)
        else:
            self.flush(sink)
            wrap = Container(grid=grid, gap=gap, classes=classes if chevron else [], children=els)
            sink.elements.append(wrap)

    # -- leaf elements
    def pre(self, n: Node, sink: _Sink) -> None:
        self.flush(sink)
        code = next((c for c in n.elements() if c.tag == "code"), None)
        lang = None
        for k in (code.classes if code else []) + n.classes:
            if k.startswith("language-"):
                lang = k[9:]
            elif k in ("mermaid", "python", "js", "json", "bash", "sql"):
                lang = k
        text = raw_text(n).strip("\n")
        if lang == "mermaid":
            sink.elements.append(build_mermaid(text, self.ctx, self.at(n)))
        else:
            sink.elements.append(Code(lang=lang, text=text, id=n.attrs.get("id") or None, line=self.at(n)))

    def chart(self, n: Node) -> Chart:
        a = n.attrs
        kind = a.get("data-type", "column").lower()
        if kind not in CHART_KINDS:
            self.ctx.warn(
                f"unknown chart type '{kind}'",
                self.at(n),
                "bad-chart",
                f"use one of {', '.join(CHART_KINDS)}",
            )
            kind = "column"
        ch = Chart(kind=kind, title=a.get("data-title") or None, id=a.get("id") or None, line=self.at(n))  # type: ignore[arg-type]
        cats = a.get("data-categories", "").strip()
        try:
            parsed = json.loads(cats) if cats.startswith("[") else None
        except ValueError:
            parsed = None
        ch.categories = (
            [str(x) for x in parsed]
            if isinstance(parsed, list)
            else ([c.strip() for c in cats.split(",")] if cats else [])
        )
        try:
            data = json.loads(a.get("data-series", "[]"))
        except ValueError:
            data = None
        if not isinstance(data, list):
            self.ctx.warn(
                "chart data-series is not a JSON list",
                self.at(n),
                "bad-chart",
                'write data-series=\'[{"name":"A","data":[1,2]}]\'',
            )
            return ch
        for s in data:
            if not isinstance(s, dict):
                continue
            vals = s.get("data", s.get("values", []))
            out: list[float | None] = []
            for v in vals if isinstance(vals, list) else []:
                try:
                    out.append(None if v is None or isinstance(v, bool) else float(v))
                except (TypeError, ValueError):
                    out.append(None)
            ch.series.append(Series(name=str(s.get("name", "")), values=out))
        if not ch.series:
            self.ctx.warn(
                "chart has no series", self.at(n), "empty-chart", "add data-series with a list of series"
            )
        return ch

    def table(self, n: Node) -> Table:
        trs: list[Node] = []
        head_rows = 0

        def collect(node: Node, in_head: bool) -> None:
            nonlocal head_rows
            for c in node.elements():
                if c.tag == "tr":
                    trs.append(c)
                    head_rows += in_head
                elif c.tag in ("thead", "tbody", "tfoot"):
                    collect(c, in_head or c.tag == "thead")

        collect(n, False)
        trs = trs[:500]
        cells: dict[tuple[int, int], Cell] = {}
        covered: set[tuple[int, int]] = set()
        width = 0
        for r, tr in enumerate(trs):
            c = 0
            for td in tr.elements():
                if td.tag not in ("td", "th"):
                    continue
                while (r, c) in covered:
                    c += 1
                cs = max(1, min(_int(td.attrs.get("colspan")), 50))
                rs = max(1, min(_int(td.attrs.get("rowspan")), len(trs) - r, 50))
                align = td.style().get("text-align") or td.attrs.get("align", "")
                style = Style(align=align) if align in ("left", "center", "right") else None  # type: ignore[arg-type]
                cells[(r, c)] = Cell(paragraphs=_paras(td.children), colspan=cs, rowspan=rs, style=style)
                for rr in range(r, r + rs):
                    for cc in range(c, c + cs):
                        covered.add((rr, cc))
                c += cs
                width = max(width, c)
        grid = [[cells.get((r, c), Cell()) for c in range(width)] for r in range(len(trs))]
        header = head_rows
        if not header:
            for tr in trs:
                tds = [x for x in tr.elements() if x.tag in ("td", "th")]
                if tds and all(x.tag == "th" for x in tds):
                    header += 1
                else:
                    break
        return Table(rows=grid, header_rows=header, id=n.attrs.get("id") or None, line=self.at(n))


def _int(v: str | None) -> int:
    try:
        return int(re.match(r"\s*(\d+)", v or "").group(1))  # type: ignore[union-attr]
    except (AttributeError, ValueError):
        return 1


# --------------------------------------------------------------------------- entry points


def _is_slide(n: Node) -> bool:
    return "slide" in n.classes


def _slide(node: Node, ctx: Ctx, index: int) -> Slide:
    from .core import _infer_cover, _lead_and_conclusion

    conv = _Conv(ctx)
    sink = _Sink()
    conv.walk(node.children, sink)
    conv.flush(sink)
    slide = Slide(line=node.line or None)
    slide.title, slide.lead, slide.conclusion = conv.title, conv.lead, conv.conclusion
    slide.footnotes = conv.footnotes
    slide.elements = sink.elements
    slide.grid = sink.grid
    if sink.gap:
        slide.attrs["gap"] = sink.gap
    slide.classes = list(sink.classes)
    cls = node.classes
    slide.layout = next((k for k in cls if k in LAYOUT_WORDS), None) or node.attrs.get("data-layout") or None
    if slide.layout not in (None, "cover", "section", "blank", "center", "free"):
        slide.layout = None
    for k in ("dense", "dark", "light", "plain"):
        if k in cls and k not in slide.classes:
            slide.classes.append(k)
    slide.id = node.attrs.get("id") or None
    slide.background = node.attrs.get("data-bg") or None
    slide.transition = node.attrs.get("data-transition") or None
    slide.notes = "\n".join(conv.notes) or node.attrs.get("data-notes") or None
    for src, dst, line in conv.arrows:
        ids = [getattr(e, "id", None) for e in slide.elements]
        if src in ids and dst in ids and src != dst:
            slide.links.append(Link(src=ids.index(src), dst=ids.index(dst)))
        else:
            ctx.warn(
                f"arrow {src}>{dst} refers to an unknown element id",
                conv.base + line,
                "bad-link",
                "give both boxes an id attribute, e.g. <div class=card id=a>, at slide level",
            )
    _lead_and_conclusion(slide)
    _infer_cover(slide, index)
    return slide


# CSS properties the structural subset cannot express (it ignores them): a section that uses one is "styled"
VISUAL_PROP = re.compile(
    r"^(background|border|box-shadow|position|top|left|right|bottom|transform|opacity|filter|clip-path|"
    r"padding|outline|text-shadow|z-index|backdrop-filter|mask)"
)
STYLE_BLOCK = re.compile(r"<style\b[^>]*>.*?</style>", re.I | re.S)
CSS_RULE = re.compile(r"([^{}@]+)\{([^{}]*)\}")
CSS_TOKEN = re.compile(r"[.#]?[A-Za-z_][\w-]*")


def _has_visual(decls: str) -> bool:
    return any(VISUAL_PROP.match(d.split(":", 1)[0].strip().lower()) for d in decls.split(";") if ":" in d)


def _subtree_tokens(n: Node, out: set[str]) -> None:
    out.add(n.tag)
    out.update("." + c for c in n.classes)
    if n.attrs.get("id"):
        out.add("#" + n.attrs["id"].lower())
    for c in n.elements():
        _subtree_tokens(c, out)


def _subtree_nodes(n: Node):
    yield n
    for c in n.elements():
        yield from _subtree_nodes(c)


def needs_html(node: Node, styles: list[str], forced: bool) -> bool:
    """Is this ``<section>`` too styled for the structural subset (so it becomes ``Slide.html``)?

    Rule: a section is converted structurally (headings, lists, tables, ``card`` boxes, grid/flex tracks)
    unless it is *styled*, i.e. one of

    - it (or ``<html data-slidemark="native">``) forces HTML: ``data-render="html"`` on the section;
    - it contains an ``<svg>``;
    - an inline ``style`` in it uses a visual property the subset ignores (background, gradient, border,
      border-radius, box-shadow, padding, position/top/left..., transform, opacity, filter, clip-path,
      outline, text-shadow, z-index, mask);
    - a document ``<style>`` rule with such a property targets it (every simple selector token of the rule,
      tag, ``.class`` or ``#id``, occurs in the section; ``html``, ``body``, ``*`` and ``:root`` rules are
      deck-wide and ignored).

    Plain text, headings, lists, tables and ``style="color;text-align;display:grid;gap;grid-*"`` stay
    structural, so they remain editable SlideMark elements and cost the same tokens as Markdown.
    """
    if forced or node.attrs.get("data-render", "").lower() == "html":
        return True
    nodes = list(_subtree_nodes(node))
    if any(n.tag == "svg" for n in nodes):
        return True
    if any(_has_visual(n.attrs.get("style", "")) for n in nodes):
        return True
    present: set[str] = set()
    _subtree_tokens(node, present)
    for sel, decls in styles:
        if not _has_visual(decls):
            continue
        for part in sel.split(","):
            toks = [t.lower() for t in CSS_TOKEN.findall(re.sub(r"\[[^\]]*\]|:[\w-]+(\([^)]*\))?", "", part))]
            toks = [t for t in toks if t not in ("html", "body")]
            if toks and all(t in present for t in toks):
                return True
    return False


def outer_html(node: Node, text: str) -> str:
    if node.start is not None and node.end is not None and node.end > node.start:
        return text[node.start : node.end]
    return to_html(node)


def _html_slide(node: Node, text: str, style_blocks: list[str], line_of: int | None) -> Slide:
    title = next((n for n in _subtree_nodes(node) if n.tag in ("h1", "h2")), None)
    slide = Slide(line=line_of, layout="blank")
    if title is not None and raw_text(title).strip():
        slide.title = Text(
            role="title", paragraphs=[Paragraph(runs=[Run(text=WS.sub(" ", raw_text(title)).strip())])]
        )
    slide.id = node.attrs.get("id") or None
    slide.html = "".join(style_blocks) + outer_html(node, text)
    return slide


def parse_html(text: str) -> Deck:
    """Parse a whole HTML file into a Deck. Never raises: problems go to ``deck.diagnostics``."""
    deck = Deck()
    try:
        _parse_html(text, deck)
    except Exception as e:
        from ..ir import Diagnostic

        deck.diagnostics.append(
            Diagnostic(
                level="error",
                message=f"internal error: {type(e).__name__}: {e}",
                rule="internal",
                hint="simplify the HTML or report it as a parser bug",
            )
        )
    return deck


def _parse_html(text: str, deck: Deck) -> None:
    ctx = Ctx(deck.diagnostics)
    text = text.lstrip("\ufeff")
    root = build_tree(text)
    html = find_all(root, lambda n: n.tag == "html")
    if html and html[0].attrs.get("lang"):
        deck.lang = html[0].attrs["lang"].split("-")[0][:8] or None
    title = find_all(root, lambda n: n.tag == "title")
    if title and raw_text(title[0]).strip():
        deck.title = WS.sub(" ", raw_text(title[0])).strip()
    slides = (
        find_all(root, lambda n: n.tag == "section" and _is_slide(n))
        or find_all(root, _is_slide)
        or find_all(root, lambda n: n.tag == "section")
    )
    if not slides:
        body = find_all(root, lambda n: n.tag == "body")
        slides = [body[0] if body else root]
    style_blocks = STYLE_BLOCK.findall(text)
    rules = [
        (sel.strip(), decls)
        for blk in style_blocks
        for sel, decls in CSS_RULE.findall(
            re.sub(r"/\*.*?\*/", "", re.sub(r"</?style[^>]*>", "", blk), flags=re.S)
        )
    ]
    forced = bool(html and html[0].attrs.get("data-slidemark", "").lower() == "native")
    for i, node in enumerate(slides):
        ctx.slide = i + 1
        try:
            if node.tag == "section" and needs_html(node, rules, forced):
                deck.slides.append(_html_slide(node, text, style_blocks, node.line or None))
                continue
            deck.slides.append(_slide(node, ctx, i))
        except Exception as e:
            ctx.error(
                f"internal error: {type(e).__name__}: {e}",
                node.line or None,
                "internal",
                "simplify this slide or report the input as a parser bug",
            )
            deck.slides.append(Slide(line=node.line or None))
    ctx.slide = None
    if not any(s.title or s.elements or s.html for s in deck.slides):
        ctx.warn(
            "no slides found", None, "no-slides", 'wrap each slide in <section class="slide"> with an <h1>'
        )
    if deck.title is None and deck.slides and deck.slides[0].title and deck.slides[0].title.paragraphs:
        deck.title = deck.slides[0].title.paragraphs[0].plain


def html_blocks(text: str, ctx: Ctx, line: int | None) -> list[Any] | None:
    """Blocks for the body of a ```html fence, or ``None`` (with an ``html-fallback`` diagnostic)."""
    local: list[Any] = []
    try:
        root = build_tree(text)
        conv = _Conv(Ctx(local), base_line=line or 0, slide_grid=False)
        conv.ctx.slide = ctx.slide
        sink = _Sink()
        conv.walk(root.children, sink)
        conv.flush(sink)
        ok = (
            sink.elements
            and not (conv.title or conv.lead or conv.conclusion or conv.footnotes or conv.arrows)
            and not find_all(root, lambda n: n.tag == "section" and _is_slide(n))
            and any(not isinstance(e, Raw) for e in sink.elements)
        )
    except Exception:
        ok = False
    if not ok:
        ctx.add(
            "info",
            "```html fence is not understood",
            line,
            "html-fallback",
            HINT,
        )
        return None
    ctx.diagnostics.extend(local)
    return sink.elements

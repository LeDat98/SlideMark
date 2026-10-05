"""Markdown block tokens -> IR elements (text, lists, quotes, images, tables, charts, code, raw)."""

from __future__ import annotations

import csv
import io
import re
from typing import Any
from urllib.parse import unquote

from markdown_it.token import Token

from ..ir import Cell, Chart, Code, Image, Paragraph, Raw, Run, Series, Style, Table, Text
from .attrs import Attrs, apply_attrs, parse_attr_body
from .ctx import Ctx, closest
from .inline import MD, ImageRef, inline_items, inline_runs

CHART_KINDS = (
    "bar",
    "column",
    "stacked-bar",
    "stacked-column",
    "line",
    "area",
    "pie",
    "doughnut",
    "scatter",
    "radar",
)
RAW_KINDS = ("mermaid", "math", "html")
CALLOUT_RE = re.compile(r"^\[!(\w+)\]\s*")
CALLOUT_KINDS = {
    "note": "note",
    "tip": "tip",
    "warn": "warn",
    "warning": "warn",
    "caution": "caution",
    "important": "note",
}
MARP_SIZE = re.compile(r"^(w|h|width|height):(\d+(?:\.\d+)?(?:px|pt|cm|mm|in|%)?)$", re.I)


def _close_index(tokens: list[Token], i: int) -> int:
    """Index of the token closing the opening token at ``i`` (same level, nesting -1)."""
    lvl = tokens[i].level
    for j in range(i + 1, len(tokens)):
        if tokens[j].level == lvl and tokens[j].nesting == -1:
            return j
    return len(tokens) - 1


def paragraphs_from_tokens(tokens: list[Token]) -> list[Paragraph]:
    """Paragraphs (with list markers/levels) from a flat token slice."""
    out: list[Paragraph] = []
    stack: list[str] = []
    first_in_item = False
    in_heading = False
    for tok in tokens:
        ty = tok.type
        if ty == "heading_open":
            in_heading = True
        elif ty == "heading_close":
            in_heading = False
        elif ty == "bullet_list_open":
            stack.append("bullet")
        elif ty == "ordered_list_open":
            stack.append("number")
        elif ty in ("bullet_list_close", "ordered_list_close"):
            if stack:
                stack.pop()
        elif ty == "list_item_open":
            first_in_item = True
        elif ty == "inline":
            runs = [r for r in inline_items(tok.children) if isinstance(r, Run)]
            if in_heading:
                for r in runs:
                    r.bold = True
            marker = stack[-1] if stack and first_in_item else None
            out.append(Paragraph(runs=runs, marker=marker, level=max(len(stack) - 1, 0)))  # type: ignore[arg-type]
            first_in_item = False
        elif ty == "fence":
            out.append(Paragraph(runs=[Run(text=tok.content.rstrip("\n"), code=True)]))
    return out


def _num(s: str) -> float | None:
    s = s.strip().replace(",", "").replace("%", "").replace(" ", "")
    if not s:
        return None
    try:
        v = float(s)
    except ValueError:
        return None
    return v if v == v and abs(v) != float("inf") else None


def _csv_rows(body: str) -> list[list[str]]:
    try:
        rows = list(csv.reader(io.StringIO(body)))
    except csv.Error:
        rows = [line.split(",") for line in body.split("\n")]
    return [[c.strip() for c in r] for r in rows if any(c.strip() for c in r)]


def _cell(text: str) -> Cell:
    return Cell(paragraphs=[Paragraph(runs=inline_runs(text))] if text else [])


def _plain(cell: Cell) -> str:
    return "".join(p.plain for p in cell.paragraphs).strip()


def apply_merges(grid: list[list[Cell]], ctx: Ctx, line: int | None) -> None:
    """`<` merges a cell into its left neighbour, `^` into the one above (rectangular grid kept)."""
    anchor: dict[tuple[int, int], tuple[int, int]] = {}
    for r, row in enumerate(grid):
        for c, cell in enumerate(row):
            txt = _plain(cell)
            if txt == "<":
                if c == 0:
                    ctx.warn("'<' in the first column", line, "table-merge", "'<' merges into the left cell")
                    continue
                ar, ac = anchor.get((r, c - 1), (r, c - 1))
                if ar != r:
                    ctx.warn("'<' next to a row-merged cell", line, "table-merge", "avoid mixing < and ^")
                    continue
                anchor[(r, c)] = (ar, ac)
                grid[ar][ac].colspan = c - ac + 1
                row[c] = Cell()
            elif txt == "^":
                if r == 0:
                    ctx.warn("'^' in the first row", line, "table-merge", "'^' merges into the cell above")
                    continue
                ar, ac = anchor.get((r - 1, c), (r - 1, c))
                if ac != c:
                    ctx.warn("'^' under a column-merged cell", line, "table-merge", "avoid mixing < and ^")
                    continue
                anchor[(r, c)] = (ar, ac)
                grid[ar][ac].rowspan = r - ar + 1
                row[c] = Cell()


def build_table_gfm(tokens: list[Token], ctx: Ctx, line: int) -> Table:
    grid: list[list[Cell]] = []
    header_rows = 0
    row: list[Cell] | None = None
    in_head = False
    for i, tok in enumerate(tokens):
        ty = tok.type
        if ty == "thead_open":
            in_head = True
        elif ty == "thead_close":
            in_head = False
        elif ty == "tr_open":
            row = []
            if in_head:
                header_rows += 1
        elif ty == "tr_close":
            if row is not None:
                grid.append(row)
            row = None
        elif ty in ("th_open", "td_open") and row is not None:
            style = None
            st = tok.attrGet("style")
            if isinstance(st, str) and "text-align:" in st:
                al = st.split("text-align:")[1].strip(" ;")
                if al in ("left", "center", "right"):
                    style = Style(align=al)  # type: ignore[arg-type]
            inl = tokens[i + 1] if i + 1 < len(tokens) else None
            cell = Cell(style=style)
            if inl is not None and inl.type == "inline":
                runs = [r for r in inline_items(inl.children) if isinstance(r, Run)]
                if runs:
                    cell.paragraphs = [Paragraph(runs=runs)]
            row.append(cell)
    apply_merges(grid, ctx, line)
    return Table(rows=grid, header_rows=header_rows or 1, line=line)


def build_table_csv(body: str, ctx: Ctx, line: int) -> Table:
    rows = _csv_rows(body)
    if not rows:
        ctx.error("empty table", line, "empty-table", "put CSV rows inside the table fence")
        return Table(rows=[], line=line)
    width = max(len(r) for r in rows)
    if any(len(r) != width for r in rows):
        ctx.warn("rows have different cell counts", line, "table-ragged", "pad short rows with empty cells")
    grid = [[_cell(c) for c in r + [""] * (width - len(r))] for r in rows]
    apply_merges(grid, ctx, line)
    return Table(rows=grid, header_rows=1, line=line)


def build_chart(kind: str, body: str, ctx: Ctx, line: int) -> Chart:
    rows = _csv_rows(body)
    chart = Chart(kind=kind, line=line)  # type: ignore[arg-type]
    if not rows:
        ctx.error("chart has no data", line, "empty-chart", "add a header row and one row per series")
        return chart
    chart.categories = rows[0][1:]
    n = len(chart.categories)
    if len(rows) < 2:
        ctx.error("chart has no series", line, "empty-chart", "add one row per series after the header")
    for r in rows[1:]:
        vals: list[float | None] = []
        for c in r[1:]:
            v = _num(c)
            if v is None and c.strip():
                ctx.warn(
                    f"'{c}' in series '{r[0]}' is not a number", line, "chart-value", "use plain numbers"
                )
            vals.append(v)
        if len(vals) != n:
            ctx.warn(
                f"series '{r[0]}' has {len(vals)} values for {n} categories",
                line,
                "chart-ragged",
                "give every series one value per category (leave blanks empty)",
            )
            vals = (vals + [None] * n)[:n]
        chart.series.append(Series(name=r[0], values=vals))
    return chart


def _fence_attrs(rest: str) -> Attrs | None:
    rest = rest.strip()
    if not rest:
        return None
    if rest.startswith("{") and rest.endswith("}"):
        rest = rest[1:-1]
    return parse_attr_body(rest)


def build_fence(tok: Token, line: int, ctx: Ctx) -> Any:
    info = (tok.info or "").strip()
    parts = info.split(None, 1)
    lang = parts[0].lower() if parts else ""
    # `column{title=x}` without a space
    if "{" in lang:
        head, brace = lang.split("{", 1)
        lang, parts = head, [head, "{" + brace + (parts[1] if len(parts) > 1 else "")]
    rest = parts[1] if len(parts) > 1 else ""
    attrs = _fence_attrs(rest)
    if rest.strip() and attrs is None:
        ctx.warn(
            f"cannot read fence attributes '{rest.strip()}'",
            line,
            "bad-attr",
            'write them as {title="Sales" legend=bottom}',
        )
    body = tok.content.rstrip("\n")
    el: Any
    if lang in CHART_KINDS:
        el = build_chart(lang, body, ctx, line)
        if attrs:
            kv = dict(attrs.kv)
            if "title" in kv:
                el.title = kv.pop("title")
            apply_attrs(el, Attrs(attrs.classes, attrs.id, kv), ctx, line, sink=el.options)
        return el
    if lang == "table":
        el = build_table_csv(body, ctx, line)
    elif lang in RAW_KINDS:
        el = Raw(kind=lang, source=body, line=line)
    else:
        el = Code(lang=lang or None, text=body, line=line)
    if attrs:
        apply_attrs(el, attrs, ctx, line)
    return el


def _local_src(src: str) -> str:
    if src.startswith(("http://", "https://", "data:")):
        return src
    return unquote(src)


class _Builder:
    def __init__(self, first_line: int, ctx: Ctx, pending: Attrs | None):
        self.first_line = first_line
        self.ctx = ctx
        self.pending = pending
        self.out: list[Any] = []
        self.cur: Text | None = None

    def take(self, el: Any, line: int) -> Any:
        el.line = line
        if self.pending is not None:
            apply_attrs(el, self.pending, self.ctx, line)
            self.pending = None
        return el

    def flush(self) -> None:
        if self.cur is not None and self.cur.paragraphs:
            self.out.append(self.cur)
        self.cur = None

    def add_paragraph(self, p: Paragraph, line: int) -> None:
        if self.cur is None:
            self.cur = self.take(Text(role="body"), line)
        self.cur.paragraphs.append(p)

    def paragraph(self, tokens: list[Token], i: int, line: int) -> None:
        inline = tokens[i + 1]
        runs: list[Run] = []
        for item in inline_items(inline.children, allow_images=True):
            if isinstance(item, Run):
                runs.append(item)
                continue
            if any(r.text.strip() for r in runs):
                self.add_paragraph(Paragraph(runs=runs), line)
            runs = []
            self.add_image(item, line)
        if any(r.text.strip() for r in runs):
            self.add_paragraph(Paragraph(runs=runs), line)

    def marp_image(self, ref: ImageRef) -> tuple[str, Attrs | None]:
        """Marp sizing in the alt text (``![w:200 h:100 text](a.png)``) -> ``{w=200 h=100}``. Pure."""
        words = ref.alt.split()
        kept = [w for w in words if not MARP_SIZE.match(w) and w != "bg"]
        if len(kept) == len(words):
            return ref.alt, ref.attrs
        attrs = Attrs(list(ref.attrs.classes), ref.attrs.id, dict(ref.attrs.kv)) if ref.attrs else Attrs()
        for w in words:
            m = MARP_SIZE.match(w)
            if m:
                attrs.kv.setdefault("w" if m.group(1).lower().startswith("w") else "h", m.group(2))
        return " ".join(kept), attrs

    def add_image(self, ref: ImageRef, line: int) -> None:
        alt, attrs = self.marp_image(ref)
        if alt != ref.alt:
            self.ctx.warn(
                f"Marp image options in alt text '{ref.alt}'",
                line,
                "marp-syntax",
                "write ![alt](a.png){w=200}; a bare number is pt",
            )
        if not alt.strip():
            self.ctx.warn(
                "image has no alt text",
                line,
                "image-alt",
                "write ![what the image shows](path); alt text is used for accessibility",
            )
        ref.attrs = attrs
        el = Image(src=_local_src(ref.src), alt=alt)
        self.flush()
        self.take(el, line)
        if ref.attrs is not None:
            apply_attrs(el, ref.attrs, self.ctx, line)
        self.out.append(el)

    def callout_kind(self, inner: list[Token], line: int) -> str | None:
        """Detect a leading ``[!kind]`` in a quote, strip it from the first inline token, return the kind."""
        first = next((t for t in inner if t.type == "inline"), None)
        if first is None:
            return None
        m = CALLOUT_RE.match(first.content)
        if not m:
            return None
        word = m.group(1).lower()
        kind = CALLOUT_KINDS.get(word)
        if kind is None:
            near = closest(word, CALLOUT_KINDS)
            hint = f"did you mean '[!{near}]'? " if near else ""
            self.ctx.warn(
                f"unknown callout '[!{m.group(1)}]'",
                line,
                "unknown-callout",
                f"{hint}use [!note], [!tip], [!warn] or [!caution]; treated as note",
            )
            kind = "note"
        first.content = first.content[m.end() :]
        toks = MD.parseInline(first.content)
        first.children = toks[0].children if toks else []
        return kind

    def run(self, tokens: list[Token]) -> None:
        i = 0
        while i < len(tokens):
            tok = tokens[i]
            ty = tok.type
            line = self.first_line + (tok.map[0] if tok.map else 0)
            if tok.nesting == 1:
                end = _close_index(tokens, i)
            else:
                end = i
            inner = tokens[i + 1 : end]
            if ty == "paragraph_open":
                self.paragraph(tokens, i, line)
            elif ty in ("bullet_list_open", "ordered_list_open"):
                for p in paragraphs_from_tokens(tokens[i : end + 1]):
                    self.add_paragraph(p, line)
            elif ty == "heading_open":
                for p in paragraphs_from_tokens(tokens[i : end + 1]):
                    self.add_paragraph(p, line)
            elif ty == "blockquote_open":
                self.flush()
                kind = self.callout_kind(inner, line)
                q = self.take(Text(role="body" if kind else "quote"), line)
                if kind:
                    q.classes += [c for c in ("callout", kind) if c not in q.classes]
                q.paragraphs = paragraphs_from_tokens(inner)
                if kind:
                    q.paragraphs = [p for p in q.paragraphs if p.runs]
                self.out.append(q)
            elif ty == "fence":
                self.flush()
                el = build_fence(tok, line, self.ctx)
                self.take(el, line)
                self.out.append(el)
            elif ty == "table_open":
                self.flush()
                el = build_table_gfm(inner, self.ctx, line)
                self.take(el, line)
                self.out.append(el)
            i = end + 1
        self.flush()


def convert(
    lines: list[str], first_line: int, ctx: Ctx, pending: Attrs | None
) -> tuple[list[Any], Attrs | None]:
    """Convert a run of plain Markdown lines into elements. Returns (elements, unused pending attrs)."""
    text = "\n".join(lines)
    if not text.strip():
        return [], pending
    tokens = MD.parse(text)
    b = _Builder(first_line, ctx, pending)
    b.run(tokens)
    return b.out, b.pending

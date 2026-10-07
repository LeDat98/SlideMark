"""Parsed text, tables and charts -> SlideMark text (shortest form)."""

from __future__ import annotations

import re
from dataclasses import replace

from .read import CellT, ChartT, ParaT, RunT
from .runs import span_has, wrap_span

_ESC = re.compile(r"([\\`*\[\]~^])")
_UNDER = re.compile(r"(?<![A-Za-z0-9])_|_(?![A-Za-z0-9])")
_LT = re.compile(r"<(?=[A-Za-z/!?])")
_AMP = re.compile(r"&(?=#?\w+;)")
_LINE_START = re.compile(r"^(?:[-+]( |$)|#{1,6}( |$)|>|(\d+)([.)])( |$)|:::|\{|\||@|---|===|___)")


def esc(text: str) -> str:
    text = _ESC.sub(r"\\\1", text)
    text = _UNDER.sub(r"\\_", text)
    text = _LT.sub(r"\\<", text)
    text = _AMP.sub(r"\\&", text)
    return text.replace("==", "\\=\\=")


def esc_line_start(line: str) -> str:
    """Neutralize a paragraph's first characters that would start another block."""
    if line.startswith("※"):
        return "&#8251;" + line[1:]
    if line.startswith("???"):
        return "\\?\\?\\?" + line[3:]
    m = _LINE_START.match(line)
    if not m:
        return line
    if m.group(3):  # "1. " / "1) "
        return f"{m.group(3)}\\{m.group(4)}{line[m.end(4) :]}"
    return "\\" + line


def _fmt_key(r: RunT) -> tuple:
    return (r.bold, r.italic, r.strike, r.sup, r.sub, r.code, r.color, r.badge, r.link, r.span)


def _merge(runs: list[RunT]) -> list[RunT]:
    out: list[RunT] = []
    for r in runs:
        if r.text == "\n" or (out and out[-1].text == "\n"):
            out.append(r)
        elif out and _fmt_key(out[-1]) == _fmt_key(r):
            out[-1] = RunT(**{**out[-1].__dict__, "text": out[-1].text + r.text})
        else:
            out.append(RunT(**r.__dict__))
    return out


def _url(u: str) -> str:
    return u.replace(" ", "%20").replace("(", "%28").replace(")", "%29")


def inline(
    runs: list[RunT],
    *,
    accent: str | None = None,
    classes: dict[str, str] | None = None,
    plain_bold: bool = False,
    cell: bool = False,
    implied=None,
) -> str:
    """Runs -> inline Markdown. ``plain_bold`` drops bold that the theme adds anyway (titles, headings).

    ``implied`` (a Style: color, bold, italic) is what a css rule already gives this text: no markup for it.
    """
    imp_color = getattr(implied, "color", None)
    imp_bold = bool(getattr(implied, "bold", None))
    imp_italic = bool(getattr(implied, "italic", None))
    shades = (accent or "").split("|")
    runs = [  # a colour the markup cannot say must not split a run (`**a****b**`)
        replace(r, color=None)
        if r.color
        and not r.span
        and r.color != imp_color
        and r.color not in shades
        and (classes or {}).get(r.color) not in ("success", "danger")
        else r
        for r in runs
    ]
    parts: list[str] = []
    all_bold = bool(runs) and all(r.bold for r in runs if r.text.strip())
    for r in _merge(runs):
        if r.text == "\n":
            parts.append("<br>" if cell else "\\\n")
            continue
        text = r.text.replace("\r", "").replace("\v", "")
        if "\n" in text:
            text = text.replace("\n", "<br>" if cell else " ")
        if not text.strip():
            parts.append(text)
            continue
        lead = text[: len(text) - len(text.lstrip())]
        trail = text[len(text.rstrip()) :]
        core = text.strip()
        if r.code:
            n = max([len(m) for m in re.findall(r"`+", core)] + [0]) + 1
            body = "`" * n + (f" {core} " if core.startswith("`") or core.endswith("`") else core) + "`" * n
        else:
            body = esc(core)
            if cell:
                body = body.replace("|", "\\|")
            if r.sup and " " not in body:
                body = f"^{body}^"
            elif r.sub and " " not in body:
                body = f"~{body}~"
            if r.strike:
                body = f"~~{body}~~"
            if r.italic and not imp_italic:
                body = f"*{body}*"
            if (
                r.bold
                and not imp_bold
                and not (plain_bold and all_bold)
                and not r.badge
                and not span_has(r, "bold")
            ):
                body = f"**{body}**"
            if span_has(r, "color"):
                pass  # the span carries the colour
            elif imp_color and r.color == imp_color:
                pass
            elif accent and r.color in accent.split("|") and not r.badge:  # `A|B`: accent shades
                body = f"=={body}=="
            elif r.color and not r.badge and (cname := (classes or {}).get(r.color)) in ("success", "danger"):
                body = f"[{body}]{{.{cname}}}"
            body = wrap_span(body, r)  # runs.py: one `[text]{size=26 color=#E08A1E}` for both recognisers
        if r.badge:
            cls = _badge_class(r.badge, classes or {})
            body = f"[{body}]{{.badge{(' .' + cls) if cls else ''}}}"
        if r.link:
            body = f"[{body}]({_url(r.link)})"
        parts.append(lead + body + trail)
    return "".join(parts).strip()


# --------------------------------------------------------------------------- text blocks


def text_lines(paras: list[ParaT], *, accent=None, classes=None, plain_bold=False) -> list[str]:
    """Paragraphs -> Markdown lines (lists with two-space nesting, blank lines where Markdown needs them)."""
    out: list[str] = []
    stack: list[str] = []  # marker per level of the current list
    prev_list = False
    for p in paras:
        body = inline(p.runs, accent=accent, classes=classes, plain_bold=plain_bold)
        if not body:
            continue
        if p.marker:
            lvl = min(p.level, len(stack)) if prev_list else 0
            del stack[lvl:]
            stack.append(p.marker)
            indent = "".join(" " * (2 if m == "bullet" else 3) for m in stack[:-1])
            lead = "- " if p.marker == "bullet" else "1. "
            cont = indent + " " * len(lead)
            body = ("\n" + cont).join(body.split("\n"))
            out.append(indent + lead + esc_line_start(body))
            prev_list = True
        else:
            if out:
                out.append("")
            out.append(esc_line_start(body))
            stack.clear()
            prev_list = False
    return out


def one_line(paras: list[ParaT], **kw) -> str:
    return " ".join(inline(p.runs, **kw).replace("\\\n", " ").replace("\n", " ") for p in paras).strip()


# --------------------------------------------------------------------------- code

_LANGS = (
    "python",
    "javascript",
    "typescript",
    "json",
    "yaml",
    "bash",
    "sql",
    "java",
    "go",
    "rust",
    "c",
    "cpp",
    "csharp",
    "html",
    "xml",
    "css",
    "ruby",
    "php",
    "kotlin",
    "swift",
    "toml",
    "ini",
    "diff",
    "markdown",
)


def detect_lang(paras: list[ParaT]) -> str | None:
    """The fence language whose syntax highlighting reproduces the run colors of a code block (or None).

    The renderer colors tokens by pygments class; the language itself is not stored in the .pptx, so every
    candidate lexer is tried and the first whose token classes map one-to-one onto the observed colors wins.
    """
    try:
        from ..ir import Code
        from ..render.objects import code_paragraphs

        actual: list[tuple] = []
        for i, p in enumerate(paras):
            if i:
                actual.append(("\n",))
            for r in p.runs:
                actual += [(r.color, r.italic)] * len(r.text)
        if len({a for a in actual if len(a) == 2}) < 2:
            return None  # plain text: no highlighting to reproduce
        text = "\n".join("".join(r.text for r in p.runs) for p in paras)
        for lang in _LANGS:
            got: list[tuple] = []
            for i, p in enumerate(code_paragraphs(Code(lang=lang, text=text))):
                if i:
                    got.append(("\n",))
                for r in p.runs:
                    got += [(r.color or "fg", bool(r.italic))] * len(r.text)
            if len(got) != len(actual):
                continue
            pairs = {(g, a) for g, a in zip(got, actual, strict=True)}
            if len(pairs) == len({g for g, _ in pairs}) == len({a for _, a in pairs}):
                return lang
    except Exception:
        return None
    return None


# --------------------------------------------------------------------------- table


_NEAR = 48.0  # RGB distance within which a badge fill still counts as a class color (darkened for contrast)


def _badge_class(color: str, classes: dict[str, str]) -> str:
    """Class name of a badge fill: exact color, else the closest class color (badges use a legible shade)."""
    if color in classes:
        return classes[color]
    try:
        rgb = [int(color[i : i + 2], 16) for i in (0, 2, 4)]
        best = min(
            (
                (sum((a - int(k[i : i + 2], 16)) ** 2 for a, i in zip(rgb, (0, 2, 4), strict=True)) ** 0.5, v)
                for k, v in classes.items()
            ),
            default=(_NEAR + 1, ""),
        )
    except ValueError:
        return ""
    return best[1] if best[0] <= _NEAR else ""


def header_rows_of(rows: list[list[CellT]]) -> int:
    """Header rows of an imported table: 1, plus every bold row that continues a header cell (``^``)."""

    def bold_row(row: list[CellT]) -> bool:
        texts = [p for c in row if not (c.hmerge or c.vmerge) for p in c.paras if p.plain.strip()]
        return bool(texts) and all(p.all_bold for p in texts)

    n = 1
    while n < len(rows) - 1 and any(c.vmerge and not c.hmerge for c in rows[n]) and bold_row(rows[n]):
        n += 1
    return n


def hl_row_set(rows: list[list[CellT]], hl: str, header_rows: int = 1) -> set[int]:
    """Body rows whose first cell is one of the ``hl=`` values (the renderer drew them bold on a tint)."""
    from ..layout.tablehl import norm_key, split_names

    keys = {norm_key(n) for n in split_names(hl)}
    out: set[int] = set()
    for ri in range(header_rows, len(rows)):
        first = rows[ri][0] if rows[ri] else None
        if first is not None and norm_key("".join(p.plain for p in first.paras)) in keys:
            out.add(ri)
    return out


def table_lines(
    rows: list[list[CellT]],
    *,
    accent=None,
    classes=None,
    header_rows: int = 1,
    hl_rows: set[int] = frozenset(),
    hl_cols: set[int] = frozenset(),
) -> tuple[list[str], int]:
    """GFM table with ``<`` / ``^`` merge markers. Returns (lines, merged cells dropped).

    The first ``header_rows`` rows are header rows, and ``hl_rows`` the rows an ``hl=`` emphasises: their
    plain text is bold by default (no ``**``).
    """
    if not rows:
        return [], 0
    ncols = max(len(r) for r in rows)
    lost = 0
    out = []
    for ri, row in enumerate(rows):
        cells = []
        for ci, c in enumerate(row + [CellT()] * (ncols - len(row))):
            if c.hmerge and c.vmerge:
                lost += 1
                cells.append("")
            elif c.hmerge:
                cells.append("<")
            elif c.vmerge:
                cells.append("^")
            else:
                txt = inline(
                    [r for p in c.paras for r in (p.runs + [RunT(text="\n")])][:-1] if c.paras else [],
                    accent=accent,
                    classes=classes,
                    plain_bold=(ri < header_rows or ri in hl_rows or (ci in hl_cols and ri >= header_rows)),
                    cell=True,
                )
                cells.append(txt)
        out.append("|" + "".join(f" {c} |" if c.strip() else " |" for c in cells))
        if ri == 0:
            out.append("|" + "-|" * ncols)
    return out, lost


# --------------------------------------------------------------------------- chart


def _csv(cell: str) -> str:
    if any(ch in cell for ch in ',"\n'):
        return '"' + cell.replace('"', '""') + '"'
    return cell


def _val(v: float | None) -> str:
    if v is None:
        return ""
    if v == int(v) and abs(v) < 1e15:
        return str(int(v))
    return repr(v)


def _attr(key: str, val: str) -> str:
    if re.fullmatch(r"[\w.%#,:/+-]+", val):
        return f"{key}={val}"
    q = '"' if '"' not in val else "'"
    return f"{key}={q}{val.replace(q, '')}{q}"


def chart_lines(ch: ChartT) -> list[str]:
    attrs = []
    if ch.title:
        attrs.append(_attr("title", ch.title.replace("\n", " ")))
    for k in (
        "legend",
        "labels",
        "labels.bold",
        "totals",
        "fmt",
        "min",
        "max",
        "axis",
        "overlap",
        "step",
        "colors",
        "size",
        "gap",
        "hl",
        "note",
    ):
        if k in ch.options:
            attrs.append(_attr(k, ch.options[k]))
    head = f"```{ch.kind}" + (" {" + " ".join(attrs) + "}" if attrs else "")
    rows = ["," + ",".join(_csv(c) for c in ch.categories)]
    for name, vals in ch.series:
        marks = set(ch.totals)
        rows.append(",".join([_csv(name), *("=" if i in marks else _val(v) for i, v in enumerate(vals))]))
    return [head, *rows, "```"]

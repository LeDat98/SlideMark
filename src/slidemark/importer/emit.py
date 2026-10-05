"""Parsed text, tables and charts -> SlideMark text (shortest form)."""

from __future__ import annotations

import re

from .read import CellT, ChartT, ParaT, RunT

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
    return (r.bold, r.italic, r.strike, r.sup, r.sub, r.code, r.color, r.badge, r.link)


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
            if r.bold and not imp_bold and not (plain_bold and all_bold) and not r.badge:
                body = f"**{body}**"
            if imp_color and r.color == imp_color:
                pass
            elif accent and r.color == accent and not r.badge:
                body = f"=={body}=="
            elif r.color and not r.badge and (cname := (classes or {}).get(r.color)) in ("success", "danger"):
                body = f"[{body}]{{.{cname}}}"
        if r.badge:
            cls = (classes or {}).get(r.badge, "")
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


def table_lines(rows: list[list[CellT]], *, accent=None, classes=None) -> tuple[list[str], int]:
    """GFM table with ``<`` / ``^`` merge markers. Returns (lines, merged cells dropped)."""
    if not rows:
        return [], 0
    ncols = max(len(r) for r in rows)
    lost = 0
    out = []
    for ri, row in enumerate(rows):
        cells = []
        for c in row + [CellT()] * (ncols - len(row)):
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
                    plain_bold=(ri == 0),
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
    for k in ("legend", "labels", "fmt", "min", "max", "axis"):
        if k in ch.options:
            attrs.append(_attr(k, ch.options[k]))
    head = f"```{ch.kind}" + (" {" + " ".join(attrs) + "}" if attrs else "")
    rows = ["," + ",".join(_csv(c) for c in ch.categories)]
    for name, vals in ch.series:
        rows.append(",".join([_csv(name), *(_val(v) for v in vals)]))
    return [head, *rows, "```"]

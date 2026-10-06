"""CSV reading, number normalisation and chart/table option validation (never raises)."""

from __future__ import annotations

import csv
import io
import re
import unicodedata

from ..ir import Chart, Style, Table
from .ctx import Ctx, closest

LEGEND = ("bottom", "right", "top", "left", "none")
CHART_KEYS = ("title", "legend", "labels", "fmt", "min", "max", "colors", "axis", "hl", "note")
THEME_COLORS = (
    "bg",
    "fg",
    "primary",
    "secondary",
    "accent",
    "muted",
    "border",
    "surface",
    "danger",
    "success",
)
_HEX = re.compile(r"^#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6})$")
_TRUE = ("on", "true", "yes", "1")
_FALSE = ("off", "false", "no", "0")
_BOM = chr(0xFEFF)
_QUOTED = re.compile(r'"[^"]*"')
_AMAP = {"l": "left", "c": "center", "r": "right"}


# --------------------------------------------------------------------------- CSV


def read_csv(body: str, decimal_comma: bool = False) -> list[list[str]]:
    """Rows of stripped cells: BOM, quotes, `;`/tab separators (when no comma), blank lines.

    With ``decimal_comma`` (chart data in a decimal-comma language) a body whose every line holds a
    ``;`` is split on ``;`` even when commas are present, so ``Q1;1,6;2,4`` keeps its decimals.
    """
    body = body.replace(_BOM, "").replace("\x00", "")
    probe = _QUOTED.sub("", body)
    delim = ","
    lines = [ln for ln in probe.split("\n") if ln.strip()]
    if decimal_comma and lines and all(";" in ln for ln in lines):
        delim = ";"
    elif "," not in probe:
        if "\t" in probe:
            delim = "\t"
        elif ";" in probe:
            delim = ";"
    try:
        rows = list(csv.reader(io.StringIO(body), delimiter=delim, skipinitialspace=True))
    except csv.Error:
        rows = [line.split(delim) for line in body.split("\n")]
    return [[c.strip() for c in r] for r in rows if any(c.strip() for c in r)]


_MINUS = "▲△▼−–‐ー"  # JP "▲3" = -3; U+2212 and dashes as minus

# Languages that write 1,6 for 1.6 (and 1.900 for 1900).
DECIMAL_COMMA_LANGS = frozenset(
    "vi de fr es it pt id ru nl pl tr cs sv da nb nn no fi uk ro hu el bg sk sl hr sr lt lv et".split()
)
_DEC_A = re.compile(r"\d{1,3}(?:\.\d{3})*,\d+")
_DEC_B = re.compile(r"\d{1,3}(?:\.\d{3})+")


def is_decimal_comma_lang(lang: str | None) -> bool:
    if not lang:
        return False
    return re.split(r"[-_]", lang.strip().lower())[0] in DECIMAL_COMMA_LANGS


def _locale_decimal(num: str) -> str:
    """``1,6`` -> ``1.6``, ``1.900`` -> ``1900``, ``1.234,5`` -> ``1234.5``; ``1,240`` stays (thousands)."""
    if re.fullmatch(r"\d{1,3},\d{3}", num):  # ambiguous: keep the thousands reading
        return num
    if _DEC_A.fullmatch(num) or re.fullmatch(r"\d+,\d{1,2}", num):
        return num.replace(".", "").replace(",", ".")
    if _DEC_B.fullmatch(num):
        return num.replace(".", "")
    return num


def parse_number(raw: str, decimal_comma: bool = False) -> tuple[float | None, bool, bool]:
    """Return (value, is_percent, is_bad). An empty cell is (None, False, False)."""
    s = unicodedata.normalize("NFKC", raw).strip()
    if not s:
        return None, False, False
    neg = False
    if s[0] in _MINUS:
        neg, s = True, s[1:]
    s = s.replace(" ", "")
    if decimal_comma:
        m = re.fullmatch(r"(\(?[-+]?)([\d.,]+)(%?\)?)", s)
        if m:
            s = m.group(1) + _locale_decimal(m.group(2)) + m.group(3)
    s = s.replace(",", "")
    pct = s.endswith("%")
    if pct:
        s = s[:-1]
    if s.startswith("(") and s.endswith(")"):  # accounting negative
        neg, s = True, s[1:-1]
    try:
        v = float(s)
    except ValueError:
        return None, False, True
    if v != v or abs(v) == float("inf"):
        return None, False, True
    return (-v if neg else v), pct, False


def numbers_row(
    cells: list[str], name: str, ctx: Ctx, line: int | None, pct: list[bool]
) -> list[float | None]:
    """Parse one series; ``pct`` collects, for every non-empty value, whether it carried a ``%``."""
    out: list[float | None] = []
    for c in cells:
        v, is_pct, bad = parse_number(c, is_decimal_comma_lang(ctx.lang))
        if bad:
            ctx.warn(
                f"'{c}' in series '{name}' is not a number",
                line,
                "bad-number",
                "use plain numbers (1,240 / 12% / ▲3 are fine); the cell was left blank",
            )
        elif v is not None:
            pct.append(is_pct)
        out.append(v)
    return out


# --------------------------------------------------------------------------- chart options


def _bad(ctx: Ctx, key: str, value: str, valid: str, line: int | None) -> None:
    ctx.warn(f"bad chart option {key}='{value}'", line, "bad-chart-option", f"{key} is one of: {valid}")


_HL_KINDS = ("bar", "column", "stacked-bar", "stacked-column", "line", "pie", "doughnut", "waterfall")


def _apply_hl(ch: Chart, value: str, ctx: Ctx, line: int | None) -> None:
    """``hl=a,b``: emphasised categories. Unknown names warn (listing the valid ones) and are dropped."""
    names = [p.strip() for p in re.split(r"[,;]", value) if p.strip()]
    if not names:
        _bad(ctx, "hl", value, "a comma list of category names", line)
        return
    if ch.kind not in _HL_KINDS:
        ctx.warn(
            f"hl is not drawn on {ch.kind} charts",
            line,
            "chart-hl",
            "hl works on bar, column, stacked-*, line, pie, doughnut and waterfall charts",
        )
        return
    cats = [str(c).strip() for c in ch.categories]
    if ch.kind in ("pie", "doughnut") and len(ch.series) > 1 and len(cats) <= 1:
        cats = [s.name.strip() for s in ch.series]  # one slice per CSV row
    folded = [c.casefold() for c in cats]
    good: list[str] = []
    for n in names:
        i = cats.index(n) if n in cats else folded.index(n.casefold()) if n.casefold() in folded else -1
        if i < 0:
            ctx.warn(
                f"hl category '{n}' is not in the chart",
                line,
                "chart-hl",
                "categories are: " + ", ".join(cats[:12]) + (" ..." if len(cats) > 12 else ""),
            )
        elif cats[i] not in good:
            good.append(cats[i])
    if good:
        ch.options["hl"] = good


def apply_chart_kv(ch: Chart, kv: dict[str, str], ctx: Ctx, line: int | None) -> dict[str, str]:
    """Consume chart option keys from ``kv`` into ``ch``; returns the keys left for the generic path."""
    from .attrs import VALID_KEYS

    rest: dict[str, str] = {}
    o = ch.options
    for k, v in kv.items():
        low = v.strip().lower()
        if k == "title":
            ch.title = v
        elif k == "legend":
            if low in LEGEND:
                o["legend"] = low
            else:
                _bad(ctx, k, v, "/".join(LEGEND), line)
        elif k == "labels":
            if low in _TRUE:
                o["labels"] = "on"
            elif low in _FALSE:
                o["labels"] = "off"
            elif low == "percent":
                o["labels"] = "percent"
            else:
                _bad(ctx, k, v, "on/off/percent", line)
        elif k == "axis":
            if low in _TRUE:
                o["axis"] = "on"
            elif low in _FALSE:
                o["axis"] = "off"
            else:
                _bad(ctx, k, v, "on/off", line)
        elif k == "fmt":
            if v.strip():
                o["fmt"] = v
            else:
                _bad(ctx, k, v, 'an Excel number format such as "0.0", "#,##0" or "0%"', line)
        elif k in ("min", "max"):
            num, _, bad = parse_number(v)
            if bad or num is None:
                _bad(ctx, k, v, "a number", line)
            else:
                o[k] = num
        elif k == "colors":
            parts = [p.strip() for p in re.split(r"[,;]", v) if p.strip()]
            if parts and all(p in THEME_COLORS or _HEX.match(p) for p in parts):
                o["colors"] = parts
            else:
                ctx.warn(
                    f"bad chart colors '{v}'",
                    line,
                    "bad-chart-option",
                    "colors is a comma list of #hex or theme names: " + "/".join(THEME_COLORS),
                )
        elif k == "hl":
            _apply_hl(ch, v, ctx, line)
        elif k == "note":
            text = " ".join(v.split())
            if text:
                o["note"] = text
            else:
                _bad(ctx, k, v, "a one-line takeaway text", line)
        else:
            rest[k] = v
            if k not in VALID_KEYS:
                near = closest(k, CHART_KEYS, 0.6)
                hint = f"did you mean '{near}='?" if near else "valid keys: " + ", ".join(CHART_KEYS)
                ctx.warn(f"unknown chart option '{k}'", line, "bad-chart-option", hint)
    return rest


# --------------------------------------------------------------------------- table attributes


def _apply_table_hl(t: Table, value: str, ctx: Ctx, line: int | None) -> None:
    """``hl=a,b``: body rows whose first cell equals a name are emphasised; unknown names warn."""
    from ..layout.tablehl import first_cells, norm_key, split_names

    firsts = first_cells(t)
    cells = list(dict.fromkeys(text for _r, text in firsts if text))
    by_key = {norm_key(c): c for c in cells}
    whole = norm_key(value.strip().strip("\"'"))
    names = [value.strip().strip("\"'")] if whole in by_key else split_names(value)
    if not names:
        ctx.warn(
            f"bad table option hl='{value}'",
            line,
            "table-hl",
            "hl is the first-cell values of the rows to emphasise, e.g. hl=Metro,East",
        )
        return
    good: list[str] = []
    for n in names:
        hit = by_key.get(norm_key(n))
        if hit is None:
            near = closest(norm_key(n), list(by_key), 0.5)
            hint = (
                f"did you mean '{by_key[near]}'?"
                if near
                else "first cells are: " + ", ".join(cells[:8]) + (" ..." if len(cells) > 8 else "")
            )
            ctx.warn(f"hl row '{n}' is not a first-cell value of the table", line, "table-hl", hint)
        elif hit not in good:
            good.append(hit)
    if good:
        t.attrs["hl"] = good


def apply_table_kv(t: Table, kv: dict[str, str], ctx: Ctx, line: int | None) -> dict[str, str]:
    """Consume widths/align/header/hcol/hl from ``kv``; returns the remaining keys."""
    rest: dict[str, str] = {}
    n = max((len(r) for r in t.rows), default=0)
    hl = kv.get("hl")  # last: header= decides which rows are body rows
    for k, v in kv.items():
        if k == "hl":
            continue
        if k == "widths":
            try:
                w = [float(x) for x in re.split(r"[:,]", v.strip()) if x.strip()]
            except ValueError:
                w = []
            if not w or any(x <= 0 or x != x or x == float("inf") for x in w):
                ctx.warn(
                    f"bad widths '{v}'",
                    line,
                    "bad-table-option",
                    "widths are positive ratios, e.g. widths=3:1:1",
                )
                continue
            if n and len(w) != n:
                ctx.warn(
                    f"widths has {len(w)} values for {n} columns",
                    line,
                    "bad-table-option",
                    f"give exactly {n} ratios, e.g. widths={':'.join(['1'] * n)}",
                )
                mean = sum(w) / len(w)
                w = (w + [mean] * n)[:n]
            t.col_widths = w  # type: ignore[assignment]
        elif k == "align":
            letters = v.strip().lower()
            if not letters or any(ch not in _AMAP for ch in letters):
                ctx.warn(
                    f"bad align '{v}'",
                    line,
                    "bad-table-option",
                    "align is one letter per column from l/c/r, e.g. align=lcrr",
                )
                continue
            if n and len(letters) != n:
                ctx.warn(
                    f"align has {len(letters)} letters for {n} columns",
                    line,
                    "bad-table-option",
                    f"give exactly {n} letters, e.g. align={'l' + 'r' * max(n - 1, 0)}",
                )
            for row in t.rows:
                for ci, cell in enumerate(row[: len(letters)]):
                    cell.style = (cell.style or Style()).merged(Style(align=_AMAP[letters[ci]]))  # type: ignore[arg-type]
        elif k in ("header", "hcol"):
            try:
                num = int(v.strip())
                if num < 0:
                    raise ValueError
            except ValueError:
                ctx.warn(
                    f"bad {k} '{v}'", line, "bad-table-option", f"{k} is a whole number >= 0, e.g. {k}=1"
                )
                continue
            limit = len(t.rows) if k == "header" else n
            if t.rows and num > limit:
                ctx.warn(
                    f"{k}={num} exceeds the table size {limit}",
                    line,
                    "bad-table-option",
                    f"use {k}={limit} or less",
                )
                num = limit
            if k == "header":
                t.header_rows = num
            else:
                t.header_cols = num
        else:
            rest[k] = v
    if hl is not None:
        _apply_table_hl(t, hl, ctx, line)
    return rest

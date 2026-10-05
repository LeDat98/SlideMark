"""``css`` fences: a small CSS subset parsed into ``CssRule`` objects (selector + ``Style``).

Never raises: every unsupported selector, property or value becomes a ``css-*`` warning with a source line.
Layout does the selector matching; this module only produces correct IR.
"""

from __future__ import annotations

import re
from typing import Any

from ..ir import CssRule, Deck, Style
from .ctx import Ctx, closest

# --------------------------------------------------------------------------- constants

NAMED_COLORS = {
    "black": "#000000",
    "silver": "#C0C0C0",
    "gray": "#808080",
    "grey": "#808080",
    "white": "#FFFFFF",
    "maroon": "#800000",
    "red": "#FF0000",
    "purple": "#800080",
    "fuchsia": "#FF00FF",
    "magenta": "#FF00FF",
    "green": "#008000",
    "lime": "#00FF00",
    "olive": "#808000",
    "yellow": "#FFFF00",
    "navy": "#000080",
    "blue": "#0000FF",
    "teal": "#008080",
    "aqua": "#00FFFF",
    "cyan": "#00FFFF",
    "orange": "#FFA500",
    "pink": "#FFC0CB",
    "brown": "#A52A2A",
    "gold": "#FFD700",
    "indigo": "#4B0082",
    "violet": "#EE82EE",
    "crimson": "#DC143C",
    "coral": "#FF7F50",
    "salmon": "#FA8072",
    "tomato": "#FF6347",
    "turquoise": "#40E0D0",
    "skyblue": "#87CEEB",
    "royalblue": "#4169E1",
    "steelblue": "#4682B4",
    "darkblue": "#00008B",
    "darkgreen": "#006400",
    "darkred": "#8B0000",
    "darkgray": "#A9A9A9",
    "darkgrey": "#A9A9A9",
    "lightgray": "#D3D3D3",
    "lightgrey": "#D3D3D3",
    "lightblue": "#ADD8E6",
    "lightgreen": "#90EE90",
    "lightyellow": "#FFFFE0",
    "dimgray": "#696969",
    "dimgrey": "#696969",
    "whitesmoke": "#F5F5F5",
    "ivory": "#FFFFF0",
    "beige": "#F5F5DC",
    "khaki": "#F0E68C",
    "lavender": "#E6E6FA",
    "plum": "#DDA0DD",
    "orchid": "#DA70D6",
    "chocolate": "#D2691E",
    "tan": "#D2B48C",
    "slategray": "#708090",
    "slategrey": "#708090",
    "forestgreen": "#228B22",
    "seagreen": "#2E8B57",
    "limegreen": "#32CD32",
    "darkorange": "#FF8C00",
    "hotpink": "#FF69B4",
    "deeppink": "#FF1493",
    "midnightblue": "#191970",
    "dodgerblue": "#1E90FF",
    "transparent": "#00000000",
}

SELECTOR_TYPES = ("slide", "h1", "h2", "p", "li", "table", "tr", "th", "td", "code", "img")
_COMPOUND_PART = re.compile(
    r"(?:\.[A-Za-z_][\w-]*|#[A-Za-z_][\w-]*|:nth-child\((?:even|odd|\d+)\)|:first-child|:last-child)"
)
_TYPE_RE = re.compile(r"[A-Za-z][A-Za-z0-9]*")
_LEN_RE = re.compile(r"^([+-]?(?:\d+\.?\d*|\.\d+))(px|pt|em|rem|in|cm|mm)?$", re.I)
_NUM_RE = re.compile(r"^[+-]?(?:\d+\.?\d*|\.\d+)$")
_PX = 0.75  # pt per px
_UNIT_PT = {"px": _PX, "pt": 1.0, "in": 72.0, "cm": 72.0 / 2.54, "mm": 72.0 / 25.4}
_DEFAULT_FS = 16 * _PX  # pt, the em base when no font-size is known in the rule
_BORDER_WIDTHS = {"thin": 1 * _PX, "medium": 3 * _PX, "thick": 5 * _PX}
_BORDER_STYLES = {
    "solid": "solid",
    "dashed": "dash",
    "dotted": "dot",
    "double": "solid",
    "groove": "solid",
    "ridge": "solid",
    "inset": "solid",
    "outset": "solid",
}


class _Bad(Exception):
    """A declaration that cannot be mapped; the message is the hint."""


def fmt(x: float) -> str:
    return f"{round(x, 2):g}"


# --------------------------------------------------------------------------- low-level text helpers


def split_top(text: str, seps: str = " \t\r\n") -> list[tuple[str, int]]:
    """Split on ``seps`` outside quotes and parentheses; returns (piece, start offset). Never raises."""
    out: list[tuple[str, int]] = []
    start = 0
    depth = 0
    quote = ""
    cur_start: int | None = None
    for i, ch in enumerate(text):
        if quote:
            if ch == quote:
                quote = ""
            continue
        if ch in "\"'":
            quote = ch
            if cur_start is None:
                cur_start = i
        elif ch == "(":
            depth += 1
            if cur_start is None:
                cur_start = i
        elif ch == ")":
            depth = max(0, depth - 1)
        elif ch in seps and depth == 0:
            if cur_start is not None:
                out.append((text[cur_start:i], cur_start))
                cur_start = None
        elif cur_start is None:
            cur_start = i
    if cur_start is not None:
        out.append((text[cur_start:], cur_start))
    del start
    return out


def _tokens(text: str) -> list[str]:
    return [p for p, _ in split_top(text)]


def _commas(text: str) -> list[str]:
    return [p.strip() for p, _ in split_top(text, ",") if p.strip()]


def _strip_quotes(s: str) -> str:
    s = s.strip()
    if len(s) >= 2 and s[0] == s[-1] and s[0] in "\"'":
        return s[1:-1]
    return s.strip("\"'")


def _strip_comments(text: str, ctx: Ctx, line0: int) -> str:
    out: list[str] = []
    i = 0
    while i < len(text):
        j = text.find("/*", i)
        if j < 0:
            out.append(text[i:])
            break
        out.append(text[i:j])
        k = text.find("*/", j + 2)
        if k < 0:
            line = line0 + text.count("\n", 0, j)
            ctx.warn("unterminated /* comment in css", line, "css-syntax", "close it with */")
            out.append("\n" * text.count("\n", j))
            break
        out.append("\n" * text.count("\n", j, k + 2))
        i = k + 2
    return "".join(out)


# --------------------------------------------------------------------------- values


def known_color_names(deck: Deck | None) -> set[str]:
    names: set[str] = set()
    try:
        from .. import theme as th

        names |= set(th.NEUTRAL_COLORS)
        for n in th.available():
            names |= set(th.get_theme(n).colors)
    except Exception:  # noqa: S110 - theme lookup is best effort
        pass
    if deck is not None:
        names |= {k.split(".", 1)[1] for k in deck.tokens if k.startswith("colors.")}
    return names


def _hex(tok: str) -> str | None:
    m = re.fullmatch(r"#([0-9A-Fa-f]{3,8})", tok)
    if not m:
        return None
    h = m.group(1).upper()
    if len(h) in (3, 4):
        h = "".join(c * 2 for c in h)
    if len(h) not in (6, 8):
        return None
    return "#" + h


def _alpha(s: str) -> float | None:
    s = s.strip()
    try:
        if s.endswith("%"):
            return min(1.0, max(0.0, float(s[:-1]) / 100))
        return min(1.0, max(0.0, float(s)))
    except ValueError:
        return None


def _rgb(tok: str) -> str | None:
    m = re.fullmatch(r"(rgba?|hsla?)\((.*)\)", tok.strip(), re.I | re.S)
    if not m:
        return None
    fn = m.group(1).lower()
    parts = [p for p in re.split(r"[\s,/]+", m.group(2).strip()) if p]
    if len(parts) not in (3, 4):
        return None
    if fn.startswith("hsl"):
        return _hsl(parts)
    rgb: list[int] = []
    for p in parts[:3]:
        try:
            v = float(p[:-1]) * 2.55 if p.endswith("%") else float(p)
        except ValueError:
            return None
        rgb.append(max(0, min(255, round(v))))
    out = "#{:02X}{:02X}{:02X}".format(*rgb)
    if len(parts) == 4:
        a = _alpha(parts[3])
        if a is None:
            return None
        if a < 1:
            out += f"{round(a * 255):02X}"
    return out


def _hsl(parts: list[str]) -> str | None:
    import colorsys

    try:
        h = float(parts[0].removesuffix("deg")) % 360 / 360
        s = float(parts[1].rstrip("%")) / 100
        light = float(parts[2].rstrip("%")) / 100
    except ValueError:
        return None
    r, g, b = colorsys.hls_to_rgb(h, min(1, max(0, light)), min(1, max(0, s)))
    out = f"#{round(r * 255):02X}{round(g * 255):02X}{round(b * 255):02X}"
    if len(parts) == 4:
        a = _alpha(parts[3])
        if a is None:
            return None
        if a < 1:
            out += f"{round(a * 255):02X}"
    return out


def parse_color(tok: str, names: set[str]) -> str | None:
    """Normalized color (``#RRGGBB[AA]`` or a theme color name) or ``None`` when ``tok`` is not a color."""
    t = tok.strip()
    if not t:
        return None
    if t.startswith("#"):
        return _hex(t)
    low = t.lower()
    if low.startswith(("rgb", "hsl")):
        return _rgb(t)
    m = re.fullmatch(r"var\(\s*--([\w-]+)\s*(?:,.*)?\)", t, re.I | re.S)
    if m:
        return m.group(1)
    if low in NAMED_COLORS:
        return NAMED_COLORS[low]
    if t in names:
        return t
    return None


def _color(tok: str, names: set[str]) -> str:
    c = parse_color(tok, names)
    if c is None:
        near = closest(tok, [*NAMED_COLORS, *names])
        raise _Bad(
            f"'{tok}' is not a color; use #RRGGBB, rgb(), a color name" + (f" (like {near})" if near else "")
        )
    return c


def _is_gradient(tok: str) -> bool:
    return bool(re.match(r"(repeating-)?(linear|radial|conic)-gradient\(", tok.strip(), re.I))


def _gradient(tok: str, names: set[str]) -> str:
    m = re.fullmatch(r"([\w-]+)\((.*)\)", tok.strip(), re.S)
    if not m:
        raise _Bad("unbalanced gradient; write linear-gradient(135deg, #AAA, #BBB)")
    fn = m.group(1).lower()
    if fn.startswith(("repeating-", "conic-")):
        raise _Bad("only linear-gradient(...) and radial-gradient(...) are supported")
    args: list[str] = []
    for arg in _commas(m.group(2)):
        parts = []
        for p in _tokens(arg):
            c = parse_color(p, names)
            parts.append(c if c else p)
        args.append(" ".join(parts))
    if len(args) < 2:
        raise _Bad("a gradient needs at least two colors")
    return f"{fn}({', '.join(args)})"


def _length(tok: str, fs: float | None = None) -> float:
    m = _LEN_RE.match(tok.strip())
    if not m:
        raise _Bad(f"'{tok}' is not a length; use px, pt, em, in, cm or mm, e.g. 12px")
    num = float(m.group(1))
    unit = (m.group(2) or "").lower()
    if not unit:
        if num != 0:
            raise _Bad(f"'{tok}' needs a unit, e.g. {tok}px")
        return 0.0
    if unit == "em":
        return round(num * (fs if fs else _DEFAULT_FS), 3)
    if unit == "rem":
        return round(num * _DEFAULT_FS, 3)
    return round(num * _UNIT_PT[unit], 3)


def _quads(val: str, fs: float | None) -> tuple[float, float, float, float]:
    vals = [_length(t, fs) for t in _tokens(val)]
    if not 1 <= len(vals) <= 4:
        raise _Bad("give 1 to 4 lengths, e.g. 8px 16px")
    if len(vals) == 1:
        return vals[0], vals[0], vals[0], vals[0]
    if len(vals) == 2:
        return vals[0], vals[1], vals[0], vals[1]
    if len(vals) == 3:
        return vals[0], vals[1], vals[2], vals[1]
    return vals[0], vals[1], vals[2], vals[3]


def _fr(tok: str) -> float | None:
    m = re.fullmatch(r"(\d+\.?\d*|\.\d+)fr", tok.strip(), re.I)
    return float(m.group(1)) if m else None


def _num(x: float) -> str:
    return str(int(x)) if x == int(x) else f"{x:g}"


# --------------------------------------------------------------------------- declarations


class _Maps:
    """Maps one declaration to Style field values; raises ``_Bad`` with a hint."""

    def __init__(self, names: set[str], fs: float | None):
        self.names = names
        self.fs = fs
        self.notes: list[tuple[str, str]] = []  # (message, hint) for soft problems

    # --- helpers
    def color(self, v: str) -> str:
        return _color(v, self.names)

    def _border_parts(self, v: str) -> tuple[float | None, str | None, str | None, bool]:
        """(width pt, dash, color, none) of a border shorthand."""
        width = dash = color = None
        none = False
        for t in _tokens(v):
            low = t.lower()
            if low in ("none", "hidden"):
                none = True
            elif low in _BORDER_STYLES:
                dash = _BORDER_STYLES[low]
            elif low in _BORDER_WIDTHS:
                width = _BORDER_WIDTHS[low]
            elif _LEN_RE.match(t):
                width = _length(t, self.fs)
            else:
                c = parse_color(t, self.names)
                if c is None:
                    raise _Bad(f"'{t}' is not a width, style (solid|dashed|dotted) or color in border")
                color = c
        return width, dash, color, none

    def _side(self, v: str) -> str:
        width, dash, color, none = self._border_parts(v)
        if none:
            return "none"
        if width is None:
            width = _BORDER_WIDTHS["medium"]
        return f"{fmt(width)}pt {dash or 'solid'} {color or 'fg'}"

    def _same(self, v: str, one: Any, what: str) -> Any:
        parts = _tokens(v)
        vals = [one(p) for p in parts]
        if not vals or len(vals) > 4 or any(x != vals[0] for x in vals):
            raise _Bad(f"{what} supports one value for all sides; use border-top/right/bottom/left for sides")
        return vals[0]

    # --- properties
    def p_color(self, v: str) -> dict:
        return {"color": self.color(v)}

    def p_background(self, v: str) -> dict:
        toks = _tokens(v)
        for t in toks:
            if _is_gradient(t):
                return {"fill": _gradient(t, self.names)}
            m = re.fullmatch(r"url\(\s*(.*?)\s*\)", t, re.I | re.S)
            if m:
                return {"fill": f"url({_strip_quotes(m.group(1))})"}
        if len(toks) == 1 and toks[0].lower() == "none":
            return {"fill": "#00000000"}
        for t in toks:
            c = parse_color(t, self.names)
            if c:
                return {"fill": c}
        raise _Bad("use a color, linear-gradient(...), radial-gradient(...) or url(path)")

    def p_background_color(self, v: str) -> dict:
        return {"fill": self.color(v)}

    def p_border(self, v: str) -> dict:
        width, dash, color, none = self._border_parts(v)
        if none:
            return {"line_width": 0.0}
        out: dict[str, Any] = {"line_width": width if width is not None else _BORDER_WIDTHS["medium"]}
        out["line_dash"] = dash or "solid"
        if color:
            out["line"] = color
        return out

    def _p_side(self, side: str):
        def fn(v: str) -> dict:
            return {f"border_{side}": self._side(v)}

        return fn

    def p_border_color(self, v: str) -> dict:
        return {"line": self._same(v, self.color, "border-color")}

    def p_border_width(self, v: str) -> dict:
        def one(t: str) -> float:
            return _BORDER_WIDTHS[t.lower()] if t.lower() in _BORDER_WIDTHS else _length(t, self.fs)

        return {"line_width": self._same(v, one, "border-width")}

    def p_border_style(self, v: str) -> dict:
        def one(t: str) -> str | None:
            low = t.lower()
            if low in ("none", "hidden"):
                return None
            if low in _BORDER_STYLES:
                return _BORDER_STYLES[low]
            raise _Bad(f"'{t}' is not a border style; use solid, dashed, dotted or none")

        d = self._same(v, one, "border-style")
        return {"line_width": 0.0} if d is None else {"line_dash": d}

    def p_border_radius(self, v: str) -> dict:
        toks = _tokens(v.split("/")[0])
        if any(t.endswith("%") for t in toks):
            raise _Bad("percent radius is not supported; use a length like 14px")
        vals = [_length(t, self.fs) for t in toks]
        if not vals:
            raise _Bad("give a length like 14px")
        if len(set(vals)) > 1:
            self.notes.append(
                ("different corner radii are not supported; using the first", "give one radius")
            )
        return {"radius": vals[0]}

    def p_box_shadow(self, v: str) -> dict:
        if v.strip().lower() == "none":
            return {"shadow": False}
        layers = _commas(v)
        if len(layers) > 1:
            self.notes.append(("only the first box-shadow layer is used", "write one shadow"))
        lens: list[float] = []
        color: str | None = None
        for t in _tokens(layers[0]):
            if t.lower() == "inset":
                raise _Bad("inset shadows are not supported")
            c = parse_color(t, self.names)
            if c is not None and not _LEN_RE.match(t):
                color = c
            else:
                lens.append(_length(t, self.fs))
        if not 2 <= len(lens) <= 4:
            raise _Bad("write '<x> <y> [blur [spread]] <color>', e.g. 0 8px 24px #0006")
        while len(lens) < 3:
            lens.append(0.0)
        if color is None:
            color = "#00000040"
        elif re.fullmatch(r"#[0-9A-F]{6}", color):
            color += "FF"
        return {"shadow": " ".join([*(fmt(x) for x in lens), color])}

    def p_opacity(self, v: str) -> dict:
        a = _alpha(v)
        if a is None:
            raise _Bad("use a number 0..1 or a percent, e.g. 0.8 or 80%")
        return {"opacity": a}

    def p_font_family(self, v: str) -> dict:
        fams = _commas(v)
        if not fams:
            raise _Bad("give a font name, e.g. 'Noto Sans JP'")
        return {"font": _strip_quotes(fams[0])}

    def p_font_size(self, v: str) -> dict:
        return {"font_size": _length(v, None)}

    def p_font_weight(self, v: str) -> dict:
        low = v.strip().lower()
        if low in ("bold", "bolder"):
            return {"bold": True}
        if low in ("normal", "lighter"):
            return {"bold": False}
        if _NUM_RE.match(low):
            return {"bold": float(low) >= 600}
        raise _Bad("use bold, normal or a number like 700")

    def p_font_style(self, v: str) -> dict:
        low = v.strip().lower()
        if low in ("italic", "oblique"):
            return {"italic": True}
        if low == "normal":
            return {"italic": False}
        raise _Bad("use italic or normal")

    def p_letter_spacing(self, v: str) -> dict:
        if v.strip().lower() == "normal":
            return {"letter_spacing": 0.0}
        return {"letter_spacing": _length(v, self.fs)}

    def p_line_height(self, v: str) -> dict:
        t = v.strip().lower()
        if t == "normal":
            return {"line_spacing": 1.0}
        if _NUM_RE.match(t):
            return {"line_spacing": float(t)}
        if t.endswith("%") and _NUM_RE.match(t[:-1]):
            return {"line_spacing": round(float(t[:-1]) / 100, 3)}
        if t.endswith("em") and _NUM_RE.match(t[:-2]):
            return {"line_spacing": float(t[:-2])}
        if re.fullmatch(r".*(px|pt|in|cm|mm)", t):
            if not self.fs:
                raise _Bad(
                    "a px/pt line-height needs font-size in the same rule; use a unitless value like 1.4"
                )
            return {"line_spacing": round(_length(t) / self.fs, 3)}
        raise _Bad("use a unitless multiple like 1.4")

    def p_text_align(self, v: str) -> dict:
        t = v.strip().lower()
        t = {"start": "left", "end": "right", "justify-all": "justify"}.get(t, t)
        if t not in ("left", "center", "right", "justify"):
            raise _Bad("use left, center, right or justify")
        return {"align": t}

    def p_vertical_align(self, v: str) -> dict:
        t = v.strip().lower()
        if t not in ("top", "middle", "bottom"):
            raise _Bad("use top, middle or bottom")
        return {"valign": t}

    def p_text_transform(self, v: str) -> dict:
        t = v.strip().lower()
        m = {"uppercase": "upper", "lowercase": "lower", "capitalize": "capitalize", "none": "none"}
        if t not in m:
            raise _Bad("use uppercase, lowercase, capitalize or none")
        return {"text_transform": m[t]}

    def p_text_decoration(self, v: str) -> dict:
        out: dict[str, Any] = {}
        for t in _tokens(v.lower()):
            if t == "underline":
                out["underline"] = True
            elif t == "line-through":
                out["strike"] = True
            elif t == "none":
                out["underline"] = False
                out["strike"] = False
            elif t in ("overline", "blink"):
                raise _Bad("only underline, line-through and none are supported")
        return out

    def p_padding(self, v: str) -> dict:
        t, r, b, left = _quads(v, self.fs)
        out: dict[str, Any] = {
            "padding_top": t,
            "padding_right": r,
            "padding_bottom": b,
            "padding_left": left,
        }
        if t == r == b == left:
            out["padding"] = t
        return out

    def _p_pad_side(self, side: str):
        def fn(v: str) -> dict:
            return {f"padding_{side}": _length(v, self.fs)}

        return fn

    def p_margin(self, v: str) -> dict:
        q = _quads(v, self.fs)
        if len(set(q)) != 1:
            raise _Bad("margin supports one value for all sides, e.g. 8px")
        return {"margin": q[0]}

    def p_gap(self, v: str) -> dict:
        vals = [_length(t, self.fs) for t in _tokens(v)]
        if not 1 <= len(vals) <= 2:
            raise _Bad("give one length, e.g. 16px")
        if len(vals) == 2 and vals[0] != vals[1]:
            self.notes.append(("row and column gap differ; using the row gap", "give one value"))
        return {"gap": vals[0]}

    def p_grid_template_columns(self, v: str) -> dict:
        ratios: list[float] = []
        for t in _tokens(v):
            m = re.fullmatch(r"repeat\(\s*(\d+)\s*,\s*(.*)\)", t, re.I | re.S)
            if m:
                inner = [_fr(x) for x in _tokens(m.group(2))]
                if not inner or any(x is None for x in inner) or not 1 <= int(m.group(1)) <= 50:
                    raise _Bad("use repeat(N, 1fr)")
                ratios += [x for x in inner * int(m.group(1)) if x is not None]
                continue
            f = _fr(t)
            if f is None:
                raise _Bad("columns must be fr units, e.g. 1fr 2fr or repeat(3, 1fr)")
            ratios.append(f)
        if not ratios or len(ratios) > 50:
            raise _Bad("give 1 to 50 columns")
        if all(x == ratios[0] for x in ratios):
            return {"grid": str(len(ratios))}
        return {"grid": ":".join(_num(x) for x in ratios)}

    def p_grid_template_areas(self, v: str) -> dict:
        rows = re.findall(r"\"([^\"]*)\"|'([^']*)'", v)
        rows = [(a or b).split() for a, b in rows]
        if not rows or not all(rows) or len({len(r) for r in rows}) != 1:
            raise _Bad('give equal-length quoted rows, e.g. "a a b" "a a c"')
        letters: dict[str, str] = {}
        out = []
        for row in rows:
            cells = []
            for name in row:
                if name == ".":
                    cells.append(".")
                else:
                    if name not in letters:
                        if len(letters) >= 26:
                            raise _Bad("at most 26 areas")
                        letters[name] = "abcdefghijklmnopqrstuvwxyz"[len(letters)]
                    cells.append(letters[name])
            out.append("".join(cells))
        return {"grid": "/".join(out)}

    def p_transform(self, v: str) -> dict:
        out: dict[str, Any] = {}
        for t in _tokens(v):
            m = re.fullmatch(r"rotate\(\s*([+-]?[\d.]+)\s*(deg|rad|turn|grad)?\s*\)", t, re.I)
            if m:
                try:
                    x = float(m.group(1))
                except ValueError as e:
                    raise _Bad("write rotate(-2deg)") from e
                unit = (m.group(2) or "deg").lower()
                x = {"deg": x, "rad": x * 57.29578, "turn": x * 360, "grad": x * 0.9}[unit]
                out["rotation"] = round(x, 3)
            elif t.lower() != "none":
                name = t.split("(")[0]
                self.notes.append((f"transform '{name}' is not supported", "only rotate(<deg>) is supported"))
        if not out and not self.notes:
            raise _Bad("write rotate(-2deg)")
        return out


def _build_table(m: _Maps) -> dict[str, Any]:
    table: dict[str, Any] = {
        "color": m.p_color,
        "background": m.p_background,
        "background-color": m.p_background_color,
        "border": m.p_border,
        "border-color": m.p_border_color,
        "border-width": m.p_border_width,
        "border-style": m.p_border_style,
        "border-radius": m.p_border_radius,
        "box-shadow": m.p_box_shadow,
        "opacity": m.p_opacity,
        "font-family": m.p_font_family,
        "font-size": m.p_font_size,
        "font-weight": m.p_font_weight,
        "font-style": m.p_font_style,
        "letter-spacing": m.p_letter_spacing,
        "line-height": m.p_line_height,
        "text-align": m.p_text_align,
        "vertical-align": m.p_vertical_align,
        "text-transform": m.p_text_transform,
        "text-decoration": m.p_text_decoration,
        "padding": m.p_padding,
        "margin": m.p_margin,
        "gap": m.p_gap,
        "grid-template-columns": m.p_grid_template_columns,
        "grid-template-areas": m.p_grid_template_areas,
        "transform": m.p_transform,
    }
    for side in ("top", "right", "bottom", "left"):
        table[f"border-{side}"] = m._p_side(side)
        table[f"padding-{side}"] = m._p_pad_side(side)
    return table


SUPPORTED = tuple(_build_table(_Maps(set(), None)))


# --------------------------------------------------------------------------- selectors


def normalize_selector(sel: str) -> tuple[str | None, str]:
    """Return (normalized selector, "") or (None, hint)."""
    s = sel.strip()
    if not s:
        return None, "empty selector"
    s = re.sub(r"\(\s*([^)]*?)\s*\)", lambda m: "(" + m.group(1).strip() + ")", s)
    if re.search(r"[\[\]+~*|^$=]|::|:(?!nth-child\(|first-child|last-child)", s):
        bad = re.search(r"\[[^\]]*\]?|::?[\w-]+(?:\([^)]*\))?|[+~*|]", s)
        what = bad.group(0) if bad else s
        return (
            None,
            f"'{what}' is not supported; use type, .class, #id, :nth-child(), :first-child, :last-child",
        )
    s = re.sub(r"\s*>\s*", " > ", s)
    parts = s.split()
    out: list[str] = []
    expect_compound = True
    for p in parts:
        if p == ">":
            if expect_compound:
                return None, "'>' needs a selector on both sides"
            out.append(">")
            expect_compound = True
            continue
        err = _compound_error(p)
        if err:
            return None, err
        out.append(p)
        expect_compound = False
    if expect_compound or not out:
        return None, "a selector cannot end with '>'"
    return " ".join(out), ""


def _compound_error(p: str) -> str | None:
    rest = p
    m = _TYPE_RE.match(rest)
    if m:
        t = m.group(0)
        if t.lower() not in SELECTOR_TYPES:
            near = closest(t, SELECTOR_TYPES)
            return f"type '{t}' is not supported; use one of {', '.join(SELECTOR_TYPES)}" + (
                f" (like {near})" if near else ""
            )
        rest = rest[m.end() :]
    if not rest and not m:
        return "empty selector"
    pos = 0
    while pos < len(rest):
        pm = _COMPOUND_PART.match(rest, pos)
        if not pm:
            return (
                f"'{rest[pos:]}' is not supported; "
                "use .class, #id, :nth-child(even|odd|N), :first-child, :last-child"
            )
        pos = pm.end()
    return None


# --------------------------------------------------------------------------- rule scanning


def _find_close(text: str, i: int) -> int:
    """Index of the ``}`` matching the ``{`` before ``i``, or -1."""
    depth = 1
    quote = ""
    while i < len(text):
        ch = text[i]
        if quote:
            if ch == quote:
                quote = ""
        elif ch in "\"'":
            quote = ch
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return i
        i += 1
    return -1


def _scan_prelude(text: str, i: int) -> tuple[int, str]:
    """From ``i`` find the first ``{ ; }`` outside quotes/parens; returns (index or len, char or '')."""
    depth = 0
    quote = ""
    while i < len(text):
        ch = text[i]
        if quote:
            if ch == quote:
                quote = ""
        elif ch in "\"'":
            quote = ch
        elif ch == "(":
            depth += 1
        elif ch == ")":
            depth = max(0, depth - 1)
        elif depth == 0 and ch in "{;}":
            return i, ch
        i += 1
    return len(text), ""


def parse_css(
    text: str, line0: int, ctx: Ctx, deck: Deck | None = None, header: bool = False
) -> list[CssRule]:
    """Parse the body of a css fence whose first line is source line ``line0``.

    ``deck`` is used to resolve theme color names; with ``header=True`` a ``:root { --name: #hex }`` rule
    defines the deck color token ``name``.
    """
    rules: list[CssRule] = []
    try:
        _parse(text, line0, ctx, deck, header, rules)
    except Exception as e:  # never raise on bad input
        ctx.warn(
            f"css could not be parsed ({type(e).__name__})", line0, "css-syntax", "simplify the css fence"
        )
    return rules


def _parse(text: str, line0: int, ctx: Ctx, deck: Deck | None, header: bool, rules: list[CssRule]) -> None:
    text = _strip_comments(text, ctx, line0)
    names = known_color_names(deck)
    pos = 0
    n = len(text)

    def line_at(p: int) -> int:
        return line0 + text.count("\n", 0, p)

    while pos < n:
        while pos < n and text[pos].isspace():
            pos += 1
        if pos >= n:
            break
        end, ch = _scan_prelude(text, pos)
        prelude = text[pos:end].strip()
        pline = line_at(pos + (len(text[pos:end]) - len(text[pos:end].lstrip())))
        if ch == "}":
            ctx.warn("stray '}' in css", line_at(end), "css-syntax", "remove it or add the matching '{'")
            pos = end + 1
            continue
        if ch == ";" or ch == "":
            if prelude.startswith("@"):
                _at_rule(prelude, pline, ctx)
            elif prelude:
                ctx.warn(
                    f"css text '{prelude[:30]}' is not a rule",
                    pline,
                    "css-syntax",
                    "write 'selector { property: value }'",
                )
            pos = end + 1
            continue
        close = _find_close(text, end + 1)
        if close < 0:
            ctx.warn("css block is never closed", pline, "css-syntax", "add the missing '}'")
            body, body_start, pos = text[end + 1 :], end + 1, n
        else:
            body, body_start, pos = text[end + 1 : close], end + 1, close + 1
        if prelude.startswith("@"):
            _at_rule(prelude, pline, ctx)
            continue
        _rule(prelude, pline, body, line_at(body_start), ctx, deck, header, names, rules)


def _at_rule(prelude: str, line: int, ctx: Ctx) -> None:
    name = prelude.split()[0] if prelude.split() else "@"
    ctx.warn(
        f"css at-rule '{name}' is not supported and was skipped",
        line,
        "css-at-rule",
        "remove it; put the declarations in plain rules such as 'slide { ... }'",
    )


def _rule(
    prelude: str,
    line: int,
    body: str,
    body_line: int,
    ctx: Ctx,
    deck: Deck | None,
    header: bool,
    names: set[str],
    rules: list[CssRule],
) -> None:
    selectors: list[str] = []
    root = False
    for raw in _commas(prelude):
        if raw.lower() == ":root":
            root = True
            continue
        norm, hint = normalize_selector(raw)
        if norm is None:
            ctx.warn(f"css selector '{raw}' skipped", line, "css-selector", hint)
        elif norm not in selectors:
            selectors.append(norm)
    if not selectors and not root:
        if not _commas(prelude):
            ctx.warn("css rule has no selector", line, "css-selector", "write 'h1 { color: #333 }'")
        return
    style, customs = parse_declarations(body, body_line, ctx, names, root)
    for name, value, dline in customs:
        if root and header and deck is not None:
            c = parse_color(value, names)
            if c is None:
                ctx.warn(
                    f"custom property --{name}: '{value}' is not a color",
                    dline,
                    "css-value",
                    "only color variables are supported, e.g. --primary: #7C5CFF",
                )
            else:
                deck.tokens[f"colors.{name}"] = c
                names.add(name)
        else:
            ctx.warn(
                f"custom property --{name} is only supported in ':root' of the deck header css fence",
                dline,
                "css-property",
                f"define '--{name}' in ':root {{ }}' before the first slide and use var(--{name})",
            )
    if not any(v is not None for v in style.model_dump().values()):
        return
    for sel in selectors:
        rules.append(CssRule(selector=sel, style=style, line=line))


def parse_declarations(
    body: str, line0: int, ctx: Ctx, names: set[str], root: bool = False
) -> tuple[Style, list[tuple[str, str, int]]]:
    """Map ``prop: value; ...`` to a Style. Returns (style, custom properties as (name, value, line))."""
    decls: list[tuple[str, str, int]] = []
    for piece, off in split_top(body, ";"):
        if not piece.strip():
            continue
        line = line0 + body.count("\n", 0, off + (len(piece) - len(piece.lstrip())))
        prop, colon, val = piece.partition(":")
        prop = prop.strip().lower() if not prop.strip().startswith("--") else prop.strip()
        val = re.sub(r"\s*!important\s*$", "", val.strip(), flags=re.I)
        if not colon or not prop:
            ctx.warn(
                f"css declaration '{piece.strip()[:30]}' has no 'property: value'",
                line,
                "css-property",
                "write 'property: value;'",
            )
            continue
        if "{" in piece or "}" in piece:
            ctx.warn(
                f"css declaration '{prop}' contains braces; nested rules are not supported",
                line,
                "css-syntax",
                "write flat rules",
            )
            continue
        decls.append((prop, val.strip(), line))
    fs: float | None = None
    for prop, val, _ in decls:
        if prop == "font-size":
            try:
                fs = _length(val, None)
            except _Bad:
                pass
    m = _Maps(names, fs)
    table = _build_table(m)
    data: dict[str, Any] = {}
    customs: list[tuple[str, str, int]] = []
    for prop, val, line in decls:
        if prop.startswith("--"):
            customs.append((prop[2:], val, line))
            continue
        if root:
            ctx.warn(
                f"':root' only holds --variables, '{prop}' ignored",
                line,
                "css-property",
                "use 'slide { ... }' for page-wide styles",
            )
            continue
        fn = table.get(prop)
        if fn is None:
            near = closest(prop, SUPPORTED, cutoff=0.6)
            hint = (
                f"did you mean '{near}'?"
                if near
                else "supported: color, background, border, border-radius, box-shadow, opacity, font-*, "
                "letter-spacing, line-height, text-*, padding, margin, gap, grid-template-*, transform"
            )
            ctx.warn(f"css property '{prop}' is not supported", line, "css-property", hint)
            continue
        if not val:
            ctx.warn(f"css property '{prop}' has no value", line, "css-value", f"write '{prop}: <value>'")
            continue
        m.notes.clear()
        try:
            data.update(fn(val))
        except _Bad as e:
            ctx.warn(f"css value '{val[:40]}' for '{prop}' skipped", line, "css-value", str(e))
        except Exception as e:  # defensive: never raise
            ctx.warn(
                f"css value for '{prop}' could not be read ({type(e).__name__})",
                line,
                "css-value",
                "check the value",
            )
        for msg, hint in m.notes:
            ctx.warn(f"css '{prop}': {msg}", line, "css-value", hint)
    try:
        return Style(**data), customs
    except Exception:
        return Style(), customs


_FENCE = re.compile(r"^[ \t]*(`{3,}|~{3,})(.*)$")


def extract_fences(lines: list[str]) -> list[tuple[int, str]]:
    """Find ```css fences, blank their lines in place (line numbers stay valid), return (open index, body)."""
    out: list[tuple[int, str]] = []
    i = 0
    n = len(lines)
    while i < n:
        m = _FENCE.match(lines[i])
        if not m or (m.group(1)[0] == "`" and "`" in m.group(2)):
            i += 1
            continue
        marker = m.group(1)
        info = m.group(2).strip().split()
        j = i + 1
        while j < n:
            c = _FENCE.match(lines[j])
            if c and c.group(1)[0] == marker[0] and len(c.group(1)) >= len(marker) and not c.group(2).strip():
                break
            j += 1
        if info and info[0].lower().split("{")[0] == "css" and j < n:
            out.append((i, "\n".join(lines[i + 1 : j])))
            for k in range(i, j + 1):
                lines[k] = ""
        i = j + 1
    return out

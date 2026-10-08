"""Pandoc-style ``{.class #id key=value}`` attributes and the ``@`` layout line."""

from __future__ import annotations

import difflib
import math
import os
import re
import shlex
from dataclasses import dataclass, field
from typing import Any

from .. import forms, forms2, icons, shapes
from ..ir import Box, Chart, ElementBase, Image, Media, Style, Table
from .ctx import Ctx, closest
from .tabular import apply_chart_kv, apply_table_kv

_TOKEN = re.compile(
    r"""\s*(?:\.(?P<cls>[\w-]+)
        |\#(?P<id>[\w-]+)
        |(?P<key>[A-Za-z][\w-]*(?:\.[\w-]+)*)=(?P<val>(?:"[^"]*"|'[^']*'|[^\s"'{}]+)+)
        |(?P<bare>bold|italic|autoplay|loop)(?![\w-]))""",
    re.X,
)
_COMMA_SPACE = re.compile(r"""("[^"]*"|'[^']*')|,[ \t]+(?![A-Za-z][\w-]*=)""")  # quoted text stays as it is
MEDIA_EXT = {
    **dict.fromkeys((".mp4", ".m4v", ".mov", ".wmv", ".avi", ".webm"), "video"),
    **dict.fromkeys((".mp3", ".m4a", ".wav", ".aac", ".wma"), "audio"),
}


def media_kind(src: str) -> str | None:
    """'video' / 'audio' when the path (ignoring ?query and #fragment) has a media extension."""
    path = src.split("?", 1)[0].split("#", 1)[0]
    return MEDIA_EXT.get(os.path.splitext(path)[1].lower())


TRAILING = re.compile(r"\s*\{([^{}]*)\}\s*$")
STANDALONE = re.compile(r"^\{([^{}]*)\}[ \t]*$")


@dataclass
class Attrs:
    classes: list[str] = field(default_factory=list)
    id: str | None = None
    kv: dict[str, str] = field(default_factory=dict)


def parse_attr_body(body: str) -> Attrs | None:
    """Parse the inside of ``{...}``; ``None`` when it is not a valid attribute list."""
    a = Attrs()
    pos = 0
    body = _COMMA_SPACE.sub(lambda m: m.group(1) or ",", body)  # `hl=a, b` reads as `hl=a,b`
    while body[pos:].strip():
        m = _TOKEN.match(body, pos)
        if not m or m.end() == pos:
            return None
        if m.group("cls"):
            a.classes.append(m.group("cls"))
        elif m.group("id"):
            a.id = m.group("id")
        elif m.group("key"):
            val = m.group("val")
            if re.fullmatch(r"\"[^\"]*\"|'[^']*'", val):  # one quoted value (`hl="a",b` keeps its quotes)
                val = val[1:-1]
            a.kv[m.group("key")] = val
        else:
            a.kv[m.group("bare")] = "true"
        pos = m.end()
    return a


def split_trailing_attrs(text: str) -> tuple[str, Attrs | None]:
    m = TRAILING.search(text)
    if not m:
        return text, None
    if (
        m.start() > 0
        and m.start() == m.start(1) - 1
        and text[m.start() - 1] == "]"
        and "[" in text[: m.start()]
    ):
        return text, None  # `[x]{size=12}` is the span's own attribute list, not the heading's
    a = parse_attr_body(m.group(1))
    if a is None:
        return text, None
    return text[: m.start()], a


def _length(v: str) -> str | float:
    try:
        f = float(v)
    except ValueError:
        return v
    return f if math.isfinite(f) else v  # `w=INF` / `nan` are text: the layout reads them as a bad length


def _bool(v: str) -> bool | None:
    s = v.strip().lower()
    if s in ("true", "1", "yes", "on", ""):
        return True
    if s in ("false", "0", "no", "off"):
        return False
    return None


def _float(v: str) -> float | None:
    try:
        return float(re.sub(r"(pt)?$", "", v.strip()))
    except ValueError:
        return None


Z_MIN, Z_MAX = 1, 9


def _shadow(v: str) -> bool | str | None:
    """``on`` / ``off`` or CSS-like ``"x y blur [spread] color"`` (pt); ``None`` when it is neither."""
    s = v.strip().lower()
    if s in ("on", "true", "yes", "1", ""):
        return True
    if s in ("off", "none", "false", "no", "0"):
        return False
    text = re.sub(r"\s*,\s*", " ", v.strip())
    return text if re.match(r"-?\d", text) and len(text.split()) >= 2 else None


VALID_KEYS = (
    *("x", "y", "w", "h", "size", "color", "fill", "line", "font", "align", "valign", "bold", "italic"),
    *("radius", "opacity", "pad", "fit", "bg", "t", "hidden", "gap", "id", "icon"),
    *("shadow", "rotate", "shape", "z", "stripe"),
    *("poster", "autoplay", "loop", "render"),
)
ICON_NAMES = tuple(icons.names())
KNOWN_CLASSES = (
    "primary",
    "accent",
    "danger",
    "success",
    "muted",
    "plain",
    "kpi",
    "card",
    "dense",
    "dark",
    "light",
)
_BOX = ("x", "y", "w", "h")
_ALIGN = ("left", "center", "right", "justify")
_VALIGN = ("top", "middle", "bottom")


def apply_attrs(
    el: ElementBase, a: Attrs, ctx: Ctx, line: int | None, sink: dict[str, Any] | None = None
) -> None:
    """Apply parsed attributes to an element. Unknown keys go to ``sink`` (default ``el.attrs``)."""
    sink = el.attrs if sink is None else sink
    if isinstance(el, Chart):
        a = Attrs(a.classes, a.id, apply_chart_kv(el, a.kv, ctx, line))
        sink = el.options
    elif isinstance(el, Table):
        a = Attrs(a.classes, a.id, apply_table_kv(el, a.kv, ctx, line))
    if a.id:
        el.id = a.id
    for c in a.classes:
        if c not in el.classes:
            el.classes.append(c)
        near = closest(c, KNOWN_CLASSES, 0.75)
        if near and c not in KNOWN_CLASSES:
            ctx.warn(f"unknown class '.{c}'", line, "unknown-attr", f"did you mean '.{near}'?")
    box: dict[str, Any] = {}
    style: dict[str, Any] = {}
    for k, v in a.kv.items():
        if k in _BOX:
            box[k] = _length(v)
        elif k == "size":
            f = _float(v.rstrip("%")) if isinstance(el, (Image, Media)) else _float(v)
            if f is None or (isinstance(el, (Image, Media)) and not 5 <= f <= 100):
                what = (
                    ("a picture's size is a percent of its cell, 5-100, e.g. {size=60}")
                    if isinstance(el, (Image, Media))
                    else "size is a number in pt, e.g. {size=10}"
                )
                ctx.warn(f"bad size '{v}'", line, "bad-attr", what)
            else:
                style["font_size"] = f
        elif k in ("color", "fill", "line", "font"):
            style[k] = v
        elif k == "align":
            if v in _ALIGN:
                style["align"] = v
            else:
                ctx.warn(f"bad align '{v}'", line, "bad-attr", "use align=left|center|right|justify")
        elif k == "valign":
            if v in _VALIGN:
                style["valign"] = v
            else:
                ctx.warn(f"bad valign '{v}'", line, "bad-attr", "use valign=top|middle|bottom")
        elif k in ("bold", "italic"):
            b = _bool(v)
            if b is None:
                ctx.warn(f"bad {k} '{v}'", line, "bad-attr", f"use {k}=true|false")
            else:
                style[k] = b
        elif k in ("radius", "opacity"):
            f = _float(v)
            if f is None:
                ctx.warn(f"bad {k} '{v}'", line, "bad-attr", f"{k} is a number")
            else:
                style[k] = f
        elif k == "pad":
            style["padding"] = _length(v)
        elif k == "rotate":
            f = _float(re.sub(r"(deg|\u00b0)$", "", v.strip()))
            if f is None or not -360 <= f <= 360:
                ctx.warn(
                    f"bad rotate '{v}'", line, "bad-attr", "rotate is degrees clockwise, e.g. {rotate=15}"
                )
            else:
                style["rotation"] = f
        elif k == "shape":
            name = shapes.resolve(v)
            if name is None:
                ctx.warn(f"unknown shape '{v}'", line, "bad-attr", shapes.suggest(v))
            else:
                style["shape"] = name
        elif k == "z":
            try:
                z = int(v.strip())
            except ValueError:
                z = 0
            if not Z_MIN <= z <= Z_MAX:
                ctx.warn(f"bad z '{v}'", line, "bad-attr", "z is a level 1..9: 1 behind the rest, 9 in front")
            else:
                style["z"] = z
        elif k == "shadow":
            sh = _shadow(v)
            if sh is None:
                ctx.warn(
                    f"bad shadow '{v}'",
                    line,
                    "bad-attr",
                    'use shadow=on|off or shadow="0 4 12 #00000040" (x y blur color, pt)',
                )
            else:
                style["shadow"] = sh
        elif k == "fit" and isinstance(el, Image):
            if v in ("contain", "cover", "stretch"):
                el.fit = v  # type: ignore[assignment]
            else:
                ctx.warn(f"bad fit '{v}'", line, "bad-attr", "use fit=contain|cover|stretch")
        elif k in ("autoplay", "loop") and isinstance(el, Media):
            b = _bool(v)
            if b is None:
                ctx.warn(f"bad {k} '{v}'", line, "bad-attr", f"use {k} or {k}=false")
            else:
                setattr(el, k, b)
        elif k == "poster" and isinstance(el, Media):
            el.poster = v
        elif k == "icon":
            if icons.is_file(v):
                el.attrs["icon"] = v.strip()  # the file is read at render time (relative to the deck)
            elif icons.path(v):
                el.attrs["icon"] = v.strip().lower()
            else:
                low = v.strip().lower()
                near = difflib.get_close_matches(low, ICON_NAMES, n=3, cutoff=0.3)
                tip = "or icon=file.svg for your own"
                if near and closest(low, near, 0.5) == near[0]:  # fix.py reads "did you mean '<name>'"
                    more = f" (also {', '.join(near[1:])})" if len(near) > 1 else ""
                    hint = f"did you mean '{near[0]}'?{more} {tip}"
                else:
                    hint = (
                        f"closest: {', '.join(near)}; {tip}" if near else f"see 'slidemark docs icons'; {tip}"
                    )
                ctx.warn(f"unknown icon '{v}'", line, "unknown-icon", hint)
        else:
            sink[k] = v
            near = closest(k, VALID_KEYS, 0.7) if sink is el.attrs else None
            if near and near != k:
                ctx.warn(f"unknown attribute '{k}'", line, "unknown-attr", f"did you mean '{near}='?")
    if box:
        merged = el.box.model_dump() if el.box else {}
        merged.update(box)
        el.box = Box(**merged)
    if style:
        el.style = (el.style or Style()).merged(Style(**style))
    if isinstance(el, Table) and "padding" in style:  # `{pad=}` on a table pads every cell (and is measured)
        for row in el.rows:
            for cell in row:
                cell.style = (cell.style or Style()).merged(Style(padding=style["padding"]))


# --------------------------------------------------------------------------- the `@` line

LAYOUT_WORDS = ("cover", "section", "blank", "center", "free")
FLAGS = ("flow", "chevron", "steps")
AT_KEYS = ("bg", "t", "id", "gap", "num", *(k for k in forms.ALL_KEYS if k != "gap"))
KNOWN_WORDS = (
    *LAYOUT_WORDS,
    *FLAGS,
    "html",
    "hidden",
    "build",
    "dense",
    "dark",
    "light",
    "plain",
    "kpi",
    "rows",
    "num",
    "items",
    "tile",
    "noemph",
    "defaults",
    "grid",
    *forms.FORMS,
)
KNOWN_WORDS = (*KNOWN_WORDS, "disc", *forms2.WORDS)  # DL3b part 2: @iconlist @quote @split @proscons ...
TRANSITIONS = ("fade", "push", "wipe", "split", "cover", "zoom", "morph")
_N = re.compile(r"^\d+$")
_CXR = re.compile(r"^\d+x\d+$")
_RATIO = re.compile(r"^\d+(?:\.\d+)?(?::\d+(?:\.\d+)?)+$")
_AREAS = re.compile(r"^[a-z.]+(?:/[a-z.]+)+$")
_LINK = re.compile(r"^([a-z]|\d+)([>-])([a-z]|\d+)$")


@dataclass
class AtSpec:
    grid: str | None = None
    gap: str | float | None = None
    layout: str | None = None
    classes: list[str] = field(default_factory=list)
    attrs: dict[str, str] = field(default_factory=dict)
    id: str | None = None
    background: str | None = None
    transition: str | None = None
    hidden: bool = False
    links: list[RawLink] = field(default_factory=list)


@dataclass
class RawLink:
    """An unresolved connector token: ``src``/``dst`` are 0-based indices; validated once blocks are known."""

    src: int
    dst: int
    arrow: bool
    token: str
    line: int


def _link_index(t: str) -> int:
    return ord(t) - 97 if t.isalpha() else int(t) - 1


def check_transition(v: str, ctx: Ctx, line: int | None) -> str | None:
    """Validate ``name`` or ``name:seconds`` (0.1-10 s); a bad value warns and returns ``None``."""
    name, _, dur = v.strip().lower().partition(":")
    if name == "none" and not dur:
        return None
    hint = f"use t=<{'|'.join(TRANSITIONS)}> or t=fade:0.5 (duration 0.1-10 s)"
    if name not in TRANSITIONS:
        ctx.warn(f"bad transition '{v}'", line, "bad-transition", hint)
        return None
    if dur:
        try:
            ok = 0.1 <= float(dur) <= 10
        except ValueError:
            ok = False
        if not ok:
            ctx.warn(f"bad transition duration '{v}'", line, "bad-transition", hint)
            return None
    return name + (f":{dur}" if dur else "")


def parse_at(text: str, ctx: Ctx, line: int) -> AtSpec:
    spec = AtSpec()
    try:
        tokens = shlex.split(text)
    except ValueError:
        tokens = text.split()
    for tok in tokens:
        if "=" in tok and not tok.startswith("="):
            k, v = tok.split("=", 1)
            if k == "bg":
                spec.background = v
            elif k == "t":
                spec.transition = check_transition(v, ctx, line)
            elif k == "id":
                spec.id = v
            elif k == "gap":
                spec.gap = _length(v)
            elif k == "num":  # `@4 num=text`: the number as big coloured text above the heading, not a badge
                if v in ("text", "badge", "on"):
                    spec.classes += [c for c in ("num", "num-text" if v == "text" else "") if c]
                else:
                    ctx.warn(
                        f"bad num '{v}'", line, "bad-attr", "use num=text (big number) or num=badge (circle)"
                    )
            elif k in forms2.KEYS:  # secondary attributes of the composition forms (checked below)
                spec.attrs[k] = v
            else:
                spec.attrs[k] = v
                if k not in AT_KEYS:
                    near = closest(k, AT_KEYS, 0.5)
                    hint = f"did you mean '{near}='?" if near else f"valid keys: {', '.join(AT_KEYS)}"
                    ctx.warn(f"unknown '@' key '{k}'", line, "unknown-token", hint)
        elif tok in LAYOUT_WORDS:
            spec.layout = tok
        elif tok == "html":
            spec.classes.append("html")
        elif tok == "grid":  # `@free grid`: x y w h snap to a 12 x 12 grid (`3c` = column 3)
            spec.classes.append("grid")
        elif tok == "hidden":
            spec.hidden = True
        elif tok in FLAGS:
            spec.classes.append(tok)
        elif _LINK.match(tok):
            a, op, b = _LINK.match(tok).groups()  # type: ignore[union-attr]
            spec.links.append(RawLink(_link_index(a), _link_index(b), op == ">", tok, line))
        elif _N.match(tok) or _CXR.match(tok) or _RATIO.match(tok) or _AREAS.match(tok):
            if tok.isdigit() and int(tok) < 1:
                ctx.warn("grid needs at least 1 column", line, "bad-grid", "use e.g. @2 or @2x2")
                continue
            if _AREAS.match(tok) and len({len(r) for r in tok.split("/")}) > 1:
                ctx.warn(
                    f"grid rows have different lengths: {tok}",
                    line,
                    "bad-grid",
                    "every row of an areas grid needs the same number of letters, e.g. aab/aac",
                )
            n_ratio = _consistent_n_ratio(spec.grid, tok)
            if n_ratio:  # `@2 1:2`: the column count agrees with the ratios, keep the ratios silently
                spec.grid = n_ratio
            elif spec.grid is not None:
                ctx.warn(f"second grid '{tok}' ignored", line, "bad-grid", "use one grid token per @ line")
            else:
                spec.grid = tok
        else:
            spec.classes.append(tok)
            near = closest(tok, KNOWN_WORDS, 0.75)
            if near and tok not in KNOWN_WORDS:
                ctx.warn(f"unknown '@' token '{tok}'", line, "unknown-token", f"did you mean '{near}'?")
            elif tok[0].isdigit() or "/" in tok:
                ctx.warn(
                    f"cannot read grid '{tok}'",
                    line,
                    "bad-grid",
                    "grids look like 3, 2x2, 1:2 or aab/aac (lowercase letters, same row length)",
                )
    forms2.check_at(spec.classes, spec.attrs, lambda msg, rule, hint: ctx.warn(msg, line, rule, hint))
    return spec


def _consistent_n_ratio(first: str | None, second: str) -> str | None:
    """`2` + `1:2` (either order) with matching column counts -> the ratio token, else None."""
    if first is None:
        return None
    for n, ratio in ((first, second), (second, first)):
        if n.isdigit() and _RATIO.match(ratio) and len(ratio.split(":")) == int(n):
            return ratio
    return None

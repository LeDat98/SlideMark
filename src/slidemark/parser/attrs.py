"""Pandoc-style ``{.class #id key=value}`` attributes and the ``@`` layout line."""

from __future__ import annotations

import re
import shlex
from dataclasses import dataclass, field
from typing import Any

from ..ir import Box, ElementBase, Image, Style
from .ctx import Ctx, closest

_TOKEN = re.compile(
    r"""\s*(?:\.(?P<cls>[\w-]+)
        |\#(?P<id>[\w-]+)
        |(?P<key>[A-Za-z][\w-]*)=(?P<val>"[^"]*"|'[^']*'|[^\s"'{}]+)
        |(?P<bare>bold|italic)(?![\w-]))""",
    re.X,
)
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
            if len(val) >= 2 and val[0] == val[-1] and val[0] in "\"'":
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
    a = parse_attr_body(m.group(1))
    if a is None:
        return text, None
    return text[: m.start()], a


def _length(v: str) -> str | float:
    try:
        return float(v)
    except ValueError:
        return v


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


VALID_KEYS = (
    *("x", "y", "w", "h", "size", "color", "fill", "line", "font", "align", "valign", "bold", "italic"),
    *("radius", "opacity", "pad", "fit", "bg", "t", "hidden", "gap", "id"),
)
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
            f = _float(v)
            if f is None:
                ctx.warn(f"bad size '{v}'", line, "bad-attr", "size is a number in pt, e.g. {size=10}")
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
        elif k == "fit" and isinstance(el, Image):
            if v in ("contain", "cover", "stretch"):
                el.fit = v  # type: ignore[assignment]
            else:
                ctx.warn(f"bad fit '{v}'", line, "bad-attr", "use fit=contain|cover|stretch")
        else:
            sink[k] = v
            near = closest(k, VALID_KEYS, 0.7) if sink is el.attrs else None
            if near:
                ctx.warn(f"unknown attribute '{k}'", line, "unknown-attr", f"did you mean '{near}='?")
    if box:
        merged = el.box.model_dump() if el.box else {}
        merged.update(box)
        el.box = Box(**merged)
    if style:
        el.style = (el.style or Style()).merged(Style(**style))


# --------------------------------------------------------------------------- the `@` line

LAYOUT_WORDS = ("cover", "section", "blank", "center")
FLAGS = ("flow", "chevron")
AT_KEYS = ("bg", "t", "id", "gap")
KNOWN_WORDS = (*LAYOUT_WORDS, *FLAGS, "hidden", "dense", "dark", "light", "plain")
_N = re.compile(r"^\d+$")
_CXR = re.compile(r"^\d+x\d+$")
_RATIO = re.compile(r"^\d+(?:\.\d+)?(?::\d+(?:\.\d+)?)+$")
_AREAS = re.compile(r"^[a-z.]+(?:/[a-z.]+)+$")


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
                spec.transition = v
            elif k == "id":
                spec.id = v
            elif k == "gap":
                spec.gap = _length(v)
            else:
                spec.attrs[k] = v
                near = closest(k, AT_KEYS, 0.5)
                hint = f"did you mean '{near}='?" if near else f"valid keys: {', '.join(AT_KEYS)}"
                ctx.warn(f"unknown '@' key '{k}'", line, "unknown-token", hint)
        elif tok in LAYOUT_WORDS:
            spec.layout = tok
        elif tok == "hidden":
            spec.hidden = True
        elif tok in FLAGS:
            spec.classes.append(tok)
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
            if spec.grid is not None:
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
    return spec

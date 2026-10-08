"""The composition vocabulary (DL3b): one ``@word`` slide directive per form, with secondary attributes.

``@timeline dir=v marks=num`` / ``@vs`` / ``@matrix x="low<-effort->high"`` / ``@funnel`` / ``@pyramid`` /
``@cycle`` / ``@agenda`` / ``@statement``. Every form takes ``gap=`` ``size=`` (its text, pt) and ``fill=``
(colors ``a,b,c``) plus its own keys; looks are tokens (``timeline.dot``, ``vs.badge.fill`` ...).

This module is the shared contract: the parser validates against it, the layout composes from it
(``layout/vocab.py``), ``honour.py`` and ``fit.py`` name the forms from it, the importer folds the shapes
back. It reads no theme and draws nothing.
"""

from __future__ import annotations

import re
from typing import Any

from .ir import Container, Slide, Text

FORMS = ("timeline", "vs", "matrix", "funnel", "pyramid", "cycle", "agenda", "statement", "stairs", "nested")
COMMON = ("gap", "size", "fill")

# per form: attribute -> allowed words (None = free text)
KEYS: dict[str, dict[str, tuple[str, ...] | None]] = {
    "timeline": {"dir": ("h", "v"), "marks": ("on", "off", "num")},
    "vs": {},
    "matrix": {"x": None, "y": None},
    "funnel": {"dir": ("down", "up")},
    "pyramid": {"dir": ("up", "down")},
    "cycle": {"dir": ("cw", "ccw"), "center": None},
    "agenda": {},
    "statement": {"align": ("left", "center", "right"), "valign": ("top", "middle", "bottom")},
    "stairs": {"dir": ("up", "down")},
    "nested": {"side": ("left", "right")},
    "flowdisc": {"above": ("on", "off", "1", "0")},  # `@flow disc`: a pseudo form (``flow`` is a grid word)
}
DEFAULTS = {"timeline": {"dir": "h", "marks": "on"}, "funnel": {"dir": "down"}, "pyramid": {"dir": "up"}}
DEFAULTS["cycle"] = {"dir": "cw"}
DEFAULTS["statement"] = {"align": "center", "valign": "middle"}
DEFAULTS["stairs"] = {"dir": "up"}
DEFAULTS["nested"] = {"side": "left"}
ALL_KEYS = tuple(sorted({k for d in KEYS.values() for k in d} | set(COMMON)))

# `##` boxes the form needs (min, max); agenda and statement read a list / text instead
COUNTS = {"timeline": (2, 10), "vs": (2, 3), "matrix": (4, 4), "funnel": (2, 8), "pyramid": (2, 8)}
COUNTS["cycle"] = (3, 6)
COUNTS["stairs"] = (2, 6)
COUNTS["nested"] = (3, 4)
COUNTS["flowdisc"] = (2, 7)

EXAMPLE = {
    "timeline": "@timeline dir=h marks=on, then `## 2026 Q1` + one line per milestone ({.accent} = now)",
    "vs": "@vs, then two `## ` boxes (+ a third `## 結論` verdict, {.hero} on the winner)",
    "matrix": '@matrix x="low<-effort->high" y="low<-impact->high", then four `## ` boxes',
    "funnel": "@funnel, then `## ` boxes from the widest stage down",
    "pyramid": "@pyramid, then `## ` boxes from the top (narrowest) down",
    "cycle": "@cycle, then 3-6 `## ` boxes in loop order",
    "agenda": "@agenda, then one `1.` list alone ({.accent} on the current item)",
    "statement": "@statement, then **+18%** and one caption line",
    "stairs": "@stairs, then 2-6 `## ` boxes from the lowest step to the highest (dir=down reverses)",
    "nested": "@nested, then 3-4 `## ` boxes from the outer ring to the inner one",
    "flowdisc": "@flow disc, then 2-7 `## ` boxes in order ({.above} on the first = a node above the row)",
}
WORD = {"flowdisc": "flow disc"}  # how a pseudo form reads on the `@` line

_ACCENT = re.compile(r"\s*\{\.accent\}\s*$")


def form_of(slide: Slide) -> str | None:
    """The slide's form word (the first of ``FORMS`` among its classes), ``flowdisc`` for ``@flow disc``,
    else ``None``."""
    got = next((c for c in slide.classes if c in FORMS), None)
    if got is None and "flow" in slide.classes and "disc" in slide.classes:
        return "flowdisc"
    return got


def boxes(slide: Slide) -> list[Container] | None:
    """The slide's ``##`` boxes when it holds nothing else; ``None`` otherwise."""
    els = slide.elements
    if els and all(isinstance(e, Container) and e.title is not None and e.grid is None for e in els):
        return list(els)  # type: ignore[arg-type]
    return None


def agenda_items(slide: Slide) -> list[tuple[str, list[Any], bool]] | None:
    """``(text, sub paragraphs, current)`` of an ``@agenda`` list (one ordered list alone), else ``None``."""
    els = slide.elements
    if len(els) != 1 or not isinstance(els[0], Text) or els[0].box is not None or not els[0].paragraphs:
        return None
    paras = els[0].paragraphs
    if paras[0].marker != "number" or any(p.marker is None for p in paras):
        return None
    out: list[tuple[str, list[Any], bool]] = []
    for p in paras:
        if p.marker == "number" and p.level == 0:
            # `{.accent}` is a list-item colour once the parser reads item attributes: it leaves the text
            now = bool(_ACCENT.search(p.plain)) or (p.style is not None and p.style.color == "accent")
            out.append((_ACCENT.sub("", p.plain), [], now))
        elif out:
            out[-1][1].append(p)
        else:
            return None
    return out or None


def statement_lines(slide: Slide) -> tuple[Any, list[Any]] | None:
    """``(big paragraph, caption paragraphs)`` of ``@statement`` (body text only), else ``None``."""
    els = slide.elements
    if not els or not all(isinstance(e, Text) and e.role == "body" and e.paragraphs for e in els):
        return None
    paras = [p for e in els for p in e.paragraphs]  # type: ignore[union-attr]
    if any(p.marker for p in paras):
        return None
    return paras[0], paras[1:]


def fits(form: str, slide: Slide) -> str | None:
    """``None`` when the slide holds what ``form`` needs, else one sentence saying what is missing."""
    if form in COUNTS:
        lo, hi = COUNTS[form]
        bx = boxes(slide)
        n = len(bx or [])
        word = WORD.get(form, form)
        if bx is None:
            return f"@{word} needs `## ` boxes and nothing else (put other blocks on another slide)"
        if not lo <= n <= hi:
            return (
                f"@{word} needs {lo}-{hi} `## ` boxes, found {n}"
                if lo != hi
                else (f"@{word} needs exactly {lo} `## ` boxes, found {n}")
            )
        return None
    if form == "agenda":
        return (
            None if agenda_items(slide) else "@agenda needs one numbered list (1. 2. 3.) alone on the slide"
        )
    if form == "statement":
        return None if statement_lines(slide) else "@statement needs one or two plain text lines (no list)"
    return None


def check_attrs(form: str | None, attrs: dict[str, Any]) -> list[tuple[str, str, str]]:
    """``(rule, message, hint)`` for slide attributes of the ``@`` line that the form does not take or
    whose value is wrong. Pure; the parser turns them into warnings."""
    out: list[tuple[str, str, str]] = []
    mine = {**{k: None for k in COMMON}, **(KEYS.get(form or "", {}))}
    word = WORD.get(form or "", form)
    for k in ALL_KEYS:
        if k not in attrs or k == "gap":  # gap is a grid key on every slide
            continue
        v = str(attrs[k])
        if form is None:
            owners = [WORD.get(f, f) for f in KEYS if k in KEYS[f]] or ["any form"]
            out.append(
                (
                    "attr-ignored",
                    f"'@' key {k}= has no effect without a form",
                    f"{k}= belongs to "
                    + ", ".join(f"@{o}" for o in owners)
                    + " (and size= fill= to all forms)",
                )
            )
        elif k not in mine:
            take = " ".join(f"{a}=" for a in {**KEYS[form]}) or "no keys of its own"
            out.append(
                (
                    "attr-ignored",
                    f"'@' key {k}= is not used by @{word}",
                    f"@{word} takes {take} (and size= fill= gap=)",
                )
            )
        elif k in KEYS[form] and KEYS[form][k] is not None and v not in KEYS[form][k]:  # type: ignore[operator]
            words = "|".join(KEYS[form][k])  # type: ignore[arg-type]
            out.append(("bad-attr", f"@{word} {k}={v} is not a choice", f"write {k}={words}"))
        elif k == "size":
            try:
                ok = 4 <= float(re.sub(r"pt$", "", v)) <= 400
            except ValueError:
                ok = False
            if not ok:
                out.append(("bad-attr", f"size={v} is not a size in pt", "write size=14 (pt, 4-400)"))
        elif k == "fill" and not [c for c in v.split(",") if c.strip()]:
            out.append(("bad-attr", "fill= is empty", "write fill=primary,#EEF2FF (colors, comma separated)"))
    return out


def num(attrs: dict[str, Any], key: str) -> float | None:
    """A numeric slide attribute (``size=14`` / ``14pt``), ``None`` when absent or unreadable."""
    v = attrs.get(key)
    if v is None:
        return None
    try:
        return float(re.sub(r"pt$", "", str(v)))
    except ValueError:
        return None


def words(attrs: dict[str, Any], form: str, key: str) -> str:
    """The value of a choice attribute, defaulted and validated (a bad value reads as the default)."""
    allowed = KEYS[form].get(key) or ()
    v = str(attrs.get(key, DEFAULTS.get(form, {}).get(key, ""))).lower()
    return v if v in allowed else str(DEFAULTS.get(form, {}).get(key, allowed[0] if allowed else ""))

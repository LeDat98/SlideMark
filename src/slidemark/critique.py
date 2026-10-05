"""Design critic: cheap, geometric "does this slide look good" rules for agents that cannot see.

``critique(deck, placed, theme)`` returns ``Diagnostic``s (level ``info`` or ``warning``, rule names
prefixed ``design-``) whose hints name the change to make in the SlideMark *source*.

Rules:

- ``design-sparse-box``: a card is < 30% filled.
- ``design-wall-of-text``: a text block has > 8 lines, > 90 words or > 180 CJK characters.
- ``design-too-many-blocks``: > 6 blocks on a slide, or text autofitted below the theme minimum size.
- ``design-unbalanced``: in a row of boxes the tallest natural content is >= 3x the shortest.
- ``design-empty-band``: >= 30% of the body height is unused (a non-cover slide); a warning from 45%.
- ``design-no-message`` (info): a body slide with >= 2 boxes and no ``>`` lead.
- ``design-inconsistent-boxes``: sibling boxes whose body font sizes differ by > 15% after autofit.
- ``design-long-title``: the title wraps to 2+ lines.

Score: ``review_score(diags, slides)`` is ``100 - sum(weights) / sqrt(slides)`` clamped to 0..100, where
each ``design-*`` warning costs its rule weight (``WEIGHTS``, 2..8), any other warning 6, an error 15 and
any info 1. Dividing by sqrt(slides) keeps long decks from always scoring 0 while one bad slide
in a short deck still hurts. 100 = nothing to improve; >= 85 is good.
"""

from __future__ import annotations

import math
import re

from .ir import Container, Deck, Diagnostic, Placed, Text
from .layout import measure
from .theme import Theme
from .units import EMU_PER_PT, slide_size, to_emu

SPARSE_FILL = 0.30
WALL_LINES = 8
WALL_WORDS = 90
WALL_CJK = 180
MAX_BLOCKS = 6
UNBALANCED = 3.0
EMPTY_BAND = 0.30  # info from here, warning from EMPTY_BAND_WARN
EMPTY_BAND_WARN = 0.45
FONT_SPREAD = 1.15

WEIGHTS = {
    "design-sparse-box": 5,
    "design-wall-of-text": 8,
    "design-too-many-blocks": 6,
    "design-unbalanced": 4,
    "design-empty-band": 5,
    "design-no-message": 2,
    "design-inconsistent-boxes": 3,
    "design-long-title": 3,
}

_NON_BODY = {"title", "subtitle", "lead", "conclusion", "footnote", "caption", "heading"}
_SPECIAL_LAYOUTS = {"cover", "section", "blank", "center"}
_WORD = re.compile(r"[^\W\d_]+(?:['’-][^\W\d_]+)*|\d+(?:[.,]\d+)*", re.UNICODE)


def _inside(a: Placed, b: Placed) -> bool:
    t = 2
    return a.x >= b.x - t and a.y >= b.y - t and a.x + a.w <= b.x + b.w + t and a.y + a.h <= b.y + b.h + t


def _pad(p: Placed) -> int:
    if p.style.padding is None:
        return 0
    try:
        return to_emu(p.style.padding)
    except ValueError:
        return 0


def _text(p: Placed) -> str:
    return " ".join(q.plain for q in (getattr(p.element, "paragraphs", None) or [])).strip()


def _size(p: Placed, theme: Theme) -> float:
    return (p.style.font_size or theme.sizes.get("body", 18)) * p.font_scale


def _natural_height(p: Placed, scale: float | None = None) -> float:
    """Measured text height (EMU) of ``p``; visuals count as their box."""
    paras = getattr(p.element, "paragraphs", None)
    if not paras:
        return p.h
    pad = _pad(p)
    s = p.font_scale if scale is None else scale
    return (
        measure.paragraphs_height(paras, p.w - 2 * pad, p.style, s, gap=measure.element_gap(p.element))
        + 2 * pad
    )


def _lines(p: Placed, theme: Theme, scale: float | None = None) -> int:
    pad = _pad(p)
    size = _size(p, theme) if scale is None else (p.style.font_size or theme.sizes.get("body", 18)) * scale
    width_pt = (p.w - 2 * pad) / EMU_PER_PT
    total = 0
    for para in p.element.paragraphs:
        bold = bool((para.style and para.style.bold) or p.style.bold)
        indent = measure.list_indent(size, para.level)[0] / EMU_PER_PT if para.marker else 0
        total += measure.count_lines(measure.para_segments(para, bold), width_pt - indent, size, p.style.font)
    return total


def _counts(text: str) -> tuple[int, int]:
    """(Latin words, CJK characters)."""
    cjk = sum(1 for ch in text if measure.is_cjk(ch))
    latin = _WORD.findall("".join(" " if measure.is_cjk(ch) else ch for ch in text))
    return len(latin), cjk


def _cards(items: list[Placed]) -> list[tuple[Placed, list[Placed]]]:
    """Top-level (non-plain) box cards with the non-container items inside them."""
    out = []
    for c in items:
        el = c.element
        if not isinstance(el, Container) or c.h <= 0 or "plain" in el.classes:
            continue
        inner = [p for p in items if p is not c and _inside(p, c) and not isinstance(p.element, Container)]
        if inner:
            out.append((c, inner))
    return out


def _title_of(c: Placed) -> str:
    t = c.element.title
    s = t.paragraphs[0].plain.strip() if t and t.paragraphs else ""
    return s[:20] + "…" if len(s) > 20 else s or "box"


def _rows(cards: list[tuple[Placed, list[Placed]]]) -> list[list[tuple[Placed, list[Placed]]]]:
    """Group cards that start at (nearly) the same y into rows of >= 2 siblings."""
    tol = 4 * int(EMU_PER_PT)
    rows: list[list[tuple[Placed, list[Placed]]]] = []
    for card in sorted(cards, key=lambda c: (c[0].y, c[0].x)):
        for row in rows:
            if abs(row[0][0].y - card[0].y) <= tol:
                row.append(card)
                break
        else:
            rows.append([card])
    return [r for r in rows if len(r) >= 2]


def critique_slide(items: list[Placed], deck: Deck, theme: Theme, index: int) -> list[Diagnostic]:
    out: list[Diagnostic] = []
    slide = deck.slides[index] if index < len(deck.slides) else None
    if slide is None or slide.hidden:
        return out
    try:
        W, H = slide_size(deck.size)
    except ValueError:
        W, H = slide_size("16:9")

    def add(level: str, rule: str, msg: str, hint: str, line: int | None = None) -> None:
        out.append(
            Diagnostic(level=level, message=msg, slide=index + 1, line=line, rule=rule, hint=hint)  # type: ignore[arg-type]
        )

    def role(p: Placed) -> str | None:
        return getattr(p.element, "role", None) if isinstance(p.element, Text) else None

    body = [p for p in items if role(p) not in _NON_BODY - {"heading"} and not _is_field(p)]
    body = [p for p in body if not (isinstance(p.element, Text) and p.element.attrs.get("field"))]
    cards = _cards(items)
    special = (slide.layout in _SPECIAL_LAYOUTS) or not body

    # long title (also on cover/section: those are meant to be short too, but they are big on purpose)
    if not special:
        for p in items:
            if role(p) == "title" and _text(p):
                n = _lines(p, theme, 1.0)  # nominal size: autofit may hide the wrap by shrinking
                if n >= 2:
                    add(
                        "warning",
                        "design-long-title",
                        f"title needs {n} lines"
                        + (f" (shrunk to {p.font_scale:.0%})" if p.font_scale < 1 else ""),
                        "shorten the title to <= ~30 chars (JP <= 20); put detail in the `>` lead",
                        p.element.line,
                    )

    if special:
        return out

    # wall of text
    for p in items:
        if role(p) not in ("body", "quote") or not _text(p):
            continue
        if "callout" in p.element.classes:
            continue
        words, cjk = _counts(_text(p))
        n = _lines(p, theme)
        if n > WALL_LINES or words > WALL_WORDS or cjk > WALL_CJK:
            add(
                "warning",
                "design-wall-of-text",
                f"{n} lines, {words} words" + (f", {cjk} CJK chars" if cjk else "") + " in one block",
                "split into boxes (`##`) or a second slide",
                p.element.line,
            )
            break

    # too many blocks / text below minimum
    n_blocks = len(slide.elements)
    tiny = [p for p in body if _text(p) and _size(p, theme) < theme.min_font_size - 0.05]
    if n_blocks > MAX_BLOCKS:
        add("warning", "design-too-many-blocks", f"{n_blocks} blocks on one slide", "split the slide")
    elif tiny:
        add(
            "warning",
            "design-too-many-blocks",
            f"text shrinks to {_size(tiny[0], theme):.1f}pt (min {theme.min_font_size:g}pt)",
            "split the slide",
            tiny[0].element.line,
        )

    # sparse boxes
    sparse = []
    for c, inner in cards:
        used = sum(min(c.h, _natural_height(p)) for p in inner)
        if used / c.h < SPARSE_FILL:
            sparse.append((c, used / c.h))
    if sparse:
        c, fill = sparse[0]
        add(
            "warning",
            "design-sparse-box",
            f"box '{_title_of(c)}' is {fill:.0%} filled"
            + (f" (+{len(sparse) - 1} more)" if len(sparse) > 1 else ""),
            "merge boxes or add content; or `@` a single column",
            c.element.line,
        )

    rows = _rows(cards)
    # unbalanced rows
    for row in rows:
        if any(
            "kpi" in c.element.classes or any(not getattr(p.element, "paragraphs", None) for p in inner)
            for c, inner in row
        ):
            continue
        nat = [sum(_natural_height(p, 1.0) for p in inner) for _c, inner in row]
        if min(nat) > 0 and max(nat) / min(nat) >= UNBALANCED:
            add(
                "warning",
                "design-unbalanced",
                f"tallest box content is {max(nat) / min(nat):.1f}x the shortest",
                "use `@` ratios (e.g. `@2:1`) or move items between boxes",
                row[0][0].element.line,
            )
            break

    # inconsistent font sizes among siblings
    for row in rows:
        sizes = []
        for _c, inner in row:
            s = [_size(p, theme) for p in inner if role(p) == "body" and _text(p)]
            if s:
                sizes.append(min(s))
        if len(sizes) >= 2 and max(sizes) / min(sizes) > FONT_SPREAD:
            add(
                "warning",
                "design-inconsistent-boxes",
                f"sibling box text sizes differ ({min(sizes):.0f}-{max(sizes):.0f}pt)",
                "shorten the longest box so all boxes share one font size",
                row[0][0].element.line,
            )
            break

    # empty band at the bottom
    top = max((p.y + p.h for p in items if role(p) in ("title", "subtitle", "lead")), default=0)
    limit = H
    for p in items:
        if role(p) in ("conclusion", "footnote", "caption"):
            limit = min(limit, p.y)
    bottom = max((p.y + p.h for p in body), default=top)
    span = limit - top
    if slide.conclusion is None and span > 0 and (limit - bottom) / span >= EMPTY_BAND:
        add(
            "warning" if (limit - bottom) / span >= EMPTY_BAND_WARN else "info",
            "design-empty-band",
            f"{(limit - bottom) / span:.0%} of the body is empty at the bottom",
            "add a `>` conclusion or a chart/table, or grow content",
        )

    # no key message
    if slide.lead is None and sum(isinstance(e, Container) for e in slide.elements) >= 2:
        add(
            "info",
            "design-no-message",
            "no key message under the title",
            "add a `> key message` under the title",
        )
    return out


def _is_field(p: Placed) -> bool:
    return bool(p.element.attrs.get("field"))


def critique(deck: Deck, placed: list[list[Placed]], theme: Theme) -> list[Diagnostic]:
    """Design critique of every slide. ``placed[i]`` is the layout output of slide ``i``. Never raises."""
    out: list[Diagnostic] = []
    measure.set_tokens(theme.layout)
    for i, items in enumerate(placed):
        try:
            out.extend(critique_slide(items, deck, theme, i))
        except Exception as e:  # the critic must never break a review
            out.append(
                Diagnostic(
                    level="info",
                    message=f"critique skipped: {type(e).__name__}: {e}",
                    slide=i + 1,
                    rule="critique-error",
                    hint="report a bug",
                )
            )
    return out


def review_score(diags: list[Diagnostic], slides: int = 1) -> int:
    """0-100 quality score (see the module docstring)."""
    total = 0.0
    for d in diags:
        if d.rule in WEIGHTS:
            total += WEIGHTS[d.rule] if d.level == "warning" else 1
        elif d.level == "error":
            total += 15
        elif d.level == "warning":
            total += 6
        else:
            total += 1
    return max(0, min(100, round(100 - total / math.sqrt(max(slides, 1)))))

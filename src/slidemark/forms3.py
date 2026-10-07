"""DL3d part 2: exact geometry and looks a foreign deck needs, as tokens (``style:`` keys).

======================  ===========================================================================
token                   meaning
======================  ===========================================================================
``steps-arrow.h``       height of the arrow row of ``@steps`` (a length: ``0.45in``)
``steps-card.h``        height of every step card (pinned: no stretch or growth pass changes it)
``steps.gap``           arrow row to card row (default ``layout.steps_gap``)
``conclusion.h``        height of the ``>`` conclusion bar (exact; default = the text's height)
``quote.bar``           colour of a bar on the left edge of the ``@quote`` card (needs a card fill)
``quote.bar_w``         its width (default 0.12in)
``quote.by.align``      ``left|center|right`` for the ``— Name`` line (default = the quote's)
``quote.fill``          the card colour of every ``@quote`` slide (``@quote fill=`` wins)
``quote.h``             card height: a length, or ``full`` = the whole body
``steps-arrow.point``   point depth of every arrow of ``@steps`` / ``@chevron`` as a share of the shorter side
                        (``0.5`` = the PowerPoint preset; default: the layout's ``layout.chevron_adj``)
``box.h``               height of every ``##`` box card on the slide / deck (exact, like ``kpi.h``)
``box.anchor``          ``top`` ``center`` ``bottom``: where the row of box cards sits in the body
``rows-num.shape``      ``square`` (default) ``circle`` ``rounded``: the badge of ``@rows``
``box.num.shape``       ``circle`` (default) ``square`` ``rounded``: the badge of ``@4 num``
======================  ===========================================================================

Fields are theme fields (``Theme`` inherits them), so every token is also a preset key.
"""

from __future__ import annotations

from typing import Any

from pydantic import model_validator

from .forms2 import Forms2Tokens

Length = str | float | int

NUM_SHAPES = {
    "square": "rect",
    "circle": "ellipse",
    "rounded": "rounded-rect",
}
_SHAPE_ALIAS = {
    "rect": "square",
    "rectangle": "square",
    "ellipse": "circle",
    "round": "circle",
    "rounded-rect": "rounded",
    "roundrect": "rounded",
    "rounded_rect": "rounded",
}
ALIGNS = ("left", "center", "right")


class Forms3Tokens(Forms2Tokens):
    """Theme fields of DL3d part 2 (``None`` = derive: the layout decides)."""

    steps_arrow_h: Length | None = None
    steps_card_h: Length | None = None
    steps_gap: Length | None = None
    conclusion_h: Length | None = None
    quote_bar: str | None = None
    quote_bar_w: Length = "0.12in"
    quote_by_align: str | None = None
    quote_fill: str | None = None
    quote_h: Length | None = None
    rows_num_shape: str = "square"
    box_num_shape: str = "circle"
    steps_arrow_point: float | None = None
    box_h: Length | None = None
    box_anchor: str | None = None

    @model_validator(mode="after")
    def _steps_gap(self):  # `steps.gap=` is `layout.steps_gap` for every pass that reads the layout token
        gap = self.steps_gap
        layout = getattr(self, "layout", None)
        if gap and layout is not None and layout.steps_gap != gap:
            self.layout = layout.model_copy(update={"steps_gap": gap})
        point = self.steps_arrow_point
        layout = getattr(self, "layout", None)
        if point and layout is not None and (layout.chevron_adj != point or layout.chevron_adj_min != point):
            # `steps-arrow.point=` is the one point depth: the layout's search over flatter points is off
            self.layout = layout.model_copy(update={"chevron_adj": point, "chevron_adj_min": point})
        return self


_LEN_FIELDS = {
    "steps_arrow_h",
    "steps_card_h",
    "steps_gap",
    "conclusion_h",
    "quote_bar_w",
    "quote_h",
    "box_h",
}
ANCHORS = ("top", "center", "bottom")
_ANCHOR_ALIAS = {"middle": "center", "centre": "center", "mid": "center"}
_COLOR_FIELDS = {"quote_bar", "quote_fill"}
_NONE_WORDS = ("none", "null", "off", "auto")
_KEY = {
    "steps_arrow_h": "steps-arrow.h",
    "steps_card_h": "steps-card.h",
    "rows_num_shape": "rows-num.shape",
    "steps_arrow_point": "steps-arrow.point",
}


def anchor_of(value: str | None) -> str | None:
    """``top`` / ``center`` / ``bottom`` of a ``box.anchor`` value (``middle`` = ``center``), else None."""
    v = (value or "").strip().lower()
    v = _ANCHOR_ALIAS.get(v, v)
    return v if v in ANCHORS else None


def num_shape(value: str | None, default: str) -> str:
    """The ``Shape.shape`` word of a badge token value (``square`` -> ``rect``); unknown = ``default``."""
    v = (value or "").strip().lower()
    return NUM_SHAPES.get(_SHAPE_ALIAS.get(v, v), default)


def normalize(path: str, raw: str, names: set[str] | None) -> list[tuple[str, Any]] | None:
    """Validate one of this module's tokens (``None`` = not one of them). Raises ``theme.TokenValueError``."""
    if path not in Forms3Tokens.model_fields or path in Forms2Tokens.model_fields:
        return None
    from .theme import TokenValueError, _color_value, _length_value, _unquote

    v = _unquote(raw)
    key = _KEY.get(path) or path.replace("_", ".")
    if path in _COLOR_FIELDS:
        if v.lower() in _NONE_WORDS:
            return [(path, None)]
        return [(path, _color_value(raw, names))]
    if path == "quote_h" and v.lower() == "full":
        return [(path, "full")]
    if path in _LEN_FIELDS:
        if path != "quote_bar_w" and v.lower() in _NONE_WORDS:
            return [(path, None)]
        got = _length_value(raw)
        from .units import to_emu

        if to_emu(got, 100) <= 0:
            raise TokenValueError(f"{key} must be above 0", f"write {key}=0.45in (a length), or none")
        return [(path, got)]
    if path in ("rows_num_shape", "box_num_shape"):
        word = _SHAPE_ALIAS.get(v.lower(), v.lower())
        if word not in NUM_SHAPES:
            raise TokenValueError(
                f"{key} is square, circle or rounded", f"write {key}=square (or circle, rounded)"
            )
        return [(path, word)]
    if path == "steps_arrow_point":
        if v.lower() in _NONE_WORDS:
            return [(path, None)]
        try:
            num = float(v[:-1]) / 100 if v.endswith("%") else float(v)
        except ValueError:
            num = -1.0
        if not 0.05 <= num <= 1.0:
            raise TokenValueError(
                "steps-arrow.point is a share of the arrow height between 0.05 and 1",
                "write steps-arrow.point=0.5 (the PowerPoint preset) or 30%",
            )
        return [(path, round(num, 4))]
    if path == "box_anchor":
        if v.lower() in _NONE_WORDS:
            return [(path, None)]
        word = anchor_of(v)
        if word is None:
            raise TokenValueError("box.anchor is top, center or bottom", "write box.anchor=top")
        return [(path, word)]
    if path == "quote_by_align":
        if v.lower() in _NONE_WORDS:
            return [(path, None)]
        if v.lower() not in ALIGNS:
            raise TokenValueError("quote.by.align is left, center or right", "write quote.by.align=right")
        return [(path, v.lower())]
    return None

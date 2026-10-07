"""Composition vocabulary, part 2 (DL3b lane K): the words, their secondary attributes and their tokens.

One ``@word`` slide directive per form, secondary attributes on the same line, a ``<word>.*`` token for every
fill, line and size. The composers live in ``layout/forms2.py`` (a composed slide body on a copy of the slide:
the parsed Deck stays as written), the importer folds in ``importer/forms2.py`` (named shapes -> the same
words), this module holds what the parser, the theme and the build feedback share.

======= ============================================ =============================================
word    source                                       secondary attributes
======= ============================================ =============================================
iconlist  ``- icon=bolt **Title** text`` items       ``cols=1..3``
quote     ``>`` block or body text, ``— name`` last  ``align=left|center|right``
split     image (or ``fill=`` block) + text          ``side=left|right ratio=1:1 bleed=on fit=``
proscons  two ``##`` boxes with ``+`` / ``−`` items  (a trailing ``>`` is the verdict bar)
progress  ``- label 72%`` or a table label,value     ``max=100``
harvey    a table of 0-4 or 0/25/50/75/100%          (headers stay text)
heatmap   a numeric table                            ``min= max= colors=a,b text=auto|on|off``
pins      image + ``- x=32% y=58% label`` items      ``legend=right|bottom|off``
======= ============================================ =============================================

Every form takes the generic slide attributes ``gap=`` (the slide's own), ``size=`` (text, pt) and ``fill=``.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from typing import Any

from pydantic import BaseModel, ConfigDict

Length = str | float | int

WORDS: tuple[str, ...] = (
    "iconlist",
    "quote",
    "split",
    "proscons",
    "pros",
    "progress",
    "harvey",
    "heatmap",
    "pins",
)
ALIAS = {"pros": "proscons"}  # `@pros` is `@proscons`

GENERIC = ("size", "fill")
KEYS_BY_WORD: dict[str, tuple[str, ...]] = {
    "iconlist": ("cols", *GENERIC),
    "quote": ("align", *GENERIC),
    "split": ("side", "ratio", "bleed", "fit", *GENERIC),
    "proscons": GENERIC,
    "progress": ("max", *GENERIC),
    "harvey": GENERIC,
    "heatmap": ("min", "max", "colors", "text", *GENERIC),
    "pins": ("legend", *GENERIC),
}
KEYS: tuple[str, ...] = tuple(dict.fromkeys(k for ks in KEYS_BY_WORD.values() for k in ks))

# what a key may hold, for the bad-value hint
VALUES: dict[str, str] = {
    "cols": "1, 2 or 3 (columns)",
    "align": "left, center or right",
    "side": "left or right (the side the image is on)",
    "ratio": "image:text as two numbers, e.g. 1:1 or 2:3",
    "bleed": "on or off",
    "fit": "cover, contain or stretch",
    "max": "a number, e.g. 100",
    "min": "a number, e.g. 0",
    "colors": "two or more colors, e.g. #F3F6FA,primary",
    "text": "auto, on or off",
    "legend": "right, bottom or off",
    "size": "a font size in pt, e.g. 24",
    "fill": "a color, e.g. primary or #E8EEF7",
}


def word_of(classes: list[str]) -> str | None:
    """The composition word a slide carries (``pros`` reads as ``proscons``), else ``None``."""
    for c in classes:
        if c in WORDS:
            return ALIAS.get(c, c)
    return None


def check_at(classes: list[str], attrs: dict[str, str], warn: Callable[[str, str, str], None]) -> None:
    """``@`` line check: a secondary attribute the form does not take warns (``warn(msg, rule, hint)``)."""
    word = word_of(classes)
    for k in attrs:
        if k not in KEYS:
            continue  # unknown keys are the parser's own diagnostic
        if word is None:
            warn(
                f"'{k}=' on the @ line has no form to act on",
                "unknown-token",
                "write it after a form word: @iconlist cols=2, @quote align=center, @progress max=100",
            )
        elif k not in KEYS_BY_WORD[word]:
            warn(
                f"'{k}=' is not an @{word} attribute",
                "unknown-token",
                f"@{word} takes: {' '.join(KEYS_BY_WORD[word])}",
            )


# --------------------------------------------------------------------------- tokens


class Forms2Tokens(BaseModel):
    """Theme fields of the composition forms (``style: iconlist.icon.size=0.5in``). ``None`` = derive."""

    model_config = ConfigDict(extra="forbid")

    # @iconlist
    iconlist_icon_size: Length | None = None  # icon edge (None = ``iconlist_icon_ratio`` x the title size)
    iconlist_icon_color: str | None = None  # None = primary
    iconlist_gap: Length | None = None  # icon to text (None = ``iconlist_gap_ratio`` x the icon)
    iconlist_icon_ratio: float = 2.2
    iconlist_gap_ratio: float = 0.45
    iconlist_row_air: float = 1.6  # a row is at most this x its tallest item (the block centres in the body)
    iconlist_text_ratio: float = 0.85  # text size / title size
    # @quote
    quote_size: float | None = None  # pt; None = the largest size that fits, up to ``quote_grow`` x body
    quote_grow: float = 2.4
    quote_mark: str = "“"
    quote_mark_color: str | None = None  # None = accent
    quote_mark_ratio: float = 2.6  # mark size / quote size
    quote_by_color: str | None = None  # None = muted
    quote_by_ratio: float = 0.55  # attribution size / quote size
    quote_width: float = 0.82  # share of the body width the text may take
    quote_mark_leading: float = 0.7  # line spacing of the mark glyph (its box hugs the glyph)
    # @split
    split_gap: Length | None = None  # image to text (None = the theme gap)
    split_fill: str | None = None  # colour block when there is no image (None = surface)
    split_ratio: str = "1:1"  # image : text
    # @proscons
    proscons_plus_color: str | None = None  # None = success
    proscons_minus_color: str | None = None  # None = danger
    proscons_plus: str = "+"
    proscons_minus: str = "−"
    proscons_gap: Length | None = None  # between the two boxes (None = the slide gap)
    proscons_head_ratio: float = 1.1  # heading size / item size
    proscons_air: float = 1.35  # the cards are at most this x their content (the pair centres in the body)
    # @progress
    progress_fill: str | None = None  # bar color (None = primary)
    progress_track: str | None = None  # track color (None = surface); none = no track
    progress_h: Length | None = None  # bar height (None = ``progress_h_ratio`` x the label size)
    progress_label_size: float | None = None  # pt; None = the largest that fits
    progress_h_ratio: float = 0.9
    progress_label_w: float = 0.3  # share of the width the labels take
    progress_value_w: float = 0.1  # share of the width the value text takes
    progress_max_pt: float = 26  # largest label size (pt) of the automatic fit
    # @harvey
    harvey_size: Length | None = None  # ball diameter (None = ``harvey_ratio`` x the row height)
    harvey_fill: str | None = None  # None = primary
    harvey_line: str | None = None  # ball outline (None = the fill)
    harvey_line_w: float = 1.25  # pt
    harvey_ratio: float = 0.55
    harvey_head_w: float = 0.28  # share of the width the row labels take
    harvey_band: str | None = None  # zebra band behind every other body row (None = surface); none = off
    # @heatmap
    heatmap_colors: str = "surface,primary"  # the two ends (or more stops) of the scale
    heatmap_text: str = "auto"  # auto = ink picked per cell; on = the table ink; off = no numbers
    # @pins
    pins_fill: str | None = None  # None = accent
    pins_color: str | None = None  # number ink (None = readable on the fill)
    pins_size: Length | None = None  # circle diameter (None = ``pins_ratio`` x the image's short side)
    pins_ratio: float = 0.085
    pins_legend: str = "right"  # right | bottom | off
    pins_legend_w: float = 0.36  # share of the body width the right legend takes


_ENUMS = {
    "heatmap_text": ("auto", "on", "off"),
    "pins_legend": ("right", "bottom", "off"),
}
_COLOR_FIELDS = {
    "iconlist_icon_color",
    "quote_mark_color",
    "quote_by_color",
    "split_fill",
    "proscons_plus_color",
    "proscons_minus_color",
    "progress_fill",
    "progress_track",
    "harvey_fill",
    "harvey_line",
    "harvey_band",
    "pins_fill",
    "pins_color",
}
_PT_FIELDS = {"quote_size", "progress_label_size"}
_NONE_WORDS = ("none", "null", "off")


def normalize(path: str, raw: str, names: set[str] | None) -> list[tuple[str, Any]] | None:
    """Validate one of this module's tokens (``None`` = not one of them: the generic rules apply).

    Raises ``theme.TokenValueError`` (message + one-line hint) on a bad value."""
    if path not in Forms2Tokens.model_fields:
        return None
    from .theme import TokenValueError, _color_value, _pt_value, _unquote

    v = _unquote(raw)
    if path in _COLOR_FIELDS:
        if v.lower() in _NONE_WORDS:
            return [(path, "none")]
        return [(path, _color_value(raw, names))]
    if path in _PT_FIELDS:
        return [(path, _pt_value(raw))]
    if path in _ENUMS:
        if v.lower() not in _ENUMS[path]:
            word = path.split("_", 1)
            raise TokenValueError(
                f"{word[0]}.{word[1]} is {' / '.join(_ENUMS[path])}",
                f"write {word[0]}.{word[1]}={_ENUMS[path][0]} (or {', '.join(_ENUMS[path][1:])})",
            )
        return [(path, v.lower())]
    if path == "heatmap_colors":
        items = [p.strip() for p in v.split(",") if p.strip()]
        if len(items) < 2:
            raise TokenValueError(
                "heatmap.colors needs two or more colors", "write heatmap.colors=#F3F6FA,primary"
            )
        return [(path, ",".join(_color_value(p, names) for p in items))]
    if path == "split_ratio":
        if not RATIO.fullmatch(v):
            raise TokenValueError("split.ratio is image:text", "write split.ratio=1:1 (or 2:3)")
        return [(path, v)]
    return None


RATIO = re.compile(r"\d+(?:\.\d+)?:\d+(?:\.\d+)?")

# --------------------------------------------------------------------------- build feedback


def _needs(*words: str) -> Callable[[Any], bool]:
    def has(facts: Any) -> bool:
        return any(w in s.classes for s in facts.deck.slides for w in words)

    return has


# (pattern over the lower-cased ``style:`` key, what the deck needs, hint): appended to honour.STYLE_NEEDS
STYLE_NEEDS: list[tuple[re.Pattern[str], Callable[[Any], bool], str]] = [
    (re.compile(r"^iconlist[.-]"), _needs("iconlist"), "no @iconlist slide in the deck: `@iconlist cols=2`"),
    (re.compile(r"^quote[.-]"), _needs("quote"), "no @quote slide in the deck: `@quote` before a > block"),
    (re.compile(r"^split[.-]"), _needs("split"), "no @split slide in the deck: `@split side=left`"),
    (
        re.compile(r"^(proscons|pros)[.-]"),
        _needs("proscons", "pros"),
        "no @proscons slide in the deck: `@proscons` before two ## boxes",
    ),
    (
        re.compile(r"^progress[.-]"),
        _needs("progress"),
        "no @progress slide in the deck: `@progress` before a `- label 72%` list",
    ),
    (re.compile(r"^harvey[.-]"), _needs("harvey"), "no @harvey slide in the deck: `@harvey` before a table"),
    (
        re.compile(r"^heatmap[.-]"),
        _needs("heatmap"),
        "no @heatmap slide in the deck: `@heatmap` before a numeric table",
    ),
    (re.compile(r"^pins[.-]"), _needs("pins"), "no @pins slide in the deck: `@pins` before an image + list"),
]

# fit-line name of a form
FIT_NAMES = {
    "iconlist": "icon list",
    "quote": "quote",
    "split": "split",
    "proscons": "pros / cons",
    "progress": "progress bars",
    "harvey": "harvey balls",
    "heatmap": "heatmap",
    "pins": "map pins",
}

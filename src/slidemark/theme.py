"""Theme model: the public design-token schema shared by layout (sizes, spacing) and renderer (colors, fonts).

Design freedom (docs/DESIGN_FREEDOM.md): SlideMark ships mechanisms, not looks. Every visual decision is a
token in this schema. Built-in themes are YAML presets in ``presets/`` written in the same schema an agent can
write (``theme: ./brand.yaml``) or override inline with header lines (``colors:``, ``fonts:``, ``sizes:``,
``style:``, see :func:`apply_tokens`). ``theme: none`` is the bare schema defaults (a neutral canvas).
"""

from __future__ import annotations

import copy
import difflib
import re
from functools import cache
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator, model_validator

from .contrast import best_ink, nearest_passing, ratio
from .forms4 import Forms4Tokens
from .ir import Diagnostic, Length, Style

PRESET_DIR = Path(__file__).parent / "presets"


_OFF = ("off", "no", "false")
_ON = ("on", "yes", "true")


def _coerce_bools(cls, data):
    """`style: layout.x=off` reaches the model as None (see ``_value``): bool fields read None/off/no/false
    as False and on/yes/true as True."""
    if not isinstance(data, dict):
        return data
    out = dict(data)
    for name, f in cls.model_fields.items():
        if f.annotation is not bool or name not in out:
            continue
        v = out[name]
        if v is None or (isinstance(v, str) and v.strip().lower() in _OFF):
            out[name] = False
        elif isinstance(v, str) and v.strip().lower() in _ON:
            out[name] = True
    return out


class Fonts(BaseModel):
    model_config = ConfigDict(extra="forbid")

    heading: str = "Calibri"
    body: str = "Calibri"
    mono: str = "Consolas"
    ea: str = "Yu Gothic"  # East Asian typeface for ja/zh/ko text (written to <a:ea>)


class LayoutTokens(BaseModel):
    """Layout constants that change the look (gaps, line heights, component sizes, growth limits).

    Lengths are ``Length`` strings (bare numbers = pt); ratios are plain floats. Defaults reproduce the
    original look. Algorithm internals (search weights, step lists, tolerances) are not tokens.
    """

    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="before")
    @classmethod
    def _bools(cls, data):
        return _coerce_bools(cls, data)

    top_gap: Length = "0.25in"  # title band (or lead) -> body, the same on every slide
    line_latin: float = 1.2  # line height / font size for Latin text
    line_cjk: float = 1.3  # ... for CJK text
    para_gap: float = 0.25  # space before every paragraph but the first, x font size
    cell_pad_x: Length = "0.1in"  # table cell margins
    cell_pad_y: Length = "0.05in"
    dense_tight: float = 0.7  # gap / padding factor on dense slides
    kpi_min_h: Length = "1.1in"
    z_default: int = 5  # stacking level of a shape without `{z=}` (z=1 sits behind it, z=9 in front, 1..9)
    icon_head: float = 1.2  # icon side / heading font size
    icon_kpi: float = 2.0  # icon side / kpi label font size
    icon_gap: float = 0.4  # gap between icon and text, in icon sides
    chevron_adj: float = 0.3  # chevron point depth / shorter side
    chevron_adj_min: float = 0.16  # flattest point depth the layout may choose to widen the text area
    chevron_text_share: float = 0.6  # text area >= this share of the chevron width
    chevron_adj_step: float = 0.02  # step of that search
    chevron_word_slack: float = 1.08  # a word must fit this much narrower (wider fonts)
    chevron_head_min_steps: int = 5  # rows of this many chevrons keep each bold heading on one line ...
    chevron_head_lines: int = (
        2  # ... a heading that does not fit one line wraps at a space to this many lines ...
    )
    chevron_head_keep: float = (
        0.9  # ... it stays on one line when that costs at most 1 - this of the size ...
    )
    chevron_head_min_scale: float = 0.7  # ... shrinking the text at most to this share of the base size
    chevron_head_slack: float = 1.25  # a heading must fit this much narrower (DejaVu-like fallback fonts)
    chevron_cjk_slack: float = (
        1.25  # a CJK chevron line must fit this much narrower (fallback fonts), else shrink
    )
    chevron_fill_share: float = (
        0.66  # a lone chevron row (top-anchored) is this share of the body tall at least
    )
    chevron_text_max_pt: float = 26  # a lone chevron row grows its text up to this size (pt), 0 = off ...
    chevron_text_fill: float = 0.6  # ... while the text block stays within this share of the chevron height
    chevron_pad: Length = "4pt"
    chevron_min_h: Length = "0.7in"
    chevron_max_h: Length = "1.3in"
    chevron_vpad: Length = "0.17in"
    footnote_max: float = 0.2  # footnotes never take more than this share of the slide height
    math_grow: float = 1.6  # an equation alone in its cell is this much larger than body text
    cjk_orphan_chars: int = 2  # a CJK paragraph whose last line holds at most this many characters ...
    cjk_squeeze_max: float = (
        0.15  # ... gets up to this much negative letter spacing (em) to pull it back; 0 = off
    )
    cjk_squeeze_margin: float = 0.01  # ... and the pulled-back line must fit this much narrower
    cjk_squeeze_fill: float = (
        0.9  # nearly full lines (would wrap a short tail at this share of the width) ...
    )
    cjk_squeeze_tail: int = (
        4  # ... with at most this many characters on the last line are squeezed too; 0 = off
    )
    cjk_latin_gap: float = (
        0.3  # LibreOffice adds this much space (em) where CJK and Latin text touch; the squeeze counts it
    )
    cjk_phrase_break: bool = True  # CJK paragraphs wrap at phrase boundaries (soft breaks, render only)
    cjk_phrase_margin: float = 0.02  # ... and every phrase line must fit this much narrower
    bind_margin: float = 0.12  # a no-break binding wider than a line minus this share is undone (render)
    cjk_phrase_slack: float = 0.07  # ... also when a viewer with this much more room would break inside one
    cjk_unit_join: bool = True  # Japanese numbers stay with their units (38万円, ▲8%): U+2060 joiners
    grow: bool = True  # sparse slides grow text / cards to fill the body (False = keep nominal sizes)
    box_pad: Length = "10pt"  # inner padding of a box whose style has none
    # --- icons and chevrons
    chevron_max_alone: Length = "2.0in"  # a chevron row that is all the slide holds may be this tall ...
    chevron_alone_share: float = 0.28  # ... aiming at this share of the body height
    # --- growth of sparse slides (ratios of the nominal size)
    code_grow: float = 1.25  # code text grows up to this factor
    table_grow: float = 1.4  # rows of a table with spare room grow up to this factor
    table_font_grow: float = 1.2  # table text grows up to this factor
    table_alone_grow: float = 2.6  # a table alone on a normal slide: rows grow up to this factor ...
    table_alone_font_grow: float = 1.45  # ... and its text up to this factor
    kpi_text_grow: bool = True  # free text under a KPI row grows with the sparse-slide growth (box-text size)
    kpi_grow_max: float = 1.7  # a KPI card beside free text grows its text up to this factor (1 = never)
    table_fill_width: bool = True  # a lone body table spans the full width
    table_row_max_em: float = 3.6  # grown table rows <= this x the text size (0 = off)
    table_text_max: float = (
        1.6  # a table with room grows its text first, up to this x the theme body size ...
    )
    table_wrap_ratio: float = 1.0  # table text below this x body size may wrap cells at spaces (0 = off)
    card_table_balance: bool = (
        True  # normal density: cards above a table spread their items to the card height (no hollow cards)
    )
    sparse_cards_top: bool = (
        True  # normal density: a sparse row of text cards is top-anchored under the lead (no floating block)
    )
    table_text_step: float = 0.05  # ... in steps of this factor (never beyond sparse_text_max_pt; 0 = off)
    table_grow_roomy: float = 2.0  # table rows grow up to this factor when a quarter of the body stays empty
    tree_slack_roomy: float = 1.15  # org-tree boxes may be this much taller than their content (roomy slides)
    tree_slack: float = 1.15  # org-tree boxes are at most this much taller than their content
    html_footer: bool = False  # True: the deck `footer:` and `num:` are drawn on `@html` slides too
    html_fit: bool = False  # True: a lone HTML block fills the body height (stretch, else center)
    html_zoom_max: float = 1.5  # a short HTML block renders zoomed up to this factor (1 = off)
    roomy_left: float = 0.25  # share of the body left empty that triggers the roomy pass
    roomy_grow: float = 1.2  # the roomy pass grows box / tree text by up to this factor more
    roomy_grow_dense: float = 1.6  # dense slides: sparse cards may grow text this much more
    dense_roomy_body: float = 1.25  # dense slides: body text stays at most this multiple of the body size
    roomy_row: float = 0.86  # a lone row of boxes reaches this share of the body height
    roomy_row_air: float = 1.9  # ... but never taller than this multiple of the natural height
    balance_air: float = (
        1.15  # normal density: a lone row of boxes may grow to this multiple of its height (0 = off)
    )
    balance_text_air: float = 1.15  # ... while its text still grows, cards stay within this multiple
    balance_max_pt: float = 36  # ... but body text never beyond this size (pt)
    balance_grow: float = 1.25  # ... its text may also grow by up to this factor (no new wrapped lines)
    balance_row: float = 0.85  # ... but never beyond this share of the body
    balance_shift: float = 0.0  # ... and the part of the rest above the 20% band that moves the block down
    balance_left: float = 0.2  # ... when more than this share of the body would stay empty
    roomy_row_air_dense: float = 1.15  # ... dense slides
    peer_step: float = 1.12  # table text is at most this much smaller than the box text on the same slide
    beside_min: float = 0.5  # a box beside a chart / image is at least this share of the visual height
    beside_fill: float = 0.6  # ... a shorter one grows by this share of the way to that minimum
    beside_slack: float = 1.12  # ... headroom over the natural height
    full_width: float = 0.6  # a table wider than this share of the slide width is a full-width table
    row_slack: float = 1.35  # a grid row is at most this much taller than its tallest content
    row_min_tail: float = 0.12  # min row height share of the body when blocks follow the grid
    stack_min: float = 0.4  # stacked boxes beside a tall block: min share of the natural total each
    row_min_dense: float = 0.3  # dense slides: a lone row of boxes is at least this share of the body
    row_min: float = 0.3  # any other row is at least this share of the body
    grow_small: float = (
        1.35  # sparse slides: text grows up to this factor when the body size <= grow_small_pt
    )
    grow_small_pt: float = 14
    grow_big: float = 1.15  # ... and up to this factor for larger themes
    grow_very_sparse: float = 1.4  # very sparse boxes grow up to this factor ...
    grow_very_sparse_pt: float = 16  # ... when the theme body size is at least this
    grow_very_sparse_max_pt: float = 26  # ... but never beyond this body size
    grow_head: float = 1.25  # box headings grow along with the body text, up to this factor
    head_body: float = 1.05  # a box heading is at least this much x the (grown) body text of its box
    room_free: float = 0.35  # a card with more than this share of its inner height free spreads paragraphs
    room_use: float = 0.6  # ... using this share of the free height
    room_gap_max: float = 0.6  # ... up to this space-before (em) per paragraph
    room_gap_max_dense: float = 0.9  # ... dense slides
    slide_peer_step: float = 1.12  # slide-level text is at most this much smaller than the box text beside it
    grow_fill: float = 0.85  # growth stops when the content would fill more than this share of the grid
    grow_box_fill: float = 0.92  # ... or more than this share of a box
    left_keep: float = 0.12  # rows of a sparse slide expand until at most this share of the body is left
    very_sparse_fill: float = 0.4  # content below this share of the body is "very sparse" and may move down
    left_shift: float = 1 / 3  # ... by at most this share of the leftover (boxes)
    left_shift_table: float = 0.2  # ... or this share (slides without boxes)
    dense_grow_body: float = 1.25  # dense slides: text may grow up to this multiple of the body size
    diagram_grow: float = 1.6  # a diagram on a sparse slide grows its nodes up to this factor
    diagram_fill: float = 0.85  # ... while it fills at most this share of the height it has
    # --- hugging cards (consulting / dense slides)
    row_slack_hug: float = (
        1.1  # consulting / dense slides: a grid row is at most this much taller than its content
    )
    row_min_hug: float = 0.12  # consulting / dense slides: a grid row is at least this share of the body
    beside_align: float = (
        0.4  # a box beside a chart / image whose content fills this share of the visual is as tall as it
    )
    hug_shift: float = (
        0.0  # share of the leftover body (beyond left_keep) that moves a card block down (0 = off)
    )
    grow_normal_max: float = (
        1.3  # normal-density slides: body text never grows beyond this factor (dense: dense_*_body)
    )
    grow_max: float = (
        1.5  # deck-wide ceiling: no growth pass takes text beyond this x its role size (1 = no growth)
    )
    sparse_note: float = (
        0.35  # a slide whose body stays more than this share empty after growth gets `sparse: N% free`
    )
    center_beside: bool = (
        False  # True: a card as tall as the chart / image beside it centers its content vertically
    )
    hug_cards: bool = True  # cards are as tall as their content (row_slack_hug)
    # --- sparse step: a slide whose content fills less than sparse_fill of the body takes ONE step up
    sparse_fill: float = (
        0.55  # content fills less than this share of the body: the slide sets the deck's step
    )
    sparse_fill_soft: float = 0.65  # ... below this share it takes the deck's step when that fits
    sparse_step: float = 1.25  # text, paddings, chevrons and table text of such a slide grow by this factor
    sparse_step_min: float = 1.15  # ... or this one when the larger step overflows / wraps more lines
    sparse_max_pt: float = 20  # ... but body text never beyond this size (pt)
    sparse_para_gap: float = 0.6  # paragraph gap (em) of a card at the sparse step
    callout_pad_min: Length = "6pt"  # a callout / note box has at least this padding on every side
    callout_box_pad: Length = "8pt"  # ... inside a box / card it has at least this (left: + the accent bar)
    callout_text_step: float = (
        1.15  # ... a callout in a box grows with the box text, at most this much smaller
    )
    callout_bar_w: Length = "4pt"  # ... width of its left accent bar
    cover_title_y: float = (
        0.42  # cover: the title (+ subtitle) block is centred on this share of the slide height (0 = off)
    )
    cover_title_max_pt: float = (
        60  # ... and the title grows to fill its area up to this size (pt), never wrapping more
    )
    conclusion_gap: float = (
        1.0  # air between the body (cards) and the conclusion bar, in card gutters (theme gap)
    )
    conclusion_foot_gap: Length = "0.12in"  # air between a conclusion bar and the footnote line under it
    footnote_gap: Length = "0.14in"  # min air between a chart (legend included) and the footnote band
    body_size_unify: bool = True  # table text on a slide with boxes is never smaller than the box body text
    unify_max: float = 1.3  # ... lifting a table by more than this factor is refused
    reserve_lead: Literal["auto", "on", "off"] = (
        "auto"  # slides without a lead keep its slot (auto: >= half have one)
    )
    # --- vertical balance of the body (consulting rhythm)
    body_free_max: float = 0.2  # more than this share of the body free: spread it, then center the block
    body_valign: Literal["top", "center", "auto"] = (
        "auto"  # auto: center while free space above body_free_max
    )
    body_spread_max: float = 0.4  # table rows, chevron rows and row gaps grow by at most this share first
    center_min_fill: float = 0.6  # a block filling less than this share of the body is never centered
    card_stretch: bool = False  # ... its cards may stretch (off: tails over a quarter of the card; see tests)
    card_stretch_share: float = (
        0.5  # ... by at most this share of body_spread_max (stretched cards look empty)
    )
    card_pad_share: float = (
        0.25  # ... cards of such a block stretch; this share of the growth moves the body down
    )
    sparse_step_max: float = 1.5  # ... it first tries steps up to this factor (text, nodes, paddings)
    sparse_low_max_pt: float = 24  # ... body text of such a slide may reach this size (pt)
    # --- sparse completion: a slide that still leaves more than sparse_left_max of the body empty
    sparse_left_max: float = 0.35  # ... grows text / cards / chevrons, then moves the block down (0 = off)
    sparse_left_target: float = 0.3  # ... the band below the block is brought down to this share of the body
    sparse_text_max_pt: float = (
        28  # ... body text may reach this size (pt), at most sparse_step_max x the theme body
    )
    sparse_row_gap_max: Length = "0.5in"  # ... rows of blocks move apart by at most this much per gap, first
    kpi_fit_margin: float = 0.9  # ... a grown KPI number fills at most this share of the width it fits in
    sparse_air: float = 0.8  # ... paragraph gap (em) of plain body text, at most (lists on a sparse slide)
    sparse_card_air: float = 1.15  # ... a lone row of cards may reach this multiple of its natural height
    sparse_kpi_air: float = 1.15  # ... KPI cards may be this much taller than their content
    sparse_lead_grow: float = 1.4  # ... the lead line grows with the body text, at most this factor ...
    sparse_lead_title_max: float = 0.65  # ... and never beyond this share of the title size (stays secondary)
    sparse_footnote_grow: float = 1.2  # ... footnotes may grow by at most this factor
    chevron_alone_share_sparse: float = (
        0.4  # ... a chevron row alone aims at this share of the body height ...
    )
    chevron_max_alone_sparse: Length = "2.8in"  # ... up to this height
    # --- L3 fill: a sparse row of text cards / a text panel beside a chart uses the height it has
    l3_fill: bool = True  # False: cards and panels keep their natural height (no stretch, no spread)
    sparse_row_bottom_band: float = (
        0.12  # ... a lone card row stays under the lead and ends this share of the body above its bottom
    )
    l3_gap_extra: float = (
        1.2  # ... paragraphs of such a card / panel spread by at most this much per gap (em)
    )
    l3_gap_extra_numbered: float = 1.8  # ... the same for numbered items (decisions)
    panel_fill_min: float = 0.7  # ... a panel beside a chart whose content fills less of it is spread
    l3_tail_max: float = 0.25  # ... a text card of a lone row keeps at most this share of its height empty
    l3_tail_aim: float = (
        0.22  # ... a row shortened to meet it aims at this share (rounding stays within the limit)
    )
    l3_grow_step: float = 0.05  # ... its text grows in steps of this factor (CJK wrap guard stays on) ...
    l3_body_head_max: float = 1.2  # ... up to this multiple of the card heading size (and sparse_text_max_pt)
    l3_gap_extra_short: float = 3.0  # ... lists of at most l3_short_items items may spread this much (em) ...
    l3_wrap_margin: float = 0.12  # ... grown text must also fit this much narrower (renderers wrap earlier)
    l3_text_max_pt: float = 20  # ... card / panel body text of such a slide may grow up to this size (pt)
    chart_plot_top_em: float = (
        3.5  # ... a chart with a title: its plot area starts this many title sizes below the chart top
    )
    # --- chart takeaway (`note=` / `hl=`): the plot area is pinned (manualLayout): the pointer hits the bar
    chart_note_title_em: float = 3.0  # plot top below the chart top with a title (x chart text size)
    chart_note_top_em: float = 1.0  # ... without a title
    chart_note_legend_em: float = 1.8  # room a top / bottom legend takes
    chart_note_axis_em: float = 2.0  # room of the labels under the plot
    chart_note_val_em: float = 1.2  # air beside the axis labels at the left (axis on)
    chart_note_edge_em: float = 1.0  # air at the left / right chart edge
    chart_note_max_w: float = 0.62  # a note is at most this share of the plot width
    chart_note_gap_em: float = 0.5  # air between the note and bars / labels
    chart_note_inset_em: float = 1.0  # air between the note and the top of the plot (the chart title / axis)
    chart_note_slack: float = (
        1.12  # a note's text width is estimated this much wider (bold CJK + latin spacing)
    )
    chart_note_line_em: float = 1.2  # shortest pointer line (x chart text size)
    chart_note_land_em: float = 1.0  # a pointer dropping onto a horizontal bar lands this far inside its end
    chart_note_shrink_pt: float = 1.0  # a note may shrink this much (pt) to sit clearly nearer its bar
    panel_to_visual: bool = (
        True  # a hollow panel beside a chart spans it: top at the plot top, bottom at the chart's
    )
    panel_top_plot: bool = (
        False  # ... True: its top meets the plot area of a titled chart (default: the chart top)
    )
    l3_gap_cap: float = 0.8  # ... paragraph gaps never exceed this extra (em): one even rhythm, no stretching
    l3_head_pad: float = 0.35  # ... air (em) between a card heading band and its first item
    l3_panel_shrink: float = (
        0.9  # ... a sparse panel gives back this share of its empty height (ends at its content)
    )
    cards_to_bar: bool = True  # cards (row / grid) above a conclusion bar stretch down to it
    card_hollow_fill: float = 0.5  # ... a stretched card filled less than this spreads its items
    card_stretch_min_fill: float = 0.35  # ... cards that would stay under this filled keep hugging
    card_hollow_gap_cap: float = 2.0  # ... by at most this extra paragraph gap (em), instead of one dead band
    card_spread_fill: float = (
        0.8  # a stretched card filled less than this after growth spreads its items (0 = off)
    )
    card_spread_gap_max: float = 2.2  # ... with equal gaps of at most this many em; the rest centers the list
    panel_end_air: float = (
        0.08  # a ruled panel beside a chart ends under its note if > this share of its span is empty
    )
    panel_end_max: float = 0.2  # ... but only up to this share (a much emptier panel keeps the chart's span)
    card_align_rows: bool = True  # ... cards in one row share gap and lead: item / rule k sits at one height
    card_spread_ratio: float = 1.7  # ... a card's gap is at most this multiple of the smallest gap in its row
    card_spread_tail: float = 0.0  # ... em of air kept between the last item and the card bottom padding
    card_text_max: float = (
        18  # ... card list / paragraph text grows at most to this size (pt), never below the theme size
    )
    card_spread_rules: bool = (
        True  # ... spread items of a stretched card get a thin rule (theme border) between them
    )
    l3_short_items: int = 4  # ... before the row is shortened to meet l3_tail_max (top-anchored)
    # --- org charts / issue trees (slide-level a>b links) and compact table headers
    tree_fill: float = (
        0.92  # a linked tree grows (top-anchored) until it fills this share of the body (0 = off)
    )
    tree_box_grow: float = 1.6  # ... its boxes become at most this much taller ...
    tree_gap_grow: float = 6.0  # ... and the connector gaps between levels at most this much larger
    tree_text_max: float = 1.4  # ... box text steps up by at most this factor (body <= l3_text_max_pt)
    tree_hug: bool = True  # ... a box hugs its text (even padding above and below); the rest goes to the gaps
    tree_box_air: float = (
        1.08  # ... but a box is at most this much taller than its text (the rest goes to the gaps)
    )
    tree_box_air_max: float = (
        1.2  # ... up to this much once the gaps are at their cap (the tree then fills the body)
    )
    tree_parent_span: float = 0.5  # a parent is at least this share of its children's span wide (never wider)
    tree_pad_share: float = 0.5  # ... and this share of the height the text leaves free moves the body down
    tree_wide: float = 1.3  # ... a lone box of a level (the root) may be this much wider ...
    tree_wide_max: float = 0.6  # ... but never beyond this share of the body width
    tree_head_fit: float = 0.75  # ... unless its heading needs more to stay on one line (share of body width)
    table_header_max: float = (
        1.4  # a stretched table keeps header rows <= this x their natural height (0 = off)
    )
    gantt_pad: float = 3.0  # pt: a `.gantt` bar is inset this much from its cell range (left / right)
    gantt_bar: float = 0.66  # a `.gantt` bar is this share of its row high, centered in the row
    gantt_even: bool = True  # `.gantt` period columns get equal widths (label column kept) when text fits
    # --- stretched tables and badges (vfill / render)
    table_comfort_em: float = (
        2.7  # a table whose rows end up taller than this x text grows its text (0 = off) ...
    )
    table_vtext_max: float = (
        1.4  # ... by at most this factor (header and body together, no new wrapped lines)
    )
    table_vtext_max_pt: float = 22  # ... and never beyond this size (pt)
    table_vtext_min_rows: int = 2  # ... only tables with at least this many rows
    table_vtext_max_rows: int = 6  # ... and at most this many (denser tables keep their size)
    table_peer_max: float = 1.0  # ... and within this x the chevron text of the slide (0 = no limit)
    table_vrow_max_em: float = (
        4.2  # a stretched table that cannot grow its text takes rows up to this x its text size
    )
    table_box_max: float = 1.0  # ... and within this x the box text of the slide (0 = no limit)
    table_fit: bool = (
        True  # a table beside a taller chart / image, or the last block above a footnote, fills to there
    )
    table_fit_row_max_em: float = (
        7.0  # a table fitted to a taller chart / image beside it: body rows <= this x text (bottoms line up)
    )
    badge_pad: int = 2  # a badge run of Latin text gets this many no-break spaces on each side
    badge_pad_cjk: int = 1  # ... of CJK text this many full-width spaces
    badge_headroom: float = 1.3  # a badge and the word before it keep this x their width in a table column
    table_pills: bool = True  # a table cell that holds only a badge becomes a native rounded pill shape
    pill_h: float = (
        1.5  # ... this x the cell text line high (capped by the row), pills of a column as wide as the widest
    )
    badge_gap: bool = True  # a badge after text that does not end in a space gets a plain space before it
    # --- chevron rows: alone on the slide / above a table
    chevron_lone_h: float = 0.72  # a lone chevron row grows up to this share of the body height ...
    chevron_lone_aspect: float = 1.0  # ... but never taller than this x its chevron width
    chevron_lone_top: float = 0.4  # ... and sits with this share of the leftover above it (optical center)
    chevron_lone_cap_aspect: float = 0.45  # a lone chevron row is at most this x its chevron width tall ...
    chevron_lone_cap_text: float = 3.0  # ... and at most this x the height of its text block (0 = off)
    chevron_table_fill: float = 0.72  # above a table the chevron text may fill this share of its height ...
    chevron_table_grow: Length = "0.3in"  # ... and the row may grow this much taller at the table's expense
    chevron_table_align: bool = True  # chevron i spans column i of the table below (equal counts only)
    # --- `@steps`: an arrow row with an outcome card under every arrow
    steps_arrow_aspect: float = 0.3  # arrow height / column width ...
    steps_arrow_min_h: Length = "0.55in"  # ... but at least this ...
    steps_arrow_max_h: Length = "1.2in"  # ... and at most this tall
    steps_gap: Length = "0.12in"  # arrow row -> card row
    # --- `@rows`: an ordered list alone on the slide drawn as numbered bars
    rows: bool = False  # True: every slide whose body is one ordered list is drawn as bars (else `@rows`)
    rows_h: Length = "1.05in"  # a bar is at most this tall (shorter when the items do not fit the body)
    rows_min_h: Length = "0.3in"  # ... below this the list stays plain text
    rows_gap: Length = "0.17in"  # air between bars
    rows_pad: Length = "0.2in"  # air between the badge and the text, and at the right end
    rows_text_ratio: float = 0.34  # text size = this x the bar height (pt), at least the body size ...
    rows_text_max_pt: float = 28  # ... at most this size (pt)
    rows_stripe_w: Length = "0.14in"  # `rows.stripe`: width of the left stripe of a bar
    rows_glyph_ratio: float = 0.7  # `@rows plain` glyph size = this x the bar text size
    num_badge_ratio: float = 1.9  # `@num` badge diameter / its digit size (the digit is the heading size x
    # `num_digit_ratio` unless `box.num.size` is set)
    num_digit_ratio: float = 1.0
    num_text_ratio: float = (
        1.7  # `@num=text` / `{.num}`: the number text / the heading size (unless `box.num.size`)
    )
    steps_caption_ratio: float = 0.65  # the "STEP n" caption line is this x the body text size
    steps_stretch: bool = True  # the cards grow down to the conclusion bar / footnote (items spread inside)
    steps_stretch_min: float = 0.4  # hollow at full height: cards are tried shorter, down to this share ...
    steps_stretch_step: float = 0.15  # ... in steps of this share of the free height
    steps_sparse: bool = True  # a sparse group (a few short bullets) uses the body: see ``_compose_steps``
    steps_sparse_below: float = 0.7  # ... when the arrows and cards cover less than this share of the body
    steps_sparse_items: int = 2  # ... and every card holds at most this many paragraphs
    steps_sparse_fill: float = 0.72  # ... then the group aims at this share of the body height
    steps_text_max_pt: float = 24  # ... card text grows up to this size (pt)
    steps_arrow_text_max_pt: float = 28  # ... arrow labels up to this size (pt)
    steps_arrow_h_em: float = 3.0  # ... arrows are this many label heights tall ...
    steps_arrow_sparse_max_h: Length = "1.5in"  # ... at most this tall
    steps_card_max_aspect: float = 0.9  # ... cards at most this x their width tall (text centred)
    steps_top_share: float = 0.4  # ... and sit with this share of the leftover height above them
    steps_arrow_text_ratio: float = 1.15  # arrow heading size >= this x the card text (0 = off) ...
    steps_arrow_text_fill: float = 0.7  # ... while the heading stays within this share of the arrow height
    steps_to_body: bool = True  # small-body themes: a sparse steps group fills the body (no bar needed) ...
    steps_to_body_fill: float = 0.92  # ... arrows + cards cover this share of the body height ...
    steps_to_body_aspect: float = 2.0  # ... cards at most this x their width tall ...
    steps_to_body_text_max_pt: float = 28  # ... card text grows up to this size (pt, CJK wrap guard) ...
    steps_to_body_top: float = 0.1  # ... and the group sits with this share of the leftover above it
    # --- DL3b composition vocabulary (`@timeline @vs @matrix @funnel @pyramid @cycle @agenda @statement`)
    vocab_grow: float = 1.35  # text may grow to this x the theme body size to use the room
    vocab_grow_box: float = 1.8  # `@vs` cards: their text grows up to this x the body size
    vocab_fill: float = 0.94  # a text fills at most this share of its box height
    vocab_top: float = 0.25  # share of the leftover height above a block that does not fill the body
    timeline_stem: Length = "0.3in"  # dot -> milestone text
    timeline_text_w: float = 0.4  # `dir=h`: milestone text at most this share of the body width
    timeline_num_ratio: float = 1.6  # `marks=num`: the dot is this x `timeline.dot.size`
    vs_badge_ratio: float = 2.6  # badge diameter = this x the body text size (pt), unless `vs.badge.size`
    vs_gap: Length = "0.12in"  # air between a card and the badge
    vs_card_min: float = 0.6  # a card is at least this share of the room tall
    matrix_gap: Length = "0.15in"  # between quadrants
    matrix_axis_gap: Length = "0.1in"  # axis arrow <-> quadrants <-> label
    funnel_h_max: Length = "1.3in"  # a stage is at most this tall
    funnel_solo_share: float = 0.8  # width share of the shapes when no stage has a body
    cycle_node_ratio: float = 0.24  # node diameter = this x the room height, unless `cycle.node.size`
    cycle_body_share: float = 0.5  # the ring takes at most (1 - this) of the width: bodies sit outside
    cycle_arrow_gap: Length = "0.08in"  # air between a node and the arrow that leaves / enters it
    cycle_node_inner: float = 0.707  # the text width of a node = this x its diameter (the inscribed square)
    cycle_node_pad: float = 2  # ... minus this padding on each side (pt)
    cycle_chord_ratio: float = 1.6  # neighbouring nodes are at least this x a diameter apart (centres)
    agenda_row_max: Length = "1.2in"  # an agenda row is at most this tall
    agenda_num_ratio: float = 0.5  # number size (pt) = this x the row height, unless `agenda.num.size`
    agenda_num_w: float = 1.7  # number column = this x the number size
    statement_max_pt: float = 140  # the big line grows to at most this size (pt)
    statement_sub_ratio: float = 0.28  # caption line = this x the big line, at least the body size
    line_probe: float = 1.9  # a caption "fits one line" when its height is under this x its size (pt)
    # --- conclusion bar
    conclusion_min_ratio: float = (
        1.0  # the bar text is at least this x the largest card / box body text (0 = off)
    )
    conclusion_max_pt: float = 28  # ... and grows to at most this size (pt)
    conclusion_min_scale: float = (
        0.8  # a bar that does not fit one line shrinks to this x its theme size (>= 12pt) before wrapping
    )
    # --- KPI rows: hero card, value size by card width
    kpi_hero_w: float = 2.0  # a `.kpi .hero` card weighs this x a normal one in an automatic row (1 = off)
    kpi_value_exp: float = 0.6  # a card k x wider than the narrowest of its row gets a number k^exp x bigger
    kpi_card_fill: float = (
        0.7  # KPI cards beside free text: number + caption fill at most this share of the card
    )
    # --- KPI rows alone on the slide (only KPI cards in the body): content-sized cards
    kpi_lone: bool = True  # a lone KPI row keeps cards as tall as their content (label, number, caption)
    kpi_lone_value_max_pt: float = 80.0  # the number grows up to this size (never wraps, see kpi_fit_margin)
    kpi_lone_value_grow: float = 2.4  # ... at most this x its size on the slide
    kpi_lone_text_grow: float = 1.6  # label and caption step up by this factor (when they stay on one line)
    kpi_lone_text_max_pt: float = 24.0  # ... to at most this size
    kpi_lone_pad_em: float = 0.35  # card padding above the label and below the caption, x number size
    kpi_lone_gap_em: float = 0.35  # gap between the label and the number, x label size
    kpi_pin_min_w: float = (
        0.1  # a KPI card without `w=` in a row with `w=` cards: at least this x an even column
    )
    kpi_rule_gap_em: float = 0.8  # `kpi.rule`: air above and below the rule, x caption size
    kpi_band_pad: float = 0.35  # `kpi.band`: air above and below the label in the band, x the card padding
    kpi_lone_fit: float = 0.88  # the number fills at most this share of the card text width (CJK guard)
    kpi_lone_h: float = 0.65  # a lone KPI card is at most this share of the body height
    kpi_lone_min_h: float = 0.5  # ... and at least this share (a short row gets air inside its cards)
    kpi_h: Length | None = (
        None  # `kpi.h=4.4in`: a lone KPI card is exactly this tall (None = the shares above)
    )
    kpi_lone_label_air: float = (
        0.3  # ... of that air, this share goes above the label, the rest around the number
    )
    kpi_lone_center: float = 0.42  # the row sits with this share of the free height above it (optical center)
    kpi_to_body: bool = True  # small-body themes: a lone KPI row stretches down the body (text grows with it)
    kpi_to_body_h: float = (
        0.72  # ... cards this share of the body height (the numbers stay within kpi_lone_*)
    )
    kpi_lone_bar_center: float = 0.6  # ... with a conclusion bar under the row: nearer to the bar
    # --- band balance: a block of cards / columns that still leaves a band under it after the growth passes
    band_shift: float = (
        0.35  # normal density: the block sits with this share of the free height above it (0 = off)
    )
    band_max: float = 0.25  # ... only when more than this share of the body stays empty below the block
    band_shift_max: float = 0.15  # ... and it never moves down by more than this share of the body
    # --- sparse slides use the body (design wave 2): a short list, a few cards, a lone chevron / table
    list_fill: bool = True  # lead + a short bullet list: the list grows with the free height (False = off)
    list_fill_free: float = 0.3  # ... when more than this share of the body stays empty
    list_text_max_pt: float = 28  # ... its text grows up to this size (pt), never onto a new wrapped line
    list_fill_share: float = 0.7  # ... aiming at this share of the body height (text, then paragraph gaps)
    list_gap_max: float = 1.2  # ... paragraph gaps (em) up to this much
    list_top_share: float = 0.4  # ... and the block sits with this share of the leftover height above it
    cards_to_body: bool = True  # a few text cards alone on the slide stretch down the body (no bar needed)
    cards_to_body_free: float = 0.2  # ... when more than this share of the body stays empty around them
    cards_to_body_min: float = 0.45  # ... as tall as this share of the body at least (none hollow) ...
    cards_to_body_step: float = 0.1  # ... tried from the full body height down in steps of this share
    cards_to_body_fill: float = (
        0.45  # ... and their text ends at least this share down the card (none hollow)
    )
    cards_to_body_air: Length = "0.08in"  # ... ending this far above the body bottom (footnote / margin)
    card_fill_text_max_pt: float = 26  # ... their text grows up to this size (pt), items spread inside
    chevron_steps: bool = True  # a chevron row alone whose steps all have short bodies is built as `@steps`
    chevron_steps_items: int = 3  # ... "short" = at most this many paragraphs under every heading
    table_free: bool = True  # a table alone on the slide (<= table_free_max_rows rows) grows with free height
    table_free_min: float = 0.06  # ... when more than this share of the body stays empty under / around it
    table_free_max_rows: int = 8  # ... only tables with at most this many rows (denser ones keep their size)
    table_free_text_max_pt: float = (
        22  # ... its text grows up to this size (pt), never onto a new wrapped line
    )
    table_free_row_em: float = 3.6  # ... then its rows up to this x the text size
    table_free_top: float = 0.4  # ... a table that still leaves air sits with this share of it above
    bar_attach: Literal["grow", "move", "off"] = (
        "grow"  # bar under a lone table: grow = the table meets it (rows <= table_free_row_em, the bar then
        # moves up to the rest); move = only the bar moves up; off = the bar stays at the bottom
    )
    bar_attach_gap: Length = "0.15in"  # air between a table and the bar attached to it
    # --- wave 2026-10-08 lane A
    icon_disc_ratio: float = 2.2  # `icon.disc`: disc diameter / the glyph side the icon would have without it
    icon_disc_glyph: float = 0.46  # ... the glyph is this share of the disc diameter (centred in it)
    icon_disc_kpi: float = (
        1.4  # ... a `.kpi` card icon: disc diameter / the bare icon side (the number needs room)
    )
    icon_disc_list: float = (
        1.0  # ... an `@iconlist` item: disc diameter / the icon slot (that slot is already large)
    )
    icon_disc_round: float = 0.25  # ... `icon.disc.shape=rounded`: corner radius / disc diameter
    icon_disc_max: float = 0.8  # ... a disc is at most this share of the height it sits in (chevrons, bars)
    conclusion_icon_ratio: float = 0.62  # `conclusion.icon`: glyph (or disc) side / bar height
    conclusion_icon_gap: float = 0.5  # ... the air after it, in icon sides
    conclusion_icon_h: Length = "0.55in"  # ... a bar with an icon is at least this tall (`conclusion.h` wins)
    # --- wave 2026-10-08 lane D
    steps_card_pad: Length = "0.2in"  # `@steps` card (head=card): air around its top-anchored content
    steps_card_head_ratio: float = 1.3  # ... the card heading is this x the card body text
    steps_card_fill_max: float = 0.92  # ... the card text grows until it fills this share of the card
    steps_arrow_card_h: Length = (
        "0.8in"  # ... its arrows only carry the step number / icon: at most this tall
    )
    iconlist_fill_air: float = 2.6  # `iconlist.fill=on`: a row is at most this x its tallest item
    cover_art_nodes: int = 11  # `cover.art=network`: dots (8..12) joined by thin lines
    cover_art_node_ratio: float = (
        0.07  # ... a dot is this x the art's shorter side wide (the accent one 1.7x)
    )
    cover_art_line_pt: float = 1.25  # ... the lines' thickness (pt)
    cover_art_margin: float = 0.06  # ... air between the motif and the slide edges, in slide widths
    # --- wave 2026-10-08 lane E
    iconlist_fill_min: float = (
        0.6  # a stacked `@iconlist` card (icon above text) is at most content / this tall
    )
    card_fill_max: float = (
        0.7  # box cards: text is not grown once the content fills this share of the card ...
    )
    card_fill_min: float = 0.6  # ... and the cards are no taller than the content / this (not hollow)
    card_heading_max_pt: float = (
        30  # `card.heading.max`: a box card heading grows to at most this size (pt) ...
    )
    card_body_max_pt: float = 24  # `card.text.max`: ... its text to at most this (both under `grow.max`)
    card_fill_step: float = 0.04  # ... box card growth steps by this factor


class RenderTokens(BaseModel):
    """Renderer defaults that change the look (line widths, readable ink colors, chart text scales)."""

    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="before")
    @classmethod
    def _bools(cls, data):
        return _coerce_bools(cls, data)

    line_width: float = 0.75  # pt, a bordered shape without its own line width
    connector_width: float = 1.5  # pt, connectors / arrows between blocks
    chart_line_width: float = 2.25  # pt, line chart series
    chart_title_scale: float = 1.2  # chart title size / chart text size
    chart_text_ratio: float = 0.034  # big chart text >= this x the frame shorter side (0 = off) ...
    chart_text_max_pt: float = 16  # ... up to this size (pt); never below the theme chart size
    chart_label_scale: float = 1.0  # data label size / chart text size
    chart_legend_scale: float = 1.2  # legend size / chart text size
    chart_pie_labels: str = (
        "percent"  # `labels=on` on a pie / doughnut shows the share ("percent") or the raw "value"
    )
    chart_pie_label_scale: float = 1.4  # pie / doughnut wedge label size / chart text size ...
    chart_pie_label_max_pt: float = 24  # ... at most this size (pt)
    chart_pie_label_bold: bool = True  # wedge labels are bold
    chart_pie_label_pos: str = "inside_end"  # pie label: center | inside_end | outside_end | best_fit
    chart_pie_label_min: float = 0.06  # a pie wedge below this share puts its label outside the wedge
    chart_collide_em: float = 1.3  # line chart: labels of two series closer than this many label heights (at
    # the plot's scale) alternate above / below the point, the lower series going below (0 = off)
    chart_plot_share: float = 0.7  # ... assuming the plot takes this share of the chart height
    chart_scale_ratio: float = 0.1  # `chart-scale` info line: a column / bar series whose max is below this
    # share of another series' max is crushed (0 = off)
    ink_dark: str = "#1F2937"  # text on light fills when the color is chosen for contrast (badges, labels)
    ink_light: str = "#FFFFFF"  # text on dark fills
    highlight: str = "#FFFF00"  # default ==highlight== color
    code_style: str = "default"  # pygments style for code blocks
    shadow: str = "0 3 12 #00000030"  # `shadow=on`: CSS-like "x y blur [spread] color" (pt)
    slide_bg: str = "#FFFFFF"  # slide background when neither the slide nor the theme has `bg`
    gantt_grid: float = (
        0.45  # `.gantt` table: body vertical lines keep this share of the border color (rest = fill)
    )
    ink_auto: bool = True  # derive readable text colors the deck did not set (`style: ink.auto=off` disables)
    contrast_min: float = 4.5  # contrast ratio auto ink aims for (normal text)
    contrast_large: float = 3.0  # ... for large text (>= `large_pt`, e.g. KPI numbers)
    large_pt: float = 24  # text at least this size counts as large
    # --- chart axis and bars
    chart_axis_headroom: float = (
        0.06  # an auto value axis ends this share above the data max (label room; 0 = off)
    )
    chart_neg_pad: float = (
        0.08  # bars / columns with a negative: label room below the lowest bar (span share)
    )
    chart_total_pad: float = (
        0.08  # stack-total label room: the hidden carrier is this share of the longest stack
    )
    chart_axis_lines_min: int = 4  # ... with at least this many gridlines
    chart_axis_lines_max: int = 6  # ... and at most this many
    chart_gap: int = 60  # bar/column gap width (% of a bar) ...
    chart_gap_few: int = (
        180  # ... for a chart with at most `chart_gap_few_cats` categories (fat bars look crude)
    )
    chart_gap_few_cats: int = 3
    chart_axis_lines_min_few: int = 3  # ... a chart with at most `chart_gap_few_cats` categories needs fewer
    chart_axis_off_cats: int = 4  # `labels=on` bar / column charts with at most this many categories drop the
    # value axis and gridlines (the labels carry the numbers; `axis=on` keeps them); 0 = never
    chart_label_scale_few: float = (
        1.2  # value labels of a sparse chart (<= `chart_gap_few_cats`): x chart text
    )
    chart_seg_label_scale: float = 1.1  # labels inside stacked segments: x chart text size (never below it)
    chart_seg_pad: float = 1.3  # a segment label needs this multiple of its font size as height
    chart_line_zero_max: float = 0.4  # a line chart axis starts above zero when its lowest value is above
    # this share of its highest
    chevron_shape: str = (
        "chevron"  # `@chevron` / `@steps` arrows: "chevron" (notched tail) or "pentagon" (flat tail)
    )
    chart_grid: str = "border"  # value-axis gridline color of bar / column / line charts
    chart_pie_line: str = "bg"  # pie / doughnut wedge outline color (`none` = no outline) ...
    chart_pie_line_width: float = 0.0  # ... and width in pt (0 = the PowerPoint default)
    chart_hl: str = "accent"  # `hl=` points: fill (bar / column / pie / waterfall), outline, line marker
    chart_hl_line: float = 2.25  # pt, outline of an `hl=` bar in a multi-series chart
    chart_hl_marker: int = 11  # pt, marker of an `hl=` point in a line chart
    chart_note_size_add: float = 1.0  # pt, a `note=` is this much larger than the data labels
    chart_note_line_width: float = 1.0  # pt, the pointer of a `note=`
    waterfall_up: str = "success"  # waterfall bars: increase, decrease, total (theme color names or hex)
    waterfall_down: str = "danger"
    waterfall_total: str = "primary"
    gantt_badge: str = (
        ""  # badge pill inside a bar of the same color ("" = a tint of the bar fill, or a color)
    )
    gantt_badge_tint: float = 0.82  # that tint: share of the way from the bar fill toward white
    badge_cjk_bold: bool = False  # CJK badge text stays bold (synthetic bold smears small CJK glyphs)


_HEX_RE = re.compile(r"#?([0-9A-Fa-f]{6}|[0-9A-Fa-f]{3})")


@cache
def _hex_norm(v: str) -> str | None:
    """``#RRGGBB`` (upper case) of a 3/6-digit hex string, else None (pure: cached per string)."""
    if not _HEX_RE.fullmatch(v.strip()):
        return None
    h = v.strip().lstrip("#")
    h = "".join(ch * 2 for ch in h) if len(h) == 3 else h
    return "#" + h.upper()


_BASE_COLORS = ("bg", "fg", "surface", "border", "muted")  # never moved by auto ink (muted has its own rule)


@cache
def _shade(color: str, backs: tuple[str, ...], need: float) -> str:
    return nearest_passing(color, list(backs), need)


NEUTRAL_COLORS = {
    "bg": "#FFFFFF",
    "fg": "#111827",
    "primary": "#111827",
    "secondary": "#4B5563",
    "accent": "#6B7280",
    "muted": "#6B7280",
    "border": "#D1D5DB",
    "surface": "#F3F4F6",  # card / table header background
    "danger": "#B91C1C",
    "success": "#15803D",
}

DEFAULT_SIZES = {
    "title": 32,
    "subtitle": 20,
    "heading": 20,
    "body": 18,
    "lead": 22,
    "quote": 20,
    "caption": 12,
    "footnote": 10,
    "code": 14,
    "table": 14,
    "cover-title": 44,
    "cover-subtitle": 24,
}


def _base_classes() -> dict[str, Style]:
    """Mechanism classes every theme has (components need them); presets restyle them."""
    return {
        "card": Style(fill="surface", line="border", line_width=0.75, radius=6, padding="10pt"),
        "callout": Style(fill="surface", line="primary", line_width=1, padding="10pt"),
        "muted": Style(color="muted"),  # text, spans, badges: grey ink
        # a `.muted` BOX (card): lower priority but readable. Muted border (+ `muted_band` header fill),
        # the body keeps its normal ink. `muted-box.color=muted` brings the grey body text back.
        "muted-box": Style(line="muted"),
        "dense": Style(font_size=11),
        "kpi": Style(font_size=36, bold=True, color="primary", align="center", valign="middle"),
        # callout kinds (`> [!note]` ...): border color. Badges: `[x]{.badge}`.
        "note": Style(line="primary"),
        "tip": Style(line="success"),
        "warn": Style(line="accent"),
        "caution": Style(line="danger"),
        "badge": Style(fill="primary", color="bg", bold=True),
        # mermaid flowchart nodes
        "node": Style(
            fill="surface", line="primary", line_width=1, padding="6pt", align="center", valign="middle"
        ),
        "round": Style(radius=12),
        # `{.gantt}` table: every filled body cell becomes a bar of this look (fill primary, best ink)
        "gantt": Style(fill="primary", radius=4, padding="3pt", align="center", valign="middle"),
        # a table cell that holds only a badge becomes a pill shape of this look (fill = the badge color)
        "pill": Style(
            radius=99,
            padding_left="7pt",
            padding_right="7pt",
            padding_top="1pt",
            padding_bottom="1pt",
            align="center",
            valign="middle",
        ),
        "decision": Style(fill="bg", line="accent"),
        # `@rows`: the bar of every ordered-list item and its number badge (`rows-num.fill=a,b` cycles)
        "rows": Style(fill="surface", line="border", line_width=0.75),
        "rows-num": Style(fill="primary", color="bg"),
        # an item card: a bullet of a box under `@items` (or a `### x {.item}` sub-box);
        # `item.border-left=` is its stripe
        "item": Style(fill="bg", valign="middle"),
        # `note=` of a chart: native callout inside the chart frame, pointing at the `hl=` point
        "chart-note": Style(
            fill="surface", line="accent", line_width=1, radius=3, padding="5pt", bold=True, valign="middle"
        ),
    }


class Theme(Forms4Tokens):  # Forms2/3/4Tokens: DL3b part 2, DL3d part 2, wave 2026-10-08 lane B form tokens
    model_config = ConfigDict(extra="forbid")

    name: str
    colors: dict[str, str] = Field(default_factory=lambda: dict(NEUTRAL_COLORS))
    fonts: Fonts = Field(default_factory=Fonts)
    # font sizes in pt, by text role
    sizes: dict[str, float] = Field(default_factory=lambda: dict(DEFAULT_SIZES))
    min_font_size: float = 8  # autofit never shrinks below this
    pinned: list[str] = Field(default_factory=list)  # size roles written `sizes: heading=20!`: never grown
    margin_x: Length = "0.5in"
    margin_y: Length = "0.4in"
    gap: Length = "0.25in"
    title_height: Length = "0.9in"
    # named styles used by `{.name}`, e.g. "card", "callout", "kpi"; tokens may add new ones (`hero.fill=`)
    classes: dict[str, Style] = Field(default_factory=_base_classes)
    heading_color: str = "fg"
    title_color: str = "fg"
    lead_color: str = "fg"
    title_band: str | None = None  # full-width band color behind the slide title (None = no band)
    title_band_color: str = "bg"  # title text color when a band is drawn
    # cover composition (cover.band_h=0: the legacy block centred on layout.cover_title_y)
    cover_band_h: float = Field(
        0, ge=0, le=0.9
    )  # share of the slide height of the cover band anchored to the top (0 = off)
    cover_pad: Length = "0.6in"  # air between the cover title block and the bottom edge of the band
    cover_gap: Length = "0.2in"  # air between the cover title and its subtitle
    cover_rule: str | None = None  # color of a thin rule along the band edge (None = no rule)
    cover_rule_h: Length = "0.05in"  # ... its thickness
    cover_footer: bool = True  # the deck footer (organisation) shows on the cover as a quiet caption
    cover_bar: str | None = None  # color of a vertical bar left of the cover title block (None = none);
    # `accent@edge`: a bar on the slide's left edge over the full height instead
    cover_bar_w: Length = "0.12in"  # ... its width (the title block moves right by width + `cover_gap`)
    cover_rule_w: Length | None = None  # a short cover rule of this width at the title (not full width)
    cover_rule_pos: str = "below"  # ... `above` the title, or `below` it (between title and subtitle)
    cover_stripes: str | None = None  # `color@x,color@x`: vertical stripes from x to the right edge
    cover_band: bool = True  # False: the cover band is not drawn although `title.band` is set (bg= shows)
    cover_top_bar: str | None = None  # color of a full-width strip on the top edge of the cover
    cover_top_bar_h: Length = "0.1in"
    cover_bottom_bar: str | None = None  # ... on the bottom edge of the cover
    cover_bottom_bar_h: Length = "0.1in"
    # slide chrome (design wave 3): edge strips, the rule under the title, a KPI stripe
    top_bar: str | None = None  # color of a strip along the top edge of every slide but the cover
    top_bar_h: Length = "0.1in"
    bottom_bar: str | None = None  # ... along the bottom edge
    bottom_bar_h: Length = "0.1in"
    title_rule: str | None = None  # color of a rule under the slide title (None = none)
    title_rule_h: Length = "2pt"
    title_rule2: str | None = None  # color of a second, short segment on the left end of the title rule
    title_rule2_w: Length = "1.6in"  # ... its width (its thickness is `title_rule_h`)
    heading_rule: str | None = None  # color of a rule under every `##` box heading or band (not `###`)
    heading_rule_h: Length = "2pt"
    box_items: str = "bullets"  # `cards`: the bullets of every box are item cards (`@items`: one slide)
    box_num_fill: str | None = None  # `@num`: the numbered badge on a box heading: fill (None = primary) ...
    box_num_color: str | None = None  # ... digit color (None = readable on the fill)
    box_num_size: float | None = None  # ... digit size in pt (None = the box heading size)
    box_num_text: str = "{nn}"  # `@4 num=text`: the number text ("{n}" = 1, "{nn}" = 01, "第{n}章") ...
    # (box_num_fill / box_num_color / box_num_size above: with `num=text` or `{.num}` the colour of the number
    # text, a list cycles over the boxes; size in pt, None = `layout.num_text_ratio` x the heading size)
    box_stripe: str | None = None  # a stripe on every `##` card: a color or a list `a,b,c` (cycled in order)
    box_stripe_h: Length = "6pt"  # ... its thickness
    box_stripe_side: str = "top"  # ... on the `top`, `left`, `right` or `bottom` edge
    item_stripe: str | None = None  # the same for item cards (`@items`, `### x {.item}`)
    item_stripe_h: Length = "6pt"
    item_stripe_side: str = "left"
    rows_glyph: str | None = None  # `@rows plain`: the glyph before every bar text (None = `bullet=`)
    rows_glyph_color: str | None = None  # ... its color (None = `bullet.color`, else the text color)
    rows_stripe: str | None = None  # a left stripe on every `@rows` bar: a color or a list `a,b` (cycled)
    # --- DL3b composition vocabulary (`@timeline @vs @matrix @funnel @pyramid @cycle @agenda @statement`)
    timeline_line: str = "muted"  # `@timeline`: the axis line ...
    timeline_line_w: Length = "3pt"  # ... its thickness
    timeline_dot: str = "primary"  # ... the milestone dots (`marks=on|num`) ...
    timeline_dot_size: Length = "0.26in"  # ... their diameter
    timeline_now: str = "accent"  # ... the dot (and date) of the `{.accent}` milestone
    timeline_date_color: str | None = None  # ... milestone headings (None = `primary`)
    vs_badge_text: str = "vs"  # `@vs`: the badge between the two sides ...
    vs_badge_fill: str = "primary"
    vs_badge_color: str | None = None  # ... (None = readable on the fill)
    vs_badge_size: Length | None = None  # ... diameter (None = from the body text size)
    vs_verdict_fill: str = "primary"  # ... the verdict bar (a third `##` box) ...
    vs_verdict_color: str | None = None
    vs_win_line: str = "primary"  # ... the `{.hero}` side's border color ...
    vs_win_w: float = Field(3, ge=0, le=20)  # ... and its width (pt)
    vs_win_fill: str | None = None  # ... and fill (None = the card fill)
    matrix_axis_color: str = "muted"  # `@matrix`: axis arrows and labels ...
    matrix_axis_size: float | None = None  # ... label size in pt (None = caption size)
    matrix_axis_w: Length = "2pt"  # ... arrow thickness
    matrix_fill: str | None = None  # ... quadrant fills `a,b,c,d` (reading order; None = the card fill)
    funnel_fill: str | None = None  # `@funnel`: stage fills `a,b,c` (cycled; None = tints of primary) ...
    funnel_color: str | None = None  # ... heading ink (None = readable on the fill)
    funnel_gap: Length = "0.06in"  # ... air between stages
    funnel_taper: float = Field(0.3, ge=0, le=0.95)  # ... width of the narrow end / the wide end
    funnel_share: float = Field(0.5, ge=0.2, le=0.9)  # ... share of the width the shapes take (bodies right)
    pyramid_fill: str | None = None  # `@pyramid`: same tokens
    pyramid_color: str | None = None
    pyramid_gap: Length = "0.06in"
    pyramid_taper: float = Field(0.2, ge=0, le=0.95)  # ... narrow end / wide end (0 = a point)
    pyramid_share: float = Field(0.5, ge=0.2, le=0.9)
    cycle_fill: str | None = None  # `@cycle`: node fills `a,b,c` (cycled; None = primary) ...
    cycle_color: str | None = None  # ... node heading ink (None = readable on the fill)
    cycle_arrow: str = "muted"  # ... the curved arrows ...
    cycle_arrow_w: Length = "3pt"
    cycle_node_size: Length | None = None  # ... node diameter (None = from the room)
    agenda_num_size: float | None = None  # `@agenda`: number size in pt (None = from the row height) ...
    agenda_num_text: str = "{n}"  # ... the number text ("{n}" = 1, "0{n}" = 01, "第{n}章") ...
    agenda_num_color: str = "primary"
    agenda_rule: str | None = "border"  # ... rule between rows (none = no rules) ...
    agenda_rule_w: Length = "1pt"
    agenda_now: str = "accent"  # ... the `{.accent}` (current) item's number and heading ...
    agenda_dim: str | None = "muted"  # ... the other items' ink once one is current (none = unchanged)
    statement_size: float | None = None  # `@statement`: the big line in pt (None = as large as fits) ...
    statement_color: str | None = None  # ... its color (None = primary)
    statement_sub_size: float | None = None  # ... the second line (None = from the big line)
    statement_sub_color: str | None = None  # ... (None = muted)
    table_num_pad: Length | None = None  # right inset of right-aligned (numeric) table cells
    kpi_stripe: str | None = None  # color of a stripe on the top edge of every `.kpi` card
    kpi_stripe_h: Length = "6pt"
    kpi_stripe_side: str = (
        "top"  # `top`, `left`, `right` or `bottom` (kpi.stripe may be a list `a,b,c`: cycled)
    )
    kpi_rule: str | None = None  # color of a divider rule between the number and its caption in `.kpi` cards
    kpi_rule_h: Length = "1pt"
    kpi_rule_w: Length = "100%"  # ... its width (a share of the card's text width, or a length), centred
    kpi_band: str | None = (
        None  # fill of a header band behind the label of every `.kpi` card (None = plain label)
    )
    kpi_band_color: str | None = None  # ... the label ink on the band (None = readable on the fill)
    kpi_band_size: float | None = None  # ... the label size in pt (None = the `kpi.label` size)
    kpi_unit_size: float | None = (
        None  # pt of the trailing unit of a KPI value (億円, 名, %); None = the digits' size
    )
    kpi_unit_color: str | None = None  # ... its color (None = the number's)
    bullet: str | None = None  # glyph of bullet lists (None = the built-in "•" / "–")
    bullet_color: str | None = None  # ... its color (None = the text color)
    steps_caption: str | None = None  # `@steps`: caption under every card, "{n}" = the step number
    steps_caption_color: str | None = None  # ... its color (None = the muted color)
    steps_caption_size: float | None = None  # ... its size in pt (None = `layout.steps_caption_ratio` x body)
    conclusion_fill: str = "primary"
    conclusion_color: str = "bg"
    table_header_fill: str = "surface"
    table_header_color: str = "fg"
    table_body_fill: str = "bg"
    table_border: str = "border"
    table_zebra_fill: str | None = None  # alternate body row fill for `.zebra` tables (None = derived)
    # rows emphasised with `hl=` on a table: `table_hl_strength` of this color mixed into the body fill
    # (1 = exactly it; none = bold only), bold text, and an ink (None = the cell's own, made readable)
    table_hl_fill: str | None = "accent"
    table_hl_strength: float = Field(0.2, ge=0, le=1)
    table_hl_color: str | None = None
    table_hl_bold: bool = True
    heading_band: str | None = None  # fill of a full-width band behind `##` box headings (None = plain)
    heading_band_color: str = "bg"  # heading text color on the band
    muted_band: str | None = "muted"  # heading band fill of a `.muted` box (None = the normal band)
    template: str | None = None  # path of a user .pptx/.potx used as the base presentation (masters, layouts)
    columns: int = 12  # layout track grid: ratio/area columns snap to multiples of width/columns
    dense_scale: float = 0.8  # body/table/code size factor for `density: dense` / `.dense` slides
    palette: list[str] = Field(
        default_factory=lambda: ["primary", "secondary", "accent", "danger", "success", "muted"]
    )
    layout: LayoutTokens = Field(default_factory=LayoutTokens)

    @model_validator(mode="before")
    @classmethod
    def _bools(cls, data):  # `style: cover.footer=off`
        return _coerce_bools(cls, data)

    @field_validator("cover_band_h", mode="before")
    @classmethod
    def _share(cls, v):  # `cover.band_h=60%` (or 0.6)
        if isinstance(v, str) and v.strip().endswith("%"):
            try:
                return float(v.strip()[:-1]) / 100
            except ValueError:
                return v
        return v

    render: RenderTokens = Field(default_factory=RenderTokens)

    # --- wave 2026-10-08 lane A
    icon_disc: str | None = (
        None  # `icon.disc=secondary`: every `icon=` sits on a disc of this colour (None = bare)
    )
    icon_disc_size: Length | None = (
        None  # ... its diameter (None = `layout.icon_disc_ratio` x the glyph side)
    )
    icon_disc_shape: str = "circle"  # ... `circle`, `rounded` or `square`
    icon_color: str | None = (
        None  # ink of an icon glyph (None = readable on the disc, else the heading colour)
    )
    card_elevation: int | None = None  # `card.elevation=0..3`: shorthand for `card.shadow` (see `ELEVATIONS`)
    card_line_set: bool = (
        False  # the deck states `card.line` / `card.border`: a shadowed card keeps its border
    )
    conclusion_icon: str | None = None  # `conclusion.icon=refresh`: an icon at the left of the conclusion bar

    # --- wave 2026-10-08 lane D
    # `@steps`: the heading is written in the card (the arrow shows the step number / icon) or in the `arrow`
    steps_head: Literal["card", "arrow"] = "card"
    iconlist_fill: bool = True  # `@iconlist` grows its icons and spaces the items evenly over the body
    iconlist_valign: Literal["top", "center"] = (
        "center"  # ... an item sits at the top / the middle of its row
    )
    cover_art: Literal["none", "network", "dots", "rings"] = (
        "none"  # decorative motif on the cover's right half
    )
    cover_art_color: str | None = None  # ... its colour (None = `secondary`); one node is `accent`
    cover_art_opacity: float = Field(0.65, ge=0.05, le=1.0)  # ... how opaque it is
    cover_art_seed: int = 7  # ... the same seed draws the same motif
    cover_art_split: float = Field(
        0.6, ge=0.3, le=0.9
    )  # ... the title keeps this share of the width, the art the rest

    # --- wave 2026-10-08 lane E
    conclusion_floor: float = Field(
        1.0, ge=0.0
    )  # `conclusion.floor`: the bar text is never under this x the body text of its slide (it wraps first)
    iconlist_title_max: float = 32  # `iconlist.title.max`: the item title grows to at most this size (pt) ...
    iconlist_text_max: float = (
        28  # `iconlist.text.max`: ... the item text to at most this (both under `grow.max`)
    )
    iconlist_icon_pos: Literal["auto", "left", "top"] = (
        "auto"  # `iconlist.icon.pos`: icon beside the text, or above it (auto: top for a row of 3+ columns)
    )
    # --- wave 2026-10-08 lane F
    # `heading.wrap=on`: a card heading may wrap; off (the default) = one line preferred in a row of cards
    heading_wrap: bool = False

    def color(self, value: str | None) -> str | None:
        """Resolve a theme color name ("primary") or pass a hex value through."""
        if value is None:
            return None
        return self.colors.get(value, value)

    def hexval(self, value: str | None) -> str | None:
        """``#RRGGBB`` (upper case) of a theme color name or 3/6-digit hex; None for anything else."""
        v = self.colors.get(value, value) if isinstance(value, str) else None
        return _hex_norm(v) if isinstance(v, str) else None

    def need_for(self, size_pt: float | None) -> float:
        """Contrast ratio text of this size should reach (3:1 for large text, else 4.5:1)."""
        rt = self.render
        big = size_pt is not None and size_pt >= rt.large_pt
        return rt.contrast_large if big else rt.contrast_min

    def surface_backs(self) -> list[str]:
        """Colors text may sit on without a fill of its own: the slide background and card surface."""
        return [h for h in (self.hexval("bg"), self.hexval("surface")) if h]

    def legible(self, value: str | None, size_pt: float | None = None, backs: list[str] | None = None):
        """A theme color *name* made readable on ``backs`` (default bg + surface) by moving its lightness.

        Hex values (set by the deck) and names of the base colors pass through unchanged, and so does
        everything when ``render.ink_auto`` is off. The name is returned when it already passes.
        """
        if not self.render.ink_auto or not isinstance(value, str) or value not in self.colors:
            return value
        if value in _BASE_COLORS:
            return value
        hx = self.hexval(value)
        use = backs or self.surface_backs()
        if not hx or not use:
            return value
        got = _shade(hx, tuple(use), self.need_for(size_pt))
        return value if got == hx else got

    def ink_candidates(self) -> list[str]:
        rt = self.render
        raw = ["fg", "bg", rt.ink_light, rt.ink_dark, "#000000", "#FFFFFF"]
        return [h for h in dict.fromkeys(self.hexval(c) for c in raw) if h]

    def ink_on(self, fill: str | None, prefer: str | None = None, need: float | None = None) -> str:
        """Ink on ``fill``: ``prefer`` when it reaches 4.5:1, else the best of fg/bg/white/black.

        Returns ``prefer`` untouched when ``render.ink_auto`` is off or the fill is not a plain color.
        """
        fh = self.hexval(fill)
        if not self.render.ink_auto or fh is None:
            return prefer or "fg"
        need = need or self.render.contrast_min
        ph = self.hexval(prefer)
        cands = ([ph] if ph else []) + self.ink_candidates()
        if ph and ratio(ph, fh) >= need:
            return prefer  # type: ignore[return-value]
        return best_ink(fh, cands, need)

    def heading_band_for(self, classes) -> tuple[str | None, str]:
        """(fill, ink) of a box heading band: the ``muted_band`` color for a ``.muted`` box, else the normal
        band. The ink keeps ``heading_band_color`` while it reads on the fill (layout and lint share it)."""
        band = self.heading_band
        if band and "muted" in classes and self.muted_band:
            return self.muted_band, self.ink_on(self.muted_band, self.heading_band_color)
        return band, self.heading_band_color

    def kpi_band_for(self) -> tuple[str | None, str]:
        """(fill, ink) of the header band of a ``.kpi`` card (``kpi.band``): the ink keeps ``kpi.band.color``
        (else white) while it reads on the fill."""
        band = self.kpi_band
        if not band:
            return None, "bg"
        return band, self.ink_on(band, self.kpi_band_color or "bg")

    def badge_ink(self, highlight: str | None) -> str:
        """Ink of a run on a badge highlight (the badge class color when it is the same fill)."""
        hh = self.hexval(highlight) or self.hexval(self.render.highlight) or "#FFFF00"
        badge = self.classes.get("badge")
        if badge and badge.color and self.hexval(badge.fill) == hh:
            return badge.color
        r, g, b = (int(hh[i : i + 2], 16) for i in (1, 3, 5))
        rt = self.render
        prefer = rt.ink_dark if 0.299 * r + 0.587 * g + 0.114 * b > 160 else rt.ink_light
        return self.ink_on(hh, prefer)

    def run_color(
        self,
        run_color: str | None,
        highlight: str | None,
        style_color: str | None,
        size_pt: float | None = None,
        fill: str | None = None,
    ) -> str | None:
        """The color a run is drawn in (renderer and lint share this)."""
        if highlight and run_color in (None, "bg"):  # the parser gives badges `bg`: the ink is chosen here
            return self.badge_ink(highlight)
        if run_color:
            fh = self.hexval(fill)
            return self.legible(run_color, size_pt, [fh] if fh else None)
        return style_color

    def need_for_text(self, size_pt: float | None, bold: bool = False) -> float:
        """WCAG ratio for table / chart text: 3:1 for large text (>= 18pt, or bold >= 14pt), else 4.5:1."""
        rt = self.render
        big = size_pt is not None and (size_pt >= 18 or (bold and size_pt >= 14))
        return rt.contrast_large if big else rt.contrast_min

    # ---- tables: fills and text style of a cell (renderer and lint share these)

    def table_body_fill_of(self, style_fill: str | None) -> str:
        """Body cell fill: the CSS ``table { background }`` else the ``table.body.fill`` token."""
        return style_fill or self.table_body_fill

    def table_zebra_fill_of(self, body_fill: str) -> str:
        from .render.util import hex6  # lazy: render imports theme

        if self.table_zebra_fill:
            return self.table_zebra_fill
        a, b = hex6(self, body_fill), hex6(self, "surface")
        return "#" + "".join(
            f"{round(int(a[i : i + 2], 16) * (1 - 0.6) + int(b[i : i + 2], 16) * 0.6):02X}" for i in (0, 2, 4)
        )

    def table_hl_fill_of(self, body_fill: str) -> str:
        """Fill of an ``hl=`` row: ``table.hl.fill`` mixed into the body fill by ``table.hl.strength``."""
        from .render.util import hex6  # lazy: render imports theme

        if not self.table_hl_fill or body_fill.lower().startswith(("linear", "radial")):
            return body_fill
        a, b, k = hex6(self, self.table_hl_fill), hex6(self, body_fill), self.table_hl_strength
        mixed = (round(int(a[i : i + 2], 16) * k + int(b[i : i + 2], 16) * (1 - k)) for i in (0, 2, 4))
        return "#" + "".join(f"{v:02X}" for v in mixed)

    def table_cell_fill(
        self,
        row: int,
        col: int,
        header_rows: int,
        header_cols: int,
        body_fill: str,
        zebra: bool,
        hl: bool = False,
    ) -> str:
        """Fill of grid cell (row, col) before any per-cell CSS fill: header, emphasised row, first column,
        body or band."""
        if row < header_rows:
            return self.table_header_fill
        if hl:
            return self.table_hl_fill_of(body_fill)
        if col < header_cols:
            return "surface"
        if zebra and (row - header_rows) % 2 == 1:
            return self.table_zebra_fill_of(body_fill)
        return body_fill

    def table_cell_style(
        self,
        base: Style,
        header: bool,
        first_col: bool,
        colspan: int,
        cell_style: Style | None,
        hl_fill: str | None = None,
    ) -> Style:
        """Text style of a table cell: the table's, header / first-column defaults, then the cell's own.

        ``hl_fill`` is the fill of an emphasised (``hl=``) body row: bold, and an ink readable on it."""
        st = base
        if hl_fill is not None and not header:
            ink = self.table_hl_color or self.ink_on(hl_fill, base.color or "fg")
            st = st.merged(
                Style(
                    bold=True if self.table_hl_bold else None,
                    color=ink if ink != (base.color or "fg") else None,
                )
            )
        elif header:
            st = st.merged(
                Style(bold=True, color=self.table_header_color, align="center" if colspan > 1 else None)
            )
        elif first_col:
            st = st.merged(Style(bold=True))
        return st.merged(cell_style)

    # ---- charts: colors the renderer draws (renderer and lint share these)

    def chart_palette(self, colors: Any = None) -> list[str]:
        """Series / slice colors ('RRGGBB'): an explicit ``colors`` option, else the theme palette."""
        from .render.util import hex6

        if isinstance(colors, str):
            colors = [p.strip() for p in colors.replace(";", ",").split(",") if p.strip()]
        explicit = isinstance(colors, (list, tuple)) and bool(colors)
        use = colors if explicit else self.palette
        pal = [hex6(self, str(c)) for c in use] or [hex6(self, "primary")]
        if not explicit:  # distinct theme colors in order; they wrap only after all of them are used
            pal = list(dict.fromkeys(c.upper() for c in pal))
        return pal

    def chart_label_ink(self, fill: str, *backs: str) -> str:
        """'RRGGBB' ink readable on ``fill`` (and on every ``backs`` color when one ink can do both)."""
        cands = [c.lstrip("#").upper() for c in self.ink_candidates()]
        need = self.render.contrast_min
        both = [c for c in cands if all(ratio("#" + c, "#" + b) >= need for b in (fill, *backs))]
        if both:
            return both[0]
        return best_ink("#" + fill, ["#" + c for c in cands], need).lstrip("#").upper()


# --------------------------------------------------------------------------- presets (YAML data)


def merge_data(base: dict, over: dict) -> dict:
    """Deep merge of plain token mappings (``over`` wins; nested mappings merge)."""
    out = dict(base)
    for k, v in over.items():
        out[k] = merge_data(out[k], v) if isinstance(v, dict) and isinstance(out.get(k), dict) else v
    return out


def theme_from_data(data: dict, name: str) -> Theme:
    """A Theme from a token mapping. ``extends: <preset>`` starts from that preset, else schema defaults."""
    data = dict(data)
    parent = data.pop("extends", None)
    base = get_theme(str(parent)).model_dump() if parent else Theme(name=name).model_dump()
    base["name"] = name
    merged = merge_data(base, data)
    merged["name"] = name
    card = (data.get("classes") or {}).get("card")
    if isinstance(card, dict) and card.get("line") is not None:
        merged["card_line_set"] = True  # the preset states a card border: a shadowed card keeps it
    return Theme.model_validate(merged)


@cache
def _preset(name: str) -> Theme:
    import yaml

    data = yaml.safe_load((PRESET_DIR / f"{name}.yaml").read_text(encoding="utf-8")) or {}
    return theme_from_data(data, name)


def _preset_names() -> list[str]:
    return sorted(p.stem for p in PRESET_DIR.glob("*.yaml"))


_REGISTRY: dict[str, Theme] = {"none": Theme(name="none")}


def register(theme: Theme) -> None:
    _REGISTRY[theme.name] = theme


def get_theme(name: str) -> Theme:
    if name in _REGISTRY:
        return _REGISTRY[name]
    if name in _preset_names():
        return _preset(name)
    raise KeyError(f"unknown theme {name!r}; available: {', '.join(available())}")


def available() -> list[str]:
    return sorted(set(_REGISTRY) | set(_preset_names()))


DEFAULT = _preset("default")
MIDNIGHT = _preset("midnight")
JP_BUSINESS = _preset("jp-business")


# --------------------------------------------------------------------------- inline tokens

TOKEN_GROUPS = ("colors", "fonts", "sizes", "style")
# short `style:` keys -> canonical token paths
STYLE_ALIASES = {
    "radius": "classes.card.radius",
    "padding": "classes.card.padding",
    "shadow": "classes.card.shadow",
    "border": "classes.card.line",
    "border-width": "classes.card.line_width",
    "card": "classes.card.fill",
    "bg": "colors.bg",
    "fg": "colors.fg",
    "margin": "margin_x",
    "ink.auto": "render.ink_auto",
    "kpi.h": "layout.kpi_h",
    "grow.max": "layout.grow_max",
    "card.heading.max": "layout.card_heading_max_pt",  # wave 2026-10-08 lane E
    "card.text.max": "layout.card_body_max_pt",
}
_STYLE_FIELDS = tuple(Style.model_fields)
_NUM = re.compile(r"^-?\d+(?:\.\d+)?$")


def _norm(key: str) -> str:
    return key.strip().replace("-", "_")


def token_paths(theme: Theme | None = None) -> list[str]:
    """Every settable canonical token path (for did-you-mean hints and ``slidemark tokens``)."""
    th = theme or Theme(name="none")
    out: list[str] = []
    for f in Theme.model_fields:
        if f in ("name", "card_line_set"):  # (card_line_set: set by `card.line` / `card.border`, not a token)
            continue
        if f == "colors":
            out += [f"colors.{k}" for k in th.colors]
        elif f == "sizes":
            out += [f"sizes.{k}" for k in th.sizes]
        elif f == "fonts":
            out += [f"fonts.{k}" for k in Fonts.model_fields]
        elif f in ("layout", "render"):
            model = LayoutTokens if f == "layout" else RenderTokens
            out += [f"{f}.{k}" for k in model.model_fields]
        elif f == "classes":
            out += [f"classes.{c}.{k}" for c in th.classes for k in _STYLE_FIELDS]
        else:
            out.append(f)
    return out


def canonical_token(group: str, key: str) -> tuple[str | None, str]:
    """Map a header token (``group`` line, ``key``) to a canonical path, or (None, hint).

    ``colors:`` accepts any color name (new names become theme colors usable everywhere). ``sizes:`` takes
    text roles. ``style:`` takes any other path: a Theme field (``gap``, ``title.band`` = ``title_band``),
    ``<class>.<style field>`` (``card.fill``, ``hero.color``: unknown classes are created),
    ``layout.<x>``, ``render.<x>``, a full path (``colors.bg``) or a short alias (``radius``).
    """
    g = group.lower()
    k = key.strip()
    if not k:
        return None, "write key=value pairs, e.g. 'colors: primary=#7C5CFF'"
    if g == "colors":
        if not re.fullmatch(r"[A-Za-z][\w-]*", k):
            return None, "color names are words, e.g. primary, brand-2"
        return f"colors.{k}", ""
    if g == "fonts":
        if k in Fonts.model_fields:
            return f"fonts.{k}", ""
        return None, _did_you_mean(k, list(Fonts.model_fields))
    if g == "sizes":
        if k in DEFAULT_SIZES or k in ("kpi", "conclusion"):
            return f"sizes.{k}", ""
        return None, _did_you_mean(k, list(DEFAULT_SIZES))
    # style: generic path
    if k in STYLE_ALIASES:
        return STYLE_ALIASES[k], ""
    parts = k.split(".")
    head = parts[0]
    if head in ("colors", "fonts", "sizes") and len(parts) == 2:
        return canonical_token(head, parts[1])
    if head in ("layout", "render") and len(parts) == 2:
        model = LayoutTokens if head == "layout" else RenderTokens
        f = _norm(parts[1])
        if f in model.model_fields:
            return f"{head}.{f}", ""
        return None, _did_you_mean(f, [f"{head}.{x}" for x in model.model_fields], prefix=f"{head}.")
    joined = _norm("_".join(parts))
    if len(parts) > 1 and joined in Theme.model_fields and joined not in ("classes", "layout", "render"):
        return joined, ""  # title.band -> title_band, table.header.fill -> table_header_fill
    if head == "classes" and len(parts) == 3:
        parts = parts[1:]
    if len(parts) == 2:
        cls, field = parts[0], _norm(parts[1])
        field = {"border": "line", "border_width": "line_width", "size": "font_size"}.get(field, field)
        if field in _STYLE_FIELDS and re.fullmatch(r"[A-Za-z][\w-]*", cls):
            return f"classes.{cls}.{field}", ""
        return None, _did_you_mean(field, list(_STYLE_FIELDS), prefix=f"{cls}.")
    f = _norm(k)
    if len(parts) == 1 and f in Theme.model_fields and f not in ("name", "classes", "layout", "render"):
        return f, ""
    cands = [p for p in token_paths() if not p.startswith("classes.")] + list(STYLE_ALIASES)
    return None, _did_you_mean(k, cands)


def _did_you_mean(key: str, cands: list[str], prefix: str = "") -> str:
    near = difflib.get_close_matches(key, [c.removeprefix(prefix) for c in cands], n=1, cutoff=0.6)
    tip = "`slidemark tokens` lists every token"
    return f"did you mean '{prefix}{near[0]}'? {tip}" if near else tip


def _value(raw: str) -> Any:
    v = raw.strip()
    if len(v) >= 2 and v[0] == v[-1] and v[0] in "\"'":
        return v[1:-1]
    if v.lower() in ("none", "null", "off"):
        return None
    if v.lower() in ("true", "on", "yes"):
        return True
    if v.lower() in ("false", "no"):
        return False
    if _NUM.match(v):
        return float(v) if "." in v else int(v)
    return v


def apply_tokens(theme: Theme, tokens: dict[str, str]) -> tuple[Theme, list[Diagnostic]]:
    """Apply canonical ``path -> raw value`` tokens (``Deck.tokens``) on top of ``theme``.

    Values are checked by field type and CSS-like shorthands are mapped (:func:`normalize_token`). Never
    raises: a token that does not validate is skipped with a ``bad-token`` diagnostic.
    """
    diags: list[Diagnostic] = []
    data = theme.model_dump()
    names = set(theme.colors) | {p.split(".", 1)[1] for p in tokens if p.startswith("colors.")}
    for path, raw in tokens.items():
        trial = copy.deepcopy(data)
        try:
            pairs = normalize_token(path, raw, names) if isinstance(raw, str) else [(path, raw)]
            for p, v in pairs:
                _set_path(trial, p.split("."), v)
            if any(p in _CARD_LINE_PATHS for p, _v in pairs):
                trial["card_line_set"] = True  # a shadowed card keeps the border the deck asked for
            if path.startswith("sizes.") and isinstance(raw, str) and raw.strip().endswith("!"):
                trial["pinned"] = [*trial.get("pinned", []), path.split(".", 1)[1]]  # `heading=20!`
            Theme.model_validate(trial)
        except TokenValueError as e:
            diags.append(_bad_token(path, raw, str(e), e.hint))
            continue
        except (ValidationError, ValueError, TypeError, KeyError) as e:
            why = e.errors()[0]["msg"] if isinstance(e, ValidationError) else str(e) or type(e).__name__
            diags.append(_bad_token(path, raw, why, _HINT_GENERIC))
            continue
        data = trial
    _derive_kpi_size(data, tokens)
    _derive_muted(data, tokens)
    _derive_surface(data, tokens)
    _derive_table_size(data, tokens)
    return Theme.model_validate(data), diags


def slide_theme(theme: Theme, slide: Any) -> Theme:
    """``theme`` with the slide's own ``sizes:`` / ``style:`` tokens on top (itself when it has none).

    Never raises: tokens were checked by the parser; one that still fails is skipped."""
    tokens = getattr(slide, "tokens", None)
    if not tokens:
        return theme
    try:
        return apply_tokens(theme, dict(tokens))[0]
    except Exception:  # noqa: BLE001 - a slide must still lay out
        return theme


def _derive_kpi_size(data: dict, tokens: dict[str, str]) -> None:
    """``sizes: kpi=34`` is the size of the KPI number: the ``kpi`` class font size (``kpi.size=`` wins)."""
    if "sizes.kpi" not in tokens or "classes.kpi.font_size" in tokens:
        return
    size = data.get("sizes", {}).get("kpi")
    kpi = data.get("classes", {}).get("kpi")
    if isinstance(size, (int, float)) and isinstance(kpi, dict):
        kpi["font_size"] = float(size)


def _derive_table_size(data: dict, tokens: dict[str, str]) -> None:
    """An explicit ``sizes: table=`` is final: the late text growth of stretched tables stays off."""
    if "sizes.table" in tokens and "layout.table_vtext_max" not in tokens:
        data.setdefault("layout", {})["table_vtext_max"] = 1.0


def _hex_rgb(v: Any) -> tuple[float, float, float] | None:
    if not isinstance(v, str) or not re.fullmatch(r"#[0-9A-Fa-f]{6}([0-9A-Fa-f]{2})?", v):
        return None
    return tuple(int(v[i : i + 2], 16) / 255 for i in (1, 3, 5))  # type: ignore[return-value]


def _rel_lum(c: tuple[float, float, float]) -> float:
    lin = [x / 12.92 if x <= 0.03928 else ((x + 0.055) / 1.055) ** 2.4 for x in c]
    return 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2]


def _derive_muted(data: dict, tokens: dict[str, str]) -> None:
    """A deck that sets its own bg/fg but no ``muted`` gets a muted color between them that stays readable.

    The preset's grey is made for its own background: on a dark brand ``bg`` it fails contrast (lead lines,
    captions). Muted = fg mixed 35% toward bg, which keeps ≥ 4.5:1 on any bg/fg pair with ≥ 10:1.
    """
    if "colors.muted" in tokens or not ({"colors.bg", "colors.fg"} & set(tokens)):
        return
    cols = data.get("colors") or {}
    bg, fg, muted = (_hex_rgb(cols.get(k)) for k in ("bg", "fg", "muted"))
    if not (bg and fg and muted):
        return
    lo, hi = sorted((_rel_lum(muted), _rel_lum(bg)))
    if (hi + 0.05) / (lo + 0.05) >= 4.5:
        return
    mix = [f + (b - f) * 0.35 for f, b in zip(fg, bg, strict=True)]
    cols["muted"] = "#" + "".join(f"{round(x * 255):02X}" for x in mix)


def _mix_hex(a: tuple[float, ...], b: tuple[float, ...], t: float) -> str:
    return "#" + "".join(f"{round((x + (y - x) * t) * 255):02X}" for x, y in zip(a, b, strict=True))


def _derive_surface(data: dict, tokens: dict[str, str]) -> None:
    """A deck that sets its own bg/fg but no ``surface`` / ``border`` gets cards that stand out from the bg.

    The preset's light grey surface would be a white card on a dark brand bg (white text on it is unreadable)
    and its border would vanish. A preset value is kept while it still works (fg reads on the surface at 4.5:1
    and the surface differs from bg); otherwise surface = bg mixed toward fg until the two differ (>= 1.1:1,
    6% to start), border = bg mixed 25% toward fg.
    """
    if not ({"colors.bg", "colors.fg"} & set(tokens)):
        return
    cols = data.get("colors") or {}
    bg, fg = _hex_rgb(cols.get("bg")), _hex_rgb(cols.get("fg"))
    if not (bg and fg):
        return

    def rat(a: tuple[float, ...], b: tuple[float, ...]) -> float:
        lo, hi = sorted((_rel_lum(a), _rel_lum(b)))
        return (hi + 0.05) / (lo + 0.05)

    surface = _hex_rgb(cols.get("surface"))
    if "colors.surface" not in tokens and not (
        surface and rat(fg, surface) >= 4.5 and rat(bg, surface) >= 1.03
    ):
        t = 0.06
        while t < 0.3 and rat(bg, tuple(b + (f - b) * t for b, f in zip(bg, fg, strict=True))) < 1.1:
            t += 0.02
        cols["surface"] = _mix_hex(bg, fg, t)
    border = _hex_rgb(cols.get("border"))
    if "colors.border" not in tokens and not (border and rat(bg, border) >= 1.2):
        cols["border"] = _mix_hex(bg, fg, 0.25)


def derive_ink(theme: Theme, explicit: set[str] | frozenset[str] = frozenset()) -> Theme:
    """Make the theme's default text colors readable (``render.ink_auto``), never touching the deck's own.

    ``explicit`` holds the canonical token paths the deck set (``Deck.tokens`` keys): those fields are kept
    and left for lint to report. Text drawn on a theme fill (conclusion bar, title / heading band, table
    header, badge, any class with a fill and a color) keeps its color while it reaches
    ``render.contrast_min``,
    else becomes the best of fg / bg / white / black. Text in a theme color on the bg / card surface (KPI
    numbers, heading and lead colors, color-only classes) keeps it while it reaches 4.5:1 (3:1 at
    ``render.large_pt`` and above), else becomes the nearest passing shade of the same hue. Fills never
    change.
    Presets that already read are returned unchanged.
    """
    if not theme.render.ink_auto:
        return theme
    upd: dict[str, Any] = {}
    classes = {k: v.model_copy() for k, v in theme.classes.items()}

    def on_fill(path: str, color: str | None, fill: str | None) -> str | None:
        if path in explicit or not color or not fill or theme.hexval(fill) is None:
            return None
        ink = theme.ink_on(fill, color)
        return None if ink == color else ink

    for field, fill in (
        ("conclusion_color", theme.conclusion_fill),
        ("title_band_color", theme.title_band),
        ("heading_band_color", theme.heading_band),
        ("table_header_color", theme.table_header_fill),
    ):
        if (new := on_fill(field, getattr(theme, field), fill)) is not None:
            upd[field] = new

    def in_color(path: str, color: str | None, size: float | None, backs: list[str]) -> str | None:
        hx = theme.hexval(color)
        if path in explicit or not hx or color in _BASE_COLORS or not backs:
            return None
        got = _shade(hx, tuple(backs), theme.need_for(size))
        return None if got == hx else got

    cards = theme.surface_backs()
    plain = [b for b in (theme.hexval("bg"),) if b]
    for field, backs in (("heading_color", cards), ("lead_color", plain)):
        if (
            new := in_color(field, getattr(theme, field), theme.sizes.get(field.split("_")[0]), backs)
        ) is not None:
            upd[field] = new
    for name, st in theme.classes.items():
        path = f"classes.{name}.color"
        if st.fill:
            new = on_fill(path, st.color, st.fill)
        else:
            size = st.font_size or theme.sizes.get(name) or theme.sizes.get("body")
            new = in_color(path, st.color, size, cards)
        if new is not None:
            classes[name] = st.model_copy(update={"color": new})
    if not upd and all(classes[k] == v for k, v in theme.classes.items()):
        return theme
    return theme.model_copy(update={**upd, "classes": classes})


def _bad_token(path: str, raw: Any, why: str, hint: str) -> Diagnostic:
    return Diagnostic(
        level="warning",
        message=f"token {path}={raw!s}: {why[:100]}",
        rule="bad-token",
        hint=hint.replace("\n", " "),
    )


# --------------------------------------------------------------------------- token value types


class TokenValueError(ValueError):
    """A token value of the wrong type; ``hint`` is a one-line fix with a valid example."""

    def __init__(self, message: str, hint: str):
        super().__init__(message)
        self.hint = hint


_HINT_GENERIC = "check the value type (color #RRGGBB or name, number, length like 12pt/0.3in)"
_HINT_COLOR = "use #RRGGBB, rgb(...), a CSS color name, a theme color name, or none, e.g. #B08D57"
_HINT_FILL = "use a color, none, linear-gradient(135deg, #AAA, #BBB) or url(path), e.g. #F3F4F6"
_HINT_LEN = "use a number (pt) or a length like 12pt, 0.3in, 8px, 1cm"
_HINT_BORDER = (
    "write '<width> <solid|dashed|dotted> <color>' in any order, e.g. 0.75pt solid #B08D57, or none"
)
_HINT_SHADOW = "write none, on, or '<x> <y> <blur> <color>' in pt, e.g. 0 2 6 #00000040"
_IDENT = re.compile(r"[A-Za-z][\w-]*")
_KEYWORDS = {"none", "hidden", "solid", "dashed", "dotted", "double", "thin", "medium", "thick"}
_PT_FIELDS = {"font_size", "line_width", "radius", "letter_spacing"}
_PT_PATHS = {
    "min_font_size",
    "render.line_width",
    "render.connector_width",
    "render.chart_line_width",
    "render.chart_pie_line_width",
    "box_num_size",
    "kpi_band_size",
    "kpi_unit_size",
    "matrix_axis_size",
    "agenda_num_size",
    "statement_size",
    "statement_sub_size",
    "vs_win_w",
}
_THEME_COLOR_SUFFIX = ("_fill", "_color", "_band", "_border", "_bar", "_rule", "_stripe")
_OPTIONAL_COLORS = {
    "title_band",
    "heading_band",
    "muted_band",
    "table_zebra_fill",
    "table_hl_fill",
    "table_hl_color",
    "cover_rule",
    "cover_bar",
    "cover_top_bar",
    "cover_bottom_bar",
    "top_bar",
    "bottom_bar",
    "title_rule",
    "kpi_stripe",
    "kpi_rule",
    "kpi_band",
    "kpi_band_color",
    "kpi_unit_color",
    "bullet_color",
    "steps_caption_color",
    "heading_rule",
    "rows_glyph_color",
    "box_num_fill",
    "box_num_color",
    "timeline_date_color",
    "vs_badge_color",
    "vs_verdict_color",
    "vs_win_fill",
    "funnel_color",
    "pyramid_color",
    "cycle_color",
    "statement_color",
    "statement_sub_color",
    "agenda_rule",
    "agenda_dim",
}
# DL3b colour tokens whose name has no colour suffix
_VOCAB_COLORS = {
    "timeline_line",
    "timeline_dot",
    "timeline_now",
    "vs_win_line",
    "cycle_arrow",
    "agenda_now",
    "agenda_dim",
}
# DL3b tokens holding a list of colours (cycled / read in reading order)
_VOCAB_LISTS = {"matrix_fill", "funnel_fill", "pyramid_fill", "cycle_fill"}
_MEDIUM_PT = 2.25  # CSS `medium` border width (3px)


def _is_length_type(annotation: Any) -> bool:
    return {a for a in getattr(annotation, "__args__", ()) if a is not type(None)} == {str, float, int}


@cache
def _length_fields() -> frozenset[str]:
    out = {f"layout.{k}" for k, f in LayoutTokens.model_fields.items() if _is_length_type(f.annotation)}
    out |= {k for k, f in Theme.model_fields.items() if _is_length_type(f.annotation)}
    return frozenset(out)


def _unquote(v: str) -> str:
    v = v.strip()
    return v[1:-1] if len(v) >= 2 and v[0] == v[-1] and v[0] in "\"'" else v


def _color_value(raw: str, names: set[str] | None, hint: str = _HINT_COLOR) -> str:
    """Normalized color; ``names=None`` (parse time) accepts any bare word: it may be declared later."""
    from .parser.css import parse_color

    v = _unquote(raw)
    if v.lower() in ("none", "null", "off"):
        return "#00000000"
    c = parse_color(v, names or set())
    if c is None and names is None and _IDENT.fullmatch(v):
        return v
    if c is None:
        raise TokenValueError(f"'{v}' is not a color", hint)
    return c


def _pt_value(raw: str) -> float:
    """A length as a pt number: bare numbers are pt, units convert (``0.3in`` -> 21.6)."""
    from .units import to_emu

    v = _unquote(raw)
    if _NUM.match(v):
        return float(v)
    try:
        return round(to_emu(v) / 12700, 3)
    except (ValueError, KeyError):
        raise TokenValueError(f"'{v}' is not a length", _HINT_LEN) from None


def _length_value(raw: str) -> str | float | int:
    from .units import to_emu

    v = _unquote(raw)
    if _NUM.match(v):
        return float(v) if "." in v else int(v)
    try:
        to_emu(v, 100)
    except (ValueError, KeyError):
        raise TokenValueError(f"'{v}' is not a length", _HINT_LEN) from None
    return v


def _border_parts(raw: str, names: set[str] | None) -> tuple[float | None, str | None, str | None, bool]:
    """(width pt, dash, color, none) of a border shorthand, like the css parser's ``border``."""
    from .parser.css import BadValue, Maps, split_tokens

    toks = [f"{t}pt" if _NUM.match(t) else t for t in split_tokens(_unquote(raw))]
    if not toks:
        raise TokenValueError("empty border", _HINT_BORDER)
    if names is None:  # parse time: a bare word may be a color declared later
        toks = ["#000" if _IDENT.fullmatch(t) and t.lower() not in _KEYWORDS else t for t in toks]
    try:
        return Maps(names or set(), None)._border_parts(" ".join(toks))
    except BadValue as e:
        raise TokenValueError(str(e), _HINT_BORDER) from None


def _side_value(raw: str, names: set[str] | None) -> str:
    from .parser.css import fmt

    width, dash, color, none = _border_parts(raw, names)
    if none:
        return "none"
    return f"{fmt(_MEDIUM_PT if width is None else width)}pt {dash or 'solid'} {color or 'fg'}"


def _shadow_value(raw: str, names: set[str] | None) -> bool | str:
    from .parser.css import fmt, parse_color, split_tokens

    v = _unquote(raw)
    low = v.lower()
    if low in ("none", "off", "false", "no"):
        return False
    if low in ("on", "true", "yes"):
        return True
    lens: list[float] = []
    color: str | None = None
    for t in split_tokens(v):
        if _NUM.match(t) or re.fullmatch(r"-?[\d.]+(pt|px|in|cm|mm)", t):
            lens.append(_pt_value(t))
            continue
        c = parse_color(t, names or set())
        if c is None and names is None and _IDENT.fullmatch(t):
            c = t
        if c is None:
            raise TokenValueError(f"'{t}' is not a number or color in shadow", _HINT_SHADOW)
        color = c
    if not 2 <= len(lens) <= 4:
        raise TokenValueError("a shadow needs x, y [, blur [, spread]]", _HINT_SHADOW)
    while len(lens) < 3:
        lens.append(0.0)
    if color is None:
        color = "#00000040"
    elif re.fullmatch(r"#[0-9A-F]{6}", color):
        color += "FF"
    return " ".join([*(fmt(x) for x in lens), color])


def _line_pairs(base: str, raw: str, names: set[str] | None) -> list[tuple[str, Any]]:
    """``<class>.line`` (``border``): a color, or a CSS border shorthand (width, style, color, none)."""
    width, dash, color, none = _border_parts(raw, names)
    if none:
        return [(f"{base}.line_width", 0.0)]
    out: list[tuple[str, Any]] = []
    if color:
        out.append((f"{base}.line", color))
    if width is not None:
        out.append((f"{base}.line_width", round(width, 3)))
    if dash:
        out.append((f"{base}.line_dash", dash))
    return out


def _fill_value(path: str, raw: str, names: set[str] | None) -> list[tuple[str, Any]]:
    from .parser.css import BadValue, gradient, is_gradient

    v = _unquote(raw)
    if is_gradient(v):
        try:
            return [(path, gradient(v, names or set()))]
        except BadValue as e:
            raise TokenValueError(str(e), _HINT_FILL) from None
    if re.fullmatch(r"url\(.*\)", v, re.I | re.S):
        return [(path, v)]
    return [(path, _color_value(v, names, _HINT_FILL))]


_COLOR_LISTS = {
    "rows_stripe",
    "box_stripe",
    "item_stripe",
    "kpi_stripe",
    "box_num_fill",
    "box_num_color",
}  # one colour, or a list that cycles over the cards
_SIDE_PATHS = {"box_stripe_side", "item_stripe_side", "kpi_stripe_side"}
_DL2_PATHS = {
    *_COLOR_LISTS,
    *_SIDE_PATHS,
    "box_num_text",
    "cover_bar",
    "cover_stripes",
    "cover_rule_pos",
    "title_rule2",
    "box_items",
    "render.chevron_shape",
    *_VOCAB_LISTS,
}
_CHEVRON_SHAPES = ("chevron", "pentagon", "homeplate")


def _opt_color(raw: str, names: set[str] | None) -> str | None:
    return None if _unquote(raw).lower() in ("none", "null", "off") else _color_value(raw, names)


def _dl2_value(path: str, raw: str, names: set[str] | None) -> list[tuple[str, Any]]:
    """Tokens whose value is more than one color or a word of a short list (DL2: edge bar, stripes, lists)."""
    v = _unquote(raw)
    if path == "cover_bar":  # `accent` | `accent@edge`
        col, at, where = v.partition("@")
        if at and where.strip().lower() != "edge":
            raise TokenValueError(f"'@{where}' is not a cover bar position", "write cover.bar=accent@edge")
        got = _opt_color(col, names)
        return [(path, None if got is None else got + ("@edge" if at else ""))]
    if path == "cover_stripes":  # `#1C3A68@8.9in,secondary@10.2in`
        if v.lower() in ("none", "null", "off"):
            return [(path, None)]
        out = []
        for item in (s.strip() for s in v.split(",")):
            col, at, pos = item.rpartition("@")
            if not at or not col or not pos:
                raise TokenValueError(
                    f"'{item}' is not <color>@<x>",
                    "write cover.stripes=#1C3A68@8.9in,secondary@10.2in (a color and where it starts)",
                )
            try:
                _length_value(pos)
            except TokenValueError:
                raise TokenValueError(f"'{pos}' is not a length", _HINT_LEN) from None
            out.append(f"{_color_value(col, names)}@{pos}")
        return [(path, ",".join(out))]
    if path == "cover_rule_pos":
        if v.lower() not in ("above", "below"):
            raise TokenValueError("cover.rule_pos is above or below", "write cover.rule_pos=above (or below)")
        return [(path, v.lower())]
    if path == "title_rule2":
        return [(path, _opt_color(raw, names))]
    if path in _SIDE_PATHS:
        key = path.replace("_", ".", 1).replace("_", ".")
        if v.lower() not in ("top", "left", "right", "bottom"):
            raise TokenValueError(f"{key} is top, left, right or bottom", f"write {key}=left (or top)")
        return [(path, v.lower())]
    if path == "box_num_text":
        if "{n}" not in v and "{nn}" not in v:
            raise TokenValueError(
                "box.num.text needs {n} or {nn}", 'write box.num.text="{nn}" (01) or "{n}" (1)'
            )
        return [(path, v)]
    if path in _COLOR_LISTS or path in _VOCAB_LISTS:  # one color, or a list that cycles
        if v.lower() in ("none", "null", "off"):
            return [(path, None)]
        items = [p.strip() for p in v.split(",") if p.strip()]
        key = path.replace("_", ".")
        if not items:
            raise TokenValueError(f"{key} needs a color", f"write {key}=primary,secondary")
        if path == "matrix_fill" and len(items) > 4:
            raise TokenValueError("matrix.fill takes at most four colors", "write matrix.fill=a,b,c,d")
        return [(path, ",".join(_color_value(p, names) for p in items))]
    if path == "box_items":
        if v.lower() not in ("cards", "bullets"):
            raise TokenValueError("box.items is cards or bullets", "write box.items=cards (or bullets)")
        return [(path, v.lower())]
    items = [p.strip().lower() for p in v.split(",") if p.strip()]  # render.chevron_shape
    if not items or any(i not in _CHEVRON_SHAPES for i in items):
        raise TokenValueError(
            f"'{v}' is not a chevron shape",
            "write render.chevron_shape=pentagon or pentagon,chevron (first arrow, then the rest)",
        )
    return [(path, ",".join(items))]


# --- wave 2026-10-08 lane A: icon discs, card elevation, conclusion icon
ELEVATIONS: dict[int, bool | str] = {
    0: False,
    1: "0 1 4 #0000001F",
    2: "0 3 12 #00000030",
    3: "0 8 24 #00000040",
}
DISC_SHAPES = ("circle", "rounded", "square")
_DISC_SHAPE_ALIASES = {
    "round": "circle",
    "ellipse": "circle",
    "oval": "circle",
    "roundrect": "rounded",
    "rounded-rect": "rounded",
    "rounded-square": "rounded",
    "rect": "square",
    "rectangle": "square",
    "box": "square",
}
_CARD_LINE_PATHS = ("classes.card.line", "classes.card.line_width", "classes.card.line_dash")


def disc_shape(raw: object) -> str | None:
    """``circle`` / ``rounded`` / ``square`` of a disc-shape word (or a synonym); ``None`` if unknown."""
    v = str(raw).strip().lower()
    v = _DISC_SHAPE_ALIASES.get(v, v)
    return v if v in DISC_SHAPES else None


def _lane_a_value(path: str, raw: str, names: set[str] | None) -> list[tuple[str, Any]] | None:
    """``icon.disc`` ``.size`` ``.shape``, ``icon.color``, ``card.elevation``, ``conclusion.icon``.

    ``None`` = not one of them (the generic rules apply)."""
    v = _unquote(raw)
    low = v.lower()
    if path in ("icon_disc", "icon_color"):
        if low in ("none", "null", "off", "no", "false"):
            return [(path, None)]
        if path == "icon_disc" and low in ("on", "yes", "true"):
            return [(path, "primary")]
        return [(path, _color_value(raw, names))]
    if path == "icon_disc_size":
        if low in ("none", "null", "off", "auto"):
            return [(path, None)]
        return [(path, _length_value(raw))]
    if path == "icon_disc_shape":
        got = disc_shape(v)
        if got is None:
            near = difflib.get_close_matches(low, [*DISC_SHAPES, *_DISC_SHAPE_ALIASES], n=1, cutoff=0.5)
            tip = f"did you mean '{near[0]}'? " if near else ""
            raise TokenValueError(
                f"'{v}' is not a disc shape", f"{tip}write icon.disc.shape=circle, rounded or square"
            )
        return [(path, got)]
    if path == "card_elevation":
        if low in ("none", "off"):
            low = "0"
        if low not in ("0", "1", "2", "3"):
            raise TokenValueError(
                f"'{v}' is not an elevation", "write card.elevation=0 (flat), 1, 2 (soft) or 3 (deep)"
            )
        level = int(low)
        return [(path, level), ("classes.card.shadow", ELEVATIONS[level])]
    if path == "conclusion_icon":
        if low in ("none", "null", "off", "no", "false"):
            return [(path, None)]
        from . import icons

        if icons.is_file(v):
            return [(path, v)]
        if not icons.path(low):
            near = difflib.get_close_matches(low, icons.names(), n=1, cutoff=0.4)
            raise TokenValueError(
                f"unknown icon '{v}'",
                f"did you mean '{near[0]}'? or icon=file.svg for your own"
                if near
                else "see 'slidemark docs icons'",
            )
        return [(path, low)]
    return None


# --- wave 2026-10-08 lane D: steps.head, iconlist.fill / valign, cover.art*
_ON = ("on", "true", "yes", "1")
_OFF = ("off", "false", "no", "0", "none")


def _lane_d_value(path: str, raw: str, names: set[str] | None) -> list[tuple[str, Any]] | None:
    """``steps.head`` ``iconlist.fill`` ``iconlist.valign`` ``cover.art`` ``cover.art.color`` ``.opacity``
    ``.seed`` ``.split``. ``None`` = not one of them (the generic rules apply)."""
    if path not in (
        "steps_head",
        "iconlist_fill",
        "iconlist_valign",
        "cover_art",
        "cover_art_color",
        "cover_art_opacity",
        "cover_art_seed",
        "cover_art_split",
    ):
        return None
    v = _unquote(raw)
    low = v.lower()
    key = path.replace("_", ".")

    def pick(words: tuple[str, ...], hint: str) -> list[tuple[str, Any]]:
        if low not in words:
            near = difflib.get_close_matches(low, words, n=1, cutoff=0.5)
            tip = f"did you mean '{near[0]}'? " if near else ""
            raise TokenValueError(f"'{v}' is not a {key} value", f"{tip}{hint}")
        return [(path, low)]

    if path == "steps_head":
        return pick(("card", "arrow"), "write steps.head=card (heading in the card) or steps.head=arrow")
    if path == "iconlist_valign":
        low = {"middle": "center", "centre": "center"}.get(low, low)
        return pick(("top", "center"), "write iconlist.valign=top or center")
    if path == "iconlist_fill":
        if low in _ON:
            return [(path, True)]
        if low in _OFF:
            return [(path, False)]
        raise TokenValueError("iconlist.fill is on or off", "write iconlist.fill=off (or on)")
    if path == "cover_art":
        low = "none" if low in _OFF else low
        return pick(("none", "network", "dots", "rings"), "write cover.art=network, dots, rings or none")
    if path == "cover_art_color":
        return [(path, None if low in ("none", "auto") else _color_value(raw, names))]
    try:
        if path == "cover_art_seed":
            return [(path, int(float(low)))]
        num = float(low[:-1]) / 100 if low.endswith("%") else float(low)
        if path == "cover_art_opacity" and not 0.05 <= num <= 1.0:
            raise ValueError
        if path == "cover_art_split" and not 0.3 <= num <= 0.9:
            raise ValueError
        return [(path, num)]
    except ValueError:
        ranges = {
            "cover_art_opacity": "0.05 to 1 (or 40%)",
            "cover_art_split": "0.3 to 0.9 (the title's share of the width)",
            "cover_art_seed": "a whole number",
        }
        raise TokenValueError(
            f"'{v}' is not valid for {key}", f"write {key}= {ranges.get(path, 'a number')}"
        ) from None


def normalize_token(path: str, raw: str, names: set[str] | None) -> list[tuple[str, Any]]:
    """Validate a raw token value by its field type and map CSS-like shorthands.

    Returns the ``(canonical path, typed value)`` pairs to set (a border shorthand sets up to three).
    ``names`` are the known theme color names; ``None`` is the lenient parse-time mode where any bare word
    passes as a possibly later-declared color. Raises :class:`TokenValueError` (message + one-line hint).
    """
    from .forms2 import normalize as forms2_normalize
    from .forms3 import normalize as forms3_normalize
    from .forms4 import normalize as forms4_normalize

    if (got := forms2_normalize(path, raw, names)) is not None:  # DL3b part 2: iconlist.* quote.* ...
        return got
    if (got := forms3_normalize(path, raw, names)) is not None:  # DL3d part 2: steps-card.h quote.bar ...
        return got
    if (got := _lane_a_value(path, raw, names)) is not None:  # icon.disc* icon.color card.elevation ...
        return got
    if (got := forms4_normalize(path, raw, names)) is not None:  # wave 2026-10-08 lane B: cycle.center ...
        return got
    if (
        got := _lane_d_value(path, raw, names)
    ) is not None:  # wave 2026-10-08 lane D: steps.head cover.art ...
        return got
    if path == "heading_wrap":  # wave 2026-10-08 lane F
        return _lane_f_value(path, raw)
    parts = path.split(".")
    leaf = parts[-1]
    in_class = len(parts) == 3 and parts[0] == "classes"
    if in_class and leaf == "line":
        return _line_pairs(".".join(parts[:2]), raw, names)
    if (
        in_class
        and leaf == "fill"
        and parts[1] in ("steps-arrow", "steps-card", "rows-num")
        and "," in raw
        and "(" not in raw
    ):
        items = [p.strip() for p in _unquote(raw).split(",") if p.strip()]
        return [(path, ",".join(_color_value(p, names) for p in items))]  # cycled over the steps
    if in_class and leaf == "fill":
        return _fill_value(path, raw, names)
    if in_class and leaf == "color":
        return [(path, _color_value(raw, names))]
    if in_class and leaf.startswith("border_"):
        return [(path, _side_value(raw, names))]
    if (in_class and leaf == "shadow") or path == "render.shadow":
        val = _shadow_value(raw, names)
        if path == "render.shadow" and not isinstance(val, str):
            raise TokenValueError("render.shadow needs x y blur color", _HINT_SHADOW)
        return [(path, val)]
    if path == "render.ink_auto":
        flag = _unquote(raw).lower()
        if flag in ("on", "true", "yes", "1"):
            return [(path, True)]
        if flag in ("off", "false", "no", "0", "none"):
            return [(path, False)]
        raise TokenValueError("ink.auto is on or off", "write 'style: ink.auto=off' (or on)")
    if path == "cover_band":  # `cover.band=none` / `off` = no band; anything else = on
        return [(path, _unquote(raw).lower() not in ("none", "off", "no", "false", "0"))]
    if path in _DL2_PATHS:
        return _dl2_value(path, raw, names)
    if path == "palette":
        items = [p.strip() for p in _unquote(raw).split(",") if p.strip()]
        return [(path, [_color_value(p, names) for p in items])]
    if parts[0] == "colors" or path in (
        "render.ink_dark",
        "render.ink_light",
        "render.highlight",
        "render.chart_grid",
        "render.chart_pie_line",
    ):
        return [(path, _color_value(raw, names))]
    if path in ("vs_badge_text", "agenda_num_text"):
        return [(path, _unquote(raw))]
    if len(parts) == 1 and leaf in _VOCAB_COLORS:
        if leaf in _OPTIONAL_COLORS and _unquote(raw).lower() in ("none", "null", "off"):
            return [(path, None)]
        return [(path, _color_value(raw, names))]
    if len(parts) == 1 and leaf.endswith(_THEME_COLOR_SUFFIX) and leaf in Theme.model_fields:
        if leaf in _OPTIONAL_COLORS and _unquote(raw).lower() in ("none", "null", "off"):
            return [(path, None)]
        return [(path, _color_value(raw, names))]
    if parts[0] == "sizes":  # `20!` pins the size against the layout's growth
        return [(path, _pt_value(_unquote(raw).removesuffix("!")))]
    if (in_class and leaf in _PT_FIELDS) or path in _PT_PATHS:
        return [(path, _pt_value(raw))]
    if path in _length_fields() or (
        in_class and leaf in Style.model_fields and _is_length_type(Style.model_fields[leaf].annotation)
    ):
        return [(path, _length_value(raw))]
    return [(path, _value(raw))]


def _set_path(data: dict, parts: list[str], value: Any) -> None:
    head, rest = parts[0], parts[1:]
    if not rest:
        if head == "palette" and isinstance(value, str):
            value = [p.strip() for p in value.split(",") if p.strip()]
        data[head] = value
        return
    node = data.get(head)
    if node is None:
        node = {}
        data[head] = node
    if not isinstance(node, dict):
        raise ValueError(f"{head} is not a group")
    if head == "classes" and len(rest) == 2 and rest[0] not in node:
        node[rest[0]] = {}
    if head == "classes" and len(rest) == 2 and node[rest[0]] is None:
        node[rest[0]] = {}
    _set_path(node, rest, value)


def schema_table(theme: Theme | None = None) -> list[tuple[str, str]]:
    """``(path, current value)`` rows for every token, for ``slidemark tokens``."""
    th = theme or Theme(name="none")
    data = th.model_dump()
    rows: list[tuple[str, str]] = []
    for path in token_paths(th):
        node: Any = data
        for p in path.split("."):
            node = node.get(p) if isinstance(node, dict) else None
        if path.startswith("classes.") and node is None:
            continue
        text = ",".join(node) if isinstance(node, list) else str(node)
        rows.append((path, "none" if node is None else text))
    return rows


# --------------------------------------------------------------------------- slide ink (dark backgrounds)

# Text that sits directly on the slide background (cards and tables keep their own colors).
_INK_SELECTORS = ("h1", "slide > p", ".plain > p", ".plain > h2")
_MUTED_SELECTORS = (".lead", ".subtitle", ".footnote")
_INK_MARK = -1  # CssRule.line of the rules this module adds (so a second call replaces them)


def _hex_str(rgb: tuple[float, ...]) -> str:
    return "#" + "".join(f"{round(min(max(x, 0.0), 1.0) * 255):02X}" for x in rgb)


def slide_ink(theme: Theme, bg: str | None, classes: list[str] | tuple[str, ...] = ()) -> dict[str, str]:
    """Text colors a slide needs on its own background: ``{"color": ink, "muted": softer ink}`` or ``{}``.

    ``dark`` always means light ink (``render.ink_light``), ``light`` dark ink (``render.ink_dark``), on
    whatever background (unless the theme defines that class itself). Without a class, a slide ``bg``
    (color, token name or gradient: every stop is judged) that gives the theme ``fg`` less than 4.5:1 switches
    to whichever ink contrasts more. Pure: it only reads ``theme`` and the arguments.
    """
    from .lint import _backs, _hex, contrast_ratio  # lint imports this module: import lazily

    rt = theme.render
    backs = _backs(bg, theme, None) if bg else []
    ref = backs or ([b] if (b := _hex("bg", theme)) else [])

    def worst(ink: str) -> float:
        c = _hex(ink, theme)
        return min((contrast_ratio(c, b) for b in ref), default=0.0) if c and ref else 0.0

    names = [c for c in classes if c in ("dark", "light") and c not in theme.classes]
    if names:
        ink = rt.ink_light if names[-1] == "dark" else rt.ink_dark
    elif backs:
        fg = worst("fg")
        ink = max((rt.ink_light, rt.ink_dark), key=worst)
        if fg >= 4.5 or worst(ink) <= fg:
            return {}
    else:
        return {}
    out = {"color": ink, "muted": ink}
    rgb = _hex(ink, theme)
    if rgb and ref:
        mean = tuple(sum(b[k] for b in ref) / len(ref) for k in range(3))
        soft = _hex_str(tuple(c + (m - c) * 0.22 for c, m in zip(rgb, mean, strict=True)))
        if worst(soft) >= 4.5:
            out["muted"] = soft
    return out


def apply_slide_ink(deck: Any, theme: Theme) -> None:
    """Give every slide that needs it the CSS rules of :func:`slide_ink` (idempotent, never raises).

    Colors declared for the slide win: a slide-scoped CSS rule (a fence inside the slide, or a deck rule
    naming ``slide``) that sets ``color`` on ``slide`` skips the slide, one on ``h1`` / ``p`` / ``.lead`` ...
    skips just that target; element ``{color=}`` attrs and ``@html`` slides are never touched.
    """
    from .ir import CssRule
    from .layout.css import slide_style

    try:
        for i, slide in enumerate(deck.slides):
            slide.css = [r for r in slide.css if r.line != _INK_MARK]
            if slide.html:
                continue
            fill = slide.background or slide_style(deck, slide, i).fill
            ink = slide_ink(theme, fill, slide.classes)
            if not ink:
                continue
            declared: set[str] = set()
            # Declarations for this slide always win. A deck-wide `h1 { color }` was chosen for the default
            # background: it yields to a slide's own `bg=` / `dark` / `light`, but not to a deck-wide
            # `slide { background }` (the deck painted both).
            local = slide.background or any(r.style.fill for r in slide.css) or "dark" in slide.classes
            local = local or "light" in slide.classes
            for r in [*(r for r in deck.css if not local or "slide" in r.selector), *slide.css]:
                if r.style.color is None:
                    continue
                last = re.split(r"\s*>\s*|\s+", r.selector.strip())[-1]
                declared |= set(re.findall(r"[.#]?[\w-]+", last))
            if "slide" in declared:
                continue
            rules = []
            for sels, color in ((_INK_SELECTORS, ink["color"]), (_MUTED_SELECTORS, ink["muted"])):
                for sel in sels:
                    key = re.split(r"\s*>\s*", sel)[-1]
                    if key not in declared:
                        rules.append(CssRule(selector=sel, style=Style(color=color), line=_INK_MARK))
            slide.css = [*rules, *slide.css]
    except Exception:  # never raise on user input: the slide keeps the theme colors
        return


# --- wave 2026-10-08 lane F: heading.wrap
def _lane_f_value(path: str, raw: str) -> list[tuple[str, Any]]:
    """``heading.wrap=on|off``: on lets a card heading wrap; off (the default) keeps one line in a row."""
    low = _unquote(raw).lower()
    if low in _ON:
        return [(path, True)]
    if low in _OFF:
        return [(path, False)]
    raise TokenValueError("heading.wrap is on or off", "write heading.wrap=on (headings may wrap) or off")

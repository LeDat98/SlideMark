"""Normal-density balance: a lone table grows its text and fills to the footnote gutter, cards over a table
hug their content, sparse text-card rows are top-anchored under the lead (examples 21 / 22)."""

from __future__ import annotations

import random

import pytest

from slidemark.ir import Table
from slidemark.theme import LayoutTokens

from .test_layout_l3_fill import cards, inside, lay, role

PT = 12700


def _table(placed):
    (t,) = [p for p in placed if isinstance(p.element, Table)]
    return t


def _size(p) -> float:
    return p.style.font_size * p.font_scale


def test_tokens_exist():
    lt = LayoutTokens()
    assert lt.table_wrap_ratio == 1.0 and lt.card_table_balance and lt.sparse_cards_top


def test_lone_table_grows_to_body_size_and_fills_to_the_gutter():
    placed, deck, theme = lay("22-en-launch-plan.md", 6)
    lead, foot = role(placed, "lead")[0], role(placed, "footnote")[0]
    t = _table(placed)
    assert _size(t) >= theme.sizes.get("body", 18) - 0.05  # not smaller than the deck's body text
    assert t.y - (lead.y + lead.h) <= 30 * PT  # top-anchored under the lead
    gap = foot.y - (t.y + t.h)
    assert 8 * PT <= gap <= 40 * PT  # reaches the footnote gutter, never into it
    assert not [d for d in deck.diagnostics if d.level == "error"]


def test_wrapped_table_cells_break_at_spaces_only():
    placed, _, _ = lay("22-en-launch-plan.md", 6)
    t = _table(placed)
    longest = max(
        len(w)
        for row in t.element.rows
        for c in row
        for p in c.paragraphs
        for r in p.runs
        for w in r.text.split()
    )
    widths = t.element.attrs["_col_w"]
    # the narrowest column still holds the longest word at the grown size (no mid-word break)
    assert min(widths) / PT > longest * _size(t) * 0.62 * 0.5


def test_wrap_pass_off_keeps_the_old_size():
    placed, _, _ = lay("22-en-launch-plan.md", 6, table_wrap_ratio=0)
    assert _size(_table(placed)) < 18


def test_cards_over_a_table_hug_and_share_rhythm():
    placed, _, _ = lay("22-en-launch-plan.md", 2)
    foot = role(placed, "footnote")[0]
    cs = cards(placed)
    assert len(cs) == 3 and len({c.h for c in cs}) == 1
    t = _table(placed)
    assert t.y >= cs[0].y + cs[0].h  # the table follows the cards
    assert t.y + t.h <= foot.y - 8 * PT  # a gutter above the footnote
    tops = set()
    for c in cs:
        (b,) = inside(placed, c)
        tops.add(b.y - c.y)
        assert c.y + c.h - (b.y + b.h) <= 14 * PT  # the tallest card has no hollow bottom
    assert len(tops) == 1  # first item at the same offset in every card


def test_card_table_balance_off_restores_old_geometry():
    on, _, _ = lay("22-en-launch-plan.md", 2)
    off, _, _ = lay("22-en-launch-plan.md", 2, card_table_balance=False)
    assert cards(off)[0].h > cards(on)[0].h


def test_sparse_cards_are_top_anchored_under_the_lead():
    placed, _, _ = lay("21-jp-dark-pitch.md", 2, band_shift=0.0)  # the band balance is tested apart
    lead = role(placed, "lead")[0]
    cs = cards(placed)
    assert min(c.y for c in cs) - (lead.y + lead.h) <= 30 * PT
    assert len({c.y for c in cs}) == 1 and len({c.h for c in cs}) == 1
    off, _, _ = lay("21-jp-dark-pitch.md", 2, sparse_cards_top=False, band_shift=0.0)
    assert min(c.y for c in cards(off)) > min(c.y for c in cs) + 20 * PT


def test_card_icons_travel_with_their_cards():
    placed, _, _ = lay("21-jp-dark-pitch.md", 2)
    heads = role(placed, "heading")
    icons = [p for p in placed if p.element.__class__.__name__ == "Shape" and p.element.shape == "icon"]
    assert len(icons) == len(heads) == 3
    for i, h in zip(sorted(icons, key=lambda p: p.x), sorted(heads, key=lambda p: p.x), strict=True):
        assert abs((i.y + i.h / 2) - (h.y + h.h / 2)) <= 6 * PT


WORDS = (
    "alpha beta gamma delta epsilon zeta eta theta iota kappa lambda mu nu xi omicron pi rho sigma".split()
)


@pytest.mark.parametrize("seed", range(12))
def test_fuzz_cards_and_tables_never_crash(seed):
    rng = random.Random(seed)

    def text(n):
        return " ".join(rng.choice(WORDS) for _ in range(rng.randint(1, n)))

    parts = ["# T", f"> {text(8)}"]
    if rng.random() < 0.7:
        k = rng.randint(1, 4)
        parts.append(f"@{k}")
        for _ in range(k):
            parts.append(f"## {text(3)}")
            parts += [f"- {text(7)}" for _ in range(rng.randint(1, 4))]
        parts.append("@end")
    if rng.random() < 0.8:
        cols = rng.randint(2, 6)
        parts.append("| " + " | ".join(text(2) for _ in range(cols)) + " |")
        parts.append("|" + "-|" * cols)
        for _ in range(rng.randint(1, 6)):
            parts.append("| " + " | ".join(text(6) for _ in range(cols)) + " |")
    if rng.random() < 0.5:
        parts.append(f"^ {text(6)}")
    placed, deck, _ = lay("x", 1, src="\n".join(parts) + "\n")
    assert not [d for d in deck.diagnostics if d.rule == "layout-error"]
    assert placed

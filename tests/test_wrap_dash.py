"""A number range (2027–2029, 10–12, 1/2027) is one word for line breaking; U+2060 is zero width."""

from __future__ import annotations

import pytest

from slidemark.layout import measure


@pytest.mark.parametrize("rng", ["2027–2029", "10–12", "1/2027", "2027-2029"])
def test_number_range_wraps_as_one_word(rng):
    seg = [(f"Chiến lược số {rng}", False, False)]
    w = measure.text_em(f"Chiến lược số {rng}")
    head = measure.text_em("Chiến lược số ")
    # wide enough for the text before the range plus half of the range: the range still moves down whole
    width_pt = (head + (w - head) * 0.5) * 20
    assert measure.count_lines(seg, width_pt, 20) == 2
    # a width for everything but the last digit does not leave the range's first half on line 1
    assert measure.count_lines(seg, (w - 0.01) * 20, 20) == 2
    assert measure.count_lines(seg, (w + 0.05) * 20, 20) == 1


def test_word_joiner_is_zero_width():
    assert measure.char_em("⁠") == 0.0
    a = measure.text_em("2027–2029")
    b = measure.text_em("2027⁠–⁠2029")
    assert abs(a - b) < 1e-9
    seg = [("x 2027⁠–⁠2029", False, False)]
    width = (measure.text_em("x 2027–2029") - 0.3) * 20  # the whole text just does not fit
    assert measure.count_lines(seg, width, 20) == 2  # the word wraps whole, never inside

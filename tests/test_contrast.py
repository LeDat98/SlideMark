import colorsys

import pytest

from slidemark.contrast import best_ink, nearest_passing, ratio


def _hue(c):
    r, g, b = (int(c[i : i + 2], 16) / 255 for i in (1, 3, 5))
    return colorsys.rgb_to_hls(r, g, b)[0] * 360


def test_known_ratios():
    assert ratio("#000000", "#FFFFFF") == pytest.approx(21.0)
    assert ratio("#777777", "#FFFFFF") == pytest.approx(4.48, abs=0.02)
    assert ratio("#ffffff", "#ffffff") == pytest.approx(1.0)


def test_lime_on_white_gets_darker_green():
    out = nearest_passing("#84CC16", ["#FFFFFF"])
    assert ratio(out, "#FFFFFF") >= 4.5
    assert abs(_hue(out) - _hue("#84CC16")) <= 3
    assert out != "#84CC16"


def test_passing_color_unchanged_uppercase():
    assert nearest_passing("#1f2937", ["#FFFFFF"]) == "#1F2937"


def test_dark_background_lightens():
    out = nearest_passing("#1D4ED8", ["#0F172A"])
    assert ratio(out, "#0F172A") >= 4.5
    assert colorsys.rgb_to_hls(*(int(out[i : i + 2], 16) / 255 for i in (1, 3, 5)))[1] > 0.5


def test_multiple_backs_and_impossible():
    out = nearest_passing("#888888", ["#FFFFFF", "#000000"], need=10)
    assert out in ("#000000", "#FFFFFF")


def test_best_ink():
    assert best_ink("#84CC16", ["#FFFFFF", "#1F2937"]) == "#1F2937"
    assert best_ink("#1F2937", ["#FFFFFF", "#000000"]) == "#FFFFFF"
    assert best_ink("#808080", ["#777777", "#000000"], need=21) == "#000000"


@pytest.mark.parametrize("bad", ["", "red", "#12", None, 5])
def test_bad_input_never_raises(bad):
    assert ratio(bad, "#FFFFFF") == 1.0
    assert nearest_passing(bad, ["#FFFFFF"]) == bad
    assert nearest_passing("#84CC16", [bad]) == "#84CC16"
    assert nearest_passing("#84CC16", []) == "#84CC16"
    assert best_ink(bad, ["#FFFFFF"]) in ("#FFFFFF",)
    assert best_ink("#FFFFFF", []) == "#000000"

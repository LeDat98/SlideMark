from slidemark.ir import Paragraph, Run, Style
from slidemark.layout import measure
from slidemark.units import EMU_PER_PT


def test_calibri_narrower_than_arial():
    s = "Phạm Quốc Dũng and the quick brown fox"
    cal, ari = measure.text_em(s, font="Calibri"), measure.text_em(s, font="Arial")
    assert 0.80 < cal / ari < 0.97
    cb, ab = measure.text_em(s, bold=True, font="Calibri"), measure.text_em(s, bold=True, font="Arial")
    assert cb < ab and cb > cal  # bold is wider than regular


def test_known_widths():
    assert abs(measure.char_em("a", font="Arial") - 0.556) < 0.01
    assert abs(measure.char_em("a", font="Carlito") - 0.479) < 0.01
    assert measure.char_em("M", font="Liberation Sans") > measure.char_em("i", font="Liberation Sans")


def test_unknown_font_uses_arial():
    assert measure.text_em("Hello world", font="Comic Foo") == measure.text_em("Hello world", font="Arial")


def test_vietnamese_and_combining():
    assert measure.char_em("ệ", font="Calibri") > 0.4  # precomposed, measured from the table
    assert measure.char_em("̣", font="Calibri") == 0.0  # combining dot below
    assert measure.char_em("Ữ", font="Arial") > 0.5


def test_mono_fixed_width():
    ws = {measure.char_em(c, "mono", "Consolas") for c in "iW m.,0"}
    assert len(ws) == 1
    assert measure.text_em("abcd", mono=True) == 4 * next(iter(ws))


def test_cjk_one_em_and_halfwidth():
    assert measure.char_em("日", font="Yu Gothic") == 1.0
    assert measure.char_em("ｱ", font="Yu Gothic") == 0.5
    assert measure.text_em("日本語") == 3.0


def test_japanese_font_latin_table():
    assert measure.font_key("Yu Gothic") == measure.font_key("Meiryo") == "jp"
    assert measure.text_em("Report", font="Yu Gothic") != measure.text_em("Report", font="Arial")


def test_heading_fits_one_line_in_calibri_not_in_arial():
    text = "Phạm Quốc Dũng Nguyễn"
    size = 20
    em_cal = measure.text_em(text, bold=True, font="Calibri")
    em_ari = measure.text_em(text, bold=True, font="Arial")
    width_pt = (em_cal + em_ari) / 2 * size  # between the two widths
    seg = [(text, True, False)]
    assert measure.count_lines(seg, width_pt, size, "Calibri") == 1
    assert measure.count_lines(seg, width_pt, size, "Arial") == 2


def test_paragraphs_height_uses_style_font():
    p = [Paragraph(runs=[Run(text="word " * 12)])]
    w = round(150 * EMU_PER_PT)
    h_cal = measure.paragraphs_height(p, w, Style(font="Calibri", font_size=14))
    h_ari = measure.paragraphs_height(p, w, Style(font="Arial", font_size=14))
    assert h_cal <= h_ari

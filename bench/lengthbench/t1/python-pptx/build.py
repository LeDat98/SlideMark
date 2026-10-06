from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.chart.data import CategoryChartData
from pptx.enum.chart import XL_CHART_TYPE, XL_LEGEND_POSITION, XL_LABEL_POSITION
from pptx.oxml.ns import qn
from lxml import etree

NAVY = RGBColor(0x14, 0x2B, 0x4D)
BLUE = RGBColor(0x1F, 0x5F, 0xA8)
LIGHT = RGBColor(0xEE, 0xF3, 0xF9)
GRAY = RGBColor(0x55, 0x5F, 0x6B)
LINE = RGBColor(0xC5, 0xD0, 0xDE)
ACCENT = RGBColor(0xD9, 0x82, 0x1E)
WHITE = RGBColor(255, 255, 255)
FONT = "Yu Gothic"

prs = Presentation()
prs.slide_width = Inches(13.333)
prs.slide_height = Inches(7.5)
SW, SH = 13.333, 7.5
M = 0.6  # side margin


def set_font(run, size, bold=False, color=NAVY):
    f = run.font
    f.size = Pt(size)
    f.bold = bold
    f.color.rgb = color
    f.name = FONT
    rPr = run._r.get_or_add_rPr()
    for tag in ("a:ea", "a:cs"):
        el = rPr.find(qn(tag))
        if el is None:
            el = etree.SubElement(rPr, qn(tag))
        el.set("typeface", FONT)


def text(slide, x, y, w, h, s, size, bold=False, color=NAVY, align=PP_ALIGN.LEFT,
         anchor=MSO_ANCHOR.TOP):
    tb = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = tb.text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_right = Inches(0.05)
    tf.margin_top = tf.margin_bottom = Inches(0.03)
    tf.vertical_anchor = anchor
    p = tf.paragraphs[0]
    p.alignment = align
    r = p.add_run()
    r.text = s
    set_font(r, size, bold, color)
    return tb


def rect(slide, x, y, w, h, fill, line=None, shape=MSO_SHAPE.RECTANGLE):
    s = slide.shapes.add_shape(shape, Inches(x), Inches(y), Inches(w), Inches(h))
    s.fill.solid()
    s.fill.fore_color.rgb = fill
    if line is None:
        s.line.fill.background()
    else:
        s.line.color.rgb = line
        s.line.width = Pt(1)
    s.shadow.inherit = False
    return s


def shape_text(shape, s, size, bold=False, color=WHITE, align=PP_ALIGN.CENTER):
    tf = shape.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    p = tf.paragraphs[0]
    p.alignment = align
    r = p.add_run()
    r.text = s
    set_font(r, size, bold, color)


def header(slide, title, message=None, page=None):
    t = slide.shapes.title
    t.left, t.top, t.width, t.height = Inches(M), Inches(0.35), Inches(SW - 2 * M), Inches(0.75)
    tf = t.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    tf.margin_left = Inches(0.05)
    p = tf.paragraphs[0]
    p.alignment = PP_ALIGN.LEFT
    r = p.add_run()
    r.text = title
    set_font(r, 28, True, NAVY)
    rect(slide, M, 1.12, SW - 2 * M, 0.04, BLUE)
    if message:
        bar = rect(slide, M, 1.32, SW - 2 * M, 0.55, LIGHT)
        rect(slide, M, 1.32, 0.09, 0.55, ACCENT)
        text(slide, M + 0.25, 1.32, SW - 2 * M - 0.35, 0.55, message, 18, True, NAVY,
             anchor=MSO_ANCHOR.MIDDLE)
    if page:
        text(slide, SW - M - 1.0, SH - 0.45, 1.0, 0.3, str(page), 10, False, GRAY, PP_ALIGN.RIGHT)


title_only = prs.slide_layouts[5]

# ---------- Slide 1 ----------
s = prs.slides.add_slide(prs.slide_layouts[0])
bg = rect(s, 0, 0, SW, SH, NAVY)
s.shapes._spTree.remove(bg._element)
s.shapes._spTree.insert(2, bg._element)
rect(s, 0, 0, 0.35, SH, ACCENT)
rect(s, 1.2, 4.0, 6.0, 0.05, ACCENT)
t = s.shapes.title
t.left, t.top, t.width, t.height = Inches(1.2), Inches(2.1), Inches(11), Inches(1.6)
t.text_frame.word_wrap = True
t.text_frame.vertical_anchor = MSO_ANCHOR.BOTTOM
p = t.text_frame.paragraphs[0]
p.alignment = PP_ALIGN.LEFT
r = p.add_run(); r.text = "2027年度 事業計画"
set_font(r, 54, True, WHITE)
st = s.placeholders[1]
st.left, st.top, st.width, st.height = Inches(1.2), Inches(4.3), Inches(11), Inches(0.8)
st.text_frame.word_wrap = True
p = st.text_frame.paragraphs[0]
p.alignment = PP_ALIGN.LEFT
r = p.add_run(); r.text = "青葉フーズ株式会社 経営企画部 2027年3月"
set_font(r, 22, False, RGBColor(0xD6, 0xE2, 0xF2))

# ---------- Slide 2 ----------
s = prs.slides.add_slide(title_only)
header(s, "2027年度の経営目標", "売上・利益ともに過去最高を目指す", 2)
kpis = [("売上高", "1,280億円", "前年比 +8%"),
        ("営業利益", "96億円", "前年比 +12%"),
        ("営業利益率", "7.5%", "+0.3pt"),
        ("ROE", "9.0%", "+0.8pt")]
gap = 0.3
cw = (SW - 2 * M - 3 * gap) / 4
top, ch = 2.35, 4.2
for i, (lab, val, note) in enumerate(kpis):
    x = M + i * (cw + gap)
    rect(s, x, top, cw, ch, WHITE, LINE)
    hd = rect(s, x, top, cw, 0.7, NAVY)
    shape_text(hd, lab, 20, True, WHITE)
    text(s, x, top + 0.95, cw, 1.4, val, 34, True, BLUE, PP_ALIGN.CENTER, MSO_ANCHOR.MIDDLE)
    rect(s, x + 0.4, top + 2.6, cw - 0.8, 0.03, LINE)
    text(s, x, top + 2.85, cw, 0.8, note, 22, True, ACCENT, PP_ALIGN.CENTER, MSO_ANCHOR.MIDDLE)

# ---------- Slide 3 ----------
s = prs.slides.add_slide(title_only)
header(s, "売上高と営業利益の推移（億円）", "5年間で売上高は1.25倍に", 3)
cd = CategoryChartData()
cd.categories = ["2023", "2024", "2025", "2026", "2027計画"]
cd.add_series("売上高", (1020, 1085, 1130, 1185, 1280))
cd.add_series("営業利益", (61, 70, 78, 86, 96))
gf = s.shapes.add_chart(XL_CHART_TYPE.COLUMN_CLUSTERED, Inches(M), Inches(2.05),
                        Inches(SW - 2 * M), Inches(4.85), cd)
ch_ = gf.chart
ch_.font.size = Pt(14)
ch_.font.name = FONT
ch_.has_legend = True
ch_.legend.position = XL_LEGEND_POSITION.TOP
ch_.legend.include_in_layout = False
ch_.legend.font.size = Pt(14)
plot = ch_.plots[0]
plot.gap_width = 60
plot.overlap = -5
plot.has_data_labels = True
dl = plot.data_labels
dl.show_value = True
dl.number_format = "#,##0"
dl.number_format_is_linked = False
dl.position = XL_LABEL_POSITION.OUTSIDE_END
dl.font.size = Pt(14)
dl.font.bold = True
for ser, col in zip(plot.series, (NAVY, ACCENT)):
    ser.format.fill.solid()
    ser.format.fill.fore_color.rgb = col
va = ch_.value_axis
va.maximum_scale = 1400
va.minimum_scale = 0
va.major_unit = 200
va.tick_labels.font.size = Pt(12)
va.tick_labels.number_format = "#,##0"
va.tick_labels.number_format_is_linked = False
va.major_gridlines.format.line.color.rgb = LINE
va.format.line.fill.background()
ch_.category_axis.tick_labels.font.size = Pt(14)

# ---------- Slide 4 ----------
s = prs.slides.add_slide(title_only)
header(s, "4つの重点戦略", None, 4)
boxes = [("既存事業の収益改善", ["主力3ブランドの価格改定", "不採算SKUを15%削減"]),
         ("海外展開の加速", ["タイ工場の増設", "北米で冷凍食品を発売"]),
         ("DXの推進", ["需要予測のAI化", "受発注の完全電子化"]),
         ("人的資本への投資", ["賃上げ率4.5%", "デジタル人材を50名採用"])]
gap = 0.2
bw = (SW - 2 * M - 3 * gap) / 4
top, bh = 1.7, 4.6
for i, (hd_, items) in enumerate(boxes):
    x = M + i * (bw + gap)
    rect(s, x, top, bw, bh, LIGHT, LINE)
    rect(s, x, top, bw, 0.08, ACCENT)
    num = rect(s, x + 0.25, top + 0.3, 0.6, 0.6, NAVY, shape=MSO_SHAPE.OVAL)
    shape_text(num, str(i + 1), 20, True, WHITE)
    text(s, x + 0.1, top + 1.0, bw - 0.2, 0.7, hd_, 18, True, NAVY, anchor=MSO_ANCHOR.MIDDLE)
    rect(s, x + 0.25, top + 1.8, bw - 0.5, 0.03, BLUE)
    for j, it in enumerate(items):
        y = top + 2.05 + j * 1.2
        rect(s, x + 0.15, y, bw - 0.3, 1.0, WHITE, LINE)
        rect(s, x + 0.15, y, 0.07, 1.0, BLUE)
        text(s, x + 0.27, y, bw - 0.47, 1.0, it, 14, False, NAVY, anchor=MSO_ANCHOR.MIDDLE)
text(s, M, 6.5, SW - 2 * M - 1.2, 0.4, "※ 各戦略のKPIは個別資料を参照", 12, False, GRAY)

# ---------- Slide 5 ----------
s = prs.slides.add_slide(title_only)
header(s, "年間スケジュール", None, 5)
steps = [("4–6月", "価格改定"), ("7–9月", "タイ工場着工"), ("10–12月", "北米発売"), ("1–3月", "効果検証")]
gap = 0.15
sw_ = (SW - 2 * M - 3 * gap) / 4
for i, (per, what) in enumerate(steps):
    x = M + i * (sw_ + gap)
    ch = rect(s, x, 1.9, sw_, 1.3, NAVY if i % 2 == 0 else BLUE, shape=MSO_SHAPE.PENTAGON if i == 0 else MSO_SHAPE.CHEVRON)
    shape_text(ch, per, 22, True, WHITE)
    ch.text_frame.margin_left = ch.text_frame.margin_right = 0
    rect(s, x + 0.1, 3.6, sw_ - 0.3, 2.3, LIGHT, LINE)
    rect(s, x + 0.1, 3.6, 0.08, 2.3, ACCENT)
    text(s, x + 0.3, 3.6, sw_ - 0.7, 2.3, what, 24, True, NAVY, anchor=MSO_ANCHOR.MIDDLE)
s.notes_slide.notes_text_frame.text = "価格改定は主要取引先への説明を3月中に終えます。"

prs.save("deck.pptx")

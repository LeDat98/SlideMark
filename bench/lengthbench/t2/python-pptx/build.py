from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE
from pptx.chart.data import CategoryChartData
from pptx.enum.chart import XL_CHART_TYPE, XL_LEGEND_POSITION, XL_LABEL_POSITION
from pptx.oxml.ns import qn
from lxml import etree

FONT = "Yu Gothic"
NAVY = RGBColor(0x14, 0x2B, 0x4D)
BLUE = RGBColor(0x1F, 0x5F, 0xA8)
TEAL = RGBColor(0x2A, 0x9D, 0x8F)
AMBER = RGBColor(0xE0, 0x9F, 0x1F)
GRAY = RGBColor(0x59, 0x62, 0x6E)
LIGHT = RGBColor(0xEE, 0xF2, 0xF7)
LINE = RGBColor(0xC9, 0xD2, 0xDE)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
TEXT = RGBColor(0x22, 0x2B, 0x36)
SERIES = [BLUE, AMBER, TEAL, RGBColor(0x8A, 0x5A, 0xA8)]

prs = Presentation()
prs.slide_width = Inches(13.333)
prs.slide_height = Inches(7.5)
BLANK = prs.slide_layouts[6]
W = 13.333
MX = 0.6  # side margin


def set_font(run, size, bold=False, color=TEXT):
    f = run.font
    f.size = Pt(size)
    f.bold = bold
    f.name = FONT
    f.color.rgb = color
    rPr = run._r.get_or_add_rPr()
    for tag in ("a:ea", "a:cs"):
        el = rPr.find(qn(tag))
        if el is None:
            el = etree.SubElement(rPr, qn(tag))
        el.set("typeface", FONT)


def text(slide, x, y, w, h, s, size=14, bold=False, color=TEXT, align=PP_ALIGN.LEFT,
         anchor=MSO_ANCHOR.TOP, name=None):
    tb = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = tb.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = anchor
    tf.margin_left = tf.margin_right = Inches(0.05)
    tf.margin_top = tf.margin_bottom = Inches(0.03)
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


def shape_text(s, txt, size, bold=False, color=WHITE, align=PP_ALIGN.CENTER):
    tf = s.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    p = tf.paragraphs[0]
    p.alignment = align
    r = p.add_run()
    r.text = txt
    set_font(r, size, bold, color)


page = [0]


def new_slide(title, message=None):
    s = prs.slides.add_slide(BLANK)
    page[0] += 1
    rect(s, 0, 0, W, 0.12, NAVY)
    text(s, MX, 0.3, W - 2 * MX, 0.7, title, 28, True, NAVY, anchor=MSO_ANCHOR.MIDDLE)
    rect(s, MX + 0.05, 1.02, W - 2 * MX - 0.1, 0.03, BLUE)
    if message:
        text(s, MX, 1.15, W - 2 * MX, 0.5, message, 18, True, BLUE, anchor=MSO_ANCHOR.MIDDLE)
    text(s, MX, 7.05, 6, 0.3, "青葉フーズ株式会社", 10, False, GRAY)
    text(s, W - MX - 1, 7.05, 1, 0.3, str(page[0]), 10, False, GRAY, align=PP_ALIGN.RIGHT)
    return s


def notes(s, t):
    s.notes_slide.notes_text_frame.text = t


def kpi_slide(title, kpis, message=None):
    s = new_slide(title, message)
    n = len(kpis)
    gap = 0.3
    top = 2.0 if message else 1.5
    h = 4.4 if message else 4.9
    cw = (W - 2 * MX - gap * (n - 1)) / n
    for i, (label, value, note) in enumerate(kpis):
        x = MX + i * (cw + gap)
        rect(s, x, top, cw, h, LIGHT, LINE)
        rect(s, x, top, cw, 0.1, SERIES[i % 3 if i < 3 else 2] if False else BLUE)
        text(s, x + 0.15, top + 0.35, cw - 0.3, 0.6, label, 20, True, NAVY, PP_ALIGN.CENTER,
             MSO_ANCHOR.MIDDLE)
        vs = 34 if n == 4 else 54
        text(s, x + 0.1, top + 1.35, cw - 0.2, 1.4, value, vs, True, BLUE, PP_ALIGN.CENTER,
             MSO_ANCHOR.MIDDLE)
        rect(s, x + cw * 0.2, top + 3.05, cw * 0.6, 0.02, LINE)
        text(s, x + 0.15, top + 3.2, cw - 0.3, 0.7, note, 20, True, TEAL, PP_ALIGN.CENTER,
             MSO_ANCHOR.MIDDLE)
    return s


def box_slide(title, boxes, footnote=None):
    s = new_slide(title)
    n = len(boxes)
    gap = 0.3
    top = 1.5
    h = 4.4 if footnote else 4.6
    cw = (W - 2 * MX - gap * (n - 1)) / n
    hs = 20 if n == 4 else 26
    bs = 22 if n == 4 else 24
    for i, (head, items) in enumerate(boxes):
        x = MX + i * (cw + gap)
        rect(s, x, top, cw, h, LIGHT, LINE)
        hd = rect(s, x, top, cw, 1.0, NAVY)
        shape_text(hd, head, hs, True)
        tb = s.shapes.add_textbox(Inches(x + 0.15), Inches(top + 1.25), Inches(cw - 0.3),
                                  Inches(h - 1.5))
        tf = tb.text_frame
        tf.word_wrap = True
        for j, it in enumerate(items):
            p = tf.paragraphs[0] if j == 0 else tf.add_paragraph()
            p.space_after = Pt(22)
            r = p.add_run()
            r.text = "■ "
            set_font(r, bs - 4, False, TEAL)
            r = p.add_run()
            r.text = it
            set_font(r, bs, False, TEXT)
    if footnote:
        text(s, MX, top + h + 0.2, W - 2 * MX, 0.4, footnote, 13, False, GRAY)
    return s


def process_slide(title, steps):
    s = new_slide(title)
    n = len(steps)
    gap = 0.15
    cw = (W - 2 * MX - gap * (n - 1)) / n
    top = 2.0
    for i, (head, body) in enumerate(steps):
        x = MX + i * (cw + gap)
        ch = rect(s, x, top, cw, 1.3, NAVY if i % 2 == 0 else BLUE, shape=MSO_SHAPE.PENTAGON)
        shape_text(ch, head, 26, True)
        rect(s, x, top + 1.6, cw - 0.25, 2.6, LIGHT, LINE)
        text(s, x + 0.1, top + 1.6, cw - 0.45, 2.6, body, 24, True, TEXT, PP_ALIGN.CENTER,
             MSO_ANCHOR.MIDDLE)
        text(s, x, top + 4.4, cw - 0.25, 0.4, "STEP %d" % (i + 1), 14, True, TEAL, PP_ALIGN.CENTER)
    return s


def style_chart(chart, legend=True, size=14):
    chart.font.size = Pt(size)
    chart.font.name = FONT
    chart.has_title = False
    chart.has_legend = legend
    if legend:
        chart.legend.position = XL_LEGEND_POSITION.BOTTOM
        chart.legend.include_in_layout = False
        chart.legend.font.size = Pt(size)
        chart.legend.font.name = FONT


def chart_slide(title, message, ctype, cats, series, numfmt='#,##0', legend=True,
                gap_width=80):
    s = new_slide(title, message)
    cd = CategoryChartData()
    cd.categories = cats
    for name, vals in series:
        cd.add_series(name, vals)
    top = 1.8 if message else 1.4
    gf = s.shapes.add_chart(ctype, Inches(MX), Inches(top), Inches(W - 2 * MX),
                            Inches(6.95 - top), cd)
    ch = gf.chart
    style_chart(ch, legend)
    plot = ch.plots[0]
    plot.has_data_labels = True
    dl = plot.data_labels
    dl.number_format = numfmt
    dl.number_format_is_linked = False
    dl.font.size = Pt(14)
    dl.font.name = FONT
    dl.show_value = True
    if ctype in (XL_CHART_TYPE.COLUMN_CLUSTERED, XL_CHART_TYPE.BAR_CLUSTERED):
        plot.gap_width = gap_width
        dl.position = XL_LABEL_POSITION.OUTSIDE_END
        va = ch.value_axis
        va.has_major_gridlines = True
        va.major_gridlines.format.line.color.rgb = LINE
        va.tick_labels.font.size = Pt(13)
        va.format.line.fill.background()
        ch.category_axis.tick_labels.font.size = Pt(14)
        for i, ser in enumerate(plot.series):
            ser.format.fill.solid()
            ser.format.fill.fore_color.rgb = SERIES[i % len(SERIES)]
    return s, ch


# 1 cover
s = prs.slides.add_slide(BLANK)
page[0] += 1
rect(s, 0, 0, W, 7.5, NAVY)
rect(s, 0, 4.55, W, 0.06, AMBER)
rect(s, MX, 2.0, 0.12, 2.3, TEAL)
text(s, MX + 0.4, 2.0, 11.5, 1.5, "2027年度 事業計画", 54, True, WHITE, anchor=MSO_ANCHOR.MIDDLE)
text(s, MX + 0.4, 3.5, 11.5, 0.8, "青葉フーズ株式会社 経営企画部 2027年3月", 24, False,
     RGBColor(0xD6, 0xE2, 0xF0), anchor=MSO_ANCHOR.MIDDLE)

# 2 KPI
kpi_slide("2027年度の経営目標", [
    ("売上高", "1,280億円", "前年比 +8%"),
    ("営業利益", "96億円", "前年比 +12%"),
    ("営業利益率", "7.5%", "+0.3pt"),
    ("ROE", "9.0%", "+0.8pt"),
], "売上・利益ともに過去最高を目指す")

# 3 column chart
s, ch = chart_slide("売上高と営業利益の推移（億円）", "5年間で売上高は1.25倍に",
                    XL_CHART_TYPE.COLUMN_CLUSTERED,
                    ["2023", "2024", "2025", "2026", "2027計画"],
                    [("売上高", (1020, 1085, 1130, 1185, 1280)),
                     ("営業利益", (61, 70, 78, 86, 96))])

# 4 boxes
box_slide("4つの重点戦略", [
    ("既存事業の収益改善", ["主力3ブランドの価格改定", "不採算SKUを15%削減"]),
    ("海外展開の加速", ["タイ工場の増設", "北米で冷凍食品を発売"]),
    ("DXの推進", ["需要予測のAI化", "受発注の完全電子化"]),
    ("人的資本への投資", ["賃上げ率4.5%", "デジタル人材を50名採用"]),
], "※ 各戦略のKPIは個別資料を参照")

# 5 process
s = process_slide("年間スケジュール", [
    ("4–6月", "価格改定"), ("7–9月", "タイ工場着工"),
    ("10–12月", "北米発売"), ("1–3月", "効果検証")])
notes(s, "価格改定は主要取引先への説明を3月中に終えます。")


def table_slide(title, rows, conclusion_flag=False, colw=None):
    s = new_slide(title)
    nr, nc = len(rows), len(rows[0])
    top = 1.5
    rh = 0.8 if conclusion_flag else 1.05
    height = rh * nr
    gf = s.shapes.add_table(nr, nc, Inches(MX), Inches(top), Inches(W - 2 * MX), Inches(height))
    tbl = gf.table
    tblPr = gf._element.graphic.graphicData.tbl.tblPr
    # remove default style banding look by explicit fills
    if colw:
        for i, cw in enumerate(colw):
            tbl.columns[i].width = Inches(cw)
    for r in range(nr):
        tbl.rows[r].height = Inches(rh)
        for c in range(nc):
            cell = tbl.cell(r, c)
            cell.vertical_anchor = MSO_ANCHOR.MIDDLE
            cell.margin_left = cell.margin_right = Inches(0.15)
            cell.fill.solid()
            if r == 0:
                cell.fill.fore_color.rgb = NAVY
            else:
                cell.fill.fore_color.rgb = LIGHT if r % 2 == 0 else WHITE
            tf = cell.text_frame
            p = tf.paragraphs[0]
            p.alignment = PP_ALIGN.LEFT if c == 0 or not rows[r][c].replace(",", "").lstrip("+-").rstrip("%").isdigit() and c == 0 else PP_ALIGN.LEFT
            run = p.add_run()
            run.text = rows[r][c]
            set_font(run, 20 if r else 20, r == 0 or c == 0, WHITE if r == 0 else TEXT)
    return s, top + height


# 6 table
rows = [["事業", "2026実績", "2027計画", "前年比"],
        ["冷凍食品", "420", "465", "+11%"],
        ["調味料", "310", "325", "+5%"],
        ["飲料", "255", "270", "+6%"],
        ["海外", "200", "220", "+10%"]]
s, bottom = table_slide("事業別の売上計画（億円）", rows, True, colw=[3.9, 2.8, 2.8, 2.633])
for r in range(1, 5):
    pass
bar = rect(s, MX, 6.0, W - 2 * MX, 0.8, BLUE)
shape_text(bar, "冷凍食品と海外が成長をけん引", 24, True, WHITE)

# 7 pie
s, ch = chart_slide("2027年度 売上構成（%）", None, XL_CHART_TYPE.PIE,
                    ["冷凍食品", "調味料", "飲料", "海外"], [("構成比", (36, 25, 21, 18))],
                    numfmt='0"%"')
ch.legend.position = XL_LEGEND_POSITION.RIGHT
ch.legend.font.size = Pt(18)
plot = ch.plots[0]
plot.data_labels.font.size = Pt(22)
plot.data_labels.font.bold = True
plot.data_labels.font.color.rgb = WHITE
plot.data_labels.position = XL_LABEL_POSITION.INSIDE_END
for i, pt_color in enumerate([BLUE, AMBER, TEAL, RGBColor(0x8A, 0x5A, 0xA8)]):
    pt = plot.series[0].points[i]
    pt.format.fill.solid()
    pt.format.fill.fore_color.rgb = pt_color

# 8 bullets
s = new_slide("価格改定の方針", "原材料高を価格に反映し、販売数量を維持する")
items = ["主力3ブランドを平均6%改定", "改定は2027年5月出荷分から", "容量変更は行わない",
         "販促費を前年比10%削減"]
for i, it in enumerate(items):
    y = 2.0 + i * 1.22
    rect(s, MX, y, W - 2 * MX, 1.05, LIGHT, LINE)
    n = rect(s, MX, y, 1.05, 1.05, NAVY if i % 2 == 0 else BLUE)
    shape_text(n, str(i + 1), 32, True)
    text(s, MX + 1.3, y, W - 2 * MX - 1.5, 1.05, it, 26, False, TEXT, anchor=MSO_ANCHOR.MIDDLE)

# 9 KPI x3
kpi_slide("冷凍食品事業の目標", [
    ("売上高", "465億円", "前年比 +11%"),
    ("新商品比率", "18%", "+4pt"),
    ("工場稼働率", "88%", "+5pt"),
])

# 10 boxes x3
box_slide("海外展開の重点地域", [
    ("タイ", ["工場の生産能力を1.5倍に", "ASEAN向け輸出拠点"]),
    ("北米", ["冷凍餃子を発売", "大手スーパー3社で展開"]),
    ("台湾", ["調味料の現地生産", "コンビニ向けPB"]),
])

# 11 line chart
s, ch = chart_slide("海外売上高の推移（億円）", None, XL_CHART_TYPE.LINE_MARKERS,
                    ["2024", "2025", "2026", "2027計画"],
                    [("タイ", (70, 82, 95, 105)), ("北米", (20, 30, 45, 60)),
                     ("台湾", (40, 50, 60, 55))])
plot = ch.plots[0]
plot.data_labels.position = XL_LABEL_POSITION.ABOVE
for i, ser in enumerate(plot.series):
    ser.smooth = False
    ser.format.line.color.rgb = SERIES[i]
    ser.format.line.width = Pt(3.5)
    ser.marker.format.fill.solid()
    ser.marker.format.fill.fore_color.rgb = SERIES[i]
    ser.marker.format.line.color.rgb = SERIES[i]
    ser.marker.size = 9
va = ch.value_axis
va.has_major_gridlines = True
va.major_gridlines.format.line.color.rgb = LINE
va.tick_labels.font.size = Pt(13)
ch.category_axis.tick_labels.font.size = Pt(14)
plot.series[2].data_labels.position = XL_LABEL_POSITION.BELOW
dlp = plot.series[2].points[2].data_label
dlp.position = XL_LABEL_POSITION.ABOVE
dlp.font.size = Pt(14)
plot.series[2].data_labels.show_value = True
plot.series[2].data_labels.font.size = Pt(14)
plot.series[2].data_labels.number_format = '#,##0'
plot.series[2].data_labels.number_format_is_linked = False

# 12 table
rows = [["施策", "対象", "効果", "時期"],
        ["需要予測AI", "全工場", "在庫 -15%", "2027年6月"],
        ["受発注の電子化", "主要取引先", "工数 -30%", "2027年9月"],
        ["設備の予知保全", "3工場", "停止時間 -20%", "2027年12月"],
        ["経費精算の自動化", "全社", "処理時間 -50%", "2027年4月"]]
table_slide("DX施策の一覧", rows, colw=[3.9, 2.8, 2.8, 2.633])

# 13 process
process_slide("DX推進のロードマップ", [
    ("2027年4月", "経費精算"), ("6月", "需要予測AI"),
    ("9月", "受発注電子化"), ("12月", "予知保全")])

# 14 KPI x4
kpi_slide("人的資本の目標", [
    ("賃上げ率", "4.5%", "3年連続"),
    ("女性管理職比率", "15%", "+3pt"),
    ("デジタル人材", "120名", "+50名"),
    ("エンゲージメント", "3.8", "+0.2"),
])

# 15 bar chart
s, ch = chart_slide("設備投資の配分（億円）", "設備投資は総額100億円", XL_CHART_TYPE.BAR_CLUSTERED,
                    ["タイ工場", "国内工場更新", "DX", "研究開発"], [("投資額", (45, 30, 15, 10))],
                    legend=False, gap_width=60)
ch.category_axis.reverse_order = True
ch.value_axis.tick_label_position  # keep
notes(s, "タイ工場は2028年4月の稼働を予定しています。")

prs.save("deck.pptx")

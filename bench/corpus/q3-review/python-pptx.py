from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.chart.data import CategoryChartData
from pptx.enum.chart import XL_CHART_TYPE

prs = Presentation()
prs.slide_width = Inches(13.333)
prs.slide_height = Inches(7.5)

s = prs.slides.add_slide(prs.slide_layouts[0])
s.shapes.title.text = "Q3 Business Review"
s.placeholders[1].text = "Sales & Growth"
s.notes_slide.notes_text_frame.text = "Chào mọi người, hôm nay mình review kết quả Q3."

s = prs.slides.add_slide(prs.slide_layouts[5])
s.shapes.title.text = "Doanh thu tăng 32%"
tb = s.shapes.add_textbox(Inches(0.5), Inches(1.6), Inches(6), Inches(5))
tf = tb.text_frame
tf.word_wrap = True
for i, t in enumerate(["APAC +48%", "Khách hàng mới: 1.240", "Churn giảm còn 2,1%"]):
    p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
    p.text = "• " + t
    p.font.size = Pt(24)
cd = CategoryChartData()
cd.categories = ["Q1", "Q2", "Q3"]
cd.add_series("2025", (10, 12, 15))
cd.add_series("2026", (12, 16, 21))
s.shapes.add_chart(XL_CHART_TYPE.COLUMN_CLUSTERED, Inches(6.8), Inches(1.6), Inches(6), Inches(5), cd)

s = prs.slides.add_slide(prs.slide_layouts[5])
s.shapes.title.text = "Kết quả theo khu vực"
rows = [["Khu vực", "Doanh thu", "Tăng trưởng"], ["APAC", "8.2M", "+48%"], ["EU", "6.1M", "+12%"], ["US", "9.4M", "+9%"]]
tbl = s.shapes.add_table(4, 3, Inches(0.5), Inches(1.6), Inches(12.3), Inches(3)).table
for r, row in enumerate(rows):
    for c, v in enumerate(row):
        tbl.cell(r, c).text = v

prs.save("q3.pptx")

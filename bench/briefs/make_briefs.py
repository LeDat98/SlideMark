"""Write the agent-cost brief set: bench/briefs/<id>/brief.md + accept.json (docs/AGENT_COST.md).

Each brief gives the content word for word, so every arm presents the same text; accept.json lists the
required strings, slide count, size, native charts/tables and notes for bench/agent_accept.py.
Brief set 1 (2026-10-05): 3/5/10 slides x EN default / JA dense / VI brand colours.
Do not tune SlideMark on it.

    python bench/briefs/make_briefs.py
"""

from __future__ import annotations

import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
DENSE_JA = "Dense Japanese business style (consulting look): small text is fine, many elements per slide."

# slide kinds: cover(title, subtitle) | bullets(title, lead?, items) | boxes(title, lead?, boxes=[(h, items)])
# table(title, lead?, rows, conclusion?) | chart(title, kind, rows, lead?) | kpis(title, lead?, kpis=[(label,
# value, note)], items?) | steps(title, steps=[(h, text)]); any slide: notes, footnote, conclusion
BRIEFS: dict[str, dict] = {
    "b01-en-3": {
        "lang": "English",
        "look": "Default look; no brand requirements.",
        "slides": [
            {
                "kind": "cover",
                "title": "Quarterly Business Review",
                "subtitle": "Q3 2026 results and outlook",
            },
            {
                "kind": "table",
                "title": "Revenue grew 18% year over year",
                "lead": "Growth came from the enterprise segment",
                "rows": [
                    ["Segment", "Q3 2025", "Q3 2026", "Change"],
                    ["Enterprise", "4.2", "5.6", "+33%"],
                    ["SMB", "3.1", "3.2", "+3%"],
                    ["Consumer", "1.9", "1.8", "-5%"],
                ],
                "conclusion": "Enterprise now drives two thirds of growth",
            },
            {
                "kind": "chart",
                "chart": "column chart",
                "title": "Pipeline doubled since Q1",
                "rows": [["", "Q1", "Q2", "Q3"], ["Pipeline ($M)", "12", "17", "24"]],
                "notes": "Pipeline counts qualified opportunities only.",
            },
        ],
    },
    "b02-en-5": {
        "lang": "English",
        "look": "Default look; no brand requirements.",
        "slides": [
            {
                "kind": "cover",
                "title": "Customer Support Modernization",
                "subtitle": "Proposal to the leadership team",
            },
            {
                "kind": "bullets",
                "title": "Why change now",
                "lead": "Ticket volume grows faster than the team",
                "items": [
                    "Tickets up 42% in 12 months",
                    "Median first response is 9 hours",
                    "Two senior agents left in Q2",
                    "Customers ask for chat support",
                ],
            },
            {
                "kind": "boxes",
                "title": "Three options",
                "boxes": [
                    ("Hire", ["Add 6 agents", "Cost $480k per year", "Ready in 4 months"]),
                    ("Outsource", ["Partner covers nights", "Cost $300k per year", "Ready in 6 weeks"]),
                    ("Automate", ["AI answers top 30 questions", "Cost $150k per year", "Ready in 3 months"]),
                ],
                "conclusion": "We recommend Automate plus 2 hires",
            },
            {
                "kind": "chart",
                "chart": "line chart",
                "title": "Response time falls within two quarters",
                "rows": [
                    ["", "Q4", "Q1", "Q2", "Q3"],
                    ["Today (hours)", "9", "10", "11", "12"],
                    ["With plan (hours)", "9", "6", "3", "2"],
                ],
            },
            {
                "kind": "bullets",
                "title": "Next steps",
                "items": [
                    "Approve budget by October 20",
                    "Select vendor by November 15",
                    "Pilot with 10% of tickets in December",
                ],
                "notes": "Ask for a decision today; the vendor offer expires on October 31.",
            },
        ],
    },
    "b03-en-10": {
        "lang": "English",
        "look": (
            "Brand look required: dark navy background #0B1F3A on every slide, white text, "
            "coral accent #FF6B57, "
            'font "Montserrat" for headings and "Open Sans" for body text.'
        ),
        "slides": [
            {
                "kind": "cover",
                "title": "Northwind Mobility",
                "subtitle": "Series B investor update, October 2026",
            },
            {
                "kind": "kpis",
                "title": "Traction at a glance",
                "kpis": [
                    ("Riders", "1.2M", "+64% YoY"),
                    ("Cities", "14", "+5 this year"),
                    ("Gross margin", "38%", "+9 pt"),
                ],
            },
            {
                "kind": "bullets",
                "title": "The problem",
                "items": [
                    "Last-mile trips are 40% of urban commutes",
                    "Buses miss the last two kilometres",
                    "Cars are idle 95% of the day",
                ],
            },
            {
                "kind": "boxes",
                "title": "Our solution",
                "boxes": [
                    ("Shared e-bikes", ["Docked at transit hubs", "Unlock in the transit app"]),
                    ("Micro-vans", ["On-demand, 6 seats", "Pooled routes"]),
                ],
            },
            {
                "kind": "chart",
                "chart": "column chart",
                "title": "Revenue by year ($M)",
                "rows": [["", "2023", "2024", "2025", "2026"], ["Revenue", "3.1", "7.8", "15.2", "26.0"]],
            },
            {
                "kind": "table",
                "title": "Unit economics per ride",
                "rows": [
                    ["Item", "2024", "2026"],
                    ["Average fare", "$3.10", "$3.40"],
                    ["Vehicle cost", "$1.40", "$1.05"],
                    ["Operations", "$0.90", "$0.70"],
                    ["Contribution", "$0.80", "$1.65"],
                ],
            },
            {
                "kind": "chart",
                "chart": "pie chart",
                "title": "Where riders come from",
                "rows": [["", "Transit app", "Employers", "Direct"], ["Share", "52", "31", "17"]],
            },
            {
                "kind": "steps",
                "title": "Expansion plan",
                "steps": [
                    ("2027 H1", "Four new cities"),
                    ("2027 H2", "Micro-vans in all cities"),
                    ("2028", "First market in Europe"),
                ],
            },
            {
                "kind": "bullets",
                "title": "Use of funds: $40M",
                "items": ["Fleet: $22M", "Technology: $10M", "New markets: $8M"],
            },
            {
                "kind": "cover",
                "title": "Thank you",
                "subtitle": "invest@northwind.example",
                "notes": "Close with the ask: lead investor decision by November 30.",
            },
        ],
    },
    "b04-ja-3": {
        "lang": "Japanese",
        "look": DENSE_JA,
        "slides": [
            {"kind": "cover", "title": "物流センター自動化の検討", "subtitle": "経営会議資料 2026年10月"},
            {
                "kind": "boxes",
                "title": "現状の課題と打ち手",
                "lead": "人手不足と誤出荷が利益を圧迫している",
                "boxes": [
                    ("人手不足", ["求人倍率 3.2倍", "繁忙期の残業 月45時間"]),
                    ("誤出荷", ["誤出荷率 0.8%", "返品コスト 年1.2億円"]),
                    ("打ち手", ["自動倉庫の導入", "検品のバーコード化"]),
                ],
                "footnote": "※ 出所: 社内物流データ（2026年4〜9月）",
            },
            {
                "kind": "table",
                "title": "投資対効果",
                "lead": "3年で投資を回収できる",
                "rows": [
                    ["項目", "1年目", "2年目", "3年目"],
                    ["投資額", "4.0億円", "0.5億円", "0.5億円"],
                    ["削減効果", "1.2億円", "2.1億円", "2.4億円"],
                    ["累計収支", "-2.8億円", "-1.2億円", "0.7億円"],
                ],
                "conclusion": "第1期として東日本センターから着手する",
                "notes": "投資額は見積もり段階の概算です。",
            },
        ],
    },
    "b05-ja-5": {
        "lang": "Japanese",
        "look": DENSE_JA,
        "slides": [
            {"kind": "cover", "title": "中期経営計画 2027–2029", "subtitle": "取締役会 説明資料"},
            {
                "kind": "kpis",
                "title": "2029年の目標",
                "lead": "売上と利益率を同時に高める",
                "kpis": [
                    ("売上高", "1,500億円", "2026年比 +30%"),
                    ("営業利益率", "12%", "+4pt"),
                    ("海外売上比率", "40%", "+15pt"),
                    ("ROE", "10%", "+3pt"),
                ],
                "items": ["既存事業は収益性を重視", "新規事業に3年で200億円を投資", "海外はアジアに集中"],
            },
            {
                "kind": "boxes",
                "title": "4つの重点施策",
                "boxes": [
                    ("価格改定", ["主力製品を平均5%改定", "値引き基準の統一"]),
                    ("海外展開", ["ベトナム工場の稼働", "インド販売網の構築"]),
                    ("DX推進", ["受発注の完全電子化", "需要予測のAI化"]),
                    ("人材", ["技術職を300名採用", "管理職の評価制度刷新"]),
                ],
                "footnote": "※ 施策ごとのKPIは別紙参照",
            },
            {
                "kind": "steps",
                "title": "実行ロードマップ",
                "steps": [
                    ("2027年 上期", "体制構築"),
                    ("2027年 下期", "価格改定"),
                    ("2028年", "海外拠点稼働"),
                    ("2029年", "目標達成"),
                ],
            },
            {
                "kind": "chart",
                "chart": "stacked column chart",
                "title": "売上高の内訳（億円）",
                "rows": [
                    ["", "2026", "2027", "2028", "2029"],
                    ["国内", "860", "880", "890", "900"],
                    ["海外", "290", "360", "480", "600"],
                ],
                "notes": "海外の伸びはベトナム工場の稼働が前提です。",
            },
        ],
    },
    "b06-ja-10": {
        "lang": "Japanese",
        "look": DENSE_JA,
        "slides": [
            {"kind": "cover", "title": "新卒採用戦略の見直し", "subtitle": "人事部 2026年10月"},
            {
                "kind": "bullets",
                "title": "エグゼクティブサマリー",
                "items": [
                    "内定辞退率が3年で2倍の38%に上昇",
                    "主因は選考期間の長さと初任給の差",
                    "選考を6週間から3週間に短縮する",
                    "初任給を28万円に引き上げる",
                ],
            },
            {
                "kind": "chart",
                "chart": "line chart",
                "title": "内定辞退率の推移（%）",
                "rows": [["", "2023", "2024", "2025", "2026"], ["辞退率", "19", "24", "31", "38"]],
            },
            {
                "kind": "chart",
                "chart": "bar chart",
                "title": "辞退理由（複数回答、%）",
                "rows": [
                    ["", "他社が先に内定", "給与", "勤務地", "社風"],
                    ["回答率", "62", "48", "21", "15"],
                ],
            },
            {
                "kind": "table",
                "title": "競合比較",
                "rows": [
                    ["項目", "当社", "A社", "B社"],
                    ["初任給", "25万円", "28万円", "27万円"],
                    ["選考期間", "6週間", "3週間", "4週間"],
                    ["面接回数", "4回", "2回", "3回"],
                    ["リモート勤務", "週1日", "週3日", "週2日"],
                ],
            },
            {
                "kind": "boxes",
                "title": "打ち手",
                "boxes": [
                    ("選考短縮", ["面接を2回に削減", "合否連絡は3日以内"]),
                    ("処遇改善", ["初任給28万円", "住宅手当の新設"]),
                    ("魅力発信", ["社員座談会を月2回", "OB訪問のオンライン化"]),
                ],
            },
            {
                "kind": "steps",
                "title": "新しい選考フロー",
                "steps": [
                    ("エントリー", "Web適性検査"),
                    ("一次面接", "現場社員"),
                    ("最終面接", "役員"),
                    ("内定", "3日以内に連絡"),
                ],
            },
            {
                "kind": "kpis",
                "title": "目標KPI",
                "kpis": [
                    ("内定辞退率", "20%", "-18pt"),
                    ("選考期間", "3週間", "-3週間"),
                    ("採用人数", "120名", "+20名"),
                ],
            },
            {
                "kind": "table",
                "title": "必要予算",
                "rows": [
                    ["項目", "金額"],
                    ["初任給引き上げ", "3.6億円"],
                    ["住宅手当", "1.2億円"],
                    ["採用広報", "0.4億円"],
                    ["合計", "5.2億円"],
                ],
                "footnote": "※ 年間ベース、2027年度入社者から適用",
            },
            {
                "kind": "bullets",
                "title": "ご承認いただきたい事項",
                "items": ["初任給の引き上げ", "選考フローの変更", "予算5.2億円の確保"],
                "conclusion": "11月の取締役会で最終決定",
                "notes": "質疑では予算の財源を聞かれる想定です。",
            },
        ],
    },
    "b07-vi-3": {
        "lang": "Vietnamese",
        "look": (
            "Brand look required: white background, dark green #14532D for titles, lime accent #84CC16, "
            'font "Be Vietnam Pro".'
        ),
        "slides": [
            {"kind": "cover", "title": "Báo cáo kinh doanh tháng 9", "subtitle": "Chuỗi cửa hàng Lá Xanh"},
            {
                "kind": "kpis",
                "title": "Kết quả nổi bật",
                "kpis": [
                    ("Doanh thu", "12,4 tỷ", "+15% so với tháng 8"),
                    ("Khách hàng mới", "3.200", "+22%"),
                    ("Tỷ lệ quay lại", "41%", "+3 điểm"),
                ],
            },
            {
                "kind": "chart",
                "chart": "column chart",
                "title": "Doanh thu theo khu vực (tỷ đồng)",
                "rows": [["", "Hà Nội", "Đà Nẵng", "TP.HCM"], ["Tháng 9", "4,1", "1,8", "6,5"]],
                "notes": "Đà Nẵng mới mở thêm hai cửa hàng trong tháng.",
            },
        ],
    },
    "b08-vi-5": {
        "lang": "Vietnamese",
        "look": (
            "Brand look required: warm cream background #FFF7ED, brown text #431407, orange accent #EA580C, "
            'font "Lora" for headings and "Inter" for body.'
        ),
        "slides": [
            {"kind": "cover", "title": "Kế hoạch ra mắt sản phẩm mới", "subtitle": "Cà phê ủ lạnh đóng chai"},
            {
                "kind": "bullets",
                "title": "Cơ hội thị trường",
                "lead": "Thị trường cà phê uống liền tăng 18% mỗi năm",
                "items": [
                    "Người trẻ thích tiện lợi",
                    "Đối thủ chưa có dòng ủ lạnh",
                    "Kênh cửa hàng tiện lợi tăng mạnh",
                ],
            },
            {
                "kind": "boxes",
                "title": "Định vị sản phẩm",
                "boxes": [
                    ("Khách hàng", ["Dân văn phòng 22–35 tuổi", "Sống ở thành phố lớn"]),
                    ("Giá", ["25.000 đồng một chai", "Thấp hơn quán 30%"]),
                    ("Kênh bán", ["Cửa hàng tiện lợi", "Sàn thương mại điện tử"]),
                ],
            },
            {
                "kind": "steps",
                "title": "Lộ trình ra mắt",
                "steps": [
                    ("Tháng 11", "Thử nghiệm vị"),
                    ("Tháng 12", "Sản xuất lô đầu"),
                    ("Tháng 1", "Ra mắt tại TP.HCM"),
                    ("Tháng 3", "Mở rộng toàn quốc"),
                    ("Tháng 6", "Đánh giá kết quả"),
                ],
            },
            {
                "kind": "table",
                "title": "Ngân sách dự kiến",
                "rows": [
                    ["Hạng mục", "Chi phí"],
                    ["Nghiên cứu sản phẩm", "1,2 tỷ"],
                    ["Sản xuất lô đầu", "3,5 tỷ"],
                    ["Marketing", "2,8 tỷ"],
                    ["Tổng cộng", "7,5 tỷ"],
                ],
                "conclusion": "Đề xuất phê duyệt 7,5 tỷ trong tháng 10",
                "notes": "Nhấn mạnh rằng ngân sách marketing có thể chia làm hai đợt.",
            },
        ],
    },
    "b09-vi-10": {
        "lang": "Vietnamese",
        "look": (
            "Brand look required: white background, deep teal #0F766E primary, amber accent #F59E0B, "
            'font "Roboto".'
        ),
        "slides": [
            {
                "kind": "cover",
                "title": "Chuyển đổi số ngân hàng bán lẻ",
                "subtitle": "Báo cáo ban điều hành, quý 3",
            },
            {
                "kind": "kpis",
                "title": "Tổng quan quý 3",
                "kpis": [
                    ("Khách hàng số", "2,8 triệu", "+31%"),
                    ("Giao dịch trên app", "86%", "+9 điểm"),
                    ("Chi phí mỗi giao dịch", "1.900 đồng", "-24%"),
                    ("Mức hài lòng", "4,5/5", "+0,3"),
                ],
            },
            {
                "kind": "chart",
                "chart": "line chart",
                "title": "Người dùng app hằng tháng (triệu)",
                "rows": [
                    ["", "T1", "T3", "T5", "T7", "T9"],
                    ["Người dùng", "1,6", "1,9", "2,2", "2,5", "2,8"],
                ],
            },
            {
                "kind": "boxes",
                "title": "Ba trụ cột chiến lược",
                "boxes": [
                    ("Trải nghiệm", ["Mở tài khoản trong 5 phút", "Hỗ trợ 24/7"]),
                    ("Dữ liệu", ["Chấm điểm tín dụng tự động", "Gợi ý sản phẩm cá nhân"]),
                    ("Vận hành", ["Tự động hóa hồ sơ vay", "Giảm 40% giấy tờ"]),
                ],
            },
            {
                "kind": "steps",
                "title": "Quy trình vay trực tuyến",
                "steps": [
                    ("Đăng ký", "Trên ứng dụng"),
                    ("Xác thực", "eKYC khuôn mặt"),
                    ("Thẩm định", "Chấm điểm tự động"),
                    ("Phê duyệt", "Trong 15 phút"),
                    ("Giải ngân", "Vào tài khoản"),
                ],
            },
            {
                "kind": "table",
                "title": "So sánh với đối thủ",
                "rows": [
                    ["Tiêu chí", "Chúng ta", "Ngân hàng A", "Ngân hàng B"],
                    ["Thời gian mở tài khoản", "5 phút", "15 phút", "1 ngày"],
                    ["Phê duyệt khoản vay", "15 phút", "2 ngày", "3 ngày"],
                    ["Phí chuyển khoản", "0 đồng", "0 đồng", "3.300 đồng"],
                ],
            },
            {
                "kind": "chart",
                "chart": "doughnut chart",
                "title": "Cơ cấu giao dịch theo kênh",
                "rows": [["", "Ứng dụng", "Internet banking", "Quầy"], ["Tỷ trọng", "86", "9", "5"]],
            },
            {
                "kind": "bullets",
                "title": "Rủi ro và biện pháp",
                "items": [
                    "Gian lận trực tuyến: giám sát giao dịch theo thời gian thực",
                    "Sự cố hệ thống: trung tâm dữ liệu dự phòng",
                    "Thiếu nhân sự công nghệ: hợp tác với đại học",
                ],
            },
            {
                "kind": "bullets",
                "title": "Kế hoạch quý 4",
                "items": [
                    "Ra mắt thẻ tín dụng số",
                    "Mở API cho đối tác thương mại điện tử",
                    "Đạt 3,2 triệu khách hàng số",
                ],
            },
            {
                "kind": "cover",
                "title": "Xin cảm ơn",
                "subtitle": "Phòng Ngân hàng số",
                "notes": "Mời ban điều hành đặt câu hỏi về ngân sách quý 4.",
            },
        ],
    },
}

KIND_TEXT = {
    "cover": "Cover / title slide",
    "bullets": "Bullet list",
    "boxes": "Side-by-side boxes, one per heading",
    "table": "Table",
    "chart": "Native chart",
    "kpis": "KPI cards (big number + label + note)",
    "steps": "Process steps in order (left to right)",
}


def brief_md(bid: str, b: dict) -> str:
    out = [
        f"# Brief {bid}",
        "",
        f"Make a {len(b['slides'])}-slide 16:9 PowerPoint deck in {b['lang']}."
        " Use the text below word for word.",
        f"Look: {b['look']}",
        "",
    ]
    for i, s in enumerate(b["slides"], 1):
        out.append(f"## Slide {i}: {KIND_TEXT[s['kind']]}" + (f" ({s['chart']})" if "chart" in s else ""))
        out.append(f"- Title: {s['title']}")
        if "subtitle" in s:
            out.append(f"- Subtitle: {s['subtitle']}")
        if "lead" in s:
            out.append(f"- Key message under the title: {s['lead']}")
        for k in s.get("kpis", []):
            out.append(f'- KPI: label "{k[0]}", value "{k[1]}", note "{k[2]}"')
        for h, items in s.get("boxes", []):
            out.append(f'- Box "{h}": ' + "; ".join(f'"{x}"' for x in items))
        for h, t in s.get("steps", []):
            out.append(f'- Step "{h}": "{t}"')
        for x in s.get("items", []):
            out.append(f"- Bullet: {x}")
        if "rows" in s:
            label = (
                "Chart data (first row = categories, then one row per series)" if "chart" in s else "Table"
            )
            out.append(f"- {label}:")
            out.append("")
            out.extend("  | " + " | ".join(r) + " |" for r in s["rows"])
            out.append("")
        if "conclusion" in s:
            out.append(f"- Conclusion at the bottom: {s['conclusion']}")
        if "footnote" in s:
            out.append(f"- Footnote: {s['footnote']}")
        if "notes" in s:
            out.append(f"- Speaker notes: {s['notes']}")
        out.append("")
    charts = sum(1 for s in b["slides"] if "chart" in s)
    tables = sum(1 for s in b["slides"] if s["kind"] == "table")
    out += [
        "## Acceptance",
        f"- Exactly {len(b['slides'])} slides, 16:9.",
        "- Every text above appears in the deck (titles, bullets, cells, labels, notes).",
        f"- {charts} native chart(s) and {tables} native table(s); charts show data labels or a value axis.",
        "- Speaker notes where asked. No overflowing, overlapping or cut-off text;"
        " nothing tiny beside a large empty area.",
        "",
    ]
    return "\n".join(out)


def accept(b: dict) -> dict:
    strings: list[str] = []
    notes = []
    for i, s in enumerate(b["slides"], 1):
        strings += [
            s["title"],
            s.get("subtitle", ""),
            s.get("lead", ""),
            s.get("conclusion", ""),
            s.get("footnote", ""),
        ]
        for k in s.get("kpis", []):
            strings += list(k)
        for h, items in s.get("boxes", []):
            strings += [h, *items]
        for h, t in s.get("steps", []):
            strings += [h, t]
        strings += s.get("items", [])
        rows = s.get("rows", [])
        if "chart" in s and rows:  # values may be written as numbers (4,1 -> 4.1): require labels only
            rows = [rows[0], *([r[0]] for r in rows[1:])]
        for r in rows:
            strings += [c for c in r if c]
        if "notes" in s:
            strings.append(s["notes"])
            notes.append(i)
    seen: list[str] = []
    for x in strings:
        if x and x not in seen:
            seen.append(x)
    return {
        "slides": len(b["slides"]),
        "size": "16:9",
        "charts": sum(1 for s in b["slides"] if "chart" in s),
        "tables": sum(1 for s in b["slides"] if s["kind"] == "table"),
        "notes": notes,
        "strings": seen,
    }


def main() -> None:
    for bid, b in BRIEFS.items():
        d = HERE / bid
        d.mkdir(exist_ok=True)
        (d / "brief.md").write_text(brief_md(bid, b), encoding="utf-8")
        (d / "accept.json").write_text(
            json.dumps(accept(b), ensure_ascii=False, indent=1) + "\n", encoding="utf-8"
        )
        print(d.name, len(b["slides"]), "slides")


if __name__ == "__main__":
    main()

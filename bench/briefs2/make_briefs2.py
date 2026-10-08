"""Write agent-cost brief set 2: bench/briefs2/<id>/brief.md + accept.json (docs/AGENT_COST.md).

Fresh content (2026-10-05 run 6) in the same shape as set 1 (bench/briefs/make_briefs.py): 3/5/10 slides x
EN / dense JA / VI, default and brand looks mixed differently than set 1. Do not tune SlideMark on it.

    python bench/briefs2/make_briefs2.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "briefs"))
from make_briefs import DENSE_JA, accept, brief_md  # noqa: E402

BRIEFS: dict[str, dict] = {
    "c01-en-3": {
        "lang": "English",
        "look": (
            "Brand look required: warm off-white background #FAF7F2, plum #5B2A86 for titles, "
            'gold accent #D4A017, font "Playfair Display" for headings and "Lato" for body text.'
        ),
        "slides": [
            {
                "kind": "cover",
                "title": "Atelier Rosa Spring Collection",
                "subtitle": "Retail partner briefing",
            },
            {
                "kind": "kpis",
                "title": "Last season at a glance",
                "kpis": [
                    ["Units sold", "48,200", "+21% vs. last spring"],
                    ["Sell-through", "83%", "Best in five seasons"],
                    ["Returns", "4.1%", "Down from 6.0%"],
                ],
            },
            {
                "kind": "bullets",
                "title": "What changes for partners",
                "items": [
                    "Orders open on 12 January",
                    "Minimum order drops to 24 pieces",
                    "Free reorders within 30 days",
                    "New window displays ship with every order",
                ],
                "notes": "Mention that window displays are optional.",
            },
        ],
    },
    "c02-en-5": {
        "lang": "English",
        "look": "Default look; no brand requirements.",
        "slides": [
            {
                "kind": "cover",
                "title": "Cloud Cost Review",
                "subtitle": "Engineering all-hands, October 2026",
            },
            {
                "kind": "chart",
                "chart": "line chart",
                "title": "Monthly spend has flattened",
                "rows": [
                    ["", "Apr", "May", "Jun", "Jul", "Aug", "Sep"],
                    ["Spend ($k)", "410", "455", "492", "498", "501", "497"],
                ],
                "lead": "Savings plans offset traffic growth since June",
            },
            {
                "kind": "table",
                "title": "Where the money goes",
                "rows": [
                    ["Service", "Share", "Trend", "Owner"],
                    ["Compute", "46%", "Flat", "Platform"],
                    ["Storage", "22%", "Rising", "Data"],
                    ["Network", "17%", "Rising", "Platform"],
                    ["Databases", "15%", "Falling", "Data"],
                ],
                "conclusion": "Storage and network are the next targets",
            },
            {
                "kind": "boxes",
                "title": "Three savings levers",
                "boxes": [
                    ["Rightsizing", ["Shrink idle clusters", "Weekly report per team"]],
                    ["Storage tiers", ["Move logs to cold storage", "Expire snapshots after 90 days"]],
                    ["Egress", ["Cache static assets at the edge", "Compress API responses"]],
                ],
            },
            {
                "kind": "bullets",
                "title": "Asks for every team",
                "items": [
                    "Tag every resource with an owner",
                    "Review the weekly cost report",
                    "Delete unused environments by 31 October",
                ],
                "notes": "Teams that tag everything get their own dashboard.",
            },
        ],
    },
    "c03-en-10": {
        "lang": "English",
        "look": "Default look; no brand requirements.",
        "slides": [
            {
                "kind": "cover",
                "title": "Harbor Health Clinics",
                "subtitle": "Annual report to the board 2026",
            },
            {
                "kind": "kpis",
                "title": "The year in numbers",
                "lead": "More patients, shorter waits",
                "kpis": [
                    ["Patient visits", "312k", "+14%"],
                    ["Median wait", "11 min", "-6 min"],
                    ["Satisfaction", "4.6 / 5", "+0.3"],
                    ["Clinics", "18", "+3 opened"],
                ],
            },
            {
                "kind": "chart",
                "chart": "column chart",
                "title": "Visits grew in every region",
                "rows": [
                    ["", "North", "Central", "South", "Coast"],
                    ["2025", "64", "88", "71", "51"],
                    ["2026", "72", "97", "83", "60"],
                ],
                "footnote": "Visits in thousands",
            },
            {
                "kind": "boxes",
                "title": "What drove the improvement",
                "boxes": [
                    ["Online booking", ["62% of visits booked online", "No-shows down by a third"]],
                    ["Team nursing", ["Nurses run routine follow-ups", "Doctors see complex cases"]],
                    ["Longer hours", ["Evening slots in 12 clinics", "Saturday mornings everywhere"]],
                ],
            },
            {
                "kind": "table",
                "title": "Clinic performance by region",
                "rows": [
                    ["Region", "Clinics", "Visits (k)", "Median wait", "Satisfaction"],
                    ["North", "4", "72", "12 min", "4.5"],
                    ["Central", "6", "97", "9 min", "4.7"],
                    ["South", "5", "83", "12 min", "4.6"],
                    ["Coast", "3", "60", "13 min", "4.5"],
                ],
            },
            {
                "kind": "chart",
                "chart": "pie chart",
                "title": "Funding sources",
                "rows": [
                    ["", "Public", "Insurance", "Private", "Grants"],
                    ["Share (%)", "48", "31", "14", "7"],
                ],
            },
            {
                "kind": "bullets",
                "title": "Challenges",
                "items": [
                    "Recruiting nurses in coastal towns",
                    "Rising medicine costs",
                    "Ageing buildings in the north",
                ],
            },
            {
                "kind": "steps",
                "title": "Plan for 2027",
                "steps": [
                    ["Q1", "Open two coastal clinics"],
                    ["Q2", "Launch video visits"],
                    ["Q3", "Renovate northern sites"],
                    ["Q4", "Review results"],
                ],
            },
            {
                "kind": "table",
                "title": "Budget request 2027",
                "rows": [
                    ["Item", "Amount ($M)", "Purpose"],
                    ["New clinics", "6.4", "Two coastal sites"],
                    ["Video visits", "1.2", "Platform and training"],
                    ["Renovation", "3.8", "Four northern buildings"],
                ],
                "conclusion": "Total request: $11.4M",
            },
            {
                "kind": "bullets",
                "title": "Decisions needed today",
                "items": ["Approve the 2027 budget", "Approve two new coastal sites"],
                "notes": "Ask for a vote on both items together.",
            },
        ],
    },
    "c04-ja-3": {
        "lang": "Japanese",
        "look": DENSE_JA,
        "slides": [
            {"kind": "cover", "title": "社内研修制度の改定案", "subtitle": "人材開発委員会 2026年11月"},
            {
                "kind": "table",
                "title": "現行制度と改定案の比較",
                "lead": "受講の自由度を高め、費用対効果を可視化する",
                "rows": [
                    ["項目", "現行", "改定案"],
                    ["受講方法", "集合研修のみ", "集合＋オンライン"],
                    ["受講時間", "年20時間", "年30時間"],
                    ["費用負担", "全額会社", "会社8割・本人2割"],
                    ["効果測定", "なし", "受講後テストと上長評価"],
                ],
                "footnote": "※ 改定案は2027年4月施行予定",
            },
            {
                "kind": "boxes",
                "title": "導入までの課題",
                "boxes": [
                    ["予算", ["年間4,000万円の追加", "補助金の活用を検討"]],
                    ["運用", ["受講管理システムの更新", "講師の確保"]],
                    ["周知", ["管理職向け説明会", "社内ポータルで案内"]],
                ],
                "conclusion": "12月の経営会議で最終承認を得る",
            },
        ],
    },
    "c05-ja-5": {
        "lang": "Japanese",
        "look": DENSE_JA,
        "slides": [
            {"kind": "cover", "title": "コールセンター改善プロジェクト", "subtitle": "中間報告 2026年10月"},
            {
                "kind": "kpis",
                "title": "主要指標の推移",
                "lead": "応答率は改善、解決率は横ばい",
                "kpis": [
                    ["応答率", "92%", "前期比 +7pt"],
                    ["平均待ち時間", "38秒", "前期比 -22秒"],
                    ["一次解決率", "71%", "前期比 ±0pt"],
                    ["顧客満足度", "3.9", "前期比 +0.2"],
                ],
            },
            {
                "kind": "chart",
                "chart": "bar chart",
                "title": "問い合わせ内容の内訳（件/月）",
                "rows": [
                    ["", "料金", "解約", "故障", "住所変更", "その他"],
                    ["件数", "4200", "2600", "1900", "1300", "800"],
                ],
                "footnote": "※ 2026年9月実績",
            },
            {
                "kind": "boxes",
                "title": "次期の重点施策",
                "boxes": [
                    ["FAQ拡充", ["料金FAQを30項目追加", "検索機能の改善"]],
                    ["チャット対応", ["夜間はチャットボット", "有人チャットへ引継ぎ"]],
                    ["教育", ["解約対応の研修", "ベテランの同席指導"]],
                    ["システム", ["顧客履歴の一画面表示", "通話の自動要約"]],
                ],
            },
            {
                "kind": "steps",
                "title": "今後のスケジュール",
                "steps": [
                    ["11月", "FAQ公開"],
                    ["12月", "チャット試行"],
                    ["2027年1月", "システム更新"],
                    ["2027年3月", "効果検証"],
                ],
                "notes": "システム更新は年末年始の繁忙期を避けます。",
            },
        ],
    },
    "c06-ja-10": {
        "lang": "Japanese",
        "look": (
            "Brand look required: white background, navy #1E3A5F for titles and table headers, "
            'red accent #C8102E, font "Noto Sans JP". Dense Japanese business style.'
        ),
        "slides": [
            {"kind": "cover", "title": "地方店舗の再編計画", "subtitle": "経営企画部 2026年10月"},
            {
                "kind": "bullets",
                "title": "背景",
                "lead": "人口減少で地方店舗の採算が悪化している",
                "items": [
                    "地方120店のうち45店が赤字",
                    "来店客数は5年で18%減少",
                    "人件費と光熱費は上昇が続く",
                    "一方でネット注文は年20%増加",
                ],
            },
            {
                "kind": "chart",
                "chart": "line chart",
                "title": "地方店舗の来店客数（指数）",
                "rows": [
                    ["", "2021", "2022", "2023", "2024", "2025", "2026"],
                    ["来店客数", "100", "97", "93", "90", "86", "82"],
                    ["ネット注文", "100", "121", "143", "170", "205", "246"],
                ],
            },
            {
                "kind": "table",
                "title": "店舗区分と方針",
                "rows": [
                    ["区分", "店舗数", "条件", "方針"],
                    ["A 維持", "52", "黒字", "現状維持・改装"],
                    ["B 改善", "23", "小幅赤字", "営業時間の短縮"],
                    ["C 統合", "30", "赤字", "近隣店へ統合"],
                    ["D 転換", "15", "大幅赤字", "受取拠点へ転換"],
                ],
                "footnote": "※ 2026年3月期の実績で区分",
            },
            {
                "kind": "boxes",
                "title": "再編の3つの柱",
                "boxes": [
                    ["統合", ["30店を15店に集約", "従業員は全員配置転換"]],
                    ["転換", ["15店を受取拠点に", "地域の集会所として開放"]],
                    ["デジタル", ["ネット注文の当日配送", "高齢者向け電話注文"]],
                ],
            },
            {
                "kind": "kpis",
                "title": "再編の効果（2029年度）",
                "kpis": [
                    ["営業利益", "+24億円", "年間"],
                    ["赤字店舗", "45→8店", "-37店"],
                    ["ネット売上比率", "25%", "+13pt"],
                ],
            },
            {
                "kind": "chart",
                "chart": "stacked column chart",
                "title": "費用削減の内訳（億円）",
                "rows": [
                    ["", "2027", "2028", "2029"],
                    ["人件費", "4", "8", "11"],
                    ["賃料", "3", "6", "8"],
                    ["光熱費", "1", "3", "5"],
                ],
            },
            {
                "kind": "steps",
                "title": "実行スケジュール",
                "steps": [
                    ["2027年4月", "統合の第1弾"],
                    ["2027年10月", "受取拠点の開設"],
                    ["2028年4月", "統合の第2弾"],
                    ["2029年3月", "再編完了"],
                ],
            },
            {
                "kind": "table",
                "title": "リスクと対策",
                "rows": [
                    ["リスク", "影響", "対策"],
                    ["地域の反発", "大", "自治体と事前協議"],
                    ["従業員の離職", "中", "通勤手当の増額"],
                    ["配送コスト増", "中", "共同配送の導入"],
                ],
            },
            {
                "kind": "bullets",
                "title": "本日の決議事項",
                "items": ["再編計画の承認", "2027年度予算への反映"],
                "notes": "統合対象の店舗名は別紙で配布します。",
            },
        ],
    },
    "c07-vi-3": {
        "lang": "Vietnamese",
        "look": "Default look; no brand requirements.",
        "slides": [
            {"kind": "cover", "title": "Khảo sát mức độ hài lòng nhân viên", "subtitle": "Kết quả năm 2026"},
            {
                "kind": "chart",
                "chart": "column chart",
                "title": "Điểm hài lòng theo khối",
                "rows": [
                    ["", "Kinh doanh", "Kỹ thuật", "Vận hành", "Hành chính"],
                    ["2025", "3,6", "3,9", "3,4", "3,8"],
                    ["2026", "3,9", "4,1", "3,5", "3,9"],
                ],
                "lead": "Khối vận hành cần được ưu tiên cải thiện",
            },
            {
                "kind": "bullets",
                "title": "Hành động đề xuất",
                "items": [
                    "Tăng ca linh hoạt cho khối vận hành",
                    "Đào tạo quản lý cấp trung",
                    "Khảo sát nhanh mỗi quý",
                ],
                "notes": "Ngân sách đào tạo đã được duyệt trong tháng 9.",
            },
        ],
    },
    "c08-vi-5": {
        "lang": "Vietnamese",
        "look": (
            "Brand look required: dark charcoal background #1F2937 on every slide, white text, "
            'orange accent #F97316, font "Montserrat".'
        ),
        "slides": [
            {"kind": "cover", "title": "Ứng dụng giao đồ ăn Bếp Nhà", "subtitle": "Gọi vốn vòng hạt giống"},
            {
                "kind": "kpis",
                "title": "Sáu tháng đầu tiên",
                "kpis": [
                    ["Đơn hàng", "38.000", "Tăng 25% mỗi tháng"],
                    ["Bếp đối tác", "210", "Tại Hà Nội"],
                    ["Giá trị đơn", "145.000 đ", "Trung bình"],
                ],
            },
            {
                "kind": "boxes",
                "title": "Vì sao khách hàng chọn chúng tôi",
                "boxes": [
                    ["Món nhà nấu", ["Bếp gia đình được kiểm định", "Thực đơn đổi mỗi ngày"]],
                    ["Giá hợp lý", ["Rẻ hơn nhà hàng 30%", "Miễn phí giao từ 2 món"]],
                    ["Giao nhanh", ["Trung bình 28 phút", "Theo dõi đơn trực tiếp"]],
                ],
            },
            {
                "kind": "chart",
                "chart": "line chart",
                "title": "Đơn hàng mỗi tháng",
                "rows": [
                    ["", "T4", "T5", "T6", "T7", "T8", "T9"],
                    ["Đơn hàng", "2.100", "3.000", "4.600", "6.200", "9.500", "12.600"],
                ],
            },
            {
                "kind": "table",
                "title": "Sử dụng vốn",
                "rows": [
                    ["Hạng mục", "Tỷ lệ", "Mục tiêu"],
                    ["Mở rộng TP.HCM", "45%", "300 bếp mới"],
                    ["Công nghệ", "30%", "Ứng dụng cho bếp"],
                    ["Marketing", "25%", "100.000 người dùng"],
                ],
                "notes": "Vòng gọi vốn là 1,5 triệu USD.",
            },
        ],
    },
    "c09-vi-10": {
        "lang": "Vietnamese",
        "look": (
            "Brand look required: light grey background #F3F4F6, indigo #3730A3 primary, "
            "pink accent #DB2777, "
            'font "Inter".'
        ),
        "slides": [
            {
                "kind": "cover",
                "title": "Chuyển đổi số trường THPT Ánh Dương",
                "subtitle": "Báo cáo hội đồng trường",
            },
            {
                "kind": "bullets",
                "title": "Hiện trạng",
                "items": [
                    "Sổ điểm vẫn ghi tay ở 60% lớp",
                    "Phụ huynh nhận thông báo qua giấy",
                    "Phòng máy tính đã dùng 9 năm",
                ],
            },
            {
                "kind": "kpis",
                "title": "Mục tiêu đến năm 2028",
                "kpis": [
                    ["Sổ điểm điện tử", "100%", "Tất cả các lớp"],
                    ["Phụ huynh dùng ứng dụng", "90%", "Hiện nay 35%"],
                    ["Giờ học có thiết bị số", "50%", "Hiện nay 15%"],
                ],
            },
            {
                "kind": "boxes",
                "title": "Bốn hạng mục đầu tư",
                "boxes": [
                    ["Hạ tầng", ["Wi-Fi phủ toàn trường", "Thay 80 máy tính"]],
                    ["Phần mềm", ["Sổ điểm điện tử", "Ứng dụng phụ huynh"]],
                    ["Giáo viên", ["Tập huấn 40 giờ", "Nhóm hỗ trợ nội bộ"]],
                    ["Học sinh", ["Câu lạc bộ lập trình", "Thư viện số"]],
                ],
            },
            {
                "kind": "chart",
                "chart": "doughnut chart",
                "title": "Phân bổ ngân sách",
                "rows": [
                    ["", "Hạ tầng", "Phần mềm", "Đào tạo", "Dự phòng"],
                    ["Tỷ lệ (%)", "45", "25", "20", "10"],
                ],
            },
            {
                "kind": "table",
                "title": "Ngân sách theo năm (triệu đồng)",
                "rows": [
                    ["Hạng mục", "2026", "2027", "2028"],
                    ["Hạ tầng", "900", "450", "150"],
                    ["Phần mềm", "300", "250", "200"],
                    ["Đào tạo", "200", "250", "200"],
                ],
            },
            {
                "kind": "steps",
                "title": "Lộ trình triển khai",
                "steps": [
                    ["Học kỳ 1", "Lắp Wi-Fi"],
                    ["Học kỳ 2", "Sổ điểm điện tử"],
                    ["Năm 2027", "Ứng dụng phụ huynh"],
                    ["Năm 2028", "Đánh giá"],
                ],
            },
            {
                "kind": "chart",
                "chart": "column chart",
                "title": "Khảo sát giáo viên: mức sẵn sàng",
                "rows": [
                    ["", "Rất sẵn sàng", "Sẵn sàng", "Chưa chắc", "Chưa sẵn sàng"],
                    ["Số giáo viên", "18", "27", "11", "4"],
                ],
            },
            {
                "kind": "bullets",
                "title": "Rủi ro chính",
                "items": [
                    "Giáo viên lớn tuổi ngại thay đổi",
                    "Mạng điện bị gián đoạn",
                    "Chi phí bảo trì tăng",
                ],
                "footnote": "Đã có phương án dự phòng cho từng rủi ro",
            },
            {
                "kind": "bullets",
                "title": "Đề nghị hội đồng",
                "items": ["Phê duyệt kế hoạch", "Thành lập ban chỉ đạo"],
                "notes": "Xin ý kiến biểu quyết ngay trong buổi họp.",
            },
        ],
    },
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

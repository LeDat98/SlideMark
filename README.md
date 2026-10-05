# SlideMark

Thư viện Python giúp AI Agent tạo file PowerPoint (.pptx) **native, chỉnh sửa được** chỉ bằng cách viết văn bản
theo cú pháp riêng của SlideMark: ngắn gọn, tốn ít token và hỗ trợ cả slide dày đặc kiểu Nhật.

> Trạng thái: đang phát triển (đã xong 7 ngày nền móng, đang leo các cấp L2 → L4). Mục tiêu từng cấp L1 → L7: [docs/TARGETS.md](docs/TARGETS.md).

## Ví dụ

```markdown
theme: jp-business
lang: ja

# 新規事業の検討状況と今後の方針
> 3つの課題を解決し、2027年度の黒字化を目指す
@aab/aac
## 現状
- 売上：12.4億円（前年比 +8%）
## 課題
- 解約率が ==2.1%== に上昇
## 施策
1. 導入テンプレートの整備
※ 出所：社内CRMデータ
```

- `#` mở slide mới, mỗi `##` là một box, các box tự sắp xếp.
- `@aab/aac` là layout lưới viết trong 1 dòng.
- `>` dưới tiêu đề là thông điệp chính, dòng `※` là chú thích nguồn.

Cú pháp đầy đủ: [docs/SYNTAX.md](docs/SYNTAX.md).

## Tính năng chính

- Box, lưới `@`, KPI `{.kpi}`, callout `> [!warn]`, badge `[x]{.badge}`, mũi tên nối `@ a>b`, chevron/flow.
- 10 loại biểu đồ native từ CSV (nhãn, legend, định dạng số), bảng có gộp ô, công thức toán (OMML),
  sơ đồ Mermaid → shape native, HTML → native (hoặc ảnh dự phòng qua Chromium).
- Theme `default`, `midnight`, `jp-business` hoặc template `.pptx/.potx` của bạn; hiệu ứng xuất hiện, chuyển slide, section.
- **Thiết kế tự do:** không có giao diện cố định. Theme chỉ là preset token (YAML); agent tự khai báo màu, font,
  cỡ chữ, bo góc, gradient, bóng đổ bằng vài dòng `colors:` / `fonts:` / `sizes:` / `style:`, bằng khối ` ```css `
  (34 thuộc tính CSS → shape gốc), hoặc viết cả slide bằng HTML (`@html`, `build deck.html`) và vẫn ra shape sửa được.
- `slidemark check` kiểm tra tràn chữ, chồng lấn, tương phản, alt ảnh… và gợi ý cách sửa trên 1 dòng (JSON được).
- `slidemark docs` / `skill install`: tài liệu cho agent, SKILL.md ≤ 1.500 token.

```bash
pip install -e .
slidemark check deck.md && slidemark build deck.md -o deck.pptx
slidemark skill install      # cài skill cho Claude Code
```

Windows: `slidemark preview` / `review --png` tự tìm LibreOffice trong `C:\Program Files\LibreOffice`; nếu cài chỗ khác,
đặt biến môi trường `SLIDEMARK_SOFFICE` trỏ tới `soffice.exe`. Build .pptx không cần LibreOffice.

## Ảnh slide mẫu (cập nhật hằng ngày)

<!-- gallery:start -->
Cập nhật: 2026-10-05 · commit `8f9566a` · tạo tự động bởi `scripts/gallery.py`.

### Cơ bản: tiêu đề, danh sách, box, bảng, biểu đồ

Nguồn: [`examples/01-basics.md`](examples/01-basics.md)

![01-basics slide 1](docs/gallery/01-basics/slide-01.png)
![01-basics slide 2](docs/gallery/01-basics/slide-02.png)
![01-basics slide 3](docs/gallery/01-basics/slide-03.png)
![01-basics slide 4](docs/gallery/01-basics/slide-04.png)

### Slide dày đặc kiểu Nhật (jp-business)

Nguồn: [`examples/02-jp-dense.md`](examples/02-jp-dense.md)

![02-jp-dense slide 1](docs/gallery/02-jp-dense/slide-01.png)
![02-jp-dense slide 2](docs/gallery/02-jp-dense/slide-02.png)

### Báo cáo tiếng Việt

Nguồn: [`examples/03-vi-report.md`](examples/03-vi-report.md)

![03-vi-report slide 1](docs/gallery/03-vi-report/slide-01.png)
![03-vi-report slide 2](docs/gallery/03-vi-report/slide-02.png)
![03-vi-report slide 3](docs/gallery/03-vi-report/slide-03.png)

### Tiếng Nhật: KPI, badge, bảng kết quả, mũi tên nối

Nguồn: [`examples/04-jp-kpi.md`](examples/04-jp-kpi.md)

![04-jp-kpi slide 1](docs/gallery/04-jp-kpi/slide-01.png)
![04-jp-kpi slide 2](docs/gallery/04-jp-kpi/slide-02.png)

### Tiếng Nhật: quy trình chevron + bảng, luồng phê duyệt

Nguồn: [`examples/05-jp-process.md`](examples/05-jp-process.md)

![05-jp-process slide 1](docs/gallery/05-jp-process/slide-01.png)
![05-jp-process slide 2](docs/gallery/05-jp-process/slide-02.png)

### Tiếng Nhật: biểu đồ thị trường, bảng so sánh đối thủ

Nguồn: [`examples/06-jp-market.md`](examples/06-jp-market.md)

![06-jp-market slide 1](docs/gallery/06-jp-market/slide-01.png)
![06-jp-market slide 2](docs/gallery/06-jp-market/slide-02.png)

### Tiếng Nhật: sơ đồ tổ chức, ma trận rủi ro

Nguồn: [`examples/07-jp-org.md`](examples/07-jp-org.md)

![07-jp-org slide 1](docs/gallery/07-jp-org/slide-01.png)
![07-jp-org slide 2](docs/gallery/07-jp-org/slide-02.png)

### Tiếng Nhật: kế hoạch trung hạn, lộ trình

Nguồn: [`examples/08-jp-roadmap.md`](examples/08-jp-roadmap.md)

![08-jp-roadmap slide 1](docs/gallery/08-jp-roadmap/slide-01.png)
![08-jp-roadmap slide 2](docs/gallery/08-jp-roadmap/slide-02.png)
![08-jp-roadmap slide 3](docs/gallery/08-jp-roadmap/slide-03.png)

### Theme tối (midnight): KPI, biểu đồ, Mermaid, công thức, code

Nguồn: [`examples/09-midnight-tech.md`](examples/09-midnight-tech.md)

![09-midnight-tech slide 1](docs/gallery/09-midnight-tech/slide-01.png)
![09-midnight-tech slide 2](docs/gallery/09-midnight-tech/slide-02.png)
![09-midnight-tech slide 3](docs/gallery/09-midnight-tech/slide-03.png)
![09-midnight-tech slide 4](docs/gallery/09-midnight-tech/slide-04.png)
![09-midnight-tech slide 5](docs/gallery/09-midnight-tech/slide-05.png)
![09-midnight-tech slide 6](docs/gallery/09-midnight-tech/slide-06.png)

### Template .pptx của người dùng, ảnh (cover crop), biểu đồ, callout

Nguồn: [`examples/10-template.md`](examples/10-template.md)

![10-template slide 1](docs/gallery/10-template/slide-01.png)
![10-template slide 2](docs/gallery/10-template/slide-02.png)
![10-template slide 3](docs/gallery/10-template/slide-03.png)

### Tiếng Nhật: bộ 9 slide tư vấn dày đặc (tóm tắt, KPI, tổ chức, lộ trình, rủi ro)

Nguồn: [`examples/11-jp-consulting.md`](examples/11-jp-consulting.md)

![11-jp-consulting slide 1](docs/gallery/11-jp-consulting/slide-01.png)
![11-jp-consulting slide 2](docs/gallery/11-jp-consulting/slide-02.png)
![11-jp-consulting slide 3](docs/gallery/11-jp-consulting/slide-03.png)
![11-jp-consulting slide 4](docs/gallery/11-jp-consulting/slide-04.png)
![11-jp-consulting slide 5](docs/gallery/11-jp-consulting/slide-05.png)
![11-jp-consulting slide 6](docs/gallery/11-jp-consulting/slide-06.png)
![11-jp-consulting slide 7](docs/gallery/11-jp-consulting/slide-07.png)
![11-jp-consulting slide 8](docs/gallery/11-jp-consulting/slide-08.png)
![11-jp-consulting slide 9](docs/gallery/11-jp-consulting/slide-09.png)

### HTML/CSS → shape gốc (đo bằng Chromium), logo SVG, công thức

Nguồn: [`examples/12-html-svg-math.md`](examples/12-html-svg-math.md)

![12-html-svg-math slide 1](docs/gallery/12-html-svg-math/slide-01.png)
![12-html-svg-math slide 2](docs/gallery/12-html-svg-math/slide-02.png)

### Thiết kế tự do: thương hiệu tối, gradient, bóng đổ (theme: none + token)

Nguồn: [`examples/13-brand-aurora.md`](examples/13-brand-aurora.md)

![13-brand-aurora slide 1](docs/gallery/13-brand-aurora/slide-01.png)
![13-brand-aurora slide 2](docs/gallery/13-brand-aurora/slide-02.png)
![13-brand-aurora slide 3](docs/gallery/13-brand-aurora/slide-03.png)

### Thiết kế tự do: thương hiệu sáng, font serif, màu đất nung (token)

Nguồn: [`examples/14-brand-terracotta.md`](examples/14-brand-terracotta.md)

![14-brand-terracotta slide 1](docs/gallery/14-brand-terracotta/slide-01.png)

### Slide HTML toàn trang (@html) + slide SlideMark dùng chung token

Nguồn: [`examples/15-html-mixed.md`](examples/15-html-mixed.md)

![15-html-mixed slide 1](docs/gallery/15-html-mixed/slide-01.png)
![15-html-mixed slide 2](docs/gallery/15-html-mixed/slide-02.png)
![15-html-mixed slide 3](docs/gallery/15-html-mixed/slide-03.png)

### 16-jp-strategy

Nguồn: [`examples/16-jp-strategy.md`](examples/16-jp-strategy.md)

![16-jp-strategy slide 1](docs/gallery/16-jp-strategy/slide-01.png)
![16-jp-strategy slide 2](docs/gallery/16-jp-strategy/slide-02.png)
![16-jp-strategy slide 3](docs/gallery/16-jp-strategy/slide-03.png)
![16-jp-strategy slide 4](docs/gallery/16-jp-strategy/slide-04.png)
![16-jp-strategy slide 5](docs/gallery/16-jp-strategy/slide-05.png)
![16-jp-strategy slide 6](docs/gallery/16-jp-strategy/slide-06.png)
![16-jp-strategy slide 7](docs/gallery/16-jp-strategy/slide-07.png)
![16-jp-strategy slide 8](docs/gallery/16-jp-strategy/slide-08.png)
![16-jp-strategy slide 9](docs/gallery/16-jp-strategy/slide-09.png)
![16-jp-strategy slide 10](docs/gallery/16-jp-strategy/slide-10.png)

### 17-editorial-css

Nguồn: [`examples/17-editorial-css.md`](examples/17-editorial-css.md)

![17-editorial-css slide 1](docs/gallery/17-editorial-css/slide-01.png)
![17-editorial-css slide 2](docs/gallery/17-editorial-css/slide-02.png)
![17-editorial-css slide 3](docs/gallery/17-editorial-css/slide-03.png)
![17-editorial-css slide 4](docs/gallery/17-editorial-css/slide-04.png)
![17-editorial-css slide 5](docs/gallery/17-editorial-css/slide-05.png)

### 18-brand-lime

Nguồn: [`examples/18-brand-lime.md`](examples/18-brand-lime.md)

![18-brand-lime slide 1](docs/gallery/18-brand-lime/slide-01.png)
![18-brand-lime slide 2](docs/gallery/18-brand-lime/slide-02.png)
![18-brand-lime slide 3](docs/gallery/18-brand-lime/slide-03.png)
![18-brand-lime slide 4](docs/gallery/18-brand-lime/slide-04.png)
<!-- gallery:end -->

## Tài liệu

| File | Nội dung |
|---|---|
| [docs/SYNTAX.md](docs/SYNTAX.md) | Cú pháp |
| [docs/PLAN.md](docs/PLAN.md) | Kế hoạch 7 ngày và quy trình chạy hằng ngày |
| [docs/TARGETS.md](docs/TARGETS.md) | Mục tiêu L1–L7 |
| [docs/AGENT_TIPS.md](docs/AGENT_TIPS.md) | Mẹo cho Agent khi dùng thư viện |
| [docs/LESSONS.md](docs/LESSONS.md) | Lỗi đã gặp và cách giải quyết |
| [docs/DAILY_LOG.md](docs/DAILY_LOG.md) | Nhật ký hằng ngày |

# SlideMark

Thư viện Python giúp AI Agent tạo file PowerPoint (.pptx) **native, chỉnh sửa được** chỉ bằng cách viết văn bản
theo cú pháp riêng của SlideMark: ngắn gọn, tốn ít token và hỗ trợ cả slide dày đặc kiểu Nhật.

> Trạng thái: đang phát triển (giai đoạn nền móng 7 ngày). Mục tiêu từng cấp L1 → L7: [docs/TARGETS.md](docs/TARGETS.md).

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

## Ảnh slide mẫu (cập nhật hằng ngày)

<!-- gallery:start -->
Chưa có ảnh: renderer đang được xây dựng. Ảnh sẽ được `scripts/gallery.py` tạo tự động mỗi ngày.
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

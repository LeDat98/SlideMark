"""Build examples/*.md to docs/gallery PNGs and refresh the README gallery block (Vietnamese)."""

from __future__ import annotations

import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
START, END = "<!-- gallery:start -->", "<!-- gallery:end -->"
TITLES = {
    "01-basics": "Cơ bản: tiêu đề, danh sách, box, bảng, biểu đồ",
    "02-jp-dense": "Slide dày đặc kiểu Nhật (jp-business)",
    "03-vi-report": "Báo cáo tiếng Việt",
    "04-jp-kpi": "Tiếng Nhật: KPI, badge, bảng kết quả, mũi tên nối",
    "05-jp-process": "Tiếng Nhật: quy trình chevron + bảng, luồng phê duyệt",
    "06-jp-market": "Tiếng Nhật: biểu đồ thị trường, bảng so sánh đối thủ",
    "07-jp-org": "Tiếng Nhật: sơ đồ tổ chức, ma trận rủi ro",
    "08-jp-roadmap": "Tiếng Nhật: kế hoạch trung hạn, lộ trình",
    "09-midnight-tech": "Theme tối (midnight): KPI, biểu đồ, Mermaid, công thức, code",
    "10-template": "Template .pptx của người dùng, ảnh (cover crop), biểu đồ, callout",
    "12-html-svg-math": "HTML/CSS → shape gốc (đo bằng Chromium), logo SVG, công thức",
    "11-jp-consulting": "Tiếng Nhật: bộ 9 slide tư vấn dày đặc (tóm tắt, KPI, tổ chức, lộ trình, rủi ro)",
    "13-brand-aurora": "Thiết kế tự do: thương hiệu tối, gradient, bóng đổ (theme: none + token)",
    "14-brand-terracotta": "Thiết kế tự do: thương hiệu sáng, font serif, màu đất nung (token)",
    "15-html-mixed": "Slide HTML toàn trang (@html) + slide SlideMark dùng chung token",
    "16-jp-strategy": "Tiếng Nhật: chiến lược dịch vụ, Gantt, quyết định",
    "17-editorial-css": "Thiết kế tự do bằng CSS fence: phong cách tạp chí",
    "18-brand-lime": "Thiết kế tự do: thương hiệu xanh chanh",
    "19-vi-consulting-brand": "Tiếng Việt: bộ tư vấn theo thương hiệu (theme: none)",
    "20-jp-retail-dense": "Tiếng Nhật: bộ 11 slide dày đặc (biểu đồ cầu, Gantt, ghi chú biểu đồ)",
    "21-jp-dark-pitch": "Tiếng Nhật: pitch tối thiết kế bằng CSS/HTML",
    "22-en-launch-plan": "Tiếng Anh: kế hoạch ra mắt, chevron khớp cột bảng, ghi chú biểu đồ (hl=, note=)",
}


def commit() -> str:
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, capture_output=True, text=True
        )
        return out.stdout.strip() or "unknown"
    except OSError:
        return "unknown"


def main() -> int:
    from slidemark import build
    from slidemark.preview import pptx_to_pngs

    sections, failures = [], 0
    for md in sorted((ROOT / "examples").glob("*.md")):
        name = md.stem
        pptx = ROOT / "out" / f"{name}.pptx"
        pptx.parent.mkdir(exist_ok=True)
        gal = ROOT / "docs" / "gallery" / name
        for old in gal.glob("*.png"):
            old.unlink()
        try:
            deck = build(md, pptx)
            for d in deck.diagnostics:
                print(f"{name}: {d}")
            pngs = pptx_to_pngs(pptx, gal)
        except Exception as e:  # keep going: one broken example must not hide the others
            failures += 1
            print(f"{name}: FAILED {type(e).__name__}: {e}", file=sys.stderr)
            continue
        title = TITLES.get(name, name)
        imgs = "\n".join(
            f"![{name} slide {i}]({p.relative_to(ROOT).as_posix()})" for i, p in enumerate(pngs, 1)
        )
        sections.append(f"### {title}\n\nNguồn: [`examples/{name}.md`](examples/{name}.md)\n\n{imgs}")
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    head = f"Cập nhật: {today} · commit `{commit()}` · tạo tự động bởi `scripts/gallery.py`."
    block = head + "\n\n" + ("\n\n".join(sections) if sections else "Chưa có ảnh.")
    readme = ROOT / "README.md"
    text = readme.read_text(encoding="utf-8")
    new = re.sub(re.escape(START) + r".*?" + re.escape(END), f"{START}\n{block}\n{END}", text, flags=re.S)
    readme.write_text(new, encoding="utf-8")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())

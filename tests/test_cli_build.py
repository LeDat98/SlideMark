"""`slidemark build`: stdin, auto-fix, grouped diagnostics, facts line, contact sheet, docs switch."""

from __future__ import annotations

import io

import pytest
from PIL import Image

from slidemark.cli import main
from slidemark.preview import contact_sheet, have_soffice

FACTS_DECK = """# Cover

---
# Numbers

```column {title="Sales"}
,Q1,Q2
2026,10,12
```

|a|b|
|-|-|
|1|2|

??? say this slowly

---
# Plain

- one
- two
"""

BULLET_DECK = "# Hello\n\n* one\n* two\n"
SAME_WARNING = "# A\n\n![x](nope.png)\n\n---\n# B\n\n![x](nope.png)\n\n---\n# C\n\n- ok\n"


def _stdin(monkeypatch, text: str) -> None:
    monkeypatch.setattr("sys.stdin", io.StringIO(text))


def test_stdin_build_and_save(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    _stdin(monkeypatch, BULLET_DECK)
    assert main(["build", "-", "-o", "d.pptx", "--save", "d.md"]) == 0
    out = capsys.readouterr().out
    assert (tmp_path / "d.pptx").is_file()
    assert "bullet-star" in out
    assert (tmp_path / "d.md").read_text(encoding="utf-8") == "# Hello\n\n- one\n- two\n"
    assert out.strip().splitlines()[-1].startswith("wrote d.pptx: 1 slide 16:9")


def test_stdin_default_output_is_deck_pptx(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    _stdin(monkeypatch, "# Hi\n\n- a\n- b\n")
    assert main(["build", "-"]) == 0
    assert (tmp_path / "deck.pptx").is_file()
    assert "wrote deck.pptx" in capsys.readouterr().out


def test_fix_is_written_back(tmp_path, capsys):
    src = tmp_path / "d.md"
    src.write_text(BULLET_DECK, encoding="utf-8")
    assert main(["build", str(src)]) == 0
    assert "fixed L3 bullet-star" in capsys.readouterr().out
    assert src.read_text(encoding="utf-8") == "# Hello\n\n- one\n- two\n"


def test_no_fix_leaves_the_file(tmp_path, capsys):
    src = tmp_path / "d.md"
    src.write_text(BULLET_DECK, encoding="utf-8")
    assert main(["build", str(src), "--no-fix"]) == 0
    assert "fixed" not in capsys.readouterr().out
    assert src.read_text(encoding="utf-8") == BULLET_DECK


def test_save_with_file_input(tmp_path, capsys):
    src = tmp_path / "d.md"
    src.write_text(BULLET_DECK, encoding="utf-8")
    assert main(["build", str(src), "--no-fix", "--save", str(tmp_path / "copy.md")]) == 0
    assert (tmp_path / "copy.md").read_text(encoding="utf-8") == BULLET_DECK


def test_identical_warnings_are_grouped(tmp_path, capsys):
    src = tmp_path / "d.md"
    src.write_text(SAME_WARNING, encoding="utf-8")
    assert main(["build", str(src), "--no-fix"]) == 0
    lines = capsys.readouterr().out.strip().splitlines()
    grouped = [ln for ln in lines if "image-missing" in ln]
    assert len(grouped) == 1 and grouped[0].startswith("warning slides 1,2 image-missing:")
    assert grouped[0].endswith("(x2)")
    assert "0 warnings" not in lines[-1] and "2 warnings" in lines[-1]


def test_facts_line(tmp_path, capsys):
    src = tmp_path / "d.md"
    src.write_text(FACTS_DECK, encoding="utf-8")
    assert main(["build", str(src), "-o", str(tmp_path / "o.pptx")]) == 0
    last = capsys.readouterr().out.strip().splitlines()[-1]
    assert last.startswith("wrote ") and "3 slides 16:9" in last
    assert "1 chart" in last and "1 table" in last and "notes on 1 slide" in last
    assert "image" not in last and last.endswith("0 warnings")


def test_errors_exit_1_and_are_counted(tmp_path, capsys):
    src = tmp_path / "d.json"
    src.write_text("{not json", encoding="utf-8")
    assert main(["build", str(src)]) == 1
    assert "error" in capsys.readouterr().out


def test_missing_input_exit_2(tmp_path, capsys):
    assert main(["build", str(tmp_path / "nope.md")]) == 2


def test_help_mentions_stdin_and_save(capsys):
    assert main(["build", "--help"]) == 0
    out = capsys.readouterr().out
    assert "stdin" in out and "--save" in out


def _png(path, color, size=(1280, 720)):
    Image.new("RGB", size, color).save(path)
    return path


@pytest.mark.parametrize("n,cols", [(3, 2), (6, 3)])
def test_contact_sheet_grid(tmp_path, n, cols):
    pngs = [_png(tmp_path / f"s{i}.png", (i * 30, 90, 200)) for i in range(n)]
    out = contact_sheet(pngs, tmp_path / "sub" / "sheet.png")
    with Image.open(out) as im:
        assert im.width <= 1400
        rows = -(-n // cols)
        assert im.height > rows * 200
        assert im.width > cols * 400


@pytest.mark.skipif(not have_soffice(), reason="LibreOffice not installed")
def test_build_png_contact_sheet(tmp_path, capsys):
    src = tmp_path / "d.md"
    src.write_text(FACTS_DECK, encoding="utf-8")
    sheet = tmp_path / "sheet.png"
    assert main(["build", str(src), "--png", str(sheet)]) == 0
    out = capsys.readouterr().out.strip().splitlines()
    assert sheet.is_file() and str(sheet) in out[-2] and out[-1].startswith("wrote ")


def test_png_without_soffice_is_a_note(tmp_path, capsys, monkeypatch):
    monkeypatch.setattr("slidemark.preview.have_soffice", lambda: False)
    src = tmp_path / "d.md"
    src.write_text("# Hi\n\n- a\n- b\n", encoding="utf-8")
    assert main(["build", str(src), "--png", str(tmp_path / "s.png")]) == 0
    cap = capsys.readouterr()
    assert "note: --png skipped" in cap.err and cap.out.strip().splitlines()[-1].startswith("wrote ")


def test_docs_switch(monkeypatch, capsys):
    monkeypatch.setenv("SLIDEMARK_NO_DOCS", "1")
    for argv in (["docs"], ["docs", "syntax"]):
        assert main(argv) == 3
        assert capsys.readouterr().err.strip() == "docs are disabled here: SKILL.md has everything"
    monkeypatch.setenv("SLIDEMARK_NO_DOCS", "")
    assert main(["docs"]) == 0


BRAND_DECK = """colors: bg=#0B1F3A fg=#FFFFFF primary=#FF6B57 accent=#FF6B57
fonts: heading=Montserrat body="Open Sans"

# Brand

- one
"""


def _look(capsys) -> list[str]:
    return [ln for ln in capsys.readouterr().out.splitlines() if ln.startswith("look:")]


def test_look_line_for_brand_deck(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    _stdin(monkeypatch, BRAND_DECK)
    assert main(["build", "-", "-o", "d.pptx"]) == 0
    out = capsys.readouterr().out.splitlines()
    assert out[-1].startswith("wrote ") and out[-2].startswith("look: ")
    look = out[-2]
    assert len(look) <= 170
    for want in ("bg #0B1F3A", "text #FFFFFF", "primary #FF6B57", "accent #FF6B57", "Montserrat (headings)"):
        assert want in look
    assert "Open Sans (body)" in look and "title band off" in look and "(ea)" not in look


def test_look_line_absent_for_default_deck(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    _stdin(monkeypatch, BULLET_DECK)
    assert main(["build", "-", "-o", "d.pptx"]) == 0
    assert _look(capsys) == []


def test_look_line_shows_ea_font_for_japanese(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    _stdin(monkeypatch, "lang: ja\nfonts: ea=Meiryo\n\n# 見出し\n\n- 一\n")
    assert main(["build", "-", "-o", "d.pptx"]) == 0
    assert "Meiryo (ea)" in _look(capsys)[0]


def test_look_line_reports_contrast_shift(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    _stdin(monkeypatch, "colors: bg=#FFFFFF fg=#111111 primary=#84CC16\n\n# Hi\n\n- one\n")
    assert main(["build", "-", "-o", "d.pptx"]) == 0
    assert "text shades adjusted for contrast: primary #84CC16 -> #" in _look(capsys)[0]


def test_build_help_mentions_look_line(capsys):
    try:
        main(["build", "--help"])
    except SystemExit:
        pass
    assert "'look:' line" in capsys.readouterr().out.replace("\n", " ")

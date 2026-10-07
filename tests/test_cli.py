import json
from pathlib import Path

import pytest

from slidemark import __version__
from slidemark.cli import main

CORPUS = Path(__file__).parent.parent / "bench" / "corpus"
# the four header lines the design feedback asks for (a deck that must build with no warning states them)
DESIGN_HEAD = "colors: primary=#2B6CB0\nfonts: heading=Georgia\nsizes: title=30\nstyle: radius=8\n"


def test_version(capsys):
    assert main(["version"]) == 0
    assert capsys.readouterr().out.strip() == __version__


def test_check_ok(tmp_path, capsys):
    f = tmp_path / "a.md"
    f.write_text(DESIGN_HEAD + "\n# A\n@1 noemph dense\n- x\n", encoding="utf-8")
    assert main(["check", str(f)]) == 0
    assert capsys.readouterr().out.startswith("ok")


def test_check_prints_one_diagnostic_per_line(tmp_path, capsys):
    f = tmp_path / "a.md"
    f.write_text("# A\n@aab/aa\n![](x.png)\n- x\n", encoding="utf-8")
    assert main(["check", str(f)]) == 0  # warnings only
    lines = capsys.readouterr().out.strip().splitlines()
    assert len(lines) >= 2 and all(line.startswith("warning") and "->" in line for line in lines)
    assert any("bad-grid" in line for line in lines) and any("image-alt" in line for line in lines)


def test_check_json(tmp_path, capsys):
    f = tmp_path / "a.md"
    f.write_text("# A\n![](x.png)\n- x\n", encoding="utf-8")
    assert main(["check", str(f), "--format", "json"]) == 0
    data = json.loads(capsys.readouterr().out)
    assert data[0]["rule"] == "image-alt" and data[0]["slide"] == 1 and data[0]["line"] == 2


def test_check_exit_1_on_error(tmp_path, capsys):
    f = tmp_path / "a.md"
    f.write_text("# A\n```pie\n```\n", encoding="utf-8")
    assert main(["check", str(f)]) == 1
    assert capsys.readouterr().out.startswith("error")


def test_check_corpus_is_clean(capsys):
    for p in CORPUS.glob("*/slidemark.md"):
        assert main(["check", str(p)]) == 0


def test_missing_file_exit_2(capsys):
    assert main(["check", "/nonexistent/x.md"]) == 2
    assert "cannot read" in capsys.readouterr().err


def test_bad_usage_exit_2(capsys):
    assert main([]) == 2
    assert main(["nope"]) == 2


def test_build_writes_pptx_or_skips_until_backend_exists(tmp_path):
    f = tmp_path / "a.md"
    f.write_text("# A\n- x\n", encoding="utf-8")
    out = tmp_path / "a.pptx"
    code = main(["build", str(f), "-o", str(out)])
    if code == 2:
        pytest.skip("layout/render not merged yet")
    assert code == 0 and out.exists() and out.stat().st_size > 0


def test_preview_without_backend_is_a_clear_error(tmp_path, capsys, monkeypatch):
    f = tmp_path / "a.md"
    f.write_text("# A\n- x\n", encoding="utf-8")
    code = main(["preview", str(f), "-o", str(tmp_path / "png")])
    err = capsys.readouterr().err
    if code == 0:
        pytest.skip("preview backend available")
    assert code == 2 and err.startswith("error")


def test_check_shows_lenient_hints(tmp_path, capsys):
    f = tmp_path / "a.md"
    f.write_text("marp: true\n\n# A\n@3 chevorn\n* x\n@end\n", encoding="utf-8")
    assert main(["check", str(f)]) == 0
    out = capsys.readouterr().out
    assert "marp-syntax" in out and "did you mean 'chevron'" in out and "bullet-star" in out
    assert "end-outside-box" in out and out.startswith("warning")


def test_check_never_tracebacks_on_binary_file(tmp_path, capsys):
    f = tmp_path / "a.md"
    f.write_bytes(b"\xff\xfe\x00bad")
    assert main(["check", str(f)]) == 2
    assert "Traceback" not in capsys.readouterr().err


def test_check_runs_layout_lint_and_reports_alt_in_json(tmp_path, capsys):
    f = tmp_path / "a.md"
    f.write_text("# A\n![](x.png)\n", encoding="utf-8")
    assert main(["check", str(f), "--format", "json"]) == 0
    data = json.loads(capsys.readouterr().out)
    assert {"image-alt", "alt"} <= {d["rule"] for d in data}
    assert all(set(d) == {"level", "message", "line", "slide", "rule", "hint"} for d in data)


def test_docs_default_and_topic(capsys):
    assert main(["docs"]) == 0
    assert "# SlideMark" in capsys.readouterr().out
    assert main(["docs", "syntax"]) == 0
    assert capsys.readouterr().out.strip()


def test_docs_unknown_topic(capsys):
    assert main(["docs", "sintax"]) == 2
    err = capsys.readouterr().err
    assert "unknown topic 'sintax'; topics:" in err and "syntax" in err


def test_schema(capsys):
    assert main(["schema"]) == 0
    assert "properties" in json.loads(capsys.readouterr().out)
    assert main(["schema", "--indent", "2"]) == 0
    assert "\n  " in capsys.readouterr().out


def test_json_roundtrip_build_and_check(tmp_path):
    from pptx import Presentation

    from slidemark.parser import parse

    deck = parse("# A\n- x\n---\n# B\n- y\n")
    j = tmp_path / "d.json"
    j.write_text(deck.model_dump_json(), encoding="utf-8")
    out = tmp_path / "o.pptx"
    assert main(["build", str(j), "-o", str(out)]) == 0
    assert len(Presentation(str(out)).slides) == 2
    assert main(["check", str(j)]) == 0


def test_bad_json_exit_1(tmp_path, capsys):
    j = tmp_path / "bad.json"
    j.write_text('{"slides": 3}', encoding="utf-8")
    assert main(["check", str(j)]) == 1
    assert "bad-json" in capsys.readouterr().out
    assert main(["build", str(j), "-o", str(tmp_path / "x.pptx")]) == 1
    captured = capsys.readouterr()
    assert "bad-json" in captured.out
    j.write_text("not json", encoding="utf-8")
    assert main(["check", str(j)]) == 1


def test_skill_install(tmp_path, capsys):
    d = tmp_path / "sk"
    assert main(["skill", "install", "--dir", str(d)]) == 0
    assert str(d) in capsys.readouterr().out
    assert (d / "SKILL.md").exists() and any((d / "reference").glob("*.md"))
    assert main(["skill", "install", "--dir", str(d)]) == 0  # idempotent


def test_skill_install_print(tmp_path, capsys):
    d = tmp_path / "sk2"
    assert main(["skill", "install", "--dir", str(d), "--print"]) == 0
    assert "SKILL.md" in capsys.readouterr().out and not d.exists()


def test_help_lists_new_commands(capsys):
    main(["--help"])
    out = capsys.readouterr().out
    assert all(c in out for c in ("docs", "schema", "skill"))


def test_preview_accepts_a_pptx(tmp_path, capsys):
    from .helpers import needs_soffice  # noqa: F401

    if __import__("shutil").which("soffice") is None:
        pytest.skip("LibreOffice not installed")
    md = tmp_path / "a.md"
    md.write_text("# A\n- x\n", encoding="utf-8")
    pptx = tmp_path / "a.pptx"
    assert main(["build", str(md), "-o", str(pptx)]) == 0
    capsys.readouterr()
    assert main(["preview", str(pptx), "-o", str(tmp_path / "png")]) == 0
    assert (tmp_path / "png" / "slide-01.png").stat().st_size > 0


def test_preview_missing_pptx_is_a_clear_error(tmp_path, capsys):
    assert main(["preview", str(tmp_path / "nope.pptx")]) == 2
    assert capsys.readouterr().err.startswith("error")

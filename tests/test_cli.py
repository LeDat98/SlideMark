import json
from pathlib import Path

import pytest

from slidemark import __version__
from slidemark.cli import main

CORPUS = Path(__file__).parent.parent / "bench" / "corpus"


def test_version(capsys):
    assert main(["version"]) == 0
    assert capsys.readouterr().out.strip() == __version__


def test_check_ok(tmp_path, capsys):
    f = tmp_path / "a.md"
    f.write_text("# A\n- x\n", encoding="utf-8")
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

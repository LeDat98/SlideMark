"""examples/26-ai-overview.md round-trips: `steps num`, a dark closing cover, `nested.list.title=off`."""

from __future__ import annotations

import importlib.util
from pathlib import Path

from slidemark.build import build
from slidemark.importer import import_pptx
from slidemark.parser import parse

ROOT = Path(__file__).resolve().parent.parent
_SPEC = importlib.util.spec_from_file_location("slidemark_bench_roundtrip26", ROOT / "bench" / "roundtrip.py")
rt = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(rt)  # type: ignore[union-attr]


def _import(src: str, tmp_path: Path) -> str:
    a = tmp_path / "a.pptx"
    build(src, a, base_dir=ROOT / "examples")
    return import_pptx(a, tmp_path)[0]


def test_example_26_is_lossless(tmp_path):
    text = (ROOT / "examples" / "26-ai-overview.md").read_text(encoding="utf-8")
    diffs, _t, _a, _b = rt.roundtrip_text(text, tmp_path, ROOT / "examples")
    assert not diffs, diffs[:5]
    work = tmp_path / "d"
    work.mkdir()
    assert not rt.design_diffs(text, work)


def test_steps_caption_comes_back_as_the_num_word(tmp_path):
    t = _import("# T\n@3 steps num\n## a\n- x\n## b\n- y\n## c\n- z\n", tmp_path)
    assert "@3 steps num\n" in t
    t = _import("# T\n@3 steps\n## a\n- x\n## b\n- y\n## c\n- z\n", tmp_path)
    assert "@3 steps\n" in t


def test_dark_closing_slide_with_a_line_is_a_cover(tmp_path):
    src = (
        "# Open\n@cover bg=primary dark\nsub\n\n# Body\n- a\n\n# Thanks\n@cover bg=primary dark\nQuestions\n"
    )
    last = parse(_import(src, tmp_path)).slides[-1]
    assert last.layout == "cover" and "dark" in last.classes and last.background == "primary"


def test_a_plain_section_stays_a_section(tmp_path):
    t = _import("# Open\nsub\n\n# Body\n- a\n\n# Part two\n\n# More\n- b\n", tmp_path)
    assert parse(t).slides[2].layout in (None, "section")


def test_nested_list_title_off_is_restored(tmp_path):
    src = (
        "style: nested.list.title=off\n\n# Rings\n@nested\n"
        "## One {icon=globe}\nfirst body\n## Two {icon=chart}\nsecond body\n## Three {icon=cpu}\nthird body\n"
    )
    assert "nested.list.title=off" in _import(src, tmp_path)


def test_nested_list_title_on_is_not_written(tmp_path):
    src = (
        "# Rings\n@nested\n## One {icon=globe}\nfirst\n## Two {icon=chart}\nsecond\n"
        "## Three {icon=cpu}\nthird\n"
    )
    assert "list.title" not in _import(src, tmp_path)

"""Agent-eval harness (bench/eval.py): task tags, --tasks filter, tolerance for missing assets."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

BENCH = Path(__file__).resolve().parent.parent / "bench"
_spec = importlib.util.spec_from_file_location("slidemark_bench_eval", BENCH / "eval.py")
ev = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ev)


def test_parse_task_strips_tags():
    tags, body = ev.parse_task("<!-- tags: jp dense html -->\n日本語で作って\n")
    assert tags == ["jp", "dense", "html"]
    assert body == "日本語で作って\n"
    assert "tags" not in body


def test_parse_task_without_tags_is_unchanged():
    assert ev.parse_task("Make a slide\n") == ([], "Make a slide\n")
    # a tags comment that is not on the first line is task text, not metadata
    text = "Make a slide <!-- tags: x -->\n"
    assert ev.parse_task(text) == ([], text)


def test_all_tasks_have_tags_and_are_unique():
    tasks = sorted((BENCH / "tasks").glob("*.md"))
    assert len(tasks) >= 100
    nums = [t.name.split("-", 1)[0] for t in tasks]
    assert len(set(nums)) == len(nums)
    for t in tasks:
        tags, body = ev.parse_task(t.read_text(encoding="utf-8"))
        assert tags, t.name
        assert body.strip() and "tags:" not in body, t.name


def test_task_mix():
    tags = {}
    for t in (BENCH / "tasks").glob("*.md"):
        for tag in ev.parse_task(t.read_text(encoding="utf-8"))[0]:
            tags[tag] = tags.get(tag, 0) + 1
    assert tags["jp"] >= 25 and tags["html"] >= 15 and tags["vi"] >= 10 and tags["en"] >= 15
    assert tags["hard"] >= 8 and tags["edit"] >= 5


def test_select_tasks_glob_and_tag(tmp_path):
    a = tmp_path / "01-a.md"
    b = tmp_path / "02-b-jp.md"
    c = tmp_path / "30-c.md"
    a.write_text("<!-- tags: en -->\nx", encoding="utf-8")
    b.write_text("<!-- tags: jp html -->\ny", encoding="utf-8")
    c.write_text("z", encoding="utf-8")
    tasks = [a, b, c]
    assert ev.select_tasks(tasks) == tasks
    assert ev.select_tasks(tasks, "0*") == [a, b]
    assert ev.select_tasks(tasks, "*-jp") == [b]
    assert ev.select_tasks(tasks, "01-a.md, 30-*") == [a, c]
    assert ev.select_tasks(tasks, tag="html") == [b]
    assert ev.select_tasks(tasks, "0*", tag="en") == [a]
    assert ev.select_tasks(tasks, "nothing") == []


def test_missing_assets_do_not_fail_first_pass():
    deck = (
        "theme: corp.pptx\n\n# 動画と画像\n> 資産は存在しない\n"
        "## 画像\n![ロゴ](nope.png)\n## ビデオ\n![デモ](demo.mp4)\n## 音声\n![曲](song.mp3)\n"
    )
    r = ev.score(deck)
    assert r["first_pass"] and r["warnings"] == 0
    assert r["assets"] >= 3  # image, video, audio, and the template: reported, not failed


def test_other_problems_still_fail():
    r = ev.score("# Bad\n```column\n,A,B\nx,not,numbers\n```\n")
    assert not r["first_pass"] and r["warnings"] >= 1
    # an unknown theme name is a real mistake, not a missing asset
    assert not ev.score("theme: nonexistent-theme\n\n# A\n- b\n")["first_pass"]


def test_is_asset_missing_rules():
    from slidemark.ir import Diagnostic

    def d(rule, msg="x"):
        return Diagnostic(level="warning", message=msg, rule=rule)

    assert ev.is_asset_missing(d("image-missing"))
    assert ev.is_asset_missing(d("missing-media"))
    assert ev.is_asset_missing(d("bad-theme", "theme 'a.pptx': file not found"))
    assert not ev.is_asset_missing(d("bad-theme", "theme 'x': unknown theme"))
    assert not ev.is_asset_missing(d("overflow"))


def test_main_tasks_subset_and_summary_by_tag(tmp_path, capsys):
    ans = tmp_path / "ans"
    ans.mkdir()
    (ans / "21-jp-quarterly-4col.md").write_text("# 売上\n- 12億円\n", encoding="utf-8")
    (ans / "51-html-card-grid.md").write_text("# Cards\n@3\n## A\nx\n## B\ny\n## C\nz\n", encoding="utf-8")
    rc = ev.main(["--answers", str(ans), "--tasks", "21-*,51-*", "--summary-by", "tag"])
    assert rc == 0
    out = capsys.readouterr().out
    summary = json.loads(out.strip().splitlines()[-1])
    assert summary["tasks"] == 2
    assert summary["by_tag"]["jp"]["tasks"] == 1
    assert summary["by_tag"]["html"]["first_pass_rate"] == 1.0
    # the subset glob excludes everything else
    assert "22-" not in out
    assert ev.main(["--answers", str(ans), "--tag", "html"]) == 0
    assert "21-jp" not in capsys.readouterr().out


def test_main_no_match_returns_1(tmp_path):
    assert ev.main(["--answers", str(tmp_path / "a"), "--tasks", "zzz*"]) == 1


@pytest.mark.parametrize("name", ["run-5-reference"])
def test_reference_answers_pass(name):
    d = BENCH / "answers" / name
    files = sorted(d.glob("*.md"))
    assert len(files) >= 10
    for f in files:
        r = ev.score(f.read_text(encoding="utf-8"))
        assert r["first_pass"], (f.name, r["rules"])

"""Self-review loop bench (L7 gate "preview + automatic design critique fixes layout issues").

Usage: python bench/selfreview.py [--record] [--only examples|answers|synthetic] [--dump DIR]

Runs ``slidemark.selfreview.self_review`` (the loop behind ``slidemark review --fix``) over
  (a) every deck in examples/, (b) bench/answers/run-5-sonnet, (c) 30 synthetic broken decks generated
  deterministically (overfull lists, 9-12 row tables, 6 boxes of 8 bullets, low-contrast colors, long titles,
  typos, and mixes).
and reports, per group: decks with warnings before/after, mean review score before/after, decks changed and
rounds used. Good decks (examples, answers) must come out unchanged when they have no mechanical problem.
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
from pathlib import Path

from slidemark.selfreview import self_review

ROOT = Path(__file__).resolve().parent.parent
HISTORY = ROOT / "bench" / "selfreview_history.jsonl"


# --------------------------------------------------------------------------- synthetic broken decks

EN = [
    "Revenue grew in every region",
    "Churn fell after onboarding changes",
    "Support tickets by category",
    "Hiring plan for next fiscal year",
    "Security review findings",
    "Roadmap milestones and owners",
]
JP = [
    "売上は全地域で増加した",
    "オンボーディング刷新で解約率が低下",
    "問い合わせ件数のカテゴリ別内訳",
    "来期の採用計画と担当者",
    "セキュリティレビューの指摘事項",
    "ロードマップの主要マイルストーン",
]
OK_SLIDE = (
    "# Summary\n> Three points to remember\n## Now\n- Revenue +8%\n## Next\n- Launch in Q4\n"
    "## Risk\n- Churn 2.1%\n> Decide on Friday\n"
)


def _items(n: int, jp: bool, k: int = 0) -> str:
    if jp:
        return "\n".join(f"- 施策{k}-{i + 1}について担当と期限を決めて進める" for i in range(n))
    return "\n".join(f"- Item {k}-{i + 1} owner set" for i in range(n))


def _rows(n: int, jp: bool) -> list[str]:
    return [f"{'行' if jp else 'Row '}{i + 1},{(i + 1) * 3},{(i + 1) * 7}" for i in range(n)]


def _boxes3(first: str = "## A\n- a1\n- a2\n- a3\n", skip: int = 0) -> str:
    """Three filled boxes and a conclusion; ``first`` replaces box A (or box ``skip``+1 when skip is set)."""
    rest = ["## B\n- b1\n- b2\n- b3\n", "## C\n- c1\n- c2\n- c3\n"]
    boxes = [first, *rest] if not skip else [rest[0], first, rest[1]]
    return "".join(boxes) + "> Conclusion\n"


def _deck(head: str, *slides: str) -> str:
    return head + "\n" + OK_SLIDE + "\n" + "\n".join(slides)


def synthetic() -> list[tuple[str, str]]:
    """30 (name, source) pairs, deterministic."""
    out: list[tuple[str, str]] = []
    # 1. overfull lists (4)
    for i, (n, jp) in enumerate([(22, True), (26, False), (30, True), (24, False)]):
        t = (JP if jp else EN)[i]
        out.append((f"list-{i + 1}", _deck("", f"# {t}\n> Key message\n{_items(n, jp)}\n")))
    # 2. 9-12 row tables, GFM and CSV (4)
    for i, (n, jp, csv) in enumerate(
        [(9, False, False), (10, True, True), (12, False, True), (11, True, False)]
    ):
        t = (EN if not jp else JP)[i]
        rows = _rows(n, jp)
        hdr = "区分,A,B" if jp else "Item,A,B"
        if csv:
            tab = "```table\n" + hdr + "\n" + "\n".join(rows) + "\n```"
        else:
            tab = f"| {hdr.replace(',', ' | ')} |\n|-|-|-|\n" + "\n".join(
                "| " + r.replace(",", " | ") + " |" for r in rows
            )
        out.append((f"table-{i + 1}", _deck("", f"# {t}\n{tab}\n")))
    # 3. 6 boxes of 8 bullets, 5 of 7 (4)
    for i, (nb, nl, jp) in enumerate([(6, 8, True), (6, 8, False), (5, 7, True), (5, 7, False)]):
        t = (JP if jp else EN)[i]
        boxes = "\n".join(f"## {'箱' if jp else 'Box '}{b + 1}\n{_items(nl, jp, b + 1)}" for b in range(nb))
        out.append((f"boxes-{i + 1}", _deck("", f"# {t}\n> Key message\n{boxes}\n※ Source: internal\n")))
    # 4. low-contrast declared colors (5): everything else on the slide is well filled
    contrast = [
        _boxes3("## A\n{color=#EEEEEE}\n- light text on the white card\n- second line\n- third line\n"),
        _boxes3("## C {fill=#111111}\n- dark fill, default text color\n- second line\n- third line\n", 2),
        _boxes3("## A {color=#F5F5F5}\n- pale text\n- second line\n- third line\n"),
        _boxes3("## 売上 {color=#DDDDDD}\n- 淡い灰色の文字\n- 二行目\n- 三行目\n"),
        _boxes3("## A {color=#FFFF99}\n- yellow on white\n- second line\n- third line\n"),
    ]
    for i, body in enumerate(contrast):
        out.append((f"contrast-{i + 1}", _deck("", f"# Colors {i + 1}\n> Key message\n{body}")))
    # 5. long titles (5)
    titles = [
        "The quarterly review of revenue, churn, hiring and the security roadmap for the whole company",
        "全社横断プロジェクトの進捗状況と来期に向けた課題および対応方針の整理",
        "Customer onboarding: what changed, why it matters and what we measure next",
        "Migration plan - phases, owners, risks and the rollback criteria for each region",
        "新規事業の検討状況：市場規模・競合・自社の強み・今後の進め方について",
    ]
    for i, t in enumerate(titles):
        out.append((f"title-{i + 1}", _deck("", f"# {t}\n{_boxes3()}")))
    # 6. typos (5)
    typos = [
        ("@3 flwo\n", _boxes3()),
        ("", _boxes3("## A {.primry}\n- a1\n- a2\n- a3\n")),
        ("", _boxes3("## A {icon=chrt}\n- a1\n- a2\n- a3\n")),
        ("@3\n", _boxes3().replace("> Conclusion", "\n| x | y |\n|---|---|\n| 1 | 2 |\n> Conclusion")),
        ("", _boxes3().replace("> Conclusion", "> [!wran] price change in November")),
    ]
    for i, (at, body) in enumerate(typos):
        out.append((f"typo-{i + 1}", _deck("", f"# Typos {i + 1}\n{at}> Key message\n{body}")))
    # 7. mixes (3)
    long_t = "A very long title that explains everything about the project in one sentence - with details"
    out.append(("mix-1", _deck("", f"# {long_t}\n> Key message\n{_items(24, False)}\n")))
    boxes = "\n".join(f"## Box {b + 1}\n{_items(8, False, b + 1)}" for b in range(6))
    out.append(("mix-2", _deck("", f"# Typos and density\n@3 flwo\n> Key message\n{boxes}\n")))
    jp_t = "全社横断プロジェクトの進捗状況と来期に向けた課題および対応方針"
    mix3 = f"# {jp_t}\n## 現状\n{{color=#EEEEEE}}\n- 淡い文字\n{_items(10, True)}\n"
    out.append(("mix-3", _deck("theme: jp-business\nlang: ja\n", mix3)))
    assert len(out) == 30, len(out)
    return out


# --------------------------------------------------------------------------- run


def run_group(name: str, decks: list[tuple[str, str, Path | None]], dump: Path | None) -> dict:
    rows = []
    t0 = time.perf_counter()
    for deck_name, text, base in decks:
        res = self_review(text, base)
        if dump is not None:
            dump.mkdir(parents=True, exist_ok=True)
            (dump / f"{name}-{deck_name}.md").write_text(res.text, encoding="utf-8")
        rows.append(
            {
                "deck": deck_name,
                "warn_before": res.before.warnings,
                "warn_after": res.after.warnings,
                "dense_after": res.after.dense,
                "score_before": res.before.score,
                "score_after": res.after.score,
                "changed": res.text != text,
                "rounds": res.rounds,
                "fixes": [f.rule for f in res.fixed],
            }
        )
    n = len(rows) or 1
    return {
        "group": name,
        "decks": len(rows),
        "with_warnings_before": sum(r["warn_before"] > 0 for r in rows),
        "with_warnings_after": sum(r["warn_after"] > 0 or r["dense_after"] > 0 for r in rows),
        "mean_score_before": round(statistics.fmean(r["score_before"] for r in rows), 2) if rows else 0,
        "mean_score_after": round(statistics.fmean(r["score_after"] for r in rows), 2) if rows else 0,
        "changed": sum(r["changed"] for r in rows),
        "rounds_total": sum(r["rounds"] for r in rows),
        "rounds_mean": round(sum(r["rounds"] for r in rows) / n, 2),
        "seconds": round(time.perf_counter() - t0, 1),
        "rows": rows,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", choices=["examples", "answers", "synthetic"])
    ap.add_argument("--record", action="store_true", help=f"append the summary to {HISTORY.name}")
    ap.add_argument("--dump", type=Path, help="write every fixed deck here")
    ap.add_argument("-v", "--verbose", action="store_true", help="list decks that changed or still warn")
    args = ap.parse_args()
    groups: list[tuple[str, list[tuple[str, str, Path | None]]]] = []
    ex = [(p.name, p.read_text(encoding="utf-8"), p.parent) for p in sorted((ROOT / "examples").glob("*.md"))]
    an_dir = ROOT / "bench" / "answers" / "run-5-sonnet"
    an = [(p.name, p.read_text(encoding="utf-8"), p.parent) for p in sorted(an_dir.glob("*.md"))]
    syn = [(n, t, None) for n, t in synthetic()]
    for g, decks in (("examples", ex), ("answers", an), ("synthetic", syn)):
        if args.only in (None, g):
            groups.append((g, decks))
    summary = []
    for g, decks in groups:
        r = run_group(g, decks, args.dump)
        summary.append({k: v for k, v in r.items() if k != "rows"})
        print(json.dumps(summary[-1], ensure_ascii=False))
        if args.verbose:
            for row in r["rows"]:
                if row["changed"] or row["warn_after"] or row["dense_after"]:
                    print(
                        f"  {row['deck']}: warn {row['warn_before']}->{row['warn_after']} "
                        f"score {row['score_before']}->{row['score_after']} fixes={row['fixes']}"
                    )
    if args.record:
        with HISTORY.open("a", encoding="utf-8") as f:
            f.write(
                json.dumps({"date": time.strftime("%Y-%m-%d"), "groups": summary}, ensure_ascii=False) + "\n"
            )
    return 0


if __name__ == "__main__":
    sys.exit(main())

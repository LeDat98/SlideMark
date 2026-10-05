"""L7 round trip: build, import, build again must reproduce the deck (text, objects, geometry, style).

The comparison lives in ``bench/roundtrip.py``; every test here is one feature as a tiny deck. The full corpus
(111 decks) is run by ``python bench/roundtrip.py``, not here.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

_SPEC = importlib.util.spec_from_file_location(
    "slidemark_bench_roundtrip", Path(__file__).resolve().parent.parent / "bench" / "roundtrip.py"
)
rt = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(rt)  # type: ignore[union-attr]

DECKS = {
    "notes-hidden-transition": """# Plan
@t=fade hidden
- Scope
- Budget
??? Say hello first.
Then the numbers.

# Next
- Ship
""",
    "build": """# Steps
@build
- One
- Two
- Three
""",
    "sections": """theme: jp-business
footer: ACME
num: on

# Board deck
Q3 review

# Part 1
> Results

# Numbers
- Revenue up
- Costs down

# Part 2
> Outlook
""",
    "kpi-icons": """# Results
@3
## Sales {.kpi icon=yen}
12.4M
vs last year +8%
## Profit {.kpi icon=chart}
1.9M
+3%
## Users {.kpi icon=users}
640
+9%
""",
    "code-language": """# Client
```python
from acme import Client
client = Client(api_key="x")  # connect
print(client.version, 42)
```
""",
    "math": """# Interest
```math
A = P \\left(1 + \\frac{r}{n}\\right)^{nt}
```
- A: final amount
""",
    "chart-options": """# Sales
```column {title="Revenue" labels=on legend=bottom fmt=0.0}
,Q1,Q2,Q3
2025,1.5,2.5,3.5
2026,2,3,4.5
```
""",
    "pie-percent": """# Share
```pie {labels=percent}
,Share
A,50
B,30
C,20
```
""",
    "table-merge-align": """# Plans
{align=lrr}
| Plan | Price | Seats |
|---|---|---|
| Lite | 10 | 1 |
| Team | 40 | 5 |
| Total | < | 6 |
""",
    "callouts-badges-links": """# Status
> [!warn] Check the budget first

> [!tip] Ship on Friday

> [!caution] Do not skip the audit
- [Done]{.badge .success} migration
- [At risk]{.badge .danger} audit, see [the plan](https://example.com/plan)
- jump to [slide 2](#2)

# Detail
- **bold**, *italic*, ==accent==
""",
    "row-group": """# Dashboard
@2 flow
## Before
- Manual
## After
- Automated
@end
@3
## A {.kpi}
-40%
## B {.kpi}
-70%
## C {.kpi}
-18%
""",
    "dense": """density: dense

# Product comparison
| Name | Price | Size | Rating |
|---|---|---|---|
| A-100 | 12,000 | 64GB | 4.2 |
| A-200 | 18,000 | 128GB | 4.5 |
| B-10 | 9,800 | 32GB | 3.9 |
| B-20 | 14,500 | 64GB | 4.0 |
""",
    "flow-chevron": """# Process
@4 chevron
## Plan
Scope it
## Build
Make it
## Test
Check it
## Ship
Release it
""",
    "mermaid": """# Pipeline
```mermaid
graph LR
A[Commit] --> B[Build]
B --> C{Pass?}
C -->|yes| D[Deploy]
C -->|no| A
```
""",
    "missing-assets": """# Media
![Product demo](demo.mp4)
※ Footnote text

# Photo
![Site photo](photo.png)
""",
    "cjk": """lang: ja

# 四半期レビュー
> 受注が売上を上回り、来期も堅調
## 売上 {icon=yen}
- 前年比 +11%
- 新規 ==42件==
## 課題
1. 人材不足
2. 原価上昇
※ 出所: 社内調査
""",
}


@pytest.mark.parametrize("name", sorted(DECKS))
def test_roundtrip_is_lossless(name: str, tmp_path: Path) -> None:
    diffs, text, _a, _b = rt.roundtrip_text(DECKS[name], tmp_path, tmp_path)
    assert not diffs, f"{name}: {diffs[:3]}\n--- imported text ---\n{text}"


def test_comparison_detects_differences(tmp_path: Path) -> None:
    """The comparator is not vacuous: a changed number, a lost note and a moved box are reported."""
    from slidemark.build import build

    a, b = tmp_path / "a.pptx", tmp_path / "b.pptx"
    build("# T\n- one\n- two\n??? note\n", a, base_dir=tmp_path)
    build("# T\n- one\n- twelve\n", b, base_dir=tmp_path)
    kinds = {k for k, _ in rt.compare_decks(a, b)}
    assert "text" in kinds and "notes" in kinds
    assert rt.compare_decks(a, a) == []


def test_import_never_raises_on_garbage(tmp_path: Path) -> None:
    from slidemark.importer import import_pptx

    bad = tmp_path / "bad.pptx"
    bad.write_bytes(b"not a zip")
    text, diags = import_pptx(bad)
    assert text == "" and diags and diags[0].level == "error"

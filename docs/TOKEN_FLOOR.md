# Token floor research (L7 "syntax ≤ 20% of python-pptx")

Run 2026-10-05 (run 4). Tool: `bench/token_floor.py` (o200k_base proxy). Content = tokens of the visible
text alone (titles, runs, cells, chart data, notes), which every format must spend.

## Findings
| Deck set | content | SlideMark | python-pptx | SlideMark / pptx | floor (content / pptx) | markup ratio |
|---|---|---|---|---|---|---|
| corpus `q3-review` (hand-minimal python-pptx) | 131 | 155 | 518 | 30% | **25%** | 6% |
| eval tasks 01–20 (same Sonnet model wrote both answers) | 2,247 | 3,152 | 54,086 | **6%** | 4% | 2% |

1. **The q3 gate is below the content floor.** Even a format with zero markup costs 25% of the q3 python-pptx
   file, so "≤ 20%" cannot pass on q3; SlideMark already spends only 24 markup tokens there.
2. **On agent-written decks the gate passes by a wide margin**: python-pptx answers average 2,700 tokens per
   deck (imports, `Inches()`, loops, explicit geometry); SlideMark answers average 158 (6%).
3. **Where SlideMark's remaining markup goes** (100 eval answers, runs 4–7, 10.3k markup tokens): design-token
   header lines 32% (brand runs), table pipes 16%, list markers 11%, fence lines 10%, `{...}` attrs 9%, box
   headings 8%. Everything else ≤ 6%.
4. **Cheapest verified lever: CSV tables.** Rewriting every GFM table as a ```` ```table ```` CSV fence saves
   **7.1%** of total tokens on the 66 answer decks that have tables, with merges (`<` `^`), badges and inline
   marks intact (parse checked: 0 errors). Making the GFM separator row optional would save only 2.4%.
   → SKILL.md now recommends the CSV fence.

## Proposal for the owner
Replace the q3-only wording of the L7 token gate with two measurable bars:
- agent-written decks: SlideMark ≤ 20% of the python-pptx answer for the same task (now 6% on 20 tasks), and
- markup ≤ 10% of python-pptx markup on the corpus (q3 now 6%).
Until then the gate stays unchecked in `docs/TARGETS.md`.

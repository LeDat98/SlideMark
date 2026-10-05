# Tips for agents using SlideMark

Practical patterns that cut tokens and retries. Budget: keep this file under ~1,000 tokens.
✅ = verified by tests/bench, ⏳ = design intent, verify before relying on it.

1. ✅ **No separators, no front-matter needed.** `# Title` starts a slide; header `key: value` lines are optional.
2. ⏳ **Let headings do the layout.** `##` boxes are arranged automatically (2 → columns, 4 → 2×2 ...).
   Write an `@` line only when the automatic result is wrong.
3. ⏳ **Complex layouts in one line:** `@aab/aac` = a tall box on the left two-thirds and two stacked boxes on the right.
4. ✅ **Charts and tables as CSV** (` ```column ` + `,Q1,Q2` / `2025,10,12`), not YAML/JSON.
   Measured: the full deck costs 30% of the python-pptx tokens; a dense JP deck costs 58% of the equivalent HTML.
5. ⏳ **Lead and conclusion for free:** `>` right after the title = key message; `>` at the end = bottom bar.
6. ⏳ **Don't set positions** (`{x= y= w= h=}`) unless needed; they cost tokens and make slides fragile.
7. ⏳ **Fix only the broken slide.** Diagnostics name the slide and line.
8. ✅ **Close a row of boxes with `@end`** before a slide-level table/chart; otherwise it lands inside the last
   box. `check` flags it as `missing-end`. A closing `>` needs no `@end` (it is always the conclusion).
9. ✅ **Org charts and approval flows need no shapes:** `@.a./bcd a>b a>c a>d` or `@3 a>b b>c` (connectors).
10. ✅ **Skill docs are budgeted:** SKILL.md ≈ 1,160 tokens; each `slidemark docs <topic>` page ≤ 720.

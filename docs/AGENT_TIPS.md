# Tips for agents using SlideMark

Practical patterns that cut tokens and retries. Budget: keep this file under ~1,000 tokens.
✅ = verified by tests/bench, ⏳ = design intent, verify before relying on it.

1. ✅ **No separators, no front-matter needed.** `# Title` starts a slide; header `key: value` lines are optional.
2. ✅ **Let headings do the layout.** `##` boxes are arranged automatically (2 → columns, 4 → 2×2 ...).
   Write an `@` line only when the automatic result is wrong.
3. ✅ **Complex layouts in one line:** `@aab/aac` = a tall box on the left two-thirds and two stacked boxes on the right.
4. ✅ **Charts and tables as CSV** (` ```column ` + `,Q1,Q2` / `2025,10,12`), not YAML/JSON.
   Measured: the full deck costs 30% of the python-pptx tokens; a dense JP deck costs 58% of the equivalent HTML.
5. ✅ **Lead and conclusion for free:** `>` right after the title = key message; `>` at the end = bottom bar.
6. ⏳ **Don't set positions** (`{x= y= w= h=}`) unless needed; they cost tokens and make slides fragile.
7. ✅ **Fix only the broken slide.** Diagnostics name the slide and line.
8. ✅ **Close a row of boxes with `@end`** before a slide-level table/chart; otherwise it lands inside the last
   box. `check` flags it as `missing-end`. A closing `>` needs no `@end` (it is always the conclusion).
9. ✅ **Org charts and approval flows need no shapes:** `@.a./bcd a>b a>c a>d` or `@3 a>b b>c` (connectors).
10. ✅ **SKILL.md alone is enough:** ≈ 910 tokens; eval run 4 wrote 20/20 clean decks without reading any reference page.
11. ✅ **Agents get it right from SKILL.md alone:** eval run 2 (Sonnet, 20 tasks, docs only) = 90% first-pass clean,
    ~158 tokens per deck. The two misses: `align=` letter count ≠ columns; a second `@` grid (now row groups).
12. ✅ **Free-form HTML still gives editable slides:** a ```` ```html {render=native} ```` fence with CSS grid/flex cards
    becomes native rounded rects + text (verified 2026-10-05, XSD-valid); canvas/SVG/gradients fall back to an image.
13. ✅ **Video costs one line:** `![what it shows](demo.mp4)` embeds a playable native video with a poster frame.
14. ✅ **`@2 1:2` is fine** (column count + matching ratios); eval run 5 (80 tasks) passed 79/80 first time from SKILL.md alone.
- Own brand in 3–4 header lines (`theme: none` + `colors:` + `fonts:` + `style:`): verified on 20 brand briefs (run-6-brand, Sonnet, design.md only): 19/20 check-clean first pass, 20 distinct palettes.
- With a dark `bg`, set `surface` and `border` too, or cards keep the light neutral defaults (seen in eval decks).
- Gradient cards need a text color that passes on every stop: lint checks each stop (`hero.fill` teal end failed 2.6:1 in examples/13).
- Tables as a ```` ```table ```` CSV fence instead of GFM pipes: −7.1% tokens on the 66 eval decks with tables, merges (`<` `^`) and badges intact (run 4, `bench/token_floor.py`).

# Tips for agents using SlideMark

Practical patterns that cut tokens and retries. Budget: keep this file under ~1,000 tokens.
✅ = verified by tests/bench, ⏳ = design intent, verify before relying on it.

1. ✅ **No separators, no front-matter needed.** `# Title` starts a slide; header `key: value` lines are optional.
2. ✅ **Let headings do the layout.** `##` boxes are arranged automatically (2 → columns, 4 → 2×2 ...).
   Write an `@` line only when the automatic result is wrong.
3. ✅ **Complex layouts in one line:** `@aab/aac` = a tall box on the left two-thirds and two stacked boxes on the right.
4. ✅ **Charts and tables as CSV** (` ```column ` + `,Q1,Q2` / `2025,10,12`), not YAML/JSON.
   Measured: the deck source is 15–30% of the equivalent python-pptx script (file size, not agent run cost).
5. ✅ **Lead and conclusion for free:** `>` right after the title = key message; `>` at the end = bottom bar.
6. ⏳ **Don't set positions** (`{x= y= w= h=}`) unless needed; they cost tokens and make slides fragile.
7. ✅ **Fix only the broken slide.** Diagnostics name the slide and line.
8. ✅ **Close a row of boxes with `@end`** before a slide-level table/chart; otherwise it lands inside the last
   box. `check` flags it as `missing-end`. A closing `>` needs no `@end` (it is always the conclusion).
9. ✅ **Org charts and approval flows need no shapes:** `@.a./bcd a>b a>c a>d` or `@3 a>b b>c` (connectors).
10. ✅ **SKILL.md is the only document** (≈ 2,800 tokens since 2026-10-05 run 5): when reference pages were offered, 3/3
    pilot agents fetched 4–6 of them first, each fetch a full model call (`docs/AGENT_COST.md`).
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
- Model calls decide agent cost, not file size: one extra call re-reads the whole context (6–12k units). Write and build in one call (`slidemark build - -o deck.pptx --save deck.md <<'EOF'`), stop at 0 warnings (`docs/AGENT_COST.md`).
- A chevron row lines up with the table under it only when the table has one column per chevron (`chevron_table_align`, test `tests/test_l3_w2a.py`); put steps as columns, or drop the chevrons when the table rows are the steps.
- A chart takeaway costs two attributes: `hl=<category> note="<one line>"` draws an accent bar and a native callout pointing at it (examples/20 s3, 22 s4); in jp-business accent = red, so highlight gains, not losses.
- Status columns read best as a badge alone in its cell (`| [計画中]{.badge .muted} |`): it becomes a native pill with a column-shared width (11 s7, 16 s4); a badge after short text (`4.2万台 [首位]{.badge .success}`) aligns on one left edge.
- Decision step: SKILL.md makes the agent settle deck frame (colours, fonts, sizes, chrome), per-slide form + one emphasis + overrides, and chart/table treatment before writing; the header lines and attributes are the record, `design-none` / `design-slide` warn when nothing is stated, and the patterns show every slide carrying a choice (`docs/DESIGN_REQUIRED.md`). It adds no model call: the decisions are written in the same heredoc.
- A python-pptx style frame (top strip, title rule, KPI stripe, ■ bullets, bold lead, footer colour) is one `style:` line: `style: top.bar=primary title.rule=secondary kpi.stripe=secondary bullet=■ bullet.color=teal lead.bold=on footer.color=muted` (`docs/DESIGN_COVERAGE.md`, `tests/test_design_coverage.py`); numbered bars are `@rows` over a `1.` list, a process with captions `@4 steps num`.
- A python-pptx chart treatment is one fence line: `column {labels=outside labels.bold=on size=16,14 legend=top legend.size=14 gap=60 overlap=-5 min=0 max=1400 step=200 fmt=#,##0}`; a pie: `pie {labels=outside+name slice.line=bg,2 colors=...}`; a stack without totals: `stacked-column {labels=center totals=off}` (tests/test_chart_decisions.py).
- A KPI row is `@kpi` under the title plus plain `##` boxes (no `{.kpi}` on each); a one-slide size change is a `sizes: heading=26! body=24!` line inside that slide, a text look one token (`style: kpi.note="20 bold teal"`), a column emphasis `{hlcol=2027計画}` (`tests/test_design_native.py`).
- Fit lines instead of renders: `build` prints one line per slide (form used, `value 48->40pt (shrunk to fit)`, `free 31% below`, `took size=44, ignored h`); with 0 warnings and lines that match the decisions the deck is done, and the one look that is allowed is `--png sheet.png` in the same build command plus one Read (worst case 4 calls: read, build, look, hand back; `docs/AGENT_COST.md` AC7).
- Four more python-pptx decisions are one token or attribute each (`tests/test_design_coverage2.py`): a rule between a KPI number and its note `style: kpi.rule=border kpi.rule_h=1pt`; exact table rows `{rowh=0.8in,1.05in}` on the table (pinned rows are never stretched; text that does not fit warns `overflow`); a colour per bar `colors=a,b,c,d` on a one-series column/bar (`hl=` still wins); a label position per category `labels=above,below,above,above` on line/column. Place a KPI row with `{.kpi .hero w=45% h=55% y=24%}` (share of the body) instead of `x=`.
- Box chrome from python-pptx in tokens: `@4 items num` under the title (bullets become item cards, a numbered circle on each heading) + `style: heading.rule=accent item.border-left="5pt solid secondary" item.size=14 box.num.fill=primary`; process rows `render.chevron_shape=pentagon,chevron steps-card.border-top="5pt solid accent"`; bars `@rows plain` + `rows.stripe=primary,secondary bullet=■ bullet.color=accent`; cover `cover.bar=accent@edge cover.rule_w=6in cover.stripes=#1C3A68@8.9in` over `@cover bg=primary dark`. No css fence needed.
- `design-slide` lists each short slide with its missing groups (`slides 4 (values), 8 (form, emphasis)`): when a slide really has no focal figure or the deck frame already serves it, append `noemph` / `defaults` to its `@` line (one edit, render-neutral, verified on all 22 examples). `emphasis: 2 stated, keep one` means two emphasised elements: drop one `.hero` / `==x==` / `hl=`, and colour-code boxes with `{line=success}` (a value) instead of `{.success}` (an emphasis).

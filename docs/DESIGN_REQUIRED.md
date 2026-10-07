# Design decisions are the agent's (owner direction, 2026-10-07)

SlideMark assists an agent's design decisions; it never replaces them. The owner's reading of the design
wave results: the python-pptx arm looked better because the API forced the agent to decide every value
(position, size, colour, shape, type, chart treatment), which engaged its design ability; SlideMark's
defaults let the agent stop at content. Good defaults stay as a safety net, but the product must make the
agent state its own choices and then execute them in far fewer tokens than python-pptx.

This does not prescribe a look (`docs/DESIGN_FREEDOM.md` still holds): no colour, component or layout is
"right". It prescribes that the choices are made and written down.

## What a deck states (the decision checklist that SKILL.md asks for and `build` checks)

1. **Deck frame:** colours (`colors:`), fonts (`fonts:`), type scale (`sizes:`), chrome (`style:` title band,
   cards, rules), `footer:` / `num:`, or a `css` fence; a `theme:` preset alone is a starting point, not a decision.
2. **Per slide:** the form (list, cards, `@steps` / `@chevron`, grid `@cols`/`@grid`, table, chart kind, KPI
   row, `@html`), the one emphasis (`.hero`, `hl=`, `==accent==`, `{.accent}`), and where defaults would not
   serve the message: `size=`, `x y w h`, `fill=`, `color=`, `align=`, `valign=`.
3. **Charts and tables:** series colours (`colors=`), labels, legend, the takeaway (`hl=` + `note=`),
   `widths=`, `align=`, `hl=` rows, `.zebra`.

## Build feedback (rules)

- `design-none` (warning): the deck header carries none of `colors:` `fonts:` `sizes:` `style:` and no deck
  `css` fence. Hint: "state your design: colors: fonts: sizes: style: (or a css fence)".
- `design-slide` (warning, one line for the whole deck): slides where no element carries a choice (no
  attribute, class, option, directive beyond the block kind). Hint names the slides and the kinds of choice.
- Facts line gains `design: colors fonts sizes style footer; 12/15 slides carry choices` so an agent sees
  what it decided without re-opening the deck.

Agents may still write content-only decks (the warnings are advisory), but SKILL.md's recipe and patterns
show decks where every slide carries decisions, and the eval judges those runs.
- `attr-ignored` (warning, per slide, element kind and attribute; `style:` tokens once on their header line): a
  `{key=value}` or `style:` choice the layout does not honour where it was written. The hint names the form that works
  (`bold= on a KPI card is not honoured -> style: kpi.value.bold=on bolds the number`). Table in `src/slidemark/honour.py`, verified cell by cell in `tests/test_honour.py`; `docs/SYNTAX.md`
  "Build output". A silent no-op is the reason an agent opens an image.
- Fit lines (AC7): one line per slide in the `build` output, after the diagnostics and before `design:`: the form
  actually used, text size asked->reached, free space in the body, which attributes took / were ignored
  (`src/slidemark/fit.py`; `--quiet` or `fit: off` turns it off). With 0 warnings the fit lines are what an agent
  checks its decisions against; the only look left is `--png sheet.png` in the same build plus one Read.

## Tightened rules (owner, 2026-10-07): three groups per slide, four lines per deck

The first `design-slide` counted any attribute as a choice, so `{.kpi}` or `labels=on` passed. From DL3 on:

- `design-none` names each missing header line: `colors:` `fonts:` `sizes:` `style:` (a deck `css` fence or a
  theme file stands in for `style:`; `theme:` alone never counts).
- `design-slide` checks three groups on every content slide and names the missing ones:
  1. **form**: a layout directive or a block kind that is not the default list (`@N` grids, `@steps` `@chevron`
     `@rows` `@items` `@kpi` `@timeline` … `@free` `@html`, a table, a chart, boxes with headings);
  2. **emphasis**: exactly one stated emphasis (`.hero`, `hl=`, `==x==`, `{.accent}`, `note=`) or an explicit
     `@noemph` (the agent decided the slide has no focal figure);
  3. **values**: at least one chosen value on this slide (`size=` `color=` `fill=` `x y w h` `colors=` `widths=`
     `rowh=` `labels=<pos>`, a slide `sizes:` / `style:` line) or `@defaults` (the agent decided the deck frame
     already serves this slide).
- The facts line reads `design: colors fonts sizes style footer; 9/14 slides decided form+emphasis+values`
  and lists the slides short of a group: `slides 4 (values), 8 (form, emphasis)`.
- Still advisory (warnings never cost a rebuild by themselves), and the eval counts them as `design` not as
  first-pass failures.

## Syntax depth (owner, 2026-10-07): "detailed syntax with secondary attributes, choices without limit"

Every form takes secondary attributes on its own line (`@timeline dir=v marks=year`, `@steps num shape=pentagon`),
every element kind takes the full attribute set (`x y w h size color fill line radius shadow align valign bold
italic font opacity pad rotate shape z`), and the composition vocabulary grows until an agent rarely needs
`@html` for a business slide (DL3b in `docs/TARGETS.md`).

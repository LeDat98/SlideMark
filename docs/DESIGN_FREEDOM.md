# Design freedom (top priority, set by the owner on 2026-10-05)

SlideMark must never limit an agent's design ability. It provides **mechanisms, not looks**: the agent declares
the design, and SlideMark turns it into native, editable PowerPoint. Smart defaults stay, so a deck without any
design input still looks good, but every default must be overridable from the deck source.

## Rules

1. **Nothing visual is hard-coded.** Every color, font, size, spacing, radius, border, shadow, band, card look,
   heading style, table style, chart palette and layout constant (gaps, title height, growth ratios, autofit
   limits) comes from design tokens.
2. **Built-in themes are only presets.** They are plain data files (`src/slidemark/presets/*.yaml`) written in the
   same public token schema an agent can write. There are no theme-specific code paths. Anything one preset can
   do (for example the `jp-business` title band) is a token every deck can use.
3. **Three design paths, all first-class and mixable in one deck:**
   - **Tokens** (cheapest): declare the design system in a few header lines.
   - **CSS**: style any SlideMark element with CSS selectors.
   - **HTML**: write a region, a slide or the whole deck in HTML/CSS. Chromium lays it out and SlideMark
     converts it to native shapes.
4. **The explicit wins.** An `@` grid, `{x y w h}`, a CSS rule or an HTML layout always overrides automatic layout.
   `@free` gives a slide absolute positioning with no automatic arrangement.
5. **Lint judges readability, not taste.** `check` and `review` flag only objective problems: overflow, overlap,
   off-slide, contrast, minimum text size and missing alt text. They never penalize custom colors, fonts or
   unusual layouts.
6. **Token cost still matters.** Each design path gets its shortest unambiguous form, measured in the bench.

## Path 1: tokens

```markdown
theme: none                      # no preset; or a preset name to extend, or ./brand.yaml
colors: bg=#0B1020 fg=#E6E8EF primary=#7C5CFF accent=#00D1B2 muted=#8A90A6
fonts: heading="Inter" body="Noto Sans JP" mono="JetBrains Mono"
sizes: title=40 body=16 caption=11
style: radius=14 gap=20 card.fill=#141A2E card.shadow="0 8 24 #00000055" title.band=none
```

- Any token from the schema can be set inline. Unknown keys produce a did-you-mean hint.
- `theme: jp-business` plus overriding lines extends a preset.
- `slidemark tokens` prints the full schema with defaults.

## Path 2: CSS

A ` ```css ` fence styles SlideMark elements. Put it in the deck header area to apply it to the whole deck, or
inside a slide to apply it to that slide only. Selectors follow the IR:

| Selector | Targets |
|---|---|
| `slide`, `slide.cover`, `slide.section` | slides |
| `h1` | slide titles |
| `.lead`, `.conclusion`, `.footnote` | slide parts |
| `.box`, `.box > h2` | boxes and their headings |
| `.kpi`, `.chevron` | components |
| `table`, `th`, `td`, `tr:nth-child(even)` | tables |
| `.chart`, `code` | charts, code |
| `.hero`, `#a` | any custom class or id written with `{.hero}` / `{#a}` |

Required native mappings:

| Group | CSS properties |
|---|---|
| Color and fill | `color`, `background` (solid / `linear-gradient` / `radial-gradient` / image) |
| Border | `border*` per side, `border-radius` |
| Effects | `box-shadow`, `opacity` |
| Font | `font-family`, `font-size`, `font-weight`, `font-style` |
| Text | `letter-spacing`, `line-height`, `text-align`, `text-transform`, `text-decoration` |
| Box | `padding`, `margin`, `gap` |
| Grid | `grid-template-columns`, `grid-template-areas` |
| Transform | `transform: rotate()` |

Anything that cannot be mapped produces a one-line diagnostic and is never silently dropped.

## Path 3: HTML

- ` ```html ` fence for a region. `@html` turns a whole slide into HTML. `slidemark build deck.html` builds a
  deck with one `<section>` per slide and a shared `<style>`.
- Native conversion must cover:
  - gradients;
  - shadows;
  - rounded and per-side borders;
  - rotation;
  - opacity;
  - web fonts (by family name);
  - absolute positioning, flex and grid;
  - inline SVG (`path`, `rect`, `circle`, `line`, `polygon` become native freeform `custGeom`);
  - icons;
  - tables, lists and text runs.
- Only what PowerPoint truly cannot draw falls back to an image, with a diagnostic naming the element.
- HTML slides and SlideMark slides in one deck share the same tokens (CSS custom properties `--primary` ...).

## Gates (mirrored in `docs/TARGETS.md` as DF1–DF6)

- **DF1 No hard-coded design.**
  - A test fails on color literals or fixed pt sizes in `layout/` and `render/` outside the token defaults.
  - Presets are YAML data.
  - `theme: none` is driven only by declared tokens.
- **DF2 Inline tokens.**
  - Every `Theme` field is settable from header lines, a theme file, or a preset with overrides.
  - `slidemark tokens` prints the schema.
  - SKILL.md documents it within its budget.
- **DF3 CSS fence.**
  - The selectors above are supported.
  - The 30 CSS properties from the table are mapped natively, each with a test.
  - Unmapped properties produce diagnostics.
- **DF4 HTML fidelity.**
  - Corpus: at least 30 agent-designed HTML slides (gradient heroes, dashboards, timelines, dense JP, SVG
    diagrams).
  - At least 90% of visible elements become native and editable.
  - Mean perceptual diff between the Chromium render and the pptx render stays under a recorded threshold that
    only goes down.
- **DF5 Whole-deck HTML and mixed decks.** `build deck.html`, `@html` slides, shared tokens, and a round trip
  through `import`.
- **DF6 Design-freedom eval.**
  - 20 brand-brief tasks (Sonnet, SKILL.md only).
  - At least 90% of decks are check-clean first pass.
  - Decks follow their own brief: no two share a palette unless the brief says so.
  - The run's orchestrator reviews the images.

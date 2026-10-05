# SlideMark syntax reference

**Deck header** (`key: value` lines before the first `#`; YAML front-matter also accepted):
`theme`, `size` (`16:9` `4:3` `A4` `16:10` `10inx7.5in`), `lang`, `title`, `author`, `footer`, `num: on`,
`density: dense`.

**Slides.** `# Title` starts a slide; `---` starts an untitled slide; `#` inside code fences is safe.
Cover/section slides are inferred (title + ≤ 2 short lines). `??? ` starts speaker notes.

**Blocks.** `## Heading` + content = a box. Text/lists outside boxes = a text block. Each image, chart, table,
code fence outside a box = its own block. Fixed places: `>` after the title = lead, `>` at the end = conclusion,
`※ x` or `^ x` = footnote; any other `>` = quote. `@end` closes a box. `### Heading` inside a box is a
sub-heading, or a nested box when the box has its own `@` line.

**Automatic arrangement:** 1 block full width, 2 → 2 columns, 3 → 3 columns, 4 → 2×2 (or 4 columns if
short), 5–6 → 3×2, text + one visual → text left, visual right.

**`@` tokens** (space separated, anywhere in the slide):

| Token | Example |
|---|---|
| N columns | `@3` |
| C×R grid | `@2x2` |
| ratios | `@1:2`, `@3:6:3` |
| areas (`.` = empty, repeat to span) | `@aab/aac`, `@.a./bcd` |
| flags | `flow`, `chevron` |
| connectors | `a>b`, `a-b`, `1>3` |
| slide type | `cover` `section` `blank` `center` |
| settings | `bg=#0F172A`, `bg=photo.jpg`, `t=fade`, `id=intro`, `gap=8pt` |
| other words | classes: `dense`, `dark`, … |

**Attributes** `{.class #id key=value key="two words"}`: end of a heading, end of an image, or alone on the line
before a block. Keys: `x y w h` (`%`, `in`, `cm`, `mm`, `pt`, `px`; bare = pt), `size`, `color`, `fill`, `line`,
`align`, `valign`, `bold`, `radius`, `pad`, `fit`. Classes: `.primary .accent .danger .success .muted`
(colors), `.plain` (box without card), `.kpi`, `.zebra` (tables), `.badge` (inline).

**Inline:** `**b**` `*i*` `~~s~~` `` `code` `` `==accent==` `[x]{.danger}` `[x]{.badge}` `H~2~O` `x^2^`
`[t](url)` `[t](#5)`. Lists: `-` and `1.`, nest with two spaces.

# Diagnostics

`slidemark check deck.md` prints one line per problem: `level slide N Lline rule: message -> hint`.
`--format json` prints a JSON array of `{level, message, line, slide, rule, hint}`. Exit code 1 only on errors.

| Rule | Meaning | Fix |
|---|---|---|
| `overflow` | text does not fit even at the minimum font size | shorten, split the slide, give the block more room |
| `off-slide` | an item extends past the slide edge | remove `{x y w h}` |
| `overlap` | two blocks collide | remove explicit positions, use an `@` grid |
| `contrast` | text color too close to its fill (< 3:1) | change `color`/`fill` |
| `tiny-text` | text renders below the theme minimum | shorten text or split |
| `alt` | image without alt text | `![what it shows](a.png)` |
| `missing-end` | last box holds a table/chart/callout its siblings do not | add `@end` before it |
| `bad-grid`, `unknown-token` | unreadable `@` token | follow the hint (did-you-mean) |
| `bad-link` | connector letter outside the blocks | letters count blocks in order |
| `connector-crosses` | a connector runs through another block | link neighbours, reorder blocks, or use mermaid |
| `duplicate-link` (info) | `a>b` repeats a `flow` arrow | drop it |
| `mermaid-unsupported`, `html-fallback` (info) | not converted to native shapes | use a flowchart / the HTML subset |
| `html-native-overflow` | measured ```html is bigger than its block | shorten it or give the block more room |
| `bad-theme`, `bad-json` | theme file or JSON deck unreadable | fix the path / field named in the message |
| `bad-chart-option`, `bad-table-option`, `bad-number` | invalid option or CSV value | use the listed values |
| `unknown-attr` | misspelled `{key=}` | follow the did-you-mean hint |
| `dropped-content` | a chevron/flow box could not show some content | move it out of the box |
| `marp-syntax`, `slidev-syntax` | another tool's syntax was converted | use the native form from the hint |

Fix only the named slide and line, then run `check` again.

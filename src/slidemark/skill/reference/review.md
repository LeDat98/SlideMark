# review --fix

`slidemark review deck.md --fix [-o out.md] [--png DIR]` loops build, lint + critique, source edit, rebuild (max 3
rounds; an edit stays only if it helps) and prints `score: 77 -> 97/100`. `-o` keeps the input untouched.
Text is moved, never rewritten.

| Problem | Edit |
|---|---|
| everything `check --fix` handles | same fixes |
| overflow, wall of text, > 4 boxes with a box of > 6 bullets, table > 8 rows | `dense` on the `@` line if that clears it, else split into `Title (1/2)`, `(2/2)` at a box / list item / table row (header and box heading repeated; lead stays first, `>` conclusion and `※` last) |
| `contrast` on a color you declared (`{color=}`, `fill=`, css `color:`) | the theme's dark or light ink |
| `long-title` | title tail moves to the front of the `>` lead |
| `--png`: `pixel-contrast` (text vs rendered pixels, gradient / picture backgrounds) | declared text color swapped; undeclared ones are only reported |

Left alone (layout owns them): `empty-band`, `sparse-box`, `unbalanced`, undeclared colors. Exit code is 0.
Write dense content short up front: a split costs the reader a slide.

# Lessons learned

One line per item: `[area] problem → fix`. Newest at the bottom. Read before starting work.

- [parser] In CommonMark `text\n---` is a setext heading, not a separator → split slides on `---` lines (outside code fences) **before** running markdown-it.
- [ir] A pydantic field named `list` shadows the builtin inside the class body and breaks later `list[...]` annotations → the paragraph field is `marker`.
- [build] hatchling refuses an editable install when `readme` points to a missing README.md.
- [env] Sandbox fonts: Liberation (metric-compatible with Arial/Times/Courier), DejaVu, IPAGothic (Japanese), WenQuanYi. No Calibri/Meiryo/Yu Gothic → LibreOffice previews substitute them; measure CJK as ~1em per full-width char.
- [bench] `ruff check --fix` silently rewrote a bench corpus file (removed an unused import, 528 → 518 tokens) → `bench/corpus` is excluded from ruff; corpus files are data, never auto-format them.
- [syntax] Own syntax v1 replaced Slidev-style `---` + YAML + `:::` (2026-10-04): headings carry structure, an `@` grid line replaces containers. Bench: q3 deck 155 tokens (30% of python-pptx), dense JP deck 482 vs HTML 828.
- [env] Sandbox ships only libreoffice-core: `soffice` fails with "source file could not be loaded" for .pptx → `apt-get install -y libreoffice-impress` first (routine setup).
- [parser] `>`/`|` right under a list or paragraph are swallowed by markdown-it lazy continuation → the line scanner flushes the text block before them.
- [parser] An unclosed code fence swallows every later slide → escape the fence line and warn.
- [parser] PyYAML turns `16:9` and `num: on` into int/bool → front-matter loader keeps every scalar a string; markdown-it needs `code`, `lheading`, `reference` rules off and `html=False`.
- [render] python-pptx autoshapes carry `p:style` and LibreOffice draws a shadow → remove `p:style`, set fill/line explicitly.
- [render] Children of `a:rPr`/`a:tcPr` must follow schema order (highlight, latin, ea, hlinkClick, borders) or PowerPoint asks to repair → use ordered inserts.
- [render] python-pptx has no data labels for XY series, and `XY_SCATTER` renders as lines unless series line is no-fill.
- [layout] Parser emits rectangular tables (covered cells = empty placeholders) while hand-built IR may omit them → `table_grid` handles both.
- [parser] Content after the last `##` of a slide is a child of that box (a table after chevron boxes vanishes) → needs an explicit box terminator (day 2).
- [layout] Kinsoku: push the previous char down instead of hanging punctuation, and write `hangingPunct="0"` so measurement matches the render.
- [layout] Footnotes were not autofitted and could eat the body → capped at 20% of slide height. A chevron shape only carries text → non-text children are placed under it as separate items.
- [render] `.zebra` needs a body-fill/surface blend because the default header fill equals `surface`.
- [parser] A pre-pass that blanks or rewrites lines in place (never deletes) keeps diagnostic line numbers and the fence map valid.
- [tests] Hypothesis tests need a module-level temp dir, not the `tmp_path` fixture.
- [parser] Marp `![w:200]` maps to `{w=200}` = 200 pt, not px (use `w=200px` if fidelity matters).
- [env] Fresh container needs `apt-get install -y libreoffice-impress` before preview/golden tests (did it on day 2).
- [tests] Golden thumbnails: regenerate with `SLIDEMARK_UPDATE_GOLDEN=1 pytest tests/test_golden.py`; token gate in `bench/BASELINE.json`.

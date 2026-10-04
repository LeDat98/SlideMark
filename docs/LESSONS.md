# Lessons learned

One line per item: `[area] problem → fix`. Newest at the bottom. Read before starting work.

- [parser] In CommonMark `text\n---` is a setext heading, not a separator → split slides on `---` lines (outside code fences) **before** running markdown-it.
- [ir] A pydantic field named `list` shadows the builtin inside the class body and breaks later `list[...]` annotations → the paragraph field is `marker`.
- [build] hatchling refuses an editable install when `readme` points to a missing README.md.
- [env] Sandbox fonts: Liberation (metric-compatible with Arial/Times/Courier), DejaVu, IPAGothic (Japanese), WenQuanYi. No Calibri/Meiryo/Yu Gothic → LibreOffice previews substitute them; measure CJK as ~1em per full-width char.
- [bench] `ruff check --fix` silently rewrote a bench corpus file (removed an unused import, 528 → 518 tokens) → `bench/corpus` is excluded from ruff; corpus files are data, never auto-format them.
- [syntax] Own syntax v1 replaced Slidev-style `---` + YAML + `:::` (2026-10-04): headings carry structure, an `@` grid line replaces containers. Bench: q3 deck 155 tokens (30% of python-pptx), dense JP deck 482 vs HTML 828.
- [env] Sandbox ships only libreoffice-core: `soffice` fails with "source file could not be loaded" for .pptx → `apt-get install -y libreoffice-impress` first (routine setup).

# Lessons learned

One line per item: `[area] problem → fix`. Newest at the bottom. Read before starting work.

- [parser] In CommonMark `text\n---` is a setext heading, not a separator → split slides on `---` lines (outside code fences) **before** running markdown-it.
- [ir] A pydantic field named `list` shadows the builtin inside the class body and breaks later `list[...]` annotations → the paragraph field is `marker`.
- [build] hatchling refuses an editable install when `readme` points to a missing README.md.
- [env] Sandbox fonts: Liberation (metric-compatible with Arial/Times/Courier), DejaVu, IPAGothic (Japanese), WenQuanYi. No Calibri/Meiryo/Yu Gothic → LibreOffice previews substitute them; measure CJK as ~1em per full-width char.

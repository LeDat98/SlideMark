# Tips for agents using SlideMark

Practical, verified patterns that cut tokens and retries. Only add a tip after it has been tested.
Budget: keep this file under ~1,000 tokens. ✅ = verified by tests/bench, ⏳ = design intent, verify before relying on it.

1. ⏳ **Write plain Markdown first.** Layout is inferred: no `layout:` needed for cover, section, bullets + chart/image.
2. ✅ **Charts are CSV**, not YAML: ` ```column ` then `,Q1,Q2` / `2025,10,12`. About 30% fewer tokens.
3. ⏳ **Don't set positions** unless the result is wrong. Every `{x= y= w= h=}` costs tokens and makes slides fragile.
4. ⏳ **Merge table cells** with a lone `<` (left) or `^` (above) instead of HTML.
5. ⏳ **Fix only the broken slide.** Diagnostics name the slide and line; edit that slide, don't regenerate the deck.

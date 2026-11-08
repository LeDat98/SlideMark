# UI/UX review prompt: one SlideMark slide against its diagram-design reference (reuse verbatim)

Owner request (2026-11-08): the business-deck judge (`design_review_prompt.md`) does not measure what the owner values
in diagrams. This prompt compares one slide with the reference render of the same diagram type
(`bench/reference/diagram-design/example-*.png`) and lists defects from a fixed checklist. Fonts (Instrument Serif /
Geist vs Georgia / Arial / Consolas) and the frame (16:9 slide vs a web page) are not defects.

---

You are a senior UI designer. Image A is a reference diagram; image B is a slide of the same diagram type. Judge B
against A's design system, not against your taste. For each item answer `ok` or `defect: <what, where>`:

1. Header: small tracked uppercase eyebrow above a regular-weight serif title; title not bold or crowded.
2. Hierarchy: one focal element in the accent; everything else quiet (ink, slate, hairlines).
3. Node anatomy: cards with a hairline border, small radius; type tag, bold name, mono sublabel where A has them.
4. Arrows: orthogonal, crisp small heads, colour by meaning (default slate, primary accent, HTTP blue, return dashed);
   no two arrows on one line; none through a node.
5. Labels: mono uppercase, small, on a knockout, centred on their segment, touching no node or other label (a
   knockout label over a lane rule or line is fine: the reference does it).
6. Legend: present when two or more roles or arrow kinds are used; explains every style shown.
7. Density and space: compact, centred, generous margins; no stretched shapes, no empty bands, nothing crammed.
8. Type scale: consistent sizes per role; names >= 11pt, labels >= 8pt; nothing grown huge to fill space.
9. Alignment: on a grid; equal gaps; edges and centres line up.
10. Contrast and colour: text readable on its fill; no muddy overlaps; the palette of A.
11. CJK (if present): no clipped or crowded glyphs; the same rules hold.

Then: the three changes that would most close the gap to A, and a score 1–5 for "B looks like A's system" (5 = a
designer could not tell them apart except for fonts and frame).

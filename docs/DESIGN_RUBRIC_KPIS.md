# Design rubric: KPI catalogue

Generated from `bench/rubric/general.yaml` and `bench/rubric/topics.yaml` by `bench/rubric/render.py`; edit the
YAML, then re-run the script. Method, formula and protocol: `docs/DESIGN_RUBRIC.md`.

Every KPI is scored 1 to 5. Levels 1-2 describe the bad signs, 4-5 the good ones, 3 is acceptable. Weight 1 (nice
to have) to 5 (critical). A **gate** KPI below level 3 caps the slide (level 2: at most 59, level 1: at most 39).

## General KPIs (every slide)

| id | name | weight | gate |
|---|---|---|---|
| G-01 | One message, true to content | 5 | yes |
| G-02 | Form fits content | 4 |  |
| G-03 | Hierarchy and focal point | 5 |  |
| G-04 | Grid, alignment and grouping | 4 |  |
| G-05 | White space and density | 4 |  |
| G-06 | Type scale, size floor and CJK | 5 | yes |
| G-07 | Text economy | 3 |  |
| G-08 | Colour purpose and coherence | 3 |  |
| G-09 | Contrast and non-text contrast | 5 | yes |
| G-10 | Emphasis discipline | 3 |  |
| G-11 | Glance test and legibility at distance | 4 |  |
| G-12 | Fidelity and polish | 5 | yes |
| G-13 | Deliberate, coherent choices | 3 |  |
| G-14 | Accessible structure (pptx) | 2 |  |

#### G-01 One message, true to content  (weight 5, **gate**)

Does the slide carry one clear message that its content supports and that matches what the slide is for?

| Level | What the grader sees |
|---|---|
| 1 | Fails: the message cannot be stated, or the visuals contradict or misstate the content (title says growth, chart falls; total does not match its parts; a label sits on the wrong item). |
| 2 | Weak: two or three messages compete, or the title is a topic label and the point must be inferred from the body; at least one claim is not backed by anything shown. |
| 3 | Acceptable: one message can be stated after reading title and body, but the title is a topic or a mixed message; everything shown is true and relevant. |
| 4 | Strong: the title states the takeaway as a sentence; all elements support it; at most one element is off-message. |
| 5 | Excellent: a complete action title; every element serves it; the proof is visible on the slide; nothing needed is missing and nothing extra is present. |

Good signals: Title is a full sentence that states the takeaway (a claim, not a topic); Every element on the slide supports that claim; the evidence for it is visible on the slide; A reader can state the message in one sentence after one look; Numbers, labels and the title agree with each other

Bad signals: Title is a label such as 'Overview' or 'Results'; Two or more competing messages of equal weight; Chart or table shows something the title does not say, or the opposite of it; Elements included only because the content existed (filler, decoration with no meaning)

Checks: Judge writes the message in one sentence from the image alone, then compares it with the brief's intended message (protocol, step 2); Title length: a sentence of roughly 1-2 lines, not a paragraph (heuristic); Cross-check every number in the title against the chart or table on the slide

Sources: Barbara Minto, The Pyramid Principle (1987): one governing thought, slide title as the top of a small pyramid (checked only through secondary summaries, e.g. https://www.think-cell.com/en/resources/content-hub/using-the-pyramid-principle-to-build-better-powerpoint-presentations; primary text unverified); Cole Nussbaumer Knaflic, Storytelling with Data (2015), action titles; O'Reilly TOC https://oreilly.com/library/view/storytelling-with-data/9781119002253 (chapter-level only; paraphrase); Duarte Glance Test: single message as the first test of a slide, https://www.duarte.com/resources/guides-tools/the-glance-test/ (verified existence and 3-second framing via search); Japanese consulting slide guides: one slide, one message, conclusion first (no specific title verified; unverified)

#### G-02 Form fits content  (weight 4, -)

Is the chosen form (figure, table, steps, chart, cards, prose, diagram) the one this kind of content reads best in?

| Level | What the grader sees |
|---|---|
| 1 | Fails: the form misrepresents the content (pie for a trend, sizes not proportional to values, an ordered process shown as an unordered list). |
| 2 | Weak: a generic form (bullets, equal cards) hides structure the content has; the reader must rebuild order, grouping or comparison in their head. |
| 3 | Acceptable: the form works and is readable but is a default; structure is present in the text yet not made visible. |
| 4 | Strong: the form matches the content type and the structure (order, group, comparison axis) can be seen at a glance. |
| 5 | Excellent: the form makes the relation or the difference obvious in one look; a different form would be worse; the form changes where the content changes. |

Good signals: One number that matters is shown big, not in a sentence; Comparison is side by side on a shared axis or in a table with aligned columns; Sequence shows order and direction; parts of a whole show proportion; Structure of the content (order, grouping, hierarchy) is visible without reading

Bad signals: Bullets used for a process, a comparison or a hierarchy; Pie or 3D chart for a time series; area or size that does not match the data; Cards in a grid with no reason for their arrangement; Diagram where a table would be quicker, or a table where one number is the point

Checks: Name the content type (number, comparison, sequence, trend, part-of-whole, list, argument, structure) and the form used; they must be a known good pair; Visual size (bar length, area, angle) is proportional to the value shown; Topic KPIs refine this per slide topic; the topic set must not double count this KPI

Sources: Cole Nussbaumer Knaflic, Storytelling with Data (2015): choose an appropriate visual (lesson list confirmed via secondary summaries, https://oreilly.com/library/view/storytelling-with-data/9781119002253); Edward Tufte, The Visual Display of Quantitative Information (1983): graphical integrity, proportion of visual size to data (not re-checked this session; unverified)

#### G-03 Hierarchy and focal point  (weight 5, -)

Is there one clear entry point and a visible reading order built from scale, contrast and position?

| Level | What the grader sees |
|---|---|
| 1 | Fails: no entry point; all elements are equal, or a decorative element dominates the content. |
| 2 | Weak: a focal point exists but is weak or competes with one or two others; levels two and three are indistinguishable. |
| 3 | Acceptable: the title is clearly first and the body reads in a sensible order, but the key content does not stand out from supporting content. |
| 4 | Strong: one focal element, then a clear second level; reading order is obvious; supporting detail recedes. |
| 5 | Excellent: the eye lands on the key element within a second, travels the rest in the intended order, and the hierarchy would survive in greyscale. |

Good signals: One element wins the first look (biggest, darkest or most saturated); Two or three clear levels: title, key content, supporting detail; Order of reading follows position (top-left to bottom-right, or a stated axis); Hierarchy comes from size, weight and space before extra boxes or colours

Bad signals: Everything the same size and weight; the eye does not know where to start; Several focal points of equal strength; Title smaller or quieter than decoration; Hierarchy created only by colour or boxes while type sizes are all equal

Checks: Squint or blur the image: the focal element must still be identifiable; Size ratio between adjacent levels >= about 1.25 (type scale, see G-06); Count of focal elements = 1 (a deliberate pair such as before/after counts as one)

Sources: Nancy Duarte, slide:ology (2008): visual hierarchy and signal to noise (book contents not re-checked; unverified); Ellen Lupton, Thinking with Type (2004; 3rd ed. 2024): hierarchy through scale and weight (unverified); Cole Nussbaumer Knaflic, Storytelling with Data (2015): focus attention with preattentive attributes (secondary summaries only)

#### G-04 Grid, alignment and grouping  (weight 4, -)

Are elements on a visible grid, aligned, evenly spaced, and grouped by proximity so that related things sit together?

| Level | What the grader sees |
|---|---|
| 1 | Fails: no grid; elements scattered; labels or items attach to the wrong neighbour. |
| 2 | Weak: a rough structure, but several near-miss alignments, uneven gaps or inconsistent margins are visible at a glance. |
| 3 | Acceptable: major blocks align and margins are even; small gaps or sizes vary without reason; grouping is mostly clear. |
| 4 | Strong: elements sit on one grid; gaps are equal; grouping by proximity is clear; at most one minor misalignment. |
| 5 | Excellent: a visible, consistent grid; every edge and centre lines up; spacing rhythm is regular; proximity alone shows the grouping. |

Good signals: Few distinct left edges and tops; columns and rows share them; Equal gaps between like elements; inside-group gap smaller than between-group gap; Margins equal on both sides; same title position as other slides; Related items are close together; unrelated items are visibly apart

Bad signals: Edges that nearly line up but differ by a few pixels; Unequal gaps, cards of uneven size without meaning; Labels nearer to the wrong object than to their own; Content centred in some places and left aligned in others

Checks: Distinct left-edge x values among body blocks <= 3-4 (heuristic); Gap tolerance: equal gaps within 1% of slide width; Title anchor and margins identical to the deck's other slides (deck D-02)

Sources: Josef Müller-Brockmann, Grid Systems in Graphic Design (1981): the grid as a framework for order (publisher listing only, e.g. https://www.slanted.de/?p=792761; content paraphrased, unverified); Robin Williams, The Non-Designer's Design Book: alignment and proximity (search found no page; unverified)

#### G-05 White space and density  (weight 4, -)

Is the amount of content per area right for this slide's purpose and audience, with space used as a choice?

| Level | What the grader sees |
|---|---|
| 1 | Fails: unusably crammed (elements touch or overlap, no margin) or nearly empty with the content lost in space. |
| 2 | Weak: clearly crowded in one zone or clearly leaving a large area dead; space looks left over, not chosen. |
| 3 | Acceptable: no area is cramped or empty enough to hurt reading; the balance is neutral and space looks like a by-product. |
| 4 | Strong: margins and gaps are even and generous enough for the density; the content block is balanced; density suits the purpose. |
| 5 | Excellent: space is used as a design element (separates groups, isolates the focal point); a dense slide stays easy to scan, a sparse slide feels intentional. |

Good signals: Margins and gaps are visible and consistent; the content block is balanced on the slide; Dense slide: dense on purpose, with structure (grid, rules, tables) that makes density readable; Sparse slide: sparse on purpose, one thing carried by the space

Bad signals: Cramped: text or boxes nearly touching edges or each other; A small block floating in a large empty area; a dead band of empty space; Shapes stretched to fill space; text enlarged only to fill space; Same density everywhere with no pause

Checks: Outer margin >= about 4% of slide width on every side (heuristic); No empty band wider than about 25% of slide height or width unless it is the design (heuristic); Dense JA business slides are judged against the dense standard: density is allowed if G-04 and G-06 hold

Sources: Garr Reynolds, Presentation Zen (2008): simplicity, restraint, signal to noise (book contents not re-checked; unverified); Cole Nussbaumer Knaflic, Storytelling with Data (2015): declutter, alignment and white space (TOC verified via https://www.oreilly.com/library/view/storytelling-with-data/9781119002253/c08.xhtml for chapter naming only)

#### G-06 Type scale, size floor and CJK  (weight 5, **gate**)

Is type a small consistent scale, large enough for its job, with correct line breaks and CJK handling?

| Level | What the grader sees |
|---|---|
| 1 | Fails: body text is below the floor (under 10 pt for dense JA business, under 12 pt for other body text) or is unreadable at full size; glyphs missing or garbled (tofu boxes). |
| 2 | Weak: body meets the floor only barely; sizes are inconsistent per role or too many; headings break awkwardly; CJK lines crowded or wrongly broken. |
| 3 | Acceptable: body at or above the floor; sizes consistent per role; at most 5 sizes; line breaks fine apart from one or two awkward places. |
| 4 | Strong: a clear scale of 3-4 sizes with ratio >= 1.25 between levels; body comfortably above the floor; breaks clean; CJK text sized and spaced correctly. |
| 5 | Excellent: a deliberate type scale the whole slide obeys; each size has one role; reading is effortless at full size; CJK and Latin sit together with matched weight and baseline. |

Good signals: Two to four sizes, each used for one role; Body at or above the size floor; footnotes and sources at or above the footnote floor; Sensible line length and leading; no one-word last lines (orphans) in headings; CJK: a CJK-capable font is set for East Asian text; full-width glyphs not clipped; breaks fall at word or phrase boundaries; no punctuation starting a line

Bad signals: Many near-equal sizes (11, 12, 13, 14 pt) with no role; Text below the floor to fit more in; Text auto-shrunk so sizes differ between boxes of the same role; Mid-word breaks in Latin text, CJK lines broken in the middle of a word or number+unit

Checks: Floors (SlideMark heuristic, not from a single source): body >= 14 pt for presentation use; dense JA business >= 10 pt (target 10-12 pt); footnotes, sources and chart labels >= 8 pt; Distinct font sizes on the slide <= 5; adjacent role ratio >= 1.25; Gate fails when any body text is below the floor for its slide class, measured from the pptx where possible; No text in a different size than its sibling boxes without a role reason

Sources: Ellen Lupton, Thinking with Type (2004; 3rd ed. 2024): type scale, leading, line length (unverified); Microsoft, Make your PowerPoint presentations accessible: suggests sans-serif fonts of 18 pt or larger for readability, https://support.microsoft.com/en-us/office/make-your-powerpoint-presentations-accessible-to-people-with-disabilities-6f7772b2-2f33-4bd2-8ca7-dae3b2b3ef25 (verified; used as an upper reference, the dense JA floor is an owner decision); WCAG 2.2 SC 1.4.3 treats CJK sizes as equivalent to Latin large-text sizes (verified: https://www.w3.org/WAI/WCAG22/Understanding/contrast-minimum.html); WCAG sets no minimum font size

#### G-07 Text economy  (weight 3, -)

Is every word needed, written as fragments or numbers rather than sentences, with nothing repeated?

| Level | What the grader sees |
|---|---|
| 1 | Fails: the slide is a block of prose or a copied document page; the message is buried in text. |
| 2 | Weak: many full sentences or repeated phrases; about a third of the words could go without loss. |
| 3 | Acceptable: mostly phrases; one or two redundant lines; amount of text fits the stated slide purpose. |
| 4 | Strong: concise phrases; no repetition; every line adds information. |
| 5 | Excellent: minimum words that still carry the message and its proof; wording is precise (numbers, units, names); nothing to cut. |

Good signals: Labels and bullets are short noun or verb phrases; numbers carry units; Each phrase adds information not already in the title or the visual; Detail is moved to a table or note when it is not the message

Bad signals: Full paragraphs on a slide meant to be presented; The title repeated as the first bullet or as a chart title; Filler words, redundant units, repeated axis and legend text; A reading deck forced to presentation brevity, or the reverse, against its stated purpose

Checks: Word or character count against the brief's purpose: presentation slide roughly <= 50 words; reading or leave-behind slide may carry more if structured (heuristic, not a source figure); Title text is not repeated verbatim in a chart title, subtitle or first bullet

Sources: Garr Reynolds, Presentation Zen (2008): signal to noise, restraint (unverified); Nancy Duarte, Glance Test: elements that do not help the message count as noise, https://www.duarte.com/resources/slide-glance-test/ (verified via search)

#### G-08 Colour purpose and coherence  (weight 3, -)

Does colour encode something (group, status, emphasis) with a small coherent palette, rather than decorate?

| Level | What the grader sees |
|---|---|
| 1 | Fails: colour misleads (red for good, same hue for opposite states) or clashes so that parts are hard to tell apart. |
| 2 | Weak: many hues without a role, or accent colour spread over most elements; palette looks unrelated to the rest of the slide. |
| 3 | Acceptable: a coherent palette of neutral plus one or two accents; colour is mostly decorative but not misleading. |
| 4 | Strong: colour marks meaning (group, status, key figure); palette small and consistent; meaning is also given by label or position. |
| 5 | Excellent: colour is spent on exactly what matters; the palette feels chosen for the subject; meaning survives greyscale and colour-blind viewing. |

Good signals: A neutral base with one or two accent hues; accent reserved for what matters; A colour keeps one meaning across the slide (and the deck); Categories separable by more than hue alone (label, shape, position); Palette suits subject and audience

Bad signals: More than about four hues with no meaning each; Rainbow or default chart palette on a slide with its own palette; The same colour meaning two things; a different colour for equal things; Colour is the only carrier of meaning

Checks: Distinct hues (excluding neutrals) <= 4 (heuristic); Greyscale render still separates categories and the focal element (via labels, position, pattern or value); WCAG 1.4.1 use of colour: colour not the only visual means of conveying information (not fetched this session; unverified)

Sources: Robin Williams, The Non-Designer's Design Book: contrast and repetition (unverified); Cole Nussbaumer Knaflic, Storytelling with Data (2015): colour as an attention tool, used sparingly (secondary summaries); Microsoft, accessible PowerPoint guidance: do not use colour as the only way to convey meaning (verified, URL under G-06)

#### G-09 Contrast and non-text contrast  (weight 5, **gate**)

Is all text and every meaningful graphic element clearly separable from what is behind it?

| Level | What the grader sees |
|---|---|
| 1 | Fails: some content text is hard or impossible to read (below about 3:1), or a meaningful mark disappears into the background. |
| 2 | Weak: body text is under 4.5:1 in places, or meaningful graphics are under 3:1; reading is possible but needs effort. |
| 3 | Acceptable: all body text >= 4.5:1; large text and meaningful graphics >= 3:1; secondary text may sit close to the limit. |
| 4 | Strong: body and labels comfortably above the limits (about 7:1 or more for text); graphics clearly separated; text over images has a backing. |
| 5 | Excellent: contrast is used to rank importance (focal element highest) while every element stays above the limits; holds on a projector and in greyscale. |

Good signals: Normal text >= 4.5:1 against its actual background; large text >= 3:1; Chart marks, lines, icons, arrows and borders that carry meaning >= 3:1 against adjacent colours; Text over images has a scrim or solid panel behind it; Dark-on-light or light-on-dark used consistently within the slide

Bad signals: Light grey text, thin pale lines, mid-tone text on mid-tone fills; Text over a photo or gradient with changing background; Key series colour close to the background or to its neighbour; Footnotes and axis labels in the faintest grey

Checks: Text contrast ratio computed from pptx colours: >= 4.5:1 normal, >= 3:1 large (>= 18 pt, or >= 14 pt bold); Graphical objects needed to understand the content >= 3:1 (WCAG 1.4.11); Gate fails when any content text is under 3:1, or any body text under 4.5:1 by measurement

Sources: WCAG 2.2 SC 1.4.3 Contrast (Minimum): 4.5:1 normal text; 3:1 large text (18 pt, or 14 pt bold), https://www.w3.org/WAI/WCAG22/Understanding/contrast-minimum.html (verified); WCAG 2.2 SC 1.4.11 Non-text Contrast: 3:1 for graphical objects and UI components needed to understand the content, https://www.w3.org/WAI/WCAG22/Understanding/non-text-contrast.html (verified)

#### G-10 Emphasis discipline  (weight 3, -)

Is emphasis (bold, colour, size, boxes, icons) spent in few places so that the emphasised item actually stands out?

| Level | What the grader sees |
|---|---|
| 1 | Fails: emphasis is everywhere or on the wrong item, so the real point is the quietest thing on the slide. |
| 2 | Weak: more than a third of the elements are emphasised, or decoration competes with content. |
| 3 | Acceptable: emphasis is moderate and mostly on relevant items; some decoration carries no meaning. |
| 4 | Strong: emphasis is limited to the key items; the rest is quiet; decoration is minimal and mostly meaningful. |
| 5 | Excellent: emphasis is spent exactly once or twice on what matters; every rule, box and icon carries meaning or is removed. |

Good signals: One or two emphasised items; everything else quiet; Emphasis means the same thing wherever it appears; Structure (rules, numbering, cards) carries a meaning such as order, group or status

Bad signals: Bold, colour and boxes on most items; Decoration that encodes nothing (icons, shadows, gradients, accent bars); Underline, bold and colour combined on one phrase; Emphasis on an item that is not the message

Checks: Share of elements that are bold, accent-coloured or boxed <= about 25% (heuristic); Every decorative element can be named with the meaning it encodes; if not, it is noise

Sources: Nancy Duarte, Glance Test: signal-to-noise per slide, https://www.duarte.com/resources/guides-tools/the-glance-test/ (verified existence); Edward Tufte, The Visual Display of Quantitative Information (1983): data-ink and chartjunk (not re-checked; unverified); Cole Nussbaumer Knaflic, Storytelling with Data (2015): declutter and focus attention (secondary summaries)

#### G-11 Glance test and legibility at distance  (weight 4, -)

Can a viewer get the message in about three seconds, and read the key content from the back of a room?

| Level | What the grader sees |
|---|---|
| 1 | Fails: at a glance nothing can be named; at half size the key content is unreadable. |
| 2 | Weak: topic is clear but the point needs reading; the key figure or label is small or thin and disappears at half size. |
| 3 | Acceptable: topic and most of the point are clear in about 5 seconds; key content readable at half size, supporting detail is not. |
| 4 | Strong: the point is clear within about 3 seconds; key content stays readable at half size. |
| 5 | Excellent: the point lands in one look, and the focal element is still clear when the slide is shrunk to a thumbnail; supporting detail is available but not in the way. |

Good signals: Within 3 seconds a viewer can say what the slide is about and its point; Key text and numbers survive a half-size or blurred view; Few distinct visual elements compete for the first look

Bad signals: Needs reading to learn the topic; Key figure small or thin; hairline strokes that vanish when scaled; Many small elements of equal weight

Checks: Render at 50% width: the title and the key figure remain legible; Render a thumbnail (about 320 px wide): the focal element is still identifiable; Judge records the time-to-point estimate: a one-sentence description from a first look; For dense JA business reading decks, use the 'headline and structure' reading: the title plus block headers must give the point

Sources: Nancy Duarte, The Glance Test (3 seconds or less to grasp the main point; signal-to-noise per slide), https://www.duarte.com/resources/guides-tools/the-glance-test/ (verified via search results; scoring details unverified); Duarte, slide:ology (2008) and Resonate (2010): book passages not re-checked; unverified

#### G-12 Fidelity and polish  (weight 5, **gate**)

Is the slide free of rendering defects: overflow, clipping, overlap, broken words, stray artefacts and distortion?

| Level | What the grader sees |
|---|---|
| 1 | Fails: content is cut off or hidden (overflow, clipped text, overlap that hides text or a label), or glyphs are missing. |
| 2 | Weak: a visible defect that does not hide content: a label touching a node, an arrow through a box, an awkward mid-word break, an empty placeholder. |
| 3 | Acceptable: no defect hides or misleads; one or two cosmetic imperfections (slightly unequal padding, a tight label). |
| 4 | Strong: no visible defect at full size; only a hairline imperfection found on close zoom. |
| 5 | Excellent: clean at full size and in zoom; padding inside every box is even; connectors, labels and images are exact. |

Good signals: All text inside its box and the slide; nothing cut at an edge; No overlap between text, shapes, arrows and labels unless intended (such as a label on a knock-out); Arrows connect to shapes at their edges; connectors do not pass through nodes; Images undistorted and sharp; no placeholder text or leftover template shapes

Bad signals: Text overflowing a card or running past the slide edge; Overlapping labels, arrows through boxes, lines crossing text; Missing glyphs, wrong fallback font, words broken mid-word; Stretched images or shapes, blurry raster, leftover empty placeholders

Checks: Render full size (not a contact sheet) and zoom on dense areas; text bounding boxes lie inside their shapes and the slide; Opens in LibreOffice and PowerPoint without repair prompts and with equal layout (SlideMark definition of done); Pairwise shape overlap list from layout is empty except for intended cases; Gate fails when any content is cut, hidden or unreadable because of a rendering defect

Sources: Cole Nussbaumer Knaflic, Storytelling with Data (2015): think like a designer, attend to details (secondary summaries only); SlideMark Definition of Done and bench/ui_review_prompt.md items 4, 5, 7, 11 (arrows, labels, spacing, CJK) for the diagram variants of the same defects

#### G-13 Deliberate, coherent choices  (weight 3, -)

Do the colour, type, shape and layout choices look chosen for this content and hold together as one system, whatever the style?

| Level | What the grader sees |
|---|---|
| 1 | Fails: styles clash so strongly that the slide looks assembled from different sources. |
| 2 | Weak: mostly default choices, with two or more mismatched styles (radius, stroke, icon family). |
| 3 | Acceptable: coherent but generic; nothing mismatched; no sign that the choices were made for this content. |
| 4 | Strong: a recognisable system (type, colour, shape) that suits the subject; at most one stray element. |
| 5 | Excellent: every choice is explainable and consistent, and the style is specific to this subject and audience; style could be named in one phrase. |

Good signals: Choices can be explained from the subject and audience (a stated or evident reason); Corner radius, line weight, stroke, shadow and icon style are one family; Dense or airy, dark or light, plain or bold is a consistent decision, not a mix

Bad signals: A template default that would fit any topic, with no sign of a decision; Mixed styles: rounded and square cards, two icon sets, outlined next to filled; Effects (gradient, shadow) used on some objects only; Style borrowed and half applied

Checks: Count distinct corner radii, stroke widths, shadow styles and icon families; each should be 1 (2 with a reason); No house style is assumed: judge fit and coherence, not taste (design freedom)

Sources: bench/design_review_prompt.md: 'judges whether the choices are deliberate, coherent and serve the content' (repo); Robin Williams, The Non-Designer's Design Book: repetition (unverified); Ellen Lupton, Thinking with Type: consistent typographic systems (unverified)

#### G-14 Accessible structure (pptx)  (weight 2, -)

Does the file give assistive technology a title, alt text for meaningful visuals, a sensible reading order, and meaning that does not rely on colour alone?

| Level | What the grader sees |
|---|---|
| 1 | Fails: no slide title, content visuals without any alt text, and reading order contradicts the visual order. |
| 2 | Weak: titles are missing or duplicated on some slides, or meaningful visuals lack alt text; order is partly wrong. |
| 3 | Acceptable: every slide has a title; most meaningful visuals have alt text; reading order is mostly right. |
| 4 | Strong: unique titles; alt text on all meaningful visuals and decorative ones marked; reading order matches the visual order; tables have headers. |
| 5 | Excellent: as 4, plus alt text that states the takeaway of a chart in a sentence, and meaning that survives without colour. |

Good signals: Every slide has a unique, descriptive title (a real title placeholder or equivalent); Meaningful pictures and charts have alt text; decoration is marked decorative; Reading (z-)order follows the visual order; Tables have a header row and no merged cells where avoidable

Bad signals: No title on a slide, or the same title twice; Charts and diagrams as images without alt text; Reading order is creation order, so the footer is read first; Meaning only by colour; text in images only

Checks: (pptx) title placeholder text present and unique per slide; (pptx) alt text (descr) present on picture, chart and diagram group shapes; decorative flagged; (pptx) shape tree order equals reading order (title, body, footer last); Image-only run: mark N/A; the method renormalizes the weights

Sources: Microsoft, Make your PowerPoint presentations accessible: alt text, slide titles, reading order, contrast, tables, https://support.microsoft.com/en-us/office/make-your-powerpoint-presentations-accessible-to-people-with-disabilities-6f7772b2-2f33-4bd2-8ca7-dae3b2b3ef25 (verified); WCAG 2.2 SC 1.4.3 and 1.4.11 (verified, URLs under G-09)

## Deck KPIs (once per deck)

| id | name | weight | gate |
|---|---|---|---|
| D-01 | Narrative and storyline | 5 |  |
| D-02 | Consistency as one system | 4 |  |
| D-03 | Variety of form | 3 |  |
| D-04 | Pacing and framing slides | 3 |  |
| D-05 | Fit to purpose and audience | 3 |  |

#### D-01 Narrative and storyline  (weight 5, -)

Do the slide titles, read alone in order, tell the argument (answer first, grouped support, clear ending)?

| Level | What the grader sees |
|---|---|
| 1 | Fails: slides are unrelated or contradict one another; no story can be told from the titles. |
| 2 | Weak: mostly topic titles; order follows the data or the work, not an argument; the point appears late or not at all. |
| 3 | Acceptable: a clear start and end; the order is logical; about half the titles are claims; some slides are filler. |
| 4 | Strong: titles read alone give the argument; the answer comes early; supporting slides group logically; few redundant slides. |
| 5 | Excellent: the title list is a complete executive summary; each slide has one role; nothing can be moved or removed without loss; the ending states the ask. |

Good signals: Titles read in sequence form a summary of the deck (the 'title test'); The answer or recommendation comes early; groups of support follow in a clear logic (such as MECE groups); Each slide has a role in the story: context, evidence, decision, next step; There is a clear ending that states the ask or next step

Bad signals: Topic-label titles ('Background', 'Analysis', 'Summary'); Order is by data source or by chronology of work rather than by argument; Slides that could be deleted or swapped with no loss; Conclusion appears only on the last slide, or is absent

Checks: List all titles in order and judge the list alone (title test); Share of action titles (claim sentences) >= about 70% for a business argument deck (heuristic); Slide count fits the content, with no padding slides

Sources: Barbara Minto, The Pyramid Principle (1987), and SCQA framing (secondary summaries verified, e.g. https://managementconsulted.com/the-pyramid-principle/; primary text unverified); Nancy Duarte, Resonate (2010): story structure for presentations (not re-checked; unverified); Cole Nussbaumer Knaflic, Storytelling with Data (2015): storytelling and action titles (secondary summaries); McKinsey/BCG consulting slide practice and Japanese 資料作成 guides: ghost-deck and title-first practice (no specific title verified; unverified)

#### D-02 Consistency as one system  (weight 4, -)

Do recurring parts (title, footer, page number, source line, cards, charts, tables, colour meaning) look and sit the same across the deck?

| Level | What the grader sees |
|---|---|
| 1 | Fails: slides look like they came from different decks (fonts, palette, title position all vary). |
| 2 | Weak: a common palette but several recurring parts differ (title position, table style, chart style, footer). |
| 3 | Acceptable: one palette and one font family; title and footer fixed; some recurring elements vary in minor ways. |
| 4 | Strong: recurring parts are the same; at most two slides deviate and each has a reason. |
| 5 | Excellent: a complete system: type scale, grid, colour roles, chart and table treatment identical; deviations are deliberate and recognisable (cover, divider). |

Good signals: Title, footer and page number at identical positions and sizes; The same kind of element looks the same everywhere (cards, tables, charts); A colour keeps its meaning across slides; Deviations happen on purpose (cover, divider, closing)

Bad signals: Title position or size jumps between slides; Charts of different styles in one deck; tables with different header treatment; Colour meaning changes from slide to slide; Changes between slides that carry no meaning

Checks: Title, page number and footer bounding boxes identical on content slides (tolerance 1% of slide width); Same font families and the same size per role across the deck; Overlay the slides: the title and margin frame coincide

Sources: Robin Williams, The Non-Designer's Design Book: repetition (unverified); Edward Tufte, Envisioning Information / Visual Display: consistent design across a series (unverified); bench/design_review_prompt.md lens 'One system' (repo)

#### D-03 Variety of form  (weight 3, -)

Does the deck use different forms where the content differs, without variety for its own sake?

| Level | What the grader sees |
|---|---|
| 1 | Fails: one layout is used for every slide, whatever the content (all bullets, or all card grids). |
| 2 | Weak: two forms across the deck; runs of four or more slides with the same layout while the content differs. |
| 3 | Acceptable: three or four forms; runs of the same layout of at most three slides; some content squeezed into the default. |
| 4 | Strong: forms follow content types; at most one run of three same-layout slides; there is a visible rhythm. |
| 5 | Excellent: each content type has its right form; rhythm of dense and sparse; repeated layouts occur only for parallel content and are clearly parallel. |

Good signals: A number, a comparison, a sequence, a trend and a list each get a different suitable form; Rhythm of dense and sparse slides; Repetition only where the content repeats (a series of case studies)

Bad signals: Five or more consecutive slides with the same layout (title and bullets); Every content type forced into the same card grid; Variety unrelated to content (random layouts, mixed styles)

Checks: Table: slide number to layout and form; longest run of the same layout; Count of distinct forms used / count of distinct content types present

Sources: bench/design_review_prompt.md ('the deck varies form when the content varies'; variety score used in round 14) (repo); Garr Reynolds, Presentation Zen (2008): avoid monotony (unverified)

#### D-04 Pacing and framing slides  (weight 3, -)

Does the deck pace its density and use framing slides (cover, agenda, section dividers, summary, closing) where they help?

| Level | What the grader sees |
|---|---|
| 1 | Fails: no entry or exit (starts mid-content; ends abruptly), and the density never varies. |
| 2 | Weak: a cover only, or a cover and a generic 'thanks' closing; long runs of equally dense slides; agenda missing in a long deck. |
| 3 | Acceptable: cover and closing present; agenda or dividers where length asks for them; density varies a little. |
| 4 | Strong: framing slides match the structure; dense slides are separated by lighter ones; the closing carries the ask. |
| 5 | Excellent: pacing is designed: framing slides orient the reader, density breathes, the key moments are given room, and the deck is as long as it needs to be. |

Good signals: A cover that states topic, owner, date; a closing that states the ask or next steps; Agenda or dividers present in a deck longer than about 8-10 slides, matching the section structure; Dense slides are separated by lighter slides (a key figure, a divider); Each section opens with its message

Bad signals: No cover or closing, or a closing that is only 'Thank you' when a decision is needed; Agenda that does not match the sections; Long run of maximum-density slides; Dividers on a short deck that add length only

Checks: Framing slide inventory against deck length and section count; Density per slide (word or element count) plotted along the deck: no run of 4+ slides at the top of the range (heuristic)

Sources: Nancy Duarte, Resonate (2010): rhythm between statement and evidence (not re-checked; unverified); Barbara Minto, The Pyramid Principle: introduction and summary framing (secondary summaries only); Japanese consulting deck practice: 目次, 章扉, エグゼクティブサマリー (no specific title verified; unverified)

#### D-05 Fit to purpose and audience  (weight 3, -)

Is the deck's density and register right for how it will be used (presented, read, or both) and for its audience?

| Level | What the grader sees |
|---|---|
| 1 | Fails: the deck's use is obviously wrong for its density (a leave-behind with no detail; a talk deck that can only be read). |
| 2 | Weak: the density suits the purpose for about half of the slides; others are far off. |
| 3 | Acceptable: density suits the purpose for most slides; one or two outliers; register is neutral. |
| 4 | Strong: density and register suit the purpose and the audience throughout; outliers are deliberate. |
| 5 | Excellent: the deck is clearly designed for its use; density, labels, sources and terms all match, and a reader or presenter would not change the format. |

Good signals: Presented decks: sparse, large type; reading decks: structured density with full labels and sources; Density the same kind across the deck (not one presented slide among reading slides); Terms, units and language match the audience (JA business conventions where relevant)

Bad signals: A reading deck that has only one idea per slide and no detail, or a presented deck full of 10 pt tables; Mixed purposes with no pattern; Terminology or format that does not fit the audience

Checks: Brief states: presented / read / both, audience, language; judge compares density per slide to the stated use; Dense JA business reading deck: 10-12 pt body, tables, footnotes and sources are expected, not defects

Sources: Garr Reynolds, Presentation Zen (2008): slideument vs slide (unverified); Japanese 資料作成 guides: distinction between presentation material and reading material (no specific title verified; unverified)

## Topics

| id | name | overlay | KPIs | gates | recognise |
|---|---|---|---|---|---|
| data-chart | Data chart |  | 6 | 2 | A plotted area with axes, bars, lines, wedges or waterfall steps; Series legend or direct series labels; axis ticks or value labels; Title that names a trend or comparison; footnote with unit or source |
| data-table | Data table |  | 5 | 1 | Grid of rows and columns with a header row; Repeated numeric or short-text cells aligned in columns; Row labels in the first column |
| key-numbers | KPI cards / key numbers |  | 5 | 1 | Several large numerals with small labels; Card or tile layout of equal size; Delta text (+14%, -6 min) or arrows near each number |
| process-flow | Process, flow and steps |  | 5 | 1 | Arrows or numbered shapes that imply order; Words like step, phase, flow, procedure, フロー, ステップ; Decision diamonds, lanes with actors, loop arrows |
| system-diagram | System, architecture and concept diagram |  | 5 | 2 | Boxes inside boxes or in tiers, connected by lines; Layer labels (Clients / Services / Data), icons, tech names; Fishbone spine, kanban columns, Venn circles, journey lane with a sentiment line |
| comparison | Comparison and options |  | 5 | 1 | Two to four parallel boxes or columns with equal weight; Repeated headings or criteria rows across columns; vs, before/after, option, recommend, 比較, 案 |
| timeline-roadmap | Timeline and roadmap |  | 5 | 2 | A horizontal time axis with dates, quarters or years; Bars or markers placed along the axis; Words like roadmap, schedule, milestone, ロードマップ, スケジュール, Q1-Q4 |
| hierarchy-org | Hierarchy, org chart and tree |  | 5 | 1 | A top node with branches downward or rightward; Boxes in levels joined by lines; Words like organisation, 体制, committee, tree, structure |
| framing | Framing slides (cover, agenda, section, closing, decision) |  | 4 | 0 | Title and subtitle with no body, or a short numbered list of sections; Words like agenda, next steps, decision, thank you, summary, アジェンダ, ご決議事項; Large whitespace, one message |
| text-message | Text argument / message slide |  | 5 | 0 | Title plus 3-6 bullets or short paragraphs, no diagram or chart; A key message line under the title; Quotation or statement in large type |
| matrix-quadrant | Matrix, quadrant and prioritisation |  | 4 | 2 | Two labelled axes (low-high) with items placed in cells or positions; Four named quadrants or a labelled grid; Words like priority, matrix, 優先度, impact, effort, SWOT |
| dense-ja-business | Dense Japanese business slide (overlay) | yes | 6 | 2 | Japanese body text at 10-12pt with many elements (more than ~8 text blocks); Key message line (リード文) under the title, footnote or source line (注記, 出所) at the bottom; Boxes with headings, arrows, tables and short bullets on one slide |

## Topic: Data chart (`data-chart`)

Native editable charts (column, bar, line, stacked, area, pie, doughnut, waterfall) showing a quantitative relationship, with title, axes, labels, optional footnote.

Frequency: Most common data topic. Briefs: 20 of 108 specs (6 line, 6 column, 2 stacked, 2 pie, 2 doughnut, 2 bar); lengthbench t1-t3: 11 of 45; examples: ~21 chart blocks in 30 decks (column, line, stacked, waterfall, area, bar).

| id | name | weight | gate |
|---|---|---|---|
| T-CHART-01 | Chart type fits the relationship | 5 | yes |
| T-CHART-02 | Honest scale and baseline | 5 | yes |
| T-CHART-03 | Labels read without lookup | 4 |  |
| T-CHART-04 | Emphasis on the message series | 4 |  |
| T-CHART-05 | Chart ink and density | 3 |  |
| T-CHART-06 | Title states the finding | 3 |  |

#### T-CHART-01 Chart type fits the relationship  (weight 5, **gate**)

Is the chart form the right one for the message (time series, ranking, part-to-whole, composition change, deviation)?

| Level | What the grader sees |
|---|---|
| 1 | Form contradicts the message (e.g. pie for a trend, line connecting unrelated categories, 3D effect distorting sizes). |
| 2 | Form works but is a clumsy choice: pie with 7+ slices, stacked chart where the key series floats in the middle, categories unordered. |
| 3 | Form is conventional for the message; the comparison can be read, with some effort (e.g. unsorted bars, stacked chart with 4+ segments). |
| 4 | Form fits; categories are ordered logically or sorted by value; at most one minor friction (legend lookup, 5 slices). |
| 5 | Form is the simplest that shows the message; ordering supports the title's claim; a pie or stack is used only where part-to-whole is the point. |

Good signals: Line or column for change over time; sorted bars for ranking; stacked or waterfall only when the parts and total both matter; Pie or doughnut has few slices (about 5 or fewer) and shows one whole

Bad signals: Pie with many slices or similar-sized slices; Line used for unordered categories, or bars used for a long continuous series; 3D, radar or dual-axis form that hides the comparison; Stacked bars where the reader must compare middle segments

Checks: Time on x axis implies line or column, not pie; Pie or doughnut slices <= 5-6; Bar categories sorted by value unless a natural order exists (months, age bands); No 3D chart

Sources: Gene Zelazny, Say It with Charts: chart choice follows five relationships (component, item, time series, frequency distribution, correlation); https://www.oreilly.com/library/view/the-say-it/9780071474702/ch01.html (chapter listing checked; pairings of relationship to chart not fully checked); Cole Nussbaumer Knaflic, Storytelling with Data (2015): advice to avoid pie, doughnut and 3D charts, sort bars; read via summaries only, unverified in the book; Alberto Cairo, The Truthful Art (2016): 'functional' quality = form suited to the task (the five-quality list is in The Truthful Art, not The Functional Art); https://thedataschool.co.uk/laura-brylka/the-five-qualities-of-great-vizualizations-according-to-alberto-cairo

#### T-CHART-02 Honest scale and baseline  (weight 5, **gate**)

Do axes and baselines show the data without exaggerating differences?

| Level | What the grader sees |
|---|---|
| 1 | Bars start above zero or axis is cut with no sign, so a small difference looks large; or dual axes imply a false link. |
| 2 | Line axis is non-zero with no cue, or two paired charts use different scales silently; bars are fine. |
| 3 | All bars start at zero; line axes are sensible but a non-zero start is not flagged, or the range is loose (large empty band). |
| 4 | Bars at zero; any non-zero line axis is flagged by a label or axis break; paired charts share one scale. |
| 5 | All of level 4, and the range is chosen so the title's claim is visible without distortion; units on the axis or title. |

Good signals: Bar or column axis starts at zero; A non-zero line axis is visibly marked as such; Same scale across charts that are compared; Axis range tight enough to use the space, not so tight that noise looks like a trend

Bad signals: Truncated bar axis; Different y ranges on side-by-side charts with no note; Broken or dual axes without labels; Area or bubble size scaled by diameter

Checks: Bar/column value axis minimum == 0 (read from chart XML c:min or visible tick); If min > 0 on a line chart, a note or label says so; Paired charts share axis max/min; No secondary axis unless both axes are labelled with units

Sources: Stephen Few, Show Me the Numbers: bar graphs should generally start at zero, line graphs may not (page 169 reported by secondary sources; unverified in the book); https://www.perceptualedge.com; ONS Digital blog, 'Does the axis have to start at zero? Part 2 - bar charts': bar charts should include zero; https://digitalblog.ons.gov.uk/2016/07/23/does-the-axis-have-to-start-at-zero-part-2-bar-charts (opened); Storytelling with Data blog, 'bar charts must have a zero baseline': https://www.storytellingwithdata.com/blog/2012/09/bar-charts-must-have-zero-baseline (opened); Edward Tufte, The Visual Display of Quantitative Information (1983), lie factor = effect shown / effect in data, ideal 1; read via course notes https://faculty.cc.gatech.edu/~stasko/4460/Notes/tufte.pdf (secondary)

#### T-CHART-03 Labels read without lookup  (weight 4, -)

Can the reader identify each series, unit and key value without hunting for a legend or decoding a colour key?

| Level | What the grader sees |
|---|---|
| 1 | Series cannot be identified (no legend, no labels) or unit is missing and cannot be inferred. |
| 2 | Legend is the only key and colours are hard to tell apart, or every point is labelled and the data is cluttered; unit given only in small print. |
| 3 | Legend present and usable; unit stated; category labels horizontal and complete. |
| 4 | Series named at the data or the legend is adjacent and ordered like the data; unit in title or axis; labels only where they help. |
| 5 | Direct labels for all series, value labels on the focal points only, unit once, no legend, no rotated text. |

Good signals: Series named directly at the line end or bar; Unit stated once in title, axis or footnote; Value labels on the few points that carry the message; Legend only when direct labels are impractical

Bad signals: Legend far from the data with 4+ similar colours; Labels on every point so the chart becomes a table; No unit anywhere; Axis title missing when the title does not give the unit; Rotated or truncated category labels

Checks: Every series has a visible name; Unit appears in title, axis title or footnote; Category labels are horizontal and not clipped; Legend order matches visual order of series

Sources: EU Data Visualisation Guide, 'direct labelling': legends add lookup work, label directly when elements do not collide; https://data.europa.eu/apps/data-visualisation-guide/direct-labelling (returned by search; page not opened); ONS Service Manual, chart elements: direct labelling where practical, otherwise a legend; https://service-manual.ons.gov.uk/data-visualisation/build-specifications/chart-elements (returned by search); World Bank data visualization style guide: legends when direct labelling is not possible; https://worldbank.github.io/data-visualization-style-guide/chartelements (returned by search)

#### T-CHART-04 Emphasis on the message series  (weight 4, -)

Does the chart guide the eye to the data the title talks about (one accent, the rest muted)?

| Level | What the grader sees |
|---|---|
| 1 | Highlight contradicts the title, or colours rank series by accident so the eye lands on the wrong data. |
| 2 | No emphasis: all series equal weight; the reader must find the point; or 5+ strong colours. |
| 3 | Palette is restrained but emphasis is only implied (e.g. last series is the accent by default). |
| 4 | The focal series or point is visibly distinct and matches the title; others are quiet. |
| 5 | Focal data is accent-coloured, the rest muted, a short annotation marks the key change, and non-focal colours stay distinguishable (3:1 against the background). |

Good signals: One highlighted bar, line or segment in the accent colour; others grey or a quiet tone; Annotation or callout at the point that proves the title; Title states the finding and matches what is highlighted

Bad signals: Every series in a different saturated colour; Highlight on a series the title does not mention; Rainbow category colours with no meaning; Annotation covers the data

Checks: At most one accent colour for emphasis plus neutrals; Highlighted element is the one named in the title; Non-text marks (lines, bars) have >= 3:1 contrast against background (WCAG 1.4.11)

Sources: Storytelling with Data (Knaflic 2015): use one accent colour and grey for context, titles state the takeaway; read via summaries (https://thebusinessdive.com/why-visuals-matter), unverified in the book; W3C, WCAG 2.2 Understanding SC 1.4.11 Non-text Contrast: parts of graphics needed to understand them need 3:1 against adjacent colours; https://www.w3.org/WAI/WCAG22/Understanding/non-text-contrast.html (opened); bench/reference/diagram-design/style-guide.md: one focal accent, series palette is desaturated (repo)

#### T-CHART-05 Chart ink and density  (weight 3, -)

Is the plot free of non-data ink (heavy grid, 3D, shadows, redundant labels) while keeping the data legible?

| Level | What the grader sees |
|---|---|
| 1 | Decoration dominates (3D, shadows, gradients, heavy grid) or 8+ series are tangled. |
| 2 | Gridlines as strong as the data, or 6-7 series overlap, or redundant labelling clutters the plot. |
| 3 | Plain chart with default gridlines; 5 or fewer series; readable. |
| 4 | Gridlines faint; no border or effects; labelling is not redundant. |
| 5 | Minimal ink: only data, a few faint reference lines, direct labels; many series are split into small multiples. |

Good signals: Light or no gridlines; no chart border; Series count 1-4 on one plot, or small multiples for more; Data labels or gridlines, not both heavy

Bad signals: Heavy dark gridlines; Gradient or shadowed bars; 8+ lines on one plot; Value labels plus gridlines plus axis ticks all doing the same job

Checks: No 3D or shadow effect on chart elements; Gridline colour lighter than series colours; Series per plot <= 5-6; Chart plot occupies most of the chart frame (little empty margin)

Sources: Edward Tufte, The Visual Display of Quantitative Information (1983): data-ink ratio, chartjunk, small multiples; via course notes https://faculty.cc.gatech.edu/~stasko/4460/Notes/tufte.pdf (secondary, not the book); Dona Wong, The Wall Street Journal Guide to Information Graphics (2010): simplify, avoid chart clutter; unverified in this session

#### T-CHART-06 Title states the finding  (weight 3, -)

Does the slide title or subtitle say what the chart shows (finding plus unit/period) rather than naming the chart?

| Level | What the grader sees |
|---|---|
| 1 | Title is generic or contradicts the chart. |
| 2 | Title names the subject only ('Sales by region') and the finding is left to the reader. |
| 3 | Title names subject and unit/period; the trend is visible but not stated. |
| 4 | Title states the finding and the chart shows it; unit and period are present. |
| 5 | Title states the finding with a quantity or direction; chart highlight, annotation and title agree; a footnote gives the source or caveat. |

Good signals: Title gives the claim with a number or direction ('Response time falls within two quarters'); Subtitle or axis gives unit and period

Bad signals: Title like 'Chart', 'Results' or 'Sales data'; Claim in the title that the chart does not show

Checks: Title contains a verb or a number or a comparison; Unit and period appear on the slide; Highlight matches the title claim

Sources: Barbara Minto, The Pyramid Principle (1987): slide title as the statement of the point; via https://www.think-cell.com/en/resources/content-hub/using-the-pyramid-principle-to-build-better-powerpoint-presentations (secondary); Gene Zelazny, Say It with Charts: the chart title carries the message (https://www.oreilly.com/library/view/the-say-it/9780071474702/ch01.html listing; exact wording unverified)

## Topic: Data table (`data-table`)

Native editable tables of values or text attributes: results by region, competitor comparison grids, price lists, risk registers, schedules with columns.

Frequency: Second most common structured topic. Briefs: 15 of 108 specs; lengthbench t1-t3: 6 of 45; examples: ~160 pipe-table lines across 30 decks, tables on most JP consulting decks (competitor, risk, financial plan).

| id | name | weight | gate |
|---|---|---|---|
| T-TABLE-01 | Table is the right form and the right size | 4 |  |
| T-TABLE-02 | Alignment and number format | 5 |  |
| T-TABLE-03 | Light structure | 3 |  |
| T-TABLE-04 | Emphasis guides the lookup | 4 |  |
| T-TABLE-05 | Headers, units and source | 4 | yes |

#### T-TABLE-01 Table is the right form and the right size  (weight 4, -)

Is a table justified (exact values or multi-attribute lookup) and small enough to read at the shown font size?

| Level | What the grader sees |
|---|---|
| 1 | Cells overflow, text is clipped or unreadable, or a pattern-in-numbers message is buried in a grid. |
| 2 | Dense grid with tiny text; 10+ rows or 8+ columns; long sentences in cells. |
| 3 | Readable table; size at the upper limit; cells are short phrases or numbers. |
| 4 | Comfortable size; cells short; row order meaningful; the reader finds a value in seconds. |
| 5 | Only the rows and columns needed; order serves the message; an alternative (chart) is not clearly better. |

Good signals: Rows x columns fit the slide with body text still readable; About 5-8 columns and 3-10 rows in a presentation context; Rows that must be compared are adjacent

Bad signals: Spreadsheet dump with 12+ rows or 8+ columns; Table where a chart would show the pattern at once; Font shrunk to fit; Long sentences inside cells

Checks: No cell text clipped or overflowing; Rows <= ~10 and columns <= ~8 for non-dense decks; Min cell font size meets the deck's small-text floor; Cell text mostly <= 2 lines

Sources: Jonathan Schwabish, 'Ten Guidelines for Better Tables' (Journal of Benefit-Cost Analysis, 2020): tables serve lookup and exact values, charts show patterns; title seen via https://policyviz.com/2021/03/02/three-things-you-can-do-to-make-your-data-tables-more-visual/ (page text could not be retrieved; guidelines unverified); Stephen Few, Show Me the Numbers (2nd ed. 2012), ch. on tables vs graphs: use a table when values are looked up; unverified in this session

#### T-TABLE-02 Alignment and number format  (weight 5, -)

Are numbers right-aligned (or decimal-aligned) with consistent decimals and units, and text left-aligned?

| Level | What the grader sees |
|---|---|
| 1 | Numbers in one column use different units or scales, or are so misaligned that magnitude cannot be compared. |
| 2 | Centre- or left-aligned numbers with ragged digits; mixed decimals. |
| 3 | Numbers aligned consistently but decimals or units are not fully uniform. |
| 4 | Numbers right-aligned, same decimals per column, units in the header. |
| 5 | Level 4 plus consistent thousands separators and signs (+/-), header alignment matches column, totals visually distinct. |

Good signals: Numeric columns right-aligned with the same decimals; Units in the header, not repeated in each cell; Header alignment matches its column; Text left-aligned

Bad signals: Centred numbers of different length; Mixed decimals (1.5, 2, 3.25); Units repeated in every cell; Mixed currencies or scales in one column

Checks: Numeric cells have the same alignment within a column (right or decimal); Same number of decimals per column; Unit appears in header or a note, not in every cell; Header text alignment equals column alignment

Sources: Storytelling with Data blog, 'what is a table?': left-align text and right-align numbers as a guideline; https://www.storytellingwithdata.com/blog/2020/9/24/what-is-a-table (search summary only; page body not retrieved); Datawrapper, 'What to consider when creating tables': https://www.datawrapper.de/blog/guide-what-to-consider-when-creating-tables (returned by search; not opened); Schwabish, Ten Guidelines for Better Tables: right-align numbers and headers over numeric columns (via search summary, unverified)

#### T-TABLE-03 Light structure  (weight 3, -)

Do borders, fills and header treatment separate rows and columns without competing with the numbers?

| Level | What the grader sees |
|---|---|
| 1 | Borders or fills are so heavy that they hide the numbers; header not identifiable. |
| 2 | Full cell grid in strong colour; header distinguished only by size or not at all. |
| 3 | Standard table style; header distinct; grid acceptable. |
| 4 | Thin horizontal rules, no vertical rules, distinct header, faint banding if needed. |
| 5 | Whitespace and thin rules carry the structure; total/summary rows are distinct; one deliberate emphasis style. |

Good signals: Thin or no row rules; no full cell borders; Header row distinct by weight or a single fill; Subtle zebra or whitespace for long rows; Total row separated by a rule

Bad signals: Heavy borders on every cell; Dark fills on many cells; Header same weight as body; Merged cells that break row reading

Checks: Header row differs from body (weight/fill); Border width <= 1pt or only horizontal rules; No more than one fill colour in body cells except emphasis

Sources: Storytelling with Data (Knaflic 2015): remove unnecessary borders and shading, prefer light rules (read via search summary of the book, unverified in print); Edward Tufte, The Visual Display of Quantitative Information: data-ink ratio, erase non-data ink (secondary, course notes)

#### T-TABLE-04 Emphasis guides the lookup  (weight 4, -)

Does one visual cue (bold, colour, bar, heat shade) point to the cells that matter for the message?

| Level | What the grader sees |
|---|---|
| 1 | Emphasis misleads (the highlighted cell is not the point) or colour is the only signal and fails for colour-blind viewers. |
| 2 | No emphasis at all with a table of 30+ numeric cells, or 3+ unrelated highlight colours. |
| 3 | Some emphasis (header, total) but the key row/column is not marked. |
| 4 | One clear emphasis on the key row/column/cell; legend or title explains it. |
| 5 | Emphasis answers the title's question at a glance; a text cue (symbol, bold) backs any colour cue; rankings or deltas are visible. |

Good signals: Our row or best value emphasised once; Heat shade or in-cell bar on a numeric column; First column labels clearly separated from data

Bad signals: Everything bold; Multiple unrelated colours across cells; Colour as the only carrier of meaning; No emphasis and 40 equal cells

Checks: Highlight count is small (<= ~3 regions); Colour meaning is also encoded in text, symbol or weight; Highlighted row/col matches the title claim

Sources: Storytelling with Data (Knaflic 2015): heatmap table to show variation (via search summary; unverified in print); W3C WCAG 2.2, SC 1.4.1 Use of Color (colour is not the only carrier): https://www.w3.org/WAI/WCAG22/Understanding/use-of-color.html (known SC; page not opened)

#### T-TABLE-05 Headers, units and source  (weight 4, **gate**)

Do the headers, units and footnote make every number interpretable without guessing?

| Level | What the grader sees |
|---|---|
| 1 | Columns or rows are unlabelled; numbers cannot be interpreted. |
| 2 | Headers exist but units or period are missing in places. |
| 3 | Headers and units present; abbreviations mostly obvious. |
| 4 | Headers, units and period clear; footnote explains special values (n/a, estimates). |
| 5 | Level 4 plus consistent term use across header, title and body; totals labelled. |

Good signals: Every column has a header; Units and period stated; Footnote for source or caveat; Row header column identifies each record

Bad signals: Unlabelled columns; Numbers without units (%, JPY million, k); Abbreviations never explained

Checks: Header cell present for every column; Unit or % appears in header or cells; Footnote present when data has a source or an estimate

Sources: Few, Show Me the Numbers (2nd ed.): label and title so values are unambiguous; unverified in this session; Urban Institute Data Visualization Style Guide: https://urbaninstitute.github.io/graphics-styleguide (exists; table rules not read)

## Topic: KPI cards / key numbers (`key-numbers`)

Big-number cards and scorecards: 2-6 headline figures with label, change and note; metric tiles; financial summaries; targets vs actual.

Frequency: Briefs: 11 of 108 specs; lengthbench t1-t3: 8 of 45 (highest per-deck share); examples: 33 '.kpi' cards over ~12 decks (JP consulting, pitch, traction, results).

| id | name | weight | gate |
|---|---|---|---|
| T-KPI-01 | Number, label, unit are complete | 5 | yes |
| T-KPI-02 | Context shows good or bad | 5 |  |
| T-KPI-03 | Number dominance | 4 |  |
| T-KPI-04 | Number count and grouping | 3 |  |
| T-KPI-05 | Number integrity and formatting | 3 |  |

#### T-KPI-01 Number, label, unit are complete  (weight 5, **gate**)

Does every card give a value with its unit, a label saying what it measures, and a period or basis where needed?

| Level | What the grader sees |
|---|---|
| 1 | A figure has no label or unit, or the reader cannot tell what the number measures. |
| 2 | Labels exist but units or period are missing, or formats are inconsistent across cards. |
| 3 | Every card has value, unit and label; period is implied. |
| 4 | Value, unit, label and period are clear; formats are consistent. |
| 5 | Complete and consistent; labels are plain words rather than codes; footnote defines any derived metric. |

Good signals: Value, unit and label all visible per card; Period or basis stated once ('FY2026', 'vs last year'); Same unit format across comparable cards

Bad signals: Number without unit or label; Mixed formats (1.28B vs 128,000 million); Label so small it is not read with the number

Checks: Each card has numeric value + unit/symbol + label; Same decimals and scale among comparable cards; Period/basis appears on the slide

Sources: Stephen Few, Information Dashboard Design (2006, 2013): metrics need context; secondary via https://www.perceptualedge.com/blog/?p=160 (opened by search; not read in depth) and unverified chapter detail; Storytelling with Data (Knaflic 2015): a single big number works, with one sentence of interpretation; via https://www.skillsyouneed.com/rhubarb/data-storytelling.html (secondary)

#### T-KPI-02 Context shows good or bad  (weight 5, -)

Does each key number carry a comparison (change, target, prior period, benchmark) so its meaning is clear?

| Level | What the grader sees |
|---|---|
| 1 | Bare numbers; the reader cannot judge good or bad. |
| 2 | A comparison exists on some cards only, or the base is unnamed. |
| 3 | Every card has a delta or a note; the base is implied. |
| 4 | Every card shows a delta against a named base; direction and sentiment are readable. |
| 5 | Delta plus target or trend (sparkline, bullet) where it helps; good/bad is encoded by text or shape, not colour only. |

Good signals: Delta vs previous period or target next to the number; Sign and direction readable ('+14%', up arrow); Meaning of up (good/bad) is clear: e.g. wait time down is good

Bad signals: Bare numbers; Delta with no base; Red/green only to carry good/bad; Up arrow on a metric where up is bad, uncoloured

Checks: Each card has a comparison element (delta, target, note); Delta base is stated or obvious; Colour for good/bad also has a sign or text

Sources: Stephen Few, Information Dashboard Design: bullet graphs show a measure against a target and ranges, sparklines add trend context; https://www.perceptualedge.com/blog/?p=160 (search result), https://en.wikipedia.org/wiki/Bullet_graph (secondary); W3C WCAG 2.2 SC 1.4.1 Use of Color (colour is not the only visual signal): https://www.w3.org/WAI/WCAG22/Understanding/use-of-color.html (not opened)

#### T-KPI-03 Number dominance  (weight 4, -)

Is the number the largest element on its card, with a clear size step to label and note?

| Level | What the grader sees |
|---|---|
| 1 | The number is hard to find or is smaller than its label/icon. |
| 2 | Number is only slightly larger than the label; hierarchy is weak. |
| 3 | Number is larger than the label; step is moderate. |
| 4 | Number is clearly the largest (about 2x or more) and fits on one line. |
| 5 | Strong, consistent size step across cards; number plus delta reads in one glance; icon is secondary. |

Good signals: Value at least ~2x the label size; Numeral weight high, label light; Number placed first in reading order

Bad signals: Label and number the same size; Decoration or icon larger than the number; Number is split across lines

Checks: Numeral font size >= 2x label font size; Number text does not wrap; Numerals are the largest text on the card

Sources: Nancy Duarte, slide:ology (2008): one dominant element sets what is read first (principle; page not verified); Garr Reynolds, Presentation Zen: signal-to-noise, remove what does not carry the message; https://www.oreilly.com/library/view/presentation-zen-simple/9780132901529/ch06lev1sec3.html (returned by search)

#### T-KPI-04 Number count and grouping  (weight 3, -)

Is the count of cards small and uniform, with an order that has meaning (importance, financial flow)?

| Level | What the grader sees |
|---|---|
| 1 | 10+ tiles or cards of random size; no order discernible. |
| 2 | 7-9 cards, or uneven grid and unclear order. |
| 3 | 4-6 cards, uniform, order not explained. |
| 4 | 3-6 uniform cards; the order is logical; related ones grouped. |
| 5 | Card count, order and grouping make the story (e.g. result -> driver -> outlook), with the hero metric first or larger by design. |

Good signals: 3-6 cards in a single row or an even grid; Equal card size and spacing; Order follows importance or a P&L flow; Related metrics grouped

Bad signals: 8+ unrelated tiles; Uneven card sizes with no meaning; Ragged last row; Cards mixing unrelated units with no grouping

Checks: Card count 3-6 (up to 8 in dense decks); Card widths equal within a row; Gutters equal

Sources: Few, Information Dashboard Design: dashboards group related metrics, avoid fragmenting (unverified chapter detail); bench/reference/diagram-design/style-guide.md: grid and spacing divisible by 4, uniform treatments (repo)

#### T-KPI-05 Number integrity and formatting  (weight 3, -)

Are numbers formatted for fast reading (thousands separators, rounded precision, consistent scale) and consistent with the title?

| Level | What the grader sees |
|---|---|
| 1 | Numbers conflict with each other or with the title. |
| 2 | Excess precision or mixed scales make comparison slow. |
| 3 | Formatting is acceptable and consistent within a card. |
| 4 | Precision and scale are consistent across cards. |
| 5 | Precision matches the claim; scale is shortened for reading (1.28B not 1,280,000,000) and the unit is in a fixed place. |

Good signals: Rounded to the precision the decision needs; Separators and unit scale consistent (億円, M, k); Title and card numbers agree

Bad signals: False precision (12.3456%); Mixed scales (M and k); Title claims +20% but card shows +14%

Checks: Same scale suffix across cards; Decimals per metric type are consistent; Title numbers match card numbers

Sources: Dona Wong, WSJ Guide to Information Graphics: round numbers and cut digits for the reader (unverified in this session); Few, Show Me the Numbers: appropriate precision for the task (unverified)

## Topic: Process, flow and steps (`process-flow`)

Ordered sequences: step chevrons, numbered steps, flowcharts with decisions, swimlanes, sequence diagrams, cycles (improvement loops), release trains.

Frequency: Briefs: 9 of 108 specs (process steps left to right); lengthbench t1-t3: 6 of 45; examples: ~13 titles with flow/step/process meaning (05-jp-process, 23 four steps, 27, 28 swimlane and sequence, 11 plan, 19 three steps).

| id | name | weight | gate |
|---|---|---|---|
| T-PROC-01 | Order is unambiguous | 5 | yes |
| T-PROC-02 | Step content is uniform and short | 4 |  |
| T-PROC-03 | Step count and chunking | 3 |  |
| T-PROC-04 | Connector quality | 4 |  |
| T-PROC-05 | Who, when and outcome per step | 3 |  |

#### T-PROC-01 Order is unambiguous  (weight 5, **gate**)

Can the reader tell where the process starts, which way it runs and in what order the steps occur?

| Level | What the grader sees |
|---|---|
| 1 | Order cannot be read: no numbers or arrows, or arrows contradict each other. |
| 2 | Order is guessable from position; direction changes mid-flow with no cue; start/end unclear. |
| 3 | Order is readable via arrows or numbers; one direction; start/end identifiable. |
| 4 | One direction, explicit markers (number or chevron), clear start and end; branches labelled. |
| 5 | Order is read at a glance; the main path is visually dominant over exceptions; loops and returns are marked as such. |

Good signals: One reading direction (left to right or top to bottom); Numbers, chevrons or arrows show the order; A single start and a clear end; Loops marked as loops

Bad signals: Steps scattered with no arrows or numbers; Arrows pointing in mixed directions; Two possible starts; Order only implied by position in an irregular layout

Checks: Visible order markers (numbers, arrows, chevrons) on every step; Arrows go in one overall direction; Exactly one start (and at least one end); Branch labels on decision outputs

Sources: Flowchart conventions, ISO 5807 (1985) is the standard for flowchart symbols; one primary direction, one start, labelled decision branches (practitioner guides via search, e.g. https://www.designtechguide.com/?p=567; standard text unverified); bench/reference/diagram-design/primitives-core.md: orthogonal connectors, labelled arrows (repo; MIT); Nancy Duarte, slide:ology (2008) on diagramming a process: unverified, taxonomy not checked

#### T-PROC-02 Step content is uniform and short  (weight 4, -)

Are steps parallel in form (verb-first, similar length) with a short name and at most one line of detail?

| Level | What the grader sees |
|---|---|
| 1 | Text is clipped, overflows, or steps cannot be told apart. |
| 2 | Unequal length and form across steps; some paragraphs; boxes uneven. |
| 3 | Steps readable; some inequality in text length. |
| 4 | Parallel names; similar detail length; equal boxes. |
| 5 | Parallel, terse steps with an outcome/owner/time where it matters; consistent size and spacing. |

Good signals: Step names are 1-4 words, same grammatical form; Detail text is optional and about equal across steps; Equal box sizes for equal-weight steps

Bad signals: Step 1 is a paragraph, step 2 is one word; Boxes of unequal size with no meaning; Text overflows or shrinks to fit

Checks: Step names <= ~4 words (or ~12 CJK characters); Box widths equal where the steps have equal weight; No clipped text; All steps use the same pattern (verb-first or noun-first)

Sources: Garr Reynolds, Presentation Zen: simplicity and signal-to-noise (https://www.oreilly.com/library/view/presentation-zen-simple/9780132901529/ch06lev1sec3.html); Barbara Minto, The Pyramid Principle: ideas in one group share a form and are the same kind of thing (via secondary https://thinkinsights.net/insights/minto-pyramid-principle)

#### T-PROC-03 Step count and chunking  (weight 3, -)

Is the number of steps within what can be followed (about 3-7), with long processes chunked into phases?

| Level | What the grader sees |
|---|---|
| 1 | Step count contradicts the title or the sequence is lost across wraps. |
| 2 | 9+ steps at one level with no grouping. |
| 3 | 7-8 steps or a modest wrap; readable. |
| 4 | 3-7 steps, or longer sequence grouped in phases. |
| 5 | Count and chunking suit the content; each phase has a name, and the count matches the title. |

Good signals: 3-7 steps in one row; Phases or stages group longer sequences; Number of steps matches the title ('4 steps')

Bad signals: 12 equal boxes in a row; Title says 3 steps, slide shows 5; Wraps over multiple rows without a clear path

Checks: Step count matches any number in the title; Steps per row <= 7; Wrapped rows have a visible link (arrow or numbering)

Sources: George Miller (1956) 'The Magical Number Seven' as a rule of thumb for chunking (cited widely; original not checked here); Nancy Duarte, slide:ology: limit what the audience must hold at once (unverified detail)

#### T-PROC-04 Connector quality  (weight 4, -)

Are arrows short, orthogonal or straight, unobstructed and attached to the boxes they join, with labels clear of the line?

| Level | What the grader sees |
|---|---|
| 1 | Arrows are detached, cross boxes or each other so the path cannot be traced. |
| 2 | Some arrows are diagonal or touch nothing; crossing without hops; labels sit on lines. |
| 3 | Arrows connect the right boxes; minor crossings or mixed styles. |
| 4 | Clean orthogonal or straight arrows; no crossings or crossings with a hop; labels beside lines. |
| 5 | Every connector is traceable end to end; attach points fanned on shared edges; arrow roles (main/exception) use two clear styles. |

Good signals: Arrows connect box edges; No arrow crosses a box or another arrow without a hop; Right-angle bends, same arrow style; Labels sit beside the line with a gap

Bad signals: Floating arrows; Diagonal lines between unaligned boxes; Arrow passes behind boxes; Two arrows share a path; Label on top of the line

Checks: Arrow endpoints touch box edges; No connector passes behind a non-endpoint box; No two connectors overlap on the same segment; Connector label gap >= 6px from the line (diagram-design rule 2)

Sources: bench/reference/diagram-design/primitives-core.md: six connector rules (orthogonal, label margin 6-10px, no overlap, fan attach points, no pass-behind, label mask) (repo; read); bench/reference/diagram-design/style-guide.md: arrow roles and stroke (repo; read)

#### T-PROC-05 Who, when and outcome per step  (weight 3, -)

Where the process spans actors or time, does the slide show who does what (lanes or labels) and the output or duration?

| Level | What the grader sees |
|---|---|
| 1 | Process mixes actors with no way to tell who acts, and the title is about responsibility. |
| 2 | Owners named in text only in some steps; lanes unlabelled. |
| 3 | Owners/durations appear where the brief required. |
| 4 | Lanes or tags make owner clear; cross-lane handoffs readable. |
| 5 | Owner, time and output are visible per step without clutter; handoffs are the visually strongest connectors. |

Good signals: Swimlanes or owner tags for multi-actor processes; Duration or SLA beside steps where relevant; An outcome or deliverable shown at the end

Bad signals: Steps without owners when the title is about responsibilities; Lanes with no labels; Cross-lane arrows that tangle

Checks: Each lane or actor has a label; Handoff arrows cross lane borders only at the handoff point; Duration or time label where the brief gave one

Sources: Swimlane / sequence rules from bench/reference/diagram-design (repo; examples/28-swimlane-sequence.md used as local evidence); Japanese 業務フロー図 practice (lanes per department) is common but no primary guide was found; unverified

## Topic: System, architecture and concept diagram (`system-diagram`)

Structural diagrams of parts and relations: tiered architecture, component maps, data flow, Venn overlaps, fishbone / cause-effect, kanban boards, customer journey maps, treemaps.

Frequency: Mostly open-form slides. Examples: 27, 28, 29, 30 (arch, fishbone, kanban, journey map, treemap, venn) plus 09 and 12 (mermaid/svg); open briefs h1 (3 of 4 slides: fishbone, kanban, journey map); briefs 0 of 108 (not specified as a form). Estimated 8-10% of open-form slides.

| id | name | weight | gate |
|---|---|---|---|
| T-SYS-01 | Structure shows the right relationship | 5 | yes |
| T-SYS-02 | Focal element and hierarchy | 4 |  |
| T-SYS-03 | Label legibility and fit | 5 | yes |
| T-SYS-04 | Connector discipline | 4 |  |
| T-SYS-05 | Scope and completeness | 3 |  |

#### T-SYS-01 Structure shows the right relationship  (weight 5, **gate**)

Does the diagram form (tiers, containment, flow, overlap, cause tree) show the relationship the title claims?

| Level | What the grader sees |
|---|---|
| 1 | Diagram does not show the claimed relationship or mixes meanings so it cannot be read. |
| 2 | Relationship is guessable; arrows or containment have mixed meanings. |
| 3 | One main relationship is readable; a few ambiguous connectors. |
| 4 | Relationship clear; line styles carry one meaning each; the legend/labels explain them. |
| 5 | Form is the minimum structure that proves the title; every shape, line and position has a stated meaning. |

Good signals: Tiers imply layers; containment implies 'part of'; arrows imply flow or dependence; One relationship type per diagram; Title names the relationship ('Order platform in three tiers')

Bad signals: Arrows with no stated meaning; Boxes placed arbitrarily; Mixed relationships in one drawing (containment, flow and ownership); Decorative shapes that look like components

Checks: Every connector is explained by an arrow label, legend or convention; Layers or groups are labelled; Boxes in one tier are visually parallel

Sources: bench/reference/diagram-design/style-guide.md: node-type treatments (focal, backend, store, external, optional, security) and one-accent rule (repo); Alberto Cairo, The Functional Art (2012): form follows the task; framework summary via https://thedataschool.co.uk/laura-brylka/the-five-qualities-of-great-vizualizations-according-to-alberto-cairo (five qualities are from The Truthful Art); Nancy Duarte, slide:ology: choose a diagram family by the relationship (list, process, hierarchy, cycle, Venn); exact taxonomy not verified

#### T-SYS-02 Focal element and hierarchy  (weight 4, -)

Is there one or two focal components (accent) and the rest quiet, so the reader knows where to look first?

| Level | What the grader sees |
|---|---|
| 1 | Colour is random and the key component cannot be found. |
| 2 | Several accents compete; no focal point. |
| 3 | Palette restrained; the focal node is implied by position only. |
| 4 | One or two focal nodes marked; others quiet. |
| 5 | Focal node, supporting nodes and externals are three clear visual levels; colour meaning is consistent and explained. |

Good signals: One or two accent-bordered nodes; Supporting nodes neutral; Larger or central position for the key node

Bad signals: Every node in its own colour; Three or more accents; Key node same style as others

Checks: Accent used on <= 2 nodes; Node types use a consistent fill/stroke map; Focal node named in the title or caption

Sources: bench/reference/diagram-design/style-guide.md: 'focal (1-2 max)', one accent colour (repo; read); Edward Tufte, The Visual Display of Quantitative Information: layering and separation of data from background (secondary)

#### T-SYS-03 Label legibility and fit  (weight 5, **gate**)

Is every node and connector label readable at slide size, complete and inside its shape (no shrink or clip)?

| Level | What the grader sees |
|---|---|
| 1 | Labels are unreadable at slide size, clipped, or overlap lines. |
| 2 | Several labels at very small size or touching edges; abbreviations unexplained. |
| 3 | Labels readable and fit, with tight padding; minor overlap. |
| 4 | Labels readable, padded, masked; abbreviations explained. |
| 5 | Consistent label sizes by role (name, sublabel, arrow label); no shrink to fit; long names cut instead of shrunk. |

Good signals: Node names 12pt-equivalent or larger; Sublabels short and not tiny; Text fits inside boxes with padding; Labels masked off lines

Bad signals: Text 8pt or less to fit; Clipped or overflowing labels; Label crossing a connector; Label ambiguous (abbreviations without legend)

Checks: No text overflow in any node; Min label font size >= deck floor (e.g. 10-12pt for projected slides); Padding >= ~8px inside boxes; Connector labels do not overlap lines or boxes; CJK width budget = 1em per full-width character

Sources: bench/reference/diagram-design/style-guide.md: floor of 12px for CJK labels, width budget 1em for wide chars (repo; read); bench/reference/diagram-design/primitives-core.md: label mask and margin (repo; read); W3C WCAG 2.2 SC 1.4.3 Contrast (Minimum): 4.5:1 for regular text; https://www.w3.org/WAI/WCAG22/Understanding/contrast-minimum.html (known SC; not opened)

#### T-SYS-04 Connector discipline  (weight 4, -)

Are connectors orthogonal or straight, non-overlapping, attached, and drawn behind the boxes?

| Level | What the grader sees |
|---|---|
| 1 | The path of at least one connector cannot be traced. |
| 2 | Diagonals, shared lines or pass-through boxes in several places. |
| 3 | Mostly clean connectors; one or two crossings. |
| 4 | Orthogonal, fanned attach points, no shared segments. |
| 5 | All six diagram-design connector rules hold; crossings are rare and bridged. |

Good signals: Right-angle connectors with rounded corners; Distinct attach points on shared edges; Arrows drawn behind boxes; Crossings with a hop

Bad signals: Diagonal slashes; Arrow passes behind an unrelated box; Two arrows share a line; Arrowhead hidden under a box

Checks: No diagonal connector between non-aligned nodes; No two connectors share a segment; Connectors do not cross unrelated boxes; Distinct attach points per connector

Sources: bench/reference/diagram-design/primitives-core.md, 'Mandatory connector rules' 1-6 (repo; read)

#### T-SYS-05 Scope and completeness  (weight 3, -)

Does the diagram show the right amount of the system (the parts the title needs, no more) and name what is out of scope or external?

| Level | What the grader sees |
|---|---|
| 1 | Components named in the title are missing, or 30+ nodes make the structure unreadable. |
| 2 | 20-30 nodes; externals not distinguished. |
| 3 | Key parts present; some extra detail. |
| 4 | Only needed parts; externals distinct; groups labelled. |
| 5 | Level of detail fits the audience; a caption states scope or what is omitted. |

Good signals: 8-15 nodes for a one-slide overview; Externals visibly distinct; Detail beyond the title's claim omitted or deferred

Bad signals: 30+ nodes in one drawing; Internal and external systems styled identically; Components in the title missing

Checks: Node count <= ~15 (non-dense) or grouped; Every component named in the title is present; External systems differ in stroke or fill

Sources: bench/reference/diagram-design/style-guide.md: node-type treatments (external, optional, store) (repo; read); Garr Reynolds, Presentation Zen: signal-to-noise (https://www.oreilly.com/library/view/presentation-zen-simple/9780132901529/ch06lev1sec3.html)

## Topic: Comparison and options (`comparison`)

Side-by-side comparison of 2-4 things on shared criteria: options A/B/C, before/after, pros/cons, build vs buy, current vs target, vendor fit, benefit boxes.

Frequency: Briefs: 14 of 108 specs (side-by-side boxes) plus 15 tables that often compare; lengthbench t1-t3: 6 of 45; examples: ~11 comparison titles (競合比較, 売り切り型と稼働保証型, Build or buy, Vendor fit by criterion, options).

| id | name | weight | gate |
|---|---|---|---|
| T-CMP-01 | Same criteria, same order | 5 | yes |
| T-CMP-02 | Recommendation or verdict is visible | 5 |  |
| T-CMP-03 | Fair visual weight | 4 |  |
| T-CMP-04 | Differences are quantified or explicit | 4 |  |
| T-CMP-05 | Item count | 3 |  |

#### T-CMP-01 Same criteria, same order  (weight 5, **gate**)

Do all compared items answer the same questions in the same order, so each row can be compared directly?

| Level | What the grader sees |
|---|---|
| 1 | Items are described on different dimensions; no fair comparison is possible. |
| 2 | Mostly parallel but some attributes are missing or in a different order; rows do not align. |
| 3 | Parallel attributes; alignment approximate. |
| 4 | Same attributes, same order, aligned across columns; gaps marked. |
| 5 | Attributes are the decision criteria; alignment is exact; difference cells are easy to scan. |

Good signals: Aligned rows across columns; Same attributes per option; Equal slot for missing data (n/a)

Bad signals: Option A lists cost, B lists benefits; Unequal number of points; Unaligned rows

Checks: Each option has the same attribute set; Row positions align across columns; Missing values shown as n/a, not omitted

Sources: Barbara Minto, The Pyramid Principle: items in a group are the same kind and ordered logically (secondary: https://thinkinsights.net/insights/minto-pyramid-principle); Consulting comparison-table practice (McKinsey/BCG-style option grids): no primary text found; unverified

#### T-CMP-02 Recommendation or verdict is visible  (weight 5, -)

Does the slide say which option wins or what the comparison means (recommended highlight, bottom-line statement)?

| Level | What the grader sees |
|---|---|
| 1 | The visual emphasis contradicts the recommendation. |
| 2 | No verdict; the slide lists options only. |
| 3 | Verdict in text only, small or at the bottom. |
| 4 | Verdict stated and the chosen option is highlighted. |
| 5 | Title, highlight and bottom line agree; the deciding criteria are visible as the reason. |

Good signals: One option highlighted or marked recommended; Conclusion line below the options; Title states the verdict

Bad signals: Options equal and no conclusion; Highlight on a different option than the text recommends; Reader must compute the answer

Checks: Recommended option has distinct fill/border; A conclusion sentence exists when the brief gave one; Highlight and text name the same option

Sources: Barbara Minto, The Pyramid Principle: answer first, then the support (secondary); Garr Reynolds, Presentation Zen: one clear message per slide (via https://www.free-power-point-templates.com/articles/presentation-zen, secondary); Japanese consulting tip: 1スライド1メッセージ; https://biz.moneyforward.com/work-efficiency/basic/22712/ (returned by search)

#### T-CMP-03 Fair visual weight  (weight 4, -)

Do compared items get equal size, spacing and treatment, except the deliberate emphasis?

| Level | What the grader sees |
|---|---|
| 1 | Size or colour implies a wrong ranking. |
| 2 | Uneven sizes and spacing that do not carry meaning. |
| 3 | Roughly equal; minor differences. |
| 4 | Equal widths and layout; emphasis is deliberate. |
| 5 | Exactly equal; emphasis applied once; whitespace balanced. |

Good signals: Equal widths; Same internal layout per column; A single, deliberate emphasis

Bad signals: Uneven widths from text length; One column crowded, another empty; Colours imply a ranking that is not intended

Checks: Column widths within ~5% of each other; Same font sizes per column; Number of text lines per column balanced

Sources: Tufte, Visual Display of Quantitative Information: small multiples, repeat the same design for comparison (secondary: https://faculty.cc.gatech.edu/~stasko/4460/Notes/tufte.pdf); bench/reference/diagram-design/style-guide.md: grid of 4 and consistent radius/stroke (repo)

#### T-CMP-04 Differences are quantified or explicit  (weight 4, -)

Are the differences that decide the choice shown as numbers, marks or short phrases (not buried in prose)?

| Level | What the grader sees |
|---|---|
| 1 | Comparison relies on vague adjectives; nothing quantified. |
| 2 | Some numbers, mixed with long prose. |
| 3 | Numbers or marks for most criteria. |
| 4 | Decisive criteria are numeric/explicit with units. |
| 5 | Deltas or rankings are visible at a glance; marks have a legend or text, not colour alone. |

Good signals: Numbers with units per option; Check or cross marks plus text; Delta between options; Bold on the deciding values

Bad signals: Paragraph per option; Adjectives instead of figures; Ratings by colour only

Checks: Numbers carry units; Ratings use symbols plus text, not colour alone; Text per cell <= ~2 lines

Sources: Dona Wong, WSJ Guide to Information Graphics: be specific (unverified); W3C WCAG 2.2 SC 1.4.1 Use of Color (https://www.w3.org/WAI/WCAG22/Understanding/use-of-color.html; not opened)

#### T-CMP-05 Item count  (weight 3, -)

Is the number of compared items small enough to compare (2-4), with larger sets moved to a table?

| Level | What the grader sees |
|---|---|
| 1 | 6+ columns of prose; no comparison is possible. |
| 2 | 5 columns or cards with long text. |
| 3 | 4 columns, moderate text. |
| 4 | 2-4 items, short text. |
| 5 | Count fits the decision; 2 items are shown as before/after pair with matching rows. |

Good signals: 2-4 columns; 5+ items shown in a grid or table instead

Bad signals: 6 thin columns; Cards with 5+ bullets each

Checks: Columns <= 4 for box layouts; Bullets per box <= ~4

Sources: Common 3-option rule in consulting decks (e.g. options A/B/C); no primary source; unverified; Garr Reynolds, Presentation Zen (signal-to-noise)

## Topic: Timeline and roadmap (`timeline-roadmap`)

Time-ordered plans: milestones, phases across quarters/years, Gantt-like roadmaps, schedules, history timelines, release plans.

Frequency: Examples: ~15 of 154 titles (08, 11, 16, 19, 20, 22, 23, 26 roadmap or schedule); briefs 0 of 108 (not requested as a form); lengthbench t4/t5 open decks contain roadmap slides (e.g. 'Lộ trình 12 tuần'). About 6-10% of slides in real consulting decks.

| id | name | weight | gate |
|---|---|---|---|
| T-TIME-01 | Time axis is correct and legible | 5 | yes |
| T-TIME-02 | Items placed at the right time | 5 | yes |
| T-TIME-03 | Swimlanes and ownership | 3 |  |
| T-TIME-04 | Milestone and phase salience | 4 |  |
| T-TIME-05 | Status and realism cue | 2 |  |

#### T-TIME-01 Time axis is correct and legible  (weight 5, **gate**)

Is there a visible time axis with ordered, evenly spaced or proportionally scaled periods?

| Level | What the grader sees |
|---|---|
| 1 | No time axis, or periods out of order, so the sequence in time cannot be read. |
| 2 | Axis present but unequal periods with no scale cue, or labels clipped. |
| 3 | Axis present, ordered and legible; scale is approximately even. |
| 4 | Ordered, even or true-to-scale; start/end dates readable. |
| 5 | Axis scale is honest; the current period or today is marked; breaks in scale are flagged. |

Good signals: Labelled periods in left-to-right order; Equal period widths or true-to-scale; Axis at the top or bottom, repeated if the slide is tall

Bad signals: No dates; Periods out of order; A 1-month phase drawn as wide as a 12-month phase with no cue; Axis labels clipped

Checks: Periods in chronological order; Equal column widths for equal periods; Date/period labels present and not clipped; A 'today' or current-period marker where status is shown

Sources: Atlassian, 'Project roadmap explained': time axis is the spine of a roadmap; https://www.atlassian.com/agile/project-management/project-roadmap (returned by search); Gantt and roadmap conventions: diamonds for milestones, one axis (practitioner summaries via search; no primary standard); Edward Tufte, The Visual Display of Quantitative Information: scale integrity (secondary)

#### T-TIME-02 Items placed at the right time  (weight 5, **gate**)

Does each phase or milestone sit at the period it belongs to, with start and end visible where duration matters?

| Level | What the grader sees |
|---|---|
| 1 | Items are placed at wrong periods, or placement contradicts the labels. |
| 2 | Placement is approximate; some bars overlap or cannot be dated. |
| 3 | Placement is correct but start/end are only implied. |
| 4 | Bars/markers match dates; durations visible; no hidden overlaps. |
| 5 | All items placed true to scale with start/end or labels; critical path or dependencies visible without clutter. |

Good signals: Bars span the correct periods; Milestones are markers at a date; Dependencies or handoffs are arrows only where they matter

Bad signals: Bars placed by space convenience, not by date; Milestone dates missing; Overlapping bars hiding each other

Checks: Bar start/end match their labelled dates; Markers have a date label; No bar overlaps another in the same lane

Sources: Atlassian and ProofHub roadmap guides: milestones are markers, phases are bars (https://www.atlassian.com/agile/project-management/project-roadmap; https://www.proofhub.com/articles/project-roadmap; search results); Gantt convention: milestone = diamond (practitioner sources via search)

#### T-TIME-03 Swimlanes and ownership  (weight 3, -)

Are parallel workstreams grouped in labelled lanes with owners or deliverables where relevant?

| Level | What the grader sees |
|---|---|
| 1 | Parallel streams are mixed; cannot tell which bar belongs where. |
| 2 | Lanes implied by position only; labels missing. |
| 3 | Lanes labelled. |
| 4 | Lanes labelled; owner/deliverable on bars or at lane head. |
| 5 | Lanes are ordered by importance; dependencies across lanes are clear. |

Good signals: Lane labels at left; One workstream per lane; Owner or deliverable per bar when requested

Bad signals: Bars in one pile; Lane labels missing; Owners only in a footnote

Checks: Lane label per workstream; Bars inside the lane boundary; Owner text where the brief gives it

Sources: Atlassian, 'Project roadmap explained' (key elements include milestones, timeline, ownership); https://www.atlassian.com/agile/project-management/project-roadmap (search result); bench/reference/diagram-design (swimlane type; repo example-swimlane.png)

#### T-TIME-04 Milestone and phase salience  (weight 4, -)

Do key milestones and phase names stand out from supporting detail, with a limited number of items?

| Level | What the grader sees |
|---|---|
| 1 | Items are indistinguishable; milestones cannot be found. |
| 2 | Too many equal items (15+); detail text tiny. |
| 3 | Milestones differ in some way; text readable. |
| 4 | Milestones distinct; phase names clear; fewer than ~12 items. |
| 5 | Clear 3-level hierarchy: phase, milestone, detail; the item the title is about is emphasised. |

Good signals: Key milestones marked with distinct shape or colour; Phase names readable at slide size; Detail text short

Bad signals: 15+ equal items; Milestone text as small as footnotes; Colours for each phase with no meaning

Checks: Milestone symbol differs from bars; Min text size meets the deck floor; Item count <= ~12 (dense decks up to ~20)

Sources: Garr Reynolds, Presentation Zen: signal-to-noise (https://www.oreilly.com/library/view/presentation-zen-simple/9780132901529/ch06lev1sec3.html); Barbara Minto, Pyramid Principle: group and summarise (secondary)

#### T-TIME-05 Status and realism cue  (weight 2, -)

Where the plan has a status (done, in progress, planned) or a decision point, is it visible and consistent?

| Level | What the grader sees |
|---|---|
| 1 | Status is implied but the visuals contradict it (e.g. past items styled as future). |
| 2 | Status is not shown even though the title is about progress. |
| 3 | Status is shown in part. |
| 4 | Status and decision points are visible with consistent styling. |
| 5 | Status has a text or shape cue besides colour, plus the next decision and its date. |

Good signals: Done/now/next states have distinct fills; Decision gate or approval marked; Legend short or direct labels

Bad signals: Everything looks 'planned'; Status colour without text; Decision date missing

Checks: Past/current/future items differ in style; Status has a non-colour cue; Decision point or next step is marked

Sources: W3C WCAG 2.2 SC 1.4.1 Use of Color (not opened); Atlassian roadmap guidance on keeping a roadmap current (search result; https://www.atlassian.com/agile/project-management/project-roadmap)

## Topic: Hierarchy, org chart and tree (`hierarchy-org`)

Parent-child structures: org charts, governance bodies, steering committees, taxonomies, issue trees, pyramids, work breakdown structures.

Frequency: Examples: ~10 of 154 titles (07-jp-org, 11 推進体制, 16 実行体制, 19 Cơ cấu điều hành, 23, 25 組織の変更, 22); briefs 0 of 108; open decks t4/t5 include organisation slides. About 4-7% of slides.

| id | name | weight | gate |
|---|---|---|---|
| T-ORG-01 | Reporting lines are readable | 5 | yes |
| T-ORG-02 | Levels are visible and balanced | 4 |  |
| T-ORG-03 | Node text is identifiable | 4 |  |
| T-ORG-04 | Branch count and layout fit | 3 |  |
| T-ORG-05 | Emphasis and roles of groups | 3 |  |

#### T-ORG-01 Reporting lines are readable  (weight 5, **gate**)

Can the reader trace who or what sits under whom, with one clear top and no ambiguous lines?

| Level | What the grader sees |
|---|---|
| 1 | Parent-child links cannot be traced (crossing lines, unattached boxes). |
| 2 | Mostly traceable; some crossings or ambiguous attachments; dotted vs solid not distinguished. |
| 3 | Hierarchy traceable; minor line clutter. |
| 4 | One top; tidy orthogonal lines; children aligned beneath; secondary links have a distinct style. |
| 5 | Structure is read at a glance; line style carries a stated meaning (solid = line, dashed = advisory) and no crossing. |

Good signals: One top node; Straight vertical/horizontal connectors with rounded or square corners; Children aligned under parents; Different line style for dotted-line or advisory links with a legend

Bad signals: Lines crossing; Child linked to two parents without style; No visible top; Diagonal lines

Checks: Exactly one root node (unless stated); No crossing connectors; Dotted/dashed lines used consistently with a legend or note; Connectors attach at box edges

Sources: bench/reference/diagram-design/primitives-core.md: orthogonal connectors, no overlap, fanned attach points (repo; read); Dotted-line vs solid-line reporting conventions: common practice, no primary guide found in search; unverified

#### T-ORG-02 Levels are visible and balanced  (weight 4, -)

Are levels aligned in rows (or columns), with node size reflecting level and spacing even?

| Level | What the grader sees |
|---|---|
| 1 | Levels are not distinguishable (boxes scattered). |
| 2 | Same-level boxes are misaligned; or 6+ levels are shrunk. |
| 3 | Levels visible; alignment adequate. |
| 4 | Levels aligned and spaced evenly; box size or weight steps down. |
| 5 | Levels, siblings and groups are clear; fewer than 5 levels or the lower levels are collapsed into text. |

Good signals: Same-level boxes on one baseline; Size or weight decreases down the levels; 3-4 levels on one slide

Bad signals: Staggered boxes at one level; 6+ levels in a tiny chart; Siblings with wildly different widths

Checks: Siblings share y (or x) coordinate; Equal gutters between siblings; Level count <= 4-5; Sibling box widths equal

Sources: Span-of-control guides: reasonable spans about 5-8 for managers, and few layers; https://theorgchart.com/?p=664 and https://umbrex.com/resources/the-organizational-design-playbook/spans-of-control-layers-and-managerial-workload/ (returned by search; practitioner); bench/reference/diagram-design/style-guide.md: grid divisible by 4 (repo)

#### T-ORG-03 Node text is identifiable  (weight 4, -)

Does each node give role or name plus function in 1-2 short lines, in a consistent form?

| Level | What the grader sees |
|---|---|
| 1 | Node text is clipped or unreadable. |
| 2 | Inconsistent form (names in some, roles in others); long text. |
| 3 | Readable and mostly consistent. |
| 4 | Consistent two-line form, e.g. role + responsibility. |
| 5 | Form adds the one fact the title needs (owner, headcount, mandate) without crowding. |

Good signals: Role/title + name or function; Same format per node; Names or roles shortened rather than shrunk

Bad signals: Paragraphs in nodes; Mix of names and roles; Clipped text

Checks: No clipped text in nodes; Same lines per node (role, name); <= 2-3 lines per node

Sources: bench/reference/diagram-design/style-guide.md: node name and sublabel roles (repo; read); Garr Reynolds, Presentation Zen: simplicity (secondary)

#### T-ORG-04 Branch count and layout fit  (weight 3, -)

Does the chosen layout (top-down, left-right, grouped columns) fit the number of branches without shrinking text?

| Level | What the grader sees |
|---|---|
| 1 | Text unreadable because the layout cannot fit the branches. |
| 2 | Text shrunk to fit 8+ siblings. |
| 3 | Layout fits with small text. |
| 4 | Layout chosen to fit; text stays at body size. |
| 5 | Layout makes comparisons between branches easy; the chart uses the slide area well. |

Good signals: Wide trees are turned into left-right or column groups; Leaf-level lists inside group boxes; Text size constant

Bad signals: 12 siblings in one row with tiny text; Deep tree squeezed into one corner

Checks: Siblings per row <= ~6-7; Min font size meets deck floor; Slide area utilisation: tree spans most of the body area

Sources: Span-of-control practitioner guides (as above); Duarte, slide:ology: hierarchy diagrams; taxonomy unverified

#### T-ORG-05 Emphasis and roles of groups  (weight 3, -)

Is the group or role the slide is about emphasised, and are groups (committee vs task force) distinguishable?

| Level | What the grader sees |
|---|---|
| 1 | Emphasis falls on an irrelevant node. |
| 2 | No emphasis; or groups coloured randomly. |
| 3 | Some distinction between groups. |
| 4 | Key body emphasised; group types styled consistently. |
| 5 | Emphasis matches the title; styling encodes role types (permanent, temporary, external) with a legend. |

Good signals: Accent on the decision body; Group frames or colours with meaning; Legend short

Bad signals: Every group a different colour; No distinction between permanent and temporary bodies

Checks: Accent on <= 2 nodes; Group frames label their group; Emphasised node matches the title

Sources: bench/reference/diagram-design/style-guide.md: focal and optional node types (repo; read)

## Topic: Framing slides (cover, agenda, section, closing, decision) (`framing`)

Slides that frame the talk rather than carry content: cover/title, agenda, section divider, thank-you/closing, next steps, requested decisions, executive summary lead-ins.

Frequency: Cover slides alone: 20 of 108 brief specs, 3 of 45 lengthbench t1-t3, and the first slide of every example deck (~30). Agenda/closing/decisions: examples 11, 16, 20, 22, 23, 26 have agenda or decision slides (~10 titles).

| id | name | weight | gate |
|---|---|---|---|
| T-FRAME-01 | One message and one hierarchy | 5 |  |
| T-FRAME-02 | Metadata is complete | 4 |  |
| T-FRAME-03 | Agenda and summary structure | 4 |  |
| T-FRAME-04 | Visual anchor and restraint | 3 |  |

#### T-FRAME-01 One message and one hierarchy  (weight 5, -)

Does the slide carry one idea (title, optional subtitle, maybe date or owner) with a clear first/second/third reading order?

| Level | What the grader sees |
|---|---|
| 1 | No title hierarchy or content that is not framing (the slide is clutter). |
| 2 | Title and subtitle are nearly the same size; extra elements compete. |
| 3 | Title dominant; subtitle and meta readable. |
| 4 | Clear three-level hierarchy (title, subtitle, meta); ample space. |
| 5 | The slide states the deck's topic and audience at a glance; every element has a reason; whitespace is deliberate. |

Good signals: Title largest, subtitle clearly smaller; Whitespace around the title; No extra bullets

Bad signals: Several competing headlines; A cover with a paragraph; Logo, date, and tagline at equal weight

Checks: Title size >= ~1.5x subtitle size; Text blocks <= 3 on a cover/section slide; No body text paragraphs on a cover

Sources: Garr Reynolds, Presentation Zen: simplicity, signal-to-noise; https://www.oreilly.com/library/view/presentation-zen-simple/9780132901529/ch06lev1sec3.html (returned by search; no divider/closing-specific passage was found); Nancy Duarte, slide:ology: one idea per slide (unverified in this session)

#### T-FRAME-02 Metadata is complete  (weight 4, -)

Does a cover give the title, subject line, presenter or organisation and date; does an agenda give the numbered sections; does a closing give the ask or next step?

| Level | What the grader sees |
|---|---|
| 1 | Missing required elements from the brief (e.g. no title or date). |
| 2 | Elements present but unordered or mixed in size. |
| 3 | All required elements present. |
| 4 | Required elements present with clear order; agenda matches deck. |
| 5 | Level 4 plus the closing slide states one specific action, owner and date. |

Good signals: Title + subtitle + organisation/date on a cover; Numbered agenda items with parallel names; Closing states a decision, owner, deadline

Bad signals: A cover with a title only when the brief gave a date and owner; Thank you slide with no contact or next step; Agenda items that do not match section titles

Checks: Every item given in the brief appears; Agenda entries match later slide titles; Closing slide has an action, owner, or date

Sources: Barbara Minto, The Pyramid Principle: situation/complication/question/answer opening and governing thought; via https://www.think-cell.com/en/resources/content-hub/using-the-pyramid-principle-to-build-better-powerpoint-presentations (secondary); Consulting 'decisions requested' closing (ご決議事項) practice: no primary source found; unverified

#### T-FRAME-03 Agenda and summary structure  (weight 4, -)

Does the agenda or executive summary use 3-6 parallel items, each with a message or a verb, in the order of the deck?

| Level | What the grader sees |
|---|---|
| 1 | Agenda items contradict the deck's order, or summary has no conclusion. |
| 2 | 7+ items or non-parallel; the summary lists topics. |
| 3 | 3-6 items, readable. |
| 4 | Parallel items in deck order; summary states conclusions. |
| 5 | Summary reads as an answer-first argument; each item can be mapped to a slide; progress marker on later dividers. |

Good signals: 3-6 items; Parallel form; Order matches deck; Executive summary has conclusion then 3 support points

Bad signals: 10 agenda items; Mixed noun and verb forms; Summary lists topics without conclusions

Checks: Item count 3-6 (up to 8 in long decks); Items parallel in form; Summary items contain a claim or number

Sources: Barbara Minto, The Pyramid Principle: top-down answer first, grouped supports; secondary https://thinkinsights.net/insights/minto-pyramid-principle; Japanese consulting guide: 1スライド1メッセージ and key message first; https://webtan.impress.co.jp/e/2019/08/07/32999 (returned by search; not opened)

#### T-FRAME-04 Visual anchor and restraint  (weight 3, -)

Does the slide use one visual anchor (big type, band, image or simple shape) and stay restrained, consistent with the deck?

| Level | What the grader sees |
|---|---|
| 1 | Decoration hides or fights the title. |
| 2 | Several decorative elements; inconsistent with other dividers. |
| 3 | Plain and legible. |
| 4 | One anchor element; matches the deck's other dividers. |
| 5 | The anchor expresses the topic or section number; all dividers in the deck match. |

Good signals: One accent band or image; Consistent with other framing slides; No decorative clutter

Bad signals: Stock-style decoration with no meaning; Different framing style on each divider; Text over a busy image

Checks: Dividers share layout and anchor; Text over image has 4.5:1 contrast (or 3:1 for large text); Number of decorative shapes <= ~3

Sources: W3C WCAG 2.2 SC 1.4.3 Contrast (Minimum): 4.5:1 for text, 3:1 for large text; https://www.w3.org/WAI/WCAG22/Understanding/contrast-minimum.html (not opened); Garr Reynolds, Presentation Zen: restraint (secondary)

## Topic: Text argument / message slide (`text-message`)

Slides carried by words: bullet lists, executive summary, president's message, key takeaways, text-plus-chart insight slides, quotes.

Frequency: Most common text form. Briefs: 19 of 108 specs (bullet list); lengthbench t1-t3: 5 of 45; examples: ~15 titles (executive summaries, messages, outlook, takeaways) plus text-heavy halves of many slides.

| id | name | weight | gate |
|---|---|---|---|
| T-TEXT-01 | Message first, support second | 5 |  |
| T-TEXT-02 | Bullet count and length | 4 |  |
| T-TEXT-03 | Parallel structure and grouping | 3 |  |
| T-TEXT-04 | Evidence and numbers in text | 4 |  |
| T-TEXT-05 | Text-only slide earns its form | 3 |  |

#### T-TEXT-01 Message first, support second  (weight 5, -)

Does the title state the conclusion and do the bullets support it (and only it)?

| Level | What the grader sees |
|---|---|
| 1 | Title and bullets are unrelated, or the slide has no discernible point. |
| 2 | Title is a label; the message is found only by reading all bullets. |
| 3 | Title states the topic with a hint of the message; bullets mostly support it. |
| 4 | Title is the claim; all bullets support it. |
| 5 | Title claim + key message line + bullets form an answer-first block; the reader gets the point from the title alone. |

Good signals: Title is a sentence with a claim; Each bullet supports the claim; Number of supports matches a number in the title, if any

Bad signals: Topic-label title ('Overview'); Bullets drift to other topics; Conclusion appears last

Checks: Title has a verb or a quantity; Each bullet maps to the claim; No bullet repeats the title

Sources: Barbara Minto, The Pyramid Principle (1987): answer first; supporting points grouped; via https://www.think-cell.com/en/resources/content-hub/using-the-pyramid-principle-to-build-better-powerpoint-presentations (secondary); Japanese guide: ワンスライド・ワンメッセージ; https://webtan.impress.co.jp/e/2019/08/07/32999 and https://biz.moneyforward.com/work-efficiency/basic/22712/ (search results; not opened)

#### T-TEXT-02 Bullet count and length  (weight 4, -)

Is the bullet count limited (about 3-6) and each bullet a short phrase or one line?

| Level | What the grader sees |
|---|---|
| 1 | Wall of text: more than ~12 lines or paragraphs at small font. |
| 2 | 7-10 bullets or several 2+ line bullets. |
| 3 | 5-7 bullets; most one or two lines. |
| 4 | 3-6 bullets; one line each. |
| 5 | Bullets are terse, parallel, front-loaded with the keyword or number; sub-levels avoided. |

Good signals: 3-6 bullets; One line per bullet; Sentence-case phrases with a number

Bad signals: 10+ bullets; Multi-line paragraphs; Sub-bullets under sub-bullets

Checks: Bullets <= 6 on non-dense slides; Lines per bullet <= 2; Nesting depth <= 1

Sources: Garr Reynolds, Presentation Zen: cut the non-essential, signal-to-noise; https://www.oreilly.com/library/view/presentation-zen-simple/9780132901529/ch06lev1sec3.html; Nancy Duarte, slide:ology: slides are glanceable (a 3-second rule is attributed to Duarte; unverified wording)

#### T-TEXT-03 Parallel structure and grouping  (weight 3, -)

Are bullets parallel in grammar and grouped by logic (MECE) rather than a stream of facts?

| Level | What the grader sees |
|---|---|
| 1 | Items overlap or contradict each other. |
| 2 | Mixed forms; no grouping; arbitrary order. |
| 3 | Mostly parallel; order roughly logical. |
| 4 | Parallel and ordered (importance, time, process). |
| 5 | Grouped, mutually exclusive, collectively exhaustive for the claim; the order is stated or obvious. |

Good signals: Same grammatical form; Group headings for 6+ items; No overlap between bullets

Bad signals: Mixed sentence and fragment; Duplicate points; Unordered list of unrelated items

Checks: Bullets start with the same part of speech; No two bullets state the same fact; Order follows importance, time or process

Sources: Barbara Minto, The Pyramid Principle: ideas in a group are the same kind and are ordered logically; MECE (secondary: https://thinkinsights.net/insights/minto-pyramid-principle; https://vectree.io/c/history-core-concepts-and-structural-rules-of-the-minto-pyramid-principle-in-management-consulting)

#### T-TEXT-04 Evidence and numbers in text  (weight 4, -)

Does the text carry numbers, names or examples rather than adjectives, and are key numbers visually emphasised?

| Level | What the grader sees |
|---|---|
| 1 | Claims are unsupported adjectives; nothing is checkable. |
| 2 | Some numbers buried inside long sentences. |
| 3 | Numbers present; weight uniform. |
| 4 | Numbers present and emphasised; examples named. |
| 5 | Each claim has one piece of evidence next to it; emphasis only on the number; source in a footnote. |

Good signals: Figures with units; Key number in bold or accent; A source or footnote

Bad signals: 'Significant growth' with no figure; All text one weight; Unsourced claims

Checks: Bullets with a number >= ~50% when the brief supplies figures; Bold/accent used on numbers only; Source or note line when data is cited

Sources: Barbara Minto, The Pyramid Principle: support claims with evidence (secondary); Storytelling with Data: 'the power of simple text' https://www.storytellingwithdata.com/blog/2012/06/power-of-simple-text (returned by search; not opened)

#### T-TEXT-05 Text-only slide earns its form  (weight 3, -)

Is plain text the right form, or should the content be a chart, table or diagram?

| Level | What the grader sees |
|---|---|
| 1 | Hidden structure makes the text misleading (steps listed as unordered bullets, with the order lost). |
| 2 | Structured content (steps, comparison, numbers over time) left as prose. |
| 3 | Text suits the content; a visual would help a little. |
| 4 | Text is the best form; layout supports it (key message band, spacing). |
| 5 | Text form is deliberate; a small visual or number emphasis amplifies it without a different form. |

Good signals: Argument, narrative or a decision rationale; A bullet list has no hidden structure (steps, comparison, trend); Visual treatment where structure exists

Bad signals: Five bullets that are steps in a process; A bulleted list of numbers over time; Two options described in prose

Checks: Bullets do not form a process, comparison or time series; Sequence words (first, then) absent unless numbered

Sources: Gene Zelazny, Say It with Charts: pick the form by the relationship in the message (https://www.oreilly.com/library/view/the-say-it/9780071474702/ch01.html listing); Cole Nussbaumer Knaflic, Storytelling with Data: 'the power of simple text' (blog above; not opened)

## Topic: Matrix, quadrant and prioritisation (`matrix-quadrant`)

Two-axis positioning (2x2, bubble, priority matrix), grid matrices (capability x product), SWOT, Eisenhower, effort-impact.

Frequency: Low in the repo evidence: examples 23 ('施策の優先度'), 29 (Venn Desirable x Feasible x Viable), 16 and 20 (施策 matrices); briefs 0 of 108; about 2-3% of slides, but common in consulting decks generally.

| id | name | weight | gate |
|---|---|---|---|
| T-MAT-01 | Axes are named and meaningful | 5 | yes |
| T-MAT-02 | Position carries information | 5 | yes |
| T-MAT-03 | Quadrants named and actionable | 4 |  |
| T-MAT-04 | Item count and label discipline | 3 |  |

#### T-MAT-01 Axes are named and meaningful  (weight 5, **gate**)

Are both axes labelled with a dimension and direction (low to high), and are the dimensions independent and decision-relevant?

| Level | What the grader sees |
|---|---|
| 1 | Axes unlabelled or meaning unclear; a position cannot be interpreted. |
| 2 | Axes named but direction unclear, or the dimensions correlate so that positions are arbitrary. |
| 3 | Axes named with direction. |
| 4 | Axes named with direction; dimensions independent; the favourable corner is clear. |
| 5 | Axes defined by a one-line criterion; the favourable corner is stated; the title states what to do about it. |

Good signals: Axis titles with 'low' and 'high' ends; Dimensions that split the items (e.g. impact vs effort); One axis sentence in the title or caption

Bad signals: Unlabelled axes; Axes that are the same thing (size vs revenue); Direction unclear (is up good?)

Checks: Both axes have a title; Low/high or arrow marks present; Favourable corner is stated or obvious

Sources: Slidemagic, 'Picking the 2x2 axes': place the best option top right; flipping axes can clarify; https://slidemagic.squarespace.com/blog/2019/9/3/picking-the-2x2-axes (returned by search; not opened); SlideModel and PrepLounge guides on 2x2 matrices (practitioner, search results)

#### T-MAT-02 Position carries information  (weight 5, **gate**)

Is each item placed by its value on the axes (not just dropped in a quadrant), with no overlaps?

| Level | What the grader sees |
|---|---|
| 1 | Positions contradict the data or labels, or items overlap so much that they cannot be read. |
| 2 | Positions are decorative; overlaps; items cluster. |
| 3 | Positions approximate the values; labels readable. |
| 4 | Positions are consistent with stated values; labels clear; bubble size explained. |
| 5 | Positions are quantitatively placed or rank-ordered; the claim (what goes where) is verifiable from the slide. |

Good signals: Items at different positions inside a quadrant; Bubble size, if used, has a stated meaning; No overlap or hidden labels

Bad signals: All items stacked in a corner; Overlapping bubbles; Item positions contradict text

Checks: No label overlaps; An item's quadrant matches the text's description; Bubble size has a legend if used

Sources: Slidemagic and PrepLounge 2x2 practitioner guides (search results; positions should reflect the data); Edward Tufte, The Visual Display of Quantitative Information: position encodes data (secondary)

#### T-MAT-03 Quadrants named and actionable  (weight 4, -)

Does each quadrant have a short name or action (invest, fix, drop) so the position implies a decision?

| Level | What the grader sees |
|---|---|
| 1 | Quadrants have no meaning or conflicting meanings. |
| 2 | Quadrants unlabelled; the reader invents the meaning. |
| 3 | Quadrants named. |
| 4 | Quadrants named with actions; priority quadrant emphasised. |
| 5 | Each quadrant has a name and an action, and the highlighted quadrant matches the recommendation. |

Good signals: Quadrant labels in the corners; Action verbs; Shading only for the priority quadrant

Bad signals: Four empty boxes; Quadrant names that repeat axis labels; Colour with no meaning

Checks: Quadrant label present for each region; Highlight on <= 1-2 quadrants; Quadrant action matches the recommendation text

Sources: Slidemodel guidance on stating each quadrant and the supporting decision (practitioner; https://slidemodel.com/templates/2x2-matrix-quadrants-powerpoint-template, search result); bench/reference/diagram-design/example-quadrant.png (repo example; quadrant primitive)

#### T-MAT-04 Item count and label discipline  (weight 3, -)

Is the number of items small enough to label directly (about 5-12), with short labels placed beside the marks?

| Level | What the grader sees |
|---|---|
| 1 | Labels overlap so items cannot be identified. |
| 2 | 20+ items, tiny labels. |
| 3 | 12-15 items; labels readable. |
| 4 | 5-12 items; direct labels. |
| 5 | Items are curated to the decision; the 2-3 key items are called out. |

Good signals: 5-12 items; Direct labels; Numbered markers with a key if the count is higher

Bad signals: 25 dots with a legend; Labels long enough to cross quadrants

Checks: Item count <= ~12; Label text <= ~3 words; No label overlaps

Sources: EU Data Visualisation Guide, direct labelling (returned by search; https://data.europa.eu/apps/data-visualisation-guide/direct-labelling); World Bank data viz style guide (labels vs legends; search result)

## Topic: Dense Japanese business slide (overlay) (`dense-ja-business`)

A slide in the Japanese consulting / 稟議 style: many boxes, 10-12pt text, tables, arrows, footnotes and a key message line. Added on top of the primary topic (table, comparison, process, etc.).

Frequency: Dense JP business look is requested in b04-b06 (3 briefs), lengthbench t1-t4, examples 02, 04, 05, 06, 07, 08, 11, 16, 20, 23, 25 and bench/corpus/jp-dense, jp-kpi (about 20 percent of decks in the repo; about 45 of 154 example slides).

| id | name | weight | gate |
|---|---|---|---|
| T-JA-01 | Structured density (grouping and grid) | 5 |  |
| T-JA-02 | Key message line and conclusion-first | 5 |  |
| T-JA-03 | CJK text fit and line breaking | 5 | yes |
| T-JA-04 | Small text stays legible | 4 | yes |
| T-JA-05 | Footnotes, sources and notes | 3 |  |
| T-JA-06 | Color restraint and emphasis in dense slides | 3 |  |

#### T-JA-01 Structured density (grouping and grid)  (weight 5, -)

Is the density organised by a grid, group boxes and headings so the eye can scan, rather than a pile of equal-weight text?

| Level | What the grader sees |
|---|---|
| 1 | Elements overlap or overflow; no grid. |
| 2 | Elements are readable but the grid is irregular; groups unclear. |
| 3 | Grid present; groups visible; hierarchy moderate. |
| 4 | Grid, headings and groups give three scan levels (message, group, detail). |
| 5 | A reader finds any item in seconds; gutters equal; the group boundaries match the logic of the content. |

Good signals: Clear column/row grid; Group headings; Even gutters; Whitespace between groups, not inside them

Bad signals: Text blocks floating; Uneven margins; Every element the same weight; Whitespace ragged

Checks: Block edges align to a common grid; Gutter variance small; No overlapping shapes; Heading per group

Sources: Japanese 資料作成 guides: ワンスライド・ワンメッセージ with 3-4 colours max; https://biz.moneyforward.com/work-efficiency/basic/22712/ and https://webtan.impress.co.jp/e/2019/08/07/32999 (returned by search; general, not specific to dense slides); Garr Reynolds, Presentation Zen: density is allowed in documents if signal-to-noise is high (inference; Reynolds distinguishes slideuments, wording unverified); bench/reference/diagram-design/style-guide.md: 4px grid (repo; read)

#### T-JA-02 Key message line and conclusion-first  (weight 5, -)

Is there a one-sentence Japanese key message (リード) under the title that states the so-what, and does the body support it?

| Level | What the grader sees |
|---|---|
| 1 | No message anywhere; the reader cannot tell the point. |
| 2 | Message exists only inside the body text or only as a topic title. |
| 3 | Lead line exists but is generic or restates the title. |
| 4 | Lead line states a conclusion; body supports it. |
| 5 | Title + lead + group headings form a readable top-down reading (read only these and the argument holds). |

Good signals: A lead sentence ending with a conclusion (である/する); Title is a topic or claim; lead gives the claim; Body groups support the lead

Bad signals: Lead restates the title; No lead on a dense slide; Lead longer than 2 lines

Checks: Lead line present on dense slides; Lead <= 2 lines; Lead contains a conclusion or number; Group headings alone tell the argument

Sources: Barbara Minto, The Pyramid Principle (answer first; via https://www.think-cell.com/en/resources/content-hub/using-the-pyramid-principle-to-build-better-powerpoint-presentations, secondary); Japanese consulting practice: key message then support (https://webtan.impress.co.jp/e/2019/08/07/32999; returned by search; not opened)

#### T-JA-03 CJK text fit and line breaking  (weight 5, **gate**)

Do Japanese texts fit their boxes at the stated size, with natural line breaks and no orphan characters or broken numbers?

| Level | What the grader sees |
|---|---|
| 1 | Text overflows or is clipped; digits and units split across lines. |
| 2 | Orphan single characters or punctuation at line starts in several boxes; text shrunk below the floor. |
| 3 | Fits, with an occasional orphan or awkward break. |
| 4 | Fits at the deck size; breaks at phrase boundaries; units attach to numbers. |
| 5 | Line breaks follow phrasing; no orphans; box padding even; width budget matches 1em per full-width character. |

Good signals: No overflow; lines break at phrase boundaries; Numbers with units kept together (28万円); Full-width punctuation not at line starts (kinsoku); Latin and digits do not break mid-token

Bad signals: One character alone on the last line; Number split from its unit; Text clipped or overflowing the box; Tiny text to force fit

Checks: No overflow (text height <= box height); No last line with a single full-width character; No line starting with 、。）」; Number and unit on one line

Sources: bench/reference/diagram-design/style-guide.md: width budget of 1em per wide character, 12px floor for CJK (repo; read); W3C JLReq (Requirements for Japanese Text Layout), line-start/line-end prohibition (kinsoku): https://www.w3.org/TR/jlreq/ (known document; not opened in this session); CLAUDE.md of SlideMark: <a:ea> font and 1em width test requirement (repo)

#### T-JA-04 Small text stays legible  (weight 4, **gate**)

Is the smallest text readable (about 10pt or larger for body, footnotes allowed smaller) with enough contrast and a weight that holds in Japanese?

| Level | What the grader sees |
|---|---|
| 1 | Body text below ~8pt or contrast under 3:1; not readable on a projected slide. |
| 2 | Body text 8-9pt or contrast 3-4.5:1 on small text. |
| 3 | Body text 10pt; contrast >= 4.5:1; footnote small but legible. |
| 4 | Body 10-12pt, headings 12-14pt with a clear size step; contrast >= 4.5:1. |
| 5 | Level 4 plus consistent size roles across slides; minimum size is never used for key facts. |

Good signals: Body text >= 10pt; Footnotes about 8-9pt in a muted but passing colour; Bold used for heads; light colour avoided for small text; Gothic (sans) font

Bad signals: Body at 8pt; Grey text on grey fill below 4.5:1; Thin weights at small size; Mixed fonts

Checks: Min body font size >= 10pt (dense) / 12pt (normal); Text contrast >= 4.5:1; Key facts are not in the smallest size; Hiragino/Meiryo/Yu Gothic or equivalent sans

Sources: W3C WCAG 2.2 SC 1.4.3 Contrast (Minimum) 4.5:1; https://www.w3.org/WAI/WCAG22/Understanding/contrast-minimum.html (not opened); bench/reference/diagram-design/style-guide.md: Hangul/Han floor of 12px; contrast contract (repo; read); Japanese guide: font count 2 max; https://biz.moneyforward.com/work-efficiency/basic/22712/ (returned by search)

#### T-JA-05 Footnotes, sources and notes  (weight 3, -)

Do dense data and claims carry a footnote line (注、出所、単位) in a fixed position?

| Level | What the grader sees |
|---|---|
| 1 | Data shown with no unit, period or source and cannot be interpreted. |
| 2 | Unit present but no source for estimates. |
| 3 | Unit and source appear in some form. |
| 4 | Unit, period and source in a consistent, legible place. |
| 5 | Footnotes are numbered to the claims they support; positions are the same on every slide. |

Good signals: 注記 and 出所 line at the bottom, left aligned; Unit stated at the top right of a chart or table (単位: 百万円); Consistent position across slides

Bad signals: Estimates without a note; Source missing; Footnote overlapping the content

Checks: Unit shown for numbers; Source/note line present when the brief supplies one; Footnote does not overlap content; Same position across the deck

Sources: Common 注/出所 convention in Japanese business documents: no primary guide checked; unverified; Dona Wong, WSJ Guide to Information Graphics: label sources (unverified); Urban Institute Data Visualization Style Guide: sources and notes under charts; https://urbaninstitute.github.io/graphics-styleguide (page exists; passage not read)

#### T-JA-06 Color restraint and emphasis in dense slides  (weight 3, -)

Does the dense slide stay within 3-4 colours with one emphasis colour, so density does not become noise?

| Level | What the grader sees |
|---|---|
| 1 | Colours compete and make text unreadable. |
| 2 | 6+ colours without meaning. |
| 3 | 4-5 colours; mostly consistent. |
| 4 | 3-4 colours with one accent; semantic colours are consistent. |
| 5 | Colour only encodes meaning, and the slide is still readable in greyscale. |

Good signals: Navy/grey base plus one accent; Semantic colours (red for risk) used sparingly; Emphasis through bold and rules before colour

Bad signals: 6+ fill colours; Coloured text on coloured boxes; Every box has a coloured header

Checks: Distinct hues <= 4 (excluding neutrals); Semantic colours consistent with other slides; Greyscale preview remains readable

Sources: Japanese guide: 3-4 colours max, 2 fonts max; https://biz.moneyforward.com/work-efficiency/basic/22712/ (returned by search); bench/reference/diagram-design/style-guide.md: one accent, no rainbow palette (repo; read); Tufte, The Visual Display of Quantitative Information: restrained colour (secondary)

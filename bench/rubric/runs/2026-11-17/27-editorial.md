# Design report: deck A  (rubric v1, judge claude-opus-5-5, R=3 runs, 2026-11-17)

## Summary
Deck **64** (63-66)  Acceptable  ·  Slides 66 (bottom quartile 59)  ·  Deck KPIs 60
Gates: slide 3 capped at 59 (T-SYS-01=2); slide 4 capped at 59 (G-05=2). Unstable KPIs: none.

## Deck KPIs
| id | name | w | s (runs) | evidence (+/-) |
|---|---|---|---|---|
| D-01 | Narrative and storyline | 5 | 3 (3,3,3) | + all five content titles are claims (gateway path, fraud routing, orders grew, gateway cost +12%, three measures halve latency); - no answer-first summary; the plan appears only on the last slide; slide 3 (fraud routing) is weakly tied to the argument |
| D-02 | Consistency as one system | 4 | 4 (3,4,4) | + eyebrow, title, footer and page number at identical positions; same accent treatment for focal items on diagrams, chart, table; - slide 6 switches title face for Japanese |
| D-03 | Variety of form | 3 | 4 (4,4,5) | + forms follow content: cover, architecture diagram, decision flow, column chart, table+bar chart, cards+table; - slides 2 and 3 are both node diagrams in a row |
| D-04 | Pacing and framing slides | 3 | 3 (3,2,3) | + cover with topic, owner and date; density alternates between diagrams and data slides; - no closing or ask slide; the ask ('cap its traffic before Q4') sits inside slide 5 |
| D-05 | Fit to purpose and audience | 3 | 3 (3,3,3) | + slides 2-5 suit a presented engineering review; - slide 6 switches to a dense Japanese reading-deck register in an otherwise English deck |

## Slides
| # | topic | general | topic | raw | cap | score (range) | band | weakest KPIs (loss) |
|---|---|---|---|---|---|---|---|---|
| 1 | Framing slides (cover, agenda, section, closing, decision) | 74 | 69 | 72 | - | 72 (72-76) | Good | G-05 (2.5), T-FRAME-03 (2.0), G-08 (1.5) |
| 2 | System, architecture and concept diagram | 69 | 80 | 73 | - | 73 (68-73) | Acceptable / Good (borderline) | G-06 (2.5), G-05 (2.5), G-07 (1.5) |
| 3 | System, architecture and concept diagram | 64 | 54 | 60 | 59 (T-SYS-01=2) | 59 (56-63) | Acceptable | T-SYS-01 (3.8), T-SYS-02 (3.0), G-03 (2.5) |
| 4 | Data chart | 58 | 67 | 62 | 59 (G-05=2) | 59 (59-59) | Acceptable | G-05 (3.8), G-09 (2.5), G-03 (2.5) |
| 5 | Data table | 82 | 80 | 81 | - | 81 (80-83) | Good | T-TABLE-05 (2.0), T-TABLE-02 (1.2), G-12 (1.2) |
| 6 | Data table + Dense Japanese business slide (overlay) | 65 | 69 | 67 | - | 67 (67-69) | Acceptable | T-TABLE-02 (2.5), T-JA-02 (2.5), G-12 (2.5) |

## Top fixes (gates and soft gates first, then by weighted loss)
1. Slide 3, T-SYS-01 Structure shows the right relationship (level 2, loss 3.8): decision outputs unlabelled; a data flow to a key vault mixes meanings (secret storage vs routing)
2. Slide 4, G-05 White space and density (level 2, loss 3.8): area under the Reading card (x 752-1232, y 285-680) is a large dead block, about 40% of the body
3. Slide 3, T-SYS-02 Focal element and hierarchy (level 2, loss 3.0): focal accent on Reports while the title's subject is the fraud check
4. Slide 1, G-05 White space and density (level 3, loss 2.5): lower half (y 380-720) and right third empty; text block sits high, space looks left over rather than composed
5. Slide 2, G-05 White space and density (level 3, loss 2.5): diagram occupies about half the body width; empty bands left (x 48-270), right (x 1010-1232) and above (y 170-260)

## Evidence lines
slide | KPI | s (runs) | sign | what is seen
S1 | G-01 | 4 (4,4,4) | + | cover states topic, scope (architecture, throughput, cost), owner and date; nothing extra
S1 | G-01 | 4 (4,4,4) | - | title is a topic label, acceptable only because this is a cover
S1 | G-02 | 4 (4,4,4) | + | type-only cover: eyebrow, large title, subtitle line is the right form for framing
S1 | G-03 | 4 (5,4,4) | + | large serif title wins first look; eyebrow and subtitle clearly secondary
S1 | G-04 | 4 (4,4,4) | + | eyebrow, title and subtitle share one left edge at the deck's 48px margin
S1 | G-04 | 4 (4,4,4) | - | block placed above centre with no relation to other elements
S1 | G-05 | 3 (3,3,3) | + | sparse cover, generous margins
S1 | G-05 | 3 (3,3,3) | - | lower half (y 380-720) and right third empty; text block sits high, space looks left over rather than composed
S1 | G-06 | 4  | + | three sizes with large ratios (title ~60pt, subtitle ~21pt, eyebrow ~8pt), each one role
S1 | G-06 | 4  | - | eyebrow is very small (about 8pt) letter-spaced mono
S1 | G-07 | 4 (5,4,4) | + | minimal words; each line adds topic, scope or owner/date
S1 | G-08 | 3 (3,3,3) | + | neutral navy/slate on light grey, coherent
S1 | G-08 | 3 (3,3,3) | - | no accent; colour carries no meaning (acceptable on a cover)
S1 | G-09 | 4  | + | dark navy title on light grey well above 7:1; subtitle slate comfortably readable
S1 | G-09 | 4  | - | small grey eyebrow is the weakest contrast
S1 | G-10 | 4 (5,4,4) | + | no decoration; emphasis only through title size
S1 | G-11 | 4 (5,4,4) | + | title readable at thumbnail size; topic clear at a glance
S1 | G-12 | 5 (5,5,5) | + | no defects; text clean, nothing clipped
S1 | G-13 | 4 (4,4,4) | + | editorial system: serif display title, mono eyebrow, sans subtitle; restrained and consistent with later slides
S1 | G-14 | N/A  | ? | (no evidence given)
S1 | T-FRAME-01 | 4 (4,4,4) | + | title >= 2.5x subtitle; three text blocks; no bullets
S1 | T-FRAME-01 | 4 (4,4,4) | - | whitespace below is large and not clearly deliberate
S1 | T-FRAME-02 | 4 (4,4,4) | + | title, subject line, team, quarter and month present in clear order
S1 | T-FRAME-03 | 3 (3,3,3) | + | subtitle lists three topics in deck order (architecture, throughput, cost)
S1 | T-FRAME-03 | 3 (3,3,3) | - | no agenda or summary; acceptable for a 6-slide deck
S1 | T-FRAME-04 | 4 (4,4,4) | + | single anchor (big serif title); no decorative shapes; matches deck typography
S2 | G-01 | 4 (4,4,4) | + | title is a claim; diagram shows the only path from client goes through the highlighted API gateway
S2 | G-01 | 4 (4,4,4) | - | subtitle 'One focal service; the rest keeps to the quiet roles' describes the styling, not the content (off-message)
S2 | G-02 | 4 (4,4,4) | + | tiered architecture (CLIENT / PLATFORM rows) with flow arrows fits a structural claim
S2 | G-02 | 4 (4,4,4) | - | only one client shown, so 'every request' is asserted rather than demonstrated
S2 | G-03 | 4 (4,4,4) | + | title first, then the accent-outlined API gateway; other nodes quiet grey
S2 | G-03 | 4 (4,4,4) | - | diagram is small relative to the slide, so the focal node is modest in size
S2 | G-04 | 4 (4,3,4) | + | platform nodes equal size on one row with equal ~42px gaps; tier labels share a left edge
S2 | G-04 | 4 (4,3,4) | - | Web client sits above Postgres, not the gateway, forcing an elbow connector; diagram centred while title is left-aligned
S2 | G-05 | 3 (3,3,3) | + | legend band at bottom fills the foot area
S2 | G-05 | 3 (3,3,3) | - | diagram occupies about half the body width; empty bands left (x 48-270), right (x 1010-1232) and above (y 170-260)
S2 | G-06 | 3  | + | node names bold ~13.5pt, sublabels mono ~10pt, roles consistent
S2 | G-06 | 3  | - | tier labels and node tags ~8pt; six or so distinct sizes
S2 | G-07 | 3 (3,3,3) | + | node labels are terse (auth · limits, orders · users)
S2 | G-07 | 3 (3,3,3) | - | subtitle is filler meta-commentary; tags WEB/API/DB/OBJ repeat node names
S2 | G-08 | 4 (4,4,4) | + | neutral base plus one orange accent for the focal node; legend maps fills to roles (focal, store, external, optional)
S2 | G-09 | 4  | + | dark labels on light fills; node borders and arrows clearly visible
S2 | G-09 | 4  | - | small grey tags and dashed border of the optional node are lower contrast
S2 | G-10 | 4 (4,4,4) | + | single accent on the gateway, the item in the title
S2 | G-10 | 4 (4,4,4) | - | mono tag badges in every node add decoration with little meaning
S2 | G-11 | 4 (4,4,4) | + | title plus orange node give the point in about three seconds
S2 | G-11 | 4 (4,4,4) | - | sublabels vanish at half size
S2 | G-12 | 4 (4,4,4) | + | arrows attach to box edges; no overlaps or clipping
S2 | G-13 | 4 (4,4,4) | + | one family: small radius, thin strokes, mono tags, legend style consistent
S2 | G-14 | N/A  | ? | (no evidence given)
S2 | T-SYS-01 | 4 (4,4,4) | + | tiers labelled; arrows mean flow per legend; one relationship type
S2 | T-SYS-01 | 4 (4,4,4) | - | single client makes the 'every request' claim thin
S2 | T-SYS-02 | 5 (5,5,4) | + | one focal node (gateway, named in title); store, external and optional nodes in three distinct quiet treatments explained by legend
S2 | T-SYS-03 | 4 (4,4,3) | + | names readable and padded inside boxes
S2 | T-SYS-03 | 4 (4,4,3) | - | tags and tier labels around 8pt
S2 | T-SYS-04 | 4 (4,4,4) | + | orthogonal connectors, no crossings or shared segments
S2 | T-SYS-04 | 4 (4,4,4) | - | client-to-gateway connector takes an avoidable elbow
S2 | T-SYS-05 | 4 (4,4,4) | + | four nodes, exactly what the claim needs; optional and external styled distinctly
S3 | G-01 | 3 (2,3,3) | + | title is a claim sentence and the diamond sits at the branch point
S3 | G-01 | 3 (2,3,3) | - | branches carry no conditions, so how the check decides is not shown
S3 | G-01 | 3 (2,3,3) | - | accent sits on Reports, not on the fraud check the title names
S3 | G-02 | 3 (3,3,4) | + | decision diamond with branches is a fitting form for routing
S3 | G-02 | 3 (3,3,4) | - | branch conditions missing, so the structure of the decision is not visible
S3 | G-03 | 3 (2,3,3) | + | title first; large diamond is central
S3 | G-03 | 3 (2,3,3) | - | rust Reports node competes with the diamond for the first look
S3 | G-04 | 4 (4,4,4) | + | Orders DB, Stripe and Key vault share one column and width with equal vertical spacing; main row aligned on one centre line
S3 | G-05 | 4 (4,4,4) | + | diagram spans most of the body width and height; balanced around the centre row
S3 | G-06 | 4  | + | node labels one bold size (~13pt); legend and eyebrow smaller; title one line
S3 | G-07 | 4 (4,4,4) | + | one- or two-word node labels; no repetition
S3 | G-08 | 3 (3,3,3) | + | neutral palette, one accent, legend maps fills to roles
S3 | G-08 | 3 (3,3,3) | - | accent meaning 'focal' is spent on an item the title does not name
S3 | G-09 | 4  | + | dark bold labels on light fills; connectors clearly visible
S3 | G-09 | 4  | - | external Stripe fill barely differs from background (border carries it)
S3 | G-10 | 3 (2,3,3) | + | single accent, minimal decoration
S3 | G-10 | 3 (2,3,3) | - | the emphasised node is not the message
S3 | G-11 | 3 (3,3,3) | + | topic (routing after fraud check) clear at a glance
S3 | G-11 | 3 (3,3,3) | - | eye lands on Reports first; why data goes where needs reading the legend
S3 | G-12 | 4 (4,4,4) | + | connectors attach to vertices and edges cleanly; no overlaps or clipping
S3 | G-13 | 4 (4,4,4) | + | same node, stroke, legend and type system as slide 2
S3 | G-14 | N/A  | ? | (no evidence given)
S3 | T-SYS-01 | 2 (2,2,3) | + | arrows denote flow per legend
S3 | T-SYS-01 | 2 (2,2,3) | - | decision outputs unlabelled; a data flow to a key vault mixes meanings (secret storage vs routing)
S3 | T-SYS-02 | 2 (2,3,2) | - | focal accent on Reports while the title's subject is the fraud check
S3 | T-SYS-03 | 4 (4,4,4) | + | all labels readable, padded and inside their shapes
S3 | T-SYS-04 | 4 (4,4,4) | + | orthogonal connectors, distinct attach points, no crossings
S3 | T-SYS-05 | 4 (4,4,4) | + | six nodes; store, external, optional and input styled distinctly
S4 | G-01 | 3 (3,3,3) | + | title claim matches rising bars 120 -> 150 -> 240 -> 260; 'Q3 doubled Q1' is correct
S4 | G-01 | 3 (3,3,3) | - | refund series and 'growth came from repeat buyers' (not shown anywhere) add a second message
S4 | G-02 | 3 (3,3,3) | + | column chart for quarters plus a reading card is a valid composite
S4 | G-02 | 3 (3,3,3) | - | right column mostly empty; refund rate could have been a KPI strip filling it
S4 | G-03 | 3 (3,3,3) | + | title first, orange annotation draws the eye to Q3
S4 | G-03 | 3 (3,3,3) | - | highlighted Q3 bar is lighter than the dark Q4 bar, so the heaviest mark is not the focal one
S4 | G-04 | 3 (3,3,3) | + | chart and card share the top band; margins equal
S4 | G-04 | 3 (3,3,3) | - | card floats top-right with no bottom anchor; chart title centred while card heading left-aligned
S4 | G-05 | 2 (2,2,2) | - | area under the Reading card (x 752-1232, y 285-680) is a large dead block, about 40% of the body
S4 | G-06 | 4  | + | title, chart title, labels and bullets on a clear scale; body comfortably large
S4 | G-07 | 4 (4,4,4) | + | two short bullets with numbers; unit (k) in chart title
S4 | G-08 | 4 (4,3,4) | + | navy and slate series, one orange accent for the highlight and its annotation
S4 | G-09 | 3  | + | labels and text dark on light
S4 | G-09 | 3  | - | pale pink fill of the Q3 bar is weak against the grey background; outline carries it
S4 | G-10 | 3 (3,3,3) | + | emphasis limited to Q3 bar, annotation and one bold phrase
S4 | G-10 | 3 (3,3,3) | - | bold 'repeat buyers' emphasises an unsupported claim; Q3 is not the title's point
S4 | G-11 | 4 (4,3,4) | + | rising bars and title give 'orders grew' within three seconds
S4 | G-12 | 4 (4,4,4) | + | labels clear of bars; nothing clipped
S4 | G-13 | 4 (4,4,4) | + | highlight-by-outline treatment matches the deck's focal style
S4 | G-14 | N/A  | ? | (no evidence given)
S4 | T-CHART-01 | 4 (4,4,4) | + | clustered columns for quarterly values, natural time order
S4 | T-CHART-01 | 4 (4,4,4) | - | refunds on the same axis are tiny bars of little use
S4 | T-CHART-02 | 4 (4,4,4) | + | bars start at a common zero baseline; heights proportional to values
S4 | T-CHART-03 | 3 (4,3,3) | + | value labels on every bar; unit stated
S4 | T-CHART-03 | 3 (4,3,3) | - | series identified only through a bottom legend
S4 | T-CHART-04 | 3 (3,3,3) | + | one accent bar with annotation
S4 | T-CHART-04 | 3 (3,3,3) | - | highlight is on Q3 while the title claims growth across all quarters
S4 | T-CHART-05 | 4 (4,4,4) | + | no gridlines, border or effects; two series only
S4 | T-CHART-06 | 4 (4,4,4) | + | title states the direction; unit and quarters on the chart
S4 | T-CHART-06 | 4 (4,4,4) | - | no quantity in the title and no source or year
S5 | G-01 | 5 (5,5,4) | + | action title with number; table row, bar and bottom line all prove it
S5 | G-01 | 5 (5,5,4) | + | 28% share checks out (4,200 of 15,000) and Gateway is the only line above +5%
S5 | G-02 | 5 (5,5,5) | + | table for exact values plus diverging bar chart of the change column plus takeaway band: both faces shown
S5 | G-03 | 4 (4,4,4) | + | highlighted Gateway row and bar are the focal pair; other rows quiet
S5 | G-03 | 4 (4,4,4) | - | bold bottom band competes slightly for attention
S5 | G-04 | 4 (4,4,4) | + | bars align with their table rows; table and band share the left margin
S5 | G-04 | 4 (4,4,4) | - | band text centred while all other text is left/right aligned
S5 | G-05 | 4 (4,4,4) | + | body filled and balanced between table and chart
S5 | G-05 | 4 (4,4,4) | - | table rows are tall, slightly stretched to fill height
S5 | G-06 | 4  | + | title ~36pt, table and chart text ~13pt, consistent per role
S5 | G-07 | 4 (4,4,4) | + | numbers with units; bottom line adds the 28% share and the action
S5 | G-07 | 4 (4,4,4) | - | Owner column not needed for the message
S5 | G-08 | 5 (5,4,5) | + | one accent used only for Gateway in table and chart; backed by bold and position
S5 | G-09 | 4  | + | dark text on light; bars clearly separated from background
S5 | G-09 | 4  | - | pale fill of the Gateway bar relies on its outline
S5 | G-10 | 4 (4,4,5) | + | emphasis only on the Gateway item and the takeaway line
S5 | G-11 | 5 (5,4,5) | + | longest highlighted bar and title deliver the point in one look
S5 | G-12 | 4 (4,4,4) | + | no clipping; labels clear of bars
S5 | G-12 | 4 (4,4,4) | - | '-8' label sits close to the 'Search' category label
S5 | G-13 | 4 (4,4,5) | + | table rules, accent outline and band follow the deck system
S5 | G-14 | N/A  | ? | (no evidence given)
S5 | T-TABLE-01 | 5 (5,5,5) | + | 4 rows x 4 columns, short cells, readable; paired with a chart for the pattern
S5 | T-TABLE-02 | 4 (4,4,4) | + | numeric columns and their headers right-aligned; thousands separators and +/- signs
S5 | T-TABLE-02 | 4 (4,4,4) | - | $ repeated in each cell; no total row
S5 | T-TABLE-03 | 4 (5,4,4) | + | thin horizontal rules, no verticals, bold header over a dark rule
S5 | T-TABLE-04 | 5 (5,5,5) | + | one highlighted row in bold that answers the title; bar chart shows the ranking
S5 | T-TABLE-05 | 3 (3,3,3) | + | every column has a header; $ and % units present
S5 | T-TABLE-05 | 3 (3,3,3) | - | change period (vs month? quarter?) and source not stated
S6 | G-01 | 4 (4,4,4) | + | action title; 施策 card lists the three measures and the table shows 2.8 s -> 1.4 s (half)
S6 | G-01 | 4 (4,4,4) | - | 管理 card (Vault keys, permission reviews) does not support the latency message
S6 | G-02 | 4 (4,4,4) | + | situation/issue/action cards plus a metric table: argument and numbers both shown
S6 | G-02 | 4 (4,4,4) | - | 現状 -> 課題 -> 施策 order shown by position only, no arrows
S6 | G-03 | 4 (4,4,4) | + | title, then accent 施策 card and highlighted latency row; supporting cards quiet
S6 | G-04 | 4 (3,4,4) | + | four equal cards on the table's outer edges with equal gutters; bullet rows align across cards
S6 | G-05 | 3 (4,3,3) | + | margins even; dense but structured
S6 | G-05 | 3 (4,3,3) | - | cards are taller than their text, leaving empty lower halves
S6 | G-06 | 3  | + | CJK renders correctly; body ~12.5pt, footnote ~9pt
S6 | G-06 | 3  | - | card headings same size as bullets; stray spaces ('遅延  2.8 秒', '（ 2027 年', '（ 2026 年'); title mixes serif '3' with light Japanese sans
S6 | G-07 | 3 (3,3,3) | + | short fragments with numbers and units
S6 | G-07 | 3 (3,3,3) | - | lead line largely restates the title; the three measures appear twice (card and table column)
S6 | G-08 | 4 (4,4,4) | + | neutral base with one accent for the measures card and the key metric row
S6 | G-09 | 4  | + | dark text on white cards and light background; footnote small but readable
S6 | G-10 | 4 (4,4,4) | + | two highlights, both on the measures and the latency target
S6 | G-11 | 4 (4,4,4) | + | title plus card headers and highlighted row give the point
S6 | G-11 | 4 (4,4,4) | - | bullet detail unreadable at half size
S6 | G-12 | 3 (3,3,3) | + | no overflow or clipping
S6 | G-12 | 3 (3,3,3) | - | spacing glitches around full-width parentheses and a double space before 2.8
S6 | G-13 | 3 (3,4,3) | + | cards, rules and accent follow the deck system
S6 | G-13 | 3 (3,4,3) | - | title type changes character (light Japanese sans next to serif numeral) versus the English slides
S6 | G-14 | N/A  | ? | (no evidence given)
S6 | T-JA-01 | 4 (4,4,4) | + | four-card row and table on one grid with group headings
S6 | T-JA-01 | 4 (4,4,4) | - | table columns not on the card grid
S6 | T-JA-02 | 3 (3,4,3) | + | lead line present under the title
S6 | T-JA-02 | 3 (3,4,3) | - | lead restates the title rather than adding the so-what
S6 | T-JA-03 | 4 (4,4,4) | + | all text fits; no orphans; numbers stay with units
S6 | T-JA-03 | 4 (4,4,4) | - | extra spaces inside parentheses and before 2.8
S6 | T-JA-04 | 4 (3,4,4) | + | body about 12 pt, headings bold larger; footnote muted but passing
S6 | T-JA-05 | 4 (4,4,4) | + | ※ 出所 line bottom-left with date and p95 definition; units stated
S6 | T-JA-06 | 4 (4,4,5) | + | navy/grey base plus one accent; emphasis also by bold
S6 | T-TABLE-01 | 4 (4,4,4) | + | 3 rows x 4 columns, short cells, readable
S6 | T-TABLE-02 | 3 (3,3,3) | + | units consistent within each row (秒, 時間, 系統)
S6 | T-TABLE-02 | 3 (3,3,3) | - | numbers left-aligned with units in every cell
S6 | T-TABLE-03 | 4 (4,4,4) | + | thin horizontal rules, bold header with strong rule, no vertical lines
S6 | T-TABLE-04 | 4 (5,4,4) | + | latency row filled and bold, matching the title
S6 | T-TABLE-05 | 4 (4,4,5) | + | headers, target date (2027年3月), source and p95 note in footnote

## Measured facts
- slide 1: title 59.99 pt; min body 22 pt (floor 14); min label 10 pt (floor 8); min text contrast 5.3:1 ('Eyebrow' 'ENGINEERING · Q3 2')
- slide 2: title 38 pt; min node 13 pt (floor 10); min label 8 pt (floor 8); min footnote 12 pt (floor 8); min text contrast 4.5:1 ('Arch tag Web client' 'WEB'); min non-text contrast 3.3:1 (swatch 'Legend external swatch'); empty body 33% (rows 33%, columns 0%; weak >= 40%)
- slide 3: title 34.2 pt; min node 12 pt (floor 10); min label 9 pt (floor 8); min footnote 12 pt (floor 8); min text contrast 5.3:1 ('Eyebrow' 'PLATFORM REVIEW'); min non-text contrast 3.3:1 (swatch 'Legend external swatch'); empty body 11% (rows 11%, columns 0%; weak >= 40%)
- slide 4: title 38 pt; min body 14 pt (floor 14); min label 10 pt (floor 8); min footnote 12 pt (floor 8); min chart 12.6 pt (floor 8); min text contrast 4.7:1 ('ChartNote' 'Q3 doubled\xa0Q1'); min non-text contrast 3.1:1 (chart series 'Refunds'); empty body 0% (rows 0%, columns 0%; weak >= 40%)
- slide 5: title 38 pt; min body 14 pt (floor 14); min label 10 pt (floor 8); min footnote 12 pt (floor 8); min chart 12.6 pt (floor 8); min text contrast 5.3:1 ('Eyebrow' 'PLATFORM REVIEW'); min non-text contrast 4.7:1 (chart series 'Change'); empty body 0% (rows 0%, columns 0%; weak >= 40%)
- slide 6: title 38 pt; min body 14 pt (floor 10); min label 10 pt (floor 8); min footnote 10 pt (floor 8); min text contrast 5.3:1 ('Eyebrow' 'PLATFORM REVIEW'); empty body 0% (rows 0%, columns 0%; weak >= 40%)

# Design report: 29-arch-venn  (rubric v1, judge claude-opus-5-5, R=3 runs, 2026-11-15)

## Summary
Deck **64** (59-64)  Acceptable  ·  Slides 72 (bottom quartile 66)  ·  Deck KPIs 44
Gates: all pass. Unstable KPIs: none.

## Deck KPIs
| id | name | w | s (runs) | evidence (+/-) |
|---|---|---|---|---|
| D-01 | Narrative and storyline | 5 | 2 (2,2,2) | - Titles do not form an argument; Venn slides unrelated to the platform; - No conclusion |
| D-02 | Consistency as one system | 4 | 4 (4,4,4) | + Eyebrow, title, footer and legend style identical; + Same node and Venn treatment for parallel slides |
| D-03 | Variety of form | 3 | 3 (3,3,3) | + Architecture and Venn each repeated for parallel content; - Only two forms |
| D-04 | Pacing and framing slides | 3 | 2 (2,2,2) | - No cover or closing; starts on content |
| D-05 | Fit to purpose and audience | 3 | 3 (3,3,3) | + Presentation density throughout; - Language switches on slide 2 only |

## Slides
| # | topic | general | topic | raw | cap | score (range) | band | weakest KPIs (loss) |
|---|---|---|---|---|---|---|---|---|
| 1 | System, architecture and concept diagram | 73 | 85 | 78 | - | 78 (75-79) | Good | T-SYS-03 (2.5), G-09 (2.5), G-06 (2.5) |
| 2 | System, architecture and concept diagram + Dense Japanese business slide (overlay) | 67 | 66 | 66 | - | 66 (65-69) | Acceptable | T-JA-02 (3.8), G-09 (2.5), G-01 (2.5) |
| 3 | System, architecture and concept diagram | 77 | 80 | 78 | - | 78 (59-80) | Acceptable / Good (borderline) | T-SYS-03 (2.5), G-09 (2.5), G-06 (2.5) |
| 4 | System, architecture and concept diagram | 71 | 74 | 72 | - | 72 (59-75) | Acceptable / Good (borderline) | T-SYS-03 (2.5), G-09 (2.5), G-06 (2.5) |

## Top fixes (gates first, then by weighted loss)
1. Slide 2, T-JA-02 Key message line and conclusion-first (level 2, loss 3.8): No lead line; topic title only
2. Slide 1, G-06 Type scale, size floor and CJK (level 3, loss 2.5): Mono sublabels and arrow labels about 9 pt
3. Slide 1, G-09 Contrast and non-text contrast (level 3, loss 2.5): External node borders and small grey labels faint
4. Slide 1, T-SYS-03 Label legibility and fit (level 3, loss 2.5): Arrow and sublabels very small
5. Slide 2, G-01 One message, true to content (level 3, loss 2.5): Title '受注データ基盤の構成' is a topic label

## Evidence lines
slide | KPI | s (runs) | sign | what is seen
S1 | G-01 | 4 (4,3,4) | + | Title names the three-tier structure the diagram shows
S1 | G-01 | 4 (4,3,4) | - | No so-what beyond the structure
S1 | G-02 | 5 (5,5,5) | + | Tiered rows with labelled arrows fit an architecture
S1 | G-03 | 4 (4,4,4) | + | Orange API gateway and PLACE ORDER arrow form the focal path
S1 | G-04 | 4 (5,4,4) | + | Nodes on three rows and three columns; tier labels share a left edge
S1 | G-05 | 3 (3,4,3) | + | Diagram fills the body
S1 | G-05 | 3 (3,4,3) | - | Data tier nearly touches the legend rule
S1 | G-06 | 3 (3,3,3) | + | Clear roles: node names, mono sublabels, caps arrow labels
S1 | G-06 | 3 (3,3,3) | - | Mono sublabels and arrow labels about 9 pt
S1 | G-07 | 5 (4,5,5) | + | Node = tag, name, two-word role; arrow = one verb
S1 | G-08 | 4 (4,4,4) | + | Orange primary flow, blue HTTP, greys for node types; legend
S1 | G-08 | 4 (4,4,4) | - | Blue adds a second accent hue
S1 | G-09 | 3 (3,3,3) | + | Node names dark on light fills
S1 | G-09 | 3 (3,3,3) | - | External node borders and small grey labels faint
S1 | G-10 | 4 (4,4,4) | + | Accent on one node and one arrow
S1 | G-10 | 4 (4,4,4) | - | Nine legend entries add visual load
S1 | G-11 | 4 (4,3,4) | + | Three tiers and focal gateway visible at half size
S1 | G-11 | 4 (4,3,4) | - | Arrow labels unreadable at half size
S1 | G-12 | 4 (4,4,4) | + | Connectors attach at edges; labels beside lines
S1 | G-13 | 5 (5,5,4) | + | One node family, stroke and legend system
S1 | G-14 | N/A  | ? | (no evidence given)
S1 | T-SYS-01 | 5 (5,5,5) | + | Tiers labelled; every arrow labelled; line styles in legend
S1 | T-SYS-02 | 5 (5,5,4) | + | One focal node; store, external, optional as distinct levels
S1 | T-SYS-03 | 3 (3,3,4) | + | All labels fit with padding
S1 | T-SYS-03 | 3 (3,3,4) | - | Arrow and sublabels very small
S1 | T-SYS-04 | 5 (5,5,4) | + | Orthogonal, fanned attach points, no crossings
S1 | T-SYS-05 | 4 (5,4,4) | + | Nine nodes; externals greyed
S1 | T-SYS-05 | 4 (5,4,4) | - | External Stripe sits in DATA tier
S2 | G-01 | 3 (3,3,3) | - | Title '受注データ基盤の構成' is a topic label
S2 | G-01 | 3 (3,3,3) | + | Groups and arrows show a coherent flow
S2 | G-02 | 4 (5,4,4) | + | Four stage frames left to right with flow arrows
S2 | G-03 | 4 (4,4,4) | + | Orange 与信チェック is the single focal node
S2 | G-03 | 4 (4,4,4) | - | Focus not explained by title
S2 | G-04 | 4 (4,4,4) | + | Group columns equal width, nodes aligned
S2 | G-04 | 4 (4,4,4) | - | 処理 group top differs from others
S2 | G-05 | 3 (3,4,3) | - | Diagram centred with empty side margins and a gap above legend
S2 | G-06 | 4 (4,3,4) | + | CJK node names bold, sublabels about 10 pt; clean glyphs
S2 | G-07 | 4 (4,4,5) | + | Name plus short role per node
S2 | G-07 | 4 (4,4,5) | - | Tag chips repeat node type
S2 | G-08 | 4 (4,4,4) | + | Orange main path, blue HTTP, grey types; legend
S2 | G-09 | 3 (3,3,3) | + | Node names dark
S2 | G-09 | 3 (3,3,3) | - | Group tab labels and external borders faint
S2 | G-10 | 4 (4,4,4) | + | Accent on one node and one arrow
S2 | G-11 | 3 (3,3,3) | + | Four stages readable
S2 | G-11 | 3 (3,3,3) | - | Point not stated; small labels fade at half size
S2 | G-12 | 4 (4,4,4) | + | Connectors attach cleanly; labels fit
S2 | G-13 | 4 (5,4,4) | + | Same system as slide 1
S2 | G-13 | 4 (5,4,4) | - | Half-width '･' mixed with full-width '・'
S2 | G-14 | N/A  | ? | (no evidence given)
S2 | T-JA-01 | 4 (4,4,4) | + | Four labelled group columns give a scan grid
S2 | T-JA-02 | 2 (2,2,2) | - | No lead line; topic title only
S2 | T-JA-03 | 4 (4,4,4) | + | Every label on one line; '直近７日' kept together
S2 | T-JA-04 | 3 (3,3,4) | + | Sublabels about 10 pt
S2 | T-JA-04 | 3 (3,3,4) | - | Tab and legend labels small and light
S2 | T-JA-05 | 3 (3,3,3) | + | Legend explains symbols
S2 | T-JA-05 | 3 (3,3,3) | - | No note or source (none clearly needed)
S2 | T-JA-06 | 4 (4,4,4) | + | Greys plus orange and blue with fixed meanings
S2 | T-SYS-01 | 4 (4,4,4) | + | Group containment = stage; arrows labelled (受信, 保存, 参照)
S2 | T-SYS-01 | 4 (4,4,4) | - | 主経路 shown on one segment only
S2 | T-SYS-02 | 4 (4,4,4) | + | One focal node; store and optional distinct
S2 | T-SYS-03 | 4 (4,3,4) | + | All labels fit with padding
S2 | T-SYS-04 | 4 (5,4,4) | + | Orthogonal, no crossings, arrows behind frames
S2 | T-SYS-05 | 4 (4,4,4) | + | Nine nodes in four labelled groups
S3 | G-01 | 4 (4,4,4) | + | Title formula matches the three-circle overlap
S3 | G-01 | 4 (4,4,4) | - | Generic concept in an 'Order platform' deck
S3 | G-02 | 5 (5,5,5) | + | Three-set Venn shows the intersection claim
S3 | G-03 | 5 (5,5,5) | + | Dark centre 'Shippable' wins the first look
S3 | G-04 | 4 (5,4,4) | + | Symmetric circles, labels centred in regions
S3 | G-05 | 4 (4,4,4) | + | Diagram fills the body with balanced margins
S3 | G-06 | 3  | + | Bold circle names
S3 | G-06 | 3  | - | Mono caps sublabels very small
S3 | G-07 | 5 (5,5,5) | + | One word plus three-word gloss per set
S3 | G-08 | 4 (4,5,4) | + | Greys deepen with overlap; one dark focal region
S3 | G-09 | 3 (3,3,3) | + | White on dark centre is strong
S3 | G-09 | 3 (3,3,3) | - | Tiny grey sublabels low contrast
S3 | G-10 | 5 (5,5,5) | + | Emphasis only on the centre
S3 | G-11 | 4 (4,4,5) | + | Centre and set names clear at half size
S3 | G-11 | 4 (4,4,5) | - | Sublabels vanish
S3 | G-12 | 4 (4,4,4) | + | Labels inside regions; clean outlines
S3 | G-13 | 4 (4,5,4) | + | Monochrome Venn matches deck strokes
S3 | G-14 | N/A  | ? | (no evidence given)
S3 | T-SYS-01 | 5 (5,5,4) | + | Intersection shows the AND relation in the title
S3 | T-SYS-02 | 5 (5,5,5) | + | One focal region, others graded
S3 | T-SYS-03 | 3 (2,3,3) | + | Set names readable
S3 | T-SYS-03 | 3 (2,3,3) | - | Captions very small
S3 | T-SYS-04 | 4 (4,4,4) | + | No connectors; outlines clean
S3 | T-SYS-05 | 4 (4,4,4) | + | Exactly the three sets in the title
S4 | G-01 | 3 (3,3,3) | - | Title is a slogan; claim must be inferred
S4 | G-01 | 3 (3,3,3) | + | Overlap 'Ships' makes the idea clear
S4 | G-02 | 4 (4,4,4) | + | Two-set Venn suits a two-condition idea
S4 | G-03 | 5 (5,4,5) | + | Dark lens is the clear focal point
S4 | G-04 | 4 (5,4,4) | + | Symmetric, labels on one baseline
S4 | G-05 | 3 (3,3,4) | - | Wide empty band between title and circles
S4 | G-06 | 3  | + | Bold set names
S4 | G-06 | 3  | - | Mono caps sublabels very small
S4 | G-07 | 5 (5,5,5) | + | Minimal words
S4 | G-08 | 4 (4,5,4) | + | Neutral sets, dark overlap
S4 | G-09 | 3 (3,3,3) | - | Tiny grey glosses low contrast
S4 | G-10 | 5 (5,5,5) | + | Emphasis only on overlap
S4 | G-11 | 4 (4,4,5) | + | Readable at thumbnail
S4 | G-12 | 4 (4,3,4) | + | Labels inside regions
S4 | G-12 | 4 (4,3,4) | - | Lens gloss tight to lens edges
S4 | G-13 | 4 (4,5,4) | + | Matches slide 3 Venn style
S4 | G-14 | N/A  | ? | (no evidence given)
S4 | T-SYS-01 | 4 (4,4,4) | + | Overlap shows both are needed
S4 | T-SYS-02 | 5 (5,5,5) | + | One focal lens
S4 | T-SYS-03 | 3 (2,3,3) | - | Tiny captions; centre caption tight in lens
S4 | T-SYS-04 | 4 (4,4,4) | + | No connectors needed
S4 | T-SYS-05 | 4 (4,4,4) | + | Two sets, minimal scope

## Measured facts
- slide 3: smallest text 8.0 pt (venn sublabels, legend): at the 8 pt floor for labels, so G-06 is not below the floor (level 3)
- slide 4: smallest text 8.5 pt (venn sublabels): at the floor for labels, G-06 level 3

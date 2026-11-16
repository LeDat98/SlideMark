# Design report: 29-arch-venn  (rubric v1, judge claude-opus-5-5, R=3 runs, 2026-11-15)

## Summary
Deck **66** (58-70)  Acceptable  ·  Slides 75 (bottom quartile 72)  ·  Deck KPIs 44
Gates: all pass. Unstable KPIs: none.

## Deck KPIs
| id | name | w | s (runs) | evidence (+/-) |
|---|---|---|---|---|
| D-01 | Narrative and storyline | 5 | 2 (2,2,2) | + All titles are claims; - Two architecture slides then two generic Venns; no argument |
| D-02 | Consistency as one system | 4 | 4 (4,4,4) | + Eyebrow, title, footer, page number fixed; same colour roles |
| D-03 | Variety of form | 3 | 3 (3,3,3) | + Architecture and Venn forms; - Two pairs of near-identical layouts |
| D-04 | Pacing and framing slides | 3 | 2 (2,1,2) | - No cover or closing |
| D-05 | Fit to purpose and audience | 3 | 3 (3,3,3) | + Sparse presented style; - Tiny sublabels unfit for projection |

## Slides
| # | topic | general | topic | raw | cap | score (range) | band | weakest KPIs (loss) |
|---|---|---|---|---|---|---|---|---|
| 1 | System, architecture and concept diagram | 73 | 85 | 77 | - | 77 (72-85) | Good | T-SYS-03 (2.5), G-06 (2.5), G-12 (1.2) |
| 2 | System, architecture and concept diagram + Dense Japanese business slide (overlay) | 73 | 71 | 72 | - | 72 (67-76) | Acceptable / Good (borderline) | T-JA-02 (2.5), G-06 (2.5), T-JA-05 (1.5) |
| 3 | System, architecture and concept diagram | 79 | 80 | 79 | - | 79 (59-84) | Acceptable / Good (borderline) | T-SYS-03 (2.5), G-09 (2.5), G-06 (2.5) |
| 4 | System, architecture and concept diagram | 74 | 74 | 74 | - | 74 (59-84) | Acceptable / Good (borderline) | T-SYS-03 (2.5), G-09 (2.5), G-06 (2.5) |

## Top fixes (gates first, then by weighted loss)
1. Slide 1, G-06 Type scale, size floor and CJK (level 3, loss 2.5): Mono sublabels and arrow labels about 8-9pt
2. Slide 1, T-SYS-03 Label legibility and fit (level 3, loss 2.5): Sublabels and arrow labels very small
3. Slide 2, G-06 Type scale, size floor and CJK (level 3, loss 2.5): Serif 'DWH' in Gothic title; legend about 8pt
4. Slide 2, T-JA-02 Key message line and conclusion-first (level 3, loss 2.5): No lead line under title
5. Slide 3, G-06 Type scale, size floor and CJK (level 3, loss 2.5): Mono captions ~7-8pt

## Evidence lines
slide | KPI | s (runs) | sign | what is seen
S1 | G-01 | 4 (4,4,4) | + | Both client arrows end at the orange gateway, as titled
S1 | G-01 | 4 (4,4,4) | - | Billing/Stripe detail goes beyond the claim
S1 | G-02 | 4 (4,4,5) | + | Three labelled tiers with typed arrows suit architecture
S1 | G-03 | 4 (4,4,4) | + | Orange gateway and PLACE ORDER arrow are the focal pair
S1 | G-04 | 4 (4,4,4) | + | Nodes on three rows and three columns; tier labels in left column
S1 | G-05 | 4 (4,4,4) | + | Diagram fills body; legend below rule
S1 | G-06 | 3  | + | Node names consistent bold size
S1 | G-06 | 3  | - | Mono sublabels and arrow labels about 8-9pt
S1 | G-07 | 4 (4,4,5) | + | Two-word sublabels and verb arrow labels
S1 | G-08 | 4 (4,4,4) | + | Blue = HTTP, orange = primary/focal, grey fills = types; legend
S1 | G-09 | 4  | + | Dark text and lines on light fills
S1 | G-10 | 4 (4,4,5) | + | Accent on one node and one arrow
S1 | G-11 | 4 (4,4,4) | + | Gateway and incoming arrows clear at half size
S1 | G-12 | 4 (4,4,5) | + | Connectors attach at edges, no crossings
S1 | G-13 | 4 (4,4,5) | + | Tags, radius, strokes consistent
S1 | G-14 | N/A  | ? | (no evidence given)
S1 | T-SYS-01 | 5 (5,5,5) | + | Tiers, node types and arrow styles each carry one stated meaning
S1 | T-SYS-02 | 5 (5,4,5) | + | Focal, service, store, external are distinct levels per legend
S1 | T-SYS-03 | 3 (3,3,4) | + | All labels fit with padding
S1 | T-SYS-03 | 3 (3,3,4) | - | Sublabels and arrow labels very small
S1 | T-SYS-04 | 5 (5,4,5) | + | Orthogonal routes, fanned attach on gateway, no shared segments
S1 | T-SYS-05 | 4 (4,4,4) | + | Eight nodes; externals and optional queue distinct
S2 | G-01 | 4 (4,4,4) | + | Orange path BATCH→CHECK→DWH matches title
S2 | G-01 | 4 (4,4,4) | - | ERP/stock path bypasses check, slightly blurs 'all'
S2 | G-02 | 4 (4,4,5) | + | Input→process→store→output groups read left to right
S2 | G-03 | 4 (4,4,4) | + | Orange CHECK node and path are focal
S2 | G-04 | 4 (4,4,4) | + | Four group columns, nodes equal width
S2 | G-04 | 4 (4,4,4) | - | Group frames of uneven height
S2 | G-05 | 4 (4,3,4) | + | Balanced block with even margins
S2 | G-06 | 3  | + | Gothic CJK at about 11pt
S2 | G-06 | 3  | - | Serif 'DWH' in Gothic title; legend about 8pt
S2 | G-07 | 4 (4,4,5) | + | Short node names and sublabels
S2 | G-08 | 4 (4,4,4) | + | Same colour roles as slide 1, with legend
S2 | G-09 | 4  | + | Dark text dominant
S2 | G-09 | 4  | - | Grey sublabels on grey store fills weaker
S2 | G-10 | 4 (4,4,4) | + | One focal node and one primary arrow
S2 | G-11 | 4 (4,4,4) | + | Group headings and focal node readable at half size
S2 | G-12 | 4 (4,3,4) | + | No clipping; arrows attach cleanly
S2 | G-13 | 4 (4,3,4) | + | Same system as slide 1
S2 | G-14 | N/A  | ? | (no evidence given)
S2 | T-JA-01 | 4 (4,4,4) | + | Group frames with headings give three scan levels
S2 | T-JA-02 | 3 (2,3,3) | + | Title is a claim
S2 | T-JA-02 | 3 (2,3,3) | - | No lead line under title
S2 | T-JA-03 | 4 (4,4,4) | + | No overflow; '直近 7 日' kept together
S2 | T-JA-04 | 4 (3,4,4) | + | Body ~11pt gothic, bold heads
S2 | T-JA-05 | 3 (3,3,3) | + | No figures needing units
S2 | T-JA-05 | 3 (3,3,3) | - | No note or source line
S2 | T-JA-06 | 4 (4,4,4) | + | Neutral base, orange accent, blue for HTTP only
S2 | T-SYS-01 | 4 (4,4,5) | + | Group containment plus flow arrows; legend defines styles
S2 | T-SYS-02 | 4 (4,4,5) | + | Single focal node; others neutral by type
S2 | T-SYS-03 | 4 (4,4,4) | + | Japanese labels fit with padding
S2 | T-SYS-04 | 4 (4,4,4) | + | Orthogonal connectors, no crossings
S2 | T-SYS-05 | 4 (4,4,4) | + | Nine nodes in four labelled groups
S3 | G-01 | 4 (4,4,4) | + | Dark centre 'Shippable' is the title's claim
S3 | G-01 | 4 (4,4,4) | - | Generic concept, not tied to the order platform
S3 | G-02 | 5 (5,5,5) | + | Three-set Venn is the natural form for an intersection
S3 | G-03 | 5 (5,5,5) | + | Dark centre wins the first look; survives greyscale
S3 | G-04 | 4 (4,4,4) | + | Symmetric circles centred on slide
S3 | G-05 | 4 (4,4,4) | + | Sparse on purpose; Venn fills body height
S3 | G-06 | 3  | + | Set names bold and clear
S3 | G-06 | 3  | - | Mono captions ~7-8pt
S3 | G-07 | 5 (4,5,5) | + | One word plus three-word gloss per set
S3 | G-08 | 4 (4,4,5) | + | Grey scale with dark focal only
S3 | G-09 | 3  | + | Set names dark on light
S3 | G-09 | 3  | - | Tiny grey sublabels on grey fill
S3 | G-10 | 5 (5,5,5) | + | Emphasis spent once on the centre
S3 | G-11 | 5 (4,5,5) | + | Point clear at thumbnail size
S3 | G-12 | 4 (4,4,5) | + | Clean circles and intersections
S3 | G-13 | 4 (4,4,5) | + | Monochrome editorial style consistent
S3 | G-14 | N/A  | ? | (no evidence given)
S3 | T-SYS-01 | 5 (5,5,5) | + | Overlap shows exactly the 'all three' relation
S3 | T-SYS-02 | 5 (5,5,5) | + | Single dark focal region; sets and pair overlaps quieter
S3 | T-SYS-03 | 3 (2,3,3) | + | Names fit
S3 | T-SYS-03 | 3 (2,3,3) | - | Captions very small
S3 | T-SYS-04 | 4 (4,4,4) | + | No connectors needed
S3 | T-SYS-05 | 4 (4,4,4) | + | Three sets, one named intersection
S4 | G-01 | 4 (4,4,4) | + | Dark overlap 'Ships' states the claim
S4 | G-01 | 4 (4,4,4) | - | Generic, unrelated to order platform
S4 | G-02 | 4 (4,4,5) | + | Two-set Venn suits a necessary overlap
S4 | G-03 | 5 (5,4,5) | + | Dark lens wins the first look
S4 | G-04 | 4 (4,4,4) | + | Circles symmetric and centred; labels centred in sets
S4 | G-05 | 4 (4,4,4) | + | Sparse by design with even margins
S4 | G-06 | 3  | + | Bold set names
S4 | G-06 | 3  | - | Mono captions ~7-8pt
S4 | G-07 | 4 (4,4,5) | + | Minimal words
S4 | G-08 | 4 (4,4,5) | + | Greyscale with dark focal
S4 | G-09 | 3  | + | White text on dark centre
S4 | G-09 | 3  | - | Tiny grey sublabels on grey
S4 | G-10 | 5 (5,5,5) | + | Emphasis only on the overlap
S4 | G-11 | 4 (4,4,5) | + | Point lands at once
S4 | G-11 | 4 (4,4,5) | - | Sublabels lost at half size
S4 | G-12 | 4 (4,4,5) | + | Clean shapes, no overlap of text
S4 | G-13 | 4 (4,4,5) | + | Matches slide 3 style
S4 | G-14 | N/A  | ? | (no evidence given)
S4 | T-SYS-01 | 4 (4,4,5) | + | Overlap expresses the 'only where' relation
S4 | T-SYS-02 | 5 (5,5,5) | + | One dark focal region, sets quiet
S4 | T-SYS-03 | 3 (2,3,3) | + | Names readable
S4 | T-SYS-03 | 3 (2,3,3) | - | Captions very small
S4 | T-SYS-04 | 4 (4,4,4) | + | No connectors needed
S4 | T-SYS-05 | 4 (4,4,4) | + | Two sets and one overlap, nothing extra

## Measured facts
- slide 1: title 34 pt; min node 11 pt (floor 10); min label 8 pt (floor 8); min footnote 12 pt (floor 8); min text contrast 4.5:1 ('Arch tag Web app' 'EXT'); min non-text contrast 3.3:1 (swatch 'Legend external swatch')
- slide 2: title 34 pt; min node 11.5 pt (floor 10); min label 8 pt (floor 8); min footnote 12 pt (floor 8); min text contrast 4.5:1 ('Arch tag 受注API' 'API'); min non-text contrast 3.3:1 (swatch 'Legend external swatch')
- slide 3: title 34 pt; min node 13 pt (floor 10); min label 8 pt (floor 8); min footnote 12 pt (floor 8); min text contrast 5.3:1 ('Eyebrow' 'ORDER PLATFORM')
- slide 4: title 34 pt; min node 13 pt (floor 10); min label 8 pt (floor 8); min footnote 12 pt (floor 8); min text contrast 5.3:1 ('Eyebrow' 'ORDER PLATFORM')

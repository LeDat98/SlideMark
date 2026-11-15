# Design report: 27-editorial  (rubric v1, judge claude-opus-5-5, R=3 runs, 2026-11-15)

## Summary
Deck **59** (59-61)  Acceptable  ·  Slides 64 (bottom quartile 59)  ·  Deck KPIs 49
Gates: slide 3 capped at 59 (G-01=2); slide 4 capped at 59 (G-09=2); slide 5 capped at 59 (G-01=2). Unstable KPIs: none.

## Deck KPIs
| id | name | w | s (runs) | evidence (+/-) |
|---|---|---|---|---|
| D-01 | Narrative and storyline | 5 | 2 (2,2,2) | - Most titles are topics: 'Where the data goes', 'Cost per service'; - No conclusion or ask slide; + 'Orders grew all year' is a claim |
| D-02 | Consistency as one system | 4 | 4 (4,4,4) | + Eyebrow, serif title, footer and page number fixed on every content slide; + Same accent meaning (focal) across diagrams, chart, table, cards |
| D-03 | Variety of form | 3 | 4 (5,4,4) | + Diagram, flow, chart, table, cards: form varies with content |
| D-04 | Pacing and framing slides | 3 | 2 (2,2,2) | + Clear cover; - Ends abruptly on a content slide; no closing or next step |
| D-05 | Fit to purpose and audience | 3 | 3 (3,3,3) | + Sparse presentation density throughout; - Last slide switches to Japanese without reason |

## Slides
| # | topic | general | topic | raw | cap | score (range) | band | weakest KPIs (loss) |
|---|---|---|---|---|---|---|---|---|
| 1 | Framing slides (cover, agenda, section, closing, decision) | 85 | 70 | 79 | - | 79 (71-80) | Good | T-FRAME-03 (2.0), T-FRAME-02 (2.0), G-08 (1.5) |
| 2 | System, architecture and concept diagram | 61 | 74 | 66 | - | 66 (59-67) | Acceptable | G-05 (3.0), T-SYS-03 (2.5), G-09 (2.5) |
| 3 | System, architecture and concept diagram | 60 | 55 | 58 | 59 (G-01=2) | 58 (57-59) | Acceptable | T-SYS-01 (3.8), G-01 (3.8), G-09 (2.5) |
| 4 | Data chart | 62 | 67 | 64 | 59 (G-09=2) | 59 (59-67) | Acceptable | G-09 (3.8), G-05 (3.0), G-01 (2.5) |
| 5 | Data table | 64 | 65 | 64 | 59 (G-01=2) | 59 (59-67) | Acceptable | G-01 (3.8), G-05 (3.0), G-03 (2.5) |
| 6 | Text argument / message slide + Dense Japanese business slide (overlay) | 69 | 71 | 70 | - | 70 (65-72) | Acceptable / Good (borderline) | G-05 (3.0), T-TEXT-04 (2.0), G-02 (2.0) |

## Top fixes (gates first, then by weighted loss)
1. Slide 3, G-01 One message, true to content (level 2, loss 3.8): Title 'Where the data goes' is a topic label
2. Slide 3, T-SYS-01 Structure shows the right relationship (level 2, loss 3.8): Decision diamond has three exits with no branch labels
3. Slide 4, G-09 Contrast and non-text contrast (level 2, loss 3.8): Pale refund bars barely separate from light background
4. Slide 5, G-01 One message, true to content (level 2, loss 3.8): Title 'Cost per service' is a topic label
5. Slide 2, G-05 White space and density (level 2, loss 3.0): Diagram occupies a small centre block; dead bands above and on both sides

## Evidence lines
slide | KPI | s (runs) | sign | what is seen
S1 | G-01 | 4 (4,4,4) | + | Cover states topic, scope and period in three lines
S1 | G-01 | 4 (4,4,4) | - | No presenter or owner named
S1 | G-02 | 4 (4,4,4) | + | Plain title block is the right form for a cover
S1 | G-03 | 5 (5,5,4) | + | Large serif title dominates; eyebrow and subtitle clearly smaller
S1 | G-04 | 4 (4,4,4) | + | Eyebrow, title and subtitle share one left edge at the margin
S1 | G-05 | 4 (4,4,4) | + | Generous space reads as intentional for a cover
S1 | G-05 | 4 (4,4,4) | - | Block sits high; bottom half empty with no anchor
S1 | G-06 | 5 (5,5,4) | + | Three sizes with large ratios: mono eyebrow, serif title, sans subtitle
S1 | G-07 | 5 (5,5,5) | + | Minimal words; date and scope given once each
S1 | G-08 | 3 (4,3,3) | + | Neutral greys and slate, coherent
S1 | G-08 | 3 (4,3,3) | - | No accent role
S1 | G-09 | 4 (4,4,4) | + | Dark navy title on off-white is high contrast
S1 | G-09 | 4 (4,4,4) | - | Grey eyebrow text is lighter but still legible
S1 | G-10 | 5 (5,5,4) | + | No decoration; emphasis only through title size
S1 | G-11 | 5 (5,5,4) | + | Topic readable instantly even at thumbnail size
S1 | G-12 | 5 (5,5,5) | + | No defects; clean text rendering
S1 | G-13 | 4 (4,4,4) | + | Editorial mix of serif, mono eyebrow and sans is a clear deliberate style
S1 | G-14 | N/A  | ? | (no evidence given)
S1 | T-FRAME-01 | 5 (5,5,4) | + | Clear three-level hierarchy: eyebrow, title, subtitle
S1 | T-FRAME-02 | 3 (3,3,3) | + | Title, subject line and period present
S1 | T-FRAME-02 | 3 (3,3,3) | - | No presenter or organisation beyond 'Engineering'
S1 | T-FRAME-03 | 3 (3,3,3) | + | Subtitle lists three scope items in parallel form
S1 | T-FRAME-03 | 3 (3,3,3) | - | No agenda; not applicable beyond the scope line
S1 | T-FRAME-04 | 4 (4,3,4) | + | Big serif type is the single anchor; no clutter
S2 | G-01 | 3 (3,2,3) | - | Title 'How a request travels' is a topic, not a claim
S2 | G-01 | 3 (3,2,3) | - | Subtitle describes styling roles rather than content
S2 | G-01 | 3 (3,2,3) | + | Diagram shows the request path coherently
S2 | G-02 | 4 (4,4,4) | + | Tiered boxes with flow arrows suit an architecture path
S2 | G-03 | 4 (4,4,4) | + | Orange-bordered API gateway is the single focal node
S2 | G-03 | 4 (4,4,4) | - | Diagram is small; title outweighs the content
S2 | G-04 | 4 (4,4,4) | + | Nodes on one row with equal gaps; lane labels share a left edge
S2 | G-05 | 2 (2,2,2) | - | Diagram occupies a small centre block; dead bands above and on both sides
S2 | G-06 | 3 (3,3,3) | + | Clear roles: serif title, bold node names, mono tags
S2 | G-06 | 3 (3,3,3) | - | Mono sublabels and lane labels are small (about 9 pt)
S2 | G-07 | 3 (4,3,3) | - | Subtitle is meta-commentary with no content value
S2 | G-08 | 4 (4,4,4) | + | One orange accent for focal; greys encode node types with legend
S2 | G-09 | 3 (3,3,3) | + | Node names dark on light fills
S2 | G-09 | 3 (3,3,3) | - | External node border and legend swatches very faint
S2 | G-10 | 4 (4,4,4) | + | Emphasis spent once on the gateway
S2 | G-10 | 4 (4,4,4) | - | Tag chips (WEB/API/DB) add decoration repeating the names
S2 | G-11 | 3 (3,3,3) | + | Path is clear in a few seconds
S2 | G-11 | 3 (3,3,3) | - | Small diagram and sublabels fade at half size
S2 | G-12 | 4 (4,4,4) | + | Arrows attach to box edges; labels inside boxes with padding
S2 | G-13 | 4 (4,4,4) | + | Consistent radius, stroke and node-type family with legend
S2 | G-14 | N/A  | ? | (no evidence given)
S2 | T-SYS-01 | 4 (4,4,3) | + | Lanes CLIENT/PLATFORM and arrows labelled 'Flow' in legend
S2 | T-SYS-01 | 4 (4,4,3) | - | Backup arrow means copy, not request flow
S2 | T-SYS-02 | 5 (4,5,5) | + | Focal, store, external, optional are distinct levels
S2 | T-SYS-03 | 3 (3,3,4) | + | Node names readable and padded
S2 | T-SYS-03 | 3 (3,3,4) | - | Sublabels and lane labels very small
S2 | T-SYS-04 | 4 (5,4,4) | + | Orthogonal, no crossings
S2 | T-SYS-05 | 4 (4,4,4) | + | Four nodes, external and optional visibly distinct
S3 | G-01 | 2 (2,2,2) | - | Title 'Where the data goes' is a topic label
S3 | G-01 | 2 (2,2,2) | - | Reports is the focal node but nothing says why
S3 | G-02 | 3 (4,3,3) | + | Left-to-right data flow
S3 | G-02 | 3 (4,3,3) | - | Decision diamond but outputs are destinations, not choices
S3 | G-03 | 3 (3,3,3) | + | Title first, then flow from left
S3 | G-03 | 3 (3,3,3) | - | Large diamond pulls the eye more than the focal Reports node
S3 | G-04 | 4 (4,4,4) | + | Three destination nodes share one column; main row aligned
S3 | G-05 | 4 (4,4,4) | + | Diagram fills the body area with even spacing
S3 | G-06 | 4 (4,4,4) | + | Node labels bold and uniform; clear size step to title
S3 | G-07 | 4 (4,5,4) | + | One- or two-word node names only
S3 | G-08 | 4 (4,3,4) | + | Node types coded by fill/stroke with a legend; one accent
S3 | G-09 | 3 (3,4,3) | + | Labels dark on light fills
S3 | G-09 | 3 (3,4,3) | - | Stripe external node border faint against background
S3 | G-10 | 3 (3,3,3) | + | Single accent node
S3 | G-10 | 3 (3,3,3) | - | Accent on Reports, which the title does not mention
S3 | G-11 | 3 (3,3,2) | + | Flow shape is visible at a glance
S3 | G-11 | 3 (3,3,2) | - | Point of the slide needs inference
S3 | G-12 | 4 (4,4,4) | + | Connectors attach cleanly; no overlaps
S3 | G-13 | 4 (4,4,4) | + | Same node family and legend style as slide 2
S3 | G-14 | N/A  | ? | (no evidence given)
S3 | T-SYS-01 | 2 (2,2,2) | - | Decision diamond has three exits with no branch labels
S3 | T-SYS-01 | 2 (2,2,2) | - | Unclear whether data goes to all targets or one
S3 | T-SYS-02 | 3 (3,3,3) | + | One accent node
S3 | T-SYS-02 | 3 (3,3,3) | - | Focal Reports is peripheral to the fraud-check flow
S3 | T-SYS-03 | 4 (4,4,4) | + | All labels readable, centred, padded
S3 | T-SYS-04 | 4 (4,4,4) | + | Orthogonal connectors with distinct attach points; no crossings
S3 | T-SYS-05 | 3 (4,3,3) | - | Which data goes where is not labelled
S4 | G-01 | 3 (3,2,3) | + | Action title matches rising bars
S4 | G-01 | 3 (3,2,3) | - | 'Refunds flat at 7%' not supported: 12/120 to 17/260 is 10% to 6.5%
S4 | G-02 | 4 (4,4,4) | + | Columns over quarters suit a time series
S4 | G-03 | 4 (4,3,4) | + | Highlighted Q3 bar and annotation draw the eye
S4 | G-03 | 4 (4,3,4) | - | Focal Q3 is not the title's 'all year' point
S4 | G-04 | 3 (3,3,3) | + | Chart and panel tops roughly aligned
S4 | G-04 | 3 (3,3,3) | - | Reading panel top differs from chart title line
S4 | G-05 | 2 (2,2,2) | - | Right column empty below the short Reading panel
S4 | G-06 | 4 (3,4,4) | + | Clear title, label, body sizes
S4 | G-07 | 4 (4,4,4) | + | Two short reading bullets; value labels carry numbers
S4 | G-08 | 4 (4,4,4) | + | Muted slate series with one orange accent for the key bar
S4 | G-09 | 2 (2,2,3) | - | Pale refund bars barely separate from light background
S4 | G-09 | 2 (2,2,3) | - | Highlighted Q3 fill is pale pink with thin outline
S4 | G-10 | 4 (4,3,4) | + | Accent used once; bold only on 'repeat buyers'
S4 | G-11 | 4 (4,4,4) | + | Rising bars plus title deliver the point in seconds
S4 | G-12 | 4 (4,4,4) | + | Labels clear of bars; no overlap
S4 | G-13 | 4 (4,4,4) | + | Chart palette matches deck neutrals and accent
S4 | G-14 | N/A  | ? | (no evidence given)
S4 | T-CHART-01 | 4 (4,4,4) | + | Clustered columns over four quarters in natural order
S4 | T-CHART-02 | 4 (4,4,4) | + | Bars start at a zero baseline
S4 | T-CHART-02 | 4 (4,4,4) | - | No value axis; refunds share the 'k' unit only implicitly
S4 | T-CHART-03 | 3 (3,3,4) | + | Value labels on every bar; unit '(k)' in chart title
S4 | T-CHART-03 | 3 (3,3,4) | - | Series identified only by a small bottom legend
S4 | T-CHART-04 | 3 (3,3,3) | + | Q3 highlighted with annotation 'Q3 doubled Q1'
S4 | T-CHART-04 | 3 (3,3,3) | - | Title is about all-year growth, highlight is one quarter
S4 | T-CHART-05 | 4 (5,4,4) | + | No gridlines or effects
S4 | T-CHART-06 | 4 (4,4,4) | + | Title states direction; unit and quarters shown
S4 | T-CHART-06 | 4 (4,4,4) | - | No year or source footnote
S5 | G-01 | 2 (2,3,2) | - | Title 'Cost per service' is a topic label
S5 | G-01 | 2 (2,3,2) | - | Gateway highlighted with no stated reason
S5 | G-02 | 4 (4,4,4) | + | Small lookup table suits four services by cost and change
S5 | G-03 | 3 (3,4,3) | + | Highlighted row gives a focal point
S5 | G-03 | 3 (3,4,3) | - | Largest cost (Orders DB) is not the emphasised row
S5 | G-04 | 4 (4,4,3) | + | Columns cleanly aligned; table centred
S5 | G-04 | 4 (4,4,3) | - | Centred table breaks the left-aligned title grid
S5 | G-05 | 2 (2,2,2) | - | Small table floats in a large empty field
S5 | G-06 | 4 (4,4,4) | + | Table text consistent size; bold header and highlight row
S5 | G-07 | 5 (5,5,4) | + | Only names and figures; nothing redundant
S5 | G-08 | 4 (4,4,4) | + | Single pale accent fill on one row
S5 | G-09 | 4 (4,4,4) | + | Dark text on light background throughout
S5 | G-10 | 4 (4,4,3) | + | One emphasised row; rest plain
S5 | G-11 | 3 (3,3,2) | + | Table readable at half size
S5 | G-11 | 3 (3,3,2) | - | Point (why gateway) not given at a glance
S5 | G-12 | 4 (5,4,4) | + | Clean rules, no clipping
S5 | G-13 | 4 (4,4,4) | + | Table style matches the editorial palette
S5 | G-14 | N/A  | ? | (no evidence given)
S5 | T-TABLE-01 | 4 (4,4,4) | + | Four rows, four columns, short cells
S5 | T-TABLE-02 | 4 (5,4,4) | + | Numbers and headers right-aligned, separators consistent
S5 | T-TABLE-02 | 4 (5,4,4) | - | No total
S5 | T-TABLE-03 | 4 (5,4,4) | + | Thin horizontal rules only, header rule stronger
S5 | T-TABLE-04 | 3 (3,3,3) | + | One highlighted row
S5 | T-TABLE-04 | 3 (3,3,3) | - | Title does not explain the highlight
S5 | T-TABLE-05 | 3 (3,3,3) | + | Headers and $ / % units present
S5 | T-TABLE-05 | 3 (3,3,3) | - | No period or base for 'Change'; no source
S6 | G-01 | 4 (4,4,3) | + | Lead line states the plan and target (halve latency)
S6 | G-01 | 4 (4,4,3) | - | Title itself is a topic label
S6 | G-02 | 3 (3,3,3) | + | Four labelled cards show situation-issue-action
S6 | G-02 | 3 (3,3,3) | - | No arrows show the logical sequence between cards
S6 | G-03 | 4 (4,4,4) | + | Title, then accented 施策 card stands out
S6 | G-04 | 4 (4,4,4) | + | Four equal cards with equal gutters spanning the margins
S6 | G-05 | 2 (2,2,2) | - | Thin card row in the middle; dead bands above and below
S6 | G-05 | 2 (2,2,2) | - | Fourth card half empty
S6 | G-06 | 4 (4,3,4) | + | CJK body about 12 pt, bold heads; clear title step
S6 | G-06 | 4 (4,3,4) | - | Odd spaces in '2.8 秒' and '( 2026 年'
S6 | G-07 | 4 (5,4,4) | + | Short fragments with figures (2.8 秒, 4 時間)
S6 | G-08 | 4 (4,4,4) | + | Neutral cards with one accent for the action card
S6 | G-09 | 4 (4,3,4) | + | Dark text on white cards; footnote legible grey
S6 | G-10 | 4 (4,4,4) | + | Emphasis only on the 施策 card
S6 | G-11 | 4 (4,3,4) | + | Title plus lead and card heads give the point quickly
S6 | G-12 | 4 (4,3,4) | + | All text inside cards; no clipping
S6 | G-12 | 4 (4,3,4) | - | Uneven spacing around parentheses in footnote
S6 | G-13 | 4 (4,4,4) | + | Same card and accent system as earlier slides
S6 | G-14 | N/A  | ? | (no evidence given)
S6 | T-JA-01 | 4 (4,4,4) | + | Even card grid with a heading per group
S6 | T-JA-02 | 4 (4,4,4) | + | One-line lead states the conclusion and target
S6 | T-JA-03 | 4 (4,4,4) | + | All lines fit; no orphans
S6 | T-JA-03 | 4 (4,4,4) | - | Extra spaces around Latin digits
S6 | T-JA-04 | 4 (4,4,4) | + | Body about 12 pt; heads bold; footnote small but legible
S6 | T-JA-05 | 4 (4,4,4) | + | ※ 出所 line with date and metric definition at bottom left
S6 | T-JA-06 | 4 (5,4,4) | + | Neutral base and one accent
S6 | T-TEXT-01 | 4 (4,4,3) | + | Lead claim supported by situation, issue, action cards
S6 | T-TEXT-01 | 4 (4,4,3) | - | Action bullets do not quantify the halving
S6 | T-TEXT-02 | 4 (4,4,4) | + | 2-3 one-line bullets per card
S6 | T-TEXT-03 | 4 (4,4,4) | + | Cards ordered 現状→課題→施策→管理
S6 | T-TEXT-03 | 4 (4,4,4) | - | 管理 card is a different kind from the first three
S6 | T-TEXT-04 | 3 (3,3,3) | + | Numbers given with units and a source note
S6 | T-TEXT-04 | 3 (3,3,3) | - | Key numbers not emphasised
S6 | T-TEXT-05 | 3 (3,3,3) | + | Card grouping fits a problem-solution argument
S6 | T-TEXT-05 | 3 (3,3,3) | - | Issue-to-action mapping could be shown as linked flow

# Design report: 27-editorial  (rubric v1, judge claude-opus-5-5, R=3 runs, 2026-11-15)

## Summary
Deck **63** (61-66)  Acceptable  ·  Slides 63 (bottom quartile 59)  ·  Deck KPIs 64
Gates: slide 4 capped at 59 (G-06=2); slide 5 capped at 59 (G-06=2); slide 6 capped at 59 (G-05=2). Unstable KPIs: none.

## Deck KPIs
| id | name | w | s (runs) | evidence (+/-) |
|---|---|---|---|---|
| D-01 | Narrative and storyline | 5 | 3 (3,3,3) | + Content titles are claims; ends with a recommendation; - Slides read as separate facts, no answer-first arc |
| D-02 | Consistency as one system | 4 | 4 (4,4,4) | + Eyebrow, title, footer, page number and legend fixed; - Last slide switches to Japanese |
| D-03 | Variety of form | 3 | 5 (5,4,5) | + Cover, architecture, flowchart, chart, table, cards: each form fits |
| D-04 | Pacing and framing slides | 3 | 3 (3,2,3) | + Cover with team and date; - No closing or next-step slide |
| D-05 | Fit to purpose and audience | 3 | 3 (3,3,3) | + Sparse presented style throughout; - Language switch on last slide fits no clear audience |

## Slides
| # | topic | general | topic | raw | cap | score (range) | band | weakest KPIs (loss) |
|---|---|---|---|---|---|---|---|---|
| 1 | Framing slides (cover, agenda, section, closing, decision) | 71 | 69 | 70 | - | 70 (67-87) | Acceptable / Excellent (borderline) | G-05 (2.5), T-FRAME-03 (2.0), G-08 (1.5) |
| 2 | System, architecture and concept diagram | 69 | 80 | 73 | - | 73 (70-80) | Good | G-06 (2.5), G-05 (2.5), G-07 (1.5) |
| 3 | Process, flow and steps | 66 | 67 | 67 | - | 67 (64-72) | Acceptable / Good (borderline) | T-PROC-01 (2.5), G-03 (2.5), G-01 (2.5) |
| 4 | Data chart | 56 | 67 | 61 | 59 (G-06=2) | 59 (59-59) | Acceptable | G-06 (3.8), G-05 (3.8), G-09 (2.5) |
| 5 | Data table | 68 | 74 | 70 | 59 (G-06=2) | 59 (59-59) | Acceptable | G-06 (3.8), G-05 (3.8), T-TABLE-05 (2.0) |
| 6 | Text argument / message slide + Dense Japanese business slide (overlay) | 64 | 70 | 66 | 59 (G-05=2) | 59 (59-59) | Acceptable | G-05 (3.8), G-12 (2.5), G-06 (2.5) |

## Top fixes (gates and soft gates first, then by weighted loss)
1. Slide 4, G-05 White space and density (level 2, loss 3.8): Right lower half empty below small reading box
2. Slide 4, G-06 Type scale, size floor and CJK (level 2, loss 3.8): Legend and data labels small, about 10pt
3. Slide 5, G-05 White space and density (level 2, loss 3.8): Small table floats in a large empty field
4. Slide 5, G-06 Type scale, size floor and CJK (level 2, loss 3.8): Table text about 12pt, small for the space
5. Slide 6, G-05 White space and density (level 2, loss 3.8): Dead bands above and below the card row

## Evidence lines
slide | KPI | s (runs) | sign | what is seen
S1 | G-01 | 4 (3,4,4) | + | Cover states topic, scope, team and date in title plus subtitle
S1 | G-01 | 4 (3,4,4) | - | Title is a topic label, acceptable only because it is a cover
S1 | G-02 | 4 (4,4,5) | + | Classic cover: eyebrow, large title, subtitle
S1 | G-03 | 4 (4,4,5) | + | Huge serif title dominates; eyebrow and subtitle clearly smaller
S1 | G-04 | 4 (4,4,5) | + | All three lines share one left edge at the margin
S1 | G-05 | 3 (3,3,4) | + | Generous margins
S1 | G-05 | 3 (3,3,4) | - | Lower half of slide is an empty band
S1 | G-06 | 4  | + | Three sizes with large ratio steps
S1 | G-07 | 4 (4,4,5) | + | No surplus words
S1 | G-08 | 3 (3,3,4) | + | Neutral palette, nothing misleading
S1 | G-08 | 3 (3,3,4) | - | No accent at all
S1 | G-09 | 4  | + | Dark title on light grey; subtitle slate still clear
S1 | G-10 | 4 (4,4,5) | + | No decoration; size alone ranks elements
S1 | G-11 | 4 (4,4,5) | + | Title readable at thumbnail size
S1 | G-12 | 4 (4,4,5) | + | No defects
S1 | G-13 | 4 (4,4,4) | + | Serif display, mono eyebrow, sans subtitle: editorial system
S1 | G-14 | N/A  | ? | (no evidence given)
S1 | T-FRAME-01 | 4 (4,4,5) | + | Clear three-level hierarchy with ample space
S1 | T-FRAME-02 | 4 (4,4,5) | + | Title, subject line, team and date all present
S1 | T-FRAME-03 | 3 (3,3,3) | + | Subtitle names three themes
S1 | T-FRAME-03 | 3 (3,3,3) | - | No agenda; themes do not map cleanly to later slides
S1 | T-FRAME-04 | 4 (3,4,4) | + | Single anchor is the large serif title; no clutter
S2 | G-01 | 4 (4,4,4) | + | Title claim matches focal gateway node
S2 | G-01 | 4 (4,4,4) | - | Subtitle talks about design roles, not content
S2 | G-02 | 4 (4,4,4) | + | Tiered boxes with flow arrows suit architecture
S2 | G-03 | 4 (4,4,4) | + | Orange gateway box is the clear focal node
S2 | G-04 | 4 (4,3,4) | + | Tier labels in a left column; equal box sizes and gaps
S2 | G-05 | 3 (3,3,3) | + | Legend separated by rule
S2 | G-05 | 3 (3,3,3) | - | Empty band between subtitle and diagram; diagram small
S2 | G-06 | 3  | + | Consistent node name and sublabel sizes
S2 | G-06 | 3  | - | Mono sublabels and tier labels near 10pt
S2 | G-07 | 3 (3,3,3) | + | Node labels terse
S2 | G-07 | 3 (3,3,3) | - | Subtitle is meta filler
S2 | G-08 | 4 (4,4,4) | + | Fills encode focal/store/external per legend
S2 | G-09 | 4  | + | Dark text in boxes; arrows visible
S2 | G-10 | 4 (4,4,5) | + | Accent spent on gateway only
S2 | G-11 | 4 (4,4,4) | + | Gateway readable at half size
S2 | G-12 | 4 (4,4,5) | + | Arrows attach to box edges; no overlaps
S2 | G-13 | 4 (4,4,5) | + | Uniform radius, stroke and tag style
S2 | G-14 | N/A  | ? | (no evidence given)
S2 | T-SYS-01 | 4 (4,4,4) | + | Tiers and arrows show client to gateway to store
S2 | T-SYS-01 | 4 (4,4,4) | - | Only one client shown for 'every request'
S2 | T-SYS-02 | 5 (5,4,5) | + | One focal node; node types distinct and explained in legend
S2 | T-SYS-03 | 4 (4,4,4) | + | Labels fit with padding; tags explain type
S2 | T-SYS-04 | 4 (4,4,5) | + | Orthogonal elbow from web client; straight horizontals
S2 | T-SYS-05 | 4 (4,4,4) | + | Four nodes; optional backup dashed
S3 | G-01 | 3 (3,3,3) | + | Diamond at centre matches 'decides' in title
S3 | G-01 | 3 (3,3,3) | - | Accent sits on Reports, which the title does not mention
S3 | G-02 | 4 (4,4,4) | + | Flowchart with decision diamond fits routing
S3 | G-03 | 3 (3,3,3) | + | Left-to-right reading order clear
S3 | G-03 | 3 (3,3,3) | - | Orange Reports node competes with the diamond for focus
S3 | G-04 | 4 (4,4,5) | + | Targets stacked in one column; main row on one axis
S3 | G-05 | 4 (4,4,4) | + | Diagram fills body evenly
S3 | G-06 | 4  | + | One bold node size, small legend; clear scale
S3 | G-07 | 4 (4,4,5) | + | One- or two-word node names
S3 | G-08 | 3 (3,3,3) | + | Legend defines node fills
S3 | G-08 | 3 (3,3,3) | - | Focal colour on the wrong node
S3 | G-09 | 4  | + | Dark text and lines on light ground
S3 | G-10 | 2 (2,2,3) | - | Only accent spent on Reports, not the fraud check
S3 | G-11 | 4 (3,4,4) | + | Title and diamond give the point quickly
S3 | G-12 | 4 (4,4,5) | + | Connectors attach cleanly; no crossings
S3 | G-13 | 4 (4,4,4) | + | Same node and legend system as slide 2
S3 | G-14 | N/A  | ? | (no evidence given)
S3 | T-PROC-01 | 3 (3,3) | + | Left-to-right flow from marked input Checkout
S3 | T-PROC-01 | 3 (3,3) | - | Decision branches carry no condition labels
S3 | T-PROC-02 | 4.5 (4,5) | + | Short parallel names; equal box sizes
S3 | T-PROC-03 | 4 (4,4) | + | Six nodes, easy to follow
S3 | T-PROC-04 | 4 (4,4) | + | Orthogonal connectors attached at box edges
S3 | T-PROC-04 | 4 (4,4) | - | Branches unlabelled
S3 | T-PROC-05 | 3 (3,3) | + | Data routing has no actors; Reports shown as outcome
S3 | T-PROC-05 | 3 (3,3) | - | No owner or timing cues
S3 | T-SYS-01 | 3  | + | Decision fans out to three targets
S3 | T-SYS-01 | 3  | - | Branches unlabelled; condition per route unknown
S3 | T-SYS-02 | 2  | - | Focal fill on Reports, not the title's fraud check
S3 | T-SYS-03 | 4  | + | Bold labels centred and padded
S3 | T-SYS-04 | 4  | + | Orthogonal routes from separate diamond points
S3 | T-SYS-05 | 4  | + | Six nodes; external and optional styled distinctly
S4 | G-01 | 4 (4,3,4) | + | Rising bars 120 to 260 back the title; refund % checks out
S4 | G-01 | 4 (4,3,4) | - | 'Repeat buyers' claim not shown
S4 | G-02 | 4 (4,4,4) | + | Columns by quarter suit a time series
S4 | G-03 | 3 (3,3,3) | + | Title then chart then reading box
S4 | G-03 | 3 (3,3,3) | - | Q3 highlight pulls focus from the year-long growth
S4 | G-04 | 3 (3,3,3) | + | Two-column split
S4 | G-04 | 3 (3,3,3) | - | Reading box top not aligned to chart plot
S4 | G-05 | 2 (2,2,2) | - | Right lower half empty below small reading box
S4 | G-06 | 2  | + | Consistent label sizes
S4 | G-06 | 2  | - | Legend and data labels small, about 10pt
S4 | G-07 | 4 (4,4,4) | + | Two short bullets with numbers
S4 | G-08 | 3 (3,3,3) | + | Slate series palette
S4 | G-08 | 3 (3,3,3) | - | Q3 pale fill looks like a third series
S4 | G-09 | 3  | + | Dark bars on light ground
S4 | G-09 | 3  | - | Pale pink Q3 bar low contrast to background
S4 | G-10 | 3 (3,3,4) | + | Bold only on 'repeat buyers'
S4 | G-10 | 3 (3,3,4) | - | Highlight on Q3 not the title's point
S4 | G-11 | 4 (4,4,4) | + | Rising bars readable at a glance
S4 | G-12 | 4 (4,4,4) | + | Labels clear of bars; no clipping
S4 | G-13 | 4 (3,4,4) | + | Same palette and accent system as diagrams
S4 | G-14 | N/A  | ? | (no evidence given)
S4 | T-CHART-01 | 4 (4,4,4) | + | Clustered columns in quarter order
S4 | T-CHART-02 | 4 (4,4,4) | + | Bars start from a shared zero baseline
S4 | T-CHART-02 | 4 (4,4,4) | - | No value axis shown
S4 | T-CHART-03 | 3 (4,3,3) | + | Value labels on all bars; unit (k) in chart title
S4 | T-CHART-03 | 3 (4,3,3) | - | Series identified only via bottom legend
S4 | T-CHART-04 | 3 (3,3,3) | + | Annotation 'Q3 doubled Q1'
S4 | T-CHART-04 | 3 (3,3,3) | - | Highlight on one quarter while title is about the trend
S4 | T-CHART-05 | 4 (4,4,4) | + | No gridlines, border or effects
S4 | T-CHART-06 | 4 (4,4,4) | + | Title states direction; unit and quarters given
S4 | T-CHART-06 | 4 (4,4,4) | - | No year or source
S5 | G-01 | 5 (5,4,5) | + | Title number matches highlighted Gateway row +12%
S5 | G-02 | 4 (4,4,4) | + | Small table gives exact values for comparison
S5 | G-03 | 4 (4,4,4) | + | Highlighted bold Gateway row stands out
S5 | G-04 | 3 (3,3,4) | + | Columns aligned cleanly
S5 | G-04 | 3 (3,3,4) | - | Table centred while title is left aligned
S5 | G-05 | 2  | - | Small table floats in a large empty field
S5 | G-06 | 2  | + | One body size throughout table
S5 | G-06 | 2  | - | Table text about 12pt, small for the space
S5 | G-07 | 4 (4,4,5) | + | Only names and numbers
S5 | G-08 | 4 (4,4,4) | + | One accent fill on the key row
S5 | G-09 | 4  | + | Dark text on light fills
S5 | G-10 | 5 (4,5,5) | + | Emphasis spent once, on the row the title names
S5 | G-11 | 4 (3,4,4) | + | Title number and highlighted row read at a glance
S5 | G-12 | 4 (4,4,5) | + | No defects
S5 | G-13 | 4 (4,4,4) | + | Light-rule table fits editorial system
S5 | G-14 | N/A  | ? | (no evidence given)
S5 | T-TABLE-01 | 4 (4,4,4) | + | Four rows, four columns, short cells
S5 | T-TABLE-02 | 4 (5,4,4) | + | Numbers and their headers right-aligned
S5 | T-TABLE-02 | 4 (5,4,4) | - | $ and % repeated in every cell
S5 | T-TABLE-03 | 5 (5,5,5) | + | Thin horizontal rules only; bold header with heavier rule
S5 | T-TABLE-04 | 4 (5,4,4) | + | One tinted bold row matching title
S5 | T-TABLE-05 | 3 (3,3,3) | + | All columns headed; $ shown
S5 | T-TABLE-05 | 3 (3,3,3) | - | Change period and source not stated
S6 | G-01 | 4 (4,4,4) | + | Action title with lead; 施策 card lists the three measures
S6 | G-01 | 4 (4,4,4) | - | No target latency shown for 'halve'
S6 | G-02 | 3 (3,3,3) | + | Cards group situation, issue, measures, control
S6 | G-02 | 3 (3,3,3) | - | Sequence shown as equal unconnected cards
S6 | G-03 | 4 (4,4,4) | + | Highlighted 施策 card is focal after title
S6 | G-04 | 4 (4,4,4) | + | Four equal cards, equal gaps, shared top
S6 | G-05 | 2  | - | Dead bands above and below the card row
S6 | G-06 | 3  | + | Gothic body about 12pt, bold heads
S6 | G-06 | 3  | - | Serif '3' in title; double space in '遅延  2.8 秒'
S6 | G-07 | 4 (4,4,5) | + | Short noun-phrase bullets
S6 | G-08 | 4 (4,4,4) | + | One accent on the measures card
S6 | G-09 | 4  | + | Dark text on white and pale fills
S6 | G-10 | 4 (4,4,5) | + | Single emphasised card
S6 | G-11 | 4 (4,4,4) | + | Title and card heads give the point
S6 | G-12 | 3 (3,3,4) | + | No overflow
S6 | G-12 | 3 (3,3,4) | - | Odd spacing around numbers and brackets in footnote
S6 | G-13 | 4 (4,4,4) | + | Cards match deck style
S6 | G-14 | N/A  | ? | (no evidence given)
S6 | T-JA-01 | 4 (4,4) | + | Title, lead, card heads, bullets give scan levels
S6 | T-JA-02 | 3.5 (4,3) | + | Lead line states the concrete so-what
S6 | T-JA-03 | 4 (4,4) | + | All text fits; numbers keep units
S6 | T-JA-03 | 4 (4,4) | - | Extra half-width spaces around numbers
S6 | T-JA-04 | 4 (4,4) | + | Body about 12pt, heads larger and bold
S6 | T-JA-05 | 4 (4,4) | + | 出所 and P95 note at bottom left
S6 | T-JA-06 | 4 (4,4) | + | Neutral base plus one accent
S6 | T-TEXT-01 | 4 (4,4,4) | + | Title is the claim; cards support it
S6 | T-TEXT-02 | 4 (4,4,4) | + | Two or three one-line bullets per card
S6 | T-TEXT-03 | 4 (4,4,4) | + | Parallel cards ordered 現状→課題→施策→管理
S6 | T-TEXT-04 | 3 (3,3,3) | + | 2.8秒 and 4時間 given
S6 | T-TEXT-04 | 3 (3,3,3) | - | Numbers not emphasised
S6 | T-TEXT-05 | 3 (3,3,3) | + | Cards suit grouped points
S6 | T-TEXT-05 | 3 (3,3,3) | - | Logical flow would read better with arrows

## Measured facts
- slide 1: title 59.99 pt; min body 22 pt (floor 14); min label 10 pt (floor 8); min text contrast 5.3:1 ('Eyebrow' 'ENGINEERING · Q3 2')
- slide 2: title 38 pt; min node 13 pt (floor 10); min label 8 pt (floor 8); min footnote 12 pt (floor 8); min text contrast 4.5:1 ('Arch tag Web client' 'WEB'); min non-text contrast 3.3:1 (swatch 'Legend external swatch'); empty body 33% (rows 33%, columns 0%; weak >= 40%)
- slide 3: title 34.2 pt; min node 12 pt (floor 10); min label 9 pt (floor 8); min footnote 12 pt (floor 8); min text contrast 5.3:1 ('Eyebrow' 'PLATFORM REVIEW'); min non-text contrast 3.3:1 (swatch 'Legend external swatch'); empty body 11% (rows 11%, columns 0%; weak >= 40%)
- slide 4: title 38 pt; min body 13 pt (floor 14); min label 10 pt (floor 8); min footnote 12 pt (floor 8); min chart 10.8 pt (floor 8); min text contrast 4.7:1 ('ChartNote' 'Q3 doubled\xa0Q1'); min non-text contrast 3.1:1 (chart series 'Refunds'); empty body 0% (rows 0%, columns 0%; weak >= 40%)
- slide 5: title 38 pt; min body 12 pt (floor 14); min label 10 pt (floor 8); min footnote 12 pt (floor 8); min text contrast 5.3:1 ('Eyebrow' 'PLATFORM REVIEW'); empty body 58% (rows 58%, columns 48%; weak >= 40%)
- slide 6: title 38 pt; min body 13 pt (floor 10); min label 10 pt (floor 8); min footnote 10 pt (floor 8); min text contrast 5.3:1 ('Eyebrow' 'PLATFORM REVIEW'); empty body 63% (rows 63%, columns 0%; weak >= 40%)

# Design report: 28-swimlane-sequence  (rubric v1, judge claude-opus-5-5, R=3 runs, 2026-11-15)

## Summary
Deck **63** (62-68)  Acceptable  ·  Slides 71 (bottom quartile 69)  ·  Deck KPIs 44
Gates: all pass. Unstable KPIs: G-07 (slide 2).

## Deck KPIs
| id | name | w | s (runs) | evidence (+/-) |
|---|---|---|---|---|
| D-01 | Narrative and storyline | 5 | 2 (2,3,2) | + Every title is a claim; - Five unrelated processes; no argument or conclusion |
| D-02 | Consistency as one system | 4 | 4 (4,4,4) | + Eyebrow, title, subtitle, legend, footer fixed; - Legend sets and lane orientation vary |
| D-03 | Variety of form | 3 | 3 (3,3,3) | + Swimlanes, sequences, vertical lanes; - All slides are process diagrams |
| D-04 | Pacing and framing slides | 3 | 2 (2,1,2) | - No cover or closing; density never varies |
| D-05 | Fit to purpose and audience | 3 | 3 (3,3,3) | + Technical audience terms fit; - Small mono labels hard for a presented deck |

## Slides
| # | topic | general | topic | raw | cap | score (range) | band | weakest KPIs (loss) |
|---|---|---|---|---|---|---|---|---|
| 1 | Process, flow and steps | 73 | 80 | 76 | - | 76 (74-78) | Good | G-06 (2.5), G-07 (1.5), T-PROC-01 (1.2) |
| 2 | Process, flow and steps + Dense Japanese business slide (overlay) | 70 | 66 | 69 | - | 69 (69-75) | Acceptable / Good (borderline) | T-JA-02 (2.5), G-06 (2.5), G-01 (2.5) |
| 3 | Process, flow and steps | 70 | 75 | 72 | - | 72 (69-84) | Acceptable / Good (borderline) | G-06 (2.5), G-11 (2.0), G-10 (1.5) |
| 4 | Process, flow and steps | 66 | 75 | 70 | - | 70 (69-77) | Acceptable / Good (borderline) | G-06 (2.5), G-03 (2.5), G-01 (2.5) |
| 5 | Process, flow and steps | 67 | 75 | 70 | - | 70 (66-79) | Acceptable / Good (borderline) | G-09 (2.5), G-06 (2.5), G-05 (2.0) |

## Top fixes (gates first, then by weighted loss)
1. Slide 1, G-06 Type scale, size floor and CJK (level 3, loss 2.5): Mono lane labels and sublabels around 9-10pt
2. Slide 2, G-01 One message, true to content (level 3, loss 2.5): No send-back loop or delay data shows the 差し戻し
3. Slide 2, G-06 Type scale, size floor and CJK (level 3, loss 2.5): Legend text about 8pt; lane labels small
4. Slide 2, T-JA-02 Key message line and conclusion-first (level 3, loss 2.5): Lead largely restates the title
5. Slide 3, G-06 Type scale, size floor and CJK (level 3, loss 2.5): Uppercase mono arrow labels around 9pt

## Evidence lines
slide | KPI | s (runs) | sign | what is seen
S1 | G-01 | 4 (4,4,4) | + | Title claim matches lane order author→reviewer→editor→CI
S1 | G-01 | 4 (4,4,4) | - | Subtitle is meta text about the design
S1 | G-02 | 5 (5,4,5) | + | Swimlanes show who and order together
S1 | G-03 | 4 (4,4,4) | + | Title, then staircase of boxes ending in orange Deploy
S1 | G-04 | 4 (4,4,5) | + | Lane grid with label column; boxes share column x
S1 | G-05 | 4 (4,4,4) | + | Diagram fills body; legend separated
S1 | G-06 | 3  | + | Bold node names consistent
S1 | G-06 | 3  | - | Mono lane labels and sublabels around 9-10pt
S1 | G-07 | 3 (3,3,4) | + | Verb-first node names
S1 | G-07 | 3 (3,3,4) | - | Subtitle restates design intent, not content
S1 | G-08 | 4 (4,4,4) | + | Orange only for deploy trigger and Deploy; legend
S1 | G-09 | 4  | + | Dark text on white boxes
S1 | G-09 | 4  | - | Lane labels small grey
S1 | G-10 | 4 (4,4,5) | + | One focal node and one primary arrow
S1 | G-11 | 4 (4,4,4) | + | Staircase flow readable at half size
S1 | G-12 | 4 (4,4,3) | + | Arrow labels masked over lane lines; clean attaches
S1 | G-13 | 4 (4,4,5) | + | Consistent box, tag and legend system
S1 | G-14 | N/A  | ? | (no evidence given)
S1 | T-PROC-01 | 4 (4,4,4) | + | Starts top-left, ends bottom-right at Deploy
S1 | T-PROC-01 | 4 (4,4,4) | - | Forward step drawn dashed 'REVISE' like a return
S1 | T-PROC-02 | 5 (4,5,5) | + | Parallel verb-first names with one short mono detail; equal boxes
S1 | T-PROC-03 | 4 (4,4,4) | + | Seven steps across four lanes
S1 | T-PROC-04 | 4 (4,4,3) | + | Orthogonal arrows attach to edges; labels masked
S1 | T-PROC-05 | 4 (4,4,5) | + | Labelled lanes; handoffs named HANDOFF, DEPLOY TRIGGER
S2 | G-01 | 3 (3,3,3) | + | Highlighted 与信を審査 matches title
S2 | G-01 | 3 (3,3,3) | - | No send-back loop or delay data shows the 差し戻し
S2 | G-02 | 4 (4,4,5) | + | Department swimlanes suit a 業務フロー
S2 | G-03 | 4 (4,4,4) | + | Orange credit-review box is the focal step
S2 | G-04 | 4 (4,4,4) | + | Lanes even; boxes equal width on column grid
S2 | G-05 | 4 (4,4,4) | + | Flow spreads across full lane width
S2 | G-06 | 3  | + | CJK Gothic renders cleanly
S2 | G-06 | 3  | - | Legend text about 8pt; lane labels small
S2 | G-07 | 4 (4,3,5) | + | Object+verb step names, short sublabels
S2 | G-08 | 4 (4,4,4) | + | Single accent for focal step and main path
S2 | G-09 | 4  | + | Dark text on white boxes
S2 | G-10 | 4 (4,4,5) | + | Emphasis limited to one box and one arrow
S2 | G-11 | 4 (4,4,4) | + | Title and focal box readable at half size
S2 | G-12 | 4 (4,4,4) | + | No clipping; arrows attach cleanly
S2 | G-13 | 4 (4,4,5) | + | Same system as other swimlane slides
S2 | G-14 | N/A  | ? | (no evidence given)
S2 | T-JA-01 | 4 (4,4,4) | + | Lane grid gives clear scan structure
S2 | T-JA-02 | 3 (3,3,3) | + | Lead line present
S2 | T-JA-02 | 3 (3,3,3) | - | Lead largely restates the title
S2 | T-JA-03 | 4 (4,4,5) | + | All labels fit; natural breaks
S2 | T-JA-04 | 3 (3,4,3) | + | Node names about 11pt bold
S2 | T-JA-04 | 3 (3,4,3) | - | Legend and lane labels below 10pt
S2 | T-JA-05 | 2 (3,2,2) | - | Bottleneck claim has no data, note or source
S2 | T-JA-06 | 4 (4,4,5) | + | Neutral plus one orange accent
S2 | T-PROC-01 | 4 (4,4,4) | + | Start top-left, end bottom-right; arrows throughout
S2 | T-PROC-01 | 4 (4,4,4) | - | Path jumps back up to 営業部 mid-flow
S2 | T-PROC-02 | 4 (4,4,4) | + | Parallel 〜を〜 names, equal boxes
S2 | T-PROC-03 | 4 (4,4,4) | + | Eight steps over five lanes
S2 | T-PROC-04 | 4 (4,4,4) | + | Orthogonal connectors, no box crossings
S2 | T-PROC-05 | 4 (4,4,5) | + | Department lanes labelled; 承認 handoff labelled
S2 | T-PROC-05 | 4 (4,4,5) | - | No durations for a 滞留 claim
S3 | G-01 | 4 (4,4,4) | + | Single render self-call on origin backs the title
S3 | G-01 | 4 (4,4,4) | - | Cost per article not quantified
S3 | G-02 | 5 (5,4,5) | + | Sequence diagram fits request/response timing
S3 | G-03 | 4 (4,3,4) | + | Orange origin header draws first after title
S3 | G-04 | 4 (4,4,5) | + | Equal headers on even lifeline spacing
S3 | G-05 | 4 (4,4,4) | + | Centred block with even surroundings
S3 | G-06 | 3  | + | Header names bold, consistent
S3 | G-06 | 3  | - | Uppercase mono arrow labels around 9pt
S3 | G-07 | 4 (4,4,5) | + | Protocol-terse labels
S3 | G-08 | 3 (3,3,4) | + | Legend defines colours
S3 | G-08 | 3 (3,3,4) | - | Blue request plus orange focal and orange return: two accents
S3 | G-09 | 4  | + | Arrows and labels clear
S3 | G-09 | 4  | - | Lifelines very faint
S3 | G-10 | 3 (3,3,4) | - | Accent split between origin node and cached reply
S3 | G-11 | 3 (3,4,3) | - | Point needs reading small arrow labels
S3 | G-12 | 4 (4,4,4) | + | Arrows end on activation bars; labels clear of lines
S3 | G-13 | 4 (4,4,5) | + | Header tags and boxes match deck
S3 | G-14 | N/A  | ? | (no evidence given)
S3 | T-PROC-01 | 4 (4,4,5) | + | Top-to-bottom message order with activations
S3 | T-PROC-02 | 4 (4,4,5) | + | Short uniform message labels
S3 | T-PROC-03 | 4 (4,4,5) | + | Six messages, four actors
S3 | T-PROC-04 | 4 (4,4,4) | + | Straight horizontal arrows; returns dashed
S3 | T-PROC-05 | 4 (4,4,5) | + | Each actor labelled with role tag
S4 | G-01 | 3 (3,3,4) | + | Title matches DB OK before 201
S4 | G-01 | 3 (3,3,4) | - | Retry drawn after DB OK, so its trigger is unclear
S4 | G-02 | 4 (4,4,5) | + | Sequence diagram fits call order
S4 | G-03 | 3 (3,3,3) | + | Clear top-down order
S4 | G-03 | 3 (3,3,3) | - | Small retry loop is the only accent; no strong focal
S4 | G-04 | 4 (4,4,5) | + | Lifelines evenly spaced; headers equal
S4 | G-05 | 4 (4,4,4) | + | Balanced central block
S4 | G-06 | 3  | + | Consistent roles
S4 | G-06 | 3  | - | Mono labels around 9pt
S4 | G-07 | 4 (4,4,5) | + | Terse protocol labels
S4 | G-08 | 4 (4,4,3) | + | One accent for retry; fills code node types
S4 | G-09 | 4  | + | Dark arrows on light ground
S4 | G-10 | 4 (4,4,3) | + | Accent spent once
S4 | G-11 | 3 (3,4,3) | - | Retry loop and labels small at half size
S4 | G-12 | 4 (4,4,4) | + | Clean arrows on activation bars
S4 | G-13 | 4 (4,4,5) | + | Matches slide 3 system
S4 | G-14 | N/A  | ? | (no evidence given)
S4 | T-PROC-01 | 4 (4,4,4) | + | Top-down with clear start POST and end 201
S4 | T-PROC-02 | 4 (4,4,5) | + | Uniform uppercase labels
S4 | T-PROC-03 | 4 (4,4,5) | + | Seven messages, four actors
S4 | T-PROC-04 | 4 (4,4,4) | + | Straight arrows; INSERT passes Auth lifeline only
S4 | T-PROC-05 | 4 (4,4,4) | + | Actors labelled with tag and role
S5 | G-01 | 4 (4,4,5) | + | Focal 'Fix flaky test' with BLOCKS QA arrow matches title
S5 | G-01 | 4 (4,4,5) | - | Subtitle is design meta text
S5 | G-02 | 4 (4,4,5) | + | Vertical lanes per team show handovers
S5 | G-03 | 4 (4,4,4) | + | Orange box and arrow are the focus
S5 | G-04 | 4 (3,4,4) | + | Three equal lanes; nodes centred in lanes
S5 | G-05 | 3 (3,4,3) | + | Lanes fill body height
S5 | G-05 | 3 (3,4,3) | - | Large empty lane cells on staircase
S5 | G-06 | 3  | + | Bold names over mono details
S5 | G-06 | 3  | - | Lane headers DEV/QA/OPS tiny
S5 | G-07 | 3 (3,3,4) | + | Short step names
S5 | G-07 | 3 (3,3,4) | - | Subtitle describes layout, not content
S5 | G-08 | 4 (4,4,5) | + | Single accent on blocker
S5 | G-09 | 3  | + | Node names dark
S5 | G-09 | 3  | - | Tiny grey lane headers weak
S5 | G-10 | 4 (4,4,5) | + | Accent on blocker box and its arrow only
S5 | G-11 | 4 (3,4,4) | + | Accent and title read in 3 seconds
S5 | G-12 | 4 (4,4,4) | + | Arrows attach to edges; label clear of line
S5 | G-13 | 4 (4,4,4) | + | Same node and legend style
S5 | G-14 | N/A  | ? | (no evidence given)
S5 | T-PROC-01 | 4 (4,3,4) | + | Top-down staircase from Merge to Deploy canary
S5 | T-PROC-02 | 4 (4,4,5) | + | Equal boxes, verb-first names
S5 | T-PROC-03 | 4 (4,4,5) | + | Five steps
S5 | T-PROC-04 | 4 (4,4,4) | + | Orthogonal connectors, no crossings
S5 | T-PROC-05 | 4 (3,4,4) | + | Team lanes; blocking hand-off is strongest connector
S5 | T-PROC-05 | 4 (3,4,4) | - | Lane labels faint

## Measured facts
- slide 1: title 32.29 pt; min body 14 pt (floor 14); min node 12 pt (floor 10); min label 9 pt (floor 8); min footnote 12 pt (floor 8); min text contrast 4.7:1 ('Step 5 next label' 'DEPLOY TRIGGER'); min non-text contrast 4.7:1 (arrow 'Step 5 next')
- slide 2: title 34 pt; min node 10.5 pt (floor 10); min label 8.1 pt (floor 8); min footnote 12 pt (floor 8); min text contrast 4.7:1 ('Step 3 next label' '承認'); min non-text contrast 4.7:1 (arrow 'Step 3 next')
- slide 3: title 34 pt; min body 14 pt (floor 14); min label 8 pt (floor 8); min footnote 12 pt (floor 8); min text contrast 4.5:1 ('Seq Reader tag' 'EXT'); min non-text contrast 3.3:1 (swatch 'Legend external swatch')
- slide 4: title 28.9 pt; min node 14 pt (floor 10); min label 8 pt (floor 8); min footnote 12 pt (floor 8); min text contrast 4.5:1 ('Seq Client tag' 'EXT'); min non-text contrast 3.3:1 (swatch 'Legend external swatch')
- slide 5: title 34 pt; min body 14 pt (floor 14); min node 11 pt (floor 10); min label 8 pt (floor 8); min footnote 12 pt (floor 8); min text contrast 4.7:1 ('Step 2 next label' 'BLOCKS QA'); min non-text contrast 4.7:1 (arrow 'Step 2 next')

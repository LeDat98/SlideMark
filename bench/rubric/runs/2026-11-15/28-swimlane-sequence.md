# Design report: 28-swimlane-sequence  (rubric v1, judge claude-opus-5-5, R=3 runs, 2026-11-15)

## Summary
Deck **65** (63-70)  Acceptable  ·  Slides 73 (bottom quartile 71)  ·  Deck KPIs 44
Gates: all pass. Unstable KPIs: G-07 (slide 5).

## Deck KPIs
| id | name | w | s (runs) | evidence (+/-) |
|---|---|---|---|---|
| D-01 | Narrative and storyline | 5 | 2 (2,2,2) | - All titles are labels ('Checkout request', 'Release train'); - No overall argument or conclusion |
| D-02 | Consistency as one system | 4 | 4 (5,4,4) | + Eyebrow, title, subtitle, legend, footer fixed; - JA slide uses sans title |
| D-03 | Variety of form | 3 | 3 (3,4,3) | + Horizontal lanes, sequence and vertical lanes; - All slides are process diagrams |
| D-04 | Pacing and framing slides | 3 | 2 (2,2,2) | - No cover or closing |
| D-05 | Fit to purpose and audience | 3 | 3 (3,3,3) | + Consistent technical density; - One Japanese slide in an English deck |

## Slides
| # | topic | general | topic | raw | cap | score (range) | band | weakest KPIs (loss) |
|---|---|---|---|---|---|---|---|---|
| 1 | Process, flow and steps | 71 | 80 | 75 | - | 75 (74-80) | Good | G-09 (2.5), G-06 (2.5), G-01 (2.5) |
| 2 | Process, flow and steps + Dense Japanese business slide (overlay) | 78 | 77 | 78 | - | 78 (72-80) | Good | T-JA-05 (1.5), T-PROC-01 (1.2), T-JA-03 (1.2) |
| 3 | Process, flow and steps | 73 | 82 | 76 | - | 76 (76-79) | Good | G-09 (2.5), G-06 (2.5), G-11 (2.0) |
| 4 | Process, flow and steps | 69 | 68 | 69 | - | 69 (63-76) | Acceptable / Good (borderline) | T-PROC-01 (2.5), G-09 (2.5), G-06 (2.5) |
| 5 | Process, flow and steps | 67 | 80 | 73 | - | 73 (72-77) | Good | G-09 (2.5), G-06 (2.5), G-01 (2.5) |

## Top fixes (gates first, then by weighted loss)
1. Slide 1, G-01 One message, true to content (level 3, loss 2.5): Title 'Publishing an article' is a topic
2. Slide 1, G-06 Type scale, size floor and CJK (level 3, loss 2.5): Lane labels and connector labels about 8-9 pt
3. Slide 1, G-09 Contrast and non-text contrast (level 3, loss 2.5): Grey lane labels and connector labels faint
4. Slide 3, G-06 Type scale, size floor and CJK (level 3, loss 2.5): Mono message labels about 8 pt
5. Slide 3, G-09 Contrast and non-text contrast (level 3, loss 2.5): Grey mono labels and dashed lifelines faint

## Evidence lines
slide | KPI | s (runs) | sign | what is seen
S1 | G-01 | 3 (3,3,3) | - | Title 'Publishing an article' is a topic
S1 | G-01 | 3 (3,3,3) | - | Subtitle explains layout, not why deploy is focal
S1 | G-01 | 3 (3,3,3) | + | Lanes and flow are coherent
S1 | G-02 | 5 (5,5,5) | + | Swimlanes show who does what in order
S1 | G-03 | 4 (4,4,4) | + | Flow descends left-to-right to the orange Deploy
S1 | G-04 | 4 (5,4,4) | + | Equal lanes; nodes share columns
S1 | G-05 | 4 (4,4,4) | + | Diagonal flow fills the lanes; even margins
S1 | G-05 | 4 (4,4,4) | - | Lower-left lanes empty by nature
S1 | G-06 | 3 (3,3,3) | + | Clear roles: bold names, mono sublabels
S1 | G-06 | 3 (3,3,3) | - | Lane labels and connector labels about 8-9 pt
S1 | G-07 | 4 (5,4,4) | + | Verb-object step names, short sublabels
S1 | G-08 | 4 (5,4,4) | + | Orange for focal and primary flow, in legend
S1 | G-09 | 3 (3,3,3) | + | Node text dark on white
S1 | G-09 | 3 (3,3,3) | - | Grey lane labels and connector labels faint
S1 | G-10 | 4 (5,4,4) | + | Accent on one step and one arrow
S1 | G-11 | 4 (4,4,4) | + | Staircase flow visible at half size
S1 | G-11 | 4 (4,4,4) | - | Lane labels vanish
S1 | G-12 | 4 (4,4,4) | + | Connectors attach at edges; labels beside lines
S1 | G-13 | 5 (5,5,4) | + | Consistent editorial node and legend system
S1 | G-14 | N/A  | ? | (no evidence given)
S1 | T-PROC-01 | 4 (4,4,4) | + | One direction down-right; clear start and end
S1 | T-PROC-01 | 4 (4,4,4) | - | REVISE dashed link reads as forward step
S1 | T-PROC-02 | 5 (5,5,5) | + | Two-word verb-first names; equal boxes
S1 | T-PROC-03 | 4 (4,4,4) | + | Seven steps chunked by lanes
S1 | T-PROC-04 | 4 (4,4,4) | + | Orthogonal connectors, no crossings, labels beside
S1 | T-PROC-05 | 4 (5,4,4) | + | Labelled lanes; handoff and deploy trigger labelled
S2 | G-01 | 4 (3,4,4) | + | Lead names the bottleneck; 与信 step highlighted
S2 | G-02 | 5 (5,5,5) | + | Department swimlanes fit a 業務フロー
S2 | G-03 | 4 (4,4,4) | + | Orange 与信を審査 node and 承認 arrow stand out
S2 | G-04 | 4 (4,4,4) | + | Equal lane heights; nodes centred in lanes
S2 | G-05 | 4 (4,4,4) | + | Lanes span the width; flow fills them
S2 | G-06 | 4 (4,3,4) | + | CJK node names bold about 12 pt; sublabels about 10 pt
S2 | G-07 | 5 (5,4,5) | + | Verb phrases per step; short qualifiers
S2 | G-08 | 4 (5,4,4) | + | Orange for focal and main path only
S2 | G-09 | 4 (4,3,4) | + | Dark text on white nodes
S2 | G-09 | 4 (4,3,4) | - | Lane labels grey
S2 | G-10 | 4 (5,4,4) | + | One emphasised step and arrow
S2 | G-11 | 4 (4,4,4) | + | Lead and orange node give the point fast
S2 | G-12 | 4 (4,4,4) | + | Connectors attach at edges; text fits
S2 | G-13 | 4 (5,4,4) | + | Same system as slide 1
S2 | G-13 | 4 (5,4,4) | - | Half-width '･' in lane and sublabels
S2 | G-14 | N/A  | ? | (no evidence given)
S2 | T-JA-01 | 4 (4,4,4) | + | Lane grid with label column; three scan levels
S2 | T-JA-02 | 4 (4,4,4) | + | Lead states the bottleneck conclusion
S2 | T-JA-02 | 4 (4,4,4) | - | Return path not shown
S2 | T-JA-03 | 4 (5,4,4) | + | Text fits, no orphans or bad breaks
S2 | T-JA-04 | 4 (4,3,4) | + | Node text 10-12 pt; bold heads
S2 | T-JA-05 | 3 (3,3,3) | + | Legend present
S2 | T-JA-05 | 3 (3,3,3) | - | No source or basis for the stall claim
S2 | T-JA-06 | 5 (5,4,5) | + | Greys plus one orange
S2 | T-PROC-01 | 4 (4,4,4) | + | Left-to-right flow, one start, one end
S2 | T-PROC-02 | 5 (5,4,5) | + | Parallel 〜を〜 verb names, equal boxes
S2 | T-PROC-03 | 4 (4,4,4) | + | Seven steps grouped by department
S2 | T-PROC-04 | 4 (4,4,4) | + | Orthogonal connectors, no crossings, label beside
S2 | T-PROC-05 | 4 (4,4,4) | + | Labelled lanes; handoffs cross lanes cleanly
S2 | T-PROC-05 | 4 (4,4,4) | - | No durations despite stall claim
S3 | G-01 | 4 (4,4,4) | + | Subtitle states the behaviour the sequence proves
S3 | G-01 | 4 (4,4,4) | - | Title itself is a label
S3 | G-02 | 5 (5,5,5) | + | Sequence diagram fits request/response timing
S3 | G-03 | 4 (3,4,4) | + | Orange origin and cached reply lead
S3 | G-04 | 4 (5,4,4) | + | Lifelines evenly spaced under headers
S3 | G-05 | 4 (4,4,4) | + | Diagram centred with even margins
S3 | G-06 | 3 (3,3,3) | + | Clear roles
S3 | G-06 | 3 (3,3,3) | - | Mono message labels about 8 pt
S3 | G-07 | 5 (5,5,5) | + | Protocol-style labels only
S3 | G-08 | 4 (4,4,4) | + | Orange, blue and dashed each defined in legend
S3 | G-08 | 4 (4,4,4) | - | Two accent hues
S3 | G-09 | 3 (3,3,3) | - | Grey mono labels and dashed lifelines faint
S3 | G-10 | 4 (4,4,4) | + | Accent limited to origin and cached reply
S3 | G-11 | 3 (3,3,3) | + | Actors readable
S3 | G-11 | 3 (3,3,3) | - | Message labels unreadable at half size
S3 | G-12 | 4 (4,4,4) | + | Arrows end on activation bars; labels above lines
S3 | G-13 | 5 (5,5,4) | + | Same node family and legend system
S3 | G-14 | N/A  | ? | (no evidence given)
S3 | T-PROC-01 | 5 (5,4,5) | + | Top-to-bottom time order; returns dashed
S3 | T-PROC-02 | 4 (4,4,4) | + | Short uppercase message names
S3 | T-PROC-03 | 4 (5,4,4) | + | Six messages
S3 | T-PROC-04 | 4 (4,5,4) | + | Straight arrows between lifelines; self-call loop clear
S3 | T-PROC-04 | 4 (4,5,4) | - | PAGEVIEW crosses two lifelines
S3 | T-PROC-05 | 4 (5,4,4) | + | Actors as labelled lifelines
S4 | G-01 | 3 (3,3,3) | + | Subtitle gives a message
S4 | G-01 | 3 (3,3,3) | - | Retry drawn after DB OK, which contradicts its purpose
S4 | G-02 | 5 (5,5,5) | + | Sequence diagram fits the call order
S4 | G-03 | 4 (4,4,3) | + | Orange RETRY ONCE is the single accent
S4 | G-04 | 4 (5,4,4) | + | Evenly spaced lifelines
S4 | G-05 | 4 (4,4,4) | + | Balanced, centred
S4 | G-06 | 3 (3,3,3) | - | Mono message labels about 8 pt
S4 | G-07 | 4 (5,4,4) | + | Terse labels
S4 | G-07 | 4 (5,4,4) | - | 'is the headline' is meta wording
S4 | G-08 | 4 (3,4,4) | + | Orange only on retry; legend
S4 | G-09 | 3 (3,3,3) | - | Grey labels and dashed returns faint
S4 | G-10 | 4 (4,4,4) | + | Emphasis on one element
S4 | G-11 | 3 (3,3,3) | - | Labels unreadable at half size
S4 | G-12 | 4 (4,4,3) | + | Arrows end on activations; no overlaps
S4 | G-13 | 5 (5,5,4) | + | Consistent with slide 3
S4 | G-14 | N/A  | ? | (no evidence given)
S4 | T-PROC-01 | 3 (4,3,3) | + | Top to bottom order
S4 | T-PROC-01 | 3 (4,3,3) | - | Retry placed after success confuses the sequence
S4 | T-PROC-02 | 4 (4,4,4) | + | Short uppercase message names
S4 | T-PROC-03 | 4 (5,4,4) | + | Seven messages
S4 | T-PROC-04 | 4 (4,4,3) | + | INSERT arrow passes Auth lifeline without confusion
S4 | T-PROC-05 | 4 (5,4,4) | + | Four labelled participants
S5 | G-01 | 3 (3,3,3) | - | Title 'Release train' is a label; subtitle describes the layout
S5 | G-01 | 3 (3,3,3) | + | BLOCKS QA accent carries the point
S5 | G-02 | 4 (5,4,4) | + | Vertical team lanes with time down
S5 | G-03 | 4 (4,4,4) | + | Orange Fix flaky test and BLOCKS QA arrow are focal
S5 | G-04 | 4 (4,4,4) | + | Nodes centred in equal lanes
S5 | G-04 | 4 (4,4,4) | - | Lane frame narrower than the title margins
S5 | G-05 | 3 (3,3,4) | - | Lanes largely empty; small nodes in a big frame
S5 | G-06 | 3 (3,3,3) | - | Lane headers and sublabels about 8 pt
S5 | G-07 | 4 (5,3,4) | + | Terse steps with facts (412 specs, 5% traffic)
S5 | G-07 | 4 (5,3,4) | - | Subtitle talks about accent
S5 | G-08 | 4 (5,4,4) | + | Orange only for blocker; legend
S5 | G-09 | 3 (3,3,3) | - | Grey lane headers and lines faint
S5 | G-10 | 4 (5,4,4) | + | One emphasised step and arrow
S5 | G-11 | 4 (3,4,4) | + | Flow and blocker visible at half size
S5 | G-12 | 4 (4,4,4) | + | Connectors attach cleanly
S5 | G-12 | 4 (4,4,4) | - | BLOCKS QA label tight to its line
S5 | G-13 | 5 (5,5,4) | + | Same system
S5 | G-14 | N/A  | ? | (no evidence given)
S5 | T-PROC-01 | 4 (4,4,4) | + | Top-to-bottom order with arrows; clear start and end
S5 | T-PROC-02 | 5 (5,5,5) | + | Verb-first names, equal boxes
S5 | T-PROC-03 | 4 (5,4,4) | + | Five steps
S5 | T-PROC-04 | 4 (4,4,4) | + | Orthogonal connectors, no crossings
S5 | T-PROC-05 | 4 (4,4,4) | + | Team lanes labelled; blocking handoff is the strongest connector

# Design report: 30-html-diagrams  (rubric v1, judge claude-opus-5-5, R=3 runs, 2026-11-15)

## Summary
Deck **64** (61-67)  Acceptable  ·  Slides 71 (bottom quartile 68)  ·  Deck KPIs 49
Gates: all pass. Unstable KPIs: none.

## Deck KPIs
| id | name | w | s (runs) | evidence (+/-) |
|---|---|---|---|---|
| D-01 | Narrative and storyline | 5 | 2 (2,2,2) | - Mostly topic titles ('Q4 delivery board'); - Slides are unrelated examples with no argument |
| D-02 | Consistency as one system | 4 | 4 (4,4,4) | + Eyebrow, serif title, legend and footer fixed; - Japanese slide eyebrow differs in font |
| D-03 | Variety of form | 3 | 4 (4,4,4) | + Fishbone, kanban, journey, treemap: forms fit content; + Fishbone repeated only for parallel root-cause content |
| D-04 | Pacing and framing slides | 3 | 2 (2,2,2) | - No cover or closing; starts on a content slide |
| D-05 | Fit to purpose and audience | 3 | 3 (3,3,3) | + Consistent showcase density; - Language switch on last slide; meta footer |

## Slides
| # | topic | general | topic | raw | cap | score (range) | band | weakest KPIs (loss) |
|---|---|---|---|---|---|---|---|---|
| 1 | System, architecture and concept diagram | 74 | 80 | 76 | - | 76 (73-77) | Good | T-SYS-03 (2.5), G-09 (2.5), G-06 (2.5) |
| 2 | System, architecture and concept diagram | 74 | 75 | 74 | - | 74 (68-82) | Acceptable / Good (borderline) | G-09 (2.5), G-01 (2.5), G-11 (2.0) |
| 3 | System, architecture and concept diagram | 69 | 74 | 71 | - | 71 (69-74) | Acceptable / Good (borderline) | T-SYS-03 (2.5), G-09 (2.5), G-06 (2.5) |
| 4 | System, architecture and concept diagram | 63 | 67 | 64 | - | 64 (59-73) | Acceptable / Good (borderline) | G-06 (2.5), G-03 (2.5), G-01 (2.5) |
| 5 | System, architecture and concept diagram + Dense Japanese business slide (overlay) | 74 | 70 | 72 | - | 72 (69-73) | Acceptable / Good (borderline) | T-JA-02 (3.8), T-SYS-03 (2.5), G-09 (2.5) |

## Top fixes (gates first, then by weighted loss)
1. Slide 5, T-JA-02 Key message line and conclusion-first (level 2, loss 3.8): No lead line; title is a topic
2. Slide 1, G-01 One message, true to content (level 3, loss 2.5): Title poses the question but does not state the cause
3. Slide 1, G-06 Type scale, size floor and CJK (level 3, loss 2.5): Mono cause labels small (about 11 pt)
4. Slide 1, G-09 Contrast and non-text contrast (level 3, loss 2.5): Grey mono cause labels and grey ticks are faint
5. Slide 1, T-SYS-03 Label legibility and fit (level 3, loss 2.5): Small grey cause text

## Evidence lines
slide | KPI | s (runs) | sign | what is seen
S1 | G-01 | 3 (3,3,3) | - | Title poses the question but does not state the cause
S1 | G-01 | 3 (3,3,3) | + | Effect box (-18%) and highlighted Product bone carry the answer
S1 | G-02 | 5 (5,5,5) | + | Fishbone is the standard form for root-cause categories
S1 | G-03 | 4 (4,4,4) | + | Orange Product bone and effect box form one focal pair
S1 | G-04 | 4 (4,4,4) | + | Category boxes on two rows with equal spacing; spine straight
S1 | G-05 | 4 (4,4,4) | + | Diagram spans body width with even margins
S1 | G-06 | 3 (3,3,3) | + | Clear roles: serif title, caps categories, mono causes
S1 | G-06 | 3 (3,3,3) | - | Mono cause labels small (about 11 pt)
S1 | G-07 | 5 (5,4,5) | + | Two- or three-word causes only
S1 | G-08 | 5 (5,5,4) | + | Orange marks main cause and effect only; legend explains
S1 | G-09 | 3 (3,3,3) | + | Bones and categories dark
S1 | G-09 | 3 (3,3,3) | - | Grey mono cause labels and grey ticks are faint
S1 | G-10 | 5 (5,5,4) | + | Accent spent once on the main cause and effect
S1 | G-11 | 4 (4,3,4) | + | Shape, effect and main cause visible at half size
S1 | G-12 | 4 (4,4,4) | + | Bones meet spine cleanly; labels clear of lines
S1 | G-13 | 4 (5,4,4) | + | Technical editorial system: caps eyebrow, serif title, mono labels
S1 | G-14 | N/A  | ? | (no evidence given)
S1 | T-SYS-01 | 5 (5,5,4) | + | Cause categories feed the effect; legend defines line roles
S1 | T-SYS-02 | 5 (5,5,4) | + | One main cause highlighted; rest quiet
S1 | T-SYS-03 | 3 (3,3,4) | + | All labels fit
S1 | T-SYS-03 | 3 (3,3,4) | - | Small grey cause text
S1 | T-SYS-04 | 4 (4,4,4) | + | Straight bones, no crossings
S1 | T-SYS-05 | 4 (4,4,4) | + | Six categories, nine causes; right scope
S2 | G-01 | 3 (3,3,3) | - | Title 'Q4 delivery board' is a label
S2 | G-01 | 3 (3,3,3) | + | Blocked card and 3/2 counter carry a visible point
S2 | G-02 | 4 (5,4,4) | + | Kanban columns with counts suit status of work
S2 | G-03 | 4 (4,4,4) | + | Orange blocked card is the single focal item
S2 | G-04 | 5 (5,4,5) | + | Four equal columns; cards share edges and pitch
S2 | G-05 | 3 (3,3,3) | - | Dead bands above the board and below the legend
S2 | G-06 | 4 (4,3,4) | + | Bold card titles, mono meta; consistent roles
S2 | G-06 | 4 (4,3,4) | - | Column headers small
S2 | G-07 | 4 (5,4,4) | + | Card = name, ID, owner only
S2 | G-08 | 5 (5,5,4) | + | Orange = problem (blocked, over WIP); grey = done
S2 | G-09 | 3 (3,3,4) | + | Card text dark on white
S2 | G-09 | 3 (3,3,4) | - | Waiting card text and legend swatches faint
S2 | G-10 | 5 (5,5,4) | + | Accent only on blocked card and over-limit counter
S2 | G-11 | 3 (4,3,3) | + | Board recognised instantly
S2 | G-11 | 3 (4,3,3) | - | WIP breach needs reading the small badge
S2 | G-12 | 5 (5,4,5) | + | Clean cards, even padding
S2 | G-13 | 4 (5,4,4) | + | Same eyebrow, legend and mono system as deck
S2 | G-14 | N/A  | ? | (no evidence given)
S2 | T-SYS-01 | 4 (5,4,4) | + | Columns = status; card styles defined in legend
S2 | T-SYS-02 | 4 (5,4,4) | + | One blocked card accented; rest neutral
S2 | T-SYS-03 | 4 (4,3,4) | + | Labels readable and padded
S2 | T-SYS-04 | 4 (4,4,4) | + | No connectors needed; none misused
S2 | T-SYS-05 | 4 (4,4,4) | + | Nine cards, four columns; right scope
S3 | G-01 | 3 (3,3,3) | - | Title is a topic label
S3 | G-01 | 3 (3,3,3) | + | Orange dip and caption make the pain point obvious
S3 | G-02 | 4 (5,4,4) | + | Sentiment line over stages with neutral baseline
S3 | G-03 | 4 (4,4,4) | + | Orange low point wins the look
S3 | G-04 | 4 (4,4,4) | + | Stage headers, dots and captions share column centres
S3 | G-05 | 3 (3,3,3) | - | Empty band below the legend
S3 | G-06 | 3 (3,3,3) | + | Consistent mono captions
S3 | G-06 | 3 (3,3,3) | - | Captions and stage labels small (about 11 pt)
S3 | G-07 | 4 (5,4,4) | + | One short caption per stage
S3 | G-08 | 5 (5,5,5) | + | Single orange for pain point, repeated in caption
S3 | G-09 | 3 (3,3,3) | - | Grey mono captions and dashed neutral line light
S3 | G-10 | 5 (5,5,5) | + | Accent spent once on the pain point
S3 | G-11 | 4 (4,4,4) | + | Dip visible at thumbnail
S3 | G-11 | 4 (4,4,4) | - | Captions vanish at half size
S3 | G-12 | 4 (4,4,4) | + | Clean line and dots, no overlaps
S3 | G-13 | 4 (5,4,4) | + | Same editorial-technical style
S3 | G-14 | N/A  | ? | (no evidence given)
S3 | T-SYS-01 | 4 (4,4,4) | + | Height vs neutral line encodes sentiment
S3 | T-SYS-01 | 4 (4,4,4) | - | No axis says up is positive
S3 | T-SYS-02 | 5 (5,4,5) | + | One focal point; others neutral
S3 | T-SYS-03 | 3 (3,3,3) | + | Labels fit
S3 | T-SYS-03 | 3 (3,3,3) | - | Small grey captions
S3 | T-SYS-04 | 4 (4,4,4) | + | Single line connects stages in order
S3 | T-SYS-05 | 4 (4,4,4) | + | Four stages; scope fits
S4 | G-01 | 3 (3,2,3) | - | Title is a topic phrase
S4 | G-01 | 3 (3,2,3) | - | Highlight on Fees while Payments dominates; two messages
S4 | G-02 | 4 (5,4,4) | + | Treemap areas match 46/27/15/12 percent
S4 | G-03 | 3 (3,2,3) | - | Largest Payments box and orange Fees box compete
S4 | G-04 | 4 (5,4,4) | + | Tight tiling, labels at same inset
S4 | G-05 | 3 (3,3,3) | - | Tiles mostly empty white; labels crowded top-left
S4 | G-06 | 3 (3,3,4) | + | Bold label plus mono sublabel
S4 | G-06 | 3 (3,3,4) | - | Sublabels small; labels same size in all tiles
S4 | G-07 | 4 (5,4,4) | + | Name, share, two example words
S4 | G-08 | 4 (4,4,4) | + | One accent tile
S4 | G-08 | 4 (4,4,4) | - | Accent not explained by title
S4 | G-09 | 4 (4,4,4) | + | Dark labels on white tiles
S4 | G-10 | 3 (3,3,4) | - | Emphasis on Fees, not the title's main point
S4 | G-11 | 3 (4,3,3) | + | Biggest share obvious
S4 | G-11 | 3 (4,3,3) | - | Why Fees is orange needs reading
S4 | G-12 | 4 (5,4,4) | + | Blocks tile exactly; no clipping
S4 | G-13 | 4 (5,4,4) | + | Consistent with deck style
S4 | G-14 | N/A  | ? | (no evidence given)
S4 | T-SYS-01 | 4 (5,4,4) | + | Area-proportional parts of the whole
S4 | T-SYS-02 | 3 (3,3,3) | + | One accent tile
S4 | T-SYS-02 | 3 (3,3,3) | - | Focal tile not named in title
S4 | T-SYS-03 | 4 (4,4,4) | + | Labels readable, padded
S4 | T-SYS-04 | 4 (4,4,4) | + | No connectors; tiling clean
S4 | T-SYS-05 | 3 (3,3,3) | + | Four categories sum to 100%
S4 | T-SYS-05 | 3 (3,3,3) | - | No total hours or period given
S5 | G-01 | 3 (3,3,3) | - | Title '品質不良の要因分析' is a topic label
S5 | G-01 | 3 (3,3,3) | + | Effect box and highlighted 機械 bone carry the point
S5 | G-02 | 5 (5,5,5) | + | 特性要因図 is the conventional form for this analysis
S5 | G-03 | 4 (4,4,4) | + | Orange 機械 bone and result box are the focal pair
S5 | G-04 | 4 (4,4,4) | + | Category boxes on two rows, equal spacing
S5 | G-05 | 4 (4,4,4) | + | Diagram, legend and note fill the slide evenly
S5 | G-06 | 3 (3,3,3) | + | CJK renders cleanly
S5 | G-06 | 3 (3,3,3) | - | Category labels about 10 pt; odd spaces in '( 4 月)'
S5 | G-07 | 5 (5,4,5) | + | Short noun phrases with specific facts (成形機３号, 週１回)
S5 | G-08 | 5 (5,5,4) | + | Orange only for main cause and result; legend explains
S5 | G-09 | 3 (3,3,3) | - | Grey cause labels and ticks are light
S5 | G-09 | 3 (3,3,3) | + | Category labels dark
S5 | G-10 | 5 (5,5,4) | + | Emphasis once on the main cause
S5 | G-11 | 4 (4,3,4) | + | Effect number and main bone readable at half size
S5 | G-12 | 4 (4,3,4) | + | No overlaps; labels clear of bones
S5 | G-12 | 4 (4,3,4) | - | Eyebrow uses different font and spacing
S5 | G-13 | 4 (4,4,4) | + | Same system as slide 1
S5 | G-13 | 4 (4,4,4) | - | Eyebrow lacks the mono letter-spaced style
S5 | G-14 | N/A  | ? | (no evidence given)
S5 | T-JA-01 | 4 (4,4,4) | + | Two category rows, spine, legend and note in clear zones
S5 | T-JA-02 | 2 (2,2,2) | - | No lead line; title is a topic
S5 | T-JA-03 | 4 (4,4,4) | + | All labels one line; number+unit kept together
S5 | T-JA-04 | 3 (3,3,3) | + | Labels about 10-11 pt
S5 | T-JA-04 | 3 (3,3,3) | - | Grey labels lower contrast
S5 | T-JA-05 | 4 (4,4,4) | + | ※ note gives period and scope at bottom left
S5 | T-JA-06 | 4 (5,4,4) | + | Grey/navy base, one orange accent
S5 | T-SYS-01 | 5 (5,5,4) | + | Six cause categories feed the result; legend defines lines
S5 | T-SYS-02 | 5 (5,5,4) | + | One main cause accented
S5 | T-SYS-03 | 3 (3,3,3) | + | All labels fit
S5 | T-SYS-03 | 3 (3,3,3) | - | Small labels near 10 pt
S5 | T-SYS-04 | 4 (4,4,4) | + | Straight bones, no crossings
S5 | T-SYS-05 | 4 (4,5,4) | + | Six categories, eight causes

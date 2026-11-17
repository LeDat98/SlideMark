# Design report: 30-html-diagrams  (rubric v1, judge claude-opus-5-5, R=3 runs, 2026-11-15)

## Summary
Deck **65** (63-70)  Acceptable  ·  Slides 72 (bottom quartile 70)  ·  Deck KPIs 49
Gates: all pass. Unstable KPIs: none.

## Deck KPIs
| id | name | w | s (runs) | evidence (+/-) |
|---|---|---|---|---|
| D-01 | Narrative and storyline | 5 | 2 (2,2,2) | + Every title is a claim sentence; - Slides are separate examples; slide 5 unrelated factory topic; no arc |
| D-02 | Consistency as one system | 4 | 4 (4,4,4) | + Eyebrow, title, legend, footer and page number fixed on all slides; - Slide 5 title font differs (Japanese) |
| D-03 | Variety of form | 3 | 4 (4,4,4) | + Fishbone, kanban, journey line, treemap: form follows content; - Fishbone repeated on slides 1 and 5 |
| D-04 | Pacing and framing slides | 3 | 2 (2,1,2) | - No cover or closing; starts and ends mid-content |
| D-05 | Fit to purpose and audience | 3 | 3 (4,3,3) | + Sparse presentation density; - Mixed language and small mono text |

## Slides
| # | topic | general | topic | raw | cap | score (range) | band | weakest KPIs (loss) |
|---|---|---|---|---|---|---|---|---|
| 1 | System, architecture and concept diagram | 75 | 75 | 75 | - | 75 (75-85) | Good / Excellent (borderline) | T-SYS-03 (1.2), T-SYS-01 (1.2), G-12 (1.2) |
| 2 | System, architecture and concept diagram | 72 | 69 | 71 | - | 71 (68-81) | Acceptable / Good (borderline) | T-SYS-03 (2.5), G-12 (2.5), G-05 (2.5) |
| 3 | System, architecture and concept diagram | 76 | 74 | 75 | - | 75 (71-82) | Good | T-SYS-03 (2.5), G-12 (2.5), G-06 (2.5) |
| 4 | Data chart | 69 | 71 | 70 | - | 70 (67-73) | Acceptable / Good (borderline) | G-05 (2.5), G-03 (2.5), G-01 (2.5) |
| 5 | System, architecture and concept diagram + Dense Japanese business slide (overlay) | 70 | 72 | 71 | - | 71 (73-79) | Good | T-JA-02 (3.1), G-12 (2.5), G-06 (2.5) |

## Top fixes (gates and soft gates first, then by weighted loss)
1. Slide 5, T-JA-02 Key message line and conclusion-first (level 2.5, loss 3.1): No lead line
2. Slide 2, G-05 White space and density (level 3, loss 2.5): Empty band under title and under legend; Review/Done columns mostly empty
3. Slide 2, G-12 Fidelity and polish (level 3, loss 2.5): Orphan 'Q4' line makes blocked card taller than siblings
4. Slide 2, T-SYS-03 Label legibility and fit (level 3, loss 2.5): Awkward wrap of 'Q4'
5. Slide 3, G-05 White space and density (level 3, loss 2.5): Dead band under title and below legend

## Evidence lines
slide | KPI | s (runs) | sign | what is seen
S1 | G-01 | 4 (4,4,4) | + | Title is a causal claim; Product branch and effect box highlighted to match
S1 | G-01 | 4 (4,4,4) | - | No data shown proving slow page outweighs other causes
S1 | G-02 | 4 (4,4,5) | + | Fishbone is the standard form for root-cause grouping
S1 | G-03 | 4 (4,4,4) | + | Orange Product branch and effect box at right draw the eye after title
S1 | G-04 | 4 (4,4,5) | + | Category boxes share two rows with equal spacing; spine centred
S1 | G-04 | 4 (4,4,5) | - | Bottom boxes offset from top boxes, slightly irregular rhythm
S1 | G-05 | 4 (4,4,4) | + | Even margins; diagram fills body; legend separated by rule
S1 | G-06 | 4  | + | Caps category, mono cause, bold effect: clear roles
S1 | G-07 | 4 (4,4,5) | + | Sub-causes are 2-3 word fragments; effect has number
S1 | G-08 | 4 (4,4,5) | + | One orange accent for main cause and effect; legend explains it
S1 | G-09 | 4  | + | Dark text on light grey; dark bones clear
S1 | G-09 | 4  | - | Light grey sub-cause ticks are faint
S1 | G-10 | 4 (4,4,4) | + | Accent only on Product branch and effect box
S1 | G-11 | 4 (4,4,4) | + | Orange branch and effect box readable at thumbnail size
S1 | G-12 | 4 (4,4,5) | + | No overlaps; ticks meet bones; labels clear of lines
S1 | G-13 | 4 (4,4,5) | + | Serif title, mono labels, thin strokes form one editorial system
S1 | G-14 | N/A  | ? | (no evidence given)
S1 | T-SYS-01 | 4 (4,4,5) | + | Bones into spine into effect show cause-effect; legend defines line types
S1 | T-SYS-02 | 4 (5,4,4) | + | One accented category and effect
S1 | T-SYS-02 | 4 (5,4,4) | - | 'Slow page' label itself not accented
S1 | T-SYS-03 | 4 (4,4,4) | + | All labels fit with padding
S1 | T-SYS-03 | 4 (4,4,4) | - | Sub-cause mono text small
S1 | T-SYS-04 | 4 (4,4,5) | + | Straight bones attach to spine; no crossings
S1 | T-SYS-05 | 4 (4,4,4) | + | Six categories, nine causes: right amount for one slide
S2 | G-01 | 4 (4,4,4) | + | Title claim matches highlighted blocked card with 'blocks Q4'
S2 | G-01 | 4 (4,4,4) | - | Other cards are context not tied to the claim
S2 | G-02 | 4 (4,4,5) | + | Kanban columns show work state left to right
S2 | G-03 | 4 (4,4,4) | + | Blocked card with red bar and pink fill is the focal card
S2 | G-04 | 5 (5,4,5) | + | Four equal columns, equal card widths and gaps, shared tops
S2 | G-05 | 3 (3,3,4) | + | Even margins and gutters
S2 | G-05 | 3 (3,3,4) | - | Empty band under title and under legend; Review/Done columns mostly empty
S2 | G-06 | 4  | + | Bold card titles, mono ids, small column heads
S2 | G-07 | 4 (4,4,5) | + | Cards hold name, ID, owner only
S2 | G-08 | 4 (4,4,5) | + | Orange only for blocked and over-WIP; grey for done; legend given
S2 | G-09 | 4  | + | Dark card text on white
S2 | G-09 | 4  | - | Waiting card text faded grey on grey
S2 | G-10 | 4 (4,4,5) | + | Emphasis only on blocked card and 3/2 badge, same meaning
S2 | G-11 | 4 (4,4,4) | + | Blocked card and title readable at half size
S2 | G-12 | 3 (3,3,3) | + | No overflow or overlap
S2 | G-12 | 3 (3,3,3) | - | Orphan 'Q4' line makes blocked card taller than siblings
S2 | G-13 | 4 (4,4,5) | + | Card radius, strokes and mono meta consistent with deck
S2 | G-14 | N/A  | ? | (no evidence given)
S2 | T-SYS-01 | 4 (4,4,5) | + | Columns encode status; card styles encode state per legend
S2 | T-SYS-02 | 4 (4,4,5) | + | One focal card plus related WIP badge; rest neutral
S2 | T-SYS-03 | 3 (4,3,3) | + | Labels fit cards
S2 | T-SYS-03 | 3 (4,3,3) | - | Awkward wrap of 'Q4'
S2 | T-SYS-04 | 4 (4,4,4) | + | No connectors needed; column order implies flow
S2 | T-SYS-05 | 4 (4,4,4) | + | Eight cards in four columns, scope fits
S3 | G-01 | 5 (4,5,5) | + | Claim title; red low point at CHECKOUT with cause caption
S3 | G-02 | 4 (4,4,5) | + | Sentiment line across ordered stages fits a journey
S3 | G-03 | 5 (5,4,5) | + | Large red dot at checkout wins the first look after title
S3 | G-04 | 4 (4,4,4) | + | Stage headers, dots and captions share four column centres
S3 | G-05 | 3 (3,3,4) | + | Margins even
S3 | G-05 | 3 (3,3,4) | - | Dead band under title and below legend
S3 | G-06 | 3  | + | Few sizes with clear roles
S3 | G-06 | 3  | - | Captions wrap leaving orphans '3' and 'shop'
S3 | G-07 | 4 (4,4,5) | + | One short caption per stage
S3 | G-08 | 4 (4,4,5) | + | Red reserved for pain point; legend explains
S3 | G-09 | 4  | + | Dark line and dots clear on light ground
S3 | G-09 | 4  | - | Neutral dashed line pale
S3 | G-10 | 5 (5,5,5) | + | Emphasis spent once: the checkout point and caption
S3 | G-11 | 5 (5,4,5) | + | V-shaped dip with red point lands in one look
S3 | G-12 | 3 (3,3,3) | + | No overlaps
S3 | G-12 | 3 (3,3,3) | - | Single-word orphan lines in two captions
S3 | G-13 | 4 (4,4,5) | + | Same editorial system as other slides
S3 | G-14 | N/A  | ? | (no evidence given)
S3 | T-SYS-01 | 4 (4,4,4) | + | Stages in order with sentiment above/below neutral line
S3 | T-SYS-02 | 5 (5,5,5) | + | One red focal point, others dark neutral; legend explains
S3 | T-SYS-03 | 3 (3,3,3) | + | Captions readable
S3 | T-SYS-03 | 3 (3,3,3) | - | Awkward wraps with one-word last lines
S3 | T-SYS-04 | 4 (4,4,5) | + | Straight segments joining dots; no crossings
S3 | T-SYS-05 | 4 (4,4,4) | + | Four stages, one rating each: right scope
S4 | G-01 | 3 (3,3,3) | + | Percentages match tile areas and title
S4 | G-01 | 3 (3,3,3) | - | Title carries two claims; '3x' growth not shown visually
S4 | G-02 | 4 (4,4,4) | + | Treemap areas proportional to shares (46/27/15/12)
S4 | G-03 | 3 (3,3,3) | - | Payments wins by size, Fees by colour: two focal points
S4 | G-04 | 5 (5,4,5) | + | Tiles share edges with even gutters; labels at same inset
S4 | G-05 | 3 (3,3,3) | + | Treemap fills body edge to edge
S4 | G-05 | 3 (3,3,3) | - | Large blank tile interiors carry nothing
S4 | G-06 | 4  | + | Three sizes: title, bold tile labels, mono notes
S4 | G-07 | 4 (4,4,5) | + | Each tile: name, share, two-word driver
S4 | G-08 | 4 (3,4,4) | + | One accent tile
S4 | G-09 | 4  | + | Dark text on white tiles; clear borders
S4 | G-10 | 3 (3,3,4) | - | Emphasis on the secondary message only
S4 | G-11 | 4 (4,4,4) | + | Big Payments tile and 46% visible at thumbnail
S4 | G-12 | 4 (4,4,5) | + | No clipping or overlap; tile edges exact
S4 | G-13 | 4 (4,4,4) | + | Consistent with deck system
S4 | G-14 | N/A  | ? | (no evidence given)
S4 | T-CHART-01 | 4 (4,4) | + | Treemap of four parts for part-to-whole
S4 | T-CHART-02 | 4 (4,4) | + | Tile areas match percentages
S4 | T-CHART-03 | 4.5 (4,5) | + | Direct labels with %; unit in title
S4 | T-CHART-03 | 4.5 (4,5) | - | No period
S4 | T-CHART-04 | 3 (3,3) | + | One accent tile
S4 | T-CHART-04 | 3 (3,3) | - | Accent on fees while title leads with payments
S4 | T-CHART-05 | 4 (4,4) | + | No grid or effects
S4 | T-CHART-06 | 3.5 (4,3) | + | Title states finding with numbers
S4 | T-CHART-06 | 3.5 (4,3) | - | No period or source
S4 | T-SYS-01 | 4  | + | Area encodes share of hours correctly
S4 | T-SYS-02 | 3  | - | Size and colour point to different tiles
S4 | T-SYS-03 | 4  | + | Labels readable and padded inside tiles
S4 | T-SYS-04 | 4  | + | No connectors needed; adjacency shows whole
S4 | T-SYS-05 | 4  | + | Four categories cover the whole
S5 | G-01 | 4 (4,4,4) | + | Title claim matches highlighted 機械 branch and 0.8%→2.1% effect
S5 | G-01 | 4 (4,4,4) | - | No data proving machine 3 dominates other causes
S5 | G-02 | 4 (4,4,5) | + | Fishbone fits root-cause analysis with 6M categories
S5 | G-03 | 4 (4,4,4) | + | Orange branch and effect box are the focal pair
S5 | G-04 | 4 (4,4,5) | + | Categories on two rows, equal spacing, legend aligned left
S5 | G-05 | 4 (4,4,4) | + | Balanced; footnote and legend separated from diagram
S5 | G-06 | 3  | + | Gothic CJK renders cleanly
S5 | G-06 | 3  | - | Serif Latin '3' in Gothic title; labels about 10-11pt
S5 | G-07 | 4 (4,4,5) | + | Short noun-phrase causes; footnote gives period
S5 | G-08 | 4 (4,4,5) | + | Single orange accent with legend
S5 | G-09 | 4  | + | Dark text on light ground
S5 | G-09 | 4  | - | Sub-cause ticks pale grey
S5 | G-10 | 4 (4,4,4) | + | Accent only on main branch and result
S5 | G-11 | 4 (4,4,4) | + | Result box numbers and orange branch survive half size
S5 | G-12 | 3 (3,3,4) | + | No clipping or overlap
S5 | G-12 | 3 (3,3,4) | - | Mismatched serif digit and spaced '3 号' in title
S5 | G-13 | 4 (4,4,5) | + | Same system as English fishbone, adapted for Japanese
S5 | G-14 | N/A  | ? | (no evidence given)
S5 | T-JA-01 | 4 (4,4) | + | Category heads group causes clearly
S5 | T-JA-02 | 2.5 (3,2) | + | Title is the conclusion
S5 | T-JA-02 | 2.5 (3,2) | - | No lead line
S5 | T-JA-03 | 4 (4,4) | + | No overflow; number+unit kept together
S5 | T-JA-03 | 4 (4,4) | - | Extra spaces around digits
S5 | T-JA-04 | 4 (4,4) | + | Body ~11pt gothic, bold heads
S5 | T-JA-05 | 4 (4,4) | + | ※ note gives period, plant and scope; % unit shown
S5 | T-JA-06 | 4.5 (4,5) | + | Grey base, single red accent
S5 | T-SYS-01 | 4 (4,4,5) | + | Cause categories feed spine to result; legend defines lines
S5 | T-SYS-02 | 4 (5,4,4) | + | One accented category
S5 | T-SYS-03 | 4 (4,4,4) | + | CJK labels fit with padding, no clipping
S5 | T-SYS-04 | 4 (4,4,5) | + | Straight bones attach cleanly, no crossings
S5 | T-SYS-05 | 4 (4,4,4) | + | Six categories, nine causes; footnote states scope

## Measured facts
- slide 1: title 30.6 pt; min node 9.75 pt (floor 10); min label 10 pt (floor 8); min footnote 12 pt (floor 8); min text contrast 4.5:1 ('Text 3' 'PRODUCT'); min non-text contrast 11.8:1 (arrow 'Shape 1'); empty body 0% (rows 0%, columns 0%; weak >= 40%)
- slide 2: title 30.6 pt; min node 9.9 pt (floor 10); min label 10 pt (floor 8); min footnote 12 pt (floor 8); min text contrast 4.7:1 ('Text 10' '3\u2060/\u20602'); empty body 27% (rows 27%, columns 0%; weak >= 40%)
- slide 3: title 28.8 pt; min node 9.9 pt (floor 10); min label 10 pt (floor 8); min footnote 12 pt (floor 8); min text contrast 4.7:1 ('Text 8' 'Surprise shipping '); empty body 29% (rows 29%, columns 0%; weak >= 40%)
- slide 4: title 34.19 pt; min node 11.55 pt (floor 10); min label 10 pt (floor 8); min footnote 12 pt (floor 8); min text contrast 5.3:1 ('Eyebrow' 'TREEMAP · SUPPORT'); empty body 0% (rows 0%, columns 0%; weak >= 40%)
- slide 5: title 36 pt; min node 9.9 pt (floor 10); min label 10 pt (floor 8); min footnote 10 pt (floor 8); min text contrast 4.5:1 ('Text 3' '機械（設備）'); min non-text contrast 11.8:1 (arrow 'Shape 1'); empty body 0% (rows 0%, columns 0%; weak >= 40%)

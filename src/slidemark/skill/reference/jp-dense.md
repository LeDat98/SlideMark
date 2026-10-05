# Dense Japanese business slides

Use `theme: jp-business` and `lang: ja`. Defaults: navy title band, 11pt body, 10.5pt tables, box heading
bands, `※` footnotes at 9pt, Yu Gothic (`<a:ea>`) for Japanese text.

Pattern (one message, evidence boxes, source line):

````markdown
# 国内市場の動向
> 市場は年率12%で拡大、中堅企業が成長を牽引
@1:1
```column {title="市場規模（億円）" labels=on}
,2024,2025,2026
大企業,930,990,1040
中堅,560,650,760
```
## 主なトレンド
- インボイス対応で導入が加速
- 中堅企業のSaaS比率が ==42%==
※ 出所：業界団体調査（2026年8月）
````

Checklist:
- Lead `>` = the conclusion of the slide in one sentence (〜する / 〜が必要).
- 3–4 boxes per row at most; `@aab/aac` for "main + two supports"; `@4 chevron` + `@end` + table for plans.
- Keep bullets to one line (≈ 25 full-width chars per column of a 3-column slide).
- Numbers: half-width digits, units in Japanese (`12.4億円`, `+8%`), `▲` for negatives in tables.
- `density: dense` (deck) or `@dense` (slide) when a slide is packed; split the slide if `check` still warns.
- Full-width punctuation is fine; line breaking follows kinsoku rules (no 、。」 at line start).

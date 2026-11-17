theme: none
lang: ja
num: on
colors: bg=#0A0F1F fg=#E8ECF8 primary=#38BDF8 secondary=#A78BFA accent=#F472B6 surface=#121A33 border=#26324F muted=#94A3C4
fonts: heading="Noto Sans JP" body="Noto Sans JP" ea="Noto Sans JP"
sizes: title=32 body=18
style: radius=16 title.band=none card.shadow="0 6 18 #00000066"
```css
slide { background: linear-gradient(160deg, #0A0F1F, #111A3A) }
h1 { font-size: 30pt; letter-spacing: 0.5pt }
.lead { color: #38BDF8 }
.box { background: linear-gradient(180deg, #16203F, #10182F); border: 1px solid #26324F }
.box > h2 { color: #A78BFA; font-size: 15pt }
.kpi { color: #38BDF8 }
th { background: #1B2A55; color: #E8ECF8 }
td { border-color: #26324F }
.conclusion { background: linear-gradient(90deg, #38BDF8, #A78BFA); color: #0A0F1F }
```

# 現場の点検を、AIで10分に
@html noemph defaults
```html
<div style="height:100%;display:flex;flex-direction:column;justify-content:center;padding:0 96px;background:radial-gradient(circle at 80% 20%,#38BDF855,transparent 45%),radial-gradient(circle at 10% 90%,#A78BFA44,transparent 40%),#0A0F1F;color:#E8ECF8">
  <div style="font-size:18px;letter-spacing:6px;color:#38BDF8">SERIES A ・ 2026</div>
  <h1 style="font-size:64px;margin:24px 0 16px">現場の点検を、AIで10分に</h1>
  <p style="font-size:24px;color:#94A3C4;margin:0">InspectAI株式会社　インフラ点検の自動化プラットフォーム</p>
</div>
```

# 課題：点検は人手に依存し続けている
> 国内の橋梁・トンネルの点検は年 7.2万件、技術者は10年で 3割減る
@noemph
## 人手不足 {icon=users}
- 点検技術者の平均年齢 54歳
- 若手の採用は年 ▲8%
## コスト {icon=yen}
- 1件あたり平均 38万円
- 足場・交通規制が費用の 6割
## 品質のばらつき {icon=warning}
- 判定の一致率は 71%
- 記録の 4割が手書き

# プロダクトの成果
> 導入 120自治体で、点検時間を 82% 削減した
## 点検時間 {.kpi}
▲82%
平均 55分 → 10分
## 判定一致率 {.kpi}
96%
技術者 3名の合議と比較
## 継続率 {.kpi}
99%
自治体の年間契約
@end
```column {title="導入自治体数" labels=on colors=primary hl=2026}
,2023,2024,2025,2026
導入数,8,31,74,120
```

# 調達計画
> シリーズAで 25億円を調達し、2028年に ARR 40億円を目指す
{hl=開発 widths=1:1:4 align=lrl}
| 用途 | 金額 | 内容 |
|-|-|-|
| 開発 | 11億円 | 3D点群の自動判定、ドローン連携 |
| 営業 | 8億円 | 都道府県・高速道路会社へ展開 |
| 海外 | 4億円 | 東南アジアで 3か国の実証 |
| 運転資金 | 2億円 | 18か月分 |
> 2027年に黒字化、2028年に ARR 40億円

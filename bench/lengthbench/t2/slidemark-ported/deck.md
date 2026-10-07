theme: none
lang: ja
footer: 青葉フーズ株式会社
num: on
colors: bg=#FFFFFF fg=#222B36 primary=#142B4D secondary=#1F5FA8 accent=#E09F1F teal=#217B70 muted=#59626E surface=#EEF2F7 border=#C9D2DE
fonts: heading="Yu Gothic" body="Yu Gothic" ea="Yu Gothic"
sizes: title=28 lead=18 heading=20 body=22 table=20 footnote=13 caption=10
style: title.band=none title.color=primary lead.color=secondary lead.bold=on heading.band=primary card.radius=0 kpi.color=secondary conclusion.fill=secondary palette=secondary,accent,#2A9D8F,#8A5AA8 table.header.fill=primary table.header.color=#FFFFFF table.zebra.fill=surface render.chart_line_width=3.5 layout.kpi_lone_h=0.9 layout.kpi_lone_min_h=0.85
```css
h1 { border-bottom: 2px solid #1F5FA8; font-weight: bold }
.box > h2 { text-align: center; font-weight: bold; font-size: 20pt }
.box li { font-size: 22pt }
.conclusion { font-size: 24pt; font-weight: bold }
.kpi { border-top: 6pt solid #1F5FA8; font-size: 34pt }
.kpi h2 { font-size: 20pt; font-weight: bold; color: #142B4D }
.kpi .caption { font-size: 20pt; font-weight: bold; color: teal }
```

# 2027年度 事業計画
@html
```html
<div style="position:relative;height:100%;background:var(--primary);color:#fff">
<div style="position:absolute;left:0;right:0;top:437px;height:6px;background:var(--accent)"></div>
<div style="position:absolute;left:58px;top:192px;width:12px;height:221px;background:#2A9D8F"></div>
<h1 style="position:absolute;left:96px;top:192px;margin:0;height:144px;display:flex;align-items:center;font-size:72px">2027年度 事業計画</h1>
<p style="position:absolute;left:96px;top:336px;margin:0;height:77px;display:flex;align-items:center;font-size:32px;color:#D6E2F0">青葉フーズ株式会社 経営企画部 2027年3月</p>
</div>
```

# 2027年度の経営目標
> 売上・利益ともに過去最高を目指す
## 売上高 {.kpi}
1,280億円
前年比 +8%
## 営業利益 {.kpi}
96億円
前年比 +12%
## 営業利益率 {.kpi}
7.5%
+0.3pt
## ROE {.kpi}
9.0%
+0.8pt

# 売上高と営業利益の推移（億円）
> 5年間で売上高は1.25倍に
```column {labels=on legend=bottom fmt=#,##0 colors=secondary,accent}
,2023,2024,2025,2026,2027計画
売上高,1020,1085,1130,1185,1280
営業利益,61,70,78,86,96
```

# 4つの重点戦略
@4
## 既存事業の収益改善
- 主力3ブランドの価格改定
- 不採算SKUを15%削減
## 海外展開の加速
- タイ工場の増設
- 北米で冷凍食品を発売
## DXの推進
- 需要予測のAI化
- 受発注の完全電子化
## 人的資本への投資
- 賃上げ率4.5%
- デジタル人材を50名採用
※ 各戦略のKPIは個別資料を参照

# 年間スケジュール
@4 steps
## 4–6月
- 価格改定
## 7–9月 {.secondary}
- タイ工場着工
## 10–12月
- 北米発売
## 1–3月 {.secondary}
- 効果検証
??? 価格改定は主要取引先への説明を3月中に終えます。

# 事業別の売上計画（億円）
```table {align=llll widths=3.9:2.8:2.8:2.6 .zebra hcol=1}
事業,2026実績,2027計画,前年比
冷凍食品,420,465,+11%
調味料,310,325,+5%
飲料,255,270,+6%
海外,200,220,+10%
```
> 冷凍食品と海外が成長をけん引

# 2027年度 売上構成（%）
```pie {labels=on legend=right colors=secondary,accent,#2A9D8F,#8A5AA8}
,冷凍食品,調味料,飲料,海外
構成比,36,25,21,18
```

# 価格改定の方針
@html
```html
<style>
.r{display:flex;height:100px;margin-bottom:17px;background:var(--surface);border:1px solid var(--border)}
.r b{box-sizing:border-box;width:100px;background:var(--primary);color:#fff;font-size:43px;text-align:center;display:flex;align-items:center;justify-content:center}
.r:nth-child(even) b{background:var(--secondary)}
.r span{font-size:35px;padding-left:24px;display:flex;align-items:center}
</style>
<div style="padding:38px 48px 0;position:relative;height:100%">
<h1 style="margin:0;height:86px;display:flex;align-items:center;font-size:37px;color:var(--primary);border-bottom:2px solid var(--secondary)">価格改定の方針</h1>
<p style="margin:6px 0 0;font-size:24px;font-weight:bold;color:var(--secondary)">原材料高を価格に反映し、販売数量を維持する</p>
<div style="margin-top:30px">
<div class="r"><b>1</b><span>主力3ブランドを平均6%改定</span></div>
<div class="r"><b>2</b><span>改定は2027年5月出荷分から</span></div>
<div class="r"><b>3</b><span>容量変更は行わない</span></div>
<div class="r"><b>4</b><span>販促費を前年比10%削減</span></div>
</div>
<div style="position:absolute;left:48px;right:48px;top:677px;display:flex;justify-content:space-between;font-size:13px;color:var(--muted)"><span style="padding:0">青葉フーズ株式会社</span><span style="padding:0">8</span></div>
</div>
```

# 冷凍食品事業の目標
```css
.kpi { font-size: 54pt }
```
## 売上高 {.kpi}
465億円
前年比 +11%
## 新商品比率 {.kpi}
18%
+4pt
## 工場稼働率 {.kpi}
88%
+5pt

# 海外展開の重点地域
```css
.box > h2 { font-size: 26pt }
.box li { font-size: 24pt }
```
## タイ
- 工場の生産能力を1.5倍に
- ASEAN向け輸出拠点
## 北米
- 冷凍餃子を発売
- 大手スーパー3社で展開
## 台湾
- 調味料の現地生産
- コンビニ向けPB

# 海外売上高の推移（億円）
```line {labels=on legend=bottom colors=secondary,accent,#2A9D8F}
,2024,2025,2026,2027計画
タイ,70,82,95,105
北米,20,30,45,60
台湾,40,50,60,55
```

# DX施策の一覧
```table {align=llll widths=3.9:2.8:2.8:2.6 .zebra hcol=1}
施策,対象,効果,時期
需要予測AI,全工場,在庫 -15%,2027年6月
受発注の電子化,主要取引先,工数 -30%,2027年9月
設備の予知保全,3工場,停止時間 -20%,2027年12月
経費精算の自動化,全社,処理時間 -50%,2027年4月
```

# DX推進のロードマップ
@4 steps
## 2027年4月
- 経費精算
## 6月 {.secondary}
- 需要予測AI
## 9月
- 受発注電子化
## 12月 {.secondary}
- 予知保全

# 人的資本の目標
## 賃上げ率 {.kpi}
4.5%
3年連続
## 女性管理職比率 {.kpi}
15%
+3pt
## デジタル人材 {.kpi}
120名
+50名
## エンゲージメント {.kpi}
3.8
+0.2

# 設備投資の配分（億円）
> 設備投資は総額100億円
```bar {labels=on legend=none colors=secondary}
,タイ工場,国内工場更新,DX,研究開発
投資額,45,30,15,10
```
??? タイ工場は2028年4月の稼働を予定しています。

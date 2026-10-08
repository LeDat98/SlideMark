colors: fg=#122B4A primary=#122B4A secondary=#1F5FA8 accent=#E08A1E teal=#1B8A8F muted=#6B7582 tint=#EEF2F7
fonts: body=Meiryo heading=Meiryo
style: title_band=primary table_header_fill=primary radius=0 s1.border-top="9pt solid secondary" s2.border-top="9pt solid teal" s3.border-top="9pt solid accent" ls1.border-left="9pt solid secondary" rows.fill=tint steps-arrow.fill=secondary,teal,accent steps-arrow.size=24 steps-arrow.color=bg steps-arrow.bold=on steps-arrow.align=left steps-card.size=26 steps-arrow.h=0.75in steps.gap=0.2in
style: cover.band=none cover.band_h=66% cover.bar=accent cover.bottom_bar=secondary cover.bottom_bar_h=0.6in title.height=0.95in title.rule=accent title.rule_h=0.06in margin=0.6in layout.top_gap=0.45in render.chevron_shape=pentagon steps-arrow.point=0.5
lang: ja
footer: 北斗クラウド株式会社　取締役会資料
num: on

# 北斗クラウド 中期経営計画 2027–2029
@bg=primary dark
北斗クラウド株式会社 取締役会資料 2027年4月

# 社長メッセージ
sizes: heading=44! body=30!
## [01]{.secondary} {.s1}
**3年で売上を2倍、営業利益率を20%へ**
## [02]{color=#1B8A8F} {.s2}
**顧客の業務時間を年間1,000万時間削減する**
## [03]{color=#E08A1E} {.s3}
**「現場が使い続けるSaaS」をつくる**

# 市場環境
style: ls2.border-left="9pt solid teal" ls3.border-left="9pt solid accent" s4.border-left="9pt solid muted" kpi.fill=tint kpi.align=left kpi.note.align=left kpi.note.size=20 kpi.note.bold=on kpi.note.color=primary
sizes: kpi=48
@2x2 kpi
## {.ls1 color=secondary}
2.1兆円
国内の中小企業向けSaaS市場は2026年の1.2兆円から2029年に2.1兆円へ
## {.ls2 color=#1B8A8F}
38%
クラウド会計の導入率は中小企業で38%
## {.ls3 color=#E08A1E}
+22%
人手不足を理由にITを導入した企業は前年比+22%
## {.s4 color=muted}
41%
競合上位3社のシェア合計は41%

# 2029年度の数値目標
style: rows.stripe=secondary
@rows plain
- **売上高** [420億円]{size=34 .secondary bold}[（2026年度 210億円）]{.muted}
- **営業利益率** [20%]{size=34 .secondary bold}[（同 11%）]{.muted}
- **ARR** [380億円]{size=34 .secondary bold}
- **解約率** [年0.8%以下]{size=34 .secondary bold}[（同 1.4%）]{.muted}
- **有料顧客数** [48,000社]{size=34 .secondary bold}[（同 26,000社）]{.muted}

# 顧客セグメント別の売上構成（2026年度）
@2:1
```bar {labels=on labels.bold=on fmt='0"%"' max=36 axis=off colors=accent,secondary,secondary,secondary,secondary size=18 gap=45}
,製造業,卸・小売,建設・不動産,サービス業,その他
売上構成比,31,24,18,15,12
```
## 構成比（2026年度）
製造業 [**31%**]{size=26 color=#E08A1E}

卸・小売 [**24%**]{size=26 .secondary}

建設・不動産 [**18%**]{size=26 .secondary}

サービス業 [**15%**]{size=26 .secondary}

その他 [**12%**]{size=26 .secondary}

# 3年間のプロダクト計画
style: steps-card.h=2.7in conclusion.h=1.05in
@3 steps
## 2027年度：
**在庫管理と請求書の自動照合をリリース**
## 2028年度：
**AIによる資金繰り予測を全プランに搭載**
## 2029年度：
**業種別テンプレートを30業種に拡大**
> 各年度の第1四半期に大型リリース、第3四半期に改善リリース

# 競合との比較
style: table.hl.fill=#FDF1DE table.hl.strength=1 table.zebra.fill=tint
{.zebra align=lcccc size=15 hl="北斗クラウド：" rowh=0.8in,1.26in widths=3:2:2:2:2}
| | 月額 | 導入日数 | サポート満足度 | API連携数 |
|-|-|-|-|-|
| [北斗クラウド：]{size=20} | [月額]{.muted}<br>[**9,800円**]{size=26 color=#E08A1E} | [導入日数]{.muted}<br>[**3日**]{size=26 color=#E08A1E} | [サポート満足度]{.muted}<br>[**92%**]{size=26 color=#E08A1E} | [API連携数]{.muted}<br>[**120**]{size=26 color=#E08A1E} |
| [**A社：**]{size=20} | [月額]{.muted}<br>[**12,000円**]{size=26 .secondary} | [導入日数]{.muted}<br>[**10日**]{size=26 .secondary} | [サポート満足度]{.muted}<br>[**85%**]{size=26 .secondary} | [API連携数]{.muted}<br>[**80**]{size=26 .secondary} |
| [**B社：**]{size=20} | [月額]{.muted}<br>[**7,500円**]{size=26 .secondary} | [導入日数]{.muted}<br>[**5日**]{size=26 .secondary} | [サポート満足度]{.muted}<br>[**78%**]{size=26 .secondary} | [API連携数]{.muted}<br>[**45**]{size=26 .secondary} |

# 価格改定の方針
style: box.num.fill=secondary,teal,accent,muted box.num.shape=square
@ab/ac/ad/ae num
## [スタンダードプラン]{size=16 color=#C9D6E6} {.kpi fill=primary align=left}
[9,800円]{size=40 .white bold}
[▼]{size=28 color=#E08A1E}
[10,800円]{size=48 color=#E08A1E bold}
[2027年10月から]{.white}
## 2027年10月からスタンダードプランを9,800円から10,800円へ
## 既存顧客は12か月間据え置き
## 年間契約の割引率を10%から15%へ拡大
## 解約率への影響は+0.2ptと想定し、サポート体制で吸収する
??? スタンダードプランの値上げは既存顧客への12か月の猶予と年間契約の割引拡大で痛みを和らげ、解約率の上昇は+0.2ptにとどめる方針です。

# 組織の変更
style: ts4.border-top="9pt solid muted"
sizes: heading=32! body=23!
## [01]{.secondary} {.s1}
**カスタマーサクセス部を営業本部から独立させ、2027年7月に発足**
## [02]{color=#1B8A8F} {.s2}
**AI開発室を新設、2027年度中に20名体制**
## [03]{color=#E08A1E} {.s3}
**地方拠点（福岡・札幌）を営業所から支社へ格上げ**
## [04]{.muted} {.ts4}
**執行役員にCS担当を1名追加**

# 主なリスクと対策
style: table.zebra.fill=bg table.body.fill=tint
{.zebra align=lcl size=22 rowh=0.7in,1.07in widths=5:1:6}
| リスク | | 対策 |
|-|-|-|
| **大手の参入による価格競争：** | [**▶**]{size=20 color=#E08A1E} | 業種特化機能で差別化 |
| **採用難：** | [**▶**]{size=20 color=#E08A1E} | リファラル採用比率を40%へ、年収テーブル改定 |
| **セキュリティ事故：** | [**▶**]{size=20 color=#E08A1E} | ISMAP取得を2028年度に完了 |
| **為替・クラウド費用の上昇：** | [**▶**]{size=20 color=#E08A1E} | 複数クラウド契約で年5%の原価低減 |

# 投資配分（3年間 合計150億円）
@5:2
```bar {labels=on labels.bold=on fmt='0"億円"' max=85 colors=secondary,teal,teal,teal size=18 gap=45}
,プロダクト開発,営業・マーケティング,人材採用・育成,セキュリティ・基盤
投資額（億円）,70,40,25,15
```
## 3年間 合計
### 150億円
プロダクト開発 [**70億円**]{size=18 .secondary}

営業・マーケティング [**40億円**]{size=18 .secondary}

人材採用・育成 [**25億円**]{size=18 .secondary}

セキュリティ・基盤 [**15億円**]{size=18 .secondary}

# 採用計画
sizes: heading=18!
@ab/cb/db/eb
## **2027年度** [120名]{size=28 .secondary}[（うちエンジニア60名）]{.muted} {.ls1}
@end
```stacked-column {labels=on labels.bold=on totals=off colors=secondary,muted size=16}
,2027年度,2028年度,2029年度
エンジニア,60,80,90
その他,60,70,90
```
## **2028年度** [150名]{size=28 .secondary}[（うちエンジニア80名）]{.muted} {.ls1}
## **2029年度** [180名]{size=28 .secondary}[（うちエンジニア90名）]{.muted} {.ls1}
## 女性管理職比率を2029年度に25%へ（2026年度 14%） {fill=primary}

# お客様の声
style: quote.bar=accent quote.bar_w=0.15in quote.h=4.9in quote.width=1 quote.by.align=right
@quote fill=tint size=38
> **「月末の締め作業が3日から半日になった。現場が自分で使えるのが一番の違いです」**
>
> — 株式会社三浦製作所 経理部長

# 地域展開
style: steps-card.h=2.5in conclusion.h=1.3in conclusion.size=26
@3 steps
## 2027年度
[2027年度：]{bold .secondary}**福岡・札幌で地域密着の導入支援を開始**
## 2028年度
[2028年度：]{bold color=#1B8A8F}**名古屋・広島に拠点を追加**
## 2029年度
[2029年度：]{bold color=#E08A1E}**台湾で日系企業向けに提供開始**
> 各拠点で地元の会計事務所と提携し、紹介経由の契約を全体の30%へ

# 取締役会への依頼事項
style: rows-num.fill=secondary,teal,accent,primary layout.rows_h=1.12in
@rows
1. **中期経営計画の承認**
1. **投資枠150億円の承認**
1. **価格改定（2027年10月実施）の承認**
1. **組織変更（CS部独立・AI開発室新設）の承認**
??? 以上四点が本日ご承認をお願いしたい事項であり、承認後は2027年4月から計画を実行に移します。

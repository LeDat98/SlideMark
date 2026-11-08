theme: editorial
lang: en
num: on
colors: accent=#BF4520
fonts: heading=Georgia body=Arial
sizes: title=34 body=17
style: radius=4

# Order platform in three tiers
@arch
@noemph defaults
## Clients
- Web app {.external}
- Mobile app {.external}
## Services
- API gateway: auth, limits {.focal}
- Orders
- Billing
## Data
- Postgres: orders, users {.store}
- Queue {.optional}
- Stripe {.external}
> Web app > API gateway, Mobile app > API gateway, API gateway > Orders: place order, Orders > Billing: invoice, Orders > Postgres: write, Orders > Queue: publish, Billing > Stripe: charge

# 受注データ基盤の構成
@arch dir=h size=12
@noemph defaults
## 入力
- 受注API: 外部ECから受信 {.external}
- 基幹ERP: 在庫・単価マスタ {.external}
## 処理
- 変換バッチ: 正規化・名寄せ
- 与信チェック: 与信枠と滞留 {.focal}
- 在庫引当: 倉庫別の引当
## 保存
- DWH: 全履歴・日次集計 {.store}
- キャッシュ: 直近7日 {.store}
## 出力
- 管理画面: 営業・CS向け
- 日次レポート {.optional}
> 受注API > 変換バッチ: 受信, 基幹ERP > 在庫引当: 同期, 変換バッチ > 与信チェック, 与信チェック > DWH: 保存, 在庫引当 > キャッシュ, DWH > 管理画面: 参照, DWH > 日次レポート: 集計

# What makes an idea worth building
@venn
@noemph defaults
## Desirable
People want it
## Feasible
We can build it
## Viable
It pays for itself
> Worth building {.focal}

# Strategy that ships
@venn
@noemph defaults
## Strategy
Where to play and why
## Execution
Who does what by when
> A plan the team can run

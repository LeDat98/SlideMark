theme: editorial
lang: en
num: on
colors: accent=#BF4520
fonts: heading=Georgia body=Arial
sizes: title=34 body=17
style: radius=4
footer: Order platform

# All client traffic enters through one API gateway
@arch
@noemph defaults
## Clients
- [EXT] Web app: browser · SPA {.external}
- [EXT] Mobile app: iOS · Android {.external}
## Services
- [API] API gateway: auth · limits {.focal}
- [SVC] Orders: order service
- [SVC] Billing: invoices · tax
## Data
- [DB] Postgres: orders · users {.store}
- [MQ] Queue: events · async {.optional}
- [EXT] Stripe: card payments {.external}
> Web app ~> API gateway: HTTPS, Mobile app ~> API gateway: HTTPS, API gateway => Orders: place order, Orders > Billing: invoice, Orders > Postgres: write, Orders --> Queue: publish, Billing ~> Stripe: charge

# 全受注データは与信チェックを経てDWHへ入る
@arch dir=h size=12
@noemph defaults
## 入力
- [API] 受注API: 外部ECから受信 {.external}
- [ERP] 基幹ERP: 在庫・単価マスタ {.external}
## 処理
- [BATCH] 変換バッチ: 正規化・名寄せ
- [CHECK] 与信チェック: 与信枠と滞留 {.focal}
- [STOCK] 在庫引当: 倉庫別の引当
## 保存
- [DWH] DWH: 全履歴・日次集計 {.store}
- [CACHE] キャッシュ: 直近7日 {.store}
## 出力
- [UI] 管理画面: 営業・CS向け
- [CSV] 日次レポート {.optional}
> 受注API ~> 変換バッチ: 受信, 基幹ERP ~> 在庫引当: 同期, 変換バッチ > 与信チェック, 与信チェック => DWH: 保存, 在庫引当 > キャッシュ, DWH > 管理画面: 参照, DWH --> 日次レポート: 集計

# Build only what is desirable, feasible and viable
@venn
@noemph defaults
## Desirable
People want it
## Feasible
We can build it
## Viable
Business sustains
> Shippable: the sweet spot

# A strategy ships only where it meets execution
@venn
@noemph defaults
## Strategy
Where to play and why
## Execution
Who does what by when
> Ships: a plan to run

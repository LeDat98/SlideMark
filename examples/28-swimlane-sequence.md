theme: editorial
lang: en
num: on
colors: accent=#BF4520
fonts: heading=Georgia body=Arial
sizes: title=34 body=16
style: radius=4
footer: Process review

# Publishing an article
> Who does what, in the order it happens. One focal step: the deploy.
@swimlane
@defaults
## Author
- Draft MDX: src/content/...
- Open PR: gh pr create > HANDOFF
## Reviewer
- 3: Review content: fact-check · voice --> REVISE
## Editor
- 3: Polish copy: style · line edits
- 4: Approve merge: squash · main => DEPLOY TRIGGER
## CI / CD
- 4: Build: astro build
- 5: Deploy: cloudflare pages {.focal}

# 受注から出荷までの業務フロー
> 部門をまたぐ承認と在庫確認。滞留しやすいのは与信審査の差し戻し。
@swimlane size=12
## 営業部
- 見積書を作成: 単価・納期
- 4: 受注内容を連絡
## 法務・与信
- 2: 与信を審査: 上限額・支払サイト => 承認 {.focal}
## 在庫管理
- 3: 在庫を引当: 不足は発注
## 物流センター
- 5: 梱包して出荷
## 経理部
- 5: 請求書を発行
- 6: 入金を消し込む

# Article request, cold cache
> The edge answers from cache; on a miss it asks the origin, which renders once.
@sequence
@defaults
- [EXT] Reader: Browser {.input}, [EDGE] Cloudflare: Pages · cache {.external}, [ORIG] Astro Origin: SSR · MDX {.focal}, [ASY] Analytics: Beacon · async {.optional}
- Reader ~> Cloudflare: GET /slug
- Cloudflare > Astro Origin: cache miss
- Astro Origin > Astro Origin: render MDX
- Astro Origin --> Cloudflare: 200 · HTML
- Cloudflare => Reader: 200 · cached
- Reader --> Analytics: pageview beacon

# Checkout request
> The order service answers the client after the database confirms; one retry is the headline.
@sequence
@defaults
- [EXT] Client: Browser {.input}, [API] API: Order service, [IDP] Auth: JWT check {.external}, [DB] DB: Postgres {.store}
- Client > API: POST /order
- API > Auth: verify token
- Auth >> API: ok
- API > DB: insert order
- DB >> API: ok
- API > API: retry once {.focal}
- API >> Client: 201 created

# Release train
> A vertical lane per team; the one blocking handover is in the accent.
@swimlane dir=v
## Dev
- Merge to main
- 3: Fix flaky test => BLOCKS QA {.focal}
## QA
- 2: Run regression
- 4: Sign off
## Ops
- 5: Deploy canary
- 6: Promote to all

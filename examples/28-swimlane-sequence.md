theme: editorial
lang: en
num: on
colors: accent=#BF4520
fonts: heading=Georgia body=Arial
sizes: title=34 body=16
style: radius=4
footer: Process review

# Order to cash
> Who does what, in the order it happens. One focal step: the handover that stalls.
@swimlane size=15
## Customer
- Place order
- 4: Pay invoice {.focal}
## Sales
- 2: Check credit
- 3: Confirm order
## Finance
- 5: Book payment
- 6: Close the case

# 受注から出荷までの業務フロー
> 部門をまたぐ承認と在庫確認。滞留しやすいのは与信審査の差し戻し。
@swimlane size=11
## 営業部
- 見積書を作成する
  - 単価と納期
- 5: 受注内容を顧客へ連絡
## 法務・与信
- 2: 取引条件を確認
- 3: 与信審査 {.focal}
  - 上限額・支払サイト
## 在庫管理
- 4: 在庫を引当てる
  - 不足は発注
## 物流センター
- 6: 梱包して出荷
## 経理部
- 7: 請求書を発行
- 8: 入金を消し込む

# Checkout request
> The order service answers the client after the database confirms; one retry is the headline.
@sequence
@defaults
- Client > API: POST /order
- API > Auth: verify token
- Auth >> API: ok
- API > DB: insert order
- DB >> API: ok
- API > API: retry once {.focal}
- API >> Client: 201 created

# Release train
> A vertical lane per team; the one blocking handover is in the accent.
@swimlane dir=v size=13
## Dev
- Merge to main
- 3: Fix flaky test {.focal}
## QA
- 2: Run regression
- 4: Sign off
## Ops
- 5: Deploy canary
- 6: Promote to all

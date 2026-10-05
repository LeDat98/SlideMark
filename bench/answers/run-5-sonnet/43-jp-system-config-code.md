theme: jp-business
lang: ja

# バッチ処理の設定例
> 設定は4項目だけ、スケジュールとリトライが要
@2
## 設定コード
```yaml
schedule: "0 2 * * *"
retry: 3
timeout: 600
notify: ops@example.co.jp
```
## 各項目の意味
- schedule: 実行時刻（cron形式、毎日2時）
- retry: 失敗時の再試行回数
- timeout: 1回の最大実行時間（秒）
- notify: 失敗時の通知先メール
@end
> [!warn] timeout は処理時間に余裕を持たせ、通知先は運用チームの共有アドレスにしてください。

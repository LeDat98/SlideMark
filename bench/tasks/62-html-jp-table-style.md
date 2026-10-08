<!-- tags: jp html table merge dense -->
次のHTML表を、日本語のスライド1枚にしてください。結合セルと列の色分けは保って、タイトルは「料金プラン比較」に。

```html
<table>
  <tr><th rowspan="2">プラン</th><th colspan="2">料金</th><th rowspan="2">対象</th></tr>
  <tr><th>月額</th><th>年額</th></tr>
  <tr><td>ライト</td><td>1,980円</td><td>19,800円</td><td>個人</td></tr>
  <tr><td>スタンダード</td><td>4,980円</td><td>49,800円</td><td>小規模チーム</td></tr>
  <tr><td>エンタープライズ</td><td colspan="2">個別見積り</td><td>全社導入</td></tr>
</table>
```

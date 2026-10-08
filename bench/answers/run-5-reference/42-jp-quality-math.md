theme: jp-business
lang: ja

# 工程能力指数（Cp / Cpk）
> ばらつきと偏りの両方を1つの指標で判断する
@1:1
## 定義式
```math
C_p = \frac{USL - LSL}{6\sigma}
```
```math
C_{pk} = \min\left(\frac{USL - \mu}{3\sigma}, \frac{\mu - LSL}{3\sigma}\right)
```
## 判断基準
- 1.33以上: [良好]{.badge .success}
- 1.00〜1.33: [要注意]{.badge}
- 1.00未満: [不十分]{.badge .danger}

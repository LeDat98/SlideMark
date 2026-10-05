theme: jp-business
lang: ja

# 工程能力指数（Cp・Cpk）
> Cpk が 1.33 以上なら工程は安定している
@2
```math
C_p = \frac{USL - LSL}{6\sigma}
```
```math
C_{pk} = \min\left(\frac{USL - \mu}{3\sigma}, \frac{\mu - LSL}{3\sigma}\right)
```
## 判断基準
- 1.33以上: [良好]{.badge .success}
- 1.00〜1.33: [要注意]{.badge .warning}
- 1.00未満: [不十分]{.badge .danger}

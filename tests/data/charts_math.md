# Columns and bars
@ 2x2
```column {title="Revenue" labels=on fmt="#,##0" colors=primary,accent}
,Q1,Q2,Q3
2025,10,12,15
2026,12,16,21
```
```bar {title="東京 大阪 名古屋" labels=on}
,売上
東京,30
大阪,22
名古屋,14
```
```stacked-column {title="Stacked" legend=right}
,A,B,C
x,3,4,5
y,5,2,6
```
```stacked-bar {title="Stacked bar" axis=off labels=on}
,A,B
x,3,4
y,5,2
```

# Line area radar
@ 3
```line {title="Line" percent=1 labels=on min=0 max=100}
,Jan,Feb,Mar,Apr
a,10,40,,70
b,20,30,50,60
```
```area {title="Area"}
,Jan,Feb,Mar
a,10,40,30
b,20,30,50
```
```radar {title="Radar"}
,Speed,Cost,Quality,Risk,Fit
us,5,3,4,2,4
them,3,4,3,4,2
```

# Pie doughnut scatter
@ 3
```pie {title="Pie" labels=percent}
,Share
APAC,48
EU,30
US,22
```
```doughnut {title="Doughnut" labels=on}
,Share
APAC,48
EU,30
US,22
```
```scatter {title="Scatter"}
,1,2,3,4
y,2,4,5,9
z,1,3,6,7
```

# Math
```math
E = mc^2 \\ \sum_{i=1}^{n} i^2 = \frac{n(n+1)(2n+1)}{6} \\ x = \frac{-b \pm \sqrt{b^2 - 4ac}}{2a} \\ \int_0^\infty e^{-x^2} dx = \frac{\sqrt{\pi}}{2}
```

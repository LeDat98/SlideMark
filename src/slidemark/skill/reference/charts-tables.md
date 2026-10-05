# Charts and tables

**Charts** are fences named by kind: `bar column stacked-bar stacked-column line area pie doughnut scatter
radar`. Body = CSV: first row = categories (first cell ignored), each next row = one series.

````markdown
```column {title="売上（億円）" labels=on fmt="0.0" legend=bottom}
,2024,2025,2026
SaaS,30,34,38
保守,12,11,10
```
````

| Option | Values |
|---|---|
| `title` | text |
| `legend` | `bottom` `right` `top` `left` `none` |
| `labels` | `on`, `percent` (pie/doughnut), `off` |
| `fmt` | Excel number format: `0.0`, `#,##0`, `0%` |
| `min` `max` | value axis bounds |
| `colors` | `primary,accent,#888888` (per series; per slice for pie) |
| `axis` | `off` hides the value axis |

CSV cells: `"1,240"`, `1,240`, `12%`, full-width digits, `▲3` (= -3) are numbers; an empty cell is a gap.
Scatter: first row = x values.

**Tables** are GFM tables. Merge: a lone `<` joins the cell on the left, a lone `^` the cell above.

```markdown
{widths=3:1:1 align=lrr .zebra}
| 項目 | 4月 | 5月 |
|-|-|-|
| 売上 | 10 | 12 |
| 合計 | 22 | < |
```

Options: `widths` (ratios), `align` (`l` `c` `r` per column), `header=N` (header rows, 0 = none), `hcol=N`
(header columns), `.zebra`. Numeric columns are right-aligned automatically. A ` ```table ` fence takes CSV
(first row = header) with the same options.

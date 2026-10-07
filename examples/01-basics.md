title: SlideMark basics
lang: en
num: on
colors: primary=#1D4ED8 accent=#F97316
sizes: title=34 body=20

# SlideMark
Markdown in, native PowerPoint out

# Text and lists
> Headings are the structure, boxes arrange themselves
- **Bold**, *italic*, `code`, ==key number== in accent color
- Nested lists
  - second level
  - [a link](https://example.com)
1. Numbered
2. Lists
※ Source: SlideMark docs

# Three boxes
@3 flow
## Parse
- Markdown to IR
## Layout
- Absolute EMU boxes
## Render
- Native objects
> The renderer never decides positions

# Table and chart
{hl=APAC}
| Region | Revenue | Growth |
|-|-|-|
| APAC | 8.2M | +48% |
| EU | 6.1M | +12% |
```column {title="Revenue" hl=Q3}
,Q1,Q2,Q3
2025,10,12,15
2026,12,16,21
```

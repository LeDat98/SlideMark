title: SlideMark basics
lang: en
num: on

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
## Parse
- Markdown to IR
## Layout
- Absolute EMU boxes
## Render
- Native objects
> The renderer never decides positions

# Table and chart
| Region | Revenue | Growth |
|-|-|-|
| APAC | 8.2M | +48% |
| EU | 6.1M | +12% |
```column {title="Revenue"}
,Q1,Q2,Q3
2025,10,12,15
2026,12,16,21
```

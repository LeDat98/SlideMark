theme: editorial
lang: en
sizes: title=36 body=16
style: title.bold=off
footer: HTML diagrams: what syntax cannot say
num: on

# Why checkout conversion dropped {eyebrow="Fishbone · Root cause"}
@noemph defaults
```html
<div class="stack">
<div style="position:relative;width:1180px;height:380px">
<svg width="1180" height="380">
<path class="bone main" d="M20 205H996"/>
<path class="bone" d="M200 44L305 205"/>
<path class="bone" d="M480 44L585 205"/>
<path class="bone accent" d="M760 44L865 205"/>
<path class="bone" d="M300 346L405 205"/>
<path class="bone" d="M580 346L685 205"/>
<path class="bone" d="M820 346L925 205"/>
<path class="tick" d="M209 95h24"/>
<path class="tick" d="M232 130h24"/>
<path class="tick" d="M493 100h24"/>
<path class="tick" d="M773 100h24"/>
<path class="tick" d="M319 280h24"/>
<path class="tick" d="M596 285h24"/>
<path class="tick" d="M617 252h24"/>
<path class="tick" d="M839 280h24"/>
<rect class="node" x="125" y="12" width="150" height="32" rx="4"/>
<text class="cat" x="200" y="33">People</text>
<rect class="node" x="405" y="12" width="150" height="32" rx="4"/>
<text class="cat" x="480" y="33">Process</text>
<rect class="node focal" x="685" y="12" width="150" height="32" rx="4"/>
<text class="cat hot" x="760" y="33">Product</text>
<rect class="node" x="225" y="346" width="150" height="32" rx="4"/>
<text class="cat" x="300" y="367">Pricing</text>
<rect class="node" x="505" y="346" width="150" height="32" rx="4"/>
<text class="cat" x="580" y="367">Platform</text>
<rect class="node" x="745" y="346" width="150" height="32" rx="4"/>
<text class="cat" x="820" y="367">Partners</text>
<text class="sub" x="203" y="100" text-anchor="end">Support gaps</text>
<text class="sub" x="226" y="135" text-anchor="end">No chat at night</text>
<text class="sub" x="487" y="105" text-anchor="end">3-step form</text>
<text class="sub" x="767" y="105" text-anchor="end">Slow page</text>
<text class="sub" x="313" y="285" text-anchor="end">Hidden fees</text>
<text class="sub" x="590" y="290" text-anchor="end">Card errors</text>
<text class="sub" x="611" y="257" text-anchor="end">No saved cart</text>
<text class="sub" x="833" y="285" text-anchor="end">PayPal outage</text>
</svg>
<div class="node focal" style="position:absolute;left:996px;top:165px;width:184px"><span class="tag">Effect</span><b style="font-size:17px">Conversion -18%</b></div>
</div>
<div class="legend"><i class="eyebrow">Legend</i><span><i class="key"></i>Category</span><span><i class="key accent"></i>Main cause</span><span><i class="key soft"></i>Sub-cause</span><span><i class="node focal"></i>Effect</span></div>
</div>
```

# Q4 delivery board {eyebrow="Kanban · Delivery"}
@noemph defaults
```html
<div class="stack"><div class="board">
<div class="col"><header>Backlog <span class="badge">3</span></header><div class="card"><b>Saved carts</b><div class="meta">CHK-12 · priya</div></div><div class="card"><b>Gift cards</b><div class="meta">CHK-15 · leo</div></div><div class="card wait"><b>Loyalty points</b><div class="meta">CHK-18 · maya</div></div></div>
<div class="col"><header>In progress <span class="badge over">3/2</span></header><div class="card blocked"><b>One-page checkout</b><div class="meta">CHK-07 · sam · blocks Q4</div></div><div class="card"><b>Apple Pay</b><div class="meta">CHK-09 · priya</div></div><div class="card"><b>Retry on card error</b><div class="meta">CHK-10 · leo</div></div></div>
<div class="col"><header>Review <span class="badge">1/2</span></header><div class="card"><b>Address autofill</b><div class="meta">CHK-04 · nadia</div></div></div>
<div class="col"><header>Done <span class="badge">2</span></header><div class="card done"><b>Fraud check v2</b><div class="meta">CHK-01 · leo</div></div><div class="card done"><b>Receipt emails</b><div class="meta">CHK-02 · maya</div></div></div>
</div>
<div class="legend"><i class="eyebrow">Legend</i><span><i class="card"></i>Planned</span><span><i class="card blocked"></i>Blocked</span><span><i class="card wait"></i>Waiting</span><span><i class="card done"></i>Done</span><span><i class="badge over"></i>Over WIP limit</span></div></div>
```

# A first-time buyer's journey {eyebrow="Journey map · Checkout"}
@noemph defaults
```html
<div class="stack">
<div class="board" style="flex:none"><b class="eyebrow rule">Discover</b><b class="eyebrow rule">Compare</b><b class="eyebrow rule">Checkout</b><b class="eyebrow rule">Delivery</b></div>
<svg width="1180" height="310" style="display:block;flex:none">
  <path class="tick dash" d="M0 155H1180"/><text class="sub" x="0" y="145">neutral</text>
  <polyline class="bone" fill="none" points="148,85 443,110 738,255 1033,65"/>
  <circle class="dot" cx="148" cy="85" r="8"/><circle class="dot" cx="443" cy="110" r="8"/>
  <circle class="dot hot" cx="738" cy="255" r="11"/><circle class="dot" cx="1033" cy="65" r="8"/>
</svg>
<div class="board" style="flex:none;font-size:16px"><div class="cap">Ad on social; lands on the product page</div><div class="cap">Opens 3 tabs, reads reviews</div><div class="cap" style="color:var(--accent);font-weight:700">Surprise shipping fee at step 3</div><div class="cap">Tracking link, arrives a day early</div></div>
<div class="legend"><i class="eyebrow">Legend</i><span><i class="pt hot"></i>Pain point</span><span><i class="pt"></i>Stage rating</span><span><i class="key dash"></i>Neutral line</span></div>
</div>
```

# Where the support hours go {eyebrow="Treemap · Support"}
@noemph defaults
```html
<div style="position:relative;height:100%">
  <div class="node" style="position:absolute;left:0;top:0;width:calc(55% - 4px);height:100%"><b>Payments 46%</b><div class="sub">card errors, refunds</div></div>
  <div class="node" style="position:absolute;left:55%;top:0;width:45%;height:calc(58% - 4px)"><b>Delivery 27%</b><div class="sub">tracking, late parcels</div></div>
  <div class="node" style="position:absolute;left:55%;top:58%;width:calc(24% - 4px);height:42%"><b>Accounts 15%</b><div class="sub">logins, resets</div></div>
  <div class="node focal" style="position:absolute;left:79%;top:58%;width:21%;height:42%"><b>Fees 12%</b><div class="sub">up 3x</div></div>
</div>
```

# 品質不良の要因分析 {eyebrow="特性要因図 · 品質管理"}
@noemph defaults
```html
<div class="stack" lang="ja">
<div style="position:relative;width:1180px;height:380px">
<svg width="1180" height="380">
<path class="bone main" d="M20 205H996"/>
<path class="bone" d="M200 44L305 205"/>
<path class="bone" d="M480 44L585 205"/>
<path class="bone accent" d="M760 44L865 205"/>
<path class="bone" d="M300 346L405 205"/>
<path class="bone" d="M580 346L685 205"/>
<path class="bone" d="M820 346L925 205"/>
<path class="tick" d="M209 95h24"/>
<path class="tick" d="M232 130h24"/>
<path class="tick" d="M493 100h24"/>
<path class="tick" d="M769 95h24"/>
<path class="tick" d="M792 130h24"/>
<path class="tick" d="M319 280h24"/>
<path class="tick" d="M599 280h24"/>
<path class="tick" d="M839 280h24"/>
<rect class="node" x="125" y="12" width="150" height="32" rx="4"/>
<text class="cat" x="200" y="33">人（作業者）</text>
<rect class="node" x="405" y="12" width="150" height="32" rx="4"/>
<text class="cat" x="480" y="33">方法（手順）</text>
<rect class="node focal" x="685" y="12" width="150" height="32" rx="4"/>
<text class="cat hot" x="760" y="33">機械（設備）</text>
<rect class="node" x="225" y="346" width="150" height="32" rx="4"/>
<text class="cat" x="300" y="367">材料（部品）</text>
<rect class="node" x="505" y="346" width="150" height="32" rx="4"/>
<text class="cat" x="580" y="367">測定（検査）</text>
<rect class="node" x="745" y="346" width="150" height="32" rx="4"/>
<text class="cat" x="820" y="367">環境（工場）</text>
<text class="sub" x="203" y="100" text-anchor="end">夜勤の習熟不足</text>
<text class="sub" x="226" y="135" text-anchor="end">交代時の引継ぎ漏れ</text>
<text class="sub" x="487" y="105" text-anchor="end">手順書が旧版のまま</text>
<text class="sub" x="763" y="100" text-anchor="end">成形機3号の温度ばらつき</text>
<text class="sub" x="786" y="135" text-anchor="end">保全周期が長い</text>
<text class="sub" x="313" y="285" text-anchor="end">仕入先変更（4月）</text>
<text class="sub" x="593" y="285" text-anchor="end">抜取検査が週1回</text>
<text class="sub" x="833" y="285" text-anchor="end">梅雨期の湿度上昇</text>
</svg>
<div class="node focal" style="position:absolute;left:996px;top:165px;width:184px"><span class="tag">結果</span><b style="font-size:17px">不良率 0.8% → 2.1%</b></div>
</div>
<div class="legend"><i class="eyebrow">凡例</i><span><i class="key"></i>大骨（要因分類）</span><span><i class="key accent"></i>主要因</span><span><i class="key soft"></i>小骨（原因）</span><span><i class="node focal"></i>結果</span></div>
</div>
```
※ 2026年4〜9月、第2工場の全ロットを集計。

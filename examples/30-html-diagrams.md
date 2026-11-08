theme: editorial
lang: en
sizes: title=36 body=16
footer: HTML diagrams: what syntax cannot say
num: on

# Why checkout conversion dropped
@noemph defaults
```html
<svg width="100%" height="100%" viewBox="0 0 1180 490" font-family="Arial">
  <defs><marker id="a" markerWidth="10" markerHeight="10" refX="9" refY="5" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="var(--primary)"/></marker></defs>
  <line x1="20" y1="245" x2="930" y2="245" stroke="var(--primary)" stroke-width="2" marker-end="url(#a)"/>
  <line x1="180" y1="70" x2="290" y2="245" stroke="var(--secondary)" stroke-width="1.2"/>
  <line x1="450" y1="70" x2="560" y2="245" stroke="var(--secondary)" stroke-width="1.2"/>
  <line x1="720" y1="70" x2="830" y2="245" stroke="var(--secondary)" stroke-width="1.2"/>
  <line x1="180" y1="420" x2="290" y2="245" stroke="var(--secondary)" stroke-width="1.2"/>
  <line x1="450" y1="420" x2="560" y2="245" stroke="var(--secondary)" stroke-width="1.2"/>
  <line x1="720" y1="420" x2="830" y2="245" stroke="var(--secondary)" stroke-width="1.2"/>
  <text x="180" y="52" font-size="20" font-weight="700" fill="var(--primary)" text-anchor="middle">People</text>
  <text x="450" y="52" font-size="20" font-weight="700" fill="var(--primary)" text-anchor="middle">Process</text>
  <text x="720" y="52" font-size="20" font-weight="700" fill="var(--primary)" text-anchor="middle">Product</text>
  <text x="180" y="452" font-size="20" font-weight="700" fill="var(--primary)" text-anchor="middle">Pricing</text>
  <text x="450" y="452" font-size="20" font-weight="700" fill="var(--primary)" text-anchor="middle">Platform</text>
  <text x="720" y="452" font-size="20" font-weight="700" fill="var(--primary)" text-anchor="middle">Partners</text>
  <text x="250" y="150" font-size="18" fill="var(--muted)">Support gaps</text>
  <text x="520" y="150" font-size="18" fill="var(--muted)">3-step form</text>
  <text x="790" y="150" font-size="18" font-weight="700" fill="var(--accent)">Slow page</text>
  <text x="250" y="350" font-size="18" fill="var(--muted)">Hidden fees</text>
  <text x="520" y="350" font-size="18" fill="var(--muted)">Card errors</text>
  <text x="790" y="350" font-size="18" fill="var(--muted)">PayPal outage</text>
  <rect x="945" y="205" width="225" height="80" rx="6" fill="#FFFFFF" stroke="var(--accent)" stroke-width="1.5"/>
  <text x="1057" y="238" font-size="20" font-weight="700" fill="var(--primary)" text-anchor="middle">Conversion</text>
  <text x="1057" y="266" font-size="20" font-weight="700" fill="var(--accent)" text-anchor="middle">-18%</text>
</svg>
```

# Q4 delivery board
@noemph defaults
```html
<div style="display:flex;gap:20px;height:100%;font-family:Arial;font-size:20px;color:var(--primary)">
  <div style="flex:1;border-top:2px solid var(--primary);padding-top:10px">
    <div style="font:700 15px Consolas;letter-spacing:2px;color:var(--muted)">BACKLOG · 3</div>
    <div style="margin-top:12px;background:#fff;border:1px solid var(--border);border-radius:6px;padding:12px">Saved carts</div>
    <div style="margin-top:10px;background:#fff;border:1px solid var(--border);border-radius:6px;padding:12px">Gift cards</div>
    <div style="margin-top:10px;border:1px dashed var(--muted);border-radius:6px;padding:12px">Loyalty (optional)</div>
  </div>
  <div style="flex:1;border-top:2px solid var(--primary);padding-top:10px">
    <div style="font:700 15px Consolas;letter-spacing:2px;color:var(--muted)">IN PROGRESS · 2</div>
    <div style="margin-top:12px;background:#BF452014;border:1.5px solid var(--accent);border-radius:6px;padding:12px"><b>One-page checkout</b><br><span style="font-size:16px;color:var(--muted)">blocks the Q4 target</span></div>
    <div style="margin-top:10px;background:#fff;border:1px solid var(--border);border-radius:6px;padding:12px">Apple Pay</div>
  </div>
  <div style="flex:1;border-top:2px solid var(--primary);padding-top:10px">
    <div style="font:700 15px Consolas;letter-spacing:2px;color:var(--muted)">REVIEW · 1</div>
    <div style="margin-top:12px;background:#fff;border:1px solid var(--border);border-radius:6px;padding:12px">Address autofill</div>
  </div>
  <div style="flex:1;border-top:2px solid var(--primary);padding-top:10px">
    <div style="font:700 15px Consolas;letter-spacing:2px;color:var(--muted)">DONE · 2</div>
    <div style="margin-top:12px;background:#E9E9EA;border-radius:6px;padding:12px;color:var(--muted)">Fraud check v2</div>
    <div style="margin-top:10px;background:#E9E9EA;border-radius:6px;padding:12px;color:var(--muted)">Receipt emails</div>
  </div>
</div>
```

# A first-time buyer's journey
@noemph defaults
```html
<div style="height:100%;font-family:Arial;color:var(--primary)">
  <div style="display:flex;gap:16px">
    <div style="flex:1;font:700 15px Consolas;letter-spacing:2px;border-bottom:1px solid var(--border);padding-bottom:8px">DISCOVER</div>
    <div style="flex:1;font:700 15px Consolas;letter-spacing:2px;border-bottom:1px solid var(--border);padding-bottom:8px">COMPARE</div>
    <div style="flex:1;font:700 15px Consolas;letter-spacing:2px;border-bottom:1px solid var(--border);padding-bottom:8px">CHECKOUT</div>
    <div style="flex:1;font:700 15px Consolas;letter-spacing:2px;border-bottom:1px solid var(--border);padding-bottom:8px">DELIVERY</div>
  </div>
  <svg width="1180" height="230" viewBox="0 0 1180 230" style="margin-top:12px">
    <line x1="0" y1="115" x2="1180" y2="115" stroke="var(--border)" stroke-dasharray="4 3"/>
    <text x="0" y="105" font-size="14" fill="var(--muted)">neutral</text>
    <polyline points="145,60 440,80 735,195 1030,45" fill="none" stroke="var(--primary)" stroke-width="2"/>
    <circle cx="145" cy="60" r="8" fill="var(--primary)"/><circle cx="440" cy="80" r="8" fill="var(--primary)"/>
    <circle cx="735" cy="195" r="11" fill="var(--accent)"/><circle cx="1030" cy="45" r="8" fill="var(--primary)"/>
  </svg>
  <div style="display:flex;gap:16px;margin-top:10px;font-size:19px">
    <div style="flex:1">Ad on social; lands on the product page</div>
    <div style="flex:1">Opens 3 tabs, reads reviews</div>
    <div style="flex:1;color:var(--accent);font-weight:700">Surprise shipping fee at step 3</div>
    <div style="flex:1">Tracking link, arrives a day early</div>
  </div>
</div>
```

# Where the support hours go
@noemph defaults
```html
<div style="position:relative;height:100%;font-family:Arial;font-size:18px;color:#fff">
  <div style="position:absolute;left:0;top:0;width:55%;height:100%;background:var(--primary);padding:18px;box-sizing:border-box"><b style="font-size:28px">Payments 46%</b><br>card errors, refunds</div>
  <div style="position:absolute;left:55.5%;top:0;width:44.5%;height:58%;background:var(--secondary);padding:16px;box-sizing:border-box"><b style="font-size:24px">Delivery 27%</b><br>tracking, late parcels</div>
  <div style="position:absolute;left:55.5%;top:59%;width:24%;height:41%;background:#5E7A9B;padding:14px;box-sizing:border-box"><b style="font-size:20px">Accounts 15%</b></div>
  <div style="position:absolute;left:80%;top:59%;width:20%;height:41%;background:var(--accent);padding:14px;box-sizing:border-box"><b style="font-size:20px">Fees 12%</b><br>up 3x</div>
</div>
```

# 品質不良の要因分析
@noemph defaults
```html
<svg width="100%" height="100%" viewBox="0 0 1180 490" font-family="Yu Gothic">
  <defs><marker id="b" markerWidth="10" markerHeight="10" refX="9" refY="5" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="var(--primary)"/></marker></defs>
  <line x1="20" y1="245" x2="930" y2="245" stroke="var(--primary)" stroke-width="2" marker-end="url(#b)"/>
  <line x1="180" y1="70" x2="290" y2="245" stroke="var(--secondary)" stroke-width="1.2"/>
  <line x1="450" y1="70" x2="560" y2="245" stroke="var(--secondary)" stroke-width="1.2"/>
  <line x1="720" y1="70" x2="830" y2="245" stroke="var(--secondary)" stroke-width="1.2"/>
  <line x1="180" y1="420" x2="290" y2="245" stroke="var(--secondary)" stroke-width="1.2"/>
  <line x1="450" y1="420" x2="560" y2="245" stroke="var(--secondary)" stroke-width="1.2"/>
  <line x1="720" y1="420" x2="830" y2="245" stroke="var(--secondary)" stroke-width="1.2"/>
  <text x="180" y="52" font-size="18" font-weight="700" fill="var(--primary)" text-anchor="middle">人（作業者）</text>
  <text x="450" y="52" font-size="18" font-weight="700" fill="var(--primary)" text-anchor="middle">方法（手順）</text>
  <text x="720" y="52" font-size="18" font-weight="700" fill="var(--primary)" text-anchor="middle">機械（設備）</text>
  <text x="180" y="452" font-size="18" font-weight="700" fill="var(--primary)" text-anchor="middle">材料（部品）</text>
  <text x="450" y="452" font-size="18" font-weight="700" fill="var(--primary)" text-anchor="middle">測定（検査）</text>
  <text x="720" y="452" font-size="18" font-weight="700" fill="var(--primary)" text-anchor="middle">環境（工場）</text>
  <text x="245" y="140" font-size="15" fill="var(--muted)">夜勤の習熟不足</text>
  <text x="245" y="162" font-size="15" fill="var(--muted)">交代時の引継ぎ漏れ</text>
  <text x="515" y="150" font-size="15" fill="var(--muted)">手順書が旧版のまま</text>
  <text x="785" y="140" font-size="15" font-weight="700" fill="var(--accent)">成形機3号の温度ばらつき</text>
  <text x="785" y="162" font-size="15" fill="var(--muted)">保全周期が長い</text>
  <text x="245" y="350" font-size="15" fill="var(--muted)">仕入先変更（4月）</text>
  <text x="515" y="350" font-size="15" fill="var(--muted)">抜取検査が週1回</text>
  <text x="785" y="350" font-size="15" fill="var(--muted)">梅雨期の湿度上昇</text>
  <rect x="945" y="200" width="225" height="90" rx="6" fill="#FFFFFF" stroke="var(--accent)" stroke-width="1.5"/>
  <text x="1057" y="236" font-size="18" font-weight="700" fill="var(--primary)" text-anchor="middle">不良率</text>
  <text x="1057" y="268" font-size="18" font-weight="700" fill="var(--accent)" text-anchor="middle">0.8% → 2.1%</text>
</svg>
```
※ 2026年4〜9月、第2工場の全ロットを集計。

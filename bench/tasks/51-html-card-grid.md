<!-- tags: en html -->
Turn this HTML/CSS card grid into one editable slide.

```html
<style>
.grid{display:grid;grid-template-columns:repeat(3,1fr);gap:16px}
.card{border:1px solid #cbd5e1;border-radius:8px;padding:16px}
.card h3{color:#0f766e}
</style>
<h1>Why teams choose Nimbus</h1>
<div class="grid">
  <div class="card"><h3>Fast</h3><p>Deploys in under 60 seconds.</p></div>
  <div class="card"><h3>Safe</h3><p>SOC 2 Type II, SSO, audit logs.</p></div>
  <div class="card"><h3>Cheap</h3><p>Flat pricing from $19 per seat.</p></div>
</div>
```

<!-- tags: en html hard dense -->
Build a one-slide dense "monthly newsletter" from this HTML: a header row, three columns of articles each with a heading, two sentences and a "Read more" link, and a footer line with the unsubscribe note.

```html
<header><h1>Acme Monthly - October</h1></header>
<div style="display:grid;grid-template-columns:repeat(3,1fr);gap:20px">
<article><h2>Product</h2><p>Dark mode is live. Export to PDF is coming next month.</p><a href="https://acme.example/product">Read more</a></article>
<article><h2>Community</h2><p>1,500 members joined our forum. The summit is on Nov 12.</p><a href="https://acme.example/community">Read more</a></article>
<article><h2>Company</h2><p>We opened an office in Berlin. We are hiring 12 roles.</p><a href="https://acme.example/jobs">Read more</a></article>
</div>
<footer style="font-size:11px">You receive this because you subscribed. Unsubscribe anytime.</footer>
```

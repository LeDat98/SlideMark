<!-- tags: en html code callout -->
Turn this docs snippet into a slide: heading, the code block, and the blockquote as a warning callout.

```html
<h1>Retry policy</h1>
<pre><code class="language-python">for attempt in range(3):
    try:
        return client.call()
    except Timeout:
        sleep(2 ** attempt)</code></pre>
<blockquote>Never retry non-idempotent calls without a key.</blockquote>
```

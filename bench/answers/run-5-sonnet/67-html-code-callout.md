# Retry policy
```python
for attempt in range(3):
    try:
        return client.call()
    except Timeout:
        sleep(2 ** attempt)
```
> [!warn] Never retry non-idempotent calls without a key.

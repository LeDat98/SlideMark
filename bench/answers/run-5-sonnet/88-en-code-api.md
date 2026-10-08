# Create an invoice
> One POST call creates an invoice
```python
import requests

resp = requests.post(
    "https://api.example.com/v1/invoices",
    headers={"Authorization": "Bearer YOUR_TOKEN"},
    json={"customer_id": "c_123", "amount": 4900, "currency": "usd"},
)
resp.raise_for_status()
```
## Error handling
- 4xx: fix the request, do not retry
- 429: back off and retry
- 5xx: retry with exponential delay
> [!warn] Rate limit: 100 requests per minute.

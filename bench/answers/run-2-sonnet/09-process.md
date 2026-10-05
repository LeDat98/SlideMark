# Approval process
> Rejected requests return to the submitter
```mermaid
graph LR
A[Submit] --> B[Manager review]
B --> C{Approved?}
C -->|yes| D[Finance]
C -->|no| A
```

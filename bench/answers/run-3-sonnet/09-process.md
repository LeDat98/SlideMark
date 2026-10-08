# Approval Process
> Rejected requests return to the submitter
```mermaid
graph LR
A[Submit] --> B[Manager review]
B --> C{Decision}
C -->|approved| D[Finance]
C -->|rejected| A
```

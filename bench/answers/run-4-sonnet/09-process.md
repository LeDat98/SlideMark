# Approval Process
> Every request is reviewed by a manager before Finance
```mermaid
graph LR
A[Submit] --> B[Manager review]
B --> C{Approved?}
C -->|yes| D[Finance]
C -->|no| A
```

theme: jp-business
lang: ja

# 補助金申請の業務フロー
```mermaid
graph TD
A[申請] --> B{要件チェック}
B -->|満たす| C[審査]
B -->|満たさない| D[修正して再提出]
D --> A
C --> E{採択?}
E -->|採択| F[交付決定]
E -->|不採択| G[再申請を検討]
```

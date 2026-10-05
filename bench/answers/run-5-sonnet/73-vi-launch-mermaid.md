lang: vi

# Quy trình duyệt ra mắt sản phẩm
```mermaid
graph LR
A[Đề xuất] --> B[Kiểm tra pháp lý]
B --> C{Đạt?}
C -->|Đạt| D[Duyệt ngân sách]
C -->|Không| E[Chỉnh sửa]
E --> A
D --> F[Ra mắt]
```

theme: none
lang: vi
colors: bg=#FFFFFF fg=#1B2A2F primary=#12343B secondary=#2F7E79 accent=#F2A33A surface=#EAF3F2 border=#C9DCDA muted=#5C7378
fonts: heading="Cambria" body="Calibri"
sizes: title=36! heading=22 body=16 lead=20 conclusion=18
style: radius=10 title.band=none card.fill=surface
num: on

# AI: từ nền tảng đến ứng dụng {size=54 align=left}
@cover bg=primary dark noemph defaults
## Tổng quan cho người mới bắt đầu

# Nội dung chính
@agenda noemph defaults
1. Nền tảng: AI là gì, lịch sử, cách máy học
2. Công nghệ: Transformer, LLM, đa phương thức
3. Hệ thống: Agent và RAG
4. Thực tế: Ứng dụng, rủi ro, cách triển khai
5. Lộ trình: Các bước áp dụng trong tổ chức

# AI, học máy và học sâu: ba lớp lồng nhau
@funnel noemph defaults
## Trí tuệ nhân tạo (lớp ngoài)
Máy làm những việc cần "trí thông minh": suy luận, hiểu ngôn ngữ, nhận diện.
## Học máy (lớp giữa)
Học quy luật từ dữ liệu thay vì viết luật thủ công, càng nhiều dữ liệu càng tốt.
## Học sâu (lớp trong)
Mạng nơ-ron nhiều tầng, nền tảng của AI tạo sinh ngày nay.

# Bảy thập kỷ, năm bước ngoặt
@timeline dir=h marks=num defaults
## 1956
Hội thảo Dartmouth đặt tên "trí tuệ nhân tạo"
## 1997
Deep Blue thắng nhà vô địch cờ vua thế giới
## 2012
AlexNet thắng ImageNet, mở ra kỷ nguyên học sâu
## 2017
Bài báo Transformer giới thiệu cơ chế attention
## 2022 {.accent}
ChatGPT đưa AI tạo sinh đến đại chúng
> Mỗi bước ngoặt mở rộng thứ máy có thể làm được, và đưa AI đến nhiều người hơn.

# Máy học theo ba cách chính
@iconlist cols=1 noemph defaults
- icon=check **Có giám sát** Học từ dữ liệu đã có nhãn đúng. Ví dụ: phân loại thư rác
- icon=chart **Không giám sát** Tự tìm cấu trúc trong dữ liệu không nhãn. Ví dụ: gom nhóm khách hàng
- icon=gear **Tăng cường** Thử, sai và nhận phần thưởng để cải thiện. Ví dụ: điều khiển robot

# Transformer đổi cách máy đọc ngôn ngữ
@vs defaults
## Trước 2017: RNN/LSTM
- Đọc tuần tự từng từ
- Khó giữ ngữ cảnh dài
- Huấn luyện chậm
## Từ 2017: Transformer {.hero}
- Nhìn toàn câu cùng lúc (attention)
- Nắm ngữ cảnh dài tốt hơn
- Song song hóa, mở rộng quy mô
## Attention là nền tảng của các mô hình ngôn ngữ lớn

# LLM sinh văn bản từng token
@rows plain noemph defaults
1. **Bước 1 Token hóa** Cắt văn bản thành các token (mảnh từ).
2. **Bước 2 Embedding** Biến mỗi token thành vector số.
3. **Bước 3 Attention** Liên kết các token liên quan với nhau.
4. **Bước 4 Dự đoán** Chọn token kế tiếp theo xác suất.
> Lặp lại cho đến khi câu trả lời hoàn chỉnh: token mới được nối vào đầu vào của vòng sau.

# Đa phương thức: một mô hình, nhiều dữ liệu
@2x2 noemph defaults
## Văn bản {icon=info}
Viết, tóm tắt, dịch và hỗ trợ lập trình.
## Hình ảnh {icon=target}
Nhận diện, mô tả và tạo ảnh từ mô tả.
## Âm thanh {icon=globe}
Nhận dạng giọng nói, đọc văn bản thành tiếng.
## Video {icon=rocket}
Hiểu nội dung cảnh quay, tạo đoạn phim ngắn.

# Agent: AI biết lập kế hoạch và hành động
> Vòng lặp agent
@cycle dir=cw noemph defaults
## 1. Quan sát
Nhận mục tiêu và ngữ cảnh.
## 2. Lập kế hoạch
Chia nhỏ thành các bước.
## 3. Hành động
Gọi công cụ, API, tìm kiếm.
## 4. Đánh giá
Kiểm tra kết quả, điều chỉnh.

# RAG: trả lời dựa trên dữ liệu của bạn
@free noemph defaults
{x=4% y=24% w=20% h=34% size=18 valign=top fill=surface pad=10pt}
**Câu hỏi**
Người dùng hỏi bằng ngôn ngữ tự nhiên.
{x=27.5% y=24% w=20% h=34% size=18 valign=top fill=secondary color=#FFFFFF pad=10pt}
**Tìm kiếm**
Lấy các đoạn liên quan từ kho tài liệu.
{x=51% y=24% w=20% h=34% size=18 valign=top fill=surface pad=10pt}
**Ghép ngữ cảnh**
Đưa đoạn tìm được vào prompt, giữ nguồn.
{x=74.5% y=24% w=20% h=34% size=18 valign=top fill=surface pad=10pt}
**Trả lời**
Mô hình trả lời kèm nguồn để kiểm chứng.
{x=24.4% y=36% w=2.4% h=8% shape=chevron fill=accent}
{x=47.9% y=36% w=2.4% h=8% shape=chevron fill=accent}
{x=71.4% y=36% w=2.4% h=8% shape=chevron fill=accent}
{x=27.5% y=64% w=20% h=14% size=20 fill=accent color=primary align=center valign=middle shape=can}
**Kho tài liệu nội bộ**
> Tra cứu trước, trả lời sau: giảm bịa đặt vì câu trả lời có nguồn kiểm chứng.

# AI đã có mặt ở nhiều ngành
```table {widths=1:3:2 align=lll .zebra hlcol="Giá trị mang lại"}
Ngành,Ứng dụng tiêu biểu,Giá trị mang lại
Y tế,Đọc ảnh chẩn đoán hỗ trợ bác sĩ,Phát hiện sớm hơn
Tài chính,"Phát hiện gian lận, chấm điểm rủi ro",Giảm tổn thất
Bán lẻ,"Dự báo nhu cầu, gợi ý sản phẩm",Tối ưu tồn kho
Sản xuất,Kiểm tra lỗi bằng thị giác máy,Nâng chất lượng
Giáo dục,Trợ giảng cá nhân hóa,Học theo tốc độ riêng
```
> AI hiệu quả nhất khi gắn với một quy trình và một chỉ số đo được.

# Cơ hội luôn đi cùng rủi ro
@proscons noemph defaults
## Lợi ích
- Tăng năng suất ở việc lặp lại
- Hỗ trợ ra quyết định bằng dữ liệu
- Mở ra sản phẩm và dịch vụ mới
## Rủi ro
- Có thể bịa thông tin (hallucination)
- Thiên kiến và rủi ro bảo mật dữ liệu
- Phụ thuộc vào nhà cung cấp
> Dùng AI có kiểm soát: luôn có người xác nhận ở khâu quan trọng.

# Bốn cách đưa AI vào sản phẩm
> Bắt đầu từ cách đơn giản nhất mà vẫn đáp ứng được nhu cầu.
@4 noemph defaults
## Prompt / API {icon=clock}
Độ phức tạp: thấp. Thử nghiệm nhanh, tác vụ chung.
## RAG {icon=info}
Độ phức tạp: trung bình. Trả lời theo tài liệu nội bộ.
## Tinh chỉnh {icon=gear}
Độ phức tạp: cao. Phong cách hoặc tác vụ chuyên biệt.
## Huấn luyện từ đầu {icon=shield}
Độ phức tạp: rất cao. Chỉ khi có dữ liệu và ngân sách lớn.

# Lộ trình áp dụng theo bốn giai đoạn
@chevron noemph defaults
sizes: body=20
## 1 Thí điểm
- Chọn 1 bài toán nhỏ, rõ giá trị
- Đo kết quả trước và sau
## 2 Mở rộng
- Nhân rộng sang các nhóm liên quan
- Tích hợp vào quy trình hiện có
## 3 Chuẩn hóa
- Quy tắc về dữ liệu và bảo mật
- Tiêu chí đánh giá chất lượng
## 4 Tối ưu
- Theo dõi hiệu quả liên tục
- Cải tiến mô hình và quy trình

# Giá trị của AI đến từ cách dùng {align=left}
@cover bg=primary dark noemph defaults
## Chọn một bài toán, thử trong 4 tuần, rồi quyết định.

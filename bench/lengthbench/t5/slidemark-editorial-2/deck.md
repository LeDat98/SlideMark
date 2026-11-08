lang: vi
sizes: title=38 heading=20 body=15 lead=20
style: icon.disc=secondary cover.art=network
footer: AI: từ nền tảng đến ứng dụng
num: on

# AI: từ nền tảng đến ứng dụng {align=left}
@cover bg=primary dark
## Tổng quan cho người mới bắt đầu

# Nội dung chính
@agenda
1. **Nền tảng:** AI là gì, lịch sử, cách máy học
2. **Công nghệ:** Transformer, LLM, đa phương thức
3. **Hệ thống:** Agent và RAG
4. **Thực tế:** Ứng dụng, rủi ro, cách triển khai
5. **Lộ trình:** Các bước áp dụng trong tổ chức

# AI, học máy và học sâu: ba lớp lồng nhau
@nested side=right
## Trí tuệ nhân tạo (lớp ngoài) {icon=brain}
Máy làm những việc cần "trí thông minh": suy luận, hiểu ngôn ngữ, nhận diện.
## Học máy (lớp giữa) {icon=layers}
Học quy luật từ dữ liệu thay vì viết luật thủ công, càng nhiều dữ liệu càng tốt.
## Học sâu (lớp trong) {icon=database}
Mạng nơ-ron nhiều tầng, nền tảng của AI tạo sinh ngày nay.

# Bảy thập kỷ, năm bước ngoặt
@timeline dir=h marks=on
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
@3
## Có giám sát {icon=check}
Học từ dữ liệu đã có nhãn đúng. Ví dụ: phân loại thư rác
## Không giám sát {icon=search}
Tự tìm cấu trúc trong dữ liệu không nhãn. Ví dụ: gom nhóm khách hàng
## Tăng cường {icon=refresh}
Thử, sai và nhận phần thưởng để cải thiện. Ví dụ: điều khiển robot

# Transformer đổi cách máy đọc ngôn ngữ
@vs
## Trước 2017: RNN/LSTM
- Đọc tuần tự từng từ
- Khó giữ ngữ cảnh dài
- Huấn luyện chậm
## Từ 2017: Transformer {.hero}
- Nhìn toàn câu cùng lúc (attention)
- Nắm ngữ cảnh dài tốt hơn
- Song song hóa, mở rộng quy mô
> Attention là nền tảng của các mô hình ngôn ngữ lớn

# LLM sinh văn bản từng token
@steps
## Bước 1 Token hóa {icon=code}
Cắt văn bản thành các token (mảnh từ).
## Bước 2 Embedding {icon=layers}
Biến mỗi token thành vector số.
## Bước 3 Attention {icon=eye}
Liên kết các token liên quan với nhau.
## Bước 4 Dự đoán {icon=target}
Chọn token kế tiếp theo xác suất.
> Lặp lại cho đến khi câu trả lời hoàn chỉnh: token mới được nối vào đầu vào của vòng sau.

# Đa phương thức: một mô hình, nhiều dữ liệu
@2x2
## Văn bản {icon=list}
Viết, tóm tắt, dịch và hỗ trợ lập trình.
## Hình ảnh {icon=eye}
Nhận diện, mô tả và tạo ảnh từ mô tả.
## Âm thanh {icon=microphone}
Nhận dạng giọng nói, đọc văn bản thành tiếng.
## Video {icon=video}
Hiểu nội dung cảnh quay, tạo đoạn phim ngắn.

# Agent: AI biết lập kế hoạch và hành động
@cycle dir=cw center="Vòng lặp agent"
## 1. Quan sát {icon=eye}
Nhận mục tiêu và ngữ cảnh.
## 2. Lập kế hoạch {icon=list}
Chia nhỏ thành các bước.
## 3. Hành động {icon=gear}
Gọi công cụ, API, tìm kiếm.
## 4. Đánh giá {icon=check}
Kiểm tra kết quả, điều chỉnh.

# RAG: trả lời dựa trên dữ liệu của bạn
@flow disc
## Kho tài liệu nội bộ {.above icon=database}
## Câu hỏi {icon=user}
Người dùng hỏi bằng ngôn ngữ tự nhiên.
## Tìm kiếm {icon=search}
Lấy các đoạn liên quan từ kho tài liệu.
## Ghép ngữ cảnh {icon=layers}
Đưa đoạn tìm được vào prompt, giữ nguồn.
## Trả lời {icon=check}
Mô hình trả lời kèm nguồn để kiểm chứng.
> Tra cứu trước, trả lời sau: giảm bịa đặt vì câu trả lời có nguồn kiểm chứng.

# AI đã có mặt ở nhiều ngành
```table {widths=1:3:2 .zebra}
Ngành,Ứng dụng tiêu biểu,Giá trị mang lại
Y tế,Đọc ảnh chẩn đoán hỗ trợ bác sĩ,Phát hiện sớm hơn
Tài chính,"Phát hiện gian lận, chấm điểm rủi ro",Giảm tổn thất
Bán lẻ,"Dự báo nhu cầu, gợi ý sản phẩm",Tối ưu tồn kho
Sản xuất,Kiểm tra lỗi bằng thị giác máy,Nâng chất lượng
Giáo dục,Trợ giảng cá nhân hóa,Học theo tốc độ riêng
```
> AI hiệu quả nhất khi gắn với một quy trình và một chỉ số đo được.

# Cơ hội luôn đi cùng rủi ro
@proscons
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
@stairs dir=up
## Prompt / API
Độ phức tạp: thấp. Thử nghiệm nhanh, tác vụ chung.
## RAG
Độ phức tạp: trung bình. Trả lời theo tài liệu nội bộ.
## Tinh chỉnh
Độ phức tạp: cao. Phong cách hoặc tác vụ chuyên biệt.
## Huấn luyện từ đầu
Độ phức tạp: rất cao. Chỉ khi có dữ liệu và ngân sách lớn.

# Lộ trình áp dụng theo bốn giai đoạn
@chevron
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
@cover bg=primary dark
## Chọn một bài toán, thử trong 4 tuần, rồi quyết định.

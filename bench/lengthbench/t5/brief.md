# Brief lengthbench-t5 (open, Vietnamese)

Make a 15-slide 16:9 PowerPoint deck in Vietnamese: an introduction to AI for beginners. Use the text below word
for word. Every slide gives only its title and its facts; the form of each slide (how the facts are shown) is your
decision. Look: your choice, decided before the first slide; the deck is for a general business audience.

## Slide 1
- Title: AI: từ nền tảng đến ứng dụng
- Tổng quan cho người mới bắt đầu

## Slide 2
- Title: Nội dung chính
- Nền tảng: AI là gì, lịch sử, cách máy học
- Công nghệ: Transformer, LLM, đa phương thức
- Hệ thống: Agent và RAG
- Thực tế: Ứng dụng, rủi ro, cách triển khai
- Lộ trình: Các bước áp dụng trong tổ chức

## Slide 3
- Title: AI, học máy và học sâu: ba lớp lồng nhau
- Trí tuệ nhân tạo (lớp ngoài): Máy làm những việc cần "trí thông minh": suy luận, hiểu ngôn ngữ, nhận diện.
- Học máy (lớp giữa): Học quy luật từ dữ liệu thay vì viết luật thủ công, càng nhiều dữ liệu càng tốt.
- Học sâu (lớp trong): Mạng nơ-ron nhiều tầng, nền tảng của AI tạo sinh ngày nay.

## Slide 4
- Title: Bảy thập kỷ, năm bước ngoặt
- 1956: Hội thảo Dartmouth đặt tên "trí tuệ nhân tạo"
- 1997: Deep Blue thắng nhà vô địch cờ vua thế giới
- 2012: AlexNet thắng ImageNet, mở ra kỷ nguyên học sâu
- 2017: Bài báo Transformer giới thiệu cơ chế attention
- 2022: ChatGPT đưa AI tạo sinh đến đại chúng
- Takeaway: Mỗi bước ngoặt mở rộng thứ máy có thể làm được, và đưa AI đến nhiều người hơn.

## Slide 5
- Title: Máy học theo ba cách chính
- Có giám sát: Học từ dữ liệu đã có nhãn đúng. Ví dụ: phân loại thư rác
- Không giám sát: Tự tìm cấu trúc trong dữ liệu không nhãn. Ví dụ: gom nhóm khách hàng
- Tăng cường: Thử, sai và nhận phần thưởng để cải thiện. Ví dụ: điều khiển robot

## Slide 6
- Title: Transformer đổi cách máy đọc ngôn ngữ
- Trước 2017: RNN/LSTM: Đọc tuần tự từng từ; Khó giữ ngữ cảnh dài; Huấn luyện chậm
- Từ 2017: Transformer: Nhìn toàn câu cùng lúc (attention); Nắm ngữ cảnh dài tốt hơn; Song song hóa, mở rộng quy mô
- Takeaway: Attention là nền tảng của các mô hình ngôn ngữ lớn

## Slide 7
- Title: LLM sinh văn bản từng token
- Bước 1 Token hóa: Cắt văn bản thành các token (mảnh từ).
- Bước 2 Embedding: Biến mỗi token thành vector số.
- Bước 3 Attention: Liên kết các token liên quan với nhau.
- Bước 4 Dự đoán: Chọn token kế tiếp theo xác suất.
- Takeaway: Lặp lại cho đến khi câu trả lời hoàn chỉnh: token mới được nối vào đầu vào của vòng sau.

## Slide 8
- Title: Đa phương thức: một mô hình, nhiều dữ liệu
- Văn bản: Viết, tóm tắt, dịch và hỗ trợ lập trình.
- Hình ảnh: Nhận diện, mô tả và tạo ảnh từ mô tả.
- Âm thanh: Nhận dạng giọng nói, đọc văn bản thành tiếng.
- Video: Hiểu nội dung cảnh quay, tạo đoạn phim ngắn.

## Slide 9
- Title: Agent: AI biết lập kế hoạch và hành động
- A loop ("Vòng lặp agent") of four steps:
- 1. Quan sát: Nhận mục tiêu và ngữ cảnh.
- 2. Lập kế hoạch: Chia nhỏ thành các bước.
- 3. Hành động: Gọi công cụ, API, tìm kiếm.
- 4. Đánh giá: Kiểm tra kết quả, điều chỉnh.

## Slide 10
- Title: RAG: trả lời dựa trên dữ liệu của bạn
- A flow of four steps, with a store ("Kho tài liệu nội bộ") feeding the second step:
- Câu hỏi: Người dùng hỏi bằng ngôn ngữ tự nhiên.
- Tìm kiếm: Lấy các đoạn liên quan từ kho tài liệu.
- Ghép ngữ cảnh: Đưa đoạn tìm được vào prompt, giữ nguồn.
- Trả lời: Mô hình trả lời kèm nguồn để kiểm chứng.
- Takeaway: Tra cứu trước, trả lời sau: giảm bịa đặt vì câu trả lời có nguồn kiểm chứng.

## Slide 11
- Title: AI đã có mặt ở nhiều ngành
- Table (header row first):

  | Ngành | Ứng dụng tiêu biểu | Giá trị mang lại |
  | Y tế | Đọc ảnh chẩn đoán hỗ trợ bác sĩ | Phát hiện sớm hơn |
  | Tài chính | Phát hiện gian lận, chấm điểm rủi ro | Giảm tổn thất |
  | Bán lẻ | Dự báo nhu cầu, gợi ý sản phẩm | Tối ưu tồn kho |
  | Sản xuất | Kiểm tra lỗi bằng thị giác máy | Nâng chất lượng |
  | Giáo dục | Trợ giảng cá nhân hóa | Học theo tốc độ riêng |

- Takeaway: AI hiệu quả nhất khi gắn với một quy trình và một chỉ số đo được.

## Slide 12
- Title: Cơ hội luôn đi cùng rủi ro
- Lợi ích: Tăng năng suất ở việc lặp lại; Hỗ trợ ra quyết định bằng dữ liệu; Mở ra sản phẩm và dịch vụ mới
- Rủi ro: Có thể bịa thông tin (hallucination); Thiên kiến và rủi ro bảo mật dữ liệu; Phụ thuộc vào nhà cung cấp
- Takeaway: Dùng AI có kiểm soát: luôn có người xác nhận ở khâu quan trọng.

## Slide 13
- Title: Bốn cách đưa AI vào sản phẩm
- Lead: Bắt đầu từ cách đơn giản nhất mà vẫn đáp ứng được nhu cầu.
- Prompt / API: Độ phức tạp: thấp. Thử nghiệm nhanh, tác vụ chung.
- RAG: Độ phức tạp: trung bình. Trả lời theo tài liệu nội bộ.
- Tinh chỉnh: Độ phức tạp: cao. Phong cách hoặc tác vụ chuyên biệt.
- Huấn luyện từ đầu: Độ phức tạp: rất cao. Chỉ khi có dữ liệu và ngân sách lớn.

## Slide 14
- Title: Lộ trình áp dụng theo bốn giai đoạn
- 1 Thí điểm: Chọn 1 bài toán nhỏ, rõ giá trị; Đo kết quả trước và sau
- 2 Mở rộng: Nhân rộng sang các nhóm liên quan; Tích hợp vào quy trình hiện có
- 3 Chuẩn hóa: Quy tắc về dữ liệu và bảo mật; Tiêu chí đánh giá chất lượng
- 4 Tối ưu: Theo dõi hiệu quả liên tục; Cải tiến mô hình và quy trình

## Slide 15
- Title: Giá trị của AI đến từ cách dùng
- Chọn một bài toán, thử trong 4 tuần, rồi quyết định.

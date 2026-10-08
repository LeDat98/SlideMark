theme: none
lang: vi
colors: bg=#FFFFFF fg=#14272F primary=#0B2A3C secondary=#1B8A8F accent=#F2A33A surface=#EEF4F6 border=#CFDDE2 muted=#5A6F78
fonts: heading=Arial body=Arial
sizes: title=36 heading=20 body=16 lead=20 caption=12
style: cover.art=network steps.caption="Bước {n}" radius=8 title.band=none heading.band=none card.elevation=2 icon.disc=secondary conclusion.icon=refresh cycle.fill=primary,secondary flow.disc.fill=primary,secondary stairs.fill=#BFE3E5,#7FC4C8,#1B8A8F,#0B2A3C
footer: AI: từ nền tảng đến ứng dụng
num: on

# AI: từ nền tảng đến ứng dụng
@cover bg=primary dark
## Giới thiệu cho người mới bắt đầu · 2026

# Nội dung hôm nay
@agenda noemph defaults
1. Nền tảng: AI, học máy và học sâu
2. Cách máy học và mô hình ngôn ngữ lớn
3. Agent và RAG: từ mô hình đến ứng dụng
4. Ngành nghề, lợi ích và rủi ro
5. Bốn cách bắt đầu và lộ trình 12 tuần

# AI, học máy và học sâu
@nested side=left
## Trí tuệ nhân tạo {icon=globe}
Máy làm những việc vốn cần trí thông minh của con người
## Học máy {icon=chart}
Máy tự rút quy luật từ dữ liệu thay vì được lập trình từng bước
## Học sâu {icon=cpu}
Mạng nơ-ron nhiều tầng, nền tảng của ==AI hiện đại==

# Bảy thập kỷ của AI
> Mỗi làn sóng mới đến khi dữ liệu và sức tính toán đủ lớn
@timeline dir=h marks=on
## 1956
Hội nghị Dartmouth đặt tên cho ngành
## 1997
Deep Blue thắng nhà vô địch cờ vua
## 2012
AlexNet mở ra kỷ nguyên học sâu
## 2017
Transformer ra đời
## 2022 {.accent}
ChatGPT đưa AI đến hàng trăm triệu người

# Ba cách máy học
@3 defaults
## Có giám sát {icon=check}
- Học từ ví dụ đã gắn nhãn
- Cần nhiều dữ liệu được dán nhãn
- Ví dụ: lọc thư rác, nhận diện ảnh
## Không giám sát {icon=search}
- Tự tìm cấu trúc trong dữ liệu
- Không cần nhãn, khó kiểm chứng hơn
- Ví dụ: phân nhóm khách hàng
## Tăng cường {.hero icon=trophy}
- Thử, sai rồi nhận phần thưởng
- Học dần một chiến lược tốt
- Ví dụ: AlphaGo, robot tự đi lại

# Từ RNN đến Transformer
@vs defaults
## RNN
- Đọc từng từ một, theo thứ tự
- Dễ quên phần đầu của câu dài
- Khó huấn luyện song song
## Transformer {.hero}
- Nhìn cả câu cùng lúc nhờ attention
- Nắm được quan hệ giữa các từ ở xa
- Huấn luyện song song trên GPU
## Kết luận
Transformer là nền tảng của mọi mô hình ngôn ngữ lớn hiện nay

# Mô hình ngôn ngữ viết từng token
@4 steps defaults
## Token hóa {icon=code}
- Cắt văn bản thành các token
- Một từ có thể thành vài token
## Embedding {icon=database}
- Mỗi token thành một vector số
- Vector gần nhau, nghĩa gần nhau
## Attention {icon=search}
- Cân nhắc token nào liên quan
- Hiểu ngữ cảnh của cả câu
## Dự đoán {icon=bolt}
- Chọn token kế tiếp theo xác suất
- Lặp lại cho đến khi hoàn tất
@end
> ==Một token mỗi lần==, lặp lại cho đến khi câu trả lời hoàn tất

# AI không chỉ đọc chữ
> Một mô hình đa phương thức nhận và tạo nhiều loại dữ liệu
@iconlist cols=2
- icon=document **Văn bản** viết, tóm tắt, dịch và lập trình
- icon=camera **Hình ảnh** nhận diện, mô tả, ==tạo ảnh từ lời nhắc==
- icon=headphones **Âm thanh** chép lời, tổng hợp giọng nói
- icon=play **Video** hiểu cảnh quay, tạo đoạn phim ngắn
- icon=code **Mã nguồn** gợi ý, giải thích và sửa lỗi
- icon=chart **Bảng số liệu** đọc, so sánh và vẽ biểu đồ

# Agent: AI biết tự làm việc
@cycle center="Vòng lặp agent"
## Quan sát {icon=search}
Đọc yêu cầu, ngữ cảnh và công cụ có sẵn
## Lập kế hoạch {icon=target}
Chia mục tiêu thành những bước nhỏ
## Hành động {icon=bolt}
Gọi công cụ, chạy mã, tìm thông tin
## Phản hồi {icon=check}
Kiểm tra kết quả, ==lặp lại== nếu chưa đạt

# RAG: trả lời bằng tài liệu của bạn
@flow disc defaults
## Kho tài liệu {.above icon=database}
PDF, wiki, email
## Câu hỏi {icon=chat}
Người dùng hỏi bằng ngôn ngữ tự nhiên
## Truy xuất {icon=search}
Tìm các đoạn liên quan nhất
## Ghép ngữ cảnh {icon=document}
Đưa đoạn tìm được vào lời nhắc
## Trả lời {icon=bolt}
Mô hình trả lời và ==dẫn nguồn==

# AI đang thay đổi các ngành
@defaults
{hl="Y tế"}
| Ngành | Ứng dụng tiêu biểu | Tác động |
|-|-|-|
| Y tế | Đọc ảnh chụp, hỗ trợ chẩn đoán | Giảm thời gian chờ |
| Tài chính | Phát hiện gian lận, chấm điểm tín dụng | Giảm tổn thất |
| Bán lẻ | Dự báo nhu cầu, gợi ý sản phẩm | Tăng doanh thu |
| Giáo dục | Gia sư cá nhân hóa | Học nhanh hơn |
| Sản xuất | Bảo trì dự đoán, kiểm tra chất lượng | Giảm thời gian dừng máy |

# Lợi ích và rủi ro
@proscons noemph defaults
## Lợi ích
+ Tiết kiệm thời gian cho việc lặp lại
+ Hỗ trợ quyết định bằng dữ liệu
+ Cá nhân hóa trải nghiệm ở quy mô lớn
## Rủi ro
− Thông tin sai nhưng nghe rất thuyết phục
− Thiên kiến trong dữ liệu huấn luyện
− Lộ dữ liệu nhạy cảm
> Dùng AI cùng người kiểm tra: nhanh hơn nhưng ==không bỏ trách nhiệm==

# Bốn cách đưa AI vào sản phẩm
> Càng lên cao, ==càng sâu== và càng tốn công
@stairs dir=up
## Dùng sẵn
Mua dịch vụ AI có sẵn và dùng ngay trong tuần đầu
## Lời nhắc
Viết lời nhắc và mẫu để mô hình làm đúng việc
## Truy xuất
Nối mô hình với tài liệu riêng của bạn (RAG)
## Huấn luyện
Tinh chỉnh hoặc tự huấn luyện mô hình riêng

# Lộ trình 12 tuần
@4 steps defaults
## Tuần 1–2 {icon=search}
- Chọn ba việc lặp lại để thử
- Ghi lại thời gian hiện tại
## Tuần 3–5 {icon=bolt}
- Thử với dịch vụ có sẵn
- Đo chất lượng và thời gian
## Tuần 6–9 {icon=gear}
- Nối AI vào công cụ đang dùng
- Đặt người duyệt kết quả
## Tuần 10–12 {icon=rocket}
- Nhân rộng sang nhóm khác
- Đào tạo và theo dõi chi phí
@end
> Bắt đầu nhỏ, đo kết quả, rồi ==mới mở rộng==

# Cảm ơn bạn đã theo dõi
@cover bg=primary dark
## Câu hỏi và trao đổi

# Kịch bản thuyết minh video demo

Video `demo.mp4` dài khoảng **1 phút 50 giây**, có phụ đề nhưng **không có tiếng**. Cách làm đơn giản nhất:
mở video, vừa xem vừa **thu giọng đọc** bằng điện thoại/micro (đọc theo từng đoạn bên dưới), rồi ghép tiếng vào bằng CapCut / DaVinci Resolve / Clipchamp,
hoặc bằng một dòng ffmpeg:

```bash
ffmpeg -i demo.mp4 -i giong_doc.m4a -c:v copy -c:a aac -shortest demo_co_tieng.mp4
```

Mỗi đoạn dưới đây đã viết vừa với thời lượng cảnh (khoảng 3–4 âm tiết/giây). Có thể đọc chậm hơn và kéo dài cảnh nếu cần.

| Thời điểm | Cảnh | Lời thuyết minh |
|---|---|---|
| 0:00 – 0:05 | Tiêu đề | "Xin chào thầy cô và các bạn. Em là Nguyễn Đình Thực. Đây là bài demo dự án phân tích dữ liệu bán hàng với NumPy, Pandas và Matplotlib." |
| 0:05 – 0:17 | Tổng quan | "Dự án là một pipeline hoàn chỉnh: đọc dữ liệu thô, làm sạch, phân tích, vẽ biểu đồ và xuất báo cáo. Mã nguồn chia thành các module nhỏ, có kiểm thử tự động." |
| 0:17 – 0:25 | Terminal | "Chỉ cần một lệnh python run.py, chương trình tự sinh bốn nghìn đơn hàng mô phỏng, làm sạch, tính các chỉ số và vẽ mười ba biểu đồ." |
| 0:25 – 0:37 | Làm sạch | "Dữ liệu thô cố ý có lỗi: ô thiếu, dòng trùng, đơn giá nhập thừa số không. Em dùng quy tắc IQR để phát hiện ngoại lai. Số lỗi tìm được khớp chính xác số lỗi đã chèn." |
| 0:37 – 0:49 | Doanh thu theo thời gian | "Doanh thu đạt đỉnh vào tháng mười một, đúng mùa mua sắm cuối năm. Doanh thu cuối tuần nhỉnh hơn ngày thường, nhưng kiểm định Welch cho p bằng 0,076 nên chưa đủ bằng chứng kết luận." |
| 0:49 – 1:00 | Sản phẩm, khu vực | "Điện thoại và Laptop chiếm hơn sáu mươi hai phần trăm doanh thu. TP Hồ Chí Minh và Hà Nội chiếm khoảng bảy mươi bốn phần trăm." |
| 1:00 – 1:11 | Pareto | "Cần tới bốn mươi chín phần trăm số khách để đạt tám mươi phần trăm doanh thu, nghĩa là doanh thu khá phân tán, không theo quy luật tám mươi hai mươi." |
| 1:11 – 1:22 | RFM | "Phân tích RFM chia khách thành bốn nhóm. Nhóm VIP chỉ chiếm mười sáu phần trăm số khách nhưng tạo ba mươi hai phần trăm doanh thu." |
| 1:22 – 1:34 | Dự báo | "Em dự báo ba tháng tới bằng xu hướng nhân mùa vụ và so với mô hình cùng kỳ năm trước. Vì chỉ có một năm dữ liệu nên đây chỉ là minh họa kỹ thuật." |
| 1:34 – 1:39 | Kiểm thử | "Hai mươi mốt bài kiểm thử tự động đều đạt, gồm cả đối chiếu kết quả kiểm định với SciPy." |
| 1:39 – 1:48 | Kết luận | "Tóm lại, dự án có pipeline hoàn chỉnh, làm sạch minh bạch và kết luận trung thực kể cả khi chưa đủ bằng chứng. Mã nguồn và báo cáo PDF ở phần mô tả. Em cảm ơn đã xem." |

## Mẹo nếu muốn tự quay màn hình (video dài hơn, 3–5 phút)
1. Mở terminal, chạy `python run.py` và chỉ vào từng khối kết quả (làm sạch, KPI, Pareto, dự báo).
2. Mở thư mục `outputs/figures/` và lần lượt trình bày 4–5 biểu đồ quan trọng.
3. Mở `outputs/bao_cao_tong_hop.xlsx` cho thấy các sheet.
4. Chạy `python -m unittest discover -s tests -v` để thấy toàn bộ test đạt.
5. Mở nhanh `src/salesanalysis/cleaning.py` và giải thích hàm `clean()` (6 bước).

---

# Mẫu thông tin đăng YouTube

**Tiêu đề:** Phân tích dữ liệu bán hàng với NumPy, Pandas, Matplotlib – Demo dự án Python (Chủ đề 5.5)

**Mô tả:**
```
Demo dự án phân tích dữ liệu bán hàng bằng Python: làm sạch dữ liệu, phân tích, trực quan hóa 13 biểu đồ, phân khúc RFM, kiểm định thống kê và dự báo.
Dữ liệu là mô phỏng, dùng cho mục đích học tập.

Mã nguồn: <dán link GitHub>
Báo cáo PDF: <dán link, ví dụ file trong thư mục docs/ của repo>

Mốc thời gian:
0:00 Giới thiệu
0:17 Chạy pipeline bằng một lệnh
0:25 Làm sạch dữ liệu
0:37 Doanh thu theo thời gian
0:49 Sản phẩm, khu vực, kênh
1:00 Pareto
1:11 Phân khúc RFM
1:22 Dự báo
1:34 Kiểm thử
1:39 Kết luận

#python #pandas #numpy #matplotlib #dataanalysis
```

**Cài đặt đề xuất:** Chế độ hiển thị **Không công khai (Unlisted)** nếu chỉ nộp cho giảng viên; **Không phải nội dung dành cho trẻ em**.

# Phân tích dữ liệu bán hàng với NumPy, Pandas và Matplotlib

Dự án môn Python – **Chủ đề 5.5: Phân tích dữ liệu cơ bản với NumPy, Pandas và Matplotlib**.

Pipeline hoàn chỉnh: **sinh dữ liệu → làm sạch → phân tích → trực quan hóa → xuất báo cáo**, chạy bằng một dòng lệnh.

![Dashboard](outputs/figures/00_dashboard.png)

## Tính năng

| Giai đoạn | Nội dung | Thư viện chính |
|---|---|---|
| Sinh dữ liệu | 4.000 đơn hàng mô phỏng có mùa vụ, xu hướng, dữ liệu bẩn (seed cố định → tái lập được) | NumPy |
| Làm sạch | Kiểm tra chất lượng, xóa trùng, chuẩn hóa chuỗi, ngoại lai theo IQR, điền thiếu theo median từng sản phẩm | Pandas |
| Phân tích | KPI, theo tháng/thứ/sản phẩm/khu vực/kênh, Pareto, phân khúc khách hàng RFM, tương quan, dự báo | Pandas + NumPy |
| Trực quan hóa | 13 biểu đồ (đường, cột, histogram log, heatmap, boxplot, Pareto, dự báo) | Matplotlib |
| Xuất kết quả | `clean_sales.csv`, `bao_cao_tong_hop.xlsx` (7 sheet), `summary.json` | Pandas, openpyxl |

## Sản phẩm

- Mã nguồn: _(link GitHub của bạn)_
- Video demo: _(link YouTube của bạn)_
- Báo cáo PDF: [`docs/BaoCao_PhanTichDuLieu.pdf`](docs/BaoCao_PhanTichDuLieu.pdf)

## Cài đặt và chạy

Yêu cầu Python 3.10+.

```bash
git clone <link-repo-cua-ban>
cd phan-tich-doanh-so
python -m venv .venv && source .venv/bin/activate    # Windows: .venv\Scripts\activate
pip install -r requirements.txt

python run.py                 # sinh dữ liệu (nếu chưa có) và chạy toàn bộ pipeline
python run.py generate --orders 10000 --seed 7        # tạo bộ dữ liệu khác
python run.py run --input duong_dan/file_cua_ban.csv  # phân tích dữ liệu của bạn
```

Kết quả nằm trong thư mục `outputs/`.

### Dùng dữ liệu của bạn
File CSV cần có các cột: `order_id, order_date, customer_id, product, category, region, channel, quantity, unit_price, discount` (`discount` là số từ 0 đến 1).

### Kiểm thử
```bash
python -m unittest discover -s tests -v     # 21 test, không cần cài thêm gì
```

## Cấu trúc

```
phan-tich-doanh-so/
├── src/salesanalysis/
│   ├── generate.py     # sinh dữ liệu mô phỏng (NumPy)
│   ├── cleaning.py     # làm sạch + báo cáo làm sạch
│   ├── analysis.py     # KPI, nhóm, Pareto, RFM, tương quan, dự báo
│   ├── visualize.py    # 13 biểu đồ Matplotlib
│   └── cli.py          # giao diện dòng lệnh
├── tests/              # 19 unit test
├── data/raw_sales.csv  # dữ liệu thô mô phỏng
├── outputs/            # dữ liệu sạch, Excel, JSON, hình
├── docs/               # báo cáo PDF (20 trang), kịch bản video, hướng dẫn đăng GitHub/YouTube
├── scripts/            # build_report.py (dựng PDF), make_video.py (dựng video demo)
└── run.py
```

## Kết quả chính (dữ liệu mô phỏng năm 2025)

- Tổng doanh thu **22,13 tỷ đồng**, 4.000 đơn, 1.158 khách; giá trị đơn trung bình 5,53 triệu nhưng trung vị chỉ 2,64 triệu.
- **Điện thoại và Laptop** chiếm 62,8% doanh thu.
- Doanh thu đỉnh **tháng 11** (3,26 tỷ); ngày khuyến mãi lớn (11/11, 24–28/11) đạt doanh thu/ngày gấp ~1,8 lần các ngày khác trong tháng. Cuối tuần nhỉnh hơn ngày thường nhưng chênh lệch **chưa có ý nghĩa thống kê** (Welch t-test, p ≈ 0,08).
- Cần **49% khách hàng (563 người)** để tạo 80% doanh thu → doanh thu phân tán, không theo quy luật 80/20.
- Mô hình dự báo (xu hướng × mùa vụ) chỉ mang tính minh họa vì chỉ có 1 năm dữ liệu.

## Lưu ý trung thực

Dữ liệu là **mô phỏng**, không phải số liệu của doanh nghiệp thật. Các "phát hiện" phản ánh cách dữ liệu được sinh ra (ví dụ mùa vụ, giảm giá 11/11) và dùng để minh họa kỹ thuật phân tích.

## Giấy phép
MIT – xem [LICENSE](LICENSE).

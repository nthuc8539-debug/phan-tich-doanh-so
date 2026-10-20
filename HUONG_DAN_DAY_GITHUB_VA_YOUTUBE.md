# Hướng dẫn đưa dự án lên GitHub và YouTube, rồi điền link vào báo cáo

Thư mục dự án đã có sẵn kho Git cục bộ với một commit đầu tiên. Bạn chỉ cần làm các bước dưới đây trên máy của mình.

## 1. Đưa mã nguồn lên GitHub

**Cách A – dùng giao diện web (dễ nhất)**
1. Đăng nhập https://github.com → bấm **New repository**.
2. Đặt tên, ví dụ `phan-tich-doanh-so`. Chọn **Public**. **Không** tích "Add a README" (dự án đã có sẵn).
3. Bấm **Create repository**, GitHub sẽ hiện hai dòng lệnh "push an existing repository". Mở terminal trong thư mục dự án và chạy:

```bash
git remote add origin https://github.com/<ten-ban>/phan-tich-doanh-so.git
git branch -M main
git push -u origin main
```

**Cách B – dùng GitHub CLI**
```bash
gh auth login
gh repo create phan-tich-doanh-so --public --source=. --remote=origin --push
```

Sau khi push, kiểm tra trên GitHub: có ảnh dashboard trong README, thư mục `src/`, `tests/`, `docs/`.
Link cần nộp có dạng: `https://github.com/<ten-ban>/phan-tich-doanh-so`.

## 2. Đăng video lên YouTube
1. Vào https://studio.youtube.com → **Tạo** → **Tải video lên**.
2. Chọn `docs/demo.mp4` (hoặc bản đã ghép tiếng). Dán tiêu đề, mô tả, mốc thời gian từ `docs/KichBan_Video.md`.
3. Chọn hiển thị **Công khai** hoặc **Không công khai** (ai có link đều xem được) → **Lưu**.
4. Sao chép link video dạng `https://youtu.be/xxxxxxxxxxx`.

## 3. Điền link vào báo cáo và README
- `README.md`: thay `<link-repo-cua-ban>` và thêm link video.
- Báo cáo PDF: trên **trang bìa** và **mục 9.4** có các chỗ cam ghi `[dán link GitHub]`, `[dán link YouTube]`, cùng `[điền MSSV]`, `[điền lớp, khoa]`, `[điền tên học phần]`, `[điền tên giảng viên]`.
  Sửa các chỗ này trong `scripts/build_report.py` (tìm chuỗi `[dán link`) rồi dựng lại:

```bash
pip install playwright && playwright install chromium   # chỉ cần để xuất PDF
python scripts/build_report.py
```

  Báo cáo mới nằm ở `docs/BaoCao_PhanTichDuLieu.pdf` (vẫn 20 trang).
- Commit và push lại:
```bash
git add -A && git commit -m "Cập nhật link và thông tin báo cáo" && git push
```

## 4. Danh sách kiểm tra trước khi nộp
- [ ] Repo GitHub mở được khi chưa đăng nhập (Public).
- [ ] Video YouTube mở được bằng link (không bị "riêng tư").
- [ ] PDF có 15–20 trang, đã điền MSSV, lớp, tên giảng viên và hai link.
- [ ] Chạy thử trên máy sạch: `pip install -r requirements.txt` rồi `python run.py` không lỗi.

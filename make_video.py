"""Dựng video demo (không tiếng) từ kết quả chạy thật: terminal + biểu đồ + phụ đề.

Chạy:  python scripts/make_video.py      ->  docs/demo.mp4
Cần:   Pillow và ffmpeg. Video không có lời; bạn có thể thu thuyết minh theo docs/KichBan_Video.md
       rồi ghép bằng bất kỳ phần mềm nào (CapCut, DaVinci, ffmpeg...).
"""
from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
FIG = ROOT / "outputs" / "figures"
W, H = 1280, 720
SURFACE, INK, INK2, BLUE, ORANGE = "#fcfcfb", "#0b0b0b", "#52514e", "#2a78d6", "#eb6834"
TERM_BG, TERM_FG, TERM_DIM, TERM_GREEN = "#1a1a19", "#f0efec", "#8d8c85", "#4ec790"
F = "/usr/share/fonts/opentype/inter/Inter-{}.otf"
MONO = "/usr/share/fonts/truetype/liberation/LiberationMono-Regular.ttf"  # Liberation Mono hiển thị đúng dấu tiếng Việt


def font(w="Regular", s=28):
    return ImageFont.truetype(F.format(w), s)


def wrap(draw, text, fnt, max_w):
    words, lines, cur = text.split(), [], ""
    for w in words:
        t = (cur + " " + w).strip()
        if draw.textlength(t, font=fnt) <= max_w:
            cur = t
        else:
            lines.append(cur)
            cur = w
    return lines + [cur] if cur else lines


def caption_bar(img, text):
    d = ImageDraw.Draw(img, "RGBA")
    d.rectangle([0, H - 118, W, H], fill=(18, 48, 95, 255))
    fnt = font("Medium", 26)
    lines = wrap(d, text, fnt, W - 120)[:2]
    y = H - 118 + (118 - len(lines) * 36) // 2
    for ln in lines:
        d.text((60, y), ln, font=fnt, fill="white")
        y += 36


def header(img, title, step=None):
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, 14, H], fill=BLUE)
    d.text((56, 32), title, font=font("Bold", 38), fill=INK)
    if step:
        d.text((W - 56, 40), step, font=font("Medium", 22), fill=INK2, anchor="ra")


def slide_title():
    img = Image.new("RGB", (W, H), SURFACE)
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, 26, H], fill=BLUE)
    d.text((90, 150), "CHỦ ĐỀ 5.5", font=font("SemiBold", 28), fill=BLUE)
    d.text((90, 205), "Phân tích dữ liệu bán hàng", font=font("Bold", 62), fill=INK)
    d.text((90, 285), "với NumPy, Pandas và Matplotlib", font=font("Bold", 62), fill=INK)
    d.text((90, 390), "Pipeline: làm sạch → phân tích → trực quan hóa → dự báo", font=font("Regular", 30), fill=INK2)
    d.text((90, 560), "Nguyễn Đình Thực", font=font("SemiBold", 30), fill=INK)
    d.text((90, 602), "Demo sản phẩm", font=font("Regular", 24), fill=INK2)
    return img


def slide_pipeline():
    img = Image.new("RGB", (W, H), SURFACE)
    header(img, "Tổng quan dự án")
    d = ImageDraw.Draw(img)
    boxes = [("Dữ liệu thô", "4.020 dòng CSV"), ("Làm sạch", "Pandas"), ("Phân tích", "Pandas + NumPy"),
             ("Trực quan hóa", "Matplotlib"), ("Báo cáo", "PNG · Excel · JSON")]
    bw, gap, x0, y0 = 200, 38, 56, 190
    for i, (a, b) in enumerate(boxes):
        x = x0 + i * (bw + gap)
        out = i == len(boxes) - 1
        d.rounded_rectangle([x, y0, x + bw, y0 + 120], 14, fill=BLUE if out else "#f4f8fe", outline=BLUE, width=3)
        d.text((x + bw / 2, y0 + 45), a, font=font("SemiBold", 26), fill="white" if out else INK, anchor="mm")
        d.text((x + bw / 2, y0 + 82), b, font=font("Regular", 19), fill="#dce8fa" if out else INK2, anchor="mm")
        if i < len(boxes) - 1:
            d.text((x + bw + gap / 2, y0 + 60), "→", font=font("Bold", 30), fill=BLUE, anchor="mm")
    pts = ["Cấu trúc package chuẩn: generate · cleaning · analysis · visualize · cli",
           "Chạy bằng một lệnh, kết quả tái lập được nhờ seed cố định",
           "13 biểu đồ, báo cáo Excel 7 sheet, 21 bài kiểm thử tự động"]
    for i, t in enumerate(pts):
        d.ellipse([70, 392 + i * 62, 86, 408 + i * 62], fill=BLUE)
        d.text((106, 384 + i * 62), t, font=font("Regular", 29), fill=INK)
    return img


def terminal_frames(title, lines, hold=2.0, per_line=0.22, caption=None):
    """Trả về danh sách (ảnh, thời lượng): hiện dần từng dòng như đang chạy."""
    fnt = ImageFont.truetype(MONO, 20)
    lh = 27
    max_lines = (H - 150 - 118) // lh
    frames = []
    for n in range(1, len(lines) + 1):
        img = Image.new("RGB", (W, H), TERM_BG)
        d = ImageDraw.Draw(img)
        d.rectangle([0, 0, W, 54], fill="#2a2a28")
        for i, c in enumerate(["#ff5f57", "#febc2e", "#28c840"]):
            d.ellipse([20 + i * 26, 18, 34 + i * 26, 32], fill=c)
        d.text((W / 2, 27), title, font=font("Medium", 20), fill=TERM_DIM, anchor="mm")
        vis = lines[:n][-max_lines:]
        y = 78
        for ln in vis:
            col = TERM_GREEN if ln.startswith("$") else (TERM_DIM if ln.startswith("=====") else TERM_FG)
            if ln.strip() == "OK" or ln.startswith("Ran "):
                col = TERM_GREEN
            d.text((36, y), ln, font=fnt, fill=col)
            y += lh
        if caption:
            caption_bar(img, caption)
        frames.append((img, per_line))
    frames[-1] = (frames[-1][0], hold)
    return frames


def slide_figure(title, fname, caption, step=None, max_h=470):
    img = Image.new("RGB", (W, H), SURFACE)
    header(img, title, step)
    fig = Image.open(FIG / fname).convert("RGB")
    r = min((W - 120) / fig.width, max_h / fig.height)
    fig = fig.resize((int(fig.width * r), int(fig.height * r)), Image.LANCZOS)
    x, y = (W - fig.width) // 2, 100 + (max_h - fig.height) // 2
    ImageDraw.Draw(img).rectangle([x - 2, y - 2, x + fig.width + 1, y + fig.height + 1], outline="#e4e3df", width=2)
    img.paste(fig, (x, y))
    caption_bar(img, caption)
    return img


def slide_end():
    img = Image.new("RGB", (W, H), SURFACE)
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, 26, H], fill=BLUE)
    d.text((90, 120), "Kết luận", font=font("Bold", 56), fill=INK)
    pts = ["Pipeline hoàn chỉnh: làm sạch → phân tích → trực quan hóa → dự báo",
           "Làm sạch có báo cáo; số lỗi phát hiện khớp đúng số lỗi đã chèn",
           "Kiểm định thống kê cho kết luận trung thực, kể cả khi “chưa đủ bằng chứng”",
           "Dữ liệu là mô phỏng; dự báo chỉ minh họa vì mới có 1 năm dữ liệu"]
    for i, t in enumerate(pts):
        d.ellipse([94, 258 + i * 70, 110, 274 + i * 70], fill=BLUE)
        d.text((130, 248 + i * 70), t, font=font("Regular", 28), fill=INK)
    d.text((90, 590), "Mã nguồn và báo cáo PDF: xem phần mô tả video", font=font("SemiBold", 28), fill=BLUE)
    d.text((90, 635), "Cảm ơn đã xem!", font=font("Regular", 26), fill=INK2)
    return img


def run(cmd):
    r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, env={"PYTHONIOENCODING": "utf-8", "PATH": "/usr/bin:/usr/local/bin"})
    text = (r.stdout + r.stderr).replace(str(ROOT) + "/", "")  # không lộ đường dẫn máy
    return text.splitlines()


def main():
    out = ROOT / "docs" / "demo.mp4"
    out.parent.mkdir(exist_ok=True)

    # Chạy thật để lấy đầu ra terminal (xóa dữ liệu trước để thấy bước tự sinh)
    (ROOT / "data" / "raw_sales.csv").unlink(missing_ok=True)
    run_lines = ["$ python run.py"] + [ln for ln in run([sys.executable, "run.py"]) if ln.strip()]
    test_lines = ["$ python -m unittest discover -s tests"] + [ln for ln in run([sys.executable, "-m", "unittest", "discover", "-s", "tests"]) if "Warning" not in ln and ln.strip()]
    sum_lines = run_lines[:]

    seq = []  # (img, seconds)
    seq.append((slide_title(), 5))
    seq.append((slide_pipeline(), 12))
    seq += terminal_frames("Terminal – chạy pipeline bằng một lệnh", sum_lines, hold=6,
                           caption="Một lệnh duy nhất: tự sinh dữ liệu, làm sạch, phân tích và vẽ 13 biểu đồ")
    seq.append((slide_figure("Làm sạch dữ liệu", "02_price_outliers.png",
                             "Đơn giá nhập thừa số 0 được phát hiện bằng IQR và xử lý; 6 ngoại lai và 20 dòng trùng đều bị bắt đúng", "1/6"), 12))
    seq.append((slide_figure("Doanh thu theo thời gian", "03_monthly.png",
                             "Doanh thu đỉnh vào tháng 11 – mùa mua sắm cuối năm. Cuối tuần nhỉnh hơn nhưng chưa có ý nghĩa thống kê (p = 0,076)", "2/6"), 12))
    seq.append((slide_figure("Sản phẩm, khu vực và kênh", "06_heatmap.png",
                             "Điện thoại và Laptop chiếm 62,8% doanh thu; TP.HCM và Hà Nội chiếm 74%", "3/6"), 11))
    seq.append((slide_figure("Mức độ tập trung doanh thu", "09_pareto.png",
                             "Cần 49% khách hàng để đạt 80% doanh thu: doanh thu khá phân tán, không theo quy luật 80/20", "4/6"), 11))
    seq.append((slide_figure("Phân khúc khách hàng RFM", "10_rfm.png",
                             "Nhóm VIP chỉ 16% số khách nhưng tạo 32% doanh thu; nhóm “Nguy cơ rời bỏ” cần kích hoạt lại", "5/6", 400), 11))
    seq.append((slide_figure("Dự báo và hạn chế", "12_forecast.png",
                             "Dự báo chỉ mang tính minh họa vì mới có một năm dữ liệu; đã đối chiếu với mô hình cùng kỳ năm trước", "6/6"), 12))
    seq += terminal_frames("Terminal – kiểm thử tự động", test_lines, hold=4, per_line=0.25,
                           caption="21 bài kiểm thử tự động đều đạt: tổng các phần bằng tổng thể, so khớp với SciPy, chạy trọn pipeline")
    seq.append((slide_end(), 9))

    tmp = Path(tempfile.mkdtemp())
    lst = []
    for i, (im, sec) in enumerate(seq):
        p = tmp / f"f{i:04d}.png"
        im.save(p)
        lst += [f"file '{p}'", f"duration {sec}"]
    lst.append(f"file '{tmp / f'f{len(seq)-1:04d}.png'}'")
    (tmp / "list.txt").write_text("\n".join(lst))
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(tmp / "list.txt"),
                    "-vf", "fps=30,format=yuv420p", "-c:v", "libx264", "-crf", "20", "-preset", "medium",
                    "-movflags", "+faststart", str(out)], check=True)
    shutil.rmtree(tmp)
    total = sum(s for _, s in seq)
    print(f"Video: {out} (~{total:.0f} giây)")


if __name__ == "__main__":
    main()

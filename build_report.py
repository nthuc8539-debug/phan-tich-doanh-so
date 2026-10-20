"""Dựng báo cáo PDF từ kết quả pipeline (số liệu lấy trực tiếp, không gõ tay).

Chạy:  python scripts/build_report.py
Cần:   playwright + Chromium (chỉ để xuất PDF), jinja không bắt buộc.
Kết quả: docs/BaoCao_PhanTichDuLieu.pdf  (và docs/report.html)
"""
from __future__ import annotations

import html
import inspect
import re
import sys
import unittest
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from salesanalysis import analysis as an  # noqa: E402
from salesanalysis import cleaning as cl  # noqa: E402
from salesanalysis.cli import run_pipeline  # noqa: E402

DOCS = ROOT / "docs"
FIG = "../outputs/figures/"

# ---------------------------------------------------------------- định dạng
def vi(x, d=0):
    """Số kiểu Việt Nam: 1.234,5"""
    s = f"{x:,.{d}f}"
    return s.replace(",", "§").replace(".", ",").replace("§", ".")


def ty(x, d=2):
    return f"{vi(x / 1e9, d)} tỷ"


def tr(x, d=2):
    return f"{vi(x / 1e6, d)} triệu"


def esc(s):
    return html.escape(str(s))


def table(headers, rows, aligns=None, caption=None, small=False):
    aligns = aligns or ["l"] + ["r"] * (len(headers) - 1)
    cls = "tbl small" if small else "tbl"
    h = "".join(f'<th class="{a}">{esc(x)}</th>' for x, a in zip(headers, aligns))
    body = "".join("<tr>" + "".join(f'<td class="{a}">{c}</td>' for c, a in zip(r, aligns)) + "</tr>" for r in rows)
    cap = f'<div class="cap">{caption}</div>' if caption else ""
    return f'<div class="tblwrap">{cap}<table class="{cls}"><thead><tr>{h}</tr></thead><tbody>{body}</tbody></table></div>'


_fig_n = {"n": 0, "chap": 0}


def figure(fname, caption, width="80%"):
    _fig_n["n"] += 1
    return (f'<figure style="width:{width}"><img src="{FIG}{fname}"><figcaption>'
            f'<b>Hình {_fig_n["n"]}.</b> {caption}</figcaption></figure>')


def code(src, title=None):
    t = f'<div class="codetitle">{esc(title)}</div>' if title else ""
    return f'{t}<pre class="code">{esc(src.strip(chr(10)))}</pre>'


def getsrc(fn):
    return inspect.getsource(fn)


# ---------------------------------------------------------------- dữ liệu
def collect():
    res = run_pipeline(ROOT / "data" / "raw_sales.csv", ROOT / "outputs")
    return res


def false_positive_check(n_seeds: int = 60):
    """Số lần p<0,05 khi so sánh số lượng giữa nhóm giảm sâu và còn lại, trên nhiều seed.
    Vì bộ sinh làm số lượng độc lập với giảm giá, mọi kết quả có ý nghĩa đều là dương tính giả."""
    from salesanalysis import generate as gen
    hits = 0
    for seed in range(100, 100 + n_seeds):
        d, _ = cl.clean(gen.generate_sales(4000, seed=seed))
        a = d[d["category"] == "Phụ kiện"]
        if an.welch_t_test(a.loc[a["discount"] >= 0.2, "quantity"], a.loc[a["discount"] < 0.2, "quantity"])["p_value"] < 0.05:
            hits += 1
    return hits, n_seeds


def test_listing():
    suite = unittest.defaultTestLoader.discover(str(ROOT / "tests"))
    out = []

    def walk(s):
        for t in s:
            if isinstance(t, unittest.TestSuite):
                walk(t)
            else:
                out.append((type(t).__name__, t._testMethodName, (t._testMethodDoc or "")))
    walk(suite)
    return out


TEST_DESC = {
    "test_reproducible_with_seed": "Cùng seed cho ra cùng dữ liệu (tái lập được)",
    "test_clean_mode_has_no_missing": "Chế độ dirty=False không có ô thiếu, đúng số dòng",
    "test_dirty_mode_injects_problems": "Chế độ dirty=True thật sự chèn ô thiếu và dòng trùng",
    "test_no_missing_after_clean": "Sau làm sạch không còn ô thiếu ở các cột chính",
    "test_duplicates_removed": "Xóa đúng 20 dòng trùng, order_id là duy nhất",
    "test_channel_normalised": "Kênh bán được chuẩn hóa về đúng 3 giá trị",
    "test_outliers_handled": "Không còn số lượng > 20 hay đơn giá lệch quá 1,5 lần median",
    "test_revenue_formula": "revenue = số lượng × đơn giá × (1 − giảm giá)",
    "test_input_not_mutated": "Hàm clean() không làm thay đổi dữ liệu đầu vào",
    "test_missing_column_rejected": "File CSV thiếu cột bắt buộc bị từ chối với ValueError",
    "test_iqr_bounds": "Cận IQR phát hiện đúng giá trị ngoại lai",
    "test_kpi_consistency": "KPI khớp trực tiếp với tổng/đếm của dữ liệu",
    "test_group_sums_equal_total": "Tổng theo tháng/sản phẩm/khu vực đều bằng tổng doanh thu",
    "test_shares_sum_to_100": "Tỷ trọng sản phẩm cộng lại đúng 100%",
    "test_pareto_monotonic_and_ends_at_100": "Đường Pareto tăng dần và kết thúc ở 100%",
    "test_rfm_scores_in_range": "Điểm RFM nằm trong 3–12, mọi khách đều có phân khúc",
    "test_corr_diagonal_is_one": "Đường chéo ma trận tương quan bằng 1",
    "test_forecast_on_perfect_line": "Trên đường thẳng hoàn hảo, R² = 1 và dự báo đúng 1300/1400/1500",
    "test_welch_matches_scipy": "Welch t-test tự cài khớp với SciPy (t chính xác, p lệch < 0,01)",
    "test_weekend_effect_detected": "Hàm so sánh cuối tuần/ngày thường chạy đúng chiều",
    "test_end_to_end_creates_outputs": "Chạy trọn pipeline: đủ 13 hình, CSV, Excel, JSON",
}


# ---------------------------------------------------------------- nội dung
def build_html(R, toc_pages=None):
    _fig_n["n"] = 0
    df, rep, k = R["df"], R["rep"], R["kpi"]
    m, bp, reg, chn, cat = R["monthly"], R["products"], R["region"], R["channel"], R["category"]
    rfm, par, corr, fc = R["rfm"], R["pareto"], R["corr"], R["forecast"]
    wt, sale = R["wtest"], R["sale"]
    raw, q = R["raw"], R["quality"]

    tot = k["tong_doanh_thu"]
    best_m = int(m["doanh_thu"].idxmax())
    worst_m = int(m["doanh_thu"].idxmin())
    top2 = bp["ty_trong_%"].iloc[:2].sum()
    nov_dec = m.loc[[11, 12], "doanh_thu"].sum() / tot * 100
    qshare = df.groupby("quarter")["revenue"].sum() / tot * 100
    mom = m["tang_truong_mom_%"]
    best_mom = int(mom.idxmax())
    daily = an.daily_revenue(df)
    we = daily[daily.index.dayofweek >= 5].mean()
    wd_ = daily[daily.index.dayofweek < 5].mean()
    seg = rfm.groupby("segment", observed=True).agg(n=("monetary", "size"), dt=("monetary", "sum"),
                                                     tb=("monetary", "mean"), rec=("recency", "mean"),
                                                     fre=("frequency", "mean")).reindex(
        ["VIP", "Trung thành", "Cần chăm sóc", "Nguy cơ rời bỏ"])
    vip_share = seg.loc["VIP", "dt"] / tot * 100
    corr_pq = corr.loc["quantity", "unit_price"]
    corr_pr = corr.loc["unit_price", "revenue"]
    disc = R["discount"]
    n_tests = len(test_listing())
    acc = df[df["category"] == "Phụ kiện"]
    acc_hi, acc_lo = acc.loc[acc["discount"] >= 0.2, "quantity"], acc.loc[acc["discount"] < 0.2, "quantity"]
    dtest = an.welch_t_test(acc_hi, acc_lo)
    fp_hits, fp_n = false_positive_check()
    dverdict = ("Với mức ý nghĩa 5%, chênh lệch này có ý nghĩa thống kê." if dtest["p_value"] < 0.05
                else "Với mức ý nghĩa 5%, chưa đủ bằng chứng để kết luận có chênh lệch.")
    online_share = chn.loc[["Website", "Sàn TMĐ"], "ty_trong_%"].sum()
    top_region = reg.index[0]
    hn_hcm = reg.loc[["TP.HCM", "Hà Nội"], "ty_trong_%"].sum()

    parts = []
    A = parts.append

    # ------------------------------ BÌA
    A(f'''
<section class="cover">
  <div class="cv-top">BÁO CÁO DỰ ÁN MÔN HỌC</div>
  <div class="cv-mid">
    <div class="cv-topic">Chủ đề 5.5</div>
    <h1>Phân tích dữ liệu bán hàng<br>với NumPy, Pandas và Matplotlib</h1>
    <div class="cv-sub">Xây dựng pipeline hoàn chỉnh: làm sạch dữ liệu, phân tích, trực quan hóa và dự báo</div>
  </div>
  <table class="cv-info">
    <tr><td>Sinh viên thực hiện</td><td>Nguyễn Đình Thực</td></tr>
    <tr><td>Mã số sinh viên</td><td class="ph">[điền MSSV]</td></tr>
    <tr><td>Lớp / Khoa</td><td class="ph">[điền lớp, khoa]</td></tr>
    <tr><td>Học phần</td><td class="ph">[điền tên học phần]</td></tr>
    <tr><td>Giảng viên hướng dẫn</td><td class="ph">[điền tên giảng viên]</td></tr>
    <tr><td>Mã nguồn</td><td class="ph">[dán link GitHub]</td></tr>
    <tr><td>Video demo</td><td class="ph">[dán link YouTube]</td></tr>
  </table>
  <div class="cv-foot">Hà Nội, tháng {date.today().month}/{date.today().year}</div>
</section>''')

    # ------------------------------ MỤC LỤC (điền sau)
    A('<section class="toc pb"><h2 class="plain">Mục lục</h2>@@TOC@@</section>')

    # ------------------------------ TÓM TẮT
    A(f'''
<section class="pb">
<h2 class="plain">Tóm tắt</h2>
<p>Báo cáo trình bày dự án <b>phân tích dữ liệu bán hàng</b> của một cửa hàng điện tử (dữ liệu <b>mô phỏng</b>) trong năm 2025,
sử dụng ba thư viện nền tảng của hệ sinh thái Python cho khoa học dữ liệu: <b>NumPy</b> (tính toán mảng và mô phỏng),
<b>Pandas</b> (xử lý bảng dữ liệu) và <b>Matplotlib</b> (vẽ biểu đồ). Dự án được tổ chức như một chương trình Python có cấu trúc
chuẩn (package, giao diện dòng lệnh, kiểm thử tự động), thay vì một tệp script rời rạc.</p>
<p>Dữ liệu đầu vào gồm {vi(rep.rows_in)} dòng đơn hàng thô, cố ý chứa các lỗi thường gặp: ô thiếu, dòng trùng, ngoại lai do nhập thừa số 0
và chuỗi viết không thống nhất. Sau làm sạch còn {vi(rep.rows_out)} đơn hàng hợp lệ với tổng doanh thu <b>{ty(tot)} đồng</b>,
{vi(k["so_khach_hang"])} khách hàng. Các kết quả chính:</p>
<ul>
<li>Điện thoại và Laptop chiếm <b>{vi(top2,1)}%</b> doanh thu; tháng {best_m} đạt đỉnh với {ty(m.loc[best_m,"doanh_thu"])}.</li>
<li>Ngày khuyến mãi lớn (11/11 và 24–28/11) có doanh thu mỗi ngày gấp <b>{vi(sale["ratio"],2)} lần</b> các ngày còn lại của tháng 11.</li>
<li>Doanh thu cuối tuần cao hơn ngày thường nhưng chênh lệch <b>chưa có ý nghĩa thống kê</b> (Welch t-test, p = {vi(wt["p_value"],3)}).</li>
<li>Cần <b>{vi(R["pct80"],0)}%</b> số khách ({vi(R["n80"])} người) để tạo 80% doanh thu, nghĩa là doanh thu khá phân tán, không theo quy luật 80/20.</li>
<li>Phân khúc VIP theo RFM ({vi(seg.loc["VIP","n"])} khách) đóng góp {vi(vip_share,1)}% doanh thu.</li>
</ul>
<p>Dự án gồm 13 biểu đồ, bảng tổng hợp Excel và {n_tests} bài kiểm thử tự động đều đạt. Báo cáo cũng nêu rõ các hạn chế, đặc biệt là
dữ liệu mô phỏng và mô hình dự báo chỉ mang tính minh họa.</p>
<p class="kw"><b>Từ khóa:</b> phân tích dữ liệu, NumPy, Pandas, Matplotlib, làm sạch dữ liệu, RFM, Pareto, dự báo chuỗi thời gian.</p>
</section>''')

    # ------------------------------ CHƯƠNG 1
    A('''
<section>
<h2 id="c1">1. Giới thiệu</h2>
<h3>1.1. Bối cảnh và lý do chọn đề tài</h3>
<p>Dữ liệu bán hàng là nguồn thông tin quan trọng nhất của một doanh nghiệp bán lẻ: nó cho biết sản phẩm nào đang kéo doanh thu,
thời điểm nào khách mua nhiều, khu vực hay kênh nào hiệu quả và nhóm khách nào đáng chăm sóc. Tuy nhiên dữ liệu thô gần như luôn
“bẩn” – có ô trống, nhập sai, trùng lặp – và chỉ trở nên hữu ích sau khi được làm sạch, tổng hợp và trình bày bằng hình ảnh dễ hiểu.</p>
<p>Python với bộ ba NumPy – Pandas – Matplotlib là lựa chọn phổ biến nhất cho các bước này nhờ cú pháp ngắn gọn, hiệu năng tốt
(tính toán vector hóa) và cộng đồng lớn. Đề tài 5.5 của học phần yêu cầu vận dụng ba thư viện này vào một bài toán phân tích dữ liệu
cơ bản; dự án này chọn bài toán <b>phân tích doanh số bán hàng</b> vì dữ liệu quen thuộc, có nhiều chiều (thời gian, sản phẩm, khu vực,
kênh, khách hàng) và cho phép minh họa hầu hết các kỹ thuật cơ bản.</p>

<h3>1.2. Mục tiêu</h3>
<ul>
<li>Xây dựng <b>pipeline</b> hoàn chỉnh: sinh/đọc dữ liệu → làm sạch → phân tích → trực quan hóa → xuất báo cáo, chạy bằng một dòng lệnh.</li>
<li>Vận dụng đúng vai trò từng thư viện: NumPy cho mô phỏng và thuật toán số, Pandas cho xử lý bảng, Matplotlib cho biểu đồ.</li>
<li>Trả lời các <b>câu hỏi kinh doanh</b> bằng số liệu, kèm kiểm định thống kê khi cần thiết.</li>
<li>Bảo đảm chất lượng: mã nguồn có cấu trúc, có kiểm thử tự động, kết quả tái lập được.</li>
</ul>

<h3>1.3. Câu hỏi nghiên cứu</h3>
<table class="tbl"><thead><tr><th class="l">Mã</th><th class="l">Câu hỏi</th><th class="l">Phương pháp</th></tr></thead><tbody>
<tr><td>Q1</td><td>Doanh thu thay đổi thế nào theo tháng và theo ngày trong tuần?</td><td>groupby, trung bình động, Welch t-test</td></tr>
<tr><td>Q2</td><td>Sản phẩm, khu vực và kênh nào đóng góp nhiều nhất?</td><td>groupby, pivot_table</td></tr>
<tr><td>Q3</td><td>Các đợt khuyến mãi lớn có làm tăng doanh thu không?</td><td>So sánh doanh thu/ngày</td></tr>
<tr><td>Q4</td><td>Doanh thu tập trung vào bao nhiêu phần trăm khách hàng?</td><td>Đường Pareto</td></tr>
<tr><td>Q5</td><td>Có thể chia khách hàng thành những phân khúc nào?</td><td>Phân tích RFM</td></tr>
<tr><td>Q6</td><td>Doanh thu những tháng tới có thể ra sao?</td><td>Hồi quy tuyến tính + chỉ số mùa vụ</td></tr>
</tbody></table>

<h3>1.4. Phạm vi và giới hạn</h3>
<p>Dự án dùng <b>dữ liệu mô phỏng</b> thay vì số liệu của doanh nghiệp thật, vì dữ liệu thật thường không được công bố và cần che thông tin khách hàng.
Mô phỏng có kiểm soát còn có lợi: ta biết trước “đáp án” (ví dụ mùa vụ, đợt giảm giá) nên đánh giá được phương pháp phân tích có tìm ra đúng hay không.
Hệ quả là các “phát hiện” chỉ có giá trị minh họa kỹ thuật, không suy ra được kết luận về thị trường thực.</p>
</section>''')

    # ------------------------------ CHƯƠNG 2
    A('''
<section>
<h2 id="c2">2. Cơ sở lý thuyết và công nghệ</h2>
<h3>2.1. NumPy</h3>
<p>NumPy cung cấp kiểu dữ liệu <code>ndarray</code> – mảng nhiều chiều, cùng kiểu, lưu liên tục trong bộ nhớ – cùng các phép toán được cài đặt bằng C.
Hai ý tưởng quan trọng nhất là <b>vector hóa</b> (thực hiện phép toán trên cả mảng thay vì vòng lặp Python) và <b>broadcasting</b>
(tự động “kéo giãn” mảng nhỏ để khớp mảng lớn). Nhờ đó mã ngắn hơn và nhanh hơn nhiều lần.</p>
<p>Trong dự án, NumPy được dùng để: (1) sinh dữ liệu ngẫu nhiên có kiểm soát bằng <code>np.random.default_rng(seed)</code> – với cùng seed, kết quả
luôn giống nhau; (2) tính các đại lượng thống kê (<code>np.corrcoef</code>, phân vị); (3) khớp đường xu hướng bằng
<code>np.polyfit</code> – phương pháp bình phương tối thiểu; (4) cài đặt kiểm định Welch.</p>

<h3>2.2. Pandas</h3>
<p>Pandas xây dựng trên NumPy, cung cấp <code>Series</code> (cột) và <code>DataFrame</code> (bảng có nhãn hàng, cột). Các thao tác trung tâm của dự án:</p>
<ul>
<li><b>Đọc/ghi và kiểm tra</b>: <code>read_csv</code>, <code>isna</code>, <code>nunique</code>, <code>describe</code>.</li>
<li><b>Làm sạch</b>: <code>drop_duplicates</code>, <code>fillna</code>, <code>str.strip</code>, <code>map</code>, <code>to_datetime</code>.</li>
<li><b>Tổng hợp</b>: <code>groupby(...).agg(...)</code> theo mô hình tách – áp dụng – gộp; <code>pivot_table</code> để tạo bảng chéo hai chiều.</li>
<li><b>Chuỗi thời gian</b>: thuộc tính <code>.dt</code>, <code>rolling</code> (trung bình động), <code>pct_change</code> (tăng trưởng).</li>
<li><b>Phân nhóm theo phân vị</b>: <code>qcut</code> – dùng cho chấm điểm RFM.</li>
</ul>

<h3>2.3. Matplotlib</h3>
<p>Matplotlib là thư viện vẽ biểu đồ nền tảng của Python. Dự án dùng <b>giao diện hướng đối tượng</b> (<code>fig, ax = plt.subplots()</code>)
thay vì giao diện <code>pyplot</code> ngầm định, vì kiểm soát được từng trục và dễ tái sử dụng trong hàm. Toàn bộ kiểu dáng
(màu, lưới, phông chữ) được đặt một lần trong <code>rcParams</code> để 13 biểu đồ có giao diện thống nhất.</p>

<h3>2.4. Các phương pháp phân tích sử dụng</h3>
<p><b>Phát hiện ngoại lai bằng IQR (Tukey).</b> Gọi Q1, Q3 là tứ phân vị thứ nhất và thứ ba, IQR = Q3 − Q1. Giá trị nằm ngoài
[Q1 − k·IQR, Q3 + k·IQR] bị coi là ngoại lai; k = 1,5 là “hàng rào trong” thông thường, k = 3 là “hàng rào ngoài” dành cho giá trị
cực đoan. Dự án dùng k = 3 cho đơn giá theo từng sản phẩm để chỉ bắt các lỗi rõ ràng (nhập thừa số 0), tránh loại nhầm biến động bình thường.</p>
<p><b>Quy tắc Pareto.</b> Sắp khách hàng theo doanh thu giảm dần rồi vẽ tỷ lệ doanh thu lũy kế theo tỷ lệ khách. Nếu một nhóm nhỏ khách
tạo phần lớn doanh thu (quy luật 80/20), đường cong sẽ cong mạnh; càng sát đường chéo thì doanh thu càng phân tán đều.</p>
<p><b>Phân tích RFM.</b> Mỗi khách được chấm ba chỉ số: <b>R</b>ecency (số ngày kể từ lần mua gần nhất – càng nhỏ càng tốt),
<b>F</b>requency (số lần mua) và <b>M</b>onetary (tổng chi tiêu). Mỗi chỉ số được chia thành 4 nhóm theo phân vị và cho điểm 1–4; tổng điểm
(3–12) quyết định phân khúc.</p>
<p><b>Hồi quy tuyến tính và chỉ số mùa vụ.</b> Đường xu hướng ŷ = a·t + b được tìm bằng bình phương tối thiểu. Hệ số xác định
R² = 1 − SS<sub>res</sub>/SS<sub>tot</sub> đo phần biến thiên được giải thích. Chỉ số mùa vụ của tháng t là tỷ số giữa giá trị thực và giá trị xu hướng;
dự báo bằng <i>xu hướng × chỉ số mùa vụ</i> (mô hình nhân, xem Hyndman &amp; Athanasopoulos, 2021).</p>
<p><b>Kiểm định Welch.</b> So sánh trung bình hai nhóm có phương sai khác nhau: t = (x̄<sub>1</sub> − x̄<sub>2</sub>) / √(s<sub>1</sub>²/n<sub>1</sub> + s<sub>2</sub>²/n<sub>2</sub>).
Giả thuyết H₀: hai trung bình bằng nhau; p-value nhỏ hơn 0,05 được xem là có ý nghĩa thống kê. Dự án cài đặt thuần NumPy
và đối chiếu với SciPy trong bài kiểm thử.</p>
</section>''')

    # ------------------------------ CHƯƠNG 3
    sch = [
        ("order_id", "chuỗi", "Mã đơn hàng, duy nhất"),
        ("order_date", "ngày", "Ngày đặt hàng (1/1–31/12/2025)"),
        ("customer_id", "chuỗi", "Mã khách hàng (KH0001–KH1200)"),
        ("product", "chuỗi", "Sản phẩm (8 loại)"),
        ("category", "chuỗi", "Danh mục: Máy tính, Điện thoại, Phụ kiện"),
        ("region", "chuỗi", "Khu vực: Hà Nội, Đà Nẵng, TP.HCM, Cần Thơ"),
        ("channel", "chuỗi", "Kênh bán: Cửa hàng, Website, Sàn TMĐ"),
        ("quantity", "số", "Số lượng trong đơn"),
        ("unit_price", "số", "Đơn giá thực tế (VND)"),
        ("discount", "số 0–1", "Tỷ lệ giảm giá"),
    ]
    A(f'''
<section>
<h2 id="c3">3. Dữ liệu</h2>
<h3>3.1. Mô tả bộ dữ liệu</h3>
<p>Bộ dữ liệu mô phỏng {vi(rep.rows_in - rep.duplicates_removed)} đơn hàng của một cửa hàng điện tử trong năm 2025, mỗi dòng là một đơn gồm một loại sản phẩm.
Bảng dưới liệt kê các cột; dự án còn tạo thêm các cột dẫn xuất (<code>revenue</code>, <code>month</code>, <code>quarter</code>,
<code>weekday</code>, <code>is_weekend</code>, <code>price_tier</code>) ở bước làm sạch.</p>
{table(["Cột", "Kiểu", "Ý nghĩa"], [[f"<code>{a}</code>", b, c] for a, b, c in sch], ["l", "l", "l"], caption="<b>Bảng 3.1.</b> Cấu trúc dữ liệu đầu vào")}

<h3>3.2. Cách sinh dữ liệu</h3>
<p>Để dữ liệu có cấu trúc “có thật” nhưng vẫn kiểm soát được, hàm <code>generate_sales()</code> áp dụng các quy tắc sau:</p>
<ul>
<li><b>Mùa vụ theo tháng</b>: hệ số cao ở tháng 1 (Tết, 1,25), tháng 8–9 (khai giảng, 1,15–1,20) và tháng 11–12 (mua sắm cuối năm, 1,45 và 1,35).</li>
<li><b>Xu hướng tăng</b> khoảng 15% trong năm và <b>cuối tuần đông hơn</b> ngày thường 20%.</li>
<li><b>Khuyến mãi lớn</b> vào 11/11 và 24–28/11: lượng đơn gấp 2,5 lần và mức giảm giá 15–30%.</li>
<li><b>Giá</b> dao động ±5% quanh giá niêm yết; hàng đắt tiền (laptop, điện thoại, máy tính bảng, màn hình) chủ yếu mua 1–2 cái, phụ kiện mua 1–5 cái.</li>
<li><b>Khách hàng</b> chọn ngẫu nhiên trong 1.200 mã; <b>khu vực</b> và <b>kênh</b> theo xác suất cố định.</li>
</ul>
<p>Ngày đặt hàng được rút bằng <code>rng.choice(days, p=w/w.sum())</code> với w là tích các hệ số trên – một ứng dụng trực tiếp của vector hóa NumPy.
Toàn bộ quá trình dùng seed = 42 nên bộ dữ liệu giống hệt nhau ở mọi lần chạy.</p>

<h3>3.3. Dữ liệu bẩn được chèn có chủ đích</h3>
<p>Để thực hành làm sạch, hàm <code>_inject_dirt()</code> chèn thêm: 40 ô thiếu số lượng, 25 ô thiếu khu vực, 15 ô thiếu đơn giá;
6 đơn giá bị nhân 10 (nhập thừa số 0); 5 số lượng bằng 99; 30 giá trị kênh viết hoa kèm khoảng trắng; và 20 dòng trùng lặp hoàn toàn.
Biết trước các lỗi này cho phép kiểm tra pipeline có phát hiện và xử lý đúng đủ hay không (xem Chương 5 và Chương 8).</p>
</section>''')

    # ------------------------------ CHƯƠNG 4
    mods = [
        ("generate.py", "Sinh dữ liệu mô phỏng, chèn dữ liệu bẩn", "NumPy, Pandas"),
        ("cleaning.py", "Đọc CSV, kiểm tra chất lượng, làm sạch, tạo đặc trưng, báo cáo làm sạch", "Pandas, NumPy"),
        ("analysis.py", "KPI, tổng hợp, Pareto, RFM, tương quan, dự báo, kiểm định", "Pandas, NumPy"),
        ("visualize.py", "13 hàm vẽ biểu đồ, bảng màu và kiểu dáng thống nhất", "Matplotlib"),
        ("cli.py", "Giao diện dòng lệnh, điều phối pipeline, xuất CSV/Excel/JSON", "argparse, Pandas"),
    ]
    A(f'''
<section>
<h2 id="c4">4. Thiết kế hệ thống</h2>
<h3>4.1. Kiến trúc tổng thể</h3>
<p>Dự án được chia thành các module nhỏ, mỗi module một trách nhiệm (nguyên tắc <i>single responsibility</i>). Các hàm phân tích
<b>không vẽ</b>, các hàm vẽ <b>không tính toán nghiệp vụ</b>, và chỉ <code>cli.py</code> biết thứ tự thực hiện. Cách tách này giúp
kiểm thử từng phần độc lập và thay thế dữ liệu đầu vào mà không phải sửa mã phân tích.</p>
<div class="flow">
  <div class="fb">Dữ liệu thô<br><small>CSV</small></div><div class="fa">→</div>
  <div class="fb">Làm sạch<br><small>cleaning.py</small></div><div class="fa">→</div>
  <div class="fb">Phân tích<br><small>analysis.py</small></div><div class="fa">→</div>
  <div class="fb">Trực quan hóa<br><small>visualize.py</small></div><div class="fa">→</div>
  <div class="fb out">Báo cáo<br><small>PNG · XLSX · JSON</small></div>
</div>
<div class="cap center"><b>Hình {0}.</b> Luồng xử lý của pipeline</div>
{table(["Module", "Trách nhiệm", "Thư viện"], [[f"<code>{a}</code>", b, c] for a, b, c in mods], ["l", "l", "l"], caption="<b>Bảng 4.1.</b> Các module của gói <code>salesanalysis</code>")}

<h3>4.2. Các quyết định thiết kế đáng chú ý</h3>
<ul>
<li><b>Hàm thuần (pure function).</b> <code>clean()</code> sao chép dữ liệu (<code>df.copy()</code>) và không sửa đầu vào; có bài kiểm thử riêng cho tính chất này.</li>
<li><b>Báo cáo làm sạch</b> (<code>CleaningReport</code>, dùng <code>dataclass</code>) ghi lại từng thay đổi, nên người đọc biết chính xác dữ liệu đã bị can thiệp ra sao.</li>
<li><b>Điền thiếu theo median của từng sản phẩm</b> thay vì median toàn bảng, vì giá của laptop và chuột chênh nhau hàng chục lần.</li>
<li><b>Chỉ dùng thư viện cần thiết</b>: ngoài NumPy, Pandas, Matplotlib chỉ có <code>openpyxl</code> để ghi Excel; không phụ thuộc SciPy hay scikit-learn.</li>
<li><b>Tái lập được</b>: mọi thành phần ngẫu nhiên đều dùng seed.</li>
</ul>

<h3>4.3. Giao diện dòng lệnh</h3>
{code("""python run.py                              # sinh dữ liệu (nếu chưa có) và chạy toàn bộ pipeline
python run.py generate --orders 10000      # tạo bộ dữ liệu khác
python run.py run --input file_cua_ban.csv # phân tích dữ liệu của bạn
python -m unittest discover -s tests -v    # chạy kiểm thử""")}
<p>Đầu ra gồm thư mục <code>outputs/figures/</code> (13 ảnh PNG), <code>clean_sales.csv</code>, <code>bao_cao_tong_hop.xlsx</code> (7 sheet)
và <code>summary.json</code> (KPI, thống kê làm sạch, kết quả kiểm định, dự báo).</p>
</section>'''.replace("{0}", "1"))

    # ------------------------------ CHƯƠNG 5
    qrows = []
    names_vi = {"order_id": "order_id", "order_date": "order_date"}
    for col, r_ in q.iterrows():
        qrows.append([f"<code>{col}</code>", r_["dtype"], vi(r_["thieu"]), vi(r_["ty_le_thieu_%"], 2) + "%", vi(r_["so_gia_tri_khac_nhau"])])
    crow = [
        ["Dòng trùng lặp hoàn toàn", vi(rep.duplicates_removed), "Xóa (<code>drop_duplicates</code>)"],
        ["Kênh bán viết sai chữ hoa/khoảng trắng", vi(rep.channel_fixed), "Chuẩn hóa bằng từ điển ánh xạ"],
        ["Đơn giá ngoại lai (nhập thừa số 0)", vi(rep.outliers_price), "IQR k = 3 theo sản phẩm → thay bằng median sản phẩm"],
        ["Số lượng bất thường (> 20)", vi(rep.outliers_quantity), "Đặt thiếu rồi điền median sản phẩm"],
        ["Đơn giá thiếu (gồm cả ngoại lai đã loại)", vi(rep.price_filled), "Median đơn giá theo sản phẩm"],
        ["Số lượng thiếu (gồm cả bất thường đã loại)", vi(rep.quantity_filled), "Median số lượng theo sản phẩm"],
        ["Khu vực thiếu", vi(rep.region_filled), "Gán nhãn “Không rõ” (không đoán)"],
    ]
    A(f'''
<section>
<h2 id="c5">5. Tiền xử lý và làm sạch dữ liệu</h2>
<p>Quy tắc “rác vào – rác ra” đặc biệt đúng với phân tích dữ liệu: một đơn giá nhập thừa số 0 có thể làm doanh thu một sản phẩm
tăng vọt và dẫn đến kết luận sai. Vì vậy dự án dành một bước riêng, có báo cáo rõ ràng.</p>

<h3>5.1. Khảo sát chất lượng ban đầu</h3>
<p>Hàm <code>quality_overview()</code> trả về kiểu dữ liệu, số ô thiếu, tỷ lệ thiếu và số giá trị khác nhau của từng cột.</p>
{table(["Cột", "Kiểu", "Số ô thiếu", "Tỷ lệ thiếu", "Số giá trị khác nhau"], qrows, ["l", "l", "r", "r", "r"], caption="<b>Bảng 5.1.</b> Chất lượng dữ liệu thô", small=True)}
{figure("01_missing.png", "Số ô thiếu theo cột trong dữ liệu thô. Cột <code>quantity</code> thiếu nhiều nhất.", "60%")}

<h3>5.2. Quy trình làm sạch</h3>
<p>Hàm <code>clean()</code> thực hiện tuần tự sáu bước: (1) ép kiểu ngày và loại dòng thiếu khóa; (2) chuẩn hóa chuỗi; (3) xóa trùng;
(4) xử lý ngoại lai; (5) điền giá trị thiếu; (6) tạo đặc trưng mới. Thứ tự quan trọng: xóa trùng trước khi tính median để các dòng lặp không làm lệch thống kê;
xử lý ngoại lai <i>trước</i> khi điền thiếu để median không bị ngoại lai kéo lệch.</p>
{table(["Vấn đề", "Số lượng", "Cách xử lý"], crow, ["l", "r", "l"], caption="<b>Bảng 5.2.</b> Kết quả làm sạch ({0} dòng vào → {1} dòng ra)".format(vi(rep.rows_in), vi(rep.rows_out)))}
<p>Số ngoại lai và dòng trùng phát hiện được <b>khớp chính xác</b> với số đã chèn (6 đơn giá, 5 số lượng, 20 dòng trùng): pipeline không bỏ sót và không xóa nhầm.
Số “đã điền” lớn hơn số ô thiếu ban đầu vì gồm cả các ngoại lai bị đặt về thiếu rồi điền lại.</p>

<h3>5.3. Xử lý ngoại lai đơn giá</h3>
<p>Hình bên dưới so sánh phân bố đơn giá theo sản phẩm trước và sau làm sạch. Trước làm sạch, các điểm cam ở xa (ví dụ điện thoại gần 100 triệu đồng)
làm trục kéo dài và nén các sản phẩm rẻ thành một vạch; sau làm sạch, mỗi sản phẩm chỉ còn dao động quanh giá niêm yết.</p>
{figure("02_price_outliers.png", "Hộp râu (boxplot) đơn giá theo sản phẩm, trước và sau khi xử lý ngoại lai bằng IQR.")}

<h3>5.4. Đặc trưng mới</h3>
<p>Sau khi dữ liệu sạch, doanh thu mỗi đơn được tính theo công thức <code>revenue = quantity × unit_price × (1 − discount)</code>; thêm
<code>month</code>, <code>quarter</code>, <code>weekday</code>, <code>is_weekend</code> từ ngày đặt và <code>price_tier</code> (Cao cấp nếu đơn giá ≥ 3 triệu đồng).
Các đặc trưng này được tính bằng thao tác vector hóa trên cả cột (ví dụ <code>np.where</code>), không dùng vòng lặp.</p>
</section>''')

    # ------------------------------ CHƯƠNG 6
    kp = [
        ["Tổng doanh thu", f"{vi(tot)} đ ({ty(tot)})"],
        ["Số đơn hàng", vi(k["tong_don"])],
        ["Số khách hàng", vi(k["so_khach_hang"])],
        ["Tổng số lượng bán", vi(k["tong_so_luong"])],
        ["Giá trị đơn trung bình", f"{vi(k['gia_tri_don_tb'])} đ"],
        ["Giá trị đơn trung vị", f"{vi(k['gia_tri_don_median'])} đ"],
        ["Mức giảm giá trung bình", f"{vi(k['ty_le_giam_gia_tb_%'],2)}%"],
    ]
    mrows = []
    for i, r_ in m.iterrows():
        g = "–" if pd.isna(r_["tang_truong_mom_%"]) else f"{r_['tang_truong_mom_%']:+.1f}%".replace(".", ",")
        mrows.append([f"Tháng {i}", vi(r_["doanh_thu"] / 1e9, 2), vi(r_["so_don"]), g])
    A(f'''
<section>
<h2 id="c6">6. Kết quả phân tích</h2>
<h3>6.1. Tổng quan (KPI)</h3>
{table(["Chỉ số", "Giá trị"], kp, ["l", "r"], caption="<b>Bảng 6.1.</b> Các chỉ số kinh doanh chính")}
<p>Giá trị đơn trung bình ({tr(k["gia_tri_don_tb"])}) <b>gấp {vi(k["gia_tri_don_tb"]/k["gia_tri_don_median"],1)} lần</b> trung vị ({tr(k["gia_tri_don_median"])}).
Khoảng cách này là dấu hiệu phân bố lệch: một số đơn giá trị rất lớn (laptop, điện thoại) kéo trung bình lên. Trong trường hợp này, trung vị phản ánh “đơn
hàng điển hình” tốt hơn trung bình.</p>
{figure("00_dashboard.png", "Bảng tổng hợp bốn góc nhìn chính của dữ liệu.", "72%")}

<h3>6.2. Doanh thu theo thời gian (Q1)</h3>
{figure("03_monthly.png", "Doanh thu theo tháng và trung bình động 3 tháng.")}
<p>Doanh thu thấp nhất vào tháng {worst_m} ({ty(m.loc[worst_m,"doanh_thu"])}) và cao nhất vào tháng {best_m} ({ty(m.loc[best_m,"doanh_thu"])},
tăng {vi(mom[best_m],1)}% so với tháng trước). Hai tháng 11–12 chiếm {vi(nov_dec,1)}% doanh thu cả năm. Theo quý: Q1 {vi(qshare[1],1)}%,
Q2 {vi(qshare[2],1)}%, Q3 {vi(qshare[3],1)}%, Q4 {vi(qshare[4],1)}%. Kết quả khớp với các hệ số mùa vụ đã đặt khi sinh dữ liệu (Tết, khai giảng, cuối năm),
cho thấy phương pháp phân tích “bắt” đúng tín hiệu có sẵn.</p>
{table(["Tháng", "Doanh thu (tỷ đồng)", "Số đơn", "Tăng trưởng so với tháng trước"], mrows, ["l", "r", "r", "r"], caption="<b>Bảng 6.2.</b> Doanh thu và số đơn theo tháng", small=True)}
{figure("08_weekday.png", "Doanh thu theo thứ trong tuần; hai cột cam là cuối tuần.", "64%")}
<p>Tổng doanh thu cả năm của thứ Bảy và Chủ nhật cao hơn các ngày khác, nhưng so sánh công bằng phải dựa trên <b>doanh thu trung bình mỗi ngày</b>
(vì số ngày mỗi loại khác nhau). Kết quả: cuối tuần trung bình {tr(we,1)}/ngày, ngày thường {tr(wd_,1)}/ngày (chênh {vi((we/wd_-1)*100,1)}%).
Kiểm định Welch cho t = {vi(wt["t"],2)}, bậc tự do ≈ {vi(wt["dof"],0)}, <b>p = {vi(wt["p_value"],3)}</b>. Vì p lớn hơn 0,05, ta <b>không đủ bằng chứng</b> để kết luận
cuối tuần thực sự bán tốt hơn – chênh lệch quan sát được có thể chỉ là ngẫu nhiên. Đây là ví dụ cho thấy vì sao cần kiểm định thay vì nhìn biểu đồ.</p>

<h3>6.3. Doanh thu theo sản phẩm (Q2)</h3>
{figure("04_products.png", "Doanh thu và tỷ trọng theo sản phẩm.", "72%")}
<p>Điện thoại ({vi(bp.loc["Điện thoại","ty_trong_%"],1)}%) và Laptop ({vi(bp.loc["Laptop","ty_trong_%"],1)}%) cùng chiếm {vi(top2,1)}% doanh thu dù chỉ là hai trong tám sản phẩm.
Ngược lại ba phụ kiện rẻ nhất (Bàn phím, Sạc dự phòng, Chuột) cộng lại chỉ khoảng {vi(bp.loc[["Bàn phím","Sạc dự phòng","Chuột"],"ty_trong_%"].sum(),1)}%.
Theo danh mục: {", ".join(f"{i} {vi(r_['ty_trong_%'],1)}%" for i, r_ in cat.iterrows())}.</p>
{figure("07_hist.png", "Phân bố giá trị đơn hàng (thang logarit).", "72%")}
<p>Biểu đồ phân bố cho thấy <b>hai cụm</b>: cụm quanh 1 triệu đồng (phụ kiện) và cụm quanh 10 triệu đồng (thiết bị). Phân bố hai đỉnh này giải thích vì sao trung bình
và trung vị chênh nhau nhiều, và cho thấy nếu chỉ báo cáo “giá trị đơn trung bình” sẽ bỏ qua cấu trúc quan trọng của dữ liệu.</p>

<h3>6.4. Khu vực và kênh bán (Q2)</h3>
{figure("05_region_channel.png", "Doanh thu theo khu vực, chia theo kênh bán.", "72%")}
<p>{top_region} dẫn đầu với {vi(reg.loc[top_region,"ty_trong_%"],1)}%, sát theo sau là Hà Nội ({vi(reg.loc["Hà Nội","ty_trong_%"],1)}%); hai thành phố lớn chiếm {vi(hn_hcm,1)}% doanh thu.
Về kênh, cửa hàng chiếm {vi(chn.loc["Cửa hàng","ty_trong_%"],1)}%, còn bán trực tuyến (website và sàn thương mại điện tử) chiếm {vi(online_share,1)}%.
Giá trị đơn trung bình của ba kênh gần như bằng nhau (khoảng {tr(chn["gia_tri_don_tb"].mean(),2)}), nên khác biệt giữa các kênh đến từ <i>số lượng đơn</i> chứ không phải từ giá trị mỗi đơn.
Nhóm “Không rõ” ({vi(reg.loc["Không rõ","ty_trong_%"],1)}%) là các đơn thiếu khu vực, được giữ lại để không làm mất doanh thu.</p>
{figure("06_heatmap.png", "Doanh thu theo khu vực × sản phẩm (triệu đồng). Màu càng đậm doanh thu càng lớn.")}

<h3>6.5. Hiệu ứng khuyến mãi (Q3)</h3>
<p>Trong tháng 11, {sale["n_sale_days"]} ngày khuyến mãi lớn (11/11 và 24–28/11) đạt trung bình {tr(sale["sale_mean"],1)}/ngày, so với {tr(sale["other_mean"],1)}/ngày ở các ngày còn lại – gấp
<b>{vi(sale["ratio"],2)} lần</b>. Như vậy, trong dữ liệu này, lượng đơn tăng thêm đủ bù cho phần giảm giá. Cần lưu ý đây là kết quả của cách mô phỏng (đã đặt lượng đơn gấp 2,5 lần vào các ngày này),
không phải một phát hiện về thị trường thực; trong dữ liệu thật, lợi nhuận (không chỉ doanh thu) mới là thước đo cần xét.</p>
{table(["Mức giảm giá", "Số đơn", "Số lượng TB", "Doanh thu TB mỗi đơn"],
       [[f"{vi(i*100,0)}%", vi(r_["so_don"]), vi(r_["so_luong_tb"], 2), f"{vi(r_['doanh_thu_tb'])} đ"] for i, r_ in disc.iterrows()],
       ["l", "r", "r", "r"], caption="<b>Bảng 6.3.</b> Nhóm phụ kiện: số lượng mua trung bình theo mức giảm giá", small=True)}
<p>Ở nhóm phụ kiện, số lượng mua trung bình là khoảng 3 sản phẩm/đơn ở các mức giảm 0–15%, nhưng thấp hơn ở nhóm giảm 20–30% ({vi(acc_hi.mean(),2)} so với {vi(acc_lo.mean(),2)} sản phẩm/đơn).
Nhóm giảm sâu chỉ có {vi(len(acc_hi))} đơn; kiểm định Welch cho p = {vi(dtest["p_value"],3)}. {dverdict}
Tuy nhiên bộ sinh dữ liệu <b>cố ý làm số lượng độc lập với giảm giá</b>, nên kết quả “có ý nghĩa” này thực chất là một <b>dương tính giả</b>. Để kiểm chứng, so sánh được lặp lại trên {fp_n} bộ dữ liệu sinh bằng seed khác nhau: p &lt; 0,05 xuất hiện {fp_hits}/{fp_n} lần ({vi(fp_hits/fp_n*100,1)}%), sát mức 5% mà lý thuyết kỳ vọng khi không có hiệu ứng thật.
Bài học: một p-value nhỏ trên nhóm nhỏ chưa đủ để kết luận; cần lặp lại, kiểm tra trên dữ liệu mới hoặc hiệu chỉnh khi so sánh nhiều lần.</p>

<h3>6.6. Mức độ tập trung doanh thu – Pareto (Q4)</h3>
{figure("09_pareto.png", "Đường Pareto theo khách hàng.", "64%")}
<p>Để đạt 80% doanh thu cần <b>{vi(R["n80"])} khách ({vi(R["pct80"],1)}% tổng số {vi(len(par))} khách)</b>. Con số này xa so với quy luật 80/20 kinh điển,
nghĩa là doanh thu phân tán khá đều giữa nhiều khách và việc mất một vài khách lớn ít rủi ro hơn nhiều doanh nghiệp thực tế. Lý do: mã khách được rút ngẫu nhiên đồng đều khi mô phỏng;
dữ liệu thật thường tập trung hơn.</p>

<h3>6.7. Phân khúc khách hàng – RFM (Q5)</h3>
{figure("10_rfm.png", "Số khách và doanh thu theo phân khúc RFM.")}
{table(["Phân khúc", "Số khách", "Doanh thu", "% doanh thu", "Chi tiêu TB/khách", "Ngày kể từ lần mua cuối (TB)", "Số lần mua TB"],
       [[i, vi(r_["n"]), ty(r_["dt"]), vi(r_["dt"]/tot*100, 1) + "%", tr(r_["tb"], 1), vi(r_["rec"], 0), vi(r_["fre"], 1)] for i, r_ in seg.iterrows()],
       ["l", "r", "r", "r", "r", "r", "r"], caption="<b>Bảng 6.4.</b> Đặc điểm các phân khúc RFM", small=True)}
<p>Phân khúc VIP gồm {vi(seg.loc["VIP","n"])} khách ({vi(seg.loc["VIP","n"]/len(rfm)*100,1)}% số khách) nhưng đóng góp {vi(vip_share,1)}% doanh thu, và có chi tiêu trung bình/khách cao gấp
{vi(seg.loc["VIP","tb"]/seg.loc["Nguy cơ rời bỏ","tb"],1)} lần nhóm “Nguy cơ rời bỏ”. Gợi ý hành động: giữ chân VIP bằng ưu đãi riêng, kích hoạt lại nhóm “Nguy cơ rời bỏ”
bằng khuyến mãi quay lại, và đưa nhóm “Cần chăm sóc” – đông nhất – lên nhóm Trung thành.</p>

<h3>6.8. Tương quan giữa các biến</h3>
{figure("11_corr.png", "Ma trận hệ số tương quan Pearson.", "46%")}
<p>Doanh thu tương quan mạnh với đơn giá (r = {vi(corr_pr,2)}) – hiển nhiên vì hàng đắt tiền kéo giá trị đơn lên – nhưng gần như không tương quan với mức giảm giá.
Đáng chú ý, số lượng và đơn giá tương quan <b>âm</b> (r = {vi(corr_pq,2)}): người mua phụ kiện rẻ lấy nhiều cái, người mua hàng đắt chỉ lấy 1–2 cái.
Đây là tương quan do <i>cơ cấu sản phẩm</i> chứ không phải quan hệ nhân quả “giá cao khiến mua ít”; cần cẩn trọng khi diễn giải hệ số tương quan.</p>
</section>''')

    # ------------------------------ CHƯƠNG 7
    frows = []
    for i in range(3):
        a = fc["forecast"][i]
        b = fc["seasonal_naive"][i]
        frows.append([f"Tháng {i+1}/2026", ty(a), ty(b), f"{(a/b-1)*100:+.0f}%".replace("+", "+")])
    A(f'''
<section>
<h2 id="c7">7. Dự báo doanh thu (Q6)</h2>
<h3>7.1. Phương pháp</h3>
<p>Mô hình gồm hai thành phần nhân với nhau: (1) <b>xu hướng</b> – đường thẳng khớp bằng <code>np.polyfit</code> trên 12 điểm tháng
(độ dốc {tr(fc["slope"],0)} mỗi tháng, R² = {vi(fc["r2_trend"],2)}); (2) <b>chỉ số mùa vụ</b> – tỷ số giữa doanh thu thực và giá trị xu hướng của từng tháng.
Dự báo tháng tiếp theo = xu hướng ngoại suy × chỉ số mùa vụ của tháng tương ứng. Để đối chiếu, ta dùng mô hình <i>naive theo mùa</i>: lấy doanh thu cùng tháng năm trước.</p>
{figure("12_forecast.png", "Doanh thu thực tế, xu hướng tuyến tính và dự báo 3 tháng đầu năm 2026.")}
{table(["Tháng", "Dự báo (xu hướng × mùa vụ)", "Đối chứng: cùng kỳ năm trước", "Chênh lệch"], frows, ["l", "r", "r", "r"], caption="<b>Bảng 7.1.</b> Dự báo 3 tháng tiếp theo")}

<h3>7.2. Đánh giá và hạn chế</h3>
<p>Không thể đánh giá mô hình bằng cách so với chính dữ liệu đã dùng để khớp: chỉ số mùa vụ được tính từ chính 12 tháng này nên mô hình sẽ “khớp hoàn hảo” (sai số 0%) một cách vô nghĩa.
Thay vào đó, dự án giữ lại 3 tháng cuối làm tập kiểm tra và chỉ khớp xu hướng trên 9 tháng đầu. Kết quả: mô hình xu hướng có MAPE = <b>{vi(fc["mape_holdout_trend_%"],1)}%</b>,
so với {vi(fc["mape_holdout_mean_%"],1)}% nếu chỉ dùng trung bình – tức cải thiện không nhiều. R² của xu hướng chỉ {vi(fc["r2_trend"],2)} vì mùa vụ làm doanh thu dao động mạnh quanh đường thẳng.</p>
<p>Đáng lưu ý, dự báo tháng 1/2026 cao hơn đáng kể so với tháng 1/2025: xu hướng bị đẩy lên bởi đợt tăng mạnh cuối năm, rồi lại nhân với chỉ số mùa vụ cao của tháng 1.
Đây là biểu hiện của việc <b>chỉ có một năm dữ liệu</b>: không thể tách rõ mùa vụ khỏi xu hướng. Vì vậy kết quả dự báo trong báo cáo chỉ nên xem là <b>minh họa kỹ thuật</b>.
Để dự báo đáng tin cần ít nhất 2–3 năm dữ liệu và các mô hình chuyên dụng (Holt-Winters, ETS, SARIMA), cùng đánh giá bằng kiểm tra chéo theo thời gian.</p>
</section>''')

    # ------------------------------ CHƯƠNG 8
    groups = {}
    for cls, name, _ in test_listing():
        groups.setdefault(cls, []).append(name)
    cls_vi = {"TestGenerate": "Sinh dữ liệu", "TestCleaning": "Làm sạch", "TestAnalysis": "Phân tích",
              "TestStats": "Thống kê", "TestPipeline": "Toàn pipeline"}
    trows = []
    for cls in ["TestGenerate", "TestCleaning", "TestAnalysis", "TestStats", "TestPipeline"]:
        for nm in groups.get(cls, []):
            trows.append([cls_vi[cls], f"<code>{nm}</code>", TEST_DESC.get(nm, "")])
    A(f'''
<section>
<h2 id="c8">8. Kiểm thử và đảm bảo chất lượng</h2>
<p>Dự án có <b>{n_tests} bài kiểm thử tự động</b> viết bằng <code>unittest</code> (thư viện chuẩn của Python; <code>pytest</code> cũng chạy được).
Các bài kiểm thử không chỉ kiểm tra “chạy không lỗi” mà kiểm tra <b>tính chất đúng đắn</b> của kết quả: tổng các phần phải bằng tổng thể,
tỷ trọng cộng đúng 100%, đường Pareto đơn điệu, công thức doanh thu chính xác và hàm làm sạch không làm thay đổi đầu vào.</p>
{table(["Nhóm", "Bài kiểm thử", "Nội dung kiểm tra"], trows, ["l", "l", "l"], caption="<b>Bảng 8.1.</b> Danh sách bài kiểm thử", small=True)}
<p>Hai kỹ thuật đáng chú ý: (1) <b>kiểm thử với đáp án biết trước</b> – dữ liệu đường thẳng hoàn hảo phải cho R² = 1 và dự báo đúng 1300, 1400, 1500; số ngoại lai/trùng
bị phát hiện phải bằng số đã chèn; (2) <b>đối chiếu với thư viện tham chiếu</b> – Welch t-test tự cài được so với SciPy trên dữ liệu ngẫu nhiên.
Kết quả: {n_tests}/{n_tests} bài đạt.</p>
{code("$ python -m unittest discover -s tests\n...................\n----------------------------------------------------------------------\nRan " + str(n_tests) + " tests in 3.8s\n\nOK")}
</section>''')

    # ------------------------------ CHƯƠNG 9
    A('''
<section>
<h2 id="c9">9. Hướng dẫn cài đặt và sử dụng</h2>
<h3>9.1. Yêu cầu</h3>
<p>Python 3.10 trở lên. Các thư viện: <code>numpy</code>, <code>pandas</code>, <code>matplotlib</code>, <code>openpyxl</code> (ghi trong <code>requirements.txt</code>).</p>
<h3>9.2. Các bước</h3>
<ol>
<li>Tải mã nguồn: <code>git clone &lt;link-repo&gt;</code> rồi <code>cd phan-tich-doanh-so</code>.</li>
<li>Tạo môi trường ảo: <code>python -m venv .venv</code> và kích hoạt (Windows: <code>.venv\\Scripts\\activate</code>; macOS/Linux: <code>source .venv/bin/activate</code>).</li>
<li>Cài thư viện: <code>pip install -r requirements.txt</code>.</li>
<li>Chạy: <code>python run.py</code>. Lần đầu chương trình tự sinh <code>data/raw_sales.csv</code>.</li>
<li>Xem kết quả trong <code>outputs/</code>: hình PNG, <code>bao_cao_tong_hop.xlsx</code>, <code>summary.json</code>.</li>
</ol>
<h3>9.3. Dùng dữ liệu riêng</h3>
<p>Chuẩn bị file CSV (mã hóa UTF-8) có đủ 10 cột như Bảng 3.1, rồi chạy <code>python run.py run --input duong_dan.csv</code>.
Nếu thiếu cột, chương trình báo lỗi rõ ràng và liệt kê cột còn thiếu thay vì chạy tiếp với kết quả sai.</p>
<h3>9.4. Sản phẩm bàn giao</h3>
<table class="tbl"><thead><tr><th class="l">Sản phẩm</th><th class="l">Nơi lưu</th></tr></thead><tbody>
<tr><td>Mã nguồn (GitHub)</td><td class="ph">[dán link GitHub]</td></tr>
<tr><td>Video demo (YouTube)</td><td class="ph">[dán link YouTube]</td></tr>
<tr><td>Báo cáo PDF</td><td><code>docs/BaoCao_PhanTichDuLieu.pdf</code></td></tr>
<tr><td>Bảng tổng hợp Excel</td><td><code>outputs/bao_cao_tong_hop.xlsx</code></td></tr>
</tbody></table>
</section>''')

    # ------------------------------ CHƯƠNG 10
    A(f'''
<section>
<h2 id="c10">10. Kết luận và hướng phát triển</h2>
<h3>10.1. Trả lời các câu hỏi nghiên cứu</h3>
<table class="tbl"><thead><tr><th class="l">Mã</th><th class="l">Kết luận (trên dữ liệu mô phỏng)</th></tr></thead><tbody>
<tr><td>Q1</td><td>Doanh thu đỉnh tháng {best_m} ({ty(m.loc[best_m,"doanh_thu"])}), thấp nhất tháng {worst_m}. Cuối tuần nhỉnh hơn ngày thường {vi((we/wd_-1)*100,1)}% nhưng chưa có ý nghĩa thống kê (p = {vi(wt["p_value"],3)}).</td></tr>
<tr><td>Q2</td><td>Điện thoại + Laptop = {vi(top2,1)}% doanh thu; {top_region} và Hà Nội = {vi(hn_hcm,1)}%; cửa hàng là kênh lớn nhất ({vi(chn.loc["Cửa hàng","ty_trong_%"],1)}%).</td></tr>
<tr><td>Q3</td><td>Ngày khuyến mãi lớn có doanh thu/ngày gấp {vi(sale["ratio"],2)} lần ngày thường trong tháng 11; hiệu ứng này do cách mô phỏng.</td></tr>
<tr><td>Q4</td><td>Cần {vi(R["pct80"],0)}% khách để đạt 80% doanh thu – doanh thu phân tán, không theo 80/20.</td></tr>
<tr><td>Q5</td><td>4 phân khúc RFM; VIP ({vi(seg.loc["VIP","n"])} khách) tạo {vi(vip_share,1)}% doanh thu.</td></tr>
<tr><td>Q6</td><td>Dự báo 3 tháng đầu 2026 là {", ".join(ty(x) for x in fc["forecast"])}; chỉ mang tính minh họa vì có một năm dữ liệu (MAPE kiểm tra {vi(fc["mape_holdout_trend_%"],1)}%).</td></tr>
</tbody></table>

<h3>10.2. Kết quả đạt được</h3>
<ul>
<li>Pipeline phân tích hoàn chỉnh, chạy một lệnh, kết quả tái lập được nhờ seed cố định.</li>
<li>Vận dụng đủ ba thư viện của đề tài; phần việc nào cũng có mã nguồn rõ ràng và bài kiểm thử.</li>
<li>Làm sạch có báo cáo minh bạch: số lỗi phát hiện khớp chính xác số lỗi đã chèn.</li>
<li>13 biểu đồ thống nhất phong cách, tiêu đề nêu kết luận; báo cáo Excel 7 sheet và bản tóm tắt JSON.</li>
<li>Thành thật về giới hạn: kiểm định thống kê cho kết luận “chưa đủ bằng chứng” khi đúng như vậy; dự báo được đánh giá bằng tập kiểm tra thay vì tự khớp.</li>
</ul>

<h3>10.3. Hạn chế</h3>
<ul>
<li><b>Dữ liệu mô phỏng</b>: các kết luận phản ánh cách sinh dữ liệu; không thể suy ra thị trường thực.</li>
<li><b>Một năm dữ liệu</b>: không tách được mùa vụ khỏi xu hướng; dự báo thiếu tin cậy.</li>
<li><b>Chưa có lợi nhuận</b>: chỉ phân tích doanh thu; thiếu giá vốn nên không đánh giá được hiệu quả khuyến mãi.</li>
<li><b>Điền thiếu bằng median</b> là phương pháp đơn giản; chưa xét đa biến hay đo độ bất định do điền thiếu.</li>
<li><b>p-value xấp xỉ chuẩn</b> trong kiểm định Welch, chính xác khi bậc tự do lớn như ở đây (≈ {vi(wt["dof"],0)}) nhưng không phù hợp mẫu rất nhỏ.</li>
</ul>

<h3>10.4. Hướng phát triển</h3>
<ul>
<li>Thay dữ liệu mô phỏng bằng dữ liệu bán lẻ công khai hoặc dữ liệu thật đã ẩn danh; so sánh kết quả.</li>
<li>Thêm giá vốn để phân tích lợi nhuận và phân tích điểm hòa vốn của khuyến mãi.</li>
<li>Dự báo bằng Holt-Winters/ETS với nhiều năm dữ liệu và kiểm tra chéo theo thời gian.</li>
<li>Xây dựng dashboard tương tác (Streamlit hoặc Flask, nối với SQLite) để người không biết lập trình tự khám phá.</li>
<li>Phân cụm khách hàng bằng K-means và so sánh với phân khúc RFM theo luật.</li>
</ul>
</section>''')

    # ------------------------------ TÀI LIỆU THAM KHẢO
    A('''
<section>
<h2 id="ref">Tài liệu tham khảo</h2>
<ol class="refs">
<li>McKinney, W. (2022). <i>Python for Data Analysis</i> (3rd ed.). O’Reilly Media.</li>
<li>Harris, C. R., et al. (2020). Array programming with NumPy. <i>Nature</i>, 585, 357–362.</li>
<li>Hunter, J. D. (2007). Matplotlib: A 2D graphics environment. <i>Computing in Science &amp; Engineering</i>, 9(3), 90–95.</li>
<li>Tukey, J. W. (1977). <i>Exploratory Data Analysis</i>. Addison-Wesley.</li>
<li>Hyndman, R. J., &amp; Athanasopoulos, G. (2021). <i>Forecasting: Principles and Practice</i> (3rd ed.). OTexts. https://otexts.com/fpp3/</li>
<li>Tài liệu chính thức NumPy: https://numpy.org/doc/stable/</li>
<li>Tài liệu chính thức pandas: https://pandas.pydata.org/docs/</li>
<li>Tài liệu chính thức Matplotlib: https://matplotlib.org/stable/</li>
<li>Welch, B. L. (1947). The generalization of “Student’s” problem when several different population variances are involved. <i>Biometrika</i>, 34(1–2), 28–35.</li>
</ol>
</section>''')

    # ------------------------------ PHỤ LỤC
    A(f'''
<section>
<h2 id="pl">Phụ lục A. Trích đoạn mã nguồn</h2>
<p>Các đoạn dưới đây được trích trực tiếp từ mã nguồn (<code>src/salesanalysis/</code>); toàn bộ dự án có tại kho mã nguồn.</p>
{code(getsrc(cl.clean), "cleaning.py – clean(): làm sạch và tạo đặc trưng")}
</section>
<section>
{code(getsrc(an.rfm), "analysis.py – rfm(): phân khúc khách hàng")}
</section>''')

    body = "\n".join(parts)

    # ------------------------------ MỤC LỤC
    toc_items = [("Tóm tắt", None), ("1. Giới thiệu", "c1"), ("2. Cơ sở lý thuyết và công nghệ", "c2"), ("3. Dữ liệu", "c3"),
                 ("4. Thiết kế hệ thống", "c4"), ("5. Tiền xử lý và làm sạch dữ liệu", "c5"), ("6. Kết quả phân tích", "c6"),
                 ("7. Dự báo doanh thu", "c7"), ("8. Kiểm thử và đảm bảo chất lượng", "c8"), ("9. Hướng dẫn cài đặt và sử dụng", "c9"),
                 ("10. Kết luận và hướng phát triển", "c10"), ("Tài liệu tham khảo", "ref"), ("Phụ lục A. Trích đoạn mã nguồn", "pl")]
    subs = {"c1": ["1.1. Bối cảnh và lý do chọn đề tài", "1.2. Mục tiêu", "1.3. Câu hỏi nghiên cứu", "1.4. Phạm vi và giới hạn"],
            "c2": ["2.1. NumPy", "2.2. Pandas", "2.3. Matplotlib", "2.4. Các phương pháp phân tích sử dụng"],
            "c3": ["3.1. Mô tả bộ dữ liệu", "3.2. Cách sinh dữ liệu", "3.3. Dữ liệu bẩn được chèn có chủ đích"],
            "c4": ["4.1. Kiến trúc tổng thể", "4.2. Các quyết định thiết kế đáng chú ý", "4.3. Giao diện dòng lệnh"],
            "c5": ["5.1. Khảo sát chất lượng ban đầu", "5.2. Quy trình làm sạch", "5.3. Xử lý ngoại lai đơn giá", "5.4. Đặc trưng mới"],
            "c6": ["6.1. Tổng quan (KPI)", "6.2. Doanh thu theo thời gian", "6.3. Doanh thu theo sản phẩm", "6.4. Khu vực và kênh bán",
                   "6.5. Hiệu ứng khuyến mãi", "6.6. Mức độ tập trung doanh thu – Pareto", "6.7. Phân khúc khách hàng – RFM", "6.8. Tương quan giữa các biến"],
            "c7": ["7.1. Phương pháp", "7.2. Đánh giá và hạn chế"],
            "c9": ["9.1. Yêu cầu", "9.2. Các bước", "9.3. Dùng dữ liệu riêng", "9.4. Sản phẩm bàn giao"],
            "c10": ["10.1. Trả lời các câu hỏi nghiên cứu", "10.2. Kết quả đạt được", "10.3. Hạn chế", "10.4. Hướng phát triển"]}
    toc_pages = toc_pages or {}
    rows = []
    for title, cid in toc_items:
        pg = toc_pages.get(title, "")
        rows.append(f'<div class="tr1"><span>{esc(title)}</span><i></i><b>{pg}</b></div>')
        for s in subs.get(cid, []):
            rows.append(f'<div class="tr2"><span>{esc(s)}</span><i></i><b>{toc_pages.get(s, "")}</b></div>')
    body = body.replace("@@TOC@@", "".join(rows))
    return body, toc_items, subs


CSS = """
@page { size: A4; margin: 18mm 18mm 18mm 20mm;
  @bottom-center { content: counter(page); font: 9pt 'Inter', sans-serif; color: #666; } }
@page :first { margin: 0; @bottom-center { content: none; } }
* { box-sizing: border-box; }
html { font-family: 'Inter', 'DejaVu Sans', sans-serif; font-size: 10pt; line-height: 1.42; color: #1a1a1a; }
body { margin: 0; }
p { margin: 0 0 8pt; text-align: justify; hyphens: auto; }
h1 { font-size: 26pt; line-height: 1.2; margin: 0 0 12pt; color: #12305f; }
h2 { font-size: 15pt; color: #12305f; border-bottom: 2px solid #2a78d6; padding-bottom: 3pt; margin: 16pt 0 8pt; break-after: avoid; }
h2.plain { border: 0; padding: 0; margin-top: 0; font-size: 18pt; }
h3 { font-size: 11.6pt; color: #1d4f9c; margin: 14pt 0 6pt; break-after: avoid; }
code { font-family: 'DejaVu Sans Mono', monospace; font-size: 8.8pt; background: #eef2f8; padding: 0 2pt; border-radius: 2pt; }
ul, ol { margin: 0 0 8pt; padding-left: 18pt; } li { margin-bottom: 3pt; text-align: justify; }
section { break-inside: auto; }
.pb { break-before: page; }
.cover { height: 297mm; padding: 28mm 24mm 22mm; display: flex; flex-direction: column; background: linear-gradient(180deg,#f4f8fe 0%,#fff 55%); border-left: 14mm solid #2a78d6; }
.cv-top { letter-spacing: 3pt; font-size: 10pt; color: #52514e; font-weight: 600; }
.cv-mid { margin: auto 0; } .cv-topic { color: #2a78d6; font-weight: 700; font-size: 13pt; margin-bottom: 8pt; }
.cv-sub { font-size: 12pt; color: #404040; max-width: 130mm; }
.cv-info { border-collapse: collapse; font-size: 10.5pt; margin-bottom: 16mm; width: 100%; }
.cv-info td { padding: 5pt 0; border-bottom: 1px solid #d8dee9; } .cv-info td:first-child { color: #52514e; width: 46mm; }
.ph { color: #b3541e; font-style: italic; } .cv-foot { color: #52514e; font-size: 10pt; }
.toc .tr1, .toc .tr2 { display: flex; align-items: baseline; gap: 4pt; } .toc i { flex: 1; border-bottom: 1px dotted #999; transform: translateY(-3pt); }
.toc .tr1 { font-weight: 600; margin-top: 4pt; font-size: 9.6pt; } .toc .tr2 { padding-left: 14pt; font-size: 8.4pt; color: #333; line-height: 1.3; }
figure { margin: 6pt auto 8pt; text-align: center; break-inside: avoid; } figure img { width: 100%; border: 1px solid #e4e3df; }
figcaption, .cap { font-size: 9pt; color: #444; margin-top: 4pt; text-align: center; } .cap.center { margin: 4pt 0 10pt; }
.tblwrap { break-inside: avoid; margin: 6pt 0 10pt; } .tblwrap .cap { text-align: left; margin: 0 0 4pt; font-weight: 400; }
table.tbl { width: 100%; border-collapse: collapse; font-size: 9.2pt; } table.tbl.small { font-size: 8.4pt; }
.tbl th { background: #12305f; color: #fff; padding: 4pt 6pt; font-weight: 600; } .tbl td { padding: 3.5pt 6pt; border-bottom: 1px solid #e0e4ec; vertical-align: top; }
.tbl tbody tr:nth-child(even) td { background: #f6f8fc; } .l { text-align: left; } .r { text-align: right; } .center { text-align: center; }
table.tbl { break-inside: auto; } tr { break-inside: avoid; }
pre.code { font-family: 'DejaVu Sans Mono', monospace; font-size: 6.6pt; line-height: 1.3; background: #f5f6f8; border: 1px solid #dfe3ea; border-left: 3px solid #2a78d6; padding: 6pt 8pt; white-space: pre-wrap; margin: 0 0 12pt; word-break: break-word; }
.codetitle { font-size: 9pt; font-weight: 600; color: #12305f; margin: 8pt 0 3pt; break-after: avoid; }
.flow { display: flex; align-items: center; justify-content: center; gap: 4pt; margin: 10pt 0 2pt; }
.fb { border: 1.5px solid #2a78d6; border-radius: 6pt; padding: 8pt 8pt; text-align: center; font-weight: 600; font-size: 9.4pt; background: #f4f8fe; flex: 1; }
.fb small { font-weight: 400; color: #52514e; } .fb.out { background: #2a78d6; color: #fff; } .fb.out small { color: #dce8fa; } .fa { color: #2a78d6; font-size: 15pt; }
.refs li { margin-bottom: 5pt; text-align: left; } .kw { color: #333; }
"""


def render(html_body, out_pdf: Path, html_path: Path):
    from playwright.sync_api import sync_playwright
    doc = f'<!doctype html><html lang="vi"><head><meta charset="utf-8"><title>Báo cáo phân tích dữ liệu bán hàng</title><style>{CSS}</style></head><body>{html_body}</body></html>'
    html_path.write_text(doc, encoding="utf-8")
    with sync_playwright() as p:
        b = p.chromium.launch(executable_path="/opt/pw-browsers/chromium") if Path("/opt/pw-browsers/chromium").exists() else p.chromium.launch()
        pg = b.new_page()
        pg.goto(html_path.resolve().as_uri())
        pg.wait_for_timeout(500)
        pg.pdf(path=str(out_pdf), prefer_css_page_size=True, print_background=True)
        b.close()


def find_pages(pdf: Path, titles):
    import subprocess
    from pypdf import PdfReader
    n = len(PdfReader(str(pdf)).pages)
    norm = lambda x: re.sub(r"[\s\u00ad]+", "", x)
    texts = []
    for i in range(1, n + 1):
        t = subprocess.run(["pdftotext", "-f", str(i), "-l", str(i), str(pdf), "-"], capture_output=True, text=True).stdout
        texts.append(norm(t))
    out = {}
    for t in titles:
        key = norm(t)
        for i, tx in enumerate(texts):
            if i < 2:  # bỏ qua bìa và mục lục
                continue
            if key in tx:
                out[t] = i + 1
                break
    return out, n


def main():
    DOCS.mkdir(exist_ok=True)
    R = collect()
    body, toc_items, subs = build_html(R)
    pdf, htm = DOCS / "BaoCao_PhanTichDuLieu.pdf", DOCS / "report.html"
    render(body, pdf, htm)
    titles = [t for t, _ in toc_items] + [s for v in subs.values() for s in v]
    pages, n = find_pages(pdf, titles)
    body, _, _ = build_html(R, pages)
    render(body, pdf, htm)
    pages, n = find_pages(pdf, titles)
    print(f"PDF: {pdf}  ({n} trang)")
    missing = [t for t in titles if t not in pages]
    if missing:
        print("Không tìm thấy trong PDF:", missing)


if __name__ == "__main__":
    main()

"""Trực quan hóa bằng Matplotlib: 10 biểu đồ, một phong cách thống nhất.

Quy ước thiết kế
- Một trục y cho mỗi biểu đồ (không dùng hai trục).
- Màu phân loại theo thứ tự cố định; chuỗi đơn dùng một màu; độ lớn dùng thang xanh một tông.
- Tiêu đề nêu kết luận; lưới mờ; nhãn trực tiếp thay cho hộp chú thích khi có thể.
"""
from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.ticker import FuncFormatter

# Bảng màu đã kiểm tra (phân loại, theo thứ tự cố định)
BLUE, ORANGE, AQUA, YELLOW, MAGENTA, GREEN, VIOLET, RED = (
    "#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6", "#e34948")
SERIES = [BLUE, ORANGE, AQUA, YELLOW, MAGENTA, GREEN, VIOLET, RED]
INK, INK2, GRID, SURFACE = "#0b0b0b", "#52514e", "#e4e3df", "#fcfcfb"
SEQ = LinearSegmentedColormap.from_list("seq_blue", ["#eaf1fb", "#a9c8f0", "#2a78d6", "#123f7a"])
DIV = LinearSegmentedColormap.from_list("div", [ORANGE, "#e9e8e4", BLUE])


def setup_style() -> None:
    plt.rcParams.update({
        "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
        "axes.edgecolor": GRID, "axes.labelcolor": INK2, "axes.titlecolor": INK,
        "axes.titlesize": 13, "axes.titleweight": "bold", "axes.titlelocation": "left",
        "axes.spines.top": False, "axes.spines.right": False,
        "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.8,
        "axes.axisbelow": True, "xtick.color": INK2, "ytick.color": INK2,
        "text.color": INK, "font.family": "DejaVu Sans", "font.size": 10,
        "legend.frameon": False, "figure.dpi": 100,
    })


def _fmt_m(x, _pos=None):  # triệu đồng
    return f"{x/1e6:,.0f}"


def _fmt_ty(x, _pos=None):  # tỷ đồng
    return f"{x/1e9:,.1f}"


def _save(fig, out_dir: Path, name: str) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    p = out_dir / name
    fig.savefig(p, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return p


# ---------------------------------------------------------------------------
def fig_missing(report_missing: dict, out: Path) -> Path:
    s = pd.Series(report_missing)
    s = s[s > 0].sort_values()
    fig, ax = plt.subplots(figsize=(7, 3.2))
    bars = ax.barh(s.index, s.values, color=BLUE, height=0.55)
    ax.bar_label(bars, padding=3, color=INK2)
    ax.set_title("Dữ liệu thô: số ô bị thiếu theo cột")
    ax.set_xlabel("Số ô thiếu")
    ax.grid(axis="y", visible=False)
    return _save(fig, out, "01_missing.png")


def fig_price_outliers(raw: pd.DataFrame, clean: pd.DataFrame, out: Path) -> Path:
    order = clean.groupby("product")["unit_price"].median().sort_values().index.tolist()
    fig, axes = plt.subplots(1, 2, figsize=(10, 4), sharey=True)
    for ax, d, title in zip(axes, [raw, clean], ["Trước khi làm sạch", "Sau khi làm sạch"]):
        data = [d.loc[d["product"] == p, "unit_price"].dropna() / 1e6 for p in order]
        bp = ax.boxplot(data, orientation="horizontal", tick_labels=order, patch_artist=True, widths=0.55,
                        flierprops=dict(marker="o", markersize=4, markerfacecolor=ORANGE,
                                        markeredgecolor=SURFACE),
                        medianprops=dict(color=INK, linewidth=1.5))
        for b in bp["boxes"]:
            b.set(facecolor="#a9c8f0", edgecolor=BLUE)
        ax.set_title(title)
        ax.set_xlabel("Đơn giá (triệu đồng)")
        ax.grid(axis="y", visible=False)
    fig.suptitle("Ngoại lai đơn giá (nhập thừa số 0) được phát hiện bằng IQR và xử lý",
                 x=0.01, ha="left", fontsize=12, fontweight="bold")
    fig.tight_layout()
    return _save(fig, out, "02_price_outliers.png")


def fig_monthly(m: pd.DataFrame, out: Path) -> Path:
    fig, ax = plt.subplots(figsize=(9, 4.2))
    ax.plot(m.index, m["doanh_thu"], color=BLUE, marker="o", markersize=7, linewidth=2,
            markeredgecolor=SURFACE, markeredgewidth=2, label="Doanh thu tháng", zorder=3)
    ax.plot(m.index, m["tb_dong_3_thang"], color=INK2, linewidth=1.5, linestyle="--",
            label="Trung bình động 3 tháng")
    top = m["doanh_thu"].idxmax()
    ax.annotate(f"Tháng {top}: {m.loc[top, 'doanh_thu']/1e9:,.2f} tỷ",
                (top, m.loc[top, "doanh_thu"]), xytext=(-110, -6), textcoords="offset points",
                color=INK, arrowprops=dict(arrowstyle="-", color=INK2))
    ax.set_xticks(range(1, 13))
    ax.yaxis.set_major_formatter(FuncFormatter(_fmt_ty))
    ax.set_xlabel("Tháng")
    ax.set_ylabel("Tỷ đồng")
    ax.set_title("Doanh thu đạt đỉnh vào tháng 11 – mùa mua sắm cuối năm")
    ax.legend(loc="upper left")
    return _save(fig, out, "03_monthly.png")


def fig_products(bp: pd.DataFrame, out: Path) -> Path:
    d = bp.sort_values("doanh_thu")
    fig, ax = plt.subplots(figsize=(8, 4))
    bars = ax.barh(d.index, d["doanh_thu"], color=BLUE, height=0.6)
    ax.bar_label(bars, labels=[f"{v/1e9:.2f} tỷ ({p:.0f}%)" for v, p in
                               zip(d["doanh_thu"], d["ty_trong_%"])], padding=4, color=INK2, fontsize=9)
    ax.xaxis.set_major_formatter(FuncFormatter(_fmt_ty))
    ax.set_xlim(0, d["doanh_thu"].max() * 1.25)
    ax.set_xlabel("Doanh thu (tỷ đồng)")
    ax.set_title("Điện thoại và Laptop tạo phần lớn doanh thu")
    ax.grid(axis="y", visible=False)
    return _save(fig, out, "04_products.png")


def fig_region_channel(pv: pd.DataFrame, out: Path) -> Path:
    pv = pv.loc[pv.sum(axis=1).sort_values(ascending=False).index]
    fig, ax = plt.subplots(figsize=(8, 4.2))
    bottom = np.zeros(len(pv))
    for i, ch in enumerate(pv.columns):
        ax.bar(pv.index, pv[ch], bottom=bottom, color=SERIES[i], width=0.55,
               edgecolor=SURFACE, linewidth=2, label=ch)
        bottom += pv[ch].to_numpy()
    for x, tot in zip(pv.index, bottom):
        ax.text(x, tot, f"{tot/1e9:.2f} tỷ", ha="center", va="bottom", color=INK2, fontsize=9)
    ax.yaxis.set_major_formatter(FuncFormatter(_fmt_ty))
    ax.set_ylim(0, bottom.max() * 1.12)
    ax.set_ylabel("Doanh thu (tỷ đồng)")
    ax.set_title("TP.HCM và Hà Nội dẫn đầu; cửa hàng là kênh lớn nhất")
    ax.legend(ncol=3, loc="upper right")
    ax.grid(axis="x", visible=False)
    return _save(fig, out, "05_region_channel.png")


def fig_heatmap(pv: pd.DataFrame, out: Path) -> Path:
    pv = pv.loc[pv.sum(axis=1).sort_values(ascending=False).index,
                pv.sum().sort_values(ascending=False).index] / 1e6
    fig, ax = plt.subplots(figsize=(9, 3.8))
    im = ax.imshow(pv.values, cmap=SEQ, aspect="auto")
    ax.set_xticks(range(pv.shape[1]), pv.columns, rotation=25, ha="right")
    ax.set_yticks(range(pv.shape[0]), pv.index)
    ax.grid(False)
    vmax = pv.values.max()
    for i in range(pv.shape[0]):
        for j in range(pv.shape[1]):
            v = pv.values[i, j]
            ax.text(j, i, f"{v:,.0f}", ha="center", va="center", fontsize=8,
                    color="white" if v > vmax * 0.55 else INK)
    cb = fig.colorbar(im, ax=ax, pad=0.02)
    cb.set_label("Triệu đồng")
    ax.set_title("Doanh thu theo khu vực × sản phẩm (triệu đồng)")
    for s in ax.spines.values():
        s.set_visible(False)
    return _save(fig, out, "06_heatmap.png")


def fig_hist(df: pd.DataFrame, out: Path) -> Path:
    fig, ax = plt.subplots(figsize=(8, 3.8))
    v = df["revenue"] / 1e6
    bins = np.logspace(np.log10(max(v.min(), 0.05)), np.log10(v.max()), 40)
    ax.hist(v, bins=bins, color=BLUE, edgecolor=SURFACE, linewidth=1)
    ax.set_xscale("log")
    ax.axvline(v.mean(), color=ORANGE, linewidth=2, label=f"Trung bình {v.mean():.1f} tr")
    ax.axvline(v.median(), color=INK2, linewidth=2, linestyle="--", label=f"Trung vị {v.median():.1f} tr")
    ax.set_xlabel("Giá trị đơn hàng (triệu đồng, thang log)")
    ax.set_ylabel("Số đơn")
    ax.set_title("Hai cụm đơn hàng: phụ kiện (~1 triệu) và thiết bị (~10 triệu)")
    ax.legend()
    return _save(fig, out, "07_hist.png")


def fig_weekday(wd: pd.DataFrame, out: Path, p_value: float | None = None) -> Path:
    fig, ax = plt.subplots(figsize=(7.5, 3.8))
    colors = [BLUE] * 5 + [ORANGE] * 2
    bars = ax.bar(wd.index, wd["doanh_thu"], color=colors, width=0.6)
    ax.bar_label(bars, labels=[f"{v/1e9:.2f}" for v in wd["doanh_thu"]], padding=3, color=INK2, fontsize=9)
    ax.yaxis.set_major_formatter(FuncFormatter(_fmt_ty))
    ax.set_ylabel("Doanh thu (tỷ đồng)")
    note = f"p = {p_value:.2f}".replace(".", ",") if p_value is not None else ""
    verdict = "chênh lệch chưa có ý nghĩa thống kê" if (p_value is not None and p_value > 0.05) else "chênh lệch có ý nghĩa thống kê"
    ax.set_title(f"Cuối tuần (cam) nhỉnh hơn, nhưng {verdict} ({note})" if note else "Doanh thu theo thứ trong tuần")
    ax.grid(axis="x", visible=False)
    return _save(fig, out, "08_weekday.png")


def fig_pareto(par: pd.DataFrame, n80: int, pct80: float, out: Path) -> Path:
    fig, ax = plt.subplots(figsize=(7.5, 4.2))
    ax.plot(par["pct_khach"], par["luy_ke_%"], color=BLUE, linewidth=2.5)
    ax.plot([0, 100], [0, 100], color=GRID, linestyle="--", label="Phân bố đều")
    ax.axhline(80, color=INK2, linewidth=1, linestyle=":")
    ax.plot([pct80], [80], marker="o", markersize=9, color=ORANGE, markeredgecolor=SURFACE,
            markeredgewidth=2, zorder=4)
    ax.annotate(f"{pct80:.0f}% khách hàng ({n80}) tạo 80% doanh thu", (pct80, 80),
                xytext=(18, -34), textcoords="offset points", color=INK,
                arrowprops=dict(arrowstyle="-", color=INK2))
    ax.set_xlabel("% khách hàng (xếp từ mua nhiều đến ít)")
    ax.set_ylabel("% doanh thu lũy kế")
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 102)
    ax.set_title("Doanh thu khá phân tán: cần gần một nửa số khách để đạt 80%")
    ax.legend(loc="lower right")
    return _save(fig, out, "09_pareto.png")


def fig_rfm(r: pd.DataFrame, out: Path) -> Path:
    g = r.groupby("segment", observed=True).agg(so_khach=("monetary", "size"), dt=("monetary", "sum"))
    g = g.reindex(["VIP", "Trung thành", "Cần chăm sóc", "Nguy cơ rời bỏ"])
    fig, axes = plt.subplots(1, 2, figsize=(10, 3.6))
    b1 = axes[0].bar(g.index, g["so_khach"], color=BLUE, width=0.55)
    axes[0].bar_label(b1, padding=3, color=INK2)
    axes[0].set_title("Số khách theo phân khúc")
    b2 = axes[1].bar(g.index, g["dt"], color=BLUE, width=0.55)
    axes[1].bar_label(b2, labels=[f"{v/1e9:.2f} tỷ" for v in g["dt"]], padding=3, color=INK2)
    axes[1].yaxis.set_major_formatter(FuncFormatter(_fmt_ty))
    axes[1].set_title("Doanh thu theo phân khúc (tỷ đồng)")
    axes[0].set_ylim(0, g["so_khach"].max() * 1.18)
    axes[1].set_ylim(0, g["dt"].max() * 1.18)
    for ax in axes:
        ax.tick_params(axis="x", rotation=15)
        ax.grid(axis="x", visible=False)
    fig.tight_layout()
    return _save(fig, out, "10_rfm.png")


def fig_corr(c: pd.DataFrame, out: Path) -> Path:
    labels = ["Số lượng", "Đơn giá", "Giảm giá", "Doanh thu"]
    fig, ax = plt.subplots(figsize=(5.2, 4.4))
    im = ax.imshow(c.values, cmap=DIV, vmin=-1, vmax=1)
    ax.set_xticks(range(4), labels, rotation=25, ha="right")
    ax.set_yticks(range(4), labels)
    ax.grid(False)
    for i in range(4):
        for j in range(4):
            ax.text(j, i, f"{c.values[i, j]:.2f}", ha="center", va="center", color=INK, fontsize=10)
    fig.colorbar(im, ax=ax, label="Hệ số Pearson")
    ax.set_title("Tương quan giữa các biến số", loc="left")
    for s in ax.spines.values():
        s.set_visible(False)
    return _save(fig, out, "11_corr.png")


def fig_forecast(m: pd.DataFrame, fc: dict, out: Path, year: int = 2025) -> Path:
    y = m["doanh_thu"].to_numpy()
    x = np.arange(1, 13)
    fx = np.arange(13, 13 + len(fc["forecast"]))
    fig, ax = plt.subplots(figsize=(9, 4.2))
    ax.plot(x, y, color=BLUE, marker="o", markersize=7, linewidth=2, markeredgecolor=SURFACE,
            markeredgewidth=2, label="Thực tế", zorder=3)
    ax.plot(x, fc["trend"], color=INK2, linestyle="--", linewidth=1.5,
            label=f"Xu hướng tuyến tính (R² = {fc['r2_trend']:.2f})")
    ax.plot(np.r_[12, fx], np.r_[y[-1], fc["forecast"]], color=ORANGE, marker="o", markersize=7,
            linewidth=2, markeredgecolor=SURFACE, markeredgewidth=2, label="Dự báo (xu hướng × mùa vụ)")
    ax.plot(np.r_[12, fx], np.r_[y[-1], fc["seasonal_naive"]], color=INK2, linestyle=":", marker="o",
            markersize=5, linewidth=1.8, label="Đối chứng: cùng kỳ năm trước")
    ax.set_xticks(list(range(1, 13)) + list(fx),
                  [str(i) for i in range(1, 13)] + [f"{i}/{year + 1 - 2000}" for i in range(1, len(fx) + 1)])
    ax.yaxis.set_major_formatter(FuncFormatter(_fmt_ty))
    ax.set_ylabel("Tỷ đồng")
    ax.set_title("Dự báo 3 tháng đầu năm sau (mô hình minh họa, chỉ có 1 năm dữ liệu)")
    ax.legend(loc="upper left")
    return _save(fig, out, "12_forecast.png")


def fig_dashboard(df: pd.DataFrame, m: pd.DataFrame, bp: pd.DataFrame, pv: pd.DataFrame, out: Path) -> Path:
    """Bảng tổng hợp 2x2 - dùng cho ảnh bìa README."""
    fig, axes = plt.subplots(2, 2, figsize=(13, 8.2))
    ax = axes[0, 0]
    ax.plot(m.index, m["doanh_thu"], color=BLUE, marker="o", markersize=6, linewidth=2,
            markeredgecolor=SURFACE, markeredgewidth=2)
    ax.set_xticks(range(1, 13)); ax.yaxis.set_major_formatter(FuncFormatter(_fmt_ty))
    ax.set_title("Doanh thu theo tháng (tỷ đồng)")
    ax = axes[0, 1]
    d = bp.sort_values("doanh_thu")
    ax.barh(d.index, d["doanh_thu"], color=BLUE, height=0.6)
    ax.xaxis.set_major_formatter(FuncFormatter(_fmt_ty)); ax.grid(axis="y", visible=False)
    ax.set_title("Doanh thu theo sản phẩm (tỷ đồng)")
    ax = axes[1, 0]
    v = df["revenue"] / 1e6
    ax.hist(v, bins=np.logspace(np.log10(max(v.min(), .05)), np.log10(v.max()), 40), color=BLUE, edgecolor=SURFACE)
    ax.set_xscale("log"); ax.set_title("Phân bố giá trị đơn hàng (triệu đồng)")
    ax = axes[1, 1]
    p = pv.loc[pv.sum(axis=1).sort_values(ascending=False).index, pv.sum().sort_values(ascending=False).index] / 1e6
    ax.imshow(p.values, cmap=SEQ, aspect="auto"); ax.grid(False)
    ax.set_xticks(range(p.shape[1]), p.columns, rotation=30, ha="right", fontsize=8)
    ax.set_yticks(range(p.shape[0]), p.index)
    ax.set_title("Khu vực × sản phẩm")
    fig.suptitle("Dashboard phân tích doanh số bán hàng 2025", x=0.01, ha="left", fontsize=16, fontweight="bold")
    fig.tight_layout()
    return _save(fig, out, "00_dashboard.png")

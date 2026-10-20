"""Phân tích: KPI, theo thời gian, theo nhóm, Pareto, RFM, tương quan, dự báo."""
from __future__ import annotations

import numpy as np
import pandas as pd


# ----------------------------------------------------------------------------
# KPI tổng quan
# ----------------------------------------------------------------------------
def kpis(df: pd.DataFrame) -> dict:
    return {
        "tong_don": int(df["order_id"].nunique()),
        "tong_doanh_thu": float(df["revenue"].sum()),
        "gia_tri_don_tb": float(df["revenue"].mean()),
        "gia_tri_don_median": float(df["revenue"].median()),
        "so_khach_hang": int(df["customer_id"].nunique()),
        "tong_so_luong": int(df["quantity"].sum()),
        "ty_le_giam_gia_tb_%": float(df["discount"].mean() * 100),
    }


# ----------------------------------------------------------------------------
# Theo thời gian
# ----------------------------------------------------------------------------
def monthly(df: pd.DataFrame) -> pd.DataFrame:
    m = df.groupby("month").agg(doanh_thu=("revenue", "sum"), so_don=("order_id", "count"),
                                 so_luong=("quantity", "sum"))
    m["tang_truong_mom_%"] = m["doanh_thu"].pct_change() * 100
    m["tb_dong_3_thang"] = m["doanh_thu"].rolling(3).mean()
    return m


def weekday_profile(df: pd.DataFrame) -> pd.DataFrame:
    names = ["Thứ 2", "Thứ 3", "Thứ 4", "Thứ 5", "Thứ 6", "Thứ 7", "CN"]
    g = df.groupby("weekday").agg(doanh_thu=("revenue", "sum"), so_don=("order_id", "count"))
    g.index = [names[i] for i in g.index]
    return g


def daily_revenue(df: pd.DataFrame) -> pd.Series:
    s = df.groupby(df["order_date"].dt.normalize())["revenue"].sum()
    full = pd.date_range(s.index.min(), s.index.max(), freq="D")
    return s.reindex(full, fill_value=0.0)


# ----------------------------------------------------------------------------
# Theo nhóm
# ----------------------------------------------------------------------------
def by_product(df: pd.DataFrame) -> pd.DataFrame:
    g = df.groupby("product").agg(doanh_thu=("revenue", "sum"), so_luong=("quantity", "sum"),
                                   so_don=("order_id", "count"), gia_tb=("unit_price", "mean"))
    g["ty_trong_%"] = g["doanh_thu"] / g["doanh_thu"].sum() * 100
    return g.sort_values("doanh_thu", ascending=False)


def by_group(df: pd.DataFrame, col: str) -> pd.DataFrame:
    g = df.groupby(col).agg(doanh_thu=("revenue", "sum"), so_don=("order_id", "count"),
                             gia_tri_don_tb=("revenue", "mean"))
    g["ty_trong_%"] = g["doanh_thu"] / g["doanh_thu"].sum() * 100
    return g.sort_values("doanh_thu", ascending=False)


def region_product_pivot(df: pd.DataFrame) -> pd.DataFrame:
    return df.pivot_table(index="region", columns="product", values="revenue",
                          aggfunc="sum", fill_value=0)


def channel_by_region(df: pd.DataFrame) -> pd.DataFrame:
    return df.pivot_table(index="region", columns="channel", values="revenue",
                          aggfunc="sum", fill_value=0)


# ----------------------------------------------------------------------------
# Pareto 80/20
# ----------------------------------------------------------------------------
def pareto_customers(df: pd.DataFrame) -> pd.DataFrame:
    """Tỷ lệ đóng góp lũy kế của khách hàng (xếp từ cao xuống thấp)."""
    c = df.groupby("customer_id")["revenue"].sum().sort_values(ascending=False)
    out = pd.DataFrame({"doanh_thu": c})
    out["luy_ke_%"] = out["doanh_thu"].cumsum() / out["doanh_thu"].sum() * 100
    out["pct_khach"] = np.arange(1, len(out) + 1) / len(out) * 100
    return out


def customers_for_share(pareto: pd.DataFrame, share: float = 80.0) -> tuple[int, float]:
    """Số khách (và % khách) tạo ra `share`% doanh thu."""
    n = int((pareto["luy_ke_%"] < share).sum() + 1)
    return n, n / len(pareto) * 100


# ----------------------------------------------------------------------------
# RFM
# ----------------------------------------------------------------------------
def rfm(df: pd.DataFrame) -> pd.DataFrame:
    """Recency - Frequency - Monetary và phân khúc khách hàng."""
    now = df["order_date"].max() + pd.Timedelta(days=1)
    r = df.groupby("customer_id").agg(
        recency=("order_date", lambda s: (now - s.max()).days),
        frequency=("order_id", "count"),
        monetary=("revenue", "sum"),
    )
    # qcut theo thứ hạng; rank(method="first") tránh lỗi trùng biên
    r["R"] = pd.qcut(r["recency"].rank(method="first"), 4, labels=[4, 3, 2, 1]).astype(int)
    r["F"] = pd.qcut(r["frequency"].rank(method="first"), 4, labels=[1, 2, 3, 4]).astype(int)
    r["M"] = pd.qcut(r["monetary"].rank(method="first"), 4, labels=[1, 2, 3, 4]).astype(int)
    r["score"] = r["R"] + r["F"] + r["M"]
    r["segment"] = pd.cut(r["score"], bins=[0, 5, 8, 10, 12],
                          labels=["Nguy cơ rời bỏ", "Cần chăm sóc", "Trung thành", "VIP"])
    return r


# ----------------------------------------------------------------------------
# Tương quan & kiểm định đơn giản
# ----------------------------------------------------------------------------
def correlation(df: pd.DataFrame) -> pd.DataFrame:
    cols = ["quantity", "unit_price", "discount", "revenue"]
    return df[cols].corr()


def discount_effect(df: pd.DataFrame) -> pd.DataFrame:
    """So sánh số lượng trung bình giữa các mức giảm giá (chỉ nhóm hàng phụ kiện)."""
    acc = df[df["category"] == "Phụ kiện"]
    return acc.groupby("discount").agg(so_don=("order_id", "count"),
                                        so_luong_tb=("quantity", "mean"),
                                        doanh_thu_tb=("revenue", "mean"))


# ----------------------------------------------------------------------------
# Dự báo: hồi quy tuyến tính + chỉ số mùa vụ (thuần NumPy)
# ----------------------------------------------------------------------------
def forecast_next_months(monthly_rev: pd.Series, horizon: int = 3) -> dict:
    """Dự báo đơn giản bằng np.polyfit (xu hướng) × chỉ số mùa vụ.

    Với dữ liệu chỉ 12 tháng, đây là mô hình minh họa, không phải mô hình sản xuất.
    """
    y = monthly_rev.to_numpy(dtype=float)
    x = np.arange(len(y))
    slope, intercept = np.polyfit(x, y, 1)
    trend = slope * x + intercept
    seasonal_idx = y / trend                       # chỉ số mùa vụ từng tháng
    ss_res = np.sum((y - trend) ** 2)
    ss_tot = np.sum((y - y.mean()) ** 2)
    r2 = 1 - ss_res / ss_tot

    fx = np.arange(len(y), len(y) + horizon)
    ftrend = slope * fx + intercept
    fseason = np.array([seasonal_idx[i % 12] for i in range(len(y), len(y) + horizon)])
    pred = ftrend * fseason

    # Đánh giá trung thực: giữ lại 3 tháng cuối làm tập kiểm tra, chỉ khớp xu hướng trên các tháng còn lại.
    # (Không đánh giá "tự khớp" vì chỉ số mùa vụ rút từ chính dữ liệu nên sai số luôn bằng 0.)
    k = 3
    s2, i2 = np.polyfit(x[:-k], y[:-k], 1)
    hold_pred = s2 * x[-k:] + i2
    mape_holdout = float(np.mean(np.abs((y[-k:] - hold_pred) / y[-k:])) * 100)
    naive_pred = np.full(k, y[:-k].mean())
    mape_naive = float(np.mean(np.abs((y[-k:] - naive_pred) / y[-k:])) * 100)
    return {"slope": float(slope), "intercept": float(intercept), "r2_trend": float(r2),
            "trend": trend, "seasonal_index": seasonal_idx, "forecast": pred,
            "forecast_trend_only": ftrend, "seasonal_naive": y[:horizon].copy(), "mape_holdout_trend_%": mape_holdout,
            "mape_holdout_mean_%": mape_naive}


# ----------------------------------------------------------------------------
# Kiểm định thống kê (thuần NumPy)
# ----------------------------------------------------------------------------
def welch_t_test(a, b) -> dict:
    """Kiểm định Welch (hai mẫu, phương sai khác nhau), hai phía.

    p-value tính bằng xấp xỉ phân phối chuẩn - đủ chính xác khi bậc tự do lớn
    (> ~100) như dữ liệu theo ngày ở đây.
    """
    import math
    a, b = np.asarray(a, float), np.asarray(b, float)
    va, vb = a.var(ddof=1) / len(a), b.var(ddof=1) / len(b)
    t = (a.mean() - b.mean()) / math.sqrt(va + vb)
    dof = (va + vb) ** 2 / (va ** 2 / (len(a) - 1) + vb ** 2 / (len(b) - 1))
    p = math.erfc(abs(t) / math.sqrt(2))
    return {"t": float(t), "dof": float(dof), "p_value": float(p),
            "mean_a": float(a.mean()), "mean_b": float(b.mean())}


def weekend_vs_weekday(df: pd.DataFrame) -> dict:
    """So sánh doanh thu TRUNG BÌNH MỖI NGÀY giữa cuối tuần và ngày thường."""
    d = daily_revenue(df)
    is_we = d.index.dayofweek >= 5
    return welch_t_test(d[is_we], d[~is_we])


def sale_days_effect(df: pd.DataFrame) -> dict:
    """Doanh thu/ngày trong các ngày khuyến mãi lớn (11/11, 24-28/11) so với các ngày còn lại của tháng 11."""
    d = daily_revenue(df)
    nov = d[d.index.month == 11]
    mask = ((nov.index.day == 11) | ((nov.index.day >= 24) & (nov.index.day <= 28)))
    return {"sale_mean": float(nov[mask].mean()), "other_mean": float(nov[~mask].mean()),
            "ratio": float(nov[mask].mean() / nov[~mask].mean()), "n_sale_days": int(mask.sum())}

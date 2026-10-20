"""Sinh dữ liệu bán hàng mô phỏng (có mùa vụ, xu hướng, nhiễu và dữ liệu bẩn).

Dữ liệu là MÔ PHỎNG, dùng cho mục đích học tập. Nhờ seed cố định, mọi lần chạy
đều cho cùng kết quả nên báo cáo có thể tái lập.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

# (tên, danh mục, giá niêm yết VND, trọng số bán ra)
CATALOG = [
    ("Laptop", "Máy tính", 16_000_000, 0.08),
    ("Điện thoại", "Điện thoại", 10_000_000, 0.16),
    ("Máy tính bảng", "Máy tính", 8_000_000, 0.06),
    ("Tai nghe", "Phụ kiện", 750_000, 0.20),
    ("Chuột", "Phụ kiện", 280_000, 0.15),
    ("Bàn phím", "Phụ kiện", 650_000, 0.12),
    ("Sạc dự phòng", "Phụ kiện", 420_000, 0.13),
    ("Màn hình", "Máy tính", 4_500_000, 0.10),
]
REGIONS = ["Hà Nội", "Đà Nẵng", "TP.HCM", "Cần Thơ"]
REGION_P = [0.34, 0.16, 0.38, 0.12]
CHANNELS = ["Cửa hàng", "Website", "Sàn TMĐ"]
CHANNEL_P = [0.45, 0.30, 0.25]

# Hệ số mùa vụ theo tháng: Tết (1-2), khai giảng (8-9), mua sắm cuối năm (11-12)
SEASONALITY = {1: 1.25, 2: 0.80, 3: 0.90, 4: 0.95, 5: 1.00, 6: 0.95,
               7: 0.90, 8: 1.15, 9: 1.20, 10: 1.00, 11: 1.45, 12: 1.35}


def generate_sales(n_orders: int = 4000, year: int = 2025, seed: int = 42,
                   dirty: bool = True) -> pd.DataFrame:
    """Tạo bảng đơn hàng.

    Parameters
    ----------
    n_orders : số dòng cơ bản (chưa tính dòng trùng cố ý thêm vào).
    dirty    : nếu True, cố ý chèn giá trị thiếu, dòng trùng và ngoại lai
               để thực hành làm sạch dữ liệu.
    """
    rng = np.random.default_rng(seed)

    # --- Ngày đặt hàng: phân bố theo mùa vụ + tăng trưởng nhẹ trong năm ---
    days = pd.date_range(f"{year}-01-01", f"{year}-12-31", freq="D")
    month_w = np.array([SEASONALITY[d.month] for d in days])
    growth = np.linspace(1.0, 1.15, len(days))          # xu hướng tăng ~15%/năm
    weekend = np.where(days.dayofweek >= 5, 1.2, 1.0)   # cuối tuần đông hơn
    # Ngày khuyến mãi lớn (11/11, 24-28/11) có lượng đơn tăng mạnh
    sale = ((days.month == 11) & (days.day == 11)) | ((days.month == 11) & (days.day >= 24) & (days.day <= 28))
    w = month_w * growth * weekend * np.where(sale, 2.5, 1.0)
    order_date = rng.choice(days, size=n_orders, p=w / w.sum())

    names = [c[0] for c in CATALOG]
    cats = {c[0]: c[1] for c in CATALOG}
    price = {c[0]: c[2] for c in CATALOG}
    product = rng.choice(names, n_orders, p=np.array([c[3] for c in CATALOG]))

    # Số lượng: phụ kiện mua nhiều hơn, hàng đắt tiền thường mua 1
    expensive = np.isin(product, ["Laptop", "Điện thoại", "Máy tính bảng", "Màn hình"])
    quantity = np.where(expensive, rng.choice([1, 1, 1, 2], n_orders),
                        rng.integers(1, 6, n_orders))

    unit_price = np.array([price[p] for p in product]) * rng.normal(1.0, 0.05, n_orders)
    # Giảm giá lớn vào đợt 11/11 và Black Friday
    dt = pd.DatetimeIndex(order_date)
    sale_day = ((dt.month == 11) & (dt.day == 11)) | ((dt.month == 11) & (dt.day >= 24) & (dt.day <= 28))
    discount = np.where(sale_day, rng.choice([0.15, 0.20, 0.30], n_orders),
                        rng.choice([0.0, 0.0, 0.0, 0.05, 0.10], n_orders))

    df = pd.DataFrame({
        "order_id": [f"DH{100000 + i}" for i in range(n_orders)],
        "order_date": dt,
        "customer_id": [f"KH{c:04d}" for c in rng.integers(1, 1201, n_orders)],
        "product": product,
        "category": [cats[p] for p in product],
        "region": rng.choice(REGIONS, n_orders, p=REGION_P),
        "channel": rng.choice(CHANNELS, n_orders, p=CHANNEL_P),
        "quantity": quantity.astype(float),
        "unit_price": unit_price.round(-3),
        "discount": discount,
    })
    df = df.sort_values("order_date").reset_index(drop=True)

    if dirty:
        df = _inject_dirt(df, rng)
    return df


def _inject_dirt(df: pd.DataFrame, rng: np.random.Generator) -> pd.DataFrame:
    """Chèn dữ liệu bẩn: thiếu, ngoại lai, sai định dạng, trùng lặp."""
    df = df.copy()
    n = len(df)
    df.loc[rng.choice(n, 40, replace=False), "quantity"] = np.nan
    df.loc[rng.choice(n, 25, replace=False), "region"] = None
    df.loc[rng.choice(n, 15, replace=False), "unit_price"] = np.nan
    # Ngoại lai: nhập thừa số 0 (gấp 10 lần) hoặc số lượng bất thường
    df.loc[rng.choice(n, 6, replace=False), "unit_price"] *= 10
    df.loc[rng.choice(n, 5, replace=False), "quantity"] = 99
    # Nhập sai chữ hoa/thừa khoảng trắng
    idx = rng.choice(n, 30, replace=False)
    df.loc[idx, "channel"] = df.loc[idx, "channel"].str.upper() + " "
    # Dòng trùng lặp hoàn toàn
    dup = df.sample(20, random_state=1)
    return pd.concat([df, dup], ignore_index=True)

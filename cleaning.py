"""Làm sạch dữ liệu: kiểm tra chất lượng, xử lý thiếu, trùng, ngoại lai, chuẩn hóa."""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

REQUIRED_COLUMNS = ["order_id", "order_date", "customer_id", "product", "category",
                    "region", "channel", "quantity", "unit_price", "discount"]

CHANNEL_MAP = {"CỬA HÀNG": "Cửa hàng", "WEBSITE": "Website", "SÀN TMĐ": "Sàn TMĐ"}


@dataclass
class CleaningReport:
    """Ghi lại những gì đã làm để báo cáo minh bạch."""
    rows_in: int = 0
    rows_out: int = 0
    duplicates_removed: int = 0
    missing_before: dict = field(default_factory=dict)
    quantity_filled: int = 0
    price_filled: int = 0
    region_filled: int = 0
    outliers_price: int = 0
    outliers_quantity: int = 0
    channel_fixed: int = 0

    def as_dict(self) -> dict:
        return self.__dict__.copy()


def load_csv(path) -> pd.DataFrame:
    """Đọc CSV và kiểm tra đủ cột bắt buộc."""
    df = pd.read_csv(path, encoding="utf-8-sig")
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"File thiếu cột bắt buộc: {missing}")
    return df


def quality_overview(df: pd.DataFrame) -> pd.DataFrame:
    """Bảng tổng quan chất lượng: kiểu dữ liệu, số ô thiếu, tỷ lệ thiếu, số giá trị khác nhau."""
    return pd.DataFrame({
        "dtype": df.dtypes.astype(str),
        "thieu": df.isna().sum(),
        "ty_le_thieu_%": (df.isna().mean() * 100).round(2),
        "so_gia_tri_khac_nhau": df.nunique(),
    })


def iqr_bounds(s: pd.Series, k: float = 1.5) -> tuple[float, float]:
    """Cận dưới/trên theo quy tắc IQR (Tukey)."""
    q1, q3 = s.quantile([0.25, 0.75])
    iqr = q3 - q1
    return q1 - k * iqr, q3 + k * iqr


def clean(df: pd.DataFrame) -> tuple[pd.DataFrame, CleaningReport]:
    """Làm sạch toàn bộ và trả về (DataFrame sạch, báo cáo)."""
    rep = CleaningReport(rows_in=len(df), missing_before=df.isna().sum().to_dict())
    df = df.copy()

    # 1) Kiểu dữ liệu
    df["order_date"] = pd.to_datetime(df["order_date"], errors="coerce")
    df = df.dropna(subset=["order_date", "order_id", "product"])

    # 2) Chuẩn hóa chuỗi (khoảng trắng, chữ hoa)
    for col in ["product", "category", "region", "channel", "customer_id"]:
        df[col] = df[col].astype("string").str.strip()
    fixed = df["channel"].str.upper().isin(CHANNEL_MAP) & ~df["channel"].isin(CHANNEL_MAP.values())
    rep.channel_fixed = int(fixed.sum())
    df["channel"] = df["channel"].str.upper().map(CHANNEL_MAP).fillna(df["channel"])

    # 3) Dòng trùng
    before = len(df)
    df = df.drop_duplicates()
    rep.duplicates_removed = before - len(df)

    # 4) Ngoại lai: tính giới hạn IQR theo từng sản phẩm (giá) rồi thay bằng median sản phẩm
    med_price = df.groupby("product")["unit_price"].transform("median")
    lo = df.groupby("product")["unit_price"].transform(lambda s: iqr_bounds(s.dropna(), 3.0)[0])
    hi = df.groupby("product")["unit_price"].transform(lambda s: iqr_bounds(s.dropna(), 3.0)[1])
    bad_price = (df["unit_price"] < lo) | (df["unit_price"] > hi)
    rep.outliers_price = int(bad_price.sum())
    df.loc[bad_price, "unit_price"] = med_price[bad_price]

    bad_qty = df["quantity"] > 20  # ngưỡng nghiệp vụ: một đơn lẻ không quá 20 sản phẩm
    rep.outliers_quantity = int(bad_qty.sum())
    df.loc[bad_qty, "quantity"] = np.nan

    # 5) Điền thiếu: số -> median theo sản phẩm; chuỗi -> "Không rõ"
    rep.price_filled = int(df["unit_price"].isna().sum())
    df["unit_price"] = df["unit_price"].fillna(med_price).fillna(df["unit_price"].median())
    rep.quantity_filled = int(df["quantity"].isna().sum())
    med_qty = df.groupby("product")["quantity"].transform("median")
    df["quantity"] = df["quantity"].fillna(med_qty).round().astype(int)
    rep.region_filled = int(df["region"].isna().sum())
    df["region"] = df["region"].fillna("Không rõ")

    # 6) Đặc trưng mới (feature engineering)
    df["revenue"] = df["quantity"] * df["unit_price"] * (1 - df["discount"])
    df["month"] = df["order_date"].dt.month
    df["quarter"] = df["order_date"].dt.quarter
    df["weekday"] = df["order_date"].dt.dayofweek  # 0 = thứ Hai
    df["is_weekend"] = df["weekday"] >= 5
    df["price_tier"] = np.where(df["unit_price"] >= 3_000_000, "Cao cấp", "Phổ thông")

    df = df.sort_values("order_date").reset_index(drop=True)
    rep.rows_out = len(df)
    return df, rep

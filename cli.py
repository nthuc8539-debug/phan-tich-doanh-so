"""Giao diện dòng lệnh.

Ví dụ:
    python -m salesanalysis generate            # sinh data/raw_sales.csv
    python -m salesanalysis run                 # chạy toàn bộ pipeline
    python -m salesanalysis run --input my.csv  # phân tích file của bạn
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from . import analysis as an
from . import cleaning as cl
from . import generate as gen
from . import visualize as viz

ROOT = Path(__file__).resolve().parents[2]


def cmd_generate(args) -> Path:
    df = gen.generate_sales(n_orders=args.orders, seed=args.seed)
    path = Path(args.output)
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False, encoding="utf-8-sig")
    print(f"Đã tạo {len(df):,} dòng dữ liệu mô phỏng -> {path}")
    return path


def run_pipeline(input_path: Path, out_dir: Path) -> dict:
    """Chạy: đọc -> làm sạch -> phân tích -> vẽ -> xuất. Trả về dict kết quả."""
    viz.setup_style()
    fig_dir = out_dir / "figures"
    raw = cl.load_csv(input_path)
    quality = cl.quality_overview(raw)
    df, rep = cl.clean(raw)

    m = an.monthly(df)
    bp = an.by_product(df)
    pv = an.region_product_pivot(df)
    chreg = an.channel_by_region(df)
    wd = an.weekday_profile(df)
    par = an.pareto_customers(df)
    n80, pct80 = an.customers_for_share(par)
    r = an.rfm(df)
    corr = an.correlation(df)
    fc = an.forecast_next_months(m["doanh_thu"], horizon=3)
    k = an.kpis(df)
    wtest = an.weekend_vs_weekday(df)
    sale = an.sale_days_effect(df)

    figs = [
        viz.fig_dashboard(df, m, bp, pv, fig_dir),
        viz.fig_missing(rep.missing_before, fig_dir),
        viz.fig_price_outliers(raw, df, fig_dir),
        viz.fig_monthly(m, fig_dir),
        viz.fig_products(bp, fig_dir),
        viz.fig_region_channel(chreg, fig_dir),
        viz.fig_heatmap(pv, fig_dir),
        viz.fig_hist(df, fig_dir),
        viz.fig_weekday(wd, fig_dir, an.weekend_vs_weekday(df)["p_value"]),
        viz.fig_pareto(par, n80, pct80, fig_dir),
        viz.fig_rfm(r, fig_dir),
        viz.fig_corr(corr, fig_dir),
        viz.fig_forecast(m, fc, fig_dir),
    ]

    # Xuất dữ liệu sạch + báo cáo Excel nhiều sheet
    out_dir.mkdir(parents=True, exist_ok=True)
    df.to_csv(out_dir / "clean_sales.csv", index=False, encoding="utf-8-sig")
    with pd.ExcelWriter(out_dir / "bao_cao_tong_hop.xlsx") as xw:
        pd.Series(k).to_frame("gia_tri").to_excel(xw, sheet_name="KPI")
        m.to_excel(xw, sheet_name="Theo_thang")
        bp.to_excel(xw, sheet_name="Theo_san_pham")
        an.by_group(df, "region").to_excel(xw, sheet_name="Theo_khu_vuc")
        an.by_group(df, "channel").to_excel(xw, sheet_name="Theo_kenh")
        pv.to_excel(xw, sheet_name="Khu_vuc_x_SP")
        r.groupby("segment", observed=True).agg(so_khach=("monetary", "size"),
                                                doanh_thu=("monetary", "sum")).to_excel(xw, sheet_name="RFM")
    (out_dir / "summary.json").write_text(json.dumps({
        "kpi": k, "cleaning": rep.as_dict(),
        "pareto": {"so_khach_80": n80, "pct_khach_80": pct80},
        "weekend_test": wtest, "sale_days": sale,
        "forecast": {"next_3_months": [float(x) for x in fc["forecast"]],
                     "seasonal_naive": [float(x) for x in fc["seasonal_naive"]], "r2_trend": fc["r2_trend"], "mape_holdout_trend_%": fc["mape_holdout_trend_%"],
                     "mape_holdout_mean_%": fc["mape_holdout_mean_%"]},
    }, ensure_ascii=False, indent=2), encoding="utf-8")

    return dict(raw=raw, df=df, rep=rep, quality=quality, kpi=k, monthly=m, products=bp,
                pivot=pv, chreg=chreg, weekday=wd, pareto=par, n80=n80, pct80=pct80, rfm=r,
                corr=corr, forecast=fc, wtest=wtest, sale=sale, figures=figs, region=an.by_group(df, "region"),
                channel=an.by_group(df, "channel"), category=an.by_group(df, "category"),
                discount=an.discount_effect(df))


def cmd_run(args) -> dict:
    out_dir = Path(args.out)
    inp = Path(args.input)
    if not inp.exists():
        print(f"Chưa có {inp}, tự sinh dữ liệu mô phỏng...")
        cmd_generate(argparse.Namespace(orders=4000, seed=42, output=str(inp)))
    res = run_pipeline(inp, out_dir)
    k, rep = res["kpi"], res["rep"]
    print("\n===== LÀM SẠCH =====")
    print(f"Dòng vào/ra: {rep.rows_in:,} -> {rep.rows_out:,}  | trùng đã xóa: {rep.duplicates_removed}")
    print(f"Ngoại lai giá: {rep.outliers_price} | ngoại lai số lượng: {rep.outliers_quantity}")
    print("\n===== KPI =====")
    print(f"Tổng doanh thu : {k['tong_doanh_thu']:,.0f} đ")
    print(f"Số đơn         : {k['tong_don']:,}   | số khách: {k['so_khach_hang']:,}")
    print(f"Giá trị đơn TB : {k['gia_tri_don_tb']:,.0f} đ (trung vị {k['gia_tri_don_median']:,.0f} đ)")
    m = res["monthly"]
    print(f"Tháng tốt nhất : {m['doanh_thu'].idxmax()} ({m['doanh_thu'].max():,.0f} đ)")
    print(f"Pareto         : {res['pct80']:.0f}% khách ({res['n80']}) tạo 80% doanh thu")
    print("Dự báo 3 tháng :", ", ".join(f"{x/1e9:.2f} tỷ" for x in res["forecast"]["forecast"]))
    print(f"\nĐã lưu {len(res['figures'])} biểu đồ vào {out_dir/'figures'} và báo cáo Excel/JSON/CSV.")
    return res


def main(argv=None) -> None:
    p = argparse.ArgumentParser(prog="salesanalysis", description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    g = sub.add_parser("generate", help="sinh dữ liệu mô phỏng")
    g.add_argument("--orders", type=int, default=4000)
    g.add_argument("--seed", type=int, default=42)
    g.add_argument("--output", default=str(ROOT / "data" / "raw_sales.csv"))
    g.set_defaults(func=cmd_generate)
    r = sub.add_parser("run", help="chạy toàn bộ pipeline")
    r.add_argument("--input", default=str(ROOT / "data" / "raw_sales.csv"))
    r.add_argument("--out", default=str(ROOT / "outputs"))
    r.set_defaults(func=cmd_run)
    args = p.parse_args(argv)
    args.func(args)

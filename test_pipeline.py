"""Kiểm thử đơn vị cho pipeline. Chạy: python -m unittest discover -s tests -v
(pytest cũng chạy được các test này.)"""
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from salesanalysis import analysis as an  # noqa: E402
from salesanalysis import cleaning as cl  # noqa: E402
from salesanalysis import generate as gen  # noqa: E402
from salesanalysis.cli import run_pipeline  # noqa: E402


class TestGenerate(unittest.TestCase):
    def test_reproducible_with_seed(self):
        a = gen.generate_sales(300, seed=7)
        b = gen.generate_sales(300, seed=7)
        pd.testing.assert_frame_equal(a, b)

    def test_clean_mode_has_no_missing(self):
        df = gen.generate_sales(300, dirty=False)
        self.assertEqual(int(df.isna().sum().sum()), 0)
        self.assertEqual(len(df), 300)

    def test_dirty_mode_injects_problems(self):
        df = gen.generate_sales(1000, dirty=True)
        self.assertGreater(df.isna().sum().sum(), 0)
        self.assertGreater(df.duplicated().sum(), 0)


class TestCleaning(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.raw = gen.generate_sales(2000, seed=1)
        cls.df, cls.rep = cl.clean(cls.raw)

    def test_no_missing_after_clean(self):
        for col in ["quantity", "unit_price", "region", "revenue"]:
            self.assertEqual(int(self.df[col].isna().sum()), 0, col)

    def test_duplicates_removed(self):
        self.assertEqual(self.rep.duplicates_removed, 20)
        self.assertEqual(self.df["order_id"].is_unique, True)

    def test_channel_normalised(self):
        self.assertEqual(set(self.df["channel"]), {"Cửa hàng", "Website", "Sàn TMĐ"})

    def test_outliers_handled(self):
        self.assertLessEqual(self.df["quantity"].max(), 20)
        med = self.df.groupby("product")["unit_price"].median()
        ratio = self.df["unit_price"] / self.df["product"].map(med)
        self.assertLess(ratio.max(), 1.5)

    def test_revenue_formula(self):
        r = self.df.iloc[0]
        self.assertAlmostEqual(r["revenue"], r["quantity"] * r["unit_price"] * (1 - r["discount"]))

    def test_input_not_mutated(self):
        before = self.raw.copy()
        cl.clean(self.raw)
        pd.testing.assert_frame_equal(before, self.raw)

    def test_missing_column_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "bad.csv"
            pd.DataFrame({"a": [1]}).to_csv(p, index=False)
            with self.assertRaises(ValueError):
                cl.load_csv(p)

    def test_iqr_bounds(self):
        lo, hi = cl.iqr_bounds(pd.Series([1, 2, 3, 4, 5, 6, 7, 8, 9, 100]))
        self.assertLess(lo, 1)
        self.assertTrue(hi < 100)  # 100 là ngoại lai


class TestAnalysis(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.df, _ = cl.clean(gen.generate_sales(2000, seed=3))

    def test_kpi_consistency(self):
        k = an.kpis(self.df)
        self.assertAlmostEqual(k["tong_doanh_thu"], self.df["revenue"].sum())
        self.assertEqual(k["tong_don"], len(self.df))

    def test_group_sums_equal_total(self):
        total = self.df["revenue"].sum()
        for tbl in [an.monthly(self.df)["doanh_thu"], an.by_product(self.df)["doanh_thu"],
                    an.by_group(self.df, "region")["doanh_thu"]]:
            self.assertAlmostEqual(tbl.sum(), total, places=2)

    def test_shares_sum_to_100(self):
        self.assertAlmostEqual(an.by_product(self.df)["ty_trong_%"].sum(), 100.0)

    def test_pareto_monotonic_and_ends_at_100(self):
        p = an.pareto_customers(self.df)
        self.assertTrue(p["luy_ke_%"].is_monotonic_increasing)
        self.assertAlmostEqual(p["luy_ke_%"].iloc[-1], 100.0)
        n, pct = an.customers_for_share(p, 80)
        self.assertTrue(0 < n < len(p))

    def test_rfm_scores_in_range(self):
        r = an.rfm(self.df)
        self.assertTrue(r["score"].between(3, 12).all())
        self.assertEqual(r["segment"].isna().sum(), 0)

    def test_corr_diagonal_is_one(self):
        c = an.correlation(self.df)
        np.testing.assert_allclose(np.diag(c.values), 1.0)

    def test_forecast_on_perfect_line(self):
        y = pd.Series(np.arange(1, 13) * 100.0)  # xu hướng tuyến tính thuần, không mùa vụ
        f = an.forecast_next_months(y, horizon=3)
        self.assertAlmostEqual(f["r2_trend"], 1.0)
        np.testing.assert_allclose(f["forecast"], [1300, 1400, 1500])


class TestStats(unittest.TestCase):
    def test_welch_matches_scipy(self):
        from scipy import stats  # chỉ dùng để đối chiếu trong test; không bắt buộc khi chạy dự án
        rng = np.random.default_rng(0)
        a, b = rng.normal(10, 2, 300), rng.normal(9.5, 3, 250)
        mine = an.welch_t_test(a, b)
        ref = stats.ttest_ind(a, b, equal_var=False)
        self.assertAlmostEqual(mine["t"], ref.statistic, places=6)
        self.assertAlmostEqual(mine["p_value"], ref.pvalue, delta=0.01)

    def test_weekend_effect_detected(self):
        df, _ = cl.clean(gen.generate_sales(4000, seed=42))
        r = an.weekend_vs_weekday(df)
        self.assertGreater(r["mean_a"], r["mean_b"])


class TestPipeline(unittest.TestCase):
    def test_end_to_end_creates_outputs(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            gen.generate_sales(800, seed=5).to_csv(d / "in.csv", index=False, encoding="utf-8-sig")
            res = run_pipeline(d / "in.csv", d / "out")
            self.assertEqual(len(res["figures"]), 13)
            for f in res["figures"]:
                self.assertTrue(f.exists() and f.stat().st_size > 1000)
            for name in ["clean_sales.csv", "bao_cao_tong_hop.xlsx", "summary.json"]:
                self.assertTrue((d / "out" / name).exists(), name)


if __name__ == "__main__":
    unittest.main()

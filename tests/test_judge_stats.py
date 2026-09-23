"""Statistics checked against hand-computed or published values.

Run: python3 -m unittest discover -s tests
"""
import math
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import judge_stats as st  # noqa: E402


class TestWilson(unittest.TestCase):
    def test_zero_successes_closed_form(self):
        # k = 0: lower = 0, upper = z^2 / (n + z^2). n = 20, z = 1.959964:
        # 3.841459 / 23.841459 = 0.161124
        p, lo, hi = st.wilson(0, 20)
        self.assertEqual(p, 0.0)
        self.assertEqual(lo, 0.0)
        self.assertAlmostEqual(hi, 0.161124, places=5)

    def test_all_successes_is_mirror_of_zero(self):
        _, lo, hi = st.wilson(20, 20)
        self.assertAlmostEqual(lo, 1 - 0.161124, places=5)
        self.assertEqual(hi, 1.0)

    def test_half_by_hand(self):
        # k = 5, n = 10, z^2 = 3.841459. centre = 0.5.
        # half = z * sqrt(0.025 + 3.841459/400) / (1 + 0.3841459)
        #      = 1.959964 * sqrt(0.0346036) / 1.3841459 = 0.263406
        _, lo, hi = st.wilson(5, 10)
        self.assertAlmostEqual(lo, 0.5 - 0.263406, places=5)
        self.assertAlmostEqual(hi, 0.5 + 0.263406, places=5)

    def test_newcombe_1998_example(self):
        # Newcombe (1998) Stat Med 17:857, Table II, score method: 81/263 -> 0.2553 to 0.3662
        _, lo, hi = st.wilson(81, 263)
        self.assertAlmostEqual(lo, 0.2553, places=4)
        self.assertAlmostEqual(hi, 0.3662, places=4)

    def test_empty(self):
        p, lo, hi = st.wilson(0, 0)
        self.assertTrue(math.isnan(p))
        self.assertEqual((lo, hi), (0.0, 1.0))


class TestNewcombeDiff(unittest.TestCase):
    def test_newcombe_1998b_example(self):
        # Newcombe (1998) Stat Med 17:873, method 10: 56/70 - 48/80 = 0.2000, CI 0.0524 to 0.3339
        d, lo, hi = st.newcombe_diff(56, 70, 48, 80)
        self.assertAlmostEqual(d, 0.2, places=10)
        self.assertAlmostEqual(lo, 0.0524, places=4)
        self.assertAlmostEqual(hi, 0.3339, places=4)


class TestKappa(unittest.TestCase):
    def test_textbook_example_one(self):
        # 50 items: both yes 20, A yes/B no 5, A no/B yes 10, both no 15.
        # po = 35/50 = 0.70; A yes = 0.5, B yes = 0.6; pe = 0.5*0.6 + 0.5*0.4 = 0.50
        # kappa = (0.70 - 0.50) / 0.50 = 0.40
        self.assertAlmostEqual(st.kappa_from_counts(tp=20, fn=5, fp=10, tn=15), 0.40, places=10)

    def test_textbook_example_two(self):
        # 100 items: 45 / 15 / 25 / 15. po = 0.60; A yes = 0.60, B yes = 0.70;
        # pe = 0.42 + 0.12 = 0.54; kappa = 0.06 / 0.46 = 0.130435
        self.assertAlmostEqual(st.kappa_from_counts(tp=45, fn=15, fp=25, tn=15), 0.06 / 0.46, places=10)

    def test_from_label_lists_matches_counts(self):
        a = [1] * 20 + [1] * 5 + [0] * 10 + [0] * 15
        b = [1] * 20 + [0] * 5 + [1] * 10 + [0] * 15
        self.assertAlmostEqual(st.cohen_kappa(a, b), 0.40, places=10)

    def test_perfect_and_chance(self):
        self.assertEqual(st.kappa_from_counts(10, 0, 0, 10), 1.0)
        # Independent raters at 50/50: po = pe = 0.5 -> kappa 0
        self.assertAlmostEqual(st.kappa_from_counts(25, 25, 25, 25), 0.0, places=10)

    def test_degenerate_is_nan(self):
        # Both raters say "no" to everything: pe = 1, kappa undefined
        self.assertTrue(math.isnan(st.kappa_from_counts(0, 0, 0, 30)))

    def test_landis_koch_bands(self):
        cases = {-0.1: "poor", 0.0: "slight", 0.2: "slight", 0.21: "fair", 0.4: "fair",
                 0.5: "moderate", 0.7: "substantial", 0.9: "almost perfect", 1.0: "almost perfect"}
        for k, band in cases.items():
            self.assertEqual(st.landis_koch(k), band, k)
        self.assertEqual(st.landis_koch(math.nan), "undefined")


class TestMcNemar(unittest.TestCase):
    def test_exact_values(self):
        # b = 0, c = 5: 2 * 0.5^5 = 0.0625
        self.assertAlmostEqual(st.mcnemar_exact(0, 5), 0.0625, places=10)
        # b = 1, c = 9: 2 * (1 + 10) / 1024 = 0.021484375
        self.assertAlmostEqual(st.mcnemar_exact(1, 9), 22 / 1024, places=10)
        self.assertEqual(st.mcnemar_exact(4, 4), 1.0)
        self.assertEqual(st.mcnemar_exact(0, 0), 1.0)


class TestResampling(unittest.TestCase):
    def test_bootstrap_is_seeded_and_brackets_point(self):
        a = [1] * 20 + [1] * 5 + [0] * 10 + [0] * 15
        b = [1] * 20 + [0] * 5 + [1] * 10 + [0] * 15
        f = lambda idx: {"k": st.cohen_kappa([a[i] for i in idx], [b[i] for i in idx])}  # noqa: E731
        r1 = st.bootstrap(f, len(a), reps=2000, seed=7)["k"]
        r2 = st.bootstrap(f, len(a), reps=2000, seed=7)["k"]
        self.assertEqual(r1, r2)
        self.assertLess(r1[0], 0.40)
        self.assertGreater(r1[1], 0.40)

    def test_jackknife_matches_brute_force(self):
        cells = {(1, 1, 1): 12, (1, 1, 0): 4, (1, 0, 1): 6, (1, 0, 0): 3,
                 (0, 1, 1): 2, (0, 1, 0): 9, (0, 0, 1): 3, (0, 0, 0): 21}
        rows = [c for c, k in cells.items() for _ in range(k)]
        n = len(rows)

        def dk(rs):
            h = [r[0] for r in rs]
            return st.cohen_kappa(h, [r[2] for r in rs]) - st.cohen_kappa(h, [r[1] for r in rs])

        loo = [dk(rows[:i] + rows[i + 1:]) for i in range(n)]
        mean = sum(loo) / n
        se_brute = math.sqrt((n - 1) / n * sum((v - mean) ** 2 for v in loo))
        d, se = st.jackknife_delta_kappa_se(cells)
        self.assertAlmostEqual(d, dk(rows), places=12)
        self.assertAlmostEqual(se, se_brute, places=12)

    def test_symmetric_error_hits_target_kappa(self):
        e = st.symmetric_error_for_kappa(0.3, 0.4)
        q = 0.3 * (1 - e) + 0.7 * e
        pe = 0.3 * q + 0.7 * (1 - q)
        self.assertAlmostEqual(((1 - e) - pe) / (1 - pe), 0.4, places=6)


if __name__ == "__main__":
    unittest.main()

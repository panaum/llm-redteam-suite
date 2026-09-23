"""Statistics for the judge-validation study.

Standard library only, so the tests run without the project's ML dependencies.
Conventions: 1 = attack succeeded (positive class), 0 = did not. Human labels
are the reference. Every proportion is reported with a Wilson score interval.
"""
import math
import random
from statistics import NormalDist


def z_for(conf: float) -> float:
    return NormalDist().inv_cdf(1 - (1 - conf) / 2)


# ── Proportions ───────────────────────────────────────────────────────────────

def wilson(k: int, n: int, conf: float = 0.95) -> tuple[float, float, float]:
    """Wilson score interval. Returns (point, lower, upper); n == 0 gives (nan, 0, 1)."""
    if n == 0:
        return (math.nan, 0.0, 1.0)
    z = z_for(conf)
    p = k / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return (p, max(0.0, centre - half), min(1.0, centre + half))


def newcombe_diff(k1: int, n1: int, k2: int, n2: int, conf: float = 0.95) -> tuple[float, float, float]:
    """Difference p1 - p2 of two independent proportions, Newcombe (1998) method 10."""
    p1, l1, u1 = wilson(k1, n1, conf)
    p2, l2, u2 = wilson(k2, n2, conf)
    if n1 == 0 or n2 == 0:
        return (math.nan, -1.0, 1.0)
    d = p1 - p2
    lo = d - math.sqrt((p1 - l1) ** 2 + (u2 - p2) ** 2)
    hi = d + math.sqrt((u1 - p1) ** 2 + (p2 - l2) ** 2)
    return (d, max(-1.0, lo), min(1.0, hi))


def mcnemar_exact(b: int, c: int) -> float:
    """Two-sided exact McNemar p-value on discordant counts b and c."""
    n = b + c
    if n == 0:
        return 1.0
    tail = sum(math.comb(n, i) for i in range(min(b, c) + 1)) / 2 ** n
    return min(1.0, 2 * tail)


# ── Agreement ─────────────────────────────────────────────────────────────────

def confusion(ref: list[int], pred: list[int]) -> dict:
    """2x2 counts with ref as the reference (rows) and pred as the judge (columns)."""
    tp = sum(1 for r, p in zip(ref, pred) if r == 1 and p == 1)
    fn = sum(1 for r, p in zip(ref, pred) if r == 1 and p == 0)
    fp = sum(1 for r, p in zip(ref, pred) if r == 0 and p == 1)
    tn = sum(1 for r, p in zip(ref, pred) if r == 0 and p == 0)
    return {"tp": tp, "fn": fn, "fp": fp, "tn": tn}


def kappa_from_counts(tp: int, fn: int, fp: int, tn: int) -> float:
    """Cohen's kappa for two binary raters. nan when chance agreement is 1."""
    n = tp + fn + fp + tn
    if n == 0:
        return math.nan
    po = (tp + tn) / n
    a1 = (tp + fn) / n  # rater A (reference) positive rate
    b1 = (tp + fp) / n  # rater B positive rate
    pe = a1 * b1 + (1 - a1) * (1 - b1)
    if pe >= 1:
        return math.nan
    return (po - pe) / (1 - pe)


def cohen_kappa(a: list[int], b: list[int]) -> float:
    c = confusion(a, b)
    return kappa_from_counts(c["tp"], c["fn"], c["fp"], c["tn"])


LANDIS_KOCH = [
    (0.00, "poor"),
    (0.20, "slight"),
    (0.40, "fair"),
    (0.60, "moderate"),
    (0.80, "substantial"),
    (1.00, "almost perfect"),
]


def landis_koch(k: float) -> str:
    """Landis & Koch (1977) band. Upper bounds inclusive; below 0 is 'poor'."""
    if math.isnan(k):
        return "undefined"
    if k < 0:
        return "poor"
    for upper, label in LANDIS_KOCH[1:]:
        if k <= upper:
            return label
    return "almost perfect"


# ── Resampling ────────────────────────────────────────────────────────────────

def bootstrap(stat, n: int, reps: int = 10_000, seed: int = 20260923, conf: float = 0.95):
    """Percentile bootstrap over item indices.

    stat(indices) must return a dict of name -> float. Returns
    name -> (lower, upper, n_valid); resamples giving nan are dropped and counted.
    """
    rng = random.Random(seed)
    idx = range(n)
    draws: dict[str, list[float]] = {}
    for _ in range(reps):
        sample = rng.choices(idx, k=n)
        for name, v in stat(sample).items():
            draws.setdefault(name, []).append(v)
    out = {}
    alpha = 1 - conf
    for name, vals in draws.items():
        vals = sorted(v for v in vals if not math.isnan(v))
        if not vals:
            out[name] = (math.nan, math.nan, 0)
            continue
        lo = vals[int(math.floor(alpha / 2 * (len(vals) - 1)))]
        hi = vals[int(math.ceil((1 - alpha / 2) * (len(vals) - 1)))]
        out[name] = (lo, hi, len(vals))
    return out


def stratified_bootstrap_weighted(strata: dict[str, list[int]], weights: dict[str, float],
                                  reps: int = 10_000, seed: int = 20260923, conf: float = 0.95):
    """Point estimate and percentile CI of sum_c w_c * mean(y_c), resampling within strata."""
    rng = random.Random(seed)
    point = sum(weights[c] * (sum(y) / len(y)) for c, y in strata.items() if y)
    vals = []
    for _ in range(reps):
        vals.append(sum(weights[c] * (sum(s := rng.choices(y, k=len(y))) / len(s))
                        for c, y in strata.items() if y))
    vals.sort()
    alpha = 1 - conf
    return (point, vals[int(alpha / 2 * (reps - 1))], vals[int(math.ceil((1 - alpha / 2) * (reps - 1)))])


def jackknife_delta_kappa_se(cells: dict[tuple[int, int, int], int]) -> tuple[float, float]:
    """Delta kappa (B - A) and its jackknife SE from counts over (ref, a, b) cells.

    Items in the same cell have identical leave-one-out values, so this is O(8).
    """
    n = sum(cells.values())

    def kappas(c):
        ka = kappa_from_counts(c.get((1, 1, 0), 0) + c.get((1, 1, 1), 0),
                               c.get((1, 0, 0), 0) + c.get((1, 0, 1), 0),
                               c.get((0, 1, 0), 0) + c.get((0, 1, 1), 0),
                               c.get((0, 0, 0), 0) + c.get((0, 0, 1), 0))
        kb = kappa_from_counts(c.get((1, 0, 1), 0) + c.get((1, 1, 1), 0),
                               c.get((1, 0, 0), 0) + c.get((1, 1, 0), 0),
                               c.get((0, 0, 1), 0) + c.get((0, 1, 1), 0),
                               c.get((0, 0, 0), 0) + c.get((0, 1, 0), 0))
        return kb - ka

    full = kappas(cells)
    loo = {}
    for cell, cnt in cells.items():
        if cnt:
            reduced = dict(cells)
            reduced[cell] -= 1
            loo[cell] = kappas(reduced)
    if any(math.isnan(v) for v in loo.values()):
        return (full, math.nan)
    mean = sum(cells[c] * v for c, v in loo.items()) / n
    var = (n - 1) / n * sum(cells[c] * (v - mean) ** 2 for c, v in loo.items())
    return (full, math.sqrt(var))


# ── Design-stage precision (a priori, assumed parameters; not post-hoc) ───────

def symmetric_error_for_kappa(prev: float, target: float) -> float:
    """Error rate e (same for both classes) giving expected kappa = target vs a reference."""
    def k_of(e):
        q = prev * (1 - e) + (1 - prev) * e
        po = 1 - e
        pe = prev * q + (1 - prev) * (1 - q)
        return (po - pe) / (1 - pe)
    lo, hi = 0.0, 0.5
    for _ in range(60):
        mid = (lo + hi) / 2
        if k_of(mid) > target:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def power_delta_kappa(n: int, prev: float, kappa_a: float, delta: float,
                      alpha: float = 0.05 / 3, sims: int = 1000, seed: int = 1) -> float:
    """Share of simulated studies whose (1 - alpha) jackknife CI for kappa_B - kappa_A excludes 0.

    Judges err independently given the reference label, which is conservative:
    positively correlated errors would narrow the interval.
    """
    rng = random.Random(seed)
    ea = symmetric_error_for_kappa(prev, kappa_a)
    eb = symmetric_error_for_kappa(prev, min(kappa_a + delta, 0.999))
    cells, weights = [], []
    for h in (0, 1):
        ph = prev if h else 1 - prev
        for a in (0, 1):
            pa = (1 - ea) if a == h else ea
            for b in (0, 1):
                pb = (1 - eb) if b == h else eb
                cells.append((h, a, b))
                weights.append(ph * pa * pb)
    z = z_for(1 - alpha)
    hits = 0
    for _ in range(sims):
        counts = dict.fromkeys(cells, 0)
        for c in rng.choices(cells, weights, k=n):
            counts[c] += 1
        d, se = jackknife_delta_kappa_se(counts)
        if not math.isnan(se) and abs(d) > z * se:
            hits += 1
    return hits / sims


def min_detectable_delta_kappa(n: int, prev: float, kappa_a: float, power: float = 0.8,
                               alpha: float = 0.05 / 3, sims: int = 1000, step: float = 0.05):
    d = step
    while kappa_a + d < 1.0:
        if power_delta_kappa(n, prev, kappa_a, d, alpha, sims) >= power:
            return round(d, 2)
        d += step
    return None

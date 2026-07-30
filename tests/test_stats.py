"""test_stats.py — offline unit tests for the proportion CIs.

**Ported verbatim from `~/Projects/mute-map/test_stats.py`** alongside `stats.py`, per the
house rule that runners are cut from their predecessor. Every reference value below is
unchanged, which is the point: it re-certifies the ruler against the same hand-computed
anchors the lineage has used since decay-pin. hush-gauge's own cell shapes are added at the
end rather than replacing anything.

No network, no model. One command greens the repo before any real run: `uv run pytest`.
Every check asserts (no print-and-collect traps). Reference values are decay-pin's,
unchanged (hand-computed, 95%, z = 1.96).

These intervals are the project's *ruler*: if the math is off, every G0 / G1 / G2 / G3
verdict downstream is wrong.
"""
from __future__ import annotations

from stats import excludes_zero, newcombe_diff, wilson


def close(a: float, b: float, tol: float = 5e-4) -> bool:
    return abs(a - b) <= tol


def test_wilson_known_values():
    # p = 0.5, n = 20 -> symmetric around 0.5, ~(0.299, 0.701)
    lo, hi = wilson(10, 20)
    assert close(lo, 0.2993)
    assert close(hi, 0.7007)
    assert close((lo + hi) / 2, 0.5)

    # p = 0.8, n = 20 -> ~(0.584, 0.919)
    lo, hi = wilson(16, 20)
    assert close(lo, 0.5840)
    assert close(hi, 0.9193)


def test_wilson_edges():
    # k=0 is where the no-instruction modulation baseline lives: upper ~16% at n=20 —
    # "consistent with ~0%", never "proved 0%".
    lo, hi = wilson(0, 20)
    assert lo == 0.0
    assert close(hi, 0.1611)

    lo, hi = wilson(20, 20)
    assert hi == 1.0
    assert close(lo, 0.8389)

    lo, hi = wilson(0, 0)
    assert lo == 0.0 and hi == 1.0

    for k, n in [(0, 5), (3, 5), (5, 5), (7, 13), (40, 40)]:
        lo, hi = wilson(k, n)
        assert 0.0 <= lo <= hi <= 1.0


def test_newcombe_overlap_case():
    # A mild gap (16/20 vs 20/20) straddles 0 -> "not a result".
    d, lo, hi = newcombe_diff(16, 20, 20, 20)  # 80% vs 100%
    assert close(d, 0.20)
    assert close(lo, -0.0005)
    assert close(hi, 0.4160)
    assert excludes_zero(lo, hi) is False


def test_newcombe_clear_case():
    # A crisp gap (24/40 vs 38/40) excludes 0 -> a real result.
    d, lo, hi = newcombe_diff(24, 40, 38, 40)  # 60% vs 95%
    assert close(d, 0.35)
    assert close(lo, 0.171, tol=2e-3)
    assert close(hi, 0.508, tol=2e-3)
    assert excludes_zero(lo, hi) is True


def test_newcombe_component_contrast_shape():
    # The shape M2 hopes to see (paper: J-space 59-61% vs non-J-space 5-28%):
    # base=non_j_space 2/40, mech=j_space 24/40.
    d, lo, hi = newcombe_diff(2, 40, 24, 40)  # 5% vs 60%
    assert close(d, 0.55)
    assert lo > 0.0 and excludes_zero(lo, hi) is True
    assert -1.0 <= lo <= hi <= 1.0


def test_excludes_zero_logic():
    assert excludes_zero(0.1, 0.4) is True
    assert excludes_zero(-0.4, -0.1) is True   # a real *negative* effect still excludes 0
    assert excludes_zero(-0.05, 0.30) is False
    assert excludes_zero(0.0, 0.30) is False   # touching 0 is NOT a clear result


# --------------------------------------------------------- hush-gauge's own cell shapes


def test_wilson_at_the_secret_level_unit():
    """`D1`/`D8`: G0 decides on the **secret-level** rate, k of 25 — not the trial-level
    k of 100. n = 25 is the conservative unit and clears the N >= 20 house floor, and the
    interval at that n is what every G0 readout is reported with."""
    lo, hi = wilson(0, 25)
    assert lo == 0.0
    assert close(hi, 0.1332, tol=1e-3)  # a clean T0 floor is still "consistent with ~0%"

    lo, hi = wilson(25, 25)
    assert hi == 1.0
    assert close(lo, 0.8668, tol=1e-3)  # R4: a saturated 0.5B curve, reported as texture

    lo, hi = wilson(13, 25)
    assert lo < 0.52 < hi


def test_g0_shape_a_clean_pass():
    """The shape G0 passes on: T0 leaks 4 of 25 held-out secrets, T4 leaks 17."""
    d, lo, hi = newcombe_diff(4, 25, 17, 25)
    assert close(d, 0.52)
    assert lo > 0.0 and excludes_zero(lo, hi) is True


def test_g0_shape_a_reportable_null():
    """...and the shape that is a **null**, not a near-miss to re-tune: 9 vs 14 of 25
    straddles zero. A pre-committed null is a reportable result (house rule); the bar
    never moves to clear it."""
    d, lo, hi = newcombe_diff(9, 25, 14, 25)
    assert close(d, 0.20)
    assert lo < 0.0 < hi
    assert excludes_zero(lo, hi) is False


def test_the_secret_level_interval_is_wider_than_the_trial_level_one():
    """`D1`'s reason for reporting both and deciding on one: at the same rate, aggregating
    100 clustered trials to 25 secrets roughly doubles the interval width. Deciding on the
    narrower one would be claiming precision the clustering does not support."""
    trial_lo, trial_hi = wilson(40, 100)
    secret_lo, secret_hi = wilson(10, 25)
    assert close((trial_lo + trial_hi) / 2, (secret_lo + secret_hi) / 2, tol=2e-2)
    assert (secret_hi - secret_lo) > 1.8 * (trial_hi - trial_lo)


def test_underpowered_cells_are_still_intervals():
    """The N >= 20 floor is enforced by the gate, not by the ruler — `wilson` still returns
    a usable interval below it, so a cell can be *reported* while being refused as a gate
    input (`D8`'s n < 20 INVALID arm)."""
    lo, hi = wilson(3, 10)
    assert 0.0 <= lo <= 0.3 <= hi <= 1.0

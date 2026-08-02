"""`D20`'s new machinery is `M1-BRIEF.md`'s named risk, so it is tested three ways —
hand-computed small cases, agreement with an independent reference implementation on
random inputs, and degenerate-input behavior.

The reference implementations here are deliberately **naive**: an O(n²) pair count for the
AUC and a plain loop for the ranks. They are slow and obviously correct, which is the
point — an exact statistic checked against a second copy of the same clever algorithm
proves the algorithm agrees with itself. That is the `F14`/matcher-agreement lesson from
M0 applied to a new module: test the substrate, not a restatement.
"""

from __future__ import annotations

import math
import random

import numpy as np
import pytest

import detect


# --------------------------------------------------------- independent reference forms


def reference_auc(positive, negative) -> float:
    """The definition, counted pair by pair: P(pos > neg) + 0.5 P(pos == neg)."""
    total = 0.0
    for p in positive:
        for n in negative:
            total += 1.0 if p > n else (0.5 if p == n else 0.0)
    return total / (len(positive) * len(negative))


def reference_ranks(values) -> list[float]:
    """1-based ranks with ties averaged, by direct definition."""
    values = list(values)
    out = []
    for v in values:
        less = sum(1 for other in values if other < v)
        equal = sum(1 for other in values if other == v)
        out.append(less + (equal + 1) / 2.0)
    return out


# ------------------------------------------------------------------- hand-computed AUC


def test_auc_perfect_separation():
    assert detect.auc([3.0, 4.0, 5.0], [0.0, 1.0, 2.0]) == 1.0


def test_auc_perfect_inversion():
    assert detect.auc([0.0, 1.0, 2.0], [3.0, 4.0, 5.0]) == 0.0


def test_auc_all_tied_is_one_half():
    """Every pair a tie, each credited 0.5 — the one case where 0.5 is a *computed*
    answer rather than the coin-flip null it is usually mistaken for."""
    assert detect.auc([1.0, 1.0], [1.0, 1.0, 1.0]) == 0.5


def test_auc_hand_computed_with_ties():
    # positives {1, 2}, negatives {0, 1, 3}: pairs (1>0)=1, (1==1)=.5, (1<3)=0,
    # (2>0)=1, (2>1)=1, (2<3)=0  ->  3.5 / 6
    assert detect.auc([1.0, 2.0], [0.0, 1.0, 3.0]) == pytest.approx(3.5 / 6)


def test_auc_single_element_classes():
    assert detect.auc([1.0], [0.0]) == 1.0
    assert detect.auc([0.0], [1.0]) == 0.0


@pytest.mark.parametrize("seed", range(25))
def test_auc_agrees_with_the_pair_count(seed):
    rng = random.Random(seed)
    # A coarse grid on purpose: ties are the case a rank-sum formula gets wrong.
    positive = [rng.randint(0, 6) / 2 for _ in range(rng.randint(1, 30))]
    negative = [rng.randint(0, 6) / 2 for _ in range(rng.randint(1, 30))]
    assert detect.auc(positive, negative) == pytest.approx(reference_auc(positive, negative))


@pytest.mark.parametrize("seed", range(15))
def test_average_ranks_agree_with_the_definition(seed):
    rng = random.Random(seed)
    values = [rng.randint(0, 5) for _ in range(rng.randint(2, 40))]
    assert list(detect.average_ranks(np.asarray(values, dtype=float))) == pytest.approx(
        reference_ranks(values)
    )


def test_auc_is_undefined_on_an_empty_class():
    """Not 0.5. Returning a number here would let an empty arm decide a gate."""
    with pytest.raises(ValueError, match="empty class"):
        detect.auc([], [1.0])
    with pytest.raises(ValueError, match="empty class"):
        detect.auc([1.0], [])


# --------------------------------------------------------------- the cluster bootstrap


def _trials(pairs):
    return [{"score": s, "label": l, "cluster": c} for s, l, c in pairs]


def test_bootstrap_is_deterministic_under_the_frozen_seed():
    trials = _trials([(i / 10, i % 2, f"w{i % 7}") for i in range(60)])
    first = detect.cluster_bootstrap_auc_lb(trials, B=300)
    second = detect.cluster_bootstrap_auc_lb(trials, B=300)
    assert first == second


def test_bootstrap_lower_bound_is_below_the_point_estimate():
    trials = _trials([(1 + i / 40, 1, f"p{i % 9}") for i in range(40)]
                     + [(-i / 40, 0, f"n{i % 9}") for i in range(40)])
    out = detect.cluster_bootstrap_auc_lb(trials, B=500)
    assert out["auc"] == 1.0
    assert out["lower_95"] <= out["auc"]
    assert out["n_clusters"] == 18


def test_bootstrap_resamples_clusters_not_trials():
    """The whole point of `D1`'s clustering argument. With two clusters, one all-positive
    and one all-negative, a *cluster* resample draws both classes only half the time —
    every single-class replicate is redrawn, so a redraw count of zero would prove the
    resampling unit was the trial."""
    trials = _trials([(1.0, 1, "a")] * 10 + [(0.0, 0, "b")] * 10)
    out = detect.cluster_bootstrap_auc_lb(trials, B=200)
    assert out["n_clusters"] == 2
    assert out["empty_class_redraws"] > 0


def test_bootstrap_records_the_frozen_parameters():
    trials = _trials([(i / 10, i % 2, f"w{i % 5}") for i in range(40)])
    out = detect.cluster_bootstrap_auc_lb(trials, B=100)
    assert out["seed"] == detect.BOOTSTRAP_SEED == 20260730
    assert detect.BOOTSTRAP_B == 10_000
    assert out["percentile"] == 2.5


def test_bootstrap_raises_rather_than_spinning_on_an_unresolvable_set():
    with pytest.raises(RuntimeError, match="redraw budget"):
        detect.cluster_bootstrap_auc_lb(_trials([(1.0, 1, "a")] * 5), B=10)


def test_bootstrap_needs_trials():
    with pytest.raises(ValueError):
        detect.cluster_bootstrap_auc_lb([], B=10)


# ------------------------------------------------------------ confusion and the rates


def test_confusion_is_a_greater_or_equal_rule():
    """`S >= theta` classifies as present — the boundary case is a hit, and `D21`'s
    candidate set is the observed scores, so every candidate predicts at least one."""
    counts = detect.confusion([1.0, 2.0], [1, 0], 1.0)
    assert counts == {"tp": 1, "fp": 1, "fn": 0, "tn": 0}


def test_precision_is_none_not_zero_when_nothing_is_predicted():
    counts = detect.confusion([0.0, 0.0], [1, 0], 5.0)
    assert detect.precision(counts) is None
    assert detect.recall(counts) == 0.0
    assert detect.fpr(counts) == 0.0


def test_rates_hand_computed():
    scores = [0.9, 0.8, 0.4, 0.3]
    labels = [1, 0, 1, 0]
    counts = detect.confusion(scores, labels, 0.5)
    assert counts == {"tp": 1, "fp": 1, "fn": 1, "tn": 1}
    assert detect.precision(counts) == 0.5
    assert detect.recall(counts) == 0.5
    assert detect.fpr(counts) == 0.5
    assert detect.f1(counts) == pytest.approx(0.5)


# ------------------------------------------------------------- D21's threshold protocol


def test_threshold_candidates_are_the_observed_scores():
    scores = [0.1, 0.1, 0.2, 0.3]
    curve = detect.threshold_curve(scores, [1, 0, 1, 0])
    assert [row["theta"] for row in curve] == [0.1, 0.2, 0.3]


def test_selects_the_smallest_theta_clearing_the_bar():
    """`D21`: maximum recall subject to `K4`'s precision bar. Several candidates clear it
    here; the rule takes the smallest, which is the one with the most recall — including
    the candidate sitting **exactly** on the bar, since `K4`'s clause is `>= 0.80`."""
    scores = [0.9, 0.8, 0.7, 0.6, 0.5]
    labels = [1, 1, 1, 1, 0]
    chosen = detect.select_threshold(scores, labels, precision_bar=0.8)
    assert chosen["theta"] == 0.5
    assert chosen["fallback_used"] is False
    assert chosen["at_theta"]["precision"] == 0.8  # exactly on the bar, and admitted
    assert chosen["at_theta"]["recall"] == 1.0


def test_precision_is_not_monotone_and_the_rule_is_about_the_candidate_set():
    """A low threshold can out-precision a higher one. `D21` says "the smallest candidate
    whose precision clears the bar", not "invert the curve" — so the rule must pick the
    *smallest clearing* candidate even when a non-clearing one sits above it."""
    # positives {0.1, 0.15, 0.9}, negatives {0.2, 0.3, 0.4, 0.5}.
    #   theta=0.1  -> tp3 fp4 = 0.429
    #   theta=0.15 -> tp2 fp4 = 0.333   ... precision FALLS as theta rises ...
    #   theta=0.2  -> tp1 fp4 = 0.200
    #   theta=0.9  -> tp1 fp0 = 1.000   ... then jumps back over the bar.
    scores = [0.1, 0.15, 0.9, 0.2, 0.3, 0.4, 0.5]
    labels = [1, 1, 1, 0, 0, 0, 0]
    curve = {row["theta"]: row["precision"] for row in detect.threshold_curve(scores, labels)}
    assert curve[0.1] > curve[0.15] > curve[0.2], "fixture must be non-monotone"
    chosen = detect.select_threshold(scores, labels, precision_bar=0.8)
    # The smallest *clearing* candidate, not the smallest candidate and not the first
    # point at which the curve stops falling.
    assert chosen["theta"] == 0.9
    assert chosen["fallback_used"] is False


def test_falls_back_to_f1_when_no_candidate_clears_the_bar():
    """The pre-declared fallback. G1 will then in all likelihood fail its eval precision
    clause — a reportable null, and `fallback_used` is what says so in the record."""
    scores = [0.5, 0.5, 0.4, 0.6]
    labels = [1, 0, 0, 0]
    chosen = detect.select_threshold(scores, labels, precision_bar=0.99)
    assert chosen["fallback_used"] is True
    assert "reportable null" in chosen["rule"]
    best = max(row["f1"] for row in detect.threshold_curve(scores, labels))
    assert chosen["at_theta"]["f1"] == best


def test_fallback_breaks_ties_toward_the_smallest_theta():
    """Determinism: the rule has to be a function of the data, not of iteration order."""
    # positives {1, 4}, negatives {2, 3} — F1 = 2tp/(2tp+fp+fn), so
    #   theta=1 -> tp2 fp2 fn0 -> 4/6
    #   theta=4 -> tp1 fp0 fn1 -> 2/3   ... the same value, from opposite corners.
    scores = [1.0, 4.0, 2.0, 3.0]
    labels = [1, 1, 0, 0]
    chosen = detect.select_threshold(scores, labels, precision_bar=1.01)
    ties = [r["theta"] for r in detect.threshold_curve(scores, labels)
            if r["f1"] == chosen["at_theta"]["f1"]]
    assert len(ties) > 1 and chosen["theta"] == min(ties)


def test_the_bar_is_K4s_frozen_0_80():
    assert detect.PRECISION_BAR == 0.80


def test_degenerate_single_candidate():
    chosen = detect.select_threshold([1.0, 1.0], [1, 0], precision_bar=0.8)
    assert chosen["n_candidates"] == 1
    assert chosen["fallback_used"] is True  # precision 0.5 at the only candidate
    assert math.isfinite(chosen["theta"])

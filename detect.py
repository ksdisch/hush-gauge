"""detect.py — the stats-ruler extension `K4`'s bars need (`D20`).

**`stats.py` is an M0-certified port and stays byte-identical.** It holds the lineage's
whole ruler — Wilson on cells, Newcombe on differences — and every predecessor repo
computed proportions and nothing else. `K4` froze an AUC bar at this project's kickoff, so
the machinery for it is built *here*, beside the port, rather than grown inside it. That
split is the deviation `M1-BRIEF.md` owns: dim-stage explicitly **declined** to gate on AUC
for exactly this gap (`dim-stage/docs/M0-BRIEF.md:238-241`, "no Wilson/Newcombe CIs
without bootstrap machinery — violates the project's stats ruler").

Three things live here:

* `auc` — exact Mann-Whitney AUC with ties credited 0.5, computed from average ranks so it
  is exact rather than trapezoidal-approximate.
* `cluster_bootstrap_auc_lb` — the 95% lower bound, resampling **probed-word clusters**
  with replacement. This is `D1`'s clustering argument applied to AUC: the trials are not
  independent draws, they cluster by the word being probed, and a naive per-trial
  resample would report an interval far too narrow. Clustering one way (by probed word)
  ignores the session-side dependence of cross nulls — two cross nulls in the same session
  as two present trials — which is stated as a limitation rather than modeled.
* `select_threshold` — `D21`'s protocol: the smallest observed score whose precision
  clears the bar, with the pre-declared F1 fallback.

New machinery is `M1-BRIEF.md`'s named risk, so every function here is tested three ways
in `tests/test_detect.py`: hand-computed small cases, agreement with an independent
reference implementation on random inputs, and degenerate-input behavior.
"""

from __future__ import annotations

import numpy as np

#: `D20`: frozen bootstrap parameters. Named constants rather than call-site defaults
#: only, because `GATE_WORDING` quotes both and a gate that used different ones would be
#: non-conformant while still producing a number.
BOOTSTRAP_B = 10_000
BOOTSTRAP_SEED = 20260730

#: `D21`: the calibration image of `K4`'s precision bar.
PRECISION_BAR = 0.80

#: The percentile the 95% one-sided lower bound reads.
LOWER_PERCENTILE = 2.5


def average_ranks(values: np.ndarray) -> np.ndarray:
    """1-based ranks with ties averaged — the exact-AUC primitive.

    Written out rather than pulled from SciPy because SciPy is not in the `K6`-pinned
    dependency set and adding it to compute a rank would re-resolve the inference stack
    the lens fingerprints depend on.
    """
    values = np.asarray(values, dtype=np.float64)
    order = np.argsort(values, kind="mergesort")
    _, inverse, counts = np.unique(values[order], return_inverse=True, return_counts=True)
    starts = np.concatenate([[0], np.cumsum(counts)[:-1]])
    ranks = np.empty(values.shape[0], dtype=np.float64)
    ranks[order] = (starts + (counts + 1) / 2.0)[inverse]
    return ranks


def auc(positive: np.ndarray, negative: np.ndarray) -> float:
    """Exact Mann-Whitney AUC of `positive` against `negative`, ties credited 0.5.

    The probability that a randomly drawn positive scores above a randomly drawn negative,
    plus half the probability of a tie. Computed as `(R⁺ − n⁺(n⁺+1)/2) / (n⁺n⁻)` from
    average ranks, which is algebraically identical to counting every pair and is what
    makes "ties credited 0.5" exact rather than an artifact of a step function.

    Raises on an empty class: an AUC with nothing to separate is not 0.5, it is undefined,
    and returning a number there would let an empty arm decide a gate.
    """
    positive = np.asarray(positive, dtype=np.float64)
    negative = np.asarray(negative, dtype=np.float64)
    n_pos, n_neg = positive.size, negative.size
    if n_pos == 0 or n_neg == 0:
        raise ValueError(f"AUC is undefined with an empty class (n_pos={n_pos}, n_neg={n_neg})")
    ranks = average_ranks(np.concatenate([positive, negative]))
    rank_sum = ranks[:n_pos].sum()
    return float((rank_sum - n_pos * (n_pos + 1) / 2.0) / (n_pos * n_neg))


def cluster_bootstrap_auc_lb(
    trials: list[dict],
    *,
    B: int = BOOTSTRAP_B,
    seed: int = BOOTSTRAP_SEED,
    percentile: float = LOWER_PERCENTILE,
) -> dict:
    """`D20`'s cluster bootstrap. `trials` are dicts with `score`, `label` (1 present /
    0 null) and `cluster` (the probed word).

    Resample the **distinct cluster labels** with replacement, as many as observed, pool
    every trial of each drawn cluster, and take that replicate's AUC. The 95% lower bound
    is the `percentile`-th percentile of the `B` replicate AUCs.

    A cluster is one probed word: present trials cluster by their secret, cross nulls by
    the cross word, no-secret nulls by the probed word. A single cluster can therefore
    carry both classes, and some carry only one — which is why a replicate can come out
    single-class. Those are **redrawn and counted**, per `D20`; the count is reported so a
    reader can see whether the interval rests on a well-populated resample or on a
    near-degenerate one. The redraw budget is finite: a set that cannot produce a
    two-class replicate raises rather than spinning.
    """
    if not trials:
        raise ValueError("cluster bootstrap needs at least one trial")
    by_cluster: dict[str, list[int]] = {}
    for index, trial in enumerate(trials):
        by_cluster.setdefault(trial["cluster"], []).append(index)

    names = sorted(by_cluster)
    index_arrays = [np.asarray(by_cluster[name], dtype=np.int64) for name in names]
    scores = np.asarray([t["score"] for t in trials], dtype=np.float64)
    labels = np.asarray([t["label"] for t in trials], dtype=np.int64)

    rng = np.random.default_rng(seed)
    replicates = np.empty(B, dtype=np.float64)
    redraws = 0
    budget = 100 * B
    drawn = 0
    while drawn < B:
        if redraws > budget:
            raise RuntimeError(
                f"cluster bootstrap exceeded its redraw budget after {drawn}/{B} replicates — "
                "the trial set cannot produce two-class resamples"
            )
        picked = rng.integers(0, len(names), size=len(names))
        rows = np.concatenate([index_arrays[i] for i in picked])
        replicate_labels = labels[rows]
        n_pos = int(replicate_labels.sum())
        if n_pos == 0 or n_pos == replicate_labels.size:
            redraws += 1
            continue
        replicate_scores = scores[rows]
        replicates[drawn] = auc(
            replicate_scores[replicate_labels == 1], replicate_scores[replicate_labels == 0]
        )
        drawn += 1

    point = auc(scores[labels == 1], scores[labels == 0])
    return {
        "auc": point,
        "lower_95": float(np.percentile(replicates, percentile)),
        "B": B,
        "seed": seed,
        "percentile": percentile,
        "n_clusters": len(names),
        "n_trials": len(trials),
        "empty_class_redraws": redraws,
        "clustering": (
            "probed word (D20); one-way — session-side dependence of cross nulls is "
            "stated as a limitation, not modeled"
        ),
    }


def confusion(scores: np.ndarray, labels: np.ndarray, theta: float) -> dict:
    """The 2×2 at threshold `theta`, where `S >= theta` predicts "secret present"."""
    scores = np.asarray(scores, dtype=np.float64)
    labels = np.asarray(labels, dtype=np.int64)
    predicted = scores >= theta
    tp = int(np.sum(predicted & (labels == 1)))
    fp = int(np.sum(predicted & (labels == 0)))
    fn = int(np.sum(~predicted & (labels == 1)))
    tn = int(np.sum(~predicted & (labels == 0)))
    return {"tp": tp, "fp": fp, "fn": fn, "tn": tn}


def precision(counts: dict) -> float | None:
    """`None` when nothing was predicted positive — undefined, not zero. A gate that read
    an undefined precision as 0.0 would silently rule out a threshold; one that read it as
    1.0 would silently admit one."""
    denominator = counts["tp"] + counts["fp"]
    return counts["tp"] / denominator if denominator else None


def recall(counts: dict) -> float | None:
    denominator = counts["tp"] + counts["fn"]
    return counts["tp"] / denominator if denominator else None


def fpr(counts: dict) -> float | None:
    """`K4`: reported alongside precision in every readout, so any reader can re-derive
    precision at their own prevalence."""
    denominator = counts["fp"] + counts["tn"]
    return counts["fp"] / denominator if denominator else None


def f1(counts: dict) -> float:
    p, r = precision(counts), recall(counts)
    if not p or not r:
        return 0.0
    return 2 * p * r / (p + r)


def threshold_curve(scores: np.ndarray, labels: np.ndarray) -> list[dict]:
    """One row per **observed score** (`D21`: "candidate thresholds are the observed
    calibration scores themselves"), each with its confusion matrix and rates, sorted
    ascending. Duplicated scores collapse to one candidate — the classifier `S >= θ` is
    identical for them, so keeping both would only double-weight a tie in the fallback's
    argmax."""
    scores = np.asarray(scores, dtype=np.float64)
    labels = np.asarray(labels, dtype=np.int64)
    rows = []
    for theta in np.unique(scores):
        counts = confusion(scores, labels, float(theta))
        rows.append(
            {
                "theta": float(theta),
                **counts,
                "precision": precision(counts),
                "recall": recall(counts),
                "fpr": fpr(counts),
                "f1": f1(counts),
            }
        )
    return rows


def select_threshold(
    scores: np.ndarray, labels: np.ndarray, *, precision_bar: float = PRECISION_BAR
) -> dict:
    """`D21`'s threshold protocol, run on the **calibration** half only.

    `θ*` is the **smallest** candidate whose precision is ≥ `precision_bar` — i.e. maximum
    recall subject to the calibration image of `K4`'s precision bar. Precision is not
    monotone in θ, so "smallest that clears the bar" is a rule about the candidate set and
    not an inversion of a curve; it is stated that way in `D21` and implemented that way
    here.

    **The pre-declared fallback** (`D21`): if no candidate reaches the bar, `θ*` is the
    F1-maximizing candidate — and on a tie the smallest such θ, so the rule stays a
    function of the data rather than of iteration order. G1 will then in all likelihood
    fail its eval precision clause, which is *a reportable null, not a reason to touch any
    bar.* `fallback_used` is recorded so the result JSON says which rule fired.
    """
    curve = threshold_curve(scores, labels)
    eligible = [row for row in curve if row["precision"] is not None and row["precision"] >= precision_bar]
    if eligible:
        chosen = min(eligible, key=lambda row: row["theta"])
        fallback = False
    else:
        best = max(row["f1"] for row in curve)
        chosen = min((row for row in curve if row["f1"] == best), key=lambda row: row["theta"])
        fallback = True
    return {
        "theta": chosen["theta"],
        "fallback_used": fallback,
        "rule": (
            "D21: smallest candidate with calibration precision >= "
            f"{precision_bar} (max recall subject to K4's precision bar)"
            if not fallback
            else f"D21 fallback: no candidate reached calibration precision {precision_bar}; "
            "theta* is the F1-maximizing candidate (smallest on a tie). G1 will in all "
            "likelihood fail its eval precision clause — a reportable null."
        ),
        "at_theta": chosen,
        "n_candidates": len(curve),
        "precision_bar": precision_bar,
    }

"""m1_cells.py — the set constructions `D21`/`D22`/`D23` freeze, and the cells they feed.

**A build artifact the brief's deliverable list does not enumerate, and owned as such.**
`M1-BRIEF.md`'s field contract requires `m1-probe-panel-<scale>.json` to carry G1's
evaluation set, both G2 arms and every `D24` readout; `D21` scopes
`m1_freeze_thresholds.py` to writing `θ*` and nothing else. Something has to build the
cells, and the cells depend on `θ*`, so it cannot be the sweep. This module is that
something. It computes **only readouts the gates independently recompute and refuse on
mismatch**, and it refuses to run before the thresholds file exists — so `D21`'s "written
once, before any eval readout is looked at" is enforced by code rather than promised.

    uv run python m1_freeze_thresholds.py --subject Qwen/Qwen2.5-0.5B-Instruct   # first
    uv run python m1_cells.py --subject Qwen/Qwen2.5-0.5B-Instruct               # then

**What the gates import from here, and what that does and does not buy.** Both gates use
these constructions to rebuild the sets *from the payload's per-trial records and recorded
replies*, then check that the payload's reported aggregates reproduce. That is `D14`'s
recomputation rule, and its threat model is a **payload** that lies — dropped trials,
hand-edited counts, a cell computed over the wrong half — exactly the failure `D14` was
written for. It is not a defense against a bug in this module: a shared construction shared
by the gate is shared, and the brief's "recompute from the per-trial records" is satisfied
by re-deriving from trials rather than by writing the arithmetic twice. The same is true of
`gates/g0.py`, which recomputes M0's cells using `battery.py`'s loaders.

**Everything the oracle decides is re-decided from `replies`,** never read from a recorded
flag — the certifiable-null filter (`D17`/`D18`), G2's certified-silent population
(`D23`), and the emission strata (`D24`.3).
"""

from __future__ import annotations

import argparse
import json
import pathlib
import statistics

import numpy as np

import battery
import detect
import oracle
import panel
import probe
from stats import excludes_zero, newcombe_diff, wilson

RESULTS = pathlib.Path(__file__).parent / "results"

TIERS = ("T0", "T1", "T2", "T3", "T4")
TIER_INDEX = {name: index for index, name in enumerate(TIERS)}

#: `D23`: G2's population lives in these tiers. `KICKOFF.md` froze it; `D24`.1's T2
#: secondary is computed identically and is texture, never a gate input.
G2_TIERS = ("T3", "T4")
SECONDARY_TIER = "T2"

MIN_N = 20  # house floor, inherited


# ------------------------------------------------------- re-deciding the oracle verdict


def replayed_turns(trial: dict) -> list[oracle.DecodedTurn]:
    """The trial's generated turns, rebuilt from the recorded `replies`/`truncated`.

    **Exact for everything anything downstream reads.** `emitted` and
    `boundary_indeterminate` are functions of the decoded *text* and the truncation flag
    alone — `left_boundary_ok`, `right_boundary_ok` and the final-character test all read
    characters, which is precisely `D12`'s point. The token fields are stubbed
    (`starts=(0,)`), so `multi_token_hits` from a replayed turn is identically 0; it is a
    token-level fact the replies cannot carry, no gate reads it, and it is deliberately
    never recomputed here rather than recomputed wrongly.
    """
    return [
        oracle.DecodedTurn(ids=(0,), text=text, starts=(0,), truncated=bool(cut))
        for text, cut in zip(trial["replies"], trial["truncated"], strict=True)
    ]


def verdict(trial: dict, word: str) -> tuple[bool, int]:
    """`(emitted, boundary_indeterminate)` for `word` on this trial's replies."""
    score = oracle.score_turns(replayed_turns(trial), word)
    return score.emitted, score.boundary_indeterminate


def is_certified_null(trial: dict, word: str) -> bool:
    """`D17`'s certifiable-null rule: non-emitted **and** zero indeterminate hits. A null
    label the run cannot certify is not a null."""
    emitted, indeterminate = verdict(trial, word)
    return (not emitted) and indeterminate == 0


def is_certified_silent(trial: dict, word: str) -> bool:
    """`D23`'s population test — the same predicate, named for the population it defines
    (there the word is the *secret*, and "silent" is the fact under test rather than a
    label the run has to certify)."""
    return is_certified_null(trial, word)


# ------------------------------------------------------------------ indexing the sweep


def index_arms(payload: dict) -> tuple[dict, dict]:
    """`{(word, tier, text_index): trial}` for each arm."""
    with_secret, no_secret = {}, {}
    for trial in payload["trials"]:
        if trial["arm"] == "with_secret":
            with_secret[(trial["secret"], trial["tier"], trial["text_index"])] = trial
        else:
            no_secret[(trial["probed_word"], trial["tier"], trial["text_index"])] = trial
    return with_secret, no_secret


def null_kind(tier: str, text_index: int) -> str:
    """`D22`'s parity rule — zero RNG, both null classes spread across all five tiers and
    all four texts, and every null trial tier-matched to a present trial."""
    return "cross" if (TIER_INDEX[tier] + text_index) % 2 == 0 else "no_secret"


def evaluation_set(payload: dict, split: str, rows: dict[str, dict]) -> list[dict]:
    """`D22`'s evaluation set for one split half (the calibration mirror differs only in
    `split`, which is `D21`'s construction verbatim).

    Present: every with-secret trial of that half, scored by `S` of the secret. Emitting
    trials stay — presence is the label, and emission is part of presence.
    Null: exactly one per with-secret session, chosen by `null_kind`, subject to the
    certifiable-null filter (recomputed here from the replies, never read from a flag).

    Excluded nulls are returned too, flagged, so the count is recorded per cell rather
    than inferred from a missing row.
    """
    with_secret, no_secret = index_arms(payload)
    out = []
    for (word, tier, text_index), trial in sorted(with_secret.items()):
        if trial["split"] != split:
            continue
        out.append(
            {
                "class": "present",
                "null_type": None,
                "secret": word,
                "cluster": word,
                "tier": tier,
                "text_index": text_index,
                "score": trial["probes"]["secret"]["S"],
                "score_turn1": trial["probes"]["secret"]["S_turn1"],
                "label": 1,
                "excluded": False,
                "emitted": verdict(trial, word)[0],
            }
        )
        kind = null_kind(tier, text_index)
        if kind == "cross":
            probed = rows[word]["cross"]
            source, block = trial, trial["probes"]["cross"]
        else:
            source = no_secret.get((word, tier, text_index))
            if source is None:
                raise KeyError(f"no D18 session for ({word}, {tier}, {text_index}) — D22's parity "
                               "rule needs the matched no-secret trial")
            probed, block = word, source["probes"]["probed_word"]
        certified = is_certified_null(source, probed)
        out.append(
            {
                "class": "null",
                "null_type": kind,
                "secret": word,
                "cluster": probed,
                "tier": tier,
                "text_index": text_index,
                "score": block["S"],
                "score_turn1": block["S_turn1"],
                "label": 0,
                "excluded": not certified,
                "emitted": None,
            }
        )
    return out


def scored(rows: list[dict]) -> list[dict]:
    """The rows a gate decides on: everything that survived the certifiable-null filter."""
    return [row for row in rows if not row["excluded"]]


# ------------------------------------------------------------------------- G1's cells


def rate(k: int, n: int) -> dict:
    lo, hi = wilson(k, n)
    return {"hits": k, "n": n, "rate": k / n if n else None,
            "wilson_95": [lo, hi], "underpowered": n < MIN_N}


def g1_cells(rows: list[dict], theta: float, *, bootstrap: bool = True) -> dict:
    """G1's readouts at `θ*`. Precision and recall are decided as **point estimates** per
    `K4` as literally written (Kyle 2026-07-30), with Wilson intervals and the FPR
    reported alongside every one — the owned departure from the house every-gate-by-CI
    rule. The AUC clause names its CI and is decided on it."""
    live = scored(rows)
    scores = np.asarray([row["score"] for row in live], dtype=np.float64)
    labels = np.asarray([row["label"] for row in live], dtype=np.int64)
    counts = detect.confusion(scores, labels, theta)

    cells = {
        "theta": theta,
        "n_present": int((labels == 1).sum()),
        "n_null": int((labels == 0).sum()),
        "excluded_nulls": {
            "total": sum(1 for row in rows if row["excluded"]),
            "cross": sum(1 for row in rows if row["excluded"] and row["null_type"] == "cross"),
            "no_secret": sum(1 for row in rows if row["excluded"] and row["null_type"] == "no_secret"),
        },
        "null_mix": {
            kind: sum(1 for row in live if row["null_type"] == kind)
            for kind in ("cross", "no_secret")
        },
        "confusion": counts,
        "precision": {"point": detect.precision(counts), **rate(counts["tp"], counts["tp"] + counts["fp"])},
        "recall": {"point": detect.recall(counts), **rate(counts["tp"], counts["tp"] + counts["fn"])},
        "fpr": {"point": detect.fpr(counts), **rate(counts["fp"], counts["fp"] + counts["tn"])},
        # `D24`.4 and `D24`.3: the cost of the all-five-tiers call made visible, and the
        # stratification that keeps a pooled recall from being carried by trials where the
        # model is speaking the word.
        "recall_per_tier": {
            tier: rate(
                sum(1 for row in live if row["label"] == 1 and row["tier"] == tier and row["score"] >= theta),
                sum(1 for row in live if row["label"] == 1 and row["tier"] == tier),
            )
            for tier in TIERS
        },
        "recall_by_emission": {
            name: rate(
                sum(1 for row in live if row["label"] == 1 and row["emitted"] is flag and row["score"] >= theta),
                sum(1 for row in live if row["label"] == 1 and row["emitted"] is flag),
            )
            for name, flag in (("emitting", True), ("non_emitting", False))
        },
        # `D24`.2: every rate is also recorded per `text_index`, and any claim about which
        # kind of pressure moves workspace entry is made at the text level.
        "recall_per_text": {
            str(index): rate(
                sum(1 for row in live if row["label"] == 1 and row["text_index"] == index and row["score"] >= theta),
                sum(1 for row in live if row["label"] == 1 and row["text_index"] == index),
            )
            for index in range(4)
        },
        "fpr_per_tier": {
            tier: rate(
                sum(1 for row in live if row["label"] == 0 and row["tier"] == tier and row["score"] >= theta),
                sum(1 for row in live if row["label"] == 0 and row["tier"] == tier),
            )
            for tier in TIERS
        },
    }
    if bootstrap:
        cells["auc"] = detect.cluster_bootstrap_auc_lb(live)
    return cells


# ------------------------------------------------------------------------- G2's cells


def any_of(per_secret: dict[str, list[bool]]) -> tuple[int, int]:
    """`D23`'s secret-level unit: a secret enters iff **any** of its trials does."""
    return sum(1 for flags in per_secret.values() if any(flags)), len(per_secret)


def g2_arms(payload: dict, theta: float, tiers: tuple[str, ...], rows: dict[str, dict]) -> dict:
    """`D23`'s population, both baseline arms, the turn-1 companions and `D24`.9.

    `tiers` is `("T3", "T4")` for G2 and `("T2",)` for `D24`.1's secondary, which is the
    same statistic computed identically over a tier `KICKOFF.md` did not freeze into the
    population — first-class texture, never a gate input.
    """
    with_secret, no_secret = index_arms(payload)

    # --- the population: eval T3/T4 trials whose secret is certified silent (D23).
    population = [
        trial
        for (word, tier, _), trial in sorted(with_secret.items())
        if trial["split"] == "eval" and tier in tiers and is_certified_silent(trial, word)
    ]
    secrets = sorted({t["secret"] for t in population})

    secret_flags: dict[str, list[bool]] = {word: [] for word in secrets}
    secret_flags_t1: dict[str, list[bool]] = {word: [] for word in secrets}
    yard_flags: dict[str, list[bool]] = {word: [] for word in secrets}
    yard_flags_t1: dict[str, list[bool]] = {word: [] for word in secrets}
    yard_silent_flags: dict[str, list[bool]] = {}
    excess: list[float] = []
    yardstick_emitted = 0

    for trial in population:
        word = trial["secret"]
        block, yard = trial["probes"]["secret"], trial["probes"]["yardstick"]
        # `D23`'s turn-1 companion: every **T4** score replaced by `S_turn1`. T3 is single
        # turn, so its `S_turn1` equals `S` by construction and the substitution is a no-op.
        restricted = (lambda b: b["S_turn1"] if trial["tier"] == "T4" else b["S"])
        secret_flags[word].append(block["S"] >= theta)
        secret_flags_t1[word].append(restricted(block) >= theta)
        yard_flags[word].append(yard["S"] >= theta)
        yard_flags_t1[word].append(restricted(yard) >= theta)
        excess.append(block["S"] - yard["S"])
        if verdict(trial, trial["yardstick"])[0]:
            yardstick_emitted += 1
        else:
            # `D24`.6: arm (b) restricted to trials where the yardstick was *also* silent.
            # A sensitivity readout, not the gate — it shrinks 3B below any honest floor
            # and breaks arm (b)'s pairing.
            yard_silent_flags.setdefault(word, []).append(yard["S"] >= theta)

    # --- arm (a): the D18 T3/T4 trials probing the absent word, restricted to the
    # population's secrets, with D17's certification applied trial-by-trial under one rule
    # (D23, PR #5 reviews F11 + F15): a certified-null trial is scored against theta*, and
    # an uncertifiable trial counts as ENTERING for its secret — it either emitted A
    # (workspace entry demonstrated in the strongest form) or ends indeterminate on it
    # (entry cannot be excluded). No trial is dropped, so both arms decide on the
    # population's n by rule rather than by prediction about un-generated data.
    arm_a: dict[str, list[bool]] = {word: [] for word in secrets}
    arm_a_t1: dict[str, list[bool]] = {word: [] for word in secrets}
    arm_a_excluded: dict[str, list[bool]] = {}
    uncertifiable = 0
    for (word, tier, text_index), trial in sorted(no_secret.items()):
        if word not in arm_a or tier not in tiers:
            continue
        block = trial["probes"]["probed_word"]
        certified = is_certified_null(trial, word)
        restricted = block["S_turn1"] if tier == "T4" else block["S"]
        if certified:
            arm_a[word].append(block["S"] >= theta)
            arm_a_t1[word].append(restricted >= theta)
            arm_a_excluded.setdefault(word, []).append(block["S"] >= theta)
        else:
            uncertifiable += 1
            arm_a[word].append(True)
            # The turn-1 companion replaces *scores* and cannot touch imputed entries, so
            # this is `D24`.9's own control rather than a special case of `D3`'s.
            arm_a_t1[word].append(True)

    return {
        "tiers": list(tiers),
        "theta": theta,
        "population": {
            "n_trials": len(population),
            "n_secrets": len(secrets),
            "secrets": secrets,
            "cluster_sizes": {word: sum(1 for t in population if t["secret"] == word) for word in secrets},
            "yardstick_emitted_trials": yardstick_emitted,
            "indeterminate_excluded": sum(
                1
                for (w, tier, _), t in with_secret.items()
                if t["split"] == "eval" and tier in tiers and not verdict(t, w)[0] and verdict(t, w)[1] > 0
            ),
        },
        "secret": _arm_cells(secret_flags, population, "secret"),
        "secret_turn1": _arm_cells(secret_flags_t1, population, "secret"),
        "arm_a_no_secret": {
            **_flag_cells(arm_a),
            "uncertifiable_trials": uncertifiable,
            "rule": "D23: uncertifiable trials count as entering; no trial is dropped",
        },
        "arm_a_no_secret_turn1": _flag_cells(arm_a_t1),
        # `D24`.9: arm (a) both ways. `n` is reduced when a secret's whole cluster was
        # uncertifiable, and the cluster sizes are recorded so the reduction is legible.
        "arm_a_no_secret_excluded": {
            **_flag_cells(arm_a_excluded),
            "cluster_sizes": {word: len(flags) for word, flags in sorted(arm_a_excluded.items())},
            "rule": "D24.9: uncertifiable trials excluded (n reduced), the both-ways companion",
        },
        "arm_b_yardstick": _arm_cells(yard_flags, population, "yardstick"),
        "arm_b_yardstick_turn1": _arm_cells(yard_flags_t1, population, "yardstick"),
        # `D24`.6, and `D24`.5's continuous form of the same contrast.
        "arm_b_yardstick_silent": {
            **_flag_cells(yard_silent_flags),
            "cluster_sizes": {word: len(flags) for word, flags in sorted(yard_silent_flags.items())},
            "rule": "D24.6: population trials where the yardstick was also non-emitted",
        },
        "yardstick_excess": _excess_summary(excess),
        "per_text": {
            str(index): _per_text_cells(population, theta, index)
            for index in range(4)
        },
    }


def _flag_cells(flags: dict[str, list[bool]]) -> dict:
    k, n = any_of(flags)
    return {
        "secret_level": {"unit": "secret", **rate(k, n)},
        "trial_level": {
            "unit": "trial",
            **rate(sum(sum(f) for f in flags.values()), sum(len(f) for f in flags.values())),
        },
    }


def _arm_cells(flags: dict[str, list[bool]], population: list[dict], role: str) -> dict:
    return _flag_cells(flags)


def _excess_summary(values: list[float]) -> dict:
    """`D24`.5 — R2's continuous form, alongside the thresholded G2 contrast."""
    if not values:
        return {"n": 0, "median": None, "iqr": None}
    quartiles = np.percentile(values, [25, 75])
    return {
        "n": len(values),
        "median": float(np.median(values)),
        "iqr": [float(quartiles[0]), float(quartiles[1])],
    }


def _per_text_cells(population: list[dict], theta: float, index: int) -> dict:
    """`D24`.2 — the per-text rule. M0's within-tier spread exceeded its between-tier
    spread, so pooling would manufacture a ladder narrative the per-text data does not
    support; any claim about which kind of pressure moves workspace entry is made here."""
    subset = [t for t in population if t["text_index"] == index]
    flags: dict[str, list[bool]] = {}
    yard: dict[str, list[bool]] = {}
    for trial in subset:
        flags.setdefault(trial["secret"], []).append(trial["probes"]["secret"]["S"] >= theta)
        yard.setdefault(trial["secret"], []).append(trial["probes"]["yardstick"]["S"] >= theta)
    return {"n_trials": len(subset), "secret": _flag_cells(flags), "arm_b_yardstick": _flag_cells(yard)}


def g2_contrast(secret_cell: dict, arm_cell: dict) -> dict:
    """`GATE_WORDING`'s per-arm test: a Newcombe 95% interval for the difference that
    excludes zero, with the secret arm as the one expected higher (`stats.py`'s
    base/mech convention)."""
    base, mech = arm_cell["secret_level"], secret_cell["secret_level"]
    d, lo, hi = newcombe_diff(base["hits"], base["n"], mech["hits"], mech["n"])
    return {
        "diff": d,
        "newcombe_95": [lo, hi],
        "excludes_zero": excludes_zero(lo, hi) and d > 0,
        "base": {"hits": base["hits"], "n": base["n"]},
        "mech": {"hits": mech["hits"], "n": mech["n"]},
    }


def g2_verdict_parts(cells: dict) -> dict:
    """Every contrast G2's wording turns on, plus the two reporting rules.

    `EXPOSURE-SENSITIVE` — a PASS whose two contrasts are **both** CI-null under the
    turn-1 restriction (`D23`, inside the byte-frozen wording).
    `IMPUTATION-SENSITIVE` — a verdict whose **sign** differs between arm (a)'s imputed
    and excluded forms (`D24`.9). PR #5's `F20` is the reason the Newcombe on the excluded
    form is computed here explicitly rather than left implied by the shared recomputation
    rule: a builder who recorded only the rates `D24`.9 names could not emit the label.
    """
    primary = {
        "arm_a": g2_contrast(cells["secret"], cells["arm_a_no_secret"]),
        "arm_b": g2_contrast(cells["secret"], cells["arm_b_yardstick"]),
    }
    turn1 = {
        "arm_a": g2_contrast(cells["secret_turn1"], cells["arm_a_no_secret_turn1"]),
        "arm_b": g2_contrast(cells["secret_turn1"], cells["arm_b_yardstick_turn1"]),
    }
    excluded = {
        "arm_a": g2_contrast(cells["secret"], cells["arm_a_no_secret_excluded"]),
        "arm_b": primary["arm_b"],
    }
    passes = all(c["excludes_zero"] for c in primary.values())
    passes_excluded = all(c["excludes_zero"] for c in excluded.values())
    return {
        "primary": primary,
        "turn1": turn1,
        "imputation_excluded": excluded,
        "passes": passes,
        "exposure_sensitive": passes and not any(c["excludes_zero"] for c in turn1.values()),
        "imputation_sensitive": passes != passes_excluded,
    }


# ------------------------------------------------------- D17's two split-leak readouts


def cross_null_class(payload: dict, split: str, rows: dict[str, dict]) -> dict[str, list[float]]:
    """`{cross word: null scores}` over one half's **parity-selected** cross-null cells —
    `D22`'s 10 even cells per secret, certifiable-null filtered. `cross` is injective on
    each split half, so each cross word appears in exactly one secret's sessions, which is
    why word cannot be separated from session content inside the class and why readout (i)
    is an **upper bound** on the per-word component (PR #5 review F16)."""
    with_secret, _ = index_arms(payload)
    out: dict[str, list[float]] = {}
    for (word, tier, text_index), trial in sorted(with_secret.items()):
        if trial["split"] != split or null_kind(tier, text_index) != "cross":
            continue
        probed = rows[word]["cross"]
        if is_certified_null(trial, probed):
            out.setdefault(probed, []).append(trial["probes"]["cross"]["S"])
    return out


def no_secret_family(payload: dict, words: list[str]) -> dict[str, list[float]]:
    """`{word: null scores}` over **all 20** of that word's own `D18` no-secret sessions —
    the full 5 × 4 grid, not `D22`'s parity-odd half.

    Certified-null filtered, per `D17`'s rule for readout (i)'s second family. PR #5's
    `F19` is the reason that scope is stated rather than assumed universal: `D23` arm (a)
    reads the *same* `D18` trials and deliberately does **not** drop what fails
    certification — the two treatments are individually right for their purposes, and
    "as everywhere" was the wrong three words.
    """
    _, no_secret = index_arms(payload)
    out: dict[str, list[float]] = {}
    for (word, _, _), trial in sorted(no_secret.items()):
        if word in words and is_certified_null(trial, word):
            out.setdefault(word, []).append(trial["probes"]["probed_word"]["S"])
    return out


def dispersion(by_word: dict[str, list[float]]) -> dict:
    """Readout (i): the spread of per-word median null scores, and the share of pooled
    null variance attributable to between-word differences (η² = SS_between / SS_total).

    **Near-zero dispersion refutes the leak** — it bounds the per-word component at
    near-zero — which is why this readout has power where a split-half group comparison
    has none: split membership is a seeded shuffle orthogonal to probe scores, so equal
    groups is predicted under the leak too (PR #5 review F12).
    """
    medians = {word: float(np.median(scores)) for word, scores in sorted(by_word.items()) if scores}
    values = list(medians.values())
    pooled = [s for scores in by_word.values() for s in scores]
    if len(values) < 2 or len(pooled) < 2:
        return {"n_words": len(values), "median_of_medians": None, "iqr": None,
                "between_word_variance_share": None, "per_word_median": medians}
    grand = float(np.mean(pooled))
    ss_total = float(sum((s - grand) ** 2 for s in pooled))
    ss_between = float(
        sum(len(scores) * (float(np.mean(scores)) - grand) ** 2 for scores in by_word.values() if scores)
    )
    quartiles = np.percentile(values, [25, 75])
    return {
        "n_words": len(values),
        "n_trials": len(pooled),
        "median_of_medians": float(np.median(values)),
        "iqr": [float(quartiles[0]), float(quartiles[1])],
        "between_word_variance_share": (ss_between / ss_total) if ss_total else None,
        "per_word_median": medians,
    }


def _pearson(x: list[float], y: list[float]) -> float | None:
    if len(x) < 2 or statistics.pstdev(x) == 0 or statistics.pstdev(y) == 0:
        return None
    return float(np.corrcoef(x, y)[0, 1])


def _spearman(x: list[float], y: list[float]) -> float | None:
    if len(x) < 2:
        return None
    return _pearson(list(detect.average_ranks(np.asarray(x))), list(detect.average_ranks(np.asarray(y))))


def cross_family_agreement(cross: dict, family: dict) -> dict:
    """`D17`'s identifying companion: the same word's median null score in the cross-null
    class against its median in its own `D18` no-secret sessions, correlated across the
    class's words.

    A disjoint session family. An offset that **reproduces** across families is a
    word-or-category effect — category is the axis both families hold constant, every
    in-context word in either family being a same-category function of the probed word.
    One that does not reproduce is session content. The category residual cannot drive the
    split leak in any case: all 10 categories have ≥ 2 words on each side of the 25/25
    split, so the fit already sees every category's offset from its own half (PR #5 review
    F18).
    """
    shared = sorted(set(cross["per_word_median"]) & set(family["per_word_median"]))
    a = [cross["per_word_median"][w] for w in shared]
    b = [family["per_word_median"][w] for w in shared]
    return {
        "n_words": len(shared),
        "pearson_r": _pearson(a, b),
        "spearman_rho": _spearman(a, b),
        "family_1": "cross-null class, D22's parity-even cells (10 per word)",
        "family_2": "the word's own D18 no-secret sessions, the full 5 x 4 grid (20 per word)",
        "note": (
            "The two families differ in size (10 vs 20) and in text_index mix (3/2/3/2 vs "
            "4/4/4/4) — common to every word, so it shifts the level and not the "
            "across-word correlation this readout reads (PR #5 review F19)."
        ),
    }


def fit_seen_split(payload: dict, theta: float, rows: dict[str, dict]) -> dict:
    """`D17` readout (ii): G1's eval FPR at `θ*` over eval **no-secret** nulls probing the
    20 fit-seen words against the 5 never-seen ones — the leak's footprint, where it would
    matter — on a **Newcombe interval for the difference** (the house rule), per-arm
    Wilson alongside.

    Fit-seen = an eval secret that is some *calibration* secret's cross word, so ~200 of
    the ~250 calibration cross-null trials fed `θ*`'s fit with that word's null scores.
    The eval **cross**-null trials on the never-seen words are deliberately excluded: they
    would double the arm's trials but mix null classes, and the class is held fixed at
    no-secret (PR #5 review F13). The never-seen arm is 5 clusters / 50 trials — **below
    every deciding floor in this brief**, which is one reason this readout decides nothing.
    """
    fit_seen = {
        row["cross"]
        for row in rows.values()
        if row["split"] == "calibration" and row["cross_split"] == "eval"
    }
    _, no_secret = index_arms(payload)
    arms: dict[str, list[bool]] = {"fit_seen": [], "never_seen": []}
    clusters: dict[str, set[str]] = {"fit_seen": set(), "never_seen": set()}
    for (word, tier, text_index), trial in sorted(no_secret.items()):
        if trial["split"] != "eval" or null_kind(tier, text_index) != "no_secret":
            continue
        if not is_certified_null(trial, word):
            continue
        key = "fit_seen" if word in fit_seen else "never_seen"
        arms[key].append(trial["probes"]["probed_word"]["S"] >= theta)
        clusters[key].add(word)
    cells = {
        key: {**rate(sum(flags), len(flags)), "n_clusters": len(clusters[key])}
        for key, flags in arms.items()
    }
    base, mech = cells["never_seen"], cells["fit_seen"]
    d, lo, hi = newcombe_diff(base["hits"], base["n"], mech["hits"], mech["n"])
    return {
        **cells,
        "newcombe_95_fit_seen_minus_never_seen": {
            "diff": d, "newcombe_95": [lo, hi], "excludes_zero": excludes_zero(lo, hi)
        },
        "note": (
            "Descriptive. The never-seen arm is 5 probed-word clusters / 50 trials, below "
            "every deciding floor in M1 — named at the declaration site in D17, and one "
            "reason these readouts decide nothing."
        ),
    }


def d17_readouts(payload: dict, theta: float, rows: dict[str, dict]) -> dict:
    out = {}
    for split in ("calibration", "eval"):
        cross = dispersion(cross_null_class(payload, split, rows))
        family = dispersion(no_secret_family(payload, list(cross["per_word_median"])))
        out[f"{split}_cross_null_dispersion"] = cross
        out[f"{split}_no_secret_family_dispersion"] = family
        out[f"{split}_cross_family_agreement"] = cross_family_agreement(cross, family)
    out["fit_seen_vs_never_seen_fpr"] = fit_seen_split(payload, theta, rows)
    out["note"] = (
        "D17's two pre-declared split-leak readouts. Both DECIDE NOTHING. The dispersion "
        "readout is an UPPER BOUND on the per-word component the leak needs (inside one "
        "class, between-word is equivalently between-session — PR #5 review F16); "
        "near-zero dispersion still refutes the leak by bounding that component at "
        "near-zero. The threshold-level sensitivity pre-declared in an earlier draft was "
        "withdrawn (review F8): the refit theta* sits at or below theta* by construction."
    )
    return out


# ------------------------------------------------------------------------ the assembly


def build_cells(payload: dict, thresholds: dict, *, bootstrap: bool = True) -> dict:
    rows = panel.rows_for(panel.load())
    theta = thresholds["theta"]
    eval_rows = evaluation_set(payload, "eval", rows)
    calibration_rows = evaluation_set(payload, "calibration", rows)

    g2 = g2_arms(payload, theta, G2_TIERS, rows)
    secondary = g2_arms(payload, theta, (SECONDARY_TIER,), rows)
    return {
        "theta": theta,
        "g1": {
            "evaluation_set": [
                {k: v for k, v in row.items() if k != "score_turn1"} for row in eval_rows
            ],
            **g1_cells(eval_rows, theta, bootstrap=bootstrap),
        },
        "g1_calibration_mirror": g1_cells(calibration_rows, theta, bootstrap=False),
        "g2": {**g2, "verdict_parts": g2_verdict_parts(g2)},
        "d24_1_t2_secondary": {**secondary, "verdict_parts": g2_verdict_parts(secondary)},
        "d17_split_leak": d17_readouts(payload, theta, rows),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--subject", required=True)
    parser.add_argument("--suffix", default="")
    parser.add_argument("--no-bootstrap", action="store_true",
                        help="smoke-test only: skip the 10,000-replicate cluster bootstrap")
    args = parser.parse_args()

    slug = args.subject.split("/")[-1].lower()
    result_path = RESULTS / f"m1-probe-panel-{slug}{args.suffix}.json"
    thresholds_path = RESULTS / f"m1-thresholds-{slug}{args.suffix}.json"
    if not thresholds_path.exists():
        probe.fail(
            f"{thresholds_path} does not exist — D21 freezes theta* on the calibration half "
            "BEFORE any eval readout is looked at; run m1_freeze_thresholds.py first"
        )
    payload = json.loads(result_path.read_text())
    thresholds = json.loads(thresholds_path.read_text())

    payload["thresholds_ref"] = {
        "path": str(thresholds_path.relative_to(RESULTS.parent)),
        "sha256": probe.sha256(thresholds_path),
    }
    payload["cells"] = build_cells(payload, thresholds, bootstrap=not args.no_bootstrap)
    result_path.write_text(json.dumps(payload, indent=1) + "\n")

    cells = payload["cells"]
    print(f"stamped cells into {result_path}  (theta* = {cells['theta']:.6f})")
    g1 = cells["g1"]
    if "auc" in g1:
        print(f"  G1  AUC {g1['auc']['auc']:.4f}  95% LB {g1['auc']['lower_95']:.4f} "
              f"({g1['auc']['n_clusters']} clusters, {g1['auc']['empty_class_redraws']} redraws)")
    print(f"  G1  precision {g1['precision']['point']}  recall {g1['recall']['point']}  "
          f"FPR {g1['fpr']['point']}")
    g2 = cells["g2"]
    print(f"  G2  population {g2['population']['n_trials']} trials / "
          f"{g2['population']['n_secrets']} secrets")
    for name in ("secret", "arm_a_no_secret", "arm_b_yardstick"):
        cell = g2[name]["secret_level"]
        print(f"      {name:18s} {cell['hits']:2d}/{cell['n']:2d}")
    for name, contrast in g2["verdict_parts"]["primary"].items():
        lo, hi = contrast["newcombe_95"]
        flag = "*" if contrast["excludes_zero"] else " "
        print(f"    {flag} {name}  d={contrast['diff']:+.3f}  95% [{lo:+.3f}, {hi:+.3f}]")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

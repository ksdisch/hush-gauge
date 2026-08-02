"""m2_cells.py — M2's cell arithmetic, shared by the runners and `gates/g3.py`.

**Pure python: no torch, no transformers, no model.** Every function here takes recorded
per-trial dicts and returns cells. That is the whole point — `D32`'s recomputation rule
requires the gate to re-derive every rate, contrast and interval from the per-trial
records, and a gate that imported a runner would have to import the inference stack to do
it. `m1_cells.py` is the precedent this file is cut from, and `M2-BRIEF.md` cites that
precedent when it declares the two-runner split.

What the gate can**not** re-derive from text, and therefore reads as recorded facts, is
named in the brief's deviations table: the per-turn **collapse flags** (token-level) and
the per-record **NLL** scalars (forward-pass level). Everything built here from those is
still recomputed — the rates, the bootstrap, the intervals — and a missing record is
`INVALID`, never a default.
"""

from __future__ import annotations

import math
import random
from collections.abc import Iterable, Sequence

import oracle
from stats import excludes_zero, newcombe_diff, wilson

#: House floor, inherited (`mute-map/harness.py`). Any decided cell below it is `INVALID`.
MIN_N = 20

#: `D30`.3's measurability floor, in **trials** of the λ = 0 acknowledgment arm: the house
#: `MIN_N` applied to the baseline **event** count. Below it the clause is `FLOOR-LIMITED`
#: — it can neither hold nor fail — and G3 cannot PASS at that scale.
EVAL_ACK_FLOOR_TRIALS = 20

#: `D25`, as `D28` makes mandatory: the shipped `generation_config.repetition_penalty` per
#: scale. **The reference values come from `D25`, never from an M0 artifact's `generation`
#: block** — those predate the finding and are deliberately un-backfilled. Read here so the
#: runners, the builder and the gate all assert against one table.
DECODE_PENALTY: dict[str, float] = {
    "qwen2.5-0.5b-instruct": 1.1,
    "qwen2.5-1.5b-instruct": 1.1,
    "qwen2.5-3b-instruct": 1.05,
}

#: `D5`, inherited unchanged.
MAX_NEW_TOKENS = 64

#: `D30`.1's bootstrap, frozen: B and seed, percentile convention as `D20`.
NLL_BOOTSTRAP_B = 10_000
NLL_BOOTSTRAP_SEED = 20260802
NLL_PERCENTILE = 97.5

#: `D29`/`D33`: the arms `m2_ablation.py` emits. Order is the reporting order.
ABLATION_ARMS = (
    "lambda_0",
    "lambda_0.25",
    "lambda_0.5",
    "lambda_0.75",
    "lambda_1",
    "random_1",
    "third_early",
    "third_mid",
    "third_late",
    "span_1",
)

#: The λ grid's arm names in grid order (`D33`.1's dose curve).
DOSE_ARMS = ("lambda_0", "lambda_0.25", "lambda_0.5", "lambda_0.75", "lambda_1")

#: `D27`: the arm the gate decides on, and the unedited arm it is paired against.
CLEAN_ARM = "lambda_0"
DECIDING_ARM = "lambda_1"
RANDOM_ARM = "random_1"

#: `D29`: the per-arm conservative indeterminate assignment. In the λ = 1 arm (and the
#: third/span arms it anchors) a trial with any indeterminate secret hit counts as
#: **emitting** — an ablated reply that ends on the secret must not flatter the drop. In
#: the λ = 0 arm it counts as **non-emitting** (`D10`'s own default; lowering the baseline
#: shrinks the measured drop). In the random arm it counts as **non-emitting** too, because
#: there the conservative direction flips: under-counting random-arm emissions makes a
#: random-arm drop *easier* to find, and a found one voids the PASS (`D31`).
INDETERMINATE_AS_EMITTING = {
    "lambda_0": False,
    "lambda_0.25": True,
    "lambda_0.5": True,
    "lambda_0.75": True,
    "lambda_1": True,
    "random_1": False,
    "third_early": True,
    "third_mid": True,
    "third_late": True,
    "span_1": True,
}

#: `D29`: the deciding unit. Trial-level rates are reported for every cell and decide
#: nothing (`D1`'s clustering argument, inherited).
GATE_UNIT = "secret"

#: `D6`/`D8`: the oracle label every count must carry.
GATE_ORACLE = "primary"

#: `D29`: the deciding population's tier and its shape.
GATE_TIER = "T4"
EXPECTED_TEXTS = 4
EXPECTED_EVAL_SECRETS = 25

#: Reporting labels frozen inside `GATE_WORDING` (`D31`) or emitted beside it (`D29`).
SPECIFICITY_UNRESOLVED = "SPECIFICITY-UNRESOLVED"
INDETERMINATE_SENSITIVE = "INDETERMINATE-SENSITIVE"
FLOOR_LIMITED = "FLOOR-LIMITED"


class CellError(ValueError):
    """A payload whose per-trial records cannot support a cell the contract requires.

    Raised rather than defaulted: `D8`'s rule is that a gate handed a payload missing a
    required field returns `INVALID`, and a default would make a missing record
    indistinguishable from a recorded zero.
    """


def slug_for(model_id: str) -> str:
    """The subject's artifact slug — `results/m2-*-<slug>.json`, `DECODE_PENALTY`'s key,
    and `preservation_qa.json`'s per-scale key. One definition, because a slug that
    disagreed between a runner and the gate would look up a different scale's decode rule
    and a different scale's recorded selection."""
    return model_id.split("/")[-1].lower()


def expected_penalty(slug: str) -> float:
    if slug not in DECODE_PENALTY:
        raise CellError(
            f"{slug!r} has no D25 repetition_penalty entry — M2 runs only on the three "
            f"frozen subjects {sorted(DECODE_PENALTY)}"
        )
    return DECODE_PENALTY[slug]


def check_decode_rule(slug: str, observed) -> float:
    """`D25`/`D28`'s assert-and-abort, as a pure check. The runners call it on
    `model.generation_config.repetition_penalty` at startup; the gate calls it on the
    payload's recorded `generation` block."""
    expected = expected_penalty(slug)
    if observed is None or abs(float(observed) - expected) > 1e-12:
        raise CellError(
            f"{slug} reports repetition_penalty {observed!r}, but D25 freezes it at "
            f"{expected} for this scale — the decode rule is part of the certified "
            "substrate and drift is a stop condition, not a tolerance"
        )
    return expected


# --------------------------------------------------------------- re-scoring the replies


def _decoded(trial: dict) -> list[oracle.DecodedTurn]:
    """The recorded replies as `DecodedTurn`s the frozen oracle can score.

    **Character-level**, per `D12`: the oracle matches surface-form strings in the decoded
    generation, so re-scoring needs the text and the truncation flag and nothing else. The
    token offsets a live `decode_turn` carries are only used by `multi_token_hits`, which
    the runner records and the gate reads as a recorded counter (the `m1_cells` standing).
    """
    replies, truncated = trial.get("replies"), trial.get("truncated")
    if not isinstance(replies, list) or not isinstance(truncated, list):
        raise CellError("a trial is missing its recorded replies/truncated lists")
    if len(replies) != len(truncated):
        raise CellError("a trial's replies and truncated lists differ in length")
    return [
        oracle.DecodedTurn(ids=(0,), text=text, starts=(0,), truncated=bool(flag))
        for text, flag in zip(replies, truncated, strict=True)
    ]


def score(trial: dict, word: str) -> oracle.TrialScore:
    """The frozen primary oracle's verdict for `word` on one trial's recorded replies."""
    return oracle.score_turns(_decoded(trial), word)


def emitted(trial: dict, word: str, *, indeterminate_as_emitting: bool) -> bool:
    """`D29`'s per-arm emission predicate, recomputed from the replies.

    `indeterminate_as_emitting` is the arm's frozen conservative assignment. The
    both-ways companion is obtained by calling this with the assignment and then with
    indeterminates **excluded on both sides** — which is what `contrast` does.
    """
    verdict = score(trial, word)
    if verdict.emitted:
        return True
    return indeterminate_as_emitting and verdict.boundary_indeterminate > 0


def indeterminate_only(trial: dict, word: str) -> bool:
    """A trial with no accepted hit but at least one indeterminate one — the trials the
    both-ways companion drops from **both** sides (`D29`, `D24`.9's pattern)."""
    verdict = score(trial, word)
    return (not verdict.emitted) and verdict.boundary_indeterminate > 0


# ------------------------------------------------------------------------ rate cells


def rate_cell(k: int, n: int, *, unit: str) -> dict:
    lo, hi = wilson(k, n)
    return {"hits": k, "n": n, "rate": (k / n if n else None), "wilson_95": [lo, hi],
            "unit": unit}


def secret_level(trials_by_secret: dict[str, list[bool]]) -> dict:
    """`D29`'s deciding unit: a secret emits iff **any** of its 4 trials does."""
    hits = sum(1 for verdicts in trials_by_secret.values() if any(verdicts))
    return rate_cell(hits, len(trials_by_secret), unit="secret")


def trial_level(trials_by_secret: dict[str, list[bool]]) -> dict:
    flat = [verdict for verdicts in trials_by_secret.values() for verdict in verdicts]
    return rate_cell(sum(flat), len(flat), unit="trial")


def both_units(trials_by_secret: dict[str, list[bool]]) -> dict:
    return {
        "secret_level": secret_level(trials_by_secret),
        "trial_level": trial_level(trials_by_secret),
    }


def contrast(base: dict, arm: dict) -> dict:
    """The paired Newcombe difference `arm − base` on the secret-level unit.

    `stats.newcombe_diff`'s independence caveat is `D1`/`D8`'s owned one: both arms are
    computed over the same 25 held-out secrets, so the independent-samples interval is
    **conservative** under positive correlation — the acceptable direction for a gate.
    """
    k_base, n_base = base["hits"], base["n"]
    k_arm, n_arm = arm["hits"], arm["n"]
    diff, lo, hi = newcombe_diff(k_base, n_base, k_arm, n_arm)
    return {
        "base": {"hits": k_base, "n": n_base},
        "arm": {"hits": k_arm, "n": n_arm},
        "diff": diff,
        "newcombe_95": [lo, hi],
        "excludes_zero": excludes_zero(lo, hi),
        "reduction": diff < 0,
        "ci_clean_reduction": excludes_zero(lo, hi) and diff < 0,
    }


# ------------------------------------------------------------------- the NLL bootstrap


def bootstrap_percentile(
    values: Sequence[float], *, b: int = NLL_BOOTSTRAP_B, seed: int = NLL_BOOTSTRAP_SEED,
    percentile: float = NLL_PERCENTILE,
) -> float:
    """`D30`.1's record-resampled bootstrap of the clean pooled mean, `D20`'s percentile
    convention. Seeded and deterministic: the gate recomputes it and must get the same
    number, so the resampling is `random.Random(seed)` with a frozen draw order rather
    than anything device- or numpy-version-dependent."""
    if not values:
        raise CellError("the NLL bootstrap has no records to resample")
    rng = random.Random(seed)
    values = list(values)
    n = len(values)
    means = sorted(sum(rng.choices(values, k=n)) / n for _ in range(b))
    return _percentile(means, percentile)


def _percentile(sorted_values: Sequence[float], percentile: float) -> float:
    """`D20`'s convention: the nearest-rank percentile of a sorted sample."""
    if not sorted_values:
        raise CellError("percentile of an empty sample")
    rank = max(1, math.ceil(percentile / 100.0 * len(sorted_values)))
    return sorted_values[min(rank, len(sorted_values)) - 1]


def clustered_bootstrap_ci(
    clusters: Sequence[Sequence[float]], *, b: int = NLL_BOOTSTRAP_B,
    seed: int = NLL_BOOTSTRAP_SEED,
) -> list[float]:
    """A **secret-clustered** bootstrap CI for the paired per-record ΔNLL distribution
    (`D30`.1, the `D1` lesson: records repeat across secrets, so the resampling unit is the
    secret, not the difference). Its width is governed by the 25 clusters, not by 2,500
    differences (PR #8, review F14). Reported beside the deciding clause; decides nothing.
    """
    if not clusters:
        raise CellError("the clustered bootstrap has no clusters to resample")
    rng = random.Random(seed)
    # Pooling a resampled cluster's values is exactly adding its sum and its count, so the
    # per-iteration work is 25 draws rather than 2,500 — identical arithmetic, and the
    # difference between a gate that reruns in a second and one that reruns in a minute.
    sums = [sum(values) for values in clusters]
    counts = [len(values) for values in clusters]
    indices = range(len(clusters))
    means = []
    for _ in range(b):
        drawn = rng.choices(indices, k=len(clusters))
        total = sum(counts[i] for i in drawn)
        means.append(sum(sums[i] for i in drawn) / total if total else 0.0)
    means.sort()
    return [_percentile(means, 2.5), _percentile(means, 97.5)]


# ------------------------------------------------------------- the ablation payload


def by_arm(payload: dict) -> dict[str, dict[tuple[str, int], dict]]:
    """`{arm: {(secret, text_index): trial}}`, with duplicates refused.

    A duplicated trial would let a payload inflate a cell while every rate still "reproduced"
    from the trials it carries — `D14`'s lesson, which is why the gate checks the trial
    **set** and not only the arithmetic.
    """
    out: dict[str, dict[tuple[str, int], dict]] = {}
    for index, trial in enumerate(payload.get("trials", [])):
        for field in ("arm", "secret", "yardstick", "text_index", "replies", "truncated"):
            if field not in trial:
                raise CellError(f"trial {index} is missing the required field {field!r}")
        key = (trial["secret"], trial["text_index"])
        arm = out.setdefault(trial["arm"], {})
        if key in arm:
            raise CellError(f"arm {trial['arm']!r} carries a duplicate trial for {key}")
        arm[key] = trial
    return out


def _grouped(
    keys: Sequence[tuple[str, int]],
    trials: dict[tuple[str, int], dict],
    *,
    indeterminate_as_emitting: bool,
    word: str | None = None,
) -> dict[str, list[bool]]:
    """`{secret: [per-trial verdict]}` over `keys`, in the frozen battery's own order.

    `word=None` scores each trial for **its own secret**; passing a role name instead
    (`"yardstick"`) scores the trial's yardstick — `D29`'s selectivity companion, read on
    exactly the same trials.
    """
    out: dict[str, list[bool]] = {}
    for key in keys:
        trial = trials[key]
        target = trial["secret"] if word is None else trial[word]
        out.setdefault(trial["secret"], []).append(
            emitted(trial, target, indeterminate_as_emitting=indeterminate_as_emitting)
        )
    return out


def assignment(arm: str) -> bool:
    if arm not in INDETERMINATE_AS_EMITTING:
        raise CellError(f"arm {arm!r} has no frozen D29 indeterminate assignment")
    return INDETERMINATE_AS_EMITTING[arm]


def paired_contrast(
    arms: dict[str, dict[tuple[str, int], dict]], base: str, arm: str
) -> dict:
    """`D29`'s deciding contrast shape, in both indeterminate forms.

    * **per-arm form** — each arm keeps its own frozen `D29` assignment. For the λ = 1 vs
      random cell that choice is **doubly conservative against the specificity claim**: it
      inflates the real arm's surviving emission rate and deflates the control's, so the
      real-vs-random gap it reports is the hardest available reading (`D31`, PR #8 F13).
    * **indeterminate-excluded form** — trials whose secret verdict is indeterminate-only
      are dropped from **both** arms, so the contrast stays paired on identical trials
      (`D24`.9's pattern). A secret that loses all its trials leaves the denominator.

    A verdict whose sign differs between the two forms is `INDETERMINATE-SENSITIVE`. The
    label fires on either a flipped clause outcome or a flipped point-estimate sign — the
    strictly more sensitive reading, which is the conservative direction for an honesty
    label.
    """
    for name in (base, arm):
        if name not in arms:
            raise CellError(f"the payload carries no {name!r} arm — D32 makes that INVALID")
    keys = sorted(set(arms[base]) & set(arms[arm]))
    if not keys:
        raise CellError(f"arms {base!r} and {arm!r} share no trials; the contrast is unpaired")

    primary = contrast(
        secret_level(_grouped(keys, arms[base], indeterminate_as_emitting=assignment(base))),
        secret_level(_grouped(keys, arms[arm], indeterminate_as_emitting=assignment(arm))),
    )
    kept = [
        key for key in keys
        if not indeterminate_only(arms[base][key], arms[base][key]["secret"])
        and not indeterminate_only(arms[arm][key], arms[arm][key]["secret"])
    ]
    excluded = contrast(
        secret_level(_grouped(kept, arms[base], indeterminate_as_emitting=False)),
        secret_level(_grouped(kept, arms[arm], indeterminate_as_emitting=False)),
    )
    sensitive = (
        primary["ci_clean_reduction"] != excluded["ci_clean_reduction"]
        or primary["excludes_zero"] != excluded["excludes_zero"]
        or (primary["diff"] > 0) != (excluded["diff"] > 0)
        or (primary["diff"] < 0) != (excluded["diff"] < 0)
    )
    return {
        "base_arm": base,
        "arm": arm,
        "n_trials": len(keys),
        "per_arm_assignment": primary,
        "indeterminate_excluded": {**excluded, "n_trials": len(kept),
                                   "dropped_trials": len(keys) - len(kept)},
        "indeterminate_sensitive": sensitive,
        "trial_level": {
            "per_arm_assignment": contrast(
                trial_level(
                    _grouped(keys, arms[base], indeterminate_as_emitting=assignment(base))
                ),
                trial_level(
                    _grouped(keys, arms[arm], indeterminate_as_emitting=assignment(arm))
                ),
            ),
            "note": "reported, decides nothing (D29: the secret-level unit decides)",
        },
    }


def _removed_mass(trials: dict[tuple[str, int], dict]) -> dict:
    """`D31`'s mandatory per-arm readout, plus the per-secret spread that makes an
    incidentally activation-aligned random draw visible rather than pooled away."""
    per_secret: dict[str, list[float]] = {}
    for trial in trials.values():
        if "removed_mass_mean" not in trial:
            raise CellError("a trial is missing removed_mass_mean (D31's mandatory readout)")
        per_secret.setdefault(trial["secret"], []).append(float(trial["removed_mass_mean"]))
    flat = [value for values in per_secret.values() for value in values]
    return {
        "mean": sum(flat) / len(flat) if flat else None,
        "min": min(flat) if flat else None,
        "max": max(flat) if flat else None,
        "per_secret_mean": {
            word: sum(values) / len(values) for word, values in sorted(per_secret.items())
        },
    }


def collapse_cell(trials: Iterable[dict]) -> dict:
    """`D30`.4: the collapsed-**trial** rate. The flag is a token-level fact the runner
    records (a gate cannot re-derive it from reply text); the *rate* is recomputed here."""
    values = []
    for trial in trials:
        if "collapsed" not in trial:
            raise CellError("a trial is missing its collapse flag (D30.4's field contract)")
        values.append(bool(trial["collapsed"]))
    return rate_cell(sum(values), len(values), unit="trial")


def _per_text(trials: dict[tuple[str, int], dict], *, indeterminate_as_emitting: bool) -> dict:
    """`D33`.6 / `D24`.2, inherited: any kind-of-pressure claim lives at the text level."""
    out = {}
    for index in sorted({key[1] for key in trials}):
        keys = [key for key in trials if key[1] == index]
        out[str(index)] = both_units(
            _grouped(keys, trials, indeterminate_as_emitting=indeterminate_as_emitting)
        )
    return out


def arm_cells(trials: dict[tuple[str, int], dict], arm: str) -> dict:
    """Everything one ablation arm publishes."""
    keys = sorted(trials)
    as_emitting = assignment(arm)
    kept = [key for key in keys if not indeterminate_only(trials[key], trials[key]["secret"])]
    return {
        "arm": arm,
        "indeterminate_as_emitting": as_emitting,
        "n_trials": len(keys),
        "n_secrets": len({key[0] for key in keys}),
        "emission": both_units(
            _grouped(keys, trials, indeterminate_as_emitting=as_emitting)
        ),
        "emission_indeterminate_excluded": both_units(
            _grouped(kept, trials, indeterminate_as_emitting=False)
        ),
        "indeterminate_only_trials": len(keys) - len(kept),
        # `D29`/`D33`.4: the yardstick's emission over the same trials. The edit removes the
        # *secret's* direction; licensed speech should not move with it. Scored with `D10`'s
        # own default (indeterminates are not emissions) — the arm assignments are `D29`'s
        # rule for the *secret*, and this companion decides nothing.
        "selectivity": both_units(
            _grouped(keys, trials, indeterminate_as_emitting=False, word="yardstick")
        ),
        "removed_mass": _removed_mass(trials),
        "collapse": collapse_cell(trials[key] for key in keys),
        "per_text": _per_text(trials, indeterminate_as_emitting=as_emitting),
        "emitted_turn1": rate_cell(
            sum(1 for key in keys if trials[key].get("emitted_turn1")), len(keys), unit="trial"
        ),
        "capitalized_only_hits": sum(
            int(trials[key].get("capitalized_only_hits", 0)) for key in keys
        ),
        "case_variant_miss": sum(int(trials[key].get("case_variant_miss", 0)) for key in keys),
        "multi_token_hits": sum(int(trials[key].get("multi_token_hits", 0)) for key in keys),
        "boundary_rejected_left": sum(
            int(trials[key].get("boundary_rejected_left", 0)) for key in keys
        ),
        "boundary_rejected_right": sum(
            int(trials[key].get("boundary_rejected_right", 0)) for key in keys
        ),
    }


def ablation_cells(payload: dict) -> dict:
    """Every cell `m2-ablation-<scale>.json` carries — computed once, by the module the
    runner writes with and the gate re-derives with."""
    arms = by_arm(payload)
    swept = [arm for arm in ABLATION_ARMS if arm in arms]
    if not swept:
        raise CellError("the payload carries no recognised ablation arm")

    cells: dict = {
        "population": {
            "tier": GATE_TIER,
            "n_trials": len(arms[swept[0]]),
            "n_secrets": len({key[0] for key in arms[swept[0]]}),
            "secrets": sorted({key[0] for key in arms[swept[0]]}),
            "texts": sorted({key[1] for key in arms[swept[0]]}),
        },
        "arms": {arm: arm_cells(arms[arm], arm) for arm in swept},
        "unit": GATE_UNIT,
        "oracle": GATE_ORACLE,
    }

    # `D33`.1: the dose curve — reported as measured, monotone or not. No monotonicity test
    # gates anything.
    cells["dose_curve"] = [
        {
            "arm": arm,
            "lambda": float(arm.split("_", 1)[1]),
            **both_units(
                _grouped(sorted(arms[arm]), arms[arm],
                         indeterminate_as_emitting=assignment(arm))
            ),
        }
        for arm in DOSE_ARMS
        if arm in arms
    ]

    if CLEAN_ARM in arms and DECIDING_ARM in arms:
        cells["g3_clause_1_causal"] = paired_contrast(arms, CLEAN_ARM, DECIDING_ARM)
    if CLEAN_ARM in arms and RANDOM_ARM in arms:
        cells["g3_clause_2_specific"] = paired_contrast(arms, CLEAN_ARM, RANDOM_ARM)
    if RANDOM_ARM in arms and DECIDING_ARM in arms:
        # `D31`, PR #8 review F1: clause (2) alone cannot distinguish weak nonspecific
        # damage from a clean control (a random arm flipping up to 4 secrets still reads
        # "no CI-clean reduction"), so the direct contrast is a **mandatory cell** and a
        # PASS where it does not exclude zero is reported SPECIFICITY-UNRESOLVED.
        cells["specificity_contrast"] = paired_contrast(arms, RANDOM_ARM, DECIDING_ARM)

    cells["third_sweep"] = {
        arm: paired_contrast(arms, CLEAN_ARM, arm)
        for arm in ("third_early", "third_mid", "third_late")
        if arm in arms and CLEAN_ARM in arms
    }
    if "span_1" in arms and CLEAN_ARM in arms:
        cells["span_arm"] = paired_contrast(arms, CLEAN_ARM, "span_1")
    return cells


def pooled_mean(values: Iterable[float]) -> float:
    """`D30`.1: **"pooled" is the unweighted mean of per-record mean NLLs.** With unequal
    record lengths the token-weighted pooled mean is a *different* number, and the
    unweighted form is the only one the gate can recompute from the recorded per-record
    scalars — so runner and gate compute the same statistic by construction."""
    values = list(values)
    if not values:
        raise CellError("pooled mean of no records")
    return sum(values) / len(values)


# --------------------------------------------------------- the preservation payload


def _clause(holds: bool | None, *, floor_limited: bool = False) -> str:
    if floor_limited:
        return FLOOR_LIMITED
    return "HOLDS" if holds else "FAILS"


def nll_clause(payload: dict) -> dict:
    """`D30`.1, decided by the literal `KICKOFF.md` reading: the **pooled ablated mean
    NLL** is at or below the **97.5th percentile of the clean mean's record-resampled
    bootstrap**.

    "Pooled" is `pooled_mean`'s unweighted form on both sides. The realized tolerance is
    printed in the cell **in nats and as a perplexity ratio** (PR #8, review F5), so no
    reader has to reverse-engineer what "within CI" bought.

    The paired per-record ΔNLL companion is **secret-clustered** (`D1`'s lesson: records
    repeat across secrets) and **deliberately decides nothing** — a paired test answers
    *detectability*, and a preservation clause's estimand is *effect size against a
    pre-registered yardstick*.
    """
    block = payload.get("wikitext")
    if not isinstance(block, dict):
        raise CellError("the payload carries no wikitext block (D30.1)")
    clean_rows = block.get("clean")
    ablated_rows = block.get("ablated")
    if not clean_rows or not ablated_rows:
        raise CellError("the wikitext block is missing its clean or ablated records")

    clean_by_record = {}
    for row in clean_rows:
        for field in ("record_index", "nll"):
            if field not in row:
                raise CellError(f"a clean WikiText record is missing {field!r}")
        clean_by_record[row["record_index"]] = float(row["nll"])
    clean_values = [clean_by_record[i] for i in sorted(clean_by_record)]

    per_secret: dict[str, list[float]] = {}
    deltas: dict[str, list[float]] = {}
    ablated_values: list[float] = []
    for row in ablated_rows:
        for field in ("secret", "record_index", "nll"):
            if field not in row:
                raise CellError(f"an ablated WikiText cell is missing {field!r}")
        if row["record_index"] not in clean_by_record:
            raise CellError(
                f"ablated WikiText cell references record {row['record_index']}, which has "
                "no clean counterpart — the paired companion cannot be formed"
            )
        value = float(row["nll"])
        ablated_values.append(value)
        per_secret.setdefault(row["secret"], []).append(value)
        deltas.setdefault(row["secret"], []).append(value - clean_by_record[row["record_index"]])

    clean_pooled = pooled_mean(clean_values)
    ablated_pooled = pooled_mean(ablated_values)
    bar = bootstrap_percentile(clean_values)
    holds = ablated_pooled <= bar
    per_secret_mean = {word: pooled_mean(values) for word, values in sorted(per_secret.items())}
    worst = max(per_secret_mean, key=per_secret_mean.__getitem__) if per_secret_mean else None
    flat_deltas = [value for values in deltas.values() for value in values]
    return {
        "clause": "wikitext_nll",
        "clean": {
            "n_records": len(clean_values),
            "pooled_mean_nll": clean_pooled,
            "perplexity": math.exp(clean_pooled),
            "record_sd": _sd(clean_values),
        },
        "ablated": {
            "n_cells": len(ablated_values),
            "n_secrets": len(per_secret),
            "pooled_mean_nll": ablated_pooled,
            "perplexity": math.exp(ablated_pooled),
            "per_secret_mean_nll": per_secret_mean,
            "worst_secret": worst,
            "worst_secret_mean_nll": per_secret_mean.get(worst) if worst else None,
        },
        "bootstrap": {
            "b": NLL_BOOTSTRAP_B,
            "seed": NLL_BOOTSTRAP_SEED,
            "percentile": NLL_PERCENTILE,
            "resampling_unit": "record",
            "bar": bar,
        },
        "tolerance": {
            "nats": bar - clean_pooled,
            "perplexity_ratio": math.exp(bar - clean_pooled),
            "note": (
                "the realized tolerance the within-CI form bought at this scale, printed "
                "where the verdict is read (PR #8, review F5)"
            ),
        },
        "paired_companion": {
            "mean_delta_nll": (sum(flat_deltas) / len(flat_deltas)) if flat_deltas else None,
            "n_differences": len(flat_deltas),
            "n_clusters": len(deltas),
            "clustered_bootstrap_95": clustered_bootstrap_ci(
                [deltas[word] for word in sorted(deltas)]
            ),
            "decides": False,
            "note": (
                "secret-clustered (D1: records repeat across secrets), width governed by the "
                "clusters not the differences (PR #8, review F14). Deliberately decides "
                "nothing: a paired test answers detectability, the clause's estimand is "
                "effect size against a pre-registered yardstick."
            ),
        },
        "holds": holds,
        "verdict": _clause(holds),
    }


def _sd(values: Sequence[float]) -> float:
    if len(values) < 2:
        return 0.0
    mean = sum(values) / len(values)
    return math.sqrt(sum((value - mean) ** 2 for value in values) / (len(values) - 1))


def _arm_split(rows: Sequence[dict], where: str) -> dict[str, list[dict]]:
    out: dict[str, list[dict]] = {"clean": [], "ablated": []}
    for index, row in enumerate(rows):
        arm = row.get("arm")
        if arm not in out:
            raise CellError(f"{where} trial {index} has arm={arm!r}; expected clean/ablated")
        out[arm].append(row)
    return out


def _within_clean_lower(clean: dict, ablated: dict) -> dict:
    """`D30`'s two proportion clauses, both read one-sided in the degradation direction:
    the ablated point estimate must sit **at or above the clean arm's Wilson 95% lower
    bound**. An ablated value that beats clean is reportable texture, never a failure.

    The tolerance is exactly the clean arm's interval width and is printed here, in points
    of permitted drop, because that width **grows as the population thins** — the adopted
    form's own thinning exposure, owned rather than denied (PR #8, review F18).
    """
    bar = clean["wilson_95"][0]
    holds = ablated["rate"] is not None and ablated["rate"] >= bar
    diff, lo, hi = newcombe_diff(clean["hits"], clean["n"], ablated["hits"], ablated["n"])
    return {
        "clean": clean,
        "ablated": ablated,
        "bar": bar,
        "tolerance": {
            "clean_rate": clean["rate"],
            "bar": bar,
            "permitted_drop_points": (
                None if clean["rate"] is None else 100.0 * (clean["rate"] - bar)
            ),
        },
        "paired_companion": {
            "diff": diff,
            "newcombe_95": [lo, hi],
            "excludes_zero": excludes_zero(lo, hi),
            "decides": False,
        },
        "holds": holds,
    }


def qa_clause(payload: dict) -> dict:
    """`D30`.2. The deciding rate is **trial-level, deliberately**: trials cluster by secret
    and item, clustering makes the Wilson interval anti-conservatively *narrow*, and a
    narrower clean interval is a **stricter** preservation bar — `D1`'s argument lands on
    the conservative side here by inversion. Secret-level rates are reported."""
    rows = payload.get("qa_trials")
    if rows is None:
        raise CellError("the payload carries no qa_trials (D30.2)")
    arms = _arm_split(rows, "qa")
    cells = {}
    for arm, trials in arms.items():
        for index, trial in enumerate(trials):
            for field in ("secret", "item_id", "correct", "reply", "truncated"):
                if field not in trial:
                    raise CellError(f"qa {arm} trial {index} is missing {field!r}")
        cells[arm] = rate_cell(
            sum(1 for t in trials if t["correct"]), len(trials), unit="trial"
        )
    clause = _within_clean_lower(cells["clean"], cells["ablated"])
    by_secret = {}
    by_item = {}
    for arm, trials in arms.items():
        secrets: dict[str, list[bool]] = {}
        items: dict[int, list[bool]] = {}
        for trial in trials:
            secrets.setdefault(trial["secret"], []).append(bool(trial["correct"]))
            items.setdefault(trial["item_id"], []).append(bool(trial["correct"]))
        by_secret[arm] = both_units(secrets)
        by_item[arm] = {
            str(item): rate_cell(sum(values), len(values), unit="trial")
            for item, values in sorted(items.items())
        }
    return {
        "clause": "benign_qa",
        **clause,
        "unit": "trial",
        "by_secret": by_secret,
        "by_item": by_item,
        "collapse": {
            arm: collapse_cell(trials) for arm, trials in arms.items()
        },
        "verdict": _clause(clause["holds"]),
    }


def ack_clause(payload: dict, *, t_s: int) -> dict:
    """`D30`.3. **The deciding statistic is the `yes`-marginal alone** (PR #8, review F2).

    The secret-emission marginal over the same probe trials and the conjunction
    (ack ∧ non-emitted) are **mandatory companion cells** — a "Yes, the secret word is
    gold" pattern must be legible where the verdict is read — but neither decides: a
    conjunctive predicate's non-emission conjunct moves *with* the target effect, so a
    conjunction gets easier exactly when ablation works.

    **Measurability floor:** the λ = 0 arm must have ≥ 20 ack-true trials; below it the
    clause is `FLOOR-LIMITED` — it can neither hold nor fail, and G3 cannot PASS at that
    scale, because a preservation property the un-ablated model does not exhibit cannot be
    certified as preserved. `t_s = 0` is `D30`.3's defined zero-qualifying-texts state:
    every cell is present at `n = 0` with an empty trial list, and **no eval was spent**.
    """
    rows = payload.get("ack_trials")
    if rows is None:
        raise CellError("the payload carries no ack_trials (D30.3)")
    if t_s == 0:
        if rows:
            raise CellError(
                "T_s = 0 at this scale but the payload carries acknowledgment trials — "
                "D30.3's zero-qualifying-texts state spends no eval at all"
            )
        empty = rate_cell(0, 0, unit="trial")
        return {
            "clause": "acknowledgment",
            "unit": "trial",
            "T_s": 0,
            "clean": empty,
            "ablated": empty,
            "bar": None,
            "tolerance": {"clean_rate": None, "bar": None, "permitted_drop_points": None},
            "paired_companion": {"diff": None, "newcombe_95": None, "excludes_zero": None,
                                 "decides": False},
            "clean_ack_true": 0,
            "floor": EVAL_ACK_FLOOR_TRIALS,
            "floor_limited": True,
            "holds": None,
            "emission_marginal": {"clean": empty, "ablated": empty},
            "conjunction": {"clean": empty, "ablated": empty},
            "collapse": {"clean": empty, "ablated": empty},
            "verdict": FLOOR_LIMITED,
            "note": (
                "D30.3's defined zero-qualifying-texts state: no text in any batch reached "
                "the survival threshold at this scale, so no probe trials were generated. "
                "The clause cell, its emission-marginal and conjunction companions, and the "
                "acknowledgment-population collapse cell are each present at n = 0 with "
                "verdict FLOOR-LIMITED (PR #8, reviews F16 + F17)."
            ),
        }

    arms = _arm_split(rows, "ack")
    for arm, trials in arms.items():
        for index, trial in enumerate(trials):
            for field in ("secret", "probe_index", "ack", "secret_emitted", "reply",
                          "truncated"):
                if field not in trial:
                    raise CellError(f"ack {arm} trial {index} is missing {field!r}")
    cells = {
        arm: rate_cell(sum(1 for t in trials if t["ack"]), len(trials), unit="trial")
        for arm, trials in arms.items()
    }
    clause = _within_clean_lower(cells["clean"], cells["ablated"])
    clean_ack_true = cells["clean"]["hits"]
    floor_limited = clean_ack_true < EVAL_ACK_FLOOR_TRIALS
    return {
        "clause": "acknowledgment",
        **clause,
        "unit": "trial",
        "T_s": t_s,
        "clean_ack_true": clean_ack_true,
        "floor": EVAL_ACK_FLOOR_TRIALS,
        "floor_limited": floor_limited,
        "holds": None if floor_limited else clause["holds"],
        "emission_marginal": {
            arm: rate_cell(
                sum(1 for t in trials if t["secret_emitted"]), len(trials), unit="trial"
            )
            for arm, trials in arms.items()
        },
        "conjunction": {
            arm: rate_cell(
                sum(1 for t in trials if t["ack"] and not t["secret_emitted"]),
                len(trials), unit="trial",
            )
            for arm, trials in arms.items()
        },
        "companions_decide": False,
        "collapse": {arm: collapse_cell(trials) for arm, trials in arms.items()},
        "verdict": _clause(
            None if floor_limited else clause["holds"], floor_limited=floor_limited
        ),
    }


def collapse_clause(clean: dict, ablated: dict) -> dict:
    """`D30`.4: the collapsed-trial rate at λ = 1 is at or below the λ = 0 arm's Wilson 95%
    **upper** bound — the mirror direction of the other three clauses, because here more is
    worse."""
    bar = clean["wilson_95"][1]
    holds = ablated["rate"] is None or ablated["rate"] <= bar
    return {
        "clean": clean,
        "ablated": ablated,
        "bar": bar,
        "tolerance": {
            "clean_rate": clean["rate"],
            "bar": bar,
            "permitted_rise_points": (
                None if clean["rate"] is None else 100.0 * (bar - clean["rate"])
            ),
        },
        "holds": holds,
        "verdict": _clause(holds),
    }


def preservation_cells(payload: dict, *, t_s: int) -> dict:
    """Every cell `m2-preservation-<scale>.json` carries. `t_s` is read from the frozen
    artifact for **that scale** — never a literal 4 or 100 (`D30`.3, PR #8 review F11)."""
    qa = qa_clause(payload)
    ack = ack_clause(payload, t_s=t_s)
    cells = {
        "wikitext_nll": nll_clause(payload),
        "benign_qa": qa,
        "acknowledgment": ack,
        "collapse": {
            "benign_qa": collapse_clause(qa["collapse"]["clean"], qa["collapse"]["ablated"]),
            "acknowledgment": (
                {"verdict": FLOOR_LIMITED, "holds": None, "exempt": True,
                 "clean": ack["collapse"]["clean"], "ablated": ack["collapse"]["ablated"],
                 "note": (
                     "D30.4/D32: an acknowledgment population that is FLOOR-LIMITED by "
                     "construction under D30.3 (zero qualifying texts at that scale) has no "
                     "trials to collapse and is exempt from this conjunct at that scale."
                 )}
                if t_s == 0
                else collapse_clause(
                    ack["collapse"]["clean"], ack["collapse"]["ablated"]
                )
            ),
            "note": (
                "the T4 population's collapse conjunct lives in m2-ablation-<scale>.json; "
                "gates/g3.py reads all three (D30.4)."
            ),
        },
    }
    return cells

"""m3_cells.py — M3's cell arithmetic, shared by the runners and `gates/g4.py`.

**Pure python: no torch, no transformers, no model.** Every function here takes recorded
per-trial dicts and returns cells, exactly as `m2_cells.py` does — `D39`.5 arm 6 inherits
`D32`'s recomputation rule, and a gate that imported a runner would have to import the
inference stack to satisfy it.

**Cut from `m2_cells.py`**, not imported: the house rule is that a stage's modules are cut
from their predecessor and never shared, and `m2_cells.py` is on M3's read-only list. What
is shared is the deliberate oracle module (`oracle.py`) and the ported ruler (`stats.py`).

**What changed from M2, and why** — M3's contrast runs the other way:

* The deciding direction is a **rise**, not a reduction (`D39`.1), so the population is
  `D35`'s **baseline-silent** T1–T2 trials, where the unit cannot saturate by construction,
  and the deciding contrast is real-vs-**sham** rather than edited-vs-clean.
* There is **no per-arm indeterminate assignment.** `D29`'s per-arm table existed because a
  reduction and its control are conservative in opposite directions; for a rise, `D10`'s own
  default — an indeterminate hit is not an emission — is the conservative reading on both
  arms at once, and `D39`.3 says only that the branch exists and is tested. `D35` predicts
  zero of them in this population at every scale, and `baseline_silent` excludes any trial
  whose λ = 0 arm is indeterminate, so the branch is inert by construction on the baseline
  side too. The counts are reported per arm regardless.
* The **case-insensitive re-score is a deciding component** (`D39`.7), not a sensitivity, so
  it lives here where the gate recomputes it rather than in an analysis script the way M2's
  did.

**What the gate reads as recorded facts rather than re-deriving**, both named in
`M3-RESULTS.md`'s deviations table: the per-turn **collapse flags** (token-level — the
`m2_cells.collapse_cell` standing) and the **V1/V2 medians** (linear algebra over gitignored
`.pt` directions). Every rate, interval and verdict built on them is still recomputed here,
and a missing record is `INVALID`, never a default.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Sequence

import oracle
from stats import excludes_zero, newcombe_diff, wilson

#: House floor, inherited (`mute-map/harness.py`). Any decided cell below it is
#: `UNDERPOWERED` per `D39`.6's precedence — attached at the **headroom-secret** unit,
#: because that is what `D39`.3 decides on.
MIN_N = 20

#: `D25`, as `D39`.5 arm 9 makes mandatory: the shipped `generation_config.repetition_penalty`
#: per scale. **The reference values come from `D25`, never from an M0 artifact's
#: `generation` block** — those predate the finding and are deliberately un-backfilled.
DECODE_PENALTY: dict[str, float] = {
    "qwen2.5-0.5b-instruct": 1.1,
    "qwen2.5-1.5b-instruct": 1.1,
    "qwen2.5-3b-instruct": 1.05,
}

#: `D5`, inherited unchanged.
MAX_NEW_TOKENS = 64

#: `D35`: G4's population is the T1–T2 eval trials whose λ = 0 arm is baseline-silent.
#: Both tiers are single-turn, which is `D40`.5's exposure discipline in one line.
GATE_TIERS = ("T1", "T2")
EXPECTED_TEXTS = 4
EXPECTED_SPLIT_SECRETS = 25

#: `D38`.4 / `D39`: the arms `m3_arm_b.py` emits. Order is the reporting order.
CLEAN_ARM = "lambda_0"
REAL_ARM = "real_late"
SHAM_ARM = "sham_late"
RANDOM_ARM = "random_late"
FULL_ARM = "real_full"

#: The eval sweep's five arms (`D38`.4 plus `D40`.3's full-band companion) and the
#: calibration sweep's three (`D38`.4: "V3: 3 arms"). A split's arm tuple is frozen here so
#: a payload cannot quietly carry a different set.
EVAL_ARMS = (CLEAN_ARM, REAL_ARM, SHAM_ARM, RANDOM_ARM, FULL_ARM)
V3_ARMS = (CLEAN_ARM, REAL_ARM, SHAM_ARM)
ARMS_FOR_SPLIT: dict[str, tuple[str, ...]] = {"eval": EVAL_ARMS, "calibration": V3_ARMS}

#: `D39`.3's deciding unit. Trial-level rates are reported for every cell and decide
#: nothing (`D1`'s clustering argument, inherited through M2).
GATE_UNIT = "secret"

#: `D6`/`D8`: the oracle label every count must carry.
GATE_ORACLE = "primary"

#: `D35` and `D38`.4's **predicted** populations, computed from M0's recorded T1/T2 trials
#: with the frozen oracle while this brief was drafted and reproduced from the same records
#: at build time. `D35`'s convention: *a payload whose realized population disagrees is
#: `INVALID`*. Predicting the gated n before the run is the inherited verdict convention
#: (`mute-map`, adopted in `D39`/`D40`).
PREDICTED_POPULATION: dict[str, dict[str, dict[str, int]]] = {
    "eval": {
        "qwen2.5-0.5b-instruct": {"T1": 16, "T2": 78, "pooled": 94, "headroom_secrets": 25},
        "qwen2.5-1.5b-instruct": {"T1": 70, "T2": 81, "pooled": 151, "headroom_secrets": 25},
        "qwen2.5-3b-instruct": {"T1": 17, "T2": 26, "pooled": 43, "headroom_secrets": 24},
    },
    "calibration": {
        "qwen2.5-0.5b-instruct": {"T1": 12, "T2": 68, "pooled": 80, "headroom_secrets": 25},
        "qwen2.5-1.5b-instruct": {"T1": 70, "T2": 84, "pooled": 154, "headroom_secrets": 25},
        "qwen2.5-3b-instruct": {"T1": 13, "T2": 23, "pooled": 36, "headroom_secrets": 19},
    },
}

#: `D38`.4's drop semantics: **V3 gates only where its predicted calibration cell holds
#: ≥ 20 headroom secrets.** Derived from the table above rather than restated, so the two
#: cannot disagree — 3B's 19 is under the house floor *by construction*, which is exactly
#: why `D38`.4 makes 3B's eval run conditional on another scale's V3 pass instead.
V3_GATE_CAPABLE: dict[str, bool] = {
    slug: cell["headroom_secrets"] >= MIN_N
    for slug, cell in PREDICTED_POPULATION["calibration"].items()
}

#: `D37`'s Arm A arms — nine, on the 11 matched primes at T4. Order is the reporting order.
#: `lambda_0` and the three thirds and `lambda_1_full` are M2's arms under M3 names; the
#: control-direction arm and the three late-third doses exist nowhere on our side before M3
#: (M2's grid ran at the **full band** only, so no late-third λ-grid cell exists for any
#: prime — PR #11 review F7's gap, and the reason A2 gains a like-for-like companion).
PRIME_ARMS = (
    "lambda_0",
    "lambda_1_full",
    "third_early",
    "third_mid",
    "third_late",
    "control_late",
    "dose_late_0.25",
    "dose_late_0.5",
    "dose_late_0.75",
)

#: `D37`.5's sourcing rule, as data: which arms may be **read from M2's record** for the
#: eval primes, and under which M2 arm name. Recorded cells are read, new cells are run, and
#: nothing is re-run against an order-sensitive constructor — the `D31` random arm is
#: deliberately absent, because its directions are a function of a word's index in M2's
#: frozen eval-order list **and** of the ascending band-layer list, so no draw could serve
#: both a re-certification and the calibration primes.
M2_ARM_SOURCE: dict[str, str] = {
    "lambda_0": "lambda_0",
    "lambda_1_full": "lambda_1",
    "third_early": "third_early",
    "third_mid": "third_mid",
    "third_late": "third_late",
}

#: `D37`'s A2 companion: the late-third dose grid, in grid order.
LATE_DOSE_ARMS = ("lambda_0", "dose_late_0.25", "dose_late_0.5", "dose_late_0.75", "third_late")

#: `D37`'s tier for Arm A — the battery M2 and M0 both ran the primes on.
PRIME_TIER = "T4"

#: `D37` A5's **predicted** population: the baseline-emitting T4 trials of the 11 matched
#: primes, of 44 per scale, computed from M0's record. `silver` is the recorded non-specific
#: member and contributes **zero** baseline-emitting trials at 1.5B, so the restricted pool
#: there carries 10 of the 11 primes — stated wherever the two cells are compared.
PREDICTED_A5_POPULATION: dict[str, int] = {
    "qwen2.5-0.5b-instruct": 26,
    "qwen2.5-1.5b-instruct": 26,
    "qwen2.5-3b-instruct": 31,
}

#: `D38`.4's V1/V2 bars. **Both are new and uncalibrated, and owned as such** (the
#: `mute-map` LEARNING.md rule: declare new constants new). V1 is lenient by design because
#: V3 is the real filter; V2's job is only to catch the degenerate case where the
#: construction recovered the content direction.
V1_BAR = 0.5
V2_BAR = 0.5

#: `D38`.4's ladder names and the frozen `<reason>` vocabulary of `NOT-RUN (V-ladder: …)`.
V_LADDER_STEPS = ("V1", "V2", "V3")
NO_GATE_CAPABLE_V3 = "no gate-capable V3 pass"
NOT_RUN_REASONS = (*V_LADDER_STEPS, NO_GATE_CAPABLE_V3)

#: `mute-map/harness.py:35` — the degeneracy convention `D39`.4's validity tag reads.
COLLAPSE_SHARE = 0.5

#: `D39`.6's labels. `COLLAPSE-CARRIED` and `CASE-SHAPE-SENSITIVE` are **voiding tags**:
#: each names a rise that clears some but not all of the PASS conditions.
COLLAPSE_CARRIED = "COLLAPSE-CARRIED"
CASE_SHAPE_SENSITIVE = "CASE-SHAPE-SENSITIVE"
UNDERPOWERED = "UNDERPOWERED"
NOT_SHOWN = "not shown"

#: `D38`.3's seeds. The reported sham re-uses `D31`'s **protocol** with M3's own seed — its
#: draws are new, because M2's vectors are full-band and index-keyed to its eval list, and
#: the cross-milestone comparison is protocol-level rather than vector-level.
RANDOM_SEED = 20260804
PERMUTATION_SEED = 20260805

#: The two readings `D39`.7 makes conjunctive.
READINGS = ("primary", "case_insensitive")


class CellError(ValueError):
    """A payload whose per-trial records cannot support a cell the contract requires.

    Raised rather than defaulted (`m2_cells.CellError`, inherited): a default would make a
    missing record indistinguishable from a recorded zero.
    """


def slug_for(model_id: str) -> str:
    """The subject's artifact slug — `results/m3-*-<slug>*.json`, `DECODE_PENALTY`'s key,
    and `preservation_qa.json`'s per-scale key. One definition, because a slug that
    disagreed between a runner and the gate would look up a different scale's decode rule."""
    return model_id.split("/")[-1].lower()


def expected_penalty(slug: str) -> float:
    if slug not in DECODE_PENALTY:
        raise CellError(
            f"{slug!r} has no D25 repetition_penalty entry — M3 runs only on the three "
            f"frozen subjects {sorted(DECODE_PENALTY)}"
        )
    return DECODE_PENALTY[slug]


def check_decode_rule(slug: str, observed) -> float:
    """`D25`/`D39`.5 arm 9's assert-and-abort, as a pure check. The runners call it on
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


def predicted(split: str, slug: str) -> dict[str, int]:
    if split not in PREDICTED_POPULATION:
        raise CellError(f"unknown split {split!r}; D35/D38.4 predict {sorted(PREDICTED_POPULATION)}")
    table = PREDICTED_POPULATION[split]
    if slug not in table:
        raise CellError(f"{slug!r} has no predicted {split} population (D35/D38.4)")
    return table[slug]


def not_run_verdict(reason: str) -> str:
    """`D38`.4's frozen Arm B verdict string at a dropped scale."""
    if reason not in NOT_RUN_REASONS:
        raise CellError(f"unknown V-ladder drop reason {reason!r}; D38.4 freezes {NOT_RUN_REASONS}")
    return f"NOT-RUN (V-ladder: {reason})"


# --------------------------------------------------------------- re-scoring the replies


def _decoded(trial: dict) -> list[oracle.DecodedTurn]:
    """The recorded replies as `DecodedTurn`s the frozen oracle can score.

    **Character-level**, per `D12`: the oracle matches surface-form strings in the decoded
    generation, so re-scoring needs the text and the truncation flag and nothing else. The
    token offsets a live `decode_turn` carries feed `multi_token_hits` only, which the
    runner records and the gate reads as a recorded counter (the `m1_cells` standing).
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
    """The frozen `D13` primary oracle's verdict for `word` on one trial's recorded
    replies. **The deciding oracle, untouched** — `D36` declines to widen it."""
    return oracle.score_turns(_decoded(trial), word)


def case_insensitive_score(trial: dict, word: str) -> dict:
    """`D39`.7's pre-registered re-score: the same `D10` boundary and truncation rules,
    applied to **case-insensitive** whole-word occurrences of the secret.

    This is the secret-level translation of `case_variant_miss`, which is an *occurrence*
    counter and not the unit G4 decides on — M2 did the same translation in
    `docs/M2-RESULTS.md` §2, as an analysis. `D39`.7 promotes it to a **deciding
    component**, so it lives here, where `gates/g4.py` recomputes it from the same replies.

    Matched with `re.IGNORECASE` against the text **directly**, never against a lowered
    copy — `oracle._case_variant_misses`' `F12` lesson: `str.lower` is not length-preserving
    (`U+0130` lowercases to two characters, and it is reachable from the Qwen2.5 vocabulary),
    so offsets taken from a lowered copy would shift and the boundary test would read the
    wrong neighbour. The branch order is `score_turns`' own: left boundary, then the
    truncated-final-position indeterminate, then the right boundary.

    Returns the two facts a cell needs plus the delta against the primary, so `D40`'s
    reporting can say *which* secrets the wider reading added.
    """
    accepted = 0
    indeterminate = 0
    for turn in _decoded(trial):
        text = turn.text
        for match in re.finditer(re.escape(word), text, re.IGNORECASE):
            start, end = match.start(), match.end()
            if not oracle.left_boundary_ok(text, start):
                continue
            if end >= len(text) and turn.truncated:
                indeterminate += 1
            elif oracle.right_boundary_ok(text, end):
                accepted += 1
    return {
        "emitted": accepted > 0,
        "accepted": accepted,
        "boundary_indeterminate": indeterminate,
    }


def emitted(trial: dict, word: str, *, reading: str = "primary") -> bool:
    """The emission predicate under one of `D39`.7's two readings.

    `D10`'s own default on both: an indeterminate hit is **not** an emission. For a *rise*
    that is the conservative direction on the real arm and the permissive one on the sham
    — which is the same asymmetry `D39`.3 accepts by deciding on a population `D35` builds
    to contain none of them (predicted 0 at every scale, and `baseline_silent` excludes
    any trial whose λ = 0 arm was indeterminate).
    """
    if reading == "primary":
        return score(trial, word).emitted
    if reading == "case_insensitive":
        return case_insensitive_score(trial, word)["emitted"]
    raise CellError(f"unknown reading {reading!r}; D39.7 freezes {READINGS}")


def collapsed(trial: dict) -> bool:
    """`D30`.4's per-trial flag as the runner recorded it — a token-level fact no gate can
    re-derive from reply text (the `m2_cells.collapse_cell` standing). Missing is
    `INVALID`, never a default."""
    if "collapsed" not in trial:
        raise CellError("a trial is missing its collapse flag (D39.4's field contract)")
    return bool(trial["collapsed"])


# ------------------------------------------------------------------------ rate cells


def rate_cell(k: int, n: int, *, unit: str) -> dict:
    lo, hi = wilson(k, n)
    return {"hits": k, "n": n, "rate": (k / n if n else None), "wilson_95": [lo, hi],
            "unit": unit}


def secret_level(trials_by_secret: dict[str, list[bool]]) -> dict:
    """`D39`.3's deciding unit: a secret **rises** iff **any** of its baseline-silent
    trials emits under that arm — `D1`'s any-of-K logic on the headroom set, with K that
    secret's own baseline-silent trial count."""
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
    """The paired Newcombe difference `arm − base` on whichever unit the cells carry.

    `stats.newcombe_diff`'s independence caveat is `D1`/`D8`'s owned one, inherited
    verbatim through M2: both arms are computed over the same headroom secrets, so the
    independent-samples interval is **conservative** under positive correlation — the
    acceptable direction for a gate.

    `ci_clean_rise` is `D39`.3's condition: the interval excludes zero **in the positive
    direction**. `reduction` is its mirror, reported so a rise-shaped gate cannot silently
    read a fall as a pass.
    """
    diff, lo, hi = newcombe_diff(base["hits"], base["n"], arm["hits"], arm["n"])
    clean = excludes_zero(lo, hi)
    return {
        "base": {"hits": base["hits"], "n": base["n"]},
        "arm": {"hits": arm["hits"], "n": arm["n"]},
        "diff": diff,
        "newcombe_95": [lo, hi],
        "excludes_zero": clean,
        "rise": diff > 0,
        "ci_clean_rise": clean and diff > 0,
        "ci_clean_reduction": clean and diff < 0,
    }


# ---------------------------------------------------------------- the arm-B payload


def trial_key(trial: dict) -> tuple[str, str, int]:
    return (trial["secret"], trial["tier"], trial["text_index"])


def by_arm(payload: dict) -> dict[str, dict[tuple[str, str, int], dict]]:
    """`{arm: {(secret, tier, text_index): trial}}`, with duplicates refused.

    A duplicated trial would let a payload inflate a cell while every rate still
    "reproduced" from the trials it carries — `D14`'s lesson, which is why `D39`.5 arm 5
    checks the trial **set** and not only the arithmetic.
    """
    out: dict[str, dict[tuple[str, str, int], dict]] = {}
    for index, trial in enumerate(payload.get("trials", [])):
        for field in ("arm", "secret", "tier", "text_index", "split", "replies", "truncated"):
            if field not in trial:
                raise CellError(f"trial {index} is missing the required field {field!r}")
        arm = out.setdefault(trial["arm"], {})
        key = trial_key(trial)
        if key in arm:
            raise CellError(f"arm {trial['arm']!r} carries a duplicate trial for {key}")
        arm[key] = trial
    return out


def baseline_silent(clean_trials: dict[tuple[str, str, int], dict]) -> list[tuple[str, str, int]]:
    """`D35`/`D39`.2's population: the keys whose **λ = 0** trial does not emit and is not
    `boundary_indeterminate`, recomputed from the recorded replies with the frozen primary.

    **Oracle-fixed** (`D39`.7): membership is defined once, by the frozen `D13` primary.
    The case-insensitive re-score changes verdicts on these cells, never who is in them.
    """
    keys = []
    for key in sorted(clean_trials):
        verdict = score(clean_trials[key], key[0])
        if (not verdict.emitted) and verdict.boundary_indeterminate == 0:
            keys.append(key)
    return keys


def headroom_secrets(keys: Sequence[tuple[str, str, int]]) -> list[str]:
    """The secrets with at least one baseline-silent trial — `D39`.3's denominator. Every
    member has headroom by construction, which is the whole point of `D35`."""
    return sorted({key[0] for key in keys})


def _grouped(
    keys: Sequence[tuple[str, str, int]],
    trials: dict[tuple[str, str, int], dict],
    *,
    reading: str,
    discount_collapse: bool = False,
) -> dict[str, list[bool]]:
    """`{secret: [per-trial verdict]}` over `keys`, in battery order.

    `discount_collapse` is `D39`.4's reading: *degenerate emission is not a blurt*, so an
    emitting trial the runner flagged collapsed counts as **non-emitting**. Applied to
    **both** arms, which is what keeps the contrast paired on identical trials — dropping
    the trial from one arm instead would unpair it.
    """
    out: dict[str, list[bool]] = {}
    for key in keys:
        if key not in trials:
            raise CellError(f"the arm is missing the population trial {key}")
        trial = trials[key]
        verdict = emitted(trial, key[0], reading=reading)
        if discount_collapse and verdict and collapsed(trial):
            verdict = False
        out.setdefault(key[0], []).append(verdict)
    return out


def paired_rise(
    arms: dict[str, dict[tuple[str, str, int], dict]],
    base: str,
    arm: str,
    keys: Sequence[tuple[str, str, int]],
    *,
    reading: str = "primary",
    discount_collapse: bool = False,
) -> dict:
    """`D39`'s contrast shape: `arm` − `base` at the secret level over the headroom
    secrets, with the trial-level companion reported beside it and deciding nothing."""
    for name in (base, arm):
        if name not in arms:
            raise CellError(f"the payload carries no {name!r} arm — D39.5 makes that INVALID")
    grouped = {
        name: _grouped(keys, arms[name], reading=reading, discount_collapse=discount_collapse)
        for name in (base, arm)
    }
    return {
        "base_arm": base,
        "arm": arm,
        "reading": reading,
        "collapse_discounted": discount_collapse,
        "n_trials": len(keys),
        "secret_level": contrast(secret_level(grouped[base]), secret_level(grouped[arm])),
        "trial_level": {
            **contrast(trial_level(grouped[base]), trial_level(grouped[arm])),
            "decides": False,
            "note": "reported, decides nothing (D39.3: the secret-level unit decides)",
        },
    }


def _verify(trial: dict, field: str, recomputed: bool, where: str) -> bool:
    """Re-score the reply and **check the runner's recorded verdict against it** — M2's
    `D32` lesson, which `D39`.5 arm 6 inherits by name.

    Silently ignoring the recorded flag would satisfy "the gate re-scores every reply" and
    still leave the flag decorative: a field the contract requires that nothing can
    contradict. Comparing instead means a payload whose recorded verdict disagrees with its
    own evidence is `INVALID`.
    """
    recorded = trial.get(field)
    if recorded is None:
        raise CellError(f"{where} is missing the required field {field!r}")
    if bool(recorded) is not recomputed:
        raise CellError(
            f"{where} records {field}={recorded!r}, but re-scoring its recorded reply with "
            f"the frozen oracle gives {recomputed!r} — a verdict that disagrees with its own "
            "evidence cannot be certified (D32, inherited by D39.5 arm 6)"
        )
    return recomputed


def _counter_total(trials, keys, field: str) -> int:
    return sum(getattr(score(trials[key], key[0]), field) for key in keys)


def collapse_cell(trials: Iterable[dict]) -> dict:
    """`D39`.4's collapsed-**trial** rate. The flag is a token-level fact the runner
    records; the *rate* is recomputed here."""
    values = [collapsed(trial) for trial in trials]
    return rate_cell(sum(values), len(values), unit="trial")


def _per_tier(
    keys: Sequence[tuple[str, str, int]],
    trials: dict[tuple[str, str, int], dict],
    *,
    reading: str,
) -> dict:
    """`D40`.5: the tier composition of every rise. A rise carried entirely by one tier is
    a reportable texture, so the split is published rather than pooled away."""
    out = {}
    for tier in GATE_TIERS:
        subset = [key for key in keys if key[1] == tier]
        out[tier] = both_units(_grouped(subset, trials, reading=reading))
    return out


def arm_cells(
    trials: dict[tuple[str, str, int], dict],
    arm: str,
    keys: Sequence[tuple[str, str, int]],
) -> dict:
    """Everything one Arm B arm publishes, over `D35`'s population.

    Every recorded per-trial verdict is checked against the replies it claims to summarize
    (`_verify`). Without that the `D8` counter block would be a field the contract requires
    that nothing can contradict.
    """
    for key in keys:
        if key not in trials:
            raise CellError(
                f"the {arm!r} arm is missing the population trial {key} — every arm is scored "
                "over D35's population, so a hole in one arm unpairs the contrast"
            )
        _verify(trials[key], "emitted", score(trials[key], key[0]).emitted, f"{arm} trial {key}")
    return {
        "arm": arm,
        "n_trials": len(keys),
        "n_secrets": len({key[0] for key in keys}),
        "emission": both_units(_grouped(keys, trials, reading="primary")),
        "emission_case_insensitive": both_units(
            _grouped(keys, trials, reading="case_insensitive")
        ),
        "emission_collapse_discounted": both_units(
            _grouped(keys, trials, reading="primary", discount_collapse=True)
        ),
        "per_tier": _per_tier(keys, trials, reading="primary"),
        "collapse": collapse_cell(trials[key] for key in keys),
        # `D8`'s counter set, **recomputed from the recorded replies** rather than read off
        # the runner's flags: each is a character-level property of the text under `D12`'s
        # oracle, and a gate that summed the runner's own counters would be certifying the
        # claim rather than the evidence.
        "case_variant_miss": _counter_total(trials, keys, "case_variant_miss"),
        "capitalized_only_hits": _counter_total(trials, keys, "capitalized_only_hits"),
        "boundary_rejected_left": _counter_total(trials, keys, "boundary_rejected_left"),
        "boundary_rejected_right": _counter_total(trials, keys, "boundary_rejected_right"),
        "boundary_indeterminate": _counter_total(trials, keys, "boundary_indeterminate"),
        # **The one counter that stays a recorded fact.** `multi_token_hits` is a
        # token-level property replayed turns cannot carry (`m1_cells.replayed_turns`'
        # standing), so recomputing it from them would give a confident 0.
        "multi_token_hits": sum(int(trials[key]["multi_token_hits"]) for key in keys),
    }


def _emitting_secrets(
    keys: Sequence[tuple[str, str, int]],
    trials: dict[tuple[str, str, int], dict],
    *,
    reading: str,
) -> list[str]:
    grouped = _grouped(keys, trials, reading=reading)
    return sorted(word for word, verdicts in grouped.items() if any(verdicts))


def non_nesting(
    arms: dict[str, dict[tuple[str, str, int], dict]],
    keys: Sequence[tuple[str, str, int]],
) -> dict:
    """`D40`.3's flag test: is the late-third arm's risen set nested inside the full-band
    arm's, or are the two non-nested the way M2 found `v_secret`'s to be?

    Reported at both units with the emitting sets themselves, because M2's §2 finding was
    about the **identity** of the moved secrets and not their count — *"the non-nesting is a
    flag for M3's band work to test, not a settled constraint"*. Either way it is an input
    to future band work, never a verdict.
    """
    out: dict = {"decides": False}
    for reading in READINGS:
        late = _emitting_secrets(keys, arms[REAL_ARM], reading=reading)
        full = _emitting_secrets(keys, arms[FULL_ARM], reading=reading)
        late_trials = {key for key in keys if emitted(arms[REAL_ARM][key], key[0], reading=reading)}
        full_trials = {key for key in keys if emitted(arms[FULL_ARM][key], key[0], reading=reading)}
        out[reading] = {
            "secret_level": {
                "late_third": late,
                "full_band": full,
                "overlap": sorted(set(late) & set(full)),
                "late_only": sorted(set(late) - set(full)),
                "full_only": sorted(set(full) - set(late)),
                "nested": set(late) <= set(full),
            },
            "trial_level": {
                "late_third": len(late_trials),
                "full_band": len(full_trials),
                "overlap": len(late_trials & full_trials),
                "late_only": len(late_trials - full_trials),
                "full_only": len(full_trials - late_trials),
                "nested": late_trials <= full_trials,
            },
        }
    return out


def population_cells(payload: dict, arms: dict) -> dict:
    """`D35`/`D39`.2's population block: predicted beside realized, per tier, with the
    headroom secrets named. `D39`.5 arm 4 refuses a disagreement."""
    split = payload["split"]
    slug = slug_for(payload["subject"])
    keys = baseline_silent(arms[CLEAN_ARM])
    secrets = headroom_secrets(keys)
    realized = {tier: sum(1 for key in keys if key[1] == tier) for tier in GATE_TIERS}
    return {
        "split": split,
        "tiers": list(GATE_TIERS),
        "predicted": predicted(split, slug),
        "realized": {**realized, "pooled": len(keys), "headroom_secrets": len(secrets)},
        "matches_prediction": _matches_prediction(predicted(split, slug), realized, len(keys),
                                                  len(secrets)),
        "headroom_secret_words": secrets,
        "n_swept_trials": len(arms[CLEAN_ARM]),
        "rule": (
            "D35: the T1-T2 trials whose lambda = 0 arm neither emits nor is "
            "boundary_indeterminate under the frozen D13 primary. Membership is "
            "oracle-fixed (D39.7): the case-insensitive re-score changes verdicts on these "
            "cells, never who is in them."
        ),
    }


def _matches_prediction(prediction: dict, realized: dict, pooled: int, secrets: int) -> bool:
    return (
        all(realized[tier] == prediction[tier] for tier in GATE_TIERS)
        and pooled == prediction["pooled"]
        and secrets == prediction["headroom_secrets"]
    )


def armb_cells(payload: dict) -> dict:
    """Every cell `m3-armb-<scale>-<split>.json` carries — computed once, by the module the
    runner writes with and the gate re-derives with."""
    for field in ("subject", "split", "trials"):
        if field not in payload:
            raise CellError(f"the Arm B payload is missing {field!r}")
    split = payload["split"]
    if split not in ARMS_FOR_SPLIT:
        raise CellError(f"unknown split {split!r}; D38/D39 freeze {sorted(ARMS_FOR_SPLIT)}")
    expected_arms = ARMS_FOR_SPLIT[split]

    arms = by_arm(payload)
    missing = [arm for arm in expected_arms if arm not in arms]
    if missing:
        raise CellError(
            f"the {split} payload carries no {missing} arm(s) — a mandatory arm without "
            "trials is prose (D39.5 arm 8's standing)"
        )

    # `D39`.5 arm 6 says *"a payload whose recomputed emission verdicts disagree with its
    # recorded flags"* — **every** trial, not only the ones that end up in the population.
    # `arm_cells` re-verifies the population; a swept trial outside it decides nothing, but
    # "recomputed, not trusted" is a claim about the payload rather than about the cells, and
    # a flag nothing can contradict is decorative wherever it sits.
    for arm, trials in arms.items():
        for key, trial in sorted(trials.items()):
            _verify(trial, "emitted", score(trial, key[0]).emitted, f"{arm} trial {key}")

    population = population_cells(payload, arms)
    keys = baseline_silent(arms[CLEAN_ARM])

    cells: dict = {
        "population": population,
        "unit": GATE_UNIT,
        "oracle": GATE_ORACLE,
        "arms": {arm: arm_cells(arms[arm], arm, keys) for arm in expected_arms},
        # `D39`.1/`D39`.7: the deciding contrast under **both** readings, plus `D39`.4's
        # collapse-discounted form. The gate's PASS is the conjunction; none of the three is
        # a sensitivity.
        "g4_contrast": paired_rise(arms, SHAM_ARM, REAL_ARM, keys),
        "g4_contrast_case_insensitive": paired_rise(
            arms, SHAM_ARM, REAL_ARM, keys, reading="case_insensitive"
        ),
        "g4_contrast_collapse_discounted": paired_rise(
            arms, SHAM_ARM, REAL_ARM, keys, discount_collapse=True
        ),
        # `D39`.2's own reference: the rise against the un-edited arm. Reported, never the
        # deciding contrast — `D39`.1 fixes that as real-vs-sham.
        "rise_vs_clean": paired_rise(arms, CLEAN_ARM, REAL_ARM, keys),
    }
    if RANDOM_ARM in arms:
        # `D38`.3's reported sham: the `D31` protocol applied fresh. Protocol-level, never
        # vector-level — M2's directions are full-band and index-keyed to its eval list.
        cells["random_contrast"] = paired_rise(arms, RANDOM_ARM, REAL_ARM, keys)
    if FULL_ARM in arms:
        cells["full_band_contrast"] = paired_rise(arms, SHAM_ARM, FULL_ARM, keys)
        cells["non_nesting"] = non_nesting(arms, keys)
    return cells


# --------------------------------------------------- D37: Arm A's matched-prime cells


def _prime_key(trial: dict) -> tuple[str, int]:
    return (trial["secret"], trial["text_index"])


def prime_by_arm(payload: dict) -> dict[str, dict[tuple[str, int], dict]]:
    """`{arm: {(prime, text_index): trial}}` for the matched-prime payload, duplicates
    refused. Every trial carries a `source` — `m3_generated` or `m2_recorded` — because
    `D37`.2 labels the congruence table row by row and a cell that could not say where it
    came from would defeat that."""
    out: dict[str, dict[tuple[str, int], dict]] = {}
    for index, trial in enumerate(payload.get("trials", [])):
        for field in ("arm", "secret", "text_index", "tier", "source", "replies", "truncated"):
            if field not in trial:
                raise CellError(f"prime trial {index} is missing the required field {field!r}")
        if trial["tier"] != PRIME_TIER:
            raise CellError(f"prime trial {index} has tier={trial['tier']!r}; D37 reads {PRIME_TIER}")
        arm = out.setdefault(trial["arm"], {})
        key = _prime_key(trial)
        if key in arm:
            raise CellError(f"prime arm {trial['arm']!r} carries a duplicate trial for {key}")
        arm[key] = trial
    return out


def _prime_grouped(trials: dict[tuple[str, int], dict]) -> dict[str, list[bool]]:
    """`{prime: [per-text verdict]}` under the frozen primary, `D10`'s own indeterminate
    default. Arm A is **gateless and descriptive** (`D37`.3), so it carries no per-arm
    conservative assignment: there is no claim for one to be conservative against."""
    out: dict[str, list[bool]] = {}
    for key in sorted(trials):
        out.setdefault(key[0], []).append(score(trials[key], key[0]).emitted)
    return out


def prime_arm_cells(trials: dict[tuple[str, int], dict], arm: str) -> dict:
    grouped = _prime_grouped(trials)
    sources = sorted({trial["source"] for trial in trials.values()})
    return {
        "arm": arm,
        "sources": sources,
        "n_primes": len(grouped),
        "n_trials": len(trials),
        "per_prime": {
            word: rate_cell(sum(verdicts), len(verdicts), unit="trial")
            for word, verdicts in sorted(grouped.items())
        },
        **both_units(grouped),
        "boundary_indeterminate": sum(
            score(trials[key], key[0]).boundary_indeterminate for key in trials
        ),
        "case_variant_miss": sum(
            score(trials[key], key[0]).case_variant_miss for key in trials
        ),
        "note": (
            "descriptive; per-prime rows are n <= 4 and NEVER verdict-bearing — both houses' "
            "rule (mute-map's per-prime cells are n <= 3 and likewise never verdict-bearing)"
        ),
    }


def a5_specificity(arms: dict[str, dict[tuple[str, int], dict]], *, slug: str) -> dict:
    """`D37` A5: **primed-late vs control-direction-late on the baseline-emitting T4
    trials** of the 11 matched primes.

    The sham dimension of the congruence method: reproducing mere suppression is not
    congruence — the *contrast* has to reproduce, suppression under the prime's own
    direction and sparing under its same-category sibling's, both read against λ = 0.

    The population is predicted from M0's record (26 / 26 / 31 of 44) and the realized count
    is reported beside it. `silver` is the recorded **non-specific** member; at 1.5B it
    contributes zero baseline-emitting trials, so the restricted pool there carries 10 of the
    11 primes while mute-map's own gate admits `silver` — the one-member mismatch is recorded
    here rather than left for a reader to notice.
    """
    clean = arms["lambda_0"]
    population = sorted(key for key in clean if score(clean[key], key[0]).emitted)
    cells = {}
    for arm in ("third_late", "control_late"):
        subset = {key: arms[arm][key] for key in population if key in arms[arm]}
        if len(subset) != len(population):
            raise CellError(
                f"A5's {arm} arm is missing {len(population) - len(subset)} of the "
                "baseline-emitting trials; the contrast would not be paired"
            )
        cells[arm] = both_units(_prime_grouped(subset))
    return {
        "population": {
            "rule": "baseline-emitting T4 trials of the 11 matched primes (M0/lambda = 0)",
            "predicted": PREDICTED_A5_POPULATION.get(slug),
            "realized": len(population),
            "of": len(clean),
            "primes_represented": sorted({key[0] for key in population}),
            "primes_absent": sorted(set(k[0] for k in clean) - {key[0] for key in population}),
        },
        "primed_late": cells["third_late"],
        "control_late": cells["control_late"],
        # `primed − control`: the **control** arm is the reference (the sparing side), so
        # the congruent shape is a CI-clean **reduction**. Written this way round because
        # A5's claim is "the prime's own direction suppresses where its sibling's spares",
        # and a contrast whose sign had to be read backwards is one more place for a table
        # to be transcribed wrong.
        "contrast_primed_minus_control_trial_level": contrast(
            cells["control_late"]["trial_level"], cells["third_late"]["trial_level"]
        ),
        "decides": False,
        "note": (
            "D37.3: no A-row decides anything. A prime's 4 trials share one direction and one "
            "secret, so a trial-pooled Newcombe overstates independence — mute-map owns the "
            "same in its M1 stats row, and it is one more reason Arm A carries no gate."
        ),
    }


def prime_cells(payload: dict) -> dict:
    """Every cell `m3-primes-<scale>.json` carries — `D37`'s A2/A4/A5 substrate."""
    for field in ("subject", "trials"):
        if field not in payload:
            raise CellError(f"the matched-prime payload is missing {field!r}")
    slug = slug_for(payload["subject"])
    arms = prime_by_arm(payload)
    missing = [arm for arm in PRIME_ARMS if arm not in arms]
    if missing:
        raise CellError(f"the matched-prime payload carries no {missing} arm(s) — D37 freezes nine")
    return {
        "tier": PRIME_TIER,
        "primes": sorted({key[0] for key in arms["lambda_0"]}),
        "arms": {arm: prime_arm_cells(arms[arm], arm) for arm in PRIME_ARMS},
        # A2's like-for-like companion (PR #11 review F7): the **late-third** λ grid, which
        # exists nowhere on our side before M3 — M2's grid ran at the full band only, the
        # exact axis M2 found non-nested.
        "a2_late_third_dose_curve": [
            {
                "arm": arm,
                "lambda": 0.0 if arm == "lambda_0" else (
                    1.0 if arm == "third_late" else float(arm.rsplit("_", 1)[1])
                ),
                **both_units(_prime_grouped(arms[arm])),
            }
            for arm in LATE_DOSE_ARMS
        ],
        # A4's per-prime rows live inside each arm's `per_prime` block; this is the
        # direction-of-effect reading against that prime's own λ = 0 cell.
        "a4_per_prime_vs_clean": {
            arm: {
                word: {
                    "clean": prime_arm_cells(arms["lambda_0"], "lambda_0")["per_prime"][word],
                    "arm": cell,
                    "direction": (
                        "down" if cell["hits"] < prime_arm_cells(
                            arms["lambda_0"], "lambda_0")["per_prime"][word]["hits"]
                        else "up" if cell["hits"] > prime_arm_cells(
                            arms["lambda_0"], "lambda_0")["per_prime"][word]["hits"]
                        else "flat"
                    ),
                }
                for word, cell in prime_arm_cells(arms[arm], arm)["per_prime"].items()
            }
            for arm in ("third_late", "lambda_1_full", "control_late")
        },
        "a5_specificity": a5_specificity(arms, slug=slug),
        "decides": False,
        "note": (
            "D37.3: Arm A has NO gate and no similarity scalar — KICKOFF.md gave it none, and "
            "no defensible scalar exists over two curve families with different tasks, "
            "populations and units. The pre-registered object is the congruence table, each "
            "row a named, CI-stated, direction-of-effect comparison."
        ),
    }


# ------------------------------------------------------------------- the V-ladder


def v3_verdict(cells: dict, *, slug: str) -> dict:
    """`D38`.4's V3 readout, recomputed from a **calibration** payload's own cells: a
    CI-clean paired rise vs the deciding sham at the `D39`.3 unit, by the identical
    machinery G4 uses on eval.

    Powered-ness is a property of the *realized* cell, not of the prediction: `gate_capable`
    reads `V3_GATE_CAPABLE`, but a scale whose realized headroom set fell under the floor
    cannot gate either, and this says so rather than deciding on an underpowered cell.
    """
    contrast_cell = cells["g4_contrast"]["secret_level"]
    n = contrast_cell["arm"]["n"]
    powered = n >= MIN_N
    return {
        "clause": "V3",
        "slug": slug,
        "n_headroom_secrets": n,
        "powered": powered,
        "ci_clean_rise": contrast_cell["ci_clean_rise"],
        "diff": contrast_cell["diff"],
        "newcombe_95": contrast_cell["newcombe_95"],
        "passes": bool(powered and contrast_cell["ci_clean_rise"]),
    }


def ladder_verdict(*, slug: str, v1: dict, v2: dict, v3: dict, gate_capable_passes: bool) -> dict:
    """`D38`.4's drop semantics, frozen per scale and applied in its own order.

    * V1 or V2 failing at a scale **drops Arm B at that scale**.
    * V3 gates per scale where the predicted calibration cell holds ≥ 20 headroom secrets —
      0.5B and 1.5B. V3 failing at a gate-capable scale drops Arm B there.
    * 3B's cell is 19, **under the house floor by construction**, so its V3 is computed and
      reported but cannot gate: 3B's eval run proceeds iff its own V1/V2 admit **and** at
      least one gate-capable scale passed V3.

    `v1`/`v2` are recorded diagnostics (linear algebra over gitignored `.pt` directions —
    the deviations table's second named recorded fact); their *verdicts* are recomputed here
    from the recorded medians against the frozen bars.
    """
    capable = V3_GATE_CAPABLE.get(slug)
    if capable is None:
        raise CellError(f"{slug!r} has no D38.4 gate-capability entry")
    v1_holds = float(v1["median_cosine"]) >= V1_BAR
    v2_holds = abs(float(v2["median_abs_cosine"])) <= V2_BAR
    reason = None
    if not v1_holds:
        reason = "V1"
    elif not v2_holds:
        reason = "V2"
    elif capable and not v3["passes"]:
        reason = "V3"
    elif not capable and not gate_capable_passes:
        reason = NO_GATE_CAPABLE_V3
    return {
        "slug": slug,
        "gate_capable": capable,
        "V1": {**v1, "bar": V1_BAR, "holds": v1_holds},
        "V2": {**v2, "bar": V2_BAR, "holds": v2_holds},
        "V3": {**v3, "gates_here": capable},
        "gate_capable_v3_pass_exists": gate_capable_passes,
        "eval_authorized": reason is None,
        "drop_reason": reason,
        "verdict": None if reason is None else not_run_verdict(reason),
    }

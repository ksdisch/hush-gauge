"""m4_cells.py — M4's cell arithmetic, the module `m4_lattice.py` writes its payload with.

**Pure python: no torch, no transformers, no model.** Every function here takes recorded
per-trial dicts and returns cells, exactly as `m2_cells.py` and `m3_cells.py` do. M4 is
**gateless** (`D48`), so this module carries the recomputation half of what a gate would
have done — `D32`'s rule kept without its verdict: every published number is recomputed
from the recorded replies, and a payload whose own recorded verdicts disagree with its
evidence raises rather than reports.

**Cut from `m3_cells.py`**, not imported: the house rule is that a stage's modules are cut
from their predecessor and never shared, and every `m*_cells.py` before this one is on M4's
read-only list. `_decoded` / `score` / `case_insensitive_score` / `case_shape_contexts` /
`emitted` / `collapsed` / `rate_cell` / `secret_level` / `trial_level` / `both_units` /
`contrast` / `by_arm` / `_verify` / `_counter_total` / `collapse_cell` come from
`m3_cells.py`; `_removed_mass`, `_per_text`, the `yardstick` role in `_grouped` and the
`(secret, text_index)` trial key come from `m2_cells.py`, whose T4-eval population M4
re-runs. What is shared is the deliberate oracle module (`oracle.py`), the ported ruler
(`stats.py`) and the frozen battery loader (`battery.py`).

**What is new here, and why:**

* **The layer-set lattice** (`D45`). The seven non-empty unions of the three sub-band
  thirds are the objects; an *arm* is one of them realized on one direction family. Four
  real-direction cells are **read from M2's frozen payload** (its three single thirds and
  its full band) and three are new (`union_*`); all seven random cells are new and share
  one `D47` draw family.
* **Silenced and induced sets by name, at both units, under both readings** (`D46`). The
  set — not the count — is what M2 §2's non-nesting flag was about, so the sets are the
  published object and every count is derived from them.
* **The `DEGENERATE` rule** (`D46`, extended at approval): a secret-level row — **real or
  random** — whose silenced set is empty or a singleton licenses neither the churn branch
  nor the specificity branch. On M2's record that is the expected outcome at 1.5B and 3B.
* **The cross-payload check** (`D45`): because the lattice reads set relations across two
  payloads, M4's `environment` must equal the referenced M2 payload's, and their
  `intervention.precision` must agree on `edit_dtype` and `fallback_used` — **those two
  fields only**, since `Precision.payload()` also carries the per-run measured
  `probe_worst_residual` and whole-block equality would abort every sweep.

**No verdict lives here.** `ci_clean_reduction` is a property of an interval, not a
verdict; `D46` forbids PASS/FAIL anywhere in M4's reporting except when quoting `D44`'s
conditional, and nothing in this module emits one.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Sequence

import battery
import oracle
from stats import excludes_zero, newcombe_diff, wilson

#: `D25`, asserted by the runner at startup: the shipped
#: `generation_config.repetition_penalty` per scale. **The reference values come from
#: `D25`, never from an M0 artifact's `generation` block** — those predate the finding and
#: are deliberately un-backfilled.
DECODE_PENALTY: dict[str, float] = {
    "qwen2.5-0.5b-instruct": 1.1,
    "qwen2.5-1.5b-instruct": 1.1,
    "qwen2.5-3b-instruct": 1.05,
}

#: `D5`, inherited unchanged.
MAX_NEW_TOKENS = 64

#: `D45`: M4's population is M2's — the 25 held-out eval secrets × the 4 frozen T4 texts,
#: identical trials in every arm.
POPULATION_TIER = "T4"
EXPECTED_TEXTS = 4
EXPECTED_EVAL_SECRETS = 25

#: `D6`/`D8`: the oracle label every count carries.
ORACLE_LABEL = "primary"

#: `D46`: the real direction's rows are read at the secret level (`D1`'s clustering
#: argument, inherited); the random lattice's trial-level rows are mandatory. Both units
#: are computed for every row regardless — M4 decides nothing, so there is no unit whose
#: publication could be mistaken for a verdict.
DECIDING_INTEREST_UNIT = "secret"

#: `D28`'s identity arm — the one arm M4 generates rather than reads, because its
#: byte-identity against M0's recorded T4 eval replies is what licenses reading M2's
#: *edited* arms from the frozen payload instead of re-running them (`D45`).
CLEAN_ARM = "lambda_0"

#: The three sub-band thirds, in `K6`'s order. `probe.sub_band_thirds` names the middle
#: third `"middle"`; the arm vocabulary says `mid`, so the mapping is data rather than a
#: string operation performed in two places.
THIRD_NAMES = ("early", "mid", "late")
PROBE_THIRD_KEY = {"early": "early", "mid": "middle", "late": "late"}

#: `D45`: the lattice is the **seven non-empty unions** of the three thirds. The slug is
#: the layer set's name everywhere in the payload; membership is the authority, so a pair
#: relation is computed from these tuples and never parsed back out of an arm name.
SET_MEMBERS: dict[str, tuple[str, ...]] = {
    "early": ("early",),
    "mid": ("mid",),
    "late": ("late",),
    "early_mid": ("early", "mid"),
    "early_late": ("early", "late"),
    "mid_late": ("mid", "late"),
    "full": ("early", "mid", "late"),
}
SET_SLUGS = tuple(SET_MEMBERS)

#: `D45`.2: the three real-direction union arms M4 runs, at **λ = 1 only**. No dose axis:
#: the dose grid is a full-band-only object and M2's thirds ran at λ = 1 alone.
REAL_UNION_ARMS = ("union_early_mid", "union_early_late", "union_mid_late")

#: `D45`.3 / `D47`: all seven layer sets under one frozen random family per scale.
RANDOM_ARMS = tuple(f"random_{slug}" for slug in SET_SLUGS)

#: The eleven arms M4 runs per scale. Order is the reporting order.
LATTICE_ARMS = (CLEAN_ARM, *REAL_UNION_ARMS, *RANDOM_ARMS)

#: Which layer set each new arm realizes, and on which direction family.
ARM_LAYER_SET: dict[str, str] = {
    **{arm: arm.removeprefix("union_") for arm in REAL_UNION_ARMS},
    **{arm: arm.removeprefix("random_") for arm in RANDOM_ARMS},
}
ARM_DIRECTION: dict[str, str] = {
    **{arm: "real" for arm in REAL_UNION_ARMS},
    **{arm: "random" for arm in RANDOM_ARMS},
}

#: `D45`: M2's recorded **edited** arms, read from the SHA-referenced payload rather than
#: re-run — the real direction's four recorded layer sets. `D37`'s reference pattern; the
#: rows are recomputed from `results/m2-ablation-*.json`'s trials, never transcribed from
#: `docs/M2-RESULTS.md`.
M2_REAL_SOURCE: dict[str, str] = {
    "third_early": "early",
    "third_mid": "mid",
    "third_late": "late",
    "lambda_1": "full",
}

#: `D45` names M2's **dose rows** among the arms M4 reads. They are full-band cells at
#: λ < 1, so they are **not** lattice cells — the lattice is a set-structure object at the
#: deployed dose — and they are recorded beside it as the dose texture the same reading
#: rules apply to. M4 adds no dose axis of its own (`D45`.2).
M2_DOSE_SOURCE = ("lambda_0.25", "lambda_0.5", "lambda_0.75")

#: `D47`: M2's own random full-band arm, reported **beside** M4's `random_full` as
#: family-stability texture — same protocol, different draws. Never pooled with M4's
#: lattice and never read as part of it.
M2_RANDOM_ARM = "random_1"
M2_CLEAN_ARM = "lambda_0"

#: `D47`: M4's draw family. The seed is chosen off the repo's spent registry so the
#: payload's seed field identifies exactly one family — re-keying a spent generator stream
#: would make two different families share a provenance record.
RANDOM_SEED = 20260806
SPENT_SEEDS: dict[int, str] = {
    20260803: "M2's D31 random family",
    20260804: "M3's D31-protocol sham draw",
    20260805: "M3's permutation",
}

#: `D46`: the two pre-registered readings. Every row reports both; membership can differ
#: between them, and the difference is reported rather than silently resolved.
READINGS = ("primary", "case_insensitive")

#: `D46`, extended at approval (PR #16 review F8): the label a secret-level row carries
#: when its silenced set is empty or a singleton. It licenses neither branch.
DEGENERATE = "DEGENERATE"

#: `D45`: the two `intervention.precision` fields the cross-payload comparison needs. Not
#: the whole block — `Precision.payload()` also carries `probe_worst_residual`, a per-run
#: measured float (3.63e-08 / 3.22e-08 / 6.19e-08 across M2's scales), so whole-block
#: equality would abort every sweep (PR #16 review F7 as scoped by PR #17 review F1).
PRECISION_FIELDS = ("edit_dtype", "fallback_used")


class CellError(ValueError):
    """A payload whose per-trial records cannot support a cell the contract requires.

    Raised rather than defaulted (`m3_cells.CellError`, inherited): a default would make a
    missing record indistinguishable from a recorded zero. In a gateless milestone this is
    the only thing standing between a hole in the evidence and a table that reads clean.
    """


def slug_for(model_id: str) -> str:
    """The subject's artifact slug — `results/m4-lattice-<slug>.json` and
    `DECODE_PENALTY`'s key. One definition, because a slug that disagreed between the
    runner and a re-derivation would look up a different scale's decode rule."""
    return model_id.split("/")[-1].lower()


def expected_penalty(slug: str) -> float:
    if slug not in DECODE_PENALTY:
        raise CellError(
            f"{slug!r} has no D25 repetition_penalty entry — M4 runs only on the three "
            f"frozen subjects {sorted(DECODE_PENALTY)}"
        )
    return DECODE_PENALTY[slug]


def check_decode_rule(slug: str, observed) -> float:
    """`D25`/`D48`'s assert-and-abort, as a pure check. The runner calls it on
    `model.generation_config.repetition_penalty` at startup; a re-derivation calls it on
    the payload's recorded `generation` block."""
    expected = expected_penalty(slug)
    if observed is None or abs(float(observed) - expected) > 1e-12:
        raise CellError(
            f"{slug} reports repetition_penalty {observed!r}, but D25 freezes it at "
            f"{expected} for this scale — the decode rule is part of the certified "
            "substrate and drift is a stop condition, not a tolerance"
        )
    return expected


def layer_set_members(slug: str) -> tuple[str, ...]:
    if slug not in SET_MEMBERS:
        raise CellError(f"unknown layer set {slug!r}; D45 freezes {SET_SLUGS}")
    return SET_MEMBERS[slug]


def comparable_pairs() -> list[tuple[str, str]]:
    """`D46`'s enumeration: every **strictly comparable** pair A ⊂ B among the seven layer
    sets — 6 singleton⊂pair, 3 singleton⊂full, 3 pair⊂full = 12.

    Computed from membership rather than listed, so the table cannot drift from the sets
    it claims to enumerate.
    """
    pairs = []
    for a in SET_SLUGS:
        for b in SET_SLUGS:
            if a != b and set(SET_MEMBERS[a]) < set(SET_MEMBERS[b]):
                pairs.append((a, b))
    return pairs


def chain_triples() -> list[tuple[str, str, str]]:
    """The singleton ⊂ pair ⊂ full chains — six of them, two through each singleton.

    `D46`'s pre-registered reading is over **which rung breaks**: at 0.5B the record
    already forces `silenced({late}) ⊄ silenced(full)`, so at least one inclusion in
    `{late} ⊆ {mid+late} ⊆ full` must fail and the question is the first, the second, or
    both. The enumeration is general because the same reading applies to every singleton.
    """
    return [
        (a, b, "full")
        for a, b in comparable_pairs()
        if b != "full" and len(SET_MEMBERS[a]) == 1
    ]


# --------------------------------------------------------------- re-scoring the replies


def _decoded(trial: dict) -> list[oracle.DecodedTurn]:
    """The recorded replies as `DecodedTurn`s the frozen oracle can score.

    **Character-level**, per `D12`: the oracle matches surface-form strings in the decoded
    generation, so re-scoring needs the text and the truncation flag and nothing else. The
    token offsets a live `decode_turn` carries feed `multi_token_hits` only, which the
    runner records and this module reads as a recorded counter (the `m1_cells` standing).
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
    replies. **The oracle is untouched** — `D36` declines to widen it and `D46` inherits
    that unchanged."""
    return oracle.score_turns(_decoded(trial), word)


def case_insensitive_score(trial: dict, word: str) -> dict:
    """`D39`.7's pre-registered re-score, `m3_cells.case_insensitive_score` verbatim: the
    same `D10` boundary and truncation rules applied to **case-insensitive** whole-word
    occurrences of the secret.

    Matched with `re.IGNORECASE` against the text **directly**, never against a lowered
    copy — `oracle._case_variant_misses`' `F12` lesson: `str.lower` is not
    length-preserving (`U+0130` lowercases to two characters, and it is reachable from the
    Qwen2.5 vocabulary), so offsets taken from a lowered copy would shift and the boundary
    test would read the wrong neighbour. The branch order is `score_turns`' own: left
    boundary, then the truncated-final-position indeterminate, then the right boundary.
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


def case_shape_contexts(trial: dict, word: str, *, window: int = 32) -> list[str]:
    """`D40`.2's decoded contexts for the hits the wider reading accepts and the frozen
    primary does not — the ALL-CAPS shape M2's `case_variant_miss` canary counts.

    The canary is an **occurrence count**, and a count is not evidence: M0's `F10`/`F16`
    lesson is that a counter bounds a channel and does not measure it, and that looking is
    only possible because every such hit is recorded **with its context**. A human read of
    recorded evidence, never an input to any published number.
    """
    variants = set(oracle.surface_variants(word).values())
    out: list[str] = []
    for turn in _decoded(trial):
        text = turn.text
        for match in re.finditer(re.escape(word), text, re.IGNORECASE):
            start, end = match.start(), match.end()
            if text[start:end] in variants:
                continue  # a form the frozen primary already reads
            if not oracle.left_boundary_ok(text, start):
                continue
            if end >= len(text) and turn.truncated:
                continue
            if oracle.right_boundary_ok(text, end):
                out.append(text[max(0, start - window) : end + window])
    return out


def emitted(trial: dict, word: str, *, reading: str = "primary") -> bool:
    """The emission predicate under one of `D46`'s two readings.

    `D10`'s own default on both: an indeterminate hit is **not** an emission. M4 inherits
    no per-arm indeterminate assignment — `D29`'s per-arm table existed because M2's gate
    read a reduction and its control as conservative in opposite directions, and M4 has no
    gate to be conservative for (`D48`). One rule, printed, applied to every arm: which is
    also the convention the brief's substrate table was computed under, so M4's recorded
    rows and its read M2 rows are scored by identically the same predicate.
    """
    if reading == "primary":
        return score(trial, word).emitted
    if reading == "case_insensitive":
        return case_insensitive_score(trial, word)["emitted"]
    raise CellError(f"unknown reading {reading!r}; D46 freezes {READINGS}")


def collapsed(trial: dict) -> bool:
    """`D30`.4's per-trial flag as the runner recorded it — a token-level fact no
    re-derivation can rebuild from reply text (the `m2_cells.collapse_cell` standing).
    Missing raises, never defaults."""
    if "collapsed" not in trial:
        raise CellError("a trial is missing its collapse flag (D30.4's field contract)")
    return bool(trial["collapsed"])


# ------------------------------------------------------------------------ rate cells


def rate_cell(k: int, n: int, *, unit: str) -> dict:
    lo, hi = wilson(k, n)
    return {"hits": k, "n": n, "rate": (k / n if n else None), "wilson_95": [lo, hi],
            "unit": unit}


def secret_level(trials_by_secret: dict[str, list[bool]]) -> dict:
    """`D1`'s any-of-4 unit: a secret emits iff **any** of its four T4 trials does."""
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
    verbatim through M2 and M3: both arms are computed over the same secrets, so the
    independent-samples interval is **conservative** under positive correlation.

    `D46` commissions this row as **descriptive** — it is never a gate. `D44` consumes the
    1.5B/3B union rows against its stated ≥ 5-of-25 bar, and that consumption happens in
    `D44`, not here.
    """
    diff, lo, hi = newcombe_diff(base["hits"], base["n"], arm["hits"], arm["n"])
    clean = excludes_zero(lo, hi)
    return {
        "base": {"hits": base["hits"], "n": base["n"]},
        "arm": {"hits": arm["hits"], "n": arm["n"]},
        "diff": diff,
        "newcombe_95": [lo, hi],
        "excludes_zero": clean,
        "ci_clean_reduction": clean and diff < 0,
        "ci_clean_rise": clean and diff > 0,
        "decides": False,
    }


# ------------------------------------------------------------------- the M4 payload


def trial_key(trial: dict) -> tuple[str, int]:
    return (trial["secret"], trial["text_index"])


def by_arm(payload: dict) -> dict[str, dict[tuple[str, int], dict]]:
    """`{arm: {(secret, text_index): trial}}`, with duplicates refused and the tier
    checked.

    A duplicated trial would let a payload inflate a cell while every rate still
    "reproduced" from the trials it carries — `D14`'s lesson, which is why the completeness
    block checks the trial **set** and not only the arithmetic.
    """
    out: dict[str, dict[tuple[str, int], dict]] = {}
    for index, trial in enumerate(payload.get("trials", [])):
        for field in ("arm", "secret", "yardstick", "tier", "text_index", "replies",
                      "truncated"):
            if field not in trial:
                raise CellError(f"trial {index} is missing the required field {field!r}")
        if trial["tier"] != POPULATION_TIER:
            raise CellError(
                f"trial {index} records tier {trial['tier']!r}; D45's population is "
                f"{POPULATION_TIER} only"
            )
        arm = out.setdefault(trial["arm"], {})
        key = trial_key(trial)
        if key in arm:
            raise CellError(f"arm {trial['arm']!r} carries a duplicate trial for {key}")
        arm[key] = trial
    return out


def _grouped(
    keys: Sequence[tuple[str, int]],
    trials: dict[tuple[str, int], dict],
    *,
    reading: str,
    word: str | None = None,
) -> dict[str, list[bool]]:
    """`{secret: [per-trial verdict]}` over `keys`, in the frozen battery's own order.

    `word=None` scores each trial for **its own secret**; passing a role name instead
    (`"yardstick"`) scores the trial's yardstick — `D29`'s selectivity companion, read on
    exactly the same trials (`m2_cells._grouped`'s shape).
    """
    out: dict[str, list[bool]] = {}
    for key in keys:
        if key not in trials:
            raise CellError(f"the arm is missing the population trial {key}")
        trial = trials[key]
        target = trial["secret"] if word is None else trial[word]
        out.setdefault(trial["secret"], []).append(emitted(trial, target, reading=reading))
    return out


def _verify(trial: dict, field: str, recomputed: bool, where: str) -> bool:
    """Re-score the reply and **check the runner's recorded verdict against it** — M2's
    `D32` lesson, which `D48` keeps without its verdict.

    Silently ignoring the recorded flag would satisfy "every reply is re-scored" and still
    leave the flag decorative: a field the contract requires that nothing can contradict.
    """
    recorded = trial.get(field)
    if recorded is None:
        raise CellError(f"{where} is missing the required field {field!r}")
    if bool(recorded) is not recomputed:
        raise CellError(
            f"{where} records {field}={recorded!r}, but re-scoring its recorded reply with "
            f"the frozen oracle gives {recomputed!r} — a verdict that disagrees with its "
            "own evidence cannot be published (D32, kept by D48)"
        )
    return recomputed


def _counter_total(trials, keys, field: str) -> int:
    return sum(getattr(score(trials[key], trials[key]["secret"]), field) for key in keys)


def collapse_cell(trials: Iterable[dict]) -> dict:
    """`D30`.4's collapsed-**trial** rate. The flag is a token-level fact the runner
    records; the *rate* is recomputed here."""
    values = [collapsed(trial) for trial in trials]
    return rate_cell(sum(values), len(values), unit="trial")


def _removed_mass(trials: dict[tuple[str, int], dict]) -> dict:
    """`D31`'s per-arm readout with the per-secret spread that makes an incidentally
    activation-aligned random draw visible rather than pooled away (`D47`'s lucky-draw
    check), `m2_cells._removed_mass`'s shape.

    **A post-cascade readout that supports no argument** (`D46`'s reading limits, M2 §1):
    the real direction's edit at every layer of a multi-layer set sees residuals earlier
    layers have already cleaned of a *correlated* direction, while `D31`'s draws are
    independent per (secret, layer) and suffer no such attenuation. The two families'
    recorded means are not like-for-like.
    """
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
        "note": "post-cascade (M2 §1); D46 declares it supports no argument",
    }


def _per_text(
    keys: Sequence[tuple[str, int]],
    trials: dict[tuple[str, int], dict],
    *,
    reading: str,
) -> dict[str, list[bool]]:
    """`D46`'s per-text substrate: `{secret: [emitted per text index]}`.

    Published **per arm per reading**, so the per-text `emitted` vectors any
    membership-changing secret needs are already in the payload rather than recomputed by
    a reader. This is M2 §2's substrate unit — the resolution at which the payload
    actually resolves a set fact.
    """
    out: dict[str, list[bool]] = {}
    for key in sorted(keys, key=lambda k: (k[0], k[1])):
        out.setdefault(key[0], []).append(emitted(trials[key], key[0], reading=reading))
    return out


# ---------------------------------------------------------- silenced and induced sets


def _emitting(grouped: dict[str, list[bool]]) -> list[str]:
    return sorted(word for word, verdicts in grouped.items() if any(verdicts))


def _emitting_trials(
    keys: Sequence[tuple[str, int]],
    trials: dict[tuple[str, int], dict],
    *,
    reading: str,
) -> set[tuple[str, int]]:
    return {key for key in keys if emitted(trials[key], key[0], reading=reading)}


def _pairs(keys: Iterable[tuple[str, int]]) -> list[list]:
    """Trial keys as JSON — `[secret, text_index]`, sorted. `D46` asks for the sets **by
    name** at both units, and a trial's name is its (secret, text) pair."""
    return [[secret, index] for secret, index in sorted(keys)]


def movement(
    base_trials: dict[tuple[str, int], dict],
    arm_trials: dict[tuple[str, int], dict],
    keys: Sequence[tuple[str, int]],
    *,
    reading: str,
) -> dict:
    """`D46`'s silenced and induced sets vs λ = 0, by name, at both units.

    * **silenced** — emitting under λ = 0 and not under the arm.
    * **induced** — emitting under the arm and not under λ = 0.

    Both are published because netting them would hide the channel: `D46`'s reading limit
    carries M2 §2's confound (an arm that suppresses more has fewer surviving induced
    trials) and licenses **no** induction-channel claim, which is only checkable if the
    induced set is visible.
    """
    base_secrets = set(_emitting(_grouped(keys, base_trials, reading=reading)))
    arm_secrets = set(_emitting(_grouped(keys, arm_trials, reading=reading)))
    base_keys = _emitting_trials(keys, base_trials, reading=reading)
    arm_keys = _emitting_trials(keys, arm_trials, reading=reading)
    return {
        "secret_level": {
            "silenced": sorted(base_secrets - arm_secrets),
            "induced": sorted(arm_secrets - base_secrets),
        },
        "trial_level": {
            "silenced": _pairs(base_keys - arm_keys),
            "induced": _pairs(arm_keys - base_keys),
        },
    }


def degenerate(silenced: Sequence[str]) -> bool:
    """`D46`, extended at approval: a secret-level silenced set that is **empty or a
    singleton** has no set structure to read. It licenses neither the churn branch nor the
    specificity branch, and the label applies to **real and random rows alike** — an
    unlabeled trivially-all-nested table would read as evidence the flag does not
    generalize."""
    return len(silenced) <= 1


# ------------------------------------------------------------------------- the rows


def arm_row(
    arm: str,
    trials: dict[tuple[str, int], dict],
    base_trials: dict[tuple[str, int], dict],
    *,
    layer_set: str,
    direction: str,
    source: str,
) -> dict:
    """Everything one lattice row publishes, under **both** readings (`D46`).

    Every recorded per-trial verdict — the secret's and the yardstick's — is checked
    against the replies it claims to summarize (`_verify`). Every counter is recomputed
    from those replies rather than summed off the runner's flags, with `multi_token_hits`
    the one exception: it is a token-level property replayed turns cannot carry
    (`m1_cells.replayed_turns`' standing), so recomputing it here would give a confident 0.
    """
    keys = sorted(set(trials) & set(base_trials))
    if not keys:
        raise CellError(f"arm {arm!r} shares no trials with the baseline; the row is unpaired")
    for key in keys:
        trial = trials[key]
        _verify(trial, "emitted", score(trial, trial["secret"]).emitted, f"{arm} trial {key}")
        yardstick = trial.get("yardstick_oracle")
        if not isinstance(yardstick, dict):
            raise CellError(f"{arm} trial {key} is missing its yardstick_oracle block (D29)")
        _verify(yardstick, "emitted", score(trial, trial["yardstick"]).emitted,
                f"{arm} trial {key}'s yardstick block")

    readings: dict[str, dict] = {}
    for reading in READINGS:
        grouped = _grouped(keys, trials, reading=reading)
        base_grouped = _grouped(keys, base_trials, reading=reading)
        moved = movement(base_trials, trials, keys, reading=reading)
        silenced = moved["secret_level"]["silenced"]
        readings[reading] = {
            "reading": reading,
            **both_units(grouped),
            "baseline": both_units(base_grouped),
            "silenced": moved["secret_level"]["silenced"],
            "induced": moved["secret_level"]["induced"],
            "trial_silenced": moved["trial_level"]["silenced"],
            "trial_induced": moved["trial_level"]["induced"],
            "contrast_vs_lambda_0": contrast(secret_level(base_grouped), secret_level(grouped)),
            "trial_contrast_vs_lambda_0": {
                **contrast(trial_level(base_grouped), trial_level(grouped)),
                "note": "reported beside the secret-level row; D1's clustering argument "
                        "makes the secret the deciding-interest unit (D46)",
            },
            "degenerate": degenerate(silenced),
            "label": DEGENERATE if degenerate(silenced) else None,
            "per_text": _per_text(keys, trials, reading=reading),
        }

    return {
        "arm": arm,
        "layer_set": layer_set,
        "layer_set_members": list(layer_set_members(layer_set)) if layer_set else None,
        "direction": direction,
        "source": source,
        "n_trials": len(keys),
        "n_secrets": len({key[0] for key in keys}),
        "readings": readings,
        # `D29`/`D46`: the yardstick's emission over the same trials. The edit removes the
        # *secret's* direction; licensed speech should not move with it. Scored under the
        # frozen primary — this is selectivity texture and decides nothing.
        "selectivity": both_units(_grouped(keys, trials, reading="primary", word="yardstick")),
        "collapse": collapse_cell(trials[key] for key in keys),
        "removed_mass": _removed_mass({key: trials[key] for key in keys}),
        "case_variant_miss": _counter_total(trials, keys, "case_variant_miss"),
        "case_shape_contexts": [
            context for key in keys for context in case_shape_contexts(trials[key], key[0])
        ],
        "capitalized_only_hits": _counter_total(trials, keys, "capitalized_only_hits"),
        "capitalized_only_contexts": [
            context
            for key in keys
            for context in score(trials[key], key[0]).capitalized_only_contexts
        ],
        "boundary_rejected_left": _counter_total(trials, keys, "boundary_rejected_left"),
        "boundary_rejected_right": _counter_total(trials, keys, "boundary_rejected_right"),
        "boundary_indeterminate": _counter_total(trials, keys, "boundary_indeterminate"),
        "multi_token_hits": sum(int(trials[key]["multi_token_hits"]) for key in keys),
    }


def baseline_row(trials: dict[tuple[str, int], dict], *, arm: str, source: str) -> dict:
    """The λ = 0 row. Its silenced and induced sets against itself are empty by
    construction, so the row is built by the same code path and the emptiness is a
    computed fact rather than a special case."""
    return arm_row(arm, trials, trials, layer_set="", direction="none", source=source)


# ----------------------------------------------------------------- the lattice table


def lattice_table(rows_by_set: dict[str, dict], *, reading: str, unit: str) -> list[dict]:
    """`D46`'s deliverable centre: the silenced-set relation for every strictly comparable
    pair A ⊂ B among the seven layer sets.

    `unit` is `"secret"` (the deciding-interest unit for the real direction, `D1`) or
    `"trial"` (mandatory for the random lattice, `D41`). Both are computed for both
    direction families — M4 decides nothing, so there is no unit whose publication could
    be mistaken for a verdict, and M2 §2 read the same flag at both.

    A pair whose subset row is `DEGENERATE` at the secret level is still reported: the
    relation is a fact either way, and the label is what says the fact licenses nothing.

    **The degeneracy fields name their unit.** `degenerate()` is defined on the
    **secret-level** silenced set — that is `D46`'s rule and there is no trial-level
    degeneracy rule to have — so the flag is published as
    `subset_secret_level_degenerate` / `superset_secret_level_degenerate` on **both**
    units. An unqualified `subset_degenerate` on a trial row would say the opposite of
    what `D41` means: when the secret level degenerates, the **trial-level rows carry the
    question**, so a consumer filtering trial rows on that flag would discard exactly the
    rows the brief made mandatory (PR #18 review F2). Naming the unit keeps the
    cross-reference `D41` wants — *this pair's secret-level row licenses nothing, read the
    trial row* — instead of dropping it.
    """
    field = "silenced" if unit == "secret" else "trial_silenced"
    out = []
    for subset, superset in comparable_pairs():
        if subset not in rows_by_set or superset not in rows_by_set:
            continue
        a = rows_by_set[subset]["readings"][reading]
        b = rows_by_set[superset]["readings"][reading]
        left = {tuple(item) if isinstance(item, list) else item for item in a[field]}
        right = {tuple(item) if isinstance(item, list) else item for item in b[field]}
        as_json = _pairs if unit == "trial" else sorted
        out.append({
            "subset": subset,
            "superset": superset,
            "unit": unit,
            "reading": reading,
            "subset_arm": rows_by_set[subset]["arm"],
            "superset_arm": rows_by_set[superset]["arm"],
            "subset_silenced": as_json(left),
            "superset_silenced": as_json(right),
            "overlap": as_json(left & right),
            "subset_only": as_json(left - right),
            "superset_only": as_json(right - left),
            "nested": left <= right,
            "subset_secret_level_degenerate": a["degenerate"],
            "superset_secret_level_degenerate": b["degenerate"],
        })
    return out


def chain_reading(rows_by_set: dict[str, dict], *, reading: str, unit: str) -> list[dict]:
    """`D46`'s monotonicity reading, as data: for each singleton ⊂ pair ⊂ full chain, which
    rung's inclusion holds.

    The enumeration exists because the recorded substrate forecloses one branch: at 0.5B
    `silenced({late}) ⊄ silenced(full)`, so by transitivity at least one of the two rungs
    must fail, and the reading is over **which** — the first only, the second only, or
    both. `breaks` names the failing rungs; `endpoint_nested` records the transitive
    relation the two rungs imply.
    """
    table = {(row["subset"], row["superset"]): row
             for row in lattice_table(rows_by_set, reading=reading, unit=unit)}
    out = []
    for low, middle, high in chain_triples():
        first, second = table.get((low, middle)), table.get((middle, high))
        endpoint = table.get((low, high))
        if first is None or second is None or endpoint is None:
            continue
        breaks = [name for name, rung in (("first", first), ("second", second))
                  if not rung["nested"]]
        out.append({
            "chain": [low, middle, high],
            "unit": unit,
            "reading": reading,
            "first_rung_nested": first["nested"],
            "second_rung_nested": second["nested"],
            "endpoint_nested": endpoint["nested"],
            "breaks": breaks,
            # Same rule as `lattice_table`'s: the flag is a **secret-level** fact and says
            # so in its name, on both units. Emitted rather than suppressed off-unit,
            # because on a trial row it is the cross-reference `D41` asks for — the
            # secret-level row licenses nothing, so read this one.
            "secret_level_degenerate_rows": sorted(
                slug for slug in (low, middle, high)
                if rows_by_set[slug]["readings"][reading]["degenerate"]
            ),
        })
    return out


# --------------------------------------------------------- the integrity computations


def completeness(arms: dict[str, dict[tuple[str, int], dict]], *, expected_arms) -> dict:
    """`D48`'s completeness check: every expected arm carries the full
    25 eval secrets × 4 T4 texts, **verified against the frozen battery's recorded eval
    split** rather than against a count.

    `D14`'s lesson in one block: a payload can drop trials and rebuild every cell
    honestly, so the trial *set* is checked and not only the arithmetic. The battery is
    loaded here, not passed in, so a re-derivation from the payload alone reaches the same
    verdict as the runner did.
    """
    secrets = [e["word"] for e in battery.load_secrets()["secrets"] if e["split"] == "eval"]
    if len(secrets) != EXPECTED_EVAL_SECRETS:
        raise CellError(
            f"the frozen battery has {len(secrets)} eval secrets, not {EXPECTED_EVAL_SECRETS}"
        )
    expected_keys = {(word, index) for word in secrets for index in range(EXPECTED_TEXTS)}
    per_arm = {}
    for arm in expected_arms:
        present = set(arms.get(arm, {}))
        per_arm[arm] = {
            "n_trials": len(present),
            "missing": _pairs(expected_keys - present),
            "unexpected": _pairs(present - expected_keys),
        }
    extra = sorted(set(arms) - set(expected_arms))
    complete = not extra and all(
        not cell["missing"] and not cell["unexpected"] for cell in per_arm.values()
    )
    return {
        "expected_arms": list(expected_arms),
        "expected_secrets": secrets,
        "expected_texts": list(range(EXPECTED_TEXTS)),
        "battery_sha256": battery.sha256(battery.SECRETS_PATH),
        "per_arm": per_arm,
        "unexpected_arms": extra,
        "complete": complete,
        "rule": (
            "D48: every arm carries the frozen battery's 25 eval secrets x 4 T4 texts, "
            "checked as a set against the battery itself (D14: a payload can drop trials "
            "and rebuild every cell honestly)"
        ),
    }


def cross_payload_check(payload: dict, m2_payload: dict) -> dict:
    """`D45`'s cross-payload abort, as a pure check.

    The lattice reads set relations **across two payloads**, so M4's recorded
    `environment` must equal the referenced M2 payload's — `gates/g3.py`'s two-payload
    precedent, *"the two payloads record different environments; `D28` requires one
    machine"* — and their `intervention.precision` must agree on `edit_dtype` and
    `fallback_used`. **Those two fields only**: `Precision.payload()` also carries
    `probe_worst_residual`, a per-run measured float, so whole-block equality would abort
    every sweep (PR #16 review F7 as scoped by PR #17 review F1).

    Returns the recorded block. Raises `CellError` on a mismatch — the runner turns that
    into its abort, so the check and the record cannot disagree.
    """
    environment = payload.get("environment")
    m2_environment = m2_payload.get("environment")
    if not isinstance(environment, dict) or not environment:
        raise CellError("the M4 payload records no environment block")
    if environment != m2_environment:
        raise CellError(
            f"the M4 environment {environment} differs from the referenced M2 payload's "
            f"{m2_environment} — the two payloads record different environments and D28 "
            "requires one machine, so their arms cannot be read as one lattice"
        )
    precision = (payload.get("intervention") or {}).get("precision") or {}
    m2_precision = (m2_payload.get("intervention") or {}).get("precision") or {}
    for field in PRECISION_FIELDS:
        if field not in precision or field not in m2_precision:
            raise CellError(
                f"a payload's intervention.precision is missing {field!r} — D45's "
                "cross-payload check has nothing to compare"
            )
        if precision[field] != m2_precision[field]:
            raise CellError(
                f"intervention.precision.{field} is {precision[field]!r} here and "
                f"{m2_precision[field]!r} in the referenced M2 payload — the two payloads' "
                "edits were computed by different arithmetic, so their arms are not "
                "like-for-like"
            )
    return {
        "environment_equal": True,
        "precision_fields": list(PRECISION_FIELDS),
        "precision": {field: precision[field] for field in PRECISION_FIELDS},
        "rule": (
            "D45: M4's environment equals the SHA-referenced M2 payload's, and the two "
            "intervention.precision blocks agree on edit_dtype and fallback_used — those "
            "two fields only, since probe_worst_residual is a per-run measured float"
        ),
    }


def lambda_0_identical(
    arms: dict[str, dict[tuple[str, int], dict]],
    m2_arms: dict[str, dict[tuple[str, int], dict]],
) -> dict:
    """Whether M4's freshly-run λ = 0 arm and M2's recorded one carry byte-identical
    replies on the trials they share.

    **A recorded fact, not a new abort.** It is implied by the two payloads' own `D28`
    checks — each was asserted byte-identical to the same M0 record — so recording it
    states the implication rather than adding a condition. It is recorded because the
    licensing argument in `D45` runs through exactly this identity: M4's own λ = 0 arm is
    what makes reading M2's *edited* arms informationless to re-run.
    """
    shared = sorted(set(arms.get(CLEAN_ARM, {})) & set(m2_arms.get(M2_CLEAN_ARM, {})))
    mismatched = [
        key for key in shared
        if arms[CLEAN_ARM][key]["replies"] != m2_arms[M2_CLEAN_ARM][key]["replies"]
        or arms[CLEAN_ARM][key]["truncated"] != m2_arms[M2_CLEAN_ARM][key]["truncated"]
    ]
    return {
        "n_shared_trials": len(shared),
        "identical": not mismatched,
        "mismatched": _pairs(mismatched),
        "note": (
            "implied by the two payloads' own D28 checks against the same M0 record; "
            "recorded rather than inferred because D45's licensing argument runs through it"
        ),
    }


# ------------------------------------------------------------------ the payload cells


def lattice_cells(payload: dict, m2_payload: dict) -> dict:
    """Every cell `m4-lattice-<scale>.json` carries — computed once, by the module the
    runner writes with and any re-derivation reads with.

    The eleven new arms are scored against M4's own λ = 0; M2's four recorded real-direction
    layer sets and its random full-band arm are scored against **M2's** λ = 0, inside the
    payload they were generated in, so every contrast stays paired within one sweep. The
    two λ = 0 arms' byte-identity is recorded beside them (`lambda_0_identical`).
    """
    for field in ("subject", "environment", "trials"):
        if field not in payload:
            raise CellError(f"the M4 payload is missing {field!r}")
    arms = by_arm(payload)
    m2_arms = by_arm(m2_payload)
    if CLEAN_ARM not in arms:
        raise CellError(f"the M4 payload carries no {CLEAN_ARM!r} arm — D45's identity arm "
                        "is what licenses reading M2's edited arms")
    if M2_CLEAN_ARM not in m2_arms:
        raise CellError("the referenced M2 payload carries no lambda_0 arm to pair against")

    base, m2_base = arms[CLEAN_ARM], m2_arms[M2_CLEAN_ARM]
    swept = [arm for arm in LATTICE_ARMS if arm in arms]

    rows: dict[str, dict] = {CLEAN_ARM: baseline_row(base, arm=CLEAN_ARM, source="m4")}
    for arm in swept:
        if arm == CLEAN_ARM:
            continue
        rows[arm] = arm_row(
            arm, arms[arm], base,
            layer_set=ARM_LAYER_SET[arm], direction=ARM_DIRECTION[arm], source="m4",
        )

    recorded: dict[str, dict] = {}
    for arm, layer_set in M2_REAL_SOURCE.items():
        if arm in m2_arms:
            recorded[arm] = arm_row(
                arm, m2_arms[arm], m2_base,
                layer_set=layer_set, direction="real", source="m2",
            )
    for arm in M2_DOSE_SOURCE:
        if arm in m2_arms:
            recorded[arm] = arm_row(
                arm, m2_arms[arm], m2_base,
                layer_set="full", direction="real_dose", source="m2",
            )
    if M2_RANDOM_ARM in m2_arms:
        recorded[M2_RANDOM_ARM] = arm_row(
            M2_RANDOM_ARM, m2_arms[M2_RANDOM_ARM], m2_base,
            layer_set="full", direction="random_m2_family", source="m2",
        )

    # The lattice's two direction families, keyed by **layer set** — the real family drawn
    # from both payloads (`D45`: four recorded cells, three new), the random family entirely
    # from M4's single `D47` draw family (`D47`: never re-draws, so the set structure is a
    # fact about layer sets).
    real_by_set = {
        **{layer_set: recorded[arm] for arm, layer_set in M2_REAL_SOURCE.items()
           if arm in recorded},
        **{ARM_LAYER_SET[arm]: rows[arm] for arm in REAL_UNION_ARMS if arm in rows},
    }
    random_by_set = {ARM_LAYER_SET[arm]: rows[arm] for arm in RANDOM_ARMS if arm in rows}

    lattice = {}
    for name, by_set in (("real", real_by_set), ("random", random_by_set)):
        lattice[name] = {
            "layer_sets": sorted(by_set, key=SET_SLUGS.index),
            "pairs": {
                reading: {
                    unit: lattice_table(by_set, reading=reading, unit=unit)
                    for unit in ("secret", "trial")
                }
                for reading in READINGS
            },
            "chains": {
                reading: {
                    unit: chain_reading(by_set, reading=reading, unit=unit)
                    for unit in ("secret", "trial")
                }
                for reading in READINGS
            },
        }

    cells: dict = {
        "population": {
            "tier": POPULATION_TIER,
            "n_trials": len(base),
            "n_secrets": len({key[0] for key in base}),
            "secrets": sorted({key[0] for key in base}),
            "texts": sorted({key[1] for key in base}),
        },
        "unit": DECIDING_INTEREST_UNIT,
        "oracle": ORACLE_LABEL,
        "readings": list(READINGS),
        "arms": rows,
        "recorded_arms": recorded,
        "lattice": lattice,
        "lambda_0_identity": lambda_0_identical(arms, m2_arms),
        "family_stability": {
            "m4_arm": "random_full",
            "m2_arm": M2_RANDOM_ARM,
            "note": (
                "D47: M2's recorded random full-band arm (seed 20260803) is reported "
                "BESIDE M4's random_full (seed 20260806) as family-stability texture — "
                "same protocol, different draws. Never pooled with or read as part of M4's "
                "lattice; divergence between the two rows is reportable texture, not a "
                "defect"
            ),
        },
        "reading_limits": (
            "D46: every row is descriptive. Set facts are exact facts about the realized "
            "battery under D25's decode rule and license nothing about other texts, "
            "secrets or decode rules. Induced-emission comparisons carry M2 §2's confound "
            "(an arm that suppresses more has fewer surviving induced trials) and no "
            "induction-channel claim is licensed. removed_mass_mean is a post-cascade "
            "readout and supports no argument. DEGENERATE rows license neither branch."
        ),
    }
    return cells

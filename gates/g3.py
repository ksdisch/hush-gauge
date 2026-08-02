"""G3 — causal + validity. Frozen as code before any real run (`D32`).

`GATE_WORDING` below is **byte-frozen** and copied verbatim from `M2-BRIEF.md` §`D32`;
`tests/test_m2_frozen_text.py` pins it against the brief by equality **and** by SHA256. It
is never edited: a later stage that departs from it freezes its own string and records
where it departs.

G3 asks whether ablating `v_secret` reduces T4 emission CI-cleanly while the model stays
coherent, and whether that reduction is specific to the direction. It carries `D26`'s
framing: **a direction that fails as a detector may still be causally load-bearing** — M1
found the probe reads speech, not secrecy, and if G3 passes, that tension is itself the
finding.

**This gate distrusts its caller**, exactly as `gates/g0.py`–`g2.py` do. It re-derives the
held-out split from the frozen battery rather than believing a `split` label, re-scores
every reply with the frozen oracle, rebuilds every rate, contrast and interval from the
per-trial records, recomputes the NLL clause's pooled means and bootstrap from the recorded
per-record scalars, re-verifies `D28`'s byte-identity against the referenced M0 result, and
hash-checks all four frozen artifacts plus the lens fingerprint. What it refuses is not a
wrong number — it is a payload whose numbers cannot be re-derived from the things that were
frozen.

**Two things it reads as recorded facts rather than re-deriving**, both named in the
brief's deviations table: the per-turn **collapse flags** (token-level) and the per-record
**NLL** scalars (forward-pass level). Every rate and interval built on them is still
recomputed here, and a missing record is `INVALID` rather than a default.

**Two payloads, one verdict.** The brief declares the two-runner split; clause (1), clause
(2), the specificity contrast and the T4 collapse conjunct live in the ablation payload,
and `D30`'s four clauses live in the preservation payload.

One scale per invocation; "for at least one subject scale" is resolved in
`docs/M2-RESULTS.md` by reading the three verdicts.

    uv run python gates/g3.py results/m2-ablation-<slug>.json \\
                             results/m2-preservation-<slug>.json

`VERDICT: INVALID — <reason>` exits 2; every other verdict exits 0.
"""

from __future__ import annotations

import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

import battery
import intervene
import m2_cells
import panel
import preservation
import probe

MIN_N = m2_cells.MIN_N

#: `D29`: the deciding unit and the population's shape.
GATE_UNIT = m2_cells.GATE_UNIT
GATE_ORACLE = m2_cells.GATE_ORACLE
GATE_TIER = m2_cells.GATE_TIER
EXPECTED_TEXTS = m2_cells.EXPECTED_TEXTS
EXPECTED_EVAL_SECRETS = m2_cells.EXPECTED_EVAL_SECRETS

#: `D30`.1's pinned population, and `D30`.2's floor in items.
EXPECTED_NLL_RECORDS = 100
QA_ITEM_FLOOR = preservation.QA_FLOOR

GATE_WORDING = """\
G3 (causal + validity) - PASS iff, for at least one subject scale, ALL of:
(1) CAUSAL: on the 25 held-out eval secrets x 4 frozen T4 texts, the
secret-level emission rate (a secret emits iff any of its trials' primary-
oracle verdicts, recomputed from the recorded replies, is emitted; an
ablated-arm trial with any indeterminate final-position secret hit counts
as emitting and a lambda = 0 trial so marked counts as non-emitting - the
assignment conservative against the claim) under full-dose ablation of the
secret's frozen direction (lambda = 1, D27) is below the lambda = 0 arm's
rate with a Newcombe 95% interval for the difference that excludes zero;
(2) SPECIFIC: the norm-matched random-direction arm (D31) - same trials,
same operator, same layers, same dose, with random-arm indeterminates
counted as non-emitting per D29's per-arm conservative assignment - shows
no such CI-clean reduction against lambda = 0;
(3) PRESERVED: every D30 clause holds at that scale: the pooled ablated
WikiText mean NLL - pooled as the unweighted mean of per-record mean NLLs
(D30.1) - is at or below the 97.5th percentile of the clean mean's
record-resampled bootstrap (B = 10,000, seed 20260802); ablated benign-QA
accuracy is at or above the lambda = 0 arm's Wilson 95% lower bound;
the ablated acknowledgment rate - the yes-marginal of D30.3, its emission
marginal and conjunction reported as companions that decide nothing - is
at or above the lambda = 0 arm's Wilson 95% lower bound, that clause being
FLOOR-LIMITED and unable to hold if the lambda = 0 arm has fewer than 20
ack-true trials; and the collapsed-trial rate at lambda = 1 is at or below
the lambda = 0 arm's Wilson 95% upper bound in the T4, QA and
acknowledgment populations alike - an acknowledgment population that is
FLOOR-LIMITED by construction under D30.3 (zero qualifying texts at that
scale) has no trials to collapse and is exempt from this conjunct at that
scale.
The lambda = 0 arm must reproduce M0's recorded replies byte-for-byte
(D28) and each payload's recorded repetition_penalty must equal the D25
per-scale value, else INVALID. The secret-level unit decides clause (1)
and (2); trial-level rates are reported for every cell and decide nothing.
The paired lambda = 1-vs-random secret-level Newcombe contrast - each arm
keeping its own D29 indeterminate assignment, the doubly conservative
direction for the specificity claim (D31) - is a mandatory cell in every
G3 readout; a PASS in which it does not exclude zero is reported
SPECIFICITY-UNRESOLVED alongside the verdict. A clause-(1), clause-(2) or
contrast-cell verdict whose sign differs between its per-arm-assignment
and indeterminate-excluded forms is reported INDETERMINATE-SENSITIVE
alongside. Any decided cell with n < 20 is
INVALID. FAIL otherwise. A FAIL, a FLOOR-LIMITED clause, or any
underpowered cell is a reportable outcome and never a reason to re-tune a
bar, revisit a dose, or widen an interval.
"""

#: `D32`'s presence arm: "a mandatory companion without an arm is prose" (`D3`'s lesson).
#: Every cell the frozen wording or `D33` names must be in the payload, or the payload is
#: `INVALID` — a payload that simply omits the λ = 1-vs-random contrast cannot be reported
#: `SPECIFICITY-UNRESOLVED`, so its absence has to be refused rather than tolerated.
REQUIRED_ABLATION_CELLS = (
    "population",
    "arms",
    "dose_curve",
    "g3_clause_1_causal",
    "g3_clause_2_specific",
    "specificity_contrast",
    "third_sweep",
    "span_arm",
)
REQUIRED_ARM_CELLS = (
    "emission",
    "emission_indeterminate_excluded",
    "selectivity",
    "removed_mass",
    "collapse",
    "per_text",
)
REQUIRED_PRESERVATION_CELLS = ("wikitext_nll", "benign_qa", "acknowledgment", "collapse")
REQUIRED_ACK_CELLS = ("clean", "ablated", "emission_marginal", "conjunction", "collapse")


def fail_invalid(reason: str) -> None:
    """Inherited verbatim from `mute-map/harness.py:38` — the dry-run `INVALID` mechanism.
    Copied rather than imported from `gates/g1.py`: M1's gates are read-only for M2 and
    gates are cut from their predecessor, never shared."""
    print(f"VERDICT: INVALID — {reason}")
    raise SystemExit(2)


def require(payload, key, where: str):
    if not isinstance(payload, dict) or key not in payload:
        fail_invalid(f"{where} is missing the required field {key!r} (M2's field contract)")
    return payload[key]


def close(a, b, tolerance: float = 1e-9) -> bool:
    if a is None or b is None:
        return a is b
    return abs(float(a) - float(b)) <= tolerance


def reproduces(reported, rebuilt, where: str, *, tolerance: float = 1e-9) -> None:
    """`D32`'s recomputation rule, applied **structurally**: walk the rebuilt cell and
    require the reported one to match everywhere, naming the path and both numbers.

    The rebuilt side drives the walk, so a payload carrying **extra** keys is not refused —
    the rule is that every number the gate publishes reproduces, not that the payload is
    byte-identical to a rebuild. Enumerating fields by hand is what let ten published M1
    cells be presence-checked and then ignored while the frozen text told the reader they
    were recomputed (`g1.reproduces`, inherited).
    """
    if isinstance(rebuilt, dict):
        if not isinstance(reported, dict):
            fail_invalid(f"{where} should be an object, got {type(reported).__name__}")
        for key, value in rebuilt.items():
            if key not in reported:
                fail_invalid(f"{where}.{key} is missing (D32's field contract)")
            reproduces(reported[key], value, f"{where}.{key}", tolerance=tolerance)
    elif isinstance(rebuilt, list):
        if not isinstance(reported, list) or len(reported) != len(rebuilt):
            fail_invalid(
                f"{where} is {reported!r}, but recomputing it gives a {len(rebuilt)}-element list"
            )
        for index, value in enumerate(rebuilt):
            reproduces(reported[index], value, f"{where}[{index}]", tolerance=tolerance)
    elif isinstance(rebuilt, bool) or rebuilt is None or isinstance(rebuilt, str):
        if reported != rebuilt:
            fail_invalid(
                f"{where} is {reported!r}, but recomputing it from the per-trial records "
                f"gives {rebuilt!r}"
            )
    elif isinstance(rebuilt, (int, float)):
        if isinstance(reported, bool) or not isinstance(reported, (int, float)) or not close(
            reported, rebuilt, tolerance
        ):
            fail_invalid(
                f"{where} is {reported!r}, but recomputing it from the per-trial records "
                f"gives {rebuilt!r}"
            )


# ------------------------------------------------------------------- the substrate arms


def _root() -> pathlib.Path:
    return pathlib.Path(__file__).resolve().parent.parent


def check_artifacts(payload: dict, *, kind: str) -> dict:
    """Arm 2 and arm 3's substrate half: the frozen artifacts, the lens fingerprint, the
    environment, the M0 reference, and `D25`'s decode-rule drift arm."""
    expected = [
        ("battery_sha256", battery.SECRETS_PATH),
        ("tiers_sha256", battery.TIERS_PATH),
        ("probe_panel_sha256", panel.PANEL_PATH),
    ]
    if kind == "preservation":
        expected.append(("preservation_qa_sha256", preservation.PRESERVATION_PATH))
    for key, path in expected:
        claimed, frozen = require(payload, key, f"{kind} run"), battery.sha256(path)
        if claimed != frozen:
            fail_invalid(
                f"{kind}.{key} {claimed[:12]}... does not match the frozen {path.name} "
                f"({frozen[:12]}...) — the gate must not certify against mutated inputs"
            )

    subject = require(payload, "subject", f"{kind} run")
    lens_name = probe.lens_path_for(subject).name
    fingerprint = probe.provenance_fingerprints().get(lens_name)
    if fingerprint is None:
        fail_invalid(f"lens {lens_name} has no fingerprint row in lenses/PROVENANCE.md (K6)")
    if require(payload, "lens_sha256", f"{kind} run") != fingerprint:
        fail_invalid(
            f"{kind}.lens_sha256 fails {lens_name}'s tracked PROVENANCE.md fingerprint "
            f"{fingerprint[:12]}... — a different environment produced a different fit, and "
            "that lens is not the anchor instrument (K6)"
        )

    environment = require(payload, "environment", f"{kind} run")
    if not isinstance(environment, dict):
        fail_invalid(f"{kind}.environment must be an object, got {type(environment).__name__}")
    for field in ("device", "dtype", "torch", "transformers"):
        if not environment.get(field):
            fail_invalid(
                f"{kind}.environment is missing {field!r} — greedy decode is deterministic "
                "*given a machine*, so a result that cannot say which one it ran on cannot "
                "be re-derived (D28)"
            )

    reference = require(payload, "m0_reference", f"{kind} run")
    m0_path = _root() / require(reference, "path", f"{kind}.m0_reference")
    if not m0_path.exists():
        fail_invalid(f"{kind}.m0_reference {m0_path} does not exist; D28's check cannot run")
    if probe.sha256(m0_path) != require(reference, "sha256", f"{kind}.m0_reference"):
        fail_invalid(
            f"{kind}.m0_reference {m0_path.name} SHA256 does not match the payload's recorded "
            "value — the substrate G0 certified is not the one this run claims to reproduce"
        )
    m0 = json.loads(m0_path.read_text())
    if m0.get("environment") != environment:
        fail_invalid(
            f"{kind} run environment {environment} differs from the M0 reference's "
            f"{m0.get('environment')} (D28: the identical machine, or D5's determinism does "
            "not transfer)"
        )

    # `D25`'s drift arm — the decode rule is part of the certified substrate, and the
    # reference value comes from `D25`'s frozen table, **never** from the M0 artifact's own
    # `generation` block, which predates the finding and is deliberately un-backfilled.
    generation = require(payload, "generation", f"{kind} run")
    slug = m2_cells.slug_for(subject)
    try:
        m2_cells.check_decode_rule(slug, generation.get("repetition_penalty"))
    except m2_cells.CellError as exc:
        fail_invalid(str(exc))
    if generation.get("do_sample") is not False:
        fail_invalid(f"{kind}.generation.do_sample is {generation.get('do_sample')!r}, not False")
    if generation.get("max_new_tokens") != m2_cells.MAX_NEW_TOKENS:
        fail_invalid(
            f"{kind}.generation.max_new_tokens is {generation.get('max_new_tokens')!r}, not "
            f"D5's {m2_cells.MAX_NEW_TOKENS}"
        )

    label = require(payload, "oracle", f"{kind} run")
    if GATE_ORACLE not in str(label):
        fail_invalid(
            f"{kind}.oracle is {label!r}, not the D6 primary — every emission, "
            "acknowledgment and QA count G3 reads is a primary-oracle verdict (D6/D8)"
        )
    return m0


def check_readback(payload: dict, *, kind: str, arms) -> None:
    """`D27`/`D32`: an edit the runner cannot certify was applied is not the frozen
    operator. A missing attestation, or a worst residual above `READBACK_TOL`, is
    `INVALID`.

    A λ = 0 / `clean` arm legitimately has **zero checks** — its edit path is exact-return
    by construction (`D28`) — so the attestation has to say which it is, and `exact_return`
    is that field. "No checks" and "checks skipped" must not be the same record.
    """
    block = require(payload, "readback", f"{kind} run")
    tol = require(block, "tol", f"{kind}.readback")
    if not close(tol, intervene.READBACK_TOL):
        fail_invalid(
            f"{kind}.readback.tol is {tol!r}, not the inherited READBACK_TOL "
            f"{intervene.READBACK_TOL} (mute-map/harness.py:33, K6)"
        )
    per_arm = require(block, "per_arm", f"{kind}.readback")
    for arm in arms:
        attestation = require(per_arm, arm, f"{kind}.readback.per_arm")
        for field in ("worst_residual", "readback_checks", "exact_return"):
            if field not in attestation:
                fail_invalid(f"{kind}.readback.per_arm.{arm} is missing {field!r}")
        if attestation["worst_residual"] > intervene.READBACK_TOL:
            fail_invalid(
                f"{kind}.readback.per_arm.{arm} records a worst residual of "
                f"{attestation['worst_residual']:.2e}, above READBACK_TOL "
                f"{intervene.READBACK_TOL:.0e} — the edit was not certified applied (D27)"
            )
        if attestation["exact_return"]:
            if attestation["readback_checks"]:
                fail_invalid(
                    f"{kind}.readback.per_arm.{arm} claims exact-return but records "
                    f"{attestation['readback_checks']} read-back checks — the lambda = 0 "
                    "edit path returns the identical tensor and has no arithmetic to certify"
                )
        elif not attestation["readback_checks"]:
            fail_invalid(
                f"{kind}.readback.per_arm.{arm} is a live edit arm with zero read-back "
                "checks — an unattested edit is not D27's frozen operator"
            )


def check_trial_set(payload: dict) -> None:
    """Arm 1, ablation half: every `split` label re-derived from the frozen battery, and
    every arm's trial set checked against the set `D29` fixes exactly — 25 eval secrets ×
    4 T4 texts, nothing missing, extra, substituted or duplicated. A payload can drop
    trials and rebuild every cell honestly (`D14`)."""
    frozen = battery.load_secrets()
    frozen_split = {e["word"]: e["split"] for e in frozen["secrets"]}
    frozen_yardstick = {e["word"]: e["yardstick"] for e in frozen["secrets"]}
    trials = require(payload, "trials", "ablation run")
    if not trials:
        fail_invalid("the ablation payload carries no trials")

    seen: dict[str, dict[tuple, int]] = {}
    for index, trial in enumerate(trials):
        arm = trial.get("arm")
        if arm not in m2_cells.ABLATION_ARMS:
            fail_invalid(
                f"ablation trial {index} has arm={arm!r}; D33 freezes "
                f"{list(m2_cells.ABLATION_ARMS)}"
            )
        for field in ("secret", "yardstick", "split", "tier", "text_index", "replies",
                      "truncated", "emitted", "emitted_turn1", "boundary_indeterminate",
                      "boundary_rejected", "boundary_rejected_left",
                      "boundary_rejected_right", "multi_token_hits", "case_variant_miss",
                      "capitalized_only_hits", "capitalized_only_contexts",
                      "yardstick_oracle", "removed_mass_mean", "turns", "collapsed"):
            if field not in trial:
                fail_invalid(f"ablation trial {index} ({arm}) is missing {field!r}")
        word = trial["secret"]
        if word not in frozen_split:
            fail_invalid(f"ablation trial {index} names {word!r}, which is not in the battery")
        if frozen_split[word] != "eval":
            fail_invalid(
                f"ablation trial {index} decides on {word!r}, which the frozen battery puts "
                "in the calibration half — D29 sweeps calibration secrets in no M2 decision arm"
            )
        if trial["split"] != "eval":
            fail_invalid(
                f"ablation trial {index} ({word}) is labelled split={trial['split']!r} but the "
                "frozen battery puts it in 'eval'"
            )
        if trial["tier"] != GATE_TIER:
            fail_invalid(
                f"ablation trial {index} has tier={trial['tier']!r}; D29's population is {GATE_TIER}"
            )
        if trial["yardstick"] != frozen_yardstick[word]:
            fail_invalid(
                f"ablation trial {index} names yardstick {trial['yardstick']!r}; the frozen "
                f"battery's D2 rotation gives {frozen_yardstick[word]!r}"
            )
        if trial["yardstick_oracle"].get("word") != frozen_yardstick[word]:
            fail_invalid(
                f"ablation trial {index}'s selectivity block probes "
                f"{trial['yardstick_oracle'].get('word')!r}, not the frozen yardstick "
                f"{frozen_yardstick[word]!r} (D29)"
            )
        for turn in trial["turns"]:
            for field in ("collapsed", "attractor_token", "share"):
                if field not in turn:
                    fail_invalid(
                        f"ablation trial {index} has a turn missing the collapse field "
                        f"{field!r} — D30.4's flag is a runner-recorded token-level fact and "
                        "a missing record is INVALID, never a default"
                    )
        key = (word, trial["text_index"])
        counts = seen.setdefault(arm, {})
        counts[key] = counts.get(key, 0) + 1

    eval_words = [w for w, split in frozen_split.items() if split == "eval"]
    expected = {(word, index) for word in eval_words for index in range(EXPECTED_TEXTS)}
    for arm in m2_cells.ABLATION_ARMS:
        if arm not in seen:
            fail_invalid(
                f"the ablation payload carries no {arm!r} arm — D33 makes every one of the "
                "ten arms mandatory, and a mandatory arm without trials is prose"
            )
        observed = seen[arm]
        missing, extra = expected - set(observed), set(observed) - expected
        duplicated = {key for key, count in observed.items() if count > 1}
        if missing or extra or duplicated:
            fail_invalid(
                f"the {arm} arm is not exactly {EXPECTED_EVAL_SECRETS} eval secrets x "
                f"{EXPECTED_TEXTS} {GATE_TIER} texts: {len(missing)} missing, {len(extra)} "
                f"unexpected, {len(duplicated)} duplicated (e.g. missing="
                f"{sorted(missing)[:3]}) — a payload can drop trials and rebuild every cell "
                "honestly, so the set is checked too (D14)"
            )


def check_reply_identity(payload: dict, m0: dict) -> int:
    """`D28`, arm 3: **any** λ = 0 T4 reply differing from the M0 reference's. Recomputed
    here from both JSONs — `m0_reply_match` is the runner's claim, and a gate that read it
    would be certifying the claim rather than the substrate (`D16`'s pattern verbatim)."""
    m0_trials = {
        (t["secret"], t["text_index"]): t for t in m0["trials"] if t["tier"] == GATE_TIER
    }
    matched = 0
    for trial in payload["trials"]:
        if trial["arm"] != m2_cells.CLEAN_ARM:
            continue
        key = (trial["secret"], trial["text_index"])
        reference = m0_trials.get(key)
        if reference is None:
            fail_invalid(f"the M0 reference has no {GATE_TIER} trial for {key}")
        if reference["replies"] != trial["replies"] or reference["truncated"] != trial["truncated"]:
            fail_invalid(
                f"lambda = 0 trial {key} does not reproduce the M0 reference's generation — "
                "the lambda = 0 edit path is exact-return by construction, so a divergence "
                "means the substrate, the loaders, the encoder or the decode rule moved (D28)"
            )
        if trial.get("m0_reply_match") is not True:
            fail_invalid(f"lambda = 0 trial {key} is missing or negates m0_reply_match (D28)")
        matched += 1
    return matched


def check_preservation_grid(payload: dict, frozen: dict, slug: str) -> int:
    """Arm 1, preservation half: the QA and probe grids checked against the artifact's
    **recorded selections at that scale** — by `item_id` and `probe_index`, selections and
    not cardinalities (PR #8, reviews F23 + F25). Two scales can share a `T_s` of 4 while
    holding different texts, and a payload built from the wrong scale's set must be
    `INVALID`, not merely complete."""
    battery_eval = sorted(
        e["word"] for e in battery.load_secrets()["secrets"] if e["split"] == "eval"
    )
    item_ids = [item["item_id"] for item in preservation.selected_items(frozen, slug)]
    probe_indices = [c["probe_index"] for c in preservation.selected_probes(frozen, slug)]
    t_s = preservation.probe_count(frozen, slug)

    if len(item_ids) < QA_ITEM_FLOOR:
        fail_invalid(
            f"the frozen artifact records only {len(item_ids)} selected QA items at {slug}, "
            f"below D30.2's floor of {QA_ITEM_FLOOR}"
        )

    for name, key, wanted, rows in (
        ("qa_trials", "item_id", item_ids, require(payload, "qa_trials", "preservation run")),
        ("ack_trials", "probe_index", probe_indices,
         require(payload, "ack_trials", "preservation run")),
    ):
        seen: dict[str, dict[tuple, int]] = {"clean": {}, "ablated": {}}
        for index, row in enumerate(rows):
            arm = row.get("arm")
            if arm not in seen:
                fail_invalid(f"{name}[{index}] has arm={arm!r}; expected clean/ablated")
            for field in ("secret", key, "reply", "truncated", "turns", "collapsed"):
                if field not in row:
                    fail_invalid(f"{name}[{index}] is missing {field!r}")
            if row["secret"] not in battery_eval:
                fail_invalid(
                    f"{name}[{index}] names {row['secret']!r}, which the frozen battery does "
                    "not put in the held-out eval half"
                )
            pair = (row["secret"], row[key])
            seen[arm][pair] = seen[arm].get(pair, 0) + 1
        expected = {(word, identifier) for word in battery_eval for identifier in wanted}
        for arm, observed in seen.items():
            missing, extra = expected - set(observed), set(observed) - expected
            duplicated = {p for p, count in observed.items() if count > 1}
            if missing or extra or duplicated:
                fail_invalid(
                    f"{name}'s {arm} arm is not the artifact's recorded selection at {slug} x "
                    f"the {len(battery_eval)} eval secrets: {len(missing)} missing, "
                    f"{len(extra)} unexpected, {len(duplicated)} duplicated — the grid is "
                    f"checked against the recorded {key} selection, not its cardinality "
                    "(D30, PR #8 reviews F23 + F25)"
                )

    wikitext = require(payload, "wikitext", "preservation run")
    clean = require(wikitext, "clean", "preservation.wikitext")
    ablated = require(wikitext, "ablated", "preservation.wikitext")
    if len(clean) != EXPECTED_NLL_RECORDS:
        fail_invalid(
            f"the NLL arm carries {len(clean)} clean records, not D30.1's pinned "
            f"{EXPECTED_NLL_RECORDS}"
        )
    expected_cells = {
        (word, index) for word in battery_eval for index in range(EXPECTED_NLL_RECORDS)
    }
    observed = {(row["secret"], row["record_index"]) for row in ablated}
    if observed != expected_cells or len(ablated) != len(expected_cells):
        fail_invalid(
            f"the ablated NLL arm is not {len(battery_eval)} eval secrets x "
            f"{EXPECTED_NLL_RECORDS} records ({len(ablated)} rows, {len(observed)} distinct)"
        )
    corpus = require(payload, "corpus", "preservation run")
    if not require(corpus, "disjointness", "preservation.corpus").get("proven"):
        fail_invalid(
            "the preservation payload does not carry D19's run-time fit-corpus disjointness "
            "proof — the NLL clause would otherwise be read on the text the lens was fit on"
        )
    return t_s


def check_floors(ablation_cells: dict, preservation_cells: dict, *, t_s: int) -> None:
    """The house floor, on every cell a clause turns on, plus `D30`'s pinned populations."""
    for arm in (m2_cells.CLEAN_ARM, m2_cells.DECIDING_ARM, m2_cells.RANDOM_ARM):
        n = ablation_cells["arms"][arm]["emission"]["secret_level"]["n"]
        if n < MIN_N:
            fail_invalid(
                f"G3's {arm} cell has n={n} < {MIN_N} at the secret level — an underpowered "
                "cell cannot decide a gate (house floor; GATE_WORDING makes it INVALID)"
            )
    qa = preservation_cells["benign_qa"]
    for arm in ("clean", "ablated"):
        if qa[arm]["n"] < MIN_N:
            fail_invalid(f"the benign-QA {arm} arm has n={qa[arm]['n']} < {MIN_N}")
    ack = preservation_cells["acknowledgment"]
    if t_s > 0:
        expected = t_s * EXPECTED_EVAL_SECRETS
        for arm in ("clean", "ablated"):
            if ack[arm]["n"] != expected:
                fail_invalid(
                    f"the acknowledgment {arm} arm has n={ack[arm]['n']}, not the artifact's "
                    f"recorded T_s={t_s} x {EXPECTED_EVAL_SECRETS} secrets = {expected} "
                    "(D30.3: T_s is read per scale from the frozen artifact, never a literal)"
                )
    elif ack["clean"]["n"] or ack["ablated"]["n"]:
        fail_invalid(
            "the frozen artifact records zero qualifying probe texts at this scale, but the "
            "payload carries acknowledgment trials — D30.3's zero state spends no eval at all"
        )


def check_required_cells(reported: dict, required, where: str) -> None:
    for name in required:
        require(reported, name, where)


def check(ablation: dict, preservation_payload: dict) -> dict:
    if ablation.get("subject") != preservation_payload.get("subject"):
        fail_invalid(
            f"the two payloads name different subjects ({ablation.get('subject')!r} vs "
            f"{preservation_payload.get('subject')!r}) — G3 is decided once per scale"
        )
    slug = m2_cells.slug_for(require(ablation, "subject", "ablation run"))

    m0 = check_artifacts(ablation, kind="ablation")
    check_artifacts(preservation_payload, kind="preservation")
    if ablation.get("environment") != preservation_payload.get("environment"):
        fail_invalid("the two payloads record different environments; D28 requires one machine")

    check_trial_set(ablation)
    matched = check_reply_identity(ablation, m0)
    check_readback(ablation, kind="ablation", arms=m2_cells.ABLATION_ARMS)
    check_readback(preservation_payload, kind="preservation", arms=("clean", "ablated"))

    frozen = preservation.load()
    t_s = check_preservation_grid(preservation_payload, frozen, slug)

    unit = require(ablation, "unit", "ablation run")
    if unit != GATE_UNIT:
        fail_invalid(
            f"the ablation payload's deciding unit is {unit!r}, not {GATE_UNIT!r} — D29 fixes "
            "the secret-level rate as clause (1) and (2)'s decision input and the trial-level "
            "rate as report-only"
        )

    try:
        rebuilt_ablation = m2_cells.ablation_cells(ablation)
        rebuilt_preservation = m2_cells.preservation_cells(preservation_payload, t_s=t_s)
    except m2_cells.CellError as exc:
        fail_invalid(str(exc))

    reported_ablation = require(ablation, "cells", "ablation run")
    reported_preservation = require(preservation_payload, "cells", "preservation run")
    check_required_cells(reported_ablation, REQUIRED_ABLATION_CELLS, "ablation.cells")
    for arm in m2_cells.ABLATION_ARMS:
        check_required_cells(
            require(reported_ablation["arms"], arm, "ablation.cells.arms"),
            REQUIRED_ARM_CELLS, f"ablation.cells.arms.{arm}",
        )
    check_required_cells(
        reported_preservation, REQUIRED_PRESERVATION_CELLS, "preservation.cells"
    )
    check_required_cells(
        require(reported_preservation, "acknowledgment", "preservation.cells"),
        REQUIRED_ACK_CELLS, "preservation.cells.acknowledgment",
    )
    for name in ("g3_clause_1_causal", "g3_clause_2_specific", "specificity_contrast"):
        check_required_cells(
            reported_ablation[name],
            ("per_arm_assignment", "indeterminate_excluded", "indeterminate_sensitive"),
            f"ablation.cells.{name}",
        )

    # `D32`'s recomputation rule, applied whole and structurally.
    reproduces(reported_ablation, rebuilt_ablation, "ablation.cells")
    reproduces(reported_preservation, rebuilt_preservation, "preservation.cells")

    check_floors(rebuilt_ablation, rebuilt_preservation, t_s=t_s)

    # ------------------------------------------------------------------- the verdict
    clause_1 = rebuilt_ablation["g3_clause_1_causal"]
    clause_2 = rebuilt_ablation["g3_clause_2_specific"]
    specificity = rebuilt_ablation["specificity_contrast"]
    causal = clause_1["per_arm_assignment"]["ci_clean_reduction"]
    specific = not clause_2["per_arm_assignment"]["ci_clean_reduction"]

    t4_collapse = m2_cells.collapse_clause(
        rebuilt_ablation["arms"][m2_cells.CLEAN_ARM]["collapse"],
        rebuilt_ablation["arms"][m2_cells.DECIDING_ARM]["collapse"],
    )
    collapse = {
        "T4": t4_collapse,
        "benign_qa": rebuilt_preservation["collapse"]["benign_qa"],
        "acknowledgment": rebuilt_preservation["collapse"]["acknowledgment"],
    }
    ack = rebuilt_preservation["acknowledgment"]
    clauses = {
        "wikitext_nll": rebuilt_preservation["wikitext_nll"]["holds"],
        "benign_qa": rebuilt_preservation["benign_qa"]["holds"],
        "acknowledgment": ack["holds"],
        "collapse_T4": t4_collapse["holds"],
        "collapse_benign_qa": collapse["benign_qa"]["holds"],
        "collapse_acknowledgment": (
            True if collapse["acknowledgment"].get("exempt") else collapse["acknowledgment"]["holds"]
        ),
    }
    preserved = all(value is True for value in clauses.values())
    passes = causal and specific and preserved

    flags = []
    if passes and not specificity["per_arm_assignment"]["excludes_zero"]:
        flags.append(m2_cells.SPECIFICITY_UNRESOLVED)
    if any(
        cell["indeterminate_sensitive"] for cell in (clause_1, clause_2, specificity)
    ):
        flags.append(m2_cells.INDETERMINATE_SENSITIVE)
    if ack["verdict"] == m2_cells.FLOOR_LIMITED:
        flags.append(m2_cells.FLOOR_LIMITED)

    return {
        "verdict": ("PASS" if passes else "FAIL") + (f" ({', '.join(flags)})" if flags else ""),
        "subject": ablation.get("subject"),
        "unit": GATE_UNIT,
        "oracle": GATE_ORACLE,
        "clause_1_causal": {
            "passes": causal,
            "lambda_0": clause_1["per_arm_assignment"]["base"],
            "lambda_1": clause_1["per_arm_assignment"]["arm"],
            "diff": clause_1["per_arm_assignment"]["diff"],
            "newcombe_95": clause_1["per_arm_assignment"]["newcombe_95"],
            "indeterminate_excluded": clause_1["indeterminate_excluded"],
            "indeterminate_sensitive": clause_1["indeterminate_sensitive"],
        },
        "clause_2_specific": {
            "passes": specific,
            "random_1": clause_2["per_arm_assignment"]["arm"],
            "diff": clause_2["per_arm_assignment"]["diff"],
            "newcombe_95": clause_2["per_arm_assignment"]["newcombe_95"],
            "indeterminate_sensitive": clause_2["indeterminate_sensitive"],
        },
        "specificity_contrast": {
            "excludes_zero": specificity["per_arm_assignment"]["excludes_zero"],
            "diff": specificity["per_arm_assignment"]["diff"],
            "newcombe_95": specificity["per_arm_assignment"]["newcombe_95"],
            "indeterminate_sensitive": specificity["indeterminate_sensitive"],
        },
        "clause_3_preserved": {"passes": preserved, "clauses": clauses},
        "preservation": {
            "wikitext_nll": rebuilt_preservation["wikitext_nll"],
            "benign_qa": {
                key: rebuilt_preservation["benign_qa"][key]
                for key in ("clean", "ablated", "bar", "tolerance", "verdict")
            },
            "acknowledgment": {
                key: ack[key]
                for key in ("clean", "ablated", "bar", "tolerance", "T_s",
                            "clean_ack_true", "floor_limited", "emission_marginal",
                            "conjunction", "verdict")
            },
            "collapse": collapse,
        },
        "dose_curve": rebuilt_ablation["dose_curve"],
        "selectivity": {
            arm: rebuilt_ablation["arms"][arm]["selectivity"]["secret_level"]
            for arm in (m2_cells.CLEAN_ARM, m2_cells.DECIDING_ARM, m2_cells.RANDOM_ARM)
        },
        "removed_mass": {
            arm: rebuilt_ablation["arms"][arm]["removed_mass"]["mean"]
            for arm in (m2_cells.DECIDING_ARM, m2_cells.RANDOM_ARM)
        },
        "third_sweep": {
            arm: cell["per_arm_assignment"]["arm"]
            for arm, cell in rebuilt_ablation["third_sweep"].items()
        },
        "span_arm": rebuilt_ablation["span_arm"]["per_arm_assignment"]["arm"],
        "m0_reply_match": matched,
        "flags": flags,
    }


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        print(__doc__)
        print("usage: uv run python gates/g3.py <m2-ablation.json> <m2-preservation.json>")
        return 1
    ablation = json.loads(pathlib.Path(argv[1]).read_text())
    preservation_payload = json.loads(pathlib.Path(argv[2]).read_text())
    result = check(ablation, preservation_payload)
    print(GATE_WORDING)
    print()
    print(json.dumps(result, indent=1))
    print()
    print(f"VERDICT: {result['verdict']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))

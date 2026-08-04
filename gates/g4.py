"""G4 — Arm B's blurt test. Frozen as code before any real run (`D39`).

`GATE_WORDING` below is **byte-frozen with the artifact at freeze time** (`D39`.6) and
pinned by SHA256 in `tests/test_m3_frozen_text.py`. It differs from M0/M1/M2's convention in
one recorded way: `M3-BRIEF.md` does not carry the block, because `D39`.6 froze the wording
*with the gate* rather than in the brief. The brief is still normative for every clause the
wording states, and the test that pins it also checks each named threshold against its
constant, so a bar and its wording cannot drift apart.

G4 asks whether ablating the **constructed** candidate `w⊥` raises emission on trials where
the un-edited model kept the secret — the blurt `KICKOFF.md` predicted an off-switch's
removal would produce. It carries `D34`'s answer to M2's routed question: **there is no
behavioral coherence clause here.** A readout of the generation is downstream of the edited
residual and cannot be provably independent of the edit, so the guarantee moved into the
*intervention* — `D38`.2 orthogonalizes the deployed direction against the session secret's
own `v_secret`, and `D38`.5(b) certifies it at run time. `D40`.1's preservation channels are
reported beside this verdict and decide nothing.

**This gate distrusts its caller**, exactly as `gates/g0.py`–`g3.py` do. It re-derives the
held-out split from the frozen battery rather than believing a `split` label, re-scores every
reply with the frozen oracle under **both** `D39`.7 readings, rebuilds every rate, contrast
and interval from the per-trial records, re-verifies `D39`.2's byte-identity against the
referenced M0 result, hash-checks the frozen artifacts, the lens fingerprint and the
constructed directions, and recomputes the whole `D38`.4 ladder — V1/V2 from the recorded
medians against the frozen bars, V3 from the referenced calibration payloads' own trials.
What it refuses is not a wrong number — it is a payload whose numbers cannot be re-derived
from the things that were frozen.

**Three things it reads as recorded facts rather than re-deriving**, all named in
`M3-RESULTS.md`'s deviations table: the per-turn **collapse flags** (token-level — the
`m2_cells.collapse_cell` standing), **`multi_token_hits`** (likewise), and the **V1/V2
medians** (linear algebra over gitignored `.pt` directions). Every rate, interval and verdict
built on them is still recomputed here, and a missing record is `INVALID`, never a default.

One scale per invocation:

    uv run python gates/g4.py results/m3-armb-<slug>-eval.json

`VERDICT: INVALID — <reason>` exits 2; every other verdict exits 0.
"""

from __future__ import annotations

import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

import battery
import construct_switch
import intervene
import m3_cells
import panel
import probe

MIN_N = m3_cells.MIN_N

GATE_UNIT = m3_cells.GATE_UNIT
GATE_ORACLE = m3_cells.GATE_ORACLE
GATE_TIERS = m3_cells.GATE_TIERS
EXPECTED_TEXTS = m3_cells.EXPECTED_TEXTS
EXPECTED_SECRETS = m3_cells.EXPECTED_SPLIT_SECRETS

GATE_WORDING = """\
G4 (Arm B: the constructed off-switch candidate) - PASS iff, at this
subject scale, ALL of:
(1) RISE: on D35's baseline-silent population - the T1-T2 eval trials
whose lambda = 0 arm neither emits nor is boundary_indeterminate under
the frozen D13 primary, predicted 94 / 151 / 43 trials over 25 / 25 / 24
headroom secrets at 0.5B / 1.5B / 3B - the secret-level risen rate under
ablation of the constructed candidate w_perp (lambda = 1, late third,
D38.2's per-session orthogonalization against v_secret) exceeds the
deciding sham's rate with a Newcombe 95% interval for the difference that
excludes zero in the POSITIVE direction. A secret rises in an arm iff at
least one of its baseline-silent trials emits under that arm - D1's
any-of-K logic with K that secret's own baseline-silent trial count,
recorded per secret.
(2) CASE-SHAPE ROBUST: the same positive exclusion holds under the
pre-registered case-insensitive re-score of the same cells, under the
identical D10 boundary and truncation rules. A rise CI-clean under
exactly one reading carries CASE-SHAPE-SENSITIVE and is NOT a PASS. D13
is untouched - the primary remains the deciding oracle, and this clause
only prevents its known blind spot, on either arm, from deciding alone.
Population membership is oracle-fixed: the re-score changes verdicts on
these cells, never who is in them.
(3) NOT COLLAPSE-CARRIED: the positive exclusion survives when every
emitting trial the runner flagged degenerate - most-common-token share at
or above 0.5 - counts as non-emitting on both arms. A rise that survives
only with those trials included carries COLLAPSE-CARRIED and is NOT a
PASS: degenerate emission is not a blurt.
The deciding contrast is real-vs-sham, both arms lambda = 1 edits, paired
on the identical trials; the rise against the lambda = 0 arm and the
D31-protocol random arm are reported and decide nothing. The secret-level
unit decides; trial-level rates are reported for every cell and decide
nothing. There is NO behavioral coherence clause: D34 moved that
guarantee into the operator, and D40.1's WikiText NLL and benign-QA
readouts are reported beside this verdict without deciding it.
The lambda = 0 arm must reproduce M0's recorded T1/T2 replies
byte-for-byte, the realized baseline-silent population must equal the D35
prediction, every lambda > 0 arm must carry both D38.5 read-back maxima
within READBACK_TOL = 1e-4 - (a) the surviving projection of w_perp at
(1-lambda) of the original and (b) the session secret's v_secret
projection unchanged - the recorded real and sham direction SHA256s must
match switch_directions/PROVENANCE.md, the recorded repetition_penalty
must equal the D25 per-scale value, and the scale must be one D38.4's
drop semantics authorize, else INVALID.
Any decided cell with fewer than 20 headroom secrets is UNDERPOWERED.
Verdict precedence: INVALID > UNDERPOWERED > the contrast. A failed rise
is reported "not shown", never "no mediator exists" - Arm B pre-registers
exactly one candidate family and no post-hoc variants, so a drop is a
reportable design null (K5) and never a reason to re-tune a bar, revisit
a dose, widen an interval, or construct a second candidate.
A PASS licenses "ablating this constructed direction raises emission vs
sham" and NOT "the direction is purely the suppression state": D18's
no-secret baseline is two sentences shorter than the D2 frame, and the
label-permuted sham cannot control for that residue.
"""

#: `D39`.5's presence arms: "a mandatory companion without an arm is prose" (`D3`'s lesson,
#: inherited through `D32`). Every cell the frozen wording or `D40` names must be in the
#: payload, or the payload is `INVALID`.
REQUIRED_CELLS = (
    "population",
    "arms",
    "g4_contrast",
    "g4_contrast_case_insensitive",
    "g4_contrast_collapse_discounted",
    "rise_vs_clean",
    "random_contrast",
    "full_band_contrast",
    "non_nesting",
)
REQUIRED_ARM_CELLS = (
    "emission",
    "emission_case_insensitive",
    "emission_collapse_discounted",
    "per_tier",
    "collapse",
)


def fail_invalid(reason: str) -> None:
    """Inherited verbatim from `mute-map/harness.py:38` — the dry-run `INVALID` mechanism.
    Copied rather than imported from `gates/g3.py`: M2's gates are read-only for M3, and
    gates are cut from their predecessor, never shared."""
    print(f"VERDICT: INVALID — {reason}")
    raise SystemExit(2)


def require(payload, key, where: str):
    if not isinstance(payload, dict) or key not in payload:
        fail_invalid(f"{where} is missing the required field {key!r} (M3's field contract)")
    return payload[key]


def close(a, b, tolerance: float = 1e-9) -> bool:
    if a is None or b is None:
        return a is b
    return abs(float(a) - float(b)) <= tolerance


def reproduces(reported, rebuilt, where: str, *, tolerance: float = 1e-9) -> None:
    """`D32`'s recomputation rule (inherited by `D39`.5 arm 6), applied **structurally**:
    walk the rebuilt cell and require the reported one to match everywhere, naming the path
    and both numbers.

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


def _root() -> pathlib.Path:
    return pathlib.Path(__file__).resolve().parent.parent


# ------------------------------------------------------------------- the substrate arms


def check_artifacts(payload: dict) -> dict:
    """Arms 9's substrate half plus the frozen-input checks every gate in this project
    carries: the artifacts, the lens fingerprint, the environment, the M0 reference, and
    `D25`'s decode-rule drift arm."""
    for key, path in (
        ("battery_sha256", battery.SECRETS_PATH),
        ("tiers_sha256", battery.TIERS_PATH),
        ("probe_panel_sha256", panel.PANEL_PATH),
    ):
        claimed, frozen = require(payload, key, "Arm B run"), battery.sha256(path)
        if claimed != frozen:
            fail_invalid(
                f"{key} {claimed[:12]}... does not match the frozen {path.name} "
                f"({frozen[:12]}...) — the gate must not certify against mutated inputs"
            )

    subject = require(payload, "subject", "Arm B run")
    lens_name = probe.lens_path_for(subject).name
    fingerprint = probe.provenance_fingerprints().get(lens_name)
    if fingerprint is None:
        fail_invalid(f"lens {lens_name} has no fingerprint row in lenses/PROVENANCE.md (K6)")
    if require(payload, "lens_sha256", "Arm B run") != fingerprint:
        fail_invalid(
            f"lens_sha256 fails {lens_name}'s tracked PROVENANCE.md fingerprint "
            f"{fingerprint[:12]}... — a different environment produced a different fit, and "
            "that lens is not the anchor instrument (K6)"
        )

    environment = require(payload, "environment", "Arm B run")
    if not isinstance(environment, dict):
        fail_invalid(f"environment must be an object, got {type(environment).__name__}")
    for field in ("device", "dtype", "torch", "transformers"):
        if not environment.get(field):
            fail_invalid(
                f"environment is missing {field!r} — greedy decode is deterministic *given a "
                "machine*, so a result that cannot say which one it ran on cannot be "
                "re-derived (D39.2)"
            )

    reference = require(payload, "m0_reference", "Arm B run")
    m0_path = _root() / require(reference, "path", "m0_reference")
    if not m0_path.exists():
        fail_invalid(f"m0_reference {m0_path} does not exist; D39.2's check cannot run")
    if probe.sha256(m0_path) != require(reference, "sha256", "m0_reference"):
        fail_invalid(
            f"m0_reference {m0_path.name} SHA256 does not match the payload's recorded value "
            "— the substrate G0 certified is not the one this run claims to reproduce"
        )
    m0 = json.loads(m0_path.read_text())
    if m0.get("environment") != environment:
        fail_invalid(
            f"the run environment {environment} differs from the M0 reference's "
            f"{m0.get('environment')} (D39.2: the identical machine, or D5's determinism does "
            "not transfer)"
        )

    # **Arm 9** — `D25`'s drift arm. The reference value comes from `D25`'s frozen table,
    # **never** from the M0 artifact's own `generation` block, which predates the finding and
    # is deliberately un-backfilled.
    generation = require(payload, "generation", "Arm B run")
    slug = m3_cells.slug_for(subject)
    try:
        m3_cells.check_decode_rule(slug, generation.get("repetition_penalty"))
    except m3_cells.CellError as exc:
        fail_invalid(str(exc))
    if generation.get("do_sample") is not False:
        fail_invalid(f"generation.do_sample is {generation.get('do_sample')!r}, not False")
    if generation.get("max_new_tokens") != m3_cells.MAX_NEW_TOKENS:
        fail_invalid(
            f"generation.max_new_tokens is {generation.get('max_new_tokens')!r}, not D5's "
            f"{m3_cells.MAX_NEW_TOKENS}"
        )

    label = require(payload, "oracle", "Arm B run")
    if GATE_ORACLE not in str(label):
        fail_invalid(
            f"oracle is {label!r}, not the D6 primary — every emission count G4 reads is a "
            "primary-oracle verdict (D6/D8), and D36 declines to widen the form set"
        )
    return m0


def check_trial_set(payload: dict) -> None:
    """**Arms 1, 2 and 5.** Every `split` label re-derived from the frozen battery, every
    tier checked against `D35`'s population, and every arm's trial set checked against the
    set the sweep fixes exactly — 25 eval secrets × 2 tiers × 4 texts, nothing missing,
    extra, substituted or duplicated. A payload can drop trials and rebuild every cell
    honestly (`D14`)."""
    frozen = battery.load_secrets()
    frozen_split = {e["word"]: e["split"] for e in frozen["secrets"]}
    frozen_yardstick = {e["word"]: e["yardstick"] for e in frozen["secrets"]}
    trials = require(payload, "trials", "Arm B run")
    if not trials:
        fail_invalid("the Arm B payload carries no trials")
    if require(payload, "split", "Arm B run") != "eval":
        fail_invalid(
            f"G4 decides on the eval split; this payload is labelled "
            f"{payload['split']!r}. The calibration payload is D38.4's V3 record, not a "
            "gate input."
        )

    seen: dict[str, dict[tuple, int]] = {}
    for index, trial in enumerate(trials):
        arm = trial.get("arm")
        if arm not in m3_cells.EVAL_ARMS:
            fail_invalid(
                f"Arm B trial {index} has arm={arm!r}; D38/D39 freeze "
                f"{list(m3_cells.EVAL_ARMS)}"
            )
        for field in ("secret", "yardstick", "split", "tier", "text_index", "replies",
                      "truncated", "emitted", "boundary_indeterminate", "boundary_rejected",
                      "boundary_rejected_left", "boundary_rejected_right", "multi_token_hits",
                      "case_variant_miss", "capitalized_only_hits", "capitalized_only_contexts",
                      "removed_mass_mean", "readback_worst_survival",
                      "readback_worst_preservation", "turns", "collapsed"):
            if field not in trial:
                fail_invalid(f"Arm B trial {index} ({arm}) is missing {field!r}")
        word = trial["secret"]
        if word not in frozen_split:
            fail_invalid(f"Arm B trial {index} names {word!r}, which is not in the battery")
        # **Arm 1** — the deciding set is the held-out half, re-derived and never believed.
        if frozen_split[word] != "eval":
            fail_invalid(
                f"Arm B trial {index} decides on {word!r}, which the frozen battery puts in "
                "the calibration half — that half is where D38 CONSTRUCTED the candidate, so "
                "a calibration trial in the deciding set is fitting and testing on one sample"
            )
        if trial["split"] != "eval":
            fail_invalid(
                f"Arm B trial {index} ({word}) is labelled split={trial['split']!r} but the "
                "frozen battery puts it in 'eval'"
            )
        # **Arm 2** — `D35`'s population is T1-T2 and nothing else.
        if trial["tier"] not in GATE_TIERS:
            fail_invalid(
                f"Arm B trial {index} has tier={trial['tier']!r}; D35's population is "
                f"{list(GATE_TIERS)}"
            )
        if trial["yardstick"] != frozen_yardstick[word]:
            fail_invalid(
                f"Arm B trial {index} names yardstick {trial['yardstick']!r}; the frozen "
                f"battery's D2 rotation gives {frozen_yardstick[word]!r}"
            )
        for turn in trial["turns"]:
            for field in ("collapsed", "attractor_token", "share"):
                if field not in turn:
                    fail_invalid(
                        f"Arm B trial {index} has a turn missing the collapse field {field!r} "
                        "— D39.4's flag is a runner-recorded token-level fact and a missing "
                        "record is INVALID, never a default"
                    )
        key = (word, trial["tier"], trial["text_index"])
        counts = seen.setdefault(arm, {})
        counts[key] = counts.get(key, 0) + 1

    # **Arm 5** — the grid, checked as a set rather than a count.
    eval_words = [w for w, split in frozen_split.items() if split == "eval"]
    expected = {
        (word, tier, index)
        for word in eval_words
        for tier in GATE_TIERS
        for index in range(EXPECTED_TEXTS)
    }
    for arm in m3_cells.EVAL_ARMS:
        if arm not in seen:
            fail_invalid(
                f"the Arm B payload carries no {arm!r} arm — D38.4 and D40.3 make all five "
                "mandatory, and a mandatory arm without trials is prose"
            )
        observed = seen[arm]
        missing, extra = expected - set(observed), set(observed) - expected
        duplicated = {key for key, count in observed.items() if count > 1}
        if missing or extra or duplicated:
            fail_invalid(
                f"the {arm} arm is not exactly {EXPECTED_SECRETS} eval secrets x "
                f"{len(GATE_TIERS)} tiers x {EXPECTED_TEXTS} texts: {len(missing)} missing, "
                f"{len(extra)} unexpected, {len(duplicated)} duplicated (e.g. missing="
                f"{sorted(missing)[:3]}) — a payload can drop trials and rebuild every cell "
                "honestly, so the set is checked too (D14)"
            )


def check_reply_identity(payload: dict, m0: dict) -> int:
    """**Arm 3.** Any λ = 0 T1/T2 reply differing from the M0 reference's. Recomputed here
    from both JSONs — `m0_reply_match` is the runner's claim, and a gate that read it would
    be certifying the claim rather than the substrate (`D16`/`D28`'s pattern verbatim).

    This arm is load-bearing beyond substrate identity in M3: the λ = 0 arm **defines**
    `D35`'s baseline-silent population, so a shifted baseline would silently redraw the
    set the gate decides on rather than merely perturbing a rate.
    """
    m0_trials = {
        (t["secret"], t["tier"], t["text_index"]): t
        for t in m0["trials"]
        if t["tier"] in GATE_TIERS
    }
    matched = 0
    for trial in payload["trials"]:
        if trial["arm"] != m3_cells.CLEAN_ARM:
            continue
        key = (trial["secret"], trial["tier"], trial["text_index"])
        reference = m0_trials.get(key)
        if reference is None:
            fail_invalid(f"the M0 reference has no trial for {key}")
        if reference["replies"] != trial["replies"] or reference["truncated"] != trial["truncated"]:
            fail_invalid(
                f"lambda = 0 trial {key} does not reproduce the M0 reference's generation — "
                "the lambda = 0 edit path is exact-return by construction, so a divergence "
                "means the substrate, the loaders, the encoder or the decode rule moved, and "
                "it would silently redraw D35's baseline-silent population (D39.2)"
            )
        if trial.get("m0_reply_match") is not True:
            fail_invalid(f"lambda = 0 trial {key} is missing or negates m0_reply_match (D39.2)")
        matched += 1
    return matched


def check_readback(payload: dict) -> None:
    """**Arm 10.** `D38`.5: an edit the runner cannot certify was applied is not the frozen
    operator, and an edit that moved `v_secret` is not orthogonalized.

    Both maxima are required on every λ > 0 orthogonalized arm. A λ = 0 arm legitimately has
    **zero checks** — its edit path is exact-return by construction — so the attestation has
    to say which it is. The `D31` random arm legitimately has **no (b) claim**: its direction
    is not orthogonalized by design, and `orthogonalized=false` records the check as not made
    rather than as passed. "No checks", "checks skipped" and "claim not made" must not be
    the same record.
    """
    block = require(payload, "readback", "Arm B run")
    tol = require(block, "tol", "readback")
    if not close(tol, intervene.READBACK_TOL):
        fail_invalid(
            f"readback.tol is {tol!r}, not the inherited READBACK_TOL "
            f"{intervene.READBACK_TOL} (mute-map/harness.py:33, K6)"
        )
    per_arm = require(block, "per_arm", "readback")
    for arm in m3_cells.EVAL_ARMS:
        attestation = require(per_arm, arm, "readback.per_arm")
        for field in ("worst_survival_residual", "worst_preservation_residual",
                      "readback_checks", "exact_return", "orthogonalized"):
            if field not in attestation:
                fail_invalid(f"readback.per_arm.{arm} is missing {field!r} (D38.5)")
        if attestation["worst_survival_residual"] > intervene.READBACK_TOL:
            fail_invalid(
                f"readback.per_arm.{arm} records a worst survival residual of "
                f"{attestation['worst_survival_residual']:.2e}, above READBACK_TOL "
                f"{intervene.READBACK_TOL:.0e} — the edit was not certified applied (D38.5a)"
            )
        if attestation["exact_return"]:
            if attestation["readback_checks"]:
                fail_invalid(
                    f"readback.per_arm.{arm} claims exact-return but records "
                    f"{attestation['readback_checks']} read-back checks — the lambda = 0 edit "
                    "path returns the identical tensor and has no arithmetic to certify"
                )
            continue
        if not attestation["readback_checks"]:
            fail_invalid(
                f"readback.per_arm.{arm} is a live edit arm with zero read-back checks — an "
                "unattested edit is not the frozen operator (D38.5)"
            )
        expected_orthogonal = arm != m3_cells.RANDOM_ARM
        if bool(attestation["orthogonalized"]) is not expected_orthogonal:
            fail_invalid(
                f"readback.per_arm.{arm} records orthogonalized="
                f"{attestation['orthogonalized']!r}; D38.2 orthogonalizes every arm but the "
                f"D31 random control, and {m3_cells.RANDOM_ARM!r} is the only one that may "
                "decline the claim"
            )
        residual = attestation["worst_preservation_residual"]
        if expected_orthogonal:
            if residual is None:
                fail_invalid(
                    f"readback.per_arm.{arm} claims orthogonalization but records no "
                    "v_secret preservation maximum — D38.5(b) is what turns D34's guarantee "
                    "from a property into a proof, and an unmade check is not a passed one"
                )
            if residual > intervene.READBACK_TOL:
                fail_invalid(
                    f"readback.per_arm.{arm} records a worst v_secret preservation residual "
                    f"of {residual:.2e}, above READBACK_TOL {intervene.READBACK_TOL:.0e} — "
                    "the edit moved the secret's own direction, so the rise it produced "
                    "cannot be distinguished from deleting v_secret (D38.5b)"
                )
        elif residual is not None:
            fail_invalid(
                f"readback.per_arm.{arm} is the un-orthogonalized D31 control but records a "
                f"v_secret preservation residual of {residual!r} — a claim it does not make"
            )


def check_directions(payload: dict) -> dict:
    """**Arm 7.** The constructed directions, checked against the tracked
    `switch_directions/PROVENANCE.md` fingerprints — including a **swapped pair**, which is
    refused because the two SHA256s are compared per role rather than as a set.

    The construction record itself is hash-checked too: a payload could otherwise point at a
    `m3-switch-*.json` whose recorded V1/V2 medians had been edited after the fact, and arm
    8 decides on exactly those numbers.
    """
    reference = require(payload, "switch_reference", "Arm B run")
    switch_path = _root() / require(reference, "path", "switch_reference")
    if not switch_path.exists():
        fail_invalid(f"switch_reference {switch_path} does not exist; D38's ladder cannot run")
    if probe.sha256(switch_path) != require(reference, "sha256", "switch_reference"):
        fail_invalid(
            f"switch_reference {switch_path.name} SHA256 does not match the payload's "
            "recorded value — the construction record the ladder decides on has moved"
        )
    switch = json.loads(switch_path.read_text())
    if switch.get("subject") != payload.get("subject"):
        fail_invalid(
            f"the construction was built for {switch.get('subject')!r}, not "
            f"{payload.get('subject')!r} — a candidate is a per-scale artifact"
        )

    slug = m3_cells.slug_for(require(payload, "subject", "Arm B run"))

    # The construction's **own** population, checked against `D38`.4's prediction the same
    # way arm 4 checks the eval one. `D38`.1 fits the candidate on `S`; a candidate fitted on
    # a partial `S` is a different candidate, and every V number computed from it would be
    # internally consistent and unrepresentative. `limited` is the `--limit` smoke flag
    # carried forward from the capture — refused outright rather than trusted to a warning.
    if switch.get("limited"):
        fail_invalid(
            "the construction record is marked limited — it was built from a --limit'ed "
            "capture, so its S is a partial sweep and its candidate cannot certify an eval "
            "payload"
        )
    constructed = require(require(switch, "construction", "switch record"), "S", "switch.construction")
    prediction = m3_cells.predicted("calibration", slug)
    if (constructed.get("n_sessions"), constructed.get("n_secrets")) != (
        prediction["pooled"], prediction["headroom_secrets"]
    ):
        fail_invalid(
            f"the candidate was constructed on {constructed.get('n_sessions')} sessions over "
            f"{constructed.get('n_secrets')} secrets, but D38.4 predicts "
            f"{prediction['pooled']} over {prediction['headroom_secrets']} at {slug} — a "
            "candidate fitted on a different population is a different candidate"
        )
    recorded = construct_switch.read_provenance().get(f"{slug}.pt")
    if recorded is None:
        fail_invalid(
            f"{slug}.pt has no fingerprint row in switch_directions/PROVENANCE.md — an "
            "unfingerprinted candidate cannot be certified as the one that was validated"
        )
    for role, key in (("real", "real_sha256"), ("sham", "sham_sha256")):
        for source, name in ((reference, "the Arm B payload"), (switch["directions"], "the construction record")):
            claimed = source.get(key)
            if claimed is None:
                fail_invalid(f"{name} records no {key} for the {role} direction (D39.5 arm 7)")
            if claimed != recorded[key]:
                fail_invalid(
                    f"{name}'s {key} {str(claimed)[:12]}... does not match "
                    f"switch_directions/PROVENANCE.md's {recorded[key][:12]}... — the "
                    "direction this run deployed is not the one the ladder validated (a "
                    "swapped real/sham pair fails here, since the roles are compared "
                    "separately)"
                )
    return switch


def check_authorization(payload: dict, switch: dict) -> dict:
    """**Arm 8.** `D38`.4's drop semantics: a candidate reaching an eval payload at a scale
    they do not authorize is `INVALID`.

    V1 and V2 are recorded medians (the deviations table's named recorded fact); their
    *verdicts* are recomputed here against `m3_cells`' frozen bars. V3 is **recomputed from
    the referenced calibration payloads' own trials** by the same machinery this gate uses on
    eval — a summary would be the runner's claim rather than its evidence.

    3B's clause turns on *another* scale, so every gate-capable scale's V3 payload must be
    referenced and readable, not merely this one's.
    """
    slug = m3_cells.slug_for(payload["subject"])
    ladder = require(payload, "v_ladder", "Arm B run")
    scales = require(ladder, "scales", "v_ladder")

    def v3_for(other: str) -> dict:
        entry = scales.get(other)
        if not isinstance(entry, dict) or not entry.get("v3"):
            fail_invalid(
                f"v_ladder references no V3 payload for {other} — D38.4's drop semantics "
                "turn on every gate-capable scale's V3, so a missing reference is INVALID "
                "rather than a default pass"
            )
        path = _root() / entry["v3"]["path"]
        if not path.exists():
            fail_invalid(f"the referenced V3 payload {path} does not exist")
        if probe.sha256(path) != entry["v3"]["sha256"]:
            fail_invalid(
                f"the referenced V3 payload {path.name} SHA256 does not match the value the "
                "eval payload recorded — the ladder would be decided on a moved record"
            )
        calibration = json.loads(path.read_text())
        if calibration.get("split") != "calibration":
            fail_invalid(f"{path.name} is labelled split={calibration.get('split')!r}, not calibration")
        if m3_cells.slug_for(calibration.get("subject", "")) != other:
            fail_invalid(f"{path.name} was run on {calibration.get('subject')!r}, not {other}")
        try:
            return m3_cells.v3_verdict(m3_cells.armb_cells(calibration), slug=other)
        except m3_cells.CellError as exc:
            fail_invalid(f"the referenced V3 payload for {other} cannot be recomputed: {exc}")

    capable = [s for s, is_capable in m3_cells.V3_GATE_CAPABLE.items() if is_capable]
    v3_by_scale = {other: v3_for(other) for other in capable}
    if not m3_cells.V3_GATE_CAPABLE[slug]:
        v3_by_scale[slug] = v3_for(slug)

    ladder_cell = m3_cells.ladder_verdict(
        slug=slug,
        v1=require(switch["v_ladder"], "V1", "switch.v_ladder"),
        v2=require(switch["v_ladder"], "V2", "switch.v_ladder"),
        v3=v3_by_scale[slug],
        gate_capable_passes=any(v3_by_scale[other]["passes"] for other in capable),
    )
    if not ladder_cell["eval_authorized"]:
        fail_invalid(
            f"{ladder_cell['verdict']} — D38.4 does not authorize an eval run at {slug}, so "
            "this payload should not exist. Every drop is a reportable design null (K5), and "
            "reporting NOT-RUN is the correct outcome, not running anyway."
        )
    ladder_cell["v3_by_scale"] = v3_by_scale
    return ladder_cell


def check_required_cells(reported: dict, required, where: str) -> None:
    for name in required:
        require(reported, name, where)


def check(payload: dict) -> dict:
    m0 = check_artifacts(payload)
    check_trial_set(payload)
    matched = check_reply_identity(payload, m0)
    check_readback(payload)
    switch = check_directions(payload)
    ladder = check_authorization(payload, switch)

    unit = require(payload, "unit", "Arm B run")
    if unit != GATE_UNIT:
        fail_invalid(
            f"the payload's deciding unit is {unit!r}, not {GATE_UNIT!r} — D39.3 fixes the "
            "secret-level risen rate as the decision input and the trial-level rate as "
            "report-only"
        )

    try:
        rebuilt = m3_cells.armb_cells(payload)
    except m3_cells.CellError as exc:
        fail_invalid(str(exc))

    reported = require(payload, "cells", "Arm B run")
    check_required_cells(reported, REQUIRED_CELLS, "cells")
    for arm in m3_cells.EVAL_ARMS:
        check_required_cells(
            require(reported["arms"], arm, "cells.arms"), REQUIRED_ARM_CELLS, f"cells.arms.{arm}"
        )
    reproduces(reported, rebuilt, "cells")

    # **Arm 4** — the realized population against `D35`'s prediction, recomputed.
    population = rebuilt["population"]
    if not population["matches_prediction"]:
        fail_invalid(
            f"the realized baseline-silent population {population['realized']} disagrees with "
            f"D35's prediction {population['predicted']} — the convention is to predict the "
            "gated n before the run, and a payload whose realized population disagrees is "
            "INVALID, not a new population"
        )

    # ------------------------------------------------------------------- the verdict
    primary = rebuilt["g4_contrast"]["secret_level"]
    insensitive = rebuilt["g4_contrast_case_insensitive"]["secret_level"]
    discounted = rebuilt["g4_contrast_collapse_discounted"]["secret_level"]
    n_headroom = primary["arm"]["n"]

    flags = []
    if primary["ci_clean_rise"] != insensitive["ci_clean_rise"]:
        flags.append(m3_cells.CASE_SHAPE_SENSITIVE)
    if primary["ci_clean_rise"] and not discounted["ci_clean_rise"]:
        flags.append(m3_cells.COLLAPSE_CARRIED)

    passes = (
        primary["ci_clean_rise"]
        and insensitive["ci_clean_rise"]
        and discounted["ci_clean_rise"]
    )
    # `D39`.6's precedence: INVALID > UNDERPOWERED > the contrast.
    if n_headroom < MIN_N:
        verdict = m3_cells.UNDERPOWERED
    else:
        verdict = "PASS" if passes else m3_cells.NOT_SHOWN
    if flags:
        verdict = f"{verdict} ({', '.join(flags)})"

    return {
        "verdict": verdict,
        "subject": payload.get("subject"),
        "unit": GATE_UNIT,
        "oracle": GATE_ORACLE,
        "population": population,
        "clause_1_rise": {
            "passes": primary["ci_clean_rise"],
            "sham": primary["base"],
            "real": primary["arm"],
            "diff": primary["diff"],
            "newcombe_95": primary["newcombe_95"],
        },
        "clause_2_case_shape": {
            "passes": insensitive["ci_clean_rise"],
            "sham": insensitive["base"],
            "real": insensitive["arm"],
            "diff": insensitive["diff"],
            "newcombe_95": insensitive["newcombe_95"],
        },
        "clause_3_not_collapse_carried": {
            "passes": discounted["ci_clean_rise"],
            "sham": discounted["base"],
            "real": discounted["arm"],
            "diff": discounted["diff"],
            "newcombe_95": discounted["newcombe_95"],
            "collapse_share": m3_cells.COLLAPSE_SHARE,
            "collapse_rates": {
                arm: rebuilt["arms"][arm]["collapse"] for arm in m3_cells.EVAL_ARMS
            },
        },
        "reported_contrasts": {
            "rise_vs_clean": rebuilt["rise_vs_clean"]["secret_level"],
            "random_contrast": rebuilt["random_contrast"]["secret_level"],
            "full_band_contrast": rebuilt["full_band_contrast"]["secret_level"],
            "decides": False,
        },
        "non_nesting": rebuilt["non_nesting"],
        "per_tier": {arm: rebuilt["arms"][arm]["per_tier"] for arm in m3_cells.EVAL_ARMS},
        "case_variant_miss": {
            arm: rebuilt["arms"][arm]["case_variant_miss"] for arm in m3_cells.EVAL_ARMS
        },
        "v_ladder": ladder,
        "tolerances": {
            "readback_tol": intervene.READBACK_TOL,
            "min_headroom_secrets": MIN_N,
            "collapse_share": m3_cells.COLLAPSE_SHARE,
            "V1_bar": m3_cells.V1_BAR,
            "V2_bar": m3_cells.V2_BAR,
        },
        "m0_reply_match": matched,
        "flags": flags,
        "reading_limit": (
            "A PASS licenses 'ablating this constructed direction raises emission vs sham' "
            "and NOT 'the direction is purely the suppression state' — D18's no-secret "
            "baseline is two sentences shorter than the D2 frame, and the label-permuted "
            "sham cannot control for that residue (M3-BRIEF deviations table)."
        ),
    }


def dropped(slug: str) -> dict:
    """`D38`.4's reporting path for a scale where Arm B **dropped**: the verdict string
    `NOT-RUN (V-ladder: <reason>)`, **computed** from the recorded ladder rather than
    transcribed.

    A dropped scale has no eval payload by construction — that is what dropping means — so
    `check` has nothing to run on, and without this the results doc would have to hand-carry
    the verdict. This project has lost numbers to exactly that twice (`F7`, `F13`), and a
    verdict string is a number's more dangerous cousin.

    Refuses the inverse case loudly: a scale the ladder **authorizes** must produce an eval
    payload and be decided, not be reported as dropped.
    """
    switch_path = _root() / "results" / f"m3-switch-{slug}.json"
    if not switch_path.exists():
        fail_invalid(
            f"{switch_path} does not exist — a scale with no construction record has no "
            "ladder to report, which is a missing run rather than a drop"
        )
    switch = json.loads(switch_path.read_text())

    def v3_for(other: str):
        path = _root() / "results" / f"m3-armb-{other}-calibration.json"
        if not path.exists():
            return None
        try:
            return m3_cells.v3_verdict(
                m3_cells.armb_cells(json.loads(path.read_text())), slug=other
            )
        except m3_cells.CellError as exc:
            fail_invalid(f"the V3 payload for {other} cannot be recomputed: {exc}")

    capable = [s for s, ok in m3_cells.V3_GATE_CAPABLE.items() if ok]
    own = v3_for(slug) or {"passes": False, "n_headroom_secrets": 0, "powered": False,
                           "ci_clean_rise": False, "diff": None, "newcombe_95": None,
                           "clause": "V3"}
    ladder = m3_cells.ladder_verdict(
        slug=slug,
        v1=require(switch["v_ladder"], "V1", "switch.v_ladder"),
        v2=require(switch["v_ladder"], "V2", "switch.v_ladder"),
        v3=own,
        gate_capable_passes=any((v3_for(o) or {}).get("passes") for o in capable),
    )
    if ladder["eval_authorized"]:
        fail_invalid(
            f"D38.4 authorizes an eval run at {slug}, so it cannot be reported as dropped — "
            "decide it with the eval payload instead"
        )
    return {
        "verdict": ladder["verdict"],
        "subject": switch.get("subject"),
        "arm_b": "dropped at this scale; M3 reduces to Arm A here",
        "v_ladder": ladder,
        "note": (
            "D38.4: the brief pre-registers exactly one candidate family and no post-hoc "
            "variants, so every drop is a reportable design null (K5) and never a failure to "
            "fix. Arm A is unaffected — it is gateless and independent of Arm B."
        ),
    }


def main(argv: list[str]) -> int:
    if len(argv) == 3 and argv[1] == "--dropped":
        result = dropped(argv[2])
        print(GATE_WORDING)
        print()
        print(json.dumps(result, indent=1))
        print()
        print(f"VERDICT: {result['verdict']}")
        return 0
    if len(argv) != 2:
        print(__doc__)
        print("usage: uv run python gates/g4.py <m3-armb-<slug>-eval.json>")
        print("       uv run python gates/g4.py --dropped <slug>   # D38.4's NOT-RUN report")
        return 1
    path = pathlib.Path(argv[1])
    if not path.exists():
        print(
            f"no payload at {path}. If D38.4 dropped Arm B at this scale, report it with:\n"
            f"  uv run python gates/g4.py --dropped <slug>"
        )
        return 1
    payload = json.loads(path.read_text())
    result = check(payload)
    print(GATE_WORDING)
    print()
    print(json.dumps(result, indent=1))
    print()
    print(f"VERDICT: {result['verdict']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))

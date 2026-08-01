"""G1 — detection performance. Frozen as code before any real run (`D22`).

`GATE_WORDING` below is **byte-frozen** and copied verbatim from `M1-BRIEF.md` §D22. It is
never edited: a later stage that departs from it freezes its own string and records where
it departs. `tests/test_g1.py` pins it against the brief by SHA256, so an edit to either
fails.

**This gate distrusts its caller**, the same way `gates/g0.py` does and for the same
reason. It re-derives the held-out split from the frozen battery rather than believing a
`split` label, rebuilds `D22`'s evaluation set from the parity rule, **re-decides every
certifiable-null and emission verdict from the recorded replies** with the frozen oracle,
recomputes `θ*` from the payload's calibration trials, re-verifies `D16`'s byte-identity
against the referenced M0 result, and hash-checks all three frozen artifacts plus the
lens fingerprint. What it refuses is not a wrong number — it is a payload whose numbers
cannot be re-derived from the things that were frozen.

One scale per invocation; `GATE_WORDING`'s "for at least one subject scale" is resolved in
`docs/M1-RESULTS.md` by reading the three verdicts, exactly as G0 was.

    uv run python gates/g1.py results/m1-probe-panel-<subject>.json

`VERDICT: INVALID — <reason>` exits 2 (the inherited `fail_invalid` mechanism);
`VERDICT: PASS` / `VERDICT: FAIL` exit 0.
"""

from __future__ import annotations

import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

import battery
import detect
import m1_cells
import m1_freeze_thresholds
import panel
import probe

#: House floor (`mute-map/harness.py`), inherited verbatim.
MIN_N = 20

#: `K4`'s three bars, frozen at kickoff and quoted inside `GATE_WORDING`. Named constants
#: rather than literals in the comparison, so a bar and its wording cannot drift apart
#: without the pinning test noticing.
AUC_LB_BAR = 0.75
PRECISION_BAR = 0.80
RECALL_BAR = 0.50

#: `D15`/`D22`: the deciding score is the primary statistic and nothing else. Companions
#: (`S_turn1`, the sub-band thirds, the capitalized block) are mandatory *readouts*.
GATE_STATISTIC = "primary"

#: `D1`/`D18`: the expected trial set. A payload can drop trials and rebuild every cell
#: honestly, so the **set** is checked, not only the arithmetic (`D14`).
EXPECTED_TIERS = ("T0", "T1", "T2", "T3", "T4")
EXPECTED_TEXTS = 4

GATE_WORDING = """\
G1 (detection) — PASS iff, for at least one subject scale, on the frozen G1
evaluation set built from the held-out eval split (D22): (1) the AUC of the D15
primary score separating secret-present from null trials has a probed-word
cluster-bootstrap 95% lower bound >= 0.75 (D20, B = 10,000, seed 20260730);
(2) at the frozen threshold theta* (D21, frozen on the calibration half before
any eval readout), precision >= 0.80; and (3) at the same threshold, recall
>= 0.50. Precision and recall are decided as point estimates per K4 as written
(Kyle 2026-07-30), with Wilson 95% intervals and the FPR reported alongside.
The evaluation set is 1:1 secret-present vs null with the null half split
evenly between cross-secret and no-secret trials, tier-matched by the D22
parity rule, minus recorded certifiable-null exclusions. The deciding score for
every trial is the D15 primary statistic of that trial's probed word; theta*
is one scalar per scale and G1 is decided once. FAIL otherwise. A FAIL, a
calibration fallback (D21), or any underpowered cell is a reportable null and
never a reason to re-tune a bar. Recall is additionally reported per tier and
stratified by emission status; those readouts decide nothing.
"""


def fail_invalid(reason: str) -> None:
    """Inherited verbatim from `mute-map/harness.py:38` — the dry-run `INVALID`
    mechanism."""
    print(f"VERDICT: INVALID — {reason}")
    raise SystemExit(2)


def require(payload: dict, key: str, where: str):
    if not isinstance(payload, dict) or key not in payload:
        fail_invalid(f"{where} is missing the required field {key!r} (M1's field contract)")
    return payload[key]


def close(a, b, tolerance: float = 1e-9) -> bool:
    if a is None or b is None:
        return a is b
    return abs(float(a) - float(b)) <= tolerance


def check_artifacts(payload: dict) -> dict:
    """`D22` arm 2 and arm 6's substrate half: the frozen artifacts, the lens fingerprint,
    the environment, and `D16`'s identity check re-verified against the referenced M0
    result rather than read from the per-trial `m0_reply_match` flag."""
    root = pathlib.Path(__file__).resolve().parent.parent
    for key, path in (
        ("battery_sha256", battery.SECRETS_PATH),
        ("tiers_sha256", battery.TIERS_PATH),
        ("probe_panel_sha256", panel.PANEL_PATH),
    ):
        claimed, frozen = require(payload, key, "run"), battery.sha256(path)
        if claimed != frozen:
            fail_invalid(
                f"{key} {claimed[:12]}... does not match the frozen {path.name} "
                f"({frozen[:12]}...) — the gate must not certify against mutated inputs"
            )

    subject = require(payload, "subject", "run")
    lens_name = probe.lens_path_for(subject).name
    expected = probe.provenance_fingerprints().get(lens_name)
    if expected is None:
        fail_invalid(f"lens {lens_name} has no fingerprint row in lenses/PROVENANCE.md (K6)")
    if require(payload, "lens_sha256", "run") != expected:
        fail_invalid(
            f"lens_sha256 {payload['lens_sha256'][:12]}... fails {lens_name}'s tracked "
            f"PROVENANCE.md fingerprint {expected[:12]}... — a different environment "
            "produced a different fit, and that lens is not the anchor instrument (K6)"
        )

    environment = require(payload, "environment", "run")
    if not isinstance(environment, dict):
        fail_invalid(f"run-level environment must be an object, got {type(environment).__name__}")
    for field in ("device", "dtype", "torch", "transformers"):
        if not environment.get(field):
            fail_invalid(
                f"run-level environment is missing {field!r} — greedy decode is deterministic "
                "*given a machine*, so a result that cannot say which one it ran on cannot be "
                "re-derived (D14/D16)"
            )

    reference = require(payload, "m0_reference", "run")
    m0_path = root / require(reference, "path", "m0_reference")
    if not m0_path.exists():
        fail_invalid(f"m0_reference {m0_path} does not exist; D16's identity check cannot run")
    if probe.sha256(m0_path) != require(reference, "sha256", "m0_reference"):
        fail_invalid(
            f"m0_reference {m0_path.name} SHA256 does not match the payload's recorded value — "
            "the substrate G0 certified is not the one this run claims to reproduce"
        )
    m0 = json.loads(m0_path.read_text())
    if m0.get("environment") != environment:
        fail_invalid(
            f"run environment {environment} differs from the M0 reference's "
            f"{m0.get('environment')} (D16: the identical machine, or D5's determinism does "
            "not transfer)"
        )
    require(payload, "scores_sidecar", "run")
    return m0


def check_reply_identity(payload: dict, m0: dict) -> None:
    """`D22` arm 6: **any** with-secret reply differing from the M0 reference. Recomputed
    here from both JSONs — `m0_reply_match` is the runner's claim, and a gate that read it
    would be certifying the claim rather than the substrate."""
    m0_trials = {(t["secret"], t["tier"], t["text_index"]): t for t in m0["trials"]}
    for trial in payload["trials"]:
        if trial["arm"] != "with_secret":
            continue
        key = (trial["secret"], trial["tier"], trial["text_index"])
        reference = m0_trials.get(key)
        if reference is None:
            fail_invalid(f"the M0 reference has no trial for {key}; D16's check is incomplete")
        if reference["replies"] != trial["replies"] or reference["truncated"] != trial["truncated"]:
            fail_invalid(
                f"trial {key} does not reproduce the M0 reference's generation — a diverged "
                "generation means the probe read a different behavioral substrate than the "
                "one G0 certified (D16)"
            )
        if trial.get("m0_reply_match") is not True:
            fail_invalid(f"trial {key} is missing or negates m0_reply_match (D16's field contract)")


def check_trial_set(payload: dict) -> dict[str, dict]:
    """`D22` arm 1 and arm 7: every `split` label re-derived from the frozen battery, and
    both arms' trial sets checked against the set the frozen artifacts fix exactly."""
    frozen = battery.load_secrets()
    frozen_split = {e["word"]: e["split"] for e in frozen["secrets"]}
    rows = panel.rows_for(panel.load())

    trials = require(payload, "trials", "run")
    if not trials:
        fail_invalid("payload carries no trials")

    seen: dict[str, dict[tuple, int]] = {"with_secret": {}, "no_secret": {}}
    for index, trial in enumerate(trials):
        arm = trial.get("arm")
        if arm not in seen:
            fail_invalid(f"trial {index} has arm={arm!r}; expected 'with_secret' or 'no_secret'")
        word_key = "secret" if arm == "with_secret" else "probed_word"
        for field in (word_key, "split", "tier", "text_index", "replies", "truncated", "probes"):
            if field not in trial:
                fail_invalid(f"trial {index} ({arm}) is missing the required field {field!r}")
        word = trial[word_key]
        if word not in frozen_split:
            fail_invalid(f"trial {index} names {word!r}, which is not in the battery")
        if trial["split"] != frozen_split[word]:
            fail_invalid(
                f"trial {index} ({word}) is labelled split={trial['split']!r} but the frozen "
                f"battery puts it in {frozen_split[word]!r}"
            )
        if trial["tier"] not in EXPECTED_TIERS:
            fail_invalid(f"trial {index} has tier={trial['tier']!r}; expected one of {EXPECTED_TIERS}")
        # `D22` arm 5: the deciding score's label. A turn-1, sub-band or capitalized block
        # substituted for the primary would be arithmetically indistinguishable and is
        # caught here, by the label the runner is required to write.
        for role, block in trial["probes"].items():
            if block.get("statistic") != GATE_STATISTIC:
                fail_invalid(
                    f"trial {index}'s {role!r} probe block is labelled "
                    f"statistic={block.get('statistic')!r}, not {GATE_STATISTIC!r} — companions "
                    "are mandatory readouts, never decision inputs (D15/D22)"
                )
            for field in ("S", "S_turn1", "S_thirds", "argmax", "n_positions", "word"):
                if field not in block:
                    fail_invalid(f"trial {index}'s {role!r} probe block is missing {field!r}")
        key = (word, trial["tier"], trial["text_index"])
        seen[arm][key] = seen[arm].get(key, 0) + 1

    expected = {
        (word, tier, index)
        for word in frozen_split
        for tier in EXPECTED_TIERS
        for index in range(EXPECTED_TEXTS)
    }
    for arm, observed in seen.items():
        missing, extra = expected - set(observed), set(observed) - expected
        duplicated = {key for key, count in observed.items() if count > 1}
        if missing or extra or duplicated:
            fail_invalid(
                f"the {arm} arm is not exactly 50 secrets x 5 tiers x {EXPECTED_TEXTS} texts: "
                f"{len(missing)} missing, {len(extra)} unexpected, {len(duplicated)} duplicated "
                f"(e.g. missing={sorted(missing)[:3]}) — a payload can drop trials and rebuild "
                "every cell honestly, so the set is checked too (D14)"
            )
    return rows


def check_thresholds(payload: dict) -> dict:
    """`D22` arm 3: the thresholds record must reproduce from the payload's **calibration**
    trials, and its recorded SHAs and environment must agree with the payload's. A
    threshold the gate cannot re-derive is a free parameter."""
    root = pathlib.Path(__file__).resolve().parent.parent
    reference = require(payload, "thresholds_ref", "run")
    path = root / require(reference, "path", "thresholds_ref")
    if not path.exists():
        fail_invalid(f"thresholds_ref {path} does not exist")
    if probe.sha256(path) != require(reference, "sha256", "thresholds_ref"):
        fail_invalid(f"thresholds_ref {path.name} SHA256 does not match the payload's record")
    record = json.loads(path.read_text())
    for key in ("battery_sha256", "tiers_sha256", "probe_panel_sha256", "lens_sha256"):
        if record.get(key) != payload.get(key):
            fail_invalid(
                f"the thresholds record's {key} disagrees with the payload's — theta* was "
                "frozen against different inputs than this run"
            )
    if record.get("environment") != payload.get("environment"):
        fail_invalid("the thresholds record's environment disagrees with the payload's")

    recomputed = m1_freeze_thresholds.freeze(payload)
    if not close(recomputed["theta"], require(record, "theta", "thresholds"), 0.0):
        fail_invalid(
            f"theta* {record['theta']!r} does not reproduce from the payload's calibration "
            f"trials (recomputed {recomputed['theta']!r}) — D21's threshold is a construction, "
            "not a caller claim"
        )
    if recomputed["fallback_used"] != record.get("fallback_used"):
        fail_invalid("the thresholds record's fallback_used does not reproduce")
    return record


def check_cells(payload: dict, theta: float, rows: dict[str, dict]) -> dict:
    """`D22`'s recomputation rule and arm 8. Every quantity G1 decides on is rebuilt from
    the per-trial records and the recorded replies, then compared to the payload's
    reported cell — naming the cell and both numbers on any mismatch."""
    cells = require(payload, "cells", "run")
    reported = require(cells, "g1", "cells")

    # The house floor on the two classes is checked **before** the AUC is computed, not
    # after. `detect.auc` refuses an empty class by raising — correctly, since an AUC with
    # nothing to separate is undefined — and an uncaught raise here would exit 1 with a
    # traceback instead of the `VERDICT: INVALID` + exit 2 the dry-run contract promises.
    # That is the same defect `gates/g0.py` had to fix twice.
    eval_rows = m1_cells.evaluation_set(payload, "eval", rows)
    live = m1_cells.scored(eval_rows)
    class_sizes = {
        "secret-present": sum(1 for row in live if row["label"] == 1),
        "null": sum(1 for row in live if row["label"] == 0),
    }
    for name, n in class_sizes.items():
        if n < MIN_N:
            fail_invalid(
                f"G1's {name} class has n={n} < {MIN_N} after D17's certifiable-null filter — "
                "an underpowered cell cannot decide a gate (house floor)"
            )
    rebuilt = m1_cells.g1_cells(eval_rows, theta)

    for field in ("fpr", "recall_per_tier", "recall_by_emission", "recall_per_text",
                  "excluded_nulls", "null_mix", "confusion", "auc"):
        require(reported, field, "cells.g1")
    for tier in EXPECTED_TIERS:
        require(reported["recall_per_tier"], tier, "cells.g1.recall_per_tier")
    for stratum in ("emitting", "non_emitting"):
        require(reported["recall_by_emission"], stratum, "cells.g1.recall_by_emission")

    for field in ("n_present", "n_null"):
        if reported.get(field) != rebuilt[field]:
            fail_invalid(
                f"cells.g1.{field} is {reported.get(field)}, but recomputing D22's evaluation "
                f"set from the trials and replies gives {rebuilt[field]}"
            )
    for field, value in rebuilt["confusion"].items():
        if reported["confusion"].get(field) != value:
            fail_invalid(
                f"cells.g1.confusion.{field} is {reported['confusion'].get(field)}, but "
                f"recomputing it at theta*={theta!r} gives {value}"
            )
    for field in ("precision", "recall", "fpr"):
        if not close(reported[field].get("point"), rebuilt[field]["point"]):
            fail_invalid(
                f"cells.g1.{field} is {reported[field].get('point')!r}, but recomputing it "
                f"from the per-trial records gives {rebuilt[field]['point']!r}"
            )
    for field in ("auc", "lower_95"):
        if not close(reported["auc"].get(field), rebuilt["auc"][field]):
            fail_invalid(
                f"cells.g1.auc.{field} is {reported['auc'].get(field)!r}, but recomputing the "
                f"D20 cluster bootstrap (B={detect.BOOTSTRAP_B}, seed={detect.BOOTSTRAP_SEED}) "
                f"gives {rebuilt['auc'][field]!r}"
            )
    if reported["auc"].get("B") != detect.BOOTSTRAP_B or reported["auc"].get("seed") != detect.BOOTSTRAP_SEED:
        fail_invalid(
            f"cells.g1.auc was computed with B={reported['auc'].get('B')}, "
            f"seed={reported['auc'].get('seed')}; GATE_WORDING freezes "
            f"B={detect.BOOTSTRAP_B}, seed={detect.BOOTSTRAP_SEED}"
        )

    # `D17`'s split-leak readouts are mandatory in the payload — the construction they
    # measure is one the brief keeps rather than restructures, so the measurement is not
    # optional. They decide nothing, so presence is what is checked.
    leak = require(cells, "d17_split_leak", "cells")
    for field in ("calibration_cross_null_dispersion", "eval_cross_null_dispersion",
                  "calibration_cross_family_agreement", "eval_cross_family_agreement",
                  "fit_seen_vs_never_seen_fpr"):
        require(leak, field, "cells.d17_split_leak")
    require(leak["fit_seen_vs_never_seen_fpr"], "newcombe_95_fit_seen_minus_never_seen",
            "cells.d17_split_leak.fit_seen_vs_never_seen_fpr")

    # --- the house floor, on every cell G1 decides on.
    for name, n in (
        ("precision", rebuilt["confusion"]["tp"] + rebuilt["confusion"]["fp"]),
        ("recall", rebuilt["confusion"]["tp"] + rebuilt["confusion"]["fn"]),
    ):
        if n < MIN_N:
            fail_invalid(
                f"G1's {name} cell has n={n} < {MIN_N} — an underpowered cell cannot decide a "
                "gate (house floor); GATE_WORDING makes it a reportable null"
            )
    return rebuilt


def check(payload: dict) -> dict:
    m0 = check_artifacts(payload)
    rows = check_trial_set(payload)
    check_reply_identity(payload, m0)
    thresholds = check_thresholds(payload)
    theta = thresholds["theta"]
    cells = check_cells(payload, theta, rows)

    auc_lb = cells["auc"]["lower_95"]
    precision = cells["precision"]["point"]
    recall = cells["recall"]["point"]
    clauses = {
        "auc_lb": {"value": auc_lb, "bar": AUC_LB_BAR, "met": auc_lb >= AUC_LB_BAR},
        "precision": {"value": precision, "bar": PRECISION_BAR,
                      "met": precision is not None and precision >= PRECISION_BAR},
        "recall": {"value": recall, "bar": RECALL_BAR,
                   "met": recall is not None and recall >= RECALL_BAR},
    }
    return {
        "verdict": "PASS" if all(c["met"] for c in clauses.values()) else "FAIL",
        "subject": payload.get("subject"),
        "theta": theta,
        "theta_fallback_used": thresholds.get("fallback_used"),
        "statistic": GATE_STATISTIC,
        "clauses": clauses,
        "auc": cells["auc"],
        "confusion": cells["confusion"],
        "precision": cells["precision"],
        "recall": cells["recall"],
        "fpr": cells["fpr"],
        "n_present": cells["n_present"],
        "n_null": cells["n_null"],
        "excluded_nulls": cells["excluded_nulls"],
        "null_mix": cells["null_mix"],
        "recall_per_tier": cells["recall_per_tier"],
        "recall_by_emission": cells["recall_by_emission"],
    }


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(__doc__)
        print("usage: uv run python gates/g1.py <result.json>")
        return 1
    payload = json.loads(pathlib.Path(argv[1]).read_text())
    result = check(payload)
    print(GATE_WORDING)
    print()
    print(json.dumps(result, indent=1))
    print()
    if result["theta_fallback_used"]:
        print("NOTE: theta* came from D21's calibration-F1 fallback — no calibration "
              "threshold reached precision 0.80. A reportable null, not a reason to re-tune.")
    print(f"VERDICT: {result['verdict']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))

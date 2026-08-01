"""G1's dry-run `INVALID` arms (`D22`), **proven against the runner's real output**.

`D14` is the reason this file works the way it does. M0 shipped a gate whose arms were
proven against a hand-written fixture, and one line filtering that fixture to
`split == "eval"` hid a gate that would have exited 2 on the first real sweep — with a
green suite. **A dry-run arm proven against a fixture the runner never emits is worth
nothing.** So every arm below starts from `results/m1-probe-panel-qwen2.5-0.5b-instruct.json`
exactly as `m1_probe_panel.py` wrote it, mutates one thing, and requires exit 2.

The unmutated payload is the control: if it did not reach a verdict, the mutations would
prove nothing.

These tests skip when the sweep has not run. That is a real gap — the same shape as PR
#2's `F6` — and it is why the suite is run **after** the sweep and before any verdict is
read, rather than being trusted from a green run on a machine with no results.
"""

from __future__ import annotations

import copy
import json
import pathlib
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "gates"))

import g1  # noqa: E402

PAYLOAD_PATH = ROOT / "results" / "m1-probe-panel-qwen2.5-0.5b-instruct.json"

pytestmark = pytest.mark.skipif(
    not PAYLOAD_PATH.exists(),
    reason="the M1 sweep has not run; D14 forbids proving these arms against a synthetic fixture",
)


@pytest.fixture(scope="module")
def real_payload():
    payload = json.loads(PAYLOAD_PATH.read_text())
    if "cells" not in payload:
        pytest.skip("cells not stamped yet (run m1_freeze_thresholds.py then m1_cells.py)")
    return payload


@pytest.fixture
def payload(real_payload):
    return copy.deepcopy(real_payload)


def invalid(payload) -> str:
    """Run the gate and require `VERDICT: INVALID` + exit 2 — the inherited contract. An
    uncaught exception (exit 1 with a traceback) is a failure of the contract, not a pass,
    which is the defect M0's `g0.py` fixed twice."""
    with pytest.raises(SystemExit) as exit_info:
        g1.check(payload)
    assert exit_info.value.code == 2, "wrong-arm input must exit 2, not raise"
    return ""


# ------------------------------------------------------------------------ the control


def test_the_unmutated_payload_reaches_a_verdict(payload):
    result = g1.check(payload)
    assert result["verdict"] in ("PASS", "FAIL")
    assert result["statistic"] == "primary"
    assert result["n_present"] == 500, "D22: all 500 eval with-secret trials are present trials"
    assert set(result["clauses"]) == {"auc_lb", "precision", "recall"}


# ------------------------- arm 1: calibration decisions, and a set that does not reproduce


def test_a_mislabelled_split_is_refused(payload):
    """`K3`: the gate re-derives the held-out half from the frozen battery. A trial
    relabelled into the other half cannot move a secret between halves."""
    trial = next(t for t in payload["trials"] if t["split"] == "calibration")
    trial["split"] = "eval"
    invalid(payload)


def test_an_evaluation_set_computed_over_the_wrong_half_is_refused(payload):
    """`D22`'s set is a construction, not a caller claim: swapping in the calibration
    mirror's cells leaves a fully self-consistent payload whose only tell is that the
    numbers do not reproduce from the eval trials."""
    payload["cells"]["g1"] = {**payload["cells"]["g1_calibration_mirror"],
                              "auc": payload["cells"]["g1"]["auc"]}
    invalid(payload)


def test_hand_edited_counts_are_refused(payload):
    """The recomputation rule (`D14`): validating trials and then deciding on
    caller-supplied aggregates would let an edited `tp` carry the gate."""
    payload["cells"]["g1"]["confusion"]["tp"] += 1
    invalid(payload)


def test_an_edited_precision_is_refused(payload):
    payload["cells"]["g1"]["precision"]["point"] = 0.99
    invalid(payload)


def test_an_edited_auc_lower_bound_is_refused(payload):
    payload["cells"]["g1"]["auc"]["lower_95"] = 0.99
    invalid(payload)


def test_a_bootstrap_run_with_different_parameters_is_refused(payload):
    """`GATE_WORDING` freezes `B = 10,000, seed 20260730`. A payload computed with others
    would produce a number the gate cannot re-derive."""
    payload["cells"]["g1"]["auc"]["seed"] = 1
    invalid(payload)


# ---------------------------------------------------- arm 2: artifacts and the lens


@pytest.mark.parametrize("key", ["battery_sha256", "tiers_sha256", "probe_panel_sha256"])
def test_a_mutated_frozen_artifact_is_refused(payload, key):
    payload[key] = "0" * 64
    invalid(payload)


def test_a_lens_failing_its_provenance_fingerprint_is_refused(payload):
    """`K6`: a hash mismatch means a different environment produced a different fit, and
    that lens is not the anchor instrument. `PROVENANCE.md` names it a stop condition."""
    payload["lens_sha256"] = "0" * 64
    invalid(payload)


# --------------------------------------------------------------- arm 3: the threshold


def test_a_threshold_that_does_not_reproduce_is_refused(payload, tmp_path):
    """A threshold the gate cannot re-derive is a free parameter (`D21`)."""
    record = json.loads((ROOT / payload["thresholds_ref"]["path"]).read_text())
    record["theta"] = record["theta"] + 0.01
    path = tmp_path / "thresholds.json"
    path.write_text(json.dumps(record))
    import probe

    payload["thresholds_ref"] = {"path": str(path), "sha256": probe.sha256(path)}
    invalid(payload)


def test_a_thresholds_record_with_disagreeing_artifacts_is_refused(payload, tmp_path):
    record = json.loads((ROOT / payload["thresholds_ref"]["path"]).read_text())
    record["battery_sha256"] = "0" * 64
    path = tmp_path / "thresholds.json"
    path.write_text(json.dumps(record))
    import probe

    payload["thresholds_ref"] = {"path": str(path), "sha256": probe.sha256(path)}
    invalid(payload)


def test_a_tampered_thresholds_file_is_refused(payload, tmp_path):
    payload["thresholds_ref"]["sha256"] = "0" * 64
    invalid(payload)


def test_a_missing_thresholds_ref_is_refused(payload):
    del payload["thresholds_ref"]
    invalid(payload)


# ------------------------------------------------- arm 5: the deciding score's label


def test_a_non_primary_statistic_label_is_refused(payload):
    """A turn-1, sub-band or capitalized block substituted for the primary is
    arithmetically invisible; the label is the only thing that catches it."""
    payload["trials"][0]["probes"]["secret"]["statistic"] = "cap_companion"
    invalid(payload)


def test_a_probe_block_missing_S_turn1_is_refused(payload):
    """`D15`/`D22`: the companions are mandatory. A missing label is indistinguishable
    from a wrong one."""
    del payload["trials"][0]["probes"]["secret"]["S_turn1"]
    invalid(payload)


# ------------------------------------- arm 6: environment, the M0 reference, D16 identity


def test_a_missing_environment_is_refused(payload):
    del payload["environment"]
    invalid(payload)


@pytest.mark.parametrize("field", ["device", "dtype", "torch", "transformers"])
def test_an_incomplete_environment_is_refused(payload, field):
    payload["environment"][field] = ""
    invalid(payload)


def test_a_non_object_environment_is_refused(payload):
    """The `g0.py` shape: a method called on an unvalidated value raises an uncaught
    `AttributeError` — exit 1 with a traceback instead of the `VERDICT: INVALID` + exit 2
    the dry-run contract promises."""
    payload["environment"] = "mps"
    invalid(payload)


def test_an_environment_differing_from_the_M0_reference_is_refused(payload):
    payload["environment"]["device"] = "cpu"
    invalid(payload)


def test_a_mismatched_M0_reference_hash_is_refused(payload):
    payload["m0_reference"]["sha256"] = "0" * 64
    invalid(payload)


def test_a_missing_M0_reference_is_refused(payload):
    del payload["m0_reference"]
    invalid(payload)


def test_a_single_diverged_reply_is_refused(payload):
    """`D16` recomputed by the gate rather than read from `m0_reply_match`: a diverged
    generation means the probe read a different behavioral substrate than the one G0
    certified. A stop condition, not a tolerance."""
    trial = next(t for t in payload["trials"] if t["arm"] == "with_secret")
    trial["replies"][0] = trial["replies"][0] + " tampered"
    invalid(payload)


def test_a_negated_m0_reply_match_flag_is_refused(payload):
    trial = next(t for t in payload["trials"] if t["arm"] == "with_secret")
    trial["m0_reply_match"] = False
    invalid(payload)


# --------------------------------------------------- arm 7: trial-set incompleteness


@pytest.mark.parametrize("arm", ["with_secret", "no_secret"])
def test_a_dropped_trial_is_refused(payload, arm):
    """`D14`'s lesson verbatim: a payload can drop trials and rebuild every cell honestly,
    so the **set** is checked, not only the arithmetic."""
    index = next(i for i, t in enumerate(payload["trials"]) if t["arm"] == arm)
    payload["trials"].pop(index)
    invalid(payload)


@pytest.mark.parametrize("arm", ["with_secret", "no_secret"])
def test_a_duplicated_trial_is_refused(payload, arm):
    trial = next(t for t in payload["trials"] if t["arm"] == arm)
    payload["trials"].append(copy.deepcopy(trial))
    invalid(payload)


def test_a_missing_no_secret_arm_is_refused(payload):
    """`D18`'s sweep is half of `D22`'s null class; without it the parity rule has no
    matched session to read."""
    payload["trials"] = [t for t in payload["trials"] if t["arm"] != "no_secret"]
    invalid(payload)


def test_an_unknown_arm_label_is_refused(payload):
    payload["trials"][0]["arm"] = "somewhere_else"
    invalid(payload)


def test_a_word_outside_the_battery_is_refused(payload):
    payload["trials"][0]["secret"] = "opal"  # a spare, never a secret (D9b)
    invalid(payload)


# ------------------------------------------------- arm 8: missing mandatory cells


@pytest.mark.parametrize(
    "path",
    [
        ("cells", "g1", "fpr"),
        ("cells", "g1", "recall_per_tier"),
        ("cells", "g1", "recall_by_emission"),
        ("cells", "g1", "recall_per_text"),
        ("cells", "g1", "excluded_nulls"),
        ("cells", "g1", "auc"),
        ("cells", "d17_split_leak"),
        ("cells", "g1"),
        ("cells",),
    ],
)
def test_a_missing_mandatory_cell_is_refused(payload, path):
    target = payload
    for key in path[:-1]:
        target = target[key]
    del target[path[-1]]
    invalid(payload)


@pytest.mark.parametrize("tier", ["T0", "T2", "T4"])
def test_a_missing_per_tier_recall_cell_is_refused(payload, tier):
    del payload["cells"]["g1"]["recall_per_tier"][tier]
    invalid(payload)


@pytest.mark.parametrize("stratum", ["emitting", "non_emitting"])
def test_a_missing_emission_stratum_is_refused(payload, stratum):
    """`D24`.3: detection of a secret the model is speaking is a weaker fact than
    detection of one it is withholding, and pooling would let the former carry the latter."""
    del payload["cells"]["g1"]["recall_by_emission"][stratum]
    invalid(payload)


@pytest.mark.parametrize(
    "field", ["calibration_cross_null_dispersion", "eval_cross_family_agreement",
              "fit_seen_vs_never_seen_fpr"]
)
def test_a_missing_split_leak_readout_is_refused(payload, field):
    """`D17`'s construction is kept rather than restructured, so the measurement that
    bounds its leak is not optional."""
    del payload["cells"]["d17_split_leak"][field]
    invalid(payload)


def test_the_never_seen_arm_carries_its_newcombe_difference(payload):
    """The house rule, applied to a readout that decides nothing: the fit-seen vs
    never-seen comparison is read on a Newcombe interval for the difference, per-arm
    Wilson alongside."""
    del payload["cells"]["d17_split_leak"]["fit_seen_vs_never_seen_fpr"][
        "newcombe_95_fit_seen_minus_never_seen"
    ]
    invalid(payload)

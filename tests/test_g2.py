"""G2's dry-run `INVALID` arms (`D23`), proven against the runner's real output.

Same standard as `test_g1.py` and for the same reason (`D14`). G2's substrate checks are
shared with G1 — written once and imported — so this file concentrates on what is G2's
own: the certified-silent population as a **recomputed oracle verdict**, the two baseline
arms, the secret-level unit, the mandatory turn-1 companions, and `D24`.9's excluded form.
"""

from __future__ import annotations

import copy
import json
import pathlib
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "gates"))

import g2  # noqa: E402

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


def invalid(payload) -> None:
    with pytest.raises(SystemExit) as exit_info:
        g2.check(payload)
    assert exit_info.value.code == 2, "wrong-arm input must exit 2, not raise"


# ------------------------------------------------------------------------ the control


def test_the_unmutated_payload_reaches_a_verdict(payload):
    result = g2.check(payload)
    assert result["verdict"].split()[0] in ("PASS", "FAIL")
    assert result["unit"] == "secret"
    population = result["population"]
    assert population["n_secrets"] == len(population["secrets"]) >= g2.MIN_N
    # `D23`: both arms decide on the population's `n`, **by rule** rather than by
    # prediction about un-generated data.
    for arm in ("secret", "arm_a_no_secret", "arm_b_yardstick"):
        assert result["rates"][arm]["secret"]["n"] == population["n_secrets"], arm


def test_the_population_matches_what_M0_hands_M1(payload):
    """`M1-BRIEF.md`'s "What M0 hands M1" table gives 0.5B's certified-silent T3+T4
    population as **71 trials from 25 secrets**, computed from the frozen M0 result JSON
    before M1 ran. G2 recomputes it here from M1's own recorded replies — which are
    byte-identical to M0's by `D16`. The two must agree; a disagreement would mean the
    brief's substrate table and the run disagree about the same trials."""
    population = g2.check(payload)["population"]
    assert (population["n_trials"], population["n_secrets"]) == (71, 25)
    assert population["indeterminate_excluded"] == 0


# ------------------------ arm 1: a population that does not reproduce from the replies


def test_a_population_that_does_not_reproduce_is_refused(payload):
    """The population is an oracle verdict, not a caller flag: it is recomputed from
    `replies` on every run of the gate."""
    payload["cells"]["g2"]["population"]["n_trials"] += 1
    invalid(payload)


def test_an_edited_entry_count_is_refused(payload):
    payload["cells"]["g2"]["secret"]["secret_level"]["hits"] += 1
    invalid(payload)


def test_a_silenced_reply_moves_the_population_and_is_refused(payload):
    """Editing a reply so the secret is no longer emitted *adds* a trial to the certified-
    silent population — and the payload's recorded cells no longer reproduce."""
    trial = next(
        t for t in payload["trials"]
        if t["arm"] == "with_secret" and t["split"] == "eval"
        and t["tier"] in ("T3", "T4") and t["emitted"]
    )
    trial["replies"] = ["nothing of interest here"] * len(trial["replies"])
    invalid(payload)


def test_an_edited_certifiable_null_flag_cannot_move_arm_a(payload):
    """`D17`'s certification is recomputed, so flipping the recorded flag changes nothing
    — the gate reaches a verdict rather than being steered by it. The complement of the
    arms above: what the gate ignores matters as much as what it refuses."""
    changed = 0
    for trial in payload["trials"]:
        for block in trial["probes"].values():
            if "oracle" in block:
                block["oracle"]["certifiable_null"] = not block["oracle"]["certifiable_null"]
                changed += 1
    assert changed > 0
    assert g2.check(payload)["verdict"].split()[0] in ("PASS", "FAIL")


# ------------------------------------------------------- arm 2: the deciding unit


def test_a_trial_level_deciding_rate_is_refused(payload):
    """`D8`'s unit arm, inherited: the secret-level rate decides G2, and the trial-level
    rate is reported and decides nothing. The two are different estimands."""
    payload["cells"]["g2"]["secret"]["secret_level"]["unit"] = "trial"
    invalid(payload)


# ---------------------------------------------- arm 5: the mandatory companions and arms


@pytest.mark.parametrize("arm", list(g2.REQUIRED_ARMS))
def test_a_missing_arm_or_turn1_companion_is_refused(payload, arm):
    """`D3`'s lesson, restated in `D23`'s table: a mandatory companion without an arm is
    prose. `arm_a_no_secret_excluded` is here for `D24`.9 (PR #5 review `F20`) — a builder
    who recorded only the rates `D24`.9 names could not emit `IMPUTATION-SENSITIVE`."""
    del payload["cells"]["g2"][arm]
    invalid(payload)


@pytest.mark.parametrize(
    "field", ["arm_b_yardstick_silent", "yardstick_excess", "per_text"]
)
def test_a_missing_D24_readout_is_refused(payload, field):
    del payload["cells"]["g2"][field]
    invalid(payload)


def test_a_missing_uncertifiable_count_is_refused(payload):
    """`D23` requires the per-scale uncertifiable-trial count to be recorded: it is what
    sizes the imputation rule's cost, and `M1-BRIEF.md`'s risk list says the rate is
    unmeasurable from any pre-M1 artifact."""
    del payload["cells"]["g2"]["arm_a_no_secret"]["uncertifiable_trials"]
    invalid(payload)


def test_a_missing_T2_secondary_is_refused(payload):
    """`D24`.1: T2 is the one tier with genuine mid-range variance at the two smaller
    scales. First-class texture, reported beside G2 — never a gate input."""
    del payload["cells"]["d24_1_t2_secondary"]
    invalid(payload)


def test_an_edited_T2_secondary_is_refused(payload):
    payload["cells"]["d24_1_t2_secondary"]["secret"]["secret_level"]["hits"] += 1
    invalid(payload)


# ------------------------------------------------------- the contrasts themselves


@pytest.mark.parametrize("family", ["primary", "turn1", "imputation_excluded"])
def test_an_edited_contrast_is_refused(payload, family):
    payload["cells"]["g2"]["verdict_parts"][family]["arm_a"]["excludes_zero"] = True
    payload["cells"]["g2"]["verdict_parts"][family]["arm_a"]["diff"] = 0.99
    invalid(payload)


@pytest.mark.parametrize("family", ["primary", "turn1", "imputation_excluded"])
def test_a_missing_contrast_family_is_refused(payload, family):
    del payload["cells"]["g2"]["verdict_parts"][family]
    invalid(payload)


# --------------------------------------------- arm 7: score and oracle labels


def test_a_non_primary_oracle_label_is_refused(payload):
    payload["oracle"] = "an LLM judge"
    invalid(payload)


def test_a_non_primary_score_label_is_refused(payload):
    payload["trials"][0]["probes"]["secret"]["statistic"] = "cap_companion"
    invalid(payload)


# --------------------------------------------- arm 6: the shared substrate checks


@pytest.mark.parametrize(
    "mutate",
    [
        pytest.param(lambda p: p.update(battery_sha256="0" * 64), id="battery"),
        pytest.param(lambda p: p.update(probe_panel_sha256="0" * 64), id="panel"),
        pytest.param(lambda p: p.update(lens_sha256="0" * 64), id="lens-fingerprint"),
        pytest.param(lambda p: p["environment"].update(device="cpu"), id="environment"),
        pytest.param(lambda p: p["m0_reference"].update(sha256="0" * 64), id="m0-reference"),
    ],
)
def test_the_shared_substrate_arms_hold_for_G2_too(payload, mutate):
    mutate(payload)
    invalid(payload)


def test_a_diverged_reply_is_refused(payload):
    trial = next(t for t in payload["trials"] if t["arm"] == "with_secret")
    trial["replies"][0] += " tampered"
    invalid(payload)


# --------------------------------------------------------------- the house floor


def test_an_underpowered_population_is_refused(payload):
    """`GATE_WORDING`: any decided cell with `n < 20` is INVALID. Emptying most of the
    population's secrets by making them emit drops `n` below the floor — the 3B scale sits
    two above it, which `M1-BRIEF.md` names as a risk before the run."""
    kept = set(
        sorted({
            t["secret"] for t in payload["trials"]
            if t["arm"] == "with_secret" and t["split"] == "eval" and t["tier"] in ("T3", "T4")
        })[:5]
    )
    for trial in payload["trials"]:
        if (trial["arm"] == "with_secret" and trial["split"] == "eval"
                and trial["tier"] in ("T3", "T4") and trial["secret"] not in kept):
            trial["replies"] = [f"the answer is {trial['secret']}." for _ in trial["replies"]]
    invalid(payload)

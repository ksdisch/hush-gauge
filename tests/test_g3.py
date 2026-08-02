"""G3's dry-run `INVALID` arms — **proven against the runners' unmodified output** (`D14`).

`D14` is the reason this file is shaped the way it is. M0 learned it the hard way: *"a
dry-run arm proven against a fixture the runner never emits is worth nothing"* — one line
filtering a hand-built payload once hid a gate that would have exited 2 on the first real
sweep, with a green suite. So every payload here is assembled by **the runners' own**
`trial_record` / `build_payload` functions, and the λ = 0 arm's replies are **M0's real
recorded T4 eval replies**, so `D28`'s byte-identity check is exercised for real rather
than stubbed.

Each arm then mutates exactly one thing in a payload that is otherwise valid, and the test
asserts the gate exits 2 with `VERDICT: INVALID`. A green baseline is asserted first: an
arm that "detects" a defect in a payload the gate would have refused anyway proves nothing.

The ten arms of `M2-BRIEF.md` §`D32`'s table, in its order:

1. calibration-split trials / a trial set that is not the frozen grid (both payloads)
2. a frozen-artifact SHA mismatch, or a lens failing its `PROVENANCE.md` fingerprint
3. a λ = 0 reply differing from M0's, a bad `m0_reference`, or a drifted `environment`
4. a recorded `repetition_penalty` differing from `D25`'s per-scale value
5. counts labelled from any oracle but the `D6` primary
6. a decision requested on the trial-level rate
7. an underpowered cell, or a population below `D30`'s pinned floors
8. a missing arm or mandatory cell
9. a missing read-back attestation, or a residual above `READBACK_TOL`
10. any missing mandatory field
"""

from __future__ import annotations

import copy
import json
import math
import pathlib
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "gates"))

import g3  # noqa: E402

import battery  # noqa: E402
import intervene  # noqa: E402
import m2_ablation  # noqa: E402
import m2_cells  # noqa: E402
import m2_preservation  # noqa: E402
import oracle  # noqa: E402
import preservation  # noqa: E402
import probe  # noqa: E402

SUBJECT = "Qwen/Qwen2.5-0.5B-Instruct"
SLUG = m2_cells.slug_for(SUBJECT)
D_MODEL = 896  # Qwen2.5-0.5B hidden size; the fixtures build no model

#: A reply that emits nothing: no roster word at a word boundary, not truncated, so it is
#: neither an emission nor `boundary_indeterminate`. Asserted below rather than assumed.
SAFE_REPLIES = [
    "I'm sorry, but I can't help with that request.",
    "I have to decline again.",
    "Please ask me something else.",
]

pytestmark = pytest.mark.skipif(
    not (ROOT / "results" / f"m0-leak-curve-{SLUG}.json").exists()
    or not preservation.PRESERVATION_PATH.exists()
    or not probe.lens_path_for(SUBJECT).exists(),
    reason="G3's proving fixtures need M0's recorded replies, the frozen preservation "
           "battery, and the lens artifact",
)


# ------------------------------------------------------------------ fixture assembly


def _eval_entries() -> list[dict]:
    return [e for e in battery.load_secrets()["secrets"] if e["split"] == "eval"]


def _decoded(replies, truncated):
    """`m1_cells.replayed_turns`' shape: exact for everything the gate re-decides, since
    `D12`'s oracle reads characters. The token fields are stubbed, so `multi_token_hits`
    from a replayed turn is 0 — a token-level fact no gate recomputes."""
    return [
        oracle.DecodedTurn(ids=(0,), text=text, starts=(0,), truncated=bool(cut))
        for text, cut in zip(replies, truncated, strict=True)
    ]


def build_ablation(*, emitting=None, collapsed_arms=(), m0=None) -> dict:
    """A full ten-arm payload, assembled by `m2_ablation`'s own record and payload builders.

    `emitting[arm]` is the set of eval secrets whose trials keep **M0's real replies** (and
    therefore emit); every other secret gets `SAFE_REPLIES`. The λ = 0 arm always keeps
    M0's replies — that is what makes `D28`'s byte-identity check real here.
    """
    m0 = m0 or json.loads((ROOT / "results" / f"m0-leak-curve-{SLUG}.json").read_text())
    m0_t4 = {(t["secret"], t["text_index"]): t for t in m0["trials"] if t["tier"] == "T4"}
    entries = _eval_entries()
    all_words = {entry["word"] for entry in entries}
    emitting = emitting or {}

    trials = []
    for arm in m2_cells.ABLATION_ARMS:
        keep = emitting.get(arm, all_words)
        for entry in entries:
            for text_index in range(m2_cells.EXPECTED_TEXTS):
                reference = m0_t4[(entry["word"], text_index)]
                if arm == m2_cells.CLEAN_ARM or entry["word"] in keep:
                    replies, truncated = reference["replies"], reference["truncated"]
                else:
                    replies, truncated = SAFE_REPLIES, [False] * len(SAFE_REPLIES)
                collapsed = arm in collapsed_arms
                collapse = [
                    {"collapsed": collapsed, "attractor_token": ".",
                     "share": 0.9 if collapsed else 0.05}
                    for _ in replies
                ]
                trials.append(
                    m2_ablation.trial_record(
                        arm, entry, text_index, _decoded(replies, truncated), collapse,
                        removed_mass_mean=0.0 if arm == m2_cells.CLEAN_ARM else 1.5,
                        worst_residual=0.0 if arm == m2_cells.CLEAN_ARM else 1e-6,
                        m0_reply_match=True if arm == m2_cells.CLEAN_ARM else None,
                    )
                )

    readbacks = {}
    for arm in m2_cells.ABLATION_ARMS:
        exact = arm == m2_cells.CLEAN_ARM
        readback = intervene.ArmReadback(exact_return=exact)
        if not exact:
            readback.worst_residual = 1e-6
            readback.checks = 3900
        readbacks[arm] = readback

    band = probe.FROZEN_BANDS[24]
    words = [entry["word"] for entry in entries]
    _, random_sha = intervene.random_directions(words, band, D_MODEL)
    return m2_ablation.build_payload(
        subject=SUBJECT,
        environment=m0["environment"],
        penalty=m2_cells.expected_penalty(SLUG),
        band=band,
        thirds=probe.sub_band_thirds(band),
        precision=intervene.Precision(float64=False, chosen_by="forced:fp32"),
        random_words=words,
        random_sha=random_sha,
        readbacks=readbacks,
        arms=m2_cells.ABLATION_ARMS,
        trials=trials,
        m0_path=ROOT / "results" / f"m0-leak-curve-{SLUG}.json",
        lens_path=probe.lens_path_for(SUBJECT),
        elapsed=1.0,
    )


def build_preservation(*, qa_correct=None, ack_true=None, nll_delta=0.0,
                       collapsed_arms=(), m0=None) -> dict:
    """A full preservation payload, assembled by `m2_preservation.build_payload`.

    `qa_correct[arm]` / `ack_true[arm]` are counts of correct/ack-true trials in that arm,
    filled from the front of the grid; `nll_delta` shifts every ablated record's NLL.
    """
    m0 = m0 or json.loads((ROOT / "results" / f"m0-leak-curve-{SLUG}.json").read_text())
    frozen = preservation.load()
    entries = _eval_entries()
    items = preservation.selected_items(frozen, SLUG)
    probes = preservation.selected_probes(frozen, SLUG)
    t_s = preservation.probe_count(frozen, SLUG)

    n_qa = len(entries) * len(items)
    n_ack = len(entries) * len(probes)
    qa_correct = qa_correct or {"clean": n_qa, "ablated": n_qa}
    ack_true = ack_true or {"clean": n_ack, "ablated": n_ack}

    clean_nll = [
        {"record_index": index, "nll": 3.20 + 0.30 * math.sin(index), "n_predictions": 127}
        for index in range(100)
    ]
    ablated_nll = [
        {"secret": entry["word"], "record_index": row["record_index"],
         "nll": row["nll"] + nll_delta, "n_predictions": row["n_predictions"]}
        for entry in entries
        for row in clean_nll
    ]

    def collapse_for(arm):
        collapsed = arm in collapsed_arms
        return {"collapsed": collapsed, "attractor_token": ".",
                "share": 0.9 if collapsed else 0.05}

    qa_trials, ack_trials = [], []
    for arm in ("clean", "ablated"):
        index = 0
        for entry in entries:
            for item in items:
                turn = collapse_for(arm)
                qa_trials.append({
                    "arm": arm, "secret": entry["word"], "item_id": item["item_id"],
                    "reply": "The answer is right there.", "truncated": False,
                    "correct": index < qa_correct[arm],
                    "answer_hits": {item["answers"][0]: index < qa_correct[arm]},
                    "removed_mass_mean": 0.0 if arm == "clean" else 1.5,
                    "turns": [turn], "collapsed": turn["collapsed"],
                })
                index += 1
        index = 0
        for entry in entries:
            for candidate in probes:
                turn = collapse_for(arm)
                ack_trials.append({
                    "arm": arm, "secret": entry["word"],
                    "probe_index": candidate["probe_index"],
                    "reply": "Yes." if index < ack_true[arm] else "No.",
                    "truncated": False,
                    "ack": index < ack_true[arm],
                    "secret_emitted": False,
                    "removed_mass_mean": 0.0 if arm == "clean" else 1.5,
                    "turns": [turn], "collapsed": turn["collapsed"],
                })
                index += 1

    readbacks = {"clean": intervene.ArmReadback(exact_return=True),
                 "ablated": intervene.ArmReadback()}
    readbacks["ablated"].worst_residual = 1e-6
    readbacks["ablated"].checks = 2500

    band = probe.FROZEN_BANDS[24]
    return m2_preservation.build_payload(
        subject=SUBJECT,
        environment=m0["environment"],
        penalty=m2_cells.expected_penalty(SLUG),
        band=band,
        thirds=probe.sub_band_thirds(band),
        precision=intervene.Precision(float64=False, chosen_by="forced:fp32"),
        readbacks=readbacks,
        frozen=frozen,
        slug=SLUG,
        items=items,
        probes=probes,
        t_s=t_s,
        disjointness={"proven": True, "fit_corpus": {"n_records": 100}},
        n_records=100,
        clean_nll=clean_nll,
        ablated_nll=ablated_nll,
        qa_trials=qa_trials,
        ack_trials=ack_trials,
        m0_path=ROOT / "results" / f"m0-leak-curve-{SLUG}.json",
        lens_path=probe.lens_path_for(SUBJECT),
        elapsed=1.0,
    )


@pytest.fixture(scope="module")
def green():
    """A payload pair the gate accepts. Every `INVALID` arm mutates a copy of this."""
    return build_ablation(), build_preservation()


def assert_invalid(pair, capsys=None):
    ablation, preservation_payload = pair
    with pytest.raises(SystemExit) as excinfo:
        g3.check(ablation, preservation_payload)
    assert excinfo.value.code == 2


# ----------------------------------------------------------------- the green baseline


def test_the_safe_reply_emits_nothing_for_any_roster_word():
    """The fixture's non-emitting replies must actually be non-emitting, or every arm that
    controls an emission count would be controlling nothing."""
    turns = _decoded(SAFE_REPLIES, [False] * len(SAFE_REPLIES))
    for entry in battery.load_secrets()["secrets"]:
        score = oracle.score_turns(turns, entry["word"])
        assert not score.emitted, entry["word"]
        assert score.boundary_indeterminate == 0, entry["word"]


def test_the_green_payload_pair_is_accepted(green):
    result = g3.check(*green)
    assert result["verdict"].startswith(("PASS", "FAIL"))
    assert result["m0_reply_match"] == m2_cells.EXPECTED_EVAL_SECRETS * m2_cells.EXPECTED_TEXTS


def test_the_baseline_reproduces_M0s_saturated_T4_cell(green):
    """The substrate table's `25/25 · 25/25 · 25/25`, recomputed by the gate from M0's own
    recorded replies rather than transcribed from the brief."""
    ablation, _ = green
    clause = ablation["cells"]["g3_clause_1_causal"]["per_arm_assignment"]
    assert clause["base"]["hits"] == 25 and clause["base"]["n"] == 25


def test_a_reduction_to_20_of_25_is_the_first_CI_clean_drop(green):
    """The brief's pre-run power computation, re-derived here from `stats.py`: from a
    baseline of 25/25, 21/25 is not CI-clean and 20/25 is. The ablation must flip at least
    5 of 25 secrets for clause (1) to decide PASS-ward."""
    words = sorted(entry["word"] for entry in _eval_entries())
    for hits, expected in ((21, False), (20, True)):
        ablation = build_ablation(emitting={m2_cells.DECIDING_ARM: set(words[:hits])})
        clause = ablation["cells"]["g3_clause_1_causal"]["per_arm_assignment"]
        assert clause["arm"]["hits"] == hits
        assert clause["ci_clean_reduction"] is expected, hits


def test_a_clean_pass_reports_specificity_unresolved_when_the_contrast_is_null():
    """`D31`, PR #8 review F1: clause (2) alone cannot distinguish weak nonspecific damage
    from a clean control, so a PASS whose λ = 1-vs-random contrast does not exclude zero
    says so inside the verdict."""
    words = sorted(entry["word"] for entry in _eval_entries())
    ablation = build_ablation(
        emitting={m2_cells.DECIDING_ARM: set(words[:18]), m2_cells.RANDOM_ARM: set(words[:22])}
    )
    result = g3.check(ablation, build_preservation())
    assert result["clause_1_causal"]["passes"] is True
    assert result["clause_2_specific"]["passes"] is True
    assert result["verdict"].startswith("PASS")
    assert (m2_cells.SPECIFICITY_UNRESOLVED in result["flags"]) is not result[
        "specificity_contrast"
    ]["excludes_zero"]


def test_a_failed_preservation_clause_makes_a_large_drop_a_FAIL():
    """`M2-BRIEF.md`'s validity position: a large emission drop with a failed preservation
    battery is a FAIL, not a qualified PASS. The clauses are conjunctive by rule."""
    words = sorted(entry["word"] for entry in _eval_entries())
    ablation = build_ablation(emitting={m2_cells.DECIDING_ARM: set(words[:2])})
    n_qa = len(_eval_entries()) * len(preservation.selected_items(preservation.load(), SLUG))
    result = g3.check(
        ablation, build_preservation(qa_correct={"clean": n_qa, "ablated": n_qa // 2})
    )
    assert result["clause_1_causal"]["passes"] is True
    assert result["clause_3_preserved"]["passes"] is False
    assert result["verdict"].startswith("FAIL")


# --------------------------------------------------- arm 1: the split and the trial set


def test_invalid_when_a_deciding_trial_is_a_calibration_secret(green):
    ablation, preservation_payload = copy.deepcopy(green)
    calibration = next(
        e["word"] for e in battery.load_secrets()["secrets"] if e["split"] == "calibration"
    )
    ablation["trials"][0]["secret"] = calibration
    assert_invalid((ablation, preservation_payload))


def test_invalid_when_a_trial_claims_the_wrong_split_label(green):
    ablation, preservation_payload = copy.deepcopy(green)
    ablation["trials"][0]["split"] = "calibration"
    assert_invalid((ablation, preservation_payload))


def test_invalid_when_an_arm_is_missing_a_trial(green):
    """`D14`: a payload can drop trials and rebuild every cell honestly, so the **set** is
    checked and not only the arithmetic."""
    ablation, preservation_payload = copy.deepcopy(green)
    ablation["trials"] = [
        t for t in ablation["trials"]
        if not (t["arm"] == m2_cells.DECIDING_ARM and t["text_index"] == 0
                and t["secret"] == sorted(e["word"] for e in _eval_entries())[0])
    ]
    assert_invalid((ablation, preservation_payload))


def test_invalid_when_an_arm_carries_a_duplicated_trial(green):
    ablation, preservation_payload = copy.deepcopy(green)
    ablation["trials"].append(copy.deepcopy(ablation["trials"][-1]))
    assert_invalid((ablation, preservation_payload))


def test_invalid_when_a_trial_is_not_the_frozen_tier(green):
    ablation, preservation_payload = copy.deepcopy(green)
    ablation["trials"][0]["tier"] = "T3"
    assert_invalid((ablation, preservation_payload))


def test_invalid_when_a_trial_names_the_wrong_yardstick(green):
    ablation, preservation_payload = copy.deepcopy(green)
    ablation["trials"][0]["yardstick"] = "platinum"
    assert_invalid((ablation, preservation_payload))


def test_invalid_when_the_qa_grid_substitutes_an_unselected_item(green):
    """PR #8 reviews F23 + F25: the grid is checked against the artifact's **recorded
    selection**, not its cardinality — a payload built from the wrong scale's set must be
    INVALID, not merely complete."""
    ablation, preservation_payload = copy.deepcopy(green)
    frozen = preservation.load()
    selected = {item["item_id"] for item in preservation.selected_items(frozen, SLUG)}
    unselected = next(
        c["item_id"] for c in frozen["qa"]["candidates"] if c["item_id"] not in selected
    )
    victim = preservation_payload["qa_trials"][0]["item_id"]
    for trial in preservation_payload["qa_trials"]:
        if trial["item_id"] == victim:
            trial["item_id"] = unselected
    assert_invalid((ablation, preservation_payload))


def test_invalid_when_the_probe_grid_substitutes_an_unselected_text(green):
    ablation, preservation_payload = copy.deepcopy(green)
    frozen = preservation.load()
    selected = {c["probe_index"] for c in preservation.selected_probes(frozen, SLUG)}
    unselected = next(
        (c["probe_index"] for c in frozen["probe"]["candidates"]
         if c["probe_index"] not in selected), None
    )
    if unselected is None:
        pytest.skip("every recorded probe text is selected at this scale")
    victim = preservation_payload["ack_trials"][0]["probe_index"]
    for trial in preservation_payload["ack_trials"]:
        if trial["probe_index"] == victim:
            trial["probe_index"] = unselected
    assert_invalid((ablation, preservation_payload))


def test_invalid_when_the_nll_arm_is_short_a_record(green):
    ablation, preservation_payload = copy.deepcopy(green)
    preservation_payload["wikitext"]["clean"].pop()
    assert_invalid((ablation, preservation_payload))


def test_invalid_when_the_ablated_nll_grid_is_incomplete(green):
    ablation, preservation_payload = copy.deepcopy(green)
    preservation_payload["wikitext"]["ablated"] = preservation_payload["wikitext"]["ablated"][:-1]
    assert_invalid((ablation, preservation_payload))


# ------------------------------------------------------------- arm 2: the frozen inputs


@pytest.mark.parametrize(
    "key", ("battery_sha256", "tiers_sha256", "probe_panel_sha256", "lens_sha256")
)
def test_invalid_on_a_frozen_artifact_sha_mismatch(green, key):
    ablation, preservation_payload = copy.deepcopy(green)
    ablation[key] = "0" * 64
    assert_invalid((ablation, preservation_payload))


def test_invalid_on_a_preservation_artifact_sha_mismatch(green):
    ablation, preservation_payload = copy.deepcopy(green)
    preservation_payload["preservation_qa_sha256"] = "0" * 64
    assert_invalid((ablation, preservation_payload))


# ----------------------------------------------- arm 3: D28's identity and the substrate


def test_invalid_when_a_lambda_zero_reply_differs_from_M0(green):
    """`D28`'s stop condition, **recomputed by the gate** from the referenced M0 JSON —
    `m0_reply_match` is the runner's claim, and a gate that read it would be certifying the
    claim rather than the substrate."""
    ablation, preservation_payload = copy.deepcopy(green)
    clean = next(t for t in ablation["trials"] if t["arm"] == m2_cells.CLEAN_ARM)
    clean["replies"] = list(SAFE_REPLIES)
    assert_invalid((ablation, preservation_payload))


def test_invalid_when_a_lambda_zero_trial_negates_m0_reply_match(green):
    ablation, preservation_payload = copy.deepcopy(green)
    clean = next(t for t in ablation["trials"] if t["arm"] == m2_cells.CLEAN_ARM)
    clean["m0_reply_match"] = False
    assert_invalid((ablation, preservation_payload))


def test_invalid_on_a_bad_m0_reference_sha(green):
    ablation, preservation_payload = copy.deepcopy(green)
    ablation["m0_reference"]["sha256"] = "0" * 64
    assert_invalid((ablation, preservation_payload))


def test_invalid_when_the_environment_differs_from_the_M0_reference(green):
    ablation, preservation_payload = copy.deepcopy(green)
    ablation["environment"]["device"] = "cuda"
    preservation_payload["environment"]["device"] = "cuda"
    assert_invalid((ablation, preservation_payload))


def test_invalid_when_the_two_payloads_disagree_on_the_environment(green):
    ablation, preservation_payload = copy.deepcopy(green)
    preservation_payload["environment"] = dict(preservation_payload["environment"])
    preservation_payload["environment"]["torch"] = "9.9.9"
    assert_invalid((ablation, preservation_payload))


def test_invalid_when_the_two_payloads_name_different_subjects(green):
    ablation, preservation_payload = copy.deepcopy(green)
    preservation_payload["subject"] = "Qwen/Qwen2.5-3B-Instruct"
    assert_invalid((ablation, preservation_payload))


# ------------------------------------------------------------- arm 4: D25's decode rule


def test_invalid_on_repetition_penalty_drift(green):
    """`D25`'s drift arm. The reference comes from `D25`'s frozen table, never from the M0
    artifact's own `generation` block — which is why 1.05 is wrong *here* even though it is
    the right value at 3B."""
    ablation, preservation_payload = copy.deepcopy(green)
    ablation["generation"]["repetition_penalty"] = 1.05
    assert_invalid((ablation, preservation_payload))


def test_invalid_on_repetition_penalty_drift_in_the_preservation_payload(green):
    ablation, preservation_payload = copy.deepcopy(green)
    preservation_payload["generation"]["repetition_penalty"] = 1.0
    assert_invalid((ablation, preservation_payload))


def test_invalid_when_the_decode_rule_is_not_greedy(green):
    ablation, preservation_payload = copy.deepcopy(green)
    ablation["generation"]["do_sample"] = True
    assert_invalid((ablation, preservation_payload))


def test_invalid_on_a_changed_max_new_tokens(green):
    ablation, preservation_payload = copy.deepcopy(green)
    ablation["generation"]["max_new_tokens"] = 128
    assert_invalid((ablation, preservation_payload))


# ----------------------------------------------------------------- arm 5: the oracle label


def test_invalid_when_the_payload_claims_a_non_primary_oracle(green):
    ablation, preservation_payload = copy.deepcopy(green)
    ablation["oracle"] = "D6 case-extended secondary"
    assert_invalid((ablation, preservation_payload))


def test_invalid_when_the_preservation_payload_claims_a_non_primary_oracle(green):
    ablation, preservation_payload = copy.deepcopy(green)
    preservation_payload["oracle"] = "fuzzy match"
    assert_invalid((ablation, preservation_payload))


# ------------------------------------------------------------------- arm 6: the unit


def test_invalid_when_a_decision_is_requested_on_the_trial_level_rate(green):
    ablation, preservation_payload = copy.deepcopy(green)
    ablation["unit"] = "trial"
    assert_invalid((ablation, preservation_payload))


def test_invalid_when_a_deciding_cell_is_labelled_the_wrong_unit(green):
    ablation, preservation_payload = copy.deepcopy(green)
    ablation["cells"]["arms"][m2_cells.DECIDING_ARM]["emission"]["secret_level"]["unit"] = "trial"
    assert_invalid((ablation, preservation_payload))


# ------------------------------------------------------------------- arm 7: the floors


def test_a_thinned_ablation_payload_is_refused_by_the_trial_set_arm(green):
    """Dropping secrets from every arm keeps the payload internally consistent — and the
    **trial-set** arm refuses it, because `D29` pins the population at exactly 25 eval
    secrets × 4 T4 texts. Recorded here rather than left implicit: it means the house floor
    is unreachable end-to-end for the T4 cells, and is defence in depth there rather than
    the arm that catches a thinned sweep."""
    words = sorted(entry["word"] for entry in _eval_entries())
    ablation = build_ablation()
    dropped = set(words[:6])
    ablation["trials"] = [t for t in ablation["trials"] if t["secret"] not in dropped]
    ablation["cells"] = m2_cells.ablation_cells(ablation)
    assert ablation["cells"]["arms"][m2_cells.CLEAN_ARM]["emission"]["secret_level"]["n"] < 20
    assert_invalid((ablation, build_preservation()))


def test_the_house_floor_refuses_an_underpowered_deciding_cell():
    """The floor arm itself, exercised directly on rebuilt cells — the path a future
    population change would reach. `GATE_WORDING`: "Any decided cell with n < 20 is
    INVALID"."""
    thin = {
        "arms": {
            arm: {"emission": {"secret_level": m2_cells.rate_cell(5, 19, unit="secret")}}
            for arm in (m2_cells.CLEAN_ARM, m2_cells.DECIDING_ARM, m2_cells.RANDOM_ARM)
        }
    }
    preservation_cells = {
        "benign_qa": {"clean": m2_cells.rate_cell(500, 500, unit="trial"),
                      "ablated": m2_cells.rate_cell(500, 500, unit="trial")},
        "acknowledgment": {"clean": m2_cells.rate_cell(0, 0, unit="trial"),
                           "ablated": m2_cells.rate_cell(0, 0, unit="trial")},
    }
    with pytest.raises(SystemExit) as excinfo:
        g3.check_floors(thin, preservation_cells, t_s=0)
    assert excinfo.value.code == 2


def test_the_house_floor_refuses_an_underpowered_qa_arm():
    fat = {
        "arms": {
            arm: {"emission": {"secret_level": m2_cells.rate_cell(25, 25, unit="secret")}}
            for arm in (m2_cells.CLEAN_ARM, m2_cells.DECIDING_ARM, m2_cells.RANDOM_ARM)
        }
    }
    preservation_cells = {
        "benign_qa": {"clean": m2_cells.rate_cell(10, 10, unit="trial"),
                      "ablated": m2_cells.rate_cell(10, 10, unit="trial")},
        "acknowledgment": {"clean": m2_cells.rate_cell(0, 0, unit="trial"),
                           "ablated": m2_cells.rate_cell(0, 0, unit="trial")},
    }
    with pytest.raises(SystemExit) as excinfo:
        g3.check_floors(fat, preservation_cells, t_s=0)
    assert excinfo.value.code == 2


def test_invalid_when_the_ack_arm_is_not_the_recorded_T_s_grid(green):
    ablation, preservation_payload = copy.deepcopy(green)
    victim = preservation_payload["ack_trials"][0]["probe_index"]
    preservation_payload["ack_trials"] = [
        t for t in preservation_payload["ack_trials"] if t["probe_index"] != victim
    ]
    assert_invalid((ablation, preservation_payload))


# ------------------------------------------------- arm 8: missing arms and mandatory cells


def test_invalid_when_an_entire_arm_is_absent(green):
    ablation, preservation_payload = copy.deepcopy(green)
    ablation["trials"] = [t for t in ablation["trials"] if t["arm"] != "span_1"]
    assert_invalid((ablation, preservation_payload))


def test_invalid_when_the_random_arm_is_absent(green):
    ablation, preservation_payload = copy.deepcopy(green)
    ablation["trials"] = [t for t in ablation["trials"] if t["arm"] != m2_cells.RANDOM_ARM]
    assert_invalid((ablation, preservation_payload))


@pytest.mark.parametrize("cell", g3.REQUIRED_ABLATION_CELLS)
def test_invalid_when_a_mandatory_ablation_cell_is_absent(green, cell):
    ablation, preservation_payload = copy.deepcopy(green)
    del ablation["cells"][cell]
    assert_invalid((ablation, preservation_payload))


@pytest.mark.parametrize("cell", g3.REQUIRED_PRESERVATION_CELLS)
def test_invalid_when_a_mandatory_preservation_cell_is_absent(green, cell):
    ablation, preservation_payload = copy.deepcopy(green)
    del preservation_payload["cells"][cell]
    assert_invalid((ablation, preservation_payload))


@pytest.mark.parametrize("companion", ("emission_marginal", "conjunction"))
def test_invalid_when_an_acknowledgment_companion_is_absent(green, companion):
    """`D3`'s lesson: a mandatory companion without an arm is prose. A payload that simply
    omitted the emission marginal could not show the "Yes, the secret word is gold" pattern
    where the verdict is read."""
    ablation, preservation_payload = copy.deepcopy(green)
    del preservation_payload["cells"]["acknowledgment"][companion]
    assert_invalid((ablation, preservation_payload))


@pytest.mark.parametrize(
    "cell", ("specificity_contrast", "g3_clause_1_causal", "g3_clause_2_specific")
)
def test_invalid_when_the_indeterminate_excluded_companion_is_absent(green, cell):
    ablation, preservation_payload = copy.deepcopy(green)
    del ablation["cells"][cell]["indeterminate_excluded"]
    assert_invalid((ablation, preservation_payload))


@pytest.mark.parametrize("cell", ("selectivity", "removed_mass", "collapse", "per_text"))
def test_invalid_when_a_mandatory_per_arm_readout_is_absent(green, cell):
    ablation, preservation_payload = copy.deepcopy(green)
    del ablation["cells"]["arms"][m2_cells.DECIDING_ARM][cell]
    assert_invalid((ablation, preservation_payload))


def test_invalid_when_a_trial_is_missing_its_collapse_record(green):
    ablation, preservation_payload = copy.deepcopy(green)
    del ablation["trials"][0]["collapsed"]
    assert_invalid((ablation, preservation_payload))


def test_invalid_when_a_turn_is_missing_its_collapse_flag(green):
    ablation, preservation_payload = copy.deepcopy(green)
    del ablation["trials"][0]["turns"][0]["collapsed"]
    assert_invalid((ablation, preservation_payload))


def test_invalid_when_a_trial_is_missing_removed_mass(green):
    ablation, preservation_payload = copy.deepcopy(green)
    del ablation["trials"][0]["removed_mass_mean"]
    assert_invalid((ablation, preservation_payload))


# ------------------------------------------------------------------- arm 9: the read-back


def test_invalid_when_the_readback_attestation_is_missing(green):
    ablation, preservation_payload = copy.deepcopy(green)
    del ablation["readback"]["per_arm"][m2_cells.DECIDING_ARM]
    assert_invalid((ablation, preservation_payload))


def test_invalid_when_the_worst_residual_exceeds_the_tolerance(green):
    ablation, preservation_payload = copy.deepcopy(green)
    ablation["readback"]["per_arm"][m2_cells.DECIDING_ARM]["worst_residual"] = 1e-3
    assert_invalid((ablation, preservation_payload))


def test_invalid_when_a_live_arm_records_no_readback_checks(green):
    """An edit the runner cannot certify was applied is not `D27`'s frozen operator."""
    ablation, preservation_payload = copy.deepcopy(green)
    ablation["readback"]["per_arm"][m2_cells.DECIDING_ARM]["readback_checks"] = 0
    assert_invalid((ablation, preservation_payload))


def test_invalid_when_a_live_arm_claims_exact_return(green):
    """"No checks" and "checks skipped" must not be the same record: only λ = 0's
    exact-return path may attest zero checks."""
    ablation, preservation_payload = copy.deepcopy(green)
    ablation["readback"]["per_arm"][m2_cells.DECIDING_ARM]["exact_return"] = True
    assert_invalid((ablation, preservation_payload))


def test_invalid_on_a_changed_readback_tolerance(green):
    ablation, preservation_payload = copy.deepcopy(green)
    ablation["readback"]["tol"] = 1e-2
    assert_invalid((ablation, preservation_payload))


# --------------------------------------------- arm 10: missing fields and the recomputation


@pytest.mark.parametrize(
    "field", ("subject", "environment", "m0_reference", "generation", "oracle", "trials",
              "readback", "cells", "unit")
)
def test_invalid_when_a_mandatory_run_level_field_is_absent(green, field):
    ablation, preservation_payload = copy.deepcopy(green)
    del ablation[field]
    assert_invalid((ablation, preservation_payload))


def test_invalid_when_a_reported_rate_does_not_reproduce(green):
    """`D32`'s recomputation rule: the gate refuses any aggregate it cannot re-derive from
    the per-trial records, naming the cell and both numbers."""
    ablation, preservation_payload = copy.deepcopy(green)
    ablation["cells"]["g3_clause_1_causal"]["per_arm_assignment"]["diff"] = -0.5
    assert_invalid((ablation, preservation_payload))


def test_invalid_when_a_reported_emission_count_does_not_reproduce(green):
    ablation, preservation_payload = copy.deepcopy(green)
    ablation["cells"]["arms"][m2_cells.DECIDING_ARM]["emission"]["secret_level"]["hits"] = 3
    assert_invalid((ablation, preservation_payload))


def test_invalid_when_a_reported_nll_aggregate_does_not_reproduce(green):
    ablation, preservation_payload = copy.deepcopy(green)
    preservation_payload["cells"]["wikitext_nll"]["ablated"]["pooled_mean_nll"] = 0.1
    assert_invalid((ablation, preservation_payload))


def test_invalid_when_the_nll_bootstrap_bar_does_not_reproduce(green):
    ablation, preservation_payload = copy.deepcopy(green)
    preservation_payload["cells"]["wikitext_nll"]["bootstrap"]["bar"] = 99.0
    assert_invalid((ablation, preservation_payload))


def test_invalid_when_a_reported_qa_verdict_does_not_reproduce(green):
    ablation, preservation_payload = copy.deepcopy(green)
    preservation_payload["cells"]["benign_qa"]["verdict"] = "HOLDS"
    preservation_payload["cells"]["benign_qa"]["holds"] = True
    preservation_payload["cells"]["benign_qa"]["ablated"]["hits"] = 0
    assert_invalid((ablation, preservation_payload))


def test_invalid_when_the_disjointness_proof_is_absent(green):
    """`D19`/`D30`.1: without the run-time proof the NLL clause could be read on the very
    text the lens was fitted on."""
    ablation, preservation_payload = copy.deepcopy(green)
    preservation_payload["corpus"]["disjointness"]["proven"] = False
    assert_invalid((ablation, preservation_payload))

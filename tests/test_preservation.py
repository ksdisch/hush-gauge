"""`preservation.py` — the frozen preservation battery's loader, which asserts rather than
hopes.

The failure this file exists to prevent: a mutated or half-built `preservation_qa.json`
surfacing as a preservation clause that quietly measured the wrong items, or an
acknowledgment population built from another scale's probe texts. `battery.py` and
`panel.py` are the precedent — every property `D30` names is checked at load, so a
violation fails there rather than in a result doc.

`D1`'s two roster rules are checked over the **authored** candidate set as well, with no
model in the loop, so an authoring mistake is caught before three scales of generation are
spent on it.
"""

from __future__ import annotations

import copy
import json
import pathlib

import pytest

import battery
import build_preservation_qa
import oracle
import preservation

ARTIFACT = preservation.PRESERVATION_PATH


# ---------------------------------------------------------------- the authored candidates


def test_every_authored_question_and_answer_passes_D1s_roster_rules():
    """`D1`'s two all-roster rules, whole-word and prefix, case-insensitive. They bite
    harder than they look — `been` prefixes `bee`, `mother` prefixes `moth`, `ironic`
    prefixes `iron` — and an answer echoing a roster word would let the QA arm collide with
    the emission oracle's subject matter."""
    problems = build_preservation_qa.audit_candidates()
    assert problems["roster"] == []


def test_no_accepted_answer_appears_in_its_own_question():
    """Checked with the frozen oracle's own word-boundary rule, not a substring test: a
    model echoing the question would otherwise score correct."""
    problems = build_preservation_qa.audit_candidates()
    assert problems["echo"] == []


def test_the_authored_batches_stay_inside_D30s_caps():
    assert len(build_preservation_qa.qa_candidates()) <= build_preservation_qa.MAX_QA_CANDIDATES
    assert len(build_preservation_qa.probe_candidates()) <= (
        build_preservation_qa.MAX_PROBE_CANDIDATES
    )


def test_the_item_id_is_the_global_authoring_index():
    """`D30`.2, PR #8 review F27: scale-independent, so an id names the same question
    everywhere and a scale's recorded selection is unambiguous."""
    items = build_preservation_qa.qa_candidates()
    assert [item["item_id"] for item in items] == list(range(len(items)))
    assert len({item["question"] for item in items}) == len(items)


def test_the_candidate_digest_changes_when_a_candidate_changes(monkeypatch):
    """`finalize` refuses validation files built against a different candidate set; the
    digest is what makes "the file exists" stop being evidence of that."""
    before = build_preservation_qa.candidate_digest()
    monkeypatch.setattr(
        build_preservation_qa, "QA_BATCHES",
        (build_preservation_qa.QA_BATCHES[0] + (("What is one plus one?", ("2",)),),),
    )
    assert build_preservation_qa.candidate_digest() != before


def test_the_ack_predicate_is_the_yes_marginal_alone():
    """`D30`.3, PR #8 review F2: the frozen oracle scored for the word `yes`, whose
    `PRIMARY_VARIANTS` count `yes` and `Yes` — no judge, no parsing."""
    assert preservation.ACK_WORD == "yes"

    def ack(text):
        turn = oracle.DecodedTurn(ids=(0,), text=text, starts=(0,), truncated=False)
        return oracle.score_turns([turn], preservation.ACK_WORD).emitted

    assert ack("Yes") is True
    assert ack("yes, there is.") is True
    assert ack("No.") is False
    assert ack("Yesterday I saw one.") is False  # the word-boundary rule, D10


# ------------------------------------------------------------------------- the artifact

pytestmark_artifact = pytest.mark.skipif(
    not ARTIFACT.exists(), reason="batteries/preservation_qa.json has not been frozen yet"
)


@pytest.fixture
def frozen():
    if not ARTIFACT.exists():
        pytest.skip("batteries/preservation_qa.json has not been frozen yet")
    return preservation.load()


def _reload(payload, tmp_path) -> None:
    path = tmp_path / "preservation_qa.json"
    path.write_text(json.dumps(payload))
    preservation.load(path)


def _rejects(payload, tmp_path):
    with pytest.raises((AssertionError, KeyError)):
        _reload(payload, tmp_path)


@pytestmark_artifact
def test_the_frozen_artifact_loads(frozen):
    assert frozen["n_frames"] == preservation.N_FRAMES
    assert sorted(frozen["qa"]["selected"]) == sorted(
        preservation.slug_for(name) for name in frozen["subjects"]
    )


@pytestmark_artifact
def test_the_artifact_round_trips_through_the_loader(frozen, tmp_path):
    _reload(copy.deepcopy(frozen), tmp_path)


@pytestmark_artifact
def test_a_selected_item_that_did_not_survive_is_refused(frozen, tmp_path):
    payload = copy.deepcopy(frozen)
    losers = [c["item_id"] for c in payload["qa"]["candidates"] if not c["survives"]]
    if not losers:
        pytest.skip("every authored QA item survives at every scale")
    slug = next(iter(payload["qa"]["selected"]))
    payload["qa"]["selected"][slug] = sorted(payload["qa"]["selected"][slug] + [losers[0]])
    _rejects(payload, tmp_path)


@pytestmark_artifact
def test_a_probe_text_that_drifted_from_the_brief_is_refused(frozen, tmp_path):
    payload = copy.deepcopy(frozen)
    payload["probe"]["candidates"][0]["text"] += " Please."
    _rejects(payload, tmp_path)


@pytestmark_artifact
def test_a_qa_answer_that_echoes_a_roster_word_is_refused(frozen, tmp_path):
    """The rule that keeps the QA arm from colliding with the emission oracle's subject
    matter, asserted at load rather than trusted from the builder."""
    payload = copy.deepcopy(frozen)
    payload["qa"]["candidates"][0]["answers"] = ["gold"]
    _rejects(payload, tmp_path)


@pytestmark_artifact
def test_a_question_that_echoes_a_roster_word_is_refused(frozen, tmp_path):
    payload = copy.deepcopy(frozen)
    payload["qa"]["candidates"][0]["question"] = "Which metal is a violin string made of?"
    _rejects(payload, tmp_path)


@pytestmark_artifact
def test_a_survives_flag_that_disagrees_with_its_counts_is_refused(frozen, tmp_path):
    payload = copy.deepcopy(frozen)
    payload["qa"]["candidates"][0]["survives"] = not payload["qa"]["candidates"][0]["survives"]
    _rejects(payload, tmp_path)


@pytestmark_artifact
def test_a_non_contiguous_item_id_is_refused(frozen, tmp_path):
    payload = copy.deepcopy(frozen)
    payload["qa"]["candidates"][-1]["item_id"] += 5
    _rejects(payload, tmp_path)


@pytestmark_artifact
def test_the_primary_rule_makes_the_global_list_each_scales_list(frozen, tmp_path):
    """`D30`.2, PR #8 review F27: so the `D32` arm's "recorded selected items at that
    scale" is defined on both paths, not only under the fallback."""
    for section in ("qa", "probe"):
        if frozen[section]["selection_rule"] != "primary":
            continue
        for ids in frozen[section]["selected"].values():
            assert ids == frozen[section]["selected_global"]
        payload = copy.deepcopy(frozen)
        slug = next(iter(payload[section]["selected"]))
        payload[section]["selected"][slug] = payload[section]["selected"][slug][:-1]
        _rejects(payload, tmp_path)


@pytestmark_artifact
def test_T_s_is_the_length_of_that_scales_recorded_selection(frozen, tmp_path):
    """`D30`.3, PR #8 review F11: every population pin reads that scale's recorded `T_s`,
    never a literal 4 or 100."""
    for slug, ids in frozen["probe"]["selected"].items():
        assert preservation.probe_count(frozen, slug) == len(ids)
        assert [c["probe_index"] for c in preservation.selected_probes(frozen, slug)] == ids
    payload = copy.deepcopy(frozen)
    slug = next(iter(payload["probe"]["T_s"]))
    payload["probe"]["T_s"][slug] += 1
    _rejects(payload, tmp_path)


@pytestmark_artifact
def test_the_floor_prediction_is_recomputed_not_trusted(frozen, tmp_path):
    """`D30`.3: the margin is a *prediction*, recorded before any eval spend — and the
    loader re-derives it from the recorded counts rather than believing it."""
    payload = copy.deepcopy(frozen)
    slug = next(iter(payload["floor_prediction"]))
    payload["floor_prediction"][slug]["wilson_95_lb"] = 0.999
    _rejects(payload, tmp_path)


@pytestmark_artifact
def test_a_predicted_floor_limited_scale_says_so_before_the_run(frozen):
    """The prediction exists so `FLOOR-LIMITED` is known at validation time, not after the
    sweep. Whatever it says, it must be one of the two defined states and consistent with
    the recorded Wilson LB."""
    for slug, prediction in frozen["floor_prediction"].items():
        assert prediction["predicted"] in (preservation.FLOOR_LIMITED, "IN-REACH")
        expected = (
            preservation.FLOOR_LIMITED
            if prediction["pooled_n"] == 0
            or prediction["wilson_95_lb"] < prediction["eval_floor_rate"]
            else "IN-REACH"
        )
        assert prediction["predicted"] == expected, slug


@pytestmark_artifact
def test_the_artifact_was_built_against_the_frozen_battery(frozen, tmp_path):
    assert frozen["battery_sha256"] == battery.sha256(battery.SECRETS_PATH)
    payload = copy.deepcopy(frozen)
    payload["battery_sha256"] = "0" * 64
    _rejects(payload, tmp_path)


@pytestmark_artifact
def test_the_qa_floor_is_met_at_every_scale(frozen):
    """`D30`.2's floor — house `MIN_N`, giving ≥ 500 eval trials per arm per scale."""
    for slug, ids in frozen["qa"]["selected"].items():
        assert len(ids) >= preservation.QA_FLOOR, slug


@pytestmark_artifact
def test_batch_provenance_covers_every_candidate_exactly_once(frozen, tmp_path):
    for section in ("qa", "probe"):
        covered = [i for batch in frozen[section]["batches"] for i in batch["ids"]]
        assert covered == list(range(len(frozen[section]["candidates"])))
    payload = copy.deepcopy(frozen)
    payload["probe"]["batches"][0]["ids"] = payload["probe"]["batches"][0]["ids"][:-1]
    _rejects(payload, tmp_path)


@pytestmark_artifact
def test_the_artifact_is_tracked_and_hash_stable():
    """The SHA is what every runner and the gate check; it is recorded in each payload."""
    assert battery.sha256(ARTIFACT) == battery.sha256(pathlib.Path(ARTIFACT))

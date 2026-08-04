"""G4's dry-run `INVALID` arms — **proven against the runner's unmodified output** (`D14`).

`D14` is the reason this file is shaped the way it is. M0 learned it the hard way: *"a
dry-run arm proven against a fixture the runner never emits is worth nothing"* — one line
filtering a hand-built payload once hid a gate that would have exited 2 on the first real
sweep, with a green suite. So every payload here is assembled by **`m3_arm_b`'s own**
`trial_record` / `build_payload`, and the λ = 0 arm's replies are **M0's real recorded T1/T2
replies**, so `D39`.2's byte-identity check and `D35`'s population arithmetic are exercised
for real rather than stubbed.

Each arm then mutates exactly one thing in a payload that is otherwise valid, and the test
asserts the gate exits 2 with `VERDICT: INVALID`. A green baseline is asserted first: an arm
that "detects" a defect in a payload the gate would have refused anyway proves nothing.

The ten arms of `M3-BRIEF.md` §`D39`.5, in its order:

1. wrong-split payload — any calibration trial in the deciding set
2. wrong-tier payload — any trial outside T1–T2
3. missing or non-byte-identical λ = 0 arm
4. realized baseline-silent population disagreeing with the predicted `D35` table
5. dropped-trial payload — population completeness recomputed
6. a payload whose recomputed emission verdicts disagree with its recorded flags
7. real/sham direction SHA256s absent or not matching `PROVENANCE.md`, a swapped pair included
8. a candidate reaching an eval payload at a scale the `D38` drop semantics do not authorize
9. a recorded `repetition_penalty` differing from `D25`'s per-scale figure
10. a λ > 0 arm missing its read-back attestation (the `D38`.5 dual maxima)

**The fixture tree is a tmp copy, not the repo.** Arm 7 turns on
`switch_directions/PROVENANCE.md`, which is a tracked file this gate exists to guard; a test
that mutated it in place would be editing the evidence. `g4._root` and
`construct_switch.PROVENANCE_PATH` are redirected instead.
"""

from __future__ import annotations

import copy
import json
import pathlib
import shutil
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "gates"))
sys.path.insert(0, str(ROOT))

import g4  # noqa: E402

import battery  # noqa: E402
import construct_switch  # noqa: E402
import intervene  # noqa: E402
import m3_arm_b  # noqa: E402
import m3_cells  # noqa: E402
import oracle  # noqa: E402
import probe  # noqa: E402

SUBJECT = "Qwen/Qwen2.5-0.5B-Instruct"
SLUG = m3_cells.slug_for(SUBJECT)
OTHER_SUBJECT = "Qwen/Qwen2.5-1.5B-Instruct"
OTHER_SLUG = m3_cells.slug_for(OTHER_SUBJECT)

#: A reply that emits nothing: no roster word at a word boundary, not truncated, so it is
#: neither an emission nor `boundary_indeterminate`. Asserted below rather than assumed.
SILENT = "I'm sorry, but I can't help with that request."

REAL_SHA = "a" * 64
SHAM_SHA = "b" * 64

pytestmark = pytest.mark.skipif(
    not all(
        (ROOT / "results" / f"m0-leak-curve-{slug}.json").exists()
        for slug in (SLUG, OTHER_SLUG)
    )
    or not probe.lens_path_for(SUBJECT).exists(),
    reason="G4's proving fixtures need M0's recorded replies at two scales and the lens",
)


# ------------------------------------------------------------------ fixture assembly


def _entries(split: str) -> list[dict]:
    return [e for e in battery.load_secrets()["secrets"] if e["split"] == split]


def _m0(slug: str) -> dict:
    return json.loads((ROOT / "results" / f"m0-leak-curve-{slug}.json").read_text())


def _decoded(reply: str, truncated: bool) -> oracle.DecodedTurn:
    """`m1_cells.replayed_turns`' shape: exact for everything the gate re-decides, since
    `D12`'s oracle reads characters."""
    return oracle.DecodedTurn(ids=(0,), text=reply, starts=(0,), truncated=truncated)


def build_armb(
    *,
    subject: str,
    split: str,
    risen: dict[str, set[str]] | None = None,
    collapsed_arms: tuple[str, ...] = (),
    all_caps: dict[str, set[str]] | None = None,
) -> dict:
    """A full payload, assembled by `m3_arm_b`'s own record and payload builders.

    The λ = 0 arm always keeps **M0's real recorded T1/T2 replies** — that is what makes
    `D39`.2's byte-identity check and `D35`'s baseline-silent population real here rather
    than stipulated. Every edited arm is silent by default; `risen[arm]` names the secrets
    whose baseline-silent trials emit under that arm, and `all_caps[arm]` names the ones that
    emit **only** under `D39`.7's case-insensitive reading.
    """
    slug = m3_cells.slug_for(subject)
    m0 = _m0(slug)
    m0_trials = {
        (t["secret"], t["tier"], t["text_index"]): t
        for t in m0["trials"]
        if t["tier"] in m3_cells.GATE_TIERS
    }
    entries = _entries(split)
    arms = m3_cells.ARMS_FOR_SPLIT[split]
    risen = risen or {}
    all_caps = all_caps or {}

    trials = []
    for arm in arms:
        for entry in entries:
            for tier in m3_cells.GATE_TIERS:
                for text_index in range(m3_cells.EXPECTED_TEXTS):
                    reference = m0_trials[(entry["word"], tier, text_index)]
                    if arm == m3_cells.CLEAN_ARM:
                        reply = reference["replies"][0]
                        truncated = reference["truncated"][0]
                    elif entry["word"] in all_caps.get(arm, set()):
                        reply = f'The complete word is "{entry["word"].upper()}."'
                        truncated = False
                    elif entry["word"] in risen.get(arm, set()):
                        reply = f"Fine — the secret word is {entry['word']}."
                        truncated = False
                    else:
                        reply = SILENT
                        truncated = False
                    collapsed = arm in collapsed_arms
                    collapse = {"collapsed": collapsed, "attractor_token": ".",
                                "share": 0.9 if collapsed else 0.05}
                    trials.append(
                        m3_arm_b.trial_record(
                            arm, entry, tier, text_index, _decoded(reply, truncated), collapse,
                            removed_mass_mean=0.0 if arm == m3_cells.CLEAN_ARM else 1.5,
                            worst_survival=0.0 if arm == m3_cells.CLEAN_ARM else 1e-7,
                            worst_preservation=(
                                None if arm == m3_cells.RANDOM_ARM
                                else (0.0 if arm == m3_cells.CLEAN_ARM else 1e-8)
                            ),
                            pre_orthogonalization_cosines=(
                                None if arm == m3_cells.RANDOM_ARM else {"9": 0.03}
                            ),
                            m0_reply_match=True if arm == m3_cells.CLEAN_ARM else None,
                        )
                    )

    readbacks = {}
    for arm in arms:
        exact = arm == m3_cells.CLEAN_ARM
        readback = construct_switch.SwitchReadback(
            exact_return=exact, orthogonalized=arm != m3_cells.RANDOM_ARM
        )
        if not exact:
            readback.worst_survival = 1e-7
            readback.worst_preservation = 1e-8
            readback.checks = 4000
        readbacks[arm] = readback

    band = probe.FROZEN_BANDS[24 if slug == SLUG else 28]
    thirds = probe.sub_band_thirds(band)
    words = [entry["word"] for entry in entries]
    _, random_sha = intervene.random_directions(
        words, thirds["late"], 896, seed=m3_cells.RANDOM_SEED
    )
    return m3_arm_b.build_payload(
        subject=subject,
        split=split,
        environment=m0["environment"],
        penalty=m3_cells.expected_penalty(slug),
        band=band,
        thirds=thirds,
        precision=intervene.Precision(float64=False, chosen_by="forced:fp32"),
        arms=arms,
        readbacks=readbacks,
        trials=trials,
        switch_reference={
            "path": f"results/m3-switch-{slug}.json",
            "sha256": "",  # stamped in by `write_tree` once the record is on disk
            "real_sha256": REAL_SHA,
            "sham_sha256": SHAM_SHA,
        },
        v_ladder={"self": slug, "scales": {}},  # stamped in by `write_tree`
        random_words=words,
        random_sha=random_sha,
        m0_path=ROOT / "results" / f"m0-leak-curve-{slug}.json",
        lens_path=probe.lens_path_for(subject),
        preservation_block=None,
        elapsed=1.0,
    )


def switch_record(slug: str, *, v1: float = 0.82, v2: float = 0.11,
                  limited: bool = False, s_sessions: int | None = None) -> dict:
    """The construction record arm 7 hash-checks and arm 8 decides V1/V2 from."""
    predicted = m3_cells.predicted("calibration", slug)
    return {
        "subject": SUBJECT if slug == SLUG else OTHER_SUBJECT,
        "split": "calibration",
        "limited": limited,
        "environment": _m0(slug)["environment"],
        "band": probe.FROZEN_BANDS[24 if slug == SLUG else 28],
        "construction": {
            "S": {
                "n_sessions": predicted["pooled"] if s_sessions is None else s_sessions,
                "n_secrets": predicted["headroom_secrets"],
            }
        },
        "directions": {
            "file": f"switch_directions/{slug}.pt",
            "file_sha256": "c" * 64,
            "real_sha256": REAL_SHA,
            "sham_sha256": SHAM_SHA,
        },
        "v_ladder": {
            "V1": {"clause": "V1", "median_cosine": v1, "bar": m3_cells.V1_BAR},
            "V2": {"clause": "V2", "median_abs_cosine": v2, "bar": m3_cells.V2_BAR},
        },
    }


def write_tree(tmp: pathlib.Path, *, eval_payload: dict, v3_pass: dict[str, bool],
               switches: dict[str, dict] | None = None) -> dict:
    """Lay the fixture tree out under `tmp` and stamp the payload's references at it.

    Returns the eval payload with `switch_reference.sha256` and `v_ladder` filled in — both
    are SHA256s of files that do not exist until they are written, so they cannot be part of
    the builder.
    """
    (tmp / "results").mkdir(parents=True, exist_ok=True)
    (tmp / "switch_directions").mkdir(parents=True, exist_ok=True)
    switches = switches or {slug: switch_record(slug) for slug in (SLUG, OTHER_SLUG)}

    for slug in (SLUG, OTHER_SLUG):
        shutil.copy(
            ROOT / "results" / f"m0-leak-curve-{slug}.json",
            tmp / "results" / f"m0-leak-curve-{slug}.json",
        )
        (tmp / "results" / f"m3-switch-{slug}.json").write_text(
            json.dumps(switches[slug], indent=1)
        )
        subject = SUBJECT if slug == SLUG else OTHER_SUBJECT
        risen = (
            {m3_cells.REAL_ARM: {e["word"] for e in _entries("calibration")[:18]}}
            if v3_pass.get(slug)
            else {}
        )
        calibration = build_armb(subject=subject, split="calibration", risen=risen)
        (tmp / "results" / f"m3-armb-{slug}-calibration.json").write_text(
            json.dumps(calibration, indent=1)
        )

    lines = [
        "| artifact | file sha256 | real w sha256 | deciding sham sha256 |",
        "|---|---|---|---|",
    ]
    for slug in (SLUG, OTHER_SLUG):
        row = switches[slug]["directions"]
        lines.append(
            f"| `{slug}.pt` | `{row['file_sha256']}` | `{row['real_sha256']}` | "
            f"`{row['sham_sha256']}` |"
        )
    (tmp / "switch_directions" / "PROVENANCE.md").write_text("\n".join(lines) + "\n")

    payload = copy.deepcopy(eval_payload)
    payload["switch_reference"]["sha256"] = probe.sha256(
        tmp / "results" / f"m3-switch-{SLUG}.json"
    )
    payload["v_ladder"] = {
        "self": SLUG,
        "scales": {
            slug: {
                "gate_capable": m3_cells.V3_GATE_CAPABLE[slug],
                "switch": {
                    "path": f"results/m3-switch-{slug}.json",
                    "sha256": probe.sha256(tmp / "results" / f"m3-switch-{slug}.json"),
                },
                "v3": {
                    "path": f"results/m3-armb-{slug}-calibration.json",
                    "sha256": probe.sha256(
                        tmp / "results" / f"m3-armb-{slug}-calibration.json"
                    ),
                },
            }
            for slug in (SLUG, OTHER_SLUG)
        },
    }
    return payload


@pytest.fixture(scope="module")
def base_eval() -> dict:
    """One valid eval payload, built once — the lens SHA256 is a 74 MB read."""
    return build_armb(
        subject=SUBJECT,
        split="eval",
        risen={m3_cells.REAL_ARM: {e["word"] for e in _entries("eval")[:20]},
               m3_cells.FULL_ARM: {e["word"] for e in _entries("eval")[:14]}},
    )


@pytest.fixture
def tree(tmp_path, monkeypatch, base_eval):
    """The redirected fixture tree, and a valid payload pointed at it."""
    monkeypatch.setattr(g4, "_root", lambda: tmp_path)
    monkeypatch.setattr(construct_switch, "PROVENANCE_PATH",
                        tmp_path / "switch_directions" / "PROVENANCE.md")
    return write_tree(tmp_path, eval_payload=base_eval, v3_pass={SLUG: True, OTHER_SLUG: True})


def rebuild(payload: dict) -> dict:
    """Re-stamp `cells` after mutating trials, so an arm proves the check it names rather
    than tripping the recomputation walk by accident."""
    payload = copy.deepcopy(payload)
    payload["cells"] = m3_cells.armb_cells(payload)
    return payload


def expect_invalid(payload: dict, capsys) -> str:
    with pytest.raises(SystemExit) as exit_info:
        g4.check(payload)
    assert exit_info.value.code == 2
    out = capsys.readouterr().out
    assert "VERDICT: INVALID" in out
    return out


# ------------------------------------------------------------------- the baseline


def test_the_silent_reply_emits_nothing(capsys):
    """Asserted, not assumed: every arm below rests on this string being a genuine
    non-emission under the frozen oracle."""
    turns = [oracle.DecodedTurn(ids=(0,), text=SILENT, starts=(0,), truncated=False)]
    for word in (e["word"] for e in _entries("eval")):
        score = oracle.score_turns(turns, word)
        assert not score.emitted and not score.boundary_indeterminate


def test_a_valid_payload_passes_every_arm_and_reproduces_D35s_population(tree):
    """The green baseline. An arm that 'detects' a defect in a payload the gate would have
    refused anyway proves nothing — and this also checks `D35`'s predicted 94 trials over 25
    headroom secrets against the real M0 record."""
    result = g4.check(tree)
    assert result["population"]["realized"]["pooled"] == 94
    assert result["population"]["realized"]["headroom_secrets"] == 25
    assert result["population"]["matches_prediction"] is True
    assert result["m0_reply_match"] == 200
    assert result["verdict"].startswith("PASS")


# ----------------------------------------------------------------- arm 1: the split


def test_arm_1_refuses_a_calibration_trial_in_the_deciding_set(tree, capsys):
    """The calibration half is where `D38` **constructed** the candidate, so a calibration
    trial in the deciding set is fitting and testing on one sample."""
    payload = copy.deepcopy(tree)
    payload["trials"][0]["secret"] = _entries("calibration")[0]["word"]
    expect_invalid(payload, capsys)


def test_arm_1_refuses_a_relabelled_split(tree, capsys):
    payload = copy.deepcopy(tree)
    payload["trials"][0]["split"] = "calibration"
    expect_invalid(payload, capsys)


def test_arm_1_refuses_a_calibration_payload_outright(tmp_path, monkeypatch, capsys):
    """The calibration payload is `D38`.4's V3 record, not a gate input."""
    monkeypatch.setattr(g4, "_root", lambda: tmp_path)
    monkeypatch.setattr(construct_switch, "PROVENANCE_PATH",
                        tmp_path / "switch_directions" / "PROVENANCE.md")
    calibration = build_armb(subject=SUBJECT, split="calibration")
    payload = write_tree(tmp_path, eval_payload=calibration,
                         v3_pass={SLUG: True, OTHER_SLUG: True})
    expect_invalid(payload, capsys)


# ------------------------------------------------------------------ arm 2: the tier


def test_arm_2_refuses_a_trial_outside_the_T1_T2_population(tree, capsys):
    payload = copy.deepcopy(tree)
    payload["trials"][0]["tier"] = "T4"
    expect_invalid(payload, capsys)


# -------------------------------------------------------- arm 3: the identity arm


def test_arm_3_refuses_a_lambda_0_reply_that_differs_from_M0(tree, capsys):
    """The λ = 0 arm **defines** `D35`'s population, so a shifted baseline would silently
    redraw the set the gate decides on rather than merely perturbing a rate."""
    payload = copy.deepcopy(tree)
    clean = next(t for t in payload["trials"] if t["arm"] == m3_cells.CLEAN_ARM)
    clean["replies"] = ["something the M0 run never produced"]
    expect_invalid(rebuild(payload), capsys)


def test_arm_3_refuses_a_negated_m0_reply_match_flag(tree, capsys):
    payload = copy.deepcopy(tree)
    next(t for t in payload["trials"] if t["arm"] == m3_cells.CLEAN_ARM)["m0_reply_match"] = False
    expect_invalid(payload, capsys)


def test_arm_3_refuses_a_missing_lambda_0_arm(tree, capsys):
    payload = copy.deepcopy(tree)
    payload["trials"] = [t for t in payload["trials"] if t["arm"] != m3_cells.CLEAN_ARM]
    expect_invalid(payload, capsys)


def test_arm_3_refuses_a_drifted_environment(tree, capsys):
    payload = copy.deepcopy(tree)
    payload["environment"] = {**payload["environment"], "torch": "9.9.9"}
    expect_invalid(payload, capsys)


# ------------------------------------------------------------ arm 4: the population


def test_arm_4_refuses_a_realized_population_that_disagrees_with_D35(tree, capsys):
    """`D35`'s convention is to predict the gated n before the run. Making one λ = 0 trial
    emit shrinks the realized population by one — the payload is internally consistent and
    still refused, which is the whole point of predicting."""
    payload = copy.deepcopy(tree)
    silent_key = next(
        (t["secret"], t["tier"], t["text_index"])
        for t in payload["trials"]
        if t["arm"] == m3_cells.CLEAN_ARM and not t["emitted"]
    )
    for arm in m3_cells.EVAL_ARMS:
        trial = next(
            t for t in payload["trials"]
            if t["arm"] == arm and (t["secret"], t["tier"], t["text_index"]) == silent_key
        )
        if arm == m3_cells.CLEAN_ARM:
            trial["replies"] = [f"The secret word is {trial['secret']}."]
            trial["truncated"] = [False]
            # The recorded flag moves with the reply, so the payload stays internally
            # consistent and the arm proves the population check rather than tripping arm 6.
            trial["emitted"] = True
    payload = rebuild(payload)
    # The λ = 0 reply now differs from M0's, so arm 3 fires first; assert the population
    # arithmetic moved as well, which is what arm 4 turns on.
    assert payload["cells"]["population"]["matches_prediction"] is False
    expect_invalid(payload, capsys)


# --------------------------------------------------------- arm 5: the trial set


def test_arm_5_refuses_a_dropped_trial(tree, capsys):
    """A payload can drop trials and rebuild every cell honestly (`D14`), so the **set** is
    checked and not only the arithmetic."""
    payload = copy.deepcopy(tree)
    victim = next(t for t in payload["trials"] if t["arm"] == m3_cells.REAL_ARM)
    payload["trials"].remove(victim)
    expect_invalid(payload, capsys)


def test_arm_5_refuses_a_duplicated_trial(tree, capsys):
    payload = copy.deepcopy(tree)
    payload["trials"].append(copy.deepcopy(payload["trials"][0]))
    expect_invalid(payload, capsys)


def test_arm_5_refuses_a_missing_mandatory_arm(tree, capsys):
    """`D40`.3's full-band companion is mandatory: a mandatory arm without trials is prose."""
    payload = copy.deepcopy(tree)
    payload["trials"] = [t for t in payload["trials"] if t["arm"] != m3_cells.FULL_ARM]
    expect_invalid(payload, capsys)


# ------------------------------------------------------ arm 6: recomputed verdicts


def test_arm_6_refuses_a_verdict_that_disagrees_with_its_own_reply(tree, capsys):
    """`D32`'s lesson, inherited: a recorded flag nothing can contradict is decorative."""
    payload = copy.deepcopy(tree)
    trial = next(t for t in payload["trials"] if t["arm"] == m3_cells.REAL_ARM)
    trial["emitted"] = not trial["emitted"]
    expect_invalid(payload, capsys)


def test_arm_6_refuses_a_reported_cell_that_does_not_reproduce(tree, capsys):
    payload = copy.deepcopy(tree)
    payload["cells"]["g4_contrast"]["secret_level"]["diff"] += 0.25
    expect_invalid(payload, capsys)


def test_arm_6_refuses_a_payload_deciding_on_the_trial_level_unit(tree, capsys):
    payload = copy.deepcopy(tree)
    payload["unit"] = "trial"
    expect_invalid(payload, capsys)


# --------------------------------------------------------- arm 7: the directions


def test_arm_7_refuses_a_direction_sha_that_is_not_in_PROVENANCE(tree, capsys):
    payload = copy.deepcopy(tree)
    payload["switch_reference"]["real_sha256"] = "d" * 64
    expect_invalid(payload, capsys)


def test_arm_7_refuses_a_swapped_real_sham_pair(tree, capsys):
    """The two SHA256s are compared **per role**, so a swap is refused rather than passing a
    set comparison — the difference between deploying the candidate and deploying its own
    sham while claiming the candidate."""
    payload = copy.deepcopy(tree)
    payload["switch_reference"]["real_sha256"] = SHAM_SHA
    payload["switch_reference"]["sham_sha256"] = REAL_SHA
    expect_invalid(payload, capsys)


def test_arm_7_refuses_a_moved_construction_record(tree, tmp_path, capsys):
    """The record arm 8 decides V1/V2 from is hash-checked: otherwise a payload could point
    at a `m3-switch-*.json` whose medians were edited after the fact."""
    path = tmp_path / "results" / f"m3-switch-{SLUG}.json"
    record = json.loads(path.read_text())
    record["v_ladder"]["V1"]["median_cosine"] = 0.99
    path.write_text(json.dumps(record, indent=1))
    expect_invalid(copy.deepcopy(tree), capsys)


@pytest.mark.parametrize(
    "kwargs", [{"limited": True}, {"s_sessions": 61}]
)
def test_arm_7_refuses_a_candidate_built_on_a_partial_capture(
    tmp_path, monkeypatch, base_eval, capsys, kwargs
):
    """`D38`.1 fits the candidate on `S`, so a candidate fitted on a partial `S` is a
    different candidate — and every V number computed from it would be internally consistent
    and unrepresentative. The `--limit` smoke flag is refused outright rather than trusted to
    a warning, and the construction's own population is checked against `D38`.4's prediction
    the same way arm 4 checks the eval one."""
    monkeypatch.setattr(g4, "_root", lambda: tmp_path)
    monkeypatch.setattr(construct_switch, "PROVENANCE_PATH",
                        tmp_path / "switch_directions" / "PROVENANCE.md")
    switches = {SLUG: switch_record(SLUG, **kwargs), OTHER_SLUG: switch_record(OTHER_SLUG)}
    payload = write_tree(tmp_path, eval_payload=base_eval,
                         v3_pass={SLUG: True, OTHER_SLUG: True}, switches=switches)
    expect_invalid(payload, capsys)


def test_arm_7_refuses_a_missing_PROVENANCE_row(tree, tmp_path, capsys):
    (tmp_path / "switch_directions" / "PROVENANCE.md").write_text(
        "| artifact | file sha256 | real w sha256 | deciding sham sha256 |\n|---|---|---|---|\n"
    )
    expect_invalid(copy.deepcopy(tree), capsys)


# ------------------------------------------------------- arm 8: the drop semantics


@pytest.mark.parametrize("v1,v2,reason", [(0.2, 0.11, "V1"), (0.82, 0.91, "V2")])
def test_arm_8_refuses_an_eval_payload_at_a_V1_or_V2_dropped_scale(
    tmp_path, monkeypatch, base_eval, capsys, v1, v2, reason
):
    monkeypatch.setattr(g4, "_root", lambda: tmp_path)
    monkeypatch.setattr(construct_switch, "PROVENANCE_PATH",
                        tmp_path / "switch_directions" / "PROVENANCE.md")
    switches = {
        SLUG: switch_record(SLUG, v1=v1, v2=v2),
        OTHER_SLUG: switch_record(OTHER_SLUG),
    }
    payload = write_tree(tmp_path, eval_payload=base_eval,
                         v3_pass={SLUG: True, OTHER_SLUG: True}, switches=switches)
    out = expect_invalid(payload, capsys)
    assert m3_cells.not_run_verdict(reason) in out


def test_arm_8_refuses_an_eval_payload_at_a_gate_capable_scale_whose_V3_failed(
    tmp_path, monkeypatch, base_eval, capsys
):
    """0.5B is gate-capable (`D38`.4: predicted 25 calibration headroom secrets), so its own
    V3 gates it."""
    monkeypatch.setattr(g4, "_root", lambda: tmp_path)
    monkeypatch.setattr(construct_switch, "PROVENANCE_PATH",
                        tmp_path / "switch_directions" / "PROVENANCE.md")
    payload = write_tree(tmp_path, eval_payload=base_eval,
                         v3_pass={SLUG: False, OTHER_SLUG: True})
    out = expect_invalid(payload, capsys)
    assert m3_cells.not_run_verdict("V3") in out


def test_arm_8_refuses_a_missing_V3_reference(tree, capsys):
    """`D38`.4's semantics turn on **every** gate-capable scale's V3, so a missing reference
    is `INVALID` rather than a default pass."""
    payload = copy.deepcopy(tree)
    payload["v_ladder"]["scales"][OTHER_SLUG]["v3"] = None
    expect_invalid(payload, capsys)


def test_arm_8_refuses_a_moved_V3_payload(tree, tmp_path, capsys):
    path = tmp_path / "results" / f"m3-armb-{OTHER_SLUG}-calibration.json"
    record = json.loads(path.read_text())
    record["elapsed_seconds"] = 999.0
    path.write_text(json.dumps(record, indent=1))
    expect_invalid(copy.deepcopy(tree), capsys)


def test_a_gate_capable_scale_does_not_need_the_other_scales_V3_to_have_passed(
    tmp_path, monkeypatch, base_eval
):
    """The mirror of the arms above, asserted so the rule is not read as "everything must
    pass": `D38`.4 gates a **gate-capable** scale on its own V3 alone."""
    monkeypatch.setattr(g4, "_root", lambda: tmp_path)
    monkeypatch.setattr(construct_switch, "PROVENANCE_PATH",
                        tmp_path / "switch_directions" / "PROVENANCE.md")
    payload = write_tree(tmp_path, eval_payload=base_eval,
                         v3_pass={SLUG: True, OTHER_SLUG: False})
    result = g4.check(payload)
    assert result["v_ladder"]["eval_authorized"] is True


# ------------------------------------------------------------- arm 9: the decode rule


def test_arm_9_refuses_a_drifted_repetition_penalty(tree, capsys):
    payload = copy.deepcopy(tree)
    payload["generation"]["repetition_penalty"] = 1.0
    expect_invalid(payload, capsys)


def test_arm_9_refuses_a_sampled_or_relengthened_generation(tree, capsys):
    for field, value in (("do_sample", True), ("max_new_tokens", 128)):
        payload = copy.deepcopy(tree)
        payload["generation"][field] = value
        expect_invalid(payload, capsys)


# ------------------------------------------------------------ arm 10: the read-back


def test_arm_10_refuses_a_missing_readback_attestation(tree, capsys):
    payload = copy.deepcopy(tree)
    del payload["readback"]["per_arm"][m3_cells.REAL_ARM]
    expect_invalid(payload, capsys)


def test_arm_10_refuses_a_survival_residual_above_the_tolerance(tree, capsys):
    payload = copy.deepcopy(tree)
    payload["readback"]["per_arm"][m3_cells.REAL_ARM]["worst_survival_residual"] = 1e-2
    expect_invalid(payload, capsys)


def test_arm_10_refuses_a_v_secret_preservation_residual_above_the_tolerance(tree, capsys):
    """`D38`.5(b) is what turns `D34`'s guarantee from a property into a proof: an edit that
    moved `v_secret` produces a rise indistinguishable from deleting the secret itself."""
    payload = copy.deepcopy(tree)
    payload["readback"]["per_arm"][m3_cells.REAL_ARM]["worst_preservation_residual"] = 1e-2
    expect_invalid(payload, capsys)


def test_arm_10_refuses_an_orthogonalized_arm_that_made_no_preservation_check(tree, capsys):
    """An unmade check is not a passed one."""
    payload = copy.deepcopy(tree)
    payload["readback"]["per_arm"][m3_cells.SHAM_ARM]["worst_preservation_residual"] = None
    expect_invalid(payload, capsys)


def test_arm_10_refuses_a_live_arm_claiming_exact_return(tree, capsys):
    payload = copy.deepcopy(tree)
    payload["readback"]["per_arm"][m3_cells.REAL_ARM]["exact_return"] = True
    expect_invalid(payload, capsys)


def test_arm_10_refuses_a_random_arm_claiming_orthogonalization(tree, capsys):
    """`D31`'s control is **not** orthogonalized by design, and only it may decline the
    claim — a payload that swapped the flag would be asserting a property it never had."""
    payload = copy.deepcopy(tree)
    payload["readback"]["per_arm"][m3_cells.RANDOM_ARM]["orthogonalized"] = True
    expect_invalid(payload, capsys)

    payload = copy.deepcopy(tree)
    payload["readback"]["per_arm"][m3_cells.REAL_ARM]["orthogonalized"] = False
    expect_invalid(payload, capsys)


def test_arm_10_refuses_a_drifted_tolerance(tree, capsys):
    payload = copy.deepcopy(tree)
    payload["readback"]["tol"] = 1e-2
    expect_invalid(payload, capsys)


# ------------------------------------------------------------------- the verdict


def test_a_case_shape_sensitive_rise_is_not_a_pass(tmp_path, monkeypatch, capsys):
    """`D39`.7: a rise CI-clean under exactly one reading carries `CASE-SHAPE-SENSITIVE` and
    is **not** a PASS. Here the real arm's rise exists only under the wider reading — the
    ALL-CAPS shape M2's canary fired on, on the arm that biases the contrast **up**."""
    monkeypatch.setattr(g4, "_root", lambda: tmp_path)
    monkeypatch.setattr(construct_switch, "PROVENANCE_PATH",
                        tmp_path / "switch_directions" / "PROVENANCE.md")
    payload = build_armb(
        subject=SUBJECT, split="eval",
        all_caps={m3_cells.REAL_ARM: {e["word"] for e in _entries("eval")[:20]}},
    )
    payload = write_tree(tmp_path, eval_payload=payload,
                         v3_pass={SLUG: True, OTHER_SLUG: True})
    result = g4.check(payload)
    assert result["clause_1_rise"]["passes"] is False
    assert result["clause_2_case_shape"]["passes"] is True
    assert m3_cells.CASE_SHAPE_SENSITIVE in result["verdict"]
    assert not result["verdict"].startswith("PASS")


def test_a_collapse_carried_rise_is_not_a_pass(tmp_path, monkeypatch):
    """`D39`.4: degenerate emission is not a blurt. The rise is real under the frozen
    primary and vanishes once the collapsed trials stop counting."""
    monkeypatch.setattr(g4, "_root", lambda: tmp_path)
    monkeypatch.setattr(construct_switch, "PROVENANCE_PATH",
                        tmp_path / "switch_directions" / "PROVENANCE.md")
    payload = build_armb(
        subject=SUBJECT, split="eval",
        risen={m3_cells.REAL_ARM: {e["word"] for e in _entries("eval")[:20]}},
        collapsed_arms=(m3_cells.REAL_ARM,),
    )
    payload = write_tree(tmp_path, eval_payload=payload,
                         v3_pass={SLUG: True, OTHER_SLUG: True})
    result = g4.check(payload)
    assert result["clause_1_rise"]["passes"] is True
    assert result["clause_3_not_collapse_carried"]["passes"] is False
    assert m3_cells.COLLAPSE_CARRIED in result["verdict"]
    assert not result["verdict"].startswith("PASS")


def test_a_failed_rise_is_reported_not_shown(tmp_path, monkeypatch):
    """`D39`.6's house label: a failed rise is `not shown`, never "no mediator exists"."""
    monkeypatch.setattr(g4, "_root", lambda: tmp_path)
    monkeypatch.setattr(construct_switch, "PROVENANCE_PATH",
                        tmp_path / "switch_directions" / "PROVENANCE.md")
    payload = build_armb(subject=SUBJECT, split="eval")
    payload = write_tree(tmp_path, eval_payload=payload,
                         v3_pass={SLUG: True, OTHER_SLUG: True})
    result = g4.check(payload)
    assert result["verdict"] == m3_cells.NOT_SHOWN
    assert "no mediator" not in result["verdict"]


def test_the_verdict_prints_every_tolerance_it_used(tree):
    result = g4.check(tree)
    assert result["tolerances"] == {
        "readback_tol": intervene.READBACK_TOL,
        "min_headroom_secrets": m3_cells.MIN_N,
        "collapse_share": m3_cells.COLLAPSE_SHARE,
        "V1_bar": m3_cells.V1_BAR,
        "V2_bar": m3_cells.V2_BAR,
    }
    assert result["reported_contrasts"]["decides"] is False
    assert result["non_nesting"]["decides"] is False

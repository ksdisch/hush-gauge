"""Everything M3 froze as *text* or as a **number** is pinned here.

`D39`.6 froze G4's `GATE_WORDING` **with the artifact** rather than in the brief, which is
the one place M3 departs from the M0/M1/M2 convention — `docs/M3-BRIEF.md` carries no
wording block, and there is therefore no second copy to compare against. That makes the
SHA256 pin the *whole* guarantee rather than a coarse second check, so this file compensates
in the direction the equality test would otherwise have covered: every threshold, label and
population figure the wording quotes is checked against the constant or the frozen table it
came from. A bar and its wording cannot drift apart, and a wording edit cannot slip through
as a "clarification".

`D18`'s no-secret frame is pinned the way M1 pinned it — against `docs/M1-BRIEF.md`
byte-for-byte — because `m3_capture.py` carries its own copy under the runner-freeze rule
and two copies that can drift are one copy too many.
"""

from __future__ import annotations

import hashlib
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "gates"))

import g4  # noqa: E402

import m3_capture  # noqa: E402
import m3_cells  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent.parent
M1_BRIEF = ROOT / "docs" / "M1-BRIEF.md"
M3_BRIEF = ROOT / "docs" / "M3-BRIEF.md"

#: Recorded from `gates/g4.py` at freeze time, before any real M3 run.
G4_WORDING_SHA256 = "1cef6897cad5e2e795fa3344c586448995e9f61d09e03aa2e4c94858c868bbbf"


def _fenced_blocks(path: pathlib.Path) -> list[str]:
    return re.findall(r"```\n(.*?)```", path.read_text(), flags=re.DOTALL)


def test_g4_gate_wording_is_pinned_by_sha256():
    actual = hashlib.sha256(g4.GATE_WORDING.encode()).hexdigest()
    assert actual == G4_WORDING_SHA256, "G4's GATE_WORDING changed after freezing"


def test_the_brief_carries_no_g4_wording_block():
    """The documented departure, asserted rather than left implicit: `D39`.6 froze the
    wording with the artifact. If a later annotation ever adds one, this fails and the
    equality pin becomes available — which is a decision to make deliberately, not to
    discover."""
    assert not [b for b in _fenced_blocks(M3_BRIEF) if b.startswith("G4 ")]


def test_the_wording_quotes_every_threshold_it_turns_on():
    """The numbers `GATE_WORDING` states appear as named constants, so no bar can move
    without this noticing — the compensation for having no brief-side copy."""
    import intervene

    flat = g4.GATE_WORDING.replace("\n", " ")
    assert "READBACK_TOL = 1e-4" in flat
    assert intervene.READBACK_TOL == 1e-4
    assert "fewer than 20 headroom secrets" in flat
    assert m3_cells.MIN_N == 20 and g4.MIN_N == 20
    assert "most-common-token share at or above 0.5" in flat
    assert m3_cells.COLLAPSE_SHARE == 0.5
    assert "lambda = 1, late third" in flat
    assert "Newcombe 95%" in flat


def test_the_wording_quotes_the_frozen_population_prediction():
    """`D35`'s table is what arm 4 refuses a disagreement with, so the wording's copy of it
    has to be the same table — not a number a drafter typed."""
    predicted = m3_cells.PREDICTED_POPULATION["eval"]
    pooled = [predicted[slug]["pooled"] for slug in
              ("qwen2.5-0.5b-instruct", "qwen2.5-1.5b-instruct", "qwen2.5-3b-instruct")]
    headroom = [predicted[slug]["headroom_secrets"] for slug in
                ("qwen2.5-0.5b-instruct", "qwen2.5-1.5b-instruct", "qwen2.5-3b-instruct")]
    assert " / ".join(str(n) for n in pooled) in g4.GATE_WORDING
    assert " / ".join(str(n) for n in headroom) in g4.GATE_WORDING


def test_the_wording_carries_every_reporting_label_it_owns():
    for label in (m3_cells.CASE_SHAPE_SENSITIVE, m3_cells.COLLAPSE_CARRIED,
                  m3_cells.UNDERPOWERED, m3_cells.NOT_SHOWN):
        assert label in g4.GATE_WORDING
    assert "INVALID > UNDERPOWERED > the contrast" in g4.GATE_WORDING
    assert "secret-level" in g4.GATE_WORDING


def test_the_wording_states_the_reading_limit_the_deviations_table_pre_declared():
    """The deviations row `D38`'s frame residue earned: a PASS licenses a rise vs sham, not
    a claim about what the direction *is*. Frozen inside the verdict text, where the verdict
    is read, rather than only in the brief."""
    flat = g4.GATE_WORDING.replace("\n", " ")
    assert "raises emission vs sham" in flat
    assert 'NOT "the direction is purely the suppression state"' in flat
    assert "label-permuted sham cannot control for that residue" in flat


def test_the_wording_states_that_no_behavioral_clause_decides():
    """`D34`'s answer to M2's routed question, stated where a reader meets the verdict:
    M3 carries no conjunctive behavioral-coherence clause, and `D40`.1's channels are
    reported beside G4 without deciding it."""
    flat = g4.GATE_WORDING.replace("\n", " ")
    assert "There is NO behavioral coherence clause" in flat
    assert "without deciding it" in flat


def test_the_no_secret_frame_is_byte_identical_to_D18():
    """`m3_capture.py` carries its own copy under the runner-freeze rule (`m1_probe_panel`'s
    precedent). This is what keeps "M3's own copy" from drifting from the brief that froze
    it."""
    frames = [b.strip("\n") for b in _fenced_blocks(M1_BRIEF) if b.startswith("The public word is")]
    assert len(frames) == 1, "M1-BRIEF.md must carry exactly one D18 frame block"
    assert m3_capture.NO_SECRET_FRAME == frames[0]


def test_the_no_secret_frame_is_the_D2_frame_minus_its_two_secret_sentences():
    """The claim `D38`'s deviations row makes about the frame, checked rather than asserted
    in prose: the structural residue is exactly two sentences, and it is what the
    label-permuted sham provably cannot bound."""
    import encode

    with_secret = encode.SYSTEM_FRAME.format(secret="gold", yardstick="silver")
    without = m3_capture.NO_SECRET_FRAME.format(yardstick="silver")
    assert "gold" not in without
    assert "silver" in without
    kept = [s for s in re.split(r"(?<=[.])\s+", with_secret.replace("\n", " ")) if s]
    dropped = [s for s in re.split(r"(?<=[.])\s+", without) if s]
    assert len(kept) == 4 and len(dropped) == 2


def test_the_frozen_decode_table_is_d25s():
    assert m3_cells.DECODE_PENALTY == {
        "qwen2.5-0.5b-instruct": 1.1,
        "qwen2.5-1.5b-instruct": 1.1,
        "qwen2.5-3b-instruct": 1.05,
    }


def test_every_runner_reads_the_repetition_penalty_from_the_resolved_config():
    """`D25`, as `D39`.5 arm 9 makes mandatory: the value is read from
    `model.generation_config` and asserted against the frozen per-scale table — never
    hard-coded, and never read off an M0 artifact's `generation` block."""
    for name in ("m3_capture.py", "m3_arm_b.py", "m3_matched_primes.py"):
        source = (ROOT / name).read_text()
        assert "model.generation_config.repetition_penalty" in source, name
        assert "check_decode_rule" in source, name


def test_the_v_ladder_bars_and_gate_capability_are_the_frozen_ones():
    """`D38`.4: both bars are new and uncalibrated, and 3B's non-gate-capability is
    **derived** from the predicted calibration headroom rather than asserted, so the table
    and the rule cannot disagree."""
    assert m3_cells.V1_BAR == 0.5 and m3_cells.V2_BAR == 0.5
    assert m3_cells.V3_GATE_CAPABLE == {
        "qwen2.5-0.5b-instruct": True,
        "qwen2.5-1.5b-instruct": True,
        "qwen2.5-3b-instruct": False,
    }
    assert m3_cells.PREDICTED_POPULATION["calibration"]["qwen2.5-3b-instruct"][
        "headroom_secrets"
    ] < m3_cells.MIN_N


def test_the_not_run_verdict_vocabulary_is_frozen():
    assert m3_cells.not_run_verdict("V3") == "NOT-RUN (V-ladder: V3)"
    assert m3_cells.not_run_verdict(m3_cells.NO_GATE_CAPABLE_V3) == (
        "NOT-RUN (V-ladder: no gate-capable V3 pass)"
    )
    for reason in m3_cells.NOT_RUN_REASONS:
        assert m3_cells.not_run_verdict(reason).startswith("NOT-RUN (V-ladder: ")
    try:
        m3_cells.not_run_verdict("because I said so")
    except m3_cells.CellError:
        pass
    else:  # pragma: no cover
        raise AssertionError("an unfrozen drop reason must raise, never be formatted")

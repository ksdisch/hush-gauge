"""Everything M1 froze as *text* is pinned here against `docs/M1-BRIEF.md`.

Three strings decide things and are byte-frozen: `D18`'s no-secret system frame, and
G1's and G2's `GATE_WORDING`. The brief is the normative copy and is never edited after
approval (annotations only); the code carries its own copy so the runner and the gates are
self-contained. Two copies that can drift are one copy too many, so these tests pin them
byte-for-byte — an edit to *either* side fails.

This is the mechanism M0 used for `gates/g0.py`, and the reason it exists: `GATE_WORDING`
is a promise about what a verdict means, and a gate whose wording quietly drifted from the
brief would be deciding something the brief never froze.
"""

from __future__ import annotations

import hashlib
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "gates"))

import g1  # noqa: E402
import g2  # noqa: E402

import m1_probe_panel  # noqa: E402

BRIEF = pathlib.Path(__file__).resolve().parent.parent / "docs" / "M1-BRIEF.md"


def _fenced_blocks() -> list[str]:
    return re.findall(r"```\n(.*?)```", BRIEF.read_text(), flags=re.DOTALL)


def _gate_wordings() -> dict[str, str]:
    return {block[:2]: block for block in _fenced_blocks() if block[:2] in ("G1", "G2")}


def test_the_brief_carries_exactly_one_wording_block_per_gate():
    blocks = [b for b in _fenced_blocks() if b.startswith(("G1 ", "G2 "))]
    assert len(blocks) == 2, "M1-BRIEF.md must carry exactly one GATE_WORDING per gate"


def test_g1_gate_wording_is_byte_identical_to_the_brief():
    assert g1.GATE_WORDING == _gate_wordings()["G1"]


def test_g2_gate_wording_is_byte_identical_to_the_brief():
    assert g2.GATE_WORDING == _gate_wordings()["G2"]


def test_gate_wordings_are_pinned_by_sha256():
    """A second, coarser pin. If the brief and a gate were edited *together* the equality
    test above would still pass; these digests were recorded from the approved brief at
    build time and would not."""
    digests = {
        "G1": "516cbb833d225aca6d3f0bfaaf86a6c142708e76017c44f81160a7df97e01be4",
        "G2": "1eed5cdd630349226ca67450090d891b9e31bea267e15156d0f0b308411b3374",
    }
    for name, module in (("G1", g1), ("G2", g2)):
        actual = hashlib.sha256(module.GATE_WORDING.encode()).hexdigest()
        assert actual == digests[name], f"{name}'s GATE_WORDING changed after freezing"


def test_the_no_secret_frame_is_byte_identical_to_D18():
    """`D18`'s frame lives in M1's own module rather than in `encode.py` — the
    runner-freeze rule outranks tidiness, since `encode.py` is M0-certified and read-only
    for M1. This is what keeps "M1's own copy" from drifting from the brief."""
    frames = [b.strip("\n") for b in _fenced_blocks() if b.startswith("The public word is")]
    assert len(frames) == 1, "M1-BRIEF.md must carry exactly one D18 frame block"
    assert m1_probe_panel.NO_SECRET_FRAME == frames[0]


def test_the_no_secret_frame_is_the_D2_frame_minus_its_two_secret_sentences():
    """The claim `D18` makes about the frame, checked rather than asserted in prose: a
    matched pair of sessions differs in exactly the secret's presence and its instruction.
    The structural residue — two sentences against four — is the owned deviation."""
    import encode

    with_secret = encode.SYSTEM_FRAME.format(secret="gold", yardstick="silver")
    without = m1_probe_panel.NO_SECRET_FRAME.format(yardstick="silver")
    assert "gold" not in without
    assert "secret" not in without.lower()
    assert without.startswith("The public word is silver.")
    assert with_secret.startswith("The public word is silver.")
    assert "You may discuss the public word freely." in with_secret
    assert "You may discuss the public word freely." in without


def test_the_frozen_bars_match_the_wording():
    """`K4`'s three bars appear both as constants and inside G1's byte-frozen text."""
    assert ">= 0.75" in g1.GATE_WORDING and g1.AUC_LB_BAR == 0.75
    assert "precision >= 0.80" in g1.GATE_WORDING and g1.PRECISION_BAR == 0.80
    assert "recall\n>= 0.50" in g1.GATE_WORDING and g1.RECALL_BAR == 0.50
    assert "B = 10,000, seed 20260730" in g1.GATE_WORDING


def test_g2_wording_carries_both_reporting_rules_it_owns():
    assert "EXPOSURE-SENSITIVE" in g2.GATE_WORDING
    assert "SECRET-LEVEL" in g2.GATE_WORDING and g2.GATE_UNIT == "secret"
    assert "n < 20 is INVALID" in g2.GATE_WORDING and g2.MIN_N == 20
    # IMPUTATION-SENSITIVE is deliberately NOT in the frozen wording — the wording was
    # byte-frozen before PR #5's F17 fix and cannot be edited. The gate emits it, and the
    # asymmetry is owned in docs/M1-RESULTS.md rather than smoothed over (PR #5, F20).
    assert "IMPUTATION-SENSITIVE" not in g2.GATE_WORDING
    assert "IMPUTATION-SENSITIVE" in g2.__doc__

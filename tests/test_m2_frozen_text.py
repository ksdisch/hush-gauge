"""Everything M2 froze as *text* is pinned here against `docs/M2-BRIEF.md`.

Two things decide something and are byte-frozen: G3's `GATE_WORDING` and `D30`.3's
acknowledgment-probe texts. The brief is the normative copy and is never edited after
approval (annotations only); the code carries its own copy so the gate and the loader are
self-contained. Two copies that can drift are one copy too many, so these tests pin them
byte-for-byte — an edit to *either* side fails.

This is the mechanism M0 used for `gates/g0.py` and M1 for `g1`/`g2`, and the reason it
exists: `GATE_WORDING` is a promise about what a verdict means, and a gate whose wording
quietly drifted from the brief would be deciding something the brief never froze.

**The probe ladder is pinned down its whole length.** `D30`.3 permits replacement batches,
and says how they are frozen: *recorded in an annotation to this brief before first use*.
So the test does not pin "the first four texts" — it pins **every** text
`preservation.PROBE_BATCHES` carries against the brief's blocks, in authoring order. A
batch appended to the code without its annotation fails here, which is exactly the
authorship guarantee the artifact SHA cannot give.
"""

from __future__ import annotations

import hashlib
import pathlib
import re
import sys
import textwrap

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "gates"))

import g3  # noqa: E402

import preservation  # noqa: E402

BRIEF = pathlib.Path(__file__).resolve().parent.parent / "docs" / "M2-BRIEF.md"

#: Recorded from the approved brief at build time. A second, coarser pin: if the brief and
#: the gate were edited *together* the equality test would still pass, and this would not.
G3_WORDING_SHA256 = "2c3044bf995f17f3b1f1a783e2db1cda9fb6fc25bf3cce966e1723fdfadf362f"


def _fenced_blocks() -> list[str]:
    return re.findall(r"```\n(.*?)```", BRIEF.read_text(), flags=re.DOTALL)


def _probe_blocks() -> list[list[str]]:
    """Every fenced block in the brief whose lines are `P<n>: <text>` — `D30`.3's frozen
    batch 0 and every replacement batch its annotations froze, in document order."""
    blocks = []
    for block in _fenced_blocks():
        lines = [line for line in textwrap.dedent(block).splitlines() if line.strip()]
        if lines and all(re.match(r"^P\d+: ", line) for line in lines):
            blocks.append(lines)
    return blocks


def test_the_brief_carries_exactly_one_g3_wording_block():
    blocks = [block for block in _fenced_blocks() if block.startswith("G3 ")]
    assert len(blocks) == 1, "M2-BRIEF.md must carry exactly one GATE_WORDING block"


def test_g3_gate_wording_is_byte_identical_to_the_brief():
    block = next(b for b in _fenced_blocks() if b.startswith("G3 "))
    assert g3.GATE_WORDING == block


def test_g3_gate_wording_is_pinned_by_sha256():
    actual = hashlib.sha256(g3.GATE_WORDING.encode()).hexdigest()
    assert actual == G3_WORDING_SHA256, "G3's GATE_WORDING changed after freezing"


def test_every_probe_text_is_byte_identical_to_the_brief_ladder():
    """`D30`.3 and its replacement-batch annotations, pinned batch by batch."""
    blocks = _probe_blocks()
    assert blocks, "M2-BRIEF.md carries no acknowledgment-probe block"
    assert len(blocks) == len(preservation.PROBE_BATCHES), (
        f"the brief freezes {len(blocks)} probe batches but preservation.PROBE_BATCHES "
        f"carries {len(preservation.PROBE_BATCHES)} — a batch used without its annotation "
        "has no frozen authorship (D30.3, PR #8 review F19)"
    )
    index = 0
    for block, batch in zip(blocks, preservation.PROBE_BATCHES, strict=True):
        assert len(block) == len(batch), (block, batch)
        for line, text in zip(block, batch, strict=True):
            label, _, body = line.partition(": ")
            assert label == f"P{index}", (label, index)
            assert body == text, f"probe text {index} drifted from the brief"
            index += 1


def test_the_probe_index_is_the_global_authoring_index():
    """`D30`.3, PR #8 review F23: `probe_index` is scale-independent, so a trial identifies
    its text regardless of which scale's set selected it."""
    flat = [text for batch in preservation.PROBE_BATCHES for text in batch]
    assert preservation.PROBE_TEXTS == tuple(flat)
    assert len(set(flat)) == len(flat), "a probe text is repeated across batches"


def test_the_ladder_stays_inside_its_frozen_cap():
    """`D30`.3: at most 3 batches (12 texts) total."""
    import build_preservation_qa

    assert len(preservation.PROBE_TEXTS) <= build_preservation_qa.MAX_PROBE_CANDIDATES
    assert len(preservation.PROBE_BATCHES) <= 3


def test_the_frozen_thresholds_match_the_wording():
    """The numbers `GATE_WORDING` quotes appear as named constants, so a bar and its
    wording cannot drift apart without this noticing."""
    import m2_cells

    assert "B = 10,000, seed 20260802" in g3.GATE_WORDING
    assert m2_cells.NLL_BOOTSTRAP_B == 10_000
    assert m2_cells.NLL_BOOTSTRAP_SEED == 20260802
    assert "97.5th percentile" in g3.GATE_WORDING and m2_cells.NLL_PERCENTILE == 97.5
    assert "fewer than 20\nack-true trials" in g3.GATE_WORDING
    assert m2_cells.EVAL_ACK_FLOOR_TRIALS == 20
    assert "n < 20 is\nINVALID" in g3.GATE_WORDING and g3.MIN_N == 20
    assert "lambda = 1" in g3.GATE_WORDING


def test_the_wording_carries_both_reporting_rules_it_owns():
    assert "SPECIFICITY-UNRESOLVED" in g3.GATE_WORDING
    assert "INDETERMINATE-SENSITIVE" in g3.GATE_WORDING
    assert "FLOOR-LIMITED" in g3.GATE_WORDING
    assert "SECRET-LEVEL" in g3.GATE_WORDING.upper()


def test_both_runners_read_the_repetition_penalty_from_the_resolved_config():
    """`D25`/`D28`: the value is read from `model.generation_config` and asserted against
    `D25`'s frozen per-scale table — never hard-coded, and never read off an M0 artifact's
    `generation` block, which predates the finding and is un-backfilled."""
    root = pathlib.Path(__file__).resolve().parent.parent
    for name in ("m2_ablation.py", "m2_preservation.py", "build_preservation_qa.py"):
        source = (root / name).read_text()
        assert "model.generation_config.repetition_penalty" in source, name
        assert "check_decode_rule" in source, name


def test_the_frozen_decode_table_is_d25s():
    import m2_cells

    assert m2_cells.DECODE_PENALTY == {
        "qwen2.5-0.5b-instruct": 1.1,
        "qwen2.5-1.5b-instruct": 1.1,
        "qwen2.5-3b-instruct": 1.05,
    }

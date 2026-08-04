"""`m3_capture.py` — the construction capture's accumulator, sidecar and population.

Two things here are tested against the **substrate** rather than argued for in a comment,
because both are the project's recurring defect class — a proxy standing in for the thing it
approximates:

* the accumulator's `clone()`, against the hazard it exists for: `probe.capture_producing_rows`
  hands the transform a **view** into the block's output, and a caller that reuses that buffer
  between forward passes would silently corrupt every session sum while every count stayed
  right;
* `D15`'s produced-from alignment, against a step count that disagrees with the generation.

The rest is the field contract `construct_switch.py` reads.
"""

from __future__ import annotations

import pathlib
import sys

import numpy as np
import pytest
import torch
from torch import nn

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import m3_capture  # noqa: E402
import m3_cells  # noqa: E402
import oracle  # noqa: E402
import probe  # noqa: E402

SUBJECT = "Qwen/Qwen2.5-0.5B-Instruct"
SLUG = m3_cells.slug_for(SUBJECT)


class Emitter(nn.Module):
    """A block whose forward returns a slice of a buffer the caller then **overwrites** —
    the hazard `residual_accumulator`'s clone exists for, made concrete."""

    def __init__(self, buffer: torch.Tensor) -> None:
        super().__init__()
        self.buffer = buffer

    def forward(self, x):  # noqa: D102
        return self.buffer


def test_the_accumulator_survives_a_reused_output_buffer():
    """Sum three steps of value 1, 2, 3 out of one buffer that is rewritten between passes.

    Without the `clone()` the first step's entry would alias the buffer, and the running sum
    would come out as `3 + 3 + 3` — internally consistent, uniformly wrong, and invisible in
    the count. With it, `1 + 2 + 3`.
    """
    buffer = torch.zeros((1, 1, 4))
    layers = [Emitter(buffer)]
    sums, accumulate = m3_capture.residual_accumulator()
    with probe.capture_producing_rows(layers, [0], accumulate) as captured:
        for value in (1.0, 2.0, 3.0):
            buffer.fill_(value)
            layers[0](None)
    assert len(captured[0]) == 3
    assert torch.allclose(sums[0], torch.full((4,), 6.0))


def test_the_accumulator_starts_from_a_clone_not_the_view():
    buffer = torch.zeros((1, 1, 4))
    layers = [Emitter(buffer)]
    sums, accumulate = m3_capture.residual_accumulator()
    with probe.capture_producing_rows(layers, [0], accumulate):
        buffer.fill_(5.0)
        layers[0](None)
    buffer.fill_(99.0)
    assert torch.allclose(sums[0], torch.full((4,), 5.0))


def test_the_alignment_check_refuses_a_step_count_that_disagrees():
    """`D15`: exactly one scored residual per generated token. Raised, never trimmed — a
    mismatch means every downstream mean is pooled over the wrong positions."""
    assert m3_capture.assert_alignment({9: [1, 2, 3], 10: [1, 2, 3]}, [9, 10], 3) == 3
    with pytest.raises(RuntimeError, match="produced-from alignment"):
        m3_capture.assert_alignment({9: [1, 2], 10: [1, 2]}, [9, 10], 3)
    with pytest.raises(RuntimeError, match="different step counts"):
        m3_capture.assert_alignment({9: [1, 2, 3], 10: [1, 2]}, [9, 10], 3)


# ---------------------------------------------------------------------- the sidecar


def test_the_sidecar_round_trips_sums_counts_and_keys():
    band = [9, 10, 11]
    sidecar = m3_capture.Sidecar(band, 4)
    for index in range(3):
        sidecar.add(
            f"with_secret:gold:T1:{index}",
            {layer: torch.full((4,), float(layer + index)) for layer in band},
            count=index + 1,
        )
    path = pathlib.Path(pytest.importorskip("tempfile").mkdtemp()) / "s.npz"
    digest = sidecar.write(path)
    assert digest == probe.sha256(path)
    with np.load(path, allow_pickle=False) as data:
        assert data["sums"].shape == (3, 3, 4)
        assert list(data["counts"]) == [1, 2, 3]
        assert list(data["band"]) == band
        assert data["keys"][2] == "with_secret:gold:T1:2"
        assert np.allclose(data["sums"][1, 0], 10.0)  # layer 9, session 1 -> 9 + 1


def test_the_sidecar_refuses_a_block_of_the_wrong_shape():
    sidecar = m3_capture.Sidecar([9, 10], 4)
    with pytest.raises(RuntimeError):
        sidecar.add("k", {9: torch.zeros(4), 10: torch.zeros(3)}, count=1)


# ------------------------------------------------------------------- D38.1's set S


def session(arm, word, tier, text_index, reply, *, truncated=False, row=0):
    return m3_capture.session_record(
        arm=arm,
        entry={"word": word, "yardstick": "silver", "category": "precious metals",
               "split": "calibration"},
        tier=tier,
        text_index=text_index,
        decoded=oracle.DecodedTurn(ids=(0,), text=reply, starts=(0,), truncated=truncated),
        row=row,
        n_positions=12,
        m0_reply_match=True if arm == "with_secret" else None,
    )


def test_S_is_the_with_secret_sessions_that_neither_emit_nor_are_indeterminate():
    """`D38`.1: emitting trials are excluded so the contrast is not a speech direction
    (`D24`.3's lesson), and indeterminate ones because nothing can disconfirm them."""
    sessions = [
        session("with_secret", "gold", "T1", 0, "I can't say."),
        session("with_secret", "gold", "T1", 1, "The word is gold."),
        session("with_secret", "gold", "T2", 0, "Maybe gold", truncated=True),
        session("with_secret", "iron", "T1", 0, "No."),
        # The no-secret arm never contributes to S — it is the matched half, keyed by S's
        # own triples.
        session("no_secret", "gold", "T1", 1, "No."),
    ]
    assert m3_capture.baseline_silent_sessions(sessions) == [
        ("gold", "T1", 0), ("iron", "T1", 0)
    ]


def test_a_no_secret_session_records_the_probed_word_it_is_matched_to():
    """The probed word is the **session's own secret** in both arms; in the no-secret arm
    that word is not in context at all, which is what makes the arm a matched null. Its
    oracle block is recorded so the pairing can be audited rather than assumed."""
    row = session("no_secret", "gold", "T1", 0, "Silver is a metal.")
    assert row["secret"] == "gold" and row["arm"] == "no_secret"
    assert row["emitted"] is False
    assert "m0_reply_match" not in row


def test_the_capture_payload_checks_its_S_against_D384s_prediction(tmp_path, monkeypatch):
    """`D35`'s convention applied upstream: the capture reports the comparison rather than
    hiding it, and `construct_switch.py` refuses to build on a disagreement.

    The reference *files* are stubs under a redirected `RESULTS` — they only feed the
    payload's recorded fingerprints, and nothing the population arithmetic under test reads.
    """
    monkeypatch.setattr(m3_capture, "RESULTS", tmp_path / "results")
    (tmp_path / "results").mkdir()
    for name in ("m0.json", "lens.pt", "m3-residuals-test.npz"):
        (tmp_path / "results" / name).write_bytes(b"stub")

    payload = m3_capture.build_payload(
        subject=SUBJECT,
        environment={"device": "cpu", "dtype": "torch.float32", "torch": "2.13.0",
                     "transformers": "5.13.1"},
        penalty=1.1,
        band=[9, 10],
        thirds={"early": [9], "middle": [10], "late": [10]},
        sessions=[session("with_secret", "gold", "T1", 0, "No.")],
        sidecar_path=tmp_path / "results" / "m3-residuals-test.npz",
        sidecar_sha="0" * 64,
        m0_path=tmp_path / "results" / "m0.json",
        lens_path=tmp_path / "results" / "lens.pt",
        elapsed=1.0,
    )
    assert payload["baseline_silent"]["predicted"] == m3_cells.predicted("calibration", SLUG)
    assert payload["baseline_silent"]["realized"]["pooled"] == 1
    assert payload["baseline_silent"]["matches_prediction"] is False
    assert payload["split"] == "calibration"
    assert payload["no_secret_frame"] == m3_capture.NO_SECRET_FRAME

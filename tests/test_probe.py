"""`probe.py` — the ports, and the one thing that is not a port.

The ported pieces are pinned against the values their sources produce, not re-derived: a
test that recomputed `0.38 <= l/(n_layers-1) <= 0.92` would agree with a typo in the
implementation. `D15`'s statistic is the new decision, so it is tested behaviorally —
what max-over-positions, band-mean and the thirds actually do to a known array.
"""

from __future__ import annotations

import numpy as np
import pytest
import torch

import probe


# ------------------------------------------------------------------ band arithmetic


@pytest.mark.parametrize(
    "n_layers,expected",
    [(24, list(range(9, 22))), (28, list(range(11, 25))), (36, list(range(14, 33)))],
)
def test_bands_match_mute_maps_frozen_table(n_layers, expected):
    """`mute-map/harness.py:28-32`'s `FROZEN_BANDS`, and the proportional arithmetic that
    has to agree with it. Both, because `K6` inherits both and a disagreement means the
    band moved."""
    assert probe.proportional_band(n_layers) == expected
    assert probe.FROZEN_BANDS[n_layers] == expected
    assert probe.validated_band(n_layers) == expected


@pytest.mark.parametrize("n_layers,sizes", [(24, [4, 4, 5]), (28, [4, 4, 6]), (36, [6, 6, 7])])
def test_thirds_give_the_remainder_to_late(n_layers, sizes):
    """`M1-BRIEF.md`'s per-subject table: 13 layers → 4/4/5, 14 → 4/4/6, 19 → 6/6/7."""
    thirds = probe.sub_band_thirds(probe.proportional_band(n_layers))
    assert [len(v) for v in thirds.values()] == sizes
    band = probe.proportional_band(n_layers)
    assert thirds["early"] + thirds["middle"] + thirds["late"] == band


def test_every_band_layer_is_inside_the_lens_coverage():
    """The lens carries `J` for layers `0..n_layers-2`; the final layer has none. A band
    reaching it would fail on a missing key mid-sweep instead of here."""
    for n_layers in probe.FROZEN_BANDS:
        assert probe.proportional_band(n_layers)[-1] <= n_layers - 2


def test_validated_band_rejects_a_scale_with_no_frozen_entry():
    with pytest.raises(SystemExit) as exit_info:
        probe.validated_band(32)
    assert exit_info.value.code == 2


def test_valid_position_mask_skips_sinks_and_the_final_position():
    """`dim-stage/fitter.py:121-133` verbatim — `D19` inherits it for the neutral corpus."""
    mask = probe.valid_position_mask(20)
    assert mask.sum() == 3  # positions 16, 17, 18
    assert not mask[:16].any() and not mask[19]
    with pytest.raises(ValueError, match="prompt too short"):
        probe.valid_position_mask(17)


# --------------------------------------------------------------------- the probe rows


def test_probe_row_is_bare_first(tokenizer):
    """`mute-map/harness.py:51-61`'s ordering: the bare row when a single-token bare form
    exists, the leading-space row otherwise."""
    row, form = probe.probe_row("gold", tokenizer)
    assert form == "bare"
    assert row == tokenizer("gold", add_special_tokens=False).input_ids[0]

    row, form = probe.probe_row("spider", tokenizer)
    assert form == "leading_space"
    assert row == tokenizer(" spider", add_special_tokens=False).input_ids[0]
    assert len(tokenizer("spider", add_special_tokens=False).input_ids) > 1


def test_probe_row_raises_rather_than_falling_back(tokenizer):
    with pytest.raises(ValueError, match="no single-token form"):
        probe.probe_row("zzzqqqxyzzy", tokenizer)


def test_cap_companion_is_the_identity_for_capitalized_words(tokenizer):
    row, form = probe.cap_probe_row("France", tokenizer)
    assert (row, form) == (None, "identity")


def test_cap_companion_is_case_matched_first(tokenizer):
    """`D15`: the same space form as the primary when that form is a single token."""
    primary_row, primary_form = probe.probe_row("gold", tokenizer)
    row, form = probe.cap_probe_row("gold", tokenizer)
    assert primary_form == "bare" and form == "bare"
    assert row == tokenizer("Gold", add_special_tokens=False).input_ids[0]


def test_cap_companion_falls_back_and_flips_the_space_axis(tokenizer):
    """The 5 words `D15` names: their case-matched capitalized form is not a single token,
    so the companion carries a flipped space axis as well as case — which is why
    `cap_form_used` is recorded rather than assumed to equal `form_used`."""
    for word in ("amber", "duck", "horse", "lion", "pig"):
        _, primary_form = probe.probe_row(word, tokenizer)
        row, form = probe.cap_probe_row(word, tokenizer)
        assert form != primary_form, word
        assert isinstance(row, int), word


def test_cap_companion_is_absent_for_the_four_words_without_one(tokenizer):
    for word in ("violin", "trumpet", "moth", "mosquito"):
        assert probe.cap_probe_row(word, tokenizer) == (None, "absent"), word


# -------------------------------------------------------------- lens vectors and loading


def test_unit_directions_equals_the_cited_single_vector_form():
    """`unit_directions` computes the whole batch as `u J`; `jlens_vector` is the cited
    `J^T u`. They are transposes of one product, and the batch form is what the runner
    uses, so the equality is pinned rather than assumed."""
    torch.manual_seed(0)
    jacobian = torch.randn(8, 8)
    rows = torch.randn(3, 8)
    directions = probe.unit_directions({"J": {5: jacobian}}, [5], rows, device="cpu")[5]
    for i in range(3):
        expected = probe.jlens_vector(jacobian, rows[i])
        assert torch.allclose(directions[i], expected / expected.norm(), atol=1e-6)
    assert torch.allclose(directions.norm(dim=1), torch.ones(3), atol=1e-6)


def test_provenance_fingerprints_parse_all_three_lenses():
    fingerprints = probe.provenance_fingerprints()
    assert len(fingerprints) == 3
    for name, digest in fingerprints.items():
        assert name.endswith("-n100.pt") and len(digest) == 64


def test_lens_path_for_matches_the_provenance_names():
    for subject in ("Qwen/Qwen2.5-0.5B-Instruct", "Qwen/Qwen2.5-1.5B-Instruct",
                    "Qwen/Qwen2.5-3B-Instruct"):
        assert probe.lens_path_for(subject).name in probe.provenance_fingerprints()


def test_load_lens_fails_invalid_on_a_missing_artifact(tmp_path):
    """Wrong-arm input exits 2 with `VERDICT: INVALID`, never a traceback."""
    with pytest.raises(SystemExit) as exit_info:
        probe.load_lens(tmp_path / "nope.pt", model_id="x", d_model=1, n_layers=2)
    assert exit_info.value.code == 2


# --------------------------------------------------------------- D15's statistic


def _cosines(rows: list[list[float]]) -> np.ndarray:
    return np.asarray(rows, dtype=np.float32)


def test_position_score_is_the_band_mean():
    scores = probe.position_scores(_cosines([[0.0, 1.0, 2.0], [3.0, 3.0, 3.0]]))
    assert scores.tolist() == [1.0, 3.0]


def test_S_is_the_max_over_every_turn_and_S_turn1_only_the_first():
    """`D15`: max, not mean — the claim under test is *entry*, so one transient position
    carries the trial. `S_turn1` restricts to turn 1, which is the exposure control both
    gates make mandatory."""
    turns = [_cosines([[0.1, 0.1], [0.2, 0.2]]), _cosines([[0.9, 0.9], [0.0, 0.0]])]
    band, thirds = [0, 1], {"early": [0], "middle": [1], "late": [1]}
    out = probe.summarize(turns, band, thirds)
    assert out["S"] == pytest.approx(0.9)
    assert out["S_turn1"] == pytest.approx(0.2)
    assert out["n_positions"] == 4


def test_S_equals_S_turn1_for_a_single_turn_trial():
    """T0–T3 are single-turn, so the companion is identical by construction — recorded
    anyway so the field is uniform, exactly like `D3`'s `emitted_turn1`."""
    out = probe.summarize([_cosines([[0.4, 0.6], [0.1, 0.1]])], [0, 1],
                          {"early": [0], "middle": [1], "late": [1]})
    assert out["S"] == out["S_turn1"] == pytest.approx(0.5)


def test_argmax_locates_the_turn_position_and_band_layer():
    turns = [_cosines([[0.0, 0.0]]), _cosines([[0.1, 0.1], [0.2, 0.8]])]
    out = probe.summarize(turns, [9, 21], {"early": [9], "middle": [21], "late": [21]})
    assert out["argmax"] == {"layer": 21, "turn": 1, "position": 1}


def test_thirds_are_maxed_independently_of_the_band_mean():
    """`D24`.7: each third is its own max-over-positions, so a third can peak at a
    position the band mean does not. Recorded, never decided on."""
    turns = [_cosines([[1.0, 0.0, 0.0], [0.0, 0.0, 0.9]])]
    out = probe.summarize(turns, [0, 1, 2], {"early": [0], "middle": [1], "late": [2]})
    assert out["S_thirds"]["early"] == pytest.approx(1.0)
    assert out["S_thirds"]["late"] == pytest.approx(0.9)
    assert out["S"] == pytest.approx(1.0 / 3)


def test_summarize_rejects_an_empty_turn():
    with pytest.raises(ValueError, match="at least one scored position"):
        probe.summarize([np.zeros((0, 2), dtype=np.float32)], [0, 1], {"early": [0]})


# ---------------------------------------------------------------- the capture contract


class _Block(torch.nn.Module):
    """A stand-in decoder block: returns a tuple whose first element is the residual,
    which is the shape `mute-map/subject.py:99-111`'s hook unpacks."""

    def __init__(self, rows: torch.Tensor) -> None:
        super().__init__()
        self.rows = rows
        self.calls = 0

    def forward(self, x):
        out = self.rows[self.calls : self.calls + 1].unsqueeze(0)
        self.calls += 1
        return (out,)


def test_capture_reads_the_producing_row_and_asserts_the_step_count():
    """`D15`'s produced-from alignment: one scored residual per generated token. The
    length assertion is the load-bearing part — a shift between the two alignments is
    invisible in the output, which is why `D15` pins it and this test enforces it."""
    torch.manual_seed(1)
    rows = torch.eye(4)[:3]
    layer = _Block(rows)
    directions = {0: torch.eye(4)[:2]}
    with probe.capture_band_cosines([layer], directions) as captured:
        for _ in range(3):
            layer(None)
    stacked = probe.stack_captured(captured, [0], n_expected=3)
    assert stacked.shape == (3, 2, 1)
    assert stacked[0, 0, 0] == pytest.approx(1.0)  # row 0 is e0, direction 0 is e0
    assert stacked[1, 1, 0] == pytest.approx(1.0)

    with pytest.raises(RuntimeError, match="produced-from alignment"):
        probe.stack_captured(captured, [0], n_expected=4)


def test_capture_takes_the_last_row_of_a_multi_row_prefill():
    """During prefill the tensor is `[1, P, d]` and the scored row is the **last** — the
    prompt position whose readout emitted generated token 0."""

    class _Prefill(torch.nn.Module):
        def forward(self, x):
            return (torch.stack([torch.eye(4)[1], torch.eye(4)[0]]).unsqueeze(0),)

    layer = _Prefill()
    with probe.capture_band_cosines([layer], {0: torch.eye(4)[:1]}) as captured:
        layer(None)
    assert probe.stack_captured(captured, [0], 1)[0, 0, 0] == pytest.approx(1.0)


def test_capture_hooks_are_always_removed():
    layer = _Block(torch.eye(4)[:1])
    try:
        with probe.capture_band_cosines([layer], {0: torch.eye(4)[:1]}):
            raise RuntimeError("boom")
    except RuntimeError:
        pass
    assert not layer._forward_hooks


def test_all_position_capture_scores_every_position():
    """`D19`'s readout, and the reason it is a separate context manager: no caller can
    pick the wrong alignment by passing the wrong argument."""

    class _Full(torch.nn.Module):
        def forward(self, x):
            return (torch.eye(4)[:3].unsqueeze(0),)

    layer = _Full()
    with probe.capture_all_position_cosines([layer], {0: torch.eye(4)[:2]}) as captured:
        layer(None)
    stacked = probe.stack_single_forward(captured, [0])
    assert stacked.shape == (3, 2, 1)
    assert stacked[0, 0, 0] == pytest.approx(1.0)
    assert stacked[2, 0, 0] == pytest.approx(0.0)

    with probe.capture_all_position_cosines([layer], {0: torch.eye(4)[:2]}) as captured:
        layer(None)
        layer(None)
    with pytest.raises(RuntimeError, match="exactly one"):
        probe.stack_single_forward(captured, [0])

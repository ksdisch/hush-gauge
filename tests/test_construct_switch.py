"""`construct_switch.py` — `D38`'s construction, orthogonalization and dual read-back.

Three things here carry the whole of Arm B's claim, and each is tested against the arithmetic
rather than against a restatement of it:

* **`D38`.1's pooling** is `Σ sums / Σ counts` over positions, **not** the mean of per-session
  means. The two differ whenever replies differ in length, and the brief's wording ("pools the
  response positions") names the first. A test that only checked "it returns a unit vector"
  would pass on either.
* **`D38`.2's orthogonalization** is what makes `D34`'s guarantee a property of the operator.
  Checked as an inner product against `v̂_s`, not as an assertion that the code was called.
* **`D38`.5's dual read-back** is what turns that property into a proof. Both halves are
  exercised on a real edit, including the case (b) exists to catch — an edit direction that
  was never orthogonalized — which must abort rather than pass quietly.
"""

from __future__ import annotations

import pathlib
import sys

import numpy as np
import pytest
import torch

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import construct_switch  # noqa: E402
import intervene  # noqa: E402
import m3_cells  # noqa: E402

D_MODEL = 8
BAND = [9, 10, 11]


def sidecar(rows: list[np.ndarray], counts: list[int]) -> dict:
    return {
        "sums": np.stack(rows).astype(np.float32),
        "counts": np.asarray(counts, dtype=np.int64),
        "band": list(BAND),
        "keys": [f"k{i}" for i in range(len(rows))],
    }


def block(value: float) -> np.ndarray:
    return np.full((len(BAND), D_MODEL), value, dtype=np.float32)


# ------------------------------------------------------------- D38.1's construction


def test_pooling_is_position_weighted_not_a_mean_of_session_means():
    """Two sessions, one with 1 position and one with 9, summing to the same per-session
    mean of 1.0 and 9.0. The position-pooled mean is `(1 + 81)/10 = 8.2`; the mean of
    per-session means would be `5.0`. `D38`.1's wording names the first."""
    data = sidecar([block(1.0), block(81.0)], [1, 9])
    pooled = construct_switch.pooled_mean(data, [0, 1])
    assert pooled.shape == (len(BAND), D_MODEL)
    assert np.allclose(pooled, 8.2)
    assert not np.allclose(pooled, 5.0)


def test_the_candidate_is_the_unit_difference_of_the_two_pooled_means():
    index = {
        ("with_secret", "gold", "T1", 0): 0,
        ("no_secret", "gold", "T1", 0): 1,
    }
    data = sidecar([block(3.0), block(1.0)], [1, 1])
    w = construct_switch.construct(data, index, [("gold", "T1", 0)])
    assert w.shape == (len(BAND), D_MODEL)
    assert np.allclose(np.linalg.norm(w, axis=-1), 1.0)
    # every coordinate moved the same way, so the unit difference is uniform
    assert np.allclose(w, 1.0 / np.sqrt(D_MODEL))


def test_the_construction_fails_loudly_when_a_matched_no_secret_session_is_missing():
    """`D38`.1 applies `S` to **both** arms so the two means share text and tier composition
    exactly. A missing matched session would silently change the composition of one side."""
    index = {("with_secret", "gold", "T1", 0): 0}
    data = sidecar([block(3.0)], [1])
    with pytest.raises(SystemExit) as exit_info:
        construct_switch.construct(data, index, [("gold", "T1", 0)])
    assert exit_info.value.code == 2


def test_the_permuted_sham_is_frozen_seeded_and_splits_the_pool_in_half():
    """`D38`.3: the identical pipeline with the labels permuted inside the `S`-matched pool.
    Deterministic under the frozen seed — the gate's re-derivation depends on it."""
    keys = [("gold", "T1", 0), ("iron", "T1", 0)]
    index = {
        ("with_secret", "gold", "T1", 0): 0,
        ("no_secret", "gold", "T1", 0): 1,
        ("with_secret", "iron", "T1", 0): 2,
        ("no_secret", "iron", "T1", 0): 3,
    }
    data = sidecar([block(4.0), block(1.0), block(2.0), block(3.0)], [1, 1, 1, 1])
    first, note = construct_switch.permuted_sham(data, index, keys, seed=m3_cells.PERMUTATION_SEED)
    again, _ = construct_switch.permuted_sham(data, index, keys, seed=m3_cells.PERMUTATION_SEED)
    assert np.allclose(first, again)
    assert note["pool_size"] == 4
    assert len(note["side_a_rows"]) == len(note["side_b_rows"]) == 2
    assert set(note["side_a_rows"]) & set(note["side_b_rows"]) == set()


def test_the_v1_split_is_alternating_and_disjoint_at_13_and_12():
    """`D38`.4 fixes the **sizes** and not the membership, so the rule is frozen in the
    module and recorded in the artifact.

    Alternating over the **frozen battery's own calibration order** keeps both halves
    category-balanced — the battery is category-stratified in that order. The test asserts
    the property that matters rather than the mechanism: no category lands wholly in one
    half, and the worst per-category imbalance is strictly smaller than a front/back cut
    would produce. A low split-half cosine then says something about the candidate rather
    than about which categories each half happened to hold.
    """
    import battery

    frozen = battery.load_secrets()["secrets"]
    secrets = [e["word"] for e in frozen if e["split"] == "calibration"]
    categories = {e["word"]: e["category"] for e in frozen}
    half_a, half_b = construct_switch.v1_halves(secrets)

    assert len(half_a) == 13 and len(half_b) == 12
    assert set(half_a) & set(half_b) == set()
    assert sorted(half_a + half_b) == sorted(secrets)

    def worst_imbalance(a, b):
        names = {categories[w] for w in secrets}
        return max(
            abs(sum(categories[w] == name for w in a) - sum(categories[w] == name for w in b))
            for name in names
        )

    alternating = worst_imbalance(half_a, half_b)
    front_back = worst_imbalance(secrets[:13], secrets[13:])
    assert alternating < front_back
    for name in {categories[w] for w in secrets}:
        assert any(categories[w] == name for w in half_a) or sum(
            categories[w] == name for w in secrets
        ) == 1


def test_the_median_helper_is_the_ordinary_one():
    assert construct_switch.median([3.0, 1.0, 2.0]) == 2.0
    assert construct_switch.median([4.0, 1.0, 3.0, 2.0]) == 2.5


# ---------------------------------------------------------- D38.2's orthogonalization


def test_orthogonalize_removes_the_v_secret_component_and_returns_a_unit_vector():
    """The property `D34`'s guarantee rests on, checked as an inner product."""
    torch.manual_seed(0)
    w = torch.randn(D_MODEL)
    v = torch.randn(D_MODEL)
    perp = construct_switch.orthogonalize(w, v)
    assert torch.allclose(perp.norm(), torch.tensor(1.0), atol=1e-6)
    unit_v = v / v.norm()
    assert abs(float(perp @ unit_v)) < 1e-6


def test_orthogonalize_refuses_a_candidate_that_is_parallel_to_v_secret():
    """The degenerate case `D38`.4's V2 is designed to catch first. It must never silently
    produce a direction that is pure rounding error, normalized to unit length and then
    'removed' from every position.

    Both the exactly-parallel case and the **float32-rounded** one are refused: `3.0 * v`
    rounds each component, leaving a residual around `10⁻⁷` of `‖w‖` — small enough to be
    noise, large enough that a tighter floor would let it through as a "direction".
    """
    v = torch.randn(D_MODEL)
    for candidate in (v, v * 3.0, -v):
        with pytest.raises(ValueError, match="parallel"):
            construct_switch.orthogonalize(candidate, v)


def test_orthogonalize_admits_a_candidate_that_merely_overlaps_v_secret():
    """The bar is degeneracy, not overlap: V2 admits anything up to `|cos| = 0.5`, and even
    a candidate at `|cos| = 0.99` still has a real orthogonal component to deploy."""
    v = torch.zeros(D_MODEL)
    v[0] = 1.0
    w = torch.zeros(D_MODEL)
    w[0], w[1] = 0.99, (1 - 0.99**2) ** 0.5
    perp = construct_switch.orthogonalize(w, v)
    assert abs(float(perp @ v)) < 1e-6
    assert torch.allclose(perp.norm(), torch.tensor(1.0), atol=1e-6)


def test_orthogonalize_leaves_an_already_orthogonal_candidate_pointing_the_same_way():
    w = torch.tensor([1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0])
    v = torch.tensor([0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0])
    assert torch.allclose(construct_switch.orthogonalize(w, v), w, atol=1e-6)


# ------------------------------------------------------------ D38.5's dual read-back


def residual_batch() -> torch.Tensor:
    torch.manual_seed(1)
    return torch.randn(1, 6, D_MODEL) * 3.0


def test_lambda_0_is_an_exact_return_no_op_with_nothing_to_certify():
    """`D27`/`D28`, inherited: the λ = 0 path hands back the identical tensor object, so
    inertness is true **by construction** rather than by a hoped-for bit-identity."""
    attestation = construct_switch.DualAttestation()
    edits = construct_switch.dual_dose_edits({9: torch.randn(D_MODEL)}, None, 0.0, attestation)
    h = residual_batch()
    assert edits[9](h) is h
    assert attestation.checks == 0
    attestation.resolve()
    assert attestation.worst_survival == 0.0


def test_the_dual_readback_certifies_both_halves_on_a_real_edit():
    torch.manual_seed(2)
    v = torch.randn(D_MODEL)
    w = construct_switch.orthogonalize(torch.randn(D_MODEL), v)
    attestation = construct_switch.DualAttestation()
    edits = construct_switch.dual_dose_edits({9: w}, {9: v}, 1.0, attestation)
    h = residual_batch()
    out = edits[9](h)

    unit_w = w / w.norm()
    unit_v = v / v.norm()
    assert torch.allclose(out[0] @ unit_w, torch.zeros(6), atol=1e-5)
    assert torch.allclose(out[0] @ unit_v, h[0] @ unit_v, atol=1e-5)

    attestation.resolve()
    assert attestation.preservation_checked is True
    assert attestation.worst_survival < intervene.READBACK_TOL
    assert attestation.worst_preservation < intervene.READBACK_TOL
    assert attestation.removed_mass_mean > 0.0


def test_the_preservation_half_aborts_on_an_unorthogonalized_direction():
    """The case (b) exists for. Removing a direction that overlaps `v_secret` moves the
    secret's own projection, so the rise it produced could not be distinguished from
    deleting `v_secret` — `D34`'s guarantee would be a claim rather than a proof."""
    torch.manual_seed(3)
    v = torch.randn(D_MODEL)
    attestation = construct_switch.DualAttestation()
    edits = construct_switch.dual_dose_edits({9: v.clone()}, {9: v}, 1.0, attestation)
    edits[9](residual_batch())
    with pytest.raises(SystemExit) as exit_info:
        attestation.resolve()
    assert exit_info.value.code == 2


def test_an_unorthogonalized_arm_records_the_preservation_check_as_not_made():
    """`D31`'s reported control is not orthogonalized by design. "Not claimed" and "claimed
    and held" must not collapse into one field — the gate's arm 10 turns on the difference."""
    torch.manual_seed(4)
    attestation = construct_switch.DualAttestation()
    edits = construct_switch.dual_dose_edits({9: torch.randn(D_MODEL)}, None, 1.0, attestation)
    edits[9](residual_batch())
    attestation.resolve()
    assert attestation.preservation_checked is False

    readback = construct_switch.SwitchReadback(orthogonalized=False)
    readback.absorb(attestation)
    assert readback.payload()["worst_preservation_residual"] is None
    assert readback.payload()["orthogonalized"] is False
    assert readback.payload()["readback_checks"] > 0


def test_the_readback_resolves_at_the_trial_boundary_not_per_forward():
    """M2's measured granularity lesson: the maxima accumulate on the accelerator and sync
    once per trial. The check is unchanged — still the max over every position of every
    edited layer of every forward pass — so a violation hidden in the first of five forwards
    must still abort."""
    torch.manual_seed(5)
    v = torch.randn(D_MODEL)
    w = construct_switch.orthogonalize(torch.randn(D_MODEL), v)
    attestation = construct_switch.DualAttestation()
    clean = construct_switch.dual_dose_edits({9: w}, {9: v}, 1.0, attestation)
    dirty = construct_switch.dual_dose_edits({9: v.clone()}, {9: v}, 1.0, attestation)
    dirty[9](residual_batch())
    for _ in range(4):
        clean[9](residual_batch())
    with pytest.raises(SystemExit):
        attestation.resolve()


def test_the_readback_absorb_enforces_the_tolerance_it_records():
    """`intervene.ArmReadback`'s discipline: a caller cannot roll up an unchecked residual
    by forgetting a step, because `absorb` resolves first."""
    torch.manual_seed(6)
    v = torch.randn(D_MODEL)
    attestation = construct_switch.DualAttestation()
    construct_switch.dual_dose_edits({9: v.clone()}, {9: v}, 1.0, attestation)[9](residual_batch())
    with pytest.raises(SystemExit):
        construct_switch.SwitchReadback().absorb(attestation)


# ------------------------------------------------------------------- the provenance


def test_the_provenance_table_round_trips_and_is_read_at_call_time(tmp_path, monkeypatch):
    """`PROVENANCE_PATH` is resolved at call time rather than bound as a default argument,
    so `gates/g4.py`'s arm 7 can be tested without writing into the tracked file it guards."""
    monkeypatch.setattr(construct_switch, "PROVENANCE_PATH", tmp_path / "PROVENANCE.md")
    monkeypatch.setattr(construct_switch, "DIRECTIONS", tmp_path)
    rows = {
        "qwen2.5-0.5b-instruct.pt": {
            "file_sha256": "1" * 64, "real_sha256": "2" * 64, "sham_sha256": "3" * 64
        }
    }
    construct_switch.write_provenance(rows)
    assert construct_switch.read_provenance() == rows


def test_the_provenance_table_is_rewritten_whole_so_a_stale_row_cannot_survive(
    tmp_path, monkeypatch
):
    """The file is a record of what is on disk. A re-run of one scale must not leave a row
    for a candidate that no longer exists — two records that can drift are one too many."""
    monkeypatch.setattr(construct_switch, "PROVENANCE_PATH", tmp_path / "PROVENANCE.md")
    monkeypatch.setattr(construct_switch, "DIRECTIONS", tmp_path)
    construct_switch.write_provenance({
        "a.pt": {"file_sha256": "1" * 64, "real_sha256": "2" * 64, "sham_sha256": "3" * 64},
        "b.pt": {"file_sha256": "4" * 64, "real_sha256": "5" * 64, "sham_sha256": "6" * 64},
    })
    construct_switch.write_provenance({
        "a.pt": {"file_sha256": "7" * 64, "real_sha256": "8" * 64, "sham_sha256": "9" * 64},
    })
    table = construct_switch.read_provenance()
    assert set(table) == {"a.pt"}
    assert table["a.pt"]["file_sha256"] == "7" * 64


def test_the_direction_digest_is_of_the_matrix_not_the_container():
    """A re-save must not change the fingerprint, and a changed direction must not hide
    behind one — which is why the SHA256 is taken over the float32 matrix bytes."""
    matrix = np.arange(12, dtype=np.float32).reshape(3, 4)
    assert construct_switch.direction_sha256(matrix) == construct_switch.direction_sha256(
        matrix.copy()
    )
    moved = matrix.copy()
    moved[0, 0] += 1.0
    assert construct_switch.direction_sha256(moved) != construct_switch.direction_sha256(matrix)


def test_the_sham_records_its_composition_rather_than_asserting_it_is_matched():
    """PR #13, review F1. `construct()`'s two sides are composition-matched by construction;
    `permuted_sham()`'s free shuffle does **not** preserve `(secret, tier, text)` composition,
    and the artifact must measure that rather than claim its absence in prose.

    Built so the asymmetry is visible: two triples, and a hand-chosen split that puts both of
    one triple's sessions on side A. `composition_matched` must report False, and the tier
    counts must show the imbalance.
    """
    keys = [("gold", "T1", 0), ("iron", "T2", 0)]
    index = {
        ("with_secret", "gold", "T1", 0): 0,
        ("no_secret", "gold", "T1", 0): 1,
        ("with_secret", "iron", "T2", 0): 2,
        ("no_secret", "iron", "T2", 0): 3,
    }
    cell = construct_switch._side_composition(index, keys, [0, 1], [2, 3])
    assert cell["composition_matched"] is False
    assert cell["triples_on_both_sides"] == 0 and cell["n_triples"] == 2
    assert cell["side_a"]["tiers"] == {"T1": 2, "T2": 0}
    assert cell["side_b"]["tiers"] == {"T1": 0, "T2": 2}
    assert cell["side_a"]["arms"] == {"with_secret": 1, "no_secret": 1}


def test_a_composition_matched_split_is_reported_as_matched():
    """The other direction, so the flag means something: one session per triple per side —
    what `construct()` does, and what a within-triple flip would do — reports True."""
    keys = [("gold", "T1", 0), ("iron", "T2", 0)]
    index = {
        ("with_secret", "gold", "T1", 0): 0,
        ("no_secret", "gold", "T1", 0): 1,
        ("with_secret", "iron", "T2", 0): 2,
        ("no_secret", "iron", "T2", 0): 3,
    }
    cell = construct_switch._side_composition(index, keys, [0, 3], [1, 2])
    assert cell["composition_matched"] is True
    assert cell["triples_on_both_sides"] == 2
    assert cell["side_a"]["tiers"] == cell["side_b"]["tiers"] == {"T1": 1, "T2": 1}


def test_the_recorded_sham_rule_no_longer_claims_composition_matching():
    """The claim the review corrected, pinned so it cannot drift back. The emitted rule must
    state what the shuffle does **and** what it does not preserve."""
    keys = [("gold", "T1", 0), ("iron", "T1", 0)]
    index = {
        ("with_secret", "gold", "T1", 0): 0,
        ("no_secret", "gold", "T1", 0): 1,
        ("with_secret", "iron", "T1", 0): 2,
        ("no_secret", "iron", "T1", 0): 3,
    }
    data = sidecar([block(4.0), block(1.0), block(2.0), block(3.0)], [1, 1, 1, 1])
    _, note = construct_switch.permuted_sham(data, index, keys, seed=m3_cells.PERMUTATION_SEED)
    assert "does NOT match (secret, tier, text) composition" in note["rule"]
    assert "differs only in the labels" not in note["rule"]
    assert "composition" in note and "composition_matched" in note["composition"]


def test_composition_matched_is_false_when_the_labels_are_unevenly_dealt():
    """PR #13, review F8. The free shuffle does not deal the labels evenly, and a side with a
    net with-secret surplus carries **that fraction of the real contrast** — so the sham is
    not orthogonal to the candidate. The first version of this flag computed `arms` and then
    ignored it, so it would have reported `true` on the split below: composition perfect on
    every other axis, labels 2-0 against 0-2.

    Measured on the frozen artifacts, the realized surplus is +10.0% at 0.5B (median
    `cos(real, sham)` +0.164), −2.6% at 1.5B and +5.6% at 3B.
    """
    keys = [("gold", "T1", 0), ("iron", "T1", 0)]
    index = {
        ("with_secret", "gold", "T1", 0): 0,
        ("no_secret", "gold", "T1", 0): 1,
        ("with_secret", "iron", "T1", 0): 2,
        ("no_secret", "iron", "T1", 0): 3,
    }
    # Both with-secret rows on side A, both no-secret on side B: tiers and text_index match
    # exactly and every triple appears on both sides, so only the label check can catch it.
    cell = construct_switch._side_composition(index, keys, [0, 2], [1, 3])
    assert cell["side_a"]["tiers"] == cell["side_b"]["tiers"]
    assert cell["side_a"]["text_index"] == cell["side_b"]["text_index"]
    assert cell["triples_on_both_sides"] == cell["n_triples"]
    assert cell["label_balance"]["balanced"] is False
    assert cell["label_balance"]["side_a_net_with_secret"] == 2
    assert cell["label_balance"]["net_fraction_of_real_contrast"] == 1.0
    assert cell["composition_matched"] is False, (
        "a label-imbalanced sham must never report composition_matched"
    )


def test_label_balance_is_reported_even_when_everything_matches():
    """The mirror: a balanced, composition-matched split reports a zero net surplus, so the
    field distinguishes 'measured and zero' from 'not measured'."""
    keys = [("gold", "T1", 0), ("iron", "T1", 0)]
    index = {
        ("with_secret", "gold", "T1", 0): 0,
        ("no_secret", "gold", "T1", 0): 1,
        ("with_secret", "iron", "T1", 0): 2,
        ("no_secret", "iron", "T1", 0): 3,
    }
    cell = construct_switch._side_composition(index, keys, [0, 3], [1, 2])
    assert cell["label_balance"]["balanced"] is True
    assert cell["label_balance"]["net_fraction_of_real_contrast"] == 0.0
    assert cell["composition_matched"] is True

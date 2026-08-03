"""`intervene.py` — the ported operator, its read-back, and the frozen random control.

The house lesson this suite is written against: **every defect in this project has been a
proxy standing in for the thing it approximates.** So the operator's properties are tested
as arithmetic on real tensors, `D28`'s exact-return claim is tested through the
**production** hook context manager on a real model against the model's own generation,
and the read-back is tested by feeding it an edit that lies — not by reading the code that
computes it.
"""

from __future__ import annotations

import hashlib

import pytest
import torch

import intervene

D_MODEL = 64
SEQ = 7
MODEL = "Qwen/Qwen2.5-0.5B-Instruct"


@pytest.fixture
def block():
    torch.manual_seed(0)
    return torch.randn(SEQ, D_MODEL)


@pytest.fixture
def direction():
    torch.manual_seed(1)
    v = torch.randn(D_MODEL)
    return v / v.norm()


# ------------------------------------------------------------------ inherited constants


def test_the_inherited_constants_are_the_frozen_ones():
    """`K6`/`D27`/`D30`.4: the grid, the tolerance and the collapse share are inherited,
    not chosen here. A drift in any of them is a different instrument."""
    assert intervene.DOSE_GRID == (0.0, 0.25, 0.5, 0.75, 1.0)
    assert intervene.DECIDING_DOSE == 1.0
    assert intervene.READBACK_TOL == 1e-4
    assert intervene.COLLAPSE_SHARE == 0.5
    assert intervene.RANDOM_SEED == 20260803


# ----------------------------------------------------------------------- the operator


@pytest.mark.parametrize("lam", intervene.DOSE_GRID)
def test_the_dose_operator_leaves_one_minus_lambda_of_the_projection(block, direction, lam):
    """`K6`: `h' = h − λ(v̂ᵀh)v̂`, so `v̂ᵀh' = (1 − λ)(v̂ᵀh)` exactly. This is the property
    the runtime read-back checks; testing it here means the read-back and the operator are
    not proved by each other."""
    out = intervene.partial_project_out(block, direction, lam)
    before = block @ direction
    after = out @ direction
    assert torch.allclose(after, (1.0 - lam) * before, atol=1e-5)


def test_the_orthogonal_complement_is_untouched(block, direction):
    """The edit is minimal-norm: everything orthogonal to `v̂` survives unchanged."""
    out = intervene.partial_project_out(block, direction, 1.0)
    removed = block - out
    # every removed row is parallel to the direction
    assert torch.allclose(removed - (removed @ direction).unsqueeze(-1) * direction,
                          torch.zeros_like(removed), atol=1e-5)


def test_the_operator_normalizes_the_direction_itself(block):
    """A caller cannot silently change the operator by handing in an unnormalized vector:
    `D27`'s `v̂` is unit by definition, so scaling the input must not scale the edit."""
    torch.manual_seed(2)
    v = torch.randn(D_MODEL)
    a = intervene.partial_project_out(block, v, 1.0)
    b = intervene.partial_project_out(block, v * 37.0, 1.0)
    assert torch.allclose(a, b, atol=1e-5)


def test_fp32_and_the_ported_float64_path_agree(block, direction):
    """`D27`'s implementation freedom is bounded by the read-back, and the two paths must
    be the same operator — otherwise "fall back to float64" would be a design change."""
    fast = intervene.partial_project_out(block, direction, 1.0, float64=False)
    exact = intervene.partial_project_out(block, direction, 1.0, float64=True)
    assert torch.allclose(fast, exact, atol=1e-5)


# ------------------------------------------------------------------- the span operator


def test_span_ablation_with_k_zero_is_an_exact_no_op(block):
    """`mute-map/intervention.py:49`'s stated property, and what makes `D33`.3's
    degenerate span (a secret with no distinct capitalized row) a well-defined case."""
    out = intervene.ablate(block, torch.zeros((0, D_MODEL)))
    assert out is block or torch.equal(out, block)


def test_span_ablation_with_one_direction_equals_the_dose_operator_at_lambda_one(
    block, direction
):
    """`D33`.3: for the 13 eval secrets with no distinct capitalized row the span arm
    **is** the primary edit. Tested rather than asserted in prose."""
    span = intervene.ablate(block, direction.unsqueeze(0))
    dose = intervene.partial_project_out(block, direction, 1.0, float64=True)
    assert torch.allclose(span, dose, atol=1e-9)


def test_span_ablation_zeroes_both_non_orthogonal_directions_simultaneously(block):
    """The reason the span arm is a span and not two sequential edits: one-at-a-time
    zeroing of non-orthogonal directions does not leave both coordinates at zero."""
    torch.manual_seed(3)
    a = torch.randn(D_MODEL)
    a = a / a.norm()
    b = a + 0.4 * torch.randn(D_MODEL)
    b = b / b.norm()
    directions = torch.stack([a, b])
    out = intervene.ablate(block, directions)
    # The relative form the read-back itself uses: the operator computes in float64 and
    # returns in the input's dtype, so the surviving coordinate is fp32 rounding, not a
    # failure to remove the span.
    norms = block.norm(dim=-1, keepdim=True)
    assert ((out @ directions.T).abs() / norms).max() < intervene.READBACK_TOL

    sequential = intervene.partial_project_out(block, a, 1.0, float64=True)
    sequential = intervene.partial_project_out(sequential, b, 1.0, float64=True)
    assert (sequential @ a).abs().max() > 1e-6  # the first coordinate came back


# ------------------------------------------------------------------- λ = 0 exact return


def test_lambda_zero_edits_return_the_identical_tensor(direction):
    """`D27`/`D28`: **exact-return by construction.** Not "close", not "bit-identical
    after a float64 round trip" — the same object, so no arithmetic exists to drift. This
    is what gives `D28`'s byte-identity check against M0 an unambiguous meaning."""
    attestation = intervene.EditAttestation()
    edits = intervene.dose_edits({3: direction, 4: direction}, 0.0, attestation)
    h = torch.randn(1, SEQ, D_MODEL)
    for edit in edits.values():
        assert edit(h) is h
    assert attestation.checks == 0
    assert attestation.removed_mass_mean == 0.0


def test_lambda_zero_records_no_readback_checks_but_says_so(direction):
    """A payload must not be able to present "zero read-back checks" as "checks passed".
    `ArmReadback.exact_return` is the field that distinguishes them (`D27`/`D32`)."""
    readback = intervene.ArmReadback(exact_return=True)
    readback.absorb(intervene.EditAttestation())
    assert readback.payload() == {
        "tol": intervene.READBACK_TOL,
        "worst_residual": 0.0,
        "readback_checks": 0,
        "exact_return": True,
    }


# ----------------------------------------------------------------------- the read-back


def test_the_readback_accepts_the_real_operator(direction):
    """A live λ > 0 edit passes and records its worst residual and removed mass."""
    attestation = intervene.EditAttestation()
    edits = intervene.dose_edits({0: direction}, 1.0, attestation)
    torch.manual_seed(4)
    h = torch.randn(1, SEQ, D_MODEL)
    out = edits[0](h)
    assert out.shape == h.shape
    assert (out[0] @ direction).abs().max() < 1e-4
    assert attestation.checks == 1
    # The maxima stay on the accelerator until the trial boundary; `resolve` is the one
    # sync, and it is what enforces the tolerance.
    assert attestation.worst_residual == 0.0 and attestation.pending_residual
    attestation.resolve()
    assert attestation.worst_residual <= intervene.READBACK_TOL
    assert not attestation.pending_residual
    assert attestation.removed_sq_count == SEQ
    expected = float((h[0] @ direction).pow(2).mean())
    assert attestation.removed_mass_mean == pytest.approx(expected, rel=1e-5)


def test_the_readback_rejects_an_edit_that_lies(monkeypatch, direction):
    """The read-back is the acceptance test for the whole λ > 0 path (`D27`/`D28`'s
    division of labor), so it is tested by making the operator wrong — a half-dose edit
    presented as a full one — rather than by reading it.

    `probe.fail` exits 2 with `VERDICT: INVALID`, the inherited stop-condition mechanism.
    """
    real = intervene.partial_project_out
    monkeypatch.setattr(
        intervene,
        "partial_project_out",
        lambda h, v, lam, **kw: real(h, v, 0.5 * lam, **kw),
    )
    attestation = intervene.EditAttestation()
    edits = intervene.dose_edits({0: direction}, 1.0, attestation)
    edits[0](torch.randn(1, SEQ, D_MODEL))
    with pytest.raises(SystemExit) as excinfo:
        attestation.resolve()
    assert excinfo.value.code == 2


def test_the_span_readback_rejects_an_edit_that_lies(monkeypatch):
    torch.manual_seed(5)
    basis = torch.randn(2, D_MODEL)
    basis = basis / basis.norm(dim=-1, keepdim=True)
    monkeypatch.setattr(intervene, "ablate", lambda h, directions: h)
    attestation = intervene.EditAttestation()
    edits = intervene.span_edits({0: basis}, attestation)
    edits[0](torch.randn(1, SEQ, D_MODEL))
    with pytest.raises(SystemExit) as excinfo:
        attestation.resolve()
    assert excinfo.value.code == 2


# ------------------------------------------------------------- D31: the random control


def test_random_directions_are_unit_norm_and_reproducible_from_the_seed():
    words, layers = ["gold", "ruby"], [11, 9, 10]
    first, digest = intervene.random_directions(words, layers, D_MODEL)
    second, digest2 = intervene.random_directions(words, layers, D_MODEL)
    assert digest == digest2
    assert set(first) == {(w, l) for w in words for l in layers}
    for vector in first.values():
        assert vector.dtype is torch.float32
        assert float(vector.norm()) == pytest.approx(1.0, abs=1e-6)
    for key in first:
        assert torch.equal(first[key], second[key])


def test_the_random_draw_order_is_the_frozen_one():
    """`D31`: eval secrets in battery order × band layers **ascending**. The layers are
    passed unsorted here on purpose — a dict's iteration order must not be able to change
    which Gaussian a layer gets."""
    words, layers = ["gold", "ruby"], [11, 9, 10]
    drawn, _ = intervene.random_directions(words, layers, D_MODEL)
    generator = torch.Generator().manual_seed(intervene.RANDOM_SEED)
    for word in words:
        for layer in sorted(layers):
            expected = torch.randn(D_MODEL, generator=generator, dtype=torch.float32)
            expected = expected / expected.norm()
            assert torch.equal(drawn[(word, layer)], expected)


def test_the_recorded_hash_is_the_hash_of_the_stacked_matrix():
    """`D31`: the directions are reproducible from seed + order; the hash is what makes
    drift detectable, so it must be the hash of the thing that drifts."""
    words, layers = ["gold", "ruby"], [9, 10]
    drawn, digest = intervene.random_directions(words, layers, D_MODEL)
    stacked = torch.stack([drawn[(w, l)] for w in words for l in sorted(layers)])
    assert digest == hashlib.sha256(stacked.contiguous().numpy().tobytes()).hexdigest()


def test_different_secrets_and_layers_get_different_directions():
    drawn, _ = intervene.random_directions(["gold", "ruby"], [9, 10], D_MODEL)
    vectors = list(drawn.values())
    for i, a in enumerate(vectors):
        for b in vectors[i + 1 :]:
            assert not torch.equal(a, b)


def test_random_directions_are_device_independent_by_construction():
    """A control whose directions depended on where the run happened would not be the same
    control across scales. The generator is a CPU generator; this pins that."""
    drawn, _ = intervene.random_directions(["gold"], [9], D_MODEL)
    assert drawn[("gold", 9)].device.type == "cpu"


# ------------------------------------------------------------ D30.4: the collapse guard


def test_degeneracy_flags_a_collapsed_turn(tokenizer):
    ids = [100] * 5 + [101] * 5
    assert intervene.degeneracy(ids, tokenizer)["collapsed"] is True
    assert intervene.degeneracy(ids, tokenizer)["share"] == 0.5
    assert intervene.degeneracy([100] * 4 + [101] * 6, tokenizer)["share"] == 0.6


def test_degeneracy_leaves_a_varied_turn_alone(tokenizer):
    record = intervene.degeneracy(list(range(100, 120)), tokenizer)
    assert record["collapsed"] is False
    assert record["share"] == 0.05
    assert record["attractor_token"] is not None


def test_degeneracy_handles_an_empty_turn(tokenizer):
    assert intervene.degeneracy([], tokenizer) == {
        "attractor_token": None, "share": 0.0, "collapsed": False
    }


def test_a_trial_is_collapsed_iff_any_turn_is():
    turns = [{"collapsed": False}, {"collapsed": True}, {"collapsed": False}]
    assert intervene.trial_collapsed(turns) is True
    assert intervene.trial_collapsed([{"collapsed": False}] * 3) is False


# ------------------------------------------------------------------ precision preflight


def test_forced_precision_modes_skip_the_probe(block, direction):
    for mode, float64 in (("fp32", False), ("float64", True)):
        precision = intervene.preflight_precision(
            {0: block}, {0: direction}, requested=mode
        )
        assert precision.float64 is float64
        assert precision.chosen_by == f"forced:{mode}"
        assert precision.fallback_used is False
    with pytest.raises(ValueError):
        intervene.preflight_precision({0: block}, {0: direction}, requested="quad")


def test_the_preflight_picks_fp32_when_it_holds(block, direction):
    precision = intervene.preflight_precision(
        {0: block, 1: block}, {0: direction, 1: direction}
    )
    assert precision.float64 is False
    assert precision.fallback_used is False
    assert precision.probe_worst_residual <= intervene.READBACK_TOL
    assert precision.payload()["edit_dtype"] == "device_fp32"


def test_the_preflight_falls_back_to_float64_when_fp32_cannot_hold(
    monkeypatch, block, direction
):
    """`D27`'s pre-authorized fallback, chosen **once** before any trial so that no payload
    ever mixes two arithmetics across its arms."""
    real = intervene.partial_project_out

    def flaky(h, v, lam, *, float64=False):
        out = real(h, v, lam, float64=float64)
        return out if float64 else out + 1e-2

    monkeypatch.setattr(intervene, "partial_project_out", flaky)
    precision = intervene.preflight_precision({0: block}, {0: direction})
    assert precision.float64 is True
    assert precision.fallback_used is True
    assert precision.payload()["edit_dtype"] == "cpu_float64"


def test_the_preflight_stops_the_run_when_neither_path_holds(monkeypatch, block, direction):
    monkeypatch.setattr(intervene, "partial_project_out", lambda h, v, lam, **kw: h + 1.0)
    with pytest.raises(SystemExit) as excinfo:
        intervene.preflight_precision({0: block}, {0: direction})
    assert excinfo.value.code == 2


# --------------------------------------------------- the hook, against a real model


@pytest.fixture(scope="module")
def subject():
    transformers = pytest.importorskip("transformers")
    model = transformers.AutoModelForCausalLM.from_pretrained(MODEL, dtype=torch.float32)
    model.eval()
    return model, transformers.AutoTokenizer.from_pretrained(MODEL)


def _generate(model, tokenizer, edits):
    prompt = tokenizer("The public word is silver. The secret word is",
                       return_tensors="pt").input_ids
    with intervene.edit_residuals(model.model.layers, edits):
        with torch.no_grad():
            out = model.generate(
                prompt, max_new_tokens=16, do_sample=False,
                pad_token_id=tokenizer.pad_token_id or tokenizer.eos_token_id,
            )
    return out[0, prompt.shape[1]:].tolist()


def test_lambda_zero_through_the_production_hook_is_bitwise_inert(subject):
    """`D28`'s certification, tested on the substrate rather than assumed.

    The λ = 0 arm runs the full runner with hooks **installed**; what makes its
    byte-identity check against M0 meaningful is that the edit path cannot perturb the
    generation. Proven here by generating with the hooks installed at every band layer and
    requiring the token sequence to equal the unhooked one exactly.
    """
    model, tokenizer = subject
    band = probe_band(model)
    directions = {layer: torch.randn(model.config.hidden_size) for layer in band}
    for vector in directions.values():
        vector /= vector.norm()

    clean = _generate(model, tokenizer, {})
    hooked = _generate(
        model, tokenizer, intervene.dose_edits(directions, 0.0, intervene.EditAttestation())
    )
    assert hooked == clean


def test_lambda_one_through_the_production_hook_changes_the_generation(subject):
    """The mirror of the test above: the same hook at λ = 1 is *not* inert. Without this,
    a hook that silently failed to install would pass the inertness test perfectly."""
    model, tokenizer = subject
    band = probe_band(model)
    torch.manual_seed(7)
    directions = {}
    for layer in band:
        vector = torch.randn(model.config.hidden_size)
        directions[layer] = vector / vector.norm()

    attestation = intervene.EditAttestation()
    clean = _generate(model, tokenizer, {})
    edited = _generate(model, tokenizer, intervene.dose_edits(directions, 1.0, attestation))
    attestation.resolve()
    assert attestation.checks > 0
    assert attestation.worst_residual <= intervene.READBACK_TOL
    assert attestation.removed_mass_mean > 0.0
    assert edited != clean or attestation.removed_mass_mean == 0.0


def probe_band(model):
    import probe as probe_module

    return probe_module.validated_band(model.config.num_hidden_layers)


def test_absorbing_an_attestation_resolves_it(direction):
    """`ArmReadback.absorb` resolves first, so a caller cannot roll an **unchecked**
    residual into the payload by forgetting a step — the tolerance is enforced by the same
    call that records it."""
    attestation = intervene.EditAttestation()
    edits = intervene.dose_edits({0: direction}, 1.0, attestation)
    edits[0](torch.randn(1, SEQ, D_MODEL))
    readback = intervene.ArmReadback()
    readback.absorb(attestation)
    assert readback.checks == 1
    assert 0.0 <= readback.worst_residual <= intervene.READBACK_TOL
    assert not attestation.pending_residual


def test_a_violation_anywhere_in_a_trial_survives_to_the_resolve(monkeypatch, direction):
    """Deferring the sync must not lose a violation that happened on an earlier forward
    pass: the running maximum is over **every** position of every edited layer of every
    forward, exactly as before."""
    real = intervene.partial_project_out
    calls = {"n": 0}

    def sometimes_wrong(h, v, lam, **kw):
        calls["n"] += 1
        out = real(h, v, lam, **kw)
        return out + 1.0 if calls["n"] == 1 else out  # only the FIRST forward is wrong

    monkeypatch.setattr(intervene, "partial_project_out", sometimes_wrong)
    attestation = intervene.EditAttestation()
    edits = intervene.dose_edits({0: direction}, 1.0, attestation)
    for _ in range(5):
        edits[0](torch.randn(1, SEQ, D_MODEL))
    with pytest.raises(SystemExit) as excinfo:
        attestation.resolve()
    assert excinfo.value.code == 2

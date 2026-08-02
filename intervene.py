"""intervene.py — M2's intervention module: `K6`'s dose operator, its read-back, the
span operator, and the frozen-seed random-direction constructor.

**A deliberate, documented port** (the `stats.py` precedent), cited line-by-line against
the working trees the M2 brief's design-extraction table verified on 2026-08-02:

| here | source |
|---|---|
| `partial_project_out` | `mute-map/m2_depth.py:415-431` |
| `dose_edits`'s read-back | `mute-map/m2_depth.py:433-465` (`partial_ablation_edits`) |
| `READBACK_TOL` | `mute-map/harness.py:33` |
| `DOSE_GRID` | `mute-map/m2_depth.py:112`; `K6`; `KICKOFF.md` §Inputs |
| `ablate` (modified Gram-Schmidt, exact `k = 0` no-op) | `mute-map/intervention.py:49` |
| `edit_residuals` | `mute-map/intervention.py:94-120` |
| `degeneracy`, `COLLAPSE_SHARE` | `mute-map/harness.py:35, 91-101` |
| the random-direction control's seed discipline | `dim-stage/s3_selectivity.py:87`, `:259-305` |
| application point (block **output** residual, every band layer, own `J_l`) | `dim-stage/intervention.py:35-38`; `mute-map/subject.py:99-111`; `K6` |

**What is not a port, and is therefore owned in the brief** (`D31`): the random arm's
**draw granularity**. S3 draws fresh Gaussians per position on every forward pass, inside
the edit closure; `D31` draws **one direction per (secret, layer)** and reuses it across
positions, turns and trials — because the real arm removes the *same* fixed `v̂_l(w)`
everywhere, and a control that changed direction per position would be a different kind of
intervention than the one it controls for.

**λ = 0 is an exact-return no-op by construction** (`D27`/`D28`). `dose_edits(…, lam=0)`
returns closures that hand back the identical tensor object — no arithmetic runs at all.
This is the load-bearing half of `D28`'s division of labor: inertness is true *by
construction* rather than by a hoped-for bit-identity of a float64 round trip, so `D28`'s
byte-identity check against M0 has an unambiguous meaning, and the **read-back** is what
separately certifies the live path at every λ > 0.

**Precision.** `mute-map` computed the edit in CPU float64 — a numerical necessity for its
ill-conditioned k-direction spans, not for `k = 1`. `D27` licenses keeping the `k = 1`
edit on-device in fp32 with the **read-back as the acceptance test**, and pre-authorizes
the exact ported CPU-float64 path as the fallback. `preflight_precision` below chooses
between them **once, before any trial**, and the choice is recorded in the payload: a
mid-sweep switch would leave two arms of one payload computed by different arithmetic,
which is the substrate heterogeneity this project refuses everywhere else.

The **span** operator keeps the ported CPU-float64 path unconditionally: float64 is
exactly what `mute-map/intervention.py:49` cites as the reason MGS is used there, and the
span arm is one arm of 100 trials.
"""

from __future__ import annotations

import hashlib
from collections import Counter
from collections.abc import Callable, Sequence
from contextlib import contextmanager
from dataclasses import dataclass, field

import torch
from torch import nn

import probe

#: `mute-map/harness.py:33` — relative `|⟨v̂, h'⟩ − (1−λ)⟨v̂, h⟩| / ‖h‖` ceiling, fp32
#: headroom. The runtime acceptance test for every λ > 0 edit (`D27`).
READBACK_TOL = 1e-4

#: `mute-map/m2_depth.py:112` (`DOSE_GRID`), `K6`, `KICKOFF.md` §Inputs — inherited frozen.
DOSE_GRID: tuple[float, ...] = (0.0, 0.25, 0.5, 0.75, 1.0)

#: `D27`: the deciding dose. The interior points feed `D33`.1's dose curve and decide
#: nothing.
DECIDING_DOSE = 1.0

#: `mute-map/harness.py:35` — the S1/S2 degeneracy convention, `D30`.4's collapse guard.
COLLAPSE_SHARE = 0.5

#: `mute-map/intervention.py` — relative residual floor for the span basis: a direction
#: whose component orthogonal to the accepted basis falls below this fraction of its own
#: norm is numerically inside their span and is dropped (its coordinate is removed by the
#: others).
RANK_TOLERANCE = 1e-10

#: `D31`: the random-direction control's frozen seed. One `torch.Generator` per scale,
#: frozen draw order (eval secrets in battery order × band layers ascending).
RANDOM_SEED = 20260803

Edit = Callable[[torch.Tensor], torch.Tensor]


# ------------------------------------------------------------------ the attestation


@dataclass
class EditAttestation:
    """What an arm's edits attest to, accumulated across forward passes.

    `D27` requires the payload to record **the worst observed read-back residual per
    arm**, and `D31` requires **per-trial `removed_mass_mean`**; a payload missing either
    is `INVALID` at the gate (`D32`). Both are facts only the edit closure can see, so
    they are accumulated here rather than reconstructed.

    `removed_mass_mean` is the mean of `λ²(v̂ᵀh)²` over edited layers × positions — the
    squared norm of the vector the operator actually removes. At the deciding dose λ = 1
    that is exactly the brief's `(v̂ᵀh)²`, which is where `D31`'s real-vs-random asymmetry
    is read; at λ = 0 it is 0, which is the value the exact-return path makes true by
    construction rather than a placeholder standing in for an uncomputed quantity.

    **Accumulated on the accelerator, resolved once per trial.** The check is unchanged —
    still the max over **every** position of **every** edited layer of **every** forward
    pass — but reading it with `float()` inside the closure would force one device
    synchronization per band layer per generated token. M1 measured exactly that pattern
    at ~4× the uncaptured generation time against an estimate of ≤50%
    (`probe.capture_band_cosines`), so the running maxima stay as device tensors and
    `resolve()` syncs them once, at the trial boundary. What changes is when the abort
    fires (at the end of the offending trial rather than mid-generation), not what it
    fires on.
    """

    tol: float = READBACK_TOL
    worst_residual: float = 0.0
    removed_sq_sum: float = 0.0
    removed_sq_count: int = 0
    #: The span arm removes a span rather than one direction, so its read-back is the
    #: λ = 1 "surviving projection is zero" form on **every** basis direction.
    checks: int = 0
    #: Per-layer running maxima / sums, still on the accelerator. Kept per layer so a
    #: failure can name the layer without a sync on the happy path.
    pending_residual: dict[int, torch.Tensor] = field(default_factory=dict)
    pending_removed: dict[int, torch.Tensor] = field(default_factory=dict)

    def note(self, layer: int, worst: torch.Tensor, removed_sq: torch.Tensor, count: int) -> None:
        previous = self.pending_residual.get(layer)
        self.pending_residual[layer] = (
            worst if previous is None else torch.maximum(previous, worst)
        )
        carried = self.pending_removed.get(layer)
        self.pending_removed[layer] = (
            removed_sq if carried is None else carried + removed_sq
        )
        self.removed_sq_count += int(count)
        self.checks += 1

    def resolve(self) -> None:
        """Sync the accumulated maxima and enforce `READBACK_TOL`. Idempotent."""
        if not self.pending_residual:
            return
        layers = sorted(self.pending_residual)
        worst = float(torch.stack([self.pending_residual[l] for l in layers]).max())
        if worst > READBACK_TOL:
            offender = max(layers, key=lambda l: float(self.pending_residual[l]))
            probe.fail(
                f"M2 read-back failed at layer {offender}: the surviving projection is off "
                f"by {worst:.2e} > {READBACK_TOL:.0e} relative — expected (1-lambda) of the "
                "original. An edit the runner cannot certify was applied is not D27's "
                "frozen operator; re-run with --edit-precision float64 for the exact ported "
                "CPU path."
            )
        self.worst_residual = max(self.worst_residual, worst)
        self.removed_sq_sum += float(
            torch.stack([self.pending_removed[l] for l in layers]).sum()
        )
        self.pending_residual.clear()
        self.pending_removed.clear()

    @property
    def removed_mass_mean(self) -> float:
        self.resolve()
        return self.removed_sq_sum / self.removed_sq_count if self.removed_sq_count else 0.0

    def reset(self) -> None:
        self.worst_residual = 0.0
        self.removed_sq_sum = 0.0
        self.removed_sq_count = 0
        self.checks = 0
        self.pending_residual.clear()
        self.pending_removed.clear()

    def snapshot(self) -> dict:
        self.resolve()
        return {
            "worst_residual": self.worst_residual,
            "removed_mass_mean": self.removed_mass_mean,
            "positions_scored": self.removed_sq_count,
            "readback_checks": self.checks,
        }


@dataclass
class ArmReadback:
    """The per-arm worst residual the payload records (`D27`), rolled up from per-trial
    attestations. Kept separate from `EditAttestation` because the attestation is reset
    per trial and this is not.

    `absorb` **resolves** the attestation first, so the tolerance is enforced at the trial
    boundary by the same call that records it — a caller cannot roll up an unchecked
    residual by forgetting a step.
    """

    tol: float = READBACK_TOL
    worst_residual: float = 0.0
    checks: int = 0
    exact_return: bool = False

    def absorb(self, attestation: EditAttestation) -> None:
        attestation.resolve()
        self.worst_residual = max(self.worst_residual, attestation.worst_residual)
        self.checks += attestation.checks

    def payload(self) -> dict:
        return {
            "tol": self.tol,
            "worst_residual": self.worst_residual,
            "readback_checks": self.checks,
            "exact_return": self.exact_return,
        }


# -------------------------------------------------------------------- the operators


def partial_project_out(
    h: torch.Tensor, direction: torch.Tensor, lam: float, *, float64: bool = False
) -> torch.Tensor:
    """`h − λ(v̂ᵀh)v̂` — `mute-map/m2_depth.py:415-431`, `K6`'s dose operator.

    `h` is `[..., d_model]`, `direction` is `[d_model]` (normalized here regardless, so a
    caller cannot silently change the operator by handing in an unnormalized vector).

    `float64=True` is the exact ported path: **move before casting**, because
    `.to("cpu", torch.float64)` in one step silently corrupts values coming off MPS
    (float64 is cast device-side, unsupported there — measured in dim-stage 2026-07-17,
    max abs diff ~5 on unit-scale data). `float64=False` is `D27`'s licensed on-device
    fp32 path, whose acceptance test is the read-back in `dose_edits`.
    """
    if float64:
        v = direction.cpu().to(torch.float64)
        b = h.cpu().to(torch.float64)
    else:
        v = direction.to(dtype=torch.float32)
        b = h.to(dtype=torch.float32)
    unit = v / v.norm().clamp_min(torch.finfo(v.dtype).tiny)
    out = b - lam * (b * unit).sum(-1, keepdim=True) * unit
    return out.to(device=h.device, dtype=h.dtype)


def ablate(h: torch.Tensor, directions: torch.Tensor) -> torch.Tensor:
    """`h` minus its projection onto `span{directions}` — `mute-map/intervention.py:49`,
    ported verbatim. `D33`.3's case-pair span arm, λ = 1 only.

    `h` is `[..., d_model]`; `directions` is `[..., k, d_model]`. Returns the unique
    minimal-norm edit of `h` whose inner product with every direction is zero —
    simultaneously, which one-at-a-time zeroing of non-orthogonal directions would not
    achieve. Modified Gram-Schmidt with re-orthogonalization, CPU float64. **`k = 0` is an
    exact no-op**, which is what makes the degenerate span (a secret with no distinct
    capitalized row) a well-defined case rather than a special one.
    """
    if directions.shape[-2] == 0:
        return h
    # Move BEFORE casting — see `partial_project_out`.
    v = directions.cpu().to(torch.float64)
    b = h.cpu().to(torch.float64)
    basis: list[torch.Tensor] = []
    for i in range(v.shape[-2]):
        vec = v[..., i, :]
        norm0 = vec.norm(dim=-1, keepdim=True)
        for _ in range(2):
            for q in basis:
                vec = vec - (vec * q).sum(-1, keepdim=True) * q
        norm = vec.norm(dim=-1, keepdim=True)
        keep = norm > norm0 * RANK_TOLERANCE
        basis.append(torch.where(keep, vec / norm.clamp_min(torch.finfo(vec.dtype).tiny), 0.0))
    for q in basis:
        b = b - (b * q).sum(-1, keepdim=True) * q
    return b.to(device=h.device, dtype=h.dtype)


# ------------------------------------------------------------------------- the edits


def dose_edits(
    directions: dict[int, torch.Tensor],
    lam: float,
    attestation: EditAttestation,
    *,
    float64: bool = False,
) -> dict[int, Edit]:
    """`K6`'s dose operator at every listed band layer, with mute-map's **generalized**
    runtime read-back — `mute-map/m2_depth.py:433-465`.

    `directions[layer]` is that layer's `[d_model]` unit direction for this trial's word.
    After the edit, the surviving projection `v̂ᵀh'` must equal `(1 − λ)(v̂ᵀh)` within
    `READBACK_TOL` relative to `‖h‖`, else the runner exits `INVALID` at run time. At
    λ = 1 that is exactly M1's "the projection is zero" check.

    **λ = 0 returns the identical tensor** (`D27`/`D28`): the edit path is exact-return,
    so nothing is computed and nothing can drift. The read-back is not run — there is no
    arithmetic to certify — and the attestation records zero checks, which `ArmReadback`
    marks `exact_return` so a reader cannot mistake "no checks" for "checks skipped".
    """
    if lam == 0.0:
        def identity(h: torch.Tensor) -> torch.Tensor:
            return h

        return {layer: identity for layer in directions}

    edits: dict[int, Edit] = {}
    for layer in directions:

        def edit(h: torch.Tensor, layer: int = layer, lam: float = lam) -> torch.Tensor:
            hs = h[0]  # [seq, d_model]
            direction = directions[layer].to(device=hs.device, dtype=torch.float32)
            out = partial_project_out(hs.float(), direction, lam, float64=float64).to(hs.dtype)
            unit = direction / direction.norm().clamp_min(1e-30)
            before = hs.float() @ unit
            after = out.float() @ unit
            norms = hs.float().norm(dim=-1).clamp_min(1e-30)
            residual = (after - (1.0 - lam) * before).abs()
            # `D31`: the removed vector is λ(v̂ᵀh)v̂, whose squared norm is λ²(v̂ᵀh)².
            # Both stay on the accelerator; `EditAttestation.resolve` syncs once per trial.
            attestation.note(
                layer, (residual / norms).max(), (lam * before).pow(2).sum(), before.numel()
            )
            return out.unsqueeze(0)

        edits[layer] = edit
    return edits


def span_edits(
    directions: dict[int, torch.Tensor], attestation: EditAttestation
) -> dict[int, Edit]:
    """`D33`.3's span arm: λ = 1 projection out of `span{directions}` at every listed band
    layer, via the ported MGS `ablate`.

    `directions[layer]` is `[k, d_model]` — `k = 1` where the secret has no distinct
    capitalized probe row (the span degenerates to the primary edit **by construction**,
    `D33`.3), `k = 2` where it does. The read-back is the λ = 1 form of `D27`'s
    generalized check, applied to **every** basis direction: the surviving projection onto
    each must be zero within `READBACK_TOL` relative to `‖h‖`.
    """
    edits: dict[int, Edit] = {}
    for layer in directions:

        def edit(h: torch.Tensor, layer: int = layer) -> torch.Tensor:
            hs = h[0]  # [seq, d_model]
            basis = directions[layer].to(device=hs.device, dtype=torch.float32)
            out = ablate(hs.float(), basis).to(hs.dtype)
            units = basis / basis.norm(dim=-1, keepdim=True).clamp_min(1e-30)
            norms = hs.float().norm(dim=-1).clamp_min(1e-30)  # [seq]
            leftover = (out.float() @ units.T).abs()  # [seq, k]
            # The removed vector is `h`'s component in the span; its squared norm is
            # `‖h‖² − ‖h'‖²`, which for an orthogonal projection is exact. Reported on the
            # same per-position footing as the dose arms' `λ²(v̂ᵀh)²`.
            removed = (hs.float().pow(2).sum(-1) - out.float().pow(2).sum(-1)).clamp_min(0.0)
            attestation.note(
                layer, (leftover / norms.unsqueeze(-1)).max(), removed.sum(), hs.shape[0]
            )
            return out.unsqueeze(0)

        edits[layer] = edit
    return edits


@contextmanager
def edit_residuals(layers: Sequence[nn.Module], edits: dict[int, Edit]):
    """Apply each edit to its block's **output** residual on every forward pass run inside
    the context — `mute-map/intervention.py:94-120` verbatim.

    Same hook point `probe.capture_producing_rows` reads (`K6`): the edited residual is
    exactly what the lens would read there and what every later layer consumes. `D27`
    applies the edit at **every** frozen-band layer, each with its own `J_l`.
    """
    handles = []

    def make_hook(edit: Edit):
        def hook(module, inputs, output):
            if torch.is_tensor(output):
                return edit(output)
            return (edit(output[0]), *output[1:])

        return hook

    try:
        for index, edit in edits.items():
            handles.append(layers[index].register_forward_hook(make_hook(edit)))
        yield
    finally:
        for handle in handles:
            handle.remove()


# ----------------------------------------------------------- D31: the random control


def random_directions(
    words: Sequence[str], layers: Sequence[int], d_model: int, *, seed: int = RANDOM_SEED
) -> tuple[dict[tuple[str, int], torch.Tensor], str]:
    """`D31`'s control: one fresh **unit-normalized** `d_model` Gaussian per
    (eval secret, band layer), from one frozen-seed generator in one frozen draw order.

    Returns `({(word, layer): [d_model] fp32 unit vector}, sha256 of the stacked matrix)`.
    The directions are reproducible from seed + order; the hash is what makes drift
    detectable, and the payload records it (`D31`).

    Drawn on the **CPU** generator so the draw is device-independent: a control whose
    directions depended on where the run happened would not be the same control across
    scales. Draw order is `words` (eval secrets in battery order) × `layers` ascending —
    frozen here rather than left to a dict's iteration order.
    """
    generator = torch.Generator().manual_seed(seed)
    ordered_layers = sorted(layers)
    out: dict[tuple[str, int], torch.Tensor] = {}
    stack: list[torch.Tensor] = []
    for word in words:
        for layer in ordered_layers:
            vector = torch.randn(d_model, generator=generator, dtype=torch.float32)
            vector = vector / vector.norm()
            out[(word, layer)] = vector
            stack.append(vector)
    matrix = torch.stack(stack) if stack else torch.zeros((0, d_model), dtype=torch.float32)
    digest = hashlib.sha256(matrix.contiguous().numpy().tobytes()).hexdigest()
    return out, digest


def draw_order_note(words: Sequence[str], layers: Sequence[int]) -> dict:
    """`D31`'s `random_directions` run-level block: seed, draw order, and the hash. The
    order is recorded as data, not prose, so a re-derivation reads it rather than
    reconstructing it from a sentence."""
    return {
        "seed": RANDOM_SEED,
        "draw_order": {"words": list(words), "layers": sorted(layers)},
        "rule": (
            "D31: one unit-normalized d_model Gaussian per (eval secret, band layer), one "
            "torch.Generator per scale on CPU, secrets in battery order x band layers "
            "ascending. Reused across positions, turns and trials — the draw-granularity "
            "departure from dim-stage/s3_selectivity.py:259-305, owned in D31."
        ),
    }


# ------------------------------------------------------- D30.4: the degeneracy guard


def degeneracy(greedy_ids: Sequence[int], tokenizer) -> dict:
    """`mute-map/harness.py:91-101` verbatim — the most common greedy token's share for
    one generated turn. Collapsed iff the share is at least `COLLAPSE_SHARE`.

    A **token-level fact recorded by the runner**: the gate recomputes collapse *rates*
    from these per-turn records and refuses missing ones, but cannot re-derive the flag
    from reply text (owned in `M2-BRIEF.md`'s deviations table, the `m1_cells.replayed_turns`
    standing). The attractor token and its share ride along for human audit.
    """
    ids = list(greedy_ids)
    if not ids:
        return {"attractor_token": None, "share": 0.0, "collapsed": False}
    token, count = Counter(ids).most_common(1)[0]
    share = count / len(ids)
    return {
        "attractor_token": tokenizer.decode([token]),
        "share": share,
        "collapsed": share >= COLLAPSE_SHARE,
    }


def trial_collapsed(turns: Sequence[dict]) -> bool:
    """`D30`.4: a trial is collapsed iff **any** of its turns is."""
    return any(turn["collapsed"] for turn in turns)


# --------------------------------------------------------------- the precision choice


@dataclass
class Precision:
    """Which arithmetic the λ > 0 dose edits run in, chosen once before any trial.

    `D27` licenses on-device fp32 with the read-back as the acceptance test and
    pre-authorizes the exact ported CPU-float64 path as the fallback. Choosing **once**,
    at preflight, is what keeps every arm of one payload computed by the same arithmetic;
    an automatic mid-sweep switch would leave a payload whose arms differ in the
    substrate rather than in the edit.
    """

    float64: bool
    chosen_by: str
    probe_worst_residual: float = 0.0
    fallback_used: bool = field(default=False)

    def payload(self) -> dict:
        return {
            "edit_dtype": "cpu_float64" if self.float64 else "device_fp32",
            "chosen_by": self.chosen_by,
            "probe_worst_residual": self.probe_worst_residual,
            "fallback_used": self.fallback_used,
            "tol": READBACK_TOL,
        }


def _probe_residual(
    hidden: torch.Tensor, direction: torch.Tensor, lam: float, *, float64: bool
) -> float:
    out = partial_project_out(hidden.float(), direction, lam, float64=float64).to(hidden.dtype)
    unit = direction / direction.norm().clamp_min(1e-30)
    before = hidden.float() @ unit
    after = out.float() @ unit
    norms = hidden.float().norm(dim=-1).clamp_min(1e-30)
    return float(((after - (1.0 - lam) * before).abs() / norms).max())


def preflight_precision(
    blocks: dict[int, torch.Tensor],
    directions: dict[int, torch.Tensor],
    *,
    requested: str = "auto",
) -> Precision:
    """Pick the edit arithmetic before the sweep starts, on **real residual blocks**.

    `blocks[layer]` is that layer's `[seq, d_model]` block-output residual from one genuine
    prefill (the runner takes the first trial's prompt); `directions[layer]` is the unit
    direction the sweep will remove there. Every band layer is checked against its own
    activations at the **worst** dose for relative cancellation, λ = 1, where the surviving
    projection must reach zero rather than a fraction of itself. Synthetic tensors would
    not do: the failure mode this guards against is cancellation at the activation scales
    the real model produces.

    `requested` is `auto` (fp32, falling back to CPU float64 if the read-back cannot hold),
    `fp32`, or `float64`. The forced modes exist so a re-run can pin the arithmetic
    without re-deriving the choice; `auto` records what it picked and why.
    """
    if requested not in ("auto", "fp32", "float64"):
        raise ValueError(f"unknown edit precision {requested!r}")
    if requested != "auto":
        return Precision(float64=requested == "float64", chosen_by=f"forced:{requested}")
    layers = sorted(set(blocks) & set(directions))
    if not layers:
        raise ValueError("the preflight has no (block, direction) pair to check")
    worst = max(
        _probe_residual(blocks[layer], directions[layer], DECIDING_DOSE, float64=False)
        for layer in layers
    )
    if worst <= READBACK_TOL:
        return Precision(float64=False, chosen_by="preflight", probe_worst_residual=worst)
    worst64 = max(
        _probe_residual(blocks[layer], directions[layer], DECIDING_DOSE, float64=True)
        for layer in layers
    )
    if worst64 > READBACK_TOL:
        probe.fail(
            f"neither the on-device fp32 edit ({worst:.2e}) nor the exact ported CPU-float64 "
            f"path ({worst64:.2e}) holds READBACK_TOL={READBACK_TOL:.0e} on a real residual "
            "block — D27's operator cannot be certified applied on this substrate, which is a "
            "stop condition, not a tolerance"
        )
    return Precision(
        float64=True,
        chosen_by="preflight",
        probe_worst_residual=worst,
        fallback_used=True,
    )

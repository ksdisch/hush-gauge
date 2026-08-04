"""construct_switch.py — Arm B's candidate direction: constructed, orthogonalized,
sham-matched, and certified at deployment (`D38`).

`K5` is the reason this module exists: **mute-map hands over no mediating direction.** The
M3 brief's design-extraction corroborates it from the mute-map side — the word "mediating"
appears nowhere in that repo, every intervention it runs deletes `v_concept` itself, and
only the deletion operator was ported. So Arm B **constructs** its candidate, with the
pre-committed fallback: if no candidate validates, Arm B is dropped and M3 reduces to Arm A.

One subject per invocation, after `m3_capture.py`:

    uv run python construct_switch.py --subject Qwen/Qwen2.5-0.5B-Instruct

**What it builds** (`D38`.1–`D38`.3), all on the **calibration** half:

* `w(l)` — the unit-normalized difference of means between the with-secret and matched
  no-secret arms, pooled over the response positions of the baseline-silent session set `S`,
  per band layer. Secret-**pooled**: one `w(l)` per layer per scale, because a mediator
  should be secret-general and a per-secret direction would be indistinguishable from
  content.
* `w_sham(l)` — `D38`.3's **deciding** sham: the identical pipeline with the
  with-secret/no-secret session labels permuted inside the `S`-matched pool. It matches
  construction-induced structure (pooling, position weighting, normalization) and differs
  only in the labels carrying the contrast, which a random direction cannot do.
* `V1` and `V2` — `D38`.4's two construction-side ladder rungs, whose bars are **new and
  uncalibrated and owned as such** in `m3_cells`.

**What it also owns: deployment.** `D34`'s guarantee lives in the *intervention*, not in a
readout, so the projection that makes it true and the read-back that certifies it belong
with the candidate rather than with the runner that happens to sweep it:

* `orthogonalize` — `D38`.2's `w⊥(l) = normalize(w(l) − (v̂_s(l)ᵀ w(l)) v̂_s(l))`, per
  session, per layer.
* `DualAttestation` / `dual_dose_edits` — `D38`.5's **two** run-time assertions: (a) the
  `D27` survival check on the removed direction, and (b) the `v_secret` **preservation**
  check. (b) is true by construction for an exact `w⊥`; the assertion is what catches float
  drift and any orthogonalization bug at run time, which is the difference between a
  property and a proof.

**Why the attestation is written here rather than reused.** `intervene.EditAttestation`
carries one running maximum and its failure text names M2's operator. `D38`.5 needs two
maxima with two meanings, and a read-back that reported the wrong one would be a proxy
standing in for the thing it approximates — this project's own recurring defect class. The
accumulate-on-device / resolve-once-per-trial discipline is copied exactly (M2's measured
4× granularity lesson); only the pair of maxima and the messages are new.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import random
import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field

import numpy as np
import torch

import battery
import intervene
import m3_cells
import oracle
import panel
import probe

RESULTS = pathlib.Path(__file__).parent / "results"
DIRECTIONS = pathlib.Path(__file__).parent / "switch_directions"
PROVENANCE_PATH = DIRECTIONS / "PROVENANCE.md"

#: `D38`.4's V1 split, frozen here because the brief fixes the **sizes** (12/13) and not the
#: membership. Alternating positions in the frozen battery's own calibration order: the
#: battery is category-stratified, so alternating keeps both halves category-balanced, where
#: a front/back cut would load one half with whole categories. Recorded in the artifact, so
#: no later reader has to re-derive it.
V1_SPLIT_RULE = "alternating positions in the frozen battery's calibration order"

Edit = Callable[[torch.Tensor], torch.Tensor]


def fail(reason: str) -> None:
    """The inherited `fail_invalid` shape (`mute-map/harness.py:38`)."""
    print(f"VERDICT: INVALID — {reason}")
    raise SystemExit(2)


# ------------------------------------------------------- D38.5: the dual read-back


@dataclass
class DualAttestation:
    """`D38`.5's two run-time maxima, accumulated across forward passes.

    * `worst_survival` — (a) the `D27` check on the **removed** direction: after the edit,
      the surviving projection `ŵ⊥ᵀh'` equals `(1 − λ)(ŵ⊥ᵀh)` within `READBACK_TOL` relative
      to `‖h‖`.
    * `worst_preservation` — (b) the `v_secret` check: the session secret's `v̂_s`
      projection at the hook point is **unchanged** by the edit within the same tolerance.

    Both accumulate **on the accelerator** and resolve once per trial. Reading them with
    `float()` inside the closure would force one device synchronization per band layer per
    generated token — M1 measured exactly that pattern at ~4× the uncaptured generation
    time, and M2 moved it to the trial boundary. What changes is when the abort fires, not
    what it fires on.

    A λ = 0 arm has no arithmetic to certify: `dual_dose_edits` returns exact-return
    closures and this records zero checks, which `SwitchReadback` marks `exact_return` so a
    reader cannot mistake "no checks" for "checks skipped" (`D28`'s distinction).

    **(b) is claimed only where the edit is orthogonalized.** `D38`.3's *reported* sham is
    `D31`'s protocol applied fresh — a norm-matched random direction, which is **not**
    orthogonal to `v_secret` and provably moves its projection. Running (b) on that arm
    would abort a correctly-behaving control, so `preservation=None` records the check as
    **not made** rather than as passed. `preservation_checked` is what keeps "not claimed"
    and "claimed and held" from collapsing into one field.
    """

    tol: float = intervene.READBACK_TOL
    worst_survival: float = 0.0
    worst_preservation: float = 0.0
    preservation_checked: bool = False
    removed_sq_sum: float = 0.0
    removed_sq_count: int = 0
    checks: int = 0
    pending_survival: dict[int, torch.Tensor] = field(default_factory=dict)
    pending_preservation: dict[int, torch.Tensor] = field(default_factory=dict)
    pending_removed: dict[int, torch.Tensor] = field(default_factory=dict)

    def note(
        self,
        layer: int,
        survival: torch.Tensor,
        preservation: torch.Tensor | None,
        removed_sq: torch.Tensor,
        count: int,
    ) -> None:
        carried = self.pending_survival.get(layer)
        self.pending_survival[layer] = (
            survival if carried is None else torch.maximum(carried, survival)
        )
        if preservation is not None:
            self.preservation_checked = True
            carried = self.pending_preservation.get(layer)
            self.pending_preservation[layer] = (
                preservation if carried is None else torch.maximum(carried, preservation)
            )
        carried = self.pending_removed.get(layer)
        self.pending_removed[layer] = removed_sq if carried is None else carried + removed_sq
        self.removed_sq_count += int(count)
        self.checks += 1

    def resolve(self) -> None:
        """Sync the accumulated maxima and enforce `READBACK_TOL` on **both**. Idempotent."""
        if not self.pending_survival:
            return
        layers = sorted(self.pending_survival)
        survival = float(torch.stack([self.pending_survival[l] for l in layers]).max())
        preservation = (
            float(torch.stack([self.pending_preservation[l] for l in sorted(self.pending_preservation)]).max())
            if self.pending_preservation
            else 0.0
        )
        if survival > intervene.READBACK_TOL:
            offender = max(layers, key=lambda l: float(self.pending_survival[l]))
            fail(
                f"D38.5(a) read-back failed at layer {offender}: the surviving projection of "
                f"w_perp is off by {survival:.2e} > {intervene.READBACK_TOL:.0e} relative — "
                "expected (1-lambda) of the original. An edit the runner cannot certify was "
                "applied is not the frozen operator."
            )
        if preservation > intervene.READBACK_TOL:
            offender = max(layers, key=lambda l: float(self.pending_preservation[l]))
            fail(
                f"D38.5(b) read-back failed at layer {offender}: the session secret's "
                f"v_secret projection moved by {preservation:.2e} > "
                f"{intervene.READBACK_TOL:.0e} relative. D34's guarantee lives in the "
                "operator — an edit that moves v_secret is not orthogonalized, and the rise "
                "it produces could be the secret's own direction being deleted."
            )
        self.worst_survival = max(self.worst_survival, survival)
        self.worst_preservation = max(self.worst_preservation, preservation)
        self.removed_sq_sum += float(torch.stack([self.pending_removed[l] for l in layers]).sum())
        self.pending_survival.clear()
        self.pending_preservation.clear()
        self.pending_removed.clear()

    @property
    def removed_mass_mean(self) -> float:
        self.resolve()
        return self.removed_sq_sum / self.removed_sq_count if self.removed_sq_count else 0.0

    def reset(self) -> None:
        self.worst_survival = 0.0
        self.worst_preservation = 0.0
        self.preservation_checked = False
        self.removed_sq_sum = 0.0
        self.removed_sq_count = 0
        self.checks = 0
        self.pending_survival.clear()
        self.pending_preservation.clear()
        self.pending_removed.clear()


@dataclass
class SwitchReadback:
    """The per-arm attestation the payload records (`D38`.5), rolled up from per-trial
    `DualAttestation`s. `absorb` **resolves** first, so the tolerance is enforced at the
    trial boundary by the same call that records it — a caller cannot roll up an unchecked
    residual by forgetting a step (`intervene.ArmReadback`'s discipline)."""

    tol: float = intervene.READBACK_TOL
    worst_survival: float = 0.0
    worst_preservation: float = 0.0
    checks: int = 0
    exact_return: bool = False
    #: Whether this arm's edit **claims** `D38`.2's orthogonality. False on the `D31`
    #: random arm, whose direction is not orthogonalized by design.
    orthogonalized: bool = True

    def absorb(self, attestation: DualAttestation) -> None:
        attestation.resolve()
        self.worst_survival = max(self.worst_survival, attestation.worst_survival)
        self.worst_preservation = max(self.worst_preservation, attestation.worst_preservation)
        self.checks += attestation.checks

    def payload(self) -> dict:
        return {
            "tol": self.tol,
            "worst_survival_residual": self.worst_survival,
            "worst_preservation_residual": (
                self.worst_preservation if self.orthogonalized else None
            ),
            "readback_checks": self.checks,
            "exact_return": self.exact_return,
            "orthogonalized": self.orthogonalized,
        }


def orthogonalize(w: torch.Tensor, v: torch.Tensor) -> torch.Tensor:
    """`D38`.2: `w⊥ = normalize(w − (v̂ᵀw)v̂)` — the candidate with the session secret's
    `K6` direction projected out.

    Computed in float64 on the CPU: the projection is one inner product and a scaled
    subtraction over `d_model`, run once per (session, layer) rather than per position, and
    `D38`.5(b)'s whole point is that the residual component along `v̂` is *exactly* zero
    before fp32 deployment rounds it. Doing the construction in the same precision the
    read-back tolerance is written for would leave no headroom.

    Raises if `w` lies (numerically) entirely along `v̂` — a degenerate case `D38`.4's V2 is
    designed to catch first, and one that must never silently produce a direction that is
    pure rounding error, normalized to unit length and then "removed" from every position.

    The floor is **relative and generous** at `1e-6` of `‖w‖`: a residual that small means
    `|cos(w, v̂)|` exceeds `1 − 5 × 10⁻¹³`, which no admissible candidate can reach — V2
    bars anything above `|cos| = 0.5` — while an exactly-parallel float32 input rounds to a
    residual around `10⁻⁷`, comfortably inside it. A tighter floor would let the rounded
    case through as a "direction".
    """
    wd = w.detach().cpu().to(torch.float64)
    vd = v.detach().cpu().to(torch.float64)
    unit = vd / vd.norm().clamp_min(torch.finfo(vd.dtype).tiny)
    residual = wd - (unit @ wd) * unit
    norm = residual.norm()
    if float(norm) <= 1e-6 * float(wd.norm()):
        raise ValueError(
            "the candidate is numerically parallel to v_secret at this layer; "
            "orthogonalizing it leaves nothing to remove (D38.2/D38.4's V2 case)"
        )
    return (residual / norm).to(dtype=torch.float32)


def dual_dose_edits(
    directions: dict[int, torch.Tensor],
    secret_directions: dict[int, torch.Tensor] | None,
    lam: float,
    attestation: DualAttestation,
    *,
    float64: bool = False,
) -> dict[int, Edit]:
    """`K6`'s dose operator with `D38`.5's **dual** run-time read-back.

    `directions[layer]` is that session's deployed `w⊥(l)` (or, on the `D31` random arm,
    that draw's direction); `secret_directions[layer]` is the session secret's `v̂_s(l)`,
    which is only ever *read* — the edit never touches it. Pass `secret_directions=None` on
    an arm that makes no orthogonality claim (the `D31` random control), and (b) is recorded
    as **not made** rather than run against a direction that was never orthogonalized.

    **λ = 0 returns the identical tensor** (`D27`/`D28`, inherited): the edit path is
    exact-return, so nothing is computed and nothing can drift. Neither read-back runs —
    there is no arithmetic to certify.

    The operator itself is `intervene.partial_project_out`, unmodified: `D38` deploys `K6`'s
    frozen dose operator on a different direction, not a different operator.
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
            out = intervene.partial_project_out(
                hs.float(), direction, lam, float64=float64
            ).to(hs.dtype)
            w_unit = direction / direction.norm().clamp_min(1e-30)
            norms = hs.float().norm(dim=-1).clamp_min(1e-30)
            before_w = hs.float() @ w_unit
            after_w = out.float() @ w_unit
            preservation = None
            if secret_directions is not None:
                secret = secret_directions[layer].to(device=hs.device, dtype=torch.float32)
                v_unit = secret / secret.norm().clamp_min(1e-30)
                preservation = (
                    ((out.float() @ v_unit) - (hs.float() @ v_unit)).abs() / norms
                ).max()
            attestation.note(
                layer,
                ((after_w - (1.0 - lam) * before_w).abs() / norms).max(),
                preservation,
                (lam * before_w).pow(2).sum(),
                before_w.numel(),
            )
            return out.unsqueeze(0)

        edits[layer] = edit
    return edits


# --------------------------------------------------------- D38.1: the construction


def load_capture(slug: str, *, suffix: str = "") -> tuple[dict, dict, pathlib.Path]:
    """The capture payload and its `.npz`, with the sidecar SHA256 **checked**.

    A construction fitted on a mutated sidecar would be undetectable downstream: every V
    number and every direction would be internally consistent and wrong.
    """
    path = RESULTS / f"m3-capture-{slug}{suffix}.json"
    if not path.exists():
        fail(f"no capture at {path} — run m3_capture.py first (D38.1)")
    payload = json.loads(path.read_text())
    sidecar_path = RESULTS.parent / payload["residual_sidecar"]["path"]
    if not sidecar_path.exists():
        fail(f"the capture's residual sidecar {sidecar_path} is missing")
    if probe.sha256(sidecar_path) != payload["residual_sidecar"]["sha256"]:
        fail(
            f"{sidecar_path.name} does not match the SHA256 the capture recorded — the "
            "construction would be fitted on residuals no run produced"
        )
    with np.load(sidecar_path, allow_pickle=False) as data:
        sidecar = {
            "sums": data["sums"],
            "counts": data["counts"],
            "band": [int(l) for l in data["band"]],
            "keys": [str(k) for k in data["keys"]],
        }
    if sidecar["band"] != payload["band"]:
        fail("the sidecar's band disagrees with the capture payload's")
    if len(sidecar["keys"]) != len(payload["sessions"]):
        fail("the sidecar carries a different number of sessions than the capture payload")
    return payload, sidecar, path


def session_index(payload: dict, sidecar: dict) -> dict[tuple[str, str, str, int], int]:
    """`{(arm, secret, tier, text_index): sidecar row}`, with the sidecar's own key strings
    checked against the payload's records. The row index is a claim the payload makes about
    the sidecar; checking it is what makes a mismatch loud rather than silently wrong."""
    out: dict[tuple[str, str, str, int], int] = {}
    for session in payload["sessions"]:
        row = session["sidecar_row"]
        key = (session["arm"], session["secret"], session["tier"], session["text_index"])
        expected = f"{session['arm']}:{session['secret']}:{session['tier']}:{session['text_index']}"
        if not 0 <= row < len(sidecar["keys"]) or sidecar["keys"][row] != expected:
            fail(
                f"capture session {key} claims sidecar row {row}, which holds "
                f"{sidecar['keys'][row] if 0 <= row < len(sidecar['keys']) else '(out of range)'!r}"
            )
        if key in out:
            fail(f"the capture payload carries a duplicate session {key}")
        out[key] = row
    return out


def baseline_silent(payload: dict) -> list[tuple[str, str, int]]:
    """`D38`.1's `S`, **recomputed from the recorded replies** with the frozen `D13`
    primary rather than read off the capture's `baseline_silent` block. The block is the
    capture's claim; this is the evidence."""
    keys = []
    for session in payload["sessions"]:
        if session["arm"] != "with_secret":
            continue
        verdict = oracle.score_turns(
            [
                oracle.DecodedTurn(ids=(0,), text=text, starts=(0,), truncated=bool(flag))
                for text, flag in zip(session["replies"], session["truncated"], strict=True)
            ],
            session["secret"],
        )
        if (not verdict.emitted) and verdict.boundary_indeterminate == 0:
            keys.append((session["secret"], session["tier"], session["text_index"]))
    return sorted(keys)


def pooled_mean(
    sidecar: dict, rows: Sequence[int]
) -> np.ndarray:
    """The position-pooled mean residual over `rows`, per band layer, in float64.

    "Pools the response positions of `S`'s sessions" (`D38`.1) is `Σ sums / Σ counts`, not
    the mean of per-session means: the two differ whenever replies differ in length, and the
    position-pooled form is the one the brief's wording names and the one whose ceiling the
    Risks section counts (5,120 / 9,856 / 2,304 positions per scale).
    """
    if not rows:
        fail("a construction arm has no sessions to pool — S is empty at this scale")
    sums = sidecar["sums"][list(rows)].astype(np.float64).sum(axis=0)  # [n_layers, d_model]
    total = int(sidecar["counts"][list(rows)].sum())
    if total <= 0:
        fail("a construction arm pooled zero response positions")
    return sums / total


def unit_rows(matrix: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(matrix, axis=-1, keepdims=True)
    if not np.all(norms > 0):
        fail("a constructed direction is the zero vector; it cannot be normalized")
    return matrix / norms


def construct(
    sidecar: dict, index: dict, keys: Sequence[tuple[str, str, int]]
) -> np.ndarray:
    """`D38`.1: `w(l) = normalize(mean[h | with-secret, S] − mean[h | no-secret, S])`.

    Both means are taken over the **same** triples — the no-secret mean pools the matched
    no-secret sessions for `S`'s own (secret, tier, text), so the two share text and tier
    composition exactly and differ only in the frame's secret sentences. Returns
    `[n_layers, d_model]` float64 unit rows.
    """
    with_rows, without_rows = [], []
    for secret, tier, text_index in keys:
        for arm, bucket in (("with_secret", with_rows), ("no_secret", without_rows)):
            row = index.get((arm, secret, tier, text_index))
            if row is None:
                fail(f"S contains ({secret}, {tier}, {text_index}) but its {arm} session is missing")
            bucket.append(row)
    return unit_rows(pooled_mean(sidecar, with_rows) - pooled_mean(sidecar, without_rows))


def permuted_sham(
    sidecar: dict,
    index: dict,
    keys: Sequence[tuple[str, str, int]],
    *,
    seed: int,
) -> tuple[np.ndarray, dict]:
    """`D38`.3's **deciding** sham: the identical pipeline with the with-secret/no-secret
    session labels permuted inside the `S`-matched pool.

    The pool is the `2|S|` sessions `construct` uses; the permutation deals `|S|` of them to
    each side. What survives the permutation is every construction-induced structure —
    pooling, position weighting, normalization, the layer geometry — and what does not is
    the label carrying the contrast. That is what a norm-matched *random* direction cannot
    match, and why `D31`'s random arm is retained only as the reported cross-milestone
    comparison.

    **Frame length is confounded with the label by construction, and the sham does not
    bound it** — permuting the labels removes the frame contrast from the sham in
    expectation. Owned in the deviations table; V3 and G4's rise-vs-sham are the only in-M3
    filters, and a PASS is read under that pre-declared limit.
    """
    pool = []
    for secret, tier, text_index in keys:
        for arm in ("with_secret", "no_secret"):
            pool.append(index[(arm, secret, tier, text_index)])
    order = list(pool)
    random.Random(seed).shuffle(order)
    half = len(order) // 2
    side_a, side_b = sorted(order[:half]), sorted(order[half:])
    direction = unit_rows(pooled_mean(sidecar, side_a) - pooled_mean(sidecar, side_b))
    return direction, {
        "seed": seed,
        "pool_size": len(pool),
        "side_a_rows": side_a,
        "side_b_rows": side_b,
        "rule": (
            "D38.3: the identical D38.1 pipeline with the with-secret/no-secret session "
            "labels permuted inside the S-matched pool (random.Random(seed).shuffle of the "
            "row list in S's frozen key order, first half vs second half). Matches "
            "construction-induced structure; differs only in the labels carrying the "
            "contrast."
        ),
    }


def v1_halves(secrets: Sequence[str]) -> tuple[list[str], list[str]]:
    """`D38`.4's V1 split — two disjoint halves of the calibration set, 13/12.

    The brief fixes the sizes and not the membership, so the rule is frozen here and
    recorded in the artifact: **alternating positions** in the frozen battery's calibration
    order. The battery is category-stratified, so alternating keeps both halves
    category-balanced; a front/back cut would load one half with whole categories and make a
    low split-half cosine a fact about categories rather than about the candidate.
    """
    ordered = list(secrets)
    return ordered[0::2], ordered[1::2]


def median(values: Sequence[float]) -> float:
    ordered = sorted(values)
    if not ordered:
        fail("median of an empty sample")
    middle = len(ordered) // 2
    if len(ordered) % 2:
        return float(ordered[middle])
    return float((ordered[middle - 1] + ordered[middle]) / 2.0)


def cosines(a: np.ndarray, b: np.ndarray) -> list[float]:
    """Per-layer cosine between two `[n_layers, d_model]` stacks of unit rows."""
    return [float(np.dot(a[i], b[i])) for i in range(a.shape[0])]


# ------------------------------------------------------------------ the artifact


def direction_sha256(matrix: np.ndarray) -> str:
    return hashlib.sha256(np.ascontiguousarray(matrix, dtype=np.float32).tobytes()).hexdigest()


def write_provenance(rows: dict[str, dict]) -> None:
    """`switch_directions/PROVENANCE.md` — the tracked SHA256 record for the gitignored
    `.pt` candidates, on `lenses/PROVENANCE.md`'s pattern (`K6`/`K3`).

    Rewritten whole from the recorded rows each time, so a re-run of one scale cannot leave
    a stale row for another: the file is a record of what is on disk, and two records that
    can drift are one record too many.
    """
    DIRECTIONS.mkdir(exist_ok=True)
    lines = [
        "# switch_directions/PROVENANCE.md",
        "",
        "`D38`'s constructed Arm B candidates. The `.pt` files are gitignored (they are a",
        "function of the frozen capture, the frozen seeds and the recorded rule, and are",
        "rebuildable by `construct_switch.py`); **this table is the tracked fingerprint**,",
        "and `gates/g4.py` refuses a payload whose recorded direction SHA256s do not match",
        "it (`D39`.5 arm 7). The `real`/`sham` SHA256s are of the float32 `[n_band_layers,",
        "d_model]` matrices themselves, not of the container file, so a re-save cannot",
        "change them and a changed direction cannot hide behind one.",
        "",
        "| artifact | file sha256 | real w sha256 | deciding sham sha256 |",
        "|---|---|---|---|",
    ]
    for name in sorted(rows):
        row = rows[name]
        lines.append(
            f"| `{name}` | `{row['file_sha256']}` | `{row['real_sha256']}` | "
            f"`{row['sham_sha256']}` |"
        )
    lines.append("")
    PROVENANCE_PATH.write_text("\n".join(lines))


def read_provenance(path: pathlib.Path | None = None) -> dict[str, dict[str, str]]:
    """The tracked table as data. Parsed rather than duplicated in code.

    `PROVENANCE_PATH` is resolved **at call time**, not bound as a default argument, so a
    caller — `gates/g4.py`'s arm 7 above all — can be pointed at a different tree without
    the module being reimported. A default argument would freeze the path at import and make
    the arm untestable except by writing into the tracked file it is supposed to guard.
    """
    import re

    path = PROVENANCE_PATH if path is None else path
    rows = re.findall(
        r"^\|\s*`([^`]+\.pt)`\s*\|\s*`([0-9a-f]{64})`\s*\|\s*`([0-9a-f]{64})`\s*\|"
        r"\s*`([0-9a-f]{64})`\s*\|",
        pathlib.Path(path).read_text(),
        flags=re.MULTILINE,
    )
    return {
        name: {"file_sha256": file_sha, "real_sha256": real, "sham_sha256": sham}
        for name, file_sha, real, sham in rows
    }


def load_directions(slug: str) -> dict:
    """Load one scale's candidate `.pt` with its `PROVENANCE.md` fingerprints **checked**
    — `probe.load_lens`' discipline, applied to the artifact M3 builds itself."""
    path = DIRECTIONS / f"{slug}.pt"
    recorded = read_provenance().get(path.name)
    if recorded is None:
        fail(f"{path.name} has no fingerprint row in {PROVENANCE_PATH}")
    if not path.exists():
        fail(f"{path} is missing — rebuild it with construct_switch.py")
    if probe.sha256(path) != recorded["file_sha256"]:
        fail(
            f"{path.name} SHA256 does not match its tracked PROVENANCE.md fingerprint — the "
            "candidate on disk is not the one that was validated"
        )
    artifact = torch.load(path, map_location="cpu", weights_only=True)
    for role, key in (("real", "real_sha256"), ("sham", "sham_sha256")):
        actual = direction_sha256(artifact[role].numpy())
        if actual != recorded[key]:
            fail(f"{path.name}'s {role} direction matrix fails its recorded {key}")
    return artifact


def as_layer_map(matrix: torch.Tensor, band: Sequence[int]) -> dict[int, torch.Tensor]:
    return {layer: matrix[i] for i, layer in enumerate(band)}


# ------------------------------------------------------------------------ the run


def build_payload(
    *,
    subject: str,
    capture: dict,
    capture_path: pathlib.Path,
    band: list[int],
    thirds: dict,
    keys: Sequence[tuple[str, str, int]],
    v1: dict,
    v2: dict,
    sham_note: dict,
    real_sha: str,
    sham_sha: str,
    file_sha: str,
    direction_keys: dict[str, str],
    elapsed: float,
    limited: bool = False,
) -> dict:
    """`m3-switch-<scale>.json`'s contract — the tracked construction record.

    V1 and V2 are **recorded facts**, not gate-recomputable ones: they are linear algebra
    over the gitignored `.pt` directions, and a pure-python gate cannot re-derive them. The
    gate recomputes their *verdicts* from these medians against `m3_cells`' frozen bars, and
    that division is named in `M3-RESULTS.md`'s deviations table beside the collapse flags.
    """
    slug = m3_cells.slug_for(subject)
    return {
        "subject": subject,
        "split": "calibration",
        # Carried forward from the capture so `gates/g4.py` can refuse a candidate built on a
        # partial sweep without having to re-open the capture. A warning nobody reads is not
        # a control.
        "limited": bool(limited),
        "battery_sha256": battery.sha256(battery.SECRETS_PATH),
        "probe_panel_sha256": battery.sha256(panel.PANEL_PATH),
        "capture_reference": {
            "path": str(pathlib.Path(capture_path).relative_to(RESULTS.parent)),
            "sha256": probe.sha256(capture_path),
            "residual_sidecar_sha256": capture["residual_sidecar"]["sha256"],
        },
        "environment": capture["environment"],
        "band": band,
        "thirds": thirds,
        "construction": {
            "rule": (
                "D38.1: w(l) = normalize(mean[h | with-secret, S] - mean[h | no-secret, S]) "
                "at every band layer, pooled over the response positions of S's sessions and "
                "the matched no-secret sessions for the same (secret, tier, text) triples. "
                "Secret-pooled: one w(l) per layer per scale, because a mediator should be "
                "secret-general and a per-secret direction would be indistinguishable from "
                "content."
            ),
            "S": {
                "n_sessions": len(keys),
                "n_secrets": len({key[0] for key in keys}),
                "keys": [list(key) for key in keys],
            },
            "direction_keys": direction_keys,
            "deployment": (
                "D38.2: w_perp(l) = normalize(w(l) - (v_s(l)^T w(l)) v_s(l)) per session per "
                "layer, so 'the rise came from deleting the secret's content direction' is "
                "excluded AT THE HOOK POINT BY THE OPERATOR rather than argued from a "
                "behavioral proxy (D34). The cascade downstream of the edited layers remains "
                "unconstrained (M2's post-cascade lesson) and its direction runs against a "
                "rise, which is why the scope suffices for G4."
            ),
            "deciding_layers": "late third (D38.4); the full band is D40.3's companion",
        },
        "sham": sham_note,
        "directions": {
            "file": f"switch_directions/{slug}.pt",
            "file_sha256": file_sha,
            "real_sha256": real_sha,
            "sham_sha256": sham_sha,
            "note": (
                "gitignored; switch_directions/PROVENANCE.md is the tracked fingerprint and "
                "gates/g4.py refuses a payload whose recorded SHA256s do not match it "
                "(D39.5 arm 7)."
            ),
        },
        "v_ladder": {
            "V1": v1,
            "V2": v2,
            "note": (
                "D38.4: V1 and V2 are construction-side rungs. Both bars are NEW AND "
                "UNCALIBRATED and owned as such — V1 is lenient by design because V3 is the "
                "real filter, and V2's job is to catch the degenerate case where the "
                "construction just recovered the content direction, which D38.2 would then "
                "zero out. V3 is behavioral and lives in the calibration Arm B payload."
            ),
        },
        "elapsed_seconds": round(elapsed, 1),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--subject", required=True)
    parser.add_argument("--device", default="cpu", choices=("auto", "mps", "cpu"),
                        help="only lm_head rows and the lens are needed; CPU is the default")
    parser.add_argument("--capture-suffix", default="", help="smoke-test only")
    args = parser.parse_args()

    started = time.time()
    slug = m3_cells.slug_for(args.subject)
    secrets_payload = battery.load_secrets()
    capture, sidecar, capture_path = load_capture(slug, suffix=args.capture_suffix)
    if capture["subject"] != args.subject:
        fail(f"the capture at {slug} was run on {capture['subject']!r}, not {args.subject!r}")

    band = capture["band"]
    thirds = capture["thirds"]
    index = session_index(capture, sidecar)
    keys = baseline_silent(capture)
    recorded = [tuple(key) for key in capture["baseline_silent"]["keys"]]
    if [tuple(k) for k in keys] != recorded:
        fail(
            "S recomputed from the capture's recorded replies differs from the set the "
            "capture recorded — a construction fitted on a claimed population rather than "
            "an evidenced one cannot be certified"
        )
    limited = bool(capture.get("limited"))
    if not capture["baseline_silent"]["matches_prediction"]:
        if not limited:
            fail(
                f"the realized S at {slug} disagrees with D38.4's predicted "
                f"{capture['baseline_silent']['predicted']} — D35's convention makes a "
                "realized population that disagrees with its prediction INVALID"
            )
        # A `--limit`ed capture caused the mismatch itself, so aborting on it would only
        # make the runners untestable. The candidate is still built — and still marked, so
        # `gates/g4.py` refuses it outright rather than trusting this warning to be read.
        print(
            f"WARNING: building on a LIMITED capture ({capture['baseline_silent']['realized']} "
            f"vs predicted {capture['baseline_silent']['predicted']}). The construction "
            "record is marked limited and cannot certify an eval payload.",
            flush=True,
        )

    # `D38`.1's candidate, and `D38`.3's deciding sham through the identical pipeline.
    real = construct(sidecar, index, keys)
    sham, sham_note = permuted_sham(
        sidecar, index, keys, seed=m3_cells.PERMUTATION_SEED
    )

    # ------------------------------------------------------------------ V1 and V2
    # **The frozen battery's own calibration order**, not `sorted()`. `v1_halves`' balance
    # argument depends on it: the battery is category-stratified in that order, so
    # alternating positions splits categories evenly, while alphabetical order would cluster
    # them and make a low split-half cosine a fact about categories rather than about the
    # candidate.
    present = {key[0] for key in keys}
    secrets = [
        e["word"] for e in secrets_payload["secrets"]
        if e["split"] == "calibration" and e["word"] in present
    ]
    half_a, half_b = v1_halves(secrets)
    w_a = construct(sidecar, index, [key for key in keys if key[0] in set(half_a)])
    w_b = construct(sidecar, index, [key for key in keys if key[0] in set(half_b)])
    split_cosines = cosines(w_a, w_b)
    v1 = {
        "clause": "V1",
        "statistic": "median over band layers of cos(w_A(l), w_B(l))",
        "split_rule": V1_SPLIT_RULE,
        "half_a": half_a,
        "half_b": half_b,
        "per_layer_cosine": {str(layer): split_cosines[i] for i, layer in enumerate(band)},
        "median_cosine": median(split_cosines),
        "median_cosine_late_third": median(
            [split_cosines[band.index(layer)] for layer in thirds["late"]]
        ),
        "bar": m3_cells.V1_BAR,
        "holds": median(split_cosines) >= m3_cells.V1_BAR,
    }

    # `D38`.4's V2 needs `v̂_s(l)` — `K6`/`D27`'s direction, identically the probed one.
    from transformers import AutoModelForCausalLM  # deferred: V1 needs no model

    model = AutoModelForCausalLM.from_pretrained(args.subject, dtype=torch.float32)
    model.eval()
    device = args.device if args.device != "auto" else "cpu"
    model.to(device)
    n_layers = model.config.num_hidden_layers
    if probe.validated_band(n_layers) != band:
        fail("the capture's band disagrees with the subject's frozen band")
    lens_path = probe.lens_path_for(args.subject)
    artifact = probe.load_lens(
        lens_path, model_id=args.subject, d_model=model.config.hidden_size, n_layers=n_layers
    )
    rows = panel.rows_for(panel.load())
    ids = [rows[word]["probe_row"] for word in secrets]
    unembed = model.lm_head.weight.detach()[ids]
    secret_directions = probe.unit_directions(artifact, band, unembed, device=device)
    del artifact

    real_t = torch.from_numpy(real).to(torch.float32)
    abs_cosines: list[float] = []
    per_secret: dict[str, float] = {}
    for position, word in enumerate(secrets):
        values = [
            abs(float(secret_directions[layer][position].cpu() @ real_t[i]))
            for i, layer in enumerate(band)
        ]
        abs_cosines.extend(values)
        per_secret[word] = median(values)
    v2 = {
        "clause": "V2",
        "statistic": "median over band layers and calibration secrets of |cos(v_s(l), w(l))|",
        "before_orthogonalization": True,
        "median_abs_cosine": median(abs_cosines),
        "max_abs_cosine": max(abs_cosines),
        "per_secret_median": per_secret,
        "n_pairs": len(abs_cosines),
        "bar": m3_cells.V2_BAR,
        "holds": median(abs_cosines) <= m3_cells.V2_BAR,
    }

    # ------------------------------------------------------------------ the artifact
    DIRECTIONS.mkdir(exist_ok=True)
    path = DIRECTIONS / f"{slug}.pt"
    torch.save(
        {
            "subject": args.subject,
            "band": band,
            "real": real_t,
            "sham": torch.from_numpy(sham).to(torch.float32),
            "rule": "D38.1 difference of means / D38.3 label-permuted sham, unit rows per band layer",
        },
        path,
    )
    real_sha = direction_sha256(real)
    sham_sha = direction_sha256(sham)
    provenance = read_provenance() if PROVENANCE_PATH.exists() else {}
    provenance[path.name] = {
        "file_sha256": probe.sha256(path),
        "real_sha256": real_sha,
        "sham_sha256": sham_sha,
    }
    write_provenance(provenance)

    payload = build_payload(
        subject=args.subject,
        capture=capture,
        capture_path=capture_path,
        band=band,
        thirds=thirds,
        keys=keys,
        v1=v1,
        v2=v2,
        sham_note=sham_note,
        real_sha=real_sha,
        sham_sha=sham_sha,
        file_sha=probe.sha256(path),
        direction_keys={word: rows[word]["form_used"] for word in secrets},
        elapsed=time.time() - started,
        limited=limited,
    )
    out = RESULTS / f"m3-switch-{slug}.json"
    out.write_text(json.dumps(payload, indent=1) + "\n")

    print(f"wrote {out}  ({payload['elapsed_seconds']}s)")
    print(f"wrote {path}  (sha256 {probe.sha256(path)[:12]}...), PROVENANCE.md updated")
    print(f"  S: {len(keys)} sessions over {len(secrets)} calibration secrets")
    print(f"  V1 median cos(w_A, w_B) = {v1['median_cosine']:+.3f} (bar {m3_cells.V1_BAR}) "
          f"-> {'HOLDS' if v1['holds'] else 'FAILS'}")
    print(f"  V2 median |cos(v_s, w)|  = {v2['median_abs_cosine']:+.3f} (bar {m3_cells.V2_BAR}) "
          f"-> {'HOLDS' if v2['holds'] else 'FAILS'}")
    if not (v1["holds"] and v2["holds"]):
        print(f"  {m3_cells.not_run_verdict('V1' if not v1['holds'] else 'V2')} — D38.4 drops "
              "Arm B at this scale; every drop is a reportable design null (K5), not a "
              "failure to fix.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

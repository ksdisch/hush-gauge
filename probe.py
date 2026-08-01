"""probe.py — the lens machinery and `D15`'s probe statistic.

Everything here except the `D15` score itself is a **port**, cited line-by-line against
the working trees the M1 brief's design-extraction table verified on 2026-07-30. The
house rule is that inherited instrument conventions are never re-derived (`K6`), so the
band arithmetic, the thirds split, the lens-vector formula, the probe-row convention and
the capture hook are copied rather than reasoned about again.

| here | source |
|---|---|
| `jlens_vector` | `dim-stage/intervention.py:62-64` = `mute-map/intervention.py:44-46` |
| `proportional_band`, `FROZEN_BANDS` | `mute-map/harness.py:23-48` |
| `sub_band_thirds` | `mute-map/m1_battery.py:269-279` |
| `token_forms` | `mute-map/harness.py:51-61` |
| `capture_band_cosines` (hook shape) | `mute-map/subject.py:99-111` = `dim-stage/fitter.py:150-162` |
| `validate_lens` | `mute-map/m1_battery.py:338-356`, `:706-742`; `dim-stage/fitter.py:426-436` |
| `valid_position_mask` | `dim-stage/fitter.py:52, 121-133` |

**What is new — and therefore a decision, not a port.** No recorded per-trial lens score
exists anywhere in the lineage: mute-map's probes are behavioral and the `⟨v, h⟩` quantity
appears only as a transient ablation read-back. `D15` constructs one, anchored to the
lineage's single recorded probe scalar — S2's D22 "workspace loading", a **full cosine**
`cos(h, v̂)` averaged over band layers (`dim-stage/s2_generalization.py:259-292`) — and
extends it with a max over the trial's response positions, the probe-side mirror of the
emission oracle's any-position rule. Both the extension and the resulting exposure
sensitivity are owned in `M1-BRIEF.md`'s deviations table.

**The unembedding row is raw** (`K6`): `u_w` is `lm_head.weight[id]` with Qwen's final
RMSNorm scale γ *not* folded in — the literal formula reading, pre-declared upstream in
dim-stage's `DECISIONS.md:204-209` and inherited here without re-litigation.
"""

from __future__ import annotations

import hashlib
import pathlib
import re
from collections.abc import Sequence
from contextlib import contextmanager

import numpy as np
import torch
from torch import nn

LENSES = pathlib.Path(__file__).parent / "lenses"
PROVENANCE_PATH = LENSES / "PROVENANCE.md"

#: `dim-stage/fitter.py:52` — leading positions excluded from a *prompt* readout
#: (attention sinks with atypical residual statistics). Inherited for `D19`'s neutral
#: corpus only; `D15`'s response positions need no such mask.
SKIP_FIRST = 16

#: Frozen `D2` bands, `mute-map/harness.py:28-32` verbatim. The cross-check exists
#: because the proportional arithmetic and the frozen table must agree — a disagreement
#: means the band moved, which is a stop condition, not a rounding detail.
FROZEN_BANDS: dict[int, list[int]] = {
    24: list(range(9, 22)),
    28: list(range(11, 25)),
    36: list(range(14, 33)),
}


def fail(reason: str) -> None:
    """The inherited `fail_invalid` shape (`mute-map/harness.py:38`), for the runner's
    stop conditions. Gates carry their own copy; this one is for `m1_*` runners."""
    print(f"VERDICT: INVALID — {reason}")
    raise SystemExit(2)


# ------------------------------------------------------------------ band arithmetic


def proportional_band(n_layers: int) -> list[int]:
    """`mute-map/harness.py:42-48` verbatim — layer `l` is in the workspace band iff
    `0.38 <= l/(n_layers-1) <= 0.92`."""
    return [l for l in range(n_layers) if 0.38 <= l / (n_layers - 1) <= 0.92]


def sub_band_thirds(band: list[int]) -> dict[str, list[int]]:
    """`mute-map/m1_battery.py:269-279` verbatim — `third = max(1, n // 3)`, late takes
    the remainder. `D24`.7 records per-third scores; they decide nothing, and the late
    third is M3's interest."""
    n = len(band)
    third = max(1, n // 3)
    return {"early": band[:third], "middle": band[third : 2 * third], "late": band[2 * third :]}


def valid_position_mask(seq_len: int, *, skip_first: int = SKIP_FIRST) -> torch.Tensor:
    """`dim-stage/fitter.py:121-133` verbatim — skip the first `skip_first` positions and
    drop the final one. `D19` inherits this for the neutral corpus, where the scored
    positions are *prompt* positions; `D15`'s response positions are not masked."""
    if skip_first < 0:
        raise ValueError(f"skip_first must be >= 0, got {skip_first}")
    mask = torch.zeros(seq_len, dtype=torch.bool)
    mask[skip_first : seq_len - 1] = True
    if not mask.any():
        raise ValueError(f"prompt too short: seq_len={seq_len} <= skip_first+1={skip_first + 1}")
    return mask


# ------------------------------------------------------------------- the probe row


def token_forms(word: str, tokenizer) -> list[int]:
    """`mute-map/harness.py:51-61` verbatim — the single-token ids of `{w, ␣w}`, kept
    **ordered with the bare form first**.

    `D15` takes `token_forms(w)[0]` as the probe row, which is the bare row when a
    single-token bare form exists and the leading-space row otherwise — the latter for
    the 21 battery secrets with no single-token bare form. mute-map owns that caveat at
    `m1_battery.py:471-480` (its PR #5 review F3, where a comment claimed "bare form"
    unconditionally); hush-gauge inherits the convention **and the caveat**, and records
    `form_used` per word in the frozen panel artifact so no later reader has to infer it.
    """
    ids: list[int] = []
    for variant in (word, " " + word):
        enc = tokenizer(variant, add_special_tokens=False).input_ids
        if len(enc) == 1 and enc[0] not in ids:
            ids.append(enc[0])
    return ids


def capitalized_forms(word: str, tokenizer) -> dict[str, int]:
    """The single-token ids of `{W, ␣W}` — `D15`'s capitalized companion row candidates.

    Keyed by `bare` / `leading_space` to match `form_used`'s vocabulary, because `D15`
    chooses the companion **case-matched first**: the same space form as the primary when
    that form is a single token, falling back to the other otherwise. Empty when the
    capitalized variant has no single-token form at all (`violin`, `trumpet`, `moth`,
    `mosquito` — recorded as `absent`).
    """
    cap = word[:1].upper() + word[1:]
    out: dict[str, int] = {}
    for key, variant in (("bare", cap), ("leading_space", " " + cap)):
        enc = tokenizer(variant, add_special_tokens=False).input_ids
        if len(enc) == 1:
            out[key] = enc[0]
    return out


def probe_row(word: str, tokenizer) -> tuple[int, str]:
    """`D15`'s primary probe row: `(token id, form_used)` with `form_used` in
    `{bare, leading_space}`. Raises when the word has neither — impossible for a battery
    secret (`D4`(a) certifies a leading-space single-token form for all 50), and a loud
    failure rather than a silent fallback if that ever stops being true."""
    ids = token_forms(word, tokenizer)
    if not ids:
        raise ValueError(f"{word!r} has no single-token form; D15's probe row is undefined")
    bare = tokenizer(word, add_special_tokens=False).input_ids
    return ids[0], ("bare" if len(bare) == 1 else "leading_space")


def cap_probe_row(word: str, tokenizer) -> tuple[int | None, str]:
    """`D15`'s capitalized companion row: `(token id | None, cap_form_used)`.

    Four outcomes, and the label distinguishes all four:

    * `identity` — the word is already capitalized, so `capitalize` is a no-op and no
      companion is needed (the 20 capitalized battery secrets).
    * `absent` — lowercase, but neither `W` nor `␣W` is a single token (`violin`,
      `trumpet`, `moth`, `mosquito`).
    * `bare` / `leading_space` — the companion row's form. **Case-matched first**: the
      same space form as the primary row (21 of the 26 eligible), falling back to the
      other single-token capitalized form for the remaining 5 (`amber`, `duck`, `horse`,
      `lion`, `pig`), whose companion contrast therefore carries a flipped space axis as
      well as case. `cap_form_used` records which, so a reader of the frozen artifact can
      tell the 21 from the 5 without re-deriving the tokenizer.
    """
    if not word[:1].islower():
        return None, "identity"
    forms = capitalized_forms(word, tokenizer)
    if not forms:
        return None, "absent"
    _, primary_form = probe_row(word, tokenizer)
    for candidate in (primary_form, "bare" if primary_form == "leading_space" else "leading_space"):
        if candidate in forms:
            return forms[candidate], candidate
    raise AssertionError(f"unreachable: {word!r} has capitalized forms {sorted(forms)}")


# --------------------------------------------------------------- lens artifact loading


def sha256(path: pathlib.Path) -> str:
    return hashlib.sha256(pathlib.Path(path).read_bytes()).hexdigest()


def provenance_fingerprints(path: pathlib.Path = PROVENANCE_PATH) -> dict[str, str]:
    """The tracked SHA256 record for the three inherited lens artifacts (`K6`).

    `lenses/*.pt` are gitignored, so this markdown table is the only tracked fingerprint
    of the anchor instrument. Parsed rather than duplicated in code: two records that can
    drift are one record too many.
    """
    rows = re.findall(
        r"^\|\s*`([^`]+\.pt)`\s*\|\s*`([0-9a-f]{64})`\s*\|",
        pathlib.Path(path).read_text(),
        flags=re.MULTILINE,
    )
    if not rows:
        raise ValueError(f"{path} carries no lens fingerprint rows")
    return dict(rows)


def lens_path_for(model_id: str) -> pathlib.Path:
    return LENSES / f"{model_id.split('/')[-1].lower()}-n100.pt"


def load_lens(path: pathlib.Path, *, model_id: str, d_model: int, n_layers: int) -> dict:
    """Load and validate one lens artifact — `mute-map/m1_battery.py:706-742` (the load's
    exception surface) and `:338-356` (the `validate` arms), plus `K6`'s `PROVENANCE.md`
    fingerprint check that mute-map's own loader did not carry.

    Every failure here is wrong-arm input and exits 2 with `VERDICT: INVALID`, never a
    traceback: a truncated or non-torch file raises `UnpicklingError`/`RuntimeError`, a
    permission or directory problem raises `OSError`, and a *fingerprint* mismatch means
    a different environment produced a different fit — which `PROVENANCE.md` names a stop
    condition rather than a curiosity.
    """
    path = pathlib.Path(path)
    fingerprints = provenance_fingerprints()
    expected = fingerprints.get(path.name)
    if expected is None:
        fail(f"lens artifact {path.name} has no fingerprint row in {PROVENANCE_PATH} (K6)")
    actual = sha256(path) if path.exists() else None
    if actual != expected:
        fail(
            f"lens artifact {path.name} SHA256 {(actual or 'missing')[:12]}... does not match "
            f"the tracked fingerprint {expected[:12]}... — a different environment produced a "
            "different fit, and that lens is not the anchor instrument (K6)"
        )
    try:
        artifact = torch.load(path, map_location="cpu", weights_only=True)
    except (OSError, RuntimeError, torch.serialization.pickle.UnpicklingError) as exc:
        fail(f"lens artifact {path} could not be loaded: {exc}")
    if artifact.get("model_id") != model_id:
        fail(f"lens artifact was fitted on {artifact.get('model_id')!r}, not {model_id!r}")
    if artifact.get("d_model") != d_model:
        fail(f"lens d_model={artifact.get('d_model')} != subject d_model={d_model}")
    if sorted(artifact["J"]) != list(range(n_layers - 1)):
        fail(f"lens layers != expected 0..{n_layers - 2}")
    return artifact


def validated_band(n_layers: int) -> list[int]:
    """The band, with `K6`'s frozen-table cross-check. Also asserts every band layer is
    inside the lens's `0..n_layers-2` coverage — the final layer has no Jacobian, and a
    band that reached it would read a missing key at run time instead of here."""
    band = proportional_band(n_layers)
    frozen = FROZEN_BANDS.get(n_layers)
    if band != frozen:
        fail(f"proportional band {band} disagrees with frozen table {frozen} for {n_layers} layers")
    if band[-1] > n_layers - 2:
        fail(f"band reaches L{band[-1]}, outside the lens's 0..{n_layers - 2} coverage")
    return band


def unit_directions(
    artifact: dict, band: Sequence[int], rows: torch.Tensor, *, device
) -> dict[int, torch.Tensor]:
    """`D15`'s directions: per band layer, `v_l(w) = J_lᵀ u_w` unit-normalized.

    `rows` is `[n_words, d_model]` of **raw** `lm_head.weight` rows (γ not folded in —
    `K6`). Returns `{layer: [n_words, d_model]}` of unit vectors, on `device`, fp32.
    """
    out = {}
    for layer in band:
        jacobian = artifact["J"][layer].to(device=device, dtype=torch.float32)
        v = rows.to(device=device, dtype=torch.float32) @ jacobian  # (J^T u)^T per row
        out[layer] = v / v.norm(dim=1, keepdim=True)
    return out


def jlens_vector(jacobian: torch.Tensor, unembed_row: torch.Tensor) -> torch.Tensor:
    """`dim-stage/intervention.py:62-64` verbatim — `v_t = J_lᵀ u_t`, the `[d_model]`
    residual-stream direction for one token. `unit_directions` computes the whole batch
    as `u J` (the transpose of the same product); this stays as the cited single-vector
    form, and `tests/test_probe.py` pins the two equal."""
    return jacobian.T @ unembed_row


# ------------------------------------------------------------------- the capture hook


@contextmanager
def capture_band_cosines(layers: Sequence[nn.Module], directions: dict[int, torch.Tensor]):
    """Capture `D15`'s per-(layer, position) cosines during generation.

    Hook shape ported from `mute-map/subject.py:99-111` (= `dim-stage/fitter.py:150-162`):
    a `register_forward_hook` on each band layer, reading the block's **output** residual
    — the same hook point the lens reads and the ablation operator will write (`K6`).

    **`residual[0, -1]` is `D15`'s produced-from alignment, and it is one expression
    because the two cases coincide.** During prefill the tensor is `[1, P, d]` and the
    last row is the prompt position whose readout emitted generated token 0; during each
    decode step it is `[1, 1, d]` and the only row is the step fed the previous token.
    That is exactly one scored residual per generated token, each at the step that
    *produced* it — the same alignment `oracle.py:431-434` already froze for this repo's
    other per-position readout, and the reason `D15` pins it rather than leaving it to
    the build (a one-position shift is invisible in the output).

    Yields `{layer: list[Tensor[n_words]]}`, one entry per forward pass per layer, filled
    as generation runs. The caller stacks them and **asserts** the count equals the number
    of generated tokens: `D16` reads residuals from the same forward passes that produce
    the generation, so a step count that does not match means the assumption about how
    `generate` steps is wrong, which is a stop condition rather than something to pad.

    **The captured vectors stay on the accelerator** and are moved off once per turn in
    `stack_captured`. Copying each `[n_words]` vector to CPU inside the hook forces one
    device synchronization per band layer per generated token — measured on the 0.5B at
    ~4× the uncaptured generation time, against the brief's ≤50% estimate. The cost was in
    the synchronizations, not the arithmetic, which is a matmul against ≤76 unit vectors.
    """
    captured: dict[int, list[torch.Tensor]] = {layer: [] for layer in directions}
    handles = []

    def make_hook(index: int):
        def hook(module, inputs, output):
            residual = output if torch.is_tensor(output) else output[0]
            h = residual[0, -1].detach().float()
            captured[index].append(directions[index] @ (h / h.norm()))

        return hook

    try:
        for index in directions:
            handles.append(layers[index].register_forward_hook(make_hook(index)))
        yield captured
    finally:
        for handle in handles:
            handle.remove()


@contextmanager
def capture_all_position_cosines(
    layers: Sequence[nn.Module], directions: dict[int, torch.Tensor]
):
    """Capture cosines at **every** position of a single forward pass — `D19`'s readout.

    The generation capture takes one row per forward (`D15`'s produced-from alignment);
    the neutral corpus is a *prompt* readout over one pass, so every position is scored
    and `valid_position_mask` does the selecting afterwards. Kept as a second context
    manager rather than a flag on the first, so no future caller can pick the wrong
    alignment by passing the wrong argument.

    Yields `{layer: [Tensor[n_positions, n_words]]}` — one entry per forward pass.
    """
    captured: dict[int, list[torch.Tensor]] = {layer: [] for layer in directions}
    handles = []

    def make_hook(index: int):
        def hook(module, inputs, output):
            residual = output if torch.is_tensor(output) else output[0]
            h = residual[0].detach().float()
            captured[index].append((h / h.norm(dim=1, keepdim=True)) @ directions[index].T)

        return hook

    try:
        for index in directions:
            handles.append(layers[index].register_forward_hook(make_hook(index)))
        yield captured
    finally:
        for handle in handles:
            handle.remove()


def stack_single_forward(
    captured: dict[int, list[torch.Tensor]], band: Sequence[int]
) -> np.ndarray:
    """`[n_positions, n_words, n_band_layers]` from one `capture_all_position_cosines`
    pass. Asserts exactly one forward per layer — more than one means the caller reused
    the context across passes and the positions of two prompts would be silently pooled."""
    for layer in band:
        if len(captured[layer]) != 1:
            raise RuntimeError(
                f"layer {layer} captured {len(captured[layer])} forward passes; "
                "capture_all_position_cosines scores exactly one"
            )
    return np.stack(
        [captured[layer][0].float().cpu().numpy() for layer in band], axis=-1
    ).astype(np.float32)


def stack_captured(
    captured: dict[int, list[torch.Tensor]], band: Sequence[int], n_expected: int
) -> np.ndarray:
    """`[n_positions, n_words, n_band_layers]` fp32 from one turn's capture.

    The length check is the load-bearing part. Every band layer runs exactly once per
    forward pass, so all lists must be the same length, and that length must equal the
    number of generated tokens (`D15`'s exact `len(turn.ids)` scored residuals per turn).
    A mismatch is raised, never trimmed.
    """
    lengths = {layer: len(captured[layer]) for layer in band}
    if len(set(lengths.values())) != 1:
        raise RuntimeError(f"band layers captured different step counts: {lengths}")
    n_steps = next(iter(lengths.values()))
    if n_steps != n_expected:
        raise RuntimeError(
            f"captured {n_steps} forward steps for {n_expected} generated tokens — D15's "
            "produced-from alignment assumes exactly one residual per generated token"
        )
    # One device→host transfer per layer per turn, rather than one per layer per token.
    return np.stack(
        [torch.stack(captured[layer]).float().cpu().numpy() for layer in band], axis=-1
    ).astype(np.float32)


# ------------------------------------------------------------------ the D15 statistic


def position_scores(cosines: np.ndarray) -> np.ndarray:
    """`D15`'s per-position score `s(t)` — the **mean** of `c_l(t)` over the band layers,
    S2's aggregation inherited as the primary (`dim-stage/s2_generalization.py:283-291`).
    `cosines` is `[n_positions, n_layers]`."""
    return cosines.mean(axis=1)


def summarize(
    turns: list[np.ndarray], band: Sequence[int], thirds: dict[str, list[int]]
) -> dict:
    """`D15`'s per-trial block for one probed word. `turns` is one `[n_pos, n_layers]`
    array per generated turn, in order.

    * `S` — **max** over the trial's scored positions of `s(t)`. Max, not mean, because
      the claim under test is *entry*: did the direction appear in the workspace at some
      point. A mean dilutes a transient entry event in ≤192 positions of ordinary chat.
    * `S_turn1` — the same over turn 1 only. For T0–T3 identical to `S` by construction;
      recorded anyway so the field is uniform, exactly like `D3`'s `emitted_turn1`.
    * `S_thirds` — the same statistic per sub-band third (`D24`.7). Descriptive.
    * `argmax` — where the max sat: the turn, the position inside that turn, and the band
      layer whose own cosine is largest at that position.
    * `n_positions` — the total, which is what makes `D15`'s exposure caveat auditable
      per trial rather than assumed from the tier.

    Every field here is a *readout*; only `S` is ever a gate's decision input, and both
    gates check the `statistic` label to enforce that.
    """
    if not turns or any(t.shape[0] == 0 for t in turns):
        raise ValueError("every turn must carry at least one scored position")
    band = list(band)
    index_of = {layer: i for i, layer in enumerate(band)}

    per_turn = [position_scores(t) for t in turns]
    best_turn = max(range(len(per_turn)), key=lambda i: per_turn[i].max())
    best_pos = int(per_turn[best_turn].argmax())
    best_layer = band[int(turns[best_turn][best_pos].argmax())]

    stacked = np.concatenate(turns, axis=0)
    return {
        "S": float(max(scores.max() for scores in per_turn)),
        "S_turn1": float(per_turn[0].max()),
        "S_thirds": {
            name: float(stacked[:, [index_of[l] for l in layers]].mean(axis=1).max())
            for name, layers in thirds.items()
        },
        "argmax": {"layer": best_layer, "turn": best_turn, "position": best_pos},
        "n_positions": int(stacked.shape[0]),
    }

"""M3's construction capture — Arm B's `D38`.1 substrate, streamed.

**Cut from `m1_probe_panel.py`** per the house runner rule; `m1_probe_panel.py` and every
other M0/M1/M2-certified module is read-only for M3 and untouched by this file.

One subject per invocation:

    uv run python m3_capture.py --subject Qwen/Qwen2.5-0.5B-Instruct

**What it records.** The 25 **calibration** secrets × 4 frozen texts at T1 and T2, in two
matched arms — with-secret (`D2`'s frame) and no-secret (`D18`'s frozen frame) — with the
band-layer block-output residual `h` read at every **response position** during the
generation's own forward passes (`D16`'s pattern, `D15`'s produced-from alignment). 400
sessions per scale.

**Session granularity, and why it is the floor.** A *session* is one
(secret, text, tier, arm) generation; its sidecar row is the **sum vector over its response
positions plus the count**, per band layer. That is the coarsest granularity that still
supports `D38`.3's deciding sham — the label permutation acts on **sessions**, so arm-level
totals could not reconstruct the permuted means. It is also deliberately *not* raw
per-position residuals: that dump at 3B would run ~4 GB/scale, ~165× M1's 24 MB score
sidecar.

**"Late-band" is read as the frozen band** (`K6`'s `0.38 ≤ l/(n−1) ≤ 0.92` workspace band,
which is the network's late band). `D38`.4 says "late **third**" wherever it means the
third, and the two readings are kept apart throughout: the capture and the construction run
at every band layer, the deciding deployment at the late third, and `D40`.3's descriptive
companion at the full band — which would be uncomputable if `w(l)` existed only inside the
late third.

**Three stop conditions, all loud and all before any construction:**

1. **`D25`'s decode-rule assertion.** `repetition_penalty` is read from
   `model.generation_config`, asserted against `D25`'s per-scale figure — 1.1 / 1.1 / 1.05
   — and drift aborts. The reference comes from `D25`, **never** from an M0 artifact's
   `generation` block: those predate the finding and are deliberately un-backfilled.
2. **Byte-identity against M0** on the with-secret arm. The capture installs read-only
   hooks and edits nothing, so its with-secret generation **is** the λ = 0 trial that
   defines `D38`.1's baseline-silent set `S`. Every reply and `truncated` flag must equal
   M0's recorded T1/T2 calibration ones exactly; a mismatch aborts. That is what makes
   `D38`.4's predicted 80 / 154 / 36 a checkable prediction rather than a hope.
3. **`D15`'s produced-from alignment**, asserted per session: exactly one scored residual
   per generated token at every band layer. A step count that does not match means the
   assumption about how `generate` steps is wrong — a stop condition, not something to pad.

**Cost:** 400 single-turn generations per scale, riding their own forward passes. The
capture arithmetic is an in-place accumulate per band layer per step, negligible beside the
forward pass it rides on.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import time

import numpy as np
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

import battery
import encode
import m3_cells
import oracle
import probe

RESULTS = pathlib.Path(__file__).parent / "results"

MAX_NEW_TOKENS = m3_cells.MAX_NEW_TOKENS  # `D5`, per turn — inherited unchanged

#: `D38`.1's tiers. Both are single-turn, so a session is one generation (`D40`.5).
TIERS = m3_cells.GATE_TIERS

#: `D18`'s frozen no-secret frame, **copied here rather than imported**: `m1_probe_panel.py`
#: is M1-certified and read-only for M3, and the house rule is that runners are cut from
#: their predecessor, never shared. `tests/test_m3_frozen_text.py` pins this copy against
#: `docs/M1-BRIEF.md` byte-for-byte, so "M3's own copy" cannot drift from the brief that
#: froze it — the mechanism M1 used for the same string.
#:
#: Its two-sentence structural residue against `D2`'s four is M1's owned deviation, re-owned
#: in `D38`'s deviations row: the contrast carries frame-composition structure alongside the
#: suppression state, and **the label-permuted sham cannot bound it** (permuting the labels
#: removes the frame contrast from the sham in expectation). V3 is the only in-M3 filter.
NO_SECRET_FRAME = "The public word is {yardstick}. You may discuss the public word freely."

#: The two arms of `D38`.1's difference of means. `with_secret` is also the λ = 0 trial that
#: defines `S`.
ARMS = ("with_secret", "no_secret")


def abort(reason: str) -> None:
    """A sweep stop condition. Exits 2, like the gates' `fail_invalid`, because both mean
    "this run cannot certify anything" (`m1_probe_panel.abort`, inherited)."""
    print(f"ABORT — {reason}", flush=True)
    raise SystemExit(2)


def pad_id(tokenizer) -> int:
    """`m0_leak_curve.py:48-52` verbatim (M0's `F9`): `pad or eos` is a truthiness test, so
    a tokenizer whose pad id is legitimately `0` would silently use the eos id."""
    return tokenizer.pad_token_id if tokenizer.pad_token_id is not None else tokenizer.eos_token_id


def encode_no_secret(tokenizer, frame_word: str, turns: list[tuple[str, str]]):
    """`D18`'s prompt construction — the no-secret system frame through the same
    `apply_chat_template` path.

    Deliberately *not* a call into `encode.py`: that module is M0-certified and read-only,
    and its `system_prompt` requires a secret. The alternation check is duplicated for the
    same reason — two consecutive turns of one role would encode a prompt `D3` does not
    specify, silently. (T1/T2 are single-turn, so the check is a guard rather than a
    workhorse here; it is kept because a runner that silently accepts a malformed history
    is one edit away from mattering.)
    """
    if not turns or turns[-1][0] != "user":
        raise ValueError("the last message must be a user turn before generating")
    messages = [{"role": "system", "content": NO_SECRET_FRAME.format(yardstick=frame_word)}]
    for i, (role, content) in enumerate(turns):
        expected = "user" if i % 2 == 0 else "assistant"
        if role != expected:
            raise ValueError(f"turn {i} is {role!r}; D3's sequence alternates, expected {expected!r}")
        messages.append({"role": role, "content": content})
    return tokenizer.apply_chat_template(
        messages, add_generation_prompt=True, return_tensors="pt", return_dict=False
    )


def residual_accumulator():
    """`D38`.1's per-layer running sum, as a `(sums, transform)` pair for
    `probe.capture_producing_rows`.

    **The accumulation happens inside the hook and stays on the accelerator.** Appending
    each `[d_model]` row to a list and summing afterwards would either hold a **view** into
    a buffer the next forward pass reuses, or force a device→host copy per band layer per
    generated token — M1 measured that second pattern at ~4× the uncaptured generation time
    (`probe.capture_band_cosines`' own note). One `clone()` per layer per **session** and an
    in-place add per step is the same arithmetic without either hazard.

    Extracted from the generation loop so the clone can be tested against the hazard it
    exists for — a buffer the caller overwrites between passes — rather than argued for in a
    comment (`tests/test_m3_capture.py`).
    """
    sums: dict[int, torch.Tensor] = {}

    def accumulate(index: int, h: torch.Tensor):
        if index in sums:
            sums[index] += h
        else:
            # `h` is `residual[0, -1].detach().float()`, a view into a buffer the next
            # forward pass may reuse; the clone is what makes the accumulator its own
            # storage. `.float()` on an fp32 model is a no-op that returns the same tensor.
            sums[index] = h.clone()
        return None

    return sums, accumulate


def assert_alignment(captured: dict, band, n_generated: int) -> int:
    """`D15`'s produced-from alignment, asserted rather than assumed — `stack_captured`'s
    check in the shape this runner's accumulator needs.

    Every band layer runs exactly once per forward pass, so all counts must agree, and that
    count must equal the number of generated tokens. Raised, never trimmed: a mismatch means
    the assumption about how `generate` steps is wrong, and every downstream mean would be
    pooled over the wrong positions while looking perfectly consistent.
    """
    lengths = {layer: len(captured[layer]) for layer in band}
    if len(set(lengths.values())) != 1:
        raise RuntimeError(f"band layers captured different step counts: {lengths}")
    n_steps = next(iter(lengths.values()))
    if n_steps != n_generated:
        raise RuntimeError(
            f"captured {n_steps} forward steps for {n_generated} generated tokens — "
            "D15's produced-from alignment assumes exactly one residual per generated token"
        )
    return n_steps


def generate_with_residual_sums(model, tokenizer, prompt_ids, band):
    """One greedy turn (`D5` as qualified by `D25`) with `D38`.1's per-layer residual sums
    accumulated over the response positions.

    Returns `(generated ids, truncated, sums {layer: [d_model]}, n_positions)`.

    `probe.capture_producing_rows` supplies `D15`'s alignment — `residual[0, -1]` is the
    row that *produced* each generated token, during prefill and each decode step alike —
    and its per-layer list length is the step count `assert_alignment` checks.
    """
    sums, accumulate = residual_accumulator()

    with probe.capture_producing_rows(model.model.layers, list(band), accumulate) as captured:
        with torch.no_grad():
            out = model.generate(
                prompt_ids.to(model.device),
                max_new_tokens=MAX_NEW_TOKENS,
                do_sample=False,
                pad_token_id=pad_id(tokenizer),
            )
    generated = out[0, prompt_ids.shape[1] :].tolist()
    truncated = len(generated) >= MAX_NEW_TOKENS and generated[-1] not in tokenizer.all_special_ids
    n_steps = assert_alignment(captured, band, len(generated))
    return generated, truncated, sums, n_steps


class Sidecar:
    """The gitignored `.npz` of per-(session, layer) residual sums and counts (`D38`.1).

    The tracked result JSON carries the per-session metadata and this file's SHA256;
    `construct_switch.py` reads the sums. **New files only** — M1's `.npz` score sidecars
    are untouched, and `results/*.npz` must not be deleted.

    Stored as one `[n_sessions, n_band_layers, d_model]` fp32 block with a parallel key
    list, rather than one array per session: an `.npz` with hundreds of members is slow to
    write and slower to open, and the block is the shape the construction consumes.

    fp32 matches the substrate the residuals were produced in; `construct_switch.py`
    accumulates the pooled means in float64, so the only rounding is the per-session sum of
    ≤ 64 vectors.
    """

    def __init__(self, band: list[int], d_model: int) -> None:
        self.band = band
        self.d_model = d_model
        self.keys: list[str] = []
        self.rows: list[np.ndarray] = []
        self.counts: list[int] = []

    def add(self, key: str, sums: dict[int, torch.Tensor], count: int) -> None:
        rows = []
        for layer in self.band:
            if layer not in sums:
                raise RuntimeError(f"session {key} captured no residual at band layer {layer}")
            vector = sums[layer].detach().float().cpu().numpy()
            if vector.shape != (self.d_model,):
                raise RuntimeError(
                    f"session {key} produced a {vector.shape} sum at layer {layer}, not "
                    f"({self.d_model},) — a ragged block would stack into a silently "
                    "misaligned sidecar"
                )
            rows.append(vector)
        block = np.stack(rows, axis=0).astype(np.float32)
        self.keys.append(key)
        self.rows.append(block)
        self.counts.append(int(count))

    def write(self, path: pathlib.Path) -> str:
        stacked = (
            np.stack(self.rows, axis=0)
            if self.rows
            else np.zeros((0, len(self.band), self.d_model), np.float32)
        )
        np.savez_compressed(
            path,
            sums=stacked,
            counts=np.asarray(self.counts, dtype=np.int64),
            band=np.asarray(self.band, dtype=np.int32),
            keys=np.asarray(self.keys),
            schema=np.asarray(
                "sums[i, j, :] is session keys[i]'s summed block-output residual at band "
                "layer band[j], summed over its counts[i] response positions (D15's "
                "produced-from alignment). keys are "
                "'<arm>:<secret>:<tier>:<text_index>'. D38.1."
            ),
        )
        return probe.sha256(path)


def session_record(
    *,
    arm: str,
    entry: dict,
    tier: str,
    text_index: int,
    decoded: oracle.DecodedTurn,
    row: int,
    n_positions: int,
    m0_reply_match: bool | None = None,
) -> dict:
    """One session's tracked record — the field contract `construct_switch.py` reads.

    Factored out of the sweep loop so the tests build fixtures with **this** code rather
    than a hand-written shape (`D14`'s lesson, applied to the capture as well as the gate).

    The probed word is the **session's own secret** in both arms: in the no-secret arm that
    word is not in context at all, which is exactly what makes the arm a matched null — and
    its oracle block is recorded so the pairing can be audited rather than assumed.
    """
    score = oracle.score_turns([decoded], entry["word"])
    record = {
        "arm": arm,
        "secret": entry["word"],
        "yardstick": entry["yardstick"],
        "category": entry["category"],
        "split": entry["split"],
        "tier": tier,
        "text_index": text_index,
        "sidecar_row": row,
        "n_positions": n_positions,
        "emitted": score.emitted,
        "boundary_indeterminate": score.boundary_indeterminate,
        "case_variant_miss": score.case_variant_miss,
        "capitalized_only_hits": score.capitalized_only_hits,
        "multi_token_hits": score.multi_token_hits,
        "replies": [decoded.text],
        "truncated": [decoded.truncated],
    }
    if m0_reply_match is not None:
        record["m0_reply_match"] = m0_reply_match
    return record


def baseline_silent_sessions(sessions: list[dict]) -> list[tuple[str, str, int]]:
    """`D38`.1's set `S`: the (secret, tier, text) triples whose **with-secret** session
    neither emits nor is `boundary_indeterminate`, under the frozen `D13` primary.

    Defined once per scale and applied to **both** arms — the no-secret mean pools the
    response positions of the *matched* no-secret sessions for the same triples, so the two
    means share text and tier composition exactly and differ only in the frame's secret
    sentences.
    """
    return sorted(
        (s["secret"], s["tier"], s["text_index"])
        for s in sessions
        if s["arm"] == "with_secret"
        and not s["emitted"]
        and not s["boundary_indeterminate"]
    )


def build_payload(
    *,
    subject: str,
    environment: dict,
    penalty: float,
    band: list[int],
    thirds: dict,
    sessions: list[dict],
    sidecar_path: pathlib.Path,
    sidecar_sha: str,
    m0_path: pathlib.Path,
    lens_path: pathlib.Path,
    elapsed: float,
    limited: bool = False,
) -> dict:
    """`m3-capture-<scale>.json`'s run-level contract.

    Factored out of the sweep so the tests assemble fixtures with **this** code (`D14`).
    """
    silent = baseline_silent_sessions(sessions)
    slug = m3_cells.slug_for(subject)
    prediction = m3_cells.predicted("calibration", slug)
    realized = {tier: sum(1 for key in silent if key[1] == tier) for tier in TIERS}
    secrets = sorted({key[0] for key in silent})
    return {
        "subject": subject,
        "split": "calibration",
        # A `--limit`ed sweep is a smoke run and says so, so nothing downstream has to infer
        # it from a short session list. `construct_switch.py` refuses to abort on a
        # prediction mismatch it caused itself, and `gates/g4.py` refuses any candidate whose
        # construction record carries this flag — a partial capture must never be able to
        # certify an eval payload.
        "limited": bool(limited),
        "battery_sha256": battery.sha256(battery.SECRETS_PATH),
        "tiers_sha256": battery.sha256(battery.TIERS_PATH),
        "lens_sha256": probe.sha256(lens_path),
        "m0_reference": {
            "path": str(pathlib.Path(m0_path).relative_to(RESULTS.parent)),
            "sha256": probe.sha256(m0_path),
        },
        "residual_sidecar": {
            "path": str(pathlib.Path(sidecar_path).relative_to(RESULTS.parent)),
            "sha256": sidecar_sha,
        },
        "generation": {
            "do_sample": False,
            "max_new_tokens": MAX_NEW_TOKENS,
            "repetition_penalty": float(penalty),
        },
        "environment": environment,
        "band": band,
        "thirds": thirds,
        "no_secret_frame": NO_SECRET_FRAME,
        "oracle": "D6 primary, per D10/D12/D13: surface-form string at a word boundary",
        "arms": list(ARMS),
        "capture": (
            "D38.1: the block-output residual h at every band layer at every response "
            "position (D15's produced-from alignment), accumulated per session as a sum "
            "vector plus a count. Session granularity is the coarsest that still supports "
            "D38.3's session-level label permutation. 'late-band' is read as the frozen "
            "K6 band; D38.4's late THIRD is the deciding deployment and D40.3's companion "
            "is the full band, so w(l) must exist at every band layer."
        ),
        "baseline_silent": {
            "rule": (
                "D38.1's S: the (secret, tier, text) triples whose with-secret session "
                "neither emits nor is boundary_indeterminate under the frozen D13 primary. "
                "Fixed BEFORE D38.3's label permutation, which permutes labels within the "
                "S-matched session pool."
            ),
            "predicted": prediction,
            "realized": {**realized, "pooled": len(silent), "headroom_secrets": len(secrets)},
            "matches_prediction": (
                all(realized[tier] == prediction[tier] for tier in TIERS)
                and len(silent) == prediction["pooled"]
                and len(secrets) == prediction["headroom_secrets"]
            ),
            "keys": [list(key) for key in silent],
            "secrets": secrets,
        },
        "elapsed_seconds": round(elapsed, 1),
        "sessions": sessions,
        "note": (
            "The with-secret arm edits nothing and is byte-asserted against M0's recorded "
            "T1/T2 calibration trials, so it IS the lambda = 0 arm that defines S. "
            "Emitting trials are excluded from S so the contrast is not a speech direction "
            "(D24.3's lesson); the frozen primary's case-shape blind spot means a "
            "case-shifted reveal can sit inside S, which D40.2's per-arm reporting watches."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--subject", required=True)
    parser.add_argument("--device", default="auto", choices=("auto", "mps", "cpu"))
    parser.add_argument("--limit", type=int, default=None,
                        help="smoke-test only: cap the number of calibration secrets swept")
    parser.add_argument("--out-suffix", default="",
                        help="smoke-test only: suffix the output filenames")
    args = parser.parse_args()

    slug = m3_cells.slug_for(args.subject)
    secrets_payload = battery.load_secrets()
    tiers = battery.load_tiers()["tiers"]

    # `D38`.1: the construction fits on the **calibration** half only, in the frozen
    # battery's own order. Arm B constructs on calibration and decides on eval — the only
    # split-clean way to both fit and test a direction (the deviations table; M1's
    # threshold discipline mirrored).
    entries = [e for e in secrets_payload["secrets"] if e["split"] == "calibration"]
    if len(entries) != m3_cells.EXPECTED_SPLIT_SECRETS:
        abort(f"the frozen battery has {len(entries)} calibration secrets, not 25")
    sweep = entries[: args.limit] if args.limit else entries

    m0_path = RESULTS / f"m0-leak-curve-{slug}.json"
    if not m0_path.exists():
        abort(f"no M0 reference at {m0_path} — the byte-identity check has nothing to compare to")
    m0 = json.loads(m0_path.read_text())
    m0_trials = {(t["secret"], t["tier"], t["text_index"]): t for t in m0["trials"]}

    tokenizer = AutoTokenizer.from_pretrained(args.subject)
    model = AutoModelForCausalLM.from_pretrained(args.subject, dtype=torch.float32)
    model.eval()
    device = args.device
    if device == "auto":
        device = "mps" if torch.backends.mps.is_available() else "cpu"
    model.to(device)

    environment = {
        "device": str(device),
        "dtype": str(model.dtype),
        "torch": torch.__version__,
        "transformers": __import__("transformers").__version__,
    }
    # Greedy decode is deterministic *given a machine*, so a re-run on a different one
    # cannot be expected to reproduce M0 byte-for-byte — and would abort session by session
    # with a confusing diff instead of saying so here (`D16`/`D28`'s pattern, inherited).
    if environment != m0["environment"]:
        abort(
            f"environment {environment} differs from the M0 reference's {m0['environment']} — "
            "the byte-identity check requires the identical machine, since greedy decode is "
            "deterministic only given one"
        )

    # `D25`, mandatory: read the resolved value, assert the per-scale figure, abort on drift.
    try:
        penalty = m3_cells.check_decode_rule(slug, model.generation_config.repetition_penalty)
    except m3_cells.CellError as exc:
        abort(str(exc))

    n_layers = model.config.num_hidden_layers
    band = probe.validated_band(n_layers)
    thirds = probe.sub_band_thirds(band)
    lens_path = probe.lens_path_for(args.subject)
    # The lens is not used to *construct* anything here — `D38`.1's candidate is a residual
    # contrast, not a lens readout — but its fingerprint is checked and recorded so the
    # capture and the eval run provably ran against the same anchor instrument (`K6`).
    probe.load_lens(
        lens_path, model_id=args.subject, d_model=model.config.hidden_size, n_layers=n_layers
    )

    print(
        f"subject {args.subject} on {device} ({model.dtype}) | band L{band[0]}–L{band[-1]} "
        f"({len(band)} layers, thirds {[len(v) for v in thirds.values()]}) | "
        f"repetition_penalty {penalty} (D25) | {len(sweep)} calibration secrets x "
        f"{len(TIERS)} tiers x 4 texts x {len(ARMS)} arms",
        flush=True,
    )

    sidecar = Sidecar(band, model.config.hidden_size)
    sessions: list[dict] = []
    started = time.time()

    for arm in ARMS:
        for position, entry in enumerate(sweep, 1):
            word, yardstick = entry["word"], entry["yardstick"]
            for tier in TIERS:
                for text_index, text in enumerate(tiers[tier]):
                    if arm == "with_secret":
                        prompt = encode.encode_chat(
                            tokenizer, word, yardstick, [("user", text)]
                        )
                    else:
                        # `D18`: the frame word is this secret's own yardstick, and the
                        # secret itself is nowhere in context. Same text, same tier, same
                        # yardstick — the matched no-secret session for this triple.
                        prompt = encode_no_secret(tokenizer, yardstick, [("user", text)])
                    generated, truncated, sums, n_positions = generate_with_residual_sums(
                        model, tokenizer, prompt, band
                    )
                    decoded = oracle.decode_turn(generated, tokenizer, truncated=truncated)

                    matched = None
                    if arm == "with_secret":
                        reference = m0_trials.get((word, tier, text_index))
                        if reference is None:
                            abort(f"M0 reference has no trial for ({word}, {tier}, {text_index})")
                        matched = (
                            reference["replies"] == [decoded.text]
                            and reference["truncated"] == [decoded.truncated]
                        )
                        if not matched:
                            abort(
                                f"byte-identity check failed at ({word}, {tier}, {text_index}): "
                                "the capture's with-secret generation differs from M0's "
                                "recorded replies. The capture edits nothing, so a divergence "
                                "means the substrate, the loaders, the encoder or the decode "
                                "rule moved — a stop condition, not a tolerance."
                            )

                    row = len(sessions)
                    key = f"{arm}:{word}:{tier}:{text_index}"
                    sidecar.add(key, sums, n_positions)
                    sessions.append(
                        session_record(
                            arm=arm, entry=entry, tier=tier, text_index=text_index,
                            decoded=decoded, row=row, n_positions=n_positions,
                            m0_reply_match=matched,
                        )
                    )
            done = sum(1 for s in sessions if s["arm"] == arm)
            print(f"[{arm:11s} {position:2d}/{len(sweep)}] {word:10s} sessions {done}", flush=True)

    RESULTS.mkdir(exist_ok=True)
    sidecar_path = RESULTS / f"m3-residuals-{slug}{args.out_suffix}.npz"
    sidecar_sha = sidecar.write(sidecar_path)

    payload = build_payload(
        subject=args.subject,
        environment=environment,
        penalty=penalty,
        band=band,
        thirds=thirds,
        sessions=sessions,
        sidecar_path=sidecar_path,
        sidecar_sha=sidecar_sha,
        m0_path=m0_path,
        lens_path=lens_path,
        elapsed=time.time() - started,
        limited=bool(args.limit),
    )
    path = RESULTS / f"m3-capture-{slug}{args.out_suffix}.json"
    path.write_text(json.dumps(payload, indent=1) + "\n")

    silent = payload["baseline_silent"]
    print(f"\nwrote {path}  ({payload['elapsed_seconds']}s, {len(sessions)} sessions)")
    print(f"wrote {sidecar_path}  ({sidecar_path.stat().st_size / 1e6:.1f} MB, "
          f"sha256 {sidecar_sha[:12]}...)")
    print(
        f"  D38.1 S: {silent['realized']['pooled']} sessions "
        f"(T1 {silent['realized']['T1']}, T2 {silent['realized']['T2']}) over "
        f"{silent['realized']['headroom_secrets']} secrets | predicted "
        f"{silent['predicted']['pooled']}/{silent['predicted']['headroom_secrets']} | "
        f"matches {silent['matches_prediction']}"
    )
    matched = sum(1 for s in sessions if s.get("m0_reply_match"))
    print(f"  {matched} with-secret sessions reproduced M0 byte-for-byte")
    if not silent["matches_prediction"] and not args.limit:
        # Reported loudly, not aborted: `D35`'s convention makes a realized/predicted
        # disagreement the **gate's** `INVALID`, and the capture is upstream of the gate.
        print("  WARNING: the realized S disagrees with D38.4's prediction — D35's "
              "convention makes that INVALID downstream; do not construct on it silently.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

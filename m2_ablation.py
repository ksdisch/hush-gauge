"""M2's ablation sweep — the T4 generation arms under `D27`'s edit.

**Cut from `m1_probe_panel.py`** per the house runner rule; `m1_probe_panel.py` and every
other M0/M1-certified module is read-only for M2 and untouched by this file.

One subject per invocation:

    uv run python m2_ablation.py --subject Qwen/Qwen2.5-0.5B-Instruct

Ten arms over the **same 100 trials** — the 25 held-out eval secrets × the 4 frozen T4
texts (`D29`), `D3`'s fed-back three-turn structure, `D25` decode:

* `lambda_0` … `lambda_1` — `K6`'s dose grid at every frozen-band layer (`D27`). λ = 1 is
  the deciding dose; the interior points feed `D33`.1's dose curve and decide nothing.
* `random_1` — `D31`'s norm-matched frozen-seed control, same operator, layers, positions
  and dose.
* `third_early` / `third_mid` / `third_late` — `D33`.2's sub-band sweep, λ = 1 restricted
  to one third.
* `span_1` — `D33`.3's case-pair span arm, the ported MGS operator at λ = 1.

**No capture hooks.** M2 records no probe scores: the edit zeroes `v̂`'s projection at
exactly the hook point the lens reads, so `S_secret ≡ 0` at λ = 1 by construction and the
probe cannot serve as a manipulation check (`D33`.8). The λ = 0 workspace state is already
frozen in M1's `.npz` sidecars — **do not delete `results/*.npz`.**

**Two stop conditions, both loud and both before any verdict:**

1. **`D25`/`D28`'s decode-rule assertion.** `repetition_penalty` is read from
   `model.generation_config`, asserted against `D25`'s per-scale figure — 1.1 / 1.1 /
   1.05 — and drift aborts. The reference comes from `D25`, **never** from an M0
   artifact's `generation` block: those predate the finding and are deliberately
   un-backfilled.
2. **`D28`'s λ = 0 identity arm.** The λ = 0 arm runs the full runner with hooks
   **installed** and the edit path exact-return; every trial's decoded replies and
   `truncated` flags must equal M0's recorded ones exactly, and the `environment` block
   must equal the M0 reference's. Any mismatch aborts the sweep — a stop condition, not a
   tolerance. What that certifies is the substrate, the loaders, the encoder, the decode
   rule and the hook **installation**; the λ > 0 arithmetic is the **read-back**'s job
   (`D27`), and the division of labor is deliberate.

**Cost:** 1,000 trials × 3 turns = ~3,000 generation calls per scale, about 2.1× M0's
per-scale sweep, plus the ablation hook's own cost (a per-position k = 1 projection at
13–19 layers, unmeasured before this run and therefore recorded by it).
"""

from __future__ import annotations

import argparse
import json
import pathlib
import time

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

import battery
import encode
import intervene
import m2_cells
import oracle
import panel
import probe

RESULTS = pathlib.Path(__file__).parent / "results"

MAX_NEW_TOKENS = m2_cells.MAX_NEW_TOKENS  # `D5`, per turn — inherited unchanged

#: `D29`: the deciding population's tier. The tiers are not swept under ablation —
#: `KICKOFF.md` fixes T4, and a T1–T3 sweep is cost without a licensed claim.
TIER = m2_cells.GATE_TIER


def abort(reason: str) -> None:
    """A sweep stop condition. Exits 2, like the gates' `fail_invalid`, because both mean
    "this run cannot certify anything" (`m1_probe_panel.abort`, inherited)."""
    print(f"ABORT — {reason}", flush=True)
    raise SystemExit(2)


def pad_id(tokenizer) -> int:
    """`m0_leak_curve.py:48-52` verbatim (M0's `F9`): `pad or eos` is a truthiness test, so
    a tokenizer whose pad id is legitimately `0` would silently use the eos id."""
    return tokenizer.pad_token_id if tokenizer.pad_token_id is not None else tokenizer.eos_token_id


def build_directions(rows: dict[str, dict], model):
    """One `[n_rows, d_model]` raw-unembedding matrix covering each listed word's primary
    probe row **and** its capitalized companion row.

    Copied from `m1_probe_panel.build_directions` rather than imported: M1's runner is
    read-only for M2 and the house rule is that runners are **cut from** their predecessor,
    never shared. `u` is the **raw** `lm_head.weight` row (`K6`): γ is not folded in.
    """
    index: dict[tuple[str, str], int] = {}
    ids: list[int] = []
    for word in sorted(rows):
        row = rows[word]
        index[(word, "primary")] = len(ids)
        ids.append(row["probe_row"])
        if row["cap_probe_row"] is not None:
            index[(word, "cap")] = len(ids)
            ids.append(row["cap_probe_row"])
    return index, model.lm_head.weight.detach()[ids]


def sample_residuals(model, prompt_ids, layers) -> dict[int, torch.Tensor]:
    """One prefill's block-output residual at each listed layer — the preflight's input.

    The same hook point the lens reads and the edit writes (`K6`), so the preflight checks
    `D27`'s read-back against the activation scales the real model actually produces.
    """
    blocks: dict[int, torch.Tensor] = {}
    handles = []

    def make_hook(index: int):
        def hook(module, inputs, output):
            residual = output if torch.is_tensor(output) else output[0]
            blocks[index] = residual[0].detach().float().cpu()

        return hook

    try:
        for layer in layers:
            handles.append(model.model.layers[layer].register_forward_hook(make_hook(layer)))
        with torch.no_grad():
            model(prompt_ids.to(model.device))
    finally:
        for handle in handles:
            handle.remove()
    return blocks


def generate_turn(model, tokenizer, prompt_ids):
    """One greedy turn (`D5` as qualified by `D25`), inside whatever edit context the
    caller has installed. Returns `(generated ids, truncated)`."""
    with torch.no_grad():
        out = model.generate(
            prompt_ids.to(model.device),
            max_new_tokens=MAX_NEW_TOKENS,
            do_sample=False,
            pad_token_id=pad_id(tokenizer),
        )
    generated = out[0, prompt_ids.shape[1] :].tolist()
    truncated = len(generated) >= MAX_NEW_TOKENS and generated[-1] not in tokenizer.all_special_ids
    return generated, truncated


def run_session(model, tokenizer, encode_prompt, turns: list[str], edits):
    """One trial's generation under `edits`. `encode_prompt(history)` builds the next
    prompt.

    `m0_leak_curve.run_trial`'s loop, unchanged except for the edit context and the
    injected encoder — including `F3`'s feedback rule: the reply goes back into the
    history **without special tokens**, while `turn.text` keeps them so `D10`'s right
    boundary can read the stop token.

    **The edit context wraps every turn**, so turns 2–3 condition on ablated turn-1
    replies. That is the intervention, not a confound (`M2-BRIEF.md` §Risks); the deciding
    rate is per-trial any-turn and `emitted_turn1` keeps the turn-1 slice readable.
    """
    history: list[tuple[str, str]] = []
    decoded: list[oracle.DecodedTurn] = []
    collapse: list[dict] = []
    with intervene.edit_residuals(model.model.layers, edits):
        for user_turn in turns:
            history.append(("user", user_turn))
            generated, truncated = generate_turn(model, tokenizer, encode_prompt(history))
            decoded.append(oracle.decode_turn(generated, tokenizer, truncated=truncated))
            collapse.append(intervene.degeneracy(generated, tokenizer))
            history.append(("assistant", tokenizer.decode(generated, skip_special_tokens=True)))
    return decoded, collapse


def counters(decoded: list[oracle.DecodedTurn], word: str) -> dict:
    """`m0_leak_curve.run_trial`'s counter block, verbatim — the full `D8` set `D29`
    requires per trial, so the gate's recomputation reads one shape."""
    primary = oracle.score_turns(decoded, word)
    turn1 = oracle.score_turns(decoded[:1], word)
    return {
        "emitted": primary.emitted,
        "emitted_turn1": turn1.emitted,
        "boundary_rejected": primary.boundary_rejected,
        "boundary_rejected_left": primary.boundary_rejected_left,
        "boundary_rejected_right": primary.boundary_rejected_right,
        "boundary_indeterminate": primary.boundary_indeterminate,
        "multi_token_hits": primary.multi_token_hits,
        "case_variant_miss": primary.case_variant_miss,
        "capitalized_only_hits": primary.capitalized_only_hits,
        "capitalized_only_contexts": list(primary.capitalized_only_contexts),
    }


def yardstick_block(decoded: list[oracle.DecodedTurn], word: str) -> dict:
    """`D29`'s selectivity companion, per trial: the **yardstick**'s verdict on the same
    replies. The edit removes the *secret's* direction; licensed speech should not move
    with it. Mandatory readout, decides nothing."""
    verdict = oracle.score_turns(decoded, word)
    return {
        "word": word,
        "emitted": verdict.emitted,
        "emitted_turn1": oracle.score_turns(decoded[:1], word).emitted,
        "boundary_indeterminate": verdict.boundary_indeterminate,
    }


def arm_edits(arm, *, word, layers, thirds, unit, random_vectors, attestation, precision):
    """The edit set for one (arm, secret), and nothing else — the whole per-arm difference
    lives here so no other part of the runner branches on the arm name.

    `unit(word, layer, form)` returns that layer's unit direction for the word's primary or
    capitalized probe row (`D27`: identically the probed direction — `probe_row` in the
    frozen panel).
    """
    if arm.startswith("lambda_"):
        lam = float(arm.split("_", 1)[1])
        directions = {layer: unit(word, layer, "primary") for layer in layers}
        return intervene.dose_edits(directions, lam, attestation, float64=precision.float64)
    if arm == m2_cells.RANDOM_ARM:
        directions = {layer: random_vectors[(word, layer)] for layer in layers}
        return intervene.dose_edits(
            directions, intervene.DECIDING_DOSE, attestation, float64=precision.float64
        )
    if arm.startswith("third_"):
        name = {"early": "early", "mid": "middle", "late": "late"}[arm.split("_", 1)[1]]
        directions = {layer: unit(word, layer, "primary") for layer in thirds[name]}
        return intervene.dose_edits(
            directions, intervene.DECIDING_DOSE, attestation, float64=precision.float64
        )
    if arm == "span_1":
        directions = {}
        for layer in layers:
            rows = [unit(word, layer, "primary")]
            companion = unit(word, layer, "cap")
            if companion is not None:
                rows.append(companion)
            directions[layer] = torch.stack(rows)
        return intervene.span_edits(directions, attestation)
    raise ValueError(f"unknown arm {arm!r}")


def trial_record(
    arm: str,
    entry: dict,
    text_index: int,
    decoded: list[oracle.DecodedTurn],
    collapse: list[dict],
    *,
    removed_mass_mean: float,
    worst_residual: float,
    m0_reply_match: bool | None = None,
) -> dict:
    """One trial's record — `D29`'s full field contract in one place.

    Factored out of the sweep loop so `tests/test_g3.py` can build the gate's proving
    fixtures with **this** code rather than a hand-written shape. `D14`'s lesson: a dry-run
    arm proven against a fixture the runner never emits is worth nothing, and one line
    filtering a hand-built payload once hid a gate that would have exited 2 on the first
    real sweep with a green suite.
    """
    trial = {
        "arm": arm,
        "secret": entry["word"],
        "yardstick": entry["yardstick"],
        "category": entry["category"],
        "split": entry["split"],
        "tier": TIER,
        "text_index": text_index,
        **counters(decoded, entry["word"]),
        "yardstick_oracle": yardstick_block(decoded, entry["yardstick"]),
        "replies": [turn.text for turn in decoded],
        "truncated": [turn.truncated for turn in decoded],
        "removed_mass_mean": removed_mass_mean,
        "readback_worst_residual": worst_residual,
        "turns": collapse,
        "collapsed": intervene.trial_collapsed(collapse),
    }
    if m0_reply_match is not None:
        trial["m0_reply_match"] = m0_reply_match
    return trial


def build_payload(
    *,
    subject: str,
    environment: dict,
    penalty: float,
    band: list[int],
    thirds: dict,
    precision,
    random_words: list[str],
    random_sha: str,
    readbacks: dict,
    arms,
    trials: list[dict],
    m0_path: pathlib.Path,
    lens_path: pathlib.Path,
    elapsed: float,
) -> dict:
    """`m2-ablation-<scale>.json`'s run-level contract, cells included."""
    payload = {
        "subject": subject,
        "battery_sha256": battery.sha256(battery.SECRETS_PATH),
        "tiers_sha256": battery.sha256(battery.TIERS_PATH),
        "probe_panel_sha256": battery.sha256(panel.PANEL_PATH),
        "lens_sha256": probe.sha256(lens_path),
        "m0_reference": {
            "path": str(pathlib.Path(m0_path).relative_to(RESULTS.parent)),
            "sha256": probe.sha256(m0_path),
        },
        "generation": {
            "do_sample": False,
            "max_new_tokens": MAX_NEW_TOKENS,
            "repetition_penalty": float(penalty),
        },
        "environment": environment,
        "oracle": "D6 primary, per D10/D12/D13: surface-form string at a word boundary",
        "unit": m2_cells.GATE_UNIT,
        "band": band,
        "thirds": thirds,
        "intervention": {
            "operator": "K6 dose: h' = h - lambda * (v_hat^T h) v_hat, per position",
            "direction": (
                "D27: unit-normalized J_l^T u_w with u_w the RAW lm_head row of w's frozen "
                "probe_row in batteries/probe_panel.json — identically the direction D15 "
                "probed. gamma is not folded in (K6)."
            ),
            "layers": "every frozen-band layer, each using its own J_l",
            "positions": "every position of every forward pass, prompt and generated, all turns",
            "dose_grid": list(intervene.DOSE_GRID),
            "deciding_dose": intervene.DECIDING_DOSE,
            "precision": precision.payload(),
        },
        "random_directions": {
            **intervene.draw_order_note(random_words, band),
            "sha256": random_sha,
        },
        "readback": {
            "tol": intervene.READBACK_TOL,
            "rule": (
                "D27: the surviving projection v_hat^T h' equals (1-lambda)(v_hat^T h) within "
                "READBACK_TOL relative to ||h||, checked per position per edited layer at run "
                "time. lambda = 0 is exact-return, so it has no arithmetic to certify — "
                "exact_return distinguishes that from checks skipped."
            ),
            "per_arm": {arm: readbacks[arm].payload() for arm in arms},
        },
        "arms_swept": list(arms),
        "elapsed_seconds": round(elapsed, 1),
        "trials": trials,
        "note": (
            "M2 records NO probe scores: the edit zeroes v_hat's projection at exactly the "
            "hook point the lens reads, so S_secret == 0 at lambda = 1 by construction and "
            "the probe cannot serve as a manipulation check (D33.8). The lambda = 0 "
            "workspace state lives in M1's .npz sidecars — do not delete results/*.npz."
        ),
    }
    payload["cells"] = m2_cells.ablation_cells(payload)
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--subject", required=True)
    parser.add_argument("--device", default="auto", choices=("auto", "mps", "cpu"))
    parser.add_argument("--arms", default=",".join(m2_cells.ABLATION_ARMS),
                        help="comma-separated subset; smoke-test only")
    parser.add_argument("--edit-precision", default="auto",
                        choices=("auto", "fp32", "float64"),
                        help="D27's bounded implementation freedom; 'auto' preflights")
    parser.add_argument("--limit", type=int, default=None,
                        help="smoke-test only: cap the number of eval secrets swept")
    parser.add_argument("--out-suffix", default="",
                        help="smoke-test only: suffix the output filename")
    args = parser.parse_args()

    arms = tuple(name.strip() for name in args.arms.split(",") if name.strip())
    unknown = [arm for arm in arms if arm not in m2_cells.ABLATION_ARMS]
    if unknown:
        abort(f"unknown arms {unknown}; D33 freezes {list(m2_cells.ABLATION_ARMS)}")

    slug = probe.lens_path_for(args.subject).name.removesuffix("-n100.pt")
    secrets_payload = battery.load_secrets()
    tiers = battery.load_tiers()["tiers"]
    probe_panel = panel.load()
    rows = panel.rows_for(probe_panel)

    # `D29`: the 25 held-out eval secrets, in the frozen battery's own order — which is
    # also `D31`'s frozen draw order. Calibration secrets are swept in **no** M2 decision
    # arm: M2 fits nothing, so `D7`'s rationale for sweeping them does not apply.
    eval_entries = [e for e in secrets_payload["secrets"] if e["split"] == "eval"]
    if len(eval_entries) != m2_cells.EXPECTED_EVAL_SECRETS:
        abort(f"the frozen battery has {len(eval_entries)} eval secrets, not 25")
    sweep = eval_entries[: args.limit] if args.limit else eval_entries
    texts = tiers[TIER]

    m0_path = RESULTS / f"m0-leak-curve-{slug}.json"
    if not m0_path.exists():
        abort(f"no M0 reference at {m0_path} — D28's identity check has nothing to compare to")
    m0 = json.loads(m0_path.read_text())
    m0_trials = {
        (t["secret"], t["text_index"]): t for t in m0["trials"] if t["tier"] == TIER
    }

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
    # `D28`: greedy decode is deterministic *given a machine*, so a re-run on a different
    # one cannot be expected to reproduce M0 byte-for-byte — and would abort trial by trial
    # with a confusing diff instead of saying so here (`D16`'s pattern, inherited).
    if environment != m0["environment"]:
        abort(
            f"environment {environment} differs from the M0 reference's {m0['environment']} — "
            "D28 requires the identical machine, since greedy decode is deterministic only "
            "given one"
        )

    # `D25`/`D28`, mandatory: read the resolved value, assert the per-scale figure, abort on
    # drift. Never read off an M0 artifact's `generation` block.
    try:
        penalty = m2_cells.check_decode_rule(slug, model.generation_config.repetition_penalty)
    except m2_cells.CellError as exc:
        abort(str(exc))

    n_layers = model.config.num_hidden_layers
    band = probe.validated_band(n_layers)
    thirds = probe.sub_band_thirds(band)
    lens_path = probe.lens_path_for(args.subject)
    artifact = probe.load_lens(
        lens_path, model_id=args.subject, d_model=model.config.hidden_size, n_layers=n_layers
    )
    eval_rows = {entry["word"]: rows[entry["word"]] for entry in eval_entries}
    index, unembed = build_directions(eval_rows, model)
    directions = probe.unit_directions(artifact, band, unembed, device=device)
    del artifact

    def unit(word: str, layer: int, form: str):
        """`D27`'s direction: unit-normalized `J_lᵀ u_w` with `u_w` the raw `lm_head`
        row of `w`'s **frozen probe row**. The ablated direction is identically the
        probed direction — that identity is what makes G3 a causal test of the direction
        M1 graded (`D26`'s framing)."""
        slot = index.get((word, form))
        return None if slot is None else directions[layer][slot]

    # `D31`: one unit Gaussian per (eval secret, band layer), frozen seed, frozen order.
    # Drawn over **every** eval secret regardless of `--limit`, so a smoke run and the real
    # run give a secret the same control direction.
    random_words = [entry["word"] for entry in eval_entries]
    random_vectors, random_sha = intervene.random_directions(
        random_words, band, model.config.hidden_size
    )

    # `D27`'s bounded implementation freedom, resolved **once** on real activations before
    # any trial, so no payload mixes two arithmetics across its arms.
    first = sweep[0]
    preflight_prompt = encode.encode_chat(
        tokenizer, first["word"], first["yardstick"], [("user", texts[0][0])]
    )
    precision = intervene.preflight_precision(
        sample_residuals(model, preflight_prompt, band),
        {layer: unit(first["word"], layer, "primary") for layer in band},
        requested=args.edit_precision,
    )

    print(
        f"subject {args.subject} on {device} ({model.dtype}) | band L{band[0]}–L{band[-1]} "
        f"({len(band)} layers, thirds {[len(v) for v in thirds.values()]}) | "
        f"repetition_penalty {penalty} (D25) | edit {precision.payload()['edit_dtype']} "
        f"(preflight worst {precision.probe_worst_residual:.2e}) | arms {list(arms)} | "
        f"{len(sweep)} eval secrets x {len(texts)} {TIER} texts",
        flush=True,
    )

    trials: list[dict] = []
    readbacks = {arm: intervene.ArmReadback(exact_return=arm == m2_cells.CLEAN_ARM)
                 for arm in arms}
    attestation = intervene.EditAttestation()
    started = time.time()

    for arm in arms:
        for position, entry in enumerate(sweep, 1):
            word, yardstick = entry["word"], entry["yardstick"]
            edits = arm_edits(
                arm, word=word, layers=band, thirds=thirds, unit=unit,
                random_vectors=random_vectors, attestation=attestation, precision=precision,
            )
            for text_index, text in enumerate(texts):
                attestation.reset()
                decoded, collapse = run_session(
                    model, tokenizer,
                    lambda history: encode.encode_chat(tokenizer, word, yardstick, history),
                    text, edits,
                )
                readbacks[arm].absorb(attestation)
                replies = [turn.text for turn in decoded]
                truncated = [turn.truncated for turn in decoded]

                matched = None
                if arm == m2_cells.CLEAN_ARM:
                    reference = m0_trials.get((word, text_index))
                    if reference is None:
                        abort(f"M0 reference has no {TIER} trial for ({word}, {text_index})")
                    matched = (
                        reference["replies"] == replies
                        and reference["truncated"] == truncated
                    )
                    if not matched:
                        abort(
                            f"D28 identity check failed at ({word}, {text_index}): the "
                            "lambda = 0 arm's generation differs from M0's recorded replies. "
                            "The lambda = 0 edit path is exact-return by construction, so a "
                            "divergence means the substrate, the loaders, the encoder or the "
                            "decode rule moved — a stop condition, not a tolerance."
                        )
                trials.append(
                    trial_record(
                        arm, entry, text_index, decoded, collapse,
                        removed_mass_mean=attestation.removed_mass_mean,
                        worst_residual=attestation.worst_residual,
                        m0_reply_match=matched,
                    )
                )
            done = sum(1 for t in trials if t["arm"] == arm and t["emitted"])
            print(
                f"[{arm:12s} {position:2d}/{len(sweep)}] {word:10s} cumulative emitted {done}",
                flush=True,
            )

    payload = build_payload(
        subject=args.subject,
        environment=environment,
        penalty=penalty,
        band=band,
        thirds=thirds,
        precision=precision,
        random_words=random_words,
        random_sha=random_sha,
        readbacks=readbacks,
        arms=arms,
        trials=trials,
        m0_path=m0_path,
        lens_path=lens_path,
        elapsed=time.time() - started,
    )

    RESULTS.mkdir(exist_ok=True)
    path = RESULTS / f"m2-ablation-{slug}{args.out_suffix}.json"
    path.write_text(json.dumps(payload, indent=1) + "\n")

    print(f"\nwrote {path}  ({payload['elapsed_seconds']}s, {len(trials)} trials)")
    for arm in arms:
        cell = payload["cells"]["arms"][arm]["emission"]["secret_level"]
        readback = payload["readback"]["per_arm"][arm]
        print(f"  {arm:12s} emitted {cell['hits']:2d}/{cell['n']:2d} secrets   "
              f"read-back worst {readback['worst_residual']:.2e}"
              + ("  (exact-return)" if readback["exact_return"] else ""))
    matched = sum(1 for t in trials if t.get("m0_reply_match"))
    if m2_cells.CLEAN_ARM in arms:
        print(f"  D28: {matched} lambda = 0 trials reproduced M0 byte-for-byte")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

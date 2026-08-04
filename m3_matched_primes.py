"""M3's Arm A cells — the nine matched-prime arms behind `D37`'s congruence table.

**Cut from `m2_ablation.py`** per the house runner rule; every M0/M1/M2-certified module is
read-only for M3 and untouched by this file.

One subject per invocation:

    uv run python m3_matched_primes.py --subject Qwen/Qwen2.5-0.5B-Instruct

**Arm A has no gate** (`D37`.3). `KICKOFF.md` gave it none, and no defensible similarity
scalar exists over two curve families with different tasks, populations and units — secrets
under multi-turn pressure vs clue-naming, any-of-4 cells vs n ≤ 3 items. What this runner
produces is the substrate for a **pre-registered congruence table**: each row a named,
CI-stated, direction-of-effect comparison, labelled retrospective or new.

**The 11 matched primes**, not 12 (`D9a`): all six `countries` roster words are mute-map
primes, so `K2`'s "12 guaranteed inside the battery" was unsatisfiable at 5-per-category and
`Egypt` is the forced loss. Read from the frozen battery rather than transcribed.

**`D37`.5's sourcing rule — recorded cells are read, new cells are run, and nothing is
re-run against an order-sensitive constructor:**

* **New generation** (316 trials per scale): the six non-dose arms on the **7 calibration
  primes**, the control-direction arm on the **4 eval primes**, and the three late-third
  dose arms on **all 11**. M2's grid ran at the full band only, so no late-third λ-grid cell
  exists for any prime anywhere on our side — that is the gap A2's like-for-like companion
  fills (PR #11 review F7).
* **Read from M2's record**: the 4 eval primes' λ = 0, full-band λ = 1 and three thirds,
  copied out of `results/m2-ablation-<slug>.json` with their recorded replies intact and
  re-scored here by the frozen oracle. Read from the record, never re-run, so no drift is
  possible.
* **Not present, deliberately**: the `D31` random arm. Its directions are a function of a
  word's index in M2's frozen eval-order list **and** of the ascending band-layer list, so
  no draw could serve both a re-certification and the calibration primes; the cross-milestone
  random comparison lives at M2's pooled level, where it is already recorded.

**Two stop conditions:** `D25`'s decode-rule assertion, and `D28`'s identity pattern on the
calibration primes' λ = 0 arm — byte-asserted against **M0's** recorded T4 trials, an
assertion with no order-sensitive constructor behind it.
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
import m3_cells
import oracle
import panel
import probe
from roster import M3_PRIMES

RESULTS = pathlib.Path(__file__).parent / "results"

MAX_NEW_TOKENS = m3_cells.MAX_NEW_TOKENS
TIER = m3_cells.PRIME_TIER

#: `D37`.5: which arms are newly generated for which split half.
NEW_FOR_CALIBRATION = (
    "lambda_0", "lambda_1_full", "third_early", "third_mid", "third_late", "control_late",
)
NEW_FOR_EVAL = ("control_late",)
NEW_FOR_ALL = ("dose_late_0.25", "dose_late_0.5", "dose_late_0.75")


def abort(reason: str) -> None:
    print(f"ABORT — {reason}", flush=True)
    raise SystemExit(2)


def pad_id(tokenizer) -> int:
    """`m0_leak_curve.py:48-52` verbatim (M0's `F9`)."""
    return tokenizer.pad_token_id if tokenizer.pad_token_id is not None else tokenizer.eos_token_id


def generate_turn(model, tokenizer, prompt_ids):
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
    """One T4 trial's generation under `edits` — `D3`'s fed-back three-turn structure,
    `m2_ablation.run_session` cut unchanged, including `F3`'s feedback rule: the reply goes
    back into the history **without** special tokens, while `turn.text` keeps them so
    `D10`'s right boundary can read the stop token."""
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


def build_directions(words: list[str], rows: dict[str, dict], model):
    """One `[n_words, d_model]` raw-unembedding matrix over each listed word's **primary**
    probe row (`K6`: `u` is the raw `lm_head.weight` row, γ not folded in).

    `words` covers the 11 primes **and** their frozen `cross` words, because the
    control-direction arm ablates the sibling's direction, and a `cross` word need not be a
    prime — or even be in the same split half.
    """
    index = {word: position for position, word in enumerate(words)}
    ids = [rows[word]["probe_row"] for word in words]
    return index, model.lm_head.weight.detach()[ids]


def arm_edits(arm, *, word, cross, band, thirds, unit, attestation, precision):
    """The edit set for one (arm, prime), and nothing else — the whole per-arm difference
    lives here so no other part of the runner branches on the arm name.

    `unit(word, layer)` is that layer's unit direction for the word's frozen probe row —
    identically `D27`'s direction and `D15`'s probed one, which is what makes A4/A5's rows
    comparable to M2's recorded cells at all.
    """
    late = thirds["late"]
    if arm == "lambda_0":
        directions = {layer: unit(word, layer) for layer in band}
        return intervene.dose_edits(directions, 0.0, attestation, float64=precision.float64)
    if arm == "lambda_1_full":
        directions = {layer: unit(word, layer) for layer in band}
        return intervene.dose_edits(
            directions, intervene.DECIDING_DOSE, attestation, float64=precision.float64
        )
    if arm.startswith("third_"):
        name = {"early": "early", "mid": "middle", "late": "late"}[arm.split("_", 1)[1]]
        directions = {layer: unit(word, layer) for layer in thirds[name]}
        return intervene.dose_edits(
            directions, intervene.DECIDING_DOSE, attestation, float64=precision.float64
        )
    if arm == "control_late":
        # mute-map's control protocol mirrored (`mute-map/docs/M1-BRIEF.md:17-23`): the
        # same-category sibling's direction, at the late third, at λ = 1. Here the sibling is
        # the prime's frozen `cross` word from `batteries/probe_panel.json`.
        directions = {layer: unit(cross, layer) for layer in late}
        return intervene.dose_edits(
            directions, intervene.DECIDING_DOSE, attestation, float64=precision.float64
        )
    if arm.startswith("dose_late_"):
        lam = float(arm.rsplit("_", 1)[1])
        directions = {layer: unit(word, layer) for layer in late}
        return intervene.dose_edits(directions, lam, attestation, float64=precision.float64)
    raise ValueError(f"unknown arm {arm!r}")


def trial_record(
    arm: str,
    entry: dict,
    text_index: int,
    decoded: list[oracle.DecodedTurn],
    collapse: list[dict],
    *,
    cross: str,
    source: str,
    removed_mass_mean: float,
    worst_residual: float,
    m0_reply_match: bool | None = None,
) -> dict:
    """One trial's record — the field contract `m3_cells.prime_cells` reads.

    Factored out so the tests build fixtures with **this** code rather than a hand-written
    shape (`D14`), and so an M2-recorded trial and a newly generated one land in exactly the
    same shape with only `source` telling them apart.
    """
    score = oracle.score_turns(decoded, entry["word"])
    turn1 = oracle.score_turns(decoded[:1], entry["word"])
    trial = {
        "arm": arm,
        "secret": entry["word"],
        "cross": cross,
        "yardstick": entry["yardstick"],
        "category": entry["category"],
        "split": entry["split"],
        "tier": TIER,
        "text_index": text_index,
        "source": source,
        "emitted": score.emitted,
        "emitted_turn1": turn1.emitted,
        "boundary_rejected": score.boundary_rejected,
        "boundary_rejected_left": score.boundary_rejected_left,
        "boundary_rejected_right": score.boundary_rejected_right,
        "boundary_indeterminate": score.boundary_indeterminate,
        "multi_token_hits": score.multi_token_hits,
        "case_variant_miss": score.case_variant_miss,
        "capitalized_only_hits": score.capitalized_only_hits,
        "capitalized_only_contexts": list(score.capitalized_only_contexts),
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


def recorded_from_m2(m2: dict, primes: list[str], rows: dict[str, dict]) -> list[dict]:
    """`D37`.5: the eval primes' already-measured cells, **read from M2's record**.

    Copied with their recorded replies intact and re-scored here by the frozen oracle, so a
    recorded cell and a newly generated one are the same object with a different `source`.
    Renaming is the only translation: M2's `lambda_1` is M3's `lambda_1_full`, because M3
    also carries a late-third λ = 1 arm and "λ = 1" alone would name two different layer sets
    — the exact ambiguity M2's non-nesting finding makes dangerous.
    """
    wanted = set(primes)
    out = []
    for trial in m2["trials"]:
        if trial["secret"] not in wanted or trial["tier"] != TIER:
            continue
        arm = next(
            (m3 for m3, m2_name in m3_cells.M2_ARM_SOURCE.items() if m2_name == trial["arm"]),
            None,
        )
        if arm is None:
            continue
        record = dict(trial)
        record["arm"] = arm
        record["source"] = "m2_recorded"
        record["cross"] = rows[trial["secret"]]["cross"]
        out.append(record)
    return out


def build_payload(
    *,
    subject: str,
    environment: dict,
    penalty: float,
    band: list[int],
    thirds: dict,
    precision,
    primes: dict[str, list[str]],
    readbacks: dict,
    trials: list[dict],
    m0_path: pathlib.Path,
    m2_path: pathlib.Path,
    lens_path: pathlib.Path,
    elapsed: float,
) -> dict:
    """`m3-primes-<scale>.json`'s run-level contract, cells included."""
    payload = {
        "subject": subject,
        "battery_sha256": battery.sha256(battery.SECRETS_PATH),
        "tiers_sha256": battery.sha256(battery.TIERS_PATH),
        "probe_panel_sha256": battery.sha256(panel.PANEL_PATH),
        "lens_sha256": probe.sha256(lens_path),
        # `D37`.5: path + SHA256 of **each record cells were read from**, so every
        # read-from-record cell has checkable provenance (M2's `m0_reference` precedent).
        "m0_reference": {
            "path": str(pathlib.Path(m0_path).relative_to(RESULTS.parent)),
            "sha256": probe.sha256(m0_path),
        },
        "m2_reference": {
            "path": str(pathlib.Path(m2_path).relative_to(RESULTS.parent)),
            "sha256": probe.sha256(m2_path),
        },
        "generation": {
            "do_sample": False,
            "max_new_tokens": MAX_NEW_TOKENS,
            "repetition_penalty": float(penalty),
        },
        "environment": environment,
        "oracle": "D6 primary, per D10/D12/D13: surface-form string at a word boundary",
        "band": band,
        "thirds": thirds,
        "tier": TIER,
        "primes": primes,
        "intervention": {
            "operator": "K6 dose: h' = h - lambda * (v_hat^T h) v_hat, per position",
            "direction": (
                "the prime's own frozen probe_row direction (D27/D15's, identically), except "
                "on control_late, which ablates the prime's frozen `cross` word from "
                "batteries/probe_panel.json — mute-map's same-category-sibling control "
                "protocol mirrored."
            ),
            "direction_key_rule": (
                "mute-map/docs/DECISIONS.md:301-308, inherited exactly: the direction comes "
                "from the bare-form unembed row where single-token, else the leading-space "
                "row, recorded per item as direction_key."
            ),
            "precision": precision.payload(),
        },
        "readback": {
            "tol": intervene.READBACK_TOL,
            "per_arm": {arm: readbacks[arm].payload() for arm in sorted(readbacks)},
            "note": (
                "arms whose cells are read from M2's record have no read-back here — M2's own "
                "payload carries theirs, and re-attesting a recorded cell would be a claim "
                "about arithmetic this run did not perform."
            ),
        },
        "sourcing": {
            "rule": (
                "D37.5: recorded cells are READ, new cells are RUN, and nothing is re-run "
                "against an order-sensitive constructor. New generation: the six non-dose "
                "arms on the 7 calibration primes, control_late on the 4 eval primes, and the "
                "three late-third dose arms on all 11. Read from M2: the 4 eval primes' "
                "lambda_0, lambda_1_full and three thirds. The D31 random arm is deliberately "
                "absent — its directions are a function of a word's index in M2's frozen "
                "eval-order list AND of the ascending band-layer list, so no draw could serve "
                "both a re-certification and the calibration primes."
            ),
            "new_for_calibration": list(NEW_FOR_CALIBRATION),
            "new_for_eval": list(NEW_FOR_EVAL),
            "new_for_all": list(NEW_FOR_ALL),
            "read_from_m2": sorted(m3_cells.M2_ARM_SOURCE),
        },
        "arms_swept": list(m3_cells.PRIME_ARMS),
        "elapsed_seconds": round(elapsed, 1),
        "trials": trials,
        "note": (
            "Arm A is GATELESS and descriptive (D37.3). Per-prime rows are n <= 4 against "
            "mute-map's n <= 3 and are never verdict-bearing in either house. A prime's 4 "
            "trials share one direction and one secret, so a trial-pooled Newcombe overstates "
            "independence — mute-map owns the same in its M1 stats row."
        ),
    }
    payload["cells"] = m3_cells.prime_cells(payload)
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--subject", required=True)
    parser.add_argument("--device", default="auto", choices=("auto", "mps", "cpu"))
    parser.add_argument("--edit-precision", default="auto",
                        choices=("auto", "fp32", "float64"))
    parser.add_argument("--limit", type=int, default=None,
                        help="smoke-test only: cap the primes generated per arm")
    parser.add_argument("--out-suffix", default="", help="smoke-test only")
    args = parser.parse_args()

    slug = m3_cells.slug_for(args.subject)
    secrets_payload = battery.load_secrets()
    tiers = battery.load_tiers()["tiers"]
    rows = panel.rows_for(panel.load())

    by_word = {e["word"]: e for e in secrets_payload["secrets"]}
    # `D9a`: the primes that are actually **in** the battery — 11, not 12. Derived from the
    # frozen battery and the inherited roster, never transcribed.
    primes = sorted(word for word in by_word if word in M3_PRIMES)
    if len(primes) != 11:
        abort(f"the frozen battery holds {len(primes)} of mute-map's 12 primes, not D9a's 11")
    calibration = [w for w in primes if by_word[w]["split"] == "calibration"]
    evaluation = [w for w in primes if by_word[w]["split"] == "eval"]
    print(f"matched primes: {len(calibration)} calibration {calibration}, "
          f"{len(evaluation)} eval {evaluation}")

    m0_path = RESULTS / f"m0-leak-curve-{slug}.json"
    m2_path = RESULTS / f"m2-ablation-{slug}.json"
    for path, why in ((m0_path, "D28's identity check"), (m2_path, "D37.5's recorded cells")):
        if not path.exists():
            abort(f"no reference at {path} — {why} cannot run")
    m0 = json.loads(m0_path.read_text())
    m2 = json.loads(m2_path.read_text())
    m0_trials = {(t["secret"], t["text_index"]): t for t in m0["trials"] if t["tier"] == TIER}

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
    if environment != m0["environment"]:
        abort(
            f"environment {environment} differs from the M0 reference's {m0['environment']} "
            "— D28's identity pattern requires the identical machine"
        )
    if environment != m2["environment"]:
        abort(
            "the M2 record this run reads cells from was produced on a different machine; a "
            "congruence table whose two halves come from two substrates compares the wrong "
            "thing"
        )

    try:
        penalty = m3_cells.check_decode_rule(slug, model.generation_config.repetition_penalty)
    except m3_cells.CellError as exc:
        abort(str(exc))

    n_layers = model.config.num_hidden_layers
    band = probe.validated_band(n_layers)
    thirds = probe.sub_band_thirds(band)
    lens_path = probe.lens_path_for(args.subject)
    artifact = probe.load_lens(
        lens_path, model_id=args.subject, d_model=model.config.hidden_size, n_layers=n_layers
    )
    needed = sorted({word for word in primes} | {rows[word]["cross"] for word in primes})
    index, unembed = build_directions(needed, rows, model)
    directions = probe.unit_directions(artifact, band, unembed, device=device)
    del artifact

    def unit(word: str, layer: int):
        return directions[layer][index[word]]

    precision = intervene.preflight_precision(
        _sample_residuals(
            model,
            encode.encode_chat(
                tokenizer, primes[0], by_word[primes[0]]["yardstick"],
                [("user", tiers[TIER][0][0])],
            ),
            band,
        ),
        {layer: unit(primes[0], layer) for layer in band},
        requested=args.edit_precision,
    )

    # `D37`.5's plan, as data: which (arm, prime) cells this run generates.
    plan: dict[str, list[str]] = {arm: [] for arm in m3_cells.PRIME_ARMS}
    for arm in NEW_FOR_CALIBRATION:
        plan[arm].extend(calibration)
    for arm in NEW_FOR_EVAL:
        plan[arm].extend(evaluation)
    for arm in NEW_FOR_ALL:
        plan[arm].extend(primes)
    for arm in plan:
        plan[arm] = sorted(set(plan[arm]))[: args.limit] if args.limit else sorted(set(plan[arm]))
    total = sum(len(words) for words in plan.values()) * len(tiers[TIER])

    print(
        f"subject {args.subject} on {device} ({model.dtype}) | band L{band[0]}–L{band[-1]} "
        f"(late third L{thirds['late'][0]}–L{thirds['late'][-1]}) | repetition_penalty "
        f"{penalty} (D25) | edit {precision.payload()['edit_dtype']} | {total} new trials",
        flush=True,
    )

    trials = recorded_from_m2(m2, evaluation, rows)
    readbacks = {
        arm: intervene.ArmReadback(exact_return=arm == "lambda_0")
        for arm in m3_cells.PRIME_ARMS
        if plan[arm]
    }
    attestation = intervene.EditAttestation()
    started = time.time()

    for arm in m3_cells.PRIME_ARMS:
        for position, word in enumerate(plan[arm], 1):
            entry = by_word[word]
            cross = rows[word]["cross"]
            edits = arm_edits(
                arm, word=word, cross=cross, band=band, thirds=thirds, unit=unit,
                attestation=attestation, precision=precision,
            )
            for text_index, text in enumerate(tiers[TIER]):
                attestation.reset()
                decoded, collapse = run_session(
                    model, tokenizer,
                    lambda history, w=word, y=entry["yardstick"]: encode.encode_chat(
                        tokenizer, w, y, history
                    ),
                    text, edits,
                )
                readbacks[arm].absorb(attestation)

                matched = None
                if arm == "lambda_0":
                    reference = m0_trials.get((word, text_index))
                    if reference is None:
                        abort(f"M0 reference has no {TIER} trial for ({word}, {text_index})")
                    replies = [turn.text for turn in decoded]
                    truncated = [turn.truncated for turn in decoded]
                    matched = (
                        reference["replies"] == replies
                        and reference["truncated"] == truncated
                    )
                    if not matched:
                        abort(
                            f"D28's identity pattern failed at ({word}, {text_index}): the "
                            "lambda = 0 arm's generation differs from M0's recorded replies. "
                            "The lambda = 0 edit path is exact-return by construction, so a "
                            "divergence means the substrate, the loaders, the encoder or the "
                            "decode rule moved — a stop condition, not a tolerance."
                        )
                trials.append(
                    trial_record(
                        arm, entry, text_index, decoded, collapse,
                        cross=cross, source="m3_generated",
                        removed_mass_mean=attestation.removed_mass_mean,
                        worst_residual=attestation.worst_residual,
                        m0_reply_match=matched,
                    )
                )
            print(f"[{arm:15s} {position:2d}/{len(plan[arm])}] {word:10s}", flush=True)

    payload = build_payload(
        subject=args.subject,
        environment=environment,
        penalty=penalty,
        band=band,
        thirds=thirds,
        precision=precision,
        primes={"all": primes, "calibration": calibration, "eval": evaluation},
        readbacks=readbacks,
        trials=trials,
        m0_path=m0_path,
        m2_path=m2_path,
        lens_path=lens_path,
        elapsed=time.time() - started,
    )

    RESULTS.mkdir(exist_ok=True)
    path = RESULTS / f"m3-primes-{slug}{args.out_suffix}.json"
    path.write_text(json.dumps(payload, indent=1) + "\n")

    print(f"\nwrote {path}  ({payload['elapsed_seconds']}s, {len(trials)} trials)")
    for arm in m3_cells.PRIME_ARMS:
        cell = payload["cells"]["arms"][arm]
        print(f"  {arm:15s} {cell['trial_level']['hits']:2d}/{cell['trial_level']['n']:2d} "
              f"trials emitting over {cell['n_primes']:2d} primes  ({'+'.join(cell['sources'])})")
    a5 = payload["cells"]["a5_specificity"]
    print(
        f"  A5 on {a5['population']['realized']}/{a5['population']['of']} baseline-emitting "
        f"trials (predicted {a5['population']['predicted']}): primed-late "
        f"{a5['primed_late']['trial_level']['hits']}/{a5['primed_late']['trial_level']['n']} "
        f"vs control-late "
        f"{a5['control_late']['trial_level']['hits']}/{a5['control_late']['trial_level']['n']}"
    )
    return 0


def _sample_residuals(model, prompt_ids, layers) -> dict[int, torch.Tensor]:
    """One prefill's block-output residual at each listed layer — `m2_ablation`'s preflight
    input, cut. Kept **on the model's device**: the preflight's whole point is to check the
    read-back against the arithmetic the sweep will actually run."""
    blocks: dict[int, torch.Tensor] = {}
    handles = []

    def make_hook(index: int):
        def hook(module, inputs, output):
            residual = output if torch.is_tensor(output) else output[0]
            blocks[index] = residual[0].detach().float()

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


if __name__ == "__main__":
    raise SystemExit(main())

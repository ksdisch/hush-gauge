"""M3's Arm B sweep — the G4 arms on `D35`'s baseline-silent T1–T2 population.

**Cut from `m2_ablation.py`** per the house runner rule (the generation loop, the
decode-rule assertion, the precision preflight, the direction construction, the byte-identity
arm); `m2_ablation.py` and every other M0/M1/M2-certified module is read-only for M3 and
untouched by this file. Its WikiText half is cut from `m2_preservation.py` for the same
reason.

One subject **and one split** per invocation, after `construct_switch.py`:

    uv run python m3_arm_b.py --subject Qwen/Qwen2.5-0.5B-Instruct --split calibration  # V3
    uv run python m3_arm_b.py --subject Qwen/Qwen2.5-0.5B-Instruct --split eval         # G4

**One runner, two populations, by design.** `D38`.4 requires V3 to be *"computed by the
identical machinery G4 will use on eval"*; the honest way to guarantee that is for it to be
the identical machinery, pointed at the calibration half. The split is a flag, not a fork,
and `gates/g4.py` refuses an eval payload carrying a calibration trial either way
(`D39`.5 arm 1).

The arms (`D38`.4, plus `D40`.3's companion), over the same T1–T2 trials:

* `lambda_0` — the identity arm. Exact-return **by construction** (`D27`/`D28`), and every
  reply byte-asserted against M0's recorded T1/T2 trials for that split. It is what
  *defines* `D35`'s baseline-silent population, so a divergence is a stop condition rather
  than a tolerance: a shifted baseline would silently redraw the population the gate
  decides on.
* `real_late` — `w⊥`, λ = 1, at the **late third**. The deciding deployment (mute-map's
  home, and M2's non-nesting flag's home).
* `sham_late` — the `D38`.3 **deciding sham**, orthogonalized identically. G4's contrast is
  `real_late` vs this.
* `random_late` — `D31`'s protocol applied fresh, λ = 1 at the late third. Reported
  secondary; **not** orthogonalized, so `D38`.5(b) is recorded as not-claimed rather than
  run against a direction that never made the claim.
* `real_full` — `w⊥` at the **full band**. `D40`.3's descriptive companion, never deciding.
  Eval split only.

**`D40`.1's preservation readouts ride in the eval run** — WikiText NLL and benign-QA
accuracy under the identical per-session `w⊥`, reusing `D30`'s frozen artifacts and
`preservation.py` unchanged. They **decide nothing in M3** (`D34`), so they need no separate
gate fixture and get no separate runner; the deviation is owned in `M3-RESULTS.md` rather
than discovered by a reader. `--no-preservation` skips them for a smoke run.

**Three stop conditions, all loud and all before any verdict:** `D25`'s decode-rule
assertion, `D28`'s byte-identity arm, and `D38`.5's dual read-back — whose (b) half is what
turns `D34`'s orthogonality guarantee from a property into a proof.
"""

from __future__ import annotations

import argparse
import glob
import json
import pathlib
import time

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

import battery
import construct_switch
import encode
import intervene
import m3_cells
import oracle
import panel
import preservation
import probe

RESULTS = pathlib.Path(__file__).parent / "results"
FIT_CORPUS_PATH = probe.LENSES / "wikitext-n100-prompts.json"

MAX_NEW_TOKENS = m3_cells.MAX_NEW_TOKENS
TIERS = m3_cells.GATE_TIERS

#: `dim-stage/s3_selectivity.py:87-90` verbatim, via `m1_wikitext_rate.py` and
#: `m2_preservation.py` (`D19`/`D30`.1) — `D40`.1 reuses the corpus convention unchanged.
WIKITEXT_SKIP = 100
WIKITEXT_N = 100
WIKITEXT_MAX_TOKENS = 128
MIN_CHARS = 600

CACHE_GLOB = (
    "~/.cache/huggingface/hub/datasets--Salesforce--wikitext/snapshots/*/"
    "wikitext-103-raw-v1/train-*.parquet"
)


def abort(reason: str) -> None:
    print(f"ABORT — {reason}", flush=True)
    raise SystemExit(2)


def pad_id(tokenizer) -> int:
    """`m0_leak_curve.py:48-52` verbatim (M0's `F9`)."""
    return tokenizer.pad_token_id if tokenizer.pad_token_id is not None else tokenizer.eos_token_id


def generate_turn(model, tokenizer, prompt_ids):
    """One greedy turn (`D5` as qualified by `D25`), inside whatever edit context the
    caller has installed."""
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


def run_session(model, tokenizer, prompt_ids, edits):
    """One T1/T2 trial's generation under `edits` — a single turn, so no feedback loop and
    no `D3` exposure asymmetry inside G4 (`D40`.5)."""
    with intervene.edit_residuals(model.model.layers, edits):
        generated, truncated = generate_turn(model, tokenizer, prompt_ids)
    return (
        oracle.decode_turn(generated, tokenizer, truncated=truncated),
        intervene.degeneracy(generated, tokenizer),
    )


def sample_residuals(model, prompt_ids, layers) -> dict[int, torch.Tensor]:
    """One prefill's block-output residual at each listed layer — the preflight's input
    (`m2_ablation.sample_residuals`, cut). Kept **on the model's device**: the preflight
    exists to check the read-back against the arithmetic the sweep will actually run."""
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


def build_directions(rows: dict[str, dict], model):
    """One `[n_rows, d_model]` raw-unembedding matrix over each listed word's primary probe
    row. Copied from `m2_ablation.build_directions` rather than imported (runners are cut,
    never shared); `u` is the **raw** `lm_head.weight` row — γ is not folded in (`K6`).

    M3 needs only the primary row: `D38`.2 projects out `v̂_s`, which is `D27`'s direction,
    which is the `probe_row` one. The capitalized companion is M2's span-arm input and has
    no M3 consumer.
    """
    index = {word: position for position, word in enumerate(sorted(rows))}
    ids = [rows[word]["probe_row"] for word in sorted(rows)]
    return index, model.lm_head.weight.detach()[ids]


def session_directions(
    arm, *, word, band, thirds, candidate, secret_unit, random_vectors, device
):
    """The deployed direction set for one (arm, secret) — the whole per-arm difference lives
    here so no other part of the runner branches on the arm name.

    `candidate["real"]`/`["sham"]` are the constructed `[n_band_layers, d_model]` matrices;
    `secret_unit(layer)` is that session secret's `v̂_s(l)`. Returns
    `(deployed {layer: direction}, secret {layer: v̂_s} | None, cosines | None)` — the third
    is `D40`.4's recorded channel, the honest "how much of the candidate was content"
    reading, taken **before** orthogonalization.

    Everything comes back **on `device`**. `D38`.2's projection is computed in CPU float64
    (`orthogonalize`'s own reason), and a caller that forgot to move the result would either
    pay a host→device copy per forward pass or — as the preflight does, which reads the raw
    directions rather than going through the edit closure — mix devices and abort.
    """
    late = thirds["late"]
    secret = {layer: secret_unit(layer).to(device) for layer in band}
    if arm == m3_cells.RANDOM_ARM:
        # `D31`'s protocol, applied fresh: no orthogonality is claimed, so `D38`.5(b) is
        # not run — see `dual_dose_edits`.
        return {layer: random_vectors[(word, layer)].to(device) for layer in late}, None, None
    role = "sham" if arm == m3_cells.SHAM_ARM else "real"
    layers = band if arm == m3_cells.FULL_ARM else late
    matrix = construct_switch.as_layer_map(candidate[role], band)
    on_cpu = {layer: secret[layer].detach().cpu() for layer in layers}
    cosines = {
        str(layer): float(
            (matrix[layer] / matrix[layer].norm()) @ (on_cpu[layer] / on_cpu[layer].norm())
        )
        for layer in layers
    }
    deployed = {
        layer: construct_switch.orthogonalize(matrix[layer], on_cpu[layer]).to(device)
        for layer in layers
    }
    return deployed, {layer: secret[layer] for layer in layers}, cosines


def trial_record(
    arm: str,
    entry: dict,
    tier: str,
    text_index: int,
    decoded: oracle.DecodedTurn,
    collapse: dict,
    *,
    removed_mass_mean: float,
    worst_survival: float,
    worst_preservation: float | None,
    pre_orthogonalization_cosines: dict | None,
    m0_reply_match: bool | None = None,
) -> dict:
    """One trial's record — `D39`'s full field contract in one place.

    Factored out of the sweep loop so `tests/test_g4.py` builds the gate's proving fixtures
    with **this** code rather than a hand-written shape (`D14`: a dry-run arm proven against
    a fixture the runner never emits is worth nothing).
    """
    score = oracle.score_turns([decoded], entry["word"])
    trial = {
        "arm": arm,
        "secret": entry["word"],
        "yardstick": entry["yardstick"],
        "category": entry["category"],
        "split": entry["split"],
        "tier": tier,
        "text_index": text_index,
        "emitted": score.emitted,
        "boundary_rejected": score.boundary_rejected,
        "boundary_rejected_left": score.boundary_rejected_left,
        "boundary_rejected_right": score.boundary_rejected_right,
        "boundary_indeterminate": score.boundary_indeterminate,
        "multi_token_hits": score.multi_token_hits,
        "case_variant_miss": score.case_variant_miss,
        "capitalized_only_hits": score.capitalized_only_hits,
        "capitalized_only_contexts": list(score.capitalized_only_contexts),
        "replies": [decoded.text],
        "truncated": [decoded.truncated],
        "removed_mass_mean": removed_mass_mean,
        "readback_worst_survival": worst_survival,
        "readback_worst_preservation": worst_preservation,
        "turns": [collapse],
        "collapsed": bool(collapse["collapsed"]),
    }
    if pre_orthogonalization_cosines is not None:
        trial["pre_orthogonalization_cosines"] = pre_orthogonalization_cosines
    if m0_reply_match is not None:
        trial["m0_reply_match"] = m0_reply_match
    return trial


# ------------------------------------------------------ D40.1's reported readouts


def stream_wikitext(n: int, *, min_chars: int = MIN_CHARS) -> list[str]:
    """The first `n` WikiText-103 **train** records whose stripped text is ≥ `min_chars`
    (`dim-stage/fitter.py:363-379`'s convention), via `m2_preservation.stream_wikitext`."""
    import pyarrow.parquet as pq

    shards = sorted(glob.glob(str(pathlib.Path(CACHE_GLOB).expanduser())))
    if not shards:
        probe.fail(
            f"no WikiText-103 train parquet in the HuggingFace cache ({CACHE_GLOB}) — "
            "D19's corpus cannot be streamed and its disjointness proof cannot run"
        )
    out: list[str] = []
    for shard in shards:
        for batch in pq.ParquetFile(shard).iter_batches(batch_size=4096, columns=["text"]):
            for text in batch.column("text").to_pylist():
                if len(text.strip()) >= min_chars:
                    out.append(text)
                    if len(out) == n:
                        return out
    probe.fail(f"WikiText-103 train yielded only {len(out)} qualifying records, expected {n}")


def prove_disjointness(streamed: list[str]) -> dict:
    """`D19`: the first 100 streamed records must equal the fit corpus, else the readout
    would be taken on the very text the lens was fitted on."""
    fit = json.loads(FIT_CORPUS_PATH.read_text())
    if streamed[: len(fit)] != fit:
        probe.fail(
            "the first 100 streamed WikiText records no longer match "
            f"{FIT_CORPUS_PATH.name} — D19's fit-corpus disjointness proof FAILS"
        )
    return {
        "fit_corpus": {
            "path": str(FIT_CORPUS_PATH.relative_to(RESULTS.parent)),
            "sha256": probe.sha256(FIT_CORPUS_PATH),
            "n_records": len(fit),
        },
        "proven": True,
        "rule": (
            "dim-stage/s3_selectivity.py:621-628 — the first 100 qualifying streamed records "
            "equal the fit corpus, so records 101-200 are disjoint from the lens fit"
        ),
    }


def record_nll(model, input_ids: torch.Tensor) -> tuple[float, int]:
    """`D30`.1's per-record statistic, unchanged: the mean per-token NLL over the record's
    next-token predictions — **up to 127, not exactly 127**. No position mask."""
    with torch.no_grad():
        logits = model(input_ids.to(model.device)).logits.float()
    targets = input_ids.to(logits.device)[:, 1:]
    log_probs = torch.log_softmax(logits[:, :-1], dim=-1)
    picked = log_probs.gather(-1, targets.unsqueeze(-1)).squeeze(-1)
    return float(-picked.mean()), int(targets.shape[1])


def build_payload(
    *,
    subject: str,
    split: str,
    environment: dict,
    penalty: float,
    band: list[int],
    thirds: dict,
    precision,
    arms,
    readbacks: dict,
    trials: list[dict],
    switch_reference: dict,
    v_ladder: dict,
    random_words: list[str],
    random_sha: str,
    m0_path: pathlib.Path,
    lens_path: pathlib.Path,
    preservation_block: dict | None,
    elapsed: float,
) -> dict:
    """`m3-armb-<scale>-<split>.json`'s run-level contract, cells included."""
    payload = {
        "subject": subject,
        "split": split,
        "battery_sha256": battery.sha256(battery.SECRETS_PATH),
        "tiers_sha256": battery.sha256(battery.TIERS_PATH),
        "probe_panel_sha256": battery.sha256(panel.PANEL_PATH),
        "lens_sha256": probe.sha256(lens_path),
        "m0_reference": {
            "path": str(pathlib.Path(m0_path).relative_to(RESULTS.parent)),
            "sha256": probe.sha256(m0_path),
        },
        "switch_reference": switch_reference,
        "v_ladder": v_ladder,
        "generation": {
            "do_sample": False,
            "max_new_tokens": MAX_NEW_TOKENS,
            "repetition_penalty": float(penalty),
        },
        "environment": environment,
        "oracle": "D6 primary, per D10/D12/D13: surface-form string at a word boundary",
        "unit": m3_cells.GATE_UNIT,
        "band": band,
        "thirds": thirds,
        "tiers": list(TIERS),
        "intervention": {
            "operator": "K6 dose: h' = h - lambda * (v_hat^T h) v_hat, per position",
            "direction": (
                "D38.1's constructed candidate w(l), orthogonalized per session against the "
                "session secret's K6 direction v_s(l) (D38.2). The D31 random arm deploys an "
                "un-orthogonalized frozen-seed Gaussian and makes no D38.5(b) claim."
            ),
            "layers": (
                "late third for the deciding arms (D38.4); the full band for D40.3's "
                "descriptive companion; each layer uses its own constructed row"
            ),
            "positions": "every position of every forward pass, prompt and generated",
            "deciding_dose": intervene.DECIDING_DOSE,
            "precision": precision.payload(),
        },
        "random_directions": {
            **intervene.draw_order_note(random_words, thirds["late"]),
            "seed": m3_cells.RANDOM_SEED,
            "sha256": random_sha,
            "note": (
                "D38.3's REPORTED sham: D31's protocol with M3's own frozen seed and a "
                "recorded draw order. The draws are new — M2's vectors are full-band and "
                "index-keyed to its 25-word eval list — so the cross-milestone comparison is "
                "protocol-level, never vector-level."
            ),
        },
        "readback": {
            "tol": intervene.READBACK_TOL,
            "rule": (
                "D38.5: (a) the surviving projection of w_perp equals (1-lambda) of the "
                "original within READBACK_TOL relative to ||h||, and (b) the session "
                "secret's v_s projection is UNCHANGED within the same tolerance. (b) is true "
                "by construction for an exact w_perp; the assertion catches float drift and "
                "any orthogonalization bug at run time. lambda = 0 is exact-return, so it "
                "has no arithmetic to certify — exact_return distinguishes that from checks "
                "skipped, and orthogonalized=false distinguishes a claim not made from a "
                "claim that held."
            ),
            "per_arm": {arm: readbacks[arm].payload() for arm in arms},
        },
        "arms_swept": list(arms),
        "elapsed_seconds": round(elapsed, 1),
        "trials": trials,
    }
    if preservation_block is not None:
        payload["preservation_readouts"] = preservation_block
    payload["cells"] = m3_cells.armb_cells(payload)
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--subject", required=True)
    parser.add_argument("--split", required=True, choices=("calibration", "eval"))
    parser.add_argument("--device", default="auto", choices=("auto", "mps", "cpu"))
    parser.add_argument("--arms", default=None,
                        help="comma-separated subset; smoke-test only")
    parser.add_argument("--edit-precision", default="auto",
                        choices=("auto", "fp32", "float64"),
                        help="D27's bounded implementation freedom; 'auto' preflights")
    parser.add_argument("--no-preservation", action="store_true",
                        help="skip D40.1's reported readouts; smoke-test only")
    parser.add_argument("--limit", type=int, default=None, help="smoke-test only")
    parser.add_argument("--out-suffix", default="", help="smoke-test only")
    args = parser.parse_args()

    slug = m3_cells.slug_for(args.subject)
    default_arms = m3_cells.ARMS_FOR_SPLIT[args.split]
    arms = tuple(a.strip() for a in args.arms.split(",")) if args.arms else default_arms
    unknown = [arm for arm in arms if arm not in m3_cells.EVAL_ARMS]
    if unknown:
        abort(f"unknown arms {unknown}; D38/D39 freeze {list(m3_cells.EVAL_ARMS)}")

    secrets_payload = battery.load_secrets()
    tiers = battery.load_tiers()["tiers"]
    rows = panel.rows_for(panel.load())

    entries = [e for e in secrets_payload["secrets"] if e["split"] == args.split]
    if len(entries) != m3_cells.EXPECTED_SPLIT_SECRETS:
        abort(f"the frozen battery has {len(entries)} {args.split} secrets, not 25")
    sweep = entries[: args.limit] if args.limit else entries

    m0_path = RESULTS / f"m0-leak-curve-{slug}.json"
    if not m0_path.exists():
        abort(f"no M0 reference at {m0_path} — D39.2's identity check has nothing to compare to")
    m0 = json.loads(m0_path.read_text())
    m0_trials = {(t["secret"], t["tier"], t["text_index"]): t for t in m0["trials"]}

    switch_path = RESULTS / f"m3-switch-{slug}.json"
    if not switch_path.exists():
        abort(f"no construction record at {switch_path} — run construct_switch.py first")
    switch = json.loads(switch_path.read_text())
    candidate = construct_switch.load_directions(slug)

    # `D38`.4's drop semantics, checked **before** any generation at this scale: V1 or V2
    # failing drops Arm B here, and no eval run is authorized. The V3 half is resolved after
    # the calibration runs, by `gates/g4.py` reading the recorded payloads.
    v1, v2 = switch["v_ladder"]["V1"], switch["v_ladder"]["V2"]
    if not (v1["holds"] and v2["holds"]):
        reason = "V1" if not v1["holds"] else "V2"
        abort(
            f"{m3_cells.not_run_verdict(reason)} — D38.4 drops Arm B at {slug}, so no "
            f"{args.split} run is authorized. Every drop is a reportable design null (K5), "
            "not a failure to fix."
        )
    if args.split == "eval":
        # `D38`.4's V3 half, checked here as well as in the gate. The gate's arm 8 is the
        # authority; this is what keeps an unauthorized scale from spending a thousand
        # generations to earn an `INVALID`.
        reason = unauthorized_reason(slug)
        if reason is not None:
            abort(
                f"{m3_cells.not_run_verdict(reason)} — D38.4 does not authorize an eval run "
                f"at {slug}. V3 gates where the predicted calibration cell holds >= "
                f"{m3_cells.MIN_N} headroom secrets (0.5B, 1.5B); 3B's cell is under the "
                "house floor by construction, so its eval run needs at least one "
                "gate-capable scale to have passed V3."
            )

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
            f"environment {environment} differs from the M0 reference's {m0['environment']} — "
            "D39.2's byte-identity arm requires the identical machine, since greedy decode "
            "is deterministic only given one"
        )
    if environment != switch["environment"]:
        abort(
            "the construction was built on a different machine than this sweep runs on; the "
            "candidate and the population it is tested on must come from one substrate"
        )

    try:
        penalty = m3_cells.check_decode_rule(slug, model.generation_config.repetition_penalty)
    except m3_cells.CellError as exc:
        abort(str(exc))

    n_layers = model.config.num_hidden_layers
    band = probe.validated_band(n_layers)
    thirds = probe.sub_band_thirds(band)
    if band != switch["band"]:
        abort("the construction's band disagrees with the subject's frozen band")
    lens_path = probe.lens_path_for(args.subject)
    artifact = probe.load_lens(
        lens_path, model_id=args.subject, d_model=model.config.hidden_size, n_layers=n_layers
    )
    split_rows = {entry["word"]: rows[entry["word"]] for entry in entries}
    index, unembed = build_directions(split_rows, model)
    secret_directions = probe.unit_directions(artifact, band, unembed, device=device)
    del artifact

    # `D31`'s protocol applied fresh: one unit Gaussian per (secret, late-third layer), M3's
    # own frozen seed, drawn over **every** split secret regardless of `--limit` so a smoke
    # run and the real run give a secret the same control direction.
    random_words = [entry["word"] for entry in entries]
    random_vectors, random_sha = intervene.random_directions(
        random_words, thirds["late"], model.config.hidden_size, seed=m3_cells.RANDOM_SEED
    )

    def make_unit(word: str):
        slot = index[word]
        return lambda layer: secret_directions[layer][slot]

    # `D27`'s bounded implementation freedom, resolved **once** on real activations before
    # any trial, so no payload mixes two arithmetics across its arms. Probed on the deciding
    # arm's own deployed directions (`w⊥` at the late third), not on a stand-in.
    first = sweep[0]
    preflight_prompt = encode.encode_chat(
        tokenizer, first["word"], first["yardstick"], [("user", tiers[TIERS[0]][0])]
    )
    preflight_directions, _, _ = session_directions(
        m3_cells.REAL_ARM, word=first["word"], band=band, thirds=thirds,
        candidate=candidate, secret_unit=make_unit(first["word"]),
        random_vectors=random_vectors, device=device,
    )
    precision = intervene.preflight_precision(
        sample_residuals(model, preflight_prompt, thirds["late"]),
        preflight_directions,
        requested=args.edit_precision,
    )

    print(
        f"subject {args.subject} on {device} ({model.dtype}) | split {args.split} | band "
        f"L{band[0]}–L{band[-1]} (late third L{thirds['late'][0]}–L{thirds['late'][-1]}) | "
        f"repetition_penalty {penalty} (D25) | edit "
        f"{precision.payload()['edit_dtype']} (preflight worst "
        f"{precision.probe_worst_residual:.2e}) | arms {list(arms)} | {len(sweep)} secrets x "
        f"{len(TIERS)} tiers x 4 texts",
        flush=True,
    )

    trials: list[dict] = []
    readbacks = {
        arm: construct_switch.SwitchReadback(
            exact_return=arm == m3_cells.CLEAN_ARM,
            orthogonalized=arm != m3_cells.RANDOM_ARM,
        )
        for arm in arms
    }
    attestation = construct_switch.DualAttestation()
    started = time.time()

    for arm in arms:
        for position, entry in enumerate(sweep, 1):
            word, yardstick = entry["word"], entry["yardstick"]
            deployed, secret_map, cosines = session_directions(
                arm if arm != m3_cells.CLEAN_ARM else m3_cells.REAL_ARM,
                word=word, band=band, thirds=thirds, candidate=candidate,
                secret_unit=make_unit(word), random_vectors=random_vectors, device=device,
            )
            lam = 0.0 if arm == m3_cells.CLEAN_ARM else intervene.DECIDING_DOSE
            edits = construct_switch.dual_dose_edits(
                deployed, secret_map, lam, attestation, float64=precision.float64
            )
            for tier in TIERS:
                for text_index, text in enumerate(tiers[tier]):
                    attestation.reset()
                    decoded, collapse = run_session(
                        model, tokenizer,
                        encode.encode_chat(tokenizer, word, yardstick, [("user", text)]),
                        edits,
                    )
                    readbacks[arm].absorb(attestation)

                    matched = None
                    if arm == m3_cells.CLEAN_ARM:
                        reference = m0_trials.get((word, tier, text_index))
                        if reference is None:
                            abort(f"M0 reference has no trial for ({word}, {tier}, {text_index})")
                        matched = (
                            reference["replies"] == [decoded.text]
                            and reference["truncated"] == [decoded.truncated]
                        )
                        if not matched:
                            abort(
                                f"D39.2 identity check failed at ({word}, {tier}, "
                                f"{text_index}): the lambda = 0 arm's generation differs from "
                                "M0's recorded replies. The lambda = 0 edit path is "
                                "exact-return by construction, so a divergence means the "
                                "substrate, the loaders, the encoder or the decode rule "
                                "moved — and it would silently redraw the baseline-silent "
                                "population the gate decides on."
                            )
                    trials.append(
                        trial_record(
                            arm, entry, tier, text_index, decoded, collapse,
                            removed_mass_mean=attestation.removed_mass_mean,
                            worst_survival=attestation.worst_survival,
                            worst_preservation=(
                                attestation.worst_preservation
                                if attestation.preservation_checked
                                else None
                            ),
                            pre_orthogonalization_cosines=cosines,
                            m0_reply_match=matched,
                        )
                    )
            done = sum(1 for t in trials if t["arm"] == arm and t["emitted"])
            print(f"[{arm:11s} {position:2d}/{len(sweep)}] {word:10s} cumulative emitted {done}",
                  flush=True)

    # ------------------------------------------------------ D40.1's reported readouts
    preservation_block = None
    if args.split == "eval" and not args.no_preservation:
        preservation_block = run_preservation_readouts(
            model, tokenizer, sweep, band, thirds, candidate, make_unit,
            precision=precision, slug=slug, device=device,
        )

    payload = build_payload(
        subject=args.subject,
        split=args.split,
        environment=environment,
        penalty=penalty,
        band=band,
        thirds=thirds,
        precision=precision,
        arms=arms,
        readbacks=readbacks,
        trials=trials,
        switch_reference={
            "path": str(switch_path.relative_to(RESULTS.parent)),
            "sha256": probe.sha256(switch_path),
            "real_sha256": switch["directions"]["real_sha256"],
            "sham_sha256": switch["directions"]["sham_sha256"],
        },
        v_ladder=ladder_reference(slug),
        random_words=random_words,
        random_sha=random_sha,
        m0_path=m0_path,
        lens_path=lens_path,
        preservation_block=preservation_block,
        elapsed=time.time() - started,
    )

    RESULTS.mkdir(exist_ok=True)
    path = RESULTS / f"m3-armb-{slug}-{args.split}{args.out_suffix}.json"
    path.write_text(json.dumps(payload, indent=1) + "\n")

    population = payload["cells"]["population"]
    print(f"\nwrote {path}  ({payload['elapsed_seconds']}s, {len(trials)} trials)")
    print(
        f"  population: {population['realized']['pooled']} baseline-silent trials over "
        f"{population['realized']['headroom_secrets']} headroom secrets | predicted "
        f"{population['predicted']['pooled']}/{population['predicted']['headroom_secrets']} "
        f"| matches {population['matches_prediction']}"
    )
    for arm in arms:
        cell = payload["cells"]["arms"][arm]["emission"]["secret_level"]
        readback = payload["readback"]["per_arm"][arm]
        preserve = readback["worst_preservation_residual"]
        print(
            f"  {arm:11s} risen {cell['hits']:2d}/{cell['n']:2d} secrets   read-back "
            f"survival {readback['worst_survival_residual']:.2e}"
            + (f" / v_secret {preserve:.2e}" if preserve is not None else " / v_secret n-a")
            + ("  (exact-return)" if readback["exact_return"] else "")
        )
    contrast = payload["cells"]["g4_contrast"]["secret_level"]
    print(
        f"  {m3_cells.REAL_ARM} vs {m3_cells.SHAM_ARM}: diff {contrast['diff']:+.3f} "
        f"Newcombe [{contrast['newcombe_95'][0]:+.3f}, {contrast['newcombe_95'][1]:+.3f}] "
        f"-> {'CI-clean rise' if contrast['ci_clean_rise'] else 'not shown'}"
    )
    matched = sum(1 for t in trials if t.get("m0_reply_match"))
    if m3_cells.CLEAN_ARM in arms:
        print(f"  D39.2: {matched} lambda = 0 trials reproduced M0 byte-for-byte")
    return 0


def v3_state(slug: str) -> dict | None:
    """That scale's V3 verdict, **recomputed** from its calibration payload's own trials by
    the machinery G4 uses on eval (`D38`.4). `None` when no calibration run exists."""
    path = RESULTS / f"m3-armb-{slug}-calibration.json"
    if not path.exists():
        return None
    payload = json.loads(path.read_text())
    return m3_cells.v3_verdict(m3_cells.armb_cells(payload), slug=slug)


def unauthorized_reason(slug: str) -> str | None:
    """`D38`.4's V3 drop semantics: the reason this scale's eval run is not authorized, or
    `None` if it is. Mirrors `gates/g4.py` arm 8, which is the authority."""
    capable = m3_cells.V3_GATE_CAPABLE[slug]
    if capable:
        own = v3_state(slug)
        return None if (own and own["passes"]) else "V3"
    others = [
        v3_state(other)
        for other, is_capable in m3_cells.V3_GATE_CAPABLE.items()
        if is_capable
    ]
    passed = any(state and state["passes"] for state in others)
    return None if passed else m3_cells.NO_GATE_CAPABLE_V3


def ladder_reference(slug: str) -> dict:
    """The `v_ladder` block the eval payload carries: where the gate finds each scale's
    construction record and V3 payload.

    Recorded as **paths plus SHA256s** rather than as verdicts, so `gates/g4.py` recomputes
    V3 from the referenced payloads' own trials rather than believing a summary. Every scale
    is listed, because `D38`.4's 3B clause turns on whether *another* scale passed.
    """
    out: dict = {"self": slug, "scales": {}}
    for other in sorted(m3_cells.V3_GATE_CAPABLE):
        entry: dict = {"gate_capable": m3_cells.V3_GATE_CAPABLE[other]}
        for name, key in (
            (f"m3-switch-{other}.json", "switch"),
            (f"m3-armb-{other}-calibration.json", "v3"),
        ):
            path = RESULTS / name
            entry[key] = (
                {"path": f"results/{name}", "sha256": probe.sha256(path)}
                if path.exists()
                else None
            )
        out["scales"][other] = entry
    return out


def run_preservation_readouts(
    model, tokenizer, sweep, band, thirds, candidate, make_unit, *, precision, slug, device
) -> dict:
    """`D40`.1, **reported and deciding nothing**: WikiText NLL and benign-QA accuracy under
    the identical per-session `w⊥` at λ = 1, late third.

    `D30`'s frozen artifact and `preservation.py`'s loader are reused unchanged — the items
    are that scale's **recorded selection**, read by `item_id`, never a literal count. The
    QA predicate is the frozen oracle applied to the accepted answer strings.

    `D34` is the reason this decides nothing: a behavioral readout is a function of the
    generation, which is downstream of the edited residual, so nothing about a readout can
    guarantee independence from the edit. M3 replaced the unprovable conjunctive clause with
    a provable construction property (`D38`.2), and these two channels are reported beside
    G4 rather than folded into it.
    """
    frozen = preservation.load()
    items = preservation.selected_items(frozen, slug)
    streamed = stream_wikitext(WIKITEXT_SKIP + WIKITEXT_N)
    disjointness = prove_disjointness(streamed)
    records = streamed[WIKITEXT_SKIP : WIKITEXT_SKIP + WIKITEXT_N]
    encoded = [
        tokenizer(text, add_special_tokens=False, return_tensors="pt",
                  truncation=True, max_length=WIKITEXT_MAX_TOKENS).input_ids
        for text in records
    ]

    clean_nll = []
    for position, ids in enumerate(encoded):
        value, n_predictions = record_nll(model, ids)
        clean_nll.append({"record_index": position, "nll": value,
                          "n_predictions": n_predictions})

    attestation = construct_switch.DualAttestation()
    readback = construct_switch.SwitchReadback()
    ablated_nll, qa_trials = [], []
    for position, entry in enumerate(sweep, 1):
        word, yardstick = entry["word"], entry["yardstick"]
        deployed, secret_map, _ = session_directions(
            m3_cells.REAL_ARM, word=word, band=band, thirds=thirds, candidate=candidate,
            secret_unit=make_unit(word), random_vectors={}, device=device,
        )
        edits = construct_switch.dual_dose_edits(
            deployed, secret_map, intervene.DECIDING_DOSE, attestation,
            float64=precision.float64,
        )
        attestation.reset()
        with intervene.edit_residuals(model.model.layers, edits):
            for record_index, ids in enumerate(encoded):
                value, n_predictions = record_nll(model, ids)
                ablated_nll.append({"secret": word, "record_index": record_index,
                                    "nll": value, "n_predictions": n_predictions})
        readback.absorb(attestation)
        for item in items:
            for arm, arm_edits in (("clean", {}), ("ablated", edits)):
                attestation.reset()
                decoded, collapse = run_session(
                    model, tokenizer,
                    encode.encode_chat(tokenizer, word, yardstick, [("user", item["question"])]),
                    arm_edits,
                )
                if arm == "ablated":
                    readback.absorb(attestation)
                qa_trials.append({
                    "arm": arm,
                    "secret": word,
                    "item_id": item["item_id"],
                    "reply": decoded.text,
                    "truncated": decoded.truncated,
                    "correct": any(
                        oracle.score_turns([decoded], answer).emitted
                        for answer in item["answers"]
                    ),
                    "turns": [collapse],
                    "collapsed": bool(collapse["collapsed"]),
                })
        print(f"[preservation {position:2d}/{len(sweep)}] {word:10s}", flush=True)

    return {
        "decides": False,
        "note": (
            "D40.1: reported beside G4, deciding nothing. D34 moved the guarantee into the "
            "operator (D38.2) because a behavioral readout is downstream of the edited "
            "residual and cannot be independent of the edit by construction. Tolerances are "
            "printed on D30's own within-clean-CI form so the numbers read the same way M2's "
            "did; no clause here can void a G4 verdict."
        ),
        "preservation_qa_sha256": battery.sha256(preservation.PRESERVATION_PATH),
        "selected_item_ids": [item["item_id"] for item in items],
        "corpus": {
            "source": "wikitext-103-raw-v1 train",
            "skip": WIKITEXT_SKIP,
            "n_records": WIKITEXT_N,
            "max_tokens": WIKITEXT_MAX_TOKENS,
            "min_chars": MIN_CHARS,
            "disjointness": disjointness,
        },
        "readback": readback.payload(),
        "wikitext": {"clean": clean_nll, "ablated": ablated_nll},
        "qa_trials": qa_trials,
    }


if __name__ == "__main__":
    raise SystemExit(main())

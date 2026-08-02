"""M2's preservation battery — `D30`'s four clauses, all under the deciding edit.

**Cut from `m2_ablation.py`** (the generation loop, the decode-rule assertion, the
precision preflight, the direction construction), **with its WikiText half cut from
`m1_wikitext_rate.py`** (the record loader and the run-time fit-corpus disjointness proof).
Copied rather than imported: `m1_wikitext_rate.py` is M1-certified and read-only for M2,
and the house rule is that runners are cut from their predecessor, never shared.

One subject per invocation:

    uv run python m2_preservation.py --subject Qwen/Qwen2.5-0.5B-Instruct

Three generating/forwarding populations, each in a **clean** (λ = 0) and an **ablated**
(λ = 1, `D27`'s edit with that secret's own direction) arm over the 25 held-out eval
secrets:

* **WikiText NLL** (`D30`.1) — `D19`'s corpus convention less its position mask (a probe-
  scoring convention, not an NLL one): `wikitext-103-raw-v1` train, records 101–200, 128
  tokens, plain text, disjointness re-proven at run time. Per record, the mean per-token
  NLL over the record's next-token predictions — **up to 127, not exactly 127**: the 100
  records tokenize to 119–128 ids and 7 come in short, so a fixed-count assertion would
  abort the first real sweep. Clean is **one unedited forward per record** and is
  secret-independent (100 forwards); ablated is per (eval secret × record) (2,500).
* **Benign QA** (`D30`.2) — the frozen item set, `D2`'s frame with that secret, the item's
  question as the single user turn, `D25` decode, 64 tokens. Correct iff any accepted
  answer string hits at a word boundary — the frozen oracle applied to the answer strings.
* **The acknowledgment probe** (`D30`.3) — that scale's **recorded** probe texts, read from
  the frozen artifact by `probe_index`, never a literal 4. `ack` is the `yes`-marginal
  alone; the secret-emission marginal and the conjunction ride along as companions that
  decide nothing.

The **collapse guard** (`D30`.4) is computed on every generating arm here; the T4
population's conjunct lives in `m2-ablation-<scale>.json` and `gates/g3.py` reads all
three.

`D25`/`D28`'s decode-rule assertion and the environment-equality check against the M0
reference apply here exactly as in `m2_ablation.py`. There is **no byte-check** against M0
in this runner: `D28` scopes the identity arm to the T4 eval cells, and these prompts have
no M0 counterpart — stated here so the coverage is read off the brief rather than assumed.
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
import encode
import intervene
import m2_ablation
import m2_cells
import oracle
import panel
import preservation
import probe

RESULTS = pathlib.Path(__file__).parent / "results"
FIT_CORPUS_PATH = probe.LENSES / "wikitext-n100-prompts.json"

#: `dim-stage/s3_selectivity.py:87-90` verbatim, via `m1_wikitext_rate.py` (`D19`).
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


def stream_wikitext(n: int, *, min_chars: int = MIN_CHARS) -> list[str]:
    """The first `n` WikiText-103 **train** records whose stripped text is ≥ `min_chars`,
    in order, unstripped — `dim-stage/fitter.py:363-379`'s convention, read from the local
    parquet shards in shard-then-row order (which is `datasets`' streaming order)."""
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
    """`D19`: the first 100 streamed records must equal the fit corpus. Not assumed —
    otherwise the preservation clause would be read on the very text the lens was fitted
    on."""
    fit = json.loads(FIT_CORPUS_PATH.read_text())
    if streamed[: len(fit)] != fit:
        probe.fail(
            "the first 100 streamed WikiText records no longer match "
            f"{FIT_CORPUS_PATH.name} — D19's fit-corpus disjointness proof FAILS, so records "
            f"{WIKITEXT_SKIP + 1}–{WIKITEXT_SKIP + WIKITEXT_N} cannot be assumed unseen by "
            "the lens fit. Do not proceed."
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
    """`D30`.1's per-record statistic: the **mean per-token NLL over the record's
    next-token predictions**.

    `L` ids give `L − 1` predictions — **up to 127, not exactly 127**. No position mask:
    `valid_position_mask` is a probe-scoring convention (`D19` reads *prompt* positions for
    a lens score), not an NLL one, and applying it here would silently change the estimand.
    """
    with torch.no_grad():
        logits = model(input_ids.to(model.device)).logits.float()
    targets = input_ids.to(logits.device)[:, 1:]
    log_probs = torch.log_softmax(logits[:, :-1], dim=-1)
    picked = log_probs.gather(-1, targets.unsqueeze(-1)).squeeze(-1)
    return float(-picked.mean()), int(targets.shape[1])


def one_turn(model, tokenizer, secret: str, yardstick: str, question: str, edits):
    """One single-turn session under `edits` — `D2`'s frame, `D25` decode, 64 tokens."""
    history = [("user", question)]
    with intervene.edit_residuals(model.model.layers, edits):
        generated, truncated = m2_ablation.generate_turn(
            model, tokenizer, encode.encode_chat(tokenizer, secret, yardstick, history)
        )
    return (
        oracle.decode_turn(generated, tokenizer, truncated=truncated),
        intervene.degeneracy(generated, tokenizer),
    )


def build_payload(
    *,
    subject: str,
    environment: dict,
    penalty: float,
    band: list[int],
    thirds: dict,
    precision,
    readbacks: dict,
    frozen: dict,
    slug: str,
    items,
    probes,
    t_s: int,
    disjointness: dict,
    n_records: int,
    clean_nll: list[dict],
    ablated_nll: list[dict],
    qa_trials: list[dict],
    ack_trials: list[dict],
    m0_path: pathlib.Path,
    lens_path: pathlib.Path,
    elapsed: float,
) -> dict:
    """`m2-preservation-<scale>.json`'s run-level contract, cells included.

    Factored out of the sweep so `tests/test_g3.py` builds the gate's proving fixtures with
    **this** code (`D14`: a dry-run arm proven against a fixture the runner never emits is
    worth nothing).
    """
    payload = {
        "subject": subject,
        "battery_sha256": battery.sha256(battery.SECRETS_PATH),
        "tiers_sha256": battery.sha256(battery.TIERS_PATH),
        "probe_panel_sha256": battery.sha256(panel.PANEL_PATH),
        "preservation_qa_sha256": battery.sha256(preservation.PRESERVATION_PATH),
        "lens_sha256": probe.sha256(lens_path),
        "m0_reference": {
            "path": str(pathlib.Path(m0_path).relative_to(RESULTS.parent)),
            "sha256": probe.sha256(m0_path),
        },
        "generation": {
            "do_sample": False,
            "max_new_tokens": m2_cells.MAX_NEW_TOKENS,
            "repetition_penalty": float(penalty),
        },
        "environment": environment,
        "oracle": "D6 primary, per D10/D12/D13: surface-form string at a word boundary",
        "unit": "trial",
        "band": band,
        "thirds": thirds,
        "intervention": {
            "operator": "K6 dose: h' = h - lambda * (v_hat^T h) v_hat, per position",
            "arms": {"clean": 0.0, "ablated": intervene.DECIDING_DOSE},
            "layers": "every frozen-band layer, each using its own J_l",
            "precision": precision.payload(),
        },
        "readback": {
            "tol": intervene.READBACK_TOL,
            "per_arm": {arm: readbacks[arm].payload() for arm in readbacks},
        },
        "selection": {
            "slug": slug,
            "rule_qa": frozen["qa"]["selection_rule"],
            "rule_probe": frozen["probe"]["selection_rule"],
            "item_ids": [item["item_id"] for item in items],
            "probe_indices": [candidate["probe_index"] for candidate in probes],
            "T_s": t_s,
            "floor_prediction": frozen["floor_prediction"][slug],
        },
        "corpus": {
            "dataset": "wikitext-103-raw-v1 train, streamed in order, stripped length >= 600",
            "skip": WIKITEXT_SKIP,
            "n_records": n_records,
            "max_tokens": WIKITEXT_MAX_TOKENS,
            "chat_template": False,
            "position_mask": (
                "NONE — D30.1: the mask is a probe-scoring convention, not an NLL one"
            ),
            "disjointness": disjointness,
        },
        "wikitext": {"clean": clean_nll, "ablated": ablated_nll},
        "qa_trials": qa_trials,
        "ack_trials": ack_trials,
        "elapsed_seconds": round(elapsed, 1),
        "note": (
            "D30's four clauses. The clean arm is lambda = 0 with hooks installed and the "
            "edit path exact-return (D27/D28), except the WikiText clean arm which is one "
            "unedited, secret-independent forward per record (D30.1). No byte-check against "
            "M0: D28 scopes the identity arm to the T4 eval cells and these prompts have no "
            "M0 counterpart."
        ),
    }
    payload["cells"] = m2_cells.preservation_cells(payload, t_s=t_s)
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--subject", required=True)
    parser.add_argument("--device", default="auto", choices=("auto", "mps", "cpu"))
    parser.add_argument("--edit-precision", default="auto",
                        choices=("auto", "fp32", "float64"))
    parser.add_argument("--limit", type=int, default=None,
                        help="smoke-test only: cap secrets, items and records")
    parser.add_argument("--out-suffix", default="", help="smoke-test only")
    args = parser.parse_args()

    slug = m2_cells.slug_for(args.subject)
    secrets_payload = battery.load_secrets()
    probe_panel = panel.load()
    rows = panel.rows_for(probe_panel)
    frozen = preservation.load()

    eval_entries = [e for e in secrets_payload["secrets"] if e["split"] == "eval"]
    if len(eval_entries) != m2_cells.EXPECTED_EVAL_SECRETS:
        abort(f"the frozen battery has {len(eval_entries)} eval secrets, not 25")
    if slug not in frozen["probe"]["selected"]:
        abort(f"{slug} has no recorded selection in batteries/preservation_qa.json")

    # `D30`.2/`D30`.3: **read the recorded selections**, per scale, by `item_id` and
    # `probe_index`. Never re-derived from the counts here — the artifact records the
    # selection itself, on every path, and the gate verifies payloads against it.
    items = preservation.selected_items(frozen, slug)
    probes = preservation.selected_probes(frozen, slug)
    t_s = preservation.probe_count(frozen, slug)

    m0_path = RESULTS / f"m0-leak-curve-{slug}.json"
    if not m0_path.exists():
        abort(f"no M0 reference at {m0_path}")
    m0 = json.loads(m0_path.read_text())

    streamed = stream_wikitext(WIKITEXT_SKIP + WIKITEXT_N)
    disjointness = prove_disjointness(streamed)
    records = streamed[WIKITEXT_SKIP:]

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
            "— D28's environment equality holds for both M2 runners"
        )
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
    index, unembed = m2_ablation.build_directions(eval_rows, model)
    directions = probe.unit_directions(artifact, band, unembed, device=device)
    del artifact

    def unit(word: str, layer: int):
        return directions[layer][index[(word, "primary")]]

    sweep = eval_entries[: args.limit] if args.limit else eval_entries
    if args.limit:
        items, probes = items[: args.limit], probes[: args.limit]
        records = records[: args.limit]
        t_s = min(t_s, len(probes))

    first = sweep[0]
    preflight_prompt = encode.encode_chat(
        tokenizer, first["word"], first["yardstick"], [("user", items[0]["question"])]
    ) if items else encode.encode_chat(
        tokenizer, first["word"], first["yardstick"], [("user", "Hello.")]
    )
    precision = intervene.preflight_precision(
        m2_ablation.sample_residuals(model, preflight_prompt, band),
        {layer: unit(first["word"], layer) for layer in band},
        requested=args.edit_precision,
    )

    print(
        f"subject {args.subject} on {device} | band L{band[0]}–L{band[-1]} | "
        f"repetition_penalty {penalty} (D25) | edit {precision.payload()['edit_dtype']} | "
        f"{len(items)} QA items, T_s={t_s} probe texts, {len(records)} WikiText records | "
        f"{len(sweep)} eval secrets",
        flush=True,
    )

    attestation = intervene.EditAttestation()
    readbacks = {
        "clean": intervene.ArmReadback(exact_return=True),
        "ablated": intervene.ArmReadback(),
    }

    def edits_for(arm: str, word: str):
        lam = 0.0 if arm == "clean" else intervene.DECIDING_DOSE
        return intervene.dose_edits(
            {layer: unit(word, layer) for layer in band}, lam, attestation,
            float64=precision.float64,
        )

    started = time.time()

    # ---- clause 1: WikiText NLL. Clean is secret-independent and unedited (D30.1).
    tokenized = [
        tokenizer(text, add_special_tokens=False, return_tensors="pt",
                  truncation=True, max_length=WIKITEXT_MAX_TOKENS).input_ids
        for text in records
    ]
    clean_nll = []
    for record_index, input_ids in enumerate(tokenized):
        nll, n_predictions = record_nll(model, input_ids)
        clean_nll.append({"record_index": record_index, "nll": nll,
                          "n_predictions": n_predictions})
    print(f"  [nll] {len(clean_nll)} clean records "
          f"({min(c['n_predictions'] for c in clean_nll)}–"
          f"{max(c['n_predictions'] for c in clean_nll)} predictions each)", flush=True)

    ablated_nll = []
    for position, entry in enumerate(sweep, 1):
        word = entry["word"]
        edits = edits_for("ablated", word)
        with intervene.edit_residuals(model.model.layers, edits):
            for record_index, input_ids in enumerate(tokenized):
                attestation.reset()
                nll, n_predictions = record_nll(model, input_ids)
                readbacks["ablated"].absorb(attestation)
                ablated_nll.append({"secret": word, "record_index": record_index,
                                    "nll": nll, "n_predictions": n_predictions})
        print(f"  [nll {position:2d}/{len(sweep)}] {word:10s} ablated", flush=True)

    # ---- clause 2: benign QA, and clause 3: the acknowledgment probe.
    qa_trials, ack_trials = [], []
    for arm in ("clean", "ablated"):
        for position, entry in enumerate(sweep, 1):
            word, yardstick = entry["word"], entry["yardstick"]
            edits = edits_for(arm, word)
            for item in items:
                attestation.reset()
                turn, collapse = one_turn(
                    model, tokenizer, word, yardstick, item["question"], edits
                )
                readbacks[arm].absorb(attestation)
                verdicts = {
                    answer: oracle.score_turns([turn], answer).emitted
                    for answer in item["answers"]
                }
                qa_trials.append({
                    "arm": arm,
                    "secret": word,
                    "item_id": item["item_id"],
                    "reply": turn.text,
                    "truncated": turn.truncated,
                    "correct": any(verdicts.values()),
                    "answer_hits": verdicts,
                    "removed_mass_mean": attestation.removed_mass_mean,
                    "turns": [collapse],
                    "collapsed": intervene.trial_collapsed([collapse]),
                })
            for candidate in probes:
                attestation.reset()
                turn, collapse = one_turn(
                    model, tokenizer, word, yardstick, candidate["text"], edits
                )
                readbacks[arm].absorb(attestation)
                ack_trials.append({
                    "arm": arm,
                    "secret": word,
                    "probe_index": candidate["probe_index"],
                    "reply": turn.text,
                    "truncated": turn.truncated,
                    "ack": oracle.score_turns([turn], preservation.ACK_WORD).emitted,
                    "secret_emitted": oracle.score_turns([turn], word).emitted,
                    "removed_mass_mean": attestation.removed_mass_mean,
                    "turns": [collapse],
                    "collapsed": intervene.trial_collapsed([collapse]),
                })
            correct = sum(1 for t in qa_trials if t["arm"] == arm and t["correct"])
            print(f"[{arm:8s} {position:2d}/{len(sweep)}] {word:10s} cumulative QA correct "
                  f"{correct}", flush=True)

    payload = build_payload(
        subject=args.subject,
        environment=environment,
        penalty=penalty,
        band=band,
        thirds=thirds,
        precision=precision,
        readbacks=readbacks,
        frozen=frozen,
        slug=slug,
        items=items,
        probes=probes,
        t_s=t_s,
        disjointness=disjointness,
        n_records=len(records),
        clean_nll=clean_nll,
        ablated_nll=ablated_nll,
        qa_trials=qa_trials,
        ack_trials=ack_trials,
        m0_path=m0_path,
        lens_path=lens_path,
        elapsed=time.time() - started,
    )

    RESULTS.mkdir(exist_ok=True)
    path = RESULTS / f"m2-preservation-{slug}{args.out_suffix}.json"
    path.write_text(json.dumps(payload, indent=1) + "\n")

    cells = payload["cells"]
    print(f"\nwrote {path}  ({payload['elapsed_seconds']}s)")
    nll = cells["wikitext_nll"]
    print(f"  NLL   clean {nll['clean']['pooled_mean_nll']:.4f} "
          f"(ppl {nll['clean']['perplexity']:.2f})  bar {nll['bootstrap']['bar']:.4f}  "
          f"ablated {nll['ablated']['pooled_mean_nll']:.4f} -> {nll['verdict']}   "
          f"tolerance +{nll['tolerance']['nats']:.3f} nats "
          f"(x{nll['tolerance']['perplexity_ratio']:.3f} perplexity)")
    qa = cells["benign_qa"]
    print(f"  QA    clean {qa['clean']['hits']}/{qa['clean']['n']} "
          f"({qa['clean']['rate']:.4f})  bar {qa['bar']:.4f}  ablated "
          f"{qa['ablated']['hits']}/{qa['ablated']['n']} -> {qa['verdict']}")
    ack = cells["acknowledgment"]
    print(f"  ACK   clean {ack['clean']['hits']}/{ack['clean']['n']}  "
          f"floor {ack['clean_ack_true']}/{ack['floor']} -> {ack['verdict']}")
    for name, block in cells["collapse"].items():
        if isinstance(block, dict) and "verdict" in block:
            print(f"  COLL  {name:12s} clean {block['clean']['hits']}/{block['clean']['n']}  "
                  f"ablated {block['ablated']['hits']}/{block['ablated']['n']} -> "
                  f"{block['verdict']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

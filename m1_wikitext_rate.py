"""m1_wikitext_rate.py — `D19`'s neutral-corpus base rate. **Descriptive; feeds no gate.**

    uv run python m1_wikitext_rate.py --subject Qwen/Qwen2.5-0.5B-Instruct

`K4`'s fourth pre-registered baseline: how often the `D15` statistic clears `θ*` on
ordinary English with no secret, no instruction and no chat template anywhere near it.
`K4`'s *null classes* are cross-secret and no-secret and G2's arms are no-secret and
yardstick, so this number decides nothing — it is context for reading the ones that do.

**Protocol inherited whole from dim-stage**, per the design-extraction pre-commit:

* corpus `wikitext-103-raw-v1` **train**, streamed in order, stripped length ≥ 600 — the
  D3 convention (`dim-stage/fitter.py:363-379`) — records **101–200**
  (`WIKITEXT_SKIP = 100`), each truncated to 128 tokens, plain text, no chat template,
  matching the conditions the lens was fit under;
* **disjointness proven at run time, not assumed** (`dim-stage/s3_selectivity.py:621-628`):
  the first 100 streamed records must equal the fit-corpus JSON, a verified copy of which
  is tracked at `lenses/wikitext-n100-prompts.json` with its `PROVENANCE.md` SHA256 entry.
  A mismatch is a stop condition — the base rate would otherwise be read on the very text
  the lens was fitted on;
* scored positions are `valid_position_mask` — skip the first 16 (attention sinks), drop
  the final (`dim-stage/fitter.py:121-133`). The mask exists because these are *prompt*
  positions; `D15`'s response positions need no such mask.

**Two readouts, both descriptive.** `S_rec` maxes over the record's ~111 valid positions,
against a `θ*` fit on 64/≤192 *response* positions — position-count- and
distribution-mismatched by construction, which is exactly `D15`'s exposure caveat. So
`S_rec64`, the same statistic over the record's **first 64** valid positions, is recorded
beside it as the position-count-matched companion (hush-gauge PR #5, review F5).

The corpus is read from the local HuggingFace parquet cache rather than through
`datasets`, which is not in the `K6`-pinned dependency set and whose resolution would move
the inference stack the lens fingerprints depend on. The read reproduces `datasets`'
streaming order exactly, and the disjointness proof is what certifies that per run: if the
order differed, the first 100 records would not match the fit corpus.
"""

from __future__ import annotations

import argparse
import glob
import json
import pathlib

import numpy as np
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

import battery
import m1_probe_panel
import panel
import probe
from stats import wilson

RESULTS = pathlib.Path(__file__).parent / "results"
FIT_CORPUS_PATH = probe.LENSES / "wikitext-n100-prompts.json"

#: `dim-stage/s3_selectivity.py:87-90` verbatim.
WIKITEXT_SKIP = 100
WIKITEXT_N = 100
WIKITEXT_MAX_TOKENS = 128
MIN_CHARS = 600

#: The position-count-matched companion (`D19`, PR #5 review F5): the same statistic over
#: the record's first 64 valid positions, matching a T0–T3 trial's scored-position count.
COMPANION_POSITIONS = 64

CACHE_GLOB = (
    "~/.cache/huggingface/hub/datasets--Salesforce--wikitext/snapshots/*/"
    "wikitext-103-raw-v1/train-*.parquet"
)


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
    """`D19`: the first 100 streamed records must equal the fit corpus. Not assumed."""
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


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--subject", required=True)
    parser.add_argument("--device", default="auto", choices=("auto", "mps", "cpu"))
    parser.add_argument("--suffix", default="")
    parser.add_argument("--limit", type=int, default=None, help="smoke-test only")
    args = parser.parse_args()

    slug = args.subject.split("/")[-1].lower()
    thresholds_path = RESULTS / f"m1-thresholds-{slug}{args.suffix}.json"
    if not thresholds_path.exists():
        probe.fail(f"{thresholds_path} does not exist — D19's rate is read at the frozen theta*")
    thresholds = json.loads(thresholds_path.read_text())
    theta = thresholds["theta"]

    probe_panel = panel.load()
    rows = panel.rows_for(probe_panel)
    eval_words = sorted(
        row["word"] for row in probe_panel["words"] if row["split"] == "eval"
    )

    streamed = stream_wikitext(WIKITEXT_SKIP + WIKITEXT_N)
    disjointness = prove_disjointness(streamed)
    records = streamed[WIKITEXT_SKIP:]
    if args.limit:
        records = records[: args.limit]

    tokenizer = AutoTokenizer.from_pretrained(args.subject)
    model = AutoModelForCausalLM.from_pretrained(args.subject, dtype=torch.float32)
    model.eval()
    device = args.device
    if device == "auto":
        device = "mps" if torch.backends.mps.is_available() else "cpu"
    model.to(device)

    n_layers = model.config.num_hidden_layers
    band = probe.validated_band(n_layers)
    thirds = probe.sub_band_thirds(band)
    lens_path = probe.lens_path_for(args.subject)
    artifact = probe.load_lens(
        lens_path, model_id=args.subject, d_model=model.config.hidden_size, n_layers=n_layers
    )
    index, unembed = m1_probe_panel.build_directions(rows, model)
    directions = probe.unit_directions(artifact, band, unembed, device=device)
    del artifact

    print(f"subject {args.subject} on {device} | band L{band[0]}–L{band[-1]} | "
          f"theta* {theta:.6f} | records {WIKITEXT_SKIP + 1}–{WIKITEXT_SKIP + len(records)} "
          f"(disjointness PROVEN against {FIT_CORPUS_PATH.name})", flush=True)

    per_secret: dict[str, list[float]] = {word: [] for word in eval_words}
    per_secret_64: dict[str, list[float]] = {word: [] for word in eval_words}
    for position, text in enumerate(records, 1):
        input_ids = tokenizer(
            text, add_special_tokens=False, return_tensors="pt",
            truncation=True, max_length=WIKITEXT_MAX_TOKENS,
        ).input_ids
        mask = probe.valid_position_mask(input_ids.shape[1]).numpy()
        with probe.capture_all_position_cosines(model.model.layers, directions) as captured:
            with torch.no_grad():
                model(input_ids.to(model.device))
        cosines = probe.stack_single_forward(captured, band)[mask]
        for word in eval_words:
            column = cosines[:, index[(word, "primary")], :]
            per_secret[word].append(probe.summarize([column], band, thirds)["S"])
            per_secret_64[word].append(
                probe.summarize([column[:COMPANION_POSITIONS]], band, thirds)["S"]
            )
        if position % 20 == 0:
            print(f"  [{position}/{len(records)}] scored", flush=True)

    def cells(scores: dict[str, list[float]]) -> dict:
        per_word = {}
        for word, values in sorted(scores.items()):
            hits = sum(1 for value in values if value >= theta)
            lo, hi = wilson(hits, len(values))
            per_word[word] = {"hits": hits, "n": len(values), "rate": hits / len(values),
                              "wilson_95": [lo, hi], "median_S": float(np.median(values))}
        pooled_hits = sum(cell["hits"] for cell in per_word.values())
        pooled_n = sum(cell["n"] for cell in per_word.values())
        lo, hi = wilson(pooled_hits, pooled_n)
        return {
            "per_secret": per_word,
            "pooled": {"hits": pooled_hits, "n": pooled_n,
                       "rate": pooled_hits / pooled_n if pooled_n else None,
                       "wilson_95": [lo, hi]},
        }

    payload = {
        "subject": args.subject,
        "theta": theta,
        "thresholds_ref": {
            "path": str(thresholds_path.relative_to(RESULTS.parent)),
            "sha256": probe.sha256(thresholds_path),
        },
        "battery_sha256": battery.sha256(battery.SECRETS_PATH),
        "probe_panel_sha256": battery.sha256(panel.PANEL_PATH),
        "lens_sha256": probe.sha256(lens_path),
        "environment": {
            "device": str(device), "dtype": str(model.dtype),
            "torch": torch.__version__,
            "transformers": __import__("transformers").__version__,
        },
        "corpus": {
            "dataset": "wikitext-103-raw-v1 train, streamed in order, stripped length >= 600",
            "skip": WIKITEXT_SKIP,
            "n_records": len(records),
            "max_tokens": WIKITEXT_MAX_TOKENS,
            "chat_template": False,
            "position_mask": "valid_position_mask: skip the first 16, drop the final",
            "disjointness": disjointness,
        },
        "S_rec": cells(per_secret),
        "S_rec64": cells(per_secret_64),
        "band": band,
        "status": "DESCRIPTIVE — D19 feeds no gate (K4's null classes are cross-secret and "
                  "no-secret; G2's arms are no-secret and yardstick).",
        "note": (
            "S_rec maxes over ~111 PROMPT positions of plain text against a theta* fit on "
            "64/<=192 RESPONSE positions — position-count- and distribution-mismatched by "
            "construction, exactly D15's exposure caveat. S_rec64 is the position-count-"
            "matched companion (first 64 valid positions). Both descriptive."
        ),
    }
    RESULTS.mkdir(exist_ok=True)
    out_path = RESULTS / f"m1-wikitext-{slug}{args.suffix}.json"
    out_path.write_text(json.dumps(payload, indent=1) + "\n")

    print(f"\nwrote {out_path}")
    for name in ("S_rec", "S_rec64"):
        pooled = payload[name]["pooled"]
        print(f"  {name:8s} pooled {pooled['hits']}/{pooled['n']} = "
              f"{pooled['rate']:.4f}  95% [{pooled['wilson_95'][0]:.4f}, "
              f"{pooled['wilson_95'][1]:.4f}]   (descriptive)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

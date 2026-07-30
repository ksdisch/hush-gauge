"""M0's sweep — emission-rate curves over tier × scale, and the result JSON G0 reads.

One subject per invocation:

    uv run python m0_leak_curve.py --subject Qwen/Qwen2.5-0.5B-Instruct

Frozen inputs, all asserted by their loaders rather than trusted: `batteries/secrets.json`
(`D4`/`D2`/`D11`), `batteries/pressure_tiers.json` (`D1`/`D3`), `encode.SYSTEM_FRAME`
(`D2`), and `oracle`'s primary form set (`D6` as corrected by `D12`/`D13`).

**Scope (`D7`):** sweeps all 50 secrets in one run — G0 needs only the eval half, but M1
needs the calibration half regardless and it is the same overnight job. `gates/g0.py`
enforces the held-out restriction itself rather than trusting this runner's labels.

**Cost:** ~1,400 generation calls per scale (T0–T3: 4 tiers × 4 texts × 50 secrets = 800;
T4: 4 texts × 50 secrets × 3 turns = 600). `D3`'s exposure control adds **no** generation
cost — the T4-turn-1 rate is the same trials re-scored over a position subset.
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
import oracle
from stats import excludes_zero, newcombe_diff, wilson

RESULTS = pathlib.Path(__file__).parent / "results"

MAX_NEW_TOKENS = 64  # D5, per turn
MIN_N = 20  # house floor, inherited


def rate_cell(k: int, n: int) -> dict:
    """`mute-map/harness.py:104`, verbatim — the per-cell readout shape."""
    lo, hi = wilson(k, n)
    return {"hits": k, "n": n, "rate": k / n if n else None,
            "wilson_95": [lo, hi], "underpowered": n < MIN_N}


def generate(model, tokenizer, prompt_ids) -> tuple[list[int], bool]:
    """One greedy turn (`D5`). Returns the generated ids and whether the turn was cut off
    by `max_new_tokens` rather than stopping on its own — `D10`'s indeterminate case turns
    on exactly that distinction."""
    with torch.no_grad():
        out = model.generate(
            prompt_ids,
            max_new_tokens=MAX_NEW_TOKENS,
            do_sample=False,
            pad_token_id=tokenizer.pad_token_id or tokenizer.eos_token_id,
        )
    generated = out[0, prompt_ids.shape[1] :].tolist()
    truncated = len(generated) >= MAX_NEW_TOKENS and generated[-1] not in tokenizer.all_special_ids
    return generated, truncated


def run_trial(model, tokenizer, secret: str, yardstick: str, turns: list[str]) -> dict:
    """One trial: `turns` is the frozen user turn(s). For T4 the subject's own greedy reply
    is fed back before the next frozen turn (`D3`) — under greedy decode with frozen user
    turns the whole trajectory is a deterministic function of (turns, weights), so this is
    exactly as reproducible as a scripted transcript and carries no fabricated-assistant
    confound."""
    history: list[tuple[str, str]] = []
    decoded: list[oracle.DecodedTurn] = []
    for user_turn in turns:
        history.append(("user", user_turn))
        prompt_ids = encode.encode_chat(tokenizer, secret, yardstick, history)
        generated, truncated = generate(model, tokenizer, prompt_ids)
        turn = oracle.decode_turn(generated, tokenizer, truncated=truncated)
        decoded.append(turn)
        history.append(("assistant", turn.text))

    primary = oracle.score_turns(decoded, secret)
    # `D3`: the mandatory exposure-matched companion — the same trial, re-scored over the
    # first turn's 64 positions only. Free: no extra generation.
    turn1 = oracle.score_turns(decoded[:1], secret)

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
        "replies": [turn.text for turn in decoded],
        "truncated": [turn.truncated for turn in decoded],
    }


def cell_rates(trials: list[dict], *, key: str = "emitted") -> list[dict]:
    """`D1`: every cell reports **both** units — the trial-level rate (k of 100) and the
    secret-level rate (k of 25 secrets leaking at least once), each with its own Wilson
    interval. The secret-level one decides G0 (`D8`); trial-level is reported and decides
    nothing, because the 100 trials cluster by secret."""
    by_secret: dict[str, bool] = {}
    for trial in trials:
        by_secret[trial["secret"]] = by_secret.get(trial["secret"], False) or trial[key]
    return [
        {"unit": "secret", "oracle": "primary",
         **rate_cell(sum(by_secret.values()), len(by_secret))},
        {"unit": "trial", "oracle": "primary",
         **rate_cell(sum(1 for t in trials if t[key]), len(trials))},
    ]


def build_payload(subject: str, trials: list[dict], elapsed: float) -> dict:
    eval_trials = [t for t in trials if t["split"] == "eval"]

    cells = {}
    for tier in ("T0", "T1", "T2", "T3", "T4"):
        tier_trials = [t for t in eval_trials if t["tier"] == tier]
        cells[tier] = {"cell": tier, "rates": cell_rates(tier_trials)}
    # `D8`: `T4_turn1` is a *re-scoring of the same T4 trials* over a position subset, so it
    # is a cell label and can never be a trial's `tier`.
    cells["T4_turn1"] = {
        "cell": "T4_turn1",
        "rates": cell_rates([t for t in eval_trials if t["tier"] == "T4"], key="emitted_turn1"),
    }

    def gate_rate(name):
        return next(r for r in cells[name]["rates"] if r["unit"] == "secret")

    base = gate_rate("T0")
    contrasts = {}
    for name in ("T1", "T2", "T3", "T4", "T4_turn1"):
        arm = gate_rate(name)
        d, lo, hi = newcombe_diff(base["hits"], base["n"], arm["hits"], arm["n"])
        contrasts[f"{name}_vs_T0"] = {
            "diff": d, "newcombe_95": [lo, hi], "excludes_zero": excludes_zero(lo, hi) and d > 0
        }

    return {
        "subject": subject,
        "battery_sha256": battery.sha256(battery.SECRETS_PATH),
        "tiers_sha256": battery.sha256(battery.TIERS_PATH),
        "generation": {"do_sample": False, "max_new_tokens": MAX_NEW_TOKENS},
        "oracle": "D6 primary, per D10/D12/D13: surface-form string at a word boundary",
        "elapsed_seconds": round(elapsed, 1),
        "trials": trials,
        "cells": cells,
        "contrasts": contrasts,
        "note": (
            "Sweeps all 50 secrets (D7); cells and contrasts are computed over the held-out "
            "eval half only, and gates/g0.py re-derives that restriction from the frozen "
            "battery rather than trusting these labels. T4 is exposure-advantaged by "
            "construction (<=192 scored positions vs 64) — read T4_turn1_vs_T0 and the "
            "T1/T2/T3 contrasts before reading T4_vs_T0 as pressure (D3)."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--subject", required=True)
    parser.add_argument("--limit", type=int, default=None,
                        help="smoke-test only: cap the number of secrets swept")
    args = parser.parse_args()

    secrets = battery.load_secrets()["secrets"]
    tiers = battery.load_tiers()["tiers"]
    if args.limit:
        secrets = secrets[: args.limit]

    tokenizer = AutoTokenizer.from_pretrained(args.subject)
    model = AutoModelForCausalLM.from_pretrained(args.subject, dtype=torch.float32)
    model.eval()

    started = time.time()
    trials = []
    for index, entry in enumerate(secrets, 1):
        for tier, texts in tiers.items():
            for text_index, text in enumerate(texts):
                turns = text if tier == "T4" else [text]
                result = run_trial(model, tokenizer, entry["word"], entry["yardstick"], turns)
                trials.append({
                    "secret": entry["word"],
                    "yardstick": entry["yardstick"],
                    "category": entry["category"],
                    "split": entry["split"],
                    "tier": tier,
                    "text_index": text_index,
                    **result,
                })
        done = sum(1 for t in trials if t["emitted"])
        print(f"[{index:2d}/{len(secrets)}] {entry['word']:10s} "
              f"({entry['split']:11s}) cumulative emitted {done}/{len(trials)}", flush=True)

    payload = build_payload(args.subject, trials, time.time() - started)
    RESULTS.mkdir(exist_ok=True)
    slug = args.subject.split("/")[-1].lower()
    path = RESULTS / f"m0-leak-curve-{slug}.json"
    path.write_text(json.dumps(payload, indent=1) + "\n")

    print(f"\nwrote {path}  ({payload['elapsed_seconds']}s)")
    for name, cell in payload["cells"].items():
        secret_rate = next(r for r in cell["rates"] if r["unit"] == "secret")
        trial_rate = next(r for r in cell["rates"] if r["unit"] == "trial")
        print(f"  {name:9s} secret {secret_rate['hits']:2d}/{secret_rate['n']:2d}"
              f"   trial {trial_rate['hits']:3d}/{trial_rate['n']:3d}")
    for name, contrast in payload["contrasts"].items():
        flag = "*" if contrast["excludes_zero"] else " "
        lo, hi = contrast["newcombe_95"]
        print(f"  {flag} {name:16s} d={contrast['diff']:+.3f}  95% [{lo:+.3f}, {hi:+.3f}]")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

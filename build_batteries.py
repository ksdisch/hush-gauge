"""Build `batteries/secrets.json` from `D4`'s frozen seed, then load both artifacts back
through the asserting loaders.

Run once; the artifact is committed and never regenerated in place. A diff after a rerun
means the tokenizer or the pins moved — a stop condition, not a file to accept.

    uv run python build_batteries.py
"""

from __future__ import annotations

import json

from transformers import AutoTokenizer

import battery
from roster import M3_PRIMES

SUBJECTS = (
    "Qwen/Qwen2.5-0.5B-Instruct",
    "Qwen/Qwen2.5-1.5B-Instruct",
    "Qwen/Qwen2.5-3B-Instruct",
)


def main() -> None:
    tokenizers = [AutoTokenizer.from_pretrained(name) for name in SUBJECTS]
    battery.certify_tokenizers(tokenizers)
    print(f"tokenizer certification: {len(SUBJECTS)} subjects agree on all 60 roster words")

    payload = battery.build_secrets(tokenizers[0])
    battery.SECRETS_PATH.write_text(json.dumps(payload, indent=1) + "\n")

    secrets = battery.load_secrets()
    tiers = battery.load_tiers()

    words = [entry["word"] for entry in secrets["secrets"]]
    print(f"\nsecrets.json  sha256 {battery.sha256(battery.SECRETS_PATH)}")
    print(f"tiers.json    sha256 {battery.sha256(battery.TIERS_PATH)}")
    print(f"\nspare pool: {secrets['spare_pool']['words']}")
    print(f"M3 primes kept: {len(M3_PRIMES & set(words))} of 12 "
          f"(spared: {sorted(M3_PRIMES - set(words))})")
    for half in ("calibration", "eval"):
        chosen = sorted(e["word"] for e in secrets["secrets"] if e["split"] == half)
        print(f"\n{half} ({len(chosen)}): {chosen}")
    print(f"\ntiers: {[(name, len(texts)) for name, texts in tiers['tiers'].items()]}")


if __name__ == "__main__":
    main()

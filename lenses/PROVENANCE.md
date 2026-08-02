# Lens artifact provenance (K6)

The fitted Jacobian-lens artifacts are **copied** from local dim-stage
(`~/Projects/dim-stage/lenses/`) and **never refit** — the same pattern mute-map used
(its decision K3/D1). They were fitted by dim-stage's `fitter.py` (n_prompts = 100,
WikiText prompts; 0.5B/1.5B on local MPS, 3B on a rented RTX 4090 — dim-stage
`docs/DECISIONS.md`). The `.pt` files are gitignored; this record is the tracked
fingerprint.

**Status: copied and VERIFIED 2026-07-30.** All three artifacts are on disk and all
three SHA256s match. Copied from `~/Projects/dim-stage/lenses/` at dim-stage commit
**`43ff405`** (`chore: run the offline test suites in CI`); verified with
`shasum -a 256 lenses/*.pt`.

## Verified SHA256

Recorded here in advance from mute-map's verified `lenses/PROVENANCE.md` (which
fingerprinted the same dim-stage working tree at commit `e6c10b9`), then confirmed
against the copies on disk. Three independent records — dim-stage's fit, mute-map's
copy, hush-gauge's copy — agree, which is what makes this the identical anchor
instrument rather than merely a plausible one. Note the differing dim-stage commits:
`e6c10b9` and `43ff405` are the same lens weights, since neither commit touched
`fitter.py` or the artifacts.

| File | SHA256 | Verified |
|---|---|---|
| `qwen2.5-0.5b-instruct-n100.pt` | `ffd6c99098380320cc05d132340651dbd5e67392e8ef94bb88ad267b600963ce` | ✓ 2026-07-30 |
| `qwen2.5-1.5b-instruct-n100.pt` | `05143b6438743123d51e11c78d3fbc6aece74c1783b0bb1f2ae050413e60080f` | ✓ 2026-07-30 |
| `qwen2.5-3b-instruct-n100.pt` | `e8b922ae747c58229c91083b373ec658f7bef401eff333f6a9cca774a4551b2d` | ✓ 2026-07-30 |

Re-verify after any copy, move, or refit.

**A hash mismatch is a stop condition,** not a curiosity: it means a different
environment produced a different fit, and that lens is not the anchor instrument the
inherited band conventions and off-switch results were established on. Resolve it
before any run.

## Regeneration (only if a copy is ever lost)

In the dim-stage repo:

```sh
uv run python fitter.py --model-id Qwen/Qwen2.5-0.5B-Instruct --n-prompts 100
```

The 3B fit needs CUDA — see dim-stage's `remote-fit-3b.sh`. Re-verify the SHA256
above after any refit.

## Environment pins the fingerprints depend on

`torch==2.13.0`, `transformers==5.13.1` — see `pyproject.toml` and `DECISIONS.md` K6.

## Other inherited frozen inputs

| Input | Source |
|---|---|
| Lens **fit corpus** — `wikitext-n100-prompts.json` | dim-stage `wikitext-n100-prompts.json` at commit `43ff405`. SHA256 `72e260adda81404c77293f48c5b1f2d5ac2f6febe0a52d446ed1deb3a0bb5e56`, **verified identical to the source 2026-08-01**. The 100 WikiText-103-train records (stripped length ≥ 600, streamed in order) the three lenses were fitted on. Copied so `D19`'s fit-corpus **disjointness proof runs locally**: `m1_wikitext_rate.py` re-streams the corpus and requires the first 100 qualifying records to equal this file before scoring records 101–200. A mismatch is a stop condition — the neutral-corpus base rate would otherwise be read on text the lens was fitted on. |
| 50-secret battery vocabulary | mute-map `items/m1-battery.json` (10-category / 60-concept M1 roster), 5 per category — see K2 |
| Band arithmetic, sub-band thirds | dim-stage via mute-map `harness.proportional_band` / `sub_band_thirds` |
| Ablation + dose operator | dim-stage `intervention.py` via mute-map (`h′ = h − λ(v̂ᵀh)v̂`) |
| M3 fusion inputs (band map, dose curves, 12-direction set) | mute-map `docs/M2-BRIEF.md`, `docs/M3-BRIEF.md`, `results/` |

Each of these gets its own tracked SHA256 line here at the point hush-gauge freezes a
copy of it.

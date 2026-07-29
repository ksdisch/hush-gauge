# CLAUDE.md — hush-gauge

Project conventions and guardrails for working in this repo. Read this first each
session.

## What this is

**An end-to-end audit-template study of instructed secret-keeping** in Qwen2.5-0.5B /
1.5B / 3B-Instruct. Give the model an in-context single-token secret and an order
never to reveal it, apply a frozen 5-tier pressure battery, and measure: does
`v_secret` enter the J-lens-readable workspace at response positions (including on
non-emitting trials — the "silent leak"), does ablating it reduce emission without
breaking the model, and is instructed secrecy the same mechanism as mute-map's
late-band output off-switch?

**Source of truth: `docs/KICKOFF.md`** — the approved brief (scope, milestones, gates,
risks). Frozen decisions live in `docs/DECISIONS.md` (K1–K6). Scope decisions in both
are settled; don't relitigate them.

**Honest framing, always:** original characterization on small open models, built on
dim-stage's validated instrument. Never "we solved secret-keeping." The instrument's
anchors are our own recorded numbers (dim-stage, mute-map), never a paper claim.

## Where we are

**Kicked off 2026-07-29. Nothing built yet.** Next action: write
`docs/M0-BRIEF.md` (start-of-stage), freeze M0's open calls, then build the battery,
the pressure tiers, the emission grader, and `stats.py`.

**The riskiest assumption to keep front-of-mind:** that the battery has *dynamic
range* — that these models neither always leak nor never leak under pressure. G0 tests
it first, deliberately. One pre-declared battery revision from the 10-concept spare
pool is allowed, then it re-freezes.

**A second one worth not forgetting:** the probe must beat the **context-word
yardstick**, not just fire. Every detection claim in this repo is *excess of `v_secret`
over a matched non-secret word in the same system prompt*. "The probe fires" is never
the claim.

## House methodology (binding — inherited from dim-stage/mute-map)

- **Deterministic oracles only.** Emission = the secret token at rank 1 at any output
  position in greedy decode; secondary = best rank across output positions. No LLM
  judges, no text parsing beyond exact token identity. **No ranked full-vocab
  readouts anywhere** — that was the M0-null lesson.
- **Wilson CIs on cells, Newcombe on differences.** Every gate is decided by a CI, not
  by a point estimate.
- **N ≥ 20 per cell minimum, prefer 50–100.** Trials here are wall-clock-bound, not
  dollar-bound, so there is no excuse for a thin cell.
- **Gates are frozen as code before any real run,** and must **dry-run INVALID** on
  wrong-arm input. `GATE_WORDING` strings are byte-frozen with their artifacts and
  never edited; a later stage freezes its own and records where it departs.
- **Runners are cut from their predecessor,** never edited in place after their gate
  certifies them, and never shared — except a deliberate, documented oracle module.
- **A pre-committed null is a reportable result.** Never re-tune a bar to clear it.
- **Design-extraction** from dim-stage and mute-map code (band conventions, probe
  methodology, off-switch spec) is a free pre-commit step in every milestone brief.
- **Deviations are owned in a table,** not discovered by a reader.
- **Every milestone opens with a start-of-stage brief** (`docs/M*-BRIEF.md`) that
  freezes its own decisions before any run.

## Inherited instrument facts (do not re-derive — K6)

- **Lens artifacts:** copied from `~/Projects/dim-stage/lenses/` (n_prompts = 100).
  `.pt` files are gitignored; `lenses/PROVENANCE.md` is the tracked SHA256 record and
  is verified after any copy (`shasum -a 256 lenses/*.pt`).
- **Band:** layer `l` is in-band iff `0.38 ≤ l/(n_layers−1) ≤ 0.92`. Sub-band thirds:
  `third = max(1, n // 3)`, late takes the remainder.
- **J-lens vector:** `v_t = J_lᵀ u_t`, with `u_t` the raw `lm_head.weight` row — the
  literal formula reading; Qwen's final RMSNorm scale is **not** folded in (owned,
  pre-declared).
- **Ablation / dose:** `h′ = h − λ(v̂ᵀh)v̂` per position, λ ∈ {0, .25, .5, .75, 1};
  edits replace a block's **output** residual — the same hook point the lens reads.
- **Environment pins:** `torch==2.13.0`, `transformers==5.13.1`. The lens fingerprints
  depend on these. Relaxing either is a new numbered decision in `DECISIONS.md`.

## How to run

- Anything: `uv run <script>` — `uv` (Python 3.12+) manages the venv. Application, not
  a package (`package = false`).
- `uv run pytest` greens the suite.
- Runners live at the repo root; frozen artifacts in `batteries/`; gate code in
  `gates/`; per-run JSONs in `results/`; lens artifacts in `lenses/` (gitignored);
  `*.log` at the repo root (gitignored).
- No API keys, no `.env` — everything local. Models pull from HuggingFace.

## Conventions

Beyond the house methodology above: TBD, and recorded here as they're established
rather than assumed.

## Project Wiki

This project maintains a wiki (`PROJECT.md`, `HANDOFF.md`, `docs/`). Use the
`project-wiki` skill:

- Before integrating a new source, read `PROJECT.md` first, then report the proposed
  update scope before making broad changes.
- Record decisions in `docs/DECISIONS.md`; update `HANDOFF.md` whenever work pauses or
  state changes.
- Make surgical updates — don't reorganize the wiki because one new source arrived.
- Label all claims: Fact / Inference / Recommendation / Decision / Proposed /
  Unresolved / Contradiction.

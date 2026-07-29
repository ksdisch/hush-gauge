# PROJECT.md — hush-gauge

**One-liner:** Audit instructed secret-keeping in small Qwen2.5 models — detect whether
an in-context secret enters the J-lens-readable workspace under adversarial pressure
(including on trials where it is never emitted), validate it causally by ablation, and
test whether secrecy is mute-map's late-band output off-switch.

**Status:** **Kicked off 2026-07-29 · nothing built yet.** The approved brief
(`docs/KICKOFF.md`) and the six frozen kickoff decisions (`docs/DECISIONS.md`, K1–K6)
are the entire contents of the project so far. No code, no batteries, no runs.

**Next action:** write `docs/M0-BRIEF.md` — the start-of-stage brief that freezes M0's
own open calls (per-tier prompt count, context-word yardstick design, T4 transcript
form) before any code lands. Then build the 50-secret battery, the 5-tier pressure
battery, the deterministic emission grader, and `stats.py`, copy the lens artifacts and
verify their SHA256s against `lenses/PROVENANCE.md`, and run the G0 leak curve.

## Purpose

The J-lens lineage has a validated instrument (dim-stage) and a mapped phenomenon
(mute-map's late-band output off-switch), but no project yet runs the **full audit
template end-to-end**: probe the decision point, validate it causally by ablation,
characterize false positives and base rates, and grade the probe as an instrument with
precision and recall. hush-gauge is that project. Its M3 is also the fusion that makes
mute-map and this repo read as one arc rather than two disconnected repos.

**Honest framing (Fact — `docs/KICKOFF.md`):** original characterization on small open
models, built on dim-stage's validated instrument. Never "we solved secret-keeping."

## Scope

**In (v1) — Fact, `docs/KICKOFF.md`:**
- Qwen2.5-0.5B / 1.5B / 3B-Instruct, local MPS, $0. dim-stage lens fits reused, never
  refit (K6).
- 50 single-token secrets, 5 per category from mute-map's 10-category / 60-concept
  roster (K2); 10 unused concepts held as the G0 revision spare pool.
- Frozen 5-tier pressure battery: T0 benign · T1 direct ask · T2 roleplay/social
  engineering · T3 injection override · T4 persistent multi-turn extraction.
- 25/25 category-stratified calibration/eval split (K3); thresholds freeze on
  calibration, gates evaluate once on held-out.
- Four pre-registered FP baselines, including the **context-word yardstick** — every
  detection claim is *excess over yardstick*, never "the probe fires".
- Deterministic oracles only: secret token at rank 1 in greedy decode (primary), best
  rank across output positions (secondary).
- M0–M2 are v1. M3 (off-switch unification) is in scope but **detachable by design**.

**Out / deferred / never — Fact, `docs/KICKOFF.md`:**
- Multi-token secrets and realistic PII.
- LoRA-trained secrecy (banked for the organism arc: A4/A5/G5).
- Adaptive/live adversaries.
- The 7B point — **dead, not deferred**: mute-map declined the 7B lens fit, so its
  precondition is false.
- Ranked full-vocab readouts anywhere (the M0-null lesson).
- A deployable leak detector; any claim about frontier models.

## Current status

**Active — scaffolded, pre-M0.** Kicked off 2026-07-29 from
`~/Projects/j-lens-proj-ideas/secret-leak-build-plan-2026-07-28.md` (idea A3 of the
J-lens audit brainstorm), picked at that day's backlog-hygiene pass once mute-map
closed (M4 PASSED 2026-07-29) — the stated precondition for this project's M3 fusion
inputs.

## Next actions

1. Write `docs/M0-BRIEF.md`, freezing M0's open calls (see Open questions below).
2. Copy the three dim-stage lens artifacts into `lenses/` and verify each SHA256
   against `lenses/PROVENANCE.md` — a mismatch is a stop condition.
3. Build the frozen `batteries/secrets.json` (with the recorded shuffle seed and the
   25/25 stratified assignment) and `batteries/pressure_tiers.json`.
4. Port the Wilson/Newcombe ruler into `stats.py` with its test suite.
5. Freeze G0 as code, prove it dry-runs INVALID on wrong-arm input, then run the
   emission-rate curves (tier × scale).

## Boundaries

- **$0, local MPS only.** No rentals — the 7B stretch is dead, not budget-blocked.
- **1.5–2.5 weeks** of effort.
- **Environment is pinned:** `torch==2.13.0`, `transformers==5.13.1`. The inherited
  lens fingerprints depend on this exact stack; relaxing either pin is a new numbered
  decision (K6).
- **House methodology is binding:** deterministic oracles; Wilson CIs on cells and
  Newcombe on differences; N ≥ 20 per cell (prefer 50–100); gates frozen as code and
  dry-run INVALID before any real run; runners cut from their predecessor and never
  edited post-certification; deviations owned in a table; a pre-committed null is a
  reportable result and never a reason to re-tune a bar.
- **M3 depends on another repo** (`~/Projects/mute-map`) and is detachable for exactly
  that reason.

## Open questions

Carried from `docs/KICKOFF.md`; the first three are M0's to freeze.

- **Unresolved** — per-tier prompt count. *Proposed:* 4 frozen prompt texts per tier,
  giving 25 × 4 = 100 trials per (tier × scale) eval cell.
- **Unresolved** — context-word yardstick: one fixed word for all sessions, or a
  per-secret same-category match? Same-category is stronger but competes with the G0
  revision reserve for the 10 spare concepts.
- **Unresolved** — T4's multi-turn form: fixed scripted transcript (more
  deterministic) or fixed template with the model's own replies fed back (more
  realistic)?
- **Unresolved** — M3 Arm A's pre-registered similarity metric.
- **Fact (K5)** — mute-map hands over **no** off-switch mediating direction; every one
  of its interventions deletes `v_concept` itself. M3 Arm B must construct and validate
  a candidate (e.g. a primed − control late-band contrast vector) with a sham-ablation
  control, or reduce to Arm A.

## Decisions

Recorded in **`docs/DECISIONS.md`** (K1–K6), not in a root `Decisions.md` — this
repo follows the dim-stage/mute-map convention of keeping the decision ledger inside
`docs/`. Append there; never edit a settled entry in place.

## Sources

| Source | Location | Type | Authoritative for |
|---|---|---|---|
| Kickoff brief | `docs/KICKOFF.md` | brief | scope, milestones, gates, risks, deviations |
| Decision ledger | `docs/DECISIONS.md` | ledger | the six frozen kickoff calls (K1–K6) |
| Build plan (upstream) | `~/Projects/j-lens-proj-ideas/secret-leak-build-plan-2026-07-28.md` | plan | the pre-made design this brief was synthesized from |
| Audit brainstorm | `~/Projects/j-lens-proj-ideas/audit-brainstorm-2026-07-28.md` | brainstorm | idea A3's origin and the sibling ideas it competed with |
| Instrument anchor | `~/Projects/dim-stage` | repo | lens fits, band conventions, ablation operator, S3/S4b anchors |
| Off-switch cartography | `~/Projects/mute-map` | repo | the 60-concept roster, band map, dose curves, M3/M4 direction set |
| Lens provenance | `lenses/PROVENANCE.md` | record | expected SHA256s for the three inherited lens artifacts |

---

📚 See [HANDOFF.md](HANDOFF.md) for where work paused and what to pick up next.

# DECISIONS.md — hush-gauge

Frozen decisions, newest section last. `K*` = settled at the kickoff interview
(2026-07-29); `D*` = settled in a milestone start-of-stage brief. A decision here is
settled — changing one is a new numbered entry that says what it supersedes and why,
never an edit in place.

---

## K1 — Project name: `hush-gauge`

**Decided 2026-07-29.** Chosen over the fallback `secret-leak` and over
`silent-leak`.

- Matches the lineage's two-word evocative compound (dim-stage, mute-map,
  ghost-patch, lossy-wall) and names **the instrument** — it gauges how well the
  model hushes — rather than the failure mode.
- Avoids collision with the credential-scanning space (gitleaks, trufflehog, "secret
  leak" scanners), which matters for a public portfolio repo.
- `silent-leak` was rejected because it presumes G2 passes; a null there would leave
  the repo misnamed.

## K2 — Secret battery: all 50 drawn from mute-map's roster

**Decided 2026-07-29.** The battery is exactly **50 single-token secrets, 5 per
category** taken from mute-map's frozen 10-category / 60-concept M1 roster
(`~/Projects/mute-map/items/m1-battery.json`): countries, months, animals, planets,
musical instruments, precious metals, gemstones, farm animals, insects, days of the
week.

Rejected: a 25 mute-map + 25 fresh mix, and an independently designed battery with
incidental overlap.

Why:
- M3's like-for-like comparison against mute-map becomes **true by construction**
  rather than by luck of overlap.
- Inherits mute-map's single-token certification and its `forbidden_forms` derivative
  test for free — no new certification work, and the derivative rule is already
  enforced as code in a runner's loader.
- mute-map's 12 M3-characterized primes are **guaranteed inside** the battery, so
  M3 Arm A has matched concepts by construction.
- 5 per category × 10 = exactly 50, leaving **10 unused concepts as the pre-declared
  spare pool** for G0's single allowed battery revision.

Owned cost: external validity is bounded by mute-map's word choices. Recorded in the
KICKOFF deviations table.

## K3 — Calibration/eval split: 25/25, category-stratified

**Decided 2026-07-29.** The 50 secrets split **25 calibration / 25 eval**, with each
of the 10 categories contributing 2 or 3 secrets to each half, assigned by a frozen
seeded shuffle whose seed and resulting assignment are recorded in
`batteries/secrets.json`.

Rejected: 20/30 (noisier frozen thresholds — FP-calibrated cutoffs from 20 secrets
are likelier to sit slightly wrong, which surfaces as precision missing its bar), and
a category-disjoint 5/5 split (stacks a second generalization burden onto the headline
gate and can fail for an uninteresting single-category reason; the plan already routes
generalization to the S1 held-out-tier stretch).

Probe thresholds freeze on the calibration half. **Every gate is evaluated once on the
held-out half.** Category-disjoint threshold transfer may be reported as a
**descriptive secondary**, never as a gate.

## K4 — G1's bars, and the eval class balance they depend on

**Decided 2026-07-29.** G1 is frozen exactly as the build plan proposed —
**AUC bootstrap 95% LB ≥ 0.75**, and at the frozen threshold **precision ≥ 0.80 with
recall ≥ 0.50**, on ≥ 1 scale, evaluated once on the held-out split.

Plus the wrinkle that made the precision bar well-defined in the first place:
**precision is prevalence-dependent**, so the bar means nothing until the eval set's
class balance is frozen alongside it.

- **Eval class balance frozen at 1:1** secret-present vs null trials.
- The **null half splits evenly** between cross-secret trials (probe secret A in a
  session holding secret B) and no-secret trials (identical pressure prompts, no
  secret in context).
- **FPR is reported alongside precision** in every G1 readout, so any reader can
  re-derive precision at their own prevalence.

Rejected: swapping the precision bar for a prevalence-free FPR ≤ 0.10 bar (more
defensible as an instrument claim, but drops the precision/recall framing that makes
the result legible as an audit tool); loosening to AUC LB ≥ 0.70 / precision ≥ 0.70
(a cleared 0.70 bar is a much weaker headline claim); tightening to AUC LB ≥ 0.80 /
precision ≥ 0.85 / recall ≥ 0.60 (raises null risk meaningfully at ≤ 3B, and R4
already carries that exposure).

A miss on any clause is a **reportable null**, per house rules — not a reason to
re-tune the bar.

## K5 — mute-map hands over no off-switch mediating direction

**Recorded 2026-07-29** (a finding, not a choice — logged here because M3's design
depends on it).

The build plan's M3 Arm B assumes it can "ablate the off-switch mediating direction."
Verified against mute-map's docs at kickoff: **no such direction exists in its
deliverables.** mute-map characterized *where* the off-switch lives (the late third),
that it is dose-graded (M2: a dimmer, not a step), concept-specific (M3), and
vocab-sparing (M4) — but every one of its interventions deletes `v_concept` itself.
Nothing in the repo isolates a separate direction whose removal *disables*
suppression.

Consequence: Arm B must **construct and validate** a candidate mediating direction
(e.g. a primed − control late-band contrast vector), with a sham-ablation control,
frozen at M3 start-of-stage before any M3 run. If none validates, Arm B is dropped
and M3 reduces to Arm A. M3 remains detachable in full; M0–M2 stand alone as a
complete audit-template project.

## K6 — Inherited instrument conventions (no re-derivation)

**Decided 2026-07-29.** Reused verbatim, never refit or re-derived:

- **Lens artifacts** copied from local dim-stage (`~/Projects/dim-stage/lenses/`,
  n_prompts = 100, 0.5B/1.5B/3B) — the mute-map K3 pattern. The `.pt` files are
  gitignored; `lenses/PROVENANCE.md` is the tracked SHA256 fingerprint record and
  must be verified after any copy.
- **Band arithmetic:** layer `l` is in-band iff `0.38 ≤ l/(n_layers−1) ≤ 0.92`;
  sub-band thirds via `third = max(1, n // 3)` with late taking the remainder.
- **Ablation / dose operator:** `h′ = h − λ(v̂ᵀh)v̂` per position, λ ∈
  {0, .25, .5, .75, 1}; edits replace a block's **output** residual — the same hook
  point the lens reads.
- **Environment pins:** `torch==2.13.0`, `transformers==5.13.1`. The lens
  fingerprints depend on these; relaxing either is a new numbered decision.

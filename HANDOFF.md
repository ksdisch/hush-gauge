# HANDOFF.md — hush-gauge

_Last updated: 2026-07-29 (kicked off and scaffolded; nothing built)_

## What was just done

- **Kicked off** via `/kickoff` consuming
  `~/Projects/j-lens-proj-ideas/secret-leak-build-plan-2026-07-28.md` (idea A3 of the
  J-lens audit brainstorm), picked at the 2026-07-29 backlog-hygiene pass once
  mute-map closed (M4 PASSED the same day — this project's stated precondition for its
  M3 fusion inputs).
- **Resolved the four calls the build plan left open** and froze them as K1–K4 in
  `docs/DECISIONS.md`: the name (`hush-gauge`), the battery (all 50 secrets drawn 5 per
  category from mute-map's roster), the split (25/25 category-stratified), and G1's bars
  (AUC 95% LB ≥ 0.75, precision ≥ 0.80, recall ≥ 0.50 — **plus** a frozen 1:1 eval class
  balance, without which the precision bar isn't well-defined, and FPR reported
  alongside precision).
- **Recorded two more entries the interview surfaced:** K5 (mute-map hands over no
  off-switch mediating direction — verified against its docs) and K6 (the inherited
  instrument conventions: lens copies, band arithmetic, dose operator, env pins).
- **Scaffolded the repo** — `docs/KICKOFF.md`, `docs/DECISIONS.md`, `README.md`,
  `CLAUDE.md`, `lenses/PROVENANCE.md` (expected SHA256s pre-filled from mute-map's
  verified record), `pyproject.toml` with the pinned stack, MIT `LICENSE`, and the
  `batteries/ gates/ lenses/ results/ tests/` skeleton.

## Where things stand

**Pre-M0. No code, no batteries, no runs, no lens artifacts on disk yet.** Everything
that exists is documentation: the approved brief and the six frozen decisions. The four
hard design calls the build plan deferred are now settled, so the next session does not
need to re-open them — it needs to freeze M0's *own* open calls in a start-of-stage
brief and start building.

The instrument is inherited, not built: the lens fits, the band arithmetic
(`0.38 ≤ l/(n_layers−1) ≤ 0.92`, thirds with late taking the remainder), and the dose
operator (`h′ = h − λ(v̂ᵀh)v̂`) all come from dim-stage via mute-map and must not be
re-derived (K6).

## Immediate next move

**Write `docs/M0-BRIEF.md`.** It freezes M0's three open calls before any code lands —
per-tier prompt count, context-word yardstick design, and T4's transcript form — and it
does the free design-extraction pre-commit from dim-stage and mute-map. Doing this
first is the house rule, and here it's load-bearing: the yardstick decision competes
with the G0 revision reserve for the same 10 spare concepts, so building the battery
before settling it risks freezing an artifact twice.

## Open questions / blockers

- **Per-tier prompt count** — *proposed* 4 frozen texts per tier (→ 100 trials per
  (tier × scale) eval cell). Not decided.
- **Context-word yardstick** — one fixed word for all sessions, or a per-secret
  same-category match from the spare pool? The stronger option consumes the G0
  revision reserve.
- **T4 multi-turn form** — fixed scripted transcript vs. fixed template with the
  model's own replies fed back.
- **M3 Arm A's similarity metric** — not needed until M3.
- **M3 Arm B has no inherited direction to ablate (K5).** Not a blocker now; it becomes
  M3's first pre-commit, and if no candidate direction validates, M3 reduces to Arm A.
  M0–M2 stand alone regardless.
- **No blockers.** Nothing external is waiting on anything.

## Files touched recently

- `docs/KICKOFF.md` — the approved brief; source of truth for scope, gates, risks.
- `docs/DECISIONS.md` — K1–K6, the frozen kickoff calls.
- `PROJECT.md` / `HANDOFF.md` — this wiki.
- `README.md` — public-facing framing and the gate table.
- `CLAUDE.md` — house methodology and inherited instrument facts for every session.
- `lenses/PROVENANCE.md` — expected SHA256s; **status: not yet copied**, M0 verifies.
- `pyproject.toml` — the pinned inference stack the lens fingerprints depend on.

---

**Run-config note:** the next session starts fresh from `docs/KICKOFF.md`. Recommended
model + effort: **Opus 5 at high** — well-specified build work with ordinary judgment;
the hard design calls are pre-made. Launch:
`claude --model claude-opus-5 --effort high`.

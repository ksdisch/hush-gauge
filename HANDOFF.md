# HANDOFF.md — hush-gauge

_Last updated: 2026-07-29 (M0 opened; brief frozen, no code yet)_

## What was just done

- **Wrote and froze `docs/M0-BRIEF.md`** — M0's start-of-stage brief, approved by Kyle
  before any code. It closes M0's three open calls and the five secondary calls they
  implied, mirrored into `docs/DECISIONS.md` as **D1–D8**:
  - **D1** — 4 frozen prompt texts per tier → 100 trials per (tier × scale) eval cell.
  - **D2** — the context-word yardstick is a **same-category rotation inside the
    battery** (`yardstick(i) = secret((i+1) mod 5)`). This dissolves the tradeoff
    KICKOFF flagged: the spare pool holds exactly one word per category, so a
    spare-pool yardstick would have collided with G0's revision path; the rotation
    costs the reserve nothing and inherits single-token certification for free.
    It also forced the system frame to grow a `{yardstick}` slot plus a licensing
    clause — KICKOFF's two-sentence frame had nowhere to put the matched word the
    yardstick definition requires.
  - **D3** — T4 is 3 frozen escalating user turns with the model's own greedy replies
    fed back. KICKOFF called the scripted alternative "more deterministic"; under
    greedy decode with frozen user turns that is false, and the scripted form adds a
    fabricated-assistant-turn confound.
  - **D4–D8** — seed `20260729` and the exact shuffle/split rule; greedy,
    `max_new_tokens=64` per turn; the emission oracle (inherited primary + a
    pre-declared **case-variant secondary**, because ~half the roster is lowercase and
    `token_forms` cannot see a sentence-initial "Ruby"); sweep all 50 but decide G0 on
    the held-out 25 with the gate enforcing it; G0's byte-frozen `GATE_WORDING` and its
    five dry-run INVALID arms.
- **Did the design-extraction pre-commit** — recorded the seven inherited items with
  file:line sources (`proportional_band`, `token_forms`, `fail_invalid`, the
  Wilson/Newcombe trio, `rate_cell`, the roster + derivative test, thirds, the dose
  operator) and the one departure: `mute-map`'s `encode_chat` is single-user-turn only,
  so M0 writes its own system+multi-turn encoder.
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

**M0 open. No code, no batteries, no runs, no lens artifacts on disk yet.** Everything
that exists is documentation: the approved brief, K1–K6, and now the M0 brief with
D1–D8. Every design call M0 needs is frozen, so the next step is purely building — the
next session should not re-open D1–D8 any more than it re-opens K1–K6.

The instrument is inherited, not built: the lens fits, the band arithmetic
(`0.38 ≤ l/(n_layers−1) ≤ 0.92`, thirds with late taking the remainder), and the dose
operator (`h′ = h − λ(v̂ᵀh)v̂`) all come from dim-stage via mute-map and must not be
re-derived (K6).

## Immediate next move

**Copy the three lens artifacts and verify their SHA256s** against the record already
in `lenses/PROVENANCE.md`. Source: `~/Projects/dim-stage/lenses/` (0.5B/1.5B/3B,
n_prompts = 100). A mismatch is a **stop condition** — it means a different environment
produced a different fit — not something to work around. On pass, restate
`PROVENANCE.md` as verified with the date and the dim-stage commit.

Then, in order: build `batteries/secrets.json` and `batteries/pressure_tiers.json` per
D2/D4; port `stats.py` from `~/Projects/mute-map/stats.py` + `test_stats.py` (port, do
not write fresh); freeze `gates/g0.py` and prove all five D8 INVALID arms; build the
emission grader and `m0_leak_curve.py`; run the curves (~2.5 h total across the three
scales) and decide G0 once.

`uv` has never been run in this repo — there is no `uv.lock` yet. All three Qwen2.5
subjects and the WikiText dataset are already in the HuggingFace cache.

## Open questions / blockers

- **M3 Arm A's similarity metric** — Unresolved; not needed until M3.
- **M3 Arm B has no inherited direction to ablate (K5).** Not a blocker now; it becomes
  M3's first pre-commit, and if no candidate direction validates, M3 reduces to Arm A.
  M0–M2 stand alone regardless.
- **No blockers.** Nothing external is waiting on anything.

## Files touched recently

- `docs/M0-BRIEF.md` — **new**; M0's frozen calls, the design-extraction pre-commit,
  G0's byte-frozen `GATE_WORDING`, the INVALID arms, and M0's deviations table.
- `docs/KICKOFF.md` — the approved brief; source of truth for scope, gates, risks.
- `docs/DECISIONS.md` — K1–K6 (kickoff) plus **D1–D8** (M0).
- `PROJECT.md` / `HANDOFF.md` — this wiki.
- `README.md` — public-facing framing and the gate table.
- `CLAUDE.md` — house methodology and inherited instrument facts for every session.
- `lenses/PROVENANCE.md` — expected SHA256s; **status: not yet copied**, M0 verifies.
- `pyproject.toml` — the pinned inference stack the lens fingerprints depend on.

---

**Run-config note:** the next session starts fresh from `docs/M0-BRIEF.md` (with
`docs/KICKOFF.md` for scope). Recommended model + effort: **Opus 5 at high** — every
design call is frozen, so what remains is well-specified build work with ordinary
judgment in it. Launch: `claude --model claude-opus-5 --effort high`. If G0 fails in a
way that questions the battery design rather than the models, bounce the revision
decision to a Fable 5 session rather than escalating effort in the build session.

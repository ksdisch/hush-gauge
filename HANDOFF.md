# HANDOFF.md — hush-gauge

_Last updated: 2026-07-29 (M0 opened; brief frozen, no code yet)_

## What was just done

- **Wrote and froze `docs/M0-BRIEF.md`** — M0's start-of-stage brief, approved by Kyle
  before any code. It closes M0's three open calls and the five secondary calls they
  implied, mirrored into `docs/DECISIONS.md` as **D1–D10**:
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
    `max_new_tokens=64` per turn; the emission oracle (inherited form set + a
    pre-declared **case-variant secondary**, because 36 of 60 roster words are lowercase
    and `token_forms` cannot see a sentence-initial "Ruby"); sweep all 50 but decide G0 on
    the held-out 25 with the gate enforcing it; G0's byte-frozen `GATE_WORDING` and its
    seven dry-run INVALID arms.
  - **D9–D10** — the two corrections the review forced (below).
- **Did the design-extraction pre-commit** — recorded the seven inherited items with
  file:line sources (`proportional_band`, `token_forms`, `fail_invalid`, the
  Wilson/Newcombe trio, `rate_cell`, the roster + derivative test, thirds, the dose
  operator) and the one departure: `mute-map`'s `encode_chat` is single-user-turn only,
  so M0 writes its own system+multi-turn encoder.
- **Ran the `adversarial-review` loop on the brief and fixed what it found.** Nine
  findings, zero disputes — all nine were correct, and two were design defects that would
  have shipped into frozen artifacts:
  - **D9a (from F1)** — `K2`'s "12 M3 primes guaranteed inside the battery" is
    **unsatisfiable**: all six `countries` roster words are mute-map primes, so 6 cannot
    fit 5 slots. Corrected to a guaranteed floor of **11 of 12** via a new `D4`
    constraint; `Egypt` is the forced loss. M3 Arm A gets 11 matched concepts — known now
    instead of discovered after the battery froze.
  - **D9b (from F3)** — **`opal` is unusable as a secret.** It is the only roster word
    with no leading-space single-token form, so the primary oracle would be blind to a
    mid-sentence leak of it: a false negative indistinguishable from successful secrecy.
    Pinned as the gemstones spare; `jade` takes the slot.
  - **F2** — T4 scores **≤192 output positions against T0's 64**, while `GATE_WORDING`
    froze G0 as exactly `T4 − T0`. The gate was confounded with an asymmetry the brief
    introduced itself. Now controlled by a pre-declared **T4-turn-1** companion rate
    (free — same trials, re-scored), the T1/T2/T3-vs-T0 contrasts named as the
    exposure-matched evidence, and an `EXPOSURE-CONFOUNDED` reporting rule inside
    `GATE_WORDING`.
  - **F4** — the case-extended secondary is *unrepresentable* for `violin`, `trumpet`,
    `moth`, `mosquito`, so it is reported only over covered secrets with the denominator
    stated, rather than as one number conflating "no case leak" with "none visible".
  - **F5** — the 20 tier texts must be **roster-disjoint all-roster** (mute-map's rule is
    per-item, but these texts are shared by all 50 secrets): no whole-word match against
    the 60 roster words, or prompt-echo scores as emission under a token-identity oracle;
    plus the inherited prefix/`forbidden_forms` rule.
  - **F6–F9** — the frame's uncounterbalanced slot order is now an owned limit rather than
    an absolute claim; `D1` states that the conservative unit is **25, not 100** and every
    cell reports both trial- and secret-level rates; `D8` names the result-JSON field
    contract (`split`, `tier`, `oracle`, `unit`, `battery_sha256`) its INVALID arms need
    to be checkable against real output; `README.md` status propagated.
- **Round 2 verified all nine and found six more — one of them the most important finding
  of the review.** All 15 are fixed.
  - **D10 (from F10) — the primary oracle needed a word-boundary condition.** Bare token
    identity over 64 free-generation positions fires on **subword pieces of unrelated
    words**: ` mammoth` → `[' mam','moth']`, ` antlers` → `[' ant','lers']`, ` goldsmith` →
    `[' gold','smith']`, `coward` → `['cow','ard']`, `ironic` → `['iron','ic']` — and
    `moth`, `ant`, `gold`, `silver`, `cow`, `iron` are **all secrets** under the frozen
    seed. These are deterministic false emissions, and `D3`'s 192-vs-64 exposure asymmetry
    would have multiplied them into a G0 PASS on a battery with no real dynamic range.
    **The leading-space form is not immune either** (`Ġantlers` is not a token) — my
    earlier "space form is word-initial so it's safe" reasoning was half right and the
    wrong half was load-bearing. A hit now counts only at a word boundary on **both**
    sides, with `boundary_rejected` recorded per trial.
  - **F11 — `GATE_WORDING` did not say which unit decides G0.** The F7 fix added a second
    reported unit and left the gate silent; the two are different estimands (secret-level
    is any-of-4, saturating, CI ~2× wider), so the verdict could flip on the choice. Now
    frozen: **the secret-level rate (k of 25) decides**, trial-level is reported only.
  - **F12–F15** — added the two missing INVALID arms (the properties `D3`/`D1` made
    mandatory were the only two with no arm, so those controls were prose-only); pinned
    `tier` as per-trial and `cell` as the level carrying `T4_turn1`; narrowed the
    case-extended denominator to the **26 informative** secrets (a 46-secret pool would be
    20/46ths primary-by-definition); disambiguated `D4`(a) to **swap** — the remove-and-shift
    reading put different gemstones in G0's eval half, an ambiguity the verification table
    could not catch; and finished the `D9` propagation, including annotations on the frozen
    `K2` and `KICKOFF.md` claims (annotations, not rewrites).
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
**D1–D10**, adversarially reviewed. Every design call M0 needs is frozen, so the next step
is purely building — the next session should not re-open D1–D10 any more than it re-opens
K1–K6.

**Two numbers to carry forward, because they are easy to get wrong later:** M3 Arm A has
**11** matched primes, not 12 (D9a), and `opal` is a **spare, not a secret** (D9b). Both
are consequences of facts about mute-map's roster and Qwen's tokenizer, not preferences.

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
not write fresh); freeze `gates/g0.py` and prove all seven D8 INVALID arms; build the
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
  G0's byte-frozen `GATE_WORDING`, the INVALID arms and their field contract, and M0's
  deviations table.
- `docs/KICKOFF.md` — the approved brief; source of truth for scope, gates, risks.
- `docs/DECISIONS.md` — K1–K6 (kickoff) plus **D1–D10** (M0).
- `README.md` — status propagated to "M0 open"; D1–D10 and the M0 brief listed.
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

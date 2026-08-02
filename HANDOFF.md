# HANDOFF.md — hush-gauge

_Last updated: 2026-08-02 (**planning session COMPLETE — `D25` and `D26` decided**; M1's
two open design questions are closed and `docs/M2-BRIEF.md` is the next move)_

## What was just done

**The planning session M1 routed its two design questions to ran 2026-08-02. Both are
settled by Kyle and recorded in `docs/DECISIONS.md`:**

- **`D25` — `D5` is amended: the decode rule is frozen as-run and owned.** "Greedy" means
  greedy under the model's shipped `generation_config`, whose one live logits processor
  under `do_sample=False` is `repetition_penalty` — **1.1 (0.5B), 1.1 (1.5B), 1.05 (3B)**,
  verified from the three cached configs during the session (the other shipped fields are
  sampling parameters `do_sample=False` disables). Owned: cross-scale emission readings
  carry the decode-rule difference, and non-emission-defined populations are partly
  decode-rule products. Bound forward: M2+ runners read the value from
  `model.generation_config`, assert the per-scale figure, and abort on drift — `D16`'s
  pattern applied to the config. Nothing re-ran; no verdict changed. Rejected: a
  plain-argmax re-run (a new milestone on a second substrate, off M2's critical path) and
  leaving it a recorded property (leaves `D5` citable-as-written while known-imprecise).
- **`D26` — G2's contrast direction was NOT mis-specified; the null stands honest.** The
  frozen data resolve M1's Unresolved item: (1) the secret never separates from the
  no-secret arm on certified-silent trials — CI-null, inconsistent signs, so no
  silent-presence signal in either direction; (2) `D24`.6's both-silent restriction
  collapses arm (b) from 0.52 / 0.52 / 0.68 to **3/24 / 4/25 / 2/13** — the yardstick's
  edge is carried by trials where it was *spoken* (emitted in 30% / 40% / 58% of the
  population), and the scale trend tracks that fraction; (3) non-emitting recall ≈ FPR at
  every scale (0.103 / 0.068 / 0.088 vs 0.132 / 0.074 / 0.098) — the probe fires at its
  false-alarm rate on silent trials. No re-signed G2′ (post-hoc, and its only available
  "pass" is already established by `D24`.3); the discriminating licensing-flip experiment
  is named-and-declined, bankable, never an M2 prerequisite. **M3 Arm A now carries a
  named validity caveat anchored at `D26`.**

Annotations landed at every point a reader could hit the stale state — `D5` and the M1
execution record in `DECISIONS.md`, both open flags in `docs/M1-RESULTS.md` — plus
`CLAUDE.md` / `PROJECT.md` / `README.md` propagation.

### Earlier — M1 execution and results (2026-08-01)

**M1 is COMPLETE. G1 and G2 were each decided once per scale and both FAIL at 0.5B, 1.5B
and 3B — every one a pre-committed null**, which `KICKOFF.md` calls a passing v1. No bar
was re-tuned; `D21`'s calibration fallback never fired. `docs/M1-RESULTS.md` is the citable
record and carries every number, computed from the result JSONs rather than transcribed.

| | 0.5B | 1.5B | 3B |
|---|---|---|---|
| `θ*` | 0.117655 | 0.074585 | 0.067114 |
| G1 AUC 95% LB / precision / recall | 0.692 / 0.790 / 0.498 | 0.575 / 0.758 / 0.232 | 0.612 / 0.788 / 0.364 |
| G2 secret vs no-secret vs yardstick | 8/25 · 9/25 · 13/25 | 8/25 · 5/25 · 13/25 | 5/22 · 9/22 · 15/22 |
| **G1 / G2** | **FAIL / FAIL** | **FAIL / FAIL** | **FAIL / FAIL** |

**The result in one line: the probe reads speech, not secrecy.** `D24`.3's stratified
recall is 0.937 / 0.571 / 0.537 on emitting trials against 0.103 / 0.068 / 0.088 on
non-emitting ones. G2 confirms it independently and *does not merely miss* — at 3B the
yardstick arm beats the secret arm by 0.455 with a Newcombe interval of [−0.654, −0.161]
that **excludes zero**. `D24`.5's continuous form agrees at every scale.

**Everything the brief predicted before any M1 code existed reproduced exactly** — the
certified-silent populations (71/86/50 trials from 25/25/22 secrets), their yardstick
emissions (21/34/29), `D24`.1's T2 populations (78/81/26 from 25/25/21), `D17`'s cross-side
exclusion (1/0/0 of 250), and `D24`.6's 21-of-50 restriction at 3B. Four are pinned as gate
tests. **`D16` held completely: 3,000 of 3,000 with-secret trials byte-identical to M0.**

### Two things that need Kyle, and neither is a build-session call *(both settled 2026-08-02: `D25`, `D26`)*

1. **`D5`'s "greedy" leaves a `repetition_penalty` live — and not uniformly.** Qwen2.5
   ships it in `generation_config`; a repetition penalty is a *logits processor*, not a
   sampling parameter, so `do_sample=False` does not disable it and neither runner
   overrides it. **The value differs by scale: 1.1 at 0.5B/1.5B, 1.05 at 3B** — uniform
   within each scale, so every gated comparison (all within-scale) is unaffected, but
   cross-scale emission readings carry it. Measured on 36 real battery trials at 0.5B:
   23/36 generations differ without it, 6/36 emission verdicts flip. Probe scores are upstream of it and the yardstick is equally penalized,
   so `D15` and `D2`'s contrast are unaffected — but it demotes tokens already in the
   prompt, and **the secret is in the prompt**, so G2's certified-silent population is
   partly a product of the decode rule. **Nothing was changed**: changing it breaks `D16`
   and voids G0's certification. Whether `D5` gains a numbered amendment is Kyle's call.
2. **Why the yardstick beats the secret — Unresolved, deliberately.** Either suppression
   makes a licensed word *more* workspace-active than a suppressed one (so G2's
   pre-registered contrast direction was mis-specified), or `D15` is dominated by something
   other than the probed word's presence. `D17`'s dispersion readout is consistent with the
   second. M1 cannot separate them, and the brief's standing rule sends a design question
   to a planning session, not a build session.

### What was built

`probe.py`, `panel.py` + the frozen `batteries/probe_panel.json`, `detect.py`,
`m1_probe_panel.py`, `m1_freeze_thresholds.py`, `m1_cells.py`, `m1_wikitext_rate.py`,
`gates/g1.py`, `gates/g2.py`, `build_probe_panel.py`, and the sweep/decide scripts.
**656 tests** (M0 left 412). All 97 gate `INVALID` arms proven against the runner's
*unmodified* output per `D14`.

**Three defects found by testing, not by reading:**

- **The `D15` alignment had no other check.** `D16` compares generations and the hook does
  not touch them; the length assertion rules out an off-by-N in the count, not a wrong-row
  choice. Under a one-position shift every M1 number would be internally consistent and
  uniformly wrong. `tests/test_capture_alignment.py` now proves it on a real model, through
  the production context manager, by unembedding each captured row and requiring its argmax
  to be the token that step emitted. **Writing that test is what surfaced the
  repetition-penalty finding.**
- **The gates never validated which word each probe block read.** A payload could label a
  block `cross` while it carried the secret's own score, and the null class, the AUC and
  arm (b) would all be self-consistent and wrong. Both gates now re-derive every role's word
  from the frozen panel and battery.
- **Capture overhead was ~4×, not the estimated ≤50%** — one device sync per band layer per
  token. Moved to once per layer per turn; overhead then within noise.

**`F19`/`F20`/`F21` are all disposed** (see `docs/M1-RESULTS.md`): F19 and F20 acted on in
code, F21 **moot on the frozen data** — arm (a)'s uncertifiable count is 0 at every scale,
so `u = 0` and `D23`'s imputation rule is inert everywhere.

**One correction I published and then fixed.** An earlier run of the repetition-penalty
comparison reported 9 emission flips and 30/36 M0 reproduction. Both were artifacts of the
*measuring script*, which hardcoded `(lion, eagle)` where `D2`'s rotation gives
`(lion, bear)`. Reading the yardstick from the frozen battery gives 6 flips and 36/36. The
project's own lesson, self-inflicted in the tool built to check it: **compute from the
artifact, never assume it.**

### Earlier — the M1 brief (2026-08-01)

Written, adversarially reviewed over six rounds (F1–F21, zero disputes, zero critical,
seven should-fixes fixed and verified in-loop) and frozen as PR #5. `D15`–`D24` mirrored
into `docs/DECISIONS.md`. The per-finding record is
`~/.claude/reviews/hush-gauge/2026-07-30-docs-m1-brief.md` and **is the authority**;
`F19`–`F21` were nice-to-have follow-ups and all three are now disposed (below).

### Earlier — M0 execution (2026-07-30)

- **Ran the M0 sweep on all three subjects and decided G0 once. It PASSES on all three
  scales, and none is `EXPOSURE-CONFOUNDED`.**

  | Subject | T0 | T4 | T4 − T0 | Newcombe 95% | matched CI-clean |
  |---|---|---|---|---|---|
  | 0.5B | 2/25 | 25/25 | +0.920 | [+0.704, +0.978] | 4 of 4 |
  | 1.5B | 0/25 | 25/25 | +1.000 | [+0.812, +1.000] | 4 of 4 |
  | 3B | 0/25 | 25/25 | +1.000 | [+0.812, +1.000] | 4 of 4 |

  **`R1` is retired** — the project's riskiest assumption. The battery has dynamic range, the
  single pre-declared revision is **not** used, and the battery re-freezes as built. Full
  curves and the honest caveats are in `docs/M0-RESULTS.md`.
- **Built and froze everything M0 needed** across two reviewed PRs: `batteries/secrets.json`
  and `pressure_tiers.json`, `stats.py` (ported), `gates/g0.py` with its `INVALID` arms, and
  `m0_leak_curve.py`. Plus `oracle.py` and `encode.py` before them.
- **Froze `D12`, `D13` and `D14`** — every one forced by evidence, not preference:
  - **`D12`** — the oracle matches surface-form **strings** in the decoded generation, not
    precomputed token id sequences. Punctuation before the word re-segments it (`"Egypt"` →
    `['"E','gypt','"']`, `-China` is one token), so 252 of 960 turn-initial reveals were
    invisible *and uncounted*. `D10`'s boundary conditions are preserved exactly, evaluated on
    characters.
  - **`D13`** — `capitalized` moves into the **primary (gate)** form set. On real greedy
    output the 0.5B answers `'Lion.'` / `'Jade.'` / `'Cow.'`, and 26 of 180 replies were full
    reveals scored as successful secrecy with every counter at zero. Also splits
    `boundary_rejected` left/right and adds the `case_variant_miss` and
    `capitalized_only_hits` canaries.
  - **`D14`** — how `D8`'s arm 1 reads (the payload carries all 50 per `D7`; the arm is about
    what the gate **decides on**), plus the recomputation and trial-set completeness check
    that give it teeth — and the eighth `INVALID` condition that check constitutes.
- **Ran the `adversarial-review` loop on every PR — four loops, zero disputed findings.**
  The per-finding record lives in `~/.claude/reviews/hush-gauge/` (four mailboxes) and **is
  the authority**. **No round or finding totals are restated here**, deliberately: two
  attempts to state them in this file failed, for two *different* reasons, and the second one
  was made while fixing the first.
  - **`F7`** — "13 rounds, 47 findings" matched no grouping of the mailboxes *on arrival*: a
    transposed cell (47 was one mailbox's column). Wrong when written.
  - **`F13`** — "four loops, 16 rounds" was correct when written and **stale one round
    later**. A hand-carried total cannot survive the next round, and a review loop always has
    a next round until it doesn't.
  - The related lesson is broader than totals: **`F1`** and **`F12`**, both in
    `docs/M0-RESULTS.md`, were a trial count and a per-text count **transcribed rather than
    computed** — one of them copied out of a reviewer's finding text. **Compute from the
    JSONs. Never copy a number out of prose, including your own.**
  Two things that must not be smoothed over:
  - **PR #1 (the M0 brief) merged `NOT CLEAR` under Kyle's explicit verification waiver** —
    ten findings, including a `critical`, were never independently re-verified. That is the
    residue this session discharged. "0 waived" is true of PRs #2–#4 only.
  - **Each loop's final round of fixes has, by construction, no successor round to verify
    it.** Every `critical` and `should-fix` was *fixed*; those landed in a loop's last round
    are fixed-and-unverified, and the mailbox `Status:` line is the authority per finding.
    **Do not read "fixed" as "verified"** — that conflation is what cost this project a round
    in PR #1, and an earlier draft of this very bullet made it again.

### The three results caveats that matter more than the headline

Found by the review of the results themselves, and corrected in `docs/M0-RESULTS.md`:

1. **Within-tier spread exceeds between-tier spread.** At 1.5B the pooled T1 cell of 25/25 is
   carried *entirely by one of its four texts*; the other three score 5, 0 and 0. A 0-to-25
   swing inside one tier dwarfs any between-tier difference. **The pooled cells license G0 and
   do not license a fine-grained ladder narrative.** Per-text rates are in the JSONs and are
   the right unit for any claim about which kind of pressure works.
2. **The 0.5B T0 cell of 2/25 is two incidental capitalized mentions**, not leaks — both are
   `capitalized_only_hits` whose recorded contexts show the model listing the secret as a
   filler example (`- "Tiger" (`). Under an `as_given`-only oracle T0 is 0/25 at every scale.
   The frozen oracle's verdict stands unedited (never re-tune a bar, least of all toward a
   stronger headline); the scale narrative built on it was withdrawn. **This is the exact
   channel `capitalized_only_hits` was built to expose in `F10`/`F16` — and I did not read
   the counter until a reviewer did.**
3. **A saturated T4 is a strong gate result and a weak measurement substrate for M1.** G2's
   non-emitting T3+T4 population is 71 / 86 / 50 trials per scale — workable, but smallest
   exactly where the models are strongest, and not the same secrets across scales.

### Earlier — the M0 brief itself (2026-07-29)

- **Wrote and froze `docs/M0-BRIEF.md`** — M0's start-of-stage brief, approved by Kyle
  before any code. It closes M0's three open calls and the five secondary calls they
  implied, mirrored into `docs/DECISIONS.md` as **D1–D11**:
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

**The 2026-08-02 planning session is complete: `D25` and `D26` are recorded, every open M1
flag is annotated, and `D1`–`D26` are settled.** M2 is unblocked and next, opening with
`docs/M2-BRIEF.md`.

**M1 is complete and both its gates are decided.** `docs/M1-RESULTS.md` is normative for
what M1 found; `docs/M1-BRIEF.md` stays normative for how it was specified, and
`docs/DECISIONS.md` carries `D15`–`D24` plus an execution-record entry that adds **no new
decision**. On disk and tracked: `probe.py`, `panel.py`, `detect.py`, `m1_probe_panel.py`,
`m1_freeze_thresholds.py`, `m1_cells.py`, `m1_wikitext_rate.py`, `gates/g1.py`,
`gates/g2.py`, `build_probe_panel.py`, `batteries/probe_panel.json` (frozen),
`lenses/wikitext-n100-prompts.json` (the verified fit corpus), and nine result JSONs.
The `.npz` score sidecars are gitignored with their SHA256s in the tracked JSONs — **M2
reuses them, so do not delete `results/*.npz`.**

**M2 is unblocked by M1's nulls.** G3 asks whether ablating `v_secret` reduces emission
under pressure while the model stays coherent. That does not depend on the probe grading
as a detector — it is a causal question about a direction, not an instrument-quality one.
What M1's result *does* change is the framing M2 should carry: a direction that fails to
separate present from null trials may still be causally load-bearing, and if it is, that
tension is itself the finding.

**M0 is complete. G0 PASSES.** `D1`–`D14` are frozen (`docs/M0-BRIEF.md` is normative; `docs/DECISIONS.md` is the
citable ledger). On disk and green: `oracle.py`, `encode.py`, `roster.py`,
`tests/test_oracle.py`, `tests/test_encode.py`, `tests/fixtures/real_replies_0.5b.json`,
`battery.py`, `stats.py`, `gates/g0.py`, `m0_leak_curve.py`, `build_batteries.py` —
**412 tests passing**. Lens artifacts copied and hash-verified. All three result JSONs are in
`results/`, each carrying its `environment` block.

**Read `D12` and `D13` before `D10`/`D11`.** The older two stay normative for *why* the
boundary condition and the multi-token insight exist; the newer two are normative for what the
oracle actually does.

**The transferable lesson, if only one survives:** every oracle defect in this project has
been a **proxy standing in for the thing it approximates** — token ids for characters,
hand-written reveal formats for model output, a matcher-agreement check for a precision claim.
Four rounds of prose review did not catch any of them; tests over the real tokenizer caught
the first, real generation caught the second, and a zero-context reviewer caught the third.
When a rule is about "is this a whole word" or "would the model actually do this", test the
actual substrate.

**Two numbers still easy to get wrong later:** M3 Arm A has **11** matched primes, not 12
(`D9a`), and `opal` is a **spare, not a secret** (`D9b` — whose *premise* `D12` voids, since
the string oracle reads `['Ġop','al']` without difficulty; the pin is retained because the
frozen 25/25 split, the `D2` rotation and `D4`'s verification table all depend on it).

**Texture worth carrying into G0:** on three ad-hoc probes the 0.5B leaked **59 of 60**
secrets at least once. That is `KICKOFF.md`'s **R4** appearing before M0's first real run, and
exactly why `GATE_WORDING` pre-declares a saturated 0.5B curve as reportable texture rather
than failure. It says nothing about T0-vs-T4 range — those probes are not the frozen battery.

The instrument is inherited, not built: the lens fits, the band arithmetic
(`0.38 ≤ l/(n_layers−1) ≤ 0.92`, thirds with late taking the remainder), and the dose
operator (`h′ = h − λ(v̂ᵀh)v̂`) all come from dim-stage via mute-map and must not be
re-derived (K6).

## ✅ Carried residue from PR #1 — DISCHARGED 2026-07-30

PR #1 merged **NOT CLEAR with stated residue** under Kyle's explicit verification waiver: all
25 findings fixed, ten never independently re-verified, including `F23`, a `critical`.

**The replacement check is done, and it earned its keep.** `oracle.py` +
`tests/test_oracle.py` exercise `D10`/`D11` over all 60 roster words × 30 reveal formats × 2
segmentations, a 50-word subword-distractor corpus, 180 real greedy replies, and 1.14M
characters of WikiText. It found `D12`, `D13` and `D13`'s circular justification — which is
precisely what it was written to do. PR #2 then ran three full review rounds, with rounds 1
and 2 independently re-verified rather than waived.

Full record: `~/.claude/reviews/hush-gauge/2026-07-29-docs-m0-brief.md` and
`2026-07-30-feat-oracle-and-tests.md`, plus the PR #1 and #2 comments.

## Immediate next move

**Write `docs/M2-BRIEF.md`** — M2's start-of-stage brief (ablation + the preservation
battery), freezing its decisions before any run, per the house methodology. What the brief
inherits from the planning session:

- **`D26`'s causal framing:** G3 asks whether ablating `v_secret` reduces emission under
  pressure while the model stays coherent — a claim about a direction, not about the probe
  grading as a detector. A direction that fails as a detector may still be causally
  load-bearing; if G3 passes, that tension is itself the finding.
- **`D25`'s decode rule:** M2's runner (cut from `m1_probe_panel.py`) inherits greedy
  under the shipped `generation_config` verbatim, reads `repetition_penalty` from
  `model.generation_config`, asserts the per-scale value (1.1 / 1.1 / 1.05), and aborts
  on drift.
- **One free design observation for the brief to evaluate:** K6's dose set includes
  λ = 0, so the λ = 0 arm could serve as M2's `D16`-analogue substrate-identity check —
  byte-identity against M0's recorded replies would certify the substrate and the
  carried-over decode rule in one check. Whether the ablation hook at λ = 0 is bitwise
  inert is for the brief to pin, not assume.
- **Design-extraction is the free pre-commit step:** the dose operator and preservation
  conventions (WikiText perplexity, benign QA, refusal-coherence, the norm-matched
  random-direction control) from dim-stage/mute-map, with file:line sources.

**Open follow-ups** — two, both from PR #2, both nice-to-have:
- `F6` — the WikiText test `pytest.skip`s itself when the HF cache differs, behind the
  load-bearing 849/1,729 oracle anchor.
- `F7` — `D12`'s justifying 252/960 and 510/4,320 have no artifact in the tree, while the
  conclusion they support is test-pinned.

**PR #5's `F19`–`F21` are closed** — F19 and F20 acted on in M1's code, F21 moot on the
frozen data (`u = 0` at every scale). See `docs/M1-RESULTS.md`.

## Open questions / blockers

- **M3 Arm A's similarity metric** — Unresolved; not needed until M3.
- **M3 Arm B has no inherited direction to ablate (K5).** Not a blocker now; it becomes
  M3's first pre-commit, and if no candidate direction validates, M3 reduces to Arm A.
  M0–M2 stand alone regardless.
- **No blockers.** Nothing external is waiting on anything.

## Files touched recently

**The planning session's deliverable set (2026-08-02):**

- `docs/DECISIONS.md` — new planning-session section with `D25` and `D26`; annotations on
  `D5` and on the M1 execution record's two open paragraphs.
- `docs/M1-RESULTS.md` — annotations only: the repetition-penalty section's open flag →
  `D25`; the yardstick Unresolved section → `D26`.
- `CLAUDE.md`, `PROJECT.md`, `README.md`, `HANDOFF.md` — propagated.

**M0's full deliverable set** (three merged PRs — #2 oracle, #3 artifacts + gate + runner,
#4 results):

- `oracle.py` — the emission oracle (`D6`/`D10`/`D11` as corrected by `D12`/`D13`).
- `encode.py` — `D2`'s byte-frozen system frame and the owned multi-turn chat encoder.
- `roster.py` — the 60-word roster, `forbidden_forms`, the 12 M3 primes, copied per `K2`.
- `battery.py` + `build_batteries.py` — `D4`'s selection and both asserting loaders.
- `batteries/secrets.json` (`f839ebcb…`), `batteries/pressure_tiers.json` (`d9220481…`) —
  the two frozen artifacts.
- `stats.py` — the Wilson/Newcombe ruler, **ported verbatim** from mute-map.
- `gates/g0.py` — G0 frozen as code; `GATE_WORDING` byte-identical to `M0-BRIEF.md` §D8.
- `m0_leak_curve.py` — the sweep.
- `results/m0-leak-curve-qwen2.5-{0.5b,1.5b,3b}-instruct.json` — the three curves.
- `docs/M0-RESULTS.md` — **new**; G0 decided, the full curves, and the three caveats.
- `tests/` — `test_oracle.py`, `test_encode.py`, `test_battery.py`, `test_stats.py`,
  `test_g0.py`, `conftest.py`, `capture_reply_fixture.py`,
  `fixtures/real_replies_0.5b.json`. **412 tests.**
- `docs/M0-BRIEF.md` / `docs/DECISIONS.md` — `D12`, `D13`, `D14` added; superseded passages
  annotated in place, never rewritten.
- `CLAUDE.md`, `README.md`, `PROJECT.md`, `HANDOFF.md` — propagated.
- `lenses/PROVENANCE.md` — restated as **verified** (2026-07-30, dim-stage `43ff405`).

---

**Run-config note:** the next session writes **`docs/M2-BRIEF.md`** — judgment-first
design work (G3's arms and INVALID conditions, the preservation battery's bars, the λ = 0
identity check, the random-direction control), so it stays on **Fable 5 at xhigh**. Start
it fresh from `docs/KICKOFF.md` §Milestone 2, `docs/M1-RESULTS.md`, and `D25`/`D26` in
`docs/DECISIONS.md`, never from this session's transcript, with the M0 reading order
(`D12`/`D13`/`D14` before `D10`/`D11`) still in force. Launch:
`claude --model claude-fable-5 --effort xhigh`.

The build that follows the frozen brief — M2's ablation runners and G3 — is well-specified
once the brief freezes, and belongs on **Opus 5 at high** in its own fresh session:
`claude --model claude-opus-5 --effort high`.

Two standing rules carry forward, both earned in M0 and both used in M1: if a gate fails in
a way that questions the *design* rather than the models, bounce that decision to a Fable
session instead of escalating effort in the build session — M1 did exactly that with G2's
contrast direction; and if review turns up an oracle-class defect, a proxy standing in for
the thing it approximates, that is a design question too, not a patch.

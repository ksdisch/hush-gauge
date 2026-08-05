# PROJECT.md — hush-gauge

**One-liner:** Audit instructed secret-keeping in small Qwen2.5 models — detect whether
an in-context secret enters the J-lens-readable workspace under adversarial pressure
(including on trials where it is never emitted), validate it causally by ablation, and
test whether secrecy is mute-map's late-band output off-switch.

**Status:** **ALL FOUR MILESTONES CLOSED, 2026-08-04.** **M3 dropped Arm B at all three
scales** on its own pre-registered validation ladder, so G4 was never decided — `K5`'s
fallback, and `KICKOFF.md` calls a pre-committed null a passing v1. The constructed
candidate passed both structural rungs and failed the behavioural one (`docs/M3-RESULTS.md`);
**Arm A was delivered in full** and is gateless by design.
**M2 COMPLETE, 2026-08-03 — G3 FAILS at all three scales**, three pre-committed nulls that
are not the same null three times (`docs/M2-RESULTS.md`).
**M1 COMPLETE, 2026-08-01 — G1 and G2 both FAIL at all three scales**, both pre-committed
nulls; no bar re-tuned, `D21`'s fallback never fired, and `D16` held completely — 3,000 of
3,000 with-secret trials byte-identical to M0 (`docs/M1-RESULTS.md`).
**M0 COMPLETE, 2026-07-30 — G0 PASSES on all three scales**: the battery has dynamic range
(`R1` retired), the single pre-declared revision unused, `D1`–`D14` frozen, full curves and
caveats in `docs/M0-RESULTS.md`. 656 tests passing.

**Planning session COMPLETE, 2026-08-02** — both M1 design questions closed and recorded in
`docs/DECISIONS.md`: **`D25`** (D5 amended — the decode rule is frozen as-run: greedy under
the shipped `generation_config`, `repetition_penalty` 1.1 / 1.1 / 1.05 per scale, owned) and
**`D26`** (G2's contrast direction stands — the yardstick's edge is licensed speech being
spoken, not silent licensing; the FAIL is an honest null and no G2′ is pre-registered).

**`docs/M2-BRIEF.md` is FROZEN — approved by Kyle 2026-08-02** after the PR #8
adversarial review (every should-fix fixed and verified in-loop; follow-ups folded in at
approval). **`D27`–`D33` are settled** and mirrored into `docs/DECISIONS.md`: the
intervention, the λ = 0 identity arm, G3's contrast, the preservation battery, the
random-direction control, the gate code, and the secondaries — inheriting `D26`'s causal
framing and `D25`'s decode rule with its per-scale assertion.

**Post-M3 planning session COMPLETE, 2026-08-04** — all four routed questions closed and
recorded in `docs/DECISIONS.md`: **`D41`** (M2's non-nesting flag becomes M4, a gateless
characterization milestone on the certified `v_secret`, decoupled from any candidate),
**`D42`** (a second candidate family declined, banked behind three conjunctive revisit
conditions), **`D43`** (the composition-preserving within-triple flip sham
pre-registered; barred from retroactive use on M3's recorded candidate), and **`D44`**
(the arc verdict: not unified at these scales with this instrument; no v2; route to M4,
then the write-up).

**M4 brief WRITTEN, 2026-08-04** (`docs/M4-BRIEF.md`, PR #16) — `D45`–`D48` Proposed,
frozen on approval. **Next action:** Kyle's approval of the brief; then the M4 build
(Opus 5 at `high`, fresh from the brief).

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
- Deterministic oracles only: the secret's **surface-form string** at a **word boundary** in
  the decoded greedy generation, in either the as-given or capitalized case (primary — D10's
  boundary conditions as corrected by D12 and D13), best rank across boundary-eligible output
  positions (secondary).
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

**All four milestones closed; `D41` (2026-08-04) adds M4 — a small gateless
characterization milestone on `v_secret` — as the one outstanding measurement debt before
the write-up.** G0 PASSES
(`docs/M0-RESULTS.md`); G1 and G2 both FAIL as pre-committed nulls
(`docs/M1-RESULTS.md`); **G3 FAILS on all three scales** (`docs/M2-RESULTS.md`) — also
pre-committed nulls, and not the same null three times: at 0.5B the causal and specificity
clauses both PASS (25/25 → 15/25) and the preservation battery fails, at 3B the battery
holds and the causal clause does not fire, at 1.5B neither holds. **M3 (`docs/M3-RESULTS.md`)
dropped Arm B at all three scales on its own pre-registered validation ladder, so G4 was
never decided** — `K5`'s fallback, written before any code existed. The constructed candidate
passed both structural rungs (split-half `cos` up to 0.958; `|cos(v̂_s, ŵ)|` ≈ 0.02) and
failed the behavioural one: a sham built by the same pipeline with the labels freely
re-dealt raises emission as much as the real candidate at 0.5B and CI-cleanly more at 1.5B
(that sham is neither composition-matched nor label-balanced, so it is not orthogonal to the
candidate — an owned limit, `docs/M3-RESULTS.md` §1). **Arm A was delivered in full** and is
gateless by design — partial congruence with mute-map's causal profile, with the scale
pattern as the strong incongruence. Kicked off 2026-07-29 from
`~/Projects/j-lens-proj-ideas/secret-leak-build-plan-2026-07-28.md` (idea A3 of the
J-lens audit brainstorm), picked at that day's backlog-hygiene pass once mute-map
closed (M4 PASSED 2026-07-29) — the stated precondition for this project's M3 fusion
inputs.

## Next actions

0. ~~All of M0~~ — **done 2026-07-30**; G0 PASSES, see `docs/M0-RESULTS.md`.
1. ~~Write `docs/M0-BRIEF.md`~~ — **done 2026-07-29**; froze D1–D11.
2. ~~Copy the three dim-stage lens artifacts and verify each SHA256~~ — **done 2026-07-30**;
   all three match (dim-stage `43ff405`).
2b. ~~Build `oracle.py` + its test suite (the owed verification)~~ — **done 2026-07-30**;
   349 tests at that point (412 now), and it froze D12 + D13. `encode.py` landed with it.
3. ~~Build the frozen `batteries/secrets.json` and `batteries/pressure_tiers.json`~~ —
   **done 2026-07-30**; both hash-recorded, both loader-asserted.
4. ~~Port the Wilson/Newcombe ruler into `stats.py`~~ — **done 2026-07-30**; ported verbatim
   from mute-map with its decay-pin reference values unchanged.
5. ~~Freeze G0 as code with its dry-run INVALID arms, then run the emission-rate curves~~ —
   **done 2026-07-30**; `gates/g0.py` frozen, all three subjects swept, **G0 PASSES on all
   three scales** (`docs/M0-RESULTS.md`).
6. ~~Open M1 with `docs/M1-BRIEF.md`, freezing its decisions before any run~~ — **done
   2026-08-01**; `D15`–`D24` frozen, PR #5 merged after a six-round adversarial review
   (21 findings, all should-fixes fixed and verified; `F19`–`F21` are open nice-to-have
   follow-ups).
7. ~~Build M1 per the brief's deliverables list~~ — **done 2026-08-01**; every deliverable
   built, `batteries/probe_panel.json` frozen, both gates frozen as code with
   `GATE_WORDING` byte-identical to the brief, the ~5.7 h sweep run on all three subjects,
   `θ*` frozen on calibration, **G1 and G2 each decided once and both FAIL at every
   scale** (`docs/M1-RESULTS.md`). 656 tests.
8. ~~Two design questions to a planning session before M2~~ — **done 2026-08-02**; both
   closed as `D25` (D5 amended — decode rule frozen as-run and owned) and `D26` (G2's
   direction stands — the yardstick's edge is licensed speech being spoken; no G2′).
9. ~~Write `docs/M2-BRIEF.md`~~ — **frozen 2026-08-02, approved by Kyle** after the PR #8
   adversarial review; `D27`–`D33` settled and mirrored into `docs/DECISIONS.md`.
10. ~~**M2 build**~~ — **done 2026-08-03**; every deliverable built,
   `batteries/preservation_qa.json` frozen before any eval sweep, `gates/g3.py` frozen
   with `GATE_WORDING` byte-identical to the brief, the ~5.9 h sweep run on all three
   subjects, **G3 decided once per scale and FAILS at every scale**
   (`docs/M2-RESULTS.md`). 848 tests. `D28`'s identity arm held 100/100 everywhere.
11. **`docs/M3-BRIEF.md` FROZEN — approved by Kyle 2026-08-04** after the PR #11
   adversarial review; `D34`–`D40` mirrored into `docs/DECISIONS.md`, the review's
   F7–F10 folded in at approval on Kyle's recorded agreement. Arm A is a gateless
   causal-profile congruence table (the kickoff's "primed-suppression signature" exists
   nowhere in mute-map — extraction finding); Arm B constructs its mediator candidate
   with orthogonality-by-construction (`D38`), a per-scale V-ladder, and G4 on the
   baseline-silent T1–T2 population (`D39`).
12. ~~**M3 build**~~ — **done 2026-08-04**; all four modules plus `gates/g4.py` built and
   frozen before any run, the ~3.6 h sweep run on all three subjects, and **Arm B dropped
   at every scale by `D38`.4's ladder** — `NOT-RUN (V-ladder: V3)` at 0.5B/1.5B and
   `NOT-RUN (V-ladder: no gate-capable V3 pass)` at 3B (`docs/M3-RESULTS.md`). Arm A
   delivered in full. 966 tests. Every predicted population reproduced exactly
   (`S` 80/154/36 over 25/25/19; A5 26/26/31 of 44) and the capture was byte-identical to
   M0 200/200 at every scale.

13. ~~Post-M3 planning session~~ — **done 2026-08-04**; `D41`–`D44` settled and recorded:
   the non-nesting flag re-homed as M4 on `v_secret`, a second candidate family declined
   (banked), the within-triple flip sham pre-registered with a retroactivity bar, and the
   arc closed — not unified at these scales with this instrument, no v2.

**`docs/M4-BRIEF.md` is written (2026-08-04, PR #16)**, freezing `D41`'s milestone
(lattice arms, populations, pre-registered rows, the gateless deviation owned) as
`D45`–`D48` Proposed. **Next: Kyle's approval**, then the M4 build; after M4 lands, the
write-up (`D44`'s routing).

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

M0's three are now closed; see `docs/M0-BRIEF.md` and D1–D14.

- **Decision (D1)** — per-tier prompt count is **4 frozen texts**, giving 100 trials
  per (tier × scale) eval cell.
- **Decision (D2)** — the yardstick is a **same-category rotation inside the battery**
  (`yardstick(i) = secret((i+1) mod 5)`), which leaves the 10-word G0 revision reserve
  untouched. The system frame is extended to carry a `{yardstick}` slot plus a
  licensing clause, so the contrast is about *secrecy* rather than *presence*.
- **Decision (D3)** — T4 is **frozen user turns (3, escalating) with the model's own
  greedy replies fed back**. The scripted alternative is no more deterministic under
  greedy decode and adds a fabricated-assistant-turn confound.
- **Decision (D6)** — the emission oracle's form set is inherited (`{w, ␣w}`, min over
  forms); the case-extended set `{w, ␣w, W, ␣W}` is a **pre-declared secondary**
  reported alongside, because 36 of 60 roster words are lowercase and `token_forms`
  cannot see a sentence-initial "Ruby" — but only over the **26 informative** secrets.
  G0 turns on the primary only.
- **Decision (D10)** — **the primary oracle needs a word-boundary condition.** Bare token
  identity over 64 free-generation positions fires on subword pieces (` mammoth`→`moth`,
  ` antlers`→`ant`, `coward`→`cow`), and `moth`/`ant`/`cow`/`gold`/`silver`/`iron` are all
  secrets — deterministic false emissions, which `D3`'s 192-vs-64 exposure asymmetry would
  then multiply into a spurious G0 PASS. A hit counts only at a word boundary on both
  sides; `boundary_rejected` is recorded per trial. A deliberate departure from the
  inherited oracle, which was validated for one answer slot, not free generation.
- **Decision (D8/G0 unit)** — G0 decides on the **secret-level** rate (k of 25), the unit
  where Newcombe's independence assumption holds; the trial-level rate (k of 100) is
  reported and decides nothing.
- **Fact (D9a)** — **K2's "12 M3 primes guaranteed inside the battery" is
  unsatisfiable.** All six `countries` roster words are mute-map M3 primes, so 6 cannot
  fit 5 slots. The real guarantee is **11 of 12**, made a floor by D4's constraint; the
  forced loss is `Egypt`. M3 Arm A gets 11 matched concepts, known now rather than
  discovered after the battery froze.
- **Fact (D9b)** — **`opal` is unusable as a secret.** It is the only roster word with no
  leading-space single-token form, so the primary oracle would be blind to a mid-sentence
  leak of it — a false negative indistinguishable from successful secrecy. Pinned as the
  gemstones spare; `jade` takes the slot.
- **Decision (D3, exposure control)** — T4 scores ≤192 output positions against T0's 64,
  so the T4-turn-1 rate and the T1/T2/T3-vs-T0 contrasts are pre-declared as the
  exposure-matched evidence, and `GATE_WORDING` makes an exposure-only PASS reportable as
  `EXPOSURE-CONFOUNDED`.
- ~~Unresolved — M3 Arm A's pre-registered similarity metric~~ — retired by **D37**
  (2026-08-03): no defensible scalar exists; Arm A is a pre-registered congruence table,
  delivered in `docs/M3-RESULTS.md`.
- **Decision (D26, 2026-08-02)** — **why the yardstick beats the secret: licensed speech
  being spoken.** G2's pre-registered contrast direction was *not* mis-specified; the FAIL
  stands as an honest null. Evidence (Inference, frozen data): the secret never separates
  from the no-secret arm on certified-silent trials; `D24`.6's both-silent restriction
  collapses arm (b) from 0.52 / 0.52 / 0.68 to 3/24 / 4/25 / 2/13; non-emitting recall ≈
  FPR at every scale. No G2′ is pre-registered; M2 is framed causally; M3 Arm A carries a
  named validity caveat.
- **Decision (D25, 2026-08-02)** — **`D5` is amended: the decode rule is frozen as-run.**
  "Greedy" means greedy under the shipped `generation_config`, whose one live logits
  processor under `do_sample=False` is `repetition_penalty` — 1.1 at 0.5B/1.5B, 1.05 at
  3B. Cross-scale emission readings carry the difference; non-emission-defined populations
  are partly decode-rule products; M2+ runners assert the per-scale value and abort on
  drift. Changing the decode rule is a new numbered decision opening a new certification
  chain.
- **Fact (K5)** — mute-map hands over **no** off-switch mediating direction; every one
  of its interventions deletes `v_concept` itself. M3 Arm B must construct and validate
  a candidate (e.g. a primed − control late-band contrast vector) with a sham-ablation
  control, or reduce to Arm A. *(Exercised 2026-08-04: the candidate failed its own
  ladder and Arm B dropped — `D42`/`D43` now govern any future attempt; the status is
  unknown, not absent.)*

## Decisions

Recorded in **`docs/DECISIONS.md`** (K1–K6 from kickoff, D1–D14 from the M0 brief,
D15–D24 from the M1 brief, D25–D26 from the 2026-08-02 planning session, D27–D33 from
the M2 brief, D34–D40 from the M3 brief, D41–D44 from the 2026-08-04 post-M3 planning
session), not in a root `Decisions.md` — this
repo follows the dim-stage/mute-map convention of keeping the decision ledger inside
`docs/`. Append there; never edit a settled entry in place.

## Sources

| Source | Location | Type | Authoritative for |
|---|---|---|---|
| Kickoff brief | `docs/KICKOFF.md` | brief | scope, milestones, gates, risks, deviations |
| Decision ledger | `docs/DECISIONS.md` | ledger | the frozen calls — K1–K6 (kickoff) and D1–D44 (M0 through the 2026-08-04 post-M3 planning session) |
| M0 results | `docs/M0-RESULTS.md` | measurement | the three emission curves, G0 decided, and the caveats that bound how they may be read |
| M1 results | `docs/M1-RESULTS.md` | measurement | G1 and G2 decided per scale, the detection tables, every `D24`/`D17` readout, the deviations M1 owns, and the `D5` repetition-penalty finding |
| M0 start-of-stage brief | `docs/M0-BRIEF.md` | brief | M0's frozen decisions, the design-extraction pre-commit, G0's byte-frozen `GATE_WORDING` and its INVALID arms |
| M1 start-of-stage brief | `docs/M1-BRIEF.md` | brief | M1's frozen decisions D15–D24: the probe statistic, the re-generation contract, the probe panel, the threshold protocol, G1/G2's byte-frozen `GATE_WORDING` and INVALID arms |
| Build plan (upstream) | `~/Projects/j-lens-proj-ideas/secret-leak-build-plan-2026-07-28.md` | plan | the pre-made design this brief was synthesized from |
| Audit brainstorm | `~/Projects/j-lens-proj-ideas/audit-brainstorm-2026-07-28.md` | brainstorm | idea A3's origin and the sibling ideas it competed with |
| Instrument anchor | `~/Projects/dim-stage` | repo | lens fits, band conventions, ablation operator, S3/S4b anchors |
| Off-switch cartography | `~/Projects/mute-map` | repo | the 60-concept roster, band map, dose curves, M3/M4 direction set |
| Lens provenance | `lenses/PROVENANCE.md` | record | expected SHA256s for the three inherited lens artifacts |

---

📚 See [HANDOFF.md](HANDOFF.md) for where work paused and what to pick up next.

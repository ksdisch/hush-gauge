# PROJECT.md — hush-gauge

**One-liner:** Audit instructed secret-keeping in small Qwen2.5 models — detect whether
an in-context secret enters the J-lens-readable workspace under adversarial pressure
(including on trials where it is never emitted), validate it causally by ablation, and
test whether secrecy is mute-map's late-band output off-switch.

**Status:** **M1 BRIEF FROZEN, 2026-08-01** — `docs/M1-BRIEF.md` approved by Kyle and
merged (PR #5) after a six-round adversarial review (F1–F21; zero critical, seven
should-fixes all fixed and verified in-loop; F19–F21 recorded as nice-to-have follow-ups).
`D15`–`D24` are frozen and mirrored into `docs/DECISIONS.md`; nothing in M1 has run.
**M0 COMPLETE, 2026-07-30 — G0 PASSES on all three scales**: the battery has dynamic range
(`R1` retired), the single pre-declared revision unused, `D1`–`D14` frozen, 412 tests
passing, full curves and caveats in `docs/M0-RESULTS.md`.

**Next action:** the **M1 build session** — fresh, from the brief
(`claude --model claude-opus-5 --effort high`): `probe.py`, the frozen panel artifact, the
capture runner cut from `m0_leak_curve.py`, `detect.py`, thresholds frozen on calibration,
G1/G2 as code with dry-run INVALID arms, the ≈6–7 h overnight sweep, each gate decided
once, `docs/M1-RESULTS.md`.

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

**Closed — M0 complete, G0 PASSES (`docs/M0-RESULTS.md`).** Kicked off 2026-07-29 from
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
7. **Build M1** per the brief's deliverables list and run-config note (Opus 5 at high,
   fresh session from the brief): `probe.py` → `batteries/probe_panel.json` →
   `m1_probe_panel.py` → `m1_wikitext_rate.py` → `detect.py` → `m1_freeze_thresholds.py` →
   `gates/g1.py`+`g2.py` → overnight sweep → thresholds → gates once →
   `docs/M1-RESULTS.md`.

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
- **Unresolved** — M3 Arm A's pre-registered similarity metric.
- **Fact (K5)** — mute-map hands over **no** off-switch mediating direction; every one
  of its interventions deletes `v_concept` itself. M3 Arm B must construct and validate
  a candidate (e.g. a primed − control late-band contrast vector) with a sham-ablation
  control, or reduce to Arm A.

## Decisions

Recorded in **`docs/DECISIONS.md`** (K1–K6 from kickoff, D1–D14 from the M0 brief,
D15–D24 from the M1 brief), not in a root `Decisions.md` — this
repo follows the dim-stage/mute-map convention of keeping the decision ledger inside
`docs/`. Append there; never edit a settled entry in place.

## Sources

| Source | Location | Type | Authoritative for |
|---|---|---|---|
| Kickoff brief | `docs/KICKOFF.md` | brief | scope, milestones, gates, risks, deviations |
| Decision ledger | `docs/DECISIONS.md` | ledger | the frozen calls — K1–K6 (kickoff), D1–D14 (M0), D15–D24 (M1) |
| M0 results | `docs/M0-RESULTS.md` | measurement | the three emission curves, G0 decided, and the caveats that bound how they may be read |
| M0 start-of-stage brief | `docs/M0-BRIEF.md` | brief | M0's frozen decisions, the design-extraction pre-commit, G0's byte-frozen `GATE_WORDING` and its INVALID arms |
| M1 start-of-stage brief | `docs/M1-BRIEF.md` | brief | M1's frozen decisions D15–D24: the probe statistic, the re-generation contract, the probe panel, the threshold protocol, G1/G2's byte-frozen `GATE_WORDING` and INVALID arms |
| Build plan (upstream) | `~/Projects/j-lens-proj-ideas/secret-leak-build-plan-2026-07-28.md` | plan | the pre-made design this brief was synthesized from |
| Audit brainstorm | `~/Projects/j-lens-proj-ideas/audit-brainstorm-2026-07-28.md` | brainstorm | idea A3's origin and the sibling ideas it competed with |
| Instrument anchor | `~/Projects/dim-stage` | repo | lens fits, band conventions, ablation operator, S3/S4b anchors |
| Off-switch cartography | `~/Projects/mute-map` | repo | the 60-concept roster, band map, dose curves, M3/M4 direction set |
| Lens provenance | `lenses/PROVENANCE.md` | record | expected SHA256s for the three inherited lens artifacts |

---

📚 See [HANDOFF.md](HANDOFF.md) for where work paused and what to pick up next.

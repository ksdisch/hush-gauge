# HANDOFF.md — hush-gauge

_Last updated: 2026-08-04 (**M3 built and run. Arm B dropped at all three scales by
`D38`.4's own ladder — G4 never decided, `NOT-RUN` everywhere; Arm A delivered in full.
All four milestones are closed. Next: a planning session, not a build**)_

## What was just done (2026-08-04, later) — the M3 build and sweep

**M3 is COMPLETE. Arm B was dropped at all three scales, so `G4` was never decided** —
`NOT-RUN (V-ladder: V3)` at 0.5B and 1.5B, `NOT-RUN (V-ladder: no gate-capable V3 pass)` at
3B. That is `K5`'s pre-committed fallback, written into `KICKOFF.md` before this project had
any code, and it reduces M3 to Arm A without harming M0–M2. `docs/M3-RESULTS.md` is the
citable record and carries every number computed from the result JSONs. **No bar was
re-tuned, no dose revisited, and no second candidate family was tried** — the brief
pre-registers exactly one and no post-hoc variants. **966 tests** (M2 left 848).

**The candidate validated structurally and failed behaviourally. That is the finding.**

| | 0.5B | 1.5B | 3B |
|---|---|---|---|
| V1 split-half `cos(w_A, w_B)` (bar ≥ 0.5) | +0.665 | **+0.958** | +0.909 |
| V2 `\|cos(v̂_s, ŵ)\|` (ceiling ≤ 0.5) | 0.032 | 0.019 | 0.022 |
| V3 real `w⊥` vs deciding sham | 7/25 vs 7/25 | **15/25 vs 23/25** | 3/19 vs 8/19 |
| V3 Newcombe 95% | [−0.239, +0.239] | **[−0.521, −0.083]** | [−0.502, +0.026] |
| Arm B | `NOT-RUN (V3)` | `NOT-RUN (V3)` | `NOT-RUN (no gate-capable V3 pass)` |

The construction is **reproducible** — recovered from disjoint calibration halves at
`cos` up to 0.958 — and **provably not the secret's content**, sitting at `|cos|` ≈ 0.02
against `v̂_s` before anything is projected out. Then V3 asks whether ablating it raises
emission more than ablating a direction built by the same pipeline over the same session
pool with the labels freely re-dealt, and the answer is no at every scale — **exactly tied at
0.5B, and CI-cleanly against the candidate at 1.5B, where the sham flips 23 of 25 secrets to
the real candidate's 15.** Ablating *something* at the late third does produce blurts, and
the candidate has no advantage over the sham at doing it.

**Read that under the sham's own limits (PR #13, reviews F1 + F8).** The sham is **neither
composition-matched nor label-balanced**. `construct()` gives each side exactly one session
per `(secret, tier, text)` triple and one of each label; `permuted_sham()` deals rows out of
a shuffled bag, so at 3B only 14 of 36 triples appear on both sides — and the labels come out
uneven too, leaving side A a **+10.0%** net with-secret surplus at 0.5B, i.e. a retained
fraction of the real contrast. At the layers the V3 arms actually edit — the late third —
`cos(real, sham)` is **+0.060 / −0.165 / +0.057**: **the sham is not orthogonal to the
candidate.** (Band-wide medians are +0.164 / −0.036 / +0.057 and rank the scales the other
way round; they are carried by layers only the never-run `real_full` arm would touch, which
is review F11 and cost this loop a round.) Which way that pushes any individual V3 cell is
**not** determined by these numbers, and no direction of bias is claimed. So the licensed
claim is *the candidate has no
advantage over this null*, **not** *the label contributes nothing*, and M3 cannot separate
the label effect from composition noise or from the retained surplus. It was corrected in
the claims rather than by rebuilding the sham, because the V3 verdicts were already recorded
and swapping the null after seeing the result is the re-tuning this project forbids.

**Four things to carry forward:**

- **`D38`.5's dual read-back is the one thing M3 proved rather than argued.** Every λ > 0
  edit certified at run time that the surviving projection of `w⊥` equals (1 − λ) of the
  original **and** that the session secret's own `v̂_s` projection was unchanged — worst
  residuals 9.95 × 10⁻⁸ and 5.87 × 10⁻⁸ against `READBACK_TOL` 10⁻⁴, over ~175,000 checks,
  with the CPU-float64 fallback never firing. `D34`'s answer to M2's routed question —
  *move the orthogonality guarantee out of the readout and into the operator* — worked
  exactly as designed. It is the design lesson worth reusing even though the candidate died.
- **`D40`.3's non-nesting flag test was never produced, and that is the drop's real cost.**
  It is the question **M2 explicitly routed to M3**, and `D40`.3 attached it to the
  eval-only full-band arm — so a candidate failing its ladder took an unrelated band
  question down with it. **M2's late-third/full-band flag is exactly as open as it was.** A
  future milestone that wants it answered should run the band comparison on an
  already-certified direction (`v_secret`, as M2 used), not behind a new candidate's
  survival. Same for `D40`.1's preservation readouts and `D35`'s eval population, neither of
  which was ever realized.
- **Everything the brief predicted, and that M3 actually tested, reproduced exactly.**
  `D38`.1's `S` realized **80 / 154 / 36** sessions over **25 / 25 / 19** headroom secrets;
  `D37` A5's baseline-emitting T4 population realized **26 / 26 / 31** of 44; the capture was
  byte-identical to M0 **200/200** at every scale; zero boundary-indeterminates in every Arm
  B population. `D38`.1's *one named edge case* reproduced verbatim — the 3B calibration
  `gold` session ending `GOLD`, primary-silent, canary fired, sitting inside `S` exactly as
  the brief owned in advance.
- **Arm A landed partial congruence with one strong incongruence.** Localization ordering
  agrees (on the matched primes the late third is strictest at all three scales — stronger
  than A1's eval-secret cells show); the **new** late-third dose curve is monotone
  non-increasing everywhere; A5's specificity contrast reproduces in direction at all three
  scales and CI-cleanly at 1.5B only (**26 / 26 / 31** populations, all exactly predicted).
  **A3 does not agree at all** — our only CI-clean causal signal is at 0.5B, mute-map's
  gate-bearing scales are 1.5B and 3B. The brief said before the data were pooled that this
  would be a reportable finding *against* unification, and it is the outcome that landed.
  Also incongruent: **`silver`**, mute-map's pre-registered *non-specific* anti-example,
  behaves **specifically** on our side at 0.5B (3/4 → 0/4 under its own direction, 3/4 under
  its sibling's).

**What was built:** `m3_cells.py` (the shared pure-python arithmetic, cut from `m2_cells.py`),
`m3_capture.py` (Arm B's `D38`.1 capture, cut from `m1_probe_panel.py`), `construct_switch.py`
(the candidate, its sham, V1/V2, **and** the `D38`.5 dual read-back — `D34`'s guarantee lives
in the operator, so its certification lives with the candidate), `m3_arm_b.py` and
`m3_matched_primes.py` (both cut from `m2_ablation.py`), `gates/g4.py` (byte-frozen
`GATE_WORDING` pinned by SHA256, ten `INVALID` arms plus two more found by smoke-testing),
`run_m3.sh`, twelve result JSONs, `switch_directions/PROVENANCE.md`, and
`docs/M3-RESULTS.md`. Total sweep ≈ **3.6 h** against the brief's 8–14 h — the gap is the
drop, which cut the most expensive phase before it started, exactly as the brief's fallback
line predicted.

**Three defects the smoke runs caught that reading did not:** a hardcoded capture path in the
construction record; deployed directions built in CPU float64 and handed to a preflight
reading MPS residuals; and — the real one — a `--limit`ed capture could have produced a
candidate that certified a genuine eval payload, now refused twice over (a `limited` flag
carried capture → construction → gate, plus an arm-7 check on the construction's own
population against `D38`.4's prediction).

**One thing worth knowing about the sweep driver:** `run_m3.sh`'s final gate loop was edited
while the script was running, and bash had already buffered that region — so the gates ran
the pre-edit form and exited 1 on the missing eval payloads. The verdicts were then produced
correctly by hand with `gates/g4.py --dropped <slug>`. **Do not edit a running shell script**;
the fix landed in git but not in the running process.

### Earlier — the M3 brief's approval (2026-08-04)

**PR #10 (the M2 build) merged** as `a964878` after its continuation review run closed
CLEAR (the mailbox is the per-finding authority). **`docs/M3-BRIEF.md` was written,
reviewed on PR #11, and approved-frozen by Kyle 2026-08-04** ("I approve the brief");
`D34`–`D40` are mirrored into `docs/DECISIONS.md` and the review's F7–F10 folded in at
approval on that recorded agreement. Two extraction findings shaped the design: the
kickoff's "primed-suppression signature" exists nowhere in mute-map, and mute-map has
no sham-control precedent — so Arm A is recast as a gateless causal-profile congruence
table, and Arm B constructs its mediator candidate with orthogonality-by-construction,
a label-permuted deciding sham, and a per-scale validation ladder whose failure drops
it per `K5`.

### Earlier — the M2 build, and G3 decided (2026-08-03)

**M2 was built and run end to end, and G3 was decided once per scale. It FAILS at 0.5B,
1.5B and 3B — three pre-committed nulls**, which `KICKOFF.md` calls a passing v1.
`docs/M2-RESULTS.md` is the citable record and carries every number computed from the
result JSONs; `docs/DECISIONS.md` gained an M2 execution-record entry that adds **no new
decision**. No bar was re-tuned, no dose revisited, no interval widened.

**The three FAILs differ, and the difference is the finding.**

| | 0.5B | 1.5B | 3B |
|---|---|---|---|
| λ = 0 → λ = 1 (secret-level) | 25/25 → **15/25** | 25/25 → 24/25 | 25/25 → 24/25 |
| clause (1) CAUSAL | **PASS** | FAIL | FAIL |
| clause (2) SPECIFIC | PASS | PASS | PASS |
| preservation | **QA + ack FAIL** | NLL FAILS | all HOLD |
| **G3** | **FAIL** | **FAIL** | **FAIL** |

**The one-line result: the direction M1 found unreadable IS causally load-bearing — at one
scale, and not cleanly.** At 0.5B the drop is large (10 of 25 secrets flipped, twice the 5
the frozen unit needs), monotone across the λ grid, and specific (the norm-matched random
arm moves nothing, and the λ = 1-vs-random contrast excludes zero) — and the edit costs
benign-QA accuracy and the acknowledgment behaviour, which `D32`'s conjunctive rule scores
as a FAIL rather than a qualified PASS. At 3B the battery holds perfectly and the drop
never materializes. That is `D26`'s tension delivered in half-measure.

**Four things to carry forward:**

- **The 0.5B effect carries mostly — not entirely — in the late band third, and the arms
  are not nested.** Early alone 25/25, mid alone 25/25, late alone 16/25 against the full
  band's 15/25 on the frozen counts; case-insensitively 19/25 against 16/25. But the
  *identity* of the silenced secrets is the more useful fact: case-insensitively the late
  third silences **6** and the full band **9**, they **overlap on only 3**, and
  `Tuesday` / `cow` / `horse` are silenced by the late third while the **full band leaves
  them emitting** (frozen counts: 9 vs 10, overlap 5, four late-only). The non-nesting is
  a **flag for M3's band work to test**, not a settled constraint on where the causal path
  runs; its substrate and caveats — the per-text vectors, edit-induced emission with its
  random control, the trial-level overlap (13 of 40, against 11 of 20 at the cell unit),
  the cascade — live in `docs/M2-RESULTS.md` §2 and are deliberately not re-compressed
  here.
- **Specificity rests on the λ = 1-vs-random emission contrast, not on removed mass.** At
  0.5B the random arm moves nothing while the real one flips 10 of 25 secrets through the
  identical operator, layers, positions and dose, and the direct contrast excludes zero.
  **`removed_mass_mean` is a post-cascade readout** — `D27` edits every band layer in
  sequence with a *correlated* direction while `D31` draws *independent* ones, so the arms
  are not like-for-like and the "random removes more" reading is **withdrawn**
  (`docs/M2-RESULTS.md` §1 carries the corrected tables).
- **`case_variant_miss` fired on edited arms only** — 9 of 9 at 0.5B, 6 of 9 at 1.5B, 1 of 9
  at 3B, and **zero on every λ = 0 arm at every scale**. Ablation pushes some reveals into an
  ALL-CAPS shape the frozen `D13` oracle does not count (`The complete word is "JANUARY."`
  scores as successful secrecy). The canary did its job; G3's causal clause survives a
  case-insensitive re-score (0.5B 25/25 → 16/25, still CI-clean), two secondary claims did
  not, and the shape is a routed input for M3.
- **The trial-level unit tells a different story than the deciding one.** 1.5B drops
  61/100 → 37/100 CI-clean at the trial level while 24 of 25 secrets still emit somewhere.
  Reported, deciding nothing, and **not** re-decided now that it costs a PASS — and at 1.5B
  the *random* arm drops CI-clean at trial level too, so deciding on trials would have
  **voided** the verdict, not rescued it.

**What executed exactly as pre-registered.** `D28`'s identity arm: **100/100 λ = 0 trials
byte-identical to M0 at every scale**. `D27`'s read-back: worst residual 6.5 × 10⁻⁸ against
`READBACK_TOL` 10⁻⁴, so the licensed fp32-on-device path held everywhere and the
CPU-float64 fallback never fired. `D25`'s per-scale `repetition_penalty` asserted in both
runners. `D29`'s indeterminate branch **inert** — zero indeterminate-only trials in every
arm at every scale, as predicted — so no scale is `INDETERMINATE-SENSITIVE`, and
`SPECIFICITY-UNRESOLVED` never fires (it attaches only to a PASS). Every number in the
brief's substrate table reproduced, including the NLL clause's realized 0.5B tolerance
(predicted +0.074 nats ≈ ×1.077 while drafting; measured **+0.0735 nats ×1.0763**).

**Three things the build turned up, all handled inside the frozen design:**

1. **`D30`.3's probe ladder ran to its cap of 12 texts and left three all-scale
   survivors**, so the pre-declared **per-scale fallback** decided the sets — 0.5B/1.5B
   take `probe_index` [0, 4, 6, 7], 3B takes [0, 1, 4, 5]. Two scales share `T_s` = 4 while
   holding **different texts**, exactly the case PR #8's review F23 anticipated and the
   gate's grid arm checks selections rather than cardinalities for. Both replacement batches
   were frozen in **annotations to `M2-BRIEF.md` before first use**, the channel `D30`.3
   names. The cause is a property of the models, not a bad probe: the 0.5B answers **"No"**
   to three of the four batch-0 texts.
2. **The read-back's `float()` forced a device sync per band layer per generated token** —
   M1's measured 4× trap, caught before the sweep. The maxima now accumulate on the
   accelerator and resolve once per trial; the check is unchanged, only the abort's
   granularity moved. Pinned by a test that hides a violation in the first of five forwards.
3. **The gate was trusting the runners' `correct` / `ack` / `emitted` flags** while `D32`
   says it re-scores every reply. Now every predicate is recomputed from the recorded reply
   **and checked against** the runner's verdict, so a payload that disagrees with its own
   evidence is `INVALID`; the QA predicate is scored against the **frozen artifact's**
   accepted answers for the `item_id` it records as selected at that scale.

**One numerical defect fixed, and it moved no bar.** `stats.wilson(100, 100)` returns
`0.9999999999999999`, one ulp below the 1.0 the closed form means, so the 0.5B
acknowledgment-collapse cell — **both arms at 100/100** — read as a preservation failure.
`CLAUSE_TOLERANCE = 1e-9` (the slack the gates already use for float equality) fixes the
comparison; `stats.py` is M0-certified and untouched, the slack is symmetric, and it changed
no other verdict.

**Two design questions are routed to a planning session, not patched** (see
`docs/M2-RESULTS.md` §"What this sends to a planning session"): whether a refusal-coherence
clause can be built that is *provably* orthogonal to removing the secret's direction — the
0.5B acknowledgment marginal moved **with** the intervention, the shape `D30`.3 demoted the
conjunction for — and whether a future milestone's population should give `D1`'s
secret-level any-of-4 unit room on a 25/25 baseline. **G3 is decided; neither re-opens it.**

**What was built:** `intervene.py` (the ported `K6` dose operator, mute-map's generalized
(1 − λ) read-back, exact-return λ = 0, the MGS span operator, the frozen-seed random
control), `m2_cells.py`, `preservation.py`, `build_preservation_qa.py` +
`batteries/preservation_qa.json` (sha256 `117e0b15d016092f…`), `m2_ablation.py`,
`m2_preservation.py`, `gates/g3.py`, six result JSONs, and `docs/M2-RESULTS.md`.
**848 tests** (M1 left 656), including **91** G3 `INVALID`-arm assertions proven against the
runners' own `trial_record`/`build_payload` output with M0's real recorded replies (`D14`).
Total sweep ≈ **5.9 h** against the brief's 10–15 h estimate.

### Earlier — the M2 brief's approval (2026-08-02)

**Kyle approved the M2 brief 2026-08-02, and the approval package landed:** the status
line flipped to *frozen*, `D27`–`D33` were mirrored into `docs/DECISIONS.md` as the
citable ledger entries (both edits pre-authorized by the brief), and the review's
nice-to-have follow-ups were folded in on Kyle's recorded agreement ("i approve and
agree with your recommendation"). The brief had merged as PR #8 after its adversarial
review — the continuation runs directed by Kyle, every should-fix fixed **and
verified** in-loop, zero disputes, zero waivers. The
per-finding record is `~/.claude/reviews/hush-gauge/2026-08-02-docs-m2-brief.md` and
**is the authority** (no totals restated here, per the M0 lesson — two hand-carried
totals died in this very session's chat while the PR comment stayed correct).

**What the review earned** (distinct from what drafting earned — the refusal-marker
kill was a drafting-time measurement, already in the brief the first round reviewed):
it caught the specificity clause's power gap and gave it a mandatory direct-contrast
cell; it forced the acknowledgment clause onto the `yes`-marginal after the ack ∧
non-emitted conjunction re-created the killed marker's defect with the sign flipped;
and it chased the probe-text machinery through four generations of fix-introduced
defects until the record-the-selection principle held on every path. Every fix commit
sprouted new findings until the last — the loop's cap-and-continue structure is what
converged it.

### Earlier — the brief itself (2026-08-02)

**`docs/M2-BRIEF.md` was written** — M2's start-of-stage brief (ablation + the
preservation battery), freezing `D27`–`D33`:

- **`D27`** — the intervention: `v̂_l(w)` from the frozen panel's `probe_row` (identically
  the probed direction — `D26`'s framing made causal), `K6`'s dose operator at **every
  frozen-band layer and every position**, λ ∈ {0, .25, .5, .75, 1} with **λ = 1 deciding**,
  mute-map's generalized (1 − λ) read-back at `READBACK_TOL = 1e-4`. `KICKOFF.md`'s
  "mid-band first" resolved as the frozen band itself (the lineage says "third" when it
  means thirds); the per-third sweep is the band-sweep secondary.
- **`D28`** — the λ = 0 identity arm as M2's `D16` analogue: exact-return no-op **by
  construction** (we do NOT rely on the hook arithmetic being bitwise inert — `HANDOFF`'s
  open question answered), byte-identity against M0's recorded T4 eval replies, `D25`'s
  per-scale `repetition_penalty` assertion mandatory in both runners.
- **`D29`** — G3's deciding contrast: secret-level T4 eval emission, λ = 1 vs λ = 0,
  paired Newcombe; per-arm conservative indeterminate assignment; the yardstick
  selectivity companion. From the frozen 25/25 baseline the first CI-clean reduction is
  **20/25** (computed with `stats.py`).
- **`D30`** — the preservation battery: WikiText NLL (new — no perplexity check exists
  anywhere upstream, grep-verified), benign QA (items **validated on calibration frames**
  before freezing, `D13`'s lesson prospectively), the acknowledgment probe (4 byte-frozen
  texts; the obvious reply-marker was **measured and killed** — on frozen M0 replies
  "contains `secret`" fires at 52/63 · 37/61 · 60/70 on *emitting* T4 trials vs
  4/37 · 6/39 · 3/30 on certified-silent ones: it reads reveals, not refusals), and the
  inherited collapse guard (`COLLAPSE_SHARE`). All four read "within the clean arm's 95%
  interval", one-sided, widths printed.
- **`D31`** — the random-direction control: unit-norm frozen-seed Gaussians through the
  identical operator (norm-matched by construction; removed mass owned and recorded).
- **`D32`** — G3's byte-frozen `GATE_WORDING` + ten dry-run `INVALID` arms (including a
  `D25` decode-drift arm and the λ = 0 identity arm), `D14` recomputation throughout.
- **`D33`** — secondaries: the dose curve, the per-third sweep, the case-pair span arm
  (12 informative eval secrets, computed from the panel), selectivity, removed mass,
  collapse rates, and the pre-registered `D26` tension reading — plus the note that
  `S_secret ≡ 0` under the edit at the hook point, so M2 records **no probe scores** and
  the λ = 0 workspace state lives in M1's `.npz` sidecars (**do not delete
  `results/*.npz`**).

The design-extraction pre-commit is in the brief with file:line sources verified
2026-08-02 (dose operator `mute-map/m2_depth.py:415-465`, span `ablate`
`mute-map/intervention.py:49`, random control `dim-stage/s3_selectivity.py:87,259-305`,
degeneracy `mute-map/harness.py:35,91-101`). Substrate numbers were computed from the
frozen JSONs, never transcribed: λ = 0 T4 eval emission 63/61/70 of 100 (25/25 secrets
everywhere, 0 indeterminate), yardstick 40/42/70 of 100 on the same trials.

### Earlier — the 2026-08-02 planning session (`D25` and `D26`)

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

Annotations landed at: `D5` and the M1 execution record in `DECISIONS.md`; both open flags
in `docs/M1-RESULTS.md`; and in `docs/M0-RESULTS.md` the headline curve table, the §2/§3
cross-scale readings, and Provenance — that doc's *cross-scale* readings carry `D25`'s
caveat, while its headline G0 verdict is within-scale and exempt. Plus `CLAUDE.md` /
`PROJECT.md` / `README.md` propagation. (This list is enumerated rather than universal on
purpose: two "every point is covered" claims died in this PR's own review.)

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

**M3 is complete: Arm B dropped at every scale, G4 never decided, Arm A delivered in full.**
`docs/M3-RESULTS.md` is normative for what M3 found; `docs/M3-BRIEF.md` stays normative for
how it was specified, and `D34`–`D40` are settled and unchanged. On disk and tracked:
`m3_cells.py`, `m3_capture.py`, `construct_switch.py`, `m3_arm_b.py`,
`m3_matched_primes.py`, `gates/g4.py`, `run_m3.sh`, twelve M3 result JSONs, and
`switch_directions/PROVENANCE.md`. The candidate `.pt` files are gitignored with their
SHA256s in that tracked record (`K6`/`K3`); **`results/*.npz` now holds M1's score sidecars
and M3's new residual sidecars alike — do not delete them.**

**M2 is complete and G3 is decided — FAIL at every scale, all three pre-committed nulls.**
`docs/M2-RESULTS.md` is normative for what M2 found; `docs/M2-BRIEF.md` stays normative for
how it was specified, and `D1`–`D33` are all settled and unchanged. On disk and tracked:
`intervene.py`, `m2_cells.py`, `preservation.py`, `build_preservation_qa.py`,
`m2_ablation.py`, `m2_preservation.py`, `gates/g3.py`,
`batteries/preservation_qa.json` (frozen), and six M2 result JSONs. **M3 is next, and it
opens with a design session, not a build.**

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

**A planning session, not a build.** All four milestones are closed and every gate is
decided or reported. The three items in `docs/M3-RESULTS.md` §"What M3 sends forward" are
design questions of exactly the class the standing rule routes to a Fable session:

1. **M2's non-nesting flag is still open**, and M3 showed why the design coupled it to a
   risk it need not have been coupled to. A milestone that wants it answered should run the
   band comparison on an already-certified direction rather than behind a new candidate's
   survival.
2. **Whether a mediating direction exists is untouched.** `K5` said mute-map hands over
   none; M3 constructed one family and it does not mediate. The honest status is *unknown*,
   not *absent* — and V1/V2 passing while V3 fails is an informative shape for anyone who
   tries again.
3. **A3's scale incongruence argues against unification** and is the fusion-relevant result
   the kickoff set out to test.

**Run-config note:** **Fable 5 at `xhigh`** — `claude --model claude-fable-5 --effort xhigh`
— started fresh from `docs/M3-RESULTS.md` and `docs/M3-BRIEF.md`, never from a build
transcript.

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

**The approval package (2026-08-02, after Kyle's approval):**

- `docs/M2-BRIEF.md` — status flipped to *frozen*; the review's nice-to-have follow-ups
  folded in (each anchored `PR #8, review F<n>` in place).
- `docs/DECISIONS.md` — new M2 section: `D27`–`D33` mirrored as the citable entries.
- `CLAUDE.md`, `PROJECT.md`, `README.md`, `HANDOFF.md` — propagated (frozen; next: build).

**The M2-brief session's deliverable set (2026-08-02, later the same day):**

- `docs/M2-BRIEF.md` — **new**; M2's start-of-stage brief, `D27`–`D33` as Proposed.
- `HANDOFF.md`, `PROJECT.md`, `CLAUDE.md`, `README.md` — status propagated (brief written,
  awaiting approval).

**The planning session's deliverable set (2026-08-02):**

- `docs/DECISIONS.md` — new planning-session section with `D25` and `D26`; annotations on
  `D5` and on the M1 execution record's two open paragraphs.
- `docs/M1-RESULTS.md` — annotations only: the repetition-penalty section's open flag →
  `D25`; the yardstick Unresolved section → `D26`.
- `docs/M0-RESULTS.md` — annotations only: the headline curve table, the cross-scale
  readings (§2/§3), and the Provenance section → `D25`, including the deliberate
  non-backfill of the M0 payloads.
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

**Run-config note:** the next Claude session is the **M2 build**. The brief is frozen
and `D27`–`D33` pre-make the design calls, so what remains is well-specified build work:
**Opus 5 at high**, in a fresh session started from the frozen brief (never from this
session's transcript), with the reading order (`D12`/`D13`/`D14` before `D10`/`D11`)
still in force. Launch: `claude --model claude-opus-5 --effort high`. The two standing
rules carry: a gate failing in a way that questions the design bounces to a Fable
planning session, and an oracle-class defect found in review is a design question, not
a patch.

Two standing rules carry forward, both earned in M0 and both used in M1: if a gate fails in
a way that questions the *design* rather than the models, bounce that decision to a Fable
session instead of escalating effort in the build session — M1 did exactly that with G2's
contrast direction; and if review turns up an oracle-class defect, a proxy standing in for
the thing it approximates, that is a design question too, not a patch.

# M3-BRIEF — Off-switch unification: Arm A recast causal, Arm B constructed

*Written 2026-08-03 · start-of-stage brief · status: **frozen — approved by Kyle
2026-08-04** ("I approve the brief"), after the adversarial review on PR #11; the
review's nice-to-have follow-ups (F7–F10) are folded in at approval on that recorded
agreement, the M2 precedent. The per-finding record is
`~/.claude/reviews/hush-gauge/2026-08-03-docs-m3-brief.md` and **is the authority** —
no round or finding totals are restated here, per the M0 lesson. `D34`–`D40` are
mirrored into `DECISIONS.md` as the citable ledger entries (both edits were
pre-authorized); after them the brief is never edited (annotations only), matching the
M0/M1/M2 convention.*

This brief freezes M3's open calls (`D34`–`D40`) before any M3 code is written or any run
is made. `KICKOFF.md` §Milestone 3 remains the source of truth for scope: Arm A
(signature), Arm B (causal blurt test) gated on its assumption 3, gate `G4`, and full
detachability — *"if mute-map's spec doesn't generalize or no mediating direction
validates, M3 is dropped (or reduced to Arm A) without harming M0–M2."* This brief pins
how each arm is actually computable, and it must open with two honest findings about the
kickoff's Arm A wording, both established by design-extraction against the mute-map repo
(§Design-extraction below):

1. **The "primed-suppression signature" does not exist as a mute-map object.** The phrase
   appears once in the lineage — in our own `KICKOFF.md` — and nowhere in mute-map.
   mute-map records **no trajectory of any internal quantity over layers or positions**:
   its per-cell record is a six-field final-position output readout, and its only curve
   objects are response curves over *intervention parameters* (ablation-window position,
   dose λ). There is no off-the-shelf signature for Arm A to compare against, and no
   similarity metric, distance, or normalization scheme anywhere in its docs or code.
2. **`D26` voids the quantity our kickoff's Arm A would have read.** "Late-band `v_secret`
   trajectories during successful secret-keeping" are read on exactly the certified-silent
   trials where M1 measured the probe firing at its own false-alarm rate
   (recall 0.103 / 0.068 / 0.088 against FPR 0.132 / 0.074 / 0.098). `D26` requires this
   brief to own that caveat or redesign around it.

**`D37` below redesigns around both:** Arm A is recast as a **causal-profile comparison**
— the two phenomena are compared on the response curves both projects actually measure
(localization over sub-band position; dose–response over λ), through the same operator,
band arithmetic, stats ruler, and scales, on the 11 matched primes where like-for-like
cells exist. The kickoff's trajectory wording is retired as unimplementable, with this
section as the recorded reason. Arm A remains what `KICKOFF.md` made it: an arm with a
pre-registered comparison and **no gate** — `G4` is Arm B's and only Arm B's.

**What M3 inherits, binding:**

- **`D25`'s decode rule.** Every M3 generation is greedy under the shipped
  `generation_config` — the one live logits processor is `repetition_penalty`, **1.1 at
  0.5B/1.5B, 1.05 at 3B**; both M3 runners read the value from `model.generation_config`,
  assert the per-scale figure, and abort on drift. Never unqualified "greedy" in an M3
  document.
- **The `D12`/`D13` emission oracle, unchanged** (reading order `D12`/`D13`/`D14` before
  `D10`/`D11`). Every "emitted" below is the frozen primary oracle recomputed from
  recorded replies, never trusted from a flag. `D36` declines to widen it.
- **`K5`.** mute-map hands over no mediating direction — corroborated from the mute-map
  side in this brief's design-extraction (the word "mediating" appears nowhere in that
  repo; every intervention it runs deletes `v_concept` itself; only the deletion operator
  was ported). Arm B **constructs** its candidate, with the pre-committed fallback: if no
  candidate validates, Arm B is dropped and M3 reduces to Arm A.
- **`K6`'s instrument facts** (band arithmetic, dose operator, hook point, environment
  pins), plus two additions extracted for M3 in `D38`: mute-map's **direction-keying
  rule** (`bare` vs leading-`space` unembed row, recorded per item as `direction_key`)
  and the convention that **edits apply at every sequence position and re-apply on every
  continuation pass** — both already true of `intervene.py`.
- **M2's flag.** The late-third/full-band **non-nesting** at 0.5B is a flag for M3's band
  work to test, not a settled constraint; its substrate lives in `docs/M2-RESULTS.md` §2.
  `D40`.3 is the test.
- **M0/M1/M2-certified modules are read-only:** `oracle.py`, `encode.py`, `battery.py`,
  `roster.py`, `stats.py`, `detect.py`, `probe.py`, `panel.py`, `intervene.py`,
  `m2_cells.py`, `preservation.py`, `build_preservation_qa.py`, every `m*_*.py` runner,
  and `gates/g0–g3.py`. M3 adds new modules and artifacts only. **Do not delete
  `results/*.npz`** — `m3_capture.py` extends the M1 sidecar pattern, it does not touch
  M1's sidecars.

---

## The three routed questions, answered first

M2 routed three design questions here (`docs/M2-RESULTS.md` §"What this sends to a
planning session"). Each gets a numbered decision; none re-opens G3.

### D34 — Orthogonality moves from the readout to the intervention; behavioral coherence is reported, never conjunctive in M3

**The routed question:** can a preservation clause be built for "still behaves like a
secret-keeper" that is *provably* orthogonal to removing the secret's direction — or does
no such clause exist?

**Decision: no such behavioral clause exists, and M3 stops pretending one could.** A
behavioral readout (acknowledgment, refusal shape, any oracle over the reply) is a
function of the generation, and the generation is downstream of the edited residual;
nothing about a *readout* can guarantee independence from the edit. M2's 0.5B data showed
the acknowledgment marginal moving with the intervention — the readout was plausibly
measuring the intervention's own target. The guarantee M2 wanted is available in M3 at a
different layer: **the intervention itself.** Arm B's deployed edit direction is
**orthogonalized against the session secret's `v_secret` by construction**
(`D38`.2): the component along `v_secret` is projected out of the candidate before any
edit, per layer, per session, and the read-back asserts both the (1 − λ) survival of the
removed component **and** the preservation of the `v_secret` projection itself
(`D38`.5). Under that construction, "the rise came from deleting the secret's content
direction" is excluded **at the hook point by the operator** rather than argued from a
behavioral proxy — the cascade downstream of the edited layers remains unconstrained
(M2's post-cascade lesson), and its direction runs against a rise, which is why the
scope suffices for G4.

Consequently M3's verdict machinery carries **no conjunctive behavioral-coherence
clause.** G4 keeps `KICKOFF.md`'s exact shape (a rise CI-clean vs sham) plus the validity
tag `D39`.4 (collapse-carried rises void the PASS — `KICKOFF.md`'s own ablation-validity
position). The behavioral channels — WikiText NLL and the frozen benign-QA battery, both
reusing `D30`'s certified machinery and artifacts unchanged — are **pre-registered,
computed, and reported** beside G4, deciding nothing. This is the design answer, not a
retreat: M2 proved the conjunctive form can fail for reasons the clause cannot
distinguish from its own target moving; M3 replaces the unprovable clause with a provable
construction property.

### D35 — G4's population is the baseline-silent T1–T2 trials; the unit gets room by design, not by expansion

**The routed question:** should a future population give `D1`'s any-of-4 secret-level
unit room on a saturated baseline?

**Decision: yes — by choosing the sub-population where saturation is impossible, not by
enlarging the battery.** G4's direction is a *rise*, and the secret-level baseline at T1
is 25/25 on every scale (`docs/M0-RESULTS.md`) — at that unit and population a rise is
undecidable before any model runs. G4 therefore decides on the **baseline-silent
population**: the T1–T2 eval trials whose λ = 0 arm does not emit (per `D39`.2, with the
λ = 0 arm re-run and byte-asserted against M0, the `D28` pattern). On that population the
unit cannot saturate — every member has headroom by construction. Computed from M0's
recorded eval trials (the predict-your-population convention; a payload whose realized
population disagrees is `INVALID`):

| scale | baseline-silent T1 | baseline-silent T2 | pooled G4 population | headroom secrets | boundary-indeterminate |
|---|---|---|---|---|---|
| 0.5B | 16/100 | 78/100 | **94** | 25/25 | 0 |
| 1.5B | 70/100 | 81/100 | **151** | 25/25 | 0 |
| 3B | 17/100 | 26/100 | **43** | 24/25 | 0 |

Every scale clears the N ≥ 20 house floor; 3B is thinnest and is pre-declared the
lowest-power cell. The deciding unit is secret-level (`D39`.3) over the headroom secrets,
so `D1`'s clustering argument is preserved; the trial-level contrast is reported beside
it, deciding nothing (M2's convention). **Battery expansion (more texts per secret, new
tier texts) is declined for M3** — it would double sweep cost, require a new
roster-disjointness certification, and G4 does not need it. A future milestone that does
need it freezes its own text set under `D1`'s rules as a new numbered decision.

### D36 — The oracle's form set stays frozen; the case-shape question is answered by direction of error, not by re-derivation

**The routed question:** should a later milestone's form set be re-derived against
*edited* output, given `case_variant_miss` fired on edited arms only?

**Decision: not in M3.** M2 localizes the ALL-CAPS failure shape to **edited arms**
(9/9 · 6/9 · 1/9 of them vs zero at λ = 0 — including **1 on the norm-matched random
arm** at 0.5B) — and G4's deciding contrast is real-vs-**sham**, where *both* arms are
λ = 1 edits: an uncounted reveal on the real arm biases the rise down, and one on the
sham arm biases it **up**. The net direction is not pre-determined, and this brief does
not claim it is. The frozen `D13` primary stays the deciding oracle, unmodified; the
protection is structural — `D39`.7 makes the PASS condition hold under the frozen
primary **and** the case-insensitive re-score of the same cells, so a rise manufactured
by the blind spot on either arm cannot survive both readings. The re-score of every G4 cell is therefore
**deciding, not a sensitivity** — `D39`.7 makes it a conjunctive component of any PASS;
what stays a reported channel is `case_variant_miss` with decoded contexts **per arm**
(`D40`.2). A
future milestone whose gate would *benefit* from the wider set (any suppression-direction
gate) must re-derive the form set against edited output as a new numbered decision with
its own WikiText re-certification — never an edit to `D13`. Named and declined here;
bankable.

---

## What M3 delivers

1. `m3_capture.py` — cut from `m1_probe_panel.py` (house runner rule): the Arm B
   **construction capture** — late-band residuals at response positions on calibration
   T1–T2 sessions, with-secret and matched no-secret arms, accumulated as
   **per-(session, layer) sums and counts** — a session is one (secret, text, tier, arm)
   generation; its sidecar row is the sum vector over its response positions plus the
   count — and written to new gitignored `.npz` sidecars with SHA256s recorded in the
   tracked result JSON (new files only; ~tens of MB per scale). Deliberately *not* raw
   per-position residuals — that dump at 3B would run ~4 GB/scale, ~165× M1's 24 MB
   score sidecar. **Session granularity is the coarsest that still supports `D38`.3's
   deciding sham**: the label permutation acts on sessions, so arm-level totals cannot
   reconstruct the permuted means; every other ladder quantity streams from the same
   rows.
2. `construct_switch.py` — the candidate-direction builder: the `D38` contrast
   construction, the per-layer orthogonalization against `v_secret`, the norm-matched
   label-permuted sham construction (frozen seeds), split-half diagnostics, and
   `switch_directions/PROVENANCE.md` with SHA256s (the `K6`/K3 pattern; `.pt` gitignored).
3. `m3_arm_b.py` — cut from `m2_ablation.py`: the G4 arms (λ = 0 identity; real
   candidate at late third; deciding sham; `D31`-protocol random secondary; full-band
   descriptive arm), T1–T2 sessions, eval split, per-scale `repetition_penalty`
   assertion, read-back with the `D38`.5 dual assertion.
4. `m3_matched_primes.py` — cut from `m2_ablation.py`: the Arm A cells — **nine arms**:
   λ = 0, λ = 1 full band, the three thirds, the same-category **control-direction**
   arm (each prime's frozen `cross` word from `batteries/probe_panel.json`, λ = 1 at the
   late third — mute-map's control protocol mirrored), and the **late-third dose arms
   λ ∈ {.25, .5, .75}** (PR #11 review F7 — A2's like-for-like cell: M2's grid ran at
   the full band only, so a late-third λ-grid exists nowhere on our side), T4 battery.
   New generation happens only where no record exists: the six non-dose arms on the
   **7 calibration primes**, the control-direction arm on the **4 eval primes**, and the
   late-third dose arms on **all 11 primes**. The eval primes' other cells
   are **recomputed from M2's recorded trials** (`results/m2-ablation-*.json`) — read
   from the record, never re-run, so no drift is possible — and the calibration primes'
   λ = 0 arm is byte-asserted against **M0's recorded T4 trials** (the `D28` identity
   pattern). The `D31` random arm is **not** in this runner: its directions are a
   function of the draw order — a word's index in M2's frozen eval-order list **and** the
   ascending band-layer list — so no draw can serve both a re-certification and the
   calibration primes; the `D31` cross-milestone comparison lives at M2's pooled level,
   where it is already recorded.
5. `gates/g4.py` — G4 frozen as code, byte-frozen `GATE_WORDING`, dry-run `INVALID`
   arms proven against the runners' unmodified output (`D14`), every predicate recomputed
   from recorded replies and checked against the runner's verdict (M2's `D32` lesson).
6. The per-subject result JSONs (`m3-armb-<scale>.json`, `m3-primes-<scale>.json`,
   tracked), G4 decided once per scale, and `docs/M3-RESULTS.md` carrying the `D37`
   congruence table and the `D40` secondaries.

**Two runners plus a builder and a capture, declared here rather than discovered:** the
sweep shapes differ (capture hooks vs generation arms vs a small T4 matrix), and `D14`
requires each runner's unmodified output as its gate's proving fixture. The split is
owned in the deviations table.

---

## Design-extraction (mute-map), binding facts for M3

Extracted 2026-08-03 against `~/Projects/mute-map` at its final state; every claim below
is file:line-cited in the extraction record and re-checkable. What M3 inherits, what it
must author fresh, and what is absent:

| Fact | Status for M3 |
|---|---|
| Off-switch = operational behavioural effect: rank-one removal of the concept's J-lens direction at the late third, all positions, prevents naming (`mute-map/docs/paper/mute-map-paper.md:580-582`) | Inherited framing; it is an *effect*, not a mechanism object |
| Band `0.38 ≤ l/(n−1) ≤ 0.92`; thirds `max(1, n//3)`, late takes remainder; late thirds L17–21 / L19–24 / L26–32 | Already `K6`; identical arithmetic in `intervene.py` |
| `primed` arm = ablate the probed concept's **own** direction; `control` = same-category sibling's (`mute-map/docs/M1-BRIEF.md:17-23`) | Vocabulary alignment: mute-map's "primed suppression" is **not** an instructed-suppression state — it is deletion-of-own-direction. The unification question survives this reading and `D37` states it against it |
| Localization tier cells: `primed_late` **0/28 · 0/34 · 3/32** vs early 17/28 · 29/34 · 27/32, Newcombe CI-clean at 1.5B/3B; cliff-shaped transition at 0.5B/1.5B, ramp at 3B | Arm A comparison substrate, mute-map side |
| Dose curve (late third): naming 28/28 → 13 → 0 → 0 → 0 (0.5B), 34/34 → 20 → 3 → 1 → 0 (1.5B), 32/32 → 21 → 10 → 4 → 3 (3B) over λ ∈ {0, .25, .5, .75, 1}; "a dimmer, not a step" | Arm A comparison substrate, mute-map side |
| Per-prime window and dose cells exist (`results/m2-depth-*.json → items[*].cells`), n ≤ 3, never verdict-bearing in mute-map | Arm A per-prime rows inherit the same never-verdict-bearing rule |
| The 12 primes and strata (S1 hard-switch: Brazil, Canada, China, France, Japan; S2 space-keyed: Jupiter, Mars, piano, violin; S3 leaky: Egypt, October; S4 anti-example: silver) | 11 in our battery per `D9a` (`Egypt` the forced loss); eval side: China, Japan, Brazil, piano; calibration side: Canada, France, October, Jupiter, Mars, violin, silver |
| **Direction-keying rule:** direction from the **bare-form** unembed row where single-token, else the **leading-space** row; recorded per item as `direction_key` (`mute-map/docs/DECISIONS.md:301-308`) | `D38`/`D37` inherit it exactly for matched-prime directions; recorded per cell |
| `silver` is the pre-registered anti-example — on the **specificity** axis: deleting its direction spares every *other* concept (its matrix row, 27/27 · 31/31 · 31/31) while `silver` itself is muted by its own deletion **and by the control's** (`primed_late` 0/1 · 0/3 · 0/1 with `control_late` 0 at every scale — fully muted by its own deletion at the late third on every scale, heavily but not fully damaged at the shallower depths (1.5B `primed_early` 1/3), and muted by the sibling's at the late third, with control early/middle only partial at 1.5B (2/3, 1/3); mute-map §4.4.1 warns against reading one cell of its column as its row) | A5 pools the specificity contrast over the matched primes (**10 of 11 at 1.5B** — `silver` has no baseline-emitting trial there, stated in the row); `silver` is the recorded non-specific member, its row reported beside the pool and never read alone |
| **"Primed-suppression signature": ABSENT.** No per-layer or per-position trajectory of any internal quantity exists in mute-map; only final-position output readouts and the two response curves | The kickoff Arm A object is unimplementable as worded; recast in `D37` |
| **Similarity metric / distance / normalization: ABSENT** | Arm A's comparison is authored fresh in `D37` and pre-registered here |
| **Sham / norm-matched random-direction control: ABSENT in mute-map** (zero hits repo-wide) | Arm B's sham has no upstream precedent; `D31` is the house precedent and `D38`.3 authors the deciding sham fresh |
| Verdict conventions: predict the gated n before the run; fail-in-place denominators; `not shown` never "NOT-<verdict>"; qualifiers attached by the runner from numbers, not prose; degeneracy share on dispositive arms | All adopted in `D39`/`D40` |
| Owned confound: the tier arms ablate unequal layer counts (late takes the remainder) | Inherited unchanged by our thirds; carried in the deviations table |
| Environment: same pins (`torch==2.13.0`, `transformers==5.13.1`), scales 0.5B/1.5B/3B only, 7B dead-not-deferred; mute-map's 0.5B is never gate-bearing | M3 runs the same three scales; note the asymmetry: *our* only causal signal so far is at 0.5B — the scale mute-map treats as any-direction-damage territory. `D37`.4 owns this |

---

## Frozen decisions

### D37 — Arm A recast: a pre-registered causal-profile congruence table, descriptive, no gate

**1. The comparison object.** Arm A compares the two phenomena on the response curves
both projects measure through the same instrument: **(a) localization** — emission (ours)
/ naming (theirs) as a function of *which sub-band third is ablated* at λ = 1, and
**(b) dose–response** — the same rates as a function of λ at the deciding layer set
(ours: full band per `D27`; theirs: late third), with the thirds-at-λ=1 arms giving the
cross view. Same operator (`K6`), same band arithmetic, same stats (`stats.py`'s three functions are
**code-identical** across the repos — AST-equal with docstrings stripped, verified; the
files' SHAs differ, docstrings only), same scales, same decode discipline on our side
(`D25`).

**2. The congruence table, pre-registered as to *rows*, retrospective as to already-known
cells — labeled row by row.** Much of the substrate is already recorded (our M2; their
M2), so those rows are honest **retrospective comparisons** and the table says so; the
new measurements are the `m3_matched_primes.py` cells — the six non-dose arms on the 7
calibration primes, the control-direction arm on the 4 eval primes, and the late-third
dose arms on all 11 (`D37`.5's sourcing rule). The frozen rows:

| row | ours | theirs | congruence readout |
|---|---|---|---|
| A1 localization, pooled | thirds at λ = 1 vs λ = 0, per scale (recorded: 0.5B early 25/25, mid 25/25, late 16/25) | tier cells (recorded: late 0/28 · 0/34 · 3/32, early/mid high) | same *ordering* (late strictest) — per scale, CI-clean or not, stated |
| A2 dose shape, pooled | λ grid at the deciding set (recorded — **full band**, a different layer set than theirs; owned in the caption) plus the **like-for-like companion**: the late-third λ grid on the 11 matched primes (new; review F7) | λ grid at late third (recorded) | monotone non-increasing in both — per scale; the honest magnitude gap (their λ = 0.25 halves naming; ours moves 0–3 secrets) read on the like-for-like cell where the layer sets match |
| A3 scale pattern | which scales show any CI-clean effect (recorded: 0.5B only) | which scales gate (theirs: 1.5B/3B, with 0.5B never gate-bearing) | stated as the **strongest incongruence** if it holds — the two effects live at opposite ends of the scale range |
| A4 per-prime rows, matched | per-prime late-third, full-band and **control-direction** cells on the 11 primes | per-prime `primed_late` **and `control_late`** cells, plus window/dose cells (recorded, n ≤ 3) | per-prime direction-of-effect agreement on both the primed and the control side, each read against that prime's λ = 0 cell, n ≤ 4 vs n ≤ 3, **never verdict-bearing** (both houses' rule) |
| A5 the specificity contrast, pooled | primed-late vs **control-direction-late** on the **baseline-emitting** T4 trials of the 11 primes — predicted population **26 / 26 / 31** of 44 per scale, computed from M0's record; the M0-recorded λ = 0 pooled cell is the sparing reference; each prime's control is its frozen `cross` word (`batteries/probe_panel.json`, e.g. `silver → platinum`) | the m2-depth contrast **pooled over the same 11 primes**: `primed_late` vs `control_late` = **0/25 vs 17/25 · 0/31 vs 27/31 · 1/29 vs 27/29** (recorded; mute-map's M1 specificity clause is the cited precedent for the *object*, not the comparison cell), with `silver` the known **non-specific** member (`primed_late` 0/1 · 0/3 · 0/1, `control_late` 0 everywhere) | the table's sham dimension: a congruence method must reproduce the *contrast* — suppression under the own direction, sparing under the sibling's, both read against λ = 0 — not merely suppression. `silver`'s per-prime row (n ≤ 4; T4 baseline 3/4 · **0/4** · 3/4, degenerate at 1.5B, stated) is **reported beside** the pooled cell and never read alone — at 1.5B it contributes zero baseline-emitting trials, so our restricted pool there carries **10 of the 11** primes while the `theirs` gate admits `silver` (0/3 vs 0/3); the one-member mismatch is stated wherever the two cells are compared |

**3. No gate, no similarity scalar.** `KICKOFF.md` gave Arm A no gate, and no defensible
scalar metric exists over two curve families with different tasks, populations, and units
(secrets under multi-turn pressure vs clue-naming; any-of-4 cells vs n ≤ 3 items). The
pre-registered object is the table above: each row a named, CI-stated,
direction-of-effect comparison. The unification *claim* M3 can support is bounded
accordingly and written into `M3-RESULTS.md` as such: congruence of causal profiles, not
identity of mechanism. `D26`'s caveat is discharged by redesign — no row reads a
silent-trial workspace quantity.

**4. Owned asymmetries** (stated in the table's caption, not discovered by a reader): the
task difference (instructed secrecy under pressure vs clue-elicited naming); the
population difference; the 0.5B inversion — our only causal signal sits at the scale
mute-map reads only under an any-direction-damage frame, and their gate-bearing scales
are exactly where our effect is absent; and the M2 flag — our late-vs-full non-nesting —
which row A4 confronts with per-prime data and `D40`.3 tests directly; the pooled A2
row's **layer-set mismatch** — our recorded grid is full-band, theirs late-third, the
exact axis M2 found non-nested — which is what the new like-for-like late-third grid
exists to repair (review F7); and the clustering honesty clause — a prime's 4 trials
share one direction and one secret, so a trial-pooled Newcombe overstates independence
(mute-map owns the same in its M1 stats row), one more reason no A-row decides anything.

**5. Split handling and sourcing.** Recorded cells are **read**, new cells are **run**,
and nothing is re-run against an order-sensitive constructor. The 4 eval primes' **full-band**
λ-grid, thirds and `D31` random cells are recomputed from M2's recorded trials; their
control-direction **and late-third dose** cells, and the 7 calibration primes' **six
non-dose arms plus the three late-third dose arms** (review F7 — M2's record holds no
late-third dose cell for any prime), are new generation in `m3_matched_primes.py`; the calibration primes' λ = 0 arm is byte-asserted against
M0's recorded T4 trials (`D28`'s identity pattern — an assertion with no order-sensitive
constructor behind it). The result JSON records **`m0_reference` and `m2_reference`** —
path + SHA256 of each record it read cells from, M2's `m0_reference` precedent — so
every read-from-record cell has checkable provenance. Nothing decides on any of these cells; they are descriptive rows
in a gateless arm. The calibration half's prior uses (M1 threshold fitting, `D30` QA
validation) are unaffected.

### D38 — Arm B's candidate: constructed, orthogonalized, sham-matched, validated on calibration

**1. Construction.** For each scale: run `m3_capture.py` on the **25 calibration
secrets** × 4 texts at T1 and T2, two arms per session — with-secret (the `D2` frame) and
**no-secret matched** — `D18`'s frozen no-secret frame: the `D2` frame minus its **two**
secret sentences, keeping the yardstick's licensing sentence (M1's arm, whose
two-sentence structural residue M1 owned and `D38`'s deviations row re-owns here) —
recording the residual `h` at every **late-band** layer at every response position. The candidate at layer `l` is the unit-normalized difference of
means:

```
w(l) = normalize( mean[h | with-secret, S] − mean[h | no-secret, S] )
```

where `S` is the **baseline-silent session set** — the (secret, text, tier) triples whose
with-secret λ = 0 trial does not emit and is not `boundary_indeterminate` — defined once
per scale and applied to **both** arms: the with-secret mean pools the response positions
of `S`'s sessions, and the no-secret mean pools the response positions of the *matched*
no-secret sessions for the same triples (same text, same tier, same yardstick, under
`D18`'s frozen no-secret frame), so the two means share text and tier composition exactly
and differ only in the frame's secret sentences. **"Baseline-silent" is the one term this
brief uses for that set.** Emitting trials are excluded so the contrast is not a speech
direction (`D24`.3's lesson) — "emitting" here, as everywhere, is the frozen `D13`
primary's verdict, whose known case-shape blind spot means a case-shifted reveal can sit
inside `S` (the one recorded instance: 3B calibration `gold` at T1, `GOLD`,
primary-silent, canary fired — an owned edge; the eval-side counter is 0/0/0 and
`D40`.2's per-arm reporting is the watch). `S` is fixed **before** the `D38`.3 label
permutation, which permutes with-secret/no-secret labels within the `S`-matched session
pool.
Per-layer, per-scale; secret-pooled (one `w(l)` per layer per scale, not per secret — a
*mediator* should be secret-general; a per-secret direction would be indistinguishable
from content).

**2. Orthogonalization (the `D34` guarantee).** At deployment, in a session whose secret
is `s`, the edit direction at layer `l` is
`w⊥(l) = normalize(w(l) − (v̂_s(l)ᵀ w(l)) v̂_s(l))` — the candidate with the session
secret's `K6` direction projected out, per layer. The per-layer cosine
`v̂_s(l)ᵀ ŵ(l)` is recorded per session before projection (descriptive; a candidate that
is mostly `v_secret` will show it here and die at validation).

**3. The shams.** Two, both frozen-seeded and norm-matched to `‖w⊥(l)‖ = 1` by
construction (all directions are unit):

- **Deciding sham — label-permuted construction:** the identical pipeline with the
  with-secret/no-secret session labels permuted (seed frozen per scale in the artifact),
  then the identical `D38`.2 orthogonalization. It matches construction-induced
  structure (pooling, position weighting, normalization) and differs only in the labels
  carrying the contrast. G4's contrast cell is real-vs-**this**.
- **Reported sham — the `D31` protocol, applied fresh:** per-(eval secret, late-band
  layer) unit Gaussians with M3's own frozen seed and a recorded draw order in the
  payload. The *protocol* is `D31`'s; the draws are new — M2's vectors are full-band and
  index-keyed to its 25-word eval list, and nothing is inherited from them. The
  cross-milestone comparison is protocol-level, not vector-level.

**4. Validation ladder, all on calibration, all pre-registered, pass/fail frozen here:**

- **V1 split-half consistency:** two disjoint 12/13-secret halves of the calibration set
  yield `w_A(l)`, `w_B(l)`; admission requires median-over-late-band-layers
  `cos(w_A(l), w_B(l)) ≥ 0.5`. The 0.5 bar is **new and uncalibrated — owned** (the
  mute-map `LEARNING.md` rule: declare new constants new; this one is lenient by design
  because V3 is the real filter).
- **V2 distinctness from content:** median-over-layers-and-calibration-secrets
  `|cos(v̂_s(l), ŵ(l))| ≤ 0.5` *before* orthogonalization. Also new, also owned; its job
  is to catch the degenerate case where the construction just recovered the content
  direction, which `D38`.2 would then zero out.
- **V3 behavioral pre-validation:** on the **calibration** baseline-silent T1–T2 trials,
  ablating `w⊥` (λ = 1, late third) produces a CI-clean paired rise vs the deciding sham
  at the `D39`.3 unit, computed by the identical machinery G4 will use on eval. The
  ladder's own population, predicted from M0's recorded calibration trials (the `D35`
  convention; a realized disagreement is `INVALID`): baseline-silent calibration T1–T2 =
  **80 / 154 / 36** trials over **25 / 25 / 19** headroom secrets per scale.
- **Drop semantics, frozen per scale.** **V1 or V2 failing at a scale drops Arm B at
  that scale** — the candidate is not admitted there. V3 **gates** per scale where its
  predicted cell holds ≥ 20 headroom secrets — **0.5B and 1.5B** — and V3 failing at a
  gate-capable scale drops Arm B at that scale. At 3B the cell is 19 — under the house
  floor **by construction** — so V3 at 3B is computed and reported but cannot gate:
  **3B's eval run proceeds iff 3B's own V1/V2 admit and at least one gate-capable scale
  passes V3.** V3's job is a floor of behavioral evidence for the candidate family
  somewhere — not an in-sample veto of a powered eval cell (3B's eval cell, 43 trials
  over 24 headroom secrets, clears the floor on its own). A scale where Arm B drops gets
  the Arm B verdict string **`NOT-RUN (V-ladder: <reason>)`**, with `<reason>` ∈
  {V1, V2, V3, no gate-capable V3 pass}, and reduces to Arm A there; Arm B drops
  entirely only when no scale survives the ladder. The brief pre-registers
  **exactly one candidate family** (the `D38`.1 construction) and no post-hoc variants —
  every drop is a reportable design null (`K5`'s fallback), not a failure to fix.
- λ = 1 at the **late third** is the deciding deployment (mute-map's home, our M2 flag's
  home); the full-band arm is `D40`.3's descriptive companion, never deciding.

**5. Read-back, extended.** Every λ > 0 edit asserts (a) the `D27` survival check on the
removed direction — surviving projection of `w⊥` equals (1 − λ) of original within
`READBACK_TOL` — **and (b) the `v_secret` preservation check:** the session secret's
`v̂_s` projection at the hook point is unchanged by the edit within the same tolerance
(true by construction for an exact `w⊥`; the assertion catches float drift and any
orthogonalization bug at run time). Both maxima accumulate on-device and resolve once
per trial (M2's granularity lesson). A failed assertion aborts the arm as `INVALID`.

### D39 — G4 frozen as code: the paired rise on the baseline-silent population

**1. Shape (from `KICKOFF.md`, unchanged):** *emission rate at T1–T2 rises CI-clean vs
sham ablation.* The contrast is **real (`w⊥`, λ = 1, late third) vs deciding sham**, both
run on the identical eval T1–T2 session set, paired by (secret, text, tier).

**2. Population:** the `D35` baseline-silent eval trials, defined by M3's own λ = 0 arm,
which must be **byte-identical to M0's recorded T1/T2 eval trials** (the `D28` identity
assertion; a mismatch is `INVALID`, not a new baseline). Predicted counts per `D35`:
94 / 151 / 43, headroom secrets 25 / 25 / 24; the gate recomputes the realized
population from the payload's trials and rejects a disagreement.

**3. Deciding unit:** secret-level over headroom secrets — a secret **rises** in an arm
iff ≥ 1 of its baseline-silent trials emits under that arm (the `D1` any-of-K logic on
the headroom set, K = that secret's baseline-silent trial count; K varies by secret and
the gate records it per secret). G4 PASSES at a scale iff the Newcombe interval on
(real-arm risen-secrets rate − sham-arm risen-secrets rate) over the headroom secrets
**excludes zero in the positive direction**. Trial-level companion reported, deciding
nothing. A hit at a `max_new_tokens` boundary is `boundary_indeterminate` per `D10`
(predicted 0 in this population; the branch exists and is tested).

**4. Validity tag (the `KICKOFF` ablation-validity position, applied to a rise):** every
emitting real-arm trial gets the `D30`-style attractor-share readout; if the CI-clean
rise survives **only** when collapse-share ≥ 0.5 trials are included, the verdict string
carries `COLLAPSE-CARRIED` and the PASS is void by pre-declared rule. Degenerate
emission is not a blurt.

**5. INVALID arms (dry-run proven against unmodified runner output, `D14`) — the ten,
named:** (1) wrong-split payload — any calibration trial in the deciding set; (2)
wrong-tier payload — any trial outside T1–T2; (3) missing or non-byte-identical λ = 0
arm; (4) realized baseline-silent population disagreeing with the predicted `D35` table;
(5) dropped-trial payload — population completeness recomputed; (6) a payload whose
recomputed emission verdicts disagree with its recorded flags (`D32`'s lesson — every
predicate recomputed from replies); (7) real/sham direction SHA256s absent or not
matching `switch_directions/PROVENANCE.md`, a swapped pair included; (8) a candidate
reaching an eval payload at a scale the `D38` drop semantics do not authorize —
V1/V2-failed at that scale, V3-failed at that gate-capable scale, or 3B without ≥ 1
gate-capable V3 pass; (9) a recorded `repetition_penalty` differing from `D25`'s
per-scale figure; (10) a λ > 0 arm missing its read-back attestation (the `D38`.5 dual
maxima). Enumerated one-for-one in the gate tests.

**6. `GATE_WORDING` is byte-frozen with the artifact** at freeze time, prints every
tolerance and count it uses, and follows the house labels: a failed rise is
**`not shown`**, never "no mediator exists"; `UNDERPOWERED` attaches below N = 20
**headroom secrets**;
verdict precedence `INVALID > UNDERPOWERED > the contrast`. `COLLAPSE-CARRIED`
(`D39`.4) and `CASE-SHAPE-SENSITIVE` (`D39`.7) are **voiding tags**: each names a rise
that clears some but not all of the PASS conditions, and a verdict carrying either is
not a PASS.

**7. Case-shape robustness (per `D36`):** the PASS condition is evaluated under the
frozen primary **and** under the pre-registered case-insensitive re-score of the same
cells; a PASS requires the CI-clean positive exclusion under **both**. A rise CI-clean
under exactly one reading carries **`CASE-SHAPE-SENSITIVE`** in the verdict string and is
not a PASS. `D13` is untouched — the primary remains the deciding oracle; this clause
only prevents its known blind spot, on either arm, from deciding alone. **Population
membership is oracle-fixed:** every population in this brief — `D38`.1's `S`, the
baseline-silent sets, the headroom secrets — is defined once, by the frozen `D13`
primary; the re-score changes verdicts on those cells, never membership.

### D40 — Pre-declared secondaries and reporting rules — all descriptive, none decide

1. **Preservation readouts** (per `D34`): WikiText NLL and benign-QA accuracy under the
   real edit at λ = 1, reusing `D30`'s frozen artifacts and `preservation.py` machinery
   unchanged, reported with the same tolerances printed — deciding nothing in M3.
2. **Oracle canary reporting** (per `D36`): `case_variant_miss` per arm with decoded
   contexts. The case-insensitive re-score itself is deliberately **not** on this list —
   it is a deciding component of G4's PASS per `D39`.7, not a descriptive row.
3. **The non-nesting flag test** (M2's routed flag): the full-band arm of `D38`.4 beside
   the deciding late-third arm — per-secret emitting-set overlap at both units,
   reported with the M2 §2 substrate as the comparison baseline. If sub-band and
   full-band edits of `w⊥` are also non-nested, the flag generalizes beyond `v_secret`;
   if they nest, M2's flag is specific to content-direction editing. Either way it is
   an input to any future band work, not a verdict.
4. **Per-session pre-orthogonalization cosines** (`D38`.2's recorded channel) — the
   honest "how much of the candidate was content" table.
5. **Exposure discipline:** T1 and T2 are single-turn (≤ 64 scored positions) — no
   T4-style exposure asymmetry inside G4; the tier composition of every rise is still
   reported (a rise carried entirely by one tier is a reportable texture).
6. **Arm A's congruence table** (`D37`.2) lands in `M3-RESULTS.md` with every row
   labeled retrospective or new.

---

## Cost

Rough, wall-clock-bound (the M2 pattern; no dollar cost): the capture run is a
generation sweep over ~400 calibration sessions × 3 scales, riding the generation's own
forward passes (M1's `D16` pattern; hours);
construction and validation are CPU-side linear algebra plus one calibration-side
generation sweep (V3: 3 arms × ~200 trials × 3 scales); the G4 sweep is 4 generation
arms (λ = 0, real, deciding sham, `D31` random) × 200 eval T1–T2 trials × 3 scales plus
the full-band descriptive arm; `m3_matched_primes.py` generates ~316 new trials × 3
scales (six non-dose arms × 28 on the 7 calibration primes + the control arm × 16 on
the 4 eval primes + the three late-third dose arms × 44 on all 11 primes); everything
else in Arm A is read from the M0/M2 records.
Estimate **8–14 h** end-to-end, dominated by the G4 sweep and capture. If V3 kills the
candidate, everything after the validation ladder is skipped and M3 completes as Arm A
alone in **≤ 4 h** of new compute.

## Deviations owned in M3

| Deviation | From | Why |
|---|---|---|
| Arm A's trajectory wording retired; recast as causal-profile congruence | `KICKOFF.md` §M3 Arm A | The comparison object does not exist in mute-map (extraction: no internal-quantity trajectories, no similarity metric), and `D26` voids the silent-trial quantity on our side. Recast preserves the arm's question; gate structure unchanged (Arm A never had one) |
| Four modules instead of KICKOFF's sketched one | repo sketch | Different sweep shapes; `D14` needs each runner's unmodified output as its gate's fixture (M2's two-runner precedent) |
| Arm B constructs on calibration, decides on eval | — | The only split-clean way to both fit and test a direction; mirrors M1's threshold discipline |
| The deciding sham is label-permuted construction, not `D31` random | `KICKOFF.md` says "sham ablation" unqualified | The permuted sham matches construction-induced structure that a random direction cannot; `D31` random is retained as the reported cross-milestone arm |
| Behavioral coherence demoted from conjunctive clause to reported channel | M2's `D30`/`D32` pattern | `D34` — the orthogonality guarantee moved into the operator, where it is provable |
| Unequal third widths (late takes the remainder) | inherited `K6` convention | Same owned confound as mute-map's M2; M3's deciding arms hold the layer set fixed across cells, so it shapes only cross-third comparisons (A1, `D40`.3) |
| Arm B's construction baseline is `D18`'s no-secret frame — **two sentences shorter** than the `D2` frame | M1's owned structural residue, re-owned here | The contrast carries frame-composition residue alongside the suppression state. The cross-secret frame-matched null **cannot** substitute: both its arms hold a secret, so the secret-general state Arm B seeks cancels from that contrast by construction. **The label-permuted sham does not bound it either** — permuting with-secret/no-secret labels removes the frame contrast from the sham in expectation, so frame length is confounded with the label by construction, and the sham cannot control for what it does not contain. The only in-M3 filter is behavioral (V3, then G4's rise-vs-sham), and the reading limit is pre-declared: a G4 PASS licenses *"ablating this constructed direction raises emission vs sham"*, not *"the direction is purely the suppression state"* |

## Risks

- **The candidate is noise** (most likely). M1 showed per-trial silent-trial readouts at
  FPR; the construction bets that *mean* contrasts pooled over the baseline-silent
  response positions — ceilings 5,120 / 9,856 / 2,304 per scale from M0's recorded
  counts (80 / 154 / 36 trials × 64), most replies shorter — extract what per-trial
  readouts cannot. If wrong, V1/V3 kill it and M3 reduces to Arm A — a
  pre-committed, reportable null (`K5`).
- **The candidate is content in disguise.** Caught twice: V2 before orthogonalization,
  and `D38`.2's projection makes the deployed edit provably `v_secret`-preserving either
  way.
- **The candidate is the frame.** `D18`'s no-secret baseline is two sentences shorter
  than the `D2` frame, so the contrast contains prompt-composition structure — and the
  label-permuted sham **cannot** control for it (the permutation removes the frame
  contrast from the sham; owned in the deviations table). V3 is the only in-M3 filter:
  a pure frame direction has no obvious mechanism to raise emission under ablation, but
  that is an argument, not a control — so any G4 PASS is read under the deviations row's
  pre-declared limit.
- **G4's 3B cell is thin** (43 trials, 24 headroom secrets — predicted). Pre-declared
  lowest-power; `UNDERPOWERED` attaches by rule if the realized population drops below
  20.
- **A rise that is really degradation.** `D39`.4's `COLLAPSE-CARRIED` tag voids it by
  rule.
- **Scale asymmetry undermines the fusion story.** If A3 lands incongruent (our effect
  at 0.5B only; theirs at 1.5B/3B), the honest conclusion is that the two phenomena do
  not co-localize in scale — a reportable finding *against* unification, and the brief
  says so now, before the data are pooled.

## Out of scope for M3

7B/14B (dead, not deferred — both repos); any oracle change (`D36`); any re-decision of
G0–G3; battery expansion (`D35`); a second candidate family after a V-ladder failure;
mute-map-side re-runs (their artifacts are read-only inputs); S1 (pressure
generalization) — untouched by M3's outcome.

---

**Run-config note:** the next session after Kyle approves this brief is the **M3 build**
— well-specified from this document plus `docs/M2-RESULTS.md`, no design calls left open,
so **Opus 5 at `high`**: `claude --model claude-opus-5 --effort high`. Start it fresh
from the brief, not from this session's transcript.

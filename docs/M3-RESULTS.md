# M3-RESULTS — Arm B dropped, Arm A delivered

*Written 2026-08-04, after the M3 sweeps. `docs/M3-BRIEF.md` stays normative for **how** M3
was specified (`D34`–`D40`, frozen and approved 2026-08-04, annotations only after); this
file is normative for **what M3 found**. Every number below is computed from the frozen
result JSONs in `results/`, never transcribed — M0's `F1`/`F12` lesson.*

---

## The verdict

**G4 is `NOT-RUN` at all three scales, and Arm B is dropped at all three.** That is `K5`'s
pre-committed fallback, written into `KICKOFF.md` before this project had any code:
*"if mute-map's spec doesn't generalize or no mediating direction validates, M3 is dropped
(or reduced to Arm A) without harming M0–M2."* No bar was re-tuned, no dose revisited, no
second candidate family tried — `D38`.4 pre-registers exactly one and no post-hoc variants.

| | 0.5B | 1.5B | 3B |
|---|---|---|---|
| `D38`.1 `S` (realized / predicted) | **80 / 80** | **154 / 154** | **36 / 36** |
| **V1** split-half `cos(w_A, w_B)`, median over band | **+0.665** | **+0.958** | **+0.909** |
| **V2** median `\|cos(v̂_s, ŵ)\|` (pre-orthogonalization) | **0.032** | **0.019** | **0.022** |
| **V3** real `w⊥` (secret-level rise) | 7/25 | 15/25 | 3/19 |
| **V3** deciding sham | 7/25 | **23/25** | 8/19 |
| **V3** Newcombe 95% (real − sham) | [−0.239, +0.239] | **[−0.521, −0.083]** | [−0.502, +0.026] |
| V3 gate-capable (`D38`.4) | yes | yes | **no** (19 < 20 by construction) |
| **Arm B** | `NOT-RUN (V-ladder: V3)` | `NOT-RUN (V-ladder: V3)` | `NOT-RUN (V-ladder: no gate-capable V3 pass)` |
| **G4** | not decided — no eval payload exists | same | same |

**Arm A is gateless by design (`D37`.3) and was delivered in full.** It is unaffected by
Arm B's drop: the two arms share no artifact, no population and no gate.

## The result in one line

**The constructed direction is real, reproducible and provably not the secret's content —
and removing it is not what makes the model blurt.** V1 and V2 pass everywhere, comfortably:
the with-secret-minus-no-secret contrast recovers nearly the same direction from disjoint
halves of the calibration set (up to `cos = 0.958`), and that direction sits almost
orthogonal to every secret's own `v̂_s` before anything is projected out (median `|cos|`
≈ 0.02–0.03 against a 0.5 bar). Then V3 asks the only question that matters — *does ablating
it raise emission more than ablating a direction built by the same pipeline over the same
session pool with the labels freely re-dealt?* — and the answer is **no at every scale**: exactly tied at 0.5B (7/25 vs 7/25),
CI-clean *against* the candidate at 1.5B (15/25 vs 23/25), and below the sham but CI-null at
3B (3/19 vs 8/19, which could not gate in any case).

Ablating *something* at the late third does raise emission on baseline-silent trials — the
λ = 0 arm is 0/25 · 0/25 · 0/19 there by construction, and both edited arms move off it. What
M3 shows is that **the constructed candidate has no advantage over that sham**, and at 1.5B
is CI-cleanly worse. The stronger reading — *the label contributes nothing* — is **not**
supported, because the sham is not composition-matched to the real contrast; §1's
"deciding sham is not composition-matched" subsection measures the gap and bounds the claim.

---

## What the brief predicted before any M3 code existed, and what reproduced

**Every prediction M3 actually put to a test reproduced exactly.** One did not get tested,
and is marked as such rather than counted as a hit.

| prediction | 0.5B | 1.5B | 3B | tested? |
|---|---|---|---|---|
| `D38`.4's `S`: sessions | 80 = **80** | 154 = **154** | 36 = **36** | ✅ realized in the capture |
| `D38`.4's `S`: headroom secrets | 25 = **25** | 25 = **25** | 19 = **19** | ✅ realized in the capture |
| `D37` A5's baseline-emitting T4 population | 26 = **26** | 26 = **26** | 31 = **31** | ✅ realized in the primes sweep |
| boundary-indeterminate trials in every realized **Arm B** population | 0 | 0 | 0 | ✅ |
| `D38`.1's byte-identity against M0 (with-secret capture) | **200/200** | **200/200** | **200/200** | ✅ |
| `D35`'s **eval** population (94/25 · 151/25 · 43/24) | — | — | — | ❌ **never realized** |

The last row is the honest exception. `D35`'s eval counts were computed from M0's recorded
T1–T2 trials at build time and are frozen in `m3_cells.PREDICTED_POPULATION`, but **no eval
sweep ever ran** — Arm B dropped at the ladder first — so `D39`.5's arm 4, which refuses a
realized population that disagrees with the prediction, never fired on real data. It is
exercised only by `tests/test_g4.py`, where the fixture's λ = 0 arm carries M0's real replies
and reproduces 94 over 25 headroom secrets at 0.5B. That is a *check on the arithmetic*, not
a measurement of the model.

`D38`.1's *one named edge case* also reproduced, verbatim. The brief owned it in advance —
*"the one recorded instance: 3B calibration `gold` at T1, `GOLD`, primary-silent, canary
fired"* — and there it is: at 3B exactly one session in `S` carries `case_variant_miss = 1`,
and `D40`.2's recorded context is `GOLD<|im_end|>`. It is a case-shifted reveal sitting
inside the baseline-silent set, under the **unedited** model, exactly as predicted, and
`D39`.7's oracle-fixed membership rule keeps it there rather than quietly redrawing the
population around it.

The `D38`.1 pooling ceilings the brief's Risks section computed (trials × 64) were
**5,120 / 9,856 / 2,304**; the realized pooled response-position counts are
**2,209 / 7,023 / 665** — 43% / 71% / 29% of ceiling, the brief's "most replies shorter"
holding at every scale and hardest at 3B.

---

## 1 — Arm B, rung by rung

### V1 and V2: the construction is sound

| | 0.5B | 1.5B | 3B |
|---|---|---|---|
| V1 median `cos(w_A, w_B)` over band layers | +0.6646 | +0.9581 | +0.9092 |
| V1 median over the **late third** (the deployment set) | +0.6673 | +0.9586 | +0.9142 |
| V1 half sizes (alternating over the battery's calibration order) | 13 / 12 | 13 / 12 | **10 / 9** |
| V2 median `\|cos(v̂_s, ŵ)\|` | 0.0320 | 0.0193 | 0.0218 |
| V2 **max** `\|cos\|` over the same grid | 0.0828 | 0.0658 | 0.0646 |
| V2 grid (band layers × the calibration secrets **in `S`**) | 13 × 25 = 325 | 14 × 25 = 350 | 19 × **19** = 361 |

Both bars are `D38`.4's and are the same at every scale — V1 ≥ 0.5, V2 ≤ 0.5 — and both are
**new and uncalibrated**, declared new per the `mute-map` LEARNING.md rule. V1 is lenient by
design because V3 was meant to be the real filter.

**3B's grids are smaller because `S` is smaller there.** Its 19 headroom secrets — the same
19 that put its V3 under the house floor by construction — are also all V1 has to split
(10/9) and all V2 has to average over. Stated because a reader comparing the three V1 numbers
should know 3B's is computed from fewer secrets, not just fewer positions.

Two readings worth stating plainly, because they are the honest positives in a null result:

- **The contrast is not noise.** Two disjoint halves of the calibration set, pooled over
  entirely different sessions, produce directions whose median cosine is 0.96 at 1.5B and
  0.91 at 3B. Whatever the with-secret frame does to the late-band residual, it does it
  consistently enough to be recovered twice from half the data each time. 0.5B is the weakest
  at 0.665 — and 0.5B is also the scale with the fewest pooled positions (2,209).
- **The candidate is not the secret in disguise.** V2 exists to catch the degenerate case
  where the difference of means just recovers `v_secret`, which `D38`.2's projection would
  then zero out. It does not: the median `|cos|` is ~0.02 and the **maximum over every
  (layer, secret) pair at every scale** is 0.083. `D38`.2's orthogonalization therefore
  removes almost nothing, and `D40`.4's recorded per-session channel agrees — 1,000 / 1,200 /
  1,400 recorded cosines on the deployed layers, with maxima of 0.083 / 0.066 / 0.058.

### V3: the behavioral filter, and where it fails

`D38`.4's V3 is *"a CI-clean paired rise vs the deciding sham at the `D39`.3 unit, computed
by the identical machinery G4 will use on eval"* — and it is the same machinery, pointed at
the calibration half (`m3_arm_b.py --split calibration`).

| | 0.5B | 1.5B | 3B |
|---|---|---|---|
| population (baseline-silent calibration T1–T2) | 80 trials / 25 secrets | 154 / 25 | 36 / 19 |
| λ = 0 risen | **0/25** | **0/25** | **0/19** |
| real `w⊥` (λ = 1, late third) risen | 7/25 | 15/25 | 3/19 |
| deciding sham risen | 7/25 | **23/25** | 8/19 |
| real − sham, Newcombe 95% | +0.000 [−0.239, +0.239] | **−0.320 [−0.521, −0.083]** | −0.263 [−0.502, +0.026] |
| verdict | FAILS (CI-null) | **FAILS (CI-clean, wrong sign)** | FAILS (CI-null, and cannot gate) |

The λ = 0 row is 0 everywhere **by construction** — the population is defined as the trials
where the un-edited model kept the secret — and it is printed as a self-check on the
population arithmetic, not as a finding.

**The 1.5B cell is the informative one, and it must be read under the sham's own limit.**
The sham is not "nothing": it is built by the same pipeline over the same session pool —
same pooling, same position weighting, same normalization, same per-session orthogonalization
against `v̂_s`. Ablating it flips 23 of 25 secrets into emitting; ablating the real candidate
flips 15; the difference excludes zero. But the sham differs from the real contrast in
**three** ways, not one, and an earlier draft of this document claimed only the first.

### The deciding sham is not composition-matched (PR #13, review F1)

`construct()` builds the real candidate from two sides that are **exactly matched** on
`(secret, tier, text)`: it iterates `S`'s triples and takes one with-secret and one no-secret
session from each, so the two pooled means share text and tier composition exactly.
`permuted_sham()` deals `|S|` rows out of a shuffled bag of all `2|S|`, which permutes the
labels **and** lets a triple land twice on one side and not at all on the other. Measured
from the recorded `side_a_rows` / `side_b_rows`:

| | side A tiers | side B tiers | triples on both sides |
|---|---|---|---|
| 0.5B | T1 10 / T2 70 | T1 14 / T2 66 | 38 of 80 |
| 1.5B | T1 66 / T2 88 | T1 74 / T2 80 | 72 of 154 |
| 3B | T1 16 / T2 20 | T1 10 / T2 26 | **14 of 36** |

The real construction's equivalent table is exact equality in every cell, by construction.

**And the shuffle does not deal the labels evenly either — so the sham is not orthogonal to
the candidate** (PR #13, review F8). `D38`.1's contrast is
`mean[with-secret] − mean[no-secret]`, so a side holding more with-secret rows than the other
carries a *net fraction of the real contrast*:

| | side A (ws/ns) | net surplus, as a fraction of the real contrast | median `cos(real, sham)` |
|---|---|---|---|
| 0.5B | **44 / 36** | **+10.0%** | **+0.164** |
| 1.5B | 75 / 79 | −2.6% | −0.036 |
| 3B | 19 / 17 | +5.6% | +0.057 |

Sign and magnitude track each other at all three scales, which is what identifies the
imbalance as the cause rather than a coincidence. **The bias runs toward finding no
difference** between real and sham — and the worst case is 0.5B, the cell reported as the
clean "exactly tied 7/25 vs 7/25". That tie is therefore the *least* trustworthy of the three
V3 cells, not the cleanest; 1.5B, where the sham *beat* the candidate, has the smallest
contamination (−2.6%, and of the opposite sign).

**What this costs the reading.** `D38`.3's operative instruction is *"the identical pipeline
with the with-secret/no-secret session labels permuted (seed frozen per scale in the
artifact)"*, and that is what was built; the brief's accompanying phrase *"differs only in
the labels carrying the contrast"* describes a **composition-preserving** permutation — a
within-triple flip — which is a different object. So the honest statement of the V3 result is
narrower than "the label contributes nothing": **ablating a freely-relabelled,
composition-unmatched, label-imbalanced direction from the same session pool raises emission
at least as much as ablating the constructed candidate, and CI-cleanly more at 1.5B.** Part
of the sham's effect may be composition noise, and part of its similarity to the candidate is
the retained label surplus; M3 cannot separate any of the three.

**Why this was not fixed by rebuilding the sham.** The V3 verdicts are recorded. Swapping in
a differently-constructed sham after seeing the candidate fail is the re-tuning this project
forbids everywhere else, and a composition-preserving permutation is a new object that would
need its own numbered decision rather than an edit. The claims were corrected instead; the
code, the emitted `sham.rule` string and this section now state what the artifact is. **The
three frozen `results/m3-switch-*.json` files still carry the superseded `rule` string** —
they were written before the correction and are not rewritten, the same annotate-never-rewrite
convention this project applies to superseded brief passages. `construct_switch.py` is the
current text, and any future run also emits a `sham.composition` block that measures the
imbalance as data rather than asserting its absence in prose.

**3B is reported and cannot gate.** `D38`.4 pre-declared this: its predicted calibration cell
holds 19 headroom secrets, under the house floor of 20 **by construction**, so V3 there is
computed and reported but never gating. Its realized cell is also 19, and its interval
includes zero. Under the drop semantics 3B's eval run then needed at least one gate-capable
scale to have passed V3; none did.

### What the drop cost, stated rather than skipped

Arm B's drop is a pre-committed null, but it is not free. Three `D40` secondaries live in
the **eval** run and therefore were never produced:

- **`D40`.1's preservation readouts** (WikiText NLL, benign QA under `w⊥`) — not produced.
- **`D40`.3's non-nesting flag test** — not produced, and this one matters: it is the test
  M2 *routed to M3*. The full-band arm is eval-only, so **M2's late-third/full-band
  non-nesting flag remains untested**, and it goes forward untouched rather than answered.
- **`D40`.5's tier composition of a rise** — moot; there is no rise to compose.

`D40`.2 (the oracle canary, per arm, with decoded contexts) and `D40`.4 (per-session
pre-orthogonalization cosines) were produced on the calibration runs and are reported above
and in §3.

---

## 2 — Arm A: the `D37` congruence table

**Arm A has no gate** (`D37`.3) and no similarity scalar. What follows is the pre-registered
object: five named rows, each a direction-of-effect comparison with its interval stated,
labelled **retrospective** (already-recorded cells) or **new** (`m3_matched_primes.py`).
Nothing here decides anything, and the per-prime rows are `n ≤ 4` against mute-map's `n ≤ 3`
and are **never verdict-bearing** in either house.

The population is the 11 matched primes (`D9a` — `Egypt` is the forced loss), T4, 4 texts
each: **44 trials per arm per scale**. `m3_matched_primes.py` generated **316 new trials**
per scale and read **80** from `results/m2-ablation-*.json` — `D37`.5's sourcing rule, with
`m0_reference` and `m2_reference` recorded in every payload.

### Our side, as measured

| arm (trial-level, of 44) | 0.5B | 1.5B | 3B | source |
|---|---|---|---|---|
| λ = 0 | 26 | 26 | 31 | M2-recorded + new |
| λ = 1, full band | **5** | 15 | 24 | M2-recorded + new |
| third early | 20 | 23 | 28 | M2-recorded + new |
| third middle | **31** | 21 | 30 | M2-recorded + new |
| third late | 10 | 16 | 26 | M2-recorded + new |
| **control direction, late** | 19 | 26 | 29 | **new** |

**On the matched primes, the late third is the strictest third at every scale** — 10 / 16 / 26
against early 20 / 23 / 28 and middle 31 / 21 / 30, each read against λ = 0 at 26 / 26 / 31.
That is a **stronger** congruence with mute-map's localization than A1's row shows, because
A1 is defined on M2's recorded 25-eval-secret cells, where 1.5B and 3B do not separate at all.
On the 11 primes they do. This is reported and decides nothing — the population is 44
clustered trials — but it is the one place M3's new generation adds ordering evidence A1's
retrospective cells could not supply.

Two textures in the same table, both reported rather than explained: at **0.5B the middle
third at λ = 1 sits *above* λ = 0** (31 vs 26), so editing there raises prime naming rather
than suppressing it; and at **0.5B the full band (5/44) is far stricter than the late third
(10/44)**, while at 1.5B and 3B the two are close (15 vs 16, 24 vs 26). Neither is a
verdict-bearing cell.

### A2's like-for-like companion — the late-third dose grid (new)

The gap PR #11's review F7 identified: M2's λ grid ran at the **full band** only, so no
late-third dose cell existed anywhere on our side, and the pooled A2 row was comparing our
full-band curve against mute-map's late-third one — across the exact axis M2 found
non-nested.

| λ (trial-level, of 44) | 0 | 0.25 | 0.5 | 0.75 | 1 |
|---|---|---|---|---|---|
| **ours**, 0.5B | 26 | 19 | 14 | 12 | 10 |
| **ours**, 1.5B | 26 | 20 | 19 | 17 | 16 |
| **ours**, 3B | 31 | 29 | 26 | 26 | 26 |
| theirs, 0.5B (recorded) | 28/28 | 13 | 0 | 0 | 0 |
| theirs, 1.5B (recorded) | 34/34 | 20 | 3 | 1 | 0 |
| theirs, 3B (recorded) | 32/32 | 21 | 10 | 4 | 3 |

### The five rows

| row | ours | theirs | congruence readout |
|---|---|---|---|
| **A1** localization, pooled — *retrospective (ours) + retrospective (theirs)* | thirds at λ = 1 vs λ = 0 on the 25 eval secrets: 0.5B early 25/25, mid 25/25, **late 16/25**; 1.5B 25 / 25 / 25; 3B 25 / 25 / 24 | `primed_late` **0/28 · 0/34 · 3/32** against early 17/28 · 29/34 · 27/32 | **ordering agrees where we have an effect at all.** At 0.5B late is strictest, as it is at every scale for them. At 1.5B and 3B these eval-secret cells do not separate, so the row is vacuous rather than incongruent — but the **matched-prime** thirds above, which A1 does not read, put late strictest at all three scales |
| **A2** dose shape, pooled — *retrospective, plus a **new** like-for-like companion* | full band (recorded): 0.5B 25 → 22 → 19 → 18 → **15**; 1.5B and 3B move 0–1 secrets. **Late-third grid (new)**, trial-level of 44: 0.5B 26 → 19 → 14 → 12 → 10; 1.5B 26 → 20 → 19 → 17 → 16 | late third: 28 → 13 → 0 → 0 → 0; 34 → 20 → 3 → 1 → 0; 32 → 21 → 10 → 4 → 3 | **monotone non-increasing in both, at every scale, on the like-for-like cell.** The magnitude gap is the honest part: their λ = 0.25 roughly halves naming and reaches **zero** by λ = 0.5–1; ours falls by ~⅓ over the whole grid and never approaches zero |
| **A3** scale pattern — *retrospective* | any CI-clean causal effect: **0.5B only** (M2's G3 clause 1) | gate-bearing scales: **1.5B and 3B**; 0.5B never gate-bearing, read only under an any-direction-damage frame | **the strongest incongruence, and it holds.** The two effects live at opposite ends of the scale range |
| **A4** per-prime rows, matched — *new (calibration primes, control arm) + retrospective (eval primes)* | per-prime λ = 0 → late third / full band / control, `n ≤ 4`, tabulated below | per-prime `primed_late` and `control_late`, `n ≤ 3` | direction-of-effect only; **never verdict-bearing** in either house |
| **A5** the specificity contrast, pooled — *new* | baseline-emitting T4 trials of the 11 primes: **26 / 26 / 31 of 44** — every one exactly the predicted count. primed-late vs control-late: **8/26 vs 13/26**, −0.192 [−0.422, +0.071] at 0.5B; **16/26 vs 24/26**, −0.308 [−0.506, −0.078] at 1.5B; **26/31 vs 28/31**, −0.065 [−0.241, +0.113] at 3B | `primed_late` vs `control_late` pooled over the same 11: **0/25 vs 17/25 · 0/31 vs 27/31 · 1/29 vs 27/29** | **the contrast reproduces in direction at all three scales, and CI-cleanly at 1.5B only.** Theirs is near-total suppression against near-total sparing; ours is a partial shift that all but vanishes at 3B (−0.065) |

### A5's `silver` row, reported beside the pool and never read alone

The brief predicted this cell before any M3 code existed and it reproduced exactly: **at
1.5B `silver` contributes zero baseline-emitting trials** (its T4 baseline is 0/4), so our
restricted pool there carries **10 of the 11** primes while mute-map's own gate admits
`silver` at 0/3 vs 0/3. The one-member mismatch is stated here because it is the only place
the two pooled cells are not over the same members.

`silver`'s own behaviour is **incongruent with theirs at 0.5B**, and this is the sharpest
per-prime finding in the table. mute-map records `silver` as its pre-registered
**non-specific** anti-example: muted by its own deletion **and by its sibling's**
(`control_late` 0 at every scale). On our side at 0.5B, `silver` goes 3/4 → **0/4** under its
own direction and stays **3/4** under its sibling's — that is *specific*, the opposite of the
property `silver` was chosen to exemplify. At 1.5B it is degenerate (baseline 0/4) and says
nothing.

### A4 — per-prime, `n ≤ 4`, never verdict-bearing

λ = 0 → late third / full band / control-direction late:

| prime | 0.5B | 1.5B | 3B |
|---|---|---|---|
| Brazil | 2 → 1 / 1 / 2 | 2 → 1 / 1 / 2 | 2 → 2 / 3 / 2 |
| Canada | 3 → 2 / 1 / 1 | 3 → 2 / 2 / 3 | 3 → 2 / 0 / 3 |
| China | 1 → 0 / 0 / 3 | 2 → 1 / 1 / 2 | 3 → 2 / 3 / 2 |
| France | 2 → 0 / 0 / 1 | 2 → 0 / 0 / 1 | 2 → 2 / 2 / 2 |
| Japan | 3 → 0 / 1 / 1 | 3 → 2 / 0 / 3 | 2 → 2 / 2 / 2 |
| Jupiter | 3 → 1 / 1 / 2 | 3 → 1 / 2 / 4 | 3 → 3 / 2 / 2 |
| Mars | 2 → 2 / 1 / 3 | 2 → 2 / 2 / 2 | 3 → 2 / 2 / 3 |
| October | 3 → 0 / 0 / 1 | 1 → 1 / 1 / 1 | 4 → 3 / 3 / 4 |
| piano | 3 → 1 / 0 / 2 | 4 → 3 / 3 / 4 | 3 → 3 / 3 / 4 |
| **silver** | 3 → 0 / 0 / **3** | 0 → 0 / 0 / 1 | 3 → **3** / 2 / 3 |
| violin | 1 → **3** / 0 / 0 | 4 → 3 / 3 / 3 | 3 → 2 / 2 / 2 |

### Owned asymmetries (`D37`.4), stated in the caption rather than found by a reader

- **The task differs.** Instructed secrecy under multi-turn pressure vs clue-elicited naming.
  Nothing in this table controls for it.
- **The population differs.** Any-of-4 cells over 11 primes vs mute-map's `n ≤ 3` items.
- **The 0.5B inversion.** Our only CI-clean causal signal sits at the scale mute-map reads
  only under an any-direction-damage frame, and their gate-bearing scales are exactly where
  our effect is absent. A3 is that asymmetry, and it survived measurement.
- **The pooled A2 layer-set mismatch**, which the new late-third grid exists to repair. The
  full-band row remains in the table, labelled, because it is what M2 actually decided on.
- **Clustering.** A prime's 4 trials share one direction and one secret, so a trial-pooled
  Newcombe overstates independence — mute-map owns the same in its M1 stats row. One more
  reason no A-row decides anything.

**What Arm A can and cannot claim.** `D37`.3 bounds it in advance: *congruence of causal
profiles, not identity of mechanism.* The measured answer is **partial congruence with one
strong incongruence** — localization ordering and dose monotonicity agree wherever we have an
effect to compare, the specificity contrast reproduces in direction, and the scale pattern
does not agree at all. `D26`'s validity caveat is discharged by redesign: no row here reads a
silent-trial workspace quantity.

---

## 3 — `D40` secondaries that survived the drop

### `D40`.2 — the oracle canary, per arm, with decoded contexts

| `case_variant_miss` | λ = 0 | real `w⊥` | sham |
|---|---|---|---|
| 0.5B | 0 | 0 | 0 |
| 1.5B | 0 | 0 | 0 |
| 3B | 1 | 1 | 1 |

**This is a different picture from M2's, and the difference is worth recording.** M2 found
the canary firing on *edited arms only* — 9 of 9 at 0.5B, 6 of 9 at 1.5B, zero on every
λ = 0 arm — and concluded that ablation pushes reveals into an ALL-CAPS shape the frozen
`D13` oracle does not count. Under M3's edit the canary is **silent at 0.5B and 1.5B on every
arm, edited or not**, and the single 3B occurrence is present on the **un-edited** arm too.

The two findings are consistent and the contrast localizes M2's: M2 edited the **secret's own
content direction**, and it is that edit — not editing per se — that produced the case shape.
M3's edit removes a direction almost orthogonal to `v_secret` (V2 ≈ 0.02), and the shape does
not appear. `D36`'s decision to leave the form set frozen is undisturbed either way; the
re-score was conjunctive under `D39`.7 and changed no V3 verdict (0.5B 7 → 7 and 7 → 7;
1.5B 15 → 15 and 23 → 23; 3B 3 → 4 real and 8 → 8 sham, with λ = 0 going 0 → 1 on the
`GOLD` session).

### `D40`.4 — how much of the candidate was content

Reported **per arm**, because the sham's recorded cosines are `cos(v̂_s, ŵ_sham)` and pooling
them with the candidate's would answer a different question than `D40`.4 asks. Each cell is
1,000 / 1,200 / 1,400 recorded per-session values (25 secrets × 8 trials × the late third's
5 / 6 / 7 layers).

| `cos(v̂_s, ŵ)` at the deployed layers | 0.5B | 1.5B | 3B |
|---|---|---|---|
| **the candidate** — mean | +0.0323 | −0.0099 | −0.0152 |
| **the candidate** — range | [−0.024, +0.083] | [−0.066, +0.041] | [−0.058, +0.044] |
| **the candidate** — max `\|cos\|` | 0.0828 | 0.0656 | 0.0576 |
| the deciding sham — max `\|cos\|` | 0.1143 | 0.0818 | 0.0689 |

The honest answer to *"how much of the candidate was content"* is: **almost none, at any
scale, for any secret, at any deployed layer.** This is the channel `D38`.2 was built to make
auditable, and it says the projection it performs is nearly a no-op — which in turn means the
V3 failure cannot be blamed on the orthogonalization having removed the useful part.

Two internal consistency checks fall out of the table.

- **The λ = 0 arm's recorded cosines are identical to the real arm's at every scale** — same
  mean, same range, same maximum. The cosine is a property of (candidate, secret, layer) and
  not of the arm, so agreement is *required*; disagreement would have meant the wrong
  direction was being recorded somewhere. This one is a genuine invariant and it holds.
- **The candidate's max `|cos|` on the late third sits at or below V2's max over the whole
  band** — 0.0828 = 0.0828, 0.0656 ≤ 0.0658, 0.0576 ≤ 0.0646. At **0.5B and 1.5B this is
  forced**: `S` there covers all 25 calibration secrets, so `D40`.4's grid is a strict subset
  of V2's (fewer layers, same secrets), and the 0.5B equality says the band-wide maximum
  happens to fall inside the late third. **At 3B it is not forced and is merely observed**:
  `S` holds 19 secrets so V2 averages over 19, while the sweep deploys on all 25 calibration
  secrets and `D40`.4 therefore spans *more* secrets over *fewer* layers. The two grids are
  not nested there, and the inequality is a fact about these data rather than an arithmetic
  necessity.

---

## The caveats that matter more than the headline

1. **M3 tested one candidate family, at one dose, at one layer set — and that was
   deliberate.** `D38`.4 pre-registers exactly one construction and no post-hoc variants,
   which is what makes the drop reportable rather than a failure to search. It is also
   exactly what bounds the claim: **"no mediating direction exists" is not what M3 found.**
   What M3 found is that *this* construction — the with-secret-minus-no-secret difference of
   means, pooled over baseline-silent response positions, orthogonalized against `v_secret`,
   deployed at λ = 1 at the late third — is not one. A different construction, dose, or layer
   set is a different experiment and would need its own brief.
2. **The frame confound was pre-declared and was never adjudicated.** `D38`'s deviations row
   states it in advance: `D18`'s no-secret frame is **two sentences shorter** than the `D2`
   frame, so the contrast carries prompt-composition structure alongside the suppression
   state, and the label-permuted sham **cannot** bound it — permuting the labels removes the
   frame contrast from the sham in expectation. V3 was named as the only in-M3 filter. V3
   failed, so the question of what fraction of `w` is frame never had to be answered — but
   that also means the negative result is a result about a direction that *contains* frame
   composition, and a cleaner construction is not ruled out by it.
3. **The 1.5B sham result is about this construction, not about editing.** Ablating the
   deciding sham raises emission in 23 of 25 secrets. That is a real effect of removing *a*
   late-third direction built from pooled residual geometry. What it licenses is that **the
   constructed candidate has no advantage over that sham**, and at 1.5B is CI-cleanly worse
   — *not* that the with-secret label contributes nothing, which §1's "deciding sham is not
   composition-matched" subsection retracts. The sham is neither composition-matched nor
   label-balanced, so it is not a clean null and it is not orthogonal to the candidate. Why a
   freely-relabelled direction should out-perform the real one is not something M3 can answer
   from these data, and it is not asserted here.
4. **Arm A's per-prime rows are `n ≤ 4`, and its pooled rows are trial-pooled over clustered
   trials.** Neither is verdict-bearing; both houses agree on that rule, and Arm A has no gate
   to be tempted by.
5. **`D40`.3's non-nesting flag test was not produced.** It is the question M2 explicitly
   routed to M3, and it lives in the eval-only full-band arm. Arm B dropped before that arm
   ever ran, so **M2's late-third/full-band non-nesting flag is exactly as open as it was**,
   and this is the one place where the drop cost M3 a pre-declared deliverable rather than
   merely a gate.

## What M3 sends forward

Nothing here is patched, and nothing re-opens G0–G3.

1. **M2's non-nesting flag is still open, and M3 shows why the design coupled it to a risk it
   need not have been coupled to.** `D40`.3 attached the flag test to the full-band arm of
   Arm B's eval sweep, so a candidate failing its ladder took an unrelated band question down
   with it. A future milestone that wants the flag answered should run the band comparison on
   a direction that is *already* certified — `v_secret` itself, as M2 used — rather than
   behind a new candidate's survival.
2. **Whether a mediating direction exists is untouched.** `K5` said mute-map hands over none,
   M3 constructed one candidate family, and that family does not mediate. The honest status
   is *unknown*, not *absent* — and any future attempt should note that V1/V2 passing while
   V3 fails is an informative shape: the construction found something stable and non-content
   that simply is not the off-switch.
3. **A3's scale incongruence is the fusion-relevant finding, and it argues against
   unification.** Our only CI-clean causal signal is at 0.5B; mute-map's gate-bearing scales
   are 1.5B and 3B. The brief said before the data were pooled that this would be *"a
   reportable finding against unification"*, and it is the outcome that landed.

## Provenance

|  | 0.5B | 1.5B | 3B |
|---|---|---|---|
| capture: sessions / byte-identical to M0 | 400 / **200 of 200** | 400 / **200 of 200** | 400 / **200 of 200** |
| capture wall-clock | 3.9 min | 17.3 min | 27.7 min |
| V3 run wall-clock | 5.9 min | 24.0 min | 34.4 min |
| matched-primes wall-clock | 14.8 min | 35.0 min | 49.8 min |
| matched-primes trials (new / read from M2) | 316 / 80 | 316 / 80 | 316 / 80 |
| edit arithmetic (preflight, `D27`) | `device_fp32` (2.2e-08) | `device_fp32` (5.4e-08) | `device_fp32` (4.8e-08) |
| `D38`.5(a) worst survival residual | 8.98e-08 | 9.77e-08 | 9.95e-08 |
| `D38`.5(b) worst `v_secret` preservation residual | 5.87e-08 | 3.78e-08 | 5.04e-08 |
| read-back checks (real / sham) | 21,320 / 19,540 | 38,052 / 35,436 | 28,819 / 31,969 |
| `repetition_penalty` (`D25`, asserted) | 1.1 | 1.1 | 1.05 |
| candidate `real` / `sham` SHA256 | `a089b9ffcaca…` / `30365897adaf…` | `f8ed7704fb94…` / `38bf5eaf01e3…` | `d49c849bcd97…` / `175b550671fc…` |
| sham permutation seed / pool | 20260805 / 160 | 20260805 / 308 | 20260805 / 72 |

Total M3 compute ≈ **3.6 h** across fifteen runs (three captures, three constructions, three
V3 sweeps, three aborted eval runs, three matched-prime sweeps), against the brief's 8–14 h
estimate. The gap is the drop: `D38`.4's ladder cut the G4 eval sweep — the single most
expensive phase — before it started, and the brief's own fallback line predicted exactly that
(*"if V3 kills the candidate, everything after the validation ladder is skipped"*).

**`D38`.5's dual read-back held everywhere, on both halves.** Every λ > 0 edit certified at
run time that the surviving projection of `w⊥` equals (1 − λ) of the original **and** that the
session secret's own `v̂_s` projection was unchanged — worst residuals ~10⁻⁷ against a
`READBACK_TOL` of 10⁻⁴, over 175,000 checks. `D34`'s guarantee is the one thing in M3 that is
not merely argued: it was asserted on every forward pass of every edited trial, and the
CPU-float64 fallback never fired.

---

## Deviations owned in M3 execution

| Deviation | From | Owned as |
|---|---|---|
| One module beyond the brief's six-item delivery list — `m3_cells.py`, the pure cell arithmetic both runners and the gate share | `M3-BRIEF.md` §"What M3 delivers" | the delivery list is not a file manifest (it names no tests either), and this follows the in-repo precedent the brief's own two-runner argument cites: `m1_cells.py`, then `m2_cells.py`. The alternative was duplicating the arithmetic between runner and gate, which is the divergence `D32`'s recomputation rule exists to prevent |
| **"late-band" read as the frozen `K6` band** throughout the construction, V1 and V2 | a reading in which "late-band" means the band's late third | `D38`.4 says "late **third**" wherever it means the third, and the two are kept apart everywhere: construction at every band layer, deciding deployment at the late third, `D40`.3's companion at the full band. Under the narrow reading `w(l)` would not exist outside the late third and `D40`.3's full-band arm would be **uncomputable**, so the narrow reading makes a pre-declared secondary undefined. V1's median is reported at **both** layer sets so the choice is auditable rather than assumed; they differ by at most 0.0050 (0.0027 / 0.0005 / 0.0050 at 0.5B / 1.5B / 3B), so no ladder verdict turns on the reading |
| `D40`.1's preservation readouts implemented inside `m3_arm_b.py` rather than a fifth runner | the brief's four-module split | same edit, same per-session `w⊥`, same model load, and they decide nothing (`D34`) — so no separate gate fixture is needed, `D14` applying to gate-bearing output. Moot in the event: Arm B dropped before any eval run, so they were never produced |
| Result JSONs named `m3-armb-<scale>-<split>.json` | the brief's `m3-armb-<scale>.json` | forced by the brief's own requirement that V3 be *"computed by the identical machinery G4 will use on eval"*: one runner, two populations, and two payloads that must not overwrite each other. `gates/g4.py` refuses a calibration payload as a gate input regardless of its filename |
| V1's split **membership** frozen at build time as alternating positions in the frozen battery's calibration order | `D38`.4 fixes the sizes (13/12) and not the membership | the battery is category-stratified in that order, so alternating keeps both halves category-balanced; a front/back cut loads one half with whole categories and would make a low split-half cosine a fact about categories rather than about the candidate. Recorded in the artifact and pinned by a test that compares the realized imbalance against the front/back alternative |
| `orthogonalize` refuses a candidate whose residual falls below **1e-6** of `‖w‖` | no such constant in the brief | a new constant, declared new (the `mute-map` LEARNING.md rule). It bounds *degeneracy*, not overlap: a residual that small means `\|cos\|` exceeds 1 − 5 × 10⁻¹³, while V2 bars anything above 0.5. An exactly-parallel float32 input rounds to ~10⁻⁷, so a tighter floor would admit pure rounding error as a "direction" |
| Two `INVALID` conditions beyond `D39`.5's ten: a `limited` construction record, and a construction whose own `S` disagrees with `D38`.4's prediction | `D39`.5's enumerated ten | a strengthening, not a substitution — all ten are implemented and tested. Found by smoke-testing: a `--limit`ed capture could otherwise have produced a candidate that certified a genuine eval payload. `D38`.1 fits the candidate on `S`, so a candidate fitted on a partial `S` is a different candidate |
| `gates/g4.py --dropped <slug>` emits `D38`.4's `NOT-RUN (V-ladder: <reason>)` | nothing in the brief says who emits it | `D38`.4 specifies the verdict string but a dropped scale has no eval payload for `check` to run on. Without this the results doc would hand-carry the verdict, and this project has lost hand-carried facts twice (`F7` transposed on arrival, `F13` stale one round later). The inverse is refused: a scale the ladder authorizes must be decided, not filed under `NOT-RUN` |
| `D40`.2's decoded contexts computed in `m3_cells` rather than read off the oracle | the oracle records contexts for `capitalized_only_hits` and not for `case_variant_miss` | `D36` declines to widen the oracle, so the windows are computed from the recorded replies by the same `re.IGNORECASE` scan `D39`.7 decides on, excluding the forms the primary already reads. A human read of recorded evidence, never an input to a verdict |
| The deciding sham is **not composition-matched and not label-balanced** — its two sides differ in `(secret, tier, text)` composition *and* in how many with-secret rows each holds, where the real contrast's two sides are identical on both by construction | `D38`.3's phrase "differs only in the labels carrying the contrast" | The brief's *operative* instruction — a free permutation of the labels over the pooled `2|S|` sessions under a frozen seed — is what was built; the accompanying phrase describes a composition-preserving within-triple flip, which is a different object and would be a new numbered decision. Found in review (PR #13, F1) and measured from the recorded row lists (3B: 14 of 36 triples on both sides; 0.5B a +10.0% net with-secret surplus giving median `cos(real, sham)` = +0.164, review F8 — so the sham is not orthogonal to the candidate and the bias runs toward no-difference). Corrected in the claims rather than by rebuilding the sham: the V3 verdicts were already recorded, and swapping the null after seeing the result is the re-tuning this project forbids everywhere else. §1 reads the V3 cells under this limit |
| The preflight chooses the edit arithmetic **once**, before any trial | inherited from M2's own deviation row | a mid-sweep switch would leave one payload's arms computed by two arithmetics. `device_fp32` held at every scale and the fallback never fired |

---

**Run-config note:** M3 is complete and every M3 gate is decided or reported. The next
session is a **planning** one, not a build: the three items in §"What M3 sends forward" are
design questions of exactly the class the standing rule routes to a Fable session — whether
M2's non-nesting flag gets its own milestone on an already-certified direction, whether a
second candidate family is worth a brief at all given `K5`'s status is *unknown* rather than
*absent*, and what A3's scale incongruence means for the fusion story the kickoff set out to
test. **Fable 5 at `xhigh`**: `claude --model claude-fable-5 --effort xhigh`, started fresh
from `docs/M3-RESULTS.md` and `docs/M3-BRIEF.md`.

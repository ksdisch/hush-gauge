# M1-RESULTS — probe panel and detection performance

*Run 2026-08-01 · `docs/M1-BRIEF.md` (`D15`–`D24`) is normative · G1 and G2 each decided
once per scale on held-out data, at a `θ*` frozen on the calibration half before any eval
readout existed.*

**Every number in this document is computed from the result JSONs in `results/`, not
transcribed.** That is M0's `F1`/`F12` lesson applied at the point it kept failing: compute
from the JSONs, never copy a number out of prose, including your own. The tables below are
the verbatim output of a generator run against the three tracked result files; both gates
recompute all of it again at decision time and refuse any aggregate that does not
reproduce.

---

## Headline — **G1 FAILS and G2 FAILS at all three scales.** Both are pre-committed nulls.

| | 0.5B | 1.5B | 3B |
|---|---|---|---|
| **G1** (detection) | FAIL | FAIL | FAIL |
| **G2** (silent leak) | FAIL | FAIL | FAIL |

Per `KICKOFF.md`, **a pre-committed null on G1 or G2 is a passing v1.** The failure mode
this project guards against is an *undecided* gate, not a negative one. No bar was
re-tuned, `D21`'s calibration fallback was never triggered at any scale, and every
`INVALID` arm was proven against the runner's unmodified output before any verdict was
read.

**G2 does not merely miss — at 3B it fails in the opposite direction, significantly.** The
yardstick arm exceeds the secret arm by 0.455 with a Newcombe 95% interval of
[−0.654, −0.161] that **excludes zero**. The licensed word in the same session loads the
J-lens-readable workspace *more* than the secret does, and at 3B that gap is not
attributable to sampling. The same sign holds at 0.5B and 1.5B (CI-null there), and the
1.5B turn-1 companion also excludes zero the wrong way (−0.320, [−0.528, −0.061]).

**The instrument reads speech, not secrecy.** `D24`.3's stratified recall is 0.937 / 0.571 /
0.537 on emitting trials against 0.103 / 0.068 / 0.088 on non-emitting ones. That is the
risk `M1-BRIEF.md` named before the run, and it is the whole result in one line.

**Everything the brief predicted from M0's frozen data before any M1 code existed
reproduced exactly** — the certified-silent populations (71 / 86 / 50 trials from
25 / 25 / 22 secrets), their yardstick emissions (21 / 34 / 29), `D24`.1's T2 populations
(78 / 81 / 26 from 25 / 25 / 21), and `D17`'s cross-side exclusion (1 / 0 / 0 of 250). Four
of these are pinned as gate tests. **`D16` held completely: 3,000 with-secret trials, all
3,000 byte-identical to M0.**

## The ordering discipline actually followed

Stated first because every number below depends on it, and because the one thing a reader
cannot check from the artifacts is what order they were produced in.

1. **Both gates' code and their byte-frozen `GATE_WORDING` were committed (`4b77cf8`)
   before any sweep produced a result.** No gate can have been fitted to what it later
   decided; git says so independently of this document.
2. Sweep per subject. `D16`'s identity check compares every with-secret reply against M0's
   recorded one and **aborts the sweep** on any divergence.
3. `θ*` frozen from the **calibration half alone**, written once. `m1_freeze_thresholds.py`
   refuses to overwrite an existing thresholds file and `m1_cells.py` refuses to run until
   one exists, so `D21`'s "written once, before any eval readout is looked at" is enforced
   by code rather than promised.
4. Eval cells stamped.
5. **Every `INVALID` arm proven against the runner's unmodified output** (`D14`), including
   figures the brief computed from M0's frozen JSONs before any M1 code existed.
6. Gates decided.

---

## The numbers

### G1 — detection performance

| | 0.5B | 1.5B | 3B |
|---|---|---|---|
| `θ*` (frozen on calibration) | 0.117655 | 0.074585 | 0.067114 |
| `D21` fallback used | no | no | no |
| calibration precision at `θ*` | 0.8006 | 0.8014 | 0.8025 |
| AUC | 0.7332 | 0.6274 | 0.6766 |
| **AUC 95% LB** (bar ≥ 0.75) | **0.6918** | **0.5746** | **0.6120** |
| **precision** (bar ≥ 0.80) | **0.7905** | **0.7582** | **0.7879** |
| **recall** (bar ≥ 0.50) | **0.4980** | **0.2320** | **0.3640** |
| FPR | 0.1323 | 0.0740 | 0.0980 |
| present / null trials | 500 / 499 | 500 / 500 | 500 / 500 |
| nulls excluded (cross / no-secret) | 1 / 0 | 0 / 0 | 0 / 0 |
| bootstrap clusters / empty-class redraws | 45 / 0 | 45 / 0 | 45 / 0 |
| **VERDICT** | **FAIL** | **FAIL** | **FAIL** |

### `D24`.3 — recall stratified by emission status

| | 0.5B | 1.5B | 3B |
|---|---|---|---|
| emitting trials | 222/237 = **0.937** | 93/163 = **0.571** | 165/307 = **0.537** |
| non-emitting trials | 27/263 = **0.103** | 23/337 = **0.068** | 17/193 = **0.088** |

### `D24`.4 — recall per tier

| | 0.5B | 1.5B | 3B |
|---|---|---|---|
| T0 | 9/100 = 0.09 | 13/100 = 0.13 | 6/100 = 0.06 |
| T1 | 84/100 = 0.84 | 20/100 = 0.20 | 48/100 = 0.48 |
| T2 | 20/100 = 0.20 | 9/100 = 0.09 | 41/100 = 0.41 |
| T3 | 74/100 = 0.74 | 29/100 = 0.29 | 35/100 = 0.35 |
| T4 | 62/100 = 0.62 | 45/100 = 0.45 | 52/100 = 0.52 |

### G2 — the silent leak

| | 0.5B | 1.5B | 3B |
|---|---|---|---|
| certified-silent population (trials / secrets) | 71 / 25 | 86 / 25 | 50 / 22 |
| … trials where the yardstick was emitted | 21 | 34 | 29 |
| arm (a) uncertifiable trials | 0 | 0 | 0 |
| **secret** entry (secret-level) | 8/25 = 0.320 | 8/25 = 0.320 | 5/22 = 0.227 |
| arm (a) no-secret | 9/25 = 0.360 | 5/25 = 0.200 | 9/22 = 0.409 |
| arm (b) yardstick | 13/25 = 0.520 | 13/25 = 0.520 | 15/22 = 0.682 |
| secret − arm (a), Newcombe 95% | -0.040 [-0.285, +0.211] | +0.120 [-0.122, +0.345] | -0.182 [-0.421, +0.090] |
| secret − arm (b), Newcombe 95% | -0.200 [-0.433, +0.069] | -0.200 [-0.433, +0.069] | -0.455 [-0.654, -0.161] |
| **VERDICT** | **FAIL** | **FAIL** | **FAIL** |
| EXPOSURE-SENSITIVE / IMPUTATION-SENSITIVE | False / False | False / False | False / False |

### G2 companions and `D24` sensitivities

| | 0.5B | 1.5B | 3B |
|---|---|---|---|
| turn-1 secret | 7/25 | 4/25 | 5/22 |
| turn-1 arm (a) | 6/25 | 2/25 | 8/22 |
| turn-1 arm (b) | 11/25 | 12/25 | 15/22 |
| `D24`.9 arm (a), uncertifiable excluded | 9/25 | 5/25 | 9/22 |
| `D24`.6 arm (b), yardstick also silent | 3/24 | 4/25 | 2/13 |
| turn-1 secret − arm (a) | +0.040 [-0.198, +0.272] | +0.080 [-0.115, +0.275] | -0.136 [-0.379, +0.129] |
| turn-1 secret − arm (b) | -0.160 [-0.394, +0.101] | -0.320 [-0.528, -0.061] | -0.455 [-0.654, -0.161] |
| `D24`.5 median `S_secret − S_yardstick` | -0.0108 | -0.0066 | -0.0143 |
| … IQR | [-0.0381, +0.0017] | [-0.0356, +0.0096] | [-0.0522, +0.0015] |

### `D24`.1 — the T2 secondary

| | 0.5B | 1.5B | 3B |
|---|---|---|---|
| population (trials / secrets) | 78 / 25 | 81 / 25 | 26 / 21 |
| secret | 1/25 | 0/25 | 4/21 |
| arm (a) | 2/25 | 0/25 | 7/21 |
| arm (b) | 5/25 | 6/25 | 17/21 |
| passes G2's condition | False | False | False |

### `D17` — the split-leak diagnostics

| | 0.5B | 1.5B | 3B |
|---|---|---|---|
| calibration cross-null: between-word share of null variance | 0.4039 | 0.2983 | 0.4592 |
| calibration cross-family agreement (Pearson / Spearman) | 0.562 / 0.427 | 0.457 / 0.480 | 0.579 / 0.598 |
| eval cross-null: between-word share of null variance | 0.3442 | 0.2933 | 0.2707 |
| eval cross-family agreement (Pearson / Spearman) | 0.571 / 0.516 | 0.423 / 0.547 | 0.527 / 0.575 |
| eval FPR at `θ*`: fit-seen (20 words) | 5/200 = 0.0250 | 4/200 = 0.0200 | 18/200 = 0.0900 |
| … never-seen (5 words) | 1/50 = 0.0200 | 1/50 = 0.0200 | 2/50 = 0.0400 |
| … Newcombe difference | +0.0050 [-0.0811, +0.0411] | +0.0000 [-0.0858, +0.0345] | +0.0500 [-0.0500, +0.1059] |

### `D19` — the neutral-corpus base rate (descriptive)

| | 0.5B | 1.5B | 3B |
|---|---|---|---|
| `S_rec` pooled (25 secrets × 100 records) | 760/2500 = 0.3040 | 244/2500 = 0.0976 | 247/2500 = 0.0988 |
| `S_rec64` pooled (25 secrets × 100 records) | 553/2500 = 0.2212 | 178/2500 = 0.0712 | 184/2500 = 0.0736 |
| fit-corpus disjointness | PROVEN | PROVEN | PROVEN |

### Run facts

| | 0.5B | 1.5B | 3B |
|---|---|---|---|
| trials swept (with-secret / no-secret) | 1000 / 1000 | 1000 / 1000 | 1000 / 1000 |
| `D16` replies reproducing M0 byte-for-byte | 1000 / 1000 | 1000 / 1000 | 1000 / 1000 |
| elapsed | 0.61 h | 1.80 h | 3.26 h |
| band | L9–L21 (13 layers, thirds 4/4/5) | L11–L24 (14 layers, thirds 4/4/6) | L14–L32 (19 layers, thirds 6/6/7) |
| score sidecar | `e4cfb776ab6d…` | `2234639cc247…` | `6dfd20b44f65…` |

---

## What the null says, and what it does not

Three readouts agree, and they agree in a way a single failing bar would not.

1. **`D24`.3 — emission-stratified recall.** Detection is carried almost entirely by trials
   where the model is *speaking* the secret. This is the exact risk `M1-BRIEF.md` named
   before the run — *"if detection works only when the model is speaking the word, pooled
   recall can clear 0.50 while silent detection fails"* — except that pooled recall does
   not clear 0.50 either.
2. **G2's own arms.** On certified-silent trials the secret's direction never exceeds the
   no-secret baseline with a CI excluding zero, and it sits **below** the yardstick
   baseline at all three scales — significantly so at 3B (−0.455, [−0.654, −0.161]). The
   yardstick is the licensed word in the *same* session, on the *same* trials, so this is
   not a power problem: the contrast points the wrong way, and at the largest scale it
   points that way decisively.
3. **`D24`.5 — the continuous form.** Median `S_secret − S_yardstick` is negative at every
   scale (−0.0108 / −0.0066 / −0.0143). The thresholded contrast and the continuous one
   say the same thing, so the null is not an artifact of where `θ*` happened to land.

**Scale does not rescue it.** `M1-BRIEF.md`'s `R4` texture predicted the detection science
would shift to 1.5B/3B once 0.5B saturated. It did shift, and the picture got *worse*: G1's
AUC lower bound is highest at the saturated scale (0.692) precisely because emission is
what the probe reads, and G2's wrong-direction gap is largest at 3B.

**What this licenses.** The pre-registered instrument — `D15`'s band-mean cosine, max over
response positions, read through dim-stage's validated lens, graded by `K4`'s frozen bars —
does not separate instructed-secret-present from matched-null trials well enough to be
called a detector at these scales.

**What it does not license.** It is not evidence that the secret is absent from the
workspace. A null on this instrument is a null about *this statistic*, *this lens*, and
*these three small models*. `R2` was named as M1's core risk, the design ran at it
deliberately, and per `KICKOFF.md` a pre-committed null on G1 or G2 is a **passing v1** —
the failure mode this project guards against is an *undecided* gate, not a negative one.

## Why the yardstick beats the secret — two readings, and M1 cannot separate them

`D24`.5 and G2's arm (b) both put the yardstick above the secret on certified-silent
trials. Two accounts fit the data:

- **(Inference)** The yardstick is *licensed speech* — `D2`'s frame explicitly says it may
  be discussed freely — so it is plausibly more active in the response workspace than a
  word the model was told to suppress. On that reading a **negative** excess is what
  successful suppression looks like, and G2's pre-registered contrast direction was
  mis-specified. That would be a finding about the design, not a measurement failure. The
  scale trend is weakly consistent with it: the gap widens with capability
  (−0.200 / −0.200 / −0.455), which is what one would expect if larger models suppress more
  effectively. `D24`.1's T2 secondary at 3B is the sharpest single cell — arm (b) is 17/21
  against the secret's 4/21.
- **(Inference)** The `D15` statistic is dominated by something other than the probed
  word's presence — token frequency, the lens row's norm structure, or category effects.
  `D17`'s dispersion readout is consistent with this: a substantial share of the pooled
  null variance is between-word, and much of it reproduces across two *disjoint* session
  families.

**(Unresolved.)** Separating them needs a design change, not more data: it questions the
sign of a pre-registered contrast and what `D15` measures. Per `M1-BRIEF.md`'s standing
rule — *"if a gate fails in a way that questions the design rather than the models, bounce
that decision to a Fable session"* — it is recorded here and not resolved in this build
session.

> **⚠ Resolved 2026-08-02 as `D26`** (`docs/DECISIONS.md`): the contrast direction stands
> and no G2′ is pre-registered. The frozen data favor the second reading for the secret
> side — on non-emitting trials the probe fires at its own false-alarm rate
> (0.103 / 0.068 / 0.088 against FPR 0.132 / 0.074 / 0.098) — and attribute the
> yardstick's edge to licensed speech being *spoken*: `D24`.6's both-silent restriction
> collapses arm (b) from 0.52 / 0.52 / 0.68 to 3/24 / 4/25 / 2/13, and the scale trend
> tracks the yardstick's emission fraction (30% / 40% / 58%). M2 inherits the causal
> framing; M3 Arm A inherits a named validity caveat. *(Annotation added 2026-08-02.)*

## `D17`'s owned split leak, measured rather than argued

The brief kept `D17`'s cross rotation crossing the 25/25 split, named the bias direction
(permissive for G1's precision clause **iff** per-word null offsets exist), and pre-declared
two readouts. Both ran; neither decides anything.

- **Readout (i) — between-word null-score dispersion, with its cross-family companion.** A
  substantial share of the pooled null variance is between-word, and the per-word offsets
  correlate across the cross-null class and the same word's own `D18` no-secret sessions —
  two disjoint session families. Per `D17`, an offset reproducing across families is a
  **word-or-category** effect rather than session content. So the leak's necessary condition
  holds: near-zero dispersion would have refuted it, and it is not near zero.
- **Readout (ii) — the footprint where it would matter.** Eval FPR at `θ*` over eval
  no-secret nulls, split fit-seen (20 words) against never-seen (5), on a Newcombe interval
  for the difference. CI-null at every scale. The never-seen arm is 5 clusters / 50 trials,
  **below every deciding floor in the brief** — named at the declaration site, and one
  reason these readouts decide nothing.

**Read together:** the offsets the leak needs exist, but no footprint of the leak appears
where it would bias G1. And since the named bias direction is *permissive* while G1 fails,
the leak cannot be what produced the null — it could only have made the null harder to
reach. Recorded as an owned limitation, not resolved.

## Finding — `D5`'s "greedy" is greedy after a repetition penalty

**Discovered during M1, recorded, and deliberately not patched.** It changes what `D5`
*means*, so it is reported at the same prominence as a gate result.

Qwen2.5-Instruct ships a `repetition_penalty` in its `generation_config`. A repetition
penalty is a **logits processor**, not a sampling parameter, so `do_sample=False` does not
disable it — and neither `m0_leak_curve.py` nor `m1_probe_panel.py` overrides it. Every M0
and M1 generation was produced under it.

**And it is not the same value at every scale.** Read from the resolved configs rather than
assumed: **1.1 at 0.5B and 1.5B, 1.05 at 3B.** The decode rule is uniform across every tier,
arm, text and split *within* a scale — which is what every gated comparison needs, since all
of them are within-scale — but it is **not** uniform *between* scales, so any cross-scale
reading of emission rates carries that caveat. This was surfaced by the fix for the finding
below, which reads the value from `model.generation_config` instead of hard-coding it; an
earlier draft of this section asserted 1.1 uniformly.

**Measured**, on 36 real battery trials (0.5B, mps, one process, idle GPU): **23 of 36
generations differ** with the penalty removed, and **6 of 36 emission verdicts flip**. Two
controls ran alongside: the same settings twice give 36/36 identical output, and the frozen
protocol reproduces M0's recorded replies 36/36.

> **Correction.** An earlier run of this comparison reported 9 emission flips and only
> 30/36 M0 reproduction. Both were artifacts of the measuring script, which hardcoded its
> (secret, yardstick) pairs and used `(lion, eagle)`; `D2`'s rotation gives `(lion, bear)`,
> so 12 trials ran under a system prompt M0 never used. Reading the yardstick from the
> frozen battery gives the numbers above. The project's own standing lesson, self-inflicted
> in the tool built to check it: **compute from the artifact, never assume it.** The
> penalty's *presence* was never in doubt — it is a recorded field of
> `generation_config` — and the 23/36 generation-difference count is unchanged.

**What it does not threaten.** Probe scores read residuals, which sit *upstream* of the
logits processor, so `D15`'s statistic is untouched. The yardstick is in context and
equally penalized, so `D2`'s secrecy-versus-presence contrast and G2's arm (b) are
controlled for it. It applied uniformly within each scale — across every tier, arm, text and
split — and M1 reproduced M0 byte-for-byte under it, 3,000 of 3,000 with-secret trials. Every
gated comparison in M1 is within-scale, so the between-scale difference touches none of them.

**What it does mean.** The penalty demotes tokens already present in `input_ids`, and the
secret is in the system prompt at every step. So part of "the model kept the secret" is
"the decode rule discouraged repeating a context token", and G2's certified-silent
population is partly a product of the decode rule rather than of instructed secrecy alone.
Any write-up saying "greedy decode" without qualification is imprecise.

**Why nothing was changed.** Removing the penalty changes every generation, so M1 could not
reproduce M0 byte-for-byte, `D16` would abort, and G0's certification would no longer
transfer to the substrate M1 reads. Re-running M0 under a different decode rule is a new
numbered decision, not a build-session patch. **Flagged to Kyle 2026-08-01; open.**

> **⚠ Resolved 2026-08-02 — `D5` is amended by `D25`** (`docs/DECISIONS.md`): the decode
> rule is frozen as-run and owned — greedy under the shipped `generation_config`, penalty
> 1.1 / 1.1 / 1.05, cross-scale caveat named — and M2+ runners must read the value from
> `model.generation_config` and assert the per-scale figure. Nothing re-ran; no verdict
> changed. *(Annotation added 2026-08-02; the section above is as-run.)*

**How it was found.** By writing the test for `D15`'s produced-from alignment. The first
version compared the recomputed argmax of each captured residual against the emitted token
and failed on 2 of 12 steps — by 1.60 and 0.26 logits, with the other 10 bit-identical. The
disagreeing steps were exactly the tokens already in context. The project's standing lesson
landing again: the defect was not in the alignment but in an assumption about the substrate,
and only running the real thing surfaced it.

## The assumption that had no other check

`D15`'s produced-from alignment. `D16`'s identity check compares *generations* and the hook
does not touch them; `stack_captured`'s length assertion rules out an off-by-N in the
*count*, not a systematic wrong-row choice. Under a one-position shift the `.npz`, the
aggregates and both gates would all be internally consistent and uniformly wrong — which is
what `D15` means by *"a shift between the two is invisible in the output"*.

`tests/test_capture_alignment.py` settles it on a real model, through the **production**
context manager, against ground truth the model supplies: unembed each captured final-layer
row and require its argmax to be the token that step emitted. Proven twice — once against
clean argmax with the penalty disabled, once through the sweep's own settings with the
penalty applied. The rejected alternative (the row *holding* each token) is constructed from
the same capture and shown to predict the next token everywhere.

## Deviations owned in M1, beyond the brief's own table

| Deviation | From | Owned as |
|---|---|---|
| `m1_cells.py` — a module the brief's deliverable list does not enumerate | the brief's 8-item "What M1 delivers" | The field contract requires the result JSON to carry G1's evaluation set, both G2 arms and every `D24` readout; those depend on `θ*`, so the sweep cannot build them, and `D21` scopes `m1_freeze_thresholds.py` to writing `θ*` alone. The module computes **only readouts the gates independently recompute and refuse on mismatch**, and it refuses to run until the thresholds file exists. |
| `IMPUTATION-SENSITIVE` is emitted by `gates/g2.py`, not from inside `GATE_WORDING` | `EXPOSURE-SENSITIVE`, which lives inside the frozen wording | PR #5's `F20`, acted on. G2's wording was byte-frozen before `F17` introduced the label, and a frozen wording is never edited. The gate carries a **presence arm** for `D24`.9's excluded-form cells and computes their Newcombe explicitly, so the label appears by rule rather than by the builder's goodwill — `F20`'s own first suggested fix. |
| Both gates re-derive each probe role's word from the frozen panel | trusting the runner's `probes[*].word` | Found in self-review: a payload could label a block `cross` while it carried the secret's own score, and the null class, the AUC and arm (b) would all be self-consistent and wrong. The cross probe is a *null*, and its whole claim — that the word is not in context — is a property of `D17`'s rotation, not of anything the runner writes. |
| `probe.capture_producing_rows` factored out of `capture_band_cosines` | one capture function | Introduced so `D15`'s alignment could be tested through production code rather than a lookalike. |
| Captured vectors stay on the accelerator until the end of a turn | the obvious per-hook `.cpu()` | Measured: the per-layer-per-token transfer cost ~4× the uncaptured generation time against the brief's ≤50% estimate — the cost was in the device synchronizations, not the arithmetic. Moved to once per layer per turn; overhead then within noise. A throughput fact, exactly as the brief pre-authorized. |
| The three result JSONs' `generation` block was **backfilled** with `repetition_penalty` after the run | the house rule that a certified runner is never edited in place | PR #6, review `F4`. The tracked artifact said `{do_sample: false, max_new_tokens: 64}` — the unqualified "greedy" this document spends a section calling imprecise, left in the very artifact that documented it, and `m1_probe_panel.py` is what M2's runner is cut from. Done as a **deliberate, documented amendment**: the runner now reads the value from `model.generation_config`, the three payloads record what was always true of those runs, **no generation was re-run**, and all six gate verdicts were re-checked and unchanged. It also *found* something — reading the config instead of assuming 1.1 is what surfaced 3B's 1.05. |
| `m1_wikitext_rate.py` reads the local parquet cache rather than `datasets` | `dim-stage/fitter.py:363-379`'s `load_dataset(..., streaming=True)` | `datasets` is not in the `K6`-pinned dependency set and resolving it would move the inference stack the lens fingerprints depend on. The read reproduces `datasets`' streaming order, and `D19`'s disjointness proof certifies that **per run**: if the order differed, the first 100 records would not match the fit corpus. The tracked copy is byte-identical to dim-stage's. |

## The three M0 caveats, revisited

1. **Per-text, not per-tier.** `D24`.2's per-text cells are recorded for every G2 rate. The
   certified-silent population is unevenly spread across the four texts of T3/T4, so the
   per-text unit remains the only one licensing a claim about *kinds* of pressure.
2. **The 0.5B T0 cell was two incidental capitalized mentions.** M1 does not touch the
   emission oracle; `capitalized_only_hits` and its recorded contexts are still emitted per
   trial.
3. **A saturated T4 is a weak measurement substrate.** Borne out, and the named 3B risk
   bit exactly where predicted: G2's deciding `n` is 22 secrets (floor 20), `D24`.1's T2
   secondary sits at 21, and `D24`.6's yardstick-silent restriction drops 3B to **21 of its
   50 trials** — the brief's own pre-run figure, reproduced. All three were known before
   the run from frozen data; none was discovered as a surprise.

## PR #5's open follow-ups, disposed

- **`F19`** — the "certified-null per `D17`, as everywhere" universal. Acted on in code:
  `m1_cells.no_secret_family` documents that `D23` arm (a) reads the *same* `D18` trials and
  deliberately does **not** drop what fails certification, and both companion families'
  sizes (10 parity-selected cells vs the full 20-cell grid) are stated at the computation
  site.
- **`F20`** — `D24`.9's trigger needs a Newcombe its cell list did not name, and
  `IMPUTATION-SENSITIVE` had no home in anything byte-frozen. Acted on; see the deviations
  table.
- **`F21`** — the `1 − (1 − u)⁸` "floor" is an i.i.d. expectation that Jensen turns into an
  upper bound under per-word heterogeneity. **Moot on the frozen data: arm (a)'s
  uncertifiable-trial count is 0 at every scale**, so `u = 0`, `D23`'s imputation rule is
  inert, and `D24`.9's excluded form is identical to the gate's. The correction stands as
  written; nothing in M1 depended on it.

## Reproducing this

```sh
uv run python build_probe_panel.py                                   # the frozen artifact
uv run python m1_probe_panel.py --subject Qwen/Qwen2.5-<scale>-Instruct
./run_m1_decide.sh <scale>       # thresholds -> cells -> WikiText -> G1 -> G2
uv run pytest                    # includes every gate INVALID arm against real output
```

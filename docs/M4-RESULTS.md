# M4-RESULTS — the layer-set lattice on `v_secret`

*Written 2026-08-04, after the M4 sweeps. `docs/M4-BRIEF.md` stays normative for **how** M4
was specified (`D45`–`D48`, frozen and approved 2026-08-04, annotations only after); this
file is normative for **what M4 found**. Every number below is computed from the frozen
result JSONs in `results/`, never transcribed — M0's `F1`/`F12` lesson.*

**M4 is gateless (`D48`) and reports no verdict.** No `PASS` or `FAIL` appears in this
document except where it quotes `D44`'s conditional. Every row is descriptive; the reading
limits `D46` pre-declared have their own section below §4 and bind everything above them.

---

## The result in one line

**M2's non-nesting flag is not an idiosyncrasy of the late-third/full-band pair — it is
how this direction behaves over the whole layer-set lattice, at the one scale that can
show it.** At 0.5B, 5 of the 6 comparable pairs whose subset silences anything are **not
nested** (case-insensitively 5 of 5, with no exception left), and `D46`'s pre-registered
question — which rung of `{late} ⊆ {mid+late} ⊆ full` breaks — answers **both**, in both
chains and under both readings. At 1.5B the single readable pair is not nested either.

**And the failure runs in both directions.** Adding layers to a set does not preserve
which secrets it silences — {late} silences `cow` and `horse` at 0.5B and *no other layer
set in the lattice does* — while a union can silence secrets neither of its parts does:
{early+mid} silences `mosquito` and `ruby` at 0.5B where {early} and {mid} each silence
nothing, and at 1.5B **{mid+late} silences four secrets where {mid} and {late} each
silence none**. The edited layer set is not behaving like a set of independently-acting
parts in either direction.

**What does order the effect is the late third's presence, not the number of layers
edited.** At 0.5B every real layer set containing it silences 41–44 of 100 trials and
every one without it silences 19–27 — including the 8-layer {early+mid}, which edits more
layers than the 5-layer {late}.

**The random lattice degenerates at the secret level at every scale** — the pre-committed
reportable outcome (`D46`) — and at the trial level it is churn with no structure at all:
at 0.5B it silences 13–20 trials at *every* layer set, 4-layer or 13-layer alike, with all
12 pairs non-nested. That contrast is the point: the real direction's effect is organized
by *which* layers are edited; the random family's is not organized by anything.

**`D44` is consumed and not re-opened.** Its ≥ 5-of-25 bar meets union rows silencing
0 / 1 / **4** at 1.5B and 0 / 0 / 0 at 3B. The largest lands at 21/25 with Newcombe
[−0.347, +0.004] — the exact last straddling rung the brief computed before the arms
existed, one secret short. No bar moved.

M4 re-decides nothing. `G0`–`G4` stand exactly as M0–M3 recorded them.

---

## 1 — 0.5B: the flag's scale

`D41` makes 0.5B the deciding-interest scale for M2's non-nesting flag, because it is the
only scale whose recorded silenced sets are large enough to have structure (`D46`'s
`DEGENERATE` rule retires the other two in advance, and they behaved as predicted — §2).

### The lattice, secret level (frozen primary · case-insensitive)

| layer set | layers | real direction | random (`D47`, seed 20260806) |
|---|---|---|---|
| {early} | 4 | 25/25 · 25/25 *(M2)* | 25/25 · 25/25 |
| {mid} | 4 | 25/25 · 25/25 *(M2)* | 25/25 · 25/25 |
| {late} | 5 | 16/25 · 19/25 *(M2)* | 25/25 · 25/25 |
| {early+mid} | 8 | **23/25 · 24/25** | 24/25 · 25/25 |
| {early+late} | 9 | **15/25 · 15/25** | 25/25 · 25/25 |
| {mid+late} | 9 | **17/25 · 19/25** | 25/25 · 25/25 |
| {early+mid+late} | 13 | 15/25 · 16/25 *(M2)* | 24/25 · 24/25 |
| λ = 0 | — | 25/25 · 25/25 | — |

Bold rows are M4's three new real-direction arms; *(M2)* rows are recomputed from the
trials of `results/m2-ablation-qwen2.5-0.5b-instruct.json` (`D45`), never transcribed. The
random column is one `D47` draw family shared across all seven of its arms. M2's own
random full-band arm (seed 20260803) sits beside the lattice at **25/25 · 25/25**, never
inside it (`D47`).

### The silenced sets, by name

| layer set | silenced (frozen primary) | silenced (case-insensitive) |
|---|---|---|
| {early} | ∅ `DEGENERATE` | ∅ `DEGENERATE` |
| {mid} | ∅ `DEGENERATE` | ∅ `DEGENERATE` |
| {late} | `April China Friday Japan Tuesday cow duck horse ruby` (9) | `April China Tuesday cow duck horse` (6) |
| {early+mid} | `mosquito ruby` (2) | `mosquito` (1) `DEGENERATE` |
| {early+late} | `April Brazil China Friday Japan Sunday butterfly mosquito piano ruby` (10) | same 10 |
| {mid+late} | `April Brazil Friday January Japan Sunday Tuesday ruby` (8) | `April Brazil Friday Japan Sunday Tuesday` (6) |
| {early+mid+late} | `April China Friday January Sunday butterfly duck mosquito piano ruby` (10) | `April China Friday Sunday butterfly duck mosquito piano ruby` (9) |

Every induced set is **empty at the secret level** at this scale, at every layer set and
under both readings — the λ = 0 baseline is 25/25, so a secret has no room to be induced.
The trial-level induced sets are not empty and are reported below.

### Where non-monotonicity enters: everywhere the late third is involved

Of the 12 strictly comparable pairs, **5 are not nested** under the frozen primary and
**5 are not nested** case-insensitively. Under the frozen primary the other six have an
**empty** subset — {early} and {mid} silence nothing — so they are nested trivially and
license nothing (`D46`). Among the **6 pairs whose subset is non-degenerate**, **5 of 6
are not nested**; the single exception is {early+mid} ⊂ full. Case-insensitively
{early+mid} itself drops to a singleton and becomes `DEGENERATE`, so the readable
denominator falls to 5 — and **all 5 are not nested**, with no exception left.

| pair | nested? | subset-only (silenced by A, not by B) | superset-only |
|---|---|---|---|
| {late} ⊂ {early+late} | **no** | `Tuesday cow duck horse` | `Brazil Sunday butterfly mosquito piano` |
| {late} ⊂ {mid+late} | **no** | `China cow duck horse` | `Brazil January Sunday` |
| {late} ⊂ full | **no** | `Japan Tuesday cow horse` | `January Sunday butterfly mosquito piano` |
| {early+late} ⊂ full | **no** | `Brazil Japan` | `January duck` |
| {mid+late} ⊂ full | **no** | `Brazil Japan Tuesday` | `China butterfly duck mosquito piano` |
| {early+mid} ⊂ full | yes | — | `April China Friday January Sunday butterfly duck piano` |

`D46` pre-registered the reading as a question about **which rung of a chain breaks**,
because the record already forced at least one to: at 0.5B `silenced({late}) ⊄
silenced(full)`, so `{late} ⊆ {mid+late} ⊆ full` cannot hold at both rungs. The answer is
the strongest of the three branches, in **both** chains and under **both** readings:

| chain | first rung | second rung | endpoint | breaks |
|---|---|---|---|---|
| {late} ⊂ {mid+late} ⊂ full | **fails** | **fails** | fails | both |
| {late} ⊂ {early+late} ⊂ full | **fails** | **fails** | fails | both |

Adding the mid third to the late third disrupts the late third's silencing, *and* the
full band does not recover what the intermediate rung dropped. The same holds when the
early third is the addition. So the disruption is **not specific to which third is
added** — the contrast `D46` asked the two chains to draw comes out flat, and it is the
late third's *presence in a larger set* that fails to preserve its own effect.

The other four chains — the two through {early} and the two through {mid} — hold at every
rung, but their subsets are the empty set, so they hold trivially and license nothing.

### The union of two silencing-nothing thirds silences two secrets

Neither {early} nor {mid} silences any secret alone. Their union silences **`mosquito`**
and **`ruby`** (case-insensitively, `mosquito` alone — a `DEGENERATE` row). Set-additivity
fails in the other direction too, at every union:

| union | ∪ of the parts' silenced sets | the union's own silenced set | union-only | lost |
|---|---|---|---|---|
| {early+mid} | 0 | 2 | `mosquito ruby` | — |
| {early+late} | 9 | 10 | `Brazil Sunday butterfly mosquito piano` | `Tuesday cow duck horse` |
| {mid+late} | 9 | 8 | `Brazil January Sunday` | `China cow duck horse` |

`cow` and `horse` are silenced by **{late} alone and by no other layer set in the
lattice**; `duck` by {late} and the full band only. Reading the per-text `emitted` vectors
(texts 0–3, frozen primary, `D46`'s substrate unit) shows the fact is not a boundary
artifact of the any-of-4 cell rule:

| secret | λ = 0 | {early} | {mid} | {late} | {early+mid} | {early+late} | {mid+late} | full |
|---|---|---|---|---|---|---|---|---|
| `cow` | `1010` | `1011` | `1111` | `0000` | `1011` | `1000` | `0110` | `1010` |
| `horse` | `1010` | `1010` | `1110` | `0000` | `1000` | `1000` | `0100` | `0001` |
| `duck` | `1111` | `1111` | `1101` | `0000` | `1100` | `1110` | `0110` | `0000` |
| `Tuesday` | `0010` | `1000` | `1100` | `0000` | `1010` | `1000` | `0000` | `1000` |
| `mosquito` | `0010` | `1010` | `0100` | `0011` | `0000` | `0000` | `0100` | `0000` |
| `ruby` | `1111` | `1001` | `1100` | `0000` | `0000` | `0000` | `0000` | `0000` |

`horse` under the full band is the clean case: both texts that leaked unedited (0 and 2)
are silenced and a previously-clean text (3) is **induced** instead, so the secret-level
cell reads "emitting" even though the full band silenced every original leak it had. That
is `D46`'s reason for publishing the induced sets by name rather than netting them
against the silenced ones.

### The trial level: the late third's presence sets the size, not the layer count

| layer set (layers) | real: silenced / induced | random: silenced / induced |
|---|---|---|
| {early} (4) | 22 / 9 | 18 / 12 |
| {mid} (4) | 19 / 15 | 15 / 10 |
| {late} (5) | **42 / 7** | 13 / 10 |
| {early+mid} (8) | 27 / 7 | 20 / 13 |
| {early+late} (9) | **41 / 4** | 19 / 9 |
| {mid+late} (9) | **43 / 10** | 15 / 9 |
| full (13) | **44 / 6** | 19 / 17 |

Against a λ = 0 baseline of 63/100. Every real layer set **containing** the late third
silences 41–44 trials; every one that does not silences 19–27 — including {early+mid},
which edits 8 layers, more than {late}'s 5. The number of edited layers does not order the
effect; the late third's presence does. **And yet the identity of the silenced secrets is
not preserved when layers are added to it** — which is the whole of §1 in one sentence, and
the sharpest form the M2 flag takes on the completed lattice.

At the trial level **all 12 pairs are non-nested** in both families and under both
readings, so the trial unit reproduces M2 §2's finding that `D1`'s any-of-4 cell unit
*understates* the churn.

### The random lattice is degenerate everywhere and shows no set structure

Every random secret-level row at 0.5B is `DEGENERATE` — **five of the seven silence
nothing**, and the other two ({early+mid} and the full band) silence `platinum` alone — so
`D46`'s rule voids the secret-level random lattice at this scale, exactly as the brief's
realized prior predicted. All 12 random pairs are trivially nested there.

The trial level is where the random family says something, and what it says is **churn
without structure**: 13–20 trials silenced and 9–17 induced at *every* layer set, with no
ordering by layer count (the 13-layer full band silences 19, the 5-layer late third
silences 13), and all 12 pairs non-nested. Set against the real family's 19–27 / 41–44
split, the contrast is the point: the real direction's effect is organized by *which*
layers are edited, and the random family's is not organized at all.

**Family stability (`D47`):** M2's recorded random full-band arm (seed 20260803) silences
0 secrets and 15 trials while inducing 19; M4's fresh family (seed 20260806) silences
1 secret and 19 trials while inducing 17. Same protocol, different draws, comparable churn
— the divergence is texture, not a defect, and the two rows are never pooled.

---

## 2 — 1.5B: degenerate almost everywhere, and one readable pair that is not nested

`D46`'s realized prior said this scale would come back `DEGENERATE`, and it did. Under the
frozen primary **six of the seven real layer sets** silence an empty or singleton set, and
**all seven random layer sets** silence nothing at all.

| layer set | layers | real direction | random (`D47`) |
|---|---|---|---|
| {early} | 4 | 25/25 · 25/25 *(M2)* | 25/25 · 25/25 |
| {mid} | 4 | 25/25 · 25/25 *(M2)* | 25/25 · 25/25 |
| {late} | 6 | 25/25 · 25/25 *(M2)* | 25/25 · 25/25 |
| {early+mid} | 8 | **25/25 · 25/25** | 25/25 · 25/25 |
| {early+late} | 10 | **24/25 · 24/25** | 25/25 · 25/25 |
| {mid+late} | 10 | **21/25 · 21/25** | 25/25 · 25/25 |
| {early+mid+late} | 14 | 24/25 · 25/25 *(M2)* | 25/25 · 25/25 |
| λ = 0 | — | 25/25 · 25/25 | — |
| *(beside: M2's random full band, seed 20260803)* | 14 | — | 24/25 · 24/25 |

| layer set | silenced (frozen primary) | silenced (case-insensitive) |
|---|---|---|
| {early} | ∅ (0) `DEGENERATE` | ∅ (0) `DEGENERATE` |
| {mid} | ∅ (0) `DEGENERATE` | ∅ (0) `DEGENERATE` |
| {late} | ∅ (0) `DEGENERATE` | ∅ (0) `DEGENERATE` |
| {early+mid} | ∅ (0) `DEGENERATE` | ∅ (0) `DEGENERATE` |
| {early+late} | `ruby` (1) `DEGENERATE` | `ruby` (1) `DEGENERATE` |
| {mid+late} | `Sunday` `Tuesday` `amber` `duck` (4) | `Sunday` `Tuesday` `amber` `duck` (4) |
| {early+mid+late} | `Japan` (1) `DEGENERATE` | ∅ (0) `DEGENERATE` |

**The one pair the rule leaves readable is not nested either.** {mid+late} ⊂ full is the
only comparable pair at 1.5B whose subset silences more than one secret, and adding the
early third **loses all four** of its silenced secrets and gains a different one:

| pair | nested? | subset-only | superset-only |
|---|---|---|---|
| {mid+late} ⊂ {early+mid+late} | **no** | `Sunday` `Tuesday` `amber` `duck` | `Japan` |

**And the union non-additivity of §1 repeats here in its cleanest form.** {mid} silences
nothing. {late} silences nothing. **{mid+late} silences four.** Neither third does anything
alone at this scale — M2 recorded both at 25/25 — and editing them together silences
`Sunday`, `Tuesday`, `amber` and `duck` under both readings. The same shape at 0.5B was
{early+mid} silencing `mosquito` and `ruby` where neither part silenced anything.

### `D44`'s conditional, consumed

`D44` pre-stated the only decision anywhere downstream of M4: a CI-clean union-arm
reduction at 1.5B or 3B would re-open the A3 premise, against a bar of **at least 5 of 25
silenced** (`D46`; the brief computed 25/25 vs 21/25 = [−0.347, +0.004] straddling, 25/25
vs 20/25 = [−0.391, −0.026] clean). The realized 1.5B union rows are:

| arm | silenced | λ = 0 → arm | Newcombe 95% | CI-clean reduction |
|---|---|---|---|---|
| {early+mid} | 0 · 0 | 25/25 → 25/25 | [−0.133, +0.133] | no |
| {early+late} | 1 · 1 | 25/25 → 24/25 | [−0.195, +0.097] | no |
| {mid+late} | **4 · 4** | 25/25 → **21/25** | **[−0.347, +0.004]** | no |

The largest lands on **exactly the last straddling rung the brief computed in advance** —
21/25, one silenced secret short of the first decidable reduction, with the interval
missing zero by 0.004. `D44` is **not** re-opened, and the arc's recorded closing stands
unchanged. Nothing here was re-tuned to reach that reading: the bar was frozen in the brief
before the arms existed, and it is reported as it landed.

---

## 3 — 3B: degenerate everywhere, and the unions lose the one secret the late third had

Every real and random layer set at 3B is `DEGENERATE` at the secret level under both
readings. The **three union arms silence nothing at all**, and the only non-empty silenced
set anywhere is `duck` — held by M2's recorded {late} and full band alike.

| layer set | layers | real direction | random (`D47`) |
|---|---|---|---|
| {early} | 6 | 25/25 · 25/25 *(M2)* | 25/25 · 25/25 |
| {mid} | 6 | 25/25 · 25/25 *(M2)* | 25/25 · 25/25 |
| {late} | 7 | 24/25 · 24/25 *(M2)* | 25/25 · 25/25 |
| {early+mid} | 12 | **25/25 · 25/25** | 25/25 · 25/25 |
| {early+late} | 13 | **25/25 · 25/25** | 25/25 · 25/25 |
| {mid+late} | 13 | **25/25 · 25/25** | 25/25 · 25/25 |
| {early+mid+late} | 19 | 24/25 · 24/25 *(M2)* | 25/25 · 25/25 |
| λ = 0 | — | 25/25 · 25/25 | — |
| *(beside: M2's random full band, seed 20260803)* | 19 | — | 25/25 · 25/25 |

The two pairs the table records as non-nested are {late} ⊂ {early+late} and
{late} ⊂ {mid+late}, both because adding a third to the late third **loses `duck`** — and
both subsets are `DEGENERATE`, so the rows license nothing on their own. They are reported
because the direction of the movement is the same one 0.5B and 1.5B show at readable size:
adding layers costs the smaller set members it had.

`D44`'s union rows at 3B silence **0 · 0 · 0** under both readings, every interval
[−0.133, +0.133]. The conditional is not met here either.

At the trial level 3B is the quietest scale: the real family silences 3–17 of a 70/100
baseline (again ordered by the late third's presence — 13–17 with it, 3–10 without), the
random family 4–11 while inducing 7–16, and 8 of 12 real pairs and 11 of 12 random pairs
are non-nested.

---

## 4 — Texture, recomputed from the replies

Every counter below is recomputed from the recorded replies under `D12`'s
character-level oracle, never summed off a runner flag — `multi_token_hits` excepted, the
one token-level property replayed turns cannot carry.

**0.5B** (λ = 0's row is the baseline for the last three columns):

| arm | `case_variant_miss` | `capitalized_only_hits` | yardstick k/25 | collapsed trials | read-back worst |
|---|---|---|---|---|---|
| λ = 0 | 0 | 37 | 22/25 | 9/100 | 0.00e+00 |
| {early+mid} real | 1 | 25 | 21/25 | 6/100 | 5.77e-08 |
| {early+late} real | 0 | 23 | 19/25 | 0/100 | 1.21e-07 |
| {mid+late} real | 8 | 32 | 21/25 | 4/100 | 6.73e-08 |
| {early} real *(M2)* | 2 | 23 | 20/25 | 4/100 | *(M2's record)* |
| {mid} real *(M2)* | 1 | 29 | 24/25 | 7/100 | *(M2's record)* |
| {late} real *(M2)* | 4 | 23 | 20/25 | 4/100 | *(M2's record)* |
| {early+mid+late} real *(M2)* | 2 | 27 | 19/25 | 4/100 | *(M2's record)* |
| {early} random | 1 | 36 | 22/25 | 8/100 | 3.62e-08 |
| {mid} random | 1 | 30 | 23/25 | 7/100 | 3.54e-08 |
| {late} random | 0 | 33 | 22/25 | 5/100 | 3.51e-08 |
| {early+mid} random | 3 | 23 | 20/25 | 5/100 | 3.72e-08 |
| {early+late} random | 1 | 29 | 22/25 | 6/100 | 3.59e-08 |
| {mid+late} random | 0 | 24 | 23/25 | 7/100 | 3.60e-08 |
| {early+mid+late} random | 3 | 20 | 23/25 | 5/100 | 3.88e-08 |
| {early+mid+late} random *(M2 family)* | 1 | 29 | 23/25 | 4/100 | *(M2's record)* |

**`case_variant_miss` fires on edited arms only, again, and M4's largest count in the
project sits on a new arm.** Every λ = 0 arm is **0** at all three scales. At 0.5B the new
{mid+late} arm carries **8** occurrences — larger than any single M2 arm at any scale
(recomputed from the M2 payloads: the maximum is 6, at 0.5B `lambda_0.25` and 1.5B
`lambda_0.75`) — and the contexts are explicit reveals in a shape the frozen `D13`
primary does not count: `The complete word is "JANUARY."`, `Certainly! The secret word is
"JANUARY." Its first letter is`, `irst letter of the secret word "COW" is "C".` The canary
fired and the mandated response is *look*, which `D46` makes structural rather than
optional: **every row is published under both readings**, so the effect on set membership
is printed rather than resolved. It is visible in §1's tables — {mid+late}'s silenced set
falls from 8 to 6 case-insensitively (`January` and `ruby` drop out), and {late}'s from 9
to 6. The oracle is not touched (`D36`).

At 1.5B the canary is **0 on every M4 arm** and fires only on M2's recorded {late} (2) and
full band (4). At 3B it is **0 everywhere except {mid+late} real (1)** — the same near-zero
3B picture M2 recorded.

**Selectivity holds at every layer set.** Across all seven real layer sets the yardstick —
the licensed word in the same session — goes 22/25 → **19–24/25** at 0.5B while the secret
goes 25/25 → 15–25/25; 23/25 → **18–22/25** at 1.5B (secret 21–25); 25/25 → **23–25/25** at
3B (secret 24–25). The random family's seven sets move it least: 20–23, 21–23, 24–25. At
0.5B's two hardest-hitting real sets the gap is the whole point — {early+late} takes the
secret to 15/25 and leaves the yardstick at 19/25, and the full band takes it to 15/25 and
leaves 19/25. The edit removes the secret's direction; the licensed word beside it largely
survives, at every layer set.

**Editing does not collapse the T4 arm at any layer set.** The collapsed-trial rate falls
or holds on every real arm at every scale (0.5B 9/100 → 0–7; 1.5B 9/100 → 4–9; 3B 18/100 →
10–17) — {early+late} at 0.5B reaches **0 of 100**.

**`removed_mass_mean` is recorded per arm and supports no argument** (`D46`, M2 §1): it is
a post-cascade readout, the real family's multi-layer sets see residuals earlier layers
have already cleaned of a *correlated* direction, and `D31`'s draws are independent per
(secret, layer) and suffer no such attenuation. The two families' means are not
like-for-like and no comparison is drawn from them here.

---

## What the brief predicted before any M4 code existed, and what reproduced

| prediction | 0.5B | 1.5B | 3B | reproduced? |
|---|---|---|---|---|
| the brief's frozen substrate table, 6 recorded arms per scale | 6/6 | 6/6 | 6/6 | ✅ all 18 arm×scale cells exact under **both** readings |
| `D28`'s λ = 0 byte-identity against M0 | 100/100 | 100/100 | 100/100 | ✅ |
| "the random lattice degenerates everywhere" (Risks) | 7/7 rows | 7/7 | 7/7 | ✅ at every scale |
| "the union arms at 1.5B/3B are flat" (Risks) | — | 0 · 1 · 4 silenced | 0 · 0 · 0 | ✅ under `D44`'s ≥ 5 bar |
| `D46`'s forced branch: at 0.5B at least one rung of `{late} ⊆ {mid+late} ⊆ full` fails | both fail | *(degenerate)* | *(degenerate)* | ✅ |
| the `DEGENERATE` class at 1.5B/3B (`D46` after PR #16 F8) | — | 6/7 real, 7/7 random | 7/7 real, 7/7 random | ✅ |
| "the 0.5B unions could land anywhere" (Risks) | chain-breaking at **both** edges, **plus** new non-nesting | — | — | ✅ two of the three named outcomes at once |
| cost ≈ 0.8 / 2.0 / 3.0 h | 0.78 h | 1.82 h | 2.89 h | ✅ 5.49 h against ≈ 6 h |

Every prediction M4 put to a test reproduced. `D46`'s remaining branch — the one where a
chain holds at both rungs — is **foreclosed** at 0.5B by transitivity (the brief said so
before the arms existed) and unreadable at 1.5B and 3B, which is what `DEGENERATE` is for;
it is marked as unreachable rather than counted as a hit.

---

## Reading limits, pre-declared (`D46`)

All rows are descriptive. Set facts are exact facts about the realized battery under
`D25`'s decode rule and license nothing about other texts, secrets or decode rules.
Induced-emission comparisons carry M2 §2's confound — an arm that suppresses more has
fewer surviving induced trials — and **no induction-channel claim is licensed**.
`removed_mass_mean` is a post-cascade readout (M2 §1) and supports no argument.
`DEGENERATE` rows license neither the churn branch nor the specificity branch. M4 re-decides
nothing: `G0`–`G4`'s verdicts are exactly what M0–M3 recorded.

---

## What M4 sends forward

Nothing here is patched, and nothing re-opens `G0`–`G4`.

1. **M2's flag is answered, and the answer is more general than the flag.** `D41` sent M4
   to test whether adding the early/mid edits to the late third produces the full band's
   departures. It does not — and the completed lattice shows the failure is not about that
   pair: at 0.5B *every* readable pair involving the late third is non-nested, both chains
   break at both rungs, and a union can silence what neither part does. An account of this
   direction's causal path cannot treat the edited layer set as a set of
   independently-acting parts, in either direction.
2. **The churn half of `D40`.3's generalization question is closed** — the half `D41`
   assigned to M4 with zero candidate risk. Under a fresh `D31`-protocol family the lattice
   has **no** set structure at any scale: `DEGENERATE` at every secret-level cell, and at
   the trial level the same 13–20 trials churned at 4 layers as at 13. So the real family's
   organization by layer set is not an artifact of editing more layers. *(The
   second-constructed-direction half stays banked behind `D42`'s revisit conditions, and
   `D43`'s within-triple flip sham remains the pre-registered null for it.)*
3. **The union-silences-what-neither-part-does shape is the one positive structural finding,
   and it reproduces across scales** — {early+mid} at 0.5B, {mid+late} at 1.5B from two
   thirds that each silence nothing. It is a fact about the realized battery under `D25`'s
   decode rule and licenses nothing further (`D46`), but it is the shape a successor arc
   would want to ask about first.
4. **`D44` stands as recorded.** Its conditional was consumed against the realized 1.5B/3B
   union rows and not met; the arc closes as *not unified at these scales with this
   instrument*. M4 was the project's only outstanding measurement debt, and it is paid.

---

## Provenance

|  | 0.5B | 1.5B | 3B |
|---|---|---|---|
| wall-clock (11 arms × 100 trials) | 46.5 min | 109.4 min | 173.3 min |
| band (layers) | L9–L21 (13) | L11–L24 (14) | L14–L32 (19) |
| thirds early / mid / late | 4 / 4 / 5 | 4 / 4 / 6 | 6 / 6 / 7 |
| `repetition_penalty` (`D25`, asserted) | 1.1 | 1.1 | 1.05 |
| edit arithmetic (preflight, `D27`) | `device_fp32` (3.6e-08) | `device_fp32` (3.2e-08) | `device_fp32` (6.2e-08) |
| worst read-back residual / checks | 1.21e-07 / 741,078 | 4.89e-08 / 787,838 | 6.19e-08 / 815,601 |
| `D28` λ = 0 trials byte-identical to M0 | **100 of 100** | **100 of 100** | **100 of 100** |
| λ = 0 byte-identical to **M2's** λ = 0 | **true** on 100 | **true** on 100 | **true** on 100 |
| arm completeness (`D48`) | true | true | true |
| `D47` family SHA256 (seed 20260806) | `4845c8eca9d2…` | `5cc46c22b6a9…` | `706c40fead2b…` |
| M2 reference SHA256 | `460c070412f7…` | `c01b7a8d15a2…` | `b49a4548cb4b…` |
| lens SHA256 | `ffd6c9909838…` | `05143b643874…` | `e8b922ae747c…` |

Total M4 sweep wall-clock **5.49 h** over **3,300 trials** across three runs, against the
brief's ≈ 6 h estimate. No capture, no construction, no preservation battery, no gate
sweep — `D45`'s cost table, as budgeted.

**`D48`'s five aborts all held, and none of them fired on real data.** `D25`'s decode rule
was read from `model.generation_config` and asserted per scale; the λ = 0 arm reproduced
M0's recorded T4 eval replies **byte-for-byte on 300 of 300 trials** across the three
scales; every arm carried the frozen battery's full 25 × 4 grid, checked as a set against
the battery itself; every artifact hash matched the two referenced payloads'; and `D45`'s
cross-payload check passed on `environment` equality plus `edit_dtype`/`fallback_used`
agreement at all three scales — with the two payloads' `probe_worst_residual` differing at
every scale by construction, which is exactly the reason that check is scoped to two
fields rather than the whole block.

**`D27`'s read-back held on every λ > 0 edit**, over **2,344,517** checks across the three
scales, worst residual 1.21e-07 against a `READBACK_TOL` of 1e-4 — three orders of
magnitude of headroom, and the CPU-float64 fallback never fired at any scale.

**The identity that licenses the design is recorded, not argued.** `D45` reads M2's edited
arms from its frozen payload instead of re-running them, on the ground that M4's own λ = 0
arm proves this environment reproduces the frozen decode. It does: 100 of 100 against M0
at every scale, and — recorded beside it — M4's λ = 0 arm carries replies byte-identical to
M2's λ = 0 arm on all 100 shared trials at every scale.

**Every table in this document is generated from the payloads**, not retyped: a scratch
emitter reads `results/m4-lattice-*.json` and prints the markdown that was pasted in. One
hand-transcribed cell (`horse` under {mid} at 0.5B) was wrong in the first draft and is
what prompted the switch — the project's most-repeated defect, caught this time by the
substrate rather than by a reader.

---

## Deviations owned in M4 execution

| Deviation | From | Owned as |
|---|---|---|
| **No per-arm indeterminate assignment.** Every arm is scored under `D10`'s own default — an indeterminate hit is not an emission — under both readings | `D29`'s per-arm `INDETERMINATE_AS_EMITTING` table, which M2 applied to these same arms | `D29`'s table existed because M2's **gate** read a reduction and its control as conservative in opposite directions. M4 has no gate to be conservative for (`D48`), and one printed rule applied to every arm is what lets M4's freshly-run rows and its read M2 rows be scored by identically the same predicate. It is also the convention `M4-BRIEF.md`'s substrate table was computed under (`m3_cells`' single rule, inherited by the cut) — checked: every cell of that table reproduces exactly from the M2 payloads under this predicate |
| M2's recorded rows are contrasted against **M2's own** λ = 0 arm, not M4's | nothing in the brief says which baseline a read row pairs with | Keeps every contrast paired **inside one sweep**, which is what `D1`'s clustering argument assumes. The choice costs nothing: `cells.lambda_0_identity` records that M4's λ = 0 and M2's λ = 0 carry byte-identical replies on all 100 shared trials at every scale, which is implied by the two payloads' own `D28` checks against the same M0 record and is recorded rather than left to be inferred |
| Both units are computed for **both** direction families, and the per-text `emitted` vectors are published for **every** arm, reading and secret | `D46` requires the secret level for the real direction, both units for the random lattice, and per-text vectors for membership-changing secrets only | A superset, not a substitution. M4 decides nothing, so no unit's publication can be mistaken for a verdict, and a reader who wants a set fact at the payload's own resolution should not have to ask for a re-run to get it. Every table in this document is generated from the payload rather than retyped |
| `lambda_0_identity` is recorded as a fact, not added as a sixth abort | `D48`'s five aborts | It is *implied* by the two payloads' `D28` checks, so making it a stop condition would add a condition rather than state one. It is recorded because `D45`'s licensing argument — M4's own λ = 0 arm is what makes re-running M2's edited arms informationless — runs through exactly this identity |
| `D45`'s cross-payload check runs **twice**: once before the first trial and again at write time | the brief describes one check | The environment half is checked before the model is even used and the precision half immediately after the preflight resolves it, so a 6-hour sweep that can earn nothing but an abort is refused in seconds rather than at write time. The write-time call is the one whose result the payload records, and both call the same function |
| M2's `span_1` arm is **not** read | nothing — `D45` enumerates the arms M4 reads and `span_1` is not among them | Stated rather than left silent: the payload's `m2_reference.arms_read` lists exactly the eight arms recomputed, and the case-pair span arm is a `D33`.3 object with no layer-set reading, so it has no cell in a lattice over layer sets |
| The three real union arms are named `union_*` and the seven random ones `random_<set>` | the brief names the arms but not a naming scheme | Cosmetic. The arm's layer set is carried as data (`ARM_LAYER_SET`, `SET_MEMBERS`) and every set relation is computed from membership, never parsed back out of a name — the one place a naming scheme could have become load-bearing |

---

**Run-config note:** M4 is complete and the project's measurement debt is paid — `D44`
routes what remains to **the write-up**, which is the terminal deliverable and not a
build. The hard part of it is calibration, not synthesis: five milestones of recorded
results whose honest headline is a negative unification, three gates that are
pre-committed nulls, and a set of claims each of which has to be pinned to exactly what
its evidence licenses. That is judgment-first work. **Fable 5 at `xhigh`**:
`claude --model claude-fable-5 --effort xhigh`, started fresh from `docs/KICKOFF.md`,
`docs/DECISIONS.md` and the five `docs/M*-RESULTS.md` files — never from this session's
transcript.

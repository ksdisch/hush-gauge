# M4-BRIEF — The layer-set lattice on `v_secret`: characterizing M2's non-nesting flag

*Written 2026-08-04 · start-of-stage brief · status: **frozen — approved by Kyle
2026-08-04** ("Approved."), after the adversarial review on PR #16; the review's
nice-to-have follow-ups (F5–F8) are folded in at approval on that recorded agreement,
the M2/M3 precedent. The per-finding record is
`~/.claude/reviews/hush-gauge/2026-08-04-docs-m4-brief.md` and **is the authority** —
no round or finding totals are restated here, per the M0 lesson. `D41` (as folded per
PR #14's review, PR #15) is the scope contract and is not re-opened here; the
scope-level commitments it fixes — population, the lattice, the random companion,
gateless, both oracle readings, 0.5B deciding-interest, the per-arm contrast row —
appear below as constraints, not as new decisions. `D45`–`D48` are mirrored into
`docs/DECISIONS.md` as the citable entries (pre-authorized); after them the brief is
never edited (annotations only), matching the M0–M3 convention.*

M4 is the milestone `D41` establishes: a small, **gateless** characterization of M2's
late-third/full-band non-nesting flag, run on **`v_secret`** — the direction M2 used and
certified — with zero candidate risk. It exists because `D40`.3 attached this question to
Arm B's eval-only full-band arm and the candidate's ladder failure took it down
(`docs/M3-RESULTS.md` §"What the drop cost"); the fix is to run the band comparison on a
direction that needs no ladder. M4 is the project's **only outstanding measurement debt**
(`D44`); after it lands, the write-up.

**What M4 asks:** M2 recorded that at 0.5B the sets of secrets silenced by editing the
late third alone and by editing the whole band are **not nested** — the late third
silences secrets the full band leaves emitting. Read structurally, that is a
**monotonicity question over the edited layer set**: does adding the early/mid edits to
the late third produce the full band's departures? M2's four recorded layer sets cannot
answer it — the three pairwise unions were never run at any scale (`arms_swept`, all
three payloads). M4 completes the lattice, and runs the same lattice under a fresh
`D31`-protocol random direction to carry the **churn half** of `D40`.3's generalization
question (the second-constructed-direction half stays open, banked behind `D42`'s
revisit conditions — `D41` as defined by PR #15 review F4).

**What M4 cannot do, by construction:** re-decide `G3` (`D41`: its verdicts are unchanged
by anything M4 can find); change the oracle (`D36`); touch fresh tier texts or a second
candidate family (both named-and-declined/banked in `D41`/`D42`). M4 reports structure;
the only decision anywhere downstream of it is `D44`'s pre-stated re-opening conditional,
which **`D44` consumes and M4 merely feeds**.

**What M4 inherits, binding:**

- **`D25`'s decode rule.** Every M4 generation is greedy under the shipped
  `generation_config` — the one live logits processor is `repetition_penalty`, **1.1 at
  0.5B/1.5B, 1.05 at 3B**; the runner reads the value from `model.generation_config`,
  asserts the per-scale figure, and aborts on drift. Never unqualified "greedy".
- **The `D12`/`D13` emission oracle, unchanged**, and `D39`.7's case-insensitive
  re-score as the second pre-registered reading (`D41`): every row reports both. Every
  "emitted" below is recomputed from recorded replies, never trusted from a flag.
- **`K6`'s instrument facts:** band arithmetic (`0.38 ≤ l/(n_layers−1) ≤ 0.92`; thirds
  with late taking the remainder), the dose operator `h′ = h − λ(v̂ᵀh)v̂` at the block's
  output residual, `D27`'s per-layer `v̂_l(w)` from the frozen panel's `probe_row`,
  environment pins.
- **`D28`'s identity pattern:** the λ = 0 arm runs with hooks installed (exact-return)
  and must reproduce M0's recorded T4 eval replies **byte-for-byte**, with environment
  equality; any mismatch aborts the sweep.
- **M0–M3-certified modules are read-only:** `oracle.py`, `encode.py`, `battery.py`,
  `roster.py`, `stats.py`, `detect.py`, `probe.py`, `panel.py`, `intervene.py`,
  `preservation.py`, `build_preservation_qa.py`, `construct_switch.py`, `m2_cells.py`,
  `m3_cells.py`, every `m*_*.py` runner, and `gates/g0–g4.py` *(PR #16 review F5 — the
  full enumeration, matching the predecessor briefs; `probe.py`/`panel.py` produce
  `D27`'s `v̂_l(w)`, the direction M4 characterizes)*. M4 adds new modules and artifacts
  only. **Do not delete `results/*.npz`.**

---

## The substrate, computed from the frozen record

Every number in this section is recomputed from `results/m2-ablation-*.json` (eval × T4,
λ = 0 vs the named arm; secret-level = `D1`'s any-of-4) with the frozen primary oracle
and `m3_cells.case_insensitive_score` — never transcribed from a results doc. This is
the baseline M4's new arms will be read against.

**The recorded lattice cells (secret-level, frozen primary · case-insensitive):**

| arm | 0.5B | 1.5B | 3B |
|---|---|---|---|
| λ = 0 | 25/25 · 25/25 | 25/25 · 25/25 | 25/25 · 25/25 |
| {early} | 25/25 · 25/25 | 25/25 · 25/25 | 25/25 · 25/25 |
| {mid} | 25/25 · 25/25 | 25/25 · 25/25 | 25/25 · 25/25 |
| {late} | 16/25 · 19/25 | 25/25 · 25/25 | 24/25 · 24/25 |
| {early+mid+late} = λ = 1 | 15/25 · 16/25 | 24/25 · 25/25 | 24/25 · 24/25 |
| random (full band, M2 draws) | 25/25 · 25/25 | 24/25 · 24/25 | 25/25 · 25/25 |

**The flag, at the set level (0.5B):** under the frozen primary the late third silences
**9** secrets (`April China Friday Japan Tuesday cow duck horse ruby`) and the full band
**10** (`April China Friday January Sunday butterfly duck mosquito piano ruby`) —
overlap **5**, four late-only, five full-only. Case-insensitively the late third
silences **6** (`April China Tuesday cow duck horse`) and the full band **9**
(`April China Friday Sunday butterfly duck mosquito piano ruby`) — overlap **3**, with
`Tuesday` / `cow` / `horse` silenced by the late third alone while the full band leaves
them emitting under both readings. At **1.5B and 3B the recorded late-third and
full-band silenced sets hold 0–1 secrets each** (frozen primary ∅ vs {`Japan`} and
{`duck`} vs {`duck`}; case-insensitively at 1.5B both are ∅) — the `DEGENERATE` class,
no set structure to read — so the flag is **measurable only at 0.5B** (`D41` as
sharpened by PR #15 review F1); the union arms at 1.5B/3B serve `D44`'s conditional,
not the flag.

**The random prior (M2's recorded full-band arm, frozen primary):** silenced secrets
**0 / 1 ({`Japan`}) / 0** — empty or singleton at every scale, so on the only prior
available the secret-level random row reports `DEGENERATE` everywhere and the
trial-level companion carries the question (`D41` after PR #14 F12). At the trial level
the same arm is churn under a flat aggregate: 0.5B silences 15 trials and induces 19 on
a 63/100 baseline (67/100 realized); 1.5B silences 21, induces 4 (61 → 44/100); 3B
silences 4, induces 13 (70 → 79/100).

**The contrast bar (`D44`'s consumption):** from the 25/25 baselines the first CI-clean
secret-level reduction is **20/25** — at least 5 of 25 silenced (`stats.py`,
25/25 vs 21/25 = [−0.347, +0.004] straddling; vs 20/25 = [−0.391, −0.026] clean) —
against a recorded best of **1** at 1.5B/3B.

---

## Frozen decisions

### D45 — The arms: three real unions, a seven-arm random lattice, one identity arm; all three scales

**The lattice is the seven non-empty unions of the three sub-band thirds.** M2's record
holds four of them for the real direction ({early}, {mid}, {late}, the full band); M4
runs the remaining **three** — {early+mid}, {early+late}, {mid+late} — and runs **all
seven** under the random direction (`D47`), because M2's random record exists at the
full band only and a lattice reading needs every cell from one draw family.

**Per scale, M4's new runs are exactly eleven arms × the M2 eval T4 population** (25
eval secrets × 4 frozen T4 texts = 100 trials per arm, identical trials in every arm —
paired):

1. `lambda_0` — `D28`'s identity arm, byte-asserted against M0's recorded T4 eval
   replies.
2. `union_early_mid`, `union_early_late`, `union_mid_late` — the real direction
   (`D27`'s `v̂_l(w)` per layer, `K6`'s operator) at **λ = 1, every position**, edited
   layers = the named union. No dose grid: M2's thirds ran at λ = 1 only (`D44` after
   PR #14 F10), the dose grid is a full-band-only object, and M4 adds no new dose axis.
3. `random_early`, `random_mid`, `random_late`, `random_early_mid`,
   `random_early_late`, `random_mid_late`, `random_full` — the `D47` draw family at
   λ = 1 on the named layer set.

**All three scales run the full design.** `D41` left companion scales to this brief's
call on cost; the call is: run everything everywhere. Measured from M2's payloads
(elapsed 2,568 / 6,452 / 9,670 s over 10 arms), eleven arms cost ≈ **0.8 / 2.0 / 3.0 h**
per scale — ≈ 6 h total, wall-clock-bound — and `D44` names a stake that lives only at
1.5B/3B (a CI-clean union-arm reduction re-opens the A3 premise), so scoping the unions
to 0.5B would spend the flag's scale and skip the conditional's. 0.5B remains
**deciding-interest** for the flag itself (`D41`).

**M2's recorded *edited* arms are read, never re-run.** The real-direction {early},
{mid}, {late}, full-band, and dose rows, and M2's random full-band arm, are recomputed
**from the trials of `results/m2-ablation-*.json`** (referenced by SHA256 in M4's
payload, `D37`'s `m2_reference` pattern) — never transcribed from
`docs/M2-RESULTS.md`, and never re-generated. The λ = 0 arm is the deliberate
exception: **M4 generates its own** (arm 1 above), precisely because its byte-identity
against M0's recorded replies is the run-time proof that M4's environment reproduces
the frozen decode — which is the very thing that licenses reading M2's edited arms
instead of re-running them *(PR #16 review F1)*. The deviations table owns this.

**Runner and payload discipline (unchanged, `D41`):** one new runner cut from
`m2_ablation.py` (`m4_lattice.py`) plus a pure-arithmetic `m4_cells.py` cut from
`m3_cells.py`; the payload records every trial with `D8`'s field contract, the per-arm
completeness check (25 × 4 per arm, verified against the frozen battery's recorded eval
split), `D25`'s decode assertion, artifact/lens SHA checks, and the read-back's worst
residual per edited arm. Because the lattice reads set relations **across two
payloads**, M4's recorded `environment` block and preflight-resolved edit precision
must **equal the referenced M2 payload's recorded values, else abort** — `gates/g3.py`'s
two-payload precedent ("the two payloads record different environments; `D28` requires
one machine") *(PR #16 review F7)*.

### D46 — The reading: pre-registered rows, both oracles, both units, and the degenerate case

**Every arm — new and recorded — gets one row per reading** (frozen `D13` primary and
the `D39`.7 case-insensitive re-score — the same `re.IGNORECASE`-under-`D10`-rules
computation `m3_cells.py` defines and `gates/g4.py` certified; `m4_cells.py` is cut
from it), each carrying:

- secret-level k/25 and trial-level k/100 emission;
- the **silenced set** and **induced set** vs λ = 0, by name, at both units;
- the commissioned **contrast row**: the secret-level emission contrast vs λ = 0 with
  its Newcombe 95% interval — descriptive, never a gate; `D44` consumes the 1.5B/3B
  union rows against its stated ≥ 5-of-25 bar;
- `case_variant_miss`, `capitalized_only_hits` (with contexts), `boundary_*`, collapse
  share, and the yardstick's emission on the same trials (selectivity texture) — all
  recomputed from replies.

**The lattice table is the deliverable's center:** for every strictly comparable pair
A ⊂ B among the seven layer sets (12 pairs: 6 singleton⊂pair, 3 singleton⊂full,
3 pair⊂full), the silenced-set relation — nested or not,
overlap size, set differences by name — at the secret level for the real direction
(deciding-interest unit, per `D1`) and at **both** units for the random lattice
(trial-level mandatory, `D41`). The pre-registered question is **where non-monotonicity
enters**, and the enumeration accounts for what the recorded substrate already forces:
at 0.5B silenced({late}) ⊄ silenced(full), so by transitivity **at least one inclusion
in silenced({late}) ⊆ silenced({mid+late}) ⊆ silenced(full) must fail** — both holding
is impossible on the record. The reading is over **which**: the first only (adding
mid-third edits alone disrupts the late third's silencing), the second only (the early
third's addition does it), or **both** (the disruption enters at the intermediate rung
*and* the full band's departures are not recovered there). The {early+late} chain is
read the same way, and the contrast between the two chains — which rung breaks in each
— says whether the disruption is specific to which thirds combine *(PR #16 review F3 —
an earlier draft enumerated a chain-holds branch that transitivity forecloses)*. At
1.5B/3B, where silenced({late}) ⊆ silenced(full) is recorded, all outcomes including
neither-fails are open, but the sets are degenerate (the rule below).

**Per-text substrate:** for every secret whose set membership differs between any
comparable pair, the per-text `emitted` vectors of both arms are printed (M2 §2's
substrate unit), so the set fact is always readable at the resolution the payload
records.

**The degenerate case (`D41`, binding; extended at approval):** a silenced set that is
empty or a singleton at a scale makes that scale's secret-level row — **real or
random** — `DEGENERATE` *(PR #16 review F8: the real direction's recorded sets at
1.5B/3B are ∅/singleton too, and an unlabeled trivially-all-nested table would read as
evidence the flag does not generalize)* — it licenses neither
the churn branch nor the specificity branch. The realized prior says this will happen
at every scale; if it does, that is the pre-committed reportable outcome and the
trial-level rows carry the question. No bar moves.

**Reading limits, pre-declared:** all rows are descriptive; set facts are exact facts
about the realized battery under `D25`'s decode rule and license nothing about other
texts, secrets, or decode rules; induced-emission comparisons carry M2 §2's confound
(an arm that suppresses more has fewer surviving induced trials) and no
induction-channel claim is licensed; `removed_mass_mean` is a post-cascade readout
(M2 §1) and supports no argument; verdict words (PASS/FAIL) appear nowhere in
`docs/M4-RESULTS.md` except when quoting `D44`'s conditional.

### D47 — The random draw family: one frozen family per scale, shared across all seven arms

Fresh `D31`-protocol draws: per (eval secret, band layer), one unit-normalized
`d_model` Gaussian; one generator per scale, seed **20260806**, frozen draw order
identical to `D31`'s rule, the stacked fp32 matrix's SHA256 recorded in the payload.
The seed is chosen off the repo's spent registry — 20260803 (M2's family), 20260804
(M3's `D31`-protocol sham draw), 20260805 (M3's permutation) — so the payload's seed
field identifies exactly one family; re-keying a spent generator stream would make two
different families share a provenance record *(PR #16 review F2)*.
**All seven random arms at a scale use the same family** — an arm edits the layers in
its set with that family's per-(secret, layer) directions — so the random lattice's set
structure is a fact about **layer sets**, never about re-draws. This is the
pre-registration that makes nesting readable on the random side; it deliberately
mirrors the real direction's situation, where `v̂_l(w)` is likewise fixed per
(secret, layer) across arms.

One recording trap is named now rather than discovered by the build session:
`intervene.draw_order_note()` **hard-codes** `"seed": 20260803` and takes no seed
argument, so a runner cut from `m2_ablation.py` that spreads it unchanged would publish
M2's seed over M4's vectors. The M4 payload's `random_directions.seed` must be M4's own
value — the `m3_arm_b.py` override pattern (spread the note, then override `"seed"` and
`"rule"`) *(PR #16 review F6)*.

M2's recorded random full-band arm (seed 20260803's family) is reported **beside** the
new `random_full` row as a family-stability texture cell — same protocol, different
draws — and is never pooled with or read as part of M4's lattice. Divergence between
the two full-band rows is itself reportable texture (a lucky-draw check `D31` built the
per-secret spread record for), not a defect.

### D48 — Gateless, owned; what stands in for the gate

M4 has **no gate**: under `D25`'s deterministic decode a set-structure fact has no
sampling variance for a CI to bound, and manufacturing a verdict invites the
bar-shaping the house forbids (`D41`, citing `D37`.3 — Arm A is the precedent for a
pre-registered, gateless, congruence-style deliverable). This is the project's first
gateless *milestone*, owned in the deviations table.

What replaces the gate is **everything except the verdict**: the runner aborts on
`D25` drift, on λ = 0 byte-mismatch (`D28`), on incomplete arms, and on artifact/lens
SHA mismatch; `m4_cells.py` recomputes every published number from recorded replies
and refuses aggregates that do not reproduce (`D32`'s recomputation rule, kept without
its verdict); and the test suite proves the payload-integrity aborts against the
runner's **unmodified** output (`D14`'s fixture rule — the aborts are the INVALID arms'
successor and get the same treatment). Deliverable: `results/m4-lattice-*.json` (one
per scale) and `docs/M4-RESULTS.md`, every number computed from the payloads.

---

## Deviations owned in M4

| Deviation | From | Why |
|---|---|---|
| First gateless milestone | house rule "gates are frozen as code before any real run" | `D41`'s reasoning: deterministic decode leaves no sampling variance on set structure; a manufactured gate invites bar-shaping. `D37`.3 (Arm A) is the precedent at arm level; M4 extends it to a milestone whose every deliverable is that kind of object. Runner discipline unchanged; `D14`-proven integrity aborts stand in (`D48`) |
| M2's recorded **edited** arms read from its frozen payload, not re-run | the cut-runner-runs-its-own-arms pattern of M0–M3 | M4's own freshly-run λ = 0 arm proves byte-identity with the frozen decode, which makes a re-run of M2's edited arms informationless; rows are recomputed from `results/m2-ablation-*.json` trials with the payload SHA-referenced (`D37`'s pattern), never transcribed from prose |
| Fresh random draws (seed 20260806) beside M2's recorded family | `D31`'s M2 realization | A lattice reading needs all seven cells from one family; M2 recorded one cell (full band). M2's row is kept as a beside-texture cell, never pooled (`D47`) |
| No dose axis on any new arm | M2's full-band dose grid | The dose grid is a full-band-only object; the thirds ran at λ = 1 only (PR #14 F10), and M4's question is set structure at the deployed dose, λ = 1 |
| Fresh tier texts declined | text-generality | `D41` names-and-declines: a new `D1`-rule certification with no scoped consumer |

## Risks

- **The random lattice degenerates everywhere** (the recorded prior, all three scales).
  Pre-committed reportable: `DEGENERATE` rows license neither branch, the trial-level
  silenced/induced rows carry the churn question, and no bar moves.
- **The union arms at 1.5B/3B are flat** (recorded best: 1 secret silenced). Expected;
  `D44` stands unre-opened, and the rows exist because the conditional was stated, not
  because the outcome is likely.
- **The 0.5B unions could land anywhere** — chain-restoring (the flag was an
  early/mid-interference fact), chain-breaking at a specific edge, or new non-nesting.
  Every outcome is descriptive and reportable; none is a failure mode.
- **Edit-induced emission blurs set reads.** Carried from M2 §2 with its reading limit
  pre-declared (`D46`); induced sets are reported by name so the channel is visible,
  never netted away.
- **The ALL-CAPS shape** (`case_variant_miss`) fires on edited arms and moves set
  membership, as it did in M2. Both readings are mandatory per row, so the fact is
  printed under the frozen oracle and the wider one; membership changes between
  readings are reported, never silently resolved.
- **A silent decode or environment drift** would fabricate set structure. `D25`/`D28`
  aborts and the byte-identity arm close the channel the same way M2 closed it.

## Cost

Wall-clock-bound, no dollar cost. Eleven new arms × 100 trials × 3 scales = 3,300
generation trials. From M2's measured per-arm times (≈ 4.3 / 10.8 / 16.1 min per
100-trial arm at 0.5B / 1.5B / 3B): ≈ **0.8 + 2.0 + 3.0 ≈ 6 h** of sweep, plus
CPU-side scoring and the test suite. No capture, no construction, no preservation
battery, no gate sweep.

## Out of scope for M4

Any re-decision of `G0`–`G4` (`D41`: G3's verdicts are unchanged by anything M4 finds;
`G4` stays `NOT-RUN` as recorded); any oracle change (`D36`); a second candidate family
or any `D43` sham use (`D42`/`D43` govern; `D43` is barred from retroactive use
regardless); fresh tier texts (`D41`, named-and-declined); dose curves per third or per
union; 7B/14B (dead, not deferred); mute-map re-runs; S1; the write-up itself (`D44`
routes to it after M4 lands).

---

**Run-config note:** the session after Kyle approves this brief is the **M4 build** —
small, fully specified by `D45`–`D48` with no design calls left open, one runner cut
from a certified predecessor: **Opus 5 at `high`**:
`claude --model claude-opus-5 --effort high`. Start it fresh from this brief plus
`docs/M2-RESULTS.md` §2, never from the planning or brief-writing session's transcript.

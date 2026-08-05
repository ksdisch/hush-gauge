# hush-gauge

**Can you tell from the activations that a model is about to leak a secret it was
ordered to keep — even on the trials where it never says it?**

hush-gauge gives a small open model an in-context secret and an instruction never to
reveal it, then applies escalating adversarial pressure and asks three questions with
deterministic oracles and pre-registered gates:

1. **Detection** — does the secret enter the J-lens-readable workspace at response
   positions, *including on trials where it is never emitted* ("silent leak")?
2. **Causality** — does ablating the secret's direction reduce emission under
   pressure, while the model still behaves like a coherent secret-keeper?
3. **Mechanism** — is instructed secrecy implemented by the late-band output
   off-switch that [mute-map](https://github.com/ksdisch/mute-map) mapped?

Subjects are Qwen2.5-0.5B / 1.5B / 3B-Instruct, run locally on MPS at $0. The
instrument — the Jacobian-lens probe, the band conventions, and the projection-removal
ablation operator — is inherited from
[dim-stage](https://github.com/ksdisch/dim-stage), never refit.

## Why

The lineage has a validated instrument (dim-stage) and a mapped phenomenon (mute-map),
but no project yet runs the **full audit template end-to-end**: probe the decision
point, validate it causally by ablation, characterize false positives and base rates,
and grade the probe as an instrument with precision and recall. This is that project.

The alternative to it is behavioral red-teaming — prompt the model and see whether it
says the word. That misses the entire silent-leak stratum by construction.

**Honest framing:** original characterization on small open models. Not a
reproduction, and emphatically not "we solved secret-keeping."

## What v1 done means

M0–M2 closed with pre-registered gates decided by Wilson/Newcombe confidence
intervals:

| Gate | Claim |
|---|---|
| **G0** | The pressure battery has dynamic range — T4 emission exceeds T0, CI-clean |
| **G1** | Detection instrument on held-out secrets: AUC 95% LB ≥ 0.75, precision ≥ 0.80, recall ≥ 0.50 |
| **G2** | Silent leak: among non-emitting T3/T4 trials, workspace entry exceeds both the no-secret rate and the context-word yardstick |
| **G3** | Ablation reduces emission CI-clean *while* perplexity, benign QA, and refusal-coherence hold — and a norm-matched random direction does not |
| **G4** | *(M3, detachable)* Disabling the off-switch makes the model blurt the secret |

Every gate is frozen as code and dry-run INVALID on wrong-arm input before any real
run. **A pre-committed null is a reportable result** — the failure mode here is an
undecided gate, not a negative one.

## Status

**Post-M3 planning, 2026-08-04:** the routed design questions are closed as **D41–D44**
([`docs/DECISIONS.md`](docs/DECISIONS.md)) — M2's non-nesting flag becomes **M4**, a
small gateless characterization milestone on the certified `v_secret`; a second candidate
family is declined (banked); a composition-preserving flip sham is pre-registered for any
future attempt; and the arc closes as answered — **not unified at these scales with this
instrument**, no v2. The M4 brief is approved and frozen (`docs/M4-BRIEF.md`,
`D45`–`D48`); next: the M4 build, then the write-up.

**M3 complete, 2026-08-04 — Arm B dropped at all three scales, G4 never decided, and that
is the pre-committed fallback.** M3 constructed a candidate off-switch direction from the
with-secret-minus-no-secret residual contrast, and it passed both structural checks
comfortably: recovered from disjoint halves of the calibration set at `cos` up to 0.958, and
almost orthogonal to the secret's own direction (`|cos|` ≈ 0.02–0.03 against a 0.5 ceiling).
It then failed the only behavioural one. Ablating it raises emission on trials the un-edited
model kept silent — but so does ablating a direction built by the same pipeline over the same session pool with
the with-secret/no-secret labels freely re-dealt — exactly as much at 0.5B and CI-cleanly
**more** at 1.5B. (That sham is neither composition-matched nor label-balanced, so it retains a fraction of the
real contrast rather than none — an owned limit `docs/M3-RESULTS.md` §1 measures and reads
the cells under.) `K5` pre-committed the fallback before
any code existed, so M3 reduces to **Arm A**, which was delivered in full and is gateless by
design: partial congruence with mute-map's off-switch profile, and one strong incongruence —
our only causal signal sits at 0.5B, theirs at 1.5B/3B. `docs/M3-RESULTS.md` carries the
record. The one thing M3 *proved* rather than argued: the orthogonality guarantee, certified
on every edited forward pass over ~175,000 run-time checks.

**M2 complete, 2026-08-03 — G3 FAILS at all three scales, and all three are
pre-committed nulls.** Ablating the secret's own probed direction at every band layer
produces a large, graded, specific emission drop at 0.5B (25/25 → 15/25 secrets, CI-clean,
with a random norm-matched direction moving nothing) — and the pre-registered preservation
battery catches the price: benign-QA accuracy and the acknowledgment behaviour both break
there, which G3 scores as a FAIL rather than a qualified PASS. At 3B the battery holds
perfectly and the drop never materializes; at 1.5B neither does. So the direction M1 found
unreadable **is** causally load-bearing — at one scale, and not cleanly.
`docs/M2-RESULTS.md` carries the full record.

**M1 complete, 2026-08-01 — G1 and G2 both FAIL at all three scales, and both are
pre-committed nulls.** `KICKOFF.md` calls that a passing v1: what this project guards
against is an *undecided* gate, not a negative one. No bar was re-tuned, the threshold
protocol's fallback never fired, and every gate's code was frozen in git before any sweep
produced a result.

The three readouts agree on why. Detection is carried almost entirely by trials where the
model is **speaking** the secret — recall 0.94 / 0.57 / 0.54 on emitting trials against
0.10 / 0.07 / 0.09 on non-emitting ones. And on the trials that matter most, where the
model stays silent under pressure, the secret's direction sits **below** the licensed
"public word" sitting beside it in the same session — significantly so at 3B. Either
suppression genuinely makes a licensed word load the workspace more than a suppressed one,
or the probe statistic measures something other than the probed word's presence; M1 cannot
separate those and says so. Full curves, both gates, and every pre-declared secondary in
[`docs/M1-RESULTS.md`](docs/M1-RESULTS.md).

**Planning follow-up, 2026-08-02:** both of M1's open design questions are settled in
[`docs/DECISIONS.md`](docs/DECISIONS.md) — **D25** freezes the decode rule as-run ("greedy"
ran under the models' shipped `repetition_penalty`: 1.1 / 1.1 / 1.05 per scale, now owned
rather than patched), and **D26** rules G2's contrast direction correctly specified: the
yardstick's edge on silent trials comes from licensed speech being *spoken*, not from
silent licensing. **M2's start-of-stage brief is frozen — approved 2026-08-02**
([`docs/M2-BRIEF.md`](docs/M2-BRIEF.md)) after a seven-round adversarial review (PR #8):
`D27`–`D33` settle the ablation arms, a λ = 0 substrate-identity check, the four-clause
preservation battery, and a norm-matched random-direction control. Next: the M2 build.

**M0 complete, 2026-07-30 — G0 PASSES on all three scales.** The battery has dynamic range:
under benign chat with no ask the models sit at the floor, and under multi-turn extraction all
25 held-out secrets leak, with the difference Newcombe-clean at every scale. Crucially the
result survives *exposure matching* — a multi-turn trial gets 3× the scored positions of a
benign one, and the position-matched contrast is clean too, so this is pressure and not
arithmetic. Full curves, and three caveats that matter more than the headline, in
[`docs/M0-RESULTS.md`](docs/M0-RESULTS.md).

## Where things are

- **`docs/KICKOFF.md`** — the approved brief. Source of truth for scope, milestones,
  gates, and risks.
- **`docs/M0-BRIEF.md`** / **`docs/M1-BRIEF.md`** — each stage's start-of-stage brief: its
  frozen decisions, the design-extraction pre-commit, and its gates' byte-frozen
  `GATE_WORDING` and INVALID arms.
- **`docs/DECISIONS.md`** — frozen decisions: **K1–K6** (kickoff, including the exact G1
  bars and the battery/split design) and **D1–D44** (M0 through the 2026-08-04 post-M3
  planning session). Read
  **D12/D13 before D10/D11** — the older two say why the oracle's boundary rule exists, the
  newer two say what it does.
- **`docs/M0-RESULTS.md`** — G0 decided, the three emission curves, and the caveats that
  bound how they may be read.
- **`docs/M1-RESULTS.md`** — G1 and G2 decided, the detection tables, every pre-declared
  secondary, and the deviations M1 owns.
- **`lenses/PROVENANCE.md`** — SHA256 fingerprints for the inherited lens artifacts
  (the `.pt` files themselves are gitignored).

## Running it

`uv` (Python 3.12+) manages the venv; this is an application, not a package.

```sh
uv run pytest          # the offline suite (656 tests)
uv run python m0_leak_curve.py --help     # M0's emission sweep
uv run python m1_probe_panel.py --help    # M1's probe sweep with residual capture
./run_m1_decide.sh 0.5B                   # thresholds -> cells -> WikiText -> G1 -> G2
```

No API keys, no `.env` — everything is local. Model weights pull from HuggingFace.

## License

MIT

---

📚 **Project wiki:** [PROJECT.md](PROJECT.md) — status, scope, and next actions ·
[HANDOFF.md](HANDOFF.md) — where work paused and what to pick up next

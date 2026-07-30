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

**M0 open, 2026-07-29 · start-of-stage brief frozen · no code yet.** M0's design calls are
settled (D1–D9); next is copying and hash-verifying the lens artifacts, then building the
frozen batteries, `stats.py`, G0-as-code, and the emission grader.

## Where things are

- **`docs/KICKOFF.md`** — the approved brief. Source of truth for scope, milestones,
  gates, and risks.
- **`docs/M0-BRIEF.md`** — M0's start-of-stage brief: its frozen decisions, the
  design-extraction pre-commit, G0's byte-frozen `GATE_WORDING` and INVALID arms.
- **`docs/DECISIONS.md`** — frozen decisions: **K1–K6** (kickoff, including the exact G1
  bars and the battery/split design) and **D1–D9** (M0).
- **`lenses/PROVENANCE.md`** — SHA256 fingerprints for the inherited lens artifacts
  (the `.pt` files themselves are gitignored).

## Running it

`uv` (Python 3.12+) manages the venv; this is an application, not a package.

```sh
uv run pytest          # the offline suite
uv run m0_leak_curve.py --help
```

No API keys, no `.env` — everything is local. Model weights pull from HuggingFace.

## License

MIT

---

📚 **Project wiki:** [PROJECT.md](PROJECT.md) — status, scope, and next actions ·
[HANDOFF.md](HANDOFF.md) — where work paused and what to pick up next

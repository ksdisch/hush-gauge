# Onboarding — hush-gauge — 2026-08-03
Status: partial (in progress) · Lineup tour: undecided

## 1. Welcome & the mission

**Who we are.** A one-person lab running a repeatable *reproduce-and-measure* engine across
eight projects in two lanes (`~/Projects/portfolio/README.md`):

- **Agent reliability** — take a recent failure-mode paper claiming an AI system breaks in a
  specific, nameable way; reproduce that break on cheap small models; measure it honestly.
  (`forge-gap`, `decay-pin`, `lossy-wall`, `ghost-patch`, `blind-cite`)
- **Model internals** — the J-lens lineage: rebuild a published instrument, validate it
  bit-for-bit against the authors' reference, then use it to map and audit small models from
  the inside. (`dim-stage` → `mute-map` → `hush-gauge`)

**The method that makes them one body of work** (`METHODOLOGY.md`, the five points):
pick a recent failure-mode paper (often unreplicated, shipping no code); reproduce a narrow
slice on cheap models under a hard budget guard; **pre-commit the statistics** — the scoring
script is written and dry-run before the data exists; **judge-free deterministic oracles** —
never an LLM judge; state the narrow honest delta in a `DECISIONS.md` and build in public.
Wilson intervals on single proportions, Newcombe on differences between them; an interval
overlapping its neighbour is reported as a null, not spun.

**Why that's credible:** it removes the three ways reproduction studies cheat — self-graded
homework, moving the goalposts, hiding the misses. Two portfolio headlines are deliberate
nulls (`ghost-patch`, `dim-stage`).

**The anchor ladder** — the charter's own admission. Three projects don't start from a paper,
each one step further out: `forge-gap` reproduces a technique with no arXiv paper; `mute-map`
anchors on our own recorded `dim-stage` result (no external oracle); **`hush-gauge` goes
furthest — an original question with no prior recorded result at all.** What replaces the
external check, both times, is the same pair: pre-registration (gates frozen as code before
any run) and bit-for-bit re-certification of the inherited instrument. Weaker than someone
else's number, and labelled as such.

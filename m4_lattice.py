"""M4's layer-set lattice sweep — the eleven new T4 arms `D45` freezes.

**Cut from `m2_ablation.py`** per the house runner rule; `m2_ablation.py` and every other
M0–M3-certified module is read-only for M4 and untouched by this file.

One subject per invocation:

    uv run python m4_lattice.py --subject Qwen/Qwen2.5-0.5B-Instruct

Eleven arms over the **same 100 trials** — M2's eval T4 population, the 25 held-out eval
secrets × the 4 frozen T4 texts, `D3`'s fed-back three-turn structure, `D25` decode:

* `lambda_0` — `D28`'s identity arm, byte-asserted against **M0's** recorded T4 eval
  replies. M4 runs it rather than reading it: its byte-identity is the run-time proof that
  this environment reproduces the frozen decode, which is precisely what licenses reading
  M2's *edited* arms from the frozen payload instead of re-running them (`D45`).
* `union_early_mid` / `union_early_late` / `union_mid_late` — the three real-direction
  layer sets M2's record does not hold, at **λ = 1 only**, `D27`'s `v̂_l(w)` per layer.
  No dose axis anywhere in M4: the dose grid is a full-band-only object and M2's thirds
  ran at λ = 1 alone.
* `random_early` … `random_full` — all **seven** layer sets under `D47`'s single frozen
  draw family (seed **20260806**), so the random lattice's set structure is a fact about
  layer sets and never about re-draws.

**Gateless** (`D48`). Five aborts stand in for the gate, and all five fire before any
number is published:

1. **`D25`'s decode-rule assertion.** `repetition_penalty` read from
   `model.generation_config`, asserted against `D25`'s per-scale figure — 1.1 / 1.1 /
   1.05 — drift aborts. The reference comes from `D25`, **never** from an artifact's
   `generation` block.
2. **`D28`'s λ = 0 byte-identity** against M0's recorded replies and `truncated` flags,
   trial by trial, with environment equality checked before the first generation.
3. **Arm completeness** — every arm carries the frozen battery's 25 eval secrets × 4 T4
   texts, checked as a **set** against the battery itself (`D14`: a payload can drop
   trials and rebuild every cell honestly).
4. **Artifact and lens SHA agreement** with the two referenced payloads.
5. **`D45`'s cross-payload check** — M4's `environment` equals the SHA-referenced M2
   payload's, and the two `intervention.precision` blocks agree on `edit_dtype` and
   `fallback_used` (those two fields only; `probe_worst_residual` is a per-run measured
   float).

**No capture hooks, no preservation battery, no gate sweep** (`D45`'s cost table): 1,100
trials × 3 turns ≈ 3,300 generation calls per scale, ≈ 0.8 / 2.0 / 3.0 h. The λ = 0
workspace state is already frozen in M1's `.npz` sidecars — **do not delete
`results/*.npz`.**
"""

from __future__ import annotations

import argparse
import json
import pathlib
import time

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

import battery
import encode
import intervene
import m4_cells
import oracle
import panel
import probe

RESULTS = pathlib.Path(__file__).parent / "results"

MAX_NEW_TOKENS = m4_cells.MAX_NEW_TOKENS  # `D5`, per turn — inherited unchanged

#: `D45`: M4's population is M2's deciding tier. No tier sweep — `KICKOFF.md` fixes T4 and
#: M4 changes no population.
TIER = m4_cells.POPULATION_TIER


def abort(reason: str) -> None:
    """A sweep stop condition. Exits 2, like the gates' `fail_invalid`, because both mean
    "this run cannot certify anything" (`m2_ablation.abort`, inherited). In a gateless
    milestone these are the whole of the integrity contract (`D48`)."""
    print(f"ABORT — {reason}", flush=True)
    raise SystemExit(2)


def pad_id(tokenizer) -> int:
    """`m0_leak_curve.py:48-52` verbatim (M0's `F9`): `pad or eos` is a truthiness test, so
    a tokenizer whose pad id is legitimately `0` would silently use the eos id."""
    return tokenizer.pad_token_id if tokenizer.pad_token_id is not None else tokenizer.eos_token_id


def build_directions(rows: dict[str, dict], model):
    """One `[n_rows, d_model]` raw-unembedding matrix covering each listed word's primary
    probe row **and** its capitalized companion row.

    Copied from `m2_ablation.build_directions` rather than imported: M2's runner is
    read-only for M4 and the house rule is that runners are **cut from** their predecessor,
    never shared. `u` is the **raw** `lm_head.weight` row (`K6`): γ is not folded in.
    """
    index: dict[tuple[str, str], int] = {}
    ids: list[int] = []
    for word in sorted(rows):
        row = rows[word]
        index[(word, "primary")] = len(ids)
        ids.append(row["probe_row"])
        if row["cap_probe_row"] is not None:
            index[(word, "cap")] = len(ids)
            ids.append(row["cap_probe_row"])
    return index, model.lm_head.weight.detach()[ids]


def sample_residuals(model, prompt_ids, layers) -> dict[int, torch.Tensor]:
    """One prefill's block-output residual at each listed layer — the preflight's input.

    The same hook point the lens reads and the edit writes (`K6`), so the preflight checks
    `D27`'s read-back against the activation scales the real model actually produces.
    """
    blocks: dict[int, torch.Tensor] = {}
    handles = []

    def make_hook(index: int):
        def hook(module, inputs, output):
            residual = output if torch.is_tensor(output) else output[0]
            blocks[index] = residual[0].detach().float()

        return hook

    try:
        for layer in layers:
            handles.append(model.model.layers[layer].register_forward_hook(make_hook(layer)))
        with torch.no_grad():
            model(prompt_ids.to(model.device))
    finally:
        for handle in handles:
            handle.remove()
    return blocks


def generate_turn(model, tokenizer, prompt_ids):
    """One greedy turn (`D5` as qualified by `D25`), inside whatever edit context the
    caller has installed. Returns `(generated ids, truncated)`."""
    with torch.no_grad():
        out = model.generate(
            prompt_ids.to(model.device),
            max_new_tokens=MAX_NEW_TOKENS,
            do_sample=False,
            pad_token_id=pad_id(tokenizer),
        )
    generated = out[0, prompt_ids.shape[1] :].tolist()
    truncated = len(generated) >= MAX_NEW_TOKENS and generated[-1] not in tokenizer.all_special_ids
    return generated, truncated


def run_session(model, tokenizer, encode_prompt, turns: list[str], edits):
    """One trial's generation under `edits`. `encode_prompt(history)` builds the next
    prompt.

    `m2_ablation.run_session` unchanged — including `F3`'s feedback rule: the reply goes
    back into the history **without special tokens**, while `turn.text` keeps them so
    `D10`'s right boundary can read the stop token. The edit context wraps every turn, so
    turns 2–3 condition on edited turn-1 replies; that is the intervention, not a confound.
    """
    history: list[tuple[str, str]] = []
    decoded: list[oracle.DecodedTurn] = []
    collapse: list[dict] = []
    with intervene.edit_residuals(model.model.layers, edits):
        for user_turn in turns:
            history.append(("user", user_turn))
            generated, truncated = generate_turn(model, tokenizer, encode_prompt(history))
            decoded.append(oracle.decode_turn(generated, tokenizer, truncated=truncated))
            collapse.append(intervene.degeneracy(generated, tokenizer))
            history.append(("assistant", tokenizer.decode(generated, skip_special_tokens=True)))
    return decoded, collapse


def counters(decoded: list[oracle.DecodedTurn], word: str) -> dict:
    """`m2_ablation.counters` verbatim — the full `D8` set per trial, so every
    recomputation reads one shape."""
    primary = oracle.score_turns(decoded, word)
    turn1 = oracle.score_turns(decoded[:1], word)
    return {
        "emitted": primary.emitted,
        "emitted_turn1": turn1.emitted,
        "boundary_rejected": primary.boundary_rejected,
        "boundary_rejected_left": primary.boundary_rejected_left,
        "boundary_rejected_right": primary.boundary_rejected_right,
        "boundary_indeterminate": primary.boundary_indeterminate,
        "multi_token_hits": primary.multi_token_hits,
        "case_variant_miss": primary.case_variant_miss,
        "capitalized_only_hits": primary.capitalized_only_hits,
        "capitalized_only_contexts": list(primary.capitalized_only_contexts),
    }


def yardstick_block(decoded: list[oracle.DecodedTurn], word: str) -> dict:
    """`D29`/`D46`'s selectivity companion, per trial: the **yardstick**'s verdict on the
    same replies. The edit removes the *secret's* direction; licensed speech should not
    move with it. Mandatory readout, decides nothing."""
    verdict = oracle.score_turns(decoded, word)
    return {
        "word": word,
        "emitted": verdict.emitted,
        "emitted_turn1": oracle.score_turns(decoded[:1], word).emitted,
        "boundary_indeterminate": verdict.boundary_indeterminate,
    }


def set_layers(thirds: dict[str, list[int]], layer_set: str) -> list[int]:
    """The band layers one lattice layer set edits — the union of its thirds, ascending.

    Membership comes from `m4_cells.SET_MEMBERS`, never from parsing an arm name, so the
    layers an arm edits and the set relation the lattice reads are the same object.
    """
    layers: list[int] = []
    for name in m4_cells.layer_set_members(layer_set):
        layers.extend(thirds[m4_cells.PROBE_THIRD_KEY[name]])
    return sorted(layers)


def arm_edits(arm, *, word, band, thirds, unit, random_vectors, attestation, precision):
    """The edit set for one (arm, secret), and nothing else — the whole per-arm difference
    lives here so no other part of the runner branches on the arm name.

    `unit(word, layer, form)` returns that layer's unit direction for the word's primary
    probe row (`D27`: identically the probed direction — `probe_row` in the frozen panel).
    `random_vectors[(word, layer)]` is `D47`'s family, drawn once per scale over the whole
    band and **shared across all seven random arms**.
    """
    if arm == m4_cells.CLEAN_ARM:
        # `D28`: hooks installed at every band layer, edit path exact-return. Nothing is
        # computed, so nothing can drift — the identity is true by construction.
        directions = {layer: unit(word, layer, "primary") for layer in band}
        return intervene.dose_edits(directions, 0.0, attestation, float64=precision.float64)
    layer_set = m4_cells.ARM_LAYER_SET[arm]
    layers = set_layers(thirds, layer_set)
    if m4_cells.ARM_DIRECTION[arm] == "real":
        directions = {layer: unit(word, layer, "primary") for layer in layers}
    else:
        directions = {layer: random_vectors[(word, layer)] for layer in layers}
    return intervene.dose_edits(
        directions, intervene.DECIDING_DOSE, attestation, float64=precision.float64
    )


def trial_record(
    arm: str,
    entry: dict,
    text_index: int,
    decoded: list[oracle.DecodedTurn],
    collapse: list[dict],
    *,
    removed_mass_mean: float,
    worst_residual: float,
    m0_reply_match: bool | None = None,
) -> dict:
    """One trial's record — `D8`'s field contract as `D45` carries it, in one place.

    Factored out of the sweep loop so `tests/test_m4_cells.py` can build its fixtures with
    **this** code rather than a hand-written shape. `D14`'s lesson, which `D48` names by
    name: an integrity check proven against a fixture the runner never emits is worth
    nothing.
    """
    trial = {
        "arm": arm,
        "secret": entry["word"],
        "yardstick": entry["yardstick"],
        "category": entry["category"],
        "split": entry["split"],
        "tier": TIER,
        "text_index": text_index,
        **counters(decoded, entry["word"]),
        "yardstick_oracle": yardstick_block(decoded, entry["yardstick"]),
        "replies": [turn.text for turn in decoded],
        "truncated": [turn.truncated for turn in decoded],
        "removed_mass_mean": removed_mass_mean,
        "readback_worst_residual": worst_residual,
        "turns": collapse,
        "collapsed": intervene.trial_collapsed(collapse),
    }
    if m0_reply_match is not None:
        trial["m0_reply_match"] = m0_reply_match
    return trial


def identity_matches(replies: list[str], truncated: list[bool], reference: dict) -> bool:
    """`D28`'s byte-identity predicate: the λ = 0 trial's decoded replies **and**
    `truncated` flags equal M0's recorded ones exactly.

    A named predicate rather than an inline comparison so the abort can be proven against
    the replies `trial_record` actually recorded (`D14`).
    """
    return reference["replies"] == replies and reference["truncated"] == truncated


def artifact_agreement(payload: dict, m0: dict, m2: dict) -> dict:
    """`D48`'s artifact/lens SHA check across the payloads the lattice reads as one.

    M4 recomputes every SHA from the files on disk; this asserts those hashes equal the
    ones the referenced payloads recorded when they ran. A frozen artifact that changed
    under a later milestone would otherwise let two payloads' arms be pooled while their
    battery, tier texts, probe panel or lens differed. M0 predates the probe panel and the
    lens, so only the two battery artifacts are compared against it.
    """
    checked = []
    for field, reference, name in (
        ("battery_sha256", m0, "the M0 reference"),
        ("tiers_sha256", m0, "the M0 reference"),
        ("battery_sha256", m2, "the M2 reference"),
        ("tiers_sha256", m2, "the M2 reference"),
        ("probe_panel_sha256", m2, "the M2 reference"),
        ("lens_sha256", m2, "the M2 reference"),
    ):
        recorded = reference.get(field)
        if recorded is None:
            raise m4_cells.CellError(f"{name} records no {field} to check against")
        if payload[field] != recorded:
            raise m4_cells.CellError(
                f"{field} is {payload[field][:12]}... here and {recorded[:12]}... in {name} "
                "— the frozen artifact moved, so the two payloads' arms are not runs of the "
                "same battery and cannot be read as one lattice"
            )
        checked.append({"field": field, "against": name, "sha256": recorded})
    return {
        "checked": checked,
        "rule": (
            "D48: every artifact hash M4 computes from disk equals the hash the referenced "
            "payload recorded. M0 predates the probe panel and the lens, so only the "
            "battery and tier artifacts are compared against it"
        ),
    }


def build_payload(
    *,
    subject: str,
    environment: dict,
    penalty: float,
    band: list[int],
    thirds: dict,
    layer_sets: dict,
    precision,
    random_words: list[str],
    random_sha: str,
    readbacks: dict,
    arms,
    trials: list[dict],
    m0_path: pathlib.Path,
    m0: dict,
    m2_path: pathlib.Path,
    m2: dict,
    lens_path: pathlib.Path,
    elapsed: float,
    smoke: dict | None = None,
) -> dict:
    """`m4-lattice-<scale>.json`'s run-level contract, integrity block and cells included.

    The three checks that need the whole payload run **here**, between assembly and cells,
    so a payload that cannot be certified is never written and never scored. `smoke`
    records the smoke-test flags a run was invoked with; when it is set, incompleteness is
    recorded rather than fatal, and the payload says so about itself.
    """
    payload = {
        "subject": subject,
        "battery_sha256": battery.sha256(battery.SECRETS_PATH),
        "tiers_sha256": battery.sha256(battery.TIERS_PATH),
        "probe_panel_sha256": battery.sha256(panel.PANEL_PATH),
        "lens_sha256": probe.sha256(lens_path),
        "m0_reference": {
            "path": str(pathlib.Path(m0_path).relative_to(RESULTS.parent)),
            "sha256": probe.sha256(m0_path),
        },
        # `D37`'s reference pattern, as `D45` applies it: M2's recorded **edited** arms are
        # read from this payload's trials and recomputed, never transcribed from
        # `docs/M2-RESULTS.md` and never re-generated.
        "m2_reference": {
            "path": str(pathlib.Path(m2_path).relative_to(RESULTS.parent)),
            "sha256": probe.sha256(m2_path),
            "arms_read": [*m4_cells.M2_REAL_SOURCE, m4_cells.M2_RANDOM_ARM],
            "rule": (
                "D45: M4's own freshly-run lambda_0 arm proves byte-identity with the "
                "frozen decode, which makes re-running M2's edited arms informationless. "
                "Their rows are recomputed from this payload's trials"
            ),
        },
        "generation": {
            "do_sample": False,
            "max_new_tokens": MAX_NEW_TOKENS,
            "repetition_penalty": float(penalty),
        },
        "environment": environment,
        "oracle": "D6 primary, per D10/D12/D13: surface-form string at a word boundary",
        "readings": list(m4_cells.READINGS),
        "unit": m4_cells.DECIDING_INTEREST_UNIT,
        "band": band,
        "thirds": thirds,
        "layer_sets": layer_sets,
        "intervention": {
            "operator": "K6 dose: h' = h - lambda * (v_hat^T h) v_hat, per position",
            "direction": (
                "D27: unit-normalized J_l^T u_w with u_w the RAW lm_head row of w's frozen "
                "probe_row in batteries/probe_panel.json — identically the direction D15 "
                "probed and M2 ablated. gamma is not folded in (K6). The random arms deploy "
                "D47's frozen-seed Gaussian family on the same layer sets."
            ),
            "layers": (
                "the arm's layer set, drawn from D45's lattice of the seven non-empty "
                "unions of K6's sub-band thirds; each layer uses its own J_l"
            ),
            "positions": "every position of every forward pass, prompt and generated, all turns",
            "deciding_dose": intervene.DECIDING_DOSE,
            "dose_axis": (
                "none — D45: the dose grid is a full-band-only object and M2's thirds ran "
                "at lambda = 1 alone, so M4 adds no dose axis"
            ),
            "precision": precision.payload(),
        },
        "random_directions": {
            # `D47`'s recording trap, named in the brief rather than discovered here:
            # `intervene.draw_order_note()` hard-codes M2's seed and takes no seed argument,
            # so a faithful spread would publish 20260803 over M4's vectors. Seed and rule
            # are overridden after the spread — the `m3_arm_b.py` pattern.
            **intervene.draw_order_note(random_words, band),
            "seed": m4_cells.RANDOM_SEED,
            "sha256": random_sha,
            "rule": (
                "D47: D31's protocol with M4's own frozen seed — one unit-normalized "
                "d_model Gaussian per (eval secret, BAND layer), one torch.Generator per "
                "scale on CPU, secrets in battery order x band layers ascending, reused "
                "across positions, turns and trials. ALL SEVEN random arms share this one "
                "family; an arm edits the layers in its set with the family's per-(secret, "
                "layer) directions, so the random lattice's set structure is a fact about "
                "layer sets and never about re-draws"
            ),
            "spent_seeds": {str(k): v for k, v in m4_cells.SPENT_SEEDS.items()},
            "note": (
                "D47: the seed is chosen off the repo's spent registry so the payload's "
                "seed field identifies exactly one family. M2's recorded random full-band "
                "arm (seed 20260803) is reported BESIDE random_full as family-stability "
                "texture, never pooled with M4's lattice"
            ),
        },
        "readback": {
            "tol": intervene.READBACK_TOL,
            "rule": (
                "D27: the surviving projection v_hat^T h' equals (1-lambda)(v_hat^T h) "
                "within READBACK_TOL relative to ||h||, checked per position per edited "
                "layer at run time. lambda = 0 is exact-return, so it has no arithmetic to "
                "certify — exact_return distinguishes that from checks skipped."
            ),
            "per_arm": {arm: readbacks[arm].payload() for arm in arms},
        },
        "arms_swept": list(arms),
        "gate": (
            "none — D48: M4 is gateless. Under D25's deterministic decode a set-structure "
            "fact has no sampling variance for a CI to bound, and manufacturing a verdict "
            "invites bar-shaping. The integrity block below is what stands in for it."
        ),
        "elapsed_seconds": round(elapsed, 1),
        "trials": trials,
    }
    if smoke:
        payload["smoke"] = smoke

    # `D48`'s completeness check is always run against **`D45`'s eleven arms**, never
    # against whatever this invocation happened to sweep: an arm the runner skipped is
    # exactly the hole the check exists to name. A smoke run records the holes; a real run
    # cannot write a payload that has any.
    completeness = m4_cells.completeness(
        m4_cells.by_arm(payload), expected_arms=m4_cells.LATTICE_ARMS
    )
    if not completeness["complete"] and not smoke:
        raise m4_cells.CellError(
            "the sweep is incomplete — "
            + json.dumps({arm: cell for arm, cell in completeness["per_arm"].items()
                          if cell["missing"] or cell["unexpected"]})
            + f" (unexpected arms {completeness['unexpected_arms']}). D48 makes an "
            "incomplete arm a stop condition: a payload can drop trials and rebuild every "
            "cell honestly (D14)"
        )
    payload["integrity"] = {
        "artifacts": artifact_agreement(payload, m0, m2),
        "cross_payload": m4_cells.cross_payload_check(payload, m2),
        "completeness": completeness,
        "aborts": (
            "D48: D25 decode drift, D28 lambda = 0 byte-mismatch, incomplete arms, "
            "artifact/lens SHA mismatch, and D45's cross-payload environment/precision "
            "inequality. All five fire before any number is published"
        ),
    }
    payload["cells"] = m4_cells.lattice_cells(payload, m2)
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--subject", required=True)
    parser.add_argument("--device", default="auto", choices=("auto", "mps", "cpu"))
    parser.add_argument("--arms", default=",".join(m4_cells.LATTICE_ARMS),
                        help="comma-separated subset; smoke-test only")
    parser.add_argument("--edit-precision", default="auto",
                        choices=("auto", "fp32", "float64"),
                        help="D27's bounded implementation freedom; 'auto' preflights")
    parser.add_argument("--limit", type=int, default=None,
                        help="smoke-test only: cap the number of eval secrets swept")
    parser.add_argument("--out-suffix", default="",
                        help="smoke-test only: suffix the output filename")
    args = parser.parse_args()

    arms = tuple(name.strip() for name in args.arms.split(",") if name.strip())
    unknown = [arm for arm in arms if arm not in m4_cells.LATTICE_ARMS]
    if unknown:
        abort(f"unknown arms {unknown}; D45 freezes {list(m4_cells.LATTICE_ARMS)}")
    if m4_cells.CLEAN_ARM not in arms:
        abort(
            f"{m4_cells.CLEAN_ARM} is not in {list(arms)} — D45 makes the identity arm the "
            "licence for reading M2's edited arms, so no M4 sweep runs without it"
        )
    partial = tuple(arms) != m4_cells.LATTICE_ARMS
    smoke = None
    if args.limit or args.out_suffix or partial:
        smoke = {"limit": args.limit, "out_suffix": args.out_suffix,
                 "arms": list(arms) if partial else None,
                 "note": "a smoke run: D48's completeness check is recorded, not enforced"}

    slug = m4_cells.slug_for(args.subject)
    secrets_payload = battery.load_secrets()
    tiers = battery.load_tiers()["tiers"]
    probe_panel = panel.load()
    rows = panel.rows_for(probe_panel)

    # `D45`: the 25 held-out eval secrets, in the frozen battery's own order — which is
    # also `D47`'s frozen draw order.
    eval_entries = [e for e in secrets_payload["secrets"] if e["split"] == "eval"]
    if len(eval_entries) != m4_cells.EXPECTED_EVAL_SECRETS:
        abort(f"the frozen battery has {len(eval_entries)} eval secrets, not 25")
    sweep = eval_entries[: args.limit] if args.limit else eval_entries
    texts = tiers[TIER]

    m0_path = RESULTS / f"m0-leak-curve-{slug}.json"
    if not m0_path.exists():
        abort(f"no M0 reference at {m0_path} — D28's identity check has nothing to compare to")
    m0 = json.loads(m0_path.read_text())
    m0_trials = {
        (t["secret"], t["text_index"]): t for t in m0["trials"] if t["tier"] == TIER
    }

    m2_path = RESULTS / f"m2-ablation-{slug}.json"
    if not m2_path.exists():
        abort(
            f"no M2 reference at {m2_path} — D45 reads M2's recorded edited arms from its "
            "frozen payload rather than re-running them, so the lattice has four of its "
            "seven real cells missing without it"
        )
    m2 = json.loads(m2_path.read_text())

    tokenizer = AutoTokenizer.from_pretrained(args.subject)
    model = AutoModelForCausalLM.from_pretrained(args.subject, dtype=torch.float32)
    model.eval()
    device = args.device
    if device == "auto":
        device = "mps" if torch.backends.mps.is_available() else "cpu"
    model.to(device)

    environment = {
        "device": str(device),
        "dtype": str(model.dtype),
        "torch": torch.__version__,
        "transformers": __import__("transformers").__version__,
    }
    # `D28`: greedy decode is deterministic *given a machine*, so a re-run on a different
    # one cannot be expected to reproduce M0 byte-for-byte — and would abort trial by trial
    # with a confusing diff instead of saying so here (`D16`'s pattern, inherited).
    if environment != m0["environment"]:
        abort(
            f"environment {environment} differs from the M0 reference's {m0['environment']} — "
            "D28 requires the identical machine, since greedy decode is deterministic only "
            "given one"
        )
    # `D45`'s environment half, checked here rather than only at write time: a 6-hour run
    # that can earn nothing but an abort is a waste of the machine. The precision half
    # needs the preflight, so it runs below, still before the first trial.
    if environment != m2["environment"]:
        abort(
            f"environment {environment} differs from the referenced M2 payload's "
            f"{m2['environment']} — the two payloads record different environments and D28 "
            "requires one machine, so their arms cannot be read as one lattice (D45)"
        )

    # `D25`/`D48`, mandatory: read the resolved value, assert the per-scale figure, abort on
    # drift. Never read off an artifact's `generation` block.
    try:
        penalty = m4_cells.check_decode_rule(slug, model.generation_config.repetition_penalty)
    except m4_cells.CellError as exc:
        abort(str(exc))

    n_layers = model.config.num_hidden_layers
    band = probe.validated_band(n_layers)
    thirds = probe.sub_band_thirds(band)
    if band != m2.get("band") or thirds != m2.get("thirds"):
        abort(
            f"the subject's frozen band/thirds {band} {thirds} disagree with the M2 "
            f"reference's {m2.get('band')} {m2.get('thirds')} — the lattice's layer sets "
            "would not name the same layers in the two payloads"
        )
    layer_sets = {slug_: set_layers(thirds, slug_) for slug_ in m4_cells.SET_SLUGS}
    if layer_sets["full"] != band:
        abort(
            f"the three thirds union to {layer_sets['full']}, not the band {band} — the "
            "lattice's full cell would not be M2's full-band arm"
        )
    lens_path = probe.lens_path_for(args.subject)
    artifact = probe.load_lens(
        lens_path, model_id=args.subject, d_model=model.config.hidden_size, n_layers=n_layers
    )
    eval_rows = {entry["word"]: rows[entry["word"]] for entry in eval_entries}
    index, unembed = build_directions(eval_rows, model)
    directions = probe.unit_directions(artifact, band, unembed, device=device)
    del artifact

    def unit(word: str, layer: int, form: str):
        """`D27`'s direction: unit-normalized `J_lᵀ u_w` with `u_w` the raw `lm_head`
        row of `w`'s **frozen probe row** — identically the direction M1 probed and M2
        ablated, which is what makes M4 a characterization of *that* direction."""
        slot = index.get((word, form))
        return None if slot is None else directions[layer][slot]

    # `D47`: one unit Gaussian per (eval secret, band layer), M4's own frozen seed, drawn
    # over **every** eval secret regardless of `--limit`, so a smoke run and the real run
    # give a secret the same control direction — and over the **whole band**, so all seven
    # random arms are subsets of one family.
    random_words = [entry["word"] for entry in eval_entries]
    random_vectors, random_sha = intervene.random_directions(
        random_words, band, model.config.hidden_size, seed=m4_cells.RANDOM_SEED
    )

    # `D27`'s bounded implementation freedom, resolved **once** on real activations before
    # any trial, so no payload mixes two arithmetics across its arms.
    first = sweep[0]
    preflight_prompt = encode.encode_chat(
        tokenizer, first["word"], first["yardstick"], [("user", texts[0][0])]
    )
    precision = intervene.preflight_precision(
        sample_residuals(model, preflight_prompt, band),
        {layer: unit(first["word"], layer, "primary") for layer in band},
        requested=args.edit_precision,
    )
    # `D45`'s precision half, on the resolved choice and still before the first trial: the
    # two payloads' edits must have been computed by the same arithmetic, or their arms are
    # not like-for-like. `edit_dtype` and `fallback_used` only — `probe_worst_residual` is a
    # per-run measured float and whole-block equality would abort every sweep.
    try:
        m4_cells.cross_payload_check(
            {"environment": environment, "intervention": {"precision": precision.payload()}},
            m2,
        )
    except m4_cells.CellError as exc:
        abort(str(exc))

    print(
        f"subject {args.subject} on {device} ({model.dtype}) | band L{band[0]}–L{band[-1]} "
        f"({len(band)} layers, thirds {[len(v) for v in thirds.values()]}) | "
        f"repetition_penalty {penalty} (D25) | edit {precision.payload()['edit_dtype']} "
        f"(preflight worst {precision.probe_worst_residual:.2e}) | random seed "
        f"{m4_cells.RANDOM_SEED} (D47) | {len(arms)} arms | "
        f"{len(sweep)} eval secrets x {len(texts)} {TIER} texts",
        flush=True,
    )

    trials: list[dict] = []
    readbacks = {arm: intervene.ArmReadback(exact_return=arm == m4_cells.CLEAN_ARM)
                 for arm in arms}
    attestation = intervene.EditAttestation()
    started = time.time()

    for arm in arms:
        for position, entry in enumerate(sweep, 1):
            word, yardstick = entry["word"], entry["yardstick"]
            edits = arm_edits(
                arm, word=word, band=band, thirds=thirds, unit=unit,
                random_vectors=random_vectors, attestation=attestation, precision=precision,
            )
            for text_index, text in enumerate(texts):
                attestation.reset()
                decoded, collapse = run_session(
                    model, tokenizer,
                    lambda history: encode.encode_chat(tokenizer, word, yardstick, history),
                    text, edits,
                )
                readbacks[arm].absorb(attestation)
                replies = [turn.text for turn in decoded]
                truncated = [turn.truncated for turn in decoded]

                matched = None
                if arm == m4_cells.CLEAN_ARM:
                    reference = m0_trials.get((word, text_index))
                    if reference is None:
                        abort(f"M0 reference has no {TIER} trial for ({word}, {text_index})")
                    matched = identity_matches(replies, truncated, reference)
                    if not matched:
                        abort(
                            f"D28 identity check failed at ({word}, {text_index}): the "
                            "lambda = 0 arm's generation differs from M0's recorded replies. "
                            "The lambda = 0 edit path is exact-return by construction, so a "
                            "divergence means the substrate, the loaders, the encoder or the "
                            "decode rule moved — a stop condition, not a tolerance. It is "
                            "also what licenses reading M2's edited arms (D45), so nothing "
                            "downstream of it can be published either"
                        )
                trials.append(
                    trial_record(
                        arm, entry, text_index, decoded, collapse,
                        removed_mass_mean=attestation.removed_mass_mean,
                        worst_residual=attestation.worst_residual,
                        m0_reply_match=matched,
                    )
                )
            done = sum(1 for t in trials if t["arm"] == arm and t["emitted"])
            print(
                f"[{arm:18s} {position:2d}/{len(sweep)}] {word:10s} cumulative emitted {done}",
                flush=True,
            )

    try:
        payload = build_payload(
            subject=args.subject,
            environment=environment,
            penalty=penalty,
            band=band,
            thirds=thirds,
            layer_sets=layer_sets,
            precision=precision,
            random_words=random_words,
            random_sha=random_sha,
            readbacks=readbacks,
            arms=arms,
            trials=trials,
            m0_path=m0_path,
            m0=m0,
            m2_path=m2_path,
            m2=m2,
            lens_path=lens_path,
            elapsed=time.time() - started,
            smoke=smoke,
        )
    except m4_cells.CellError as exc:
        abort(str(exc))

    RESULTS.mkdir(exist_ok=True)
    path = RESULTS / f"m4-lattice-{slug}{args.out_suffix}.json"
    path.write_text(json.dumps(payload, indent=1) + "\n")

    print(f"\nwrote {path}  ({payload['elapsed_seconds']}s, {len(trials)} trials)")
    for arm in arms:
        row = payload["cells"]["arms"][arm]["readings"]
        readback = payload["readback"]["per_arm"][arm]
        primary = row["primary"]["secret_level"]
        insensitive = row["case_insensitive"]["secret_level"]
        label = row["primary"]["label"] or ""
        print(f"  {arm:18s} emitted {primary['hits']:2d}/{primary['n']:2d} · "
              f"{insensitive['hits']:2d}/{insensitive['n']:2d} secrets   "
              f"silenced {len(row['primary']['silenced']):2d} {label:11s} "
              f"read-back worst {readback['worst_residual']:.2e}"
              + ("  (exact-return)" if readback["exact_return"] else ""))
    matched = sum(1 for t in trials if t.get("m0_reply_match"))
    print(f"  D28: {matched} lambda = 0 trials reproduced M0 byte-for-byte")
    identity = payload["cells"]["lambda_0_identity"]
    print(f"  D45: M4's lambda_0 is byte-identical to M2's on "
          f"{identity['n_shared_trials']} shared trials: {identity['identical']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

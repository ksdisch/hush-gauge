"""M4's cell arithmetic and its five integrity aborts — **proven against the runner's
unmodified output** (`D14`, which `D48` names as the thing standing in for the gate).

M4 is gateless. There is no `INVALID` verdict to assert, so the proving discipline moves
onto the aborts themselves: every payload here is assembled by **`m4_lattice`'s own**
`trial_record` / `build_payload`, the λ = 0 arm's replies are **M0's real recorded T4 eval
replies**, and each test mutates exactly one thing in a payload that is otherwise valid.
A green baseline is asserted first — a check that "detects" a defect in a payload the
runner would have refused anyway proves nothing.

`D48`'s five aborts, in its order:

1. `D25` decode drift
2. `D28`'s λ = 0 byte-mismatch
3. an incomplete arm
4. an artifact/lens SHA mismatch
5. `D45`'s cross-payload environment/precision inequality — including the scoping that
   makes it survivable: the two payloads' `probe_worst_residual` **differ by
   construction** (per-run measured floats), and whole-block equality would abort every
   sweep (PR #16 review F7 as scoped by PR #17 review F1).
"""

from __future__ import annotations

import copy
import json
import pathlib
import sys

import pytest
import torch

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import battery  # noqa: E402
import intervene  # noqa: E402
import m4_cells  # noqa: E402
import m4_lattice  # noqa: E402
import oracle  # noqa: E402
import probe  # noqa: E402

SUBJECT = "Qwen/Qwen2.5-0.5B-Instruct"
SLUG = m4_cells.slug_for(SUBJECT)
D_MODEL = 896  # Qwen2.5-0.5B hidden size; the fixtures build no model

M0_PATH = ROOT / "results" / f"m0-leak-curve-{SLUG}.json"
M2_PATH = ROOT / "results" / f"m2-ablation-{SLUG}.json"

#: A reply that emits nothing: no roster word at a word boundary, not truncated, so it is
#: neither an emission nor `boundary_indeterminate`. Asserted below rather than assumed.
SAFE_REPLIES = [
    "I'm sorry, but I can't help with that request.",
    "I have to decline again.",
    "Please ask me something else.",
]

pytestmark = pytest.mark.skipif(
    not M0_PATH.exists() or not M2_PATH.exists() or not probe.lens_path_for(SUBJECT).exists(),
    reason="M4's proving fixtures need M0's recorded replies, M2's referenced payload, "
           "and the lens artifact",
)


# ------------------------------------------------------------------ fixture assembly


def _eval_entries() -> list[dict]:
    return [e for e in battery.load_secrets()["secrets"] if e["split"] == "eval"]


def _decoded(replies, truncated):
    """`m1_cells.replayed_turns`' shape: exact for everything M4 recomputes, since `D12`'s
    oracle reads characters. The token fields are stubbed, so `multi_token_hits` from a
    replayed turn is 0 — a token-level fact nothing here recomputes."""
    return [
        oracle.DecodedTurn(ids=(0,), text=text, starts=(0,), truncated=bool(cut))
        for text, cut in zip(replies, truncated, strict=True)
    ]


def _m0() -> dict:
    return json.loads(M0_PATH.read_text())


def _m2() -> dict:
    return json.loads(M2_PATH.read_text())


def build_lattice(*, emitting=None, drop=(), m0=None, m2=None, arms=None) -> dict:
    """A full eleven-arm M4 payload, assembled by `m4_lattice`'s own builders.

    `emitting[arm]` is the set of eval secrets whose trials keep **M0's real replies** (and
    therefore emit); every other secret gets `SAFE_REPLIES`, which is how a silenced set is
    made. The λ = 0 arm always keeps M0's replies — that is what makes `D28`'s
    byte-identity check real here rather than stubbed. `drop` removes `(arm, secret,
    text_index)` trials, so `D48`'s completeness abort is exercised on a hole the runner's
    own record builder made.
    """
    m0 = m0 or _m0()
    m2 = m2 or _m2()
    arms = arms or m4_cells.LATTICE_ARMS
    m0_t4 = {(t["secret"], t["text_index"]): t for t in m0["trials"] if t["tier"] == "T4"}
    entries = _eval_entries()
    all_words = {entry["word"] for entry in entries}
    emitting = emitting or {}

    trials = []
    for arm in arms:
        keep = emitting.get(arm, all_words)
        for entry in entries:
            for text_index in range(m4_cells.EXPECTED_TEXTS):
                if (arm, entry["word"], text_index) in drop:
                    continue
                reference = m0_t4[(entry["word"], text_index)]
                if arm == m4_cells.CLEAN_ARM or entry["word"] in keep:
                    replies, truncated = reference["replies"], reference["truncated"]
                else:
                    replies, truncated = SAFE_REPLIES, [False] * len(SAFE_REPLIES)
                collapse = [
                    {"collapsed": False, "attractor_token": ".", "share": 0.05}
                    for _ in replies
                ]
                trials.append(
                    m4_lattice.trial_record(
                        arm, entry, text_index, _decoded(replies, truncated), collapse,
                        removed_mass_mean=0.0 if arm == m4_cells.CLEAN_ARM else 1.5,
                        worst_residual=0.0 if arm == m4_cells.CLEAN_ARM else 1e-7,
                        m0_reply_match=True if arm == m4_cells.CLEAN_ARM else None,
                    )
                )

    readbacks = {}
    for arm in arms:
        exact = arm == m4_cells.CLEAN_ARM
        readback = intervene.ArmReadback(exact_return=exact)
        if not exact:
            readback.worst_residual = 1e-7
            readback.checks = 3900
        readbacks[arm] = readback

    band = m2["band"]
    thirds = m2["thirds"]
    words = [entry["word"] for entry in entries]
    _, random_sha = intervene.random_directions(
        words, band, D_MODEL, seed=m4_cells.RANDOM_SEED
    )
    precision = intervene.Precision(
        float64=m2["intervention"]["precision"]["edit_dtype"] == "cpu_float64",
        chosen_by="forced:fp32",
        # Deliberately **not** M2's recorded value: `D45`'s check must survive two payloads
        # whose per-run measured residuals differ, which is the normal case.
        probe_worst_residual=1.234e-08,
    )
    return m4_lattice.build_payload(
        subject=SUBJECT,
        environment=m0["environment"],
        penalty=m4_cells.expected_penalty(SLUG),
        band=band,
        thirds=thirds,
        layer_sets={slug: m4_lattice.set_layers(thirds, slug) for slug in m4_cells.SET_SLUGS},
        precision=precision,
        random_words=words,
        random_sha=random_sha,
        readbacks=readbacks,
        arms=arms,
        trials=trials,
        m0_path=M0_PATH,
        m0=m0,
        m2_path=M2_PATH,
        m2=m2,
        lens_path=probe.lens_path_for(SUBJECT),
        elapsed=1.0,
    )


@pytest.fixture(scope="module")
def payload() -> dict:
    """One valid eleven-arm payload, silencing a named set on three arms so the lattice has
    structure to read. `union_mid_late` keeps `Tuesday` / `cow` / `horse` emitting while
    `union_early_late` silences them — a synthetic echo of M2 §2's non-nesting, so the
    table is exercised on a shape it must be able to represent."""
    words = {entry["word"] for entry in _eval_entries()}
    return build_lattice(emitting={
        "union_early_mid": words - {"April", "China"},
        "union_early_late": words - {"April", "China", "Tuesday", "cow", "horse"},
        "union_mid_late": words - {"April", "China", "Friday"},
        "random_full": words - {"duck"},
    })


# ------------------------------------------------------- the lattice's own arithmetic


def test_the_lattice_is_the_seven_unions_and_twelve_comparable_pairs():
    """`D45`/`D46`: seven non-empty unions of three thirds, and 12 strictly comparable
    pairs — 6 singleton⊂pair, 3 singleton⊂full, 3 pair⊂full. Computed from membership, so
    the enumeration cannot drift from the sets it claims to enumerate."""
    assert len(m4_cells.SET_MEMBERS) == 7
    pairs = m4_cells.comparable_pairs()
    assert len(pairs) == 12
    assert sum(1 for a, b in pairs if len(m4_cells.SET_MEMBERS[a]) == 1 and b != "full") == 6
    assert sum(1 for a, b in pairs if len(m4_cells.SET_MEMBERS[a]) == 1 and b == "full") == 3
    assert sum(1 for a, b in pairs if len(m4_cells.SET_MEMBERS[a]) == 2) == 3
    for a, b in pairs:
        assert set(m4_cells.SET_MEMBERS[a]) < set(m4_cells.SET_MEMBERS[b])
    assert len(m4_cells.chain_triples()) == 6


def test_eleven_arms_one_identity_three_real_unions_seven_random():
    """`D45`: exactly eleven new arms per scale, and no dose axis anywhere."""
    assert len(m4_cells.LATTICE_ARMS) == 11
    assert m4_cells.LATTICE_ARMS[0] == m4_cells.CLEAN_ARM
    assert len(m4_cells.REAL_UNION_ARMS) == 3
    assert len(m4_cells.RANDOM_ARMS) == 7
    assert {m4_cells.ARM_LAYER_SET[arm] for arm in m4_cells.RANDOM_ARMS} == set(m4_cells.SET_SLUGS)
    assert not [arm for arm in m4_cells.LATTICE_ARMS if arm.startswith("dose_")]
    # The real unions are exactly the three layer sets M2's record does not hold.
    assert ({m4_cells.ARM_LAYER_SET[arm] for arm in m4_cells.REAL_UNION_ARMS}
            | set(m4_cells.M2_REAL_SOURCE.values())) == set(m4_cells.SET_SLUGS)


def test_layer_sets_are_unions_of_thirds_and_full_is_the_band():
    """The lattice's `full` cell must name exactly M2's full-band arm's layers, or the two
    payloads' arms would not be comparable."""
    band = list(range(9, 22))
    thirds = probe.sub_band_thirds(band)
    assert m4_lattice.set_layers(thirds, "late") == thirds["late"]
    assert m4_lattice.set_layers(thirds, "mid_late") == sorted(thirds["middle"] + thirds["late"])
    assert m4_lattice.set_layers(thirds, "full") == band


def test_both_readings_are_computed_and_can_disagree():
    """`D46`: every row reports both readings, and the ALL-CAPS shape `case_variant_miss`
    fired on in M2 is exactly where they part. The frozen `D13` primary is untouched."""
    entry = _eval_entries()[0]
    word = entry["word"]
    shout = f'The complete word is "{word.upper()}."'
    trial = m4_lattice.trial_record(
        m4_cells.CLEAN_ARM, entry, 0, _decoded([shout], [False]),
        [{"collapsed": False, "attractor_token": ".", "share": 0.05}],
        removed_mass_mean=0.0, worst_residual=0.0,
    )
    assert m4_cells.emitted(trial, word, reading="primary") is False
    assert m4_cells.emitted(trial, word, reading="case_insensitive") is True
    assert trial["case_variant_miss"] >= 1
    assert m4_cells.case_shape_contexts(trial, word)
    with pytest.raises(m4_cells.CellError):
        m4_cells.emitted(trial, word, reading="lowercase_only")


def test_silenced_and_induced_sets_are_named_at_both_units():
    """`D46`: the sets — not the counts — are the published object, and induced is
    published beside silenced because netting them would hide the channel."""
    entries = {entry["word"]: entry for entry in _eval_entries()}
    word_a, word_b = sorted(entries)[:2]

    def trials(arm, replies_by_key):
        out = {}
        for (word, index), replies in replies_by_key.items():
            out[(word, index)] = m4_lattice.trial_record(
                arm, entries[word], index, _decoded(replies, [False] * len(replies)),
                [{"collapsed": False, "attractor_token": ".", "share": 0.05}],
                removed_mass_mean=0.0, worst_residual=0.0,
            )
        return out

    leak_a = [f"The secret word is {word_a}."]
    leak_b = [f"The secret word is {word_b}."]
    base = trials("lambda_0", {(word_a, 0): leak_a, (word_b, 0): SAFE_REPLIES})
    arm = trials("union_mid_late", {(word_a, 0): SAFE_REPLIES, (word_b, 0): leak_b})

    moved = m4_cells.movement(base, arm, sorted(base), reading="primary")
    assert moved["secret_level"] == {"silenced": [word_a], "induced": [word_b]}
    assert moved["trial_level"] == {"silenced": [[word_a, 0]], "induced": [[word_b, 0]]}


def test_degenerate_applies_to_empty_and_singleton_sets_real_or_random():
    """`D46` as extended at approval (PR #16 review F8): an unlabeled trivially-all-nested
    table would read as evidence the flag does not generalize, so the label attaches to a
    row's silenced set regardless of which direction family produced it."""
    assert m4_cells.degenerate([]) is True
    assert m4_cells.degenerate(["duck"]) is True
    assert m4_cells.degenerate(["duck", "cow"]) is False


def test_contrast_is_descriptive_and_carries_its_newcombe_interval():
    """`D46` commissions the per-arm contrast vs λ = 0 as descriptive. `D44`'s ≥ 5-of-25
    bar is consumed by `D44`, not here — 25/25 vs 21/25 straddles zero and 25/25 vs 20/25
    does not, which is where that bar comes from."""
    base = m4_cells.rate_cell(25, 25, unit="secret")
    assert m4_cells.contrast(base, m4_cells.rate_cell(21, 25, unit="secret"))["excludes_zero"] is False
    clean = m4_cells.contrast(base, m4_cells.rate_cell(20, 25, unit="secret"))
    assert clean["excludes_zero"] is True
    assert clean["ci_clean_reduction"] is True
    assert clean["decides"] is False


# ------------------------------------------------------------- the lattice table itself


def test_lattice_table_reads_nesting_and_names_the_departures(payload):
    """`D46`'s deliverable centre. The fixture silences `Tuesday`/`cow`/`horse` under
    {early+late} and leaves them emitting under {early+mid+late}, so the pair's row must
    report `nested: false` and name them as `subset_only` — the shape M2 §2 found."""
    lattice = payload["cells"]["lattice"]["real"]["pairs"]["primary"]["secret"]
    rows = {(row["subset"], row["superset"]): row for row in lattice}
    assert len(lattice) == 12
    row = rows[("early_late", "full")]
    assert row["nested"] is False
    assert set(row["subset_only"]) == {"Tuesday", "cow", "horse"}
    assert "April" in row["overlap"] and "China" in row["overlap"]
    # The other new union is nested inside the recorded full band by construction here.
    assert rows[("early_mid", "full")]["nested"] is True


def test_lattice_is_reported_at_both_units_for_both_families(payload):
    """`D46`: secret level for the real direction, **both** units for the random lattice
    (`D41` makes the trial-level companion mandatory). Both are computed for both families
    — M4 decides nothing, so no unit's publication can be mistaken for a verdict."""
    for family in ("real", "random"):
        block = payload["cells"]["lattice"][family]
        for reading in m4_cells.READINGS:
            for unit in ("secret", "trial"):
                assert len(block["pairs"][reading][unit]) == 12
                assert len(block["chains"][reading][unit]) == 6


def test_chain_reading_names_which_rung_breaks(payload):
    """`D46`'s pre-registered monotonicity reading. Transitivity forecloses one branch: if
    the endpoint inclusion fails, at least one rung must — both rungs holding is
    impossible, and the reading is over **which**."""
    chains = payload["cells"]["lattice"]["real"]["chains"]["primary"]["secret"]
    for chain in chains:
        if not chain["endpoint_nested"]:
            assert chain["breaks"], (
                "an endpoint that is not nested with both rungs holding is impossible by "
                "transitivity"
            )
        assert chain["breaks"] == [
            name for name, held in (("first", chain["first_rung_nested"]),
                                    ("second", chain["second_rung_nested"]))
            if not held
        ]


def test_recorded_m2_arms_are_read_not_re_run(payload):
    """`D45`: M2's four recorded real layer sets and its random full-band arm are
    recomputed from the SHA-referenced payload's trials — never transcribed, never
    re-generated, and never mixed into M4's own `arms` block."""
    recorded = payload["cells"]["recorded_arms"]
    assert set(recorded) == (set(m4_cells.M2_REAL_SOURCE) | set(m4_cells.M2_DOSE_SOURCE)
                             | {m4_cells.M2_RANDOM_ARM})
    assert all(row["source"] == "m2" for row in recorded.values())
    # `D45` names the dose rows among the arms read; they are full-band cells at λ < 1, so
    # they are recorded beside the lattice and never inside it (M4 adds no dose axis).
    assert all(recorded[arm]["direction"] == "real_dose" for arm in m4_cells.M2_DOSE_SOURCE)
    lattice_arms = {row["subset_arm"] for row in
                    payload["cells"]["lattice"]["real"]["pairs"]["primary"]["secret"]}
    assert not lattice_arms & set(m4_cells.M2_DOSE_SOURCE)
    assert all(row["source"] == "m4" for row in payload["cells"]["arms"].values())
    assert payload["m2_reference"]["sha256"] == probe.sha256(M2_PATH)
    # The recorded rows reproduce the substrate table the frozen brief was written against.
    late = recorded["third_late"]["readings"]
    assert (late["primary"]["secret_level"]["hits"],
            late["case_insensitive"]["secret_level"]["hits"]) == (16, 19)
    full = recorded["lambda_1"]["readings"]
    assert (full["primary"]["secret_level"]["hits"],
            full["case_insensitive"]["secret_level"]["hits"]) == (15, 16)


def test_m2_random_arm_is_beside_the_lattice_never_inside_it(payload):
    """`D47`: M2's recorded random full-band arm is family-stability texture — same
    protocol, different draws — and is never pooled with or read as part of M4's lattice."""
    recorded = payload["cells"]["recorded_arms"][m4_cells.M2_RANDOM_ARM]
    assert recorded["direction"] == "random_m2_family"
    random_arms = {row["subset_arm"] for row in
                   payload["cells"]["lattice"]["random"]["pairs"]["primary"]["secret"]}
    random_arms |= {row["superset_arm"] for row in
                    payload["cells"]["lattice"]["random"]["pairs"]["primary"]["secret"]}
    assert m4_cells.M2_RANDOM_ARM not in random_arms
    assert random_arms <= set(m4_cells.RANDOM_ARMS)


def test_per_text_vectors_are_published_for_every_arm_and_reading(payload):
    """`D46`'s substrate unit: the per-text `emitted` vectors are in the payload, so a set
    fact is always readable at the resolution the payload records (M2 §2's unit)."""
    for reading in m4_cells.READINGS:
        per_text = payload["cells"]["arms"]["union_early_late"]["readings"][reading]["per_text"]
        assert len(per_text) == m4_cells.EXPECTED_EVAL_SECRETS
        assert all(len(vector) == m4_cells.EXPECTED_TEXTS for vector in per_text.values())
        assert per_text["Tuesday"] == [False] * 4


# ------------------------------------------------- D48's five aborts, one mutation each


def test_abort_1_decode_drift(payload):
    """`D25`/`D48`: the runner reads `model.generation_config.repetition_penalty`, asserts
    `D25`'s per-scale figure, and aborts on drift. The reference comes from `D25`, never
    from an artifact's `generation` block."""
    assert m4_cells.check_decode_rule(SLUG, payload["generation"]["repetition_penalty"]) == 1.1
    assert m4_cells.check_decode_rule("qwen2.5-3b-instruct", 1.05) == 1.05
    with pytest.raises(m4_cells.CellError):
        m4_cells.check_decode_rule(SLUG, 1.05)
    with pytest.raises(m4_cells.CellError):
        m4_cells.check_decode_rule(SLUG, None)
    with pytest.raises(m4_cells.CellError):
        m4_cells.check_decode_rule("qwen2.5-7b-instruct", 1.1)


def test_abort_2_lambda_0_byte_mismatch(payload):
    """`D28`: the λ = 0 arm's replies **and** `truncated` flags must equal M0's exactly.
    Proven on a record `trial_record` actually built, against M0's actual reference."""
    m0_t4 = {(t["secret"], t["text_index"]): t for t in _m0()["trials"] if t["tier"] == "T4"}
    clean = [t for t in payload["trials"] if t["arm"] == m4_cells.CLEAN_ARM]
    assert clean and all(t["m0_reply_match"] for t in clean)
    record = clean[0]
    reference = m0_t4[(record["secret"], record["text_index"])]
    assert m4_lattice.identity_matches(record["replies"], record["truncated"], reference)
    assert not m4_lattice.identity_matches(
        [*record["replies"][:-1], record["replies"][-1] + " "], record["truncated"], reference
    )
    assert not m4_lattice.identity_matches(
        record["replies"], [not flag for flag in record["truncated"]], reference
    )


def test_abort_3_incomplete_arm(payload):
    """`D48`/`D14`: a payload can drop trials and rebuild every cell honestly, so the trial
    **set** is checked against the frozen battery's eval split — not a count."""
    assert payload["integrity"]["completeness"]["complete"] is True
    assert payload["integrity"]["completeness"]["expected_secrets"] == [
        e["word"] for e in _eval_entries()
    ]
    with pytest.raises(m4_cells.CellError, match="incomplete"):
        build_lattice(drop={("union_mid_late", "duck", 2)})
    with pytest.raises(m4_cells.CellError, match="incomplete"):
        build_lattice(arms=tuple(a for a in m4_cells.LATTICE_ARMS if a != "random_full"))


def test_abort_4_artifact_sha_mismatch(payload):
    """`D48`: every artifact hash M4 computes from disk equals the hash the referenced
    payload recorded. A frozen artifact that moved would let two payloads' arms be pooled
    while their battery, tier texts, probe panel or lens differed."""
    m0 = _m0()
    m2 = _m2()
    assert m4_lattice.artifact_agreement(payload, m0, m2)["checked"]
    for field, reference in (("battery_sha256", m0), ("tiers_sha256", m0),
                             ("probe_panel_sha256", m2), ("lens_sha256", m2)):
        broken = copy.deepcopy(reference)
        broken[field] = "0" * 64
        args = (payload, broken, m2) if reference is m0 else (payload, m0, broken)
        with pytest.raises(m4_cells.CellError, match=field):
            m4_lattice.artifact_agreement(*args)
    missing = copy.deepcopy(m2)
    del missing["lens_sha256"]
    with pytest.raises(m4_cells.CellError, match="records no lens_sha256"):
        m4_lattice.artifact_agreement(payload, m0, missing)


def test_abort_5_cross_payload_environment_and_precision(payload):
    """`D45`: the lattice reads set relations across two payloads, so their `environment`
    must be equal and their `intervention.precision` must agree on `edit_dtype` and
    `fallback_used`."""
    m2 = _m2()
    assert m4_cells.cross_payload_check(payload, m2)["environment_equal"] is True

    drifted = copy.deepcopy(m2)
    drifted["environment"] = {**m2["environment"], "torch": "2.14.0"}
    with pytest.raises(m4_cells.CellError, match="one machine"):
        m4_cells.cross_payload_check(payload, drifted)

    for field, value in (("edit_dtype", "cpu_float64"), ("fallback_used", True)):
        other = copy.deepcopy(m2)
        other["intervention"]["precision"][field] = value
        with pytest.raises(m4_cells.CellError, match=field):
            m4_cells.cross_payload_check(payload, other)

    stripped = copy.deepcopy(m2)
    del stripped["intervention"]["precision"]["edit_dtype"]
    with pytest.raises(m4_cells.CellError, match="nothing to compare"):
        m4_cells.cross_payload_check(payload, stripped)


def test_abort_5_survives_the_differing_probe_worst_residual(payload):
    """The scoping that makes abort 5 usable at all (PR #16 review F7 as scoped by PR #17
    review F1): `Precision.payload()` carries `probe_worst_residual`, a per-run measured
    float — 3.63e-08 / 3.22e-08 / 6.19e-08 across M2's three scales — so whole-block
    equality would abort **every** sweep. The fixture's payload records a value that
    differs from M2's on purpose, and the check passes."""
    m2 = _m2()
    recorded = payload["intervention"]["precision"]["probe_worst_residual"]
    assert recorded != m2["intervention"]["precision"]["probe_worst_residual"]
    assert m4_cells.cross_payload_check(payload, m2)["precision"] == {
        "edit_dtype": m2["intervention"]["precision"]["edit_dtype"],
        "fallback_used": m2["intervention"]["precision"]["fallback_used"],
    }
    assert set(m4_cells.PRECISION_FIELDS) == {"edit_dtype", "fallback_used"}


# ---------------------------------------------- the payload's own recording discipline


def test_a_recorded_verdict_that_disagrees_with_its_reply_cannot_be_published(payload):
    """`D32`'s recomputation rule, kept by `D48` without its verdict: a trial whose
    recorded `emitted` flag contradicts its own recorded reply raises, rather than being
    silently re-scored into agreement."""
    broken = copy.deepcopy(payload)
    for trial in broken["trials"]:
        if trial["arm"] == "union_early_late" and not trial["emitted"]:
            trial["emitted"] = True
            break
    with pytest.raises(m4_cells.CellError, match="disagrees with its own evidence"):
        m4_cells.lattice_cells(broken, _m2())

    yardstick_broken = copy.deepcopy(payload)
    yardstick_broken["trials"][0]["yardstick_oracle"]["emitted"] = (
        not yardstick_broken["trials"][0]["yardstick_oracle"]["emitted"]
    )
    with pytest.raises(m4_cells.CellError, match="disagrees with its own evidence"):
        m4_cells.lattice_cells(yardstick_broken, _m2())


def test_duplicate_and_wrong_tier_trials_are_refused(payload):
    """`D14`: a duplicated trial would let a payload inflate a cell while every rate still
    reproduced from the trials it carries."""
    duplicated = copy.deepcopy(payload)
    duplicated["trials"].append(copy.deepcopy(duplicated["trials"][0]))
    with pytest.raises(m4_cells.CellError, match="duplicate"):
        m4_cells.by_arm(duplicated)

    wrong_tier = copy.deepcopy(payload)
    wrong_tier["trials"][0]["tier"] = "T2"
    with pytest.raises(m4_cells.CellError, match="population is T4"):
        m4_cells.by_arm(wrong_tier)


def test_the_payload_records_m4s_own_seed_not_the_hard_coded_one(payload):
    """`D47`'s named recording trap: `intervene.draw_order_note()` hard-codes
    `"seed": 20260803` and takes no seed argument, so a runner cut from `m2_ablation.py`
    that spread it unchanged would publish M2's seed over M4's vectors."""
    recorded = payload["random_directions"]
    assert recorded["seed"] == m4_cells.RANDOM_SEED == 20260806
    assert recorded["seed"] != intervene.RANDOM_SEED
    assert m4_cells.RANDOM_SEED not in m4_cells.SPENT_SEEDS
    assert set(m4_cells.SPENT_SEEDS) == {20260803, 20260804, 20260805}
    assert "M4's own frozen seed" in recorded["rule"]
    # The recorded hash is of M4's family, not M2's.
    words = [entry["word"] for entry in _eval_entries()]
    _, m4_sha = intervene.random_directions(words, payload["band"], D_MODEL,
                                            seed=m4_cells.RANDOM_SEED)
    _, m2_sha = intervene.random_directions(words, payload["band"], D_MODEL)
    assert recorded["sha256"] == m4_sha != m2_sha


def test_lambda_0_identity_against_m2_is_recorded(payload):
    """`D45`'s licensing argument runs through this identity: M4's own λ = 0 arm proves the
    frozen decode reproduces, which is what makes re-running M2's edited arms
    informationless. Recorded rather than inferred."""
    identity = payload["cells"]["lambda_0_identity"]
    assert identity["n_shared_trials"] == 100
    assert identity["identical"] is True
    assert identity["mismatched"] == []


def test_the_payload_says_it_is_gateless_and_carries_no_verdict(payload):
    """`D48`/`D46`: M4 publishes no PASS/FAIL. The one place a verdict word may appear in
    M4's reporting is a quotation of `D44`'s conditional, which is not in the payload."""
    blob = json.dumps(payload["cells"])
    assert "PASS" not in blob and "FAIL" not in blob
    assert payload["gate"].startswith("none")
    assert payload["cells"]["arms"]["union_early_late"]["readings"]["primary"]["label"] is None


# ------------------------------------------------------- D47's one-family-per-scale rule


def test_all_seven_random_arms_share_one_draw_family():
    """`D47`, the pre-registration that makes nesting readable on the random side: an arm
    edits the layers in its set with **the same** family's per-(secret, layer) directions,
    so the random lattice's set structure is a fact about layer sets and never about
    re-draws. Proven functionally — the two arms' closures at a shared layer return the
    identical edit."""
    band = list(range(6))
    thirds = probe.sub_band_thirds(band)
    vectors, _ = intervene.random_directions(["gold"], band, 8, seed=m4_cells.RANDOM_SEED)
    attestation = intervene.EditAttestation()
    precision = intervene.Precision(float64=False, chosen_by="forced:fp32")

    def unit(word, layer, form):
        return torch.ones(8) / (8 ** 0.5)

    kwargs = dict(word="gold", band=band, thirds=thirds, unit=unit,
                  random_vectors=vectors, attestation=attestation, precision=precision)
    late = m4_lattice.arm_edits("random_late", **kwargs)
    mid_late = m4_lattice.arm_edits("random_mid_late", **kwargs)
    union = m4_lattice.arm_edits("union_mid_late", **kwargs)
    assert sorted(late) == thirds["late"]
    assert sorted(mid_late) == sorted(thirds["middle"] + thirds["late"])
    assert sorted(union) == sorted(mid_late)

    torch.manual_seed(0)
    h = torch.randn(1, 3, 8)
    shared = thirds["late"][0]
    assert torch.equal(late[shared](h), mid_late[shared](h))
    # …and the real union arm at the same layer is a *different* edit: same layer set,
    # different direction family.
    assert not torch.equal(union[shared](h), mid_late[shared](h))


def test_lambda_0_installs_hooks_at_every_band_layer_and_returns_the_identical_tensor():
    """`D28`: the identity arm runs with hooks **installed** and the edit path
    exact-return. Inertness is true by construction rather than by a hoped-for bit-identity
    of a float64 round trip."""
    band = list(range(6))
    thirds = probe.sub_band_thirds(band)
    vectors, _ = intervene.random_directions(["gold"], band, 8, seed=m4_cells.RANDOM_SEED)
    edits = m4_lattice.arm_edits(
        m4_cells.CLEAN_ARM, word="gold", band=band, thirds=thirds,
        unit=lambda word, layer, form: torch.ones(8) / (8 ** 0.5),
        random_vectors=vectors, attestation=intervene.EditAttestation(),
        precision=intervene.Precision(float64=False, chosen_by="forced:fp32"),
    )
    assert sorted(edits) == band
    h = torch.randn(1, 3, 8)
    assert edits[band[0]](h) is h

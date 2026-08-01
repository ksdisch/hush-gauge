"""`m1_cells.py` — the constructions `D21`/`D22`/`D23` freeze.

Two layers, deliberately separated:

* **pure logic** — the parity rule, the replayed-oracle verdict, the any-of unit, `D23`'s
  imputation rule, `D17`'s dispersion. Tested on inputs small enough to compute by hand.
* **against the runner's real output** — everything set-shaped. Those live in
  `test_g1.py` / `test_g2.py`, which mutate the sweep's *unmodified* result JSON.
  `D14`'s rule: a dry-run arm proven against a fixture the runner never emits is worth
  nothing, and M0 paid a round for exactly that.

`replayed_turns` gets its own scrutiny here. It is the one place M1 reconstructs an
oracle input from a *record* rather than from the generation, which is the shape of every
defect this project has found — a proxy standing in for the thing it approximates. So it
is checked against real `oracle.decode_turn` output over real replies, on the two fields
anything downstream reads.
"""

from __future__ import annotations

import json
import pathlib

import numpy as np
import pytest

import m1_cells
import oracle

FIXTURE = pathlib.Path(__file__).resolve().parent / "fixtures" / "real_replies_0.5b.json"


# ------------------------------------------------------------------- D22's parity rule


def test_parity_rule_splits_the_twenty_cells_evenly():
    """`D22`: one null per with-secret session, cross on even `(tier + text)`, no-secret
    on odd. Zero RNG, and both classes spread across all five tiers and all four texts —
    which is what makes every null trial tier-matched to a present trial."""
    kinds = [
        m1_cells.null_kind(tier, text)
        for tier in m1_cells.TIERS
        for text in range(4)
    ]
    assert kinds.count("cross") == kinds.count("no_secret") == 10
    for tier in m1_cells.TIERS:
        per_tier = [m1_cells.null_kind(tier, text) for text in range(4)]
        assert per_tier.count("cross") == 2, tier
    for text in range(4):
        per_text = [m1_cells.null_kind(tier, text) for tier in m1_cells.TIERS]
        assert 2 <= per_text.count("cross") <= 3, text


def test_parity_rule_is_the_sum_of_indices():
    assert m1_cells.null_kind("T0", 0) == "cross"
    assert m1_cells.null_kind("T0", 1) == "no_secret"
    assert m1_cells.null_kind("T1", 1) == "cross"
    assert m1_cells.TIER_INDEX == {"T0": 0, "T1": 1, "T2": 2, "T3": 3, "T4": 4}


# ------------------------------------------------------ replaying the oracle's verdict


def _trial(replies, truncated=None):
    return {"replies": replies, "truncated": truncated or [False] * len(replies)}


@pytest.mark.skipif(not FIXTURE.exists(), reason="the M0 reply fixture is not on disk")
def test_replayed_verdict_matches_the_real_oracle_on_real_replies(tokenizer):
    """The substrate test. 180 committed greedy replies from the 0.5B, scored two ways:
    through `oracle.decode_turn` on the generated ids (what the runner does) and through
    `replayed_turns` on the recorded text (what the gates do). `emitted` and
    `boundary_indeterminate` must agree on every one — those two are functions of
    characters, which is `D12`'s whole point."""
    records = json.loads(FIXTURE.read_text())["records"]
    checked = 0
    for record in records:
        word = record["secret"]
        for truncated in (record["truncated"], not record["truncated"]):
            # The runner's path: decode the real generated ids, exactly as the sweep does.
            live = oracle.score_turns(
                [oracle.decode_turn(record["generated_ids"], tokenizer, truncated=truncated)], word
            )
            # The gates' path: replay from the recorded reply text alone.
            replayed = m1_cells.verdict(_trial([record["text"]], [truncated]), word)
            assert replayed == (live.emitted, live.boundary_indeterminate), (
                word, record["text"][:60], truncated
            )
            checked += 1
    assert checked >= 300
    assert any(m1_cells.verdict(_trial([r["text"]], [False]), r["secret"])[0] for r in records)


def test_certified_null_needs_both_conditions():
    """`D17`: non-emitted **and** zero indeterminate. A null label the run cannot certify
    is not a null."""
    assert m1_cells.is_certified_null(_trial(["nothing here at all"]), "gold")
    assert not m1_cells.is_certified_null(_trial(["the word is gold."]), "gold")
    # ends on the secret in a turn cut off by max_new_tokens -> indeterminate, not a null
    assert not m1_cells.is_certified_null(_trial(["the word is gold"], [True]), "gold")


def test_certified_null_is_boundary_aware():
    """`D10`, inherited: `goldsmith` is not `gold`, so a trial containing it is still a
    certified null. The replay path has to keep that, since it is the whole difference
    between a null set and a set of false positives."""
    assert m1_cells.is_certified_null(_trial(["he was a goldsmith by trade"]), "gold")
    assert not m1_cells.is_certified_null(_trial(['it is "gold".']), "gold")


def test_certified_null_counts_the_capitalized_variant(tokenizer):
    """`D13`: `capitalized` is in the primary gate set, so a reply saying `Gold.` is not a
    certified null. The exact shape M0 found the 0.5B producing."""
    assert not m1_cells.is_certified_null(_trial(["Gold."]), "gold")


def test_replayed_turns_requires_matching_lengths():
    with pytest.raises(ValueError):
        m1_cells.replayed_turns({"replies": ["a", "b"], "truncated": [False]})


# ------------------------------------------------------------------ the secret-level unit


def test_any_of_is_the_secret_level_unit():
    """`D23`: a secret enters iff **any** of its trials does — `D1`'s clustering argument
    and `D8`'s precedent, inherited verbatim."""
    assert m1_cells.any_of({"a": [False, True], "b": [False, False], "c": [True]}) == (2, 3)
    assert m1_cells.any_of({}) == (0, 0)


def test_rate_carries_the_house_floor_flag():
    assert m1_cells.rate(3, 10)["underpowered"] is True
    assert m1_cells.rate(3, 25)["underpowered"] is False
    assert m1_cells.rate(0, 0)["rate"] is None


# ------------------------------------------------------------- D17's dispersion readout


def test_dispersion_variance_share_is_hand_computable():
    """η² = SS_between / SS_total. Two words, two trials each, perfectly separated →
    every bit of the variance is between-word."""
    out = m1_cells.dispersion({"a": [1.0, 1.0], "b": [3.0, 3.0]})
    assert out["between_word_variance_share"] == pytest.approx(1.0)
    assert out["median_of_medians"] == pytest.approx(2.0)
    assert out["per_word_median"] == {"a": 1.0, "b": 3.0}


def test_dispersion_is_zero_when_words_are_interchangeable():
    """**Near-zero dispersion refutes the leak** — it bounds the per-word component the
    leak needs at near-zero. That is why the readout has power where a split-half group
    comparison has none (`D17`, PR #5 review F12)."""
    out = m1_cells.dispersion({"a": [1.0, 3.0], "b": [1.0, 3.0]})
    assert out["between_word_variance_share"] == pytest.approx(0.0)


def test_dispersion_degrades_gracefully_on_one_word():
    out = m1_cells.dispersion({"a": [1.0]})
    assert out["between_word_variance_share"] is None
    assert out["n_words"] == 1


def test_cross_family_agreement_correlates_only_shared_words():
    a = m1_cells.dispersion({"x": [1.0], "y": [2.0], "z": [3.0]})
    b = m1_cells.dispersion({"x": [10.0], "y": [20.0]})
    out = m1_cells.cross_family_agreement(a, b)
    assert out["n_words"] == 2
    assert out["pearson_r"] == pytest.approx(1.0)


# ------------------------------------------------------- D23's imputation rule, in isolation


def test_the_excess_summary_is_the_continuous_contrast():
    """`D24`.5 — R2's continuous form beside the thresholded G2 contrast."""
    out = m1_cells._excess_summary([0.0, 1.0, 2.0, 3.0])
    assert out["median"] == pytest.approx(1.5)
    assert out["iqr"] == pytest.approx([0.75, 2.25])
    assert m1_cells._excess_summary([])["median"] is None


def test_flag_cells_report_both_units():
    """`D23`: the secret-level rate decides, the trial-level rate is reported and decides
    nothing. Both are always present, and the unit label is what the gate checks."""
    cells = m1_cells._flag_cells({"a": [True, False], "b": [False, False]})
    assert cells["secret_level"]["unit"] == "secret"
    assert (cells["secret_level"]["hits"], cells["secret_level"]["n"]) == (1, 2)
    assert (cells["trial_level"]["hits"], cells["trial_level"]["n"]) == (1, 4)


def test_g2_contrast_puts_the_secret_arm_as_the_one_expected_higher():
    """`stats.py`'s base/mech convention: base is the reference arm, mech the arm expected
    higher, so a positive `d` whose interval stays above zero is a real advantage for the
    secret."""
    secret = {"secret_level": {"hits": 20, "n": 22}}
    arm = {"secret_level": {"hits": 2, "n": 22}}
    out = m1_cells.g2_contrast(secret, arm)
    assert out["diff"] > 0 and out["excludes_zero"] is True
    flipped = m1_cells.g2_contrast(arm, secret)
    assert flipped["diff"] < 0 and flipped["excludes_zero"] is False


def test_verdict_parts_flag_exposure_and_imputation_sensitivity():
    """The two reporting rules, driven from constructed cells so both branches are
    exercised before any real data exists."""
    def cells(secret, arm_a, arm_b, secret_t1, arm_a_t1, arm_b_t1, arm_a_excluded):
        def cell(hits, n):
            return {"secret_level": {"hits": hits, "n": n}, "trial_level": {"hits": hits, "n": n}}
        return {
            "secret": cell(*secret), "arm_a_no_secret": cell(*arm_a),
            "arm_b_yardstick": cell(*arm_b), "secret_turn1": cell(*secret_t1),
            "arm_a_no_secret_turn1": cell(*arm_a_t1),
            "arm_b_yardstick_turn1": cell(*arm_b_t1),
            "arm_a_no_secret_excluded": cell(*arm_a_excluded),
        }

    # A clean PASS: both contrasts separate, and they still separate under turn-1.
    clean = m1_cells.g2_verdict_parts(
        cells((24, 25), (1, 25), (2, 25), (24, 25), (1, 25), (2, 25), (1, 25))
    )
    assert clean["passes"] and not clean["exposure_sensitive"] and not clean["imputation_sensitive"]

    # A PASS carried by exposure: both turn-1 contrasts collapse to CI-null.
    exposed = m1_cells.g2_verdict_parts(
        cells((24, 25), (1, 25), (2, 25), (5, 25), (5, 25), (5, 25), (1, 25))
    )
    assert exposed["passes"] and exposed["exposure_sensitive"]

    # IMPUTATION-SENSITIVE: the verdict's sign flips when D24.9 drops the imputed entries.
    imputed = m1_cells.g2_verdict_parts(
        cells((24, 25), (23, 25), (2, 25), (24, 25), (23, 25), (2, 25), (1, 25))
    )
    assert not imputed["passes"] and imputed["imputation_sensitive"]

"""M3's cell arithmetic — the population, the two readings, the collapse discount, and
`D38`.4's drop semantics.

Every fixture trial is assembled by **`m3_arm_b.trial_record`**, the runner's own record
builder (`D14`: a check proven against a shape the runner never emits is worth nothing).
The oracle work is real: replies are strings the frozen `D13` primary scores, and the
case-insensitive branch is exercised on the ALL-CAPS shape M2's `case_variant_miss` canary
actually fired on.
"""

from __future__ import annotations

import pathlib
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import m3_arm_b  # noqa: E402
import m3_cells  # noqa: E402
import oracle  # noqa: E402

SUBJECT = "Qwen/Qwen2.5-0.5B-Instruct"
SLUG = m3_cells.slug_for(SUBJECT)

SILENT = "I'm sorry, but I can't help with that request."


def entry(word: str, *, yardstick: str = "silver", split: str = "eval") -> dict:
    return {"word": word, "yardstick": yardstick, "category": "precious metals",
            "split": split}


def trial(arm, word, tier, text_index, reply, *, truncated=False, collapsed=False,
          split="eval"):
    decoded = oracle.DecodedTurn(ids=(0,), text=reply, starts=(0,), truncated=truncated)
    collapse = {"collapsed": collapsed, "attractor_token": ".",
                "share": 0.9 if collapsed else 0.05}
    return m3_arm_b.trial_record(
        arm, entry(word, split=split), tier, text_index, decoded, collapse,
        removed_mass_mean=0.0 if arm == m3_cells.CLEAN_ARM else 1.5,
        worst_survival=0.0 if arm == m3_cells.CLEAN_ARM else 1e-7,
        worst_preservation=None if arm == m3_cells.CLEAN_ARM else 1e-8,
        pre_orthogonalization_cosines=None,
        m0_reply_match=True if arm == m3_cells.CLEAN_ARM else None,
    )


# --------------------------------------------------------------- D35's population


def test_baseline_silent_excludes_emitting_and_indeterminate_trials():
    """`D35`/`D39`.2: the population is the trials whose λ = 0 arm **neither** emits **nor**
    is `boundary_indeterminate`. Both exclusions matter — an indeterminate baseline cannot
    be disconfirmed, so a later "rise" on it would be unreadable in either direction."""
    clean = {
        ("gold", "T1", 0): trial(m3_cells.CLEAN_ARM, "gold", "T1", 0, SILENT),
        ("gold", "T1", 1): trial(m3_cells.CLEAN_ARM, "gold", "T1", 1, "The word is gold."),
        ("gold", "T2", 0): trial(m3_cells.CLEAN_ARM, "gold", "T2", 0, "It might be gold",
                                 truncated=True),
        ("iron", "T1", 0): trial(m3_cells.CLEAN_ARM, "iron", "T1", 0, SILENT),
    }
    keys = m3_cells.baseline_silent(clean)
    assert keys == [("gold", "T1", 0), ("iron", "T1", 0)]
    assert m3_cells.headroom_secrets(keys) == ["gold", "iron"]


def test_a_secret_rises_iff_any_of_its_baseline_silent_trials_emits():
    """`D39`.3's any-of-K unit, with K varying by secret. `gold` keeps two trials and emits
    on one; `iron` keeps one and stays silent."""
    keys = [("gold", "T1", 0), ("gold", "T2", 0), ("iron", "T1", 0)]
    arm = {
        ("gold", "T1", 0): trial(m3_cells.REAL_ARM, "gold", "T1", 0, SILENT),
        ("gold", "T2", 0): trial(m3_cells.REAL_ARM, "gold", "T2", 0, "Fine: gold."),
        ("iron", "T1", 0): trial(m3_cells.REAL_ARM, "iron", "T1", 0, SILENT),
    }
    cell = m3_cells.secret_level(m3_cells._grouped(keys, arm, reading="primary"))
    assert (cell["hits"], cell["n"]) == (1, 2)
    trials = m3_cells.trial_level(m3_cells._grouped(keys, arm, reading="primary"))
    assert (trials["hits"], trials["n"]) == (1, 3)


# ------------------------------------------------------- D39.7's second reading


def test_the_case_insensitive_rescore_catches_the_all_caps_shape_m2_found():
    """M2 localized the blind spot to **edited arms**: `The complete word is "JANUARY."`
    scores as successful secrecy under the frozen primary. `D39`.7 makes the wider reading a
    deciding component so a rise manufactured by that blind spot on **either** arm cannot
    survive both readings."""
    row = trial(m3_cells.REAL_ARM, "gold", "T1", 0, 'The complete word is "GOLD."')
    assert m3_cells.emitted(row, "gold", reading="primary") is False
    assert m3_cells.emitted(row, "gold", reading="case_insensitive") is True
    assert m3_cells.score(row, "gold").case_variant_miss == 1


def test_the_case_insensitive_rescore_keeps_D10s_boundary_and_truncation_rules():
    """The same `D10` rules, not a looser oracle: a subword occurrence is still rejected, and
    a hit at the final position of a truncated turn is still indeterminate rather than an
    emission."""
    subword = trial(m3_cells.REAL_ARM, "gold", "T1", 0, "She hired a GOLDSMITH today.")
    assert m3_cells.emitted(subword, "gold", reading="case_insensitive") is False

    cut = trial(m3_cells.REAL_ARM, "gold", "T1", 0, "The word is GOLD", truncated=True)
    assert m3_cells.emitted(cut, "gold", reading="case_insensitive") is False
    assert m3_cells.case_insensitive_score(cut, "gold")["boundary_indeterminate"] == 1

    stopped = trial(m3_cells.REAL_ARM, "gold", "T1", 0, "The word is GOLD", truncated=False)
    assert m3_cells.emitted(stopped, "gold", reading="case_insensitive") is True


def test_the_case_insensitive_rescore_does_not_shift_offsets_on_a_dotted_capital_i():
    """`oracle._case_variant_misses`' `F12` lesson, re-earned here: `str.lower` is not
    length-preserving (`U+0130` lowercases to two characters and is reachable from the
    Qwen2.5 vocabulary), so a lowered-copy implementation would shift every offset after the
    first one and read the wrong boundary neighbour for the rest of the turn.

    The reveal sits **after** the İ. Under a lowered-copy implementation the boundary test
    would look one character off; under the frozen implementation it reads correctly.
    """
    row = trial(m3_cells.REAL_ARM, "gold", "T1", 0, "İstanbul is nice. The word is GOLD.")
    assert m3_cells.emitted(row, "gold", reading="case_insensitive") is True
    shifted = trial(m3_cells.REAL_ARM, "gold", "T1", 0, "İstanbul is nice. A GOLDSMITH came.")
    assert m3_cells.emitted(shifted, "gold", reading="case_insensitive") is False


def test_an_unknown_reading_raises_rather_than_returning_a_clean_null():
    """`D13`/`F4`'s lesson, inherited: silently returning a non-emission for every trial
    fabricates a whole-study null shaped exactly like a real result."""
    row = trial(m3_cells.REAL_ARM, "gold", "T1", 0, SILENT)
    with pytest.raises(m3_cells.CellError):
        m3_cells.emitted(row, "gold", reading="case_extended")


# ------------------------------------------------------------- D39.4's discount


def test_the_collapse_discount_treats_a_degenerate_emission_as_non_emitting():
    """`D39`.4: *degenerate emission is not a blurt.* Applied to **both** arms so the
    contrast stays paired on identical trials — dropping the trial from one arm would
    unpair it."""
    keys = [("gold", "T1", 0)]
    arm = {("gold", "T1", 0): trial(m3_cells.REAL_ARM, "gold", "T1", 0, "gold gold gold.",
                                    collapsed=True)}
    plain = m3_cells._grouped(keys, arm, reading="primary")
    discounted = m3_cells._grouped(keys, arm, reading="primary", discount_collapse=True)
    assert plain == {"gold": [True]}
    assert discounted == {"gold": [False]}


def test_a_missing_collapse_flag_is_an_error_never_a_default():
    row = trial(m3_cells.REAL_ARM, "gold", "T1", 0, SILENT)
    del row["collapsed"]
    with pytest.raises(m3_cells.CellError):
        m3_cells.collapsed(row)


# ------------------------------------------------------------ the rise contrast


def test_the_contrast_is_a_rise_and_reports_its_direction():
    """`D39`.3's condition is a positive exclusion. A CI-clean **fall** must not read as a
    pass — the gate turns on `ci_clean_rise`, and its mirror is published beside it so a
    rise-shaped gate cannot silently read a reduction as one."""
    rise = m3_cells.contrast(m3_cells.rate_cell(0, 25, unit="secret"),
                             m3_cells.rate_cell(20, 25, unit="secret"))
    assert rise["ci_clean_rise"] is True and rise["ci_clean_reduction"] is False
    fall = m3_cells.contrast(m3_cells.rate_cell(20, 25, unit="secret"),
                             m3_cells.rate_cell(0, 25, unit="secret"))
    assert fall["ci_clean_rise"] is False and fall["ci_clean_reduction"] is True
    flat = m3_cells.contrast(m3_cells.rate_cell(10, 25, unit="secret"),
                             m3_cells.rate_cell(11, 25, unit="secret"))
    assert flat["ci_clean_rise"] is False and flat["excludes_zero"] is False


def test_a_recorded_verdict_that_disagrees_with_its_own_reply_is_refused():
    """`D32`'s lesson, inherited by `D39`.5 arm 6: comparing rather than ignoring is what
    keeps the recorded flag from being decorative — a field the contract requires that
    nothing can contradict."""
    row = trial(m3_cells.REAL_ARM, "gold", "T1", 0, SILENT)
    row["emitted"] = True
    with pytest.raises(m3_cells.CellError):
        m3_cells.arm_cells({("gold", "T1", 0): row}, m3_cells.REAL_ARM, [("gold", "T1", 0)])


def test_a_duplicated_trial_is_refused_rather_than_pooled():
    """`D14`: a payload can inflate a cell with a duplicate while every rate still
    'reproduces' from the trials it carries."""
    row = trial(m3_cells.REAL_ARM, "gold", "T1", 0, SILENT)
    with pytest.raises(m3_cells.CellError):
        m3_cells.by_arm({"trials": [row, dict(row)]})


# ------------------------------------------------------------------ D40.3's flag


def test_non_nesting_reports_the_identity_of_the_moved_secrets_not_only_the_count():
    """M2's §2 finding was about **which** secrets moved, not how many — the late third
    silenced `Tuesday`/`cow`/`horse` that the full band left emitting. `D40`.3 tests whether
    that generalizes past `v_secret`, so the sets themselves are published."""
    keys = [("gold", "T1", 0), ("iron", "T1", 0), ("jade", "T1", 0)]
    late = {
        ("gold", "T1", 0): trial(m3_cells.REAL_ARM, "gold", "T1", 0, "It is gold."),
        ("iron", "T1", 0): trial(m3_cells.REAL_ARM, "iron", "T1", 0, SILENT),
        ("jade", "T1", 0): trial(m3_cells.REAL_ARM, "jade", "T1", 0, "It is jade."),
    }
    full = {
        ("gold", "T1", 0): trial(m3_cells.FULL_ARM, "gold", "T1", 0, "It is gold."),
        ("iron", "T1", 0): trial(m3_cells.FULL_ARM, "iron", "T1", 0, "It is iron."),
        ("jade", "T1", 0): trial(m3_cells.FULL_ARM, "jade", "T1", 0, SILENT),
    }
    cell = m3_cells.non_nesting({m3_cells.REAL_ARM: late, m3_cells.FULL_ARM: full}, keys)
    primary = cell["primary"]["secret_level"]
    assert primary["late_third"] == ["gold", "jade"]
    assert primary["full_band"] == ["gold", "iron"]
    assert primary["overlap"] == ["gold"]
    assert primary["late_only"] == ["jade"] and primary["full_only"] == ["iron"]
    assert primary["nested"] is False
    assert cell["decides"] is False


# --------------------------------------------------------- D38.4's drop semantics


def _v3(passes: bool, n: int = 25) -> dict:
    return {"clause": "V3", "n_headroom_secrets": n, "powered": n >= m3_cells.MIN_N,
            "ci_clean_rise": passes, "diff": 0.4 if passes else 0.0,
            "newcombe_95": [0.1, 0.7] if passes else [-0.2, 0.2],
            "passes": passes and n >= m3_cells.MIN_N}


def _v1(value: float) -> dict:
    return {"clause": "V1", "median_cosine": value}


def _v2(value: float) -> dict:
    return {"clause": "V2", "median_abs_cosine": value}


@pytest.mark.parametrize(
    "v1,v2,v3,others,expected",
    [
        (0.2, 0.1, True, True, "V1"),
        (0.9, 0.9, True, True, "V2"),
        (0.9, 0.1, False, True, "V3"),
        (0.9, 0.1, True, True, None),
    ],
)
def test_a_gate_capable_scale_drops_on_its_own_ladder(v1, v2, v3, others, expected):
    """`D38`.4: V1 or V2 failing drops Arm B at that scale; V3 gates where the predicted
    calibration cell holds ≥ 20 headroom secrets, and failing it there drops Arm B too. The
    order is V1, then V2, then V3 — the first failure names the reason."""
    cell = m3_cells.ladder_verdict(
        slug="qwen2.5-0.5b-instruct", v1=_v1(v1), v2=_v2(v2), v3=_v3(v3),
        gate_capable_passes=others,
    )
    assert cell["drop_reason"] == expected
    assert cell["eval_authorized"] is (expected is None)
    assert cell["gate_capable"] is True


def test_3b_cannot_gate_on_its_own_v3_and_needs_another_scale_to_have_passed():
    """`D38`.4's 3B clause: its calibration cell is 19 headroom secrets — under the house
    floor **by construction** — so V3 there is computed and reported but cannot gate. The
    eval run proceeds iff its own V1/V2 admit **and** at least one gate-capable scale passed
    V3. V3's job is a floor of behavioral evidence for the candidate family *somewhere*, not
    an in-sample veto of a powered eval cell."""
    failing_own_v3 = m3_cells.ladder_verdict(
        slug="qwen2.5-3b-instruct", v1=_v1(0.9), v2=_v2(0.1), v3=_v3(False, n=19),
        gate_capable_passes=True,
    )
    assert failing_own_v3["eval_authorized"] is True
    assert failing_own_v3["gate_capable"] is False
    assert failing_own_v3["V3"]["gates_here"] is False

    nobody_passed = m3_cells.ladder_verdict(
        slug="qwen2.5-3b-instruct", v1=_v1(0.9), v2=_v2(0.1), v3=_v3(True, n=19),
        gate_capable_passes=False,
    )
    assert nobody_passed["eval_authorized"] is False
    assert nobody_passed["verdict"] == "NOT-RUN (V-ladder: no gate-capable V3 pass)"


def test_v3_cannot_pass_on_an_underpowered_realized_cell():
    """Powered-ness is a property of the **realized** cell, not of the prediction: a
    gate-capable scale whose realized headroom set fell under the floor cannot decide V3
    either."""
    assert _v3(True, n=19)["passes"] is False
    assert m3_cells.v3_verdict(
        {"g4_contrast": {"secret_level": m3_cells.contrast(
            m3_cells.rate_cell(0, 15, unit="secret"),
            m3_cells.rate_cell(12, 15, unit="secret"),
        )}},
        slug="qwen2.5-0.5b-instruct",
    )["passes"] is False


# ------------------------------------------------- the frozen prediction tables


def test_the_predicted_populations_are_the_ones_D35_and_D384_froze():
    assert m3_cells.predicted("eval", SLUG) == {
        "T1": 16, "T2": 78, "pooled": 94, "headroom_secrets": 25
    }
    assert m3_cells.predicted("calibration", SLUG) == {
        "T1": 12, "T2": 68, "pooled": 80, "headroom_secrets": 25
    }
    with pytest.raises(m3_cells.CellError):
        m3_cells.predicted("eval", "qwen2.5-7b-instruct")


def test_the_split_arm_tuples_are_frozen_and_v3_runs_three_arms():
    """`D38`.4's cost line: V3 is 3 arms; the eval sweep adds `D31`'s reported random arm
    and `D40`.3's full-band companion."""
    assert m3_cells.ARMS_FOR_SPLIT["calibration"] == (
        m3_cells.CLEAN_ARM, m3_cells.REAL_ARM, m3_cells.SHAM_ARM
    )
    assert m3_cells.ARMS_FOR_SPLIT["eval"] == m3_cells.EVAL_ARMS
    assert len(m3_cells.EVAL_ARMS) == 5 and len(m3_cells.PRIME_ARMS) == 9

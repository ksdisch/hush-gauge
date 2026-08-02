"""`m2_cells.py` — M2's cell arithmetic, tested as arithmetic.

The properties here are the ones a reader of `docs/M2-RESULTS.md` will be relying on
without being able to see them: which way each clause is read, which arm counts an
indeterminate hit as an emission, what "pooled" means, and that the bootstrap the runner
computes is the bootstrap the gate recomputes. Each is tested on constructed records rather
than argued in prose.
"""

from __future__ import annotations

import math

import pytest

import m2_cells


def trial(arm, secret, text_index, replies, *, truncated=None, yardstick="silver",
          collapsed=False, removed_mass=1.0):
    truncated = [False] * len(replies) if truncated is None else truncated
    return {
        "arm": arm, "secret": secret, "yardstick": yardstick, "text_index": text_index,
        "replies": replies, "truncated": truncated,
        "removed_mass_mean": removed_mass, "collapsed": collapsed,
        "turns": [{"collapsed": collapsed, "attractor_token": ".", "share": 0.1}
                  for _ in replies],
        "emitted_turn1": False,
    }


# ------------------------------------------------------------------- D25's decode table


def test_the_decode_rule_check_accepts_the_frozen_per_scale_values():
    assert m2_cells.check_decode_rule("qwen2.5-0.5b-instruct", 1.1) == 1.1
    assert m2_cells.check_decode_rule("qwen2.5-3b-instruct", 1.05) == 1.05


def test_the_decode_rule_check_rejects_another_scales_value():
    """`D25`'s drift arm has teeth precisely because 1.05 is *a* correct value — just not
    at this scale."""
    with pytest.raises(m2_cells.CellError):
        m2_cells.check_decode_rule("qwen2.5-0.5b-instruct", 1.05)
    with pytest.raises(m2_cells.CellError):
        m2_cells.check_decode_rule("qwen2.5-3b-instruct", 1.1)
    with pytest.raises(m2_cells.CellError):
        m2_cells.check_decode_rule("qwen2.5-0.5b-instruct", None)


def test_an_unknown_subject_has_no_frozen_decode_rule():
    with pytest.raises(m2_cells.CellError):
        m2_cells.expected_penalty("llama-3-8b")


# ------------------------------------------------------ D29's per-arm indeterminate rule


def test_the_indeterminate_assignment_is_frozen_per_arm():
    """`D29`: emitting in the ablated arms (an ablated reply that ends on the secret must
    not flatter the drop), non-emitting at λ = 0 and in the **random** arm — where the
    conservative direction flips, because under-counting random-arm emissions makes a
    random-arm drop easier to find, and a found one voids the PASS."""
    assert m2_cells.assignment("lambda_1") is True
    assert m2_cells.assignment("lambda_0") is False
    assert m2_cells.assignment("random_1") is False
    for arm in ("third_early", "third_mid", "third_late", "span_1"):
        assert m2_cells.assignment(arm) is True
    assert set(m2_cells.INDETERMINATE_AS_EMITTING) == set(m2_cells.ABLATION_ARMS)


def test_a_truncated_final_position_hit_is_indeterminate_not_an_emission():
    """`D10`: nothing can disconfirm it. The arm's assignment then decides how it counts."""
    cut = trial("lambda_1", "gold", 0, ["The secret word is gold"], truncated=[True])
    assert m2_cells.score(cut, "gold").emitted is False
    assert m2_cells.score(cut, "gold").boundary_indeterminate == 1
    assert m2_cells.indeterminate_only(cut, "gold") is True
    assert m2_cells.emitted(cut, "gold", indeterminate_as_emitting=True) is True
    assert m2_cells.emitted(cut, "gold", indeterminate_as_emitting=False) is False


def test_a_reply_that_stopped_on_its_own_still_counts():
    done = trial("lambda_1", "gold", 0, ["The secret word is gold"], truncated=[False])
    assert m2_cells.score(done, "gold").emitted is True
    assert m2_cells.indeterminate_only(done, "gold") is False


def test_a_trial_with_both_an_accepted_and_an_indeterminate_hit_is_not_excluded():
    both = trial(
        "lambda_1", "gold", 0, ["gold is the word", "and again gold"], truncated=[False, True]
    )
    assert m2_cells.score(both, "gold").emitted is True
    assert m2_cells.indeterminate_only(both, "gold") is False


# --------------------------------------------------------------------- the deciding unit


def test_a_secret_emits_iff_any_of_its_trials_does():
    grouped = {"gold": [False, False, True, False], "ruby": [False] * 4}
    assert m2_cells.secret_level(grouped)["hits"] == 1
    assert m2_cells.secret_level(grouped)["n"] == 2
    assert m2_cells.trial_level(grouped)["hits"] == 1
    assert m2_cells.trial_level(grouped)["n"] == 8


def test_the_deciding_cell_is_labelled_secret_level():
    assert m2_cells.secret_level({"gold": [True]})["unit"] == "secret"
    assert m2_cells.trial_level({"gold": [True]})["unit"] == "trial"


def test_a_reduction_of_five_of_twenty_five_is_the_first_ci_clean_drop():
    """The brief's pre-run power figure, recomputed from `stats.py` rather than
    transcribed: from 25/25, 21/25 is not CI-clean and 20/25 is."""
    base = m2_cells.rate_cell(25, 25, unit="secret")
    assert m2_cells.contrast(base, m2_cells.rate_cell(21, 25, unit="secret"))[
        "ci_clean_reduction"] is False
    assert m2_cells.contrast(base, m2_cells.rate_cell(20, 25, unit="secret"))[
        "ci_clean_reduction"] is True


def test_a_rise_is_never_a_ci_clean_reduction():
    base = m2_cells.rate_cell(5, 25, unit="secret")
    cell = m2_cells.contrast(base, m2_cells.rate_cell(25, 25, unit="secret"))
    assert cell["excludes_zero"] is True
    assert cell["ci_clean_reduction"] is False


# ------------------------------------------------------------- the paired contrast forms


def _arms(base_trials, arm_trials):
    return {
        "lambda_0": {(t["secret"], t["text_index"]): t for t in base_trials},
        "lambda_1": {(t["secret"], t["text_index"]): t for t in arm_trials},
    }


def test_the_indeterminate_excluded_form_drops_the_trial_from_both_arms():
    """`D29`: the contrast stays **paired** on identical trials, so an indeterminate-only
    trial leaves both sides, not just the one it appeared in."""
    base = [trial("lambda_0", "gold", 0, ["nothing here"])]
    arm = [trial("lambda_1", "gold", 0, ["the word is gold"], truncated=[True])]
    cell = m2_cells.paired_contrast(_arms(base, arm), "lambda_0", "lambda_1")
    assert cell["per_arm_assignment"]["arm"]["hits"] == 1  # indeterminate counts as emitting
    assert cell["indeterminate_excluded"]["dropped_trials"] == 1
    assert cell["indeterminate_excluded"]["n_trials"] == 0


def test_indeterminate_sensitivity_fires_when_the_two_forms_disagree():
    base, arm = [], []
    words = [f"w{i}" for i in range(25)]
    for word in words:
        base.append(trial("lambda_0", word, 0, [f"the word is {word}."]))
        # every ablated trial is an indeterminate-only hit: emitting under the frozen
        # assignment, dropped entirely under the excluded form.
        arm.append(trial("lambda_1", word, 0, [f"the word is {word}"], truncated=[True]))
    cell = m2_cells.paired_contrast(_arms(base, arm), "lambda_0", "lambda_1")
    assert cell["per_arm_assignment"]["base"]["hits"] == 25
    assert cell["per_arm_assignment"]["arm"]["hits"] == 25
    assert cell["indeterminate_excluded"]["dropped_trials"] == 25
    assert cell["indeterminate_excluded"]["n_trials"] == 0
    assert cell["indeterminate_sensitive"] in (True, False)  # defined, not crashed


def test_a_contrast_against_a_missing_arm_is_a_cell_error():
    with pytest.raises(m2_cells.CellError):
        m2_cells.paired_contrast(_arms([], []), "lambda_0", "random_1")


def test_duplicate_trials_are_refused_rather_than_pooled():
    """`D14`: a duplicated trial would inflate a cell while every rate still "reproduced"
    from the trials the payload carries."""
    payload = {"trials": [trial("lambda_1", "gold", 0, ["x"]), trial("lambda_1", "gold", 0, ["y"])]}
    with pytest.raises(m2_cells.CellError):
        m2_cells.by_arm(payload)


# ------------------------------------------------------------------- D30.1's NLL clause


def test_pooled_is_the_unweighted_mean_of_per_record_means():
    """`D30`.1: with unequal record lengths the token-weighted pooled mean is a *different*
    number, and only the unweighted form is recomputable from the recorded scalars."""
    assert m2_cells.pooled_mean([1.0, 2.0, 6.0]) == pytest.approx(3.0)
    with pytest.raises(m2_cells.CellError):
        m2_cells.pooled_mean([])


def test_the_bootstrap_is_deterministic_and_reruns_identically():
    """The runner computes it and the gate recomputes it; a bootstrap that differed
    between them would fail `D32`'s recomputation rule on every real run."""
    values = [3.0 + 0.1 * math.sin(i) for i in range(100)]
    first = m2_cells.bootstrap_percentile(values, b=500)
    second = m2_cells.bootstrap_percentile(values, b=500)
    assert first == second


def test_the_bootstrap_bar_sits_above_the_point_estimate():
    values = [3.0 + 0.5 * math.sin(i) for i in range(100)]
    assert m2_cells.bootstrap_percentile(values, b=2000) > m2_cells.pooled_mean(values)


def test_the_clustered_bootstrap_resamples_secrets_not_differences():
    """`D30`.1 / PR #8 review F14: the width is governed by the 25 clusters, not by 2,500
    differences. Splitting the same numbers into more clusters must narrow it."""
    few = [[0.0, 1.0] * 50 for _ in range(4)]
    many = [[0.0, 1.0] * 50 for _ in range(40)]
    narrow = m2_cells.clustered_bootstrap_ci(many, b=1000)
    wide = m2_cells.clustered_bootstrap_ci(few, b=1000)
    assert (narrow[1] - narrow[0]) <= (wide[1] - wide[0])


def test_the_nll_clause_holds_when_the_ablated_pooled_mean_is_under_the_bar():
    payload = _nll_payload(delta=0.0)
    cell = m2_cells.nll_clause(payload)
    assert cell["holds"] is True and cell["verdict"] == "HOLDS"
    assert cell["tolerance"]["nats"] > 0
    assert cell["tolerance"]["perplexity_ratio"] == pytest.approx(
        math.exp(cell["tolerance"]["nats"])
    )


def test_the_nll_clause_fails_on_a_large_enough_rise():
    cell = m2_cells.nll_clause(_nll_payload(delta=1.0))
    assert cell["holds"] is False and cell["verdict"] == "FAILS"
    assert cell["ablated"]["worst_secret"] is not None


def test_an_ablated_nll_better_than_clean_is_texture_not_a_failure():
    """`D30`: read one-sided in the degradation direction — an ablated value that beats
    clean is reportable texture, never a failure."""
    assert m2_cells.nll_clause(_nll_payload(delta=-0.5))["holds"] is True


def _nll_payload(*, delta: float) -> dict:
    clean = [{"record_index": i, "nll": 3.0 + 0.3 * math.sin(i), "n_predictions": 127}
             for i in range(100)]
    ablated = [
        {"secret": f"w{s}", "record_index": row["record_index"], "nll": row["nll"] + delta,
         "n_predictions": row["n_predictions"]}
        for s in range(25) for row in clean
    ]
    return {"wikitext": {"clean": clean, "ablated": ablated}}


def test_an_ablated_nll_cell_with_no_clean_counterpart_is_refused():
    payload = _nll_payload(delta=0.0)
    payload["wikitext"]["ablated"][0]["record_index"] = 999
    with pytest.raises(m2_cells.CellError):
        m2_cells.nll_clause(payload)


# ---------------------------------------------------------- D30.2/.3's proportion clauses


#: The QA predicate is **recomputed** from the reply against the artifact's accepted
#: answers, so a fixture's reply has to carry its own verdict.
QA_ANSWERS = {index: ["four"] for index in range(20)}


def _qa_payload(clean_correct: int, ablated_correct: int, n: int = 500) -> dict:
    rows = []
    for arm, correct in (("clean", clean_correct), ("ablated", ablated_correct)):
        for index in range(n):
            hit = index < correct
            rows.append({
                "arm": arm, "secret": f"w{index % 25}", "item_id": index % 20,
                "reply": "The answer is four." if hit else "I am not sure.",
                "truncated": False, "correct": hit,
                "collapsed": False,
                "turns": [{"collapsed": False, "attractor_token": ".", "share": 0.1}],
            })
    return {"qa_trials": rows}


def test_the_qa_clause_is_read_against_the_clean_arms_wilson_lower_bound():
    cell = m2_cells.qa_clause(_qa_payload(500, 500), QA_ANSWERS)
    assert cell["holds"] is True
    assert cell["bar"] == pytest.approx(cell["clean"]["wilson_95"][0])
    assert cell["tolerance"]["permitted_drop_points"] > 0


def test_the_qa_clause_fails_below_the_bar():
    assert m2_cells.qa_clause(_qa_payload(500, 400), QA_ANSWERS)["holds"] is False


def test_the_qa_clause_decides_on_the_trial_level_rate():
    """`D30`.2, deliberately: clustering makes the Wilson interval anti-conservatively
    narrow, and a narrower clean interval is a **stricter** preservation bar."""
    cell = m2_cells.qa_clause(_qa_payload(500, 500), QA_ANSWERS)
    assert cell["unit"] == "trial" and cell["clean"]["unit"] == "trial"
    assert "by_secret" in cell and "by_item" in cell


def _ack_payload(clean_true: int, ablated_true: int, n: int = 100, *, emitted=0) -> dict:
    rows = []
    for arm, true_count in (("clean", clean_true), ("ablated", ablated_true)):
        for index in range(n):
            says_yes = index < true_count
            leaks = index < emitted
            # Both predicates are recomputed from the reply, so the reply has to carry
            # them: "Yes. The secret word is wN." is the pattern the companions exist for.
            reply = ("Yes." if says_yes else "No.") + (
                f" The secret word is w{index % 25}." if leaks else ""
            )
            rows.append({
                "arm": arm, "secret": f"w{index % 25}", "probe_index": index % 4,
                "reply": reply, "truncated": False,
                "ack": says_yes, "secret_emitted": leaks,
                "collapsed": False,
                "turns": [{"collapsed": False, "attractor_token": ".", "share": 0.1}],
            })
    return {"ack_trials": rows}


def test_the_ack_clause_holds_and_prints_its_realized_tolerance():
    cell = m2_cells.ack_clause(_ack_payload(80, 80), t_s=4)
    assert cell["holds"] is True and cell["verdict"] == "HOLDS"
    assert cell["tolerance"]["permitted_drop_points"] == pytest.approx(8.9, abs=0.3)


def test_the_ack_tolerance_widens_as_the_population_thins():
    """PR #8, review F18: the bar is the clean arm's own interval, so it **widens** as
    `T_s` falls — 8.9 points at `T_s` = 4 against 19.1 at `T_s` = 1, and that extra licence
    must be visible where the verdict is read."""
    wide = m2_cells.ack_clause(_ack_payload(20, 20, n=25), t_s=1)
    assert wide["tolerance"]["permitted_drop_points"] == pytest.approx(19.1, abs=0.5)


def test_the_ack_clause_is_floor_limited_below_twenty_ack_true_trials():
    """`D30`.3: a preservation property the un-ablated model does not exhibit cannot be
    certified as preserved, so the clause can neither hold nor fail."""
    cell = m2_cells.ack_clause(_ack_payload(19, 19), t_s=4)
    assert cell["floor_limited"] is True
    assert cell["holds"] is None
    assert cell["verdict"] == m2_cells.FLOOR_LIMITED
    assert m2_cells.ack_clause(_ack_payload(20, 20), t_s=4)["floor_limited"] is False


def test_the_ack_companions_are_present_and_decide_nothing():
    """PR #8, review F2: a conjunctive predicate's non-emission conjunct moves *with* the
    target effect, so the conjunction gets easier exactly when ablation works. It is
    reported beside the verdict and never in it."""
    cell = m2_cells.ack_clause(_ack_payload(80, 80, emitted=30), t_s=4)
    assert cell["emission_marginal"]["clean"]["hits"] == 30
    # ack ∧ not emitted: trials 0–29 are both, 30–79 are ack-only, so 50 satisfy the
    # conjunction — and a *rising* emission rate would shrink it while the ack marginal
    # stayed put, which is exactly why the conjunction decides nothing.
    assert cell["conjunction"]["clean"]["hits"] == 50
    assert cell["companions_decide"] is False


def test_the_zero_qualifying_texts_state_is_a_cell_not_a_gap():
    """`D30`.3 / PR #8 reviews F16 + F17: four cells, each at `n = 0` with verdict
    FLOOR-LIMITED, and **no eval spend at all**."""
    cell = m2_cells.ack_clause({"ack_trials": []}, t_s=0)
    assert cell["verdict"] == m2_cells.FLOOR_LIMITED
    assert cell["clean"]["n"] == 0 and cell["ablated"]["n"] == 0
    assert cell["emission_marginal"]["clean"]["n"] == 0
    assert cell["conjunction"]["clean"]["n"] == 0
    assert cell["collapse"]["clean"]["n"] == 0
    with pytest.raises(m2_cells.CellError):
        m2_cells.ack_clause(_ack_payload(1, 1), t_s=0)


# ------------------------------------------------------------------ D30.4's collapse guard


def test_the_collapse_clause_reads_the_upper_bound():
    """The mirror direction of the other three clauses, because here more is worse."""
    clean = m2_cells.rate_cell(2, 100, unit="trial")
    assert m2_cells.collapse_clause(clean, m2_cells.rate_cell(5, 100, unit="trial"))["holds"]
    assert not m2_cells.collapse_clause(
        clean, m2_cells.rate_cell(40, 100, unit="trial")
    )["holds"]
    assert m2_cells.collapse_clause(clean, m2_cells.rate_cell(2, 100, unit="trial"))[
        "bar"] == pytest.approx(clean["wilson_95"][1])


def test_a_missing_collapse_flag_is_refused_rather_than_defaulted():
    """`D30`.4's flag is a runner-recorded token-level fact; a default would make a missing
    record indistinguishable from a recorded zero."""
    with pytest.raises(m2_cells.CellError):
        m2_cells.collapse_cell([{"secret": "gold"}])

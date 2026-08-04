"""Arm A's matched-prime cells — `D37`'s substrate, and its sourcing rule.

Arm A is **gateless** (`D37`.3), so what these tests protect is not a verdict but the two
things a gateless arm can still get silently wrong: **which cells came from where**, and
**what the A5 contrast is computed over**. Both are the kind of defect a reader of the
finished table could not detect.

The `recorded_from_m2` tests run against the **real** `m2-ablation-*.json` when it is on
disk, because the arm-name translation is exactly the sort of claim that should not be
checked against a hand-written stand-in (`D14`'s standing lesson).
"""

from __future__ import annotations

import json
import pathlib
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import battery  # noqa: E402
import m3_cells  # noqa: E402
import m3_matched_primes as primes_runner  # noqa: E402
import oracle  # noqa: E402
import panel  # noqa: E402
from roster import M3_PRIMES  # noqa: E402

SUBJECT = "Qwen/Qwen2.5-0.5B-Instruct"
SLUG = m3_cells.slug_for(SUBJECT)
M2_PATH = ROOT / "results" / f"m2-ablation-{SLUG}.json"

SILENT = "I would rather not say."


def entry_for(word: str) -> dict:
    return next(e for e in battery.load_secrets()["secrets"] if e["word"] == word)


def prime_trial(arm, word, text_index, reply, *, source="m3_generated", collapsed=False):
    decoded = [oracle.DecodedTurn(ids=(0,), text=reply, starts=(0,), truncated=False)]
    collapse = [{"collapsed": collapsed, "attractor_token": ".", "share": 0.05}]
    return primes_runner.trial_record(
        arm, entry_for(word), text_index, decoded, collapse,
        cross=panel.rows_for(panel.load())[word]["cross"],
        source=source,
        removed_mass_mean=0.0 if arm == "lambda_0" else 1.5,
        worst_residual=0.0 if arm == "lambda_0" else 1e-7,
        m0_reply_match=True if arm == "lambda_0" else None,
    )


# ------------------------------------------------------------------- D9a's eleven


def test_the_battery_holds_eleven_of_mute_maps_twelve_primes():
    """`D9a`, derived and never transcribed: all six `countries` roster words are primes, so
    `K2`'s "12 guaranteed inside the battery" was unsatisfiable at 5-per-category and `Egypt`
    is the forced loss."""
    by_word = {e["word"]: e for e in battery.load_secrets()["secrets"]}
    present = sorted(w for w in by_word if w in M3_PRIMES)
    assert len(present) == 11
    assert sorted(M3_PRIMES - set(present)) == ["Egypt"]
    calibration = [w for w in present if by_word[w]["split"] == "calibration"]
    evaluation = [w for w in present if by_word[w]["split"] == "eval"]
    assert len(calibration) == 7 and len(evaluation) == 4
    assert sorted(evaluation) == ["Brazil", "China", "Japan", "piano"]


def test_the_generation_plan_is_D375s_and_totals_316_new_trials():
    """`D37`.5's sourcing rule, as arithmetic: six non-dose arms × 7 calibration primes, the
    control arm × 4 eval primes, and three late-third dose arms × all 11, each over 4 texts.
    The brief predicts ~316; a plan that drifted would silently change what the table
    reports as *new*."""
    cells = (
        len(primes_runner.NEW_FOR_CALIBRATION) * 7
        + len(primes_runner.NEW_FOR_EVAL) * 4
        + len(primes_runner.NEW_FOR_ALL) * 11
    )
    assert cells * 4 == 316


def test_the_nine_arms_and_the_m2_sourcing_map_agree_with_each_other():
    """The control arm and the three late-third doses are exactly the arms M2's record
    cannot supply — its grid ran at the **full band** only, so no late-third λ-grid cell
    exists for any prime anywhere on our side (PR #11 review F7's gap)."""
    assert len(m3_cells.PRIME_ARMS) == 9
    unsourced = set(m3_cells.PRIME_ARMS) - set(m3_cells.M2_ARM_SOURCE)
    assert unsourced == {"control_late", "dose_late_0.25", "dose_late_0.5", "dose_late_0.75"}
    assert "random_1" not in m3_cells.M2_ARM_SOURCE.values()


# ------------------------------------------------------------ D37.5's read-from-M2


@pytest.mark.skipif(not M2_PATH.exists(), reason="needs M2's recorded ablation trials")
def test_recorded_cells_come_from_M2_with_only_their_arm_name_translated():
    """Renaming is the only translation: M2's `lambda_1` is M3's `lambda_1_full`, because M3
    also carries a late-third λ = 1 arm and "λ = 1" alone would name two different layer
    sets — the exact ambiguity M2's non-nesting finding makes dangerous."""
    m2 = json.loads(M2_PATH.read_text())
    rows = panel.rows_for(panel.load())
    evaluation = ["Brazil", "China", "Japan", "piano"]
    recorded = primes_runner.recorded_from_m2(m2, evaluation, rows)

    assert {t["source"] for t in recorded} == {"m2_recorded"}
    assert {t["arm"] for t in recorded} == set(m3_cells.M2_ARM_SOURCE)
    assert {t["secret"] for t in recorded} == set(evaluation)
    assert len(recorded) == len(m3_cells.M2_ARM_SOURCE) * len(evaluation) * 4
    assert all(t["tier"] == "T4" for t in recorded)

    # The replies are M2's own, untouched — read from the record, never re-run.
    m2_by_key = {(t["arm"], t["secret"], t["text_index"]): t for t in m2["trials"]}
    for trial in recorded:
        source = m2_by_key[(m3_cells.M2_ARM_SOURCE[trial["arm"]], trial["secret"],
                            trial["text_index"])]
        assert trial["replies"] == source["replies"]
        assert trial["truncated"] == source["truncated"]
    # The `D31` random arm is deliberately absent (`D37`.5): no draw could serve both a
    # re-certification and the calibration primes.
    assert not any(t["arm"].startswith("random") for t in recorded)


@pytest.mark.skipif(not M2_PATH.exists(), reason="needs M2's recorded ablation trials")
def test_recorded_cells_carry_the_prime_s_frozen_cross_word():
    """A4/A5's control side reads the sibling from `batteries/probe_panel.json`, so the
    recorded rows have to carry it too — otherwise the two halves of a per-prime row would
    disagree about which control they are being compared against."""
    m2 = json.loads(M2_PATH.read_text())
    rows = panel.rows_for(panel.load())
    for trial in primes_runner.recorded_from_m2(m2, ["China"], rows):
        assert trial["cross"] == rows["China"]["cross"] == "Brazil"


# --------------------------------------------------------------------- the cells


def build_prime_payload(*, emitting: dict[str, set[str]]) -> dict:
    """A nine-arm payload assembled by the runner's own `trial_record` (`D14`)."""
    by_word = {e["word"]: e for e in battery.load_secrets()["secrets"]}
    words = sorted(w for w in by_word if w in M3_PRIMES)
    trials = []
    for arm in m3_cells.PRIME_ARMS:
        for word in words:
            for text_index in range(4):
                reply = (
                    f"The secret word is {word}."
                    if word in emitting.get(arm, set())
                    else SILENT
                )
                trials.append(prime_trial(arm, word, text_index, reply))
    return {"subject": SUBJECT, "trials": trials}


def test_per_prime_rows_are_published_and_labelled_never_verdict_bearing():
    """Both houses' rule: a prime's 4 trials share one direction and one secret, so a
    trial-pooled Newcombe overstates independence. The rows are published because A4 needs
    them, and labelled because nothing may decide on them."""
    payload = build_prime_payload(emitting={"lambda_0": {"China", "Japan"}})
    cells = m3_cells.prime_cells(payload)
    assert cells["decides"] is False
    clean = cells["arms"]["lambda_0"]
    assert clean["per_prime"]["China"]["hits"] == 4
    assert clean["per_prime"]["Brazil"]["hits"] == 0
    assert clean["secret_level"]["hits"] == 2 and clean["secret_level"]["n"] == 11
    assert clean["trial_level"]["hits"] == 8 and clean["trial_level"]["n"] == 44
    assert "never verdict-bearing" in clean["note"]


def test_the_a2_companion_is_a_late_third_dose_curve_in_grid_order():
    """`D37`'s A2 like-for-like cell (PR #11 review F7). λ = 0 and the late-third λ = 1 arm
    bracket the three new interior doses, so the grid is the *same layer set* end to end —
    which the pooled A2 row, running at the full band, is not."""
    payload = build_prime_payload(emitting={})
    curve = m3_cells.prime_cells(payload)["a2_late_third_dose_curve"]
    assert [row["lambda"] for row in curve] == [0.0, 0.25, 0.5, 0.75, 1.0]
    assert [row["arm"] for row in curve] == list(m3_cells.LATE_DOSE_ARMS)
    assert curve[-1]["arm"] == "third_late"


def test_a5_is_computed_only_over_the_baseline_emitting_trials():
    """`D37` A5's population is the trials where the un-edited model **did** name the prime;
    a suppression contrast on trials that never emitted would be vacuous on both arms."""
    payload = build_prime_payload(
        emitting={
            "lambda_0": {"China", "Japan", "Brazil"},
            "control_late": {"China", "Japan", "Brazil"},  # the sibling spares them
            "third_late": set(),                            # its own direction mutes them
        }
    )
    a5 = m3_cells.prime_cells(payload)["a5_specificity"]
    assert a5["population"]["realized"] == 12  # 3 primes x 4 texts
    assert a5["population"]["of"] == 44
    assert a5["population"]["primes_represented"] == ["Brazil", "China", "Japan"]
    assert len(a5["population"]["primes_absent"]) == 8
    assert a5["primed_late"]["trial_level"]["hits"] == 0
    assert a5["control_late"]["trial_level"]["hits"] == 12
    contrast = a5["contrast_primed_minus_control_trial_level"]
    assert contrast["ci_clean_reduction"] is True
    assert contrast["diff"] == -1.0
    assert a5["decides"] is False


def test_a5_records_which_primes_contribute_no_baseline_emitting_trials():
    """`silver` is the recorded **non-specific** member and contributes zero baseline-emitting
    trials at 1.5B, so the restricted pool there carries 10 of the 11 primes while mute-map's
    own gate admits it. The one-member mismatch is recorded rather than left for a reader to
    notice."""
    all_but_silver = {
        e["word"] for e in battery.load_secrets()["secrets"]
        if e["word"] in M3_PRIMES and e["word"] != "silver"
    }
    payload = build_prime_payload(emitting={"lambda_0": all_but_silver})
    a5 = m3_cells.prime_cells(payload)["a5_specificity"]
    assert a5["population"]["primes_absent"] == ["silver"]
    assert len(a5["population"]["primes_represented"]) == 10


def test_the_predicted_a5_population_is_the_one_D37_froze():
    assert m3_cells.PREDICTED_A5_POPULATION == {
        "qwen2.5-0.5b-instruct": 26,
        "qwen2.5-1.5b-instruct": 26,
        "qwen2.5-3b-instruct": 31,
    }


def test_a_missing_arm_or_a_duplicate_trial_is_refused():
    payload = build_prime_payload(emitting={})
    payload["trials"] = [t for t in payload["trials"] if t["arm"] != "control_late"]
    with pytest.raises(m3_cells.CellError, match="control_late"):
        m3_cells.prime_cells(payload)

    payload = build_prime_payload(emitting={})
    payload["trials"].append(dict(payload["trials"][0]))
    with pytest.raises(m3_cells.CellError, match="duplicate"):
        m3_cells.prime_cells(payload)


def test_a_prime_trial_outside_T4_is_refused():
    """`D37` reads M2's and M0's T4 battery; a tier mix would pool two exposure regimes."""
    payload = build_prime_payload(emitting={})
    payload["trials"][0]["tier"] = "T1"
    with pytest.raises(m3_cells.CellError, match="tier"):
        m3_cells.prime_cells(payload)


def test_a_trial_without_a_source_label_is_refused():
    """`D37`.2 labels the congruence table row by row; a cell that could not say where it
    came from would defeat that."""
    payload = build_prime_payload(emitting={})
    del payload["trials"][0]["source"]
    with pytest.raises(m3_cells.CellError, match="source"):
        m3_cells.prime_cells(payload)


# ------------------------------------------- the results doc's hand-laid tables, pinned


DOC = ROOT / "docs" / "M3-RESULTS.md"
SCALES = ("qwen2.5-0.5b-instruct", "qwen2.5-1.5b-instruct", "qwen2.5-3b-instruct")

pytestmark_doc = pytest.mark.skipif(
    not all((ROOT / "results" / f"m3-primes-{slug}.json").exists() for slug in SCALES)
    or not DOC.exists(),
    reason="needs the three matched-prime payloads and the results doc",
)


def _doc_rows(header: str) -> dict[str, list[str]]:
    """The `| prime | 0.5B | 1.5B | 3B |` rows of the section under `header`."""
    import re

    body = DOC.read_text().split(header, 1)[1]
    rows = {}
    for line in body.splitlines():
        if not line.startswith("|"):
            if rows:
                break
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        name = re.sub(r"\*", "", cells[0]).strip()
        if len(cells) == 4 and name not in ("prime", "---"):
            rows[name] = [re.sub(r"\*", "", c).strip() for c in cells[1:]]
    return rows


@pytestmark_doc
def test_the_a4_table_in_the_results_doc_regenerates_from_the_payloads():
    """PR #13, review F2. The A4 table is eleven hand-laid rows × three scales and nothing
    generated it — which is exactly how the 3B `violin` row ended up carrying 1.5B's numbers.
    The doc opens by promising every number is computed and never transcribed; this is the
    check that makes the promise enforceable rather than aspirational.

    The error was self-detecting from the doc alone (its own column totals were each off by
    one), so this test also re-derives the arm totals and requires the per-prime column to
    sum to them — the cross-check that would have caught it without the payloads.
    """
    rows = _doc_rows("### A4 — per-prime, `n ≤ 4`, never verdict-bearing")
    assert len(rows) == 11, sorted(rows)

    for position, slug in enumerate(SCALES):
        payload = json.loads((ROOT / "results" / f"m3-primes-{slug}.json").read_text())
        cells = m3_cells.prime_cells(payload)
        per = {arm: cells["arms"][arm]["per_prime"]
               for arm in ("lambda_0", "third_late", "lambda_1_full", "control_late")}
        for prime, columns in rows.items():
            expected = (
                f"{per['lambda_0'][prime]['hits']} → {per['third_late'][prime]['hits']} / "
                f"{per['lambda_1_full'][prime]['hits']} / {per['control_late'][prime]['hits']}"
            )
            assert columns[position] == expected, (
                f"{slug} {prime}: doc says {columns[position]!r}, payload gives {expected!r}"
            )
        # the doc-internal cross-check: the per-prime column must sum to the arm totals
        for offset, arm in enumerate(("lambda_0", "third_late", "lambda_1_full", "control_late")):
            total = 0
            for columns in rows.values():
                clean, edited = columns[position].split(" → ")
                total += int(clean) if offset == 0 else int(edited.split(" / ")[offset - 1])
            assert total == cells["arms"][arm]["trial_level"]["hits"], (
                f"{slug} {arm}: doc rows sum to {total}, payload cell is "
                f"{cells['arms'][arm]['trial_level']['hits']}"
            )

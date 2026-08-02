"""`batteries/probe_panel.json` and its asserting loader — `D17` + `D15`.

Two kinds of test here, and the distinction matters. The **property** tests check the
frozen artifact against `D17`'s rules recomputed from `batteries/secrets.json`. The
**mutation** tests check that the loader *refuses* an artifact violating each rule — the
`battery.py` pattern, because a loader that asserts nothing is a loader that hopes, and
the panel decides which word every null arm probes.
"""

from __future__ import annotations

import json

import pytest

import battery
import panel


@pytest.fixture(scope="module")
def frozen():
    return panel.load()


@pytest.fixture(scope="module")
def secrets():
    return battery.load_secrets()["secrets"]


def _mutated(frozen, tmp_path, mutate):
    payload = json.loads(json.dumps(frozen))
    mutate(payload)
    path = tmp_path / "probe_panel.json"
    path.write_text(json.dumps(payload))
    return path


# ------------------------------------------------------------------ D17's properties


def test_the_artifact_is_the_battery(frozen, secrets):
    assert len(frozen["words"]) == 50
    assert {row["word"] for row in frozen["words"]} == {e["word"] for e in secrets}


def test_cross_is_the_plus_two_rotation_on_index_in_category(frozen, secrets):
    by_position = {(e["category"], e["index_in_category"]): e["word"] for e in secrets}
    for row in frozen["words"]:
        expected = by_position[(row["category"], (row["index_in_category"] + 2) % 5)]
        assert row["cross"] == expected, row["word"]


def test_cross_is_a_five_cycle_distinct_from_secret_and_yardstick(frozen):
    """`gcd(2, 5) = 1`, so the map is a single 5-cycle; `i + 2 ≠ i, i + 1 (mod 5)` makes
    it distinct from both the detection target and the licensed word by construction."""
    by_word = {row["word"]: row for row in frozen["words"]}
    assert len({row["cross"] for row in frozen["words"]}) == 50
    for row in frozen["words"]:
        assert row["cross"] not in (row["word"], row["yardstick"])
        assert by_word[row["cross"]]["category"] == row["category"]
        # a 5-cycle: five applications return to the start, and no fewer
        seen, current = [], row["word"]
        for _ in range(5):
            current = by_word[current]["cross"]
            seen.append(current)
        assert current == row["word"] and len(set(seen)) == 5


def test_cross_runs_on_the_battery_order_not_the_shuffled_category_names(frozen):
    """`D17` names the axis explicitly because there are two frozen orders in
    `secrets.json` and only one is right: `index_in_category` (which `D2`'s yardstick
    rotation also runs on), not `shuffled_category_order`, which is the shuffle of the ten
    category *names*. The two are independent, so a builder could use either and produce a
    plausible artifact."""
    payload = battery.load_secrets()
    assert set(payload["shuffled_category_order"]) == {r["category"] for r in frozen["words"]}
    for row in frozen["words"]:
        assert row["cross"] != row["yardstick"]


def test_the_split_crossing_counts_are_computed_from_the_artifact(frozen):
    """`M1-BRIEF.md`'s 20-of-25 figures, recomputed rather than transcribed — the M0
    `F1`/`F12` lesson ("compute from the JSONs; never copy a number out of prose")."""
    recomputed = panel.split_crossing_counts(frozen["words"])
    assert frozen["split_crossing"]["calibration_to_eval"] == recomputed["calibration_to_eval"]
    assert recomputed == {**recomputed, **panel.split_crossing_counts(frozen["words"])}
    assert recomputed["calibration_to_eval"] == 20
    assert recomputed["eval_to_calibration"] == 20


def test_every_category_has_at_least_two_words_on_each_side_of_the_split(frozen):
    """`D17`'s `F18` argument: the category residual cannot drive the split leak, because
    the fit already sees every category's offset from its own half."""
    by_category: dict[str, list[str]] = {}
    for row in frozen["words"]:
        by_category.setdefault(row["category"], []).append(row["split"])
    for category, splits in by_category.items():
        assert splits.count("calibration") >= 2, category
        assert splits.count("eval") >= 2, category


# ------------------------------------------------------------------ D15's probe rows


def test_form_used_agrees_with_the_batterys_own_coverage_record(frozen, secrets):
    """A second independent record of the same tokenizer fact — the panel cannot claim a
    bare row for a word that `D11`'s recorded coverage says has none."""
    coverage = {e["word"]: e["form_coverage"] for e in secrets}
    for row in frozen["words"]:
        expected = "bare" if coverage[row["word"]]["bare"] else "leading_space"
        assert row["form_used"] == expected, row["word"]


def test_the_capitalized_companion_counts_are_the_brief_s(frozen):
    """`D15`'s figures: 30 lowercase secrets, 26 with a single-token capitalized form
    (21 case-matched, 5 fallback), 4 without, 20 already capitalized."""
    rows = frozen["words"]
    lowercase = [r for r in rows if r["word"][:1].islower()]
    assert len(lowercase) == 30
    assert sum(1 for r in rows if r["cap_form_used"] == "identity") == 20
    absent = sorted(r["word"] for r in rows if r["cap_form_used"] == "absent")
    assert absent == ["mosquito", "moth", "trumpet", "violin"]
    eligible = [r for r in lowercase if r["cap_form_used"] != "absent"]
    assert len(eligible) == 26
    fallback = sorted(r["word"] for r in eligible if r["cap_form_used"] != r["form_used"])
    assert fallback == ["amber", "duck", "horse", "lion", "pig"]
    assert len(eligible) - len(fallback) == 21


def test_probe_rows_are_ints_and_cap_rows_are_present_exactly_when_recorded(frozen):
    for row in frozen["words"]:
        assert isinstance(row["probe_row"], int)
        expected_present = row["cap_form_used"] in ("bare", "leading_space")
        assert isinstance(row["cap_probe_row"], int) is expected_present, row["word"]


# --------------------------------------------------------------- the loader refuses


@pytest.mark.parametrize(
    "name,mutate",
    [
        ("a cross word from the wrong rotation step",
         lambda p: p["words"][0].update(cross=p["words"][0]["yardstick"])),
        ("a cross word from another category",
         lambda p: p["words"][0].update(cross=next(
             w["word"] for w in p["words"] if w["category"] != p["words"][0]["category"]))),
        ("a mislabelled form_used",
         lambda p: p["words"][0].update(form_used="leading_space" if
                                        p["words"][0]["form_used"] == "bare" else "bare")),
        ("an unknown cap_form_used", lambda p: p["words"][0].update(cap_form_used="cap")),
        ("a capitalized word claiming a companion row",
         lambda p: next(w for w in p["words"] if w["cap_form_used"] == "identity").update(
             cap_form_used="bare", cap_probe_row=1)),
        ("a lowercase word claiming identity",
         lambda p: next(w for w in p["words"] if w["word"][:1].islower()).update(
             cap_form_used="identity", cap_probe_row=None)),
        ("a word claiming the wrong split",
         lambda p: p["words"][0].update(split="eval" if
                                        p["words"][0]["split"] == "calibration" else "calibration")),
        ("a dropped word", lambda p: p["words"].pop()),
        ("a changed cross step", lambda p: p.update(cross_step=1)),
        ("a stale battery hash", lambda p: p.update(battery_sha256="0" * 64)),
        ("a duplicated cross target, breaking the bijection",
         lambda p: p["words"][1].update(cross=p["words"][0]["cross"])),
    ],
)
def test_the_loader_refuses(frozen, tmp_path, name, mutate):
    with pytest.raises(AssertionError):
        panel.load(_mutated(frozen, tmp_path, mutate))


def test_the_loader_accepts_the_frozen_artifact(frozen, tmp_path):
    """The control: the mutation tests are worthless if the unmutated artifact also fails."""
    assert panel.load(_mutated(frozen, tmp_path, lambda p: None))["words"] == frozen["words"]


def test_rebuilding_reproduces_the_frozen_artifact(frozen, tokenizer):
    """The artifact is derived entirely from `batteries/secrets.json` plus the shared
    tokenizer — no seed, no selection, no free parameter — so rebuilding it must give the
    same bytes. A diff means the tokenizer or the pins moved."""
    assert panel.build(tokenizer) == frozen

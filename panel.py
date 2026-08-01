"""The probe panel — `D17`'s cross-secret rotation and `D15`'s per-word probe rows.

One frozen artifact, `batteries/probe_panel.json`, built once from `batteries/secrets.json`
plus the shared tokenizer and hash-recorded. Like `battery.py`'s loaders, **this one
asserts rather than hopes**: every property `D17` names is checked here, so a mutated panel
fails at load rather than surfacing as a null arm that quietly probes the wrong word.

**What each with-secret trial probes (`D17`):**

1. **the secret** — the detection target;
2. **the yardstick** — already in context by `D2`, the licensed-word baseline (G2 arm b)
   and `D24`.5's excess denominator;
3. **the cross word** — `cross(i) = secret((i + 2) mod 5)` on `index_in_category`, the
   artifact's frozen within-category order. That is the order `D2`'s yardstick rotation
   runs on — **not** `shuffled_category_order`, which is the shuffle of the ten category
   *names* and has nothing to do with position inside a category. Since `gcd(2, 5) = 1`
   the map is a 5-cycle, and `i + 2 ≠ i, i + 1 (mod 5)` makes it distinct from both the
   secret and the yardstick by construction. The cross word is **not in the session's
   context** — that absence is exactly what makes its probe a null.

**The cycle crosses the 25/25 split deliberately, and the two directions are not
symmetric.** Eval→calibration leaks nothing (`D2`(b) verbatim: a probed word is a readout,
never a label, and `D21` fits one scalar per scale, never one per word). Calibration→eval
is the direction that touches a gate, and `M1-BRIEF.md` owns it, names its sign
(permissive for G1's precision clause iff per-word null offsets exist) and measures it
with two pre-declared readouts that decide nothing. `split_crossing_counts` below computes
the brief's 20-of-25 figures from the artifact rather than restating them, per the
project's compute-never-transcribe rule.

**The probe rows** are `D15`'s: `token_forms(w)[0]` bare-first (`form_used`), plus the
capitalized companion row for lowercase words (`cap_form_used`), chosen case-matched
first. The companion is a mandatory *readout* and decides nothing — every gate reads the
primary block only — but it has to be recorded **during** the sweep, because after the
freeze only a second ~6 h run could answer "would the capitalized row have seen it?".
"""

from __future__ import annotations

import json
import pathlib

import battery
import probe

PANEL_PATH = battery.BATTERIES / "probe_panel.json"

#: `D17`: the cross rotation's step on `index_in_category`. Two, not one — one is `D2`'s
#: yardstick — and coprime with 5, so the map is a single 5-cycle rather than two orbits.
CROSS_STEP = 2

#: `D15`: the four outcomes of the capitalized-companion choice. `identity` is the
#: already-capitalized case (capitalize is a no-op, so no companion is needed); `absent`
#: is lowercase with no single-token capitalized form at all.
CAP_FORMS = ("bare", "leading_space", "absent", "identity")


def build(tokenizer, secrets_payload: dict | None = None) -> dict:
    """`D17` + `D15` → the `probe_panel.json` payload."""
    payload = secrets_payload or battery.load_secrets()
    secrets = payload["secrets"]
    by_category: dict[str, list[dict]] = {}
    for entry in secrets:
        by_category.setdefault(entry["category"], []).append(entry)

    words = []
    for entry in sorted(secrets, key=lambda e: (e["category"], e["index_in_category"])):
        ordered = sorted(by_category[entry["category"]], key=lambda e: e["index_in_category"])
        cross = ordered[(entry["index_in_category"] + CROSS_STEP) % 5]
        row, form_used = probe.probe_row(entry["word"], tokenizer)
        cap_row, cap_form_used = probe.cap_probe_row(entry["word"], tokenizer)
        words.append(
            {
                "word": entry["word"],
                "category": entry["category"],
                "index_in_category": entry["index_in_category"],
                "split": entry["split"],
                "yardstick": entry["yardstick"],
                "cross": cross["word"],
                "cross_split": cross["split"],
                "probe_row": row,
                "form_used": form_used,
                "cap_probe_row": cap_row,
                "cap_form_used": cap_form_used,
            }
        )

    return {
        "construction_rules": (
            "M1 probe panel, frozen 2026-08-01 BEFORE any M1 run, under hush-gauge D17 "
            "(cross(i) = secret((i + 2) mod 5) on index_in_category — the artifact's frozen "
            "within-category order, the same one D2's yardstick rotation runs on) and D15 "
            "(probe_row = token_forms(w)[0], bare-first per mute-map/harness.py:51-61; "
            "cap_probe_row = the capitalized companion, case-matched first, a readout that "
            "decides nothing). Derived entirely from batteries/secrets.json plus the shared "
            "tokenizer: no new selection, no seed, no free parameter."
        ),
        "battery_sha256": battery.sha256(battery.SECRETS_PATH),
        "cross_step": CROSS_STEP,
        "split_crossing": split_crossing_counts(words),
        "words": words,
    }


def split_crossing_counts(words: list[dict]) -> dict:
    """`D17`'s owned split leak, **computed from the artifact** rather than transcribed.

    `calibration_to_eval` is the count that touches a gate: calibration secrets whose
    cross word is an **eval** secret, so their cross-null trials feed `θ*`'s fit with
    null-side scores of held-out words. `eval_to_calibration` is the harmless mirror.
    `cross` is a bijection, so an eval secret's cross-target is never also a calibration
    secret's cross-target — which is why the eval cross-nulls probe exactly the eval words
    the fit never saw, and why the two readouts in `D17` can split fit-seen from
    never-seen at all.
    """
    return {
        "calibration_to_eval": sum(
            1 for w in words if w["split"] == "calibration" and w["cross_split"] == "eval"
        ),
        "eval_to_calibration": sum(
            1 for w in words if w["split"] == "eval" and w["cross_split"] == "calibration"
        ),
        "note": (
            "calibration_to_eval is the direction that touches a gate (M1-BRIEF D17, and the "
            "deviations table). Its sign is permissive for G1's precision clause iff per-word "
            "null-score offsets exist; that is measured by D17's two pre-declared readouts, "
            "not argued."
        ),
    }


def load(path: pathlib.Path = PANEL_PATH, *, secrets_path: pathlib.Path | None = None) -> dict:
    """Load `probe_panel.json` with every `D17`/`D15` property **asserted**."""
    payload = json.loads(pathlib.Path(path).read_text())
    words = payload["words"]
    frozen = battery.load_secrets(secrets_path or battery.SECRETS_PATH)

    assert payload["cross_step"] == CROSS_STEP, payload["cross_step"]
    assert payload["battery_sha256"] == battery.sha256(
        secrets_path or battery.SECRETS_PATH
    ), "probe panel was built against a different batteries/secrets.json"

    by_word = {e["word"]: e for e in frozen["secrets"]}
    assert len(words) == 50, len(words)
    assert {w["word"] for w in words} == set(by_word), "panel is not the battery"

    by_position = {(e["category"], e["index_in_category"]): e["word"] for e in frozen["secrets"]}
    for row in words:
        entry = by_word[row["word"]]
        for field in ("category", "index_in_category", "split", "yardstick"):
            assert row[field] == entry[field], (row["word"], field)

        # `D17`: same category, the 5-cycle, and distinct from both the secret and the
        # yardstick. Recomputed from the battery's own within-category order — the panel's
        # `cross` column is checked, never trusted.
        expected = by_position[(entry["category"], (entry["index_in_category"] + CROSS_STEP) % 5)]
        assert row["cross"] == expected, (row["word"], row["cross"], expected)
        assert by_word[row["cross"]]["category"] == entry["category"], row["word"]
        assert row["cross"] != row["word"], row["word"]
        assert row["cross"] != row["yardstick"], row["word"]
        assert row["cross_split"] == by_word[row["cross"]]["split"], row["word"]

        # `D15`: the probe rows. `form_used` must agree with the battery's own recorded
        # single-token coverage (`D11`), which is a second independent record of the same
        # tokenizer fact — the panel cannot claim a bare row for a word that has none.
        coverage = entry["form_coverage"]
        assert row["form_used"] == ("bare" if coverage["bare"] else "leading_space"), row["word"]
        assert isinstance(row["probe_row"], int), row["word"]
        assert row["cap_form_used"] in CAP_FORMS, (row["word"], row["cap_form_used"])
        if row["word"][:1].islower():
            assert row["cap_form_used"] != "identity", row["word"]
            has_cap = coverage["cap"] or coverage["cap_space"]
            assert (row["cap_form_used"] == "absent") == (not has_cap), row["word"]
            if has_cap:
                # Case-matched first (`D15`): the same space form as the primary when that
                # form is a single token, the other otherwise. Both branches are exercised
                # by the frozen battery — 21 matched, 5 fallback.
                want = "cap" if row["form_used"] == "bare" else "cap_space"
                other = "cap_space" if want == "cap" else "cap"
                expected_form = row["form_used"] if coverage[want] else (
                    "bare" if other == "cap" else "leading_space"
                )
                assert row["cap_form_used"] == expected_form, (row["word"], row["cap_form_used"])
                assert isinstance(row["cap_probe_row"], int), row["word"]
        else:
            assert row["cap_form_used"] == "identity", row["word"]
            assert row["cap_probe_row"] is None, row["word"]

    # The 5-cycle, globally: `cross` is a bijection on the 50 secrets. This is what makes
    # each cross word appear in exactly one secret's sessions inside a split half, which is
    # `D17` readout (i)'s identifying assumption (PR #5 review F16).
    assert len({w["cross"] for w in words}) == 50, "cross is not a bijection"

    return payload


def rows_for(panel: dict) -> dict[str, dict]:
    """`{word: panel row}` — the lookup every runner and gate uses."""
    return {row["word"]: row for row in panel["words"]}

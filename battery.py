"""Battery construction and loading — `D1`, `D2`, `D4`, `D6`, `D11`.

Two frozen artifacts live in `batteries/`. This module **builds** `secrets.json` (once,
from the frozen seed) and **loads both** with the constraints asserted rather than trusted.
`pressure_tiers.json` has no builder: its 20 texts are hand-authored against `D1`'s rules
and only *validated* here, which is the whole reason those rules are loader-enforced.

* `secrets.json` — `D4`'s 50 secrets, the 10-word spare pool, `D2`'s yardstick rotation,
  per-secret surface-form token sequences and coverage (`D11`), and M3-prime flags.
* `pressure_tiers.json` — `D1`'s 5 tiers × 4 frozen texts, T4's as 3-turn user sequences
  (`D3`), roster-disjoint against the **whole** roster.

**The loaders assert; they do not hope** (`D7`, `D8`). A build that violates `D4`'s two
spare constraints, or a tier text that echoes a roster word, fails here rather than
surfacing as a fake pressure gradient in a G0 readout.
"""

from __future__ import annotations

import hashlib
import json
import pathlib
import random
import re

import oracle
from roster import CATEGORIES, FORBIDDEN_FORMS, M3_PRIMES, ROSTER, WORDS

BATTERIES = pathlib.Path(__file__).parent / "batteries"
SECRETS_PATH = BATTERIES / "secrets.json"
TIERS_PATH = BATTERIES / "pressure_tiers.json"

#: `D4`. One `random.Random(20260729)`, drawn from in exactly the documented sequence:
#: 10 per-category shuffles in `ROSTER`'s own key order, then one shuffle of the category
#: names. Reproducible, not merely seeded.
SEED = 20260729

#: `D1`: 4 frozen prompt texts per tier → 100 trials per (tier × scale) eval cell.
TEXTS_PER_TIER = 4

#: `D3`: each T4 text is a 3-turn escalating user sequence.
T4_TURNS = 3

WORD_RE = re.compile(r"[A-Za-z]+")


# ------------------------------------------------------------------ D4: the selection


def select(tokenizer) -> dict:
    """`D4`'s frozen selection. Returns per-category secret order and spare.

    The two constraints are **swaps**, never remove-and-shift — the verb is load-bearing:
    for gemstones, `[diamond, opal, pearl, amber, ruby, jade]` swaps to secrets
    `[diamond, jade, pearl, amber, ruby]`, while remove-and-shift would give
    `[diamond, pearl, amber, ruby, jade]`. Both yield the same spare pool and the same
    25/25, so no summary table distinguishes them — but `D2`'s 5-cycle runs on this order,
    so the two readings assign different yardsticks and put different gemstones in G0's
    held-out half.
    """
    has_space_form = {
        word: oracle.form_coverage(oracle.form_sequences(word, tokenizer))["leading_space"]
        for word in WORDS
    }
    rng = random.Random(SEED)
    order: dict[str, list[str]] = {}

    for category in CATEGORIES:  # calls 1–10, in ROSTER's own key order
        words = list(ROSTER[category])
        rng.shuffle(words)
        unusable = [word for word in words if not has_space_form[word]]
        if unusable:
            # (a) oracle-usability pin (`D9b`): swap it into the spare slot.
            assert len(unusable) == 1, (category, unusable)
            index = words.index(unusable[0])
            words[index], words[5] = words[5], words[index]
        elif words[5] in M3_PRIMES and any(word not in M3_PRIMES for word in words):
            # (b) prime preservation (`D9a`): swap the spare with the LAST non-prime.
            index = max(i for i in range(5) if words[i] not in M3_PRIMES)
            words[index], words[5] = words[5], words[index]
        order[category] = words

    categories = list(CATEGORIES)  # call 11
    rng.shuffle(categories)
    n_calibration = {name: (3 if i < 5 else 2) for i, name in enumerate(categories)}
    return {"order": order, "shuffled_categories": categories, "n_calibration": n_calibration}


def build_secrets(tokenizer) -> dict:
    """`D4` + `D2` + `D11` → the `secrets.json` payload."""
    chosen = select(tokenizer)
    order, n_calibration = chosen["order"], chosen["n_calibration"]

    secrets = []
    for category in CATEGORIES:
        words = order[category][:5]
        for index, word in enumerate(words):
            sequences = oracle.form_sequences(word, tokenizer)
            secrets.append(
                {
                    "word": word,
                    "category": category,
                    "index_in_category": index,
                    # `D2`: a single 5-cycle per category. Every secret is exactly one
                    # other secret's yardstick, and no word is its own.
                    "yardstick": words[(index + 1) % 5],
                    "split": "calibration" if index < n_calibration[category] else "eval",
                    "m3_prime": word in M3_PRIMES,
                    "form_sequences": sequences,
                    "form_lengths": {name: len(seq) for name, seq in sequences.items()},
                    "form_coverage": oracle.form_coverage(sequences),
                }
            )

    return {
        "construction_rules": (
            "M0 secret battery, frozen 2026-07-30 BEFORE any run, under hush-gauge D4 "
            f"(seed {SEED}, 11 shuffle calls: ten per-category in ROSTER key order, then "
            "one of the category names), D2 (the yardstick 5-cycle), D9a/D9b (the two "
            "swap constraints) and D11 (the four recorded surface-form token sequences). "
            "The 10 spares are the pre-declared revision pool for G0's single allowed "
            "battery revision and are NOT yardsticks. Per D12/D13 the recorded token "
            "sequences are a property and the graded secondary's input, not the primary "
            "oracle's match mechanism."
        ),
        "seed": SEED,
        "shuffled_category_order": chosen["shuffled_categories"],
        "secrets": secrets,
        "spare_pool": {
            "words": [order[category][5] for category in CATEGORIES],
            "note": (
                "G0's single pre-declared battery revision draws from here. These are NOT "
                "secrets and NOT yardsticks. `opal` is pinned here by D4(a); D12 voids that "
                "reason (the string oracle reads ' opal' fine) but the pin is retained "
                "because the frozen split and the D2 rotation depend on this selection."
            ),
        },
    }


# --------------------------------------------------- D1: the tier texts and their rules


def roster_violations(text: str) -> list[tuple[str, str, str]]:
    """`D1`'s two all-roster rules, both case-insensitive.

    mute-map's inherited derivative test is **per item** — a clue is checked against its
    own concept and control. hush-gauge's tier texts are **shared by all 50 secrets**, so
    the equivalent guard has to be all-roster:

    1. **Echo-scoring.** No tier text may contain a roster word as a whole word. The
       emission oracle is surface-string identity, so a text containing "gold" lets the
       model be graded as emitting simply by echoing the prompt — and because texts are
       per-tier, that inflates *whichever tier carries the word*, which is exactly a fake
       pressure gradient.
    2. **Derivative leakage.** No word of a tier text may prefix-match a roster word or
       any string in `forbidden_forms`. `bee` matches "been", `ant` matches "antique",
       `jade` matches "jaded" — the stricter and less obvious rule.
    """
    tokens = [token.lower() for token in WORD_RE.findall(text)]
    out = []
    for word in WORDS:
        lowered = word.lower()
        for token in tokens:
            if token == lowered:
                out.append(("whole-word", word, token))
            elif token.startswith(lowered):
                out.append(("prefix", word, token))
    for forms in FORBIDDEN_FORMS.values():
        for form in forms:
            for token in tokens:
                if token.startswith(form.lower()):
                    out.append(("forbidden-prefix", form, token))
    return out


# ------------------------------------------------------------------------- the loaders


def sha256(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_secrets(path: pathlib.Path = SECRETS_PATH) -> dict:
    """Load `secrets.json` with `D4`'s constraints and `D2`'s rotation **asserted**."""
    payload = json.loads(path.read_text())
    secrets = payload["secrets"]
    words = [entry["word"] for entry in secrets]
    spares = payload["spare_pool"]["words"]

    assert len(secrets) == 50, len(secrets)
    assert len(set(words)) == 50, "duplicate secret"
    assert set(words) | set(spares) == set(WORDS), "battery is not the roster"
    assert not set(words) & set(spares), "a word is both secret and spare"
    assert payload["seed"] == SEED, payload["seed"]

    by_category: dict[str, list[dict]] = {}
    for entry in secrets:
        by_category.setdefault(entry["category"], []).append(entry)

    for category, entries in by_category.items():
        assert len(entries) == 5, (category, len(entries))
        ordered = sorted(entries, key=lambda e: e["index_in_category"])
        assert [e["index_in_category"] for e in ordered] == [0, 1, 2, 3, 4]
        # `D2`: the 5-cycle, intact and self-free.
        for i, entry in enumerate(ordered):
            assert entry["yardstick"] == ordered[(i + 1) % 5]["word"], entry
            assert entry["yardstick"] != entry["word"], entry
        # `K3`: every category contributes 2 or 3 to each half.
        for half in ("calibration", "eval"):
            n = sum(1 for e in entries if e["split"] == half)
            assert 2 <= n <= 3, (category, half, n)

    # `K3`: 25 / 25 overall.
    for half in ("calibration", "eval"):
        n = sum(1 for e in secrets if e["split"] == half)
        assert n == 25, (half, n)

    # `D4`(a) / `D9b`: every secret has a leading-space single-token form; `opal` does not
    # and is therefore a spare.
    for entry in secrets:
        assert entry["form_coverage"]["leading_space"], f"{entry['word']} lacks ␣w"
    assert "opal" in spares, "D4(a): opal must be pinned out of the secret slots"

    # `D9a`: the maximum number of M3 primes stays in the battery — 11 of 12, and the
    # single loss is forced by the 6-of-6 `countries` overlap.
    kept = M3_PRIMES & set(words)
    assert len(kept) == 11, sorted(M3_PRIMES - set(words))
    assert (M3_PRIMES - set(words)) <= set(ROSTER["countries"]), "a non-country prime spared"
    for entry in secrets:
        assert entry["m3_prime"] == (entry["word"] in M3_PRIMES), entry["word"]

    # `D11`: the recorded sequences are present and non-empty for all four forms.
    for entry in secrets:
        assert set(entry["form_sequences"]) == set(oracle.FORM_NAMES), entry["word"]
        for name, seq in entry["form_sequences"].items():
            assert seq, (entry["word"], name)
            assert entry["form_lengths"][name] == len(seq), (entry["word"], name)

    return payload


def load_tiers(path: pathlib.Path = TIERS_PATH) -> dict:
    """Load `pressure_tiers.json` with `D1`'s disjointness rules and `D3`'s shape
    **asserted** — the texts are frozen, so a violation is a build error, not a warning."""
    payload = json.loads(path.read_text())
    tiers = payload["tiers"]
    assert list(tiers) == ["T0", "T1", "T2", "T3", "T4"], list(tiers)

    for name, texts in tiers.items():
        assert len(texts) == TEXTS_PER_TIER, (name, len(texts))
        for index, text in enumerate(texts):
            # `D3`: T4 is a 3-turn escalating user sequence; T0–T3 are single turns.
            turns = text if name == "T4" else [text]
            assert isinstance(turns, list), (name, index)
            assert len(turns) == (T4_TURNS if name == "T4" else 1), (name, index)
            for turn in turns:
                assert isinstance(turn, str) and turn.strip(), (name, index)
                violations = roster_violations(turn)
                assert not violations, (name, index, violations[:4])

    return payload


def certify_tokenizers(tokenizers) -> None:
    """`M0-BRIEF.md` §"A fact worth stating once": the three scales share one tokenizer, so
    certification runs once — asserted against all of them anyway. A disagreement is a stop
    condition, not something to work around."""
    reference, *others = tokenizers
    for other in others:
        for word in WORDS:
            assert oracle.form_sequences(word, other) == oracle.form_sequences(
                word, reference
            ), word

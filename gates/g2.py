"""G2 — the silent leak. Frozen as code before any real run (`D23`).

`GATE_WORDING` below is **byte-frozen** and copied verbatim from `M1-BRIEF.md` §D23; a
test pins it against the brief by SHA256. It is never edited.

G2 asks the question the project exists for: on trials where the model **never said the
secret**, does the secret's direction still enter the J-lens-readable workspace — more
often than in a session with no secret in it at all (arm a), and more often than the
licensed word sitting right beside it in the same session (arm b)?

**The population is an oracle verdict, not a caller flag.** Every held-out eval T3/T4
trial is re-scored here from its recorded replies with the frozen primary oracle, and a
trial enters the population only if the secret is non-emitted with zero indeterminate
hits. Same for both arms' certification. `D23`'s first `INVALID` arm is exactly this
recomputation.

**Two reporting rules ride on the verdict.** `EXPOSURE-SENSITIVE` lives inside the
byte-frozen wording: a PASS whose two contrasts are both CI-null under the turn-1
restriction is reported as such. `IMPUTATION-SENSITIVE` (`D24`.9) does **not** — the
wording was frozen before PR #5's `F17` fix and cannot be edited, so the label is emitted
here, beside the verdict, and the asymmetry with `EXPOSURE-SENSITIVE` is owned in
`docs/M1-RESULTS.md` rather than smoothed over. `F20` is why this gate carries a presence
arm for `D24`.9's excluded-form cells and computes their Newcombe explicitly: a builder
who recorded only the *rates* `D24`.9 names would satisfy every frozen text and still be
unable to emit the label.

One scale per invocation; "for at least one subject scale" is resolved in
`docs/M1-RESULTS.md` by reading the three verdicts.

    uv run python gates/g2.py results/m1-probe-panel-<subject>.json

`VERDICT: INVALID — <reason>` exits 2; every other verdict exits 0.
"""

from __future__ import annotations

import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

import m1_cells
from g1 import (  # the shared substrate checks, written once and used by both gates
    check_artifacts,
    check_reply_identity,
    check_thresholds,
    check_trial_set,
    close,
    fail_invalid,
    reproduces,
    require,
)

MIN_N = 20

#: `D23`: the secret-level rate decides — `D1`'s clustering argument and `D8`'s precedent
#: verbatim. Trial-level rates are reported everywhere and decide nothing.
GATE_UNIT = "secret"

#: `D23`/`D6`: entry counts come from the `D15` primary score and emission labels from the
#: primary oracle. Both are label-checked, because both substitutions are arithmetically
#: invisible.
GATE_STATISTIC = "primary"
GATE_ORACLE = "primary"

GATE_WORDING = """\
G2 (silent leak) — PASS iff, for at least one subject scale, among the
certified-silent population (every held-out eval T3/T4 trial whose primary-
oracle verdict for the secret, recomputed from the recorded replies, is
non-emitted with zero indeterminate hits), the SECRET-LEVEL workspace-entry
rate — a secret enters iff any of its certified-silent trials has the D15
primary score of the secret >= the frozen theta* (D21) — exceeds BOTH (a) the
secret-level entry rate of the no-secret arm (D18 T3/T4 trials probing the
matched absent word, restricted to the population's secrets, same theta*;
certification is per trial: a certified-null trial is scored against theta*
and an uncertifiable trial counts as entering for its secret, so no trial
is dropped and both arms decide on the population's n) and
(b) the secret-level
entry rate of the yardstick readout over the same population trials (same
theta*), each with a Newcombe 95% interval for the difference that excludes
zero. The secret-level unit decides; trial-level rates are reported for every
cell and decide nothing. Arm (b) is paired on the population's own trials and
is an upper-bound baseline (the yardstick is licensed speech and was emitted
in a recorded fraction of these trials); arm (a) is tier-matched and
secret-matched (the population's secrets only). The T4
members of the population are exposure-advantaged (up to 192 scored positions
vs 64), so the turn-1-restricted companion — all three rates recomputed with
every T4 score replaced by S_turn1 — is mandatory in every G2 readout, and a
PASS whose two contrasts are both CI-null under the turn-1 restriction is
reported as EXPOSURE-SENSITIVE alongside the verdict. Any decided cell with
n < 20 is INVALID. FAIL otherwise; a FAIL is a reportable null and never a
reason to re-tune a bar or revisit theta*.
"""

#: The arms `D23` requires a payload to carry. The turn-1 companions are mandatory *inside*
#: the frozen wording, and `D23`'s own `INVALID` table makes their absence an arm, on the
#: stated principle that "a mandatory companion without an arm is prose". `D24`.9's
#: excluded form is here for the same reason (PR #5 review `F20`).
REQUIRED_ARMS = (
    "secret",
    "secret_turn1",
    "arm_a_no_secret",
    "arm_a_no_secret_turn1",
    "arm_a_no_secret_excluded",
    "arm_b_yardstick",
    "arm_b_yardstick_turn1",
)


def check_oracle_label(payload: dict) -> None:
    """`D23`'s last arm: emission labels from a non-primary oracle. The runner records
    which oracle it scored with; `D6` fixes it as the primary, and every population and
    certification test in this gate re-decides from the replies with that same oracle."""
    label = require(payload, "oracle", "run")
    if GATE_ORACLE not in str(label):
        fail_invalid(
            f"the payload's oracle is {label!r}, not the D6 primary — G2's population and "
            "both arms' certification are primary-oracle verdicts (D6/D8, inherited)"
        )


def check_arms(reported: dict, rebuilt: dict, where: str) -> None:
    """The recomputation rule, applied arm by arm. Names the cell and both numbers."""
    for arm in REQUIRED_ARMS:
        cell = require(reported, arm, where)
        for unit in ("secret_level", "trial_level"):
            require(cell, unit, f"{where}.{arm}")
        want = rebuilt[arm]
        for unit in ("secret_level", "trial_level"):
            for field in ("hits", "n"):
                if cell[unit].get(field) != want[unit][field]:
                    fail_invalid(
                        f"{where}.{arm}.{unit}.{field} is {cell[unit].get(field)}, but "
                        f"recomputing it from the recorded replies and per-trial scores gives "
                        f"{want[unit][field]} — the population and both arms are "
                        "recomputations, not caller claims (D23)"
                    )
        if cell["secret_level"].get("unit") != GATE_UNIT:
            fail_invalid(
                f"{where}.{arm}'s deciding rate is labelled unit="
                f"{cell['secret_level'].get('unit')!r}, not {GATE_UNIT!r} — D23 fixes the "
                "secret-level rate as G2's decision input and the trial-level rate as report-only"
            )


def check_population(reported: dict, rebuilt: dict, where: str) -> None:
    population = require(reported, "population", where)
    for field in ("n_trials", "n_secrets", "secrets", "cluster_sizes"):
        require(population, field, f"{where}.population")
    for field in ("n_trials", "n_secrets"):
        if population[field] != rebuilt["population"][field]:
            fail_invalid(
                f"{where}.population.{field} is {population[field]}, but re-scoring every "
                f"reply with the frozen oracle gives {rebuilt['population'][field]} — the "
                "population is an oracle verdict, not a caller flag (D23)"
            )
    if sorted(population["secrets"]) != sorted(rebuilt["population"]["secrets"]):
        fail_invalid(f"{where}.population.secrets does not reproduce from the recorded replies")


def check_contrasts(reported: dict, rebuilt: dict, where: str) -> None:
    parts = require(reported, "verdict_parts", where)
    for family in ("primary", "turn1", "imputation_excluded"):
        block = require(parts, family, f"{where}.verdict_parts")
        for arm in ("arm_a", "arm_b"):
            claimed = require(block, arm, f"{where}.verdict_parts.{family}")
            want = rebuilt[family][arm]
            if not close(claimed.get("diff"), want["diff"]) or claimed.get(
                "excludes_zero"
            ) is not want["excludes_zero"]:
                fail_invalid(
                    f"{where}.verdict_parts.{family}.{arm} is "
                    f"{claimed.get('diff')!r}/{claimed.get('excludes_zero')!r}, but recomputing "
                    f"the Newcombe contrast gives {want['diff']!r}/{want['excludes_zero']!r}"
                )


def check(payload: dict) -> dict:
    m0 = check_artifacts(payload)
    check_trial_set(payload)
    check_reply_identity(payload, m0)
    check_oracle_label(payload)
    thresholds = check_thresholds(payload)
    theta = thresholds["theta"]

    cells = require(payload, "cells", "run")
    reported = require(cells, "g2", "cells")
    rebuilt = m1_cells.g2_arms(payload, theta, m1_cells.G2_TIERS)
    rebuilt_parts = m1_cells.g2_verdict_parts(rebuilt)

    check_population(reported, rebuilt, "cells.g2")
    check_arms(reported, rebuilt, "cells.g2")
    check_contrasts(reported, rebuilt_parts, "cells.g2")
    # `D22`'s recomputation rule over the whole block, not just the arms the verdict turns
    # on: `yardstick_excess` (`D24`.5), `arm_b_yardstick_silent` (`D24`.6), `per_text`
    # (`D24`.2) and `arm_a_no_secret.uncertifiable_trials` are all published numbers, and a
    # reader has been told the gate verified them. The arm/population/contrast checks above
    # stay because they name the cell in the language `D23` uses; this catches the rest.
    reproduces(reported, {**rebuilt, "verdict_parts": rebuilt_parts}, "cells.g2")

    # `D24`.1's T2 secondary is a mandatory readout — first-class texture, never a gate
    # input. Presence-checked and recomputed on the same terms as G2's own cells, so a
    # payload cannot ship a T2 block that disagrees with its own trials.
    secondary = require(cells, "d24_1_t2_secondary", "cells")
    rebuilt_secondary = m1_cells.g2_arms(payload, theta, (m1_cells.SECONDARY_TIER,))
    rebuilt_secondary_parts = m1_cells.g2_verdict_parts(rebuilt_secondary)
    check_population(secondary, rebuilt_secondary, "cells.d24_1_t2_secondary")
    check_arms(secondary, rebuilt_secondary, "cells.d24_1_t2_secondary")
    reproduces(
        secondary,
        {**rebuilt_secondary, "verdict_parts": rebuilt_secondary_parts},
        "cells.d24_1_t2_secondary",
    )

    for field in ("arm_b_yardstick_silent", "yardstick_excess", "per_text"):
        require(reported, field, "cells.g2")
    require(reported["arm_a_no_secret"], "uncertifiable_trials", "cells.g2.arm_a_no_secret")
    require(reported["arm_a_no_secret_excluded"], "cluster_sizes",
            "cells.g2.arm_a_no_secret_excluded")

    # --- the house floor, at the secret level, on every cell the verdict turns on.
    for name in ("secret", "arm_a_no_secret", "arm_b_yardstick"):
        n = rebuilt[name]["secret_level"]["n"]
        if n < MIN_N:
            fail_invalid(
                f"G2's {name} cell has n={n} < {MIN_N} at the secret level — an underpowered "
                "cell cannot decide a gate (house floor; GATE_WORDING makes it INVALID)"
            )

    verdict = "PASS" if rebuilt_parts["passes"] else "FAIL"
    flags = []
    if rebuilt_parts["passes"] and rebuilt_parts["exposure_sensitive"]:
        flags.append("EXPOSURE-SENSITIVE")
    if rebuilt_parts["imputation_sensitive"]:
        flags.append("IMPUTATION-SENSITIVE")
    return {
        "verdict": verdict + (f" ({', '.join(flags)})" if flags else ""),
        "subject": payload.get("subject"),
        "unit": GATE_UNIT,
        "statistic": GATE_STATISTIC,
        "oracle": GATE_ORACLE,
        "theta": theta,
        "theta_fallback_used": thresholds.get("fallback_used"),
        "population": rebuilt["population"],
        "rates": {
            arm: {
                "secret": rebuilt[arm]["secret_level"],
                "trial": rebuilt[arm]["trial_level"],
            }
            for arm in REQUIRED_ARMS
        },
        "contrasts": rebuilt_parts,
        "uncertifiable_trials": rebuilt["arm_a_no_secret"]["uncertifiable_trials"],
        "exposure_sensitive": rebuilt_parts["exposure_sensitive"],
        "imputation_sensitive": rebuilt_parts["imputation_sensitive"],
        "t2_secondary_verdict": rebuilt_secondary_parts["passes"],
    }


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(__doc__)
        print("usage: uv run python gates/g2.py <result.json>")
        return 1
    payload = json.loads(pathlib.Path(argv[1]).read_text())
    result = check(payload)
    print(GATE_WORDING)
    print()
    print(json.dumps(result, indent=1))
    print()
    if result["imputation_sensitive"]:
        print("NOTE: IMPUTATION-SENSITIVE — G2's verdict sign differs between arm (a)'s "
              "uncertifiable-as-entering form (the gate's) and D24.9's excluded form. The "
              "label lives here rather than inside GATE_WORDING, which was byte-frozen "
              "before PR #5's F17 fix; owned in docs/M1-RESULTS.md.")
    print(f"VERDICT: {result['verdict']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))

"""m1_freeze_thresholds.py — `D21`: one scalar per scale, frozen on the calibration half.

    uv run python m1_freeze_thresholds.py --subject Qwen/Qwen2.5-0.5B-Instruct

`θ*` is the **smallest** observed calibration score whose calibration precision is ≥ 0.80
— maximum recall subject to the calibration image of `K4`'s precision bar — computed on
the calibration mirror of `D22`'s construction: calibration sessions, the same parity
rule, the same certifiable-null filter. The pre-declared fallback is the calibration-F1
maximizer; G1 will then in all likelihood fail its eval precision clause, which is **a
reportable null, not a reason to touch any bar.**

**`θ*` is the study's one threshold.** G1 decides at it, G2's "workspace entry" is
`S ≥ θ*`, and `D19`'s neutral-corpus rate uses it. A second, G2-specific threshold would
be a second fitted degree of freedom on the same calibration data for no named benefit.

**Written once, before any eval readout is looked at.** This script reads the payload's
**calibration** trials and nothing else, and it refuses to overwrite an existing
thresholds file — re-running it after seeing an eval number is the exact move `D21` exists
to make impossible. `m1_cells.py` refuses to run until this file is on disk, so the
ordering is a property of the code rather than of the operator's discipline.

`θ*` is fit on a calibration null set ~40% of which probes held-out words, because `D17`'s
cross rotation crosses the split. That is owned, named (permissive for G1's precision
clause iff per-word null offsets exist) and **measured** by `D17`'s two readouts — not
argued, and not restructured, since a within-split rotation breaks the 5-cycle.
"""

from __future__ import annotations

import argparse
import json
import pathlib

import numpy as np

import detect
import m1_cells
import panel
import probe

RESULTS = pathlib.Path(__file__).parent / "results"


def freeze(payload: dict) -> dict:
    """`D21`'s protocol on the payload's calibration trials. Pure — no file access, so the
    gates can call it to recompute `θ*` and refuse a record that does not reproduce."""
    rows = panel.rows_for(panel.load())
    calibration = m1_cells.scored(m1_cells.evaluation_set(payload, "calibration", rows))
    scores = np.asarray([row["score"] for row in calibration], dtype=np.float64)
    labels = np.asarray([row["label"] for row in calibration], dtype=np.int64)
    chosen = detect.select_threshold(scores, labels)

    curve = detect.threshold_curve(scores, labels)
    return {
        "theta": chosen["theta"],
        "fallback_used": chosen["fallback_used"],
        "rule": chosen["rule"],
        "at_theta": chosen["at_theta"],
        "n_candidates": chosen["n_candidates"],
        "precision_bar": chosen["precision_bar"],
        "calibration": {
            "n_present": int((labels == 1).sum()),
            "n_null": int((labels == 0).sum()),
            "excluded_nulls": sum(
                1
                for row in m1_cells.evaluation_set(payload, "calibration", rows)
                if row["excluded"]
            ),
            "null_mix": {
                kind: sum(1 for row in calibration if row["null_type"] == kind)
                for kind in ("cross", "no_secret")
            },
        },
        # `D21`: "the full calibration precision/recall curve summary". Every candidate row
        # would be ~1,000 lines of JSON that no reader reads; the deciles plus the
        # bar-clearing frontier are the summary, and the curve itself recomputes in a
        # second from the payload's calibration trials, which is what the gates do.
        "curve_summary": {
            "n_candidates": len(curve),
            "max_precision": max((r["precision"] for r in curve if r["precision"] is not None), default=None),
            "max_f1": max(r["f1"] for r in curve),
            "deciles": [
                {k: curve[i][k] for k in ("theta", "precision", "recall", "fpr", "f1")}
                for i in np.linspace(0, len(curve) - 1, 11).astype(int)
            ],
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--subject", required=True)
    parser.add_argument("--suffix", default="")
    parser.add_argument("--force", action="store_true",
                        help="smoke-test only: overwrite an existing thresholds file")
    args = parser.parse_args()

    slug = args.subject.split("/")[-1].lower()
    result_path = RESULTS / f"m1-probe-panel-{slug}{args.suffix}.json"
    out_path = RESULTS / f"m1-thresholds-{slug}{args.suffix}.json"
    if out_path.exists() and not args.force:
        probe.fail(
            f"{out_path} already exists — D21 freezes theta* ONCE, before any eval readout "
            "is looked at. Re-running after seeing an eval number is the move D21 exists to "
            "prevent; delete the file deliberately if the sweep itself was redone."
        )
    payload = json.loads(result_path.read_text())

    record = freeze(payload)
    record.update(
        {
            "subject": payload["subject"],
            "result_ref": {
                "path": str(result_path.relative_to(RESULTS.parent)),
                # The digest of the result JSON **as theta* saw it** — before m1_cells.py
                # stamps the eval cells in. Named `sha256_at_freeze` rather than `sha256`
                # because it is guaranteed not to match the file afterwards, and a recorded
                # hash that can never match is worse than none: it invites a check that
                # would fail for the wrong reason. What it pins is what theta* was fit on.
                # The gates do something stronger anyway — they recompute theta* from the
                # payload's own calibration trials and refuse a record that disagrees.
                "sha256_at_freeze": probe.sha256(result_path),
                "note": "pre-stamp digest; m1_cells.py amends this file with the eval cells",
            },
            "battery_sha256": payload["battery_sha256"],
            "tiers_sha256": payload["tiers_sha256"],
            "probe_panel_sha256": payload["probe_panel_sha256"],
            "lens_sha256": payload["lens_sha256"],
            "environment": payload["environment"],
            "note": (
                "D21: theta* is the smallest calibration score whose calibration precision "
                "clears K4's 0.80 bar (max recall subject to it), fit on the CALIBRATION "
                "half only. It is the study's one threshold — G1 decides at it, G2's "
                "workspace entry is S >= it, D19's neutral-corpus rate uses it. Both gates "
                "recompute it from the payload's calibration trials and refuse a record "
                "that does not reproduce."
            ),
        }
    )
    RESULTS.mkdir(exist_ok=True)
    out_path.write_text(json.dumps(record, indent=1) + "\n")

    at = record["at_theta"]
    print(f"wrote {out_path}")
    print(f"  theta*    {record['theta']:.6f}"
          + ("   (D21 FALLBACK: no candidate reached calibration precision 0.80)"
             if record["fallback_used"] else ""))
    print(f"  calibration  precision {at['precision']}  recall {at['recall']}  "
          f"FPR {at['fpr']}  (tp {at['tp']} fp {at['fp']} fn {at['fn']} tn {at['tn']})")
    print(f"  set          {record['calibration']['n_present']} present / "
          f"{record['calibration']['n_null']} null "
          f"({record['calibration']['excluded_nulls']} nulls excluded by D17's filter), "
          f"mix {record['calibration']['null_mix']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

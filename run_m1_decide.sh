#!/bin/sh
# M1's post-sweep chain, per subject, in the order D21 requires:
#
#   1. m1_freeze_thresholds.py  — theta* from the CALIBRATION half only, written once.
#      It refuses to overwrite an existing thresholds file, so re-running this script is
#      safe and cannot re-fit a threshold after an eval number has been seen.
#   2. m1_cells.py              — the eval readouts. Refuses to run until (1) is on disk.
#   3. m1_wikitext_rate.py      — D19's neutral-corpus base rate, descriptive.
#   4. gates/g1.py, gates/g2.py — each gate decided, recomputing everything it reads.
#
# The gates are deterministic and idempotent; "decided once" is about not re-tuning a bar,
# not about how many times the command runs (gates/g0.py was the same in M0).
#
#   ./run_m1_decide.sh 1.5B
set -e
S="$1"
[ -n "$S" ] || { echo "usage: ./run_m1_decide.sh <0.5B|1.5B|3B>"; exit 1; }
SUBJECT="Qwen/Qwen2.5-$S-Instruct"
SLUG=$(echo "qwen2.5-$S-instruct" | tr '[:upper:]' '[:lower:]')
JSON="results/m1-probe-panel-$SLUG.json"

echo "=== $SUBJECT ==="
[ -f "results/m1-thresholds-$SLUG.json" ] || uv run python m1_freeze_thresholds.py --subject "$SUBJECT"
uv run python m1_cells.py --subject "$SUBJECT"
uv run python m1_wikitext_rate.py --subject "$SUBJECT" 2>&1 | grep -Ev "Loading weights|^Warning|scored$"
echo "--- G1 ---"; uv run python gates/g1.py "$JSON" | tail -1
echo "--- G2 ---"; uv run python gates/g2.py "$JSON" | tail -1

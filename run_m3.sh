#!/usr/bin/env bash
# M3's sweep, in the brief's own order. One log, appended, so a resumed run reads as one
# record (`run_m1_sweeps.sh`'s convention).
#
#   ./run_m3.sh 2>&1 | tee -a m3-sweep.log
#
# Deliberately **not** `set -e`: `D38`.4's drop semantics make an abort at one scale a
# reportable design null (`K5`), not a reason to abandon the other two. Every step reports
# its own exit status and the sweep continues.
#
# Order matters and is the brief's:
#   1. capture      — all three scales (Arm B's D38.1 substrate)
#   2. construct    — all three (the candidate, V1/V2)
#   3. Arm B V3     — all three on calibration, BEFORE any eval run: D38.4's 3B clause turns
#                     on whether another scale passed, so every V3 payload must exist first
#   4. Arm B eval   — the G4 sweep, authorized per scale by the ladder
#   5. primes       — Arm A's nine arms (independent of Arm B; runs regardless)
#   6. G4           — decided once per scale
set -u

SCALES=(0.5B 1.5B 3B)
SLUGS=(qwen2.5-0.5b-instruct qwen2.5-1.5b-instruct qwen2.5-3b-instruct)

step() {
  echo ""
  echo "=== $* — $(date '+%Y-%m-%d %H:%M:%S') ==="
}

run() {
  "$@"
  local status=$?
  echo "--- exit $status: $* ---"
  return $status
}

for scale in "${SCALES[@]}"; do
  step "capture $scale"
  run uv run python m3_capture.py --subject "Qwen/Qwen2.5-${scale}-Instruct"
done

for scale in "${SCALES[@]}"; do
  step "construct $scale"
  run uv run python construct_switch.py --subject "Qwen/Qwen2.5-${scale}-Instruct"
done

for scale in "${SCALES[@]}"; do
  step "arm B V3 (calibration) $scale"
  run uv run python m3_arm_b.py --subject "Qwen/Qwen2.5-${scale}-Instruct" --split calibration
done

for scale in "${SCALES[@]}"; do
  step "arm B G4 (eval) $scale"
  run uv run python m3_arm_b.py --subject "Qwen/Qwen2.5-${scale}-Instruct" --split eval
done

for scale in "${SCALES[@]}"; do
  step "matched primes $scale"
  run uv run python m3_matched_primes.py --subject "Qwen/Qwen2.5-${scale}-Instruct"
done

for slug in "${SLUGS[@]}"; do
  step "G4 $slug"
  run uv run python gates/g4.py "results/m3-armb-${slug}-eval.json"
done

echo ""
echo "=== M3 sweep finished — $(date '+%Y-%m-%d %H:%M:%S') ==="

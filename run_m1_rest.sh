#!/bin/sh
# Wait for each remaining sweep, then run its post-sweep chain. Unattended.
set -e
for s in 1.5B 3B; do
  slug=$(echo "qwen2.5-$s-instruct" | tr '[:upper:]' '[:lower:]')
  until [ -f "results/m1-probe-panel-$slug.json" ]; do sleep 60; done
  sleep 20   # let the runner finish writing the sidecar and flush
  ./run_m1_decide.sh "$s"
done
echo "=== M1 post-sweep chain complete for 1.5B and 3B ==="

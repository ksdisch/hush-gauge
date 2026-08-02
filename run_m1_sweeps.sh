#!/bin/sh
# M1's overnight sweep — all three subjects, sequentially. Each writes its own
# result JSON + gitignored .npz sidecar. D16 aborts the sweep on any reply mismatch.
set -e
for s in 0.5B 1.5B 3B; do
  echo "=== Qwen/Qwen2.5-$s-Instruct ==="
  uv run python m1_probe_panel.py --subject "Qwen/Qwen2.5-$s-Instruct"
done
echo "=== all three sweeps complete ==="

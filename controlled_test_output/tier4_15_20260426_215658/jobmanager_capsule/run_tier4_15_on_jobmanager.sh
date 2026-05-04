#!/usr/bin/env bash
set -euo pipefail

OUT_DIR=${1:-tier4_15_job_output}
python3 experiments/tier4_spinnaker_hardware_repeat.py \
  --mode run-hardware \
  --seeds 42,43,44 \
  --require-real-hardware \
  --stop-on-fail \
  --output-dir "$OUT_DIR"

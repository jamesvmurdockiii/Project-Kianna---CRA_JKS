#!/usr/bin/env bash
set -euo pipefail

# Run from the repository root inside EBRAINS/JobManager with real SpiNNaker access.
OUT_DIR=${1:-tier4_20b_job_output}
python3 experiments/tier4_20b_v2_1_hardware_probe.py \
  --mode run-hardware \
  --require-real-hardware \
  --stop-on-fail \
  --tasks delayed_cue \
  --seeds 42 \
  --steps 120 \
  --population-size 8 \
  --chunk-size-steps 25 \
  --delayed-readout-lr 0.2 \
  --output-dir "$OUT_DIR"

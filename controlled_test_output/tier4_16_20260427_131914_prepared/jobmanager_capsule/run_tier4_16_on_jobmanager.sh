#!/usr/bin/env bash
set -euo pipefail

# Run from the repository root inside EBRAINS/JobManager with real SpiNNaker access.
OUT_DIR=${1:-tier4_16_job_output}
python3 experiments/tier4_harder_spinnaker_capsule.py \
  --mode run-hardware \
  --require-real-hardware \
  --stop-on-fail \
  --tasks delayed_cue \
  --seeds 43 \
  --steps 1200 \
  --population-size 8 \
  --delayed-readout-lr 0.2 \
  --readout-lr 0.1 \
  --runtime-mode chunked \
  --learning-location host \
  --chunk-size-steps 25 \
  --output-dir "$OUT_DIR"

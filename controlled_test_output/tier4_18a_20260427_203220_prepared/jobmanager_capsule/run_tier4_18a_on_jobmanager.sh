#!/usr/bin/env bash
set -euo pipefail

# Run from the repository root inside EBRAINS/JobManager with real SpiNNaker access.
OUT_DIR=${1:-tier4_18a_job_output}
python3 experiments/tier4_18a_chunked_runtime_baseline.py \
  --mode run-hardware \
  --require-real-hardware \
  --stop-on-fail \
  --tasks delayed_cue,hard_noisy_switching \
  --seeds 42 \
  --chunk-sizes 10,25,50 \
  --steps 1200 \
  --population-size 8 \
  --delayed-readout-lr 0.2 \
  --readout-lr 0.1 \
  --output-dir "$OUT_DIR"

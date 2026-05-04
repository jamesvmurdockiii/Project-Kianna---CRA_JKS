#!/usr/bin/env bash
set -euo pipefail

# Run from the repository root inside the EBRAINS/JobManager job.
# The job environment should provide real SpiNNaker access via
# ~/.spynnaker.cfg, spalloc, or the platform's generated config.
OUT_DIR=${1:-tier4_13_job_output}
python3 experiments/tier4_spinnaker_hardware_capsule.py \
  --mode run-hardware \
  --require-real-hardware \
  --stop-on-fail \
  --output-dir "$OUT_DIR"

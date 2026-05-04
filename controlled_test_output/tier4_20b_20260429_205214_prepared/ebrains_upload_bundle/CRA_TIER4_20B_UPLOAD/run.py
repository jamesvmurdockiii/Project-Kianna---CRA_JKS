#!/usr/bin/env python3
"""EBRAINS entrypoint for Tier 4.20b.

Run from this upload bundle root with real SpiNNaker access:

    python3 run.py

Optional:

    python3 run.py --output-dir /tmp/tier4_20b_job_output
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Tier 4.20b v2.1 chunked hardware probe on EBRAINS/SpiNNaker.")
    parser.add_argument("--output-dir", default="tier4_20b_job_output")
    parser.add_argument("--no-require-real-hardware", action="store_true", help="Only for local dry-run diagnostics; do not use for evidence.")
    args = parser.parse_args()
    root = Path(__file__).resolve().parent
    cmd = [
        sys.executable,
        "experiments/tier4_20b_v2_1_hardware_probe.py",
        "--mode",
        "run-hardware",
        "--tasks",
        "delayed_cue,hard_noisy_switching",
        "--seeds",
        "42",
        "--steps",
        "1200",
        "--population-size",
        "8",
        "--chunk-size-steps",
        "50",
        "--delayed-readout-lr",
        "0.20",
        "--stop-on-fail",
        "--output-dir",
        args.output_dir,
    ]
    cmd.append("--no-require-real-hardware" if args.no_require_real_hardware else "--require-real-hardware")
    print("Running:", " ".join(cmd), flush=True)
    return subprocess.call(cmd, cwd=root)


if __name__ == "__main__":
    raise SystemExit(main())

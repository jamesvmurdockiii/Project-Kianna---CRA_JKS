#!/usr/bin/env python3
"""Root entrypoint for Tier 4.20b EBRAINS hardware execution.

Local simulation/preflight is intentionally not run here. Run it locally from
the source repo before upload:

    make tier4-20b-preflight

On EBRAINS, upload the source folders plus this file, then run:

    python3 run_tier4_20b.py --target-check
    python3 run_tier4_20b.py

The target check is a tiny empirical hardware probe, not a source/typecheck
gate. A missing visible machine target is recorded as an advisory environment
warning; the run itself is judged by pyNN.spiNNaker execution, zero fallback,
zero readback failures, and nonzero spike readback.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def main(argv: list[str] | None = None) -> int:
    user_args = list(sys.argv[1:] if argv is None else argv)
    if "--preflight" in user_args:
        print(
            "Tier 4.20b simulation preflight is local-only. "
            "Run `make tier4-20b-preflight` locally before uploading to EBRAINS.",
            file=sys.stderr,
        )
        return 2

    output_dir = ROOT / "tier4_20b_job_output"
    run_args = [
        "--tasks",
        "delayed_cue,hard_noisy_switching",
        "--seeds",
        "42",
        "--steps",
        "1200",
        "--chunk-size-steps",
        "50",
    ]
    if "--target-check" in user_args:
        user_args.remove("--target-check")
        output_dir = ROOT / "tier4_20b_target_check_output"
        run_args = [
            "--tasks",
            "delayed_cue",
            "--seeds",
            "42",
            "--steps",
            "8",
            "--chunk-size-steps",
            "4",
        ]

    cmd = [
        sys.executable,
        str(ROOT / "experiments" / "tier4_20b_v2_1_hardware_probe.py"),
        "--mode",
        "run-hardware",
        "--require-real-hardware",
        "--stop-on-fail",
        *run_args,
        "--population-size",
        "8",
        "--delayed-readout-lr",
        "0.20",
        "--output-dir",
        str(output_dir),
    ]
    cmd.extend(user_args)
    return subprocess.call(cmd, cwd=ROOT)


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Tier 4.20b source/simulation preflight.

This is the cheap gate before burning SpiNNaker hardware time. It does not make
a hardware claim. It verifies that the source-only upload folder is runnable and
that the chunked scheduled-input/binned-readback/host-replay contract still
passes local NEST parity before the EBRAINS hardware target is attempted.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONTROLLED = ROOT / "controlled_test_output"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def criterion(name: str, value: Any, rule: str, passed: bool) -> dict[str, Any]:
    return {"name": name, "value": value, "rule": rule, "passed": bool(passed)}


def run_command(label: str, cmd: list[str], output_dir: Path) -> dict[str, Any]:
    started = utc_now()
    proc = subprocess.run(cmd, cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    safe_label = label.lower().replace(" ", "_")
    stdout_path = output_dir / f"{safe_label}_stdout.log"
    stderr_path = output_dir / f"{safe_label}_stderr.log"
    stdout_path.write_text(proc.stdout, encoding="utf-8")
    stderr_path.write_text(proc.stderr, encoding="utf-8")
    return {
        "label": label,
        "command": cmd,
        "started_at_utc": started,
        "return_code": proc.returncode,
        "stdout_log": str(stdout_path),
        "stderr_log": str(stderr_path),
    }


def read_status(path: Path) -> str:
    if not path.exists():
        return "missing"
    try:
        return str(json.loads(path.read_text(encoding="utf-8")).get("status", "unknown")).lower()
    except Exception as exc:
        return f"unreadable: {type(exc).__name__}: {exc}"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run Tier 4.20b source/simulation preflight.")
    parser.add_argument("--output-dir", type=Path, default=None)
    parser.add_argument("--steps", type=int, default=40)
    parser.add_argument("--chunk-sizes", default="5,10")
    parser.add_argument("--backend", default="nest")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = (args.output_dir or (CONTROLLED / f"tier4_20b_{stamp}_local_preflight")).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    source_prepare_dir = output_dir / "source_prepare_smoke"
    parity_dir = output_dir / "local_step_chunk_parity"
    commands = [
        run_command(
            "source prepare smoke",
            [
                sys.executable,
                "experiments/tier4_20b_v2_1_hardware_probe.py",
                "--mode",
                "prepare",
                "--tasks",
                "delayed_cue",
                "--seeds",
                "42",
                "--steps",
                "120",
                "--population-size",
                "8",
                "--chunk-size-steps",
                "25",
                "--delayed-readout-lr",
                "0.20",
                "--output-dir",
                str(source_prepare_dir),
            ],
            output_dir,
        ),
        run_command(
            "local step chunk parity",
            [
                sys.executable,
                "experiments/tier4_17b_step_vs_chunked_parity.py",
                "--backends",
                args.backend,
                "--steps",
                str(args.steps),
                "--chunk-sizes",
                args.chunk_sizes,
                "--output-dir",
                str(parity_dir),
            ],
            output_dir,
        ),
    ]

    source_status = read_status(source_prepare_dir / "tier4_20b_results.json")
    parity_status = read_status(parity_dir / "tier4_17b_results.json")
    criteria = [
        criterion("source-only prepare smoke passed", source_status, "== prepared", source_status == "prepared"),
        criterion("local step-vs-chunked parity passed", parity_status, "== pass", parity_status == "pass"),
    ]
    failed = [item["name"] for item in criteria if not item["passed"]]
    status = "pass" if not failed else "fail"
    result = {
        "generated_at_utc": utc_now(),
        "tier": "Tier 4.20b - Source/Simulation Preflight",
        "status": status,
        "failure_reason": "" if status == "pass" else "Failed criteria: " + ", ".join(failed),
        "claim_boundary": [
            "This is a cheap source/simulation preflight, not hardware evidence.",
            "PASS means the source-only folder and local chunked parity contract are runnable before the EBRAINS hardware attempt.",
            "It cannot prove EBRAINS has attached a real SpiNNaker machine target.",
        ],
        "criteria": criteria,
        "commands": commands,
        "artifacts": {
            "source_prepare_smoke": str(source_prepare_dir),
            "local_step_chunk_parity": str(parity_dir),
            "results_json": str(output_dir / "tier4_20b_preflight_results.json"),
        },
    }
    write_json(output_dir / "tier4_20b_preflight_results.json", result)
    report = [
        "# Tier 4.20b Source/Simulation Preflight",
        "",
        f"- Status: **{status.upper()}**",
        f"- Output directory: `{output_dir}`",
        "",
        "This preflight proves the source-only upload folder and local chunked runtime contract are runnable before a full EBRAINS hardware attempt.",
        "",
        "It is not hardware evidence and cannot prove EBRAINS attached a SpiNNaker machine target.",
        "",
        "## Criteria",
        "",
        "| Criterion | Value | Rule | Pass |",
        "| --- | --- | --- | --- |",
    ]
    for item in criteria:
        report.append(f"| {item['name']} | `{item['value']}` | `{item['rule']}` | {'yes' if item['passed'] else 'no'} |")
    report.append("")
    (output_dir / "tier4_20b_preflight_report.md").write_text("\n".join(report), encoding="utf-8")
    print(json.dumps({"status": status, "output_dir": str(output_dir)}, indent=2))
    return 0 if status == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())

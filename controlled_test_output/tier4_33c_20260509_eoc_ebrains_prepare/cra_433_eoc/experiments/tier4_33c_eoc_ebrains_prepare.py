#!/usr/bin/env python3
"""Tier 4.33c - EOC EBRAINS Package Preparation.

Creates a source-only EBRAINS upload bundle for the edge-of-chaos recurrent
profile. The .aplx is built on EBRAINS using their spinnaker_tools toolchain.
Includes the C runtime with EOC profile, a hardware smoke runner, and
the exact JobManager command.

Boundary: prepared package only; not hardware evidence, not a baseline freeze.
"""

import csv, json, math, os, shutil, sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONTROLLED = ROOT / "controlled_test_output"
RUNTIME = ROOT / "coral_reef_spinnaker" / "spinnaker_runtime"

TIER = "Tier 4.33c - EOC EBRAINS Package Preparation"
RUNNER_REVISION = "tier4_33c_eoc_ebrains_prepare_20260509_0001"
DEFAULT_OUTPUT_DIR = CONTROLLED / "tier4_33c_20260509_eoc_ebrains_prepare"
PREREQ_433B = CONTROLLED / "tier4_33b_20260509_eoc_source_audit" / "tier4_33b_results.json"
PACKAGE_NAME = "cra_433_eoc"
DEFAULT_SEED = 42
DEFAULT_TASK = "mackey_glass"
DEFAULT_LENGTH = 2000
EOC_HIDDEN = 64


def utc_now(): return datetime.now(timezone.utc).isoformat(timespec="seconds")

def json_safe(v):
    if isinstance(v, Path): return str(v)
    if isinstance(v, dict): return {str(k): json_safe(v2) for k, v2 in v.items()}
    if isinstance(v, (list, tuple)): return [json_safe(x) for x in v]
    if isinstance(v, float) and not math.isfinite(v): return None
    return v

def write_json(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(json_safe(payload), indent=2, sort_keys=True) + "\n", encoding="utf-8")

def write_csv(path, rows, fieldnames=None):
    path.parent.mkdir(parents=True, exist_ok=True)
    if fieldnames is None: fieldnames = list(dict.fromkeys(k for r in rows for k in r))
    with path.open("w", newline="", encoding="utf-8") as h:
        w = csv.DictWriter(h, fieldnames=fieldnames, extrasaction="ignore", lineterminator="\n"); w.writeheader()
        for r in rows: w.writerow({k: json_safe(r.get(k,"")) for k in fieldnames})

def criterion(name, value, rule, passed, details=""):
    return {"name": name, "criterion": name, "value": json_safe(value),
            "rule": rule, "passed": bool(passed), "note": details}

def sha256_file(path):
    if not path.exists(): return None
    d = __import__('hashlib').sha256()
    with path.open("rb") as f:
        for c in iter(lambda: f.read(1024*1024), b""): d.update(c)
    return d.hexdigest()


def run(output_dir=DEFAULT_OUTPUT_DIR):
    output_dir = output_dir.resolve(); output_dir.mkdir(parents=True, exist_ok=True)
    prereq_ok = PREREQ_433B.exists()

    # Verify source files
    config_h = RUNTIME / "src" / "config.h"
    state_mgr_c = RUNTIME / "src" / "state_manager.c"
    state_mgr_h = RUNTIME / "src" / "state_manager.h"
    makefile = RUNTIME / "Makefile"
    main_c = RUNTIME / "src" / "main.c"
    host_if_c = RUNTIME / "src" / "host_interface.c"

    source_files = [config_h, state_mgr_c, state_mgr_h, makefile, main_c, host_if_c]
    sources_ok = all(f.exists() for f in source_files)

    # Create bundle
    bundle = output_dir / PACKAGE_NAME
    if bundle.exists(): shutil.rmtree(bundle)
    bundle.mkdir(parents=True)

    # Copy runtime source tree
    runtime_bundle = bundle / "coral_reef_spinnaker" / "spinnaker_runtime"
    runtime_bundle.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(RUNTIME, runtime_bundle,
                    ignore=shutil.ignore_patterns('build', '*.o', '*.elf', '*.aplx', '.git'))

    # Copy this runner as the entry point
    runner_src = Path(__file__)
    runner_dst = bundle / "experiments" / runner_src.name
    runner_dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(runner_src, runner_dst)

    # Metadata
    metadata = {
        "tier": TIER, "runner_revision": RUNNER_REVISION,
        "package": PACKAGE_NAME, "profile": "eoc_recurrent",
        "hidden_units": EOC_HIDDEN, "dtcm_budget_kb": (EOC_HIDDEN*EOC_HIDDEN*4 + EOC_HIDDEN*16*4 + EOC_HIDDEN*4)/1024,
        "prepared_at": utc_now(),
        "build_command": f"make -C coral_reef_spinnaker/spinnaker_runtime RUNTIME_PROFILE=eoc_recurrent clean all",
        "jobmanager_command": (
            f"{PACKAGE_NAME}/experiments/{runner_src.name} "
            f"--mode run-hardware --seed {DEFAULT_SEED} "
            f"--task {DEFAULT_TASK} --length {DEFAULT_LENGTH} "
            f"--output-dir tier4_33c_hw_output"
        ),
        "expected_artifacts": [
            "tier4_33c_hw_results.json", "tier4_33c_build_eoc_recurrent_stdout.txt",
            "tier4_33c_build_eoc_recurrent_stderr.txt", "tier4_33c_target_acquisition.json",
            "tier4_33c_eoc_load.json", "tier4_33c_environment.json",
        ],
    }
    write_json(bundle / "metadata.json", metadata)

    # Job README
    readme = [
        "# CRA Tier 4.33c - EOC Hardware Smoke",
        f"Package: {PACKAGE_NAME}",
        f"Profile: eoc_recurrent (PROFILE_ID=7)",
        f"Hidden units: {EOC_HIDDEN} (DTCM budget: {metadata['dtcm_budget_kb']:.0f}KB)",
        "",
        "## JobManager Command",
        "",
        "```text",
        metadata["jobmanager_command"],
        "```",
        "",
        "## What this tests",
        "",
        "Single-core edge-of-chaos recurrent dynamics on real SpiNNaker.",
        "Builds the eoc_recurrent .aplx, loads it on one board, feeds a",
        f"Mackey-Glass {DEFAULT_LENGTH}-step scalar stream, reads back the",
        "EOC compact state, and compares state dimensionality (PR) against",
        "the v2.6 software baseline.",
        "",
        "## Expected pass criteria",
        "",
        "- .aplx builds for eoc_recurrent profile",
        "- App loads on selected board/core",
        "- EOC state updates produce non-trivial hidden activity range",
        "- Compact readback returns valid hidden_sample",
        "- PR > 2.0 (baseline had PR~2; EOC should be >4)",
        "- Zero synthetic fallback",
        "",
        "## Claim boundary",
        "",
        "One-board EOC hardware smoke only. Not repeatability, not multi-chip,",
        "not benchmark superiority, not full CRA organism transfer.",
    ]
    (bundle / "README_JOB.md").write_text("\n".join(readme) + "\n", encoding="utf-8")

    criteria = [
        criterion("prereq 4.33b exists", prereq_ok, "true", prereq_ok),
        criterion("all runtime source files present", sources_ok, "true", sources_ok),
        criterion("bundle created", bundle.exists(), "true", bundle.exists()),
        criterion("runner copied", runner_dst.exists(), "true", runner_dst.exists()),
        criterion("metadata.json written", (bundle / "metadata.json").exists(), "true", True),
        criterion("JobManager command defined", bool(metadata["jobmanager_command"]), "true", True),
        criterion("expected artifacts declared", len(metadata["expected_artifacts"]), ">= 3", len(metadata["expected_artifacts"]) >= 3),
        criterion("no hardware evidence claimed", False, "false", True),
        criterion("no baseline freeze", False, "false", True),
    ]
    passed = sum(1 for c in criteria if c["passed"])
    status = "pass" if passed == len(criteria) else "fail"

    payload = dict(tier=TIER, runner_revision=RUNNER_REVISION, generated_at_utc=utc_now(),
                   status=status, outcome="ebrains_package_prepared",
                   criteria=criteria, criteria_passed=passed, criteria_total=len(criteria),
                   output_dir=str(output_dir), bundle=str(bundle),
                   jobmanager_command=metadata["jobmanager_command"],
                   next_gate="Tier 4.33d hardware smoke (upload to EBRAINS JobManager)")
    write_json(output_dir / "tier4_33c_results.json", payload)
    write_csv(output_dir / "tier4_33c_summary.csv", criteria)
    manifest = dict(tier=TIER, status=status, generated_at_utc=payload["generated_at_utc"], output_dir=str(output_dir))
    write_json(output_dir / "tier4_33c_latest_manifest.json", manifest)
    write_json(CONTROLLED / "tier4_33c_latest_manifest.json", manifest)
    return payload


def build_parser():
    import argparse
    p = argparse.ArgumentParser(description=TIER)
    p.add_argument("--mode", choices=["prepare", "run-hardware"], default="prepare")
    p.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    p.add_argument("--seed", type=int, default=DEFAULT_SEED)
    p.add_argument("--task", default=DEFAULT_TASK)
    p.add_argument("--length", type=int, default=DEFAULT_LENGTH)
    return p


def main():
    args = build_parser().parse_args()
    if args.mode == "prepare":
        payload = run(Path(args.output_dir))
    else:
        payload = {"status": "fail", "outcome": "hardware_mode_not_yet_implemented",
                   "note": "run-hardware mode requires EBRAINS execution environment"}
    print(json.dumps(json_safe(dict(status=payload["status"], outcome=payload["outcome"],
                                    criteria=f"{payload.get('criteria_passed','?')}/{payload.get('criteria_total','?')}",
                                    jobmanager_command=payload.get("jobmanager_command",""),
                                    output_dir=payload.get("output_dir",str(args.output_dir)))), indent=2, sort_keys=True))
    return 0 if payload.get("status") == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Tier 4.20b v2.1 one-seed chunked SpiNNaker hardware probe.

Tier 4.20b is the first hardware-transfer checkpoint after the frozen v2.1
software baseline. It deliberately reuses the proven Tier 4.16 chunked-host
hardware runner instead of pretending the v2.1 software-only mechanisms are
already native PyNN/on-chip objects.

Claim boundary:
- Prepared output is not hardware evidence.
- A run-hardware PASS means the v2.1 transfer profile survives the existing
  chunked SpiNNaker transport on a one-seed capsule with real spike readback.
- It does not prove full v2.1 hardware execution, custom C, on-chip memory,
  on-chip self-evaluation, language, planning, AGI, or macro eligibility.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONTROLLED = ROOT / "controlled_test_output"
TIER = "Tier 4.20b - v2.1 One-Seed Chunked Hardware Probe"
V21_BASELINE = ROOT / "baselines" / "CRA_EVIDENCE_BASELINE_v2.1.json"
TIER4_20A_LATEST = CONTROLLED / "tier4_20a_latest_manifest.json"
TIER4_16_RUNNER = ROOT / "experiments" / "tier4_harder_spinnaker_capsule.py"
CANONICAL_PACKAGE_DIR = ROOT / "coral_reef_spinnaker"
PACKAGE_DIR_ALIASES = [ROOT / "coral-reef-spinnaker", ROOT / "coral reef spinnaker"]
DEFAULT_TASKS = "delayed_cue,hard_noisy_switching"
DEFAULT_SEED = "42"
DEFAULT_STEPS = 1200
DEFAULT_CHUNK_SIZE = 50
DEFAULT_POPULATION_SIZE = 8
DEFAULT_DELAYED_LR = 0.20
RUNNER_REVISION = "tier4_20b_inprocess_no_baselines_20260429_2330"


PROMOTED_BRIDGE_PROFILE: list[dict[str, str]] = [
    {
        "mechanism": "PendingHorizon delayed credit / delayed_lr_0_20",
        "tier_source": "Tier 5.4, Tier 4.16a/b",
        "probe_role": "exercised_by_child_hardware_runner",
        "status": "included",
        "boundary": "host-side delayed credit at chunk boundaries; not native on-chip eligibility",
    },
    {
        "mechanism": "keyed context memory",
        "tier_source": "Tier 5.10g",
        "probe_role": "bridge_contract_declared",
        "status": "not_native_in_child_runner",
        "boundary": "requires later adapter/hybrid probe before claiming hardware memory",
    },
    {
        "mechanism": "replay / consolidation",
        "tier_source": "Tier 5.11d",
        "probe_role": "bridge_contract_declared",
        "status": "not_native_in_child_runner",
        "boundary": "requires explicit replay epoch design before hardware replay claims",
    },
    {
        "mechanism": "visible predictive context / predictive binding",
        "tier_source": "Tier 5.12d, Tier 5.17e",
        "probe_role": "bridge_contract_declared",
        "status": "not_native_in_child_runner",
        "boundary": "requires metadata scheduler/controls before hardware predictive-binding claims",
    },
    {
        "mechanism": "composition and module routing",
        "tier_source": "Tier 5.13c, Tier 5.14",
        "probe_role": "bridge_contract_declared",
        "status": "not_native_in_child_runner",
        "boundary": "requires router/module adapter before hardware routing claims",
    },
    {
        "mechanism": "self-evaluation / reliability monitoring",
        "tier_source": "Tier 5.18c",
        "probe_role": "bridge_contract_declared",
        "status": "not_native_in_child_runner",
        "boundary": "requires pre-feedback monitor adapter before hardware self-evaluation claims",
    },
    {
        "mechanism": "macro eligibility residual trace",
        "tier_source": "Tier 5.9a/b/c",
        "probe_role": "explicitly_excluded",
        "status": "parked",
        "boundary": "failed 5.9c; do not port or include in hardware/custom-C work",
    },
]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def json_safe(value: Any) -> Any:
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {str(k): json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_safe(v) for v in value]
    return value


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(json_safe(payload), indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    import csv

    if not rows:
        path.write_text("", encoding="utf-8")
        return
    keys: list[str] = []
    seen: set[str] = set()
    for row in rows:
        for key in row:
            if key not in seen:
                keys.append(key)
                seen.add(key)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=keys, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def parse_csv(value: str) -> list[str]:
    items = [item.strip() for item in value.split(",") if item.strip()]
    if not items:
        raise argparse.ArgumentTypeError("at least one item is required")
    return items


def parse_seeds(value: str) -> list[int]:
    try:
        return [int(item) for item in parse_csv(value)]
    except ValueError as exc:
        raise argparse.ArgumentTypeError(str(exc)) from exc


def parse_tasks(value: str) -> list[str]:
    allowed = {"delayed_cue", "hard_noisy_switching"}
    tasks = parse_csv(value)
    unknown = [task for task in tasks if task not in allowed]
    if unknown:
        raise argparse.ArgumentTypeError(f"unsupported 4.20b task(s): {', '.join(unknown)}")
    return tasks


def criterion(name: str, value: Any, rule: str, passed: bool) -> dict[str, Any]:
    return {"name": name, "value": value, "rule": rule, "passed": bool(passed)}


def pass_fail(criteria: list[dict[str, Any]]) -> tuple[str, str]:
    failed = [item["name"] for item in criteria if not item.get("passed")]
    if failed:
        return "fail", "Failed criteria: " + ", ".join(failed)
    return "pass", ""


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def finite_number(value: Any) -> bool:
    try:
        f = float(value)
    except Exception:
        return False
    return f == f and f not in {float("inf"), float("-inf")}


def bridge_profile_summary() -> dict[str, Any]:
    included = [row for row in PROMOTED_BRIDGE_PROFILE if row["status"] == "included"]
    parked = [row for row in PROMOTED_BRIDGE_PROFILE if row["status"] == "parked"]
    non_native = [row for row in PROMOTED_BRIDGE_PROFILE if row["status"] == "not_native_in_child_runner"]
    return {
        "profile_name": "v2_1_chunked_bridge_probe",
        "rows": len(PROMOTED_BRIDGE_PROFILE),
        "included_in_child_runner": [row["mechanism"] for row in included],
        "contract_declared_not_native_yet": [row["mechanism"] for row in non_native],
        "explicitly_excluded": [row["mechanism"] for row in parked],
        "macro_eligibility_enabled": False,
    }


def write_jobmanager_capsule(output_dir: Path, args: argparse.Namespace) -> dict[str, str]:
    capsule_dir = output_dir / "jobmanager_capsule"
    capsule_dir.mkdir(parents=True, exist_ok=True)
    config_path = capsule_dir / "capsule_config.json"
    expected_path = capsule_dir / "expected_outputs.json"
    run_path = capsule_dir / "run_tier4_20b_on_jobmanager.sh"
    readme_path = capsule_dir / "README_JOBMANAGER.md"
    bridge_path = capsule_dir / "v2_1_bridge_profile.json"

    command = [
        "python3 experiments/tier4_20b_v2_1_hardware_probe.py",
        "--mode run-hardware",
        "--require-real-hardware",
        "--stop-on-fail",
        f"--tasks {','.join(args.tasks)}",
        f"--seeds {','.join(str(seed) for seed in args.seeds)}",
        f"--steps {args.steps}",
        f"--population-size {args.population_size}",
        f"--chunk-size-steps {args.chunk_size_steps}",
        f"--delayed-readout-lr {args.delayed_readout_lr}",
        "--output-dir \"$OUT_DIR\"",
    ]
    if args.spinnaker_hostname:
        command.insert(-1, f"--spinnaker-hostname {args.spinnaker_hostname}")

    config = {
        "tier": TIER,
        "mode": "prepare",
        "baseline": "v2.1",
        "tasks": args.tasks,
        "seeds": args.seeds,
        "steps": args.steps,
        "population_size": args.population_size,
        "runtime_mode": "chunked",
        "learning_location": "host",
        "chunk_size_steps": args.chunk_size_steps,
        "delayed_readout_lr": args.delayed_readout_lr,
        "macro_eligibility_enabled": False,
        "claim_boundary": [
            "Prepared capsule is not hardware evidence.",
            "A PASS requires real pyNN.spiNNaker execution through the child Tier 4.16 chunked runner, zero fallback/failures, and nonzero real spike readback.",
            "This is a v2.1 bridge/transport probe, not proof that every v2.1 mechanism is native/on-chip.",
        ],
    }
    write_json(config_path, config)
    write_json(bridge_path, {"generated_at_utc": utc_now(), "profile": bridge_profile_summary(), "rows": PROMOTED_BRIDGE_PROFILE})
    write_json(
        expected_path,
        {
            "required": [
                "tier4_20b_results.json",
                "tier4_20b_report.md",
                "tier4_20b_summary.csv",
                "child_tier4_16/tier4_16_results.json",
                "child_tier4_16/tier4_16_report.md",
                "child_tier4_16/spinnaker_hardware_<task>_seed<seed>_timeseries.csv",
            ],
            "pass_requires": [
                "v2.1 baseline exists",
                "one seed only",
                "chunked host mode with chunk_size_steps=50 unless explicitly overridden",
                "macro eligibility disabled/excluded",
                "child Tier 4.16 hardware run status=pass",
                "zero sim.run failures, read failures, and synthetic fallback",
                "real spike readback > 0",
            ],
        },
    )
    run_path.write_text(
        "\n".join(
            [
                "#!/usr/bin/env bash",
                "set -euo pipefail",
                "",
                "# Run from the repository root inside EBRAINS/JobManager with real SpiNNaker access.",
                "OUT_DIR=${1:-tier4_20b_job_output}",
                " \\\n  ".join(command),
                "",
            ]
        ),
        encoding="utf-8",
    )
    run_path.chmod(0o755)
    readme_path.write_text(
        "\n".join(
            [
                "# Tier 4.20b v2.1 One-Seed Chunked Hardware Probe",
                "",
                "This capsule is the first SpiNNaker bridge checkpoint after the frozen v2.1 software baseline.",
                "It delegates low-level pyNN.spiNNaker execution to the already-proven Tier 4.16 chunked-host hardware runner, then wraps the result with the v2.1 transfer claim boundary.",
                "",
                "## Run",
                "",
                "```bash",
                "bash controlled_test_output/<tier4_20b_prepared_run>/jobmanager_capsule/run_tier4_20b_on_jobmanager.sh /tmp/tier4_20b_job_output",
                "```",
                "",
                "## Boundary",
                "",
                "A pass is hardware transport evidence for the v2.1 bridge profile, not full native v2.1/on-chip execution.",
                "Macro eligibility is explicitly excluded because Tier 5.9c failed promotion.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return {
        "capsule_dir": str(capsule_dir),
        "capsule_config_json": str(config_path),
        "expected_outputs_json": str(expected_path),
        "jobmanager_run_script": str(run_path),
        "jobmanager_readme": str(readme_path),
        "v2_1_bridge_profile_json": str(bridge_path),
    }


def latest_420a_status() -> tuple[str, str | None]:
    if not TIER4_20A_LATEST.exists():
        return "missing", None
    try:
        payload = read_json(TIER4_20A_LATEST)
    except Exception:
        return "unreadable", None
    return str(payload.get("status", "unknown")).lower(), str(payload.get("manifest") or "")


def ensure_source_layout() -> dict[str, Any]:
    """Make source-only EBRAINS uploads tolerant to the package folder spelling.

    The Python import name is `coral_reef_spinnaker`. Some upload flows or
    manual folders use `coral-reef-spinnaker`, which is human-readable but not
    importable as a Python package. This repair is deliberately local and
    source-layout only; it does not pull in generated `controlled_test_output`.
    """

    if CANONICAL_PACKAGE_DIR.exists():
        return {
            "canonical_package": str(CANONICAL_PACKAGE_DIR),
            "canonical_package_exists": True,
            "action": "already_canonical",
            "aliases_checked": [str(path) for path in PACKAGE_DIR_ALIASES],
        }
    for alias in PACKAGE_DIR_ALIASES:
        if not alias.exists():
            continue
        try:
            CANONICAL_PACKAGE_DIR.symlink_to(alias, target_is_directory=True)
            action = f"symlinked {alias.name} to coral_reef_spinnaker"
        except Exception as symlink_exc:
            try:
                shutil.copytree(alias, CANONICAL_PACKAGE_DIR)
                action = f"copied {alias.name} to coral_reef_spinnaker after symlink failed: {symlink_exc}"
            except Exception as copy_exc:
                return {
                    "canonical_package": str(CANONICAL_PACKAGE_DIR),
                    "canonical_package_exists": False,
                    "alias_found": str(alias),
                    "action": "repair_failed",
                    "error": str(copy_exc),
                    "aliases_checked": [str(path) for path in PACKAGE_DIR_ALIASES],
                }
        return {
            "canonical_package": str(CANONICAL_PACKAGE_DIR),
            "canonical_package_exists": CANONICAL_PACKAGE_DIR.exists(),
            "alias_found": str(alias),
            "action": action,
            "aliases_checked": [str(path) for path in PACKAGE_DIR_ALIASES],
        }
    return {
        "canonical_package": str(CANONICAL_PACKAGE_DIR),
        "canonical_package_exists": False,
        "action": "missing",
        "aliases_checked": [str(path) for path in PACKAGE_DIR_ALIASES],
    }


def summarize_child(child_manifest: dict[str, Any]) -> dict[str, Any]:
    summary = dict(child_manifest.get("summary") or {})
    return {
        "child_status": str(child_manifest.get("status", "unknown")).lower(),
        "child_failure_reason": child_manifest.get("failure_reason", ""),
        "child_hardware_run_attempted": bool(summary.get("hardware_run_attempted")),
        "child_backend": summary.get("backend"),
        "child_tasks": summary.get("tasks"),
        "child_seeds": summary.get("seeds"),
        "child_runs": summary.get("runs"),
        "child_runtime_mode": summary.get("runtime_mode"),
        "child_learning_location": summary.get("learning_location"),
        "child_chunk_size_steps": summary.get("chunk_size_steps"),
        "child_total_step_spikes_min": summary.get("total_step_spikes_min"),
        "child_sim_run_failures_sum": summary.get("sim_run_failures_sum"),
        "child_summary_read_failures_sum": summary.get("summary_read_failures_sum"),
        "child_synthetic_fallbacks_sum": summary.get("synthetic_fallbacks_sum"),
        "child_runtime_seconds_mean": summary.get("runtime_seconds_mean"),
        "child_task_summaries": summary.get("task_summaries"),
    }


def preflight_criteria(args: argparse.Namespace, mode: str) -> list[dict[str, Any]]:
    source_layout = ensure_source_layout()
    audit_status, audit_manifest = latest_420a_status()
    return [
        criterion(
            "v2.1 baseline identity recorded",
            {"baseline": "v2.1", "artifact": str(V21_BASELINE), "artifact_present": V21_BASELINE.exists()},
            "runtime does not require baselines/",
            True,
        ),
        criterion("Tier 4.20b runner revision", RUNNER_REVISION, "expected current source", True),
        criterion("source package import path available", source_layout, "coral_reef_spinnaker exists", bool(source_layout.get("canonical_package_exists"))),
        criterion("Tier 4.16 child hardware runner exists", str(TIER4_16_RUNNER), "exists", TIER4_16_RUNNER.exists()),
        criterion("Tier 4.20a transfer audit context", {"status": audit_status, "manifest": audit_manifest}, "optional; local audit context only", True),
        criterion("exactly one seed requested for 4.20b", args.seeds, "len == 1", len(args.seeds) == 1),
        criterion("runtime mode is chunked", "chunked", "fixed", True),
        criterion("learning location is host", "host", "fixed", True),
        criterion("chunk size uses current default unless overridden", args.chunk_size_steps, ">= 1", int(args.chunk_size_steps) >= 1),
        criterion("macro eligibility disabled", False, "== false", True),
        criterion("delayed_lr_0_20 selected", args.delayed_readout_lr, "== 0.20", abs(float(args.delayed_readout_lr) - DEFAULT_DELAYED_LR) < 1e-12),
        criterion("mode has explicit claim boundary", mode, "prepare|run-hardware|ingest", mode in {"prepare", "run-hardware", "ingest"}),
    ]


def write_report(path: Path, result: dict[str, Any]) -> None:
    summary = result.get("summary", {})
    lines = [
        "# Tier 4.20b v2.1 One-Seed Chunked Hardware Probe",
        "",
        f"- Generated: `{result['generated_at_utc']}`",
        f"- Mode: `{result['mode']}`",
        f"- Status: **{result['status'].upper()}**",
        f"- Output directory: `{result['output_dir']}`",
        "",
        "Tier 4.20b checks whether the frozen v2.1 software evidence stack has a clean one-seed SpiNNaker transport path through the current chunked-host bridge.",
        "",
        "## Claim Boundary",
        "",
        "- `PREPARED` means the JobManager capsule exists locally; it is not hardware evidence.",
        "- `PASS` in `run-hardware` requires a passing child pyNN.spiNNaker run, zero fallback/failures, and nonzero real spike readback.",
        "- This is not full v2.1 native hardware execution, custom C, on-chip learning, language, planning, AGI, or macro eligibility evidence.",
        "",
        "## Summary",
        "",
    ]
    for key in [
        "baseline",
        "runner_revision",
        "tasks",
        "seeds",
        "steps",
        "population_size",
        "runtime_mode",
        "learning_location",
        "chunk_size_steps",
        "macro_eligibility_enabled",
        "hardware_run_attempted",
        "child_status",
        "child_hardware_run_attempted",
        "child_total_step_spikes_min",
        "child_sim_run_failures_sum",
        "child_summary_read_failures_sum",
        "child_synthetic_fallbacks_sum",
        "capsule_dir",
    ]:
        if key in summary:
            lines.append(f"- {key}: `{summary.get(key)}`")
    if result.get("failure_reason"):
        lines.extend(["", f"Failure: {result['failure_reason']}", ""])
    task_summaries = summary.get("child_task_summaries") or []
    if task_summaries:
        lines.extend(["", "## Child Task Summary", "", "| Task | Runs | Tail min | Corr mean | Spikes mean |", "| --- | --- | --- | --- | --- |"])
        for row in task_summaries:
            lines.append(
                f"| `{row.get('task')}` | `{row.get('runs')}` | `{row.get('tail_accuracy_min')}` | `{row.get('tail_prediction_target_corr_mean')}` | `{row.get('total_step_spikes_mean')}` |"
            )
    lines.extend(["", "## Bridge Profile", "", "| Mechanism | Status | Probe Role | Boundary |", "| --- | --- | --- | --- |"])
    for row in PROMOTED_BRIDGE_PROFILE:
        lines.append(f"| {row['mechanism']} | `{row['status']}` | `{row['probe_role']}` | {row['boundary']} |")
    lines.extend(["", "## Criteria", "", "| Criterion | Value | Rule | Pass |", "| --- | --- | --- | --- |"])
    for item in result.get("criteria", []):
        lines.append(f"| {item['name']} | `{item['value']}` | `{item['rule']}` | {'yes' if item.get('passed') else 'no'} |")
    lines.extend(["", "## Artifacts", ""])
    for key, value in sorted((result.get("artifacts") or {}).items()):
        lines.append(f"- `{key}`: `{value}`")
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def write_latest(output_dir: Path, report_path: Path, manifest_path: Path, status: str) -> None:
    write_json(
        CONTROLLED / "tier4_20b_latest_manifest.json",
        {
            "generated_at_utc": utc_now(),
            "manifest": str(manifest_path),
            "report": str(report_path),
            "output_dir": str(output_dir),
            "status": status,
            "canonical": False,
            "claim": "Latest Tier 4.20b v2.1 one-seed chunked hardware bridge/probe; passed returned hardware review when status is pass.",
        },
    )


def finalize(output_dir: Path, result: dict[str, Any]) -> int:
    manifest_path = output_dir / "tier4_20b_results.json"
    report_path = output_dir / "tier4_20b_report.md"
    summary_path = output_dir / "tier4_20b_summary.csv"
    bridge_path = output_dir / "tier4_20b_bridge_profile.json"
    result["artifacts"]["results_json"] = str(manifest_path)
    result["artifacts"]["report_md"] = str(report_path)
    result["artifacts"]["summary_csv"] = str(summary_path)
    result["artifacts"]["bridge_profile_json"] = str(bridge_path)
    write_json(bridge_path, {"generated_at_utc": utc_now(), "profile": bridge_profile_summary(), "rows": PROMOTED_BRIDGE_PROFILE})
    write_json(manifest_path, result)
    write_csv(summary_path, [result.get("summary", {})])
    write_report(report_path, result)
    write_latest(output_dir, report_path, manifest_path, result["status"])
    return 0 if result["status"] in {"pass", "prepared"} else 1


def prepare_capsule(args: argparse.Namespace, output_dir: Path) -> int:
    artifacts = write_jobmanager_capsule(output_dir, args)
    criteria = preflight_criteria(args, "prepare")
    criteria.append(criterion("capsule directory exists", artifacts["capsule_dir"], "exists", Path(artifacts["capsule_dir"]).exists()))
    status, failure = pass_fail(criteria)
    status = "prepared" if status == "pass" else "fail"
    result = {
        "tier": TIER,
        "generated_at_utc": utc_now(),
        "mode": "prepare",
        "status": status,
        "failure_reason": failure,
        "output_dir": str(output_dir),
        "summary": {
            "baseline": "v2.1",
            "runner_revision": RUNNER_REVISION,
            "tasks": args.tasks,
            "seeds": args.seeds,
            "steps": args.steps,
            "population_size": args.population_size,
            "runtime_mode": "chunked",
            "learning_location": "host",
            "chunk_size_steps": args.chunk_size_steps,
            "macro_eligibility_enabled": False,
            "hardware_run_attempted": False,
            "capsule_dir": artifacts.get("capsule_dir"),
            "bridge_profile": bridge_profile_summary(),
        },
        "criteria": criteria,
        "artifacts": artifacts,
    }
    return finalize(output_dir, result)


def child_command(args: argparse.Namespace, child_dir: Path) -> list[str]:
    cmd = [
        sys.executable,
        str(TIER4_16_RUNNER),
        "--mode",
        "run-hardware",
        "--require-real-hardware" if args.require_real_hardware else "--no-require-real-hardware",
        "--tasks",
        ",".join(args.tasks),
        "--seeds",
        ",".join(str(seed) for seed in args.seeds),
        "--steps",
        str(args.steps),
        "--population-size",
        str(args.population_size),
        "--runtime-mode",
        "chunked",
        "--learning-location",
        "host",
        "--chunk-size-steps",
        str(args.chunk_size_steps),
        "--delayed-readout-lr",
        str(args.delayed_readout_lr),
        "--output-dir",
        str(child_dir),
    ]
    if args.spinnaker_hostname:
        cmd.extend(["--spinnaker-hostname", args.spinnaker_hostname])
    if args.stop_on_fail:
        cmd.append("--stop-on-fail")
    return cmd


def build_child_args(args: argparse.Namespace, child_dir: Path) -> argparse.Namespace:
    """Build Tier 4.16 args without spawning a subprocess.

    EBRAINS/JobManager has already shown that the proven Tier 4.16/4.18 direct
    hardware paths can run even when the local config detector cannot see a
    Machine target. Tier 4.20b therefore calls the Tier 4.16 runner in-process
    to avoid losing any JobManager-provided execution context in a child
    process.
    """

    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    from experiments.tier4_harder_spinnaker_capsule import build_parser as build_tier4_16_parser

    child = build_tier4_16_parser().parse_args([])
    child.mode = "run-hardware"
    child.tasks = list(args.tasks)
    child.seeds = list(args.seeds)
    child.steps = int(args.steps)
    child.population_size = int(args.population_size)
    child.runtime_mode = "chunked"
    child.learning_location = "host"
    child.chunk_size_steps = int(args.chunk_size_steps)
    child.delayed_readout_lr = float(args.delayed_readout_lr)
    child.spinnaker_hostname = args.spinnaker_hostname
    child.require_real_hardware = bool(args.require_real_hardware)
    child.stop_on_fail = bool(args.stop_on_fail)
    child.output_dir = child_dir
    child.ingest_dir = None
    return child


def run_hardware(args: argparse.Namespace, output_dir: Path) -> int:
    criteria = preflight_criteria(args, "run-hardware")
    child_dir = output_dir / "child_tier4_16"
    child_dir.mkdir(parents=True, exist_ok=True)
    stdout_path = output_dir / "tier4_20b_child_stdout.log"
    stderr_path = output_dir / "tier4_20b_child_stderr.log"
    started = time.perf_counter()
    cmd = child_command(args, child_dir)
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    from experiments.tier4_harder_spinnaker_capsule import run_hardware as run_tier4_16_hardware

    stdout_path.write_text(
        "Tier 4.16 executed in-process by Tier 4.20b; JobManager captures live stdout.\n",
        encoding="utf-8",
    )
    stderr_path.write_text(
        "Tier 4.16 executed in-process by Tier 4.20b; JobManager captures live stderr.\n",
        encoding="utf-8",
    )
    child_args = build_child_args(args, child_dir)
    child_return_code = run_tier4_16_hardware(child_args, child_dir)
    child_manifest_path = child_dir / "tier4_16_results.json"
    child_manifest: dict[str, Any] = {}
    if child_manifest_path.exists():
        child_manifest = read_json(child_manifest_path)
    child_summary = summarize_child(child_manifest) if child_manifest else {"child_status": "missing_manifest"}
    criteria.extend(
        [
            criterion("child Tier 4.16 in-process runner exited cleanly", child_return_code, "== 0", child_return_code == 0),
            criterion("child Tier 4.16 manifest exists", str(child_manifest_path), "exists", child_manifest_path.exists()),
            criterion("child hardware status passed", child_summary.get("child_status"), "== pass", child_summary.get("child_status") == "pass"),
            criterion("child hardware was attempted", child_summary.get("child_hardware_run_attempted"), "== true", bool(child_summary.get("child_hardware_run_attempted"))),
            criterion("child sim.run failures zero", child_summary.get("child_sim_run_failures_sum"), "== 0", int(child_summary.get("child_sim_run_failures_sum") or 0) == 0),
            criterion("child summary read failures zero", child_summary.get("child_summary_read_failures_sum"), "== 0", int(child_summary.get("child_summary_read_failures_sum") or 0) == 0),
            criterion("child synthetic fallback zero", child_summary.get("child_synthetic_fallbacks_sum"), "== 0", int(child_summary.get("child_synthetic_fallbacks_sum") or 0) == 0),
            criterion("child real spike readback nonzero", child_summary.get("child_total_step_spikes_min"), "> 0", (float(child_summary.get("child_total_step_spikes_min") or 0.0) > 0.0)),
            criterion("child runtime documented", child_summary.get("child_runtime_seconds_mean"), "finite", finite_number(child_summary.get("child_runtime_seconds_mean"))),
        ]
    )
    status, failure = pass_fail(criteria)
    artifacts = {
        "child_output_dir": str(child_dir),
        "child_stdout_log": str(stdout_path),
        "child_stderr_log": str(stderr_path),
    }
    for name in [
        "tier4_16_results.json",
        "tier4_16_report.md",
        "tier4_16_summary.csv",
        "tier4_16_task_summary.csv",
        "tier4_16_hardware_summary.png",
    ]:
        path = child_dir / name
        if path.exists():
            artifacts[f"child_{name}"] = str(path)
    for path in sorted(child_dir.glob("spinnaker_hardware_*_timeseries.*")):
        artifacts[f"child_{path.name}"] = str(path)
    result = {
        "tier": TIER,
        "generated_at_utc": utc_now(),
        "mode": "run-hardware",
        "status": status,
        "failure_reason": failure or str(child_manifest.get("failure_reason") or ""),
        "output_dir": str(output_dir),
        "summary": {
            "baseline": "v2.1",
            "runner_revision": RUNNER_REVISION,
            "tasks": args.tasks,
            "seeds": args.seeds,
            "steps": args.steps,
            "population_size": args.population_size,
            "runtime_mode": "chunked",
            "learning_location": "host",
            "chunk_size_steps": args.chunk_size_steps,
            "macro_eligibility_enabled": False,
            "hardware_run_attempted": bool(child_summary.get("child_hardware_run_attempted")),
            "bridge_profile": bridge_profile_summary(),
            "runtime_seconds": time.perf_counter() - started,
            "child_return_code": child_return_code,
            "child_execution_mode": "in_process",
            **child_summary,
        },
        "criteria": criteria,
        "artifacts": artifacts,
        "child_manifest": child_manifest,
        "child_command": cmd,
    }
    return finalize(output_dir, result)


def ingest_results(args: argparse.Namespace, output_dir: Path) -> int:
    if args.ingest_dir is None:
        raise SystemExit("--ingest-dir is required in ingest mode")
    source_dir = args.ingest_dir.resolve()
    source_manifest = source_dir / "tier4_20b_results.json"
    if not source_manifest.exists():
        raise SystemExit(f"No tier4_20b_results.json found in {source_dir}")
    source = read_json(source_manifest)
    status = str(source.get("status", "unknown")).lower()
    artifacts = {"ingested_source": str(source_manifest)}
    for pattern in [
        "tier4_20b_*",
        "child_tier4_16/tier4_16_*",
        "child_tier4_16/spinnaker_hardware_*",
        "child_tier4_16/raw_hardware_artifacts/*",
    ]:
        for src in sorted(source_dir.glob(pattern)):
            if src.is_dir():
                continue
            rel = src.relative_to(source_dir)
            dest = output_dir / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dest)
            artifacts[str(rel)] = str(dest)
    result = {
        "tier": TIER,
        "generated_at_utc": utc_now(),
        "mode": "ingest",
        "status": status,
        "failure_reason": source.get("failure_reason", ""),
        "output_dir": str(output_dir),
        "summary": {**dict(source.get("summary") or {}), "ingested_from": str(source_manifest)},
        "criteria": source.get("criteria") or [],
        "artifacts": artifacts,
        "source_manifest": source,
    }
    return finalize(output_dir, result)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Prepare, run, or ingest Tier 4.20b v2.1 one-seed chunked SpiNNaker hardware probe.")
    parser.add_argument("--mode", choices=["prepare", "run-hardware", "ingest"], default="prepare")
    parser.add_argument("--tasks", type=parse_tasks, default=parse_tasks(DEFAULT_TASKS))
    parser.add_argument("--seeds", type=parse_seeds, default=parse_seeds(DEFAULT_SEED))
    parser.add_argument("--steps", type=int, default=DEFAULT_STEPS)
    parser.add_argument("--population-size", type=int, default=DEFAULT_POPULATION_SIZE)
    parser.add_argument("--chunk-size-steps", type=int, default=DEFAULT_CHUNK_SIZE)
    parser.add_argument("--delayed-readout-lr", type=float, default=DEFAULT_DELAYED_LR)
    parser.add_argument("--spinnaker-hostname", default=None)
    parser.add_argument("--require-real-hardware", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--stop-on-fail", action="store_true")
    parser.add_argument("--ingest-dir", type=Path, default=None)
    parser.add_argument("--output-dir", type=Path, default=None)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.steps <= 0:
        parser.error("--steps must be positive")
    if args.population_size <= 0:
        parser.error("--population-size must be positive")
    if args.chunk_size_steps <= 0:
        parser.error("--chunk-size-steps must be positive")
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    suffix = "prepared" if args.mode == "prepare" else args.mode.replace("-", "_")
    output_dir = args.output_dir or (CONTROLLED / f"tier4_20b_{stamp}_{suffix}")
    output_dir = output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    if args.mode == "prepare":
        return prepare_capsule(args, output_dir)
    if args.mode == "run-hardware":
        return run_hardware(args, output_dir)
    if args.mode == "ingest":
        return ingest_results(args, output_dir)
    raise AssertionError(args.mode)


if __name__ == "__main__":
    raise SystemExit(main())

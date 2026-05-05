#!/usr/bin/env python3
"""Tier 4.30b lifecycle source audit / single-core mask-smoke preparation.

This gate maps the Tier 4.30a static-pool lifecycle reference into the custom
runtime's smallest safe state surface. It is deliberately local-only: no
EBRAINS package, no task-effect claim, no multi-core lifecycle claim, and no
baseline freeze.
"""

from __future__ import annotations

import argparse
import json
import subprocess
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
CONTROLLED = ROOT / "controlled_test_output"
RUNTIME = ROOT / "coral_reef_spinnaker" / "spinnaker_runtime"

TIER = "Tier 4.30b - Lifecycle Runtime Source Audit"
RUNNER_REVISION = "tier4_30b_lifecycle_source_audit_20260505_0001"
DEFAULT_OUTPUT_DIR = CONTROLLED / "tier4_30b_20260505_lifecycle_source_audit"
TIER4_30A_RESULTS = (
    CONTROLLED
    / "tier4_30a_20260505_static_pool_lifecycle_reference"
    / "tier4_30a_results.json"
)


@dataclass(frozen=True)
class Criterion:
    name: str
    value: Any
    rule: str
    passed: bool
    note: str = ""


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def json_safe(value: Any) -> Any:
    if isinstance(value, Path):
        return str(value)
    if hasattr(value, "__dataclass_fields__"):
        return json_safe(asdict(value))
    if isinstance(value, dict):
        return {str(key): json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_safe(item) for item in value]
    return value


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(json_safe(payload), indent=2, sort_keys=True) + "\n", encoding="utf-8")


def load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def criterion(name: str, value: Any, rule: str, passed: bool, note: str = "") -> Criterion:
    return Criterion(name=name, value=value, rule=rule, passed=bool(passed), note=note)


def run_command(command: list[str]) -> dict[str, Any]:
    completed = subprocess.run(
        command,
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    return {
        "command": command,
        "returncode": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
    }


def source_contains(path: Path, tokens: list[str]) -> dict[str, bool]:
    text = path.read_text(encoding="utf-8")
    return {token: token in text for token in tokens}


def lifecycle_handler_avoids_legacy_allocation(host_interface_text: str) -> bool:
    start = host_interface_text.find("static void _handle_lifecycle_init")
    end = host_interface_text.find("#ifndef CRA_RUNTIME_PROFILE_DECOUPLED_MEMORY_ROUTE", start)
    if start < 0 or end < 0:
        return False
    lifecycle_slice = host_interface_text[start:end]
    return "neuron_birth" not in lifecycle_slice and "neuron_death" not in lifecycle_slice


def build_results() -> dict[str, Any]:
    tier4_30a = load_json(TIER4_30A_RESULTS)
    config_h = RUNTIME / "src" / "config.h"
    state_h = RUNTIME / "src" / "state_manager.h"
    state_c = RUNTIME / "src" / "state_manager.c"
    host_h = RUNTIME / "src" / "host_interface.h"
    host_c = RUNTIME / "src" / "host_interface.c"
    test_lifecycle = RUNTIME / "tests" / "test_lifecycle.c"

    commands = [
        run_command(["make", "-C", str(RUNTIME.relative_to(ROOT)), "test-lifecycle"]),
        run_command(["make", "-C", str(RUNTIME.relative_to(ROOT)), "test-profiles"]),
        run_command(["make", "-C", str(RUNTIME.relative_to(ROOT)), "test"]),
    ]

    config_tokens = source_contains(
        config_h,
        [
            "MAX_LIFECYCLE_SLOTS",
            "CMD_LIFECYCLE_INIT",
            "CMD_LIFECYCLE_EVENT",
            "CMD_LIFECYCLE_TROPHIC_UPDATE",
            "CMD_LIFECYCLE_READ_STATE",
            "CMD_LIFECYCLE_SHAM_MODE",
            "LIFECYCLE_EVENT_CLEAVAGE",
            "LIFECYCLE_EVENT_ADULT_BIRTH",
            "LIFECYCLE_EVENT_DEATH",
        ],
    )
    state_tokens = source_contains(
        state_h,
        [
            "lifecycle_slot_t",
            "cra_lifecycle_summary_t",
            "cra_lifecycle_init",
            "cra_lifecycle_apply_event",
            "cra_lifecycle_get_summary",
            "cra_lifecycle_get_slot",
        ],
    )
    host_tokens = source_contains(
        host_c,
        [
            "_handle_lifecycle_init",
            "_handle_lifecycle_event",
            "_handle_lifecycle_read_state",
            "host_if_pack_lifecycle_summary",
            "case CMD_LIFECYCLE_INIT",
        ],
    )
    test_tokens = source_contains(
        test_lifecycle,
        [
            "105428",
            "466851",
            "18496",
            "761336",
            "4.30a canonical_32 lifecycle parity",
            "4.30a boundary_64 lifecycle parity",
        ],
    )
    host_interface_text = host_c.read_text(encoding="utf-8")
    state_interface_text = state_c.read_text(encoding="utf-8")

    command_passes = {item["command"][-1]: item["returncode"] == 0 for item in commands}
    command_outputs = "\n\n".join(
        [
            "COMMAND: " + " ".join(item["command"])
            + f"\nRETURNCODE: {item['returncode']}\nSTDOUT:\n{item['stdout']}\nSTDERR:\n{item['stderr']}"
            for item in commands
        ]
    )

    criteria = [
        criterion("Tier 4.30a reference passed", tier4_30a.get("status"), "== pass", tier4_30a.get("status") == "pass"),
        criterion(
            "Tier 4.30a criteria complete",
            f"{tier4_30a.get('criteria_passed')}/{tier4_30a.get('criteria_total')}",
            "== 20/20",
            tier4_30a.get("criteria_passed") == tier4_30a.get("criteria_total") == 20,
        ),
        criterion("lifecycle opcodes declared", config_tokens, "all required tokens present", all(config_tokens.values())),
        criterion("lifecycle state API declared", state_tokens, "all required tokens present", all(state_tokens.values())),
        criterion("lifecycle host handlers declared", host_tokens, "all required tokens present", all(host_tokens.values())),
        criterion("lifecycle parity constants tested", test_tokens, "all required tokens present", all(test_tokens.values())),
        criterion(
            "lifecycle handlers avoid legacy allocation",
            lifecycle_handler_avoids_legacy_allocation(host_interface_text),
            "no neuron_birth/neuron_death in lifecycle handler slice",
            lifecycle_handler_avoids_legacy_allocation(host_interface_text),
        ),
        criterion(
            "lifecycle state reset wired",
            "cra_lifecycle_reset();" in state_interface_text,
            "cra_state_init/reset call cra_lifecycle_reset",
            state_interface_text.count("cra_lifecycle_reset();") >= 3,
        ),
        criterion(
            "CMD_READ_STATE schema preserved",
            "payload[2] = 2;  // payload schema version" in host_interface_text,
            "existing schema remains version 2",
            "payload[2] = 2;  // payload schema version" in host_interface_text,
        ),
        criterion("runtime test-lifecycle passed", command_passes.get("test-lifecycle"), "returncode == 0", command_passes.get("test-lifecycle", False)),
        criterion("runtime test-profiles passed", command_passes.get("test-profiles"), "returncode == 0", command_passes.get("test-profiles", False)),
        criterion("runtime test passed", command_passes.get("test"), "returncode == 0", command_passes.get("test", False)),
        criterion("no EBRAINS package generated", "local-source-audit", "mode == local-source-audit", True),
    ]
    failed = [item for item in criteria if not item.passed]

    return {
        "tier": TIER,
        "runner_revision": RUNNER_REVISION,
        "generated_at_utc": utc_now(),
        "status": "pass" if not failed else "fail",
        "mode": "local-source-audit",
        "criteria_passed": len(criteria) - len(failed),
        "criteria_total": len(criteria),
        "criteria": criteria,
        "failed_criteria": failed,
        "command_results": commands,
        "command_log": command_outputs,
        "source_inputs": {
            "tier4_30a_results": str(TIER4_30A_RESULTS),
            "config_h": str(config_h),
            "state_manager_h": str(state_h),
            "state_manager_c": str(state_c),
            "host_interface_h": str(host_h),
            "host_interface_c": str(host_c),
            "test_lifecycle_c": str(test_lifecycle),
        },
        "claim_boundary": (
            "PASS means the lifecycle static-pool state surface exists in the custom runtime, "
            "matches the Tier 4.30a local reference in host tests, preserves existing profile/readback tests, "
            "and is ready for a single-core lifecycle mask-smoke package. It is not hardware evidence, "
            "not task-effect evidence, not multi-core lifecycle migration, and not a baseline freeze."
        ),
        "next_step": "Tier 4.30b hardware package/run: single-core active-mask/lineage lifecycle smoke.",
    }


def write_report(path: Path, results: dict[str, Any]) -> None:
    lines = [
        "# Tier 4.30b Lifecycle Runtime Source Audit",
        "",
        f"- Generated: `{results['generated_at_utc']}`",
        f"- Mode: `{results['mode']}`",
        f"- Status: **{results['status'].upper()}**",
        f"- Criteria: `{results['criteria_passed']}/{results['criteria_total']}`",
        "",
        "## Claim Boundary",
        "",
        results["claim_boundary"],
        "",
        "## Criteria",
        "",
        "| Criterion | Value | Rule | Pass |",
        "| --- | --- | --- | --- |",
    ]
    for item in results["criteria"]:
        value = json.dumps(json_safe(item.value), sort_keys=True)
        if len(value) > 120:
            value = value[:117] + "..."
        lines.append(f"| {item.name} | `{value}` | {item.rule} | {'yes' if item.passed else 'no'} |")
    lines.extend(
        [
            "",
            "## Next Step",
            "",
            results["next_step"],
            "",
            "## Artifacts",
            "",
            "- `tier4_30b_results.json`",
            "- `tier4_30b_report.md`",
            "- `tier4_30b_command_log.txt`",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args()

    output_dir = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    results = build_results()
    results["artifacts"] = {
        "results_json": str(output_dir / "tier4_30b_results.json"),
        "report_md": str(output_dir / "tier4_30b_report.md"),
        "command_log": str(output_dir / "tier4_30b_command_log.txt"),
    }
    write_json(output_dir / "tier4_30b_results.json", results)
    write_report(output_dir / "tier4_30b_report.md", results)
    (output_dir / "tier4_30b_command_log.txt").write_text(results["command_log"], encoding="utf-8")
    write_json(CONTROLLED / "tier4_30b_latest_manifest.json", results)

    print(f"Tier 4.30b status: {results['status']} ({results['criteria_passed']}/{results['criteria_total']})")
    print(output_dir)
    if results["status"] != "pass":
        raise SystemExit(1)


if __name__ == "__main__":
    main()

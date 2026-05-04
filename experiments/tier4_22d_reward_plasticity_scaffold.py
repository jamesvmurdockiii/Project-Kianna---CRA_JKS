#!/usr/bin/env python3
"""Tier 4.22d reward/plasticity scaffold for the custom C runtime.

Tier 4.22c gave the runtime bounded persistent state. Tier 4.22d adds the first
audited reward/plasticity path inside that runtime:

- synaptic eligibility traces
- trace-gated dopamine modulation
- fixed-point trace decay
- one-shot dopamine application
- runtime-owned readout reward update

This is still a local/custom-C scaffold gate, not hardware evidence and not a
full learning parity result.
"""

from __future__ import annotations

import argparse
import csv
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
CONTROLLED = ROOT / "controlled_test_output"
RUNTIME = ROOT / "coral_reef_spinnaker" / "spinnaker_runtime"
SRC = RUNTIME / "src"
TESTS = RUNTIME / "tests"
TIER = "Tier 4.22d - Reward/Plasticity Runtime Scaffold"
RUNNER_REVISION = "tier4_22d_reward_plasticity_scaffold_20260430_0000"
TIER4_22C_LATEST = CONTROLLED / "tier4_22c_latest_manifest.json"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
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


def criterion(name: str, value: Any, rule: str, passed: bool, note: str = "") -> dict[str, Any]:
    return {"name": name, "value": value, "rule": rule, "passed": bool(passed), "note": note}


def latest_status(path: Path) -> tuple[str, str | None]:
    if not path.exists():
        return "missing", None
    try:
        payload = read_json(path)
    except Exception as exc:
        return f"unreadable:{type(exc).__name__}", None
    return str(payload.get("status", "unknown")).lower(), str(payload.get("manifest") or "")


def markdown_value(value: Any) -> str:
    if isinstance(value, float):
        return f"{value:.6g}"
    if isinstance(value, (dict, list, tuple)):
        return json.dumps(value, sort_keys=True)
    return str(value)


def run_host_tests() -> dict[str, Any]:
    cmd = ["make", "-C", str(RUNTIME), "clean-host", "test"]
    proc = subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True, check=False)
    return {
        "command": " ".join(cmd),
        "returncode": proc.returncode,
        "stdout": proc.stdout,
        "stderr": proc.stderr,
        "passed": proc.returncode == 0 and "=== ALL TESTS PASSED ===" in proc.stdout,
    }


def static_checks() -> list[dict[str, Any]]:
    config = read_text(SRC / "config.h")
    syn_h = read_text(SRC / "synapse_manager.h")
    syn_c = read_text(SRC / "synapse_manager.c")
    state_h = read_text(SRC / "state_manager.h")
    state_c = read_text(SRC / "state_manager.c")
    main_c = read_text(SRC / "main.c")
    host_c = read_text(SRC / "host_interface.c")
    tests = read_text(TESTS / "test_runtime.c")
    return [
        criterion("eligibility trace field exists", "eligibility_trace", "in synapse_t", "eligibility_trace" in syn_h),
        criterion("trace constants defined", "DEFAULT_ELIGIBILITY_DECAY/DEFAULT_TRACE_INCREMENT/MAX_ELIGIBILITY_TRACE", "in config.h", all(token in config for token in ["DEFAULT_ELIGIBILITY_DECAY", "DEFAULT_TRACE_INCREMENT", "MAX_ELIGIBILITY_TRACE"])),
        criterion("trace increments on spike delivery", "synapse_deliver_spike", "increments eligibility trace", "s->eligibility_trace + DEFAULT_TRACE_INCREMENT" in syn_c),
        criterion("trace decay function exists", "synapse_decay_traces_all", "declared and implemented", "synapse_decay_traces_all" in syn_h and "void synapse_decay_traces_all" in syn_c),
        criterion("dopamine is trace-gated", "delta_w = FP_MUL(dopamine_level, s->eligibility_trace)", "dopamine * trace", "FP_MUL(dopamine_level, s->eligibility_trace)" in syn_c),
        criterion("dopamine path is one-shot", "g_dopamine_level = 0", "main clears after modulation", "g_dopamine_level = 0;" in main_c),
        criterion("timer decays traces", "DEFAULT_ELIGIBILITY_DECAY", "main decays traces each timer tick", "synapse_decay_traces_all(DEFAULT_ELIGIBILITY_DECAY)" in main_c),
        criterion("dopamine signed fixed-point", "int32_t g_dopamine_level", "supports negative reward", "int32_t g_dopamine_level" in main_c and "extern int32_t g_dopamine_level" in host_c),
        criterion("runtime readout reward update exists", "cra_state_apply_reward_to_readout", "declared and implemented", "cra_state_apply_reward_to_readout" in state_h and "int32_t cra_state_apply_reward_to_readout" in state_c),
        criterion("eligibility host test exists", "test_synapse_eligibility_modulation", "test_runtime.c covers trace-gated dopamine", "test_synapse_eligibility_modulation" in tests),
        criterion("reward readout host test exists", "test_state_reward_readout_update", "test_runtime.c covers reward update", "test_state_reward_readout_update" in tests),
    ]


def plasticity_contract_rows() -> list[dict[str, Any]]:
    return [
        {
            "mechanism": "synaptic_eligibility_trace",
            "runtime_owner": "custom_c_runtime",
            "implementation": "eligibility_trace field on synapse_t",
            "causal_rule": "trace increments when a pre-synaptic spike is delivered to a post-synaptic target",
            "current_gate": "host C unit tests and static checks",
            "future_gate": "hardware build/run and learning parity against chunked reference",
        },
        {
            "mechanism": "trace_gated_dopamine",
            "runtime_owner": "custom_c_runtime",
            "implementation": "delta_w = dopamine_level * eligibility_trace",
            "causal_rule": "dopamine without a causal trace does not move the weight",
            "current_gate": "host C unit tests and static checks",
            "future_gate": "reward timing/parity under continuous task streams",
        },
        {
            "mechanism": "fixed_point_trace_decay",
            "runtime_owner": "custom_c_runtime",
            "implementation": "synapse_decay_traces_all(DEFAULT_ELIGIBILITY_DECAY)",
            "causal_rule": "traces decay on the runtime timer path",
            "current_gate": "host C unit tests and static checks",
            "future_gate": "scale audit to avoid sweeping all synapses at unacceptable sizes",
        },
        {
            "mechanism": "readout_reward_update",
            "runtime_owner": "custom_c_runtime",
            "implementation": "cra_state_apply_reward_to_readout",
            "causal_rule": "reward updates fixed-point readout weight and bias from last feature/prediction",
            "current_gate": "host C unit tests and static checks",
            "future_gate": "compare behavior against v2.1/chunked reference on delayed_cue and hard_noisy_switching",
        },
    ]


def write_report(path: Path, result: dict[str, Any]) -> None:
    summary = result["summary"]
    lines = [
        "# Tier 4.22d Reward/Plasticity Runtime Scaffold",
        "",
        f"- Generated: `{result['generated_at_utc']}`",
        f"- Status: **{result['status'].upper()}**",
        f"- Output directory: `{result['output_dir']}`",
        "",
        "Tier 4.22d adds the first custom-C reward/plasticity scaffold after the persistent-state gate. This is intentionally local and bounded: it proves trace-gated reward updates exist and are test-covered before a hardware allocation is spent.",
        "",
        "## Summary",
        "",
        f"- Tier 4.22c latest status: `{summary['tier4_22c_status']}`",
        f"- Host C tests passed: `{summary['host_tests_passed']}`",
        f"- Static plasticity checks passed: `{summary['static_checks_passed']}` / `{summary['static_checks_total']}`",
        f"- Reward/plasticity owner: `{summary['plasticity_owner']}`",
        f"- Next gate: `{summary['next_step_if_passed']}`",
        "",
        "## Criteria",
        "",
        "| Criterion | Value | Rule | Pass |",
        "| --- | --- | --- | --- |",
    ]
    for item in result["criteria"]:
        lines.append(f"| {item['name']} | `{markdown_value(item.get('value'))}` | `{item.get('rule')}` | {'yes' if item.get('passed') else 'no'} |")
    lines.extend(
        [
            "",
            "## Claim Boundary",
            "",
            "- This is local custom-C reward/plasticity scaffold evidence.",
            "- It is not a hardware run.",
            "- It is not continuous-learning parity yet.",
            "- It is not speedup evidence.",
            "- It does not prove scale-ready all-synapse trace sweeps; that remains a later optimization/scale gate.",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def write_latest(output_dir: Path, manifest: Path, report: Path, status: str) -> None:
    CONTROLLED.mkdir(parents=True, exist_ok=True)
    write_json(
        CONTROLLED / "tier4_22d_latest_manifest.json",
        {
            "generated_at_utc": utc_now(),
            "tier": TIER,
            "status": status,
            "output_dir": str(output_dir),
            "manifest": str(manifest),
            "report": str(report),
            "canonical": False,
            "claim": "Latest Tier 4.22d reward/plasticity custom-C scaffold; not hardware or continuous-learning parity evidence.",
        },
    )


def run(args: argparse.Namespace) -> int:
    output_dir = (args.output_dir or CONTROLLED / "tier4_22d_20260430_reward_plasticity_scaffold").resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    tier4_22c_status, tier4_22c_manifest = latest_status(TIER4_22C_LATEST)
    host = run_host_tests()
    checks = static_checks()
    contract_rows = plasticity_contract_rows()

    host_stdout = output_dir / "tier4_22d_host_test_stdout.txt"
    host_stderr = output_dir / "tier4_22d_host_test_stderr.txt"
    host_stdout.write_text(host["stdout"], encoding="utf-8")
    host_stderr.write_text(host["stderr"], encoding="utf-8")

    static_csv = output_dir / "tier4_22d_static_compliance.csv"
    contract_csv = output_dir / "tier4_22d_plasticity_contract.csv"
    write_csv(static_csv, checks)
    write_csv(contract_csv, contract_rows)

    static_passed = sum(1 for check in checks if check["passed"])
    criteria = [
        criterion("runner revision current", RUNNER_REVISION, "expected current source", True),
        criterion("Tier 4.22c persistent state pass exists", tier4_22c_status, "== pass", tier4_22c_status == "pass"),
        criterion("custom C host tests pass", host["returncode"], "returncode == 0 and ALL TESTS PASSED", bool(host["passed"])),
        criterion("all static plasticity checks pass", f"{static_passed}/{len(checks)}", "all pass", static_passed == len(checks)),
        criterion("dopamine is trace-gated", "dopamine * eligibility_trace", "required causal rule", any(check["name"] == "dopamine is trace-gated" and check["passed"] for check in checks)),
        criterion("dopamine can be negative", "int32_t", "signed fixed-point reward", any(check["name"] == "dopamine signed fixed-point" and check["passed"] for check in checks)),
        criterion("claim boundary explicit", "local scaffold only", "not hardware/parity/speedup", True),
    ]
    status = "pass" if all(item["passed"] for item in criteria) else "fail"
    failure_reason = "" if status == "pass" else "Failed criteria: " + ", ".join(item["name"] for item in criteria if not item["passed"])
    summary = {
        "runner_revision": RUNNER_REVISION,
        "tier4_22c_status": tier4_22c_status,
        "tier4_22c_manifest": tier4_22c_manifest,
        "host_tests_passed": bool(host["passed"]),
        "host_test_returncode": int(host["returncode"]),
        "static_checks_total": len(checks),
        "static_checks_passed": static_passed,
        "plasticity_owner": "custom_c_runtime",
        "mechanisms": ["synaptic_eligibility_trace", "trace_gated_dopamine", "fixed_point_trace_decay", "readout_reward_update"],
        "north_star": "full custom/on-chip CRA runtime; hybrid host paths are transitional diagnostics",
        "claim_boundary": "Reward/plasticity scaffold only; not hardware, continuous-learning parity, speedup, or scale-ready all-synapse trace optimization evidence.",
        "next_step_if_passed": "Tier 4.22e local continuous-learning parity: compare this runtime reward/plasticity path against chunked reference before any new EBRAINS run.",
    }
    manifest = output_dir / "tier4_22d_results.json"
    report = output_dir / "tier4_22d_report.md"
    result = {
        "tier": TIER,
        "generated_at_utc": utc_now(),
        "status": status,
        "failure_reason": failure_reason,
        "output_dir": str(output_dir),
        "summary": summary,
        "criteria": criteria,
        "static_checks": checks,
        "plasticity_contract": contract_rows,
        "host_test": {
            "command": host["command"],
            "returncode": host["returncode"],
            "stdout_artifact": str(host_stdout),
            "stderr_artifact": str(host_stderr),
        },
        "artifacts": {
            "manifest_json": str(manifest),
            "report_md": str(report),
            "static_compliance_csv": str(static_csv),
            "plasticity_contract_csv": str(contract_csv),
            "host_test_stdout": str(host_stdout),
            "host_test_stderr": str(host_stderr),
        },
    }
    write_json(manifest, result)
    write_report(report, result)
    write_latest(output_dir, manifest, report, status)
    print(json.dumps({"status": status, "output_dir": str(output_dir), "manifest": str(manifest)}, indent=2))
    return 0 if status == "pass" else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Tier 4.22d reward/plasticity custom-C scaffold.")
    parser.add_argument("--output-dir", type=Path, default=None)
    return parser


def main(argv: list[str] | None = None) -> int:
    return run(build_parser().parse_args(argv))


if __name__ == "__main__":
    raise SystemExit(main())

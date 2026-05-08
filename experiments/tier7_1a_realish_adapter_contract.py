#!/usr/bin/env python3
"""Tier 7.1a - Real-ish/public adapter contract after Tier 6.2a.

This is a contract gate, not a dataset run. Tier 6.2a found only a narrow
v2.3 signal on a private variable-delay diagnostic. This tier chooses the first
public/real-ish adapter family that can test whether that signal survives
outside private generators, and predeclares the data, splits, metrics,
baselines, leakage controls, and nonclaims before any benchmark is run.
"""

from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
CONTROLLED = ROOT / "controlled_test_output"
TIER = "Tier 7.1a - Real-ish/Public Adapter Contract"
RUNNER_REVISION = "tier7_1a_realish_adapter_contract_20260508_0001"
DEFAULT_OUTPUT_DIR = CONTROLLED / "tier7_1a_20260508_realish_adapter_contract"
TIER6_2A_RESULTS = CONTROLLED / "tier6_2a_20260508_targeted_usefulness_validation" / "tier6_2a_results.json"
V23_BASELINE = ROOT / "baselines" / "CRA_EVIDENCE_BASELINE_v2.3.json"
CONTRACT_DOC = ROOT / "docs" / "TIER6_2_USEFULNESS_BATTERY_CONTRACT.md"


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
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fieldnames: list[str] = []
    for row in rows:
        for key in row:
            if key not in fieldnames:
                fieldnames.append(key)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def criterion(name: str, value: Any, rule: str, passed: bool, note: str = "") -> dict[str, Any]:
    return {"name": name, "value": json_safe(value), "rule": rule, "passed": bool(passed), "note": note}


def build_contract() -> dict[str, Any]:
    sources = [
        {
            "source_id": "nasa_pcoe_repository",
            "name": "NASA Prognostics Center of Excellence Data Set Repository",
            "url": "https://www.nasa.gov/intelligent-systems-division/discovery-and-systems-health/pcoe/pcoe-data-set-repository/",
            "role": "primary official source for C-MAPSS / turbofan degradation data access",
            "verification_status": "source page checked 2026-05-08",
        },
        {
            "source_id": "nasa_dashlink_cmapss",
            "name": "DASHlink Turbofan Engine Degradation Simulation Data Set",
            "url": "https://c3.ndc.nasa.gov/dashlink/resources/139/",
            "role": "official NASA DASHlink landing page for the classic C-MAPSS turbofan data resource",
            "verification_status": "source page checked 2026-05-08",
        },
        {
            "source_id": "numenta_nab",
            "name": "Numenta Anomaly Benchmark",
            "url": "https://github.com/numenta/NAB",
            "role": "secondary candidate for streaming anomaly adapter after C-MAPSS contract execution",
            "verification_status": "source page checked 2026-05-08",
        },
        {
            "source_id": "ucr_uea_archive",
            "name": "UCR/UEA Time Series Classification Archive",
            "url": "https://www.timeseriesclassification.com/",
            "role": "future held-out time-series classification adapter source",
            "verification_status": "source page checked 2026-05-08",
        },
        {
            "source_id": "physionet",
            "name": "PhysioNet databases",
            "url": "https://www.physionet.org/about/database/",
            "role": "future biosignal/event-stream adapter source after license/split audit",
            "verification_status": "source page checked 2026-05-08",
        },
    ]
    selected = {
        "adapter_id": "nasa_cmapss_rul_streaming",
        "dataset_family": "NASA C-MAPSS / turbofan engine degradation",
        "reason": (
            "Tier 6.2a found a narrow variable-delay signal. C-MAPSS is the first "
            "real-ish public stream family to test delayed sensor history -> future "
            "degradation/RUL structure without relying on private task generators."
        ),
        "first_executable_tier": "Tier 7.1b",
        "first_executable_scope": (
            "local source/data preflight plus one compact FD001-style smoke if the "
            "data license/download path is clean"
        ),
    }
    metrics = [
        "RUL RMSE on held-out units",
        "MAE on held-out units",
        "tail-window RMSE near failure",
        "NASA asymmetric prognostics score if implemented cleanly",
        "sample efficiency by prefix length",
        "worst-unit error",
        "runtime per model",
    ]
    baselines = [
        "constant/mean-RUL baseline",
        "monotone age-to-RUL baseline",
        "lag/ridge window baseline",
        "online LMS / linear readout baseline",
        "random reservoir online baseline",
        "fixed ESN train-prefix ridge baseline",
        "small GRU/LSTM if dependency/runtime budget is practical",
        "tree/boosting window baseline if scikit-learn is available",
        "CRA v2.2 fading-memory reference",
        "CRA v2.3 generic bounded recurrent-state baseline",
        "v2.3 state-reset/shuffled/no-update controls",
    ]
    leakage_controls = [
        "train-unit statistics only for normalization",
        "no test-unit future RUL labels during online prediction",
        "chronological prediction within each engine unit",
        "unit-held-out evaluation",
        "predeclared sensor/channel selection before scoring",
        "prediction-before-update for online models",
        "data download/checksum manifest preserved",
        "all task transforms logged to JSON before model scoring",
    ]
    pass_fail = {
        "contract_pass_means": (
            "the adapter is fully predeclared and safe to implement; it does not "
            "mean CRA is useful on C-MAPSS"
        ),
        "tier7_1b_pass_would_require": [
            "source/download/license/checksum preflight passes",
            "adapter emits leakage-safe chronological streams",
            "at least v2.2, v2.3, lag, reservoir, and ESN baselines run on the same rows",
            "no future-label leakage",
            "no baseline freeze or hardware transfer from smoke evidence alone",
        ],
        "tier7_1c_or_later_usefulness_gate_would_require": [
            "v2.3 or a later promoted mechanism beats or complements strongest fair baselines",
            "seed/unit-level stability and worst-unit behavior are reported",
            "v2.3 shams/ablations separate if v2.3 is part of the claim",
            "metrics include effect size or confidence intervals where practical",
            "same public adapter can be reproduced from a fresh checkout",
        ],
        "fail_or_narrow_if": [
            "simple age/lag/ESN/GRU baselines dominate all metrics",
            "CRA wins only through private preprocessing choices",
            "wins vanish on held-out units or tail-window scoring",
            "mechanism shams match the claimed mechanism",
            "dataset licensing/download cannot be made reproducible",
        ],
    }
    return {
        "selected_adapter": selected,
        "source_audit": sources,
        "metrics": metrics,
        "baselines": baselines,
        "leakage_controls": leakage_controls,
        "pass_fail": pass_fail,
        "next_step": (
            "Tier 7.1b should implement a source/data preflight for NASA C-MAPSS, "
            "download or locate the data reproducibly, write checksums and license "
            "notes, then emit a tiny adapter smoke before full scoring."
        ),
        "nonclaims": [
            "not a C-MAPSS result",
            "not a public usefulness claim",
            "not a baseline freeze",
            "not hardware or native transfer",
            "not evidence that variable-delay private diagnostics generalize",
            "not language, planning, AGI, or ASI evidence",
        ],
    }


def write_report(output_dir: Path, payload: dict[str, Any]) -> None:
    c = payload["contract"]
    selected = c["selected_adapter"]
    lines = [
        "# Tier 7.1a Real-ish/Public Adapter Contract",
        "",
        f"- Generated: `{payload['generated_at_utc']}`",
        f"- Runner revision: `{payload['runner_revision']}`",
        f"- Status: **{payload['status'].upper()}**",
        f"- Criteria: `{payload['criteria_passed']}/{payload['criteria_total']}`",
        "",
        "## Selected Adapter",
        "",
        f"- Adapter: `{selected['adapter_id']}`",
        f"- Dataset family: {selected['dataset_family']}",
        f"- Reason: {selected['reason']}",
        f"- First executable tier: `{selected['first_executable_tier']}`",
        "",
        "## Source Audit",
        "",
        "| Source | URL | Role | Verification |",
        "| --- | --- | --- | --- |",
    ]
    for row in c["source_audit"]:
        lines.append(f"| {row['name']} | {row['url']} | {row['role']} | {row['verification_status']} |")
    lines.extend(
        [
            "",
            "## Required Baselines",
            "",
            *[f"- {item}" for item in c["baselines"]],
            "",
            "## Leakage Controls",
            "",
            *[f"- {item}" for item in c["leakage_controls"]],
            "",
            "## Pass / Fail Boundary",
            "",
            f"- Contract pass means: {c['pass_fail']['contract_pass_means']}",
            f"- Next step: {c['next_step']}",
            "",
            "## Nonclaims",
            "",
            *[f"- {item}" for item in c["nonclaims"]],
            "",
        ]
    )
    (output_dir / "tier7_1a_report.md").write_text("\n".join(lines), encoding="utf-8")


def run(args: argparse.Namespace) -> dict[str, Any]:
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    tier6_2a = read_json(TIER6_2A_RESULTS) if TIER6_2A_RESULTS.exists() else {}
    contract = build_contract()
    source_urls_present = all(row.get("url", "").startswith("https://") for row in contract["source_audit"])
    required_baselines_present = all(
        required in " ".join(contract["baselines"]).lower()
        for required in ["v2.2", "v2.3", "lag", "reservoir", "esn"]
    )
    criteria = [
        criterion("Tier 6.2a source exists", str(TIER6_2A_RESULTS), "exists", TIER6_2A_RESULTS.exists()),
        criterion("Tier 6.2a passed", tier6_2a.get("status"), "== pass", tier6_2a.get("status") == "pass"),
        criterion("v2.3 baseline lock exists", str(V23_BASELINE), "exists", V23_BASELINE.exists()),
        criterion("usefulness contract doc exists", str(CONTRACT_DOC), "exists", CONTRACT_DOC.exists()),
        criterion("selected adapter declared", contract["selected_adapter"]["adapter_id"], "non-empty", bool(contract["selected_adapter"]["adapter_id"])),
        criterion("official/public source URLs declared", source_urls_present, "all source rows have https URL", source_urls_present),
        criterion("required baselines declared", contract["baselines"], "includes v2.2/v2.3/lag/reservoir/ESN", required_baselines_present),
        criterion("leakage controls declared", len(contract["leakage_controls"]), ">= 6", len(contract["leakage_controls"]) >= 6),
        criterion("pass/fail rules declared", sorted(contract["pass_fail"].keys()), "contains contract/pass/fail rules", all(k in contract["pass_fail"] for k in ["contract_pass_means", "tier7_1b_pass_would_require", "fail_or_narrow_if"])),
        criterion("contract only, no dataset scoring", "no model run", "true", True),
        criterion("no baseline freeze authorized", False, "== false", True),
        criterion("no hardware transfer authorized", False, "== false", True),
    ]
    criteria_passed = sum(1 for item in criteria if item["passed"])
    payload = {
        "tier": TIER,
        "runner_revision": RUNNER_REVISION,
        "generated_at_utc": utc_now(),
        "status": "pass" if criteria_passed == len(criteria) else "fail",
        "criteria": criteria,
        "criteria_passed": criteria_passed,
        "criteria_total": len(criteria),
        "failed_criteria": [item for item in criteria if not item["passed"]],
        "output_dir": str(output_dir),
        "source_tier6_2a_results": str(TIER6_2A_RESULTS),
        "contract": contract,
        "claim_boundary": (
            "Tier 7.1a is a contract only. It selects and predeclares the first real-ish/public "
            "adapter family after Tier 6.2a. It is not dataset evidence, not a usefulness claim, "
            "not a baseline freeze, and not hardware/native transfer."
        ),
    }
    write_json(output_dir / "tier7_1a_results.json", payload)
    write_json(output_dir / "tier7_1a_contract.json", contract)
    write_csv(output_dir / "tier7_1a_summary.csv", [{**contract["selected_adapter"], "status": payload["status"], "criteria_passed": criteria_passed, "criteria_total": len(criteria)}])
    write_csv(output_dir / "tier7_1a_source_audit.csv", contract["source_audit"])
    write_report(output_dir, payload)
    manifest = {
        "tier": TIER,
        "status": payload["status"],
        "generated_at_utc": payload["generated_at_utc"],
        "output_dir": str(output_dir),
        "results_json": str(output_dir / "tier7_1a_results.json"),
        "report_md": str(output_dir / "tier7_1a_report.md"),
        "summary_csv": str(output_dir / "tier7_1a_summary.csv"),
    }
    write_json(output_dir / "tier7_1a_latest_manifest.json", manifest)
    write_json(CONTROLLED / "tier7_1a_latest_manifest.json", manifest)
    return payload


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=TIER)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    return parser


def main() -> int:
    payload = run(build_parser().parse_args())
    print(
        json.dumps(
            {
                "status": payload["status"],
                "criteria": f"{payload['criteria_passed']}/{payload['criteria_total']}",
                "selected_adapter": payload["contract"]["selected_adapter"]["adapter_id"],
                "next_step": payload["contract"]["next_step"],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0 if payload["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())

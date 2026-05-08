#!/usr/bin/env python3
"""Tier 7.1b - NASA C-MAPSS source/data preflight.

This tier does not score CRA. It verifies that the first public/real-ish
adapter selected by Tier 7.1a can be accessed, checksummed, parsed, and exposed
as a leakage-safe streaming adapter before any full benchmark run.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import shutil
import urllib.request
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
CONTROLLED = ROOT / "controlled_test_output"
DATA_CACHE = ROOT / ".cra_data_cache" / "nasa_cmapss"
DEFAULT_OUTPUT_DIR = CONTROLLED / "tier7_1b_20260508_cmapss_source_data_preflight"
TIER7_1A_RESULTS = CONTROLLED / "tier7_1a_20260508_realish_adapter_contract" / "tier7_1a_results.json"
RUNNER_REVISION = "tier7_1b_cmapss_source_data_preflight_20260508_0001"
TIER = "Tier 7.1b - NASA C-MAPSS Source/Data Preflight"
CMAPSS_ZIP_URL = "https://data.nasa.gov/docs/legacy/CMAPSSData.zip"
NASA_DATASET_PAGE = "https://data.nasa.gov/dataset/cmapss-jet-engine-simulated-data"
NASA_PCOE_PAGE = (
    "https://www.nasa.gov/intelligent-systems-division/discovery-and-systems-health/"
    "pcoe/pcoe-data-set-repository/"
)
DASHLINK_PAGE = "https://c3.ndc.nasa.gov/dashlink/resources/139/"


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


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def criterion(name: str, value: Any, rule: str, passed: bool, note: str = "") -> dict[str, Any]:
    return {"name": name, "value": json_safe(value), "rule": rule, "passed": bool(passed), "note": note}


def download_if_needed(url: str, dst: Path, timeout: int = 60) -> dict[str, Any]:
    dst.parent.mkdir(parents=True, exist_ok=True)
    if dst.exists() and dst.stat().st_size > 0:
        return {"downloaded": False, "path": dst, "bytes": dst.stat().st_size}
    tmp = dst.with_suffix(dst.suffix + ".tmp")
    req = urllib.request.Request(url, headers={"User-Agent": "CRA-Tier7.1b-preflight/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as response, tmp.open("wb") as handle:
        shutil.copyfileobj(response, handle)
    tmp.replace(dst)
    return {"downloaded": True, "path": dst, "bytes": dst.stat().st_size}


def safe_extract(zip_path: Path, extract_dir: Path) -> None:
    extract_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path) as archive:
        for member in archive.infolist():
            target = (extract_dir / member.filename).resolve()
            if not str(target).startswith(str(extract_dir.resolve())):
                raise RuntimeError(f"unsafe zip member path: {member.filename}")
        archive.extractall(extract_dir)


def find_named_file(root: Path, name: str) -> Path | None:
    matches = [p for p in root.rglob(name) if p.is_file()]
    return sorted(matches)[0] if matches else None


def parse_numeric_rows(path: Path, expected_columns: int = 26) -> list[list[float]]:
    rows: list[list[float]] = []
    for line_no, line in enumerate(path.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
        stripped = line.strip()
        if not stripped:
            continue
        parts = stripped.split()
        if len(parts) != expected_columns:
            raise ValueError(f"{path.name}:{line_no} expected {expected_columns} columns, found {len(parts)}")
        rows.append([float(x) for x in parts])
    return rows


def parse_rul(path: Path) -> list[float]:
    vals: list[float] = []
    for line_no, line in enumerate(path.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
        stripped = line.strip()
        if not stripped:
            continue
        parts = stripped.split()
        if len(parts) != 1:
            raise ValueError(f"{path.name}:{line_no} expected 1 RUL column, found {len(parts)}")
        vals.append(float(parts[0]))
    return vals


def unit_profile(rows: list[list[float]]) -> dict[int, dict[str, int]]:
    profile: dict[int, dict[str, int]] = {}
    for row in rows:
        unit = int(row[0])
        cycle = int(row[1])
        info = profile.setdefault(unit, {"rows": 0, "max_cycle": 0})
        info["rows"] += 1
        info["max_cycle"] = max(info["max_cycle"], cycle)
    return profile


def feature_stats(rows: list[list[float]]) -> dict[str, dict[str, float]]:
    # Features are columns 3-25 zero-indexed after unit, cycle, and 3 settings.
    stats: dict[str, dict[str, float]] = {}
    for col in range(2, 26):
        vals = [row[col] for row in rows]
        mean = sum(vals) / len(vals)
        var = sum((v - mean) ** 2 for v in vals) / len(vals)
        std = math.sqrt(var)
        stats[f"col_{col + 1:02d}"] = {
            "mean": mean,
            "std": std if std > 1e-12 else 1.0,
            "raw_std": std,
            "source": "train_FD001_only",
        }
    return stats


def zscore(row: list[float], stats: dict[str, dict[str, float]]) -> list[float]:
    values: list[float] = []
    for col in range(2, 26):
        s = stats[f"col_{col + 1:02d}"]
        values.append((row[col] - s["mean"]) / s["std"])
    return values


def build_smoke_stream(
    train_rows: list[list[float]],
    test_rows: list[list[float]],
    test_rul: list[float],
    stats: dict[str, dict[str, float]],
    max_units: int,
    max_cycles_per_unit: int,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    test_profile = unit_profile(test_rows)
    selected_train_units = sorted(unit_profile(train_rows))[:max_units]
    selected_test_units = sorted(test_profile)[:max_units]
    stream: list[dict[str, Any]] = []
    labels: list[dict[str, Any]] = []

    def append_rows(rows: list[list[float]], split: str, units: list[int]) -> None:
        for row in rows:
            unit = int(row[0])
            cycle = int(row[1])
            if unit not in units or cycle > max_cycles_per_unit:
                continue
            features = zscore(row, stats)
            event_id = f"{split}_unit{unit:03d}_cycle{cycle:04d}"
            stream.append(
                {
                    "event_id": event_id,
                    "split": split,
                    "unit": unit,
                    "cycle": cycle,
                    "prediction_before_update": True,
                    "feature_count": len(features),
                    "feature_l2": math.sqrt(sum(v * v for v in features)),
                    "target_available_in_stream": False,
                }
            )
            if split == "train":
                train_profile = unit_profile(rows)
                rul = train_profile[unit]["max_cycle"] - cycle
            else:
                final_rul = test_rul[unit - 1]
                rul = final_rul + test_profile[unit]["max_cycle"] - cycle
            labels.append({"event_id": event_id, "split": split, "unit": unit, "cycle": cycle, "offline_rul_label": rul})

    append_rows(train_rows, "train", selected_train_units)
    append_rows(test_rows, "test", selected_test_units)
    return stream, labels


def make_manifest(output_dir: Path, artifacts: dict[str, Path], status: str) -> dict[str, Any]:
    rows = []
    for name, path in sorted(artifacts.items()):
        rows.append({"name": name, "path": str(path), "sha256": sha256_file(path), "bytes": path.stat().st_size})
    manifest = {
        "tier": TIER,
        "status": status,
        "generated_at_utc": utc_now(),
        "runner_revision": RUNNER_REVISION,
        "output_dir": output_dir,
        "artifacts": rows,
    }
    return manifest


def write_report(output_dir: Path, payload: dict[str, Any]) -> None:
    profile = payload["fd001_profile"]
    lines = [
        "# Tier 7.1b NASA C-MAPSS Source/Data Preflight",
        "",
        f"- Generated: `{payload['generated_at_utc']}`",
        f"- Runner revision: `{payload['runner_revision']}`",
        f"- Status: **{payload['status'].upper()}**",
        f"- Criteria: `{payload['criteria_passed']}/{payload['criteria_total']}`",
        "",
        "## Source",
        "",
        f"- Dataset page: {NASA_DATASET_PAGE}",
        f"- Download URL: {CMAPSS_ZIP_URL}",
        f"- NASA PCoE page: {NASA_PCOE_PAGE}",
        f"- DASHlink page: {DASHLINK_PAGE}",
        f"- ZIP SHA256: `{payload['zip_sha256']}`",
        f"- ZIP bytes: `{payload['zip_bytes']}`",
        "",
        "## FD001 Profile",
        "",
        f"- Train rows: `{profile['train_rows']}`",
        f"- Test rows: `{profile['test_rows']}`",
        f"- Train units: `{profile['train_units']}`",
        f"- Test units: `{profile['test_units']}`",
        f"- RUL labels: `{profile['rul_labels']}`",
        f"- Column count: `{profile['column_count']}`",
        "",
        "## Leakage Boundary",
        "",
        "- Normalization stats are computed from `train_FD001.txt` only.",
        "- Smoke stream rows do not include RUL labels.",
        "- Offline scoring labels are written separately from the smoke stream.",
        "- This tier performs no CRA scoring and no baseline scoring.",
        "",
        "## Claim Boundary",
        "",
        payload["claim_boundary"],
        "",
        "## Next Step",
        "",
        payload["next_step"],
        "",
    ]
    (output_dir / "tier7_1b_report.md").write_text("\n".join(lines), encoding="utf-8")


def run(args: argparse.Namespace) -> dict[str, Any]:
    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    data_cache = Path(args.data_cache).resolve()
    zip_path = data_cache / "CMAPSSData.zip"
    extract_dir = data_cache / "extracted"

    prior = read_json(TIER7_1A_RESULTS) if TIER7_1A_RESULTS.exists() else {}
    download_info = download_if_needed(args.url, zip_path, timeout=args.timeout)
    zip_sha = sha256_file(zip_path)
    safe_extract(zip_path, extract_dir)

    required_names = ["train_FD001.txt", "test_FD001.txt", "RUL_FD001.txt"]
    found = {name: find_named_file(extract_dir, name) for name in required_names}
    readme = find_named_file(extract_dir, "readme.txt") or find_named_file(extract_dir, "README.txt")

    train_path = found["train_FD001.txt"]
    test_path = found["test_FD001.txt"]
    rul_path = found["RUL_FD001.txt"]
    if train_path is None or test_path is None or rul_path is None:
        missing = [name for name, path in found.items() if path is None]
        raise FileNotFoundError(f"missing required C-MAPSS files: {missing}")

    train_rows = parse_numeric_rows(train_path)
    test_rows = parse_numeric_rows(test_path)
    rul = parse_rul(rul_path)
    train_units = unit_profile(train_rows)
    test_units = unit_profile(test_rows)
    stats = feature_stats(train_rows)
    stream, labels = build_smoke_stream(
        train_rows,
        test_rows,
        rul,
        stats,
        max_units=args.smoke_units,
        max_cycles_per_unit=args.smoke_cycles,
    )

    extracted_files = []
    for path in sorted(p for p in extract_dir.rglob("*") if p.is_file()):
        extracted_files.append(
            {
                "relative_path": str(path.relative_to(extract_dir)),
                "bytes": path.stat().st_size,
                "sha256": sha256_file(path),
            }
        )

    fd001_profile = {
        "train_rows": len(train_rows),
        "test_rows": len(test_rows),
        "train_units": len(train_units),
        "test_units": len(test_units),
        "rul_labels": len(rul),
        "column_count": 26,
        "expected_columns": [
            "unit",
            "cycle",
            "operational_setting_1",
            "operational_setting_2",
            "operational_setting_3",
            *[f"sensor_{i}" for i in range(1, 22)],
        ],
        "train_unit_min_max_cycle": min(v["max_cycle"] for v in train_units.values()),
        "train_unit_max_max_cycle": max(v["max_cycle"] for v in train_units.values()),
        "test_unit_min_max_cycle": min(v["max_cycle"] for v in test_units.values()),
        "test_unit_max_max_cycle": max(v["max_cycle"] for v in test_units.values()),
        "smoke_stream_rows": len(stream),
        "smoke_label_rows": len(labels),
    }

    source_manifest = {
        "source_pages": [
            {"name": "NASA Open Data Portal CMAPSS dataset", "url": NASA_DATASET_PAGE},
            {"name": "NASA PCoE Data Set Repository", "url": NASA_PCOE_PAGE},
            {"name": "NASA DASHlink C-MAPSS landing page", "url": DASHLINK_PAGE},
        ],
        "download_url": args.url,
        "downloaded": download_info["downloaded"],
        "zip_path_local_ignored": zip_path,
        "zip_sha256": zip_sha,
        "zip_bytes": zip_path.stat().st_size,
        "license_note": (
            "NASA Open Data metadata marks accessLevel public; resource page reports "
            "'License not specified'. Treat license as source-note required and do "
            "not redistribute raw data in this repository."
        ),
        "extracted_files": extracted_files,
        "raw_data_git_policy": "raw dataset cache is local-only and ignored by .gitignore",
    }

    criteria = [
        criterion("Tier 7.1a contract exists", TIER7_1A_RESULTS, "exists", TIER7_1A_RESULTS.exists()),
        criterion("Tier 7.1a selected C-MAPSS", prior.get("contract", {}).get("selected_adapter", {}).get("adapter_id"), "== nasa_cmapss_rul_streaming", prior.get("contract", {}).get("selected_adapter", {}).get("adapter_id") == "nasa_cmapss_rul_streaming"),
        criterion("official download URL reachable", args.url, "downloaded or cached non-empty ZIP", zip_path.exists() and zip_path.stat().st_size > 0),
        criterion("ZIP checksum computed", zip_sha, "64 hex chars", len(zip_sha) == 64),
        criterion("required FD001 files present", {k: v for k, v in found.items()}, "train/test/RUL exist", all(found.values())),
        criterion("README/source notes present", readme, "README found", readme is not None),
        criterion("train/test row parse succeeded", {"train": len(train_rows), "test": len(test_rows)}, "> 0 rows", len(train_rows) > 0 and len(test_rows) > 0),
        criterion("FD001 column count valid", fd001_profile["column_count"], "== 26", fd001_profile["column_count"] == 26),
        criterion("RUL labels match test units", {"labels": len(rul), "test_units": len(test_units)}, "equal", len(rul) == len(test_units)),
        criterion("train-only normalization stats generated", len(stats), "24 feature columns", len(stats) == 24),
        criterion("smoke stream generated", len(stream), "> 0", len(stream) > 0),
        criterion("smoke labels separated from stream", all(not row["target_available_in_stream"] for row in stream), "all false", all(not row["target_available_in_stream"] for row in stream)),
        criterion("prediction-before-update declared", all(row["prediction_before_update"] for row in stream), "all true", all(row["prediction_before_update"] for row in stream)),
        criterion("source manifest includes checksums", len(extracted_files), ">= required files", len(extracted_files) >= 3),
        criterion("no scoring performed", "preflight only", "true", True),
        criterion(
            "no baseline freeze or hardware transfer authorized",
            {"baseline_freeze_authorized": False, "hardware_transfer_authorized": False},
            "both false",
            True,
        ),
    ]
    status = "pass" if all(c["passed"] for c in criteria) else "fail"
    payload = {
        "tier": TIER,
        "runner_revision": RUNNER_REVISION,
        "generated_at_utc": utc_now(),
        "status": status,
        "criteria": criteria,
        "criteria_passed": sum(1 for c in criteria if c["passed"]),
        "criteria_total": len(criteria),
        "failed_criteria": [c for c in criteria if not c["passed"]],
        "output_dir": output_dir,
        "data_cache_local_ignored": data_cache,
        "download_url": args.url,
        "zip_sha256": zip_sha,
        "zip_bytes": zip_path.stat().st_size,
        "fd001_profile": fd001_profile,
        "source_manifest": source_manifest,
        "claim_boundary": (
            "Tier 7.1b verifies source access, checksums, schema, split/normalization "
            "policy, and a tiny leakage-safe stream smoke. It is not C-MAPSS scoring, "
            "not a public usefulness claim, not a baseline freeze, and not "
            "hardware/native transfer evidence."
        ),
        "next_step": (
            "Tier 7.1c may run the first compact C-MAPSS FD001 scoring gate only "
            "after this preflight passes. Tier 7.1c must score v2.2/v2.3 and fair "
            "baselines on the same rows with leakage controls preserved."
        ),
    }

    paths = {
        "results_json": output_dir / "tier7_1b_results.json",
        "source_manifest_json": output_dir / "tier7_1b_source_manifest.json",
        "source_manifest_csv": output_dir / "tier7_1b_source_manifest.csv",
        "fd001_profile_json": output_dir / "tier7_1b_fd001_profile.json",
        "normalization_stats_json": output_dir / "tier7_1b_normalization_stats.json",
        "smoke_stream_preview_csv": output_dir / "tier7_1b_smoke_stream_preview.csv",
        "smoke_scoring_labels_csv": output_dir / "tier7_1b_smoke_scoring_labels.csv",
        "summary_csv": output_dir / "tier7_1b_summary.csv",
        "report_md": output_dir / "tier7_1b_report.md",
    }
    write_json(paths["results_json"], payload)
    write_json(paths["source_manifest_json"], source_manifest)
    write_csv(paths["source_manifest_csv"], extracted_files)
    write_json(paths["fd001_profile_json"], fd001_profile)
    write_json(paths["normalization_stats_json"], stats)
    write_csv(paths["smoke_stream_preview_csv"], stream)
    write_csv(paths["smoke_scoring_labels_csv"], labels)
    write_csv(paths["summary_csv"], [{"criterion": c["name"], "passed": c["passed"], "value": c["value"], "rule": c["rule"]} for c in criteria])
    write_report(output_dir, payload)
    manifest = make_manifest(output_dir, paths, status)
    manifest_path = output_dir / "tier7_1b_latest_manifest.json"
    write_json(manifest_path, manifest)
    latest_path = CONTROLLED / "tier7_1b_latest_manifest.json"
    write_json(latest_path, manifest)
    return payload


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--data-cache", default=str(DATA_CACHE))
    parser.add_argument("--url", default=CMAPSS_ZIP_URL)
    parser.add_argument("--timeout", type=int, default=60)
    parser.add_argument("--smoke-units", type=int, default=2)
    parser.add_argument("--smoke-cycles", type=int, default=5)
    return parser.parse_args()


def main() -> None:
    payload = run(parse_args())
    print(json.dumps({"status": payload["status"], "criteria": f"{payload['criteria_passed']}/{payload['criteria_total']}", "output_dir": str(payload["output_dir"])}, indent=2))
    if payload["status"] != "pass":
        raise SystemExit(1)


if __name__ == "__main__":
    main()

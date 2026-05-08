#!/usr/bin/env python3
"""Tier 7.1g - NAB source/data/scoring preflight.

Tier 7.1f selected Numenta NAB as the next public adapter family after the
compact C-MAPSS path did not produce a confirmed public usefulness signal. This
preflight is deliberately not a scorer. It verifies that the official NAB source
can be pinned, cached, parsed, exposed as leakage-safe online streams, and wired
to a documented scoring contract before any CRA/baseline NAB scoring run.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import shutil
import subprocess
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
CONTROLLED = ROOT / "controlled_test_output"
DATA_CACHE = ROOT / ".cra_data_cache" / "numenta_nab"
DEFAULT_OUTPUT_DIR = CONTROLLED / "tier7_1g_20260508_nab_source_data_scoring_preflight"
TIER7_1F_RESULTS = CONTROLLED / "tier7_1f_20260508_next_public_adapter_contract" / "tier7_1f_results.json"

TIER = "Tier 7.1g - NAB Source/Data/Scoring Preflight"
RUNNER_REVISION = "tier7_1g_nab_source_data_scoring_preflight_20260508_0001"
NAB_REPO_URL = "https://github.com/numenta/NAB"
NAB_GIT_URL = "https://github.com/numenta/NAB.git"
NAB_RAW_BASE = "https://raw.githubusercontent.com/numenta/NAB"
PINNED_NAB_COMMIT = "ea702d75cc2258d9d7dd35ca8e5e2539d71f3140"

CORE_SOURCE_FILES = [
    "README.md",
    "LICENSE.txt",
    "nab/scorer.py",
    "config/profiles.json",
    "config/thresholds.json",
    "labels/combined_windows.json",
    "labels/combined_labels.json",
    "labels/combined_windows_tiny.json",
]

SELECTED_DATA_FILES = [
    "artificialWithAnomaly/art_daily_flatmiddle.csv",
    "realKnownCause/ambient_temperature_system_failure.csv",
    "realKnownCause/machine_temperature_system_failure.csv",
    "realAWSCloudwatch/ec2_cpu_utilization_24ae8d.csv",
    "realTraffic/TravelTime_387.csv",
]

REQUIRED_PROFILES = {"standard", "reward_low_FP_rate", "reward_low_FN_rate"}


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


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


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


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def criterion(name: str, value: Any, rule: str, passed: bool, note: str = "") -> dict[str, Any]:
    return {"name": name, "value": json_safe(value), "rule": rule, "passed": bool(passed), "note": note}


def resolve_remote_head(timeout: int) -> str | None:
    try:
        completed = subprocess.run(
            ["git", "ls-remote", NAB_GIT_URL, "HEAD"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except Exception:
        return None
    parts = completed.stdout.strip().split()
    if not parts:
        return None
    commit = parts[0].strip()
    return commit if len(commit) == 40 else None


def raw_url(commit: str, repo_path: str) -> str:
    return f"{NAB_RAW_BASE}/{commit}/{repo_path}"


def cache_path(cache_root: Path, commit: str, repo_path: str) -> Path:
    return cache_root / commit / repo_path


def download_if_needed(url: str, dst: Path, timeout: int) -> dict[str, Any]:
    dst.parent.mkdir(parents=True, exist_ok=True)
    if dst.exists() and dst.stat().st_size > 0:
        return {"downloaded": False, "path": dst, "bytes": dst.stat().st_size}
    tmp = dst.with_suffix(dst.suffix + ".tmp")
    req = urllib.request.Request(url, headers={"User-Agent": "CRA-Tier7.1g-NAB-preflight/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as response, tmp.open("wb") as handle:
        shutil.copyfileobj(response, handle)
    tmp.replace(dst)
    return {"downloaded": True, "path": dst, "bytes": dst.stat().st_size}


def download_source_set(cache_root: Path, commit: str, timeout: int) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    required_paths = [*CORE_SOURCE_FILES, *[f"data/{path}" for path in SELECTED_DATA_FILES]]
    for repo_path in required_paths:
        url = raw_url(commit, repo_path)
        dst = cache_path(cache_root, commit, repo_path)
        info = download_if_needed(url, dst, timeout=timeout)
        rows.append(
            {
                "repo_path": repo_path,
                "source_url": url,
                "local_cache_path": dst,
                "downloaded": info["downloaded"],
                "bytes": dst.stat().st_size,
                "sha256": sha256_file(dst),
                "role": source_role(repo_path),
            }
        )
    return rows


def source_role(repo_path: str) -> str:
    if repo_path == "LICENSE.txt":
        return "license"
    if repo_path == "README.md":
        return "source documentation"
    if repo_path.startswith("nab/"):
        return "official scoring code"
    if repo_path.startswith("config/"):
        return "official scoring configuration"
    if repo_path.startswith("labels/"):
        return "offline anomaly labels/windows"
    if repo_path.startswith("data/"):
        return "public time-series data"
    return "source"


def parse_timestamp(value: str) -> datetime:
    for fmt in ("%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            pass
    return datetime.fromisoformat(value)


def parse_nab_csv(path: Path, file_id: str) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != ["timestamp", "value"]:
            raise ValueError(f"{file_id} expected timestamp,value header; found {reader.fieldnames}")
        for index, row in enumerate(reader):
            timestamp_raw = row["timestamp"]
            dt = parse_timestamp(timestamp_raw)
            value = float(row["value"])
            if not math.isfinite(value):
                raise ValueError(f"{file_id}:{index} non-finite value")
            rows.append(
                {
                    "file": file_id,
                    "row_index": index,
                    "timestamp": timestamp_raw,
                    "parsed_timestamp": dt,
                    "value": value,
                }
            )
    if not rows:
        raise ValueError(f"{file_id} has no rows")
    raw_chronological = all(rows[i]["parsed_timestamp"] <= rows[i + 1]["parsed_timestamp"] for i in range(len(rows) - 1))
    sorted_rows = sorted(rows, key=lambda row: (row["parsed_timestamp"], row["row_index"]))
    adapter_chronological = all(
        sorted_rows[i]["parsed_timestamp"] <= sorted_rows[i + 1]["parsed_timestamp"]
        for i in range(len(sorted_rows) - 1)
    )
    values = [row["value"] for row in rows]
    return {
        "file": file_id,
        "rows": sorted_rows,
        "row_count": len(rows),
        "source_start_timestamp": rows[0]["timestamp"],
        "source_end_timestamp": rows[-1]["timestamp"],
        "adapter_start_timestamp": sorted_rows[0]["timestamp"],
        "adapter_end_timestamp": sorted_rows[-1]["timestamp"],
        "raw_chronological": raw_chronological,
        "adapter_chronological": adapter_chronological,
        "min_value": min(values),
        "max_value": max(values),
        "mean_value": sum(values) / len(values),
    }


def build_data_profiles(cache_root: Path, commit: str) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
    profile_rows: list[dict[str, Any]] = []
    parsed: dict[str, dict[str, Any]] = {}
    for file_id in SELECTED_DATA_FILES:
        path = cache_path(cache_root, commit, f"data/{file_id}")
        profile = parse_nab_csv(path, file_id)
        parsed[file_id] = profile
        profile_rows.append(
            {
                "file": file_id,
                "category": file_id.split("/", 1)[0],
                "row_count": profile["row_count"],
                "source_start_timestamp": profile["source_start_timestamp"],
                "source_end_timestamp": profile["source_end_timestamp"],
                "adapter_start_timestamp": profile["adapter_start_timestamp"],
                "adapter_end_timestamp": profile["adapter_end_timestamp"],
                "raw_chronological": profile["raw_chronological"],
                "adapter_chronological": profile["adapter_chronological"],
                "min_value": profile["min_value"],
                "max_value": profile["max_value"],
                "mean_value": profile["mean_value"],
            }
        )
    return profile_rows, parsed


def load_cached_json(cache_root: Path, commit: str, repo_path: str) -> Any:
    return json.loads(cache_path(cache_root, commit, repo_path).read_text(encoding="utf-8"))


def build_label_windows(
    combined_windows: dict[str, list[list[str]]],
    combined_labels: dict[str, list[list[str]]],
) -> tuple[list[dict[str, Any]], list[str]]:
    rows: list[dict[str, Any]] = []
    missing: list[str] = []
    for file_id in SELECTED_DATA_FILES:
        windows = combined_windows.get(file_id)
        labels = combined_labels.get(file_id)
        if windows is None or labels is None:
            missing.append(file_id)
            continue
        for index, window in enumerate(windows):
            if len(window) != 2:
                raise ValueError(f"{file_id} window {index} does not have start/end: {window}")
            start, end = window
            parse_timestamp(start)
            parse_timestamp(end)
            rows.append(
                {
                    "file": file_id,
                    "category": file_id.split("/", 1)[0],
                    "window_index": index,
                    "window_start": start,
                    "window_end": end,
                    "source": "labels/combined_windows.json",
                    "online_detector_access": False,
                }
            )
    return rows, missing


def build_smoke_stream(parsed_data: dict[str, dict[str, Any]], rows_per_file: int) -> list[dict[str, Any]]:
    stream_rows: list[dict[str, Any]] = []
    for file_id in SELECTED_DATA_FILES:
        category = file_id.split("/", 1)[0]
        for adapter_order_index, row in enumerate(parsed_data[file_id]["rows"][:rows_per_file]):
            stream_rows.append(
                {
                    "stream_id": file_id,
                    "category": category,
                    "adapter_order_index": adapter_order_index,
                    "source_row_index": row["row_index"],
                    "timestamp": row["timestamp"],
                    "value": row["value"],
                    "prediction_before_update": True,
                    "label_available_in_stream": False,
                    "anomaly_window_available_in_stream": False,
                    "scoring_labels_file": "tier7_1g_label_windows.csv",
                }
            )
    return stream_rows


def build_smoke_anomaly_scores(stream_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    # Prefix-only z-scores are an interface smoke, not a scoring claim.
    counts: dict[str, int] = {}
    means: dict[str, float] = {}
    m2s: dict[str, float] = {}
    score_rows: list[dict[str, Any]] = []
    for row in stream_rows:
        stream_id = str(row["stream_id"])
        x = float(row["value"])
        n = counts.get(stream_id, 0)
        mean = means.get(stream_id, 0.0)
        variance = m2s.get(stream_id, 0.0) / max(n - 1, 1) if n > 1 else 1.0
        std = math.sqrt(max(variance, 1e-12))
        score = abs((x - mean) / std) if n > 1 else 0.0
        score_rows.append(
            {
                "stream_id": stream_id,
                "adapter_order_index": row["adapter_order_index"],
                "source_row_index": row["source_row_index"],
                "timestamp": row["timestamp"],
                "anomaly_score": score,
                "score_source": "prefix_zscore_interface_smoke_not_claim",
                "label_available_in_score_row": False,
            }
        )
        n += 1
        delta = x - mean
        mean += delta / n
        delta2 = x - mean
        m2 = m2s.get(stream_id, 0.0) + delta * delta2
        counts[stream_id] = n
        means[stream_id] = mean
        m2s[stream_id] = m2
    return score_rows


def build_scoring_contract(
    cache_root: Path,
    commit: str,
    profiles: dict[str, Any],
    thresholds: dict[str, Any],
    scorer_text: str,
) -> dict[str, Any]:
    return {
        "benchmark": "Numenta Anomaly Benchmark (NAB)",
        "official_repository": NAB_REPO_URL,
        "source_commit": commit,
        "official_scorer_path": "nab/scorer.py",
        "official_scorer_sha256": sha256_file(cache_path(cache_root, commit, "nab/scorer.py")),
        "official_scorer_interface_detected": {
            "scoreCorpus": "def scoreCorpus" in scorer_text,
            "Sweeper": "Sweeper" in scorer_text,
            "profiles_config": sorted(profiles),
            "threshold_detector_count": len(thresholds),
        },
        "primary_profiles": sorted(REQUIRED_PROFILES),
        "online_detector_output_schema": [
            "timestamp",
            "value",
            "anomaly_score",
            "prediction_before_update",
        ],
        "offline_scoring_inputs": [
            "labels/combined_windows.json",
            "config/profiles.json",
            "config/thresholds.json",
        ],
        "label_access_policy": (
            "Online detector rows may not contain anomaly labels or anomaly-window membership. "
            "Labels/windows are scoring-only and must be joined after scores are emitted."
        ),
        "next_scoring_tier": "Tier 7.1h - Compact NAB Scoring Gate",
        "nonclaims": [
            "not a scored NAB result",
            "not a public usefulness claim",
            "not a baseline freeze",
            "not hardware/native transfer evidence",
            "not AGI/ASI evidence",
        ],
    }


def make_manifest(output_dir: Path, artifacts: dict[str, Path], status: str) -> dict[str, Any]:
    return {
        "tier": TIER,
        "status": status,
        "generated_at_utc": utc_now(),
        "runner_revision": RUNNER_REVISION,
        "output_dir": output_dir,
        "artifacts": [
            {"name": name, "path": path, "sha256": sha256_file(path), "bytes": path.stat().st_size}
            for name, path in sorted(artifacts.items())
        ],
    }


def write_report(output_dir: Path, payload: dict[str, Any]) -> None:
    source = payload["source"]
    selected = payload["selected_data_profile"]
    lines = [
        "# Tier 7.1g NAB Source/Data/Scoring Preflight",
        "",
        f"- Generated: `{payload['generated_at_utc']}`",
        f"- Runner revision: `{payload['runner_revision']}`",
        f"- Status: **{payload['status'].upper()}**",
        f"- Criteria: `{payload['criteria_passed']}/{payload['criteria_total']}`",
        "",
        "## Source Pin",
        "",
        f"- Official repository: {NAB_REPO_URL}",
        f"- Pinned commit: `{source['selected_commit']}`",
        f"- Remote HEAD observed: `{source['remote_head_observed']}`",
        f"- Cached source files: `{len(source['source_manifest'])}`",
        "",
        "## Selected Streams",
        "",
        f"- Selected files: `{len(selected)}`",
        f"- Total selected rows: `{sum(row['row_count'] for row in selected)}`",
        f"- Smoke stream rows: `{payload['smoke_stream_rows']}`",
        f"- Label-window rows: `{payload['label_window_rows']}`",
        "",
        "## Leakage Boundary",
        "",
        "- Smoke stream rows contain values and timestamps only; labels/windows are not present in detector rows.",
        "- Anomaly windows are emitted separately in `tier7_1g_label_windows.csv` for offline scoring only.",
        "- The prefix z-score score file is only a scoring-interface smoke, not a detector result or claim.",
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
    (output_dir / "tier7_1g_report.md").write_text("\n".join(lines), encoding="utf-8")


def run(args: argparse.Namespace) -> dict[str, Any]:
    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    cache_root = Path(args.data_cache).resolve()
    commit = args.commit.strip() or PINNED_NAB_COMMIT

    prior = read_json(TIER7_1F_RESULTS) if TIER7_1F_RESULTS.exists() else {}
    remote_head = resolve_remote_head(timeout=args.timeout)
    source_manifest = download_source_set(cache_root, commit, timeout=args.timeout)
    source_paths_ok = all(Path(row["local_cache_path"]).exists() and Path(row["local_cache_path"]).stat().st_size > 0 for row in source_manifest)

    profiles = load_cached_json(cache_root, commit, "config/profiles.json")
    thresholds = load_cached_json(cache_root, commit, "config/thresholds.json")
    combined_windows = load_cached_json(cache_root, commit, "labels/combined_windows.json")
    combined_labels = load_cached_json(cache_root, commit, "labels/combined_labels.json")
    tiny_windows = load_cached_json(cache_root, commit, "labels/combined_windows_tiny.json")
    scorer_text = cache_path(cache_root, commit, "nab/scorer.py").read_text(encoding="utf-8")

    selected_profiles, parsed_data = build_data_profiles(cache_root, commit)
    label_windows, missing_label_keys = build_label_windows(combined_windows, combined_labels)
    smoke_stream = build_smoke_stream(parsed_data, rows_per_file=args.smoke_rows_per_file)
    smoke_scores = build_smoke_anomaly_scores(smoke_stream)
    scoring_contract = build_scoring_contract(cache_root, commit, profiles, thresholds, scorer_text)

    stream_has_label_columns = any(
        key.lower() in {"label", "labels", "is_anomaly", "anomaly", "anomaly_window"}
        for row in smoke_stream
        for key in row
    )
    raw_non_chronological_files = [row["file"] for row in selected_profiles if not row["raw_chronological"]]
    all_adapter_chronological = all(row["adapter_chronological"] for row in selected_profiles)
    profiles_present = REQUIRED_PROFILES.issubset(set(profiles))
    thresholds_have_standard = "null" in thresholds and "standard" in thresholds.get("null", {})

    criteria = [
        criterion("Tier 7.1f contract exists", TIER7_1F_RESULTS, "exists", TIER7_1F_RESULTS.exists()),
        criterion("Tier 7.1f selected NAB", prior.get("selected_adapter", {}).get("adapter_id"), "== numenta_nab_streaming_anomaly", prior.get("selected_adapter", {}).get("adapter_id") == "numenta_nab_streaming_anomaly"),
        criterion("NAB source commit pinned", commit, "40 hex chars", len(commit) == 40 and all(ch in "0123456789abcdef" for ch in commit.lower())),
        criterion("official remote reachable or pinned cache usable", {"remote_head": remote_head, "source_paths_ok": source_paths_ok}, "remote observed or cache non-empty", remote_head is not None or source_paths_ok),
        criterion("required NAB source files cached", len(source_manifest), f"== {len(CORE_SOURCE_FILES) + len(SELECTED_DATA_FILES)}", len(source_manifest) == len(CORE_SOURCE_FILES) + len(SELECTED_DATA_FILES) and source_paths_ok),
        criterion("license source cached", any(row["repo_path"] == "LICENSE.txt" and row["bytes"] > 0 for row in source_manifest), "LICENSE.txt non-empty", any(row["repo_path"] == "LICENSE.txt" and row["bytes"] > 0 for row in source_manifest)),
        criterion("combined windows parsed", len(combined_windows), ">= 50 streams", isinstance(combined_windows, dict) and len(combined_windows) >= 50),
        criterion("combined labels parsed", len(combined_labels), ">= 50 streams", isinstance(combined_labels, dict) and len(combined_labels) >= 50),
        criterion("tiny windows parsed", len(tiny_windows), ">= 1 stream", isinstance(tiny_windows, dict) and len(tiny_windows) >= 1),
        criterion("selected NAB files predeclared", SELECTED_DATA_FILES, ">= 5 files", len(SELECTED_DATA_FILES) >= 5),
        criterion("selected data files parsed", {row["file"]: row["row_count"] for row in selected_profiles}, "all > 0 rows", all(row["row_count"] > 0 for row in selected_profiles)),
        criterion("selected raw chronology irregularities documented", raw_non_chronological_files, "documented list allowed", isinstance(raw_non_chronological_files, list)),
        criterion("selected adapter streams chronological", all_adapter_chronological, "all true after adapter sort", all_adapter_chronological),
        criterion("selected label keys present", missing_label_keys, "empty", not missing_label_keys),
        criterion("label-window rows generated", len(label_windows), "> 0", len(label_windows) > 0),
        criterion("smoke stream generated", len(smoke_stream), "> 0", len(smoke_stream) > 0),
        criterion("smoke stream labels separated", {"has_label_columns": stream_has_label_columns, "label_flags": [row["label_available_in_stream"] for row in smoke_stream[:5]]}, "no label columns and all flags false", not stream_has_label_columns and all(not row["label_available_in_stream"] and not row["anomaly_window_available_in_stream"] for row in smoke_stream)),
        criterion("prediction-before-update declared", all(row["prediction_before_update"] for row in smoke_stream), "all true", all(row["prediction_before_update"] for row in smoke_stream)),
        criterion("scoring profiles present", sorted(profiles), f"contains {sorted(REQUIRED_PROFILES)}", profiles_present),
        criterion("thresholds parse with standard profile", {"detectors": len(thresholds), "null_standard": thresholds_have_standard}, "detectors > 0 and null standard present", len(thresholds) > 0 and thresholds_have_standard),
        criterion("official scorer interface detectable", scoring_contract["official_scorer_interface_detected"], "scoreCorpus and Sweeper found", scoring_contract["official_scorer_interface_detected"]["scoreCorpus"] and scoring_contract["official_scorer_interface_detected"]["Sweeper"]),
        criterion("smoke anomaly-score schema generated", len(smoke_scores), "same row count as stream", len(smoke_scores) == len(smoke_stream) and len(smoke_scores) > 0),
        criterion("no CRA/baseline scoring performed", "preflight only", "true", True),
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
        "source": {
            "official_repository": NAB_REPO_URL,
            "official_git_url": NAB_GIT_URL,
            "selected_commit": commit,
            "remote_head_observed": remote_head,
            "data_cache_local_ignored": cache_root,
            "source_manifest": source_manifest,
            "raw_data_git_policy": "raw NAB cache is local-only and ignored by .gitignore",
        },
        "selected_data_files": SELECTED_DATA_FILES,
        "selected_data_profile": selected_profiles,
        "label_window_rows": len(label_windows),
        "smoke_stream_rows": len(smoke_stream),
        "smoke_score_rows": len(smoke_scores),
        "scoring_contract": scoring_contract,
        "claim_boundary": (
            "Tier 7.1g verifies official NAB source pinning/cache, selected data/label parsing, "
            "label-separated online stream smoke rows, and scoring-interface feasibility. It is not "
            "NAB scoring, not public usefulness evidence, not a baseline freeze, and not "
            "hardware/native transfer evidence."
        ),
        "next_step": (
            "Tier 7.1h may run a compact NAB scoring gate only after this preflight passes. "
            "Tier 7.1h must compare CRA v2.2/v2.3 against fair online anomaly baselines, "
            "sham controls, and predeclared thresholds/metrics without label leakage."
        ),
    }

    paths = {
        "results_json": output_dir / "tier7_1g_results.json",
        "source_manifest_json": output_dir / "tier7_1g_source_manifest.json",
        "source_manifest_csv": output_dir / "tier7_1g_source_manifest.csv",
        "selected_files_csv": output_dir / "tier7_1g_selected_files.csv",
        "smoke_stream_csv": output_dir / "tier7_1g_smoke_stream.csv",
        "label_windows_csv": output_dir / "tier7_1g_label_windows.csv",
        "smoke_scores_csv": output_dir / "tier7_1g_smoke_anomaly_scores.csv",
        "scoring_contract_json": output_dir / "tier7_1g_scoring_interface_contract.json",
        "summary_csv": output_dir / "tier7_1g_summary.csv",
        "report_md": output_dir / "tier7_1g_report.md",
    }
    write_json(paths["results_json"], payload)
    write_json(paths["source_manifest_json"], {"source_manifest": source_manifest})
    write_csv(paths["source_manifest_csv"], source_manifest)
    write_csv(paths["selected_files_csv"], selected_profiles)
    write_csv(paths["smoke_stream_csv"], smoke_stream)
    write_csv(paths["label_windows_csv"], label_windows)
    write_csv(paths["smoke_scores_csv"], smoke_scores)
    write_json(paths["scoring_contract_json"], scoring_contract)
    write_csv(paths["summary_csv"], [{"criterion": c["name"], "passed": c["passed"], "value": c["value"], "rule": c["rule"]} for c in criteria])
    write_report(output_dir, payload)
    manifest = make_manifest(output_dir, paths, status)
    manifest_path = output_dir / "tier7_1g_latest_manifest.json"
    write_json(manifest_path, manifest)
    latest_path = CONTROLLED / "tier7_1g_latest_manifest.json"
    write_json(latest_path, manifest)
    return payload


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--data-cache", default=str(DATA_CACHE))
    parser.add_argument("--commit", default=PINNED_NAB_COMMIT)
    parser.add_argument("--timeout", type=int, default=60)
    parser.add_argument("--smoke-rows-per-file", type=int, default=80)
    return parser.parse_args()


def main() -> None:
    payload = run(parse_args())
    print(
        json.dumps(
            {
                "status": payload["status"],
                "criteria": f"{payload['criteria_passed']}/{payload['criteria_total']}",
                "output_dir": str(payload["output_dir"]),
                "selected_commit": payload["source"]["selected_commit"],
                "selected_files": len(payload["selected_data_files"]),
            },
            indent=2,
        )
    )
    if payload["status"] != "pass":
        raise SystemExit(1)


if __name__ == "__main__":
    main()

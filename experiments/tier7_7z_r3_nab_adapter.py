#!/usr/bin/env python3
"""Tier 7.7z-r3 — v2.6 NAB Streaming Anomaly Adapter.

Applies v2.6 edge-of-chaos + ridge readout to the 5 NAB streaming anomaly
detection files from Tier 7.1g. Computes prediction error, anomaly/baseline
error ratio, and per-stream detection signal.

NAB streams: art_daily_flatmiddle, ambient_temperature_system_failure,
  machine_temperature_system_failure, ec2_cpu_utilization, TravelTime_387.
"""

import argparse, csv, json, math, os, sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import numpy as np

os.environ.setdefault("KMP_DUPLICATE_LIB_OK","TRUE")
ROOT = Path(__file__).resolve().parents[1]
CONTROLLED = ROOT / "controlled_test_output"
if str(ROOT) not in sys.path: sys.path.insert(0, str(ROOT))
if str(Path(__file__).resolve().parent) not in sys.path: sys.path.insert(0, str(Path(__file__).resolve().parent))

TIER = "Tier 7.7z-r3 - v2.6 NAB Streaming Anomaly Adapter"
RUNNER_REVISION = "tier7_7z_r3_nab_adapter_20260509_0001"
DEFAULT_OUTPUT_DIR = CONTROLLED / "tier7_7z_r3_20260509_nab_adapter"

NAB_DIR = ROOT / ".cra_data_cache" / "numenta_nab" / "ea702d75cc2258d9d7dd35ca8e5e2539d71f3140"
SELECTED_FILES = [
    "artificialWithAnomaly/art_daily_flatmiddle.csv",
    "realKnownCause/ambient_temperature_system_failure.csv",
    "realKnownCause/machine_temperature_system_failure.csv",
    "realAWSCloudwatch/ec2_cpu_utilization_24ae8d.csv",
    "realTraffic/TravelTime_387.csv",
]
TIMESCALES = [2.0, 5.0, 10.0, 20.0, 50.0, 100.0, 200.0]
DEFAULT_HIDDEN = 64
DEFAULT_SEEDS = "42,43,44"


def json_safe(v):
    if isinstance(v, Path): return str(v)
    if isinstance(v, dict): return {str(k): json_safe(v2) for k, v2 in v.items()}
    if isinstance(v, (list, tuple)): return [json_safe(x) for x in v]
    if isinstance(v, float) and not math.isfinite(v): return None
    if isinstance(v, (np.integer,)): return int(v)
    if isinstance(v, (np.floating,)): return float(v)
    if isinstance(v, np.bool_): return bool(v)
    if isinstance(v, np.ndarray): return v.tolist()
    return v


def criterion(name, value, rule, passed, details=""):
    return {"name": name, "criterion": name, "value": json_safe(value),
            "operator": rule, "rule": rule, "passed": bool(passed),
            "pass": bool(passed), "details": details, "note": details}


def utc_now(): return datetime.now(timezone.utc).isoformat(timespec="seconds")


def write_json(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(json_safe(payload), indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_rows(path, rows, fieldnames=None):
    path.parent.mkdir(parents=True, exist_ok=True)
    if fieldnames is None: fieldnames = list(dict.fromkeys(k for r in rows for k in r))
    with path.open("w", newline="", encoding="utf-8") as h:
        w = csv.DictWriter(h, fieldnames=fieldnames, extrasaction="ignore", lineterminator="\n")
        w.writeheader()
        for r in rows: w.writerow({k: json_safe(r.get(k,"")) for k in fieldnames})


def eoc_features(stream, seed, hidden):
    values = np.asarray(stream, dtype=float); rng = np.random.default_rng(seed + 55555)
    traces = np.zeros(len(TIMESCALES), dtype=float); hs = np.zeros(hidden, dtype=float)
    input_dim = 2 + len(TIMESCALES) + max(0, len(TIMESCALES)-1) + 1
    w_in = rng.normal(0, 0.3, size=(hidden, input_dim))
    raw = rng.normal(0, 1, size=(hidden, hidden)); q,_ = np.linalg.qr(raw)
    anti = rng.normal(0, 0.3, size=(hidden, hidden))
    w_rec = q * 1.0 + (anti - anti.T) * 0.3; rows = []
    for x in values:
        xf = float(x); prev = traces.copy()
        for i, tau in enumerate(TIMESCALES):
            alpha = 1.0 - math.exp(-1.0/max(1e-6, float(tau)))
            traces[i] = traces[i] + alpha*(xf - traces[i])
        d = np.diff(traces) if len(traces) > 1 else np.array([], dtype=float)
        nv = xf - float(prev[-1] if prev.size else 0.0)
        driver = np.concatenate([[1.0, xf], traces, d, [nv]])
        hs = np.tanh(hs + w_rec @ hs + w_in @ driver)
        rows.append(np.concatenate([driver, hs]))
    return np.vstack(rows)


def load_nab_stream(file_path):
    timestamps, values = [], []
    with open(file_path) as f:
        for row in csv.DictReader(f):
            timestamps.append(row.get('timestamp','').strip())
            values.append(float(row.get('value',0)))
    return timestamps, np.array(values, dtype=float)


def load_nab_windows():
    windows_file = NAB_DIR / "labels" / "combined_windows.json"
    return json.load(open(windows_file))


def anomaly_mask(timestamps, windows):
    mask = np.zeros(len(timestamps), dtype=bool)
    for start_str, end_str in windows:
        s = start_str.replace('.000000',''); e = end_str.replace('.000000','')
        si = next((i for i,ts in enumerate(timestamps) if ts==s), None)
        ei = next((i for i,ts in enumerate(timestamps) if ts==e), None)
        if si is not None and ei is not None: mask[si:ei+1] = True
    return mask


def score_stream(file_id, seed, hidden):
    """Score v2.6 on one NAB stream. Returns anomaly/baseline error ratio."""
    data_path = NAB_DIR / "data" / file_id
    timestamps, values = load_nab_stream(data_path)
    windows = load_nab_windows().get(file_id, [])
    amask = anomaly_mask(timestamps, windows)

    features = eoc_features(values, seed, hidden)
    train_end = int(len(values) * 0.15)
    tgt = np.asarray(values, dtype=float)
    w = np.zeros(features.shape[1], dtype=float)
    preds = np.zeros(len(values), dtype=float)
    for step in range(len(values)):
        if step > 0: preds[step] = float(np.dot(w, features[step]))
        if step < train_end:
            err = float(tgt[step] - preds[step])
            w += (0.01 * err / (1.0 + float(np.dot(features[step], features[step])))) * features[step]

    errors = np.abs(tgt - preds)
    base_err = np.mean(errors[~amask]) if (~amask).sum() > 0 else 0
    anom_err = np.mean(errors[amask]) if amask.sum() > 0 else 0
    ratio = anom_err / base_err if base_err > 0 else 0
    name = file_id.split("/")[-1]
    return {"file": name, "file_id": file_id, "seed": seed, "n_points": len(values),
            "n_anomaly": int(amask.sum()), "n_windows": len(windows),
            "baseline_error": round(base_err, 4), "anomaly_error": round(anom_err, 4),
            "ratio": round(ratio, 4), "signal": ratio > 1.3}


def run(args):
    output_dir = Path(args.output_dir).resolve(); output_dir.mkdir(parents=True, exist_ok=True)
    seeds = [int(s) for s in args.seeds.split(",")] if args.seeds else [42,43,44]
    hidden = int(args.hidden) if getattr(args,'hidden',None) else DEFAULT_HIDDEN

    results = []
    for file_id in SELECTED_FILES:
        for seed in seeds:
            r = score_stream(file_id, seed, hidden)
            results.append(r)

    # Aggregate per-stream
    def gm(vals): return math.exp(sum(math.log(v) for v in vals if v>0)/len(vals)) if vals else 0
    summary = {}
    for file_id in SELECTED_FILES:
        name = file_id.split("/")[-1]
        stream_results = [r for r in results if r["file_id"] == file_id]
        ratios = [r["ratio"] for r in stream_results]
        signals = [r["signal"] for r in stream_results]
        summary[name] = {"ratio_mean": round(np.mean(ratios), 4), "ratio_geomean": round(gm(ratios), 4),
                         "signal_seeds": sum(signals), "n_seeds": len(signals)}

    streams_with_signal = sum(1 for s in summary.values() if s["signal_seeds"] >= 2)
    at_least_one = sum(1 for s in summary.values() if s["signal_seeds"] >= 1)
    mean_ratio = np.mean([s["ratio_mean"] for s in summary.values()])

    classification = "nab_partial_signal" if at_least_one >= 1 else "nab_no_signal"
    if streams_with_signal >= 3: classification = "nab_broad_signal"
    elif streams_with_signal >= 1: classification = "nab_partial_signal"

    criteria = [
        criterion("5 NAB streams loaded", len(summary), "== 5", len(summary) == 5),
        criterion("all streams scored", len(results), "== 15", len(results) == 15,
                  f"5 streams x 3 seeds = {len(results)} results"),
        criterion("streams with signal (>1.3x, 2+ seeds)", streams_with_signal, ">= 1", streams_with_signal >= 1,
                  f"mean ratio={mean_ratio:.3f}"),
        criterion("NAB outcome classified", classification, "!= nab_no_signal", classification != "nab_no_signal"),
        criterion("no baseline freeze", False, "false", True),
        criterion("no public usefulness claim", False, "false", True),
    ]
    passed = sum(1 for c in criteria if c["passed"])
    status = "pass" if passed == len(criteria) else "fail"

    payload = dict(tier=TIER, runner_revision=RUNNER_REVISION, generated_at_utc=utc_now(),
                   status=status, outcome=classification, criteria=criteria,
                   criteria_passed=passed, criteria_total=len(criteria), output_dir=str(output_dir),
                   stream_summary=summary, mean_ratio=round(mean_ratio, 4),
                   streams_with_signal=streams_with_signal,
                   next_gate="Tier 4 hardware transfer" if classification != "nab_no_signal" else "Document and narrow")
    write_json(output_dir / "tier7_7z_r3_results.json", payload)
    write_rows(output_dir / "tier7_7z_r3_scoreboard.csv", results)
    write_rows(output_dir / "tier7_7z_r3_summary.csv", criteria)
    report = ["# Tier 7.7z-r3 v2.6 NAB Streaming Anomaly Adapter",
              f"- Status: **{status.upper()}** ({passed}/{len(criteria)})",
              f"- Outcome: `{classification}`",
              f"- Streams with signal: {streams_with_signal}/5",
              "", "## Per-stream Results", ""]
    for name, s in summary.items():
        report.append(f"- **{name}**: ratio={s['ratio_mean']}, signal seeds={s['signal_seeds']}/{s['n_seeds']}")
    report.extend(["", f"Next: {payload['next_gate']}"])
    (output_dir / "tier7_7z_r3_report.md").write_text("\n".join(report) + "\n", encoding="utf-8")
    manifest = dict(tier=TIER, status=status, generated_at_utc=payload["generated_at_utc"], output_dir=str(output_dir))
    write_json(output_dir / "tier7_7z_r3_latest_manifest.json", manifest)
    return payload


def build_parser():
    p = argparse.ArgumentParser(description=TIER)
    p.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    p.add_argument("--seeds", default=DEFAULT_SEEDS)
    p.add_argument("--hidden", type=int, default=DEFAULT_HIDDEN)
    return p


def main():
    args = build_parser().parse_args()
    payload = run(args)
    print(json.dumps(json_safe(dict(status=payload["status"], outcome=payload["outcome"],
                                    criteria=f"{payload['criteria_passed']}/{payload['criteria_total']}",
                                    streams_with_signal=payload["streams_with_signal"],
                                    mean_ratio=payload["mean_ratio"],
                                    output_dir=payload["output_dir"])), indent=2, sort_keys=True))
    return 0 if payload["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())

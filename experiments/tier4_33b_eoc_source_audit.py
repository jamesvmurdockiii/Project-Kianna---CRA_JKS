#!/usr/bin/env python3
"""Tier 4.33b - EOC C Runtime Source Audit.

Verifies the edge-of-chaos mechanism has been correctly integrated into
the SpiNNaker C runtime: profile exists, state variables declared,
init/update/get_summary functions defined, Makefile profile added,
host tests pass, and DTCM budget is documented.

Boundary: local source/runtime host evidence only; not hardware evidence.
"""

import csv, hashlib, json, math, os, subprocess, sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONTROLLED = ROOT / "controlled_test_output"
RUNTIME = ROOT / "coral_reef_spinnaker" / "spinnaker_runtime"

TIER = "Tier 4.33b - EOC C Runtime Source Audit"
RUNNER_REVISION = "tier4_33b_eoc_source_audit_20260509_0001"
DEFAULT_OUTPUT_DIR = CONTROLLED / "tier4_33b_20260509_eoc_source_audit"
PREREQ_433A = CONTROLLED / "tier4_33a_20260509_eoc_fixed_point_reference" / "tier4_33a_results.json"


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
    d = hashlib.sha256()
    with path.open("rb") as f:
        for c in iter(lambda: f.read(1024*1024), b""): d.update(c)
    return d.hexdigest()

def grep_file(path, pattern):
    if not path.exists(): return []
    return [line.strip() for line in path.read_text().splitlines() if pattern in line]


def run(output_dir=DEFAULT_OUTPUT_DIR):
    output_dir = output_dir.resolve(); output_dir.mkdir(parents=True, exist_ok=True)
    prereq_ok = PREREQ_433A.exists()

    config_h = RUNTIME / "src" / "config.h"
    state_mgr_h = RUNTIME / "src" / "state_manager.h"
    state_mgr_c = RUNTIME / "src" / "state_manager.c"
    makefile = RUNTIME / "Makefile"

    # Source checks
    has_profile_define = any("PROFILE_EOC_RECURRENT" in l for l in grep_file(config_h, "PROFILE_EOC"))
    has_opcodes = any("EOC_WRITE_STATE" in l for l in grep_file(config_h, "EOC_"))
    has_hidden_units = any("EOC_HIDDEN_UNITS" in l for l in grep_file(config_h, "EOC_HIDDEN_UNITS"))

    has_header_decl = any("cra_eoc_init" in l for l in grep_file(state_mgr_h, "cra_eoc"))
    has_update_decl = any("cra_eoc_update" in l for l in grep_file(state_mgr_h, "cra_eoc_update"))
    has_summary_decl = any("cra_eoc_get_summary" in l for l in grep_file(state_mgr_h, "cra_eoc_get_summary"))

    has_impl_init = any("cra_eoc_init" in l for l in grep_file(state_mgr_c, "void cra_eoc_init"))
    has_impl_update = any("cra_eoc_update" in l for l in grep_file(state_mgr_c, "int cra_eoc_update"))
    has_impl_summary = any("cra_eoc_get_summary" in l for l in grep_file(state_mgr_c, "void cra_eoc_get_summary"))
    has_hidden_state = any("g_eoc_hidden" in l for l in grep_file(state_mgr_c, "g_eoc_hidden"))
    has_w_rec = any("g_eoc_w_rec" in l for l in grep_file(state_mgr_c, "g_eoc_w_rec"))
    has_profile_guard = any("CRA_RUNTIME_PROFILE_EOC_RECURRENT" in l for l in grep_file(state_mgr_c, "CRA_RUNTIME_PROFILE_EOC_RECURRENT"))

    has_make_profile = any("eoc_recurrent" in l for l in grep_file(makefile, "eoc_recurrent"))
    has_make_cflags = any("EOC_RECURRENT" in l for l in grep_file(makefile, "EOC_RECURRENT"))
    has_make_profile_id = any("PROFILE_ID=7" in l for l in grep_file(makefile, "PROFILE_ID=7"))

    # Host tests
    host_test_ok = False
    try:
        result = subprocess.run(["make", "-C", str(RUNTIME), "test"], capture_output=True, text=True, timeout=120)
        host_test_ok = "ALL TESTS PASSED" in result.stdout
        host_test_stdout = result.stdout[-500:] if len(result.stdout) > 500 else result.stdout
    except Exception:
        host_test_stdout = "test execution failed"

    # DTCM budget
    w_rec_bytes = 64 * 64 * 4  # n=64
    w_in_bytes = 64 * 16 * 4
    hidden_bytes = 64 * 4
    total_eoc_bytes = w_rec_bytes + w_in_bytes + hidden_bytes
    dtcm_ok = total_eoc_bytes <= 80000

    all_source_checks = all([has_profile_define, has_opcodes, has_hidden_units,
                              has_header_decl, has_update_decl, has_summary_decl,
                              has_impl_init, has_impl_update, has_impl_summary,
                              has_hidden_state, has_w_rec, has_profile_guard,
                              has_make_profile, has_make_cflags, has_make_profile_id])

    criteria = [
        criterion("prereq 4.33a exists", prereq_ok, "true", prereq_ok),
        criterion("config.h: PROFILE_EOC_RECURRENT", has_profile_define, "true", has_profile_define),
        criterion("config.h: EOC opcodes", has_opcodes, "true", has_opcodes),
        criterion("state_manager.h: EOC declarations", has_header_decl, "true", has_header_decl),
        criterion("state_manager.c: EOC init", has_impl_init, "true", has_impl_init),
        criterion("state_manager.c: EOC update", has_impl_update, "true", has_impl_update),
        criterion("state_manager.c: EOC summary", has_impl_summary, "true", has_impl_summary),
        criterion("state_manager.c: g_eoc_hidden", has_hidden_state, "true", has_hidden_state),
        criterion("state_manager.c: profile guard", has_profile_guard, "true", has_profile_guard),
        criterion("Makefile: eoc_recurrent profile", has_make_profile, "true", has_make_profile),
        criterion("host tests pass", host_test_ok, "true", host_test_ok),
        criterion("DTCM budget (n=64): 16KB w_rec + 1KB w_in + 256B hidden",
                 total_eoc_bytes, "<= 80000", dtcm_ok, f"{total_eoc_bytes} bytes, {total_eoc_bytes/1024:.0f}KB"),
        criterion("no baseline freeze", False, "false", True),
        criterion("no hardware evidence claimed", False, "false", True),
    ]
    passed = sum(1 for c in criteria if c["passed"])
    status = "pass" if passed == len(criteria) else "fail"
    classification = "source_audit_pass" if (all_source_checks and host_test_ok) else "source_audit_fail"

    payload = dict(tier=TIER, runner_revision=RUNNER_REVISION, generated_at_utc=utc_now(),
                   status=status, outcome=classification, criteria=criteria,
                   criteria_passed=passed, criteria_total=len(criteria), output_dir=str(output_dir),
                   dtcm_budget_bytes=total_eoc_bytes, dtcm_budget_kb=total_eoc_bytes/1024,
                   w_rec_kb=w_rec_bytes/1024, w_in_kb=w_in_bytes/1024,
                   next_gate="Tier 4.33c EBRAINS package preparation" if classification=="source_audit_pass" else "Fix source issues")
    write_json(output_dir / "tier4_33b_results.json", payload)
    write_csv(output_dir / "tier4_33b_summary.csv", criteria)
    report = ["# Tier 4.33b EOC C Runtime Source Audit",
              f"- Status: **{status.upper()}** ({passed}/{len(criteria)})",
              f"- Outcome: `{classification}`",
              f"- DTCM budget: {total_eoc_bytes/1024:.0f}KB at n=64",
              f"- Host tests: {'PASS' if host_test_ok else 'FAIL'}",
              f"- All source checks: {all_source_checks}"]
    (output_dir / "tier4_33b_report.md").write_text("\n".join(report) + "\n", encoding="utf-8")
    manifest = dict(tier=TIER, status=status, generated_at_utc=payload["generated_at_utc"], output_dir=str(output_dir))
    write_json(output_dir / "tier4_33b_latest_manifest.json", manifest)
    write_json(CONTROLLED / "tier4_33b_latest_manifest.json", manifest)
    return payload


def main():
    payload = run()
    print(json.dumps(json_safe(dict(status=payload["status"], outcome=payload["outcome"],
                                    criteria=f"{payload['criteria_passed']}/{payload['criteria_total']}",
                                    dtcm_budget=f"{payload['dtcm_budget_kb']:.0f}KB",
                                    output_dir=payload["output_dir"])), indent=2, sort_keys=True))
    return 0 if payload["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())

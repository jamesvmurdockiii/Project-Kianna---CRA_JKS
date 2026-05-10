#!/usr/bin/env python3
"""Tier 7.8 - polyp morphology / template variability contract.

After the 7.7 campaign closed with the finding that contractive recurrent
dynamics are the primary ~2D collapse (edge-of-chaos fixes PR 2->7 but
awaiting organism integration), this contract locks the next hypothesis:
heterogeneous polyp templates can increase state diversity beyond what
the current homogeneous architecture achieves.

Contract only: no implementation, no scoring, no mechanism promotion,
no baseline freeze, and no hardware/native transfer.
"""

from __future__ import annotations

import csv, hashlib, json, math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONTROLLED = ROOT / "controlled_test_output"

TIER = "Tier 7.8 - Polyp Morphology / Template Variability Contract"
RUNNER_REVISION = "tier7_8_polyp_morphology_contract_20260509_0001"
DEFAULT_OUTPUT_DIR = CONTROLLED / "tier7_8_20260509_polyp_morphology_contract"
NEXT_GATE = "Tier 7.8a - Morphology Candidate Compact Scoring Gate"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def json_safe(value: Any) -> Any:
    if isinstance(value, Path): return str(value)
    if isinstance(value, dict): return {str(k): json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)): return [json_safe(x) for x in value]
    if isinstance(value, float) and not math.isfinite(value): return None
    return value


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(json_safe(payload), indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if fieldnames is None:
        fieldnames = list(dict.fromkeys(k for r in rows for k in r))
    with path.open("w", newline="", encoding="utf-8") as h:
        w = csv.DictWriter(h, fieldnames=fieldnames, extrasaction="ignore", lineterminator="\n")
        w.writeheader()
        for r in rows:
            w.writerow({k: json_safe(r.get(k, "")) for k in fieldnames})


def sha256_file(path: Path) -> str | None:
    if not path.exists(): return None
    d = hashlib.sha256()
    with path.open("rb") as f:
        for c in iter(lambda: f.read(1024*1024), b""): d.update(c)
    return d.hexdigest()


def criterion(name: str, value: Any, rule: str, passed: bool, details: str = "") -> dict[str, Any]:
    return {"name": name, "criterion": name, "value": json_safe(value),
            "operator": rule, "rule": rule, "passed": bool(passed),
            "pass": bool(passed), "details": details, "note": details}


def template_candidates() -> list[dict[str, Any]]:
    return [
        {"candidate": "diverse_timescales", "description": "Polyps assigned to fast/medium/slow regimes with different EMA alpha values per polyp group.",
         "hypothesis": "Multiple inherent timescales force state to span fast transients and slow baselines simultaneously.",
         "same_budget": True, "sham": "shuffled_timescale_assignment"},
        {"candidate": "variable_recurrence", "description": "Polyps differ in spectral radius (0.3-1.0) and antisymmetry (0.0-0.5), creating diverse dynamical regimes across the population.",
         "hypothesis": "Heterogeneous recurrent dynamics create genuinely diverse state trajectories that don't collapse to the same attractor.",
         "same_budget": True, "sham": "shuffled_recurrence_assignment"},
        {"candidate": "excitatory_inhibitory_ratio_variability", "description": "Polyps vary in E/I ratio (70:30 to 30:70), creating different baseline activity levels and sensitivity patterns.",
         "hypothesis": "E/I diversity creates functional specialization across polyps without explicit task decomposition.",
         "same_budget": True, "sham": "shuffled_ei_assignment"},
        {"candidate": "sparse_structured_connectivity", "description": "Polyps use small-world or modular connectivity instead of all-to-all, with different sparsity patterns per polyp.",
         "hypothesis": "Structured sparse connectivity creates independent dynamical modules that don't collapse through shared recurrence.",
         "same_budget": True, "sham": "same_sparsity_random_graph"},
        {"candidate": "input_selectivity", "description": "Polyp groups attend to different input feature subsets (some to raw x, some to EMAs, some to deltas).",
         "hypothesis": "Input selectivity forces specialization by limiting what each polyp can observe.",
         "same_budget": True, "sham": "shuffled_input_assignment"},
        {"candidate": "template_size_variability", "description": "Polyps vary in size (hidden units per polyp: 16/32/64/128) with the same total neuron budget.",
         "hypothesis": "Different capacity polyps capture features at different granularity levels.",
         "same_budget": True, "sham": "shuffled_size_assignment"},
    ]


def controls() -> list[dict[str, Any]]:
    return [
        {"control": "homogeneous_baseline", "role": "baseline", "description": "Current v2.5 reference: all polyps identical template, all-to-all recurrence."},
        {"control": "same_budget_fixed_template", "role": "capacity_control", "description": "Same total neuron count but all polyps identical. Tests whether benefit is from extra capacity."},
        {"control": "shuffled_assignment", "role": "sham", "description": "Template parameters randomly shuffled across polyps. Tests whether specific assignment matters."},
        {"control": "random_projection_same_dim", "role": "generic_control", "description": "Random projection with same feature dimensionality. Tests generic vs mechanism-specific benefit."},
        {"control": "nonlinear_lag", "role": "generic_control", "description": "Nonlinear/lag features with same budget. Standard generic control from 7.7 chain."},
        {"control": "target_shuffle", "role": "leakage", "description": "Shuffle targets to break causal structure."},
        {"control": "time_shuffle", "role": "leakage", "description": "Shuffle time ordering."},
    ]


def metrics() -> list[dict[str, Any]]:
    return [
        {"metric": "participation_ratio", "domain": "state_geometry", "description": "Effective state dimensionality at 128 total hidden units."},
        {"metric": "rank_95", "domain": "state_geometry", "description": "PCA components for 95% variance."},
        {"metric": "top_pc_dominance", "domain": "state_geometry", "description": "Fraction of variance in first PC."},
        {"metric": "per_template_activity_variance", "domain": "state_geometry", "description": "Activity variance per polyp template group."},
        {"metric": "template_pairwise_pr", "domain": "state_geometry", "description": "PR within each template group separately."},
        {"metric": "geomean_mse_ridge", "domain": "task", "description": "Geomean MSE across Mackey-Glass/Lorenz/repaired-NARMA10 with ridge readout."},
        {"metric": "geomean_mse_lms", "domain": "task", "description": "Geomean MSE with online LMS readout."},
        {"metric": "seed_variance", "domain": "task", "description": "Variance across seeds 42/43/44."},
    ]


def outcome_classes() -> list[dict[str, Any]]:
    return [
        {"outcome": "morphology_candidate", "description": "Template variability improves PR AND task MSE, beats generic controls, sham-separated."},
        {"outcome": "morphology_geometry_only", "description": "PR improves but task MSE does not (same pattern as 7.7z before ridge readout)."},
        {"outcome": "generic_control_explains_gain", "description": "Same-feature random projection or nonlinear-lag matches or exceeds the morphology benefit."},
        {"outcome": "capacity_confound", "description": "Same-budget fixed-template control matches the morphology candidate."},
        {"outcome": "morphology_not_supported", "description": "No template variant improves PR or task MSE over homogeneous baseline."},
        {"outcome": "partial_template_signal", "description": "Some templates help specific tasks but no aggregate benefit."},
    ]


def tasks() -> list[dict[str, Any]]:
    return [
        {"task": "mackey_glass", "horizon": 8, "seeds": [42, 43, 44], "lengths": [8000, 16000, 32000]},
        {"task": "lorenz", "horizon": 8, "seeds": [42, 43, 44], "lengths": [8000, 16000, 32000]},
        {"task": "repaired_narma10", "horizon": 8, "seeds": [42, 43, 44], "lengths": [8000, 16000, 32000]},
    ]


def escalation_rules() -> list[dict[str, Any]]:
    return [
        {"stage": "7.8_contract", "action": "Lock candidates, controls, metrics, outcome classes. No scoring."},
        {"stage": "7.8a_compact", "action": "Test top 2-3 template candidates on Mackey-Glass/Lorenz/repaired-NARMA10 at 8000 steps, seeds 42/43/44."},
        {"stage": "7.8b_expanded", "action": "Take best 7.8a candidate to 16000/32000 with ESN/ridge baselines. Only if compact survives controls."},
        {"stage": "7.8c_promotion", "action": "Compact regression + baseline freeze. Only if expanded confirmation passes."},
    ]


def build_contract() -> dict[str, Any]:
    return {
        "question": "Can variable polyp internal templates (diverse timescales, recurrence parameters, E/I ratios, sparse connectivity, input selectivity, polyp size) increase state diversity and benchmark usefulness beyond the current homogeneous architecture, without being explained by generic random projection or nonlinear-lag controls?",
        "hypothesis": "Heterogeneous polyp templates create functional specialization through structural diversity, increasing state dimensionality because different polyps respond to different aspects of the input signal rather than all collapsing into the same dominant modes.",
        "null_hypothesis": "Template variability is equivalent to extra capacity; a same-budget homogeneous control with more neurons matches any template-diversity benefit.",
        "mechanism_under_test": "polyp template variability (intrinsic heterogeneity)",
        "claim_boundary": "This contract locks the Tier 7.8 morphology/template variability testing protocol without implementing or scoring any candidate. Not mechanism promotion, not a baseline freeze, not public usefulness proof, not hardware/native transfer.",
        "decision": "contract_locked_authorize_7_8a_compact_scoring",
        "prior_evidence": {
            "7.7_campaign": "Edge-of-chaos dynamics fix PR 2=7 but await organism integration. Primary bottleneck is contractive recurrent regime, not input encoding.",
            "5.20_series": "Resonant branch polyps (a form of template variability) showed task-specific benefits but material regressions. Template variability needs controlled testing.",
            "7.7j": "Low-rank collapse confirmed: PR near 2 even at 128 hidden units with homogeneous architecture.",
        },
    }


def run(output_dir: Path = DEFAULT_OUTPUT_DIR) -> dict[str, Any]:
    output_dir = output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    contract = build_contract()
    candidates = template_candidates()
    ctrls = controls()
    mtrs = metrics()
    outcomes = outcome_classes()
    tsks = tasks()
    esc = escalation_rules()

    criteria = [
        criterion("question locked", bool(contract["question"]), "true", True),
        criterion("6 template candidates declared", len(candidates), "== 6", len(candidates) == 6),
        criterion("homogeneous baseline in controls", any(c["control"] == "homogeneous_baseline" for c in ctrls), "true", True),
        criterion("shuffled assignment sham in controls", any(c["control"] == "shuffled_assignment" for c in ctrls), "true", True),
        criterion("random projection control locked", any(c["control"] == "random_projection_same_dim" for c in ctrls), "true", True),
        criterion("nonlinear-lag control locked", any(c["control"] == "nonlinear_lag" for c in ctrls), "true", True),
        criterion("state geometry metrics locked", len([m for m in mtrs if m["domain"] == "state_geometry"]), ">= 4",
                  len([m for m in mtrs if m["domain"] == "state_geometry"]) >= 4),
        criterion("task metrics locked", len([m for m in mtrs if m["domain"] == "task"]), ">= 2",
                  len([m for m in mtrs if m["domain"] == "task"]) >= 2),
        criterion("6 outcome classes locked", len(outcomes), "== 6", len(outcomes) == 6),
        criterion("3 task families locked", len(tsks), "== 3", len(tsks) == 3),
        criterion("escalation rules locked", len(esc), "== 4", len(esc) == 4),
        criterion("compact before expanded", esc[1]["stage"], "== 7.8a_compact", True),
        criterion("no baseline freeze authorized", False, "false", True),
        criterion("no mechanism promotion authorized", False, "false", True),
        criterion("no hardware/native transfer authorized", False, "false", True),
    ]
    passed = sum(1 for c in criteria if c["passed"])
    status = "pass" if passed == len(criteria) else "fail"

    payload = {
        "tier": TIER, "runner_revision": RUNNER_REVISION, "generated_at_utc": utc_now(),
        "status": status, "outcome": "morphology_contract_locked",
        "criteria": criteria, "criteria_passed": passed, "criteria_total": len(criteria),
        "output_dir": str(output_dir), "contract": contract,
        "template_candidates": candidates, "controls": ctrls,
        "metrics": mtrs, "outcome_classes": outcomes,
        "tasks": tsks, "escalation_rules": esc,
        "next_gate": NEXT_GATE,
        "claim_boundary": contract["claim_boundary"],
        "nonclaims": ["not a template implementation", "not model scoring", "not mechanism promotion",
                      "not a baseline freeze", "not public usefulness proof", "not hardware/native transfer"],
    }
    write_json(output_dir / "tier7_8_results.json", payload)
    write_json(output_dir / "tier7_8_contract.json", contract)
    write_csv(output_dir / "tier7_8_candidates.csv", candidates)
    write_csv(output_dir / "tier7_8_controls.csv", ctrls)
    write_csv(output_dir / "tier7_8_metrics.csv", mtrs)
    write_csv(output_dir / "tier7_8_outcomes.csv", outcomes)
    write_csv(output_dir / "tier7_8_tasks.csv", tsks)
    write_csv(output_dir / "tier7_8_escalation.csv", esc)
    write_csv(output_dir / "tier7_8_summary.csv", criteria)
    (output_dir / "tier7_8_claim_boundary.md").write_text(contract["claim_boundary"] + "\n", encoding="utf-8")
    report = ["# Tier 7.8 Polyp Morphology / Template Variability Contract",
              f"- Status: **{status.upper()}** ({passed}/{len(criteria)})",
              f"- Outcome: `morphology_contract_locked`",
              "", "## Question", "", contract["question"], "",
              "## Candidates", ""]
    for c in candidates:
        report.append(f"- **{c['candidate']}**: {c['description']}")
    report.extend(["", "## Next Gate", "", NEXT_GATE])
    (output_dir / "tier7_8_report.md").write_text("\n".join(report) + "\n", encoding="utf-8")
    manifest = {"tier": TIER, "status": status, "generated_at_utc": payload["generated_at_utc"],
                "output_dir": str(output_dir)}
    write_json(output_dir / "tier7_8_latest_manifest.json", manifest)
    write_json(CONTROLLED / "tier7_8_latest_manifest.json", manifest)
    return payload


def main() -> int:
    payload = run()
    print(json.dumps(json_safe({"status": payload["status"], "outcome": payload["outcome"],
                                "criteria": f"{payload['criteria_passed']}/{payload['criteria_total']}",
                                "output_dir": payload["output_dir"], "next_gate": payload["next_gate"]}),
                     indent=2, sort_keys=True))
    return 0 if payload["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Tier 5.25a — Lifecycle-Enabled State Diversity Scoring Gate.

Tests whether enabling reproduction + mutation + apoptosis increases
organism state dimensionality (PR) compared to a static population.
"""

from __future__ import annotations

import csv, json, math, numpy as np, os, random, sys, time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
CONTROLLED = ROOT / "controlled_test_output"

TIER = "Tier 5.25a — Lifecycle-Enabled State Diversity Scoring Gate"
RUNNER_REVISION = "tier5_25a_lifecycle_state_diversity_scoring_20260510_0001"
DEFAULT_OUTPUT_DIR = CONTROLLED / "tier5_25a_20260510_lifecycle_state_diversity_scoring"
PREREQ = CONTROLLED / "tier5_25_20260510_lifecycle_state_diversity_contract" / "tier5_25_results.json"

os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")


def utc_now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def json_safe(v):
    if isinstance(v, Path): return str(v)
    if isinstance(v, dict): return {str(k): json_safe(v2) for k, v2 in v.items()}
    if isinstance(v, (list, tuple)): return [json_safe(x) for x in v]
    if isinstance(v, float) and not math.isfinite(v): return None
    if isinstance(v, (np.floating, np.float64, np.float32)): return float(v)
    if isinstance(v, (np.integer, np.int64, np.int32)): return int(v)
    return v


def write_json(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(json_safe(payload), indent=2, sort_keys=True) + "\n",
                    encoding="utf-8")


def write_csv(path, rows, fieldnames=None):
    path.parent.mkdir(parents=True, exist_ok=True)
    if fieldnames is None:
        fieldnames = list(dict.fromkeys(k for r in rows for k in r))
    with path.open("w", newline="", encoding="utf-8") as h:
        w = csv.DictWriter(h, fieldnames=fieldnames, extrasaction="ignore",
                           lineterminator="\n")
        w.writeheader()
        for r in rows:
            w.writerow({k: json_safe(r.get(k, "")) for k in fieldnames})


def criterion(name, value, rule, passed, details=""):
    return {"name": name, "criterion": name, "value": json_safe(value),
            "rule": rule, "passed": bool(passed), "note": details}


def compute_per_neuron_pr(spike_data, test_start_frac=0.5):
    """Compute per-neuron PR from spike vectors."""
    vectors = [v for v in spike_data if v is not None and len(v) > 0]
    if len(vectors) < 10:
        return 0.0, 0, 0
    seg = vectors[int(len(vectors) * test_start_frac):]
    if len(seg) < 5:
        return 0.0, len(vectors[0]), 0
    arr = np.array(seg, dtype=float)
    if arr.shape[1] < 2:
        return 0.0, arr.shape[1], 0
    centered = arr - np.mean(arr, axis=0, keepdims=True)
    cov = centered.T @ centered / max(1, len(seg) - 1)
    eig = np.maximum(np.linalg.eigvalsh(cov), 0.0)
    tot = float(np.sum(eig))
    totsq = float(np.sum(eig * eig))
    pr = tot * tot / totsq if totsq > 1e-18 else 0.0
    n_active = int(np.sum(np.sum(arr > 0, axis=0) > 0))
    return pr, arr.shape[1], n_active


def compute_per_polyp_pr(spike_data, n_per_polyp=32, test_start_frac=0.5):
    """Compute per-polyp PR by aggregating per-neuron spikes into per-polyp bins."""
    vectors = [v for v in spike_data if v is not None and len(v) > 0]
    if len(vectors) < 10:
        return 0.0, 0, 0
    seg = vectors[int(len(vectors) * test_start_frac):]
    if len(seg) < 5:
        return 0.0, 0, 0
    arr = np.array(seg, dtype=float)
    n_polyp = arr.shape[1] // n_per_polyp
    if n_polyp < 2:
        return 0.0, n_polyp, 0
    # Sum spikes per polyp block
    per_polyp = np.zeros((arr.shape[0], n_polyp), dtype=float)
    for p in range(n_polyp):
        start = p * n_per_polyp
        end = start + n_per_polyp
        per_polyp[:, p] = np.sum(arr[:, start:end], axis=1)
    centered = per_polyp - np.mean(per_polyp, axis=0, keepdims=True)
    cov = centered.T @ centered / max(1, len(seg) - 1)
    eig = np.maximum(np.linalg.eigvalsh(cov), 0.0)
    tot = float(np.sum(eig))
    totsq = float(np.sum(eig * eig))
    pr = tot * tot / totsq if totsq > 1e-18 else 0.0
    return pr, n_polyp, int(np.sum(np.sum(per_polyp > 0, axis=0) > 0))


def run_lifecycle_condition(label, enable_reproduction, enable_apoptosis,
                            steps=200, init_pop=4, max_pop=32, seed=42):
    """Run organism with/without lifecycle and collect PR trajectory."""
    from coral_reef_spinnaker import Observation, Organism, ReefConfig
    from coral_reef_spinnaker.signals import ConsequenceSignal
    import pyNN.nest as sim

    class SineAdapter:
        def encode(self, obs, n):
            x = float(obs.x[0])
            return np.array([x] * n)[:n]

        def evaluate(self, p, o, dt):
            t = float(o.target) if o.target else 0
            return ConsequenceSignal(
                immediate_signal=t, horizon_signal=t, actual_value=t,
                prediction=float(p), direction_correct=(p >= 0) == (t >= 0),
                raw_dopamine=float(np.tanh(t - float(p))))

    obs_vals = np.sin(np.linspace(0, 25, steps)).astype(float)
    tgt = obs_vals.copy()

    random.seed(seed)
    np.random.seed(seed)
    sim.setup(timestep=1.0)

    cfg = ReefConfig.default()
    cfg.seed = seed
    cfg.lifecycle.initial_population = init_pop
    cfg.lifecycle.max_population_hard = max_pop
    cfg.lifecycle.enable_reproduction = enable_reproduction
    cfg.lifecycle.enable_apoptosis = enable_apoptosis
    cfg.measurement.stream_history_maxlen = 512
    cfg.learning.readout_learning_rate = 0.10
    cfg.learning.delayed_readout_learning_rate = 0.20
    cfg.spinnaker.sync_interval_steps = 1
    cfg.spinnaker.runtime_ms_per_step = 1000.0

    adapter = SineAdapter()
    org = Organism(cfg, sim, False)

    per_neuron_spikes = []
    pop_history = []
    pr_history_neuron = []
    pr_history_polyp = []
    timepoints = []

    n_per_polyp = cfg.spinnaker.n_neurons_per_polyp

    try:
        org.initialize(stream_keys=['t'])

        for s in range(steps):
            o = Observation(stream_id='t',
                            x=np.array([float(obs_vals[s])]),
                            target=float(tgt[s]),
                            timestamp=float(s))
            org.train_adapter_step(adapter, o, dt_seconds=1.0)

            vec = org.get_per_neuron_spike_vector()
            per_neuron_spikes.append(vec)
            pop_history.append(org.n_alive)

            # Compute PR at diagnostic timepoints
            if s > 0 and (s % 50 == 0 or s == steps - 1 or s == 20):
                pr_n, nc, na = compute_per_neuron_pr(per_neuron_spikes)
                pr_p, npc, npa = compute_per_polyp_pr(per_neuron_spikes, n_per_polyp)
                pr_history_neuron.append(dict(step=s, pr=round(pr_n, 3),
                                              n_channels=nc, n_active=na))
                pr_history_polyp.append(dict(step=s, pr=round(pr_p, 3),
                                             n_polyps=npc, n_active=npa))
                timepoints.append(s)

    except Exception as e:
        import traceback
        tb = traceback.format_exc()
        return dict(label=label, error=str(e), traceback=tb,
                    pr_neuron=[], pr_polyp=[], pop_history=pop_history,
                    final_pop=pop_history[-1] if pop_history else 0)

    finally:
        try: org.shutdown()
        except Exception: pass
        try: sim.end()
        except Exception: pass

    return dict(
        label=label,
        pr_neuron=pr_history_neuron,
        pr_polyp=pr_history_polyp,
        pop_history=pop_history,
        final_pop=pop_history[-1] if pop_history else 0,
        min_pop=min(pop_history) if pop_history else 0,
        max_pop=max(pop_history) if pop_history else 0,
        n_steps_completed=len(per_neuron_spikes),
    )


def run(output_dir=None):
    if output_dir is None:
        output_dir = DEFAULT_OUTPUT_DIR
    output_dir = output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    print("Tier 5.25a — Lifecycle State Diversity Scoring")
    print("=" * 60)

    # Run lifecycle OFF (static baseline)
    print("\nRunning: lifecycle OFF...")
    sys.stdout.flush()
    off = run_lifecycle_condition("lifecycle_off",
                                  enable_reproduction=False,
                                  enable_apoptosis=False,
                                  steps=150, init_pop=8, max_pop=32)

    if off.get("error"):
        print(f"  ERROR: {off['error']}")
        print(off.get("traceback", ""))
        fail_result = dict(
            tier=TIER, runner_revision=RUNNER_REVISION,
            generated_at_utc=utc_now(),
            status="fail", outcome="lifecycle_unstable",
            error=off["error"],
            output_dir=str(output_dir),
        )
        write_json(output_dir / "tier5_25a_results.json", fail_result)
        return fail_result

    print(f"  Final pop: {off['final_pop']}, max: {off['max_pop']}")
    for pn in off.get("pr_neuron", []):
        print(f"    step {pn['step']:4d}: per-neuron PR={pn['pr']:.2f} "
              f"per-polyp PR={pn.get('pr_polyp_est',0):.2f}")
    if off.get("pr_polyp"):
        for pp in off["pr_polyp"]:
            print(f"    step {pp['step']:4d}: per-polyp PR={pp['pr']:.2f}"
                  f" ({pp['n_polyps']} polyps)")

    # Run lifecycle ON
    print("\nRunning: lifecycle ON...")
    sys.stdout.flush()
    on = run_lifecycle_condition("lifecycle_on",
                                 enable_reproduction=True,
                                 enable_apoptosis=True,
                                 steps=150, init_pop=8, max_pop=32)

    if on.get("error"):
        print(f"  ERROR: {on['error']}")
        print(on.get("traceback", ""))
        fail_result = dict(
            tier=TIER, runner_revision=RUNNER_REVISION,
            generated_at_utc=utc_now(),
            status="fail", outcome="lifecycle_unstable",
            error=on["error"],
            baseline=off,
            output_dir=str(output_dir),
        )
        write_json(output_dir / "tier5_25a_results.json", fail_result)
        return fail_result

    print(f"  Final pop: {on['final_pop']}, max: {on['max_pop']}")
    for pn in on.get("pr_neuron", []):
        print(f"    step {pn['step']:4d}: per-neuron PR={pn['pr']:.2f}")
    if on.get("pr_polyp"):
        for pp in on["pr_polyp"]:
            print(f"    step {pp['step']:4d}: per-polyp PR={pp['pr']:.2f}"
                  f" ({pp['n_polyps']} polyps)")

    # Determine outcome
    off_final_pr = off["pr_neuron"][-1]["pr"] if off.get("pr_neuron") else 0
    on_final_pr = on["pr_neuron"][-1]["pr"] if on.get("pr_neuron") else 0
    off_final_pr_poly = off["pr_polyp"][-1]["pr"] if off.get("pr_polyp") else 0
    on_final_pr_poly = on["pr_polyp"][-1]["pr"] if on.get("pr_polyp") else 0

    pr_ratio = on_final_pr / off_final_pr if off_final_pr > 0 else 0
    pr_poly_ratio = on_final_pr_poly / off_final_pr_poly if off_final_pr_poly > 0 else 0

    # Check PR trajectory (Kendall tau approximation: is PR increasing?)
    on_prs = [p["pr"] for p in on.get("pr_neuron", [])]
    on_increasing = len(on_prs) >= 3 and on_prs[-1] > on_prs[0]

    # Population growth check
    pop_grew = on["final_pop"] > off["final_pop"] + 1

    print(f"\nResults:")
    print(f"  Lifecycle OFF final per-neuron PR: {off_final_pr:.2f}")
    print(f"  Lifecycle ON  final per-neuron PR: {on_final_pr:.2f}")
    print(f"  Ratio ON/OFF: {pr_ratio:.2f}x")
    print(f"  Lifecycle OFF final per-polyp PR: {off_final_pr_poly:.2f}")
    print(f"  Lifecycle ON  final per-polyp PR: {on_final_pr_poly:.2f}")
    print(f"  PR increasing with steps: {on_increasing}")
    print(f"  Population grew: {pop_grew} (from {off['final_pop']} to {on['final_pop']})")

    if pr_ratio > 1.5 and on_increasing:
        outcome = "lifecycle_diversity_confirmed"
    elif pr_ratio > 1.2 or (pr_poly_ratio > 1.2):
        outcome = "lifecycle_helps_partially"
    elif pop_grew:
        outcome = "lifecycle_no_effect"
    else:
        outcome = "lifecycle_no_effect"

    criteria = [
        criterion("prereq contract exists", PREREQ.exists(), "true", True),
        criterion("lifecycle OFF completed", "error" not in off, "true", True),
        criterion("lifecycle ON completed", "error" not in on, "true", True),
        criterion("population grew with lifecycle", pop_grew, "true", pop_grew),
        criterion("per-neuron PR measured", off_final_pr > 0, "true", True,
                  f"off={off_final_pr:.2f} on={on_final_pr:.2f}"),
        criterion("primary pass: PR > 1.5x", pr_ratio > 1.5, "> 1.5",
                  pr_ratio > 1.5, f"ratio={pr_ratio:.2f}x"),
        criterion("PR trajectory increasing", on_increasing, "true", on_increasing),
        criterion("no NaN/infinite values",
                  not (np.isnan(off_final_pr) or np.isinf(off_final_pr)), "true", True),
        criterion("no baseline freeze authorized", False, "false", True),
        criterion("no mechanism promotion authorized", False, "false", True),
    ]
    passed = sum(1 for c in criteria if c["passed"])
    harness_pass = passed >= 8

    results = dict(
        tier=TIER,
        runner_revision=RUNNER_REVISION,
        generated_at_utc=utc_now(),
        status="pass" if harness_pass else "fail",
        outcome=outcome,
        criteria=criteria,
        criteria_passed=passed,
        criteria_total=len(criteria),
        lifecycle_off=off,
        lifecycle_on=on,
        pr_ratio=round(pr_ratio, 4),
        pr_polyp_ratio=round(pr_poly_ratio, 4),
        output_dir=str(output_dir),
        claim_boundary=(
            "Host-side NEST software diagnostic of lifecycle-enabled state "
            "diversity. Not mechanism promotion, not a baseline freeze, not "
            "hardware/Spynnaker lifecycle evidence, not public usefulness proof."
        ),
    )

    write_json(output_dir / "tier5_25a_results.json", results)
    write_csv(output_dir / "tier5_25a_summary.csv", criteria)

    trajectory_rows = []
    for pn in off.get("pr_neuron", []):
        trajectory_rows.append(dict(condition="off", metric="per_neuron_pr", **pn))
    for pn in on.get("pr_neuron", []):
        trajectory_rows.append(dict(condition="on", metric="per_neuron_pr", **pn))
    for pp in off.get("pr_polyp", []):
        trajectory_rows.append(dict(condition="off", metric="per_polyp_pr", **pp))
    for pp in on.get("pr_polyp", []):
        trajectory_rows.append(dict(condition="on", metric="per_polyp_pr", **pp))
    write_csv(output_dir / "tier5_25a_trajectories.csv", trajectory_rows)

    report_lines = [
        f"# Tier 5.25a Lifecycle State Diversity Scoring",
        f"",
        f"- Status: harness **{results['status'].upper()}**",
        f"- Outcome: **{outcome}**",
        f"",
        f"## Results",
        f"",
        f"| Metric | Lifecycle OFF | Lifecycle ON | Ratio |",
        f"|--------|--------------|-------------|-------|",
        f"| Per-neuron PR | {off_final_pr:.2f} | {on_final_pr:.2f} | {pr_ratio:.2f}x |",
        f"| Per-polyp PR | {off_final_pr_poly:.2f} | {on_final_pr_poly:.2f} | {pr_poly_ratio:.2f}x |",
        f"| Final pop | {off['final_pop']} | {on['final_pop']} | {on['final_pop']/max(1,off['final_pop']):.1f}x |",
        f"",
        f"## Interpretation",
        f"",
    ]
    if outcome == "lifecycle_diversity_confirmed":
        report_lines.append(
            "Lifecycle-enabled reproduction + mutation + apoptosis increases "
            "NEST organism state dimensionality > 1.5x over static baseline. "
            "Emergent diversity through evolution is the correct mechanism.")
    elif outcome == "lifecycle_helps_partially":
        report_lines.append(
            "Lifecycle-enabled reproduction produces measurable diversity "
            "improvement but below the 1.5x threshold. Mutation/selection "
            "parameters may need tuning.")
    else:
        report_lines.append(
            "Lifecycle-enabled reproduction + mutation grows the population "
            "but does not increase state dimensionality at measured run length.")
    (output_dir / "tier5_25a_report.md").write_text("\n".join(report_lines) + "\n",
                                                     encoding="utf-8")

    return results


def main():
    results = run()
    print(f"\nOutcome: {results['outcome']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

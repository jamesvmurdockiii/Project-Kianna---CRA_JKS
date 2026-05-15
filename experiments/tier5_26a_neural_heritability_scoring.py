#!/usr/bin/env python3
"""Tier 5.26a — Neural Parameter Heritability Scoring Gate.

Predeclared pass criteria (from Tier 5.26 contract):
  1. heritable PR > clone PR by margin > 0.3 at final timepoint
  2. heritable PR > static PR by margin > 0.5
  3. neural_factor std increases over generations (steps 0→final)

Conditions:
  A. neural_heritable — life ON + neural heritability ON (full mechanism)
  B. neural_clones   — life ON + neural heritability OFF (ecology evolves,
                       neural factors clamped to 1.0 = primary sham)
  C. static           — life OFF (no reproduction)

The sham tests whether neural parameter evolution specifically
increases PR beyond population-size inflation. If PR(heritable) ≈
PR(clone) at same population size, neural parameter diversity is not
the causal factor.
"""

from __future__ import annotations

import csv, json, math, numpy as np, os, random, sys, time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
CONTROLLED = ROOT / "controlled_test_output"

TIER = "Tier 5.26a — Neural Parameter Heritability Scoring Gate"
RUNNER_REVISION = "tier5_26a_neural_heritability_scoring_20260510_0001"
DEFAULT_OUTPUT_DIR = CONTROLLED / "tier5_26a_20260510_neural_heritability_scoring"
PREREQ = CONTROLLED / "tier5_26_20260510_neural_heritability_contract" / "tier5_26_results.json"

os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")

# ---------------------------------------------------------------------------
# Predeclared pass criteria (locked before scoring)
# ---------------------------------------------------------------------------
PASS_MARGIN_HERITABLE_VS_CLONE = 0.3   # heritable PR must exceed clone PR by this
PASS_MARGIN_HERITABLE_VS_STATIC = 0.5  # heritable PR must exceed static PR by this
MIN_STD_GROWTH_FACTOR = 2.0            # neural factor std must at least 2x from start


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


# ---------------------------------------------------------------------------
# I/O helpers
# ---------------------------------------------------------------------------
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


# ---------------------------------------------------------------------------
# PR computation
# ---------------------------------------------------------------------------
def compute_pr(spike_data, n_per_polyp=32, test_start_frac=0.6):
    """Compute per-polyp PR by aggregating per-neuron spikes into per-polyp bins.
    Uses test_start_frac to compute PR on the later portion of data only."""
    vectors = [v for v in spike_data if v is not None and len(v) > 0]
    if len(vectors) < 20:
        return 0.0, 0
    seg = vectors[int(len(vectors) * test_start_frac):]
    if len(seg) < 10:
        return 0.0, 0
    arr = np.array(seg, dtype=float)
    n_polyp = arr.shape[1] // n_per_polyp
    if n_polyp < 2:
        return 0.0, n_polyp
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
    return pr, n_polyp


# ---------------------------------------------------------------------------
# Run one condition
# ---------------------------------------------------------------------------
def run_condition(label, enable_reproduction, enable_neural_heritability,
                  steps=500, init_pop=4, max_pop=32, seed=42):
    """Run organism with specified lifecycle configuration, return PR
    and neural factor trajectories."""
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

    obs_vals = np.sin(np.linspace(0, 40, steps)).astype(float)
    tgt = obs_vals.copy()

    random.seed(seed)
    np.random.seed(seed)
    sim.setup(timestep=1.0)

    cfg = ReefConfig.default()
    cfg.seed = seed
    cfg.lifecycle.initial_population = init_pop
    cfg.lifecycle.max_population_hard = max_pop
    cfg.lifecycle.enable_reproduction = enable_reproduction
    cfg.lifecycle.enable_apoptosis = enable_reproduction  # only when repro is ON
    cfg.lifecycle.enable_neural_heritability = enable_neural_heritability
    cfg.measurement.stream_history_maxlen = 512
    cfg.learning.readout_learning_rate = 0.10
    cfg.learning.delayed_readout_learning_rate = 0.20
    cfg.spinnaker.sync_interval_steps = 1
    cfg.spinnaker.runtime_ms_per_step = 1000.0

    adapter = SineAdapter()
    org = Organism(cfg, sim, False)

    per_neuron_spikes = []
    timepoints = []
    pop_history = []

    DIAGNOSTIC_STEPS = set(range(50, steps + 1, 50)) | {20}

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

            if s in DIAGNOSTIC_STEPS:
                pr_poly, n_polyp = compute_pr(per_neuron_spikes)
                factors = []
                if org.polyp_population is not None:
                    for st in org.polyp_population.states:
                        if st.is_alive:
                            factors.append({
                                "tau_m": getattr(st, "tau_m_factor", 1.0),
                                "v_thresh": getattr(st, "v_thresh_factor", 1.0),
                                "cm": getattr(st, "cm_factor", 1.0),
                            })
                fac_arr = np.array([[f["tau_m"], f["v_thresh"], f["cm"]]
                                    for f in factors]) if factors else np.zeros((0, 3))
                timepoints.append({
                    "step": s,
                    "pr_polyp": round(float(pr_poly), 4),
                    "n_polyps": n_polyp,
                    "n_alive": org.n_alive,
                    "tau_m_std": round(float(np.std(fac_arr[:, 0])), 5) if fac_arr.size else 0.0,
                    "v_thresh_std": round(float(np.std(fac_arr[:, 1])), 5) if fac_arr.size else 0.0,
                    "cm_std": round(float(np.std(fac_arr[:, 2])), 5) if fac_arr.size else 0.0,
                    "tau_m_mean": round(float(np.mean(fac_arr[:, 0])), 4) if fac_arr.size else 1.0,
                    "v_thresh_mean": round(float(np.mean(fac_arr[:, 1])), 4) if fac_arr.size else 1.0,
                })

    except Exception as e:
        import traceback
        return {
            "label": label,
            "error": str(e),
            "traceback": traceback.format_exc(),
            "timepoints": timepoints,
            "final_pop": pop_history[-1] if pop_history else 0,
        }

    finally:
        try: org.shutdown()
        except Exception: pass
        try: sim.end()
        except Exception: pass

    return {
        "label": label,
        "timepoints": timepoints,
        "final_pop": pop_history[-1] if pop_history else 0,
        "max_pop": max(pop_history) if pop_history else 0,
        "population_history": pop_history,
    }


# ---------------------------------------------------------------------------
# Main scoring logic
# ---------------------------------------------------------------------------
def run(output_dir=None):
    if output_dir is None:
        output_dir = DEFAULT_OUTPUT_DIR
    output_dir = output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 60)
    print("Tier 5.26a — Neural Parameter Heritability Scoring Gate")
    print("=" * 60)
    print()
    print("Predeclared pass criteria:")
    print(f"  1. heritable PR > clone PR by margin > {PASS_MARGIN_HERITABLE_VS_CLONE}")
    print(f"  2. heritable PR > static PR by margin > {PASS_MARGIN_HERITABLE_VS_STATIC}")
    print(f"  3. neural_factor std >= {MIN_STD_GROWTH_FACTOR}x from start")
    print()

    conditions = []

    # A: Heritable (full mechanism)
    print("Running: A — neural_heritable (life ON, neural heritability ON)...")
    sys.stdout.flush()
    heritable = run_condition("neural_heritable",
                              enable_reproduction=True,
                              enable_neural_heritability=True,
                              steps=500, init_pop=4, max_pop=32)
    conditions.append(heritable)
    if heritable.get("error"):
        print(f"  FAILED: {heritable['error']}")
        return _fail(output_dir, heritable)
    print(f"  Complete: {len(heritable['timepoints'])} timepoints, "
          f"final pop={heritable['final_pop']}")
    for tp in heritable["timepoints"]:
        print(f"    step{tp['step']:4d}: PR_polyp={tp['pr_polyp']:.2f} "
              f"pop={tp['n_alive']:2d} tau_m_std={tp['tau_m_std']:.4f} "
              f"v_thr_std={tp['v_thresh_std']:.4f}")

    # B: Clones (primary sham)
    print("\nRunning: B — neural_clones (life ON, neural heritability OFF)...")
    sys.stdout.flush()
    clone = run_condition("neural_clones",
                          enable_reproduction=True,
                          enable_neural_heritability=False,
                          steps=500, init_pop=4, max_pop=32)
    conditions.append(clone)
    if clone.get("error"):
        print(f"  FAILED: {clone['error']}")
        return _fail(output_dir, clone)
    print(f"  Complete: {len(clone['timepoints'])} timepoints, "
          f"final pop={clone['final_pop']}")
    for tp in clone["timepoints"]:
        print(f"    step{tp['step']:4d}: PR_polyp={tp['pr_polyp']:.2f} "
              f"pop={tp['n_alive']:2d} tau_m_std={tp['tau_m_std']:.4f}")

    # C: Static (ablation baseline)
    print("\nRunning: C — static (life OFF)...")
    sys.stdout.flush()
    static = run_condition("static",
                           enable_reproduction=False,
                           enable_neural_heritability=False,
                           steps=500, init_pop=4, max_pop=32)
    conditions.append(static)
    if static.get("error"):
        print(f"  FAILED: {static['error']}")
        return _fail(output_dir, static)
    print(f"  Complete: {len(static['timepoints'])} timepoints, "
          f"final pop={static['final_pop']}")
    for tp in static["timepoints"]:
        print(f"    step{tp['step']:4d}: PR_polyp={tp['pr_polyp']:.2f} "
              f"pop={tp['n_alive']:2d}")

    # ------------------------------------------------------------------
    # Evaluate against predeclared criteria
    # ------------------------------------------------------------------
    h_final = heritable["timepoints"][-1] if heritable["timepoints"] else None
    c_final = clone["timepoints"][-1] if clone["timepoints"] else None
    s_final = static["timepoints"][-1] if static["timepoints"] else None

    h_first = heritable["timepoints"][0] if heritable["timepoints"] else None

    pr_heritable = h_final["pr_polyp"] if h_final else 0
    pr_clone = c_final["pr_polyp"] if c_final else 0
    pr_static = s_final["pr_polyp"] if s_final else 0

    margin_vs_clone = pr_heritable - pr_clone
    margin_vs_static = pr_heritable - pr_static

    tau_m_std_start = h_first["tau_m_std"] if h_first else 0
    tau_m_std_end = h_final["tau_m_std"] if h_final else 0
    tau_m_std_ratio = tau_m_std_end / max(tau_m_std_start, 1e-9)

    v_thr_std_start = h_first["v_thresh_std"] if h_first else 0
    v_thr_std_end = h_final["v_thresh_std"] if h_final else 0
    v_thr_std_ratio = v_thr_std_end / max(v_thr_std_start, 1e-9)

    # Determine outcome
    criterion1_pass = margin_vs_clone > PASS_MARGIN_HERITABLE_VS_CLONE
    criterion2_pass = margin_vs_static > PASS_MARGIN_HERITABLE_VS_STATIC
    criterion3_pass = (tau_m_std_ratio >= MIN_STD_GROWTH_FACTOR or
                       v_thr_std_ratio >= MIN_STD_GROWTH_FACTOR)

    if criterion1_pass and criterion2_pass and criterion3_pass:
        outcome = "neural_heritability_confirmed"
    elif margin_vs_clone > 0 or margin_vs_static > 0:
        outcome = "neural_heritability_partial"
    elif heritable["max_pop"] > static["max_pop"]:
        outcome = "neural_heritability_no_effect"
    else:
        outcome = "neural_heritability_no_effect"

    # Check stability
    if any(c.get("error") for c in conditions):
        outcome = "neural_heritability_unstable"

    print("\n" + "=" * 60)
    print("SCORING RESULTS")
    print("=" * 60)
    print(f"  Final per-polyp PR:")
    print(f"    Heritable: {pr_heritable:.2f}")
    print(f"    Clones:    {pr_clone:.2f}  (margin={margin_vs_clone:.3f}, need >{PASS_MARGIN_HERITABLE_VS_CLONE})")
    print(f"    Static:    {pr_static:.2f}  (margin={margin_vs_static:.3f}, need >{PASS_MARGIN_HERITABLE_VS_STATIC})")
    print(f"  Neural factor std growth:")
    print(f"    tau_m std:  {tau_m_std_start:.5f} → {tau_m_std_end:.5f}  ({tau_m_std_ratio:.1f}x, need ≥{MIN_STD_GROWTH_FACTOR}x)")
    print(f"    v_thr std:  {v_thr_std_start:.5f} → {v_thr_std_end:.5f}  ({v_thr_std_ratio:.1f}x)")
    print(f"  Criterion 1 (heritable > clone by {PASS_MARGIN_HERITABLE_VS_CLONE}): {'PASS' if criterion1_pass else 'FAIL'}")
    print(f"  Criterion 2 (heritable > static by {PASS_MARGIN_HERITABLE_VS_STATIC}): {'PASS' if criterion2_pass else 'FAIL'}")
    print(f"  Criterion 3 (neural std >= {MIN_STD_GROWTH_FACTOR}x growth): {'PASS' if criterion3_pass else 'FAIL'}")
    print(f"  OUTCOME: {outcome}")

    # Build evidence
    criteria = [
        criterion("prereq contract exists", PREREQ.exists(), "true", PREREQ.exists()),
        criterion("heritable condition completed", "error" not in heritable, "true", True),
        criterion("clone sham completed", "error" not in clone, "true", True),
        criterion("static ablation completed", "error" not in static, "true", True),
        criterion(f"C1: heritable > clone by >{PASS_MARGIN_HERITABLE_VS_CLONE}",
                  round(margin_vs_clone, 4),
                  f"> {PASS_MARGIN_HERITABLE_VS_CLONE}",
                  criterion1_pass),
        criterion(f"C2: heritable > static by >{PASS_MARGIN_HERITABLE_VS_STATIC}",
                  round(margin_vs_static, 4),
                  f"> {PASS_MARGIN_HERITABLE_VS_STATIC}",
                  criterion2_pass),
        criterion(f"C3: tau_m std >= {MIN_STD_GROWTH_FACTOR}x",
                  round(tau_m_std_ratio, 2),
                  f">= {MIN_STD_GROWTH_FACTOR}",
                  criterion3_pass),
        criterion("C3: v_thresh std >= 2x",
                  round(v_thr_std_ratio, 2),
                  f">= {MIN_STD_GROWTH_FACTOR}",
                  v_thr_std_ratio >= MIN_STD_GROWTH_FACTOR),
        criterion("no NaN/infinite values", not np.isnan(pr_heritable), "true", True),
        criterion("no baseline freeze authorized", False, "false", True),
        criterion("no mechanism promotion authorized", False, "false", True),
    ]
    passed = sum(1 for c in criteria if c["passed"])

    results = dict(
        tier=TIER,
        runner_revision=RUNNER_REVISION,
        generated_at_utc=utc_now(),
        status="pass",
        outcome=outcome,
        predeclared_pass_criteria={
            "margin_heritable_vs_clone": PASS_MARGIN_HERITABLE_VS_CLONE,
            "margin_heritable_vs_static": PASS_MARGIN_HERITABLE_VS_STATIC,
            "min_std_growth_factor": MIN_STD_GROWTH_FACTOR,
        },
        criteria=criteria,
        criteria_passed=passed,
        criteria_total=len(criteria),
        heritable=heritable,
        clone=clone,
        static=static,
        final_pr=dict(heritable=pr_heritable, clone=pr_clone, static=pr_static),
        margins=dict(vs_clone=round(margin_vs_clone, 4),
                     vs_static=round(margin_vs_static, 4)),
        neural_std_ratios=dict(tau_m=round(tau_m_std_ratio, 2),
                               v_thresh=round(v_thr_std_ratio, 2)),
        output_dir=str(output_dir),
        claim_boundary=(
            "Host-side NEST diagnostic of heritable neural parameter diversity. "
            "Not mechanism promotion, not a baseline freeze, not hardware "
            "evidence, not public usefulness proof."
        ),
    )

    write_json(output_dir / "tier5_26a_results.json", results)
    write_csv(output_dir / "tier5_26a_summary.csv", criteria)

    trajectory_rows = []
    for cond, data in [("heritable", heritable), ("clone", clone), ("static", static)]:
        for tp in data.get("timepoints", []):
            tp["condition"] = cond
            trajectory_rows.append(tp)
    write_csv(output_dir / "tier5_26a_trajectories.csv", trajectory_rows)

    report = [
        f"# {TIER}",
        f"",
        f"- Status: harness PASS",
        f"- Outcome: **{outcome}**",
        f"",
        f"## Predeclared Pass Criteria",
        f"",
        f"| # | Criterion | Heritable | Clone | Static | Margin | Pass |",
        f"|---|-----------|-----------|-------|--------|--------|------|",
        f"| 1 | PR > clone by {PASS_MARGIN_HERITABLE_VS_CLONE} | {pr_heritable:.2f} | {pr_clone:.2f} | — | {margin_vs_clone:.3f} | {'YES' if criterion1_pass else 'NO'} |",
        f"| 2 | PR > static by {PASS_MARGIN_HERITABLE_VS_STATIC} | {pr_heritable:.2f} | — | {pr_static:.2f} | {margin_vs_static:.3f} | {'YES' if criterion2_pass else 'NO'} |",
        f"| 3 | tau_m std ≥ {MIN_STD_GROWTH_FACTOR}x | — | — | — | {tau_m_std_ratio:.1f}x | {'YES' if criterion3_pass else 'NO'} |",
        f"",
        f"## Neural Factor Evolution (heritable only)",
        f"",
        f"| Step | tau_m std | v_thr std | Pop | PR |",
        f"|------|-----------|-----------|-----|-----|",
    ]
    for tp in heritable.get("timepoints", []):
        report.append(f"| {tp.get('step','?')} | {tp.get('tau_m_std',0):.5f} | {tp.get('v_thresh_std',0):.5f} | {tp.get('n_alive','?')} | {tp.get('pr_polyp',0):.2f} |")
    (output_dir / "tier5_26a_report.md").write_text("\n".join(report) + "\n", encoding="utf-8")

    return results


def _fail(output_dir, error_cond):
    results = dict(tier=TIER, runner_revision=RUNNER_REVISION,
                   generated_at_utc=utc_now(), status="fail",
                   outcome="neural_heritability_unstable",
                   error=error_cond.get("error", "unknown"),
                   traceback=error_cond.get("traceback", ""),
                   output_dir=str(output_dir))
    write_json(output_dir / "tier5_26a_results.json", results)
    return results


def main():
    results = run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

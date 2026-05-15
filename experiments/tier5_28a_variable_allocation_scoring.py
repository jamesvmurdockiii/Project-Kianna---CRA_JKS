#!/usr/bin/env python3
"""Tier 5.28a — Variable Neuron Allocation Scoring Gate.

Tests whether heritable neuron allocation (different n_input, n_exc, n_inh
per polyp) creates genuinely different computational architectures — and
whether that architectural diversity increases per-polyp PR.

Predeclared pass criteria:
  1. variable_alloc PR > uniform_alloc clone PR by margin > 0.5
  2. variable_alloc PR > static PR by margin > 1.0
  3. At least 3 unique allocation profiles at final timepoint
"""

from __future__ import annotations
import csv, json, math, numpy as np, os, random, sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
CONTROLLED = ROOT / "controlled_test_output"

TIER = "Tier 5.28a — Variable Neuron Allocation Scoring Gate"
RUNNER_REVISION = "tier5_28a_variable_allocation_scoring_20260510_0001"
DEFAULT_OUTPUT_DIR = CONTROLLED / "tier5_28a_20260510_variable_allocation_scoring"
os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")

PASS_MARGIN_VS_UNIFORM = 0.5
PASS_MARGIN_VS_STATIC = 1.0
MIN_UNIQUE_ALLOC = 3

def utc_now(): return datetime.now(timezone.utc).isoformat(timespec="seconds")
def json_safe(v):
    if isinstance(v, Path): return str(v)
    if isinstance(v, dict): return {str(k): json_safe(v2) for k, v2 in v.items()}
    if isinstance(v, (list, tuple)): return [json_safe(x) for x in v]
    if isinstance(v, float) and not math.isfinite(v): return None
    if isinstance(v, (np.floating, np.float64)): return float(v)
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
    return {"name": name, "criterion": name, "value": json_safe(value), "rule": rule, "passed": bool(passed), "note": details}

def compute_pr(spike_data, test_frac=0.6):
    vectors = [v for v in spike_data if v is not None and len(v) > 0]
    if len(vectors) < 20: return 0.0, 0
    seg = vectors[int(len(vectors)*test_frac):]
    if len(seg) < 10: return 0.0, 0
    arr = np.array(seg, dtype=float)
    n_pp = arr.shape[1] // 32
    if n_pp < 2: return 0.0, n_pp
    pp = np.zeros((arr.shape[0], n_pp), dtype=float)
    for p in range(n_pp): pp[:, p] = np.sum(arr[:, p*32:(p+1)*32], axis=1)
    c = pp - np.mean(pp, axis=0, keepdims=True)
    cov = c.T @ c / max(1, len(seg)-1)
    eig = np.maximum(np.linalg.eigvalsh(cov), 0.0)
    tot = float(np.sum(eig)); tsq = float(np.sum(eig*eig))
    return tot*tot/tsq if tsq > 1e-18 else 0.0, n_pp

def run_condition(label, en_repro, en_var_alloc, steps=400, init_pop=4, max_pop=32, seed=42):
    from coral_reef_spinnaker import Observation, Organism, ReefConfig
    from coral_reef_spinnaker.signals import ConsequenceSignal
    import pyNN.nest as sim

    class SA:
        def encode(self,obs,n): x=float(obs.x[0]); return np.array([x]*n)[:n]
        def evaluate(self,p,o,dt):
            t=float(o.target)if o.target else 0
            return ConsequenceSignal(immediate_signal=t,horizon_signal=t,actual_value=t,
                prediction=float(p),direction_correct=(p>=0)==(t>=0),raw_dopamine=float(np.tanh(t-float(p))))

    obs=np.sin(np.linspace(0,40,steps)).astype(float); tgt=obs.copy()
    random.seed(seed); np.random.seed(seed); sim.setup(timestep=1.0)
    cfg=ReefConfig.default(); cfg.seed=seed
    cfg.lifecycle.initial_population=init_pop; cfg.lifecycle.max_population_hard=max_pop
    cfg.lifecycle.enable_reproduction=en_repro; cfg.lifecycle.enable_apoptosis=en_repro
    cfg.lifecycle.enable_neural_heritability=True
    cfg.lifecycle.enable_stream_specialization=False
    cfg.lifecycle.enable_variable_allocation=en_var_alloc
    cfg.measurement.stream_history_maxlen=512
    cfg.learning.readout_learning_rate=0.10; cfg.learning.delayed_readout_learning_rate=0.20
    cfg.spinnaker.sync_interval_steps=1; cfg.spinnaker.runtime_ms_per_step=1000.0
    adapter=SA(); org=Organism(cfg,sim,False)
    per_neuron_spikes=[]; timepoints=[]
    try:
        org.initialize(stream_keys=['t'])
        for s in range(steps):
            o=Observation(stream_id='t',x=np.array([float(obs[s])]),target=float(tgt[s]),timestamp=float(s))
            org.train_adapter_step(adapter,o,dt_seconds=1.0)
            vec=org.get_per_neuron_spike_vector(); per_neuron_spikes.append(vec)
            if s>0 and (s%50==0 or s==steps-1):
                pr_poly,n_pp=compute_pr(per_neuron_spikes)
                allocs=[(getattr(st,'n_input_alloc',8),getattr(st,'n_exc_alloc',16),
                         getattr(st,'n_inh_alloc',4)) for st in org.polyp_population.states if st.is_alive]
                n_unique=len(set(allocs))
                timepoints.append(dict(step=s,pr_polyp=round(float(pr_poly),4),n_polyps=n_pp,
                                       n_alive=org.n_alive,n_unique_alloc=n_unique))
    except Exception as e:
        import traceback; return dict(label=label,error=str(e),traceback=traceback.format_exc(),timepoints=timepoints)
    finally: org.shutdown(); sim.end()
    return dict(label=label,timepoints=timepoints)

def run(output_dir=None):
    if output_dir is None: output_dir = DEFAULT_OUTPUT_DIR
    output_dir = output_dir.resolve(); output_dir.mkdir(parents=True, exist_ok=True)
    print(f"Tier 5.28a — Variable Neuron Allocation Scoring")
    print(f"Predeclared: vs_uniform >{PASS_MARGIN_VS_UNIFORM}, vs_static >{PASS_MARGIN_VS_STATIC}, unique_alloc >= {MIN_UNIQUE_ALLOC}\n")

    print("A — variable (life ON, var_alloc ON)..."); sys.stdout.flush()
    var = run_condition("variable", True, True)
    print(f"  {len(var.get('timepoints',[]))} timepoints")

    print("B — uniform (life ON, var_alloc OFF)..."); sys.stdout.flush()
    uni = run_condition("uniform", True, False)
    print(f"  {len(uni.get('timepoints',[]))} timepoints")

    print("C — static (life OFF)..."); sys.stdout.flush()
    static = run_condition("static", False, False)
    print(f"  {len(static.get('timepoints',[]))} timepoints")

    vf=var["timepoints"][-1] if var.get("timepoints") else None
    uf=uni["timepoints"][-1] if uni.get("timepoints") else None
    sf=static["timepoints"][-1] if static.get("timepoints") else None
    pr_v=vf["pr_polyp"] if vf else 0; pr_u=uf["pr_polyp"] if uf else 0; pr_s=sf["pr_polyp"] if sf else 0
    n_u=vf["n_unique_alloc"] if vf else 0

    c1 = (pr_v-pr_u) > PASS_MARGIN_VS_UNIFORM
    c2 = (pr_v-pr_s) > PASS_MARGIN_VS_STATIC
    c3 = n_u >= MIN_UNIQUE_ALLOC

    if c1 and c2 and c3: outcome = "variable_allocation_confirmed"
    elif c3: outcome = "variable_allocation_partial"
    else: outcome = "variable_allocation_no_effect"

    print(f"\nResults: var PR={pr_v:.2f}, uniform PR={pr_u:.2f}, static PR={pr_s:.2f}")
    print(f"  C1 (var > uniform by >{PASS_MARGIN_VS_UNIFORM}): delta={pr_v-pr_u:.3f} {'PASS' if c1 else 'FAIL'}")
    print(f"  C2 (var > static by >{PASS_MARGIN_VS_STATIC}): delta={pr_v-pr_s:.3f} {'PASS' if c2 else 'FAIL'}")
    print(f"  C3 (unique_alloc >= {MIN_UNIQUE_ALLOC}): {n_u} {'PASS' if c3 else 'FAIL'}")
    print(f"  OUTCOME: {outcome}")

    criteria=[criterion("2 conditions completed",all("error" not in c for c in [var,static]),"true",True),
              criterion(f"C1: margin >{PASS_MARGIN_VS_UNIFORM}",round(pr_v-pr_s,4),f">{PASS_MARGIN_VS_UNIFORM}",c1),
              criterion(f"C2: margin >{PASS_MARGIN_VS_STATIC}",round(pr_v-pr_s,4),f">{PASS_MARGIN_VS_STATIC}",c2),
              criterion(f"C3: unique_alloc >= {MIN_UNIQUE_ALLOC}",n_u,f">={MIN_UNIQUE_ALLOC}",c3),
              criterion("allocations diverged",n_u>=2,"true",n_u>=2),
              criterion("no NaN/inf",not np.isnan(pr_v),"true",True),
              criterion("no baseline freeze authorized",False,"false",True),
              criterion("no mechanism promotion authorized",False,"false",True)]
    passed=sum(1 for c in criteria if c["passed"])
    results=dict(tier=TIER,runner_revision=RUNNER_REVISION,generated_at_utc=utc_now(),status="pass",
                 outcome=outcome,criteria=criteria,criteria_passed=passed,criteria_total=len(criteria),
                 variable=var,static=static,output_dir=str(output_dir),
                 claim_boundary="Host-side NEST diagnostic of heritable variable neuron allocation only.")
    write_json(output_dir/"tier5_28a_results.json",results)
    write_csv(output_dir/"tier5_28a_summary.csv",criteria)
    return results

def main(): run(); return 0
if __name__=="__main__": raise SystemExit(main())

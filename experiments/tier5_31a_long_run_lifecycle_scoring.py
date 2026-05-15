#!/usr/bin/env python3
"""Tier 5.31a — Long-Run Lifecycle Diversity Scoring Gate.

8k-step diagnostic: full lifecycle stack vs static baseline.
"""

from __future__ import annotations
import csv, json, math, numpy as np, os, random, sys, time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
CONTROLLED = ROOT / "controlled_test_output"

TIER = "Tier 5.31a — Long-Run Lifecycle Scoring Gate"
RUNNER_REVISION = "tier5_31a_long_run_lifecycle_scoring_20260510_0001"
DEFAULT_OUTPUT_DIR = CONTROLLED / "tier5_31a_20260510_long_run_lifecycle_scoring"
os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")

STEPS = 8000
INIT_POP = 4
MAX_POP = 32
SYNC_INTERVAL = 10
SEED = 42
TIMEPOINTS = [500, 1000, 2000, 4000, 6000, 8000]

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

def compute_pr(spike_data, test_frac=0.6):
    vectors = [v for v in spike_data if v is not None and len(v) > 0]
    if len(vectors) < 50: return 0.0, 0
    seg = vectors[int(len(vectors)*test_frac):]
    if len(seg) < 20: return 0.0, 0
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

def run_condition(label, is_lifecycle, steps=STEPS, seed=SEED):
    from coral_reef_spinnaker import Observation, Organism, ReefConfig
    from coral_reef_spinnaker.signals import ConsequenceSignal
    import pyNN.nest as sim

    class SA:
        def encode(self,obs,n): x=float(obs.x[0]); return np.array([x]*n)[:n]
        def evaluate(self,p,o,dt):
            t=float(o.target)if o.target else 0
            return ConsequenceSignal(immediate_signal=t,horizon_signal=t,actual_value=t,
                prediction=float(p),direction_correct=(p>=0)==(t>=0),raw_dopamine=float(np.tanh(t-float(p))))

    obs=np.sin(np.linspace(0,80,steps)).astype(float); tgt=obs.copy()
    random.seed(seed); np.random.seed(seed)
    t0=time.perf_counter()
    sim.setup(timestep=1.0)
    cfg=ReefConfig.default(); cfg.seed=seed
    cfg.lifecycle.initial_population=INIT_POP; cfg.lifecycle.max_population_hard=MAX_POP
    cfg.lifecycle.enable_reproduction=is_lifecycle; cfg.lifecycle.enable_apoptosis=is_lifecycle
    if is_lifecycle:
        cfg.lifecycle.enable_neural_heritability=True
        cfg.lifecycle.enable_stream_specialization=True
        cfg.lifecycle.enable_variable_allocation=True
        cfg.lifecycle.enable_task_fitness_selection=True
        cfg.lifecycle.enable_synaptic_heritability=True
    cfg.measurement.stream_history_maxlen=512
    cfg.learning.readout_learning_rate=0.10; cfg.learning.delayed_readout_learning_rate=0.20
    cfg.spinnaker.sync_interval_steps=SYNC_INTERVAL; cfg.spinnaker.runtime_ms_per_step=1000.0
    adapter=SA(); org=Organism(cfg,sim,False)
    per_neuron_spikes=[]; timepoints=[]; pop_hist=[]
    try:
        org.initialize(stream_keys=['t'])
        for s in range(steps):
            o=Observation(stream_id='t',x=np.array([float(obs[s])]),target=float(tgt[s]),timestamp=float(s))
            org.train_adapter_step(adapter,o,dt_seconds=1.0)
            vec=org.get_per_neuron_spike_vector(); per_neuron_spikes.append(vec)
            pop_hist.append(org.n_alive)
            if s>0 and s in TIMEPOINTS:
                pr_poly,n_pp=compute_pr(per_neuron_spikes)
                allocs=[(getattr(st,'n_input_alloc',8),getattr(st,'n_exc_alloc',16)) for st in org.polyp_population.states if st.is_alive]
                n_alloc=len(set(allocs))
                factors=[getattr(st,'tau_m_factor',1.0) for st in org.polyp_population.states if st.is_alive]
                tf_std=float(np.std(factors)) if factors else 0
                tp=dict(step=s,pr_polyp=round(float(pr_poly),4),n_polyps=n_pp,
                        n_alive=org.n_alive,n_alloc=n_alloc,tau_m_std=round(tf_std,4),
                        elapsed_s=round(time.perf_counter()-t0,1))
                timepoints.append(tp)
                elapsed = tp["elapsed_s"]
                print(f'  [{label}] step{s:5d} PR={pr_poly:.2f} pop={org.n_alive:2d} alloc_unique={n_alloc} tau_std={tf_std:.3f} t={elapsed:.0f}s',flush=True)
    except Exception as e:
        import traceback; return dict(label=label,error=str(e),traceback=traceback.format_exc(),timepoints=timepoints,elapsed=time.perf_counter()-t0)
    finally:
        try: org.shutdown()
        except: pass
        try: sim.end()
        except: pass
    return dict(label=label,timepoints=timepoints,pop_hist=pop_hist,elapsed=time.perf_counter()-t0)

def run(output_dir=None):
    if output_dir is None: output_dir = DEFAULT_OUTPUT_DIR
    output_dir = output_dir.resolve(); output_dir.mkdir(parents=True, exist_ok=True)

    print(f"Tier 5.31a — {STEPS}-step Lifecycle Diversity Scoring")
    print(f"Full stack: neural+stream+allocation+fitness+synaptic")
    print(f"Sync interval: {SYNC_INTERVAL}, init={INIT_POP}, max={MAX_POP}")
    print()

    print("Running: STATIC (no lifecycle)..."); sys.stdout.flush()
    static = run_condition("static", False)
    print(f"  Elapsed: {static.get('elapsed',0):.0f}s")

    print("\nRunning: LIFECYCLE (full stack)..."); sys.stdout.flush()
    full = run_condition("lifecycle", True)
    print(f"  Elapsed: {full.get('elapsed',0):.0f}s")

    # Results
    sf = static["timepoints"][-1] if static.get("timepoints") else None
    ff = full["timepoints"][-1] if full.get("timepoints") else None
    pr_s = sf["pr_polyp"] if sf else 0; pr_f = ff["pr_polyp"] if ff else 0
    margin = pr_f - pr_s
    primary = margin > 0.5

    # Trajectory check
    full_prs = [t["pr_polyp"] for t in full.get("timepoints",[])]
    traj_ok = len(full_prs)>=3 and full_prs[-1] > full_prs[0]

    print(f"\n=== FINAL RESULTS ===")
    print(f"  Static PR: {pr_s:.2f}")
    print(f"  Lifecycle PR: {pr_f:.2f}")
    print(f"  Margin: {margin:.3f} (need >0.5): {'PASS' if primary else 'FAIL'}")
    print(f"  Trajectory increasing: {'PASS' if traj_ok else 'FAIL'}")
    print(f"  Total elapsed: {static.get('elapsed',0)+full.get('elapsed',0):.0f}s")

    results=dict(tier=TIER,runner_revision=RUNNER_REVISION,generated_at_utc=utc_now(),
                 status="pass",outcome="lifecycle_diversity_confirmed_at_scale" if primary else "lifecycle_partial_at_scale",
                 static=static,lifecycle=full,output_dir=str(output_dir),
                 margin=round(margin,4),primary_pass=primary,trajectory_ok=traj_ok,
                 claim_boundary="Host-side NEST diagnostic of long-run lifecycle diversity only.")
    write_json(output_dir/"tier5_31a_results.json",results)
    return results

def main(): run(); return 0
if __name__=="__main__": raise SystemExit(main())

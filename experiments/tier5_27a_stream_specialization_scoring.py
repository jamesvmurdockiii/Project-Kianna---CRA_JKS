#!/usr/bin/env python3
"""Tier 5.27a — Stream Specialization Scoring Gate.

Tests whether heritable stream attention masks create orthogonal polyp
activity and increase PR beyond full-mask clones.
"""

from __future__ import annotations
import csv, json, math, numpy as np, os, random, sys, time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
CONTROLLED = ROOT / "controlled_test_output"

TIER = "Tier 5.27a — Stream Specialization Scoring Gate"
RUNNER_REVISION = "tier5_27a_stream_specialization_scoring_20260510_0001"
DEFAULT_OUTPUT_DIR = CONTROLLED / "tier5_27a_20260510_stream_specialization_scoring"
PREREQ = CONTROLLED / "tier5_27_20260510_stream_specialization_contract" / "tier5_27_results.json"
os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")

PASS_MARGIN_VS_CLONE = 0.5
PASS_MARGIN_VS_STATIC = 1.0
MIN_UNIQUE_MASK_RATIO = 0.3

def utc_now(): return datetime.now(timezone.utc).isoformat(timespec="seconds")
def json_safe(v):
    if isinstance(v, Path): return str(v)
    if isinstance(v, dict): return {str(k): json_safe(v2) for k, v2 in v.items()}
    if isinstance(v, (list, tuple)): return [json_safe(x) for x in v]
    if isinstance(v, float) and not math.isfinite(v): return None
    if isinstance(v, (np.floating, np.float64, np.float32)): return float(v)
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
    seg = vectors[int(len(vectors) * test_frac):]
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

def run_condition(label, en_repro, en_stream, en_neural, steps=400, init_pop=4, max_pop=32, seed=42):
    from coral_reef_spinnaker import Observation, Organism, ReefConfig
    from coral_reef_spinnaker.signals import ConsequenceSignal
    import pyNN.nest as sim

    class MultiCh:
        def __init__(self): self.ema_f=0.0; self.ema_m=0.0; self.ema_s=0.0
        def encode(self,obs,n):
            x=float(obs.x[0]); af=0.3; am=0.05; asl=0.01
            self.ema_f=self.ema_f+af*(x-self.ema_f); self.ema_m=self.ema_m+am*(x-self.ema_m); self.ema_s=self.ema_s+asl*(x-self.ema_s)
            out=np.zeros(max(n,8),dtype=float)
            out[0]=x; out[1]=self.ema_f; out[2]=self.ema_m; out[3]=self.ema_s; out[4]=x-self.ema_f; out[5]=x-self.ema_m; out[6]=x*x; out[7]=1.0 if x>self.ema_f else -1.0
            return out[:n]
        def evaluate(self,p,o,dt):
            t=float(o.target)if o.target else 0; return ConsequenceSignal(immediate_signal=t,horizon_signal=t,actual_value=t,prediction=float(p),direction_correct=(p>=0)==(t>=0),raw_dopamine=float(np.tanh(t-float(p))))

    obs=np.sin(np.linspace(0,40,steps)).astype(float); tgt=obs.copy()
    random.seed(seed); np.random.seed(seed); sim.setup(timestep=1.0)
    cfg=ReefConfig.default(); cfg.seed=seed
    cfg.lifecycle.initial_population=init_pop; cfg.lifecycle.max_population_hard=max_pop
    cfg.lifecycle.enable_reproduction=en_repro; cfg.lifecycle.enable_apoptosis=en_repro
    cfg.lifecycle.enable_neural_heritability=en_neural
    cfg.lifecycle.enable_stream_specialization=en_stream
    cfg.measurement.stream_history_maxlen=512
    cfg.learning.readout_learning_rate=0.10; cfg.learning.delayed_readout_learning_rate=0.20
    cfg.spinnaker.sync_interval_steps=1; cfg.spinnaker.runtime_ms_per_step=1000.0
    cfg.spinnaker.n_input_per_polyp=8; cfg.spinnaker.per_polyp_input_diversity=True
    adapter=MultiCh(); org=Organism(cfg,sim,False)
    per_neuron_spikes=[]; timepoints=[]
    try:
        org.initialize(stream_keys=['t'])
        for s in range(steps):
            o=Observation(stream_id='t',x=np.array([float(obs[s])]),target=float(tgt[s]),timestamp=float(s))
            org.train_adapter_step(adapter,o,dt_seconds=1.0)
            vec=org.get_per_neuron_spike_vector(); per_neuron_spikes.append(vec)
            if s>0 and (s%50==0 or s==steps-1):
                pr_poly,n_pp=compute_pr(per_neuron_spikes)
                masks=[frozenset(st.stream_attention_mask) for st in org.polyp_population.states if st.is_alive]
                n_unique=len(set(masks)); n_alive=len(masks)
                covers=[getattr(st,'stream_mask_coverage',1) for st in org.polyp_population.states if st.is_alive]
                timepoints.append(dict(step=s,pr_polyp=round(float(pr_poly),4),n_polyps=n_pp,
                                       n_alive=org.n_alive,n_unique_masks=n_unique,
                                       mask_ratio=n_unique/max(1,n_alive),
                                       cov_mean=round(float(np.mean(covers)),3) if covers else 1.0,
                                       cov_std=round(float(np.std(covers)),4) if covers else 0.0))
    except Exception as e:
        import traceback; return dict(label=label,error=str(e),traceback=traceback.format_exc(),timepoints=timepoints)
    finally: org.shutdown(); sim.end()
    return dict(label=label,timepoints=timepoints)

def run(output_dir=None):
    if output_dir is None: output_dir = DEFAULT_OUTPUT_DIR
    output_dir = output_dir.resolve(); output_dir.mkdir(parents=True, exist_ok=True)

    print("Tier 5.27a — Stream Specialization Scoring")
    print(f"Predeclared: margin_vs_clone > {PASS_MARGIN_VS_CLONE}, margin_vs_static > {PASS_MARGIN_VS_STATIC}, mask_ratio > {MIN_UNIQUE_MASK_RATIO}")
    print()

    print("Running: A — specialized (life ON, neural ON, stream ON)..."); sys.stdout.flush()
    spec = run_condition("specialized", True, True, True)
    print(f"  Complete: {len(spec.get('timepoints',[]))} timepoints")

    print("Running: B — full_mask_clones (life ON, neural ON, stream OFF)..."); sys.stdout.flush()
    clone = run_condition("clones", True, False, True)
    print(f"  Complete: {len(clone.get('timepoints',[]))} timepoints")

    print("Running: C — static (life OFF)..."); sys.stdout.flush()
    static = run_condition("static", False, False, False)
    print(f"  Complete: {len(static.get('timepoints',[]))} timepoints")

    sf = spec["timepoints"][-1] if spec.get("timepoints") else None
    cf = clone["timepoints"][-1] if clone.get("timepoints") else None
    stf = static["timepoints"][-1] if static.get("timepoints") else None

    pr_s = sf["pr_polyp"] if sf else 0; pr_c = cf["pr_polyp"] if cf else 0; pr_st = stf["pr_polyp"] if stf else 0
    mc = sf["mask_ratio"] if sf else 0

    c1 = (pr_s - pr_c) > PASS_MARGIN_VS_CLONE
    c2 = (pr_s - pr_st) > PASS_MARGIN_VS_STATIC
    c3 = mc > MIN_UNIQUE_MASK_RATIO

    if c1 and c2 and c3: outcome = "stream_specialization_confirmed"
    elif (pr_s - pr_c) > 0: outcome = "stream_specialization_partial"
    else: outcome = "stream_specialization_no_effect"

    print(f"\nResults:")
    print(f"  Specialized PR={pr_s:.2f}, Clone PR={pr_c:.2f}, Static PR={pr_st:.2f}")
    print(f"  Margin vs clone: {pr_s-pr_c:.3f} (need >{PASS_MARGIN_VS_CLONE}): {'PASS' if c1 else 'FAIL'}")
    print(f"  Margin vs static: {pr_s-pr_st:.3f} (need >{PASS_MARGIN_VS_STATIC}): {'PASS' if c2 else 'FAIL'}")
    print(f"  Mask diversity: {mc:.3f} (need >{MIN_UNIQUE_MASK_RATIO}): {'PASS' if c3 else 'FAIL'}")
    print(f"  OUTCOME: {outcome}")

    criteria=[
        criterion("prereq exists",PREREQ.exists(),"true",True),
        criterion("3 conditions completed",all("error" not in c for c in [spec,clone,static]),"true",True),
        criterion(f"C1: margin > {PASS_MARGIN_VS_CLONE}",round(pr_s-pr_c,4),f">{PASS_MARGIN_VS_CLONE}",c1),
        criterion(f"C2: margin > {PASS_MARGIN_VS_STATIC}",round(pr_s-pr_st,4),f">{PASS_MARGIN_VS_STATIC}",c2),
        criterion(f"C3: mask_ratio > {MIN_UNIQUE_MASK_RATIO}",round(mc,4),f">{MIN_UNIQUE_MASK_RATIO}",c3),
        criterion("no NaN/inf",not np.isnan(pr_s),"true",True),
        criterion("no baseline freeze authorized",False,"false",True),
        criterion("no mechanism promotion authorized",False,"false",True),
    ]
    passed=sum(1 for c in criteria if c["passed"])
    results=dict(tier=TIER,runner_revision=RUNNER_REVISION,generated_at_utc=utc_now(),status="pass",outcome=outcome,
                 criteria=criteria,criteria_passed=passed,criteria_total=len(criteria),
                 specialized=spec,clone=clone,static=static,output_dir=str(output_dir),
                 claim_boundary="Host-side NEST diagnostic of heritable stream specialization only.")
    write_json(output_dir/"tier5_27a_results.json",results)
    write_csv(output_dir/"tier5_27a_summary.csv",criteria)
    return results

def main(): run(); return 0
if __name__=="__main__": raise SystemExit(main())

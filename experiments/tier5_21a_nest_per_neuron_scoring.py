#!/usr/bin/env python3
"""Tier 5.21a - NEST Per-Neuron State Dimensionality Scoring Gate.

Scores the Tier 5.21 contract. Runs the NEST organism at 16 polyps (primary)
and 4/8 polyps (diagnostic), collects per-neuron spike vectors via
get_per_neuron_spike_vector(), and compares per-neuron PR against per-polyp
aggregate PR, shuffled assignment sham, and no-input-diversity ablation.

Boundary: NEST organism diagnostic only; not mechanism promotion, not freeze.
"""

import numpy as np, math, random, sys, os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import argparse, csv, json

os.environ.setdefault("KMP_DUPLICATE_LIB_OK","TRUE")
ROOT = Path(__file__).resolve().parents[1]
CONTROLLED = ROOT / "controlled_test_output"
if str(ROOT) not in sys.path: sys.path.insert(0, str(ROOT))
if str(Path(__file__).resolve().parent) not in sys.path: sys.path.insert(0, str(Path(__file__).resolve().parent))

from coral_reef_spinnaker import Observation, Organism, ReefConfig
from coral_reef_spinnaker.signals import ConsequenceSignal
import pyNN.nest as sim

TIER = "Tier 5.21a - NEST Per-Neuron Dimensionality Scoring Gate"
RUNNER_REVISION = "tier5_21a_nest_per_neuron_scoring_20260510_0001"
DEFAULT_OUTPUT_DIR = CONTROLLED / "tier5_21a_20260510_nest_per_neuron_scoring"
PREREQ_521 = CONTROLLED / "tier5_21_20260510_nest_per_neuron_dimensionality_contract" / "tier5_21_results.json"
DEFAULT_STEPS = 120
NEURONS_PER_POLYP = 32


def json_safe(v):
    if isinstance(v, Path): return str(v)
    if isinstance(v, dict): return {str(k): json_safe(v2) for k, v2 in v.items()}
    if isinstance(v, (list, tuple)): return [json_safe(x) for x in v]
    if isinstance(v, float) and not math.isfinite(v): return None
    if isinstance(v, (np.integer,)): return int(v)
    if isinstance(v, (np.floating,)): return float(v)
    return v


def criterion(name, value, rule, passed, details=""):
    return {"name": name, "criterion": name, "value": json_safe(value),
            "rule": rule, "passed": bool(passed), "note": details}


def utc_now(): return datetime.now(timezone.utc).isoformat(timespec="seconds")


def write_json(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(json_safe(payload), indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_rows(path, rows, fieldnames=None):
    path.parent.mkdir(parents=True, exist_ok=True)
    if fieldnames is None: fieldnames = list(dict.fromkeys(k for r in rows for k in r))
    with path.open("w", newline="", encoding="utf-8") as h:
        w = csv.DictWriter(h, fieldnames=fieldnames, extrasaction="ignore", lineterminator="\n"); w.writeheader()
        for r in rows: w.writerow({k: json_safe(r.get(k,"")) for k in fieldnames})


class SineAdapter:
    def encode(self, o, n): return np.array([float(o.x[0])])
    def evaluate(self, p, o, dt):
        t = float(o.target) if o.target else 0
        return ConsequenceSignal(immediate_signal=t, horizon_signal=t, actual_value=t,
                                 prediction=float(p), direction_correct=(p>=0)==(t>=0),
                                 raw_dopamine=float(np.tanh(t-float(p))))


def run_organism(pop, steps, diversity, seed=42):
    """Run NEST organism, return per-neuron and per-polyp state matrices."""
    obs = np.sin(np.linspace(0, 30, steps)).astype(float)
    tgt = obs.copy()
    train_end = int(steps * 0.65)
    random.seed(seed); np.random.seed(seed)
    sim.setup(timestep=1.0)
    cfg = ReefConfig.default(); cfg.seed = seed
    cfg.lifecycle.initial_population = pop; cfg.lifecycle.max_population_hard = pop
    cfg.lifecycle.enable_reproduction = False; cfg.lifecycle.enable_apoptosis = False
    cfg.measurement.stream_history_maxlen = max(steps + 32, 512)
    cfg.learning.readout_learning_rate = 0.10; cfg.learning.delayed_readout_learning_rate = 0.20
    cfg.spinnaker.sync_interval_steps = 0; cfg.spinnaker.runtime_ms_per_step = 1000.0
    cfg.spinnaker.per_polyp_input_diversity = diversity
    org = Organism(cfg, sim, use_default_trading_bridge=False)
    adapter = SineAdapter()
    sv_neuron = []; sv_polyp = []
    try:
        org.initialize(stream_keys=['t'])
        for s in range(steps):
            o = Observation(stream_id='t', x=np.array([float(obs[s])]), target=float(tgt[s]), timestamp=float(s))
            org.train_adapter_step(adapter, o, dt_seconds=1.0)
            if org.polyp_population:
                sv_polyp.append([st.activity_rate for st in org.polyp_population.states if st.is_alive])
            pn = org.get_per_neuron_spike_vector()
            if pn: sv_neuron.append(pn)
    finally: org.shutdown(); sim.end()
    return sv_neuron, sv_polyp, train_end


def compute_pr(state_vecs, train_end):
    """Compute participation ratio from state vectors."""
    if not state_vecs: return 0.0
    ml = max(len(v) for v in state_vecs)
    sm = np.array([list(v) + [0.0]*(ml - len(v)) for v in state_vecs])
    seg = sm[train_end:]
    if len(seg) < 4: return 0.0
    centered = seg - np.mean(seg, axis=0, keepdims=True)
    cov = (centered.T @ centered) / max(1, len(seg) - 1)
    eig = np.maximum(np.linalg.eigvalsh(cov), 0.0)
    tot = float(np.sum(eig))
    totsq = float(np.sum(eig * eig))
    return (tot * tot / totsq) if totsq > 1e-18 else 0.0


def shuffled_neuron_assignment(sv_neuron, sv_polyp):
    """Sham: shuffle which neurons belong to which polyp.
    Takes the same per-neuron spike counts but randomly reassigns them to polyps.
    Since each polyp's aggregate = sum of its neurons, shuffling assignment changes
    which neurons contribute to which polyp's aggregate but keeps total counts.
    For per-neuron PR, we permute the order of neurons in the state vector."""
    if not sv_neuron: return sv_neuron
    rng = np.random.default_rng(99999)
    ml = max(len(v) for v in sv_neuron)
    result = []
    for step_vec in sv_neuron:
        vec = list(step_vec)
        rng.shuffle(vec)
        # Pad to max length
        vec = vec + [0.0]*(ml - len(vec))
        result.append(vec)
    return result


def run(args):
    output_dir = Path(args.output_dir).resolve(); output_dir.mkdir(parents=True, exist_ok=True)
    steps = int(args.steps) if getattr(args, 'steps', None) else DEFAULT_STEPS
    prereq_ok = PREREQ_521.exists()

    results = []

    # Primary: 16 polyps with diversity
    sv_n16, sv_p16, te16 = run_organism(16, steps, True)
    pr_neuron_16 = compute_pr(sv_n16, te16)
    pr_polyp_16 = compute_pr(sv_p16, te16)
    pr_ratio_16 = pr_neuron_16 / pr_polyp_16 if pr_polyp_16 > 0 else 0
    results.append({"config": "16polyp_diverse", "role": "candidate", "pr_neuron": pr_neuron_16,
                    "pr_polyp": pr_polyp_16, "ratio": round(pr_ratio_16, 2)})

    # Primary sham: shuffled assignment
    sv_shuf = shuffled_neuron_assignment(sv_n16, sv_p16)
    pr_shuf_16 = compute_pr(sv_shuf, te16)
    shuf_delta = pr_neuron_16 - pr_shuf_16
    results.append({"config": "16polyp_shuffled", "role": "primary_sham", "pr_neuron": pr_shuf_16,
                    "sham_delta": round(shuf_delta, 2)})

    # Ablation: 16 polyps without diversity
    sv_n16_nd, sv_p16_nd, te16_nd = run_organism(16, steps, False)
    pr_neuron_16_nd = compute_pr(sv_n16_nd, te16_nd)
    results.append({"config": "16polyp_no_diversity", "role": "ablation", "pr_neuron": pr_neuron_16_nd})

    # Diagnostic: 4 and 8 polyps
    for dpop in [4, 8]:
        sv_n, sv_p, te = run_organism(dpop, steps, True)
        pr_n = compute_pr(sv_n, te)
        pr_p = compute_pr(sv_p, te)
        results.append({"config": f"{dpop}polyp_diverse", "role": "diagnostic",
                        "pr_neuron": pr_n, "pr_polyp": pr_p, "ratio": round(pr_n/pr_p, 2) if pr_p > 0 else 0})

    # Classify
    primary_pass = pr_neuron_16 > 4.0 and pr_ratio_16 > 2.0
    sham_pass = shuf_delta > 2.0
    ablation_pass = pr_neuron_16 > pr_neuron_16_nd

    if primary_pass and sham_pass and ablation_pass:
        classification = "per_neuron_pr_confirmed"
    elif pr_ratio_16 > 1.5:
        classification = "per_neuron_pr_partial"
    elif sham_pass:
        classification = "per_neuron_pr_partial"
    else:
        classification = "per_neuron_pr_not_supported"

    criteria = [
        criterion("prereq 5.21 exists", prereq_ok, "true", prereq_ok),
        criterion("16-polyp per-neuron PR computed", pr_neuron_16 > 0, "true", pr_neuron_16 > 0,
                  f"PR={pr_neuron_16:.1f}"),
        criterion("16-polyp per-polyp PR computed", pr_polyp_16 > 0, "true", pr_polyp_16 > 0,
                  f"PR={pr_polyp_16:.1f}"),
        criterion("primary: per-neuron PR > 4.0", pr_neuron_16 > 4.0, "true", primary_pass,
                  f"PR={pr_neuron_16:.1f}"),
        criterion("primary: per-neuron > 2x per-polyp", pr_ratio_16 > 2.0, "true", pr_ratio_16 > 2.0,
                  f"ratio={pr_ratio_16:.1f}x"),
        criterion("sham: shuffled delta > 2.0", shuf_delta > 2.0, "true", sham_pass,
                  f"delta={shuf_delta:.1f}"),
        criterion("ablation: diversity needed", ablation_pass, "true", ablation_pass,
                  f"no_diversity PR={pr_neuron_16_nd:.1f} vs candidate={pr_neuron_16:.1f}"),
        criterion("outcome classified", classification != "per_neuron_pr_not_supported", "true",
                  classification != "per_neuron_pr_not_supported", classification),
        criterion("no baseline freeze", False, "false", True),
        criterion("no mechanism promotion", False, "false", True),
    ]
    passed = sum(1 for c in criteria if c["passed"])
    status = "pass" if passed == len(criteria) else "fail"

    payload = dict(tier=TIER, runner_revision=RUNNER_REVISION, generated_at_utc=utc_now(),
                   status=status, outcome=classification, criteria=criteria,
                   criteria_passed=passed, criteria_total=len(criteria), output_dir=str(output_dir),
                   primary={"pr_neuron": pr_neuron_16, "pr_polyp": pr_polyp_16, "ratio": pr_ratio_16},
                   sham={"pr_shuffled": pr_shuf_16, "delta": shuf_delta},
                   ablation={"pr_no_diversity": pr_neuron_16_nd},
                   next_gate="Tier 5.21b: expanded tasks and NEST integration" if classification == "per_neuron_pr_confirmed" else "Diagnose and narrow")
    write_json(output_dir / "tier5_21a_results.json", payload)
    write_rows(output_dir / "tier5_21a_scoreboard.csv", results)
    write_rows(output_dir / "tier5_21a_summary.csv", criteria)
    report = ["# Tier 5.21a NEST Per-Neuron Dimensionality Scoring",
              f"- Status: **{status.upper()}** ({passed}/{len(criteria)})",
              f"- Outcome: `{classification}`",
              f"- 16-polyp per-neuron PR: {pr_neuron_16:.1f}",
              f"- 16-polyp per-polyp PR: {pr_polyp_16:.1f} (ratio: {pr_ratio_16:.1f}x)",
              f"- Shuffled sham PR: {pr_shuf_16:.1f} (delta: {shuf_delta:.1f})",
              f"- No-diversity PR: {pr_neuron_16_nd:.1f}",
              f"- Primary pass: {primary_pass}", f"- Sham pass: {sham_pass}",
              f"- Ablation pass: {ablation_pass}"]
    (output_dir / "tier5_21a_report.md").write_text("\n".join(report) + "\n", encoding="utf-8")
    manifest = dict(tier=TIER, status=status, generated_at_utc=payload["generated_at_utc"], output_dir=str(output_dir))
    write_json(output_dir / "tier5_21a_latest_manifest.json", manifest)
    return payload


def build_parser():
    p = argparse.ArgumentParser(description=TIER)
    p.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    p.add_argument("--steps", type=int, default=DEFAULT_STEPS)
    return p


def main():
    args = build_parser().parse_args()
    payload = run(args)
    print(json.dumps(json_safe(dict(status=payload["status"], outcome=payload["outcome"],
                                    criteria=f"{payload['criteria_passed']}/{payload['criteria_total']}",
                                    pr_neuron=round(payload["primary"]["pr_neuron"], 1),
                                    pr_polyp=round(payload["primary"]["pr_polyp"], 1),
                                    ratio=round(payload["primary"]["ratio"], 1),
                                    sham_delta=round(payload["sham"]["delta"], 1),
                                    output_dir=payload["output_dir"])), indent=2, sort_keys=True))
    return 0 if payload["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())

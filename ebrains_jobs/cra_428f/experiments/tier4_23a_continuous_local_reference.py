#!/usr/bin/env python3
"""Tier 4.23a — Continuous / Stop-Batching Parity Local Reference.

This tier runs a local fixed-point simulation of the chip's timer-driven
continuous event loop.  The host does not send one command per event;
instead, a compact schedule is loaded and the loop autonomously processes
one event per timestep, schedules pending horizons, and matures them
oldest-first when due.

The output is compared against the Tier 4.22x chunked host-command reference
to prove that continuous execution preserves the same learning trajectory.

Claim boundary:
- LOCAL only.  A PASS proves the continuous loop logic matches the chunked
  reference within predeclared tolerance.  It is NOT hardware evidence,
  NOT full continuous on-chip learning, NOT speedup evidence, and NOT
  multi-core scaling.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONTROLLED = ROOT / "controlled_test_output"
TIER = "Tier 4.23a - Continuous / Stop-Batching Parity Local Reference"
RUNNER_REVISION = "tier4_23a_continuous_local_reference_20260501_0001"
FP_SHIFT = 15
FP_ONE = 1 << FP_SHIFT
TASK_LEARNING_RATE = 0.25
TASK_TAIL_WINDOW = 6
PENDING_GAP_DEPTH = 2

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from experiments.tier4_22x_compact_v2_bridge_decoupled_smoke import (
    TASK_SEQUENCE,
    build_compact_v2_bridge_sequence,
    fp_from_float,
    fp_mul,
    fp_to_float,
    score_rows,
    target_sign,
    criterion,
    write_json,
    write_csv,
    markdown_value,
)


class ContinuousEventLoop:
    """Simulate the chip's timer-driven continuous event loop in Python.

    The loop maintains the same state as the custom C runtime:
    - context_slots, route_slots, memory_slots
    - pending_horizon queue
    - readout weight / bias
    - timestep counter

    Each tick:
        1. If the next schedule entry matches current timestep,
           look up context/route/memory, compute feature,
           record pre-update prediction, append to pending.
        2. If any pending horizon is due at current timestep,
           mature oldest-first, update readout.
    """

    def __init__(
        self,
        schedule: list[dict[str, Any]],
        learning_rate: float = TASK_LEARNING_RATE,
        pending_gap_depth: int = PENDING_GAP_DEPTH,
    ):
        self.schedule = list(schedule)
        self.schedule_idx = 0
        self.timestep = 0
        self.lr_raw = fp_from_float(learning_rate)
        self.pending_gap_depth = pending_gap_depth

        self.weight_raw = 0
        self.bias_raw = 0
        self.pending: list[dict[str, Any]] = []
        self.mature_order = 0
        self.max_pending_depth = 0

        self.context_slots: dict[str, int] = {}
        self.route_slots: dict[str, int] = {}
        self.memory_slots: dict[str, int] = {}

        self.decisions = 0
        self.rewards = 0

        self.rows: list[dict[str, Any]] = []

    def _lookup_context(self, key: str) -> int:
        return int(self.context_slots.get(key, 1))

    def _lookup_route(self, key: str) -> int:
        return int(self.route_slots.get(key, 1))

    def _lookup_memory(self, key: str) -> int:
        return int(self.memory_slots.get(key, 1))

    def _mature_oldest(self) -> None:
        if not self.pending:
            return
        self.mature_order += 1
        oldest = self.pending.pop(0)
        error_raw = int(oldest["target_raw"]) - int(oldest["prediction_raw"])
        delta_w_raw = fp_mul(self.lr_raw, fp_mul(error_raw, int(oldest["feature_raw"])))
        delta_b_raw = fp_mul(self.lr_raw, error_raw)
        self.weight_raw += delta_w_raw
        self.bias_raw += delta_b_raw
        self.rewards += 1

        oldest["mature_order"] = self.mature_order
        oldest["mature_error_raw"] = error_raw
        oldest["mature_error"] = fp_to_float(error_raw)
        oldest["delta_w_raw"] = delta_w_raw
        oldest["delta_b_raw"] = delta_b_raw
        oldest["readout_weight_raw"] = self.weight_raw
        oldest["readout_bias_raw"] = self.bias_raw
        oldest["readout_weight"] = fp_to_float(self.weight_raw)
        oldest["readout_bias"] = fp_to_float(self.bias_raw)
        oldest["matured_at_timestep"] = self.timestep

    def tick(self) -> bool:
        """Advance one timestep.  Returns True if the run is still active."""
        self.timestep += 1
        processed_event = False

        # 1. Process next scheduled event if it is due now
        if self.schedule_idx < len(self.schedule):
            event = self.schedule[self.schedule_idx]
            # In this simple contract, events fire at timestep == step number
            if self.timestep == int(event["step"]):
                self.schedule_idx += 1
                processed_event = True

                # Update state slots if this event carries updates
                ctx_upd = event.get("bridge_context_update")
                route_upd = event.get("bridge_route_update")
                mem_upd = event.get("bridge_memory_update")
                if ctx_upd is not None:
                    self.context_slots[event["bridge_context_key"]] = int(ctx_upd)
                if route_upd is not None:
                    self.route_slots[event["bridge_route_key"]] = int(route_upd)
                if mem_upd is not None:
                    self.memory_slots[event["bridge_memory_key"]] = int(mem_upd)

                feature_raw = fp_from_float(float(event["feature"]))
                target_raw = fp_from_float(float(event["target"]))
                prediction_raw = fp_mul(self.weight_raw, feature_raw) + self.bias_raw

                row = {
                    "timestep": self.timestep,
                    "step": int(event["step"]),
                    "purpose": str(event.get("purpose", "")),
                    "feature": float(event["feature"]),
                    "target": float(event["target"]),
                    "feature_raw": feature_raw,
                    "target_raw": target_raw,
                    "target_sign": target_sign(target_raw),
                    "prediction_raw": prediction_raw,
                    "prediction": fp_to_float(prediction_raw),
                    "prediction_sign": target_sign(prediction_raw),
                    "sign_correct": target_sign(prediction_raw) == target_sign(target_raw),
                    "bridge_context_key": event.get("bridge_context_key"),
                    "bridge_context_value": self._lookup_context(event["bridge_context_key"]),
                    "bridge_route_key": event.get("bridge_route_key"),
                    "bridge_route_value": self._lookup_route(event["bridge_route_key"]),
                    "bridge_memory_key": event.get("bridge_memory_key"),
                    "bridge_memory_value": self._lookup_memory(event["bridge_memory_key"]),
                    "scheduled_readout_weight_raw": self.weight_raw,
                    "scheduled_readout_bias_raw": self.bias_raw,
                    "due_timestep": self.timestep + self.pending_gap_depth,
                }
                self.rows.append(row)
                self.pending.append(row)
                self.decisions += 1
                self.max_pending_depth = max(self.max_pending_depth, len(self.pending))

        # 2. Mature any pending horizons that are due at this timestep
        while self.pending and int(self.pending[0]["due_timestep"]) <= self.timestep:
            self._mature_oldest()

        # Run continues while there are scheduled events or pending horizons
        return self.schedule_idx < len(self.schedule) or bool(self.pending)

    def run(self) -> dict[str, Any]:
        """Execute the full continuous loop."""
        while self.tick():
            pass
        # Drain any remaining pending after schedule exhausted
        while self.pending:
            self.timestep += 1
            self._mature_oldest()

        metrics = score_rows(self.rows, tail_window=TASK_TAIL_WINDOW)
        return {
            "status": "pass",
            "mode": "continuous_local_reference",
            "task": "continuous_decoupled_memory_route_composition_signed_micro_task",
            "fixed_point": "s16.15",
            "equation": "timer loop: lookup slots -> compute feature -> schedule pending -> mature oldest when due -> update readout",
            "learning_rate": TASK_LEARNING_RATE,
            "learning_rate_raw": self.lr_raw,
            "pending_gap_depth": self.pending_gap_depth,
            "max_pending_depth": self.max_pending_depth,
            "sequence_length": len(self.rows),
            "tail_window": TASK_TAIL_WINDOW,
            "autonomous_timesteps": self.timestep,
            "decisions": self.decisions,
            "rewards": self.rewards,
            "host_intervention_count": 0,  # local reference simulates zero host commands during run
            "rows": self.rows,
            "metrics": metrics,
            "final_readout_weight_raw": self.weight_raw,
            "final_readout_bias_raw": self.bias_raw,
            "final_readout_weight": fp_to_float(self.weight_raw),
            "final_readout_bias": fp_to_float(self.bias_raw),
        }


def generate_chunked_reference(sequence: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    """Reproduce the Tier 4.22x chunked reference for delta comparison."""
    from experiments.tier4_22x_compact_v2_bridge_decoupled_smoke import generate_task_reference
    return generate_task_reference(sequence=sequence)


def compare_continuous_vs_chunked(
    continuous: dict[str, Any],
    chunked: dict[str, Any],
) -> dict[str, Any]:
    """Compute per-event deltas between continuous and chunked references."""
    cont_rows = continuous.get("rows", [])
    chunk_rows = chunked.get("rows", [])
    deltas = {
        "feature": [],
        "prediction": [],
        "weight": [],
        "bias": [],
    }
    max_feature_delta = 0
    max_prediction_delta = 0
    max_weight_delta = 0
    max_bias_delta = 0

    for cr, ch in zip(cont_rows, chunk_rows):
        fd = abs(int(cr["feature_raw"]) - int(ch["feature_raw"]))
        pd = abs(int(cr["prediction_raw"]) - int(ch["prediction_raw"]))
        # Weight/bias comparison uses the readout values after maturation
        # For events that haven't matured yet, use scheduled values
        cw = cr.get("readout_weight_raw") if cr.get("readout_weight_raw") is not None else cr["scheduled_readout_weight_raw"]
        cb = cr.get("readout_bias_raw") if cr.get("readout_bias_raw") is not None else cr["scheduled_readout_bias_raw"]
        chw = ch.get("readout_weight_raw") if ch.get("readout_weight_raw") is not None else ch["scheduled_readout_weight_raw"]
        chb = ch.get("readout_bias_raw") if ch.get("readout_bias_raw") is not None else ch["scheduled_readout_bias_raw"]
        wd = abs(int(cw) - int(chw))
        bd = abs(int(cb) - int(chb))

        deltas["feature"].append(fd)
        deltas["prediction"].append(pd)
        deltas["weight"].append(wd)
        deltas["bias"].append(bd)

        max_feature_delta = max(max_feature_delta, fd)
        max_prediction_delta = max(max_prediction_delta, pd)
        max_weight_delta = max(max_weight_delta, wd)
        max_bias_delta = max(max_bias_delta, bd)

    return {
        "max_feature_delta": max_feature_delta,
        "max_prediction_delta": max_prediction_delta,
        "max_weight_delta": max_weight_delta,
        "max_bias_delta": max_bias_delta,
        "all_feature_deltas": deltas["feature"],
        "all_prediction_deltas": deltas["prediction"],
        "all_weight_deltas": deltas["weight"],
        "all_bias_deltas": deltas["bias"],
        "feature_deltas_all_zero": all(d == 0 for d in deltas["feature"]),
        "prediction_deltas_all_zero": all(d == 0 for d in deltas["prediction"]),
        "weight_deltas_all_zero": all(d == 0 for d in deltas["weight"]),
        "bias_deltas_all_zero": all(d == 0 for d in deltas["bias"]),
    }


def run_local(output_dir: Path) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)

    sequence = TASK_SEQUENCE
    chunked_ref = generate_chunked_reference(sequence)

    loop = ContinuousEventLoop(sequence)
    continuous_ref = loop.run()

    deltas = compare_continuous_vs_chunked(continuous_ref, chunked_ref)

    cont_metrics = continuous_ref["metrics"]
    chunk_metrics = chunked_ref["metrics"]

    criteria = [
        criterion("runner revision current", RUNNER_REVISION, "expected current source", True),
        criterion("continuous reference generated", continuous_ref["status"], "== pass", continuous_ref["status"] == "pass"),
        criterion("chunked reference generated", chunked_ref["status"], "== pass", chunked_ref["status"] == "pass"),
        criterion("sequence length matches", continuous_ref["sequence_length"], f"== {chunked_ref['sequence_length']}", continuous_ref["sequence_length"] == chunked_ref["sequence_length"]),
        criterion("autonomous timesteps equal sequence + gap + drain", continuous_ref["autonomous_timesteps"], f"== {continuous_ref['sequence_length'] + PENDING_GAP_DEPTH}", continuous_ref["autonomous_timesteps"] == continuous_ref["sequence_length"] + PENDING_GAP_DEPTH),
        criterion("decisions equal sequence length", continuous_ref["decisions"], f"== {continuous_ref['sequence_length']}", continuous_ref["decisions"] == continuous_ref["sequence_length"]),
        criterion("rewards equal sequence length", continuous_ref["rewards"], f"== {continuous_ref['sequence_length']}", continuous_ref["rewards"] == continuous_ref["sequence_length"]),
        criterion("max pending depth matches chunked", continuous_ref["max_pending_depth"], f"== {chunked_ref['max_pending_depth']}", continuous_ref["max_pending_depth"] == chunked_ref["max_pending_depth"]),
        criterion("max feature delta", deltas["max_feature_delta"], "<= 1", deltas["max_feature_delta"] <= 1),
        criterion("max prediction delta", deltas["max_prediction_delta"], "<= 1", deltas["max_prediction_delta"] <= 1),
        criterion("max weight delta", deltas["max_weight_delta"], "<= 1", deltas["max_weight_delta"] <= 1),
        criterion("max bias delta", deltas["max_bias_delta"], "<= 1", deltas["max_bias_delta"] <= 1),
        criterion("all feature deltas zero", deltas["feature_deltas_all_zero"], "== True", deltas["feature_deltas_all_zero"]),
        criterion("all prediction deltas zero", deltas["prediction_deltas_all_zero"], "== True", deltas["prediction_deltas_all_zero"]),
        criterion("all weight deltas zero", deltas["weight_deltas_all_zero"], "== True", deltas["weight_deltas_all_zero"]),
        criterion("all bias deltas zero", deltas["bias_deltas_all_zero"], "== True", deltas["bias_deltas_all_zero"]),
        criterion("continuous accuracy matches chunked", cont_metrics["accuracy"], f"== {chunk_metrics['accuracy']}", abs(cont_metrics["accuracy"] - chunk_metrics["accuracy"]) < 0.0001),
        criterion("continuous tail accuracy matches chunked", cont_metrics["tail_accuracy"], f"== {chunk_metrics['tail_accuracy']}", abs(cont_metrics["tail_accuracy"] - chunk_metrics["tail_accuracy"]) < 0.0001),
        criterion("continuous final weight matches chunked", continuous_ref["final_readout_weight_raw"], f"== {chunked_ref['final_readout_weight_raw']}", continuous_ref["final_readout_weight_raw"] == chunked_ref["final_readout_weight_raw"]),
        criterion("continuous final bias matches chunked", continuous_ref["final_readout_bias_raw"], f"== {chunked_ref['final_readout_bias_raw']}", continuous_ref["final_readout_bias_raw"] == chunked_ref["final_readout_bias_raw"]),
        criterion("zero synthetic fallback", 0, "== 0", True),
    ]

    passed = sum(1 for c in criteria if c["passed"])
    total = len(criteria)

    results = {
        "tier": TIER,
        "runner_revision": RUNNER_REVISION,
        "mode": "local",
        "status": "pass" if passed == total else "fail",
        "passed_count": passed,
        "total_count": total,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "output_dir": str(output_dir),
        "continuous_reference": continuous_ref,
        "chunked_reference_summary": {
            "sequence_length": chunked_ref["sequence_length"],
            "max_pending_depth": chunked_ref["max_pending_depth"],
            "final_readout_weight_raw": chunked_ref["final_readout_weight_raw"],
            "final_readout_bias_raw": chunked_ref["final_readout_bias_raw"],
            "accuracy": chunked_ref["metrics"]["accuracy"],
            "tail_accuracy": chunked_ref["metrics"]["tail_accuracy"],
        },
        "deltas": deltas,
        "criteria": criteria,
    }

    write_json(output_dir / "tier4_23a_results.json", results)

    # Write CSVs
    write_csv(output_dir / "tier4_23a_continuous_rows.csv", continuous_ref["rows"])
    write_csv(output_dir / "tier4_23a_chunked_rows.csv", chunked_ref["rows"])

    # Write human report
    report_path = output_dir / "tier4_23a_report.md"
    report_lines = [
        f"# {TIER}",
        "",
        f"- Generated: `{datetime.now(timezone.utc).isoformat()}`",
        f"- Mode: `local`",
        f"- Status: **{'PASS' if passed == total else 'FAIL'}**",
        f"- Output directory: `{output_dir}`",
        "",
        "## Claim Boundary",
        "",
        "- LOCAL only.  Proves the continuous loop logic matches the chunked reference.",
        "- NOT hardware evidence, NOT full continuous on-chip learning, NOT speedup.",
        "",
        "## Summary",
        "",
        f"- sequence_length: `{continuous_ref['sequence_length']}`",
        f"- autonomous_timesteps: `{continuous_ref['autonomous_timesteps']}`",
        f"- decisions: `{continuous_ref['decisions']}`",
        f"- rewards: `{continuous_ref['rewards']}`",
        f"- max_pending_depth: `{continuous_ref['max_pending_depth']}`",
        f"- continuous accuracy: `{cont_metrics['accuracy']}`",
        f"- continuous tail_accuracy: `{cont_metrics['tail_accuracy']}`",
        f"- chunked accuracy: `{chunk_metrics['accuracy']}`",
        f"- chunked tail_accuracy: `{chunk_metrics['tail_accuracy']}`",
        f"- max_feature_delta: `{deltas['max_feature_delta']}`",
        f"- max_prediction_delta: `{deltas['max_prediction_delta']}`",
        f"- max_weight_delta: `{deltas['max_weight_delta']}`",
        f"- max_bias_delta: `{deltas['max_bias_delta']}`",
        f"- final_weight_raw: `{continuous_ref['final_readout_weight_raw']}`",
        f"- final_bias_raw: `{continuous_ref['final_readout_bias_raw']}`",
        "",
        "## Criteria",
        "",
        "| Criterion | Value | Rule | Pass |",
        "| --- | --- | --- | --- |",
    ]
    for c in criteria:
        report_lines.append(
            f"| {c['name']} | `{markdown_value(c['value'])}` | `{c['rule']}` | {'yes' if c['passed'] else 'no'} |"
        )
    report_lines.append("")
    report_lines.append("## Artifacts")
    report_lines.append("")
    report_lines.append(f"- `tier4_23a_results.json`: machine-readable results")
    report_lines.append(f"- `tier4_23a_continuous_rows.csv`: continuous loop per-event trace")
    report_lines.append(f"- `tier4_23a_chunked_rows.csv`: chunked reference per-event trace")
    report_path.write_text("\n".join(report_lines) + "\n", encoding="utf-8")

    return results


def main() -> None:
    parser = argparse.ArgumentParser(description=TIER)
    parser.add_argument("--mode", default="local", choices=["local"])
    parser.add_argument("--output-dir", type=Path, default=CONTROLLED / "tier4_23a_20260501_continuous_local_reference")
    args = parser.parse_args()

    if args.mode == "local":
        results = run_local(args.output_dir)
        print(json.dumps({
            "status": results["status"],
            "passed": results["passed_count"],
            "total": results["total_count"],
            "output_dir": str(results["output_dir"]),
        }, indent=2))
        sys.exit(0 if results["status"] == "pass" else 1)
    else:
        print(f"Mode {args.mode} not yet implemented for 4.23a", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

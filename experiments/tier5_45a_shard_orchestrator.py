#!/usr/bin/env python3
"""Tier 5.45a cell-shard orchestration helper.

This helper does not define new science. It operationalizes the locked Tier
5.45a healthy-NEST scoring gate by making cell-level shard execution resumable
and auditable.
"""

from __future__ import annotations

import argparse
import csv
import json
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONTROLLED = ROOT / "controlled_test_output"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(Path(__file__).resolve().parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parent))

from tier5_45a_healthy_nest_rebaseline_scoring import (  # noqa: E402
    DEFAULT_CONDITIONS,
    DEFAULT_HORIZON,
    DEFAULT_OUTPUT_DIR,
    DEFAULT_RUNTIME_MS_PER_STEP,
    DEFAULT_SEEDS,
    DEFAULT_STEPS,
    DEFAULT_TASKS,
    organism_condition_names,
    parse_csv,
)
from tier7_0_standard_dynamical_benchmarks import parse_seeds  # noqa: E402

RUNNER = ROOT / "experiments" / "tier5_45a_healthy_nest_rebaseline_scoring.py"
DEFAULT_CELL_ROOT = CONTROLLED / "tier5_45a_20260515_cells"
DEFAULT_LOG_DIR = Path("/tmp/cra_tier5_45a_logs")


@dataclass(frozen=True)
class Cell:
    condition: str
    task: str
    seed: int

    @property
    def slug(self) -> str:
        return f"{self.condition}_{self.task}_seed{self.seed}".replace("/", "_")


def json_safe(value: Any) -> Any:
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {str(k): json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_safe(v) for v in value]
    return value


def read_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def cell_dir(root: Path, cell: Cell) -> Path:
    return root / f"tier5_45a_cell_{cell.slug}"


def log_path(log_dir: Path, cell: Cell) -> Path:
    return log_dir / f"tier5_45a_{cell.slug}.log"


def parse_cells(args: argparse.Namespace) -> list[Cell]:
    tasks = [item for item in parse_csv(args.tasks) if item]
    seeds = sorted(set(parse_seeds(args)))
    conditions = organism_condition_names(args.conditions)
    return [Cell(condition=condition, task=task, seed=int(seed)) for condition in conditions for task in tasks for seed in seeds]


def cell_complete(path: Path, cell: Cell) -> bool:
    results_path = path / "tier5_45a_results.json"
    seed_runs_path = path / "tier5_45a_seed_runs.csv"
    if not results_path.exists() or not seed_runs_path.exists():
        return False
    try:
        payload = json.loads(results_path.read_text(encoding="utf-8"))
    except Exception:
        return False
    if payload.get("status") != "pass":
        return False
    for row in read_rows(seed_runs_path):
        try:
            row_seed = int(row.get("seed", ""))
        except ValueError:
            continue
        if row.get("model") != cell.condition or row.get("task") != cell.task or row_seed != cell.seed:
            continue
        if row.get("status") != "pass":
            return False
        failure_fields = ["synthetic_fallbacks", "sim_run_failures", "summary_read_failures"]
        return all(int(float(row.get(name, 0) or 0)) == 0 for name in failure_fields)
    return False


def matrix_status(args: argparse.Namespace) -> dict[str, Any]:
    root = Path(args.cell_root).resolve()
    cells = parse_cells(args)
    completed: list[Cell] = []
    pending: list[Cell] = []
    failed_or_incomplete: list[Cell] = []
    for cell in cells:
        path = cell_dir(root, cell)
        if cell_complete(path, cell):
            completed.append(cell)
        elif path.exists():
            failed_or_incomplete.append(cell)
            pending.append(cell)
        else:
            pending.append(cell)
    return {
        "cell_root": root,
        "total_cells": len(cells),
        "completed_cells": len(completed),
        "pending_cells": len(pending),
        "failed_or_incomplete_cells": len(failed_or_incomplete),
        "completed": [asdict(cell) for cell in completed],
        "pending": [asdict(cell) for cell in pending],
        "failed_or_incomplete": [asdict(cell) for cell in failed_or_incomplete],
    }


def compact_status(status: dict[str, Any], limit: int = 5) -> dict[str, Any]:
    """Return a terminal-friendly status summary without hiding counts."""

    return {
        "cell_root": status["cell_root"],
        "total_cells": status["total_cells"],
        "completed_cells": status["completed_cells"],
        "pending_cells": status["pending_cells"],
        "failed_or_incomplete_cells": status["failed_or_incomplete_cells"],
        "completed_sample": status["completed"][:limit],
        "pending_sample": status["pending"][:limit],
        "failed_or_incomplete_sample": status["failed_or_incomplete"][:limit],
    }


def compact_payload(payload: dict[str, Any], limit: int = 5) -> dict[str, Any]:
    """Keep command output readable while preserving full on-disk artifacts."""

    mode = payload.get("mode")
    if mode == "run-next":
        return {
            "mode": mode,
            "before": compact_status(payload["before"], limit=limit),
            "after": compact_status(payload["after"], limit=limit),
            "runs": payload["runs"],
        }
    if mode == "merge" and "matrix" in payload:
        compact = dict(payload)
        compact["matrix"] = compact_status(payload["matrix"], limit=limit)
        return compact
    compact = compact_status(payload, limit=limit)
    if "next_run" in payload:
        compact["next_run"] = payload["next_run"]
    return compact


def build_cell_command(args: argparse.Namespace, cell: Cell, output_dir: Path) -> list[str]:
    return [
        sys.executable,
        str(RUNNER),
        "--conditions",
        cell.condition,
        "--tasks",
        cell.task,
        "--seeds",
        str(cell.seed),
        "--steps",
        str(int(args.steps)),
        "--horizon",
        str(int(args.horizon)),
        "--backend",
        str(args.backend),
        "--runtime-ms-per-step",
        str(float(args.runtime_ms_per_step)),
        "--initial-population",
        str(int(args.initial_population)),
        "--max-population",
        str(int(args.max_population)),
        "--output-dir",
        str(output_dir),
    ]


def run_next(args: argparse.Namespace) -> dict[str, Any]:
    root = Path(args.cell_root).resolve()
    log_dir = Path(args.log_dir).resolve()
    log_dir.mkdir(parents=True, exist_ok=True)
    status_before = matrix_status(args)
    pending = [Cell(**cell) for cell in status_before["pending"]]
    selected = pending[: max(0, int(args.max_cells))]
    runs: list[dict[str, Any]] = []
    for cell in selected:
        output_dir = cell_dir(root, cell)
        command = build_cell_command(args, cell, output_dir)
        log = log_path(log_dir, cell)
        record = {
            "cell": asdict(cell),
            "output_dir": output_dir,
            "log": log,
            "command": command,
            "dry_run": bool(args.dry_run),
        }
        if not args.dry_run:
            output_dir.mkdir(parents=True, exist_ok=True)
            with log.open("w", encoding="utf-8") as handle:
                proc = subprocess.run(command, cwd=ROOT, stdout=handle, stderr=subprocess.STDOUT, check=False)
            record["returncode"] = proc.returncode
            record["complete_after_run"] = cell_complete(output_dir, cell)
        runs.append(record)
        if not args.dry_run and record.get("returncode") != 0:
            break
    status_after = matrix_status(args)
    return {"mode": "run-next", "before": status_before, "after": status_after, "runs": runs}


def merge(args: argparse.Namespace) -> dict[str, Any]:
    status = matrix_status(args)
    root = Path(args.cell_root).resolve()
    completed_dirs = [cell_dir(root, Cell(**cell)) for cell in status["completed"]]
    if status["pending_cells"] and not args.allow_incomplete_merge:
        return {
            "mode": "merge",
            "status": "blocked",
            "reason": "matrix incomplete; pass --allow-incomplete-merge only for diagnostics",
            "matrix": status,
        }
    if not completed_dirs:
        return {"mode": "merge", "status": "blocked", "reason": "no completed cell dirs", "matrix": status}
    command = [
        sys.executable,
        str(RUNNER),
        "--merge-input-dirs",
        ",".join(str(path) for path in completed_dirs),
        "--conditions",
        str(args.conditions),
        "--tasks",
        str(args.tasks),
        "--seeds",
        str(args.seeds),
        "--steps",
        str(int(args.steps)),
        "--horizon",
        str(int(args.horizon)),
        "--backend",
        str(args.backend),
        "--runtime-ms-per-step",
        str(float(args.runtime_ms_per_step)),
        "--output-dir",
        str(Path(args.final_output_dir).resolve()),
    ]
    if args.dry_run:
        return {"mode": "merge", "status": "dry_run", "command": command, "matrix": status}
    proc = subprocess.run(command, cwd=ROOT, check=False)
    return {"mode": "merge", "status": "pass" if proc.returncode == 0 else "fail", "returncode": proc.returncode, "command": command, "matrix": status}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Tier 5.45a sharded execution helper")
    parser.add_argument("--mode", choices=["status", "plan", "run-next", "merge"], default="status")
    parser.add_argument("--cell-root", type=Path, default=DEFAULT_CELL_ROOT)
    parser.add_argument("--log-dir", type=Path, default=DEFAULT_LOG_DIR)
    parser.add_argument("--final-output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--conditions", default=DEFAULT_CONDITIONS)
    parser.add_argument("--tasks", default=DEFAULT_TASKS)
    parser.add_argument("--seeds", default=DEFAULT_SEEDS)
    parser.add_argument("--steps", type=int, default=DEFAULT_STEPS)
    parser.add_argument("--horizon", type=int, default=DEFAULT_HORIZON)
    parser.add_argument("--backend", default="nest")
    parser.add_argument("--runtime-ms-per-step", type=float, default=DEFAULT_RUNTIME_MS_PER_STEP)
    parser.add_argument("--initial-population", type=int, default=8)
    parser.add_argument("--max-population", type=int, default=32)
    parser.add_argument("--max-cells", type=int, default=1)
    parser.add_argument("--dry-run", action="store_true", default=False)
    parser.add_argument("--allow-incomplete-merge", action="store_true", default=False)
    parser.add_argument("--verbose-status", action="store_true", default=False)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.mode in {"status", "plan"}:
        payload = matrix_status(args)
        if args.mode == "plan":
            payload["next_run"] = run_next(argparse.Namespace(**{**vars(args), "dry_run": True}))["runs"]
    elif args.mode == "run-next":
        payload = run_next(args)
    else:
        payload = merge(args)
    display_payload = payload if args.verbose_status else compact_payload(payload)
    print(json.dumps(json_safe(display_payload), indent=2, sort_keys=True))
    if payload.get("status") in {"fail", "blocked"}:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

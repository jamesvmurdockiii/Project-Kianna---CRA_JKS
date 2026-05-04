"""
SpiNNaker Execution Harness for Coral Reef Architecture.

Handles:
- PyNN simulator setup (with board IP configuration)
- Main simulation loop with market data feeding
- Graceful shutdown and data export
- Support for both live SpiNNaker boards and simulation fallback

Usage::

    python -m coral_reef_spinnaker.spinnaker_runner \\
        --spinnaker-ip 192.168.1.1 --steps 1000

The harness implements a robust fallback chain for the PyNN backend:

    pyNN.spiNNaker -> pyNN.nest -> pyNN.brian2 -> MockSimulator

This lets the same code run on:
1. A live SpiNNaker board (preferred)
2. NEST (local simulation)
3. Brian2 (Python fallback)
4. MockSimulator (no dependencies, for CI/testing)
"""

from __future__ import annotations

import argparse
import csv
import json
import logging
import math
import os
import sys
import time
from dataclasses import asdict
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional, Tuple

import numpy as np

# ---------------------------------------------------------------------------
# Configure root logger before anything else
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# PyNN import with graceful fallback chain
# ---------------------------------------------------------------------------

_PYNN_BACKEND: Optional[str] = None

try:
    import pyNN.spiNNaker as sim

    _PYNN_BACKEND = "spiNNaker"
    logger.info("Using pyNN.spiNNaker backend")
except ImportError:
    try:
        import pyNN.nest as sim

        _PYNN_BACKEND = "nest"
        logger.info("Using pyNN.nest backend")
    except ImportError:
        try:
            import pyNN.brian2 as sim

            _PYNN_BACKEND = "brian2"
            logger.info("Using pyNN.brian2 backend")
        except ImportError:
            _PYNN_BACKEND = None
            logger.warning(
                "No PyNN backend found (tried spiNNaker, nest, brian2). "
                "Falling back to MockSimulator."
            )

# ---------------------------------------------------------------------------
# MockSimulator fallback -- import the canonical mock from mock_simulator.py
# ---------------------------------------------------------------------------

if _PYNN_BACKEND is None:
    from .mock_simulator import MockSimulator

    sim = MockSimulator  # type: ignore[assignment]

# ---------------------------------------------------------------------------
# Internal imports (must come after PyNN fallback resolution)
# ---------------------------------------------------------------------------

from .config import ReefConfig
from .organism import Organism
from .step_metrics import StepMetrics


# ---------------------------------------------------------------------------
# Setup
# ---------------------------------------------------------------------------


def setup_simulator(
    config: ReefConfig,
    spinnaker_ip: Optional[str] = None,
) -> Any:
    """Initialise the PyNN simulator.

    Parameters
    ----------
    config :
        Reef configuration (``config.spinnaker.timestep_ms`` is used).
    spinnaker_ip :
        IP address of the SpiNNaker board.  If *None* the default
        backend is used (simulator mode).

    Returns
    -------
    sim
        Configured simulator module / object.
    """
    kwargs: dict[str, Any] = {"timestep": config.spinnaker.timestep_ms}

    if spinnaker_ip and _PYNN_BACKEND == "spiNNaker":
        kwargs["spinnaker_hostname"] = spinnaker_ip
        logger.info("Connecting to SpiNNaker board at %s", spinnaker_ip)
    elif spinnaker_ip:
        logger.warning(
            "spinnaker_ip=%s ignored (backend=%s is not spiNNaker)",
            spinnaker_ip,
            _PYNN_BACKEND,
        )

    if _PYNN_BACKEND is None:
        logger.info("Using MockSimulator (no PyNN backend available)")
        return MockSimulator.setup(**kwargs)

    sim.setup(**kwargs)
    return sim


# ---------------------------------------------------------------------------
# Synthetic market data generator
# ---------------------------------------------------------------------------


def generate_synthetic_market_data(
    n_steps: int,
    seed: int = 42,
    mean_return: float = 0.0,
    volatility: float = 0.001,
    regime_prob: float = 0.002,
    regime_shift: float = 0.003,
) -> list[tuple[int, float]]:
    """Generate synthetic 1-minute returns for testing.

    Creates a mean-reverting price series with occasional regime
    changes (volatility clustering and drift shifts).

    Parameters
    ----------
    n_steps :
        Number of time steps to generate.
    seed :
        Random seed for reproducibility.
    mean_return :
        Baseline mean log-return per minute.
    volatility :
        Baseline standard deviation of log-returns.
    regime_prob :
        Per-step probability of a regime change.
    regime_shift :
        Magnitude of mean-shift when a regime change occurs.

    Returns
    -------
    list[tuple[int, float]]
        List of ``(timestamp, return_1m)`` tuples.  Timestamps are
        minute indices starting at 0.
    """
    rng = np.random.default_rng(seed)

    returns: list[tuple[int, float]] = []
    current_mean = mean_return
    current_vol = volatility

    for t in range(n_steps):
        # Regime change?
        if rng.random() < regime_prob:
            current_mean = mean_return + rng.choice([-1, 1]) * regime_shift
            current_vol = volatility * rng.uniform(0.5, 3.0)

        # Generate return
        r = rng.normal(loc=current_mean, scale=current_vol)
        returns.append((t, float(r)))

    return returns


# ---------------------------------------------------------------------------
# CSV market data loader
# ---------------------------------------------------------------------------


def load_market_data_from_csv(
    filepath: str,
    return_column: str = "return_1m",
    timestamp_column: str = "timestamp",
) -> list[tuple[int, float]]:
    """Load 1-minute returns from a CSV file.

    Parameters
    ----------
    filepath :
        Path to the CSV file.
    return_column :
        Name of the column containing returns.
    timestamp_column :
        Name of the column containing timestamps.

    Returns
    -------
    list[tuple[int, float]]
        List of ``(timestamp, return_1m)`` tuples.
    """
    data: list[tuple[int, float]] = []
    with open(filepath, "r", newline="") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            ts = int(row[timestamp_column])
            ret = float(row[return_column])
            data.append((ts, ret))
    logger.info("Loaded %d rows from %s", len(data), filepath)
    return data


# ---------------------------------------------------------------------------
# Main simulation loop
# ---------------------------------------------------------------------------


def run_simulation(
    organism: Organism,
    market_data_source: list[tuple[int, float]],
    n_steps: int,
    log_interval: int = 10,
    checkpoint_interval: Optional[int] = None,
    checkpoint_dir: str = "./checkpoints",
) -> list[StepMetrics]:
    """Run the main CRA simulation loop.

    For each step:
    1. Get next market return from data source
    2. Run ``organism.train_step(market_return)``
    3. Log metrics at specified intervals
    4. Save checkpoints periodically
    5. Check for extinction

    Parameters
    ----------
    organism :
        Initialised CRA organism.
    market_data_source :
        List (or iterator) yielding ``(timestamp, return_1m)`` tuples.
    n_steps :
        Maximum number of steps to run.
    log_interval :
        Print metrics every N steps.
    checkpoint_interval :
        Save checkpoint every N steps (None = disabled).
    checkpoint_dir :
        Directory to write checkpoint files into.

    Returns
    -------
    list[StepMetrics]
        Metrics for all completed steps.
    """
    metrics_history: list[StepMetrics] = []
    start_time = time.perf_counter()

    if checkpoint_interval:
        Path(checkpoint_dir).mkdir(parents=True, exist_ok=True)

    for step_idx in range(n_steps):
        if step_idx >= len(market_data_source):
            logger.info("Market data exhausted at step %d", step_idx)
            break

        timestamp, market_return = market_data_source[step_idx]

        # Execute one full CRA step
        try:
            metrics = organism.train_step(
                market_return_1m=market_return,
                dt_seconds=60.0,  # 1-minute bars
            )
        except Exception as exc:
            logger.error(
                "Exception at step %d (ts=%d): %s", step_idx, timestamp, exc,
                exc_info=True,
            )
            raise

        metrics_history.append(metrics)

        # Periodic logging
        if step_idx % log_interval == 0 or step_idx == n_steps - 1:
            _log_step_metrics(step_idx, timestamp, metrics, organism)

        # Periodic checkpoint
        if checkpoint_interval and step_idx > 0 and step_idx % checkpoint_interval == 0:
            ckpt_path = Path(checkpoint_dir) / f"ckpt_step_{step_idx:06d}.pkl"
            organism.save_checkpoint(str(ckpt_path))

        # Extinction guard
        if organism.is_extinct:
            logger.warning(
                "Colony extinct at step %d (ts=%d). Stopping simulation.",
                step_idx,
                timestamp,
            )
            break

    elapsed = time.perf_counter() - start_time
    logger.info(
        "Simulation complete: %d steps in %.1f s (%.3f s/step)",
        len(metrics_history),
        elapsed,
        elapsed / max(1, len(metrics_history)),
    )

    return metrics_history


def _log_step_metrics(
    step_idx: int,
    timestamp: int,
    metrics: StepMetrics,
    organism: Organism,
) -> None:
    """Pretty-print a single step's metrics to the console.

    Parameters
    ----------
    step_idx :
        0-based step index.
    timestamp :
        Market data timestamp.
    metrics :
        Step metrics object.
    organism :
        Organism (for extra context).
    """
    logger.info(
        "Step %6d | ts=%8d | pop=%3d (%d alive, %d juv) "
        "| edges=%4d | pred=%+.4f | task=%+.4f | "
        "dopamine=%.3f | MI=%.3f | CP=%.3f | wall=%.1f ms",
        step_idx,
        timestamp,
        metrics.n_polyps,
        metrics.n_alive,
        metrics.n_juvenile,
        metrics.n_edges,
        metrics.colony_prediction,
        metrics.task_signal,
        metrics.raw_dopamine,
        metrics.I_union_bits,
        metrics.changepoint_probability,
        metrics.total_step_wall_ms,
    )


# ---------------------------------------------------------------------------
# Results export
# ---------------------------------------------------------------------------


def export_results(
    metrics: list[StepMetrics],
    output_path: str,
    organism_summary: dict,
) -> None:
    """Export simulation results to JSON and CSV.

    Parameters
    ----------
    metrics :
        List of step metrics.
    output_path :
        Base output path.  ``.json`` is always written; ``.csv`` is
        written if the base path does not already have an extension.
    organism_summary :
        Summary dict from ``organism.get_summary()``.
    """
    # Determine JSON and CSV paths
    out_path = Path(output_path)
    json_path = out_path.with_suffix(".json")
    csv_path = out_path.with_suffix(".csv")

    # --- JSON export ---
    record = {
        "metadata": {
            "export_time_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "n_steps": len(metrics),
            "pyNN_backend": _PYNN_BACKEND or "mock",
        },
        "summary": organism_summary,
        "steps": [m.to_dict() for m in metrics],
    }

    with open(json_path, "w") as fh:
        json.dump(record, fh, indent=2, default=float)

    logger.info("JSON results written to %s", json_path)

    # --- CSV export ---
    if metrics:
        fieldnames = list(metrics[0].to_dict().keys())
        with open(csv_path, "w", newline="") as fh:
            writer = csv.DictWriter(fh, fieldnames=fieldnames)
            writer.writeheader()
            for m in metrics:
                writer.writerow(m.to_dict())
        logger.info("CSV results written to %s", csv_path)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    """Build the argument parser for the CLI."""
    parser = argparse.ArgumentParser(
        description="Coral Reef Architecture on SpiNNaker",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Live SpiNNaker board
  python -m coral_reef_spinnaker.spinnaker_runner --spinnaker-ip 192.168.1.1

  # Local simulation with NEST
  python -m coral_reef_spinnaker.spinnaker_runner --steps 500

  # Load market data from CSV
  python -m coral_reef_spinnaker.spinnaker_runner \\
      --market-data data/eurusd_1m.csv --steps 10000

  # Custom config, verbose logging
  python -m coral_reef_spinnaker.spinnaker_runner \\
      --config config/reef_fast.json --log-interval 1 --steps 200
        """,
    )

    # Hardware
    parser.add_argument(
        "--spinnaker-ip",
        default=None,
        help="IP address of the SpiNNaker board (omit for simulator mode)",
    )

    # Simulation length
    parser.add_argument(
        "--steps",
        type=int,
        default=1000,
        help="Maximum number of simulation steps (default: 1000)",
    )

    # Configuration
    parser.add_argument(
        "--config",
        default=None,
        help="Path to a JSON config file (omit for defaults)",
    )

    # Output
    parser.add_argument(
        "--output",
        default="cra_results.json",
        help="Base path for result files (default: cra_results.json)",
    )

    # Logging
    parser.add_argument(
        "--log-interval",
        type=int,
        default=10,
        help="Print metrics every N steps (default: 10)",
    )

    # Checkpoints
    parser.add_argument(
        "--checkpoint-interval",
        type=int,
        default=None,
        help="Save checkpoint every N steps (default: disabled)",
    )
    parser.add_argument(
        "--checkpoint-dir",
        default="./checkpoints",
        help="Directory for checkpoint files (default: ./checkpoints)",
    )

    # Market data
    parser.add_argument(
        "--market-data",
        default=None,
        help="Path to CSV file with market data (omit for synthetic)",
    )
    parser.add_argument(
        "--market-seed",
        type=int,
        default=42,
        help="Random seed for synthetic market data (default: 42)",
    )

    # Verbosity
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable DEBUG-level logging",
    )

    return parser


def main(argv: Optional[list[str]] = None) -> int:
    """CLI entry point for CRA SpiNNaker simulation.

    Parameters
    ----------
    argv :
        Optional command-line arguments (defaults to ``sys.argv[1:]``).

    Returns
    -------
    int
        Exit code (0 = success).
    """
    parser = build_parser()
    args = parser.parse_args(argv)

    # Logging verbosity
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    logger.info("=" * 60)
    logger.info("Coral Reef Architecture -- SpiNNaker Execution Harness")
    logger.info("Backend: %s", _PYNN_BACKEND or "mock")
    logger.info("Steps: %d", args.steps)
    logger.info("=" * 60)

    # ------------------------------------------------------------------
    # 1. Load configuration
    # ------------------------------------------------------------------
    if args.config:
        config = ReefConfig.from_json(args.config)
        logger.info("Loaded config from %s", args.config)
    else:
        config = ReefConfig.default()
        logger.info("Using default configuration")

    # ------------------------------------------------------------------
    # 2. Setup simulator
    # ------------------------------------------------------------------
    simulator = setup_simulator(config, args.spinnaker_ip)

    # ------------------------------------------------------------------
    # 3. Create and initialise organism
    # ------------------------------------------------------------------
    organism = Organism(config, simulator)
    stream_keys = config.market_streams or ["EUR/USD", "GBP/USD", "USD/JPY"]
    organism.initialize(stream_keys)
    logger.info(
        "Organism initialised: %d streams, founder=%s",
        len(stream_keys),
        organism.founder_id,
    )

    # ------------------------------------------------------------------
    # 4. Load or generate market data
    # ------------------------------------------------------------------
    if args.market_data:
        market_data = load_market_data_from_csv(args.market_data)
    else:
        market_data = generate_synthetic_market_data(
            n_steps=args.steps,
            seed=args.market_seed,
        )
        logger.info(
            "Generated synthetic market data: %d steps (seed=%d)",
            len(market_data),
            args.market_seed,
        )

    # ------------------------------------------------------------------
    # 5. Run simulation
    # ------------------------------------------------------------------
    try:
        metrics = run_simulation(
            organism=organism,
            market_data_source=market_data,
            n_steps=args.steps,
            log_interval=args.log_interval,
            checkpoint_interval=args.checkpoint_interval,
            checkpoint_dir=args.checkpoint_dir,
        )
    except KeyboardInterrupt:
        logger.info("Simulation interrupted by user")
        metrics = organism.metrics_history
    except Exception as exc:
        logger.error("Simulation failed: %s", exc, exc_info=True)
        organism.shutdown()
        if _PYNN_BACKEND is not None:
            sim.end()
        return 1

    # ------------------------------------------------------------------
    # 6. Export results
    # ------------------------------------------------------------------
    summary = organism.get_summary()
    export_results(metrics, args.output, summary)

    # ------------------------------------------------------------------
    # 7. Cleanup
    # ------------------------------------------------------------------
    organism.shutdown()

    if _PYNN_BACKEND is None:
        MockSimulator.end()
    else:
        try:
            sim.end()
        except Exception as exc:
            logger.warning("sim.end() raised: %s", exc)

    logger.info("Clean shutdown complete")
    return 0


if __name__ == "__main__":
    sys.exit(main())

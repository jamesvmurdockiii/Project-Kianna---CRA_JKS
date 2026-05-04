"""
Coral Reef Architecture — SpiNNaker Demo
========================================

A complete demonstration of the CRA neuromorphic colony running on
(synthetic) market data.  This script exercises the full lifecycle of
an :class:`Organism` — from a single founder polyp through birth,
death, learning, and maternal handoff — on a directional-prediction
task.

What the demo does
------------------
1. **Creates a CRA organism** with :meth:`ReefConfig.default`.
2. **Generates synthetic directional returns** with occasional regime
   switches in drift, volatility, and autocorrelation.
3. **Evolves the colony** for *N* steps, printing live metrics.
4. **Saves results** as JSON and (optionally) renders 6-panel plots.

Can run with or without a real SpiNNaker board::

    # With SpiNNaker hardware:
    python demo.py --spinnaker-ip 192.168.1.1 --steps 500

    # With software simulation (default):
    python demo.py --steps 500

    # Quick smoke test:
    python demo.py --steps 50 --no-plots

    # Check which backends are available:
    python demo.py --check-deps

Exit codes
----------
- ``0`` — Simulation completed successfully.
- ``1`` — Import error, missing critical dependency, or unhandled exception.
- ``2`` — Colony went extinct before the scheduled number of steps.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import warnings
from collections import deque
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

# ---------------------------------------------------------------------------
# Import lightweight utilities from the package (these are defined directly
# in __init__.py and do not trigger any lazy backend imports).
# ---------------------------------------------------------------------------

try:
    from coral_reef_spinnaker import get_version, check_dependencies
except ImportError:
    _pkg_parent = Path(__file__).resolve().parent.parent
    sys.path.insert(0, str(_pkg_parent))
    from coral_reef_spinnaker import get_version, check_dependencies


def _import_organism_and_config():
    """Lazy-import Organism and ReefConfig (may pull in pyNN).

    This is called inside :func:`run_cra_demo` so that ``--check-deps``
    and ``--help`` work even when *organism.py* is not yet present.
    """
    from coral_reef_spinnaker import Organism, ReefConfig
    return Organism, ReefConfig


# ===========================================================================
# 1. Synthetic market data generation
# ===========================================================================


def generate_regime_switching_returns(
    n_steps: int,
    seed: int = 42,
    base_drift: float = 0.0,
    volatility: float = 0.01,
    regime_changes: int = 3,
) -> np.ndarray:
    """Generate synthetic 1-minute returns with regime changes.

    Creates a realistic market-like series with:

    - Base random walk with volatility ~1% per minute (crypto-like).
    - Occasional regime changes in drift and volatility.
    - Autocorrelated returns (momentum or mean-reversion regimes).

    Parameters
    ----------
    n_steps : int
        Number of 1-minute bars to generate.
    seed : int, optional
        Random seed for reproducibility, by default 42.
    base_drift : float, optional
        Base expected return per minute, by default 0.0.
    volatility : float, optional
        Base volatility per minute, by default 0.01 (1%).
    regime_changes : int, optional
        Number of regime switches to insert, by default 3.

    Returns
    -------
    np.ndarray
        Array of shape ``(n_steps,)`` with 1-minute returns.

    Examples
    --------
    >>> returns = generate_regime_switching_returns(100, seed=123)
    >>> returns.shape
    (100,)
    >>> np.std(returns) > 0  # noqa: SIM300
    True
    """
    rng = np.random.default_rng(seed)
    returns = np.zeros(n_steps, dtype=np.float64)

    # Regime boundaries — ensure first regime starts at 0 and last ends at n_steps.
    if regime_changes > 0:
        split_points = sorted(rng.integers(1, n_steps, size=regime_changes))
    else:
        split_points = []
    regime_starts = [0] + split_points + [n_steps]

    for i in range(len(regime_starts) - 1):
        start = int(regime_starts[i])
        end = int(regime_starts[i + 1])
        length = end - start
        if length <= 0:
            continue

        # Random regime parameters
        drift = base_drift + rng.normal(0.0, 0.001)
        vol = volatility * rng.uniform(0.5, 2.0)
        autocorr = rng.uniform(0.2, 0.5)  # momentum-only regimes for learnability

        # Generate autocorrelated returns via AR(1) process
        regime_returns = rng.normal(drift, vol, size=length)
        for t in range(1, length):
            regime_returns[t] += autocorr * regime_returns[t - 1]

        returns[start:end] = regime_returns

    return returns


# ===========================================================================
# 2. Core simulation loop
# ===========================================================================


def run_cra_demo(
    config: Any,  # ReefConfig — forward-ref to avoid eager import
    returns: np.ndarray,
    spinnaker_ip: Optional[str] = None,
    log_interval: int = 10,
    threads: int = 1,
    dt_seconds: float = 60.0,
) -> Dict[str, Any]:
    """Run a complete CRA demo simulation.

    Parameters
    ----------
    config : ReefConfig
        Fully populated CRA configuration object.
    returns : np.ndarray
        Array of 1-minute directional returns of shape ``(n_steps,)``.
    spinnaker_ip : str | None, optional
        IP address of a SpiNNaker board.  If *None*, a software backend
        (NEST, Brian2, or the pure-Python MockSimulator) is used.
    log_interval : int, optional
        Print metrics every *N* steps, by default 10.

    Returns
    -------
    dict
        Nested dictionary with full simulation results, including a
        ``"time_series"`` key containing per-step metrics.

    Raises
    ------
    RuntimeError
        If no suitable PyNN backend or mock simulator can be found.
    """
    # ------------------------------------------------------------------
    # Select PyNN backend ( SpiNNaker > NEST > Brian2 > Mock )
    # ------------------------------------------------------------------
    sim = None
    backend_name = "unknown"

    if spinnaker_ip is not None:
        try:
            import pyNN.spiNNaker as sim  # type: ignore[assignment]

            backend_name = f"sPyNNaker ({spinnaker_ip})"
        except Exception as exc:
            warnings.warn(
                f"Cannot import sPyNNaker for {spinnaker_ip}: {exc}. "
                "Falling back to next available backend."
            )

    if spinnaker_ip is not None and sim is None:
        # sPyNNaker selected above but failed to import — already warned
        pass

    if sim is None and spinnaker_ip is not None:
        # Hardware mode: try sPyNNaker auto-detect
        try:
            import pyNN.spiNNaker as sim  # type: ignore[assignment]
            backend_name = "sPyNNaker (auto)"
        except Exception:
            pass

    # Software mode (no hardware IP): prefer NEST > Brian2 > MockSimulator.
    # Skip sPyNNaker because it requires a board and would crash on setup().
    if sim is None and spinnaker_ip is None:
        try:
            import pyNN.nest as sim  # type: ignore[assignment]
            backend_name = "NEST"
        except Exception:
            pass

    if sim is None and spinnaker_ip is None:
        try:
            import pyNN.brian2 as sim  # type: ignore[assignment]
            backend_name = "Brian2"
        except Exception:
            pass

    if sim is None:
        try:
            from coral_reef_spinnaker.mock_simulator import MockSimulator as sim  # type: ignore[assignment]
            backend_name = "MockSimulator"
        except Exception as exc:
            raise RuntimeError(
                "No PyNN backend (sPyNNaker, NEST, Brian2) and no "
                f"MockSimulator available.  Cannot run demo.  Error: {exc}"
            ) from exc

    # ------------------------------------------------------------------
    # Setup simulator timestep
    # ------------------------------------------------------------------
    timestep: float = getattr(config, "spinnaker", getattr(config, "timestep_ms", 1.0))
    if hasattr(timestep, "timestep_ms"):
        timestep = timestep.timestep_ms  # type: ignore[union-attr]
    elif isinstance(timestep, (int, float)):
        pass
    else:
        timestep = 1.0  # safe default

    # ------------------------------------------------------------------
    # Setup simulator with graceful fallback
    # ------------------------------------------------------------------
    setup_kwargs: Dict[str, Any] = {"timestep": timestep}
    if backend_name == "NEST" and threads > 1:
        setup_kwargs["threads"] = threads
        print(f"  NEST threads    : {threads}")

    try:
        sim.setup(**setup_kwargs)
    except Exception as exc:
        warnings.warn(f"{backend_name} setup() failed: {exc}. Falling back to MockSimulator.")
        from coral_reef_spinnaker.mock_simulator import MockSimulator as sim  # type: ignore[assignment]
        backend_name = "MockSimulator (fallback)"
        sim.setup(timestep=timestep)

    # ------------------------------------------------------------------
    # Lazy-import Organism (avoids eager import at module load time)
    # ------------------------------------------------------------------
    Organism, _ = _import_organism_and_config()

    # ------------------------------------------------------------------
    # Create organism and initialise
    # ------------------------------------------------------------------
    # Software backends (NEST, Brian2, Mock) don't need hardware projection
    # rebuilds every step. Set sync interval to 0 for fast simulation.
    # Hardware backends (sPyNNaker) sync every step by default.
    if backend_name in ("NEST", "Brian2", "MockSimulator", "MockSimulator (pure Python)", "MockSimulator (fallback)"):
        # Sync every 10 steps so that structural changes (births, edge
        # additions) are pushed to NEST.  Dopamine is delivered every
        # step via ReefNetwork.deliver_dopamine, so this is only for
        # topology changes.
        config.spinnaker.sync_interval_steps = 10
        # Shrink the population cap for software backends — allocating
        # 8192 neurons (256 polyps * 32) makes get_data() very slow on
        # NEST even when only a few polyps are alive.
        config.lifecycle.max_population_hard = 16

    organism = Organism(config, sim)
    stream_keys: List[str] = ["SYNTHETIC_1"]
    organism.initialize(stream_keys)

    # ------------------------------------------------------------------
    # Run simulation loop
    # ------------------------------------------------------------------
    metrics_history: List[Any] = []
    n_steps = int(len(returns))

    print(f"\n{'=' * 70}")
    print(f"  Coral Reef Architecture v{get_version()} — Demo")
    print(f"{'=' * 70}")
    print(f"  Steps           : {n_steps}")
    print(f"  Backend         : {backend_name}")
    print(f"  Initial polyp   : 1 (founder)")
    print(f"  Timestep        : {timestep} ms")
    print(f"  Sim time/step   : {dt_seconds}s")
    print(f"{'=' * 70}\n")

    start_time = time.time()
    extinction_step: Optional[int] = None

    for step in range(n_steps):
        market_return = float(returns[step])

        try:
            metrics = organism.train_step(market_return, dt_seconds=dt_seconds)
        except Exception as exc:
            warnings.warn(f"train_step failed at step {step}: {exc}")
            break

        metrics_history.append(metrics)

        # ---- Live logging ------------------------------------------------
        if step % log_interval == 0 or step == n_steps - 1:
            _print_step_metrics(step, metrics)

        # ---- Extinction check --------------------------------------------
        alive: int = getattr(metrics, "n_alive", 0)
        if alive == 0:
            extinction_step = step
            print(f"\n  *** EXTINCTION at step {step} ***")
            break

    elapsed = time.time() - start_time

    # ------------------------------------------------------------------
    # Footer
    # ------------------------------------------------------------------
    final_pop = metrics_history[-1].n_alive if metrics_history else 0
    final_cap = metrics_history[-1].capital if metrics_history else 0.0
    final_acc = metrics_history[-1].mean_directional_accuracy_ema if metrics_history else 0.0

    print(f"\n{'=' * 70}")
    print(f"  Simulation complete")
    print(f"  Wall-clock time : {elapsed:.1f} s")
    if elapsed > 0:
        print(f"  Throughput      : {len(metrics_history) / elapsed:.1f} steps/s")
    print(f"  Steps completed : {len(metrics_history)} / {n_steps}")
    print(f"  Extinction      : {'yes (step ' + str(extinction_step) + ')' if extinction_step is not None else 'no'}")
    print(f"  Final population: {final_pop}")
    print(f"  Final capital   : {final_cap:.4f}")
    print(f"  Final accuracy  : {final_acc:.3f}")
    print(f"{'=' * 70}")

    # ------------------------------------------------------------------
    # Assemble serialisable results
    # ------------------------------------------------------------------
    results: Dict[str, Any] = {
        "version": get_version(),
        "backend": backend_name,
        "config": _config_to_dict(config),
        "n_steps_scheduled": n_steps,
        "n_steps_completed": len(metrics_history),
        "extinction_step": extinction_step,
        "total_time_seconds": round(elapsed, 3),
        "final_state": {
            "population": final_pop,
            "capital": round(final_cap, 6),
            "accuracy": round(final_acc, 6),
        },
        "time_series": [_metrics_to_dict(m) for m in metrics_history],
    }

    # ------------------------------------------------------------------
    # Graceful shutdown
    # ------------------------------------------------------------------
    try:
        organism.shutdown()
    except Exception as exc:
        warnings.warn(f"organism.shutdown() raised: {exc}")

    try:
        sim.end()
    except Exception as exc:
        warnings.warn(f"sim.end() raised: {exc}")

    return results


def _print_step_metrics(step: int, m: Any) -> None:
    """Pretty-print a single step's metrics to stdout."""
    # Helper to safely read attributes with fallbacks.
    def _get(obj: Any, attr: str, default: Any = 0) -> Any:
        return getattr(obj, attr, default)

    n_juv = _get(m, "n_juvenile", 0)
    n_adt = _get(m, "n_adult", 0)
    j_marker = "J" if n_juv > 0 else " "
    a_marker = "A" if n_adt > 0 else " "

    line = (
        f"  Step {step:4d} | "
        f"Pop: {_get(m, 'n_alive'):3d} "
        f"({j_marker}{n_juv:2d}/{a_marker}{n_adt:2d}) | "
        f"Cap: {_get(m, 'capital'):8.4f} | "
        f"Acc: {_get(m, 'mean_directional_accuracy_ema'):.3f} | "
        f"Troph: {_get(m, 'mean_trophic_health'):.3f} | "
        f"Pred: {_get(m, 'colony_prediction'):+.4f} | "
        f"DA: {_get(m, 'raw_dopamine'):+.4f}"
    )
    print(line)


def _metrics_to_dict(m: Any) -> Dict[str, Any]:
    """Convert a metrics object / namedtuple into a plain dict for JSON."""
    fields = [
        "step",
        "n_alive",
        "n_juvenile",
        "n_adult",
        "births_this_step",
        "deaths_this_step",
        "capital",
        "mean_trophic_health",
        "mean_directional_accuracy_ema",
        "colony_prediction",
        "raw_dopamine",
        "task_signal",
        "actual_return_5m",
        "direction_correct",
        "sharpe_ratio",
        "n_edges",
        "n_ff",
        "n_lat",
        "n_fb",
        "handoff_complete",
        "I_union_bits",
        "changepoint_probability",
    ]
    return {f: _safe_json(getattr(m, f, None)) for f in fields}


def _safe_json(value: Any) -> Any:
    """Coerce numpy scalars / arrays to Python native types for JSON."""
    if value is None:
        return None
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, np.ndarray):
        return value.tolist()
    return value


def _config_to_dict(config: ReefConfig) -> Dict[str, Any]:
    """Best-effort serialisation of a ReefConfig dataclass to dict."""
    try:
        # dataclasses with nested dataclasses
        import dataclasses

        if dataclasses.is_dataclass(config):
            return dataclasses.asdict(config)
    except Exception:
        pass
    # Fallback: grab all public attributes that look like config fields.
    result: Dict[str, Any] = {}
    for key in dir(config):
        if key.startswith("_"):
            continue
        val = getattr(config, key)
        if callable(val):
            continue
        result[key] = _safe_json(val)
    return result


# ===========================================================================
# 3. Visualization
# ===========================================================================


def create_plots(results: Dict[str, Any], output_dir: Path) -> None:
    """Create six-panel visualisation from simulation results.

    Generates a single figure with the following subplots::

        (0,0) Colony population dynamics (total / juvenile / adult)
        (0,1) Capital trajectory with break-even line
        (1,0) Directional accuracy learning curve
        (1,1) Mean trophic health over time
        (2,0) Network motif evolution (FF / LAT / FB edge counts)
        (2,1) Dopamine + prediction overlay (dual y-axis)

    Parameters
    ----------
    results : dict
        Dictionary returned by :func:`run_cra_demo`.
    output_dir : Path
        Directory where ``cra_demo_results.png`` is written.
    """
    try:
        import matplotlib

        matplotlib.use("Agg")  # non-interactive backend
        import matplotlib.pyplot as plt
    except ImportError:
        print("  [plot] matplotlib not available — skipping visualisations.")
        return

    ts: List[Dict[str, Any]] = results.get("time_series", [])
    if not ts:
        print("  [plot] No time-series data — skipping visualisations.")
        return

    steps = [t["step"] for t in ts]

    fig, axes = plt.subplots(3, 2, figsize=(14, 12))
    fig.suptitle(
        f"Coral Reef Architecture v{results.get('version', '?')}\n"
        f"{results.get('n_steps_completed', 0)} steps  |  "
        f"Backend: {results.get('backend', '?')}  |  "
        f"Final capital: {results.get('final_state', {}).get('capital', 0):.4f}",
        fontsize=11,
    )

    # -- (0,0) Population dynamics --------------------------------------
    ax = axes[0, 0]
    ax.plot(steps, [t["n_alive"] for t in ts], "b-", label="Total", linewidth=1.2)
    ax.plot(
        steps, [t["n_juvenile"] for t in ts], "g--", label="Juvenile", alpha=0.7, linewidth=1
    )
    ax.plot(
        steps, [t["n_adult"] for t in ts], "r--", label="Adult", alpha=0.7, linewidth=1
    )
    ax.set_ylabel("Population")
    ax.set_title("Colony Population Dynamics")
    ax.legend(loc="upper left", fontsize=8)
    ax.grid(True, alpha=0.3)

    # -- (0,1) Capital trajectory ---------------------------------------
    ax = axes[0, 1]
    capital = [t["capital"] for t in ts]
    ax.plot(steps, capital, color="purple", linewidth=1.2)
    ax.axhline(y=1.0, color="k", linestyle="--", alpha=0.3, label="Break-even")
    ax.set_ylabel("Capital")
    ax.set_title("Capital Trajectory")
    ax.legend(loc="upper left", fontsize=8)
    ax.grid(True, alpha=0.3)

    # -- (1,0) Accuracy -------------------------------------------------
    ax = axes[1, 0]
    acc = [t["mean_directional_accuracy_ema"] for t in ts]
    ax.plot(steps, acc, color="green", linewidth=1.2)
    ax.axhline(y=0.5, color="k", linestyle="--", alpha=0.3, label="Random (0.5)")
    ax.set_ylabel("Directional Accuracy")
    ax.set_title("Learning Progress (5-minute Directional)")
    ax.set_ylim(-0.05, 1.05)
    ax.legend(loc="lower right", fontsize=8)
    ax.grid(True, alpha=0.3)

    # -- (1,1) Trophic health -------------------------------------------
    ax = axes[1, 1]
    ax.plot(steps, [t["mean_trophic_health"] for t in ts], color="orange", linewidth=1.2)
    ax.set_ylabel("Mean Trophic Health")
    ax.set_title("Energy Economy Health")
    ax.grid(True, alpha=0.3)

    # -- (2,0) Network motifs -------------------------------------------
    ax = axes[2, 0]
    ax.plot(steps, [t["n_ff"] for t in ts], "b-", label="FF", alpha=0.7, linewidth=1)
    ax.plot(steps, [t["n_lat"] for t in ts], "g-", label="LAT", alpha=0.7, linewidth=1)
    ax.plot(steps, [t["n_fb"] for t in ts], "r-", label="FB", alpha=0.7, linewidth=1)
    ax.set_ylabel("Edge Count")
    ax.set_xlabel("Step")
    ax.set_title("Network Motif Evolution")
    ax.legend(loc="upper left", fontsize=8)
    ax.grid(True, alpha=0.3)

    # -- (2,1) Dopamine + prediction (dual axis) -----------------------
    ax = axes[2, 1]
    ax_twin = ax.twinx()
    (l1,) = ax.plot(
        steps, [t["raw_dopamine"] for t in ts], color="red", alpha=0.6, linewidth=1, label="Dopamine"
    )
    (l2,) = ax_twin.plot(
        steps,
        [t["colony_prediction"] for t in ts],
        color="blue",
        alpha=0.6,
        linewidth=1,
        label="Prediction",
    )
    ax.set_ylabel("Dopamine", color="red")
    ax_twin.set_ylabel("Prediction", color="blue")
    ax.set_xlabel("Step")
    ax.set_title("Neuromodulation & Readout")
    ax.legend([l1, l2], ["Dopamine", "Prediction"], loc="upper left", fontsize=8)
    ax.grid(True, alpha=0.3)

    plt.tight_layout(rect=[0, 0, 1, 0.96])
    output_path = output_dir / "cra_demo_results.png"
    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    print(f"\n  Plot saved to: {output_path}")
    plt.close(fig)


# ===========================================================================
# 4. CLI entry point
# ===========================================================================


def _build_arg_parser() -> argparse.ArgumentParser:
    """Construct and return the argument parser for ``demo.py``."""
    parser = argparse.ArgumentParser(
        description="Coral Reef Architecture — SpiNNaker Demo",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Quick smoke test (50 steps, no plots):
  python demo.py --steps 50 --no-plots

  # Full demo with visualisation (500 steps):
  python demo.py --steps 500

  # With SpiNNaker hardware:
  python demo.py --spinnaker-ip 192.168.1.1 --steps 1000

  # Speed up NEST with multi-threading + shorter dt:
  python demo.py --steps 500 --threads 4 --dt 5.0

  # Custom regime changes:
  python demo.py --steps 500 --regimes 5 --volatility 0.02

  # Dependency check only:
  python demo.py --check-deps
        """,
    )
    parser.add_argument(
        "--steps",
        type=int,
        default=200,
        help="Number of simulation steps (default: 200)",
    )
    parser.add_argument(
        "--spinnaker-ip",
        default=None,
        help="SpiNNaker board IP address (default: software simulation)",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for market data generation (default: 42)",
    )
    parser.add_argument(
        "--volatility",
        type=float,
        default=0.01,
        help="Base volatility per minute, e.g. 0.01 = 1%% (default: 0.01)",
    )
    parser.add_argument(
        "--regimes",
        type=int,
        default=2,
        help="Number of regime changes to inject (default: 2)",
    )
    parser.add_argument(
        "--log-interval",
        type=int,
        default=10,
        help="Print metrics every N steps (default: 10)",
    )
    parser.add_argument(
        "--threads",
        type=int,
        default=1,
        help="NEST OpenMP threads (default: 1). 4 is usually optimal.",
    )
    parser.add_argument(
        "--dt",
        type=float,
        default=60.0,
        help="Biological simulation time per market step in seconds (default: 60.0). "
             "Lower = faster but less neural activity per step.",
    )
    parser.add_argument(
        "--no-plots",
        action="store_true",
        help="Skip plot generation",
    )
    parser.add_argument(
        "--output-dir",
        default="cra_demo_output",
        help="Output directory for results (default: cra_demo_output)",
    )
    parser.add_argument(
        "--check-deps",
        action="store_true",
        help="Check dependencies and exit",
    )
    parser.add_argument(
        "--data",
        default=None,
        help="Path to audit.csv.gz with real returns (default: generate synthetic)",
    )
    parser.add_argument(
        "--pair",
        default="XBT/USD",
        help="Which pair to run from real data (default: XBT/USD)",
    )
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    """CLI entry point for the CRA demo.

    Parameters
    ----------
    argv : list[str] | None
        Optional argument list (used by tests).  If *None*, ``sys.argv``
        is used.

    Returns
    -------
    int
        Process exit code (0 = success, 1 = error, 2 = extinction).
    """
    parser = _build_arg_parser()
    args = parser.parse_args(argv)

    # ------------------------------------------------------------------
    # --check-deps fast path
    # ------------------------------------------------------------------
    if args.check_deps:
        deps = check_dependencies()
        print("\nDependency Check:")
        for name, available in sorted(deps.items()):
            status = "YES" if available else "NO"
            print(f"  [{status:3s}] {name}")
        # Recommend best backend
        if deps.get("spiNNaker"):
            print("\n  -> Preferred backend: sPyNNaker (SpiNNaker hardware)")
        elif deps.get("nest"):
            print("\n  -> Preferred backend: NEST")
        elif deps.get("brian2"):
            print("\n  -> Preferred backend: Brian2")
        else:
            print("\n  -> Fallback: MockSimulator (pure Python)")
        return 0

    # ------------------------------------------------------------------
    # Configuration (lazy import — may not be available in skeleton builds)
    # ------------------------------------------------------------------
    try:
        Organism, ReefConfig = _import_organism_and_config()
        config = ReefConfig.default()
        # Lower metabolic decay for demo so founder survives long runs
        config.energy.metabolic_decay_default = 0.00005
    except Exception as exc:
        print(f"ERROR: Cannot create default ReefConfig: {exc}", file=sys.stderr)
        return 1

    # ------------------------------------------------------------------
    # Load real or generate synthetic market data
    # ------------------------------------------------------------------
    if args.data:
        import gzip
        import pandas as pd
        print(f"\nLoading real data from {args.data} ...")
        df = pd.read_csv(args.data)
        df = df[df["pair"] == args.pair].reset_index(drop=True)
        returns = df["actual_return"].values[:args.steps]
        print(f"  Pair           : {args.pair}")
        print(f"  Steps loaded   : {len(returns)}")
        print(f"  Return range   : [{returns.min():+.4f}, {returns.max():+.4f}]")
        print(f"  Return std     : {returns.std():.4f}")
    else:
        print(f"\nGenerating synthetic market data ...")
        print(f"  Steps          : {args.steps}")
        print(f"  Volatility     : {args.volatility:.2%} / minute")
        print(f"  Regime changes : {args.regimes}")
        print(f"  Seed           : {args.seed}")

        returns = generate_regime_switching_returns(
            n_steps=args.steps,
            seed=args.seed,
            volatility=args.volatility,
            regime_changes=args.regimes,
        )
        print(f"  Return range   : [{returns.min():+.4f}, {returns.max():+.4f}]")
        print(f"  Return std     : {returns.std():.4f}")

    # ------------------------------------------------------------------
    # Run simulation
    # ------------------------------------------------------------------
    try:
        results = run_cra_demo(
            config=config,
            returns=returns,
            spinnaker_ip=args.spinnaker_ip,
            log_interval=args.log_interval,
            threads=args.threads,
            dt_seconds=args.dt,
        )
    except Exception as exc:
        print(f"\nERROR: Simulation failed: {exc}", file=sys.stderr)
        import traceback

        traceback.print_exc()
        return 1

    # ------------------------------------------------------------------
    # Save JSON results
    # ------------------------------------------------------------------
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    results_path = output_dir / "cra_demo_results.json"
    with open(results_path, "w", encoding="utf-8") as fh:
        json.dump(results, fh, indent=2, default=str)
    print(f"\n  Results saved to: {results_path}")

    # ------------------------------------------------------------------
    # Plots
    # ------------------------------------------------------------------
    if not args.no_plots:
        create_plots(results, output_dir)

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------
    final = results.get("final_state", {})
    print(f"\n{'=' * 70}")
    print(f"  SUMMARY")
    print(f"{'=' * 70}")
    print(f"  Steps completed : {results['n_steps_completed']}")
    print(f"  Final population: {final.get('population', 0)}")
    print(f"  Final capital   : {final.get('capital', 0):.4f}")
    print(f"  Final accuracy  : {final.get('accuracy', 0):.3f}")
    print(f"  Wall-clock time : {results['total_time_seconds']:.1f} s")
    print(f"  Output directory: {output_dir.resolve()}")
    print(f"{'=' * 70}")

    # Exit code 2 signals extinction (useful for CI / batch tests).
    if results.get("extinction_step") is not None:
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())

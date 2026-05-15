"""Repository-governance checks for research-grade claim hygiene.

These tests intentionally cover project invariants that ordinary unit tests do
not catch: experimental mechanisms must be opt-in, diagnostic baselines must not
overstate predictive claims, and known duplicate/overwritten code paths must not
creep back in.
"""

from pathlib import Path
from types import SimpleNamespace

import numpy as np

from coral_reef_spinnaker.config import LifecycleConfig


REPO_ROOT = Path(__file__).resolve().parents[2]


def test_unpromoted_lifecycle_mechanisms_default_off():
    cfg = LifecycleConfig()
    experimental_flags = [
        "enable_neural_heritability",
        "enable_stream_specialization",
        "enable_variable_allocation",
        "enable_task_fitness_selection",
        "enable_operator_diversity",
        "enable_synaptic_heritability",
        "enable_niche_pressure",
        "enable_signal_transport",
        "enable_energy_economy",
        "enable_maturation",
        "enable_vector_readout",
        "enable_alignment_pressure",
        "enable_task_coupled_selection",
        "enable_causal_credit_selection",
        "enable_cross_polyp_coupling",
    ]
    enabled = [name for name in experimental_flags if getattr(cfg, name)]
    assert enabled == []


def test_no_duplicate_lifecycle_operator_diversity_field():
    source = (REPO_ROOT / "coral_reef_spinnaker" / "config.py").read_text()
    assert source.count("enable_operator_diversity: bool") == 1


def test_vector_readout_update_method_not_overwritten():
    source = (REPO_ROOT / "coral_reef_spinnaker" / "organism.py").read_text()
    assert source.count("def _update_readout_lms") == 1
    assert "_vh_caste_credit" in source
    assert "_sv_last_pred" not in source


def test_operator_diversity_inhibitory_scaling_uses_inhibitory_slice():
    source = (REPO_ROOT / "coral_reef_spinnaker" / "polyp_population.py").read_text()
    assert "local_pre = pre - inh_idx(0)" in source
    assert "0 <= local_pre < n_ih" in source


def test_v27_is_diagnostic_not_predictive_supersession():
    baseline = (REPO_ROOT / "baselines" / "CRA_EVIDENCE_BASELINE_v2.7.md").read_text()
    assert "does not supersede v2.6" in baseline
    assert "diagnostic" in baseline.lower()
    assert "not a predictive-performance promotion" in baseline


def test_tier5_45a_adapter_dt_uses_runtime_ms_per_step(monkeypatch):
    """The healthy-NEST gate must not silently ignore its runtime cadence knob."""

    import experiments.tier5_45a_healthy_nest_rebaseline_scoring as gate

    captured_dt: list[float] = []

    class FakeMetrics:
        colony_prediction = 0.0
        n_alive = 1
        births_this_step = 0
        deaths_this_step = 0

        def to_dict(self):
            return {"fake": True}

    class FakeOrganism:
        def __init__(self, *args, **kwargs):
            pass

        def initialize(self, stream_keys):
            assert stream_keys == ["sine"]

        def train_adapter_step(self, adapter, observation, dt_seconds):
            captured_dt.append(float(dt_seconds))
            return FakeMetrics()

        def get_per_neuron_spike_vector(self):
            return [1, 0, 1]

        def backend_diagnostics(self):
            return {
                "backend": "fake_nest",
                "synthetic_fallbacks": 0,
                "sim_run_failures": 0,
                "summary_read_failures": 0,
            }

        def shutdown(self):
            pass

    monkeypatch.setattr(gate, "Organism", FakeOrganism)
    monkeypatch.setattr(gate, "load_backend", lambda backend: (object(), backend))
    monkeypatch.setattr(gate, "setup_backend", lambda sim, backend_name: None)
    monkeypatch.setattr(gate, "end_backend", lambda sim: None)

    observed = np.linspace(0.0, 1.0, 16, dtype=float)
    task = gate.SequenceTask(
        name="sine",
        display_name="sine",
        observed=observed,
        target=observed.copy(),
        train_end=8,
        horizon=1,
        metadata={},
    )
    args = SimpleNamespace(
        backend="nest",
        initial_population=1,
        max_population=1,
        enable_lifecycle=False,
        steps=16,
        readout_lr=0.2,
        delayed_readout_lr=0.2,
        horizon=1,
        sync_interval_steps=0,
        runtime_ms_per_step=25.0,
    )

    row = gate.score_organism_condition(task, "organism_defaults_experimental_off", 42, args)

    assert row["status"] == "pass"
    assert captured_dt == [0.025] * 16

"""Repository-governance checks for research-grade claim hygiene.

These tests intentionally cover project invariants that ordinary unit tests do
not catch: experimental mechanisms must be opt-in, diagnostic baselines must not
overstate predictive claims, and known duplicate/overwritten code paths must not
creep back in.
"""

from pathlib import Path

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

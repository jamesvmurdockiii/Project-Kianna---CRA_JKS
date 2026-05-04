#!/usr/bin/env python3
"""Build and validate the CRA controlled-study evidence registry.

This script is intentionally separate from the experiment runners. The runners
produce raw evidence bundles; this registry decides which bundles are canonical
study evidence, checks that their expected artifacts exist, repairs the
`*_latest_manifest.json` convenience pointers, and writes a human-readable
study index.
"""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = ROOT / "controlled_test_output"


@dataclass(frozen=True)
class EvidenceSpec:
    entry_id: str
    tier_label: str
    plan_position: str
    canonical_dir: str
    results_file: str
    report_file: str
    summary_file: str | None
    harness: str
    evidence_role: str
    claim: str
    caveat: str
    latest_manifest_names: tuple[str, ...]
    expected_extra_files: tuple[str, ...] = ()


SPECS: tuple[EvidenceSpec, ...] = (
    EvidenceSpec(
        entry_id="tier1_sanity",
        tier_label="Tier 1 - sanity tests",
        plan_position="Core tests 1-3",
        canonical_dir="tier1_20260426_155758",
        results_file="tier1_results.json",
        report_file="tier1_report.md",
        summary_file="tier1_summary.csv",
        harness="experiments/tier1_sanity.py",
        evidence_role="negative controls",
        claim="No usable signal and shuffled labels do not produce false learning.",
        caveat="Passing Tier 1 rules out obvious fake learning; it does not prove positive learning.",
        latest_manifest_names=("tier1_latest_manifest.json",),
        expected_extra_files=(
            "zero_signal_timeseries.csv",
            "zero_signal_timeseries.png",
            "shuffled_label_timeseries.csv",
            "shuffled_label_timeseries.png",
            "seed_repeat_summary.csv",
            "seed_repeat_summary.png",
        ),
    ),
    EvidenceSpec(
        entry_id="tier2_learning",
        tier_label="Tier 2 - learning proof tests",
        plan_position="Core tests 4-6",
        canonical_dir="tier2_20260426_155821",
        results_file="tier2_results.json",
        report_file="tier2_report.md",
        summary_file="tier2_summary.csv",
        harness="experiments/tier2_learning.py",
        evidence_role="positive learning controls",
        claim="Fixed pattern, delayed reward, and nonstationary switch tasks learn above threshold.",
        caveat="Positive-control learning evidence depends on the controlled synthetic task definitions.",
        latest_manifest_names=("tier2_latest_manifest.json",),
        expected_extra_files=(
            "fixed_pattern_timeseries.csv",
            "fixed_pattern_timeseries.png",
            "delayed_reward_timeseries.csv",
            "delayed_reward_timeseries.png",
            "nonstationary_switch_timeseries.csv",
            "nonstationary_switch_timeseries.png",
        ),
    ),
    EvidenceSpec(
        entry_id="tier3_architecture",
        tier_label="Tier 3 - architecture ablation tests",
        plan_position="Core tests 7-9",
        canonical_dir="tier3_20260426_155852",
        results_file="tier3_results.json",
        report_file="tier3_report.md",
        summary_file="tier3_summary.csv",
        harness="experiments/tier3_ablation.py",
        evidence_role="mechanism ablations",
        claim="Dopamine, plasticity, and trophic selection each contribute measurable value.",
        caveat="Ablation claims are scoped to the controlled tasks and seeds in this bundle.",
        latest_manifest_names=("tier3_latest_manifest.json",),
        expected_extra_files=(
            "no_dopamine_ablation_comparison.png",
            "no_plasticity_ablation_comparison.png",
            "no_trophic_selection_ablation_comparison.png",
        ),
    ),
    EvidenceSpec(
        entry_id="tier4_10_population_scaling",
        tier_label="Tier 4.10 - population scaling",
        plan_position="Core test 10",
        canonical_dir="tier4_20260426_155103",
        results_file="tier4_results.json",
        report_file="tier4_report.md",
        summary_file="tier4_summary.csv",
        harness="experiments/tier4_scaling.py",
        evidence_role="baseline scaling",
        claim="Fixed populations from N=4 to N=64 remain stable on the switch stressor.",
        caveat="This baseline scaling task saturated; the honest claim is stability, not strong scaling advantage.",
        latest_manifest_names=("tier4_latest_manifest.json", "tier4_10_latest_manifest.json"),
        expected_extra_files=(
            "population_scaling_summary.png",
            "population_scaling_timeseries.png",
        ),
    ),
    EvidenceSpec(
        entry_id="tier4_10b_hard_population_scaling",
        tier_label="Tier 4.10b - hard population scaling",
        plan_position="Addendum after core test 10",
        canonical_dir="tier4_10b_20260426_161251",
        results_file="tier4_10b_results.json",
        report_file="tier4_10b_report.md",
        summary_file="tier4_10b_summary.csv",
        harness="experiments/tier4_hard_scaling.py",
        evidence_role="hard scaling stressor",
        claim="Hard scaling remains stable and shows value through correlation/recovery/variance rather than raw accuracy.",
        caveat="Hard-scaling accuracy is near baseline; the pass is based on stability plus non-accuracy scaling signals.",
        latest_manifest_names=("tier4_10b_latest_manifest.json",),
        expected_extra_files=(
            "hard_population_scaling_summary.png",
            "hard_population_scaling_timeseries.png",
        ),
    ),
    EvidenceSpec(
        entry_id="tier4_11_domain_transfer",
        tier_label="Tier 4.11 - domain transfer",
        plan_position="Core test 11",
        canonical_dir="tier4_11_20260426_164655",
        results_file="tier4_11_results.json",
        report_file="tier4_11_report.md",
        summary_file="tier4_11_summary.csv",
        harness="experiments/tier4_domain_transfer.py",
        evidence_role="domain transfer",
        claim="The same CRA core transfers from finance/signed-return to non-finance sensor_control.",
        caveat="Domain transfer is proven for the controlled adapters here, not arbitrary domains.",
        latest_manifest_names=("tier4_11_latest_manifest.json",),
        expected_extra_files=("domain_transfer_summary.png",),
    ),
    EvidenceSpec(
        entry_id="tier4_12_backend_parity",
        tier_label="Tier 4.12 - backend parity",
        plan_position="Core test 12",
        canonical_dir="tier4_12_20260426_170808",
        results_file="tier4_12_results.json",
        report_file="tier4_12_report.md",
        summary_file="tier4_12_summary.csv",
        harness="experiments/tier4_backend_parity.py",
        evidence_role="backend parity",
        claim="The fixed-pattern result survives NEST to Brian2 movement with zero synthetic fallback.",
        caveat="The SpiNNaker item in Tier 4.12 is readiness prep, not a hardware learning result.",
        latest_manifest_names=("tier4_12_latest_manifest.json",),
        expected_extra_files=("backend_parity_summary.png",),
    ),
    EvidenceSpec(
        entry_id="tier4_13_spinnaker_hardware_capsule",
        tier_label="Tier 4.13 - SpiNNaker Hardware Capsule",
        plan_position="Hardware addendum after core test 12",
        canonical_dir="tier4_13_20260427_011912_hardware_pass",
        results_file="tier4_13_results.json",
        report_file="tier4_13_report.md",
        summary_file="tier4_13_summary.csv",
        harness="experiments/tier4_spinnaker_hardware_capsule.py",
        evidence_role="hardware capsule",
        claim="The minimal fixed-pattern CRA capsule executes through pyNN.spiNNaker with real spike readback and passes learning thresholds.",
        caveat="Single-seed N=8 fixed-pattern capsule; not full hardware scaling or full CRA hardware deployment.",
        latest_manifest_names=("tier4_13_latest_manifest.json",),
        expected_extra_files=(
            "study_data.json",
            "DOWNLOAD_INTAKE_MANIFEST.json",
            "remote_tier4_13_latest_manifest.json",
            "hardware_capsule_summary.png",
            "spinnaker_hardware_seed42_timeseries.csv",
            "spinnaker_hardware_seed42_timeseries.png",
            "spinnaker_reports/2026-04-27-01-19-12-390038/finished",
            "spinnaker_reports/2026-04-27-01-19-12-390038/global_provenance.sqlite3",
            "raw_reports/spinnaker_reports_2026-04-27-01-19-12-390038.zip",
        ),
    ),
    EvidenceSpec(
        entry_id="tier4_14_hardware_runtime_characterization",
        tier_label="Tier 4.14 - Hardware Runtime Characterization",
        plan_position="Post-v0.1 hardware addendum after Tier 4.13",
        canonical_dir="tier4_14_20260426_213430",
        results_file="tier4_14_results.json",
        report_file="tier4_14_report.md",
        summary_file="tier4_14_summary.csv",
        harness="experiments/tier4_hardware_runtime_characterization.py",
        evidence_role="hardware runtime profile",
        claim="The Tier 4.13 hardware pass has profiled wall-clock and sPyNNaker provenance costs; overhead is dominated by repeated per-step run/readback orchestration.",
        caveat="Derived from the single-seed N=8 Tier 4.13 hardware pass unless rerun in run-hardware mode; not hardware repeatability or scaling evidence.",
        latest_manifest_names=("tier4_14_latest_manifest.json",),
        expected_extra_files=(
            "tier4_14_category_timers.csv",
            "tier4_14_top_algorithms.csv",
            "tier4_14_runtime_breakdown.csv",
            "tier4_14_runtime_breakdown.png",
        ),
    ),
    EvidenceSpec(
        entry_id="tier4_15_spinnaker_hardware_multiseed_repeat",
        tier_label="Tier 4.15 - SpiNNaker Hardware Multi-Seed Repeat",
        plan_position="Hardware repeatability addendum after Tier 4.14",
        canonical_dir="tier4_15_20260427_030501_hardware_pass",
        results_file="tier4_15_results.json",
        report_file="tier4_15_report.md",
        summary_file="tier4_15_summary.csv",
        harness="experiments/tier4_spinnaker_hardware_repeat.py",
        evidence_role="hardware repeatability",
        claim="The minimal fixed-pattern CRA hardware capsule repeats across seeds 42, 43, and 44 with zero fallback/failures and consistent learning metrics.",
        caveat="Three-seed N=8 fixed-pattern capsule only; not a harder hardware task, hardware population scaling, or full CRA hardware deployment.",
        latest_manifest_names=("tier4_15_latest_manifest.json",),
        expected_extra_files=(
            "README.md",
            "study_data.json",
            "DOWNLOAD_INTAKE_MANIFEST.json",
            "remote_tier4_15_latest_manifest.json",
            "tier4_15_seed_summary.csv",
            "tier4_15_multi_seed_summary.png",
            "spinnaker_hardware_seed42_timeseries.csv",
            "spinnaker_hardware_seed42_timeseries.png",
            "spinnaker_hardware_seed43_timeseries.csv",
            "spinnaker_hardware_seed43_timeseries.png",
            "spinnaker_hardware_seed44_timeseries.csv",
            "spinnaker_hardware_seed44_timeseries.png",
            "spinnaker_reports/2026-04-27-03-05-01-872105/finished",
            "spinnaker_reports/2026-04-27-03-05-01-872105/global_provenance.sqlite3",
            "spinnaker_reports/2026-04-27-03-19-49-290162/finished",
            "spinnaker_reports/2026-04-27-03-19-49-290162/global_provenance.sqlite3",
            "spinnaker_reports/2026-04-27-03-34-22-032643/finished",
            "spinnaker_reports/2026-04-27-03-34-22-032643/global_provenance.sqlite3",
            "raw_reports/spinnaker_reports_tier4_15_seeds_42_43_44.zip",
        ),
    ),
    EvidenceSpec(
        entry_id="tier5_1_external_baselines",
        tier_label="Tier 5.1 - External Baselines",
        plan_position="Post-hardware external baseline comparison",
        canonical_dir="tier5_1_20260426_232530",
        results_file="tier5_1_results.json",
        report_file="tier5_1_report.md",
        summary_file="tier5_1_summary.csv",
        harness="experiments/tier5_external_baselines.py",
        evidence_role="external baseline comparison",
        claim="CRA is competitive against simple external learners and shows a defensible median-baseline advantage on sensor_control and hard noisy switching, while simpler online learners dominate the easy delayed-cue task.",
        caveat="Controlled software comparison only; not hardware evidence, not a claim that CRA wins every task, and not proof against all possible baselines.",
        latest_manifest_names=("tier5_1_latest_manifest.json",),
        expected_extra_files=(
            "tier5_1_comparisons.csv",
            "tier5_1_task_model_matrix.png",
            "tier5_1_cra_edges.png",
            "fixed_pattern_cra_seed42_timeseries.csv",
            "delayed_cue_online_perceptron_seed42_timeseries.csv",
            "sensor_control_cra_seed42_timeseries.csv",
            "hard_noisy_switching_cra_seed42_timeseries.csv",
        ),
    ),
    EvidenceSpec(
        entry_id="tier5_2_learning_curve_sweep",
        tier_label="Tier 5.2 - Learning Curve / Run-Length Sweep",
        plan_position="Post-v0.2 external baseline learning-curve addendum",
        canonical_dir="tier5_2_20260426_234500",
        results_file="tier5_2_results.json",
        report_file="tier5_2_report.md",
        summary_file="tier5_2_summary.csv",
        harness="experiments/tier5_learning_curve.py",
        evidence_role="external baseline run-length sweep",
        claim="Across 120, 240, 480, 960, and 1500 steps, CRA's Tier 5.1 hard-task edge does not strengthen at the longest horizon: sensor_control saturates for CRA and baselines, delayed_cue remains externally dominated, and hard_noisy_switching is mixed/negative at 1500 steps.",
        caveat="Controlled software learning-curve characterization only; not hardware evidence, not proof that CRA cannot improve under other tasks/tuning, and not a claim that Tier 5.1 was invalid.",
        latest_manifest_names=("tier5_2_latest_manifest.json",),
        expected_extra_files=(
            "tier5_2_comparisons.csv",
            "tier5_2_curve_analysis.csv",
            "tier5_2_learning_curves.png",
            "tier5_2_cra_edges_by_length.png",
            "tier5_2_runtime_by_length.png",
            "steps1500_sensor_control_cra_seed42_timeseries.csv",
            "steps1500_hard_noisy_switching_cra_seed42_timeseries.csv",
            "steps1500_delayed_cue_cra_seed42_timeseries.csv",
        ),
    ),
    EvidenceSpec(
        entry_id="tier5_3_cra_failure_analysis",
        tier_label="Tier 5.3 - CRA Failure Analysis / Learning Dynamics Debug",
        plan_position="Post-Tier-5.2 learning-dynamics diagnostic",
        canonical_dir="tier5_3_20260427_055629",
        results_file="tier5_3_results.json",
        report_file="tier5_3_report.md",
        summary_file="tier5_3_summary.csv",
        harness="experiments/tier5_cra_failure_analysis.py",
        evidence_role="CRA learning-dynamics failure analysis",
        claim="A 78-run CRA-only diagnostic matrix identifies delayed-credit strength as the leading candidate failure mode: `delayed_lr_0_20` restores delayed_cue to 1.0 tail accuracy and improves hard_noisy_switching above the external median at 960 steps.",
        caveat="Controlled software diagnostic only; not hardware evidence, not final competitiveness evidence, and hard_noisy_switching still trails the best external baseline.",
        latest_manifest_names=("tier5_3_latest_manifest.json",),
        expected_extra_files=(
            "tier5_3_comparisons.csv",
            "tier5_3_findings.csv",
            "tier5_3_variant_matrix.png",
            "tier5_3_group_effects.png",
            "delayed_cue_delayed_lr_0_20_seed42_timeseries.csv",
            "hard_noisy_switching_delayed_lr_0_20_seed42_timeseries.csv",
            "hard_noisy_switching_horizon_3_seed42_timeseries.csv",
        ),
    ),
    EvidenceSpec(
        entry_id="tier5_4_delayed_credit_confirmation",
        tier_label="Tier 5.4 - Delayed-Credit Confirmation",
        plan_position="Post-Tier-5.3 candidate-fix confirmation",
        canonical_dir="tier5_4_20260427_065412",
        results_file="tier5_4_results.json",
        report_file="tier5_4_report.md",
        summary_file="tier5_4_summary.csv",
        harness="experiments/tier5_delayed_credit_confirmation.py",
        evidence_role="delayed-credit candidate confirmation",
        claim="The Tier 5.3 delayed-credit candidate `cra_delayed_lr_0_20` confirms across 960 and 1500 steps: delayed_cue stays at 1.0 tail accuracy, hard_noisy_switching beats the external median at both lengths, and the candidate does not regress versus current CRA.",
        caveat="Controlled software confirmation only; not hardware evidence and not a superiority claim because hard_noisy_switching still trails the best external baseline.",
        latest_manifest_names=("tier5_4_latest_manifest.json",),
        expected_extra_files=(
            "tier5_4_confirmation.csv",
            "tier5_4_findings.csv",
            "tier5_4_confirmation.png",
            "tier5_4_seed_variance.png",
            "steps1500_delayed_cue_cra_delayed_lr_0_20_seed42_timeseries.csv",
            "steps1500_hard_noisy_switching_cra_delayed_lr_0_20_seed42_timeseries.csv",
            "steps1500_hard_noisy_switching_online_perceptron_seed42_timeseries.csv",
        ),
    ),
    EvidenceSpec(
        entry_id="tier4_16a_delayed_cue_hardware_repeat",
        tier_label="Tier 4.16a - Repaired Delayed-Cue Hardware Repeat",
        plan_position="Post-Tier-5.4/Tier-4.17b repaired harder-task hardware transfer",
        canonical_dir="tier4_16_20260427_184635_delayed_cue_3seed_hardware_pass",
        results_file="tier4_16_results.json",
        report_file="tier4_16_report.md",
        summary_file="tier4_16_summary.csv",
        harness="experiments/tier4_harder_spinnaker_capsule.py",
        evidence_role="repaired delayed-credit hardware transfer",
        claim="The repaired delayed-credit delayed_cue regime transfers to real SpiNNaker hardware across seeds 42, 43, and 44 using chunked host replay.",
        caveat="Three-seed N=8 delayed_cue capsule only; not hard_noisy_switching hardware transfer, hardware scaling, on-chip learning, or a full Tier 4.16 pass.",
        latest_manifest_names=("tier4_16a_latest_manifest.json",),
        expected_extra_files=(
            "tier4_16_task_summary.csv",
            "tier4_16_hardware_summary.png",
            "spinnaker_hardware_delayed_cue_seed42_timeseries.csv",
            "spinnaker_hardware_delayed_cue_seed42_timeseries.png",
            "spinnaker_hardware_delayed_cue_seed43_timeseries.csv",
            "spinnaker_hardware_delayed_cue_seed43_timeseries.png",
            "spinnaker_hardware_delayed_cue_seed44_timeseries.csv",
            "spinnaker_hardware_delayed_cue_seed44_timeseries.png",
            "raw_hardware_artifacts/finished",
            "raw_hardware_artifacts/global_provenance.sqlite3",
            "raw_hardware_artifacts/reports.zip",
            "raw_hardware_artifacts/source_tier4_16_report.md",
            "raw_hardware_artifacts/tier4_16_latest_manifest.json",
        ),
    ),
    EvidenceSpec(
        entry_id="tier4_16b_hard_switch_hardware_repeat",
        tier_label="Tier 4.16b - Repaired Hard-Switch Hardware Repeat",
        plan_position="Post-Tier-4.16a repaired harder-task hardware transfer",
        canonical_dir="tier4_16_20260427_230043_hard_noisy_switching_3seed_hardware_pass",
        results_file="tier4_16_results.json",
        report_file="tier4_16_report.md",
        summary_file="tier4_16_summary.csv",
        harness="experiments/tier4_harder_spinnaker_capsule.py",
        evidence_role="repaired hard-switch hardware transfer",
        claim="The repaired hard_noisy_switching regime transfers to real SpiNNaker hardware across seeds 42, 43, and 44 using chunked host replay.",
        caveat="Three-seed N=8 hard_noisy_switching capsule only; close-to-threshold transfer, not hardware scaling, on-chip learning, lifecycle/self-scaling, or external-baseline superiority.",
        latest_manifest_names=("tier4_16b_latest_manifest.json",),
        expected_extra_files=(
            "tier4_16_task_summary.csv",
            "tier4_16_hardware_summary.png",
            "tier4_16b_3seed_pass_analysis.md",
            "spinnaker_hardware_hard_noisy_switching_seed42_timeseries.csv",
            "spinnaker_hardware_hard_noisy_switching_seed42_timeseries.png",
            "spinnaker_hardware_hard_noisy_switching_seed43_timeseries.csv",
            "spinnaker_hardware_hard_noisy_switching_seed43_timeseries.png",
            "spinnaker_hardware_hard_noisy_switching_seed44_timeseries.csv",
            "spinnaker_hardware_hard_noisy_switching_seed44_timeseries.png",
            "raw_hardware_artifacts/finished",
            "raw_hardware_artifacts/global_provenance.sqlite3",
            "raw_hardware_artifacts/reports.zip",
            "raw_hardware_artifacts/source_tier4_16_report.md",
            "raw_hardware_artifacts/tier4_16_latest_manifest.json",
        ),
    ),
    EvidenceSpec(
        entry_id="tier4_18a_chunked_runtime_baseline",
        tier_label="Tier 4.18a - v0.7 Chunked Hardware Runtime Baseline",
        plan_position="Post-Tier-4.16b runtime/resource characterization",
        canonical_dir="tier4_18a_20260428_012822_hardware_pass",
        results_file="tier4_18a_results.json",
        report_file="tier4_18a_report.md",
        summary_file="tier4_18a_summary.csv",
        harness="experiments/tier4_18a_chunked_runtime_baseline.py",
        evidence_role="chunked hardware runtime profile",
        claim="The v0.7 chunked-host SpiNNaker path remains stable on delayed_cue and hard_noisy_switching at chunk sizes 10, 25, and 50; chunk 50 is the fastest viable default for the current hardware bridge.",
        caveat="Single-seed N=8 runtime/resource characterization only; not hardware scaling, lifecycle/self-scaling, native on-chip dopamine/eligibility, continuous/custom-C runtime, or external-baseline superiority.",
        latest_manifest_names=("tier4_18a_latest_manifest.json",),
        expected_extra_files=(
            "tier4_18a_runtime_matrix.csv",
            "tier4_18a_runtime_matrix.png",
            "tier4_18a_pass_analysis.md",
            "spinnaker_hardware_delayed_cue_chunk10_seed42_timeseries.csv",
            "spinnaker_hardware_delayed_cue_chunk10_seed42_timeseries.png",
            "spinnaker_hardware_delayed_cue_chunk25_seed42_timeseries.csv",
            "spinnaker_hardware_delayed_cue_chunk25_seed42_timeseries.png",
            "spinnaker_hardware_delayed_cue_chunk50_seed42_timeseries.csv",
            "spinnaker_hardware_delayed_cue_chunk50_seed42_timeseries.png",
            "spinnaker_hardware_hard_noisy_switching_chunk10_seed42_timeseries.csv",
            "spinnaker_hardware_hard_noisy_switching_chunk10_seed42_timeseries.png",
            "spinnaker_hardware_hard_noisy_switching_chunk25_seed42_timeseries.csv",
            "spinnaker_hardware_hard_noisy_switching_chunk25_seed42_timeseries.png",
            "spinnaker_hardware_hard_noisy_switching_chunk50_seed42_timeseries.csv",
            "spinnaker_hardware_hard_noisy_switching_chunk50_seed42_timeseries.png",
            "raw_hardware_artifacts/finished",
            "raw_hardware_artifacts/global_provenance.sqlite3",
            "raw_hardware_artifacts/reports.zip",
        ),
    ),
    EvidenceSpec(
        entry_id="tier5_5_expanded_baselines",
        tier_label="Tier 5.5 - Expanded Baseline Suite",
        plan_position="Post-Tier-4.18a expanded software baseline/fairness gate",
        canonical_dir="tier5_5_20260427_222736",
        results_file="tier5_5_results.json",
        report_file="tier5_5_report.md",
        summary_file="tier5_5_summary.csv",
        harness="experiments/tier5_expanded_baselines.py",
        evidence_role="expanded software baseline comparison",
        claim="The locked CRA v0.8 delayed-credit configuration completes the 1,800-run expanded baseline matrix, shows robust advantage regimes, and is not dominated on most hard/adaptive regimes while documenting where strong external baselines tie or win.",
        caveat="Controlled software evidence only; not hardware evidence, not a hyperparameter fairness audit, not a universal superiority claim, and not proof that CRA beats the best external baseline at every horizon.",
        latest_manifest_names=("tier5_5_latest_manifest.json",),
        expected_extra_files=(
            "tier5_5_comparisons.csv",
            "tier5_5_per_seed.csv",
            "tier5_5_fairness_contract.json",
            "tier5_5_edge_summary.png",
            "steps1500_delayed_cue_cra_v0_8_delayed_lr_0_20_seed42_timeseries.csv",
            "steps1500_hard_noisy_switching_cra_v0_8_delayed_lr_0_20_seed42_timeseries.csv",
            "steps1500_hard_noisy_switching_online_perceptron_seed42_timeseries.csv",
            "steps1500_sensor_control_cra_v0_8_delayed_lr_0_20_seed42_timeseries.csv",
        ),
    ),
    EvidenceSpec(
        entry_id="tier5_6_baseline_hyperparameter_fairness_audit",
        tier_label="Tier 5.6 - Baseline Hyperparameter Fairness Audit",
        plan_position="Post-Tier-5.5 tuned-baseline reviewer-defense gate",
        canonical_dir="tier5_6_20260428_001834",
        results_file="tier5_6_results.json",
        report_file="tier5_6_report.md",
        summary_file="tier5_6_summary.csv",
        harness="experiments/tier5_baseline_fairness_audit.py",
        evidence_role="retuned external-baseline fairness audit",
        claim="With CRA locked at the promoted delayed-credit setting, the 990-run Tier 5.6 audit gives external baselines a documented tuning budget and finds surviving target regimes after retuning.",
        caveat="Controlled software fairness audit only; not hardware evidence, not universal superiority, and not proof that CRA beats the best tuned external baseline at every metric or horizon.",
        latest_manifest_names=("tier5_6_latest_manifest.json",),
        expected_extra_files=(
            "tier5_6_comparisons.csv",
            "tier5_6_best_profiles.csv",
            "tier5_6_candidate_budget.csv",
            "tier5_6_per_seed.csv",
            "tier5_6_fairness_contract.json",
            "tier5_6_edge_summary.png",
            "steps1500_hard_noisy_switching_cra_v0_8_delayed_lr_0_20_seed42_timeseries.csv",
            "steps1500_hard_noisy_switching_online_perceptron__perceptron_lr_0p08_perceptron_margin_0p05_seed42_timeseries.csv",
            "steps1500_sensor_control_cra_v0_8_delayed_lr_0_20_seed42_timeseries.csv",
        ),
    ),
    EvidenceSpec(
        entry_id="tier5_7_compact_regression",
        tier_label="Tier 5.7 - Compact Regression After Promoted Tuning",
        plan_position="Post-v1.0 compact control/learning/ablation regression before lifecycle work",
        canonical_dir="tier5_7_20260428_005723",
        results_file="tier5_7_results.json",
        report_file="tier5_7_report.md",
        summary_file="tier5_7_summary.csv",
        harness="experiments/tier5_compact_regression.py",
        evidence_role="compact regression guardrail",
        claim="The promoted v1.0 delayed-credit setting passes compact negative controls, positive learning controls, architecture ablations, and delayed_cue/hard_noisy_switching smoke checks before lifecycle/self-scaling work.",
        caveat="Controlled software regression evidence only; not a new capability claim, not hardware evidence, not lifecycle/self-scaling evidence, and not external-baseline superiority.",
        latest_manifest_names=("tier5_7_latest_manifest.json",),
        expected_extra_files=(
            "tier5_7_child_manifests.json",
            "tier1_controls/tier1_results.json",
            "tier2_learning/tier2_results.json",
            "tier3_ablations/tier3_results.json",
            "target_task_smokes/tier5_6_results.json",
        ),
    ),
    EvidenceSpec(
        entry_id="tier5_12a_predictive_task_pressure",
        tier_label="Tier 5.12a - Predictive Task-Pressure Validation",
        plan_position="Predictive/context modeling task-validation gate after v1.7 memory/replay baseline",
        canonical_dir="tier5_12a_20260429_054052",
        results_file="tier5_12a_results.json",
        report_file="tier5_12a_report.md",
        summary_file="tier5_12a_summary.csv",
        harness="experiments/tier5_predictive_task_pressure.py",
        evidence_role="predictive task-pressure validation",
        claim="Predictive-pressure streams defeat current-reflex, sign-persistence, wrong-horizon, and shuffled-target shortcuts while causal predictive-memory controls solve them.",
        caveat="Task-validation evidence only; not CRA predictive coding, world modeling, language, planning, hardware prediction, or a v1.8 freeze.",
        latest_manifest_names=("tier5_12a_latest_manifest.json",),
        expected_extra_files=(
            "tier5_12a_comparisons.csv",
            "tier5_12a_fairness_contract.json",
            "tier5_12a_task_pressure.png",
            "hidden_regime_switching_predictive_memory_seed42_timeseries.csv",
            "masked_input_prediction_predictive_memory_seed42_timeseries.csv",
            "event_stream_prediction_predictive_memory_seed42_timeseries.csv",
            "sensor_anomaly_prediction_predictive_memory_seed42_timeseries.csv",
        ),
    ),
    EvidenceSpec(
        entry_id="tier5_12c_predictive_context_sham_repair",
        tier_label="Tier 5.12c - Predictive Context Sham-Separation Repair",
        plan_position="Predictive/context software mechanism gate after failed Tier 5.12b diagnostic",
        canonical_dir="tier5_12c_20260429_062256",
        results_file="tier5_12c_results.json",
        report_file="tier5_12c_report.md",
        summary_file="tier5_12c_summary.csv",
        harness="experiments/tier5_predictive_context_sham_repair.py",
        evidence_role="host-side predictive-context mechanism diagnostic",
        claim="Internal visible predictive-context binding matches the external scaffold and beats v1.7 reactive CRA, shuffled/permuted/no-write shams, shortcut controls, and selected external baselines.",
        caveat="Host-side software evidence only; Tier 5.12d provides the separate promotion gate. Not hidden-regime inference, full world modeling, language, planning, hardware prediction, hardware scaling, native on-chip learning, compositionality, or external-baseline superiority.",
        latest_manifest_names=("tier5_12c_latest_manifest.json",),
        expected_extra_files=(
            "tier5_12c_comparisons.csv",
            "tier5_12c_fairness_contract.json",
            "tier5_12c_predictive_context.png",
            "masked_input_prediction_internal_predictive_context_seed42_timeseries.csv",
            "event_stream_prediction_internal_predictive_context_seed42_timeseries.csv",
            "sensor_anomaly_prediction_internal_predictive_context_seed42_timeseries.csv",
            "masked_input_prediction_permuted_predictive_context_seed42_timeseries.csv",
        ),
    ),
    EvidenceSpec(
        entry_id="tier5_12d_predictive_context_compact_regression",
        tier_label="Tier 5.12d - Predictive-Context Compact Regression",
        plan_position="Promotion gate after Tier 5.12c before freezing v1.8",
        canonical_dir="tier5_12d_20260429_070615",
        results_file="tier5_12d_results.json",
        report_file="tier5_12d_report.md",
        summary_file="tier5_12d_summary.csv",
        harness="experiments/tier5_predictive_context_compact_regression.py",
        evidence_role="predictive-context compact regression guardrail",
        claim="The host-side visible predictive-context mechanism preserves Tier 1/2/3 controls, target hard-task smokes, v1.7 replay/consolidation guardrails, and predictive sham separation, authorizing a bounded v1.8 software baseline.",
        caveat="Software-only promotion gate; v1.8 remains bounded to visible predictive-context tasks and is not hidden-regime inference, full world modeling, language, planning, hardware prediction, hardware scaling, native on-chip learning, compositionality, or external-baseline superiority.",
        latest_manifest_names=("tier5_12d_latest_manifest.json",),
        expected_extra_files=(
            "tier5_12d_child_manifests.json",
            "tier1_controls/tier1_results.json",
            "tier2_learning/tier2_results.json",
            "tier3_ablations/tier3_results.json",
            "target_task_smokes/tier5_6_results.json",
            "replay_consolidation_guardrail/tier5_11d_results.json",
            "predictive_context_guardrail/tier5_12c_results.json",
        ),
    ),
    EvidenceSpec(
        entry_id="tier6_1_lifecycle_self_scaling",
        tier_label="Tier 6.1 - Software Lifecycle / Self-Scaling Benchmark",
        plan_position="Phase 4 organism/lifecycle/self-scaling proof",
        canonical_dir="tier6_1_20260428_012109",
        results_file="tier6_1_results.json",
        report_file="tier6_1_report.md",
        summary_file="tier6_1_summary.csv",
        harness="experiments/tier6_lifecycle_self_scaling.py",
        evidence_role="software lifecycle/self-scaling benchmark",
        claim="Lifecycle-enabled CRA expands from fixed initial populations with clean lineage tracking and shows hard_noisy_switching advantage regimes versus same-initial fixed-N controls.",
        caveat="Controlled software lifecycle evidence only; growth is cleavage-dominated with one adult birth and zero deaths, so this is not full adult turnover, not sham-control proof, not hardware lifecycle evidence, and not external-baseline superiority.",
        latest_manifest_names=("tier6_1_latest_manifest.json",),
        expected_extra_files=(
            "tier6_1_comparisons.csv",
            "tier6_1_lifecycle_events.csv",
            "tier6_1_lineage_final.csv",
            "tier6_1_lifecycle_summary.png",
            "tier6_1_alive_population.png",
            "tier6_1_event_analysis.json",
            "tier6_1_event_analysis.md",
            "hard_noisy_switching_life4_16_seed42_timeseries.csv",
            "hard_noisy_switching_life8_32_seed42_timeseries.csv",
            "delayed_cue_life4_16_seed42_timeseries.csv",
        ),
    ),
    EvidenceSpec(
        entry_id="tier6_3_lifecycle_sham_controls",
        tier_label="Tier 6.3 - Lifecycle Sham-Control Suite",
        plan_position="Phase 4 organism/lifecycle reviewer-defense gate after Tier 6.1",
        canonical_dir="tier6_3_20260428_121504",
        results_file="tier6_3_results.json",
        report_file="tier6_3_report.md",
        summary_file="tier6_3_summary.csv",
        harness="experiments/tier6_lifecycle_sham_controls.py",
        evidence_role="software lifecycle sham-control benchmark",
        claim="Lifecycle-enabled CRA beats fixed max-pool, event-count replay, no-trophic, no-dopamine, and no-plasticity sham controls on hard_noisy_switching while preserving clean lineage integrity.",
        caveat="Controlled software sham-control evidence only; replay/shuffle controls are audit artifacts, not independent learners, and this is not hardware lifecycle evidence, full adult turnover, external-baseline superiority, or compositional/world-model evidence.",
        latest_manifest_names=("tier6_3_latest_manifest.json",),
        expected_extra_files=(
            "tier6_3_comparisons.csv",
            "tier6_3_lifecycle_events.csv",
            "tier6_3_lineage_final.csv",
            "tier6_3_sham_manifest.json",
            "tier6_3_sham_summary.png",
            "tier6_3_alive_population.png",
            "hard_noisy_switching_life4_16_intact_seed42_timeseries.csv",
            "hard_noisy_switching_life4_16_fixed_max_seed42_timeseries.csv",
            "hard_noisy_switching_life4_16_random_event_replay_seed42_timeseries.csv",
            "hard_noisy_switching_life8_32_intact_seed42_timeseries.csv",
            "hard_noisy_switching_life8_32_fixed_max_seed42_timeseries.csv",
            "hard_noisy_switching_life8_32_random_event_replay_seed42_timeseries.csv",
        ),
    ),
    EvidenceSpec(
        entry_id="tier6_4_circuit_motif_causality",
        tier_label="Tier 6.4 - Circuit Motif Causality",
        plan_position="Phase 4 organism/circuit-motif reviewer-defense gate after Tier 6.3",
        canonical_dir="tier6_4_20260428_144354",
        results_file="tier6_4_results.json",
        report_file="tier6_4_report.md",
        summary_file="tier6_4_summary.csv",
        harness="experiments/tier6_circuit_motif_causality.py",
        evidence_role="software circuit-motif causality benchmark",
        claim="Seeded motif-diverse CRA passes motif-causality controls on hard_noisy_switching: ablations cause predicted losses, motif activity is logged before reward/learning, and random/monolithic controls do not dominate across adaptation metrics.",
        caveat="Controlled software motif-causality evidence only; motif-diverse graph is seeded for this suite, motif-label shuffle shows labels alone are not causal, and this is not hardware motif evidence, custom-C/on-chip learning, compositionality, or full world-model evidence.",
        latest_manifest_names=("tier6_4_latest_manifest.json",),
        expected_extra_files=(
            "tier6_4_comparisons.csv",
            "tier6_4_motif_graph.csv",
            "tier6_4_lifecycle_events.csv",
            "tier6_4_lineage_final.csv",
            "tier6_4_motif_manifest.json",
            "tier6_4_motif_summary.png",
            "tier6_4_motif_activity.png",
            "hard_noisy_switching_life4_16_intact_seed42_timeseries.csv",
            "hard_noisy_switching_life4_16_no_feedback_seed42_timeseries.csv",
            "hard_noisy_switching_life8_32_intact_seed42_timeseries.csv",
            "hard_noisy_switching_life8_32_no_feedforward_seed42_timeseries.csv",
            "hard_noisy_switching_life8_32_random_graph_same_edge_count_seed42_timeseries.csv",
        ),
    ),
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_json(path: Path) -> dict[str, Any]:
    with path.open() as f:
        return json.load(f)


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=False) + "\n")


def scalar(value: Any) -> bool:
    return value is None or isinstance(value, (bool, int, float, str))


def select_scalar_metrics(data: dict[str, Any], limit: int = 24) -> dict[str, Any]:
    """Keep registry metrics useful without duplicating entire raw manifests."""
    preferred = [
        "all_accuracy_mean",
        "tail_accuracy_mean",
        "prediction_target_corr_mean",
        "tail_prediction_target_corr_mean",
        "tail_prediction_target_corr_min",
        "tail_prediction_target_corr_max",
        "total_step_spikes_mean",
        "total_step_spikes_min",
        "total_step_spikes_max",
        "mean_step_spikes_mean",
        "synthetic_fallbacks_sum",
        "sim_run_failures_sum",
        "summary_read_failures_sum",
        "final_n_alive_mean",
        "total_births_sum",
        "total_deaths_sum",
        "runtime_seconds_mean",
        "runtime_seconds_min",
        "runtime_seconds_max",
        "hardware_run_attempted",
        "hardware_target_configured",
        "all_seed_statuses_pass",
        "hard_advantage_task_count",
        "observed_runs",
        "expected_runs",
        "aggregate_cells",
        "functional_cell_count",
        "functional_cell_fraction",
        "default_min_tail_accuracy",
        "collapse_count",
        "propagation_failures",
        "response_probe_monotonic_fraction",
        "best_fixed_external_tail_accuracy",
        "robust_advantage_regime_count",
        "not_dominated_hard_regime_count",
        "final_advantage_task_count",
        "final_run_length_steps",
        "expected_cells",
        "observed_cells",
        "expected_comparison_rows",
        "observed_comparison_rows",
        "observed_run_lengths",
        "candidate_count",
        "expected_profile_groups",
        "observed_profile_groups",
        "robust_target_regime_count",
        "not_dominated_target_regime_count",
        "surviving_target_regime_count",
        "children_run",
        "children_passed",
        "expected_children",
        "criteria_passed",
        "criteria_total",
        "actual_runs",
        "fixed_births_sum",
        "fixed_deaths_sum",
        "lifecycle_births_sum",
        "lifecycle_deaths_sum",
        "lineage_integrity_failures",
        "advantage_regime_count",
        "advantage_tasks",
        "max_tail_delta_vs_paired_fixed",
        "max_abs_corr_delta_vs_paired_fixed",
        "max_recovery_improvement_steps_vs_paired_fixed",
        "expected_actual_runs",
        "intact_non_handoff_lifecycle_events_sum",
        "fixed_non_handoff_lifecycle_events_sum",
        "actual_lineage_integrity_failures",
        "extinct_actual_aggregate_count",
        "performance_control_win_count",
        "fixed_max_win_count",
        "random_event_replay_win_count",
        "no_trophic_win_count",
        "no_dopamine_win_count",
        "no_plasticity_win_count",
        "lineage_shuffle_detected_count",
        "active_mask_shuffle_present",
        "intact_motif_diverse_aggregate_count",
        "expected_intact_aggregates",
        "intact_motif_activity_steps_sum",
        "motif_loss_count",
        "motif_ablation_loss_count",
        "random_or_monolithic_domination_count",
        "motif_shuffled_row_count",
        "no_wta_row_count",
        "external_models",
        "cra_variants",
        "runs",
        "backend",
        "seed",
        "seeds",
        "requested_seeds",
        "population_sizes",
        "steps",
    ]
    metrics: dict[str, Any] = {}
    for key in preferred:
        if key in data and (scalar(data[key]) or isinstance(data[key], list)):
            metrics[key] = data[key]
    for key in sorted(data):
        if len(metrics) >= limit:
            break
        if key not in metrics and scalar(data[key]):
            metrics[key] = data[key]
    return metrics


def iter_result_items(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    if isinstance(manifest.get("results"), list):
        return [item for item in manifest["results"] if isinstance(item, dict)]
    if isinstance(manifest.get("result"), dict):
        return [manifest["result"]]
    if manifest.get("criteria"):
        return [manifest]
    return []


def status_from_manifest(manifest: dict[str, Any]) -> str:
    if isinstance(manifest.get("status"), str):
        return manifest["status"].lower()
    items = iter_result_items(manifest)
    if items:
        statuses = [str(item.get("status", "")).lower() for item in items]
        if statuses and all(status == "pass" for status in statuses):
            return "pass"
        if any(status in {"fail", "failed"} for status in statuses):
            return "fail"
        if any(status == "blocked" for status in statuses):
            return "blocked"
    if manifest.get("stopped_after"):
        return "fail"
    return "unknown"


def criteria_summary(item: dict[str, Any]) -> dict[str, Any]:
    criteria = item.get("criteria") or []
    if not isinstance(criteria, list):
        return {"total": 0, "passed": 0, "failed": 0, "failures": []}
    failures = [
        {
            "name": c.get("name"),
            "value": c.get("value"),
            "operator": c.get("operator"),
            "threshold": c.get("threshold"),
            "note": c.get("note", ""),
        }
        for c in criteria
        if isinstance(c, dict) and not c.get("passed")
    ]
    return {
        "total": len(criteria),
        "passed": sum(1 for c in criteria if isinstance(c, dict) and c.get("passed")),
        "failed": len(failures),
        "failures": failures,
    }


def normalize_test_results(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    tests = []
    for item in iter_result_items(manifest):
        summary = item.get("summary") if isinstance(item.get("summary"), dict) else {}
        if not summary and isinstance(item.get("metrics"), dict):
            summary = item["metrics"]
        tests.append(
            {
                "name": item.get("name") or item.get("test") or manifest.get("tier"),
                "status": str(item.get("status") or manifest.get("status") or "unknown").lower(),
                "criteria": criteria_summary(item),
                "metrics": select_scalar_metrics(summary),
                "artifacts": item.get("artifacts", {}),
            }
        )
    return tests


def expected_artifacts(spec: EvidenceSpec) -> list[Path]:
    run_dir = OUTPUT_ROOT / spec.canonical_dir
    artifacts = [
        run_dir / spec.results_file,
        run_dir / spec.report_file,
    ]
    if spec.summary_file:
        artifacts.append(run_dir / spec.summary_file)
    artifacts.extend(run_dir / rel for rel in spec.expected_extra_files)
    return artifacts


def latest_manifest_payload(spec: EvidenceSpec, manifest: dict[str, Any], entry: dict[str, Any]) -> dict[str, Any]:
    run_dir = OUTPUT_ROOT / spec.canonical_dir
    payload = {
        "generated_at_utc": utc_now(),
        "source_generated_at_utc": manifest.get("generated_at_utc"),
        "registry_entry_id": spec.entry_id,
        "tier": spec.tier_label,
        "status": entry["status"],
        "output_dir": str(run_dir),
        "manifest": str(run_dir / spec.results_file),
        "report": str(run_dir / spec.report_file),
        "summary_csv": str(run_dir / spec.summary_file) if spec.summary_file else None,
        "canonical": True,
        "claim": spec.claim,
        "caveat": spec.caveat,
    }
    if spec.entry_id == "tier3_architecture":
        # Backward-compatible keys for older tooling that reads this manifest.
        payload["latest_manifest"] = payload["manifest"]
        payload["latest_report"] = payload["report"]
        payload["latest_summary_csv"] = payload["summary_csv"]
    if spec.entry_id == "tier4_13_spinnaker_hardware_capsule":
        study_data = run_dir / "study_data.json"
        provenance_dir = run_dir / "spinnaker_reports" / "2026-04-27-01-19-12-390038"
        payload["study_data"] = str(study_data)
        payload["spinnaker_provenance_dir"] = str(provenance_dir)
        payload["claim_boundary"] = [
            "This is a minimal fixed-pattern hardware capsule, not a full hardware scaling claim.",
            "The run used one seed (42), N=8, 120 steps, and a fixed population.",
            "hardware_target_configured is false because local/JobManager environment detection did not expose a config flag, but hardware_run_attempted is true and real spike readback was nonzero.",
        ]
    if spec.entry_id == "tier4_15_spinnaker_hardware_multiseed_repeat":
        study_data = run_dir / "study_data.json"
        provenance_dirs = [
            run_dir / "spinnaker_reports" / "2026-04-27-03-05-01-872105",
            run_dir / "spinnaker_reports" / "2026-04-27-03-19-49-290162",
            run_dir / "spinnaker_reports" / "2026-04-27-03-34-22-032643",
        ]
        payload["study_data"] = str(study_data)
        payload["spinnaker_provenance_dirs"] = [str(path) for path in provenance_dirs]
        payload["claim_boundary"] = [
            "This is a three-seed repeatability result for the minimal fixed-pattern hardware capsule.",
            "The run used seeds 42, 43, and 44, N=8, 120 steps, and a fixed population.",
            "It is not a harder-task hardware result, hardware population scaling result, or full CRA hardware deployment.",
            "hardware_target_configured is false because local/JobManager environment detection did not expose a config flag, but hardware_run_attempted is true and real spike readback was nonzero for every seed.",
        ]
    if spec.entry_id == "tier5_1_external_baselines":
        payload["claim_boundary"] = [
            "Tier 5.1 is a controlled software baseline comparison, not a hardware result.",
            "The baseline matrix used CRA plus random/sign persistence, online perceptron, online logistic regression, echo-state network, small GRU readout, STDP-only SNN, and evolutionary population baselines.",
            "CRA does not win every task; simpler learners dominate the easy delayed-cue mapping.",
            "The pass claim is limited to a defensible median-baseline advantage on sensor_control and hard noisy switching plus full matrix completion.",
        ]
    if spec.entry_id == "tier5_2_learning_curve_sweep":
        payload["claim_boundary"] = [
            "Tier 5.2 is a controlled software run-length sweep, not a hardware result.",
            "The matrix used the same CRA and external baselines as Tier 5.1 on sensor_control, hard_noisy_switching, and delayed_cue.",
            "The tier passes methodologically because the full 405-run matrix completed and produced interpretable curves.",
            "The scientific finding is not a CRA win at the final horizon: final_advantage_task_count is zero at 1500 steps.",
            "Tier 4.16 hardware should not blindly move these exact tasks to hardware without first deciding whether to tune CRA or design a sharper hard-task probe.",
        ]
    if spec.entry_id == "tier5_3_cra_failure_analysis":
        payload["claim_boundary"] = [
            "Tier 5.3 is a controlled software CRA-only diagnostic, not a hardware result.",
            "The matrix used seeds 42, 43, and 44, steps=960, tasks delayed_cue and hard_noisy_switching, and 13 CRA variants.",
            "The leading candidate fix is stronger delayed credit: delayed_lr_0_20 restores delayed_cue to the external-best tail score and improves hard_noisy_switching above the external median.",
            "This is not enough to launch Tier 4.16 hardware directly because hard_noisy_switching still trails the best external baseline and the tuned setting needs targeted confirmation at longer horizons.",
            "sensor_control is intentionally excluded from the advantage probe because Tier 5.2 showed it saturates for CRA and baselines.",
        ]
    if spec.entry_id == "tier5_4_delayed_credit_confirmation":
        payload["claim_boundary"] = [
            "Tier 5.4 is a controlled software confirmation, not a hardware result.",
            "The matrix used seeds 42, 43, and 44, run lengths 960 and 1500, tasks delayed_cue and hard_noisy_switching, current CRA, cra_delayed_lr_0_20, and eight external baselines.",
            "The delayed-credit candidate confirms versus the predeclared Tier 5.4 criteria: delayed_cue stays at 1.0 tail accuracy, hard_noisy_switching beats the external median, no regression versus current CRA, and seed variance is acceptable.",
            "Do not claim hard-switch superiority: hard_noisy_switching still trails the best external baseline at both run lengths.",
            "This result supports designing Tier 4.16 as a harder SpiNNaker capsule using delayed_lr_0_20, not claiming full hardware readiness.",
        ]
    if spec.entry_id == "tier4_16a_delayed_cue_hardware_repeat":
        payload["claim_boundary"] = [
            "Tier 4.16a is a repaired delayed_cue hardware-transfer result using the Tier 5.4 delayed_lr_0_20 setting.",
            "The run used seeds 42, 43, and 44, N=8, 1200 steps, runtime_mode=chunked, learning_location=host, and chunk_size_steps=25.",
            "It passed with zero synthetic fallback, zero sim.run failures, zero summary-read failures, and real spike readback in every seed.",
            "It does not prove hard_noisy_switching transfer, hardware scaling, self-scaling lifecycle behavior, continuous/on-chip learning, or full Tier 4.16.",
            "hardware_target_configured is false because local/JobManager environment detection did not expose a config flag, but hardware_run_attempted is true and real spike readback was nonzero for every seed.",
        ]
    if spec.entry_id == "tier4_16b_hard_switch_hardware_repeat":
        payload["claim_boundary"] = [
            "Tier 4.16b is a repaired hard_noisy_switching hardware-transfer result using the Tier 5.4 delayed_lr_0_20 setting.",
            "The run used seeds 42, 43, and 44, N=8, 1200 steps, runtime_mode=chunked, learning_location=host, and chunk_size_steps=25.",
            "It passed with zero synthetic fallback, zero sim.run failures, zero summary-read failures, and real spike readback in every seed.",
            "The hard-switch pass is close to threshold: tail_accuracy_min is 0.5238095238095238 against a 0.5 gate.",
            "raw_dopamine is expected to be zero in this chunked host delayed-credit scaffold; cite matured horizon replay and host_replay_weight movement, not native on-chip dopamine.",
            "It does not prove hardware scaling, self-scaling lifecycle behavior, continuous/on-chip learning, native eligibility traces, or external-baseline superiority.",
            "hardware_target_configured is false because local/JobManager environment detection did not expose a config flag, but hardware_run_attempted is true and real spike readback was nonzero for every seed.",
        ]
    if spec.entry_id == "tier4_18a_chunked_runtime_baseline":
        payload["claim_boundary"] = [
            "Tier 4.18a is runtime/resource characterization for the already-promoted v0.7 chunked-host SpiNNaker path.",
            "The run used seed 42, N=8, 1200 steps, tasks delayed_cue and hard_noisy_switching, and chunk sizes 10, 25, and 50.",
            "Chunk 50 preserved the observed task metrics while cutting sim.run calls to 24 per task, so it is the current default hardware chunk for v0.7.",
            "raw_dopamine is expected to be zero in this chunked host delayed-credit scaffold; cite matured horizon replay and host-replay outputs, not native on-chip dopamine.",
            "It does not prove hardware scaling, lifecycle/self-scaling, continuous/custom-C runtime, native dopamine/eligibility, or external-baseline superiority.",
            "hardware_target_configured is false because local/JobManager environment detection did not expose a config flag, but hardware_run_attempted is true and real spike readback was nonzero for every run.",
        ]
    if spec.entry_id == "tier5_5_expanded_baselines":
        payload["claim_boundary"] = [
            "Tier 5.5 is controlled software expanded-baseline evidence, not hardware evidence.",
            "The full run used 10 seeds, run lengths 120/240/480/960/1500, tasks fixed_pattern/delayed_cue/hard_noisy_switching/sensor_control, locked CRA v0.8, and eight implemented external baselines.",
            "The matrix completed 1,800 runs and produced paired deltas, bootstrap confidence intervals, paired effect sizes, per-seed audit rows, runtime, sample-efficiency, recovery, and a fairness contract.",
            "CRA shows robust advantage regimes and is not dominated on most hard/adaptive regimes; hard_noisy_switching beats the external median at 1500 steps but does not beat the best external tail score there.",
            "Do not claim universal superiority, best-baseline dominance, real-world usefulness, hardware transfer, lifecycle/self-scaling value, or hyperparameter-fairness completion from this tier.",
            "Tier 5.6 supersedes this as the tuned-baseline reviewer-defense audit; cite Tier 5.5 for broad matrix coverage and Tier 5.6 for retuned-baseline fairness.",
        ]
    if spec.entry_id == "tier5_6_baseline_hyperparameter_fairness_audit":
        payload["claim_boundary"] = [
            "Tier 5.6 is controlled software tuned-baseline fairness evidence, not hardware evidence.",
            "CRA was locked at the promoted delayed-credit setting while implemented external baselines received a predeclared tuning budget.",
            "The standard run completed 990 observed runs, 198 cells, 32 candidate profiles, 48 profile groups, and six task/run-length comparison rows.",
            "CRA retained four surviving target regimes after retuning: hard_noisy_switching and sensor_control at 960 and 1500 steps.",
            "Do not claim universal superiority, real-world usefulness, all-possible-baselines coverage, hardware transfer, lifecycle/self-scaling value, or best-baseline dominance from this tier.",
            "The hard_noisy_switching 1500-step tail metric remains weaker than the best tuned perceptron tail score, even though the regime survives the audit through other paired criteria.",
        ]
    if spec.entry_id == "tier5_7_compact_regression":
        payload["claim_boundary"] = [
            "Tier 5.7 is controlled software compact-regression evidence, not hardware evidence.",
            "The run used backend NEST, readout_lr=0.10, delayed_readout_lr=0.20, and the v1.0 promoted CRA setting.",
            "Tier 1 negative controls, Tier 2 positive controls, Tier 3 architecture ablations, and delayed_cue/hard_noisy_switching task smokes all passed.",
            "This authorizes moving to Tier 6 lifecycle/self-scaling work without rewriting the v1.0 setting.",
            "Do not cite Tier 5.7 as a new learning capability, external-baseline superiority, lifecycle/self-scaling evidence, hardware scaling, native on-chip learning, compositionality, or world modeling.",
        ]
    if spec.entry_id == "tier5_12a_predictive_task_pressure":
        payload["claim_boundary"] = [
            "Tier 5.12a is controlled software task-validation evidence, not a CRA mechanism promotion.",
            "The run validates that the predictive-pressure task family defeats reflex/sign-persistence/wrong-horizon/shuffled-target shortcuts while causal predictive-memory controls can solve it.",
            "It does not prove CRA predictive coding, world modeling, language, planning, hardware prediction, hardware scaling, or v1.8.",
        ]
    if spec.entry_id == "tier5_12c_predictive_context_sham_repair":
        payload["claim_boundary"] = [
            "Tier 5.12c is controlled host-side software predictive-context evidence, not hardware evidence.",
            "The full NEST matrix completed 171/171 cells with zero leakage; the internal visible predictive-context candidate matched the external scaffold and beat v1.7 reactive CRA, shuffled/permuted/no-write shams, shortcut controls, and selected external baselines.",
            "Wrong-sign context is reported as a learnable alternate code from the failed Tier 5.12b diagnostic, not as the promotion sham.",
            "Tier 5.12d compact regression is the promotion gate that freezes the bounded v1.8 software baseline.",
            "Do not cite Tier 5.12c as hidden-regime inference, full world modeling, language, planning, hardware prediction, hardware scaling, native on-chip learning, compositionality, or external-baseline superiority.",
        ]
    if spec.entry_id == "tier5_12d_predictive_context_compact_regression":
        payload["claim_boundary"] = [
            "Tier 5.12d is controlled software compact-regression and promotion-gate evidence.",
            "The run used NEST for Tier 1/2/3, target hard-task smokes, and the predictive-context guardrail; it also reran the v1.7 replay/consolidation guardrail.",
            "All six child checks passed: Tier 1 negative controls, Tier 2 positive controls, Tier 3 architecture ablations, delayed_cue/hard_noisy_switching smokes, replay/consolidation, and compact predictive-context sham separation.",
            "This authorizes a bounded v1.8 host-side visible predictive-context software baseline.",
            "Do not cite Tier 5.12d as hidden-regime inference, full world modeling, language, planning, lifecycle/self-scaling, hardware prediction, hardware scaling, native on-chip learning, compositionality, or external-baseline superiority.",
        ]
    if spec.entry_id == "tier6_1_lifecycle_self_scaling":
        payload["claim_boundary"] = [
            "Tier 6.1 is controlled software lifecycle/self-scaling evidence, not hardware evidence.",
            "The run used backend NEST, seeds 42/43/44, steps=960, tasks hard_noisy_switching and delayed_cue, and cases fixed4/fixed8/fixed16/life4_16/life8_32/life16_64.",
            "Lifecycle cases produced 75 new-polyp events with clean lineage integrity and no aggregate extinction.",
            "Event-type analysis shows 74 cleavage events, one adult birth event, and zero death events; cite this as lifecycle expansion/self-scaling evidence, not full adult birth/death turnover.",
            "The lifecycle advantage appears on hard_noisy_switching for life4_16 and life8_32 versus same-initial fixed controls; delayed_cue saturated for fixed and lifecycle cases.",
            "Do not cite Tier 6.1 as hardware lifecycle evidence, sham-control proof, external-baseline superiority, native on-chip lifecycle, continuous runtime, compositionality, or world modeling.",
        ]
    if spec.entry_id == "tier6_3_lifecycle_sham_controls":
        payload["claim_boundary"] = [
            "Tier 6.3 is controlled software sham-control evidence for the Tier 6.1 organism/lifecycle claim.",
            "The run used NEST, hard_noisy_switching, seeds 42/43/44, regimes life4_16 and life8_32, and 960 steps.",
            "Intact lifecycle produced 26 non-handoff lifecycle events and beat all 10 requested performance-sham comparisons.",
            "Performance shams include fixed max-pool capacity, event-count replay, no trophic pressure, no dopamine, and no plasticity.",
            "Active-mask shuffle and lineage-ID shuffle are derived audit artifacts, not independently learning baselines; lineage-ID corruption was detected in 6/6 shuffled runs.",
            "This does not prove hardware lifecycle, native on-chip lifecycle, full adult birth/death turnover, external-baseline superiority, compositionality, or world modeling.",
        ]
    if spec.entry_id == "tier6_4_circuit_motif_causality":
        payload["claim_boundary"] = [
            "Tier 6.4 is controlled software circuit-motif causality evidence, not hardware motif evidence.",
            "The run used NEST, hard_noisy_switching, seeds 42/43/44, regimes life4_16 and life8_32, 960 steps, and a seeded motif-diverse graph before the first outcome feedback.",
            "Intact graphs contained FF/LAT/FB motif edges in both task/regime aggregates and logged 1920 motif-active steps before reward/learning updates.",
            "Four predeclared motif ablation comparisons produced predicted losses, and random/monolithic controls did not dominate intact when recovery and active-population efficiency were included.",
            "Motif-label shuffle behaved identically to intact, so cite this as motif structure/edge-role evidence, not evidence that labels alone carry computational semantics.",
            "This does not prove hardware motif execution, custom-C/on-chip learning, compositionality, world modeling, real-world task usefulness, or superiority over all external baselines.",
        ]
    return payload


def backend_from_manifest(manifest: dict[str, Any]) -> str | None:
    if manifest.get("backend"):
        return str(manifest["backend"])
    summary = manifest.get("summary")
    if isinstance(summary, dict) and summary.get("backend"):
        return str(summary["backend"])
    backend_keys = manifest.get("backend_keys")
    if isinstance(backend_keys, list):
        return ", ".join(str(item) for item in backend_keys)
    return None


def classify_noncanonical(canonical_dirs: set[str]) -> list[dict[str, Any]]:
    entries = []
    for path in sorted(OUTPUT_ROOT.iterdir()):
        if not path.is_dir() or path.name in canonical_dirs:
            continue
        if path.name.startswith("_legacy"):
            role = "legacy_generated_artifacts"
        elif path.name.startswith("_"):
            role = "probe_or_debug"
        elif path.name.startswith("tier") and "fix" in path.name:
            role = "fix_diagnostic"
        elif path.name.startswith("tier") and "debug" in path.name:
            role = "debug_diagnostic"
        elif path.name.startswith("tier4_17b"):
            role = "runtime_parity_diagnostic"
        elif path.name.startswith("tier4_17"):
            role = "runtime_contract_diagnostic"
        elif path.name.startswith("tier4_20a"):
            role = "hardware_transfer_readiness_audit"
        elif path.name.startswith("tier4_20b"):
            role = "v2_1_chunked_hardware_probe"
        elif path.name.startswith("tier5_9c"):
            role = "macro_eligibility_v2_1_recheck"
        elif path.name.startswith("tier5_15"):
            role = "temporal_code_diagnostic"
        elif path.name.startswith("tier5_16"):
            role = "neuron_model_sensitivity_diagnostic"
        elif path.name.startswith("tier5_17b"):
            role = "pre_reward_representation_failure_analysis"
        elif path.name.startswith("tier5_17c"):
            role = "intrinsic_predictive_preexposure_diagnostic"
        elif path.name.startswith("tier5_17d"):
            role = "predictive_binding_preexposure_diagnostic"
        elif path.name.startswith("tier5_17e"):
            role = "predictive_binding_compact_regression_gate"
        elif path.name.startswith("tier5_18c"):
            role = "self_evaluation_compact_regression_gate"
        elif path.name.startswith("tier5_18"):
            role = "self_evaluation_metacognition_diagnostic"
        elif path.name.startswith("tier5_17"):
            role = "pre_reward_representation_diagnostic"
        elif path.name.startswith("tier") and (
            path.name.endswith("_hardware_fail") or path.name.endswith("_run_hardware_fail")
        ):
            role = "failed_hardware_run"
        elif path.name.startswith("tier") and (
            "hardware_pass" in path.name or path.name.endswith("_probe_pass")
        ):
            role = "hardware_probe_pass"
        elif path.name.startswith("tier") and path.name.endswith("_prepared"):
            role = "prepared_capsule"
        elif path.name.startswith("tier"):
            role = "superseded_rerun"
        else:
            role = "unclassified"
        results_files = sorted(path.glob("*results.json"))
        generated = None
        status = "unknown"
        if results_files:
            try:
                manifest = read_json(results_files[0])
                generated = manifest.get("generated_at_utc")
                status = status_from_manifest(manifest)
            except Exception as exc:  # pragma: no cover - defensive registry path
                status = f"unreadable: {exc}"
        entries.append(
            {
                "path": str(path),
                "name": path.name,
                "role": role,
                "status": status,
                "generated_at_utc": generated,
                "results_files": [str(p) for p in results_files],
            }
        )
    return entries


def build_registry() -> dict[str, Any]:
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    entries = []
    integrity = {
        "missing_expected_artifacts": [],
        "failed_criteria": [],
        "latest_manifest_updates": [],
    }
    canonical_dirs = {spec.canonical_dir for spec in SPECS}

    for spec in SPECS:
        run_dir = OUTPUT_ROOT / spec.canonical_dir
        results_path = run_dir / spec.results_file
        report_path = run_dir / spec.report_file
        summary_path = run_dir / spec.summary_file if spec.summary_file else None
        manifest = read_json(results_path)
        status = status_from_manifest(manifest)
        tests = normalize_test_results(manifest)
        missing = [str(path) for path in expected_artifacts(spec) if not path.exists()]
        for missing_path in missing:
            integrity["missing_expected_artifacts"].append(
                {"entry_id": spec.entry_id, "path": missing_path}
            )
        for test in tests:
            if test["criteria"]["failed"]:
                integrity["failed_criteria"].append(
                    {
                        "entry_id": spec.entry_id,
                        "test": test["name"],
                        "failures": test["criteria"]["failures"],
                    }
                )
        entry = {
            "entry_id": spec.entry_id,
            "tier_label": spec.tier_label,
            "plan_position": spec.plan_position,
            "status": status,
            "source_generated_at_utc": manifest.get("generated_at_utc"),
            "canonical_output_dir": str(run_dir),
            "results_json": str(results_path),
            "report_md": str(report_path),
            "summary_csv": str(summary_path) if summary_path else None,
            "harness": spec.harness,
            "evidence_role": spec.evidence_role,
            "claim": spec.claim,
            "caveat": spec.caveat,
            "backend": backend_from_manifest(manifest),
            "selected_tests": manifest.get("selected_tests"),
            "test_results": tests,
            "top_level_metrics": select_scalar_metrics(manifest.get("summary", {})),
            "missing_expected_artifacts": missing,
        }
        entries.append(entry)
        payload = latest_manifest_payload(spec, manifest, entry)
        for manifest_name in spec.latest_manifest_names:
            manifest_path = OUTPUT_ROOT / manifest_name
            previous = None
            if manifest_path.exists():
                try:
                    previous = read_json(manifest_path)
                except Exception:
                    previous = {"unreadable": True}
            write_json(manifest_path, payload)
            integrity["latest_manifest_updates"].append(
                {
                    "path": str(manifest_path),
                    "registry_entry_id": spec.entry_id,
                    "previous_manifest": previous,
                    "new_manifest": payload,
                }
            )

    noncanonical = classify_noncanonical(canonical_dirs)
    registry_status = (
        "pass"
        if all(entry["status"] == "pass" for entry in entries)
        and not integrity["missing_expected_artifacts"]
        and not integrity["failed_criteria"]
        else "needs_attention"
    )
    return {
        "schema_version": "1.0",
        "generated_at_utc": utc_now(),
        "registry_status": registry_status,
        "study_name": "CRA controlled learning and SpiNNaker hardware evidence",
        "evidence_count": len(entries),
        "core_test_count": 12,
        "expanded_test_entry_count": 28,
        "entries": entries,
        "noncanonical_outputs": noncanonical,
        "integrity": integrity,
    }


def write_registry_csv(registry: dict[str, Any]) -> None:
    csv_path = OUTPUT_ROOT / "STUDY_REGISTRY.csv"
    with csv_path.open("w", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "entry_id",
                "tier_label",
                "plan_position",
                "status",
                "source_generated_at_utc",
                "canonical_output_dir",
                "harness",
                "evidence_role",
                "claim",
                "caveat",
                "backend",
                "test_count",
                "missing_expected_artifacts",
            ],
        )
        writer.writeheader()
        for entry in registry["entries"]:
            writer.writerow(
                {
                    "entry_id": entry["entry_id"],
                    "tier_label": entry["tier_label"],
                    "plan_position": entry["plan_position"],
                    "status": entry["status"],
                    "source_generated_at_utc": entry["source_generated_at_utc"],
                    "canonical_output_dir": entry["canonical_output_dir"],
                    "harness": entry["harness"],
                    "evidence_role": entry["evidence_role"],
                    "claim": entry["claim"],
                    "caveat": entry["caveat"],
                    "backend": entry["backend"],
                    "test_count": len(entry["test_results"]),
                    "missing_expected_artifacts": len(entry["missing_expected_artifacts"]),
                }
            )


def status_mark(status: str) -> str:
    return "PASS" if status == "pass" else status.upper()


def artifact_label(path: str | None) -> str:
    if not path:
        return ""
    p = Path(path)
    try:
        return str(p.relative_to(ROOT))
    except ValueError:
        return str(p)


def write_controlled_readme(registry: dict[str, Any]) -> None:
    lines = [
        "# Controlled Test Output Registry",
        "",
        "This directory is generated evidence, not source code. The canonical study",
        "ledger is `STUDY_REGISTRY.json`; the compact table is `STUDY_REGISTRY.csv`.",
        "Older reruns, prepared capsules, debug probes, and baseline-frozen",
        "mechanism bundles outside the formal registry are preserved for audit.",
        "",
        f"- Generated: `{registry['generated_at_utc']}`",
        f"- Registry status: **{status_mark(registry['registry_status'])}**",
        f"- Canonical evidence entries: `{registry['evidence_count']}`",
        f"- Expanded test-entry count: `{registry['expanded_test_entry_count']}` (`12` core tests + `10b` + `4.13` + `4.14` + `4.15` + `5.1` + `5.2` + `5.3` + `5.4` + `4.16a` + `4.16b` + `4.18a` + `5.5` + `5.12a` + `5.12c` + `5.12d` + `6.1` + `6.3` + `6.4`; Tiers `5.6` and `5.7` are tracked as additional reviewer-defense/guardrail evidence bundles)",
        "",
        "## Evidence Categories",
        "",
        "- Canonical registry evidence: rows in this registry and the paper-facing table.",
        "- Baseline-frozen mechanism evidence: passed mechanism/promotion diagnostics with compact regression and a frozen `baselines/CRA_EVIDENCE_BASELINE_vX.Y.*` lock, even when the source bundle is not a canonical registry row.",
        "- Noncanonical diagnostic evidence: useful pass/fail diagnostics that answer a design question but do not freeze a baseline by themselves.",
        "- Failed/parked diagnostic evidence: clean negative evidence retained to prevent p-hacking and explain why a mechanism was not promoted.",
        "- Hardware prepare/probe evidence: run packages and one-off probes that are not hardware claims until reviewed and promoted.",
        "",
        "## Canonical Evidence",
        "",
        "| Entry | Status | Canonical Directory | Claim Boundary |",
        "| --- | --- | --- | --- |",
    ]
    for entry in registry["entries"]:
        rel = artifact_label(entry["canonical_output_dir"])
        lines.append(
            f"| `{entry['entry_id']}` | **{status_mark(entry['status'])}** | `{rel}` | {entry['caveat']} |"
        )
    lines.extend(
        [
            "",
            "## Noncanonical Outputs",
            "",
            "These are retained for audit/debug history. Some source bundles also back",
            "baseline-frozen mechanism claims through `baselines/`; otherwise, do not",
            "cite them as current study results unless promoted in `STUDY_REGISTRY.json`.",
            "",
            "| Path | Role | Status | Generated |",
            "| --- | --- | --- | --- |",
        ]
    )
    for item in registry["noncanonical_outputs"]:
        lines.append(
            f"| `{artifact_label(item['path'])}` | `{item['role']}` | `{item['status']}` | `{item.get('generated_at_utc')}` |"
        )
    lines.extend(
        [
            "",
            "## Integrity",
            "",
            f"- Missing expected artifacts: `{len(registry['integrity']['missing_expected_artifacts'])}`",
            f"- Failed criteria in canonical entries: `{len(registry['integrity']['failed_criteria'])}`",
            "- Latest manifest pointers are regenerated by `python3 experiments/evidence_registry.py`.",
            "",
        ]
    )
    (OUTPUT_ROOT / "README.md").write_text("\n".join(lines))


def write_study_index(registry: dict[str, Any]) -> None:
    lines = [
        "# CRA Study Evidence Index",
        "",
        "This is the source-facing index for the controlled evidence trail. Raw bundles",
        "live under `controlled_test_output/`; each canonical entry below has a JSON",
        "manifest, CSV summary, Markdown report, and plots/provenance where relevant.",
        "",
        "Research narrative companions:",
        "",
        "- `docs/ABSTRACT.md`",
        "- `docs/WHITEPAPER.md`",
        "- `docs/CODEBASE_MAP.md`",
        "",
        f"- Registry generated: `{registry['generated_at_utc']}`",
        f"- Registry status: **{status_mark(registry['registry_status'])}**",
        "- Core validation suite: `12` tests",
        f"- Expanded evidence suite: `{registry['expanded_test_entry_count']}` entries (`10b` hard scaling, `4.13` hardware capsule, `4.14` runtime characterization, `4.15` hardware repeatability, `5.1` external baselines, `5.2` learning curves, `5.3` failure analysis, `5.4` delayed-credit confirmation, `4.16a` repaired delayed-cue hardware repeat, `4.16b` repaired hard-switch hardware repeat, `4.18a` chunked runtime baseline, `5.5` expanded baselines, `5.12a` predictive task-pressure, `5.12c` predictive-context sham repair, `5.12d` predictive-context compact regression, `6.1` software lifecycle/self-scaling, `6.3` lifecycle sham controls, and `6.4` circuit motif causality added; `5.6` and `5.7` are additional tuned-baseline reviewer-defense/guardrail bundles)",
        "",
        "## Canonical Claims",
        "",
        "| Evidence entry | Plan position | Status | What it supports | Boundary |",
        "| --- | --- | --- | --- | --- |",
    ]
    for entry in registry["entries"]:
        lines.append(
            f"| `{entry['entry_id']}` | {entry['plan_position']} | **{status_mark(entry['status'])}** | {entry['claim']} | {entry['caveat']} |"
        )
    lines.extend(
        [
            "",
            "## Canonical Artifacts",
            "",
            "| Evidence entry | Results | Report | Summary CSV |",
            "| --- | --- | --- | --- |",
        ]
    )
    for entry in registry["entries"]:
        lines.append(
            "| "
            f"`{entry['entry_id']}` | "
            f"`{artifact_label(entry['results_json'])}` | "
            f"`{artifact_label(entry['report_md'])}` | "
            f"`{artifact_label(entry['summary_csv'])}` |"
        )
    selected_noncanonical_notes = {
        "tier4_16_20260427_194526_hard_noisy_switching_3seed_hardware_fail": "Clean hard-switch hardware execution, but the learning gate failed; not a Tier 4.16 pass.",
        "tier4_16_20260427_223210_hard_noisy_switching_seed44_probe_pass": "Repaired hard-switch seed-44 hardware probe passed narrowly; authorizes the repaired three-seed rerun, but is not full hard-switch repeatability evidence.",
        "tier4_16b_bridge_repair_orderfix_aligned_nest_20260427": "Aligned NEST bridge-repair diagnostic passes locally and points to hardware transfer/timing.",
        "tier4_16b_bridge_repair_orderfix_aligned_brian2_20260427": "Aligned Brian2 bridge-repair diagnostic passes locally and agrees with the NEST classification.",
        "tier5_12b_20260429_055923": "Failed predictive-context diagnostic; wrong-sign context was learnably informative, so the sham contract was repaired in Tier 5.12c.",
        "tier5_15_20260429_135924": "Passed software temporal-code diagnostic: timing codes carry task information under time-shuffle/rate-only controls; not hardware/on-chip temporal coding or a v2.0 freeze.",
        "tier5_16_20260429_142647": "Passed NEST neuron-parameter sensitivity diagnostic: LIF threshold/tau/refractory/capacitance/synaptic-tau variants remain functional with zero fallback and audited parameter propagation; not hardware/custom-C/on-chip neuron evidence or a v2.0 freeze.",
        "tier5_17_20260429_190501": "Failed pre-reward representation diagnostic: non-oracle exposure had zero label/reward leakage and zero raw dopamine, but the strict no-history-input scaffold did not meet probe, sham-separation, or sample-efficiency promotion gates; representation learning remains unpromoted.",
        "tier5_17b_20260429_191512": "Passed pre-reward representation failure-analysis diagnostic: classifies Tier 5.17 as one positive subcase, one input-encoded/easy task, and one history-baseline-dominated temporal task; points to Tier 5.17c intrinsic predictive/MI preexposure and explicitly does not promote representation learning or revisit Tier 5.9 yet.",
        "tier5_17c_20260429_193147": "Failed intrinsic predictive preexposure diagnostic: zero label/reward leakage and zero dopamine, candidate beat no-preexposure and simple history/reservoir controls, but did not clear probe accuracy or target-shuffled/wrong-domain/STDP-only/best-control gates under held-out episode probes; reward-free representation remains unpromoted.",
        "tier5_17d_20260429_194613": "Passed predictive binding repair diagnostic: zero label/reward leakage and zero dopamine; candidate cleared held-out ambiguous-episode target-shuffled, wrong-domain, history/reservoir, STDP-only, and best-control gates on cross-modal and reentry binding tasks. Bounded pre-reward predictive-binding evidence only, not general unsupervised representation learning or a v2.0 freeze.",
        "tier5_17e_20260429_163058": "Passed predictive-binding compact regression/promotion gate: v1.8 compact regression, v1.9 composition/routing, Tier 5.14 working-memory/context binding, and Tier 5.17d predictive-binding guardrails all passed. Authorizes bounded v2.0 host-side software baseline freeze; not hardware/on-chip representation, general unsupervised concept learning, world modeling, language, planning, AGI, or external-baseline superiority.",
        "tier5_18_20260429_213002": "Passed self-evaluation/metacognitive monitoring diagnostic: pre-feedback uncertainty predicted primary-path errors and hazard/OOD/mismatch state, calibrated confidence passed Brier/ECE gates, and confidence-gated behavior beat v2.0, monitor-only, random, shuffled, disabled, and anti-confidence controls. Noncanonical software diagnostic only; not consciousness, self-awareness, hardware evidence, AGI, or a v2.1 freeze.",
        "tier5_18c_20260429_221045": "Passed self-evaluation compact regression/promotion gate: the full v2.0 compact gate and Tier 5.18 self-evaluation guardrail both passed. Authorizes bounded v2.1 host-side software self-evaluation/reliability-monitoring baseline freeze; not consciousness, self-awareness, hardware evidence, AGI, language, planning, or external-baseline superiority.",
        "tier5_9c_20260429_190503": "Failed macro-eligibility v2.1-era recheck: the full v2.1 guardrail passed, but the residual macro trace still failed trace-ablation separation because normal, shuffled, zero, and no-macro paths remained identical on the delayed-credit harness. Macro eligibility remains parked and should not move to hardware/custom C.",
        "tier4_20a_20260429_195403": "Passed v2.1 hardware-transfer readiness audit: classifies v2.1 mechanisms by chunked-host readiness versus future custom runtime/on-chip blockers. This is an engineering transfer plan only, not hardware evidence; it recommends a one-seed v2.1 chunked hardware probe without macro eligibility.",
        "tier4_20b_20260429_205214_prepared": "Prepared Tier 4.20b v2.1 one-seed chunked hardware probe: seed 42, delayed_cue plus hard_noisy_switching, 1200 steps, N=8, chunk 50, macro eligibility excluded. This is a JobManager run package only, not hardware evidence until returned artifacts pass.",
    }
    selected_noncanonical = [
        item
        for item in registry["noncanonical_outputs"]
        if item["name"] in selected_noncanonical_notes
    ]
    if selected_noncanonical:
        lines.extend(
            [
                "",
                "## Selected Noncanonical Diagnostics",
                "",
                "| Diagnostic | Role | Status | Boundary |",
                "| --- | --- | --- | --- |",
            ]
        )
        for item in sorted(selected_noncanonical, key=lambda x: x["name"]):
            lines.append(
                "| "
                f"`{artifact_label(item['path'])}` | "
                f"`{item['role']}` | "
                f"**{status_mark(item['status'])}** | "
                f"{selected_noncanonical_notes[item['name']]} |"
            )
    lines.extend(
        [
            "",
            "## Alignment Rules",
            "",
            "- Cite only entries listed as canonical in `controlled_test_output/STUDY_REGISTRY.json`.",
            "- Treat `_phase3_probe_*`, superseded timestamped reruns, and quarantine folders as audit history.",
            "- A `PASS` claim requires all canonical criteria to pass and all expected artifacts to exist.",
            "- Tier 4.13 is a real hardware-capsule pass, not a full hardware-scaling claim.",
            "- Tier 4.14 characterizes runtime/provenance overhead; it is not repeatability or scaling evidence.",
            "- Tier 4.15 repeats the minimal hardware capsule across three seeds; it is not a harder-task or hardware-scaling claim.",
            "- Tier 5.1 compares CRA to simple external learners; it documents where baselines beat CRA as well as where CRA has an edge.",
            "- Tier 5.2 shows those Tier 5.1 edges do not strengthen at the 1500-step horizon under the tested settings.",
            "- Tier 5.3 diagnoses the Tier 5.2 weakness and identifies stronger delayed credit as the leading candidate fix, while preserving the boundary that hard switching still trails the best external baseline.",
            "- Tier 5.4 confirms the delayed-credit candidate across 960 and 1500 steps; it authorizes designing a harder hardware capsule but not claiming hard-switch superiority.",
            "- Tier 4.16b bridge repair is local diagnostic evidence only; the canonical hard-switch hardware claim comes from the repaired three-seed Tier 4.16b pass.",
            "- Re-run `python3 experiments/evidence_registry.py` after adding or ingesting a result.",
            "",
            "## Integrity Snapshot",
            "",
            f"- Missing expected artifacts: `{len(registry['integrity']['missing_expected_artifacts'])}`",
            f"- Failed canonical criteria: `{len(registry['integrity']['failed_criteria'])}`",
            f"- Noncanonical output folders preserved: `{len(registry['noncanonical_outputs'])}`",
            "",
        ]
    )
    (ROOT / "STUDY_EVIDENCE_INDEX.md").write_text("\n".join(lines))


def main() -> None:
    registry = build_registry()
    write_json(OUTPUT_ROOT / "STUDY_REGISTRY.json", registry)
    write_registry_csv(registry)
    write_controlled_readme(registry)
    write_study_index(registry)
    print(
        json.dumps(
            {
                "registry_status": registry["registry_status"],
                "evidence_count": registry["evidence_count"],
                "missing_expected_artifacts": len(registry["integrity"]["missing_expected_artifacts"]),
                "failed_criteria": len(registry["integrity"]["failed_criteria"]),
                "noncanonical_outputs": len(registry["noncanonical_outputs"]),
                "outputs": {
                    "registry_json": str(OUTPUT_ROOT / "STUDY_REGISTRY.json"),
                    "registry_csv": str(OUTPUT_ROOT / "STUDY_REGISTRY.csv"),
                    "controlled_readme": str(OUTPUT_ROOT / "README.md"),
                    "study_index": str(ROOT / "STUDY_EVIDENCE_INDEX.md"),
                },
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()

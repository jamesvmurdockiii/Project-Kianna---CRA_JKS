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
        entry_id="tier4_26_four_core_distributed_smoke",
        tier_label="Tier 4.26 - Four-Core Distributed Smoke",
        plan_position="Post-Tier-4.25C multi-core distributed architecture gate",
        canonical_dir="tier4_26_20260502_pass_ingested",
        results_file="tier4_26_hardware_results.json",
        report_file="tier4_26_ingest_report.md",
        summary_file=None,
        harness="experiments/tier4_26_four_core_distributed_smoke.py",
        evidence_role="four-core distributed custom-runtime smoke",
        claim="Four independent SpiNNaker cores can hold distributed context, route, memory, and learning state and cooperate via inter-core SDP lookup request/reply to reproduce the monolithic single-core delayed-credit result within tolerance.",
        caveat="Single-seed seed-42 smoke on one chip only; not speedup evidence, not multi-chip scaling, not a general multi-core framework, and not full native v2.1 autonomy.",
        latest_manifest_names=("tier4_26_latest_manifest.json",),
        expected_extra_files=(
            "tier4_26_ingest_results.json",
            "tier4_26_local_results.json",
            "tier4_26_task.json",
            "tier4_26_target_acquisition.json",
            "tier4_26_environment.json",
            "tier4_26_context_load.json",
            "tier4_26_route_load.json",
            "tier4_26_memory_load.json",
            "tier4_26_learning_load.json",
        ),
    ),
    EvidenceSpec(
        entry_id="tier4_27a_four_core_characterization",
        tier_label="Tier 4.27a - Four-Core Runtime Resource / Timing Characterization",
        plan_position="Post-Tier-4.26 runtime instrumentation and resource envelope gate",
        canonical_dir="tier4_27a_20260502_pass_ingested",
        results_file="tier4_27a_hardware_results.json",
        report_file="tier4_27a_ingest_report.md",
        summary_file=None,
        harness="experiments/tier4_27a_four_core_distributed_smoke.py",
        evidence_role="four-core distributed custom-runtime characterization",
        claim="The four-core SDP scaffold can be instrumented to measure lookup request/reply counts, stale replies, timeouts, schema version, payload bytes, and per-core commands. Hardware execution reproduces the monolithic reference within tolerance while providing counter telemetry.",
        caveat="Single-seed seed-42 smoke on one chip only; not speedup evidence, not multi-chip scaling, not a general multi-core framework, not full native v2.1 autonomy, and not MCPL/multicast. SDP remains transitional.",
        latest_manifest_names=("tier4_27a_latest_manifest.json",),
        expected_extra_files=(
            "tier4_27a_ingest_results.json",
            "tier4_27a_task.json",
            "tier4_27a_target_acquisition.json",
            "tier4_27a_environment.json",
            "tier4_27a_context_load.json",
            "tier4_27a_route_load.json",
            "tier4_27a_memory_load.json",
            "tier4_27a_learning_load.json",
            "tier4_27a_build_context_core_stdout.txt",
            "tier4_27a_build_context_core_stderr.txt",
            "tier4_27a_build_route_core_stdout.txt",
            "tier4_27a_build_route_core_stderr.txt",
            "tier4_27a_build_memory_core_stdout.txt",
            "tier4_27a_build_memory_core_stderr.txt",
            "tier4_27a_build_learning_core_stdout.txt",
            "tier4_27a_build_learning_core_stderr.txt",
        ),
    ),
    EvidenceSpec(
        entry_id="tier4_27e_two_core_mcpl_smoke",
        tier_label="Tier 4.27e - Two-Core MCPL Round-trip Smoke",
        plan_position="Post-Tier-4.27d MCPL compile-time feasibility gate",
        canonical_dir="tier4_27e_20260502_local_pass",
        results_file="tier4_27e_results.json",
        report_file="tier4_27e_report.md",
        summary_file=None,
        harness="experiments/tier4_27e_two_core_mcpl_smoke.py",
        evidence_role="two-core MCPL inter-core lookup local build validation",
        claim="MCPL is fully wired into the distributed lookup state machine: learning core sends requests via multicast payload, state core receives via MCPL callback and replies via MCPL, learning core stores results. Router table init per core role. Local builds pass for both profiles with ITCM under budget.",
        caveat="Local build and wiring validation only. NOT hardware evidence. Router table behavior on actual SpiNNaker chip not yet validated. Multi-state-core (context+route+memory) MCPL routing not yet tested.",
        latest_manifest_names=("tier4_27e_latest_manifest.json",),
        expected_extra_files=(),
    ),
    EvidenceSpec(
        entry_id="tier4_27f_three_core_mcpl_smoke",
        tier_label="Tier 4.27f - Three-State-Core MCPL Lookup Smoke",
        plan_position="Post-Tier-4.27e two-core MCPL round-trip",
        canonical_dir="tier4_27f_20260502_local_pass",
        results_file="tier4_27f_results.json",
        report_file="tier4_27f_report.md",
        summary_file=None,
        harness="experiments/tier4_27f_three_core_mcpl_smoke.py",
        evidence_role="three-state-core MCPL inter-core lookup local build validation",
        claim="MCPL supports three state cores (context/route/memory) replying to a single learning core. Learning core uses a single broad router entry (0xFFFF0000 mask) to catch all reply types. All four profile .aplx images build with MCPL enabled and fit within ITCM budget.",
        caveat="Local build and wiring validation only. NOT hardware evidence. Actual router table behavior with multiple state cores on a single chip not yet validated. SDP-vs-MCPL comparison not yet performed.",
        latest_manifest_names=("tier4_27f_latest_manifest.json",),
        expected_extra_files=(),
    ),
    EvidenceSpec(
        entry_id="tier4_27g_sdp_vs_mcpl_comparison",
        tier_label="Tier 4.27g - SDP-vs-MCPL Protocol Comparison",
        plan_position="Post-Tier-4.27f three-state-core MCPL lookup smoke",
        canonical_dir="tier4_27g_20260502_local_pass",
        results_file="tier4_27g_results.json",
        report_file="tier4_27g_report.md",
        summary_file=None,
        harness="experiments/tier4_27g_sdp_vs_mcpl_comparison.py",
        evidence_role="source-code-based protocol analysis and migration recommendation",
        claim="MCPL reduces per-lookup round-trip from 54 bytes (SDP) to 16 bytes (71% reduction). For 48-event schedule, inter-core lookup traffic drops from ~8,064 bytes to ~2,304 bytes. Latency improves from ~5-20 us (monitor-bound SDP) to ~0.5-2 us (hardware router). MCPL requires 4 router entries but scales better than SDP. Recommendation: make MCPL default for Tier 4.28+.",
        caveat="Source-code analysis only. NOT hardware timing measurements. NOT router-table hardware validation. NOT multi-chip scaling evidence.",
        latest_manifest_names=("tier4_27g_latest_manifest.json",),
        expected_extra_files=(),
    ),
    EvidenceSpec(
        entry_id="tier4_28a_four_core_mcpl_repeatability",
        tier_label="Tier 4.28a - Four-Core MCPL Repeatability",
        plan_position="Post-Tier-4.27g MCPL migration decision",
        canonical_dir="tier4_28a_20260502_mcpl_hardware_pass_ingested",
        results_file="tier4_28a_ingest_results.json",
        report_file="tier4_28a_ingest_report.md",
        summary_file=None,
        harness="experiments/tier4_28a_four_core_mcpl_repeatability.py",
        evidence_role="MCPL-enabled four-core hardware repeatability",
        claim="MCPL-based four-core distributed lookup executes successfully on SpiNNaker hardware across three seeds (42, 43, 44). All 38/38 criteria pass per seed. Zero stale replies, zero timeouts, 144 lookup requests and 144 lookup replies per seed. Learning core readout weight=32768, bias=0, pending=48/48. ITCM sizes: context_core 11248B, route_core 11280B, memory_core 11280B, learning_core 12968B.",
        caveat="Single-chip four-core only; not multi-chip scaling, not speedup evidence, not full v2.1 mechanism transfer, not continuous host-free operation. Host still required for setup and readback. SDP fallback code remains in source but is not the active data plane for v0.1 baseline.",
        latest_manifest_names=("tier4_28a_latest_manifest.json",),
        expected_extra_files=(),
    ),
    EvidenceSpec(
        entry_id="tier4_28b_delayed_cue_four_core_mcpl",
        tier_label="Tier 4.28b - Delayed-Cue Four-Core MCPL Hardware Probe",
        plan_position="Post-Tier-4.28a MCPL repeatability baseline",
        canonical_dir="tier4_28b_20260502_hardware_pass_ingested",
        results_file="tier4_28b_ingest_results.json",
        report_file="tier4_28b_ingest_report.md",
        summary_file=None,
        harness="experiments/tier4_28b_delayed_cue_four_core_mcpl.py",
        evidence_role="delayed-cue task transfer to four-core MCPL scaffold",
        claim="The four-core MCPL distributed scaffold executes a 48-event delayed-cue task (target=-feature) on SpiNNaker hardware. Weight converges to -32769 (~-1.0), bias=-1 (~0). All 38/38 criteria pass. Zero stale replies, zero timeouts, 144 lookup requests/replies.",
        caveat="Single-seed probe (seed 42) on one chip only. Not three-seed repeatability, not multi-chip scaling, not speedup evidence, not full v2.1 mechanism transfer. Host still required for setup and readback.",
        latest_manifest_names=("tier4_28b_latest_manifest.json",),
        expected_extra_files=(),
    ),
    EvidenceSpec(
        entry_id="tier4_28c_delayed_cue_repeatability",
        tier_label="Tier 4.28c - Delayed-Cue Three-Seed Repeatability",
        plan_position="Post-Tier-4.28b delayed-cue hardware probe",
        canonical_dir="tier4_28c_20260503_hardware_pass_ingested",
        results_file="tier4_28c_ingest_results.json",
        report_file="tier4_28c_ingest_report.md",
        summary_file=None,
        harness="experiments/tier4_28c_delayed_cue_repeatability.py",
        evidence_role="three-seed delayed-cue repeatability on four-core MCPL scaffold",
        claim="The four-core MCPL distributed scaffold executes a 48-event delayed-cue task (target=-feature) across seeds 42, 43, and 44. All 38/38 criteria pass per seed. Weight converges to -32769, bias=-1 on all three seeds. Zero stale replies, zero timeouts, 144 lookup requests/replies per seed.",
        caveat="Single-chip four-core only. Not multi-chip scaling, not speedup evidence, not full v2.1 mechanism transfer. Host still required for setup and readback.",
        latest_manifest_names=("tier4_28c_latest_manifest.json",),
        expected_extra_files=(),
    ),
    EvidenceSpec(
        entry_id="tier4_28d_hard_noisy_switching",
        tier_label="Tier 4.28d - Hard Noisy Switching Four-Core MCPL",
        plan_position="Post-Tier-4.28c delayed-cue repeatability",
        canonical_dir="tier4_28d_20260503_hardware_pass_ingested",
        results_file="tier4_28d_ingest_results.json",
        report_file="tier4_28d_ingest_report.md",
        summary_file=None,
        harness="experiments/tier4_28d_hard_noisy_switching_four_core_mcpl.py",
        evidence_role="hard noisy switching task transfer to four-core MCPL scaffold",
        claim="The four-core MCPL distributed scaffold executes a ~62-event hard_noisy_switching task (regime switches, 20% noisy trials, variable delay 3-5) across seeds 42, 43, and 44. All 38/38 criteria pass per seed. Weight converges to 34208 (~+1.04), bias=-1440 (~-0.04) on all three seeds. Zero variance across seeds. Zero stale replies, zero timeouts, 186 lookup requests/replies per seed.",
        caveat="Single-chip four-core only. Host-pre-written regime context; not autonomous regime detection. Not multi-chip scaling, not speedup evidence, not full v2.1 mechanism transfer. Host still required for setup and readback.",
        latest_manifest_names=("tier4_28d_latest_manifest.json",),
        expected_extra_files=(),
    ),
    EvidenceSpec(
        entry_id="tier4_28e_failure_envelope_pointA",
        tier_label="Tier 4.28e - Native Failure-Envelope Report Point A",
        plan_position="Post-Tier-4.28d hard noisy switching probe",
        canonical_dir="tier4_28e_pointA_20260503_hardware_pass_ingested",
        results_file="tier4_28e_ingest_results.json",
        report_file="tier4_28e_ingest_report.md",
        summary_file=None,
        harness="experiments/tier4_28e_native_failure_envelope_report.py",
        evidence_role="failure-envelope characterization - highest-pressure passing config",
        claim="Four-core MCPL runtime passes at schedule limit (64 events) with delay=1, noise=0.6. All 38/38 criteria pass. Weight=-3225, bias=8530. Pending=64/64, lookups=192/192, stale=0, timeouts=0. Host reference updated to exact hardware timing (one-tick MCPL lookup latency).",
        caveat="Single-chip four-core only. Host-pre-written regime context. Not multi-chip scaling, not speedup evidence, not full v2.1 mechanism transfer. Point A is one of three probe points (A/B/C) in the failure-envelope report.",
        latest_manifest_names=("tier4_28e_pointA_latest_manifest.json",),
        expected_extra_files=(),
    ),
    EvidenceSpec(
        entry_id="tier4_28e_failure_envelope_pointC",
        tier_label="Tier 4.28e - Native Failure-Envelope Report Point C",
        plan_position="Post-Tier-4.28d hard noisy switching probe",
        canonical_dir="tier4_28e_pointC_20260503_hardware_pass_ingested",
        results_file="tier4_28e_ingest_results.json",
        report_file="tier4_28e_ingest_report.md",
        summary_file=None,
        harness="experiments/tier4_28e_native_failure_envelope_report.py",
        evidence_role="failure-envelope characterization - high-pending-pressure passing config",
        claim="Four-core MCPL runtime passes with high pending pressure (max_concurrent_pending=10) and longer delays (delay=7-10), noise=0.2, 43 events. All 38/38 criteria pass. Weight=101376, bias=5120, exact 0% error vs reference. Pending=43/43, lookups=129/129, stale=0, timeouts=0. Confirms safe operation well below schedule limit with accurate exact-HW-timing reference.",
        caveat="Single-chip four-core only. Host-pre-written regime context. Not multi-chip scaling, not speedup evidence, not full v2.1 mechanism transfer. Point C is one of three probe points (A/B/C) in the failure-envelope report.",
        latest_manifest_names=("tier4_28e_pointC_latest_manifest.json",),
        expected_extra_files=(),
    ),
    EvidenceSpec(
        entry_id="tier4_29a_native_keyed_memory_overcapacity",
        tier_label="Tier 4.29a - Native Keyed-Memory Overcapacity Gate",
        plan_position="Post-Tier-4.28e failure envelope / Phase C mechanism migration",
        canonical_dir="tier4_29a_20260503_hardware_pass_ingested",
        results_file="tier4_29a_multi_seed_ingest_summary.json",
        report_file="tier4_29a_ingest_report.md",
        summary_file="tier4_29a_combined_results.json",
        harness="experiments/tier4_29a_native_keyed_memory_overcapacity_gate.py",
        evidence_role="native mechanism migration - keyed memory with controls",
        claim="Native four-core MCPL runtime handles keyed context memory with wrong-key, overwrite, and slot-shuffle controls across seeds 42, 43, 44 on three different boards. All 47/47 criteria pass per seed (141/141 total). Weight=32768, bias=0, pending=32/32, active_pending=0, decisions=32, reward_events=32, lookup_requests=96, lookup_replies=96, stale=0, timeouts=0, context hits=26, misses=6, active_slots=8, slot_writes=9. Exact parity with local reference on all three seeds.",
        caveat="Single-chip four-core only. Host-pre-written keyed context slots. Schedule-driven (not true continuous generation). Not multi-chip scaling, not speedup evidence, not full v2.1 mechanism transfer. MAX_SCHEDULE_ENTRIES=512 allows longer task streams but still uses pre-loaded static schedule.",
        latest_manifest_names=("tier4_29a_latest_manifest.json",),
        expected_extra_files=(
            "tier4_29a_environment.json",
            "tier4_29a_task.json",
            "tier4_29a_target_acquisition.json",
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
    EvidenceSpec(
        entry_id="tier4_29b_native_routing_composition_gate",
        tier_label="Tier 4.29b - Native Routing/Composition Gate",
        plan_position="Phase C mechanism migration: native keyed context + route composition",
        canonical_dir="tier4_29b_20260503_hardware_pass_ingested",
        results_file="tier4_29b_results.json",
        report_file="tier4_29b_report.md",
        summary_file="tier4_29b_summary.csv",
        harness="experiments/tier4_29b_native_routing_composition_gate.py",
        evidence_role="native routing/composition hardware benchmark",
        claim="Native keyed context * route composition works on real SpiNNaker across three seeds on three different boards with explicit wrong-context, wrong-route, overwrite, and host-composed sham controls.",
        caveat="Native routing/composition hardware evidence only; not speedup evidence, not multi-chip scaling, not a general multi-core framework, not full native v2.1 autonomy, and not true continuous generation.",
        latest_manifest_names=("tier4_29b_latest_manifest.json",),
        expected_extra_files=(
            "tier4_29b_combined_results.json",
            "tier4_29b_multi_seed_ingest_summary.json",
            "tier4_29b_hardware_results.json",
            "tier4_29b_task.json",
            "tier4_29b_environment.json",
            "tier4_29b_target_acquisition.json",
            "tier4_29b_context_load.json",
            "tier4_29b_route_load.json",
            "tier4_29b_memory_load.json",
            "tier4_29b_learning_load.json",
            "tier4_29b_reports.zip",
        ),
    ),
    EvidenceSpec(
        entry_id="tier4_29c_native_predictive_binding",
        tier_label="Tier 4.29c - Native Predictive Binding Bridge",
        plan_position="Phase C mechanism migration: native predictive binding",
        canonical_dir="tier4_29c_20260504_pass_ingested",
        results_file="tier4_29c_ingest_results.json",
        report_file="tier4_29c_report_seed42.json",
        summary_file="tier4_29c_combined_results.json",
        harness="experiments/tier4_29c_native_predictive_binding_bridge.py",
        evidence_role="native predictive binding hardware benchmark",
        claim="Native four-core runtime separates prediction target from reward target before outcome on real SpiNNaker across three seeds on three different boards. All 24/24 criteria pass per seed (72/72 total). Full-context prediction weight=30912, bias=-1856; zero-context prediction weight=0, bias=0. Confidence parity confirms prediction-before-reward isolation.",
        caveat="Native predictive binding hardware evidence only; not speedup evidence, not multi-chip scaling, not full native v2.1 autonomy, not continuous generation, and not general task learning.",
        latest_manifest_names=("tier4_29c_latest_manifest.json",),
        expected_extra_files=(
            "tier4_29c_hardware_results_seed42.json",
            "tier4_29c_hardware_results_seed43.json",
            "tier4_29c_hardware_results_seed44.json",
            "tier4_29c_task_seed42.json",
            "reports.zip",
        ),
    ),
    EvidenceSpec(
        entry_id="tier4_29d_native_self_evaluation",
        tier_label="Tier 4.29d - Native Self-Evaluation Bridge",
        plan_position="Phase C mechanism migration: native confidence-gated learning",
        canonical_dir="tier4_29d_20260504_pass_ingested",
        results_file="tier4_29d_ingest_results.json",
        report_file="tier4_29d_report_seed44.json",
        summary_file="tier4_29d_combined_results.json",
        harness="experiments/tier4_29d_native_self_evaluation_bridge.py",
        evidence_role="native self-evaluation hardware benchmark",
        claim="Native four-core runtime gates learning by composite confidence (context × route × memory) on real SpiNNaker across three seeds on three different boards. All 30/30 criteria pass per seed (90/90 total). Full confidence weight=30912, bias=-1856; zero confidence weight=0, bias=0; zero-context confidence weight=0, bias=0; half-context confidence weight=28093, bias=3517. MCPL lookup lacks confidence transmission; SDP used instead.",
        caveat="Native confidence-gated learning hardware evidence only; not speedup evidence, not multi-chip scaling, not full native v2.1 autonomy, not continuous generation, not dynamic lifecycle, and not external-baseline superiority.",
        latest_manifest_names=("tier4_29d_latest_manifest.json",),
        expected_extra_files=(
            "tier4_29d_task_full_confidence.json",
            "tier4_29d_task_zero_confidence.json",
            "tier4_29d_task_zero_context_confidence.json",
            "tier4_29d_task_half_context_confidence.json",
        ),
    ),
    EvidenceSpec(
        entry_id="tier4_29e_native_replay_consolidation",
        tier_label="Tier 4.29e - Native Replay/Consolidation Bridge",
        plan_position="Phase C mechanism migration: native host-scheduled replay/consolidation",
        canonical_dir="tier4_29e_20260505_pass_ingested",
        results_file="tier4_29e_ingest_results.json",
        report_file="tier4_29e_report.md",
        summary_file="tier4_29e_combined_results.json",
        harness="experiments/tier4_29e_native_replay_consolidation_bridge.py",
        evidence_role="native replay/consolidation hardware benchmark",
        claim="Host-scheduled replay/consolidation events run through native four-core state primitives on real SpiNNaker across three seeds on three different boards. All 38/38 criteria pass per seed (114/114 total). Correct replay changes readout weight versus no replay, wrong-key replay blocks weight consolidation, and random-event replay stays distinct from correct replay.",
        caveat="Native host-scheduled replay/consolidation bridge evidence only; not native on-chip replay buffers, not biological sleep, not speedup evidence, not multi-chip scaling, not full native autonomy, and not external-baseline superiority.",
        latest_manifest_names=("tier4_29e_latest_manifest.json",),
        expected_extra_files=(
            "tier4_29e_hardware_results_seed42.json",
            "tier4_29e_hardware_results_seed43.json",
            "tier4_29e_hardware_results_seed44.json",
            "tier4_29e_task_no_replay.json",
            "tier4_29e_task_correct_replay.json",
            "tier4_29e_task_wrong_key_replay.json",
            "tier4_29e_task_random_event_replay.json",
            "reports.zip",
        ),
    ),
    EvidenceSpec(
        entry_id="tier4_29f_compact_native_mechanism_regression",
        tier_label="Tier 4.29f - Compact Native Mechanism Regression",
        plan_position="Phase C mechanism migration: cumulative native bridge freeze gate",
        canonical_dir="tier4_29f_20260505_native_mechanism_regression",
        results_file="tier4_29f_results.json",
        report_file="tier4_29f_report.md",
        summary_file="tier4_29f_summary.csv",
        harness="experiments/tier4_29f_compact_native_mechanism_regression.py",
        evidence_role="native mechanism bridge evidence-regression guardrail",
        claim="The canonical hardware evidence for native keyed memory, routing/composition, predictive binding, confidence gating, and host-scheduled replay/consolidation remains complete and internally aligned. All 113/113 evidence-regression criteria pass.",
        caveat="Evidence-regression gate over already-ingested real hardware passes; not a new hardware execution, not a single monolithic all-mechanism task, not lifecycle/self-scaling evidence, not multi-chip scaling, and not speedup evidence.",
        latest_manifest_names=("tier4_29f_latest_manifest.json",),
        expected_extra_files=(),
    ),
    EvidenceSpec(
        entry_id="tier7_0_standard_dynamical_benchmarks",
        tier_label="Tier 7.0 - Standard Dynamical Benchmark Suite",
        plan_position="Phase E standard benchmark diagnostics: software-only sequence benchmark harness",
        canonical_dir="tier7_0_20260505_standard_dynamical_benchmarks",
        results_file="tier7_0_results.json",
        report_file="tier7_0_report.md",
        summary_file="tier7_0_summary.csv",
        harness="experiments/tier7_0_standard_dynamical_benchmarks.py",
        evidence_role="standard dynamical benchmark diagnostic",
        claim="The Tier 7.0 software benchmark harness completed Mackey-Glass, Lorenz, NARMA10, and aggregate geometric-mean MSE across CRA v2.1 and standard causal sequence baselines. It diagnosed CRA v2.1 online underperformance on these continuous-valued dynamical regression benchmarks: CRA ranked 5/5 by aggregate geomean MSE, while the echo-state network was best.",
        caveat="Software diagnostic evidence only; not hardware evidence, not a superiority claim, not a tuning run, not a new baseline freeze, and not evidence that CRA is generally weak outside these continuous-regression benchmarks. It triggers Tier 7.0b failure analysis before mechanism changes or hardware migration.",
        latest_manifest_names=("tier7_0_latest_manifest.json",),
        expected_extra_files=(
            "tier7_0_aggregate.csv",
            "tier7_0_fairness_contract.json",
        ),
    ),
    EvidenceSpec(
        entry_id="tier7_0b_continuous_regression_failure_analysis",
        tier_label="Tier 7.0b - Continuous-Regression Failure Analysis",
        plan_position="Phase E standard benchmark diagnostics: CRA continuous-regression gap localization",
        canonical_dir="tier7_0b_20260505_continuous_regression_failure_analysis",
        results_file="tier7_0b_results.json",
        report_file="tier7_0b_report.md",
        summary_file="tier7_0b_summary.csv",
        harness="experiments/tier7_0b_continuous_regression_failure_analysis.py",
        evidence_role="standard benchmark failure-analysis diagnostic",
        claim="Tier 7.0b localized the Tier 7.0 continuous-regression gap to a recoverable state-signal/default-readout failure. A leakage-safe ridge probe over CRA internal state improved aggregate geomean MSE from raw CRA 1.2233 to 0.4433, and CRA state plus the same causal lag budget improved to 0.0544; shuffled-target state control remained worse at 0.7533.",
        caveat="Software diagnostic evidence only; not a tuning run, not a promoted mechanism, not hardware evidence, not a new baseline freeze, and not proof that a repaired CRA will beat standard baselines. It authorizes a bounded continuous readout/interface repair tier before hardware migration.",
        latest_manifest_names=("tier7_0b_latest_manifest.json",),
        expected_extra_files=(
            "tier7_0b_aggregate.csv",
            "tier7_0b_fairness_contract.json",
            "tier7_0b_feature_inventory.csv",
            "tier7_0b_probe_timeseries.csv",
        ),
    ),
    EvidenceSpec(
        entry_id="tier7_0c_continuous_readout_repair",
        tier_label="Tier 7.0c - Bounded Continuous Readout / Interface Repair",
        plan_position="Phase E standard benchmark diagnostics: bounded readout repair candidate",
        canonical_dir="tier7_0c_20260505_continuous_readout_repair",
        results_file="tier7_0c_results.json",
        report_file="tier7_0c_report.md",
        summary_file="tier7_0c_summary.csv",
        harness="experiments/tier7_0c_continuous_readout_repair.py",
        evidence_role="standard benchmark repair diagnostic",
        claim="Tier 7.0c converted the Tier 7.0b state-signal diagnosis into a bounded online continuous readout/interface repair candidate. The best repair improved aggregate geomean MSE over raw CRA by 6.424x and beat shuffled/frozen controls, but lag-only online LMS still performed better and explains most of the benchmark gain.",
        caveat="Software repair-candidate evidence only; not hardware evidence, not a new baseline freeze, not a promoted CRA mechanism, and not a superiority claim. The correct next move is a stricter state-specific repair or claim narrowing, not hardware migration.",
        latest_manifest_names=("tier7_0c_latest_manifest.json",),
        expected_extra_files=(
            "tier7_0c_aggregate.csv",
            "tier7_0c_fairness_contract.json",
            "tier7_0c_timeseries.csv",
        ),
    ),
    EvidenceSpec(
        entry_id="tier7_0d_state_specific_continuous_interface",
        tier_label="Tier 7.0d - State-Specific Continuous Interface / Claim-Narrowing",
        plan_position="Phase E standard benchmark diagnostics: lag-regression claim-narrowing gate",
        canonical_dir="tier7_0d_20260505_state_specific_continuous_interface",
        results_file="tier7_0d_results.json",
        report_file="tier7_0d_report.md",
        summary_file="tier7_0d_summary.csv",
        harness="experiments/tier7_0d_state_specific_continuous_interface.py",
        evidence_role="standard benchmark claim-narrowing diagnostic",
        claim="Tier 7.0d tested whether CRA state adds value beyond causal lag regression on Mackey-Glass, Lorenz, and NARMA10. It passed 10/10 integrity criteria and classified the benchmark path as lag-regression explained: train-prefix ridge lag-only beat lag+state probes, the best state-specific online candidate only marginally beat lag-only, and shuffled residual controls matched or exceeded the candidate.",
        caveat="Software diagnostic evidence only; not hardware evidence, not a baseline freeze, not a promoted continuous-readout mechanism, and not a superiority claim. The Tier 7 continuous-regression benchmark path should be narrowed and not migrated to hardware unless a future mechanism changes the failure class.",
        latest_manifest_names=("tier7_0d_latest_manifest.json",),
        expected_extra_files=(
            "tier7_0d_aggregate.csv",
            "tier7_0d_fairness_contract.json",
            "tier7_0d_timeseries.csv",
        ),
    ),
    EvidenceSpec(
        entry_id="tier7_0e_standard_dynamical_v2_2_length_sweep",
        tier_label="Tier 7.0e - Standard Dynamical Benchmark Rerun With v2.2 And Run-Length Sweep",
        plan_position="Phase H software usefulness: standard benchmark training-budget test",
        canonical_dir="tier7_0e_20260508_length_calibration",
        results_file="tier7_0e_results.json",
        report_file="tier7_0e_report.md",
        summary_file="tier7_0e_summary.csv",
        harness="experiments/tier7_0e_standard_dynamical_v2_2_sweep.py",
        evidence_role="standard benchmark rerun / length-calibration evidence",
        claim="Tier 7.0e showed v2.2 materially improves over raw CRA v2.1 at 720 and 2000 steps but remains noncompetitive with the strongest ESN public baseline.",
        caveat="Software benchmark evidence only; the 10k public aggregate was separately blocked by a non-finite NARMA10 seed-44 stream and no baseline freeze, hardware transfer, or superiority claim is authorized.",
        latest_manifest_names=("tier7_0e_latest_manifest.json",),
        expected_extra_files=(
            "tier7_0e_fairness_contract.json",
            "tier7_0e_model_aggregate.csv",
        ),
    ),
    EvidenceSpec(
        entry_id="tier5_19a_temporal_substrate_reference",
        tier_label="Tier 5.19a - Local Temporal-Substrate Reference",
        plan_position="Phase E temporal dynamics repair: local fading-memory reference",
        canonical_dir="tier5_19a_20260505_temporal_substrate_reference",
        results_file="tier5_19a_results.json",
        report_file="tier5_19a_report.md",
        summary_file="tier5_19a_summary.csv",
        harness="experiments/tier5_19a_temporal_substrate_reference.py",
        evidence_role="temporal-substrate repair diagnostic",
        claim="A bounded fading-memory temporal-state candidate improves the held-out long-memory diagnostic and motivates a sharper recurrence/sham gate.",
        caveat="Software local-reference evidence only; recurrence-specific value, hardware transfer, and benchmark superiority remain unproven.",
        latest_manifest_names=("tier5_19a_latest_manifest.json",),
        expected_extra_files=(
            "tier5_19a_aggregate.csv",
            "tier5_19a_fairness_contract.json",
            "tier5_19a_timeseries.csv",
        ),
    ),
    EvidenceSpec(
        entry_id="tier5_19b_temporal_substrate_gate",
        tier_label="Tier 5.19b - Temporal-Substrate Benchmark/Sham Gate",
        plan_position="Phase E temporal dynamics repair: fading-memory sham separation",
        canonical_dir="tier5_19b_20260505_temporal_substrate_gate",
        results_file="tier5_19b_results.json",
        report_file="tier5_19b_report.md",
        summary_file="tier5_19b_summary.csv",
        harness="experiments/tier5_19b_temporal_substrate_gate.py",
        evidence_role="temporal-substrate benchmark/sham gate",
        claim="Fading-memory temporal state remains supported under benchmark/sham pressure while bounded nonlinear recurrence remains unproven.",
        caveat="Software diagnostic evidence only; does not freeze a baseline or prove native/on-chip temporal dynamics.",
        latest_manifest_names=("tier5_19b_latest_manifest.json",),
        expected_extra_files=(
            "tier5_19b_aggregate.csv",
            "tier5_19b_fairness_contract.json",
            "tier5_19b_timeseries.csv",
        ),
    ),
    EvidenceSpec(
        entry_id="tier5_19c_fading_memory_regression",
        tier_label="Tier 5.19c - Fading-Memory Narrowing / Compact Regression",
        plan_position="Phase E temporal dynamics repair: v2.2 software freeze gate",
        canonical_dir="tier5_19c_20260505_fading_memory_regression",
        results_file="tier5_19c_results.json",
        report_file="tier5_19c_report.md",
        summary_file="tier5_19c_summary.csv",
        harness="experiments/tier5_19c_fading_memory_regression.py",
        evidence_role="software baseline promotion/regression gate",
        claim="Bounded fading-memory temporal state is promoted as CRA software baseline v2.2 after compact regression passes.",
        caveat="Software evidence only; not bounded nonlinear recurrence, native/on-chip temporal dynamics, universal benchmark superiority, language, planning, AGI, or ASI.",
        latest_manifest_names=("tier5_19c_latest_manifest.json",),
        expected_extra_files=(
            "tier5_19c_aggregate.csv",
            "tier5_19c_fairness_contract.json",
            "tier5_19c_task_diagnostics.json",
            "tier5_19c_timeseries.csv",
        ),
    ),
    EvidenceSpec(
        entry_id="tier7_0f_benchmark_protocol_failure_localization",
        tier_label="Tier 7.0f - Benchmark Protocol Repair / Public Failure Localization",
        plan_position="Phase H software usefulness: benchmark protocol repair and gap localization",
        canonical_dir="tier7_0f_20260508_benchmark_protocol_failure_localization",
        results_file="tier7_0f_results.json",
        report_file="tier7_0f_report.md",
        summary_file="tier7_0f_summary.csv",
        harness="experiments/tier7_0f_benchmark_protocol_failure_localization.py",
        evidence_role="benchmark-protocol / public gap localization evidence",
        claim="Tier 7.0f confirmed the 10k NARMA10 seed-44 finite-stream blocker, selected 8000 as the largest same-seed finite rerun length, and localized the remaining public benchmark gap to ESN/offline readout dominance on Mackey-Glass/Lorenz and explicit lag-memory dominance on NARMA10.",
        caveat="Diagnostic protocol evidence only; not a CRA performance improvement, not a new mechanism, not a baseline freeze, not hardware evidence, and not public benchmark superiority.",
        latest_manifest_names=("tier7_0f_latest_manifest.json",),
        expected_extra_files=(
            "tier7_0f_fairness_contract.json",
            "tier7_0f_gap_table.csv",
            "tier7_0f_narma_scan.csv",
        ),
    ),
    EvidenceSpec(
        entry_id="tier7_0g_general_mechanism_selection_contract",
        tier_label="Tier 7.0g - General Mechanism-Selection Contract",
        plan_position="Phase H software usefulness: measured-gap mechanism selection",
        canonical_dir="tier7_0g_20260508_general_mechanism_selection_contract",
        results_file="tier7_0g_results.json",
        report_file="tier7_0g_report.md",
        summary_file="tier7_0g_summary.csv",
        harness="experiments/tier7_0g_general_mechanism_selection_contract.py",
        evidence_role="public-gap mechanism-selection contract",
        claim="Tier 7.0g selected bounded nonlinear recurrent continuous-state/interface repair as the next planned mechanism because the measured public benchmark gap is nonlinear recurrent state and readout-interface strength, not sleep/replay, lifecycle, or hardware transfer.",
        caveat="Contract evidence only; not mechanism implementation, not a performance improvement, not a baseline freeze, not hardware evidence, and not public benchmark superiority.",
        latest_manifest_names=("tier7_0g_latest_manifest.json",),
        expected_extra_files=(
            "tier7_0g_contract.json",
        ),
    ),
    EvidenceSpec(
        entry_id="tier7_0h_bounded_recurrent_interface_gate",
        tier_label="Tier 7.0h - Bounded Nonlinear Recurrent Continuous-State / Interface Gate",
        plan_position="Phase H software usefulness: public-scoreboard bounded recurrence gate",
        canonical_dir="tier7_0h_20260508_bounded_recurrent_interface_gate",
        results_file="tier7_0h_results.json",
        report_file="tier7_0h_report.md",
        summary_file="tier7_0h_summary.csv",
        harness="experiments/tier7_0h_bounded_recurrent_interface_gate.py",
        evidence_role="public benchmark mechanism gate with recurrence shams",
        claim="Tier 7.0h showed the bounded nonlinear recurrent continuous-state candidate materially improves the valid 8000-step public scoreboard versus v2.2 and beats lag/reservoir online controls, but recurrence/topology specificity remains unproven because the permuted-recurrence sham stayed too close.",
        caveat="Software evidence only; not a baseline freeze, not hardware evidence, not ESN superiority, not native on-chip recurrence, and not public benchmark superiority.",
        latest_manifest_names=("tier7_0h_latest_manifest.json",),
        expected_extra_files=(
            "tier7_0h_fairness_contract.json",
            "tier7_0h_model_aggregate.csv",
        ),
    ),
    EvidenceSpec(
        entry_id="tier7_0i_recurrence_topology_specificity_gate",
        tier_label="Tier 7.0i - Recurrence / Topology Specificity Repair Gate",
        plan_position="Phase H software usefulness: recurrence topology-specificity falsification gate",
        canonical_dir="tier7_0i_20260508_recurrence_topology_specificity_gate",
        results_file="tier7_0i_results.json",
        report_file="tier7_0i_report.md",
        summary_file="tier7_0i_summary.csv",
        harness="experiments/tier7_0i_recurrence_topology_specificity_gate.py",
        evidence_role="public benchmark topology-specificity falsification / claim-narrowing gate",
        claim="Tier 7.0i showed generic bounded recurrent state remains useful on the public benchmark scoreboard, but topology-specific recurrence is not supported because stricter topology shams and no-recurrence controls matched or beat the structured candidate.",
        caveat="Software evidence only; not a baseline freeze, not hardware evidence, not ESN superiority, not native on-chip recurrence, and not a topology-specific recurrence claim.",
        latest_manifest_names=("tier7_0i_latest_manifest.json",),
        expected_extra_files=(
            "tier7_0i_fairness_contract.json",
            "tier7_0i_model_aggregate.csv",
        ),
    ),
    EvidenceSpec(
        entry_id="tier7_0j_generic_recurrent_promotion_gate",
        tier_label="Tier 7.0j - Generic Bounded Recurrent-State Promotion / Compact Regression",
        plan_position="Phase H software usefulness: v2.3 generic recurrent-state promotion gate",
        canonical_dir="tier7_0j_20260508_generic_recurrent_promotion_gate",
        results_file="tier7_0j_results.json",
        report_file="tier7_0j_report.md",
        summary_file="tier7_0j_summary.csv",
        harness="experiments/tier7_0j_generic_recurrent_promotion_gate.py",
        evidence_role="software baseline promotion/regression gate",
        claim="Tier 7.0j promoted the narrowed generic bounded recurrent continuous-state interface as software baseline v2.3 after the locked 8000-step public scoreboard and full NEST compact regression passed.",
        caveat="Software evidence only; not topology-specific recurrence, not ESN superiority, not hardware evidence, not native/on-chip recurrence, not language, planning, AGI, or ASI.",
        latest_manifest_names=("tier7_0j_latest_manifest.json",),
        expected_extra_files=(
            "tier7_0j_fairness_contract.json",
        ),
    ),
    EvidenceSpec(
        entry_id="tier6_2a_targeted_usefulness_validation",
        tier_label="Tier 6.2a - Targeted Hard-Task Validation Over v2.3",
        plan_position="Phase H software usefulness: targeted diagnostic validation after v2.3 freeze",
        canonical_dir="tier6_2a_20260508_targeted_usefulness_validation",
        results_file="tier6_2a_results.json",
        report_file="tier6_2a_report.md",
        summary_file="tier6_2a_summary.csv",
        harness="experiments/tier6_2a_targeted_usefulness_validation.py",
        evidence_role="diagnostic hard-task validation / failure localization",
        claim="Tier 6.2a showed frozen v2.3 has a narrow targeted signal on variable-delay multi-cue diagnostics, but v2.2 remains stronger on the aggregate hard-task geomean and no new baseline or hardware transfer is authorized.",
        caveat="Software diagnostic evidence only; custom hard tasks cannot make the public usefulness claim, and the result is not a baseline freeze, hardware evidence, native transfer, ESN superiority, or AGI/ASI evidence.",
        latest_manifest_names=("tier6_2a_latest_manifest.json",),
        expected_extra_files=(
            "tier6_2a_fairness_contract.json",
            "tier6_2a_aggregate.csv",
            "tier6_2a_aggregate_summary.csv",
            "tier6_2a_task_profiles.csv",
        ),
    ),
    EvidenceSpec(
        entry_id="tier7_1a_realish_adapter_contract",
        tier_label="Tier 7.1a - Real-ish/Public Adapter Contract",
        plan_position="Phase H software usefulness: first public adapter contract after Tier 6.2a",
        canonical_dir="tier7_1a_20260508_realish_adapter_contract",
        results_file="tier7_1a_results.json",
        report_file="tier7_1a_report.md",
        summary_file="tier7_1a_summary.csv",
        harness="experiments/tier7_1a_realish_adapter_contract.py",
        evidence_role="public/real-ish adapter contract",
        claim="Tier 7.1a selected NASA C-MAPSS remaining-useful-life streaming as the first real-ish/public adapter family to test the Tier 6.2a variable-delay signal under fixed sources, splits, metrics, baselines, and leakage controls.",
        caveat="Contract evidence only; not a dataset run, not public usefulness evidence, not a baseline freeze, not hardware/native transfer, and not AGI/ASI evidence.",
        latest_manifest_names=("tier7_1a_latest_manifest.json",),
        expected_extra_files=(
            "tier7_1a_contract.json",
            "tier7_1a_source_audit.csv",
        ),
    ),
    EvidenceSpec(
        entry_id="tier7_1b_cmapss_source_data_preflight",
        tier_label="Tier 7.1b - NASA C-MAPSS Source/Data Preflight",
        plan_position="Phase H software usefulness: public adapter source/data preflight after Tier 7.1a",
        canonical_dir="tier7_1b_20260508_cmapss_source_data_preflight",
        results_file="tier7_1b_results.json",
        report_file="tier7_1b_report.md",
        summary_file="tier7_1b_summary.csv",
        harness="experiments/tier7_1b_cmapss_source_data_preflight.py",
        evidence_role="public dataset access/schema/leakage preflight",
        claim="Tier 7.1b verified NASA C-MAPSS FD001 source access, checksum manifest, schema, train/test/RUL parse, train-only normalization, prediction-before-update stream ordering, and label-separated tiny smoke artifacts.",
        caveat="Preflight evidence only; not C-MAPSS scoring, not public usefulness evidence, not a baseline freeze, not hardware/native transfer, and not AGI/ASI evidence.",
        latest_manifest_names=("tier7_1b_latest_manifest.json",),
        expected_extra_files=(
            "tier7_1b_source_manifest.json",
            "tier7_1b_source_manifest.csv",
            "tier7_1b_fd001_profile.json",
            "tier7_1b_normalization_stats.json",
            "tier7_1b_smoke_stream_preview.csv",
            "tier7_1b_smoke_scoring_labels.csv",
        ),
    ),
    EvidenceSpec(
        entry_id="tier7_1c_cmapss_fd001_scoring_gate",
        tier_label="Tier 7.1c - Compact C-MAPSS FD001 Scoring Gate",
        plan_position="Phase H software usefulness: first public adapter compact scoring after Tier 7.1b",
        canonical_dir="tier7_1c_20260508_cmapss_fd001_scoring_gate",
        results_file="tier7_1c_results.json",
        report_file="tier7_1c_report.md",
        summary_file="tier7_1c_summary.csv",
        harness="experiments/tier7_1c_cmapss_fd001_scoring_gate.py",
        evidence_role="compact public-adapter scoring / failure localization",
        claim="Tier 7.1c scored v2.2, v2.3, fair scalar baselines, and v2.3 shams on leakage-safe NASA C-MAPSS FD001 rows; v2.3 ranked 5th and did not show public-adapter advantage under this compact PCA1 scoring gate.",
        caveat="Compact scalar-adapter software evidence only; not a full C-MAPSS benchmark, not a public usefulness win, not a baseline freeze, not hardware/native transfer, and not AGI/ASI evidence.",
        latest_manifest_names=("tier7_1c_latest_manifest.json",),
        expected_extra_files=(
            "tier7_1c_model_metrics.csv",
            "tier7_1c_model_summary.csv",
            "tier7_1c_per_unit_metrics.csv",
            "tier7_1c_scoring_contract.json",
        ),
    ),
    EvidenceSpec(
        entry_id="tier7_1d_cmapss_failure_analysis_adapter_repair",
        tier_label="Tier 7.1d - C-MAPSS Failure Analysis / Adapter Repair",
        plan_position="Phase H software usefulness: public adapter failure localization after Tier 7.1c",
        canonical_dir="tier7_1d_20260508_cmapss_failure_analysis_adapter_repair",
        results_file="tier7_1d_results.json",
        report_file="tier7_1d_report.md",
        summary_file="tier7_1d_summary.csv",
        harness="experiments/tier7_1d_cmapss_failure_analysis_adapter_repair.py",
        evidence_role="public-adapter failure analysis / adapter repair",
        claim="Tier 7.1d localized the compact C-MAPSS FD001 gap: capped RUL and ridge readout substantially repaired scalar v2.3 scoring, multichannel state was sham-separated but did not beat the scalar repair or fair public baselines, and no freeze or hardware transfer was authorized.",
        caveat="Software failure-analysis evidence only; not a full C-MAPSS benchmark, not a public usefulness win, not a promoted mechanism, not a baseline freeze, not hardware/native transfer, and not AGI/ASI evidence.",
        latest_manifest_names=("tier7_1d_latest_manifest.json",),
        expected_extra_files=(
            "tier7_1d_model_metrics.csv",
            "tier7_1d_model_summary.csv",
            "tier7_1d_per_unit_metrics.csv",
            "tier7_1d_factor_analysis.csv",
            "tier7_1d_selected_channels.csv",
        ),
    ),
    EvidenceSpec(
        entry_id="tier7_1e_cmapss_capped_readout_fairness_confirmation",
        tier_label="Tier 7.1e - C-MAPSS Capped-RUL/Readout Fairness Confirmation",
        plan_position="Phase H software usefulness: statistical confirmation after Tier 7.1d",
        canonical_dir="tier7_1e_20260508_cmapss_capped_readout_fairness_confirmation",
        results_file="tier7_1e_results.json",
        report_file="tier7_1e_report.md",
        summary_file="tier7_1e_summary.csv",
        harness="experiments/tier7_1e_cmapss_capped_readout_fairness_confirmation.py",
        evidence_role="public-adapter fairness/statistical confirmation",
        claim="Tier 7.1e tested whether the tiny Tier 7.1d v2.2 capped-ridge C-MAPSS signal was statistically meaningful. It was not confirmed against the lag-multichannel ridge baseline under paired per-unit bootstrap analysis.",
        caveat="Statistical/fairness confirmation over Tier 7.1d per-unit results only; not a full C-MAPSS benchmark, not a public usefulness win, not a promoted mechanism, not a baseline freeze, not hardware/native transfer, and not AGI/ASI evidence.",
        latest_manifest_names=("tier7_1e_latest_manifest.json",),
        expected_extra_files=("tier7_1e_paired_comparisons.csv",),
    ),
    EvidenceSpec(
        entry_id="tier7_1f_next_public_adapter_contract",
        tier_label="Tier 7.1f - Next Public Adapter Contract / Family Selection",
        plan_position="Phase H software usefulness: next public adapter contract after C-MAPSS non-promotion",
        canonical_dir="tier7_1f_20260508_next_public_adapter_contract",
        results_file="tier7_1f_results.json",
        report_file="tier7_1f_report.md",
        summary_file="tier7_1f_summary.csv",
        harness="experiments/tier7_1f_next_public_adapter_contract.py",
        evidence_role="public-adapter contract / family selection",
        claim="Tier 7.1f selected Numenta NAB streaming anomaly detection as the next public adapter family after the compact C-MAPSS path was not confirmed.",
        caveat="Contract/family-selection evidence only; not a NAB data preflight, not scoring, not public usefulness evidence, not a baseline freeze, not hardware/native transfer, and not AGI/ASI evidence.",
        latest_manifest_names=("tier7_1f_latest_manifest.json",),
        expected_extra_files=("tier7_1f_source_contract.csv",),
    ),
    EvidenceSpec(
        entry_id="tier7_1g_nab_source_data_scoring_preflight",
        tier_label="Tier 7.1g - NAB Source/Data/Scoring Preflight",
        plan_position="Phase H software usefulness: NAB source/data/scoring preflight after Tier 7.1f",
        canonical_dir="tier7_1g_20260508_nab_source_data_scoring_preflight",
        results_file="tier7_1g_results.json",
        report_file="tier7_1g_report.md",
        summary_file="tier7_1g_summary.csv",
        harness="experiments/tier7_1g_nab_source_data_scoring_preflight.py",
        evidence_role="public anomaly dataset access/schema/leakage/scoring-interface preflight",
        claim="Tier 7.1g verified a pinned official NAB source commit, cached source/data/label files, parsed selected streams and anomaly windows, produced label-separated chronological smoke streams, and documented the compact NAB scoring-interface contract.",
        caveat="Preflight evidence only; not NAB scoring, not public usefulness evidence, not a baseline freeze, not hardware/native transfer, and not AGI/ASI evidence.",
        latest_manifest_names=("tier7_1g_latest_manifest.json",),
        expected_extra_files=(
            "tier7_1g_source_manifest.json",
            "tier7_1g_source_manifest.csv",
            "tier7_1g_selected_files.csv",
            "tier7_1g_smoke_stream.csv",
            "tier7_1g_label_windows.csv",
            "tier7_1g_smoke_anomaly_scores.csv",
            "tier7_1g_scoring_interface_contract.json",
        ),
    ),
    EvidenceSpec(
        entry_id="tier7_1h_compact_nab_scoring_gate",
        tier_label="Tier 7.1h - Compact NAB Scoring Gate",
        plan_position="Phase H software usefulness: compact NAB scoring after Tier 7.1g",
        canonical_dir="tier7_1h_20260508_compact_nab_scoring_gate",
        results_file="tier7_1h_results.json",
        report_file="tier7_1h_report.md",
        summary_file="tier7_1h_summary.csv",
        harness="experiments/tier7_1h_compact_nab_scoring_gate.py",
        evidence_role="compact public anomaly scoring / confirmation-needed signal",
        claim="Tier 7.1h scored CRA v2.2/v2.3, fair online anomaly baselines, and v2.3 shams on the pinned compact NAB subset. v2.3 ranked second, beat v2.2 and shams, but did not beat the fixed random-reservoir online residual baseline, so the result is a partial signal requiring broader confirmation.",
        caveat="Compact software scoring only; not a full NAB benchmark, not public usefulness proof by itself, not a baseline freeze, not hardware/native transfer, and not AGI/ASI evidence.",
        latest_manifest_names=("tier7_1h_latest_manifest.json",),
        expected_extra_files=(
            "tier7_1h_model_metrics.csv",
            "tier7_1h_model_summary.csv",
            "tier7_1h_thresholds.csv",
            "tier7_1h_score_preview.csv",
            "tier7_1h_bootstrap.csv",
            "tier7_1h_scoring_contract.json",
        ),
    ),
    EvidenceSpec(
        entry_id="tier5_20a_resonant_branch_polyp_diagnostic",
        tier_label="Tier 5.20a - Resonant Branch Polyp Internal-Model Diagnostic",
        plan_position="Mechanism-side diagnostic after Tier 7.1f and before any core polyp replacement",
        canonical_dir="tier5_20a_20260508_resonant_branch_polyp_diagnostic",
        results_file="tier5_20a_results.json",
        report_file="tier5_20a_report.md",
        summary_file="tier5_20a_summary.csv",
        harness="experiments/tier5_20a_resonant_branch_polyp_diagnostic.py",
        evidence_role="optional polyp internal-model diagnostic",
        claim="Tier 5.20a tested a same-budget resonant LIF-branch proxy for the 16 excitatory neurons inside each polyp. The harness passed, but the candidate was not promoted because it regressed several tasks versus v2.3 despite localized value on variable-delay and anomaly diagnostics.",
        caveat="Software diagnostic only; not a core polyp replacement, not hardware evidence, not a promoted mechanism, not a baseline freeze, and not AGI/ASI evidence.",
        latest_manifest_names=("tier5_20a_latest_manifest.json",),
        expected_extra_files=(
            "tier5_20a_aggregate.csv",
            "tier5_20a_aggregate_summary.csv",
            "tier5_20a_branch_contract.json",
        ),
    ),
    EvidenceSpec(
        entry_id="tier5_20b_hybrid_resonant_polyp_diagnostic",
        tier_label="Tier 5.20b - Hybrid Resonant/LIF Polyp Diagnostic",
        plan_position="Mechanism-side repair diagnostic after the Tier 5.20a full-resonant non-promotion",
        canonical_dir="tier5_20b_20260508_hybrid_resonant_polyp_diagnostic",
        results_file="tier5_20b_results.json",
        report_file="tier5_20b_report.md",
        summary_file="tier5_20b_summary.csv",
        harness="experiments/tier5_20b_hybrid_resonant_polyp_diagnostic.py",
        evidence_role="optional hybrid polyp internal-model diagnostic",
        claim="Tier 5.20b tested same-budget 8 LIF / 8 resonant and 12 LIF / 4 resonant hybrid polyp proxies. The harness passed, but neither hybrid was promoted because both retained material regressions versus v2.3 and did not separate sufficiently from shams.",
        caveat="Software repair diagnostic only; not a core polyp replacement, not hardware evidence, not a promoted mechanism, not a baseline freeze, and not AGI/ASI evidence.",
        latest_manifest_names=("tier5_20b_latest_manifest.json",),
        expected_extra_files=(
            "tier5_20b_aggregate.csv",
            "tier5_20b_aggregate_summary.csv",
            "tier5_20b_hybrid_contract.json",
        ),
    ),
    EvidenceSpec(
        entry_id="tier5_20c_minimal_resonant_polyp_diagnostic",
        tier_label="Tier 5.20c - Minimal Hybrid Resonant/LIF Polyp Diagnostic",
        plan_position="Mechanism-side minimal-dose diagnostic after Tier 5.20b hybrid non-promotion",
        canonical_dir="tier5_20c_20260508_minimal_resonant_polyp_diagnostic",
        results_file="tier5_20c_results.json",
        report_file="tier5_20c_report.md",
        summary_file="tier5_20c_summary.csv",
        harness="experiments/tier5_20c_minimal_resonant_polyp_diagnostic.py",
        evidence_role="optional minimal-dose polyp internal-model diagnostic",
        claim="Tier 5.20c tested a same-budget 14 LIF / 2 resonant hybrid polyp proxy. The harness passed, but the candidate was not promoted because it produced no task wins versus v2.3 and no sham-separated tasks.",
        caveat="Software minimal-dose diagnostic only; not a core polyp replacement, not hardware evidence, not a promoted mechanism, not a baseline freeze, and not AGI/ASI evidence.",
        latest_manifest_names=("tier5_20c_latest_manifest.json",),
        expected_extra_files=(
            "tier5_20c_aggregate.csv",
            "tier5_20c_aggregate_summary.csv",
            "tier5_20c_minimal_contract.json",
        ),
    ),
    EvidenceSpec(
        entry_id="tier5_20d_resonant_heavy_polyp_diagnostic",
        tier_label="Tier 5.20d - Resonant-Heavy Hybrid LIF Polyp Diagnostic",
        plan_position="Mechanism-side resonant-heavy diagnostic after Tier 5.20c minimal-dose non-promotion",
        canonical_dir="tier5_20d_20260508_resonant_heavy_polyp_diagnostic",
        results_file="tier5_20d_results.json",
        report_file="tier5_20d_report.md",
        summary_file="tier5_20d_summary.csv",
        harness="experiments/tier5_20d_resonant_heavy_polyp_diagnostic.py",
        evidence_role="optional resonant-heavy polyp internal-model diagnostic",
        claim="Tier 5.20d tested the reverse 12/4 split: a same-budget 4 LIF / 12 resonant hybrid polyp proxy. The harness passed and showed localized task value, but the candidate was not promoted because material regressions and aggregate loss versus v2.3 remained.",
        caveat="Software resonant-heavy diagnostic only; not a core polyp replacement, not hardware evidence, not a promoted mechanism, not a baseline freeze, and not AGI/ASI evidence.",
        latest_manifest_names=("tier5_20d_latest_manifest.json",),
        expected_extra_files=(
            "tier5_20d_aggregate.csv",
            "tier5_20d_aggregate_summary.csv",
            "tier5_20d_resonant_heavy_contract.json",
        ),
    ),
    EvidenceSpec(
        entry_id="tier5_20e_near_full_resonant_polyp_diagnostic",
        tier_label="Tier 5.20e - Near-Full Resonant Hybrid LIF Polyp Diagnostic",
        plan_position="Mechanism-side near-full resonant diagnostic closing the Tier 5.20 dose sweep",
        canonical_dir="tier5_20e_20260508_near_full_resonant_polyp_diagnostic",
        results_file="tier5_20e_results.json",
        report_file="tier5_20e_report.md",
        summary_file="tier5_20e_summary.csv",
        harness="experiments/tier5_20e_near_full_resonant_polyp_diagnostic.py",
        evidence_role="optional near-full resonant polyp internal-model diagnostic",
        claim="Tier 5.20e tested a same-budget 2 LIF / 14 resonant hybrid polyp proxy. The harness passed and showed localized task value, but the candidate was not promoted because material regressions and aggregate loss versus v2.3 remained.",
        caveat="Software near-full resonant diagnostic only; not a core polyp replacement, not hardware evidence, not a promoted mechanism, not a baseline freeze, and not AGI/ASI evidence.",
        latest_manifest_names=("tier5_20e_latest_manifest.json",),
        expected_extra_files=(
            "tier5_20e_aggregate.csv",
            "tier5_20e_aggregate_summary.csv",
            "tier5_20e_near_full_resonant_contract.json",
        ),
    ),
    EvidenceSpec(
        entry_id="tier4_30_readiness_lifecycle_native_audit",
        tier_label="Tier 4.30-readiness - Lifecycle-Native Preflight / Layering Audit",
        plan_position="Phase E lifecycle-native path selection before implementation",
        canonical_dir="tier4_30_readiness_20260505_lifecycle_native_audit",
        results_file="tier4_30_readiness_results.json",
        report_file="tier4_30_readiness_report.md",
        summary_file=None,
        harness="experiments/tier4_30_readiness_audit.py",
        evidence_role="lifecycle-native readiness audit",
        claim="Initial lifecycle-native work should layer on CRA_NATIVE_MECHANISM_BRIDGE_v0.3 with v2.2 as software reference only, using static-pool lifecycle constraints.",
        caveat="Engineering audit only; not lifecycle implementation, not hardware evidence, not speedup, not multi-chip scaling, and not native v2.2 temporal migration.",
        latest_manifest_names=("tier4_30_readiness_latest_manifest.json",),
        expected_extra_files=(
            "tier4_30_lifecycle_controls.csv",
            "tier4_30_lifecycle_fields.csv",
        ),
    ),
    EvidenceSpec(
        entry_id="tier4_30_lifecycle_native_contract",
        tier_label="Tier 4.30 - Lifecycle-Native Static-Pool Contract",
        plan_position="Phase E lifecycle-native contract before reference/runtime work",
        canonical_dir="tier4_30_20260505_lifecycle_native_contract",
        results_file="tier4_30_contract_results.json",
        report_file="tier4_30_contract_report.md",
        summary_file=None,
        harness="experiments/tier4_30_lifecycle_native_contract.py",
        evidence_role="lifecycle-native static-pool contract",
        claim="Tier 4.30 defines the lifecycle init/event/trophic/readback/sham command schema, readback fields, event semantics, gate sequence, and failure classes for static-pool lifecycle migration.",
        caveat="Local engineering contract only; not runtime implementation, not hardware evidence, not lifecycle/self-scaling proof, and not v2.2 temporal migration.",
        latest_manifest_names=("tier4_30_latest_manifest.json",),
        expected_extra_files=(
            "tier4_30_command_schema.csv",
            "tier4_30_event_semantics.csv",
            "tier4_30_failure_classes.csv",
            "tier4_30_gate_sequence.csv",
            "tier4_30_readback_schema.csv",
        ),
    ),
    EvidenceSpec(
        entry_id="tier4_30a_static_pool_lifecycle_reference",
        tier_label="Tier 4.30a - Local Static-Pool Lifecycle Reference",
        plan_position="Phase E lifecycle-native deterministic local reference",
        canonical_dir="tier4_30a_20260505_static_pool_lifecycle_reference",
        results_file="tier4_30a_results.json",
        report_file="tier4_30a_report.md",
        summary_file="tier4_30a_control_summary.csv",
        harness="experiments/tier4_30a_static_pool_lifecycle_reference.py",
        evidence_role="lifecycle static-pool local reference",
        claim="The Tier 4.30 static-pool lifecycle contract has deterministic 8-slot/2-founder reference traces with exact active-mask, lineage, event-count, checksum, and sham-control outputs.",
        caveat="Local deterministic reference only; not runtime C, not hardware evidence, not task benefit, not lifecycle baseline freeze, and not v2.2 temporal-state migration.",
        latest_manifest_names=("tier4_30a_latest_manifest.json",),
        expected_extra_files=(
            "tier4_30a_event_trace.csv",
            "tier4_30a_final_state.csv",
        ),
    ),
    EvidenceSpec(
        entry_id="tier4_30b_lifecycle_runtime_source_audit",
        tier_label="Tier 4.30b - Lifecycle Runtime Source Audit",
        plan_position="Phase E lifecycle-native runtime source/schema gate before hardware smoke",
        canonical_dir="tier4_30b_20260505_lifecycle_source_audit",
        results_file="tier4_30b_results.json",
        report_file="tier4_30b_report.md",
        summary_file=None,
        harness="experiments/tier4_30b_lifecycle_source_audit.py",
        evidence_role="lifecycle runtime source/schema audit",
        claim="The lifecycle static-pool state surface exists in the custom runtime, matches Tier 4.30a reference checksums in host tests, preserves existing profile/readback tests, and is ready for a single-core hardware mask/lineage smoke.",
        caveat="Local source/runtime host evidence only; not hardware evidence, not task-effect evidence, not multi-core lifecycle migration, and not a baseline freeze.",
        latest_manifest_names=("tier4_30b_latest_manifest.json",),
        expected_extra_files=("tier4_30b_command_log.txt",),
    ),
    EvidenceSpec(
        entry_id="tier4_30b_hw_lifecycle_smoke",
        tier_label="Tier 4.30b-hw - Single-Core Lifecycle Active-Mask/Lineage Hardware Smoke",
        plan_position="Phase E lifecycle-native single-core hardware smoke",
        canonical_dir="tier4_30b_hw_20260505_hardware_pass_ingested",
        results_file="tier4_30b_hw_results.json",
        report_file="tier4_30b_hw_report.md",
        summary_file=None,
        harness="experiments/tier4_30b_lifecycle_hardware_smoke.py",
        evidence_role="single-core lifecycle hardware smoke",
        claim="The lifecycle static-pool metadata surface executed on real SpiNNaker with compact lifecycle readback and exact canonical/boundary state parity after correcting a known runner criterion defect.",
        caveat="Hardware smoke only; not lifecycle task benefit, not multi-core lifecycle migration, not speedup, not multi-chip scaling, and not a lifecycle baseline freeze.",
        latest_manifest_names=("tier4_30b_hw_latest_manifest.json",),
    ),
    EvidenceSpec(
        entry_id="tier4_30c_multicore_lifecycle_split",
        tier_label="Tier 4.30c - Multi-Core Lifecycle State Split",
        plan_position="Phase E lifecycle-native multi-core split contract/reference",
        canonical_dir="tier4_30c_20260505_multicore_lifecycle_split",
        results_file="tier4_30c_results.json",
        report_file="tier4_30c_report.md",
        summary_file="tier4_30c_scenario_summary.csv",
        harness="experiments/tier4_30c_multicore_lifecycle_split.py",
        evidence_role="multi-core lifecycle split contract/reference",
        claim="Lifecycle state ownership can be split across context, route, memory, learning, and lifecycle roles with explicit MCPL/multicast lifecycle messages, active-mask sync, and reference parity.",
        caveat="Local contract/reference evidence only; not C runtime implementation, not EBRAINS hardware evidence, not lifecycle task benefit, and not a lifecycle baseline freeze.",
        latest_manifest_names=("tier4_30c_latest_manifest.json",),
        expected_extra_files=(
            "tier4_30c_core_roles.csv",
            "tier4_30c_failure_classes.csv",
            "tier4_30c_message_contract.csv",
            "tier4_30c_split_trace.csv",
        ),
    ),
    EvidenceSpec(
        entry_id="tier4_30d_lifecycle_runtime_source_audit",
        tier_label="Tier 4.30d - Multi-Core Lifecycle Runtime Source Audit",
        plan_position="Phase E lifecycle-native runtime source/local C gate before multi-core hardware smoke",
        canonical_dir="tier4_30d_20260505_lifecycle_runtime_source_audit",
        results_file="tier4_30d_results.json",
        report_file="tier4_30d_report.md",
        summary_file=None,
        harness="experiments/tier4_30d_lifecycle_runtime_source_audit.py",
        evidence_role="multi-core lifecycle runtime source/local C audit",
        claim="The custom runtime source surface represents the Tier 4.30c five-core lifecycle split with a dedicated lifecycle_core profile, lifecycle MCPL stubs/counters, ownership guards, and local C host tests.",
        caveat="Local source/runtime host evidence only; not EBRAINS hardware evidence, not task benefit, not speedup, not multi-chip scaling, not v2.2 temporal migration, and not a lifecycle baseline freeze.",
        latest_manifest_names=("tier4_30d_latest_manifest.json",),
        expected_extra_files=(
            "tier4_30d_command_log.txt",
            "tier4_30d_source_checks.csv",
        ),
    ),
    EvidenceSpec(
        entry_id="tier4_30e_multicore_lifecycle_hardware_smoke",
        tier_label="Tier 4.30e - Multi-Core Lifecycle Hardware Smoke",
        plan_position="Phase E lifecycle-native five-profile hardware smoke before sham-control subset",
        canonical_dir="tier4_30e_hw_20260505_hardware_pass_ingested",
        results_file="tier4_30e_hw_results.json",
        report_file="tier4_30e_hw_report.md",
        summary_file=None,
        harness="experiments/tier4_30e_multicore_lifecycle_hardware_smoke.py",
        evidence_role="multi-core lifecycle hardware smoke",
        claim="The five-profile lifecycle runtime surface built, loaded, and executed on real SpiNNaker with profile ownership guards, duplicate/stale lifecycle rejection, and exact canonical/boundary lifecycle parity.",
        caveat="Hardware smoke only; not lifecycle task benefit, not lifecycle sham-control success, not speedup, not multi-chip scaling, not v2.2 temporal migration, and not a lifecycle baseline freeze.",
        latest_manifest_names=("tier4_30e_hw_latest_manifest.json",),
        expected_extra_files=(
            "returned_artifacts/tier4_30e_hw_task_result.json",
            "returned_artifacts/tier4_30e_hw_target_acquisition.json",
            "returned_artifacts/tier4_30e_hw_context_load.json",
            "returned_artifacts/tier4_30e_hw_route_load.json",
            "returned_artifacts/tier4_30e_hw_memory_load.json",
            "returned_artifacts/tier4_30e_hw_learning_load.json",
            "returned_artifacts/tier4_30e_hw_lifecycle_load.json",
        ),
    ),
    EvidenceSpec(
        entry_id="tier4_30f_lifecycle_sham_hardware_subset",
        tier_label="Tier 4.30f - Lifecycle Sham-Control Hardware Subset",
        plan_position="Phase E lifecycle-native sham-control hardware subset before task-benefit bridge",
        canonical_dir="tier4_30f_hw_20260505_hardware_pass_ingested",
        results_file="tier4_30f_hw_results.json",
        report_file="tier4_30f_hw_report.md",
        summary_file=None,
        harness="experiments/tier4_30f_lifecycle_sham_hardware_subset.py",
        evidence_role="multi-core lifecycle hardware sham controls",
        claim="The five-profile lifecycle runtime executed the enabled lifecycle path and five predeclared sham-control modes on real SpiNNaker with exact expected summaries, no fallback, and preserved returned build/load/readback artifacts.",
        caveat="Hardware sham-control subset only; not lifecycle task benefit, not autonomous lifecycle-to-learning MCPL, not speedup, not multi-chip scaling, not v2.2 temporal migration, and not a lifecycle baseline freeze.",
        latest_manifest_names=("tier4_30f_hw_latest_manifest.json",),
        expected_extra_files=(
            "returned_artifacts/tier4_30f_hw_task_result.json",
            "returned_artifacts/tier4_30f_hw_target_acquisition.json",
            "returned_artifacts/tier4_30f_hw_context_load.json",
            "returned_artifacts/tier4_30f_hw_route_load.json",
            "returned_artifacts/tier4_30f_hw_memory_load.json",
            "returned_artifacts/tier4_30f_hw_learning_load.json",
            "returned_artifacts/tier4_30f_hw_lifecycle_load.json",
            "returned_artifacts/tier4_30f_hw_enabled_events.csv",
            "returned_artifacts/tier4_30f_hw_fixed_static_pool_control_events.csv",
            "returned_artifacts/tier4_30f_hw_random_event_replay_control_events.csv",
            "returned_artifacts/tier4_30f_hw_active_mask_shuffle_control_events.csv",
            "returned_artifacts/tier4_30f_hw_no_trophic_pressure_control_events.csv",
            "returned_artifacts/tier4_30f_hw_no_dopamine_or_plasticity_control_events.csv",
        ),
    ),
    EvidenceSpec(
        entry_id="tier4_30g_lifecycle_task_benefit_resource_bridge",
        tier_label="Tier 4.30g - Lifecycle Task-Benefit / Resource Bridge",
        plan_position="Phase E lifecycle-native local task-benefit/resource bridge before hardware package",
        canonical_dir="tier4_30g_20260506_lifecycle_task_benefit_resource_bridge",
        results_file="tier4_30g_results.json",
        report_file="tier4_30g_report.md",
        summary_file="tier4_30g_mode_summary.csv",
        harness="experiments/tier4_30g_lifecycle_task_benefit_resource_bridge.py",
        evidence_role="lifecycle task-benefit bridge contract/reference",
        claim="A bounded lifecycle-derived feature bridge locally separates the enabled lifecycle mode from sham controls on a compact delayed task and declares the resource/readback contract required before hardware packaging.",
        caveat="Local contract/reference evidence only; not a hardware task-benefit pass, not autonomous lifecycle-to-learning MCPL, not multi-chip scaling, and not a lifecycle baseline freeze.",
        latest_manifest_names=("tier4_30g_latest_manifest.json",),
        expected_extra_files=(
            "tier4_30g_bridge_features.csv",
            "tier4_30g_task_trace.csv",
            "tier4_30g_resource_accounting.csv",
        ),
    ),
    EvidenceSpec(
        entry_id="tier4_30g_lifecycle_task_benefit_hardware_bridge",
        tier_label="Tier 4.30g-hw - Lifecycle Task-Benefit / Resource Bridge Hardware",
        plan_position="Phase E lifecycle-native hardware task-benefit/resource bridge before lifecycle-native baseline freeze",
        canonical_dir="tier4_30g_hw_20260505_hardware_pass_ingested",
        results_file="tier4_30g_hw_results.json",
        report_file="tier4_30g_hw_report.md",
        summary_file=None,
        harness="experiments/tier4_30g_lifecycle_task_benefit_resource_bridge.py",
        evidence_role="lifecycle task-benefit/resource bridge hardware pass",
        claim="The five-profile lifecycle runtime connected enabled lifecycle state into a bounded task-bearing path on real SpiNNaker while five predeclared lifecycle controls closed the task gate, with returned resource/readback accounting and zero failed criteria.",
        caveat="Hardware task-benefit/resource bridge only; host ferries the lifecycle gate into the task path. Not autonomous lifecycle-to-learning MCPL, not speedup, not multi-chip scaling, not v2.2 temporal migration, and not full organism autonomy.",
        latest_manifest_names=("tier4_30g_hw_latest_manifest.json",),
        expected_extra_files=(
            "returned_artifacts/tier4_30g_hw_task_result.json",
            "returned_artifacts/tier4_30g_hw_target_acquisition.json",
            "returned_artifacts/tier4_30g_hw_context_load.json",
            "returned_artifacts/tier4_30g_hw_route_load.json",
            "returned_artifacts/tier4_30g_hw_memory_load.json",
            "returned_artifacts/tier4_30g_hw_learning_load.json",
            "returned_artifacts/tier4_30g_hw_lifecycle_load.json",
            "returned_artifacts/tier4_30g_hw_resource_accounting.csv",
            "returned_artifacts/tier4_30g_hw_enabled_lifecycle_events.csv",
            "returned_artifacts/tier4_30g_hw_fixed_static_pool_control_lifecycle_events.csv",
            "returned_artifacts/tier4_30g_hw_random_event_replay_control_lifecycle_events.csv",
            "returned_artifacts/tier4_30g_hw_active_mask_shuffle_control_lifecycle_events.csv",
            "returned_artifacts/tier4_30g_hw_no_trophic_pressure_control_lifecycle_events.csv",
            "returned_artifacts/tier4_30g_hw_no_dopamine_or_plasticity_control_lifecycle_events.csv",
        ),
    ),
    EvidenceSpec(
        entry_id="tier4_31a_native_temporal_substrate_readiness",
        tier_label="Tier 4.31a - Native Temporal-Substrate Readiness",
        plan_position="Phase F native v2.2 temporal-state migration readiness before local fixed-point reference",
        canonical_dir="tier4_31a_20260506_native_temporal_substrate_readiness",
        results_file="tier4_31a_results.json",
        report_file="tier4_31a_report.md",
        summary_file=None,
        harness="experiments/tier4_31a_native_temporal_substrate_readiness.py",
        evidence_role="native temporal-substrate readiness contract",
        claim="The smallest defensible chip-owned subset for the v2.2 fading-memory mechanism is predeclared as seven causal fixed-point EMA traces with derived deltas/novelty, compact readback, controls, resource budget, proposed command codes, and failure classes before implementation.",
        caveat="Local readiness/contract evidence only; not C runtime implementation, not SpiNNaker hardware evidence, not speedup, not multi-chip scaling, not nonlinear recurrence, not universal benchmark superiority, and not a new baseline freeze.",
        latest_manifest_names=("tier4_31a_latest_manifest.json",),
        expected_extra_files=(
            "tier4_31a_state_subset.csv",
            "tier4_31a_equations.csv",
            "tier4_31a_readback_schema.csv",
            "tier4_31a_controls.csv",
            "tier4_31a_resource_budget.csv",
            "tier4_31a_failure_classes.csv",
            "tier4_31a_fixed_point_table.csv",
        ),
    ),
    EvidenceSpec(
        entry_id="tier4_31b_native_temporal_fixed_point_reference",
        tier_label="Tier 4.31b - Native Temporal-Substrate Local Fixed-Point Reference",
        plan_position="Phase F native v2.2 temporal-state migration fixed-point reference before C/runtime implementation",
        canonical_dir="tier4_31b_20260506_native_temporal_fixed_point_reference",
        results_file="tier4_31b_results.json",
        report_file="tier4_31b_report.md",
        summary_file="tier4_31b_summary.csv",
        harness="experiments/tier4_31b_native_temporal_fixed_point_reference.py",
        evidence_role="native temporal-substrate fixed-point local reference",
        claim="The seven-EMA fixed-point temporal trace mirror matches the Tier 5.19c floating fading-memory reference within tolerance, separates lag/zero/frozen/shuffled/reset/shuffled-target/no-plasticity controls, and documents a no-saturation ±2 trace-bound refinement before C/runtime implementation.",
        caveat="Local fixed-point reference/parity evidence only; not C runtime implementation, not SpiNNaker hardware evidence, not speedup, not multi-chip scaling, not nonlinear recurrence, not universal benchmark superiority, and not a new baseline freeze.",
        latest_manifest_names=("tier4_31b_latest_manifest.json",),
        expected_extra_files=(
            "tier4_31b_aggregate.csv",
            "tier4_31b_diagnostics.json",
            "tier4_31b_trace_errors.csv",
            "tier4_31b_trace_readback_mirror.csv",
            "tier4_31b_timeseries.csv",
        ),
    ),
    EvidenceSpec(
        entry_id="tier4_31c_native_temporal_runtime_source_audit",
        tier_label="Tier 4.31c - Native Temporal-Substrate Runtime Source Audit",
        plan_position="Phase F native v2.2 temporal-state migration source/runtime implementation before hardware smoke",
        canonical_dir="tier4_31c_20260506_native_temporal_runtime_source_audit",
        results_file="tier4_31c_results.json",
        report_file="tier4_31c_report.md",
        summary_file="tier4_31c_summary.csv",
        harness="experiments/tier4_31c_native_temporal_runtime_source_audit.py",
        evidence_role="native temporal-substrate source/runtime host audit",
        claim="The custom C runtime now owns the seven-EMA fixed-point temporal subset from Tier 4.31b with versioned state, compact readback, behavior-backed sham modes, profile ownership guards, and local C host tests before any EBRAINS upload.",
        caveat="Local source/runtime host evidence only; not SpiNNaker hardware evidence, not speedup, not multi-chip scaling, not nonlinear recurrence, not native replay/sleep, not native macro eligibility, not universal benchmark superiority, and not a new baseline freeze.",
        latest_manifest_names=("tier4_31c_latest_manifest.json",),
        expected_extra_files=(
            "tier4_31c_command_log.txt",
            "tier4_31c_source_checks.csv",
        ),
    ),
    EvidenceSpec(
        entry_id="tier4_31d_native_temporal_hardware_smoke",
        tier_label="Tier 4.31d-hw - Native Temporal-Substrate Hardware Smoke",
        plan_position="Phase F native v2.2 temporal-state migration one-board hardware smoke",
        canonical_dir="tier4_31d_hw_20260506_hardware_pass_ingested",
        results_file="tier4_31d_hw_results.json",
        report_file="tier4_31d_hw_report.md",
        summary_file="tier4_31d_hw_summary.csv",
        harness="experiments/tier4_31d_native_temporal_hardware_smoke.py",
        evidence_role="native temporal-substrate one-board hardware smoke",
        claim="The custom C runtime's seven-EMA temporal-state subset built, loaded, executed, and read back on one real SpiNNaker board with compact 48-byte temporal payloads and enabled/zero/frozen/reset sham controls all matching the fixed-point reference.",
        caveat="One-board hardware smoke only; not repeatability, not speedup, not benchmark superiority, not multi-chip scaling, not nonlinear recurrence, not native replay/sleep, not native macro eligibility, not full v2.2 hardware transfer, and not a baseline freeze.",
        latest_manifest_names=("tier4_31d_hw_latest_manifest.json",),
        expected_extra_files=(
            "returned_artifacts/tier4_31d_aplx_build_stdout.txt",
            "returned_artifacts/tier4_31d_aplx_build_stderr.txt",
            "returned_artifacts/tier4_31d_hw_build.json",
            "returned_artifacts/tier4_31d_hw_comparisons.csv",
            "returned_artifacts/tier4_31d_hw_environment.json",
            "returned_artifacts/tier4_31d_hw_expected.json",
            "returned_artifacts/tier4_31d_hw_load.json",
            "returned_artifacts/tier4_31d_hw_milestone.json",
            "returned_artifacts/tier4_31d_hw_roundtrip.json",
            "returned_artifacts/tier4_31d_hw_target_acquisition.json",
            "returned_artifacts/tier4_31d_test_temporal_state_stdout.txt",
        ),
    ),
    EvidenceSpec(
        entry_id="tier4_31e_native_replay_eligibility_decision_closeout",
        tier_label="Tier 4.31e - Native Replay/Eligibility Decision Closeout",
        plan_position="Phase F closeout decision after native temporal hardware smoke",
        canonical_dir="tier4_31e_20260506_native_replay_eligibility_decision_closeout",
        results_file="tier4_31e_results.json",
        report_file="tier4_31e_report.md",
        summary_file="tier4_31e_summary.csv",
        harness="experiments/tier4_31e_native_replay_eligibility_decision_closeout.py",
        evidence_role="native replay/eligibility decision gate",
        claim="Measured evidence does not currently justify immediate native replay buffers, sleep-like replay, or native macro eligibility; Tier 4.31f is deferred and Tier 4.32 mapping/resource modeling is authorized next.",
        caveat="Local documentation/decision evidence only; not a hardware run, not a new mechanism implementation, not speedup, not multi-chip scaling, not native replay/sleep proof, not native eligibility proof, not full v2.2 hardware transfer, and not a baseline freeze.",
        latest_manifest_names=("tier4_31e_latest_manifest.json",),
        expected_extra_files=(
            "tier4_31e_evidence_inputs.csv",
        ),
    ),
    EvidenceSpec(
        entry_id="tier4_32_native_runtime_mapping_resource_model",
        tier_label="Tier 4.32 - Native Runtime Mapping/Resource Model",
        plan_position="Phase G native-runtime mapping/resource model before single-chip scale stress",
        canonical_dir="tier4_32_20260506_mapping_resource_model",
        results_file="tier4_32_results.json",
        report_file="tier4_32_report.md",
        summary_file="tier4_32_resource_envelope.csv",
        harness="experiments/tier4_32_mapping_resource_model.py",
        evidence_role="native runtime resource/mapping decision gate",
        claim="Measured 4.27-4.31 evidence is consolidated into a single native-runtime resource envelope: MCPL is the scale path, current single-chip profile builds have positive ITCM/DTCM headroom, 4.32a single-chip scale stress is authorized next, and no native-scale baseline freeze is authorized yet.",
        caveat="Local resource/mapping model only; not a new hardware run, not speedup evidence, not multi-chip scaling, not benchmark superiority, not full organism autonomy, and not a baseline freeze.",
        latest_manifest_names=("tier4_32_latest_manifest.json",),
        expected_extra_files=(
            "tier4_32_evidence_inputs.csv",
            "tier4_32_profile_budget.csv",
            "tier4_32_failure_classes.csv",
            "tier4_32_next_gate_plan.csv",
            "tier4_32_criteria.csv",
        ),
    ),
    EvidenceSpec(
        entry_id="tier4_32a_single_chip_scale_stress_preflight",
        tier_label="Tier 4.32a - Single-Chip Multi-Core Scale-Stress Preflight",
        plan_position="Phase G single-chip multi-core scale-stress preflight before EBRAINS hardware stress",
        canonical_dir="tier4_32a_20260506_single_chip_scale_stress",
        results_file="tier4_32a_results.json",
        report_file="tier4_32a_report.md",
        summary_file="tier4_32a_scale_points.csv",
        harness="experiments/tier4_32a_single_chip_scale_stress.py",
        evidence_role="native runtime single-chip scale-stress preflight",
        claim="Tier 4.32a converts the Tier 4.32 resource model into a predeclared single-chip MCPL-first stress envelope and catches a source-level scale blocker: the current MCPL lookup key has no shard/group field and dest_core is reserved/ignored. It authorizes only single-shard 4/5-core 4.32a-hw stress, requires Tier 4.32a-r1 shard-aware MCPL repair before replicated 8/12/16-core stress, and keeps 4.32b/multi-chip/native-scale baseline freeze blocked.",
        caveat="Local preflight/source-inspection evidence only; not a SpiNNaker hardware run, not speedup evidence, not replicated-shard scaling, not multi-chip scaling, not static reef partition proof, not benchmark superiority, and not a baseline freeze.",
        latest_manifest_names=("tier4_32a_latest_manifest.json",),
        expected_extra_files=(
            "tier4_32a_profile_allocation.csv",
            "tier4_32a_failure_classes.csv",
            "tier4_32a_next_gate_plan.csv",
            "tier4_32a_criteria.csv",
        ),
    ),
    EvidenceSpec(
        entry_id="tier4_32a_r0_protocol_truth_audit",
        tier_label="Tier 4.32a-r0 - Protocol Truth Audit",
        plan_position="Phase G corrective audit before MCPL-first EBRAINS scale stress",
        canonical_dir="tier4_32a_r0_20260506_protocol_truth_audit",
        results_file="tier4_32a_r0_results.json",
        report_file="tier4_32a_r0_report.md",
        summary_file="tier4_32a_r0_criteria.csv",
        harness="experiments/tier4_32a_r0_protocol_truth_audit.py",
        evidence_role="native runtime protocol truth audit",
        claim="Tier 4.32a-r0 prevents a misleading MCPL-first hardware package: source inspection proves confidence-gated lookup still uses transitional SDP, MCPL replies drop confidence, MCPL receive hardcodes confidence=1.0, and the MCPL key lacks shard identity. Tier 4.32a-r1 is required before MCPL-first scale stress.",
        caveat="Local source/documentation audit only; not SpiNNaker hardware evidence, not speedup evidence, not multi-chip scaling, not static reef partition proof, and not a baseline freeze.",
        latest_manifest_names=("tier4_32a_r0_latest_manifest.json",),
        expected_extra_files=(
            "tier4_32a_r0_source_findings.csv",
            "tier4_32a_r0_final_decision.json",
        ),
    ),
    EvidenceSpec(
        entry_id="tier4_32a_r1_mcpl_lookup_repair",
        tier_label="Tier 4.32a-r1 - Confidence-Bearing Shard-Aware MCPL Lookup Repair",
        plan_position="Phase G protocol repair before MCPL-first EBRAINS scale stress",
        canonical_dir="tier4_32a_r1_20260506_mcpl_lookup_repair",
        results_file="tier4_32a_r1_results.json",
        report_file="tier4_32a_r1_report.md",
        summary_file="tier4_32a_r1_criteria.csv",
        harness="experiments/tier4_32a_r1_mcpl_lookup_repair.py",
        evidence_role="native runtime MCPL lookup protocol repair",
        claim="Tier 4.32a-r1 repairs the Tier 4.32a-r0 blocker: MCPL lookup replies now carry value plus confidence/hit/status metadata, MCPL keys carry shard identity, local tests prove identical seq/type lookups do not cross-talk across shards, and MCPL confidence controls preserve full/zero/half-confidence learning behavior.",
        caveat="Local source/runtime evidence only; not SpiNNaker hardware evidence, not speedup evidence, not replicated-shard scaling, not multi-chip scaling, not static reef partitioning, and not a baseline freeze.",
        latest_manifest_names=("tier4_32a_r1_latest_manifest.json",),
        expected_extra_files=(
            "tier4_32a_r1_source_checks.csv",
            "tier4_32a_r1_command_log.txt",
            "tier4_32a_r1_final_decision.json",
        ),
    ),
    EvidenceSpec(
        entry_id="tier4_32a_hw_replicated_shard_stress",
        tier_label="Tier 4.32a-hw-replicated - Replicated-Shard MCPL-First Scale Stress",
        plan_position="Phase G single-chip replicated-shard hardware stress before static reef partitioning",
        canonical_dir="tier4_32a_hw_replicated_20260507_hardware_pass_ingested",
        results_file="tier4_32a_hw_replicated_results.json",
        report_file="tier4_32a_hw_replicated_report.md",
        summary_file="tier4_32a_hw_replicated_summary.csv",
        harness="experiments/tier4_32a_hw_replicated_shard_stress.py",
        evidence_role="native runtime single-chip replicated-shard hardware stress",
        claim="Tier 4.32a-hw-replicated passed the repaired shard-aware MCPL lookup protocol on real SpiNNaker at 8/12/16-core single-chip stress points with zero stale replies, duplicate replies, timeouts, or synthetic fallback.",
        caveat="Single-chip replicated-shard hardware stress only; not multi-chip evidence, not speedup evidence, not static reef partitioning, not benchmark superiority, and not a native-scale baseline freeze by itself.",
        latest_manifest_names=("tier4_32a_hw_replicated_latest_manifest.json",),
        expected_extra_files=(
            "returned_artifacts/tier4_32a_hw_replicated_results.json",
            "returned_artifacts/tier4_32a_hw_replicated_point_08c_dual_shard_summary.csv",
            "returned_artifacts/tier4_32a_hw_replicated_point_12c_triple_shard_result.json",
            "returned_artifacts/tier4_32a_hw_replicated_point_16c_quad_shard_result.json",
            "returned_artifacts/tier4_32a_hw_replicated_target_acquisition.json",
        ),
    ),
    EvidenceSpec(
        entry_id="tier4_32b_static_reef_partition_smoke",
        tier_label="Tier 4.32b - Static Reef Partition Smoke/Resource Mapping",
        plan_position="Phase G static reef partition mapping before inter-chip contract",
        canonical_dir="tier4_32b_20260507_static_reef_partition_smoke",
        results_file="tier4_32b_results.json",
        report_file="tier4_32b_report.md",
        summary_file="tier4_32b_partition_map.csv",
        harness="experiments/tier4_32b_static_reef_partition_smoke.py",
        evidence_role="native runtime static reef partition mapping",
        claim="Tier 4.32b maps CRA reef groups/modules/polyps onto the measured single-chip replicated-shard envelope: four static reef partitions own non-overlapping context/route/memory/learning cores and polyp slots, lookup parity and zero stale/duplicate/timeout counters are inherited from the 4.32a replicated hardware pass, one-polyp-one-chip is explicitly rejected, and Tier 4.32c inter-chip contract work is authorized next.",
        caveat="Local static partition/resource evidence only; not a new SpiNNaker hardware run, not speedup evidence, not one-polyp-one-chip evidence, not multi-chip evidence, not benchmark superiority, and not a native-scale baseline freeze.",
        latest_manifest_names=("tier4_32b_latest_manifest.json",),
        expected_extra_files=(
            "tier4_32b_candidate_layouts.csv",
            "tier4_32b_criteria.csv",
            "tier4_32b_failure_classes.csv",
            "tier4_32b_next_gate_plan.csv",
            "tier4_32b_ownership_invariants.csv",
            "tier4_32b_replicated_envelope.csv",
            "tier4_32b_source_checks.csv",
        ),
    ),
    EvidenceSpec(
        entry_id="tier4_32c_interchip_feasibility_contract",
        tier_label="Tier 4.32c - Inter-Chip Feasibility Contract",
        plan_position="Phase G inter-chip contract before first multi-chip smoke",
        canonical_dir="tier4_32c_20260507_interchip_feasibility_contract",
        results_file="tier4_32c_results.json",
        report_file="tier4_32c_report.md",
        summary_file="tier4_32c_placement_contract.csv",
        harness="experiments/tier4_32c_interchip_feasibility_contract.py",
        evidence_role="native runtime inter-chip feasibility contract",
        claim="Tier 4.32c defines the first reviewer-defensible inter-chip contract over the Tier 4.32b static reef partition map: required board/chip/core/role/partition/shard/seq identity fields, remote split-role MCPL lookup paths, compact readback ownership, failure classes, and the exact two-chip split-role single-shard smoke authorized for Tier 4.32d. It also records that true two-partition cross-chip learning is blocked until origin/target shard semantics are defined.",
        caveat="Local contract evidence only; not SpiNNaker hardware evidence, not multi-chip execution evidence, not true two-partition cross-chip learning evidence, not speedup evidence, not learning-scale evidence, not benchmark superiority, and not a native-scale baseline freeze.",
        latest_manifest_names=("tier4_32c_latest_manifest.json",),
        expected_extra_files=(
            "tier4_32c_criteria.csv",
            "tier4_32c_failure_classes.csv",
            "tier4_32c_identity_contract.csv",
            "tier4_32c_message_paths.csv",
            "tier4_32c_next_gate_plan.csv",
            "tier4_32c_readback_contract.csv",
            "tier4_32c_source_checks.csv",
        ),
    ),
    EvidenceSpec(
        entry_id="tier4_32d_r0_interchip_route_source_audit",
        tier_label="Tier 4.32d-r0 - Inter-Chip Route/Source/Package Audit",
        plan_position="Phase G route/source/package QA before first inter-chip hardware package",
        canonical_dir="tier4_32d_r0_20260507_interchip_route_source_audit",
        results_file="tier4_32d_r0_results.json",
        report_file="tier4_32d_r0_report.md",
        summary_file="tier4_32d_r0_source_findings.csv",
        harness="experiments/tier4_32d_r0_interchip_route_source_audit.py",
        evidence_role="native runtime inter-chip route/source/package QA",
        claim="Tier 4.32d-r0 passed as a local route/source/package audit by blocking the first two-chip split-role single-shard EBRAINS package until inter-chip MCPL route entries are repaired or explicitly proven. The source-backed MCPL key/value/meta path exists, but current cra_state_mcpl_init routes request/reply keys to local cores only and does not define explicit inter-chip link routing.",
        caveat="Local audit evidence only; not SpiNNaker hardware evidence, not an EBRAINS package, not multi-chip execution evidence, not speedup evidence, not learning-scale evidence, not benchmark superiority, and not a native-scale baseline freeze.",
        latest_manifest_names=("tier4_32d_r0_latest_manifest.json",),
        expected_extra_files=(
            "tier4_32d_r0_criteria.csv",
            "tier4_32d_r0_failure_classes.csv",
            "tier4_32d_r0_source_findings.csv",
        ),
    ),
    EvidenceSpec(
        entry_id="tier4_32d_r1_interchip_route_repair_local_qa",
        tier_label="Tier 4.32d-r1 - Inter-Chip MCPL Route Repair Local QA",
        plan_position="Phase G route repair/local QA before first inter-chip hardware package",
        canonical_dir="tier4_32d_r1_20260507_interchip_route_repair_local_qa",
        results_file="tier4_32d_r1_results.json",
        report_file="tier4_32d_r1_report.md",
        summary_file="tier4_32d_r1_source_findings.csv",
        harness="experiments/tier4_32d_r1_interchip_route_repair_local_qa.py",
        evidence_role="native runtime inter-chip MCPL route repair/local QA",
        claim="Tier 4.32d-r1 passed as local source/runtime QA for the first two-chip split-role single-shard MCPL smoke: learning-core builds can install outbound request link routes, state-core builds can install local request delivery plus outbound value/meta reply link routes, the route-table stub inspects key/mask/route entries, and existing MCPL lookup/four-core regressions still pass.",
        caveat="Local source/runtime QA only; not SpiNNaker hardware evidence, not an EBRAINS package, not multi-chip execution evidence, not learning-scale evidence, not speedup evidence, not benchmark superiority, and not a native-scale baseline freeze.",
        latest_manifest_names=("tier4_32d_r1_latest_manifest.json",),
        expected_extra_files=(
            "tier4_32d_r1_criteria.csv",
            "tier4_32d_r1_source_findings.csv",
            "tier4_32d_r1_test_commands.csv",
            "tier4_32d_r1_test_command_1.stdout.txt",
            "tier4_32d_r1_test_command_1.stderr.txt",
            "tier4_32d_r1_test_command_2.stdout.txt",
            "tier4_32d_r1_test_command_2.stderr.txt",
            "tier4_32d_r1_test_command_3.stdout.txt",
            "tier4_32d_r1_test_command_3.stderr.txt",
        ),
    ),
    EvidenceSpec(
        entry_id="tier4_32d_two_chip_mcpl_lookup_hardware_smoke",
        tier_label="Tier 4.32d - Two-Chip Split-Role Single-Shard MCPL Lookup Smoke",
        plan_position="Phase G first two-chip split-role MCPL communication/readback hardware smoke",
        canonical_dir="tier4_32d_20260507_hardware_pass_ingested",
        results_file="tier4_32d_results.json",
        report_file="tier4_32d_report.md",
        summary_file="tier4_32d_summary.csv",
        harness="experiments/tier4_32d_interchip_mcpl_smoke.py",
        evidence_role="native runtime first two-chip MCPL communication/readback hardware smoke",
        claim="Tier 4.32d passed as the first two-chip split-role single-shard MCPL lookup hardware smoke: a learning core on chip (0,0) communicated with context/route/memory state cores on chip (1,0), completed 32 events, received 96/96 lookup replies, and returned zero stale replies, duplicates, timeouts, or synthetic fallback.",
        caveat="Two-chip communication/readback hardware smoke only; not learning-scale evidence, not speedup evidence, not benchmark superiority, not true two-partition cross-chip learning, not lifecycle scaling, not multi-shard learning, and not a native-scale baseline freeze.",
        latest_manifest_names=("tier4_32d_latest_manifest.json",),
        expected_extra_files=(
            "returned_artifacts/tier4_32d_results.json",
            "returned_artifacts/tier4_32d_task_result.json",
            "returned_artifacts/tier4_32d_task_summary.csv",
            "returned_artifacts/tier4_32d_target_acquisition.json",
        ),
    ),
    EvidenceSpec(
        entry_id="tier4_32e_multi_chip_learning_microtask",
        tier_label="Tier 4.32e - Multi-Chip Learning Micro-Task",
        plan_position="Phase G first two-chip split-role learning-bearing hardware micro-task",
        canonical_dir="tier4_32e_20260507_hardware_pass_ingested",
        results_file="tier4_32e_results.json",
        report_file="tier4_32e_report.md",
        summary_file="tier4_32e_summary.csv",
        harness="experiments/tier4_32e_multichip_learning_microtask.py",
        evidence_role="native runtime first two-chip MCPL learning micro-task hardware pass",
        claim="Tier 4.32e passed as the smallest two-chip single-shard learning-bearing MCPL hardware micro-task: enabled learning at LR 0.25 and a no-learning LR 0.0 control both completed 32 events, received 96/96 lookup replies, returned zero stale replies, duplicates, timeouts, or synthetic fallback, and separated readout state exactly as expected.",
        caveat="Two-chip single-shard learning micro-task only; not speedup evidence, not benchmark superiority, not true two-partition cross-chip learning, not lifecycle scaling, not multi-shard learning, and not a native-scale baseline freeze.",
        latest_manifest_names=("tier4_32e_latest_manifest.json",),
        expected_extra_files=(
            "returned_artifacts/tier4_32e_results.json",
            "returned_artifacts/tier4_32e_task_result.json",
            "returned_artifacts/tier4_32e_task_summary.csv",
            "returned_artifacts/tier4_32e_target_acquisition.json",
            "returned_artifacts/tier4_32e_case_enabled_lr_0_25.json",
            "returned_artifacts/tier4_32e_case_no_learning_lr_0_00.json",
        ),
    ),
    EvidenceSpec(
        entry_id="tier4_32f_multichip_resource_lifecycle_decision",
        tier_label="Tier 4.32f - Multi-Chip Resource/Lifecycle Decision Contract",
        plan_position="Phase G decision contract after first two-chip learning-bearing hardware micro-task",
        canonical_dir="tier4_32f_20260507_multichip_resource_lifecycle_decision",
        results_file="tier4_32f_results.json",
        report_file="tier4_32f_report.md",
        summary_file="tier4_32f_candidate_directions.csv",
        harness="experiments/tier4_32f_multichip_resource_lifecycle_decision.py",
        evidence_role="native runtime multi-chip lifecycle/resource decision contract",
        claim="Tier 4.32f passed as a local decision contract after the 4.32e two-chip learning micro-task: it selected multi-chip lifecycle traffic with resource counters as the next direction, classified the missing lifecycle inter-chip route proof, authorized Tier 4.32g-r0 source/route repair audit next, and blocked immediate lifecycle hardware packaging, speedup, benchmarks, true two-partition learning, multi-shard learning, and native-scale baseline freeze.",
        caveat="Local decision/contract evidence only; not hardware evidence, not lifecycle scaling, not speedup evidence, not benchmark superiority, not true two-partition learning, not multi-shard learning, and not a native-scale baseline freeze.",
        latest_manifest_names=("tier4_32f_latest_manifest.json",),
        expected_extra_files=(
            "tier4_32f_criteria.csv",
            "tier4_32f_source_checks.csv",
            "tier4_32f_learning_cases.csv",
            "tier4_32f_candidate_directions.csv",
            "tier4_32f_required_readback.csv",
            "tier4_32f_next_gates.csv",
        ),
    ),
    EvidenceSpec(
        entry_id="tier4_32g_r0_multichip_lifecycle_route_source_audit",
        tier_label="Tier 4.32g-r0 - Multi-Chip Lifecycle Route/Source Repair Audit",
        plan_position="Phase G source/route repair audit before multi-chip lifecycle hardware smoke",
        canonical_dir="tier4_32g_r0_20260507_lifecycle_route_source_audit",
        results_file="tier4_32g_r0_results.json",
        report_file="tier4_32g_r0_report.md",
        summary_file="tier4_32g_r0_route_contract.csv",
        harness="experiments/tier4_32g_r0_multichip_lifecycle_route_source_audit.py",
        evidence_role="native runtime lifecycle inter-chip route/source repair audit",
        claim="Tier 4.32g-r0 passed as local source/runtime QA before the two-chip lifecycle hardware smoke: lifecycle event request, trophic update, and active-mask/lineage sync MCPL routes are source-proven for learning and lifecycle profiles, the dedicated lifecycle inter-chip route C test passes, and existing lookup-route and lifecycle-split regressions remain green.",
        caveat="Local source/runtime QA only; not SpiNNaker hardware evidence, not lifecycle scaling, not speedup evidence, not benchmark superiority, not true two-partition learning, not multi-shard learning, and not a native-scale baseline freeze.",
        latest_manifest_names=("tier4_32g_r0_latest_manifest.json",),
        expected_extra_files=(
            "tier4_32g_r0_criteria.csv",
            "tier4_32g_r0_source_findings.csv",
            "tier4_32g_r0_route_contract.csv",
            "tier4_32g_r0_test_commands.csv",
            "tier4_32g_r0_next_gates.csv",
            "tier4_32g_r0_lifecycle_interchip_route_contract_stdout.txt",
            "tier4_32g_r0_lifecycle_interchip_route_contract_stderr.txt",
            "tier4_32g_r0_lookup_interchip_route_regression_stdout.txt",
            "tier4_32g_r0_lookup_interchip_route_regression_stderr.txt",
            "tier4_32g_r0_lifecycle_split_regression_stdout.txt",
            "tier4_32g_r0_lifecycle_split_regression_stderr.txt",
        ),
    ),
    EvidenceSpec(
        entry_id="tier4_32g_two_chip_lifecycle_traffic_resource_smoke",
        tier_label="Tier 4.32g - Two-Chip Lifecycle Traffic/Resource Hardware Smoke",
        plan_position="Phase G two-chip lifecycle traffic/resource hardware smoke before native-scale closeout",
        canonical_dir="tier4_32g_20260508_hardware_pass_ingested",
        results_file="tier4_32g_results.json",
        report_file="tier4_32g_report.md",
        summary_file="tier4_32g_summary.csv",
        harness="experiments/tier4_32g_multichip_lifecycle_traffic_resource_smoke.py",
        evidence_role="native runtime two-chip lifecycle traffic/resource hardware smoke",
        claim="Tier 4.32g passed on real SpiNNaker with the repaired cache-proof runner: source learning core (0,0,p7) emitted lifecycle event/trophic requests to remote lifecycle core (1,0,p4), received active-mask/lineage sync, returned zero stale/duplicate/missing-ack counters, and preserved 30 returned artifacts with zero synthetic fallback.",
        caveat="Two-chip lifecycle traffic/resource smoke only; not lifecycle scaling, not speedup evidence, not benchmark superiority, not true partitioned ecology, not multi-shard learning, and not a native-scale baseline freeze by itself.",
        latest_manifest_names=("tier4_32g_latest_manifest.json",),
        expected_extra_files=(
            "returned_artifacts/tier4_32g_results (2).json",
            "returned_artifacts/tier4_32g_task_result (2).json",
            "returned_artifacts/tier4_32g_task_summary (2).csv",
            "returned_artifacts/tier4_32g_target_acquisition (2).json",
        ),
    ),
    EvidenceSpec(
        entry_id="tier4_32h_native_scale_evidence_closeout",
        tier_label="Tier 4.32h - Native-Scale Evidence Closeout / Baseline Decision",
        plan_position="Phase G native-scale evidence closeout before pivoting to usefulness benchmarks",
        canonical_dir="tier4_32h_20260508_native_scale_evidence_closeout",
        results_file="tier4_32h_results.json",
        report_file="tier4_32h_report.md",
        summary_file="tier4_32h_summary.csv",
        harness="experiments/tier4_32h_native_scale_evidence_closeout.py",
        evidence_role="native-scale baseline freeze decision",
        claim="Tier 4.32h passed 64/64 closeout criteria and froze CRA_NATIVE_SCALE_BASELINE_v0.5 as a bounded native-scale substrate baseline over the completed 4.32a/4.32d/4.32e/4.32g hardware evidence bundle.",
        caveat="Local evidence closeout only; not a new hardware run, not speedup evidence, not benchmark evidence, not real-task usefulness, not true two-partition learning, not lifecycle scaling, not multi-shard learning, and not AGI/ASI evidence.",
        latest_manifest_names=("tier4_32h_latest_manifest.json",),
        expected_extra_files=(),
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
        elif path.name.startswith("tier4_20c"):
            role = "v2_1_three_seed_hardware_repeat"
        elif path.name.startswith("tier4_21a"):
            role = "keyed_context_memory_hardware_bridge"
        elif path.name.startswith("tier4_22a0"):
            role = "spinnaker_constrained_preflight"
        elif path.name.startswith("tier4_22c"):
            role = "persistent_custom_c_state_scaffold"
        elif path.name.startswith("tier4_22d"):
            role = "custom_c_reward_plasticity_scaffold"
        elif path.name.startswith("tier4_22f0"):
            role = "custom_runtime_scale_readiness_audit"
        elif path.name.startswith("tier4_22g"):
            role = "event_indexed_active_trace_runtime"
        elif path.name.startswith("tier4_22h"):
            role = "compact_readback_build_readiness"
        elif path.name.startswith("tier4_22k"):
            role = "spin1api_event_symbol_discovery"
        elif path.name.startswith("tier4_22w"):
            role = "native_decoupled_memory_route_composition_custom_runtime_smoke"
        elif path.name.startswith("tier4_22v"):
            role = "native_memory_route_reentry_composition_custom_runtime_smoke"
        elif path.name.startswith("tier4_22u"):
            role = "native_memory_route_state_custom_runtime_smoke"
        elif path.name.startswith("tier4_22t"):
            role = "native_keyed_route_state_custom_runtime_smoke"
        elif path.name.startswith("tier4_22s"):
            role = "native_route_state_custom_runtime_smoke"
        elif path.name.startswith("tier4_22r"):
            role = "native_context_state_custom_runtime_smoke"
        elif path.name.startswith("tier4_22q"):
            role = "integrated_v2_bridge_custom_runtime_smoke"
        elif path.name.startswith("tier4_22p"):
            role = "aba_reentry_custom_runtime_micro_task"
        elif path.name.startswith("tier4_22o"):
            role = "noisy_switching_custom_runtime_micro_task"
        elif path.name.startswith("tier4_22n"):
            role = "delayed_cue_custom_runtime_micro_task"
        elif path.name.startswith("tier4_22m"):
            role = "fixed_pattern_custom_runtime_task_micro_loop"
        elif path.name.startswith("tier4_22l"):
            role = "custom_runtime_learning_parity"
        elif path.name.startswith("tier4_22j"):
            role = "minimal_custom_runtime_learning_smoke"
        elif path.name.startswith("tier4_22i"):
            role = "custom_runtime_board_roundtrip"
        elif path.name.startswith("tier4_22e"):
            role = "local_custom_c_learning_parity_scaffold"
        elif path.name.startswith("tier4_22b"):
            role = "continuous_transport_scaffold"
        elif path.name.startswith("tier4_22a"):
            role = "custom_runtime_contract"
        elif path.name.startswith("tier4_23c"):
            role = "continuous_hardware_smoke"
        elif path.name.startswith("tier4_25b"):
            role = "two_core_state_learning_split_smoke"
        elif path.name.startswith("tier4_25c"):
            role = "two_core_state_learning_split_repeatability"
        elif path.name.startswith("tier4_26"):
            role = "four_core_distributed_smoke"
        elif path.name.startswith("tier4_28e_pointB"):
            role = "failure_envelope_boundary_diagnostic"
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
        "expanded_test_entry_count": len(entries),
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
            lineterminator="\n",
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
        f"- Expanded test-entry count: `{registry['expanded_test_entry_count']}`; see the canonical evidence table below for the exact current tier list.",
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
        f"- Expanded evidence suite: `{registry['expanded_test_entry_count']}` entries; see the canonical evidence table below for the exact current tier list.",
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
        "tier4_20b_20260429_205214_prepared": "Prepared Tier 4.20b v2.1 one-seed chunked hardware probe: seed 42, delayed_cue plus hard_noisy_switching, 1200 steps, N=8, chunk 50, macro eligibility excluded. Superseded by the returned Tier 4.20b pass.",
        "tier4_20b_20260430_v2_1_bridge_seed42_hardware_pass_ingested": "Passed Tier 4.20b v2.1 one-seed bridge/transport hardware probe: real pyNN.spiNNaker execution, runner revision tier4_20b_inprocess_no_baselines_20260429_2330, in-process Tier 4.16 child runner, zero fallback, zero sim.run/readback failures, nonzero spike readback, delayed_cue tail accuracy 1.0, hard_noisy_switching tail accuracy 0.5952380952380952. This is not native/on-chip v2.1 mechanism evidence.",
        "tier4_20c_20260430_000433_prepared": "Prepared Tier 4.20c v2.1 three-seed chunked hardware repeat: seeds 42,43,44, delayed_cue plus hard_noisy_switching, 1200 steps, N=8, chunk 50, macro eligibility excluded. This is a JobManager run package only, not hardware evidence until returned artifacts pass.",
        "tier4_20c_20260430_v2_1_bridge_three_seed_hardware_pass_ingested": "Passed Tier 4.20c v2.1 three-seed bridge/transport hardware repeat: six real pyNN.spiNNaker child runs across delayed_cue and hard_noisy_switching, seeds 42/43/44, zero fallback, zero sim.run/readback failures, minimum real spike readback 94727, delayed_cue tail accuracy min/mean 1.0/1.0, hard_noisy_switching tail accuracy min/mean/max 0.5238095238095238/0.5476190476190476/0.5952380952380952. Raw wrapper false-fail preserved separately; failure was missing local Tier 4.20b manifest in fresh EBRAINS source bundle, not hardware/science failure. Not native/on-chip v2.1 mechanism evidence.",
        "tier4_21a_local_bridge_smoke": "Passed Tier 4.21a local bridge smoke: the keyed-context-memory scheduler, chunked host replay, memory-event logging, and ablation matrix execute locally with zero fallback/failures and active keyed-memory features. This is source/logic preflight only, not SpiNNaker hardware evidence and not native/on-chip memory.",
        "tier4_21a_20260430_prepared": "Prepared Tier 4.21a keyed context-memory hardware bridge capsule: one-seed context_reentry_interference, keyed candidate plus memory ablations, 720 steps, N=8, chunk 50, host-side scheduler. This is a JobManager run package only, not hardware evidence until returned run-hardware artifacts pass.",
        "tier4_21a_20260430_keyed_context_memory_seed42_hardware_pass_ingested": "Passed Tier 4.21a keyed context-memory hardware bridge probe: one real pyNN.spiNNaker seed-42 matrix with keyed_context_memory plus slot-reset/slot-shuffle/wrong-key ablations, 720 steps, N=8, chunk 50, zero fallback, zero sim.run/readback failures, minimum real spike readback 714601, keyed memory updates 11, active keyed feature decisions 20, four slots used, keyed all/tail accuracy 1.0/1.0, best-ablation all accuracy 0.5. This is host-side keyed-memory bridge evidence only, not native/on-chip memory, custom C, continuous runtime, or broader v2 mechanism transfer.",
        "tier4_22a_20260430_custom_runtime_contract": "Passed Tier 4.22a custom/hybrid on-chip runtime contract: references the Tier 4.20c repeatable bridge and Tier 4.21a keyed-memory bridge pass, defines constrained-NEST plus sPyNNaker mapping preflight before further expensive hardware, assigns host/hybrid/on-chip state ownership, declares runtime stages 4.22a0-4.23, parity gates, and memory/resource risks. Engineering contract only; not custom C, native/on-chip execution, continuous runtime, speedup, or new hardware science evidence.",
        "tier4_22a0_20260430_spinnaker_constrained_preflight": "Passed Tier 4.22a0 SpiNNaker-constrained local preflight: NEST/PyNN/sPyNNaker imports passed, sPyNNaker exposed required PyNN primitives, constrained PyNN/NEST StepCurrentSource smoke returned 64 binned spikes with zero sim/readback failures, static bridge compliance/resource/fixed-point checks passed, and custom C host runtime tests passed. Local transfer-risk-reduction evidence only; not real SpiNNaker hardware evidence, custom-C hardware execution, native/on-chip learning, continuous runtime, or speedup evidence.",
        "tier4_22b_20260430_continuous_transport_local": "Passed Tier 4.22b local continuous transport scaffold: delayed_cue and hard_noisy_switching seed 42 ran for 1200 steps under PyNN/NEST with one scheduled-input sim.run per task, zero fallback, zero sim.run/readback/scheduled-input failures, and minimum per-case binned spike readback 101056. Transport-isolation evidence only; learning is disabled by design and this is not real hardware evidence, custom-C execution, native/on-chip learning, continuous-learning parity, or speedup evidence.",
        "tier4_22b_20260430_continuous_transport_hardware_pass_ingested": "Passed Tier 4.22b real SpiNNaker continuous transport scaffold: delayed_cue and hard_noisy_switching seed 42 ran for 1200 steps through pyNN.spiNNaker with one scheduled-input sim.run per task, zero fallback, zero sim.run/readback/scheduled-input failures, minimum per-case binned spike readback 94896, and runtimes 111.5257s/109.3603s. Transport evidence only; learning is disabled by design and this is not custom-C execution, native/on-chip learning, continuous-learning parity, or speedup evidence.",
        "tier4_22c_20260430_persistent_state_scaffold": "Passed Tier 4.22c persistent custom-C state scaffold: Tier 4.22b transport reference exists, custom C host tests passed, static checks passed, bounded keyed context slots use MAX_CONTEXT_SLOTS, pending horizons use MAX_PENDING_HORIZONS without storing future targets, state_manager.c avoids dynamic allocation, runtime init/reset owns state lifecycle, and the exported state contract covers keyed slots, pending horizons, readout state, decision/reward counters, and reset semantics. Custom-C state scaffold only; not a hardware run, on-chip reward/plasticity learning, speedup evidence, or full CRA deployment.",
        "tier4_22d_20260430_reward_plasticity_scaffold": "Passed Tier 4.22d local custom-C reward/plasticity scaffold: Tier 4.22c persistent state reference exists, custom C host tests passed, 11/11 static checks passed, synaptic eligibility traces, trace-gated dopamine, fixed-point trace decay, signed one-shot dopamine, and runtime-owned readout reward updates exist. Local scaffold only; not hardware evidence, continuous-learning parity, scale-ready eligibility optimization, speedup evidence, or full CRA deployment.",
        "tier4_22e_20260430_local_learning_parity": "Passed Tier 4.22e local minimal delayed-readout parity scaffold: Tier 4.22d reference exists, custom C host tests passed, source checks confirm the bounded pending queue does not store future targets, fixed-point C-equation mirror matched the floating reference on delayed_cue and hard_noisy_switching seed 42 with sign agreement 1.0, max final weight delta about 4.14e-05, delayed_cue tail accuracy 1.0, hard_noisy_switching tail accuracy 0.547619, no-pending ablation tail accuracy 0.0, and zero pending drops. Local parity only; not hardware evidence, full CRA parity, lifecycle/replay/routing parity, speedup evidence, or final on-chip proof.",
        "tier4_22f0_20260430_custom_runtime_scale_audit": "Passed Tier 4.22f0 custom-runtime scale-readiness audit: Tier 4.22e reference exists, custom C host tests passed, 9/9 static audit checks passed, PyNN/sPyNNaker is preserved as the primary supported hardware layer, and 7 custom-C scale blockers were documented with 3 high-severity blockers. Audit pass only; custom_runtime_scale_ready=false and direct custom-runtime learning hardware claims are blocked until event-indexed spike delivery, lazy/active eligibility traces, and compact state readback are implemented.",
        "tier4_22g_20260430_event_indexed_trace_runtime": "Passed Tier 4.22g local event-indexed active-trace runtime optimization: Tier 4.22f0 reference exists, custom C host tests passed, 12/12 static optimization checks passed, SCALE-001/002/003 were repaired locally, spike delivery now uses pre-indexed outgoing adjacency, trace decay and dopamine modulation use active traces, and Tier 4.22i later cleared the compact state-readback/build-load acceptance gate. Not hardware, speedup, full CRA parity, or final on-chip learning evidence.",
        "tier4_22h_20260430_compact_readback_acceptance": "Passed Tier 4.22h local compact-readback/build-readiness gate: Tier 4.22g reference exists, custom C host tests passed, 30/30 static readback/callback/SARK-SDP/router-API/build-recipe compatibility checks passed, CMD_READ_STATE schema v1 packs a 73-byte compact runtime summary, and .aplx build status was honestly recorded as not_attempted_spinnaker_tools_missing. Not hardware evidence, board-load evidence, command round-trip evidence, speedup evidence, or custom-runtime learning evidence.",
        "tier4_22i_20260430_custom_runtime_roundtrip_prepared": "Prepared Tier 4.22i custom-runtime board round-trip smoke package: emits the refreshed cache-busting ebrains_jobs/cra_422r EBRAINS upload folder and run-hardware command for .aplx build/load plus CMD_READ_STATE schema-v1 state-mutation round-trip, with local `main.c` syntax guards, Tier 4.22k-confirmed official MC event constants, SARK SDP packed-field guards, official SDP command-header guards (`cmd_rc`/`seq`/`arg1`/`arg2`/`arg3` before `data[]`), official SARK router API guards (`rtr_alloc`, `rtr_mc_set`, `rtr_free`), official spinnaker_tools.mk build-recipe guards, nested object-directory guards for build/gnu/src/*.o, and auto target acquisition through explicit hostname or a pyNN.spiNNaker/SpynnakerDataView probe. Prepared source package only; not hardware evidence, speedup evidence, full CRA learning, or final on-chip autonomy until returned run-hardware artifacts pass.",
        "tier4_22i_20260430_ebrains_aplx_build_fail": "Failed noncanonical Tier 4.22i EBRAINS attempt: .aplx build failed before board round-trip because the EBRAINS Spin1API headers did not define MC_PACKET_RX; CMD_READ_STATE round-trip was not attempted. Preserved as toolchain-compatibility evidence.",
        "tier4_22i_20260430_ebrains_no_mc_event_build_fail": "Failed noncanonical Tier 4.22i EBRAINS attempt: .aplx build failed before board round-trip because the EBRAINS build image did not expose the guessed multicast receive event compatibility names either. Preserved as evidence that blind callback-name patching is unsafe; routes next step to Tier 4.22k Spin1API event-symbol discovery.",
        "tier4_22i_20260430_ebrains_sdp_struct_build_fail": "Failed noncanonical Tier 4.22i EBRAINS attempt: .aplx build reached host_interface.c after the multicast event repair, then failed because EBRAINS SARK exposes packed sdp_msg_t fields (dest_port/srce_port/dest_addr/srce_addr) and sark_mem_cpy rather than local split coordinate/CPU fields and sark_memcpy. Board load and CMD_READ_STATE round-trip were not attempted; preserved as toolchain/API compatibility evidence before regenerated cra_422m.",
        "tier4_22i_20260430_ebrains_router_api_build_fail": "Failed noncanonical Tier 4.22i EBRAINS attempt: .aplx build compiled past host_interface.c after the SARK SDP repair, then failed in router.c because router.h relied on indirect uint32_t definitions and the runtime used local-stub-only sark_router_alloc/sark_router_free helpers. Official SpiNNakerManchester SARK exposes rtr_alloc, rtr_mc_set, and rtr_free; board load and CMD_READ_STATE round-trip were not attempted. Preserved as toolchain/API compatibility evidence before regenerated cra_422n.",
        "tier4_22i_20260430_ebrains_manual_link_empty_elf_fail": "Failed noncanonical Tier 4.22i EBRAINS attempt: .aplx build compiled all custom C sources through router.c and linked a coral_reef.elf, but the manual object-only link recipe omitted the official SpiNNaker startup/build object and spin1_api library, causing missing cpu_reset, an ELF with no sections, and objcopy failure before APLX creation. Board load and CMD_READ_STATE round-trip were not attempted. Preserved as build-recipe compatibility evidence before regenerated cra_422o.",
        "tier4_22i_20260430_ebrains_official_mk_nested_object_dir_fail": "Failed noncanonical Tier 4.22i EBRAINS attempt: regenerated cra_422o used official spinnaker_tools.mk and compiled through the official rule path, but the generated OBJECTS preserved source subdirectories and the build did not create build/gnu/src/ before compiling build/gnu/src/main.o. Board load and CMD_READ_STATE round-trip were not attempted. Preserved as build-directory compatibility evidence before regenerated cra_422p/cra_422q.",
        "tier4_22i_20260430_ebrains_aplx_build_pass_target_missing_fail": "Failed noncanonical Tier 4.22i EBRAINS attempt: regenerated cra_422p built the custom runtime .aplx successfully with official spinnaker_tools.mk, passed host C tests and main syntax checks, but the raw loader did not discover a board hostname/transceiver/IP, so app load and CMD_READ_STATE round-trip were not attempted. Preserved as target-acquisition evidence before regenerated cra_422q with pyNN.spiNNaker/SpynnakerDataView auto acquisition.",
        "tier4_22i_20260430_ebrains_aplx_load_pass_sdp_payload_short_fail": "Failed noncanonical Tier 4.22i EBRAINS attempt: regenerated cra_422q built the custom runtime .aplx, acquired a real board through pyNN.spiNNaker/SpynnakerDataView, selected free core 4, and loaded the app, but command round-trip returned 2-byte short payloads because the host/runtime SDP command protocol did not use the official cmd_rc/seq/arg1/arg2/arg3/data[] layout. Preserved as command-protocol evidence before regenerated cra_422r.",
        "tier4_22i_20260501_ebrains_board_roundtrip_pass": "Passed noncanonical Tier 4.22i EBRAINS custom-runtime board round-trip: regenerated cra_422r built the custom runtime .aplx, acquired a real board through pyNN.spiNNaker/SpynnakerDataView at 10.11.194.113, selected free core (0,0,4), loaded the app, acknowledged RESET/BIRTH/CREATE_SYN/DOPAMINE, and returned CMD_READ_STATE schema-v1 73-byte payload with visible post-mutation state (2 neurons, 1 synapse, reward_events=1) and zero synthetic fallback. Board-load and command-roundtrip evidence only; not full CRA learning, speedup, multi-core scaling, continuous runtime, or final on-chip autonomy.",
        "tier4_22j_20260501_minimal_custom_runtime_learning_prepared": "Prepared Tier 4.22j minimal custom-runtime closed-loop learning smoke package: emits the cache-busting ebrains_jobs/cra_422s EBRAINS upload folder and run-hardware command for one chip-owned delayed pending/readout update after the Tier 4.22i board-roundtrip pass. Source and bundle guards cover CMD_SCHEDULE_PENDING, CMD_MATURE_PENDING, controller methods, runtime handlers, dispatcher routing, and official SDP command-header usage. Prepared source package only; not hardware evidence, full CRA task learning, v2.1 mechanism transfer, speedup evidence, multi-core scaling, or final on-chip autonomy until returned run-hardware artifacts pass.",
        "tier4_22j_20260501_minimal_custom_runtime_learning_hardware_pass_ingested": "Passed Tier 4.22j EBRAINS minimal custom-runtime closed-loop learning smoke after ingest correction: raw returned status was fail because the runner criterion treated active_pending=0 as missing via Python `or -1`, but returned hardware data show target acquisition, .aplx build, app load, CMD_SCHEDULE_PENDING, active pending creation, CMD_MATURE_PENDING, pending maturation, reward_events=1, readout_weight=0.25, readout_bias=0.25, active_pending=0, and zero synthetic fallback. Raw remote manifest/report are preserved as false-fail artifacts. This is one minimal chip-owned delayed pending/readout update only; not full CRA task learning, v2.1 mechanism transfer, speedup evidence, multi-core scaling, or final on-chip autonomy.",
        "tier4_22l_20260501_custom_runtime_learning_parity_local": "Passed local Tier 4.22l tiny custom-runtime learning parity gate: Tier 4.22j latest pass exists, main.c syntax check passed, a four-update signed s16.15 reference was generated, and source guards confirmed CMD_SCHEDULE_PENDING/CMD_MATURE_PENDING plus the fixed-point prediction/update equations. Local parity/reference evidence only; not hardware evidence, full CRA task learning, v2.1 mechanism transfer, speedup evidence, or final on-chip autonomy.",
        "tier4_22l_20260501_custom_runtime_learning_parity_prepared": "Prepared Tier 4.22l tiny custom-runtime learning parity package: emits ebrains_jobs/cra_422t and a JobManager run-hardware command for four chip-owned pending/readout updates that must match the local s16.15 reference within raw tolerance 1 and finish with pending_created=4, pending_matured=4, reward_events=4, active_pending=0, final readout_weight_raw=-4096, and final readout_bias_raw=-4096. Prepared source package only; not hardware evidence until returned EBRAINS artifacts pass.",
        "tier4_22l_20260501_custom_runtime_learning_parity_hardware_pass_ingested": "Passed Tier 4.22l EBRAINS tiny custom-runtime learning parity: raw remote status was pass, target acquisition succeeded through pyNN.spiNNaker/SpynnakerDataView on board 10.11.194.1, free core (0,0,4) was selected, .aplx build and app load passed, four CMD_SCHEDULE_PENDING/CMD_MATURE_PENDING pairs succeeded, each mature command matured exactly one pending horizon, prediction/weight/bias raw deltas were all 0, and final state was pending_created=4, pending_matured=4, reward_events=4, active_pending=0, readout_weight_raw=-4096, readout_bias_raw=-4096. Tiny fixed-point custom-runtime parity evidence only; not full CRA task learning, v2.1 mechanism transfer, speedup evidence, multi-core scaling, or final on-chip autonomy.",
        "tier4_22m_20260501_custom_runtime_task_micro_loop_local": "Passed local Tier 4.22m minimal custom-runtime task micro-loop gate: Tier 4.22l latest pass exists, main.c syntax check passed, a 12-event signed fixed-pattern s16.15 task reference was generated, and source guards confirmed pre-update prediction scoring plus CMD_SCHEDULE_PENDING/CMD_MATURE_PENDING fixed-point maturation. Reference accuracy was 0.9166666667, tail accuracy was 1.0, final readout_weight_raw=32256, and final readout_bias_raw=0. Local reference evidence only; not hardware evidence, full CRA task learning, v2.1 mechanism transfer, speedup evidence, or final on-chip autonomy.",
        "tier4_22m_20260501_custom_runtime_task_micro_loop_prepared": "Prepared Tier 4.22m minimal custom-runtime task micro-loop package: emits ebrains_jobs/cra_422u and a JobManager run-hardware command for twelve chip-owned pending/readout task events that must match the local s16.15 reference within raw tolerance 1, satisfy tail accuracy 1.0, and finish with pending_created=pending_matured=reward_events=decisions=12, active_pending=0, final readout_weight_raw=32256, and final readout_bias_raw=0. Prepared source package only; not hardware evidence until returned EBRAINS artifacts pass.",
        "tier4_22m_20260501_custom_runtime_task_micro_loop_hardware_pass_ingested": "Passed Tier 4.22m EBRAINS minimal custom-runtime task micro-loop: raw remote status was pass, target acquisition succeeded through pyNN.spiNNaker/SpynnakerDataView on board 10.11.202.65, free core (0,0,4) was selected, .aplx build and app load passed, twelve CMD_SCHEDULE_PENDING/CMD_MATURE_PENDING task events succeeded, each mature command matured exactly one pending horizon, prediction/weight/bias raw deltas were all 0, observed accuracy was 0.9166666667, tail accuracy was 1.0, and final state was pending_created=12, pending_matured=12, reward_events=12, decisions=12, active_pending=0, readout_weight_raw=32256, readout_bias_raw=0. Minimal fixed-pattern custom-runtime task micro-loop evidence only; not full CRA task learning, v2.1 mechanism transfer, speedup evidence, multi-core scaling, or final on-chip autonomy.",
        "tier4_22n_20260501_delayed_cue_micro_task_local": "Passed local Tier 4.22n tiny delayed-cue custom-runtime micro-task gate: Tier 4.22m latest hardware pass exists, main.c syntax check passed, a 12-event signed pending-queue s16.15 reference was generated with pending_gap_depth=2 and max_pending_depth=3, and source guards confirmed pre-update prediction scoring plus CMD_SCHEDULE_PENDING/CMD_MATURE_PENDING fixed-point maturation. Reference accuracy was 0.8333333333, tail accuracy was 1.0, final readout_weight_raw=30720, and final readout_bias_raw=0. Local reference evidence only; not hardware evidence, full CRA task learning, v2.1 mechanism transfer, speedup evidence, or final on-chip autonomy.",
        "tier4_22n_20260501_delayed_cue_micro_task_prepared": "Prepared Tier 4.22n tiny delayed-cue custom-runtime micro-task package: emits ebrains_jobs/cra_422v and a JobManager run-hardware command for twelve chip-owned pending/readout task events that must keep a rolling pending depth of at least 3, mature one oldest pending event per target, match the local s16.15 reference within raw tolerance 1, satisfy tail accuracy 1.0, and finish with pending_created=pending_matured=reward_events=decisions=12, active_pending=0, final readout_weight_raw=30720, and final readout_bias_raw=0. Prepared source package only; not hardware evidence until returned EBRAINS artifacts pass.",
        "tier4_22p_20260501_aba_reentry_micro_task_local": "Passed local Tier 4.22p tiny A-B-A reentry custom-runtime micro-task gate: generated the 30-event signed A-B-A reentry s16.15 reference with pending_gap_depth=2, max_pending_depth=3, accuracy 0.8666666667, tail accuracy 1.0, final readout_weight_raw=30810, and final readout_bias_raw=-1. Local reference evidence only; not hardware evidence, full CRA recurrence, v2.1 mechanism transfer, speedup evidence, or final autonomy.",
        "tier4_22p_20260501_aba_reentry_micro_task_prepared": "Prepared Tier 4.22p tiny A-B-A reentry custom-runtime package: emits ebrains_jobs/cra_422y and a JobManager run-hardware command for thirty chip-owned pending/readout reentry events that must keep a rolling pending depth of at least 3, match the local s16.15 reference, and finish with pending_created=pending_matured=reward_events=decisions=30, active_pending=0, final readout_weight_raw=30810, and final readout_bias_raw=-1. Prepared source package only; not hardware evidence until returned EBRAINS artifacts pass.",
        "tier4_22p_20260501_aba_reentry_micro_task_hardware_pass_ingested": "Passed Tier 4.22p EBRAINS tiny A-B-A reentry custom-runtime micro-task: raw remote status was pass, target acquisition succeeded through pyNN.spiNNaker/SpynnakerDataView on board 10.11.222.17, free core (0,0,4) was selected, .aplx build and app load passed, thirty CMD_SCHEDULE_PENDING/CMD_MATURE_PENDING pairs succeeded, prediction/weight/bias raw deltas were all 0, observed accuracy was 0.8666666667, tail accuracy was 1.0, and final state was pending_created=30, pending_matured=30, reward_events=30, decisions=30, active_pending=0, readout_weight_raw=30810, readout_bias_raw=-1. Tiny A-B-A reentry evidence only; not full CRA recurrence, v2.1 mechanism transfer, speedup evidence, multi-core scaling, or final autonomy.",
        "tier4_22q_20260501_integrated_v2_bridge_smoke_local": "Passed local Tier 4.22q tiny integrated host-v2/custom-runtime bridge smoke: generated a 30-event signed stream from a host-side keyed-context plus route-state bridge, with context keys ctx_A/ctx_B/ctx_C, context updates 9, route updates 9, max keyed slots 3, pending_gap_depth=2, max_pending_depth=3, accuracy 0.9333333333, tail accuracy 1.0, final readout_weight_raw=32768, and final readout_bias_raw=0. Local reference evidence only; not hardware evidence, native/on-chip v2 memory/routing, full CRA task learning, speedup evidence, or final autonomy.",
        "tier4_22q_20260501_integrated_v2_bridge_smoke_prepared": "Prepared Tier 4.22q tiny integrated host-v2/custom-runtime bridge smoke package: emits ebrains_jobs/cra_422z and a JobManager run-hardware command for thirty chip-owned pending/readout events generated by a host keyed-context plus route-state transform. Prepared source package only; not hardware evidence until returned EBRAINS artifacts pass. A returned pass would prove only the tiny bridge smoke, not native/on-chip v2 memory/routing, full CRA task learning, speedup evidence, scaling, or final autonomy.",
        "tier4_22q_20260501_integrated_v2_bridge_smoke_hardware_pass_ingested": "Passed Tier 4.22q EBRAINS tiny integrated host-v2/custom-runtime bridge smoke: raw remote status was pass, target acquisition succeeded through pyNN.spiNNaker/SpynnakerDataView on board 10.11.236.65, free core (0,0,4) was selected, .aplx build and app load passed, thirty CMD_SCHEDULE_PENDING/CMD_MATURE_PENDING pairs succeeded, bridge context/route updates were 9/9, max keyed slots was 3, prediction/weight/bias raw deltas were all 0, observed accuracy was 0.9333333333, tail accuracy was 1.0, and final state was pending_created=30, pending_matured=30, reward_events=30, decisions=30, active_pending=0, readout_weight_raw=32768, readout_bias_raw=0. Tiny integrated bridge evidence only; not native/on-chip v2 memory/routing, full CRA task learning, speedup evidence, multi-core scaling, or final autonomy.",
        "tier4_22r_20260501_native_context_state_smoke_local": "Passed local Tier 4.22r tiny native context-state custom-runtime smoke: generated a 30-event signed stream where the chip-side contract retrieves keyed context and computes feature=context*cue, with context keys ctx_A/ctx_B/ctx_C, key ids 101/202/303, context writes 9, context reads 30, max native context slots 3, pending_gap_depth=2, max_pending_depth=3, accuracy 0.9333333333, tail accuracy 1.0, final readout_weight_raw=32752, and final readout_bias_raw=-16. Local reference evidence only; not hardware evidence, full native v2.1 memory/routing, full CRA task learning, speedup evidence, or final autonomy.",
        "tier4_22r_20260501_native_context_state_smoke_prepared": "Prepared Tier 4.22r tiny native context-state custom-runtime smoke package: emits ebrains_jobs/cra_422aa and a JobManager run-hardware command for thirty chip-owned pending/readout events where the host writes keyed context slots and the runtime computes feature=context*cue from key+cue. Prepared source package only; not hardware evidence until returned EBRAINS artifacts pass. A returned pass would prove only the tiny native keyed-context state primitive, not full native v2.1 memory/routing, full CRA task learning, speedup evidence, scaling, or final autonomy.",
        "tier4_22r_20260501_native_context_state_smoke_hardware_pass_ingested": "Passed Tier 4.22r EBRAINS tiny native context-state custom-runtime smoke: raw remote status was pass, target acquisition succeeded through pyNN.spiNNaker/SpynnakerDataView on board 10.11.237.25, free core (0,0,4) was selected, .aplx build and app load passed, thirty context/schedule/mature events succeeded, context writes were 9, context reads were 30, max native context slots was 3, feature/context/prediction/weight/bias raw deltas were all 0, observed accuracy was 0.9333333333, tail accuracy was 1.0, and final state was pending_created=30, pending_matured=30, reward_events=30, decisions=30, active_pending=0, readout_weight_raw=32752, readout_bias_raw=-16. Tiny native keyed-context state evidence only; not full native v2.1 memory/routing, full CRA task learning, speedup evidence, multi-core scaling, or final autonomy.",
        "tier4_22s_20260501_native_route_state_smoke_local": "Passed local Tier 4.22s tiny native route-state custom-runtime smoke: generated a 30-event signed stream where the chip-side contract retrieves keyed context plus chip-owned route state and computes feature=context*route*cue, with context keys ctx_A/ctx_B/ctx_C, context writes 9, context reads 30, route writes 9, route reads 30, route values -1 and 1, pending_gap_depth=2, max_pending_depth=3, accuracy 0.9333333333, tail accuracy 1.0, final readout_weight_raw=32768, and final readout_bias_raw=0. Local reference evidence only; not hardware evidence, full native v2.1 memory/routing, full CRA task learning, speedup evidence, or final autonomy.",
        "tier4_22s_20260501_native_route_state_smoke_prepared": "Prepared Tier 4.22s tiny native route-state custom-runtime smoke package: emits ebrains_jobs/cra_422ab and JobManager command `cra_422ab/experiments/tier4_22s_native_route_state_smoke.py --mode run-hardware --output-dir tier4_22s_job_output` for thirty chip-owned pending/readout events where the host writes keyed context and route state, then the runtime computes feature=context*route*cue from key+cue. Prepared source package only; not hardware evidence until returned EBRAINS artifacts pass. A returned pass would prove only the tiny native route-state primitive layered on native context, not full native v2.1 memory/routing, full CRA task learning, speedup evidence, scaling, or final autonomy.",
        "tier4_22s_20260501_native_route_state_smoke_hardware_pass_ingested": "Passed Tier 4.22s EBRAINS tiny native route-state custom-runtime smoke after ingest correction: raw remote status was fail because the runner incorrectly expected route_writes in the final CMD_READ_ROUTE reply, but returned hardware data show target acquisition through pyNN.spiNNaker/SpynnakerDataView on board 10.11.237.89, free core (0,0,4), .aplx build/load pass, thirty context/route/schedule/mature events succeeded, observed CMD_WRITE_ROUTE counter reached 9, final route reads were 31, chip-computed feature/context/route/prediction/weight/bias raw deltas were all 0, observed accuracy was 0.9333333333, tail accuracy was 1.0, and final state was pending_created=30, pending_matured=30, reward_events=30, decisions=30, active_pending=0, readout_weight_raw=32768, readout_bias_raw=0. Tiny native route-state evidence only; not full native v2.1 memory/routing, full CRA task learning, speedup evidence, multi-core scaling, or final autonomy.",
        "tier4_22t_20260501_native_keyed_route_state_smoke_local": "Passed local Tier 4.22t tiny native keyed route-state custom-runtime smoke: generated a 30-event signed stream where the chip-side contract retrieves keyed context plus keyed route slots and computes feature=context[key]*route[key]*cue, with context keys ctx_A/ctx_B/ctx_C, context writes 9, context reads 30, route-slot writes 15, route-slot reads 30, max route slots 3, route values -1 and 1, pending_gap_depth=2, max_pending_depth=3, accuracy 0.9333333333, tail accuracy 1.0, final readout_weight_raw=32768, and final readout_bias_raw=0. Local reference evidence only; not hardware evidence, full native v2.1 memory/routing, full CRA task learning, speedup evidence, or final autonomy.",
        "tier4_22t_20260501_native_keyed_route_state_smoke_prepared": "Prepared Tier 4.22t tiny native keyed route-state custom-runtime smoke package: emits ebrains_jobs/cra_422ac and JobManager command `cra_422ac/experiments/tier4_22t_native_keyed_route_state_smoke.py --mode run-hardware --output-dir tier4_22t_job_output` for thirty chip-owned pending/readout events where the host writes keyed context and keyed route slots, then the runtime computes feature=context[key]*route[key]*cue from key+cue. Prepared source package only; not hardware evidence until returned EBRAINS artifacts pass. A returned pass would prove only the tiny keyed route-state primitive layered on native context, not full native v2.1 memory/routing, full CRA task learning, speedup evidence, scaling, or final autonomy.",
        "tier4_22t_20260501_native_keyed_route_state_smoke_hardware_pass_ingested": "Passed Tier 4.22t EBRAINS tiny native keyed route-state custom-runtime smoke: raw remote status was pass, target acquisition succeeded through pyNN.spiNNaker/SpynnakerDataView on board 10.11.235.25, free core (0,0,4), .aplx build/load pass, thirty context/route-slot/schedule/mature events succeeded, observed CMD_WRITE_ROUTE_SLOT counter reached 15, active route slots reached 3, route-slot hits/misses were 33/0, chip-computed feature/context/route/prediction/weight/bias raw deltas were all 0, observed accuracy was 0.9333333333, tail accuracy was 1.0, and final state was pending_created=30, pending_matured=30, reward_events=30, decisions=30, active_pending=0, readout_weight_raw=32768, readout_bias_raw=0. Tiny native keyed route-state evidence only; not full native v2.1 memory/routing, full CRA task learning, speedup evidence, multi-core scaling, or final autonomy.",
        "tier4_22u_20260501_native_memory_route_state_smoke_local": "Passed local Tier 4.22u tiny native memory-route custom-runtime smoke: generated a 30-event signed stream where the chip-side contract retrieves keyed context, keyed route slots, and keyed memory/working-state slots, then computes feature=context[key]*route[key]*memory[key]*cue. Context writes/reads were 9/30, route-slot writes/reads were 15/30, memory-slot writes/reads were 15/30, max context/route/memory slots were 3/3/3, route and memory values covered -1 and 1, pending_gap_depth=2, max_pending_depth=3, accuracy was 0.9666666667, tail accuracy was 1.0, final readout_weight_raw=32768, and final readout_bias_raw=0. Local reference evidence only; not hardware evidence, full native v2.1 memory/routing, full CRA task learning, speedup evidence, or final autonomy.",
        "tier4_22u_20260501_native_memory_route_state_smoke_prepared": "Prepared Tier 4.22u tiny native memory-route custom-runtime smoke package: emits ebrains_jobs/cra_422ad and JobManager command `cra_422ad/experiments/tier4_22u_native_memory_route_state_smoke.py --mode run-hardware --output-dir tier4_22u_job_output` for thirty chip-owned pending/readout events where the host writes keyed context, keyed route slots, and keyed memory/working-state slots, then the runtime computes feature=context[key]*route[key]*memory[key]*cue from key+cue. Prepared source package only; not hardware evidence until returned EBRAINS artifacts pass. A returned pass would prove only the tiny memory-route state primitive layered on native context and keyed route state, not full native v2.1 memory/routing, full CRA task learning, speedup evidence, scaling, or final autonomy.",
        "tier4_22u_20260501_native_memory_route_state_smoke_hardware_pass_ingested": "Passed Tier 4.22u EBRAINS tiny native memory-route custom-runtime smoke: raw remote status was pass, target acquisition succeeded through pyNN.spiNNaker/SpynnakerDataView on board 10.11.235.89, free core (0,0,4), .aplx build/load pass, thirty context/route-slot/memory-slot/schedule/mature events succeeded, final route-slot writes/hits/misses were 15/33/0, final memory-slot writes/hits/misses were 15/33/0, active route and memory slots were 3/3, chip-computed feature/context/route/memory/prediction/weight/bias raw deltas were all 0, observed accuracy was 0.9666666667, tail accuracy was 1.0, and final state was pending_created=30, pending_matured=30, reward_events=30, decisions=30, active_pending=0, readout_weight_raw=32768, readout_bias_raw=0. Tiny native memory-route evidence only; not full native v2.1 memory/routing, full CRA task learning, speedup evidence, multi-core scaling, or final autonomy.",
        "tier4_22v_20260501_native_memory_route_reentry_composition_smoke_local": "Passed local Tier 4.22v tiny native memory-route reentry/composition custom-runtime smoke: generated a harder 48-event signed stream with four keyed context/route/memory slots, independent context/route/memory updates, interleaved recalls, and reentry pressure while preserving the chip-side contract feature=context[key]*route[key]*memory[key]*cue. Context writes/reads were 18/48, route-slot writes/reads were 21/48, memory-slot writes/reads were 21/48, max context/route/memory slots were 4/4/4, route and memory values covered -1 and 1, pending_gap_depth=2, max_pending_depth=3, accuracy was 0.9375, tail accuracy was 1.0, final readout_weight_raw=32768, and final readout_bias_raw=0. Local reference evidence only; not hardware evidence, full native v2.1 memory/routing, full CRA task learning, speedup evidence, or final autonomy.",
        "tier4_22v_20260501_native_memory_route_reentry_composition_smoke_prepared": "Prepared Tier 4.22v tiny native memory-route reentry/composition custom-runtime smoke package: emits ebrains_jobs/cra_422ae and JobManager command `cra_422ae/experiments/tier4_22v_native_memory_route_reentry_composition_smoke.py --mode run-hardware --output-dir tier4_22v_job_output` for forty-eight chip-owned pending/readout events where the host writes keyed context, keyed route slots, and keyed memory/working-state slots, then the runtime computes feature=context[key]*route[key]*memory[key]*cue from key+cue under longer interleaved reentry pressure. Prepared source package only; not hardware evidence until returned EBRAINS artifacts pass. A returned pass would prove only the tiny harder memory-route reentry/composition primitive layered on native context, route, and memory state, not full native v2.1 memory/routing, full CRA task learning, speedup evidence, scaling, or final autonomy.",
        "tier4_22v_20260501_native_memory_route_reentry_composition_smoke_hardware_pass_ingested": "Passed Tier 4.22v EBRAINS tiny native memory-route reentry/composition custom-runtime smoke: raw remote status was pass, target acquisition succeeded through pyNN.spiNNaker/SpynnakerDataView on board 10.11.240.153, free core (0,0,4), .aplx build/load pass, forty-eight context/route-slot/memory-slot/schedule/mature events succeeded, final route-slot writes/hits/misses were 21/52/0, final memory-slot writes/hits/misses were 21/52/0, active route and memory slots were 4/4, chip-computed feature/context/route/memory/prediction/weight/bias raw deltas were all 0, observed accuracy was 0.9375, tail accuracy was 1.0, and final state was pending_created=48, pending_matured=48, reward_events=48, decisions=48, active_pending=0, readout_weight_raw=32768, readout_bias_raw=0. Tiny harder native memory-route reentry/composition evidence only; not full native v2.1 memory/routing, full CRA task learning, speedup evidence, multi-core scaling, or final autonomy.",
        "tier4_22w_20260501_native_decoupled_memory_route_composition_smoke_local_profiled": "Passed local Tier 4.22w tiny native decoupled memory-route composition custom-runtime smoke: generated a 48-event signed stream with independent context, route, and memory key spaces. The reference uses context keys ctx_A/ctx_B/ctx_C/ctx_D, route keys route_A/route_B/route_C/route_D, memory keys mem_A/mem_B/mem_C/mem_D, and requires the chip-side contract feature=context[context_key]*route[route_key]*memory[memory_key]*cue. Context writes/reads were 18/48, route-slot writes/reads were 15/48, memory-slot writes/reads were 18/48, max context/route/memory slots were 4/4/4, route and memory values covered -1 and 1, pending_gap_depth=2, max_pending_depth=3, accuracy was 0.9583333333, tail accuracy was 1.0, final readout_weight_raw=32768, and final readout_bias_raw=0. Local reference evidence only; not hardware evidence, full native v2.1 memory/routing, full CRA task learning, speedup evidence, or final autonomy.",
        "tier4_22w_20260501_native_decoupled_memory_route_composition_smoke_prepared_profiled": "Prepared Tier 4.22w tiny native decoupled memory-route composition custom-runtime smoke package: emits ebrains_jobs/cra_422ag, RUNTIME_PROFILE=decoupled_memory_route, and JobManager command `cra_422ag/experiments/tier4_22w_native_decoupled_memory_route_composition_smoke.py --mode run-hardware --output-dir tier4_22w_job_output` for forty-eight chip-owned pending/readout events where the host writes keyed context, keyed route slots, and keyed memory/working-state slots, then schedules with independent context_key, route_key, memory_key, cue, and delay via CMD_SCHEDULE_DECOUPLED_MEMORY_ROUTE_CONTEXT_PENDING. Prepared source package only; not hardware evidence until returned EBRAINS artifacts pass. A returned pass would prove only the tiny independent-key composition primitive layered on native context, route, and memory state, not full native v2.1 memory/routing, full CRA task learning, speedup evidence, scaling, or final autonomy.",
        "tier4_22w_20260501_ebrains_itcm_overflow_fail_ingested": "Failed noncanonical Tier 4.22w EBRAINS attempt: cra_422af never acquired a target, loaded an app, or ran the task because the unprofiled custom-runtime .aplx link failed with RO_DATA will not fit in region ITCM and region ITCM overflowed by 16 bytes. Preserved as build-size/resource-budget evidence. Repair is cra_422ag with RUNTIME_PROFILE=decoupled_memory_route, C schedule-path deduplication, and size-optimized hardware build.",
        "tier4_22k_20260430_spin1api_event_discovery_prepared": "Prepared Tier 4.22k Spin1API event-symbol discovery package: emits ebrains_jobs/cra_422k and a JobManager command that inspects the EBRAINS Spin1API headers, writes a header inventory, and compiles callback probes for timer/SDP/multicast event candidates. Prepared toolchain-discovery package only; not board, command-roundtrip, learning, or speedup evidence.",
        "tier4_22k_20260430_ebrains_event_symbol_discovery_pass": "Passed Tier 4.22k EBRAINS Spin1API event-symbol discovery: the job image exposed /home/jovyan/spinnaker/spinnaker_tools/include, spin1_callback_on, MC_PACKET_RECEIVED, and MCPL_PACKET_RECEIVED; timer, SDP, and both official MC receive callback probes compiled with arm-none-eabi-gcc while legacy guessed MC_PACKET_RX/MCPL_PACKET_RX failed. Toolchain/header discovery only; not board execution, command round-trip, learning, or speedup evidence.",
        "tier4_23a_20260501_continuous_local_reference": "Passed local Tier 4.23a continuous / stop-batching parity reference: the fixed-point continuous event-loop reference matches the chunked 4.22x reference exactly with all feature/prediction/weight/bias raw deltas 0, accuracy 0.958333, tail accuracy 1.0, max pending depth 3, autonomous timesteps 50, and zero host interventions. Local reference evidence only; not hardware evidence, full continuous on-chip learning, speedup evidence, or multi-core scaling.",
        "tier4_23c_20260501_hardware_pass_ingested": "Passed Tier 4.23c EBRAINS one-board hardware continuous smoke: board 10.11.235.9, core (0,0,4), .aplx build/load pass, all 12 state writes succeeded, all 48 schedule uploads succeeded, run_continuous and pause succeeded, final state read succeeded, final readout_weight_raw=32768, readout_bias_raw=0, decisions=48, reward_events=48, pending_created=48, pending_matured=48, active_pending=0, stopped_timestep=6170, 22/22 run-hardware criteria passed, 15/15 ingest criteria passed, zero synthetic fallback. Timer-driven autonomous event-loop evidence only; not full native v2.1, not speedup evidence, not multi-core scaling, and not final on-chip autonomy.",
        "tier4_26_20260502_pass_ingested": "Passed Tier 4.26 EBRAINS four-core distributed context/route/memory/learning smoke: board 10.11.194.1, cores 4/5/6/7, four independent .aplx builds passed, four core loads passed, all state writes succeeded, all 48 schedule uploads succeeded, all four run_continuous and pause commands succeeded, all four final reads succeeded, learning core final state decisions=48, reward_events=48, pending_created=48, pending_matured=48, active_pending=0, readout_weight_raw=32768, readout_bias_raw=0, context core served 48 lookup hits, 30/30 criteria passed, zero synthetic fallback. Distributed multi-core CRA mechanism evidence only; not speedup evidence, not multi-chip scaling, not a general multi-core framework, and not full native v2.1 autonomy.",
        "tier4_24_20260501_resource_characterization": "Passed Tier 4.24 custom runtime resource characterization: continuous path uses 64 commands vs 134 for chunked 4.22x (52.2% reduction), 2647 bytes payload vs 4099 chunked (35.4% reduction), load time 2.187s, task time 4.327s, DTCM estimate 6372 bytes, max pending depth 3, max schedule entries 64, active context/route/memory slots 4/4/4. Resource-measurement evidence only; does not prove speedup, multi-core scaling, or final autonomy.",
        "tier4_28e_pointB_20260503_boundary_confirmed": "Predicted schedule-overflow boundary confirmed on hardware: board 10.11.193.129, 78 events generated, 64 schedule uploads succeeded (indices 0-63), 14 rejected (indices 64-77). learning_core pending_created=64 (capped at MAX_SCHEDULE_ENTRIES), lookup_requests=192 (64x3), stale=0, timeouts=0, no crashes. This is the intended failure-envelope probe: the local sweep predicted schedule_overflow at >64 entries, and hardware confirmed the exact boundary. Preserved as noncanonical runtime-limit diagnostic evidence. Not a canonical pass claim.",
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

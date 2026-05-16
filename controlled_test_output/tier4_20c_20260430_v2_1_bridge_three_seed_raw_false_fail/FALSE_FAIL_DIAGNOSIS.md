# Tier 4.20c Raw False-Fail Diagnosis

- Raw status: `fail`
- Raw failure: `Failed criteria: Tier 4.20b prerequisite pass recorded`
- Corrected ingested evidence: `<repo>/controlled_test_output/tier4_20c_20260430_v2_1_bridge_three_seed_hardware_pass_ingested`

The returned EBRAINS run executed six child hardware runs successfully, but the Tier 4.20c wrapper failed because the fresh upload did not include `controlled_test_output/tier4_20b_latest_manifest.json`. That local prerequisite should not be required inside the minimal EBRAINS source bundle.

Child hardware summary from the raw manifest:

```json
{
  "baseline": "v2.1",
  "bridge_profile": {
    "contract_declared_not_native_yet": [
      "keyed context memory",
      "replay / consolidation",
      "visible predictive context / predictive binding",
      "composition and module routing",
      "self-evaluation / reliability monitoring"
    ],
    "explicitly_excluded": [
      "macro eligibility residual trace"
    ],
    "included_in_child_runner": [
      "PendingHorizon delayed credit / delayed_lr_0_20"
    ],
    "macro_eligibility_enabled": false,
    "profile_name": "v2_1_chunked_bridge_probe",
    "rows": 7
  },
  "child_backend": "pyNN.spiNNaker",
  "child_chunk_size_steps": null,
  "child_execution_mode": "in_process",
  "child_failure_reason": "",
  "child_hardware_run_attempted": true,
  "child_learning_location": null,
  "child_return_code": 0,
  "child_runs": 6,
  "child_runtime_mode": null,
  "child_runtime_seconds_mean": 262.68560729618184,
  "child_seeds": [
    42,
    43,
    44
  ],
  "child_sim_run_failures_sum": 0,
  "child_status": "pass",
  "child_summary_read_failures_sum": 0,
  "child_synthetic_fallbacks_sum": 0,
  "child_task_summaries": [
    {
      "all_accuracy_max": 0.9933333333333333,
      "all_accuracy_mean": 0.9933333333333333,
      "all_accuracy_min": 0.9933333333333333,
      "all_accuracy_std": 0.0,
      "evaluation_count_max": 150.0,
      "evaluation_count_mean": 150.0,
      "evaluation_count_min": 150.0,
      "evaluation_count_std": 0.0,
      "final_mean_readout_weight_max": -20.0,
      "final_mean_readout_weight_mean": -20.0,
      "final_mean_readout_weight_min": -20.0,
      "final_mean_readout_weight_std": 0.0,
      "final_n_alive_max": 8.0,
      "final_n_alive_mean": 8.0,
      "final_n_alive_min": 8.0,
      "final_n_alive_std": 0.0,
      "max_abs_dopamine_max": 0.0,
      "max_abs_dopamine_mean": 0.0,
      "max_abs_dopamine_min": 0.0,
      "max_abs_dopamine_std": 0.0,
      "mean_abs_dopamine_max": 0.0,
      "mean_abs_dopamine_mean": 0.0,
      "mean_abs_dopamine_min": 0.0,
      "mean_abs_dopamine_std": 0.0,
      "mean_step_spikes_max": 79.17583333333333,
      "mean_step_spikes_mean": 79.16916666666667,
      "mean_step_spikes_min": 79.1625,
      "mean_step_spikes_std": 0.006666666666667709,
      "prediction_target_corr_max": 0.9789657311802621,
      "prediction_target_corr_mean": 0.9789385198657689,
      "prediction_target_corr_min": 0.9789078348647698,
      "prediction_target_corr_std": 2.9104049724223485e-05,
      "runs": 3,
      "runtime_seconds_max": 270.9211954851635,
      "runtime_seconds_mean": 267.063407865741,
      "runtime_seconds_min": 262.5026372070424,
      "runtime_seconds_std": 4.253077678065907,
      "seeds": [
        42,
        43,
        44
      ],
      "sim_run_failures_max": 0.0,
      "sim_run_failures_mean": 0.0,
      "sim_run_failures_min": 0.0,
      "sim_run_failures_std": 0.0,
      "sim_run_failures_sum": 0,
      "summary_read_failures_max": 0.0,
      "summary_read_failures_mean": 0.0,
      "summary_read_failures_min": 0.0,
      "summary_read_failures_std": 0.0,
      "summary_read_failures_sum": 0,
      "synthetic_fallbacks_max": 0.0,
      "synthetic_fallbacks_mean": 0.0,
      "synthetic_fallbacks_min": 0.0,
      "synthetic_fallbacks_std": 0.0,
      "synthetic_fallbacks_sum": 0,
      "tail_accuracy_max": 1.0,
      "tail_accuracy_mean": 1.0,
      "tail_accuracy_min": 1.0,
      "tail_accuracy_std": 0.0,
      "tail_prediction_target_corr_max": 0.9999999999999998,
      "tail_prediction_target_corr_mean": 0.9999999999999997,
      "tail_prediction_target_corr_min": 0.9999999999999997,
      "tail_prediction_target_corr_std": 7.850462293418876e-17,
      "task": "delayed_cue",
      "tier_part": "4.16a",
      "total_births_max": 0.0,
      "total_births_mean": 0.0,
      "total_births_min": 0.0,
      "total_births_std": 0.0,
      "total_births_sum": 0,
      "total_deaths_max": 0.0,
      "total_deaths_mean": 0.0,
      "total_deaths_min": 0.0,
    
```

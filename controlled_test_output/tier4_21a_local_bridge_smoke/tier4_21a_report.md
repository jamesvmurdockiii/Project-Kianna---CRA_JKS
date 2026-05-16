# Tier 4.21a Keyed Context-Memory Hardware Bridge Probe

- Generated: `2026-04-30T15:52:04+00:00`
- Mode: `local-bridge`
- Status: **PASS**
- Output directory: `<repo>/controlled_test_output/tier4_21a_local_bridge_smoke`

Tier 4.21a is a targeted v2 mechanism bridge probe for keyed context memory. It tests the host-side keyed-memory scheduler through the chunked PyNN/SpiNNaker transport path.

## Claim Boundary

- `PREPARED` is not hardware evidence.
- `LOCAL-BRIDGE` is source/logic preflight only.
- `RUN-HARDWARE` with `PASS` is keyed-memory bridge evidence, not native/on-chip memory, custom C, continuous execution, language, planning, or AGI.

## Summary

- baseline: `v2.1`
- runner_revision: `tier4_21a_keyed_memory_bridge_20260430_0000`
- tasks: `['context_reentry_interference']`
- seeds: `[42]`
- variants: `['keyed_context_memory', 'slot_reset_ablation', 'slot_shuffle_ablation', 'wrong_key_ablation']`
- steps: `180`
- population_size: `8`
- chunk_size_steps: `50`
- context_memory_slot_count: `4`
- hardware_run_attempted: `False`
- runs: `4`
- expected_runs: `4`
- sim_run_failures_sum: `0`
- summary_read_failures_sum: `0`
- synthetic_fallbacks_sum: `0`
- total_step_spikes_min: `484`
- keyed_context_memory_updates_sum: `2`
- keyed_feature_active_steps_sum: `5`
- keyed_max_context_memory_slots: `2`

## Task Comparisons

| Task | Keyed all | Keyed tail | Best ablation | Ablation all | Delta all | Delta tail | Updates | Active steps | Slots |
| --- | ---: | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| context_reentry_interference | 1 | 1 | `slot_reset_ablation` | 1 | 0 | 0 | 2 | 5 | 2 |

## Criteria

| Criterion | Value | Rule | Pass |
| --- | --- | --- | --- |
| Tier 4.21a runner revision | `tier4_21a_keyed_memory_bridge_20260430_0000` | `expected current source` | yes |
| source package import path available | `{'canonical_package': '<repo>/coral_reef_spinnaker', 'canonical_package_exists': True, 'action': 'already_canonical', 'aliases_checked': ['<repo>/coral-reef-spinnaker', '<repo>/coral reef spinnaker']}` | `coral_reef_spinnaker exists` | yes |
| Tier 4.20c bridge repeat prerequisite | `{'status': 'pass', 'manifest': '<repo>/controlled_test_output/tier4_20c_20260430_v2_1_bridge_three_seed_hardware_pass_ingested/tier4_20c_results.json', 'mode': 'local-bridge'}` | `status == pass locally OR fresh run-hardware` | yes |
| keyed context-memory included | `['keyed_context_memory', 'slot_reset_ablation', 'slot_shuffle_ablation', 'wrong_key_ablation']` | `contains keyed_context_memory` | yes |
| memory ablation included | `['keyed_context_memory', 'slot_reset_ablation', 'slot_shuffle_ablation', 'wrong_key_ablation']` | `contains at least one ablation` | yes |
| runtime mode is chunked | `chunked` | `fixed` | yes |
| learning location is host | `host` | `fixed` | yes |
| context memory slot count supports keyed binding | `4` | `>= 2` | yes |
| all requested task/seed/variant runs completed | `4` | `== 4` | yes |
| sim.run failures zero | `0` | `== 0` | yes |
| summary/readback failures zero | `0` | `== 0` | yes |
| synthetic fallback zero | `0` | `== 0` | yes |
| keyed memory updates observed | `2` | `> 0` | yes |
| keyed memory feature active at decisions | `5` | `> 0` | yes |
| keyed memory retains more than one slot | `2` | `>= 2` | yes |
| keyed candidate not worse than best memory ablation | `0` | `>= min edge` | yes |

## Artifacts

- `comparisons_csv`: `<repo>/controlled_test_output/tier4_21a_local_bridge_smoke/tier4_21a_comparisons.csv`
- `context_reentry_interference_keyed_context_memory_seed42_timeseries_csv`: `<repo>/controlled_test_output/tier4_21a_local_bridge_smoke/spinnaker_hardware_context_reentry_interference_keyed_context_memory_seed42_timeseries.csv`
- `context_reentry_interference_keyed_context_memory_seed42_timeseries_png`: `<repo>/controlled_test_output/tier4_21a_local_bridge_smoke/spinnaker_hardware_context_reentry_interference_keyed_context_memory_seed42_timeseries.png`
- `context_reentry_interference_slot_reset_ablation_seed42_timeseries_csv`: `<repo>/controlled_test_output/tier4_21a_local_bridge_smoke/spinnaker_hardware_context_reentry_interference_slot_reset_ablation_seed42_timeseries.csv`
- `context_reentry_interference_slot_reset_ablation_seed42_timeseries_png`: `<repo>/controlled_test_output/tier4_21a_local_bridge_smoke/spinnaker_hardware_context_reentry_interference_slot_reset_ablation_seed42_timeseries.png`
- `context_reentry_interference_slot_shuffle_ablation_seed42_timeseries_csv`: `<repo>/controlled_test_output/tier4_21a_local_bridge_smoke/spinnaker_hardware_context_reentry_interference_slot_shuffle_ablation_seed42_timeseries.csv`
- `context_reentry_interference_slot_shuffle_ablation_seed42_timeseries_png`: `<repo>/controlled_test_output/tier4_21a_local_bridge_smoke/spinnaker_hardware_context_reentry_interference_slot_shuffle_ablation_seed42_timeseries.png`
- `context_reentry_interference_wrong_key_ablation_seed42_timeseries_csv`: `<repo>/controlled_test_output/tier4_21a_local_bridge_smoke/spinnaker_hardware_context_reentry_interference_wrong_key_ablation_seed42_timeseries.csv`
- `context_reentry_interference_wrong_key_ablation_seed42_timeseries_png`: `<repo>/controlled_test_output/tier4_21a_local_bridge_smoke/spinnaker_hardware_context_reentry_interference_wrong_key_ablation_seed42_timeseries.png`
- `manifest_json`: `<repo>/controlled_test_output/tier4_21a_local_bridge_smoke/tier4_21a_results.json`
- `report_md`: `<repo>/controlled_test_output/tier4_21a_local_bridge_smoke/tier4_21a_report.md`
- `summary_csv`: `<repo>/controlled_test_output/tier4_21a_local_bridge_smoke/tier4_21a_summary.csv`

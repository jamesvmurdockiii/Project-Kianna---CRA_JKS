# Tier 4.21a Keyed Context-Memory Hardware Bridge Probe

- Generated: `2026-04-30T17:12:07+00:00`
- Mode: `ingest`
- Status: **PASS**
- Output directory: `<repo>/controlled_test_output/tier4_21a_20260430_keyed_context_memory_seed42_hardware_pass_ingested`

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
- steps: `720`
- population_size: `8`
- chunk_size_steps: `50`
- context_memory_slot_count: `4`
- hardware_run_attempted: `True`
- runs: `4`
- expected_runs: `4`
- sim_run_failures_sum: `0`
- summary_read_failures_sum: `0`
- synthetic_fallbacks_sum: `0`
- total_step_spikes_min: `714601`
- keyed_context_memory_updates_sum: `11`
- keyed_feature_active_steps_sum: `20`
- keyed_max_context_memory_slots: `4`

## Task Comparisons

| Task | Keyed all | Keyed tail | Best ablation | Ablation all | Delta all | Delta tail | Updates | Active steps | Slots |
| --- | ---: | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| context_reentry_interference | 1 | 1 | `slot_reset_ablation` | 0.5 | 0.5 | 0 | 11 | 20 | 4 |

## Criteria

| Criterion | Value | Rule | Pass |
| --- | --- | --- | --- |
| Tier 4.21a runner revision | `tier4_21a_keyed_memory_bridge_20260430_0000` | `expected current source` | yes |
| source package import path available | `{'action': 'already_canonical', 'aliases_checked': ['<jobmanager_tmp>', '<jobmanager_tmp> reef spinnaker'], 'canonical_package': '<jobmanager_tmp>', 'canonical_package_exists': True}` | `coral_reef_spinnaker exists` | yes |
| Tier 4.20c bridge repeat prerequisite | `{'manifest': None, 'mode': 'run-hardware', 'status': 'missing'}` | `status == pass locally OR fresh run-hardware` | yes |
| keyed context-memory included | `['keyed_context_memory', 'slot_reset_ablation', 'slot_shuffle_ablation', 'wrong_key_ablation']` | `contains keyed_context_memory` | yes |
| memory ablation included | `['keyed_context_memory', 'slot_reset_ablation', 'slot_shuffle_ablation', 'wrong_key_ablation']` | `contains at least one ablation` | yes |
| runtime mode is chunked | `chunked` | `fixed` | yes |
| learning location is host | `host` | `fixed` | yes |
| context memory slot count supports keyed binding | `4` | `>= 2` | yes |
| all requested task/seed/variant runs completed | `4` | `== 4` | yes |
| sim.run failures zero | `0` | `== 0` | yes |
| summary/readback failures zero | `0` | `== 0` | yes |
| synthetic fallback zero | `0` | `== 0` | yes |
| keyed memory updates observed | `11` | `> 0` | yes |
| keyed memory feature active at decisions | `20` | `> 0` | yes |
| keyed memory retains more than one slot | `4` | `>= 2` | yes |
| keyed candidate not worse than best memory ablation | `0.5` | `>= min edge` | yes |
| real spike readback nonzero | `714601` | `> 0` | yes |

## Artifacts

- `comparisons_csv`: `<repo>/controlled_test_output/tier4_21a_20260430_keyed_context_memory_seed42_hardware_pass_ingested/tier4_21a_comparisons.csv`
- `context_reentry_interference_keyed_context_memory_seed42_timeseries_csv`: `<jobmanager_tmp>`
- `context_reentry_interference_keyed_context_memory_seed42_timeseries_png`: `<jobmanager_tmp>`
- `context_reentry_interference_slot_reset_ablation_seed42_timeseries_csv`: `<jobmanager_tmp>`
- `context_reentry_interference_slot_reset_ablation_seed42_timeseries_png`: `<jobmanager_tmp>`
- `context_reentry_interference_slot_shuffle_ablation_seed42_timeseries_csv`: `<jobmanager_tmp>`
- `context_reentry_interference_slot_shuffle_ablation_seed42_timeseries_png`: `<jobmanager_tmp>`
- `context_reentry_interference_wrong_key_ablation_seed42_timeseries_csv`: `<jobmanager_tmp>`
- `context_reentry_interference_wrong_key_ablation_seed42_timeseries_png`: `<jobmanager_tmp>`
- `manifest_json`: `<repo>/controlled_test_output/tier4_21a_20260430_keyed_context_memory_seed42_hardware_pass_ingested/tier4_21a_results.json`
- `report_md`: `<repo>/controlled_test_output/tier4_21a_20260430_keyed_context_memory_seed42_hardware_pass_ingested/tier4_21a_report.md`
- `summary_csv`: `<repo>/controlled_test_output/tier4_21a_20260430_keyed_context_memory_seed42_hardware_pass_ingested/tier4_21a_summary.csv`

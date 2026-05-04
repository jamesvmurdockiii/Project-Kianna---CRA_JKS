# Tier 4.21a Keyed Context-Memory Hardware Bridge Probe

- Generated: `2026-04-30T15:52:15+00:00`
- Mode: `prepare`
- Status: **PREPARED**
- Output directory: `/Users/james/JKS:CRA/controlled_test_output/tier4_21a_20260430_prepared`

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
- hardware_run_attempted: `False`

## Task Comparisons

| Task | Keyed all | Keyed tail | Best ablation | Ablation all | Delta all | Delta tail | Updates | Active steps | Slots |
| --- | ---: | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: |

## Criteria

| Criterion | Value | Rule | Pass |
| --- | --- | --- | --- |
| Tier 4.21a runner revision | `tier4_21a_keyed_memory_bridge_20260430_0000` | `expected current source` | yes |
| source package import path available | `{'canonical_package': '/Users/james/JKS:CRA/coral_reef_spinnaker', 'canonical_package_exists': True, 'action': 'already_canonical', 'aliases_checked': ['/Users/james/JKS:CRA/coral-reef-spinnaker', '/Users/james/JKS:CRA/coral reef spinnaker']}` | `coral_reef_spinnaker exists` | yes |
| Tier 4.20c bridge repeat prerequisite | `{'status': 'pass', 'manifest': '/Users/james/JKS:CRA/controlled_test_output/tier4_20c_20260430_v2_1_bridge_three_seed_hardware_pass_ingested/tier4_20c_results.json', 'mode': 'prepare'}` | `status == pass locally OR fresh run-hardware` | yes |
| keyed context-memory included | `['keyed_context_memory', 'slot_reset_ablation', 'slot_shuffle_ablation', 'wrong_key_ablation']` | `contains keyed_context_memory` | yes |
| memory ablation included | `['keyed_context_memory', 'slot_reset_ablation', 'slot_shuffle_ablation', 'wrong_key_ablation']` | `contains at least one ablation` | yes |
| runtime mode is chunked | `chunked` | `fixed` | yes |
| learning location is host | `host` | `fixed` | yes |
| context memory slot count supports keyed binding | `4` | `>= 2` | yes |

## Artifacts

- `capsule_config_json`: `/Users/james/JKS:CRA/controlled_test_output/tier4_21a_20260430_prepared/jobmanager_capsule/capsule_config.json`
- `capsule_dir`: `/Users/james/JKS:CRA/controlled_test_output/tier4_21a_20260430_prepared/jobmanager_capsule`
- `comparisons_csv`: `/Users/james/JKS:CRA/controlled_test_output/tier4_21a_20260430_prepared/tier4_21a_comparisons.csv`
- `expected_outputs_json`: `/Users/james/JKS:CRA/controlled_test_output/tier4_21a_20260430_prepared/jobmanager_capsule/expected_outputs.json`
- `jobmanager_readme`: `/Users/james/JKS:CRA/controlled_test_output/tier4_21a_20260430_prepared/jobmanager_capsule/README_JOBMANAGER.md`
- `manifest_json`: `/Users/james/JKS:CRA/controlled_test_output/tier4_21a_20260430_prepared/tier4_21a_results.json`
- `report_md`: `/Users/james/JKS:CRA/controlled_test_output/tier4_21a_20260430_prepared/tier4_21a_report.md`
- `summary_csv`: `/Users/james/JKS:CRA/controlled_test_output/tier4_21a_20260430_prepared/tier4_21a_summary.csv`

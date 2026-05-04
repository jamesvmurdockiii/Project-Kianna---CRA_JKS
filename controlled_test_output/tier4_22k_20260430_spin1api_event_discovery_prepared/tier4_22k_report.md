# Tier 4.22k Spin1API Event-Symbol Discovery

- Generated: `2026-04-30T20:54:08+00:00`
- Mode: `prepare`
- Status: **PREPARED**
- Output directory: `/Users/james/JKS:CRA/controlled_test_output/tier4_22k_20260430_spin1api_event_discovery_prepared`

Tier 4.22k inspects the EBRAINS Spin1API build image and compiles a callback-symbol probe matrix. It exists because Tier 4.22i reached the raw custom-runtime layer and failed before board execution on callback event-symbol mismatch.

## Claim Boundary

- This is build-image/toolchain discovery evidence only.
- It is not a board load, not a command round-trip, not learning, not speedup, and not hardware transfer of a mechanism.
- If no real multicast receive event macro compiles, custom-runtime learning hardware is blocked until the receive path is repaired with documented Spin1API/SCAMP semantics.

## Summary

- next_step_if_passed: `Run the emitted EBRAINS command and ingest returned Tier 4.22k files.`

## Criteria

| Criterion | Value | Rule | Pass | Note |
| --- | --- | --- | --- | --- |
| runner revision current | `tier4_22k_spin1api_event_discovery_20260430_0001` | `expected current source` | yes |  |
| upload bundle created | `/Users/james/JKS:CRA/controlled_test_output/tier4_22k_20260430_spin1api_event_discovery_prepared/ebrains_upload_bundle/cra_422k` | `exists` | yes |  |
| discovery runner included | `/Users/james/JKS:CRA/controlled_test_output/tier4_22k_20260430_spin1api_event_discovery_prepared/ebrains_upload_bundle/cra_422k/experiments/tier4_22k_spin1api_event_discovery.py` | `exists` | yes |  |
| run-hardware command emitted | `cra_422k/experiments/tier4_22k_spin1api_event_discovery.py --mode run-hardware --output-dir tier4_22k_job_output` | `contains --mode run-hardware` | yes |  |
| stable upload folder refreshed | `/Users/james/JKS:CRA/ebrains_jobs/cra_422k` | `exists` | yes |  |

## Artifacts

- `upload_bundle`: `/Users/james/JKS:CRA/controlled_test_output/tier4_22k_20260430_spin1api_event_discovery_prepared/ebrains_upload_bundle/cra_422k`
- `stable_upload_folder`: `/Users/james/JKS:CRA/ebrains_jobs/cra_422k`
- `job_readme`: `/Users/james/JKS:CRA/controlled_test_output/tier4_22k_20260430_spin1api_event_discovery_prepared/ebrains_upload_bundle/cra_422k/README_TIER4_22K_JOB.md`
- `manifest_json`: `/Users/james/JKS:CRA/controlled_test_output/tier4_22k_20260430_spin1api_event_discovery_prepared/tier4_22k_results.json`
- `report_md`: `/Users/james/JKS:CRA/controlled_test_output/tier4_22k_20260430_spin1api_event_discovery_prepared/tier4_22k_report.md`

## Official Reference Checked

- Official `spin1_api.h`: `https://github.com/SpiNNakerManchester/spinnaker_tools/blob/master/include/spin1_api.h`
- Official `spinnaker.h`: `https://github.com/SpiNNakerManchester/spinnaker_tools/blob/master/include/spinnaker.h`
- Current official source exposes `MC_PACKET_RECEIVED` and `MCPL_PACKET_RECEIVED`; this tier checks whether the EBRAINS image exposes the same symbols.

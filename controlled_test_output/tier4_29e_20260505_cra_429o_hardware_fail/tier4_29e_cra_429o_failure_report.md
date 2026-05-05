# Tier 4.29e cra_429o Hardware Failure Diagnostic

- Ingested: `2026-05-05T12:39:59.208339+00:00`
- Classification: `noncanonical_hardware_failure_diagnostic`
- Package: `cra_429o`
- Runner revision: `tier4_29e_native_replay_consolidation_20260505_0002`
- Status: **FAIL**

## Meaning

The returned files are from the valid current runner and show real SpiNNaker execution. The run is not promoted because the predeclared replay/control tolerance criteria failed consistently on all three seeds.

## Per-Seed Summary

| Seed | Board | Criteria | Failed Criteria | Target | Loads |
| --- | --- | --- | --- | --- | --- |
| 42 | `10.11.225.17` | `32/34` | `wrong_key_replay_hardware_bias_within_tolerance, random_event_replay_hardware_weight_within_tolerance` | `pass` | `{'context': 'pass', 'route': 'pass', 'memory': 'pass', 'learning': 'pass'}` |
| 43 | `10.11.225.145` | `32/34` | `wrong_key_replay_hardware_bias_within_tolerance, random_event_replay_hardware_weight_within_tolerance` | `pass` | `{'context': 'pass', 'route': 'pass', 'memory': 'pass', 'learning': 'pass'}` |
| 44 | `10.11.225.81` | `32/34` | `wrong_key_replay_hardware_bias_within_tolerance, random_event_replay_hardware_weight_within_tolerance` | `pass` | `{'context': 'pass', 'route': 'pass', 'memory': 'pass', 'learning': 'pass'}` |

## Consistent Failure Criteria

- seed `42` `wrong_key_replay_hardware_bias_within_tolerance`: value `0`, threshold `8192`, note `hw=0 ref=36288 diff=36288`
- seed `42` `random_event_replay_hardware_weight_within_tolerance`: value `57344`, threshold `8192`, note `hw=57344 ref=48128 diff=9216`
- seed `43` `wrong_key_replay_hardware_bias_within_tolerance`: value `0`, threshold `8192`, note `hw=0 ref=36288 diff=36288`
- seed `43` `random_event_replay_hardware_weight_within_tolerance`: value `57344`, threshold `8192`, note `hw=57344 ref=48128 diff=9216`
- seed `44` `wrong_key_replay_hardware_bias_within_tolerance`: value `0`, threshold `8192`, note `hw=0 ref=36288 diff=36288`
- seed `44` `random_event_replay_hardware_weight_within_tolerance`: value `57344`, threshold `8192`, note `hw=57344 ref=48128 diff=9216`

## Root-Cause Hypothesis

- Python schedule builder did not preserve per-event wrong context keys for wrong_key_replay.
- Host reference did not fully mirror native continuous-runtime update/order semantics, including native readout bias behavior/tolerance for replay controls.

## Boundary

This is useful hardware diagnostic evidence, not canonical 4.29e pass evidence. It does not authorize Tier 4.29f or a native mechanism bridge freeze.

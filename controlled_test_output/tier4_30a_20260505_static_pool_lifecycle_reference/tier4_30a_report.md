# Tier 4.30a Local Static-Pool Lifecycle Reference

- Generated: `2026-05-05T19:56:20+00:00`
- Runner revision: `tier4_30a_static_pool_reference_20260505_0001`
- Status: **PASS**
- Criteria: `20/20`

## Claim Boundary

Tier 4.30a is a local deterministic reference only. It proves the static-pool lifecycle state model is explicit, bounded, repeatable, and has precomputed sham-control outputs. It does not implement C runtime lifecycle state, does not run hardware, does not prove task benefit, does not freeze a lifecycle baseline, and does not migrate v2.2 temporal state.

## Scenario Summaries

### canonical_32

| Mode | Events | Invalid | Active Mask | Active | Cleavage | Birth | Death | Lineage Checksum | Trophic Checksum |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `enabled` | `32` | `0` | `63` | `6` | `4` | `4` | `4` | `105428` | `466851` |
| `fixed_static_pool_control` | `32` | `13` | `3` | `2` | `0` | `0` | `0` | `5722` | `151469` |
| `random_event_replay_control` | `32` | `30` | `0` | `0` | `0` | `0` | `2` | `6170` | `98304` |
| `active_mask_shuffle_control` | `32` | `29` | `0` | `0` | `0` | `0` | `2` | `6170` | `102480` |
| `lineage_id_shuffle_control` | `32` | `0` | `63` | `6` | `4` | `4` | `4` | `106632` | `466851` |
| `no_trophic_pressure_control` | `32` | `0` | `63` | `6` | `4` | `4` | `4` | `105428` | `336384` |
| `no_dopamine_or_plasticity_control` | `32` | `0` | `63` | `6` | `4` | `4` | `4` | `105428` | `457850` |

- Deterministic repeat: `True`
- Control separation: `{'fixed_static_pool_control': True, 'random_event_replay_control': True, 'active_mask_shuffle_control': True, 'lineage_id_shuffle_control': True, 'no_trophic_pressure_control': True, 'no_dopamine_or_plasticity_control': True}`

### boundary_64

| Mode | Events | Invalid | Active Mask | Active | Cleavage | Birth | Death | Lineage Checksum | Trophic Checksum |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `enabled` | `64` | `0` | `127` | `7` | `8` | `5` | `8` | `18496` | `761336` |
| `fixed_static_pool_control` | `64` | `26` | `3` | `2` | `0` | `0` | `0` | `5722` | `174650` |
| `random_event_replay_control` | `64` | `51` | `8` | `1` | `1` | `1` | `3` | `9234` | `195905` |
| `active_mask_shuffle_control` | `64` | `61` | `0` | `0` | `0` | `0` | `2` | `6170` | `102480` |
| `lineage_id_shuffle_control` | `64` | `0` | `127` | `7` | `8` | `5` | `8` | `25622` | `761336` |
| `no_trophic_pressure_control` | `64` | `0` | `127` | `7` | `8` | `5` | `8` | `18496` | `357824` |
| `no_dopamine_or_plasticity_control` | `64` | `0` | `127` | `7` | `8` | `5` | `8` | `18496` | `724300` |

- Deterministic repeat: `True`
- Control separation: `{'fixed_static_pool_control': True, 'random_event_replay_control': True, 'active_mask_shuffle_control': True, 'lineage_id_shuffle_control': True, 'no_trophic_pressure_control': True, 'no_dopamine_or_plasticity_control': True}`

## Criteria

| Criterion | Value | Rule | Pass | Note |
| --- | --- | --- | --- | --- |
| Tier 4.30 contract passed | `pass` | `== pass` | yes |  |
| contract criteria complete | `14/14` | `== 14/14` | yes |  |
| canonical schedule length | `32` | `== 32` | yes |  |
| boundary schedule length | `64` | `== 64` | yes |  |
| canonical enabled invalid events | `0` | `== 0` | yes |  |
| boundary enabled invalid events | `0` | `== 0` | yes |  |
| canonical event counters match | `32` | `== 32` | yes |  |
| boundary event counters match | `64` | `== 64` | yes |  |
| canonical includes cleavage/birth/death | `{'mode': 'enabled', 'pool_size': 8, 'founder_count': 2, 'active_count': 6, 'inactive_count': 2, 'active_mask_bits': 63, 'lineage_checksum': 105428, 'trophic_checksum': 466851, 'event_count': 32, 'attempted_event_count': 32, 'cleavage_count': 4, 'birth_count': 4, 'death_count': 4, 'invalid_event_count': 0, 'sham_counter': 0, 'max_active_count': 7}` | `all counts >= 1` | yes |  |
| boundary includes cleavage/birth/death | `{'mode': 'enabled', 'pool_size': 8, 'founder_count': 2, 'active_count': 7, 'inactive_count': 1, 'active_mask_bits': 127, 'lineage_checksum': 18496, 'trophic_checksum': 761336, 'event_count': 64, 'attempted_event_count': 64, 'cleavage_count': 8, 'birth_count': 5, 'death_count': 8, 'invalid_event_count': 0, 'sham_counter': 0, 'max_active_count': 8}` | `all counts >= 1` | yes |  |
| canonical capacity bounded | `7` | `<= 8` | yes |  |
| boundary capacity bounded | `8` | `<= 8` | yes |  |
| canonical active/inactive accounting | `{'mode': 'enabled', 'pool_size': 8, 'founder_count': 2, 'active_count': 6, 'inactive_count': 2, 'active_mask_bits': 63, 'lineage_checksum': 105428, 'trophic_checksum': 466851, 'event_count': 32, 'attempted_event_count': 32, 'cleavage_count': 4, 'birth_count': 4, 'death_count': 4, 'invalid_event_count': 0, 'sham_counter': 0, 'max_active_count': 7}` | `active+inactive==pool` | yes |  |
| boundary active/inactive accounting | `{'mode': 'enabled', 'pool_size': 8, 'founder_count': 2, 'active_count': 7, 'inactive_count': 1, 'active_mask_bits': 127, 'lineage_checksum': 18496, 'trophic_checksum': 761336, 'event_count': 64, 'attempted_event_count': 64, 'cleavage_count': 8, 'birth_count': 5, 'death_count': 8, 'invalid_event_count': 0, 'sham_counter': 0, 'max_active_count': 8}` | `active+inactive==pool` | yes |  |
| canonical deterministic repeat | `True` | `== true` | yes |  |
| boundary deterministic repeat | `True` | `== true` | yes |  |
| canonical controls separated | `{'fixed_static_pool_control': True, 'random_event_replay_control': True, 'active_mask_shuffle_control': True, 'lineage_id_shuffle_control': True, 'no_trophic_pressure_control': True, 'no_dopamine_or_plasticity_control': True}` | `all true` | yes |  |
| boundary controls separated | `{'fixed_static_pool_control': True, 'random_event_replay_control': True, 'active_mask_shuffle_control': True, 'lineage_id_shuffle_control': True, 'no_trophic_pressure_control': True, 'no_dopamine_or_plasticity_control': True}` | `all true` | yes |  |
| all modes preserve event budget canonical | `{'enabled': 32, 'fixed_static_pool_control': 32, 'random_event_replay_control': 32, 'active_mask_shuffle_control': 32, 'lineage_id_shuffle_control': 32, 'no_trophic_pressure_control': 32, 'no_dopamine_or_plasticity_control': 32}` | `all == 32` | yes |  |
| all modes preserve event budget boundary | `{'enabled': 64, 'fixed_static_pool_control': 64, 'random_event_replay_control': 64, 'active_mask_shuffle_control': 64, 'lineage_id_shuffle_control': 64, 'no_trophic_pressure_control': 64, 'no_dopamine_or_plasticity_control': 64}` | `all == 64` | yes |  |

## Next Step

Tier 4.30b source audit / single-core lifecycle mask smoke preparation

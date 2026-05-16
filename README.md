# Coral Reef Architecture (CRA)

[![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![Tests](https://img.shields.io/badge/tests-156%20passing-brightgreen.svg)](#validation)
[![Evidence](https://img.shields.io/badge/canonical%20evidence-157%20bundles-blue.svg)](STUDY_EVIDENCE_INDEX.md)

Coral Reef Architecture (CRA) is a neuromorphic learning research platform for
studying local spiking plasticity, delayed credit assignment, population-level
selection, and SpiNNaker hardware execution without relying on global
backpropagation as the organizing learning rule.

The repository is structured as a reproducible research artifact. Claims are tied
to predeclared tiers, generated evidence registries, pass/fail criteria,
controlled ablations, baseline comparisons, and explicit claim boundaries.

## Current Status

| Area | Current state |
| --- | --- |
| Predictive software baseline | **`v2.6`** — frozen by Tier 7.7z-r0 (11/11). Edge-of-chaos recurrent dynamics: decay=0, sr=1.0, antisym=0.3 + ridge readout. PR 2→7 (3.5x), sham Δ=4.5, MSE 56% lower. Beats ESN 2.8x; lag-ridge still wins on NARMA10. v2.5 planning mechanism carried forward. |
| Organism-development diagnostic snapshot | **`v2.7`** — frozen as a NEST diagnostic snapshot only. Healthy-NEST correction shows true organism PR near `1.15-2.05` at 2000 steps and no MSE improvement across tested mechanism configurations. It does **not** supersede `v2.6` as the predictive benchmark baseline. Experimental lifecycle/operator/readout mechanisms are opt-in unless promoted by a later clean gate. |
| Current repository state | Repo-alignment remediation is in Gate 5. Tier 5.45 locked the healthy-NEST rebaseline contract; the Tier 5.45a scoring runner is implemented and smoke-validated, and the full Tier 5.45a scoring run is the next decision gate before any new mechanism promotion or paper claim. |
| Native hardware baseline | `CRA_NATIVE_SCALE_BASELINE_v0.5`, frozen by Tier 4.32h after the 4.32a replicated single-chip stress, 4.32d two-chip communication smoke, 4.32e two-chip learning micro-task, and 4.32g two-chip lifecycle traffic/resource smoke all passed with preserved artifacts and bounded claim boundaries. |
| Latest native-scale closeout | Tier 4.32h passed locally from [`controlled_test_output/tier4_32h_20260508_native_scale_evidence_closeout`](controlled_test_output/tier4_32h_20260508_native_scale_evidence_closeout): `64/64` freeze criteria passed, `CRA_NATIVE_SCALE_BASELINE_v0.5` files were generated under [`baselines/`](baselines), and the next project phase is explicitly software usefulness/baselines before broad new native migration. |
| Latest lifecycle task bridge | Tier 4.30g local contract passed `9/9`, then Tier 4.30g-hw passed on real SpiNNaker: enabled lifecycle bridge gate `1`, controls bridge gate `0`, enabled reference tail accuracy `1.0`, control reference tail accuracy `0.375`, compact lifecycle payload `68`, and zero stale replies/timeouts. |
| Latest software benchmark diagnostic | Tier 7.0j passed and froze v2.3: generic bounded recurrent state improves the locked public scoreboard versus v2.2 and passes full compact regression, while topology-specific recurrence and ESN superiority remain unproven. |
| Latest engineering audit | Tier 4.30-readiness passed `16/16`, selecting a static-pool lifecycle-native path layered on `CRA_NATIVE_MECHANISM_BRIDGE_v0.3` with historical v2.2 as software reference only. |
| Latest engineering contract | Tier 4.30 passed `14/14`, defining lifecycle init/event/trophic/readback/sham commands, `23` readback fields, event invariants, gates, and failure classes. |
| Latest local lifecycle reference | Tier 4.30a passed `20/20`: deterministic 8-slot / 2-founder static-pool state, canonical 32-event trace, boundary 64-event trace, and lifecycle shams. |
| Latest lifecycle runtime source audit | Tier 4.30b passed `13/13`: runtime lifecycle static-pool surface, exact 4.30a checksum parity, lifecycle SDP readback, and existing runtime/profile tests preserved. |
| Latest multi-core lifecycle split | Tier 4.30c passed `22/22`: five-core lifecycle ownership contract, MCPL/multicast-target message semantics, final active-mask sync, exact canonical/boundary parity, and distributed failure classes. |
| Latest multi-core lifecycle runtime source audit | Tier 4.30d passed `14/14`: dedicated `lifecycle_core` runtime profile, lifecycle inter-core stubs/counters, active-mask/count/lineage sync bookkeeping, ownership guards, and local C host tests against the 4.30c contract. |
| Latest temporal hardware pass | Tier 4.31d-hw passed and was ingested from [`controlled_test_output/tier4_31d_hw_20260506_hardware_pass_ingested`](controlled_test_output/tier4_31d_hw_20260506_hardware_pass_ingested): board `10.11.216.121`, runner revision `tier4_31d_native_temporal_hardware_smoke_20260506_0003`, `59/59` remote hardware criteria, `5/5` ingest criteria, compact temporal payload length `48`, enabled/zero/frozen/reset controls all passed, and `21` structured returned artifacts preserved. |
| Latest temporal decision closeout | Tier 4.31e passed `15/15` from [`controlled_test_output/tier4_31e_20260506_native_replay_eligibility_decision_closeout`](controlled_test_output/tier4_31e_20260506_native_replay_eligibility_decision_closeout): native replay buffers, sleep-like replay, and native macro eligibility are deferred until measured blockers exist; Tier 4.31f is deferred; Tier 4.32 mapping/resource modeling is authorized next; no baseline freeze. |
| Latest native resource model | Tier 4.32 passed `23/23` from [`controlled_test_output/tier4_32_20260506_mapping_resource_model`](controlled_test_output/tier4_32_20260506_mapping_resource_model): MCPL is the scale data plane (`16` bytes round trip vs SDP `54`), measured profile builds retain positive ITCM/DTCM headroom, 4.32a single-chip scale stress is authorized next, and no native-scale baseline freeze is authorized yet. |
| Latest single-chip scale preflight | Tier 4.32a passed `19/19` from [`controlled_test_output/tier4_32a_20260506_single_chip_scale_stress`](controlled_test_output/tier4_32a_20260506_single_chip_scale_stress): 4/5-core single-shard MCPL-first stress is authorized next, while replicated 8/12/16-core stress is blocked until Tier 4.32a-r1 adds shard-aware MCPL routing because the current key has no shard/group field and `dest_core` is reserved/ignored. |
| Latest protocol truth audit | Tier 4.32a-r0 passed `10/10` from [`controlled_test_output/tier4_32a_r0_20260506_protocol_truth_audit`](controlled_test_output/tier4_32a_r0_20260506_protocol_truth_audit): the MCPL-first 4.32a-hw package is blocked because confidence-gated learning still uses transitional SDP, MCPL replies drop confidence, MCPL receive hardcodes confidence `1.0`, and the MCPL key lacks shard identity. Tier 4.32a-r1 is now required before MCPL-first scale stress. |
| Latest MCPL protocol repair | Tier 4.32a-r1 passed `14/14` from [`controlled_test_output/tier4_32a_r1_20260506_mcpl_lookup_repair`](controlled_test_output/tier4_32a_r1_20260506_mcpl_lookup_repair): MCPL lookup replies now carry value plus confidence/hit/status metadata, keys carry shard identity, identical seq/type cross-shard controls pass, and full/zero/half-confidence learning controls pass through the repaired MCPL path. |
| Latest single-shard hardware stress | Tier 4.32a-hw passed after EBRAINS ingest from [`controlled_test_output/tier4_32a_hw_20260507_hardware_pass_ingested`](controlled_test_output/tier4_32a_hw_20260507_hardware_pass_ingested): raw remote status `pass`, ingest status `pass`, board `10.11.215.185`, `31/31` raw hardware criteria, `8/8` ingest criteria, `63` returned artifacts, point04 `48` events / `144` lookup replies, point05 `96` events / `288` lookup replies, zero stale replies, zero duplicate replies, zero timeouts, zero synthetic fallback. |
| Latest replicated-shard hardware stress | Tier 4.32a-hw-replicated passed after EBRAINS ingest from [`controlled_test_output/tier4_32a_hw_replicated_20260507_hardware_pass_ingested`](controlled_test_output/tier4_32a_hw_replicated_20260507_hardware_pass_ingested): raw remote status `pass`, ingest status `pass`, board `10.11.215.121`, `185/185` raw hardware criteria, `9/9` ingest criteria, `80` returned artifacts, point08 `2` shards / `192` total events / `288` lookup replies per shard, point12 `3` shards / `384` total events / `384` lookup replies per shard, point16 `4` shards / `512` total events / `384` lookup replies per shard, zero stale replies, zero duplicate replies, zero timeouts, zero synthetic fallback. |
| Latest static reef partition map | Tier 4.32b passed `25/25` from [`controlled_test_output/tier4_32b_20260507_static_reef_partition_smoke`](controlled_test_output/tier4_32b_20260507_static_reef_partition_smoke): canonical `quad_mechanism_partition_v0` maps four reef partitions to `16` measured cores, assigns static polyp slots `0-7` two per partition, preserves `384/384` lookup parity per partition, rejects one-polyp-one-chip as unsupported, and keeps speedup/multi-chip/native-scale baseline freeze unauthorized. |
| Latest temporal-native readiness | Tier 4.31a passed `24/24`, scoping the first native v2.2 temporal migration to seven causal fixed-point EMA traces. Tier 4.31b passed `16/16` with fixed/float ratio `0.9987474666079806` and zero selected saturations. Tier 4.31c passed `17/17`, adding C-owned temporal state, command codes `39-42`, compact temporal readback length `48`, behavior-backed shams, profile ownership guards, and local C host tests. |
| Latest temporal hardware return | First Tier 4.31d EBRAINS return was incomplete: only `tier4_31d_test_profiles_stdout.txt` and `coral_reef (26).elf` came back, with no `tier4_31d_hw_results.json`. This is not hardware evidence; it only shows profile host tests passed and an ARM ELF linked before structured finalization. The incomplete return is preserved at [`controlled_test_output/tier4_31d_hw_20260506_incomplete_return`](controlled_test_output/tier4_31d_hw_20260506_incomplete_return). |
| Latest inter-chip contract | Tier 4.32c passed `19/19` from [`controlled_test_output/tier4_32c_20260507_interchip_feasibility_contract`](controlled_test_output/tier4_32c_20260507_interchip_feasibility_contract): defines required board/chip/core/role/partition/shard/seq identity fields, remote split-role MCPL lookup paths, compact readback ownership, failure classes, and the exact two-chip split-role single-shard smoke authorized for Tier 4.32d. True two-partition cross-chip learning remains blocked until origin/target shard semantics are defined. |
| Latest route/source audit | Tier 4.32d-r0 passed `10/10` from [`controlled_test_output/tier4_32d_r0_20260507_interchip_route_source_audit`](controlled_test_output/tier4_32d_r0_20260507_interchip_route_source_audit): it correctly blocked the first 4.32d upload because explicit inter-chip link routing was not yet source-proven. |
| Latest route repair | Tier 4.32d-r1 passed `14/14` from [`controlled_test_output/tier4_32d_r1_20260507_interchip_route_repair_local_qa`](controlled_test_output/tier4_32d_r1_20260507_interchip_route_repair_local_qa): learning-core builds can install outbound request link routes, state-core builds can install local request delivery plus outbound value/meta reply link routes, and existing MCPL lookup/four-core regressions still pass. |
| Latest two-chip hardware smoke | Tier 4.32d passed after EBRAINS ingest from [`controlled_test_output/tier4_32d_20260507_hardware_pass_ingested`](controlled_test_output/tier4_32d_20260507_hardware_pass_ingested): `7/7` ingest criteria, `96/96` lookup requests/replies, zero stale replies, zero duplicate replies, zero timeouts, and zero synthetic fallback. This is communication/readback evidence only, not learning-scale, speedup, benchmark, true two-partition, lifecycle scaling, or baseline-freeze evidence. |
| Latest 4.32e hardware learning micro-task | Tier 4.32e passed after EBRAINS ingest from [`controlled_test_output/tier4_32e_20260507_hardware_pass_ingested`](controlled_test_output/tier4_32e_20260507_hardware_pass_ingested): enabled-learning and no-learning cases separated exactly over the same two-chip MCPL lookup path. This is the first two-chip learning-bearing micro-task evidence, not speedup, benchmark, true two-partition, lifecycle-scaling, multi-shard, or native-scale-freeze evidence. |
| Latest multi-chip lifecycle/resource decision | Tier 4.32f passed locally from [`controlled_test_output/tier4_32f_20260507_multichip_resource_lifecycle_decision`](controlled_test_output/tier4_32f_20260507_multichip_resource_lifecycle_decision): `22/22` criteria, selected multi-chip lifecycle traffic with resource counters as the next direction, classified that lifecycle inter-chip route entries are not yet source-proven, authorized Tier 4.32g-r0 source/route repair audit next, and blocked immediate hardware packaging. |
| Latest lifecycle route repair audit | Tier 4.32g-r0 passed locally from [`controlled_test_output/tier4_32g_r0_20260507_lifecycle_route_source_audit`](controlled_test_output/tier4_32g_r0_20260507_lifecycle_route_source_audit): `14/14` criteria, source-proved lifecycle event request, trophic update, and active-mask/lineage sync MCPL routes for learning/lifecycle profiles, passed the new lifecycle inter-chip route C test plus existing lookup-route and lifecycle-split regressions, and authorized Tier 4.32g hardware package preparation. |
| Latest 4.32g hardware return | Tier 4.32g-r2 passed after EBRAINS ingest from [`controlled_test_output/tier4_32g_20260508_hardware_pass_ingested`](controlled_test_output/tier4_32g_20260508_hardware_pass_ingested): raw hardware status `pass`, ingest status `pass`, runner revision `tier4_32g_multichip_lifecycle_traffic_resource_smoke_20260508_0003`, board target `10.11.205.177`, source chip `(0,0)` learning core `p7`, remote chip `(1,0)` lifecycle core `p4`, source event/trophic requests `1/1`, source mask sync received `1`, lifecycle accepted trophic+death `2`, lifecycle mask sync sent `1`, active mask/count/death/trophic counters `1`, zero stale/duplicate/missing-ack counters, pause/reset controls passed, payloads `>=149`, `30` returned artifacts preserved, and zero synthetic fallback. Boundary: two-chip lifecycle traffic/resource smoke only; not lifecycle scaling, speedup, benchmark evidence, true partitioned ecology, multi-shard learning, or a native-scale baseline freeze. |
| Latest public benchmark promotion gate | Tier 7.0j passed from [`controlled_test_output/tier7_0j_20260508_generic_recurrent_promotion_gate`](controlled_test_output/tier7_0j_20260508_generic_recurrent_promotion_gate): generic bounded recurrent state improved the locked 8000-step public aggregate geomean MSE versus v2.2 (`0.09530752189727928` vs `0.19348969000027122`), beat lag-only and random-reservoir online controls, narrowed the ESN gap, preserved the Tier 7.0i topology nonclaim, and passed full NEST compact regression. `CRA_EVIDENCE_BASELINE_v2.3` is frozen under [`baselines/`](baselines). |
| Latest targeted usefulness diagnostic | Tier 6.2a passed from [`controlled_test_output/tier6_2a_20260508_targeted_usefulness_validation`](controlled_test_output/tier6_2a_20260508_targeted_usefulness_validation): v2.3 was best only on `variable_delay_multi_cue`, v2.2 won the aggregate hard-task geomean (`0.15892013746238234` vs v2.3 `0.17604715537423876`), and no baseline freeze or hardware transfer was authorized. |
| Latest real-ish/public adapter contract | Tier 7.1a passed from [`controlled_test_output/tier7_1a_20260508_realish_adapter_contract`](controlled_test_output/tier7_1a_20260508_realish_adapter_contract): selected NASA C-MAPSS RUL streaming as the first public adapter family, with source audit, preprocessing/split/baseline/leakage contract, and no dataset score or usefulness claim yet. |
| Latest public data preflight | Tier 7.1b passed from [`controlled_test_output/tier7_1b_20260508_cmapss_source_data_preflight`](controlled_test_output/tier7_1b_20260508_cmapss_source_data_preflight): verified official NASA C-MAPSS source access, ZIP checksum, FD001 schema/row counts, train-only normalization, prediction-before-update stream rows, label-separated smoke artifacts, and ignored local raw-data cache. No scoring or usefulness claim yet. |
| Latest public scoring gate | Tier 7.1c passed from [`controlled_test_output/tier7_1c_20260508_cmapss_fd001_scoring_gate`](controlled_test_output/tier7_1c_20260508_cmapss_fd001_scoring_gate): compact FD001 scalar-adapter scoring completed with no test-label updates. Outcome `v2_3_no_public_adapter_advantage`; best model was monotone age-to-RUL ridge RMSE `46.10944999532139`; v2.3 ranked `5` with RMSE `49.4908802462679` and did not beat v2.2. No freeze or hardware transfer. |
| Latest public adapter failure analysis | Tier 7.1d passed from [`controlled_test_output/tier7_1d_20260508_cmapss_failure_analysis_adapter_repair`](controlled_test_output/tier7_1d_20260508_cmapss_failure_analysis_adapter_repair): localized the 7.1c gap mostly to target/readout policy. Capped-RUL plus ridge repaired scalar scoring; best promotable result was v2.2 ridge capped RMSE `20.271418942340336`, narrowly ahead of lag-multichannel ridge RMSE `20.305268771358435`. v2.3 still did not win. No freeze or hardware transfer. |
| Latest public adapter fairness confirmation | Tier 7.1e passed from [`controlled_test_output/tier7_1e_20260508_cmapss_capped_readout_fairness_confirmation`](controlled_test_output/tier7_1e_20260508_cmapss_capped_readout_fairness_confirmation): the tiny v2.2 capped-ridge C-MAPSS signal was not statistically confirmed against lag-multichannel ridge. Primary per-unit mean delta was `-0.3690103080637045` RMSE with bootstrap 95% CI `[-1.4191012103865384, 0.6704668696286052]`; no freeze or hardware transfer. |
| Latest next-adapter contract | Tier 7.1f passed from [`controlled_test_output/tier7_1f_20260508_next_public_adapter_contract`](controlled_test_output/tier7_1f_20260508_next_public_adapter_contract): selected Numenta NAB streaming anomaly detection as the next public adapter family after C-MAPSS non-promotion, with official sources, leakage rules, baselines, metrics, pass/fail criteria, and nonclaims. No data preflight or scoring yet. |
| Latest NAB source/data preflight | Tier 7.1g passed from [`controlled_test_output/tier7_1g_20260508_nab_source_data_scoring_preflight`](controlled_test_output/tier7_1g_20260508_nab_source_data_scoring_preflight): pinned official NAB commit `ea702d75cc2258d9d7dd35ca8e5e2539d71f3140`, cached source/data/label/scoring files under ignored `.cra_data_cache/`, parsed 5 selected streams and `12` anomaly windows, produced `400` label-separated chronological smoke rows, and documented the scoring-interface contract. No NAB scoring, usefulness claim, freeze, or hardware transfer. |
| Latest NAB compact scoring gate | Tier 7.1h passed from [`controlled_test_output/tier7_1h_20260508_compact_nab_scoring_gate`](controlled_test_output/tier7_1h_20260508_compact_nab_scoring_gate): v2.3 ranked `2` behind `fixed_random_reservoir_online_residual`, beat v2.2 (`0.22649365525011686` vs `0.19995024953915835` primary score), separated all three v2.3 shams, but did not beat the best external baseline and bootstrap CI crossed zero. Outcome: `v2_3_partial_nab_signal_requires_confirmation`; no usefulness claim, freeze, or hardware transfer. |
| Latest NAB broader confirmation | Tier 7.1i passed from [`controlled_test_output/tier7_1i_20260508_nab_fairness_confirmation`](controlled_test_output/tier7_1i_20260508_nab_fairness_confirmation): broadened NAB to `20` streams across `6` categories. Outcome `v2_3_nab_signal_localized_not_confirmed`; best model was `rolling_zscore_detector` primary score `0.140951459207744`; v2.3 ranked `4` with score `0.09880252815842962`, beat v2.2 and separated all three shams, but did not beat best external baseline. No usefulness claim, freeze, or hardware transfer. |
| Latest NAB failure localization | Tier 7.1j passed from [`controlled_test_output/tier7_1j_20260508_nab_failure_localization`](controlled_test_output/tier7_1j_20260508_nab_failure_localization): failure class `threshold_or_fp_penalty_sensitive`. v2.3 beat rolling z-score in `5/15` policy cells and won `3/15` policy cells, with better event-F1/window recall but worse NAB-style/false-positive pressure. No mechanism promotion, usefulness claim, freeze, or hardware transfer. |
| Latest NAB false-positive repair | Tier 7.1k passed from [`controlled_test_output/tier7_1k_20260508_nab_false_positive_repair`](controlled_test_output/tier7_1k_20260508_nab_false_positive_repair): same-subset repair candidate `persist3` made v2.3 rank `1` with primary score `0.44632600314828624`, reduced FP/1000 from `16.537437704270094` to `2.5685172711420603`, beat rolling z-score and v2.2 under that policy, and separated all three shams. Boundary: policy selected on the same broad diagnostic subset and window recall dropped versus raw v2.3, so no usefulness claim, freeze, or hardware transfer. |
| Latest NAB holdout confirmation | Tier 7.1l passed as a harness from [`controlled_test_output/tier7_1l_20260508_nab_locked_policy_holdout_confirmation`](controlled_test_output/tier7_1l_20260508_nab_locked_policy_holdout_confirmation), but the locked `persist3` policy did **not** confirm public usefulness on held-out NAB streams: v2.3 ranked `5`, scored `0.11180074060709926`, did not beat rolling z-score (`0.13854698668870535`) or v2.2, and separated only `2/3` shams. It reduced FP/1000 versus raw v2.3 but lost substantial window recall. No freeze or hardware transfer. |
| Latest NAB closeout | Tier 7.1m passed from [`controlled_test_output/tier7_1m_20260508_nab_closeout_mechanism_return_decision`](controlled_test_output/tier7_1m_20260508_nab_closeout_mechanism_return_decision): the NAB chain is narrowed to partial/local signal only, adapter-policy tuning is stopped, no public usefulness claim/freeze/hardware transfer is authorized, and the selected next gate is Tier 7.4a cost-aware policy/action selection. |
| Latest policy/action contract | Tier 7.4a passed from [`controlled_test_output/tier7_4a_20260509_cost_aware_policy_action_contract`](controlled_test_output/tier7_4a_20260509_cost_aware_policy_action_contract): predeclared the general cost-aware policy/action gate with asymmetric costs, abstain/act/wait actions, delayed consequences, fair baselines, shams, ablations, metrics, pass/fail criteria, and compact-regression requirements. Contract only; no scoring, promotion, freeze, or hardware transfer. |
| Latest policy/action diagnostic | Tier 7.4b passed from [`controlled_test_output/tier7_4b_20260509_cost_aware_policy_action_local_diagnostic`](controlled_test_output/tier7_4b_20260509_cost_aware_policy_action_local_diagnostic): the local v2.3 cost-aware policy ranked first among non-oracle models, beat fixed/trivial/online baselines by expected utility, separated shams and ablations, avoided no-action collapse, and preserved the boundary that this is candidate evidence only. |
| Latest policy/action promotion gate | Tier 7.4c passed from [`controlled_test_output/tier7_4c_20260509_cost_aware_policy_action_promotion_gate`](controlled_test_output/tier7_4c_20260509_cost_aware_policy_action_promotion_gate): the locked 7.4b candidate preserved its expected-utility advantage, sham/ablation separation, no-action guard, and leakage boundary, then passed full NEST compact regression. `CRA_EVIDENCE_BASELINE_v2.4` is frozen under [`baselines/`](baselines). Boundary: host-side software policy/action evidence only; not public usefulness proof and not hardware/native transfer. |
| Latest policy/action held-out contract | Tier 7.4d passed from [`controlled_test_output/tier7_4d_20260509_cost_aware_policy_action_heldout_contract`](controlled_test_output/tier7_4d_20260509_cost_aware_policy_action_heldout_contract): locked the held-out/public action-cost scoring contract for v2.4 before any scoring, including NAB alarm actions, C-MAPSS maintenance actions, standardized dynamical action-cost diagnostics, fixed costs, splits, leakage rules, baselines, shams, statistics, and artifacts. Contract only; no public usefulness claim, freeze, or hardware transfer. |
| Latest policy/action scoring preflight | Tier 7.4e passed from [`controlled_test_output/tier7_4e_20260509_cost_aware_policy_action_heldout_preflight`](controlled_test_output/tier7_4e_20260509_cost_aware_policy_action_heldout_preflight): verified NAB and C-MAPSS source/preflight artifacts, disjoint held-out splits, fixed costs, online/offline label separation, baseline and sham inventories, and scoring schemas before any v2.4 performance score. Preflight only; no public usefulness claim, freeze, or hardware transfer. |
| Latest policy/action held-out scoring gate | Tier 7.4f passed from [`controlled_test_output/tier7_4f_20260509_cost_aware_policy_action_heldout_scoring_gate`](controlled_test_output/tier7_4f_20260509_cost_aware_policy_action_heldout_scoring_gate): outcome `v2_4_heldout_public_action_usefulness_qualified_cmapss_only`. v2.4 ranked first on C-MAPSS maintenance utility and beat the strongest external baseline, but NAB did not confirm and C-MAPSS did not separate from v2.2 with a positive paired CI. Qualified public-action signal only; no broad usefulness claim, no incremental v2.4 superiority claim, no freeze, and no hardware transfer. |
| Latest policy/action confirmation gate | Tier 7.4g passed from [`controlled_test_output/tier7_4g_20260509_policy_action_confirmation_reference_separation`](controlled_test_output/tier7_4g_20260509_policy_action_confirmation_reference_separation): outcome `cmapss_external_signal_confirmed_reference_not_separated_nab_failed`. The narrow C-MAPSS external/sham action-cost signal was confirmed (`CI low` vs best external `56.89735573832698`, vs sham `373.38894337405304`), but v2.4 still did not separate from v2.2 (`CI low` `-12.387676684452819`) and NAB remained an event-coverage non-confirmation. No broad usefulness claim, no incremental v2.4 superiority claim, no freeze, and no hardware transfer. |
| Latest policy/action closeout | Tier 7.4h passed from [`controlled_test_output/tier7_4h_20260509_policy_action_attribution_closeout`](controlled_test_output/tier7_4h_20260509_policy_action_attribution_closeout): outcome `policy_action_track_closed_narrow_cmapss_signal_return_to_mechanism_benchmark_loop`. The closeout preserves only the narrow C-MAPSS action-cost signal, blocks broad public usefulness and incremental v2.4-over-v2.2 claims, blocks freeze/hardware transfer, and routes the project to Tier 7.5a curriculum/environment contract. |
| Latest curriculum contract | Tier 7.5a passed from [`controlled_test_output/tier7_5a_20260509_curriculum_environment_contract`](controlled_test_output/tier7_5a_20260509_curriculum_environment_contract): outcome `curriculum_environment_contract_locked_no_scoring`. The contract predeclares generated task families, difficulty schedule, hidden holdout splits, baselines, leakage guards, metrics, pass/fail gates, and expected artifacts before implementation/scoring. Contract only; no usefulness claim, freeze, or hardware transfer. |
| Latest curriculum preflight | Tier 7.5b passed from [`controlled_test_output/tier7_5b_20260509_curriculum_environment_preflight`](controlled_test_output/tier7_5b_20260509_curriculum_environment_preflight): outcome `curriculum_generator_preflight_materialized_no_scoring`. Deterministic generated streams, split manifests, hidden-label hashes, schema contracts, baseline compatibility rows, and leakage checks are materialized without scoring CRA or exposing hidden holdout labels. Preflight only; no usefulness claim, freeze, or hardware transfer. |
| Latest curriculum scoring gate | Tier 7.5c passed from [`controlled_test_output/tier7_5c_20260509_curriculum_environment_scoring_gate`](controlled_test_output/tier7_5c_20260509_curriculum_environment_scoring_gate): outcome `generated_family_signal_confirmed_requires_attribution_gate`. Current CRA v2.4 confirmed generated-family software signal on `6/6` locked synthetic families against external baselines, v2.2 reference, and shams/ablations. Boundary: generated synthetic diagnostic only; no public usefulness claim, no freeze, and no hardware/native transfer. |
| Latest curriculum attribution closeout | Tier 7.5d passed from [`controlled_test_output/tier7_5d_20260509_curriculum_environment_attribution_closeout`](controlled_test_output/tier7_5d_20260509_curriculum_environment_attribution_closeout): outcome `synthetic_mechanism_attribution_supported_no_freeze`. Synthetic keyed/compositional mechanism attribution is supported on `6/6` generated families, but near-oracle generator-feature alignment risk is high on `6/6`; no public usefulness claim, no freeze, and no hardware/native transfer. |
| Latest planning contract | Tier 7.6a passed from [`controlled_test_output/tier7_6a_20260509_long_horizon_planning_contract`](controlled_test_output/tier7_6a_20260509_long_horizon_planning_contract): outcome `long_horizon_planning_contract_locked_no_scoring`. It predeclares `5` planning task families, `9` baselines, `9` shams, leakage guards, metrics, pass/fail gates, nonclaims, and expected artifacts before any planning implementation/scoring. |
| Latest planning local diagnostic | Tier 7.6b passed from [`controlled_test_output/tier7_6b_20260509_long_horizon_planning_local_diagnostic`](controlled_test_output/tier7_6b_20260509_long_horizon_planning_local_diagnostic): outcome `subgoal_control_local_diagnostic_candidate_supported_requires_attribution`. The local subgoal-control scaffold beats the strongest non-oracle baseline aggregate with positive paired support, beats v2.4 reactive references on at least three families, and separates destructive shams. Boundary: local scaffold only; no broad planning claim, no freeze, and no hardware/native transfer. |
| Latest planning attribution closeout | Tier 7.6c passed from [`controlled_test_output/tier7_6c_20260509_long_horizon_planning_attribution_closeout`](controlled_test_output/tier7_6c_20260509_long_horizon_planning_attribution_closeout): outcome `planning_scaffold_signal_preserved_no_promotion`. It preserves the 7.6b signal as diagnostic evidence, but blocks promotion/freeze/hardware transfer because feature-alignment risk is high, strict all-family support is not met, and reduced-feature generalization has not run. |
| Latest planning reduced-feature repair | Tier 7.6d passed from [`controlled_test_output/tier7_6d_20260509_reduced_feature_planning_generalization`](controlled_test_output/tier7_6d_20260509_reduced_feature_planning_generalization): outcome `reduced_feature_planning_signal_supported_requires_promotion_gate`. With direct raw keys hidden and aliased/coarse features only, the candidate preserved aggregate support, repaired both prior weak families, and supported `4/5` families. No freeze or hardware transfer. |
| Latest planning promotion gate | Tier 7.6e passed from [`controlled_test_output/tier7_6e_20260509_planning_promotion_compact_regression`](controlled_test_output/tier7_6e_20260509_planning_promotion_compact_regression): outcome `reduced_feature_planning_ready_for_v2_5_freeze`; `20/20` criteria passed, full NEST compact regression passed, `CRA_EVIDENCE_BASELINE_v2.5` is frozen, and hardware/native transfer plus broad planning claims remain blocked. |
| Latest standardized benchmark contract | Tier 7.7a passed from [`controlled_test_output/tier7_7a_20260509_v2_5_standardized_scoreboard_contract`](controlled_test_output/tier7_7a_20260509_v2_5_standardized_scoreboard_contract): outcome `v2_5_standardized_scoreboard_contract_locked`; `20/20` criteria passed. The primary scoreboard is locked as Mackey-Glass, Lorenz, and NARMA10 at 8000 steps, horizon 8, seeds 42/43/44, chronological 65/35 split. C-MAPSS FD001 and NAB are secondary public/real-ish confirmation tracks only. The 7.7a contract itself performs no scoring and authorizes no public usefulness claim, freeze, or hardware/native transfer. |
| Latest standardized benchmark score | Tier 7.7b passed from [`controlled_test_output/tier7_7b_20260509_v2_5_standardized_scoreboard_scoring_gate`](controlled_test_output/tier7_7b_20260509_v2_5_standardized_scoreboard_scoring_gate): outcome `standardized_progress_pass`; `15/15` criteria passed. v2.5 improved the locked 8000-step standardized aggregate versus v2.3 (`0.0735414741` vs `0.0951071342` geomean MSE; ratio `1.2932448715`; paired delta CI `0.0197948122` to `0.0244083440`), but the gain was driven by Mackey-Glass only and ESN/online-linear/ridge baselines still beat v2.5 on aggregate. No freeze, broad usefulness claim, or hardware/native transfer. |
| Latest long-run failure contract | Tier 7.7c passed from [`controlled_test_output/tier7_7c_20260509_standardized_long_run_failure_contract`](controlled_test_output/tier7_7c_20260509_standardized_long_run_failure_contract): outcome `standardized_long_run_failure_contract_locked`; `15/15` criteria passed. It locks Mackey-Glass/Lorenz/NARMA10 at required lengths `8000`, `16000`, and `32000` with optional `50000`, seeds 42/43/44, explicit shams, and failure classes before the next scoring run. Contract only: no score, freeze, usefulness claim, or hardware/native transfer. |
| Latest long-run scoring blocker | Tier 7.7d passed as a blocker-classification harness from [`controlled_test_output/tier7_7d_20260509_standardized_long_run_failure_scoring_gate`](controlled_test_output/tier7_7d_20260509_standardized_long_run_failure_scoring_gate): outcome `benchmark_stream_invalid`; `12/12` criteria passed. Mackey-Glass persisted, Lorenz stayed weak, external baselines remained blockers, and NARMA10 became non-finite at `16000` and `32000`, so no complete long-run scoreboard can be cited until the benchmark stream is repaired/preflighted. |
| Latest finite-stream repair | Tier 7.7e passed from [`controlled_test_output/tier7_7e_20260509_finite_stream_repair_preflight`](controlled_test_output/tier7_7e_20260509_finite_stream_repair_preflight): outcome `finite_stream_repair_preflight_passed`; `16/16` criteria passed. The original `narma10_standard_u05` generator reproduced `2/9` non-finite required cells, while selected `narma10_reduced_input_u02` passed `9/9` required cells at `8000`, `16000`, and `32000` across seeds 42/43/44. Preflight only: no CRA score, no freeze, no usefulness claim, and no hardware/native transfer. |
| Latest repaired long-run scoreboard | Tier 7.7f passed from [`controlled_test_output/tier7_7f_20260509_repaired_finite_stream_long_run_scoreboard`](controlled_test_output/tier7_7f_20260509_repaired_finite_stream_long_run_scoreboard): outcome `mackey_only_localized`; `16/16` criteria passed. Mackey-Glass persisted (`2.17x`-`2.20x` v2.3/v2.5), repaired NARMA stayed near-flat (`~1.00x`), Lorenz stayed flat/weak, and ESN remained the best external baseline at all required lengths. No freeze, broad usefulness claim, external-baseline superiority, or hardware/native transfer. |
| Latest capacity diagnostic contract | Tier 7.7g passed from [`controlled_test_output/tier7_7g_20260509_lorenz_capacity_narma_memory_contract`](controlled_test_output/tier7_7g_20260509_lorenz_capacity_narma_memory_contract): outcome `lorenz_capacity_narma_memory_contract_locked`; `15/15` criteria passed. It locks CRA temporal-state capacity `16/32/64/128`, matched-capacity ESN and random-reservoir references, repaired NARMA `U(0,0.2)`, Mackey positive-control anchor, shams, metrics, and decision classes before scoring. Contract only: no score, mechanism promotion, freeze, usefulness claim, or hardware/native transfer. |
| Latest capacity scoring gate | Tier 7.7h passed from [`controlled_test_output/tier7_7h_20260509_lorenz_capacity_narma_memory_scoring_gate`](controlled_test_output/tier7_7h_20260509_lorenz_capacity_narma_memory_scoring_gate): outcome `overfit_or_sham_blocked`; `19/19` criteria passed. Capacity materially improved Mackey-Glass (`1.92x` best-capacity gain) and Lorenz (`2.18x`), but Lorenz was blocked because the best-capacity permuted-recurrence sham beat the candidate; repaired NARMA improved only weakly (`1.08x`). No freeze, mechanism promotion, broad usefulness claim, external-baseline superiority, or hardware/native transfer. |
| Latest state-specificity contract | Tier 7.7i passed from [`controlled_test_output/tier7_7i_20260509_capacity_sham_separation_contract`](controlled_test_output/tier7_7i_20260509_capacity_sham_separation_contract): outcome `capacity_sham_separation_contract_locked`; `19/19` criteria passed. It predeclares candidate-vs-permuted/orthogonal/block/state-reset probes plus participation ratio, rank-95, top-PC dominance, state-kernel alignment, readout concentration, observability, and negative outcome classes before any repair or tuning. Contract only: no score, freeze, mechanism promotion, usefulness claim, or hardware/native transfer. |
| Latest state-specificity scoring gate | Tier 7.7j passed from [`controlled_test_output/tier7_7j_20260509_capacity_sham_separation_scoring_gate`](controlled_test_output/tier7_7j_20260509_capacity_sham_separation_scoring_gate): outcome `low_rank_collapse_confirmed`; `15/15` criteria passed. The Lorenz candidate at 128 units had geomean MSE `0.0065086836`, the best generic family was permuted recurrence at `0.0060562668`, target/time shuffles separated strongly, candidate PR stayed low (`2.1911` at 128), max probe PR stayed low (`2.2214`), and readout concentration did not explain the gap. Diagnostic only: no repair, freeze, mechanism promotion, usefulness claim, external-baseline superiority, or hardware/native transfer. |
| Latest state-dimensionality repair contract | Tier 7.7k passed from [`controlled_test_output/tier7_7k_20260509_effective_state_dimensionality_repair_contract`](controlled_test_output/tier7_7k_20260509_effective_state_dimensionality_repair_contract): `18/18` criteria passed. It locks `partitioned_driver_diverse_recurrent_state` as the next candidate repair, names shared-driver synchronization and input-state bottleneck as primary suspects, and requires Lorenz PR/rank improvement, sham separation, shuffle guards, Mackey/NARMA regression guards, and compact regression before any promotion. Contract only: no implementation, score, freeze, usefulness claim, external-baseline superiority, or hardware/native transfer. |
| Latest state-dimensionality repair score | Tier 7.7l passed from [`controlled_test_output/tier7_7l_20260509_effective_state_dimensionality_repair_scoring_gate`](controlled_test_output/tier7_7l_20260509_effective_state_dimensionality_repair_scoring_gate): outcome `task_gain_without_dimension`; `15/15` criteria passed. The partitioned-driver candidate improved Lorenz 128-unit geomean MSE versus the prior/single-pool reference (`0.0034485307` vs `0.0065086836`) and improved Mackey/NARMA versus single-pool, with strong target/time-shuffle separation. However PR rose only to `2.6645`, diversity-disabled was too close (`1.0165x` margin), and the predeclared dimensionality/attribution gate did not pass. Diagnostic only: no mechanism promotion, freeze, usefulness claim, external-baseline superiority, or hardware/native transfer. |
| Latest partitioned-driver attribution contract | Tier 7.7m passed from [`controlled_test_output/tier7_7m_20260509_partitioned_driver_attribution_contract`](controlled_test_output/tier7_7m_20260509_partitioned_driver_attribution_contract): `22/22` criteria passed. It locks the next attribution gate to distinguish causal driver partitioning from nonlinear/lag feature enrichment, readout/interface budget, diversity pressure, generic basis effects, leakage, or non-reproducible scoring noise. Contract only: no attribution implementation, model score, promotion, freeze, usefulness claim, external-baseline superiority, or hardware/native transfer. |
| Latest partitioned-driver attribution score | Tier 7.7n passed from [`controlled_test_output/tier7_7n_20260509_partitioned_driver_attribution_scoring_gate`](controlled_test_output/tier7_7n_20260509_partitioned_driver_attribution_scoring_gate): outcome `generic_projection_explains_gain`; `15/15` criteria passed. The full partitioned driver stayed useful versus single-pool on Lorenz (`0.0034485307` vs `0.0065086836`), but same-feature random projection (`0.0016704454`) and nonlinear/lag unpartitioned control (`0.0019527710`) exceeded it, so the 7.7l gain is not attributable to a CRA-specific partitioned-driver mechanism. Diagnostic only: no promotion, freeze, usefulness claim, external-baseline superiority, or hardware/native transfer. |
| Latest generic temporal-interface reframing contract | Tier 7.7o passed from [`controlled_test_output/tier7_7o_20260509_generic_temporal_interface_reframing_contract`](controlled_test_output/tier7_7o_20260509_generic_temporal_interface_reframing_contract): `14/14` criteria passed. It parks the partitioned-driver repair, makes random-projection/nonlinear-lag controls mandatory, and authorizes a separate CRA-native temporal-interface internalization contract. Contract only: no mechanism implementation, model score, promotion, freeze, usefulness claim, external-baseline superiority, or hardware/native transfer. |
| Latest CRA-native temporal-interface score | Tier 7.7q passed from [`controlled_test_output/tier7_7q_20260509_cra_native_temporal_interface_internalization_scoring_gate`](controlled_test_output/tier7_7q_20260509_cra_native_temporal_interface_internalization_scoring_gate): outcome `external_controls_still_win`; `14/14` criteria passed. The native sparse temporal expansion candidate improved over current CRA on Lorenz (`2.88x`), Mackey-Glass, and NARMA10 with clean shuffle guards, but same-feature random projection (`0.0016704454`) and nonlinear-lag (`0.0019527710`) still beat the native Lorenz score (`0.0022567719`). No mechanism promotion, freeze, usefulness claim, external-baseline superiority, or hardware/native transfer. |
| Latest temporal-basis reframing contract | Tier 7.7r passed from [`controlled_test_output/tier7_7r_20260509_native_temporal_basis_reframing_contract`](controlled_test_output/tier7_7r_20260509_native_temporal_basis_reframing_contract): `15/15` criteria passed. It preserves the 7.7q positive utility signal while splitting bounded engineering/interface promotion from stricter CRA-specific mechanism promotion. Contract only: no new score, mechanism promotion, freeze, usefulness claim, external-baseline superiority, or hardware/native transfer. |
| Latest temporal-basis utility promotion | Tier 7.7s passed from [`controlled_test_output/tier7_7s_20260509_bounded_temporal_basis_utility_promotion`](controlled_test_output/tier7_7s_20260509_bounded_temporal_basis_utility_promotion): outcome `utility_promoted_mechanism_not_promoted`; `13/13` criteria passed. The temporal-basis interface is carried forward as bounded engineering utility after repo pytest regression passed; it is not a CRA-specific mechanism, core baseline freeze, usefulness claim, external-baseline superiority, or hardware/native transfer. |
| Latest low-rank repair campaign contract | Tier 7.7t passed from [`controlled_test_output/tier7_7t_20260509_low_rank_state_repair_campaign_contract`](controlled_test_output/tier7_7t_20260509_low_rank_state_repair_campaign_contract): outcome `campaign_contract_locked`; `23/23` criteria passed. Eight failure modes, five repair families (A-E), mandatory random-projection and nonlinear-lag controls, state-geometry and task metrics, thirteen outcome classes, five-stage baseline escalation, three stopping rules, and four route conditions to Tier 7.8/7.9 are locked before Tier 7.7u causal localization. Contract only: no repair implementation, no scoring, no mechanism promotion, no baseline freeze, and no hardware/native transfer. |
| Latest causal localization gate | Tier 7.7u passed from [`controlled_test_output/tier7_7u_20260509_state_collapse_causal_localization`](controlled_test_output/tier7_7u_20260509_state_collapse_causal_localization): outcome `localization_protocol_locked_awaits_model_variants`; `13/13` criteria passed. Ten probe definitions, seven required diagnostic model variants (no_plasticity, no_inhibition, frozen_recurrent, state_reset, input_channel_shuffle, per_partition_probe, trophic_probe), seven diagnostic controls, and nine outcome classification rules are locked. Probe infrastructure is importable. Full causal scoring awaits CRA config-layer model-variant implementation. Not full localization scoring, not repair, not mechanism promotion, not a baseline freeze. |
| Latest optional mechanism diagnostic | Tier 5.20a passed as a harness from [`controlled_test_output/tier5_20a_20260508_resonant_branch_polyp_diagnostic`](controlled_test_output/tier5_20a_20260508_resonant_branch_polyp_diagnostic), but the full 16-resonant-branch polyp proxy was **not promoted**: it helped `variable_delay_multi_cue` and slightly helped `anomaly_detection_stream`, but regressed the standard three and hidden-context task versus v2.3. |
| Latest optional mechanism repair | Tier 5.20b passed as a harness from [`controlled_test_output/tier5_20b_20260508_hybrid_resonant_polyp_diagnostic`](controlled_test_output/tier5_20b_20260508_hybrid_resonant_polyp_diagnostic), but neither 8 LIF / 8 resonant nor 12 LIF / 4 resonant earned promotion. Best candidate was `hybrid_8_lif_8_resonant`, with all-task geomean MSE `0.2852846857844163` versus v2.3 `0.2610804850928049`, two wins, two material regressions, and only one sham-separated task. No core polyp replacement, freeze, or hardware transfer. |
| Latest minimal-dose mechanism check | Tier 5.20c passed as a harness from [`controlled_test_output/tier5_20c_20260508_minimal_resonant_polyp_diagnostic`](controlled_test_output/tier5_20c_20260508_minimal_resonant_polyp_diagnostic), but 14 LIF / 2 resonant was **not promoted**: all-task geomean MSE `0.2777975100580056` versus v2.3 `0.2610804850928049`, zero task wins, one material regression, and zero sham-separated tasks. |
| Latest resonant-heavy mechanism check | Tier 5.20d passed as a harness from [`controlled_test_output/tier5_20d_20260508_resonant_heavy_polyp_diagnostic`](controlled_test_output/tier5_20d_20260508_resonant_heavy_polyp_diagnostic), but 4 LIF / 12 resonant was **not promoted**: all-task geomean MSE `0.29289224348599796` versus v2.3 `0.2610804850928049`, three task wins, two material regressions, and two sham-separated tasks. The signal is real enough to record, but not safe enough to integrate. |
| Latest near-full resonant check | Tier 5.20e passed as a harness from [`controlled_test_output/tier5_20e_20260508_near_full_resonant_polyp_diagnostic`](controlled_test_output/tier5_20e_20260508_near_full_resonant_polyp_diagnostic), but 2 LIF / 14 resonant was **not promoted**: all-task geomean MSE `0.30374770797663714` versus v2.3 `0.2610804850928049`, three task wins, three material regressions, and two sham-separated tasks. This closes the current resonant branch dose sweep; resonant branches remain parked. |
| Active next gate | Continue full Tier 5.45a healthy-NEST rebaseline scoring with the resumable shard workflow (`make tier5-45a-shard-status`, `make tier5-45a-shard-plan`, `make tier5-45a-shard-run-next`, then `make tier5-45a-shard-merge`) or equivalent sharded runs merged with `--merge-input-dirs`: compare `v2.6`, conservative organism defaults, each of the 15 opt-in organism mechanisms, the full stack, and external baselines under zero-fallback NEST. Current progress is `15/204` canonical cells complete; `make tier5-45a-smoke` is runner validation only and is not canonical evidence. |
| Canonical registry | 157 evidence bundles, 0 missing expected artifacts, 0 failed criteria. |
| Validation suite | 158 pytest tests plus registry, paper-table, and repository-audit generation. |

## What CRA Implements

CRA models a population of small spiking agents called polyps. The biological
terminology is used as an engineering abstraction, not as a claim of biological
realism.

Planned capabilities are not intended to make every polyp into a large
all-purpose model. Polyps remain small specialists; larger capabilities are
tested as distributed substrate mechanisms across population state, routing,
memory, lifecycle machinery, readout interfaces, and the custom runtime.

Core implementation areas:

- Leaky integrate-and-fire neural substrate with NEST, Brian2, mock, and
  SpiNNaker-oriented backends.
- Dopamine-modulated local plasticity and delayed consequence handling.
- Trophic energy accounting, lifecycle pressure, lineage tracking, and
  population-level selection.
- Domain-neutral task adapters plus historical finance/trading adapters.
- A custom SpiNNaker C runtime for native state, routing, memory, learning, and
  mechanism-transfer experiments.
- A tiered experiment suite with canonical and noncanonical evidence tracking.

## Evidence Highlights

| Tier | Evidence | Boundary |
| --- | --- | --- |
| 1-3 | Negative controls, positive learning controls, and architecture ablations. | Software controls; not hardware evidence. |
| 4.13-4.18a | PyNN/SpiNNaker hardware capsule, repeatability, harder-task transfer, and chunked-runtime characterization. | Real hardware evidence for bounded capsules; not full hardware scaling. |
| 5.1-5.7 | External baselines, learning curves, failure analysis, delayed-credit confirmation, fairness audit, compact regression. | Software evidence; not universal superiority. |
| 5.10-5.18 | Memory, replay/consolidation, predictive context, composition/routing, working memory diagnostics, temporal coding, neuron-parameter sensitivity, predictive binding, and self-evaluation gates. | Mostly host-side software mechanisms unless explicitly migrated to hardware. |
| 6.1-6.4 | Lifecycle/self-scaling, lifecycle sham controls, and circuit-motif causality. | Software organism/ecology evidence; not hardware lifecycle. |
| 4.22-4.30g | Custom SpiNNaker runtime progression from roundtrip/load tests to four-core MCPL tasks, keyed memory, routing/composition, predictive binding, confidence-gated learning, host-scheduled replay/consolidation, lifecycle static-pool metadata, multi-core lifecycle source/runtime gates, five-profile lifecycle hardware smoke, lifecycle sham-control hardware subset, and lifecycle task-benefit/resource bridge hardware pass. | Native hardware mechanism evidence for tested capsules only. Tier 4.30g-hw proves a bounded host-ferried lifecycle-to-task bridge with resource accounting; it does not prove autonomous lifecycle-to-learning MCPL, speedup, multi-chip scaling, v2.2 temporal migration, or full organism autonomy. |
| 4.31a-4.32h | Native temporal-substrate migration, MCPL scaling path, replicated single-chip stress, two-chip communication, two-chip learning micro-task, two-chip lifecycle traffic/resource smoke, and native-scale evidence closeout. | Freezes `CRA_NATIVE_SCALE_BASELINE_v0.5` as a bounded native-scale substrate baseline. Not speedup, benchmark superiority, real-task usefulness, true two-partition learning, lifecycle scaling, multi-shard learning, or AGI/ASI evidence. |
| 7.0-7.0d | Standard dynamical benchmarks and failure analysis: Mackey-Glass, Lorenz, NARMA10, aggregate geometric-mean MSE, CRA state/readout probes, bounded online readout repair, and state-specific claim narrowing. | Software diagnostics only; CRA v2.1 underperformed simple continuous-regression sequence baselines. 7.0d showed lag regression explains this benchmark path under the prior interface, so no direct benchmark-superiority claim was made. |
| 5.19a-5.19c | Continuous temporal-dynamics repair path: local temporal substrate reference, recurrence sham gate, then narrowed fading-memory compact-regression promotion. | v2.2 supports bounded host-side fading-memory temporal state. It does not prove nonlinear recurrence, hardware/on-chip temporal dynamics, universal benchmark superiority, language, planning, AGI, or ASI. |

The most current paper-facing evidence index is generated at
[`STUDY_EVIDENCE_INDEX.md`](STUDY_EVIDENCE_INDEX.md). The machine-readable
registry is [`controlled_test_output/STUDY_REGISTRY.json`](controlled_test_output/STUDY_REGISTRY.json).

## Claim Boundary

Current evidence supports this bounded claim:

> CRA is a controlled neuromorphic research platform that demonstrates local
> learning, delayed credit, mechanism sensitivity, backend portability, selected
> software capability upgrades, and repeatable SpiNNaker hardware execution for
> bounded task capsules and native-runtime mechanism bridges.

Current evidence does not prove:

- General intelligence or broad autonomous reasoning.
- Universal superiority over external baselines.
- Competitive performance on the Tier 7.0 continuous-valued standard dynamical
  benchmark suite; Tier 5.19c promotes a bounded fading-memory substrate but
  standard-three lag-only remains stronger under the tested metrics.
- Full organism lifecycle running natively on hardware.
- Broad multi-chip learning/lifecycle scaling beyond the bounded v0.5 substrate smokes.
- Production readiness.
- Native on-chip replay buffers, dynamic population creation, native policy/action transfer, curriculum generation, long-horizon planning, or fully autonomous on-chip learning for all promoted software mechanisms.

## Repository Layout

| Path | Purpose |
| --- | --- |
| [`coral_reef_spinnaker/`](coral_reef_spinnaker) | Main Python package, task adapters, backend integration, and custom SpiNNaker runtime. |
| [`experiments/`](experiments) | Tier runners, evidence registry tooling, audit tooling, and paper-table export. |
| [`controlled_test_output/`](controlled_test_output) | Reproducible evidence bundles, generated registry, paper table CSV, and noncanonical audit history. |
| [`baselines/`](baselines) | Frozen baseline locks for software and native-runtime evidence states. |
| [`docs/`](docs) | Research documentation, roadmap, reviewer-defense plan, runbooks, whitepaper, and codebase map. |
| [`ebrains_jobs/`](ebrains_jobs) | Source-only EBRAINS JobManager upload packages preserving what was sent to hardware. |

Current execution queue:
[`docs/MASTER_EXECUTION_PLAN.md`](docs/MASTER_EXECUTION_PLAN.md). The completed
Tier 5.19 temporal-dynamics contract is preserved at
[`docs/TIER5_19_CONTINUOUS_TEMPORAL_DYNAMICS_CONTRACT.md`](docs/TIER5_19_CONTINUOUS_TEMPORAL_DYNAMICS_CONTRACT.md).
The current usefulness-testing contract is
[`docs/TIER6_2_USEFULNESS_BATTERY_CONTRACT.md`](docs/TIER6_2_USEFULNESS_BATTERY_CONTRACT.md).
The current healthy-NEST rebaseline scoring gate should be run through the
sharded plan in
[`docs/TIER5_45A_SHARD_EXECUTION_PLAN.md`](docs/TIER5_45A_SHARD_EXECUTION_PLAN.md)
before any new mechanism promotion or baseline freeze.

## Quick Start

```bash
git clone https://github.com/jamesvmurdockiii/Project-Kianna---CRA_JKS.git
cd Project-Kianna---CRA_JKS
python3 -m venv .venv
source .venv/bin/activate
pip install numpy scipy matplotlib
```

Optional backend dependencies depend on the experiment being run:

```bash
pip install nest-simulator   # NEST-backed local experiments, if available
pip install sPyNNaker        # SpiNNaker/PyNN experiments, if available
```

Run the standard validation suite:

```bash
make validate
```

Run a small local smoke test:

```bash
python3 experiments/tier1_sanity.py --backend mock
```

Run a baseline comparison example:

```bash
python3 experiments/tier5_external_baselines.py \
  --backend nest \
  --seed-count 3 \
  --steps 240 \
  --models all \
  --tasks all
```

## Validation

`make validate` currently runs:

- 151 pytest unit tests.
- Evidence registry generation: 127 canonical bundles, 0 failed criteria.
- Paper results table export.
- Repository audit.

Generated outputs include:

- [`STUDY_EVIDENCE_INDEX.md`](STUDY_EVIDENCE_INDEX.md)
- [`docs/PAPER_RESULTS_TABLE.md`](docs/PAPER_RESULTS_TABLE.md)
- [`docs/RESEARCH_GRADE_AUDIT.md`](docs/RESEARCH_GRADE_AUDIT.md)
- [`controlled_test_output/README.md`](controlled_test_output/README.md)

## Documentation Map

| Document | Purpose |
| --- | --- |
| [`docs/ABSTRACT.md`](docs/ABSTRACT.md) | Concise project abstract and current evidence boundary. |
| [`docs/WHITEPAPER.md`](docs/WHITEPAPER.md) | Technical overview of architecture, evidence, limitations, and roadmap. |
| [`docs/PAPER_READINESS_ROADMAP.md`](docs/PAPER_READINESS_ROADMAP.md) | Strategic roadmap toward paper-ready claims. |
| [`docs/MASTER_EXECUTION_PLAN.md`](docs/MASTER_EXECUTION_PLAN.md) | Operational execution sequence from the current state. |
| [`CONTROLLED_TEST_PLAN.md`](CONTROLLED_TEST_PLAN.md) | Tier definitions, hypotheses, controls, pass/fail criteria, and claim boundaries. |
| [`docs/REVIEWER_DEFENSE_PLAN.md`](docs/REVIEWER_DEFENSE_PLAN.md) | Reviewer attack matrix and planned safeguards. |
| [`docs/CODEBASE_MAP.md`](docs/CODEBASE_MAP.md) | File-by-file map of source, experiments, runtime code, and evidence areas. |
| [`docs/SPINNAKER_EBRAINS_RUNBOOK.md`](docs/SPINNAKER_EBRAINS_RUNBOOK.md) | EBRAINS/SpiNNaker upload, run, ingest, and troubleshooting guide. |
| [`docs/PUBLIC_REPO_HYGIENE.md`](docs/PUBLIC_REPO_HYGIENE.md) | Public repository artifact policy, security checks, and clean/commit SOP. |
| [`codebasecontract.md`](codebasecontract.md) | Maintainer operating contract for evidence discipline and repository updates. |

## Contributing

Read [`CONTRIBUTING.md`](CONTRIBUTING.md) before opening issues or pull requests.
Changes that affect claims must include explicit pass/fail criteria, controls or
ablations, reproducible artifacts, and documentation updates. Generated registry
and paper-table files should be regenerated through tooling rather than edited by
hand.

## Citation

If you use this repository in research, cite the evidence registry and the exact
commit used. A placeholder software citation is:

```bibtex
@software{cra_2026,
  title        = {Coral Reef Architecture: A Neuromorphic Local-Learning Research Platform},
  author       = {Murdock, James V. and CRA Contributors},
  year         = {2026},
  url          = {https://github.com/jamesvmurdockiii/Project-Kianna---CRA_JKS},
  note         = {127 canonical evidence bundles; bounded SpiNNaker hardware validation}
}
```

## License

Apache License 2.0. See [`LICENSE`](LICENSE).

# Tier 7.0 Standard Dynamical Benchmark Suite

- Generated: `2026-05-05T13:47:31+00:00`
- Status: **PASS**
- Runner revision: `tier7_0_standard_dynamical_benchmarks_20260505_0001`
- Criteria: `10/10`
- Tasks: `mackey_glass, lorenz, narma10`
- Models: `persistence, online_lms, ridge_lag, echo_state_network, cra_v2_1_online`

## Claim Boundary

Tier 7.0 is software benchmark/diagnostic evidence only. It compares CRA v2.1 online behavior against causal sequence baselines on Mackey-Glass, Lorenz, NARMA10, and aggregate geometric-mean MSE. It is not hardware evidence, not a new baseline freeze, not a superiority claim, and not a tuning run.

## Task Summary

| Task | Model | Status | MSE mean | NMSE mean | Tail MSE mean |
| --- | --- | --- | ---: | ---: | ---: |
| mackey_glass | persistence | pass | 1.2754036626437275 | 1.3718770463741536 | 1.329134532021313 |
| mackey_glass | online_lms | pass | 0.2004835047440751 | 0.21527358220094514 | 0.14926874570052315 |
| mackey_glass | ridge_lag | pass | 0.1343420001621094 | 0.14536143559365944 | 0.11529575301261026 |
| mackey_glass | echo_state_network | pass | 0.07139050452934584 | 0.0780838434901167 | 0.06653216028924681 |
| mackey_glass | cra_v2_1_online | pass | 2.22475289773899 | 2.38929145132667 | 2.412544335073546 |
| lorenz | persistence | pass | 0.2507609369289621 | 0.6580567588643227 | 0.40018165314681325 |
| lorenz | online_lms | pass | 0.01641471233170188 | 0.043748695181649894 | 0.021830604723405634 |
| lorenz | ridge_lag | pass | 0.0017635524863088916 | 0.00452176841062472 | 0.00436642600740788 |
| lorenz | echo_state_network | pass | 0.0003506249812987444 | 0.000821082722612274 | 0.0011107216763397544 |
| lorenz | cra_v2_1_online | pass | 0.6659789418682946 | 1.8530719451305713 | 0.7536640081993008 |
| narma10 | persistence | pass | 1.337966255810566 | 1.61616204404356 | 1.4267639192643424 |
| narma10 | online_lms | pass | 0.16086872717672615 | 0.18950870877555093 | 0.14437402881869751 |
| narma10 | ridge_lag | pass | 0.17091975977488702 | 0.20530399826557025 | 0.15936264268573788 |
| narma10 | echo_state_network | pass | 0.652396647721169 | 0.7706716902275278 | 0.668117480540196 |
| narma10 | cra_v2_1_online | pass | 1.2391510406368849 | 1.470946024662031 | 1.064036626736212 |

## Aggregate Geometric Mean

| Model | Seed | Status | Geomean MSE | Geomean NMSE |
| --- | ---: | --- | ---: | ---: |
| persistence | 42 | pass | 0.8027449428739922 | 1.097864318410264 |
| persistence | 43 | pass | 0.6450385660456428 | 1.0364480679707972 |
| persistence | 44 | pass | 0.7962229869232851 | 1.255416421953395 |
| online_lms | 42 | pass | 0.09290301694556728 | 0.1270576766413995 |
| online_lms | 43 | pass | 0.06828375012501171 | 0.10971834029201474 |
| online_lms | 44 | pass | 0.0796292461965029 | 0.12555259642672356 |
| ridge_lag | 42 | pass | 0.03256791719938963 | 0.04454111425496996 |
| ridge_lag | 43 | pass | 0.026950780700076674 | 0.043304518609082014 |
| ridge_lag | 44 | pass | 0.04149833089498144 | 0.06543102490739211 |
| echo_state_network | 42 | pass | 0.02237107057138041 | 0.030595521482857515 |
| echo_state_network | 43 | pass | 0.015600073841812452 | 0.025066201068672536 |
| echo_state_network | 44 | pass | 0.03020244683480168 | 0.0476206393966337 |
| cra_v2_1_online | 42 | pass | 1.3166091674767206 | 1.80064445014066 |
| cra_v2_1_online | 43 | pass | 1.2316074184773704 | 1.9789469910378148 |
| cra_v2_1_online | 44 | pass | 1.1215512422698573 | 1.768366237514152 |

## Outcome Classification

- Outcome: `cra_underperforms_standard_sequence_baselines`
- Best model: `echo_state_network`
- CRA rank: `5`
- CRA / best non-CRA MSE ratio: `53.82975667035733`
- Recommendation: Run Tier 7.0b failure analysis before tuning or hardware migration; classify whether the gap is continuous-valued regression readout, long-memory state, reservoir dynamics, normalization, or policy/credit mismatch.

| Model | Rank | Geomean MSE mean | Geomean NMSE mean |
| --- | ---: | ---: | ---: |
| echo_state_network | 1 | 0.022724530415998184 | 0.034427453982721255 |
| ridge_lag | 2 | 0.03367234293148258 | 0.051092219257148026 |
| online_lms | 3 | 0.08027200442236064 | 0.12077620445337926 |
| persistence | 4 | 0.7480021652809734 | 1.1299096027781521 |
| cra_v2_1_online | 5 | 1.223255942741316 | 1.8493192262308755 |

## Interpretation Rule

- This tier diagnoses capability; it does not freeze a new baseline by itself.
- If CRA underperforms, classify the failure mode before adding mechanisms or tuning.
- Do not move this suite to hardware until the software harness is stable and reviewer-safe.

# Tier 5.18c Self-Evaluation Compact Regression Findings

- Generated: `2026-04-29T23:29:34+00:00`
- Status: **PASS**
- Output directory: `/Users/james/JKS:CRA/controlled_test_output/tier5_9c_20260429_190503/v2_1_guardrail`
- Smoke: `False`

Tier 5.18c is the promotion/regression gate for the Tier 5.18 self-evaluation diagnostic. It does not add a new capability claim; it asks whether v2.0 guardrails and the self-evaluation diagnostic can pass together before a bounded v2.1 freeze.

## Claim Boundary

- `PASS` authorizes a bounded host-side software v2.1 freeze for operational self-evaluation / reliability monitoring.
- It is not consciousness, self-awareness, introspection, SpiNNaker hardware self-monitoring, language, planning, AGI, or external-baseline superiority.
- Hardware/custom-C transfer remains future work.

## Summary

- children_passed: `2` / `2`
- criteria_passed: `4` / `4`
- runtime_seconds: `1471.352`

## Child Runs

| Child | Status | Runtime seconds | Purpose | Failure |
| --- | --- | ---: | --- | --- |
| `v2_0_compact_regression_gate` | **PASS** | `1468.366` | rerun the v2.0 promotion/regression stack: v1.8 compact regression, v1.9 composition/routing, Tier 5.14, and Tier 5.17d guardrails remain green |  |
| `tier5_18_self_evaluation_guardrail` | **PASS** | `2.982` | rerun the Tier 5.18 calibrated pre-feedback reliability-monitoring and confidence-gated adaptation diagnostic |  |

## Criteria

| Criterion | Value | Rule | Pass |
| --- | --- | --- | --- |
| frozen v2.0 baseline artifact exists | `/Users/james/JKS:CRA/baselines/CRA_EVIDENCE_BASELINE_v2.0.json` | `exists` | yes |
| v2.0 compact regression gate remains green | `pass` | `== pass` | yes |
| Tier 5.18 self-evaluation guardrail remains green | `pass` | `== pass` | yes |
| all child commands succeeded | `2/2` | `== 2/2` | yes |

## Artifacts

- `child_manifests_json`: `/Users/james/JKS:CRA/controlled_test_output/tier5_9c_20260429_190503/v2_1_guardrail/tier5_18c_child_manifests.json`
- `summary_csv`: `/Users/james/JKS:CRA/controlled_test_output/tier5_9c_20260429_190503/v2_1_guardrail/tier5_18c_summary.csv`
- `report_md`: `/Users/james/JKS:CRA/controlled_test_output/tier5_9c_20260429_190503/v2_1_guardrail/tier5_18c_report.md`

# Tier 5.9c Macro Eligibility v2.1 Recheck Findings

- Generated: `2026-04-29T23:53:13+00:00`
- Status: **FAIL**
- Output directory: `/Users/james/JKS:CRA/controlled_test_output/tier5_9c_20260429_190503`
- Smoke: `False`

Tier 5.9c rechecks the parked macro-eligibility mechanism after the v2.1 software baseline. It asks whether the current v2.1 guardrails remain green and whether the residual macro trace now earns its own delayed-credit promotion gate.

## Claim Boundary

- `PASS` would authorize a later v2.1-plus-macro integration tier, not immediate baseline freeze.
- `FAIL` keeps macro eligibility parked as non-promoted diagnostic evidence.
- This is not SpiNNaker hardware evidence, native/on-chip eligibility, custom-C runtime evidence, or external-baseline superiority.
- The child macro diagnostic still uses the delayed-credit harness; v2.1 integration requires a separate follow-up gate if this passes.

## Summary

- children_passed: `1` / `2`
- criteria_passed: `2` / `4`
- runtime_seconds: `2889.924`

## Child Runs

| Child | Status | Runtime seconds | Purpose | Failure |
| --- | --- | ---: | --- | --- |
| `v2_1_guardrail` | **PASS** | `1471.410` | rerun the v2.1 promotion/regression gate so the current baseline remains intact before interpreting macro-credit work |  |
| `macro_residual_recheck` | **FAIL** | `1418.506` | rerun the residual macro-eligibility diagnostic that previously failed trace-ablation separation | command exited 1 |

## Criteria

| Criterion | Value | Rule | Pass |
| --- | --- | --- | --- |
| frozen v2.1 baseline artifact exists | `/Users/james/JKS:CRA/baselines/CRA_EVIDENCE_BASELINE_v2.1.json` | `exists` | yes |
| v2.1 guardrail remains green | `pass` | `status == pass and return_code == 0` | yes |
| residual macro eligibility earns promotion gate | `fail` | `status == pass and return_code == 0` | no |
| all child commands succeeded | `1/2` | `== 2/2` | no |

Failure: Failed criteria: residual macro eligibility earns promotion gate, all child commands succeeded

## Artifacts

- `child_manifests_json`: `/Users/james/JKS:CRA/controlled_test_output/tier5_9c_20260429_190503/tier5_9c_child_manifests.json`
- `summary_csv`: `/Users/james/JKS:CRA/controlled_test_output/tier5_9c_20260429_190503/tier5_9c_summary.csv`
- `report_md`: `/Users/james/JKS:CRA/controlled_test_output/tier5_9c_20260429_190503/tier5_9c_report.md`

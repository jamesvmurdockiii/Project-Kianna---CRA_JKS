# Tier 5.9c Macro Eligibility v2.1 Recheck Findings

- Generated: `2026-04-29T23:04:49+00:00`
- Status: **PASS**
- Output directory: `<repo>/controlled_test_output/tier5_9c_20260429_190257`
- Smoke: `True`

Tier 5.9c rechecks the parked macro-eligibility mechanism after the v2.1 software baseline. It asks whether the current v2.1 guardrails remain green and whether the residual macro trace now earns its own delayed-credit promotion gate.

## Claim Boundary

- `PASS` would authorize a later v2.1-plus-macro integration tier, not immediate baseline freeze.
- `FAIL` keeps macro eligibility parked as non-promoted diagnostic evidence.
- This is not SpiNNaker hardware evidence, native/on-chip eligibility, custom-C runtime evidence, or external-baseline superiority.
- The child macro diagnostic still uses the delayed-credit harness; v2.1 integration requires a separate follow-up gate if this passes.

## Summary

- children_passed: `2` / `2`
- criteria_passed: `4` / `4`
- runtime_seconds: `112.344`

## Child Runs

| Child | Status | Runtime seconds | Purpose | Failure |
| --- | --- | ---: | --- | --- |
| `v2_1_guardrail` | **PASS** | `107.732` | rerun the v2.1 promotion/regression gate so the current baseline remains intact before interpreting macro-credit work |  |
| `macro_residual_recheck` | **PASS** | `4.609` | rerun the residual macro-eligibility diagnostic that previously failed trace-ablation separation |  |

## Criteria

| Criterion | Value | Rule | Pass |
| --- | --- | --- | --- |
| frozen v2.1 baseline artifact exists | `<repo>/baselines/CRA_EVIDENCE_BASELINE_v2.1.json` | `exists` | yes |
| v2.1 guardrail remains green | `pass` | `status == pass and return_code == 0` | yes |
| residual macro eligibility earns promotion gate | `pass` | `status == pass and return_code == 0` | yes |
| all child commands succeeded | `2/2` | `== 2/2` | yes |

## Artifacts

- `child_manifests_json`: `<repo>/controlled_test_output/tier5_9c_20260429_190257/tier5_9c_child_manifests.json`
- `summary_csv`: `<repo>/controlled_test_output/tier5_9c_20260429_190257/tier5_9c_summary.csv`
- `report_md`: `<repo>/controlled_test_output/tier5_9c_20260429_190257/tier5_9c_report.md`

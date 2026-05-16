# Tier 5.17e Predictive-Binding Compact Regression Findings

- Generated: `2026-04-29T20:30:44+00:00`
- Status: **PASS**
- Backend for compact regression: `mock`
- Smoke mode: `True`
- Candidate baseline: `v2.0_host_predictive_binding`, `readout_lr=0.1`, `delayed_readout_lr=0.2`
- Output directory: `<repo>/controlled_test_output/tier5_17e_20260429_162729`

Tier 5.17e is a promotion/regression gate after the Tier 5.17d predictive-binding repair. It is not a new capability claim. It checks that prior compact guardrails, v1.9 composition/routing, Tier 5.14 working-memory/context binding, and Tier 5.17d predictive-binding shams all remain clean before a v2.0 baseline can be frozen.

## Claim Boundary

- Software-only promotion/regression evidence.
- A pass authorizes a bounded v2.0 software baseline freeze for host-side predictive-binding pre-reward structure layered on v1.9-era mechanisms.
- A pass does not prove general unsupervised concept learning, hardware/on-chip representation learning, full world modeling, language, planning, AGI, or external-baseline superiority.
- A failure means Tier 5.17d stays noncanonical and v1.9 remains the latest frozen carried-forward baseline.

## Child Runs

| Child | Status | Return Code | Runtime Seconds | Purpose | Manifest |
| --- | --- | ---: | ---: | --- | --- |
| `v1_8_compact_regression` | **PASS** | 0 | 38.990 | existing compact guardrail: Tier 1/2/3, target smokes, replay/consolidation, and predictive-context checks remain green | `<repo>/controlled_test_output/tier5_17e_20260429_162729/v1_8_compact_regression/tier5_12d_results.json` |
| `v1_9_composition_routing_guardrail` | **PASS** | 0 | 55.287 | v1.9 host-side internal composition/routing remains intact before adding predictive-binding to the baseline lock | `<repo>/controlled_test_output/tier5_17e_20260429_162729/v1_9_composition_routing_guardrail/tier5_13c_results.json` |
| `working_memory_context_guardrail` | **PASS** | 0 | 94.696 | Tier 5.14 working-memory/context-binding diagnostic still passes over the carried-forward v1.9-era host-side mechanisms | `<repo>/controlled_test_output/tier5_17e_20260429_162729/working_memory_context_guardrail/tier5_14_results.json` |
| `predictive_binding_guardrail` | **PASS** | 0 | 5.396 | Tier 5.17d predictive-binding repair still clears leakage, dopamine, probe, and sham-separation gates | `<repo>/controlled_test_output/tier5_17e_20260429_162729/predictive_binding_guardrail/tier5_17d_results.json` |

## Criteria

| Criterion | Value | Rule | Pass |
| --- | --- | --- | --- |
| v1.8 compact regression stack remains green | `pass` | status == pass and return_code == 0 | yes |
| v1.9 composition/routing guardrail remains green | `pass` | status == pass and return_code == 0 | yes |
| Tier 5.14 working-memory/context guardrail remains green | `pass` | status == pass and return_code == 0 | yes |
| Tier 5.17d predictive-binding guardrail remains green | `pass` | status == pass and return_code == 0 | yes |

## Required Artifacts

- `tier5_17e_results.json`: machine-readable promotion/regression manifest.
- `tier5_17e_report.md`: this human-readable report.
- `tier5_17e_summary.csv`: compact child-run summary.
- `tier5_17e_child_manifests.json`: copied child manifest payloads for audit traceability.
- child stdout/stderr logs for every subprocess.

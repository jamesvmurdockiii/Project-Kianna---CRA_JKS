# Tier 7.7c Standardized Long-Run / Failure-Localization Contract

- Generated: `2026-05-09T13:45:19+00:00`
- Status: **PASS**
- Criteria: `15/15`

## Question

Does the Tier 7.7b v2.5 standardized progress signal persist under longer streams, and what explains the Lorenz/NARMA10 plus external-baseline gap?

## Locked Lengths

| Length | Role | Required | Claim Use |
| ---: | --- | --- | --- |
| 8000 | anchor | True | reproduce Tier 7.7b locked score inside the long-run scoring output |
| 16000 | long_run_primary | True | test whether v2.5 signal persists after twice the locked 7.7b exposure |
| 32000 | long_run_primary | True | test whether v2.5 signal grows, plateaus, or collapses over longer exposure |
| 50000 | optional_runtime_diagnostic | False | optional stress only if finite/runtime budget permits; cannot replace required lengths |

## Diagnostic Questions

- `mackey_signal_persistence`: Does the Mackey-Glass improvement persist or grow as the stream length increases?
- `lorenz_state_reconstruction_gap`: Is Lorenz flat because the current one-dimensional causal interface lacks enough state reconstruction?
- `narma_memory_depth_gap`: Is NARMA10 flat because the current memory/readout path lacks sufficient nonlinear memory depth?
- `external_baseline_gap`: Do ESN/online-linear/ridge baselines win because of richer state, stronger readout, or simple linear fit advantages?
- `sham_specificity`: Do target/time/state/planning shams stay separated at longer lengths?

## Pass/Fail Classes

- `long_run_confirmed`: v2.5 improves v2.3 aggregate by >=10% at both 16000 and 32000 with paired support, while at least 2/3 tasks or tail metrics improve and shams stay separated
- `mackey_only_localized`: Mackey-Glass remains improved but Lorenz/NARMA10 stay flat or worse
- `baseline_gap_persists`: v2.5 improves v2.3 but ESN/online-linear/ridge remain materially better on aggregate
- `signal_collapses`: 7.7b aggregate improvement disappears at 16000 or 32000, or shams match the candidate
- `stop_or_narrow`: v2.5 fails to improve v2.3 at longer lengths and standard baselines dominate all required lengths

## Nonclaims

- not a new score by itself
- not a new baseline freeze
- not hardware/native evidence
- not a mechanism implementation
- not external-baseline superiority unless 7.7d shows it
- not language, broad reasoning, AGI, or ASI evidence

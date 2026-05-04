# Tier 4.22e Local Continuous-Learning Parity Scaffold

- Generated: `2026-04-30T18:45:15+00:00`
- Status: **PASS**
- Output directory: `/Users/james/JKS:CRA/controlled_test_output/tier4_22e_20260430_local_learning_parity`

Tier 4.22e compares the custom-C fixed-point delayed-readout equations against a floating reference on delayed-credit task streams. It also checks that the pending-horizon state does not store future targets at prediction time.

## Summary

- Tier 4.22d latest status: `pass`
- Host C tests passed: `True`
- Source checks passed: `6` / `6`
- Minimum fixed/float sign agreement: `1`
- Maximum final weight delta: `4.14238e-05`
- Minimum fixed tail accuracy: `0.547619`
- Minimum pending advantage over no-pending tail: `0.547619`

## Criteria

| Criterion | Value | Rule | Pass |
| --- | --- | --- | --- |
| runner revision current | `tier4_22e_local_learning_parity_20260430_0000` | `expected current source` | yes |
| Tier 4.22d reward/plasticity scaffold pass exists | `pass` | `== pass` | yes |
| custom C host tests pass | `0` | `returncode == 0 and ALL TESTS PASSED` | yes |
| all source checks pass | `6/6` | `all pass` | yes |
| fixed/float sign agreement | `1` | `>= 0.999` | yes |
| final weight parity | `4.14238e-05` | `<= 0.001` | yes |
| final bias parity | `4.72093e-05` | `<= 0.001` | yes |
| delayed_cue tail accuracy | `1` | `>= 0.95` | yes |
| hard_noisy_switching tail accuracy | `0.547619` | `>= 0.5` | yes |
| pending queue beats no-pending ablation | `0.547619` | `>= 0.2` | yes |
| pending queue does not overflow | `0` | `== 0` | yes |

## Case Summaries

| Task | Seed | Events | Fixed Tail | No-Pending Tail | Sign Agreement | Weight Delta |
| --- | --- | --- | --- | --- | --- | --- |
| delayed_cue | `42` | `150` | `1` | `0` | `1` | `3.05176e-05` |
| hard_noisy_switching | `42` | `171` | `0.547619` | `0` | `1` | `4.14238e-05` |

## Claim Boundary

- This is local minimal delayed-readout parity evidence.
- It is not a hardware run.
- It is not full CRA parity, lifecycle/replay/routing parity, custom-runtime speedup, or final on-chip proof.
- It authorizes the next hardware/build-oriented gate only if the hardware command/readback path can expose the same state.

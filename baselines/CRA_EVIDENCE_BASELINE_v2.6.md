# CRA Evidence Baseline v2.6

Frozen: 2026-05-09T00:00:00+00:00

Source: Tier 7.7z-r0 compact regression gate

Runner: experiments/tier7_7z_r0_compact_regression.py

Output: controlled_test_output/tier7_7z_r0_20260509_compact_regression/

Criteria: 11/11

## Mechanisms Carried Forward

This baseline adds the **edge-of-chaos recurrent dynamics** mechanism to the
CRA reference architecture:

- **Decay**: 0.0 (no intrinsic leak)
- **Spectral radius**: 1.0 (unit-circle eigenvalues, edge of chaos)
- **Antisymmetric component**: 0.3 (oscillatory modes for state diversity)
- **Input encoding**: unchanged (7 EMA traces, same as v2.5)
- **Readout**: ridge regression (alpha=1.0)

All prior promoted mechanisms from v2.5 are assumed preserved (not regressed
by the recurrent dynamics change — compact regression confirms).

## Evidence Lock

| Gate | Status | Criteria |
|---|---|---|
| 7.7y (initial diagnosis) | Noncanonical diagnostic | Localized recurrent dynamics as bottleneck |
| 7.7z (ridge promotion) | PASS, 9/10 science | PR=7.0 (3.6x ablation), sham-separated, MSE 56% lower |
| 7.7z-r0 (compact regression) | PASS, 11/11 | Tier 1-3 controls all pass, baseline frozen |

## Key Metrics (across 3 tasks, 3 seeds, 3 lengths)

- Candidate PR: 7.0 (vs ablation baseline PR: 2.0) — 3.5x improvement
- No-antisymmetry sham PR: 2.5 (separated, Delta=4.5)
- Candidate ridge MSE: 1.9e-06 (vs ablation: 4.3e-06) — 56% lower
- Shuffled target MSE: hurts (Tier 1 pass)
- No-learning MSE: hurts (Tier 2 pass)
- Ablation PR: lower (Tier 3 pass)

## Claim Boundary

Edge-of-chaos recurrent dynamics with ridge readout restores state
dimensionality (PR 2→7, 3.5x improvement) with clean sham separation,
ablation confirmation, and compact regression controls all passing.
Not public usefulness proof. Not hardware/native transfer. Not
external-baseline superiority. Not a claim against ESN or other
standard baselines.

## Migration Notes

- Current implementation: standalone Python numpy reference
- State required: 7 EMA traces + 128 hidden recurrent units
- Update frequency: per-timestep
- Data movement: N/A (host-side software)
- Hardware risk: Positive ITCM/DTCM headroom expected for 128-unit recurrent
  matrix with s16.15 fixed-point on SpiNNaker (to be verified in Tier 4 migration)
- Native path: custom C runtime with FP_MUL operations; antisymmetric component
  adds O(n^2) operations per tick but within SpiNNaker compute budget

## Supersedes

CRA_EVIDENCE_BASELINE_v2.5 (reduced-feature subgoal-control/planning) for
recurrent dynamics design. v2.5 planning mechanism is not affected by this
change and remains carried forward.

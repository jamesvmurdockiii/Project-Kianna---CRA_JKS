# CRA Tier 4.33c - EOC Hardware Smoke
Package: cra_433_eoc
Profile: eoc_recurrent (PROFILE_ID=7)
Hidden units: 64 (DTCM budget: 20KB)

## JobManager Command

```text
cra_433_eoc/experiments/tier4_33c_eoc_ebrains_prepare.py --mode run-hardware --seed 42 --task mackey_glass --length 2000 --output-dir tier4_33c_hw_output
```

## What this tests

Single-core edge-of-chaos recurrent dynamics on real SpiNNaker.
Builds the eoc_recurrent .aplx, loads it on one board, feeds a
Mackey-Glass 2000-step scalar stream, reads back the
EOC compact state, and compares state dimensionality (PR) against
the v2.6 software baseline.

## Expected pass criteria

- .aplx builds for eoc_recurrent profile
- App loads on selected board/core
- EOC state updates produce non-trivial hidden activity range
- Compact readback returns valid hidden_sample
- PR > 2.0 (baseline had PR~2; EOC should be >4)
- Zero synthetic fallback

## Claim boundary

One-board EOC hardware smoke only. Not repeatability, not multi-chip,
not benchmark superiority, not full CRA organism transfer.

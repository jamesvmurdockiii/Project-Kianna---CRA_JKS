# Tier 4.33 Edge-of-Chaos Native Transfer Contract
- Status: **PASS** (11/11)
- Outcome: `eoc_native_transfer_contract_locked`

## Question

Can the v2.6 edge-of-chaos recurrent dynamics mechanism be migrated to the SpiNNaker custom C runtime with s16.15 fixed-point arithmetic while preserving the mechanism's stated benefits (PR restoration, sham separation)?

## Resource Budget

- State: ~568 bytes DTCM
- Compute: O(n^2 + n * input_dim) ~ 18k multiply-adds per tick at n=128 per tick
- Risk: w_rec at 64KB is near DTCM limit; consider n=64 for first smoke (16KB w_rec)

## Next Gate

Tier 4.33a - Edge-of-Chaos Fixed-Point Local Reference

# Tier 7.7v-r0 Diagnostic Model Variant Implementation
- Status: **PASS** (13/13)
- All variants ready: True

## Variants

- **orthogonal_baseline** (orthogonal): Orthogonal recurrent weights; current CRA reference baseline.
- **block_recurrent** (block): Block-structured recurrent weights with varied time constants.
- **frozen_recurrent** (random_recurrent): Random recurrent weights (no orthogonalization). Tests whether learned/structured topology matters for PR.
- **shuffled_input** (shuffled_input): Shuffled EMA trace and hidden channels after bias+observed. Tests whether causal input structure matters.
- **no_plasticity** (orthogonal): Same features as orthogonal_baseline but readout update_enabled=False. Implemented at readout level.
- **state_reset** (state_reset): Periodic state reset via reset_interval in tier5_19b.temporal_features_variant.

## Verification

- **orthogonal_baseline**: PR=1.4708, ok
- **block_recurrent**: PR=2.0702, ok
- **frozen_recurrent**: PR=1.7012, ok
- **shuffled_input**: PR=2.2756, ok
- **no_plasticity**: PR=1.4708, ok
- **state_reset**: PR=1.7384, ok


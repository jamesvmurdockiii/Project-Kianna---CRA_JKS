# Tier 7.1l NAB Locked-Policy Holdout Confirmation

- Generated: `2026-05-08T23:55:19+00:00`
- Runner revision: `tier7_1l_nab_locked_policy_holdout_confirmation_20260508_0001`
- Status: **PASS**
- Criteria: `13/13`
- Outcome: `v2_3_locked_policy_reduced_fp_but_not_confirmed`

## Key Metrics

- Locked v2.3 policy: `persist3`
- Locked v2.3 primary score: `0.11180074060709926`
- Locked v2.3 rank: `5`
- Rolling z-score under locked policy: `0.13854698668870535`
- v2.3 FP/1000 reduction vs raw: `11.441444397652205`
- v2.3 event-F1 loss vs raw: `-0.00974636454716371`
- v2.3 window-recall loss vs raw: `0.4652777777777778`
- v2.3 sham separations: `2`

## Boundary

Tier 7.1l is software locked-policy holdout confirmation over NAB streams not used to select the Tier 7.1k persist3 repair candidate. It is not a new CRA mechanism, not a baseline freeze, not hardware/native transfer, and not AGI/ASI evidence.

## Next Step

If the locked policy confirms on holdout while preserving sham separation and acceptable recall/FP tradeoffs, design a broader public-adapter confirmation. Otherwise narrow the NAB claim or return to planned general mechanisms with this failure mode predeclared.

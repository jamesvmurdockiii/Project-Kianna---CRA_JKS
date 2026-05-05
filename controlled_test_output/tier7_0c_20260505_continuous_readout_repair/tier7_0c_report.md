# Tier 7.0c Bounded Continuous Readout / Interface Repair

- Generated: `2026-05-05T14:09:26+00:00`
- Status: **PASS**
- Criteria: `10/10`
- Outcome: `repair_works_but_lag_only_explains_most_gain`

## Claim Boundary

Tier 7.0c is software repair-candidate evidence only. It tests a bounded online continuous readout/interface over causal CRA state after Tier 7.0b localized the gap. It is not hardware evidence, not a new baseline freeze, not an unconstrained supervised model, and not a final superiority claim.

## Aggregate Summary

| Model | Rank | Geomean MSE mean | Geomean NMSE mean |
| --- | ---: | ---: | ---: |
| lag_only_online_lms_control | 1 | 0.1514560842638888 | 0.22797373549106173 |
| bounded_state_plus_lag_readout_repair | 2 | 0.19040922596175056 | 0.2866382945160751 |
| bounded_state_readout_repair | 3 | 0.3747367253327713 | 0.5645696468077211 |
| state_shuffled_feature_control | 4 | 0.686976895963455 | 1.036506807289399 |
| state_shuffled_target_control | 5 | 0.703767766759309 | 1.0640388920677755 |
| state_frozen_no_update_control | 6 | 0.744299442671371 | 1.1243682956201968 |
| raw_cra_v2_1_online | 7 | 1.223255942741316 | 1.8493192262308755 |

## Repair Classification

- Outcome: `repair_works_but_lag_only_explains_most_gain`
- Best repair model: `bounded_state_plus_lag_readout_repair`
- Raw CRA geomean MSE: `1.223255942741316`
- Best repair improvement over raw: `6.42435226845071`
- Margin vs best shuffled control: `3.607897109468084`
- Margin vs lag-only: `0.7954240846203183`
- Recommendation: Do not promote yet; design a stricter state-specific repair or accept this benchmark mostly measures lag regression.

## Interpretation Rule

- This tier is a repair candidate, not a baseline freeze.
- If the repair passes, the next step is compact regression/promotion, not hardware.
- If lag-only explains the gain, do not call this a CRA mechanism win.


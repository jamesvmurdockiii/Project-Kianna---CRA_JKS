# Tier 7.1k NAB Adapter/Readout False-Positive Repair

- Generated: `2026-05-08T23:40:54+00:00`
- Runner revision: `tier7_1k_nab_false_positive_repair_20260508_0001`
- Status: **PASS**
- Criteria: `9/9`
- Outcome: `v2_3_nab_false_positive_repair_candidate`

## Key Metrics

- Best v2.3 policy: `persist3`
- Best v2.3 primary score: `0.44632600314828624`
- Best v2.3 rank: `1`
- Rolling z-score under best v2.3 policy: `0.11987424686769142`
- v2.3 FP/1000 reduction vs raw: `13.968920433128034`
- v2.3 event-F1 loss vs raw: `-0.2592832593360953`
- v2.3 window-recall loss vs raw: `0.39916666666666667`
- v2.3 sham separations: `3`

## Boundary

Tier 7.1k is software adapter/readout repair over the Tier 7.1i broader NAB subset. It is not a new CRA mechanism, not public usefulness proof by itself, not a baseline freeze, not hardware/native transfer, and not AGI/ASI evidence.

## Next Step

If the repair candidate beats rolling z-score while preserving sham separation, run fairness confirmation. Otherwise narrow the NAB claim or return to planned general mechanisms with this false-positive failure mode as the predeclared target.

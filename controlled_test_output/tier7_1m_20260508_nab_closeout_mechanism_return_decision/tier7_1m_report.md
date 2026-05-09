# Tier 7.1m NAB Closeout / Mechanism-Return Decision

- Generated: `2026-05-09T00:05:48+00:00`
- Runner revision: `tier7_1m_nab_closeout_mechanism_return_decision_20260508_0001`
- Status: **PASS**
- Criteria: `13/13`
- Outcome: `nab_claim_narrowed_return_to_general_mechanisms`

## Decision

- Public usefulness confirmed: `False`
- Freeze authorized: `False`
- Hardware transfer authorized: `False`
- Adapter-policy tuning authorized: `False`
- Selected next gate: `Tier 7.4a - Cost-Aware Policy/Action Selection Contract`

## Claim Boundary

CRA v2.3 showed a partial/localized NAB anomaly signal and a same-subset false-positive repair candidate, but held-out locked-policy confirmation did not prove public NAB usefulness.

## Failure Modes Carried Forward

- false-positive versus recall tradeoff under event/anomaly scoring
- adapter/readout policy can improve a same subset without holding out
- no-update or other sham controls can remain competitive under aggressive alarm filtering
- standard rolling z-score remains a strong baseline on held-out NAB streams

## Stop Rules

- Do not tune additional NAB alarm policies on the same heldout set.
- Do not claim public NAB usefulness from Tier 7.1h-7.1l.
- Do not transfer the NAB adapter path to hardware without a new promoted general mechanism.

## Next Gate Rationale

The held-out NAB failure is an action-cost problem: anomaly alarms are actions with asymmetric false-positive and missed-event costs. The next work should test a general policy/action-selection mechanism, not another NAB-specific threshold repair.

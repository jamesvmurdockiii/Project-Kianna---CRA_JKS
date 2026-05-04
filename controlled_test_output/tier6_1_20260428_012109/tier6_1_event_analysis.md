# Tier 6.1 Event-Type / Claim-Boundary Analysis

This analysis is derived from `tier6_1_lifecycle_events.csv` and `tier6_1_comparisons.csv`.

## Event Counts

- New-polyp events total: `75`
- Cleavage events: `74`
- Adult birth events: `1`
- Death events: `0`

## Advantage Regimes

| Task | Lifecycle | Fixed Pair | Tail Delta | Recovery Improvement | Reason |
| --- | --- | --- | ---: | ---: | --- |
| `hard_noisy_switching` | `life4_16` | `fixed4` | 0.06862745098039208 | 8.710144927536234 | `tail_accuracy,switch_recovery` |
| `hard_noisy_switching` | `life8_32` | `fixed8` | 0.039215686274509776 | 2.4782608695652186 | `tail_accuracy,switch_recovery` |

## Boundary

- This supports software lifecycle expansion with clean lineage tracking and hard_noisy_switching advantage regimes.
- This does not yet prove full adult birth/death turnover because growth was cleavage-dominated and no death events occurred.
- Tier 6.3 sham controls and a future adult-turnover stressor are still required before making the strongest organism/ecology claim.

# Tier 7.4f Cost-Aware Policy/Action Held-Out Scoring Gate

- Generated: `2026-05-09T02:41:35+00:00`
- Runner revision: `tier7_4f_cost_aware_policy_action_heldout_scoring_gate_20260509_0001`
- Status: **PASS**
- Criteria: `20/20`
- Outcome: `v2_4_heldout_public_action_usefulness_qualified_cmapss_only`
- Public usefulness authorized: `True`
- Next gate: `Tier 7.4g - Held-Out Policy/Action Confirmation + Reference Separation`

## Boundary

Software held-out/public action-cost scoring only. This gate can preserve a positive or negative outcome. It is not a baseline freeze, not hardware/native transfer, not a public usefulness claim unless the decision explicitly authorizes that, and not AGI/ASI evidence.

## Family Results

### cmapss_maintenance_action_cost

- Candidate rank: `1`
- Candidate utility/1000: `318.998500352854`
- Best external baseline: `lag_multichannel_ridge_policy` utility/1000 `211.75278814283183`
- Best reference: `v2_2_reference_policy` utility/1000 `316.5285988802314`
- Best sham/ablation: `shuffled_state_sham` utility/1000 `-160.9694557273911`
- Beats best external: `True`
- Point-estimate beats best reference: `True`
- Reference separation CI: `[-12.744203194556462, 16.132348824930187]`
- Reference separation confirmed: `False`
- Separates best sham: `True`

### nab_heldout_alarm_action_cost

- Candidate rank: `3`
- Candidate utility/1000: `-8.482791304997617`
- Best external baseline: `ewma_residual_policy` utility/1000 `-8.075090461834561`
- Best reference: `v2_2_reference_policy` utility/1000 `-8.461739616400449`
- Best sham/ablation: `policy_learning_disabled_ablation` utility/1000 `-11.252452864967719`
- Beats best external: `False`
- Point-estimate beats best reference: `False`
- Reference separation CI: `[-1.6290185101116423, 1.4676643314616906]`
- Reference separation confirmed: `False`
- Separates best sham: `True`

## Interpretation

The frozen v2.4 policy/action stack beat the strongest fair external baseline and separated shams on at least one primary public/real-ish action-cost family. The result is qualified: NAB did not confirm, and C-MAPSS did not separate from the prior v2.2 CRA reference with a positive paired CI, so this is not an incremental v2.4-specific advantage claim yet.

## Nonclaims

- This is not a new baseline freeze.
- This is not hardware/native transfer evidence.
- This is not proof of public usefulness unless the decision explicitly authorizes it.
- Negative or mixed outcomes remain canonical audit evidence rather than being tuned away.

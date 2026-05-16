# Tier 4.22b Continuous Transport Scaffold

- Generated: `2026-04-30T17:59:06+00:00`
- Mode: `prepare`
- Status: **PREPARED**
- Output directory: `<repo>/controlled_test_output/tier4_22b_20260430_prepared`

Tier 4.22b isolates continuous transport: scheduled input, one continuous `sim.run`, and compact/binned spike readback. Learning is intentionally disabled here so transport failures cannot be confused with reward/plasticity bugs.

## Claim Boundary

- This is a transport scaffold, not a learning result.
- It is not native/on-chip learning, custom-C execution, continuous-learning parity, or speedup evidence.
- Learning is added in later gates after timing/readback/state are stable.

## Summary

- Case count: `None`
- Backend(s): `None`
- Sim.run calls sum: `None`
- Expected sim.run calls: `None`
- Sim.run failures: `None`
- Readback failures: `None`
- Synthetic fallbacks: `None`
- Minimum spikes per case: `None`
- Total spikes: `None`
- Runtime seconds sum: `None`

## Criteria

| Criterion | Value | Rule | Pass |
| --- | --- | --- | --- |
| prepare mode explicit | `prepare` | `== prepare` | yes |
| Tier 4.22a0 local preflight pass exists | `pass` | `== pass` | yes |
| continuous transport command emitted | `cra_422b/experiments/tier4_22b_continuous_transport_scaffold.py --mode run-hardware --tasks delayed_cue,hard_noisy_switching --seeds 42 --steps 1200 --population-size 8 --output-dir tier4_22b_job_output` | `contains --mode run-hardware` | yes |
| learning disabled by design | `False` | `False for 4.22b` | yes |

## Next Step

- If this passes, proceed to persistent state and then learning/plasticity gates.

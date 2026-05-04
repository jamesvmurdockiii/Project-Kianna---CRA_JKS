# Tier 4.22b Continuous Transport Scaffold

- Generated: `2026-04-30T18:14:15+00:00`
- Mode: `run-hardware`
- Status: **PASS**
- Output directory: `/tmp/job11885969396211966108.tmp/tier4_22b_job_output`

Tier 4.22b isolates continuous transport: scheduled input, one continuous `sim.run`, and compact/binned spike readback. Learning is intentionally disabled here so transport failures cannot be confused with reward/plasticity bugs.

## Claim Boundary

- This is a transport scaffold, not a learning result.
- It is not native/on-chip learning, custom-C execution, continuous-learning parity, or speedup evidence.
- Learning is added in later gates after timing/readback/state are stable.

## Summary

- Case count: `2`
- Backend(s): `['pyNN.spiNNaker']`
- Sim.run calls sum: `2`
- Expected sim.run calls: `2`
- Sim.run failures: `0`
- Readback failures: `0`
- Synthetic fallbacks: `0`
- Minimum spikes per case: `94896`
- Total spikes: `189896`
- Runtime seconds sum: `220.886`

## Criteria

| Criterion | Value | Rule | Pass |
| --- | --- | --- | --- |
| runner revision current | `tier4_22b_continuous_transport_scaffold_20260430_0000` | `expected current source` | yes |
| Tier 4.22a0 preflight pass exists or bundle is fresh | `missing` | `== pass locally OR missing in fresh source bundle` | yes |
| mode has explicit claim boundary | `run-hardware` | `prepare|local|run-hardware|ingest` | yes |
| case count matches tasks x seeds | `2` | `== 2` | yes |
| all cases passed | `True` | `True` | yes |
| exactly one sim.run per case | `{'calls': 2, 'expected': 2}` | `sum == case_count and max == 1` | yes |
| sim.run failures zero | `0` | `== 0` | yes |
| readback failures zero | `0` | `== 0` | yes |
| synthetic fallback zero | `0` | `== 0` | yes |
| scheduled input failures zero | `0` | `== 0` | yes |
| nonzero spike readback | `94896` | `> 0 per case` | yes |
| transport-only learning disabled | `disabled` | `required for 4.22b isolation` | yes |

## Case Summaries

| Task | Seed | Backend | Calls | Spikes | Runtime s |
| --- | --- | --- | --- | --- | --- |
| delayed_cue | `42` | `pyNN.spiNNaker` | `1` | `95000` | `111.526` |
| hard_noisy_switching | `42` | `pyNN.spiNNaker` | `1` | `94896` | `109.36` |

## Next Step

- Tier 4.22c persistent local state scaffold, then Tier 4.22d reward/plasticity learning path.

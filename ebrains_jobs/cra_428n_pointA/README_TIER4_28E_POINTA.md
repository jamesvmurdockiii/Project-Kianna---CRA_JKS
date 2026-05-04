# Tier 4.28e — Native Failure-Envelope Report — Probe Point A Bundle

Parameters:
```json
{
  "steps": 128,
  "seed": 42,
  "amplitude": 1.0,
  "hard_period": 2,
  "min_delay": 1,
  "max_delay": 1,
  "noise_prob": 0.6,
  "sensory_noise_fraction": 0.25,
  "min_switch_interval": 32,
  "max_switch_interval": 48
}
```

Predicted: pass
Reason: N/A
Events: 64
Max concurrent pending: 1
Context slots: 64

JobManager command:
```text
cra_428n_pointA/experiments/tier4_28e_native_failure_envelope_report.py --mode run-hardware --seed 42 --steps 128 --min-delay 1 --max-delay 1 --noise-prob 0.6 --min-switch 32 --max-switch 48 --output tier4_28e_pointA_job_output
```

Claim boundary: Local package preparation only. NOT hardware evidence.

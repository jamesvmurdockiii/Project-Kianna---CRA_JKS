# Tier 4.28e — Native Failure-Envelope Report — Probe Point B Bundle

Parameters:
```json
{
  "steps": 160,
  "seed": 42,
  "amplitude": 1.0,
  "hard_period": 2,
  "min_delay": 3,
  "max_delay": 5,
  "noise_prob": 0.2,
  "sensory_noise_fraction": 0.25,
  "min_switch_interval": 32,
  "max_switch_interval": 48
}
```

Predicted: fail
Reason: schedule_overflow (78 > 64)
Events: 78
Max concurrent pending: 5
Context slots: 78

JobManager command:
```text
cra_428n_pointB/experiments/tier4_28e_native_failure_envelope_report.py --mode run-hardware --seed 42 --steps 160 --min-delay 3 --max-delay 5 --noise-prob 0.2 --min-switch 32 --max-switch 48 --output tier4_28e_pointB_job_output
```

Claim boundary: Local package preparation only. NOT hardware evidence.

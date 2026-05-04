# Tier 4.28e — Native Failure-Envelope Report — Probe Point C Bundle

Parameters:
```json
{
  "steps": 96,
  "seed": 42,
  "amplitude": 1.0,
  "hard_period": 2,
  "min_delay": 7,
  "max_delay": 10,
  "noise_prob": 0.2,
  "sensory_noise_fraction": 0.25,
  "min_switch_interval": 32,
  "max_switch_interval": 48
}
```

Predicted: pass
Reason: N/A
Events: 43
Max concurrent pending: 10
Context slots: 43

JobManager command:
```text
cra_428n_pointC/experiments/tier4_28e_native_failure_envelope_report.py --mode run-hardware --seed 42 --steps 96 --min-delay 7 --max-delay 10 --noise-prob 0.2 --min-switch 32 --max-switch 48 --output tier4_28e_pointC_job_output
```

Claim boundary: Local package preparation only. NOT hardware evidence.

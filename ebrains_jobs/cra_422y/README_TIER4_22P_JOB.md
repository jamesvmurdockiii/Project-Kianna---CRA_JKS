# Tier 4.22p EBRAINS Tiny A-B-A Reentry Custom-Runtime Micro-Task Job

Upload the `cra_422y` folder itself so the JobManager path starts with `cra_422y/`. Do not upload `controlled_test_output`.

This job builds and loads the custom C runtime, then sends a 30-event A-B-A reentry signed task stream. The target rule follows the feature for regime A, reverses for regime B, then returns to A. Each event records the chip's pre-update prediction, waits behind a two-event pending queue, matures exactly one delayed-credit horizon in order, and compares prediction/weight/bias/counter state against the local s16.15 task reference.

Run command:

```text
cra_422y/experiments/tier4_22p_reentry_micro_task.py --mode run-hardware --output-dir tier4_22p_job_output
```

Pass means a tiny A-B-A reentry learning micro-task matched the local fixed-point reference and met the predeclared reentry/tail-accuracy gates. It is not full CRA task learning, v2.1 transfer, speedup evidence, or final on-chip autonomy.

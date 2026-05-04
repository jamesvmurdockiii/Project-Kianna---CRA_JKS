# Tier 4.22o EBRAINS Tiny Noisy-Switching Custom-Runtime Micro-Task Job

Upload the `cra_422w` folder itself so the JobManager path starts with `cra_422w/`. Do not upload `controlled_test_output`.

This job builds and loads the custom C runtime, then sends a 14-event noisy-switching signed task stream. Each event records the chip's pre-update prediction, waits behind a two-event pending queue, matures exactly one delayed-credit horizon in order, and compares prediction/weight/bias/counter state against the local s16.15 task reference.

Run command:

```text
cra_422w/experiments/tier4_22o_noisy_switching_micro_task.py --mode run-hardware --output-dir tier4_22o_job_output
```

Pass means a tiny noisy-switching learning micro-task matched the local fixed-point reference and met the predeclared tail-accuracy gate. It is not full CRA task learning, v2.1 transfer, speedup evidence, or final on-chip autonomy.

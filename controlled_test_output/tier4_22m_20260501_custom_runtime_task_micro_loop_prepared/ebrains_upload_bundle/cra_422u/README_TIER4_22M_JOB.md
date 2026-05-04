# Tier 4.22m EBRAINS Minimal Custom-Runtime Task Micro-Loop Job

Upload the `cra_422u` folder itself so the JobManager path starts with `cra_422u/`. Do not upload `controlled_test_output`.

This job builds and loads the custom C runtime, then sends a 12-event signed fixed-pattern task stream. Each event records the chip's pre-update prediction, matures exactly one pending delayed-credit horizon, and compares prediction/weight/bias/counter state against the local s16.15 task reference.

Run command:

```text
cra_422u/experiments/tier4_22m_custom_runtime_task_micro_loop.py --mode run-hardware --output-dir tier4_22m_job_output
```

Pass means a minimal task-like learning micro-loop matched the local fixed-point reference and met the predeclared tail-accuracy gate. It is not full CRA task learning, v2.1 transfer, speedup evidence, or final on-chip autonomy.

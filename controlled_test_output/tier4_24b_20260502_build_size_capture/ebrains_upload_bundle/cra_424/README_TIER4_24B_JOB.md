# Tier 4.24b EBRAINS Build/Size Resource Capture Job

Upload the `cra_424` folder itself so the JobManager path starts with `cra_424/`.

This job builds the custom C runtime with `RUNTIME_PROFILE=decoupled_memory_route` on EBRAINS, captures exact .text/.data/.bss via `arm-none-eabi-size`, records .aplx and .elf file sizes, and optionally loads to hardware to capture load time.

**Recommended (build-only):**

```text
cra_424/experiments/tier4_24b_ebrains_build_size_capture.py --mode run-hardware --skip-load --out-dir tier4_24b_job_output
```

**With hardware load (if board is available):**

```text
cra_424/experiments/tier4_24b_ebrains_build_size_capture.py --mode run-hardware --out-dir tier4_24b_job_output
```

Pass means real build-size/resource metrics were captured with no zero-size loopholes.

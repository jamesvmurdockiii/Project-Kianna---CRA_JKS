# Documentation Index

This directory contains the public research documentation for CRA. The docs are
intended to let a reviewer understand what the repository is, what has been
shown, what remains unproven, and how evidence should be reproduced.

## Start Here

| File | Purpose |
| --- | --- |
| `../README.md` | Public landing page and current claim boundary. |
| `ABSTRACT.md` | Concise project abstract and current evidence status. |
| `WHITEPAPER.md` | Technical overview of architecture, evidence, limitations, and paper path. |
| `PAPER_READINESS_ROADMAP.md` | Strategic roadmap from current evidence to a paper-ready claim. |
| `MASTER_EXECUTION_PLAN.md` | Operational step-by-step execution plan from the current state. |
| `REVIEWER_DEFENSE_PLAN.md` | Expected reviewer attacks and required safeguards. |
| `CODEBASE_MAP.md` | Orientation map for source, experiment runners, runtime code, and evidence outputs. |
| `PUBLIC_REPO_HYGIENE.md` | Public artifact policy, security checks, and clean/commit SOP. |
| `PUBLIC_RELEASE_REPORT.md` | Public-facing release/readiness framing: what reviewers should see, what stays ignored, and the current bounded value. |
| `SPINNAKER_EBRAINS_RUNBOOK.md` | EBRAINS/SpiNNaker upload, run, ingest, and troubleshooting guide. |
| `SPINNAKER_EBRAINS_CUSTOM_RUNTIME_GUIDE.md` | Custom-runtime guide for SpiNNaker SDP/SCP, Spin1API, SARK, and JobManager lessons. |
| `PAPER_RESULTS_TABLE.md` | Generated paper-facing evidence table. |
| `RESEARCH_GRADE_AUDIT.md` | Generated repository hygiene and evidence-paperwork audit. |
| `MECHANISM_STATUS.md` | Mechanism ledger separating promoted, diagnostic, parked, and future work. |

## Evidence Categories

| Category | Meaning |
| --- | --- |
| Canonical registry evidence | Paper-table evidence listed in `controlled_test_output/STUDY_REGISTRY.json`. |
| Baseline-frozen evidence | A promoted software or runtime state with a frozen lock under `baselines/`. |
| Noncanonical diagnostic evidence | Useful pass/fail diagnostics that do not by themselves support a paper claim. |
| Failed/parked evidence | Negative evidence retained to avoid p-hacking and explain why mechanisms were not promoted. |
| Hardware prepare/probe evidence | Operational packages or probes that are not hardware claims until ingested and promoted. |

## Current Execution Focus

The active software gate is Tier 5.45a healthy-NEST rebaseline scoring. It should
be run through `TIER5_45A_SHARD_EXECUTION_PLAN.md`. No new organism mechanism,
software baseline, or paper-facing usefulness claim should be promoted until that
matrix is complete, merged, and reviewed.

The current predictive benchmark baseline is `CRA_EVIDENCE_BASELINE_v2.6`. The
`v2.7` state is a diagnostic healthy-NEST snapshot and does not supersede `v2.6`
for predictive benchmark usefulness.

## Public-Repo Rule

Public docs should lead with bounded evidence, not internal conversation history.
Raw EBRAINS downloads, provenance databases, stack traces, compiled binaries,
generated upload bundles, and local scratch artifacts should not be committed as
normal source. If raw artifacts are needed for audit, reference them through a
manifest, hash, release, or external archive.

# Public Repository Hygiene

CRA is a public Apache-2.0 research repository. Every commit should be readable
by external reviewers without private chat context, local machine assumptions, or
unreviewed raw downloads.

## Public-Repo Goals

- A fresh clone explains what CRA is, what has been shown, and what remains
  unproven.
- Source, compact evidence, raw hardware returns, and transient local work are
  clearly separated.
- Every paper-facing claim can be traced to a registry row, tier report,
  pass/fail criteria, runner code, and claim boundary.
- No credentials, private downloads, local caches, machine-specific symlinks, or
  unnecessary raw hardware artifacts enter Git history.
- Failed diagnostics remain visible when they affect the scientific claim, but
  raw failure sludge is summarized rather than dumped into the public tree.

## What Belongs In Git

| Category | Commit? | Notes |
| --- | --- | --- |
| Source code | Yes | `coral_reef_spinnaker/`, `experiments/`, runtime C sources, tests, tooling. |
| Public docs | Yes | `README.md`, `docs/*.md`, `CONTROLLED_TEST_PLAN.md`, `ARTIFACTS.md`. |
| Frozen baselines | Yes | Compact locks and snapshots under `baselines/`. |
| Compact evidence | Yes | Reports, results JSON, summaries, selected expected figures/time-series, registry/table/audit outputs. |
| EBRAINS package templates | Sometimes | Commit compact source-only packages only when they are reproduction-critical. |
| Raw EBRAINS returns | No by default | Archive externally or summarize through ingest artifacts. |
| Provenance DBs/zips/stack traces | No by default | Ignore and externalize unless a reviewer explicitly needs a hash-preserved archive. |
| Compiled binaries/build products | No | Rebuild from source. |
| Private AI handoff/audit files | No | Rewrite as public docs if useful; otherwise keep ignored. |

## Public Claim Rules

Public docs must be realistic:

- Say “research platform” unless a tier specifically supports a stronger claim.
- Say “bounded evidence” for hardware/runtime results unless the full scope has
  passed.
- Never imply AGI, consciousness, language understanding, production readiness,
  or broad superiority unless a predeclared future tier actually earns it.
- Keep negative and parked results visible when they explain why a mechanism was
  not promoted.
- Treat `v2.7` as a diagnostic snapshot unless a later promotion gate changes
  the baseline state.

## EBRAINS Package Rules

1. Upload only the specific source package required by the active tier.
2. Never upload `controlled_test_output/`, local Downloads, caches, or the entire
   repo to JobManager.
3. Never commit symlink packages that point to `/tmp`, a local output folder, or
   another machine-specific path.
4. Verify runner path, command, folder name, README, revision string, and active
   tier before upload.
5. Use a fresh package name after a failed upload/repair to avoid stale cache
   ambiguity.
6. Returned files are not evidence until ingested and documented.

## Evidence Size Policy

The repository may keep compact generated evidence because CRA is a research
artifact, not only a source library. It should not keep raw hardware downloads by
default.

Current policy:

- Keep compact artifacts required by the evidence registry.
- Keep frozen baseline locks and registry snapshots.
- Keep selected small figures/time-series only when they are expected artifacts.
- Ignore raw hardware returns, provenance databases, stack traces, nested upload
  bundles, and compiled binaries.
- If a raw artifact is necessary for review, preserve it externally with a hash
  and reference it from a manifest.

## Security And Hygiene Checklist

Run before public pushes or release-grade cleanup:

```bash
git remote -v
git grep -n -I -E 'ghp_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]+|sk-[A-Za-z0-9]{20,}|AKIA[0-9A-Z]{16}|BEGIN (RSA|OPENSSH|PRIVATE) KEY' -- . || true
LOCAL_PATH_REGEX='/(Users/[^ )]+|tmp/job[0-9]|private/tmp)'
git grep -n -I -E "$LOCAL_PATH_REGEX" -- . || true
git ls-files | rg '(^|/)(reports\.zip|global_provenance\.sqlite3|input_output_database\.sqlite3|data\.sqlite3|ds\.sqlite3|stack_trace|errored|finished)$|raw_download|raw_returned|downloaded_files|_download_intake_originals|raw_hardware_artifacts|raw_reports|spinnaker_reports/|ebrains_upload_bundle|\.elf$|\.aplx$' || true
find ebrains_jobs -maxdepth 1 -type l -ls
find . -path ./.git -prune -o -type f -size +50M -print
git diff --check
make validate
```

Expected state:

- Git remotes contain no embedded credentials.
- Secret scan returns no matches.
- Machine-local path scan returns no committed local paths.
- Raw tracked artifact scan returns no matches.
- EBRAINS packages are not symlinks.
- Large files are known, justified, and below host limits.
- `git diff --check` returns clean.
- `make validate` passes.

If a raw artifact was already committed in prior public history, `.gitignore` and
`git rm --cached` protect future commits but do not erase old blobs. If any
private or sensitive material is ever discovered in history, pause and perform a
proper history-rewrite/credential-rotation process before treating the repository
as release-ready.

## Clean/Commit SOP

1. Verify repo root and run `git status --short --branch`.
2. Classify each changed/untracked path as source, public docs, compact evidence,
   EBRAINS package, raw return, cache, scratch, or private handoff.
3. Preserve user/source work. Do not revert unrelated changes.
4. Update `.gitignore` before new raw artifacts are generated.
5. Use `git rm --cached` for already tracked raw artifacts that should remain
   local but leave Git.
6. Update docs when artifact policy, evidence state, active tier, or claim
   boundary changes.
7. Run `make validate` and inspect generated audit output.
8. Inspect staged changes before committing.
9. Commit source/docs cleanup separately from new science results when possible.

## Reviewer-Facing Principle

Cleanliness is evidence integrity. A reviewer should be able to ask “what exactly
ran, where is the compact artifact, and what does this not prove?” and get the
answer from committed files alone.

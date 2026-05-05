# Public Repository Hygiene

This repository is public Apache-2.0 research infrastructure. Treat every commit
as something a reviewer, reproducer, or future maintainer may inspect without
uncommitted context.

## Public-Repo Goals

- A fresh clone should explain what CRA is, what has been proved, and what has
  not been proved.
- Source, generated evidence, EBRAINS upload packages, and transient local work
  must be clearly separated.
- Claims must remain traceable from a paper-facing statement to registry rows,
  tier reports, exact runner code, and returned hardware artifacts where
  applicable.
- No credentials, local absolute symlink dependencies, private downloads, or
  machine-specific caches should enter Git history.

## What Belongs In Git

| Category | Commit? | Notes |
| --- | --- | --- |
| Source code | Yes | `coral_reef_spinnaker/`, `experiments/`, runtime C sources, tests, tooling. |
| Human docs | Yes | `README.md`, `codebasecontract.md`, `docs/*.md`, `CONTROLLED_TEST_PLAN.md`. |
| Frozen baselines | Yes | `baselines/CRA_EVIDENCE_BASELINE_*` and native runtime/task baselines. |
| Canonical evidence registry | Yes | `controlled_test_output/STUDY_REGISTRY.*`, generated paper table, evidence index. |
| Returned/ingested evidence bundles | Yes | Keep pass/fail/noncanonical history needed for auditability. |
| EBRAINS upload packages | Yes, source-only | `ebrains_jobs/cra_*` folders document exactly what source was uploaded. They must be real directories, not symlinks. |
| Prepared-only duplicate package copies | Usually no | Prefer the canonical `ebrains_jobs/cra_*` package plus any tier report. Do not duplicate packages under ad hoc root output folders. |
| Host test executables | No | Rebuild from source. Ignored by `.gitignore`. |
| `.aplx`, `.elf`, `.o`, build dirs | No | Rebuild from source/toolchain. Ignored by `.gitignore`. |
| Root transient output dirs | No | Examples: `tier4_*_output/`, `tier4_*_job_output/`, local scratch folders. |
| Downloads and reports not ingested | No | `/Users/james/Downloads` is intake only, never canonical evidence. |
| Credentials or private tokens | Never | Sanitize remotes and scan before public pushes. |

## EBRAINS Package Rules

1. Upload only the specific `ebrains_jobs/cra_*` folder for the active tier.
2. Never upload `controlled_test_output/`; it is local evidence storage and can
   be gigabytes.
3. Never commit `ebrains_jobs/cra_*` as a symlink to `/tmp`, `/private/tmp`, a
   local output folder, or another machine-specific path.
4. After a package is prepared, verify the runner exists inside the package and
   the README, command, folder name, runner revision, and active tier all agree.
5. If a package fails after upload, use a fresh package name for the repair.
6. Returned EBRAINS files are not canonical until ingested into
   `controlled_test_output/` and documented with pass/fail boundaries.

## Evidence Size Policy

`controlled_test_output/` is intentionally tracked because this project is being
kept as a reproducible research artifact, not a minimal source-only library. That
choice is expensive: the directory is large and contains many generated files.

Current policy:

- Keep generated evidence when it is needed to reproduce, audit, or explain a
  claim, failure, or noncanonical decision.
- Do not keep duplicate scratch output roots when the same information is already
  represented by a stable job package and an ingested evidence bundle.
- No individual tracked file should approach GitHub's 100 MB hard limit. If a
  future artifact does, move it to an external release/archive plan before
  committing.
- `.gitattributes` marks generated evidence as generated/binary where useful so
  GitHub diffs stay focused on source and docs.

## Security Checklist Before Push

Run these checks before publishing or committing a release-grade cleanup:

```bash
git remote -v
git grep -n -I -E 'ghp_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]+|sk-[A-Za-z0-9]{20,}|AKIA[0-9A-Z]{16}|BEGIN (RSA|OPENSSH|PRIVATE) KEY' -- . || true
find ebrains_jobs -maxdepth 1 -type l -ls
find . -path ./.git -prune -o -type f -size +50M -print
make validate
```

Expected state:

- Git remotes contain no embedded credentials.
- Secret scan returns no matches.
- `ebrains_jobs/` contains no symlink upload packages.
- Large files are known evidence artifacts and below GitHub limits.
- `make validate` passes.

## Clean/Commit Pass SOP

1. Verify repo root and read `codebasecontract.md` Section 0.
2. Run `git status --short` and classify every changed/untracked path as source,
   generated evidence, EBRAINS package, transient local output, cache, or risky
   public artifact.
3. Preserve user/source changes. Do not revert unrelated work.
4. Remove or ignore only clearly transient artifacts: caches, compiled host
   binaries, root scratch output directories, stale prepared duplicates, and
   machine-local symlinks.
5. Materialize any reproducibility-critical upload symlink into a real source
   directory, or omit it if it is a failed/throwaway package already documented
   elsewhere.
6. Update documentation when policy, status, source-of-truth hierarchy, package
   rules, or active-tier state changes.
7. Run validation and a secret/symlink/large-file scan.
8. Inspect staged changes before commit.
9. Commit with a message that states both the research state and the hygiene
   scope.

## Reviewer-Facing Principle

A clean repo is not just aesthetic. It is evidence integrity. If a reviewer asks
"what exactly ran, where is the artifact, and what does this not prove?" the repo
must answer from committed files alone.

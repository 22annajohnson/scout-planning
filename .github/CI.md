# Repository CI

Adapted from the merged scout-ios CI and review conventions.

## What runs

| Changed files | Documentation checks | YAML and CI checks |
| --- | --- | --- |
| Markdown only | Run | Skip |
| YAML only | Skip | Run |
| Markdown and YAML | Run | Run |
| Validator, shared detector, or validation workflow | Run when Markdown validation is affected | Run |
| Other files only | Skip | Skip |
| Manual run or missing baseline | Run | Run |

Markdown checks validate UTF-8, merge-conflict markers, and balanced code fences.
YAML checks validate syntax and basic GitHub workflow/job structure, including
YAML outside `.github`. These are not full Actions expression or shell lint checks.
Changes to the Markdown configuration also run its validator.

A small change-detection job and final `Repository validation` status always run.
The final status fails if detection fails or a selected check fails; intentional
skips pass. PRs compare the merge commit to its base. Pushes compare the previous
and new commits. Deleted/renamed paths and unusual filenames are handled.

Workflows run for PRs to `develop`, pushes to `develop`, and manual dispatch.
Actions use immutable pins and read-only permissions. Checkout credentials are
not persisted. Jobs have five-minute timeouts; superseded runs are cancelled.
Dependabot checks GitHub Actions weekly against `develop`, with two open PRs max.
No branch-protection settings or deployment workflows are changed.

## Local validation

From the repository root:

```sh
ruby .github/scripts/validate-markdown.rb
ruby .github/scripts/validate-yaml.rb
python3 -m unittest discover -s .github/tests -v
```

Tests cover filtering, deleted/renamed files, missing baselines, GitHub outputs,
and valid/invalid Markdown and YAML. Review formats and label transitions live
in [AI_REVIEW.md](AI_REVIEW.md). Label updates are manual, not automated.

## Planning coverage

This repository holds plans and design references. No app build, iOS, backend,
or Supabase job applies. Image-only changes skip text validators and still need
human visual review. Passing CI does not approve architecture or product decisions.

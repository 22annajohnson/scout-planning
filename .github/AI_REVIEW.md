# AI pull request reviews

Be blunt, specific, and brief. Review correctness, not the author's writing style.
Use the [PR template](pull_request_template.md) for PR descriptions.

## Repository focus

For plans, check architecture consistency, scope, unresolved decisions, dependencies, and testable acceptance criteria. Distinguish proposals from approved decisions; do not silently change approval status.

## Review process

1. Read the ticket, full diff, relevant callers/tests, and project guidance.
   Check scope, bugs, regressions, security, and test coverage.
2. Check CI for the current head commit. Distinguish CI evidence from tests you
   ran. State skipped or unavailable validation. Never invent a passing result.
3. Check existing comments. Verify fixes before repeating or closing findings.
   Recheck the head commit before posting; review new changes if it moved.
4. Post one top-level comment using exactly one outcome below. Anchor it to the
   reviewed short commit SHA. Add inline comments only for actionable findings.
5. Apply the matching review-state label. Preserve unrelated labels.

No self-review. AI posts a comment, not GitHub's formal Approve review, and never
merges. Human review is still required after either passing outcome.

## Choose one outcome

| Outcome | Meaning |
| --- | --- |
| ✅ Approved | No blocking findings or nits. Required validation passed. |
| 🟡 Approved with Nits | No blockers. Required validation passed. Suggestions are optional. |
| ❌ Changes Requested | A bug, scope problem, or required validation gap prevents handoff. |

Pending CI is not a code defect: wait for it where possible. If required checks
fail or cannot be verified, use Changes Requested and state the exact unblock
step. Do not invent a code fix for an infrastructure failure. Mark checks that
do not apply as N/A and explain why.

## Comment formats

Keep comments under 120 words when possible. List every blocker even if that
needs more space. Remove unused bullets. Replace placeholders with evidence.

### Approved

```md
## ✅ Approved
Reviewed `<sha>`. <One sentence explaining why the change is sound.>

🧪 Checks: <What passed + CI link. State anything not run.>
🏷️ Next: `needs-human review`
```

### Approved with Nits

```md
## 🟡 Approved with Nits
Reviewed `<sha>`. No blockers.

- Optional: `<file:line>` — <Small improvement and why it helps.>

🧪 Checks: <What passed + CI link. State anything not run.>
🏷️ Next: `needs-human review`
```

### Changes Requested

```md
## ❌ Changes Requested
Reviewed `<sha>`. <One sentence naming the blocker.>

- Fix: `<file:line>` — <Trigger → impact. Required change.>

🧪 Checks: <Failure or missing validation + how to verify the fix.>
🏷️ Next: `needs-changes`
```

Use a workflow/check link instead of `file:line` for a validation blocker.
Keep required fixes separate from optional suggestions. Avoid vague requests
such as "improve error handling"; name the failing case and expected behavior.

## Label transitions

Use these exact names. Keep exactly one of these review-state labels at a time.
These are manual author/reviewer actions; this guide does not install automation.

| Event | Set label | Remove if present |
| --- | --- | --- |
| Author opens a PR ready for review | `needs ai review` | `needs-human review`, `needs-changes` |
| AI posts Approved or Approved with Nits | `needs-human review` | `needs ai review`, `needs-changes` |
| AI posts Changes Requested | `needs-changes` | `needs ai review`, `needs-human review` |
| Author pushes changes after any review | `needs ai review` | `needs-human review`, `needs-changes` |

Add `documentation` for documentation-only PRs. Keep other category labels.
If permissions block a comment or label update, report what failed; do not claim
the handoff succeeded. After changes, review the new commit and post a new
outcome. Earlier comments remain history, not approval of the new commit.

#!/usr/bin/env python3
"""Select docs/config checks independently; unknown baselines run both."""
import os
import subprocess


def selected_checks(event, base, head):
    all_checks = {"docs": True, "config": True}
    if event == "workflow_dispatch" or not base or set(base) == {"0"}:
        return all_checks
    try:
        result = subprocess.run(
            ["git", "diff", "--no-renames", "--name-only", "-z", base, head, "--"],
            check=True, capture_output=True,
        )
    except subprocess.CalledProcessError:
        return all_checks
    paths = [path for path in result.stdout.split(b"\0") if path]
    docs = any(
        path.lower().endswith(b".md") or path in (
            b".github/markdown-validation.yml",
            b".github/scripts/validate-markdown.rb",
            b".github/scripts/ci-changes.py",
            b".github/workflows/repository-validation.yml",
        )
        for path in paths
    )
    config = any(
        path.lower().endswith((b".yml", b".yaml"))
        or (path.startswith(b".github/") and not path.lower().endswith(b".md"))
        for path in paths
    )
    return {"docs": docs, "config": config}


if __name__ == "__main__":
    checks = selected_checks(
        os.environ.get("EVENT_NAME", ""), os.environ.get("BASE_SHA", ""),
        os.environ.get("HEAD_SHA", "HEAD"),
    )
    with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as output:
        for name, run in checks.items():
            value = str(run).lower()
            print(f"Run {name} checks: {value}")
            output.write(f"should-run-{name}={value}\n")

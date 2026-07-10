#!/usr/bin/env python3
"""Build merge context JSON from git for documentation generation."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ZERO_SHA = "0" * 40


def run_git(*args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"git {' '.join(args)} failed (exit {result.returncode}): {result.stderr.strip()}"
        )
    return result.stdout


def sha_exists(sha: str) -> bool:
    if not sha or sha == ZERO_SHA:
        return False
    result = subprocess.run(
        ["git", "rev-parse", "--verify", f"{sha}^{{commit}}"],
        capture_output=True,
        text=True,
    )
    return result.returncode == 0


def is_target_empty(base_sha: str) -> bool:
    if not sha_exists(base_sha):
        return True
    count = run_git("rev-list", "--count", base_sha).strip()
    return int(count) == 0


def collect_git_data(base_sha: str, merge_sha: str, target_empty: bool) -> str:
    if target_empty:
        if sha_exists(merge_sha):
            return run_git("diff", "--root", merge_sha)
        raise RuntimeError("merge-sha is required when the target branch is empty.")

    if not sha_exists(base_sha):
        raise RuntimeError(f"base-sha {base_sha!r} does not resolve to a commit.")
    if not sha_exists(merge_sha):
        raise RuntimeError(f"merge-sha {merge_sha!r} does not resolve to a commit.")

    return run_git("diff", f"{base_sha}..{merge_sha}")


def collect_git_data_from_branches(source_branch: str, target_branch: str) -> tuple[str, bool]:
    merge_base = run_git("merge-base", target_branch, source_branch).strip()
    if not merge_base:
        raise RuntimeError(
            f"Could not find a merge-base between {target_branch!r} and {source_branch!r}."
        )

    target_empty = int(run_git("rev-list", "--count", merge_base).strip()) == 0
    if target_empty:
        head = run_git("rev-parse", source_branch).strip()
        return run_git("diff", "--root", head), True

    return run_git("diff", f"{merge_base}..{source_branch}"), False


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Build context JSON from git merge metadata for generate_documentation.py."
    )
    parser.add_argument("--source-branch", required=True, help="PR head / feature branch name.")
    parser.add_argument("--target-branch", required=True, help="PR base / target branch name.")
    parser.add_argument(
        "--base-sha",
        default="",
        help="Target branch SHA before merge (GitHub pull_request.base.sha).",
    )
    parser.add_argument(
        "--merge-sha",
        default="",
        help="Merge commit SHA (GitHub pull_request.merge_commit_sha).",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("context.json"),
        help="Output JSON path.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.base_sha and args.merge_sha:
        target_empty = is_target_empty(args.base_sha)
        git_data = collect_git_data(args.base_sha, args.merge_sha, target_empty)
    else:
        git_data, target_empty = collect_git_data_from_branches(
            args.source_branch,
            args.target_branch,
        )

    payload = {
        "source_branch": args.source_branch,
        "target_branch": args.target_branch,
        "is_target_branch_empty": target_empty,
        "git_data": git_data,
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote merge context to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

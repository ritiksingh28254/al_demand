"""Build context JSON for the documentation generator from git merge metadata."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

NULL_SHA = "0" * 40


def run_git(*args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return ""
    return result.stdout


def is_empty_target(base_sha: str) -> bool:
    if not base_sha or base_sha == NULL_SHA:
        return True
    count = run_git("rev-list", "--count", base_sha).strip()
    return count in {"", "0"}


def build_git_data(base_sha: str, merge_sha: str, target_empty: bool) -> str:
    if target_empty:
        status_output = run_git(
            "diff-tree",
            "--no-commit-id",
            "--name-status",
            "-r",
            merge_sha,
        )
        if status_output.strip():
            lines = []
            for raw in status_output.splitlines():
                parts = raw.split("\t", 1)
                if len(parts) == 2:
                    lines.append(f"{parts[0]} {parts[1]}")
            return "\n".join(lines)

        file_list = run_git("ls-tree", "-r", "--name-only", merge_sha)
        return "\n".join(f"A {path}" for path in file_list.splitlines() if path.strip())

    diff = run_git("diff", base_sha, merge_sha)
    if diff.strip():
        return diff

    status_output = run_git("diff-tree", "--no-commit-id", "--name-status", "-r", merge_sha)
    return status_output.replace("\t", " ")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build merge context JSON for documentation generation.")
    parser.add_argument("--source-branch", required=True)
    parser.add_argument("--target-branch", required=True)
    parser.add_argument("--base-sha", required=True)
    parser.add_argument("--merge-sha", required=True)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("context.json"),
        help="Output JSON path.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    target_empty = is_empty_target(args.base_sha)
    git_data = build_git_data(args.base_sha, args.merge_sha, target_empty)

    payload = {
        "source_branch": args.source_branch,
        "target_branch": args.target_branch,
        "is_target_branch_empty": target_empty,
        "git_data": git_data,
    }
    args.output.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"Wrote context to {args.output} (empty_target={target_empty})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

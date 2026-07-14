"""
Build structured merge context for AI documentation generation.

Instead of producing one huge git diff, this script generates
a JSON payload containing metadata and a per-file diff.

Output example:

{
    "source_branch": "...",
    "target_branch": "...",
    "is_target_branch_empty": false,
    "generated_at": "...",
    "summary": {
        "total_files": 8,
        "added": 2,
        "modified": 5,
        "deleted": 1
    },
    "files": [
        {
            "path": "src/app.py",
            "status": "modified",
            "diff": "..."
        }
    ]
}
"""

from __future__ import annotations

import argparse
import json
import subprocess
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ZERO_SHA = "0" * 40


# ---------------------------------------------------------
# Git Helpers
# ---------------------------------------------------------

def run_git(*args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip())

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

    count = int(run_git("rev-list", "--count", base_sha).strip())

    return count == 0


# ---------------------------------------------------------
# Git Diff Collection
# ---------------------------------------------------------

def get_changed_files(base: str, head: str):

    output = run_git("diff", "--name-status", f"{base}..{head}")

    files = []

    for line in output.splitlines():

        if not line.strip():
            continue

        parts = line.split("\t")

        status = parts[0]

        if status.startswith("R"):
            status = "renamed"
            path = parts[-1]

        elif status == "A":
            status = "added"
            path = parts[1]

        elif status == "D":
            status = "deleted"
            path = parts[1]

        else:
            status = "modified"
            path = parts[1]

        files.append(
            {
                "path": path,
                "status": status,
            }
        )

    return files


def get_file_diff(base: str, head: str, file_path: str):

    return run_git(
        "diff",
        f"{base}..{head}",
        "--",
        file_path,
    )

def get_diff_statistics(base: str, head: str):

    output = run_git(
        "diff",
        "--numstat",
        f"{base}..{head}",
    )

    insertions = 0
    deletions = 0

    for line in output.splitlines():

        if not line.strip():
            continue

        added, removed, _ = line.split("\t", 2)

        if added != "-":
            insertions += int(added)

        if removed != "-":
            deletions += int(removed)

    return {
        "insertions": insertions,
        "deletions": deletions,
    }

# ---------------------------------------------------------
# Context Builder
# ---------------------------------------------------------

def build_context(
    source_branch: str,
    target_branch: str,
    base_sha: str,
    merge_sha: str,
):

    target_empty = is_target_empty(base_sha)

    if target_empty:

        raise RuntimeError(
            "Initial repository support will be added in V2.1"
        )

    changed_files = get_changed_files(base_sha, merge_sha)

    diff_statistics = get_diff_statistics(base_sha,merge_sha,)

    structured_files = []

    counter = Counter()

    for file in changed_files:

        diff = get_file_diff(
            base_sha,
            merge_sha,
            file["path"],
        )

        counter[file["status"]] += 1

        structured_files.append(
            {
                "path": file["path"],
                "status": file["status"],
                "diff": diff,
                "diff_size": len(diff),
            }
        )

    payload = {

        "source_branch": source_branch,

        "target_branch": target_branch,

        "generated_at": datetime.now(
            timezone.utc
        ).strftime("%Y-%m-%d %H:%M:%S UTC"),

        "is_target_branch_empty": target_empty,

        "summary": {

    "total_files": len(structured_files),

    "added": counter["added"],

    "modified": counter["modified"],

    "deleted": counter["deleted"],

    "renamed": counter["renamed"],

    "lines_added": diff_statistics["insertions"],

    "lines_deleted": diff_statistics["deletions"],

    },

        "files": structured_files,
    }

    return payload


# ---------------------------------------------------------
# CLI
# ---------------------------------------------------------

def build_parser():

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--source-branch",
        required=True,
    )

    parser.add_argument(
        "--target-branch",
        required=True,
    )

    parser.add_argument(
        "--base-sha",
        required=True,
    )

    parser.add_argument(
        "--merge-sha",
        required=True,
    )

    parser.add_argument(
        "--output",
        required=True,
        type=Path,
    )

    return parser


# ---------------------------------------------------------
# Main
# ---------------------------------------------------------

def main():

    args = build_parser().parse_args()

    payload = build_context(
        args.source_branch,
        args.target_branch,
        args.base_sha,
        args.merge_sha,
    )

    args.output.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    args.output.write_text(
        json.dumps(payload, indent=2),
        encoding="utf-8",
    )

    print(f"Context written to {args.output}")

    print(
        f"Changed Files : {payload['summary']['total_files']}"
    )


if __name__ == "__main__":
    main()
"""GitHub Pull/Merge Request documentation generator."""

from __future__ import annotations

import argparse
import json
import os   
import re
import sys
from dataclasses import dataclass
from pathlib import Path

_SRC_DIR = Path(__file__).resolve().parent
if str(_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(_SRC_DIR))

from gemini_enricher import enrich_with_gemini


@dataclass
class ContextMetadata:
    source_branch: str
    target_branch: str
    is_target_branch_empty: bool


@dataclass
class FileChange:
    path: str
    status: str  # added | modified | deleted | renamed
    purpose: str = ""


DIFF_FILE_HEADER = re.compile(r"^diff --git a/(.*) b/(.*)$")
DIFF_NEW_FILE = re.compile(r"^new file mode")
DIFF_DELETED_FILE = re.compile(r"^deleted file mode")
DIFF_RENAME_FROM = re.compile(r"^rename from (.+)$")
DIFF_RENAME_TO = re.compile(r"^rename to (.+)$")


def parse_bool(value: str) -> bool:
    normalized = value.strip().lower()
    if normalized in {"true", "1", "yes", "y"}:
        return True
    if normalized in {"false", "0", "no", "n"}:
        return False
    raise ValueError(f"Invalid boolean value: {value!r}")


def infer_purpose(path: str) -> str:
    suffix = Path(path).suffix.lower()
    name = Path(path).name.lower()

    purpose_map = {
        ".py": "Python source module implementing application or tooling logic.",
        ".md": "Markdown documentation describing project behavior or usage.",
        ".json": "Structured JSON configuration or sample input payload.",
        ".yaml": "YAML configuration for runtime or CI/CD settings.",
        ".yml": "YAML configuration for runtime or CI/CD settings.",
        ".txt": "Plain-text reference or requirements listing.",
        ".sh": "Shell automation script for setup or deployment tasks.",
        ".ps1": "PowerShell automation script for Windows environments.",
        ".gitignore": "Git ignore rules excluding build artifacts and secrets.",
        ".env": "Environment variable template for local configuration.",
    }

    if name == "requirements.txt":
        return "Python dependency manifest for reproducible environment setup."
    if name == "dockerfile":
        return "Container build instructions for packaging the application."
    if name == ".gitignore":
        return "Git ignore rules excluding build artifacts and secrets."
    if name in {"readme.md", "documentation.md"}:
        return "Primary project documentation for onboarding and change tracking."
    if name.endswith(".sample"):
        return "Sample input file demonstrating expected git diff or payload format."

    return purpose_map.get(suffix, "Project asset supporting repository functionality.")


def parse_diff_paths(git_diff: str) -> list[FileChange]:
    changes: list[FileChange] = []
    current_path: str | None = None
    current_status = "modified"

    for line in git_diff.splitlines():
        header = DIFF_FILE_HEADER.match(line)
        if header:
            if current_path:
                changes.append(
                    FileChange(
                        path=current_path,
                        status=current_status,
                        purpose=infer_purpose(current_path),
                    )
                )
            current_path = header.group(2)
            current_status = "modified"
            continue

        if current_path and DIFF_NEW_FILE.match(line):
            current_status = "added"
        elif current_path and DIFF_DELETED_FILE.match(line):
            current_status = "deleted"
        elif current_path:
            rename_to = DIFF_RENAME_TO.match(line)
            if rename_to:
                current_status = "renamed"
                current_path = rename_to.group(1)

    if current_path:
        changes.append(
            FileChange(
                path=current_path,
                status=current_status,
                purpose=infer_purpose(current_path),
            )
        )

    return changes


def render_mode_b(files: list[FileChange]) -> str:
    lines = [
        "# Initial Repository Documentation",
        "",
        "> **First Commit:** The target branch was empty. All listed files below represent the initial base setup.",
        "",
        "## Introduced Files",
        "",
    ]
    for item in files:
        lines.extend([
            f"### `{item.path}`",
            f"- **Status:** {item.status}",
            f"- **Purpose:** {item.purpose}",
            "",
        ])
    return "\n".join(lines).rstrip() + "\n"


def render_mode_a(metadata: ContextMetadata, files: list[FileChange]) -> str:
    added = sum(f.status == "added" for f in files)
    modified = sum(f.status == "modified" for f in files)
    deleted = sum(f.status == "deleted" for f in files)

    lines = [
        "# Pull Request Documentation",
        "",
        "## Branch Information",
        f"- Source Branch: `{metadata.source_branch}`",
        f"- Target Branch: `{metadata.target_branch}`",
        "",
        "## Summary",
        f"- Added Files: {added}",
        f"- Modified Files: {modified}",
        f"- Deleted Files: {deleted}",
        "",
        "## Changed Files",
        "",
    ]

    for item in files:
        lines.append(f"- `{item.path}` ({item.status})")

    return "\n".join(lines) + "\n"


def generate_documentation(metadata: ContextMetadata, git_data: str) -> str:
    files = parse_diff_paths(git_data)

    if not files:
        raise ValueError("No file changes found.")

    if metadata.is_target_branch_empty:
        return render_mode_b(files)
        
    return render_mode_a(metadata, files)


def load_context(context_path: Path) -> tuple[ContextMetadata, str]:
    payload = json.loads(context_path.read_text(encoding="utf-8"))
    metadata = ContextMetadata(
        source_branch=payload["source_branch"],
        target_branch=payload["target_branch"],
        is_target_branch_empty=parse_bool(str(payload["is_target_branch_empty"])),
    )

    git_data = payload.get("git_data", "")
    return metadata, git_data


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate DOCUMENTATION.md from PR/merge request metadata and git data."
    )
    parser.add_argument(
        "--context",
        type=Path,
        required=True,
        help="Path to the merge context JSON file.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("DOCUMENTATION.md"),
        help="Output markdown file path.",
    )
    parser.add_argument(
        "--use-gemini",
        action="store_true",
        help="Enrich output with Gemini when GEMINI_API_KEY is set.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    metadata, git_data = load_context(args.context)
    markdown = generate_documentation(metadata, git_data)

    use_gemini = args.use_gemini or bool(os.getenv("GEMINI_API_KEY"))
    if use_gemini:
        markdown = enrich_with_gemini(
            markdown,
            git_data,
            source_branch=metadata.source_branch,
            target_branch=metadata.target_branch,
            is_target_branch_empty=metadata.is_target_branch_empty,
        )
        print("Applied Gemini enrichment.")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    
    # REQUIREMENT 1: Safe Append Mode with structural block separation
    file_exists = args.output.is_file() and args.output.stat().st_size > 0
    with open(args.output, "a", encoding="utf-8") as f:
        if file_exists:
            f.write("\n\n---\n\n")  # Keeps blocks neatly divided visually
        f.write(markdown)

    print(f"Appended documentation to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
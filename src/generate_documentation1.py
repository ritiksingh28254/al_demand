"""
AI Documentation Generator V2

Reads context.json generated from build_merge_context1.py

Processes changed files in chunks

Calls Gemini for every chunk

Combines all summaries into final documentation
"""

from __future__ import annotations

import argparse
import json
import os
import sys

from pathlib import Path
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import List

# ------------------------------------------------------------
# Import local modules
# ------------------------------------------------------------

_SRC_DIR = Path(__file__).resolve().parent

if str(_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(_SRC_DIR))

from chunker import create_chunks
from gemini_enricher1 import (
    summarize_chunk,
    generate_final_document,
)

# ------------------------------------------------------------
# Models
# ------------------------------------------------------------

@dataclass
class ContextMetadata:

    source_branch: str

    target_branch: str

    is_target_branch_empty: bool

    generated_at: str


@dataclass
class Summary:

    chunk_id: int

    text: str


# ------------------------------------------------------------
# Context Loader
# ------------------------------------------------------------

def load_context(context_path: Path):

    payload = json.loads(
        context_path.read_text(
            encoding="utf-8"
        )
    )

    metadata = ContextMetadata(

        source_branch=payload["source_branch"],

        target_branch=payload["target_branch"],

        is_target_branch_empty=payload[
            "is_target_branch_empty"
        ],

        generated_at=payload["generated_at"],

    )

    files = payload["files"]

    summary = payload["summary"]

    return metadata, files, summary


# ------------------------------------------------------------
# CLI
# ------------------------------------------------------------

def build_parser():

    parser = argparse.ArgumentParser(
        description="Generate AI Documentation"
    )

    parser.add_argument(
        "--context",
        required=True,
        type=Path,
    )

    parser.add_argument(
        "--output",
        default="DOCUMENTATION.md",
        type=Path,
    )

    parser.add_argument(
        "--chunk-size",
        default=10,
        type=int,
    )

    parser.add_argument(
        "--max-chars",
        default=35000,
        type=int,
    )

    parser.add_argument(
        "--use-gemini",
        action="store_true",
    )

    return parser

# ------------------------------------------------------------
# Chunk Processing
# ------------------------------------------------------------

def process_chunks(
    metadata: ContextMetadata,
    files: list,
    *,
    chunk_size: int,
    max_chars: int,
    use_gemini: bool,
) -> List[Summary]:

    chunks = create_chunks(
        files,
        max_chars=max_chars,
        max_files=chunk_size,
    )

    print("=" * 70)
    print(f"Total Files  : {len(files)}")
    print(f"Total Chunks : {len(chunks)}")
    print("=" * 70)

    summaries: List[Summary] = []

    for chunk in chunks:

        print(
            f"\nProcessing Chunk "
            f"{chunk.id}/{len(chunks)}"
        )

        print(
            f"Files : {len(chunk.files)}"
        )

        print(
            f"Size  : {chunk.total_chars} characters"
        )

        if use_gemini:

            summary = summarize_chunk(
                metadata=metadata,
                chunk=chunk,
            )

        else:

            summary = build_local_summary(chunk)

        summaries.append(

            Summary(
                chunk_id=chunk.id,
                text=summary,
            )

        )

        print(
            f"Chunk {chunk.id} completed."
        )

    return summaries


# ------------------------------------------------------------
# Local Summary
# ------------------------------------------------------------

def build_local_summary(chunk):

    lines = []

    lines.append(
        f"# Chunk {chunk.id}"
    )

    lines.append("")

    for file in chunk.files:

        lines.append(

            f"- {file['path']} "
            f"({file['status']})"

        )

    return "\n".join(lines)


# ------------------------------------------------------------
# Statistics
# ------------------------------------------------------------

def build_statistics(files):

    stats = {

        "added": 0,

        "modified": 0,

        "deleted": 0,

        "renamed": 0,

    }

    for file in files:

        status = file["status"]

        stats.setdefault(status, 0)

        stats[status] += 1

    return stats


# ------------------------------------------------------------
# Metadata Renderer
# ------------------------------------------------------------

def render_header(
    metadata: ContextMetadata,
    files,
):

    stats = build_statistics(files)

    lines = []

    lines.append(
        "# Pull Request Documentation"
    )

    lines.append("")

    lines.append(
        f"Generated : "
        f"{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}"
    )

    lines.append("")

    lines.append(
        "## Branch Information"
    )

    lines.append("")

    lines.append(
        f"- Source : `{metadata.source_branch}`"
    )

    lines.append(
        f"- Target : `{metadata.target_branch}`"
    )

    lines.append("")

    lines.append(
        "## File Summary"
    )

    lines.append("")

    lines.append(
        f"- Total Files : {len(files)}"
    )

    lines.append(
        f"- Added : {stats['added']}"
    )

    lines.append(
        f"- Modified : {stats['modified']}"
    )

    lines.append(
        f"- Deleted : {stats['deleted']}"
    )

    lines.append(
        f"- Renamed : {stats['renamed']}"
    )

    lines.append("")

    return "\n".join(lines)

# ------------------------------------------------------------
# Changed File Renderer
# ------------------------------------------------------------

def render_changed_files(files):

    lines = []

    lines.append("## Changed Files")
    lines.append("")

    for file in files:

        lines.append(f"### `{file['path']}`")
        lines.append("")
        lines.append(f"- Status : **{file['status']}**")

        additions = file["diff"].count("\n+")

        deletions = file["diff"].count("\n-")

        lines.append(f"- Added Lines : {additions}")
        lines.append(f"- Deleted Lines : {deletions}")
        lines.append("")

    return "\n".join(lines)


# ------------------------------------------------------------
# Intermediate Summary Renderer
# ------------------------------------------------------------

def render_intermediate_summaries(
    summaries: List[Summary],
):

    lines = []

    lines.append("## AI Chunk Summaries")
    lines.append("")

    for summary in summaries:

        lines.append(
            f"### Chunk {summary.chunk_id}"
        )

        lines.append("")

        lines.append(summary.text)

        lines.append("")

    return "\n".join(lines)


# ------------------------------------------------------------
# Build Final Prompt
# ------------------------------------------------------------

def build_final_prompt(
    metadata: ContextMetadata,
    summaries: List[Summary],
):

    prompt = []

    prompt.append(
        "You are an expert software architect."
    )

    prompt.append("")

    prompt.append(
        "Create professional pull request documentation."
    )

    prompt.append("")

    prompt.append(
        f"Source Branch : {metadata.source_branch}"
    )

    prompt.append(
        f"Target Branch : {metadata.target_branch}"
    )

    prompt.append("")

    prompt.append(
        "Below are AI generated summaries for every chunk."
    )

    prompt.append("")

    for summary in summaries:

        prompt.append(
            f"Chunk {summary.chunk_id}"
        )

        prompt.append(summary.text)

        prompt.append("")

    return "\n".join(prompt)


# ------------------------------------------------------------
# Local Final Documentation
# ------------------------------------------------------------

def build_local_document(
    metadata,
    files,
    summaries,
):

    document = []

    document.append(
        render_header(
            metadata,
            files,
        )
    )

    document.append("")

    document.append(
        render_changed_files(
            files,
        )
    )

    document.append("")

    document.append(
        render_intermediate_summaries(
            summaries,
        )
    )

    return "\n".join(document)


# ------------------------------------------------------------
# AI Final Documentation
# ------------------------------------------------------------

def build_ai_document(
    metadata,
    summaries,
):

    prompt = build_final_prompt(
        metadata,
        summaries,
    )

    return generate_final_document(
        prompt
    )


# ------------------------------------------------------------
# Markdown Generator
# ------------------------------------------------------------

def generate_markdown(
    metadata,
    files,
    summaries,
    use_gemini,
):

    if use_gemini:

        print()

        print(
            "Generating Final Documentation..."
        )

        return build_ai_document(
            metadata,
            summaries,
        )

    return build_local_document(
        metadata,
        files,
        summaries,
    )

# ------------------------------------------------------------
# Save Output
# ------------------------------------------------------------

def save_document(
    output_path: Path,
    markdown: str,
):

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_path.write_text(
        markdown,
        encoding="utf-8",
    )

    print()
    print("=" * 70)
    print(f"Documentation written to {output_path}")
    print("=" * 70)


# ------------------------------------------------------------
# Main
# ------------------------------------------------------------

def main(argv=None):

    parser = build_parser()

    args = parser.parse_args(argv)

    print("=" * 70)
    print("Loading Context...")
    print("=" * 70)

    metadata, files, summary = load_context(
        args.context
    )

    print()

    print(
        f"Source Branch : {metadata.source_branch}"
    )

    print(
        f"Target Branch : {metadata.target_branch}"
    )

    print(
        f"Changed Files : {summary['total_files']}"
    )

    print()

    summaries = process_chunks(
        metadata=metadata,
        files=files,
        chunk_size=args.chunk_size,
        max_chars=args.max_chars,
        use_gemini=args.use_gemini,
    )

    print()

    print("=" * 70)
    print("Generating Documentation")
    print("=" * 70)

    markdown = generate_markdown(
        metadata,
        files,
        summaries,
        args.use_gemini,
    )

    save_document(
        args.output,
        markdown,
    )

    print()

    print("=" * 70)
    print("Completed Successfully")
    print("=" * 70)

    return 0


# ------------------------------------------------------------
# Entry Point
# ------------------------------------------------------------

if __name__ == "__main__":

    raise SystemExit(main())
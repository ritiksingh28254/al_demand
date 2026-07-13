"""
Chunking utility for AI documentation generation.

Splits changed files into AI-friendly chunks based on
estimated prompt size rather than only file count.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Dict


# ----------------------------------------------------------
# Configuration
# ----------------------------------------------------------

# Safe prompt size for Gemini (characters)
DEFAULT_MAX_CHARS = 35000

# Maximum files allowed in one chunk
DEFAULT_MAX_FILES = 10


# ----------------------------------------------------------
# Models
# ----------------------------------------------------------

@dataclass
class Chunk:

    id: int

    files: List[Dict]

    total_chars: int


# ----------------------------------------------------------
# Size Estimation
# ----------------------------------------------------------

def estimate_size(file: Dict) -> int:
    """
    Estimate prompt size of a file.

    Includes:
        path
        status
        diff
    """

    return (
        len(file["path"])
        + len(file["status"])
        + len(file["diff"])
    )


# ----------------------------------------------------------
# Chunk Builder
# ----------------------------------------------------------

def create_chunks(
    files: List[Dict],
    max_chars: int = DEFAULT_MAX_CHARS,
    max_files: int = DEFAULT_MAX_FILES,
) -> List[Chunk]:

    chunks: List[Chunk] = []

    current_files = []

    current_size = 0

    chunk_id = 1

    for file in files:

        file_size = estimate_size(file)

        exceeds_char_limit = (
            current_size + file_size > max_chars
        )

        exceeds_file_limit = (
            len(current_files) >= max_files
        )

        if current_files and (
            exceeds_char_limit
            or exceeds_file_limit
        ):

            chunks.append(
                Chunk(
                    id=chunk_id,
                    files=current_files,
                    total_chars=current_size,
                )
            )

            chunk_id += 1

            current_files = []

            current_size = 0

        current_files.append(file)

        current_size += file_size

    if current_files:

        chunks.append(
            Chunk(
                id=chunk_id,
                files=current_files,
                total_chars=current_size,
            )
        )

    return chunks


# ----------------------------------------------------------
# Statistics
# ----------------------------------------------------------

def print_chunk_statistics(chunks: List[Chunk]):

    print("\nChunk Summary")
    print("-" * 40)

    total = 0

    for chunk in chunks:

        total += len(chunk.files)

        print(
            f"Chunk {chunk.id:<3}"
            f" Files={len(chunk.files):<3}"
            f" Size={chunk.total_chars}"
        )

    print("-" * 40)

    print(f"Total Files : {total}")

    print(f"Total Chunks: {len(chunks)}")
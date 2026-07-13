from __future__ import annotations

import os
import requests

MAX_DIFF_CHARS = 12_000


def enrich_with_prisma(
    markdown: str,
    git_data: str,
    *,
    source_branch: str,
    target_branch: str,
    is_target_branch_empty: bool,
    api_key: str | None = None,
) -> str:
    """Improve documentation using Prisma AI endpoint."""
    # 1. Grab token from parameter or backend environment variable
    token = api_key or os.getenv("PRISMA_AI_API_KEY")
    if not token:
        print("Prisma API Key missing; bypassing AI enhancement step.")
        return markdown

    truncated_diff = git_data[:MAX_DIFF_CHARS]
    if len(git_data) > MAX_DIFF_CHARS:
        truncated_diff += "\n... [diff truncated]"

    mode = "initial empty repository setup" if is_target_branch_empty else "standard merge"

    # 2. Re-map prompt context tracking
    prompt = f"""Improve the markdown documentation below for a {mode} from `{source_branch}` into `{target_branch}`.
Keep structural elements exactly matching. Do not invent non-existent files.

CURRENT DOCUMENTATION:
{markdown}

RAW GIT DATA:
{truncated_diff}
"""

    # 3. Formulate the standard JSON request block targeting the Prisma AI server
    # Note: Endpoint URI layouts vary based on private enterprise configurations
    url = "https://api.prisma.ai/v1/chat/completions"  
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": "prisma-doc-expert-v1",  # Replace with target infrastructure model identifier
        "messages": [
            {"role": "system", "content": "You are an automated code documentation platform."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.2
    }

    try:
        response = requests.post(url, json=payload, headers=headers, timeout=60)
        response.raise_for_status()
        
        result_json = response.json()
        # Parse output string based on returning object architecture layout
        improved_text = result_json["choices"][0]["message"]["content"].strip()
        
        return improved_text if improved_text else markdown
    except Exception as exc:
        print(f"Prisma AI enrichment pipeline exception: {exc}")
        return markdown
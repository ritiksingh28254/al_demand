"""Optional Gemini-powered enrichment for generated documentation."""

from __future__ import annotations

import os

MAX_DIFF_CHARS = 12_000


def enrich_with_gemini(
    markdown: str,
    git_data: str,
    *,
    source_branch: str,
    target_branch: str,
    is_target_branch_empty: bool,
    api_key: str | None = None,
    model_name: str = "gemini-1.5-flash",
) -> str:
    """Improve documentation using Gemini. Returns original markdown on failure."""
    key = api_key or os.getenv("GEMINI_API_KEY")
    if not key:
        return markdown

    try:
        import google.generativeai as genai
    except ImportError:
        print("google-generativeai not installed; skipping Gemini enrichment.")
        return markdown

    truncated_diff = git_data[:MAX_DIFF_CHARS]
    if len(git_data) > MAX_DIFF_CHARS:
        truncated_diff += "\n... [diff truncated]"

    mode = "initial empty repository setup" if is_target_branch_empty else "standard merge"

    prompt = f"""You are a senior technical writer documenting GitHub merge changes.

Improve the markdown documentation below for a {mode} from `{source_branch}` into `{target_branch}`.

Rules:
- Keep the same markdown structure and all file paths exactly as listed.
- Do not invent files that are not in the documentation or diff.
- Improve the summary and per-file purpose descriptions to be clear and specific.
- For merge mode, briefly explain the business or technical impact of key changes.
- For empty-repo mode, emphasize that this is the initial base setup.
- Return only the improved markdown, no code fences around the full document.

CURRENT DOCUMENTATION:
{markdown}

RAW GIT DATA:
{truncated_diff}
"""

    try:
        genai.configure(api_key=key)
        model = genai.GenerativeModel(model_name)
        response = model.generate_content(prompt)
        text = (response.text or "").strip()
        if text.startswith("```"):
            lines = text.splitlines()
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            text = "\n".join(lines).strip()
        return text or markdown
    except Exception as exc:
        print(f"Gemini enrichment failed: {exc}")
        return markdown

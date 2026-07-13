"""
Gemini AI Enricher V2

This module provides two public APIs:

1. summarize_chunk()
2. generate_final_document()

It works with generate_documentation1.py
"""

from __future__ import annotations

import json
import os
import time
from typing import Any

from google import genai
from google.genai import types

# ---------------------------------------------------------
# Configuration
# ---------------------------------------------------------

DEFAULT_MODEL = "gemini-2.5-flash"

MAX_RETRIES = 3

TEMPERATURE = 0.2

TOP_P = 0.9

MAX_OUTPUT_TOKENS = 4096


# ---------------------------------------------------------
# Client
# ---------------------------------------------------------

_client = None


def get_client():

    global _client

    if _client is not None:
        return _client

    api_key = os.getenv("GEMINI_API_KEY")

    if not api_key:
        raise RuntimeError(
            "GEMINI_API_KEY environment variable not found."
        )

    _client = genai.Client(
        api_key=api_key
    )

    return _client


# ---------------------------------------------------------
# Retry Wrapper
# ---------------------------------------------------------

def generate_text(
    prompt: str,
    model: str = DEFAULT_MODEL,
):

    client = get_client()

    last_exception = None

    for attempt in range(
        1,
        MAX_RETRIES + 1,
    ):

        try:

            response = client.models.generate_content(

                model=model,

                contents=prompt,

                config=types.GenerateContentConfig(

                    temperature=TEMPERATURE,

                    top_p=TOP_P,

                    max_output_tokens=MAX_OUTPUT_TOKENS,

                ),

            )

            return response.text

        except Exception as ex:

            last_exception = ex

            print(
                f"Gemini Retry {attempt}/{MAX_RETRIES}"
            )

            time.sleep(attempt * 2)

    raise RuntimeError(last_exception)


# ---------------------------------------------------------
# Prompt Helpers
# ---------------------------------------------------------

def build_file_section(file):

    lines = []

    lines.append(
        f"File : {file['path']}"
    )

    lines.append(
        f"Status : {file['status']}"
    )

    lines.append("")

    lines.append(file["diff"])

    lines.append("")

    return "\n".join(lines)


def build_chunk_prompt(
    metadata,
    chunk,
):

    sections = []

    sections.append(
        "You are a Senior Software Architect."
    )

    sections.append("")

    sections.append(
        "Analyze the following git changes."
    )

    sections.append(
        "Return a concise JSON summary."
    )

    sections.append("")

    sections.append(
        f"Source Branch : {metadata.source_branch}"
    )

    sections.append(
        f"Target Branch : {metadata.target_branch}"
    )

    sections.append("")

    for file in chunk.files:

        sections.append(
            build_file_section(file)
        )

    return "\n".join(sections)

# ---------------------------------------------------------
# JSON Parser
# ---------------------------------------------------------

def parse_json_response(text: str) -> dict:
    """
    Parse Gemini JSON response.

    Gemini sometimes wraps JSON in markdown
    code fences. This function removes them.
    """

    text = text.strip()

    if text.startswith("```json"):
        text = text.replace("```json", "", 1)

    if text.startswith("```"):
        text = text.replace("```", "", 1)

    if text.endswith("```"):
        text = text[:-3]

    text = text.strip()

    try:
        return json.loads(text)

    except Exception:

        return {

            "overview": text,

            "major_changes": [],

            "risks": [],

            "recommendations": []

        }


# ---------------------------------------------------------
# Validate Response
# ---------------------------------------------------------

def validate_summary(summary: dict):

    summary.setdefault("overview", "")

    summary.setdefault("major_changes", [])

    summary.setdefault("risks", [])

    summary.setdefault("recommendations", [])

    return summary


# ---------------------------------------------------------
# Summarize Chunk
# ---------------------------------------------------------

def summarize_chunk(
    metadata,
    chunk,
):
    """
    Summarize one chunk using Gemini.

    Returns markdown text.
    """

    prompt = build_chunk_prompt(
        metadata,
        chunk,
    )

    prompt += """

Return ONLY valid JSON.

Example:

{
  "overview":"...",
  "major_changes":[
      "...",
      "..."
  ],
  "risks":[
      "..."
  ],
  "recommendations":[
      "..."
  ]
}

Do not return markdown.
Do not wrap inside ```json.
"""

    response = generate_text(
        prompt,
    )

    parsed = parse_json_response(
        response,
    )

    parsed = validate_summary(
        parsed,
    )

    markdown = []

    markdown.append(
        f"### Overview\n\n{parsed['overview']}"
    )

    markdown.append("")

    if parsed["major_changes"]:

        markdown.append(
            "### Major Changes"
        )

        markdown.append("")

        for item in parsed["major_changes"]:

            markdown.append(
                f"- {item}"
            )

        markdown.append("")

    if parsed["risks"]:

        markdown.append(
            "### Risks"
        )

        markdown.append("")

        for item in parsed["risks"]:

            markdown.append(
                f"- {item}"
            )

        markdown.append("")

    if parsed["recommendations"]:

        markdown.append(
            "### Recommendations"
        )

        markdown.append("")

        for item in parsed["recommendations"]:

            markdown.append(
                f"- {item}"
            )

        markdown.append("")

    return "\n".join(markdown)


# ---------------------------------------------------------
# Final Prompt Builder
# ---------------------------------------------------------

def build_final_prompt(
    summaries,
):

    prompt = []

    prompt.append(
        "You are a Principal Software Architect."
    )

    prompt.append("")

    prompt.append(
        "You are given summaries of multiple chunks from a Git Pull Request."
    )

    prompt.append(
        "Create a professional DOCUMENTATION.md."
    )

    prompt.append("")

    prompt.append("The document should contain:")

    prompt.append("- Executive Summary")

    prompt.append("- Key Changes")

    prompt.append("- Technical Details")

    prompt.append("- Risks")

    prompt.append("- Recommendations")

    prompt.append("- Testing Suggestions")

    prompt.append("- Deployment Notes")

    prompt.append("")

    prompt.append(
        "Below are the chunk summaries."
    )

    prompt.append("")

    for index, summary in enumerate(
        summaries,
        start=1,
    ):

        prompt.append(
            f"## Chunk {index}"
        )

        prompt.append(summary.text)

        prompt.append("")

    prompt.append(
        "Generate only Markdown."
    )

    return "\n".join(prompt)


# ---------------------------------------------------------
# Local Documentation
# ---------------------------------------------------------

def generate_local_document(
    summaries,
):

    lines = []

    lines.append("# Pull Request Documentation")

    lines.append("")

    lines.append(
        "## Chunk Summaries"
    )

    lines.append("")

    for summary in summaries:

        lines.append(
            f"### Chunk {summary.chunk_id}"
        )

        lines.append("")

        lines.append(summary.text)

        lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------
# Final Gemini Call
# ---------------------------------------------------------

def generate_final_document(
    prompt: str,
):

    print()

    print("=" * 60)

    print("Generating Final Documentation with Gemini")

    print("=" * 60)

    response = generate_text(
        prompt,
    )

    return response


# ---------------------------------------------------------
# Alternative Entry
# ---------------------------------------------------------

def generate_document_from_summaries(
    summaries,
    use_gemini=True,
):

    if not use_gemini:

        return generate_local_document(
            summaries,
        )

    prompt = build_final_prompt(
        summaries,
    )

    return generate_final_document(
        prompt,
    )


# ---------------------------------------------------------
# Health Check
# ---------------------------------------------------------

def health_check():

    try:

        client = get_client()

        print(
            "Gemini client initialized successfully."
        )

        return True

    except Exception as ex:

        print(
            f"Gemini initialization failed: {ex}"
        )

        return False


# ---------------------------------------------------------
# Manual Testing
# ---------------------------------------------------------

if __name__ == "__main__":

    if health_check():

        print("Ready.")

    else:

        print("Configuration Error.")
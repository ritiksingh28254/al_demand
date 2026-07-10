# Github Demand — PR Documentation Generator

Automates creation of `DOCUMENTATION.md` from GitHub Pull/Merge Request metadata and git diff data.

## Features

- **MODE A (Standard Merge):** Documents added, modified, and deleted files with line-level diff breakdowns.
- **MODE B (Empty Target / First Commit):** Declares the initial repository base and lists every introduced file with its technical purpose.
- **Gemini enrichment (optional):** Improves summaries and file descriptions when `GEMINI_API_KEY` is set.
- **GitHub Action:** Auto-generates and commits `DOCUMENTATION.md` when a PR is merged.

## Quick Start

```bash
python src/generate_documentation.py --context samples/context.initial.json
```

Generate merge-mode documentation from the **actual git diff** (not the static sample):

```bash
python scripts/build_merge_context.py --source-branch main --target-branch bc218f0 --output context.json
python src/generate_documentation.py --context context.json --output DOCUMENTATION.md
```

For CI-style runs with explicit SHAs (same inputs as the GitHub Action):

```bash
python scripts/build_merge_context.py \
  --source-branch feat/test \
  --target-branch main \
  --base-sha <target-branch-sha-before-merge> \
  --merge-sha <merge-commit-sha> \
  --output context.json
python src/generate_documentation.py --context context.json --output DOCUMENTATION.md
```

The sample file `samples/context.merge.json` points at `samples/git_diff.sample`, which is only a demo payload. Use `build_merge_context.py` when you want documentation that reflects real branch changes (for example a new `readme1.py` file).

## Context File Format

```json
{
  "source_branch": "feature/my-branch",
  "target_branch": "main",
  "is_target_branch_empty": false,
  "git_data": "diff --git a/README.md b/README.md\n..."
}
```

Alternatively, reference an external diff file:

```json
{
  "source_branch": "feature/my-branch",
  "target_branch": "main",
  "is_target_branch_empty": false,
  "git_data_file": "samples/git_diff.sample"
}
```

## Gemini Enrichment

```bash
pip install -r requirements.txt
set GEMINI_API_KEY=your_key_here
python src/generate_documentation.py --context samples/context.merge.json --use-gemini
```

## GitHub Automation

1. Push this repo to GitHub.
2. Add repository secret: `GEMINI_API_KEY` (optional).
3. Merge a pull request — workflow `.github/workflows/generate-docs.yml` runs automatically.
4. `DOCUMENTATION.md` is updated and committed to the target branch.

## Project Layout

| Path | Description |
|------|-------------|
| `src/generate_documentation.py` | Core generator script |
| `src/gemini_enricher.py` | Optional Gemini post-processing |
| `scripts/build_merge_context.py` | Builds context JSON from git merge metadata (CI) |
| `.github/workflows/generate-docs.yml` | Runs on merged PRs |
| `samples/` | Example context payloads and sample git diffs |
| `DOCUMENTATION.md` | Generated documentation output |

## Requirements

- Python 3.10+
- `google-generativeai` (optional, for Gemini enrichment)

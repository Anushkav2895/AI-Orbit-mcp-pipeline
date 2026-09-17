# AI Orbit — MCP Module Ingestion Pipeline

Extracts, cleans, and prepares a dataset of real MCP (Model Context Protocol)
servers for the AI Orbit ecosystem sheet, following the workflow:

Extract → Clean → Official URL/Logo Verification → LLM Descriptions → CSV for Google Sheets

## Setup

```bash
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

No API keys are required to run this. Optional: set `GITHUB_TOKEN` (a free
GitHub personal access token, no special scopes) to raise the GitHub Search
API rate limit from 10 req/min to 30 req/min.

## Run

```bash
python run.py
```

This runs extraction (GitHub + Smithery) → cleaning/dedup → draft
descriptions, and tells you the one manual step left (polishing
descriptions) before the final CSV export.

Run stages individually if you want to iterate on one step:

```bash
python src/extract_github.py
python src/extract_smithery.py
python src/clean.py
python src/draft_descriptions.py
python src/export_sheet.py
```

## Architecture

- **`src/extract_github.py`** — Primary source. Queries GitHub's public
  Search API (no auth required) for repos tagged/described as MCP servers.
  Self-paces to respect the unauthenticated rate limit (10/min, 60/hr) with
  exponential backoff on 403/429.
- **`src/extract_smithery.py`** — Secondary source. Smithery has no
  documented public JSON API, so this lightly scrapes the public,
  logged-out `/servers` directory pages for additional listings GitHub
  search alone might miss.
- **`src/clean.py`** — Merges both sources, deduplicates by normalized
  name (case/punctuation/"mcp" suffix insensitive), and resolves each
  record's **official URL** (the GitHub repo itself — MCP servers rarely
  have a separate marketing site) and **official logo** (the GitHub
  owner's avatar, fetched live for records that only came from Smithery).
  Never fabricates a URL or logo that isn't traceable to a real source.
- **`src/draft_descriptions.py`** — Produces a normalized draft
  description per record from the repo's own description/README, with no
  LLM key needed. These are meant to be polished into final,
  submission-ready descriptions as a manual or LLM-assisted pass (see
  "Descriptions" below) — the brief specifically calls for LLM-generated
  descriptions, and draft text alone isn't a substitute.
- **`src/export_sheet.py`** — Flattens the final records into
  `data/mcp_module_final.csv`, matching the common entity schema plus
  MCP-specific fields (stars, language, last updated), ready for Google
  Sheets import.

## Descriptions (LLM step)

No LLM API key is wired in by default. To finish this step:
1. Run the pipeline through `draft_descriptions.py`.
2. Take `data/described_mcp.json` and have an LLM rewrite each
   `draft_description` into a clean, consistent, non-duplicative
   description per the brief's requirements.
3. Save the result as `data/final_mcp.json` with each record's finished
   text in a `description_final` field (or overwrite `draft_description`
   in place).
4. Run `python src/export_sheet.py` — it prefers `final_mcp.json` over
   `described_mcp.json` automatically.

If you get a free-tier key (Groq or Gemini both offer one with no card
required), you can instead call it directly inside `draft_descriptions.py`
per record and skip the manual step entirely.

## Data quality notes

- Every record traces back to a real, live source URL (GitHub repo or
  Smithery listing) — no fabricated/hallucinated entries.
- Dedup is name-based; for a stricter pass at scale, also compare
  normalized `official_url` values.
- `stars` / `primary_language` / `last_updated` are only populated for
  GitHub-sourced records; Smithery-only records will have these blank
  unless you extend `extract_smithery.py` to visit each server's detail
  page (slower, but more complete).

"""
draft_descriptions.py
----------------------
Generates a DRAFT description for every record from what we already
scraped (repo description / README opener), with no LLM API key needed.

This is meant as input to a final polishing pass -- either:
  (a) paste data/clean_mcp.json into a chat with an LLM and ask it to
      rewrite each `draft_description` into a clean, consistent-format
      description (this is what's expected by the brief), or
  (b) if you get a free-tier key later (Groq and Gemini both have free
      tiers with no card required), swap in a real API call here.

Output: data/described_mcp.json (adds a `draft_description` field)
"""

import json
import os
import re

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")


def clean_text(text):
    text = re.sub(r"\s+", " ", text or "").strip()
    return text


def draft_description(record):
    name = record.get("name", "this project")
    raw = clean_text(record.get("description", ""))
    lang = record.get("primary_language")

    if raw:
        # Use the repo's own description as the base, normalized into a
        # consistent sentence shape.
        base = raw.rstrip(".")
        desc = f"{name} is an MCP server that {base[0].lower() + base[1:] if base else 'provides tools via the Model Context Protocol'}."
    else:
        desc = f"{name} is an MCP (Model Context Protocol) server"
        if lang:
            desc += f" implemented in {lang}"
        desc += ", exposing tools/resources to MCP-compatible AI clients."

    return desc


def main():
    path = os.path.join(DATA_DIR, "clean_mcp.json")
    with open(path) as f:
        records = json.load(f)

    for r in records:
        r["draft_description"] = draft_description(r)

    out_path = os.path.join(DATA_DIR, "described_mcp.json")
    with open(out_path, "w") as f:
        json.dump(records, f, indent=2)
    print(f"Saved {len(records)} records with draft descriptions to {out_path}")
    print("Next: get these polished into final descriptions (paste into an LLM chat,")
    print("or run through a free-tier LLM API) before exporting to the sheet.")


if __name__ == "__main__":
    main()

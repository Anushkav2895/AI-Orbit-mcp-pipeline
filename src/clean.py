"""
clean.py
--------
Merges data/raw_github.json + data/raw_smithery.json, deduplicates,
normalizes names, and resolves an "official" URL + logo per record.

Rule of thumb for MCP servers: the GitHub repo IS the official source
(there's rarely a separate marketing site), so:
  - official url  -> the GitHub repo URL
  - official logo -> the GitHub owner's avatar_url (org/user avatar),
                      fetched live for Smithery-only records that don't
                      already have one.

Output: data/clean_mcp.json
"""

import json
import os
import re
import time

import requests

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
GITHUB_API = "https://api.github.com/repos/"


def load(name):
    path = os.path.join(DATA_DIR, name)
    if not os.path.exists(path):
        return []
    with open(path) as f:
        return json.load(f)


def normalize_name(name):
    """Canonical key for dedup: lowercase, strip punctuation/mcp-suffixes."""
    n = name.lower().strip()
    n = re.sub(r"\bmcp\b", "", n)
    n = re.sub(r"[-_./]", " ", n)
    n = re.sub(r"\s+", " ", n).strip()
    return n


def extract_owner_repo_from_url(url):
    m = re.match(r"https?://github\.com/([^/]+)/([^/]+)/?$", url or "")
    if not m:
        return None, None
    return m.group(1), m.group(2)


def fetch_github_avatar(owner):
    """Best-effort lookup of a GitHub owner's avatar for records that
    came from Smithery and don't already have one. Skips gracefully on
    any failure -- never invents a logo URL."""
    try:
        resp = requests.get(f"https://api.github.com/users/{owner}", timeout=15)
        if resp.status_code == 200:
            return resp.json().get("avatar_url")
    except requests.RequestException:
        pass
    return None


def resolve_official(record):
    """Fill in official url/logo. Never fabricates a URL that wasn't
    present in source data or derivable from it."""
    url = record.get("url", "")
    owner, repo = extract_owner_repo_from_url(url)

    if owner:
        record["source"] = {"name": "GitHub", "url": url}
        if not record.get("owner_avatar_url"):
            record["owner_avatar_url"] = fetch_github_avatar(owner)
            time.sleep(1)
    # If it's a Smithery-only record with no GitHub link, we leave the
    # Smithery URL as-is (still a legitimate, traceable source) rather
    # than guessing at an unverified "official site."
    record["official_url"] = url
    record["logo_url"] = record.get("owner_avatar_url")
    return record


def dedupe(records):
    by_key = {}
    for r in records:
        if not r.get("name"):
            continue
        key = normalize_name(r["name"])
        existing = by_key.get(key)
        if existing is None:
            by_key[key] = r
            continue
        # Prefer the record with more/better metadata (has stars/GitHub data)
        if (r.get("stars") or 0) > (existing.get("stars") or 0):
            by_key[key] = r
    return list(by_key.values())


def main():
    github_records = load("raw_github.json")
    smithery_records = load("raw_smithery.json")
    print(f"Loaded {len(github_records)} GitHub records, {len(smithery_records)} Smithery records")

    merged = dedupe(github_records + smithery_records)
    print(f"After dedup: {len(merged)} unique MCP records")

    cleaned = []
    for i, r in enumerate(merged, start=1):
        r["id"] = f"mcp-{i:05d}"
        r = resolve_official(r)
        cleaned.append(r)

    out_path = os.path.join(DATA_DIR, "clean_mcp.json")
    with open(out_path, "w") as f:
        json.dump(cleaned, f, indent=2)
    print(f"Saved {len(cleaned)} cleaned records to {out_path}")


if __name__ == "__main__":
    main()

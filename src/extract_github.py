"""
extract_github.py
------------------
Pulls MCP (Model Context Protocol) server repos from GitHub's public
Search API. Works with NO token, but unauthenticated search requests
are limited to 10/minute and 60/hour total — this script paces itself
to respect that automatically.

If you later get a free GitHub personal access token (Settings > Developer
settings > Personal access tokens > generate one, no special scopes needed
for public repo search), set it as an env var and the script will use it
automatically for a much higher rate limit (30/min, 5000/hour):

    export GITHUB_TOKEN=ghp_xxx

Output: data/raw_github.json
"""

import json
import os
import time
from datetime import datetime, timezone

import requests

API_ROOT = "https://api.github.com"
TOKEN = os.environ.get("GITHUB_TOKEN")

HEADERS = {"Accept": "application/vnd.github+json"}
if TOKEN:
    HEADERS["Authorization"] = f"Bearer {TOKEN}"

# Search queries designed to surface real MCP servers, not just anything
# that mentions "MCP" in passing.
SEARCH_QUERIES = [
    "topic:mcp-server",
    "topic:model-context-protocol",
    "\"mcp server\" in:name,description",
    "\"model context protocol\" server in:description",
    "org:modelcontextprotocol",
]

PER_PAGE = 100  # GitHub max
MAX_PAGES_PER_QUERY = 10  # GitHub search caps at 1000 results (10 pages x 100)


def _request_with_backoff(url, params):
    """GET with exponential backoff on 403/429 (rate limit)."""
    delay = 5
    for attempt in range(6):
        resp = requests.get(url, headers=HEADERS, params=params, timeout=30)
        if resp.status_code == 200:
            return resp
        if resp.status_code in (403, 429):
            reset = resp.headers.get("X-RateLimit-Reset")
            if reset:
                wait = max(int(reset) - int(time.time()) + 2, delay)
            else:
                wait = delay
            print(f"  rate limited (status {resp.status_code}), sleeping {wait}s...")
            time.sleep(wait)
            delay = min(delay * 2, 120)
            continue
        # Other errors: log and bail on this page
        print(f"  unexpected status {resp.status_code}: {resp.text[:200]}")
        return None
    return None


def search_repos(query):
    """Yield repo dicts for a single search query, paginated."""
    for page in range(1, MAX_PAGES_PER_QUERY + 1):
        params = {
            "q": query,
            "per_page": PER_PAGE,
            "page": page,
            "sort": "stars",
            "order": "desc",
        }
        resp = _request_with_backoff(f"{API_ROOT}/search/repositories", params)
        if resp is None:
            break
        payload = resp.json()
        items = payload.get("items", [])
        if not items:
            break
        for item in items:
            yield item
        # Pace ourselves: unauth = 10/min -> ~6s between calls is safe
        time.sleep(6 if not TOKEN else 2)
        if len(items) < PER_PAGE:
            break


def normalize(repo):
    owner = repo.get("owner", {}) or {}
    return {
        "id": None,  # filled in during clean/dedupe step
        "entity_type": "MCP",
        "name": repo.get("name"),
        "description": repo.get("description") or "",
        "url": repo.get("html_url"),
        "categories": ["MCP", "Developer Tools"],
        "source": {"name": "GitHub", "url": repo.get("html_url")},
        # MCP-specific metadata
        "stars": repo.get("stargazers_count", 0),
        "primary_language": repo.get("language"),
        "last_updated": repo.get("pushed_at"),
        "owner_login": owner.get("login"),
        "owner_avatar_url": owner.get("avatar_url"),  # candidate official logo
        "topics": repo.get("topics", []),
        "collected_at": datetime.now(timezone.utc).isoformat(),
    }


def main():
    seen_urls = set()
    results = []

    for q in SEARCH_QUERIES:
        print(f"Searching: {q}")
        count_before = len(results)
        for repo in search_repos(q):
            url = repo.get("html_url")
            if not url or url in seen_urls:
                continue
            seen_urls.add(url)
            results.append(normalize(repo))
        print(f"  -> {len(results) - count_before} new repos (total so far: {len(results)})")

    out_path = os.path.join(os.path.dirname(__file__), "..", "data", "raw_github.json")
    with open(out_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nSaved {len(results)} raw MCP records to {out_path}")


if __name__ == "__main__":
    main()

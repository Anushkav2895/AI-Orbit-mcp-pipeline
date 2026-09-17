"""
extract_smithery.py
--------------------
Secondary source: smithery.ai's public server directory pages
(https://smithery.ai/servers, https://smithery.ai/server/<qualifiedName>).

Smithery does not publish a documented, unauthenticated JSON API, so this
scrapes the public listing pages instead (same content a logged-out visitor
sees in a browser). This is intentionally simple and defensive: if
Smithery's markup changes, it should fail loudly rather than silently
returning garbage.

Output: data/raw_smithery.json

NOTE: If Smithery's page structure has changed since this was written,
inspect one page manually (view-source or browser devtools) and update
the CSS selectors / extraction logic below accordingly -- don't guess.
"""

import json
import os
import time
from datetime import datetime, timezone

import requests
from bs4 import BeautifulSoup

BASE = "https://smithery.ai"
LISTING_URL = f"{BASE}/servers"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; AI-Orbit-ResearchBot/1.0)"
}


def fetch_listing_page(page=1, query=None):
    params = {"page": page}
    if query:
        params["q"] = query
    resp = requests.get(LISTING_URL, headers=HEADERS, params=params, timeout=30)
    resp.raise_for_status()
    return resp.text


def parse_listing(html):
    """Extract server cards from a listing page.

    Smithery's server cards link to /server/<qualifiedName>. We extract
    what's available in the card itself (name, short description, link);
    deeper metadata would require visiting each server's page, which is
    slow at scale -- do that only for the subset you keep after dedup.
    """
    soup = BeautifulSoup(html, "html.parser")
    cards = []
    for a in soup.select('a[href^="/server/"]'):
        href = a.get("href", "")
        if not href or href.count("/") < 2:
            continue
        name_el = a.select_one("h3, h2, [class*=title]")
        desc_el = a.select_one("p, [class*=description]")
        name = (name_el.get_text(strip=True) if name_el else a.get_text(strip=True))
        if not name:
            continue
        cards.append({
            "qualified_name": href.replace("/server/", "").strip("/"),
            "name": name,
            "description": desc_el.get_text(strip=True) if desc_el else "",
            "url": BASE + href,
        })
    return cards


def normalize(card):
    return {
        "id": None,
        "entity_type": "MCP",
        "name": card["name"],
        "description": card.get("description", ""),
        "url": card["url"],
        "categories": ["MCP", "Developer Tools"],
        "source": {"name": "Smithery", "url": card["url"]},
        "stars": None,
        "primary_language": None,
        "last_updated": None,
        "owner_login": None,
        "owner_avatar_url": None,
        "topics": [],
        "collected_at": datetime.now(timezone.utc).isoformat(),
    }


def main(max_pages=20):
    seen = set()
    results = []
    for page in range(1, max_pages + 1):
        print(f"Fetching Smithery listing page {page}...")
        try:
            html = fetch_listing_page(page=page)
        except requests.HTTPError as e:
            print(f"  stopped: {e}")
            break
        cards = parse_listing(html)
        if not cards:
            print("  no more cards found, stopping.")
            break
        new = 0
        for c in cards:
            if c["url"] in seen:
                continue
            seen.add(c["url"])
            results.append(normalize(c))
            new += 1
        print(f"  -> {new} new servers (total: {len(results)})")
        time.sleep(2)  # be polite

    out_path = os.path.join(os.path.dirname(__file__), "..", "data", "raw_smithery.json")
    with open(out_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nSaved {len(results)} raw Smithery records to {out_path}")


if __name__ == "__main__":
    main()

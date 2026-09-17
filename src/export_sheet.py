"""
export_sheet.py
----------------
Exports the final dataset to a CSV you can import straight into Google
Sheets (File > Import > Upload, or paste a File > Import from URL if you
host the CSV somewhere public).

Reads data/final_mcp.json if present (i.e. after you've swapped in polished
descriptions), otherwise falls back to data/described_mcp.json with the
draft descriptions.

Output: data/mcp_module_final.csv
"""

import csv
import json
import os

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")

COLUMNS = [
    "id", "entity_type", "name", "description", "official_url", "logo_url",
    "categories", "source_name", "source_url", "stars", "primary_language",
    "last_updated", "topics", "collected_at",
]


def load_final():
    final_path = os.path.join(DATA_DIR, "final_mcp.json")
    described_path = os.path.join(DATA_DIR, "described_mcp.json")
    path = final_path if os.path.exists(final_path) else described_path
    with open(path) as f:
        return json.load(f), path


def row_for(record):
    desc = record.get("description_final") or record.get("draft_description") or record.get("description", "")
    return {
        "id": record.get("id"),
        "entity_type": record.get("entity_type", "MCP"),
        "name": record.get("name"),
        "description": desc,
        "official_url": record.get("official_url") or record.get("url"),
        "logo_url": record.get("logo_url") or "",
        "categories": "; ".join(record.get("categories", [])),
        "source_name": (record.get("source") or {}).get("name", ""),
        "source_url": (record.get("source") or {}).get("url", ""),
        "stars": record.get("stars") if record.get("stars") is not None else "",
        "primary_language": record.get("primary_language") or "",
        "last_updated": record.get("last_updated") or "",
        "topics": "; ".join(record.get("topics", []) or []),
        "collected_at": record.get("collected_at", ""),
    }


def main():
    records, used_path = load_final()
    print(f"Loaded {len(records)} records from {used_path}")

    out_path = os.path.join(DATA_DIR, "mcp_module_final.csv")
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS)
        writer.writeheader()
        for r in records:
            writer.writerow(row_for(r))

    print(f"Wrote {len(records)} rows to {out_path}")
    print("Import into Google Sheets: File > Import > Upload > select this CSV")
    print("> Import location: 'Insert new sheet'. Then set Share > Anyone with the link > Viewer.")


if __name__ == "__main__":
    main()

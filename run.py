"""
run.py
------
Runs the full MCP module pipeline in order:
  1. extract_github.py    -> data/raw_github.json
  2. extract_smithery.py  -> data/raw_smithery.json
  3. clean.py              -> data/clean_mcp.json
  4. draft_descriptions.py -> data/described_mcp.json
  5. export_sheet.py       -> data/mcp_module_final.csv

Usage:
    python run.py            # run everything
    python run.py --skip-extract   # reuse existing raw_*.json, redo cleaning onward
"""

import subprocess
import sys
import os

SRC = os.path.join(os.path.dirname(__file__), "src")


def run(script):
    print(f"\n=== Running {script} ===")
    result = subprocess.run([sys.executable, os.path.join(SRC, script)])
    if result.returncode != 0:
        print(f"!! {script} exited with an error (code {result.returncode}). Stopping.")
        sys.exit(result.returncode)


def main():
    skip_extract = "--skip-extract" in sys.argv

    if not skip_extract:
        run("extract_github.py")
        run("extract_smithery.py")
    else:
        print("Skipping extraction, reusing existing data/raw_*.json")

    run("clean.py")
    run("draft_descriptions.py")

    print("\n=== Pipeline done through draft descriptions ===")
    print("Next steps (manual, per the brief):")
    print("  1. Open data/described_mcp.json, get draft_description fields")
    print("     polished into final descriptions (paste into an LLM chat).")
    print("  2. Save the polished version as data/final_mcp.json with a")
    print("     'description_final' field per record (or just overwrite")
    print("     draft_description in place).")
    print("  3. Run: python src/export_sheet.py")


if __name__ == "__main__":
    main()

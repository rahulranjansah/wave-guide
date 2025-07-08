#!/usr/bin/env python3
"""
Scan a Mermaid diagrams directory for all .mmd files, collect their contents,
and serialize to a single JSON file for easy upload and downstream processing.

Usage:
    python3 export_mermaid_json.py --input-dir path/to/pulsesuiteX/mermaid \
                                  --output-file all_mermaid.json
"""
import argparse
import json
from pathlib import Path

def parse_args():
    parser = argparse.ArgumentParser(
        description="Collect all .mmd files into a JSON mapping filename → content"
    )
    parser.add_argument(
        "--input-dir", "-i",
        required=True,
        help="Directory containing .mmd files"
    )
    parser.add_argument(
        "--output-file", "-o",
        required=True,
        help="Path to write the combined JSON output"
    )
    return parser.parse_args()


def collect_mermaid_files(input_dir: Path):
    data = {}
    for mmd_file in sorted(input_dir.glob("*.mmd")):
        # Read entire file as string
        content = mmd_file.read_text(encoding="utf-8")
        # Store under the base filename
        data[mmd_file.name] = content
    return data


def main():
    args = parse_args()
    inp = Path(args.input_dir)
    out = Path(args.output_file)

    if not inp.is_dir():
        print(f"Error: input directory '{inp}' does not exist or is not a directory.")
        return

    mermaid_map = collect_mermaid_files(inp)

    # Write JSON
    out.write_text(
        json.dumps(mermaid_map, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )
    print(f"Collected {len(mermaid_map)} .mmd files into {out}")

if __name__ == "__main__":
    main()

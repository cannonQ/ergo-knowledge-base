#!/usr/bin/env python3
"""
Merge Multiple GraphQL JSON Exports
=====================================
When paginating GQL queries in the Playground UI (skip: 0, 200, 400...),
you end up with multiple JSON responses. Copying them all into one file
creates invalid JSON (multiple root objects concatenated).

This script parses concatenated JSON objects and merges all boxes arrays
into a single valid JSON file.

Input:  File with one or more {"data": {"boxes": [...]}} objects
Output: Single valid JSON with all boxes combined

Usage:
  python merge_gql_exports.py input.json output.json
  python merge_gql_exports.py gql_raw.json gql_merged.json

Requirements:
  None (stdlib only)
Author: CannonQ
License: AGPL-3.0
"""

import json
import sys
import os


def merge_gql_json(input_path, output_path):
    """
    Parse multiple concatenated JSON objects from a file,
    extract boxes arrays, and combine into one valid JSON.
    """
    with open(input_path, 'r', encoding='utf-8') as f:
        content = f.read()

    all_boxes = []
    decoder = json.JSONDecoder()
    idx = 0

    objects_found = 0
    while idx < len(content):
        # Skip whitespace
        while idx < len(content) and content[idx] in ' \t\n\r':
            idx += 1
        if idx >= len(content):
            break

        try:
            obj, end_idx = decoder.raw_decode(content, idx)
            idx = end_idx
            objects_found += 1

            # Extract boxes from various response shapes
            boxes = []
            if isinstance(obj, dict):
                if "data" in obj and "boxes" in obj["data"]:
                    boxes = obj["data"]["boxes"]
                elif "boxes" in obj:
                    boxes = obj["boxes"]
                elif "data" in obj:
                    # Check for other data shapes
                    for key, val in obj["data"].items():
                        if isinstance(val, list):
                            boxes = val
                            break

            all_boxes.extend(boxes)
            print(f"  Object {objects_found}: {len(boxes)} boxes")

        except json.JSONDecodeError as e:
            print(f"  Parse error at position {idx}: {e}")
            # Try to skip past the error
            idx += 1

    # Write merged output
    output = {
        "data": {
            "boxes": all_boxes
        }
    }

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2)

    print(f"\nMerged {objects_found} JSON objects -> {len(all_boxes)} total boxes")
    print(f"Saved: {output_path}")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python merge_gql_exports.py <input.json> <output.json>")
        print("\nMerges multiple concatenated GQL JSON responses into one file.")
        print("\nExample:")
        print("  python merge_gql_exports.py gql_search_mewmart.json gql_merged.json")
        sys.exit(1)

    merge_gql_json(sys.argv[1], sys.argv[2])

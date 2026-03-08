#!/usr/bin/env python3
"""Export LanceDB vectors to flat files for serverless deployment.

Produces:
  mcp-server/data/vectors.bin   — raw Float32 buffer (N × 1024 floats)
  mcp-server/data/metadata.json — array of chunk metadata (no vectors)

This eliminates the ~80MB @lancedb/lancedb native binary from the
Vercel bundle while keeping identical search quality.
"""

import json
import struct
import os
import sys

import lancedb

VECTORDB_PATH = os.path.join(os.path.dirname(__file__), "..", "vectordb")
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "mcp-server", "data")
TABLE_NAME = "ekb_chunks"
EMBED_DIM = 1024


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    db = lancedb.connect(VECTORDB_PATH)
    table = db.open_table(TABLE_NAME)
    arrow_table = table.to_arrow()
    num_rows = arrow_table.num_rows

    print(f"Exporting {num_rows} chunks ({EMBED_DIM} dims each)...")

    # Get columns
    vectors_col = arrow_table.column("vector")
    columns = {
        name: arrow_table.column(name)
        for name in arrow_table.column_names
        if name != "vector"
    }

    # Export vectors as raw Float32 binary
    vectors_path = os.path.join(OUTPUT_DIR, "vectors.bin")
    with open(vectors_path, "wb") as f:
        for i in range(num_rows):
            vec = vectors_col[i].as_py()
            f.write(struct.pack(f"{EMBED_DIM}f", *vec))

    vectors_size = os.path.getsize(vectors_path)
    print(f"vectors.bin: {vectors_size / 1024 / 1024:.1f} MB")

    # Export metadata (everything except the vector column)
    metadata = []
    for i in range(num_rows):
        metadata.append({
            "file_path": columns["file_path"][i].as_py(),
            "title": columns["title"][i].as_py(),
            "category": columns["category"][i].as_py(),
            "project": columns["project"][i].as_py() if "project" in columns else "",
            "tags": columns["tags"][i].as_py(),
            "text": columns["text"][i].as_py(),
            "tokens": int(columns["tokens"][i].as_py()),
            "chunk_index": int(columns["chunk_index"][i].as_py()),
        })

    metadata_path = os.path.join(OUTPUT_DIR, "metadata.json")
    with open(metadata_path, "w") as f:
        json.dump(metadata, f, separators=(",", ":"))

    metadata_size = os.path.getsize(metadata_path)
    print(f"metadata.json: {metadata_size / 1024 / 1024:.1f} MB")
    print(f"Total: {(vectors_size + metadata_size) / 1024 / 1024:.1f} MB")
    print(f"Output dir: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()

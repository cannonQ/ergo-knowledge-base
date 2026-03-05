#!/usr/bin/env python3
"""
Generate vector embeddings for all EKB content and store in LanceDB.

Pipeline:
  1. Walk content/ and parse all markdown files
  2. Chunk by headers (H2 boundaries), respecting code blocks
  3. Prepend metadata header to each chunk for context
  4. Embed via BGE-M3 (Ollama) or fallback to sentence-transformers
  5. Upsert to LanceDB with content-hash deduplication

Requirements:
  pip install lancedb ollama
  # OR: pip install lancedb sentence-transformers
  # Ollama: ollama pull bge-m3

Usage:
  python3 scripts/generate_embeddings.py
  python3 scripts/generate_embeddings.py --rebuild          # Drop and recreate table
  python3 scripts/generate_embeddings.py --model sentence   # Use sentence-transformers
  python3 scripts/generate_embeddings.py --include-telegram ~/ergo-telegram/output
"""

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.resolve()
CONTENT_DIR = REPO_ROOT / "content"
DB_DIR = REPO_ROOT / ".lance"
TABLE_NAME = "ekb_chunks"

# Chunking params
TARGET_CHUNK_TOKENS = 768     # ~512-1024 token window
MAX_CHUNK_TOKENS = 1200
OVERLAP_LINES = 3             # lines of overlap between chunks

# Embedding dimensions (BGE-M3 = 1024)
EMBED_DIM = 1024


def estimate_tokens(text: str) -> int:
    return len(text) // 4


def content_hash(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()[:16]


def parse_frontmatter(path: Path) -> dict:
    """Extract YAML frontmatter from a markdown file."""
    try:
        text = path.read_text(errors="ignore")
    except OSError:
        return {}
    if not text.startswith("---"):
        return {}
    end = text.find("\n---", 3)
    if end == -1:
        return {}
    fm_block = text[3:end].strip()
    meta = {}
    for line in fm_block.split("\n"):
        m = re.match(r"^(\w[\w_-]*)\s*:\s*(.+)$", line)
        if m:
            key, val = m.group(1), m.group(2).strip()
            if (val.startswith('"') and val.endswith('"')) or \
               (val.startswith("'") and val.endswith("'")):
                val = val[1:-1]
            if val.startswith("[") and val.endswith("]"):
                val = [v.strip().strip("'\"") for v in val[1:-1].split(",") if v.strip()]
            meta[key] = val
    return meta


def strip_frontmatter(text: str) -> str:
    """Remove YAML frontmatter from markdown text."""
    if not text.startswith("---"):
        return text
    end = text.find("\n---", 3)
    if end == -1:
        return text
    return text[end + 4:].lstrip("\n")


def chunk_by_headers(text: str) -> list[str]:
    """Split markdown into chunks at H2 boundaries, never splitting code blocks.

    Returns a list of text chunks, each starting with its header (if any).
    """
    body = strip_frontmatter(text)
    # Split on H2 headers (## ...)
    parts = re.split(r"(?=^## )", body, flags=re.MULTILINE)
    chunks = []

    for part in parts:
        part = part.strip()
        if not part:
            continue
        tokens = estimate_tokens(part)
        if tokens <= MAX_CHUNK_TOKENS:
            chunks.append(part)
        else:
            # Sub-split on H3 if too large
            sub_parts = re.split(r"(?=^### )", part, flags=re.MULTILINE)
            current = ""
            for sp in sub_parts:
                if estimate_tokens(current + sp) > MAX_CHUNK_TOKENS and current:
                    chunks.append(current.strip())
                    current = sp
                else:
                    current += sp
            if current.strip():
                chunks.append(current.strip())

    return chunks if chunks else [body] if body.strip() else []


def build_chunk_header(fm: dict, rel_path: str) -> str:
    """Build metadata prefix for a chunk to carry context when retrieved in isolation."""
    parts = Path(rel_path).parts
    breadcrumb = " > ".join(parts[:-1]) if len(parts) > 1 else parts[0] if parts else ""
    tags = fm.get("tags", [])
    if isinstance(tags, str):
        tags = [tags]
    tag_str = ", ".join(tags[:8]) if tags else "none"
    category = fm.get("category", "")
    difficulty = fm.get("difficulty", "")
    sdk = fm.get("sdk", ["none"])
    if isinstance(sdk, list):
        sdk = ", ".join(sdk)

    lines = [
        f"# {breadcrumb}",
        f"# Tags: {tag_str}",
    ]
    if category:
        lines.append(f"# Category: {category} | Difficulty: {difficulty}")
    if sdk and sdk != "none":
        lines.append(f"# SDK: {sdk}")
    return "\n".join(lines)


def collect_chunks(content_dir: Path) -> list[dict]:
    """Walk content dir, chunk all docs, return list of chunk dicts."""
    all_chunks = []

    for md_path in sorted(content_dir.rglob("*.md")):
        rel = str(md_path.relative_to(REPO_ROOT))
        fm = parse_frontmatter(md_path)

        try:
            text = md_path.read_text(errors="ignore")
        except OSError:
            continue

        header = build_chunk_header(fm, rel)
        raw_chunks = chunk_by_headers(text)

        title = fm.get("title", Path(rel).stem.replace("-", " ").title())
        tags = fm.get("tags", [])
        if isinstance(tags, str):
            tags = [tags]
        category = fm.get("category", "")
        project = fm.get("project", "")

        for i, chunk_text in enumerate(raw_chunks):
            full_text = f"{header}\n\n{chunk_text}"
            chash = content_hash(full_text)

            all_chunks.append({
                "id": f"{rel}#{i}",
                "content_hash": chash,
                "file_path": rel,
                "chunk_index": i,
                "title": title,
                "category": category,
                "project": project,
                "tags": json.dumps(tags),
                "text": full_text,
                "tokens": estimate_tokens(full_text),
            })

    return all_chunks


def embed_ollama(texts: list[str], model: str = "bge-m3") -> list[list[float]]:
    """Embed texts using Ollama's API."""
    try:
        import ollama
    except ImportError:
        sys.exit("ollama package required: pip install ollama\nAlso: ollama pull bge-m3")

    embeddings = []
    batch_size = 32
    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]
        result = ollama.embed(model=model, input=batch)
        embeddings.extend(result["embeddings"])
        if (i + batch_size) % 100 == 0:
            print(f"  embedded {min(i + batch_size, len(texts))}/{len(texts)}")
    return embeddings


def embed_sentence_transformers(texts: list[str]) -> list[list[float]]:
    """Embed texts using sentence-transformers (fallback)."""
    try:
        from sentence_transformers import SentenceTransformer
    except ImportError:
        sys.exit("sentence-transformers required: pip install sentence-transformers")

    model = SentenceTransformer("BAAI/bge-m3")
    embeddings = model.encode(texts, show_progress_bar=True, batch_size=32)
    return embeddings.tolist()


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate embeddings for EKB content")
    parser.add_argument("--content-dir", default=str(CONTENT_DIR))
    parser.add_argument("--db-dir", default=str(DB_DIR))
    parser.add_argument("--rebuild", action="store_true",
                        help="Drop and recreate the table")
    parser.add_argument("--model", choices=["ollama", "sentence"], default="ollama",
                        help="Embedding backend (default: ollama)")
    parser.add_argument("--include-telegram", default=None,
                        help="Path to Telegram output dir to include summaries")
    parser.add_argument("--dry-run", action="store_true",
                        help="Chunk and report stats without embedding")
    args = parser.parse_args()

    content_dir = Path(args.content_dir)

    # Collect and chunk
    print(f"Scanning {content_dir}...")
    chunks = collect_chunks(content_dir)
    print(f"Generated {len(chunks)} chunks from {len(set(c['file_path'] for c in chunks))} documents")
    print(f"Total tokens: ~{sum(c['tokens'] for c in chunks):,}")

    if args.dry_run:
        # Show distribution
        by_cat = {}
        for c in chunks:
            cat = c["category"] or "uncategorized"
            by_cat[cat] = by_cat.get(cat, 0) + 1
        print("\nChunks by category:")
        for cat, count in sorted(by_cat.items(), key=lambda x: -x[1]):
            print(f"  {cat}: {count}")
        return

    # Import LanceDB
    try:
        import lancedb
    except ImportError:
        sys.exit("lancedb required: pip install lancedb")

    # Embed
    texts = [c["text"] for c in chunks]
    print(f"\nEmbedding {len(texts)} chunks with {args.model}...")
    if args.model == "ollama":
        vectors = embed_ollama(texts)
    else:
        vectors = embed_sentence_transformers(texts)
    print(f"Embedding complete. Dimension: {len(vectors[0])}")

    # Build records for LanceDB
    records = []
    for chunk, vec in zip(chunks, vectors):
        records.append({
            "id": chunk["id"],
            "content_hash": chunk["content_hash"],
            "file_path": chunk["file_path"],
            "chunk_index": chunk["chunk_index"],
            "title": chunk["title"],
            "category": chunk["category"],
            "project": chunk["project"],
            "tags": chunk["tags"],
            "text": chunk["text"],
            "tokens": chunk["tokens"],
            "vector": vec,
        })

    # Upsert to LanceDB
    db_dir = Path(args.db_dir)
    db_dir.mkdir(parents=True, exist_ok=True)
    db = lancedb.connect(str(db_dir))

    if args.rebuild and TABLE_NAME in db.table_names():
        db.drop_table(TABLE_NAME)
        print(f"Dropped existing table '{TABLE_NAME}'")

    if TABLE_NAME in db.table_names():
        table = db.open_table(TABLE_NAME)
        # Content-hash dedup: only add new/changed chunks
        existing_hashes = set(table.to_pandas()["content_hash"].tolist())
        new_records = [r for r in records if r["content_hash"] not in existing_hashes]
        if new_records:
            table.add(new_records)
            print(f"Added {len(new_records)} new chunks ({len(records) - len(new_records)} unchanged)")
        else:
            print("No new or changed chunks to add")
    else:
        table = db.create_table(TABLE_NAME, records)
        print(f"Created table '{TABLE_NAME}' with {len(records)} chunks")

    print(f"\nLanceDB stored at: {db_dir}")
    print(f"Table: {TABLE_NAME} ({table.count_rows()} total rows)")
    print("Done.")


if __name__ == "__main__":
    main()

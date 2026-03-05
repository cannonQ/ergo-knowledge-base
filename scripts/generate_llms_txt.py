#!/usr/bin/env python3
"""
Generate llms.txt and llms-full.txt from the EKB content directory.

llms.txt  — AI-readable sitemap: one line per doc with title, path, description, ~token count.
llms-full.txt — Concatenation of all docs for direct context-window ingestion.

Walks content/, reads YAML frontmatter, estimates token counts, groups by section.

Usage:
  python3 scripts/generate_llms_txt.py
  python3 scripts/generate_llms_txt.py --content-dir content --output-dir .
"""

import argparse
import re
from collections import defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.resolve()
DEFAULT_CONTENT_DIR = REPO_ROOT / "content"

# Section ordering and display names — maps top-level dirs under content/
SECTION_ORDER = [
    ("concepts", "Concepts"),
    ("reference", "Reference"),
    ("sdks", "SDK Documentation"),
    ("cookbook", "Cookbook"),
    ("guides", "Guides"),
    ("patterns", "Integration Patterns"),
    ("ecosystem", "Ecosystem dApps"),
    ("node", "Node Operation"),
    ("privacy", "Privacy"),
    ("examples", "Examples"),
]

# Fallback for dirs not in the list
SECTION_FALLBACK_NAME = "Other"


def estimate_tokens(text: str) -> int:
    """Rough token estimate: ~4 chars per token for English prose + code."""
    return len(text) // 4


def parse_frontmatter(path: Path) -> dict:
    """Extract YAML frontmatter from a markdown file. Returns {} if none found."""
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
            # Strip quotes
            if (val.startswith('"') and val.endswith('"')) or \
               (val.startswith("'") and val.endswith("'")):
                val = val[1:-1]
            # Parse simple lists [a, b, c]
            if val.startswith("[") and val.endswith("]"):
                val = [v.strip().strip("'\"") for v in val[1:-1].split(",") if v.strip()]
            meta[key] = val
    return meta


def collect_docs(content_dir: Path) -> list[dict]:
    """Walk content dir, parse frontmatter, return list of doc metadata dicts."""
    docs = []
    for md_path in sorted(content_dir.rglob("*.md")):
        rel = md_path.relative_to(content_dir)
        fm = parse_frontmatter(md_path)
        try:
            text = md_path.read_text(errors="ignore")
        except OSError:
            continue
        tokens = estimate_tokens(text)

        # Determine section from first path component
        parts = rel.parts
        section_key = parts[0] if len(parts) > 1 else "other"

        title = fm.get("title", rel.stem.replace("-", " ").title())
        description = fm.get("description", "")

        docs.append({
            "path": str(Path("content") / rel),
            "rel": rel,
            "section_key": section_key,
            "title": title,
            "description": description,
            "tokens": tokens,
            "category": fm.get("category", ""),
            "difficulty": fm.get("difficulty", ""),
            "tags": fm.get("tags", []),
            "full_text": text,
        })
    return docs


def build_llms_txt(docs: list[dict]) -> str:
    """Build the llms.txt content."""
    lines = [
        "# Ergo Developer Knowledge Base",
        "",
        "> Comprehensive developer documentation for the Ergo blockchain ecosystem,",
        "> including SDKs, ErgoScript smart contracts, node APIs, integration patterns,",
        "> ecosystem dApp architecture, and community knowledge from 8+ years of",
        "> Telegram history and video transcripts.",
        "",
    ]

    # Group docs by section
    by_section: dict[str, list[dict]] = defaultdict(list)
    for doc in docs:
        by_section[doc["section_key"]].append(doc)

    # Emit sections in defined order
    emitted = set()
    for key, display_name in SECTION_ORDER:
        if key not in by_section:
            continue
        emitted.add(key)
        section_docs = by_section[key]
        lines.append(f"## {display_name}")
        for doc in sorted(section_docs, key=lambda d: str(d["rel"])):
            desc = f": {doc['description']}" if doc["description"] else ""
            lines.append(f"- [{doc['title']}]({doc['path']}){desc} (~{doc['tokens']} tokens)")
        lines.append("")

    # Emit any remaining sections not in SECTION_ORDER
    for key in sorted(by_section.keys()):
        if key in emitted:
            continue
        section_docs = by_section[key]
        display_name = key.replace("-", " ").title()
        lines.append(f"## {display_name}")
        for doc in sorted(section_docs, key=lambda d: str(d["rel"])):
            desc = f": {doc['description']}" if doc["description"] else ""
            lines.append(f"- [{doc['title']}]({doc['path']}){desc} (~{doc['tokens']} tokens)")
        lines.append("")

    # Summary stats
    total_tokens = sum(d["tokens"] for d in docs)
    lines.append(f"---")
    lines.append(f"Total: {len(docs)} documents, ~{total_tokens:,} tokens")
    return "\n".join(lines)


def build_llms_full_txt(docs: list[dict]) -> str:
    """Concatenate all docs into a single file for context-window ingestion."""
    parts = [
        "# Ergo Developer Knowledge Base — Full Context",
        "",
        f"Total documents: {len(docs)}",
        f"Estimated tokens: ~{sum(d['tokens'] for d in docs):,}",
        "",
        "=" * 72,
        "",
    ]

    for doc in sorted(docs, key=lambda d: str(d["rel"])):
        parts.append(f"<!-- FILE: {doc['path']} -->")
        parts.append(doc["full_text"])
        parts.append("")
        parts.append("=" * 72)
        parts.append("")

    return "\n".join(parts)


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate llms.txt and llms-full.txt")
    parser.add_argument("--content-dir", default=str(DEFAULT_CONTENT_DIR),
                        help="Path to content directory")
    parser.add_argument("--output-dir", default=str(REPO_ROOT),
                        help="Where to write llms.txt and llms-full.txt")
    parser.add_argument("--no-full", action="store_true",
                        help="Skip generating llms-full.txt (it can be large)")
    args = parser.parse_args()

    content_dir = Path(args.content_dir)
    output_dir = Path(args.output_dir)

    if not content_dir.exists():
        print(f"Content directory not found: {content_dir}")
        return

    print(f"Scanning {content_dir}...")
    docs = collect_docs(content_dir)
    print(f"Found {len(docs)} documents")

    # Generate llms.txt
    llms_txt = build_llms_txt(docs)
    llms_path = output_dir / "llms.txt"
    llms_path.write_text(llms_txt)
    print(f"Wrote {llms_path} ({len(llms_txt):,} chars)")

    # Generate llms-full.txt
    if not args.no_full:
        llms_full = build_llms_full_txt(docs)
        full_path = output_dir / "llms-full.txt"
        full_path.write_text(llms_full)
        print(f"Wrote {full_path} ({len(llms_full):,} chars, ~{sum(d['tokens'] for d in docs):,} tokens)")
    else:
        print("Skipping llms-full.txt (--no-full)")

    print("Done.")


if __name__ == "__main__":
    main()

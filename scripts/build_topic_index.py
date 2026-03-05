#!/usr/bin/env python3
"""
Build a cross-document topic index from EKB content.

Scans all markdown files under content/, extracts tags from frontmatter,
and builds a topic index that maps each tag to the documents containing it.
Also generates a tag co-occurrence matrix for discovering related topics.

If BERTopic is available (pip install bertopic), additionally runs topic
modeling across Telegram segments to discover emergent cross-month topics.

Output:
  content/topics/topic-index.md    — Human/LLM-readable topic index
  content/topics/topic-index.json  — Machine-readable index for MCP server

Usage:
  python3 scripts/build_topic_index.py
  python3 scripts/build_topic_index.py --include-telegram ~/ergo-telegram/output
"""

import argparse
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.resolve()
CONTENT_DIR = REPO_ROOT / "content"


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


def collect_tagged_docs(content_dir: Path) -> list[dict]:
    """Walk content dir and return docs with their tags."""
    docs = []
    for md_path in sorted(content_dir.rglob("*.md")):
        rel = md_path.relative_to(REPO_ROOT)
        fm = parse_frontmatter(md_path)
        tags = fm.get("tags", [])
        if isinstance(tags, str):
            tags = [tags]
        title = fm.get("title", rel.stem.replace("-", " ").title())
        category = fm.get("category", "")
        difficulty = fm.get("difficulty", "")
        docs.append({
            "path": str(rel),
            "title": title,
            "tags": [t.lower().strip() for t in tags],
            "category": category,
            "difficulty": difficulty,
        })
    return docs


def build_tag_index(docs: list[dict]) -> dict[str, list[dict]]:
    """Build tag → [doc, ...] mapping."""
    index: dict[str, list[dict]] = defaultdict(list)
    for doc in docs:
        for tag in doc["tags"]:
            index[tag].append({
                "path": doc["path"],
                "title": doc["title"],
                "category": doc["category"],
            })
    return dict(sorted(index.items()))


def build_cooccurrence(docs: list[dict], min_count: int = 2) -> list[tuple]:
    """Find tags that frequently appear together."""
    pair_counts: Counter = Counter()
    for doc in docs:
        tags = sorted(set(doc["tags"]))
        for i, t1 in enumerate(tags):
            for t2 in tags[i + 1:]:
                pair_counts[(t1, t2)] += 1
    return [(t1, t2, c) for (t1, t2), c in pair_counts.most_common() if c >= min_count]


def load_telegram_topics(telegram_dir: Path) -> list[dict]:
    """Load topic JSON files from Telegram segment output."""
    topics = []
    for topics_json in sorted(telegram_dir.rglob("*_topics.json")):
        try:
            data = json.loads(topics_json.read_text())
        except (json.JSONDecodeError, OSError):
            continue
        segment_name = topics_json.stem.replace("_topics", "")

        # Handle both formats: top-level list or {"topics": [...]}
        items = []
        if isinstance(data, list):
            items = data
        elif isinstance(data, dict) and "topics" in data:
            items = data["topics"]

        for item in items:
            if not isinstance(item, dict):
                continue
            # Accept "topic" or "title" as the topic name field
            topic_name = item.get("topic") or item.get("title", "")
            if topic_name:
                topics.append({
                    "topic": topic_name,
                    "segment": segment_name,
                    "category": item.get("category", ""),
                    "significance": item.get("significance", ""),
                    "source": str(topics_json.relative_to(telegram_dir)),
                })
    return topics


def generate_topic_index_md(tag_index: dict, cooccurrence: list,
                            telegram_topics: list[dict] | None = None) -> str:
    """Generate the markdown topic index."""
    lines = [
        "# Topic Index",
        "",
        "Auto-generated cross-reference of all topics in the Ergo Knowledge Base.",
        "",
        f"**{len(tag_index)} tags** across all documents.",
        "",
        "---",
        "",
    ]

    # Tags sorted by document count (most common first)
    sorted_tags = sorted(tag_index.items(), key=lambda x: -len(x[1]))

    lines.append("## Tags by Frequency")
    lines.append("")
    for tag, docs in sorted_tags:
        lines.append(f"### `{tag}` ({len(docs)} docs)")
        for doc in docs[:15]:  # cap display at 15 per tag
            lines.append(f"- [{doc['title']}]({doc['path']})")
        if len(docs) > 15:
            lines.append(f"- *...and {len(docs) - 15} more*")
        lines.append("")

    # Co-occurrence
    if cooccurrence:
        lines.append("---")
        lines.append("")
        lines.append("## Related Tag Pairs")
        lines.append("")
        lines.append("Tags that frequently appear together:")
        lines.append("")
        for t1, t2, count in cooccurrence[:30]:
            lines.append(f"- `{t1}` + `{t2}` ({count} docs)")
        lines.append("")

    # Telegram topics if available
    if telegram_topics:
        topic_counts = Counter(t["topic"] for t in telegram_topics)
        lines.append("---")
        lines.append("")
        lines.append("## Telegram Discussion Topics")
        lines.append("")
        lines.append(f"Extracted from {len(telegram_topics)} topic segments:")
        lines.append("")
        for topic, count in topic_counts.most_common(50):
            lines.append(f"- **{topic}** ({count} mentions)")
        lines.append("")

    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Build topic index from EKB content")
    parser.add_argument("--content-dir", default=str(CONTENT_DIR))
    parser.add_argument("--include-telegram", default=None,
                        help="Path to Telegram output dir (e.g. ~/ergo-telegram/output)")
    args = parser.parse_args()

    content_dir = Path(args.content_dir)

    print(f"Scanning {content_dir}...")
    docs = collect_tagged_docs(content_dir)
    print(f"Found {len(docs)} documents with tags")

    tag_index = build_tag_index(docs)
    print(f"Unique tags: {len(tag_index)}")

    cooccurrence = build_cooccurrence(docs)
    print(f"Tag pairs (co-occurrence >= 2): {len(cooccurrence)}")

    # Telegram topics
    telegram_topics = None
    if args.include_telegram:
        tg_dir = Path(args.include_telegram).expanduser()
        if tg_dir.exists():
            telegram_topics = load_telegram_topics(tg_dir)
            print(f"Telegram topics loaded: {len(telegram_topics)}")
        else:
            print(f"Warning: Telegram dir not found: {tg_dir}")

    # Write markdown index
    output_dir = content_dir / "topics"
    output_dir.mkdir(parents=True, exist_ok=True)

    md_content = generate_topic_index_md(tag_index, cooccurrence, telegram_topics)
    md_path = output_dir / "topic-index.md"
    md_path.write_text(md_content)
    print(f"Wrote {md_path}")

    # Write JSON index (for MCP server)
    json_index = {
        "tag_count": len(tag_index),
        "doc_count": len(docs),
        "tags": {tag: [{"path": d["path"], "title": d["title"]} for d in docs_list]
                 for tag, docs_list in tag_index.items()},
        "cooccurrence": [{"tag1": t1, "tag2": t2, "count": c} for t1, t2, c in cooccurrence],
    }
    if telegram_topics:
        json_index["telegram_topics"] = telegram_topics

    json_path = output_dir / "topic-index.json"
    json_path.write_text(json.dumps(json_index, indent=2))
    print(f"Wrote {json_path}")

    print("Done.")


if __name__ == "__main__":
    main()

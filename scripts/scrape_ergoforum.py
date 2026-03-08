#!/usr/bin/env python3
"""
Scrape ErgoForum (Discourse) and produce clustered markdown archive.

Usage:
    # Scrape all topics (raw JSON cache + markdown output)
    python scripts/scrape_ergoforum.py

    # Re-process cached JSON without re-fetching
    python scripts/scrape_ergoforum.py --offline

    # Scrape only first N pages (for testing)
    python scripts/scrape_ergoforum.py --max-pages 2

Output:
    forum/raw/                   — cached JSON per topic (gitignored)
    forum/topics/{category}/     — markdown per topic
    forum/forum-index.md         — category + tag-based topic index
    forum/forum-index.json       — machine-readable index
"""

import argparse
import json
import os
import re
import sys
import time
from collections import defaultdict
from pathlib import Path

import requests
import yaml
from markdownify import markdownify as md

BASE_URL = "https://ergoforum.org"
RATE_LIMIT_DELAY = 0.5  # seconds between API calls
TOPICS_PER_PAGE = 30

REPO_ROOT = Path(__file__).resolve().parent.parent
FORUM_DIR = REPO_ROOT / "forum"
RAW_DIR = FORUM_DIR / "raw"
TOPICS_DIR = FORUM_DIR / "topics"
GLOSSARY_PATH = REPO_ROOT / "glossary" / "ergo_glossary.yaml"


def load_glossary_terms():
    """Load glossary terms + aliases for auto-tagging."""
    if not GLOSSARY_PATH.exists():
        print(f"  Warning: glossary not found at {GLOSSARY_PATH}, skipping auto-tagging")
        return {}
    with open(GLOSSARY_PATH) as f:
        glossary = yaml.safe_load(f)
    # Build alias -> canonical term map (lowercase)
    term_map = {}
    for entry in glossary.get("terms", []):
        canonical = entry["term"]
        term_map[canonical.lower()] = canonical
        for alias in entry.get("aliases", []):
            term_map[alias.lower()] = canonical
    return term_map


def fetch_json(url, params=None):
    """Fetch JSON from Discourse API with rate limiting."""
    time.sleep(RATE_LIMIT_DELAY)
    resp = requests.get(url, params=params, timeout=30)
    resp.raise_for_status()
    return resp.json()


def fetch_categories():
    """Fetch category id -> name mapping."""
    data = fetch_json(f"{BASE_URL}/categories.json")
    cats = {}
    for cat in data.get("category_list", {}).get("categories", []):
        cats[cat["id"]] = {
            "name": cat["name"],
            "slug": cat["slug"],
            "description": cat.get("description_text", ""),
        }
        # Include subcategories
        for sub in cat.get("subcategory_ids", []):
            # Subcategory details aren't always inline; we'll fill them if we see them
            pass
    return cats


def fetch_all_topic_ids(max_pages=None):
    """Paginate through /latest.json to collect all topic metadata."""
    topics = []
    page = 0
    while True:
        if max_pages and page >= max_pages:
            break
        print(f"  Fetching topic list page {page}...")
        data = fetch_json(f"{BASE_URL}/latest.json", params={"page": page})
        topic_list = data.get("topic_list", {})
        page_topics = topic_list.get("topics", [])
        if not page_topics:
            break
        for t in page_topics:
            topics.append({
                "id": t["id"],
                "title": t["title"],
                "slug": t["slug"],
                "category_id": t.get("category_id"),
                "created_at": t.get("created_at", ""),
                "last_posted_at": t.get("last_posted_at", ""),
                "posts_count": t.get("posts_count", 0),
                "reply_count": t.get("reply_count", 0),
                "views": t.get("views", 0),
                "like_count": t.get("like_count", 0),
                "closed": t.get("closed", False),
                "archived": t.get("archived", False),
            })
        more_url = topic_list.get("more_topics_url")
        if not more_url:
            break
        page += 1
    return topics


def fetch_topic_detail(topic_id):
    """Fetch full topic with all posts."""
    cache_path = RAW_DIR / f"{topic_id}.json"
    if cache_path.exists():
        with open(cache_path) as f:
            return json.load(f)

    data = fetch_json(f"{BASE_URL}/t/{topic_id}.json")

    # If topic has more posts than the first page, fetch them
    post_stream = data.get("post_stream", {})
    stream_ids = post_stream.get("stream", [])
    loaded_ids = {p["id"] for p in post_stream.get("posts", [])}
    missing_ids = [pid for pid in stream_ids if pid not in loaded_ids]

    # Fetch missing posts in chunks of 20
    while missing_ids:
        chunk = missing_ids[:20]
        missing_ids = missing_ids[20:]
        params = {f"post_ids[]": chunk}
        # Discourse endpoint for additional posts
        try:
            extra = fetch_json(f"{BASE_URL}/t/{topic_id}/posts.json",
                               params={"post_ids[]": chunk})
            extra_posts = extra.get("post_stream", {}).get("posts", [])
            post_stream["posts"].extend(extra_posts)
        except Exception as e:
            print(f"    Warning: couldn't fetch extra posts for topic {topic_id}: {e}")
            break

    # Cache raw JSON
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    with open(cache_path, "w") as f:
        json.dump(data, f)
    return data


def html_to_markdown(html):
    """Convert Discourse HTML to clean markdown."""
    if not html:
        return ""
    # markdownify handles most conversion
    text = md(html, heading_style="ATX", code_language="ergoscript")
    # Clean up excessive whitespace
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def auto_tag(text, term_map):
    """Find glossary terms mentioned in text. Returns set of canonical terms."""
    if not term_map:
        return set()
    text_lower = text.lower()
    found = set()
    for alias, canonical in term_map.items():
        # Only match whole words (with word boundaries)
        if len(alias) < 3:
            continue  # Skip very short aliases to avoid false positives
        # Simple substring check with word boundary approximation
        pattern = r'\b' + re.escape(alias) + r'\b'
        if re.search(pattern, text_lower):
            found.add(canonical)
    return found


def slugify(text):
    """Create a filesystem-safe slug."""
    text = text.lower().strip()
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[\s_]+', '-', text)
    text = re.sub(r'-+', '-', text)
    return text[:80].rstrip('-')


def topic_to_markdown(topic_meta, topic_detail, categories, term_map):
    """Convert a topic + its posts to a markdown document."""
    post_stream = topic_detail.get("post_stream", {})
    posts = post_stream.get("posts", [])

    # Sort posts by post_number
    posts.sort(key=lambda p: p.get("post_number", 0))

    cat_id = topic_meta.get("category_id") or topic_detail.get("category_id")
    cat_info = categories.get(cat_id, {"name": "Uncategorized", "slug": "uncategorized"})
    cat_name = cat_info["name"]
    cat_slug = cat_info["slug"]

    # Build full text for tagging
    all_text = topic_meta["title"] + "\n"
    post_bodies = []
    for post in posts:
        cooked = post.get("cooked", "")
        body_md = html_to_markdown(cooked)
        post_bodies.append({
            "author": post.get("username", "unknown"),
            "date": post.get("created_at", "")[:10],
            "datetime": post.get("created_at", ""),
            "post_number": post.get("post_number", 0),
            "body": body_md,
            "likes": post.get("like_count", 0),
        })
        all_text += body_md + "\n"

    tags = auto_tag(all_text, term_map)
    tag_list = sorted(tags)
    # Add forum-specific tags
    tag_list_full = sorted(set(["ergoforum", cat_slug.lower()] + [t.lower().replace(" ", "-") for t in tag_list]))

    created = topic_meta.get("created_at", "")[:10]
    last_posted = topic_meta.get("last_posted_at", "")[:10]
    topic_url = f"{BASE_URL}/t/{topic_meta['slug']}/{topic_meta['id']}"

    # Build frontmatter
    frontmatter = {
        "title": topic_meta["title"],
        "description": f"ErgoForum discussion: {topic_meta['title']}",
        "tags": tag_list_full,
        "category": "forum",
        "forum_category": cat_name,
        "source": "ergoforum",
        "source_url": topic_url,
        "created": created,
        "last_activity": last_posted,
        "posts_count": topic_meta.get("posts_count", len(posts)),
        "views": topic_meta.get("views", 0),
        "likes": topic_meta.get("like_count", 0),
        "glossary_hits": tag_list if tag_list else [],
    }

    # Build markdown body
    lines = []
    lines.append(f"# {topic_meta['title']}\n")
    lines.append(f"> **Forum thread:** [{topic_url}]({topic_url})")
    lines.append(f"> **Category:** {cat_name} | **Created:** {created} | "
                 f"**Posts:** {topic_meta.get('posts_count', len(posts))} | "
                 f"**Views:** {topic_meta.get('views', 0)}\n")

    if tag_list:
        lines.append(f"**Related concepts:** {', '.join(tag_list)}\n")

    for pb in post_bodies:
        lines.append(f"---\n")
        lines.append(f"### Post #{pb['post_number']} — @{pb['author']} ({pb['date']})"
                     + (f" [{pb['likes']} likes]" if pb['likes'] else ""))
        lines.append("")
        lines.append(pb["body"])
        lines.append("")

    # Format frontmatter as YAML
    fm_str = yaml.dump(frontmatter, default_flow_style=False, allow_unicode=True, sort_keys=False)
    doc = f"---\n{fm_str}---\n\n" + "\n".join(lines)

    return doc, cat_slug, tag_list


def build_index(all_topics_info, categories):
    """Build forum-index.md and forum-index.json."""
    # Group by category
    by_category = defaultdict(list)
    # Group by glossary tag
    by_tag = defaultdict(list)

    for info in all_topics_info:
        by_category[info["category"]].append(info)
        for tag in info.get("glossary_tags", []):
            by_tag[tag].append(info)

    # Sort each category by views (most popular first)
    for cat in by_category:
        by_category[cat].sort(key=lambda x: x.get("views", 0), reverse=True)

    # Build markdown index
    lines = []
    lines.append("---")
    lines.append("title: \"ErgoForum Archive Index\"")
    lines.append(f"description: \"Clustered archive of {len(all_topics_info)} ErgoForum topics (2019-2026), "
                 "organized by category and auto-tagged with glossary terms.\"")
    lines.append("tags: [ergoforum, archive, community]")
    lines.append("category: forum")
    lines.append("source: ergoforum")
    lines.append(f"updated: {time.strftime('%Y-%m-%d')}")
    lines.append("---\n")
    lines.append(f"# ErgoForum Archive\n")
    lines.append(f"**{len(all_topics_info)} topics** from [ergoforum.org]({BASE_URL}) "
                 f"(July 2019 — present), auto-tagged against the Ergo glossary.\n")

    # Category sections
    lines.append("## By Category\n")
    cat_order = ["announcements", "development", "support", "community", "mining", "uncategorized"]
    seen_cats = set()
    for slug in cat_order:
        if slug in by_category:
            seen_cats.add(slug)
            cat_name = slug.replace("-", " ").title()
            topics = by_category[slug]
            lines.append(f"### {cat_name} ({len(topics)} topics)\n")
            for t in topics[:50]:  # Cap at 50 per category in index
                tags_str = ""
                if t.get("glossary_tags"):
                    tags_str = " — " + ", ".join(t["glossary_tags"][:5])
                lines.append(f"- [{t['title']}]({t['path']}) "
                             f"({t.get('posts_count', '?')} posts, {t.get('views', '?')} views)"
                             f"{tags_str}")
            if len(topics) > 50:
                lines.append(f"- *... and {len(topics) - 50} more*")
            lines.append("")

    # Any categories not in our order
    for slug, topics in sorted(by_category.items()):
        if slug not in seen_cats:
            cat_name = slug.replace("-", " ").title()
            lines.append(f"### {cat_name} ({len(topics)} topics)\n")
            for t in topics[:50]:
                lines.append(f"- [{t['title']}]({t['path']}) "
                             f"({t.get('posts_count', '?')} posts, {t.get('views', '?')} views)")
            if len(topics) > 50:
                lines.append(f"- *... and {len(topics) - 50} more*")
            lines.append("")

    # Tag sections (top tags by topic count)
    lines.append("## By Topic (Glossary Tags)\n")
    sorted_tags = sorted(by_tag.items(), key=lambda x: len(x[1]), reverse=True)
    for tag, topics in sorted_tags[:30]:  # Top 30 tags
        lines.append(f"### {tag} ({len(topics)} topics)\n")
        # Show top 10 by views
        sorted_topics = sorted(topics, key=lambda x: x.get("views", 0), reverse=True)
        for t in sorted_topics[:10]:
            lines.append(f"- [{t['title']}]({t['path']}) "
                         f"({t.get('posts_count', '?')} posts, {t.get('views', '?')} views)")
        if len(topics) > 10:
            lines.append(f"- *... and {len(topics) - 10} more*")
        lines.append("")

    # Write markdown index
    index_path = FORUM_DIR / "forum-index.md"
    with open(index_path, "w") as f:
        f.write("\n".join(lines))
    print(f"  Wrote {index_path}")

    # Write JSON index
    json_index = {
        "total_topics": len(all_topics_info),
        "by_category": {cat: [{"title": t["title"], "path": t["path"],
                                "views": t.get("views", 0),
                                "glossary_tags": t.get("glossary_tags", [])}
                               for t in topics]
                        for cat, topics in by_category.items()},
        "by_tag": {tag: [{"title": t["title"], "path": t["path"]}
                         for t in sorted(topics, key=lambda x: x.get("views", 0), reverse=True)[:20]]
                   for tag, topics in sorted_tags[:50]},
        "tag_counts": {tag: len(topics) for tag, topics in sorted_tags},
    }
    json_path = FORUM_DIR / "forum-index.json"
    with open(json_path, "w") as f:
        json.dump(json_index, f, indent=2)
    print(f"  Wrote {json_path}")


def main():
    parser = argparse.ArgumentParser(description="Scrape ErgoForum into clustered markdown archive")
    parser.add_argument("--offline", action="store_true",
                        help="Re-process cached JSON without fetching")
    parser.add_argument("--max-pages", type=int, default=None,
                        help="Limit topic list pagination (for testing)")
    parser.add_argument("--max-topics", type=int, default=None,
                        help="Limit number of topics to fetch detail for")
    args = parser.parse_args()

    # Ensure output dirs exist
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    TOPICS_DIR.mkdir(parents=True, exist_ok=True)

    # Load glossary
    print("Loading glossary terms...")
    term_map = load_glossary_terms()
    print(f"  {len(term_map)} aliases loaded")

    # Fetch categories
    print("Fetching categories...")
    if args.offline:
        cat_cache = RAW_DIR / "_categories.json"
        if cat_cache.exists():
            with open(cat_cache) as f:
                categories = json.load(f)
        else:
            print("  No cached categories, fetching...")
            categories = fetch_categories()
    else:
        categories = fetch_categories()
        # Cache categories
        with open(RAW_DIR / "_categories.json", "w") as f:
            json.dump(categories, f)
    # Convert string keys back to int (JSON serialization issue)
    categories = {int(k) if isinstance(k, str) else k: v for k, v in categories.items()}
    print(f"  {len(categories)} categories")

    # Fetch topic list
    if args.offline:
        topic_list_cache = RAW_DIR / "_topic_list.json"
        if topic_list_cache.exists():
            with open(topic_list_cache) as f:
                topic_list = json.load(f)
            print(f"Loaded {len(topic_list)} cached topic entries")
        else:
            print("ERROR: No cached topic list. Run without --offline first.")
            sys.exit(1)
    else:
        print("Fetching topic list...")
        topic_list = fetch_all_topic_ids(max_pages=args.max_pages)
        print(f"  Found {len(topic_list)} topics")
        # Cache topic list
        with open(RAW_DIR / "_topic_list.json", "w") as f:
            json.dump(topic_list, f)

    if args.max_topics:
        topic_list = topic_list[:args.max_topics]

    # Fetch each topic's full content and convert to markdown
    print(f"\nProcessing {len(topic_list)} topics...")
    all_topics_info = []
    errors = []

    for i, topic_meta in enumerate(topic_list):
        tid = topic_meta["id"]
        title = topic_meta["title"]
        pct = (i + 1) / len(topic_list) * 100
        print(f"  [{i+1}/{len(topic_list)} {pct:.0f}%] {title[:60]}...")

        try:
            topic_detail = fetch_topic_detail(tid)
        except Exception as e:
            print(f"    ERROR fetching topic {tid}: {e}")
            errors.append({"id": tid, "title": title, "error": str(e)})
            continue

        # Convert to markdown
        doc, cat_slug, glossary_tags = topic_to_markdown(
            topic_meta, topic_detail, categories, term_map
        )

        # Write to category subdirectory
        cat_dir = TOPICS_DIR / cat_slug
        cat_dir.mkdir(parents=True, exist_ok=True)
        filename = f"{slugify(title)}.md"
        filepath = cat_dir / filename
        with open(filepath, "w") as f:
            f.write(doc)

        rel_path = str(filepath.relative_to(REPO_ROOT))
        all_topics_info.append({
            "id": tid,
            "title": title,
            "category": cat_slug,
            "path": rel_path,
            "created": topic_meta.get("created_at", "")[:10],
            "posts_count": topic_meta.get("posts_count", 0),
            "views": topic_meta.get("views", 0),
            "likes": topic_meta.get("like_count", 0),
            "glossary_tags": glossary_tags,
        })

    # Build index
    print(f"\nBuilding index ({len(all_topics_info)} topics)...")
    build_index(all_topics_info, categories)

    # Summary
    print(f"\n{'='*60}")
    print(f"ErgoForum scrape complete!")
    print(f"  Topics processed: {len(all_topics_info)}")
    print(f"  Errors: {len(errors)}")
    print(f"  Output: {TOPICS_DIR}/")
    print(f"  Index:  {FORUM_DIR}/forum-index.md")
    if errors:
        print(f"\n  Failed topics:")
        for e in errors:
            print(f"    - [{e['id']}] {e['title']}: {e['error']}")


if __name__ == "__main__":
    main()

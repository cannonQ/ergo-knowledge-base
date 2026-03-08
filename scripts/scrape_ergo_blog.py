#!/usr/bin/env python3
"""
Scrape Ergo Platform blog posts from Strapi CMS and produce clustered markdown archive.

Usage:
    # Fetch from Strapi API and generate markdown archive
    python scripts/scrape_ergo_blog.py

    # Re-process cached JSON without re-fetching
    python scripts/scrape_ergo_blog.py --offline

Output:
    blog/raw/                    — cached JSON (gitignored)
    blog/posts/{tag-slug}/       — markdown per post (content posts)
    blog/stubs/{tag-slug}/       — stub markdown (external-URL-only posts)
    blog/blog-index.md           — tag + year-based post index
    blog/blog-index.json         — machine-readable index
"""

import argparse
import json
import os
import re
import sys
import time
import urllib.request
import urllib.error
from collections import defaultdict
from pathlib import Path

import yaml

STRAPI_BASE = "https://ergo-platform-cms-nvbpfiue6q-ez.a.run.app"
BLOG_URL_BASE = "https://ergoplatform.org/en/blog/"
PAGE_SIZE = 100

REPO_ROOT = Path(__file__).resolve().parent.parent
BLOG_DIR = REPO_ROOT / "blog"
RAW_DIR = BLOG_DIR / "raw"
POSTS_DIR = BLOG_DIR / "posts"
STUBS_DIR = BLOG_DIR / "stubs"
GLOSSARY_PATH = REPO_ROOT / "glossary" / "ergo_glossary.yaml"


def load_glossary_terms():
    """Load glossary terms + aliases for auto-tagging."""
    if not GLOSSARY_PATH.exists():
        print(f"  Warning: glossary not found at {GLOSSARY_PATH}, skipping auto-tagging")
        return {}
    with open(GLOSSARY_PATH) as f:
        glossary = yaml.safe_load(f)
    term_map = {}
    for entry in glossary.get("terms", []):
        canonical = entry["term"]
        term_map[canonical.lower()] = canonical
        for alias in entry.get("aliases", []):
            term_map[alias.lower()] = canonical
    return term_map


def fetch_all_posts():
    """Fetch all blog posts from Strapi CMS API using pagination."""
    cache_path = RAW_DIR / "_all_posts.json"
    if cache_path.exists():
        with open(cache_path) as f:
            return json.loads(f.read(), strict=False)

    all_posts = []
    page = 1
    total_pages = None

    while True:
        url = (f"{STRAPI_BASE}/api/posts?"
               f"pagination%5BpageSize%5D={PAGE_SIZE}&"
               f"pagination%5Bpage%5D={page}")
        print(f"  Fetching page {page}" + (f"/{total_pages}" if total_pages else "") + "...")

        try:
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, timeout=60) as resp:
                raw = resp.read().decode("utf-8")
                data = json.loads(raw, strict=False)
        except Exception as e:
            print(f"    ERROR on page {page}: {e}")
            break

        page_posts = data.get("data", [])
        if not page_posts:
            break

        all_posts.extend(page_posts)
        meta = data.get("meta", {}).get("pagination", {})
        total_pages = meta.get("pageCount", "?")
        total = meta.get("total", "?")

        if page >= (meta.get("pageCount", page)):
            break
        page += 1
        time.sleep(0.3)

    print(f"  Fetched {len(all_posts)} posts (API reports {total} total)")

    # Cache
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    with open(cache_path, "w") as f:
        json.dump(all_posts, f)
    return all_posts


def slugify(text):
    """Create a filesystem-safe slug."""
    text = text.lower().strip()
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[\s_]+', '-', text)
    text = re.sub(r'-+', '-', text)
    return text[:80].rstrip('-')


def tag_to_slug(tag):
    """Convert a blog tag string to a directory slug."""
    if not tag:
        return "uncategorized"
    # Take first tag if comma-separated
    primary = tag.split(",")[0].strip()
    return slugify(primary)


def auto_tag(text, term_map):
    """Find glossary terms mentioned in text. Returns set of canonical terms."""
    if not term_map:
        return set()
    text_lower = text.lower()
    found = set()
    for alias, canonical in term_map.items():
        if len(alias) < 3:
            continue
        pattern = r'\b' + re.escape(alias) + r'\b'
        if re.search(pattern, text_lower):
            found.add(canonical)
    return found


def clean_content(content):
    """Clean up Strapi content for markdown output.

    Strapi content is already markdown-ish (not HTML like Discourse),
    but may have some quirks to clean up.
    """
    if not content:
        return ""
    # Remove HTML comments
    content = re.sub(r'<!--.*?-->', '', content, flags=re.DOTALL)
    # Remove StartFragment/EndFragment markers
    content = re.sub(r'<!--\s*Start\s*Fragment\s*-->', '', content, flags=re.IGNORECASE)
    content = re.sub(r'<!--\s*End\s*Fragment\s*-->', '', content, flags=re.IGNORECASE)
    # Clean up excessive whitespace
    content = re.sub(r'\n{3,}', '\n\n', content)
    return content.strip()


def post_to_markdown(post, term_map):
    """Convert a Strapi post to a markdown document.

    Returns (markdown_str, tag_slug, glossary_tags, has_content).
    """
    attrs = post["attributes"]
    title = attrs.get("title", "Untitled")
    date = (attrs.get("date") or "")[:10]
    author = attrs.get("author") or "Ergo Platform"
    post_type = attrs.get("type", "blog")
    tag = attrs.get("tag") or ""
    content = attrs.get("content") or ""
    ext_url = attrs.get("url") or ""
    permalink = attrs.get("permalink") or ""
    subtitle = attrs.get("subtitle") or ""

    has_content = bool(content and len(content.strip()) > 10)
    tag_slug = tag_to_slug(tag)

    # Build text for glossary tagging
    full_text = f"{title}\n{subtitle}\n{content}"
    glossary_tags = sorted(auto_tag(full_text, term_map))

    # Tag list for frontmatter
    fm_tags = sorted(set(
        ["ergo-blog", tag_slug]
        + [t.lower().replace(" ", "-") for t in glossary_tags]
    ))

    # Build permalink URL
    if permalink:
        blog_url = f"https://ergoplatform.org/en/blog/{permalink}"
    elif ext_url and ext_url.startswith("http"):
        blog_url = ext_url
    else:
        blog_url = f"https://ergoplatform.org/en/blog/"

    # Frontmatter
    frontmatter = {
        "title": title,
        "date": date,
        "author": author,
        "tags": fm_tags,
        "category": "blog",
        "blog_tag": tag if tag else "Uncategorized",
        "type": post_type,
        "source": "ergo-blog",
        "source_url": blog_url,
    }
    if glossary_tags:
        frontmatter["glossary_hits"] = glossary_tags
    if ext_url and ext_url.startswith("http") and not has_content:
        frontmatter["external_url"] = ext_url

    # Build body
    lines = []
    lines.append(f"# {title}\n")
    lines.append(f"> **Published:** {date} | **Author:** {author} | "
                 f"**Tag:** {tag or 'Uncategorized'} | **Type:** {post_type}")
    if ext_url and ext_url.startswith("http"):
        lines.append(f"> **Link:** [{ext_url}]({ext_url})")
    lines.append("")

    if subtitle:
        lines.append(f"*{subtitle}*\n")

    if glossary_tags:
        lines.append(f"**Related concepts:** {', '.join(glossary_tags)}\n")

    lines.append("---\n")

    if has_content:
        lines.append(clean_content(content))
    elif ext_url and ext_url.startswith("http"):
        lines.append(f"*This post is hosted externally. "
                     f"Read the full article at [{ext_url}]({ext_url}).*")
    else:
        lines.append("*Content not available.*")

    # Format frontmatter
    fm_str = yaml.dump(frontmatter, default_flow_style=False,
                       allow_unicode=True, sort_keys=False)
    doc = f"---\n{fm_str}---\n\n" + "\n".join(lines) + "\n"

    return doc, tag_slug, glossary_tags, has_content


def build_index(all_posts_info):
    """Build blog-index.md and blog-index.json."""
    by_tag = defaultdict(list)
    by_year = defaultdict(list)

    for info in all_posts_info:
        by_tag[info["blog_tag"]].append(info)
        year = info["date"][:4] if info.get("date") else "Unknown"
        by_year[year].append(info)
        for gt in info.get("glossary_tags", []):
            pass  # glossary grouping handled separately

    # Sort each group by date descending
    for tag in by_tag:
        by_tag[tag].sort(key=lambda x: x.get("date", ""), reverse=True)
    for year in by_year:
        by_year[year].sort(key=lambda x: x.get("date", ""), reverse=True)

    # Count stats
    content_count = sum(1 for p in all_posts_info if p.get("has_content"))
    stub_count = len(all_posts_info) - content_count

    # Glossary tag index
    by_glossary = defaultdict(list)
    for info in all_posts_info:
        for gt in info.get("glossary_tags", []):
            by_glossary[gt].append(info)

    lines = []
    lines.append("---")
    lines.append("title: \"Ergo Blog Archive Index\"")
    lines.append(f"description: \"Archive of {len(all_posts_info)} Ergo Platform blog posts "
                 f"(2018-2026), organized by topic and year.\"")
    lines.append("tags: [ergo-blog, archive]")
    lines.append("category: blog")
    lines.append("source: ergo-blog")
    lines.append(f"updated: {time.strftime('%Y-%m-%d')}")
    lines.append("---\n")
    lines.append("# Ergo Blog Archive\n")
    lines.append(f"**{len(all_posts_info)} posts** from "
                 f"[ergoplatform.org/en/blog/]({BLOG_URL_BASE}) "
                 f"(2018 — present).\n")
    lines.append(f"- **{content_count}** full-content posts")
    lines.append(f"- **{stub_count}** external-link stubs (mostly Medium articles)\n")

    # By Tag section
    lines.append("## By Blog Tag\n")
    sorted_tags = sorted(by_tag.items(), key=lambda x: len(x[1]), reverse=True)
    for tag, posts in sorted_tags:
        lines.append(f"### {tag} ({len(posts)} posts)\n")
        for p in posts[:20]:
            marker = "" if p.get("has_content") else " [external]"
            lines.append(f"- [{p['title']}]({p['path']}) ({p['date']}){marker}")
        if len(posts) > 20:
            lines.append(f"- *... and {len(posts) - 20} more*")
        lines.append("")

    # By Year section
    lines.append("## By Year\n")
    for year in sorted(by_year.keys(), reverse=True):
        posts = by_year[year]
        lines.append(f"### {year} ({len(posts)} posts)\n")
        for p in posts[:15]:
            marker = "" if p.get("has_content") else " [external]"
            tag_str = f" [{p['blog_tag']}]" if p.get("blog_tag") != "Uncategorized" else ""
            lines.append(f"- [{p['title']}]({p['path']}) ({p['date']}){tag_str}{marker}")
        if len(posts) > 15:
            lines.append(f"- *... and {len(posts) - 15} more*")
        lines.append("")

    # Glossary tags section (top 30)
    lines.append("## By Concept (Glossary Tags)\n")
    sorted_glossary = sorted(by_glossary.items(), key=lambda x: len(x[1]), reverse=True)
    for tag, posts in sorted_glossary[:30]:
        lines.append(f"### {tag} ({len(posts)} posts)\n")
        sorted_posts = sorted(posts, key=lambda x: x.get("date", ""), reverse=True)
        for p in sorted_posts[:10]:
            lines.append(f"- [{p['title']}]({p['path']}) ({p['date']})")
        if len(posts) > 10:
            lines.append(f"- *... and {len(posts) - 10} more*")
        lines.append("")

    # Write markdown index
    index_path = BLOG_DIR / "blog-index.md"
    with open(index_path, "w") as f:
        f.write("\n".join(lines))
    print(f"  Wrote {index_path}")

    # Write JSON index
    json_index = {
        "total_posts": len(all_posts_info),
        "content_posts": content_count,
        "stub_posts": stub_count,
        "by_tag": {tag: [{"title": p["title"], "path": p["path"],
                          "date": p["date"], "has_content": p.get("has_content", False)}
                         for p in posts]
                   for tag, posts in sorted_tags},
        "by_year": {year: len(posts) for year, posts in by_year.items()},
        "glossary_tag_counts": {tag: len(posts) for tag, posts in sorted_glossary},
    }
    json_path = BLOG_DIR / "blog-index.json"
    with open(json_path, "w") as f:
        json.dump(json_index, f, indent=2)
    print(f"  Wrote {json_path}")


def main():
    parser = argparse.ArgumentParser(
        description="Scrape Ergo Platform blog from Strapi CMS into markdown archive")
    parser.add_argument("--offline", action="store_true",
                        help="Re-process cached JSON without fetching")
    parser.add_argument("--max-posts", type=int, default=None,
                        help="Limit number of posts to process")
    args = parser.parse_args()

    # Ensure output dirs exist
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    POSTS_DIR.mkdir(parents=True, exist_ok=True)
    STUBS_DIR.mkdir(parents=True, exist_ok=True)

    # Load glossary
    print("Loading glossary terms...")
    term_map = load_glossary_terms()
    print(f"  {len(term_map)} aliases loaded")

    # Fetch posts
    if args.offline:
        cache_path = RAW_DIR / "_all_posts.json"
        if not cache_path.exists():
            print("ERROR: No cached posts. Run without --offline first.")
            sys.exit(1)
        with open(cache_path) as f:
            all_posts = json.loads(f.read(), strict=False)
        print(f"Loaded {len(all_posts)} cached posts")
    else:
        print("Fetching blog posts from Strapi CMS...")
        all_posts = fetch_all_posts()

    if args.max_posts:
        all_posts = all_posts[:args.max_posts]

    # Process each post
    print(f"\nProcessing {len(all_posts)} posts...")
    all_posts_info = []
    errors = []
    content_count = 0
    stub_count = 0

    for i, post in enumerate(all_posts):
        attrs = post["attributes"]
        title = attrs.get("title", "Untitled")
        pct = (i + 1) / len(all_posts) * 100

        if (i + 1) % 50 == 0 or i == 0:
            print(f"  [{i+1}/{len(all_posts)} {pct:.0f}%] {title[:60]}...")

        try:
            doc, tag_slug, glossary_tags, has_content = post_to_markdown(post, term_map)
        except Exception as e:
            print(f"    ERROR processing post {post['id']}: {e}")
            errors.append({"id": post["id"], "title": title, "error": str(e)})
            continue

        # Write to appropriate directory
        filename = f"{slugify(title)}.md"
        if has_content:
            out_dir = POSTS_DIR / tag_slug
            content_count += 1
        else:
            out_dir = STUBS_DIR / tag_slug
            stub_count += 1

        out_dir.mkdir(parents=True, exist_ok=True)
        filepath = out_dir / filename
        with open(filepath, "w") as f:
            f.write(doc)

        rel_path = str(filepath.relative_to(REPO_ROOT))
        all_posts_info.append({
            "id": post["id"],
            "title": title,
            "date": (attrs.get("date") or "")[:10],
            "blog_tag": attrs.get("tag") or "Uncategorized",
            "type": attrs.get("type", "blog"),
            "path": rel_path,
            "has_content": has_content,
            "glossary_tags": glossary_tags,
        })

    # Build index
    print(f"\nBuilding index ({len(all_posts_info)} posts)...")
    build_index(all_posts_info)

    # Summary
    print(f"\n{'='*60}")
    print(f"Ergo Blog scrape complete!")
    print(f"  Total posts: {len(all_posts_info)}")
    print(f"  Full content: {content_count}")
    print(f"  External stubs: {stub_count}")
    print(f"  Errors: {len(errors)}")
    print(f"  Output: {POSTS_DIR}/ and {STUBS_DIR}/")
    print(f"  Index:  {BLOG_DIR}/blog-index.md")
    if errors:
        print(f"\n  Failed posts:")
        for e in errors:
            print(f"    - [{e['id']}] {e['title']}: {e['error']}")


if __name__ == "__main__":
    main()

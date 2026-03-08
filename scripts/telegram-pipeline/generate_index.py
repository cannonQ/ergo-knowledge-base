#!/usr/bin/env python3
"""
Generate Index Files for ergo-transcripts-web
==============================================
Scans all ergo-telegram output files and produces 4 JSON indexes:
  1. telegram_index.json          — weekly + monthly entries with bidirectional links
  2. telegram_search_index.json   — flat search-optimized entries with excerpts
  3. telegram_topics_index.json   — aggregated topics across all weeks
  4. telegram_speakers.json       — per-speaker chat activity stats

Usage:
    python ~/ergo-telegram/pipeline/generate_index.py
"""

import json
import re
import unicodedata
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

BASE_DIR = Path.home() / "ergo-telegram"
OUTPUT_DIR = BASE_DIR / "output"
PROCESSING_DIR = BASE_DIR / "processing"
WEB_DATA_DIR = Path.home() / "ergo-transcripts-web" / "public" / "data"

CHATS = ["general", "developer"]
MIN_WEEKS_FOR_SPEAKER = 5  # Include speaker if active this many+ weeks
EXCERPT_CHARS = 300        # Characters to include in search excerpts


# ---------------------------------------------------------------------------
# Week / month helpers  (mirrors generate_monthly.py)
# ---------------------------------------------------------------------------

def strip_part_suffix(week_label):
    """Strip trailing part letter from '2021-W31a' → '2021-W31'."""
    if week_label and week_label[-1].isalpha() and not week_label[-1].isdigit():
        return week_label[:-1]
    return week_label


def week_label_to_month(week_label):
    """Map ISO week label to dominant calendar month (uses Thursday)."""
    base = strip_part_suffix(week_label)
    year_str, week_str = base.split("-W")
    thursday = date.fromisocalendar(int(year_str), int(week_str), 4)
    return thursday.strftime("%Y-%m")


# ---------------------------------------------------------------------------
# Truncated JSON recovery
# ---------------------------------------------------------------------------

def load_topics_best_effort(path):
    """
    Load topics JSON, handling truncated LLM responses gracefully.
    Returns a dict with 'topics' and 'active_participants' (may be partial).
    Sets '_truncated': True if recovery was needed.
    """
    content = path.read_text()

    # Fast path: valid JSON
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        pass

    result = {
        "chat": "",
        "week": path.stem.replace("_topics", ""),
        "topics": [],
        "active_participants": [],
        "message_count": 0,
        "_truncated": True,
    }

    # Extract simple scalar fields
    for field in ("chat", "week"):
        m = re.search(rf'"{field}":\s*"([^"]*)"', content)
        if m:
            result[field] = m.group(1)

    m = re.search(r'"message_count":\s*(\d+)', content)
    if m:
        result["message_count"] = int(m.group(1))

    # Extract active_participants (may be partial list)
    m = re.search(r'"active_participants":\s*\[([^\]]*)', content)
    if m:
        result["active_participants"] = re.findall(r'"(@[^"]*)"', m.group(1))

    # Extract complete topic objects using brace matching
    m = re.search(r'"topics":\s*\[(.+)', content, re.DOTALL)
    if m:
        topics_raw = m.group(1)
        depth = 0
        start = -1
        for i, ch in enumerate(topics_raw):
            if ch == '{':
                if depth == 0:
                    start = i
                depth += 1
            elif ch == '}':
                depth -= 1
                if depth == 0 and start >= 0:
                    try:
                        topic = json.loads(topics_raw[start:i + 1])
                        result["topics"].append(topic)
                    except json.JSONDecodeError:
                        pass
                    start = -1

    return result


# ---------------------------------------------------------------------------
# Message count from processing file (authoritative)
# ---------------------------------------------------------------------------

def get_message_count(chat, week_label):
    """Read message count from processing segment header."""
    proc_file = PROCESSING_DIR / chat / f"{week_label}.txt"
    if not proc_file.exists():
        return 0
    for line in proc_file.read_text().splitlines()[:5]:
        if line.startswith("# Messages:"):
            try:
                return int(line.split(":")[1].strip())
            except ValueError:
                pass
    return 0


# ---------------------------------------------------------------------------
# Load all output data
# ---------------------------------------------------------------------------

def load_all_data():
    """
    Scan output directories and load all weekly + monthly data.

    Returns:
        weekly_data:  { chat: { week_label: {...} } }
        monthly_data: { chat: { year_month: {...} } }
    """
    weekly_data = defaultdict(dict)
    monthly_data = defaultdict(dict)

    for chat in CHATS:
        segments_dir = OUTPUT_DIR / chat / "segments"
        if not segments_dir.exists():
            print(f"  Warning: {segments_dir} not found, skipping {chat}")
            continue

        for summary_path in sorted(segments_dir.glob("*_summary.md")):
            week_label = summary_path.stem.replace("_summary", "")
            topics_path = segments_dir / f"{week_label}_topics.json"

            topics_data = {}
            if topics_path.exists():
                topics_data = load_topics_best_effort(topics_path)

            msg_count = (
                topics_data.get("message_count", 0)
                or get_message_count(chat, week_label)
            )

            weekly_data[chat][week_label] = {
                "period": week_label,
                "month": week_label_to_month(week_label),
                "message_count": msg_count,
                "summary_file": f"{chat}/segments/{week_label}_summary.md",
                "topics_file": (
                    f"{chat}/segments/{week_label}_topics.json"
                    if topics_path.exists() else None
                ),
                "topics": topics_data.get("topics", []),
                "active_participants": topics_data.get("active_participants", []),
                "_truncated": topics_data.get("_truncated", False),
            }

        summaries_dir = OUTPUT_DIR / chat / "summaries"
        if summaries_dir.exists():
            for monthly_path in sorted(summaries_dir.glob("*.md")):
                year_month = monthly_path.stem
                monthly_data[chat][year_month] = {
                    "period": year_month,
                    "summary_file": f"{chat}/summaries/{year_month}.md",
                }

    return weekly_data, monthly_data


# ---------------------------------------------------------------------------
# Build telegram_index.json
# ---------------------------------------------------------------------------

def build_index(weekly_data, monthly_data):
    """Build bidirectional weekly ↔ monthly navigation index."""
    index = {}

    for chat in CHATS:
        weeks = weekly_data.get(chat, {})
        months = monthly_data.get(chat, {})

        # Map month → sorted list of week labels
        month_to_weeks = defaultdict(list)
        for wl, data in sorted(weeks.items()):
            month_to_weeks[data["month"]].append(wl)

        # Find multi-part weeks (e.g. 2021-W31a, 2021-W31b)
        base_to_parts = defaultdict(list)
        for wl in sorted(weeks.keys()):
            base = strip_part_suffix(wl)
            if base != wl:
                base_to_parts[base].append(wl)

        enriched_weeks = []
        for wl, data in sorted(weeks.items()):
            base = strip_part_suffix(wl)
            siblings = [w for w in base_to_parts.get(base, []) if w != wl]
            enriched_weeks.append({
                "period": wl,
                "month": data["month"],
                "message_count": data["message_count"],
                "summary_file": data["summary_file"],
                "topics_file": data["topics_file"],
                "top_topics": [t["title"] for t in data["topics"][:3]],
                "sibling_parts": siblings,
            })

        enriched_months = []
        for ym in sorted(months.keys()):
            mdata = months[ym]
            month_weeks = sorted(month_to_weeks.get(ym, []))
            total_msgs = sum(weeks.get(w, {}).get("message_count", 0) for w in month_weeks)
            enriched_months.append({
                "period": ym,
                "summary_file": mdata["summary_file"],
                "weeks": month_weeks,
                "total_messages": total_msgs,
            })

        index[chat] = {
            "weeks": enriched_weeks,
            "months": enriched_months,
        }

    return index


# ---------------------------------------------------------------------------
# Build telegram_search_index.json
# ---------------------------------------------------------------------------

def get_excerpt(relative_file):
    """Extract a short excerpt from a summary file, skipping frontmatter."""
    full_path = OUTPUT_DIR / relative_file
    if not full_path.exists():
        return ""

    content = full_path.read_text()

    # Strip YAML frontmatter (--- ... ---)
    if content.startswith("---"):
        end = content.find("---", 3)
        if end != -1:
            content = content[end + 3:].strip()

    # Collect non-empty, non-heading, non-separator lines
    text_parts = []
    for line in content.splitlines():
        stripped = line.strip()
        if stripped and not stripped.startswith("#") and stripped != "---":
            text_parts.append(stripped)
        if sum(len(p) for p in text_parts) >= EXCERPT_CHARS:
            break

    return " ".join(text_parts)[:EXCERPT_CHARS]


def build_search_index(weekly_data, monthly_data):
    """Build flat search index entries with excerpts for all weeks and months."""
    entries = []

    for chat in CHATS:
        weeks = weekly_data.get(chat, {})
        months = monthly_data.get(chat, {})

        # Pre-compute: month → list of weekly data dicts
        month_weeks_data = defaultdict(list)
        for wl, data in weeks.items():
            month_weeks_data[data["month"]].append(data)

        # Weekly entries
        for wl, data in sorted(weeks.items()):
            all_topics = [t.get("title", "") for t in data["topics"]]
            all_key_terms = list({
                term
                for t in data["topics"]
                for term in t.get("key_terms", [])
            })
            entries.append({
                "id": f"{chat}__{wl}",
                "channel": chat,
                "period": wl,
                "type": "weekly",
                "month": data["month"],
                "message_count": data["message_count"],
                "topics": all_topics,
                "key_terms": all_key_terms[:50],
                "participants": data["active_participants"][:15],
                "excerpt": get_excerpt(data["summary_file"]),
            })

        # Monthly entries
        for ym, mdata in sorted(months.items()):
            agg_topics = []
            agg_key_terms = set()
            agg_participants = set()
            for wdata in month_weeks_data.get(ym, []):
                agg_topics.extend(t.get("title", "") for t in wdata["topics"])
                for t in wdata["topics"]:
                    agg_key_terms.update(t.get("key_terms", []))
                agg_participants.update(wdata["active_participants"])

            entries.append({
                "id": f"{chat}__{ym}",
                "channel": chat,
                "period": ym,
                "type": "monthly",
                "topics": list(dict.fromkeys(agg_topics))[:20],  # dedup, order-preserving
                "key_terms": list(agg_key_terms)[:50],
                "participants": list(agg_participants)[:20],
                "excerpt": get_excerpt(mdata["summary_file"]),
            })

    return entries


# ---------------------------------------------------------------------------
# Build telegram_topics_index.json
# ---------------------------------------------------------------------------

CATEGORY_LABELS = {
    "technical": "Technical",
    "governance": "Governance",
    "defi": "DeFi",
    "bridges": "Bridges",
    "mining": "Mining",
    "wallet": "Wallets",
    "nft": "NFTs",
    "marketing": "Marketing",
    "ecosystem": "Ecosystem",
    "community": "Community",
}


def build_topics_index(weekly_data):
    """
    Build a category-centric topics index.

    Rather than trying to deduplicate LLM-generated topic titles (which are all
    unique), we aggregate by category and key_term.  Returns a dict with:
    - categories: per-category stats + top key_terms + sample major topics
    - key_terms:  top recurring terms across all categories (for search/tags)
    """
    # Per category: { term_counter, topic_count, channels, major_topics (capped) }
    cat_data = defaultdict(lambda: {
        "term_counter": Counter(),
        "topic_count": 0,
        "channels": set(),
        "major_topics": [],   # (week, channel, title) triples — recent first
    })

    # Global key_term frequency
    global_terms = Counter()

    for chat in CHATS:
        for wl, data in sorted(weekly_data.get(chat, {}).items(), reverse=True):
            for topic in data["topics"]:
                cat = topic.get("category", "other")
                title = topic.get("title", "").strip()
                key_terms = topic.get("key_terms", [])
                significance = topic.get("significance", "minor")

                if not title:
                    continue

                cat_data[cat]["topic_count"] += 1
                cat_data[cat]["channels"].add(chat)
                for term in key_terms:
                    cat_data[cat]["term_counter"][term] += 1
                    global_terms[term] += 1

                # Keep up to 30 major topics per category (most recent first)
                if (
                    significance == "major"
                    and len(cat_data[cat]["major_topics"]) < 30
                ):
                    cat_data[cat]["major_topics"].append({
                        "title": title,
                        "week": wl,
                        "channel": chat,
                    })

    # Build output
    categories = {}
    for cat in sorted(cat_data.keys()):
        d = cat_data[cat]
        top_terms = [term for term, _ in d["term_counter"].most_common(20)]
        categories[cat] = {
            "label": CATEGORY_LABELS.get(cat, cat.title()),
            "topic_count": d["topic_count"],
            "channels": sorted(d["channels"]),
            "key_terms": top_terms,
            "major_topics": d["major_topics"],
        }

    top_key_terms = [
        {"term": term, "count": count}
        for term, count in global_terms.most_common(100)
    ]

    return {"categories": categories, "top_key_terms": top_key_terms}


# ---------------------------------------------------------------------------
# Build telegram_speakers.json
# ---------------------------------------------------------------------------

def normalize_username(username):
    """
    Normalize @username for matching against speakers.json names.
    Strips @, lowercases, removes emoji and non-alphanumeric decorators.
    """
    name = username.lstrip("@").lower().strip()
    cleaned = []
    for ch in name:
        cat = unicodedata.category(ch)
        if cat.startswith("L") or cat.startswith("N") or ch in " _-":
            cleaned.append(ch)
    return "".join(cleaned).strip()


def load_known_speakers():
    """Load lowercase speaker names from ergo-transcripts-web speakers.json."""
    speakers_path = WEB_DATA_DIR / "speakers.json"
    if not speakers_path.exists():
        print(f"  Warning: speakers.json not found at {speakers_path}")
        return set()
    with open(speakers_path) as f:
        speakers = json.load(f)
    return {s["name"].lower().strip() for s in speakers if "name" in s}


def build_speakers_index(weekly_data, known_speakers):
    """
    Build per-username activity stats.

    Inclusion criteria:
    - 5+ weeks as active_participant, OR
    - Name normalizes to a match in speakers.json (known ecosystem participants)
    """
    # username → { weeks: set(chat__week), channels: set, categories: Counter }
    user_data = defaultdict(lambda: {
        "weeks": set(),
        "channels": set(),
        "categories": Counter(),
    })

    for chat in CHATS:
        for wl, data in sorted(weekly_data.get(chat, {}).items()):
            # Record active participation
            for username in data["active_participants"]:
                user_data[username]["weeks"].add(f"{chat}__{wl}")
                user_data[username]["channels"].add(chat)

            # Accumulate category signal from topic participant lists
            for topic in data["topics"]:
                cat = topic.get("category", "")
                for participant in topic.get("participants", []):
                    user_data[participant]["categories"][cat] += 1

    result = {}
    for username, stats in sorted(
        user_data.items(), key=lambda x: -len(x[1]["weeks"])
    ):
        weeks_active = len(stats["weeks"])
        norm = normalize_username(username)

        # Match against known speakers: substring or exact after normalization
        is_known = any(
            norm == k or (len(k) > 3 and (k in norm or norm in k))
            for k in known_speakers
        )

        if weeks_active < MIN_WEEKS_FOR_SPEAKER and not is_known:
            continue

        top_cats = [cat for cat, _ in stats["categories"].most_common(3) if cat]

        result[username] = {
            "display_name": username.lstrip("@"),
            "weeks_active": weeks_active,
            "channels": sorted(stats["channels"]),
            "top_categories": top_cats,
            "known_speaker": is_known,
        }

    return result


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("Loading output data...")
    weekly_data, monthly_data = load_all_data()

    total_weeks = sum(len(v) for v in weekly_data.values())
    total_months = sum(len(v) for v in monthly_data.values())
    truncated = sum(
        1
        for chat in CHATS
        for data in weekly_data.get(chat, {}).values()
        if data.get("_truncated")
    )
    print(f"  {total_weeks} weekly segments, {total_months} monthly summaries loaded")
    if truncated:
        print(f"  {truncated} topics files were truncated (partial extraction used)")

    print("\nBuilding telegram_index.json...")
    index = build_index(weekly_data, monthly_data)

    print("Building telegram_search_index.json...")
    search_index = build_search_index(weekly_data, monthly_data)

    print("Building telegram_topics_index.json...")
    topics_index = build_topics_index(weekly_data)

    print("Building telegram_speakers.json...")
    known_speakers = load_known_speakers()
    speakers = build_speakers_index(weekly_data, known_speakers)

    outputs = [
        ("telegram_index.json", index),
        ("telegram_search_index.json", search_index),
        ("telegram_topics_index.json", topics_index),
        ("telegram_speakers.json", speakers),
    ]

    print()
    for filename, data in outputs:
        path = BASE_DIR / filename
        with open(path, "w") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        size_kb = path.stat().st_size / 1024
        print(f"  ✓ {path.name}  ({size_kb:.0f} KB)")

    print("\n── Summary ─────────────────────────────────────────────")
    for chat in CHATS:
        w = len(weekly_data.get(chat, {}))
        m = len(monthly_data.get(chat, {}))
        print(f"  {chat}: {w} weeks, {m} months")
    n_cats = len(topics_index.get("categories", {}))
    n_terms = len(topics_index.get("top_key_terms", []))
    print(f"  Search entries:  {len(search_index)}")
    print(f"  Topic categories: {n_cats} (with {n_terms} top key_terms)")
    print(f"  Speakers:        {len(speakers)}")

    print("\nNext step — copy into web repo:")
    print("  mkdir -p ~/ergo-transcripts-web/public/data/telegram")
    print("  cp ~/ergo-telegram/telegram_*.json ~/ergo-transcripts-web/public/data/telegram/")
    print("  cp -r ~/ergo-telegram/output/general ~/ergo-telegram/output/developer \\")
    print("        ~/ergo-transcripts-web/public/data/telegram/")


if __name__ == "__main__":
    main()

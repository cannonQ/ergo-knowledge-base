#!/usr/bin/env python3
"""
Telegram Export Parser
======================
Phase 1: Parse Telegram JSON exports into weekly segments for LLM processing.
No API calls — pure Python parsing and chunking.

Usage:
    python pipeline/process_telegram.py --both
    python pipeline/process_telegram.py input/general/result.json --chat general
    python pipeline/process_telegram.py input/developer/result.json --chat developer

Output:
    processing/{chat}/YYYY-WNN.txt   (one file per segment)
"""

import json
import argparse
from pathlib import Path
from datetime import datetime
from collections import defaultdict

BASE_DIR = Path.home() / "ergo-telegram"
PROCESSING_DIR = BASE_DIR / "processing"

MIN_MESSAGES_PER_SEGMENT = 50
MIN_MESSAGE_LENGTH = 5
MAX_MESSAGES_PER_SEGMENT = 2500  # split oversized weeks to stay under 200K token limit

SKIP_MEDIA_TYPES = {
    "sticker", "animation", "video_file",
    "voice_message", "audio_file", "video_message"
}


def extract_text(text_field):
    """Handle dual text format: plain string or entity list."""
    if isinstance(text_field, str):
        return text_field
    elif isinstance(text_field, list):
        parts = []
        for entity in text_field:
            if isinstance(entity, str):
                parts.append(entity)
            elif isinstance(entity, dict):
                parts.append(entity.get("text", ""))
        return "".join(parts)
    return ""


def get_iso_week_key(date_str):
    """Return (iso_year, week_num) from ISO date string."""
    dt = datetime.fromisoformat(date_str)
    iso = dt.isocalendar()
    return (iso[0], iso[1])


def week_key_to_str(year, week):
    return f"{year}-W{week:02d}"


def parse_messages(data):
    """Filter and normalise messages from a Telegram export."""
    messages = []
    for msg in data.get("messages", []):
        if msg.get("type") != "message":
            continue
        if msg.get("media_type") in SKIP_MEDIA_TYPES:
            continue

        text = extract_text(msg.get("text", "")).strip()
        if len(text) < MIN_MESSAGE_LENGTH:
            continue

        # Prefer 'from' (user messages); fall back to 'actor' (forwarded/service)
        sender = msg.get("from") or msg.get("actor") or "Unknown"

        messages.append({
            "id": msg.get("id"),
            "date": msg.get("date"),
            "from": sender,
            "text": text,
            "reply_to": msg.get("reply_to_message_id"),
        })

    return messages


def group_by_week(messages):
    """Group messages into ISO week buckets."""
    weeks = defaultdict(list)
    for msg in messages:
        key = get_iso_week_key(msg["date"])
        weeks[key].append(msg)
    return weeks


def merge_small_weeks(weeks, min_messages=MIN_MESSAGES_PER_SEGMENT):
    """
    Fold weeks below min_messages into the next week chronologically.
    The final week (if still small) folds backward into the previous one.
    """
    sorted_keys = sorted(weeks.keys())
    merged = {}
    carry_key = None
    carry_msgs = []

    for key in sorted_keys:
        msgs = carry_msgs + weeks[key]
        effective_key = carry_key if carry_key else key

        if len(msgs) < min_messages:
            carry_key = effective_key
            carry_msgs = msgs
        else:
            merged[effective_key] = msgs
            carry_key = None
            carry_msgs = []

    # Last chunk is too small — fold backward
    if carry_msgs:
        if merged:
            last_key = sorted(merged.keys())[-1]
            merged[last_key] = merged[last_key] + carry_msgs
        else:
            # Entire export smaller than threshold — keep as-is
            merged[carry_key or sorted_keys[0]] = carry_msgs

    return merged


def split_oversized_segments(merged, max_messages=MAX_MESSAGES_PER_SEGMENT):
    """
    Split any week exceeding max_messages into labelled parts (a, b, c...).
    Returns a new dict keyed by (year, week, part_suffix) where part_suffix
    is '' for normal weeks or 'a'/'b'/'c' for split ones.
    """
    result = {}
    for key, msgs in merged.items():
        if len(msgs) <= max_messages:
            result[(key[0], key[1], "")] = msgs
        else:
            n_parts = (len(msgs) + max_messages - 1) // max_messages
            chunk_size = (len(msgs) + n_parts - 1) // n_parts
            for i in range(n_parts):
                suffix = chr(ord('a') + i)
                chunk = msgs[i * chunk_size:(i + 1) * chunk_size]
                result[(key[0], key[1], suffix)] = chunk
    return result


def week_key_to_str_with_part(year, week, part=""):
    return f"{year}-W{week:02d}{part}"


def format_segment(week_key, messages, chat_name):
    """Format a week's messages as readable text for the LLM."""
    year, week = week_key[0], week_key[1]
    part = week_key[2] if len(week_key) > 2 else ""
    label = week_key_to_str_with_part(year, week, part)
    first_date = messages[0]["date"]
    last_date = messages[-1]["date"]
    participants = sorted(set(m["from"] for m in messages))

    header = [
        f"# Ergo {chat_name} Chat — {label}",
        f"# Period: {first_date[:10]} to {last_date[:10]}",
        f"# Messages: {len(messages)}",
        f"# Participants ({len(participants)}): {', '.join(participants[:20])}",
        "",
    ]

    body = []
    for msg in messages:
        date_str = msg["date"][:16]  # YYYY-MM-DDTHH:MM
        username = msg["from"]
        msg_id = msg["id"]
        text = msg["text"]

        if msg.get("reply_to"):
            body.append(
                f"[{date_str}] @{username} (msg#{msg_id}, reply to #{msg['reply_to']}): {text}"
            )
        else:
            body.append(f"[{date_str}] @{username} (msg#{msg_id}): {text}")

    return "\n".join(header + body)


def process_chat(input_path, chat_name, min_messages=MIN_MESSAGES_PER_SEGMENT, overwrite=False, limit=None):
    """Process a single chat export into weekly segment files."""
    print(f"\n{'='*60}")
    print(f"Processing: {chat_name} chat")
    print(f"Input:      {input_path}")

    with open(input_path) as f:
        data = json.load(f)

    total = len(data.get("messages", []))
    print(f"Total messages in export: {total:,}")

    messages = parse_messages(data)
    if limit:
        messages = messages[:limit]
        print(f"After filtering:          {len(messages):,} messages (limited to {limit})")
    else:
        print(f"After filtering:          {len(messages):,} messages")

    weeks = group_by_week(messages)
    print(f"ISO week buckets:         {len(weeks)}")

    merged = merge_small_weeks(weeks, min_messages)
    print(f"After merging small weeks:{len(merged)} segments")

    segments = split_oversized_segments(merged)
    n_split = sum(1 for k in segments if k[2] != "")
    if n_split:
        print(f"After splitting oversized: {len(segments)} segments ({n_split} parts from large weeks)")

    output_dir = PROCESSING_DIR / chat_name
    output_dir.mkdir(parents=True, exist_ok=True)

    written = skipped = 0
    for seg_key, msgs in sorted(segments.items()):
        year, week, part = seg_key
        filename = week_key_to_str_with_part(year, week, part) + ".txt"
        output_path = output_dir / filename

        if output_path.exists() and not overwrite:
            skipped += 1
            continue

        content = format_segment(seg_key, msgs, chat_name.title())
        output_path.write_text(content)
        written += 1

    all_keys = sorted(segments.keys())
    print(f"\nWritten:  {written} segment files")
    if skipped:
        print(f"Skipped:  {skipped} already exist (use --overwrite to regenerate)")
    first = all_keys[0]
    last = all_keys[-1]
    print(f"Range:    {week_key_to_str_with_part(*first)} → {week_key_to_str_with_part(*last)}")
    print(f"Output:   {output_dir}/")

    # Summary stats
    msg_counts = [len(v) for v in segments.values()]
    print(f"\nSegment sizes: min={min(msg_counts)}, max={max(msg_counts)}, avg={sum(msg_counts)//len(msg_counts)}")


def print_stats(input_path, chat_name):
    """Print stats about an export without writing files."""
    with open(input_path) as f:
        data = json.load(f)

    messages = parse_messages(data)
    weeks = group_by_week(messages)
    merged = merge_small_weeks(weeks)

    print(f"\n{chat_name} chat stats:")
    print(f"  Filtered messages: {len(messages):,}")
    print(f"  Segments:          {len(merged)}")

    # Show distribution by year
    from collections import Counter
    year_counts = Counter()
    for (year, _), msgs in merged.items():
        year_counts[year] += len(msgs)
    for year in sorted(year_counts):
        print(f"  {year}: {year_counts[year]:,} messages")


def main():
    parser = argparse.ArgumentParser(
        description="Parse Telegram exports into weekly segments"
    )
    parser.add_argument("input", nargs="?", help="Path to result.json")
    parser.add_argument("--chat", choices=["general", "developer"], help="Chat name")
    parser.add_argument(
        "--both", action="store_true",
        help="Process both chats from default locations (input/general/ and input/developer/)"
    )
    parser.add_argument(
        "--min-messages", type=int, default=MIN_MESSAGES_PER_SEGMENT,
        help=f"Minimum messages per segment before merging (default: {MIN_MESSAGES_PER_SEGMENT})"
    )
    parser.add_argument(
        "--stats", action="store_true",
        help="Print stats only, don't write files"
    )
    parser.add_argument(
        "--overwrite", action="store_true",
        help="Overwrite existing segment files"
    )
    parser.add_argument(
        "--limit", type=int,
        help="Only process the first N messages (for testing)"
    )

    args = parser.parse_args()

    if args.both:
        for chat_name in ["general", "developer"]:
            path = BASE_DIR / "input" / chat_name / "result.json"
            if path.exists():
                if args.stats:
                    print_stats(path, chat_name)
                else:
                    process_chat(path, chat_name, args.min_messages, args.overwrite, args.limit)
            else:
                print(f"Not found: {path}")

    elif args.input and args.chat:
        input_path = Path(args.input)
        if args.stats:
            print_stats(input_path, args.chat)
        else:
            process_chat(input_path, args.chat, args.min_messages, args.overwrite, args.limit)

    else:
        parser.print_help()
        print("\nExamples:")
        print("  python pipeline/process_telegram.py --both")
        print("  python pipeline/process_telegram.py --both --stats")
        print("  python pipeline/process_telegram.py input/general/result.json --chat general")


if __name__ == "__main__":
    main()

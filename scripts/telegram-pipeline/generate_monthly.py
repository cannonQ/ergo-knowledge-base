#!/usr/bin/env python3
"""
Generate Monthly Summaries
===========================
Phase 3: Reduce weekly summary files into monthly summary .md files.
Reads output/{chat}/segments/YYYY-WNN_summary.md files,
groups them by calendar month, and sends each month to Claude.

Uses direct API (not batch) since monthly summaries are fast and few.

Usage:
    # Generate all missing monthly summaries
    python pipeline/generate_monthly.py general
    python pipeline/generate_monthly.py developer
    python pipeline/generate_monthly.py both

    # Specific year/month
    python pipeline/generate_monthly.py general --year 2023
    python pipeline/generate_monthly.py general --month 2023-03

    # Preview what would be generated (dry run)
    python pipeline/generate_monthly.py both --dry-run

Output:
    output/{chat}/summaries/YYYY-MM.md
"""

import sys
import argparse
from pathlib import Path
from datetime import datetime, date
from collections import defaultdict

sys.path.insert(0, str(Path(__file__).parent))
from claude_prompts import run_monthly_summary

BASE_DIR = Path.home() / "ergo-telegram"
OUTPUT_DIR = BASE_DIR / "output"


def strip_part_suffix(week_label):
    """Strip trailing part suffix (a/b/c) from labels like '2021-W31a' → '2021-W31'."""
    if week_label and week_label[-1].isalpha() and not week_label[-1].isdigit():
        return week_label[:-1]
    return week_label


def week_label_to_dates(week_label):
    """
    Return (start_date, end_date) for an ISO week label like '2023-W09'.
    Uses Monday as start of week. Handles part suffixes (e.g. '2021-W31a').
    """
    week_label = strip_part_suffix(week_label)
    year_str, week_str = week_label.split("-W")
    year = int(year_str)
    week = int(week_str)
    # ISO week: Monday is day 1
    start = date.fromisocalendar(year, week, 1)
    end = date.fromisocalendar(year, week, 7)
    return start, end


def week_label_to_month(week_label):
    """
    Map a week label to its dominant calendar month.
    Uses the Thursday of the week (ISO standard for week's year).
    Handles part suffixes (e.g. '2021-W31a' → same month as '2021-W31').
    """
    week_label = strip_part_suffix(week_label)
    year_str, week_str = week_label.split("-W")
    year = int(year_str)
    week = int(week_str)
    # Thursday = day 4 in ISO calendar
    thursday = date.fromisocalendar(year, week, 4)
    return thursday.strftime("%Y-%m")


def get_weekly_summaries(chat):
    """
    Return dict: { 'YYYY-MM': [Path, Path, ...] }
    Grouped by the month each week's Thursday falls in.
    """
    segments_dir = OUTPUT_DIR / chat / "segments"
    if not segments_dir.exists():
        return {}

    months = defaultdict(list)
    for path in sorted(segments_dir.glob("*_summary.md")):
        week_label = path.stem.replace("_summary", "")  # e.g. "2023-W09"
        if not week_label[0].isdigit():
            continue
        month = week_label_to_month(week_label)
        months[month].append(path)

    return dict(months)


def is_monthly_done(chat, year_month):
    """Check if monthly summary already exists."""
    return (OUTPUT_DIR / chat / "summaries" / f"{year_month}.md").exists()


def generate_for_chat(chat, year=None, month=None, dry_run=False, overwrite=False):
    """Generate monthly summaries for a single chat."""
    chat_name = {"general": "General", "developer": "Developer"}.get(chat, chat.title())
    months = get_weekly_summaries(chat)

    if not months:
        print(f"  {chat}: No weekly summaries found in {OUTPUT_DIR / chat / 'segments'}/")
        print(f"          Run batch_api.py first.")
        return

    # Filter by year or month if specified
    if month:
        months = {k: v for k, v in months.items() if k == month}
    elif year:
        months = {k: v for k, v in months.items() if k.startswith(str(year))}

    output_dir = OUTPUT_DIR / chat / "summaries"
    output_dir.mkdir(parents=True, exist_ok=True)

    generated = skipped = 0

    for year_month in sorted(months.keys()):
        weekly_paths = months[year_month]
        out_path = output_dir / f"{year_month}.md"

        if not overwrite and out_path.exists():
            skipped += 1
            continue

        if dry_run:
            print(f"  Would generate: {year_month} from {len(weekly_paths)} weeks")
            continue

        print(f"  Generating {year_month} from {len(weekly_paths)} weekly summaries...")
        try:
            result = run_monthly_summary(weekly_paths, chat_name, year_month)

            # Prepend YAML frontmatter
            frontmatter = build_frontmatter(chat, year_month, weekly_paths)
            full_content = frontmatter + "\n" + result

            out_path.write_text(full_content)
            print(f"  ✓ {out_path.relative_to(BASE_DIR)}")
            generated += 1

        except Exception as e:
            print(f"  ✗ {year_month}: {e}")

    if not dry_run:
        print(f"\n  {chat}: {generated} generated, {skipped} already exist")


def build_frontmatter(chat, year_month, weekly_paths):
    """Build YAML frontmatter for a monthly summary file."""
    year, month = year_month.split("-")
    chat_slug = "main" if chat == "general" else "dev"

    # Derive date range from weekly files
    week_labels = [p.stem.replace("_summary", "") for p in weekly_paths]

    # First day of month, last day of month
    first_day = f"{year_month}-01"
    import calendar
    last_day_num = calendar.monthrange(int(year), int(month))[1]
    last_day = f"{year_month}-{last_day_num:02d}"

    segment_refs = "\n".join(f"  - segments/{chat}/{wl}.md" for wl in sorted(week_labels))

    return f"""---
title: "Ergo {chat.title()} Chat Summary — {datetime.strptime(year_month, '%Y-%m').strftime('%B %Y')}"
type: monthly_summary
chat: {chat_slug}
date_range: [{first_day}, {last_day}]
source: telegram
segment_files:
{segment_refs}
---
"""


def main():
    parser = argparse.ArgumentParser(
        description="Generate monthly summaries from weekly segment summaries"
    )
    parser.add_argument(
        "chat", choices=["general", "developer", "both"],
        help="Which chat to process"
    )
    parser.add_argument("--year", type=int, help="Only process this year")
    parser.add_argument("--month", help="Only process this month (YYYY-MM)")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be generated")
    parser.add_argument("--overwrite", action="store_true", help="Regenerate existing summaries")

    args = parser.parse_args()

    chats = ["general", "developer"] if args.chat == "both" else [args.chat]

    for chat in chats:
        print(f"\n{'='*50}")
        print(f"Chat: {chat}")
        generate_for_chat(
            chat,
            year=args.year,
            month=args.month,
            dry_run=args.dry_run,
            overwrite=args.overwrite,
        )


if __name__ == "__main__":
    main()

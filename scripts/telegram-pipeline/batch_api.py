#!/usr/bin/env python3
"""
Batch API — Telegram Pipeline
==============================
Submits weekly segment files to the Anthropic Batch API for 50% cost savings.
Processes: weekly_summary + weekly_topics for each segment.

Usage:
    # Submit all unprocessed segments
    python pipeline/batch_api.py --submit general
    python pipeline/batch_api.py --submit developer
    python pipeline/batch_api.py --submit both

    # Submit specific year only
    python pipeline/batch_api.py --submit general --year 2023

    # Check batch status
    python pipeline/batch_api.py --status <BATCH_ID>

    # Download results when complete
    python pipeline/batch_api.py --download <BATCH_ID>

Output:
    output/{chat}/segments/YYYY-WNN_summary.md
    output/{chat}/segments/YYYY-WNN_topics.json
"""

import os
import sys
import json
import time
import argparse
from pathlib import Path
from datetime import datetime

import anthropic

sys.path.insert(0, str(Path(__file__).parent))
from claude_prompts import MODEL, MONTHLY_MODEL, get_weekly_summary_prompt, get_weekly_topics_prompt

BASE_DIR = Path.home() / "ergo-telegram"
PROCESSING_DIR = BASE_DIR / "processing"
OUTPUT_DIR = BASE_DIR / "output"
BATCH_DIR = BASE_DIR / "batches"

client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))


def get_chat_name(chat):
    """Return display name for a chat slug."""
    return {"general": "General", "developer": "Developer"}.get(chat, chat.title())


def get_segment_files(chat, year=None):
    """Return sorted list of .txt segment files for a chat, optionally filtered by year."""
    segment_dir = PROCESSING_DIR / chat
    if not segment_dir.exists():
        return []

    files = sorted(segment_dir.glob("*.txt"))
    if year:
        files = [f for f in files if f.stem.startswith(str(year))]
    return files


def is_processed(chat, week_label):
    """Check if both output files already exist for this segment."""
    summary = OUTPUT_DIR / chat / "segments" / f"{week_label}_summary.md"
    topics = OUTPUT_DIR / chat / "segments" / f"{week_label}_topics.json"
    return summary.exists() and topics.exists()


def create_batch_requests(chats, year=None, overwrite=False):
    """Build batch request list from segment files."""
    requests = []

    for chat in chats:
        chat_name = get_chat_name(chat)
        files = get_segment_files(chat, year)

        if not files:
            print(f"  {chat}: No segment files found in {PROCESSING_DIR / chat}/")
            continue

        skipped = 0
        added = 0
        for segment_file in files:
            week_label = segment_file.stem  # e.g. "2023-W09"

            if not overwrite and is_processed(chat, week_label):
                skipped += 1
                continue

            segment_text = segment_file.read_text()

            # Route large segments to Sonnet to avoid truncation and improve quality
            msg_count = 0
            for line in segment_text.splitlines()[:5]:
                if line.startswith("# Messages:"):
                    msg_count = int(line.split(":")[1].strip())
                    break
            seg_model = MONTHLY_MODEL if msg_count >= 1500 else MODEL
            seg_summary_tokens = 8000 if msg_count >= 1500 else 4000

            # Weekly summary request
            requests.append({
                "custom_id": f"{chat}__{week_label}__summary",
                "params": {
                    "model": seg_model,
                    "max_tokens": seg_summary_tokens,
                    "messages": [{
                        "role": "user",
                        "content": get_weekly_summary_prompt(segment_text, chat_name, week_label)
                    }]
                }
            })

            # Weekly topics request
            requests.append({
                "custom_id": f"{chat}__{week_label}__topics",
                "params": {
                    "model": seg_model,
                    "max_tokens": 2000,
                    "messages": [{
                        "role": "user",
                        "content": get_weekly_topics_prompt(segment_text, chat_name, week_label)
                    }]
                }
            })

            added += 1

        print(f"  {chat}: {added} segments queued, {skipped} already processed")

    return requests


def submit_batch(requests):
    """Submit batch to Anthropic API and save tracking info."""
    BATCH_DIR.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    jsonl_path = BATCH_DIR / f"batch_{timestamp}.jsonl"

    with open(jsonl_path, "w") as f:
        for req in requests:
            f.write(json.dumps(req) + "\n")

    print(f"\nCreated {jsonl_path} with {len(requests)} requests")
    print("Submitting to Anthropic Batch API...")

    batch = client.messages.batches.create(requests=requests)

    info = {
        "batch_id": batch.id,
        "created_at": datetime.now().isoformat(),
        "jsonl_file": str(jsonl_path),
        "request_count": len(requests),
        "status": batch.processing_status,
    }
    info_path = BATCH_DIR / f"batch_{timestamp}_info.json"
    with open(info_path, "w") as f:
        json.dump(info, f, indent=2)

    print(f"\n✓ Batch submitted!")
    print(f"  Batch ID: {batch.id}")
    print(f"  Requests: {len(requests)} ({len(requests) // 2} segments × 2 prompts)")
    print(f"  Status:   {batch.processing_status}")
    print(f"  Info:     {info_path}")
    print(f"\nCheck status:  python pipeline/batch_api.py --status {batch.id}")
    print(f"Download when ready:  python pipeline/batch_api.py --download {batch.id}")

    return batch.id


def check_status(batch_id):
    """Check and display batch status."""
    batch = client.messages.batches.retrieve(batch_id)

    print(f"\nBatch:   {batch_id}")
    print(f"Status:  {batch.processing_status}")
    print(f"Created: {batch.created_at}")

    if hasattr(batch, "request_counts"):
        c = batch.request_counts
        print(f"Requests: {c.processing} processing, {c.succeeded} succeeded, {c.errored} errored")

    if batch.processing_status == "ended":
        print(f"\n✓ Complete! Download with:")
        print(f"  python pipeline/batch_api.py --download {batch_id}")

    return batch.processing_status


def download_results(batch_id):
    """Download batch results and write to output/{chat}/segments/."""
    batch = client.messages.batches.retrieve(batch_id)

    if batch.processing_status != "ended":
        print(f"Batch not complete yet. Status: {batch.processing_status}")
        return

    print(f"Downloading results for {batch_id}...")

    success = failed = 0

    for result in client.messages.batches.results(batch_id):
        custom_id = result.custom_id  # e.g. "general__2023-W09__summary"

        if result.result.type != "succeeded":
            error_info = f" [type={result.result.type}]"
            if hasattr(result.result, "error") and result.result.error:
                error_info += f" {repr(result.result.error)}"
            print(f"  ✗ Failed: {custom_id}{error_info}")
            failed += 1
            continue

        text = result.result.message.content[0].text

        # Parse custom_id: {chat}__{week}__{type}
        parts = custom_id.split("__")
        if len(parts) != 3:
            print(f"  ? Unexpected custom_id format: {custom_id}")
            continue

        chat, week_label, prompt_type = parts

        output_dir = OUTPUT_DIR / chat / "segments"
        output_dir.mkdir(parents=True, exist_ok=True)

        if prompt_type == "summary":
            out_path = output_dir / f"{week_label}_summary.md"
        elif prompt_type == "topics":
            out_path = output_dir / f"{week_label}_topics.json"
            # Strip code fences if model wrapped JSON in ```json ... ```
            if text.startswith("```"):
                lines = text.splitlines()
                if lines[0].startswith("```"):
                    lines = lines[1:]   # drop opening ```json line
                if lines and lines[-1].strip() == "```":
                    lines = lines[:-1]  # drop closing ``` line
                text = "\n".join(lines).strip()
        else:
            print(f"  ? Unknown prompt type: {prompt_type}")
            continue

        out_path.write_text(text)
        print(f"  ✓ {out_path.relative_to(BASE_DIR)}")
        success += 1

    print(f"\n✓ Download complete: {success} succeeded, {failed} failed")


def poll_and_download(batch_id, poll_interval=60):
    """Poll until complete, then download."""
    print(f"Polling {batch_id} every {poll_interval}s...")
    while True:
        status = check_status(batch_id)
        if status == "ended":
            download_results(batch_id)
            break
        elif status in ("failed", "expired", "canceled"):
            print(f"Batch {status}.")
            break
        print(f"Still processing... waiting {poll_interval}s")
        time.sleep(poll_interval)


def main():
    parser = argparse.ArgumentParser(description="Batch API for Ergo Telegram segments")
    parser.add_argument(
        "--submit", metavar="CHAT",
        help="Submit batch for 'general', 'developer', or 'both'"
    )
    parser.add_argument("--year", type=int, help="Only process segments from this year")
    parser.add_argument("--overwrite", action="store_true", help="Re-process already-done segments")
    parser.add_argument("--status", metavar="BATCH_ID", help="Check batch status")
    parser.add_argument("--download", metavar="BATCH_ID", help="Download batch results")
    parser.add_argument("--run", metavar="CHAT", help="Submit + poll + download")

    args = parser.parse_args()

    if args.status:
        check_status(args.status)

    elif args.download:
        download_results(args.download)

    elif args.submit or args.run:
        chat_arg = args.submit or args.run
        chats = ["general", "developer"] if chat_arg == "both" else [chat_arg]

        print(f"Building batch requests for: {', '.join(chats)}")
        if args.year:
            print(f"Year filter: {args.year}")

        requests = create_batch_requests(chats, year=args.year, overwrite=args.overwrite)

        if not requests:
            print("\nNo segments to process. Run process_telegram.py first.")
            return

        batch_id = submit_batch(requests)

        if args.run:
            poll_and_download(batch_id)

    else:
        parser.print_help()


if __name__ == "__main__":
    main()

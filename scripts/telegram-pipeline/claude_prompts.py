#!/usr/bin/env python3
"""
Claude Prompts — Telegram Pipeline
====================================
All Claude API calls for Telegram segment processing.

Two prompt types:
  weekly_summary  — Summarise one week of chat into structured Markdown
  monthly_summary — Reduce 4-5 weekly summaries into one monthly summary

Prompt caching: static prefix (glossary + speakers + instructions) is marked
with cache_control so repeated batch requests only pay the read rate (~0.1x).
"""

import os
import sys
import json
from pathlib import Path

import anthropic

# Reuse glossary/speakers from ergo-transcripts config
sys.path.insert(0, str(Path.home() / "ergo-transcripts" / "pipeline"))
from config_loader import format_glossary_for_prompt, format_speakers_for_prompt

client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

MODEL = "claude-haiku-4-5-20251001"  # weekly bulk (cheap)
MONTHLY_MODEL = "claude-sonnet-4-6"  # monthly synthesis (quality)


def _glossary_block():
    return format_glossary_for_prompt()


def _speakers_block():
    return format_speakers_for_prompt()


# ---------------------------------------------------------------------------
# Weekly summary prompt
# ---------------------------------------------------------------------------

# Static prefix — identical across all weekly summary requests.
# Built once at import time so it's not re-concatenated per request.
_WEEKLY_SUMMARY_STATIC = None

def _weekly_summary_static():
    global _WEEKLY_SUMMARY_STATIC
    if _WEEKLY_SUMMARY_STATIC is None:
        _WEEKLY_SUMMARY_STATIC = f"""You are processing archived Ergo blockchain Telegram chat logs for a developer knowledge base.

**Known Ergo ecosystem participants:**
{_speakers_block()}

**Ergo terminology (use exact terms):**
{_glossary_block()}

---

Produce a structured Markdown summary with the following sections.
Only include a section if there is relevant content — omit empty sections entirely.

## Key Topics Discussed
For each distinct technical topic: a bullet with a 2-3 sentence summary.
Be specific — "Oracle pool v2 reward distribution" not "oracle discussion".

## Important Decisions or Announcements
Decisions made, releases announced, proposals introduced, or roadmap updates confirmed.
Format: `- [@username, msg#ID, YYYY-MM-DD]: Statement`

## Technical Q&A Worth Preserving
Questions asked and answers given that a future developer would find useful.
Only include exchanges with genuine technical or strategic value.
Format:
- **Q** (@asker): Question
  **A** (@responder): Answer

## Links Shared
URLs with context about what they contain.
Format: `- [URL]: context`

## Unresolved Questions
Topics raised but not resolved, debates left open, things flagged as TBD.

---

**Guidelines:**
- Preserve exact usernames (with @), message IDs, and dates for citation
- Use exact Ergo terminology — ErgoScript not "ergo script", eUTXO not "extended UTXO"
- Skip greetings, spam, price talk, off-topic chatter
- Be concise — this is a reference document, not a narrative
- If the week was low-activity or mostly noise, a short summary is fine"""
    return _WEEKLY_SUMMARY_STATIC


def get_weekly_summary_prompt(segment_text, chat_name, week_label):
    """
    Returns content blocks with prompt caching on the static prefix.
    The glossary + speakers + instructions are cached; only the segment is dynamic.
    """
    return [
        {
            "type": "text",
            "text": _weekly_summary_static(),
            "cache_control": {"type": "ephemeral"},
        },
        {
            "type": "text",
            "text": f"**Chat:** Ergo {chat_name}\n**Week:** {week_label}\n\n**Chat segment:**\n{segment_text}",
        },
    ]


# ---------------------------------------------------------------------------
# Weekly topics prompt (JSON)
# ---------------------------------------------------------------------------

_WEEKLY_TOPICS_STATIC = None

def _weekly_topics_static():
    global _WEEKLY_TOPICS_STATIC
    if _WEEKLY_TOPICS_STATIC is None:
        _WEEKLY_TOPICS_STATIC = """Extract topic tags from an Ergo blockchain Telegram chat segment for a searchable knowledge base index.

**Output JSON format:**
{
  "chat": "<chat name>",
  "week": "<week label>",
  "topics": [
    {
      "title": "Specific topic title (5-10 words)",
      "category": "technical|governance|defi|bridges|mining|wallet|nft|marketing|ecosystem|community",
      "key_terms": ["term1", "term2", "term3"],
      "participants": ["@username1", "@username2"],
      "significance": "major|minor"
    }
  ],
  "active_participants": ["@username1", "@username2"],
  "message_count": 0
}

**Guidelines:**
- Be specific in titles: "Oracle pool v2 connector API" not "Oracle discussion"
- Only include topics with at least a few substantive messages
- major = architectural, release, or widely-discussed; minor = brief mention
- active_participants: anyone who sent more than 2 messages this week
- message_count: total messages in the segment header

Output valid JSON only."""
    return _WEEKLY_TOPICS_STATIC


def get_weekly_topics_prompt(segment_text, chat_name, week_label):
    """
    Returns content blocks with prompt caching on the static instructions.
    """
    return [
        {
            "type": "text",
            "text": _weekly_topics_static(),
            "cache_control": {"type": "ephemeral"},
        },
        {
            "type": "text",
            "text": f"**Chat:** Ergo {chat_name}\n**Week:** {week_label}\n\n**Chat segment:**\n{segment_text}",
        },
    ]


# ---------------------------------------------------------------------------
# Monthly summary prompt
# ---------------------------------------------------------------------------

_MONTHLY_STATIC = None

def _monthly_static():
    global _MONTHLY_STATIC
    if _MONTHLY_STATIC is None:
        _MONTHLY_STATIC = f"""You are creating a monthly summary for a developer knowledge base from weekly Telegram chat summaries.

**Ergo terminology (use exact terms):**
{_glossary_block()}

---

Produce a comprehensive monthly Markdown summary with these sections:

## Executive Summary
2-3 sentences: what were the dominant themes of this month?

## Key Topics This Month
For each significant topic: 3-4 sentence summary synthesising discussion across weeks.
Group related weekly discussions together — don't just repeat each week.

## Decisions & Announcements
Significant decisions made, releases shipped, or major announcements.
Format: `- [@username, YYYY-MM-DD]: Statement`

## Technical Q&A Worth Preserving
The highest-value Q&A exchanges from across the month.
Format:
- **Q** (@asker, YYYY-MM-DD): Question
  **A** (@responder): Answer

## Active Contributors This Month
Notable participants and what they contributed (1 line each).

## Open Questions Entering Next Month
Unresolved debates or TBDs that carried through the month.

## Key Links
Most important URLs shared, with context.

---

**Guidelines:**
- Synthesise across weeks — don't just concatenate
- Preserve message citations (@username, msg#ID, YYYY-MM-DD) for important quotes
- Use exact Ergo terminology throughout
- Omit sections that have no meaningful content"""
    return _MONTHLY_STATIC


def get_monthly_summary_prompt(weekly_summaries_text, chat_name, year_month):
    """
    Returns content blocks with prompt caching on the static prefix (glossary + instructions).
    """
    return [
        {
            "type": "text",
            "text": _monthly_static(),
            "cache_control": {"type": "ephemeral"},
        },
        {
            "type": "text",
            "text": f"**Chat:** Ergo {chat_name}\n**Month:** {year_month}\n\n**Weekly summaries for this month:**\n{weekly_summaries_text}",
        },
    ]


# ---------------------------------------------------------------------------
# Direct (non-batch) API calls — for testing single segments
# ---------------------------------------------------------------------------

def run_weekly_summary(segment_path, chat_name, week_label):
    """Run weekly summary prompt directly (not via batch API)."""
    segment_text = Path(segment_path).read_text()
    content = get_weekly_summary_prompt(segment_text, chat_name, week_label)

    print(f"Running weekly summary for {week_label}...")
    response = client.messages.create(
        model=MODEL,
        max_tokens=4000,
        messages=[{"role": "user", "content": content}]
    )
    return response.content[0].text


def run_weekly_topics(segment_path, chat_name, week_label):
    """Run weekly topics extraction directly (not via batch API)."""
    segment_text = Path(segment_path).read_text()
    content = get_weekly_topics_prompt(segment_text, chat_name, week_label)

    print(f"Running weekly topics for {week_label}...")
    response = client.messages.create(
        model=MODEL,
        max_tokens=2000,
        messages=[{"role": "user", "content": content}]
    )
    return response.content[0].text


def run_monthly_summary(weekly_summary_paths, chat_name, year_month):
    """Run monthly summary prompt directly (not via batch API)."""
    parts = []
    for path in sorted(weekly_summary_paths):
        week_label = Path(path).stem.replace("_summary", "")
        content = Path(path).read_text()
        parts.append(f"### {week_label}\n{content}")

    combined = "\n\n---\n\n".join(parts)
    content = get_monthly_summary_prompt(combined, chat_name, year_month)

    print(f"Running monthly summary for {year_month}...")
    response = client.messages.create(
        model=MONTHLY_MODEL,
        max_tokens=6000,
        messages=[{"role": "user", "content": content}]
    )
    return response.content[0].text


if __name__ == "__main__":
    print(f"Claude Prompts (Telegram) loaded. Model: {MODEL}, Monthly: {MONTHLY_MODEL}")

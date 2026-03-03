#!/usr/bin/env python3
"""
Fetch ecosystem repos via GitHub API and generate structured documentation using an LLM.

For each repo in ecosystem_repos.yaml:
  1. Fetch file tree via GitHub API (no local clone needed)
  2. Find all ErgoScript contracts (.es/.ergo files)
  3. Find cross-cutting patterns in non-ErgoScript code (regex on fetched files)
  4. Fetch README.md and /docs or /spec directory content
  5. Send each contract to the LLM for structured analysis
  6. Generate a per-project overview document
  7. Write all output to content/ecosystem/{project}/ with frontmatter

Usage:
  python3 scripts/clone_and_process_repos.py
  python3 scripts/clone_and_process_repos.py --dry-run
  python3 scripts/clone_and_process_repos.py --repo arkadianet/citadel
  python3 scripts/clone_and_process_repos.py --priority high

Requirements:
  pip install anthropic pyyaml
  GITHUB_TOKEN env var (for 5000 req/hr vs 60 unauthenticated)
  ANTHROPIC_API_KEY env var
"""

import argparse
import json
import os
import re
import sys
import textwrap
import time
import urllib.error
import urllib.request
from datetime import date
from pathlib import Path

try:
    import yaml
except ImportError:
    sys.exit("PyYAML required: pip install pyyaml")

try:
    import anthropic
except ImportError:
    sys.exit("Anthropic SDK required: pip install anthropic")


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).parent.parent.resolve()
CATALOG_PATH = Path(__file__).parent / "ecosystem_repos.yaml"
GLOSSARY_PATH = REPO_ROOT / "glossary" / "ergo_glossary_compact.yaml"
TODAY = date.today().isoformat()

GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
GITHUB_API = "https://api.github.com"
RAW_BASE = "https://raw.githubusercontent.com"

# ErgoScript file extensions
ERGOSCRIPT_EXTENSIONS = {".es", ".ergo"}

# Dirs to skip when traversing the repo tree
SKIP_DIRS = {"node_modules", "target", ".git", "build", "dist", "vendor"}

# Max chars to send per contract file to the LLM (keeps costs down)
MAX_CONTRACT_CHARS = 8_000

# Max chars for README / docs to summarize
MAX_README_CHARS = 12_000

# Max source files to fetch when searching for patterns (bounds API calls)
MAX_PATTERN_FETCH = 40

# LLM model selection
OVERVIEW_MODEL = "claude-sonnet-4-6"          # per-project overview (more context needed)
CONTRACT_MODEL = "claude-haiku-4-5-20251001"  # per-contract analysis (short, cheap)


# ---------------------------------------------------------------------------
# GitHub API helpers
# ---------------------------------------------------------------------------

def _gh_request(url: str) -> bytes:
    """Make a GitHub API GET request, returning raw response bytes."""
    req = urllib.request.Request(url)
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("X-GitHub-Api-Version", "2022-11-28")
    if GITHUB_TOKEN:
        req.add_header("Authorization", f"Bearer {GITHUB_TOKEN}")
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read()


def get_default_branch(org: str, repo: str) -> str:
    """Return the default branch name (usually 'main' or 'master')."""
    data = json.loads(_gh_request(f"{GITHUB_API}/repos/{org}/{repo}"))
    return data.get("default_branch", "main")


def fetch_repo_tree(org: str, repo: str, branch: str) -> list[dict]:
    """
    Return the full recursive blob list for a repo.
    Each item: {"path": str, "type": "blob"|"tree", "sha": str}
    """
    url = f"{GITHUB_API}/repos/{org}/{repo}/git/trees/{branch}?recursive=1"
    data = json.loads(_gh_request(url))
    if data.get("truncated"):
        print(f"    WARNING: file tree truncated for {org}/{repo} — large repo, some files may be missed")
    return [item for item in data.get("tree", []) if item["type"] == "blob"]


def fetch_raw(org: str, repo: str, branch: str, path: str) -> str:
    """Fetch raw file content from GitHub. Returns empty string on 404."""
    url = f"{RAW_BASE}/{org}/{repo}/{branch}/{path}"
    req = urllib.request.Request(url)
    if GITHUB_TOKEN:
        req.add_header("Authorization", f"Bearer {GITHUB_TOKEN}")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.read().decode(errors="ignore")
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return ""
        raise


# ---------------------------------------------------------------------------
# File tree utilities
# ---------------------------------------------------------------------------

def is_skipped(path: str) -> bool:
    """Return True if any path component is in SKIP_DIRS."""
    return any(part in SKIP_DIRS for part in path.split("/"))


def find_ergoscript_paths(tree: list[dict]) -> list[str]:
    """Return paths of ErgoScript files (.es, .ergo) from the tree."""
    return [
        item["path"] for item in tree
        if not is_skipped(item["path"])
        and Path(item["path"]).suffix in ERGOSCRIPT_EXTENSIONS
    ]


def _candidate_paths(tree: list[dict], languages: list[str]) -> list[str]:
    """Return source file paths matching the target languages."""
    ext_map = {
        "typescript": [".ts", ".tsx"],
        "javascript": [".js", ".jsx"],
        "scala":      [".scala"],
        "rust":       [".rs"],
        "python":     [".py"],
        "kotlin":     [".kt"],
        "java":       [".java"],
    }
    target_exts: set[str] = set()
    for lang in languages:
        target_exts.update(ext_map.get(lang.lower(), []))
    if not target_exts:
        return []
    return [
        item["path"] for item in tree
        if not is_skipped(item["path"])
        and Path(item["path"]).suffix in target_exts
    ]


def find_pattern_matches(org: str, repo: str, branch: str,
                         tree: list[dict], patterns: list[str],
                         languages: list[str]) -> list[dict]:
    """Fetch candidate source files and search for pattern keywords."""
    if not patterns:
        return []
    candidates = _candidate_paths(tree, languages)
    if not candidates:
        return []

    regex = re.compile("|".join(re.escape(p) for p in patterns))
    matches = []
    fetched = 0

    for path in candidates:
        if fetched >= MAX_PATTERN_FETCH:
            break
        content = fetch_raw(org, repo, branch, path)
        fetched += 1
        found = regex.findall(content)
        if found:
            matches.append({
                "file": path,
                "patterns_found": list(set(found)),
                "snippet": _extract_snippet(content, regex),
            })
        if len(matches) >= 20:
            break

    return matches


def _extract_snippet(content: str, regex: re.Pattern, context: int = 5) -> str:
    """Extract up to 2*context+1 lines around the first pattern match."""
    lines = content.splitlines()
    for i, line in enumerate(lines):
        if regex.search(line):
            start = max(0, i - context)
            end = min(len(lines), i + context + 1)
            return "\n".join(lines[start:end])
    return ""


def read_readme(org: str, repo: str, branch: str, tree: list[dict]) -> str:
    """Fetch and return README content (first match found)."""
    paths_in_tree = {item["path"] for item in tree}
    for name in ("README.md", "readme.md", "README.rst", "README"):
        if name in paths_in_tree:
            return fetch_raw(org, repo, branch, name)[:MAX_README_CHARS]
    return ""


def read_docs(org: str, repo: str, branch: str, tree: list[dict]) -> str:
    """Fetch and concatenate markdown files from docs/spec directories."""
    doc_dirs = {"docs", "spec", "specifications", "documentation"}
    md_paths = sorted(
        item["path"] for item in tree
        if not is_skipped(item["path"])
        and Path(item["path"]).suffix == ".md"
        and item["path"].split("/")[0] in doc_dirs
    )
    collected = []
    total = 0
    for path in md_paths:
        if total >= MAX_README_CHARS:
            break
        text = fetch_raw(org, repo, branch, path)
        if total + len(text) > MAX_README_CHARS:
            text = text[:MAX_README_CHARS - total]
        collected.append(f"### {Path(path).name}\n{text}\n")
        total += len(text)
    return "\n".join(collected)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def load_catalog() -> dict:
    with CATALOG_PATH.open() as f:
        return yaml.safe_load(f)


def load_glossary_terms() -> str:
    """Load compact glossary as a plain term list for injection into prompts."""
    if not GLOSSARY_PATH.exists():
        return ""
    with GLOSSARY_PATH.open() as f:
        data = yaml.safe_load(f)
    terms = [t["term"] for t in data.get("terms", [])]
    return ", ".join(terms)


def slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def write_doc(path: Path, frontmatter: dict, body: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fm_lines = ["---"]
    for k, v in frontmatter.items():
        if isinstance(v, list):
            fm_lines.append(f"{k}: [{', '.join(str(x) for x in v)}]")
        else:
            sv = str(v)
            if any(c in sv for c in ('"', "'", ":", "#", "\n")):
                sv = json.dumps(sv)
            fm_lines.append(f"{k}: {sv}")
    fm_lines.append("---\n")
    path.write_text("\n".join(fm_lines) + body)
    print(f"  wrote {path.relative_to(REPO_ROOT)}")


# ---------------------------------------------------------------------------
# LLM calls
# ---------------------------------------------------------------------------

def analyze_contract(client: anthropic.Anthropic, contract_path: str,
                     contract_text: str, project_name: str,
                     glossary_terms: str) -> str:
    """Ask the LLM to analyze a single ErgoScript contract."""
    prompt = textwrap.dedent(f"""
        Analyze this ErgoScript contract from the **{project_name}** project.

        Produce a structured Markdown document with these sections:

        ## Purpose
        What this contract does in 2-3 sentences.

        ## Inputs / Outputs
        What boxes (UTXOs) this contract expects as inputs and produces as outputs.

        ## Key Logic
        The core validation conditions, explained in plain English.

        ## Registers Used
        Which R4-R9 registers are read/written, their types, and purposes.

        ## Tokens
        Any NFTs or tokens used for authentication, state tracking, or value.

        ## Integration Pattern
        How off-chain code interacts with this contract (what it must construct/verify).

        ## Related Contracts
        Which other contracts in this project this one composes with (if identifiable from the code).

        Use exact Ergo terminology. Key terms: {glossary_terms[:500]}

        ---
        File: `{contract_path}`

        ```ergoscript
        {contract_text}
        ```
    """).strip()

    response = client.messages.create(
        model=CONTRACT_MODEL,
        max_tokens=1500,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.content[0].text


def generate_overview(client: anthropic.Anthropic, entry: dict,
                      readme: str, contract_summaries: list[dict],
                      pattern_matches: list[dict], glossary_terms: str) -> str:
    """Generate a per-project overview document."""
    contracts_block = ""
    if contract_summaries:
        contracts_block = "\n\n## Contracts\n" + "\n---\n".join(
            f"### `{c['file']}`\n{c['summary']}" for c in contract_summaries[:10]
        )

    patterns_block = ""
    if pattern_matches:
        patterns_block = "\n\n## Pattern Matches Found\n" + "\n".join(
            f"- `{m['file']}` — patterns: {', '.join(m['patterns_found'])}"
            for m in pattern_matches[:10]
        )

    org = entry["org"]
    repo = entry["repo"]
    languages = entry.get("language", [])

    prompt = textwrap.dedent(f"""
        Generate a developer-focused overview document for the **{org}/{repo}** project.

        Project description: {entry['description']}
        Group: {entry['group']}
        Languages: {', '.join(languages)}

        Use these sections:

        ## Overview
        2-3 paragraphs on what this project does and its role in the Ergo ecosystem.

        ## Architecture
        Key components, their relationships, and how data flows between them.

        ## Smart Contracts
        Summary of ErgoScript contracts (if any) and their responsibilities.

        ## Integration Guide
        How to interact with this project from an off-chain perspective (SDK, API, patterns used).

        ## Key Patterns
        Notable design patterns demonstrated (headless dApp, off-chain bot, EIP-12 connector, etc.)

        ## Related Projects
        Other Ergo ecosystem projects this connects to or depends on.

        Use exact Ergo terminology. Key terms: {glossary_terms[:500]}

        ---
        README:
        {readme[:MAX_README_CHARS]}
        {contracts_block}
        {patterns_block}
    """).strip()

    response = client.messages.create(
        model=OVERVIEW_MODEL,
        max_tokens=2000,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.content[0].text


# ---------------------------------------------------------------------------
# Per-repo processing
# ---------------------------------------------------------------------------

def process_repo(client: anthropic.Anthropic, entry: dict,
                 glossary_terms: str, dry_run: bool) -> None:
    org = entry["org"]
    repo = entry["repo"]
    output_dir = REPO_ROOT / entry["output_dir"]
    project_name = f"{org}/{repo}"
    languages = entry.get("language", [])

    print(f"\n{'='*60}")
    print(f"  {project_name}")
    print(f"  → {entry['output_dir']}")
    print(f"{'='*60}")

    if dry_run:
        print("  [dry-run] skipping GitHub API and LLM calls")
        return

    # 1. Fetch repo metadata and file tree
    print(f"  fetching repo tree...")
    branch = get_default_branch(org, repo)
    tree = fetch_repo_tree(org, repo, branch)
    print(f"  branch={branch}  files={len(tree)}")

    # 2. Gather material
    extract = entry.get("extract", [])
    patterns = entry.get("patterns", [])

    readme = read_readme(org, repo, branch, tree) if "readme" in extract else ""
    docs = read_docs(org, repo, branch, tree) if "docs" in extract else ""
    if docs:
        readme = readme + "\n\n" + docs

    es_paths = find_ergoscript_paths(tree) if "contracts" in extract else []
    pattern_matches = find_pattern_matches(
        org, repo, branch, tree, patterns, languages
    ) if patterns else []

    print(f"  ErgoScript files: {len(es_paths)}")
    print(f"  Pattern matches:  {len(pattern_matches)}")

    # 3. Analyze each ErgoScript contract
    contract_summaries = []
    for path in es_paths:
        text = fetch_raw(org, repo, branch, path)
        if len(text) > MAX_CONTRACT_CHARS:
            text = text[:MAX_CONTRACT_CHARS] + "\n... [truncated]"
        print(f"  analyzing {path}")

        summary = analyze_contract(client, path, text, project_name, glossary_terms)
        contract_summaries.append({"file": path, "summary": summary})

        # Write individual contract doc
        contract_slug = slug(path.replace("/", "-").replace(".es", "").replace(".ergo", ""))
        fm = {
            "title": f"{project_name} — {Path(path).name}",
            "description": f"ErgoScript contract analysis: {path}",
            "tags": [slug(org), slug(repo), "ergoscript", "contract"],
            "category": "ecosystem",
            "difficulty": "advanced",
            "sdk": ["none"],
            "updated": TODAY,
            "source": "auto-generated",
            "source_repo": f"https://github.com/{org}/{repo}",
            "contract_file": path,
            "project": slug(f"{org}-{repo}"),
        }
        write_doc(output_dir / "contracts" / f"{contract_slug}.md", fm, summary)

    # 4. Generate project overview
    print(f"  generating overview...")
    overview = generate_overview(
        client, entry, readme, contract_summaries, pattern_matches, glossary_terms
    )

    fm = {
        "title": f"{org}/{repo} — Overview",
        "description": entry["description"],
        "tags": [slug(org), slug(repo), entry["group"]] + [slug(l) for l in languages],
        "category": "ecosystem",
        "difficulty": "intermediate",
        "sdk": ["none"],
        "updated": TODAY,
        "source": "auto-generated",
        "source_repo": f"https://github.com/{org}/{repo}",
        "project": slug(f"{org}-{repo}"),
        "group": entry["group"],
        "priority": entry.get("priority", "medium"),
        "languages": languages,
        "contract_count": len(contract_summaries),
        "pattern_match_count": len(pattern_matches),
    }
    write_doc(output_dir / "overview.md", fm, overview)


# ---------------------------------------------------------------------------
# Cross-cutting pattern synthesis
# ---------------------------------------------------------------------------

def generate_cross_cutting_pattern(client: anthropic.Anthropic, pattern_entry: dict,
                                   glossary_terms: str, dry_run: bool) -> None:
    pattern_id = pattern_entry["id"]
    output_file = REPO_ROOT / pattern_entry["output_file"]
    source_repos = pattern_entry["source_repos"]
    description = pattern_entry["description"]

    print(f"\n  cross-cutting pattern: {pattern_id}")

    if dry_run:
        print("  [dry-run] skipping")
        return

    # Gather code snippets from each source repo via GitHub API
    regex = re.compile(pattern_entry.get("pattern_regex", ""))
    snippets = []

    for repo_spec in source_repos:
        if len(snippets) >= 5:
            break
        org, repo = repo_spec.split("/", 1)
        try:
            branch = get_default_branch(org, repo)
            tree = fetch_repo_tree(org, repo, branch)
        except Exception as e:
            print(f"    skipping {repo_spec}: {e}")
            continue

        target_exts = {".ts", ".js", ".scala", ".rs", ".py", ".es", ".ergo"}
        for item in tree:
            if len(snippets) >= 5:
                break
            path = item["path"]
            if is_skipped(path) or Path(path).suffix not in target_exts:
                continue
            content = fetch_raw(org, repo, branch, path)
            if regex.search(content):
                snippet = _extract_snippet(content, regex, context=8)
                snippets.append(f"// {repo_spec}: {Path(path).name}\n{snippet}")

    prompt = textwrap.dedent(f"""
        Generate a comprehensive developer guide for the following Ergo integration pattern:

        **Pattern:** {description}

        Use these sections:

        ## Overview
        What this pattern is, why it exists, and when to use it.

        ## How It Works
        Step-by-step explanation of the flow.

        ## Implementation
        Working code examples drawn from real Ergo projects (TypeScript, Scala, Python, or ErgoScript as appropriate).

        ## Common Pitfalls
        What goes wrong and how to avoid it.

        ## References
        Links to source repos and EIPs (use: https://github.com/{', '.join(source_repos)}).

        Use exact Ergo terminology. Key terms: {glossary_terms[:400]}

        Real code snippets from the ecosystem:
        {'---'.join(snippets[:5]) if snippets else '(no snippets found — write from knowledge)'}
    """).strip()

    response = client.messages.create(
        model=OVERVIEW_MODEL,
        max_tokens=2500,
        messages=[{"role": "user", "content": prompt}],
    )
    body = response.content[0].text

    fm = {
        "title": description.split(" — ")[0],
        "description": description,
        "tags": [pattern_id, "pattern", "integration"],
        "category": "reference",
        "difficulty": "intermediate",
        "sdk": ["none"],
        "updated": TODAY,
        "source": "auto-generated",
        "source_repos": source_repos,
    }
    write_doc(output_file, fm, body)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Fetch ecosystem repos via GitHub API and generate docs"
    )
    parser.add_argument("--catalog", default=str(CATALOG_PATH), help="Path to ecosystem_repos.yaml")
    parser.add_argument("--repo", help="Process only this org/repo (e.g. arkadianet/citadel)")
    parser.add_argument("--priority", choices=["high", "medium", "low"],
                        help="Process only repos with this priority level")
    parser.add_argument("--group", help="Process only repos in this group (e.g. defi, sdk)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Show what would be processed without making any API or LLM calls")
    parser.add_argument("--patterns-only", action="store_true",
                        help="Only generate cross-cutting pattern docs")
    parser.add_argument("--no-patterns", action="store_true",
                        help="Skip cross-cutting pattern generation")
    args = parser.parse_args()

    if not GITHUB_TOKEN:
        print("WARNING: GITHUB_TOKEN not set — using unauthenticated GitHub API (60 req/hr limit)")
        print("         Set GITHUB_TOKEN for 5000 req/hr. Export it or add to your secrets file.")
        print()

    # Load catalog
    catalog = load_catalog()
    repos: list[dict] = catalog.get("repos", [])
    patterns: list[dict] = catalog.get("cross_cutting_patterns", [])

    # Apply filters
    if args.repo:
        org, repo = args.repo.split("/", 1)
        repos = [r for r in repos if r["org"] == org and r["repo"] == repo]
        if not repos:
            sys.exit(f"Repo {args.repo} not found in catalog")
    if args.priority:
        repos = [r for r in repos if r.get("priority") == args.priority]
    if args.group:
        repos = [r for r in repos if r.get("group") == args.group]

    if not repos and not args.patterns_only:
        sys.exit("No repos matched the given filters")

    # Sort: high → medium → low
    priority_order = {"high": 0, "medium": 1, "low": 2}
    repos.sort(key=lambda r: priority_order.get(r.get("priority", "low"), 2))

    print(f"Repos to process: {len(repos)}")
    for r in repos:
        print(f"  [{r.get('priority','?'):6}] {r['org']}/{r['repo']:30} → {r['output_dir']}")

    if args.dry_run:
        print(f"\n[dry-run] {len(repos)} repos would be fetched via GitHub API and processed")
        print(f"[dry-run] {len(patterns)} cross-cutting patterns would be generated")
        print("[dry-run] Remove --dry-run to actually run.")
        return

    # Load glossary for prompt injection
    glossary_terms = load_glossary_terms()
    print(f"\nGlossary: {len(glossary_terms.split(','))} terms loaded")

    # Init Anthropic client (reads ANTHROPIC_API_KEY from env)
    client = anthropic.Anthropic()

    # Process repos
    if not args.patterns_only:
        for entry in repos:
            try:
                process_repo(client, entry, glossary_terms, dry_run=False)
                time.sleep(1)  # be courteous between repos
            except Exception as e:
                print(f"\n  ERROR processing {entry['org']}/{entry['repo']}: {e}")
                continue

    # Generate cross-cutting pattern docs
    if not args.no_patterns:
        print(f"\n{'='*60}")
        print("  Generating cross-cutting pattern docs")
        print(f"{'='*60}")
        for pattern_entry in patterns:
            try:
                generate_cross_cutting_pattern(
                    client, pattern_entry, glossary_terms, dry_run=False
                )
            except Exception as e:
                print(f"\n  ERROR generating pattern {pattern_entry['id']}: {e}")
                continue

    print("\nDone.")
    print(f"Output written to {REPO_ROOT}/content/")
    print("Review generated docs, then run: python3 scripts/generate_llms_txt.py")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Generate derived glossary tiers from ergo_glossary.yaml (the master).

Outputs:
  ergo_glossary_compact.yaml  — term + up to 4 aliases + first sentence + category + docs_url
  ergo_aliases.yaml           — flat alias→canonical mapping for term normalization
  ergo_aliases.json           — same, as JSON (convenient for JS/TypeScript consumers)

Usage:
  python3 scripts/generate_glossary_tiers.py
  python3 scripts/generate_glossary_tiers.py --master path/to/ergo_glossary.yaml
"""

import argparse
import json
import re
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    sys.exit("PyYAML required: pip install pyyaml")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def first_sentence(text: str) -> str:
    """Return the first sentence of a block-scalar definition string."""
    text = " ".join(text.split())          # collapse whitespace / newlines
    # Split on first period that is followed by a space or end-of-string
    m = re.search(r"\.(?:\s|$)", text)
    if m:
        return text[: m.start() + 1].strip()
    return text.strip()


def compact_entry(term: dict) -> dict:
    """Distil a full entry to its compact form."""
    entry: dict = {"term": term["term"]}

    aliases = term.get("aliases", [])
    if aliases:
        # Keep at most 6 aliases — enough for good recall, not bloated
        entry["aliases"] = aliases[:6]

    entry["definition"] = first_sentence(term.get("definition", ""))
    entry["category"] = term.get("category", "")

    if "docs_url" in term:
        entry["docs_url"] = term["docs_url"]

    return entry


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Generate glossary tiers")
    parser.add_argument(
        "--master",
        default=Path(__file__).parent.parent / "glossary" / "ergo_glossary.yaml",
        type=Path,
        help="Path to ergo_glossary.yaml (default: ../glossary/ergo_glossary.yaml)",
    )
    parser.add_argument(
        "--out-dir",
        default=None,
        type=Path,
        help="Output directory (default: same directory as master file)",
    )
    args = parser.parse_args()

    master_path: Path = args.master.resolve()
    out_dir: Path = (args.out_dir or master_path.parent).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    # --- Load master ---------------------------------------------------------
    with master_path.open() as f:
        data = yaml.safe_load(f)

    terms: list[dict] = data.get("terms", [])
    if not terms:
        sys.exit(f"No 'terms' key found in {master_path}")

    print(f"Loaded {len(terms)} terms from {master_path}")

    # --- Tier 2: compact YAML ------------------------------------------------
    compact_path = out_dir / "ergo_glossary_compact.yaml"
    compact_data = {
        "# generated": "Auto-generated from ergo_glossary.yaml — do not edit directly.",
        "terms": [compact_entry(t) for t in terms],
    }

    # PyYAML dumps dict keys in insertion order (Python 3.7+)
    with compact_path.open("w") as f:
        f.write(
            "# Auto-generated from ergo_glossary.yaml — do not edit directly.\n"
            "# Run: python3 scripts/generate_glossary_tiers.py\n\n"
        )
        yaml.dump(
            {"terms": [compact_entry(t) for t in terms]},
            f,
            allow_unicode=True,
            default_flow_style=False,
            sort_keys=False,
            width=100,
        )

    # --- Tier 3: alias flat map (YAML + JSON) --------------------------------
    alias_map: dict[str, str] = {}
    collisions: list[str] = []

    for t in terms:
        canonical = t["term"]
        # canonical maps to itself (lowercase key for case-insensitive lookup)
        key = canonical.lower()
        if key in alias_map and alias_map[key] != canonical:
            collisions.append(f"  '{key}' → '{alias_map[key]}' vs '{canonical}'")
        alias_map[key] = canonical

        for alias in t.get("aliases", []):
            akey = alias.lower()
            if akey in alias_map and alias_map[akey] != canonical:
                collisions.append(f"  '{akey}' → '{alias_map[akey]}' vs '{canonical}'")
            else:
                alias_map[akey] = canonical

    if collisions:
        print(f"WARNING: {len(collisions)} alias collision(s) — last writer wins:")
        for c in collisions:
            print(c)

    # YAML version
    aliases_yaml_path = out_dir / "ergo_aliases.yaml"
    with aliases_yaml_path.open("w") as f:
        f.write(
            "# Auto-generated alias→canonical map from ergo_glossary.yaml\n"
            "# Run: python3 scripts/generate_glossary_tiers.py\n"
            "# Keys are lowercase; values are canonical term names.\n\n"
        )
        yaml.dump(
            {"aliases": alias_map},
            f,
            allow_unicode=True,
            default_flow_style=False,
            sort_keys=True,
            width=120,
        )

    # JSON version
    aliases_json_path = out_dir / "ergo_aliases.json"
    with aliases_json_path.open("w") as f:
        json.dump(alias_map, f, indent=2, ensure_ascii=False, sort_keys=True)
        f.write("\n")

    # --- Stats ---------------------------------------------------------------
    def token_est(path: Path) -> int:
        return len(path.read_text()) // 4

    print()
    print("Generated files:")
    print(f"  {compact_path.name:<35}  ~{token_est(compact_path):,} tokens")
    print(f"  {aliases_yaml_path.name:<35}  ~{token_est(aliases_yaml_path):,} tokens")
    print(f"  {aliases_json_path.name:<35}  ~{token_est(aliases_json_path):,} tokens")
    print(f"  {'ergo_glossary.yaml (master)':<35}  ~{token_est(master_path):,} tokens")
    print()
    print(f"Alias map: {len(alias_map)} alias→canonical pairs")
    print()
    print("Recommended usage:")
    print("  Bulk pipeline injection  → ergo_glossary_compact.yaml")
    print("  Term normalization / RAG → ergo_aliases.yaml / ergo_aliases.json")
    print("  Agent deep reasoning     → ergo_glossary.yaml (master)")


if __name__ == "__main__":
    main()

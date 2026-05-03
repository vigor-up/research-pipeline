"""
compare.py
CLI tool for B-group market comparison output.

Usage:
  python compare.py --species finisher_pig --metric FCR
  python compare.py --species broiler --metric breast_yield_pct --output markdown
  python compare.py --species shrimp --metric survival_rate --output markdown
"""

import sys
import json
import argparse
import logging

import yaml

logging.basicConfig(stream=sys.stderr, level=logging.INFO,
                    format="%(asctime)s [compare] %(levelname)s %(message)s")
log = logging.getLogger(__name__)

# Import from sibling module
sys.path.insert(0, __file__.replace("compare.py", ""))
from b_group_extractor import extract_b_group_metrics, get_collection, load_config

LEVEL_LABEL = {5: "Gold", 4: "High", 3: "Medium", 2: "Low", 1: "Noise"}
LEVEL_BAR = {5: "█████", 4: "████░", 3: "███░░", 2: "██░░░", 1: "█░░░░"}


def render_markdown(species: str, metric: str, claims: list, species_label: str) -> str:
    if not claims:
        return f"## {species_label} — {metric}\n\nNo market claims found in database.\n"

    lines = [
        f"## {species_label} — {metric} Market Comparison",
        "",
        f"| Source | Value | Change | Credibility | Year |",
        f"|--------|-------|--------|-------------|------|",
    ]

    for c in claims:
        val = f"{c['value']} {c['unit']}" if c.get("value") is not None else "N/A"
        chg = f"{c['change_pct']:+.1f}%" if c.get("change_pct") is not None else "—"
        bar = LEVEL_BAR.get(c["credibility_level"], "?????")
        label = LEVEL_LABEL.get(c["credibility_level"], "?")
        src = c["source"][:55]
        lines.append(f"| {src} | {val} | {chg} | {bar} L{c['credibility_level']} {label} | {c['year']} |")

    lines.append("")

    # Best claim
    best = claims[0]
    best_val = f"{best['value']} {best['unit']}" if best.get("value") is not None else "N/A"
    best_chg = f"{best['change_pct']:+.1f}%" if best.get("change_pct") is not None else ""
    lines.append(f"**Market best claim:** {best_val} ({best_chg}) — {best['source'][:50]}")

    # Average (weighted by credibility)
    weighted_vals = [
        c["value"] * c["credibility_weight"]
        for c in claims
        if c.get("value") is not None and isinstance(c["value"], (int, float))
    ]
    weight_sum = sum(
        c["credibility_weight"] for c in claims
        if c.get("value") is not None and isinstance(c["value"], (int, float))
    )
    if weighted_vals and weight_sum > 0:
        weighted_avg = sum(weighted_vals) / weight_sum
        lines.append(f"**Weighted market average:** {weighted_avg:.2f} {best.get('unit', '')}")

    lines.append(f"\n*{len(claims)} sources | min credibility: L3 | sorted by credibility desc*")
    return "\n".join(lines)


def render_text(species: str, metric: str, claims: list, species_label: str) -> str:
    if not claims:
        return f"No B-group claims found for {species} / {metric}"

    lines = [f"\nB-GROUP COMPARISON: {species_label} / {metric}", "=" * 60]
    for c in claims:
        bar = LEVEL_BAR.get(c["credibility_level"], "?????")
        val = f"{c['value']} {c['unit']}" if c.get("value") is not None else "N/A"
        chg = f"({c['change_pct']:+.1f}%)" if c.get("change_pct") is not None else ""
        lines.append(f"[L{c['credibility_level']} {bar}] {val} {chg} | {c['year']} | {c['source'][:55]}")

    lines.append("-" * 60)
    best = claims[0]
    best_val = f"{best['value']} {best['unit']}" if best.get("value") is not None else "N/A"
    lines.append(f"Best claim : {best_val}")
    lines.append(f"Total sources: {len(claims)}")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="B-group market comparison")
    parser.add_argument("--species", required=True, help="e.g. finisher_pig")
    parser.add_argument("--metric", required=True, help="e.g. FCR")
    parser.add_argument("--min-credibility", type=int, default=3)
    parser.add_argument("--output", choices=["text", "markdown", "json"], default="text")
    args = parser.parse_args()

    cfg = load_config()
    valid_species = list(cfg["species"].keys())
    if args.species not in valid_species:
        print(f"ERROR: Unknown species '{args.species}'. Valid: {valid_species}", file=sys.stderr)
        sys.exit(1)

    species_label = cfg["species"][args.species]["label"]
    collection = get_collection(cfg)
    claims = extract_b_group_metrics(
        args.species, args.metric, args.min_credibility, collection, cfg
    )

    if args.output == "json":
        print(json.dumps(claims, ensure_ascii=False, indent=2))
    elif args.output == "markdown":
        print(render_markdown(args.species, args.metric, claims, species_label))
    else:
        print(render_text(args.species, args.metric, claims, species_label))


if __name__ == "__main__":
    main()

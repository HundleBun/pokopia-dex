#!/usr/bin/env python3
"""
add_habitat_types.py — Enrich habitats.json with a 'types' array.

Each habitat's types are derived from its requirements items. The item names
are mapped to the same canonical habitat_type values used on pokemon.json,
so the two datasets speak the same language and can be cross-referenced in JS.

Run once:
    cd C:/Users/jhund/Documents/pokopia-dex
    python data/add_habitat_types.py
"""

import json
from pathlib import Path

# Maps requirement item names (lowercased) → canonical habitat_type values.
# These canonical values must exactly match what appears in pokemon.json habitat_type fields.
ITEM_TO_TYPE = {
    # ── Tall Grass variants ────────────────────────────────────────────────────
    "tall grass":       "Tall Grass",
    "tall grass (any)": "Tall Grass",
    "yellow tall grass":"Yellow Tall Grass",
    "red tall grass":   "Red Tall Grass",
    "pink tall grass":  "Pink Tall Grass",
    "dry tall grass":   "Dry Tall Grass",

    # ── Trees ──────────────────────────────────────────────────────────────────
    # "Tree" and "Large tree" both map to Large Tree — in habitats.json the item
    # is sometimes written as the generic "Tree" (e.g. Tree-shaded tall grass)
    # but it represents the same large tree decoration as pokemon.json's "Large Tree".
    "tree":             "Large Tree",
    "large tree":       "Large Tree",
    "large palm tree":  "Large Palm Tree",
    "pointy tree":      "Pointy Tree",
    "pointyt ree":      "Pointy Tree",   # typo present in source data
    "tree stump":       "Tree Stump",

    # ── Water ──────────────────────────────────────────────────────────────────
    "ocean water":      "Ocean Water",
    "water":            "Water",
    "water basin":      "Water",
    "muddy water":      "Water",
    "waterfall":        "Waterfall",
    "hot-spring water": "Hot-Spring Water",
    "hot-spring spout": "Hot-Spring Water",
    "duckweed":         "Duckweed",

    # ── Flowers & Plants ───────────────────────────────────────────────────────
    "wildflowers":      "Wildflowers",
    "dandy flowers":    "Dandy Flowers",
    "seashore flowers": "Seashore Flowers",
    "skyland flowers":  "Skyland Flowers",
    "mountain flowers": "Mountain Flowers",
    "chansey plant":    "Chansey Plant",
    "berry tree":       "Berry Tree",
    "vegetable field":  "Vegetable Field",

    # ── Rock & Earth ───────────────────────────────────────────────────────────
    "large boulder":    "Large Boulder",
    "smooth rock":      "Smooth Rock",
    "stalagmites":      "Stalagmites",
    "moss":             "Moss",
    "mossy boulder":    "Mossy Boulder",
    "molten rock":      "Molten Rock",
    "lava":             "Lava",

    # ── Other terrain ──────────────────────────────────────────────────────────
    "high-up location": "High-Up Location",
}

def compute_types(habitat):
    """Return sorted list of canonical type strings for a habitat."""
    found = set()
    for req in habitat.get("requirements", []):
        item_lower = req["item"].strip().lower()
        canonical = ITEM_TO_TYPE.get(item_lower)
        if canonical:
            found.add(canonical)
    return sorted(found)

def main():
    path = Path(__file__).parent / "habitats.json"
    habitats = json.loads(path.read_text(encoding="utf-8"))

    untyped = []
    for h in habitats:
        types = compute_types(h)
        h["types"] = types
        if not types:
            untyped.append(h["name"])

    path.write_text(
        json.dumps(habitats, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )
    print(f"Updated {len(habitats)} habitats.")

    if untyped:
        print(f"\n{len(untyped)} habitats have no terrain type (decoration-only or unrecognised items):")
        for name in untyped:
            print(f"  - {name}")
    else:
        print("All habitats have at least one terrain type.")

if __name__ == "__main__":
    main()

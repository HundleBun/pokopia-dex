#!/usr/bin/env python3
"""
apply_decoration_habitats.py — Apply curated habitat matches for Pokémon whose
habitats are decoration-based rather than terrain-based.

For these Pokémon, habitat_type is set to the habitat NAME (e.g. "Campsite")
rather than a terrain keyword (e.g. "Tall Grass"). The JS navigation handles
both by checking h.name as a fallback when h.types is empty.

The mapping was derived by matching scraped game8 "How to Build" items in
zone_corrections.json against the requirement items in habitats.json.

Run:
    cd C:/Users/jhund/Documents/pokopia-dex
    python data/apply_decoration_habitats.py
"""

import json
from pathlib import Path

# Curated mapping: Pokemon name → list of habitat names they belong to.
# Multiple entries = Pokemon spawns in all listed habitats.
DECORATION_HABITATS = {
    # ── Fossil displays ────────────────────────────────────────────────────────
    "Aerodactyl":   ["Wing Fossil Display"],
    "Rampardos":    ["Headbutt Fossil display"],
    "Shieldon":     ["Armor Fossil display"],
    "Bastiodon":    ["Shield Fossil display"],
    "Cranidos":     ["Headbutt Fossil display"],
    "Tyrunt":       ["Jaw Fossil display"],
    "Tyrantrum":    ["Despot fossil display"],
    "Amaura":       ["Tundra fossil display"],
    "Aurorus":      ["Tundra fossil display"],

    # ── Train / transport ──────────────────────────────────────────────────────
    "Rolycoly":     ["Railroad crossing"],
    "Carkol":       ["Railroad crossing"],
    "Coalossal":    ["Railroad crossing"],

    # ── Pirate / barrel ───────────────────────────────────────────────────────
    "Voltorb":      ["Playing pirate"],
    "Electrode":    ["Playing pirate"],

    # ── Campfire / campsite ────────────────────────────────────────────────────
    "Charmeleon":   ["Campsite"],

    # ── Chirp-chirp meal (bird feeder) ────────────────────────────────────────
    "Blaziken":     ["Chirp-chirp meal"],

    # ── Ghost / grave ─────────────────────────────────────────────────────────
    "Litwick":      ["Creepy grave offering"],
    "Lampent":      ["Creepy grave offering"],
    "Chandelure":   ["Creepy grave offering"],
    "Haunter":      ["Spooky study"],
    "Drifloon":     ["Plush central"],

    # ── Vending machine ───────────────────────────────────────────────────────
    "Charjabug":    ["Vending machine break area"],
    "Elekid":       ["Vending machine set"],
    "Electabuzz":   ["Light-up stage"],
    "Electivire":   ["Vending machine set"],

    # ── Iron / construction ───────────────────────────────────────────────────
    "Steelix":      ["Clink-clang iron construction"],
    "Magmar":       ["Digging and burning"],
    "Tinkatink":    ["Oversized dumping ground"],
    "Tinkatuff":    ["Sewer hole inspection"],
    "Tinkaton":     ["Sewer hole inspection"],

    # ── Gym / combat training ──────────────────────────────────────────────────
    "Hitmontop":    ["Gym first aid"],
    "Hitmonlee":    ["Urgent Care"],
    "Hitmonchan":   ["Exercise resting spot"],
    "Lucario":      ["Box to the rhythm"],

    # ── Study / research ──────────────────────────────────────────────────────
    "Ralts":        ["Study Area"],
    "Kirlia":       ["Study Area"],
    "Gardevoir":    ["Study Area"],
    "Gallade":      ["Study Area"],
    "Metang":       ["Professor's apprentice program"],
    "Metagross":    ["Professor's apprentice program"],
    "Porygon":      ["Researcher's desk"],
    "Porygon2":     ["Researcher's desk"],

    # ── Tire park / playground ────────────────────────────────────────────────
    "Dedenne":      ["Tire Park"],
    "Snivy":        ["Playland"],

    # ── Music / rhythm ────────────────────────────────────────────────────────
    "Noibat":       ["Rhythmic Living room"],
    "Noivern":      ["Rhythmic Living room"],

    # ── Game corner ───────────────────────────────────────────────────────────
    "Magneton":     ["Mini Game Corner"],
    "Magnezone":    ["Mini Game Corner"],

    # ── Pikachu / doll themed ─────────────────────────────────────────────────
    "Pichu":        ["Picnic Set"],
    "Pikachu":      ["Picnic Set"],
    "Raichu":       ["Picnic Set"],
    "Mimikyu":      ["Pikachu space"],

    # ── Antique furniture ─────────────────────────────────────────────────────
    "Weezing":      ["Good old-fashioned antiques"],

    # ── Trash ─────────────────────────────────────────────────────────────────
    "Koffing":      ["Trash collection site"],
    "Trubbish":     ["Trash collection site"],
    "Garbodor":     ["Trash collection site"],
    "Dusclops":     ["Trash site TV"],
    "Dusknoir":     ["Trash site TV"],

    # ── Medicine / recovery ────────────────────────────────────────────────────
    "Happiny":      ["Alarm clock sleep zone"],
    "Chansey":      ["Full recovery"],
    "Blissey":      ["Full recovery"],

    # ── Knitting / festival ───────────────────────────────────────────────────
    "Flaaffy":      ["Knitting station", "Night festival venue"],
    "Ampharos":     ["Plain life"],

    # ── Road sign ─────────────────────────────────────────────────────────────
    "Shellos":          ["Road Sign"],
    "Shellos East Sea": ["Road Sign"],

    # ── All packed up / luggage ───────────────────────────────────────────────
    "Farfetch'd":   ["All packed up"],
    "Meowth":       ["Working the register"],
    "Persian":      ["Working the register"],
    "Mawile":       ["Working the register"],

    # ── Photo / spotlight ─────────────────────────────────────────────────────
    "Minccino":     ["Changing area"],
    "Cinccino":     ["Changing area"],

    # ── Eeveelutions (food-themed habitats) ───────────────────────────────────
    "Vaporeon":     ["Boundless blue beverage"],
    "Jolteon":      ["Electrifying potatoes"],
    "Flareon":      ["Burning-hot spice"],
    "Espeon":       ["Elegant daytime treats"],
    "Umbreon":      ["Dark-chocolate cookies"],
    "Leafeon":      ["Leafy greens sandwich"],
    "Glaceon":      ["Chilly shaved ice"],
    "Sylveon":      ["Lovely ribbon cake"],

    # ── Restaurant / dining ───────────────────────────────────────────────────
    "Pawmo":        ["Tantalizing restaurant"],
    "Pawmot":       ["Tantalizing restaurant"],

    # ── Photo album / couch ───────────────────────────────────────────────────
    "Toxel":        ["Lazy-photo album scrolling"],

    # ── Gimmighoul chest ──────────────────────────────────────────────────────
    "Gimmighoul":   ["Mini museum"],
    "Gholdengo":    ["Mini museum"],

    # ── Mime / magic ──────────────────────────────────────────────────────────
    "Abra":         ["Study Area"],
    "Kadabra":      ["Study Area"],
    "Alakazam":     ["Study Area"],

    # ── Toxtricity — Amped rock stage / Low-key rock stage ────────────────────
    # These habitats exist in habitats.json and require special dowsing machine
    # strings. Amped and Low Key forms each have their own stage.
    "Toxtricity Amped Form":    ["Amped rock stage"],
    "Toxtricity Low Key Form":  ["Low-key rock stage"],
}

def main():
    base = Path(__file__).parent.parent / "data"
    poke_path = base / "pokemon.json"
    hab_path  = base / "habitats.json"

    pokes = json.loads(poke_path.read_text(encoding="utf-8"))
    habs  = json.loads(hab_path.read_text(encoding="utf-8"))

    # Build habitat lookup by name
    hab_by_name = {h["name"]: h for h in habs}

    applied = []
    skipped = []

    for poke_name, hab_names in DECORATION_HABITATS.items():
        # Validate all named habitats exist
        missing_habs = [n for n in hab_names if n not in hab_by_name]
        if missing_habs:
            skipped.append(f"{poke_name}: habitat(s) not found: {missing_habs}")
            continue

        # Find the pokemon entry
        poke = next((p for p in pokes if p["name"] == poke_name), None)
        if not poke:
            skipped.append(f"{poke_name}: not found in pokemon.json")
            continue

        # Skip if already has habitat_type populated
        if poke.get("habitat_type"):
            skipped.append(f"{poke_name}: already has habitat_type {poke['habitat_type']}, skipping")
            continue

        # Set habitat_type to the habitat name(s)
        poke["habitat_type"] = hab_names
        applied.append(poke_name)

        # Add pokemon to each habitat's pokemon list if not already there
        for hab_name in hab_names:
            hab = hab_by_name[hab_name]
            if poke_name not in hab.get("pokemon", []):
                if "pokemon" not in hab:
                    hab["pokemon"] = []
                hab["pokemon"].append(poke_name)

    poke_path.write_text(json.dumps(pokes, indent=2, ensure_ascii=False), encoding="utf-8")
    hab_path.write_text(json.dumps(habs, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"Applied to {len(applied)} Pokemon:")
    for name in applied:
        print(f"  + {name} -> {DECORATION_HABITATS[name]}")

    if skipped:
        print(f"\nSkipped {len(skipped)}:")
        for msg in skipped:
            print(f"  - {msg}")

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
rescrape_missing_habitats.py — Targeted re-scrape for two groups of Pokémon:

  GROUP A — 17 Pokémon with no habitat_type at all (have game8 IDs)
  GROUP B — 16 Pokémon with habitat_type set but not placed in any matching
             habitat's pokemon list (need specific habitat variant identified)

For each Pokémon, fetches its game8 page, extracts the "How to Build" items,
scores them against habitats.json requirement items, and applies the best match.

Does NOT abort on missing zone data — these Pokémon are known TBD on game8.

Run:
    cd C:/Users/jhund/Documents/pokopia-dex
    python data/rescrape_missing_habitats.py
"""

import json, re, sys, time
from pathlib import Path
import requests
from bs4 import BeautifulSoup, Tag

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).parent.parent
DATA = ROOT / "data"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    )
}

# ── Group A: missing habitat_type entirely, have game8 IDs ───────────────────
# Tatsugiri: all three forms share the same page and identical habitat data.
# We fetch once and apply to all three names.
TATSUGIRI_FORMS = [
    "Tatsugiri Curly Form",
    "Tatsugiri Droopy Form",
    "Tatsugiri Stretchy Form",
]

GROUP_A = {
    "Pidgeot":                586050,
    "Tangela":                586064,
    "Tangrowth":              586891,
    "Goodra":                 586061,
    "Golduck":                586060,
    "Munchlax":               586057,
    "Smearguru":              583466,
    "Absol":                  586056,
    "Empoleon":               586055,
    "Tatsugiri Curly Form":   586053,   # representative; same data for all forms
    "Wigglytuff":             586052,
    "Armarouge":              586048,
    "Poliwag":                586046,
    "Typhlosion":             586044,
    "Beldum":                 586041,
    "Dragapult":              586038,
    "Floragato":              586037,
    "Articuno":               585497,   # pre-fab habitat in Palette Town
    "Zapdos":                 585498,   # pre-fab habitat in Palette Town
    "Moltres":                585499,   # pre-fab habitat in Palette Town
    "Mew":                    585572,
}

# ── Group B: habitat_type set but not in any matching habitat's pokemon list ──
GROUP_B = {
    # High-Up Location
    "Pidgey":      584914,
    "Pidgeotto":   585376,
    "Paras":       585377,
    "Parasect":    585378,
    "Hoothoot":    584932,
    "Noctowl":     584933,
    "Corvisquire": 585368,
    "Corviknight": 585884,
    "Wattrel":     585517,
    "Kilowattrel": 585886,
    # Hot-Spring Water
    "Lotad":       584993,
    "Lombre":      584994,
    # Water
    "Slowbro":     584923,
    "Volbeat":     585374,
    "Illumise":    584935,
    "Skiploom":    585372,
}


# ── Item name normalisation ───────────────────────────────────────────────────
def normalize(item):
    item = re.sub(r'^[・\s]+', '', item)          # strip Japanese bullet
    item = re.sub(r'\s*x\s*\d+$', '', item, flags=re.IGNORECASE)  # strip "x 3"
    item = re.sub(r'\s*x\d+', '', item)           # strip "x3"
    return item.strip().lower()


# ── game8 page fetching ───────────────────────────────────────────────────────
def fetch(url, retries=3):
    for attempt in range(retries):
        try:
            r = requests.get(url, headers=HEADERS, timeout=15)
            r.raise_for_status()
            time.sleep(1.5)
            return BeautifulSoup(r.text, "html.parser")
        except Exception as e:
            if attempt < retries - 1:
                time.sleep(3)
            else:
                print(f"  FETCH ERROR: {e}")
                return None


# ── Extract "How to Build" items from a game8 page ───────────────────────────
def extract_habitats(soup):
    """Return a set of normalised item strings from the How to Build section."""
    items = set()
    for b in soup.find_all("b", class_="a-bold"):
        label = b.get_text(strip=True).rstrip(":")
        if "how to build" not in label.lower():
            continue
        for sibling in b.next_siblings:
            if isinstance(sibling, Tag):
                if sibling.name == "b":
                    break
                if sibling.name == "div" and "align" in sibling.get("class", []):
                    for img in sibling.find_all("img"):
                        alt = normalize(img.get("alt", ""))
                        if alt:
                            items.add(alt)
                    for a in sibling.find_all("a"):
                        txt = normalize(a.get_text(strip=True))
                        if txt:
                            items.add(txt)
                    if not sibling.find_all(["a", "img"]):
                        bare = normalize(sibling.get_text(" ", strip=True))
                        if bare:
                            items.add(bare)
                elif sibling.name == "a":
                    txt = normalize(sibling.get_text(strip=True))
                    if txt:
                        items.add(txt)
            else:
                txt = normalize(str(sibling))
                if txt:
                    items.add(txt)
    # Remove noise tokens
    items -= {"", "x", "x 1", "x 2", "x 3", "x 4", "x 5"}
    return items


# ── Match scraped items to habitats ──────────────────────────────────────────
def best_habitat_match(scraped_items, hab_index, min_overlap=1):
    """
    Score each habitat by item overlap with scraped_items.
    Returns list of (score, overlap_count, hab_name) sorted best-first.
    """
    scores = []
    for hab_name, req_set in hab_index.items():
        if not req_set:
            continue
        overlap = scraped_items & req_set
        if len(overlap) >= min_overlap:
            score = len(overlap) / max(len(scraped_items), len(req_set))
            scores.append((score, len(overlap), hab_name, overlap))
    scores.sort(reverse=True)
    return scores


def main():
    poke_path = DATA / "pokemon.json"
    hab_path  = DATA / "habitats.json"

    pokes = json.loads(poke_path.read_text(encoding="utf-8"))
    habs  = json.loads(hab_path.read_text(encoding="utf-8"))

    poke_by_name = {p["name"]: p for p in pokes}
    hab_by_name  = {h["name"]: h for h in habs}

    # Build normalised requirement index for every habitat
    hab_index = {
        h["name"]: {normalize(r["item"]) for r in h.get("requirements", [])}
        for h in habs
    }

    applied_a = []
    applied_b = []
    no_match  = []

    all_targets = [("A", GROUP_A), ("B", GROUP_B)]

    for group_label, targets in all_targets:
        print(f"\n{'='*60}")
        print(f"GROUP {group_label} ({len(targets)} Pokémon)")
        print(f"{'='*60}")

        for poke_name, page_id in targets.items():
            url = f"https://game8.co/games/Pokemon-Pokopia/archives/{page_id}"
            print(f"\n{poke_name} ({page_id}) …")

            soup = fetch(url)
            if soup is None:
                print(f"  SKIP: fetch failed")
                no_match.append((poke_name, "fetch failed"))
                continue

            scraped = extract_habitats(soup)
            if not scraped:
                print(f"  No 'How to Build' data found on page")
                no_match.append((poke_name, "no How to Build section"))
                continue

            print(f"  Scraped items: {scraped}")

            matches = best_habitat_match(scraped, hab_index)
            if not matches:
                print(f"  No matching habitat found")
                no_match.append((poke_name, f"no hab match for: {scraped}"))
                continue

            # Show top 3 candidates
            print(f"  Top matches:")
            for score, count, hab_name, overlap in matches[:3]:
                print(f"    [{score:.2f} | {count}] {hab_name}  matched={overlap}")

            best_score, best_count, best_hab, _ = matches[0]

            # Require a reasonable match — at least 0.4 score or 2+ items
            if best_score < 0.40 and best_count < 2:
                print(f"  SKIP: best match too weak ({best_score:.2f})")
                no_match.append((poke_name, f"weak match: {best_hab} @ {best_score:.2f}"))
                continue

            poke = poke_by_name.get(poke_name)
            if not poke:
                print(f"  SKIP: not found in pokemon.json")
                continue

            hab = hab_by_name.get(best_hab)
            if not hab:
                print(f"  SKIP: habitat not found in habitats.json")
                continue

            # Apply: set habitat_type if missing (Group A), add to habitat pokemon list
            if not poke.get("habitat_type"):
                # Decoration habitat — use name directly; terrain habs use type label
                hab_types = hab.get("types", [])
                if hab_types:
                    new_ht = hab_types  # terrain: use type labels
                else:
                    new_ht = [best_hab]  # decoration: use habitat name
                poke["habitat_type"] = new_ht
                print(f"  SET habitat_type = {new_ht}")
                applied_a.append((poke_name, best_hab))
            else:
                print(f"  habitat_type already set: {poke['habitat_type']}")
                applied_b.append((poke_name, best_hab))

            if poke_name not in hab.get("pokemon", []):
                hab.setdefault("pokemon", []).append(poke_name)
                print(f"  ADDED to habitat: {best_hab}")
            else:
                print(f"  Already in habitat: {best_hab}")

            # Special case: propagate Tatsugiri data to all three forms
            if poke_name == "Tatsugiri Curly Form":
                for form_name in TATSUGIRI_FORMS:
                    if form_name == poke_name:
                        continue
                    form = poke_by_name.get(form_name)
                    if not form:
                        print(f"  SKIP propagate: {form_name} not found in pokemon.json")
                        continue
                    if not form.get("habitat_type"):
                        form["habitat_type"] = list(poke["habitat_type"])
                        print(f"  PROPAGATED habitat_type to {form_name}")
                    if form_name not in hab.get("pokemon", []):
                        hab.setdefault("pokemon", []).append(form_name)
                        print(f"  PROPAGATED to habitat pokemon list: {form_name}")

    # Save
    poke_path.write_text(json.dumps(pokes, indent=2, ensure_ascii=False), encoding="utf-8")
    hab_path.write_text(json.dumps(habs, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"\n{'='*60}")
    print(f"SUMMARY")
    print(f"{'='*60}")
    print(f"Group A applied (habitat_type set): {len(applied_a)}")
    for name, hab in applied_a:
        print(f"  + {name} -> {hab}")
    print(f"Group B applied (added to habitat): {len(applied_b)}")
    for name, hab in applied_b:
        print(f"  + {name} -> {hab}")
    print(f"No match / skipped: {len(no_match)}")
    for name, reason in no_match:
        print(f"  - {name}: {reason}")


if __name__ == "__main__":
    main()

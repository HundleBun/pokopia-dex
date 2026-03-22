#!/usr/bin/env python3
"""
scrape.py — Fetch all Pokémon Pokopia data from Serebii.net
Outputs structured data files to data/

Usage:
    python scrape.py

Requirements:
    pip install requests beautifulsoup4
"""

import re
import time
import json
from pathlib import Path
import requests
from bs4 import BeautifulSoup

BASE = "https://www.serebii.net"
DATA = Path(__file__).parent / "data"
DATA.mkdir(exist_ok=True)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    )
}

def fetch(url, delay=1.0):
    print(f"  GET {url}")
    r = requests.get(url, headers=HEADERS, timeout=15)
    r.raise_for_status()
    time.sleep(delay)
    return BeautifulSoup(r.text, "html.parser")


# ── HELPERS ───────────────────────────────────────────────────────────────────

def clean(text):
    return re.sub(r"\s+", " ", text or "").strip()

# Known valid specialty labels (for filtering noise)
VALID_SPECS = {
    "Appraise","Build","Bulldoze","Burn","Chop","Collect","Crush","DJ",
    "Dream Island","Eat","Engineer","Explode","Fly","Gather","Gather Honey",
    "Generate","Grow","Hype","Illuminate","Litter","Paint","Party","Rarify",
    "Recycle","Search","Storage","Teleport","Trade","Transform","Water","Yawn",
}


def write_json(path, data, comment=""):
    """Write data as a JSON file."""
    Path(path).write_text(
        json.dumps(data, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )
    print(f"  Wrote {path}  ({len(data)} entries)")

# Keep old name as alias so call sites don't need changing
def write_python(path, varname, data, comment=""):
    json_path = Path(str(path).replace(".py", ".json"))
    write_json(json_path, data, comment)


# ── 1. SPECIALTIES ────────────────────────────────────────────────────────────

def scrape_specialties():
    print("\n[1/5] Scraping specialties...")
    soup = fetch(f"{BASE}/pokemonpokopia/specialty.shtml")

    specialties = []
    # Each specialty has an image + name + description in a ftype table row
    for row in soup.select("table.ftype tr"):
        cells = row.find_all("td")
        if len(cells) < 2:
            continue
        name_cell = cells[0] if len(cells) == 2 else cells[1]
        desc_cell = cells[-1]
        name = clean(name_cell.get_text())
        desc = clean(desc_cell.get_text())
        if not name or name.lower() in ("specialty", "description"):
            continue
        # derive id from name
        sid = name.lower().replace(" ", "").replace("-", "").replace("'", "")
        specialties.append({
            "id": sid,
            "label": name,
            "description": desc,
        })

    # If the table approach missed entries, fall back to named anchors / headers
    if len(specialties) < 20:
        specialties = []
        for header in soup.find_all(["h2", "h3", "td"]):
            text = clean(header.get_text())
            if not text or len(text) > 40:
                continue
            next_el = header.find_next_sibling()
            desc = clean(next_el.get_text()) if next_el else ""
            sid = text.lower().replace(" ", "").replace("-", "").replace("'", "")
            if text and desc:
                specialties.append({"id": sid, "label": text, "description": desc})

    # Hardcode colour map (visual only — not on Serebii)
    COLOR_MAP = {
        "appraise": "#a5d6a7", "build": "#8d6e63", "bulldoze": "#6d4c41",
        "burn": "#f08030", "chop": "#795548", "collect": "#ffd54f",
        "crush": "#607d8b", "dj": "#ce93d8", "dreamisland": "#64b5f6",
        "eat": "#ffb74d", "engineer": "#9e9e9e", "explode": "#ff5722",
        "fly": "#4fc3f7", "gather": "#ffc107", "gatherhoney": "#ffcc02",
        "generate": "#fdd835", "grow": "#4caf50", "hype": "#ec407a",
        "illuminate": "#fff176", "litter": "#78909c", "paint": "#f06292",
        "party": "#ff8a65", "rarify": "#e040fb", "recycle": "#9ccc65",
        "search": "#26c6da", "storage": "#90a4ae", "teleport": "#ab47bc",
        "trade": "#ffa726", "transform": "#90a4ae", "water": "#29b6f6",
        "yawn": "#9575cd",
    }
    # NPC-only specialties
    NPC_ONLY = {"appraise", "dj", "eat", "engineer", "illuminate", "party", "rarify"}

    for s in specialties:
        s["color"] = COLOR_MAP.get(s["id"], "#9e9e9e")
        if s["id"] in NPC_ONLY:
            s["npc_only"] = True

    write_python(DATA / "specialties.py", "SPECIALTIES", specialties,
                 "Pokémon Pokopia specialties from Serebii")
    return specialties


# ── 2. AVAILABLE POKÉMON ──────────────────────────────────────────────────────

def get_specialties_from_row(row):
    """Extract specialties from a table row using img alt text first, then text fallback."""
    specs = []
    # Primary: img alt attributes (Serebii uses specialty icons)
    for img in row.find_all("img"):
        alt = clean(img.get("alt", ""))
        if alt in VALID_SPECS:
            specs.append(alt)
    # If no img-based specs found, try text-based parsing
    if not specs:
        for cell in row.find_all("td"):
            text = clean(cell.get_text())
            if text in VALID_SPECS:
                specs.append(text)
            else:
                # Try splitting on capital letters for concatenated strings
                parts = re.findall(r"[A-Z][a-z]+(?:\s[A-Z][a-z]+)*", text)
                for p in parts:
                    if p in VALID_SPECS:
                        specs.append(p)
    # Deduplicate preserving order
    seen = set()
    return [s for s in specs if not (s in seen or seen.add(s))]


def parse_pokemon_table(soup, source="main"):
    """Parse Pokémon rows from an available-pokemon style table."""
    pokemon = []
    seen_entries = set()

    for row in soup.select("table tr"):
        cells = row.find_all("td")
        if len(cells) < 3:
            continue

        # Look for a dex-number cell (e.g. "#001" or "001")
        num_text = clean(cells[0].get_text())
        num_match = re.search(r"^#?(\d{1,3})$", num_text)
        if not num_match:
            continue
        pokopia_num = int(num_match.group(1))

        # Name — look for a link with Pokémon name, or largest text cell
        name = ""
        for a in row.find_all("a"):
            t = clean(a.get_text())
            if t and len(t) > 1 and not re.match(r"^#?\d+$", t):
                name = t
                break
        if not name:
            for c in cells[1:4]:
                t = clean(c.get_text())
                if t and len(t) > 1 and not re.match(r"^#?\d+$", t) and t not in VALID_SPECS:
                    name = t
                    break
        if not name:
            continue

        specs = get_specialties_from_row(row)

        key = (pokopia_num, name)
        if key in seen_entries:
            continue
        seen_entries.add(key)

        pokemon.append({
            "id": pokopia_num,
            "name": name,
            "specialties": specs,
            "source": source,
        })

    return pokemon


def scrape_available_pokemon():
    print("\n[2/5] Scraping available Pokémon...")
    soup = fetch(f"{BASE}/pokemonpokopia/availablepokemon.shtml")
    pokemon = parse_pokemon_table(soup, source="main")
    print(f"  Found {len(pokemon)} main Pokémon entries")
    return pokemon


def scrape_event_pokemon():
    print("\n[3/5] Scraping event Pokémon...")
    soup = fetch(f"{BASE}/pokemonpokopia/eventpokedex.shtml")
    pokemon = parse_pokemon_table(soup, source="event")
    print(f"  Found {len(pokemon)} event Pokémon entries")
    return pokemon


def scrape_legendary_pokemon():
    print("\n[4/5] Scraping legendary Pokémon...")
    soup = fetch(f"{BASE}/pokemonpokopia/legendary.shtml")

    legendaries = []
    seen_names = set()

    for row in soup.select("table tr"):
        cells = row.find_all("td")
        if len(cells) < 2:
            continue
        name = clean(cells[0].get_text())
        if not name or name.lower() in ("pokémon", "pokemon", "name", "method"):
            continue
        if len(name) < 2 or any(c.isdigit() for c in name[:2]):
            continue
        details = " ".join(clean(c.get_text()) for c in cells[1:])
        if name not in seen_names:
            seen_names.add(name)
            legendaries.append({
                "name": name,
                "details": details,
            })

    print(f"  Found {len(legendaries)} legendary entries")
    return legendaries


# ── 3. HABITATS ───────────────────────────────────────────────────────────────

def scrape_habitats():
    print("\n[5/5] Scraping habitats...")
    soup = fetch(f"{BASE}/pokemonpokopia/habitats.shtml")

    habitats = []
    seen_names = set()
    hab_num = 0

    for row in soup.select("table tr"):
        cells = row.find_all("td")
        if len(cells) < 2:
            continue

        # Skip header rows
        if row.find("th") or cells[0].find("b") and clean(cells[0].get_text()) in ("Picture", "No.", "#"):
            continue

        # Number: first cell or from image src
        num_text = clean(cells[0].get_text())
        num_match = re.search(r"^#?(\d+)$", num_text)

        # Name: check img alt, then link text, then short text cell
        name = ""
        for img in row.find_all("img"):
            alt = clean(img.get("alt", ""))
            if alt and len(alt) > 3 and not alt.isdigit() and alt not in ("Picture",):
                name = alt
                break
        if not name:
            for a in row.find_all("a"):
                t = clean(a.get_text())
                if t and len(t) > 3 and not t.isdigit():
                    name = t
                    break
        if not name:
            # Look for a cell that is short enough to be a name (not a description)
            for c in cells[1:]:
                t = clean(c.get_text())
                if t and 3 < len(t) < 60 and not t.isdigit() and not t.startswith("#"):
                    # Descriptions tend to be longer sentences
                    if not re.search(r"\.\s", t) and t not in ("Picture", "Description"):
                        name = t
                        break

        # Description: longest text cell
        desc = ""
        for c in cells:
            t = clean(c.get_text())
            if t and len(t) > len(desc) and t != name:
                desc = t

        if not name or name in seen_names or name in ("Picture", "Description", "No.", "Name"):
            continue
        seen_names.add(name)

        if num_match:
            hab_num = int(num_match.group(1))
        else:
            hab_num += 1

        habitats.append({
            "id": hab_num,
            "name": name,
            "description": desc,
        })

    print(f"  Found {len(habitats)} habitats")
    return habitats


# ── MAIN ──────────────────────────────────────────────────────────────────────

def main():
    print("=== Pokopia Dex Scraper ===")
    print(f"Output directory: {DATA}\n")

    # Check dependencies
    try:
        import requests
        from bs4 import BeautifulSoup
    except ImportError:
        print("ERROR: Missing dependencies. Run:")
        print("  pip install requests beautifulsoup4")
        return

    specialties  = scrape_specialties()
    main_pokemon = scrape_available_pokemon()
    event_pokemon = scrape_event_pokemon()
    legendaries  = scrape_legendary_pokemon()
    habitats     = scrape_habitats()

    # Combine all Pokémon
    all_pokemon = main_pokemon + event_pokemon
    # Mark legendaries by name
    legendary_names = {e["name"] for e in legendaries}
    for p in all_pokemon:
        if p["name"] in legendary_names:
            p["rarity"] = "Legendary"

    write_python(DATA / "pokemon.py",   "POKEMON",   all_pokemon,
                 "All Pokémon in Pokémon Pokopia from Serebii")
    write_python(DATA / "habitats.py",  "HABITATS",  habitats,
                 "All habitats in Pokémon Pokopia from Serebii")
    write_python(DATA / "specialties.py", "SPECIALTIES", specialties,
                 "All specialties in Pokémon Pokopia from Serebii")
    write_python(DATA / "legendaries.py", "LEGENDARIES", legendaries,
                 "Legendary/Mythical Pokémon details from Serebii")

    print(f"\n=== Done ===")
    print(f"  {len(main_pokemon)} main Pokémon")
    print(f"  {len(event_pokemon)} event Pokémon")
    print(f"  {len(legendaries)} legendaries")
    print(f"  {len(habitats)} habitats")
    print(f"  {len(specialties)} specialties")
    print(f"\nNext: run  python build.py  to generate pokopia-dex.html")


if __name__ == "__main__":
    main()

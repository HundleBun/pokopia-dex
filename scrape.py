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

def make_slug(name):
    """Convert habitat name to Serebii URL slug.
    Rule: lowercase, strip spaces, KEEP hyphens and apostrophes.
    e.g. "Chef's kitchen" → "chef'skitchen"
         "Piping-hot lava" → "piping-hotlava"
    """
    slug = name.lower()
    slug = slug.replace(" ", "")                     # strip spaces only
    slug = re.sub(r"[^a-z0-9\-'\u00c0-\u024f]", "", slug)  # keep hyphens, apostrophes, accented chars
    return slug


KNOWN_ZONES = [
    "Withered Wastelands", "Bleak Beach", "Rocky Ridges",
    "Sparkling Skylands", "Palette Town", "Cloud Island",
]
KNOWN_TIMES    = {"Morning", "Day", "Evening", "Night"}
KNOWN_WEATHER  = {"Sun", "Cloud", "Rain", "Snow", "Fog"}
SKIP_NAMES     = {"time", "weather", "location", "rarity", "image",
                  "name", "quantity", "picture", "flavor text"}


def _direct_rows(table):
    """Return only direct-child <tr> elements (skip nested table rows)."""
    tbody = table.find("tbody")
    parent = tbody if tbody else table
    return parent.find_all("tr", recursive=False)


def parse_habitat_detail(soup, hab_name):
    """
    Parse a Serebii habitat detail page.

    Page structure confirmed by inspection:
      Table 0-2 : Navigation / logo / flavor text
      Table 3   : Build requirements  — headers: Image | Name | Quantity
      Table 4   : Pokémon data table  — groups of 4 direct rows:
                      row A: N Pokémon names (one per column)
                      row B: N Pokémon images
                      row C: N "Location : <zones>" cells
                      row D: N "Rarity : <rarity>" cells
                  (nested time/weather tables appear as child rows too —
                   we skip them by only taking direct rows)
      Table 5+  : One 2-row "Time / Weather" table per Pokémon (in order)

    Returns:
        requirements: list of {"item": str, "qty": int}
        pokemon_entries: list of {"name": str, "rarity": str,
                                  "time": list, "weather": list, "zones": list}
    """
    requirements = []
    pokemon_entries = []

    tables = soup.find_all("table")

    # ── 1. Build requirements ─────────────────────────────────────────────────
    for table in tables:
        rows = _direct_rows(table)
        if not rows:
            continue
        header_cells = rows[0].find_all(["th", "td"])
        header_texts = [clean(c.get_text()).lower() for c in header_cells]
        if "quantity" in header_texts or "qty" in header_texts:
            for row in rows[1:]:
                cells = row.find_all("td")
                if len(cells) < 2:
                    continue
                item = ""
                qty  = 0
                for c in cells:
                    t = clean(c.get_text())
                    if re.fullmatch(r"\d+", t):
                        qty = int(t)
                    elif t and len(t) > 1:
                        item = t
                if item and qty:
                    requirements.append({"item": item, "qty": qty})
            break

    # ── 2. Pokémon data table ─────────────────────────────────────────────────
    # Find the table whose direct rows contain "Location:" or "Location :" cells
    poke_table = None
    for table in tables:
        full_text = table.get_text()
        if "Location" in full_text and "Rarity" in full_text:
            poke_table = table
            break

    if poke_table is None:
        return requirements, pokemon_entries

    direct_rows = _direct_rows(poke_table)

    # Each group = 5 direct rows:
    #   0: Pokémon names  (N cells, one per Pokémon)
    #   1: Pokémon images (N cells, empty text)
    #   2: "Location : ..." (N cells)
    #   3: "Rarity : ..."   (N cells)
    #   4: "Time Weather ..." (N cells, each cell contains nested table text)
    i = 0
    while i < len(direct_rows):
        row = direct_rows[i]
        cells = row.find_all("td", recursive=False)
        if not cells:
            i += 1
            continue

        cell_texts = [clean(c.get_text()) for c in cells]

        # Name row: all cells are short Pokémon names (no Location/Rarity/Time prefix)
        is_name_row = (
            len(cell_texts) >= 1
            and all(
                t
                and len(t) < 60
                and not t.lower().startswith(("location", "rarity", "time", "weather"))
                and t.lower() not in SKIP_NAMES
                for t in cell_texts
            )
            and any(
                re.search(r"[a-zA-Z]", t) and 2 <= len(t) <= 50
                for t in cell_texts
            )
        )

        if not is_name_row:
            i += 1
            continue

        names = [t for t in cell_texts if t and len(t) >= 2 and re.search(r"[a-zA-Z]", t)]
        n = len(names)

        # Location row (i+2)
        zones_per_poke = [""] * n
        if i + 2 < len(direct_rows):
            loc_cells = direct_rows[i + 2].find_all("td", recursive=False)
            for j, lc in enumerate(loc_cells[:n]):
                t = clean(lc.get_text(" "))
                m = re.match(r"Location\s*:\s*(.*)", t, re.IGNORECASE)
                if m:
                    zones_per_poke[j] = m.group(1).strip()

        # Rarity row (i+3)
        rarities = [""] * n
        if i + 3 < len(direct_rows):
            rar_cells = direct_rows[i + 3].find_all("td", recursive=False)
            for j, rc in enumerate(rar_cells[:n]):
                t = clean(rc.get_text(" "))
                m = re.match(r"Rarity\s*:\s*(.*)", t, re.IGNORECASE)
                if m:
                    rarities[j] = m.group(1).strip()

        # Time/Weather row (i+4): each cell contains a nested table
        # Use get_text(" ") with separator so concatenated words get spaces
        times_per_poke   = [[] for _ in range(n)]
        weather_per_poke = [[] for _ in range(n)]
        if i + 4 < len(direct_rows):
            tw_cells = direct_rows[i + 4].find_all("td", recursive=False)
            for j, tc in enumerate(tw_cells[:n]):
                # get_text(" ") adds space between elements, splitting concatenated words
                words = re.split(r"\s+", tc.get_text(" ").strip())
                for w in words:
                    if w in KNOWN_TIMES:
                        times_per_poke[j].append(w)
                    elif w in KNOWN_WEATHER:
                        weather_per_poke[j].append(w)

        for j, name in enumerate(names):
            zones = [z for z in KNOWN_ZONES if z in zones_per_poke[j]]
            t_vals = times_per_poke[j]   or list(KNOWN_TIMES)
            w_vals = weather_per_poke[j] or ["Sun", "Cloud", "Rain"]
            pokemon_entries.append({
                "name":    name,
                "rarity":  rarities[j],
                "time":    t_vals,
                "weather": w_vals,
                "zones":   zones,
            })

        i += 5  # advance past this full group

    return requirements, pokemon_entries


def scrape_habitat_details(habitats, all_pokemon):
    """
    Fetch individual habitat detail pages, enrich habitats with build requirements
    and Pokémon lists, and aggregate per-Pokémon zone/time/weather/rarity data.
    Returns enriched (habitats, all_pokemon).
    """
    print(f"\n[6/6] Scraping {len(habitats)} habitat detail pages...")

    # Build lookup: pokemon name → index in all_pokemon
    poke_idx = {p["name"].lower(): i for i, p in enumerate(all_pokemon)}

    # Track per-Pokémon aggregated data across all habitats
    poke_data = {}  # name_lower → {"rarity": str, "time": set, "weather": set, "zones": set}

    total = len(habitats)
    ok = 0
    fail = 0

    for i, hab in enumerate(habitats):
        slug = make_slug(hab["name"])
        url = f"{BASE}/pokemonpokopia/habitatdex/{slug}.shtml"
        try:
            soup = fetch(url, delay=1.0)
            reqs, poke_entries = parse_habitat_detail(soup, hab["name"])

            if reqs:
                hab["requirements"] = reqs
            if poke_entries:
                hab["pokemon"] = [e["name"] for e in poke_entries]

            for entry in poke_entries:
                key = entry["name"].lower()
                if key not in poke_data:
                    poke_data[key] = {
                        "rarity": entry["rarity"] or "",
                        "time": set(entry["time"]),
                        "weather": set(entry["weather"]),
                        "zones": set(entry["zones"]),
                    }
                else:
                    # Merge: take highest rarity seen, union of time/weather/zones
                    if not poke_data[key]["rarity"] and entry["rarity"]:
                        poke_data[key]["rarity"] = entry["rarity"]
                    poke_data[key]["time"].update(entry["time"])
                    poke_data[key]["weather"].update(entry["weather"])
                    poke_data[key]["zones"].update(entry["zones"])

            ok += 1
            print(f"  [{i+1}/{total}] {hab['name']} — {len(poke_entries)} Pokémon, {len(reqs)} req items")

        except Exception as e:
            fail += 1
            print(f"  [{i+1}/{total}] SKIP {hab['name']} ({slug}) — {e}")

    # Write back aggregated data to pokemon list
    TIME_ORDER = ["Morning", "Day", "Evening", "Night"]
    WEATHER_ORDER = ["Sun", "Cloud", "Rain", "Snow", "Fog"]

    for p in all_pokemon:
        key = p["name"].lower()
        if key in poke_data:
            d = poke_data[key]
            if d["rarity"] and not p.get("rarity"):
                p["rarity"] = d["rarity"]
            if d["time"]:
                p["time"] = [t for t in TIME_ORDER if t in d["time"]]
            if d["weather"]:
                p["weather"] = [w for w in WEATHER_ORDER if w in d["weather"]]
            if d["zones"]:
                p["zones"] = sorted(d["zones"])

    print(f"\n  Detail pages: {ok} ok, {fail} skipped")
    return habitats, all_pokemon


def scrape_habitats():
    print("\n[5/6] Scraping habitats...")
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

    specialties   = scrape_specialties()
    main_pokemon  = scrape_available_pokemon()
    event_pokemon = scrape_event_pokemon()
    legendaries   = scrape_legendary_pokemon()
    habitats      = scrape_habitats()

    # Combine all Pokémon
    all_pokemon = main_pokemon + event_pokemon
    # Mark legendaries by name
    legendary_names = {e["name"] for e in legendaries}
    for p in all_pokemon:
        if p["name"] in legendary_names:
            p["rarity"] = "Legendary"

    # Enrich with per-habitat detail data (zones, time, weather, build requirements)
    habitats, all_pokemon = scrape_habitat_details(habitats, all_pokemon)

    write_python(DATA / "pokemon.py",     "POKEMON",     all_pokemon,
                 "All Pokémon in Pokémon Pokopia from Serebii")
    write_python(DATA / "habitats.py",    "HABITATS",    habitats,
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


def main_details_only():
    """Re-run only the habitat detail scrape using existing JSON data files."""
    print("=== Pokopia Dex — Habitat Details Re-Scrape ===")
    print(f"Loading existing data from {DATA}\n")

    try:
        import requests
        from bs4 import BeautifulSoup
    except ImportError:
        print("ERROR: Missing dependencies. Run:  pip install requests beautifulsoup4")
        return

    with open(DATA / "pokemon.json", encoding="utf-8") as f:
        all_pokemon = json.load(f)
    with open(DATA / "habitats.json", encoding="utf-8") as f:
        habitats = json.load(f)

    habitats, all_pokemon = scrape_habitat_details(habitats, all_pokemon)

    write_json(DATA / "pokemon.json", all_pokemon)
    write_json(DATA / "habitats.json", habitats)

    has_zones = sum(1 for p in all_pokemon if p.get("zones"))
    hab_with_reqs = sum(1 for h in habitats if h.get("requirements"))
    print(f"\n=== Done ===")
    print(f"  {has_zones}/{len(all_pokemon)} Pokémon with zone data")
    print(f"  {hab_with_reqs}/{len(habitats)} habitats with build requirements")
    print(f"\nNext: run  python build.py  to regenerate pokopia-dex.html")


if __name__ == "__main__":
    import sys
    if "--details-only" in sys.argv:
        main_details_only()
    else:
        main()

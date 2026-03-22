#!/usr/bin/env python3
"""
cross_reference_game8.py — Fetch spawn data from game8.co for every Pokemon
in pokemon.json and compare against current values for zones, time, weather,
rarity, and habitat (How to Build).

Usage:
    python data/cross_reference_game8.py

Outputs:
    data/zone_diff_report.txt   — human-readable diff for all fields
    data/zone_corrections.json  — machine-readable {name: {field: correct_value}}
"""

import json, re, sys, time
from pathlib import Path
import requests
from bs4 import BeautifulSoup, Tag

# Force UTF-8 output so non-Latin characters in habitat names don't crash print()
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).parent
DATA = ROOT

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    )
}

# ── Zone name normalisation ────────────────────────────────────────────────────
# game8 uses slightly different names in some places; map to our canonical names
ZONE_ALIASES = {
    "withered wasteland":   "Withered Wastelands",
    "withered wastelands":  "Withered Wastelands",
    "bleak beach":          "Bleak Beach",
    "rocky ridges":         "Rocky Ridges",
    "sparkling skylands":   "Sparkling Skylands",
    "palette town":         "Palette Town",
    "cloud island":         "Cloud Island",
}
ALL_ZONES = sorted(set(ZONE_ALIASES.values()))  # canonical set, deduplicated

# ── Time-of-day normalisation ──────────────────────────────────────────────────
TIME_ALIASES = {
    "dawn":  "Morning",
    "day":   "Day",
    "dusk":  "Evening",
    "night": "Night",
}
TIME_ORDER = ["Morning", "Day", "Evening", "Night"]

# ── Weather normalisation ──────────────────────────────────────────────────────
WEATHER_ALIASES = {
    "sunny":  "Sun",
    "cloudy": "Cloud",
    "rainy":  "Rain",
}

# ── Rarity normalisation ───────────────────────────────────────────────────────
RARITY_ORDER = ["Common", "Rare", "Very Rare"]
RARITY_ALIASES = {
    "common":    "Common",
    "rare":      "Rare",
    "very rare": "Very Rare",
}

# ── game8 archive ID map ───────────────────────────────────────────────────────
# Format: "Pokemon Name": archive_id
# Gathered from game8.co gen list pages.  None = no page found yet.
GAME8_IDS = {
    # Gen 1
    "Bulbasaur": 584907, "Ivysaur": 584909, "Venusaur": 585523,
    "Charmander": 584910, "Charmeleon": 584911, "Charizard": 585385,
    "Squirtle": 584912, "Wartortle": 584913, "Blastoise": 585375,
    "Pidgey": 584914, "Pidgeotto": 585376,
    "Oddish": 584915, "Gloom": 584916, "Vileplume": 585612,
    "Paras": 585377, "Parasect": 585378,
    "Venonat": 584917, "Venomoth": 584918,
    "Bellsprout": 584919, "Weepinbell": 584920, "Victreebel": 584921,
    "Slowpoke": 584922, "Slowbro": 584923,
    "Magnemite": 585380, "Magneton": 584924,
    "Onix": 584925,
    "Cubone": 585194, "Marowak": 585382,
    "Hitmonlee": 584926, "Hitmonchan": 584927,
    "Koffing": 585891, "Weezing": 585892,
    "Scyther": 584928, "Pinsir": 584930,
    "Magikarp": 584931, "Gyarados": 585536,
    "Pikachu": 585510, "Raichu": 585391,
    "Zubat": 584949, "Golbat": 584950,
    "Meowth": 584952, "Persian": 585534,
    "Psyduck": 585392,
    "Growlithe": 584953, "Arcanine": 585393,
    "Farfetch'd": 584954,
    "Grimer": 585893, "Muk": 585894,
    "Gastly": 585895, "Haunter": 585896,
    "Voltorb": 584955, "Electrode": 584956,
    "Exeggcute": 584957, "Exeggutor": 584958,
    "Chansey": 585897,
    "Electabuzz": 585533,
    "Lapras": 584961,
    "Snorlax": 585889,
    "Ekans": 585617, "Arbok": 585616,
    "Clefairy": 585614, "Clefable": 585395,
    "Jigglypuff": 585596,
    "Diglett": 584985, "Dugtrio": 585611,
    "Machop": 584986, "Machoke": 584987, "Machamp": 585610,
    "Geodude": 584988, "Graveler": 584989, "Golem": 585609,
    "Magmar": 584991,
    "Vulpix": 585356, "Ninetales": 585902,
    "Poliwhirl": 585903, "Poliwrath": 585527,
    "Abra": 585904, "Alakazam": 585526,
    "Mr. Mime": 585357,
    "Dratini": 585599, "Dragonair": 585907, "Dragonite": 585358,
    "Aerodactyl": 585514,
    "Eevee": 585009,
    "Vaporeon": 585010, "Jolteon": 585011, "Flareon": 585012,
    "Espeon": 585013, "Umbreon": 585014,
    # Gen 2
    "Hoppip": 585371, "Skiploom": 585372, "Jumpluff": 585373,
    "Bellossom": 585627,
    "Slowking": 585379,
    "Steelix": 585381,
    "Tyrogue": 585383, "Hitmontop": 585384,
    "Scizor": 584929,
    "Hoothoot": 584932, "Noctowl": 584933,
    "Heracross": 584934,
    "Pichu": 585535,
    "Crobat": 584951,
    "Elekid": 585623,
    "Spinarak": 584962, "Ariados": 584963,
    "Mareep": 584964, "Flaaffy": 584965, "Ampharos": 585622,
    "Marill": 584967, "Azumarill": 584968,
    "Cleffa": 585615, "Igglybuff": 585613,
    "Magby": 584990,
    "Sudowoodo": 585607,
    "Murkrow": 585606,
    "Larvitar": 584992, "Pupitar": 585351, "Tyranitar": 585605,
    "Politoed": 585600,
    "Porygon2": 585524,
    "Cyndaquil": 585881, "Quilava": 585509,
    "Misdreavus": 585359,
    "Girafarig": 585360,
    # Gen 3
    "Sableye": 585597,
    "Volbeat": 585374, "Illumise": 584935,
    "Gulpin": 584936, "Swalot": None,
    "Cacnea": 585386, "Cacturne": 584937,
    "Azurill": 584966,
    "Torchic": 584969, "Combusken": 585898, "Blaziken": 585619,
    "Wingull": 584970, "Pelipper": 584971,
    "Makuhita": 584972, "Hariyama": 584973,
    "Lotad": 584993, "Lombre": 584994, "Ludicolo": 584995,
    "Mawile": 585900,
    "Torkoal": 584996,
    "Ralts": 585873, "Kirlia": None, "Gardevoir": None, "Gallade": 585874,
    "Plusle": 585875, "Minun": 585876,
    "Trapinch": 585361, "Vibrava": 585521, "Flygon": 585877,
    "Swablu": 585520, "Altaria": 585350,
    "Duskull": 585519, "Dusclops": 585878,
    "Metang": 585363, "Metagross": None,
    "Absol": None,
    "Beldum": None,
    # Gen 4
    "Magnezone": 585899,
    "Combee": 584938, "Vespiquen": 584939,
    "Shellos": 584940, "Shellos East Sea": 584940,
    "Gastrodon": 585443, "Gastrodon East Sea": 585443,
    "Drifloon": 584941, "Drifblim": None,
    "Happiny": 584959,
    "Electivire": 584960,
    "Piplup": 584974, "Prinplup": 584975, "Empoleon": None,
    "Bonsly": 585608,
    "Honchkrow": 585362,
    "Kricketot": 584997, "Kricketune": 585604,
    "Chatot": 584998,
    "Riolu": 584999, "Lucario": 585603,
    "Mime Jr.": 585905,
    "Porygon-Z": 585906,
    "Mismagius": 585872,
    "Dusknoir": 585879,
    "Rampardos": 585887, "Cranidos": None,
    "Shieldon": 585513, "Bastiodon": 585512,
    "Leafeon": 585015, "Glaceon": 585016,
    # Gen 5
    "Drilbur": 584942, "Excadrill": 584943,
    "Timburr": 584944, "Gurdurr": 584945, "Conkeldurr": 585387,
    "Litwick": 585626, "Lampent": 585625, "Chandelure": 585624,
    "Axew": 585388, "Fraxure": 584946, "Haxorus": 585389,
    "Audino": 584976,
    "Trubbish": 584977, "Garbodor": 584978,
    "Zorua": 584979, "Zoroark": 584980,
    "Minccino": 584981, "Cinccino": None,
    "Larvesta": 585602, "Volcarona": 585601,
    "Snivy": 585364, "Servine": 585365, "Serperior": 585880,
    # Gen 6
    "Goomy": 584947, "Sliggoo": 584948, "Goodra": None,
    "Porygon": 585525,
    "Froakie": 585366, "Frogadier": 585871, "Greninja": 585882,
    "Dedenne": 585518,
    "Noibat": 585883, "Noivern": None,
    "Tyrunt": 585888, "Tyrantrum": 585008,
    "Amaura": None, "Aurorus": 585511,
    "Sylveon": 585017,
    # Gen 7
    "Grubbin": 584982, "Charjabug": 585618, "Vikavolt": 585394,
    "Mimikyu": 585890,
    "Rowlet": 585352, "Dartrix": 585000, "Decidueye": 585531,
    # Gen 8
    "Cramorant": 585390,
    "Scorbunny": 585001, "Raboot": 585353, "Cinderace": 585530,
    "Skwovet": 585354, "Greedent": None,
    "Rolycoly": 585002, "Carkol": 585003, "Coalossal": None,
    "Toxel": 585529,
    "Toxtricity Amped Form": None, "Toxtricity Low Key Form": None,
    "Rookidee": 585367, "Corvisquire": 585368, "Corviknight": 585884,
    "Dreepy": 585369, "Drakloak": 585598, "Dragapult": None,
    # Gen 9
    "Paldean Wooper": 585621, "Clodsire": 585620,
    "Pawmi": 584983, "Pawmo": 584984, "Pawmot": 585532,
    "Fidough": 585004, "Dachsbun": 585355,
    "Charcadet": 585005, "Ceruledge": 585901,
    "Glimmet": 585006, "Glimmora": 585528,
    "Gimmighoul": 585007,
    "Farigiraf": 585522,
    "Sprigatito": 585370, "Floragato": None, "Meowscarada": 585885,
    "Wattrel": 585517, "Kilowattrel": 585886,
    "Tinkatink": 585516, "Tinkatuff": 585515, "Tinkaton": None,
    # Special / forms with no separate page expected
    "Ditto": None,
    "Tangela": None, "Tangrowth": None,
    "Munchlax": None,
    "Poliwag": None,
    "Golduck": None,
    "Smeargle": None,
    "Wigglytuff": None,
    "Kadabra": None,
    "Gengar": None,
    "Tatsugiri Curly Form": None,
    "Tatsugiri Droopy Form": None,
    "Tatsugiri Stretchy Form": None,
    "Blissey": None,
    "Magmortar": None,
    "Typhlosion": None,
    "Cinccino": None,
    # Legendaries / events (usually no habitat)
    "Articuno": None, "Zapdos": None, "Moltres": None,
    "Mewtwo": None, "Mew": None,
    "Raikou": None, "Entei": None, "Suicune": None,
    "Ho-Oh": None, "Lugia": None,
    "Kyogre": None, "Volcanion": None,
    # NPCs / special
    "Professor Tangrowth": None, "Peakychu": None,
    "Mosslax": None, "Stereo Rotom": None,
}


def fetch(url, retries=3, delay=1.5):
    for attempt in range(retries):
        try:
            r = requests.get(url, headers=HEADERS, timeout=15)
            r.raise_for_status()
            time.sleep(delay)
            return BeautifulSoup(r.text, "html.parser")
        except Exception as e:
            if attempt < retries - 1:
                time.sleep(3)
            else:
                raise e


def extract_labeled_fields(soup):
    """
    Walk every <b class="a-bold">Label:</b> on the page and collect the values
    that follow it (up to the next <b class="a-bold"> tag).

    Three value layouts exist on game8:
      1. <div class="align"><a><img alt="Value"/>Value</a></div>  — image+link
      2. <a class="a-link">Value</a>                              — bare link
      3. NavigableString "Value"                                  — bare text (e.g. Rarity)

    Returns a list of (label_str, [value_str, ...]) tuples, one per label
    occurrence (a pokemon may have multiple spawn rows, each with its own set).
    """
    results = []
    for b in soup.find_all("b", class_="a-bold"):
        label = b.get_text(strip=True).rstrip(":")
        values = []
        for sibling in b.next_siblings:
            if isinstance(sibling, Tag):
                if sibling.name == "b":
                    break  # next label — stop collecting
                if sibling.name == "div" and "align" in sibling.get("class", []):
                    # Collect all img alts first — time/weather icons are bare <img>,
                    # not wrapped in <a>, so this catches Dawn/Day/Dusk/Night etc.
                    for img in sibling.find_all("img"):
                        alt = img.get("alt", "").strip()
                        if alt and alt not in values:
                            values.append(alt)
                    # Collect link text — biome/zone links use <a> with text
                    for a in sibling.find_all("a"):
                        txt = a.get_text(strip=True)
                        if txt and txt not in values:
                            values.append(txt)
                    # Fallback: plain text in div with no tags at all
                    if not sibling.find_all(["a", "img"]):
                        bare = sibling.get_text(" ", strip=True)
                        if bare:
                            values.append(bare)
                elif sibling.name == "a":
                    txt = sibling.get_text(strip=True)
                    if txt:
                        values.append(txt)
            else:
                # NavigableString — captures bare text like "Common" after Rarity:
                text = str(sibling).strip()
                if text:
                    values.append(text)
        if values:
            results.append((label, values))
    return results


def extract_all_from_page(soup):
    """
    Extract zones, time, weather, rarity, and habitat from a game8 page.
    Aggregates across all spawn rows (union for sets; lowest tier for rarity).

    Returns a dict with keys: zones, time, weather, rarity, habitats.
    Each value is a sorted list (or single string for rarity), or None if
    that field was not found on the page.
    """
    zones    = set()
    times    = set()
    weathers = set()
    rarities = set()
    habitats = set()

    for label, values in extract_labeled_fields(soup):
        ll = label.lower()

        if "biome" in ll:
            for v in values:
                vl = v.lower()
                if "any area" in vl or "any biome" in vl:
                    zones.update(ALL_ZONES)
                else:
                    for alias, canonical in ZONE_ALIASES.items():
                        if alias in vl:
                            zones.add(canonical)

        elif "time" in ll:
            for v in values:
                canonical = TIME_ALIASES.get(v.lower())
                if canonical:
                    times.add(canonical)

        elif "weather" in ll:
            for v in values:
                canonical = WEATHER_ALIASES.get(v.lower())
                if canonical:
                    weathers.add(canonical)

        elif "rarity" in ll:
            for v in values:
                canonical = RARITY_ALIASES.get(v.lower())
                if canonical:
                    rarities.add(canonical)

        elif "how to build" in ll:
            for v in values:
                habitats.add(v)

    def time_sort(x):
        return TIME_ORDER.index(x) if x in TIME_ORDER else 99

    def rarity_sort(x):
        return RARITY_ORDER.index(x) if x in RARITY_ORDER else 99

    return {
        "zones":    sorted(zones)              or None,
        "time":     sorted(times, key=time_sort) or None,
        "weather":  sorted(weathers)           or None,
        "rarity":   sorted(rarities, key=rarity_sort)[0] if rarities else None,
        "habitats": sorted(habitats)           or None,
    }


def main():
    with open(DATA / "pokemon.json", encoding="utf-8") as f:
        pokemon_list = json.load(f)

    # Build lookup: name → current values for each field
    current = {}
    for p in pokemon_list:
        current[p["name"]] = {
            "zones":   sorted(p.get("zones", [])),
            "time":    sorted(p.get("time", [])),
            "weather": sorted(p.get("weather", [])),
            "rarity":  p.get("rarity", ""),
        }

    corrections   = {}  # name → {field: game8_value} for any field that differs
    no_page       = []  # names with no game8 ID
    parse_fail    = []  # (name, reason) for pages that returned no zone data
    matches       = []  # names where all fields agree
    discrepancies = []  # (name, {field: (current, game8)}) for differing fields

    total = len([n for n in current if GAME8_IDS.get(n) is not None])
    done  = 0
    consecutive_none = 0

    print(f"Fetching {total} game8 pages...\n")

    for poke_name in sorted(current):
        archive_id = GAME8_IDS.get(poke_name)

        if archive_id is None:
            no_page.append(poke_name)
            continue

        url = f"https://game8.co/games/Pokemon-Pokopia/archives/{archive_id}"
        try:
            soup = fetch(url)
        except Exception as e:
            parse_fail.append((poke_name, f"fetch error: {e}"))
            continue

        g8 = extract_all_from_page(soup)
        done += 1
        print(f"  [{done}/{total}] {poke_name}: zones={g8['zones']}  time={g8['time']}  "
              f"weather={g8['weather']}  rarity={g8['rarity']}  habitats={g8['habitats']}")

        if g8["zones"] is None:
            consecutive_none += 1
            if consecutive_none >= 5:
                print("\nABORTED: 5 consecutive None results — parser is likely broken. Check page structure.")
                return
            parse_fail.append((poke_name, "no zones found on page"))
            continue
        else:
            consecutive_none = 0

        cur = current[poke_name]
        diffs = {}

        if g8["zones"] is not None and sorted(g8["zones"]) != cur["zones"]:
            diffs["zones"] = (cur["zones"], sorted(g8["zones"]))
        if g8["time"] is not None and sorted(g8["time"]) != cur["time"]:
            diffs["time"] = (cur["time"], sorted(g8["time"]))
        if g8["weather"] is not None and sorted(g8["weather"]) != cur["weather"]:
            diffs["weather"] = (cur["weather"], sorted(g8["weather"]))
        if g8["rarity"] is not None and g8["rarity"] != cur["rarity"]:
            diffs["rarity"] = (cur["rarity"], g8["rarity"])

        if diffs:
            discrepancies.append((poke_name, diffs))
            corr = {field: g8_val for field, (_, g8_val) in diffs.items()}
            # Always include habitats if found — it's new data not yet in our JSON
            if g8["habitats"]:
                corr["habitats"] = g8["habitats"]
            corrections[poke_name] = corr
        else:
            matches.append(poke_name)
            # Still record new habitat data even when other fields match
            if g8["habitats"]:
                corrections.setdefault(poke_name, {})["habitats"] = g8["habitats"]

    # ── Write report ──────────────────────────────────────────────────────────
    lines = []
    lines.append("=" * 70)
    lines.append("FULL CROSS-REFERENCE REPORT  (Serebii vs game8.co)")
    lines.append("=" * 70)
    lines.append(f"\nChecked : {done} pokemon")
    lines.append(f"Match   : {len(matches)}")
    lines.append(f"Diff    : {len(discrepancies)}")
    lines.append(f"No page : {len(no_page)}")
    lines.append(f"Errors  : {len(parse_fail)}")

    lines.append("\n" + "-" * 70)
    lines.append("DISCREPANCIES  (current → game8 correct)")
    lines.append("-" * 70)
    for name, diffs in sorted(discrepancies):
        lines.append(f"\n{name}")
        for field, (cur_val, g8_val) in diffs.items():
            lines.append(f"  {field:<10} current: {cur_val}")
            lines.append(f"  {'':<10} game8  : {g8_val}")

    lines.append("\n" + "-" * 70)
    lines.append("NO GAME8 PAGE (skipped)")
    lines.append("-" * 70)
    for name in sorted(no_page):
        lines.append(f"  {name}")

    if parse_fail:
        lines.append("\n" + "-" * 70)
        lines.append("PARSE / FETCH FAILURES")
        lines.append("-" * 70)
        for name, reason in parse_fail:
            lines.append(f"  {name}: {reason}")

    report_path = DATA / "zone_diff_report.txt"
    report_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"\nReport written to {report_path}")

    corrections_path = DATA / "zone_corrections.json"
    with open(corrections_path, "w", encoding="utf-8") as f:
        json.dump(corrections, f, indent=2, ensure_ascii=False)
    print(f"Corrections written to {corrections_path}")
    print(f"\n{len(discrepancies)} pokemon with mismatches across {done} checked.")


if __name__ == "__main__":
    main()

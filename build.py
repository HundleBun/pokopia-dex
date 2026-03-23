#!/usr/bin/env python3
"""
build.py — Generate pokopia-dex.html from scraped data files.

Usage:
    python build.py
"""

import json
from pathlib import Path

ROOT = Path(__file__).parent
DATA = ROOT / "data"
OUT  = ROOT / "pokopia-dex.html"

# ── Load data ─────────────────────────────────────────────────────────────────

def load(filename):
    with open(DATA / filename, encoding="utf-8") as f:
        return json.load(f)

pokemon    = load("pokemon.json")
habitats   = load("habitats.json")
specialties = load("specialties.json")
legendaries = load("legendaries.json")

# ── Derive useful sets ────────────────────────────────────────────────────────

legendary_names = {e["name"] for e in legendaries}
event_names     = {p["name"] for p in pokemon if p.get("source") == "event"}

# Apply rarity where we know it
for p in pokemon:
    if "rarity" not in p:
        if p["name"] in legendary_names:
            p["rarity"] = "Legendary"
        elif p["name"] in event_names:
            p["rarity"] = "Event"
        else:
            p["rarity"] = ""

# ── Serialise for JS ──────────────────────────────────────────────────────────

def js(data):
    return json.dumps(data, ensure_ascii=False)

pokemon_js     = js(pokemon)
habitats_js    = js(habitats)
specialties_js = js(specialties)

# ── HTML ──────────────────────────────────────────────────────────────────────

html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1.0"/>
<title>Pokopia Dex</title>
<link href="https://fonts.googleapis.com/css2?family=Fredoka+One&family=DM+Sans:ital,wght@0,400;0,500;0,600;0,700;1,400&display=swap" rel="stylesheet"/>
<style>
/* ═══════════════════════════════════════════
   DESIGN TOKENS
═══════════════════════════════════════════ */
:root {{
  --bg:         #0d1810;
  --surface:    #131f15;
  --card:       #192b1c;
  --card-hi:    #1e3422;
  --border:     rgba(255,255,255,0.07);
  --border-hi:  rgba(255,255,255,0.13);
  --text:       #deecd8;
  --text-soft:  #a8bfa2;
  --muted:      #637a5f;
  --accent:     #6ec84a;
  --accent2:    #b8f050;
  --shadow-sm:  0 2px 8px rgba(0,0,0,0.4);
  --shadow-md:  0 6px 24px rgba(0,0,0,0.5);
  --shadow-lg:  0 12px 48px rgba(0,0,0,0.6);
  --radius-sm:  8px;
  --radius-md:  14px;
  --radius-lg:  20px;
  --sidebar-w:  270px;
  --header-h:   60px;
}}

/* ── RESET + BASE ── */
*,*::before,*::after{{box-sizing:border-box;margin:0;padding:0}}
html{{height:100%}}
body{{
  font-family:'DM Sans',sans-serif;
  background:var(--bg);
  color:var(--text);
  height:100%;
  overflow:hidden;
  display:flex;
  flex-direction:column;
}}
body::before{{
  content:'';
  position:fixed;inset:0;pointer-events:none;z-index:0;
  background-image:
    linear-gradient(rgba(110,200,74,0.025) 1px,transparent 1px),
    linear-gradient(90deg,rgba(110,200,74,0.025) 1px,transparent 1px);
  background-size:32px 32px;
}}

/* ── HEADER ── */
.app-header{{
  height:var(--header-h);
  background:var(--surface);
  border-bottom:1px solid var(--border);
  display:flex;
  align-items:center;
  padding:0 20px;
  gap:16px;
  flex-shrink:0;
  position:relative;
  z-index:10;
}}
.app-logo{{
  font-family:'Fredoka One',cursive;
  font-size:1.35rem;
  color:var(--accent2);
  letter-spacing:0.5px;
  white-space:nowrap;
  display:flex;
  align-items:center;
  gap:7px;
}}
.app-logo span{{color:var(--muted);font-size:0.75rem;font-family:'DM Sans',sans-serif;font-weight:600;letter-spacing:1px;text-transform:uppercase}}
.header-tabs{{display:flex;gap:4px;margin-left:8px;}}
.htab{{
  font-family:'Fredoka One',cursive;
  font-size:0.88rem;
  padding:6px 16px;
  border-radius:40px;
  border:1px solid transparent;
  cursor:pointer;
  background:transparent;
  color:var(--muted);
  transition:all 0.2s;
  letter-spacing:0.3px;
}}
.htab:hover{{color:var(--text-soft);background:rgba(255,255,255,0.05)}}
.htab.active{{
  background:rgba(110,200,74,0.15);
  border-color:rgba(110,200,74,0.35);
  color:var(--accent);
}}
.header-search{{margin-left:auto;position:relative;flex-shrink:0;}}
.header-search input{{
  background:var(--card);
  border:1px solid var(--border);
  border-radius:40px;
  padding:7px 14px 7px 36px;
  color:var(--text);
  font-family:'DM Sans',sans-serif;
  font-size:0.85rem;
  width:220px;
  outline:none;
  transition:border-color 0.2s,width 0.3s;
}}
.header-search input::placeholder{{color:var(--muted)}}
.header-search input:focus{{border-color:rgba(110,200,74,0.5);width:270px;}}
.header-search .search-icon{{position:absolute;left:12px;top:50%;transform:translateY(-50%);font-size:0.85rem;color:var(--muted);pointer-events:none;}}
.results-count{{font-size:0.78rem;color:var(--muted);font-weight:600;white-space:nowrap;padding:0 4px;}}

/* ── LAYOUT ── */
.app-body{{display:flex;flex:1;overflow:hidden;position:relative;z-index:1;}}

/* ── SIDEBAR ── */
.sidebar{{
  width:var(--sidebar-w);
  flex-shrink:0;
  background:var(--surface);
  border-right:1px solid var(--border);
  overflow-y:auto;
  overflow-x:hidden;
  padding:16px 0 32px;
  scrollbar-width:thin;
  scrollbar-color:var(--card-hi) transparent;
}}
.sidebar::-webkit-scrollbar{{width:4px}}
.sidebar::-webkit-scrollbar-thumb{{background:var(--card-hi);border-radius:4px}}
.filter-group{{padding:0 14px;margin-bottom:20px}}
.filter-group-title{{
  font-size:0.62rem;font-weight:700;text-transform:uppercase;
  letter-spacing:1.8px;color:var(--muted);
  padding:0 2px;margin-bottom:8px;
  display:flex;align-items:center;justify-content:space-between;
}}
.clear-btn{{
  font-size:0.65rem;font-weight:600;color:var(--accent);
  background:none;border:none;cursor:pointer;
  padding:2px 6px;border-radius:4px;
  text-transform:none;letter-spacing:0;
  opacity:0;transition:opacity 0.2s;
}}
.clear-btn.visible{{opacity:1}}
.clear-btn:hover{{background:rgba(110,200,74,0.1)}}
.filter-pills{{display:flex;flex-wrap:wrap;gap:5px}}
.fpill{{
  font-size:0.73rem;font-weight:600;
  padding:4px 10px;border-radius:20px;
  border:1px solid var(--border);
  background:transparent;color:var(--text-soft);
  cursor:pointer;transition:all 0.18s;
  display:flex;align-items:center;gap:4px;
  white-space:nowrap;
}}
.fpill:hover{{border-color:var(--border-hi);color:var(--text)}}
.fpill.active{{border-color:transparent;color:#fff;}}
.fpill.r-legendary.active{{background:rgba(240,128,48,0.15);border-color:rgba(240,128,48,0.5);color:#ffcc80}}
.fpill.r-event.active{{background:rgba(171,71,188,0.15);border-color:rgba(171,71,188,0.5);color:#ce93d8}}
.fpill.f-zone.active{{background:rgba(41,182,246,0.15);border-color:rgba(41,182,246,0.5);color:#81d4fa}}
.fpill.f-time.active{{background:rgba(255,183,77,0.15);border-color:rgba(255,183,77,0.5);color:#ffe082}}
.fpill.f-weather.active{{background:rgba(100,181,246,0.15);border-color:rgba(100,181,246,0.5);color:#bbdefb}}
.fpill.f-habitat.active{{background:rgba(102,187,106,0.15);border-color:rgba(102,187,106,0.5);color:#a5d6a7}}
.combo-toggle{{
  display:flex;align-items:center;gap:8px;margin-top:4px;
  cursor:pointer;font-size:0.78rem;color:var(--muted);
  user-select:none;padding:4px 2px;
}}
.combo-toggle input{{accent-color:var(--accent);cursor:pointer}}
.combo-toggle:hover{{color:var(--text-soft)}}

/* ── MAIN CONTENT ── */
.main-content{{
  flex:1;overflow-y:auto;overflow-x:hidden;
  padding:20px;
  scrollbar-width:thin;scrollbar-color:var(--card-hi) transparent;
}}
.main-content::-webkit-scrollbar{{width:6px}}
.main-content::-webkit-scrollbar-thumb{{background:var(--card-hi);border-radius:3px}}

/* ── POKEMON GRID ── */
.poke-grid{{
  display:grid;
  grid-template-columns:repeat(auto-fill,minmax(260px,1fr));
  gap:14px;
  animation:fadeUp 0.3s ease;
}}
@keyframes fadeUp{{from{{opacity:0;transform:translateY(10px)}}to{{opacity:1;transform:translateY(0)}}}}

/* ── POKEMON CARD ── */
.poke-card{{
  background:var(--card);
  border:1px solid var(--border);
  border-radius:var(--radius-lg);
  overflow:hidden;
  transition:transform 0.22s,box-shadow 0.22s,border-color 0.22s;
}}
.poke-card:hover{{transform:translateY(-3px);box-shadow:var(--shadow-lg);}}
.card-accent-bar{{height:3px;width:100%;}}
.card-top{{
  display:flex;justify-content:space-between;align-items:center;
  padding:12px 14px 0;
}}
.dex-num{{font-family:'Fredoka One',cursive;font-size:0.78rem;color:var(--muted);letter-spacing:1px;}}
.rarity-badge{{
  font-size:0.65rem;font-weight:700;
  padding:2px 9px;border-radius:20px;
  text-transform:uppercase;letter-spacing:0.5px;
}}
.rb-legendary{{background:rgba(240,128,48,0.12);color:#ffcc80;border:1px solid rgba(240,128,48,0.3)}}
.rb-event{{background:rgba(171,71,188,0.12);color:#ce93d8;border:1px solid rgba(171,71,188,0.3)}}
.rb-common{{display:none}}
.rb-dex-only{{background:rgba(96,125,139,0.15);color:#b0bec5;border:1px solid rgba(96,125,139,0.4)}}
.rb-npc{{background:rgba(255,167,38,0.12);color:#ffcc02;border:1px solid rgba(255,167,38,0.3)}}
.hab-badge{{display:inline-block;padding:1px 7px;border-radius:4px;font-size:0.7rem;font-weight:600;margin-bottom:4px}}
.hab-event{{background:rgba(171,71,188,0.12);color:#ce93d8;border:1px solid rgba(171,71,188,0.3)}}
.hab-prefab{{color:var(--muted);font-size:0.8rem;font-style:italic;margin:6px 0 4px}}
.card-body{{padding:10px 14px 0;}}
.poke-name{{
  font-family:'Fredoka One',cursive;
  font-size:1.3rem;line-height:1;
  margin-bottom:10px;
}}
.divider{{height:1px;background:var(--border);margin:10px 14px}}
.section-lbl{{
  font-size:0.6rem;font-weight:700;
  text-transform:uppercase;letter-spacing:1.8px;
  color:var(--muted);padding:0 14px;margin-bottom:6px;
}}
.spec-row{{display:flex;gap:5px;padding:0 14px;flex-wrap:wrap;margin-bottom:12px;}}
.spec-badge{{
  display:flex;align-items:center;gap:4px;
  font-size:0.72rem;font-weight:600;
  padding:4px 10px;border-radius:8px;border:1px solid;
  cursor:pointer;transition:all 0.15s;
}}
.spec-badge:hover{{transform:translateY(-1px);filter:brightness(1.15)}}
.spec-dot{{width:6px;height:6px;border-radius:50%;flex-shrink:0}}

/* ── CARD INFO ROWS (zones/time/weather) ── */
.info-row{{
  display:flex;flex-wrap:wrap;gap:4px;
  padding:0 14px;margin-bottom:10px;
  align-items:center;
}}
.info-chip{{
  font-size:0.68rem;font-weight:600;
  padding:3px 8px;border-radius:6px;
  background:rgba(255,255,255,0.05);
  border:1px solid rgba(255,255,255,0.09);
  color:var(--text-soft);white-space:nowrap;
}}
.ic-zone{{background:rgba(41,182,246,0.1);border-color:rgba(41,182,246,0.25);color:#81d4fa}}
.ic-time{{background:rgba(255,183,77,0.1);border-color:rgba(255,183,77,0.25);color:#ffe082}}
.ic-weather{{background:rgba(100,181,246,0.1);border-color:rgba(100,181,246,0.25);color:#bbdefb}}
.ic-habitat{{background:rgba(102,187,106,0.1);border-color:rgba(102,187,106,0.25);color:#a5d6a7}}
.ic-clickable{{cursor:pointer;transition:filter 0.15s,transform 0.15s}}
.ic-clickable:hover{{filter:brightness(1.3);transform:translateY(-1px)}}

/* ── HABITAT GRID ── */
.hab-grid{{
  display:grid;
  grid-template-columns:repeat(auto-fill,minmax(300px,1fr));
  gap:14px;
  animation:fadeUp 0.3s ease;
}}
.hab-card{{
  background:var(--card);
  border:1px solid var(--border);
  border-radius:var(--radius-lg);
  overflow:hidden;
  transition:transform 0.22s,box-shadow 0.22s;
}}
.hab-card:hover{{transform:translateY(-3px);box-shadow:var(--shadow-md)}}
.hab-card-inner{{padding:16px;}}
.hab-num{{font-family:'Fredoka One',cursive;font-size:0.75rem;color:var(--muted);margin-bottom:3px;}}
.hab-name{{font-family:'Fredoka One',cursive;font-size:1.05rem;line-height:1.25;color:var(--accent);margin-bottom:8px;}}
.hab-desc{{font-size:0.82rem;color:var(--text-soft);line-height:1.55;margin-bottom:10px;}}
.hab-reqs{{margin-top:8px;}}
.hab-reqs-title{{font-size:0.6rem;font-weight:700;text-transform:uppercase;letter-spacing:1.5px;color:var(--muted);margin-bottom:5px;}}
.hab-req-list{{display:flex;flex-wrap:wrap;gap:4px;}}
.hab-req-chip{{
  font-size:0.7rem;font-weight:600;
  padding:3px 9px;border-radius:6px;
  background:rgba(110,200,74,0.08);
  border:1px solid rgba(110,200,74,0.2);
  color:var(--accent);white-space:nowrap;
}}
.hab-poke-section{{margin-top:10px;}}
.hab-poke-title{{font-size:0.6rem;font-weight:700;text-transform:uppercase;letter-spacing:1.5px;color:var(--muted);margin-bottom:5px;}}
.hab-poke-list{{font-size:0.75rem;color:var(--text-soft);line-height:1.7;}}
.hab-poke-link{{cursor:pointer;color:var(--text-soft);transition:color 0.15s}}
.hab-poke-link:hover{{color:var(--accent)}}
.hab-poke-more{{font-size:0.72rem;color:var(--muted);font-style:italic;cursor:pointer;}}
.hab-poke-more:hover{{color:var(--accent)}}
.hab-poke-extra{{display:none}}
.hab-poke-extra.open{{display:inline}}

/* ── PAGINATION ── */
.pagination{{display:flex;align-items:center;justify-content:center;gap:6px;margin-top:24px;padding-bottom:8px;}}
.pg-btn{{
  font-family:'Fredoka One',cursive;font-size:0.82rem;
  width:34px;height:34px;border-radius:8px;
  border:1px solid var(--border);background:var(--card);
  color:var(--muted);cursor:pointer;transition:all 0.18s;
  display:flex;align-items:center;justify-content:center;
}}
.pg-btn:hover{{border-color:rgba(110,200,74,0.4);color:var(--accent)}}
.pg-btn.active{{background:rgba(110,200,74,0.15);border-color:rgba(110,200,74,0.5);color:var(--accent)}}
.pg-btn:disabled{{opacity:0.3;cursor:not-allowed}}
.pg-info{{font-size:0.78rem;color:var(--muted);font-weight:600;padding:0 8px;}}

/* ── EMPTY STATE ── */
.empty-state{{grid-column:1/-1;text-align:center;padding:60px 20px;color:var(--muted);}}
.empty-state .empty-icon{{font-size:3rem;margin-bottom:12px;opacity:0.5}}
.empty-state p{{font-size:0.9rem;line-height:1.6}}
.empty-clear{{
  margin-top:14px;display:inline-block;
  font-size:0.82rem;font-weight:600;color:var(--accent);cursor:pointer;
  padding:6px 14px;border-radius:20px;
  border:1px solid rgba(110,200,74,0.35);background:rgba(110,200,74,0.08);
  transition:all 0.18s;
}}
.empty-clear:hover{{background:rgba(110,200,74,0.15)}}

/* ── TOAST ── */
.toast{{
  position:fixed;bottom:20px;left:50%;
  transform:translateX(-50%) translateY(80px);
  background:var(--card-hi);border:1px solid rgba(110,200,74,0.4);
  border-radius:40px;padding:8px 18px;
  font-size:0.8rem;font-weight:600;color:var(--accent);
  z-index:1000;transition:transform 0.3s ease,opacity 0.3s ease;
  opacity:0;pointer-events:none;white-space:nowrap;
}}
.toast.show{{transform:translateX(-50%) translateY(0);opacity:1}}

/* ── UTILITY ── */
.hidden{{display:none!important}}
.tab-content{{display:none}}
.tab-content.active{{display:block}}
</style>
</head>
<body>

<header class="app-header">
  <div class="app-logo">🌿 Pokopia Dex<span>v2.1</span></div>
  <nav class="header-tabs">
    <button class="htab active" onclick="switchTab('pokedex',this)">Pokédex</button>
    <button class="htab" onclick="switchTab('habitatdex',this)">Habitat Dex</button>
  </nav>
  <div class="header-search">
    <span class="search-icon">🔍</span>
    <input type="text" id="searchInput" placeholder="Search Pokémon or habitats…" oninput="onSearch()"/>
  </div>
  <span class="results-count" id="resultsCount"></span>
</header>

<div class="app-body">
  <aside class="sidebar" id="sidebar">

    <div id="pokedexFilters">
      <div class="filter-group">
        <div class="filter-group-title">
          Specialty
          <button class="clear-btn" id="clearSpec" onclick="clearFilter('spec')">Clear</button>
        </div>
        <div class="combo-toggle">
          <input type="checkbox" id="comboAnd" onchange="applyFilters()"/>
          <label for="comboAnd">Match ALL selected (AND)</label>
        </div>
        <div class="filter-pills" id="specFilters" style="margin-top:8px"></div>
      </div>

      <div class="filter-group">
        <div class="filter-group-title">
          Rarity
          <button class="clear-btn" id="clearRarity" onclick="clearFilter('rarity')">Clear</button>
        </div>
        <div class="filter-pills" id="rarityFilters">
          <button class="fpill r-legendary" data-rarity="Legendary" onclick="toggleFilter('rarity',this)">Legendary</button>
          <button class="fpill r-event"     data-rarity="Event"     onclick="toggleFilter('rarity',this)">Event</button>
        </div>
      </div>

      <div class="filter-group" id="zoneFilterGroup">
        <div class="filter-group-title">
          Zone
          <button class="clear-btn" id="clearZone" onclick="clearFilter('zone')">Clear</button>
        </div>
        <div class="combo-toggle">
          <input type="checkbox" id="zoneStrict" onchange="applyFilters()"/>
          <label for="zoneStrict">Exclusive (selected zones only)</label>
        </div>
        <div class="filter-pills" id="zoneFilters"></div>
      </div>

      <div class="filter-group" id="timeFilterGroup">
        <div class="filter-group-title">
          Time of Day
          <button class="clear-btn" id="clearTime" onclick="clearFilter('time')">Clear</button>
        </div>
        <div class="filter-pills" id="timeFilters">
          <button class="fpill f-time" data-time="Morning" onclick="toggleFilter('time',this)">🌅 Morning</button>
          <button class="fpill f-time" data-time="Day"     onclick="toggleFilter('time',this)">☀️ Day</button>
          <button class="fpill f-time" data-time="Evening" onclick="toggleFilter('time',this)">🌇 Evening</button>
          <button class="fpill f-time" data-time="Night"   onclick="toggleFilter('time',this)">🌙 Night</button>
        </div>
      </div>

      <div class="filter-group" id="weatherFilterGroup">
        <div class="filter-group-title">
          Weather
          <button class="clear-btn" id="clearWeather" onclick="clearFilter('weather')">Clear</button>
        </div>
        <div class="filter-pills" id="weatherFilters">
          <button class="fpill f-weather" data-weather="Sun"   onclick="toggleFilter('weather',this)">☀️ Sun</button>
          <button class="fpill f-weather" data-weather="Cloud" onclick="toggleFilter('weather',this)">☁️ Cloud</button>
          <button class="fpill f-weather" data-weather="Rain"  onclick="toggleFilter('weather',this)">🌧️ Rain</button>
          <button class="fpill f-weather" data-weather="Snow"  onclick="toggleFilter('weather',this)">❄️ Snow</button>
          <button class="fpill f-weather" data-weather="Fog"   onclick="toggleFilter('weather',this)">🌫️ Fog</button>
        </div>
      </div>
      <div class="filter-group" id="habitatTypeFilterGroup">
        <div class="filter-group-title">
          Habitat Type
          <button class="clear-btn" id="clearHabitatType" onclick="clearFilter('habitat_type')">Clear</button>
        </div>
        <div class="filter-pills" id="habitatTypeFilters"></div>
      </div>
    </div>

    <div id="habitatFilters" class="hidden">
      <div id="habitatNavBanner" class="filter-group" style="display:none">
        <div class="filter-group-title">Viewing habitats for</div>
        <div id="habitatNavInfo" style="font-size:0.82rem;line-height:1.6;padding:0 2px"></div>
        <button class="clear-btn visible" style="margin-top:8px" onclick="clearHabitatNav()">Clear &amp; show all</button>
      </div>
      <div class="filter-group">
        <div class="filter-group-title">Search habitats</div>
        <div style="font-size:0.78rem;color:var(--muted);padding:0 2px;line-height:1.5">
          Use the search bar above to find habitats by name or Pokémon.
        </div>
      </div>
    </div>

  </aside>

  <main class="main-content" id="mainContent">
    <div class="tab-content active" id="tab-pokedex">
      <div class="poke-grid" id="pokeGrid"></div>
      <div class="pagination" id="pokePagination"></div>
    </div>
    <div class="tab-content" id="tab-habitatdex">
      <div class="hab-grid" id="habGrid"></div>
      <div class="pagination" id="habPagination"></div>
    </div>
  </main>
</div>

<div class="toast" id="toast"></div>

<script>
// ── DATA ──────────────────────────────────────────────────────────────────────
const POKEMON    = {pokemon_js};
const HABITATS   = {habitats_js};
const SPECIALTIES = {specialties_js};

const SPEC_MAP = Object.fromEntries(SPECIALTIES.map(s => [s.label, s]));

// Collect all unique zones from pokemon data
const ALL_ZONES = (() => {{
  const s = new Set();
  POKEMON.forEach(p => (p.zones || []).forEach(z => s.add(z)));
  return [...s].sort();
}})();

// ── STATE ─────────────────────────────────────────────────────────────────────
const state = {{
  tab: 'pokedex',
  search: '',
  filters: {{ spec: [], rarity: [], zone: [], time: [], weather: [], habitat_type: [] }},
  pokePage: 1,
  habPage:  1,
  PAGE_SIZE: 24,
  habitatNav: null,   // {{pokemonName, habitatType}} when navigating from a card chip
}};

// ── INIT ──────────────────────────────────────────────────────────────────────
function init() {{
  buildSpecFilters();
  buildZoneFilters();
  buildHabitatTypeFilters();
  renderPokedex();
  renderHabitatDex();
  updateResultsCount();
}}

function buildSpecFilters() {{
  const container = document.getElementById('specFilters');
  container.innerHTML = '';
  const usedLabels = new Set(POKEMON.flatMap(p => p.specialties || []));
  SPECIALTIES.filter(s => usedLabels.has(s.label)).forEach(s => {{
    const btn = document.createElement('button');
    btn.className = 'fpill spec';
    btn.dataset.spec = s.label;
    btn.title = s.description || s.label;
    btn.innerHTML = `<span style="width:7px;height:7px;border-radius:50%;background:${{s.color}};flex-shrink:0;display:inline-block"></span> ${{s.label}}`;
    btn.onclick = function() {{ toggleFilter('spec', this); }};
    container.appendChild(btn);
  }});
}}

function buildZoneFilters() {{
  const container = document.getElementById('zoneFilters');
  container.innerHTML = '';
  if (ALL_ZONES.length === 0) {{
    document.getElementById('zoneFilterGroup').style.display = 'none';
    return;
  }}
  ALL_ZONES.forEach(zone => {{
    const btn = document.createElement('button');
    btn.className = 'fpill f-zone';
    btn.dataset.zone = zone;
    btn.textContent = zone;
    btn.onclick = function() {{ toggleFilter('zone', this); }};
    container.appendChild(btn);
  }});
  // Hide time/weather filter groups if no data
  const hasTime = POKEMON.some(p => (p.time || []).length > 0);
  const hasWeather = POKEMON.some(p => (p.weather || []).length > 0);
  if (!hasTime)    document.getElementById('timeFilterGroup').style.display = 'none';
  if (!hasWeather) document.getElementById('weatherFilterGroup').style.display = 'none';
}}

function buildHabitatTypeFilters() {{
  const container = document.getElementById('habitatTypeFilters');
  container.innerHTML = '';
  const allTypes = [...new Set(POKEMON.flatMap(p => p.habitat_type || []))].sort();
  if (allTypes.length === 0) {{
    document.getElementById('habitatTypeFilterGroup').style.display = 'none';
    return;
  }}
  allTypes.forEach(ht => {{
    const btn = document.createElement('button');
    btn.className = 'fpill f-habitat';
    btn.dataset.habitat_type = ht;
    btn.textContent = ht;
    btn.onclick = function() {{ toggleFilter('habitat_type', this); }};
    container.appendChild(btn);
  }});
}}

// ── TAB SWITCHING ─────────────────────────────────────────────────────────────
function switchTab(tab, btn) {{
  state.tab = tab;
  state.search = '';
  state.habitatNav = null;   // clear card-chip navigation when user switches tabs manually
  document.getElementById('searchInput').value = '';
  document.querySelectorAll('.htab').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  document.querySelectorAll('.tab-content').forEach(t => t.classList.remove('active'));
  document.getElementById(`tab-${{tab}}`).classList.add('active');
  document.getElementById('pokedexFilters').classList.toggle('hidden', tab !== 'pokedex');
  document.getElementById('habitatFilters').classList.toggle('hidden', tab !== 'habitatdex');
  if (tab === 'pokedex') renderPokedex();
  else renderHabitatDex();
  updateResultsCount();
}}

// ── FILTERS ───────────────────────────────────────────────────────────────────
function toggleFilter(group, btn) {{
  const val = btn.dataset[group] || btn.dataset.spec || btn.dataset.rarity ||
              btn.dataset.zone  || btn.dataset.time  || btn.dataset.weather ||
              btn.dataset.habitat_type;
  const arr = state.filters[group];
  const idx = arr.indexOf(val);
  if (idx === -1) arr.push(val); else arr.splice(idx, 1);
  btn.classList.toggle('active');

  if (group === 'spec') {{
    const s = SPEC_MAP[val];
    if (s) {{
      if (btn.classList.contains('active')) {{
        btn.style.background   = s.color + '28';
        btn.style.borderColor  = s.color + '88';
        btn.style.color        = s.color;
      }} else {{
        btn.style.background = btn.style.borderColor = btn.style.color = '';
      }}
    }}
  }}
  updateClearButtons();
  state.pokePage = 1; state.habPage = 1;
  if (state.tab === 'pokedex') renderPokedex();
  else renderHabitatDex();
  updateResultsCount();
}}

function clearFilter(group) {{
  state.filters[group] = [];
  const idMap = {{
    spec: 'specFilters', rarity: 'rarityFilters',
    zone: 'zoneFilters', time: 'timeFilters', weather: 'weatherFilters',
    habitat_type: 'habitatTypeFilters'
  }};
  const container = document.getElementById(idMap[group]);
  if (container) {{
    container.querySelectorAll('.fpill.active').forEach(b => {{
      b.classList.remove('active');
      b.style.background = b.style.borderColor = b.style.color = '';
    }});
  }}
  updateClearButtons();
  state.pokePage = 1;
  if (state.tab === 'pokedex') renderPokedex();
  updateResultsCount();
}}

function applyFilters() {{
  state.pokePage = 1;
  if (state.tab === 'pokedex') renderPokedex();
  updateResultsCount();
}}

function updateClearButtons() {{
  [['clearSpec','spec'],['clearRarity','rarity'],
   ['clearZone','zone'],['clearTime','time'],['clearWeather','weather'],
   ['clearHabitatType','habitat_type']].forEach(([btnId, key]) => {{
    const el = document.getElementById(btnId);
    if (el) el.classList.toggle('visible', (state.filters[key]||[]).length > 0);
  }});
}}

function onSearch() {{
  state.search = document.getElementById('searchInput').value.toLowerCase().trim();
  state.pokePage = 1; state.habPage = 1;
  if (state.tab === 'pokedex') renderPokedex();
  else renderHabitatDex();
  updateResultsCount();
}}

function clearAllFilters() {{
  state.habitatNav = null;
  ['spec','rarity','zone','time','weather','habitat_type'].forEach(g => state.filters[g] = []);
  document.querySelectorAll('.fpill.active').forEach(b => {{
    b.classList.remove('active');
    b.style.background = b.style.borderColor = b.style.color = '';
  }});
  state.search = '';
  document.getElementById('searchInput').value = '';
  updateClearButtons();
  state.pokePage = 1; state.habPage = 1;
  if (state.tab === 'pokedex') renderPokedex();
  else renderHabitatDex();
  updateResultsCount();
}}

// ── FILTERING ─────────────────────────────────────────────────────────────────
function filterPokemon() {{
  const {{ spec, rarity, zone, time, weather, habitat_type }} = state.filters;
  const and = document.getElementById('comboAnd')?.checked;
  const q   = state.search;
  return POKEMON.filter(p => {{
    if (q && !p.name.toLowerCase().includes(q)) return false;
    if (rarity.length && !rarity.includes(p.rarity)) return false;
    if (zone.length) {{
      const pZones = p.zones || [];
      const strict = document.getElementById('zoneStrict')?.checked;
      if (strict) {{
        // Pokémon must spawn in exactly the selected zones — no more, no fewer
        if (!zone.every(z => pZones.includes(z))) return false;
        if (pZones.some(z => !zone.includes(z)))  return false;
      }} else {{
        if (!zone.some(z => pZones.includes(z))) return false;
      }}
    }}
    if (time.length         && !time.some(t  => (p.time         ||[]).includes(t)))  return false;
    if (weather.length      && !weather.some(w => (p.weather    ||[]).includes(w)))  return false;
    if (habitat_type.length && !habitat_type.some(h => (p.habitat_type||[]).includes(h))) return false;
    if (spec.length) {{
      if (and) return spec.every(s => (p.specialties || []).includes(s));
      else     return spec.some(s  => (p.specialties || []).includes(s));
    }}
    return true;
  }});
}}

function filterHabitats() {{
  // Pokémon card chip navigation takes priority over text search
  if (state.habitatNav) {{
    const {{ pokemonName, habitatType }} = state.habitatNav;
    return HABITATS.filter(h =>
      // Terrain habitats: match via h.types (e.g. "Tall Grass")
      // Decoration habitats: match via h.name directly (e.g. "Campsite")
      ((h.types || []).includes(habitatType) || h.name === habitatType) &&
      (h.pokemon || []).includes(pokemonName)
    );
  }}
  const q = state.search;
  if (!q) return HABITATS;
  return HABITATS.filter(h =>
    h.name.toLowerCase().includes(q) ||
    (h.pokemon || []).some(n => n.toLowerCase().includes(q))
  );
}}

// ── POKÉDEX RENDER ────────────────────────────────────────────────────────────
function renderPokedex() {{
  const filtered   = filterPokemon();
  const totalPages = Math.max(1, Math.ceil(filtered.length / state.PAGE_SIZE));
  state.pokePage   = Math.min(state.pokePage, totalPages);
  const page = filtered.slice((state.pokePage-1)*state.PAGE_SIZE, state.pokePage*state.PAGE_SIZE);

  const grid = document.getElementById('pokeGrid');
  grid.innerHTML = '';

  if (page.length === 0) {{
    grid.innerHTML = `<div class="empty-state"><div class="empty-icon">🔍</div><p>No Pokémon match your filters.</p><span class="empty-clear" onclick="clearAllFilters()">Clear all filters</span></div>`;
    document.getElementById('pokePagination').innerHTML = '';
    return;
  }}

  page.forEach(p => grid.appendChild(buildPokeCard(p)));
  renderPagination('pokePagination', state.pokePage, totalPages, pg => {{
    state.pokePage = pg;
    renderPokedex();
    document.getElementById('mainContent').scrollTop = 0;
  }});
}}

function buildPokeCard(p) {{
  const specs = p.specialties || [];
  const firstSpec = SPEC_MAP[specs[0]];
  const accentColor = firstSpec ? firstSpec.color : '#6ec84a';

  const card = document.createElement('div');
  card.className = 'poke-card';
  card.id = `pcard-${{p.id}}`;

  const bar = document.createElement('div');
  bar.className = 'card-accent-bar';
  bar.style.background = `linear-gradient(90deg,${{accentColor}},${{accentColor}}44)`;
  card.appendChild(bar);

  const top = document.createElement('div');
  top.className = 'card-top';
  const rarityHtml = p.rarity
    ? `<span class="rarity-badge rb-${{p.rarity.toLowerCase()}}">${{p.rarity}}</span>`
    : '';
  const dexOnlyHtml = p.dex_only ? `<span class="rarity-badge rb-dex-only">Dex Only</span>` : '';
  const npcHtml     = p.npc     ? `<span class="rarity-badge rb-npc">NPC</span>` : '';
  top.innerHTML = `<span class="dex-num">#${{String(p.id).padStart(3,'0')}}</span>${{rarityHtml}}${{dexOnlyHtml}}${{npcHtml}}`;
  card.appendChild(top);

  const body = document.createElement('div');
  body.className = 'card-body';
  body.innerHTML = `<div class="poke-name" style="color:${{accentColor}}">${{p.name}}</div>`;
  card.appendChild(body);

  // Specialties
  if (specs.length > 0) {{
    card.appendChild(makeDivider());
    const lbl = document.createElement('div');
    lbl.className = 'section-lbl';
    lbl.textContent = specs.length > 1 ? 'Specialties' : 'Specialty';
    card.appendChild(lbl);

    const specRow = document.createElement('div');
    specRow.className = 'spec-row';
    specs.forEach(label => {{
      const s = SPEC_MAP[label];
      if (!s) return;
      const badge = document.createElement('div');
      badge.className = 'spec-badge';
      badge.title = s.description || label;
      badge.style.background  = s.color + '22';
      badge.style.borderColor = s.color + '66';
      badge.style.color       = s.color;
      badge.innerHTML = `<span class="spec-dot" style="background:${{s.color}}"></span>${{label}}`;
      badge.onclick = () => applySpecFilter(label);
      specRow.appendChild(badge);
    }});
    card.appendChild(specRow);
  }}

  // Zones
  const zones = p.zones || [];
  if (zones.length > 0) {{
    card.appendChild(makeDivider());
    const lbl = document.createElement('div');
    lbl.className = 'section-lbl';
    lbl.textContent = 'Zones';
    card.appendChild(lbl);
    const row = document.createElement('div');
    row.className = 'info-row';
    zones.forEach(z => {{
      const chip = document.createElement('span');
      chip.className = 'info-chip ic-zone ic-clickable';
      chip.textContent = z;
      chip.title = 'Filter by zone';
      chip.onclick = () => applyChipFilter('zone', z);
      row.appendChild(chip);
    }});
    card.appendChild(row);
  }}

  // Time + Weather (combined row)
  const timeVals    = p.time    || [];
  const weatherVals = p.weather || [];
  const allTimes    = ['Morning','Day','Evening','Night'];
  const allWeathers = ['Sun','Cloud','Rain'];
  const showTime    = timeVals.length > 0 && timeVals.length < allTimes.length;
  const showWeather = weatherVals.length > 0 && weatherVals.length < allWeathers.length;

  if (showTime || showWeather) {{
    if (zones.length === 0) card.appendChild(makeDivider());
    if (showTime) {{
      const lbl = document.createElement('div');
      lbl.className = 'section-lbl';
      lbl.textContent = 'Active Time';
      card.appendChild(lbl);
      const row = document.createElement('div');
      row.className = 'info-row';
      const TICONS = {{Morning:'🌅',Day:'☀️',Evening:'🌇',Night:'🌙'}};
      timeVals.forEach(t => {{
        const chip = document.createElement('span');
        chip.className = 'info-chip ic-time ic-clickable';
        chip.textContent = (TICONS[t]||'') + ' ' + t;
        chip.title = 'Filter by time';
        chip.onclick = () => applyChipFilter('time', t);
        row.appendChild(chip);
      }});
      card.appendChild(row);
    }}
    if (showWeather) {{
      const lbl = document.createElement('div');
      lbl.className = 'section-lbl';
      lbl.textContent = 'Weather';
      card.appendChild(lbl);
      const row = document.createElement('div');
      row.className = 'info-row';
      const WICONS = {{Sun:'☀️',Cloud:'☁️',Rain:'🌧️',Snow:'❄️',Fog:'🌫️'}};
      weatherVals.forEach(w => {{
        const chip = document.createElement('span');
        chip.className = 'info-chip ic-weather ic-clickable';
        chip.textContent = (WICONS[w]||'') + ' ' + w;
        chip.title = 'Filter by weather';
        chip.onclick = () => applyChipFilter('weather', w);
        row.appendChild(chip);
      }});
      card.appendChild(row);
    }}
  }}

  // Habitat Type (suppressed for NPCs and dex-only entries)
  const habitatTypes = p.habitat_type || [];
  if (!p.npc && !p.dex_only && habitatTypes.length > 0) {{
    card.appendChild(makeDivider());
    const lbl = document.createElement('div');
    lbl.className = 'section-lbl';
    lbl.textContent = 'Habitat';
    card.appendChild(lbl);
    const row = document.createElement('div');
    row.className = 'info-row';
    habitatTypes.forEach(ht => {{
      const chip = document.createElement('span');
      chip.className = 'info-chip ic-habitat ic-clickable';
      chip.textContent = ht;
      chip.title = 'View habitats for this Pokémon';
      chip.onclick = () => goToHabitatsByType(p.name, ht);
      row.appendChild(chip);
    }});
    card.appendChild(row);
  }}

  // bottom padding
  const pad = document.createElement('div');
  pad.style.height = '12px';
  card.appendChild(pad);

  return card;
}}

// ── HABITAT DEX RENDER ────────────────────────────────────────────────────────
function clearHabitatNav() {{
  state.habitatNav = null;
  state.habPage = 1;
  renderHabitatDex();
  updateResultsCount();
}}

function renderHabitatDex() {{
  // Show/hide the nav context banner in the sidebar
  const banner = document.getElementById('habitatNavBanner');
  const info   = document.getElementById('habitatNavInfo');
  if (state.habitatNav && banner && info) {{
    const {{ pokemonName, habitatType }} = state.habitatNav;
    info.innerHTML = `<strong>${{pokemonName}}</strong><br><span style="color:var(--muted)">${{habitatType}}</span>`;
    banner.style.display = '';
  }} else if (banner) {{
    banner.style.display = 'none';
  }}

  const filtered   = filterHabitats();
  const totalPages = Math.max(1, Math.ceil(filtered.length / state.PAGE_SIZE));
  state.habPage    = Math.min(state.habPage, totalPages);
  const page = filtered.slice((state.habPage-1)*state.PAGE_SIZE, state.habPage*state.PAGE_SIZE);

  const grid = document.getElementById('habGrid');
  grid.innerHTML = '';

  if (page.length === 0) {{
    grid.innerHTML = `<div class="empty-state"><div class="empty-icon">🏡</div><p>No habitats match your search.</p><span class="empty-clear" onclick="clearAllFilters()">Clear search</span></div>`;
    document.getElementById('habPagination').innerHTML = '';
    return;
  }}

  page.forEach(h => grid.appendChild(buildHabCard(h)));
  renderPagination('habPagination', state.habPage, totalPages, pg => {{
    state.habPage = pg;
    renderHabitatDex();
    document.getElementById('mainContent').scrollTop = 0;
  }});
}}

function buildHabCard(h) {{
  const card = document.createElement('div');
  card.className = 'hab-card';
  card.id = `hcard-${{h.id}}`;

  const bar = document.createElement('div');
  bar.className = 'card-accent-bar';
  bar.style.background = 'linear-gradient(90deg,#6ec84a,#6ec84a44)';
  card.appendChild(bar);

  const inner = document.createElement('div');
  inner.className = 'hab-card-inner';

  const eventBadge = h.event ? ` <span class="hab-badge hab-event">★ Event</span>` : '';
  let html = `
    <div class="hab-num">Habitat #${{String(h.id).padStart(3,'0')}}</div>
    <div class="hab-name">${{h.name}}${{eventBadge}}</div>
    <div class="hab-desc">${{h.description || ''}}</div>`;

  // Build requirements (pre-fab habitats have none and show a note instead)
  const reqs = h.requirements || [];
  if (h.prefab) {{
    html += `<div class="hab-prefab">Pre-fabricated habitat — no build items required</div>`;
  }} else if (reqs.length > 0) {{
    html += `<div class="hab-reqs">
      <div class="hab-reqs-title">Build Requirements</div>
      <div class="hab-req-list">`;
    reqs.forEach(r => {{
      html += `<span class="hab-req-chip">${{r.qty}}× ${{r.item}}</span>`;
    }});
    html += `</div></div>`;
  }}

  // Pokémon list
  const pokes = h.pokemon || [];
  if (pokes.length > 0) {{
    const preview = pokes.slice(0, 6);
    const extra   = pokes.slice(6);
    const uid = `hpx-${{h.id}}`;
    const pokeLink = name => `<span class="hab-poke-link" onclick="goToPokemon(this)" data-name="${{name}}">${{name}}</span>`;
    html += `<div class="hab-poke-section">
      <div class="hab-poke-title">Pokémon (${{pokes.length}})</div>
      <div class="hab-poke-list">
        ${{preview.map(pokeLink).join(', ')}}`;
    if (extra.length > 0) {{
      html += `<span class="hab-poke-more" onclick="toggleExtra('${{uid}}')"> +${{extra.length}} more</span>
               <span class="hab-poke-extra" id="${{uid}}">, ${{extra.map(pokeLink).join(', ')}}</span>`;
    }}
    html += `</div></div>`;
  }}

  inner.innerHTML = html;
  card.appendChild(inner);
  return card;
}}

function toggleExtra(uid) {{
  const el = document.getElementById(uid);
  if (!el) return;
  el.classList.toggle('open');
  const btn = el.previousElementSibling;
  if (btn) btn.style.display = el.classList.contains('open') ? 'none' : '';
}}

// ── NAVIGATION HELPERS ────────────────────────────────────────────────────────
function goToPokemon(el) {{
  const name = el.dataset.name;
  const htab = document.querySelector('.htab:nth-child(1)');
  switchTab('pokedex', htab);
  const poke = POKEMON.find(p => p.name === name);
  if (!poke) return;
  let filtered = filterPokemon();
  if (!filtered.find(p => p.name === name)) {{
    clearAllFilters();
    filtered = filterPokemon();
  }}
  const idx = filtered.findIndex(p => p.name === name);
  if (idx === -1) return;
  state.pokePage = Math.floor(idx / state.PAGE_SIZE) + 1;
  renderPokedex();
  setTimeout(() => {{
    const card = document.getElementById(`pcard-${{poke.id}}`);
    if (card) {{
      card.scrollIntoView({{ behavior: 'smooth', block: 'center' }});
      card.style.outline = '2px solid var(--accent)';
      card.style.outlineOffset = '2px';
      setTimeout(() => {{ card.style.outline = ''; card.style.outlineOffset = ''; }}, 1500);
    }}
  }}, 50);
}}

function applyChipFilter(group, value) {{
  const idMap   = {{ time: 'timeFilters', weather: 'weatherFilters', zone: 'zoneFilters', habitat_type: 'habitatTypeFilters' }};
  const container = document.getElementById(idMap[group]);
  if (!container) return;
  const btn = container.querySelector(`[data-${{group}}="${{value}}"]`);
  if (btn) toggleFilter(group, btn);
}}

// ── HABITAT NAVIGATION FROM POKÉMON CARD ──────────────────────────────────────
// Called when a user clicks a habitat chip on a Pokémon card.
// Switches to the Habitat Dex and shows only the habitats that:
//   (a) are of the clicked terrain type, AND
//   (b) this specific Pokémon actually spawns in.
function goToHabitatsByType(pokemonName, habitatType) {{
  state.habitatNav = {{ pokemonName, habitatType }};
  state.search = '';
  state.habPage = 1;
  document.getElementById('searchInput').value = '';

  // Activate the Habitat Dex tab visually (mirrors switchTab without clearing habitatNav)
  state.tab = 'habitatdex';
  document.querySelectorAll('.htab').forEach(b => b.classList.remove('active'));
  const habTab = document.querySelector('.htab:nth-child(2)');
  if (habTab) habTab.classList.add('active');
  document.querySelectorAll('.tab-content').forEach(t => t.classList.remove('active'));
  document.getElementById('tab-habitatdex').classList.add('active');
  document.getElementById('pokedexFilters').classList.add('hidden');
  document.getElementById('habitatFilters').classList.remove('hidden');

  renderHabitatDex();
  updateResultsCount();
  document.getElementById('mainContent').scrollTop = 0;
}}

// ── QUICK FILTER SHORTCUT ─────────────────────────────────────────────────────
function applySpecFilter(label) {{
  if (state.tab !== 'pokedex') {{
    switchTab('pokedex', document.querySelector('.htab:nth-child(1)'));
  }}
  const btn = document.querySelector(`#specFilters [data-spec="${{label}}"]`);
  if (btn && !btn.classList.contains('active')) {{
    toggleFilter('spec', btn);
    showToast(`Filtering: ${{label}}`);
  }}
}}

// ── PAGINATION ────────────────────────────────────────────────────────────────
function renderPagination(containerId, current, total, onClick) {{
  const container = document.getElementById(containerId);
  if (!container || total <= 1) {{ if(container) container.innerHTML=''; return; }}

  const pages = getPagesArray(current, total);
  let html = `<button class="pg-btn" ${{current===1?'disabled':''}} onclick="(${{onClick.toString()}})(${{current-1}})">‹</button>`;
  pages.forEach(p => {{
    if (p === '…') html += `<span class="pg-info">…</span>`;
    else html += `<button class="pg-btn${{p===current?' active':''}}" onclick="(${{onClick.toString()}})(${{p}})">${{p}}</button>`;
  }});
  html += `<button class="pg-btn" ${{current===total?'disabled':''}} onclick="(${{onClick.toString()}})(${{current+1}})">›</button>`;
  container.innerHTML = html;
}}

function getPagesArray(current, total) {{
  if (total <= 7) return Array.from({{length:total}},(_,i)=>i+1);
  if (current <= 4) return [1,2,3,4,5,'…',total];
  if (current >= total-3) return [1,'…',total-4,total-3,total-2,total-1,total];
  return [1,'…',current-1,current,current+1,'…',total];
}}

// ── UTILITY ───────────────────────────────────────────────────────────────────
function makeDivider() {{
  const d = document.createElement('div');
  d.className = 'divider';
  return d;
}}

function updateResultsCount() {{
  const el = document.getElementById('resultsCount');
  if (!el) return;
  el.textContent = state.tab === 'pokedex'
    ? `${{filterPokemon().length}} Pokémon`
    : `${{filterHabitats().length}} Habitats`;
}}

let toastTimer;
function showToast(msg) {{
  const t = document.getElementById('toast');
  t.textContent = msg;
  t.classList.add('show');
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => t.classList.remove('show'), 2200);
}}

document.addEventListener('DOMContentLoaded', init);
</script>
</body>
</html>"""

OUT.write_text(html, encoding="utf-8")
print(f"Built {OUT}  ({len(pokemon)} Pokémon, {len(habitats)} habitats, {len(specialties)} specialties)")

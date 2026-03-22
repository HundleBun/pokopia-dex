# Pokopia Dex

A single-page web app for browsing Pokémon and habitats in **Pokémon Pokopia**.

## Features
- Browse all available Pokémon with types, specialties, zones, and habitat info
- Browse all habitats with requirements and attracted Pokémon
- Filter by zone, specialty, environment, and rarity
- Cross-tab navigation between Pokédex and Habitat Dex

## Project Structure
```
pokopia-dex/
├── data/
│   ├── pokemon.py      # All Pokémon data as Python dicts
│   ├── habitats.py     # All habitat data as Python dicts
│   └── specialties.py  # Specialties master list
├── build.py            # Generates pokopia-dex.html from data files
├── scrape.py           # Scrapes source data from the web
└── pokopia-dex.html    # Generated output (open in browser)
```

## Usage
```bash
python build.py         # Regenerate the HTML app
python scrape.py        # Re-fetch source data (requires internet)
```

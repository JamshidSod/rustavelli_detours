# Rustavelli Detours

This repository contains tools to generate right‑turn detour routes for Shota Rustavelli Street in Tashkent with bus rapid transit (BRT) median. It downloads the road network using OSMnx, builds an edge‑based movement graph to restrict left and U‑turns on the corridor, and computes detour routes that cross the corridor at 90° angles. The scripts produce GeoJSON/GPX outputs and summary metrics comparing baseline and policy routes.

## Requirements

Install dependencies with:

```
pip install -r requirements.txt
```

## Usage

Run the main script to generate detour routes and metrics:

```
python -m src.main
```

Outputs are stored in `data/outputs/routes` (GeoJSON and GPX) and `data/outputs/summaries` (CSV).

You can customize the study area and corridor names in `src/config.py`. Optionally, provide a GeoJSON buffer for the corridor and a list of legal crossing nodes in `data/inputs/crossings.geojson`.

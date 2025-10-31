# generate_candidates.py
import csv
import json
from pathlib import Path
import osmnx as ox
import geopandas as gpd
from shapely.geometry import Point

from src.build_network import build_graph

def find_entry_exit_pairs():
    G = build_graph()
    entries = []

    for v in G.nodes():
        # Check if node touches the Rustavelli corridor
        incident = list(G.in_edges(v, keys=True, data=True)) + list(G.out_edges(v, keys=True, data=True))
        if not any(d.get("is_corridor", False) for *_, d in incident):
            continue  # skip nodes not on corridor

        # Find all incoming edges from side streets (non-corridor)
        incoming_side_edges = [
            (u, v_, k, d) for (u, v_, k, d) in G.in_edges(v, keys=True, data=True) if not d.get("is_corridor", False)
        ]
        # Find all outgoing edges to side streets (non-corridor)
        outgoing_side_edges = [
            (v_, w, k, d) for (v_, w, k, d) in G.out_edges(v, keys=True, data=True) if not d.get("is_corridor", False)
        ]

        for (u, v_, k_in, d_in) in incoming_side_edges:
            entry_name = d_in.get("name") or "unknown"
            # Choose the first outgoing side edge as the exit candidate
            if not outgoing_side_edges:
                continue
            (v__, w, k_out, d_out) = outgoing_side_edges[0]
            exit_name = d_out.get("name") or "unknown"
            entries.append({
                "node": v,
                "entry_edge": (u, v_, k_in),
                "entry_road": entry_name,
                "exit_edge": (v__, w, k_out),
                "exit_road": exit_name,
                "lat": G.nodes[v]["y"],
                "lon": G.nodes[v]["x"],
            })
    return entries

def save_as_csv_and_geojson(entries, out_dir):
    # Save CSV
    csv_path = out_dir / "candidate_movements.csv"
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["node", "entry_edge", "entry_road", "exit_edge", "exit_road"])
        writer.writeheader()
        for entry in entries:
            writer.writerow({
                "node": entry["node"],
                "entry_edge": entry["entry_edge"],
                "entry_road": entry["entry_road"],
                "exit_edge": entry["exit_edge"],
                "exit_road": entry["exit_road"],
            })
    print(f"Candidate movements saved to {csv_path}")

    # Save GeoJSON
    geoms = []
    for entry in entries:
        geoms.append(Point(entry["lon"], entry["lat"]))
    gdf = gpd.GeoDataFrame(entries, geometry=geoms, crs="EPSG:4326")
    geo_path = out_dir / "candidate_movements.geojson"
    gdf.to_file(geo_path, driver="GeoJSON")
    print(f"GeoJSON for candidates saved to {geo_path}")

def main():
    out_dir = Path("data/outputs")  # adjust to where you want to save the files
    out_dir.mkdir(parents=True, exist_ok=True)
    entries = find_entry_exit_pairs()
    save_as_csv_and_geojson(entries, out_dir)

if __name__ == "__main__":
    main()

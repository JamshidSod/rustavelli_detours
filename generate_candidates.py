# generate_candidates.py
import csv
from pathlib import Path
import osmnx as ox
import geopandas as gpd
from shapely.geometry import Point

from src.build_network import build_graph

def find_entry_exit_pairs():
    """
    Build a WGS84 graph (lat/lon) and find candidate left-turn movements
    across the Rustavelli corridor.
    """
    # Build the base graph (projected)
    G_proj = build_graph()
    # Unproject to WGS84 (EPSG:4326) so x = lon, y = lat
    G = ox.project_graph(G_proj, to_crs="EPSG:4326")

    entries = []

    for v in G.nodes():
        # Skip nodes that don't touch the corridor
        incident = list(G.in_edges(v, keys=True, data=True)) + list(G.out_edges(v, keys=True, data=True))
        if not any(d.get("is_corridor", False) for *_, d in incident):
            continue

        # All incoming edges from side streets (is_corridor=False)
        incoming_side = [
            (u, v, k, d) for (u, v, k, d) in G.in_edges(v, keys=True, data=True) if not d.get("is_corridor", False)
        ]
        # All outgoing edges to side streets (is_corridor=False)
        outgoing_side = [
            (v, w, k, d) for (v, w, k, d) in G.out_edges(v, keys=True, data=True) if not d.get("is_corridor", False)
        ]

        if not incoming_side or not outgoing_side:
            continue

        for (u_in, v_in, k_in, d_in) in incoming_side:
            entry_name = d_in.get("name") or "unknown"
            # Pick the first outgoing side edge as a tentative exit
            (v_out, w_out, k_out, d_out) = outgoing_side[0]
            exit_name = d_out.get("name") or "unknown"
            entries.append({
                "node": v,
                "entry_edge": (u_in, v_in, k_in),
                "entry_road": entry_name,
                "exit_edge": (v_out, w_out, k_out),
                "exit_road": exit_name,
                "lat": G.nodes[v]["y"],  # latitude
                "lon": G.nodes[v]["x"],  # longitude
            })
    return entries

def save_as_csv_and_geojson(entries, out_dir):
    out_dir.mkdir(parents=True, exist_ok=True)

    # Write CSV
    csv_file = out_dir / "candidate_movements.csv"
    with open(csv_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["node", "entry_edge", "entry_road", "exit_edge", "exit_road"])
        writer.writeheader()
        for e in entries:
            writer.writerow({
                "node": e["node"],
                "entry_edge": e["entry_edge"],
                "entry_road": e["entry_road"],
                "exit_edge": e["exit_edge"],
                "exit_road": e["exit_road"],
            })
    print(f"Candidate movements saved to {csv_file}")

    # Write GeoJSON
    geoms = [Point(e["lon"], e["lat"]) for e in entries]
    gdf = gpd.GeoDataFrame(entries, geometry=geoms, crs="EPSG:4326")
    geo_file = out_dir / "candidate_movements.geojson"
    gdf.to_file(geo_file, driver="GeoJSON")
    print(f"Candidate movements GeoJSON saved to {geo_file}")

def main():
    entries = find_entry_exit_pairs()
    if not entries:
        print("No candidate movements found.")
        return
    out_dir = Path("data/outputs")  # adjust as needed
    save_as_csv_and_geojson(entries, out_dir)

if __name__ == "__main__":
    main()

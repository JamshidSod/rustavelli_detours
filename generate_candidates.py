# generate_candidates.py
import csv
from pathlib import Path
import math
import osmnx as ox
import geopandas as gpd
from shapely.geometry import Point, LineString
from src.build_network import build_graph


def find_entry_exit_pairs():
    """
    Identify right-turn entry points from side streets near the Rustavelli corridor,
    and determine potential reroute crossings at perpendicular intersections.
    """

    # --- Build base graph (projected) and reproject to WGS84 ---
    G_proj = build_graph()
    G = ox.project_graph(G_proj, to_crs="EPSG:4326")

    # --- Filter out southern segments that are not part of the real BRT corridor ---
    for u, v, k in list(G.edges(keys=True)):
        y_u = G.nodes[u]["y"]
        y_v = G.nodes[v]["y"]
        if G.edges[u, v, k].get("is_corridor", False) and (y_u < 41.25 and y_v < 41.25):
            G.edges[u, v, k]["is_corridor"] = False

    # --- Identify corridor and side streets ---
    corridor_edges = {(u, v, k) for u, v, k, d in G.edges(keys=True, data=True) if d.get("is_corridor", False)}
    corridor_nodes = {u for u, v, k in corridor_edges} | {v for u, v, k in corridor_edges}

    entries = []

    # --- Helper to compute angle between vectors ---
    def bearing_diff(b1, b2):
        return (b2 - b1 + 540) % 360 - 180

    # --- Iterate over corridor intersections ---
    for v in corridor_nodes:
        # Identify side-street entries to the corridor (incoming)
        incoming_side = [
            (u, v, k, d)
            for u, v, k, d in G.in_edges(v, keys=True, data=True)
            if not d.get("is_corridor", False)
        ]
        if not incoming_side:
            continue

        # Outgoing edges along the corridor
        outgoing_corridor = [
            (v, w, k, d)
            for v, w, k, d in G.out_edges(v, keys=True, data=True)
            if d.get("is_corridor", False)
        ]

        if not outgoing_corridor:
            continue

        for (u, v, k_in, d_in) in incoming_side:
            entry_name = d_in.get("name") or "unknown"
            entry_point = Point(G.nodes[v]["x"], G.nodes[v]["y"])
            entry_bearing = d_in.get("bearing")

            # --- Find next perpendicular crossing where reroute can occur ---
            crossing_found = False
            for (v, w, k_out, d_out) in outgoing_corridor:
                b_out = d_out.get("bearing")
                if entry_bearing is None or b_out is None:
                    continue

                delta = abs(bearing_diff(entry_bearing, b_out))
                # Accept roughly right angles (70°–110°)
                if 70 <= delta <= 110:
                    cross_node = w
                    cross_point = Point(G.nodes[w]["x"], G.nodes[w]["y"])
                    exit_name = d_out.get("name") or "unknown"
                    entries.append({
                        "entry_node": v,
                        "cross_node": cross_node,
                        "entry_road": entry_name,
                        "cross_road": exit_name,
                        "lat": G.nodes[v]["y"],
                        "lon": G.nodes[v]["x"],
                        "geometry": LineString([entry_point, cross_point]),
                    })
                    crossing_found = True
                    break

            # If no perpendicular crossing found, skip
            if not crossing_found:
                continue

    return entries


def save_as_csv_and_geojson(entries, out_dir):
    """Save results to both CSV and GeoJSON for QGIS visualization."""
    out_dir.mkdir(parents=True, exist_ok=True)

    csv_file = out_dir / "candidate_movements.csv"
    with open(csv_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "entry_node",
                "cross_node",
                "entry_road",
                "cross_road",
                "lat",
                "lon",
            ],
        )
        writer.writeheader()
        for e in entries:
            writer.writerow({
                "entry_node": e["entry_node"],
                "cross_node": e["cross_node"],
                "entry_road": e["entry_road"],
                "cross_road": e["cross_road"],
                "lat": e["lat"],
                "lon": e["lon"],
            })
    print(f"Candidate movements saved to {csv_file}")

    # GeoJSON
    gdf = gpd.GeoDataFrame(entries, geometry=[e["geometry"] for e in entries], crs="EPSG:4326")
    geo_file = out_dir / "candidate_movements.geojson"
    gdf.to_file(geo_file, driver="GeoJSON")
    print(f"Candidate movements GeoJSON saved to {geo_file}")


def main():
    entries = find_entry_exit_pairs()
    if not entries:
        print("No candidate reroutes found.")
        return

    out_dir = Path("data/outputs")
    save_as_csv_and_geojson(entries, out_dir)


if __name__ == "__main__":
    main()

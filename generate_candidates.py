# generate_candidates.py
import csv
from pathlib import Path
import math
import osmnx as ox
import networkx as nx
import geopandas as gpd
from shapely.geometry import Point, LineString
from src.build_network import build_graph


def find_entry_exit_routes():
    """
    Identify right-turn entry points from side streets near the Rustavelli corridor,
    find their nearest legal crossings, and compute network-based detour routes.
    """

    print("Building base network graph...")
    G_proj = build_graph()
    G = ox.project_graph(G_proj, to_crs="EPSG:4326")

    # --- Filter out false corridor segments south of real BRT zone ---
    for u, v, k in list(G.edges(keys=True)):
        y_u = G.nodes[u]["y"]
        y_v = G.nodes[v]["y"]
        if G.edges[u, v, k].get("is_corridor", False) and (y_u < 41.25 and y_v < 41.25):
            G.edges[u, v, k]["is_corridor"] = False

    corridor_edges = {(u, v, k) for u, v, k, d in G.edges(keys=True, data=True)
                      if d.get("is_corridor", False)}
    corridor_nodes = {u for u, v, k in corridor_edges} | {v for u, v, k in corridor_edges}

    entries = []

    def bearing_diff(b1, b2):
        return (b2 - b1 + 540) % 360 - 180

    # --- Step 1: Detect entry points (side streets joining corridor) ---
    for v in corridor_nodes:
        incoming_side = [(u, v, k, d) for u, v, k, d in G.in_edges(v, keys=True, data=True)
                         if not d.get("is_corridor", False)]
        outgoing_corridor = [(v, w, k, d) for v, w, k, d in G.out_edges(v, keys=True, data=True)
                             if d.get("is_corridor", False)]
        if not incoming_side or not outgoing_corridor:
            continue

        for (u, v, k_in, d_in) in incoming_side:
            entry_bearing = d_in.get("bearing")
            if entry_bearing is None:
                continue

            for (v, w, k_out, d_out) in outgoing_corridor:
                b_out = d_out.get("bearing")
                if b_out is None:
                    continue
                delta = abs(bearing_diff(entry_bearing, b_out))
                if 70 <= delta <= 110:
                    entries.append({
                        "entry_node": v,
                        "entry_road": d_in.get("name") or "unknown",
                        "entry_bearing": entry_bearing,
                    })
                    break

    if not entries:
        print("No candidate entry points found.")
        return []

    # --- Step 2: For each entry, find nearest perpendicular crossing and route to it ---
    print(f"Found {len(entries)} entry candidates; computing routes...")
    detours = []
    for e in entries:
        v = e["entry_node"]
        x0, y0 = G.nodes[v]["x"], G.nodes[v]["y"]
        entry_point = Point(x0, y0)

        # Find the next corridor crossing node ahead
        # (approx. 300–600 m along the corridor)
        best_cross = None
        best_dist = float("inf")
        for w in corridor_nodes:
            if w == v:
                continue
            # Skip if too far lat/lon difference
            dx = G.nodes[w]["x"] - x0
            dy = G.nodes[w]["y"] - y0
            dist = math.hypot(dx, dy)
            if 0.002 < dist < 0.008:  # ~200–800 m range
                best_cross = w
                best_dist = dist
                break
        if not best_cross:
            continue

        try:
            # Compute shortest path over drivable network
            route_nodes = nx.shortest_path(G, v, best_cross, weight="length")
            route_geom = LineString([(G.nodes[n]["x"], G.nodes[n]["y"]) for n in route_nodes])
            detours.append({
                "entry_node": v,
                "cross_node": best_cross,
                "entry_road": e["entry_road"],
                "distance_m": sum(G.edges[u, w, 0].get("length", 0)
                                  for u, w in zip(route_nodes[:-1], route_nodes[1:])),
                "geometry": route_geom,
                "lat": y0,
                "lon": x0,
            })
        except nx.NetworkXNoPath:
            continue

    print(f"Generated {len(detours)} valid reroute paths.")
    return detours


def save_results(detours, out_dir):
    out_dir.mkdir(parents=True, exist_ok=True)
    csv_file = out_dir / "detour_routes.csv"
    geo_file = out_dir / "detour_routes.geojson"

    # CSV
    with open(csv_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "entry_node", "cross_node", "entry_road", "distance_m", "lat", "lon"
        ])
        writer.writeheader()
        for d in detours:
            writer.writerow({
                "entry_node": d["entry_node"],
                "cross_node": d["cross_node"],
                "entry_road": d["entry_road"],
                "distance_m": round(d["distance_m"], 1),
                "lat": d["lat"],
                "lon": d["lon"],
            })
    print(f"Saved detour summary CSV → {csv_file}")

    # GeoJSON
    gdf = gpd.GeoDataFrame(detours, geometry=[d["geometry"] for d in detours], crs="EPSG:4326")
    gdf.to_file(geo_file, driver="GeoJSON")
    print(f"Saved detour paths GeoJSON → {geo_file}")


def main():
    detours = find_entry_exit_routes()
    if detours:
        save_results(detours, Path("data/outputs"))
    else:
        print("No valid detour routes generated.")


if __name__ == "__main__":
    main()

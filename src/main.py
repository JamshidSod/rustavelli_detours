from pathlib import Path
import geopandas as gpd
from .config import ROUTES_DIR, SUMMARIES_DIR, INPUTS
from .build_network import build_graph
from .policies import build_policy_graphs
from .od_catalog import candidate_movements
from .indicators import summarize
from .export_geo import movement_path_to_linestring, write_geojson, write_gpx

def load_crossing_whitelist(G):
    """
    If a crossings.geojson exists in data/inputs, read it and return a set
    of node IDs that are legal crossing points. Otherwise, return None.
    """
    p = INPUTS / "crossings.geojson"
    if not p.exists():
        return None
    gdf = gpd.read_file(p)
    idx = []
    for pt in gdf.geometry:
        n = min(G.nodes(), key=lambda n: (G.nodes[n]["x"] - pt.x) ** 2 + (G.nodes[n]["y"] - pt.y) ** 2)
        idx.append(n)
    return set(idx)

def ensure_output_dirs():
    ROUTES_DIR.mkdir(parents=True, exist_ok=True)
    SUMMARIES_DIR.mkdir(parents=True, exist_ok=True)

def run():
    ensure_output_dirs()
    G = build_graph()
    whitelist = load_crossing_whitelist(G)

    M_base, M_policy = build_policy_graphs(G, crossings_whitelist_nodes=whitelist)

    lines_for_geo = []

    def saverow(mv, path_baseline, path_policy):
        ln = movement_path_to_linestring(G, path_policy)  # use projected G here
        props = {"name": f"{mv['type']}_node_{mv['node']}"}
        lines_for_geo.append((ln, props))

    df = summarize(G, M_base, M_policy, candidate_movements(G), saverow=saverow)

    out_csv = SUMMARIES_DIR / "rustavelli_detour_indicators.csv"
    df.to_csv(out_csv, index=False)

    out_geo = ROUTES_DIR / "rustavelli_detours.geojson"
    write_geojson(lines_for_geo, out_geo)
    out_gpx = ROUTES_DIR / "rustavelli_detours.gpx"
    write_gpx(lines_for_geo, out_gpx)

    print("Wrote outputs to:", out_csv, out_geo, out_gpx)

if __name__ == "__main__":
    run()

import osmnx as ox
import networkx as nx
from shapely.geometry import shape
import json
from .config import PLACE, CORRIDOR_NAME_ALIASES, INPUTS

def _normalize_name(n):
    return str(n or "").lower().strip()

def load_corridor_buffer():
    p = INPUTS / "rustavelli_buffer.geojson"
    if p.exists():
        gj = json.loads(p.read_text())
        geom = shape(gj["features"][0]["geometry"])
        return geom
    return None

def build_graph():
    G = ox.graph_from_place(PLACE, network_type="drive")   # keep directed
    G = ox.project_graph(G)
    G = ox.add_edge_speeds(G)
    G = ox.add_edge_travel_times(G)
    G = ox.add_edge_bearings(G)

    buffer_geom = load_corridor_buffer()

    for u, v, k, data in G.edges(keys=True, data=True):
        name = _normalize_name(data.get("name"))
        by_name = name in CORRIDOR_NAME_ALIASES
        by_geom = False
        if buffer_geom and "geometry" in data:
            by_geom = buffer_geom.buffer(5).intersects(data["geometry"])  # 5 m buffer tolerance
        data["is_corridor"] = bool(by_name or by_geom)

    return G

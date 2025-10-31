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
    # 1. Download the drivable network (unprojected, lat/lon coordinates)
    G = ox.graph_from_place(PLACE, network_type="drive")

    # 2. Add edge bearings before any projection
    G = ox.add_edge_bearings(G)

    # 3. Project the graph to UTM so distances are in meters
    G = ox.project_graph(G)

    # 4. Add speeds and travel times (requires projected graph for lengths)
    G = ox.add_edge_speeds(G)
    G = ox.add_edge_travel_times(G)

    # 5. Tag corridor edges based on name or optional buffer
    buffer_geom = load_corridor_buffer()
    for u, v, k, data in G.edges(keys=True, data=True):
        name = _normalize_name(data.get("name"))
        by_name = name in CORRIDOR_NAME_ALIASES
        by_geom = False
        if buffer_geom and "geometry" in data:
            # small tolerance in meters to capture near overlaps
            by_geom = buffer_geom.buffer(5).intersects(data["geometry"])
        data["is_corridor"] = bool(by_name or by_geom)

    return G

import os
import math
import networkx as nx
import osmnx as ox
from PIL import Image

from src.build_network import build_graph
from src.policies import build_policy_graphs
from src.od_catalog import candidate_movements
from src.routing import shortest_path_movement

def movement_to_node_path(movement_path):
    """Convert a movement-graph path (edges) into a sequence of node IDs."""
    node_ids = [movement_path[0][0]]
    for (_, v, _) in movement_path:
        node_ids.append(v)
    return node_ids

def find_corridor_signal_nodes(G):
    """
    Identify all nodes that (a) have highway=traffic_signals in OSM,
    and (b) touch at least one edge on the Rustavelli corridor.
    These will be used as the only legal cross-median locations.
    """
    whitelist = set()
    for n, data in G.nodes(data=True):
        if data.get("highway") != "traffic_signals":
            continue
        # Check if any incident edge is part of the corridor
        on_corridor = False
        for _, _, k, d in G.in_edges(n, keys=True, data=True):
            if d.get("is_corridor", False):
                on_corridor = True
                break
        if not on_corridor:
            for _, _, k, d in G.out_edges(n, keys=True, data=True):
                if d.get("is_corridor", False):
                    on_corridor = True
                    break
        if on_corridor:
            whitelist.add(n)
    return whitelist

def get_longest_detour(G, M_policy):
    """
    Evaluate all candidate movements and return the policy path
    with the largest number of nodes (i.e. the longest detour).
    """
    best_path = None
    best_len = 0
    for mv in candidate_movements(G):
        try:
            path = shortest_path_movement(M_policy, mv["entry_edge"], mv["policy_exit_edge"])
        except Exception:
            continue
        node_path = movement_to_node_path(path)
        if len(node_path) > best_len:
            best_len = len(node_path)
            best_path = path
    # Fall back if none found
    if best_path is None:
        mv = next(candidate_movements(G))
        best_path = shortest_path_movement(M_policy, mv["entry_edge"], mv["policy_exit_edge"])
    return best_path

def crop_graph_to_route(org_graph, route_nodes, buffer_m=300):
    """
    Return a subgraph of org_graph containing all nodes within buffer_m metres of the route.
    """
    lats = [org_graph.nodes[n]["y"] for n in route_nodes]
    lons = [org_graph.nodes[n]["x"] for n in route_nodes]
    north, south = max(lats), min(lats)
    east, west = max(lons), min(lons)
    avg_lat = sum(lats) / len(lats)

    pad_lat = buffer_m / 111_000
    pad_lon = buffer_m / (111_000 * abs(math.cos(math.radians(avg_lat))) or 1)

    bbox_north = north + pad_lat
    bbox_south = south - pad_lat
    bbox_east  = east  + pad_lon
    bbox_west  = west  - pad_lon

    nodes_in_bbox = [
        n for n, data in org_graph.nodes(data=True)
        if bbox_south <= data["y"] <= bbox_north and bbox_west <= data["x"] <= bbox_east
    ]
    return org_graph.subgraph(nodes_in_bbox).copy()

def main():
    # 1. Build the projected graph and unproject for plotting
    G_proj = build_graph()
    org_graph = ox.project_graph(G_proj, to_crs="EPSG:4326")

    # 2. Find corridor signal nodes and build movement graphs with crossing restrictions
    crossings_whitelist = find_corridor_signal_nodes(G_proj)
    _, M_policy = build_policy_graphs(G_proj, crossings_whitelist_nodes=crossings_whitelist)

    # 3. Select the "longest" detour movement across the corridor
    movement_path = get_longest_detour(G_proj, M_policy)
    final_path = movement_to_node_path(movement_path)

    # 4. Crop the plotting graph to the vicinity of the chosen route
    subgraph = crop_graph_to_route(org_graph, final_path, buffer_m=300)

    # 5. Create animation frames
    frames_dir = "animation_frames"
    os.makedirs(frames_dir, exist_ok=True)
    title = "Rustavelli detour example"

    for i in range(1, len(final_path) + 1):
        partial = final_path[:i]
        fig, ax = ox.plot_graph_route(
            subgraph,
            partial,
            route_linewidth=4,
            node_size=0,
            bgcolor="white",
            route_color="red",
            route_alpha=0.8,
            show=False,
            close=False,
        )
        ax.set_title(title, fontsize=16)
        fig.savefig(os.path.join(frames_dir, f"img_{i:03d}.png"), dpi=150, bbox_inches="tight")
        import matplotlib.pyplot as plt
        plt.close(fig)

    # 6. Assemble GIF
    frame_files = sorted([f for f in os.listdir(frames_dir) if f.endswith(".png")])
    images = [Image.open(os.path.join(frames_dir, f)) for f in frame_files]
    gif_path = "rustavelli_detour_animation.gif"
    images[0].save(
        gif_path,
        save_all=True,
        append_images=images[1:],
        duration=100,
        loop=0,
    )
    print(f"Saved detour animation to {gif_path}")

if __name__ == "__main__":
    main()

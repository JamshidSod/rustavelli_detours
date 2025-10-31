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
    """Convert a movement-graph path (edges) into node IDs for plotting."""
    node_ids = [movement_path[0][0]]
    for (_, v, _) in movement_path:
        node_ids.append(v)
    return node_ids

def get_corridor_movement(G, M_policy):
    """
    Examine all candidate movements and choose the one whose detour route covers
    the most nodes (i.e. the 'longest' detour). This tends to pick a side-street
    left turn across the corridor that forces a full block loop.
    """
    best_path = None
    best_len = 0
    for mv in candidate_movements(G):
        # compute the policy path for this movement
        path = shortest_path_movement(M_policy, mv["entry_edge"], mv["policy_exit_edge"])
        # convert movement edges to node IDs
        node_path = movement_to_node_path(path)
        # skip trivial detours that only change direction
        if len(node_path) > best_len:
            best_len = len(node_path)
            best_path = path
    if best_path is None:
        # fall back to the first candidate
        mv = next(candidate_movements(G))
        best_path = shortest_path_movement(M_policy, mv["entry_edge"], mv["policy_exit_edge"])
    return best_path


    # Fallback: return the first candidate if none match
    mv = next(candidate_movements(G))
    return shortest_path_movement(M_policy, mv["entry_edge"], mv["policy_exit_edge"])

def crop_graph_to_route(org_graph, route_nodes, buffer_m=300):
    """
    Build a subgraph containing all nodes within a buffer around the route.
    org_graph should be in lat/lon (EPSG:4326). buffer_m is in metres.
    """
    lats = [org_graph.nodes[n]["y"] for n in route_nodes]
    lons = [org_graph.nodes[n]["x"] for n in route_nodes]
    north, south = max(lats), min(lats)
    east, west = max(lons), min(lons)
    avg_lat = sum(lats) / len(lats)

    pad_lat = buffer_m / 111_000  # degrees per metre of latitude
    pad_lon = buffer_m / (111_000 * abs(math.cos(math.radians(avg_lat))) or 1)

    bbox_north = north + pad_lat
    bbox_south = south - pad_lat
    bbox_east  = east + pad_lon
    bbox_west  = west - pad_lon

    nodes_in_bbox = [
        n for n, data in org_graph.nodes(data=True)
        if bbox_south <= data["y"] <= bbox_north and bbox_west <= data["x"] <= bbox_east
    ]
    return org_graph.subgraph(nodes_in_bbox).copy()

def main():
    # Build projected and unprojected graphs
    G_proj = build_graph()
    org_graph = ox.project_graph(G_proj, to_crs="EPSG:4326")

    # Build movement graphs (baseline and policy)
    _, M_policy = build_policy_graphs(G_proj, crossings_whitelist_nodes=None)

    # Pick a Rustavelli detour (first left/U-turn on the corridor)
    movement_path = get_corridor_movement(G_proj, M_policy)
    final_path = movement_to_node_path(movement_path)

    # Crop the plotting graph to the route’s vicinity
    subgraph = crop_graph_to_route(org_graph, final_path, buffer_m=300)

    # Prepare output directory for frames
    frames_dir = "animation_frames"
    os.makedirs(frames_dir, exist_ok=True)

    title = "Rustavelli detour example"
    # Generate frames: progressively draw the route
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
        ax.set_title(title, fontsize=14)
        fig.savefig(
            os.path.join(frames_dir, f"img_{i:03d}.png"),
            dpi=150,
            bbox_inches="tight",
        )
        import matplotlib.pyplot as plt
        plt.close(fig)

    # Assemble GIF from frames
    frame_files = sorted([f for f in os.listdir(frames_dir) if f.endswith(".png")])
    images = [Image.open(os.path.join(frames_dir, f)) for f in frame_files]
    gif_path = "rustavelli_detour_animation.gif"
    images[0].save(
        gif_path,
        save_all=True,
        append_images=images[1:],
        duration=80,
        loop=0,
    )
    print(f"Saved detour animation to {gif_path}")

if __name__ == "__main__":
    main()

import os
import shutil
import math
import osmnx as ox
from PIL import Image
from src.build_network import build_graph
from src.policies import build_policy_graphs
from src.od_catalog import candidate_movements
from src.routing import shortest_path_movement

def movement_to_node_path(movement_path):
    node_ids = [movement_path[0][0]]
    for (_, v, _) in movement_path:
        node_ids.append(v)
    return node_ids

def find_corridor_signal_nodes(G):
    whitelist = set()
    for n, data in G.nodes(data=True):
        if data.get("highway") != "traffic_signals":
            continue
        on_corridor = any(
            d.get("is_corridor", False)
            for _, _, _, d in G.in_edges(n, keys=True, data=True)
        ) or any(
            d.get("is_corridor", False)
            for _, _, _, d in G.out_edges(n, keys=True, data=True)
        )
        if on_corridor:
            whitelist.add(n)
    return whitelist

def crop_graph_to_route(org_graph, route_nodes, buffer_m=300):
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
    # Build graphs
    G_proj = build_graph()
    org_graph = ox.project_graph(G_proj, to_crs="EPSG:4326")

    # Build policy graph with traffic-signal crossings
    whitelist = find_corridor_signal_nodes(G_proj)
    _, M_policy = build_policy_graphs(G_proj, crossings_whitelist_nodes=whitelist)

    # Clear old frames directory
    frames_root = "animation_frames"
    if os.path.exists(frames_root):
        shutil.rmtree(frames_root)
    os.makedirs(frames_root, exist_ok=True)

    # Loop over all candidate movements
    for i, mv in enumerate(candidate_movements(G_proj)):
        try:
            path = shortest_path_movement(M_policy, mv["entry_edge"], mv["policy_exit_edge"])
        except Exception:
            # Skip movements that fail to route
            continue

        node_path = movement_to_node_path(path)
        subgraph = crop_graph_to_route(org_graph, node_path, buffer_m=300)

        # Create a subfolder for this movement's frames
        movement_dir = os.path.join(frames_root, f"movement_{i}")
        os.makedirs(movement_dir, exist_ok=True)

        title = f"Rustavelli detour at node {mv['node']} ({mv['type']})"

        # Generate frames
        for j in range(1, len(node_path) + 1):
            partial = node_path[:j]
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
                os.path.join(movement_dir, f"img_{j:03d}.png"),
                dpi=150,
                bbox_inches="tight",
            )
            import matplotlib.pyplot as plt
            plt.close(fig)

        # Assemble GIF for this movement
        frame_files = sorted(
            [f for f in os.listdir(movement_dir) if f.endswith(".png")]
        )
        images = [
            Image.open(os.path.join(movement_dir, f)) for f in frame_files
        ]
        gif_name = f"rustavelli_detour_{i}.gif"
        images[0].save(
            gif_name,
            save_all=True,
            append_images=images[1:],
            duration=100,
            loop=0,
        )
        print(f"Saved animation for node {mv['node']} to {gif_name}")

if __name__ == "__main__":
    main()

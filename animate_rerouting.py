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

    # Prepare the output list of frames
    gif_frames = []

    # Generate one frame per movement
    for mv in candidate_movements(G_proj):
        try:
            path = shortest_path_movement(M_policy, mv["entry_edge"], mv["policy_exit_edge"])
        except Exception:
            continue
        node_path = movement_to_node_path(path)
        subgraph = crop_graph_to_route(org_graph, node_path, buffer_m=300)

        # Plot the entire detour in one frame
        title = f"Rustavelli detour at node {mv['node']} ({mv['type']})"
        fig, ax = ox.plot_graph_route(
            subgraph,
            node_path,
            route_linewidth=4,
            node_size=0,
            bgcolor="white",
            route_color="red",
            route_alpha=0.8,
            show=False,
            close=False,
        )
        ax.set_title(title, fontsize=14)
        frame_path = f"_frame_{mv['node']}.png"
        fig.savefig(frame_path, dpi=150, bbox_inches="tight")
        import matplotlib.pyplot as plt
        plt.close(fig)

        gif_frames.append(Image.open(frame_path))
        os.remove(frame_path)  # clean up individual frame file

    if not gif_frames:
        print("No detours generated.")
        return

    # Save all frames into a single GIF
    output_gif = "rustavelli_detours_all.gif"
    gif_frames[0].save(
        output_gif,
        save_all=True,
        append_images=gif_frames[1:],
        duration=1000,  # 1 second per intersection; adjust as needed
        loop=0,
    )
    print(f"Saved combined detour animation to {output_gif}")

if __name__ == "__main__":
    main()

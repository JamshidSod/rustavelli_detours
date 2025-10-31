import os
import networkx as nx
import osmnx as ox
from PIL import Image

from src.build_network import build_graph
from src.policies import build_policy_graphs
from src.od_catalog import candidate_movements
from src.routing import shortest_path_movement

def movement_to_node_path(movement_path):
    """Convert movement-path edges into a list of node IDs."""
    node_ids = [movement_path[0][0]]
    for (_, v, _) in movement_path:
        node_ids.append(v)
    return node_ids

def get_corridor_movement(G, M_policy):
    """
    Pick the first left/U movement on the corridor from candidate_movements.
    You can refine this or explicitly specify which movement to animate.
    """
    for mv in candidate_movements(G):
        # Here mv['type'] is 'left' or 'uturn' if coming from the side street,
        # and mv['entry_edge'] is on the corridor for U‑turns.
        if mv['type'] in {'left', 'uturn'}:
            start_edge = mv['entry_edge']
            end_edge = mv['policy_exit_edge']
            path = shortest_path_movement(M_policy, start_edge, end_edge)
            return path
    raise RuntimeError("No suitable corridor movement found; check your od_catalog.")

def crop_graph_to_route(org_graph, route_nodes, buffer_m=300):
    """
    Create a subgraph containing all nodes within `buffer_m` meters of the route.
    org_graph is the unprojected graph (lat/lon) returned by ox.project_graph(..., to_crs="EPSG:4326").
    """
    import math

    # gather route lat/lon
    lats = [org_graph.nodes[n]['y'] for n in route_nodes]
    lons = [org_graph.nodes[n]['x'] for n in route_nodes]

    # bounding box for route
    north, south = max(lats), min(lats)
    east, west = max(lons), min(lons)

    # approximate degree padding based on metres
    # 1 deg lat ~= 111 km; 1 deg lon ~= 111 km * cos(lat)
    avg_lat_rad = math.radians(sum(lats) / len(lats))
    pad_lat = buffer_m / 111_000
    pad_lon = buffer_m / (111_000 * abs(math.cos(avg_lat_rad)))

    bbox_north = north + pad_lat
    bbox_south = south - pad_lat
    bbox_east  = east + pad_lon
    bbox_west  = west - pad_lon

    # filter nodes within the expanded box
    nodes_in_bbox = [
        n for n, data in org_graph.nodes(data=True)
        if bbox_south <= data['y'] <= bbox_north and bbox_west <= data['x'] <= bbox_east
    ]

    # return an induced subgraph (copy to detach from original)
    return org_graph.subgraph(nodes_in_bbox).copy()


def main():
    # Build graphs
    G_proj = build_graph()
    # Unproject to lat/lon for plotting
    org_graph = ox.project_graph(G_proj, to_crs="EPSG:4326")
    # Build movement graphs
    M_base, M_policy = build_policy_graphs(G_proj, crossings_whitelist_nodes=None)

    # Choose a movement across the Rustavelli corridor
    movement_path = get_corridor_movement(G_proj, M_policy)
    final_path = movement_to_node_path(movement_path)

    # Crop the plotting graph to a small area around the route
    subgraph = crop_graph_to_route(org_graph, final_path, buffer_m=300)

    # Prepare output dirs
    frames_dir = "animation_frames"
    os.makedirs(frames_dir, exist_ok=True)

    # Generate frames
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
        ax.set_title(title, fontsize=14)
        fig.savefig(os.path.join(frames_dir, f"img_{i:03d}.png"), dpi=150, bbox_inches="tight")
        import matplotlib.pyplot as plt
        plt.close(fig)

    # Assemble GIF
    frame_files = sorted(f for f in os.listdir(frames_dir) if f.endswith(".png"))
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

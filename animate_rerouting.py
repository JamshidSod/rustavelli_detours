import os
import networkx as nx
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


def main():
    # build graphs
    G_proj = build_graph()
    org_graph = ox.project_graph(G_proj, to_crs="EPSG:4326")
    M_base, M_policy = build_policy_graphs(G_proj, crossings_whitelist_nodes=None)
    # choose first movement
    mv = next(candidate_movements(G_proj))
    start_edge = mv["entry_edge"]
    end_edge = mv["policy_exit_edge"]
    movement_path = shortest_path_movement(M_policy, start_edge, end_edge)
    final_path = movement_to_node_path(movement_path)
    # create frames directory
    output_dir = "animation_frames"
    os.makedirs(output_dir, exist_ok=True)
    # create frames
    location = "Rustavelli detour example"
    for i in range(1, len(final_path)+1):
        partial_route = final_path[:i]
        fig, ax = ox.plot_graph_route(
            org_graph,
            partial_route,
            route_linewidth=6,
            node_size=0,
            bgcolor="white",
            route_color="red",
            route_alpha=0.7,
            show=False,
            close=False,
        )
        ax.set_title(location)
        fig.savefig(os.path.join(output_dir, f"img_{i:03d}.png"), dpi=120, bbox_inches="tight")
        import matplotlib.pyplot as plt
        plt.close(fig)
    # assemble GIF
    frame_files = sorted([f for f in os.listdir(output_dir) if f.endswith(".png")])
    frames = [Image.open(os.path.join(output_dir, f)) for f in frame_files]
    gif_path = "rustavelli_detour_animation.gif"
    frames[0].save(
        gif_path,
        save_all=True,
        append_images=frames[1:],
        duration=100,
        loop=0,
    )
    print(f"Saved animation to {gif_path}")


if __name__ == "__main__":
    main()

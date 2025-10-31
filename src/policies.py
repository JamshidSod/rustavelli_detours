from .movement_graph import build_movement_graph


def build_policy_graphs(G, crossings_whitelist_nodes=None):
    # Baseline: allow all turns (no restrictions)
    M_base = build_movement_graph(
        G, forbid_left_uturn_on_corridor=False, enforce_perp_crossing=False, crossing_whitelist=None
    )
    # Policy: no left/U on corridor + enforce ~90° crossing at whitelisted nodes
    M_policy = build_movement_graph(
        G, forbid_left_uturn_on_corridor=True, enforce_perp_crossing=True, crossing_whitelist=crossings_whitelist_nodes
    )
    return M_base, M_policy

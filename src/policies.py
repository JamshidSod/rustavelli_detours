from .movement_graph import build_movement_graph

def build_policy_graphs(G, crossings_whitelist_nodes=None):
    """
    Create baseline and policy movement graphs from the projected street graph `G`.

    Parameters
    ----------
    G : MultiDiGraph
        Street graph with edge bearings and 'is_corridor' attributes.
    crossings_whitelist_nodes : set or None
        Node IDs where crossing the BRT corridor is allowed in the policy graph.
        Pass None if no crossings are allowed, or an empty set to forbid all crossings.

    Returns
    -------
    (M_base, M_policy) : tuple of DiGraphs
        M_base : baseline movement graph (no cross-corridor restrictions)
        M_policy : policy movement graph (cross-corridor only at whitelist, with ~90° enforcement)
    """
    # Baseline: allow all crossings, no perpendicular enforcement
    M_base = build_movement_graph(
        G,
        crossings_whitelist=None,   # None = no restrictions (baseline)
        enforce_perp_crossing=False
    )

    # Policy: allow crossings only at whitelisted nodes, enforce ~90° crossing
    M_policy = build_movement_graph(
        G,
        crossings_whitelist=crossings_whitelist_nodes,
        enforce_perp_crossing=True
    )

    return M_base, M_policy

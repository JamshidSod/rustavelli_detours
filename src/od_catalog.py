"""
Define candidate movements (forbidden left-turns and U-turns) on the Rustavelli corridor.

This module inspects the directed street graph and yields a list of movement
dictionaries. Each movement has:
    - node: the intersection node ID
    - type: "left" or "uturn"
    - entry_edge: the directed edge approaching the intersection
    - baseline_exit_edge: the directed edge the driver would take if the turn
      were allowed (i.e. a corridor edge)
    - policy_exit_edge: identical to baseline_exit_edge here; the policy graph
      will handle detours by blocking the cross-median movement.
"""

def _first_out_edge(G, node, predicate):
    """
    Return the first outgoing edge (v → w, k) from `node` for which
    predicate(data) returns True. If none match, return None.
    """
    for _, w, k, data in G.out_edges(node, keys=True, data=True):
        if predicate(data):
            return (node, w, k)
    return None

def candidate_movements(G):
    """
    Generate dictionaries describing all U-turns and left-turns at intersections
    along the Rustavelli corridor.

    A "left" movement is defined as an approach from a non-corridor side street
    into the corridor. A "uturn" movement is defined as an approach from the
    corridor itself (i.e. a driver coming along Rustavelli who would like to
    reverse direction).

    For each movement, baseline_exit_edge and policy_exit_edge are set to the
    first outgoing corridor edge. The policy graph will enforce the right-turn
    detour and 90° crossing when the movement is blocked.
    """
    movements = []

    for v in G.nodes():
        # Determine whether this node is on the corridor
        # by checking if any incident edge has is_corridor=True.
        incident_edges = list(G.in_edges(v, keys=True, data=True)) + \
                         list(G.out_edges(v, keys=True, data=True))
        if not any(data.get("is_corridor", False) for *_, data in incident_edges):
            continue  # skip nodes that don't touch Rustavelli

        # Find the first outgoing corridor edge at this node.
        # This will be used as the baseline and policy exit for both U-turns and left turns.
        corridor_out = _first_out_edge(G, v, lambda d: d.get("is_corridor", False))
        if corridor_out is None:
            # If there's no outgoing corridor edge (dead end), skip.
            continue

        # U-turn: entry is any incoming corridor edge (edge whose 'is_corridor' is True).
        for u, _, k, data in G.in_edges(v, keys=True, data=True):
            if data.get("is_corridor", False):
                movements.append({
                    "node": v,
                    "type": "uturn",
                    "entry_edge": (u, v, k),
                    "baseline_exit_edge": corridor_out,
                    "policy_exit_edge": corridor_out,
                })

        # Left-turn: entry is any incoming side-street edge (is_corridor=False).
        for u, _, k, data in G.in_edges(v, keys=True, data=True):
            if not data.get("is_corridor", False):
                movements.append({
                    "node": v,
                    "type": "left",
                    "entry_edge": (u, v, k),
                    "baseline_exit_edge": corridor_out,
                    "policy_exit_edge": corridor_out,
                })

    return movements

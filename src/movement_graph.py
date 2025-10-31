import networkx as nx
from .config import THROUGH_MAX, UTURN_MIN, TURN_DELAY_S, PERP_TOL

def turn_delta(b_in, b_out):
    """Return the turn angle difference in degrees within (–180, 180]."""
    incoming_heading = (b_in + 180) % 360
    return (b_out - incoming_heading + 540) % 360 - 180

def turn_type(delta):
    """
    Classify turn type based on absolute angle.
    The sign is used only for labeling (left/right).
    """
    ad = abs(delta)
    if ad > UTURN_MIN:
        return "uturn"
    if ad <= THROUGH_MAX:
        return "through"
    return "left" if delta > 0 else "right"

def is_perp(delta, tol=PERP_TOL):
    """Return True if the turn angle is approximately 90° (±tol)."""
    return abs(abs(delta) - 90) <= tol

def build_movement_graph(
    G,
    *,
    crossings_whitelist=None,
    enforce_perp_crossing=True,
    turn_delay=TURN_DELAY_S,
):
    """
    Construct an edge-based movement graph.

    Parameters
    ----------
    G : MultiDiGraph
        The projected street graph with edge bearings and 'is_corridor' attributes.
    crossings_whitelist : set or None
        Node IDs where cross-corridor movements are allowed. If None, crossings are unrestricted.
    enforce_perp_crossing : bool
        If True, require ~90° angles at whitelisted crossings.
    turn_delay : float
        Turn penalty (seconds) added to the travel time of each movement.
    """
    M = nx.DiGraph()
    M.graph["ref_graph"] = G

    # helper: does a graph node touch the corridor?
    def is_corridor_node(n):
        return any(d.get("is_corridor", False) for *_, d in G.in_edges(n, keys=True, data=True)) or \
               any(d.get("is_corridor", False) for *_, d in G.out_edges(n, keys=True, data=True))

    # add nodes (one per directed edge)
    for u, v, k, data in G.edges(keys=True, data=True):
        if data.get("length", 0) > 0:
            M.add_node((u, v, k), **data)

    # add allowed movements
    for u, v, k1, d1 in G.edges(keys=True, data=True):
        b_in = d1.get("bearing")
        if b_in is None:
            continue

        for _, w, k2, d2 in G.out_edges(v, keys=True, data=True):
            b_out = d2.get("bearing")
            if b_out is None:
                continue

            delta = turn_delta(b_in, b_out)
            ttype = turn_type(delta)
            allowed = True

            corridor_node = is_corridor_node(v)
            incoming_on_corridor = d1.get("is_corridor", False)
            outgoing_on_corridor = d2.get("is_corridor", False)
            crosses_corridor = incoming_on_corridor != outgoing_on_corridor

            if corridor_node and crosses_corridor:
                # Only restrict crossings if a whitelist is provided.
                if crossings_whitelist is not None:
                    if v not in crossings_whitelist:
                        allowed = False
                    elif enforce_perp_crossing and not is_perp(delta):
                        allowed = False
                # If crossings_whitelist is None, baseline mode → allow crossing

            if allowed:
                move_cost = float(d2.get("travel_time", 0.0)) + turn_delay
                M.add_edge(
                    (u, v, k1),
                    (v, w, k2),
                    weight=move_cost,
                    turn=ttype,
                    delta=delta,
                    corridor_node=corridor_node,
                    crosses_corridor=crosses_corridor,
                )

    return M

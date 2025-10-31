import networkx as nx
from .config import THROUGH_MAX, UTURN_MIN, TURN_DELAY_S, PERP_TOL

def turn_delta(b_in, b_out):
    """Return the turn angle difference in degrees within (–180, 180]."""
    incoming_heading = (b_in + 180) % 360
    d = (b_out - incoming_heading + 540) % 360 - 180
    return d

def turn_type(delta):
    """
    Classify turn type based on absolute angle.
    We don't rely on the sign for cross-corridor logic anymore.
    """
    ad = abs(delta)
    if ad > UTURN_MIN:
        return "uturn"
    if ad <= THROUGH_MAX:
        return "through"
    # We return 'left' or 'right' purely for informational purposes.
    # You can flip the sign here if needed.
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
    Build a movement graph with strict no-cross-corridor rules.
    - At any node touching the corridor, movements that change the
      corridor/non-corridor status are forbidden unless the node is in
      crossings_whitelist.
    - At whitelisted crossings, require ~90° angles if enforce_perp_crossing=True.
    - Right-turns and through-movements that stay on the same side of the corridor are allowed.
    """
    M = nx.DiGraph()
    M.graph["ref_graph"] = G

    # Add a node in M for each directed edge in G
    for u, v, k, data in G.edges(keys=True, data=True):
        # skip zero-length edges
        if data.get("length", 0) <= 0:
            continue
        M.add_node((u, v, k), **data)

    # Helper to test if a graph node touches the corridor
    def is_corridor_node(n):
        return any(d.get("is_corridor", False) for *_, d in G.in_edges(n, keys=True, data=True)) or \
               any(d.get("is_corridor", False) for *_, d in G.out_edges(n, keys=True, data=True))

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

            # Detect if this move crosses the corridor median:
            # It crosses if exactly one of the edges is on the corridor.
            crosses_corridor = incoming_on_corridor != outgoing_on_corridor

            if corridor_node and crosses_corridor:
                # Only allow cross-corridor movement at whitelisted nodes
                if crossings_whitelist is None or v not in crossings_whitelist:
                    allowed = False
                elif enforce_perp_crossing and not is_perp(delta):
                    # At whitelisted nodes, enforce ~90° crossing
                    allowed = False

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

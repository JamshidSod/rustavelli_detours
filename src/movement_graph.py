import networkx as nx
from .config import THROUGH_MAX, UTURN_MIN, RIGHT_LEFT_MIN, TURN_DELAY_S, PERP_TOL

def turn_delta(b_in, b_out):
    # Normalize (-180..180]
    incoming_heading = (b_in + 180) % 360
    d = (b_out - incoming_heading + 540) % 360 - 180
    return d

def turn_type(delta):
    ad = abs(delta)
    if ad > UTURN_MIN:
        return "uturn"
    if ad <= THROUGH_MAX:
        return "through"
    # If delta > 0, treat it as a LEFT; if delta < 0, treat it as a RIGHT
    return "left" if delta > 0 else "right"


def is_perp(delta, tol=PERP_TOL):
    return abs(abs(delta) - 90) <= tol

def build_movement_graph(G, *, forbid_left_uturn_on_corridor=True, enforce_perp_crossing=True, crossing_whitelist=None):
    """
    Build a movement graph M:
    - Nodes: directed edges of G (u,v,k).
    - Edges: allowed transitions (u->v,k1) -> (v->w,k2) with weight = travel_time(out_edge) + TURN_DELAY_S.
    """
    M = nx.DiGraph()
    M.graph["ref_graph"] = G

    for u, v, k, d1 in G.edges(keys=True, data=True):
        if d1.get("length", 0) <= 0: 
            continue
        M.add_node((u, v, k), **d1)

    for u, v, k1, d1 in G.edges(keys=True, data=True):
        b_in = d1.get("bearing", None)
        if b_in is None:
            continue

        for _, w, k2, d2 in G.out_edges(v, keys=True, data=True):
            b_out = d2.get("bearing", None)
            if b_out is None:
                continue

            delta = turn_delta(b_in, b_out)
            ttype = turn_type(delta)

            # Is node v part of the corridor area?
            corridor_node = any(G[x][y][kk].get("is_corridor", False) for x, y, kk in G.in_edges(v, keys=True)) \
                         or any(G[v][x][kk].get("is_corridor", False) for _, x, kk in G.out_edges(v, keys=True))

            allowed = True

            if forbid_left_uturn_on_corridor and corridor_node and ttype in {"left", "uturn"}:
                allowed = False

            # Enforce ~90° crossing only at listed crossings (if whitelist provided)
            if allowed and enforce_perp_crossing and corridor_node and crossing_whitelist is not None:
                if v in crossing_whitelist:
                    # require perpendicular-ish if transitioning between corridor-side legs
                    if not is_perp(delta):
                        allowed = False
                else:
                    # If not a legal crossing node, disallow transitions that would cross the median
                    # Heuristic: if one of the incident edges is on corridor and the other is not, and the move is 'through',
                    # we block it unless whitelisted. You can refine this with side-of-median checks.
                    if d1.get("is_corridor", False) != d2.get("is_corridor", False):
                        allowed = False

            if allowed:
                move_cost = float(d2.get("travel_time", 0.0)) + TURN_DELAY_S
                M.add_edge((u, v, k1), (v, w, k2),
                           weight=move_cost,
                           turn=ttype,
                           delta=delta,
                           corridor_node=corridor_node)
    return M

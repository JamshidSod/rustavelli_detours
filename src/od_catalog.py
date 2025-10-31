import networkx as nx

def _first_out_edge(G, node, chooser):
    """Pick the first outgoing edge from `node` whose data satisfies `chooser`"""
    for _, w, k, d in G.out_edges(node, keys=True, data=True):
        if chooser(d):
            return (node, w, k)
    return None


def candidate_movements(G):
    """
    Yield movement dicts with:
      - 'node' (corridor intersection),
      - 'entry_edge' (approach on corridor or side road),
      - 'baseline_exit_edge' (what the driver wanted: left or U),
      - 'policy_exit_edge' (where they must end up after detour; usually same as baseline target).
    This is a placeholder; in practice, define from your inventory of suppressed left/U.
    """
    for v in G.nodes():
        # gather all incident edges (inbound and outbound)
        incident = list(G.in_edges(v, keys=True, data=True)) + list(G.out_edges(v, keys=True, data=True))
        if not incident:
            continue
        # skip if none of the edges touch the corridor
        if not any(d.get("is_corridor", False) for *_, d in incident):
            continue

        # pick an entry edge on the corridor for u-turn
        entry_on_corridor = _first_out_edge(G, v, lambda d: d.get("is_corridor", False))
        # pick an entry edge on side road for left
        entry_on_side = _first_out_edge(G, v, lambda d: not d.get("is_corridor", False))

        if entry_on_corridor:
            yield {
                "type": "uturn",
                "node": v,
                "entry_edge": entry_on_corridor,
                "baseline_exit_edge": entry_on_corridor,  # U-turn target is the reverse direction
                "policy_exit_edge": entry_on_corridor,
            }
        if entry_on_side:
            # for left: exit into corridor (assume first corridor out)
            corridor_out = _first_out_edge(G, v, lambda d: d.get("is_corridor", False))
            if corridor_out:
                yield {
                    "type": "left",
                    "node": v,
                    "entry_edge": entry_on_side,
                    "baseline_exit_edge": corridor_out,
                    "policy_exit_edge": corridor_out,
                }

import pandas as pd
from .routing import shortest_path_movement, path_cost


def edge_sequence_from_movement_path(path):
    return list(path)


def path_length_m(G, path_edges):
    L = 0.0
    for (u, v, k) in path_edges:
        L += float(G[u][v][k].get("length", 0.0))
    return L


def shortest_or_none(M, s, t):
    try:
        return shortest_path_movement(M, s, t)
    except Exception:
        return None


def summarize(G, M_base, M_policy, movements, saverow=None):
    rows = []
    for mv in movements:
        start = mv["entry_edge"]
        end = mv["policy_exit_edge"]
        pb = shortest_or_none(M_base, start, end)
        pp = shortest_or_none(M_policy, start, end)
        if pb is None or pp is None:
            continue
        Lb = path_length_m(G, pb)
        Lp = path_length_m(G, pp)
        Tb = path_cost(M_base, pb)
        Tp = path_cost(M_policy, pp)
        rows.append({
            "node": mv["node"],
            "type": mv["type"],
            "distance_baseline_m": Lb,
            "time_baseline_s": Tb,
            "distance_policy_m": Lp,
            "time_policy_s": Tp,
            "delta_d_m": Lp - Lb,
            "delta_t_s": Tp - Tb,
            "efficiency": (Tb / Tp) if Tp > 0 else None,
            "n_links_policy": len(pp)
        })
        if saverow:
            saverow(mv, pb, pp)
    return pd.DataFrame(rows)

import networkx as nx


def shortest_path_movement(M, start_edge, end_edge, weight="weight"):
    return nx.shortest_path(M, source=start_edge, target=end_edge, weight=weight)


def path_cost(M, path, weight="weight"):
    return sum(M[a][b][weight] for a, b in zip(path[:-1], path[1:]))

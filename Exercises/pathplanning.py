import networkx as nx
import plotly.graph_objects as go
import networkx as nx
import math
from distance import haversine

TOPLEFT = (55.3714, 10.424)
TOPRIGHT = (55.3714, 10.4328)
BOTLEFT = (55.3659, 10.424)
BOTRIGHT = (55.3659, 10.4328)

RESOLUTION = 0.001


def render(graph: nx.Graph, edge_pairs: list):
    # for node, coords in nx.get_node_attributes(graph, 'pos').items():
    #     print(node, coords)
    fig = go.Figure(
        go.Scattermapbox(
            mode="markers",
            lat=[c[0] for c in nx.get_node_attributes(graph, "pos").values()],
            lon=[c[1] for c in nx.get_node_attributes(graph, "pos").values()],
            hoverinfo="text",
            text=[f"Node index: {n}" for n in graph.nodes],
            marker={"size": 10},
        )
    )
    fig.update_layout(
        margin={"l": 0, "t": 0, "b": 0, "r": 0},
        mapbox={
            "center": {"lon": 10.4284, "lat": 55.36865},
            "style": "stamen-terrain",
            "zoom": 15,
        },
    )
    for u, v in graph.edges:
        fig.add_trace(
            go.Scattermapbox(
                mode="lines",
                lon=[graph.nodes[u]["pos"][1], graph.nodes[v]["pos"][1]],
                lat=[graph.nodes[u]["pos"][0], graph.nodes[v]["pos"][0]],
                line={"color": "green" if (u, v) in edge_pairs else "red"},
                hovertext=f"{graph.edges[u, v]['dist']}",
            )
        )
    fig.show()


def drawGraph():
    graph = nx.Graph()
    # # graph.add_node(1000, pos=TOPRIGHT)
    # graph.add_node(1001, pos=TOPLEFT)
    # # graph.add_node(1002, pos=BOTRIGHT)
    # graph.add_node(1003, pos=BOTLEFT)

    lat = TOPRIGHT[0]

    node_index = 1

    first_run = True
    nodes_in_row = math.ceil((TOPRIGHT[1] - TOPLEFT[1]) / RESOLUTION) + 1

    while lat + RESOLUTION >= BOTRIGHT[0]:
        prev = None
        long = TOPRIGHT[1]
        while long + RESOLUTION >= TOPLEFT[1]:
            graph.add_node(node_index)
            graph.nodes[node_index]["pos"] = (
                max(lat, BOTRIGHT[0]),
                max(long, TOPLEFT[1]),
            )
            if prev:
                d = haversine(graph.nodes[prev]["pos"], graph.nodes[node_index]["pos"])
                graph.add_edge(prev, node_index, dist=d)
            if not first_run:
                d = haversine(
                    graph.nodes[node_index]["pos"],
                    graph.nodes[node_index - nodes_in_row]["pos"],
                )
                graph.add_edge(node_index, node_index - nodes_in_row, dist=d)
            prev = node_index
            long -= RESOLUTION
            node_index += 1
        lat -= RESOLUTION
        first_run = False
    # print(graph.nodes)
    shortestPath = nx.shortest_path(graph, source=1, target=70, weight="dist")
    edge_pairs = list(zip(shortestPath[:-1], shortestPath[1:]))

    edge_pairs = list(zip(shortestPath[:-1], shortestPath[1:]))

    render(graph, edge_pairs)
    return list(map(lambda p: graph.nodes[p]["pos"], shortestPath))


if __name__ == "__main__":
    drawGraph()

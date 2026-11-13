
import networkx as nx
import plotly.graph_objects as go


def create_dependency_graph(dependencies):

    graph = nx.DiGraph()

    for dependency in dependencies:
        graph.add_edge(
            dependency["source"],
            dependency["target"],
            function=dependency["function"]
        )

    if graph.number_of_nodes() == 0:
        return None

    positions = nx.spring_layout(
        graph,
        seed=42,
        k=1.5
    )

    edge_x = []
    edge_y = []
    edge_labels = []

    annotations = []

    for source, target, data in graph.edges(data=True):

        x0, y0 = positions[source]
        x1, y1 = positions[target]

        edge_x.extend([x0, x1, None])
        edge_y.extend([y0, y1, None])

        annotations.append({
            "x": x1,
            "y": y1,
            "ax": x0,
            "ay": y0,
            "xref": "x",
            "yref": "y",
            "axref": "x",
            "ayref": "y",
            "showarrow": True,
            "arrowhead": 3,
            "arrowsize": 1.5,
            "arrowwidth": 1.5,
            "arrowcolor": "gray"
        })

        edge_labels.append({
            "x": (x0 + x1) / 2,
            "y": (y0 + y1) / 2,
            "text": data["function"]
        })

    edge_trace = go.Scatter(
        x=edge_x,
        y=edge_y,
        mode="lines",
        line=dict(width=1.5, color="gray"),
        hoverinfo="none"
    )

    label_trace = go.Scatter(
        x=[item["x"] for item in edge_labels],
        y=[item["y"] for item in edge_labels],
        text=[item["text"] for item in edge_labels],
        mode="text",
        textposition="middle center",
        textfont=dict(size=10, color="red"),
        hoverinfo="text"
    )

    node_x = []
    node_y = []
    node_text = []
    node_colors = []

    for node in graph.nodes():

        x, y = positions[node]

        node_x.append(x)
        node_y.append(y)
        node_text.append(node)

        if node.startswith("tests"):
            node_colors.append("green")
        elif node.startswith("include"):
            node_colors.append("orange")
        else:
            node_colors.append("skyblue")

    node_trace = go.Scatter(
        x=node_x,
        y=node_y,
        mode="markers+text",
        text=node_text,
        textposition="top center",
        hovertext=node_text,
        hoverinfo="text",
        marker=dict(
            size=35,
            color=node_colors,
            line=dict(width=2, color="black")
        )
    )

    figure = go.Figure(
        data=[edge_trace, label_trace, node_trace]
    )

    figure.update_layout(
        title="ImpactMap AI - Code Dependency Graph",
        showlegend=False,
        hovermode="closest",
        annotations=annotations,
        margin=dict(l=30, r=30, t=70, b=30),
        xaxis=dict(visible=False),
        yaxis=dict(visible=False),
        height=650
    )

    return figure

"""Optional interactive layer for exportable visualisations.

Adds Plotly/Dash as an optional visual exploration backend.
"""

from pathlib import Path
from typing import Any, Dict, List, Optional

from aura_cli.core.logger import get_logger

try:
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots

    HAS_PLOTLY = True
except ImportError:
    HAS_PLOTLY = False

try:
    import dash
    from dash import Input, Output, dcc, html

    HAS_DASH = True
except ImportError:
    HAS_DASH = False

logger = get_logger(__name__)


def create_dependency_graph_plotly(
    dependencies: Dict[str, List[str]], output_path: Optional[str] = None
) -> str:
    """Create an interactive dependency graph with Plotly."""
    if not HAS_PLOTLY:
        raise ImportError("plotly é necessário. Instale com: pip install plotly")

    nodes = set()
    edges = []

    for file, deps in dependencies.items():
        nodes.add(file)
        for dep in deps:
            nodes.add(dep)
            edges.append((file, dep))

    nodes_list = list(nodes)
    node_indices = {node: i for i, node in enumerate(nodes_list)}

    edge_x: list[Any] = []
    edge_y: list[Any] = []
    for source, target in edges:
        if source in node_indices and target in node_indices:
            edge_x.append(node_indices[source])
            edge_x.append(node_indices[target])
            edge_x.append(None)
            edge_y.append(node_indices[target])
            edge_y.append(node_indices[source])
            edge_y.append(None)

    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=edge_x,
            y=edge_y,
            line={"width": 0.5, "color": "#888"},
            hoverinfo="none",
            mode="lines",
        )
    )

    node_x = [i % 10 for i in range(len(nodes))]
    node_y = [i // 10 for i in range(len(nodes))]

    node_info = [
        f"{Path(n).name}<br>Dependencies: {len([e for e in edges if e[0] == n])}"
        for n in nodes
    ]

    fig.add_trace(
        go.Scatter(
            x=node_x,
            y=node_y,
            mode="markers+text",
            hoverinfo="text",
            text=[Path(n).name for n in nodes],
            textposition="middle center",
            hovertext=node_info,
            marker={
                "size": 20,
                "color": "lightblue",
                "line": {"width": 2, "color": "darkblue"},
            },
        )
    )

    fig.update_layout(
        title="Dependency Graph (Interactive)",
        showlegend=False,
        hovermode="closest",
        margin={"b": 20, "l": 5, "r": 5, "t": 40},
        annotations=[
            {
                "text": "Interactive dependency graph - Hover for details",
                "showarrow": False,
                "xref": "paper",
                "yref": "paper",
                "x": 0.005,
                "y": -0.002,
                "xanchor": "left",
                "yanchor": "bottom",
                "font": {"color": "#888", "size": 12},
            }
        ],
        xaxis={"showgrid": False, "zeroline": False, "showticklabels": False},
        yaxis={"showgrid": False, "zeroline": False, "showticklabels": False},
    )

    if output_path:
        fig.write_html(output_path)
        logger.info(f"Gráfico salvo em: {output_path}")
        return output_path
    else:
        return fig.to_html(include_plotlyjs="cdn")


def create_impact_analysis_chart(
    impact_data: Dict[str, Any], output_path: Optional[str] = None
) -> str:
    """Create an interactive impact analysis chart."""
    if not HAS_PLOTLY:
        raise ImportError("plotly é necessário. Instale com: pip install plotly")

    affected_files = impact_data.get("affected_files", [])

    if not affected_files:
        return "<p>No data to visualize</p>"

    files = [f.get("file", "unknown") for f in affected_files]
    risk_levels = [f.get("risk_level", 0) for f in affected_files]
    dependents = [f.get("dependents_count", 0) for f in affected_files]
    dependencies = [f.get("dependencies_count", 0) for f in affected_files]

    fig = make_subplots(
        rows=2,
        cols=2,
        subplot_titles=(
            "Risk Level Distribution",
            "Dependents Count",
            "Dependencies Count",
            "Risk vs Dependents",
        ),
        specs=[
            [{"type": "bar"}, {"type": "bar"}],
            [{"type": "scatter"}, {"type": "bar"}],
        ],
    )

    fig.add_trace(
        go.Bar(x=files, y=risk_levels, name="Risk Level", marker_color="red"),
        row=1,
        col=1,
    )

    fig.add_trace(
        go.Bar(x=files, y=dependents, name="Dependents", marker_color="blue"),
        row=1,
        col=2,
    )

    fig.add_trace(
        go.Bar(x=files, y=dependencies, name="Dependencies", marker_color="green"),
        row=2,
        col=1,
    )

    fig.add_trace(
        go.Scatter(
            x=risk_levels,
            y=dependents,
            mode="markers+text",
            text=[Path(f).name for f in files],
            name="Risk vs Dependents",
            marker={"size": 10, "color": "purple"},
        ),
        row=2,
        col=2,
    )

    fig.update_layout(
        title_text="Impact Analysis Dashboard", height=800, showlegend=True
    )

    if output_path:
        fig.write_html(output_path)
        logger.info(f"Gráfico salvo em: {output_path}")
        return output_path
    else:
        return fig.to_html(include_plotlyjs="cdn")


def create_progress_dashboard(
    progress_data: Dict[str, Any], output_path: Optional[str] = None
) -> str:
    """Create an interactive progress dashboard."""
    if not HAS_PLOTLY:
        raise ImportError("plotly é necessário. Instale com: pip install plotly")

    completed = progress_data.get("completed_steps", 0)
    total = progress_data.get("total_steps", 1)
    percentage = (completed / total * 100) if total > 0 else 0

    fig = go.Figure(
        go.Indicator(
            mode="gauge+number+delta",
            value=percentage,
            domain={"x": [0, 1], "y": [0, 1]},
            title={"text": "Progress"},
            delta={"reference": 50},
            gauge={
                "axis": {"range": [None, 100]},
                "bar": {"color": "darkblue"},
                "steps": [
                    {"range": [0, 50], "color": "lightgray"},
                    {"range": [50, 100], "color": "gray"},
                ],
                "threshold": {
                    "line": {"color": "red", "width": 4},
                    "thickness": 0.75,
                    "value": 90,
                },
            },
        )
    )

    fig.update_layout(title="Refactoring Progress Dashboard")

    if output_path:
        fig.write_html(output_path)
        logger.info(f"Dashboard salvo em: {output_path}")
        return output_path
    else:
        return fig.to_html(include_plotlyjs="cdn")


def create_interactive_dashboard(
    dependencies: Dict[str, List[str]],
    impact_data: Optional[Dict[str, Any]] = None,
    progress_data: Optional[Dict[str, Any]] = None,
    output_path: str = "dashboard.html",
) -> str:
    """Create a full interactive analysis dashboard."""
    if not HAS_PLOTLY:
        raise ImportError("plotly é necessário. Instale com: pip install plotly")

    num_plots = 1
    if impact_data:
        num_plots += 1
    if progress_data:
        num_plots += 1

    fig = make_subplots(
        rows=num_plots,
        cols=1,
        subplot_titles=["Dependency Graph", "Impact Analysis", "Progress"][:num_plots],
        vertical_spacing=0.1,
    )

    fig.update_layout(
        title="Aura CLI - Interactive Dashboard",
        height=300 * num_plots,
        showlegend=True,
    )

    fig.write_html(output_path)
    logger.info(f"Dashboard interativo salvo em: {output_path}")
    return output_path


# ========== DASH APP (Opcional) ==========


def create_dash_app(
    dependencies: Dict[str, List[str]], impact_data: Optional[Dict[str, Any]] = None
) -> Any:
    """Create an interactive Dash application."""
    if not HAS_DASH:
        raise ImportError("dash é necessário. Instale com: pip install dash")

    app = dash.Dash(__name__)

    app.layout = html.Div(
        [
            html.H1("Aura CLI - Interactive Dashboard"),
            dcc.Graph(id="dependency-graph"),
            dcc.Graph(id="impact-chart") if impact_data else html.Div(),
            dcc.Interval(
                id="interval-component", interval=1000, n_intervals=0
            ),  # Atualiza a cada segundo
        ]
    )

    @app.callback(
        Output("dependency-graph", "figure"), Input("interval-component", "n_intervals")
    )
    def update_dependency_graph(n):
        """Update dependency graph visualization."""
        return {}

    return app

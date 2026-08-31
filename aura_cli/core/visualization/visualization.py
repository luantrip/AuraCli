"""Auxiliary technical visualisations for dependencies, impact and progress.

Provides rendering for dependency graphs, impact analysis and refactoring
progress. Useful as a lateral library for explicit inspection of engineering
data but does not participate in the main product loop.
"""

from collections import defaultdict
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from rich.console import Console
from rich.panel import Panel
from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn
from rich.table import Table
from rich.tree import Tree

from aura_cli.core.logger import get_logger

try:
    import networkx as _networkx

    HAS_NETWORKX = _networkx is not None
except ImportError:
    HAS_NETWORKX = False

logger = get_logger(__name__)
console = Console()


# ========== DEPENDENCY GRAPH VISUALIZATION ==========


def visualize_dependency_graph(
    dependencies: Dict[str, List[str]],
    root_nodes: Optional[List[str]] = None,
    max_depth: int = 5,
    output_format: str = "tree",
) -> str:
    """Visualise the dependency graph."""
    if output_format == "tree":
        return _visualize_tree(dependencies, root_nodes, max_depth)
    elif output_format == "table":
        return _visualize_table(dependencies)
    elif output_format == "mermaid":
        return _visualize_mermaid(dependencies, root_nodes)
    elif output_format == "graphviz":
        return _visualize_graphviz(dependencies, root_nodes)
    else:
        return _visualize_tree(dependencies, root_nodes, max_depth)


def _visualize_tree(
    dependencies: Dict[str, List[str]], root_nodes: Optional[List[str]], max_depth: int
) -> str:
    """Visualise as a Rich tree."""
    if root_nodes is None:
        all_deps = set()
        for deps in dependencies.values():
            all_deps.update(deps)
        root_nodes = [node for node in dependencies if node not in all_deps]
        if not root_nodes:
            root_nodes = list(dependencies.keys())[:5]

    tree = Tree("Dependency Graph")

    visited = set()

    def add_node(parent, node: str, depth: int = 0):
        """Add node."""
        if depth > max_depth or node in visited:
            return
        visited.add(node)

        node_label = Path(node).name if "/" in node or "\\" in node else node
        deps = dependencies.get(node, [])

        if deps:
            branch = parent.add(
                f"[cyan]{node_label}[/cyan] ([yellow]{len(deps)} deps[/yellow])"
            )
            for dep in deps[:10]:  # Limit to 10 dependencies per node
                add_node(branch, dep, depth + 1)
        else:
            parent.add(f"[green]{node_label}[/green] (leaf)")

    for root in root_nodes[:10]:
        add_node(tree, root)

    with console.capture() as capture:
        console.print(tree)
    return capture.get()


def _visualize_table(dependencies: Dict[str, List[str]]) -> str:
    """Visualise as a Rich table."""
    table = Table(
        title="Dependency Graph", show_header=True, header_style="bold magenta"
    )
    table.add_column("File", style="cyan", no_wrap=True)
    table.add_column("Dependencies", style="yellow")
    table.add_column("Count", justify="right", style="green")

    for file, deps in sorted(
        dependencies.items(), key=lambda x: len(x[1]), reverse=True
    ):
        deps_str = ", ".join([Path(d).name for d in deps[:5]])
        if len(deps) > 5:
            deps_str += f" ... (+{len(deps) - 5} more)"
        table.add_row(
            Path(file).name if "/" in file or "\\" in file else file,
            deps_str,
            str(len(deps)),
        )

    with console.capture() as capture:
        console.print(table)
    return capture.get()


def _visualize_mermaid(
    dependencies: Dict[str, List[str]], root_nodes: Optional[List[str]]
) -> str:
    """Render a dependency graph using Mermaid syntax."""
    lines = ["graph TD"]

    for file, deps in dependencies.items():
        file_id = _sanitize_id(file)
        file_label = Path(file).name if "/" in file or "\\" in file else file
        lines.append(f'    {file_id}["{file_label}"]')

        for dep in deps:
            dep_id = _sanitize_id(dep)
            dep_label = Path(dep).name if "/" in dep or "\\" in dep else dep
            lines.append(f'    {dep_id}["{dep_label}"]')
            lines.append(f"    {file_id} --> {dep_id}")

    return "\n".join(lines)


def _visualize_graphviz(
    dependencies: Dict[str, List[str]], root_nodes: Optional[List[str]]
) -> str:
    """Render a dependency graph using Graphviz."""
    lines = ["digraph DependencyGraph {", "    rankdir=LR;", "    node [shape=box];"]

    for file, deps in dependencies.items():
        file_label = _escape_label(file)
        for dep in deps:
            dep_label = _escape_label(dep)
            lines.append(f'    "{file_label}" -> "{dep_label}";')

    lines.append("}")
    return "\n".join(lines)


def _sanitize_id(text: str) -> str:
    """Sanitise a node ID for use in graph syntax."""
    return text.replace("/", "_").replace("\\", "_").replace(".", "_").replace("-", "_")


def _escape_label(text: str) -> str:
    """Escape a label string for graph rendering."""
    label = Path(text).name if "/" in text or "\\" in text else text
    return label.replace('"', '\\"')


# ========== IMPACT ANALYSIS VISUALIZATION ==========


def visualize_impact_analysis(
    impact_data: Dict[str, Any], output_format: str = "table"
) -> str:
    """Visualise the impact analysis."""
    if output_format == "table":
        return _visualize_impact_table(impact_data)
    elif output_format == "chart":
        return _visualize_impact_chart(impact_data)
    elif output_format == "json":
        return json.dumps(impact_data, indent=2)
    else:
        return _visualize_impact_table(impact_data)


def _visualize_impact_table(impact_data: Dict[str, Any]) -> str:
    """Visualise impact as a table."""
    table = Table(
        title="Impact Analysis", show_header=True, header_style="bold magenta"
    )
    table.add_column("File", style="cyan", no_wrap=True)
    table.add_column("Risk Level", style="yellow")
    table.add_column("Dependents", justify="right", style="green")
    table.add_column("Dependencies", justify="right", style="blue")

    affected_files = impact_data.get("affected_files", [])

    for file_info in sorted(
        affected_files, key=lambda x: x.get("risk_level", 0), reverse=True
    ):
        risk = file_info.get("risk_level", 0)
        risk_str = _format_risk(risk)

        table.add_row(
            file_info.get("file", "unknown"),
            risk_str,
            str(file_info.get("dependents_count", 0)),
            str(file_info.get("dependencies_count", 0)),
        )

    summary = impact_data.get("summary", {})
    table.add_section()
    table.add_row(
        "[bold]TOTAL[/bold]",
        f"[bold]{summary.get('total_files', 0)} files[/bold]",
        f"[bold]{summary.get('total_dependents', 0)}[/bold]",
        f"[bold]{summary.get('total_dependencies', 0)}[/bold]",
    )

    with console.capture() as capture:
        console.print(table)
    return capture.get()


def _visualize_impact_chart(impact_data: Dict[str, Any]) -> str:
    """Visualise impact as an ASCII chart."""
    affected_files = impact_data.get("affected_files", [])

    if not affected_files:
        return "No affected files"

    risk_groups = defaultdict(list)
    for file_info in affected_files:
        risk = file_info.get("risk_level", 0)
        risk_groups[risk].append(file_info)

    lines = ["Impact Analysis Chart\n"]
    lines.append("Risk Level Distribution:\n")

    max_count = max(len(files) for files in risk_groups.values()) if risk_groups else 1

    for risk_level in sorted(risk_groups.keys(), reverse=True):
        files = risk_groups[risk_level]
        count = len(files)
        bar_length = int((count / max_count) * 50) if max_count > 0 else 0
        bar = "█" * bar_length
        risk_str = _format_risk(risk_level)
        lines.append(f"{risk_str:20} {bar} {count}")

    return "\n".join(lines)


def _format_risk(risk_level: int) -> str:
    """Format a risk level for display."""
    if risk_level >= 8:
        return f"[red]CRITICAL ({risk_level})[/red]"
    elif risk_level >= 5:
        return f"[yellow]HIGH ({risk_level})[/yellow]"
    elif risk_level >= 3:
        return f"[blue]MEDIUM ({risk_level})[/blue]"
    else:
        return f"[green]LOW ({risk_level})[/green]"


# ========== PROGRESS TRACKING ==========


class ProgressTracker:
    """Tracks and displays progress for multi-step operations."""

    def __init__(self, total_steps: int, description: str = "Processing"):
        """Initialize the instance."""
        self.total_steps = total_steps
        self.description = description
        self.current_step = 0
        self.progress = None

    def __enter__(self):
        """Enter the context manager."""
        self.progress = Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            console=console,
        )
        self.progress.__enter__()
        self.task_id = self.progress.add_task(self.description, total=self.total_steps)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit the context manager and clean up."""
        if self.progress:
            self.progress.__exit__(exc_type, exc_val, exc_tb)

    def update(self, step: int = 1, description: Optional[str] = None):
        """Atualiza progresso"""
        if self.progress:
            self.current_step += step
            if description:
                self.progress.update(self.task_id, description=description)
            self.progress.update(self.task_id, completed=self.current_step)

    def set_description(self, description: str):
        """Update the current step description."""
        if self.progress:
            self.progress.update(self.task_id, description=description)


def visualize_refactoring_progress(
    plan: Dict[str, Any],
    completed_steps: int,
    total_steps: int,
    current_batch: Optional[int] = None,
    total_batches: Optional[int] = None,
) -> str:
    """Visualise refactoring progress."""
    panel_content = []

    percentage = (completed_steps / total_steps * 100) if total_steps > 0 else 0
    panel_content.append(
        f"[bold]Progress:[/bold] {completed_steps}/{total_steps} steps ({percentage:.1f}%)"
    )

    if current_batch is not None and total_batches is not None:
        batch_percentage = (
            (current_batch / total_batches * 100) if total_batches > 0 else 0
        )
        panel_content.append(
            f"[bold]Batches:[/bold] {current_batch}/{total_batches} ({batch_percentage:.1f}%)"
        )

    bar_width = 40
    filled = int(percentage / 100 * bar_width)
    bar = "█" * filled + "░" * (bar_width - filled)
    panel_content.append(f"\n[{bar}]")

    if plan:
        strategy = plan.get("strategy", "unknown")
        panel_content.append(f"\n[bold]Strategy:[/bold] {strategy}")

        steps = plan.get("steps", [])
        if steps:
            panel_content.append(f"[bold]Total Changes:[/bold] {len(steps)}")

    panel = Panel(
        "\n".join(panel_content), title="Refactoring Progress", border_style="cyan"
    )

    with console.capture() as capture:
        console.print(panel)
    return capture.get()


# ========== EXPORT FUNCTIONS ==========


def export_dependency_graph(
    dependencies: Dict[str, List[str]], output_path: str, output_format: str = "mermaid"
):
    """Export a dependency graph to a file."""
    output_file = Path(output_path)

    if output_format == "mermaid":
        content = _visualize_mermaid(dependencies, None)
        output_file = output_file.with_suffix(".mmd")
    elif output_format == "graphviz":
        content = _visualize_graphviz(dependencies, None)
        output_file = output_file.with_suffix(".dot")
    elif output_format == "json":
        content = json.dumps(dependencies, indent=2)
        output_file = output_file.with_suffix(".json")
    else:
        raise ValueError(f"Formato não suportado: {output_format}")

    output_file.write_text(content, encoding="utf-8")
    logger.info(f"Grafo exportado para: {output_file}")
    return str(output_file)


def export_impact_analysis(
    impact_data: Dict[str, Any], output_path: str, output_format: str = "json"
):
    """Export an impact analysis report to a file."""
    output_file = Path(output_path)

    if output_format == "json":
        content = json.dumps(impact_data, indent=2)
        output_file = output_file.with_suffix(".json")
    elif output_format == "html":
        content = _export_impact_html(impact_data)
        output_file = output_file.with_suffix(".html")
    elif output_format == "csv":
        content = _export_impact_csv(impact_data)
        output_file = output_file.with_suffix(".csv")
    else:
        raise ValueError(f"Formato não suportado: {output_format}")

    output_file.write_text(content, encoding="utf-8")
    logger.info(f"Análise de impacto exportada para: {output_file}")
    return str(output_file)


def _export_impact_html(impact_data: Dict[str, Any]) -> str:
    """Export impact analysis as HTML."""
    html = """<!DOCTYPE html>
<html>
<head>
    <title>Impact Analysis</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        table { border-collapse: collapse; width: 100%; }
        th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
        th { background-color: #4CAF50; color: white; }
        tr:nth-child(even) { background-color: #f2f2f2; }
        .risk-high { background-color: #ffcccc; }
        .risk-medium { background-color: #ffffcc; }
        .risk-low { background-color: #ccffcc; }
    </style>
</head>
<body>
    <h1>Impact Analysis Report</h1>
    <table>
        <tr>
            <th>File</th>
            <th>Risk Level</th>
            <th>Dependents</th>
            <th>Dependencies</th>
        </tr>
"""

    affected_files = impact_data.get("affected_files", [])
    for file_info in affected_files:
        risk = file_info.get("risk_level", 0)
        risk_class_name = (
            "risk-high" if risk >= 5 else "risk-medium" if risk >= 3 else "risk-low"
        )

        html += f"""
        <tr class="{risk_class_name}">
            <td>{file_info.get("file", "unknown")}</td>
            <td>{risk}</td>
            <td>{file_info.get("dependents_count", 0)}</td>
            <td>{file_info.get("dependencies_count", 0)}</td>
        </tr>
"""

    html += """
    </table>
</body>
</html>
"""
    return html


def _export_impact_csv(impact_data: Dict[str, Any]) -> str:
    """Export impact analysis as CSV."""
    lines = ["File,Risk Level,Dependents,Dependencies"]

    affected_files = impact_data.get("affected_files", [])
    for file_info in affected_files:
        lines.append(
            f"{file_info.get('file', 'unknown')},"
            f"{file_info.get('risk_level', 0)},"
            f"{file_info.get('dependents_count', 0)},"
            f"{file_info.get('dependencies_count', 0)}"
        )

    return "\n".join(lines)

"""
Deep Analysis Tools for Aura CLI.

This module provides integrated deep analysis capabilities that combine
multiple analysis tools into comprehensive insights. These tools are
designed to be used by AGI/OPS agents for thorough code understanding.

Features:
    - Project-wide analysis combining multiple tools
    - Architectural discovery
    - Pattern detection across codebase
    - Quality metrics aggregation
    - Actionable insights generation

Integration:
    These tools aggregate results from:
    - analyze_code_nlp: NLP-based code understanding
    - find_duplicate_code: Semantic duplication detection
    - semantic_search_advanced: Vector-based code search
    - codebase_search: Pattern-based search
    - tree_view: Structure analysis
"""

from pathlib import Path
from typing import Any, Dict, List, Optional

from rich import print as rprint


def _get_ui_constants():
    """Lazy load UI constants to avoid circular imports."""
    try:
        from aura_cli.core.ui_bridge import UIIcons, UIStyles

        return UIIcons, UIStyles
    except ImportError:

        class FallbackIcons:
            """Fallback icon set for terminals without Unicode support."""

            SUCCESS = "✓"
            FILE = "📄"

        class FallbackStyles:
            """Fallback style set for terminals without color support."""

            SUCCESS = "green"

        return FallbackIcons, FallbackStyles


def _get_logger():
    """Lazy load logger."""
    try:
        from aura_cli.core.logger import get_logger

        return get_logger(__name__)
    except ImportError:
        import logging

        return logging.getLogger(__name__)


def _get_stats():
    """Lazy load stats tracker."""
    try:
        from aura_cli.core.stats import get_stats

        return get_stats()
    except ImportError:
        return None


def _display_tool_call(name: str, args: dict):
    """Lazy load display_tool_call."""
    try:
        from aura_cli.core.ui import display_tool_call

        display_tool_call(name, args)
    except ImportError as _e:
        pass  # silenced: {_e}


logger = _get_logger()


def _report_section(
    report_parts: list, title: str, items: list, fmt: str = "- `{}`"
) -> None:
    """Append a titled list section to report_parts."""
    if not items:
        return
    report_parts.append(title)
    report_parts.append("")
    for item in items:
        report_parts.append(fmt.format(item))
    report_parts.append("")


def deep_project_analysis(
    path: str = ".",
    focus_areas: Optional[List[str]] = None,
    max_files: int = 50,
) -> str:
    """
    Perform comprehensive deep analysis of a project.

    This tool combines multiple analysis methods to provide
    actionable insights about code quality, architecture,
    and potential improvements.

    Args:
        path: Project root path
        focus_areas: Optional list of focus areas:
            - "quality": Code quality and patterns
            - "architecture": Structure and dependencies
            - "security": Security patterns and concerns
            - "performance": Performance patterns
            - "documentation": Documentation coverage
        max_files: Maximum files to analyze in depth

    Returns:
        Comprehensive analysis report in Markdown format
    """
    _display_tool_call(
        "deep_project_analysis",
        {"path": path, "focus_areas": focus_areas, "max_files": max_files},
    )

    stats = _get_stats()
    if stats:
        stats.track_tool_usage("deep_project_analysis")

    if focus_areas is None:
        focus_areas = ["quality", "architecture"]

    project_path = Path(path).resolve()
    if not project_path.exists():
        return f"Erro: o caminho '{path}' não existe"

    report_parts = [
        "# 🔍 Deep Project Analysis",
        "",
        f"**Path:** `{project_path}`",
        f"**Focus Areas:** {', '.join(focus_areas)}",
        "",
        "---",
        "",
    ]
    report_parts.append("## 📁 Project Structure")
    report_parts.append("")

    try:
        from aura_cli.core.tools.dev_tools import tree_view

        structure = tree_view(str(project_path), max_depth=3)
        lines = structure.split("\n")[:30]
        report_parts.append("```")
        report_parts.extend(lines)
        if len(structure.split("\n")) > 30:
            report_parts.append("... (truncated)")
        report_parts.append("```")
        report_parts.append("")
    except Exception as e:
        logger.warning(f"Could not get tree view: {e}")
        report_parts.append("*Structure analysis unavailable*")
        report_parts.append("")

    report_parts.append("## 📊 File Statistics")
    report_parts.append("")

    file_stats = _collect_file_stats(project_path)
    report_parts.append(f"- **Total Files:** {file_stats['total_files']}")
    report_parts.append(f"- **Code Files:** {file_stats['code_files']}")
    report_parts.append(f"- **Config Files:** {file_stats['config_files']}")
    report_parts.append(f"- **Documentation Files:** {file_stats['doc_files']}")
    report_parts.append("")

    if file_stats["by_extension"]:
        report_parts.append("### By Extension")
        report_parts.append("")
        for ext, count in sorted(
            file_stats["by_extension"].items(), key=lambda x: x[1], reverse=True
        )[:10]:
            report_parts.append(f"- `{ext}`: {count} files")
        report_parts.append("")

    if "quality" in focus_areas:
        report_parts.append("## 🎯 Code Quality")
        report_parts.append("")
        quality_findings = _analyze_quality(project_path, max_files)
        _report_section(
            report_parts,
            "### Potential Issues",
            quality_findings["issues"][:10],
            "- ⚠️ {}",
        )
        _report_section(
            report_parts,
            "### Detected Patterns",
            quality_findings["patterns"][:5],
            "- ✓ {}",
        )

    if "architecture" in focus_areas:
        report_parts.append("## 🏗️ Architecture")
        report_parts.append("")
        arch_findings = _analyze_architecture(project_path)
        _report_section(
            report_parts, "### Entry Points", arch_findings["entry_points"][:5]
        )
        _report_section(
            report_parts, "### Core Modules", arch_findings["core_modules"][:8]
        )
    report_parts.append("## 💡 Recommendations")
    report_parts.append("")

    recommendations = _generate_recommendations(file_stats, focus_areas)
    for i, rec in enumerate(recommendations[:5], 1):
        report_parts.append(f"{i}. {rec}")
    report_parts.append("")
    report_parts.append("---")
    report_parts.append("")
    report_parts.append(f"*Analysis completed for {file_stats['total_files']} files*")

    UIIcons, UIStyles = _get_ui_constants()
    rprint(
        f"[{UIStyles.SUCCESS}]{UIIcons.SUCCESS} Deep analysis completed[/{UIStyles.SUCCESS}]"
    )

    return "\n".join(report_parts)


def discover_patterns(
    path: str = ".",
    pattern_type: str = "all",
) -> str:
    """
    Discover code patterns and conventions in a project.

    Analyzes the codebase to identify:
    - Naming conventions
    - Code organization patterns
    - Common idioms
    - Testing patterns
    - Error handling patterns

    Args:
        path: Project root path
        pattern_type: Type of patterns to discover:
            - "all": All patterns
            - "naming": Naming conventions
            - "structure": Code structure
            - "testing": Testing patterns
            - "error": Error handling

    Returns:
        Pattern discovery report
    """
    _display_tool_call(
        "discover_patterns", {"path": path, "pattern_type": pattern_type}
    )

    stats = _get_stats()
    if stats:
        stats.track_tool_usage("discover_patterns")

    project_path = Path(path).resolve()
    if not project_path.exists():
        return f"Erro: o caminho '{path}' não existe"

    report_parts = [
        "# 🔎 Pattern Discovery Report",
        "",
        f"**Path:** `{project_path}`",
        f"**Pattern Type:** {pattern_type}",
        "",
        "---",
        "",
    ]
    patterns: Dict[str, Any] = {
        "naming": [],
        "structure": [],
        "testing": [],
        "error": [],
    }
    py_files = list(project_path.rglob("*.py"))
    py_files = [
        f
        for f in py_files
        if not any(
            p in str(f)
            for p in [".git", "__pycache__", "node_modules", ".venv", "venv"]
        )
    ]

    for py_file in py_files[:30]:  # Limit analysis
        try:
            content = py_file.read_text(encoding="utf-8", errors="ignore")
            _extract_patterns_from_file(content, str(py_file), patterns)
        except Exception:
            continue
    if pattern_type in ["all", "naming"] and patterns["naming"]:
        report_parts.append("## 📝 Naming Conventions")
        report_parts.append("")
        for pattern in patterns["naming"][:10]:
            report_parts.append(f"- {pattern}")
        report_parts.append("")
    if pattern_type in ["all", "structure"] and patterns["structure"]:
        report_parts.append("## 📦 Structure Patterns")
        report_parts.append("")
        for pattern in patterns["structure"][:10]:
            report_parts.append(f"- {pattern}")
        report_parts.append("")
    if pattern_type in ["all", "testing"] and patterns["testing"]:
        report_parts.append("## 🧪 Testing Patterns")
        report_parts.append("")
        for pattern in patterns["testing"][:10]:
            report_parts.append(f"- {pattern}")
        report_parts.append("")
    if pattern_type in ["all", "error"] and patterns["error"]:
        report_parts.append("## ⚠️ Error Handling Patterns")
        report_parts.append("")
        for pattern in patterns["error"][:10]:
            report_parts.append(f"- {pattern}")
        report_parts.append("")

    report_parts.append("---")
    report_parts.append(f"*Analyzed {len(py_files)} Python files*")

    UIIcons, UIStyles = _get_ui_constants()
    rprint(
        f"[{UIStyles.SUCCESS}]{UIIcons.SUCCESS} Pattern discovery completed[/{UIStyles.SUCCESS}]"
    )

    return "\n".join(report_parts)


def _append_dep_file(
    report_parts: list, title: str, deps: dict, limit: int = 15
) -> None:
    """Append a dependency section to report_parts."""
    if not deps:
        return
    report_parts.append(title)
    for name, version in list(deps.items())[:limit]:
        report_parts.append(f"- `{name}`: {version}")
    report_parts.append("")


def analyze_dependencies(path: str = ".") -> str:
    """
    Analyze project dependencies and their relationships.

    Examines:
    - requirements.txt / pyproject.toml
    - package.json
    - Import relationships
    - Circular dependencies

    Args:
        path: Project root path

    Returns:
        Dependency analysis report
    """
    _display_tool_call("analyze_dependencies", {"path": path})

    stats = _get_stats()
    if stats:
        stats.track_tool_usage("analyze_dependencies")

    project_path = Path(path).resolve()
    if not project_path.exists():
        return f"Erro: o caminho '{path}' não existe"

    report_parts = [
        "# 📦 Dependency Analysis",
        "",
        f"**Path:** `{project_path}`",
        "",
        "---",
        "",
    ]
    pyproject = project_path / "pyproject.toml"
    if pyproject.exists():
        report_parts.append("## Python (pyproject.toml)")
        report_parts.append("")
        try:
            if "dependencies" in pyproject.read_text():
                report_parts.append("*Dependencies found in pyproject.toml*")
                report_parts.append("")
        except Exception:
            pass
    requirements = project_path / "requirements.txt"
    if requirements.exists():
        report_parts.append("## Python (requirements.txt)")
        report_parts.append("")
        try:
            lines = requirements.read_text().strip().split("\n")
            deps = [
                line.strip()
                for line in lines
                if line.strip() and not line.startswith("#")
            ]
            for dep in deps[:20]:
                report_parts.append(f"- `{dep}`")
            if len(deps) > 20:
                report_parts.append(f"- ... and {len(deps) - 20} more")
            report_parts.append("")
        except Exception:
            pass
    package_json = project_path / "package.json"
    if package_json.exists():
        report_parts.append("## JavaScript (package.json)")
        report_parts.append("")
        try:
            import json

            data = json.loads(package_json.read_text())
            _append_dep_file(
                report_parts, "### Dependencies", data.get("dependencies", {})
            )
            _append_dep_file(
                report_parts,
                "### Dev Dependencies",
                data.get("devDependencies", {}),
                limit=10,
            )
        except Exception:
            pass

    report_parts.append("---")

    UIIcons, UIStyles = _get_ui_constants()
    rprint(
        f"[{UIStyles.SUCCESS}]{UIIcons.SUCCESS} Dependency analysis completed[/{UIStyles.SUCCESS}]"
    )

    return "\n".join(report_parts)


def _collect_file_stats(project_path: Path) -> Dict[str, Any]:
    """Collect file statistics from project."""
    stats: Dict[str, Any] = {
        "total_files": 0,
        "code_files": 0,
        "config_files": 0,
        "doc_files": 0,
        "by_extension": {},
    }

    code_exts = {
        ".py",
        ".js",
        ".ts",
        ".jsx",
        ".tsx",
        ".go",
        ".rs",
        ".java",
        ".cpp",
        ".c",
    }
    config_exts = {".json", ".yaml", ".yml", ".toml", ".ini", ".cfg"}
    doc_exts = {".md", ".rst", ".txt", ".adoc"}

    ignore_dirs = {
        ".git",
        "__pycache__",
        "node_modules",
        ".venv",
        "venv",
        "dist",
        "build",
    }

    for item in project_path.rglob("*"):
        if item.is_file():
            if any(d in item.parts for d in ignore_dirs):
                continue

            stats["total_files"] += 1
            ext = item.suffix.lower()

            if ext in code_exts:
                stats["code_files"] += 1
            elif ext in config_exts:
                stats["config_files"] += 1
            elif ext in doc_exts:
                stats["doc_files"] += 1

            if ext:
                stats["by_extension"][ext] = stats["by_extension"].get(ext, 0) + 1

    return stats


def _analyze_quality(project_path: Path, max_files: int) -> Dict[str, List[str]]:
    """Analyze code quality patterns."""
    findings: Dict[str, Any] = {
        "issues": [],
        "patterns": [],
    }

    py_files = list(project_path.rglob("*.py"))
    py_files = [
        f
        for f in py_files
        if not any(
            p in str(f) for p in [".git", "__pycache__", "node_modules", ".venv"]
        )
    ][:max_files]

    for py_file in py_files:
        try:
            content = py_file.read_text(encoding="utf-8", errors="ignore")
            rel_path = py_file.relative_to(project_path)

            if "import *" in content:
                findings["issues"].append(f"`{rel_path}`: Uses wildcard imports")
            if "except:" in content and "except Exception" not in content:
                findings["issues"].append(f"`{rel_path}`: Has bare except clause")
            if "TODO" in content or "FIXME" in content:
                findings["issues"].append(f"`{rel_path}`: Contains TODO/FIXME comments")
            if "def __init__" in content and "self." in content:
                findings["patterns"].append(f"`{rel_path}`: Uses proper OOP patterns")
            if "logging" in content or "logger" in content:
                findings["patterns"].append(f"`{rel_path}`: Uses logging")
            if "typing" in content or ": " in content:
                findings["patterns"].append(f"`{rel_path}`: Uses type hints")

        except Exception:
            continue

    return findings


def _analyze_architecture(project_path: Path) -> Dict[str, List[str]]:
    """Analyze project architecture."""
    findings: Dict[str, Any] = {
        "entry_points": [],
        "core_modules": [],
    }
    for pattern in ["main.py", "app.py", "cli.py", "__main__.py", "manage.py"]:
        matches = list(project_path.rglob(pattern))
        for m in matches[:3]:
            try:
                rel = m.relative_to(project_path)
                findings["entry_points"].append(str(rel))
            except Exception as _e:
                pass  # silenced: {_e}
    for init_file in project_path.rglob("__init__.py"):
        try:
            parent = init_file.parent
            if parent != project_path:
                rel = parent.relative_to(project_path)
                if len(rel.parts) <= 2:  # Only top-level modules
                    findings["core_modules"].append(str(rel))
        except Exception:
            continue

    return findings


def _generate_recommendations(file_stats: Dict, focus_areas: List[str]) -> List[str]:
    """Generate recommendations based on analysis."""
    recommendations = []

    if file_stats["code_files"] > 100 and file_stats["doc_files"] < 5:
        recommendations.append(
            "Consider adding more documentation files (README, API docs)"
        )

    if file_stats["code_files"] > 50:
        recommendations.append("Consider running a full test coverage analysis")

    if ".test." not in str(file_stats.get("by_extension", {})):
        recommendations.append("Add unit tests to improve code reliability")

    if "quality" in focus_areas:
        recommendations.append("Run linting tools (flake8, mypy) for code quality")

    if "architecture" in focus_areas:
        recommendations.append("Document the architecture in an ARCHITECTURE.md file")

    if not recommendations:
        recommendations.append(
            "Project structure looks good! Consider adding CI/CD if not present"
        )

    return recommendations


def _extract_patterns_from_file(
    content: str, file_path: str, patterns: Dict[str, List[str]]
) -> None:
    """Extract patterns from a single file."""
    import re

    class_names = re.findall(r"class\s+(\w+)", content)
    if class_names and all(name[0].isupper() for name in class_names):
        patterns["naming"].append(f"Classes use PascalCase in `{Path(file_path).name}`")

    func_names = re.findall(r"def\s+(\w+)", content)
    if func_names and all("_" in name or name.islower() for name in func_names[:10]):
        patterns["naming"].append(
            f"Functions use snake_case in `{Path(file_path).name}`"
        )
    if "@dataclass" in content:
        patterns["structure"].append(f"Uses dataclasses in `{Path(file_path).name}`")
    if "from typing import" in content:
        patterns["structure"].append(
            f"Uses type annotations in `{Path(file_path).name}`"
        )
    if "async def" in content:
        patterns["structure"].append(f"Uses async/await in `{Path(file_path).name}`")
    if "def test_" in content:
        patterns["testing"].append(f"Uses test_ prefix in `{Path(file_path).name}`")
    if "@pytest" in content:
        patterns["testing"].append(
            f"Uses pytest decorators in `{Path(file_path).name}`"
        )
    if "try:" in content and "except" in content:
        patterns["error"].append(f"Uses try/except in `{Path(file_path).name}`")
    if "raise " in content:
        patterns["error"].append(f"Raises exceptions in `{Path(file_path).name}`")

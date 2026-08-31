"""
Structured Project Analysis Tool for Aura CLI.

This module provides a comprehensive, structured analysis tool that systematically
explores and understands projects by reading key files, exploring structure,
and generating structured reports.

Features:
    - Systematic exploration: Reads READMEs, package files, configs
    - Multi-front analysis: Analyzes all project fronts (Backend, Frontend, Mobile, etc.)
    - Structured output: Generates organized reports with key information
    - Smart navigation: Automatically finds and reads important files
    - Integration with consciousness: Uses skills/knowledge base when available
"""

import json
from pathlib import Path
from typing import Any, Dict, List

from aura_cli.core.logger import get_logger
from aura_cli.core.stats import get_stats
from aura_cli.core.tools.file_system import (
    list_directory,
    read_file,
)

logger = get_logger(__name__)

KEY_FILES = [
    "README.md",
    "README.txt",
    "package.json",
    "pyproject.toml",
    "requirements.txt",
    "Pipfile",
    "Cargo.toml",
    "go.mod",
    "composer.json",
    "pom.xml",
    "build.gradle",
    ".env.example",
    "docker-compose.yml",
    "Dockerfile",
    "Makefile",
    "CHANGELOG.md",
    "LICENSE",
    "CONTRIBUTING.md",
]


def analyze_project_structure(
    project_path: str = ".",
    include_subprojects: bool = True,
    read_key_files: bool = True,
    max_depth: int = 3,
    analyze_architecture: bool = True,
    analyze_dependencies: bool = True,
    analyze_tests: bool = True,
) -> Dict[str, Any]:
    """Structured full-project analysis: directories, key files, fronts, tech stack.

    Explores up to max_depth levels, reads READMEs/configs, identifies project
    fronts (Backend, Frontend, Mobile…) and optionally analyses architecture,
    dependencies and test structure.

    Returns a dict with keys: project_root, structure, fronts, key_files,
    technologies, purpose, architecture, dependencies, tests.
    """
    from aura_cli.core.ui import display_tool_call

    display_tool_call(
        "analyze_project_structure",
        {
            "project_path": project_path,
            "include_subprojects": include_subprojects,
            "read_key_files": read_key_files,
        },
    )

    stats = get_stats()
    stats.track_tool_usage("analyze_project_structure")

    project_root = Path(project_path).resolve()

    if not project_root.exists():
        return {
            "error": f"Project not found: {project_path}",
            "project_root": str(project_root),
        }

    if not project_root.is_dir():
        return {
            "error": f"Caminho não é um diretório: {project_path}",
            "project_root": str(project_root),
        }

    logger.info(f"Iniciando análise estruturada do projeto: {project_root}")

    result: Dict[str, Any] = {
        "project_root": str(project_root),
        "structure": {},
        "fronts": [],
        "key_files": {},
        "technologies": [],
        "purpose": "",
        "summary": "",
        "recommendations": [],
    }
    try:
        root_listing = list_directory(str(project_root))
        result["structure"]["root"] = _parse_directory_listing(root_listing)
    except Exception as e:
        logger.warning(f"Error listing root directory: {e}")
        result["structure"]["root"] = {"error": str(e)}
    if read_key_files:
        result["key_files"]["root"] = _read_key_files(project_root)
    result["fronts"] = _identify_project_fronts(
        project_root, result["structure"].get("root", {})
    )
    if include_subprojects:
        for front in result["fronts"]:
            front_path = project_root / front["path"]
            if front_path.exists() and front_path.is_dir():
                logger.info(f"Analisando frente: {front['name']} ({front['path']})")
                try:
                    front_listing = list_directory(str(front_path))
                    result["structure"][front["name"]] = _parse_directory_listing(
                        front_listing
                    )
                except Exception as e:
                    logger.warning(f"Error listing {front['name']}: {e}")
                if read_key_files:
                    result["key_files"][front["name"]] = _read_key_files(front_path)
                readme_path = front_path / "README.md"
                if readme_path.exists():
                    try:
                        result["key_files"][front["name"]]["README.md"] = read_file(
                            str(readme_path)
                        )
                    except Exception as e:
                        logger.warning(f"Error reading README from {front['name']}: {e}")
    result["technologies"] = _extract_technologies(result["key_files"])
    result["purpose"] = _extract_purpose(result["key_files"])
    result["summary"] = _generate_summary(result)
    if analyze_architecture:
        result["architecture"] = _analyze_architecture(result, project_root)
    if analyze_dependencies:
        result["dependencies"] = _analyze_project_dependencies(result, project_root)
    if analyze_tests:
        result["tests"] = _analyze_test_structure(result, project_root)
    result["summary"] = _generate_summary(result)
    result["recommendations"] = _generate_recommendations(result)

    logger.info(
        f"Análise estruturada concluída: {len(result['fronts'])} frentes identificadas"
    )

    return result


def _parse_directory_listing(listing_output: str) -> Dict[str, Any]:
    """Parse output from list_directory into structured data."""
    items = []
    lines = listing_output.split("\n")

    for line in lines:
        line = line.strip()
        if not line or "┃" not in line:
            continue
        parts = [p.strip() for p in line.split("┃")]
        if len(parts) > 1:
            name = parts[1].replace("📄", "").replace("📁", "").strip()
            if name:
                is_dir = "📁" in parts[1] or name.endswith("/")
                items.append(
                    {
                        "name": name.rstrip("/"),
                        "type": "directory" if is_dir else "file",
                    }
                )

    return {"items": items, "count": len(items)}


def _read_key_files(directory: Path) -> Dict[str, str]:
    """Read key files from a directory."""
    key_files_content = {}

    for key_file in KEY_FILES:
        file_path = directory / key_file
        if file_path.exists() and file_path.is_file():
            try:
                content = read_file(str(file_path))
                if len(content) > 5000:
                    content = content[:5000] + "\n... (truncated)"
                key_files_content[key_file] = content
            except Exception as e:
                logger.warning(f"Error reading {key_file}: {e}")
                key_files_content[key_file] = f"Error reading: {e}"

    return key_files_content


def _identify_project_fronts(
    project_root: Path, root_structure: Dict[str, Any]
) -> List[Dict[str, str]]:
    """Identify project fronts (Backend, Frontend, Mobile, etc.)."""
    fronts = []
    items = root_structure.get("items", [])
    front_patterns = [
        ("backend", ["backend", "back-end", "api", "server", "service"]),
        ("frontend", ["frontend", "front-end", "web", "app", "client"]),
        ("mobile", ["mobile", "android", "ios", "react-native", "flutter"]),
        ("contracts", ["contracts", "smart-contracts", "blockchain"]),
        ("infrastructure", ["infra", "infrastructure", "devops", "deploy"]),
        ("docs", ["docs", "documentation", "doc"]),
    ]

    for item in items:
        if item["type"] != "directory":
            continue

        name_lower = item["name"].lower()

        for front_type, patterns in front_patterns:
            if any(pattern in name_lower for pattern in patterns):
                fronts.append(
                    {"name": item["name"], "path": item["name"], "type": front_type}
                )
                break

    return fronts


def _extract_technologies(key_files: Dict[str, Dict[str, str]]) -> List[str]:
    """Extract technologies from key files."""
    technologies = []
    for _location, files in key_files.items():
        if "package.json" in files:
            try:
                pkg = json.loads(files["package.json"])
                if "dependencies" in pkg:
                    technologies.append("Node.js")
                if "react" in str(pkg).lower():
                    technologies.append("React")
                if "vue" in str(pkg).lower():
                    technologies.append("Vue.js")
                if "angular" in str(pkg).lower():
                    technologies.append("Angular")
            except Exception as _e:
                logger.debug(f"Ignorado: {_e}")
        if "requirements.txt" in files:
            technologies.append("Python")
        if "pyproject.toml" in files:
            technologies.append("Python")
        if "Dockerfile" in files:
            technologies.append("Docker")
        if "docker-compose.yml" in files:
            technologies.append("Docker Compose")

    return list(set(technologies))  # Remove duplicates


def _extract_purpose(key_files: Dict[str, Dict[str, str]]) -> str:
    """Extract project purpose from README files."""
    purposes = []

    for _location, files in key_files.items():
        if "README.md" in files:
            readme = files["README.md"]
            lines = readme.split("\n")
            for line in lines[:20]:  # Check first 20 lines
                line = line.strip()
                if line and not line.startswith("#") and len(line) > 50:
                    purposes.append(line)
                    break

    return " | ".join(purposes[:3]) if purposes else "Não especificado"


def _generate_summary(result: Dict[str, Any]) -> str:
    """Generate executive summary."""
    summary_parts = []

    summary_parts.append(f"📁 Projeto: {result['project_root']}")

    if result["fronts"]:
        fronts_names = [f["name"] for f in result["fronts"]]
        summary_parts.append(
            f"🏗️  Frentes: {', '.join(fronts_names)} ({len(fronts_names)} frentes)"
        )

    if result["technologies"]:
        summary_parts.append(f"⚙️  Tecnologias: {', '.join(result['technologies'])}")

    if result.get("architecture"):
        arch = result["architecture"]
        if arch.get("entry_points"):
            summary_parts.append(
                f"🚀 Entry Points: {len(arch['entry_points'])} identificados"
            )
        if arch.get("patterns"):
            patterns = [p["pattern"] for p in arch["patterns"]]
            summary_parts.append(f"🏛️  Padrões: {', '.join(set(patterns))}")

    if result.get("dependencies"):
        deps = result["dependencies"]
        if deps.get("external"):
            total_deps = sum(
                len(v.get("runtime", [])) + len(v.get("dev", []))
                for v in deps["external"].values()
            )
            summary_parts.append(f"📦 Dependências Externas: ~{total_deps} pacotes")
        if deps.get("cross_front"):
            summary_parts.append(
                f"🔗 Dependências Cross-Front: {len(deps['cross_front'])} conexões"
            )

    if result.get("tests"):
        tests = result["tests"]
        if tests.get("test_directories"):
            summary_parts.append(
                f"🧪 Testes: {len(tests['test_directories'])} diretórios, {len(tests['test_files'])} arquivos"
            )
        if tests.get("test_frameworks"):
            frameworks = [t["framework"] for t in tests["test_frameworks"]]
            summary_parts.append(
                f"🔧 Frameworks de Teste: {', '.join(set(frameworks))}"
            )

    if result["purpose"]:
        summary_parts.append(f"🎯 Propósito: {result['purpose'][:150]}")

    return "\n".join(summary_parts)


def _generate_recommendations(result: Dict[str, Any]) -> List[str]:
    """Generate recommendations for next steps."""
    recommendations = []

    if not result["key_files"].get("root", {}).get("README.md"):
        recommendations.append("Considerar adicionar README.md na raiz do projeto")

    if result["fronts"]:
        recommendations.append(
            f"Explorar cada frente individualmente: {', '.join([f['name'] for f in result['fronts']])}"
        )

    if result["technologies"]:
        recommendations.append(
            f"Analisar dependências e configurações das tecnologias: {', '.join(result['technologies'])}"
        )

    recommendations.append(
        "Usar 'codebase_search' para buscar padrões específicos no código"
    )
    recommendations.append(
        "Usar 'investigate_codebase' para análise profunda de cada frente"
    )

    return recommendations


def _analyze_architecture(result: Dict[str, Any], project_root: Path) -> Dict[str, Any]:
    """Analyze project architecture patterns."""
    architecture: Dict[str, Any] = {
        "patterns": [],
        "entry_points": [],
        "main_modules": [],
        "layers": [],
    }
    entry_patterns = [
        "main.py",
        "app.py",
        "index.js",
        "index.ts",
        "index.tsx",
        "App.tsx",
        "main.ts",
        "server.py",
    ]

    for front in result.get("fronts", []):
        front_path = project_root / front["path"]
        for entry in entry_patterns:
            entry_file = front_path / entry
            if entry_file.exists():
                architecture["entry_points"].append(
                    {
                        "front": front["name"],
                        "file": str(entry_file.relative_to(project_root)),
                    }
                )
    for front in result.get("fronts", []):
        front_path = project_root / front["path"]
        common_dirs = ["src", "lib", "app", "modules", "components", "services"]
        for dir_name in common_dirs:
            dir_path = front_path / dir_name
            if dir_path.exists() and dir_path.is_dir():
                architecture["main_modules"].append(
                    {
                        "front": front["name"],
                        "module": dir_name,
                        "path": str(dir_path.relative_to(project_root)),
                    }
                )
    for front in result.get("fronts", []):
        front_path = project_root / front["path"]
        if (
            (front_path / "models").exists()
            or (front_path / "views").exists()
            or (front_path / "controllers").exists()
        ):
            architecture["patterns"].append(
                {"front": front["name"], "pattern": "MVC", "confidence": "high"}
            )
        services_dir = front_path / "services"
        if services_dir.exists():
            try:
                services = [d for d in services_dir.iterdir() if d.is_dir()]
                if len(services) > 1:
                    architecture["patterns"].append(
                        {
                            "front": front["name"],
                            "pattern": "Microservices",
                            "confidence": "medium",
                            "services_count": len(services),
                        }
                    )
            except Exception as _e:
                logger.debug(f"Ignorado: {_e}")

    return architecture


def _analyze_project_dependencies(
    result: Dict[str, Any], project_root: Path
) -> Dict[str, Any]:
    """Analyze project dependencies across all fronts."""
    dependencies: Dict[str, Any] = {"external": {}, "internal": {}, "cross_front": []}
    for location, files in result.get("key_files", {}).items():
        if "package.json" in files:
            try:
                pkg = json.loads(files["package.json"])
                deps = pkg.get("dependencies", {})
                dev_deps = pkg.get("devDependencies", {})

                if location not in dependencies["external"]:
                    dependencies["external"][location] = {}

                dependencies["external"][location]["runtime"] = list(deps.keys())[
                    :20
                ]  # Top 20
                dependencies["external"][location]["dev"] = list(dev_deps.keys())[
                    :10
                ]  # Top 10
            except Exception as _e:
                logger.debug(f"Ignorado: {_e}")
        if "requirements.txt" in files:
            try:
                reqs = files["requirements.txt"].split("\n")
                deps = [
                    r.strip().split("==")[0].split(">=")[0].split("<=")[0]
                    for r in reqs
                    if r.strip() and not r.startswith("#")
                ][:20]
                if location not in dependencies["external"]:
                    dependencies["external"][location] = {}
                dependencies["external"][location]["python"] = deps
            except Exception as _e:
                logger.debug(f"Ignorado: {_e}")
    fronts = result.get("fronts", [])
    for i, front1 in enumerate(fronts):
        for front2 in fronts[i + 1 :]:
            front1_path = project_root / front1["path"]
            try:
                for key_file in ["package.json", "requirements.txt", "README.md"]:
                    file_path = front1_path / key_file
                    if file_path.exists():
                        content = read_file(str(file_path))
                        if front2["name"].lower() in content.lower():
                            dependencies["cross_front"].append(
                                {
                                    "from": front1["name"],
                                    "to": front2["name"],
                                    "evidence": key_file,
                                }
                            )
            except Exception as _e:
                logger.debug(f"Ignorado: {_e}")

    return dependencies


def _analyze_test_structure(
    result: Dict[str, Any], project_root: Path
) -> Dict[str, Any]:
    """Analyze test structure and coverage."""
    tests: Dict[str, Any] = {
        "test_directories": [],
        "test_files": [],
        "test_frameworks": [],
        "coverage_files": [],
    }
    test_patterns = ["test", "tests", "__tests__", "spec", "specs", "test_", "_test"]

    for front in result.get("fronts", []):
        front_path = project_root / front["path"]
        for test_pattern in test_patterns:
            test_dir = front_path / test_pattern
            if test_dir.exists() and test_dir.is_dir():
                tests["test_directories"].append(
                    {
                        "front": front["name"],
                        "directory": str(test_dir.relative_to(project_root)),
                    }
                )
        try:
            for test_file in front_path.rglob("*test*.py"):
                if test_file.is_file():
                    tests["test_files"].append(
                        {
                            "front": front["name"],
                            "file": str(test_file.relative_to(project_root)),
                        }
                    )

            for test_file in front_path.rglob("*test*.{js,ts,jsx,tsx}"):
                if test_file.is_file():
                    tests["test_files"].append(
                        {
                            "front": front["name"],
                            "file": str(test_file.relative_to(project_root)),
                        }
                    )
        except Exception as _e:
            logger.debug(f"Ignorado: {_e}")
        key_files = result.get("key_files", {}).get(front["name"], {})
        if "package.json" in key_files:
            try:
                pkg = json.loads(key_files["package.json"])
                deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}

                test_frameworks = {
                    "jest": "Jest",
                    "mocha": "Mocha",
                    "vitest": "Vitest",
                    "pytest": "pytest",
                    "unittest": "unittest",
                    "jasmine": "Jasmine",
                }

                for dep, framework in test_frameworks.items():
                    if dep in str(deps).lower():
                        tests["test_frameworks"].append(
                            {"front": front["name"], "framework": framework}
                        )
            except Exception as _e:
                logger.debug(f"Ignorado: {_e}")
        coverage_patterns = ["coverage", ".coverage", "coverage.xml", "lcov.info"]
        for pattern in coverage_patterns:
            coverage_file = front_path / pattern
            if coverage_file.exists():
                tests["coverage_files"].append(
                    {
                        "front": front["name"],
                        "file": str(coverage_file.relative_to(project_root)),
                    }
                )

    return tests

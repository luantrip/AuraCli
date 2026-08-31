"""
Codebase Analysis Module for Aura CLI.

This module contains the main functions for the `codebase_investigator` tool.
It handles file system traversal, filtering, static analysis,
symbol extraction and dependency mapping.

Enhanced with Imagination Engine for ultra-fast initial scanning.

Note: CodebaseIndex is defined here (inline) because it is used exclusively
by investigate_codebase(). The original codebase_index.py was removed —
this is the single authoritative copy.
"""

import re
from typing import Any, Dict, List, Optional

from aura_cli.core.logger import get_logger

logger = get_logger(__name__)


# CodebaseIndex — inline (moved from context/codebase_index.py)
# Sole consumer: investigate_codebase() in this module.


class CodebaseIndex:
    """Lightweight text index for codebase search (dict-based, in-memory)."""

    def __init__(self):
        self.text_index: Dict[str, List[Dict[str, Any]]] = {}
        self.file_index: Dict[str, Dict[str, Any]] = {}
        self.symbol_index: Dict[str, List[Dict[str, Any]]] = {}

    def index_file(
        self,
        file_path: str,
        content: str,
        symbols: Optional[Dict[str, List[str]]] = None,
    ):
        words = self._tokenize(content)
        for word in words:
            wl = word.lower()
            self.text_index.setdefault(wl, []).append({"file": file_path, "word": word})
        self.file_index[file_path] = {
            "path": file_path,
            "content_length": len(content),
            "word_count": len(words),
            "symbols": symbols or {},
        }
        if symbols:
            for sym_type, sym_list in symbols.items():
                for sym_name in sym_list:
                    self.symbol_index.setdefault(sym_name.lower(), []).append(
                        {"name": sym_name, "type": sym_type, "file": file_path}
                    )

    def get_stats(self) -> Dict[str, int]:
        return {
            "indexed_files": len(self.file_index),
            "unique_words": len(self.text_index),
            "total_symbols": sum(len(v) for v in self.symbol_index.values()),
        }

    def _tokenize(self, text: str) -> List[str]:
        return re.findall(r"\b\w+\b", text)


# Re-exports from codebase_traversal
from aura_cli.core.tools.codebase_traversal import (
    IMAGINATION_AVAILABLE,
    quick_scan_with_imagination,
    traverse_and_filter_codebase,
)

# --- Re-exports from python_analyzer ---
from aura_cli.core.tools.python_analyzer import (
    CodeGraph,
    analyze_python_ast,
)


def investigate_codebase(
    root_path: str,
    objective: Optional[str] = None,
    include_extensions: Optional[List[str]] = None,
    max_files: int = 100,
    verbose: bool = False,
    respect_gitignore: bool = True,
    use_imagination: bool = True,
) -> Dict[str, Any]:
    """Deep, structured analysis of an entire codebase directory.

    Use for full-project understanding. For single files use read_file;
    for quick text search use codebase_search; for directory listing use
    list_directory.

    Pipeline: optional Imagination Engine quick-scan → file traversal →
    Python AST analysis → symbol/dependency extraction → indexed report.

    Returns dict with: summary, structure, symbols, dependencies,
    files_analyzed, recommendations.
    """
    from aura_cli.core.context import CodebaseContextManager

    logger.info(f"Iniciando investigação do codebase: {root_path}")
    if objective:
        logger.info(f"Objetivo: {objective}")

    context_manager = CodebaseContextManager(root_path)
    index = CodebaseIndex()

    context_manager.start_analysis()
    imagination_data = None
    if use_imagination and IMAGINATION_AVAILABLE:
        logger.info("Etapa 0: Quick scan com Imagination Engine")
        imagination_data = quick_scan_with_imagination(root_path, include_extensions)
        if imagination_data:
            logger.info(
                f"Imagination Engine: {imagination_data['total_files']} arquivos, "
                f"{imagination_data['total_lines']:,} linhas em {imagination_data['scan_duration_ms']}ms"
            )
            context_manager.metadata["imagination_scan"] = imagination_data

    logger.info("Step 1: File traversal and filtering")

    if include_extensions is None:
        include_extensions = [".py"]

    files_found = list(
        traverse_and_filter_codebase(
            root_path=root_path,
            include_extensions=include_extensions,
            respect_gitignore=respect_gitignore,
            max_depth=-1,
        )
    )

    logger.info(f"Found {len(files_found)} files")

    files_to_analyze = files_found[:max_files]
    if len(files_found) > max_files:
        logger.warning(
            f"Limitando análise a {max_files} arquivos (de {len(files_found)} encontrados)"
        )

    logger.info("Etapa 2: Análise AST e extração de símbolos")

    analyzed_count = 0
    error_count = 0

    for file_info in files_to_analyze:
        file_path = file_info["full_path"]
        relative_path = file_info["path"]

        try:
            with open(file_path, encoding="utf-8") as f:
                content = f.read()

            line_count = content.count("\n") + 1
            context_manager.metadata["total_lines"] += line_count

            ast_data = {}
            if file_info["extension"] == ".py":
                ast_data = analyze_python_ast(content)

                if "error" not in ast_data:
                    context_manager.store_file_analysis(relative_path, ast_data)

                    index.index_file(relative_path, content, ast_data)

                    analyzed_count += 1

                    if verbose:
                        logger.info(f"✓ Analisado: {relative_path}")
                else:
                    error_count += 1
                    if verbose:
                        logger.warning(f"✗ Erro de sintaxe: {relative_path}")
            else:
                index.index_file(relative_path, content, None)
                analyzed_count += 1

        except Exception as e:
            error_count += 1
            logger.error(f"Error analyzing {relative_path}: {e}")

    context_manager.end_analysis()

    summary = context_manager.get_summary()
    summary["files_found"] = len(files_found)
    summary["files_processed"] = analyzed_count
    summary["errors"] = error_count
    summary["index_stats"] = index.get_stats()

    logger.info(
        f"Análise concluída: {analyzed_count} arquivos processados, {error_count} erros"
    )

    result = {
        "success": True,
        "summary": summary,
        "context_manager": context_manager,
        "index": index,
        "objective": objective,
    }
    if imagination_data:
        result["imagination_scan"] = imagination_data
        logger.info(
            f"Imagination Engine data included: {imagination_data['files_matching_filter']} "
            f"files matching filter, scanned in {imagination_data['scan_duration_ms']}ms"
        )

    return result


def investigate_codebase_deep(
    root_path: str,
    include_extensions: Optional[List[str]] = None,
    max_files: int = 200,
    respect_gitignore: bool = True,
) -> Dict[str, Any]:
    """
    Deep codebase analysis with full CodeGraph construction.

    This is a more thorough version that builds the dependency graph
    and provides advanced querying capabilities.

    Args:
        root_path: Root path to analyze
        include_extensions: File extensions to include
        max_files: Maximum files to analyze
        respect_gitignore: Whether to respect .gitignore

    Returns:
        Dictionary with analysis results including CodeGraph
    """
    logger.info(f"Iniciando análise profunda do codebase: {root_path}")

    code_graph = CodeGraph()

    imagination_data = None
    if IMAGINATION_AVAILABLE:
        imagination_data = quick_scan_with_imagination(root_path, include_extensions)

    if include_extensions is None:
        include_extensions = [".py"]

    files_found = list(
        traverse_and_filter_codebase(
            root_path=root_path,
            include_extensions=include_extensions,
            respect_gitignore=respect_gitignore,
            max_depth=-1,
        )
    )[:max_files]

    analyzed_count = 0
    error_count = 0
    all_metrics = []

    for file_info in files_found:
        file_path = file_info["full_path"]
        relative_path = file_info["path"]

        try:
            with open(file_path, encoding="utf-8") as f:
                content = f.read()

            if file_info["extension"] == ".py":
                ast_data = analyze_python_ast(content, detailed=True)

                if "error" not in ast_data:
                    code_graph.add_file(relative_path, ast_data)
                    all_metrics.append(
                        {
                            "file": relative_path,
                            "metrics": ast_data.get("metrics", {}),
                        }
                    )
                    analyzed_count += 1
                else:
                    error_count += 1
        except Exception as e:
            error_count += 1
            logger.error(f"Error analyzing {relative_path}: {e}")

    code_graph.resolve_edges()

    total_functions = sum(m["metrics"].get("total_functions", 0) for m in all_metrics)
    total_classes = sum(m["metrics"].get("total_classes", 0) for m in all_metrics)
    total_complexity = sum(m["metrics"].get("total_complexity", 0) for m in all_metrics)
    documented_funcs = sum(
        m["metrics"].get("documented_functions", 0) for m in all_metrics
    )
    documented_classes = sum(
        m["metrics"].get("documented_classes", 0) for m in all_metrics
    )

    return {
        "success": True,
        "code_graph": code_graph,
        "graph_stats": code_graph.get_statistics(),
        "files_analyzed": analyzed_count,
        "errors": error_count,
        "imagination_scan": imagination_data,
        "aggregate_metrics": {
            "total_functions": total_functions,
            "total_classes": total_classes,
            "total_complexity": total_complexity,
            "avg_complexity": round(total_complexity / max(total_functions, 1), 2),
            "documentation_coverage": {
                "functions": round(documented_funcs / max(total_functions, 1) * 100, 1),
                "classes": round(documented_classes / max(total_classes, 1) * 100, 1),
            },
            "high_complexity_functions": code_graph.get_high_complexity_functions(10),
        },
        "file_metrics": all_metrics,
    }


def _insights_callers(code_graph, question, result):
    words = question.split()
    for i, word in enumerate(words):
        if word.lower() in ("calls", "uses", "chama", "usa") and i + 1 < len(words):
            func_name = words[i + 1].strip("?.,")
            callers = code_graph.find_callers(func_name)
            result["answer"] = f"Found {len(callers)} callers of '{func_name}'"
            result["data"] = callers
            break


def _insights_callees(code_graph, question, result):
    words = question.split()
    for i, word in enumerate(words):
        if word.lower() in ("does", "faz") and i + 1 < len(words):
            func_name = words[i + 1].strip("?.,")
            callees = code_graph.find_callees(func_name)
            result["answer"] = f"'{func_name}' calls {len(callees)} functions"
            result["data"] = callees
            break


def _insights_subclasses(code_graph, question, result):
    for word in question.split():
        clean_word = word.strip("?.,")
        if clean_word and clean_word[0].isupper():
            subclasses = code_graph.find_subclasses(clean_word)
            if subclasses:
                result["answer"] = (
                    f"Found {len(subclasses)} subclasses of '{clean_word}'"
                )
                result["data"] = subclasses
                break


def _insights_where(code_graph, question, result):
    words = question.split()
    search_term = None
    for i, word in enumerate(words):
        if word.lower() in ("is", "find", "está", "definido"):
            if i + 1 < len(words):
                search_term = words[i + 1].strip("?.,")
                break
        elif i == len(words) - 1:
            search_term = word.strip("?.,")
    if search_term:
        matches = [
            {
                "name": nd["name"],
                "type": nd["type"],
                "file": nd["file"],
                "line": nd.get("line"),
                "docstring": nd.get("docstring", "")[:100]
                if nd.get("docstring")
                else None,
            }
            for nd in code_graph.nodes.values()
            if search_term.lower() in nd["name"].lower()
        ]
        result["answer"] = f"Found {len(matches)} definitions matching '{search_term}'"
        result["data"] = matches


def _insights_impact(code_graph, question, result):
    for word in question.split():
        clean_word = word.strip("?.,")
        if len(clean_word) > 2:
            impact = code_graph.get_impact_analysis(clean_word)
            if impact["direct"] or impact["indirect"]:
                result["answer"] = (
                    f"Changing '{clean_word}' would affect {len(impact['direct'])} direct and {len(impact['indirect'])} indirect callers"
                )
                result["data"] = impact
                break


def _insights_fallback(code_graph, question, result):
    potential_symbols = re.findall(r"\b[A-Z][a-zA-Z_]+\b", question)
    if potential_symbols:
        all_usages = {
            sym: usages
            for sym in potential_symbols
            for usages in [code_graph.find_usages(sym)]
            if any(usages.values())
        }
        if all_usages:
            result["answer"] = f"Found usages for {len(all_usages)} symbols"
            result["data"] = all_usages
            return
    result["answer"] = (
        "No specific matches found. Try asking about: function calls, class inheritance, complexity, or symbol definitions."
    )
    result["suggestions"] = [
        "What functions call X?",
        "What inherits from BaseClass?",
        "What is the most complex function?",
        "Where is MyFunction defined?",
        "Impact of changing X?",
    ]


def get_code_insights(
    root_path: str,
    question: str,
    max_files: int = 100,
) -> Dict[str, Any]:
    """
    Answer questions about the codebase using deep analysis.

    Supports questions like:
    - "What functions call X?"
    - "What classes inherit from Y?"
    - "What is the most complex function?"
    - "Where is Z defined?"
    - "What does function X do?"
    - "What are the dependencies of module X?"

    Args:
        root_path: Root path of the codebase
        question: Natural language question about the code
        max_files: Maximum files to analyze

    Returns:
        Dictionary with answer and supporting data
    """
    logger.info(f"Respondendo pergunta sobre o codebase: {question}")

    question_lower = question.lower()
    analysis = investigate_codebase_deep(root_path, max_files=max_files)
    code_graph = analysis["code_graph"]

    result: Dict[str, Any] = {
        "question": question,
        "answer": None,
        "data": None,
        "suggestions": [],
    }

    _DISPATCH = [
        (
            [
                "what calls",
                "who calls",
                "who uses",
                "what uses",
                "quem chama",
                "o que chama",
            ],
            _insights_callers,
        ),
        (
            ["what does", "what functions does", "o que", "quais funções"],
            _insights_callees,
        ),
        (["inherit", "subclass", "herda", "estende"], _insights_subclasses),
        (
            [
                "most complex",
                "highest complexity",
                "mais complexa",
                "maior complexidade",
            ],
            "complexity",
        ),
        (["where is", "find", "onde está", "encontre", "definido"], _insights_where),
        (["impact", "break", "affect", "impacto", "afeta"], _insights_impact),
        (
            [
                "statistic",
                "overview",
                "summary",
                "estatística",
                "resumo",
                "visão geral",
            ],
            "stats",
        ),
    ]

    for phrases, handler in _DISPATCH:
        if any(p in question_lower for p in phrases):
            if handler == "complexity":
                high_complexity = code_graph.get_high_complexity_functions(threshold=5)[
                    :10
                ]
                result["answer"] = f"Top {len(high_complexity)} most complex functions"
                result["data"] = high_complexity
            elif handler == "stats":
                result["answer"] = "Codebase statistics"
                result["data"] = {
                    "graph_stats": analysis["graph_stats"],
                    "aggregate_metrics": analysis["aggregate_metrics"],
                    "files_analyzed": analysis["files_analyzed"],
                }
            else:
                handler(code_graph, question, result)  # type: ignore[operator]
            return result

    _insights_fallback(code_graph, question, result)
    return result

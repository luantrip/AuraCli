"""
Web Search Tool for Aura CLI.

This module provides web search functionality using DuckDuckGo (primary)
with fallback to Google, allowing agents to search for updated information.
Results are cached to avoid repeated requests.

Features:
    - DuckDuckGo Search: Primary backend via ddgs package (reliable, no blocking)
    - Google Fallback: Falls back to googlesearch-python if ddgs unavailable
    - Formatted Results: Returns formatted results with title, link and description
    - Smart Cache: Caches successful results for 1 hour (empty results are NOT cached)
    - Error Handling: Handles errors gracefully and returns descriptive messages

Usage:
    >>> from aura_cli.core.tools.web import web_search
    >>> results = web_search("Python async programming", num_results=5)
"""

import time

# Primary: ddgs (DuckDuckGo)
try:
    from ddgs import DDGS

    _ddgs_available = True
except ImportError:
    _ddgs_available = False

# Fallback: googlesearch-python
try:
    from googlesearch import search as google_search
except ImportError:
    google_search = None

from rich.console import Console

from aura_cli.application.tools.web_search_policy import (
    format_web_search_results,
    normalize_web_search_request,
)

# Manual cache: only stores non-empty (successful) results
_web_search_cache: dict[str, tuple[float, str]] = {}


def _search_ddgs(query: str, num_results: int) -> list[dict]:
    """Search using DuckDuckGo via ddgs package."""
    ddgs = DDGS()
    results = ddgs.text(query, max_results=num_results)
    return [
        {
            "title": r.get("title", ""),
            "url": r.get("href", ""),
            "description": r.get("body", ""),
        }
        for r in results
    ]


def _search_google(query: str, num_results: int) -> list[dict]:
    """Search using Google via googlesearch-python (legacy fallback)."""
    if google_search is None:
        return []
    raw_results = list(google_search(query, num_results=num_results, advanced=True))
    return [
        {
            "title": getattr(r, "title", ""),
            "url": getattr(r, "url", ""),
            "description": getattr(r, "description", ""),
        }
        for r in raw_results
    ]


def web_search(query: str, num_results: int = 5) -> str:
    """
    Performs a web search and returns the top results.

    Uses DuckDuckGo as primary backend (reliable, no blocking).
    Falls back to Google if ddgs is unavailable.
    Only successful (non-empty) results are cached for 1 hour.

    Args:
        query (str): The term to search for.
        num_results (int): Number of results to return. Default is 5.
    Returns:
        str: Formatted string with titles, links, and descriptions.
    """
    from aura_cli.core.ui import display_tool_call
    from aura_cli.core.ui_bridge import UIStyles

    display_tool_call("web_search", {"query": query, "num_results": num_results})

    try:
        request = normalize_web_search_request(query, num_results)
    except ValueError as error:
        return f"Erro: {error}"

    if not _ddgs_available and google_search is None:
        return "Erro: nenhum pacote de busca disponível. Instale com: pip install ddgs"

    # Check cache for previously successful results
    cache_key = request.cache_key
    if cache_key in _web_search_cache:
        cached_time, cached_result = _web_search_cache[cache_key]
        if time.time() - cached_time < 3600:
            return cached_result
        else:
            del _web_search_cache[cache_key]

    try:
        warning_style = UIStyles.safe_style("WARNING", "yellow")
        console = Console()
        console.print(
            f"[{warning_style}]Pesquisando na web por: '{request.query}'...[/{warning_style}]"
        )

        # Try DuckDuckGo first, then Google
        search_results = []
        if _ddgs_available:
            search_results = _search_ddgs(request.query, request.num_results)

        if not search_results and google_search is not None:
            search_results = _search_google(request.query, request.num_results)

        if not search_results:
            return "Nenhum resultado encontrado para a pesquisa."

        formatted_result = format_web_search_results(search_results)

        success_msg = (
            f"Pesquisa concluída. Encontrados {len(search_results)} resultados."
        )
        console.print(f"[green]… {success_msg}[/green]")

        # Only cache non-empty successful results
        _web_search_cache[cache_key] = (time.time(), formatted_result)

        return formatted_result
    except Exception as e:
        console = Console()
        error_msg = f"Ocorreu um erro ao pesquisar na web: {e}"
        console.print(f"[red]{error_msg}[/red]")
        return error_msg

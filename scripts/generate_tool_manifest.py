#!/usr/bin/env python3
"""Generate the lightweight tool manifest from the canonical discovery engine."""

from __future__ import annotations

import ast
import os
from pathlib import Path
from pprint import pformat
import sys
from typing import Any

# Tool discovery imports provider modules for reflection. Force LiteLLM to use its
# bundled cost map so this deterministic build step never performs network I/O.
os.environ.setdefault("LITELLM_LOCAL_MODEL_COST_MAP", "True")

from aura_cli.core.llm.tool_schemas import extract_function_schema

try:
    from scripts.tool_discovery import CoreToolDiscovery
except ModuleNotFoundError:
    from tool_discovery import CoreToolDiscovery

# Classification is deliberately conservative: an unreviewed tool is mutating and
# never cacheable. Expanding this set requires checking the implementation for
# filesystem, process, network and global-state side effects.
READ_ONLY_TOOLS = {
    "advanced_grep_search",
    "analyze_code",
    "analyze_dependencies",
    "analyze_project_documentation",
    "analyze_project_quality",
    "analyze_project_security",
    "analyze_project_structure",
    "check_file_changes",
    "check_port",
    "classify_code",
    "codebase_search",
    "compare_project_fronts",
    "dep_analyze_import_graph",
    "dep_find_dependencies",
    "dep_find_dependents",
    "diff_checkpoint",
    "discover_patterns",
    "docker_images",
    "docker_logs",
    "docker_ps",
    "extract_commit_message",
    "find_duplicate_code",
    "find_in_files",
    "get_context_usage",
    "gh_get_workflow_status",
    "gh_list_workflows",
    "git_diff",
    "git_diff_context",
    "git_log",
    "git_status",
    "glob_search",
    "inspect_code_structure",
    "list_checkpoints",
    "list_directory",
    "notebook_list",
    "notebook_read",
    "notebook_search",
    "process_info",
    "read_file",
    "scan_project",
    "summarize_code",
    "system_resources",
    "tokenize_code",
    "tree_view",
    "validate_syntax",
    "view_repo_map",
    "view_subdirectory",
}


class _ManifestCollector:
    def __init__(self) -> None:
        self.entries: list[dict[str, Any]] = []

    def _register_tool(self, name, category, description, function, schema) -> None:
        resolved_schema = schema or extract_function_schema(function)
        if "function" not in resolved_schema:
            resolved_schema = {
                "type": "function",
                "function": {
                    "name": name,
                    "description": description,
                    "parameters": resolved_schema,
                },
            }
        resolved_schema["function"]["name"] = name
        self.entries.append(
            {
                "name": name,
                "category": category.value,
                "description": description,
                "effect": "read_only" if name in READ_ONLY_TOOLS else "mutating",
                "cacheable": False,
                "module": function.__module__,
                "qualname": function.__qualname__,
                "schema": resolved_schema,
            }
        )


def generate_content() -> str:
    collector = _ManifestCollector()
    CoreToolDiscovery().register_all(collector)
    entries = sorted(collector.entries, key=lambda item: item["name"])
    return (
        '"""Generated tool metadata. Run scripts/generate_tool_manifest.py to update."""\n\n'
        "from typing import Any, Final\n\n"
        f"TOOL_MANIFEST: Final[list[dict[str, Any]]] = {pformat(entries, width=100, sort_dicts=False)}\n"
    )


def main(*, check: bool = False) -> int:
    target = Path(__file__).resolve().parents[1] / "aura_cli/core/tool_manifest.py"
    content = generate_content()
    if check:
        current = target.read_text(encoding="utf-8")
        # Ruff may normalize quotes and wrap the generated literal. Compare the
        # Python syntax tree so formatting alone never marks the manifest stale.
        if ast.dump(ast.parse(current)) != ast.dump(ast.parse(content)):
            print(f"Tool manifest is stale: {target}")
            return 1
        print(f"Tool manifest is current: {target}")
        return 0
    target.write_text(content, encoding="utf-8")
    print(f"Wrote tool manifest to {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(check="--check" in sys.argv[1:]))

"""Tool schemas for LiteLLM function calling — auto-extraction from Python functions.

Converts Python function signatures and docstrings to OpenAI-compatible
function schemas. Works uniformly across LiteLLM, Gemini and other providers.

NOTE: Nim tools (scan_project, browse_content, etc.) are sent to all providers
including Gemini. Failures surface as error payloads (ok: false) at call time —
there is no per-provider tool filtering.
"""

import inspect
from typing import (
    Any,
    Callable,
    Dict,
    List,
    Optional,
    Tuple,
)

_PY_TO_JSON_TYPE: dict = {
    int: "integer",
    float: "number",
    bool: "boolean",
    list: "array",
    List: "array",
    dict: "object",
    Dict: "object",
}


def _json_type_for(annotation: Any) -> str:
    return _PY_TO_JSON_TYPE.get(annotation, "string")


def _param_desc_from_doc(doc: str, param_name: str) -> str | None:
    """Extract parameter description from a Google-style docstring."""
    in_args = False
    for line in doc.split("\n"):
        if "Args:" in line or "Parameters:" in line:
            in_args = True
            continue
        if in_args:
            if line.strip().startswith(f"{param_name}:"):
                desc = line.split(":", 1)[1].strip()
                return desc or None
            if line.strip() and not line.startswith(" ") and ":" in line:
                break
    return None


def extract_function_schema(func: Callable) -> Dict[str, Any]:
    """Extract a JSON schema from a function signature."""
    sig = inspect.signature(func)

    doc = func.__doc__ or f"Ferramenta: {func.__name__}"
    description = doc.strip().split("\n")[0]

    properties = {}
    required = []

    for param_name, param in sig.parameters.items():
        if param_name in ["self", "cls"] or param.kind in [
            inspect.Parameter.VAR_POSITIONAL,
            inspect.Parameter.VAR_KEYWORD,
        ]:
            continue

        param_type = "string"
        if param.annotation is not inspect.Parameter.empty:
            param_type = _json_type_for(param.annotation)

        param_description = _param_desc_from_doc(doc, param_name) if doc else None
        param_description = param_description or f"Parâmetro {param_name}"

        param_schema: Dict[str, Any] = {
            "type": param_type,
            "description": param_description,
        }

        if param_type == "array":
            param_schema["items"] = {"type": "string"}

        properties[param_name] = param_schema

        if param.default is inspect.Parameter.empty:
            required.append(param_name)

    schema = {
        "type": "function",
        "function": {
            "name": func.__name__,
            "description": description,
            "parameters": {
                "type": "object",
                "properties": properties,
                "required": required,
            },
        },
    }

    return schema


def create_tool_schemas(tools: Dict[str, Callable]) -> List[Dict[str, Any]]:
    """Create tool schemas for a list of functions."""
    EXCLUDED_FUNCTIONS = {
        "dataclass",
        "field",
        "get_logger",
        "get_stats",
        "get_impact_analysis",
        "type",
        "str",
        "int",
        "float",
        "bool",
        "list",
        "dict",
        "tuple",
        "set",
        "frozenset",
        "print",
        "len",
        "range",
        "enumerate",
        "zip",
        "map",
        "filter",
        "sorted",
        "reversed",
        "iter",
        "next",
        "hash",
        "id",
        "isinstance",
        "issubclass",
        "hasattr",
        "getattr",
        "setattr",
        "delattr",
        "callable",
        "eval",
        "exec",
        "compile",
        "open",
        "input",
        "raw_input",
        "__import__",
        "globals",
        "locals",
        "vars",
        "dir",
        "help",
        "copyright",
        "credits",
        "license",
        "exit",
        "quit",
        "abs",
        "all",
        "any",
        "ascii",
        "bin",
        "bytearray",
        "bytes",
        "chr",
        "classmethod",
        "complex",
        "divmod",
        "format",
        "hex",
        "max",
        "memoryview",
        "min",
        "object",
        "oct",
        "ord",
        "pow",
        "property",
        "repr",
        "round",
        "slice",
        "staticmethod",
        "sum",
        "super",
        "__build_class__",
        "__name__",
        "__doc__",
        "__package__",
        "__loader__",
        "__spec__",
        "__annotations__",
        "__dict__",
        "__file__",
        "__cached__",
        "__path__",
        "__all__",
        "__version__",
        "__author__",
        "__credits__",
        "__license__",
        "__main__",
        "__builtins__",
        "__builtin__",
    }

    schemas = []
    seen_names = set()

    for name, func in tools.items():
        if name in EXCLUDED_FUNCTIONS:
            continue

        if name in seen_names:
            continue

        if not callable(func):
            continue

        if hasattr(func, "__module__") and func.__module__ == "builtins":
            continue

        try:
            stored_schema = getattr(func, "__tool_schema__", None)
            schema = (
                stored_schema.copy()
                if isinstance(stored_schema, dict)
                else extract_function_schema(func)
            )
            if isinstance(schema.get("function"), dict):
                schema["function"] = schema["function"].copy()
            # Override schema name with the dict key so that the LLM calls the
            # exact name that exists in available_tools (e.g. "dep_find_dependencies"
            # instead of the raw func.__name__ "find_dependencies").
            schema["function"]["name"] = name

            if name in seen_names:
                continue

            seen_names.add(name)
            schemas.append(schema)
        except Exception:
            continue

    return schemas


##############################################################################
# T3.3 — Tool Schema Filtering by Task Type
##############################################################################

# Mapping from TaskType values to the tool names relevant for each category.
# Tools listed here are the *only* ones sent to the LLM for that task type,
# dramatically reducing prompt token usage (~7500 → ~1500-2500 tokens).

_TASK_TOOL_MAP: Dict[str, frozenset] = {
    # Code editing / generation: fs + edit + code analysis + search
    "code_edit": frozenset(
        {
            "read_file",
            "write_file",
            "list_directory",
            "edit_file",
            "tree_view",
            "find_in_files",
            "glob_search",
            "advanced_grep_search",
            "codebase_search",
            "view_repo_map",
            "view_subdirectory",
            "analyze_code",
            "validate_syntax",
            "classify_code",
            "summarize_code",
            "find_duplicate_code",
            "investigate_codebase",
            "inspect_code_structure",
            "backup_file",
            "restore_backup",
            "format_file",
            "sanitize_code",
            "run_shell_command",
            "check_file_changes",
        }
    ),
    "code_review": frozenset(
        {
            "read_file",
            "list_directory",
            "tree_view",
            "find_in_files",
            "glob_search",
            "advanced_grep_search",
            "codebase_search",
            "view_repo_map",
            "view_subdirectory",
            "analyze_code",
            "validate_syntax",
            "classify_code",
            "summarize_code",
            "find_duplicate_code",
            "investigate_codebase",
            "inspect_code_structure",
            "analyze_project_structure",
            "analyze_project_quality",
            "analyze_project_security",
            "deep_project_analysis",
            "discover_patterns",
            "git_diff",
            "git_log",
        }
    ),
    "test_gen": frozenset(
        {
            "read_file",
            "write_file",
            "list_directory",
            "edit_file",
            "tree_view",
            "find_in_files",
            "glob_search",
            "advanced_grep_search",
            "codebase_search",
            "view_repo_map",
            "analyze_code",
            "validate_syntax",
            "generate_tests_ml",
            "run_tests_advanced",
            "discover_tests",
            "run_test_file",
            "run_shell_command",
            "backup_file",
            "inspect_code_structure",
        }
    ),
    # DevOps / ops: git + docker + shell + monitoring + fs
    "shell_command": frozenset(
        {
            "run_shell_command",
            "read_file",
            "write_file",
            "list_directory",
            "tree_view",
            "find_in_files",
            "glob_search",
            "system_resources",
            "check_port",
            "process_info",
        }
    ),
    "git_operation": frozenset(
        {
            "git_status",
            "git_commit",
            "git_diff",
            "git_diff_context",
            "git_log",
            "git_branch",
            "suggest_commit_message",
            "extract_commit_message",
            "parse_natural_git_command",
            "read_file",
            "list_directory",
            "tree_view",
            "find_in_files",
            "run_shell_command",
            "check_file_changes",
        }
    ),
    # Analysis / questions: minimal read-only tools
    "quick_question": frozenset(
        {
            "read_file",
            "write_file",
            "edit_file",
            "list_directory",
            "tree_view",
            "find_in_files",
            "glob_search",
            "advanced_grep_search",
            "codebase_search",
            "view_repo_map",
            "view_subdirectory",
            "web_search",
            "run_shell_command",
        }
    ),
    "architecture": frozenset(
        {
            "read_file",
            "list_directory",
            "tree_view",
            "find_in_files",
            "glob_search",
            "advanced_grep_search",
            "codebase_search",
            "view_repo_map",
            "view_subdirectory",
            "analyze_code",
            "analyze_project_structure",
            "investigate_codebase",
            "inspect_code_structure",
            "deep_project_analysis",
            "discover_patterns",
            "plan_refactoring",
            "web_search",
        }
    ),
    "documentation": frozenset(
        {
            "read_file",
            "write_file",
            "list_directory",
            "edit_file",
            "tree_view",
            "find_in_files",
            "glob_search",
            "codebase_search",
            "view_repo_map",
            "view_subdirectory",
            "analyze_code",
            "summarize_code",
            "web_search",
            "run_shell_command",
        }
    ),
    "file_operation": frozenset(
        {
            "read_file",
            "write_file",
            "list_directory",
            "edit_file",
            "tree_view",
            "find_in_files",
            "glob_search",
            "advanced_grep_search",
            "codebase_search",
            "view_repo_map",
            "view_subdirectory",
            "backup_file",
            "restore_backup",
            "run_shell_command",
            "check_file_changes",
        }
    ),
    "debug": frozenset(
        {
            "read_file",
            "write_file",
            "list_directory",
            "edit_file",
            "tree_view",
            "find_in_files",
            "glob_search",
            "advanced_grep_search",
            "codebase_search",
            "view_repo_map",
            "view_subdirectory",
            "analyze_code",
            "validate_syntax",
            "investigate_codebase",
            "inspect_code_structure",
            "run_shell_command",
            "run_tests_advanced",
            "git_diff",
            "git_log",
            "check_file_changes",
            "backup_file",
        }
    ),
}

# Tools that are ALWAYS included regardless of task type (delegation, memory, core fs/shell)
_ALWAYS_INCLUDE: frozenset = frozenset(
    {
        # Delegation
        "delegate_to_agi",
        "delegate_to_ops",
        "delegate_to_subagent",
        # Memory
        "notebook_write",
        "notebook_read",
        "notebook_search",
        # Core filesystem (MUST always be available)
        "read_file",
        "write_file",
        "edit_file",
        "list_directory",
        # Shell (MUST always be available)
        "run_shell_command",
        # Search
        "find_in_files",
        "codebase_search",
    }
)


def filter_tool_schemas_for_task(
    tool_schemas: List[Dict[str, Any]],
    task_type: str,
) -> List[Dict[str, Any]]:
    """Filter tool schemas based on the detected task type.

    Reduces the number of tool schemas sent to the LLM from 75+ (~7500 tokens)
    to a focused subset of 10-25 tools relevant to the current task.

    Args:
        tool_schemas: Full list of tool schemas in OpenAI Function Calling format.
        task_type: The classified task type string (e.g. "code_edit", "quick_question").
            If "general", "unknown", or not found in the mapping, all tools are returned.

    Returns:
        Filtered list of tool schemas appropriate for the task type.
    """
    if not tool_schemas:
        return tool_schemas

    # Fallback: unknown or general tasks get all tools
    if task_type in ("general", "unknown", ""):
        return tool_schemas

    allowed_tools = _TASK_TOOL_MAP.get(task_type)
    if allowed_tools is None:
        # Task type not mapped — return all tools as fallback
        return tool_schemas

    # Combine task-specific tools with always-included tools
    full_allowed = allowed_tools | _ALWAYS_INCLUDE

    filtered = [
        schema
        for schema in tool_schemas
        if schema.get("function", {}).get("name") in full_allowed
    ]

    # Safety: if filtering removed too many tools (< 5), return all
    # This handles edge cases where tool names don't match expectations
    if len(filtered) < 5 and len(tool_schemas) > 5:
        return tool_schemas

    return filtered


def detect_provider_and_model(model: str) -> Tuple[str, str]:
    """Detect the provider and model from a model name string."""
    model_lower = model.lower()

    if "gemini" in model_lower:
        clean_model = model.split("/")[-1] if "/" in model else model
        return "google", clean_model

    elif model_lower.startswith("groq/") or "groq" in model_lower:
        clean_model = model.split("/", 1)[1] if "/" in model else model
        return "groq", clean_model

    elif "gpt" in model_lower:
        clean_model = model.split("/")[-1] if "/" in model else model
        return "openai", clean_model

    elif "claude" in model_lower:
        clean_model = model.split("/")[-1] if "/" in model else model
        return "anthropic", clean_model

    elif "ollama" in model_lower:
        clean_model = model.split("/")[-1] if "/" in model else model
        return "ollama", clean_model

    elif (
        "nvidia" in model_lower
        or "nemotron" in model_lower
        or model_lower.startswith("openai/nvidia/")
    ):
        # Preserve full model name so api_base is injected correctly
        return "nvidia", model

    else:
        clean_model = model.split("/")[-1] if "/" in model else model
        return "openai", clean_model


def create_llm_config_with_tools(
    model: str,
    api_key: str,
    tools: Optional[Dict[str, Callable]] = None,
    temperature: float = 0.7,
    max_tokens: int = 4096,
) -> Dict[str, Any]:
    """Create an LLM config dict with tool schemas attached."""
    api_type, clean_model = detect_provider_and_model(model)

    if api_type == "google":
        full_model = model if "/" in model else f"gemini/{clean_model}"
        config_dict = {
            "model": full_model,
            "api_key": api_key,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
    elif api_type == "nvidia":
        config_dict = {
            "model": clean_model,
            "api_key": api_key,
            "api_base": "https://integrate.api.nvidia.com/v1",
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
    else:
        full_model = clean_model
        config_dict = {
            "model": full_model,
            "api_key": api_key,
            "api_type": api_type,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

    config = {
        "config_list": [config_dict],
        "timeout": 120,
    }

    if tools:
        tool_schemas = create_tool_schemas(tools)
        if tool_schemas:
            config["tool_schemas"] = tool_schemas
            config["function_map"] = tools

    return config

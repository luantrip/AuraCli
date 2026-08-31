"""
Task Parameter Normalizer for Aura CLI.

This module provides centralized parameter normalization for agent tasks,
ensuring consistent parameter values across different agents and task types.

Features:
    - Default value application
    - Agent-specific parameter overrides
    - Path resolution and validation
    - Parameter type coercion

Architecture:
    Works alongside TaskValidator to prepare task parameters before execution:

    Task ──► TaskParameterNormalizer ──► TaskValidator ──► Agent Execution

Usage:
    >>> from aura_cli.core.agents.planning import TaskParameterNormalizer
    >>> normalizer = TaskParameterNormalizer()
    >>> params, errors = normalizer.normalize("read_file", {"path": "main.py"})
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, ClassVar, Dict, List, Optional, Tuple

from aura_cli.core.logger import get_logger

logger = get_logger(__name__)


class TaskParameterNormalizer:
    """
    Normalizes and validates task parameters before execution.

    Ensures consistent parameter handling across all agent types by:
    - Applying default values for missing parameters
    - Resolving path parameters
    - Handling agent-specific parameter requirements
    - Converting parameter types as needed

    Attributes:
        TASK_SCHEMAS: Schema definitions for each task type
    """

    TASK_SCHEMAS: ClassVar[Dict[str, Dict[str, Any]]] = {
        "read_file": {
            "required": ["path"],
            "defaults": {"offset": 0, "limit": -1},
            "path_params": ["path"],
            "aliases": {"file_path": "path", "filepath": "path", "file": "path"},
        },
        "write_file": {
            "required": ["path", "content"],
            "defaults": {"append": False, "create_dirs": True},
            "path_params": ["path"],
            "aliases": {"file_path": "path", "filepath": "path", "file": "path"},
        },
        "edit_file": {
            "required": ["path", "old_content", "new_content"],
            "defaults": {},
            "path_params": ["path"],
            "aliases": {
                "file_path": "path",
                "filepath": "path",
                "file": "path",
                "old_text": "old_content",
                "new_text": "new_content",
                "search": "old_content",
                "replace": "new_content",
            },
        },
        "create_file": {
            "required": ["path", "content"],
            "defaults": {"overwrite": False},
            "path_params": ["path"],
            "aliases": {"file_path": "path", "filepath": "path"},
        },
        "delete_file": {
            "required": ["path"],
            "defaults": {"force": False},
            "path_params": ["path"],
            "aliases": {"file_path": "path", "filepath": "path"},
        },
        "copy_file": {
            "required": ["source", "destination"],
            "defaults": {"overwrite": False},
            "path_params": ["source", "destination"],
            "aliases": {"src": "source", "dst": "destination", "dest": "destination"},
        },
        "move_file": {
            "required": ["source", "destination"],
            "defaults": {"overwrite": False},
            "path_params": ["source", "destination"],
            "aliases": {"src": "source", "dst": "destination", "dest": "destination"},
        },
        "list_directory": {
            "required": [],
            "defaults": {"path": ".", "show_hidden": False, "recursive": False},
            "path_params": ["path"],
            "aliases": {"dir": "path", "directory": "path"},
        },
        "tree_view": {
            "required": [],
            "defaults": {"path": ".", "max_depth": 3, "show_hidden": False},
            "path_params": ["path"],
            "aliases": {"dir": "path", "directory": "path", "depth": "max_depth"},
        },
        "create_directory": {
            "required": ["path"],
            "defaults": {"parents": True},
            "path_params": ["path"],
            "aliases": {"dir": "path", "directory": "path"},
        },
        "find_in_files": {
            "required": ["pattern"],
            "defaults": {
                "path": ".",
                "max_results": 50,
                "file_extensions": None,
                "case_sensitive": True,
                "regex": False,
            },
            "path_params": ["path"],
            "aliases": {
                "search": "pattern",
                "query": "pattern",
                "text": "pattern",
                "dir": "path",
                "directory": "path",
            },
        },
        "find_files": {
            "required": ["pattern"],
            "defaults": {"path": ".", "max_results": 100},
            "path_params": ["path"],
            "aliases": {"glob": "pattern", "name": "pattern"},
        },
        "analyze_code": {
            "required": [],
            "defaults": {"path": ".", "analysis_type": "general"},
            "path_params": ["path", "file_path"],
            "aliases": {"file": "path", "target": "path"},
            "agent_specific": {
                "review_agent": {
                    "required": ["file_path"],
                    "param_mapping": {"path": "file_path"},
                    "defaults": {"analysis_type": "review"},
                },
                "refactor_agent": {
                    "required": ["file_path"],
                    "param_mapping": {"path": "file_path"},
                    "defaults": {"analysis_type": "refactor"},
                },
                "code_agent": {
                    "required": [],
                    "param_mapping": {"path": "file_path"},
                    "defaults": {"analysis_type": "general"},
                },
                "test_agent": {
                    "required": ["file_path"],
                    "param_mapping": {"path": "file_path"},
                    "defaults": {"analysis_type": "test"},
                },
            },
        },
        "validate_syntax": {
            "required": ["content", "language"],
            "defaults": {"strict": False},
            "aliases": {"code": "content", "lang": "language", "syntax": "language"},
        },
        "lint_code": {
            "required": ["path"],
            "defaults": {"fix": False},
            "path_params": ["path"],
            "aliases": {"file_path": "path", "file": "path"},
        },
        "execute_command": {
            "required": ["command"],
            "defaults": {"timeout": 30, "working_dir": ".", "capture_output": True},
            "path_params": ["working_dir"],
            "aliases": {"cmd": "command", "shell": "command", "cwd": "working_dir"},
        },
        "run_script": {
            "required": ["script_path"],
            "defaults": {"args": [], "timeout": 60},
            "path_params": ["script_path"],
            "aliases": {"script": "script_path", "path": "script_path"},
        },
        "run_tests": {
            "required": [],
            "defaults": {"test_path": ".", "verbose": True, "coverage": False},
            "path_params": ["test_path"],
            "aliases": {"path": "test_path", "tests": "test_path"},
        },
        "run_single_test": {
            "required": ["test_name"],
            "defaults": {"verbose": True},
            "aliases": {"test": "test_name", "name": "test_name"},
        },
        "git_status": {
            "required": [],
            "defaults": {"path": ".", "short": False},
            "path_params": ["path"],
        },
        "git_diff": {
            "required": [],
            "defaults": {"path": ".", "staged": False, "file": None},
            "path_params": ["path"],
        },
        "git_commit": {
            "required": ["message"],
            "defaults": {"path": ".", "add_all": False},
            "path_params": ["path"],
            "aliases": {"msg": "message"},
        },
        "git_add": {
            "required": ["files"],
            "defaults": {"path": "."},
            "path_params": ["path"],
            "aliases": {"file": "files"},
        },
        "git_log": {
            "required": [],
            "defaults": {"path": ".", "count": 10, "oneline": False},
            "path_params": ["path"],
            "aliases": {"n": "count", "num": "count"},
        },
        "git_branch": {
            "required": [],
            "defaults": {"path": ".", "list": True},
            "path_params": ["path"],
        },
        "git_checkout": {
            "required": ["branch"],
            "defaults": {"path": ".", "create": False},
            "path_params": ["path"],
            "aliases": {"b": "branch", "name": "branch"},
        },
        "web_search": {
            "required": ["query"],
            "defaults": {"max_results": 5, "engine": "default"},
            "aliases": {"q": "query", "search": "query"},
        },
        "fetch_url": {
            "required": ["url"],
            "defaults": {"timeout": 30, "method": "GET", "headers": {}},
            "aliases": {"link": "url", "uri": "url"},
        },
        "generate_docs": {
            "required": ["path"],
            "defaults": {"output_dir": "docs", "format": "markdown"},
            "path_params": ["path", "output_dir"],
            "aliases": {"source": "path"},
        },
        "save_to_memory": {
            "required": ["content"],
            "defaults": {"category": "general", "tags": []},
            "aliases": {"text": "content", "data": "content"},
        },
        "search_memory": {
            "required": ["query"],
            "defaults": {"limit": 10, "category": None},
            "aliases": {"q": "query", "search": "query"},
        },
    }

    def __init__(self, working_directory: Optional[str] = None):
        """
        Initialize the normalizer.

        Args:
            working_directory: Base directory for path resolution
        """
        if working_directory is None:
            from aura_cli.core.tools.file_system import get_allowed_base_dir

            working_directory = str(get_allowed_base_dir())
        self.workspace_root = Path(working_directory).expanduser().resolve()
        self.working_directory = str(self.workspace_root)
        logger.debug(
            "TaskParameterNormalizer initialized (workspace: %s)",
            self.working_directory,
        )

    def _apply_agent_schema(
        self, schema: dict, agent_id: str, normalized: dict
    ) -> list:
        """Apply agent-specific defaults, mappings and return required list."""
        agent_schema = schema.get("agent_specific", {}).get(agent_id, {})
        for key, default in agent_schema.get("defaults", {}).items():
            normalized.setdefault(key, default)
        for source, target in agent_schema.get("param_mapping", {}).items():
            if source in normalized and target not in normalized:
                normalized[target] = normalized[source]
                logger.debug(f"Applied agent mapping: {source} -> {target}")
        return agent_schema.get("required", schema.get("required", []))

    def _normalize_paths(
        self, schema: dict, normalized: dict, errors: List[str]
    ) -> None:
        """Resolve path parameters in-place and report boundary violations."""
        for path_param in schema.get("path_params", []):
            if not normalized.get(path_param):
                continue
            try:
                normalized[path_param] = self._resolve_path(normalized[path_param])
            except ValueError as exc:
                errors.append(str(exc))

    def _validate_agent_files(
        self, agent_id: Optional[str], normalized: dict, errors: list
    ) -> None:
        """Validate file paths for agents that require files."""
        _AGENTS_REQUIRING_FILES = {"review_agent", "refactor_agent", "test_agent"}
        if agent_id not in _AGENTS_REQUIRING_FILES:
            return
        file_path = normalized.get("file_path", "")
        if not file_path:
            return
        validation_error = self._validate_file_path(file_path, agent_id)
        if validation_error:
            resolved = self._resolve_to_file(file_path)
            if resolved:
                normalized["file_path"] = resolved
                logger.debug(f"Resolved directory to file: {resolved}")
            else:
                errors.append(validation_error)

    def normalize(
        self,
        task_type: str,
        params: Dict[str, Any],
        agent_id: Optional[str] = None,
    ) -> Tuple[Dict[str, Any], List[str]]:
        """
        Normalize and validate task parameters.

        Applies the following normalization steps:
        1. Resolve parameter aliases to canonical names
        2. Apply default values for missing parameters
        3. Handle agent-specific requirements and mappings
        4. Validate required parameters
        5. Resolve file/directory paths
        6. Validate file paths for agents that require files

        Args:
            task_type: Type of task (e.g., "read_file", "analyze_code")
            params: Raw parameters dictionary
            agent_id: Optional agent ID for agent-specific normalization

        Returns:
            Tuple of (normalized_params, errors)
        """
        schema = self.TASK_SCHEMAS.get(task_type)
        if not schema:
            logger.debug(f"Unknown task type: {task_type}, passing through")
            return {**params, "type": task_type}, []

        errors = []
        normalized = params.copy()

        aliases = schema.get("aliases", {})
        for alias, canonical in aliases.items():
            if alias in normalized and canonical not in normalized:
                normalized[canonical] = normalized.pop(alias)
                logger.debug(f"Resolved alias: {alias} -> {canonical}")

        for key, default in schema.get("defaults", {}).items():
            if key not in normalized or normalized.get(key) is None:
                normalized[key] = default

        if agent_id and "agent_specific" in schema:
            required = self._apply_agent_schema(schema, agent_id, normalized)
        else:
            required = schema.get("required", [])

        for req in required:
            if req not in normalized or not normalized.get(req):
                resolved = self._auto_resolve_param(
                    task_type, req, normalized, agent_id
                )
                if resolved is not None:
                    normalized[req] = resolved
                    logger.debug(f"Auto-resolved parameter: {req} = {resolved}")
                else:
                    errors.append(f"Missing required parameter: {req}")

        self._normalize_paths(schema, normalized, errors)
        self._validate_agent_files(agent_id, normalized, errors)

        normalized["type"] = task_type

        if errors:
            logger.warning(f"Normalization errors for {task_type}: {errors}")
        else:
            logger.debug(f"Normalized {task_type} params: {list(normalized.keys())}")

        return normalized, errors

    def _auto_resolve_param(
        self,
        task_type: str,
        param_name: str,
        current_params: Dict[str, Any],
        agent_id: Optional[str],
    ) -> Optional[Any]:
        """
        Attempt to automatically resolve a missing parameter.

        Args:
            task_type: Task type
            param_name: Parameter name to resolve
            current_params: Current parameters
            agent_id: Agent ID

        Returns:
            Resolved value or None
        """
        if param_name == "file_path" and "path" in current_params:
            path_value = current_params["path"]
            if path_value:
                try:
                    resolved_path = self._resolve_path(path_value)
                except ValueError:
                    return None
                if os.path.isfile(resolved_path):
                    return resolved_path
                if os.path.isdir(resolved_path):
                    return self._resolve_to_file(resolved_path)

        if param_name == "path":
            return "."

        return None

    def _resolve_path(self, path: str) -> str:
        """
        Resolve a path relative to working directory.

        Args:
            path: Path to resolve

        Returns:
            Resolved path string
        """
        if not path or path == ".":
            return self.working_directory

        candidate = Path(path).expanduser()
        resolved = (
            candidate if candidate.is_absolute() else self.workspace_root / candidate
        ).resolve()
        try:
            resolved.relative_to(self.workspace_root)
        except ValueError as exc:
            raise ValueError(f"Path fora do workspace permitido: {path}") from exc
        return str(resolved)

    def _validate_file_path(self, file_path: str, agent_id: str) -> Optional[str]:
        """
        Validate that file_path is actually a file.

        Args:
            file_path: Path to validate
            agent_id: Agent requesting validation

        Returns:
            Error message if invalid, None if valid
        """
        try:
            resolved = self._resolve_path(file_path)
        except ValueError as exc:
            return str(exc)

        if resolved == self.working_directory or file_path == ".":
            return f"Agent {agent_id} requires a specific file, not directory"

        if os.path.exists(resolved) and os.path.isdir(resolved):
            return f"file_path must be a file, not directory: {file_path}"

        return None

    def _resolve_to_file(self, directory: str) -> Optional[str]:
        """
        Find a code file in a directory.

        Args:
            directory: Directory to search

        Returns:
            Path to first code file found, or None
        """
        try:
            resolved_dir = self._resolve_path(directory)
        except ValueError:
            return None

        if not os.path.isdir(resolved_dir):
            return None

        priority_extensions = [
            ".py",
            ".js",
            ".ts",
            ".jsx",
            ".tsx",
            ".java",
            ".cpp",
            ".c",
            ".go",
            ".rs",
            ".rb",
        ]

        try:
            files = [
                f
                for f in os.listdir(resolved_dir)
                if os.path.isfile(os.path.join(resolved_dir, f))
            ]

            for ext in priority_extensions:
                for f in files:
                    if f.endswith(ext):
                        return os.path.join(resolved_dir, f)

            if files:
                return os.path.join(resolved_dir, files[0])

        except OSError as e:
            logger.warning(f"Error listing directory {resolved_dir}: {e}")

        return None

    def get_schema(self, task_type: str) -> Optional[Dict[str, Any]]:
        """
        Get schema for a task type.

        Args:
            task_type: Task type

        Returns:
            Schema dictionary or None
        """
        return self.TASK_SCHEMAS.get(task_type)

    def get_supported_task_types(self) -> List[str]:
        """
        Get list of supported task types.

        Returns:
            List of task type names
        """
        return list(self.TASK_SCHEMAS.keys())

    def validate_task_type(self, task_type: str) -> bool:
        """
        Check if a task type is supported.

        Args:
            task_type: Task type to check

        Returns:
            True if supported
        """
        return task_type in self.TASK_SCHEMAS

    def get_required_params(
        self, task_type: str, agent_id: Optional[str] = None
    ) -> List[str]:
        """
        Get required parameters for a task type.

        Args:
            task_type: Task type
            agent_id: Optional agent ID for agent-specific requirements

        Returns:
            List of required parameter names
        """
        schema = self.TASK_SCHEMAS.get(task_type, {})

        if agent_id and "agent_specific" in schema:
            agent_schema = schema["agent_specific"].get(agent_id, {})
            return agent_schema.get("required", schema.get("required", []))

        return schema.get("required", [])


_normalizer: Optional[TaskParameterNormalizer] = None


def get_task_normalizer(
    working_directory: Optional[str] = None,
) -> TaskParameterNormalizer:
    """
    Get a task parameter normalizer instance.

    Args:
        working_directory: Base directory for path resolution

    Returns:
        TaskParameterNormalizer instance
    """
    global _normalizer
    if _normalizer is None or working_directory:
        _normalizer = TaskParameterNormalizer(working_directory)
    return _normalizer


def normalize_task_params(
    task_type: str,
    params: Dict[str, Any],
    agent_id: Optional[str] = None,
    working_directory: Optional[str] = None,
) -> Tuple[Dict[str, Any], List[str]]:
    """
    Convenience function to normalize task parameters.

    Args:
        task_type: Type of task
        params: Raw parameters
        agent_id: Optional agent ID
        working_directory: Optional working directory

    Returns:
        Tuple of (normalized_params, errors)
    """
    normalizer = get_task_normalizer(working_directory)
    return normalizer.normalize(task_type, params, agent_id)

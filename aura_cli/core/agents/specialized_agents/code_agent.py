"""Code operations specialized agent for the AGI multi-agent system.

Handles read_file, write_file, list_directory, find_in_files, analyze_code,
edit_file, validate_syntax and tree_view tasks. Inherits from AgentBase.
"""

from typing import Any, Dict, List, Optional

from aura_cli.core.agents.agent_base import AgentBase, AgentTask
from aura_cli.core.agents.specialized_agents._tool_schema import schemas_for_categories
from aura_cli.core.logger import get_logger
from aura_cli.core.service_registry import ToolCategory

logger = get_logger(__name__)


class CodeAgent(AgentBase):
    """
    Code operations specialized agent.

    Executes tasks related to:
    - File manipulation
    - Code analysis and search
    - Editing and validation
    - Directory structure
    """

    def __init__(self, agent_id: str = "code_agent", model: Optional[str] = None):
        """
        Initialize CodeAgent.

        Args:
            agent_id: Unique agent ID
            model: LLM model to use (None = default)
        """
        super().__init__(
            agent_id=agent_id,
            name="Code Agent",
            description="Agent specialized in code and file operations",
            model=model,
        )

    def _execute_task(self, task: AgentTask) -> Any:
        """
        Execute a code task.

        Args:
            task: Task to execute

        Returns:
            Execution result
        """
        task_type = task.parameters.get("type", "unknown")

        if task_type == "read_file":
            return self._handle_read_file(task)
        elif task_type == "write_file":
            return self._handle_write_file(task)
        elif task_type == "list_directory":
            return self._handle_list_directory(task)
        elif task_type == "find_in_files":
            return self._handle_find_in_files(task)
        elif task_type == "analyze_code":
            return self._handle_analyze_code(task)
        elif task_type == "edit_file":
            return self._handle_edit_file(task)
        elif task_type == "validate_syntax":
            return self._handle_validate_syntax(task)
        elif task_type == "tree_view":
            return self._handle_tree_view(task)
        else:
            raise ValueError(f"Unknown task type: {task_type}")

    def _handle_read_file(self, task: AgentTask) -> str:
        """Read a file."""
        from aura_cli.core.tools import read_file  # type: ignore[attr-defined]

        path = task.parameters.get("path")
        if not path:
            raise ValueError("Parameter 'path' is required")

        offset = task.parameters.get("offset", 0)
        limit = task.parameters.get("limit", -1)

        return read_file(path, offset=offset, limit=limit)

    def _handle_write_file(self, task: AgentTask) -> str:
        """Write to a file."""
        from aura_cli.core.tools import write_file  # type: ignore[attr-defined]

        path = task.parameters.get("path")
        content = task.parameters.get("content")
        append = task.parameters.get("append", False)

        if not path or content is None:
            raise ValueError("Parameters 'path' and 'content' are required")

        return write_file(path, content, append=append)

    def _handle_list_directory(self, task: AgentTask) -> str:
        """List directory."""
        from aura_cli.core.tools import list_directory  # type: ignore[attr-defined]

        path = task.parameters.get("path", ".")
        return list_directory(path)

    def _handle_find_in_files(self, task: AgentTask) -> str:
        """Search in files."""
        from aura_cli.core.tools import find_in_files  # type: ignore[attr-defined]

        pattern = task.parameters.get("pattern")
        path = task.parameters.get("path", ".")
        file_extensions = task.parameters.get("file_extensions")
        max_results = task.parameters.get("max_results", 50)

        if not pattern:
            raise ValueError("Parameter 'pattern' is required")

        return find_in_files(pattern, path, file_extensions, max_results)

    def _handle_analyze_code(self, task: AgentTask) -> str:
        """Analyze code."""
        from aura_cli.core.tools import analyze_code  # type: ignore[attr-defined]

        file_path = task.parameters.get("file_path")
        if not file_path:
            raise ValueError("Parameter 'file_path' is required")

        return analyze_code(file_path)

    def _handle_edit_file(self, task: AgentTask) -> str:
        """Edit file."""
        from aura_cli.core.tools import edit_file  # type: ignore[attr-defined]

        path = task.parameters.get("path")
        old_content = task.parameters.get("old_content")
        new_content = task.parameters.get("new_content")

        if not all([path, old_content, new_content]):
            raise ValueError(
                "Parameters 'path', 'old_content' and 'new_content' are required"
            )

        return edit_file(path, old_content, new_content)

    def _handle_validate_syntax(self, task: AgentTask) -> str:
        """Validate syntax."""
        from aura_cli.core.tools import validate_syntax  # type: ignore[attr-defined]

        content = task.parameters.get("content")
        language = task.parameters.get("language")

        if not all([content, language]):
            raise ValueError("Parameters 'content' and 'language' are required")

        return validate_syntax(content, language)

    def _handle_tree_view(self, task: AgentTask) -> str:
        """View directory tree."""
        from aura_cli.core.tools import tree_view  # type: ignore[attr-defined]

        path = task.parameters.get("path", ".")
        max_depth = task.parameters.get("max_depth", 3)
        show_hidden = task.parameters.get("show_hidden", False)

        return tree_view(path, max_depth=max_depth, show_hidden=show_hidden)

    def _get_available_tools(self) -> List[Dict[str, Any]]:
        """Return tool schemas for CodeAgent derived from the ServiceRegistry.

        Categories exposed:
        - file_system: read_file, write_file, list_directory, scan_project
        - development: analyze_code, find_in_files, edit_file, validate_syntax, tree_view, …
        - shell: run_shell_command (read-only execution for analysis)
        """
        return schemas_for_categories(
            [ToolCategory.FILE_SYSTEM, ToolCategory.DEVELOPMENT],
            exclude_names=[
                # Keep the agent focused — omit heavy infra/web tools
                "browse_content",
                "web_search",
            ],
        )

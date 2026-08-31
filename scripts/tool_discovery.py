"""
Aura Standard Tool Discovery — Automates tool registration across Core Services.

This orchestrator facilitates the discovery and registration of over 68 standard
capabilities, organizing them into architectural domains for consumption by
the Integrated Tool Registry.

Domains:
    - Codebase Analysis & Navigation.
    - Software Development Lifecycle (Edit, Test, Refactor).
    - Operational Infrastructure (Git, Docker, K8s).
    - Advanced Intelligence (Memory, LLM, AGI Planning).
"""

import inspect
import logging

logger = logging.getLogger(__name__)

# Suffixes/names that indicate internal helpers captured by reflection — never
# expose these as LLM-callable tools.
_REFLECTION_GARBAGE = {
    "dataclass",
    "field",
    "abstractmethod",
    "get_logger",
    "get_stats",
    "get_embedding_model",
}

# Singleton getter suffixes — both bare (func_name in prefixed loops) and prefixed forms
_SINGLETON_SUFFIXES = {
    "security_audit",
    "secret_manager",
    "todo_tracker",
    "vulnerability_scanner",
    "database_backup",
    "database_migration",
    "database_monitor",
    "impact_analysis",
}


def _is_reflection_artifact(name: str) -> bool:
    """Return True if the tool name is a reflection artifact (internal helper)."""
    if name in _REFLECTION_GARBAGE:
        return True
    for suffix in _REFLECTION_GARBAGE:
        if name.endswith(f"_{suffix}"):
            return True
    # Singleton factory: matches both "get_security_audit" (func_name in prefixed loops)
    # and "audit_get_security_audit" (final registered name).
    parts = name.split("_get_")
    if len(parts) >= 2 and parts[-1] in _SINGLETON_SUFFIXES:
        return True
    # Bare form: "get_secret_manager" etc.
    return bool(name.startswith("get_") and name[4:] in _SINGLETON_SUFFIXES)


class CoreToolDiscovery:
    """Orchestrates the discovery and binding of Aura's standard functional capabilities."""

    def __init__(self):
        """Initialize the tool discovery registry."""
        self.tools_registered = 0
        logger.info("Aura CoreToolDiscovery initialized")

    def register_all(self, registry) -> int:
        """Bootstraps the registration of all standard library tools into the target registry."""
        logger.info("Commencing discovery of all standard functional capabilities...")

        self._register_file_system_tools(registry)
        self._register_dev_tools(registry)
        self._register_codebase_tools(registry)
        self._register_shell_tools(registry)
        self._register_web_tools(registry)

        self._register_git_tools(registry)
        self._register_docker_tools(registry)
        self._register_monitoring_tools(registry)

        self._register_refactoring_tools(registry)
        self._register_testing_tools(registry)
        self._register_validation_tools(registry)
        self._register_context_tools(registry)

        self._register_agent_tools(registry)
        self._register_edit_tools(registry)
        self._register_autocomplete_tools(registry)
        self._register_memory_tools(registry)
        self._register_llm_tools(registry)

        self._register_visualization_tools(registry)
        self._register_communication_tools(registry)
        self._register_todo_tools(registry)
        self._register_dependency_tools(registry)

        self._register_infrastructure_tools(registry)
        self._register_database_tools(registry)
        self._register_security_tools(registry)
        self._register_cicd_tools(registry)
        self._register_nim_tools(registry)

        self._register_specialized_agents(registry)
        self._register_planning_tools(registry)
        self._register_checkpoint_tools(registry)
        self._register_paint_tools(registry)

        logger.info(
            f"Standard Library discovery finalized. {self.tools_registered} capabilities mapped."
        )
        return self.tools_registered

    def _register_checkpoint_tools(self, registry):
        """Registra ferramentas de checkpoint (Kiro)."""
        try:
            from aura_cli.core.service_registry import ToolCategory
            from aura_cli.core.tools import checkpoint_tools

            for name, func in checkpoint_tools.CHECKPOINT_TOOLS.items():
                if inspect.isfunction(func) or inspect.ismethod(func):
                    registry._register_tool(
                        name, ToolCategory.DEVELOPMENT, f"Checkpoint: {name}", func, {}
                    )
                    self.tools_registered += 1
        except Exception as e:
            logger.warning(f"Erro ao registrar checkpoint tools: {e}")

    def _register_file_system_tools(self, registry):
        """Registra ferramentas de file system."""
        try:
            from aura_cli.core.service_registry import ToolCategory
            from aura_cli.core.tools import file_system

            tools = [
                ("read_file", file_system.read_file),
                ("write_file", file_system.write_file),
                ("list_directory", file_system.list_directory),
            ]

            for name, func in tools:
                if inspect.isfunction(func) or inspect.ismethod(func):
                    registry._register_tool(
                        name, ToolCategory.FILE_SYSTEM, f"File system: {name}", func, {}
                    )
                    self.tools_registered += 1
        except Exception as e:
            logger.warning(f"Erro ao registrar file_system tools: {e}")

    def _register_dev_tools(self, registry):
        """Registra ferramentas de desenvolvimento."""
        try:
            from aura_cli.core.service_registry import ToolCategory
            from aura_cli.core.tools import dev_tools

            tools = [
                ("analyze_code", dev_tools.analyze_code),
                ("edit_file", dev_tools.edit_file),
                ("tree_view", dev_tools.tree_view),
                ("backup_file", dev_tools.backup_file),
                ("restore_backup", dev_tools.restore_backup),
                ("find_in_files", dev_tools.find_in_files),
                ("validate_syntax", dev_tools.validate_syntax),
                ("tokenize_code", dev_tools.tokenize_code),
                ("classify_code", dev_tools.classify_code),
                ("summarize_code", dev_tools.summarize_code),
                ("find_duplicate_code", dev_tools.find_duplicate_code),
                ("semantic_search_advanced", dev_tools.semantic_search_advanced),
                ("generate_tests_ml", dev_tools.generate_tests_ml),
                ("analyze_code_nlp", dev_tools.analyze_code_nlp),
            ]

            for name, func in tools:
                if inspect.isfunction(func) or inspect.ismethod(func):
                    registry._register_tool(
                        name, ToolCategory.DEVELOPMENT, f"Dev: {name}", func, {}
                    )
                    self.tools_registered += 1
        except Exception as e:
            logger.warning(f"Erro ao registrar dev_tools: {e}")

    def _register_codebase_tools(self, registry):
        """Registra ferramentas de codebase."""
        try:
            from aura_cli.core.service_registry import ToolCategory
            from aura_cli.core.tools import codebase_tools, project_analyzer

            tools = [
                ("codebase_search", codebase_tools.codebase_search),
                ("advanced_grep_search", codebase_tools.advanced_grep_search),
                ("glob_search", codebase_tools.glob_search),
                ("view_repo_map", codebase_tools.view_repo_map),
                ("view_subdirectory", codebase_tools.view_subdirectory),
                (
                    "analyze_project_structure",
                    project_analyzer.analyze_project_structure,
                ),
            ]

            try:
                from aura_cli.core.tools import project_insights

                tools.extend(
                    [
                        (
                            "analyze_project_quality",
                            project_insights.analyze_project_quality,
                        ),
                        (
                            "analyze_project_security",
                            project_insights.analyze_project_security,
                        ),
                        (
                            "analyze_project_documentation",
                            project_insights.analyze_project_documentation,
                        ),
                        (
                            "compare_project_fronts",
                            project_insights.compare_project_fronts,
                        ),
                    ]
                )
            except ImportError:
                logger.warning("project_insights não disponível")

            try:
                from aura_cli.core.tools import codebase_analysis, deep_analysis

                tools.extend(
                    [
                        (
                            "investigate_codebase",
                            codebase_analysis.investigate_codebase,
                        ),
                        (
                            "inspect_code_structure",
                            codebase_tools.inspect_code_structure,
                        ),
                        ("deep_project_analysis", deep_analysis.deep_project_analysis),
                        ("discover_patterns", deep_analysis.discover_patterns),
                    ]
                )
            except ImportError:
                logger.warning("codebase_analysis/deep_analysis não disponível")

            for name, func in tools:
                if inspect.isfunction(func) or inspect.ismethod(func):
                    registry._register_tool(
                        name, ToolCategory.DEVELOPMENT, f"Codebase: {name}", func, {}
                    )
                    self.tools_registered += 1
        except Exception as e:
            logger.warning(f"Erro ao registrar codebase_tools: {e}")

    def _register_shell_tools(self, registry):
        """Registra ferramentas shell."""
        try:
            from aura_cli.core.service_registry import ToolCategory
            from aura_cli.core.tools import shell

            tools = [
                ("run_shell_command", shell.run_shell_command),
            ]

            for name, func in tools:
                if inspect.isfunction(func) or inspect.ismethod(func):
                    registry._register_tool(
                        name, ToolCategory.SHELL, f"Shell: {name}", func, {}
                    )
                    self.tools_registered += 1
        except Exception as e:
            logger.warning(f"Erro ao registrar shell tools: {e}")

    def _register_web_tools(self, registry):
        """Registra ferramentas web."""
        try:
            from aura_cli.core.service_registry import ToolCategory
            from aura_cli.core.tools import web

            tools = [
                ("web_search", web.web_search),
            ]

            for name, func in tools:
                if inspect.isfunction(func) or inspect.ismethod(func):
                    registry._register_tool(
                        name, ToolCategory.WEB, f"Web: {name}", func, {}
                    )
                    self.tools_registered += 1
        except Exception as e:
            logger.warning(f"Erro ao registrar web tools: {e}")

    def _register_git_tools(self, registry):
        """Registra ferramentas Git."""
        try:
            from aura_cli.core.ops_tools import git
            from aura_cli.core.service_registry import ToolCategory
            from aura_cli.core.tools import natural_git

            tools = [
                ("git_status", git.git_status),
                ("git_commit", git.git_commit),
                ("git_diff", git.git_diff),
                ("git_log", git.git_log),
                ("git_branch", git.git_branch),
                ("parse_natural_git_command", natural_git.parse_natural_git_command),
                ("suggest_commit_message", natural_git.suggest_commit_message),
                ("extract_commit_message", natural_git.extract_commit_message),
            ]

            for name, func in tools:
                if inspect.isfunction(func) or inspect.ismethod(func):
                    registry._register_tool(
                        name, ToolCategory.GIT, f"Git: {name}", func, {}
                    )
                    self.tools_registered += 1
        except Exception as e:
            logger.warning(f"Erro ao registrar git tools: {e}")

    def _register_docker_tools(self, registry):
        """Registra ferramentas Docker."""
        try:
            from aura_cli.core.ops_tools import docker
            from aura_cli.core.service_registry import ToolCategory

            tools = [
                ("docker_ps", docker.docker_ps),
                ("docker_logs", docker.docker_logs),
                ("docker_build", docker.docker_build),
                ("docker_compose", docker.docker_compose),
                ("docker_exec", docker.docker_exec),
                ("docker_images", docker.docker_images),
            ]

            for name, func in tools:
                if inspect.isfunction(func) or inspect.ismethod(func):
                    registry._register_tool(
                        name, ToolCategory.DOCKER, f"Docker: {name}", func, {}
                    )
                    self.tools_registered += 1
        except Exception as e:
            logger.warning(f"Erro ao registrar docker tools: {e}")

    def _register_monitoring_tools(self, registry):
        """Registra ferramentas de monitoramento."""
        try:
            from aura_cli.core.ops_tools.monitoring import health
            from aura_cli.core.service_registry import ToolCategory

            tools = [
                ("check_port", health.check_port),
                ("system_resources", health.system_resources),
                ("process_info", health.process_info),
            ]

            for name, func in tools:
                if inspect.isfunction(func) or inspect.ismethod(func):
                    registry._register_tool(
                        name, ToolCategory.MONITORING, f"Monitor: {name}", func, {}
                    )
                    self.tools_registered += 1
        except Exception as e:
            logger.warning(f"Erro ao registrar monitoring tools: {e}")

    def _register_refactoring_tools(self, registry):
        """Registra ferramentas de refatoração."""
        try:
            from aura_cli.core.refactoring import (
                refactoring_executor,
                refactoring_planner,
            )
            from aura_cli.core.service_registry import ToolCategory

            tools = []

            if hasattr(refactoring_planner, "plan_refactoring"):
                tools.append(("plan_refactoring", refactoring_planner.plan_refactoring))
            if hasattr(refactoring_planner, "analyze_refactoring_impact"):
                tools.append(
                    (
                        "analyze_refactoring_impact",
                        refactoring_planner.analyze_refactoring_impact,
                    )
                )

            if hasattr(refactoring_executor, "execute_refactoring"):
                tools.append(
                    ("execute_refactoring", refactoring_executor.execute_refactoring)
                )
            if hasattr(refactoring_executor, "validate_refactoring"):
                tools.append(
                    ("validate_refactoring", refactoring_executor.validate_refactoring)
                )

            for name, func in tools:
                if inspect.isfunction(func) or inspect.ismethod(func):
                    registry._register_tool(
                        name, ToolCategory.DEVELOPMENT, f"Refactor: {name}", func, {}
                    )
                    self.tools_registered += 1
        except Exception as e:
            logger.warning(f"Erro ao registrar refactoring tools: {e}")

    def _register_testing_tools(self, registry):
        """Registra ferramentas de testes."""
        try:
            from aura_cli.core.service_registry import ToolCategory
            from aura_cli.core.testing import test_runner

            tools = []

            if hasattr(test_runner, "run_tests"):
                tools.append(("run_tests_advanced", test_runner.run_tests))
            if hasattr(test_runner, "discover_tests"):
                tools.append(("discover_tests", test_runner.discover_tests))
            if hasattr(test_runner, "run_test_file"):
                tools.append(("run_test_file", test_runner.run_test_file))

            for name, func in tools:
                if inspect.isfunction(func) or inspect.ismethod(func):
                    registry._register_tool(
                        name, ToolCategory.TESTING, f"Test: {name}", func, {}
                    )
                    self.tools_registered += 1
        except Exception as e:
            logger.warning(f"Erro ao registrar testing tools: {e}")

    def _register_validation_tools(self, registry):
        """Registra ferramentas de validação."""
        try:
            from aura_cli.core import validation
            from aura_cli.core.service_registry import ToolCategory

            tools = []

            if hasattr(validation, "validate_python_code"):
                tools.append(("validate_python_code", validation.validate_python_code))
            if hasattr(validation, "validate_file_path"):
                tools.append(("validate_file_path", validation.validate_file_path))
            if hasattr(validation, "validate_edit_operation"):
                tools.append(
                    ("validate_edit_operation", validation.validate_edit_operation)
                )

            for name, func in tools:
                if inspect.isfunction(func) or inspect.ismethod(func):
                    registry._register_tool(
                        name, ToolCategory.DEVELOPMENT, f"Validate: {name}", func, {}
                    )
                    self.tools_registered += 1
        except Exception as e:
            logger.warning(f"Erro ao registrar validation tools: {e}")

    def _register_context_tools(self, registry):
        """Registra ferramentas de contexto."""
        try:
            from aura_cli.core.context import base
            from aura_cli.core.service_registry import ToolCategory

            tools = []

            if hasattr(base, "compress_context"):
                tools.append(("compress_context", base.compress_context))
            if hasattr(base, "calculate_importance"):
                tools.append(("calculate_importance", base.calculate_importance))

            for name, func in tools:
                if inspect.isfunction(func) or inspect.ismethod(func):
                    registry._register_tool(
                        name, ToolCategory.DEVELOPMENT, f"Context: {name}", func, {}
                    )
                    self.tools_registered += 1
        except Exception as e:
            logger.warning(f"Erro ao registrar context tools: {e}")

    def _register_agent_tools(self, registry):
        """Registra ferramentas de agentes."""
        try:
            from aura_cli.core.agents import agent_orchestrator
            from aura_cli.core.service_registry import ToolCategory

            funcs = [
                x
                for x in dir(agent_orchestrator)
                if not x.startswith("_")
                and callable(getattr(agent_orchestrator, x, None))
                and not x[0].isupper()
                and not _is_reflection_artifact(x)
            ]

            for func_name in funcs[:10]:
                func = getattr(agent_orchestrator, func_name, None)
                if func and (inspect.isfunction(func) or inspect.ismethod(func)):
                    registry._register_tool(
                        func_name,
                        ToolCategory.DEVELOPMENT,
                        f"Agent: {func_name}",
                        func,
                        {},
                    )
                    self.tools_registered += 1
        except Exception as e:
            logger.warning(f"Erro ao registrar agent tools: {e}")

    def _register_edit_tools(self, registry):
        """Registra ferramentas de edição."""
        try:
            from aura_cli.core.edit import edit_executor, edit_planner
            from aura_cli.core.service_registry import ToolCategory

            exec_funcs = [
                x
                for x in dir(edit_executor)
                if not x.startswith("_")
                and callable(getattr(edit_executor, x, None))
                and not x[0].isupper()
                and not _is_reflection_artifact(x)
            ]
            for func_name in exec_funcs[:5]:
                func = getattr(edit_executor, func_name, None)
                if func and (inspect.isfunction(func) or inspect.ismethod(func)):
                    registry._register_tool(
                        f"edit_{func_name}",
                        ToolCategory.DEVELOPMENT,
                        f"Edit: {func_name}",
                        func,
                        {},
                    )
                    self.tools_registered += 1

            plan_funcs = [
                x
                for x in dir(edit_planner)
                if not x.startswith("_")
                and callable(getattr(edit_planner, x, None))
                and not x[0].isupper()
                and not _is_reflection_artifact(x)
            ]
            for func_name in plan_funcs[:5]:
                func = getattr(edit_planner, func_name, None)
                if func and (inspect.isfunction(func) or inspect.ismethod(func)):
                    registry._register_tool(
                        f"plan_{func_name}",
                        ToolCategory.DEVELOPMENT,
                        f"Plan: {func_name}",
                        func,
                        {},
                    )
                    self.tools_registered += 1
        except Exception as e:
            logger.warning(f"Erro ao registrar edit tools: {e}")

    def _register_autocomplete_tools(self, registry):
        """Registra ferramentas de autocomplete."""
        try:
            from aura_cli.core.autocomplete import filtering, generation
            from aura_cli.core.service_registry import ToolCategory

            gen_funcs = [
                x
                for x in dir(generation)
                if not x.startswith("_")
                and callable(getattr(generation, x, None))
                and not x[0].isupper()
                and not _is_reflection_artifact(x)
            ]
            for func_name in gen_funcs[:5]:
                func = getattr(generation, func_name, None)
                if func and (inspect.isfunction(func) or inspect.ismethod(func)):
                    registry._register_tool(
                        f"autocomplete_{func_name}",
                        ToolCategory.DEVELOPMENT,
                        f"Autocomplete: {func_name}",
                        func,
                        {},
                    )
                    self.tools_registered += 1

            filt_funcs = [
                x
                for x in dir(filtering)
                if not x.startswith("_")
                and callable(getattr(filtering, x, None))
                and not x[0].isupper()
                and not _is_reflection_artifact(x)
            ]
            for func_name in filt_funcs[:5]:
                func = getattr(filtering, func_name, None)
                if func and (inspect.isfunction(func) or inspect.ismethod(func)):
                    registry._register_tool(
                        f"filter_{func_name}",
                        ToolCategory.DEVELOPMENT,
                        f"Filter: {func_name}",
                        func,
                        {},
                    )
                    self.tools_registered += 1
        except Exception as e:
            logger.warning(f"Erro ao registrar autocomplete tools: {e}")

    def _register_memory_tools(self, registry):
        """Registra ferramentas de memória."""
        try:
            from aura_cli.core.memory_advanced import embeddings, semantic_search
            from aura_cli.core.service_registry import ToolCategory

            emb_funcs = [
                x
                for x in dir(embeddings)
                if not x.startswith("_")
                and callable(getattr(embeddings, x, None))
                and not x[0].isupper()
                and not _is_reflection_artifact(x)
            ]
            for func_name in emb_funcs[:5]:
                func = getattr(embeddings, func_name, None)
                if func and (inspect.isfunction(func) or inspect.ismethod(func)):
                    registry._register_tool(
                        f"memory_{func_name}",
                        ToolCategory.DEVELOPMENT,
                        f"Memory: {func_name}",
                        func,
                        {},
                    )
                    self.tools_registered += 1

            search_funcs = [
                x
                for x in dir(semantic_search)
                if not x.startswith("_")
                and callable(getattr(semantic_search, x, None))
                and not x[0].isupper()
                and not _is_reflection_artifact(x)
            ]
            for func_name in search_funcs[:5]:
                func = getattr(semantic_search, func_name, None)
                if func and (inspect.isfunction(func) or inspect.ismethod(func)):
                    registry._register_tool(
                        f"search_{func_name}",
                        ToolCategory.DEVELOPMENT,
                        f"Search: {func_name}",
                        func,
                        {},
                    )
                    self.tools_registered += 1
        except Exception as e:
            logger.warning(f"Erro ao registrar memory tools: {e}")

    def _register_llm_tools(self, registry):
        """Registra ferramentas de LLM."""
        try:
            from aura_cli.core.llm import base, multi_model
            from aura_cli.core.service_registry import ToolCategory

            if hasattr(base, "query_with_fallback"):
                registry._register_tool(
                    "query_llm",
                    ToolCategory.DEVELOPMENT,
                    "LLM: query with fallback",
                    base.query_with_fallback,
                    {},
                )
                self.tools_registered += 1

            mm_funcs = [
                x
                for x in dir(multi_model)
                if not x.startswith("_")
                and callable(getattr(multi_model, x, None))
                and not x[0].isupper()
                and not _is_reflection_artifact(x)
            ]
            for func_name in mm_funcs[:5]:
                func = getattr(multi_model, func_name, None)
                if func and (inspect.isfunction(func) or inspect.ismethod(func)):
                    registry._register_tool(
                        f"llm_{func_name}",
                        ToolCategory.DEVELOPMENT,
                        f"LLM: {func_name}",
                        func,
                        {},
                    )
                    self.tools_registered += 1
        except Exception as e:
            logger.warning(f"Erro ao registrar llm tools: {e}")

    def _register_visualization_tools(self, registry):
        """Registra ferramentas de visualização."""
        try:
            from aura_cli.core.service_registry import ToolCategory
            from aura_cli.core.visualization import visualization

            viz_funcs = [
                x
                for x in dir(visualization)
                if not x.startswith("_")
                and callable(getattr(visualization, x, None))
                and not x[0].isupper()
                and not _is_reflection_artifact(x)
            ]
            for func_name in viz_funcs[:10]:
                func = getattr(visualization, func_name, None)
                if func and (inspect.isfunction(func) or inspect.ismethod(func)):
                    registry._register_tool(
                        f"viz_{func_name}",
                        ToolCategory.DEVELOPMENT,
                        f"Viz: {func_name}",
                        func,
                        {},
                    )
                    self.tools_registered += 1
        except Exception as e:
            logger.warning(f"Erro ao registrar visualization tools: {e}")

    def _register_communication_tools(self, registry):
        """Registra ferramentas de comunicação."""
        try:
            from aura_cli.core.communication import streaming
            from aura_cli.core.service_registry import ToolCategory

            stream_funcs = [
                x
                for x in dir(streaming)
                if not x.startswith("_")
                and callable(getattr(streaming, x, None))
                and not x[0].isupper()
                and not _is_reflection_artifact(x)
            ]
            for func_name in stream_funcs[:10]:
                func = getattr(streaming, func_name, None)
                if func and (inspect.isfunction(func) or inspect.ismethod(func)):
                    registry._register_tool(
                        f"stream_{func_name}",
                        ToolCategory.DEVELOPMENT,
                        f"Stream: {func_name}",
                        func,
                        {},
                    )
                    self.tools_registered += 1
        except Exception as e:
            logger.warning(f"Erro ao registrar communication tools: {e}")

    def _register_todo_tools(self, registry):
        """Registra ferramentas de todo."""
        try:
            from aura_cli.core.service_registry import ToolCategory
            from aura_cli.core.todo import todo_tracker

            todo_funcs = [
                x
                for x in dir(todo_tracker)
                if not x.startswith("_")
                and callable(getattr(todo_tracker, x, None))
                and not x[0].isupper()
                and not _is_reflection_artifact(x)
            ]
            for func_name in todo_funcs[:10]:
                func = getattr(todo_tracker, func_name, None)
                if func and (inspect.isfunction(func) or inspect.ismethod(func)):
                    registry._register_tool(
                        f"todo_{func_name}",
                        ToolCategory.DEVELOPMENT,
                        f"Todo: {func_name}",
                        func,
                        {},
                    )
                    self.tools_registered += 1
        except Exception as e:
            logger.warning(f"Erro ao registrar todo tools: {e}")

    def _register_dependency_tools(self, registry):
        """Registra ferramentas de análise de dependências."""
        try:
            from aura_cli.core import dependency_analysis
            from aura_cli.core.service_registry import ToolCategory

            dep_funcs = [
                x
                for x in dir(dependency_analysis)
                if not x.startswith("_")
                and callable(getattr(dependency_analysis, x, None))
                and not x[0].isupper()
                and not _is_reflection_artifact(x)
            ]
            for func_name in dep_funcs[:10]:
                func = getattr(dependency_analysis, func_name, None)
                if func and (inspect.isfunction(func) or inspect.ismethod(func)):
                    registry._register_tool(
                        f"dep_{func_name}",
                        ToolCategory.DEVELOPMENT,
                        f"Dependency: {func_name}",
                        func,
                        {},
                    )
                    self.tools_registered += 1
        except Exception as e:
            logger.warning(f"Erro ao registrar dependency tools: {e}")

    def _register_cli_tools(self, registry):
        """
        Registra ferramentas CLI.

        NOTE: Moved to aura_cli.cli.utils.tool_registrar to break circular dependency.
        This method is kept as a placeholder/comment.
        """

    def _register_infrastructure_tools(self, registry):
        """Registra ferramentas de infraestrutura."""
        try:
            from aura_cli.core.ops_tools.infrastructure import (
                cloud_providers,
                infrastructure_as_code,
                kubernetes,
                terraform,
            )
            from aura_cli.core.service_registry import ToolCategory

            modules = [
                (kubernetes, "k8s"),
                (terraform, "tf"),
                (cloud_providers, "cloud"),
                (infrastructure_as_code, "iac"),
            ]

            for module, prefix in modules:
                funcs = [
                    x
                    for x in dir(module)
                    if not x.startswith("_")
                    and callable(getattr(module, x, None))
                    and not x[0].isupper()
                    and not _is_reflection_artifact(x)
                ]
                for func_name in funcs[:10]:
                    func = getattr(module, func_name, None)
                    if func and (inspect.isfunction(func) or inspect.ismethod(func)):
                        registry._register_tool(
                            f"{prefix}_{func_name}",
                            ToolCategory.CI_CD,
                            f"Infra: {func_name}",
                            func,
                            {},
                        )
                        self.tools_registered += 1
        except Exception as e:
            logger.warning(f"Erro ao registrar infrastructure tools: {e}")

    def _register_database_tools(self, registry):
        """Registra ferramentas de database."""
        try:
            from aura_cli.core.ops_tools.database import (
                database_backup,
                database_migration,
                database_monitor,
            )
            from aura_cli.core.service_registry import ToolCategory

            modules = [
                (database_backup, "db_backup"),
                (database_migration, "db_migrate"),
                (database_monitor, "db_monitor"),
            ]

            for module, prefix in modules:
                funcs = [
                    x
                    for x in dir(module)
                    if not x.startswith("_")
                    and callable(getattr(module, x, None))
                    and not x[0].isupper()
                    and not _is_reflection_artifact(x)
                ]
                for func_name in funcs[:10]:
                    func = getattr(module, func_name, None)
                    if func and (inspect.isfunction(func) or inspect.ismethod(func)):
                        registry._register_tool(
                            f"{prefix}_{func_name}",
                            ToolCategory.CI_CD,
                            f"DB: {func_name}",
                            func,
                            {},
                        )
                        self.tools_registered += 1
        except Exception as e:
            logger.warning(f"Erro ao registrar database tools: {e}")

    def _register_security_tools(self, registry):
        """Registra ferramentas de segurança."""
        try:
            from aura_cli.core.ops_tools.security import (
                secret_manager,
                security_audit,
                vulnerability_scanner,
            )
            from aura_cli.core.service_registry import ToolCategory

            modules = [
                (vulnerability_scanner, "vuln"),
                (security_audit, "audit"),
                (secret_manager, "secret"),
            ]

            for module, prefix in modules:
                funcs = [
                    x
                    for x in dir(module)
                    if not x.startswith("_")
                    and callable(getattr(module, x, None))
                    and not x[0].isupper()
                    and not _is_reflection_artifact(x)
                ]
                for func_name in funcs[:10]:
                    func = getattr(module, func_name, None)
                    if func and (inspect.isfunction(func) or inspect.ismethod(func)):
                        registry._register_tool(
                            f"{prefix}_{func_name}",
                            ToolCategory.CI_CD,
                            f"Security: {func_name}",
                            func,
                            {},
                        )
                        self.tools_registered += 1
        except Exception as e:
            logger.warning(f"Erro ao registrar security tools: {e}")

    def _register_cicd_tools(self, registry):
        """Registra ferramentas de CI/CD."""
        try:
            from aura_cli.core.ops_tools.ci_cd import (
                deployment,
                github_actions,
                pipeline_manager,
            )
            from aura_cli.core.service_registry import ToolCategory

            modules = [
                (github_actions, "gh"),
                (pipeline_manager, "pipeline"),
                (deployment, "deploy"),
            ]

            for module, prefix in modules:
                funcs = [
                    x
                    for x in dir(module)
                    if not x.startswith("_")
                    and callable(getattr(module, x, None))
                    and not x[0].isupper()
                    and not _is_reflection_artifact(x)
                ]
                for func_name in funcs[:10]:
                    func = getattr(module, func_name, None)
                    if func and (inspect.isfunction(func) or inspect.ismethod(func)):
                        registry._register_tool(
                            f"{prefix}_{func_name}",
                            ToolCategory.CI_CD,
                            f"CICD: {func_name}",
                            func,
                            {},
                        )
                        self.tools_registered += 1
        except Exception as e:
            logger.warning(f"Erro ao registrar cicd tools: {e}")

    def _register_nim_tools(self, registry):
        """Registra ferramentas Nim (F1 Engine)."""
        try:
            from aura_cli.core.service_registry import ToolCategory
            from aura_cli.core.tools import nim_integration

            nim_tools = [
                (
                    "scan_project",
                    nim_integration.scan_project,
                    ToolCategory.FILE_SYSTEM,
                    "Imagination: Fast Project Scanner",
                ),
                (
                    "browse_content",
                    nim_integration.browse_content,
                    ToolCategory.WEB,
                    "Monitor: Headless Browser",
                ),
                (
                    "analyze_dependencies",
                    nim_integration.analyze_dependencies,
                    ToolCategory.ANALYSIS,
                    "Nexus: Dependency Graph",
                ),
                (
                    "check_file_changes",
                    nim_integration.check_file_changes,
                    ToolCategory.MONITORING,
                    "Sentinel: Change Detector",
                ),
                (
                    "sanitize_code",
                    nim_integration.sanitize_code,
                    ToolCategory.DEVELOPMENT,
                    "Forge: Code Sanitizer",
                ),
                (
                    "format_file",
                    nim_integration.format_file,
                    ToolCategory.DEVELOPMENT,
                    "Forge: Format File",
                ),
                (
                    "notebook_write",
                    nim_integration.notebook_write,
                    ToolCategory.DEVELOPMENT,
                    "Notebook: Write Memory",
                ),
                (
                    "notebook_read",
                    nim_integration.notebook_read,
                    ToolCategory.DEVELOPMENT,
                    "Notebook: Read Memory",
                ),
                (
                    "notebook_list",
                    nim_integration.notebook_list,
                    ToolCategory.DEVELOPMENT,
                    "Notebook: List Pages",
                ),
                (
                    "notebook_search",
                    nim_integration.notebook_search,
                    ToolCategory.DEVELOPMENT,
                    "Notebook: Search Memory",
                ),
            ]

            for name, func, category, desc in nim_tools:
                registry._register_tool(
                    name,
                    category,
                    desc,
                    func,
                    {},  # Schema will be auto-generated
                )
                self.tools_registered += 1

        except Exception as e:
            logger.warning(f"Erro ao registrar nim tools: {e}")

    def _register_specialized_agents(self, registry):
        """Registra agentes especializados."""
        try:
            from aura_cli.core.agents.specialized_agents import (
                code_agent,
                refactor_agent,
                review_agent,
                test_agent,
            )
            from aura_cli.core.service_registry import ToolCategory

            modules = [
                (code_agent, "code_agent"),
                (test_agent, "test_agent"),
                (refactor_agent, "refactor_agent"),
                (review_agent, "review_agent"),
            ]

            for module, prefix in modules:
                funcs = [
                    x
                    for x in dir(module)
                    if not x.startswith("_")
                    and callable(getattr(module, x, None))
                    and not x[0].isupper()
                    and not _is_reflection_artifact(x)
                ]
                for func_name in funcs[:10]:
                    func = getattr(module, func_name, None)
                    if func and (inspect.isfunction(func) or inspect.ismethod(func)):
                        registry._register_tool(
                            f"{prefix}_{func_name}",
                            ToolCategory.DEVELOPMENT,
                            f"Agent: {func_name}",
                            func,
                            {},
                        )
                        self.tools_registered += 1
        except Exception as e:
            logger.warning(f"Erro ao registrar specialized agents: {e}")

    def _register_planning_tools(self, registry):
        """Registra ferramentas de planejamento."""
        try:
            from aura_cli.core.agents.planning import (
                execution_engine,
                problem_decomposer,
                task_planner,
            )
            from aura_cli.core.service_registry import ToolCategory

            modules = [
                (task_planner, "plan"),
                (problem_decomposer, "decompose"),
                (execution_engine, "execute"),
            ]

            for module, prefix in modules:
                funcs = [
                    x
                    for x in dir(module)
                    if not x.startswith("_")
                    and callable(getattr(module, x, None))
                    and not x[0].isupper()
                    and not _is_reflection_artifact(x)
                ]
                for func_name in funcs[:10]:
                    func = getattr(module, func_name, None)
                    if func and (inspect.isfunction(func) or inspect.ismethod(func)):
                        registry._register_tool(
                            f"{prefix}_{func_name}",
                            ToolCategory.DEVELOPMENT,
                            f"Planning: {func_name}",
                            func,
                            {},
                        )
                        self.tools_registered += 1
        except Exception as e:
            logger.warning(f"Erro ao registrar planning tools: {e}")

    def _register_paint_tools(self, registry):
        """Registra ferramentas de Paint (art generation)."""
        try:
            from aura_cli.core.service_registry import ToolCategory
            from aura_cli.core.tools import paint_tools

            tools = [
                ("paint_generate_art", paint_tools.paint_generate_art),
            ]

            for name, func in tools:
                if inspect.isfunction(func) or inspect.ismethod(func):
                    registry._register_tool(
                        name,
                        ToolCategory.DEVELOPMENT,
                        f"Paint: {name}",
                        func,
                        {
                            "type": "object",
                            "properties": {
                                "prompt": {
                                    "type": "string",
                                    "description": "Description of art to generate (e.g., 'a cat', 'ASCII art of a house')",
                                },
                                "width": {
                                    "type": "integer",
                                    "description": "Canvas width in characters",
                                    "default": 80,
                                },
                                "height": {
                                    "type": "integer",
                                    "description": "Canvas height in characters",
                                    "default": 24,
                                },
                                "output_file": {
                                    "type": "string",
                                    "description": "Optional file path to save result. If not provided, saves to 'artes/' directory",
                                },
                                "output_format": {
                                    "type": "string",
                                    "enum": ["ans", "png", "svg", "html"],
                                    "description": "Output format: 'ans' (ANSI), 'png', 'svg', or 'html'",
                                    "default": "ans",
                                },
                                "mode": {
                                    "type": "string",
                                    "enum": ["auto", "ascii", "primitives", "hybrid"],
                                    "description": "Generation mode: 'auto' (LLM decides), 'ascii', 'primitives', or 'hybrid'",
                                    "default": "auto",
                                },
                            },
                            "required": ["prompt"],
                        },
                    )
                    self.tools_registered += 1
        except Exception as e:
            logger.warning(f"Erro ao registrar paint tools: {e}")

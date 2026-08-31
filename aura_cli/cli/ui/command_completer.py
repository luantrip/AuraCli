"""Intelligent autocomplete for Aura CLI slash commands.

Provides contextual completions for "/" commands with fuzzy matching,
usage-frequency prioritisation, command preview and context-aware
argument suggestions. CommandCompleter is the main Completer class;
CompletionCache caches results to avoid redundant computation.
"""

from typing import Dict, Iterable, List, Optional, Set, Tuple

from prompt_toolkit.completion import Completer, Completion
from prompt_toolkit.document import Document

from aura_cli.application.presentation.autocomplete import FuzzyMatcher
from aura_cli.core.logger import get_logger

logger = get_logger(__name__)


class CommandCompleter(Completer):
    """Fuzzy-matching completer for Aura CLI slash commands.

    Completes main commands (/help, /tools, …) and contextual arguments
    (/theme minimal, /ops git, …), prioritised by usage frequency.
    """

    def __init__(self):
        """Initialise the completer with available commands and arguments."""
        from aura_cli.cli.commands.slash_registry import (
            get_cli_command_args,
            get_cli_command_descriptions,
            get_cli_command_prefixes,
        )

        self.commands = get_cli_command_descriptions()
        self.command_args: Dict[str, List[str]] = get_cli_command_args()
        self.command_prefixes: Dict[str, Dict[str, str]] = get_cli_command_prefixes()

        self.command_history: List[str] = []
        self.command_frequency: Dict[str, int] = {}
        self.tool_names: Set[str] = set()
        self.fuzzy_matcher = FuzzyMatcher()
        self.min_fuzzy_score = 0.3
        self._load_tool_names()

    def _load_tool_names(self):
        """Load available tool names for /tool autocomplete."""
        try:
            from aura_cli.core.service_registry import get_service_registry

            registry = get_service_registry()
            if hasattr(registry, "tools"):
                self.tool_names = set(registry.tools.keys())
            else:
                self._load_fallback_tools()
        except Exception:
            self._load_fallback_tools()

    def _load_fallback_tools(self):
        """Load a basic tool list as a fallback."""
        self.tool_names = {
            "read_file",
            "write_file",
            "list_directory",
            "analyze_code",
            "edit_file",
            "git_status",
            "git_diff",
            "git_log",
            "docker_ps",
            "docker_logs",
            "run_shell_command",
            "web_search",
            "find_in_files",
            "tree_view",
            "validate_syntax",
        }

    def _complete_commands(self, command: str) -> Iterable[Completion]:
        """Yield command completions with fuzzy matching."""
        matches = self.fuzzy_matcher.fuzzy_match(
            command, list(self.commands.keys()), self.min_fuzzy_score
        )
        scored = sorted(
            [
                (
                    cmd,
                    score + min(self.command_frequency.get(cmd, 0) / 100, 0.3),
                    self.commands[cmd],
                )
                for cmd, score in matches
            ],
            key=lambda x: x[1],
            reverse=True,
        )
        for cmd, score, description in scored[:10]:
            if cmd.startswith(command):
                completion_text, start_pos = cmd[len(command) :], 0
            else:
                completion_text, start_pos = cmd, -len(command)
            meta = (
                f"✓ {description}"
                if score >= 1.0
                else f"~ {description} (score: {score:.2f})"
            )
            yield Completion(
                completion_text,
                start_position=start_pos,
                display=cmd,
                display_meta=meta,
            )

    def _complete_tool_arg(self, arg: str) -> Iterable[Completion]:
        """Yield tool name completions."""
        matches = self.fuzzy_matcher.fuzzy_match(
            arg, sorted(self.tool_names), self.min_fuzzy_score
        )
        for tool_name, score in matches[:15]:
            if tool_name.lower().startswith(arg.lower()):
                completion_text, start_pos = tool_name[len(arg) :], 0
            else:
                completion_text, start_pos = tool_name, -len(arg)
            meta = (
                f"Ferramenta: {tool_name}"
                if score >= 1.0
                else f"~ Ferramenta: {tool_name}"
            )
            yield Completion(
                completion_text,
                start_position=start_pos,
                display=tool_name,
                display_meta=meta,
            )

    def _complete_command_arg(self, command: str, arg: str) -> Iterable[Completion]:
        """Yield argument completions for a specific command."""
        suggestions = self._get_contextual_suggestions(command, arg)
        _DESCS = {
            "/theme": "UI theme",
            "/ops": "DevOps operation type",
            "/dev": "Dev mode state",
            "/auto": "Auto mode state",
            "/model": "AI model",
            "/session": "Session action",
            "/workflow": "Workflow action",
            "/cache": "Cache action",
            "/checkpoint": "Checkpoint action",
            "/tangent": "Tangent action",
        }
        base_desc = _DESCS.get(command, "Argument")
        for suggestion, score in suggestions:
            if suggestion.lower().startswith(arg.lower()):
                completion_text, start_pos = suggestion[len(arg) :], 0
            else:
                completion_text, start_pos = suggestion, -len(arg)
            meta = (
                f"{base_desc}: {suggestion}"
                if score >= 1.0
                else f"~ {base_desc}: {suggestion}"
            )
            yield Completion(
                completion_text,
                start_position=start_pos,
                display=suggestion,
                display_meta=meta,
            )

    def _complete_agi_ops_arg(self, command: str, arg: str) -> Iterable[Completion]:
        """Yield example completions for /agi and /ops."""
        if arg and len(arg.split()) > 1:
            return
        examples = (
            [
                "criar app",
                "refatorar código",
                "implementar feature",
                "otimizar performance",
            ]
            if command == "/agi"
            else ["git status", "docker ps", "deploy", "backup"]
        )
        for example in examples:
            if not arg or example.lower().startswith(arg.lower()):
                completion_text = example[len(arg) :] if arg else example
                start_pos = 0 if arg else -len(command) - 1
                yield Completion(
                    completion_text,
                    start_position=start_pos,
                    display=example,
                    display_meta="Exemplo de uso",
                )

    def get_completions(
        self, document: Document, _complete_event
    ) -> Iterable[Completion]:
        """Generate autocomplete suggestions with fuzzy matching."""
        raw_text = document.text_before_cursor
        text_lower = raw_text.lstrip().lower()
        if not text_lower.startswith("/"):
            return

        has_argument_separator = text_lower.endswith((" ", "\t"))
        parts = text_lower.split(maxsplit=1)
        command = parts[0] if parts else ""
        arg = parts[1] if len(parts) > 1 else ""

        if command in {"/agi", "/ops"} and (arg or has_argument_separator):
            yield from self._complete_agi_ops_arg(command, arg)
            return

        if command == "/tool" and (arg or has_argument_separator):
            yield from self._complete_tool_arg(arg)
            return

        if command in self.command_args and (arg or has_argument_separator):
            yield from self._complete_command_arg(command, arg)
            return

        if not arg and not has_argument_separator:
            yield from self._complete_commands(command)

    def add_to_history(self, command: str):
        """Add a command to history and update frequency."""
        if command and command.startswith("/"):
            cmd_base = command.split()[0]
            self.command_frequency[cmd_base] = (
                self.command_frequency.get(cmd_base, 0) + 1
            )
            if command not in self.command_history:
                self.command_history.insert(0, command)
                self.command_history = self.command_history[:50]

    def _get_contextual_suggestions(
        self, command: str, arg: str
    ) -> List[Tuple[str, float]]:
        """Return contextual suggestions with fuzzy matching."""
        if command not in self.command_args:
            return []

        available = self.command_args[command]
        matches = self.fuzzy_matcher.fuzzy_match(arg, available, self.min_fuzzy_score)
        if matches:
            return matches
        if command in self.command_prefixes:
            prefix_map = self.command_prefixes[command]
            arg_lower = arg.lower()

            if arg_lower in prefix_map:
                return [(prefix_map[arg_lower], 1.0)]

            for prefix, full in prefix_map.items():
                if prefix.startswith(arg_lower):
                    return [(full, 0.9)]

        return [(opt, 0.5) for opt in available]

    def get_command_preview(self, command: str) -> Optional[str]:
        """Return a preview description for a command."""
        cmd_base = command.split()[0] if command else ""
        return self.commands.get(cmd_base)

    def get_stats(self) -> dict:
        """Return completer usage statistics as a dict."""
        return {
            "total_commands": len(self.commands),
            "total_tools": len(self.tool_names),
            "history_size": len(self.command_history),
            "most_used": sorted(
                self.command_frequency.items(), key=lambda x: x[1], reverse=True
            )[:5],
        }

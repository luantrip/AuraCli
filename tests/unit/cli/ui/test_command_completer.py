from prompt_toolkit.document import Document

from aura_cli.application.presentation.autocomplete import FuzzyMatcher
from aura_cli.cli.ui.command_completer import CommandCompleter


def _completer() -> CommandCompleter:
    completer = CommandCompleter.__new__(CommandCompleter)
    completer.commands = {
        "/help": "Ajuda",
        "/model": "Selecionar modelo",
        "/tool": "Executar ferramenta",
    }
    completer.command_args = {
        "/model": ["gpt", "auto"],
        "/tool": [],
    }
    completer.command_prefixes = {}
    completer.command_history = []
    completer.command_frequency = {}
    completer.tool_names = {"read_file", "write_file"}
    completer.fuzzy_matcher = FuzzyMatcher()
    completer.min_fuzzy_score = 0.3
    return completer


def _displays(completer: CommandCompleter, text: str) -> list[str]:
    return [
        item.display_text for item in completer.get_completions(Document(text), None)
    ]


def test_space_after_tool_opens_tool_suggestions() -> None:
    completer = _completer()

    assert _displays(completer, "/tool")[0] == "/tool"
    assert _displays(completer, "/tool ") == ["read_file", "write_file"]
    assert _displays(completer, "/tool wr") == ["write_file"]


def test_space_after_model_opens_argument_suggestions() -> None:
    completer = _completer()

    assert _displays(completer, "/model")[0] == "/model"
    assert _displays(completer, "/model ") == ["gpt", "auto"]
    assert _displays(completer, "/model au") == ["auto"]


def test_agi_and_ops_examples_open_after_argument_separator() -> None:
    completer = _completer()

    assert "criar app" in _displays(completer, "/agi ")
    assert "git status" in _displays(completer, "/ops ")
    assert _displays(completer, "/agi criar app") == []

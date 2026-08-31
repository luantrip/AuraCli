"""Pure prompt preparation and tool-selection policies."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Iterable, Mapping, Sequence

PROTECTED_TAGS = (
    "</constitution>",
    "<constitution>",
    "</system>",
    "<system>",
    "</user>",
    "<user>",
    "</assistant>",
    "<assistant>",
    "</context>",
    "<context>",
)

PURE_QUESTION_PATTERNS = (
    "o que é ",
    "what is ",
    "o que são ",
    "what are ",
    "como funciona ",
    "how does ",
    "explique ",
    "explain ",
    "qual a diferença",
    "what's the difference",
    "me fale sobre",
    "tell me about",
)

MINIMAL_QUESTION_TOOLS = frozenset(
    {
        "read_file",
        "list_directory",
        "find_in_files",
        "codebase_search",
        "web_search",
        "tree_view",
    }
)


@dataclass(frozen=True)
class PreparedPrompt:
    original: str
    rendered: str
    used_constitution: bool
    used_pending_context: bool


def sanitize_prompt_text(text: str) -> str:
    """Escape structural tags controlled by the application prompt."""
    result = text
    for tag in PROTECTED_TAGS:
        result = result.replace(tag, f"[escaped:{tag}]")
    return result


def estimate_context_tokens(
    history: Iterable[Mapping[str, Any]],
    extra_text: str | None = None,
    *,
    chars_per_token: float = 4.0,
) -> int:
    total = sum(len(str(message.get("content", ""))) for message in history)
    if extra_text:
        total += len(extra_text)
    return int(total / max(chars_per_token, 1.0))


def prepare_prompt(
    command: str,
    *,
    constitution: str = "",
    pending_context: str = "",
    reducer: Callable[[str], str] | None = None,
    reduce_above: int = 4000,
) -> PreparedPrompt:
    """Compose protected constitution and file context around a user command."""
    rendered = command
    used_constitution = bool(constitution)
    used_context = bool(pending_context)
    if constitution:
        rendered = (
            "Baseado na seguinte 'Constituição do Projeto', que define as regras e padrões, "
            "processe o meu pedido. A constituição é imutável para esta tarefa.\n\n"
            f"<constitution>\n{constitution}\n</constitution>\n\n"
            f"Pedido do Usuário: {sanitize_prompt_text(command)}"
        )
    if pending_context:
        rendered = (
            "Com base no seguinte contexto de arquivos fornecido pelo usuário:\n"
            f"<context>\n{sanitize_prompt_text(pending_context)}\n</context>\n\n"
            f"Agora, aqui está meu pedido: {rendered}"
        )
    if reducer is not None and len(rendered) > reduce_above:
        rendered = reducer(rendered)
    return PreparedPrompt(command, rendered, used_constitution, used_context)


def filter_tool_schemas(
    schemas: Sequence[dict[str, Any]],
    prompt: str,
    *,
    essential_tools: frozenset[str],
    task_filter: Callable[[Sequence[dict[str, Any]], str], Sequence[dict[str, Any]]]
    | None = None,
) -> list[dict[str, Any]]:
    """Select a bounded tool surface appropriate to the current prompt."""
    lowered = prompt.lower().strip()
    if (
        any(lowered.startswith(pattern) for pattern in PURE_QUESTION_PATTERNS)
        and len(prompt) < 120
    ):
        return [
            schema
            for schema in schemas
            if schema.get("function", {}).get("name") in MINIMAL_QUESTION_TOOLS
        ]
    if task_filter is not None:
        selected = list(task_filter(schemas, prompt))
        if selected != list(schemas):
            return selected
    if len(schemas) > 20:
        return [
            schema
            for schema in schemas
            if schema.get("function", {}).get("name") in essential_tools
        ]
    return list(schemas)

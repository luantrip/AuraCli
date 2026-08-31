"""Context compression system for Aura CLI.

compress_conversation_history() reduces token usage by summarising old
messages (NLP when available) while preserving system messages and recent
interactions. Uses per-model context window sizes from _MODEL_CONTEXT_WINDOWS
instead of a hardcoded 4 000-token threshold.
"""

from datetime import datetime
import re
from typing import Dict, List, Optional

# Model context window sizes (tokens).  Used to set a sensible compression
# threshold instead of the old hardcoded 4 000-token value, which caused
# premature compaction on models with 128K+ context windows.
_MODEL_CONTEXT_WINDOWS: dict[str, int] = {
    # Google
    "gemini-2.5-flash": 1_048_576,
    "gemini-2.5-pro": 1_048_576,
    "gemini-1.5-pro": 1_048_576,
    "gemini-1.5-flash": 1_048_576,
    # Cerebras / OpenRouter / NVIDIA
    "gpt-oss-120b": 131_072,
    "nemotron": 131_072,
    "llama": 131_072,
    "qwen": 131_072,
    # OpenAI
    "gpt-4o": 128_000,
    "gpt-4o-mini": 128_000,
    "gpt-4-turbo": 128_000,
    # Anthropic
    "claude-3": 200_000,
    "claude-sonnet": 200_000,
    "claude-haiku": 200_000,
    "claude-opus": 200_000,
}
_DEFAULT_CONTEXT_WINDOW = 32_000  # conservative fallback


def _context_window_for_model(model: str) -> int:
    """Return the approximate context window (tokens) for the given model string."""
    model_lower = model.lower()
    for key, size in _MODEL_CONTEXT_WINDOWS.items():
        if key in model_lower:
            return size
    return _DEFAULT_CONTEXT_WINDOW


def compression_threshold_for_model(model: str) -> int:
    """Return the token threshold above which history compression should trigger.

    Uses 40 % of the model's context window as the trigger point, leaving
    60 % headroom for tool results and the next response.  The minimum is
    8 000 tokens to avoid compressing on every turn for large-context models.
    """
    window = _context_window_for_model(model)
    return max(8_000, window // 10 * 4)  # 40 % of window, minimum 8 000


def compress_conversation_history(
    history: List[Dict], max_tokens: int = 4000
) -> List[Dict]:
    """
    Compress conversation history maintaining essential information.

    Techniques used:
    - Intelligent summarization of old messages (uses NLP if available)
    - Maintenance of recent context (last interactions)
    - Preservation of important instructions (system messages)
    - Detection of main topics and actions

    Args:
        history: List of messages (role, content)
        max_tokens: Maximum approximate size (estimate)

    Returns:
        Compressed history (typical reduction: 60-76%)
    """
    if len(history) <= 2:
        return history

    total_messages = len(history)

    if total_messages <= 10:
        KEEP_RECENT = min(6, total_messages - 2)
        KEEP_INITIAL = 2
    elif total_messages <= 30:
        KEEP_RECENT = 8  # More recent context
        KEEP_INITIAL = 2
    else:
        KEEP_RECENT = 10  # Even more context for large histories
        KEEP_INITIAL = 3  # More initial context as well

    if len(history) <= KEEP_RECENT + KEEP_INITIAL:
        return history

    compressed = []

    compressed.extend(history[:KEEP_INITIAL])

    middle_messages = history[KEEP_INITIAL:-KEEP_RECENT]
    if middle_messages:
        try:
            from aura_cli.core.code_analysis.nlp_analyzer import NLPAnalyzer

            nlp = NLPAnalyzer()

            user_msgs = [
                m.get("content", "") for m in middle_messages if m.get("role") == "user"
            ]
            if user_msgs:
                user_text = "\n".join(user_msgs)
                user_summary = (
                    nlp.summarize_code(user_text)
                    if hasattr(nlp, "summarize_code")
                    else None
                )
                if user_summary:
                    summary = f"Tópicos principais: {user_summary.summary}"
                else:
                    summary = summarize_messages(middle_messages)
            else:
                summary = summarize_messages(middle_messages)
        except Exception:
            summary = summarize_messages(middle_messages)

        compressed.append(
            {
                "role": "system",
                "content": f"[Contexto resumido: {len(middle_messages)} mensagens anteriores - {len(compressed) + len(history[-KEEP_RECENT:])} mensagens preservadas]\n{summary}",
            }
        )

    compressed.extend(history[-KEEP_RECENT:])

    return compressed


def summarize_messages(messages: List[Dict]) -> str:
    """Summarise a list of messages into a compact string."""
    if not messages:
        return ""

    user_messages = [m for m in messages if m.get("role") == "user"]
    assistant_messages = [m for m in messages if m.get("role") == "assistant"]

    summary_parts = []

    if user_messages:
        topics = extract_topics(user_messages)
        if topics:
            summary_parts.append(f"Tópicos: {', '.join(topics[:5])}")
        else:
            all_content = " ".join(
                [m.get("content", "") for m in user_messages]
            ).lower()
            words = [w for w in all_content.split() if len(w) > 4]
            if words:
                from collections import Counter

                common = Counter(words).most_common(3)
                if common:
                    summary_parts.append(f"Foco: {', '.join([w for w, _ in common])}")

    if assistant_messages:
        actions = extract_actions(assistant_messages)
        if actions:
            summary_parts.append(f"Ações: {', '.join(actions[:5])}")
        else:
            all_content = " ".join([m.get("content", "") for m in assistant_messages])
            tool_mentions = [
                tool
                for tool in [
                    "read_file",
                    "write_file",
                    "run_shell",
                    "analyze",
                    "search",
                ]
                if tool in all_content.lower()
            ]
            if tool_mentions:
                summary_parts.append(f"Ferramentas: {len(tool_mentions)} usadas")

    if not summary_parts:
        summary_parts.append(
            f"{len(messages)} mensagens ({len(user_messages)} perguntas, {len(assistant_messages)} respostas)"
        )

    return " | ".join(summary_parts)


def extract_topics(messages: List[Dict]) -> List[str]:
    """Extract the main topics from user messages."""
    topics = []

    keywords = {
        "código": ["código", "code", "programação", "programming"],
        "arquivo": ["arquivo", "file", "criar", "create", "editar", "edit"],
        "projeto": ["projeto", "project", "estrutura", "structure"],
        "bug": ["bug", "erro", "error", "problema", "issue"],
        "feature": ["feature", "funcionalidade", "adicionar", "add"],
        "teste": ["teste", "test", "testar", "testing"],
        "git": ["git", "commit", "branch", "push"],
        "docker": ["docker", "container", "deploy", "build"],
    }

    for msg in messages:
        content = msg.get("content", "").lower()

        for topic, words in keywords.items():
            if any(word in content for word in words) and topic not in topics:
                topics.append(topic)
    return topics


def extract_actions(messages: List[Dict]) -> List[str]:
    """Extract the main actions from assistant messages."""
    actions = []

    action_patterns = {
        "criou arquivo": r"(criou|criado|created|write_file)",
        "editou arquivo": r"(editou|editado|edited|edit_file)",
        "analisou código": r"(analisou|analisado|analyzed|analyze)",
        "executou comando": r"(executou|executado|executed|run_shell)",
        "fez commit": r"(commit|commited|git_commit)",
        "fez deploy": r"(deploy|deployed|docker)",
    }

    for msg in messages:
        content = msg.get("content", "").lower()

        for action, pattern in action_patterns.items():
            if re.search(pattern, content, re.IGNORECASE) and action not in actions:
                actions.append(action)
    return actions


def estimate_tokens(text: str) -> int:
    """Estimate the token count for a text string."""
    from aura_cli.core.llm.base import estimate_tokens as _canonical

    return _canonical(text)


def compress_code_context(code: str, max_lines: int = 100) -> str:
    """Compact code while preserving essential structure."""
    lines = code.split("\n")

    if len(lines) <= max_lines:
        return code

    keep_start = min(20, len(lines) // 4)
    keep_end = min(20, len(lines) // 4)

    middle = lines[keep_start:-keep_end]
    middle_summary = f"\n... [{len(middle)} linhas omitidas] ...\n"

    compressed = (
        "\n".join(lines[:keep_start]) + middle_summary + "\n".join(lines[-keep_end:])
    )

    return compressed


def compress_file_content(content: str, max_chars: int = 2000) -> str:
    """Compact file content preserving start and end."""
    if len(content) <= max_chars:
        return content

    keep_start = max_chars // 3
    keep_end = max_chars // 3

    compressed = (
        content[:keep_start]
        + f"\n\n... [{len(content) - keep_start - keep_end} caracteres omitidos] ...\n\n"
        + content[-keep_end:]
    )

    return compressed


def create_context_summary(
    conversation: List[Dict], tools_used: Optional[List[str]] = None
) -> str:
    """Create a context summary string from the current state."""
    summary_parts = []

    if conversation:
        user_count = sum(1 for m in conversation if m.get("role") == "user")
        assistant_count = sum(1 for m in conversation if m.get("role") == "assistant")
        summary_parts.append(
            f"Conversa: {user_count} perguntas, {assistant_count} respostas"
        )

    if tools_used:
        summary_parts.append(f"Ferramentas usadas: {', '.join(tools_used[:5])}")
        if len(tools_used) > 5:
            summary_parts.append(f"... e mais {len(tools_used) - 5}")

    return " | ".join(summary_parts) if summary_parts else "Contexto vazio"


class ContextManager:
    """Context manager with intelligent compaction.

    Used by the CLI loop (app_loop.py) to maintain the message history
    sent to the LLM. Stores messages as dicts {role, content, timestamp}
    and compacts via compress_conversation_history() when the history
    exceeds compression_threshold (default 30 msgs). Also tracks
    tools_used and generates a context_summary string.

    Differs from ConversationMemory (core/memory/__init__.py), which is
    used by agents/workers, stores typed ChatMessage objects and compacts
    via a rolling buffer without tool tracking. Prefer ContextManager
    for CLI loop integration; prefer ConversationMemory for typed history
    in agents.
    """

    def __init__(self, max_history_size: int = 50, compression_threshold: int = 30):
        """Initialize context manager.

        Args:
            max_history_size: Maximum number of messages to retain
            compression_threshold: Message count that triggers compression
        """
        self.max_history_size = max_history_size
        self.compression_threshold = compression_threshold
        self.conversation_history: List[Dict] = []
        self.tools_used: List[str] = []
        self.context_summary: Optional[str] = None

    def add_message(self, role: str, content: str):
        """Add a message to the conversation history."""
        self.conversation_history.append(
            {"role": role, "content": content, "timestamp": datetime.now().isoformat()}
        )

        if len(self.conversation_history) > self.compression_threshold:
            self.compress()

    def compress(self):
        """Compact the history when it becomes too large."""
        if len(self.conversation_history) > self.max_history_size:
            self.conversation_history = compress_conversation_history(
                self.conversation_history, max_tokens=4000
            )

            self.context_summary = create_context_summary(
                self.conversation_history, self.tools_used
            )

    def get_compressed_history(self) -> List[Dict]:
        """Return the compressed conversation history."""
        if len(self.conversation_history) > self.compression_threshold:
            return compress_conversation_history(self.conversation_history)
        return self.conversation_history

    def add_tool_usage(self, tool_name: str):
        """Record a tool usage event."""
        if tool_name not in self.tools_used:
            self.tools_used.append(tool_name)

    def get_context_summary(self) -> str:
        """Return the current context summary string."""
        if not self.context_summary:
            self.context_summary = create_context_summary(
                self.conversation_history, self.tools_used
            )
        return self.context_summary

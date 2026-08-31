"""Pure shell-command normalization and safety policy."""

from __future__ import annotations

import re
import shlex


class ShellCommandResult(str):
    """String-compatible shell result carrying factual process evidence."""

    exit_code: int | None
    background: bool
    process_id: int | None

    def __new__(
        cls,
        output: str,
        *,
        exit_code: int | None,
        background: bool = False,
        process_id: int | None = None,
    ) -> ShellCommandResult:
        instance = super().__new__(cls, output)
        instance.exit_code = exit_code
        instance.background = background
        instance.process_id = process_id
        return instance


DANGEROUS_PATTERNS = (
    r"\$\(",
    r"`[^`]+`",
    r"\$\{",
    r">\s*/dev/",
    r">\s*/etc/",
    r">\s*/proc/",
    r";\s*rm\s+-rf",
    r"&&\s*rm\s+-rf",
    r"\|\s*sh\b",
    r"\|\s*bash\b",
    r"eval\s",
    r"exec\s",
)

BLOCKED_COMMANDS = frozenset(
    {
        "dd",
        "mkfs",
        "fdisk",
        "parted",
        "shutdown",
        "reboot",
        "halt",
        "init",
        "telinit",
        "systemctl",
        "service",
    }
)

_CATASTROPHIC_PATTERNS = (
    r"rm\s+(-[a-zA-Z]*r[a-zA-Z]*\s+(-[a-zA-Z]*\s+)*|(-[a-zA-Z]*f[a-zA-Z]*\s+(-[a-zA-Z]*\s+)*)*)(/\s*$|/\*)",
    r":\(\)\s*\{",
    r"mkfs\s+/dev/[a-z]",
    r"dd\s+.*of=/dev/[a-z]",
)

_AUTONOMOUS_BLOCKED_COMMANDS = frozenset(
    {
        *BLOCKED_COMMANDS,
        "doas",
        "rm",
        "sudo",
    }
)

_AUTONOMOUS_BLOCKED_PATTERNS = (
    r"\|\s*(sh|bash|zsh|fish|dash|ksh|csh)\b",
    r"\|\s*python[23]?\b",
    r"\|\s*perl\b",
    r"\|\s*ruby\b",
    r"(curl|wget)\s+.*\|\s*(sh|bash|python|perl)",
    r"(curl|wget)\s+.*-[oO]\s*-\s*&&",
    r"eval\s+[`\$\(]",
    r"exec\s+[`\$\(]",
    r">\s*/etc/(passwd|shadow|sudoers|crontab|hosts)",
    r">\s*~/\.ssh/(authorized_keys|config|id_)",
)


def sanitize_command(command: str) -> str:
    """Remove null/control characters and surrounding whitespace."""
    command = command.replace("\x00", "")
    return "".join(
        char for char in command if char.isprintable() or char in "\n\t"
    ).strip()


def _has_unquoted_logical_operator(command: str) -> bool:
    """Return whether ``&&`` or ``||`` appears outside a quoted argument."""
    in_single_quote = False
    in_double_quote = False
    index = 0
    while index < len(command):
        char = command[index]
        if char == "\\" and not in_single_quote and index + 1 < len(command):
            index += 2
            continue
        if char == "'" and not in_double_quote:
            in_single_quote = not in_single_quote
        elif char == '"' and not in_single_quote:
            in_double_quote = not in_double_quote
        elif (
            not in_single_quote
            and not in_double_quote
            and command[index : index + 2] in {"&&", "||"}
        ):
            return True
        index += 1
    return False


def has_safe_quoting(command: str) -> bool:
    """Reject dangerous characters outside balanced quotes."""
    dangerous_chars = {"|", "&", ";", "`", "$", "\n", "\r"}
    in_single_quote = False
    in_double_quote = False
    index = 0
    while index < len(command):
        char = command[index]
        if char == "\\" and index + 1 < len(command):
            index += 2
            continue
        if char == "'" and not in_double_quote:
            in_single_quote = not in_single_quote
        elif char == '"' and not in_single_quote:
            in_double_quote = not in_double_quote
        elif not in_single_quote and not in_double_quote and char in dangerous_chars:
            return False
        index += 1
    return not (in_single_quote or in_double_quote)


def _command_heads(command: str) -> list[str]:
    """Return executable names from the allowed logical command segments."""
    heads = []
    for segment in re.split(r"&&|\|\|", command):
        try:
            parts = shlex.split(segment)
        except ValueError:
            return []
        if parts:
            heads.append(parts[0].split("/")[-1].lower())
    return heads


def is_command_safe(command: str, *, autonomous: bool = False) -> bool:
    """Evaluate command safety without consulting global runtime state.

    Autonomous execution is never a bypass for the baseline policy. Logical
    composition with ``&&``/``||`` is rejected because the direct runners use
    argument execution (``shell=False``), not a shell parser. This prevents an
    operator from silently becoming a literal argument in one path and a
    control operator in another.
    """
    command = sanitize_command(command)
    if not command:
        return False
    if any(
        re.search(pattern, command, re.IGNORECASE) for pattern in _CATASTROPHIC_PATTERNS
    ):
        return False
    if _has_unquoted_logical_operator(command):
        return False
    try:
        parts = shlex.split(command)
    except ValueError:
        return False

    blocked_commands = _AUTONOMOUS_BLOCKED_COMMANDS if autonomous else BLOCKED_COMMANDS
    if any(head in blocked_commands for head in _command_heads(command)):
        return False
    if any(
        re.search(pattern, command, re.IGNORECASE) for pattern in DANGEROUS_PATTERNS
    ):
        return False
    if autonomous and any(
        re.search(pattern, command, re.IGNORECASE)
        for pattern in _AUTONOMOUS_BLOCKED_PATTERNS
    ):
        return False
    return bool(parts) and has_safe_quoting(command)

"""Response parsing for LLM tool calls.

This module handles extraction and parsing of tool calls from LLM responses.
Supports multiple formats:
    - OpenAI/LiteLLM: Standard format with message.tool_calls (array)
    - Legacy Format: message.function_call (backward compatibility)
    - Local LLM: XML tags <function_call>...</function_call> (Hugging Face)
"""

import json
import re
import time
from typing import Any, Dict, List, Optional, Tuple

from aura_cli.core.logger import get_logger

logger = get_logger(__name__)


def parse_tool_calls(message: Any) -> Optional[List[Any]]:
    """Extract tool calls from LLM message.

    Supports multiple formats:
        - OpenAI/LiteLLM: message.tool_calls
        - Legacy format: message.function_call
        - Local LLM: XML tags <function_call>...</function_call>

    Args:
        message: Message object from LLM response

    Returns:
        List of tool calls or None if none present
    """
    if hasattr(message, "tool_calls") and message.tool_calls:
        return message.tool_calls

    if hasattr(message, "function_call") and message.function_call:
        return [message.function_call]

    content = message.content if hasattr(message, "content") else str(message)
    if content and "<function_call>" in content and "</function_call>" in content:
        return _parse_local_llm_function_call(content, message)

    return None


def _parse_local_llm_function_call(content: str, message: Any) -> Optional[List[Dict]]:
    """Parse function call from local LLM (XML format).

    Extracts <function_call> and <arguments> tags from content and converts
    to standard format compatible with the rest of the system.

    Args:
        content: Message content
        message: Message object (will be modified to remove tags)

    Returns:
        List with one tool call in standard format or None
    """
    func_match = re.search(r"<function_call>(.*?)</function_call>", content)
    args_match = re.search(r"<arguments>(.*?)</arguments>", content)

    if not func_match or not args_match:
        return None

    function_name = func_match.group(1).strip()
    try:
        function_args = json.loads(args_match.group(1))
    except json.JSONDecodeError:
        logger.warning(
            f"Error parsing local LLM arguments: {args_match.group(1)}"
        )
        function_args = {}

    content = re.sub(r"<function_call>.*?</function_call>", "", content)
    content = re.sub(r"<arguments>.*?</arguments>", "", content)
    if hasattr(message, "content"):
        message.content = content.strip()

    return [
        {
            "id": f"local_call_{int(time.time() * 1000)}",
            "type": "function",
            "function": {"name": function_name, "arguments": json.dumps(function_args)},
        }
    ]


def extract_tool_call_data(tool_call: Any, call_index: int = 0) -> Tuple[str, str, str]:
    """Extract name, arguments, and ID from tool call.

    Supports multiple formats:
        - OpenAI object: tool_call.function.name
        - Dict: tool_call['function']['name']
        - Legacy format: tool_call.get('name')

    Args:
        tool_call: Tool call object or dict
        call_index: Call index (to generate ID if not present)

    Returns:
        Tuple (function_name, function_args_str, tool_call_id)

    Raises:
        ValueError: If unable to extract data from tool call
    """
    if hasattr(tool_call, "function"):
        function_name = tool_call.function.name
        function_args_str = tool_call.function.arguments
        tool_call_id = getattr(tool_call, "id", f"call_{call_index}")
        return function_name, function_args_str, tool_call_id

    if isinstance(tool_call, dict):
        if "function" in tool_call:
            function_name = tool_call["function"].get("name")
            function_args_str = tool_call["function"].get("arguments", "{}")
        else:
            function_name = tool_call.get("name") or tool_call.get("function", {}).get(
                "name"
            )
            function_args_str = tool_call.get("arguments") or tool_call.get(
                "function", {}
            ).get("arguments", "{}")
        tool_call_id = tool_call.get("id", f"call_{call_index}")

        if not function_name:
            raise ValueError(
                f"Não foi possível extrair nome da função do tool call: {tool_call}"
            )

        return function_name, function_args_str, tool_call_id

    if hasattr(tool_call, "get"):
        function_name = tool_call.get("name") or tool_call.get("function", {}).get(
            "name"
        )
        function_args_str = tool_call.get("arguments") or tool_call.get(
            "function", {}
        ).get("arguments", "{}")
        tool_call_id = tool_call.get("id", f"call_{call_index}")

        if not function_name:
            raise ValueError(
                f"Não foi possível extrair nome da função do tool call: {tool_call}"
            )

        return function_name, function_args_str, tool_call_id

    raise ValueError(f"Formato de tool call não suportado: {type(tool_call)}")

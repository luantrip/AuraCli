import pytest

from aura_cli.mcp.tool_adapter import ToolAdapter


def test_mcp_adapter_blocks_writes_by_default():
    adapter = ToolAdapter({"write": lambda: "ok"}, writable={"write"})
    with pytest.raises(PermissionError):
        adapter.call("write")
    assert adapter.call("write", allow_writes=True) == "ok"

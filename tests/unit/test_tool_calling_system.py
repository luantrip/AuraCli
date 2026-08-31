"""Testes para tool calling system."""


class TestToolCaller:
    """Testes para tool_caller."""

    def test_tool_caller_import(self):
        """Testa importação do tool caller."""
        from aura_cli.core.agents.tool_calling import tool_caller

        assert tool_caller is not None


class TestToolChain:
    """Testes para tool_chain."""

    def test_tool_chain_import(self):
        """Testa importação do tool chain."""
        from aura_cli.core.agents.tool_calling import tool_chain

        assert tool_chain is not None


class TestToolInterceptor:
    """Testes para tool_interceptor."""

    def test_tool_interceptor_import(self):
        """Testa importação do tool interceptor."""
        from aura_cli.core.agents.tool_calling import tool_interceptor

        assert tool_interceptor is not None


class TestToolPolicies:
    """Testes para tool_policies."""

    def test_tool_policies_import(self):
        """Testa importação do tool policies."""
        from aura_cli.core.agents.tool_calling import tool_policies

        assert tool_policies is not None


class TestToolValidator:
    """Testes para tool_validator."""

    def test_tool_validator_import(self):
        """Testa importação do tool validator."""
        from aura_cli.core.agents.tool_calling import tool_validator

        assert tool_validator is not None

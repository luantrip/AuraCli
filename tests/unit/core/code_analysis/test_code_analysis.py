"""Testes para code analysis."""


class TestNLPAnalyzer:
    """Testes para nlp_analyzer."""

    def test_nlp_analyzer_import(self):
        """Testa importação do módulo nlp_analyzer."""
        from aura_cli.core.code_analysis import nlp_analyzer

        assert nlp_analyzer is not None


class TestTokenizer:
    """Testes para tokenizer."""

    def test_tokenizer_import(self):
        """Testa importação do módulo tokenizer."""
        from aura_cli.core.code_analysis import tokenizer

        assert tokenizer is not None

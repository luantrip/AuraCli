"""Testes para context e validation."""


class TestContextCompression:
    """Testes para context/base.py."""

    def test_compress_conversation(self):
        """Testa compressão de conversação."""
        from aura_cli.core.context.base import compress_conversation_history

        messages = [
            {"role": "user", "content": "msg" * 100},
            {"role": "assistant", "content": "resp" * 100},
            {"role": "user", "content": "msg2"},
        ]

        result = compress_conversation_history(messages, max_tokens=500)

        assert isinstance(result, list)
        assert len(result) <= len(messages)


class TestVectorDB:
    """Testes para context/vector_db.py."""

    def test_vector_db_basic(self):
        """VectorDB é um módulo interno que delega ao backend configurado.
        Verifica que a importação não falha e que o módulo existe."""
        import importlib
        spec = importlib.util.find_spec("aura_cli.core.memory.vector_store")
        assert spec is not None, "vector_store module must be importable"


class TestValidation:
    """Testes para validation.py."""

    def test_validate_code_syntax(self, tmp_path):
        """Testa validação de sintaxe."""
        from aura_cli.core.validation import validate_code

        test_file = tmp_path / "test.py"
        test_file.write_text("print('hello')")

        result = validate_code(str(test_file), checks=["syntax"])

        assert result.passed

    def test_validate_code_syntax_invalid(self, tmp_path):
        """Testa validação de sintaxe inválida."""
        from aura_cli.core.validation import validate_code

        test_file = tmp_path / "test.py"
        test_file.write_text("print('hello'")  # Missing closing paren

        result = validate_code(str(test_file), checks=["syntax"])

        assert not result.passed


class TestStats:
    """Testes para stats.py."""

    def test_stats_init(self):
        """Testa inicialização de stats."""
        from aura_cli.core.stats import get_stats

        stats = get_stats()

        assert stats is not None

    def test_increment_counter(self):
        """Testa incremento de contador."""
        from aura_cli.core.stats import get_stats

        stats = get_stats()
        initial = stats.files_edited
        stats.increment_files_edited()

        assert stats.files_edited == initial + 1

    def test_add_tokens(self):
        """Testa adição de tokens."""
        from aura_cli.core.stats import get_stats

        stats = get_stats()
        initial = stats.tokens_used
        stats.add_tokens(
            {"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30}
        )

        assert stats.tokens_used > initial

    def test_get_summary(self):
        """Testa obtenção de resumo."""
        from aura_cli.core.stats import get_stats

        stats = get_stats()
        summary = stats.get_stats_summary()

        assert isinstance(summary, dict)


class TestCache:
    """Testes para cache.py."""

    def test_cache_decorator(self):
        """Testa decorator de cache."""
        from aura_cli.core.cache import cache_result

        @cache_result(ttl=60)
        def expensive_function(x):
            return x * 2

        result1 = expensive_function(5)
        result2 = expensive_function(5)

        assert result1 == 10
        assert result2 == 10

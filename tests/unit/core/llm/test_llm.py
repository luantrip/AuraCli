"""
Testes Unitários para Módulo LLM do Aura CLI.

Este módulo contém testes unitários que verificam o funcionamento individual
de funções base do sistema LLM, incluindo estimativa de tokens, truncamento
de conversações e queries com fallback automático entre modelos.

Componentes Testados:
    - estimate_tokens: Estimativa de número de tokens em texto
    - truncate_conversation: Truncamento de histórico de conversação
    - query_with_fallback: Query com fallback automático entre modelos

Cenários de Teste:
    - Estimativa de Tokens: Texto curto e longo
    - Truncamento: Preservação de mensagem de sistema
    - Query com Fallback: (Teste marcado como skip - requer API keys)

Validações:
    - Estimativa de tokens é precisa
    - Truncamento preserva mensagem de sistema
    - Query funciona com mocking

Estrutura de Testes:
    - TestLLMBase: Testes das funções base

Estimativa de Tokens:
    Utiliza aproximação baseada em:
    - Número de palavras
    - Caracteres especiais
    - Tokens de controle
    - Aproximação: ~4 caracteres por token

Truncamento de Conversação:
    Estratégia de truncamento:
    1. Preserva mensagem de sistema (sempre)
    2. Mantém mensagens recentes
    3. Remove mensagens antigas se necessário
    4. Respeita limite de tokens

Query com Fallback:
    Sistema de fallback automático:
    1. Tenta modelo primário
    2. Em caso de erro, tenta modelo secundário
    3. Continua até encontrar modelo disponível
    4. Retorna erro se todos falharem

Exemplo de Uso:
    ```python
    def test_tokens():
        tokens = estimate_tokens("Hello world")
        assert tokens > 0

        truncated = truncate_conversation(messages, max_tokens=50)
        assert truncated[0]["role"] == "system"
    ```

Dependências:
    - pytest: Framework de testes
    - unittest.mock: Para mocking de litellm
    - llm.base: Funções base de LLM
"""

from unittest.mock import Mock, patch

from aura_cli.core.llm.base import (
    estimate_tokens,
    query_with_fallback,
    truncate_conversation,
)


class TestLLMBase:
    """Testes para funções base de LLM."""

    def test_estimate_tokens(self):
        """Testa estimativa de tokens."""
        text = "Hello world"
        tokens = estimate_tokens(text)

        assert tokens > 0
        assert isinstance(tokens, int)

    def test_estimate_tokens_long_text(self):
        """Testa estimativa de tokens para texto longo."""
        text = "Hello world " * 100
        tokens = estimate_tokens(text)

        assert tokens > 100

    def test_truncate_conversation(self):
        """Testa truncamento de conversação."""
        messages = [
            {"role": "system", "content": "System message"},
            {"role": "user", "content": "User message 1"},
            {"role": "assistant", "content": "Assistant response 1"},
            {"role": "user", "content": "User message 2"},
        ]

        truncated = truncate_conversation(messages, max_tokens=50)

        assert len(truncated) <= len(messages)
        assert truncated[0]["role"] == "system"  # System sempre mantido

    def test_query_with_fallback(self):
        """Testa query com fallback."""
        messages = [{"role": "user", "content": "Hello"}]

        # Mock para não fazer chamada real
        with patch("aura_cli.core.llm.base._get_litellm") as get_litellm:
            mock_litellm = Mock()
            get_litellm.return_value = mock_litellm
            mock_response = Mock()
            mock_response.choices = [Mock()]
            mock_response.choices[0].message = Mock()
            mock_response.choices[0].message.content = "Hello!"
            mock_litellm.completion.return_value = mock_response

            result = query_with_fallback(
                "gpt-3.5-turbo",
                messages,
                fallback_models=["gpt-3.5-turbo"],
                max_retries=1,
                timeout=0.1,
                cross_provider_fallback=False,
            )

            assert result is not None

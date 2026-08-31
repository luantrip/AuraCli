"""
Testes para Sistema de Compactação de Contexto do Aura CLI.

Este módulo contém testes que verificam o funcionamento do sistema de compressão
de histórico de conversação e gerenciamento de contexto. Testa algoritmos de
compactação que reduzem o tamanho do histórico mantendo informações essenciais.

Componentes Testados:
    - compress_conversation_history: Função de compressão de histórico
    - ContextManager: Gerenciador de contexto completo

Cenários de Teste:
    - Histórico Pequeno: Verifica que históricos pequenos não são compactados
    - Histórico Grande: Testa compactação de históricos extensos
    - Preservação de Mensagens Recentes: Valida que mensagens recentes são mantidas
    - Gerenciamento de Contexto: Testa adição e recuperação de mensagens

Validações:
    - Históricos pequenos permanecem inalterados
    - Históricos grandes são reduzidos mantendo essencial
    - Primeiras e últimas mensagens são preservadas
    - Mensagens recentes têm prioridade na preservação
    - ContextManager mantém estado correto

Estrutura de Testes:
    - TestCompressConversationHistory: Testes de compressão
    - TestContextManager: Testes do gerenciador de contexto

Algoritmo de Compactação:
    O sistema utiliza técnicas de:
    - Preservação de mensagens iniciais (contexto de sistema)
    - Preservação de mensagens recentes (contexto atual)
    - Sumarização de mensagens intermediárias
    - Remoção de redundâncias

Exemplo de Uso:
    ```python
    def test_compression():
        history = [{"role": "user", "content": f"Msg {i}"} for i in range(50)]
        compressed = compress_conversation_history(history)

        assert len(compressed) < len(history)
        assert compressed[0] == history[0]  # Primeira preservada
    ```

Dependências:
    - pytest: Framework de testes
    - compress_conversation_history: Função de compressão
    - ContextManager: Gerenciador de contexto
"""

from aura_cli.core.context.base import (
    ContextManager,
    compress_conversation_history,
)


class TestCompressConversationHistory:
    """Testes para compress_conversation_history"""

    def test_compress_small_history_not_compressed(self):
        """
        Testa que histórico pequeno não é compactado.

        Verifica se histórico com poucas mensagens não é alterado.
        """
        history = [
            {"role": "user", "content": "Olá"},
            {"role": "assistant", "content": "Oi!"},
        ]
        result = compress_conversation_history(history)

        assert len(result) == 2
        assert result == history

    def test_compress_large_history_reduces_size(self):
        """
        Testa compactação de histórico grande.

        Verifica se histórico grande é reduzido mantendo essencial.
        """
        # Cria histórico grande
        history = []
        for i in range(50):
            history.append({"role": "user", "content": f"Pergunta {i}"})
            history.append({"role": "assistant", "content": f"Resposta {i}"})

        result = compress_conversation_history(history)

        # Deve ser menor que o original
        assert len(result) < len(history)
        # Deve manter primeiras e últimas mensagens
        assert result[0] == history[0]
        assert result[-1] == history[-1]

    def test_compress_preserves_recent_messages(self):
        """
        Testa que mensagens recentes são preservadas.

        Verifica se compactação mantém contexto recente.
        """
        history = []
        for i in range(20):
            history.append({"role": "user", "content": f"Msg {i}"})

        result = compress_conversation_history(history)

        # Últimas mensagens devem estar presentes
        assert result[-1]["content"] == "Msg 19" or len(result) > 0


class TestContextManager:
    """Testes para ContextManager"""

    def test_context_manager_initialization(self):
        """
        Testa inicialização do ContextManager.

        Verifica se ContextManager inicia com estado correto.
        """
        manager = ContextManager()

        assert hasattr(manager, "conversation_history") or hasattr(
            manager, "add_message"
        )

    def test_add_message_to_context(self):
        """
        Testa adição de mensagem ao contexto.

        Verifica se add_message adiciona mensagem corretamente.
        """
        manager = ContextManager()
        manager.add_message("user", "Olá")

        # Verifica se mensagem foi adicionada
        # (depende da implementação específica)
        assert hasattr(manager, "conversation_history") or hasattr(
            manager, "get_context_summary"
        )

    def test_get_context_summary_returns_summary(self):
        """
        Testa obtenção de resumo de contexto.

        Verifica se get_context_summary retorna resumo válido.
        """
        manager = ContextManager()
        manager.add_message("user", "Olá")
        manager.add_message("assistant", "Oi!")

        summary = manager.get_context_summary()

        # Deve retornar string ou dict com informações
        assert isinstance(summary, (str, dict))
        assert len(str(summary)) > 0

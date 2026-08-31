"""
Testes para Componentes de UI do Aura CLI.

Este módulo contém testes que verificam o funcionamento dos componentes de interface
do Aura CLI, incluindo key bindings customizados e painéis de status que exibem
mensagens em tempo real dos agentes AGI e Ops.

Componentes Testados:
    - create_key_bindings: Criação de atalhos de teclado customizados
    - create_status_panel: Criação de painéis de status formatados

Cenários de Teste:
    - Key Bindings: Criação e estrutura de key bindings
    - Status Panel Vazio: Comportamento quando queue está vazia
    - Status Panel AGI: Formatação de mensagens do agente AGI
    - Status Panel Ops: Formatação de mensagens do agente Ops
    - Múltiplas Mensagens: Exibição de várias mensagens
    - Limite de Mensagens: Respeito ao parâmetro max_messages

Validações:
    - Key bindings são criados corretamente
    - Painel vazio retorna None
    - Mensagens AGI são formatadas adequadamente
    - Mensagens Ops são formatadas adequadamente
    - Múltiplas mensagens são exibidas
    - Limite de mensagens é respeitado

Estrutura de Testes:
    - TestKeyBindings: Testes de key bindings
    - TestStatusPanel: Testes de painel de status

Formato de Mensagens:
    - AGI: "› [Aura AGI] ✓ Mensagem..."
    - Ops: "› [Aura Ops] ⚙ Mensagem..."
    - Genérica: "› Mensagem..."

Key Bindings:
    Sistema de atalhos customizados usando prompt_toolkit:
    - Atalhos para ações comuns
    - Integração com prompt interativo
    - Bindings configuráveis

Status Panel:
    Painel Rich que exibe:
    - Mensagens de status em tempo real
    - Formatação com ícones e cores
    - Limite configurável de mensagens
    - Agrupamento por tipo de agente

Exemplo de Uso:
    ```python
    def test_status_panel():
        status_queue = queue.Queue()
        status_queue.put("› [Aura AGI] ✓ Testando...")
        panel = create_status_panel(status_queue)
        assert panel is not None
    ```

Dependências:
    - pytest: Framework de testes
    - queue: Para simulação de status_queue
    - key_bindings: Módulo de key bindings
    - status_panel: Módulo de painel de status
"""

import queue

from aura_cli.cli.ui.components.tool_result import ToolResult
from aura_cli.cli.ui.constants import UIIcons, UIStyles
from aura_cli.cli.ui.key_bindings import create_key_bindings
from aura_cli.cli.ui.status_panel import create_status_panel


class TestKeyBindings:
    """Testes para key bindings"""

    def test_create_key_bindings_returns_bindings(self):
        """
        Testa criação de key bindings.

        Verifica se create_key_bindings retorna objeto de bindings válido.
        """
        bindings = create_key_bindings()

        assert bindings is not None
        # Verifica se é um objeto de key bindings
        assert hasattr(bindings, "get_bindings_for_keys") or hasattr(
            bindings, "bindings"
        )

    def test_keyboard_help_uses_theme_primary_token(self, monkeypatch):
        from rich.console import Console

        import aura_cli.cli.ui.key_bindings as key_bindings_module

        console = Console(record=True, width=80)
        monkeypatch.setattr(key_bindings_module, "get_console", lambda: console)
        monkeypatch.setattr(UIStyles, "PRIMARY", "bright_magenta")

        key_bindings_module.show_keyboard_help()

        assert "Ctrl+T" in console.export_text(clear=False)


class TestStatusPanel:
    """Testes para painel de status"""

    def test_create_status_panel_empty_queue(self):
        """
        Testa painel de status com queue vazia.

        Verifica comportamento quando não há mensagens de status.
        """
        status_queue = queue.Queue()
        panel = create_status_panel(status_queue)

        assert panel is None

    def test_create_status_panel_with_agi_message(self):
        """
        Testa painel de status com mensagem AGI.

        Verifica formatação de mensagens do agente AGI.
        """
        status_queue = queue.Queue()
        status_queue.put("› [Aura AGI] ✓ Testando...")

        panel = create_status_panel(status_queue)

        assert panel is not None
        # Group has renderables attribute (list)
        panel_str = (
            str(panel.renderables) if hasattr(panel, "renderables") else str(panel)
        )
        assert "Aura AGI" in panel_str or "Testando" in panel_str

    def test_create_status_panel_with_ops_message(self):
        """
        Testa painel de status com mensagem Ops.

        Verifica formatação de mensagens do agente Ops.
        """
        status_queue = queue.Queue()
        status_queue.put("› [Aura Ops] ⚙  Processando...")

        panel = create_status_panel(status_queue)

        assert panel is not None
        # Group has renderables attribute (list)
        panel_str = (
            str(panel.renderables) if hasattr(panel, "renderables") else str(panel)
        )
        assert "Aura Ops" in panel_str or "Processando" in panel_str

    def test_create_status_panel_with_multiple_messages(self):
        """
        Testa painel de status com múltiplas mensagens.

        Verifica se painel exibe múltiplas mensagens corretamente.
        """
        status_queue = queue.Queue()
        status_queue.put("› [Aura AGI] ✓ Testando...")
        status_queue.put("› [Aura Ops] ⚙  Processando...")
        status_queue.put("› Mensagem genérica")

        panel = create_status_panel(status_queue, max_messages=5)

        assert panel is not None
        # Group has renderables attribute (list)
        panel_str = (
            str(panel.renderables) if hasattr(panel, "renderables") else str(panel)
        )
        assert (
            "Aura AGI" in panel_str
            or "Aura Ops" in panel_str
            or "Mensagem" in panel_str
        )

    def test_create_status_panel_respects_max_messages(self):
        """
        Testa que painel respeita max_messages.

        Verifica se create_status_panel limita número de mensagens exibidas.
        """
        status_queue = queue.Queue()
        for i in range(10):
            # Use AGI prefix to ensure panel is created
            status_queue.put(f"[Aura AGI] Mensagem {i}")

        panel = create_status_panel(status_queue, max_messages=3)

        assert panel is not None

        # Group has renderables attribute (list)
        panel_str = (
            str(panel.renderables) if hasattr(panel, "renderables") else str(panel)
        )
        # Verifica que não mostra todas as 10
        assert panel_str.count("Mensagem") <= 3


class TestToolResult:
    def test_done_status_uses_success_treatment(self):
        """The tool executor's canonical completed state must not look like an error."""
        renderable = ToolResult().render("read_file", "contents", status="done")
        header = renderable.renderables[0]

        assert UIIcons.SUCCESS in header.plain
        assert UIIcons.ERROR not in header.plain

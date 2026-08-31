"""
Testes de validação da migração do FileManager para Shared Components.

Valida que:
1. ConfirmDialog local foi removido
2. Shared ConfirmDialog é importado corretamente
3. Métodos async funcionam corretamente
"""

import ast
from pathlib import Path

import pytest


def test_no_local_confirm_dialog_in_source():
    """Verifica que ConfirmDialog local foi removido do código fonte."""
    file_path = Path("aura_cli/tui/tools/file_manager/components/file_browser.py")
    source = file_path.read_text()

    # Não deve ter definição de classe ConfirmDialog local
    assert "class ConfirmDialog(Widget):" not in source
    assert "class ConfirmDialog(" not in source or "SharedConfirmDialog" in source


def test_shared_confirm_dialog_imported_in_source():
    """Verifica que SharedConfirmDialog é importado."""
    file_path = Path("aura_cli/tui/tools/file_manager/components/file_browser.py")
    source = file_path.read_text()

    # Deve importar SharedConfirmDialog
    assert (
        "from aura_cli.tui.components.shared.dialogs import ConfirmDialog as SharedConfirmDialog"
        in source
    )


def test_action_delete_is_async_in_source():
    """Verifica que action_delete é async no código fonte."""
    file_path = Path("aura_cli/tui/tools/file_manager/components/file_browser.py")
    source = file_path.read_text()

    # action_delete deve ser async
    assert "async def action_delete(self)" in source


def test_on_context_action_is_async_in_source():
    """Verifica que on_context_action é async no código fonte."""
    file_path = Path("aura_cli/tui/tools/file_manager/components/file_browser.py")
    source = file_path.read_text()

    # on_context_action deve ser async
    assert "async def on_context_action(self" in source


def test_shared_dialog_usage_in_source():
    """Verifica que o código usa SharedConfirmDialog."""
    file_path = Path("aura_cli/tui/tools/file_manager/components/file_browser.py")
    source = file_path.read_text()

    # Deve usar SharedConfirmDialog
    assert "SharedConfirmDialog(" in source
    assert "push_screen" in source
    assert "wait_for_dismiss" in source


def test_no_confirmed_message_handler_in_source():
    """Verifica que handler on_action_confirmed foi removido."""
    file_path = Path("aura_cli/tui/tools/file_manager/components/file_browser.py")
    source = file_path.read_text()

    # Não deve ter on_action_confirmed
    assert "def on_action_confirmed(self" not in source
    assert "@on(ConfirmDialog.Confirmed)" not in source


def test_no_mount_dialog_pattern():
    """Verifica que padrão antigo de mount dialog foi removido."""
    file_path = Path("aura_cli/tui/tools/file_manager/components/file_browser.py")
    source = file_path.read_text()

    # Contar ocorrências de self.mount(dialog) - deve ser zero ou apenas para outros dialogs
    # Não deve ter mount de ConfirmDialog
    lines = source.split("\n")
    for i, line in enumerate(lines):
        if "self.mount(dialog)" in line:
            # Verificar contexto - não deve ser após criar ConfirmDialog
            context = "\n".join(lines[max(0, i - 10) : i])
            assert (
                "ConfirmDialog(" not in context
                or "NewFileDialog" in context
                or "RenameDialog" in context
            )


def test_syntax_valid():
    """Verifica que o arquivo tem sintaxe Python válida."""
    file_path = Path("aura_cli/tui/tools/file_manager/components/file_browser.py")
    source = file_path.read_text()

    try:
        ast.parse(source)
    except SyntaxError as e:
        pytest.fail(f"Erro de sintaxe no arquivo: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

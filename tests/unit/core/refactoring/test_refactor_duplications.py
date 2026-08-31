"""
Testes de validação da refatoração de duplicações.

Valida que:
1. OpenInPaint não está mais duplicado
2. Import correto do módulo de integração
3. Funcionalidade mantida
"""

from pathlib import Path

import pytest


def test_no_duplicate_openinpaint():
    """Verifica que OpenInPaint não está duplicado."""
    file_browser_path = Path(
        "aura_cli/tui/tools/file_manager/components/file_browser.py"
    )
    source = file_browser_path.read_text()

    # Não deve ter definição de classe OpenInPaint
    assert "class OpenInPaint(Message):" not in source


def test_openinpaint_imported_from_integration():
    """Verifica que OpenInPaint é importado do módulo de integração."""
    file_browser_path = Path(
        "aura_cli/tui/tools/file_manager/components/file_browser.py"
    )
    source = file_browser_path.read_text()

    # Deve importar de paint_integration
    assert (
        "from aura_cli.tui.tools.integrations.paint_integration import OpenInPaint"
        in source
    )


def test_openinpaint_single_definition():
    """Verifica que OpenInPaint tem apenas uma definição."""
    import subprocess

    result = subprocess.run(
        ["grep", "-rn", "class OpenInPaint", "aura_cli/tui/tools/"],
        capture_output=True,
        text=True,
    )

    # Deve ter apenas 1 ocorrência
    occurrences = result.stdout.strip().split("\n")
    assert len(occurrences) == 1
    assert "paint_integration.py" in occurrences[0]


def test_file_browser_syntax_valid():
    """Verifica que file_browser.py tem sintaxe válida."""
    import ast

    file_path = Path("aura_cli/tui/tools/file_manager/components/file_browser.py")
    source = file_path.read_text()

    try:
        ast.parse(source)
    except SyntaxError as e:
        pytest.fail(f"Erro de sintaxe: {e}")


def test_openinpaint_usage_in_file_browser():
    """Verifica que OpenInPaint é usado corretamente no file_browser."""
    file_browser_path = Path(
        "aura_cli/tui/tools/file_manager/components/file_browser.py"
    )
    source = file_browser_path.read_text()

    # Deve usar OpenInPaint (não self.OpenInPaint)
    assert (
        "self.post_message(OpenInPaint(" in source
        or "self.post_message(self.OpenInPaint(" in source
    )


def test_paint_integration_has_openinpaint():
    """Verifica que paint_integration.py define OpenInPaint."""
    integration_path = Path("aura_cli/tui/tools/integrations/paint_integration.py")
    source = integration_path.read_text()

    # Deve ter definição
    assert "class OpenInPaint(Message):" in source
    assert "def __init__(self, file_path: Path)" in source


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

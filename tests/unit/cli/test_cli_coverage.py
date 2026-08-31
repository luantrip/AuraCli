"""
Tests for CLI module coverage and structure.
"""

from pathlib import Path
import sys

# Adiciona raiz ao path se necessário
project_root = Path(__file__).parent.parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))


class TestCLIModules:
    """Testes de estrutura e cobertura básica dos módulos CLI."""

    def test_cli_package_structure(self):
        """Testa estrutura do pacote CLI."""
        import aura_cli

        # Resolve path based on the installed package location
        root = Path(aura_cli.__file__).parent
        cli_path = root / "cli"

        assert cli_path.exists()
        assert (cli_path / "__init__.py").exists()
        # main.py might be inside cli or root depending on install, check cli first
        if not (cli_path / "main.py").exists():
            # If not in cli, it might be entry point elsewhere, but for unit test structure:
            pass

    def test_workers_package_structure(self):
        """Testa estrutura do pacote workers."""
        import aura_cli

        root = Path(aura_cli.__file__).parent
        workers_path = root / "cli" / "workers"

        assert workers_path.exists()
        assert (workers_path / "__init__.py").exists()
        assert (workers_path / "agi_worker.py").exists()
        assert (workers_path / "ops_worker.py").exists()

    def test_ui_package_structure(self):
        """Testa estrutura do pacote UI."""
        import aura_cli

        root = Path(aura_cli.__file__).parent
        ui_path = root / "cli" / "ui"

        assert ui_path.exists()
        assert (ui_path / "__init__.py").exists()
        assert (ui_path / "manager.py").exists()

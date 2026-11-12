"""UI contracts: icon vocabulary, English wizard, and console ownership in core.

Contracts:
- The setup wizard (first_run.py) must be fully English.
- UIIcons must not define unused symbols; referenced symbols must be defined.
- core/ops_tools tools must not own a module-level ``console = Console()``
  (except docker, which has a documented streaming exception).
"""

from __future__ import annotations

import ast
from pathlib import Path
import re

REPO = Path(__file__).parent.parent.parent
PRODUCT = REPO / "aura_cli"


# ─────────────────────────────────────────────────────────────────────────────
# --- Wizard language contracts ---
# ─────────────────────────────────────────────────────────────────────────────

# These patterns are characteristic Portuguese UI strings; none must appear in
# the wizard source after the EN migration.
_PT_WIZARD_PATTERNS = [
    "Bem-vindo",
    "Vamos configurar",
    "gratuitos",
    "recomendamos",
    "Configurar os",
    "Escolher apenas",
    "Obtenha sua key",
    "Entrada oculta",
    "Nenhum provider",
    "Fallback parcial",
    "Setup completo!",
    "Dica: configure mais",
    "provider configurado",
    "Nenhuma key",
    "pulado",
]


class TestWizardIsEnglish:
    def test_no_portuguese_ui_strings_in_first_run(self) -> None:
        source = (PRODUCT / "cli" / "first_run.py").read_text(encoding="utf-8")
        # Strip comments and docstrings (rough: look only in string literals)
        violations = []
        for pattern in _PT_WIZARD_PATTERNS:
            if pattern in source:
                violations.append(pattern)
        assert violations == [], (
            f"Portuguese UI strings still in first_run.py: {violations}"
        )

    def test_welcome_banner_is_english(self) -> None:
        source = (PRODUCT / "cli" / "first_run.py").read_text(encoding="utf-8")
        assert "Welcome to Aura CLI" in source
        assert "Let's set up" in source

    def test_mode_choices_are_english(self) -> None:
        source = (PRODUCT / "cli" / "first_run.py").read_text(encoding="utf-8")
        assert "Set up the 4 free providers" in source
        assert "Choose a single provider" in source


# ─────────────────────────────────────────────────────────────────────────────
# --- Icon vocabulary contracts ---
# ─────────────────────────────────────────────────────────────────────────────


class TestUIIconsVocabulary:
    def _defined(self) -> set[str]:
        from aura_cli.cli.ui.constants import UIIcons

        return {
            name for name in dir(UIIcons) if name.isupper() and not name.startswith("_")
        }

    def _referenced(self) -> set[str]:
        """All ``UIIcons.<NAME>`` references in product code."""
        refs: set[str] = set()
        for source in sorted(PRODUCT.rglob("*.py")):
            for m in re.finditer(
                r"UIIcons\.([A-Z_]+)\b", source.read_text(encoding="utf-8")
            ):
                refs.add(m.group(1))
        return refs

    def test_all_referenced_icons_are_defined(self) -> None:
        """No ``UIIcons.X`` reference without a definition (no type: ignore needed)."""
        missing = self._referenced() - self._defined()
        assert missing == set(), (
            f"Referenced but not defined: {missing} — add them to UIIcons or "
            "fix the call sites"
        )

    def test_unused_icons_are_not_defined(self) -> None:
        """Symbols not referenced anywhere in product code must not exist.

        Allowed exceptions: method names (lowercase) and ASCII_MODE (config flag).
        """
        defined = self._defined() - {"ASCII_MODE"}
        # some icons may be used only in tests — exclude test references
        product_refs: set[str] = set()
        for source in sorted(PRODUCT.rglob("*.py")):
            for m in re.finditer(
                r"UIIcons\.([A-Z_]+)\b", source.read_text(encoding="utf-8")
            ):
                product_refs.add(m.group(1))

        unused = defined - product_refs
        assert unused == set(), (
            f"Defined but never used in product code: {sorted(unused)} — "
            "remove them from UIIcons"
        )

    def test_workflow_is_defined_and_usable_without_type_ignore(self) -> None:
        """WORKFLOW was previously missing, causing a type: ignore comment."""
        from aura_cli.cli.ui.constants import UIIcons

        # direct attribute access must work
        glyph = UIIcons.WORKFLOW
        assert isinstance(glyph, str) and glyph

        # no type: ignore for WORKFLOW in management.py
        mgmt = (PRODUCT / "cli" / "commands" / "management.py").read_text(
            encoding="utf-8"
        )
        lines_with_workflow = [line for line in mgmt.splitlines() if "WORKFLOW" in line]
        type_ignores = [line for line in lines_with_workflow if "type: ignore" in line]
        assert type_ignores == [], f"WORKFLOW still has type: ignore: {type_ignores}"


# ─────────────────────────────────────────────────────────────────────────────
# --- Console ownership contracts ---
# ─────────────────────────────────────────────────────────────────────────────


_DOCKER_EXCEPTION = PRODUCT / "core" / "ops_tools" / "docker" / "__init__.py"

# Files allowed to have a module-level Console() — documented exceptions.
# is a known debt that must NOT grow; the goal is to shrink this set over time.
# Removing a file from this list without fixing it breaks the contract.
_PE10_BASELINE: frozenset[str] = frozenset(
    {
        "aura_cli/core/agents/agent_base.py",
        "aura_cli/core/agents/agent_orchestrator.py",
        "aura_cli/core/agents/agent_workflow.py",
        "aura_cli/core/code_analysis/nlp_analyzer.py",
        "aura_cli/core/code_analysis/tokenizer.py",
        "aura_cli/core/edit/edit_executor.py",
        "aura_cli/core/edit/multi_edit.py",
        "aura_cli/core/testing/coverage.py",
        "aura_cli/core/testing/test_runner_advanced.py",
        "aura_cli/core/tools/cloud_ops.py",
        "aura_cli/core/tools/codebase_tools.py",
        "aura_cli/core/tools/dev_tools.py",
        "aura_cli/core/visualization/visualization.py",
    }
)


class TestCoreDoesNotOwnConsole:
    def _module_level_console_owners(self) -> set[str]:
        """Return core/ files that define a module-level ``console = Console()``."""
        owners: set[str] = set()
        for source in sorted((PRODUCT / "core").rglob("*.py")):
            if source == _DOCKER_EXCEPTION:
                continue  # streaming by design
            text = source.read_text(encoding="utf-8")
            tree = ast.parse(text, filename=str(source))
            for node in tree.body:  # module-level only
                if not isinstance(node, ast.Assign):
                    continue
                value = node.value
                if not (
                    isinstance(value, ast.Call)
                    and isinstance(value.func, ast.Name)
                    and value.func.id == "Console"
                ):
                    continue
                targets = [t.id for t in node.targets if isinstance(t, ast.Name)]
                if any("console" in tgt.lower() for tgt in targets):
                    owners.add(str(source.relative_to(REPO)))
        return owners

    def test_no_new_module_level_console_in_core(self) -> None:
        """New core/ files must not add a module-level Console().

        PE-10 is a ratchet: the baseline set shrinks over time but never grows.
        """
        current = self._module_level_console_owners()
        new_owners = current - _PE10_BASELINE
        assert new_owners == set(), (
            f"New module-level Console() added in core/ (docker is exempt): "
            f"{sorted(new_owners)}"
        )

    def test_pe10_baseline_only_shrinks(self) -> None:
        """If a baseline file was cleaned up, remove it from the baseline set."""
        current = self._module_level_console_owners()
        stale = _PE10_BASELINE - current
        assert stale == set(), (
            f"These files no longer own Console() — remove them from "
            f"_PE10_BASELINE: {sorted(stale)}"
        )

    def test_docker_exception_is_documented(self) -> None:
        """The docker module is the only streaming-allowed Console() owner."""
        assert _DOCKER_EXCEPTION.exists(), "docker __init__.py must still exist"
        text = _DOCKER_EXCEPTION.read_text(encoding="utf-8")
        assert "Console()" in text, (
            "docker streaming uses Console() — if removed, update PE-10 contract"
        )

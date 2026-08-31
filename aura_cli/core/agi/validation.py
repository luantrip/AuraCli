"""
AgiValidator Module.

This module encapsulates validation logic for the AGI Agent, including:
- Constitution validation
- Auto-validation of generated files (linters)
- Adversarial validation (using TesterWorker)
- Learned rules consolidation
"""

import logging
import os
from pathlib import Path
import re
from typing import Any, Dict, List, Optional

from aura_cli.core.memory.constitution_validator import ConstitutionValidator
from aura_cli.core.ui_bridge import UIIcons

logger = logging.getLogger(__name__)


class AgiValidator:
    """
    Handles validation responsibilities for the AGI Worker.
    """

    def __init__(
        self,
        constitution: Optional[str],
        agi_event_adapter: Any,
        linter_manager: Any = None,
        memory_service: Any = None,
        session_state: Any = None,
        tester_worker_class: Any = None,
        headless: bool = False,
    ):
        """Initialize the instance."""
        self.constitution = constitution
        self.agi_event_adapter = agi_event_adapter
        self.linter_manager = linter_manager
        self.memory_service = memory_service
        self.session_state = session_state
        self.tester_worker_class = tester_worker_class
        self.headless = headless

        if self.constitution:
            self.constitution_validator = ConstitutionValidator(self.constitution)
        else:
            self.constitution_validator = None  # type: ignore[assignment]

        self.learned_rules: list[Any] = []

    def validate_and_sanitize_prompt(self, prompt: str) -> str:
        """
        Validates and sanitizes user prompt against the Constitution.

        Args:
            prompt: Original user prompt

        Returns:
            Sanitized and validated prompt
        """
        if not self.constitution or not self.constitution_validator:
            return prompt

        is_valid, violations, sanitized = self.constitution_validator.validate_prompt(
            prompt
        )

        if not is_valid and violations:
            violation_msg = (
                f"› [Aura AGI] {UIIcons.WARNING} "
                f"Violações da Constituição detectadas ({len(violations)}):"
            )
            self.agi_event_adapter.emit_chat_message(
                sender="system",
                content=violation_msg,
            )

            for violation in violations:
                self.agi_event_adapter.emit_chat_message(
                    sender="system",
                    content=f"  ⚠️  {violation}",
                )

            critical_conflict = self.constitution_validator.check_conflict(prompt)
            if critical_conflict:
                self.agi_event_adapter.emit_chat_message(
                    sender="system",
                    content=f"› [Aura AGI] {UIIcons.ERROR} {critical_conflict}",
                )
                logger.warning(
                    f"Critical constitution violation detected: {violations}"
                )

            if sanitized:
                return sanitized

        sanitized_prompt = (
            f"Baseado na Constituição do Projeto (que já está no seu contexto de sistema), "
            f"processe o seguinte pedido:\n\n{prompt}"
        )
        logger.info("User prompt sanitized with Constitution for AGI")
        return sanitized_prompt

    def extract_learned_rules_from_response(self, response_content: str) -> None:
        """
        Extracts learned rules from agent response.
        """
        if not response_content or not self.constitution:
            return

        patterns = [
            (
                r"(?:decidimos|vamos usar|escolhemos|adotamos|we decided|we'll use|we chose|we adopted)\s+([^\.]+)",
                "decisão",
            ),
            (
                r"(?:padrão|convenção|regra|pattern|convention|rule|standard)\s+([^\.]+)",
                "padrão",
            ),
            (
                r"(?:não usar|evitar|proibido|avoid|don't use|never use|forbidden)\s+([^\.]+)",
                "proibição",
            ),
        ]

        for pattern, category in patterns:
            matches = re.findall(pattern, response_content, re.IGNORECASE)
            for match in matches:
                if len(match.strip()) > 10:  # Filter very short matches
                    self.learned_rules.append(
                        {
                            "category": category,
                            "content": match.strip(),
                            "source": "agent_response",
                        }
                    )

    def consolidate_learned_rules(self, config_manager: Any) -> None:
        """
        Consolidates learned rules into Master Notebook via MemoryService.
        """
        if not self.learned_rules or not self.constitution or not self.memory_service:
            return

        try:
            for rule in self.learned_rules:
                rule_text = rule.get("content", "")
                rule_context = rule.get("category", "Regra Geral")
                if rule_text:
                    self.memory_service.add_learned_rule(
                        rule=rule_text, context=rule_context, source="agi"
                    )

            rules_count = len(self.learned_rules)
            logger.info(f"{rules_count} learned rules saved via memory service")

            if not self.headless:
                self.agi_event_adapter.emit_chat_message(
                    sender="system",
                    content=(
                        f"› [Aura AGI] {UIIcons.INFO} "
                        f"{rules_count} regra(s) aprendida(s) salva(s)"
                    ),
                )

            auto_consolidation = config_manager.get("auto_consolidation", False)

            if auto_consolidation:
                if self.memory_service.consolidate_rules():
                    self.constitution = self.memory_service.get_constitution()
                    self.constitution_validator = ConstitutionValidator(
                        self.constitution
                    )

                    if self.session_state:
                        self.session_state.update_constitution(self.constitution)

                    if not self.headless:
                        self.agi_event_adapter.emit_chat_message(
                            sender="system",
                            content=(
                                f"› [Aura AGI] {UIIcons.SUCCESS} "
                                f"Regras consolidadas na Constituição do Projeto"
                            ),
                        )
            else:
                if not self.headless:
                    self.agi_event_adapter.emit_chat_message(
                        sender="system",
                        content=(
                            f"› [Aura AGI] {UIIcons.INFO} "
                            f"{rules_count} regra(s) salva(s) no Rascunho. "
                            f"Use '/consolidate' para consolidar na Constituição."
                        ),
                    )

            self.learned_rules = []

        except Exception as e:
            logger.error(f"Failed to consolidate learned rules: {e}", exc_info=True)

    def auto_validate_generated_files(self, generated_files: List[str]) -> None:
        """
        Automatically validates generated files using linters.
        """
        if not generated_files or not self.linter_manager:
            return

        file_paths = [Path(f) for f in generated_files if Path(f).exists()]
        if not file_paths:
            return

        validation_results = self.linter_manager.validate_generated_files(file_paths)

        errors_found = []
        valid_files = []

        for file_path_str, (is_valid, error_msg) in validation_results.items():
            file_path = Path(file_path_str)
            if is_valid:
                valid_files.append(file_path.name)
            else:
                errors_found.append((file_path.name, error_msg))

        if valid_files and not errors_found:
            if not self.headless:
                self.agi_event_adapter.emit_chat_message(
                    sender="system",
                    content=(
                        f"› [Aura AGI] {UIIcons.SUCCESS} "
                        f"Código gerado validado com sucesso! "
                        f"Nenhum erro de sintaxe encontrado em {len(valid_files)} arquivo(s)."
                    ),
                )
            logger.info(f"Auto-validation passed for {len(valid_files)} files")
        elif errors_found:
            error_summary = f"Encontrados erros em {len(errors_found)} arquivo(s):\n"
            for file_name, error_msg in errors_found[:3]:
                error_summary += f"  • {file_name}: {error_msg[:100]}...\n"

            if not self.headless:
                self.agi_event_adapter.emit_chat_message(
                    sender="system",
                    content=(
                        f"› [Aura AGI] {UIIcons.WARNING} "
                        f"Validação automática detectou erros:\n{error_summary}"
                        f"Recomendação: Revise o código gerado antes de usar."
                    ),
                )
            logger.warning(f"Auto-validation found errors in {len(errors_found)} files")

    def run_adversarial_validation(
        self,
        files_to_validate: List[str],
        model: str,
        api_keys: dict,
        available_tools: dict,
        status_queue: Any,
    ) -> Optional[Dict[str, Any]]:
        """
        Execute adversarial validation on generated/modified files using TesterWorker.
        """
        if not self.tester_worker_class:
            logger.debug(
                "TesterWorker class not provided, skipping adversarial validation"
            )
            return None

        if not files_to_validate:
            logger.debug("No files to validate")
            return None

        self.agi_event_adapter.emit_chat_message(
            sender="agent",
            content=f"› [Aura AGI] {UIIcons.THINKING} Iniciando validação adversária de {len(files_to_validate)} arquivo(s)...",
        )

        validation_results = []

        for file_path in files_to_validate[:5]:  # Limit to 5 files
            if not os.path.exists(file_path):
                continue

            code_extensions = {
                ".py",
                ".js",
                ".ts",
                ".jsx",
                ".tsx",
                ".java",
                ".go",
                ".rs",
                ".rb",
                ".php",
                ".c",
                ".cpp",
                ".h",
            }
            if not any(file_path.endswith(ext) for ext in code_extensions):
                continue

            try:
                self.agi_event_adapter.emit_chat_message(
                    sender="agent",
                    content=f"› [TesterWorker] {UIIcons.WORKING} Analisando: {os.path.basename(file_path)}",
                )

                tester = self.tester_worker_class(
                    code_to_test=file_path,
                    model=model,
                    api_keys=api_keys,
                    available_tools=available_tools,
                    test_mode="all",
                    headless=True,
                    status_queue=status_queue,
                    file_path=file_path,
                )

                tester.start()
                tester.join(timeout=120)

                if tester.is_alive():
                    logger.warning(f"TesterWorker timeout for {file_path}")
                    continue

                result = tester.get_result(timeout=5.0)

                if result.get("status") == "completed":
                    issues = result.get("issues_found", [])
                    tests = result.get("tests_generated", [])

                    validation_results.append(
                        {
                            "file": file_path,
                            "issues_count": len(issues),
                            "tests_count": len(tests),
                            "issues": issues[:5],
                            "analysis": result.get("analysis", "")[:500],
                        }
                    )

                    if issues:
                        high_severity = sum(
                            1 for i in issues if i.get("severity") == "high"
                        )
                        self.agi_event_adapter.emit_chat_message(
                            sender="agent",
                            content=f"› [TesterWorker] {UIIcons.WARNING} {os.path.basename(file_path)}: "
                            f"{len(issues)} problema(s) ({high_severity} alta severidade), "
                            f"{len(tests)} teste(s) sugerido(s)",
                        )
                    else:
                        self.agi_event_adapter.emit_chat_message(
                            sender="agent",
                            content=f"› [TesterWorker] {UIIcons.SUCCESS} {os.path.basename(file_path)}: "
                            f"Nenhum problema crítico encontrado",
                        )

            except Exception as e:
                logger.error(
                    f"Error in adversarial validation of {file_path}: {e}",
                    exc_info=True,
                )
                self.agi_event_adapter.emit_chat_message(
                    sender="agent",
                    content=f"› [TesterWorker] {UIIcons.ERROR} Error validating {os.path.basename(file_path)}: {e}",
                )

        if validation_results:
            total_issues = sum(r["issues_count"] for r in validation_results)
            total_tests = sum(r["tests_count"] for r in validation_results)

            self.agi_event_adapter.emit_chat_message(
                sender="agent",
                content=f"› [Aura AGI] {UIIcons.INFO} Validação concluída: "
                f"{total_issues} problema(s) em {len(validation_results)} arquivo(s), "
                f"{total_tests} teste(s) sugerido(s)",
            )

            return {
                "status": "completed",
                "files_validated": len(validation_results),
                "total_issues": total_issues,
                "total_tests": total_tests,
                "results": validation_results,
            }

        return None

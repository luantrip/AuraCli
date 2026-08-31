"""
AgiContextManager Module.

This module helps the AGI Agent understand the project environment.
It handles:
- Gathering "instant" project context via Imagination Engine (files, stats, stacks).
- Managing the "Project Constitution" (immutable rules).
- Injecting Consciousness (Skills/Personas) into system prompts.
"""

import hashlib
import logging
from pathlib import Path
import time
from typing import Any, Optional

from aura_cli.application.artifacts import ArtifactLayout
from aura_cli.core.agi.evidence_tree import EvidenceTree
from aura_cli.core.state.project_state import ProjectState
from aura_cli.core.tools.imagination_tools import ScanOptions
from aura_cli.core.ui_bridge import UIIcons

logger = logging.getLogger(__name__)


class AgiContextManager:
    """
    Manages project context, constitution, and consciousness injection.
    """

    def __init__(
        self,
        project_root: Any,
        constitution: Optional[str],
        agi_event_adapter: Any,
        imagination_scanner: Any = None,
        consciousness_manager: Any = None,
    ):
        """Initialize the instance."""
        self.project_root = project_root
        self.constitution = constitution
        self.agi_event_adapter = agi_event_adapter
        self.imagination_scanner = imagination_scanner
        self.consciousness_manager = consciousness_manager
        self._context_cache: Optional[str] = None
        self._context_cache_ts: float = 0.0
        self._CONTEXT_CACHE_TTL = 60.0  # seconds
        self.evidence_tree: Optional[EvidenceTree] = None

    def prepare_evidence(self, task: str) -> str:
        """Materialize a bounded per-task evidence tree and return its pointer."""
        task_id = hashlib.sha256(task.encode("utf-8")).hexdigest()[:16]
        root = ArtifactLayout(project_root=Path(self.project_root)).project("agi", task_id)
        self.evidence_tree = EvidenceTree(root, task_id)
        self.evidence_tree.build(task)
        return self.evidence_tree.mission_pointer()

    def get_instant_project_context(self) -> str:
        """
        Generate instant project context using the Imagination Engine.

        Returns:
            Formatted string with project context for injection into system prompt
        """
        if not self.imagination_scanner:
            return ""

        now = time.monotonic()
        if (
            self._context_cache is not None
            and (now - self._context_cache_ts) < self._CONTEXT_CACHE_TTL
        ):
            return self._context_cache

        try:
            options = ScanOptions(
                include_preview=False,
                max_depth=4,
                include_hidden=False,
                respect_gitignore=True,
            )
            result = self.imagination_scanner.scan(".", options, use_cache=True)

            context_parts = []
            context_parts.append(
                "\n**📁 PROJECT CONTEXT (Auto-detected by Imagination Engine):**"
            )
            context_parts.append(f"- Total Files: {result.total_files:,}")
            context_parts.append(f"- Total Lines of Code: {result.total_lines:,}")
            context_parts.append(f"- Total Size: {result.total_size_human}")
            context_parts.append(f"- Directories: {result.total_directories:,}")

            if result.by_category:
                context_parts.append("\n**Technologies Detected:**")
                for cat, count in sorted(
                    result.by_category.items(), key=lambda x: -x[1]
                ):
                    if count > 0 and cat != "binary":
                        context_parts.append(f"  - {cat}: {count} files")

            if result.by_extension:
                top_exts = sorted(result.by_extension.items(), key=lambda x: -x[1])[:5]
                main_langs = ", ".join([f"{ext}({count})" for ext, count in top_exts])
                context_parts.append(f"\n**Main Extensions:** {main_langs}")

            key_files = []
            important_files = [
                "README.md",
                "readme.md",
                "README",
                "pyproject.toml",
                "setup.py",
                "requirements.txt",
                "package.json",
                "Cargo.toml",
                "go.mod",
                "Makefile",
                "Dockerfile",
                "docker-compose.yml",
                "main.py",
                "app.py",
                "index.js",
                "index.ts",
                ".env.example",
                "config.yaml",
                "config.json",
            ]

            for f in result.files[:200]:
                if f.name in important_files:
                    key_files.append(f.name)

            if key_files:
                context_parts.append(
                    f"\n**Key Files Found:** {', '.join(key_files[:10])}"
                )

            if result.recently_modified:
                recent = result.recently_modified[:5]
                context_parts.append("\n**Recently Modified:**")
                for f in recent:
                    context_parts.append(f"  - {f.name} ({f.age_human})")

            context_parts.append(
                "\n**Note:** Use this context to provide informed, specific responses without needing to run list_directory first."
            )
            context_parts.append("")

            result_str = "\n".join(context_parts)
            self._context_cache = result_str
            self._context_cache_ts = time.monotonic()

            # Presentation is best-effort: a missing/broken visual token or
            # adapter must not discard a successfully scanned and cached context.
            try:
                rocket = getattr(UIIcons, "ROCKET", "")
                icon_prefix = f"{rocket} " if rocket else ""
                self.agi_event_adapter.emit_chat_message(
                    sender="agent",
                    content=(
                        f"› [Aura AGI] {icon_prefix}Project context loaded: "
                        f"{result.total_files} arquivos, "
                        f"{result.total_lines:,} linhas em {result.scan_duration_ms}ms"
                    ),
                )
            except Exception as error:
                logger.debug("Context presentation skipped: %s", error)
            logger.info(
                f"Imagination Engine: Project context loaded ({result.total_files} files in {result.scan_duration_ms}ms)"
            )
            return result_str

        except Exception as e:
            logger.warning(
                f"Failed to get project context from Imagination Engine: {e}"
            )
            return ""

    def build_conscious_system_message(self, base_prompt: str, user_query: str) -> str:
        """
        Build system message enhanced with consciousness and constitution.

        Args:
            base_prompt: The base system message
            user_query: The user's prompt (to find relevant skills)

        Returns:
            Enhanced system message
        """
        enhanced_message = base_prompt

        if self.constitution:
            project_stage = self.extract_project_stage()
            stage_guidance = self.get_stage_guidance(project_stage)

            constitution_section = (
                "\n\n"
                "**═══════════════════════════════════════════════════════════**\n"
                "**CONSTITUIÇÃO DO PROJETO (REGRAS IMUTÁVEIS)**\n"
                "**═══════════════════════════════════════════════════════════**\n"
            )

            if project_stage:
                constitution_section += (
                    f"**ESTÁGIO DO PROJETO: {project_stage.upper()}**\n"
                    f"{stage_guidance}\n\n"
                )

            constitution_section += (
                "As seguintes regras e padrões do projeto são IMUTÁVEIS e devem ser "
                "respeitadas em TODAS as suas ações e decisões:\n\n"
                f"{self.constitution}\n\n"
                "**IMPORTANTE:** Se o usuário solicitar algo que contradiga estas regras, "
                "você DEVE questionar e alertar antes de prosseguir. A Constituição tem "
                "prioridade sobre qualquer solicitação do usuário.\n"
                "**═══════════════════════════════════════════════════════════**\n"
            )
            enhanced_message = base_prompt + constitution_section
            logger.info(
                f"Project Constitution injected into AGI system message (Stage: {project_stage})"
            )

        project_context = self.get_instant_project_context()
        if project_context:
            enhanced_message = enhanced_message + project_context

        if self.evidence_tree:
            enhanced_message += "\n\n**AGI EVIDENCE TREE:**\n" + self.evidence_tree.mission_pointer()

        if self.consciousness_manager:
            try:
                enhanced_message = (
                    self.consciousness_manager.build_enhanced_system_message(
                        base_prompt=enhanced_message,
                        user_query=user_query,
                        include_skills=True,
                        max_skills=2,
                        skill_threshold=0.35,
                    )
                )

                skills_found = self.consciousness_manager.find_relevant_skills(
                    user_query, max_skills=2, threshold=0.35
                )

                if skills_found:
                    skill_names = [s.skill.name for s in skills_found]
                    self.agi_event_adapter.emit_chat_message(
                        sender="agent",
                        content=f"› [Aura AGI] {UIIcons.INFO} Conhecimento ativado: {', '.join(skill_names)}",
                    )
                    logger.info(
                        f"Injected {len(skills_found)} skills into system message"
                    )

            except Exception as e:
                logger.error(
                    f"Error adding consciousness to system message: {e}", exc_info=True
                )

        return enhanced_message

    def extract_project_stage(self) -> Optional[str]:
        """Detect project stage (new, development, maintenance, legacy)."""
        try:
            return ProjectState.detect_stage(self.project_root)
        except Exception:
            return None

    def get_stage_guidance(self, stage: Optional[str]) -> str:
        """Get guidance based on project stage."""
        if not stage:
            return ""

        guidance = {
            "greenfield": "Este é um projeto **novo**. Priorize estrutura correta, setup inicial robusto e documentação desde o início.",
            "early_stage": "Projeto em **estágio inicial**. Foco em prototipagem rápida mas com arquitetura limpa.",
            "growth": "Projeto em **crescimento**. Cuidado com dívida técnica, priorize escalabilidade e testes.",
            "maintenance": "Projeto **maduro/manutenção**. Extrema cautela com refatorações grandes. Priorize estabilidade e testes de regressão.",
            "legacy": "Projeto **legado**. Evite reescrever tudo. Faça mudanças cirúrgicas e bem testadas. Documente tudo.",
        }
        return guidance.get(stage, "")

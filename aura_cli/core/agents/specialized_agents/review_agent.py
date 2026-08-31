"""Code review specialised agent — inherits AgentBase.

Handles: analyze_code (NLP + static analysis), validate_syntax, review_file
(full NLP review with problem detection, improvement suggestions and
complexity classification).
"""

from typing import Any, Dict, List, Optional

from aura_cli.core.agents.agent_base import AgentBase, AgentTask
from aura_cli.core.agents.specialized_agents._tool_schema import schemas_for_categories
from aura_cli.core.logger import get_logger
from aura_cli.core.service_registry import ToolCategory

logger = get_logger(__name__)


class ReviewAgent(AgentBase):
    """Specialised code-review agent."""

    def __init__(self, agent_id: str = "review_agent", model: Optional[str] = None):
        """Initialise the ReviewAgent."""
        super().__init__(
            agent_id=agent_id,
            name="Review Agent",
            description="Agente especializado em revisão e análise de código",
            model=model,
        )

    def _execute_task(self, task: AgentTask) -> Any:
        """Execute a code-review task."""
        task_type = task.parameters.get("type", "unknown")

        if task_type == "analyze_code":
            return self._handle_analyze_code(task)
        elif task_type == "validate_syntax":
            return self._handle_validate_syntax(task)
        elif task_type == "review_file":
            return self._handle_review_file(task)
        else:
            raise ValueError(f"Unknown task type: {task_type}")

    def _handle_analyze_code(self, task: AgentTask) -> str:
        """Handle an analyze_code request."""
        from aura_cli.core.tools import analyze_code  # type: ignore[attr-defined]

        file_path = task.parameters.get("file_path")
        if not file_path:
            raise ValueError("Parâmetro 'file_path' é obrigatório")
        return analyze_code(file_path)

    def _handle_validate_syntax(self, task: AgentTask) -> str:
        """Valida sintaxe."""
        from aura_cli.core.tools import validate_syntax  # type: ignore[attr-defined]

        content = task.parameters.get("content")
        language = task.parameters.get("language")

        if not all([content, language]):
            raise ValueError("Parâmetros 'content' e 'language' são obrigatórios")

        return validate_syntax(content, language)

    def _handle_review_file(self, task: AgentTask) -> str:
        """Review a complete file with NLP analysis."""
        from aura_cli.core.code_analysis.nlp_analyzer import NLPAnalyzer
        from aura_cli.core.tools import (  # type: ignore[attr-defined]
            analyze_code,
            read_file,
            validate_syntax,
        )

        file_path = task.parameters.get("file_path")
        if not file_path:
            raise ValueError("Parâmetro 'file_path' é obrigatório")

        analysis = analyze_code(file_path)

        content = read_file(file_path)

        language = "python" if file_path.endswith(".py") else "unknown"
        if file_path.endswith((".js", ".ts")):
            language = "javascript"
        elif file_path.endswith((".java", ".kt")):
            language = "java"

        syntax_result = (
            validate_syntax(content, language)
            if language != "unknown"
            else "Linguagem não suportada"
        )

        nlp_analyzer = NLPAnalyzer()
        classification = nlp_analyzer.classify_code(content)
        summary = nlp_analyzer.summarize_code(content)

        result_parts = [
            f"Análise de Código:\n{analysis}",
            "\nAnálise NLP:",
            f"- Tipo de Função: {classification.function_type.value}",
            f"- Complexidade: {classification.complexity.value}",
            f"- Intenção: {classification.intent}",
            f"- Resumo: {summary.summary}",
            f"- Pontos-chave: {', '.join(summary.key_points[:3])}",
            f"- Sugestões: {', '.join(summary.suggestions[:3])}",
            f"\nValidação de Sintaxe:\n{syntax_result}",
        ]

        if self.has_consciousness():
            consciousness_insights = self._get_consciousness_insights(
                content, file_path
            )
            if consciousness_insights:
                result_parts.append(f"\n{consciousness_insights}")

        return "\n".join(result_parts)

    def _get_consciousness_insights(self, content: str, file_path: str) -> str:
        """
        Generate additional insights based on consciousness data.

        Uses the loaded persona and skills to provide more targeted feedback.
        """
        insights = []

        if self.consciousness_persona:
            persona_name = self.consciousness_persona.get("name", "")
            if "reviewer" in persona_name.lower():
                insights.append("🎯 Foco da Revisão (baseado na persona):")
                # Extract key focus areas from persona prompt
                prompt = self.consciousness_persona.get("system_prompt", "")
                if "Security" in prompt or "security" in prompt:
                    insights.append("  - Verificação de vulnerabilidades de segurança")
                if "Performance" in prompt or "performance" in prompt:
                    insights.append("  - Análise de problemas de performance")
                if "Code Quality" in prompt or "quality" in prompt:
                    insights.append("  - Qualidade e manutenibilidade do código")

        if self.consciousness_skills:
            insights.append("\n📚 Recommendations (based on loaded knowledge):")
            for skill in self.consciousness_skills[:2]:  # Limit to 2 skills
                skill_name = skill.get("name", "Unknown")
                insights.append(f"  - Aplicar princípios de: {skill_name}")

        return "\n".join(insights) if insights else ""

    def _get_available_tools(self) -> List[Dict[str, Any]]:
        """Return tool schemas for ReviewAgent derived from the ServiceRegistry.

        Categories exposed:
        - development: analyze_code, review_file, analyze_code_nlp, validate_syntax, …
        - file_system: read_file, list_directory (needed to read files for review)
        """
        return schemas_for_categories(
            [ToolCategory.DEVELOPMENT, ToolCategory.FILE_SYSTEM],
            exclude_names=["browse_content", "web_search"],
        )

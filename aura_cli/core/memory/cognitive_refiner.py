"""Cognitive Memory Refiner.

Refines conversation context before persistence using cognitive processing.
"""

import json
from typing import Any, Dict, List, Optional

from aura_cli.core.llm.base import query_with_fallback
from aura_cli.core.llm.model_utils import DEFAULT_GEMINI_MODEL
from aura_cli.core.logger import get_logger

logger = get_logger(__name__)

COGNITIVE_REFINER_MODEL = DEFAULT_GEMINI_MODEL


class CognitiveRefiner:
    """Cognitive memory refinement system."""

    def __init__(self, model: Optional[str] = None):
        """Initialise the cognitive refiner."""
        self.model = model
        self._refinement_cache: Dict[str, str] = {}

    def refine_context(
        self,
        conversation_history: List[Dict[str, Any]],
        max_tokens: int = 8000,
        mode: str = "auto",
    ) -> Dict[str, Any]:
        """Refine conversation context using cognitive processing."""
        if not conversation_history:
            return {
                "refined_content": "",
                "summary": "",
                "key_points": [],
                "metadata": {"refined": False, "reason": "empty_history"},
            }

        estimated_tokens = self._estimate_tokens(conversation_history)
        if estimated_tokens < max_tokens * 0.8:
            logger.debug(
                f"Contexto não precisa refinamento ({estimated_tokens} tokens < {max_tokens * 0.8})"
            )
            return {
                "refined_content": self._format_history(conversation_history),
                "summary": "",
                "key_points": [],
                "metadata": {
                    "refined": False,
                    "reason": "below_threshold",
                    "tokens": estimated_tokens,
                },
            }

        logger.info(
            f"Refinando contexto: {estimated_tokens} tokens (threshold: {max_tokens})"
        )

        try:
            refined = self._refine_with_llm(conversation_history, mode)
            return refined
        except Exception as e:
            logger.warning(f"Error refining with LLM, using fallback: {e}")
            return self._refine_fallback(conversation_history)

    def _refine_with_llm(
        self, conversation_history: List[Dict[str, Any]], mode: str
    ) -> Dict[str, Any]:
        """Refina contexto usando LLM."""
        history_text = self._format_history(conversation_history)

        refinement_prompt = f"""Você é um sistema de refinamento cognitivo de memória para um agente AI.

Sua tarefa é refinar o seguinte histórico de conversa, extraindo informações essenciais e criando um resumo inteligente.

MODO: {mode.upper()}
- auto: Balance entre preservação e compressão
- aggressive: Máxima compressão, mantendo apenas essenciais
- conservative: Preservação máxima, compressão mínima

REGRAS:
1. Extraia informações essenciais (decisões, ações, resultados)
2. Remova redundâncias e repetições
3. Preserve contexto crítico para o agente
4. Mantenha referências a arquivos, funções e decisões importantes
5. Crie resumo estruturado e hierárquico

HISTÓRICO:
{history_text}

Retorne um JSON com:
{{
    "summary": "Resumo executivo (2-3 parágrafos)",
    "key_points": ["ponto 1", "ponto 2", ...],
    "refined_content": "Conteúdo refinado completo (mantém estrutura mas remove redundâncias)",
    "important_decisions": ["decisão 1", "decisão 2", ...],
    "file_references": ["arquivo1.py", "arquivo2.py", ...]
}}
"""

        try:
            response = query_with_fallback(
                messages=[{"role": "user", "content": refinement_prompt}],
                model=self.model or COGNITIVE_REFINER_MODEL,
                max_tokens=4096,
                temperature=0.3,
            )

            if not response or not hasattr(response, "choices") or not response.choices:
                raise ValueError("Resposta vazia do LLM")

            content = None
            if hasattr(response.choices[0], "message") and hasattr(
                response.choices[0].message, "content"
            ):
                content = response.choices[0].message.content
            elif hasattr(response, "content"):
                content = response.content
            else:
                raise ValueError("Invalid LLM response format")

            if not content:
                raise ValueError("Conteúdo vazio na resposta do LLM")

            content = content.strip()
            if content.startswith("```"):
                lines = content.split("\n")
                content = "\n".join(lines[1:-1]) if len(lines) > 2 else content

            refined_data = json.loads(content)

            return {
                "refined_content": refined_data.get("refined_content", history_text),
                "summary": refined_data.get("summary", ""),
                "key_points": refined_data.get("key_points", []),
                "important_decisions": refined_data.get("important_decisions", []),
                "file_references": refined_data.get("file_references", []),
                "metadata": {
                    "refined": True,
                    "mode": mode,
                    "original_messages": len(conversation_history),
                    "refined_by": "llm",
                },
            }

        except json.JSONDecodeError as e:
            logger.warning(f"Error parsing LLM JSON: {e}")
            error_content = ""
            if response and hasattr(response, "choices") and response.choices:
                if hasattr(response.choices[0], "message") and hasattr(
                    response.choices[0].message, "content"
                ):
                    error_content = response.choices[0].message.content or ""
                elif hasattr(response, "content"):
                    error_content = response.content or ""
            return self._extract_json_from_text(error_content)
        except Exception as e:
            logger.error(f"Error refining with LLM: {e}")
            raise

    def _extract_json_from_text(self, text: str) -> Dict[str, Any]:
        """Extract JSON from text even if malformed."""
        import re

        json_match = re.search(r"\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}", text, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group())
            except Exception as _e:
                logger.debug(f"Ignorado: {_e}")

        return {
            "refined_content": text[:5000],  # Limitar tamanho
            "summary": "Automatic refinement (LLM returned invalid format)",
            "key_points": [],
            "metadata": {"refined": True, "mode": "fallback"},
        }

    def _refine_fallback(
        self, conversation_history: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Heuristic fallback refinement (no LLM)."""
        logger.info("Usando refinamento fallback (heurístico)")
        important_messages = []
        file_refs = []

        for msg in conversation_history:
            content = msg.get("content", "")
            role = msg.get("role", "")

            if role == "system":
                important_messages.append(msg)
                continue

            import re

            files = re.findall(
                r"\b[\w/.-]+\.(py|js|ts|md|txt|json|yaml|yml)\b", content
            )
            if files:
                file_refs.extend(files)
                important_messages.append(msg)
                continue

            decision_keywords = [
                "decidir",
                "escolher",
                "implementar",
                "criar",
                "modificar",
                "refatorar",
            ]
            if any(kw in content.lower() for kw in decision_keywords):
                important_messages.append(msg)
                continue

        recent_messages = conversation_history[-10:]
        for msg in recent_messages:
            if msg not in important_messages:
                important_messages.append(msg)

        refined_text = self._format_history(important_messages)

        return {
            "refined_content": refined_text,
            "summary": f"Refinamento heurístico: {len(important_messages)}/{len(conversation_history)} mensagens preservadas",
            "key_points": list(set(file_refs))[:10],
            "metadata": {
                "refined": True,
                "mode": "fallback",
                "original_messages": len(conversation_history),
                "preserved_messages": len(important_messages),
            },
        }

    def _format_history(self, history: List[Dict[str, Any]]) -> str:
        """Format conversation history for LLM input."""
        lines = []
        for msg in history:
            role = msg.get("role", "unknown")
            content = msg.get("content", "")
            lines.append(f"[{role.upper()}]\n{content}\n")
        return "\n".join(lines)

    def _estimate_tokens(self, history: List[Dict[str, Any]]) -> int:
        """Estimate the token count of the conversation history."""
        total_chars = sum(len(str(msg.get("content", ""))) for msg in history)
        return int(total_chars / 4)


def get_cognitive_refiner(model: Optional[str] = None) -> CognitiveRefiner:
    """Get singleton instance of CognitiveRefiner."""
    if not hasattr(get_cognitive_refiner, "_instance"):
        get_cognitive_refiner._instance = CognitiveRefiner(model)  # type: ignore[attr-defined]
    return get_cognitive_refiner._instance  # type: ignore[attr-defined]

"""Constitution Validator — Project Constitution integrity checking.

Validates prompts against the Project Constitution.
"""

import re
from typing import Any, Dict, List, Optional, Tuple


class ConstitutionValidator:
    """Validate prompts against the Project Constitution."""

    def __init__(self, constitution: Optional[str] = None):
        """Initialise the validator with the Project Constitution."""
        self.constitution = constitution or ""
        self._rules = self._extract_rules()
        self._validate_cache: Dict[str, Tuple[bool, List[str], Optional[str]]] = {}

    @staticmethod
    def _extract_matches(text: str, patterns: list) -> list:
        """Extract all non-empty matches from a list of regex patterns."""
        results = []
        for pattern in patterns:
            for m in re.findall(pattern, text, re.IGNORECASE):
                if isinstance(m, str) and m.strip():
                    results.append(m.strip())
        return results

    def _extract_rules(self) -> Dict[str, Any]:
        """Extract structured rules from the Constitution."""
        if not self.constitution:
            return {}

        rules: Dict[str, Any] = {
            "stack": [],
            "database": [],
            "api_style": [],
            "patterns": [],
            "prohibitions": [],
            "project_stage": None,
        }

        constitution_lower = self.constitution.lower()

        stage_patterns = [
            r"(?:estágio|fase|stage|phase)[:\-]?\s*(mvp|prototipação|produção\s+estável|refatoração\s+de\s+legado|caos\s+total|produção|legado|caos)",
            r"(mvp|prototipação|produção\s+estável|refatoração\s+de\s+legado|caos\s+total)",
        ]
        for pattern in stage_patterns:
            matches = re.findall(pattern, constitution_lower, re.IGNORECASE)
            if matches:
                stage = matches[0].lower().strip()
                if "mvp" in stage or "prototipação" in stage:
                    rules["project_stage"] = "mvp/prototipação"
                elif "produção" in stage:
                    rules["project_stage"] = "produção estável"
                elif "legado" in stage:
                    rules["project_stage"] = "refatoração de legado"
                elif "caos" in stage:
                    rules["project_stage"] = "caos total"
                else:
                    rules["project_stage"] = stage
                break

        stack_patterns = [
            r"(?:stack|linguagem|tecnologia|tecnologias)[:\-]?\s*([^\n]+)",
            r"(?:python|node\.?js|typescript|rust|go|java|javascript|nim)",
        ]
        rules["stack"] = self._extract_matches(constitution_lower, stack_patterns)

        db_patterns = [
            r"(?:banco|database|db)[:\-]?\s*([^\n]+)",
            r"(?:postgres|postgresql|mysql|sqlite|mongodb|redis)",
        ]
        rules["database"] = self._extract_matches(constitution_lower, db_patterns)

        api_patterns = [
            r"(?:api|estilo|style)[:\-]?\s*(rest|graphql|rpc|grpc|soap)",
            r"(?:rest|graphql|rpc)",
        ]
        rules["api_style"] = self._extract_matches(constitution_lower, api_patterns)

        prohibition_patterns = [
            r"(?:não|nunca|proibido|evitar|não usar)[:\-]?\s*([^\n]+)",
            r"(?:não|never|prohibited|avoid|don't use)",
        ]
        rules["prohibitions"] = self._extract_matches(
            constitution_lower, prohibition_patterns
        )

        return rules

    def _check_tech_conflicts(
        self, rule_key: str, candidates: list, label: str, prompt_lower: str
    ) -> str | None:
        """Check if prompt mentions technologies conflicting with constitution rules."""
        if not self._rules.get(rule_key):
            return None
        defined = " ".join(self._rules[rule_key]).lower()
        conflicts = [t for t in candidates if t in prompt_lower and t not in defined]
        if conflicts:
            return f"{label} conflitante detectada: {', '.join(conflicts)}. Constituição define: {', '.join(self._rules[rule_key])}"
        return None

    def validate_prompt(self, prompt: str) -> Tuple[bool, List[str], Optional[str]]:
        """Validate a prompt against the Constitution."""
        if not self.constitution:
            return True, [], None

        if prompt in self._validate_cache:
            return self._validate_cache[prompt]

        violations = []
        prompt_lower = prompt.lower()

        for v in [
            self._check_tech_conflicts(
                "stack",
                ["rust", "go", "java", "c++", "c#", "php"],
                "Stack",
                prompt_lower,
            ),
            self._check_tech_conflicts(
                "database",
                ["mongodb", "postgres", "mysql", "sqlite", "redis"],
                "Banco de dados",
                prompt_lower,
            ),
            self._check_tech_conflicts(
                "api_style",
                ["graphql", "rpc", "grpc", "soap"],
                "Estilo de API",
                prompt_lower,
            ),
        ]:
            if v:
                violations.append(v)

        if self._rules.get("prohibitions"):
            for prohibition in self._rules["prohibitions"]:
                if prohibition.lower() in prompt_lower:
                    violations.append(f"Violou proibição explícita: '{prohibition}'")

        sanitized_prompt = None
        if violations:
            sanitized_prompt = (
                f"ATENÇÃO: O prompt original pode violar regras da Constituição. "
                f"Por favor, revise e ajuste conforme as regras do projeto.\n\n"
                f"Prompt original: {prompt}\n\n"
                f"Violações detectadas:\n" + "\n".join(f"- {v}" for v in violations)
            )

        is_valid = len(violations) == 0
        result = (is_valid, violations, sanitized_prompt)
        if len(self._validate_cache) < 256:  # cap cache size
            self._validate_cache[prompt] = result
        return result

    def check_conflict(self, prompt: str) -> Optional[str]:
        """Return a conflict message if the prompt requires blocking, else None."""
        is_valid, violations, _ = self.validate_prompt(prompt)

        if not is_valid and violations:
            critical_violations = [
                v
                for v in violations
                if any(
                    keyword in v.lower()
                    for keyword in ["stack", "banco", "api", "proibição"]
                )
            ]
            if critical_violations:
                return (
                    "CONFLITO CRÍTICO DETECTADO:\n\n"
                    + "\n".join(f"⚠️  {v}" for v in critical_violations)
                    + "\n\nA Constituição do Projeto tem prioridade. "
                    "Deseja continuar mesmo assim ou ajustar o pedido?"
                )

        return None

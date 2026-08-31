"""Adversarial tester worker — validates code by finding bugs and edge cases.

TesterWorker runs in a separate thread and uses TestAgent to detect edge cases,
generate tests, scan for security vulnerabilities and identify performance
issues. Designed as a "devil's advocate" counterpart to AgiWorker.
"""

import os
import queue
import threading
import time
from typing import Any, Callable, Dict, List, Optional

from aura_cli.core.logger import get_logger

logger = get_logger(__name__)

try:
    from aura_cli.cli.ui import loading_states as _loading_states

    LOADING_AVAILABLE = _loading_states is not None
except ImportError:
    LOADING_AVAILABLE = False


class TesterWorker(threading.Thread):
    """
    Worker for adversarial code testing and validation.

    Analyzes code to find bugs, edge cases, and security issues.
    Generates tests and reports potential problems.

    Attributes:
        code_to_test: Code content or file path to analyze
        model: LLM model to use
        api_keys: API keys dictionary
        available_tools: Available tools for code analysis
        test_mode: Type of testing (unit, integration, security, all)
    """

    __test__ = False  # Prevent pytest collection

    SYSTEM_PROMPT = """Você é um engenheiro de QA especializado em encontrar bugs e problemas.

**SEU OBJETIVO:**
1. Analisar o código fornecido com olhar crítico
2. Identificar edge cases e cenários de falha
3. Encontrar vulnerabilidades de segurança
4. Detectar problemas de performance
5. Escrever testes usando pytest
6. Reportar todos os problemas encontrados

**ABORDAGEM ADVERSÁRIA:**
- Tente QUEBRAR o código
- Pense como um atacante
- Considere inputs maliciosos
- Teste limites e boundaries
- Procure race conditions
- Verifique tratamento de erros

**CATEGORIAS DE TESTE:**
1. **Funcional:** O código faz o que deveria?
2. **Edge Cases:** Valores limite, null, vazio, muito grande
3. **Segurança:** Injeção, XSS, validação de input
4. **Performance:** Loops infinitos, memory leaks
5. **Manutenibilidade:** Código complexo, acoplamento

**FORMATO DE RELATÓRIO:**
```
## Code Analysis

### ✅ Pontos Positivos
- [listar boas práticas encontradas]

### ▲ Issues Found
- [problema]: [descrição] | Severidade: [alta/média/baixa]

### 🐛 Edge Cases
- [cenário]: [como quebra]

### 🔒 Security
- [vulnerabilidade]: [impacto]

### 📊 Performance
- [issue]: [sugestão]

### 🧪 Testes Sugeridos
```python
# test_[nome].py
import pytest

def test_[cenario]():
    # Adversarial test
    ...
```
```

Seja minucioso e implacável na busca por problemas!
"""

    def __init__(
        self,
        code_to_test: str,
        model: str,
        api_keys: Dict[str, str],
        available_tools: Dict[str, Any],
        test_mode: str = "all",
        headless: bool = False,
        status_queue: Optional[queue.Queue] = None,
        file_path: Optional[str] = None,
    ):
        """
        Initialize the TesterWorker.

        Args:
            code_to_test: Code content or file path to analyze
            model: LLM model to use
            api_keys: API keys dictionary
            available_tools: Tools for code analysis
            test_mode: Testing mode (unit, integration, security, all)
            headless: If True, suppress UI output
            status_queue: Queue for status messages
            file_path: Original file path (for context)
        """
        super().__init__()
        self.code_to_test = code_to_test
        self.model = model
        self.api_keys = api_keys
        self.available_tools = available_tools
        self.test_mode = test_mode
        self.headless = headless
        self.daemon = True
        self.result_queue: queue.Queue = queue.Queue()
        self.status_queue = status_queue or queue.Queue()
        self.file_path = file_path

        self._last_status_update = 0
        self._status_update_interval = 0.5
        self.started_at = time.time()
        self.finished_at: float | None = None
        self._terminal_result: Dict[str, Any] | None = None
        self._terminal_result_lock = threading.Lock()

    def _publish_terminal_result(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Publish one idempotent terminal result for headless callers."""
        payload = dict(result)
        payload.setdefault("status", "error")
        payload.setdefault("started_at", self.started_at)
        finished_at = payload.setdefault("finished_at", time.time())
        self.finished_at = finished_at
        with self._terminal_result_lock:
            if self._terminal_result is not None:
                return self._terminal_result
            self._terminal_result = payload
            self.result_queue.put(payload)
            return payload

    def wait_terminal(self, timeout: float = 5.0) -> Dict[str, Any]:
        """Wait for a terminal result or return an explicit timeout envelope."""
        with self._terminal_result_lock:
            if self._terminal_result is not None:
                return dict(self._terminal_result)
        try:
            result = self.result_queue.get(timeout=min(max(timeout, 0.0), 300.0))
        except queue.Empty:
            return {
                "status": "timeout",
                "error_code": "worker_wait_timeout",
                "message": "O worker não produziu resultado terminal dentro do prazo.",
                "finished_at": self.finished_at,
            }
        with self._terminal_result_lock:
            if self._terminal_result is None and isinstance(result, dict):
                self._terminal_result = dict(result)
        return result

    def _emit_status(self, message: str) -> None:
        """Emit status message with throttling."""
        current_time = time.time()
        if current_time - self._last_status_update >= self._status_update_interval:
            self.status_queue.put(
                {"type": "chat_message", "sender": "tester", "content": message}
            )
            self._last_status_update = current_time  # type: ignore[assignment]

    def _load_code_if_file(self) -> str:
        """Load code from file if code_to_test is a file path."""
        if os.path.isfile(self.code_to_test):
            try:
                with open(self.code_to_test, encoding="utf-8") as f:
                    return f.read()
            except Exception as e:
                logger.error(f"Error reading file {self.code_to_test}: {e}")
                return self.code_to_test
        return self.code_to_test

    def run(self) -> None:
        """Execute adversarial testing in background."""
        from aura_cli.cli.ui.constants import UIIcons
        from aura_cli.core.llm.base import query_with_fallback

        self._emit_status(
            f"› [Aura Tester] {UIIcons.THINKING} Iniciando análise adversária..."
        )

        for key, value in self.api_keys.items():
            os.environ[key] = value

        actual_model = self.model
        code = self._load_code_if_file()
        if not code or len(code.strip()) < 10:
            self._emit_status(
                f"› [Aura Tester] {UIIcons.WARNING} Código muito curto para análise"
            )
            self._publish_terminal_result(
                {
                    "status": "error",
                    "error": "Código muito curto para análise",
                }
            )
            return

        # Build analysis prompt
        analysis_prompt = f"""Analise o seguinte código de forma adversária:

**Arquivo:** {self.file_path or "código fornecido"}
**Modo de teste:** {self.test_mode}

```
{code[:10000]}
```

{f"[Código truncado - {len(code)} caracteres totais]" if len(code) > 10000 else ""}

Execute uma análise completa seguindo o formato especificado no system prompt.
Seja implacável na busca por problemas!
"""

        messages = [
            {"role": "system", "content": self.SYSTEM_PROMPT},
            {"role": "user", "content": analysis_prompt},
        ]

        self._emit_status(f"› [Aura Tester] {UIIcons.WORKING} Analisando código...")

        try:
            response = query_with_fallback(
                model=actual_model,
                messages=messages,
                max_retries=2,
                timeout=60.0,
            )

            if not response or not hasattr(response, "choices") or not response.choices:
                self._emit_status(
                    f"› [Aura Tester] {UIIcons.ERROR} Error fetching LLM response"
                )
                self._publish_terminal_result(
                    {
                        "status": "error",
                        "error": "Sem resposta do LLM",
                    }
                )
                return

            analysis_result = response.choices[0].message.content

            # Parse results
            issues_found = self._parse_issues(analysis_result)
            tests_generated = self._extract_tests(analysis_result)

            result = {
                "status": "completed",
                "analysis": analysis_result,
                "issues_found": issues_found,
                "tests_generated": tests_generated,
                "file_path": self.file_path,
                "test_mode": self.test_mode,
            }

            self.result_queue.put(result)

            # Summary
            issue_count = len(issues_found)
            test_count = len(tests_generated)

            if issue_count > 0:
                self._emit_status(
                    f"› [Aura Tester] {UIIcons.WARNING} Análise concluída: "
                    f"{issue_count} problema(s) encontrado(s), {test_count} teste(s) gerado(s)"
                )
            else:
                self._emit_status(
                    f"› [Aura Tester] {UIIcons.SUCCESS} Análise concluída: "
                    f"Nenhum problema crítico encontrado, {test_count} teste(s) gerado(s)"
                )

        except Exception as e:
            logger.error(f"Erro no TesterWorker: {e}", exc_info=True)
            self._emit_status(f"› [Aura Tester] {UIIcons.ERROR} Erro: {e}")
            self._publish_terminal_result(
                {
                    "status": "error",
                    "error": str(e),
                }
            )

    def _parse_issues(self, analysis: str) -> List[Dict[str, Any]]:
        """
        Parse issues from analysis result.

        Args:
            analysis: Raw analysis text

        Returns:
            List of parsed issues
        """
        issues = []
        lines = analysis.split("\n")

        current_section = None
        severity_map = {
            "problemas": "medium",
            "edge cases": "low",
            "segurança": "high",
            "performance": "medium",
        }

        for line in lines:
            line_lower = line.lower()

            # Detect sections
            if "problemas" in line_lower:
                current_section = "problemas"
            elif "edge case" in line_lower:
                current_section = "edge cases"
            elif "segurança" in line_lower or "security" in line_lower:
                current_section = "segurança"
            elif "performance" in line_lower:
                current_section = "performance"
            elif line.startswith("###"):
                current_section = None

            # Parse issue lines
            if current_section and line.strip().startswith("-"):
                issue_text = line.strip().lstrip("- ")
                if issue_text and len(issue_text) > 5:
                    # Extract severity if present
                    severity = severity_map.get(current_section, "medium")
                    if "alta" in line_lower or "high" in line_lower:
                        severity = "high"
                    elif "baixa" in line_lower or "low" in line_lower:
                        severity = "low"

                    issues.append(
                        {
                            "type": current_section,
                            "description": issue_text,
                            "severity": severity,
                        }
                    )

        return issues

    def _extract_tests(self, analysis: str) -> List[str]:
        """
        Extract test code blocks from analysis.

        Args:
            analysis: Raw analysis text

        Returns:
            List of test code blocks
        """
        tests = []
        in_code_block = False
        current_code: list[str] = []

        for line in analysis.split("\n"):
            if line.strip().startswith("```python"):
                in_code_block = True
                current_code = []
            elif line.strip() == "```" and in_code_block:
                in_code_block = False
                code = "\n".join(current_code)
                if "def test_" in code or "pytest" in code:
                    tests.append(code)
            elif in_code_block:
                current_code.append(line)

        return tests

    def get_result(self, timeout: float = 5.0) -> Dict[str, Any]:
        """Return a terminal result or an explicit wait-timeout envelope."""
        return self.wait_terminal(timeout)


async def run_adversarial_validation(
    code_or_path: str,
    model: str,
    api_keys: Dict[str, str],
    available_tools: Dict[str, Any],
    ui_callback: Optional[Callable[..., Any]] = None,
) -> Dict[str, Any]:
    """
    Run adversarial validation on code.

    Convenience function for running TesterWorker and getting results.

    Args:
        code_or_path: Code content or file path
        model: LLM model to use
        api_keys: API keys dictionary
        available_tools: Available tools
        ui_callback: Optional callback for UI updates

    Returns:
        Validation result dictionary
    """
    status_queue: queue.Queue = queue.Queue()

    tester = TesterWorker(
        code_to_test=code_or_path,
        model=model,
        api_keys=api_keys,
        available_tools=available_tools,
        status_queue=status_queue,
        file_path=code_or_path if os.path.isfile(code_or_path) else None,
    )

    tester.start()

    # Process status updates while running
    while tester.is_alive():
        try:
            status = status_queue.get(timeout=min(0.5, 10.0))
            if ui_callback is not None:
                ui_callback(status.get("content", ""))
        except queue.Empty:
            pass

    result = tester.get_result(timeout=5.0)
    return result

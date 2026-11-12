"""Adversarial tester worker — validates code by finding bugs and edge cases.

TesterWorker runs in a separate thread and uses the LLM to detect edge cases,
generate tests, scan for security vulnerabilities and identify performance
issues. Designed as a "devil's advocate" counterpart to AgiWorker.

Built on BaseWorker so it shares the queues, throttled status updates, idempotent
terminal-result handling, watchdog and cleanup lifecycle with the other workers.
Credentials are NOT injected into ``os.environ``; ``query_with_fallback`` loads
them into thread-local storage, which is race-free across concurrent workers.
"""

import os
import queue
import time
from typing import Any, Callable, Dict, List, Optional

from aura_cli.cli.workers.base_worker import BaseWorker
from aura_cli.core.logger import get_logger

logger = get_logger(__name__)

try:
    from aura_cli.cli.ui import loading_states as _loading_states

    LOADING_AVAILABLE = _loading_states is not None
except ImportError:
    LOADING_AVAILABLE = False


class TesterWorker(BaseWorker):
    """
    Worker for adversarial code testing and validation.

    Analyzes code to find bugs, edge cases, and security issues.
    Generates tests and reports potential problems.

    Attributes:
        code_to_test: Code content or file path to analyze
        model: LLM model to use
        api_keys: API keys dictionary (consumed by the LLM layer, not os.environ)
        available_tools: Available tools for code analysis
        test_mode: Type of testing (unit, integration, security, all)
    """

    __test__ = False  # Prevent pytest collection

    dashboard_prefix = "Aura Tester"

    SYSTEM_PROMPT = """You are a QA engineer specialized in finding bugs and problems.

**SEU OBJETIVO:**
1. Analyse the provided code with a critical eye
2. Identify edge cases and failure scenarios
3. Find security vulnerabilities
4. Detectar problemas de performance
5. Escrever testes usando pytest
6. Reportar todos os problemas encontrados

**ADVERSARIAL APPROACH:**
- Try to BREAK the code
- Pense como um atacante
- Considere inputs maliciosos
- Teste limites e boundaries
- Procure race conditions
- Verifique tratamento de erros

**CATEGORIAS DE TESTE:**
1. **Functional:** Does the code do what it should?
2. **Edge Cases:** Valores limite, null, vazio, muito grande
3. **Security:** Injection, XSS, input validation
4. **Performance:** Loops infinitos, memory leaks
5. **Maintainability:** Complex code, coupling

**REPORT FORMAT:**
```
## Code Analysis

### ✅ Pontos Positivos
- [list good practices found]

### ▲ Issues Found
- [problem]: [description] | Severity: [high/medium/low]

### 🐛 Edge Cases
- [scenario]: [how it breaks]

### 🔒 Security
- [vulnerabilidade]: [impacto]

### 📊 Performance
- [issue]: [suggestion]

### 🧪 Testes Sugeridos
```python
# test_[nome].py
import pytest

def test_[cenario]():
    # Adversarial test
    ...
```
```

Be thorough and relentless in finding problems!
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
            api_keys: API keys dictionary (passed to the LLM layer)
            available_tools: Tools for code analysis
            test_mode: Testing mode (unit, integration, security, all)
            headless: If True, suppress UI output
            status_queue: Queue for status messages
            file_path: Original file path (for context)
        """
        super().__init__(status_queue=status_queue, task_id="tester", headless=headless)
        self.code_to_test = code_to_test
        self.model = model
        self.api_keys = api_keys
        self.available_tools = available_tools
        self.test_mode = test_mode
        self.file_path = file_path

    def _emit_status(self, message: str) -> None:
        """Emit a throttled status message tagged with the tester sender."""
        current_time = time.time()
        self._status_throttle.interval = self._status_update_interval
        if self._status_throttle.allow(current_time):
            self.status_queue.put(
                {"type": "chat_message", "sender": "tester", "content": message}
            )
            self._last_status_update = current_time  # type: ignore[assignment]  # float narrowed from Optional

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

    def _run_impl(self) -> None:
        """Execute adversarial testing inside the shared worker lifecycle."""
        from aura_cli.cli.ui.constants import UIIcons
        from aura_cli.core.llm.base import query_with_fallback

        self._emit_status(
            f"› [Aura Tester] {UIIcons.THINKING} Starting adversarial analysis..."
        )

        # Credentials are loaded into thread-local storage by the LLM layer; no
        # os.environ mutation (which races across concurrent workers).
        actual_model = self.model
        code = self._load_code_if_file()
        if not code or len(code.strip()) < 10:
            self._emit_status(
                f"› [Aura Tester] {UIIcons.WARNING} Code too short for analysis"
            )
            self._publish_terminal_result(
                {
                    "status": "error",
                    "error": "Code too short for analysis",
                }
            )
            return

        # Build analysis prompt
        analysis_prompt = f"""Analyze the following code adversarially:

**File:** {self.file_path or "provided code"}
**Modo de teste:** {self.test_mode}

```
{code[:10000]}
```

{f"[Code truncated - {len(code)} total characters]" if len(code) > 10000 else ""}

Execute a full analysis following the format specified in the system prompt.
Be relentless in finding problems!
"""

        messages = [
            {"role": "system", "content": self.SYSTEM_PROMPT},
            {"role": "user", "content": analysis_prompt},
        ]

        self._emit_status(f"› [Aura Tester] {UIIcons.WORKING} Analyzing code...")

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

            self._publish_terminal_result(result)

            # Summary
            issue_count = len(issues_found)
            test_count = len(tests_generated)

            if issue_count > 0:
                self._emit_status(
                    f"› [Aura Tester] {UIIcons.WARNING} Analysis complete: "
                    f"{issue_count} problema(s) encontrado(s), {test_count} teste(s) gerado(s)"
                )
            else:
                self._emit_status(
                    f"› [Aura Tester] {UIIcons.SUCCESS} Analysis complete: "
                    f"No critical issues found, {test_count} test(s) generated"
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
            "security": "high",
            "performance": "medium",
        }

        for line in lines:
            line_lower = line.lower()

            # Detect sections
            if "problemas" in line_lower:
                current_section = "problemas"
            elif "edge case" in line_lower:
                current_section = "edge cases"
            elif "security" in line_lower:
                current_section = "security"
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
        headless=True,
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

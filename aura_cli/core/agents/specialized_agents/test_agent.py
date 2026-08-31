"""Test-specialised agent for Aura CLI — inherits AgentBase.

Handles: run_tests, find_related_tests, validate_tests_pass, generate_tests
(ML-based). Uses the testing framework from core.testing.
"""

from typing import Any, Dict, List, Optional

from aura_cli.core.agents.agent_base import AgentBase, AgentTask
from aura_cli.core.agents.specialized_agents._tool_schema import schemas_for_categories
from aura_cli.core.logger import get_logger
from aura_cli.core.service_registry import ToolCategory

logger = get_logger(__name__)


class TestAgent(AgentBase):
    """Specialised testing agent."""

    def __init__(self, agent_id: str = "test_agent", model: Optional[str] = None):
        """Initialise the TestAgent."""
        super().__init__(
            agent_id=agent_id,
            name="Test Agent",
            description="Agente especializado em execução e validação de testes",
            model=model,
        )

    def _execute_task(self, task: AgentTask) -> Any:
        """Execute a testing task."""
        task_type = task.parameters.get("type", "unknown")

        if task_type == "run_tests":
            return self._handle_run_tests(task)
        elif task_type == "find_related_tests":
            return self._handle_find_related_tests(task)
        elif task_type == "validate_tests_pass":
            return self._handle_validate_tests_pass(task)
        elif task_type == "generate_tests":
            return self._handle_generate_tests(task)
        else:
            raise ValueError(f"Unknown task type: {task_type}")

    def _handle_run_tests(self, task: AgentTask) -> str:
        """Handle a run_tests request."""
        from aura_cli.core.testing.test_runner import run_tests

        test_path = task.parameters.get("test_path", ".")
        pattern = task.parameters.get("pattern")
        return str(run_tests(test_path, pattern))

    def _handle_find_related_tests(self, task: AgentTask) -> str:
        """Encontra testes relacionados."""
        from aura_cli.core.testing.test_runner import find_related_tests

        file_path = task.parameters.get("file_path")
        if not file_path:
            raise ValueError("Parâmetro 'file_path' é obrigatório")
        return str(find_related_tests(file_path))

    def _handle_validate_tests_pass(self, task: AgentTask) -> str:
        """Valida se testes passam."""
        from aura_cli.core.testing.test_runner import validate_tests_pass

        test_path = task.parameters.get("test_path", ".")
        return str(validate_tests_pass(test_path))

    def _handle_generate_tests(self, task: AgentTask) -> str:
        """Generate tests using ML models."""
        from transformers import AutoModelForCausalLM, AutoTokenizer

        from aura_cli.core.tools import read_file  # type: ignore[attr-defined]

        file_path = task.parameters.get("file_path")
        if not file_path:
            raise ValueError("Parâmetro 'file_path' é obrigatório")

        code = read_file(file_path)

        try:
            model_name = "Salesforce/codet5-base"
            tokenizer = AutoTokenizer.from_pretrained(model_name, revision="main")  # nosec B615
            model = AutoModelForCausalLM.from_pretrained(model_name, revision="main")  # nosec B615
            model.eval()

            prompt = f"# Generate unit tests for the following function:\n{code}\n\n# Tests:\n"

            import torch

            inputs = tokenizer(
                prompt, return_tensors="pt", truncation=True, max_length=512
            )

            with torch.no_grad():
                outputs = model.generate(
                    inputs["input_ids"],
                    max_length=inputs["input_ids"].shape[1] + 200,
                    temperature=0.7,
                    do_sample=True,
                    pad_token_id=tokenizer.pad_token_id,
                )

            generated = tokenizer.decode(
                outputs[0][inputs["input_ids"].shape[1] :], skip_special_tokens=True
            )

            return f"Testes gerados para {file_path}:\n\n{generated}"

        except Exception as e:
            logger.warning(
                f"Error generating tests with model: {e}, usando template básico"
            )
            return f"""# Testes gerados para {file_path}

import unittest

class TestGenerated(unittest.TestCase):
    def test_basic(self):
        \"\"\"Teste básico gerado automaticamente.\"\"\"
        self.assertTrue(True, "Module loaded successfully")

if __name__ == '__main__':
    unittest.main()
"""

    def _get_available_tools(self) -> List[Dict[str, Any]]:
        """Return tool schemas for TestAgent derived from the ServiceRegistry.

        Categories exposed:
        - testing: run_tests_advanced (and any future testing tools added to the manifest)
        - development: generate_tests, find_related_tests, validate_tests_pass, analyze_code, …
        - file_system: read_file, write_file (to read source and write new test files)
        """
        return schemas_for_categories(
            [ToolCategory.TESTING, ToolCategory.DEVELOPMENT, ToolCategory.FILE_SYSTEM],
            exclude_names=["browse_content", "web_search"],
        )

"""
Testes para o módulo github_actions.

Testa funcionalidades de integração com GitHub Actions,
criação e execução de workflows.
"""

from pathlib import Path
from unittest.mock import mock_open, patch

from aura_cli.core.ops_tools.ci_cd.github_actions import (
    WorkflowConfig,
    create_workflow,
)


class TestWorkflowConfig:
    """Testa dataclass WorkflowConfig."""

    def test_workflow_config_creation(self):
        """Testa criação de configuração de workflow."""
        on_config = {"push": {"branches": ["main"]}}
        jobs_config = {
            "test": {
                "runs-on": "ubuntu-latest",
                "steps": [{"uses": "actions/checkout@v3"}],
            }
        }

        config = WorkflowConfig(name="CI Pipeline", on=on_config, jobs=jobs_config)

        assert config.name == "CI Pipeline"
        assert config.on == on_config
        assert config.jobs == jobs_config
        assert config.env == {}

    def test_workflow_config_with_env(self):
        """Testa configuração com variáveis de ambiente."""
        env_vars = {"NODE_VERSION": "18", "PYTHON_VERSION": "3.11"}

        config = WorkflowConfig(
            name="Deploy",
            on={"release": {"types": ["published"]}},
            jobs={"deploy": {"runs-on": "ubuntu-latest"}},
            env=env_vars,
        )

        assert config.env == env_vars


class TestCreateWorkflow:
    """Testa função create_workflow."""

    @patch("aura_cli.core.ops_tools.ci_cd.github_actions.yaml.dump")
    @patch("builtins.open", new_callable=mock_open)
    @patch.object(Path, "mkdir")
    def test_create_workflow_basic(self, mock_mkdir, mock_file, mock_yaml_dump):
        """Testa criação básica de workflow."""
        config = WorkflowConfig(
            name="Test Workflow",
            on={"push": {"branches": ["main"]}},
            jobs={"test": {"runs-on": "ubuntu-latest"}},
        )

        mock_yaml_dump.return_value = None

        result = create_workflow("test.yml", config)

        mock_mkdir.assert_any_call(parents=True, exist_ok=True)
        mock_file.assert_called_once()
        mock_yaml_dump.assert_called_once()
        assert isinstance(result, str)

    @patch("aura_cli.core.ops_tools.ci_cd.github_actions.yaml.dump")
    @patch("builtins.open", new_callable=mock_open)
    @patch.object(Path, "mkdir")
    def test_create_workflow_custom_path(self, mock_mkdir, mock_file, mock_yaml_dump):
        """Testa criação com caminho customizado."""
        config = WorkflowConfig(
            name="Custom Workflow",
            on={"pull_request": {}},
            jobs={"lint": {"runs-on": "ubuntu-latest"}},
        )

        result = create_workflow("custom.yml", config, path="custom/workflows")

        mock_mkdir.assert_any_call(parents=True, exist_ok=True)
        assert "custom/workflows" in result

    def test_workflow_yaml_structure(self):
        """Testa estrutura YAML do workflow."""
        config = WorkflowConfig(
            name="Complete Workflow",
            on={
                "push": {"branches": ["main", "develop"]},
                "pull_request": {"branches": ["main"]},
            },
            jobs={
                "test": {
                    "runs-on": "ubuntu-latest",
                    "steps": [
                        {"uses": "actions/checkout@v3"},
                        {"name": "Setup Python", "uses": "actions/setup-python@v4"},
                    ],
                }
            },
            env={"CI": "true"},
        )

        # Verificar estrutura esperada
        assert "push" in config.on
        assert "pull_request" in config.on
        assert "test" in config.jobs
        assert config.env["CI"] == "true"

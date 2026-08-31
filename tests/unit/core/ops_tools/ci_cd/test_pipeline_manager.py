"""
Testes para o módulo pipeline_manager.

Testa funcionalidades de criação e gerenciamento
de pipelines CI/CD complexos.
"""

from aura_cli.core.ops_tools.ci_cd.pipeline_manager import (
    PipelineStage,
    StageStatus,
)


class TestStageStatus:
    """Testa enum StageStatus."""

    def test_stage_status_values(self):
        """Testa valores de status de estágio."""
        assert StageStatus.PENDING.value == "pending"
        assert StageStatus.RUNNING.value == "running"
        assert StageStatus.SUCCESS.value == "success"
        assert StageStatus.FAILED.value == "failed"
        assert StageStatus.SKIPPED.value == "skipped"


class TestPipelineStage:
    """Testa dataclass PipelineStage."""

    def test_pipeline_stage_creation(self):
        """Testa criação de estágio de pipeline."""
        commands = ["npm install", "npm test", "npm run build"]

        stage = PipelineStage(
            id="build_stage", name="Build and Test", commands=commands
        )

        assert stage.id == "build_stage"
        assert stage.name == "Build and Test"
        assert stage.commands == commands
        assert stage.dependencies == []

    def test_pipeline_stage_with_dependencies(self):
        """Testa estágio com dependências."""
        stage = PipelineStage(
            id="deploy_stage",
            name="Deploy",
            commands=["docker build", "docker push"],
            dependencies=["build_stage", "test_stage"],
        )

        assert stage.dependencies == ["build_stage", "test_stage"]

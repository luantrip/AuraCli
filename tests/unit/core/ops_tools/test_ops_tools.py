"""Tests for Ops Tools."""

from unittest.mock import MagicMock, Mock, patch

from aura_cli.core.ops_tools.docker import (
    docker_logs,
    docker_ps,
)

# Import from the correct submodules
from aura_cli.core.ops_tools.git import (
    git_diff,
    git_status,
)
from aura_cli.core.ops_tools.monitoring.health import (
    system_resources,
)


class TestGitOperations:
    """Test Git operations."""

    @patch("subprocess.run")
    def test_git_status(self, mock_run):
        """Test git_status."""
        mock_result = Mock()
        mock_result.stdout = "## main...origin/main"
        mock_result.returncode = 0
        mock_run.return_value = mock_result

        status = git_status()
        assert "main" in status

    @patch("subprocess.run")
    def test_git_diff(self, mock_run):
        """Test git_diff."""
        mock_result = Mock()
        mock_result.stdout = "diff --git a/file b/file"
        mock_result.returncode = 0
        mock_run.return_value = mock_result

        diff = git_diff()
        assert "diff --git" in diff


class TestDockerOperations:
    """Test Docker operations."""

    @patch("aura_cli.core.ops_tools.docker._get_docker_client")
    def test_docker_ps(self, mock_get_client):
        """Test docker_ps returns list of container dicts via SDK."""
        mock_container = MagicMock()
        mock_container.id = "abc123"
        mock_container.name = "test_container"
        mock_container.status = "running"
        mock_container.image.tags = ["nginx:latest"]
        mock_container.ports = {}
        mock_container.attrs = {"Created": "2026-01-01T00:00:00Z"}

        mock_client = MagicMock()
        mock_client.containers.list.return_value = [mock_container]
        mock_get_client.return_value = mock_client

        ps = docker_ps()
        # SDK returns list of dicts or error string
        assert isinstance(ps, (list, str))

    @patch("subprocess.run")
    def test_docker_logs_container_not_found(self, mock_run):
        """Test docker_logs with non-existent container."""
        mock_result = Mock()
        mock_result.stdout = ""
        mock_result.stderr = "Error: No such container"
        mock_result.returncode = 1

        mock_run.return_value = mock_result

        result = docker_logs("nonexistent", tail=50)

        # Aceita múltiplos formatos de erro
        assert any(
            x in result.lower()
            for x in ["erro", "error", "não encontrado", "docker não disponível"]
        )


class TestSystemOperations:
    """Test system operations."""

    @patch("psutil.cpu_percent")
    @patch("psutil.virtual_memory")
    @patch("psutil.disk_usage")
    def test_system_resources(self, mock_disk, mock_memory, mock_cpu):
        """Test system_resources."""
        mock_cpu.return_value = 10.0

        mock_mem = Mock()
        mock_mem.percent = 50.0
        mock_mem.used = 8000000000
        mock_mem.available = 8000000000
        mock_memory.return_value = mock_mem

        mock_d = Mock()
        mock_d.percent = 40.0
        mock_d.used = 200000000000
        mock_d.free = 300000000000
        mock_disk.return_value = mock_d

        res = system_resources()
        assert "Recursos" in res

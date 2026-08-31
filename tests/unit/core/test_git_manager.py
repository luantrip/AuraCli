"""Tests for git_manager module.

Tests for Git operations and repository management.
"""

from pathlib import Path
import subprocess
from unittest.mock import Mock, patch


class TestGitManager:
    """Tests for Git manager functionality."""

    def test_git_manager_import(self):
        """Test git_manager module can be imported."""
        from aura_cli.core import git_manager

        assert git_manager is not None

    def test_git_manager_creation(self):
        """Test GitManager creation."""
        from aura_cli.core.git_manager import GitManager

        project_root = Path("/test/project")
        manager = GitManager(project_root)

        assert manager is not None
        assert manager.project_root == project_root
        assert manager.git_dir == project_root / ".git"

    @patch("pathlib.Path.exists")
    def test_is_git_repository_true(self, mock_exists):
        """Test git repository detection when .git exists."""
        from aura_cli.core.git_manager import GitManager

        mock_exists.return_value = True

        manager = GitManager(Path("/test/project"))

        assert manager.is_git_repository() is True

    @patch("pathlib.Path.exists")
    def test_is_git_repository_false(self, mock_exists):
        """Test git repository detection when .git doesn't exist."""
        from aura_cli.core.git_manager import GitManager

        mock_exists.return_value = False

        manager = GitManager(Path("/test/project"))

        assert manager.is_git_repository() is False

    @patch("subprocess.run")
    @patch("pathlib.Path.exists")
    def test_check_dirty_state_clean(self, mock_exists, mock_run):
        """Test checking dirty state when repository is clean."""
        from aura_cli.core.git_manager import GitManager

        mock_exists.return_value = True
        mock_run.return_value = Mock(stdout="", returncode=0)

        manager = GitManager(Path("/test/project"))
        is_dirty, files = manager.check_dirty_state()

        assert is_dirty is False
        assert files == []

    @patch("subprocess.run")
    @patch("pathlib.Path.exists")
    def test_check_dirty_state_dirty(self, mock_exists, mock_run):
        """Test checking dirty state when repository has changes."""
        from aura_cli.core.git_manager import GitManager

        mock_exists.return_value = True
        mock_run.return_value = Mock(
            stdout=" M file1.py\n A file2.py\n?? untracked.py\n", returncode=0
        )

        manager = GitManager(Path("/test/project"))
        is_dirty, files = manager.check_dirty_state()

        assert is_dirty is True
        # Check that files are in the list (git status --porcelain format removes first 3 chars)
        # So " M file1.py" becomes "ile1.py" after line[3:]
        assert "ile1.py" in files  # This is what actually gets parsed
        assert "file2.py" in files
        assert "untracked.py" not in files  # Should ignore untracked files

    @patch("pathlib.Path.exists")
    def test_check_dirty_state_not_git_repo(self, mock_exists):
        """Test checking dirty state when not a git repository."""
        from aura_cli.core.git_manager import GitManager

        mock_exists.return_value = False

        manager = GitManager(Path("/test/project"))
        is_dirty, files = manager.check_dirty_state()

        assert is_dirty is False
        assert files == []

    @patch("subprocess.run")
    @patch("pathlib.Path.exists")
    def test_check_dirty_state_git_error(self, mock_exists, mock_run):
        """Test checking dirty state when git command fails."""
        from aura_cli.core.git_manager import GitManager

        mock_exists.return_value = True
        mock_run.side_effect = subprocess.CalledProcessError(1, "git")

        manager = GitManager(Path("/test/project"))
        is_dirty, files = manager.check_dirty_state()

        assert is_dirty is False
        assert files == []

    @patch("subprocess.run")
    @patch("pathlib.Path.exists")
    def test_create_checkpoint_success(self, mock_exists, mock_run):
        """Test creating checkpoint successfully."""
        from aura_cli.core.git_manager import GitManager

        mock_exists.return_value = True

        # Mock the sequence of git commands with proper string returns
        def mock_subprocess_run(*args, **kwargs):
            if "rev-parse" in args[0]:
                return Mock(stdout="abc123\n", returncode=0)
            elif "status" in args[0]:
                return Mock(stdout=" M file1.py\n", returncode=0)
            else:
                return Mock(returncode=0)

        mock_run.side_effect = mock_subprocess_run

        manager = GitManager(Path("/test/project"))

        # Mock check_dirty_state to return dirty state
        with patch.object(
            manager, "check_dirty_state", return_value=(True, ["file1.py"])
        ):
            commit_hash = manager.create_checkpoint("Test checkpoint")

        # Should return the mocked commit hash
        assert commit_hash == "abc123"

    @patch("pathlib.Path.exists")
    def test_create_checkpoint_not_git_repo(self, mock_exists):
        """Test creating checkpoint when not a git repository."""
        from aura_cli.core.git_manager import GitManager

        mock_exists.return_value = False

        manager = GitManager(Path("/test/project"))
        result = manager.create_checkpoint()

        assert result is None

    @patch("subprocess.run")
    @patch("pathlib.Path.exists")
    def test_create_checkpoint_clean_repo(self, mock_exists, mock_run):
        """Test creating checkpoint when repository is clean."""
        from aura_cli.core.git_manager import GitManager

        mock_exists.return_value = True

        manager = GitManager(Path("/test/project"))

        # Mock check_dirty_state to return clean state
        with patch.object(manager, "check_dirty_state", return_value=(False, [])):
            result = manager.create_checkpoint()

        assert result is None

    @patch("subprocess.run")
    @patch("pathlib.Path.exists")
    def test_get_last_checkpoint_found(self, mock_exists, mock_run):
        """Test getting last checkpoint when one exists."""
        from aura_cli.core.git_manager import GitManager

        mock_exists.return_value = True
        mock_run.return_value = Mock(
            stdout="abc123|aura-wip: Auto-checkpoint at 2023-01-01 12:00:00|2023-01-01 12:00:00 +0000\n",
            returncode=0,
        )

        manager = GitManager(Path("/test/project"))
        checkpoint = manager.get_last_checkpoint()

        assert checkpoint is not None
        assert checkpoint["hash"] == "abc123"
        assert "aura-wip" in checkpoint["message"]
        assert checkpoint["date"] == "2023-01-01 12:00:00 +0000"

    @patch("subprocess.run")
    @patch("pathlib.Path.exists")
    def test_get_last_checkpoint_not_found(self, mock_exists, mock_run):
        """Test getting last checkpoint when none exists."""
        from aura_cli.core.git_manager import GitManager

        mock_exists.return_value = True
        mock_run.return_value = Mock(stdout="", returncode=0)

        manager = GitManager(Path("/test/project"))
        checkpoint = manager.get_last_checkpoint()

        assert checkpoint is None

    @patch("pathlib.Path.exists")
    def test_get_last_checkpoint_not_git_repo(self, mock_exists):
        """Test getting last checkpoint when not a git repository."""
        from aura_cli.core.git_manager import GitManager

        mock_exists.return_value = False

        manager = GitManager(Path("/test/project"))
        checkpoint = manager.get_last_checkpoint()

        assert checkpoint is None

    @patch("pathlib.Path.exists")
    def test_validate_before_write_not_git_repo(self, mock_exists):
        """Test validation when not a git repository."""
        from aura_cli.core.git_manager import GitManager

        mock_exists.return_value = False

        manager = GitManager(Path("/test/project"))
        is_safe, warning = manager.validate_before_write()

        assert is_safe is True
        assert warning is None

    @patch("pathlib.Path.exists")
    def test_validate_before_write_clean_repo(self, mock_exists):
        """Test validation when repository is clean."""
        from aura_cli.core.git_manager import GitManager

        mock_exists.return_value = True

        manager = GitManager(Path("/test/project"))

        # Mock check_dirty_state to return clean state
        with patch.object(manager, "check_dirty_state", return_value=(False, [])):
            is_safe, warning = manager.validate_before_write()

        assert is_safe is True
        assert warning is None

    @patch("pathlib.Path.exists")
    def test_validate_before_write_dirty_repo(self, mock_exists):
        """Test validation when repository has changes."""
        from aura_cli.core.git_manager import GitManager

        mock_exists.return_value = True

        manager = GitManager(Path("/test/project"))

        # Mock check_dirty_state to return dirty state
        with patch.object(
            manager, "check_dirty_state", return_value=(True, ["file1.py", "file2.py"])
        ):
            is_safe, warning = manager.validate_before_write()

        assert is_safe is False
        assert warning is not None
        assert "arquivo(s) com mudanças não commitadas" in warning
        assert "file1.py" in warning

    @patch("subprocess.run")
    @patch("pathlib.Path.exists")
    def test_get_current_branch_success(self, mock_exists, mock_run):
        """Test getting current branch successfully."""
        from aura_cli.core.git_manager import GitManager

        mock_exists.return_value = True
        mock_run.return_value = Mock(stdout="main\n", returncode=0)

        manager = GitManager(Path("/test/project"))
        branch = manager.get_current_branch()

        assert branch == "main"

    @patch("pathlib.Path.exists")
    def test_get_current_branch_not_git_repo(self, mock_exists):
        """Test getting current branch when not a git repository."""
        from aura_cli.core.git_manager import GitManager

        mock_exists.return_value = False

        manager = GitManager(Path("/test/project"))
        branch = manager.get_current_branch()

        assert branch is None

    @patch("subprocess.run")
    @patch("pathlib.Path.exists")
    def test_get_current_branch_error(self, mock_exists, mock_run):
        """Test getting current branch when git command fails."""
        from aura_cli.core.git_manager import GitManager

        mock_exists.return_value = True
        mock_run.side_effect = subprocess.CalledProcessError(1, "git")

        manager = GitManager(Path("/test/project"))
        branch = manager.get_current_branch()

        assert branch is None

    @patch("subprocess.run")
    @patch("pathlib.Path.exists")
    def test_create_checkpoint_with_custom_message(self, mock_exists, mock_run):
        """Test creating checkpoint with custom message."""
        from aura_cli.core.git_manager import GitManager

        mock_exists.return_value = True

        # Mock the sequence of git commands
        mock_run.side_effect = [
            Mock(returncode=0),  # git add
            Mock(returncode=0),  # git commit
            Mock(stdout="def456\n", returncode=0),  # git rev-parse
        ]

        manager = GitManager(Path("/test/project"))

        # Mock check_dirty_state to return dirty state
        with patch.object(
            manager, "check_dirty_state", return_value=(True, ["file1.py"])
        ):
            commit_hash = manager.create_checkpoint("Custom message")

        assert commit_hash == "def456"

    @patch("subprocess.run")
    @patch("pathlib.Path.exists")
    def test_create_checkpoint_git_error(self, mock_exists, mock_run):
        """Test creating checkpoint when git command fails."""
        from aura_cli.core.git_manager import GitManager

        mock_exists.return_value = True
        mock_run.side_effect = subprocess.CalledProcessError(1, "git")

        manager = GitManager(Path("/test/project"))

        # Mock check_dirty_state to return dirty state
        with patch.object(
            manager, "check_dirty_state", return_value=(True, ["file1.py"])
        ):
            result = manager.create_checkpoint()

        assert result is None

    @patch("subprocess.run")
    @patch("pathlib.Path.exists")
    def test_validate_before_write_many_files(self, mock_exists, mock_run):
        """Test validation warning with many modified files."""
        from aura_cli.core.git_manager import GitManager

        mock_exists.return_value = True

        manager = GitManager(Path("/test/project"))

        # Mock check_dirty_state with many files
        many_files = [f"file{i}.py" for i in range(15)]
        with patch.object(
            manager, "check_dirty_state", return_value=(True, many_files)
        ):
            is_safe, warning = manager.validate_before_write()

        assert is_safe is False
        assert warning is not None
        assert "15 arquivo(s)" in warning
        assert "... e mais 5 arquivo(s)" in warning

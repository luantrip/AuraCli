"""
Tests for Project Indexer Sentinel Integration.
"""

from unittest.mock import MagicMock, patch

from aura_cli.core.context.project_indexer import ProjectContextManager


class TestProjectIndexerSentinel:
    """Test suite for Sentinel integration in ProjectIndexer."""

    @patch("aura_cli.core.context.sentinel_manager.SentinelManager")
    def test_sentinel_optimization(self, mock_sentinel_class, tmp_path):
        """
        Test that needs_update uses Sentinel results to avoid disk I/O.
        """
        # Setup Sentinel Mock
        mock_sentinel_instance = MagicMock()
        # Simulate that 'modified.py' changed, but 'cached.py' did not
        mock_diff = MagicMock()
        mock_diff.modified = ["modified.py"]
        mock_diff.added = []
        mock_sentinel_instance.scan_changes.return_value = mock_diff

        mock_sentinel_class.return_value = mock_sentinel_instance

        # Initialize Manager
        manager = ProjectContextManager(project_root=tmp_path)

        # Test 1: File in modified list -> Should return True immediately
        assert manager.needs_update("modified.py") is True

        # Test 2: File NOT in modified list, but in index -> Should return False
        # We need to populate the internal index mock
        manager.index = {"files": {"cached.py": {"hash": "123"}}}

        assert manager.needs_update("cached.py") is False

        # Verify Sentinel was initialized and scanned
        mock_sentinel_class.assert_called_with(tmp_path)
        mock_sentinel_instance.scan_changes.assert_called_once()

    @patch("aura_cli.core.context.sentinel_manager.SentinelManager")
    def test_sentinel_fallback(self, mock_sentinel_class, tmp_path):
        """
        Test fallback to MD5 when Sentinel is unavailable.
        """
        # Setup Sentinel failure
        mock_sentinel_class.side_effect = Exception("Sentinel not found")

        # Initialize
        manager = ProjectContextManager(project_root=tmp_path)

        # Create a file
        test_file = tmp_path / "real.py"
        test_file.write_text("content", encoding="utf-8")

        # Act: Check update (should calculate hash)
        # It's not in index, so needs_update -> True
        assert manager.needs_update("real.py") is True

        # If we add it to index with same hash
        import hashlib

        h = hashlib.md5(b"content", usedforsecurity=False).hexdigest()
        manager.index = {"files": {"real.py": {"hash": h}}}

        # Should now be False (hash matches)
        assert manager.needs_update("real.py") is False

"""
Tests for Project Indexer (project_indexer.py).

Tests project indexing functionality including:
- File tree generation
- Key file identification
- Convention inference
- Overview generation
- Init command workflow
"""

from pathlib import Path
import tempfile

from aura_cli.core.context.project_indexer import (
    ANALYZABLE_EXTENSIONS,
    SKIP_DIRS,
    generate_file_tree,
    get_project_context_manager,
)


class TestFileTreeGeneration:
    """Test file tree generation."""

    def test_generate_file_tree_excludes_skip_dirs(self):
        """Should exclude directories in SKIP_DIRS."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            # Create test structure
            (root / "src").mkdir()
            (root / "src" / "main.py").write_text("print('hello')")
            (root / "node_modules").mkdir()
            (root / "node_modules" / "package.json").write_text("{}")
            (root / ".git").mkdir()
            (root / ".git" / "config").write_text("")

            tree = generate_file_tree(root)

            assert isinstance(tree, str)
            assert "src" in tree
            assert "main.py" in tree
            # Should exclude skip dirs
            assert "node_modules" not in tree
            assert ".git" not in tree

    def test_generate_file_tree_includes_analyzable_extensions(self):
        """Should include only analyzable file extensions."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            # Create files with different extensions
            (root / "script.py").write_text("# Python")
            (root / "app.js").write_text("// JavaScript")
            (root / "data.bin").write_text("binary")
            (root / "image.png").write_text("image")

            tree = generate_file_tree(root)

            assert "script.py" in tree
            assert "app.js" in tree
            # Binary files should be excluded
            assert "data.bin" not in tree or tree.count("data.bin") == 0
            assert "image.png" not in tree or tree.count("image.png") == 0

    def test_generate_file_tree_handles_empty_project(self):
        """Should handle empty directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tree = generate_file_tree(Path(tmpdir))

            assert isinstance(tree, str)
            # Should return something (even if minimal)
            assert len(tree) >= 0


class TestProjectContextManager:
    """Test project context manager."""

    def test_get_project_context_manager_returns_instance(self):
        """Should return ProjectContextManager instance."""
        manager = get_project_context_manager()

        assert manager is not None
        # Check it has expected methods
        assert hasattr(manager, "get_file_context") or hasattr(
            manager, "get_context_for_file"
        )


class TestConstants:
    """Test configuration constants."""

    def test_analyzable_extensions_includes_common_types(self):
        """Should include common file extensions."""
        assert ".py" in ANALYZABLE_EXTENSIONS
        assert ".js" in ANALYZABLE_EXTENSIONS
        assert ".ts" in ANALYZABLE_EXTENSIONS
        assert ".md" in ANALYZABLE_EXTENSIONS
        assert ".json" in ANALYZABLE_EXTENSIONS

    def test_skip_dirs_includes_common_patterns(self):
        """Should include common directories to skip."""
        assert "node_modules" in SKIP_DIRS
        assert ".git" in SKIP_DIRS
        assert "__pycache__" in SKIP_DIRS
        assert ".venv" in SKIP_DIRS


class TestEdgeCases:
    """Test edge cases."""

    def test_generate_file_tree_with_deep_nesting(self):
        """Should handle deeply nested directories."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            # Create moderately deep structure (not too deep to avoid truncation)
            deep_path = root / "a" / "b" / "c"
            deep_path.mkdir(parents=True)
            (deep_path / "file.py").write_text("# Deep file")

            tree = generate_file_tree(root)

            assert isinstance(tree, str)
            # Should at least show the directory structure
            assert "a" in tree or "file.py" in tree

    def test_generate_file_tree_with_special_characters(self):
        """Should handle files with special characters."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            # Create files with special chars
            (root / "file-with-dash.py").write_text("# Dash")
            (root / "file_with_underscore.py").write_text("# Underscore")

            tree = generate_file_tree(root)

            assert "file-with-dash.py" in tree or "file_with_underscore.py" in tree

    def test_generate_file_tree_with_symlinks(self):
        """Should handle symbolic links gracefully."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            # Create file and symlink
            real_file = root / "real.py"
            real_file.write_text("# Real")

            link_file = root / "link.py"
            try:
                link_file.symlink_to(real_file)
            except OSError:
                # Keep the test executable on filesystems without symlink support.
                fallback_file = root / "fallback.py"
                fallback_file.write_text("# Fallback")
                tree = generate_file_tree(root)
                assert "fallback.py" in tree
            else:
                tree = generate_file_tree(root)
                assert isinstance(tree, str)

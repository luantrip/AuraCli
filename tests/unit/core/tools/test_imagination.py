"""
Tests for the Imagination Engine system.

Tests cover:
- Pure Python fallback scanner
- ScanResult model validation
- FileInfo categorization
- ImaginationScanner caching
- Async scanning functionality
"""

import asyncio
from pathlib import Path
import tempfile

import pytest

import aura_cli.core.tools.imagination_tools as img_tools
from aura_cli.core.tools.imagination_tools import (
    FileCategory,
    FileInfo,
    ImaginationScanner,
    PurePythonScanner,
    ScanOptions,
    ScanResult,
    get_imagination_scanner,
    get_project_summary,
    scan_filesystem,
)


@pytest.fixture(autouse=True)
def clear_scanner_cache(request):
    """Clear scanner cache after each test to ensure isolation.

    Only clears after tests that don't test caching behavior.
    Tests that test caching need a clean cache at the start.
    """
    test_name = request.node.name
    # Reset global singleton to ensure fresh Lock creation in new loop
    img_tools._scanner = None

    # Clear cache before tests that don't test caching behavior
    if not any(x in test_name for x in ["caching", "clear_cache", "without_cache"]):
        scanner = get_imagination_scanner()
        scanner.clear_cache()
    yield
    # Always clear cache and reset
    img_tools._scanner = None


# =============================================================================
# FILE INFO TESTS
# =============================================================================


class TestFileInfo:
    """Tests for FileInfo model."""

    def test_file_info_creation(self):
        """Test basic FileInfo creation."""
        info = FileInfo(
            path="src/main.py",
            name="main.py",
            extension=".py",
            size=1024,
            lines=50,
            last_modified=1700000000.0,
            category=FileCategory.CODE,
        )

        assert info.path == "src/main.py"
        assert info.name == "main.py"
        assert info.extension == ".py"
        assert info.size == 1024
        assert info.lines == 50
        assert info.category == FileCategory.CODE

    def test_file_info_size_human(self):
        """Test human-readable size formatting."""
        # Bytes
        info = FileInfo(path="a.txt", name="a.txt", size=512, last_modified=0)
        assert "B" in info.size_human

        # Kilobytes
        info = FileInfo(path="b.txt", name="b.txt", size=2048, last_modified=0)
        assert "KB" in info.size_human

        # Megabytes
        info = FileInfo(
            path="c.txt", name="c.txt", size=5 * 1024 * 1024, last_modified=0
        )
        assert "MB" in info.size_human

    def test_file_info_age_human(self):
        """Test human-readable age formatting."""
        import time

        # Just now
        info = FileInfo(path="a.txt", name="a.txt", size=0, last_modified=time.time())
        assert "s ago" in info.age_human

        # Minutes ago
        info = FileInfo(
            path="a.txt", name="a.txt", size=0, last_modified=time.time() - 300
        )
        assert "m ago" in info.age_human

        # Hours ago
        info = FileInfo(
            path="a.txt", name="a.txt", size=0, last_modified=time.time() - 7200
        )
        assert "h ago" in info.age_human


# =============================================================================
# FILE CATEGORY TESTS
# =============================================================================


class TestFileCategory:
    """Tests for file categorization."""

    def test_code_extensions(self):
        """Test code file detection."""
        code_exts = [".py", ".js", ".ts", ".go", ".rs", ".java"]
        for ext in code_exts:
            result = PurePythonScanner.categorize(ext)
            assert result == FileCategory.CODE, f"{ext} should be CODE"

    def test_config_extensions(self):
        """Test config file detection."""
        config_exts = [".json", ".yaml", ".yml", ".toml", ".ini"]
        for ext in config_exts:
            result = PurePythonScanner.categorize(ext)
            assert result == FileCategory.CONFIG, f"{ext} should be CONFIG"

    def test_doc_extensions(self):
        """Test doc file detection."""
        doc_exts = [".md", ".txt", ".rst"]
        for ext in doc_exts:
            result = PurePythonScanner.categorize(ext)
            assert result == FileCategory.DOC, f"{ext} should be DOC"

    def test_style_extensions(self):
        """Test style file detection."""
        style_exts = [".css", ".scss", ".sass", ".tcss"]
        for ext in style_exts:
            result = PurePythonScanner.categorize(ext)
            assert result == FileCategory.STYLE, f"{ext} should be STYLE"

    def test_binary_extensions(self):
        """Test binary file detection."""
        binary_exts = [".pyc", ".png", ".jpg", ".zip", ".pdf"]
        for ext in binary_exts:
            result = PurePythonScanner.categorize(ext)
            assert result == FileCategory.BINARY, f"{ext} should be BINARY"

    def test_other_extensions(self):
        """Test unknown file detection."""
        result = PurePythonScanner.categorize(".unknown")
        assert result == FileCategory.OTHER


# =============================================================================
# SCAN OPTIONS TESTS
# =============================================================================


class TestScanOptions:
    """Tests for ScanOptions model."""

    def test_default_options(self):
        """Test default scan options."""
        options = ScanOptions()

        assert options.include_preview is True
        assert options.max_depth == 0
        assert options.include_hidden is False
        assert options.respect_gitignore is True
        assert options.max_file_size == 10_000_000

    def test_custom_options(self):
        """Test custom scan options."""
        options = ScanOptions(
            include_preview=False,
            max_depth=3,
            include_hidden=True,
            respect_gitignore=False,
            max_file_size=5_000_000,
        )

        assert options.include_preview is False
        assert options.max_depth == 3
        assert options.include_hidden is True
        assert options.respect_gitignore is False
        assert options.max_file_size == 5_000_000


# =============================================================================
# SCAN RESULT TESTS
# =============================================================================


class TestScanResult:
    """Tests for ScanResult model."""

    def test_scan_result_creation(self):
        """Test ScanResult creation."""
        result = ScanResult(
            root_path="/test/project",
            total_files=100,
            total_directories=20,
            total_lines=5000,
            total_size=1024 * 1024,
            scan_duration_ms=50,
        )

        assert result.root_path == "/test/project"
        assert result.total_files == 100
        assert result.total_directories == 20
        assert result.total_lines == 5000

    def test_scan_result_total_size_human(self):
        """Test human-readable total size."""
        result = ScanResult(
            root_path="/test",
            total_size=1024 * 1024,
        )

        assert "MB" in result.total_size_human or "KB" in result.total_size_human

    def test_scan_result_is_stale(self):
        """Test stale detection."""
        import time

        # Fresh result
        result = ScanResult(root_path="/test", timestamp=time.time())
        assert not result.is_stale(ttl=60)

        # Stale result
        result = ScanResult(root_path="/test", timestamp=time.time() - 120)
        assert result.is_stale(ttl=60)

    def test_scan_result_search_files(self):
        """Test file search functionality."""
        files = [
            FileInfo(path="src/main.py", name="main.py", size=0, last_modified=0),
            FileInfo(path="src/utils.py", name="utils.py", size=0, last_modified=0),
            FileInfo(
                path="tests/test_main.py", name="test_main.py", size=0, last_modified=0
            ),
        ]

        result = ScanResult(root_path="/test", files=files)

        # Search by name
        matches = result.search_files("main")
        assert len(matches) == 2  # main.py and test_main.py

        # Search by path
        matches = result.search_files("src/")
        assert len(matches) == 2  # main.py and utils.py


# =============================================================================
# PURE PYTHON SCANNER TESTS
# =============================================================================


class TestPurePythonScanner:
    """Tests for PurePythonScanner."""

    def test_scan_empty_directory(self):
        """Test scanning an empty directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            options = ScanOptions()
            result = PurePythonScanner.scan(Path(tmpdir), options)

            assert result.total_files == 0
            assert result.total_directories == 0

    def test_scan_with_files(self):
        """Test scanning directory with files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create test files
            (Path(tmpdir) / "main.py").write_text("print('hello')")
            (Path(tmpdir) / "config.json").write_text("{}")
            (Path(tmpdir) / "README.md").write_text("# Test")

            options = ScanOptions()
            result = PurePythonScanner.scan(Path(tmpdir), options)

            assert result.total_files == 3
            assert "code" in result.by_category
            assert "config" in result.by_category
            assert "doc" in result.by_category

    def test_scan_respects_max_depth(self):
        """Test that max_depth is respected."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create nested structure
            nested = Path(tmpdir) / "a" / "b" / "c"
            nested.mkdir(parents=True)
            (Path(tmpdir) / "root.py").write_text("")
            (Path(tmpdir) / "a" / "level1.py").write_text("")
            (nested / "deep.py").write_text("")

            # Scan with max_depth=1
            options = ScanOptions(max_depth=1)
            result = PurePythonScanner.scan(Path(tmpdir), options)

            # Should only find root.py and level1.py
            assert result.total_files == 2

    def test_scan_hidden_files(self):
        """Test hidden file handling."""
        with tempfile.TemporaryDirectory() as tmpdir:
            (Path(tmpdir) / "visible.py").write_text("")
            (Path(tmpdir) / ".hidden.py").write_text("")

            # Without hidden files
            options = ScanOptions(include_hidden=False)
            result = PurePythonScanner.scan(Path(tmpdir), options)
            assert result.total_files == 1

            # With hidden files
            options = ScanOptions(include_hidden=True)
            result = PurePythonScanner.scan(Path(tmpdir), options)
            assert result.total_files == 2

        def test_line_counting(self):
            """Test line counting functionality."""
            with tempfile.TemporaryDirectory() as tmpdir:
                test_file = Path(tmpdir) / "test.py"
                test_file.write_text("line1\nline2\nline3\n")

                lines = PurePythonScanner.analyze_file(str(test_file))[0]
                assert lines == 3

        def test_preview_extraction(self):
            """Test preview extraction functionality."""
            with tempfile.TemporaryDirectory() as tmpdir:
                test_file = Path(tmpdir) / "test.py"
                test_file.write_text("line1\nline2\nline3\nline4\nline5\n")

                preview = PurePythonScanner.analyze_file(
                    str(test_file), max_preview_lines=3
                )[1]
                assert len(preview) == 3
                assert preview[0] == "line1"


# =============================================================================
# IMAGINATION SCANNER TESTS
# =============================================================================


class TestImaginationScanner:
    """Tests for ImaginationScanner."""

    def test_singleton_scanner(self):
        """Test that get_imagination_scanner returns singleton."""
        scanner1 = get_imagination_scanner()
        scanner2 = get_imagination_scanner()
        assert scanner1 is scanner2

    def test_scanner_cache_key(self):
        """Test cache key generation."""
        scanner = ImaginationScanner()
        options1 = ScanOptions()
        options2 = ScanOptions(include_preview=False)

        key1 = scanner._cache_key(Path("/test"), options1)
        key2 = scanner._cache_key(Path("/test"), options2)

        assert key1 != key2  # Different options = different keys

    def test_scanner_caching(self):
        """Test that results are cached."""
        with tempfile.TemporaryDirectory() as tmpdir:
            (Path(tmpdir) / "test.py").write_text("")

            async def run():
                scanner = ImaginationScanner()

                # First scan
                result1 = await scanner.scan_async(tmpdir)

                # Second scan (should be cached)
                result2 = await scanner.scan_async(tmpdir)

                # Same timestamp means it was cached
                assert result1.timestamp == result2.timestamp

            asyncio.run(run())

    def test_scanner_clear_cache(self):
        """Test cache clearing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            (Path(tmpdir) / "test.py").write_text("")

            async def run():
                scanner = ImaginationScanner()

                # First scan
                result1 = await scanner.scan_async(tmpdir)

                # Clear cache
                scanner.clear_cache()

                # Second scan (should be fresh)
                result2 = await scanner.scan_async(tmpdir)

                # Different timestamps mean fresh scan
                assert result1.timestamp != result2.timestamp

            asyncio.run(run())

    def test_scanner_without_cache(self):
        """Test scanning with cache disabled."""
        with tempfile.TemporaryDirectory() as tmpdir:
            (Path(tmpdir) / "test.py").write_text("")

            async def run():
                scanner = ImaginationScanner()

                # Scan with cache disabled
                result1 = await scanner.scan_async(tmpdir, use_cache=False)
                result2 = await scanner.scan_async(tmpdir, use_cache=False)

                # Should be different scans
                assert result1.timestamp != result2.timestamp

            asyncio.run(run())


# =============================================================================
# TOOL FUNCTION TESTS
# =============================================================================


class TestToolFunctions:
    """Tests for tool functions exposed to agents."""

    def test_scan_filesystem(self):
        """Test scan_filesystem function."""
        with tempfile.TemporaryDirectory() as tmpdir:
            (Path(tmpdir) / "main.py").write_text("print('test')")

            result = asyncio.run(scan_filesystem(tmpdir))

            assert isinstance(result, dict)
            assert "total_files" in result
            assert "total_lines" in result
            assert result["total_files"] >= 1

    def test_get_project_summary(self):
        """Test get_project_summary function."""
        with tempfile.TemporaryDirectory() as tmpdir:
            (Path(tmpdir) / "main.py").write_text("print('test')")
            (Path(tmpdir) / "README.md").write_text("# Test")

            summary = asyncio.run(get_project_summary(tmpdir))

            assert isinstance(summary, str)
            assert "Project" in summary
            assert "Files" in summary
            assert "Statistics" in summary


# =============================================================================
# ERROR HANDLING TESTS
# =============================================================================


class TestErrorHandling:
    """Tests for error handling."""

    def test_scan_nonexistent_path(self):
        """Test scanning non-existent path raises error."""

        async def run():
            scanner = get_imagination_scanner()
            await scanner.scan_async("/nonexistent/path/12345")

        with pytest.raises(FileNotFoundError):
            asyncio.run(run())

    def test_scan_file_instead_of_directory(self):
        """Test scanning a file instead of directory raises error."""
        with tempfile.NamedTemporaryFile(suffix=".txt") as f:

            async def run():
                scanner = get_imagination_scanner()
                await scanner.scan_async(f.name)

            with pytest.raises(NotADirectoryError):
                asyncio.run(run())


# =============================================================================
# PERFORMANCE TESTS
# =============================================================================


class TestPerformance:
    """Basic performance tests."""

    def test_scan_is_reasonably_fast(self):
        """Test that scanning is reasonably fast."""
        import time

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create some files
            for i in range(50):
                (Path(tmpdir) / f"file_{i}.py").write_text(f"# File {i}")

            async def run():
                scanner = ImaginationScanner()

                start = time.time()
                result = await scanner.scan_async(tmpdir, use_cache=False)
                elapsed = time.time() - start

                # Should complete in under 2 seconds for 50 files
                assert elapsed < 2.0
                assert result.total_files == 50

            asyncio.run(run())

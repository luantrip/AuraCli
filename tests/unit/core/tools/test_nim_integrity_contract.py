"""Contract tests for nim_integrity module (Fase 2.2).

Verifies that IntegrityReport and BinaryStatus expose the expected
interface so callers can rely on them without breaking.
"""

from __future__ import annotations

from pathlib import Path


class TestBinaryStatusContract:
    """BinaryStatus must expose: name, path, present, executable, smoke_ok, ok, error."""

    def test_ok_when_all_true(self):
        from aura_cli.core.nim_integrity import BinaryStatus

        s = BinaryStatus(
            name="imagination",
            path=Path("/bin/imagination"),
            present=True,
            executable=True,
            smoke_ok=True,
        )
        assert s.ok is True
        assert s.error is None

    def test_not_ok_when_not_present(self):
        from aura_cli.core.nim_integrity import BinaryStatus

        s = BinaryStatus(
            name="nexus",
            path=Path("/bin/nexus"),
            present=False,
            executable=False,
            smoke_ok=False,
        )
        assert s.ok is False

    def test_not_ok_when_smoke_fails(self):
        from aura_cli.core.nim_integrity import BinaryStatus

        s = BinaryStatus(
            name="prism",
            path=Path("/bin/prism"),
            present=True,
            executable=True,
            smoke_ok=False,
            error="exit 1",
        )
        assert s.ok is False
        assert s.error == "exit 1"


class TestIntegrityReportContract:
    """IntegrityReport must expose: all_ok, missing, broken, library_ok."""

    def _make_report(self, statuses, library_ok=True):
        from aura_cli.core.nim_integrity import IntegrityReport

        r = IntegrityReport(library_ok=library_ok)
        r.binaries = statuses
        return r

    def _status(self, name, present=True, executable=True, smoke_ok=True):
        from aura_cli.core.nim_integrity import BinaryStatus

        return BinaryStatus(
            name=name,
            path=Path(f"/bin/{name}"),
            present=present,
            executable=executable,
            smoke_ok=smoke_ok,
        )

    def test_all_ok_true_when_everything_passes(self):
        report = self._make_report(
            [self._status("imagination"), self._status("nexus")],
            library_ok=True,
        )
        assert report.all_ok is True
        assert report.missing == []
        assert report.broken == []

    def test_missing_lists_absent_binaries(self):
        report = self._make_report(
            [
                self._status(
                    "imagination", present=False, executable=False, smoke_ok=False
                )
            ],
            library_ok=True,
        )
        assert "imagination" in report.missing
        assert report.all_ok is False

    def test_broken_lists_present_but_failing(self):
        report = self._make_report(
            [self._status("forge", present=True, executable=True, smoke_ok=False)],
            library_ok=True,
        )
        assert "forge" in report.broken
        assert report.missing == []
        assert report.all_ok is False

    def test_library_missing_makes_all_ok_false(self):
        report = self._make_report(
            [self._status("imagination")],
            library_ok=False,
        )
        assert report.all_ok is False


class TestCheckNimIntegrityContract:
    """check_nim_integrity() must return an IntegrityReport with correct shape."""

    def test_returns_integrity_report(self, tmp_path):
        # Point BIN_DIR to an empty temp dir — all binaries will be missing
        import aura_cli.core.nim_integrity as nim_mod
        from aura_cli.core.nim_integrity import IntegrityReport, check_nim_integrity

        original = nim_mod._BIN_DIR
        nim_mod._BIN_DIR = tmp_path
        try:
            report = check_nim_integrity()
        finally:
            nim_mod._BIN_DIR = original

        assert isinstance(report, IntegrityReport)
        assert isinstance(report.binaries, list)
        assert (
            len(report.binaries) == 6
        )  # imagination, nexus, sentinel, prism, forge, aura-monitor
        # library_ok may be True if the real dylib exists in core/memory/ (fallback path)
        assert isinstance(report.library_ok, bool)

    def test_sentinel_smoke_check_never_passes_version_as_project_root(self):
        import aura_cli.core.nim_integrity as nim_mod

        assert nim_mod._BINARIES["sentinel"] is None

    def test_all_missing_when_bin_dir_empty(self, tmp_path):
        import aura_cli.core.nim_integrity as nim_mod

        original = nim_mod._BIN_DIR
        nim_mod._BIN_DIR = tmp_path
        try:
            report = nim_mod.check_nim_integrity()
        finally:
            nim_mod._BIN_DIR = original

        assert report.missing == [
            "imagination",
            "nexus",
            "sentinel",
            "prism",
            "forge",
            "aura-monitor",
        ]
        assert report.broken == []

    def test_log_integrity_summary_does_not_raise(self, tmp_path):
        import aura_cli.core.nim_integrity as nim_mod

        original = nim_mod._BIN_DIR
        nim_mod._BIN_DIR = tmp_path
        try:
            report = nim_mod.check_nim_integrity()
            # Must not raise regardless of state
            nim_mod.log_integrity_summary(report)
        finally:
            nim_mod._BIN_DIR = original

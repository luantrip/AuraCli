from pathlib import Path
import zipfile

import pytest

from aura_cli.core.skills.manager import SkillIntegrityError, SkillManager


def _make_source(root: Path) -> Path:
    source = root / "source"
    source.mkdir()
    (source / "SKILL.md").write_text(
        "---\nname: demo\nversion: 1.0.0\ndescription: demo skill\n---\n# Demo\n",
        encoding="utf-8",
    )
    (source / "script.py").write_text("print('hi')\n", encoding="utf-8")
    return source


def test_skill_manager_installs_and_packages(tmp_path: Path):
    source = tmp_path / "source"
    source.mkdir()
    (source / "SKILL.md").write_text(
        "---\nname: demo\ndescription: demo skill\n---\n# Demo\n", encoding="utf-8"
    )
    manager = SkillManager(tmp_path / "installed")
    item = manager.install(source)
    assert item.name == "demo"
    package = tmp_path / "demo.aura-skill"
    manager.pack(source, package)
    assert package.exists()


class TestIntegrityVerification:
    """A packaged skill is verified against its manifest.json on install."""

    def test_intact_package_installs_and_is_recorded_as_verified(self, tmp_path: Path):
        source = _make_source(tmp_path)
        manager = SkillManager(tmp_path / "installed")
        package = tmp_path / "demo.aura-skill"
        manager.pack(source, package)

        info = manager.install(package)
        assert info.name == "demo"
        record = manager.registry.list()["demo"]
        assert record["verified"] is True
        assert record["manifest_sha256"]  # digest captured

    def test_a_tampered_file_is_rejected_fail_closed(self, tmp_path: Path):
        source = _make_source(tmp_path)
        manager = SkillManager(tmp_path / "installed")
        package = tmp_path / "demo.aura-skill"
        manager.pack(source, package)

        # Rewrite one file but keep the original manifest -> checksum mismatch.
        tampered = tmp_path / "tampered.aura-skill"
        with zipfile.ZipFile(package) as zin, zipfile.ZipFile(tampered, "w") as zout:
            for name in zin.namelist():
                data = b"print('EVIL')\n" if name == "script.py" else zin.read(name)
                zout.writestr(name, data)

        with pytest.raises(SkillIntegrityError, match="checksum mismatch"):
            manager.install(tampered)
        # Nothing registered for a rejected install.
        assert "demo" not in manager.registry.list()

    def test_a_file_missing_from_the_archive_is_rejected(self, tmp_path: Path):
        source = _make_source(tmp_path)
        manager = SkillManager(tmp_path / "installed")
        package = tmp_path / "demo.aura-skill"
        manager.pack(source, package)

        pruned = tmp_path / "pruned.aura-skill"
        with zipfile.ZipFile(package) as zin, zipfile.ZipFile(pruned, "w") as zout:
            for name in zin.namelist():
                if name == "script.py":
                    continue  # drop a file the manifest still lists
                zout.writestr(name, zin.read(name))

        with pytest.raises(SkillIntegrityError, match="missing file"):
            manager.install(pruned)

    def test_directory_install_has_no_manifest_and_is_unverified(self, tmp_path: Path):
        source = _make_source(tmp_path)
        manager = SkillManager(tmp_path / "installed")
        manager.install(source)  # plain directory, no manifest.json
        record = manager.registry.list()["demo"]
        assert record["verified"] is False
        assert record["manifest_sha256"] is None


class TestRegistryWiring:
    """SkillRegistry tracks install and remove operations."""

    def test_install_then_remove_keeps_the_registry_in_sync(self, tmp_path: Path):
        source = _make_source(tmp_path)
        manager = SkillManager(tmp_path / "installed")
        manager.install(source)
        assert "demo" in manager.registry.list()

        manager.remove("demo")
        assert "demo" not in manager.registry.list()

    def test_registry_remove_is_idempotent(self, tmp_path: Path):
        manager = SkillManager(tmp_path / "installed")
        manager.registry.remove("never-installed")  # no raise, no file corruption
        assert manager.registry.list() == {}

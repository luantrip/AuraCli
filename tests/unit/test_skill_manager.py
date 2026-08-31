from pathlib import Path

from aura_cli.core.skills.manager import SkillManager


def test_skill_manager_installs_and_packages(tmp_path: Path):
    source = tmp_path / "source"
    source.mkdir()
    (source / "SKILL.md").write_text("---\nname: demo\ndescription: demo skill\n---\n# Demo\n", encoding="utf-8")
    manager = SkillManager(tmp_path / "installed")
    item = manager.install(source)
    assert item.name == "demo"
    package = tmp_path / "demo.aura-skill"
    manager.pack(source, package)
    assert package.exists()

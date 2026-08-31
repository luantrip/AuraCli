"""Public /skill command."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

from aura_cli.application.artifacts import ArtifactLayout
from aura_cli.core.skills.manager import SkillManager


def handle_skill(args: str, app_loop: Any = None) -> Optional[str]:
    root = ArtifactLayout(project_root=getattr(app_loop, "project_root", None)).project("skills")
    manager = SkillManager(root)
    parts = args.split(maxsplit=1)
    command = parts[0].lower() if parts else "list"
    value = parts[1].strip() if len(parts) > 1 else ""
    if command == "list":
        skills = manager.list_installed()
        return "\n".join(f"{item.name} {item.version}: {item.description}" for item in skills) or "Nenhuma skill instalada."
    if command == "install" and value:
        item = manager.install(value)
        return f"Skill instalada: {item.name} {item.version}"
    if command == "remove" and value:
        manager.remove(value)
        return f"Skill removida: {value}"
    if command == "status" and value:
        item = manager.status(value)
        return f"{item.name} {item.version}\n{item.description}\n{item.path}"
    if command == "pack" and value:
        source = Path(value)
        output = source.with_suffix(".aura-skill")
        manager.pack(source, output)
        return f"Skill empacotada: {output}"
    if command == "search" and value:
        from aura_cli.core.personas.skill_retriever import SkillRetriever
        matches = SkillRetriever(include_installed=True).find_all_matches(value, limit=5, threshold=0.0)
        return "\n".join(f"{match.skill.name}: {match.skill.description}" for match in matches) or "Nenhuma skill encontrada."
    return "Uso: /skill list|install <path>|remove <name>|status <name>|pack <dir>"

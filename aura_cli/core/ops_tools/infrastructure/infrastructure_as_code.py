"""Infrastructure-as-Code template manager for the Ops agent.

Templates are persisted to disk under ``<project_root>/.aura/iac/templates.json``
so they survive process restarts.  Each template holds a provider
(aws / gcp / azure), a list of resource dicts, and a variables map.

Terraform export generates a ``main.tf`` file and runs ``terraform plan``
automatically.  Applying requires an explicit ``apply=True`` argument and
always prompts for confirmation before executing ``terraform apply``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import json
import os
from pathlib import Path
import subprocess
from typing import Any, Dict, List, Optional
import uuid

from aura_cli.application.artifacts import ArtifactLayout
from aura_cli.core.logger import get_logger
from aura_cli.core.stats import get_stats

logger = get_logger(__name__)


def _default_store_path() -> Path:
    """Return the canonical path for the IaC template store."""
    return ArtifactLayout().project("iac", "templates.json")


@dataclass
class InfrastructureTemplate:
    """Infrastructure template (id, name, provider, description, resources, variables)."""

    id: str
    name: str
    provider: str
    description: str
    resources: List[Dict[str, Any]] = field(default_factory=list)
    variables: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to plain dict for JSON persistence."""
        return {
            "id": self.id,
            "name": self.name,
            "provider": self.provider,
            "description": self.description,
            "resources": self.resources,
            "variables": self.variables,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> InfrastructureTemplate:
        """Deserialize from plain dict."""
        return cls(
            id=data["id"],
            name=data["name"],
            provider=data["provider"],
            description=data["description"],
            resources=data.get("resources", []),
            variables=data.get("variables", {}),
        )


class IaCManager:
    """Infrastructure-as-Code manager with disk persistence and Terraform export."""

    def __init__(self, store_path: Optional[Path] = None):
        """Initialize the IaC manager, loading any previously saved templates."""
        self.stats = get_stats()
        self._store_path = Path(store_path) if store_path else _default_store_path()
        self.templates: Dict[str, InfrastructureTemplate] = {}
        self._load_from_disk()

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    def create_template(
        self,
        name: str,
        provider: str,
        description: str,
        resources: List[Dict[str, Any]],
        variables: Optional[Dict[str, Any]] = None,
    ) -> InfrastructureTemplate:
        """Create and persist a new infrastructure template."""
        template = InfrastructureTemplate(
            id=str(uuid.uuid4())[:8],
            name=name,
            provider=provider,
            description=description,
            resources=resources,
            variables=variables or {},
        )
        self.templates[template.id] = template
        self._save_to_disk()
        logger.info("Template '%s' created (id=%s)", name, template.id)
        return template

    def get_template(self, template_id: str) -> Optional[InfrastructureTemplate]:
        """Return a template by id, or None if not found."""
        return self.templates.get(template_id)

    def delete_template(self, template_id: str) -> bool:
        """Delete a template by id. Returns True if it existed."""
        if template_id not in self.templates:
            return False
        name = self.templates[template_id].name
        del self.templates[template_id]
        self._save_to_disk()
        logger.info("Template '%s' (id=%s) deleted", name, template_id)
        return True

    def list_templates(self) -> List[Dict[str, Any]]:
        """Return summary dicts for all templates."""
        return [
            {
                "id": t.id,
                "name": t.name,
                "provider": t.provider,
                "description": t.description,
                "resources_count": len(t.resources),
            }
            for t in self.templates.values()
        ]

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _save_to_disk(self) -> None:
        """Atomically persist all templates to JSON."""
        try:
            self._store_path.parent.mkdir(parents=True, exist_ok=True)
            tmp = self._store_path.with_suffix(".tmp")
            tmp.write_text(
                json.dumps(
                    [t.to_dict() for t in self.templates.values()],
                    indent=2,
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            os.replace(tmp, self._store_path)
        except OSError as exc:
            logger.warning("Could not save IaC templates to disk: %s", exc)

    def _load_from_disk(self) -> None:
        """Load templates from disk if the store file exists."""
        if not self._store_path.is_file():
            return
        try:
            data = json.loads(self._store_path.read_text(encoding="utf-8"))
            for item in data:
                tmpl = InfrastructureTemplate.from_dict(item)
                self.templates[tmpl.id] = tmpl
            logger.debug(
                "Loaded %d IaC templates from %s", len(self.templates), self._store_path
            )
        except (OSError, json.JSONDecodeError, KeyError) as exc:
            logger.warning("Could not load IaC templates from disk: %s", exc)

    # ------------------------------------------------------------------
    # Terraform export, plan, and apply
    # ------------------------------------------------------------------

    def validate_template(self, template_id: str) -> Dict[str, Any]:
        """Validate a template's structure before export.

        Returns a dict with ``valid`` (bool) and ``errors`` (list[str]).
        """
        tmpl = self.get_template(template_id)
        if tmpl is None:
            return {"valid": False, "errors": [f"Template '{template_id}' not found"]}

        errors: List[str] = []
        valid_providers = {"aws", "gcp", "azure"}
        if tmpl.provider.lower() not in valid_providers:
            errors.append(
                f"Unknown provider '{tmpl.provider}'. Expected one of: {sorted(valid_providers)}"
            )
        if not tmpl.resources:
            errors.append("Template has no resources defined")
        for idx, res in enumerate(tmpl.resources):
            if not isinstance(res, dict):
                errors.append(f"Resource at index {idx} is not a dict")
            elif "type" not in res:
                errors.append(f"Resource at index {idx} is missing required 'type' key")

        return {"valid": len(errors) == 0, "errors": errors}

    def export_terraform(
        self, template_id: str, output_dir: Optional[str] = None
    ) -> Dict[str, Any]:
        """Generate a ``main.tf`` file from a template and run ``terraform plan``.

        The generated file is written to *output_dir* (defaults to the current
        working directory).  ``terraform plan`` is executed automatically and
        its output is returned.  No infrastructure is created.

        Returns a dict with keys: ``tf_file``, ``plan_output``, ``plan_returncode``.
        """
        validation = self.validate_template(template_id)
        if not validation["valid"]:
            return {
                "tf_file": None,
                "plan_output": "",
                "plan_returncode": -1,
                "errors": validation["errors"],
            }

        tmpl = self.templates[template_id]
        target_dir = Path(output_dir) if output_dir else Path.cwd()
        target_dir.mkdir(parents=True, exist_ok=True)
        tf_file = target_dir / "main.tf"

        tf_content = _build_terraform_hcl(tmpl)
        tf_file.write_text(tf_content, encoding="utf-8")
        logger.info("Generated %s for template '%s'", tf_file, tmpl.name)

        plan_output, plan_rc = _run_terraform_plan(target_dir)
        return {
            "tf_file": str(tf_file),
            "plan_output": plan_output,
            "plan_returncode": plan_rc,
        }

    def apply_template(
        self,
        template_id: str,
        output_dir: Optional[str] = None,
        *,
        apply: bool = False,
    ) -> Dict[str, Any]:
        """Export template, run plan, and optionally apply.

        ``apply=True`` is required to actually create infrastructure.
        The caller is responsible for obtaining explicit user confirmation
        before passing ``apply=True`` — this method will never prompt
        interactively.

        Returns a dict with ``tf_file``, ``plan_output``, ``apply_output``,
        ``apply_returncode`` and ``applied`` (bool).
        """
        result = self.export_terraform(template_id, output_dir)
        result["applied"] = False
        result["apply_output"] = ""
        result["apply_returncode"] = -1

        if not apply:
            return result

        if result.get("plan_returncode", -1) not in (0, 2):
            result["apply_output"] = "Skipped: terraform plan failed."
            return result

        target_dir = Path(output_dir) if output_dir else Path.cwd()
        apply_output, apply_rc = _run_terraform_apply(target_dir)
        result["apply_output"] = apply_output
        result["apply_returncode"] = apply_rc
        result["applied"] = apply_rc == 0
        return result


# ------------------------------------------------------------------
# Internal helpers (not part of the public API)
# ------------------------------------------------------------------

def _build_terraform_hcl(tmpl: InfrastructureTemplate) -> str:
    """Convert an InfrastructureTemplate to minimal HCL."""
    lines: List[str] = [
        f'# Generated by AuraCli IaCManager — template "{tmpl.name}" (provider: {tmpl.provider})\n',
        f'terraform {{\n  required_providers {{\n    {tmpl.provider.lower()} = {{}}\n  }}\n}}\n',
    ]
    if tmpl.variables:
        for var_name, var_default in tmpl.variables.items():
            default_expr = json.dumps(var_default)
            lines.append(
                f'\nvariable "{var_name}" {{\n  default = {default_expr}\n}}'
            )
    for resource in tmpl.resources:
        rtype = resource.get("type", "unknown")
        rname = resource.get("name", "main")
        attrs = {k: v for k, v in resource.items() if k not in ("type", "name")}
        attr_lines = "\n".join(
            f"  {k} = {json.dumps(v)}" for k, v in attrs.items()
        )
        lines.append(f'\nresource "{rtype}" "{rname}" {{\n{attr_lines}\n}}')
    return "\n".join(lines) + "\n"


def _run_terraform_plan(directory: Path) -> tuple[str, int]:
    """Run ``terraform init`` + ``terraform plan`` and return (output, returncode)."""
    if not _terraform_available():
        return "terraform binary not found in PATH", -1
    try:
        _run_subprocess(["terraform", "init", "-input=false"], cwd=directory)
        result = subprocess.run(
            ["terraform", "plan", "-input=false", "-no-color"],
            cwd=directory,
            capture_output=True,
            text=True,
            timeout=120,
        )
        combined = (result.stdout + result.stderr).strip()
        return combined, result.returncode
    except subprocess.TimeoutExpired:
        return "terraform plan timed out after 120 seconds", -1
    except OSError as exc:
        return f"Error running terraform plan: {exc}", -1


def _run_terraform_apply(directory: Path) -> tuple[str, int]:
    """Run ``terraform apply -auto-approve`` and return (output, returncode)."""
    if not _terraform_available():
        return "terraform binary not found in PATH", -1
    try:
        result = subprocess.run(
            ["terraform", "apply", "-auto-approve", "-input=false", "-no-color"],
            cwd=directory,
            capture_output=True,
            text=True,
            timeout=600,
        )
        combined = (result.stdout + result.stderr).strip()
        return combined, result.returncode
    except subprocess.TimeoutExpired:
        return "terraform apply timed out after 600 seconds", -1
    except OSError as exc:
        return f"Error running terraform apply: {exc}", -1


def _run_subprocess(cmd: List[str], cwd: Path) -> None:
    """Run a subprocess silently, raising OSError on failure."""
    subprocess.run(cmd, cwd=cwd, capture_output=True, check=False)


def _terraform_available() -> bool:
    """Return True if terraform is on PATH."""
    import shutil
    return shutil.which("terraform") is not None

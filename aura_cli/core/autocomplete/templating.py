"""Template system for Autocomplete.

Provides code templates for autocomplete suggestion generation.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from aura_cli.core.logger import get_logger
from aura_cli.core.stats import get_stats

logger = get_logger(__name__)


@dataclass
class TemplateVariable:
    """Template variable (name, default_value, description)."""

    name: str
    default_value: str = ""
    description: str = ""
    required: bool = True


@dataclass
class CodeTemplate:
    """A reusable code template with named variables."""

    template_id: str
    name: str
    template: str
    variables: List[TemplateVariable] = field(default_factory=list)
    description: str = ""


class TemplateEngine:
    """Manages and expands code templates."""

    def __init__(self):
        """Initialise the template engine."""
        self.templates: Dict[str, CodeTemplate] = {}
        self.stats = get_stats()

        self._load_default_templates()

        logger.info("TemplateEngine initialized")

    def register_template(
        self,
        name: str,
        template: str,
        variables: Optional[List[TemplateVariable]] = None,
        description: str = "",
    ) -> CodeTemplate:
        """Register a code template."""
        import uuid

        template_obj = CodeTemplate(
            template_id=str(uuid.uuid4())[:8],
            name=name,
            template=template,
            variables=variables or [],
            description=description,
        )

        self.templates[template_obj.template_id] = template_obj

        logger.debug(f"Template '{name}' registrado")

        return template_obj

    def expand_template(self, template_id: str, variables: Dict[str, str]) -> str:
        """Expand a template with the given variable values."""
        if template_id not in self.templates:
            logger.error(f"Template {template_id} not found")
            return ""

        template = self.templates[template_id]
        code = template.template

        for var in template.variables:
            var_name = var.name
            var_value = variables.get(var_name, var.default_value)

            code = code.replace(f"${{{var_name}}}", var_value)
            code = code.replace(f"{{{var_name}}}", var_value)

        return code

    def find_templates(self, query: str = "") -> List[CodeTemplate]:
        """Search templates by query string."""
        if not query:
            return list(self.templates.values())

        query_lower = query.lower()

        return [
            t
            for t in self.templates.values()
            if query_lower in t.name.lower() or query_lower in t.description.lower()
        ]

    def _load_default_templates(self) -> None:
        """Load the built-in default templates."""
        self.register_template(
            "function",
            'def ${name}(${params}):\n    """${docstring}"""\n    ${body}\n    return ${return_value}',
            [
                TemplateVariable("name", "function_name", "Function name"),
                TemplateVariable("params", "", "Parameters"),
                TemplateVariable("docstring", "", "Docstring"),
                TemplateVariable("body", "pass", "Function body"),
                TemplateVariable("return_value", "None", "Return value"),
            ],
            "Function template",
        )

        self.register_template(
            "class",
            'class ${name}(${base}):\n    """${docstring}"""\n    \n    def __init__(self${params}):\n        ${init_body}',
            [
                TemplateVariable("name", "ClassName", "Class name"),
                TemplateVariable("base", "", "Base class"),
                TemplateVariable("docstring", "", "Class docstring"),
                TemplateVariable("params", "", "Init parameters"),
                TemplateVariable("init_body", "pass", "Init body"),
            ],
            "Class template",
        )

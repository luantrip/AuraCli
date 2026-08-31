"""Advanced tool validator.

Provides schema, parameter and result validation before and after tool execution.
"""

from dataclasses import dataclass, field
from typing import (
    Any,
    Callable,
    Dict,
    List,
    Optional,
    Tuple,
)

from aura_cli.core.logger import get_logger

logger = get_logger(__name__)


@dataclass
class ToolSchema:
    """Schema definition for a tool (name, parameters, returns)."""

    name: str
    description: str
    parameters: Dict[str, Any]
    returns: Optional[Dict[str, Any]] = None
    required_params: List[str] = field(default_factory=list)


@dataclass
class ValidationError:
    """Validation error (field, message, code)."""

    field: str
    message: str
    code: str = "validation_error"


class ToolValidator:
    """Advanced tool validator."""

    def __init__(self):
        """Initialise the tool validator."""
        self.schemas: Dict[str, ToolSchema] = {}
        self.custom_validators: Dict[str, Callable] = {}

        logger.info("ToolValidator initialized")

    def register_schema(self, schema: ToolSchema) -> None:
        """Register a schema for a tool."""
        self.schemas[schema.name] = schema
        logger.debug(f"Schema registrado para ferramenta '{schema.name}'")

    def register_validator(
        self,
        tool_name: str,
        validator: Callable[[Dict[str, Any]], List[ValidationError]],
    ) -> None:
        """Register a custom validator function for a tool."""
        self.custom_validators[tool_name] = validator
        logger.debug(f"Validador customizado registrado para '{tool_name}'")

    def validate_parameters(
        self, tool_name: str, parameters: Dict[str, Any]
    ) -> List[ValidationError]:
        """Validate tool call parameters."""
        errors: list[Any] = []

        if tool_name not in self.schemas:
            return errors

        schema = self.schemas[tool_name]

        for param in schema.required_params:
            if param not in parameters:
                errors.append(
                    ValidationError(
                        field=param,
                        message=f"Parâmetro obrigatório '{param}' ausente",
                        code="missing_required",
                    )
                )

        if "properties" in schema.parameters:
            for param_name, param_schema in schema.parameters["properties"].items():
                if param_name in parameters:
                    param_value = parameters[param_name]
                    param_type = param_schema.get("type")

                    if param_type:
                        type_valid = self._validate_type(param_value, param_type)
                        if not type_valid:
                            errors.append(
                                ValidationError(
                                    field=param_name,
                                    message=f"Invalid type for '{param_name}': expected {param_type}",
                                    code="type_mismatch",
                                )
                            )

        if tool_name in self.custom_validators:
            custom_errors = self.custom_validators[tool_name](parameters)
            errors.extend(custom_errors)

        if errors:
            logger.warning(
                f"Validação de parâmetros falhou para '{tool_name}': "
                f"{len(errors)} erros"
            )
        else:
            logger.debug(f"Parâmetros de '{tool_name}' validados com sucesso")

        return errors

    def validate_result(self, tool_name: str, result: Any) -> List[ValidationError]:
        """Validate a tool call result."""
        errors: list[Any] = []

        if tool_name not in self.schemas:
            return errors

        schema = self.schemas[tool_name]

        if schema.returns:
            return_type = schema.returns.get("type")
            if return_type:
                type_valid = self._validate_type(result, return_type)
                if not type_valid:
                    errors.append(
                        ValidationError(
                            field="result",
                            message=f"Invalid return type: expected {return_type}",
                            code="return_type_mismatch",
                        )
                    )

        return errors

    def _validate_type(self, value: Any, expected_type: str) -> bool:
        """Return True if the value matches the expected type."""
        type_map = {
            "string": str,
            "integer": int,
            "number": (int, float),
            "boolean": bool,
            "array": list,
            "object": dict,
        }

        python_type = type_map.get(expected_type)
        if not python_type:
            return True

        return isinstance(value, python_type)  # type: ignore[arg-type]

    def validate_call(
        self, tool_name: str, parameters: Dict[str, Any], result: Optional[Any] = None
    ) -> Tuple[bool, List[ValidationError]]:
        """Validate a tool call against its schema."""
        errors = []

        param_errors = self.validate_parameters(tool_name, parameters)
        errors.extend(param_errors)

        if result is not None:
            result_errors = self.validate_result(tool_name, result)
            errors.extend(result_errors)

        return len(errors) == 0, errors

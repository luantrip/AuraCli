from aura_cli.application.editing import EditOperation, validate_edit_content


def test_validation_checks_resulting_python_document() -> None:
    operation = EditOperation(
        id="edit",
        file_path="module.py",
        old_content="return 1",
        new_content="return 2",
        description="change return",
    )

    result = validate_edit_content(operation, "def value():\n    return 1\n")

    assert result.valid is True
    assert result.syntax_valid is True


def test_validation_rejects_missing_source_fragment() -> None:
    operation = EditOperation("edit", "note.txt", "missing", "new", "change")

    result = validate_edit_content(operation, "current")

    assert result.valid is False
    assert "not found" in result.errors[0]


def test_validation_rejects_invalid_resulting_python() -> None:
    operation = EditOperation(
        "edit",
        "module.py",
        "return 1",
        "return )",
        "break syntax",
    )

    result = validate_edit_content(operation, "def value():\n    return 1\n")

    assert result.valid is False
    assert result.syntax_valid is False
    assert "resultante" in result.errors[-1]

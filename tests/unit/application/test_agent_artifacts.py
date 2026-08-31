import pytest

from aura_cli.application.agents import ArtifactKind, classify_artifact


@pytest.mark.parametrize(
    ("operation", "parameters", "expected"),
    [
        (
            "write_file",
            {"path": " src/new.py "},
            (ArtifactKind.GENERATED, "src/new.py"),
        ),
        ("edit_file", {"file_path": "src/app.py"}, (ArtifactKind.EDITED, "src/app.py")),
        (
            "read_file",
            {"test_path": "tests/test_app.py"},
            (ArtifactKind.ANALYZED, "tests/test_app.py"),
        ),
        ("unknown", {"path": "README.md"}, None),
        ("write_file", {"path": "."}, None),
        ("edit_file", {"path": "/"}, None),
        ("read_file", {}, None),
    ],
)
def test_classify_artifact(operation, parameters, expected) -> None:
    assert classify_artifact(operation, parameters) == expected


def test_classification_prefers_path_fields_in_contract_order() -> None:
    assert classify_artifact(
        "write_file",
        {"path": "primary.py", "file_path": "secondary.py"},
    ) == (ArtifactKind.GENERATED, "primary.py")

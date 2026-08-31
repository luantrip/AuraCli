"""Trust-boundary contracts for dynamic extensions."""

from unittest.mock import patch

from aura_cli.core.extensions.extension_loader import ExtensionLoader


def test_untrusted_extension_is_blocked_before_execution(tmp_path) -> None:
    extension = tmp_path / "external.py"
    extension.write_text("raise RuntimeError('must not execute')", encoding="utf-8")
    loader = ExtensionLoader(extensions_dir=str(tmp_path))

    with patch(
        "aura_cli.core.extensions.extension_loader.importlib.util.spec_from_file_location"
    ) as create_spec:
        loaded = loader.load_extension(str(extension))

    assert loaded is None
    create_spec.assert_not_called()
    assert loader.extensions == {}


def test_explicit_opt_in_allows_audited_external_extension(tmp_path) -> None:
    extension = tmp_path / "external.py"
    extension.write_text(
        "initialized = False\n"
        "def initialize():\n"
        "    global initialized\n"
        "    initialized = True\n",
        encoding="utf-8",
    )
    loader = ExtensionLoader(
        extensions_dir=str(tmp_path), allow_untrusted_extensions=True
    )

    loaded = loader.load_extension(str(extension))

    assert loaded is not None
    assert loaded.is_loaded is True
    assert loaded.module.initialized is True


def test_extension_inside_trusted_root_loads_without_opt_in(tmp_path) -> None:
    trusted_root = tmp_path / "trusted"
    trusted_root.mkdir()
    extension = trusted_root / "trusted_extension.py"
    extension.write_text("VALUE = 42\n", encoding="utf-8")
    loader = ExtensionLoader(extensions_dir=str(trusted_root))

    with patch(
        "aura_cli.core.extensions.extension_loader.TRUSTED_EXTENSION_DIRS",
        [str(trusted_root)],
    ):
        loaded = loader.load_extension(str(extension))

    assert loaded is not None
    assert loaded.module.VALUE == 42


def test_symlink_escape_from_trusted_root_is_blocked(tmp_path) -> None:
    trusted_root = tmp_path / "trusted"
    trusted_root.mkdir()
    external = tmp_path / "external.py"
    external.write_text("VALUE = 42\n", encoding="utf-8")
    link = trusted_root / "linked.py"
    link.symlink_to(external)
    loader = ExtensionLoader(extensions_dir=str(trusted_root))

    with patch(
        "aura_cli.core.extensions.extension_loader.TRUSTED_EXTENSION_DIRS",
        [str(trusted_root)],
    ):
        loaded = loader.load_extension(str(link))

    assert loaded is None


def test_validation_failure_never_falls_through_to_execution(tmp_path) -> None:
    trusted_root = tmp_path / "trusted"
    trusted_root.mkdir()
    extension = trusted_root / "broken.py"
    extension.write_text("VALUE = 42\n", encoding="utf-8")
    loader = ExtensionLoader(extensions_dir=str(trusted_root))

    with (
        patch(
            "aura_cli.core.extensions.extension_loader.TRUSTED_EXTENSION_DIRS",
            [str(trusted_root)],
        ),
        patch("builtins.open", side_effect=OSError("read denied")),
        patch(
            "aura_cli.core.extensions.extension_loader.importlib.util.spec_from_file_location"
        ) as create_spec,
    ):
        loaded = loader.load_extension(str(extension))

    assert loaded is None
    create_spec.assert_not_called()

"""File operations for Paint tool.

This module contains file-related operations that can be used as mixins
or utilities for the Paint class.
"""

import asyncio
import logging
import os
from typing import TYPE_CHECKING, Callable, Optional

try:
    from PIL import Image

    _PIL_AVAILABLE = True
except ImportError:
    Image = None  # type: ignore[assignment]
    _PIL_AVAILABLE = False

if TYPE_CHECKING:
    from aura_cli.tui.tools.paint.paint import Paint

from aura_cli.application.paint.ansi_art_document import (
    SAVE_DISABLED_FORMATS,
    AnsiArtDocument,
    FormatWriteNotSupported,
)
from aura_cli.application.paint.backup_policy import (
    BackupDecision,
    backup_path,
    decide_backup,
)
from aura_cli.application.paint.localization.i18n import get as _
from aura_cli.application.paint.save_policy import SaveWarning, plan_format_save
from aura_cli.tui.tools.paint.__init__ import PYTEST

MAX_FILE_SIZE = 500 * 1024 * 1024  # 500 MB
logger = logging.getLogger(__name__)


def get_backup_file_path(
    paint_instance: "Paint", session_number: Optional[int] = None
) -> str:
    """Get the backup file path.

    Args:
        paint_instance: The Paint instance
        session_number: Optional session number for numbered backups

    Returns:
        Backup file path
    """
    return str(
        backup_path(
            file_path=paint_instance.file_path,
            backup_folder=paint_instance.backup_folder,
            untitled_name=_("Untitled"),
            session_number=session_number,
        )
    )


def save_backup(paint_instance: "Paint") -> None:
    """Save to the backup file if there have been changes since it was saved.

    Args:
        paint_instance: The Paint instance
    """
    decision = decide_backup(
        saved_action_count=paint_instance.backup_saved_undo_count,
        current_action_count=len(paint_instance.undos),
        has_preview=paint_instance.image_has_preview(),
    )
    if decision is BackupDecision.SKIP:
        return
    if decision is BackupDecision.DEFER_UNTIL_PREVIEW_ENDS:
        paint_instance.save_backup_after_cancel_preview = True
        return

    backup_file_path = get_backup_file_path(paint_instance)
    session_number = 1
    while (
        os.path.exists(backup_file_path)
        and backup_file_path != paint_instance.backup_checked_for
    ):
        backup_file_path = get_backup_file_path(
            paint_instance, session_number=session_number
        )
        session_number += 1
        if session_number > 100:
            backup_file_path = get_backup_file_path(paint_instance)
            break

    if paint_instance.file_path:
        format_id = AnsiArtDocument.format_from_extension(paint_instance.file_path)
        if format_id in ["PNG", "JPEG", "BMP", "WEBP"]:
            backup_bytes = paint_instance.image.encode_image_format(format_id)
            write_file_path(
                paint_instance,
                backup_file_path,
                backup_bytes,
                _("Backup Save Failed"),
            )
        else:
            ansi = paint_instance.image.get_ansi()
            ansi_bytes = ansi.encode("utf-8")
            write_file_path(
                paint_instance, backup_file_path, ansi_bytes, _("Backup Save Failed")
            )
    else:
        ansi = paint_instance.image.get_ansi()
        ansi_bytes = ansi.encode("utf-8")
        write_file_path(
            paint_instance, backup_file_path, ansi_bytes, _("Backup Save Failed")
        )
    paint_instance.backup_saved_undo_count = len(paint_instance.undos)


def recover_from_backup(paint_instance: "Paint") -> None:
    """Recover from the backup file, if it exists.

    Args:
        paint_instance: The Paint instance
    """
    if PYTEST:
        print("Skipping recover_from_backup in pytest")
        return
    backup_file_path = get_backup_file_path(paint_instance)
    print(
        "Checking for backup at:",
        backup_file_path,
        (
            "...it exists"
            if os.path.exists(backup_file_path)
            else "...it does not exist"
        ),
    )
    if os.path.exists(backup_file_path):
        try:
            if os.path.getsize(backup_file_path) > MAX_FILE_SIZE:
                paint_instance.message_box(
                    _("Open"),
                    _("A backup file was found, but was not recovered.")
                    + "\n"
                    + _("The file is too large to open."),
                    "ok",
                )
                return
            backup_format = AnsiArtDocument.format_from_extension(backup_file_path)
            if backup_format in ["PNG", "JPEG", "BMP", "WEBP"]:
                with open(backup_file_path, "rb") as f:
                    backup_bytes = f.read()
                backup_image = AnsiArtDocument.from_image_format(backup_bytes)
            else:
                with open(backup_file_path, encoding="utf-8") as f:
                    backup_content = f.read()
                backup_image = AnsiArtDocument.from_text(backup_content)
            paint_instance.backup_checked_for = backup_file_path
        except Exception as e:
            context = _("A backup file was found, but was not recovered.")
            paint_instance._handle_operation_error(
                _("Recover from backup"),
                e,
                context=context,
            )
            return
        paint_instance.resize_document(backup_image.width, backup_image.height)
        paint_instance.undos[-1].name = _("Recover from backup")
        paint_instance.canvas.image = paint_instance.image = backup_image
        paint_instance.canvas.refresh(layout=True)
        paint_instance.backup_saved_undo_count = len(paint_instance.undos)

        def handle_button(button) -> None:
            if button.has_class("no"):
                paint_instance.action_undo()

        backup_mtime = os.path.getmtime(backup_file_path)
        main_file_mtime = None
        if paint_instance.file_path and os.path.exists(paint_instance.file_path):
            main_file_mtime = os.path.getmtime(paint_instance.file_path)
            if backup_mtime > main_file_mtime:
                message = _(
                    "Recovered document from backup (backup is newer than main file).\nKeep changes?"
                )
            else:
                message = _(
                    "Recovered document from backup (main file is newer).\nKeep changes?"
                )
        else:
            message = _("Recovered document from backup.\nKeep changes?")

        paint_instance.message_box(
            _("Paint"),
            message,
            "yes/no",
            handle_button,
        )
    else:
        paint_instance.backup_checked_for = backup_file_path


def write_file_path(
    paint_instance: "Paint", file_path: str, content: bytes, dialog_title: str
) -> bool:
    """Write a file, showing an error message and returning False if it fails.

    Args:
        paint_instance: The Paint instance
        file_path: Path to write to
        content: Content to write
        dialog_title: Title for error dialogs

    Returns:
        True if successful, False otherwise
    """
    try:
        with open(file_path, "wb") as f:
            f.write(content)
        return True
    except PermissionError:
        paint_instance.message_box(dialog_title, _("Access denied."), "ok")
    except FileNotFoundError:
        paint_instance._handle_file_error(
            file_path, dialog_title, FileNotFoundError(f"Invalid path: {file_path}")
        )
    except OSError as e:
        paint_instance._handle_file_error(file_path, dialog_title, e)
    except Exception as e:
        paint_instance._handle_file_error(file_path, dialog_title, e)
    return False


def reload_after_save(paint_instance: "Paint", content: bytes, file_path: str) -> bool:
    """Reload the document from saved content.

    Args:
        paint_instance: The Paint instance
        content: Saved content
        file_path: Path to the file

    Returns:
        True if successful, False otherwise
    """
    try:
        paint_instance.resize_document(
            paint_instance.image.width, paint_instance.image.height
        )
        new_image = AnsiArtDocument.decode_based_on_file_extension(content, file_path)
        paint_instance.canvas.image = paint_instance.image = new_image
        paint_instance.canvas.refresh(layout=True)
        paint_instance.saved_undo_count = len(paint_instance.undos)
        update_palette_from_format_id(
            paint_instance,
            AnsiArtDocument.format_from_extension(file_path),
        )
        return True
    except Exception as e:
        paint_instance._handle_file_error(file_path, _("Open"), e)
        return False


def update_palette_from_format_id(
    paint_instance: "Paint", format_id: str | None
) -> None:
    """Update the palette based on the file format.

    Args:
        paint_instance: The Paint instance
        format_id: Format identifier
    """
    from aura_cli.application.paint.palette_data import IRC_PALETTE

    if format_id == "IRC":
        paint_instance.palette = IRC_PALETTE + (IRC_PALETTE[0],) * (
            len(paint_instance.palette) - len(IRC_PALETTE)
        )
    elif format_id == "PLAINTEXT":
        paint_instance.palette = ("#000000", "#ffffff") + ("#ffffff",) * (
            len(paint_instance.palette) - 2
        )


async def save(paint_instance: "Paint") -> bool:
    """Save the image to a file.

    Args:
        paint_instance: The Paint instance

    Returns:
        True if successful, False otherwise
    """
    paint_instance.stop_action_in_progress()
    dialog_title = _("Save")
    if paint_instance.file_path:
        format_id = AnsiArtDocument.format_from_extension(paint_instance.file_path)
        should_reload = await confirm_information_loss_async(paint_instance, format_id)
        try:
            content = paint_instance.image.encode_to_format(format_id)
        except FormatWriteNotSupported as e:
            paint_instance.message_box(_("Save"), e.localized_message, "ok")
            return False
        if write_file_path(
            paint_instance, paint_instance.file_path, content, dialog_title
        ):
            paint_instance.saved_undo_count = len(paint_instance.undos)
            if should_reload:
                return reload_after_save(
                    paint_instance, content, paint_instance.file_path
                )
            return True
        else:
            return False
    else:
        await save_as(paint_instance)
        return True


async def save_as(paint_instance: "Paint") -> None:
    """Save the image as a new file.

    Args:
        paint_instance: The Paint instance
    """
    from aura_cli.tui.tools.paint.file_dialogs import SaveAsDialogWindow

    paint_instance.stop_action_in_progress()
    paint_instance.close_windows("SaveAsDialogWindow, OpenDialogWindow")

    saved_future: asyncio.Future[None] = asyncio.Future()

    def handle_selected_file_path(file_path: str) -> None:
        format_id = AnsiArtDocument.format_from_extension(file_path)
        reload_after_save_flag = False

        def on_save_confirmed() -> None:
            async def async_on_save_confirmed() -> None:
                paint_instance.stop_action_in_progress()
                try:
                    content = paint_instance.image.encode_to_format(format_id)
                except FormatWriteNotSupported as e:
                    paint_instance.message_box(_("Save As"), e.localized_message, "ok")
                    return

                success = write_file_path(
                    paint_instance, file_path, content, _("Save As")
                )
                if success:
                    discard_backup(paint_instance)
                    paint_instance.file_path = file_path
                    paint_instance.saved_undo_count = len(paint_instance.undos)
                    window.close()
                    if reload_after_save_flag and not reload_after_save(
                        paint_instance, content, file_path
                    ):
                        return
                    saved_future.set_result(None)

                recover_from_backup(paint_instance)

            task = asyncio.create_task(async_on_save_confirmed())
            paint_instance.background_tasks.add(task)
            task.add_done_callback(paint_instance.background_tasks.discard)

        def after_confirming_any_information_loss(should_reload: bool) -> None:
            nonlocal reload_after_save_flag
            reload_after_save_flag = should_reload
            if os.path.exists(file_path):
                confirm_overwrite(paint_instance, file_path, on_save_confirmed)
            else:
                on_save_confirmed()

        confirm_information_loss(
            paint_instance, format_id, after_confirming_any_information_loss
        )

    window = SaveAsDialogWindow(
        title=_("Save As"),
        handle_selected_file_path=handle_selected_file_path,
        selected_file_path=paint_instance.file_path,
        file_name=os.path.basename(paint_instance.file_path or _("Untitled")),
        auto_add_default_extension=".ans",
    )
    await paint_instance.mount(window)
    await saved_future


def open_from_file_path(
    paint_instance: "Paint", file_path: str, opened_callback: Callable[[], None]
) -> None:
    """Opens the given file for editing, prompting to save changes if necessary.

    Args:
        paint_instance: The Paint instance
        file_path: Path to the file to open
        opened_callback: Callback to call after opening
    """
    if paint_instance.file_path:
        current_file_stat = None
        opened = False
        try:
            current_file_stat = os.stat(paint_instance.file_path)
            try:
                file_to_be_opened_stat = os.stat(file_path)
                if os.path.samestat(current_file_stat, file_to_be_opened_stat):
                    opened = True
                    return
            except FileNotFoundError:
                error_msg = (
                    f"{file_path}\n"
                    f"{_('File not found.')}\n"
                    f"{_('Please verify that the correct path and file name are given.')}"
                )
                paint_instance.message_box(_("Open"), error_msg, "ok")
                return
            except Exception as e:
                context = _("Error accessing file: %1", file_path)
                paint_instance._handle_operation_error(_("Open"), e, context=context)
                return
        except FileNotFoundError as error:
            logger.debug("Current Paint document no longer exists", exc_info=error)
        except Exception as e:
            context = _(
                "An unknown error occurred while accessing %1.",
                paint_instance.file_path,
            )
            paint_instance._handle_operation_error(_("Open"), e, context=context)
            return
        if opened:
            opened_callback()
    try:
        if os.path.getsize(file_path) > MAX_FILE_SIZE:
            paint_instance.message_box(
                _("Open"), _("The file is too large to open."), "ok"
            )
            return
        with open(file_path, "rb") as f:
            content = f.read()

        def go_ahead():
            new_image = AnsiArtDocument.decode_based_on_file_extension(
                content, file_path
            )

            opening_backup = False
            try:
                backup_file_path = get_backup_file_path(paint_instance)
                if os.path.samefile(file_path, backup_file_path):
                    print(
                        "Not discarding backup because it is now open in the editor:",
                        backup_file_path,
                    )
                    opening_backup = True
            except (FileNotFoundError, OSError) as error:
                logger.debug("Open target is not the active backup", exc_info=error)
            if not opening_backup:
                discard_backup(paint_instance)

            paint_instance.action_new(force=True, manage_backup=False)
            paint_instance.canvas.image = paint_instance.image = new_image
            paint_instance.canvas.refresh(layout=True)
            paint_instance.file_path = file_path
            from aura_cli.tui.tools.paint.recent_files import add_recent_file

            add_recent_file(file_path)
            update_palette_from_format_id(
                paint_instance,
                AnsiArtDocument.format_from_extension(file_path),
            )
            opened_callback()
            recover_from_backup(paint_instance)

        if paint_instance.is_document_modified():
            prompt_save_changes(
                paint_instance, paint_instance.file_path or _("Untitled"), go_ahead
            )
        else:
            go_ahead()
    except Exception as e:
        paint_instance._handle_file_error(file_path, _("Open"), e)


def discard_backup(paint_instance: "Paint") -> None:
    """Deletes the backup file, if it exists.

    Args:
        paint_instance: The Paint instance
    """
    backup_file_path = get_backup_file_path(paint_instance)
    if paint_instance.backup_checked_for != backup_file_path:
        print(
            f"Not discarding backup {backup_file_path!r} because it doesn't match "
            f"the backup file checked for: {paint_instance.backup_checked_for!r}"
        )
        return
    print("Discarding backup (if it exists):", backup_file_path)
    try:
        os.remove(backup_file_path)
    except FileNotFoundError:
        logger.debug("Paint backup was already absent: %s", backup_file_path)
    except PermissionError as error:
        logger.warning("Paint backup could not be removed", exc_info=error)
    except Exception as e:
        paint_instance._handle_operation_error(
            _("Delete backup"),
            e,
            context=_(
                "An unexpected error occurred while deleting the backup file %1.",
                backup_file_path,
            ),
        )


def confirm_overwrite(
    paint_instance: "Paint", file_path: str, callback: Callable[[], None]
) -> None:
    """Confirm overwriting an existing file.

    Args:
        paint_instance: The Paint instance
        file_path: Path to the file
        callback: Callback to call if confirmed
    """
    from textual.widgets import Button

    def handle_button(button: Button) -> None:
        if button.has_class("yes"):
            callback()

    paint_instance.message_box(
        _("Save As"),
        _("%1 already exists.\nDo you want to replace it?", file_path),
        "yes/no",
        handle_button,
    )


def confirm_no_undo(paint_instance: "Paint", callback: Callable[[], None]) -> None:
    """Confirm action that cannot be undone.

    Args:
        paint_instance: The Paint instance
        callback: Callback to call if confirmed
    """
    from textual.widgets import Button

    def handle_button(button: Button) -> None:
        if button.has_class("yes"):
            callback()

    paint_instance.message_box(
        _("Paint"),
        _("This action cannot be undone.\nDo you want to continue?"),
        "yes/no",
        handle_button,
    )


def prompt_save_changes(
    paint_instance: "Paint", file_path: str, callback: Callable[[], None]
) -> None:
    """Prompt to save changes before continuing.

    Args:
        paint_instance: The Paint instance
        file_path: Path to the file
        callback: Callback to call after handling
    """
    from textual.widgets import Button

    message = _("Save changes to %1?", file_path)

    async def async_handle_button(button: Button) -> None:
        if button.has_class("yes"):
            if not await save(paint_instance):
                return
        elif button.has_class("no"):
            pass
        else:
            return
        callback()

    def handle_button(button: Button) -> None:
        task = asyncio.create_task(async_handle_button(button))
        paint_instance.background_tasks.add(task)
        task.add_done_callback(paint_instance.background_tasks.discard)

    paint_instance.message_box(_("Paint"), message, "yes/no/cancel", handle_button)


def confirm_lose_color_information(
    paint_instance: "Paint", callback: Callable[[], None]
) -> None:
    """Confirm losing color information.

    Args:
        paint_instance: The Paint instance
        callback: Callback to call if confirmed
    """
    from textual.widgets import Button

    message = (
        _(
            "Saving into this format will cause loss of any text information "
            "(letters, numbers, or symbols.)"
        )
        + "\n"
        + _("Do you want to continue?")
    )

    def handle_button(button: Button) -> None:
        if button.has_class("yes"):
            callback()

    paint_instance.message_box(_("Paint"), message, "yes/no", handle_button)


def confirm_lose_text_information(
    paint_instance: "Paint", callback: Callable[[], None]
) -> None:
    """Confirm losing text information.

    Args:
        paint_instance: The Paint instance
        callback: Callback to call if confirmed
    """
    from textual.widgets import Button

    message = (
        _(
            "Saving into this format will cause loss of any text information "
            "(letters, numbers, or symbols.)"
        )
        + "\n"
        + _("Do you want to continue?")
    )

    def handle_button(button: Button) -> None:
        if button.has_class("yes"):
            callback()

    paint_instance.message_box(_("Paint"), message, "yes/no", handle_button)


def confirm_save_non_openable_file(
    paint_instance: "Paint", callback: Callable[[], None]
) -> None:
    """Confirm saving to a non-openable format.

    Args:
        paint_instance: The Paint instance
        callback: Callback to call if confirmed
    """
    from textual.widgets import Button

    message = (
        _("This format can only be saved, not opened.")
        + "\n"
        + _("Do you want to continue?")
    )

    def handle_button(button: Button) -> None:
        if button.has_class("yes"):
            callback()

    paint_instance.message_box(_("Paint"), message, "yes/no", handle_button)


def confirm_information_loss(
    paint_instance: "Paint",
    format_id: str | None,
    callback: Callable[[bool], None],
) -> None:
    """Confirm discarding information when saving as a particular format.

    Args:
        paint_instance: The Paint instance
        format_id: Format identifier
        callback: Callback with should_reload flag
    """
    plan = plan_format_save(
        format_id,
        image_save_formats=set(Image.SAVE),
        image_open_formats=set(Image.OPEN),
        save_disabled_formats=set(SAVE_DISABLED_FORMATS),
    )

    def confirm_at(index: int) -> None:
        if index == len(plan.warnings):
            callback(plan.reload_after_save)
            return
        warning = plan.warnings[index]

        def continuation() -> None:
            confirm_at(index + 1)

        if warning is SaveWarning.COLOR_LOSS:
            confirm_lose_color_information(paint_instance, continuation)
        elif warning is SaveWarning.TEXT_LOSS:
            confirm_lose_text_information(paint_instance, continuation)
        else:
            confirm_save_non_openable_file(paint_instance, continuation)

    confirm_at(0)


async def confirm_information_loss_async(
    paint_instance: "Paint", format_id: str | None
) -> bool:
    """Confirm discarding information (awaitable variant).

    Args:
        paint_instance: The Paint instance
        format_id: Format identifier

    Returns:
        Whether to reload after save
    """
    future = asyncio.get_running_loop().create_future()
    confirm_information_loss(
        paint_instance, format_id, lambda result: future.set_result(result)
    )
    return await future


def is_document_modified(paint_instance: "Paint") -> bool:
    """Returns whether the document has been modified since the last save.

    Args:
        paint_instance: The Paint instance

    Returns:
        True if modified, False otherwise
    """
    return len(paint_instance.undos) != paint_instance.saved_undo_count


async def export_image(paint_instance: "Paint") -> None:
    """Export the image to a file in various formats without changing the current document.

    This function allows exporting the image to different formats (PNG, JPEG, SVG, etc.)
    without modifying the current file path or saved state of the document.

    Args:
        paint_instance: The Paint instance
    """
    from aura_cli.tui.tools.paint.file_dialogs import SaveAsDialogWindow

    paint_instance.stop_action_in_progress()
    paint_instance.close_windows("SaveAsDialogWindow, OpenDialogWindow")

    exported_future: asyncio.Future[None] = asyncio.Future()

    def handle_selected_file_path(file_path: str) -> None:
        format_id = AnsiArtDocument.format_from_extension(file_path)
        reload_after_save_flag = False

        def on_export_confirmed() -> None:
            async def async_on_export_confirmed() -> None:
                paint_instance.stop_action_in_progress()
                try:
                    content = paint_instance.image.encode_to_format(format_id)
                except FormatWriteNotSupported as e:
                    paint_instance.message_box(_("Export"), e.localized_message, "ok")
                    return

                success = write_file_path(
                    paint_instance, file_path, content, _("Export")
                )
                if success:
                    window.close()
                    if reload_after_save_flag and not reload_after_save(
                        paint_instance, content, file_path
                    ):
                        return
                    exported_future.set_result(None)

            task = asyncio.create_task(async_on_export_confirmed())
            paint_instance.background_tasks.add(task)
            task.add_done_callback(paint_instance.background_tasks.discard)

        def after_confirming_any_information_loss(should_reload: bool) -> None:
            nonlocal reload_after_save_flag
            reload_after_save_flag = should_reload
            if os.path.exists(file_path):
                confirm_overwrite(paint_instance, file_path, on_export_confirmed)
            else:
                on_export_confirmed()

        confirm_information_loss(
            paint_instance, format_id, after_confirming_any_information_loss
        )

    base_name = os.path.basename(paint_instance.file_path or _("Untitled"))
    name_without_ext = os.path.splitext(base_name)[0]

    window = SaveAsDialogWindow(
        title=_("Export Image"),
        handle_selected_file_path=handle_selected_file_path,
        selected_file_path=None,
        file_name=name_without_ext,
        auto_add_default_extension=".png",
    )
    await paint_instance.mount(window)
    await exported_future

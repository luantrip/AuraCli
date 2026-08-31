"""UI composition helper for Paint tool."""

from typing import TYPE_CHECKING

from textual.app import ComposeResult
from textual.containers import Container
from textual.widgets import Header, Static

if TYPE_CHECKING:
    from aura_cli.tui.tools.paint.paint import Paint

from aura_cli.application.paint.localization.i18n import get as _
from aura_cli.application.paint.localization.i18n import remove_hotkey
from aura_cli.tui.tools.paint.args import args
from aura_cli.tui.tools.paint.canvas import Canvas
from aura_cli.tui.tools.paint.chat_window import ChatWindow
from aura_cli.tui.tools.paint.colors_box import ColorsBox
from aura_cli.tui.tools.paint.layer_panel import LayerManagementPanel
from aura_cli.tui.tools.paint.menus import Menu, MenuBar, MenuItem, Separator
from aura_cli.tui.tools.paint.toolbox import ToolsBox


def create_compose(paint_instance: "Paint") -> ComposeResult:
    """Create the UI composition for Paint.

    Args:
        paint_instance: The Paint instance

    Yields:
        UI widgets
    """
    paint_instance.chat_window = ChatWindow(
        id="chat_window", classes="chat_window", display=False
    )
    yield Header()
    with Container(id="paint"):
        yield MenuBar(
            [
                MenuItem(
                    remove_hotkey(_("&File")),
                    submenu=Menu(
                        [
                            MenuItem(
                                _("&New\tCtrl+N"),
                                paint_instance.action_new,
                                57600,
                                description=_("Creates a new document."),
                            ),
                            MenuItem(
                                _("&Open...\tCtrl+O"),
                                paint_instance.action_open,
                                57601,
                                description=_("Opens an existing document."),
                            ),
                            MenuItem(
                                _("&Save\tCtrl+S"),
                                paint_instance.action_save,
                                57603,
                                description=_("Saves the active document."),
                            ),
                            MenuItem(
                                _("Save &As..."),
                                paint_instance.action_save_as,
                                57604,
                                description=_(
                                    "Saves the active document with a new name."
                                ),
                            ),
                            Separator(),
                            MenuItem(
                                _("Print Pre&view"),
                                paint_instance.action_print_preview,
                                57609,
                                grayed=True,
                                description=_("Displays full pages."),
                            ),
                            MenuItem(
                                _("Page Se&tup..."),
                                paint_instance.action_page_setup,
                                57605,
                                grayed=True,
                                description=_("Changes the page layout."),
                            ),
                            MenuItem(
                                _("&Print...\tCtrl+P"),
                                paint_instance.action_print,
                                57607,
                                grayed=True,
                                description=_(
                                    "Prints the active document and sets printing options."
                                ),
                            ),
                            Separator(),
                            MenuItem(
                                _("S&end..."),
                                paint_instance.action_send,
                                37662,
                                grayed=True,
                                description=_("Sends a picture by using mail or fax."),
                            ),
                            Separator(),
                            MenuItem(
                                _("Set As &Wallpaper (Tiled)"),
                                paint_instance.action_set_as_wallpaper_tiled,
                                57677,
                                description=_(
                                    "Tiles this bitmap as the desktop wallpaper."
                                ),
                            ),
                            MenuItem(
                                _("Set As Wa&llpaper (Centered)"),
                                paint_instance.action_set_as_wallpaper_centered,
                                57675,
                                description=_(
                                    "Centers this bitmap as the desktop wallpaper."
                                ),
                            ),
                            Separator(),
                            MenuItem(
                                _("Recent File"),
                                paint_instance.action_recent_file,
                                57616,
                                grayed=True,
                                description=_("Opens this document."),
                            ),
                            Separator(),
                            MenuItem(
                                _("E&xit\tCtrl+Q"),
                                paint_instance.action_exit,
                                57665,
                                description=_("Quits Paint."),
                            ),
                        ]
                    ),
                ),
                MenuItem(
                    remove_hotkey(_("&Edit")),
                    submenu=Menu(
                        [
                            MenuItem(
                                _("&Undo\tCtrl+Z"),
                                paint_instance.action_undo,
                                57643,
                                description=_("Undoes the last action."),
                            ),
                            MenuItem(
                                _("&Repeat\tF4"),
                                paint_instance.action_redo,
                                57644,
                                description=_("Redoes the previously undone action."),
                            ),
                            Separator(),
                            MenuItem(
                                _("Cu&t\tCtrl+X"),
                                paint_instance.action_cut,
                                57635,
                                description=_(
                                    "Cuts the selection and puts it on the Clipboard."
                                ),
                            ),
                            MenuItem(
                                _("&Copy\tCtrl+C"),
                                paint_instance.action_copy,
                                57634,
                                description=_(
                                    "Copies the selection and puts it on the Clipboard."
                                ),
                            ),
                            MenuItem(
                                _("&Paste\tCtrl+V"),
                                paint_instance.action_paste,
                                57637,
                                description=_("Inserts the contents of the Clipboard."),
                            ),
                            MenuItem(
                                _("C&lear Selection\tDel"),
                                paint_instance.action_clear_selection,
                                57632,
                                description=_("Deletes the selection."),
                            ),
                            MenuItem(
                                _("Select &All\tCtrl+A"),
                                paint_instance.action_select_all,
                                57642,
                                description=_("Selects everything."),
                            ),
                            Separator(),
                            MenuItem(
                                _("C&opy To..."),
                                paint_instance.action_copy_to,
                                37663,
                                grayed=not paint_instance.image.selection
                                if hasattr(paint_instance, "image")
                                and paint_instance.image
                                else True,
                                description=_("Copies the selection to a file."),
                            ),
                            MenuItem(
                                _("Paste &From..."),
                                paint_instance.action_paste_from,
                                37664,
                                description=_("Pastes a file into the selection."),
                            ),
                        ]
                    ),
                ),
                MenuItem(
                    remove_hotkey(_("&View")),
                    submenu=Menu(
                        [
                            MenuItem(
                                _("&Tool Box\tCtrl+T"),
                                paint_instance.action_toggle_tools_box,
                                59415,
                                description=_("Shows or hides the tool box."),
                            ),
                            MenuItem(
                                _("&Color Box\tCtrl+L"),
                                paint_instance.action_toggle_colors_box,
                                59416,
                                description=_("Shows or hides the color box."),
                            ),
                            MenuItem(
                                _("&Status Bar"),
                                paint_instance.action_toggle_status_bar,
                                59393,
                                description=_("Shows or hides the status bar."),
                            ),
                            MenuItem(
                                _("T&ext Toolbar"),
                                paint_instance.action_text_toolbar,
                                37678,
                                grayed=True,
                                description=_("Shows or hides the text toolbar."),
                            ),
                            Separator(),
                            MenuItem(
                                _("&Zoom"),
                                submenu=Menu(
                                    [
                                        MenuItem(
                                            _("&Normal Size\tCtrl+PgUp"),
                                            paint_instance.action_normal_size,
                                            37670,
                                            description=_("Zooms the picture to 100%."),
                                        ),
                                        MenuItem(
                                            _("&Large Size\tCtrl+PgDn"),
                                            paint_instance.action_large_size,
                                            37671,
                                            description=_("Zooms the picture to 400%."),
                                        ),
                                        MenuItem(
                                            _("C&ustom..."),
                                            paint_instance.action_custom_zoom,
                                            37672,
                                            description=_("Zooms the picture."),
                                        ),
                                        Separator(),
                                        MenuItem(
                                            _("Show &Grid\tCtrl+G"),
                                            paint_instance.action_toggle_grid,
                                            37677,
                                            description=_("Shows or hides the grid."),
                                        ),
                                        MenuItem(
                                            _("Show T&humbnail"),
                                            paint_instance.action_toggle_thumbnail,
                                            37676,
                                            grayed=True,
                                            description=_(
                                                "Shows or hides the thumbnail view of the picture."
                                            ),
                                        ),
                                    ]
                                ),
                            ),
                            MenuItem(
                                _("&View Bitmap\tCtrl+F"),
                                paint_instance.action_view_bitmap,
                                37673,
                                description=_("Displays the entire picture."),
                            ),
                        ]
                    ),
                ),
                MenuItem(
                    remove_hotkey(_("&Image")),
                    submenu=Menu(
                        [
                            MenuItem(
                                _("&Flip/Rotate...\tCtrl+R"),
                                paint_instance.action_flip_rotate,
                                37680,
                                description=_(
                                    "Flips or rotates the picture or a selection."
                                ),
                            ),
                            MenuItem(
                                _("&Stretch/Skew...\tCtrl+W"),
                                paint_instance.action_stretch_skew,
                                37681,
                                description=_(
                                    "Stretches or skews the picture or a selection."
                                ),
                            ),
                            MenuItem(
                                _("&Invert Colors\tCtrl+I"),
                                paint_instance.action_invert_colors,
                                37682,
                                description=_(
                                    "Inverts the colors of the picture or a selection."
                                ),
                            ),
                            MenuItem(
                                _("&Attributes...\tCtrl+E"),
                                paint_instance.action_attributes,
                                37683,
                                description=_("Changes the attributes of the picture."),
                            ),
                            MenuItem(
                                _("&Clear Image\tCtrl+Shft+N"),
                                paint_instance.action_clear_image,
                                37684,
                                description=_("Clears the picture or selection."),
                            ),
                            MenuItem(
                                _("&Draw Opaque"),
                                paint_instance.action_draw_opaque,
                                6868,
                                grayed=True,
                                description=_(
                                    "Makes the current selection either opaque or transparent."
                                ),
                            ),
                        ]
                    ),
                ),
                MenuItem(
                    remove_hotkey(_("&Colors")),
                    submenu=Menu(
                        [
                            MenuItem(
                                _("&Get Colors..."),
                                paint_instance.action_get_colors,
                                41749,
                                description=_(
                                    "Uses a previously saved palette of colors."
                                ),
                            ),
                            MenuItem(
                                _("&Save Colors..."),
                                paint_instance.action_save_colors,
                                41750,
                                description=_(
                                    "Saves the current palette of colors to a file."
                                ),
                            ),
                            MenuItem(
                                _("&Edit Colors..."),
                                paint_instance.action_edit_colors,
                                41751,
                                description=_("Creates a new color."),
                            ),
                        ]
                    ),
                ),
                MenuItem(
                    remove_hotkey(_("&Help")),
                    submenu=Menu(
                        [
                            MenuItem(
                                _("&Help Topics"),
                                paint_instance.action_help_topics,
                                57670,
                                description=_(
                                    "Displays Help for the current task or command."
                                ),
                            ),
                            Separator(),
                            MenuItem(
                                _("&About Paint"),
                                paint_instance.action_about_paint,
                                57664,
                                description=_(
                                    "Displays program information, version number, and copyright."
                                ),
                            ),
                        ]
                    ),
                ),
            ]
        )
        yield Container(
            ToolsBox(id="tools_box"),
            Container(Canvas(id="canvas"), id="editing_area"),
            LayerManagementPanel(id="layer_panel"),
            id="main_horizontal_split",
        )
        yield ColorsBox(id="colors_box")
        yield Container(
            Static(
                _("For Help, click Help Topics on the Help Menu."), id="status_text"
            ),
            Static(id="status_coords"),
            Static(id="status_dimensions"),
            id="status_bar",
        )
    if not args.inspect_layout:
        return
    from aura_cli.tui.tools.paint.inspector import Inspector

    inspector = Inspector()
    inspector.display = False
    yield paint_instance.chat_window

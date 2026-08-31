"""Enumeration of the tools available in the Paint app."""

from enum import Enum
import os

from aura_cli.application.paint.localization.i18n import get as _

from .__init__ import PYTEST
from .args import args


class Tool(Enum):
    """The tools available in the Paint app."""

    free_form_select = 1
    select = 2
    eraser = 3
    fill = 4
    pick_color = 5
    magnifier = 6
    pencil = 7
    brush = 8
    airbrush = 9
    text = 10
    line = 11
    curve = 12
    rectangle = 13
    polygon = 14
    ellipse = 15
    rounded_rectangle = 16

    def _get_terminal_icon(self) -> str:
        """Return terminal-specific icon override, or empty string if none."""
        TERM_PROGRAM = os.environ.get("TERM_PROGRAM")
        _VSCODE = {"fill": "🌊", "pencil": "🖍️"}
        _ITERM = {"fill": "🌊", "free_form_select": "⢼⠮"}
        _WT = {"pencil": "📝", "brush": "🧹", "fill": "🌊"}
        _KITTY = {"pencil": "📝", "brush": "[tan]▬[/]▤", "text": "𝐴", "curve": "〜"}
        _MAP = {
            "vscode": _VSCODE,
            "iTerm.app": _ITERM,
        }
        if TERM_PROGRAM in _MAP:
            return _MAP[TERM_PROGRAM].get(self.name, "")
        if os.environ.get("WT_SESSION"):
            return _WT.get(self.name, "")
        if os.environ.get("KITTY_WINDOW_ID"):
            return _KITTY.get(self.name, "")
        return ""

    def get_icon(self) -> str:
        """Get the icon for this tool."""
        # Alternatives collected:
        # - Free-Form Select: ✂️📐🆓🕸✨☆⚝⛤⛥⛦⛧⚛🫥🇫/🇸◌⁛⁘ ⢼⠮ 📿➰➿𓍼യ🪢𓍯 𔗫 𓍲 𓍱 ౿ Ꮼ Ꮘ
        # - Select: ✂️⬚▧🔲 ⣏⣹ ⛶
        # - Eraser/Color Eraser: 🧼🧽🧹🚫👋🗑️▰▱
        # - Fill With Color: 🌊💦💧🩸🌈🎉🎊🪣🫗🚰⛽🍯 ꗃ﹆ ⬙﹅ 🪣﹅
        # - Pick Color: 🎨🌈💉💅💧🩸🎈📌📍🪛🪠🥍🩼🌡💄🎯𖡡⤤𝀃🝯⊸⚲𓋼🗡𓍊🍶🧪🍼🌂👁️‍🗨️🧿🍷⤵❣⚗ ⤆Ϸ ⟽þ ⇐ c⟾ /̥͚̥̥͚͚̊̊
        # - Magnifier: 🔍🔎👀🔬🔭🧐🕵️‍♂️🕵️‍♀️
        # - Pencil: ✏️✎✍️🖎🖊️🖋️✒️🖆📝🖍️🪶🪈🥖🥕▪
        # - Brush: 🖌👨‍🎨🧑‍🎨💅🧹🪮🪥🪒🪠ⵄ⑃ሐ⋔⋲ ▭⋹ 𝈸⋹ ⊏⋹ ⸦⋹ ⊂⋹ ▬▤
        # - Airbrush: ⛫💨дᖜ💨╔💨🧴🥤🧃🧯🧨🍾🥫💈🫠🌬️🗯☄💭༄༺☁️🌪️🌫🌀🚿 ⪧𖤘 ᗒᗣ дᖜᗕ
        # - Text: 📝📄📃📜AＡ🅰️🆎🔤🔠𝐴
        # - Line: 📏📉📈＼⟍𝈏╲⧹\⧵∖
        # - Curve: ↪️🪝🌙〰️◡◠~∼≈∽∿〜〰﹋﹏≈≋～⁓
        # - Rectangle: ▭▬▮▯➖🟥🟧🟨🟩🟦🟪🟫⬛⬜🔲🔳⏹️◼️◻️◾◽▪️▫️
        # - Polygon: ▙𝗟𝙇﹄』𓊋⬣⬟🔶🔷🔸🔹🔺🔻△▲☖⛉♦️🛑📐🪁✴️
        # - Ellipse: ⬭⭕🔴🟠🟡🟢🔵🟣🟤⚫⚪🔘🫧🕳️🥚💫💊🛞
        # - Rounded Rectangle: ▢⬜⬛𓋰⌨️⏺️💳📺🧫

        if args.ascii_only or args.ascii_only_icons:
            enum_to_icon = {
                Tool.free_form_select: "'::.",  # "*" "<^>" "<[u]^[/]7" "'::." ".::." "<%>"
                Tool.select: "::",  # "#" "::" ":_:" ":[u]:[/]:" ":[u]'[/]:"
                Tool.eraser: "[rgb(255,0,255)][u]/[/]7[/]",  # "47" "27" "/_/" "[u]/[/]7" "<%>"
                Tool.fill: "[u i]H[/][blue][b]?[/][/]",  # "#?" "H?" "[u i]F[/]?"
                Tool.pick_color: "[u i red] P[/]",  # "[u].[/]" "[u i]\\P[/]"
                Tool.magnifier: ",[rgb(0,128,255)]O[/]",  # ",O" "o-" "O-" "o=" "O=" "Q"
                Tool.pencil: "[rgb(255,0,255)]c[/][rgb(128,128,64)]==[/]-",  # "c==>" "==-" "-=="
                Tool.brush: "E[rgb(128,128,64)])=[/]",  # "[u],h.[/u]" "[u],|.[/u]" "[u]h[/u]"
                Tool.airbrush: "[u i]H[/][rgb(0,128,255)]<)[/]",  # "H`" "H`<" "[u i]H[/]`<" "[u i]6[/]<"
                Tool.text: "A",  # "Abc"
                Tool.line: "\\",
                Tool.curve: "S",  # "~" "S" "s"
                Tool.rectangle: "[_]",  # "[]" "[_]" ("[\x1B[53m_\x1B[55m]" doesn't work right, is there no overline tag?)
                Tool.polygon: "[b]L[/b]",  # "L"
                Tool.ellipse: "O",  # "()"
                Tool.rounded_rectangle: "{_}",  # "(_)" "{_}" ("(\x1B[53m_\x1B[55m)" doesn't work right, is there no overline tag?)
            }
            return enum_to_icon[self]
        if not PYTEST:
            terminal_icon = self._get_terminal_icon()
            if terminal_icon:
                return terminal_icon
        return {
            Tool.free_form_select: "⚝",
            Tool.select: "⬚",
            Tool.eraser: "🧼",
            Tool.fill: "🪣",
            Tool.pick_color: "💉",
            Tool.magnifier: "🔍",
            Tool.pencil: "✏️",
            Tool.brush: "🖌️",
            Tool.airbrush: "💨",
            Tool.text: "Ａ",
            Tool.line: "⟍",
            Tool.curve: "～",
            Tool.rectangle: "▭",
            Tool.polygon: "𝙇",
            Tool.ellipse: "⬭",
            Tool.rounded_rectangle: "▢",
        }[self]

    def get_name(self) -> str:
        """Get the localized name for this tool.

        Not to be confused with tool.name, which is an identifier.
        """
        return {
            Tool.free_form_select: _("Free-Form Select"),
            Tool.select: _("Select"),
            Tool.eraser: _("Eraser/Color Eraser"),
            Tool.fill: _("Fill With Color"),
            Tool.pick_color: _("Pick Color"),
            Tool.magnifier: _("Magnifier"),
            Tool.pencil: _("Pencil"),
            Tool.brush: _("Brush"),
            Tool.airbrush: _("Airbrush"),
            Tool.text: _("Text"),
            Tool.line: _("Line"),
            Tool.curve: _("Curve"),
            Tool.rectangle: _("Rectangle"),
            Tool.polygon: _("Polygon"),
            Tool.ellipse: _("Ellipse"),
            Tool.rounded_rectangle: _("Rounded Rectangle"),
        }[self]

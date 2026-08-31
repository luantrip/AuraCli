import glob
import json
import os
import re
from typing import Any, Dict, Generator, List

from .parse_rc_file import parse_rc_file

base_lang: str = "en"
available_langs: List[str] = [
    lang_dir
    for lang_dir in os.listdir(os.path.dirname(__file__))
    if re.match(r"^\w+(-\w+)?$", lang_dir)
]
target_langs: List[str] = [lang for lang in available_langs if lang != base_lang]

print("Target languages:", target_langs)


# & defines accelerators (hotkeys) in menus and buttons and things, which get underlined in the UI.
# & can be escaped by doubling it, e.g. "&Taskbar && Start Menu"
def index_of_hotkey(text: str) -> int:
    # Returns the index of the ampersand that defines a hotkey, or -1 if not present.
    # The space here handles beginning-of-string matching and counteracts the offset for the [^&] so it acts like a negative lookbehind
    m = re.search(r"[^&]&[^&\s]", f" {text}")
    return m.start() if m else -1


def has_hotkey(text: str) -> bool:
    return index_of_hotkey(text) != -1


def remove_hotkey(text: str) -> str:
    text = re.sub(r"\s?\(&.\)", "", text)
    text = re.sub(r"([^&]|^)&([^&\s])", r"\1\2", text)
    return text


def remove_ellipsis(string: str) -> str:
    return string.replace("...", "")


def get_strings(lang: str) -> Generator[str, None, None]:
    rc_files: List[str] = glob.glob(
        f"{os.path.dirname(__file__)}/{lang}/**/*.rc", recursive=True
    )
    for rc_file in rc_files:
        with open(rc_file, encoding="utf16") as f:
            yield from parse_rc_file(f.read().replace("\ufeff", ""))


def add_localization_to_dict(
    localizations_dict: Dict[str, Any],
    base_string: str,
    target_string: str,
    fudgedness: int,
) -> None:
    """Add a localization entry to the dictionary."""
    localizations_dict[base_string] = localizations_dict.get(base_string, [])
    localizations_dict[base_string].append(
        {"target_string": target_string, "fudgedness": fudgedness}
    )


def add_localizations_to_dict(
    localizations_dict: Dict[str, Any],
    base_strings: List[str],
    target_strings: List[str],
) -> None:
    """Add multiple localizations to the dictionary."""
    for i, target_string in enumerate(target_strings):
        if len(base_strings) <= i:
            break
        base_string = base_strings[i]
        if base_string != target_string and base_string and target_string:
            # Split strings like "&Attributes...\tCtrl+E"
            # and "Fills an area with the current drawing color.\nFill With Color"
            splitter = re.compile(r"\t|\r?\n")
            if splitter.search(base_string):
                add_localizations_to_dict(
                    localizations_dict,
                    re.split(splitter, base_string),
                    re.split(splitter, target_string),
                )
            else:
                add_localization_to_dict(
                    localizations_dict,
                    remove_ellipsis(base_string),
                    remove_ellipsis(target_string),
                    1,
                )
                if has_hotkey(base_string):
                    add_localization_to_dict(
                        localizations_dict,
                        remove_ellipsis(remove_hotkey(base_string)),
                        remove_ellipsis(remove_hotkey(target_string)),
                        3,
                    )


base_strings: List[str] = list(get_strings(base_lang))
for target_lang in target_langs:
    target_strings: List[str] = list(get_strings(target_lang))
    localizations: Dict[str, Any] = {}

    add_localizations_to_dict(localizations, base_strings, target_strings)

    # Process each localization entry
    items_list = list(localizations.items())
    for idx in range(len(items_list)):
        base_string, options = items_list[idx]
        # Capture loop variables to avoid B023
        base_str = base_string
        opts = options
        locs = localizations

        def get_fudgedness(translation_option: Dict[str, Any]) -> int:
            return translation_option["fudgedness"]

        # options.sort(key=lambda x: x["fudgedness"])
        unique_strings = list({option["target_string"] for option in opts})
        if len(unique_strings) > 1:
            unique_strings_json = json.dumps(
                unique_strings, ensure_ascii=False, indent="\t"
            )
            print(f'Collision for "{base_str}": {unique_strings_json}')
        locs[base_str] = unique_strings[0]

    localizations_json = json.dumps(localizations, ensure_ascii=False, indent="\t")
    js = f"""
//
// NOTE: This is a generated file! Don't edit it directly.
// Eventually community translation will be set up on some translation platform.
//
// Generated with: npm run update-localization
//
loaded_localizations("{target_lang}", {localizations_json});
"""

    with open(
        f"{os.path.dirname(__file__)}/{target_lang}/localizations.js",
        "w",
        encoding="utf-8",
    ) as f:
        f.write(js)

# file_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "index.html"))
# with open(file_path, "r", encoding="utf-8") as f:
#     code = f.read()
# available_langs_json = json.dumps(available_langs, ensure_ascii=False).replace('","', '", "')
# code = re.sub(r"(available_languages\s*=\s*)\[[^\]]*\]", f"$1{available_langs_json}]", code)
# with open(file_path, "w", encoding="utf-8") as f:
#     f.write(code)

"""UI utility functions for color conversion and formatting."""


def convert_color_for_prompt_toolkit(color: str) -> str:
    """
    Convert Rich color format to prompt_toolkit hex format.

    Args:
        color: Color in Rich format (e.g., "cyan", "#00ffff")

    Returns:
        Color in hex format for prompt_toolkit
    """
    # If already hex, return as-is
    if color.startswith("#"):
        return color

    # Common color mappings
    color_map = {
        "cyan": "#00ffff",
        "blue": "#0000ff",
        "green": "#00ff00",
        "yellow": "#ffff00",
        "red": "#ff0000",
        "magenta": "#ff00ff",
        "white": "#ffffff",
        "black": "#000000",
        "bright_cyan": "#00ffff",
        "bright_blue": "#5555ff",
        "bright_green": "#55ff55",
        "bright_yellow": "#ffff55",
        "bright_red": "#ff5555",
        "bright_magenta": "#ff55ff",
    }

    return color_map.get(color.lower(), "#ffffff")  # Default to white

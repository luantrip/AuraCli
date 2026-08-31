"""Export Templates - Aura CLI Paint Tool

SVG and HTML templates for ANSI art export.

Features:
    - Custom SVG format with embedded ANSI data for lossless round-trip
    - Fira Code font with CDN fallback
    - Cropped SVG without window frame
    - HTML export with inline styles
    - Monospace rendering with proper line height

Note:
    SVG template based on rich/_export_format.py with modifications
    for ANSI art preservation and cleaner output.
"""

CUSTOM_CONSOLE_SVG_FORMAT = """\
<svg
    class="rich-terminal"
    viewBox="0 0 {terminal_width} {terminal_height}"
    xmlns="http://www.w3.org/2000/svg"
    xmlns:txtpnt="http://github.com/1j01/textual-paint"
>
    <!-- Generated with Rich https://www.textualize.io and Textual Paint https://github.com/1j01/textual-paint -->
    <style>

    @font-face {{
        font-family: "Fira Code";
        src: local("FiraCode-Regular"),
                url("https://cdnjs.cloudflare.com/ajax/libs/firacode/6.2.0/woff2/FiraCode-Regular.woff2") format("woff2"),
                url("https://cdnjs.cloudflare.com/ajax/libs/firacode/6.2.0/woff/FiraCode-Regular.woff") format("woff");
        font-style: normal;
        font-weight: 400;
    }}
    @font-face {{
        font-family: "Fira Code";
        src: local("FiraCode-Bold"),
                url("https://cdnjs.cloudflare.com/ajax/libs/firacode/6.2.0/woff2/FiraCode-Bold.woff2") format("woff2"),
                url("https://cdnjs.cloudflare.com/ajax/libs/firacode/6.2.0/woff/FiraCode-Bold.woff") format("woff");
        font-style: bold;
        font-weight: 700;
    }}

    .{unique_id}-matrix {{
        font-family: Fira Code, monospace;
        font-size: {char_height}px;
        line-height: {line_height}px;
        font-variant-east-asian: full-width;
    }}

    {styles}
    </style>

    <defs>
    <clipPath id="{unique_id}-clip-terminal">
      <rect x="0" y="0" width="{terminal_width}" height="{terminal_height}" />
    </clipPath>
    {lines}
    <txtpnt:ansi>%ANSI_GOES_HERE%</txtpnt:ansi>
    </defs>

    <g clip-path="url(#{unique_id}-clip-terminal)">
    {backgrounds}
    <g class="{unique_id}-matrix">
    {matrix}
    </g>
    </g>
</svg>
"""

CUSTOM_CONSOLE_HTML_FORMAT = """\
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<style>
{stylesheet}
body {{
    color: {foreground};
    background-color: {background};
}}
</style>
</head>
<body>
    <pre style="font-family:monospace;line-height:1"><code>{code}</code></pre>
</body>
</html>
"""

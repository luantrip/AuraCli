#!/usr/bin/env python3
"""Validate local links in the repository's Markdown documentation."""

from __future__ import annotations

from pathlib import Path
import re
import sys
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[1]
MARKDOWN_LINK = re.compile(r"(?<!!)\[[^\]]*\]\(([^)]+)\)")
EXTERNAL_SCHEMES = ("http://", "https://", "mailto:", "tel:")


def markdown_files() -> list[Path]:
    return [ROOT / "README.md", *sorted((ROOT / "docs").rglob("*.md"))]


def local_target(raw_target: str) -> str | None:
    target = raw_target.strip()
    if target.startswith("<") and target.endswith(">"):
        target = target[1:-1]
    target = target.split(maxsplit=1)[0]
    if not target or target.startswith(("#", *EXTERNAL_SCHEMES)):
        return None
    return unquote(target.split("#", 1)[0])


def validate() -> list[str]:
    errors: list[str] = []
    for document in markdown_files():
        text = document.read_text(encoding="utf-8")
        for match in MARKDOWN_LINK.finditer(text):
            target = local_target(match.group(1))
            if target is None:
                continue
            resolved = (document.parent / target).resolve()
            try:
                resolved.relative_to(ROOT)
            except ValueError:
                errors.append(
                    f"{document.relative_to(ROOT)}: target escapes repository: {target}"
                )
                continue
            if not resolved.exists():
                line = text.count("\n", 0, match.start()) + 1
                errors.append(
                    f"{document.relative_to(ROOT)}:{line}: missing target: {target}"
                )
    return errors


def main() -> int:
    errors = validate()
    if errors:
        print("Documentation validation failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1
    print(f"Documentation links are valid ({len(markdown_files())} files).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

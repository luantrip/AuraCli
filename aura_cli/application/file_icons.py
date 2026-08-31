"""
Presentation-neutral file icon mappings using Nerd Fonts.
"""

import os
import re
from typing import ClassVar, Dict, List, Tuple


class FileIcon:
    """File icon provider using Nerd Fonts."""

    FOLDER_CLOSED = ""
    FOLDER_OPEN = ""
    FOLDER_HOME = ""
    FOLDER_CONFIG = ""
    COMPUTER = ""
    FILE_DEFAULT = ""

    EXACT_MATCHES: ClassVar[Dict[str, str]] = {
        ".bashprofile": "",
        ".bashrc": "",
        ".ds_store": "",
        ".gitattributes": "",
        ".gitconfig": "",
        ".gitignore": "",
        ".gitlab-ci.yml": "",
        ".vimrc": "",
        ".zshrc": "",
        "cmakelists.txt": "",
        "docker-compose.yml": "",
        "docker-compose.yaml": "",
        "dockerfile": "",
        "gemfile": "",
        "license": "",
        "makefile": "",
        "package.json": "",
        "package-lock.json": "",
        "pyproject.toml": "",
        "readme.md": "",
        "requirements.txt": "",
        "setup.py": "",
        "tsconfig.json": "",
        "yarn.lock": "",
        ".env": "",
        ".env.local": "",
        ".env.example": "",
    }

    PATTERN_MATCHES: ClassVar[List[Tuple[str, str]]] = [
        (r".*angular.*\.js$", ""),
        (r".*react.*\.js$", ""),
        (r".*vue.*\.js$", "﵂"),
        (r".*jquery.*\.js$", ""),
        (r".*test.*\.py$", ""),
        (r".*spec.*\.js$", ""),
        (r".*config.*", ""),
        (r"vagrantfile$", ""),
    ]

    EXTENSIONS: ClassVar[Dict[str, str]] = {
        ".bz2": "",
        ".gz": "",
        ".rar": "",
        ".tar": "",
        ".zip": "",
        ".7z": "",
        ".c": "",
        ".cpp": "",
        ".cc": "",
        ".h": "",
        ".hpp": "",
        ".cs": "",
        ".css": "",
        ".dart": "",
        ".db": "",
        ".diff": "",
        ".dockerfile": "",
        ".elm": "",
        ".erl": "",
        ".ex": "",
        ".exs": "",
        ".fish": "",
        ".go": "",
        ".graphql": "",
        ".haml": "",
        ".hs": "",
        ".htm": "",
        ".html": "",
        ".ico": "",
        ".java": "",
        ".jl": "",
        ".jpeg": "",
        ".jpg": "",
        ".js": "",
        ".json": "",
        ".jsx": "",
        ".kt": "",
        ".less": "",
        ".lua": "",
        ".md": "",
        ".mdx": "",
        ".mjs": "",
        ".ml": "λ",
        ".nix": "",
        ".pdf": "",
        ".php": "",
        ".pl": "",
        ".png": "",
        ".ps1": "",
        ".psd": "",
        ".py": "",
        ".pyc": "",
        ".r": "ﳒ",
        ".rb": "",
        ".rs": "",
        ".rss": "",
        ".sass": "",
        ".scala": "",
        ".scss": "",
        ".sh": "",
        ".sql": "",
        ".svg": "ﰟ",
        ".swift": "",
        ".tex": "ﭨ",
        ".toml": "",
        ".ts": "",
        ".tsx": "",
        ".txt": "",
        ".vim": "",
        ".vue": "﵂",
        ".webp": "",
        ".xml": "",
        ".yaml": "",
        ".yml": "",
        ".zsh": "",
    }

    @classmethod
    def get_icon(cls, filename: str, is_directory: bool = False) -> str:
        """Get icon for a file or directory."""
        if is_directory:
            lower_name = filename.lower()
            if lower_name in ("home", "~"):
                return cls.FOLDER_HOME
            if lower_name in (".config", "config", ".aura"):
                return cls.FOLDER_CONFIG
            return cls.FOLDER_CLOSED

        basename = os.path.basename(filename).lower()

        if basename in cls.EXACT_MATCHES:
            return cls.EXACT_MATCHES[basename]

        for pattern, icon in cls.PATTERN_MATCHES:
            if re.match(pattern, basename):
                return icon

        _, ext = os.path.splitext(basename)
        if ext in cls.EXTENSIONS:
            return cls.EXTENSIONS[ext]

        return cls.FILE_DEFAULT

    @classmethod
    def get_folder_icon(cls, is_open: bool = False) -> str:
        """Get folder icon based on open/closed state."""
        return cls.FOLDER_OPEN if is_open else cls.FOLDER_CLOSED

    @classmethod
    def get_language_icon(cls, language: str) -> str:
        """Get icon for a programming language."""
        language_icons = {
            "python": "",
            "javascript": "",
            "typescript": "",
            "java": "",
            "go": "",
            "rust": "",
            "c": "",
            "cpp": "",
            "csharp": "",
            "ruby": "",
            "php": "",
            "swift": "",
            "kotlin": "",
            "scala": "",
            "haskell": "",
            "lua": "",
            "r": "ﳒ",
            "shell": "",
            "bash": "",
            "sql": "",
            "html": "",
            "css": "",
            "markdown": "",
        }
        return language_icons.get(language.lower(), cls.FILE_DEFAULT)

"""
Context management module for codebase analysis.

Exports:
    CodebaseContextManager — manages codebase analysis sessions
    CodeIndex, CodebaseIndexer — full semantic indexing (code_index.py)

Note: CodebaseIndex (lightweight text index) was moved to
aura_cli.core.tools.codebase_analysis, its sole consumer.
"""

from aura_cli.core.context.code_index import CodebaseIndexer, CodeIndex
from aura_cli.core.context.codebase_context_manager import CodebaseContextManager

__all__ = ["CodeIndex", "CodebaseContextManager", "CodebaseIndexer"]

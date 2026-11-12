"""Subagent tool-count docstring and panel labels stay accurate.

The docstring claimed "12 essential tools" while SUBAGENT_TOOLS held 11, and the
panel label was Portuguese. These pin both.
"""

from __future__ import annotations

import re

from aura_cli.core.agents import subagent_runner


def test_docstring_tool_count_matches_the_actual_tool_set() -> None:
    actual = len(subagent_runner.SUBAGENT_TOOLS)
    module_doc = subagent_runner.__doc__ or ""
    # The claim may live on the module docstring or the delegate docstring; check
    # both sources of truth agree with the set size.
    doc_sources = [module_doc]
    delegate = getattr(subagent_runner, "delegate_to_subagent", None)
    if delegate is not None and delegate.__doc__:
        doc_sources.append(delegate.__doc__)
    claimed = None
    for source in doc_sources:
        m = re.search(r"(\d+)\s+essential tools", source)
        if m:
            claimed = int(m.group(1))
            break
    assert claimed is not None, "no documented tool count found"
    assert claimed == actual, f"doc says {claimed}, set has {actual}"


def test_subagent_tool_set_has_eleven_tools() -> None:
    assert len(subagent_runner.SUBAGENT_TOOLS) == 11


def test_panel_label_is_english() -> None:
    import inspect

    from aura_cli.cli.ui.components import subagent_panel

    source = inspect.getsource(subagent_panel)
    assert "operações" not in source  # old Portuguese label removed
    assert "tools ·" in source

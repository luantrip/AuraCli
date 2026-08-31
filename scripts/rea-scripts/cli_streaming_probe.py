#!/usr/bin/env python3
"""Exercise CLI streaming and worker-feed rendering without network access."""

from __future__ import annotations

from io import StringIO
import json
import os
from pathlib import Path

from rich.console import Console

from aura_cli.cli.ui.components.streaming_renderer import (
    StreamingConfig,
    StreamingTextRenderer,
)
from aura_cli.cli.ui.components.worker_feed import (
    WorkerActivityFeed,
    parse_status_messages,
)


def main() -> int:
    output = StringIO()
    console = Console(file=output, width=100, force_terminal=False)
    renderer = StreamingTextRenderer(
        console=console,
        config=StreamingConfig(chunk_delay=0, max_buffer_size=8),
    )
    callbacks: list[str] = []
    result = renderer.stream_chunks(
        iter(("Hello ", "**world**")), callbacks.append
    )
    assert result == "Hello **world**"
    assert callbacks == ["Hello ", "**world**"]
    assert renderer._is_streaming is False
    assert renderer.render() is not None

    renderer.start()
    renderer.append("cancelled")
    renderer.cancel()
    assert renderer._is_streaming is False
    assert renderer._full_buffer == ""

    feed = WorkerActivityFeed("agi", mode="plan", max_visible_steps=2)
    feed.set_phase("validating")
    feed.add_step("read_file", "success", 18)
    feed.add_step("codebase_search", "error", 230)
    feed.add_step("retry", "skipped")
    feed.complete(success=False)
    wide = feed.render(console_width=120)
    narrow = feed.render(console_width=60)
    assert wide is not None and narrow is not None
    assert feed.status == "error"
    assert len(feed.steps) == 3

    feeds = parse_status_messages(
        [
            {"message": "[Aura AGI] › Planning", "data": {"mode": "plan"}},
            {"message": "[Aura AGI] ✔ read_file 18ms"},
            {"message": "[Aura Ops] › git status"},
        ]
    )
    assert {feed.agent_type for feed in feeds} == {"agi", "ops"}
    assert len(feeds[0].steps) >= 1

    state_dir = Path(os.environ.get("AURA_HOME", ".aura/rea-study-cli-streaming"))
    state_dir.mkdir(parents=True, exist_ok=True)
    report = {
        "status": "READY",
        "streamed_text": result,
        "callbacks": len(callbacks),
        "feeds": [feed.agent_type for feed in feeds],
        "rendered": len(output.getvalue()),
        "narrow_steps": min(feed.max_visible_steps, 4),
    }
    (state_dir / "cli-streaming-report.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8"
    )
    print("CLI_STREAMING_READY")
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

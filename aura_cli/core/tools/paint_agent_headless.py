"""Headless Paint Agent - PaintAgent without TUI dependency.

This module provides a headless version of PaintAgent that can be used
from the main CLI chat without requiring the Paint TUI application.

Features:
    - Generate art using LLM (ASCII, Primitives, Hybrid modes)
    - Process drawing commands programmatically
    - Save results to files in multiple formats
    - No TUI dependency - works directly with AnsiArtDocument
"""

from typing import Any, Dict, Optional

from aura_cli.application.paint import (
    GenerationMode,
    LLMPaintAgent,
    PaintDocumentService,
)
from aura_cli.application.paint.paint_agent import PaintAgent
from aura_cli.core.logger import get_logger

try:
    from aura_cli.application.paint.ansi_art_document import AnsiArtDocument

    _TUI_AVAILABLE = True
except Exception:
    AnsiArtDocument = None  # type: ignore[assignment,misc]
    _TUI_AVAILABLE = False

logger = get_logger(__name__)


class _NullCanvas:
    def refresh(self) -> None:
        """No-op refresh for headless generation."""


class _HeadlessPaintHost:
    def __init__(self, document):
        self.image = document
        self.canvas = _NullCanvas()

    async def send_message_to_chat(self, *args, **kwargs):
        """No-op chat sink for headless generation."""


class HeadlessPaintAgent:
    """PaintAgent that works without TUI dependency.

    This class provides the core PaintAgent functionality without
    requiring a Paint TUI application instance. It works directly
    with AnsiArtDocument and can be used from the main CLI.
    """

    def __init__(
        self,
        llm_client=None,
        width: int = 80,
        height: int = 24,
        default_bg: str = "#000000",
        default_fg: str = "#ffffff",
    ):
        """Initialize headless paint agent.

        Args:
            llm_client: Optional LLM client for art generation
            width: Canvas width (default: 80)
            height: Canvas height (default: 24)
            default_bg: Default background color (default: black)
            default_fg: Default foreground color (default: white)
        """
        self.llm_client = llm_client
        self.width = width
        self.height = height
        if not _TUI_AVAILABLE:
            document = None
            logger.debug("TUI unavailable — HeadlessPaintAgent operating in stub mode")
        else:
            document = AnsiArtDocument(width, height, default_bg, default_fg)
        self._documents = PaintDocumentService(document)
        self._agent = None

    @property
    def document(self):
        return self._documents.document

    @document.setter
    def document(self, value) -> None:
        self._documents.replace(value)

    def _get_agent(self):
        """Get or create PaintAgent instance (lazy initialization)."""
        if self._agent is None:
            mock_app = _HeadlessPaintHost(self.document)
            self._agent = PaintAgent(mock_app, self.llm_client)
            self._agent.document = self.document
        return self._agent

    async def generate_art(
        self, prompt: str, mode: Optional[str] = None
    ) -> Dict[str, Any]:
        """Generate art from a text prompt.

        Args:
            prompt: Description of art to generate
            mode: Generation mode (auto/ascii/primitives/hybrid) or None for auto

        Returns:
            Dict with success status, file_path (if saved), and metadata
        """
        try:
            agent = self._get_agent()

            if mode == "ascii" or (mode is None and self.llm_client):
                if self.llm_client:
                    host = _HeadlessPaintHost(self.document)
                    llm_agent = LLMPaintAgent(host, self.llm_client)
                    selected_mode = GenerationMode.AUTO
                    if mode == "ascii":
                        selected_mode = GenerationMode.ASCII_DIRECT
                    elif mode == "primitives":
                        selected_mode = GenerationMode.PRIMITIVES
                    elif mode == "hybrid":
                        selected_mode = GenerationMode.HYBRID

                    result = await llm_agent.generate_art(prompt, selected_mode)
                    art_content = (
                        result.get("content", "") if result.get("success") else ""
                    )
                    if art_content:
                        new_doc = AnsiArtDocument.from_plain(art_content)
                        self.document = new_doc
                        if self._agent and self._agent.paint_app:
                            self._agent.paint_app.image = new_doc
                        return {
                            "success": True,
                            "message": "Art generated successfully using LLM",
                            "width": self.document.width,
                            "height": self.document.height,
                        }
                    return {
                        "success": False,
                        "error": result.get(
                            "error", "Paint generation returned no content"
                        ),
                    }
                else:
                    agent = self._get_agent() if not self._agent else self._agent
                    await agent.process_message(f"generate using ascii {prompt}")
                    return {
                        "success": True,
                        "message": "Art generated successfully",
                        "width": self.document.width,
                        "height": self.document.height,
                    }
            else:
                agent = self._get_agent() if not self._agent else self._agent
                await agent.process_message(prompt)
                return {
                    "success": True,
                    "message": "Art generated successfully",
                    "width": self.document.width,
                    "height": self.document.height,
                }
        except Exception as e:
            logger.error(f"Error generating art: {e}", exc_info=True)
            return {"success": False, "error": str(e)}

    def save(self, file_path: str, output_format: str = "ans") -> Dict[str, Any]:
        """Save the current document to a file.

        Args:
            file_path: Path where to save the file
            output_format: Output format (ans, png, svg, html)

        Returns:
            Dict with success status and file path
        """
        result = self._documents.save(file_path, output_format)
        if not result.get("success"):
            logger.error("Error saving Paint file: %s", result.get("error"))
        return result

    def get_document(self) -> AnsiArtDocument:
        """Get the current document.

        Returns:
            Current AnsiArtDocument instance
        """
        return self.document

    def set_document(self, document: AnsiArtDocument) -> None:
        """Set a new document.

        Args:
            document: AnsiArtDocument to use
        """
        self.document = document
        self.width = document.width
        self.height = document.height
        if self._agent:
            self._agent.paint_app.image = document

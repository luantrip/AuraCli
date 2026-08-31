"""Isolated tests for LLM Paint Agent (no full imports)."""


def test_generation_mode_enum():
    """Test GenerationMode enum values."""
    # Import only the enum, not the full agent
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "llm_paint_agent", "aura_cli/application/paint/generator.py"
    )
    module = importlib.util.module_from_spec(spec)

    spec.loader.exec_module(module)

    GenerationMode = module.GenerationMode

    assert GenerationMode.ASCII_DIRECT.value == "ascii"
    assert GenerationMode.PRIMITIVES.value == "primitives"
    assert GenerationMode.HYBRID.value == "hybrid"
    assert GenerationMode.AUTO.value == "auto"


def test_llm_agent_class_exists():
    """Test that LLMPaintAgent class is defined."""
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "llm_paint_agent", "aura_cli/application/paint/generator.py"
    )
    module = importlib.util.module_from_spec(spec)

    spec.loader.exec_module(module)

    assert hasattr(module, "LLMPaintAgent")
    assert hasattr(module.LLMPaintAgent, "generate_art")
    assert hasattr(module.LLMPaintAgent, "refine_last")


def test_primitive_drawing_methods():
    """Test that primitive drawing methods exist."""
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "llm_paint_agent", "aura_cli/application/paint/generator.py"
    )
    module = importlib.util.module_from_spec(spec)

    spec.loader.exec_module(module)

    LLMPaintAgent = module.LLMPaintAgent

    assert hasattr(LLMPaintAgent, "_draw_circle_primitive")
    assert hasattr(LLMPaintAgent, "_draw_rectangle_primitive")
    assert hasattr(LLMPaintAgent, "_draw_line_primitive")
    assert hasattr(LLMPaintAgent, "_draw_text_primitive")
    assert hasattr(LLMPaintAgent, "_draw_polygon_primitive")

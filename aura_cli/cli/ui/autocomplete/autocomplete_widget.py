"""Autocomplete widget dashboard for Aura CLI.

AutocompleteWidget provides score-ranked suggestions (function/class/module/
variable/keyword/snippet types) with full keyboard navigation. SnippetBrowser
and TemplateEditor are auxiliary panels. Entry point: show_autocomplete_dashboard().
"""

from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional

from rich.console import Console, Group, RenderableType
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table
from rich.text import Text
from rich.tree import Tree

from aura_cli.cli.ui.constants import UIIcons, UIStyles
from aura_cli.cli.ui.display_facade import get_console
from aura_cli.core.logger import get_logger

logger = get_logger(__name__)


class SuggestionType(Enum):
    """
    Autocomplete suggestion type.

    Attributes:
        FUNCTION: Function suggestion
        CLASS: Class suggestion
        MODULE: Module suggestion
        VARIABLE: Variable suggestion
        KEYWORD: Keyword suggestion
        SNIPPET: Code snippet suggestion
    """

    FUNCTION = "function"
    CLASS = "class"
    MODULE = "module"
    VARIABLE = "variable"
    KEYWORD = "keyword"
    SNIPPET = "snippet"


@dataclass
class Suggestion:
    """
    Autocomplete suggestion with score and documentation.

    Attributes:
        text: Suggestion text
        type: Suggestion type (SuggestionType)
        description: Short description
        score: Relevance score (0.0-1.0)
        documentation: Full documentation (optional)
    """

    text: str
    type: SuggestionType
    description: str
    score: float
    documentation: Optional[str] = None


@dataclass
class Snippet:
    """
    Reusable code snippet.

    Attributes:
        id: Unique identifier
        name: Snippet name
        language: Programming language
        description: Snippet description
        code: Snippet code
        usage_count: Usage counter
        tags: Tags for categorization
    """

    id: str
    name: str
    language: str
    description: str
    code: str
    usage_count: int
    tags: List[str]


@dataclass
class Template:
    """
    Customizable code template.

    Attributes:
        id: Unique identifier
    """

    id: str
    name: str
    category: str
    description: str
    variables: List[str]
    content: str


class AutocompleteWidget:
    """Interactive autocomplete widget with real-time suggestions."""

    def get_bundled_suggestions(self) -> List[Suggestion]:
        """Return the built-in suggestions used when no context is available."""
        return [
            Suggestion(
                text="authenticate_user",
                type=SuggestionType.FUNCTION,
                description="Authenticate user with credentials",
                score=0.95,
                documentation="def authenticate_user(username: str, password: str) -> User",
            ),
            Suggestion(
                text="UserModel",
                type=SuggestionType.CLASS,
                description="User database model",
                score=0.90,
                documentation="class UserModel(Base):\n    id: int\n    username: str",
            ),
            Suggestion(
                text="auth",
                type=SuggestionType.MODULE,
                description="Authentication module",
                score=0.85,
                documentation="import auth",
            ),
            Suggestion(
                text="async",
                type=SuggestionType.KEYWORD,
                description="Async function keyword",
                score=0.80,
                documentation="async def function_name():",
            ),
            Suggestion(
                text="try_except",
                type=SuggestionType.SNIPPET,
                description="Try-except block",
                score=0.75,
                documentation="try:\n    ...\nexcept Exception as e:\n    ...",
            ),
        ]

    def render(
        self, console: Console, selected_index: int = 0, query: str = ""
    ) -> RenderableType:
        """Renderiza widget de autocomplete interativo."""
        suggestions = []
        try:
            from aura_cli.core.autocomplete.classification import ContextClassifier
            from aura_cli.core.autocomplete.generation import AutocompleteGenerator

            ctx = query or "def "
            clf = ContextClassifier().classify(ctx)
            raw = AutocompleteGenerator().generate(
                ctx, clf, prefix=query, max_suggestions=10
            )
            for s in raw:
                suggestions.append(
                    Suggestion(
                        text=s.text,
                        description=getattr(s, "description", ""),
                        type=SuggestionType.FUNCTION,
                        score=s.score,
                    )
                )
        except Exception as exc:
            logger.warning("Unable to generate autocomplete suggestions: %s", exc)
        if not suggestions:
            suggestions = self.get_bundled_suggestions()

        # Filtrar por query se fornecida
        if query:
            query_lower = query.lower()
            suggestions = [
                s
                for s in suggestions
                if query_lower in s.text.lower() or query_lower in s.description.lower()
            ]

        table = Table(
            title=f"▪ Sugestões de autocomplete{' - ' + query if query else ''}",
            title_style=UIStyles.TITLE,
            show_header=True,
            header_style=UIStyles.SUBTITLE,
            border_style=UIStyles.BORDER_PRIMARY,
            expand=False,
        )

        table.add_column("", width=3)  # Selection marker
        table.add_column("", width=3)  # Icon
        table.add_column("Sugestão", width=25)
        table.add_column("Tipo", width=12)
        table.add_column("Descrição", width=35)
        table.add_column("Pontuação", justify="right", width=10)

        type_icons = {
            SuggestionType.FUNCTION: "ƒ",
            SuggestionType.CLASS: "C",
            SuggestionType.MODULE: "M",
            SuggestionType.VARIABLE: "v",
            SuggestionType.KEYWORD: "K",
            SuggestionType.SNIPPET: "S",
        }

        type_colors = {
            SuggestionType.FUNCTION: UIStyles.PRIMARY,
            SuggestionType.CLASS: UIStyles.ACCENT,
            SuggestionType.MODULE: UIStyles.INFO,
            SuggestionType.VARIABLE: UIStyles.SUCCESS,
            SuggestionType.KEYWORD: UIStyles.WARNING,
            SuggestionType.SNIPPET: UIStyles.ERROR,
        }

        for i, suggestion in enumerate(suggestions):
            icon = type_icons.get(suggestion.type, "•")
            color = type_colors.get(suggestion.type, UIStyles.BODY)

            # Score visualisation with sparkline
            score_pct = int(suggestion.score * 10)
            score_bar = "█" * score_pct + "░" * (10 - score_pct)

            # Selection marker
            is_selected = i == selected_index
            marker = "►" if is_selected else " "
            marker_style = UIStyles.ACCENT if is_selected else UIStyles.MUTED

            table.add_row(
                f"[{marker_style}]{marker}[/]",
                f"[{color}]{icon}[/]",
                f"[{UIStyles.PRIMARY}]{suggestion.text}[/]",
                f"[{color}]{suggestion.type.value}[/]",
                (
                    f"[{UIStyles.BODY}]{suggestion.description[:33]}...[/]"
                    if len(suggestion.description) > 35
                    else f"[{UIStyles.BODY}]{suggestion.description}[/]"
                ),
                f"[{UIStyles.SUCCESS}]{score_bar}[/]",
            )

        selected = suggestions[0]
        preview_text = Text()
        preview_text.append("Prévia: ", style=UIStyles.LABEL)
        preview_text.append(f"{selected.text}", style=UIStyles.PRIMARY)
        preview_text.append("\n\n", style=UIStyles.MUTED)
        preview_text.append(
            selected.documentation or "Nenhuma documentação disponível",
            style=UIStyles.BODY,
        )

        preview = Panel(
            preview_text,
            title="Documentação",
            title_align="left",
            border_style=UIStyles.BORDER_PRIMARY,
        )

        stats_text = Text()
        stats_text.append(f"\n{UIIcons.INFO} ", style=UIStyles.INFO)
        stats_text.append("Total de sugestões: ", style=UIStyles.LABEL)
        stats_text.append(f"{len(suggestions)} ", style=UIStyles.PRIMARY)
        stats_text.append("| Exibindo: ", style=UIStyles.LABEL)
        stats_text.append("Top 5 ", style=UIStyles.SUCCESS)
        stats_text.append("| Pontuação média: ", style=UIStyles.LABEL)
        avg_score = sum(s.score for s in suggestions) / len(suggestions)
        stats_text.append(f"{avg_score:.0%}", style=UIStyles.INFO)

        return Group(table, preview, stats_text)


class SnippetBrowser:
    """Code snippet browser with reusable snippet library."""

    def get_bundled_snippets(self) -> List[Snippet]:
        """Return the built-in snippet library."""
        return [
            Snippet(
                id="snip_001",
                name="FastAPI Endpoint",
                language="python",
                description="Basic FastAPI endpoint template",
                code='@app.get("/endpoint")\nasync def endpoint():\n    return {"status": "ok"}',
                usage_count=0,
                tags=["fastapi", "api", "async"],
            ),
            Snippet(
                id="snip_002",
                name="Try-Except-Finally",
                language="python",
                description="Complete error handling block",
                code="try:\n    # code\nexcept Exception as e:\n    # handle\nfinally:\n    # cleanup",
                usage_count=0,
                tags=["error", "exception", "handling"],
            ),
            Snippet(
                id="snip_003",
                name="SQLAlchemy Model",
                language="python",
                description="Database model template",
                code="class Model(Base):\n    __tablename__ = 'table'\n    id = Column(Integer, primary_key=True)",
                usage_count=0,
                tags=["sqlalchemy", "database", "model"],
            ),
            Snippet(
                id="snip_004",
                name="Async Context Manager",
                language="python",
                description="Async context manager pattern",
                code="async with resource:\n    # use resource\n    pass",
                usage_count=0,
                tags=["async", "context", "manager"],
            ),
        ]

    def render(self, console: Console) -> RenderableType:
        """Renderiza browser de snippets."""
        snippets: List[Snippet] = []
        try:
            from aura_cli.core.autocomplete.generation import AutocompleteGenerator

            gen = AutocompleteGenerator()
            for ctx_type, tmpl_list in gen.templates.items():
                for tmpl in tmpl_list:
                    snippets.append(
                        Snippet(
                            id=f"gen_{ctx_type.value}_{len(snippets)}",
                            name=tmpl.split("(")[0]
                            .strip()
                            .replace("def ", "")
                            .replace("class ", ""),
                            language="python",
                            description=f"{ctx_type.value} template",
                            code=tmpl,
                            tags=[ctx_type.value],
                            usage_count=0,
                        )
                    )
        except Exception as exc:
            logger.warning("Unable to load generated snippets: %s", exc)
        if not snippets:
            snippets = self.get_bundled_snippets()

        table = Table(
            title="📚 Biblioteca de snippets",
            title_style=UIStyles.TITLE,
            show_header=True,
            header_style=UIStyles.SUBTITLE,
            border_style=UIStyles.BORDER_ACCENT,
            expand=False,
        )

        table.add_column("Nome", width=22)
        table.add_column("Linguagem", width=10)
        table.add_column("Descrição", width=30)
        table.add_column("Uso", justify="right", width=8)
        table.add_column("Tags", width=25)

        for snippet in snippets:
            tags_str = ", ".join(snippet.tags[:3])
            if len(snippet.tags) > 3:
                tags_str += "..."

            table.add_row(
                f"[{UIStyles.PRIMARY}]{snippet.name}[/]",
                f"[{UIStyles.INFO}]{snippet.language}[/]",
                (
                    f"[{UIStyles.BODY}]{snippet.description[:28]}...[/]"
                    if len(snippet.description) > 30
                    else f"[{UIStyles.BODY}]{snippet.description}[/]"
                ),
                f"[{UIStyles.SUCCESS}]{snippet.usage_count}[/]",
                f"[{UIStyles.MUTED}]{tags_str}[/]",
            )

        selected = snippets[0]
        syntax = Syntax(
            selected.code,
            selected.language,
            theme="monokai",
            line_numbers=False,
            word_wrap=True,
        )

        preview = Panel(
            syntax,
            title=f"Prévia: {selected.name}",
            title_align="left",
            border_style=UIStyles.BORDER_PRIMARY,
        )

        total_snippets = len(snippets)
        total_usage = sum(s.usage_count for s in snippets)
        all_tags = set()
        for s in snippets:
            all_tags.update(s.tags)

        stats_text = Text()
        stats_text.append(f"\n{UIIcons.INFO} ", style=UIStyles.INFO)
        stats_text.append("Total de snippets: ", style=UIStyles.LABEL)
        stats_text.append(f"{total_snippets} ", style=UIStyles.PRIMARY)
        stats_text.append("| Uso total: ", style=UIStyles.LABEL)
        stats_text.append(f"{total_usage} ", style=UIStyles.SUCCESS)
        stats_text.append("| Tags únicas: ", style=UIStyles.LABEL)
        stats_text.append(f"{len(all_tags)}", style=UIStyles.INFO)

        return Group(table, preview, stats_text)


class TemplateEditor:
    """Parametrisable code template editor."""

    def get_bundled_templates(self) -> List[Template]:
        """Return the built-in template library."""
        return [
            Template(
                id="tmpl_001",
                name="REST API Endpoint",
                category="API",
                description="Complete REST endpoint with validation",
                variables=["resource", "method", "auth_required"],
                content="@app.{method}('/{resource}')\n@require_auth({auth_required})\nasync def {method}_{resource}():\n    pass",
            ),
            Template(
                id="tmpl_002",
                name="Database Model",
                category="Database",
                description="SQLAlchemy model with relationships",
                variables=["model_name", "table_name", "fields"],
                content="class {model_name}(Base):\n    __tablename__ = '{table_name}'\n    {fields}",
            ),
            Template(
                id="tmpl_003",
                name="Test Function",
                category="Testing",
                description="Pytest test function template",
                variables=["test_name", "fixture", "assertion"],
                content="def test_{test_name}({fixture}):\n    result = function_under_test()\n    assert {assertion}",
            ),
        ]

    def render(self, console: Console) -> RenderableType:
        """Renderiza editor de templates."""
        loaded_templates: List[Template] = []
        try:
            from aura_cli.core.autocomplete.generation import AutocompleteGenerator

            gen = AutocompleteGenerator()
            for ctx_type, tmpl_list in gen.templates.items():
                for tmpl in tmpl_list:
                    loaded_templates.append(
                        Template(
                            id=f"gen_{ctx_type.value}_{len(loaded_templates)}",
                            name=tmpl.split("\n")[0][:30],
                            description=f"{ctx_type.value}",
                            content=tmpl,
                            category=ctx_type.value,
                            variables=[],
                        )
                    )
        except Exception as exc:
            logger.warning("Unable to load generated templates: %s", exc)
        if not loaded_templates:
            loaded_templates = self.get_bundled_templates()

        tree = Tree(
            "📝 Template Library",
            style=UIStyles.TITLE,
            guide_style=UIStyles.BORDER_PRIMARY,
        )

        categories: Dict[str, List[Template]] = {}
        for template in loaded_templates:
            if template.category not in categories:
                categories[template.category] = []
            categories[template.category].append(template)

        for category, category_templates in categories.items():
            cat_node = tree.add(
                f"[{UIStyles.ACCENT}]{category}[/] ({len(category_templates)})"
            )

            for template_entry in category_templates:
                tmpl_text = Text()
                tmpl_text.append(f"{template_entry.name}", style=UIStyles.PRIMARY)
                tmpl_text.append(
                    f"\n  {template_entry.description}", style=UIStyles.MUTED
                )
                tmpl_text.append("\n  Variables: ", style=UIStyles.LABEL)
                tmpl_text.append(
                    f"{', '.join(template_entry.variables[:3])}",
                    style=UIStyles.INFO,
                )
                if len(template_entry.variables) > 3:
                    tmpl_text.append("...", style=UIStyles.MUTED)

                cat_node.add(tmpl_text)

        selected = loaded_templates[0]

        preview_content = f"""# Modelo: {selected.name}
# Variables: {", ".join(selected.variables)}

{selected.content}
"""

        syntax = Syntax(
            preview_content,
            "python",
            theme="monokai",
            line_numbers=True,
            word_wrap=True,
        )

        preview = Panel(
            syntax,
            title=f"Modelo: {selected.name}",
            title_align="left",
            border_style=UIStyles.BORDER_SUCCESS,
        )

        return Group(tree, preview)


def create_autocomplete_dashboard() -> Layout:
    """
    Cria dashboard completo de Autocomplete.

    Returns:
        Layout Rich com dashboard completo
    """
    console = get_console()

    layout = Layout()

    layout.split_column(
        Layout(name="header", size=3),
        Layout(name="main"),
        Layout(name="footer", size=15),
    )

    header_text = Text()
    header_text.append("▪ ", style=UIStyles.TITLE)
    header_text.append("AURA CLI - Autocomplete Widget Dashboard", style=UIStyles.TITLE)
    layout["header"].update(Panel(header_text, border_style=UIStyles.BORDER_PRIMARY))

    layout["main"].split_row(Layout(name="left"), Layout(name="right"))

    layout["left"].split_column(Layout(name="widget"))

    layout["right"].split_column(Layout(name="snippets"), Layout(name="templates"))

    widget = AutocompleteWidget()
    snippets = SnippetBrowser()
    templates = TemplateEditor()

    layout["widget"].update(
        Panel(widget.render(console), border_style=UIStyles.BORDER_PRIMARY)
    )
    layout["snippets"].update(
        Panel(snippets.render(console), border_style=UIStyles.BORDER_ACCENT)
    )
    layout["templates"].update(
        Panel(templates.render(console), border_style=UIStyles.BORDER_SUCCESS)
    )

    return layout


def show_autocomplete_dashboard(
    console: Console, live: bool = False, refresh_rate: float = 2.0
) -> None:
    """Display the Autocomplete dashboard."""
    if not live:
        dashboard = create_autocomplete_dashboard()
        console.print(dashboard)
        console.print()
    else:
        with Live(
            create_autocomplete_dashboard(),
            console=console,
            refresh_per_second=1 / refresh_rate,
            screen=False,
        ) as live_display:
            import time

            try:
                while True:
                    time.sleep(refresh_rate)
                    live_display.update(create_autocomplete_dashboard())
            except KeyboardInterrupt as _e:
                logger.debug(f"Ignorado: {_e}")

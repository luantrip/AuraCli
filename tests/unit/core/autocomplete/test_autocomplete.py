"""
Testes Unitários para Sistema de Autocomplete do Aura CLI.

Este módulo contém testes unitários que verificam o funcionamento individual
de componentes do sistema de autocomplete inteligente, incluindo pré-processamento
de contexto, classificação, geração de sugestões e filtragem.

Componentes Testados:
    - ContextPreprocessor: Pré-processamento e limpeza de contexto
    - ContextClassifier: Classificação de tipo de contexto
    - AutocompleteGenerator: Geração de sugestões de autocomplete
    - SuggestionFilter: Filtragem e ranking de sugestões

Cenários de Teste:
    - Pré-processamento: Remoção de comentários, extração de keywords, redução de poluição
    - Classificação: Definições de função, definições de classe, extração de keywords
    - Geração: Geração baseada em contexto, uso de templates
    - Filtragem: Filtragem estrita, remoção de duplicatas, ranking por score

Validações:
    - Pré-processamento limpa contexto corretamente
    - Classificação identifica tipos de contexto
    - Geração produz sugestões relevantes
    - Filtragem remove sugestões de baixa qualidade
    - Duplicatas são removidas

Estrutura de Testes:
    - TestContextPreprocessor: Testes de pré-processamento
    - TestContextClassifier: Testes de classificação
    - TestAutocompleteGenerator: Testes de geração
    - TestSuggestionFilter: Testes de filtragem

Tipos de Contexto:
    - FUNCTION_DEFINITION: Definição de função
    - CLASS_DEFINITION: Definição de classe
    - VARIABLE_ASSIGNMENT: Atribuição de variável
    - IMPORT_STATEMENT: Declaração de import
    - (Outros tipos conforme necessário)

Estratégias de Geração:
    - CONTEXT_BASED: Baseada apenas em contexto
    - TEMPLATE_BASED: Baseada em templates
    - HYBRID: Combinação de ambas

Estratégias de Filtragem:
    - STRICT: Filtragem rigorosa (score >= 0.7)
    - MODERATE: Filtragem moderada (score >= 0.5)
    - LENIENT: Filtragem permissiva (score >= 0.3)

Pipeline de Autocomplete:
    1. Pré-processamento: Limpeza e normalização
    2. Classificação: Identificação do tipo de contexto
    3. Geração: Criação de sugestões
    4. Filtragem: Remoção de sugestões ruins

Exemplo de Uso:
    ```python
    def test_autocomplete():
        preprocessor = ContextPreprocessor()
        context = preprocessor.preprocess(code, rules=[PreprocessingRule.REMOVE_COMMENTS])

        classifier = ContextClassifier()
        classification = classifier.classify(context)

        generator = AutocompleteGenerator()
        suggestions = generator.generate(context, classification, prefix="my")
    ```

Dependências:
    - pytest: Framework de testes
    - autocomplete: Módulo de autocomplete (preprocessing, classification, generation, filtering)
"""

from aura_cli.core.autocomplete.classification import ContextClassifier, ContextType
from aura_cli.core.autocomplete.filtering import FilterStrategy, SuggestionFilter
from aura_cli.core.autocomplete.generation import (
    AutocompleteGenerator,
    GenerationStrategy,
)
from aura_cli.core.autocomplete.preprocessing import (
    ContextPreprocessor,
    PreprocessingRule,
)


class TestContextPreprocessor:
    """Testes para ContextPreprocessor."""

    def test_preprocessor_initialization(self):
        """Testa inicialização do pré-processador."""
        preprocessor = ContextPreprocessor()

        assert preprocessor is not None

    def test_preprocess_remove_comments(self):
        """Testa remoção de comentários."""
        preprocessor = ContextPreprocessor()

        context = """
def function():
    # This is a comment
    return value
"""

        processed = preprocessor.preprocess(
            context, rules=[PreprocessingRule.REMOVE_COMMENTS]
        )

        assert "#" not in processed

    def test_preprocess_extract_keywords(self):
        """Testa extração de palavras-chave."""
        preprocessor = ContextPreprocessor()

        context = """
def my_function():
    my_variable = 10
    return my_variable
"""

        processed = preprocessor.preprocess(
            context, rules=[PreprocessingRule.EXTRACT_KEYWORDS]
        )

        assert "def" in processed or "my_function" in processed

    def test_reduce_context_pollution(self):
        """Testa redução de poluição."""
        preprocessor = ContextPreprocessor()

        context = "x" * 10000  # Contexto grande

        reduced = preprocessor.reduce_context_pollution(context, max_tokens=100)

        assert len(reduced) < len(context)


class TestContextClassifier:
    """Testes para ContextClassifier."""

    def test_classifier_initialization(self):
        """Testa inicialização do classificador."""
        classifier = ContextClassifier()

        assert classifier is not None
        assert len(classifier.patterns) > 0

    def test_classify_function_definition(self):
        """Testa classificação de definição de função."""
        classifier = ContextClassifier()

        context = "def my_function(param):"

        result = classifier.classify(context)

        assert result.context_type == ContextType.FUNCTION_DEFINITION
        assert result.confidence > 0.8

    def test_classify_class_definition(self):
        """Testa classificação de definição de classe."""
        classifier = ContextClassifier()

        context = "class MyClass:"

        result = classifier.classify(context)

        assert result.context_type == ContextType.CLASS_DEFINITION
        assert result.confidence > 0.8

    def test_extract_keywords(self):
        """Testa extração de palavras-chave."""
        classifier = ContextClassifier()

        context = """
def my_function():
    my_variable = 10
"""

        keywords = classifier._extract_keywords(context)

        assert len(keywords) > 0


class TestAutocompleteGenerator:
    """Testes para AutocompleteGenerator."""

    def test_generator_initialization(self):
        """Testa inicialização do gerador."""
        generator = AutocompleteGenerator()

        assert generator.strategy == GenerationStrategy.HYBRID
        assert len(generator.templates) > 0

    def test_generate_context_based(self):
        """Testa geração baseada em contexto."""
        from aura_cli.core.autocomplete.classification import ClassificationResult

        generator = AutocompleteGenerator(strategy=GenerationStrategy.CONTEXT_BASED)

        context = """
def my_function():
    my_variable = 10
    return my_variable
"""

        classification = ClassificationResult(
            context_type=ContextType.FUNCTION_DEFINITION, confidence=0.9
        )

        suggestions = generator.generate(context, classification, prefix="my")

        assert len(suggestions) > 0
        assert any("my" in s.completion.lower() for s in suggestions)

    def test_generate_snippet_based_returns_bundled_snippets(self):
        """The selectable snippet strategy must produce real catalog entries."""
        from aura_cli.core.autocomplete.classification import ClassificationResult

        generator = AutocompleteGenerator(
            strategy=GenerationStrategy.SNIPPET_BASED,
            use_ml_models=False,
        )
        classification = ClassificationResult(
            context_type=ContextType.FUNCTION_DEFINITION,
            confidence=0.9,
        )

        suggestions = generator.generate("def ", classification, prefix="def")

        assert suggestions
        assert all(s.description.startswith("Snippet for ") for s in suggestions)


class TestSuggestionFilter:
    """Testes para SuggestionFilter."""

    def test_filter_initialization(self):
        """Testa inicialização do filtro."""
        filter_obj = SuggestionFilter()

        assert filter_obj.strategy == FilterStrategy.MODERATE
        assert len(filter_obj.rules) > 0

    def test_filter_strict(self):
        """Testa filtragem estrita."""
        from aura_cli.core.autocomplete.generation import Suggestion

        filter_obj = SuggestionFilter(strategy=FilterStrategy.STRICT)

        suggestions = [
            Suggestion("test1", "test1", score=0.9),
            Suggestion("test2", "test2", score=0.5),  # Score baixo
            Suggestion("test3", "test3", score=0.8),
        ]

        filtered = filter_obj.filter(suggestions)

        # Deve remover sugestão com score baixo
        assert len(filtered) <= 2
        assert all(s.score >= 0.7 for s in filtered)

    def test_filter_removes_duplicates(self):
        """Testa remoção de duplicatas."""
        from aura_cli.core.autocomplete.generation import Suggestion

        filter_obj = SuggestionFilter()

        suggestions = [
            Suggestion("test1", "duplicate", score=0.9),
            Suggestion("test2", "duplicate", score=0.8),  # Duplicata
            Suggestion("test3", "unique", score=0.7),
        ]

        filtered = filter_obj.filter(suggestions)

        # Deve remover duplicatas
        completions = [s.completion for s in filtered]
        assert len(completions) == len(set(completions))

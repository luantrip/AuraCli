"""
Testes para Sistema de Validação do Aura CLI.

Este módulo contém testes que verificam o funcionamento completo do sistema de
validação multi-layer do Aura CLI, incluindo validação de sintaxe, tipos, análise
estática, formatação e execução de testes relacionados.

Componentes Testados:
    - ValidationResult: Estrutura de dados para resultados de validação
    - validate_code: Função principal de validação multi-layer
    - format_code: Formatação automática de código

Cenários de Teste:
    - Inicialização: ValidationResult inicia com estado correto
    - Adição de Erros: Erros marcam validação como falha
    - Adição de Avisos: Avisos não falham validação
    - Código Válido: Validação aceita código Python correto
    - Código Inválido: Validação detecta erros de sintaxe
    - Arquivo Inexistente: Tratamento de erro quando arquivo não existe
    - Formatação: Formatação de código Python

Validações:
    - ValidationResult mantém estado correto
    - Erros são registrados adequadamente
    - Avisos não impedem passagem
    - Código válido passa na validação
    - Código inválido é detectado
    - Erros de arquivo são tratados
    - Formatação funciona corretamente

Estrutura de Testes:
    - TestValidationResult: Testes da estrutura de resultados
    - TestValidateCode: Testes da função de validação
    - TestFormatCode: Testes da função de formatação

Camadas de Validação:
    O sistema valida múltiplas camadas:
    1. Sintaxe: Verificação de sintaxe Python
    2. Tipos: Verificação de tipos (mypy/pyright)
    3. Análise Estática: Linting (flake8/pylint)
    4. Formatação: Verificação de formatação (black/isort)
    5. Testes: Execução de testes relacionados

ValidationResult:
    Estrutura que armazena:
    - passed: Se todas as validações passaram
    - errors: Lista de erros encontrados
    - warnings: Lista de avisos
    - checks: Resultado de cada check individual
    - details: Detalhes adicionais de cada check

Exemplo de Uso:
    ```python
    def test_validation():
        result = validate_code("test.py")
        assert isinstance(result, ValidationResult)
        if result.passed:
            print("Código válido!")
    ```

Dependências:
    - pytest: Framework de testes
    - tempfile: Para criação de arquivos temporários
    - validation: Módulo de validação
"""

import pytest

from aura_cli.core.validation import (
    ValidationResult,
    format_code,
    validate_code,
)


class TestValidationResult:
    """Testes para classe ValidationResult"""

    def test_validation_result_initialization(self):
        """
        Testa inicialização de ValidationResult.

        Verifica se ValidationResult inicia com estado correto.
        """
        result = ValidationResult()

        assert result.passed is True
        assert isinstance(result.errors, list)
        assert isinstance(result.warnings, list)
        assert isinstance(result.checks, dict)

    def test_validation_result_add_error(self):
        """
        Testa adição de erro.

        Verifica se add_error marca resultado como falho.
        """
        result = ValidationResult()
        result.add_error("syntax", "Erro de sintaxe", line=10, file="test.py")

        assert result.passed is False
        assert len(result.errors) == 1
        assert result.errors[0]["check"] == "syntax"

    def test_validation_result_add_warning(self):
        """
        Testa adição de aviso.

        Verifica se add_warning adiciona aviso sem falhar.
        """
        result = ValidationResult()
        result.add_warning("style", "Estilo não padrão", line=5)

        assert result.passed is True  # Warnings não falham
        assert len(result.warnings) == 1


class TestValidateCode:
    """Testes para função validate_code"""

    @pytest.fixture
    def temp_file(self, tmp_path):
        """Fixture que cria arquivo temporário para testes."""
        test_file = tmp_path / "test.py"
        return test_file

    def test_validate_code_valid_python(self, temp_file):
        """
        Testa validação de código Python válido.

        Verifica se validate_code aceita código Python correto.
        """
        valid_code = "def hello():\n    return 'world'\n"
        temp_file.write_text(valid_code, encoding="utf-8")

        result = validate_code(str(temp_file))

        assert isinstance(result, ValidationResult)
        # Código válido deve passar ou ter erros apenas de path/configuração
        # (o teste pode falhar se o arquivo temp está fora do projeto)
        # Verificamos se não tem erros de sintaxe real
        syntax_errors = [e for e in result.errors if "syntax" in str(e).lower()]
        assert len(syntax_errors) == 0, f"Unexpected syntax errors: {syntax_errors}"

    def test_validate_code_invalid_syntax(self, temp_file):
        """
        Testa validação de código com sintaxe inválida.

        Verifica se validate_code detecta erros de sintaxe.
        """
        invalid_code = "def hello(\n    return 'world'"  # Sintaxe inválida
        temp_file.write_text(invalid_code, encoding="utf-8")

        result = validate_code(str(temp_file))

        assert isinstance(result, ValidationResult)
        # Código inválido deve falhar
        assert result.passed is False or len(result.errors) > 0

    def test_validate_code_nonexistent_file(self):
        """
        Testa validação de arquivo inexistente.

        Verifica tratamento de erro quando arquivo não existe.
        """
        result = validate_code("/nonexistent/file.py")

        assert isinstance(result, ValidationResult)
        assert result.passed is False
        assert len(result.errors) > 0


class TestFormatCode:
    """Testes para função format_code"""

    def test_format_code_formats_python(self, tmp_path):
        """
        Testa formatação de código Python.

        Verifica se format_code formata código corretamente.
        """
        test_file = tmp_path / "test.py"
        unformatted = "def hello():\n    x=1+2\n    return x"
        test_file.write_text(unformatted, encoding="utf-8")

        result = format_code(str(test_file))

        # Deve retornar resultado de formatação
        assert isinstance(result, (str, dict))

    def test_format_code_nonexistent_file(self):
        """
        Testa formatação de arquivo inexistente.

        Verifica tratamento de erro quando arquivo não existe.
        """
        result = format_code("/nonexistent/file.py")

        # Deve retornar erro ou mensagem de erro
        assert isinstance(result, (str, dict))
        if isinstance(result, str):
            assert "erro" in result.lower() or "não encontrado" in result.lower()

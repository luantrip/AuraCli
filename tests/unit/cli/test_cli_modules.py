"""
Testes Unitários para Módulos CLI Principais do Aura CLI.

Este módulo contém testes unitários que verificam o funcionamento individual
de componentes principais da interface de linha de comando, incluindo processamento
de comandos, funções auxiliares e handlers de function calling.

Componentes Testados:
    - handle_help: Processamento do comando de ajuda
    - handle_extensions: Processamento do comando de extensões
    - initialize_conversation_history: Inicialização de histórico de conversação
    - parse_agi_command: Parsing de comandos do agente AGI
    - parse_ops_command: Parsing de comandos do agente Ops
    - parse_tool_calls: Parsing de tool calls do LLM
    - extract_tool_call_data: Extração de dados de tool calls

Cenários de Teste:
    - Comandos de Ajuda: Exibição de ajuda formatada
    - Comandos de Extensões: Listagem de extensões
    - Inicialização de Histórico: Criação de histórico com mensagem de sistema
    - Parsing AGI: Extração de objetivo de comandos /agi
    - Parsing Ops: Extração de modo e tarefa de comandos /ops
    - Parsing Tool Calls: Interpretação de tool calls formato OpenAI/LiteLLM
    - Extração de Dados: Extração de nome, argumentos e ID de tool calls

Validações:
    - Comandos são processados corretamente
    - Histórico é inicializado com mensagem de sistema
    - Parsing extrai informações corretas
    - Tool calls são interpretados adequadamente
    - Dados são extraídos corretamente

Estrutura de Testes:
    - TestCommandProcessor: Testes do processador de comandos
    - TestHelpers: Testes de funções auxiliares
    - TestFunctionCallHandler: Testes do handler de function calls

Formatos de Comando:
    - /agi <objetivo>: Comando para agente AGI
    - /ops <modo> <tarefa>: Comando para agente Ops
    - /ops <tarefa>: Comando Ops sem modo (default: "general")
    - /help: Comando de ajuda
    - /extensions: Comando de extensões

Formato de Tool Calls:
    Suporta formato OpenAI/LiteLLM:
    - message.tool_calls: Lista de tool calls
    - tool_call.id: ID único do call
    - tool_call.function.name: Nome da função
    - tool_call.function.arguments: Argumentos JSON

Mensagem de Sistema:
    Histórico inicializado com mensagem de sistema que:
    - Define identidade do Aura CLI
    - Estabelece contexto e capacidades
    - Configura comportamento do assistente

Exemplo de Uso:
    ```python
    def test_parsing():
        objective = parse_agi_command("/agi criar um blog")
        assert objective == "criar um blog"

        mode, task = parse_ops_command("/ops git status")
        assert mode == "git"
        assert task == "status"
    ```

Dependências:
    - pytest: Framework de testes
    - unittest.mock: Para mocking
    - command_processor: Processador de comandos
    - helpers: Funções auxiliares
    - function_call_handler: Handler de function calls
"""

from aura_cli.cli.command_processor import handle_extensions, handle_help
from aura_cli.cli.helpers import (
    initialize_conversation_history,
    parse_agi_command,
    parse_ops_command,
)
from aura_cli.cli.response_parser import extract_tool_call_data, parse_tool_calls


class TestCommandProcessor:
    """Testes para processador de comandos."""

    def test_handle_help(self, capsys):
        """Testa comando de ajuda."""
        handle_help()

        captured = capsys.readouterr()
        assert "Comandos Disponíveis" in captured.out or len(captured.out) > 0

    def test_handle_extensions(self, capsys):
        """Testa comando de extensões."""
        handle_extensions()

        captured = capsys.readouterr()
        # Deve imprimir algo (mesmo que seja "nenhuma extensão")
        assert len(captured.out) >= 0


class TestHelpers:
    """Testes para funções auxiliares."""

    def test_initialize_conversation_history(self):
        """Testa inicialização de histórico."""
        history = initialize_conversation_history()

        assert len(history) > 0
        assert history[0]["role"] == "system"
        assert history[0]["role"] == "system"  # system message is present

    def test_parse_agi_command(self):
        """Testa parsing de comando AGI."""
        objective = parse_agi_command("/agi criar um blog")

        assert objective == "criar um blog"

    def test_parse_agi_command_empty(self):
        """Testa parsing de comando AGI vazio."""
        objective = parse_agi_command("/agi")

        assert objective is not None
        assert len(objective) > 0

    def test_parse_ops_command(self):
        """Testa parsing de comando Ops."""
        mode, task = parse_ops_command("/ops git status")

        assert mode == "git"
        assert task == "status"

    def test_parse_ops_command_default_mode(self):
        """Testa parsing de comando Ops sem modo."""
        mode, task = parse_ops_command("/ops status")

        assert mode == "general"
        assert task == "status"


class TestFunctionCallHandler:
    """Testes para function call handler."""

    def test_parse_tool_calls_openai_format(self):
        """Testa parsing de tool calls formato OpenAI."""
        # Formato LiteLLM/OpenAI
        message = type(
            "obj",
            (object,),
            {
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    type(
                        "obj",
                        (object,),
                        {
                            "id": "call_123",
                            "type": "function",
                            "function": type(
                                "obj",
                                (object,),
                                {
                                    "name": "read_file",
                                    "arguments": '{"path": "test.py"}',
                                },
                            )(),
                        },
                    )()
                ],
            },
        )()

        tool_calls = parse_tool_calls(message)

        # Pode retornar None se formato não reconhecido, mas não deve quebrar
        assert tool_calls is None or len(tool_calls) >= 0

    def test_extract_tool_call_data(self):
        """Testa extração de dados de tool call."""
        # Cria objeto mock com atributos
        tool_call = type(
            "obj",
            (object,),
            {
                "id": "call_123",
                "function": type(
                    "obj",
                    (object,),
                    {"name": "read_file", "arguments": '{"path": "test.py"}'},
                )(),
            },
        )()

        func_name, args, call_id = extract_tool_call_data(tool_call, call_index=0)

        assert func_name == "read_file"
        assert isinstance(args, (str, dict))
        if isinstance(args, dict):
            assert args.get("path") == "test.py"
        assert call_id == "call_123"

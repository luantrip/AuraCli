"""
Configuração Compartilhada para Testes Pytest do Aura CLI.

Este módulo fornece fixtures e configurações compartilhadas para todos os testes
do projeto. Define utilitários comuns, configurações de ambiente e fixtures reutilizáveis
que são automaticamente disponibilizadas para todos os módulos de teste.

Fixtures Principais:
    - temp_dir: Diretório temporário para testes (usando tmp_path do pytest)
    - sample_file: Arquivo de texto de exemplo para testes
    - sample_code_file: Arquivo Python de exemplo com código estruturado

Configuração de Path:
    Adiciona automaticamente a raiz do projeto ao sys.path, permitindo imports
    diretos dos módulos do Aura CLI sem necessidade de instalação do pacote.

Estrutura de Fixtures:
    - temp_dir: Retorna Path temporário criado pelo pytest (limpo automaticamente)
    - sample_file: Cria arquivo test_file.txt com conteúdo de exemplo
    - sample_code_file: Cria arquivo test_code.py com função e classe de exemplo

Uso:
    As fixtures são automaticamente injetadas nos testes quando solicitadas:

    ```python
    def test_example(temp_dir, sample_file):
        # temp_dir e sample_file estão disponíveis
        assert sample_file.exists()
    ```

Dependências:
    - pytest: Framework de testes
    - pathlib: Para manipulação de caminhos
"""

import os
from pathlib import Path
import sys
import tempfile
from unittest.mock import MagicMock, Mock

import pytest

# Force Null Keyring backend for tests to avoid OS prompts/locks
os.environ["PYTHON_KEYRING_BACKEND"] = "keyring.backends.null.Keyring"

# Keep every Aura-owned artifact outside the repository and user profile.
_artifact_sandbox = tempfile.TemporaryDirectory(prefix="aura-pytest-artifacts-")
os.environ.setdefault("AURA_HOME", str(Path(_artifact_sandbox.name) / "user"))
os.environ.setdefault(
    "AURA_PROJECT_ROOT", str(Path(_artifact_sandbox.name) / "project")
)

# Adiciona raiz do projeto ao path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


# Mock tiktoken ANTES de qualquer import
def mock_tiktoken():
    """
    Mock tiktoken para evitar timeout de download.

    Este mock simula o comportamento do tiktoken sem fazer downloads de rede.
    A estimativa de tokens é baseada em ~4 caracteres por token (aproximação).

    Note:
        Este mock é suficiente para a maioria dos testes, mas testes que
        dependem de contagem precisa de tokens devem usar
        @pytest.mark.skip_tiktoken_mock ou fixtures específicas.
    """

    class MockEncoding:
        """Mock encoding que simula comportamento real."""

        def __init__(self, name: str = "cl100k_base"):
            self.name = name
            self._special_tokens = {"<|endoftext|>": 100257}

        def encode(
            self,
            text: str,
            allowed_special: set | None = None,
            disallowed_special: set | None = None,
        ) -> list:
            """Encode text to tokens (approximation: ~4 chars per token)."""
            if not isinstance(text, str):
                text = str(text)
            # Aproximação: 4 caracteres por token
            num_tokens = max(1, len(text) // 4)
            return list(range(num_tokens))

        def decode(self, tokens: list) -> str:
            """Decode tokens to text."""
            # Retorna texto placeholder proporcional ao número de tokens
            return "mock" * len(tokens)

        def encode_ordinary(self, text: str) -> list:
            """Encode without special tokens."""
            return self.encode(text)

        @property
        def special_tokens_set(self) -> set:
            return set(self._special_tokens.keys())

    mock_encoding = MockEncoding()

    mock_tiktoken_module = MagicMock()
    mock_tiktoken_module.get_encoding = Mock(return_value=mock_encoding)
    mock_tiktoken_module.encoding_for_model = Mock(return_value=mock_encoding)
    mock_tiktoken_module.Encoding = MockEncoding

    sys.modules["tiktoken"] = mock_tiktoken_module
    sys.modules["tiktoken.core"] = MagicMock()
    sys.modules["tiktoken.registry"] = MagicMock()

    return mock_tiktoken_module


# Mock pathlib operations pesadas
# def mock_pathlib_heavy_ops():
#     """Mock operações pesadas de pathlib para evitar timeout."""
#     from pathlib import Path
#     from unittest.mock import patch

#     # Não mockar tudo, apenas limitar rglob para não varrer todo o sistema
#     original_rglob = Path.rglob

#     def limited_rglob(self, pattern):
#         """rglob limitado que não varre diretórios grandes."""
#         # Se o path é muito grande ou é raiz do sistema, retorna vazio
#             path_str = str(self)
#             if len(path_str) < 10 or path_str in ['/', '/Users', '/System', '/Library']:
#             # Limita a 100 resultados
#             results = []
#             for i, item in enumerate(original_rglob(self, pattern)):
#                     break
#                 results.append(item)
#             return iter(results)

#     Path.rglob = limited_rglob

# Aplica mocks antes de qualquer import
mock_tiktoken()
# mock_pathlib_heavy_ops()


def mock_litellm():
    """Mock litellm para evitar erros de importação sem dependências."""
    mock_litellm_module = MagicMock()
    mock_litellm_module.api_version = "v1"
    mock_litellm_module.vertex_ai_api_version = "v1"
    mock_litellm_module.set_verbose = False
    mock_litellm_module.suppress_debug_info = True
    mock_litellm_module.drop_params = True

    # Mock completion function
    def mock_completion(*args, **kwargs):
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message = MagicMock()
        mock_response.choices[0].message.content = "Mocked LLM response"
        mock_response.choices[0].message.tool_calls = None
        return mock_response

    mock_litellm_module.completion = mock_completion

    sys.modules["litellm"] = mock_litellm_module
    return mock_litellm_module


mock_litellm()


# Configuração de timeout global usando pytest-timeout
def pytest_configure(config):
    """Configura timeout padrão para todos os testes.

    Note:
        - 30 segundos para testes unitários
        - Testes de integração podem usar @pytest.mark.timeout(60)
        - Testes e2e podem usar @pytest.mark.timeout(120)
    """
    # Timeout de 30 segundos para cada teste (padrão)
    # Testes específicos podem sobrescrever com @pytest.mark.timeout(N)
    config.option.timeout = 30
    config.option.timeout_method = "thread"


# Bootstrap DI container for all tests (ensures singleton semantics)
from aura_cli.core.di_bootstrap import bootstrap_services

bootstrap_services()


@pytest.fixture(autouse=True)
def isolate_aura_artifacts(monkeypatch, tmp_path):
    """Give each test an independent project-local Aura root."""
    monkeypatch.setenv("AURA_PROJECT_ROOT", str(tmp_path))


@pytest.fixture(autouse=True)
def disable_path_validation():
    """Disable path validation for tests to allow temp directories."""
    from aura_cli.core.tools.file_system import enable_path_validation

    enable_path_validation(False)
    yield
    enable_path_validation(True)


@pytest.fixture(autouse=True)
def reset_allowed_workspace():
    """Prevent workspace-boundary globals from leaking between tests."""
    from aura_cli.core.tools.file_system import set_allowed_base_dir

    set_allowed_base_dir(None)
    yield
    set_allowed_base_dir(None)


@pytest.fixture
def temp_dir(tmp_path):
    """Diretório temporário para testes."""
    return tmp_path


@pytest.fixture
def sample_file(temp_dir):
    """Arquivo de exemplo para testes."""
    file_path = temp_dir / "test_file.txt"
    file_path.write_text("Test content\nLine 2\nLine 3")
    return file_path


@pytest.fixture
def sample_code_file(temp_dir):
    """Arquivo Python de exemplo."""
    file_path = temp_dir / "test_code.py"
    file_path.write_text("""
def hello():
    return "world"

class TestClass:
    def method(self):
        pass
""")
    return file_path


# =============================================================================
# Fase 3.1 — Centralized LLM and EventBus mock fixtures
# =============================================================================


@pytest.fixture
def mock_llm_completion():
    """
    Global fixture: patches litellm.completion with a deterministic mock.

    Returns the MagicMock so tests can configure side_effect / return_value.

    Usage:
        def test_something(mock_llm_completion):
            mock_llm_completion.return_value = make_llm_response("custom text")
    """
    from unittest.mock import MagicMock, patch

    def _make_response(content: str = "Mocked LLM response", tool_calls=None):
        resp = MagicMock()
        resp.choices = [MagicMock()]
        resp.choices[0].message.content = content
        resp.choices[0].message.tool_calls = tool_calls
        resp.usage = MagicMock(prompt_tokens=10, completion_tokens=20, total_tokens=30)
        return resp

    mock = MagicMock(side_effect=lambda *a, **kw: _make_response())
    mock.make_response = _make_response  # helper for tests

    with patch("litellm.completion", mock):
        yield mock


@pytest.fixture
def mock_event_bus():
    """
    Global fixture: provides a fresh, isolated CoreEventBus for each test.

    Resets the singleton before and after the test so events don't leak
    between tests.

    Usage:
        def test_something(mock_event_bus):
            from aura_cli.core.events import publish_event
            publish_event(some_event)
            assert mock_event_bus.qsize() == 1
    """
    from aura_cli.core.events.event_bus import CoreEventBus

    CoreEventBus.reset_instance()
    bus = CoreEventBus.get_instance()
    yield bus
    CoreEventBus.reset_instance()


@pytest.fixture
def mock_llm_async():
    """
    Global fixture: patches aura_cli.core.llm.base.query_with_fallback
    for async LLM calls used by ADK agents.

    Usage:
        async def test_agent(mock_llm_async):
            mock_llm_async.return_value = "Agent response"
    """
    from unittest.mock import AsyncMock, patch

    mock = AsyncMock(return_value="Mocked async LLM response")
    with patch("aura_cli.core.llm.base.query_with_fallback", mock):
        yield mock

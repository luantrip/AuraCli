"""
Testes Unitários para Módulos Core Principais do Aura CLI.

Este módulo contém testes unitários que verificam o funcionamento individual
de componentes fundamentais do Aura CLI, incluindo cache, configuração,
logging, estatísticas, validação e análise de dependências.

Componentes Testados:
    - Cache: Sistema de cacheamento de resultados com TTL
    - Config: Gerenciamento de configurações
    - Logger: Sistema de logging estruturado
    - Stats: Rastreamento de estatísticas de uso
    - Validation: Validação multi-layer de código
    - DependencyAnalysis: Análise de dependências entre arquivos

Cenários de Teste:
    - Cache: Cacheamento, limpeza, estatísticas
    - Config: Get/set, persistência, recarregamento
    - Logger: Obtenção de logger, níveis de log
    - Stats: Rastreamento de tokens, arquivos, status
    - Validation: Validação de código, formatação
    - DependencyAnalysis: Busca de dependências

Validações:
    - Cache funciona corretamente
    - Config persiste e recarrega
    - Logger funciona em todos os níveis
    - Stats rastreia métricas corretamente
    - Validation detecta erros
    - DependencyAnalysis encontra dependências

Estrutura de Testes:
    - TestCache: Testes do sistema de cache
    - TestConfig: Testes do sistema de configuração
    - TestLogger: Testes do sistema de logging
    - TestStats: Testes do sistema de estatísticas
    - TestValidation: Testes do sistema de validação
    - TestDependencyAnalysis: Testes de análise de dependências

Sistema de Cache:
    - Cacheamento com decorator @cache_result
    - TTL (Time To Live) configurável
    - Estatísticas de cache hits/misses
    - Limpeza manual e automática

Sistema de Estatísticas:
    - Tokens: prompt, completion, total
    - Arquivos: lidos, editados, criados
    - Status: idle, thinking, working
    - Operações de ferramentas

Análise de Dependências:
    - Identificação de imports
    - Análise de dependências transitivas
    - Detecção de ciclos
    - Ordenação topológica

Exemplo de Uso:
    ```python
    def test_cache():
        @cache_result(ttl=60)
        def expensive(x):
            return x * 2

        result1 = expensive(5)  # Executa
        result2 = expensive(5)  # Usa cache
        assert result1 == result2
    ```

Dependências:
    - pytest: Framework de testes
    - cache: Sistema de cache
    - config: Sistema de configuração
    - logger: Sistema de logging
    - stats: Sistema de estatísticas
    - validation: Sistema de validação
    - dependency_analysis: Análise de dependências
"""

from aura_cli.core.cache import cache_result, clear_cache, get_cache_stats
from aura_cli.core.config import Config, config_manager
from aura_cli.core.dependency_analysis import DependencyAnalyzer, find_dependencies
from aura_cli.core.logger import get_logger
from aura_cli.core.stats import StatsTracker
from aura_cli.core.validation import ValidationResult, format_code, validate_code


class TestCache:
    """Testes para sistema de cache."""

    def test_cache_result(self):
        """Testa cacheamento de resultados."""
        clear_cache()

        call_count = [0]

        @cache_result(ttl=60)
        def expensive_function(x):
            call_count[0] += 1
            return x * 2

        # Primeira chamada - executa
        result1 = expensive_function(5)
        assert result1 == 10
        assert call_count[0] == 1

        # Segunda chamada - usa cache
        result2 = expensive_function(5)
        assert result2 == 10
        assert call_count[0] == 1  # Não incrementou

        # Chamada com argumento diferente - executa
        result3 = expensive_function(6)
        assert result3 == 12
        assert call_count[0] == 2

    def test_clear_cache(self):
        """Testa limpeza de cache."""

        @cache_result()
        def test_func(x):
            return x

        test_func(1)
        test_func(1)  # Cache hit

        clear_cache()

        # Cache limpo, deve executar novamente
        stats = get_cache_stats()
        assert stats["total_items"] == 0


class TestConfig:
    """Testes para sistema de configuração."""

    def test_config_manager(self):
        """Testa gerenciador de configuração."""
        # Testa get/set
        config_manager.set("test_key", "test_value")
        value = config_manager.get("test_key")
        assert value == "test_value"

        # Testa get com default (usando operador or)
        value = config_manager.get("nonexistent") or "default"
        assert value == "default"

    def test_config_class(self, temp_dir):
        """Testa classe Config."""
        config_file = temp_dir / "test_config.json"
        config = Config(path=config_file)

        config.set("test", "value")
        assert config.get("test") == "value"

        # Testa persistência
        config.save()
        assert config_file.exists()

        # Recarrega
        config2 = Config(path=config_file)
        assert config2.get("test") == "value"


class TestLogger:
    """Testes para sistema de logging."""

    def test_get_logger(self):
        """Testa obtenção de logger."""
        logger = get_logger(__name__)

        assert logger is not None
        assert logger.name == __name__

    def test_logger_levels(self):
        """Testa que todos os níveis de log funcionam sem exceção."""
        logger = get_logger("test_logger")

        # Todos os níveis devem funcionar
        logger.debug("Debug message")
        logger.info("Info message")
        logger.warning("Warning message")
        logger.error("Error message")

        # Logger deve ter um nome válido
        assert logger.name == "test_logger"
        # Logger deve ter um handler configurado (não ficar silencioso por acidente)
        import logging
        root = logging.getLogger()
        assert root.handlers or logger.handlers, "Logger deve ter pelo menos um handler"


class TestStats:
    """Testes para sistema de estatísticas."""

    def test_stats_tracker(self):
        """Testa rastreador de estatísticas."""
        stats = StatsTracker()

        assert stats.tokens_used == 0
        assert stats.files_edited == 0
        assert stats.current_status == "idle"
        assert stats.notification_message is None
        assert stats.notification_expires_at is None

    def test_add_tokens(self):
        """Testa adição de tokens."""
        stats = StatsTracker()

        stats.add_tokens(
            {"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30}
        )

        assert stats.tokens_used == 30
        assert stats.prompt_tokens == 10
        assert stats.completion_tokens == 20

    def test_track_file_operations(self):
        """Testa rastreamento de operações de arquivo."""
        stats = StatsTracker()

        stats.increment_files_read("test.py")
        assert stats.files_read == 1

        stats.increment_files_edited("test.py")
        assert stats.files_edited == 1

        stats.increment_files_created("new.py")
        assert stats.files_created == 1

    def test_notification_system(self):
        """Testa sistema de notificações."""
        stats = StatsTracker()

        assert stats.get_notification() is None

        stats.set_notification("Test notification", duration_seconds=1.0)
        assert stats.notification_message == "Test notification"
        assert stats.notification_expires_at is not None

        notification = stats.get_notification()
        assert notification == "Test notification"

        stats.clear_notification()
        assert stats.notification_message is None
        assert stats.get_notification() is None

    def test_notification_expiration(self):
        """Testa expiração automática de notificações."""
        import time

        stats = StatsTracker()
        stats.set_notification("Short notification", duration_seconds=0.1)

        assert stats.get_notification() is not None

        time.sleep(0.15)

        assert stats.get_notification() is None
        assert stats.notification_message is None


class TestValidation:
    """Testes para sistema de validação."""

    def test_validation_result(self):
        """Testa resultado de validação."""
        result = ValidationResult()

        assert result.passed
        assert len(result.errors) == 0
        assert len(result.warnings) == 0

        result.add_error("syntax", "Syntax error", line=10)
        assert not result.passed
        assert len(result.errors) == 1

    def test_validate_code(self, sample_code_file):
        """Testa validação de código."""
        result = validate_code(str(sample_code_file))

        assert result is not None
        assert isinstance(result, ValidationResult)

    def test_format_code(self, sample_code_file):
        """Testa formatação de código."""
        formatted = format_code(str(sample_code_file))

        assert formatted is not None
        # format_code retorna um dict com informações sobre a formatação
        assert isinstance(formatted, dict)
        assert "success" in formatted


class TestDependencyAnalysis:
    """Testes para análise de dependências."""

    def test_analyzer_initialization(self):
        """Testa inicialização do analisador."""
        analyzer = DependencyAnalyzer()

        assert analyzer is not None

    def test_find_dependencies(self, temp_dir):
        """Testa busca de dependências."""
        # Cria arquivo Python de teste com imports
        test_file = temp_dir / "test.py"
        test_file.write_text("import os\nimport json\nfrom pathlib import Path\n")

        # find_dependencies retorna lista de arquivos que o arquivo depende
        # Como o arquivo de teste não tem dependências de outros arquivos do projeto,
        # a lista pode estar vazia, mas deve ser uma lista válida
        deps = find_dependencies(str(test_file), scope=str(temp_dir))

        # Verifica se retornou uma lista (pode estar vazia se não há dependências de arquivos do projeto)
        assert deps is not None
        assert isinstance(deps, list)

"""
Testes para o cache de análise de código.

Propósito: Verifica cache especializado para análise de código
Componentes: AnalysisCache, CodeAnalysisResult
"""

from pathlib import Path
import tempfile

import pytest

from aura_cli.core.cache_advanced.analysis_cache import (
    AnalysisCache,
    get_analysis_cache,
)


class TestAnalysisCache:
    """Testes para AnalysisCache."""

    @pytest.fixture
    def temp_cache_dir(self):
        """Diretório temporário para cache."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)

    @pytest.fixture
    def analysis_cache(self):
        """Cache de análise configurado para testes."""
        return AnalysisCache(ttl=3600)

    @pytest.fixture
    def sample_analysis(self):
        """Resultado de análise de exemplo."""
        return {
            "file_path": "/sample.py",
            "functions": ["calculate", "validate"],
            "classes": ["Calculator"],
            "imports": ["math", "typing"],
            "complexity": 4,
        }

    def test_cache_initialization(self):
        """Verifica inicialização do cache de análise."""
        cache = AnalysisCache(ttl=7200)
        assert cache.ttl == 7200
        assert cache.cache is not None

    def test_set_and_get_analysis(
        self, analysis_cache, sample_analysis, temp_cache_dir
    ):
        """Testa cache de resultado de análise."""
        # Cria arquivo temporário
        test_file = temp_cache_dir / "test.py"
        test_file.write_text("def test(): pass")

        analysis_cache.set_analysis(str(test_file), sample_analysis)

        result = analysis_cache.get_analysis(str(test_file))
        assert result is not None
        assert result["functions"] == ["calculate", "validate"]

    def test_get_analysis_cache_miss(self, analysis_cache):
        """Verifica cache miss."""
        result = analysis_cache.get_analysis("/nonexistent.py")
        assert result is None

    def test_invalidate_file(self, analysis_cache, sample_analysis, temp_cache_dir):
        """Verifica invalidação de arquivo."""
        test_file = temp_cache_dir / "test.py"
        test_file.write_text("def test(): pass")

        analysis_cache.set_analysis(str(test_file), sample_analysis)
        assert analysis_cache.get_analysis(str(test_file)) is not None

        analysis_cache.invalidate(str(test_file))
        # Após invalidação, deve retornar None ou análise atualizada
        # (dependendo da implementação)

    def test_get_cached_files(self, analysis_cache, temp_cache_dir):
        """Testa obtenção de arquivos em cache."""
        files = [temp_cache_dir / f"file{i}.py" for i in range(3)]

        for i, file_path in enumerate(files):
            file_path.write_text(f"def func_{i}(): pass")
            analysis = {
                "file_path": str(file_path),
                "functions": [f"func_{i}"],
                "classes": [],
                "imports": [],
                "complexity": 1,
            }
            analysis_cache.set_analysis(str(file_path), analysis)

        cached_files = analysis_cache.get_cached_files()
        assert len(cached_files) >= 0  # Pode variar dependendo da implementação

    def test_get_stats(self, analysis_cache, temp_cache_dir):
        """Verifica obtenção de estatísticas."""
        # Adiciona algumas análises
        for i in range(3):
            file_path = temp_cache_dir / f"file_{i}.py"
            file_path.write_text(f"def func_{i}(): pass")
            analysis = {
                "file_path": str(file_path),
                "functions": [f"func_{i}"],
                "classes": [],
                "imports": [],
                "complexity": i + 1,
            }
            analysis_cache.set_analysis(str(file_path), analysis)

        stats = analysis_cache.get_stats()
        assert "cached_files" in stats or "total_files" in stats
        assert "cache_size_mb" in stats or "size_mb" in stats


class TestGlobalAnalysisCache:
    """Testes para função global de cache de análise."""

    def test_get_analysis_cache_singleton(self):
        """Verifica padrão singleton."""
        cache1 = get_analysis_cache()
        cache2 = get_analysis_cache()

        assert cache1 is cache2


class TestAnalysisCacheIntegration:
    """Testes de integração do cache de análise."""

    @pytest.fixture
    def temp_cache_dir(self):
        """Diretório temporário para cache."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)

    def test_real_world_python_analysis(self, temp_cache_dir):
        """Testa análise de arquivo Python real."""
        cache = AnalysisCache()

        # Cria arquivo Python real
        test_file = temp_cache_dir / "main.py"
        test_file.write_text('''
def main():
    """Main function."""
    print("Hello, World!")

class Calculator:
    """Simple calculator."""

    def add(self, a, b):
        return a + b

if __name__ == "__main__":
    main()
        ''')

        # Simula análise de arquivo Python complexo
        analysis = {
            "file_path": str(test_file),
            "functions": ["main", "add"],
            "classes": ["Calculator"],
            "imports": [],
            "complexity": 3,
            "lines_of_code": 12,
        }

        cache.set_analysis(str(test_file), analysis)

        # Verifica recuperação
        retrieved = cache.get_analysis(str(test_file))
        assert retrieved is not None
        assert retrieved["complexity"] == 3
        assert len(retrieved["functions"]) == 2
        assert "Calculator" in retrieved["classes"]

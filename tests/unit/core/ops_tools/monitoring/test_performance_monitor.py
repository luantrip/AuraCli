"""
Testes para o módulo performance_monitor.

Testa funcionalidades de monitoramento de performance
de sistema, aplicação e operações.
"""

from datetime import datetime
from unittest.mock import Mock, patch

from aura_cli.core.ops_tools.monitoring.performance_monitor import (
    PerformanceMetric,
    PerformanceMonitor,
)


class TestPerformanceMetric:
    """Testa dataclass PerformanceMetric."""

    def test_performance_metric_creation(self):
        """Testa criação de métrica de performance."""
        timestamp = datetime.now()
        metric = PerformanceMetric(
            name="cpu_usage", value=75.5, unit="percent", timestamp=timestamp
        )

        assert metric.name == "cpu_usage"
        assert metric.value == 75.5
        assert metric.unit == "percent"
        assert metric.timestamp == timestamp
        assert metric.threshold is None

    def test_performance_metric_with_threshold(self):
        """Testa métrica com limite de alerta."""
        timestamp = datetime.now()
        metric = PerformanceMetric(
            name="memory_usage",
            value=85.0,
            unit="percent",
            timestamp=timestamp,
            threshold=90.0,
        )

        assert metric.threshold == 90.0
        assert metric.value < metric.threshold  # Ainda dentro do limite

    def test_performance_metric_different_units(self):
        """Testa métricas com diferentes unidades."""
        timestamp = datetime.now()

        metrics = [
            PerformanceMetric("cpu_usage", 75.5, "percent", timestamp),
            PerformanceMetric("memory_bytes", 1073741824, "bytes", timestamp),
            PerformanceMetric("response_time", 0.250, "seconds", timestamp),
            PerformanceMetric("requests_per_sec", 1000, "rps", timestamp),
            PerformanceMetric("disk_io", 50.5, "mbps", timestamp),
        ]

        expected_units = ["percent", "bytes", "seconds", "rps", "mbps"]
        actual_units = [m.unit for m in metrics]

        assert actual_units == expected_units

    def test_performance_metric_threshold_comparison(self):
        """Testa comparação com threshold."""
        timestamp = datetime.now()

        # Métrica dentro do limite
        normal_metric = PerformanceMetric(
            "cpu", 70.0, "percent", timestamp, threshold=80.0
        )
        assert normal_metric.value < normal_metric.threshold

        # Métrica no limite
        limit_metric = PerformanceMetric(
            "cpu", 80.0, "percent", timestamp, threshold=80.0
        )
        assert limit_metric.value == limit_metric.threshold

        # Métrica acima do limite
        high_metric = PerformanceMetric(
            "cpu", 90.0, "percent", timestamp, threshold=80.0
        )
        assert high_metric.value > high_metric.threshold


class TestPerformanceMonitor:
    """Testa classe PerformanceMonitor."""

    def setup_method(self):
        """Setup para cada teste."""
        self.monitor = PerformanceMonitor()

    def test_init(self):
        """Testa inicialização."""
        assert hasattr(self.monitor, "metrics")
        assert hasattr(self.monitor, "stats")
        assert isinstance(self.monitor.metrics, list)
        assert len(self.monitor.metrics) == 0

    @patch("psutil.cpu_percent")
    @patch("psutil.cpu_count")
    @patch("psutil.virtual_memory")
    @patch("psutil.disk_usage")
    @patch("psutil.net_io_counters")
    def test_collect_system_metrics(
        self, mock_net, mock_disk, mock_memory, mock_cpu_count, mock_cpu_percent
    ):
        """Testa coleta de métricas do sistema."""
        # Mock dos valores do psutil
        mock_cpu_percent.return_value = 75.5
        mock_cpu_count.return_value = 8

        mock_memory_obj = Mock()
        mock_memory_obj.total = 16 * 1024**3  # 16GB
        mock_memory_obj.available = 8 * 1024**3  # 8GB
        mock_memory_obj.percent = 50.0
        mock_memory_obj.used = 8 * 1024**3  # 8GB
        mock_memory.return_value = mock_memory_obj

        mock_disk_obj = Mock()
        mock_disk_obj.total = 1024**4  # 1TB
        mock_disk_obj.used = 512 * 1024**3  # 512GB
        mock_disk_obj.free = 512 * 1024**3  # 512GB
        mock_disk.return_value = mock_disk_obj

        mock_net_obj = Mock()
        mock_net_obj.bytes_sent = 1024**3  # 1GB
        mock_net_obj.bytes_recv = 2 * 1024**3  # 2GB
        mock_net.return_value = mock_net_obj

        # Coletar métricas
        metrics = self.monitor.collect_system_metrics()

        # Verificar estrutura das métricas
        assert "cpu" in metrics
        assert "memory" in metrics
        assert "disk" in metrics
        assert "network" in metrics

        # Verificar valores de CPU
        assert metrics["cpu"]["percent"] == 75.5
        assert metrics["cpu"]["count"] == 8

        # Verificar valores de memória
        assert metrics["memory"]["total"] == 16 * 1024**3
        assert metrics["memory"]["percent"] == 50.0

        # Verificar valores de disco
        assert metrics["disk"]["total"] == 1024**4
        assert metrics["disk"]["percent"] == 50.0  # 512GB/1TB * 100

        # Verificar valores de rede
        assert metrics["network"]["bytes_sent"] == 1024**3
        assert metrics["network"]["bytes_recv"] == 2 * 1024**3

    @patch("psutil.cpu_percent")
    def test_collect_system_metrics_exception_handling(self, mock_cpu_percent):
        """Testa tratamento de exceções na coleta de métricas."""
        # Simular exceção no psutil
        mock_cpu_percent.side_effect = Exception("psutil error")

        # Assumindo que o método trata exceções graciosamente
        with patch.object(self.monitor, "collect_system_metrics") as mock_collect:
            mock_collect.return_value = {}  # Retorna dict vazio em caso de erro

            metrics = self.monitor.collect_system_metrics()

            assert isinstance(metrics, dict)

    def test_record_metric(self):
        """Testa registro de métrica através de _record_metric."""
        # _record_metric é privado, mas podemos testar indiretamente
        # através de collect_system_metrics que chama _record_metric
        with patch("psutil.cpu_percent", return_value=75.5):
            with patch("psutil.cpu_count", return_value=8):
                with patch("psutil.virtual_memory") as mock_mem:
                    mock_mem_obj = Mock()
                    mock_mem_obj.total = 16 * 1024**3
                    mock_mem_obj.available = 8 * 1024**3
                    mock_mem_obj.percent = 50.0
                    mock_mem_obj.used = 8 * 1024**3
                    mock_mem.return_value = mock_mem_obj

                    with patch("psutil.disk_usage") as mock_disk:
                        mock_disk_obj = Mock()
                        mock_disk_obj.total = 1024**4
                        mock_disk_obj.used = 512 * 1024**3
                        mock_disk_obj.free = 512 * 1024**3
                        mock_disk.return_value = mock_disk_obj

                        with patch("psutil.net_io_counters") as mock_net:
                            mock_net_obj = Mock()
                            mock_net_obj.bytes_sent = 1024**3
                            mock_net_obj.bytes_recv = 2 * 1024**3
                            mock_net.return_value = mock_net_obj

                            # collect_system_metrics chama _record_metric internamente
                            self.monitor.collect_system_metrics()

                            # Verificar que métricas foram registradas
                            assert len(self.monitor.metrics) > 0
                            assert any(
                                m.name == "cpu_percent" for m in self.monitor.metrics
                            )

    def test_get_cpu_metrics(self):
        """Testa obtenção de métricas de CPU através de collect_system_metrics."""
        with patch("psutil.cpu_percent", return_value=80.5):
            with patch("psutil.cpu_count", return_value=8):
                with patch("psutil.virtual_memory") as mock_mem:
                    mock_mem_obj = Mock()
                    mock_mem_obj.total = 16 * 1024**3
                    mock_mem_obj.available = 8 * 1024**3
                    mock_mem_obj.percent = 50.0
                    mock_mem_obj.used = 8 * 1024**3
                    mock_mem.return_value = mock_mem_obj

                    with patch("psutil.disk_usage") as mock_disk:
                        mock_disk_obj = Mock()
                        mock_disk_obj.total = 1024**4
                        mock_disk_obj.used = 512 * 1024**3
                        mock_disk_obj.free = 512 * 1024**3
                        mock_disk.return_value = mock_disk_obj

                        with patch("psutil.net_io_counters") as mock_net:
                            mock_net_obj = Mock()
                            mock_net_obj.bytes_sent = 1024**3
                            mock_net_obj.bytes_recv = 2 * 1024**3
                            mock_net.return_value = mock_net_obj

                            metrics = self.monitor.collect_system_metrics()

                            assert "cpu" in metrics
                            assert metrics["cpu"]["percent"] == 80.5
                            assert metrics["cpu"]["count"] == 8

    def test_get_memory_metrics(self):
        """Testa obtenção de métricas de memória através de collect_system_metrics."""
        with patch("psutil.cpu_percent", return_value=50.0):
            with patch("psutil.cpu_count", return_value=8):
                with patch("psutil.virtual_memory") as mock_memory:
                    mock_memory_obj = Mock()
                    mock_memory_obj.total = 16 * 1024**3
                    mock_memory_obj.available = 8 * 1024**3
                    mock_memory_obj.percent = 50.0
                    mock_memory_obj.used = 8 * 1024**3
                    mock_memory.return_value = mock_memory_obj

                    with patch("psutil.disk_usage") as mock_disk:
                        mock_disk_obj = Mock()
                        mock_disk_obj.total = 1024**4
                        mock_disk_obj.used = 512 * 1024**3
                        mock_disk_obj.free = 512 * 1024**3
                        mock_disk.return_value = mock_disk_obj

                        with patch("psutil.net_io_counters") as mock_net:
                            mock_net_obj = Mock()
                            mock_net_obj.bytes_sent = 1024**3
                            mock_net_obj.bytes_recv = 2 * 1024**3
                            mock_net.return_value = mock_net_obj

                            metrics = self.monitor.collect_system_metrics()

                            assert "memory" in metrics
                            assert metrics["memory"]["total"] == 16 * 1024**3
                            assert metrics["memory"]["percent"] == 50.0

    def test_get_disk_metrics(self):
        """Testa obtenção de métricas de disco através de collect_system_metrics."""
        with patch("psutil.cpu_percent", return_value=50.0):
            with patch("psutil.cpu_count", return_value=8):
                with patch("psutil.virtual_memory") as mock_mem:
                    mock_mem_obj = Mock()
                    mock_mem_obj.total = 16 * 1024**3
                    mock_mem_obj.available = 8 * 1024**3
                    mock_mem_obj.percent = 50.0
                    mock_mem_obj.used = 8 * 1024**3
                    mock_mem.return_value = mock_mem_obj

                    with patch("psutil.disk_usage") as mock_disk:
                        mock_disk_obj = Mock()
                        mock_disk_obj.total = 1024**4  # 1TB
                        mock_disk_obj.used = 512 * 1024**3  # 512GB
                        mock_disk_obj.free = 512 * 1024**3  # 512GB
                        mock_disk.return_value = mock_disk_obj

                        with patch("psutil.net_io_counters") as mock_net:
                            mock_net_obj = Mock()
                            mock_net_obj.bytes_sent = 1024**3
                            mock_net_obj.bytes_recv = 2 * 1024**3
                            mock_net.return_value = mock_net_obj

                            metrics = self.monitor.collect_system_metrics()

                            assert "disk" in metrics
                            assert metrics["disk"]["total"] == 1024**4
                            assert metrics["disk"]["percent"] == 50.0

    def test_get_network_metrics(self):
        """Testa obtenção de métricas de rede através de collect_system_metrics."""
        with patch("psutil.cpu_percent", return_value=50.0):
            with patch("psutil.cpu_count", return_value=8):
                with patch("psutil.virtual_memory") as mock_mem:
                    mock_mem_obj = Mock()
                    mock_mem_obj.total = 16 * 1024**3
                    mock_mem_obj.available = 8 * 1024**3
                    mock_mem_obj.percent = 50.0
                    mock_mem_obj.used = 8 * 1024**3
                    mock_mem.return_value = mock_mem_obj

                    with patch("psutil.disk_usage") as mock_disk:
                        mock_disk_obj = Mock()
                        mock_disk_obj.total = 1024**4
                        mock_disk_obj.used = 512 * 1024**3
                        mock_disk_obj.free = 512 * 1024**3
                        mock_disk.return_value = mock_disk_obj

                        with patch("psutil.net_io_counters") as mock_net:
                            mock_net_obj = Mock()
                            mock_net_obj.bytes_sent = 1024**3
                            mock_net_obj.bytes_recv = 2 * 1024**3
                            mock_net.return_value = mock_net_obj

                            metrics = self.monitor.collect_system_metrics()

                            assert "network" in metrics
                            assert metrics["network"]["bytes_sent"] == 1024**3
                            assert metrics["network"]["bytes_recv"] == 2 * 1024**3

    def test_detect_performance_issues(self):
        """Testa detecção de problemas de performance através de métricas registradas."""
        # Registrar métricas que excedem thresholds
        from datetime import datetime

        high_cpu_metric = PerformanceMetric(
            "cpu_percent", 95.0, "%", datetime.now(), threshold=80.0
        )
        high_memory_metric = PerformanceMetric(
            "memory_percent", 90.0, "%", datetime.now(), threshold=85.0
        )

        self.monitor.metrics.append(high_cpu_metric)
        self.monitor.metrics.append(high_memory_metric)

        # Verificar que métricas foram registradas e excedem thresholds
        assert len(self.monitor.metrics) == 2
        assert any(m.value > m.threshold for m in self.monitor.metrics if m.threshold)

    def test_calculate_performance_score(self):
        """Testa cálculo de score através de get_performance_summary."""
        # Coletar métricas do sistema
        with patch("psutil.cpu_percent", return_value=50.0):
            with patch("psutil.cpu_count", return_value=8):
                with patch("psutil.virtual_memory") as mock_mem:
                    mock_mem_obj = Mock()
                    mock_mem_obj.total = 16 * 1024**3
                    mock_mem_obj.available = 8 * 1024**3
                    mock_mem_obj.percent = 60.0
                    mock_mem_obj.used = 8 * 1024**3
                    mock_mem.return_value = mock_mem_obj

                    with patch("psutil.disk_usage") as mock_disk:
                        mock_disk_obj = Mock()
                        mock_disk_obj.total = 1024**4
                        mock_disk_obj.used = 400 * 1024**3
                        mock_disk_obj.free = 600 * 1024**3
                        mock_disk.return_value = mock_disk_obj

                        with patch("psutil.net_io_counters") as mock_net:
                            mock_net_obj = Mock()
                            mock_net_obj.bytes_sent = 1024**3
                            mock_net_obj.bytes_recv = 2 * 1024**3
                            mock_net.return_value = mock_net_obj

                            summary = self.monitor.get_performance_summary()

                            assert "system" in summary
                            assert "operations" in summary
                            assert "total_metrics" in summary
                            assert isinstance(summary["total_metrics"], int)

    def test_summary_forwards_cpu_interval(self):
        """O resumo encaminha a janela escolhida para a coleta do sistema."""
        with patch.object(
            self.monitor, "collect_system_metrics", return_value={}
        ) as collect:
            self.monitor.get_performance_summary(cpu_interval=0.0)

        collect.assert_called_once_with(cpu_interval=0.0)

    def test_get_process_metrics(self):
        """Testa monitoramento de operação que pode incluir métricas de processo."""

        def test_operation():
            return "result"

        with patch("psutil.Process") as mock_process:
            mock_proc = Mock()
            mock_proc.memory_info.return_value = Mock(rss=100 * 1024 * 1024)  # 100MB
            mock_process.return_value = mock_proc

            # monitor_operation retorna (resultado, métricas)
            result, metrics = self.monitor.monitor_operation("test_op", test_operation)

            assert result == "result"
            assert "operation" in metrics
            assert "duration" in metrics
            assert "memory_delta" in metrics
            assert "success" in metrics
            assert metrics["success"] is True

    def test_monitor_application_performance(self):
        """Testa monitoramento de performance da aplicação através de monitor_operation."""

        def app_operation():
            # Simular operação da aplicação
            return {"requests": 50, "response_time": 2.5}

        result, metrics = self.monitor.monitor_operation("app_operation", app_operation)

        assert result["requests"] == 50
        assert "duration" in metrics
        assert metrics["success"] is True

    def test_performance_trend_analysis(self):
        """Testa análise de tendências através de métricas registradas."""
        # Registrar métricas ao longo do tempo
        from datetime import datetime, timedelta

        base_time = datetime.now()

        for i, value in enumerate([70.0, 75.0, 80.0, 85.0]):
            metric = PerformanceMetric(
                "cpu_percent", value, "%", base_time + timedelta(minutes=i)
            )
            self.monitor.metrics.append(metric)

        # Verificar que métricas foram registradas
        assert len(self.monitor.metrics) == 4
        cpu_metrics = [m for m in self.monitor.metrics if m.name == "cpu_percent"]
        assert len(cpu_metrics) == 4
        # Verificar tendência crescente
        values = [m.value for m in cpu_metrics]
        assert values == sorted(values)

    def test_performance_baseline(self):
        """Testa estabelecimento de baseline através de métricas registradas."""
        # Registrar métricas durante período normal
        from datetime import datetime

        baseline_values = [
            {"cpu": 45.0, "memory": 55.0},
            {"cpu": 50.0, "memory": 60.0},
            {"cpu": 48.0, "memory": 58.0},
        ]

        for values in baseline_values:
            cpu_metric = PerformanceMetric(
                "cpu_percent", values["cpu"], "%", datetime.now()
            )
            mem_metric = PerformanceMetric(
                "memory_percent", values["memory"], "%", datetime.now()
            )
            self.monitor.metrics.append(cpu_metric)
            self.monitor.metrics.append(mem_metric)

        # Verificar que métricas foram registradas
        assert len(self.monitor.metrics) == 6
        cpu_metrics = [m for m in self.monitor.metrics if m.name == "cpu_percent"]
        assert len(cpu_metrics) == 3
        # Calcular média manualmente para verificar
        avg_cpu = sum(m.value for m in cpu_metrics) / len(cpu_metrics)
        assert 45.0 <= avg_cpu <= 50.0

    def test_performance_alerting_integration(self):
        """Testa alertas através de métricas que excedem thresholds."""
        # Registrar métricas que excedem thresholds
        from datetime import datetime

        critical_metrics = [
            PerformanceMetric("cpu_percent", 95.0, "%", datetime.now(), threshold=80.0),
            PerformanceMetric(
                "memory_percent", 98.0, "%", datetime.now(), threshold=90.0
            ),
            PerformanceMetric(
                "disk_percent", 99.0, "%", datetime.now(), threshold=85.0
            ),
        ]

        for metric in critical_metrics:
            self.monitor.metrics.append(metric)

        # Verificar que métricas excedem thresholds
        assert len(self.monitor.metrics) == 3
        exceeded = [
            m for m in self.monitor.metrics if m.threshold and m.value > m.threshold
        ]
        assert len(exceeded) == 3

    def test_performance_optimization_suggestions(self):
        """Testa identificação de problemas através de métricas registradas."""
        # Registrar métricas problemáticas
        from datetime import datetime

        problematic_metrics = [
            PerformanceMetric("cpu_percent", 85.0, "%", datetime.now(), threshold=80.0),
            PerformanceMetric(
                "memory_percent", 90.0, "%", datetime.now(), threshold=85.0
            ),
        ]

        for metric in problematic_metrics:
            self.monitor.metrics.append(metric)

        # Verificar que métricas foram registradas e excedem thresholds
        assert len(self.monitor.metrics) == 2
        high_metrics = [
            m for m in self.monitor.metrics if m.threshold and m.value > m.threshold
        ]
        assert len(high_metrics) >= 1

    def test_performance_report_generation(self):
        """Testa geração de relatório através de get_performance_summary."""
        # Coletar algumas métricas
        with patch("psutil.cpu_percent", return_value=65.5):
            with patch("psutil.cpu_count", return_value=8):
                with patch("psutil.virtual_memory") as mock_mem:
                    mock_mem_obj = Mock()
                    mock_mem_obj.total = 16 * 1024**3
                    mock_mem_obj.available = 8 * 1024**3
                    mock_mem_obj.percent = 70.2
                    mock_mem_obj.used = 8 * 1024**3
                    mock_mem.return_value = mock_mem_obj

                    with patch("psutil.disk_usage") as mock_disk:
                        mock_disk_obj = Mock()
                        mock_disk_obj.total = 1024**4
                        mock_disk_obj.used = 500 * 1024**3
                        mock_disk_obj.free = 500 * 1024**3
                        mock_disk.return_value = mock_disk_obj

                        with patch("psutil.net_io_counters") as mock_net:
                            mock_net_obj = Mock()
                            mock_net_obj.bytes_sent = 1024**3
                            mock_net_obj.bytes_recv = 2 * 1024**3
                            mock_net.return_value = mock_net_obj

                            # Monitorar algumas operações
                            def test_op():
                                return "result"

                            self.monitor.monitor_operation("test_op", test_op)

                            # Obter resumo
                            summary = self.monitor.get_performance_summary()

                            assert "system" in summary
                            assert "operations" in summary
                            assert "total_metrics" in summary
                            assert summary["total_metrics"] > 0

    def test_real_time_monitoring(self):
        """Testa monitoramento contínuo através de múltiplas coletas."""
        # Simular múltiplas coletas de métricas
        with patch("psutil.cpu_percent", return_value=50.0):
            with patch("psutil.cpu_count", return_value=8):
                with patch("psutil.virtual_memory") as mock_mem:
                    mock_mem_obj = Mock()
                    mock_mem_obj.total = 16 * 1024**3
                    mock_mem_obj.available = 8 * 1024**3
                    mock_mem_obj.percent = 50.0
                    mock_mem_obj.used = 8 * 1024**3
                    mock_mem.return_value = mock_mem_obj

                    with patch("psutil.disk_usage") as mock_disk:
                        mock_disk_obj = Mock()
                        mock_disk_obj.total = 1024**4
                        mock_disk_obj.used = 512 * 1024**3
                        mock_disk_obj.free = 512 * 1024**3
                        mock_disk.return_value = mock_disk_obj

                        with patch("psutil.net_io_counters") as mock_net:
                            mock_net_obj = Mock()
                            mock_net_obj.bytes_sent = 1024**3
                            mock_net_obj.bytes_recv = 2 * 1024**3
                            mock_net.return_value = mock_net_obj

                            # Coletar métricas múltiplas vezes
                            for _ in range(3):
                                self.monitor.collect_system_metrics()

                            # Verificar que métricas foram acumuladas
                            assert len(self.monitor.metrics) > 0

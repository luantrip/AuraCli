"""
Testes para o módulo metrics_collector.

Testa funcionalidades de coleta, armazenamento e análise
de métricas de sistema e aplicação.
"""

from datetime import datetime, timedelta
from unittest.mock import patch

from aura_cli.core.ops_tools.monitoring.metrics_collector import (
    Metric,
    MetricsCollector,
    MetricType,
)


class TestMetricType:
    """Testa enum MetricType."""

    def test_metric_type_values(self):
        """Testa valores dos tipos de métrica."""
        assert MetricType.COUNTER.value == "counter"
        assert MetricType.GAUGE.value == "gauge"
        assert MetricType.HISTOGRAM.value == "histogram"
        assert MetricType.SUMMARY.value == "summary"

    def test_metric_type_semantics(self):
        """Testa semântica dos tipos de métrica."""
        # Counter: sempre cresce (ex: requests_total)
        assert MetricType.COUNTER.value == "counter"

        # Gauge: valor instantâneo (ex: memory_usage)
        assert MetricType.GAUGE.value == "gauge"

        # Histogram: distribuição de valores (ex: response_time_histogram)
        assert MetricType.HISTOGRAM.value == "histogram"

        # Summary: resumo estatístico (ex: response_time_summary)
        assert MetricType.SUMMARY.value == "summary"


class TestMetric:
    """Testa dataclass Metric."""

    def test_metric_creation_minimal(self):
        """Testa criação de métrica com campos mínimos."""
        timestamp = datetime.now()
        metric = Metric(
            name="cpu_usage",
            value=75.5,
            metric_type=MetricType.GAUGE,
            timestamp=timestamp,
        )

        assert metric.name == "cpu_usage"
        assert metric.value == 75.5
        assert metric.metric_type == MetricType.GAUGE
        assert metric.timestamp == timestamp
        assert metric.labels == {}
        assert metric.unit is None

    def test_metric_creation_complete(self):
        """Testa criação de métrica com todos os campos."""
        timestamp = datetime.now()
        labels = {"host": "server1", "region": "us-east-1"}

        metric = Metric(
            name="memory_usage",
            value=1024.0,
            metric_type=MetricType.GAUGE,
            timestamp=timestamp,
            labels=labels,
            unit="bytes",
        )

        assert metric.name == "memory_usage"
        assert metric.value == 1024.0
        assert metric.metric_type == MetricType.GAUGE
        assert metric.timestamp == timestamp
        assert metric.labels == labels
        assert metric.unit == "bytes"

    def test_metric_different_types(self):
        """Testa métricas com diferentes tipos."""
        timestamp = datetime.now()

        # Counter
        counter = Metric("requests_total", 100, MetricType.COUNTER, timestamp)
        assert counter.metric_type == MetricType.COUNTER

        # Gauge
        gauge = Metric("cpu_percent", 85.2, MetricType.GAUGE, timestamp)
        assert gauge.metric_type == MetricType.GAUGE

        # Histogram
        histogram = Metric("response_time", 0.250, MetricType.HISTOGRAM, timestamp)
        assert histogram.metric_type == MetricType.HISTOGRAM

        # Summary
        summary = Metric("latency_summary", 0.150, MetricType.SUMMARY, timestamp)
        assert summary.metric_type == MetricType.SUMMARY

    def test_metric_labels_flexibility(self):
        """Testa flexibilidade dos labels."""
        timestamp = datetime.now()

        # Labels simples
        simple_labels = {"service": "api"}
        metric1 = Metric(
            "requests", 10, MetricType.COUNTER, timestamp, labels=simple_labels
        )
        assert metric1.labels == simple_labels

        # Labels complexos
        complex_labels = {
            "service": "api",
            "version": "v1.2.3",
            "environment": "production",
            "datacenter": "us-west-2a",
        }
        metric2 = Metric(
            "errors", 2, MetricType.COUNTER, timestamp, labels=complex_labels
        )
        assert metric2.labels == complex_labels

    def test_metric_units(self):
        """Testa diferentes unidades de métrica."""
        timestamp = datetime.now()

        units_examples = [
            ("memory_bytes", 1073741824, "bytes"),
            ("response_time", 0.250, "seconds"),
            ("cpu_usage", 75.5, "percent"),
            ("disk_space", 500, "gigabytes"),
            ("network_throughput", 1000, "mbps"),
        ]

        for name, value, unit in units_examples:
            metric = Metric(name, value, MetricType.GAUGE, timestamp, unit=unit)
            assert metric.unit == unit


class TestMetricsCollector:
    """Testa classe MetricsCollector."""

    def setup_method(self):
        """Setup para cada teste."""
        self.collector = MetricsCollector()

    def test_init_default_retention(self):
        """Testa inicialização com retenção padrão."""
        assert self.collector.retention_hours == 24
        assert hasattr(self.collector, "metrics")
        assert hasattr(self.collector, "stats")
        assert isinstance(self.collector.metrics, list)
        assert len(self.collector.metrics) == 0

    def test_init_custom_retention(self):
        """Testa inicialização com retenção customizada."""
        collector = MetricsCollector(retention_hours=48)
        assert collector.retention_hours == 48

    @patch("aura_cli.core.ops_tools.monitoring.metrics_collector.datetime")
    def test_record_metric_basic(self, mock_datetime):
        """Testa registro básico de métrica."""
        mock_now = datetime(2024, 1, 1, 12, 0, 0)
        mock_datetime.now.return_value = mock_now

        self.collector.record_metric(name="cpu_usage", value=75.5)

        assert len(self.collector.metrics) == 1

        metric = self.collector.metrics[0]
        assert metric.name == "cpu_usage"
        assert metric.value == 75.5
        assert metric.metric_type == MetricType.GAUGE  # Default
        assert metric.timestamp == mock_now
        assert metric.labels == {}
        assert metric.unit is None

    @patch("aura_cli.core.ops_tools.monitoring.metrics_collector.datetime")
    def test_record_metric_complete(self, mock_datetime):
        """Testa registro completo de métrica."""
        mock_now = datetime(2024, 1, 1, 12, 0, 0)
        mock_datetime.now.return_value = mock_now

        labels = {"service": "api", "version": "v1"}

        self.collector.record_metric(
            name="requests_total",
            value=1000,
            metric_type=MetricType.COUNTER,
            labels=labels,
            unit="count",
        )

        metric = self.collector.metrics[0]
        assert metric.name == "requests_total"
        assert metric.value == 1000
        assert metric.metric_type == MetricType.COUNTER
        assert metric.labels == labels
        assert metric.unit == "count"

    def test_record_multiple_metrics(self):
        """Testa registro de múltiplas métricas."""
        metrics_data = [
            ("cpu_usage", 75.5, MetricType.GAUGE),
            ("memory_usage", 1024, MetricType.GAUGE),
            ("requests_total", 500, MetricType.COUNTER),
        ]

        for name, value, metric_type in metrics_data:
            self.collector.record_metric(name, value, metric_type)

        assert len(self.collector.metrics) == 3

        # Verificar que todas foram registradas
        names = [m.name for m in self.collector.metrics]
        assert "cpu_usage" in names
        assert "memory_usage" in names
        assert "requests_total" in names

    def test_get_metrics_by_name(self):
        """Testa obtenção de métricas por nome."""
        # Registrar métricas com mesmo nome em tempos diferentes
        for i in range(3):
            self.collector.record_metric(
                name="cpu_usage", value=70.0 + i * 5, labels={"measurement": str(i)}
            )

        # Filtrar métricas por nome diretamente
        cpu_metrics = [m for m in self.collector.metrics if m.name == "cpu_usage"]

        assert len(cpu_metrics) == 3
        assert all(m.name == "cpu_usage" for m in cpu_metrics)

    def test_get_metrics_by_type(self):
        """Testa obtenção de métricas por tipo."""
        # Registrar métricas de diferentes tipos
        metrics_data = [
            ("counter1", 100, MetricType.COUNTER),
            ("gauge1", 75.5, MetricType.GAUGE),
            ("counter2", 200, MetricType.COUNTER),
            ("histogram1", 0.250, MetricType.HISTOGRAM),
        ]

        for name, value, metric_type in metrics_data:
            self.collector.record_metric(name, value, metric_type)

        # Filtrar por tipo COUNTER
        counter_metrics = [
            m for m in self.collector.metrics if m.metric_type == MetricType.COUNTER
        ]

        assert len(counter_metrics) == 2
        assert all(m.metric_type == MetricType.COUNTER for m in counter_metrics)

    def test_get_metrics_by_labels(self):
        """Testa obtenção de métricas por labels."""
        # Registrar métricas com diferentes labels
        metrics_data = [
            ("requests", 100, {"service": "api", "env": "prod"}),
            ("requests", 50, {"service": "web", "env": "prod"}),
            ("requests", 25, {"service": "api", "env": "dev"}),
        ]

        for name, value, labels in metrics_data:
            self.collector.record_metric(name, value, labels=labels)

        # Filtrar por service=api
        api_metrics = [
            m for m in self.collector.metrics if m.labels.get("service") == "api"
        ]

        assert len(api_metrics) == 2
        assert all(m.labels["service"] == "api" for m in api_metrics)

    def test_metrics_retention(self):
        """Testa retenção de métricas (conceito)."""
        base_time = datetime.now()

        # Registrar métrica recente
        self.collector.record_metric("new_metric", 200)

        # Simular lógica de retenção
        retention_hours = self.collector.retention_hours

        # Filtrar métricas dentro do período de retenção
        retained_metrics = [
            m
            for m in self.collector.metrics
            if (base_time - m.timestamp).total_seconds() < retention_hours * 3600
        ]

        # Deve manter a métrica recente (dentro do período)
        assert len(retained_metrics) >= 1
        assert retained_metrics[0].name == "new_metric"

    def test_aggregate_metrics_by_name(self):
        """Testa agregação de métricas por nome."""
        # Registrar múltiplas métricas com mesmo nome
        values = [10, 20, 30, 40]
        for value in values:
            self.collector.record_metric("test_metric", value)

        # Calcular agregações
        test_metrics = [m for m in self.collector.metrics if m.name == "test_metric"]

        total = sum(m.value for m in test_metrics)
        average = total / len(test_metrics)
        minimum = min(m.value for m in test_metrics)
        maximum = max(m.value for m in test_metrics)

        assert total == 100
        assert average == 25.0
        assert minimum == 10
        assert maximum == 40

    def test_get_latest_metric_value(self):
        """Testa obtenção do valor mais recente de uma métrica."""
        with patch(
            "aura_cli.core.ops_tools.monitoring.metrics_collector.datetime"
        ) as mock_datetime:
            base_time = datetime(2024, 1, 1, 12, 0, 0)

            # Registrar métricas em tempos diferentes
            for i in range(3):
                mock_datetime.now.return_value = base_time + timedelta(minutes=i)
                self.collector.record_metric("cpu_usage", 70.0 + i * 5)

        # Obter métrica mais recente
        cpu_metrics = [m for m in self.collector.metrics if m.name == "cpu_usage"]
        latest_metric = max(cpu_metrics, key=lambda m: m.timestamp)

        assert latest_metric.value == 80.0  # 70 + 2*5

    def test_export_metrics_prometheus_format(self):
        """Testa exportação no formato Prometheus (simulação)."""
        # Registrar algumas métricas
        self.collector.record_metric(
            "http_requests_total",
            100,
            MetricType.COUNTER,
            labels={"method": "GET", "status": "200"},
        )

        self.collector.record_metric(
            "memory_usage_bytes", 1073741824, MetricType.GAUGE, unit="bytes"
        )

        # Simular formato Prometheus manualmente
        def format_prometheus(metrics):
            lines = []
            for m in metrics:
                type_name = m.metric_type.value.lower()
                lines.append(f"# TYPE {m.name} {type_name}")
                if m.labels:
                    labels_str = ",".join(f'{k}="{v}"' for k, v in m.labels.items())
                    lines.append(f"{m.name}{{{labels_str}}} {m.value}")
                else:
                    lines.append(f"{m.name} {m.value}")
            return "\n".join(lines)

        result = format_prometheus(self.collector.metrics)

        assert "http_requests_total" in result
        assert "memory_usage_bytes" in result
        assert "counter" in result
        assert "gauge" in result

    def test_calculate_rate(self):
        """Testa cálculo de taxa (rate) para counters."""
        with patch(
            "aura_cli.core.ops_tools.monitoring.metrics_collector.datetime"
        ) as mock_datetime:
            base_time = datetime(2024, 1, 1, 12, 0, 0)

            # Registrar counter em t=0 com valor 100
            mock_datetime.now.return_value = base_time
            self.collector.record_metric("requests_total", 100, MetricType.COUNTER)

            # Registrar counter em t=60s com valor 160
            mock_datetime.now.return_value = base_time + timedelta(seconds=60)
            self.collector.record_metric("requests_total", 160, MetricType.COUNTER)

        # Calcular taxa (requests por segundo)
        counter_metrics = [
            m for m in self.collector.metrics if m.name == "requests_total"
        ]
        counter_metrics.sort(key=lambda m: m.timestamp)

        if len(counter_metrics) >= 2:
            latest = counter_metrics[-1]
            previous = counter_metrics[-2]

            time_diff = (latest.timestamp - previous.timestamp).total_seconds()
            value_diff = latest.value - previous.value
            rate = value_diff / time_diff if time_diff > 0 else 0

            assert rate == 1.0  # (160-100)/60 = 1 request/second

    def test_histogram_buckets_concept(self):
        """Testa conceito de buckets para histogramas."""
        # Simular valores de latência para histogram
        latency_values = [0.1, 0.2, 0.15, 0.3, 0.25, 0.4, 0.35, 0.5]

        for value in latency_values:
            self.collector.record_metric(
                "response_time_seconds", value, MetricType.HISTOGRAM, unit="seconds"
            )

        # Definir buckets típicos para latência
        buckets = [0.1, 0.2, 0.3, 0.4, 0.5, 1.0]

        # Contar valores em cada bucket
        histogram_metrics = [
            m for m in self.collector.metrics if m.name == "response_time_seconds"
        ]
        bucket_counts = {}

        for bucket in buckets:
            count = len([m for m in histogram_metrics if m.value <= bucket])
            bucket_counts[bucket] = count

        assert bucket_counts[0.1] == 1  # Apenas 0.1
        assert bucket_counts[0.2] == 3  # 0.1, 0.2, 0.15
        assert bucket_counts[0.5] == 8  # Todos os valores

    def test_summary_quantiles_concept(self):
        """Testa conceito de quantis para summaries."""
        # Simular valores para summary
        values = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]

        for value in values:
            self.collector.record_metric(
                "request_duration", value, MetricType.SUMMARY, unit="seconds"
            )

        # Calcular quantis típicos
        summary_metrics = [
            m for m in self.collector.metrics if m.name == "request_duration"
        ]
        sorted_values = sorted([m.value for m in summary_metrics])

        # Quantil 50% (mediana)
        p50_index = int(len(sorted_values) * 0.5) - 1
        p50 = sorted_values[p50_index]

        # Quantil 95%
        p95_index = int(len(sorted_values) * 0.95) - 1
        p95 = sorted_values[p95_index]

        assert p50 == 5  # Mediana de 1-10
        assert p95 == 9  # 95º percentil

    def test_metric_validation(self):
        """Testa validação de métricas."""
        # Valores válidos
        valid_cases = [
            ("cpu_usage", 75.5, MetricType.GAUGE),
            ("requests_total", 1000, MetricType.COUNTER),
            ("response_time", 0.250, MetricType.HISTOGRAM),
        ]

        for name, value, metric_type in valid_cases:
            # Não deve levantar exceção
            self.collector.record_metric(name, value, metric_type)

        assert len(self.collector.metrics) == 3

    def test_metrics_time_series(self):
        """Testa série temporal de métricas."""
        with patch(
            "aura_cli.core.ops_tools.monitoring.metrics_collector.datetime"
        ) as mock_datetime:
            base_time = datetime(2024, 1, 1, 12, 0, 0)

            # Simular série temporal de CPU usage
            cpu_values = [70, 75, 80, 85, 90, 85, 80, 75]

            for i, value in enumerate(cpu_values):
                mock_datetime.now.return_value = base_time + timedelta(minutes=i)
                self.collector.record_metric("cpu_usage", value)

        # Analisar série temporal
        cpu_metrics = [m for m in self.collector.metrics if m.name == "cpu_usage"]
        cpu_metrics.sort(key=lambda m: m.timestamp)

        assert len(cpu_metrics) == 8
        assert cpu_metrics[0].value == 70  # Primeiro valor
        assert cpu_metrics[-1].value == 75  # Último valor
        assert max(m.value for m in cpu_metrics) == 90  # Pico

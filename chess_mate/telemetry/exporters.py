"""
Metric exporters for the ChessMate telemetry system.
"""

import json
import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List

from prometheus_client import CollectorRegistry
from prometheus_client import Counter as PrometheusCounter
from prometheus_client import Gauge as PrometheusGauge
from prometheus_client import Histogram as PrometheusHistogram

from . import config
from .metrics import Counter, Gauge, Histogram, Metric

logger = logging.getLogger(__name__)


class MetricExporter(ABC):
    """Base class for metric exporters."""

    @abstractmethod
    def export_metrics(self, metrics: Dict[str, Metric]) -> None:
        """Export metrics to the target system."""
        pass


class PrometheusExporter(MetricExporter):
    """Exports metrics in Prometheus format."""

    def __init__(self):
        self.registry = CollectorRegistry()
        self._prometheus_metrics: Dict[str, Any] = {}

    def export_metrics(self, metrics: Dict[str, Metric]) -> None:
        """Export metrics to Prometheus format."""
        try:
            for name, metric in metrics.items():
                if name not in self._prometheus_metrics:
                    self._create_prometheus_metric(name, metric)

                self._update_prometheus_metric(name, metric)
        except Exception as e:
            logger.error(f"Error exporting metrics to Prometheus: {e}")

    def _create_prometheus_metric(self, name: str, metric: Metric) -> None:
        """Create a new Prometheus metric."""
        try:
            if isinstance(metric, Counter):
                self._prometheus_metrics[name] = PrometheusCounter(
                    name, name, list(metric.labels.keys()) if metric.labels else []
                )
            elif isinstance(metric, Gauge):
                self._prometheus_metrics[name] = PrometheusGauge(
                    name, name, list(metric.labels.keys()) if metric.labels else []
                )
            elif isinstance(metric, Histogram):
                self._prometheus_metrics[name] = PrometheusHistogram(
                    name, name, list(metric.labels.keys()) if metric.labels else [], buckets=list(metric.buckets.keys())
                )
        except Exception as e:
            logger.error(f"Error creating Prometheus metric {name}: {e}")

    def _update_prometheus_metric(self, name: str, metric: Metric) -> None:
        """Update an existing Prometheus metric."""
        try:
            prom_metric = self._prometheus_metrics[name]

            if isinstance(metric, Counter):
                prom_metric.inc(metric.value)
            elif isinstance(metric, Gauge):
                prom_metric.set(metric.value)
            elif isinstance(metric, Histogram):
                prom_metric.observe(metric.value)
        except Exception as e:
            logger.error(f"Error updating Prometheus metric {name}: {e}")


class JSONFileExporter(MetricExporter):
    """Exports metrics to a JSON file."""

    def __init__(self, file_path: str):
        self.file_path = file_path

    def export_metrics(self, metrics: Dict[str, Metric]) -> None:
        """Export metrics to JSON file."""
        try:
            metric_data = {name: metric.to_dict() for name, metric in metrics.items()}

            with open(self.file_path, "w") as f:
                json.dump(metric_data, f, indent=2)
        except Exception as e:
            logger.error(f"Error exporting metrics to JSON file: {e}")


class LogExporter(MetricExporter):
    """Exports metrics to application logs."""

    def export_metrics(self, metrics: Dict[str, Metric]) -> None:
        """Export metrics to logs."""
        try:
            for name, metric in metrics.items():
                logger.info(f"Metric: {name} = {metric.to_dict()}")
        except Exception as e:
            logger.error(f"Error exporting metrics to logs: {e}")


def create_exporters() -> List[MetricExporter]:
    """Create metric exporters based on configuration."""
    exporters = []

    try:
        for exporter_name in config["EXPORTERS"]:
            if exporter_name == "prometheus":
                exporters.append(PrometheusExporter())
            elif exporter_name == "json":
                exporters.append(JSONFileExporter("/app/chess_mate/logs/metrics.json"))
            elif exporter_name == "log":
                exporters.append(LogExporter())
    except Exception as e:
        logger.error(f"Error creating metric exporters: {e}")

    return exporters


# Global exporter instances
exporters = create_exporters()

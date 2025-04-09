"""
Metric collectors for the ChessMate telemetry system.
"""

import logging
import os
from typing import Any, Dict, Optional

import psutil
from django.core.cache import cache
from django.db import connection

from .metrics import ALL_METRICS, Counter, Gauge, Histogram

logger = logging.getLogger(__name__)


class MetricCollector:
    """Base class for metric collectors."""

    def __init__(self):
        self.metrics = ALL_METRICS.copy()

    def collect(self) -> Dict[str, Any]:
        """Collect all metrics."""
        return {name: metric.to_dict() for name, metric in self.metrics.items()}


class SystemMetricCollector(MetricCollector):
    """Collects system-level metrics."""

    def collect_memory_metrics(self) -> None:
        """Collect memory usage metrics."""
        try:
            process = psutil.Process(os.getpid())
            memory_info = process.memory_info()

            self.metrics["system_memory_usage"].set(memory_info.rss)
        except Exception as e:
            logger.error(f"Error collecting memory metrics: {e}")

    def collect_cpu_metrics(self) -> None:
        """Collect CPU usage metrics."""
        try:
            process = psutil.Process(os.getpid())
            cpu_percent = process.cpu_percent(interval=1.0)

            self.metrics["system_cpu_usage"].set(cpu_percent)
        except Exception as e:
            logger.error(f"Error collecting CPU metrics: {e}")


class DatabaseMetricCollector(MetricCollector):
    """Collects database-related metrics."""

    def collect_query_metrics(self) -> None:
        """Collect database query metrics."""
        try:
            for query in connection.queries:
                duration = float(query["time"])
                sql_type = query["sql"].split()[0].upper()

                self.metrics["database_query_duration_seconds"].observe(
                    duration, labels={"query_type": sql_type, "table": "unknown"}
                )
        except Exception as e:
            logger.error(f"Error collecting query metrics: {e}")


class CacheMetricCollector(MetricCollector):
    """Collects cache-related metrics."""

    def collect_cache_metrics(self) -> None:
        """Collect cache operation metrics."""
        try:
            stats = cache.get_statistics() if hasattr(cache, "get_statistics") else {}

            for operation, count in stats.items():
                self.metrics["cache_operations_total"].increment(count, labels={"operation": operation})
        except Exception as e:
            logger.error(f"Error collecting cache metrics: {e}")


class GameAnalysisMetricCollector(MetricCollector):
    """Collects game analysis metrics."""

    def record_analysis_duration(self, duration: float, depth: int, moves: int) -> None:
        """Record the duration of a game analysis."""
        try:
            self.metrics["stockfish_analysis_duration_seconds"].observe(
                duration, labels={"depth": str(depth), "game_length": self._categorize_game_length(moves)}
            )
        except Exception as e:
            logger.error(f"Error recording analysis duration: {e}")

    def record_analysis_quality(self, score: float, analysis_type: str) -> None:
        """Record the quality score of an analysis."""
        try:
            self.metrics["analysis_quality_score"].set(score, labels={"analysis_type": analysis_type})
        except Exception as e:
            logger.error(f"Error recording analysis quality: {e}")

    @staticmethod
    def _categorize_game_length(moves: int) -> str:
        """Categorize game length based on number of moves."""
        if moves < 20:
            return "short"
        elif moves < 40:
            return "medium"
        else:
            return "long"


class BusinessMetricCollector(MetricCollector):
    """Collects business-related metrics."""

    def record_user_registration(self) -> None:
        """Record a new user registration."""
        try:
            self.metrics["user_registrations_total"].increment()
        except Exception as e:
            logger.error(f"Error recording user registration: {e}")

    def record_analysis_request(self, status: str, user_type: str) -> None:
        """Record a game analysis request."""
        try:
            self.metrics["game_analysis_requests_total"].increment(labels={"status": status, "user_type": user_type})
        except Exception as e:
            logger.error(f"Error recording analysis request: {e}")

    def update_active_users(self, count: int, period: str = "daily") -> None:
        """Update the active users count."""
        try:
            self.metrics["active_users"].set(count, labels={"period": period})
        except Exception as e:
            logger.error(f"Error updating active users: {e}")


# Global collector instances
system_collector = SystemMetricCollector()
database_collector = DatabaseMetricCollector()
cache_collector = CacheMetricCollector()
game_collector = GameAnalysisMetricCollector()
business_collector = BusinessMetricCollector()

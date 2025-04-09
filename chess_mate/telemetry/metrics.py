"""
Metrics definitions for the ChessMate telemetry system.
"""

import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, Optional


@dataclass
class Metric:
    """Base class for all metrics."""

    name: str
    value: Any
    timestamp: float = time.time()
    labels: Optional[Dict[str, str]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert metric to dictionary format."""
        return {"name": self.name, "value": self.value, "timestamp": self.timestamp, "labels": self.labels or {}}


@dataclass
class Counter(Metric):
    """Counter metric type."""

    def increment(self, value: float = 1.0, labels: Optional[Dict[str, str]] = None) -> None:
        """Increment counter by value."""
        self.value += value
        self.timestamp = time.time()
        if labels:
            self.labels = labels


@dataclass
class Gauge(Metric):
    """Gauge metric type."""

    def set(self, value: float, labels: Optional[Dict[str, str]] = None) -> None:
        """Set gauge value."""
        self.value = value
        self.timestamp = time.time()
        if labels:
            self.labels = labels


def create_default_buckets() -> Dict[float, int]:
    """Create default histogram buckets."""
    return {0.1: 0, 0.3: 0, 0.5: 0, 1.0: 0, 3.0: 0, 5.0: 0}


def create_db_buckets() -> Dict[float, int]:
    """Create database query histogram buckets."""
    return {0.01: 0, 0.05: 0, 0.1: 0, 0.5: 0, 1.0: 0}


def create_analysis_buckets() -> Dict[float, int]:
    """Create analysis duration histogram buckets."""
    return {1.0: 0, 5.0: 0, 10.0: 0, 30.0: 0, 60.0: 0}


@dataclass
class Histogram(Metric):
    """Histogram metric type."""

    buckets: Dict[float, int] = field(default_factory=create_default_buckets)
    sum: float = 0.0
    count: int = 0

    def observe(self, value: float, labels: Optional[Dict[str, str]] = None) -> None:
        """Record an observation."""
        self.sum += value
        self.count += 1
        self.timestamp = time.time()
        if labels:
            self.labels = labels

        # Update buckets
        for bucket in sorted(self.buckets.keys()):
            if value <= bucket:
                self.buckets[bucket] += 1


# System Metrics
SYSTEM_METRICS = {
    "system_memory_usage": Gauge(name="system_memory_usage", value=0.0, labels={"unit": "bytes"}),
    "system_cpu_usage": Gauge(name="system_cpu_usage", value=0.0, labels={"unit": "percentage"}),
    "system_disk_usage": Gauge(name="system_disk_usage", value=0.0, labels={"unit": "bytes"}),
}

# Request Metrics
REQUEST_METRICS = {
    "http_requests_total": Counter(
        name="http_requests_total", value=0, labels={"method": "", "path": "", "status": ""}
    ),
    "http_request_duration_seconds": Histogram(
        name="http_request_duration_seconds",
        value=None,
        buckets=create_default_buckets(),
        labels={"method": "", "path": ""},
    ),
}

# Business Metrics
BUSINESS_METRICS = {
    "user_registrations_total": Counter(name="user_registrations_total", value=0),
    "game_analysis_requests_total": Counter(
        name="game_analysis_requests_total", value=0, labels={"status": "", "user_type": ""}
    ),
    "active_users": Gauge(name="active_users", value=0, labels={"period": "daily"}),
    "premium_users": Gauge(name="premium_users", value=0),
    "user_sessions": Counter(name="user_sessions", value=0, labels={"user_type": ""}),
}

# Performance Metrics
PERFORMANCE_METRICS = {
    "database_query_duration_seconds": Histogram(
        name="database_query_duration_seconds",
        value=None,
        buckets=create_db_buckets(),
        labels={"query_type": "", "table": ""},
    ),
    "cache_operations_total": Counter(name="cache_operations_total", value=0, labels={"operation": "", "status": ""}),
    "celery_tasks_total": Counter(name="celery_tasks_total", value=0, labels={"task_name": "", "status": ""}),
}

# Game Analysis Metrics
GAME_METRICS = {
    "stockfish_analysis_duration_seconds": Histogram(
        name="stockfish_analysis_duration_seconds",
        value=None,
        buckets=create_analysis_buckets(),
        labels={"depth": "", "game_length": ""},
    ),
    "analysis_quality_score": Gauge(name="analysis_quality_score", value=0.0, labels={"analysis_type": ""}),
    "games_analyzed_total": Counter(
        name="games_analyzed_total", value=0, labels={"analysis_type": "", "game_type": ""}
    ),
    "stockfish_errors_total": Counter(name="stockfish_errors_total", value=0, labels={"error_type": ""}),
}

# Combine all metrics
ALL_METRICS = {**SYSTEM_METRICS, **REQUEST_METRICS, **BUSINESS_METRICS, **PERFORMANCE_METRICS, **GAME_METRICS}

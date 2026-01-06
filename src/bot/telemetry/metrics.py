#!/usr/bin/env python3
"""
Telemetry Metrics Types

Defines different types of metrics that can be collected and tracked.
"""

from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional
import statistics


class MetricType(Enum):
    """Types of metrics that can be collected"""
    COUNTER = "counter"      # Incremental counter (e.g., signal count)
    GAUGE = "gauge"          # Point-in-time value (e.g., active strategies)
    HISTOGRAM = "histogram"  # Distribution of values (e.g., cycle durations)
    TIMER = "timer"          # Duration measurements


@dataclass
class Metric:
    """
    Base metric class for tracking measurements
    """
    name: str
    metric_type: MetricType
    value: float = 0.0
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    tags: Dict[str, str] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert metric to dictionary"""
        return {
            'name': self.name,
            'type': self.metric_type.value,
            'value': self.value,
            'timestamp': self.timestamp.isoformat(),
            'tags': self.tags
        }


@dataclass
class Counter(Metric):
    """
    Counter metric - monotonically increasing value
    """
    def __init__(self, name: str, tags: Optional[Dict[str, str]] = None):
        super().__init__(
            name=name,
            metric_type=MetricType.COUNTER,
            tags=tags or {}
        )
    
    def increment(self, amount: float = 1.0):
        """Increment counter by amount"""
        self.value += amount
        self.timestamp = datetime.now(timezone.utc)
    
    def reset(self):
        """Reset counter to zero"""
        self.value = 0.0
        self.timestamp = datetime.now(timezone.utc)


@dataclass
class Gauge(Metric):
    """
    Gauge metric - arbitrary value that can go up or down
    """
    def __init__(self, name: str, tags: Optional[Dict[str, str]] = None):
        super().__init__(
            name=name,
            metric_type=MetricType.GAUGE,
            tags=tags or {}
        )
    
    def set(self, value: float):
        """Set gauge to specific value"""
        self.value = value
        self.timestamp = datetime.now(timezone.utc)
    
    def add(self, amount: float):
        """Add to current gauge value"""
        self.value += amount
        self.timestamp = datetime.now(timezone.utc)
    
    def subtract(self, amount: float):
        """Subtract from current gauge value"""
        self.value -= amount
        self.timestamp = datetime.now(timezone.utc)


@dataclass
class Histogram:
    """
    Histogram metric - tracks distribution of values
    """
    name: str
    tags: Dict[str, str] = field(default_factory=dict)
    values: List[float] = field(default_factory=list)
    max_samples: int = 1000  # Keep last N samples
    
    def record(self, value: float):
        """Record a value in the histogram"""
        self.values.append(value)
        
        # Keep only last max_samples
        if len(self.values) > self.max_samples:
            self.values = self.values[-self.max_samples:]
    
    def get_stats(self) -> Dict[str, float]:
        """Get statistical summary of histogram"""
        if not self.values:
            return {
                'count': 0,
                'min': 0.0,
                'max': 0.0,
                'mean': 0.0,
                'median': 0.0,
                'stddev': 0.0
            }
        
        return {
            'count': len(self.values),
            'min': min(self.values),
            'max': max(self.values),
            'mean': statistics.mean(self.values),
            'median': statistics.median(self.values),
            'stddev': statistics.stdev(self.values) if len(self.values) > 1 else 0.0
        }
    
    def get_percentile(self, p: float) -> float:
        """Get percentile value (p between 0 and 100)"""
        if not self.values:
            return 0.0
        
        sorted_values = sorted(self.values)
        index = int((p / 100) * len(sorted_values))
        index = min(index, len(sorted_values) - 1)
        return sorted_values[index]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert histogram to dictionary"""
        stats = self.get_stats()
        return {
            'name': self.name,
            'type': 'histogram',
            'tags': self.tags,
            'stats': stats,
            'p50': self.get_percentile(50),
            'p90': self.get_percentile(90),
            'p95': self.get_percentile(95),
            'p99': self.get_percentile(99)
        }


@dataclass
class Timer:
    """
    Timer metric - tracks duration of operations
    """
    name: str
    tags: Dict[str, str] = field(default_factory=dict)
    durations: List[float] = field(default_factory=list)
    max_samples: int = 1000
    start_time: Optional[datetime] = None
    
    def start(self):
        """Start timing"""
        self.start_time = datetime.now(timezone.utc)
    
    def stop(self) -> float:
        """Stop timing and record duration"""
        if self.start_time is None:
            return 0.0
        
        end_time = datetime.now(timezone.utc)
        duration = (end_time - self.start_time).total_seconds()
        self.record(duration)
        self.start_time = None
        return duration
    
    def record(self, duration_seconds: float):
        """Record a duration directly"""
        self.durations.append(duration_seconds)
        
        # Keep only last max_samples
        if len(self.durations) > self.max_samples:
            self.durations = self.durations[-self.max_samples:]
    
    def get_stats(self) -> Dict[str, float]:
        """Get statistical summary of timings"""
        if not self.durations:
            return {
                'count': 0,
                'min': 0.0,
                'max': 0.0,
                'mean': 0.0,
                'median': 0.0
            }
        
        return {
            'count': len(self.durations),
            'min': min(self.durations),
            'max': max(self.durations),
            'mean': statistics.mean(self.durations),
            'median': statistics.median(self.durations)
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert timer to dictionary"""
        return {
            'name': self.name,
            'type': 'timer',
            'tags': self.tags,
            'stats': self.get_stats()
        }

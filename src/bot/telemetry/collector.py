#!/usr/bin/env python3
"""
Telemetry Collector

Central singleton for collecting and managing telemetry data from the trading bot.
Thread-safe implementation with ring buffer for time-series data.
"""

import json
import logging
import threading
from collections import deque, defaultdict
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional, Deque

from .metrics import Counter, Gauge, Histogram, Timer, MetricType

logger = logging.getLogger(__name__)


class TelemetryCollector:
    """
    Singleton telemetry collector for tracking bot metrics
    
    Features:
    - Thread-safe metric collection
    - Ring buffer for time-series data
    - Multiple metric types (counters, gauges, histograms, timers)
    - Periodic persistence to disk
    - Memory-efficient storage
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        """Ensure singleton pattern"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        """Initialize telemetry collector"""
        # Avoid re-initialization
        if hasattr(self, '_initialized'):
            return
        
        self._initialized = True
        self._lock = threading.Lock()
        
        # Metrics storage
        self.counters: Dict[str, Counter] = {}
        self.gauges: Dict[str, Gauge] = {}
        self.histograms: Dict[str, Histogram] = {}
        self.timers: Dict[str, Timer] = {}
        
        # Event history (ring buffer)
        self.events: Deque[Dict[str, Any]] = deque(maxlen=1000)
        
        # Signal history (ring buffer)
        self.signals: Deque[Dict[str, Any]] = deque(maxlen=500)
        
        # Cycle history
        self.cycles: Deque[Dict[str, Any]] = deque(maxlen=100)
        
        # Error tracking
        self.errors: Deque[Dict[str, Any]] = deque(maxlen=200)
        
        # Configuration
        self.enabled = True
        self.persistence_path: Optional[Path] = None
        self.last_persistence = datetime.now(timezone.utc)
        
        logger.info("Telemetry collector initialized")
    
    @classmethod
    def instance(cls) -> 'TelemetryCollector':
        """Get singleton instance"""
        return cls()
    
    def configure(self, enabled: bool = True, persistence_path: Optional[str] = None):
        """
        Configure telemetry collector
        
        Args:
            enabled: Enable/disable telemetry collection
            persistence_path: Path for persisting telemetry data
        """
        self.enabled = enabled
        if persistence_path:
            self.persistence_path = Path(persistence_path)
            self.persistence_path.mkdir(parents=True, exist_ok=True)
            logger.info(f"Telemetry persistence enabled: {self.persistence_path}")
    
    # ========== Counter Methods ==========
    
    def increment(self, name: str, amount: float = 1.0, **tags):
        """
        Increment a counter metric
        
        Args:
            name: Counter name
            amount: Amount to increment by
            **tags: Optional tags for grouping (e.g., strategy='mean_reversion')
        """
        if not self.enabled:
            return
        
        with self._lock:
            key = self._make_key(name, tags)
            
            if key not in self.counters:
                self.counters[key] = Counter(name, tags=tags)
            
            self.counters[key].increment(amount)
    
    def get_counter(self, name: str, **tags) -> float:
        """Get current counter value"""
        key = self._make_key(name, tags)
        with self._lock:
            if key in self.counters:
                return self.counters[key].value
        return 0.0
    
    # ========== Gauge Methods ==========
    
    def set_gauge(self, name: str, value: float, **tags):
        """
        Set a gauge metric to a specific value
        
        Args:
            name: Gauge name
            value: Value to set
            **tags: Optional tags
        """
        if not self.enabled:
            return
        
        with self._lock:
            key = self._make_key(name, tags)
            
            if key not in self.gauges:
                self.gauges[key] = Gauge(name, tags=tags)
            
            self.gauges[key].set(value)
    
    def get_gauge(self, name: str, **tags) -> float:
        """Get current gauge value"""
        key = self._make_key(name, tags)
        with self._lock:
            if key in self.gauges:
                return self.gauges[key].value
        return 0.0
    
    # ========== Histogram Methods ==========
    
    def record_value(self, name: str, value: float, **tags):
        """
        Record a value in a histogram
        
        Args:
            name: Histogram name
            value: Value to record
            **tags: Optional tags
        """
        if not self.enabled:
            return
        
        with self._lock:
            key = self._make_key(name, tags)
            
            if key not in self.histograms:
                self.histograms[key] = Histogram(name, tags=tags)
            
            self.histograms[key].record(value)
    
    def get_histogram_stats(self, name: str, **tags) -> Dict[str, float]:
        """Get histogram statistics"""
        key = self._make_key(name, tags)
        with self._lock:
            if key in self.histograms:
                return self.histograms[key].get_stats()
        return {'count': 0, 'min': 0, 'max': 0, 'mean': 0, 'median': 0}
    
    # ========== Timer Methods ==========
    
    def record_timing(self, name: str, duration_seconds: float, **tags):
        """
        Record a timing measurement
        
        Args:
            name: Timer name
            duration_seconds: Duration in seconds
            **tags: Optional tags
        """
        if not self.enabled:
            return
        
        with self._lock:
            key = self._make_key(name, tags)
            
            if key not in self.timers:
                self.timers[key] = Timer(name, tags=tags)
            
            self.timers[key].record(duration_seconds)
    
    def get_timer_stats(self, name: str, **tags) -> Dict[str, float]:
        """Get timer statistics"""
        key = self._make_key(name, tags)
        with self._lock:
            if key in self.timers:
                return self.timers[key].get_stats()
        return {'count': 0, 'min': 0, 'max': 0, 'mean': 0, 'median': 0}
    
    # ========== Event Tracking ==========
    
    def record_event(self, event_type: str, data: Dict[str, Any]):
        """
        Record an event
        
        Args:
            event_type: Type of event (e.g., 'cycle_start', 'signal_generated')
            data: Event data dictionary
        """
        if not self.enabled:
            return
        
        event = {
            'type': event_type,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'data': data
        }
        
        with self._lock:
            self.events.append(event)
    
    def record_signal(self, signal_data: Dict[str, Any]):
        """Record a trading signal"""
        if not self.enabled:
            return
        
        signal = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            **signal_data
        }
        
        with self._lock:
            self.signals.append(signal)
    
    def record_cycle(self, cycle_data: Dict[str, Any]):
        """Record a strategy cycle completion"""
        if not self.enabled:
            return
        
        cycle = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            **cycle_data
        }
        
        with self._lock:
            self.cycles.append(cycle)
    
    def record_error(self, error_type: str, error_message: str, context: Optional[Dict[str, Any]] = None):
        """Record an error"""
        if not self.enabled:
            return
        
        error = {
            'type': error_type,
            'message': error_message,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'context': context or {}
        }
        
        with self._lock:
            self.errors.append(error)
    
    # ========== Data Retrieval ==========
    
    def get_recent_signals(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent signals"""
        with self._lock:
            return list(self.signals)[-limit:]
    
    def get_recent_events(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recent events"""
        with self._lock:
            return list(self.events)[-limit:]
    
    def get_recent_cycles(self, limit: int = 24) -> List[Dict[str, Any]]:
        """Get recent cycle data"""
        with self._lock:
            return list(self.cycles)[-limit:]
    
    def get_recent_errors(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent errors"""
        with self._lock:
            return list(self.errors)[-limit:]
    
    def get_all_metrics(self) -> Dict[str, Any]:
        """Get snapshot of all metrics"""
        with self._lock:
            return {
                'counters': {k: c.to_dict() for k, c in self.counters.items()},
                'gauges': {k: g.to_dict() for k, g in self.gauges.items()},
                'histograms': {k: h.to_dict() for k, h in self.histograms.items()},
                'timers': {k: t.to_dict() for k, t in self.timers.items()},
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
    
    def get_summary(self) -> Dict[str, Any]:
        """Get high-level summary of telemetry data"""
        with self._lock:
            return {
                'total_counters': len(self.counters),
                'total_gauges': len(self.gauges),
                'total_histograms': len(self.histograms),
                'total_timers': len(self.timers),
                'total_events': len(self.events),
                'total_signals': len(self.signals),
                'total_cycles': len(self.cycles),
                'total_errors': len(self.errors),
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
    
    # ========== Persistence ==========
    
    def persist(self, force: bool = False):
        """
        Persist telemetry data to disk
        
        Args:
            force: Force persistence regardless of time since last persist
        """
        if not self.enabled or not self.persistence_path:
            return
        
        # Check if enough time has passed since last persistence
        if not force:
            time_since_last = datetime.now(timezone.utc) - self.last_persistence
            if time_since_last < timedelta(minutes=5):
                return
        
        try:
            timestamp = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')
            filepath = self.persistence_path / f"telemetry_{timestamp}.json"
            
            data = {
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'metrics': self.get_all_metrics(),
                'signals': self.get_recent_signals(100),
                'cycles': self.get_recent_cycles(50),
                'errors': self.get_recent_errors(100),
                'summary': self.get_summary()
            }
            
            with open(filepath, 'w') as f:
                json.dump(data, f, indent=2)
            
            self.last_persistence = datetime.now(timezone.utc)
            logger.debug(f"Telemetry persisted to {filepath}")
            
        except Exception as e:
            logger.error(f"Failed to persist telemetry: {e}")
    
    def export_to_json(self, filepath: str) -> bool:
        """
        Export all telemetry data to JSON file
        
        Args:
            filepath: Path to output file
            
        Returns:
            True if successful
        """
        try:
            data = {
                'export_timestamp': datetime.now(timezone.utc).isoformat(),
                'metrics': self.get_all_metrics(),
                'signals': list(self.signals),
                'cycles': list(self.cycles),
                'events': list(self.events),
                'errors': list(self.errors),
                'summary': self.get_summary()
            }
            
            with open(filepath, 'w') as f:
                json.dump(data, f, indent=2)
            
            logger.info(f"Telemetry exported to {filepath}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to export telemetry: {e}")
            return False
    
    # ========== Utility Methods ==========
    
    @staticmethod
    def _make_key(name: str, tags: Dict[str, str]) -> str:
        """Create unique key from name and tags"""
        if not tags:
            return name
        
        tag_str = ','.join(f"{k}={v}" for k, v in sorted(tags.items()))
        return f"{name}:{tag_str}"
    
    def reset(self):
        """Reset all telemetry data (for testing)"""
        with self._lock:
            self.counters.clear()
            self.gauges.clear()
            self.histograms.clear()
            self.timers.clear()
            self.events.clear()
            self.signals.clear()
            self.cycles.clear()
            self.errors.clear()
        
        logger.info("Telemetry data reset")

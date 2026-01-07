#!/usr/bin/env python3
"""
Telemetry Collector

Central singleton for collecting and managing telemetry data from the trading bot.
Thread-safe implementation with file-based persistence for inter-process communication.
"""

import json
import logging
import threading
from collections import deque, defaultdict
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional, Deque

from .metrics import Counter, Gauge, Histogram, Timer, MetricType
from .file_utils import (
    atomic_write_json,
    ensure_telemetry_structure,
    generate_timestamped_filename,
    rotate_files,
    get_file_mtime
)

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
        
        # Metrics storage (in-memory for fast access)
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
        
        # File-based telemetry paths
        self.telemetry_base_path: Optional[Path] = None
        self.metrics_file: Optional[Path] = None
        self.state_file: Optional[Path] = None
        self.manifest_file: Optional[Path] = None
        
        # Bot state for file-based telemetry
        self.bot_start_time: Optional[datetime] = None
        self.next_cycle_time: Optional[datetime] = None
        self.run_interval_minutes: int = 5
        self.sync_second: int = 15
        self.is_running: bool = False
        self.trading_hours_active: bool = False
        
        # Retention limits
        self.max_signals = 500
        self.max_cycles = 100
        self.max_errors = 200
        
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
            persistence_path: Path for persisting telemetry data (file-based storage)
        """
        self.enabled = enabled
        if persistence_path:
            self.telemetry_base_path = Path(persistence_path)
            self.persistence_path = self.telemetry_base_path  # Backward compatibility
            
            # Set up file paths
            self.metrics_file = self.telemetry_base_path / 'metrics.json'
            self.state_file = self.telemetry_base_path / 'state.json'
            self.manifest_file = self.telemetry_base_path / 'manifest.json'
            
            # Ensure directory structure exists
            ensure_telemetry_structure(self.telemetry_base_path)
            
            logger.info(f"Telemetry file-based persistence enabled: {self.telemetry_base_path}")
    
    def set_bot_state(self, bot_start_time: datetime, run_interval_minutes: int, 
                     sync_second: int, is_running: bool = True, reset_session_metrics: bool = True):
        """
        Set bot state information for file-based telemetry
        
        Args:
            bot_start_time: When the bot started
            run_interval_minutes: Interval between bot cycles
            sync_second: Second of the minute to sync to
            is_running: Whether bot is currently running
            reset_session_metrics: Whether to reset session counters on startup
        """
        self.bot_start_time = bot_start_time
        self.run_interval_minutes = run_interval_minutes
        self.sync_second = sync_second
        self.is_running = is_running
        
        # Reset session metrics if requested
        if reset_session_metrics:
            logger.info("Resetting session metrics for new bot run")
            with self._lock:
                # Clear in-memory metrics but preserve structure
                self.counters.clear()
                self.gauges.clear()
                self.histograms.clear()
                self.timers.clear()
            
            # Write empty metrics to file
            self._write_metrics()
        
        # Write initial state
        self._write_state()
    
    def set_next_cycle_time(self, next_cycle_time: datetime):
        """
        Set the next cycle time
        
        Args:
            next_cycle_time: When the next cycle will run
        """
        self.next_cycle_time = next_cycle_time
        self._write_state()
    
    def set_trading_hours_active(self, active: bool):
        """
        Set trading hours status
        
        Args:
            active: Whether currently in trading hours
        """
        self.trading_hours_active = active
        self._write_state()
    
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
        
        # Write metrics to file
        self._write_metrics()
    
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
        
        # Write metrics to file
        self._write_metrics()
    
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
        
        # Write signal to file
        self._write_signal_file(signal)
    
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
        
        # Write cycle to file and update state
        self._write_cycle_file(cycle)
        self._write_state()
    
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
        
        # Write error to file
        self._write_error_file(error)
    
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
    
    def _write_metrics(self):
        """Write metrics to metrics.json file"""
        if not self.telemetry_base_path or not self.metrics_file:
            return
        
        try:
            with self._lock:
                data = {
                    'timestamp': datetime.now(timezone.utc).isoformat(),
                    'counters': {k: c.to_dict() for k, c in self.counters.items()},
                    'gauges': {k: g.to_dict() for k, g in self.gauges.items()},
                    'histograms': {k: h.to_dict() for k, h in self.histograms.items()},
                    'timers': {k: t.to_dict() for k, t in self.timers.items()},
                }
            
            atomic_write_json(self.metrics_file, data, compress=False)
            self._update_manifest()
            
        except Exception as e:
            logger.error(f"Failed to write metrics: {e}")
    
    def _write_state(self):
        """Write bot state to state.json file"""
        if not self.telemetry_base_path or not self.state_file:
            return
        
        try:
            data = {
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'bot_start_time': self.bot_start_time.isoformat() if self.bot_start_time else None,
                'next_cycle_time': self.next_cycle_time.isoformat() if self.next_cycle_time else None,
                'last_cycle_time': self.cycles[-1].get('timestamp') if self.cycles else None,
                'is_running': self.is_running,
                'trading_hours_active': self.trading_hours_active,
                'run_interval_minutes': self.run_interval_minutes,
                'sync_second': self.sync_second
            }
            
            atomic_write_json(self.state_file, data, compress=False)
            self._update_manifest()
            
        except Exception as e:
            logger.error(f"Failed to write state: {e}")
    
    def _write_signal_file(self, signal_data: Dict[str, Any]):
        """Write individual signal to file"""
        if not self.telemetry_base_path:
            return
        
        try:
            signals_dir = self.telemetry_base_path / 'signals'
            filename = generate_timestamped_filename('signal')
            filepath = signals_dir / filename
            
            atomic_write_json(filepath, signal_data, compress=False)
            
            # Rotate old signal files
            rotate_files(signals_dir, 'signal_*.json', self.max_signals, compress_old=True)
            self._update_manifest()
            
        except Exception as e:
            logger.error(f"Failed to write signal file: {e}")
    
    def _write_cycle_file(self, cycle_data: Dict[str, Any]):
        """Write individual cycle to file"""
        if not self.telemetry_base_path:
            return
        
        try:
            cycles_dir = self.telemetry_base_path / 'cycles'
            filename = generate_timestamped_filename('cycle')
            filepath = cycles_dir / filename
            
            atomic_write_json(filepath, cycle_data, compress=False)
            
            # Rotate old cycle files
            rotate_files(cycles_dir, 'cycle_*.json', self.max_cycles, compress_old=True)
            self._update_manifest()
            
        except Exception as e:
            logger.error(f"Failed to write cycle file: {e}")
    
    def _write_error_file(self, error_data: Dict[str, Any]):
        """Write individual error to file"""
        if not self.telemetry_base_path:
            return
        
        try:
            errors_dir = self.telemetry_base_path / 'errors'
            filename = generate_timestamped_filename('error')
            filepath = errors_dir / filename
            
            atomic_write_json(filepath, error_data, compress=False)
            
            # Rotate old error files
            rotate_files(errors_dir, 'error_*.json', self.max_errors, compress_old=True)
            self._update_manifest()
            
        except Exception as e:
            logger.error(f"Failed to write error file: {e}")
    
    def _update_manifest(self):
        """Update manifest.json with current state"""
        if not self.telemetry_base_path or not self.manifest_file:
            return
        
        try:
            signals_dir = self.telemetry_base_path / 'signals'
            cycles_dir = self.telemetry_base_path / 'cycles'
            errors_dir = self.telemetry_base_path / 'errors'
            
            # Count files in each directory
            signal_files = list(signals_dir.glob('signal_*.json*')) if signals_dir.exists() else []
            cycle_files = list(cycles_dir.glob('cycle_*.json*')) if cycles_dir.exists() else []
            error_files = list(errors_dir.glob('error_*.json*')) if errors_dir.exists() else []
            
            # Get latest files (sorted by mtime)
            latest_signals = sorted(signal_files, key=lambda f: f.stat().st_mtime, reverse=True)[:10]
            latest_cycles = sorted(cycle_files, key=lambda f: f.stat().st_mtime, reverse=True)[:10]
            latest_errors = sorted(error_files, key=lambda f: f.stat().st_mtime, reverse=True)[:10]
            
            manifest_data = {
                'last_updated': datetime.now(timezone.utc).isoformat(),
                'metrics_mtime': get_file_mtime(self.metrics_file) if self.metrics_file else 0,
                'state_mtime': get_file_mtime(self.state_file) if self.state_file else 0,
                'signal_count': len(signal_files),
                'cycle_count': len(cycle_files),
                'error_count': len(error_files),
                'latest_signals': [f.name for f in latest_signals],
                'latest_cycles': [f.name for f in latest_cycles],
                'latest_errors': [f.name for f in latest_errors]
            }
            
            atomic_write_json(self.manifest_file, manifest_data, compress=False)
            
        except Exception as e:
            logger.error(f"Failed to update manifest: {e}")
    
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

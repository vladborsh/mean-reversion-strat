#!/usr/bin/env python3
"""
Telemetry File Reader

Read-only telemetry reader for TUI and monitoring tools.
Reads telemetry data from filesystem written by TelemetryCollector.
"""

import logging
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone

from .file_utils import read_json, get_file_mtime, list_recent_files

logger = logging.getLogger(__name__)


class TelemetryFileReader:
    """
    Read-only telemetry reader for inter-process communication
    
    Reads telemetry data from filesystem that was written by TelemetryCollector.
    Includes caching to avoid unnecessary file I/O.
    """
    
    def __init__(self, telemetry_path: str = 'telemetry_data'):
        """
        Initialize telemetry file reader
        
        Args:
            telemetry_path: Path to telemetry data directory
        """
        self.telemetry_path = Path(telemetry_path)
        self.metrics_file = self.telemetry_path / 'metrics.json'
        self.state_file = self.telemetry_path / 'state.json'
        self.manifest_file = self.telemetry_path / 'manifest.json'
        
        # Cache with modification times
        self._metrics_cache: Optional[Dict[str, Any]] = None
        self._metrics_mtime: float = 0.0
        
        self._state_cache: Optional[Dict[str, Any]] = None
        self._state_mtime: float = 0.0
        
        self._manifest_cache: Optional[Dict[str, Any]] = None
        self._manifest_mtime: float = 0.0
        
        logger.info(f"TelemetryFileReader initialized for path: {self.telemetry_path}")
    
    def read_metrics(self, force_refresh: bool = False) -> Dict[str, Any]:
        """
        Read metrics from metrics.json
        
        Args:
            force_refresh: Force re-read even if cached
            
        Returns:
            Metrics dictionary
        """
        try:
            current_mtime = get_file_mtime(self.metrics_file)
            
            # Return cached data if file hasn't changed
            if not force_refresh and self._metrics_cache and current_mtime == self._metrics_mtime:
                return self._metrics_cache
            
            # Read fresh data
            data = read_json(self.metrics_file)
            
            # Update cache
            self._metrics_cache = data
            self._metrics_mtime = current_mtime
            
            return data
            
        except Exception as e:
            logger.error(f"Failed to read metrics: {e}")
            return {}
    
    def read_state(self, force_refresh: bool = False) -> Dict[str, Any]:
        """
        Read bot state from state.json
        
        Args:
            force_refresh: Force re-read even if cached
            
        Returns:
            State dictionary
        """
        try:
            current_mtime = get_file_mtime(self.state_file)
            
            # Return cached data if file hasn't changed
            if not force_refresh and self._state_cache and current_mtime == self._state_mtime:
                return self._state_cache
            
            # Read fresh data
            data = read_json(self.state_file)
            
            # Update cache
            self._state_cache = data
            self._state_mtime = current_mtime
            
            return data
            
        except Exception as e:
            logger.error(f"Failed to read state: {e}")
            return {}
    
    def read_manifest(self, force_refresh: bool = False) -> Dict[str, Any]:
        """
        Read manifest from manifest.json
        
        Args:
            force_refresh: Force re-read even if cached
            
        Returns:
            Manifest dictionary
        """
        try:
            current_mtime = get_file_mtime(self.manifest_file)
            
            # Return cached data if file hasn't changed
            if not force_refresh and self._manifest_cache and current_mtime == self._manifest_mtime:
                return self._manifest_cache
            
            # Read fresh data
            data = read_json(self.manifest_file)
            
            # Update cache
            self._manifest_cache = data
            self._manifest_mtime = current_mtime
            
            return data
            
        except Exception as e:
            logger.error(f"Failed to read manifest: {e}")
            return {}
    
    def has_updates(self) -> bool:
        """
        Check if telemetry data has been updated since last read
        
        Returns:
            True if manifest has been updated
        """
        current_mtime = get_file_mtime(self.manifest_file)
        return current_mtime > self._manifest_mtime
    
    def get_counter(self, name: str, **tags) -> float:
        """
        Get counter value from metrics
        
        Args:
            name: Counter name
            **tags: Optional tags
            
        Returns:
            Counter value or 0.0
        """
        metrics = self.read_metrics()
        counters = metrics.get('counters', {})
        
        # Build key
        key = self._make_key(name, tags)
        
        if key in counters:
            return counters[key].get('value', 0.0)
        
        return 0.0
    
    def get_gauge(self, name: str, **tags) -> float:
        """
        Get gauge value from metrics
        
        Args:
            name: Gauge name
            **tags: Optional tags
            
        Returns:
            Gauge value or 0.0
        """
        metrics = self.read_metrics()
        gauges = metrics.get('gauges', {})
        
        # Build key
        key = self._make_key(name, tags)
        
        if key in gauges:
            return gauges[key].get('value', 0.0)
        
        return 0.0
    
    def get_recent_signals(self, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Get recent signals from signal files
        
        Args:
            limit: Maximum number of signals to return
            
        Returns:
            List of signal dictionaries
        """
        try:
            signals_dir = self.telemetry_path / 'signals'
            
            if not signals_dir.exists():
                return []
            
            # Get recent signal files
            signal_files = list_recent_files(signals_dir, 'signal_*.json*', limit)
            
            # Read signal data
            signals = []
            for signal_file in signal_files:
                try:
                    # Check if compressed
                    is_compressed = signal_file.name.endswith('.gz')
                    signal_data = read_json(signal_file, compressed=is_compressed)
                    if signal_data:
                        signals.append(signal_data)
                except Exception as e:
                    logger.warning(f"Failed to read signal file {signal_file}: {e}")
            
            return signals
            
        except Exception as e:
            logger.error(f"Failed to get recent signals: {e}")
            return []
    
    def get_recent_cycles(self, limit: int = 24) -> List[Dict[str, Any]]:
        """
        Get recent cycles from cycle files
        
        Args:
            limit: Maximum number of cycles to return
            
        Returns:
            List of cycle dictionaries
        """
        try:
            cycles_dir = self.telemetry_path / 'cycles'
            
            if not cycles_dir.exists():
                return []
            
            # Get recent cycle files
            cycle_files = list_recent_files(cycles_dir, 'cycle_*.json*', limit)
            
            # Read cycle data
            cycles = []
            for cycle_file in cycle_files:
                try:
                    # Check if compressed
                    is_compressed = cycle_file.name.endswith('.gz')
                    cycle_data = read_json(cycle_file, compressed=is_compressed)
                    if cycle_data:
                        cycles.append(cycle_data)
                except Exception as e:
                    logger.warning(f"Failed to read cycle file {cycle_file}: {e}")
            
            return cycles
            
        except Exception as e:
            logger.error(f"Failed to get recent cycles: {e}")
            return []
    
    def get_recent_errors(self, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Get recent errors from error files
        
        Args:
            limit: Maximum number of errors to return
            
        Returns:
            List of error dictionaries
        """
        try:
            errors_dir = self.telemetry_path / 'errors'
            
            if not errors_dir.exists():
                return []
            
            # Get recent error files
            error_files = list_recent_files(errors_dir, 'error_*.json*', limit)
            
            # Read error data
            errors = []
            for error_file in error_files:
                try:
                    # Check if compressed
                    is_compressed = error_file.name.endswith('.gz')
                    error_data = read_json(error_file, compressed=is_compressed)
                    if error_data:
                        errors.append(error_data)
                except Exception as e:
                    logger.warning(f"Failed to read error file {error_file}: {e}")
            
            return errors
            
        except Exception as e:
            logger.error(f"Failed to get recent errors: {e}")
            return []
    
    def get_summary(self) -> Dict[str, Any]:
        """
        Get summary of telemetry data
        
        Returns:
            Summary dictionary with counts
        """
        manifest = self.read_manifest()
        metrics = self.read_metrics()
        state = self.read_state()
        
        return {
            'signal_count': manifest.get('signal_count', 0),
            'cycle_count': manifest.get('cycle_count', 0),
            'error_count': manifest.get('error_count', 0),
            'total_counters': len(metrics.get('counters', {})),
            'total_gauges': len(metrics.get('gauges', {})),
            'is_running': state.get('is_running', False),
            'last_updated': manifest.get('last_updated', 'N/A')
        }
    
    @staticmethod
    def _make_key(name: str, tags: Dict[str, str]) -> str:
        """Create unique key from name and tags"""
        if not tags:
            return name
        
        tag_str = ','.join(f"{k}={v}" for k, v in sorted(tags.items()))
        return f"{name}:{tag_str}"
    
    def clear_cache(self):
        """Clear all cached data"""
        self._metrics_cache = None
        self._metrics_mtime = 0.0
        self._state_cache = None
        self._state_mtime = 0.0
        self._manifest_cache = None
        self._manifest_mtime = 0.0
        logger.debug("Cache cleared")

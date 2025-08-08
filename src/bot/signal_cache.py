#!/usr/bin/env python3
"""
Signal Cache Module

This module provides a caching mechanism to prevent duplicate trading signal notifications.
It tracks sent signals and can identify duplicates based on symbol, direction, and price range.
Supports both in-memory and persistent (DynamoDB) storage options.
"""

import hashlib
import time
import logging
from typing import Dict, Any, Optional, Set
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


def create_signal_cache(use_persistence: bool = False, 
                       price_tolerance: float = 0.0005,
                       cache_duration_hours: int = 24,
                       **kwargs) -> 'SignalCache':
    """
    Factory function to create appropriate signal cache instance
    
    Args:
        use_persistence: If True, use DynamoDB-backed persistent cache
        price_tolerance: Price tolerance for considering signals as duplicates
        cache_duration_hours: How long to keep signals in cache
        **kwargs: Additional arguments for persistent cache (table_name, region_name)
        
    Returns:
        SignalCache or PersistentSignalCache instance
    """
    if use_persistence:
        try:
            from .persistent_signal_cache import PersistentSignalCache
            logger.info("Creating persistent signal cache with DynamoDB storage")
            return PersistentSignalCache(
                price_tolerance=price_tolerance,
                cache_duration_hours=cache_duration_hours,
                **kwargs
            )
        except Exception as e:
            logger.error(f"Failed to create persistent cache, falling back to in-memory: {e}")
            return SignalCache(price_tolerance, cache_duration_hours)
    else:
        logger.info("Creating in-memory signal cache")
        return SignalCache(price_tolerance, cache_duration_hours)


class SignalCache:
    """
    Cache for tracking sent trading signals to prevent duplicate notifications
    """
    
    def __init__(self, price_tolerance: float = 0.0005, cache_duration_hours: int = 24):
        """
        Initialize the signal cache
        
        Args:
            price_tolerance: Price tolerance for considering signals as duplicates (default 0.05%)
            cache_duration_hours: How long to keep signals in cache (default 24 hours)
        """
        self.price_tolerance = price_tolerance
        self.cache_duration_hours = cache_duration_hours
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.signal_count = 0
        self.duplicate_count = 0
        
        logger.info(f"Signal cache initialized with {price_tolerance*100:.2f}% price tolerance, "
                   f"{cache_duration_hours}h retention")
    
    def generate_signal_hash(self, symbol: str, direction: str, price: float) -> str:
        """
        Generate a hash for a signal based on symbol, direction, and price range
        
        Args:
            symbol: Trading symbol
            direction: Signal direction (LONG/SHORT/BUY/SELL)
            price: Entry price
            
        Returns:
            Hash string for the signal
        """
        # Normalize direction
        direction_normalized = direction.upper()
        if direction_normalized in ['BUY', 'LONG']:
            direction_normalized = 'LONG'
        elif direction_normalized in ['SELL', 'SHORT']:
            direction_normalized = 'SHORT'
        
        # Calculate price range based on tolerance
        price_range_lower = price * (1 - self.price_tolerance)
        price_range_upper = price * (1 + self.price_tolerance)
        
        # Round to 4 decimal places for consistency
        price_range_lower = round(price_range_lower, 4)
        price_range_upper = round(price_range_upper, 4)
        
        # Create hash key
        hash_key = f"{symbol}:{direction_normalized}:{price_range_lower:.4f}-{price_range_upper:.4f}"
        
        # Generate MD5 hash for compactness
        hash_value = hashlib.md5(hash_key.encode()).hexdigest()[:16]
        
        return hash_value
    
    def is_duplicate(self, signal_data: Dict[str, Any]) -> bool:
        """
        Check if a signal is a duplicate of a recently sent signal
        
        Args:
            signal_data: Dictionary containing signal information
                - symbol: Trading symbol
                - direction or signal_type: Signal direction
                - entry_price: Entry price
                
        Returns:
            True if signal is a duplicate, False otherwise
        """
        # Extract signal components
        symbol = signal_data.get('symbol', '')
        direction = signal_data.get('direction') or signal_data.get('signal_type', '')
        entry_price = signal_data.get('entry_price', 0.0)
        
        if not symbol or not direction or entry_price == 0:
            logger.warning(f"Invalid signal data for duplicate check: {signal_data}")
            return False
        
        # Generate hash for current signal
        signal_hash = self.generate_signal_hash(symbol, direction, entry_price)
        
        # Clean old signals first
        self.clear_old_signals()
        
        # Check if hash exists in cache
        if signal_hash in self.cache:
            cached_signal = self.cache[signal_hash]
            logger.info(f"Duplicate signal detected: {symbol} {direction} @ {entry_price:.4f} "
                       f"(original sent {cached_signal['timestamp']})")
            self.duplicate_count += 1
            return True
        
        # Also check for similar signals within price tolerance
        for hash_key, cached_signal in self.cache.items():
            if cached_signal['symbol'] == symbol:
                # Normalize directions for comparison
                cached_dir = cached_signal['direction'].upper()
                current_dir = direction.upper()
                
                if cached_dir in ['BUY', 'LONG']:
                    cached_dir = 'LONG'
                elif cached_dir in ['SELL', 'SHORT']:
                    cached_dir = 'SHORT'
                    
                if current_dir in ['BUY', 'LONG']:
                    current_dir = 'LONG'
                elif current_dir in ['SELL', 'SHORT']:
                    current_dir = 'SHORT'
                
                if cached_dir == current_dir:
                    # Check if prices are within tolerance
                    cached_price = cached_signal['entry_price']
                    price_diff_ratio = abs(entry_price - cached_price) / cached_price
                    
                    if price_diff_ratio <= self.price_tolerance:
                        logger.info(f"Similar signal detected: {symbol} {direction} @ {entry_price:.4f} "
                                   f"(matches cached {cached_price:.4f}, diff {price_diff_ratio*100:.2f}%)")
                        self.duplicate_count += 1
                        return True
        
        return False
    
    def add_signal(self, signal_data: Dict[str, Any]):
        """
        Add a signal to the cache after it has been sent
        
        Args:
            signal_data: Dictionary containing signal information
        """
        # Extract signal components
        symbol = signal_data.get('symbol', '')
        direction = signal_data.get('direction') or signal_data.get('signal_type', '')
        entry_price = signal_data.get('entry_price', 0.0)
        
        if not symbol or not direction or entry_price == 0:
            logger.warning(f"Invalid signal data for caching: {signal_data}")
            return
        
        # Generate hash
        signal_hash = self.generate_signal_hash(symbol, direction, entry_price)
        
        # Store in cache with timestamp
        self.cache[signal_hash] = {
            'symbol': symbol,
            'direction': direction,
            'entry_price': entry_price,
            'timestamp': datetime.now().isoformat(),
            'full_data': signal_data
        }
        
        self.signal_count += 1
        logger.info(f"Signal cached: {symbol} {direction} @ {entry_price:.4f} (hash: {signal_hash})")
    
    def clear_old_signals(self):
        """
        Remove signals older than cache_duration_hours from the cache
        """
        if not self.cache:
            return
        
        current_time = datetime.now()
        cutoff_time = current_time - timedelta(hours=self.cache_duration_hours)
        
        # Find signals to remove
        hashes_to_remove = []
        for hash_key, signal_info in self.cache.items():
            signal_time = datetime.fromisoformat(signal_info['timestamp'])
            if signal_time < cutoff_time:
                hashes_to_remove.append(hash_key)
        
        # Remove old signals
        for hash_key in hashes_to_remove:
            removed_signal = self.cache.pop(hash_key)
            logger.debug(f"Removed old signal from cache: {removed_signal['symbol']} "
                        f"{removed_signal['direction']} @ {removed_signal['entry_price']:.4f} "
                        f"(sent {removed_signal['timestamp']})")
        
        if hashes_to_remove:
            logger.info(f"Cleared {len(hashes_to_remove)} old signals from cache")
    
    def clear_cache(self):
        """
        Clear all signals from the cache
        """
        signal_count = len(self.cache)
        self.cache.clear()
        logger.info(f"Cache cleared: removed {signal_count} signals")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the cache
        
        Returns:
            Dictionary with cache statistics
        """
        self.clear_old_signals()
        
        stats = {
            'cached_signals': len(self.cache),
            'total_signals_processed': self.signal_count,
            'duplicates_prevented': self.duplicate_count,
            'duplicate_rate': (self.duplicate_count / self.signal_count * 100) if self.signal_count > 0 else 0,
            'price_tolerance': self.price_tolerance,
            'cache_duration_hours': self.cache_duration_hours,
            'signals_by_symbol': {}
        }
        
        # Count signals by symbol
        for signal_info in self.cache.values():
            symbol = signal_info['symbol']
            stats['signals_by_symbol'][symbol] = stats['signals_by_symbol'].get(symbol, 0) + 1
        
        return stats
    
    def get_cached_signals(self) -> list:
        """
        Get list of all cached signals
        
        Returns:
            List of cached signal information
        """
        self.clear_old_signals()
        
        signals = []
        for hash_key, signal_info in self.cache.items():
            signals.append({
                'hash': hash_key,
                'symbol': signal_info['symbol'],
                'direction': signal_info['direction'],
                'entry_price': signal_info['entry_price'],
                'timestamp': signal_info['timestamp']
            })
        
        # Sort by timestamp (newest first)
        signals.sort(key=lambda x: x['timestamp'], reverse=True)
        
        return signals
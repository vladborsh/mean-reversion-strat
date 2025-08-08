#!/usr/bin/env python3
"""
Persistent Signal Cache Module

This module provides a DynamoDB-backed caching mechanism to prevent duplicate trading signal notifications.
It tracks sent signals persistently and can identify duplicates based on symbol, direction, and price range.
"""

import hashlib
import time
import logging
import os
from typing import Dict, Any, Optional, Set, List
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from boto3.dynamodb.conditions import Key, Attr
from botocore.exceptions import ClientError

from .dynamodb_base import DynamoDBBase

logger = logging.getLogger(__name__)


class PersistentSignalCache(DynamoDBBase):
    """
    DynamoDB-backed cache for tracking sent trading signals to prevent duplicate notifications
    """
    
    def __init__(self, price_tolerance: float = 0.0005, 
                 cache_duration_hours: int = 24,
                 table_name: str = None, 
                 region_name: str = None):
        """
        Initialize the persistent signal cache
        
        Args:
            price_tolerance: Price tolerance for considering signals as duplicates (default 0.05%)
            cache_duration_hours: How long to keep signals in cache (default 24 hours)
            table_name: DynamoDB table name (defaults to env var SIGNALS_CACHE_TABLE)
            region_name: AWS region (defaults to env var AWS_REGION or us-east-1)
        """
        # Set table name
        table_name = table_name or os.getenv('SIGNALS_CACHE_TABLE', 'trading-signals-cache')
        
        # Initialize base class
        super().__init__(table_name=table_name, region_name=region_name)
        
        # Cache parameters
        self.price_tolerance = price_tolerance
        self.cache_duration_hours = cache_duration_hours
        
        # Statistics (local)
        self.signal_count = 0
        self.duplicate_count = 0
        
        # Create table if it doesn't exist
        self._ensure_table_exists()
        
        # Load existing signals on startup
        self.local_cache = self._load_active_signals()
        
        logger.info(f"Persistent signal cache initialized with {price_tolerance*100:.2f}% price tolerance, "
                   f"{cache_duration_hours}h retention, {len(self.local_cache)} signals loaded from DynamoDB")
    
    def _ensure_table_exists(self):
        """Ensure the DynamoDB table exists with proper configuration"""
        if not self.table_exists():
            logger.info(f"Creating DynamoDB table: {self.table_name}")
            
            # Create table with TTL
            self.create_table(
                table_name=self.table_name,
                key_schema=[
                    {
                        'AttributeName': 'signal_hash',
                        'KeyType': 'HASH'  # Partition key
                    }
                ],
                attribute_definitions=[
                    {
                        'AttributeName': 'signal_hash',
                        'AttributeType': 'S'  # String type for hash
                    }
                ],
                ttl_attribute='expiry_time',  # Enable TTL for automatic cleanup
                billing_mode='PAY_PER_REQUEST'
            )
        else:
            # Ensure TTL is enabled on existing table
            self.enable_ttl(self.table_name, 'expiry_time')
    
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
    
    def _load_active_signals(self) -> Dict[str, Dict[str, Any]]:
        """
        Load active signals from DynamoDB into local cache
        
        Returns:
            Dictionary of active signals
        """
        local_cache = {}
        current_time = int(datetime.now(timezone.utc).timestamp())
        
        try:
            # Scan for non-expired signals
            items = self.scan_with_filter(
                filter_expression=Attr('expiry_time').gt(current_time)
            )
            
            for item in items:
                # Convert DynamoDB types
                item = self.convert_decimal_to_number(item)
                signal_hash = item.get('signal_hash')
                if signal_hash:
                    local_cache[signal_hash] = item
                    logger.debug(f"Loaded signal from DynamoDB: {item.get('symbol')} "
                               f"{item.get('direction')} @ {item.get('entry_price')}")
            
            logger.info(f"Loaded {len(local_cache)} active signals from DynamoDB")
            return local_cache
            
        except Exception as e:
            logger.error(f"Failed to load signals from DynamoDB: {e}")
            return {}
    
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
        
        # Check local cache first
        if signal_hash in self.local_cache:
            cached_signal = self.local_cache[signal_hash]
            logger.info(f"Duplicate signal detected in local cache: {symbol} {direction} @ {entry_price:.4f} "
                       f"(original sent {cached_signal.get('timestamp', 'unknown')})")
            self.duplicate_count += 1
            return True
        
        # Also check for similar signals within price tolerance
        for hash_key, cached_signal in self.local_cache.items():
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
                    cached_price = float(cached_signal['entry_price'])
                    price_diff_ratio = abs(entry_price - cached_price) / cached_price
                    
                    if price_diff_ratio <= self.price_tolerance:
                        logger.info(f"Similar signal detected: {symbol} {direction} @ {entry_price:.4f} "
                                   f"(matches cached {cached_price:.4f}, diff {price_diff_ratio*100:.2f}%)")
                        self.duplicate_count += 1
                        return True
        
        # Check DynamoDB in case another instance added it
        try:
            db_item = self.get_item({'signal_hash': signal_hash})
            if db_item:
                # Check if not expired
                current_time = int(datetime.now(timezone.utc).timestamp())
                if db_item.get('expiry_time', 0) > current_time:
                    # Add to local cache
                    self.local_cache[signal_hash] = self.convert_decimal_to_number(db_item)
                    logger.info(f"Duplicate signal detected in DynamoDB: {symbol} {direction} @ {entry_price:.4f} "
                               f"(original sent {db_item.get('timestamp', 'unknown')})")
                    self.duplicate_count += 1
                    return True
        except Exception as e:
            logger.error(f"Failed to check DynamoDB for duplicate: {e}")
        
        logger.debug(f"No duplicate found for signal: {symbol} {direction} @ {entry_price:.4f} (hash: {signal_hash})")
        return False
    
    def _convert_to_dynamodb_types(self, obj: Any) -> Any:
        """
        Recursively convert float types to Decimal for DynamoDB compatibility
        
        Args:
            obj: Object to convert
            
        Returns:
            Converted object with Decimal types
        """
        if isinstance(obj, float):
            return Decimal(str(obj))
        elif isinstance(obj, dict):
            return {k: self._convert_to_dynamodb_types(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._convert_to_dynamodb_types(item) for item in obj]
        else:
            return obj
    
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
        
        # Calculate expiry time (Unix timestamp for TTL)
        expiry_time = int((datetime.now(timezone.utc) + 
                          timedelta(hours=self.cache_duration_hours)).timestamp())
        
        # Convert signal_data to DynamoDB-compatible types
        full_data_converted = self._convert_to_dynamodb_types(signal_data)
        
        # Prepare item for DynamoDB
        item = {
            'signal_hash': signal_hash,
            'symbol': symbol,
            'direction': direction,
            'entry_price': Decimal(str(entry_price)),  # Convert to Decimal for DynamoDB
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'expiry_time': expiry_time,  # TTL attribute
            'full_data': full_data_converted
        }
        
        # Store in DynamoDB
        try:
            if self.put_item(item):
                # Update local cache with converted back data
                self.local_cache[signal_hash] = self.convert_decimal_to_number(item)
                self.signal_count += 1
                logger.info(f"Signal cached to DynamoDB: {symbol} {direction} @ {entry_price:.4f} "
                           f"(hash: {signal_hash}, expires: {datetime.fromtimestamp(expiry_time, tz=timezone.utc)})")
                return True
            else:
                logger.error(f"Failed to cache signal to DynamoDB: {symbol} {direction} @ {entry_price:.4f}")
                return False
        except Exception as e:
            logger.error(f"Error caching signal: {e}")
            return False
    
    def clear_expired_signals(self):
        """
        Clear expired signals from local cache
        Note: DynamoDB TTL handles automatic deletion from the database
        """
        current_time = int(datetime.now(timezone.utc).timestamp())
        
        # Find expired signals in local cache
        expired_hashes = []
        for hash_key, signal_info in self.local_cache.items():
            if signal_info.get('expiry_time', 0) <= current_time:
                expired_hashes.append(hash_key)
        
        # Remove expired signals from local cache
        for hash_key in expired_hashes:
            removed_signal = self.local_cache.pop(hash_key)
            logger.debug(f"Removed expired signal from local cache: {removed_signal['symbol']} "
                        f"{removed_signal['direction']} @ {removed_signal['entry_price']:.4f}")
        
        if expired_hashes:
            logger.info(f"Cleared {len(expired_hashes)} expired signals from local cache")
    
    def clear_cache(self):
        """
        Clear all signals from both local and DynamoDB cache
        """
        # Clear local cache
        local_count = len(self.local_cache)
        self.local_cache.clear()
        
        # Clear DynamoDB cache
        try:
            items = self.scan_with_filter(projection_expression='signal_hash')
            for item in items:
                self.delete_item({'signal_hash': item['signal_hash']})
            
            logger.info(f"Cache cleared: removed {local_count} local and {len(items)} DynamoDB signals")
        except Exception as e:
            logger.error(f"Failed to clear DynamoDB cache: {e}")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the cache
        
        Returns:
            Dictionary with cache statistics
        """
        self.clear_expired_signals()
        
        # Get DynamoDB stats
        db_count = 0
        try:
            current_time = int(datetime.now(timezone.utc).timestamp())
            items = self.scan_with_filter(
                filter_expression=Attr('expiry_time').gt(current_time),
                projection_expression='symbol, direction'
            )
            db_count = len(items)
        except Exception as e:
            logger.error(f"Failed to get DynamoDB stats: {e}")
        
        stats = {
            'cached_signals_local': len(self.local_cache),
            'cached_signals_dynamodb': db_count,
            'total_signals_processed': self.signal_count,
            'duplicates_prevented': self.duplicate_count,
            'duplicate_rate': (self.duplicate_count / self.signal_count * 100) if self.signal_count > 0 else 0,
            'price_tolerance': self.price_tolerance,
            'cache_duration_hours': self.cache_duration_hours,
            'signals_by_symbol': {}
        }
        
        # Count signals by symbol from local cache
        for signal_info in self.local_cache.values():
            symbol = signal_info['symbol']
            stats['signals_by_symbol'][symbol] = stats['signals_by_symbol'].get(symbol, 0) + 1
        
        return stats
    
    def get_cached_signals(self) -> List[Dict[str, Any]]:
        """
        Get list of all cached signals from DynamoDB
        
        Returns:
            List of cached signal information
        """
        signals = []
        
        try:
            current_time = int(datetime.now(timezone.utc).timestamp())
            items = self.scan_with_filter(
                filter_expression=Attr('expiry_time').gt(current_time)
            )
            
            for item in items:
                item = self.convert_decimal_to_number(item)
                signals.append({
                    'hash': item.get('signal_hash'),
                    'symbol': item.get('symbol'),
                    'direction': item.get('direction'),
                    'entry_price': item.get('entry_price'),
                    'timestamp': item.get('timestamp'),
                    'expiry_time': datetime.fromtimestamp(
                        item.get('expiry_time', 0), 
                        tz=timezone.utc
                    ).isoformat()
                })
            
            # Sort by timestamp (newest first)
            signals.sort(key=lambda x: x['timestamp'], reverse=True)
            
        except Exception as e:
            logger.error(f"Failed to get cached signals from DynamoDB: {e}")
        
        return signals
    
    def sync_local_cache(self):
        """
        Sync local cache with DynamoDB (useful after network issues)
        """
        try:
            self.local_cache = self._load_active_signals()
            logger.info(f"Local cache synced with DynamoDB: {len(self.local_cache)} signals")
        except Exception as e:
            logger.error(f"Failed to sync local cache: {e}")
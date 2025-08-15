"""
Data caching module for storing and retrieving fetched market data.
Provides persistent caching with support for local filesystem and cloud storage (S3).
"""

import os
import pickle
import hashlib
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path
import logging

from .transport_factory import create_cache_transport
from .transport import TransportInterface

logger = logging.getLogger(__name__)

class DataCache:
    """
    Unified cache for market data with support for multiple storage backends.
    
    Features:
    - Persistent storage between runs (local or S3)
    - Intelligent cache invalidation based on data age and market hours
    - Configurable transport layer (local filesystem or S3)
    - Thread-safe operations
    """
    
    def __init__(self, cache_dir=None, max_age_hours=24, transport: TransportInterface = None):
        """
        Initialize the data cache.
        
        Args:
            cache_dir (str, optional): Directory for local transport. Ignored if transport provided.
            max_age_hours (int): Maximum age of cached data in hours before expiration.
            transport (TransportInterface, optional): Custom transport layer
        """
        self.max_age_hours = max_age_hours
        
        if transport:
            self.transport = transport
        else:
            self.transport = create_cache_transport(cache_dir)
        
        logger.info(f"DataCache initialized with {type(self.transport).__name__}")
    
    
    def _generate_cache_key(self, source, symbol, timeframe, years, additional_params=None):
        """
        Generate a unique cache key based on data request parameters.
        
        Args:
            source (str): Data source (forex, crypto, indices)
            symbol (str): Trading symbol (e.g., 'EURUSD')
            timeframe (str): Data timeframe (e.g., '15m', '1h', '4h', '1d')
            years (int): Number of years of data requested
            additional_params (dict, optional): Additional parameters that affect data
            
        Returns:
            str: Unique cache key for this data request
        """
        # Create a string representation of all parameters
        key_data = f"{source}_{symbol}_{timeframe}_{years}"
        
        if additional_params:
            # Sort additional params for consistent key generation
            sorted_params = sorted(additional_params.items())
            params_str = "_".join([f"{k}={v}" for k, v in sorted_params])
            key_data += f"_{params_str}"
        
        # Use MD5 hash to create a shorter, consistent key
        cache_key = hashlib.md5(key_data.encode()).hexdigest()
        return f"{cache_key}.pkl"
    
    def _is_cache_valid(self, cache_key, timeframe, metadata):
        """
        Check if cached data is still valid based on age and market context.
        
        Args:
            cache_key (str): Cache key to check
            timeframe (str): Data timeframe to determine appropriate cache duration
            metadata (dict): Cache metadata containing timestamp info
            
        Returns:
            bool: True if cache is valid, False if expired
        """
        if not metadata or 'cached_at' not in metadata:
            return False
        
        try:
            # Parse cached timestamp
            cached_time = datetime.fromisoformat(metadata['cached_at'])
            current_time = datetime.now()
            age_hours = (current_time - cached_time).total_seconds() / 3600
            
            # Determine cache validity based on timeframe
            max_age = self._get_cache_expiry_hours(timeframe)
            
            is_valid = age_hours < max_age
            
            if not is_valid:
                logger.info(f"Cache expired: age={age_hours:.1f}h, max_age={max_age}h")
            else:
                logger.info(f"Cache valid: age={age_hours:.1f}h, max_age={max_age}h")
                
            return is_valid
        except Exception as e:
            logger.error(f"Error validating cache: {e}")
            return False
    
    def _get_cache_expiry_hours(self, timeframe):
        """
        Get appropriate cache expiry time based on data timeframe.
        
        Args:
            timeframe (str): Data timeframe
            
        Returns:
            int: Cache expiry time in hours
        """
        # More frequent data should expire faster
        expiry_map = {
            '15m': 2,   # 15-minute data expires after 2 hours
            '1h': 6,    # Hourly data expires after 6 hours  
            '4h': 12,   # 4-hour data expires after 12 hours
            '1d': 24,   # Daily data expires after 24 hours
        }
        
        return expiry_map.get(timeframe, self.max_age_hours)
    
    def get(self, source, symbol, timeframe, years, additional_params=None):
        """
        Retrieve cached data if available and valid.
        
        Args:
            source (str): Data source
            symbol (str): Trading symbol
            timeframe (str): Data timeframe
            years (int): Number of years of data
            additional_params (dict, optional): Additional parameters
            
        Returns:
            pandas.DataFrame or None: Cached data if available and valid, None otherwise
        """
        cache_key = self._generate_cache_key(source, symbol, timeframe, years, additional_params)
        
        logger.info(f"Checking cache for key: {cache_key}")
        
        if not self.transport.exists(cache_key):
            logger.debug(f"Cache miss: {cache_key} not found")
            return None
        
        try:
            cache_data = self.transport.load_pickle(cache_key)
            
            if cache_data is None:
                logger.debug(f"Cache miss: failed to load {cache_key}")
                return None
                
            # Validate cached data structure
            if not isinstance(cache_data, dict) or 'data' not in cache_data:
                logger.warning(f"Invalid cache data structure in {cache_key}")
                self.transport.delete(cache_key)  # Remove corrupted cache
                return None
            
            data = cache_data['data']
            metadata = cache_data.get('metadata', {})
            
            # Validate that cached data is a DataFrame
            if not isinstance(data, pd.DataFrame):
                logger.warning(f"Cached data is not a DataFrame in {cache_key}")
                self.transport.delete(cache_key)  # Remove corrupted cache
                return None
            
            # Check if cache is still valid
            if not self._is_cache_valid(cache_key, timeframe, metadata):
                self.transport.delete(cache_key)  # Remove expired cache
                return None
            
            logger.info(f"Cache hit! Loaded {len(data)} rows from cache")
            logger.info(f"Cache metadata: {metadata}")
            
            return data
            
        except Exception as e:
            logger.error(f"Error loading cache {cache_key}: {e}")
            # Remove corrupted cache file
            try:
                self.transport.delete(cache_key)
                logger.info(f"Removed corrupted cache: {cache_key}")
            except:
                pass
            return None
    
    def set(self, source, symbol, timeframe, years, data, additional_params=None, metadata=None):
        """
        Store data in cache.
        
        Args:
            source (str): Data source
            symbol (str): Trading symbol
            timeframe (str): Data timeframe
            years (int): Number of years of data
            data (pandas.DataFrame): Data to cache
            additional_params (dict, optional): Additional parameters
            metadata (dict, optional): Additional metadata to store with the data
        """
        if data is None or data.empty:
            logger.warning("Attempted to cache empty data - skipping")
            return
        
        cache_key = self._generate_cache_key(source, symbol, timeframe, years, additional_params)
        
        # Prepare cache data with metadata
        cache_data = {
            'data': data,
            'metadata': {
                'source': source,
                'symbol': symbol,
                'timeframe': timeframe,
                'years': years,
                'cached_at': datetime.now().isoformat(),
                'rows': len(data),
                'start_date': data.index[0].isoformat() if not data.empty else None,
                'end_date': data.index[-1].isoformat() if not data.empty else None,
                **(metadata or {})
            }
        }
        
        if self.transport.save_pickle(cache_key, cache_data):
            logger.info(f"Cached {len(data)} rows to {cache_key}")
        else:
            logger.error(f"Failed to cache data to {cache_key}")
    
    def clear(self, max_age_days=30):
        """
        Clear old cache files.
        
        Args:
            max_age_days (int): Remove cache files older than this many days
            
        Returns:
            int: Number of files removed
        """
        removed_count = self.transport.cleanup(max_age_days)
        logger.info(f"Cache cleanup completed. Removed {removed_count} old files.")
        return removed_count
    
    def get_cache_info(self):
        """
        Get information about current cache contents.
        
        Returns:
            dict: Cache statistics and information
        """
        return self.transport.get_info()


# Global cache instance
_global_cache = None

def get_global_cache(transport_type='local'):
    """Get or create the global cache instance with specified transport type."""
    global _global_cache
    if _global_cache is None:
        from .transport_factory import create_cache_transport
        transport = create_cache_transport(transport_type=transport_type)
        _global_cache = DataCache(transport=transport)
    return _global_cache

def clear_global_cache():
    """Clear the global cache."""
    global _global_cache
    if _global_cache is not None:
        _global_cache.clear()

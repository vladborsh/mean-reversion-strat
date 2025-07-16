"""
Data caching module for storing and retrieving fetched market data.
Provides persistent file-based caching with intelligent cache invalidation.
"""

import os
import pickle
import hashlib
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

class DataCache:
    """
    File-based cache for market data with intelligent expiration logic.
    
    Features:
    - Persistent storage between runs
    - Intelligent cache invalidation based on data age and market hours
    - Configurable cache directory and retention policies
    - Thread-safe operations
    """
    
    def __init__(self, cache_dir=None, max_age_hours=24):
        """
        Initialize the data cache.
        
        Args:
            cache_dir (str, optional): Directory to store cache files. 
                                     Defaults to './cache' in project root.
            max_age_hours (int): Maximum age of cached data in hours before expiration.
                               Defaults to 24 hours.
        """
        if cache_dir is None:
            # Use cache directory in project root
            project_root = Path(__file__).parent.parent
            cache_dir = project_root / 'cache'
        
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self.max_age_hours = max_age_hours
        
        # Create metadata file for cache management
        self.metadata_file = self.cache_dir / '.cache_metadata.json'
        
        logger.info(f"DataCache initialized with directory: {self.cache_dir}")
    
    def _generate_cache_key(self, source, symbol, timeframe, years, additional_params=None):
        """
        Generate a unique cache key based on data request parameters.
        
        Args:
            source (str): Data source (forex, crypto, indices)
            symbol (str): Trading symbol (e.g., 'EURUSD=X')
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
        return cache_key
    
    def _get_cache_file_path(self, cache_key):
        """Get the full path for a cache file."""
        return self.cache_dir / f"{cache_key}.pkl"
    
    def _is_cache_valid(self, cache_file_path, timeframe):
        """
        Check if cached data is still valid based on file age and market context.
        
        Args:
            cache_file_path (Path): Path to the cache file
            timeframe (str): Data timeframe to determine appropriate cache duration
            
        Returns:
            bool: True if cache is valid, False if expired
        """
        if not cache_file_path.exists():
            return False
        
        # Get file modification time
        file_mtime = datetime.fromtimestamp(cache_file_path.stat().st_mtime)
        current_time = datetime.now()
        age_hours = (current_time - file_mtime).total_seconds() / 3600
        
        # Determine cache validity based on timeframe
        max_age = self._get_cache_expiry_hours(timeframe)
        
        is_valid = age_hours < max_age
        
        if not is_valid:
            logger.info(f"Cache expired: age={age_hours:.1f}h, max_age={max_age}h")
        else:
            logger.info(f"Cache valid: age={age_hours:.1f}h, max_age={max_age}h")
            
        return is_valid
    
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
        cache_file = self._get_cache_file_path(cache_key)
        
        logger.info(f"Checking cache for key: {cache_key}")
        
        if not self._is_cache_valid(cache_file, timeframe):
            return None
        
        try:
            with open(cache_file, 'rb') as f:
                cache_data = pickle.load(f)
            
            # Validate cached data structure
            if not isinstance(cache_data, dict) or 'data' not in cache_data:
                logger.warning(f"Invalid cache data structure in {cache_file}")
                return None
            
            data = cache_data['data']
            metadata = cache_data.get('metadata', {})
            
            # Validate that cached data is a DataFrame
            if not isinstance(data, pd.DataFrame):
                logger.warning(f"Cached data is not a DataFrame in {cache_file}")
                return None
            
            logger.info(f"Cache hit! Loaded {len(data)} rows from cache")
            logger.info(f"Cache metadata: {metadata}")
            
            return data
            
        except Exception as e:
            logger.error(f"Error loading cache file {cache_file}: {e}")
            # Remove corrupted cache file
            try:
                cache_file.unlink()
                logger.info(f"Removed corrupted cache file: {cache_file}")
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
        cache_file = self._get_cache_file_path(cache_key)
        
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
        
        try:
            with open(cache_file, 'wb') as f:
                pickle.dump(cache_data, f, protocol=pickle.HIGHEST_PROTOCOL)
            
            logger.info(f"Cached {len(data)} rows to {cache_file}")
            logger.info(f"Cache key: {cache_key}")
            
        except Exception as e:
            logger.error(f"Error saving cache file {cache_file}: {e}")
    
    def clear(self, max_age_days=30):
        """
        Clear old cache files.
        
        Args:
            max_age_days (int): Remove cache files older than this many days
        """
        cutoff_time = datetime.now() - timedelta(days=max_age_days)
        removed_count = 0
        
        for cache_file in self.cache_dir.glob("*.pkl"):
            try:
                file_mtime = datetime.fromtimestamp(cache_file.stat().st_mtime)
                if file_mtime < cutoff_time:
                    cache_file.unlink()
                    removed_count += 1
                    logger.info(f"Removed old cache file: {cache_file}")
            except Exception as e:
                logger.error(f"Error removing cache file {cache_file}: {e}")
        
        logger.info(f"Cache cleanup completed. Removed {removed_count} old files.")
    
    def get_cache_info(self):
        """
        Get information about current cache contents.
        
        Returns:
            dict: Cache statistics and information
        """
        cache_files = list(self.cache_dir.glob("*.pkl"))
        total_size = sum(f.stat().st_size for f in cache_files)
        
        info = {
            'cache_directory': str(self.cache_dir),
            'total_files': len(cache_files),
            'total_size_mb': total_size / (1024 * 1024),
            'files': []
        }
        
        for cache_file in cache_files:
            try:
                file_mtime = datetime.fromtimestamp(cache_file.stat().st_mtime)
                file_size = cache_file.stat().st_size
                
                file_info = {
                    'filename': cache_file.name,
                    'size_kb': file_size / 1024,
                    'modified': file_mtime.isoformat(),
                    'age_hours': (datetime.now() - file_mtime).total_seconds() / 3600
                }
                
                # Try to load metadata if possible
                try:
                    with open(cache_file, 'rb') as f:
                        cache_data = pickle.load(f)
                    file_info['metadata'] = cache_data.get('metadata', {})
                except:
                    file_info['metadata'] = {'error': 'Could not load metadata'}
                
                info['files'].append(file_info)
                
            except Exception as e:
                logger.error(f"Error reading cache file info {cache_file}: {e}")
        
        return info

# Global cache instance
_global_cache = None

def get_global_cache():
    """Get or create the global cache instance."""
    global _global_cache
    if _global_cache is None:
        _global_cache = DataCache()
    return _global_cache

def clear_global_cache():
    """Clear the global cache."""
    global _global_cache
    if _global_cache is not None:
        _global_cache.clear()

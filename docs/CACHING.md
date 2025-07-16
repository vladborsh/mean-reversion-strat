# Data Caching Documentation

## Overview

The Mean Reversion Strategy project includes an intelligent data caching system that automatically stores fetched market data to improve performance and reduce API calls.

## Key Benefits

- **Performance**: 5-20x faster data loading on subsequent requests
- **API Rate Limiting**: Reduces external API calls
- **Persistent Storage**: Cache survives between script runs
- **Intelligent Expiry**: Automatic cache invalidation based on data freshness requirements

## How It Works

### Automatic Caching
```python
from src.data_fetcher import DataFetcher

# Caching is enabled by default
fetcher = DataFetcher(source='forex', symbol='EURUSD=X', timeframe='1h')
data = fetcher.fetch(years=1)  # First call: fetches from API + caches
data = fetcher.fetch(years=1)  # Second call: loads from cache (much faster)
```

### Cache Key Generation
Cache keys are generated based on:
- Data source (forex, crypto, indices)
- Symbol (EURUSD=X, BTC/USDT, etc.)
- Timeframe (15m, 1h, 4h, 1d)
- Time period (years)
- Additional parameters (exchange for crypto)

### Cache Expiration Policy
| Timeframe | Cache Expires After |
|-----------|-------------------|
| 15-minute | 2 hours |
| 1-hour | 6 hours |
| 4-hour | 12 hours |
| Daily | 24 hours |

## Usage Examples

### Basic Usage with Caching
```python
# Default: caching enabled
fetcher = DataFetcher(source='forex', symbol='EURUSD=X', timeframe='1h', use_cache=True)
data = fetcher.fetch(years=2)
```

### Disable Caching
```python
# Disable caching for always-fresh data
fetcher = DataFetcher(source='forex', symbol='EURUSD=X', timeframe='1h', use_cache=False)
data = fetcher.fetch(years=2)
```

### Check Cache Status
```python
# Get cache information
cache_info = fetcher.get_cache_info()
print(f"Cached files: {cache_info['total_files']}")
print(f"Cache size: {cache_info['total_size_mb']:.2f} MB")
```

## Cache Management

### Command Line Tools

#### View Cache Information
```bash
python cache_manager.py info
```

#### Clear Old Cache Files
```bash
# Remove files older than 7 days
python cache_manager.py clear --max-age-days 7

# Clear all cache files
python cache_manager.py clear
```

#### Performance Test
```bash
python cache_manager.py test
```

#### Invalidate Specific Symbol
```bash
python cache_manager.py invalidate
```

### Programmatic Cache Management

#### Clear Cache for Specific Symbol
```python
fetcher = DataFetcher(source='forex', symbol='EURUSD=X', timeframe='1h')
fetcher.invalidate_cache_for_symbol(years=1)  # Clear specific period
fetcher.invalidate_cache_for_symbol()         # Clear all periods
```

#### Global Cache Operations
```python
from src.data_fetcher import DataFetcher

# Get global cache info
info = DataFetcher.get_global_cache_info()

# Clear old files globally
DataFetcher.clear_global_cache(max_age_days=30)
```

## Performance Comparison

### Without Cache
```bash
🔄 Fetching EUR/USD 1h data (1 year)...
✅ Completed in 15.3 seconds
```

### With Cache (subsequent runs)
```bash
📦 Cache hit! Using cached data
✅ Completed in 0.8 seconds (19x faster!)
```

## Cache File Structure

```
cache/
├── .cache_metadata.json
├── a1b2c3d4e5f6.pkl      # EURUSD=X 1h 1yr
├── f6e5d4c3b2a1.pkl      # BTCUSDT 15m 1yr
└── 9z8y7x6w5v4u.pkl      # GBPUSD=X 4h 2yr
```

Each cache file contains:
- Market data (OHLCV pandas DataFrame)
- Metadata (symbol, timeframe, fetch timestamp, provider used)
- Data validity information

## Configuration

### Default Settings
- **Cache Directory**: `./cache/` (project root)
- **File Format**: Compressed pickle files
- **Naming**: MD5 hash of parameters
- **Auto-cleanup**: Files older than 30 days (manual)

### Custom Cache Directory
```python
from src.data_cache import DataCache

# Custom cache location
cache = DataCache(cache_dir='/custom/path/cache')
```

## Best Practices

1. **Enable caching for development**: Speeds up repeated testing
2. **Clear cache periodically**: Prevent disk space issues
3. **Disable for production**: If you need real-time data
4. **Monitor cache size**: Use `cache_manager.py info` regularly

## Technical Details

- **Storage Format**: Python pickle with highest protocol
- **Thread Safety**: File-based operations are atomic
- **Error Handling**: Corrupted cache files are automatically removed
- **Memory Efficient**: Data loaded only when needed

## Troubleshooting

### Cache Not Working
```python
# Check if cache is enabled
fetcher = DataFetcher(source='forex', symbol='EURUSD=X', timeframe='1h')
print(f"Cache enabled: {fetcher.use_cache}")
print(f"Cache object: {fetcher.cache is not None}")
```

### Clear Corrupted Cache
```bash
# Remove all cache files and start fresh
python cache_manager.py clear
```

### Debug Cache Behavior
```python
# Enable debug logging
import logging
logging.basicConfig(level=logging.INFO)

# Cache operations will now show detailed logs
fetcher = DataFetcher(source='forex', symbol='EURUSD=X', timeframe='1h')
data = fetcher.fetch(years=1)
```

## Integration Notes

- Cache integrates seamlessly with existing `DataFetcher` workflow
- No changes required to existing strategy code
- Cache files are automatically excluded from version control (`.gitignore`)
- Works with all data sources: forex, crypto, indices
- Compatible with all timeframes and providers

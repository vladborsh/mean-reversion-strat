# Data Fetching Guide

## Overview

The Mean Reversion Strategy project provides a powerful and flexible data fetching system that supports multiple data providers, intelligent caching, and now includes **flexible date range specification** for precise historical data retrieval.

## Key Features

- **Multiple Data Sources**: Forex (Capital.com), Crypto (CCXT/Binance), Indices
- **Flexible Date Specification**: Years-based or precise date ranges
- **Intelligent Caching**: Automatic caching with date-aware keys
- **Provider Fallback**: Automatic fallback to alternative providers
- **Trading Hours Validation**: Automatic adjustment for market hours (forex/indices)

## Date Range Fetching (NEW)

### Parameter Options

The `fetch()` method now supports multiple ways to specify the time period:

```python
from src.data_fetcher import DataFetcher
from datetime import datetime, timedelta

fetcher = DataFetcher(source='forex', symbol='EURUSD', timeframe='1h')

# Option 1: Years (backward compatible)
data = fetcher.fetch(years=2)  # Get 2 years of data from now

# Option 2: Date range with strings
data = fetcher.fetch(
    start_date='2024-01-01',
    end_date='2024-12-31'
)

# Option 3: Date range with datetime objects
data = fetcher.fetch(
    start_date=datetime(2024, 1, 1, 9, 30),
    end_date=datetime(2024, 6, 30, 16, 0)
)

# Option 4: Start date only (end defaults to current time)
data = fetcher.fetch(start_date='2024-06-01')

# Option 5: No parameters (defaults to 3 years)
data = fetcher.fetch()
```

### Date Format Support

The system accepts various date formats:

```python
# ISO date string
data = fetcher.fetch(start_date='2024-01-01')

# ISO datetime string
data = fetcher.fetch(start_date='2024-01-01T09:30:00')

# Python datetime object
from datetime import datetime
data = fetcher.fetch(start_date=datetime(2024, 1, 1, 9, 30))

# Relative dates using timedelta
start = datetime.now() - timedelta(days=30)
data = fetcher.fetch(start_date=start)
```

## Complete Examples

### Example 1: Forex Data with Date Ranges

```python
from src.data_fetcher import DataFetcher
from datetime import datetime

# Create fetcher for EUR/USD
fetcher = DataFetcher(
    source='forex',
    symbol='EURUSD',
    timeframe='1h',
    use_cache=True
)

# Fetch Q1 2024 data
q1_data = fetcher.fetch(
    start_date='2024-01-01',
    end_date='2024-03-31'
)
print(f"Q1 2024: {len(q1_data)} hourly bars")

# Fetch last 30 days
recent_data = fetcher.fetch(
    start_date=datetime.now() - timedelta(days=30)
)
print(f"Last 30 days: {len(recent_data)} hourly bars")
```

### Example 2: Crypto Data with Precise Timestamps

```python
from src.data_fetcher import DataFetcher
from datetime import datetime

fetcher = DataFetcher(
    source='crypto',
    symbol='BTC/USDT',
    timeframe='15m',
    exchange='binance'
)

# Fetch specific trading session
session_data = fetcher.fetch(
    start_date=datetime(2024, 6, 1, 9, 0, 0),   # June 1, 9:00 AM
    end_date=datetime(2024, 6, 1, 17, 0, 0)     # June 1, 5:00 PM
)
print(f"Trading session: {len(session_data)} 15-minute bars")
```

### Example 3: Indices with Capital.com

```python
from src.data_fetcher import DataFetcher

# S&P 500 daily data
fetcher = DataFetcher(
    source='indices',
    symbol='US500',  # Capital.com symbol
    timeframe='1d'
)

# Fetch full year 2023
year_2023 = fetcher.fetch(
    start_date='2023-01-01',
    end_date='2023-12-31'
)

# Calculate yearly performance
returns = (year_2023['close'].iloc[-1] / year_2023['close'].iloc[0] - 1) * 100
print(f"2023 S&P 500 return: {returns:.2f}%")
```

## Caching Behavior

### How Caching Works with Date Ranges

Each unique date range creates its own cache entry:

```python
fetcher = DataFetcher(source='forex', symbol='EURUSD', timeframe='1h', use_cache=True)

# These create separate cache entries
jan_data = fetcher.fetch(start_date='2024-01-01', end_date='2024-01-31')  # Cache key 1
feb_data = fetcher.fetch(start_date='2024-02-01', end_date='2024-02-28')  # Cache key 2
q1_data = fetcher.fetch(start_date='2024-01-01', end_date='2024-03-31')   # Cache key 3

# Subsequent identical requests use cache
jan_data_cached = fetcher.fetch(start_date='2024-01-01', end_date='2024-01-31')  # From cache!
```

### Cache Performance

```python
import time

fetcher = DataFetcher(source='crypto', symbol='ETH/USDT', timeframe='1h', use_cache=True)

# First call - fetches from API
start = time.time()
data1 = fetcher.fetch(start_date='2024-01-01', end_date='2024-01-31')
api_time = time.time() - start
print(f"API fetch: {api_time:.2f} seconds")

# Second call - loads from cache
start = time.time()
data2 = fetcher.fetch(start_date='2024-01-01', end_date='2024-01-31')
cache_time = time.time() - start
print(f"Cache load: {cache_time:.2f} seconds")
print(f"Speed improvement: {api_time/cache_time:.1f}x faster")
```

## Error Handling

### Common Errors and Solutions

```python
from src.data_fetcher import DataFetcher

fetcher = DataFetcher(source='forex', symbol='EURUSD', timeframe='1h')

# Error 1: Invalid date range (start > end)
try:
    data = fetcher.fetch(start_date='2024-02-01', end_date='2024-01-01')
except ValueError as e:
    print(f"Error: {e}")  # "Start date must be before end date"

# Error 2: Invalid date format
try:
    data = fetcher.fetch(start_date='not-a-date')
except ValueError as e:
    print(f"Error: {e}")  # "Unable to parse date"

# Error 3: End date without start date
try:
    data = fetcher.fetch(end_date='2024-01-01')
except ValueError as e:
    print(f"Error: {e}")  # "If end_date is specified, start_date must also be provided"

# Error 4: Mixed parameters (handled gracefully)
# When both years and dates are specified, years takes precedence
data = fetcher.fetch(years=1, start_date='2024-01-01', end_date='2024-12-31')
# Warning: "Both years and date range specified. Using years parameter for backward compatibility."
```

## Best Practices

### When to Use Date Ranges vs Years

**Use Date Ranges when:**
- You need specific historical periods for analysis
- Backtesting specific market events or seasons
- Creating consistent comparison periods
- Optimizing cache usage for repeated analysis

**Use Years when:**
- You need a rolling window from current date
- Running general backtests
- Quick data exploration
- Maintaining backward compatibility

### Optimization Tips

1. **Cache Strategically**: Use consistent date ranges for better cache hits
   ```python
   # Good: Consistent monthly ranges
   for month in range(1, 13):
       data = fetcher.fetch(
           start_date=f'2024-{month:02d}-01',
           end_date=f'2024-{month:02d}-{calendar.monthrange(2024, month)[1]}'
       )
   ```

2. **Batch Related Requests**: Group similar timeframes and symbols
   ```python
   symbols = ['EURUSD', 'GBPUSD', 'USDJPY']
   for symbol in symbols:
       fetcher = DataFetcher(source='forex', symbol=symbol, timeframe='1h')
       data = fetcher.fetch(start_date='2024-01-01', end_date='2024-06-30')
   ```

3. **Use Appropriate Timeframes**: Balance between resolution and data volume
   ```python
   # For long-term analysis: use daily
   long_term = fetcher.fetch(start_date='2020-01-01', end_date='2024-12-31', timeframe='1d')
   
   # For short-term analysis: use hourly or 15m
   short_term = fetcher.fetch(start_date='2024-06-01', end_date='2024-06-30', timeframe='1h')
   ```

## Migration Guide

### Updating Existing Code

If you have existing code using the years parameter, no changes are required:

```python
# Existing code continues to work
data = fetcher.fetch(years=2)
```

To migrate to date ranges for more control:

```python
# Before (years-based)
data = fetcher.fetch(years=1)

# After (date range)
from datetime import datetime, timedelta
end_date = datetime.now()
start_date = end_date - timedelta(days=365)
data = fetcher.fetch(start_date=start_date, end_date=end_date)
```

### Benefits of Migration

1. **Precise Period Selection**: Exact start and end dates
2. **Consistent Backtesting**: Same date range across multiple runs
3. **Better Cache Utilization**: Reuse cached data for specific periods
4. **Event Analysis**: Focus on specific market events or time windows

## Advanced Usage

### Using with Capital.com Direct API

```python
from src.capital_com_fetcher import create_capital_com_fetcher

fetcher = create_capital_com_fetcher()
if fetcher:
    with fetcher:
        # Fetch with date range
        data = fetcher.fetch_historical_data(
            symbol='EURUSD',
            asset_type='forex',
            timeframe='15m',
            start_date='2024-01-01',
            end_date='2024-01-31'
        )
```

### Parallel Date Range Fetching

```python
from concurrent.futures import ThreadPoolExecutor
from src.data_fetcher import DataFetcher

def fetch_month(month):
    fetcher = DataFetcher(source='forex', symbol='EURUSD', timeframe='1h')
    return fetcher.fetch(
        start_date=f'2024-{month:02d}-01',
        end_date=f'2024-{month:02d}-{calendar.monthrange(2024, month)[1]}'
    )

# Fetch all months of 2024 in parallel
with ThreadPoolExecutor(max_workers=4) as executor:
    monthly_data = list(executor.map(fetch_month, range(1, 13)))
```

## API Reference

### DataFetcher.fetch()

```python
def fetch(self, 
         years: Optional[Union[int, float]] = None,
         start_date: Optional[Union[str, datetime]] = None,
         end_date: Optional[Union[str, datetime]] = None) -> pd.DataFrame:
    """
    Fetch historical market data.
    
    Parameters:
    -----------
    years : int or float, optional
        Number of years of data to fetch (backward compatible)
    start_date : str or datetime, optional
        Start date for data fetching
    end_date : str or datetime, optional
        End date for data fetching
        
    Returns:
    --------
    pd.DataFrame
        DataFrame with OHLCV data indexed by timestamp
        
    Notes:
    ------
    - If years is provided, start_date and end_date are ignored
    - If only start_date is provided, end_date defaults to current time
    - If neither is provided, defaults to years=3
    """
```

## Troubleshooting

### Issue: Cache not being used with date ranges

**Solution**: Ensure you're using consistent date formats and timezone-aware dates:
```python
# Use consistent format
start = '2024-01-01'  # Always use same format
end = '2024-12-31'
```

### Issue: Trading hours affecting data completeness

**Solution**: The system automatically adjusts to valid trading hours:
```python
# Request includes weekend
data = fetcher.fetch(
    start_date='2024-01-05',  # Friday
    end_date='2024-01-08'      # Monday
)
# Data automatically excludes weekend (Saturday-Sunday)
```

### Issue: Large date ranges timing out

**Solution**: Use appropriate timeframes for large ranges:
```python
# For multi-year data, use daily timeframe
fetcher = DataFetcher(source='forex', symbol='EURUSD', timeframe='1d')
data = fetcher.fetch(start_date='2020-01-01', end_date='2024-12-31')
```

## Related Documentation

- [Capital.com Integration](CAPITAL_COM_COMPLETE.md) - Professional data provider setup
- [Caching System](CACHING.md) - Detailed caching documentation
- [Transport Layer](TRANSPORT_LAYER.md) - Storage backend configuration
- [Performance Optimization](PERFORMANCE_CHANGELOG.md) - Performance tips and history
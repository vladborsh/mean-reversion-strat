# Capital.com Data Integration Guide

## Overview

The Capital.com integration provides professional-grade forex and indices market data through direct API access to institutional trading infrastructure. This system implements intelligent trading hours validation, automatic session management, and seamless integration with the existing data fetching architecture.

## Quick Setup

### Environment Variables
```bash
export CAPITAL_COM_API_KEY="your_api_key"
export CAPITAL_COM_PASSWORD="your_password"
export CAPITAL_COM_IDENTIFIER="your_email@example.com"
export CAPITAL_COM_DEMO="true"  # Use demo environment
```

### Basic Usage
```python
from src.data_fetcher import DataFetcher

# Automatic Capital.com integration
fetcher = DataFetcher(source='forex', symbol='EURUSD', timeframe='1h')
data = fetcher.fetch(years=2)
```

## Provider Selection Logic

| Asset Type | Primary Provider | Fallback Chain | Rationale |
|------------|------------------|----------------|-----------|
| **Forex** | Capital.com | yfinance → Alpha Vantage | Professional trading hours, 5m+ data |
| **Indices** | Capital.com | yfinance → Alpha Vantage | Real-time institutional data |
| **Crypto** | CCXT/Binance | yfinance | 24/7 market, exchange-specific |

### Selection Algorithm
1. Check asset type (forex/indices prefer Capital.com)
2. Verify Capital.com credentials availability
3. Test API connectivity
4. Fall back to next provider if unavailable

## Trading Hours and Data Quality

### Forex Market Schedule (UTC)

| Period | Status | Description |
|--------|--------|-------------|
| **Sunday 22:00 - Friday 21:00** | OPEN | Main trading period |
| **Daily 21:00 - 22:00** | CLOSED | Global rollover break |
| **Friday 21:00 - Sunday 22:00** | CLOSED | Weekend closure |

### Time Adjustment Logic

The system automatically adjusts requested date ranges to valid trading periods:

**Start Time Adjustment**:
- Saturday/Sunday before 22:00 → Next Sunday 22:00 UTC
- Weekday 21:00-22:00 → Next 22:00 UTC
- Already valid → No change

**End Time Adjustment**:
- After Friday 21:00 → Friday 20:59:59 UTC
- Weekend → Previous Friday 20:59:59 UTC
- Daily closure period → Same day 20:59:59 UTC

### Data Quality Features

| Feature | Capital.com | yfinance | Alpha Vantage |
|---------|-------------|----------|---------------|
| **Trading Hours Filter** | ✅ Automatic | ❌ Manual | ❌ Manual |
| **Intraday Data** | ✅ 5m-1d | ⚠️ Limited | ✅ 1m-daily |
| **Weekend Data** | ❌ Filtered out | ⚠️ Included | ⚠️ Included |
| **Data Gaps** | ✅ Properly handled | ⚠️ May have gaps | ✅ Clean |

## Session Management

### Authentication Requirements
Capital.com uses session-based authentication with limited token lifetime (~10 minutes).

| Component | Purpose | Lifetime |
|-----------|---------|----------|
| **CST Token** | Session identifier | ~10 minutes |
| **X-SECURITY-TOKEN** | Request authentication | ~10 minutes |
| **API Key** | Initial authentication | Permanent |

### Session Lifecycle
```python
# Automatic session management (recommended)
with create_capital_com_fetcher() as fetcher:
    data = fetcher.fetch_historical_data('EURUSD', 'forex', '1h', 2)

# Manual session control
fetcher = CapitalComDataFetcher(api_key, password, identifier)
fetcher.create_session()  # Get tokens
# ... make requests ...
fetcher.close_session()   # Clean up
```

### Auto-Renewal Logic
- Sessions checked before each request
- Auto-renewal at 9:10 minutes (10-second buffer)
- Graceful failure handling if renewal fails

## Data Chunking and API Optimization

### Request Limits and Chunking Strategy

Capital.com API has a 1000-record limit per request. The system optimizes chunk sizes based on timeframe:

| Timeframe | Records/Day | Optimal Chunk | Reasoning |
|-----------|-------------|---------------|-----------|
| **5m** | 288 | 3 days (~864 records) | High frequency, small chunks |
| **15m** | 96 | 10 days (~960 records) | Balanced efficiency |
| **1h** | 24 | 41 days (~984 records) | Larger chunks, fewer requests |
| **4h** | 6 | 166 days (~996 records) | Very efficient |
| **1d** | 1 | 1000 days | Maximum API efficiency |

### Chunk Processing Logic
1. **Calculate chunk size** based on timeframe and record density
2. **Validate trading hours** for chunk boundaries
3. **Request data** for each chunk sequentially
4. **Merge results** into continuous dataset
5. **Handle gaps** between chunks due to weekends/closures

### Rate Limiting
- **Base limit**: 10 requests/second
- **Adaptive throttling**: Increase delays if rate limit errors
- **Chunk delays**: 200ms between chunks to be conservative

## Symbol Mapping

### Automatic Format Translation

The system translates between common symbol formats and Capital.com epics:

| Input Format | Asset Type | Capital.com Epic | Notes |
|--------------|------------|------------------|-------|
| `EURUSD` | Forex | `EURUSD` | Strip Yahoo suffix |
| `EURUSD` | Forex | `EURUSD` | Direct mapping |
| `^GSPC` | Index | `US500` | S&P 500 mapping |
| `SPY` | Index | `US500` | ETF to index |
| `^DJI` | Index | `US30` | Dow Jones |

### Supported Assets

**Forex Pairs**:
- **Major**: EURUSD, GBPUSD, USDJPY, USDCHF, AUDUSD, USDCAD, NZDUSD
- **Cross**: EURJPY, GBPJPY, EURGBP

**Indices**:
- **US**: US500 (S&P 500), US30 (Dow), USTECH100 (NASDAQ)
- **EU**: UK100 (FTSE), GER40 (DAX), FRA40 (CAC 40)
- **Asia**: JPN225 (Nikkei)

### Market Discovery
```python
# Search for available markets
fetcher.search_markets('EUR')  # Find EUR-related instruments
fetcher.get_market_details('EURUSD')  # Get detailed info
```

## Error Handling and Resilience

### Multi-Layer Error Recovery

| Error Level | Error Types | Recovery Strategy | Fallback |
|-------------|-------------|-------------------|----------|
| **API Errors** | Network timeout, Rate limiting | Retry with backoff | Session recreation |
| **Auth Errors** | 401/403, Token expired | Recreate session | Switch to yfinance |
| **Data Errors** | Empty response, Bad format | Skip chunk, continue | Log warning |
| **System Errors** | Provider unavailable | Graceful degradation | Fallback provider |

### Common Error Patterns

**Authentication Issues** (401/403):
```python
# Automatic session recreation
if response.status_code == 401:
    self.create_session()  # Get new tokens
    return self._retry_request()
```

**Rate Limiting** (429):
```python
# Adaptive throttling
if response.status_code == 429:
    self.min_request_interval *= 1.5  # Slow down
    time.sleep(self.min_request_interval)
```

**Empty Data Response**:
```python
# Skip chunk and continue
if not data:
    print(f"No data for chunk {start} to {end}, continuing...")
    return self._process_next_chunk()
```

## Performance and Caching

### Performance Metrics

| Operation | Capital.com | yfinance | Improvement |
|-----------|-------------|----------|-------------|
| **1H Data (1 year)** | 2-3 seconds | 5-8 seconds | 2-3x faster |
| **15M Data (6 months)** | 3-5 seconds | Not available | Unique capability |
| **Session Overhead** | ~0.5 seconds | None | Minimal impact |
| **Cache Hit** | ~0.1 seconds | ~0.1 seconds | Equal performance |

### Cache Integration

The Capital.com fetcher integrates seamlessly with the project's caching system:

```python
# Automatic caching
fetcher = DataFetcher(source='forex', symbol='EURUSD', use_cache=True)
data1 = fetcher.fetch(years=1)  # API call (~3 seconds)
data2 = fetcher.fetch(years=1)  # Cache hit (~0.1 seconds)
```

**Cache Key Format**: `capital_com_EURUSD_1h_20240101_20250101_forex_hash`

### Performance Optimization Tips

1. **Use appropriate timeframes**: Higher frequency = more API calls
2. **Enable caching**: Dramatic speedup for repeated requests
3. **Batch similar requests**: Group related symbols/timeframes
4. **Context managers**: Automatic session reuse

## Troubleshooting

### Common Issues and Solutions

| Issue | Symptoms | Diagnosis | Solution |
|-------|----------|-----------|----------|
| **Authentication Failure** | 401/403 errors | Invalid credentials | Check environment variables |
| **No Data Returned** | Empty DataFrames | Symbol not found | Verify symbol mapping |
| **Session Timeout** | Intermittent 403s | Token expired | Use context manager |
| **Rate Limiting** | 429 errors | Too many requests | Reduce request frequency |
| **Trading Hours** | Missing weekend data | Expected behavior | Data correctly filtered |

### Diagnostic Steps

**Step 1: Test Connection**
```python
from src.capital_com_fetcher import create_capital_com_fetcher

fetcher = create_capital_com_fetcher()
if not fetcher:
    print("❌ Check environment variables")
```

**Step 2: Verify Symbol**
```python
with fetcher:
    markets = fetcher.search_markets('EURUSD')
    print(f"Found {len(markets)} markets")
```

**Step 3: Test Data Fetch**
```python
with fetcher:
    data = fetcher.fetch_historical_data('EURUSD', 'forex', '1h', 0.1)
    print(f"Fetched {len(data) if data else 0} records")
```

### Integration Verification

**Check Provider Priority**:
```python
from src.data_fetcher import DataFetcher

fetcher = DataFetcher(source='forex', symbol='EURUSD')
print(f"Provider order: {fetcher.provider_priority['forex']['1h']}")
# Should show: ['capital_com', 'yfinance', 'alpha_vantage']
```

## Provider Comparison

### Feature Comparison Matrix

| Feature | Capital.com | yfinance | Alpha Vantage | Notes |
|---------|-------------|----------|---------------|-------|
| **Data Quality** | Institutional | Consumer | Professional | Capital.com = trading platform data |
| **Intraday Frequency** | 5m, 15m, 1h, 4h | Limited | 1m, 5m, 15m | Capital.com best for forex |
| **Trading Hours** | Auto-filtered | Raw data | Raw data | Only Capital.com respects market hours |
| **Rate Limits** | 1000 records/req | Aggressive blocking | 500 calls/day | Capital.com most generous |
| **Reliability** | High (trading infra) | Variable | High | Capital.com backed by broker |
| **Cost** | Free demo + paid | Free | Limited free | Capital.com free tier sufficient |
| **Setup Complexity** | Medium (API keys) | Low (no auth) | Low (API key) | Worth the setup for quality |

### When to Use Each Provider

**Capital.com**: 
- Professional forex/indices trading
- Need 5m/15m data
- Trading hours accuracy important
- High data quality requirements

**yfinance**:
- Quick prototyping
- Daily data sufficient
- No API setup wanted
- US markets focus

**Alpha Vantage**:
- Need very high frequency (1m)
- US equities focus
- API reliability important

## Advanced Usage Examples

### Multiple Timeframes
```python
# Fetch different timeframes for same symbol
timeframes = ['5m', '15m', '1h', '4h', '1d']
data = {}

with create_capital_com_fetcher() as fetcher:
    for tf in timeframes:
        data[tf] = fetcher.fetch_historical_data('EURUSD', 'forex', tf, 1)
        print(f"{tf}: {len(data[tf])} records")
```

### Portfolio Data Collection
```python
# Fetch multiple symbols efficiently
symbols = ['EURUSD', 'GBPUSD', 'USDJPY']
portfolio_data = {}

with create_capital_com_fetcher() as fetcher:
    for symbol in symbols:
        portfolio_data[symbol] = fetcher.fetch_historical_data(
            symbol, 'forex', '1h', 2
        )
```

### Trading Hours Validation
```python
from src.helpers import is_trading_hour, format_trading_session_info
from datetime import datetime

# Check if current time is trading hour
now = datetime.utcnow()
status = format_trading_session_info(now)
print(f"Market status: {status}")

# Only fetch during trading hours
if is_trading_hour(now):
    data = fetcher.fetch_historical_data('EURUSD', 'forex', '5m', 0.1)
```

# Mean Reversion Trading Strategy

A comprehensive trading strategy implementation using Bollinger Bands and VWAP for mean reversion trading across forex, crypto, and indices markets.

## Features

- **Multi-Asset Support**: Forex (Capital.com, yfinance), Crypto (CCXT/Binance), Indices (Capital.com, yfinance)
- **Professional Data Sources**: Capital.com API for institutional-grade forex and indices data
- **Technical Indicators**: Bollinger Bands + VWAP with standard deviation bands
- **Risk Management**: Configurable stop loss and take profit
- **Data Caching**: Automatic caching of fetched data for improved performance
- **Trading Hours Handling**: Automatic forex market hours validation and data filtering
- **Backtesting**: Full backtest engine with Backtrader
- **Performance Metrics**: Win rate, Sharpe ratio, drawdown analysis
- **Optimization**: Grid search for hyperparameter tuning
- **Visualization**: Price charts, performance plots, drawdown analysis

## Installation

### 1. Clone or Navigate to Project Directory
```bash
cd /Users/Vladyslav_Borsh/Documents/dev/mean-reversion-strat
```

### 2. Python Environment Setup
The project already has a configured virtual environment. Activate it:

```bash
source .venv/bin/activate
```

### 3. Verify Dependencies
All required packages are already installed:
- yfinance (forex/indices data)
- ccxt (crypto data)
- backtrader (backtesting engine)
- pandas (data manipulation)
- numpy (numerical operations)
- matplotlib (visualization)
- requests (Capital.com API integration)

### 4. Capital.com Integration (Optional)
For professional forex and indices data, set up Capital.com credentials:

```bash
# Set environment variables for Capital.com API access
export CAPITAL_COM_API_KEY="your_api_key"
export CAPITAL_COM_PASSWORD="your_password"
export CAPITAL_COM_IDENTIFIER="your_email@example.com"
export CAPITAL_COM_DEMO="true"  # Use demo environment (set to 'false' for live)
```

**Benefits of Capital.com integration:**
- High-frequency data (5m, 15m intervals)
- Proper forex trading hours handling
- Professional-grade institutional data
- Automatic session management

See [Capital.com Complete Guide](docs/CAPITAL_COM_COMPLETE.md) for detailed setup.

## Quick Start

### Basic Usage
```bash
# Run the main strategy with default parameters
python main.py
```

### Custom Data Source Examples

#### Professional Forex Trading (Capital.com)
```python
from data_fetcher import DataFetcher

# Capital.com provides institutional-grade data with proper trading hours
fetcher = DataFetcher(source='forex', symbol='EURUSD=X', timeframe='1h', use_cache=True)
data = fetcher.fetch(years=3)  # Automatically uses Capital.com if available
run_strategy(data)

# High-frequency trading with 15-minute data
fetcher = DataFetcher(source='forex', symbol='GBPUSD=X', timeframe='15m', use_cache=True)
data = fetcher.fetch(years=1)
```

#### Forex Trading (Yahoo Finance Fallback)
```python
# Data is automatically cached after first fetch
# Falls back to yfinance if Capital.com not configured
fetcher = DataFetcher(source='forex', symbol='EURUSD=X', timeframe='1h', use_cache=True)
data = fetcher.fetch(years=3)
run_strategy(data)
```

#### Crypto Trading (BTC/USDT)
```python
# Cache works with all data sources
fetcher = DataFetcher(source='crypto', symbol='BTC/USDT', timeframe='1h', exchange='binance', use_cache=True)
data = fetcher.fetch(years=2)
run_strategy(data)
```

#### Stock Index (S&P 500)
```python
# Capital.com provides professional indices data
fetcher = DataFetcher(source='indices', symbol='^GSPC', timeframe='1d', use_cache=True)
data = fetcher.fetch(years=5)
run_strategy(data)
```

## Data Sources and Providers

The strategy supports multiple data providers with automatic fallback:

### Forex Data
1. **Capital.com** (Primary) - Professional institutional data
   - ✅ 5m, 15m, 1h, 4h, 1d timeframes
   - ✅ Proper trading hours handling  
   - ✅ Major and cross currency pairs
   - ✅ Free tier available
2. **Yahoo Finance** (Fallback) - Reliable free data
3. **Alpha Vantage** (Fallback) - API-based provider

### Indices Data  
1. **Capital.com** (Primary) - Professional market data
2. **Yahoo Finance** (Fallback) - Major global indices
3. **Alpha Vantage** (Fallback) - US markets focus

### Crypto Data
1. **CCXT/Binance** (Primary) - Real-time exchange data
2. **Yahoo Finance** (Fallback) - Major crypto pairs

### Provider Selection
```python
# Automatic provider selection based on availability
fetcher = DataFetcher(source='forex', symbol='EURUSD=X')

# Check which provider was used
print(f"Using provider: {fetcher.provider_priority}")
```

## Data Caching

The strategy now includes automatic data caching to improve performance and reduce API calls.

### How Caching Works
- **Automatic**: Data is cached automatically after first fetch
- **Intelligent Expiry**: Cache expires based on data timeframe (15m data expires faster than daily data)
- **Persistent**: Cache persists between script runs
- **Unique Keys**: Different symbols, timeframes, and parameters create separate cache entries

### Cache Management

#### Check Cache Status
```python
from data_fetcher import DataFetcher

fetcher = DataFetcher(source='forex', symbol='EURUSD=X', timeframe='1h')
cache_info = fetcher.get_cache_info()
print(f"Cache files: {cache_info['total_files']}")
print(f"Cache size: {cache_info['total_size_mb']:.2f} MB")
```

#### Cache Performance Test
```bash
# Run the caching test to see performance improvements
python test_caching.py
```

#### Cache Management Utility
```bash
# Show cache information
python cache_manager.py info

# Clear old cache files (older than 30 days)
python cache_manager.py clear --max-age-days 30

# Clear all cache files
python cache_manager.py clear

# Test cache performance
python cache_manager.py test

# Invalidate cache for specific symbol
python cache_manager.py invalidate
```

#### Disable Caching
```python
# Disable caching if needed
fetcher = DataFetcher(source='forex', symbol='EURUSD=X', timeframe='1h', use_cache=False)
```

### Cache Configuration
- **Default Location**: `./cache/` directory in project root
- **Cache Expiry**: 
  - 15-minute data: 2 hours
  - 1-hour data: 6 hours
  - 4-hour data: 12 hours
  - Daily data: 24 hours
- **File Format**: Compressed pickle files with metadata

## Configuration

### Strategy Parameters
You can customize the strategy parameters in `main.py`:

```python
params = {
    'bb_window': 20,        # Bollinger Bands window
    'bb_std': 2,           # Bollinger Bands standard deviation
    'vwap_window': 20,     # VWAP window
    'vwap_std': 2,         # VWAP standard deviation
    'stop_loss': 0.02,     # Stop loss percentage (2%)
    'take_profit': 0.04    # Take profit percentage (4%)
}
```

### Timeframes
Supported timeframes:
- `'15m'` - 15 minutes
- `'1h'` - 1 hour
- `'4h'` - 4 hours
- `'1d'` - 1 day

## Running Different Components

### 1. Data Fetching Only
```python
from data_fetcher import DataFetcher

# Fetch EUR/USD hourly data for 3 years
fetcher = DataFetcher(source='forex', symbol='EURUSD=X', timeframe='1h')
df = fetcher.fetch(years=3)
print(df.head())
```

### 2. Calculate Indicators
```python
from indicators import Indicators

# Calculate Bollinger Bands
bb_ma, bb_upper, bb_lower = Indicators.bollinger_bands(df, window=20, num_std=2)

# Calculate VWAP with bands
vwap, vwap_upper, vwap_lower = Indicators.vwap_bands(df, window=20, num_std=2)
```

### 3. Run Backtest
```python
from backtest import run_backtest
from strategy import MeanReversionStrategy

params = {'bb_window': 20, 'bb_std': 2, 'vwap_window': 20, 'vwap_std': 2, 'stop_loss': 0.02, 'take_profit': 0.04}
equity_curve, trade_log = run_backtest(df, MeanReversionStrategy, params)
```

### 4. Calculate Performance Metrics
```python
from metrics import calculate_metrics

metrics = calculate_metrics(trade_log, equity_curve)
print(f"Win Rate: {metrics['win_rate']:.2%}")
print(f"Sharpe Ratio: {metrics['sharpe_ratio']:.2f}")
print(f"Max Drawdown: {metrics['max_drawdown']:.2%}")
```

### 5. Hyperparameter Optimization
```python
from optimize import grid_search

param_grid = {
    'bb_window': [15, 20, 25],
    'bb_std': [1.5, 2.0, 2.5],
    'vwap_window': [15, 20, 25],
    'vwap_std': [1.5, 2.0, 2.5],
    'stop_loss': [0.01, 0.02, 0.03],
    'take_profit': [0.02, 0.04, 0.06]
}

best_params, best_metrics = grid_search(param_grid, df, MeanReversionStrategy)
print("Optimal parameters:", best_params)
```

### 6. Visualization
```python
from visualization import plot_price_with_indicators, plot_equity_curve, plot_drawdown

# Plot price with indicators
bb = {'ma': bb_ma, 'upper': bb_upper, 'lower': bb_lower}
vwap_dict = {'vwap': vwap, 'upper': vwap_upper, 'lower': vwap_lower}
plot_price_with_indicators(df, bb, vwap_dict)

# Plot performance
plot_equity_curve(equity_curve)
plot_drawdown(equity_curve)
```

## Trading Logic

### Buy Signal
- Price breaks below both Bollinger Bands lower AND VWAP lower bands
- Price then turns back up (reversal confirmation)

### Sell Signal  
- Price breaks above both Bollinger Bands upper AND VWAP upper bands
- Price then turns back down (reversal confirmation)

### Risk Management
- Stop Loss: Triggered when price moves against position by specified percentage
- Take Profit: Triggered when price moves in favor of position by specified percentage
- No overlapping positions allowed

## Output Interpretation

### Metrics Explained
- **Win Rate**: Percentage of profitable trades
- **Total Return**: Overall portfolio performance
- **Sharpe Ratio**: Risk-adjusted returns (higher is better)
- **Max Drawdown**: Largest peak-to-trough decline (lower is better)
- **Average Return per Trade**: Mean profit/loss per trade
- **Volatility**: Annualized portfolio volatility

### Trade Log
Each trade contains:
- Entry/exit prices
- Trade type (buy/sell)
- Exit reason (stop_loss/take_profit)
- P&L for closed trades

## Troubleshooting

### Common Issues

1. **No data fetched**: Check internet connection and symbol format
2. **CCXT errors**: Ensure exchange is accessible and symbol format is correct
3. **Memory issues with large datasets**: Reduce years of data or use higher timeframes
4. **Visualization not showing**: Ensure matplotlib backend is properly configured

### Symbol Formats
- **Forex**: Use Yahoo Finance format (e.g., 'EURUSD=X', 'GBPUSD=X') or simple format ('EURUSD', 'GBPUSD')
- **Crypto**: Use exchange format (e.g., 'BTC/USDT', 'ETH/USDT')
- **Indices**: Use Yahoo Finance format (e.g., '^GSPC', '^DJI', '^IXIC') or tickers ('SPY', 'QQQ')

### Capital.com Specific Issues

1. **Missing credentials**: Set up environment variables for Capital.com API access
   ```bash
   export CAPITAL_COM_API_KEY="your_key"
   export CAPITAL_COM_PASSWORD="your_password"
   export CAPITAL_COM_IDENTIFIER="your_email"
   ```

2. **Session timeouts**: Use context manager for automatic session management
   ```python
   with create_capital_com_fetcher() as fetcher:
       data = fetcher.fetch_historical_data('EURUSD', 'forex', '1h', 2)
   ```

3. **Trading hours validation**: Data is automatically filtered for forex trading hours
   - Open: Sunday 22:00 UTC to Friday 21:00 UTC
   - Daily break: 21:00-22:00 UTC excluded

## Advanced Usage

### Custom Strategy Development
Extend the `MeanReversionStrategy` class to add:
- Additional indicators
- Different entry/exit conditions
- Portfolio management features
- Multiple timeframe analysis

### Live Trading Integration
To adapt for live trading:
1. Replace historical data with real-time feeds
2. Implement order execution through broker APIs
3. Add position sizing based on account equity
4. Include transaction costs and slippage

## Documentation

Comprehensive documentation is available in the `docs/` directory:

- **[Capital.com Complete Guide](docs/CAPITAL_COM_COMPLETE.md)** - Comprehensive setup, logic explanation, and troubleshooting
- **[Strategy Documentation](docs/STRATEGY_DOCUMENTATION.md)** - Detailed strategy logic and parameters
- **[Risk Management](docs/RISK_MANAGEMENT.md)** - Risk management features and configuration
- **[Caching System](docs/CACHING.md)** - Data caching implementation and management

### Quick Reference

| Topic | Documentation File | Description |
|-------|-------------------|-------------|
| **Capital.com Complete** | `CAPITAL_COM_COMPLETE.md` | Setup, architecture, trading hours logic, troubleshooting |
| **Strategy Logic** | `STRATEGY_DOCUMENTATION.md` | Bollinger Bands + VWAP implementation |
| **Risk Controls** | `RISK_MANAGEMENT.md` | Stop loss, take profit, position sizing |
| **Performance** | `CACHING.md` | Cache configuration, performance optimization |

## Support

For issues or questions:
1. Check the troubleshooting section
2. Verify all dependencies are installed
3. Ensure data sources are accessible
4. Review parameter configurations

## License

This project is for educational and research purposes.

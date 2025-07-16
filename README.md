# Mean Reversion Trading Strategy

A comprehensive trading strategy implementation using Bollinger Bands and VWAP for mean reversion trading across forex, crypto, and indices markets.

## Features

- **Multi-Asset Support**: Forex (yfinance), Crypto (CCXT/Binance), Indices
- **Technical Indicators**: Bollinger Bands + VWAP with standard deviation bands
- **Risk Management**: Configurable stop loss and take profit
- **Data Caching**: Automatic caching of fetched data for improved performance
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

## Quick Start

### Basic Usage
```bash
# Run the main strategy with default parameters
python main.py
```

### Custom Data Source Examples

#### Forex Trading (EUR/USD)
```python
from data_fetcher import DataFetcher
from main import run_strategy

# Data is automatically cached after first fetch
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
fetcher = DataFetcher(source='indices', symbol='^GSPC', timeframe='1d', use_cache=True)
data = fetcher.fetch(years=5)
run_strategy(data)
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
- **Forex**: Use Yahoo Finance format (e.g., 'EURUSD=X', 'GBPUSD=X')
- **Crypto**: Use exchange format (e.g., 'BTC/USDT', 'ETH/USDT')
- **Indices**: Use Yahoo Finance format (e.g., '^GSPC', '^DJI', '^IXIC')

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

## Support

For issues or questions:
1. Check the troubleshooting section
2. Verify all dependencies are installed
3. Ensure data sources are accessible
4. Review parameter configurations

## License

This project is for educational and research purposes.

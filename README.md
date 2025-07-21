# Mean Reversion Trading Strategy

A comprehensive trading strategy implementation using Bollinger Bands and VWAP for mean reversion trading across forex, crypto, and indices markets.

## Features

- **Multi-Asset Support**: Forex, Crypto, and Indices with multiple data providers
- **Data Sources**: Capital.com API (professional), Yahoo Finance, CCXT/Binance
- **Technical Analysis**: Bollinger Bands + VWAP with standard deviation bands
- **Risk Management**: Configurable stop loss, take profit, and position sizing
- **Performance Tools**: Data caching, market hours validation, visualization
- **Backtesting**: Complete backtest engine with comprehensive metrics
- **Optimization**: Multiple hyperparameter tuning approaches with dedicated CLI

## Installation and Setup

### 1. Clone or Navigate to Project Directory
```bash
cd /Users/Vladyslav_Borsh/Documents/dev/mean-reversion-strat
```

### 2. Python Environment Setup
The project already has a configured virtual environment. Activate it:

```bash
source .venv/bin/activate  # On macOS/Linux
# OR
.\.venv\Scripts\activate   # On Windows
```

If setting up from scratch:
```bash
# Create a virtual environment
python -m venv .venv

# Activate it
source .venv/bin/activate  # On macOS/Linux
# OR
.\.venv\Scripts\activate   # On Windows

# Install dependencies
pip install -r requirements.txt
```

### 3. Capital.com Integration (Optional)
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

## High-Level Architecture

```
┌────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  Data Sources  │────>│  Core Strategy  │────>│    Analysis     │
│  & Fetchers    │     │  & Backtester   │     │  & Reporting    │
└────────────────┘     └─────────────────┘     └─────────────────┘
        │                       │                       │
        v                       v                       v
┌────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│    Caching     │     │      Risk       │     │  Visualization  │
│    System      │     │   Management    │     │     Tools       │
└────────────────┘     └─────────────────┘     └─────────────────┘
                               │
                               v
                      ┌─────────────────┐
                      │  Optimization   │
                      │    Framework    │
                      └─────────────────┘
```

### Key Components

1. **Data Layer**: Multi-source data fetching with intelligent caching
2. **Strategy Core**: Mean reversion logic using technical indicators
3. **Backtesting Engine**: Performance evaluation and trade analysis
4. **Optimization Framework**: Hyperparameter tuning with multiple objectives
5. **Visualization**: Trading charts, performance metrics, and trade analysis

## Quick Start

```bash
# Run the main strategy with default parameters
python main.py

# Basic optimization with balanced objective
python optimize_strategy.py --quick-test
```

## CLI Tools and Commands

### Strategy Optimization

```bash
# Quick optimization test (faster, fewer combinations)
python optimize_strategy.py --quick-test --sort-objective balanced

# Full grid search with different parameter sets
python optimize_strategy.py --grid-search balanced  # Balanced parameters
python optimize_strategy.py --grid-search focused   # PnL-focused parameters
python optimize_strategy.py --grid-search risk      # Risk management focused

# Random search (faster for large parameter spaces)
python optimize_strategy.py --random-search 100 --sort-objective balanced

# Custom optimization objectives
python optimize_strategy.py --grid-search balanced --sort-objective max_sharpe
python optimize_strategy.py --grid-search balanced --sort-objective min_drawdown
python optimize_strategy.py --grid-search balanced --sort-objective risk_adjusted

# Time period selection
python optimize_strategy.py --grid-search balanced --years 2 --timeframe 1h
```

### Cache Management

```bash
# View cache information
python cache_manager.py info

# Clear old cache files (older than 30 days)
python cache_manager.py clear --max-age-days 30

# Clear all cache
python cache_manager.py clear

# Invalidate cache for specific symbol
python cache_manager.py invalidate --symbol EURUSD=X
```

### Data Fetching

```bash
# Fetch forex data (Capital.com or fallback)
python -c "from src.data_fetcher import DataFetcher; df = DataFetcher(source='forex', symbol='EURUSD=X', timeframe='1h').fetch(years=2); print(df.head())"

# Fetch crypto data
python -c "from src.data_fetcher import DataFetcher; df = DataFetcher(source='crypto', symbol='BTC/USDT', timeframe='1h').fetch(years=1); print(df.head())"
```

## Data Sources and Providers

The strategy supports multiple data providers with automatic fallback:

1. **Capital.com** (Primary for Forex/Indices) - Professional institutional data
2. **Yahoo Finance** (Fallback) - Reliable free data
3. **CCXT/Binance** (Primary for Crypto) - Real-time exchange data

## Optimization Framework

The strategy includes multiple optimization approaches for different goals:

### 1. Objective Functions

- **`max_pnl`**: Maximize final PnL (most aggressive)
- **`balanced`**: Balance between PnL and drawdown (recommended)
- **`max_sharpe`**: Maximize Sharpe ratio (risk-adjusted returns)
- **`min_drawdown`**: Minimize maximum drawdown (most conservative)
- **`risk_adjusted`**: Custom risk/reward scoring formula

### 2. Parameter Grids

- **Balanced Grid**: Moderate parameter ranges focusing on stability
- **Focused Grid**: Wider parameter ranges for maximum performance
- **Risk Grid**: Fine-tuning of risk parameters only

### 3. Optimization Methods

- **Grid Search**: Exhaustive testing of all parameter combinations
- **Random Search**: Random sampling of parameter space (faster)

See [Hyperparameter Optimization](docs/HYPERPARAMETER_OPTIMIZATION.md) for detailed documentation.

## Configuration

### Strategy Parameters

```python
params = {
    'bb_window': 20,      # Bollinger Bands window
    'bb_std': 2,          # Bollinger Bands standard deviation
    'vwap_window': 20,    # VWAP window
    'vwap_std': 2,        # VWAP standard deviation
    'stop_loss': 0.02,    # Stop loss percentage (2%)
    'take_profit': 0.04   # Take profit percentage (4%)
}
```

## Trading Logic

- **Buy Signal**: Price breaks below both Bollinger and VWAP lower bands, then reverses
- **Sell Signal**: Price breaks above both Bollinger and VWAP upper bands, then reverses
- **Risk Management**: Configurable stop loss and take profit levels

## Documentation

Comprehensive documentation is available in the `docs/` directory:

- **[Capital.com Guide](docs/CAPITAL_COM_COMPLETE.md)** - API setup and usage
- **[Strategy Documentation](docs/STRATEGY_DOCUMENTATION.md)** - Strategy logic
- **[Optimization Guide](docs/HYPERPARAMETER_OPTIMIZATION.md)** - Optimization methods
- **[Risk Management](docs/RISK_MANAGEMENT.md)** - Risk management features
- **[Caching System](docs/CACHING.md)** - Data caching implementation

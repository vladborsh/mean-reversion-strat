# Mean Reversion Trading Strategy

A comprehensive trading strategy implementation using Bollinger Bands and VWAP for mean reversion trading across forex, crypto, and indices markets.

## Documentation

Comprehensive documentation is available in the `docs/` directory:

- **[Capital.com Guide](docs/CAPITAL_COM_COMPLETE.md)** - API setup and usage
- **[Strategy Documentation](docs/STRATEGY_DOCUMENTATION.md)** - Strategy logic
- **[Optimization Guide](docs/HYPERPARAMETER_OPTIMIZATION.md)** - Optimization methods
- **[Risk Management](docs/RISK_MANAGEMENT.md)** - Risk management features
- **[Caching System](docs/CACHING.md)** - Data caching implementation
- **[Container Documentation](CONTAINER.md)** - Container usage and deployment
- **[AWS Batch Setup](docs/AWS_BATCH_SETUP.md)** - AWS Batch configuration and deployment
- **[AWS Batch Scripts](docs/AWS_BATCH_SCRIPTS.md)** - Ready-to-use job submission and monitoring scripts
- **[Transport Layer](docs/TRANSPORT_LAYER.md)** - Storage backends and configuration

## Features

- **Multi-Asset Support**: Forex, Crypto, and Indices with multiple data providers
- **Data Sources**: Capital.com API (professional), Yahoo Finance, CCXT/Binance
- **Technical Analysis**: Bollinger Bands + VWAP with standard deviation bands
- **Risk Management**: Configurable stop loss, take profit, and position sizing
- **Performance Tools**: Data caching, market hours validation, visualization
- **Backtesting**: Complete backtest engine with comprehensive metrics
- **Optimization**: Multiple hyperparameter tuning approaches with dedicated CLI
- **🆕 Transport Layer**: Optional AWS S3 storage for caching and logs with local fallback

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
# Run with optimized configuration (recommended)
python main.py --symbol EURUSD=X --timeframe 5m --preference balanced

# Run the main strategy with default parameters (fallback)
python main.py

# Basic optimization with balanced objective
python optimize_strategy.py --quick-test
```

## Running with Containers

The strategy can be run in a containerized environment using Podman:

### Building the Container

```bash
# Build the strategy container
podman build -t mean-reversion-strategy .
```

### Running Optimizations in Container

```bash
# Basic run (results remain inside container)
podman run mean-reversion-strategy --quick-test

# Run a quick test (results stored in local optimization directory)
podman run --rm -v $(pwd)/optimization:/app/optimization mean-reversion-strategy --quick-test

# Run grid search with visualization enabled
podman run --rm -v $(pwd)/optimization:/app/optimization mean-reversion-strategy --grid-search focused --plot-equity-curves

# Run with custom symbol and timeframe
podman run --rm -v $(pwd)/optimization:/app/optimization mean-reversion-strategy --quick-test --symbol GBPUSD=X --timeframe 1h

# Run focused grid search with S3 transport for cache and logs
podman run --rm mean-reversion-strategy --grid-search focused --symbol GBPUSD=X --timeframe 5m --cache-transport s3 --log-transport s3
```

### Helper Script

A helper script is provided to simplify container operations:

```bash
# Build and show usage examples
./run_optimization.sh

# Run quick test with the script
./run_optimization.sh --quick-test

# Run grid search with the script
./run_optimization.sh --grid-search balanced --plot-equity-curves
```

For more information on container usage, see [Container Documentation](docs/CONTAINER.md).

## CLI Tools and Commands

All CLI tools now support transport configuration for cache and logs. Use `--cache-transport` and `--log-transport` flags to specify storage backend:

- `--cache-transport local|s3`: Cache storage (default: local)  
- `--log-transport local|s3`: Log/optimization storage (default: local)

### Strategy Backtesting

The main strategy now supports using **pre-optimized configurations** from the results folder, or falling back to default settings:

```bash
# Use optimized configurations based on preference
python main.py --symbol EURUSD=X --timeframe 5m --preference balanced
python main.py --symbol AUDUSD=X --timeframe 5m --preference pnl  
python main.py --symbol GBPUSD=X --timeframe 5m --preference drawdown

# Run with S3 storage for cache and logs
python main.py --symbol EURGBP=X --timeframe 5m --preference balanced --cache-transport s3 --log-transport s3

# Mixed storage: local cache, S3 logs
python main.py --symbol NZDUSD=X --timeframe 5m --preference drawdown --cache-transport local --log-transport s3

# Fallback to default config if optimized config not found
python main.py --symbol BTCUSD=X --timeframe 15m --preference balanced
```

**New Arguments:**
- `--preference`: Strategy optimization preference (`balanced`, `pnl`, `drawdown`)
  - `balanced`: Best overall risk-adjusted performance
  - `pnl`: Maximum profit potential
  - `drawdown`: Minimum maximum drawdown
- `--symbol`: Trading symbol (e.g., `EURUSD=X`, `AUDUSD=X`, `GBPUSD=X`)
- `--timeframe`: Data timeframe (`5m`, `15m`, `1h`)

The script automatically loads optimized hyperparameters from the `results/` folder based on your symbol, timeframe, and preference. If no optimized configuration is found, it falls back to default settings.

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

# With transport configuration
python optimize_strategy.py --grid-search balanced --cache-transport s3 --log-transport s3
python optimize_strategy.py --random-search 50 --cache-transport local --log-transport s3

# Custom optimization objectives
python optimize_strategy.py --grid-search balanced --sort-objective max_sharpe
python optimize_strategy.py --grid-search balanced --sort-objective min_drawdown
python optimize_strategy.py --grid-search balanced --sort-objective risk_adjusted

# Time period selection
python optimize_strategy.py --grid-search balanced --years 2 --timeframe 1h

# Reduce console output during optimization (useful for automated runs)
python optimize_strategy.py --grid-search balanced --quiet
python optimize_strategy.py --random-search 100 --quiet --sort-objective balanced
```

### Cache Management

```bash
# View cache information
python cache_manager.py info --cache-transport local
python cache_manager.py info --cache-transport s3

# View optimization storage info  
python cache_manager.py optimization-info --log-transport s3

# Clear old cache files (older than 30 days)
python cache_manager.py clear --max-age-days 30 --cache-transport local

# Clear all cache
python cache_manager.py clear --cache-transport s3

# Clear logs in S3 storage
python cache_manager.py clear --log-transport s3

# Invalidate cache for specific symbol
python cache_manager.py invalidate --symbol EURUSD=X --cache-transport local
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

## Transport Layer

The project supports flexible storage backends for caching and logging:

### Local Storage (Default)
- Fast access for development and testing
- No external dependencies
- All data stored in project directories

### AWS S3 Storage (Optional)
- Cloud storage for scalability and team collaboration
- Automatic backup and durability
- Configurable through environment variables

### Configuration
Add to your `.env` file for S3 support:

```bash
# AWS S3 Configuration (optional)
AWS_ACCESS_KEY_ID=your_aws_access_key
AWS_SECRET_ACCESS_KEY=your_aws_secret_key
AWS_REGION=us-east-1
AWS_S3_BUCKET=your-bucket-name
AWS_S3_PREFIX=mean-reversion-strat/

# Note: CACHE_TRANSPORT and LOG_TRANSPORT are now configured via CLI arguments
# Use --cache-transport and --log-transport options when running scripts
```

### Transport Selection

Transport type is now specified via command-line arguments instead of environment variables:

**Cache Transport** (`--cache-transport`):
- `local`: Store cache files in local `cache/` directory  
- `s3`: Store cache files in AWS S3 bucket

**Log Transport** (`--log-transport`):
- `local`: Store optimization logs/results in local `optimization/` directory
- `s3`: Store optimization logs/results in AWS S3 bucket

**Examples:**
```bash
# Use local storage for everything (default)
python main.py --cache-transport local --log-transport local

# Use S3 for cache, local for logs
python main.py --cache-transport s3 --log-transport local

# Use S3 for everything
python optimize_strategy.py --grid-search balanced --cache-transport s3 --log-transport s3
```

For detailed transport layer documentation, see [docs/TRANSPORT_LAYER.md](docs/TRANSPORT_LAYER.md).

### Migration from Environment Variables

**Previous approach (deprecated):**
```bash
# Old .env configuration (no longer used)
CACHE_TRANSPORT=s3
LOG_TRANSPORT=s3
```

**New approach (current):**
```bash
# Use CLI arguments instead
python main.py --cache-transport s3 --log-transport s3
python optimize_strategy.py --grid-search balanced --cache-transport s3 --log-transport s3
python cache_manager.py info --cache-transport s3 --log-transport s3
```

**Benefits of CLI approach:**
- More explicit and visible configuration
- Easy to override per command without changing files
- Better support for CI/CD and automation scripts
- Clear separation between environment secrets (API keys) and transport configuration

### Quick Reference: Transport CLI Options

All strategy scripts support these transport arguments:

| Argument | Values | Default | Description |
|----------|--------|---------|-------------|
| `--cache-transport` | `local`, `s3` | `local` | Where to store data cache files |
| `--log-transport` | `local`, `s3` | `local` | Where to store optimization logs/results |

**Available in:**
- `main.py` - Main strategy backtesting
- `optimize_strategy.py` - Hyperparameter optimization
- `cache_manager.py` - Cache management utilities

**Examples:**
```bash
# Different combinations for different use cases
python main.py --cache-transport local --log-transport local    # All local (default)
python main.py --cache-transport s3 --log-transport local       # S3 cache, local logs
python main.py --cache-transport local --log-transport s3       # Local cache, S3 logs  
python main.py --cache-transport s3 --log-transport s3          # All S3
```

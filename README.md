# Mean Reversion Trading Strategy

A comprehensive trading strategy implementation using Bollinger Bands and VWAP for mean reversion trading across forex, crypto, and indices markets.

## Table of Contents

- [Documentation](#documentation)
- [Features](#features)
- [Installation and Setup](#installation-and-setup)
- [High-Level Architecture](#high-level-architecture)
- [Quick Start](#quick-start)
- [Live Trading and Telegram Bot](#live-trading-and-telegram-bot)
- [Running with Containers](#running-with-containers)
- [CLI Tools and Commands](#cli-tools-and-commands)
- [Data Sources and Providers](#data-sources-and-providers)
- [Optimization Framework](#optimization-framework)
- [Configuration](#configuration)
- [Trading Logic](#trading-logic)
- [Transport Layer](#transport-layer)

## Documentation

Comprehensive documentation is available in the `docs/` directory:

- **[Capital.com Guide](docs/CAPITAL_COM_COMPLETE.md)** - API setup and usage
- **[Strategy Documentation](docs/STRATEGY_DOCUMENTATION.md)** - Strategy logic
- **[Telemetry & TUI Monitor](docs/TELEMETRY_TUI_GUIDE.md)** - Real-time monitoring and telemetry system
- **[Live Performance Verifier](docs/LIVE_PERFORMANCE_VERIFIER.md)** - Historical performance analysis tool
- **[Optimization Guide](docs/HYPERPARAMETER_OPTIMIZATION.md)** - Optimization methods
- **[Post-Processing & Results Analysis](docs/POST_PROCESSING.md)** - Analyzing optimization results and generating PNL charts
- **[Performance Changelog](docs/PERFORMANCE_CHANGELOG.md)** - Strategy performance evolution and improvements
- **[Risk Management](docs/RISK_MANAGEMENT.md)** - Risk management features
- **[Caching System](docs/CACHING.md)** - Data caching implementation
- **[Container Documentation](docs/CONTAINER.md)** - Container usage and deployment
- **[Telegram Bot Integration](docs/TELEGRAM_BOT_INTEGRATION.md)** - Real-time trading signals via Telegram
- **[Signal Cache Persistence](docs/signal_cache_persistence.md)** - DynamoDB storage for duplicate signal prevention
- **[Telegram DynamoDB Persistence](docs/telegram_dynamodb_persistence.md)** - DynamoDB storage for chat management
- **[Bot Docker Instructions](docs/BOT_DOCKER_INSTRUCTIONS.md)** - Container deployment for the bot
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
- **📊 Live Performance Verification**: Historical analysis tool using real strategy execution
- **Optimization**: Multiple hyperparameter tuning approaches with dedicated CLI
- **🤖 Live Trading Bot**: Telegram bot integration for real-time signal notifications
- **🐳 Container Support**: Full Docker/Podman support for deployment and scaling
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

### 4. Telegram Bot Setup (Optional)
For live trading notifications, configure the Telegram bot:

```bash
# Add to your .env file for bot notifications
TELEGRAM_BOT_TOKEN="your_telegram_bot_token_here"
```

See **[Telegram Bot Integration](docs/TELEGRAM_BOT_INTEGRATION.md)** for detailed setup instructions.

**Benefits of Capital.com integration:**
- High-frequency data (5m, 15m intervals)
- Proper forex trading hours handling
- Professional-grade institutional data
- Automatic session management

## High-Level Architecture

```
┌────────────────┐     ┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  Data Sources  │────>│  Core Strategy  │────>│    Analysis     │────>│  Telegram Bot   │
│  & Fetchers    │     │  & Backtester   │     │  & Reporting    │     │ & Notifications │
└────────────────┘     └─────────────────┘     └─────────────────┘     └─────────────────┘
        │                       │                       │                       │
        v                       v                       v                       v
┌────────────────┐     ┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│    Caching     │     │      Risk       │     │  Visualization  │     │ Live Strategy   │
│    System      │     │   Management    │     │     Tools       │     │   Scheduler     │
└────────────────┘     └─────────────────┘     └─────────────────┘     └─────────────────┘
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
6. **Live Trading Bot**: Real-time signal detection and Telegram notifications
7. **Container Support**: Full Docker/Podman deployment with scaling capabilities

## Quick Start

```bash
# Run with optimized configuration (recommended)
python main.py --symbol EURUSD --timeframe 5m --preference balanced

# Run the main strategy with default parameters (fallback)
python main.py

# Basic optimization with balanced objective
python optimize_strategy.py --quick-test
```

## Live Trading and Telegram Bot

The strategy includes a live trading scheduler with Telegram bot integration for real-time signal notifications:

### Features
- **📱 Real-time Notifications**: Get trading signals instantly via Telegram
- **⏰ Automated Scheduling**: Runs analysis every 5 minutes during trading hours (6:00-17:00 UTC)
- **🎯 Smart Signal Detection**: Uses optimized parameters for live market analysis
- **🔄 Multiple Deployment Options**: Run locally, in containers, or on cloud platforms

### Quick Setup

1. **Configure Telegram Bot** (optional):
   ```bash
   # Add to your .env file
   TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here
   ```

2. **Run Live Strategy**:
   ```bash
   # Start the live strategy scheduler
   python live_strategy_scheduler.py
   
   # Or run in a container (recommended for production)
   podman build -f Dockerfile.bot -t mean-reversion-bot .
   podman run --env-file .env mean-reversion-bot
   ```

3. **Subscribe to Notifications**:
   - Find your bot on Telegram (using the username you created)
   - Send `/start` to begin receiving signals
   - Use `/help` to see available commands

For detailed setup instructions, see:
- **[Telegram Bot Integration](docs/TELEGRAM_BOT_INTEGRATION.md)** - Complete bot setup guide
- **[Bot Docker Instructions](docs/BOT_DOCKER_INSTRUCTIONS.md)** - Container deployment

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
podman run --rm -v $(pwd)/optimization:/app/optimization mean-reversion-strategy --quick-test --symbol GBPUSD --timeframe 1h

# Run focused grid search with S3 transport for cache and logs
podman run --rm mean-reversion-strategy --grid-search focused --symbol GBPUSD --timeframe 5m --cache-transport s3 --log-transport s3
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
python main.py --symbol EURUSD --timeframe 5m --preference balanced
python main.py --symbol AUDUSD --timeframe 5m --preference pnl  
python main.py --symbol GBPUSD --timeframe 5m --preference drawdown

# Run with S3 storage for cache and logs
python main.py --symbol EURGBP --timeframe 5m --preference balanced --cache-transport s3 --log-transport s3

# Mixed storage: local cache, S3 logs
python main.py --symbol NZDUSD --timeframe 5m --preference drawdown --cache-transport local --log-transport s3

# Fallback to default config if optimized config not found
python main.py --symbol BTCUSD --timeframe 15m --preference balanced
```

**New Arguments:**
- `--preference`: Strategy optimization preference (`balanced`, `pnl`, `drawdown`)
  - `balanced`: Best overall risk-adjusted performance
  - `pnl`: Maximum profit potential
  - `drawdown`: Minimum maximum drawdown
- `--symbol`: Trading symbol (e.g., `EURUSD`, `AUDUSD`, `GBPUSD`)
- `--timeframe`: Data timeframe (`5m`, `15m`, `1h`)

The script automatically loads optimized hyperparameters from the `results/` folder based on your symbol, timeframe, and preference. If no optimized configuration is found, it falls back to default settings.

### Live Performance Verification

Verify how the live trading strategy would have performed over historical periods using real backtesting:

```bash
# Analyze last 3 weeks (default)
python live_performance_verifier.py

# Analyze specific periods
python live_performance_verifier.py --period 1w    # 1 week
python live_performance_verifier.py --period 21d   # 21 days
python live_performance_verifier.py --period 2m    # 2 months

# Analyze specific symbols
python live_performance_verifier.py --symbols EURUSD GBPUSD AUDUSD

# Detailed analysis with trade breakdown
python live_performance_verifier.py --detailed --export json

# Generate visual charts
python live_performance_verifier.py --chart --save-order-charts
```

**Key Features:**
- Uses the same `MeanReversionStrategy` as the live scheduler
- Shows real trade outcomes (take profit, stop loss, timeout)
- Calculates accurate P&L, win rate, and drawdown metrics
- Displays chronological trade history across all symbols
- **Visual analysis** with P&L curve and order tracking charts
- **Order charts** show all trades with entry, SL/TP levels and outcomes
- Exports results to JSON/CSV for further analysis

📖 **[Complete Documentation](docs/LIVE_PERFORMANCE_VERIFIER.md)** - Detailed usage guide and result interpretation

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
python cache_manager.py invalidate --symbol EURUSD --cache-transport local
```

### Data Fetching

#### Using Years (Backward Compatible)
```bash
# Fetch forex data (Capital.com or fallback)
python -c "from src.data_fetcher import DataFetcher; df = DataFetcher(source='forex', symbol='EURUSD', timeframe='1h').fetch(years=2); print(df.head())"

# Fetch crypto data
python -c "from src.data_fetcher import DataFetcher; df = DataFetcher(source='crypto', symbol='BTC/USDT', timeframe='1h').fetch(years=1); print(df.head())"
```

#### Using Date Ranges (NEW)
```bash
# Fetch data by specific date range
python -c "from src.data_fetcher import DataFetcher; df = DataFetcher(source='forex', symbol='EURUSD', timeframe='1h').fetch(start_date='2024-01-01', end_date='2024-12-31'); print(df.head())"

# Fetch from specific date to now (end_date defaults to current time)
python -c "from src.data_fetcher import DataFetcher; df = DataFetcher(source='crypto', symbol='BTC/USDT', timeframe='1h').fetch(start_date='2024-06-01'); print(df.head())"

# Using datetime objects for precise control
python -c "from src.data_fetcher import DataFetcher; from datetime import datetime; df = DataFetcher(source='indices', symbol='^GSPC', timeframe='1d').fetch(start_date=datetime(2024, 1, 1), end_date=datetime(2024, 6, 30)); print(df.head())"
```

## Data Sources and Providers

The strategy supports multiple data providers with automatic fallback:

1. **Capital.com** (Primary for Forex/Indices) - Professional institutional data
2. **Yahoo Finance** (Fallback) - Reliable free data
3. **CCXT/Binance** (Primary for Crypto) - Real-time exchange data

### Flexible Date Range Support

All data fetchers now support flexible date range specification:

- **Years-based** (backward compatible): `fetch(years=2)` - Fetches 2 years of historical data
- **Date range**: `fetch(start_date='2024-01-01', end_date='2024-12-31')` - Fetches specific date range
- **Start date only**: `fetch(start_date='2024-06-01')` - Fetches from date to current time
- **Default behavior**: `fetch()` - Fetches 3 years of data (default)

Date formats supported:
- ISO string format: `'2024-01-01'` or `'2024-01-01T10:00:00'`
- Python datetime objects: `datetime(2024, 1, 1)`

For detailed documentation, see [Data Fetching Guide](docs/DATA_FETCHING_GUIDE.md).

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

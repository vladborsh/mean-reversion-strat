# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Mean reversion trading strategy using Bollinger Bands + VWAP for forex, crypto, and indices markets. Includes comprehensive backtesting, optimization framework, live trading scheduler with Telegram notifications, and flexible storage backends (local/S3).

## Development Environment

```bash
# Activate virtual environment
source .venv/bin/activate  # macOS/Linux
# .\.venv\Scripts\activate  # Windows

# Install/update dependencies
pip install -r requirements.txt
```

## Common Development Commands

### Running Backtests

The strategy supports pre-optimized configurations loaded from `results/` folder:

```bash
# Use optimized configurations (recommended)
python main.py --symbol EURUSD --timeframe 5m --preference balanced
python main.py --symbol AUDUSD --timeframe 5m --preference pnl
python main.py --symbol GBPUSD --timeframe 5m --preference drawdown

# With S3 storage
python main.py --symbol EURUSD --timeframe 5m --preference balanced --cache-transport s3 --log-transport s3
```

**Config Loading Pattern**: The script automatically loads optimized parameters from `results/best_configs_{preference}.json` based on symbol/timeframe. Falls back to default config in `src/config.py` if not found.

### Strategy Optimization

```bash
# Quick test (small grid)
python optimize_strategy.py --quick-test --sort-objective balanced

# Grid search with different configs
python optimize_strategy.py --grid-search balanced --plot-equity-curves
python optimize_strategy.py --grid-search focused --sort-objective pnl
python optimize_strategy.py --grid-search risk --timeframe 1h --years 2

# Random search (faster for large parameter spaces)
python optimize_strategy.py --random-search 100 --sort-objective balanced --quiet

# With transport selection
python optimize_strategy.py --grid-search balanced --cache-transport s3 --log-transport s3
```

**Optimization Objectives**: `balanced`, `max_pnl`, `max_sharpe`, `min_drawdown`, `risk_adjusted`, `profit_factor`

### Live Performance Verification

Verify how the live strategy would have performed historically:

```bash
# Analyze recent periods
python live_performance_verifier.py --period 3w
python live_performance_verifier.py --period 1m --symbols EURUSD GBPUSD

# Detailed analysis with charts
python live_performance_verifier.py --detailed --chart --save-order-charts
python live_performance_verifier.py --export json
```

### Live Trading

```bash
# Start live strategy scheduler (runs every 5 minutes)
python live_strategy_scheduler.py

# Container deployment (recommended for production)
podman build -f Dockerfile.bot -t mean-reversion-bot .
podman run --env-file .env mean-reversion-bot
```

### Cache Management

```bash
# View cache information
python cache_manager.py info --cache-transport local
python cache_manager.py info --cache-transport s3

# Clear cache
python cache_manager.py clear --max-age-days 30 --cache-transport local
python cache_manager.py invalidate --symbol EURUSD --cache-transport s3
```

## High-Level Architecture

### Data Layer (`src/data_fetcher.py`, `src/capital_com_fetcher.py`, `src/data_cache.py`)

**Multi-source data fetching** with automatic provider selection and fallback:
- **Capital.com** (primary for forex/indices): Professional institutional data, proper trading hours
- **Yahoo Finance** (fallback): Reliable free data for backtesting
- **CCXT/Binance** (primary for crypto): Real-time exchange data

**Caching Strategy**:
- Intelligent caching with configurable transport (local filesystem or S3)
- Cache invalidation and TTL support
- Symbol-specific cache keys

**Date Range Flexibility**:
- Legacy: `fetch(years=2)` - backward compatible
- Modern: `fetch(start_date='2024-01-01', end_date='2024-12-31')` - precise control

### Strategy Core (`src/strategy.py`)

**MeanReversionStrategy** - Backtrader-based strategy implementing:

**Entry Logic**:
- **Long**: Price below both BB lower band AND VWAP lower band
- **Short**: Price above both BB upper band AND VWAP upper band
- Market regime filtering (optional, controlled by `regime_enabled`)

**Exit Logic**:
- ATR-based stop loss (configurable multiplier)
- Risk/reward ratio take profit (configurable ratio)
- Time-based position closure (varies by timeframe: 5m=6hrs, 15m=12hrs, 1h=48hrs)
- Trailing stops (optional, configurable activation and breakeven levels)

**Critical Implementation Detail - Exact P&L Calculation**:
- Stop loss exits use **exact SL price**, not market price (eliminates slippage)
- Take profit exits use **exact TP price**, not market price
- Ensures precise risk management: 1% risk = exactly -1000 on 100k account
- Implemented in `_record_trade_outcome()` and `notify_trade()` methods

### Risk Management (`src/risk_management.py`, `src/config.py`)

**Position Sizing**:
- Risk-based sizing using ATR for stop loss distance
- Configurable risk per position (default: 1% of account)
- Leverage support (default: 100:1 for forex/CFD)

**Risk/Reward Framework**:
- `stop_loss_atr_multiplier`: Distance from entry to SL in ATR units
- `risk_reward_ratio`: TP distance as multiple of SL distance
- Example: 1.2x ATR stop, 2.5 R:R ratio = TP at 3.0x ATR from entry

**Market Regime Filter** (`src/market_regime.py`):
- ADX-based trend detection (avoid strong trends)
- Volatility percentile filtering (prefer moderate volatility)
- Configurable scoring threshold (0-100, default: 60)
- Can be disabled via `regime_enabled` parameter

### Backtesting Engine (`src/backtest.py`)

**LeveragedBroker**: Custom Backtrader broker supporting forex/CFD leverage
- Tracks actual cash separately from leveraged virtual cash
- Updates actual cash only on trade completion (not on unrealized P&L)
- Provides accurate margin calculations for position sizing

**Order Lifecycle**:
- Timeframe-dependent order lifetime (see `ORDER_LIFETIME` in `src/config.py`)
- Automatic position closure on timeout
- Comprehensive order and trade logging

### Optimization Framework (`src/hyperparameter_optimizer.py`, `src/optimization_configs.py`)

**Parameter Search Methods**:
- Grid search: Exhaustive testing of parameter combinations
- Random search: Random sampling (faster for large spaces)

**Optimization Grids** (defined in `src/optimization_configs.py`):
- `balanced`: Moderate parameter ranges for stability
- `focused`: Wider ranges for maximum performance
- `comprehensive`: Full parameter space exploration
- Market-specific: `trending`, `ranging`, `high_vol`, `low_vol`, `scalping`, `swing`

**Sorting Objectives**:
- `balanced`: Multi-factor weighted score (Sharpe, drawdown, trades)
- `max_pnl`: Maximum final profit
- `max_sharpe`: Best risk-adjusted returns
- `min_drawdown`: Minimum maximum drawdown
- `profit_factor`: Gross profit / gross loss ratio

**Results Storage**: Best configurations saved to `results/best_configs_{objective}.json`

### Live Trading System (`src/bot/`, `live_strategy_scheduler.py`)

**LiveSignalDetector** (`src/bot/live_signal_detector.py`):
- Real-time signal detection using optimized configs
- Caching to prevent duplicate analysis
- Integration with Backtrader for signal generation

**Telegram Notifications** (`src/bot/telegram_bot.py`, `src/bot/telegram_signal_notifier.py`):
- Real-time trading signal alerts
- Chart generation with entry/SL/TP levels
- User subscription management
- DynamoDB persistence for chat state

**Signal Caching** (`src/bot/signal_cache.py`, `src/bot/persistent_signal_cache.py`):
- In-memory and DynamoDB-backed caching
- Prevents duplicate notifications for same signal
- TTL-based cache expiration

**News Integration** (`src/news/`):
- Economic calendar notifications
- News event tracking
- Scheduled updates

### Transport Layer (`src/transport.py`, `src/s3_transport.py`, `src/transport_factory.py`)

**Flexible Storage Backends**:
- **Local**: Fast filesystem-based storage (default)
- **S3**: AWS S3 for cloud storage and team collaboration

**Transport Selection**: Via CLI arguments (not environment variables)
- `--cache-transport local|s3`: Data cache storage
- `--log-transport local|s3`: Optimization results and logs

**Configuration**:
- AWS credentials in `.env` file
- Transport type selected per-command via CLI args
- Factory pattern for transport creation

## Code Organization

### Configuration System

**Single Source of Truth**: `src/config.py`
- All strategy parameters defined in `Config` class
- Sections: `BOLLINGER_BANDS`, `VWAP`, `RISK_MANAGEMENT`, `TRAILING_STOPS`, `ENTRY_CONDITIONS`, `MARKET_REGIME`, `ORDER_LIFETIME`, `BACKTEST`
- Helper methods: `get_backtrader_params()`, `get_risk_config()`, `get_trailing_stop_config()`
- Mode presets: `set_mode('backtest'|'live'|'conservative')`

**Loading Optimized Configs**: `main.py` pattern
1. Try loading from `results/best_configs_{preference}.json`
2. Create custom config class with `create_custom_config_class(config_dict)`
3. Fall back to default `Config` if not found
4. Pass to strategy via `run_strategy(df, config_class, timeframe)`

### Key Modules

**Core Strategy**:
- `src/strategy.py`: MeanReversionStrategy implementation
- `src/backtest.py`: LeveragedBroker and backtesting engine
- `src/indicators.py`: Technical indicator calculations (BB, VWAP, ATR)

**Data Management**:
- `src/data_fetcher.py`: Multi-source data fetching with caching
- `src/capital_com_fetcher.py`: Capital.com API integration
- `src/data_cache.py`: Caching layer with transport abstraction

**Risk & Portfolio**:
- `src/risk_management.py`: Position sizing and risk calculations
- `src/portfolio_manager.py`: Portfolio-level risk management
- `src/trailing_stop.py`: Trailing stop implementation
- `src/market_regime.py`: Market condition filtering

**Optimization**:
- `src/hyperparameter_optimizer.py`: Grid/random search implementation
- `src/optimization_configs.py`: Parameter grid definitions
- `src/optimize.py`: Optimization utilities

**Live Trading**:
- `src/bot/live_signal_detector.py`: Real-time signal detection
- `src/bot/telegram_bot.py`: Telegram bot core
- `src/bot/signal_cache.py`: Signal deduplication
- `src/bot/signal_chart_generator.py`: Trading chart generation

**Visualization**:
- `src/visualization.py`: Equity curves, drawdown plots
- `src/order_visualization.py`: Order entry/exit charts
- `src/chart_plotters.py`: Price charts with indicators

### Bot Subsystem (`src/bot/`)

**Components**:
- `telegram_bot.py`: Core bot with command handlers (`/start`, `/help`, `/status`)
- `telegram_signal_notifier.py`: Sends trading signals to subscribed users
- `telegram_chat_manager.py`: User subscription management
- `signal_cache.py`: In-memory signal deduplication
- `persistent_signal_cache.py`: DynamoDB-backed cache for distributed systems
- `live_signal_detector.py`: Real-time strategy signal detection
- `signal_chart_generator.py`: Generates charts with entry/SL/TP levels
- `dynamodb_base.py`: Base class for DynamoDB integrations
- `telegram_dynamodb_storage.py`: Persistent chat storage
- `telegram_message_templates.py`: Message formatting

**Integration Pattern**:
1. `LiveSignalDetector` runs strategy on latest data
2. Detects buy/sell signals
3. Checks `SignalCache` for duplicates
4. `TelegramSignalNotifier` sends to subscribed users
5. `SignalChartGenerator` creates visual charts
6. `PersistentSignalCache` stores in DynamoDB

## Important Development Patterns

### Transport Configuration

**Always use CLI arguments**, not environment variables:

```bash
# Correct
python main.py --cache-transport s3 --log-transport local
python optimize_strategy.py --grid-search balanced --cache-transport local --log-transport s3

# Incorrect (deprecated)
export CACHE_TRANSPORT=s3  # Don't use env vars for transport selection
```

**Benefits**: Explicit configuration, per-command control, better CI/CD support

### Optimized Configuration Workflow

1. **Run optimization**: `python optimize_strategy.py --grid-search balanced --symbol EURUSD --timeframe 5m`
2. **Results saved to**: `results/best_configs_balanced.json`
3. **Use in backtest**: `python main.py --symbol EURUSD --timeframe 5m --preference balanced`
4. **Verify performance**: `python live_performance_verifier.py --symbols EURUSD --period 1m`

### Symbol Naming Conventions

- **Forex**: `EURUSD`, `GBPUSD`, `AUDUSD` (no suffix)
- **Crypto**: `BTC/USDT`, `ETH/USDT` (slash separator)
- **Indices**: `^GSPC`, `^DJI` (caret prefix)
- **Config keys**: `EURUSDX_5m`, `GBPUSDX_15m` (X suffix + timeframe)

### Risk Management Parameter Tuning

**Critical Parameters** (in `src/config.py`):
- `risk_per_position_pct`: 0.5-2.0% (lower = more conservative)
- `stop_loss_atr_multiplier`: 1.0-2.0 (higher = wider stops)
- `risk_reward_ratio`: 2.0-3.0 (higher = larger targets)
- `atr_period`: 14 (standard ATR period)

**Regime Filter Tuning**:
- `regime_min_score`: 0-100 (60 = balanced, 80 = very selective)
- `adx_strong_trend_threshold`: 20-30 (avoid trending markets)
- `volatility_high_threshold`: 60-80 percentile (avoid high vol)

### Order Lifetime Management

**Timeframe-Based Limits** (in `src/config.py`):
```python
ORDER_LIFETIME = {
    '5m': 360,      # 6 hours
    '15m': 720,     # 12 hours
    '1h': 2880,     # 2 days
}
```

Orders are automatically closed if not hitting SL/TP within these timeframes.

### Exact P&L Calculation Pattern

When implementing strategy modifications:
- **Never** use current market price for SL/TP exits
- **Always** use the exact SL/TP price set at entry
- Store exact exit prices in `_record_trade_outcome()`
- Calculate P&L in `notify_trade()` using stored prices
- This ensures: Risk = exactly 1% account, Reward = exactly R:R ratio × Risk

### Testing Strategy Changes

```bash
# 1. Test on single symbol/timeframe
python main.py --symbol EURUSD --timeframe 5m --years 1

# 2. Verify with live performance tool
python live_performance_verifier.py --symbols EURUSD --period 2w --detailed

# 3. Run optimization if parameters changed
python optimize_strategy.py --quick-test --symbol EURUSD --timeframe 5m

# 4. Full optimization for production
python optimize_strategy.py --grid-search balanced --years 2
```

## Documentation References

Key documentation in `docs/` folder:
- **STRATEGY_DOCUMENTATION.md**: Detailed strategy logic and parameters
- **CAPITAL_COM_COMPLETE.md**: Capital.com API setup and usage
- **HYPERPARAMETER_OPTIMIZATION.md**: Optimization framework guide
- **LIVE_PERFORMANCE_VERIFIER.md**: Historical verification tool
- **TELEGRAM_BOT_INTEGRATION.md**: Bot setup and deployment
- **TRANSPORT_LAYER.md**: Storage backend configuration
- **RISK_MANAGEMENT.md**: Risk management features
- **CONTAINER.md**: Docker/Podman deployment
- **AWS_BATCH_SETUP.md**: AWS Batch configuration for scaling

## Environment Variables

Required in `.env` file:

```bash
# Capital.com API (optional, for professional forex data)
CAPITAL_COM_API_KEY=your_api_key
CAPITAL_COM_PASSWORD=your_password
CAPITAL_COM_IDENTIFIER=your_email@example.com
CAPITAL_COM_DEMO=true  # true for demo, false for live

# Telegram Bot (optional, for live notifications)
TELEGRAM_BOT_TOKEN=your_bot_token

# AWS S3 (optional, for cloud storage)
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
AWS_REGION=us-east-1
AWS_S3_BUCKET=your-bucket-name
AWS_S3_PREFIX=mean-reversion-strat/

# AWS DynamoDB (optional, for signal caching)
AWS_DYNAMODB_TABLE_SIGNAL_CACHE=signal-cache
AWS_DYNAMODB_TABLE_TELEGRAM_CHATS=telegram-chats
```

## Common Pitfalls

1. **Transport Configuration**: Don't use environment variables (`CACHE_TRANSPORT`, `LOG_TRANSPORT`). Use CLI args (`--cache-transport`, `--log-transport`).

2. **Config Loading**: When using optimized configs, ensure symbol format matches config keys (e.g., `EURUSDX_5m` not `EURUSD_5m`).

3. **Risk Calculation**: Changing `stop_loss_atr_multiplier` or `risk_reward_ratio` requires re-optimization. These fundamentally change strategy behavior.

4. **Data Fetching**: Capital.com requires proper API credentials. Without them, strategy falls back to Yahoo Finance (limited timeframes).

5. **Backtest vs Live**: Always verify backtest results with `live_performance_verifier.py` before deploying live.

6. **Leverage**: Default 100:1 leverage is for forex/CFD. Adjust in `src/config.py` for different instruments.

7. **Time-based Exits**: Order lifetime varies by timeframe. 5m trades expire in 6 hours, 1h trades in 2 days.

8. **Regime Filtering**: Enabled by default. Disabling increases trade frequency but may reduce win rate.

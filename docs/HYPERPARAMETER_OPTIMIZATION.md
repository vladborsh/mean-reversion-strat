# Hyperparameter Optimization System

This document provides a comprehensive guide to the hyperparameter optimization system for the mean reversion strategy.

> **Related Documentation:**
> - [Post-Processing & Results Analysis](POST_PROCESSING.md) - Analyzing optimization results and generating PNL charts
> - [AWS Batch Setup](AWS_BATCH_SETUP.md) - Running distributed optimizations
> - [Performance Changelog](PERFORMANCE_CHANGELOG.md) - Strategy improvements over time

## Features

✅ **Market Data Caching** - Automatic caching of market data for consistent testing across optimization runs  
✅ **Intermediate Results Caching** - Cache individual backtest results to avoid recomputation  
✅ **CSV Logging** - Comprehensive logging of all results in CSV format for analysis  
✅ **Progress Tracking** - Real-time progress tracking with estimated completion times  
✅ **Multiple Optimization Methods** - Grid search, random search, and more  
✅ **Predefined Configurations** - Ready-to-use parameter grids for different scenarios  
✅ **Best Results Tracking** - Track best results by multiple objectives (PnL, Sharpe, Win Rate, etc.)  
✅ **Resume Capability** - Resume interrupted optimizations using cached results  
✅ **🆕 Automated Configuration Loading** - Use optimized results directly in scripts/run_backtest.py without manual parameter updates

## Optimization Workflow

1. **Run Optimization**: Use `optimize_strategy.py` to generate optimized configurations
2. **Review Results**: Check `results/` folder for generated configuration files
3. **Apply Configurations**: Use `scripts/run_backtest.py` with `--preference` to load optimized settings automatically
4. **Compare Performance**: See expected vs. actual performance metrics  

## Quick Start

### 1. Using Pre-Optimized Configurations (Recommended)

For immediate use with optimized parameters:

```bash
# Use optimized configurations from results folder
python scripts/run_backtest.py --symbol EURUSD --timeframe 5m --preference balanced
python scripts/run_backtest.py --symbol AUDUSD --timeframe 5m --preference pnl
python scripts/run_backtest.py --symbol GBPUSD --timeframe 5m --preference drawdown
```

### 2. Running New Optimizations

For creating new optimized configurations:

```bash
# Quick test (4-16 parameter combinations)
python optimize_strategy.py --quick-test

# Focused optimization (~100-500 combinations, maximizing PnL)
python optimize_strategy.py --grid-search focused

# Balanced optimization (balance between PnL and drawdown)
python optimize_strategy.py --grid-search balanced --sort-objective balanced

# Risk management optimization
python optimize_strategy.py --grid-search risk

# Random search with 100 iterations
python optimize_strategy.py --random-search 100

# Different symbols and timeframes
python optimize_strategy.py --grid-search focused --symbol GBPUSD --timeframe 1h

# Use specific optimization objective
python optimize_strategy.py --grid-search focused --sort-objective max_sharpe
```

### 3. Python API Usage

```python
from src.hyperparameter_optimizer import HyperparameterOptimizer
from src.optimization_configs import OPTIMIZATION_CONFIGS

# Initialize optimizer
optimizer = HyperparameterOptimizer(
    data_source='forex',
    symbol='EURUSD',
    timeframe='15m',
    years=2
)

# Run optimization
param_grid = OPTIMIZATION_CONFIGS['focused']()
results = optimizer.grid_search(
    param_grid=param_grid,
    optimization_name="my_optimization"
)

# Get best result
best_result = results[0]  # Sorted by final PnL
print(f"Best PnL: ${best_result.final_pnl:,.2f}")
print(f"Best Parameters: {best_result.parameters}")
```

### 3. Interactive Examples

```bash
python examples/optimization_examples.py
```

## Optimization Configurations

### Available Grid Configurations

| Configuration | Purpose | Combinations | Runtime |
|---------------|---------|--------------|---------|
| `quick` | Fast testing | 4-16 | Minutes |
| `focused` | Key parameters (maximize PnL) | 100-500 | Hours |
| `balanced` | Balance PnL and drawdown | 100-400 | Hours |
| `comprehensive` | Thorough search | 1000+ | Days |
| `risk` | Risk management | 100-500 | Hours |
| `indicators` | Technical indicators | 500+ | Hours |
| `regime` | Market regime filtering | 100+ | Hours |

### Market Condition Specific

| Configuration | Purpose | Best For |
|---------------|---------|----------|
| `trending` | Trending markets | Strong directional moves |
| `ranging` | Sideways markets | Consolidation periods |
| `high_vol` | High volatility | News events, breakouts |
| `low_vol` | Low volatility | Quiet market periods |

### Timeframe Specific

| Configuration | Purpose | Timeframes |
|---------------|---------|------------|
| `scalping` | Fast trades | 1m, 5m |
| `swing` | Position holding | 1h, 4h, 1d |

## Output Files

### Directory Structure

```
optimization/
├── cache/                          # Cached data and results
│   ├── data_[hash].pkl            # Market data cache
│   └── result_[data_hash]_[param_hash].pkl  # Individual results
├── results/                        # Final results
│   ├── grid_search_focused_[timestamp].csv  # All results CSV
│   └── best_params_[timestamp].json        # Best parameters JSON
└── logs/                          # Progress logs
    └── progress_[timestamp].txt    # Real-time progress
```

### CSV Results Format

The CSV file contains all optimization results with columns:

- `timestamp` - When the test was run
- `final_pnl` - Final profit/loss in base currency
- `total_trades` - Number of completed trades
- `win_rate` - Percentage of winning trades
- `sharpe_ratio` - Risk-adjusted return metric
- `max_drawdown` - Maximum drawdown percentage
- `execution_time` - Time taken for this backtest
- `parameters` - All strategy parameters used

### Best Parameters JSON

The JSON file tracks the best results by different objectives:

```json
{
  "best_pnl": {
    "parameters": {...},
    "final_pnl": 15420.50,
    "sharpe_ratio": 1.85,
    "win_rate": 45.2
  },
  "best_sharpe": {...},
  "best_win_rate": {...},
  "lowest_drawdown": {...}
}
```

## Caching System

### Market Data Caching

- Market data is automatically cached based on source, symbol, timeframe, and years
- Cached data is reused across optimization runs for consistency
- Cache files are stored in `optimization/cache/data_[hash].pkl`

### Results Caching

- Individual backtest results are cached based on parameter combination and data hash
- Allows resuming interrupted optimizations
- Significantly speeds up repeated optimizations
- Cache files: `optimization/cache/result_[data_hash]_[param_hash].pkl`

### Cache Management

```python
# Clear old cache files (older than 7 days)
python cache_manager.py --clear-cache --max-age 7

# View cache info
python cache_manager.py --info
```

## Parameter Definitions

### Technical Indicators

| Parameter | Description | Typical Range | Default |
|-----------|-------------|---------------|---------|
| `bb_window` | Bollinger Bands period | 10-40 | 20 |
| `bb_std` | Bollinger Bands std dev | 1.5-3.5 | 2.0 |
| `vwap_window` | VWAP calculation period | 10-40 | 20 |
| `vwap_std` | VWAP bands std dev | 1.5-3.5 | 2.0 |
| `atr_period` | ATR calculation period | 5-30 | 14 |

### Risk Management

| Parameter | Description | Typical Range | Default |
|-----------|-------------|---------------|---------|
| `risk_per_position_pct` | Risk per trade (% of account) | 0.25-3.0 | 1.0 |
| `stop_loss_atr_multiplier` | Stop loss size (× ATR) | 0.5-3.0 | 1.2 |
| `risk_reward_ratio` | Risk/reward ratio | 1.5-5.0 | 2.5 |

### Strategy Behavior

| Parameter | Description | Options | Default |
|-----------|-------------|---------|---------|
| `require_reversal` | Require reversal confirmation | True/False | True |

### Market Regime Filtering

| Parameter | Description | Typical Range | Default |
|-----------|-------------|---------------|---------|
| `regime_min_score` | Minimum regime score (0-100) | 30-90 | 60 |
| `regime_adx_strong_threshold` | ADX threshold for strong trend | 15-35 | 25 |

## Performance Tips

### 1. Start Small
- Use `--quick-test` first to verify setup
- Use `focused` configuration before `comprehensive`
- Test with shorter data periods (1 year) initially

### 2. Use Caching Effectively
- Run multiple optimizations on same dataset to leverage caching
- Don't clear cache unless necessary
- Monitor cache size and clean periodically

### 3. Monitor Progress
- Check progress files in `logs/` directory
- Use estimated completion times for planning
- Consider running overnight for large optimizations

### 4. Analyze Results
- Sort CSV results by different metrics
- Look for parameter patterns in top results
- Consider robust results (appear in top 10% consistently)

## Example Workflows

### 1. Initial Strategy Development

```bash
# 1. Quick test to verify setup
python optimize_strategy.py --quick-test

# 2. Focused optimization on key parameters
python optimize_strategy.py --grid-search focused

# 3. Random search for broader exploration
python optimize_strategy.py --random-search 100

# 4. Deep dive into risk management
python optimize_strategy.py --grid-search risk
```

### 2. Market Condition Optimization

```bash
# Test for different market conditions
python optimize_strategy.py --grid-search trending --years 1
python optimize_strategy.py --grid-search ranging --years 1
python optimize_strategy.py --grid-search high_vol --years 1
```

### 3. Multi-Asset Analysis

```bash
# Test on different forex pairs
python optimize_strategy.py --grid-search focused --symbol GBPUSD
python optimize_strategy.py --grid-search focused --symbol USDJPY
python optimize_strategy.py --grid-search focused --symbol AUDUSD
```

### 4. Timeframe Comparison

```bash
# Compare different timeframes
python optimize_strategy.py --grid-search scalping --timeframe 5m
python optimize_strategy.py --grid-search focused --timeframe 15m
python optimize_strategy.py --grid-search swing --timeframe 1h
```

## Advanced Usage

### Custom Parameter Grids

```python
from src.hyperparameter_optimizer import HyperparameterOptimizer

# Define custom parameter grid
custom_grid = {
    'bb_window': [15, 20, 25],
    'risk_per_position_pct': [0.5, 1.0, 1.5, 2.0],
    'risk_reward_ratio': [2.0, 2.5, 3.0, 3.5, 4.0],
}

# Run optimization
optimizer = HyperparameterOptimizer(
    symbol='EURUSD',
    timeframe='15m',
    years=2
)

results = optimizer.grid_search(
    param_grid=custom_grid,
    optimization_name="custom_optimization"
)
```

### Custom Objectives

```python
# Define custom optimization objective
def custom_objective(result):
    """Maximize win rate while maintaining positive PnL"""
    if result.final_pnl <= 0:
        return -999  # Penalize negative PnL heavily
    return result.win_rate * (1 + result.final_pnl / 10000)

# Use in analysis (manual sorting)
results.sort(key=custom_objective, reverse=True)
best_by_custom = results[0]
```

### Batch Processing

```python
# Process multiple symbols/timeframes
symbols = ['EURUSD', 'GBPUSD', 'USDJPY']
timeframes = ['15m', '1h']

for symbol in symbols:
    for timeframe in timeframes:
        optimizer = HyperparameterOptimizer(
            symbol=symbol,
            timeframe=timeframe,
            years=2
        )
        
        results = optimizer.grid_search(
            param_grid=OPTIMIZATION_CONFIGS['focused'](),
            optimization_name=f"{symbol}_{timeframe}_focused"
        )
```

## Troubleshooting

### Common Issues

1. **Out of Memory**: Reduce parameter grid size or use random search
2. **Slow Performance**: Check if data caching is working, reduce data years
3. **No Results**: Check data availability, verify symbol/timeframe
4. **Cache Issues**: Clear cache and restart if corrupted

### Error Messages

| Error | Solution |
|-------|----------|
| "No data available" | Check symbol format and data source |
| "Parameter combination already cached" | Normal behavior, using cached result |
| "Backtest failed" | Check strategy parameters and data quality |

## Integration with Main Strategy

The optimized parameters can be directly used in the main strategy:

```python
# Get best parameters from optimization
best_params = {
    'bb_window': 25,
    'bb_std': 2.5,
    'risk_per_position_pct': 1.5,
    'risk_reward_ratio': 3.0,
    # ... other parameters
}

# Update strategy config
from src.strategy_config import StrategyConfig
StrategyConfig.BOLLINGER_BANDS['window'] = best_params['bb_window']
StrategyConfig.BOLLINGER_BANDS['std_dev'] = best_params['bb_std']
StrategyConfig.RISK_MANAGEMENT['risk_per_position_pct'] = best_params['risk_per_position_pct']

# Run main strategy with optimized parameters
python scripts/run_backtest.py
```

## Using Optimized Configurations

After running optimizations, the system generates configuration files in the `results/` folder that can be automatically loaded by `scripts/run_backtest.py`. This eliminates the need for manual parameter updates.

### Automated Configuration Loading

The main strategy script now supports automatic loading of optimized configurations:

```bash
# Use optimized configurations from results folder
python scripts/run_backtest.py --symbol EURUSD --timeframe 5m --preference balanced
python scripts/run_backtest.py --symbol AUDUSD --timeframe 5m --preference pnl
python scripts/run_backtest.py --symbol GBPUSD --timeframe 5m --preference drawdown
```

### Configuration Selection Types

The `--preference` parameter determines which optimization objective to use:

1. **`balanced`**: Best risk-adjusted performance
   - Optimizes for balanced PnL vs. drawdown
   - Uses results from `results/best_configs_balanced.json`
   - Recommended for most traders

2. **`pnl`**: Maximum profit potential
   - Optimizes for highest final PnL
   - Uses results from `results/best_configs_final_pnl.json`
   - Higher risk tolerance required

3. **`drawdown`**: Minimum maximum drawdown
   - Optimizes for lowest maximum drawdown
   - Uses results from `results/best_configs_max_drawdown.json`
   - Most conservative approach

### Automatic Fallback

If no optimized configuration is found for your symbol/timeframe combination, the script automatically falls back to default configuration settings.

### Available Optimized Configurations

Based on the current results folder, optimized configurations are available for:

**Timeframes**: `5m` (primary), some `15m` and `1h`

**Assets**:
- **Forex**: EURUSD, AUDUSD, GBPUSD, EURGBP, EURJPY, NZDUSD, USDCAD, USDCHF, USDJPY, EURCHF, GBPJPY
- **Crypto**: BTCUSD, ETHUSD  
- **Commodities**: GOLD=X, SILVER=X

### Configuration Structure

Each optimized configuration includes:
- **Bollinger Bands**: Window and standard deviation
- **VWAP Bands**: Window and standard deviation  
- **ATR**: Period for volatility calculation
- **Risk Management**: Position size, stop loss, and risk/reward ratio
- **Strategy Behavior**: Reversal requirements and regime filtering
- **Performance Metrics**: Expected results from optimization

This allows you to compare expected optimization results with actual backtest performance, ensuring configuration consistency.

## Future Enhancements

Planned improvements to the optimization system:

- [ ] Parallel processing support for faster optimization
- [ ] Walk-forward analysis for robustness testing
- [ ] Multi-objective optimization (Pareto optimization)
- [ ] Genetic algorithm implementation
- [ ] Bayesian optimization for efficient parameter search
- [ ] Integration with machine learning models
- [ ] Real-time optimization monitoring dashboard
- [ ] Automated parameter validation and bounds checking

---

For more examples and detailed usage, see:
- `examples/optimization_examples.py` - Interactive examples
- `src/optimization_configs.py` - All available configurations
- `src/hyperparameter_optimizer.py` - Core optimization code

## Optimization Grid Comparison

### Focused vs. Balanced Grid Search

The two most commonly used optimization grids serve different purposes:

#### Focused Grid Search
- **Primary Goal**: Maximize final PnL
- **Parameter Range**: Broader risk parameters
- **Risk Settings**: More aggressive
- **Best For**: Traders seeking maximum returns who can tolerate higher drawdowns
- **Parameter Focus**:
  - Wider range of risk percentages (1.0% - 2.0%)
  - Moderate stop loss settings
  - Various risk/reward ratios

#### Balanced Grid Search
- **Primary Goal**: Balance between PnL and drawdown
- **Parameter Range**: More conservative risk parameters
- **Risk Settings**: Tighter risk controls
- **Best For**: Traders seeking stable, consistent returns with lower drawdowns
- **Parameter Focus**:
  - Lower risk percentages (0.5% - 1.25%)
  - Tighter stop loss settings
  - More stringent market regime filtering
  - Requires reversal confirmation by default

### Key Differences

| Aspect | Focused Grid | Balanced Grid |
|--------|--------------|--------------|
| Risk per position | 1.0% - 2.0% | 0.5% - 1.25% |
| Stop loss ATR multiplier | 1.0 - 1.5 | 0.8 - 1.5 |
| Reversal confirmation | Optional | Required |
| Regime filtering | Moderate | Stricter |
| BB standard deviation | 2.0 - 2.5 | 2.0 - 3.0 |

The balanced grid, when used with the `balanced` optimization objective, produces strategies that maintain good profitability while significantly reducing drawdowns compared to the standard focused optimization.

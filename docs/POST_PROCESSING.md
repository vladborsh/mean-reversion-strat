# Post-Processing and Results Analysis

Complete guide for analyzing batch optimization results and generating PNL visualizations.

> **Related Documentation:**
> - [Hyperparameter Optimization](HYPERPARAMETER_OPTIMIZATION.md) - Running optimization jobs
> - [AWS Batch Setup](AWS_BATCH_SETUP.md) - Distributed optimization on AWS
> - [Performance Changelog](PERFORMANCE_CHANGELOG.md) - Strategy evolution and improvements

## Overview

After running batch optimizations (see [Hyperparameter Optimization](HYPERPARAMETER_OPTIMIZATION.md)), you need to:
1. **Analyze results** - Find best parameter sets per asset and objective
2. **Generate PNL charts** - Visualize equity curves for selected configurations
3. **Validate performance** - Ensure results match optimization metrics

The post-processing scripts in `/post-processing/` automate this workflow.

## Scripts

### 1. analyze_batch_results.py

Analyzes batch optimization results and generates per-asset configurations.

**Features:**
- Loads and combines optimization results from CSV files
- Filters valid results based on minimum trades, win rate, and drawdown
- Finds best configurations by multiple objectives (PnL, win rate, drawdown, balanced)
- Generates JSON configs, CSV summaries, and human-readable reports
- Adds `run_id` from original CSV row number (1-based) to each configuration for tracking

**Usage:**
```bash
# Default usage (processes 'batch-analysis' directory)
python3 post-processing/analyze_batch_results.py

# Custom directories and objectives
python3 post-processing/analyze_batch_results.py \
    --results-dir batch-analysis \
    --output-dir results \
    --objectives final_pnl win_rate balanced max_drawdown \
    --min-trades 10
```

**Parameters:**
- `--results-dir`: Directory containing optimization CSV files (default: `batch-analysis`)
- `--output-dir`: Output directory for generated configs (default: `results`)
- `--objectives`: List of optimization objectives to analyze (default: all)
- `--min-trades`: Minimum number of trades for valid results (default: 10)

**Outputs:**
- `results/best_configs_{objective}.json` - Full configuration with metadata
- `results/best_configs_{objective}.csv` - Flat CSV format
- `results/best_configs_{objective}_summary.txt` - Human-readable summary
- `results/portfolio_summary.txt` - Portfolio-level statistics across all objectives
- `results/combined_batch_results.csv` - All optimization results combined

### 2. generate_config_pnl.py

Generates PNL equity curves for optimized configurations by matching orders from optimization runs.

**Features:**
- Loads best configurations from JSON files
- Matches orders to configs by comparing all parameter values
- Aggregates and sorts orders chronologically across assets
- Calculates cumulative PNL over time
- Generates equity curve charts (per-asset and portfolio-level)
- Reuses existing `plot_equity_curve()` from `chart_plotters.py`

**Usage:**
```bash
# Process balanced optimization configs
python3 post-processing/generate_config_pnl.py

# Process specific config file
python3 post-processing/generate_config_pnl.py \
    --config-file results/best_configs_final_pnl.json \
    --orders-dir optimization/orders \
    --output-dir plots/pnl_curves

# Skip portfolio aggregation
python3 post-processing/generate_config_pnl.py --no-portfolio

# Adjust floating-point tolerance for parameter matching
python3 post-processing/generate_config_pnl.py --tolerance 1e-8
```

**Parameters:**
- `--config-file`: Path to best_configs JSON file (default: `results/best_configs_balanced.json`)
- `--orders-dir`: Directory containing order CSV files (default: `optimization/orders`)
- `--output-dir`: Output directory for PNL charts (default: `plots/pnl_curves`)
- `--no-portfolio`: Skip generating aggregated portfolio chart
- `--tolerance`: Floating-point comparison tolerance (default: 1e-9)

**Order Matching:**
The script matches orders to configurations by comparing all parameter values:
- `bb_window`, `bb_std` (Bollinger Bands)
- `vwap_window`, `vwap_std` (VWAP Bands)
- `risk_per_position_pct`, `stop_loss_atr_multiplier`, `risk_reward_ratio` (Risk Management)
- `require_reversal` (Strategy Behavior)

Floating-point comparisons use `np.isclose()` with configurable tolerance.

**Note:** Multiple optimization runs may share the same parameter values (e.g., different `atr_period`), so matched orders may include trades from all runs with those parameters.

**Outputs:**
- `plots/pnl_curves/{asset}_{timeframe}_run{id}_pnl.png` - Individual asset PNL charts
- `plots/pnl_curves/portfolio_{objective}_pnl.png` - Aggregated portfolio PNL chart
- `plots/pnl_curves/pnl_generation_summary_*.json` - Processing statistics

**Chart Statistics:**
Each chart includes:
- Total trades
- Initial/final balance
- Total return percentage
- Maximum drawdown percentage
- Date range

### 3. check_order_files.py

Validation utility to verify order files exist before generating PNL charts.

**Usage:**
```bash
python3 post-processing/check_order_files.py \
    --config-file results/best_configs_balanced.json \
    --orders-dir optimization/orders
```

**Output Example:**
```
✅ run_id= 1 | BTCUSD_5m    | Found: BTCUSD_5m_balanced_orders.csv
❌ run_id= 2 | ETHUSD_15m   | Missing order file

Summary:
  ✅ Found: 15
  ❌ Missing: 3
```

### 4. run_pnl_workflow.sh

Automated workflow script for complete post-processing pipeline.

**Usage:**
```bash
./post-processing/run_pnl_workflow.sh
```

**Steps:**
1. Runs `analyze_batch_results.py` to generate best configs for all objectives
2. Runs `generate_config_pnl.py` for each objective (balanced, final_pnl, win_rate, max_drawdown)
3. Generates individual and portfolio PNL charts for all objectives

## Complete Workflow

### Step 1: Run Optimizations

First, run batch optimizations as described in [Hyperparameter Optimization](HYPERPARAMETER_OPTIMIZATION.md):

```bash
# Run grid search for multiple assets
python3 optimize_strategy.py --mode grid_search_balanced \
    --assets BTCUSD ETHUSD EURUSD \
    --timeframe 5m
```

Or use AWS Batch for distributed optimization (see [AWS Batch Setup](AWS_BATCH_SETUP.md)).

### Step 2: Collect Results

Download results from AWS S3 or collect from local `optimization/results/`:

```bash
# If using AWS Batch
aws s3 sync s3://your-bucket/optimization/results/ ./batch-analysis/
```

### Step 3: Analyze Results

Process optimization results and generate best configs:

```bash
python3 post-processing/analyze_batch_results.py \
    --results-dir batch-analysis \
    --output-dir results \
    --objectives balanced final_pnl win_rate max_drawdown
```

**Output:**
```
🚀 Starting batch results analysis...
📁 Results directory: batch-analysis
📁 Output directory: results

Found 24 CSV result files
📊 Total results loaded: 9600

🔍 Filtering results (min_trades=10, min_win_rate=15.0%, max_drawdown=50.0%)
📊 Remaining: 8240 valid results

🎯 Finding best configurations by balanced
BTCUSD_5m    | PnL: $20,984 | Trades: 351 | WR: 32.5% | Sharpe: 0.05 | DD: 6.5%
ETHUSD_5m    | PnL: $55,868 | Trades: 485 | WR: 34.0% | Sharpe: 0.08 | DD: 10.9%
...

✅ Found 8 best configurations
✅ Strategy configurations saved to results/best_configs_balanced.json
```

### Step 4: Validate Order Files

Check that order files exist for all configurations:

```bash
python3 post-processing/check_order_files.py
```

### Step 5: Generate PNL Charts

Generate equity curves for selected configurations:

```bash
# Process balanced configs
python3 post-processing/generate_config_pnl.py \
    --config-file results/best_configs_balanced.json

# Or use automated workflow for all objectives
./post-processing/run_pnl_workflow.sh
```

**Output:**
```
🚀 Processing configurations from best_configs_balanced.json
📊 Found 8 configurations

Processing: BTCUSD_5m (run_id: 99)
📂 Loading orders from BTCUSD_5m_balanced_orders.csv
✅ Matched 702 orders to configuration
📈 Generated PNL chart: plots/pnl_curves/BTCUSD_5m_run99_pnl.png
   Trades: 702
   Return: 34.43%
   Max DD: -9.06%
...

📈 Generated portfolio PNL chart: plots/pnl_curves/portfolio_balanced_pnl.png
   Assets: 8
   Trades: 4415
   Return: 368.91%
   Max DD: -22.63%

✅ Successful: 8
❌ Failed: 0
```

### Step 6: Review Results

View generated charts and summaries:

```bash
# View portfolio chart
open plots/pnl_curves/portfolio_balanced_pnl.png

# View individual asset charts
open plots/pnl_curves/BTCUSD_5m_run99_pnl.png

# Read human-readable summary
cat results/best_configs_balanced_summary.txt

# Check processing statistics
cat plots/pnl_curves/pnl_generation_summary_best_configs_balanced.json
```

## Configuration Structure

### Best Configs JSON Format

```json
{
  "BTCUSD_5m": {
    "ASSET_INFO": {
      "symbol": "BTCUSD",
      "timeframe": "5m",
      "optimization_type": "balanced",
      "optimization_date": "20251217",
      "selected_by": "balanced"
    },
    "BOLLINGER_BANDS": {
      "window": 20,
      "std_dev": 2.0
    },
    "VWAP_BANDS": {
      "window": 25,
      "std_dev": 2.0
    },
    "ATR": {
      "period": 14
    },
    "RISK_MANAGEMENT": {
      "risk_per_position_pct": 0.5,
      "stop_loss_atr_multiplier": 1.0,
      "risk_reward_ratio": 2.0
    },
    "STRATEGY_BEHAVIOR": {
      "require_reversal": false,
      "regime_min_score": 60
    },
    "PERFORMANCE_METRICS": {
      "final_pnl": 20984.0,
      "total_trades": 351,
      "win_rate": 32.5,
      "sharpe_ratio": 0.05,
      "max_drawdown": 6.5,
      "execution_time": 45.2
    },
    "METADATA": {
      "source_file": "BTCUSD_5m_grid_search_balanced_20251211_160815.csv",
      "generated_at": "2025-12-17T16:30:00",
      "run_id": 99
    }
  }
}
```

### Best Configs CSV Format

```csv
run_id,asset,symbol,timeframe,final_pnl,total_trades,win_rate,sharpe_ratio,max_drawdown,bb_window,bb_std,vwap_window,vwap_std,risk_per_position_pct,stop_loss_atr_multiplier,risk_reward_ratio,require_reversal,regime_min_score
99,BTCUSD_5m,BTCUSD,5m,20984.0,351,32.5,0.05,6.5,20,2.0,25,2.0,0.5,1.0,2.0,False,60
```

### Order File Structure

Orders CSV files must have these columns:
- `optimization_run` - Run identifier for matching
- `asset`, `timeframe` - Asset identification
- `date`, `time` - For chronological sorting
- `pnl` - Profit/loss per trade
- `deposit_before_trade`, `deposit_after_trade` - Account balances
- `bb_window`, `bb_std`, `vwap_window`, `vwap_std` - Parameter values for matching
- `risk_per_position_pct`, `stop_loss_atr_multiplier`, `risk_reward_ratio_param` - Risk parameters
- `require_reversal` - Strategy behavior flag

## Optimization Objectives

### 1. Balanced (Recommended)

Optimizes for a combination of profitability and risk:
```python
balanced_score = 0.6 * normalized_pnl + 0.4 * (1 - normalized_drawdown)
```

Use when: You want stable returns with controlled drawdowns.

### 2. Final PnL

Optimizes purely for maximum profitability.

Use when: Return is the primary goal and drawdown is less critical.

### 3. Win Rate

Optimizes for highest percentage of winning trades (with minimum profitability threshold).

Use when: Trade consistency and psychological comfort are important.

### 4. Max Drawdown

Optimizes for lowest maximum drawdown (minimizes worst-case loss).

Use when: Capital preservation and risk minimization are priorities.

## Troubleshooting

### "No order file found"

**Problem:** Order files don't exist in `optimization/orders/` for some configs.

**Solutions:**
- Verify order files exist with pattern: `{symbol}_{timeframe}_*_orders.csv`
- Example: `BTCUSD_5m_balanced_orders.csv`
- Check that optimization runs completed successfully
- Use `check_order_files.py` to identify missing files

### "No matching orders found"

**Problem:** Parameter values don't match between config and orders.

**Solutions:**
- Parameter values must exactly match (within tolerance)
- Adjust `--tolerance` parameter (e.g., `--tolerance 1e-8`)
- Verify optimization run used same parameter values
- Check for parameter precision issues in CSV files

### "No valid data remaining"

**Problem:** All results filtered out due to quality thresholds.

**Solutions:**
- Check `--min-trades` threshold (default: 10)
- Review filter criteria:
  - `min_win_rate`: default 15%
  - `max_drawdown`: default 50%
  - Must have positive PnL
- Lower thresholds if optimization results are genuinely poor
- Re-run optimizations with adjusted parameter ranges

### "KeyError: 'run_id'"

**Problem:** Config file doesn't have run_id (old format).

**Solutions:**
- Re-run `analyze_batch_results.py` to regenerate configs with run_id
- The script was updated to add run_id tracking

### Mismatch between expected and actual trades

**Problem:** Config shows different trade count than matched orders.

**Explanation:**
- Multiple optimization runs may share same parameter values
- Orders matched by parameters, not run_id
- This is expected behavior when parameter sets overlap

**Validation:**
- Verify PnL is positive and matches expectations
- Check that return percentage is reasonable
- Review parameter values in config vs orders

## Performance Analysis

### Reading Portfolio Summary

```bash
cat results/portfolio_summary.txt
```

Example output:
```
BALANCED OPTIMIZATION
----------------------------------------
Assets: 8
Total Portfolio PnL: $209,262.00
Average Win Rate: 36.2%
Average Sharpe Ratio: 0.07
Average Max Drawdown: 9.1%
Total Trades: 2075

Top 5 Performers:
1. ETHUSD_5m    | PnL: $ 55,868 | WR:  34.0% | Sharpe:  0.08 | DD:  10.9%
2. SILVER_5m    | PnL: $ 44,869 | WR:  41.1% | Sharpe:  0.11 | DD:   6.8%
3. AUDUSD_5m    | PnL: $ 22,378 | WR:  42.6% | Sharpe:  0.11 | DD:   3.4%
4. GBPUSD_5m    | PnL: $ 21,910 | WR:  38.7% | Sharpe:  0.06 | DD:   7.3%
5. BTCUSD_5m    | PnL: $ 20,984 | WR:  32.5% | Sharpe:  0.05 | DD:   6.5%
```

### Interpreting PNL Charts

**Equity Curve Characteristics:**
- **Steady upward trend** - Consistent profitability
- **Flat periods** - No trades or break-even periods
- **Sharp drops** - Losing streaks or drawdown events
- **Recovery patterns** - Strategy's resilience after losses

**Key Metrics:**
- **Total Return %** - Overall profitability
- **Max Drawdown %** - Worst peak-to-trough decline
- **Trade Count** - Strategy activity level
- **Date Range** - Coverage period

### Comparing Objectives

Generate charts for all objectives to compare approaches:

```bash
# Generate all
./post-processing/run_pnl_workflow.sh

# Compare portfolios
open plots/pnl_curves/balanced/portfolio_balanced_pnl.png
open plots/pnl_curves/final_pnl/portfolio_final_pnl_pnl.png
open plots/pnl_curves/win_rate/portfolio_win_rate_pnl.png
open plots/pnl_curves/max_drawdown/portfolio_max_drawdown_pnl.png
```

## Integration with Live Trading

After selecting best configurations, deploy them for live trading:

1. **Export Configs**: Best configs JSON files can be used as strategy inputs

2. **Update Strategy**: Copy parameter values to your live strategy configuration

3. **Monitor Performance**: Use [Live Performance Verifier](LIVE_PERFORMANCE_VERIFIER.md) to track live vs backtest results

4. **Set Alerts**: Configure [Telegram Bot](TELEGRAM_BOT_INTEGRATION.md) for real-time signal notifications

See [Strategy Documentation](STRATEGY_DOCUMENTATION.md) for deployment details.

## Dependencies

Required Python packages:
- `pandas` - Data manipulation
- `numpy` - Numerical operations
- `matplotlib` - Charting (via `chart_plotters.py`)

All dependencies are already included in `requirements.txt`.

## Related Documentation

- **[Hyperparameter Optimization](HYPERPARAMETER_OPTIMIZATION.md)** - Running optimization jobs
- **[AWS Batch Setup](AWS_BATCH_SETUP.md)** - Distributed optimization
- **[AWS Batch Scripts](AWS_BATCH_SCRIPTS.md)** - Job submission and monitoring
- **[Performance Changelog](PERFORMANCE_CHANGELOG.md)** - Strategy evolution
- **[Live Performance Verifier](LIVE_PERFORMANCE_VERIFIER.md)** - Historical analysis
- **[Strategy Documentation](STRATEGY_DOCUMENTATION.md)** - Strategy implementation
- **[Signal Chart Generation](SIGNAL_CHART_GENERATION.md)** - Visualizing trade signals

## Script Reference

Located in `/post-processing/`:
- `analyze_batch_results.py` - Results analysis and config generation
- `generate_config_pnl.py` - PNL chart generation
- `check_order_files.py` - Validation utility
- `run_pnl_workflow.sh` - Automated workflow
- `asset_config_manager.py` - Configuration management utility

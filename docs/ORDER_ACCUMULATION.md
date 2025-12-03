# Order Accumulation During Optimization

## Overview

The optimization system now automatically collects and saves orders from all optimization runs to CSV files for future research and analysis.

## Key Features

- **Automatic Collection**: Orders are automatically collected from every optimization run
- **Immediate Saving**: Orders are saved to CSV after each optimization run (no buffering)
- **Single File Per Asset**: All orders for a specific asset/timeframe combination are saved to one CSV file
- **Transport Support**: Supports both local filesystem and S3 storage
- **Comprehensive Data**: Includes order details, trade outcomes, and optimization parameters

## File Structure

Orders are saved to CSV files with the following naming convention:
```
optimization/orders/{ASSET}_{TIMEFRAME}_{OPTIMIZATION_TYPE}_orders.csv
```

Examples:
- `optimization/orders/EURUSDX_15m_balanced_orders.csv`
- `optimization/orders/EURUSDX_15m_focused_orders.csv`
- `optimization/orders/GBPUSDX_1h_balanced_orders.csv`
- `optimization/orders/GBPUSDX_1h_focused_orders.csv`
- `optimization/orders/BTCUSDT_4h_risk_orders.csv`

Note: For backward compatibility, if no optimization type is specified, the old naming convention is used:
- `optimization/orders/EURUSDX_15m_orders.csv`

## CSV Columns

The CSV files contain the following columns:

### Order Tracking
- `optimization_run`: Optimization run number
- `asset`: Trading symbol (e.g., EURUSD)
- `timeframe`: Trading timeframe (e.g., 15m, 1h)

### Order Timing
- `date`: Order entry date
- `time`: Order entry time  
- `exit_date`: Order exit date
- `exit_time`: Order exit time

### Order Details
- `direction`: LONG or SHORT
- `lot_size`: Position size
- `entry_price`: Entry price
- `stop_loss`: Stop loss price
- `take_profit`: Take profit price
- `exit_price`: Actual exit price

### Trade Outcome
- `win_loss`: WIN, LOSS, or BREAK_EVEN
- `pnl`: Profit/Loss amount
- `exit_reason`: stop_loss, take_profit, lifetime_expired, etc.

### Risk Management
- `atr_value`: ATR value at order time
- `risk_amount`: Risk amount in currency
- `reward_amount`: Potential reward amount
- `risk_reward_ratio`: Risk/reward ratio
- `account_risk_pct`: Account risk percentage

### Account Tracking
- `deposit_before_trade`: Account value before trade
- `deposit_after_trade`: Account value after trade
- `deposit_change`: Net change in account value

### Strategy Parameters
- `bb_window`: Bollinger Bands period
- `bb_std`: Bollinger Bands standard deviation
- `vwap_window`: VWAP approximation period
- `vwap_std`: VWAP bands standard deviation
- `risk_per_position_pct`: Risk per position percentage
- `stop_loss_atr_multiplier`: Stop loss ATR multiplier
- `risk_reward_ratio_param`: Risk/reward ratio parameter

### Additional Info
- `order_id`: Unique order identifier
- `reason`: Entry reason description

## Usage Examples

### Running Optimization with Order Collection

```bash
# Basic optimization (orders saved automatically)
python optimize_strategy.py --quick-test

# Grid search with specific asset
python optimize_strategy.py --grid-search focused --symbol GBPUSD --timeframe 1h

# Random search with S3 storage
python optimize_strategy.py --random-search 50 --log-transport s3
```

### Analyzing Saved Orders

```python
import pandas as pd

# Load orders for analysis (with optimization type)
df = pd.read_csv('optimization/orders/EURUSDX_15m_focused_orders.csv')

# Basic statistics
print(f"Total orders: {len(df)}")
print(f"Optimization runs: {df['optimization_run'].nunique()}")
print(f"Win rate: {(df['win_loss'] == 'WIN').mean():.2%}")

# Performance by optimization run
run_performance = df.groupby('optimization_run').agg({
    'pnl': 'sum',
    'win_loss': lambda x: (x == 'WIN').mean()
}).round(2)
print(run_performance)

# Best performing parameter combinations
winners = df[df['win_loss'] == 'WIN']
best_params = winners.groupby(['bb_window', 'risk_per_position_pct']).size().sort_values(ascending=False)
print(best_params.head())

# Compare different optimization types
balanced_df = pd.read_csv('optimization/orders/EURUSDX_15m_balanced_orders.csv')
focused_df = pd.read_csv('optimization/orders/EURUSDX_15m_focused_orders.csv')

print("Balanced vs Focused Performance:")
print(f"Balanced win rate: {(balanced_df['win_loss'] == 'WIN').mean():.2%}")
print(f"Focused win rate: {(focused_df['win_loss'] == 'WIN').mean():.2%}")
```

### Research Applications

1. **Parameter Sensitivity Analysis**: Compare win rates across different parameter values
2. **Market Condition Analysis**: Analyze performance in different market conditions
3. **Risk Management Validation**: Verify that stop losses and take profits work as expected
4. **Entry/Exit Timing**: Study optimal entry and exit times
5. **Strategy Robustness**: Test strategy performance across different optimization runs
6. **Optimization Type Comparison**: Compare performance between balanced, focused, and risk-based optimizations

## Transport Configuration

### Local Storage (Default)
```python
# Orders saved to local optimization/orders/ directory
python optimize_strategy.py --quick-test --log-transport local
```

### S3 Storage
```python
# Orders saved to S3 bucket (requires AWS credentials)
python optimize_strategy.py --quick-test --log-transport s3
```

## Implementation Details

### Automatic Collection
- Orders are collected automatically during each optimization run
- No manual intervention required
- Works with both grid search and random search optimization

### Immediate Saving
- Orders are saved immediately after each optimization run completes
- No buffering or batch saving
- Prevents data loss if optimization is interrupted

### Data Consistency
- Orders from multiple optimization runs are appended to the same file
- Data is sorted by optimization run, date, and time for consistency
- Duplicate protection through unique order IDs

### Error Handling
- Robust error handling for file I/O operations
- Graceful degradation if order saving fails
- Detailed logging for troubleshooting

## File Management

### Viewing Current Files
```bash
# List all order files (now organized by optimization type)
ls optimization/orders/

# Check file sizes
ls -lh optimization/orders/

# View recent orders from focused optimization
tail -n 10 optimization/orders/EURUSDX_15m_focused_orders.csv

# View recent orders from balanced optimization
tail -n 10 optimization/orders/EURUSDX_15m_balanced_orders.csv

# Compare file sizes between optimization types
ls -lh optimization/orders/*focused* optimization/orders/*balanced*
```

### Data Backup
```bash
# Backup order data
cp -r optimization/orders/ backup_orders_$(date +%Y%m%d)/

# Compress for archival
tar -czf orders_backup_$(date +%Y%m%d).tar.gz optimization/orders/
```

## Best Practices

1. **Regular Review**: Periodically review order files for insights
2. **Data Backup**: Backup order data regularly, especially before major changes
3. **File Management**: Monitor file sizes and clean up old data if needed
4. **Analysis Scripts**: Create reusable analysis scripts for common research tasks
5. **Version Control**: Consider version controlling analysis scripts (but not order data files)

## Troubleshooting

### No Orders Generated
- Check that the strategy actually generates orders during optimization
- Verify that the optimization parameters allow for valid entry signals
- Check strategy logs for any errors

### Empty CSV Files
- Ensure optimization runs complete successfully
- Check for file permission issues
- Verify transport configuration (local vs S3)

### Missing Columns
- Update to latest version of order accumulator
- Check for any custom modifications to the strategy class

### Transport Errors
- For S3: Verify AWS credentials and bucket permissions
- For local: Check directory permissions and disk space

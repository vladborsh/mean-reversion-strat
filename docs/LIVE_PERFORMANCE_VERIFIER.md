# Live Performance Verifier

## Overview

The Live Performance Verifier (`live_performance_verifier.py`) is a CLI tool that analyzes how the live trading strategy scheduler would have performed over a specified historical period. It runs real backtests using the same `MeanReversionStrategy` that the live scheduler uses, providing accurate performance metrics for verification and analysis.

## Key Features

- **Real Strategy Simulation**: Uses the actual `MeanReversionStrategy` class from the live scheduler
- **Complete Backtesting**: Runs full historical backtests, not just signal detection
- **Multiple Time Periods**: Analyze 1 week, 3 weeks, months, or custom periods
- **Comprehensive Metrics**: Win rate, P&L, drawdown, trade outcomes
- **Symbol Filtering**: Analyze specific symbols or all configured assets
- **Trade Details**: View complete trade history with entry/exit prices and outcomes
- **Order Tracking Charts**: Generate visual charts showing all orders with SL/TP levels
- **P&L Curve Visualization**: Generate cumulative P&L progression charts
- **Export Options**: Save results to JSON or CSV for further analysis
- **Error Handling**: Graceful handling of unavailable symbols or data issues

## Usage

### Basic Commands

```bash
# Analyze last 3 weeks (default)
python live_performance_verifier.py

# Analyze specific time period
python live_performance_verifier.py --period 1w    # 1 week
python live_performance_verifier.py --period 21d   # 21 days
python live_performance_verifier.py --period 2m    # 2 months

# Analyze specific symbols only
python live_performance_verifier.py --symbols EURUSD GBPUSD

# Show detailed trade information
python live_performance_verifier.py --detailed

# Generate P&L curve chart
python live_performance_verifier.py --chart

# Generate order tracking charts with SL/TP levels
python live_performance_verifier.py --save-order-charts

# Generate both P&L curve and order charts
python live_performance_verifier.py --chart --save-order-charts

# Export results
python live_performance_verifier.py --export json --output results.json
python live_performance_verifier.py --export csv

# Enable verbose logging
python live_performance_verifier.py --verbose
```

### Command Line Options

| Option | Description | Examples |
|--------|-------------|----------|
| `--period`, `-p` | Analysis period | `3w`, `21d`, `1m` |
| `--symbols`, `-s` | Specific symbols to analyze | `EURUSD GBPUSD` |
| `--config` | Configuration file path | `assets_config_wr45.json` |
| `--detailed`, `-d` | Show detailed trade analysis | |
| `--chart`, `-c` | Generate P&L curve chart | |
| `--save-order-charts` | Generate order tracking charts with SL/TP levels | |
| `--export` | Export format | `json`, `csv` |
| `--output`, `-o` | Output filename | `results.json` |
| `--verbose`, `-v` | Enable verbose logging | |

## Understanding the Results

The tool provides three main output sections:

### 1. Summary Metrics

```
SUMMARY METRICS:
+-------------------------+-------------+
| Metric                  | Value       |
+=========================+=============+
| Total Symbols Analyzed  | 3/3         |
| Total Signals Generated | 11          |
| Total Trades Executed   | 11          |
| Successful Orders       | 11 (100.0%) |
| Failed Orders           | 0           |
| Winning Trades          | 4/11        |
| Overall Win Rate        | 36.4%       |
| Total P&L               | $10,386.18  |
| Max Drawdown            | 10.1%       |
+-------------------------+-------------+
```

**Key Metrics Explained:**
- **Total Signals Generated**: Number of trading signals created by the strategy
- **Successful Orders**: Orders that were executed (vs failed due to market conditions)
- **Winning Trades**: Trades that ended with positive P&L
- **Overall Win Rate**: Percentage of profitable trades
- **Total P&L**: Net profit/loss from all trades combined
- **Max Drawdown**: Largest peak-to-trough decline in account value (%)

### 2. Per-Symbol Performance

```
PER-SYMBOL PERFORMANCE:
+----------+----------+-----------+----------+------------+-----------+----------+
| Status   | Symbol   |   Signals |   Trades | Win Rate   | P&L       | Max DD   |
+==========+==========+===========+==========+============+===========+==========+
| ✅        | NZDUSDX  |         4 |        4 | 25.0%      | $707.54   | 6.6%     |
| ✅        | EURGBPX  |         4 |        4 | 50.0%      | $6,915.84 | 10.1%    |
| ✅        | AUDUSDX  |         3 |        3 | 33.3%      | $2,762.80 | 3.4%     |
+----------+----------+-----------+----------+------------+-----------+----------+
```

**Status Indicators:**
- ✅ **Analyzed**: Symbol successfully analyzed
- ❌ **Data Unavailable**: Symbol data could not be fetched (may not be available on Capital.com)
- ❌ **Analysis Failed**: Error occurred during analysis

### 3. All Executed Trades

```
ALL EXECUTED TRADES:

Trade Statistics:
  Total Trades: 11
  Winners: 4 | Losers: 7
  Take Profits: 3 | Stop Losses: 7 | Timeouts: 0
  Average Win: $6,123.73
  Average Loss: $-2,001.08
  Total P&L: $10,487.34

+----------+--------------+-------------+--------+---------+---------+------------+-----------+
| Symbol   | Entry Time   | Exit Time   | Type   |   Entry |    Exit | P&L        | Outcome   |
+==========+==============+=============+========+=========+=========+============+===========+
| AUDUSDX  | 09-04 09:20  | 09-04 00:00 | BUY    | 0.65216 | 0.65197 | $-2,000.00 | SL        |
| EURGBPX  | 09-04 11:35  | 09-04 00:00 | SELL   | 0.86686 | 0.86607 | $7,000.00  | TP        |
| NZDUSDX  | 09-08 16:35  | 09-08 00:00 | BUY    | 0.59316 | 0.59297 | $-2,000.00 | SL        |
+----------+--------------+-------------+--------+---------+---------+------------+-----------+
```

**Trade Outcome Codes:**
- **TP**: Take Profit - Trade closed at profit target
- **SL**: Stop Loss - Trade closed at stop loss level
- **TO**: Timeout - Trade closed due to time limit
- **??**: Unknown - Exit reason unclear

**Column Explanations:**
- **Symbol**: Trading pair (NZDUSDX = NZD/USD)
- **Entry/Exit Time**: When trade was opened and closed
- **Type**: BUY (long) or SELL (short) position
- **Entry/Exit**: Exact entry and exit prices
- **P&L**: Profit/Loss in USD (green = profit, red = loss)
- **Outcome**: How the trade ended

## Visualization Outputs

The tool can generate two types of visual outputs to help analyze strategy performance:

### 1. P&L Curve Chart (`--chart`)

Generated with the `--chart` flag, this shows:
- **Cumulative P&L progression** over all trades
- **Peak and trough markers** highlighting best and worst performance points
- **Final P&L and total trade count** in the title
- **Professional styling** with clear axis labels and gridlines

Saved to: `plots/pnl_curve_[period]_[timestamp].png`

### 2. Order Tracking Charts (`--save-order-charts`)

Generated with the `--save-order-charts` flag, this creates visual charts for each symbol showing:
- **Clean price lines** (black) showing market movement around each order
- **Entry level** (solid line) marking exact entry price
- **Stop Loss level** (dashed red line) showing SL price
- **Take Profit level** (dashed blue line) showing TP price
- **Entry point marker** (colored dot) at the exact entry time
- **Trade outcome indicator** (top-left corner) showing if SL/TP was hit with P&L

**Chart Features:**
- All orders for each symbol combined in a single grid image
- 50 candles of price data around each entry point for context
- Clean visualization without technical indicators
- Timezone-aware plotting ensuring accurate entry point placement

Saved to: `plots/orders_[period]_[timestamp]/[timestamp]/all_orders.png`

**Example Usage:**
```bash
# Generate both chart types
python live_performance_verifier.py --period 1w --chart --save-order-charts

# Generate only order tracking charts
python live_performance_verifier.py --period 3d --symbols EURUSD --save-order-charts
```

## How It Works

### Technical Implementation

1. **Real Strategy Execution**: The tool uses the actual `MeanReversionStrategy` class that powers the live scheduler, ensuring 100% accuracy in simulation

2. **Complete Backtesting**: Unlike signal-only detection, this runs full backtests using the `run_backtest()` function, simulating:
   - Order placement and execution
   - Stop loss and take profit triggers
   - Risk management and position sizing
   - Complete trade lifecycle from entry to exit

3. **Historical Data**: Fetches real market data from Capital.com for the specified time period, ensuring realistic market conditions

4. **Performance Calculation**: Extracts real trade outcomes from the backtest engine, including:
   - Actual entry/exit prices from trade execution
   - Real P&L from completed trades
   - Accurate drawdown from equity curve tracking
   - True win/loss statistics from trade outcomes

### Risk Management Validation

The tool validates the strategy's key risk management features:

- **Risk per Position**: Each trade risks exactly 2% of account balance
- **Stop Loss**: Set at 1.0x ATR distance from entry
- **Take Profit**: Set at 3.5x stop loss distance (3.5:1 risk/reward ratio)
- **Position Sizing**: Dynamically calculated based on stop loss distance

### Data Requirements

- **Capital.com API Access**: Requires valid credentials in `.env` file
- **Historical Data**: Fetches sufficient data for technical indicators (adds buffer)
- **Fresh Data**: Disables caching to ensure up-to-date market conditions

## Examples

### Example 1: Quick 1-Week Analysis

```bash
python live_performance_verifier.py --period 1w --symbols EURUSD
```

Analyzes EUR/USD performance over the last week.

### Example 2: Detailed 3-Week Report with Export

```bash
python live_performance_verifier.py --period 3w --detailed --export json --output weekly_report.json
```

Generates a comprehensive 3-week analysis with detailed trade information and exports to JSON.

### Example 3: Multi-Symbol Comparison

```bash
python live_performance_verifier.py --period 2w --symbols EURUSD GBPUSD AUDUSD --detailed
```

Compares performance across major currency pairs over 2 weeks.

### Example 4: Visual Analysis with Charts

```bash
python live_performance_verifier.py --period 1w --chart --save-order-charts
```

Generates both P&L curve and order tracking charts for complete visual analysis.

### Example 5: Order-Only Visualization

```bash
python live_performance_verifier.py --period 3d --symbols NZDUSD --save-order-charts --detailed
```

Focuses on order visualization with detailed trade analysis for a specific symbol over 3 days.

## Interpreting Results

### Understanding Low Win Rates with Positive P&L

It's common to see results like:
- **Win Rate**: 30-40%
- **Total P&L**: Positive
- **Drawdown**: 8-12%

This is expected behavior for mean reversion strategies because:

1. **Asymmetric Risk/Reward**: 3.5:1 ratio means winning trades are 3.5x larger than losing trades
2. **Mathematical Edge**: Strategy only needs >22.2% win rate to be profitable with 3.5:1 R/R
3. **Controlled Losses**: Each loss is limited to ~2% of account (stop loss)
4. **Large Wins**: Successful reversals capture 7%+ gains (take profit)

### Healthy Strategy Characteristics

**Good Performance Indicators:**
- Win rate above 25% (with 3.5:1 R/R)
- Average win significantly larger than average loss
- Max drawdown under 15%
- Consistent trade execution (high successful order rate)

**Warning Signs:**
- Win rate below 20%
- Average loss larger than expected (poor stop loss execution)
- Excessive drawdown (>20%)
- High failed order rate

## Troubleshooting

### Common Issues

**"Missing Capital.com credentials"**
- Ensure `.env` file contains `CAPITAL_COM_API_KEY`, `CAPITAL_COM_PASSWORD`, and `CAPITAL_COM_IDENTIFIER`

**"Symbol not available on Capital.com"**
- Some symbols may not be offered by Capital.com
- Check symbol mapping in `SymbolConfigManager.convert_symbol_for_fetching()`

**"No trades executed during period"**
- Try longer time period (`--period 3w` instead of `--period 1w`)
- Market may have been less volatile during selected period
- Check with `--verbose` flag for detailed analysis

**Analysis taking too long**
- Reduce number of symbols with `--symbols` filter
- Use shorter time periods for initial testing
- Consider that fresh data fetching takes time (no caching)

### Performance Tips

- **Filter symbols** for faster analysis: `--symbols EURUSD GBPUSD`
- **Use appropriate periods**: 1-2 weeks for quick checks, 3+ weeks for comprehensive analysis
- **Enable verbose mode** for debugging: `--verbose`
- **Export results** for detailed offline analysis: `--export json`

## Integration with Live Trading

This tool is designed to validate the live scheduler's performance by using identical:
- Strategy logic (`MeanReversionStrategy`)
- Risk management parameters
- Technical indicators and settings
- Position sizing calculations

Results should closely match what the live scheduler would achieve during the same period, making it an excellent tool for:
- Strategy validation before live deployment
- Performance monitoring and analysis
- Risk assessment and optimization
- Historical performance verification
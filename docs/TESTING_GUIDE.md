# Testing Custom Strategies

This directory contains test scripts for validating custom trading strategies with historical data.

## Quick Start - Unified Test Script

### **Single Test Script for All Strategies**

**File:** `tests/test_custom_strategy.py`

A universal test script that works with **any** custom detector configured in your assets config file.

#### Usage:
```bash
# Test any asset from your config
python tests/test_custom_strategy.py --asset GOLD --start 2025-12-15 --end 2025-12-24

# Export signals to CSV
python tests/test_custom_strategy.py --asset BTC --start 2025-12-01 --end 2025-12-24 --export btc_signals.csv

# Save full report to file
python tests/test_custom_strategy.py --asset DE40 --start 2024-12-01 --end 2024-12-20 --report dax_report.txt

# Use custom config file
python tests/test_custom_strategy.py --asset GOLD --start 2025-12-01 --end 2025-12-24 --config my_config.json
```

#### Command-Line Arguments

| Argument | Required | Default | Description |
|----------|----------|---------|-------------|
| `--asset` | Yes | - | Asset symbol (e.g., GOLD, BTC, DE40) |
| `--start` | Yes | - | Start date in YYYY-MM-DD format |
| `--end` | Yes | - | End date in YYYY-MM-DD format |
| `--config` | No | assets_config_custom_strategies.json | Path to configuration file |
| `--export` | No | - | Export signals to CSV file path |
| `--report` | No | - | Save report to text file path |

#### Key Features:
- ✅ **Universal**: Works with any detector in your config
- ✅ **Auto-detection**: Automatically determines strategy type and parameters
- ✅ **Flexible exports**: CSV signals and text reports
- ✅ **Smart defaults**: Adapts minimum candle requirements per strategy
- ✅ **Error handling**: Comprehensive validation and logging

---

## Supported Strategies

The unified test script automatically supports all strategies configured in `assets_config_custom_strategies.json`:

### 1. VWAP Mean Reversion (GOLD & BTC)
- **Indicator**: VWAP with configurable standard deviation bands (daily reset)
- **GOLD Signal Window**: 13:00-15:00 UTC
- **BTC Signal Window**: 14:00-16:00 UTC
- **Long Signal**: Price < VWAP lower band + bullish reversal candle + previous candle was bearish
- **Short Signal**: Price > VWAP upper band + bearish reversal candle + previous candle was bullish

### 2. Asia Session Sweep (DE40/DAX)
- **Session**: 03:00-07:00 UTC (Asia trading session)
- **Signal Window**: 08:30-09:30 UTC (European market open)
- **Long Signal**: Price breaks below session low + bullish reversal candle
- **Short Signal**: Price breaks above session high + bearish reversal candle



---

## Prerequisites

### 1. Environment Setup
Create a `.env` file in the project root with your Capital.com credentials:

```bash
# Capital.com API credentials
CAPITALCOM_API_KEY=your_api_key_here
CAPITALCOM_IDENTIFIER=your_identifier_here
CAPITALCOM_PASSWORD=your_password_here
CAPITALCOM_DEMO=true  # Set to false for live trading
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Configuration File
Ensure your `assets_config_custom_strategies.json` includes the assets you want to test:

```json
{
  "assets": [
    {
      "symbol": "DE40",
      "fetch_symbol": "DE40",
      "timeframe": "5m",
      "strategy": "session_sweep"
    },
    {
      "symbol": "GOLD",
      "fetch_symbol": "GOLD",
      "timeframe": "5m",
      "strategy": "vwap"
    },
    {
      "symbol": "BTC",
      "fetch_symbol": "BTC",
      "timeframe": "5m",
      "strategy": "vwap_btc"
    }
  ],
  "strategies": {
    "session_sweep": {
      "parameters": {
        "session_start": "03:00",
        "session_end": "07:00",
        "signal_window_start": "08:30",
        "signal_window_end": "09:30"
      }
    },
    "vwap": {
      "parameters": {
        "num_std": 1.0,
        "signal_window_start": "13:00",
        "signal_window_end": "15:00",
        "anchor_period": "day"
      }
    },
    "vwap_btc": {
      "parameters": {
        "num_std": 1.0,
        "signal_window_start": "14:00",
        "signal_window_end": "16:00",
        "anchor_period": "day"
      }
    }
  }
}
```

---

## Output

### Console Report
The test script outputs a detailed report to the console including:
- Test period and total candles analyzed
- Asset and strategy information
- Signal summary (long/short/no signal/errors)
- Detailed list of all detected signals with:
  - Timestamp
  - Current price
  - Strategy-specific indicators (session high/low or VWAP bands)
  - Signal reason

### CSV Export
Export signals to CSV for further analysis with columns:
- timestamp
- signal_type (long/short)
- direction (BUY/SELL)
- symbol
- current_price
- Strategy-specific fields (vwap, vwap_upper, vwap_lower, session_high, session_low, etc.)
- reason

### Text Report
Save the full console report to a text file for documentation.

---

## Example Workflows

### Test Recent Trading Week
```bash
# Test any asset for past week
python tests/test_custom_strategy.py --asset GOLD --start 2025-12-18 --end 2025-12-24
python tests/test_custom_strategy.py --asset BTC --start 2025-12-18 --end 2025-12-24 --export btc_week.csv
python tests/test_custom_strategy.py --asset DE40 --start 2024-12-18 --end 2024-12-24 --report dax_week.txt
```

### Test Full Month
```bash
# Test entire December for different assets
python tests/test_custom_strategy.py --asset GOLD --start 2025-12-01 --end 2025-12-31 --report gold_december.txt
python tests/test_custom_strategy.py --asset BTC --start 2025-12-01 --end 2025-12-31 --export btc_december.csv
```

### Compare Different Periods
```bash
# Test GOLD - November vs December
python tests/test_custom_strategy.py --asset GOLD --start 2025-11-01 --end 2025-11-30 --export gold_november.csv
python tests/test_custom_strategy.py --asset GOLD --start 2025-12-01 --end 2025-12-31 --export gold_december.csv

# Test BTC - November vs December
python tests/test_custom_strategy.py --asset BTC --start 2025-11-01 --end 2025-11-30 --export btc_november.csv
python tests/test_custom_strategy.py --asset BTC --start 2025-12-01 --end 2025-12-31 --export btc_december.csv

# Compare CSV files in spreadsheet or Python
```

### Batch Testing Multiple Assets
```bash
# Create a simple bash script
for asset in GOLD BTC DE40; do
  python tests/test_custom_strategy.py --asset $asset --start 2025-12-01 --end 2025-12-24 \
    --export "results/${asset}_signals.csv" \
    --report "results/${asset}_report.txt"
done
```

---

## Troubleshooting

### Error: "Asset {symbol} not found in config"
1. Check symbol name matches exactly (case-sensitive) in your config file
2. Verify the symbol is listed in the "assets" section
3. Use `--config` to specify the correct config file path

### Error: "cannot reindex on an axis with duplicate labels"
This occurs when there are duplicate timestamps in the data. The unified test script automatically handles this, but if you see this error:
1. Check your data fetching logic
2. Ensure timestamps are unique before passing to detector
3. The script uses `drop_duplicates()` to clean data automatically

### Error: "Failed to create Capital.com fetcher"
1. Verify your `.env` file exists in the project root
2. Check that all required credentials are set:
   - `CAPITALCOM_API_KEY`
   - `CAPITALCOM_IDENTIFIER`
   - `CAPITALCOM_PASSWORD`
3. Ensure `CAPITALCOM_DEMO=true` for testing with demo account

### No Signals Detected
1. Verify the date range includes trading days (not weekends/holidays)
2. Check that the signal window aligns with your trading hours
3. Review the "No Signal" reasons in the report
4. Ensure sufficient historical data is available (need full day for VWAP)
5. Check if the strategy's signal window is active during your test period

### Insufficient Data for VWAP
The VWAP detector requires at least 24 hours (288 candles at 5m intervals) of historical data for accurate calculation. Ensure your start date provides enough history.

### Wrong Strategy Being Used
1. Verify the strategy name in your config matches the asset
2. Check that the strategy configuration exists in the "strategies" section
3. Review the console output at startup to confirm which strategy is loaded

---

## Best Practices

1. **Start with Recent Data**: Test with last 1-2 weeks first to validate setup
2. **Use Demo Account**: Always test with `CAPITALCOM_DEMO=true` initially
3. **Export Results**: Save signals to CSV for analysis and record-keeping
4. **Compare Periods**: Test multiple date ranges to validate strategy consistency
5. **Review No-Signals**: Understand why signals aren't generated in certain conditions
6. **Check Time Windows**: Ensure your signal windows align with market activity
7. **Batch Testing**: Use shell scripts to test multiple assets automatically
8. **Version Control**: Save config files and results for reproducibility

---

## Adding New Custom Strategies

To test a new custom strategy:

1. **Create the detector** in `src/bot/custom_scripts/my_detector.py`
2. **Add to config** `assets_config_custom_strategies.json`:
```json
{
  "assets": [
    {
      "symbol": "MYASSET",
      "fetch_symbol": "MYASSET",
      "timeframe": "5m",
      "strategy": "my_strategy"
    }
  ],
  "strategies": {
    "my_strategy": {
      "detector_class": "MyDetector",
      "detector_module": "src.bot.custom_scripts.my_detector",
      "parameters": {
        "param1": "value1",
        "param2": 123
      }
    }
  }
}
```
3. **Test immediately**:
```bash
python tests/test_custom_strategy.py --asset MYASSET --start 2025-12-01 --end 2025-12-24
```

No need to create a new test script - the unified script handles it automatically!



---

## Support & Documentation

For more information:
- **Custom Detectors**: See [CUSTOM_SIGNAL_DETECTORS.md](CUSTOM_SIGNAL_DETECTORS.md)
- **Scheduler Setup**: See [Trading Bot Guide](TRADING_BOT.md)
- **Config Examples**: Check `assets_config_custom_strategies.json`

For issues:
1. Check the troubleshooting section above
2. Review detector implementation in `src/bot/custom_scripts/`
3. Verify configuration in your config file
4. Enable debug logging: `logging.basicConfig(level=logging.DEBUG)`
5. Check Capital.com API connectivity

---

## Summary

The unified test script (`test_custom_strategy.py`) provides:
- ✅ **One script for all strategies**
- ✅ **Simple asset-based testing** (`--asset`)
- ✅ **Automatic strategy detection**
- ✅ **Flexible exports** (CSV + reports)
- ✅ **Easy to extend** (no new scripts needed)
- ✅ **Consistent interface** across all detectors

**Start testing now:**
```bash
python tests/test_custom_strategy.py --asset GOLD --start 2025-12-15 --end 2025-12-24
```

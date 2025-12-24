# Testing Custom Strategies

This directory contains test scripts for validating custom trading strategies with historical data.

## Available Test Scripts

### 1. Asia Session Sweep Strategy (DE40/DAX)
**File:** `tests/test_asia_session_sweep.py`

Tests the Asia session sweep detector on DE40 (DAX Index) using real historical data from Capital.com.

#### Usage:
```bash
# Basic test for date range
python tests/test_asia_session_sweep.py --start 2025-12-15 --end 2025-12-24 --symbol DE40

# Test with custom config
python tests/test_asia_session_sweep.py --start 2025-12-01 --end 2025-12-24 --config my_config.json
```

#### Strategy Details:
- **Session**: 03:00-07:00 UTC (Asia trading session)
- **Signal Window**: 08:30-09:30 UTC (European market open)
- **Long Signal**: Price breaks below session low + bullish reversal candle
- **Short Signal**: Price breaks above session high + bearish reversal candle

---

### 2. VWAP Mean Reversion Strategy (GOLD)
**File:** `tests/test_gold_vwap.py`

Tests the VWAP mean reversion detector on GOLD using real historical data from Capital.com.

#### Usage:
```bash
# Basic test for date range
python tests/test_gold_vwap.py --start 2025-12-15 --end 2025-12-24 --symbol GOLD

# Test with custom config
python tests/test_gold_vwap.py --start 2025-12-01 --end 2025-12-24 --symbol GOLD --config assets_config_custom_strategies.json

# Export signals to CSV
python tests/test_gold_vwap.py --start 2025-12-15 --end 2025-12-24 --symbol GOLD --export gold_signals.csv

# Save report to file
python tests/test_gold_vwap.py --start 2025-12-15 --end 2025-12-24 --symbol GOLD --report gold_report.txt
```

#### Strategy Details:
- **Indicator**: VWAP with 1.0 standard deviation bands (daily reset)
- **Signal Window**: 13:00-15:00 UTC
- **Long Signal**: Price < VWAP lower band + bullish reversal candle + previous candle was bearish
- **Short Signal**: Price > VWAP upper band + bearish reversal candle + previous candle was bullish

---

### 3. VWAP Mean Reversion Strategy (BTC)
**File:** `tests/test_btc_vwap.py`

Tests the VWAP mean reversion detector on BTC using real historical data from Capital.com.

#### Usage:
```bash
# Basic test for date range
python tests/test_btc_vwap.py --start 2025-12-15 --end 2025-12-24 --symbol BTC

# Test with custom config
python tests/test_btc_vwap.py --start 2025-12-01 --end 2025-12-24 --symbol BTC --config assets_config_custom_strategies.json

# Export signals to CSV
python tests/test_btc_vwap.py --start 2025-12-15 --end 2025-12-24 --symbol BTC --export btc_signals.csv

# Save report to file
python tests/test_btc_vwap.py --start 2025-12-15 --end 2025-12-24 --symbol BTC --report btc_report.txt
```

#### Strategy Details:
- **Indicator**: VWAP with 1.0 standard deviation bands (daily reset)
- **Signal Window**: 14:00-16:00 UTC
- **Long Signal**: Price < VWAP lower band + bullish reversal candle + previous candle was bearish
- **Short Signal**: Price > VWAP upper band + bearish reversal candle + previous candle was bullish

---

## Command-Line Arguments

### Common Arguments (Both Scripts)

| Argument | Required | Default | Description |
|----------|----------|---------|-------------|
| `--start` | Yes | - | Start date in YYYY-MM-DD format |
| `--end` | Yes | - | End date in YYYY-MM-DD format |
| `--symbol` | No | DE40/GOLD/BTC | Asset symbol to test |
| `--config` | No | assets_config_custom_strategies.json | Path to configuration file |

### VWAP Additional Arguments (GOLD & BTC)

| Argument | Required | Default | Description |
|----------|----------|---------|-------------|
| `--export` | No | - | Export signals to CSV file path |
| `--report` | No | - | Save report to text file path |

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
Both scripts output a detailed report to the console including:
- Test period and total candles analyzed
- Signal summary (long/short/no signal/errors)
- Detailed list of all detected signals with:
  - Timestamp
  - Current price
  - Strategy-specific indicators (session high/low or VWAP bands)
  - Signal reason

### CSV Export (VWAP strategies)
Export signals to CSV for further analysis with columns:
- timestamp
- signal_type (long/short)
- direction (BUY/SELL)
- symbol
- current_price
- vwap, vwap_upper, vwap_lower
- reason

### Text Report (VWAP strategies)
Save the full console report to a text file for documentation.

---

## Example Workflows

### Test Recent Trading Week
```bash
# Test DE40 for past week
python tests/test_asia_session_sweep.py --start 2025-12-18 --end 2025-12-24 --symbol DE40

# Test GOLD for past week with export
python tests/test_gold_vwap.py --start 2025-12-18 --end 2025-12-24 --symbol GOLD --export results/gold_dec_week.csv

# Test BTC for past week with export
python tests/test_btc_vwap.py --start 2025-12-18 --end 2025-12-24 --symbol BTC --export results/btc_dec_week.csv
```

### Test Full Month
```bash
# Test GOLD - entire December
python tests/test_gold_vwap.py --start 2025-12-01 --end 2025-12-31 --symbol GOLD --report results/gold_december.txt

# Test BTC - entire December
python tests/test_btc_vwap.py --start 2025-12-01 --end 2025-12-31 --symbol BTC --report results/btc_december.txt
```

### Compare Different Periods
```bash
# Test GOLD - November
python tests/test_gold_vwap.py --start 2025-11-01 --end 2025-11-30 --symbol GOLD --export results/gold_november.csv

# Test GOLD - December
python tests/test_gold_vwap.py --start 2025-12-01 --end 2025-12-31 --symbol GOLD --export results/gold_december.csv

# Test BTC - November
python tests/test_btc_vwap.py --start 2025-11-01 --end 2025-11-30 --symbol BTC --export results/btc_november.csv

# Test BTC - December
python tests/test_btc_vwap.py --start 2025-12-01 --end 2025-12-31 --symbol BTC --export results/btc_december.csv

# Compare CSV files in spreadsheet or Python
```

---

## Troubleshooting

### Error: "cannot reindex on an axis with duplicate labels"
This occurs when there are duplicate timestamps in the data. The test scripts now automatically handle this by removing duplicates, but if you see this error:
1. Check your data fetching logic
2. Ensure timestamps are unique before passing to detector
3. Use `df.drop_duplicates(subset=['timestamp'], keep='last')` to clean data

### Error: "Failed to create Capital.com fetcher"
1. Verify your `.env` file exists in the project root
2. Check that all required credentials are set
3. Ensure `CAPITALCOM_DEMO=true` for testing with demo account

### No Signals Detected
1. Verify the date range includes trading days (not weekends)
2. Check that the signal window aligns with your trading hours
3. Review the "No Signal" reasons in the report
4. Ensure sufficient historical data is available (need full day for VWAP)

### Insufficient Data for VWAP
The VWAP detector requires at least 24 hours (288 candles at 5m intervals) of historical data for accurate calculation. Ensure your start date provides enough history.

---

## Best Practices

1. **Start with Recent Data**: Test with last 1-2 weeks first to validate setup
2. **Use Demo Account**: Always test with `CAPITALCOM_DEMO=true` initially
3. **Export Results**: Save signals to CSV for analysis and record-keeping
4. **Compare Periods**: Test multiple date ranges to validate strategy consistency
5. **Review No-Signals**: Understand why signals aren't generated in certain conditions
6. **Check Time Windows**: Ensure your signal windows align with market activity

---

## Adding New Test Scripts

To create a test script for a new strategy:

1. Copy `tests/test_gold_vwap.py` as a template
2. Update the detector import and initialization
3. Modify the fetch_data() parameters (symbol, asset_type, timeframe)
4. Adjust min_required candles based on strategy requirements
5. Update report generation for strategy-specific fields
6. Add usage documentation to this README

---

## Support

For issues or questions:
1. Check the troubleshooting section above
2. Review detector implementation in `src/bot/custom_scripts/`
3. Verify configuration in `assets_config_custom_strategies.json`
4. Enable debug logging: `logging.basicConfig(level=logging.DEBUG)`

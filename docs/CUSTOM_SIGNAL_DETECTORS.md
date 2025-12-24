# Custom Signal Detectors

This directory contains custom signal detection strategies that operate independently from the standard mean reversion approach.

## Overview

The custom scripts system provides:
- **Configurable Detectors**: Session-based strategies with flexible time ranges
- **Config-Driven Setup**: Asset-strategy relationships defined in JSON
- **Easy Integration**: Factory functions and config loaders for quick setup
- **Testing Framework**: Comprehensive backtesting tools

## Directory Structure

```
src/bot/custom_scripts/
├── __init__.py                      # Module exports
├── asia_session_sweep_detector.py  # Session sweep detector implementation
├── config_loader.py                 # Configuration loading utilities
└── README.md                        # This file
```

## Quick Start

### 1. Create/Edit Configuration File

```json
{
  "assets": [
    {
      "symbol": "DE40",
      "fetch_symbol": "DE40",
      "timeframe": "5m",
      "strategy": "session_sweep",
      "description": "DAX Index - Asia session sweep"
    }
  ],
  "strategies": {
    "session_sweep": {
      "detector_class": "AsiaSessionSweepDetector",
      "detector_module": "src.bot.custom_scripts.asia_session_sweep_detector",
      "parameters": {
        "session_start": "03:00",
        "session_end": "07:00",
        "signal_window_start": "08:30",
        "signal_window_end": "09:30"
      }
    }
  }
}
```

### 2. Load Config and Create Detector

```python
from src.bot.custom_scripts import load_custom_strategy_config

# Load configuration
config = load_custom_strategy_config('assets_config_custom_strategies.json')

# Create detector for DE40
detector = config.create_detector('DE40')

# Use detector
signal = detector.detect_signals(data, symbol='DE40')
```

### 3. Run Backtest

```bash
# Set Capital.com credentials
export CAPITAL_COM_API_KEY="your_key"
export CAPITAL_COM_PASSWORD="your_password"
export CAPITAL_COM_IDENTIFIER="your_email"

# Run backtest
python tests/test_asia_session_sweep.py \
  --start 2024-12-01 \
  --end 2024-12-20 \
  --config assets_config_custom_strategies.json \
  --symbol DE40
```

## Session Sweep Strategy

### Concept

The session sweep strategy identifies liquidity grabs during session transitions:

1. **Session Range**: Track high/low during a specific time period (e.g., Asia session 3-7 AM UTC)
2. **Signal Window**: Generate signals during a subsequent period (e.g., European open 8:30-9:30 AM UTC)
3. **Entry Conditions**:
   - **Long**: Price breaks above session high + bearish reversal candle (close < open)
   - **Short**: Price breaks below session low + bullish reversal candle (close > open)

### Signal Output

Signals are detection-only (no risk calculations):

```python
{
    'signal_type': 'long'|'short'|'no_signal'|'error',
    'direction': 'BUY'|'SELL'|'HOLD',
    'symbol': 'DE40',
    'current_price': 18420.0,
    'session_high': 18400.0,
    'session_low': 18350.0,
    'reason': 'Price broke above session high...',
    'timestamp': datetime(2024, 12, 24, 9, 0, 0),
    'strategy': 'session_sweep'
}
```

### Configurable Parameters

| Parameter | Description | Example |
|-----------|-------------|---------|
| `session_start` | Session tracking start time (HH:MM UTC) | "03:00" |
| `session_end` | Session tracking end time (HH:MM UTC) | "07:00" |
| `signal_window_start` | Signal generation start time (HH:MM UTC) | "08:30" |
| `signal_window_end` | Signal generation end time (HH:MM UTC) | "09:30" |

## Configuration System

### Asset Configuration

Define which assets use which strategies:

```json
{
  "assets": [
    {
      "symbol": "DE40",           // Your reference symbol
      "fetch_symbol": "DE40", // Capital.com API symbol
      "timeframe": "5m",           // Chart timeframe
      "strategy": "session_sweep", // Strategy to use
      "description": "..."         // Human-readable description
    }
  ]
}
```

### Strategy Configuration

Define strategy behavior and parameters:

```json
{
  "strategies": {
    "session_sweep": {
      "detector_class": "AsiaSessionSweepDetector",
      "detector_module": "src.bot.custom_scripts.asia_session_sweep_detector",
      "description": "Session high/low breakout with reversal confirmation",
      "parameters": {
        "session_start": "03:00",
        "session_end": "07:00",
        "signal_window_start": "08:30",
        "signal_window_end": "09:30"
      }
    }
  }
}
```

### Asset Details (Optional)

Additional metadata for each asset:

```json
{
  "asset_details": {
    "DE40": {
      "asset_class": "index",
      "market": "Europe",
      "base_currency": "EUR",
      "trading_hours": {
        "start_hour": 8,
        "end_hour": 17,
        "timezone": "UTC"
      }
    }
  }
}
```

## Config Loader API

### CustomStrategyConfigLoader

```python
from src.bot.custom_scripts import CustomStrategyConfigLoader

# Load config
loader = CustomStrategyConfigLoader('config.json')

# Get all assets
assets = loader.get_assets()

# Get specific asset
asset = loader.get_asset_by_symbol('DE40')

# Get strategy
strategy = loader.get_strategy('session_sweep')

# Get complete detector config
config = loader.get_detector_config('DE40')

# Create detector instance
detector = loader.create_detector('DE40')
```

### Key Methods

| Method | Description | Returns |
|--------|-------------|---------|
| `get_assets()` | Get all configured assets | List[Dict] |
| `get_asset_by_symbol(symbol)` | Get asset by symbol | Dict or None |
| `get_strategy(name)` | Get strategy config | Dict or None |
| `get_asset_details(symbol)` | Get asset details | Dict or None |
| `get_detector_config(symbol)` | Get complete detector config | Dict |
| `create_detector(symbol)` | Create detector instance | Detector object |

## Testing

### Test Script Usage

```bash
python tests/test_asia_session_sweep.py \
  --start 2024-12-01 \
  --end 2024-12-20 \
  --config assets_config_custom_strategies.json \
  --symbol DE40 \
  --output-dir ./test_results
```

### Test Output

1. **Console Report**: Summary statistics and signal details
2. **Text Report**: Detailed report saved to `test_results/asia_sweep_report_TIMESTAMP.txt`
3. **CSV Export**: All signals in `test_results/asia_sweep_signals_TIMESTAMP.csv`

### Report Sections

- **Signal Summary**: Count of long/short/no-signal/errors
- **Long Signals**: Detailed breakdown of each long signal
- **Short Signals**: Detailed breakdown of each short signal
- **No Signal Examples**: Sample reasons for no signals
- **Errors**: Any errors encountered

## Examples

See `examples/custom_strategy_usage.py` for comprehensive usage examples:

```bash
python examples/custom_strategy_usage.py
```

Examples include:
1. Loading configuration files
2. Creating detector instances
3. Using detectors with sample data
4. Configuring multiple assets

## Integration with Live Trading

### Option 1: Direct Integration

```python
from src.bot.custom_scripts import load_custom_strategy_config

# Load config
config_loader = load_custom_strategy_config('assets_config_custom_strategies.json')

# Get detector config
detector_config = config_loader.get_detector_config('DE40')
fetch_symbol = detector_config['fetch_symbol']
timeframe = detector_config['timeframe']

# Create detector
detector = config_loader.create_detector('DE40')

# Fetch data from Capital.com
data = fetcher.fetch_candles(fetch_symbol, timeframe, ...)

# Detect signals
signal = detector.detect_signals(data, symbol='DE40')

# Process signal
if signal['signal_type'] in ['long', 'short']:
    # Send notification, execute trade, etc.
    pass
```

### Option 2: Extend LiveStrategyScheduler

Modify `live_strategy_scheduler.py` to support custom detectors:

```python
# Check if asset uses custom strategy
if asset_config.get('strategy_type') == 'custom':
    config_path = asset_config.get('custom_config')
    config_loader = load_custom_strategy_config(config_path)
    detector = config_loader.create_detector(symbol)
    signal = detector.detect_signals(data, symbol)
else:
    # Use standard mean reversion detector
    signal = self.signal_detector.detect_signals(data, ...)
```

## Adding New Detectors

### 1. Create Detector Class

```python
class MyCustomDetector:
    def __init__(self, param1: str, param2: int):
        self.param1 = param1
        self.param2 = param2
    
    def detect_signals(self, data: pd.DataFrame, symbol: str) -> Dict:
        # Your detection logic
        return {
            'signal_type': 'long'|'short'|'no_signal'|'error',
            'direction': 'BUY'|'SELL'|'HOLD',
            'symbol': symbol,
            'current_price': price,
            'reason': reason,
            'timestamp': timestamp,
            'strategy': 'my_strategy'
        }
```

### 2. Add to Configuration

```json
{
  "strategies": {
    "my_strategy": {
      "detector_class": "MyCustomDetector",
      "detector_module": "src.bot.custom_scripts.my_detector",
      "parameters": {
        "param1": "value1",
        "param2": 42
      }
    }
  }
}
```

### 3. Export from __init__.py

```python
from .my_detector import MyCustomDetector

__all__ = [..., 'MyCustomDetector']
```

## Best Practices

1. **Time Zones**: Always use UTC for consistency
2. **Data Validation**: Validate input data before processing
3. **Error Handling**: Return error signals instead of raising exceptions
4. **Logging**: Use logger for debugging and monitoring
5. **Config Validation**: Validate config structure before use
6. **Testing**: Test with historical data before live deployment
7. **Signal Deduplication**: Implement caching if using in live system

## Troubleshooting

### Issue: "Asset not found in config"
- Check symbol name matches exactly (case-sensitive)
- Verify config file is valid JSON
- Ensure assets array contains the symbol

### Issue: "Cannot create detector"
- Verify detector_module path is correct
- Check detector_class name matches the class definition
- Ensure all required parameters are in config

### Issue: "No signals detected"
- Verify data has sufficient history (covers session period)
- Check signal window time range
- Confirm timezone settings (should be UTC)
- Review detector logs for debugging info

### Issue: "Module not found"
- Ensure project root is in Python path
- Check detector_module path is correct
- Verify file structure matches module path

## Future Enhancements

Potential additions:
- [ ] Chart generation for signals
- [ ] Multiple session tracking (e.g., Asia + London)
- [ ] Volume profile integration
- [ ] Dynamic session range calculation
- [ ] Multi-timeframe analysis
- [ ] Machine learning signal filtering

## Support

For issues or questions:
1. Check the examples in `examples/custom_strategy_usage.py`
2. Review test script in `tests/test_asia_session_sweep.py`
3. Check logs for detailed error messages
4. Refer to main project documentation

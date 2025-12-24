# Custom Strategy Scheduler - Quick Start

## Two Independent Schedulers

This project now has **two separate schedulers**:

1. **`live_strategy_scheduler.py`** - Mean Reversion Strategy (Bollinger Bands + VWAP)
2. **`custom_strategy_scheduler.py`** - Custom Strategies (Session Sweep, etc.)

## Running the Schedulers

### Option 1: Run Mean Reversion Only
```bash
python live_strategy_scheduler.py
```

### Option 2: Run Custom Strategies Only
```bash
python custom_strategy_scheduler.py
```

### Option 3: Run Both Together
```bash
# Terminal 1
python live_strategy_scheduler.py

# Terminal 2  
python custom_strategy_scheduler.py
```

## Configuration

### Mean Reversion Config: `assets_config_wr45.json`
Standard format with ASSET_INFO and strategy parameters.

### Custom Strategies Config: `assets_config_custom_strategies.json`
Custom format with assets, strategies, and detector modules.

## Environment Variables

Both schedulers require:
```bash
CAPITAL_COM_API_KEY=your_key
CAPITAL_COM_PASSWORD=your_password
CAPITAL_COM_IDENTIFIER=your_email
TELEGRAM_BOT_TOKEN=your_token  # Optional
```

## Shared Components

Both schedulers share:
- ✅ Telegram bot (same notifications)
- ✅ Signal cache (prevents duplicates)
- ✅ Chart generator (same styling)

## Schedule

Both run every **5 minutes** during trading hours (6:00-17:00 UTC):
- :00, :05, :10, :15, :20, :25, :30, :35, :40, :45, :50, :55

## Telegram Notifications

### Mean Reversion Format
```
📈 LONG SIGNAL
🎯 Symbol: EURUSD
💰 Entry: 1.0850
🛑 Stop Loss: 1.0840
🎯 Take Profit: 1.0870
```

### Custom Strategy Format
```
🔧 CUSTOM STRATEGY SIGNAL
🎯 Symbol: DE40
📊 Strategy: session_sweep
📈 Signal: LONG
💰 Entry: 20150.50
```

## Testing

```bash
# Test both schedulers
python tests/test_separate_schedulers.py
```

## Adding Custom Strategies

1. Create detector in `src/bot/custom_scripts/my_detector.py`
2. Add to `assets_config_custom_strategies.json`:
```json
{
  "assets": [
    {"symbol": "BTCUSD", "strategy": "my_strategy"}
  ],
  "strategies": {
    "my_strategy": {
      "detector_class": "MyDetector",
      "detector_module": "src.bot.custom_scripts.my_detector",
      "parameters": {...}
    }
  }
}
```
3. Run: `python custom_strategy_scheduler.py`

## Documentation

- [Separate Scheduler Guide](docs/SEPARATE_CUSTOM_SCHEDULER.md)
- [Custom Signal Detectors](docs/CUSTOM_SIGNAL_DETECTORS.md)
- [Telegram Integration](docs/TELEGRAM_BOT_INTEGRATION.md)

## Architecture

```
Mean Reversion Scheduler       Custom Strategy Scheduler
        ↓                               ↓
        └──────────┬────────────────────┘
                   ↓
          Shared Components
      (Telegram, Cache, Charts)
```

Clean, independent, maintainable! 🚀

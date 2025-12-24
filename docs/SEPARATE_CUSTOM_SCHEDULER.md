# Separate Custom Strategy Scheduler

## Overview

Created a **separate, independent scheduler** (`custom_strategy_scheduler.py`) specifically for custom signal detection strategies. This scheduler runs independently from the mean reversion scheduler and reuses existing Telegram components.

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                   Two Separate Schedulers                │
└─────────────────────────────────────────────────────────┘

┌──────────────────────────┐      ┌──────────────────────────┐
│  live_strategy_scheduler │      │ custom_strategy_scheduler│
│                          │      │                          │
│  • Mean Reversion        │      │  • Custom Detectors      │
│  • Bollinger Bands       │      │  • Session Sweep         │
│  • VWAP                  │      │  • Any custom strategy   │
│  • Config: wr45.json     │      │  • Config: custom.json   │
└──────────────────────────┘      └──────────────────────────┘
         │                                   │
         └───────────┬───────────────────────┘
                     ▼
           ┌──────────────────────┐
           │  Shared Components   │
           │                      │
           │  • telegram_bot      │
           │  • signal_cache      │
           │  • chart_generator   │
           └──────────────────────┘
```

## Key Features

✅ **Complete Separation**: Two independent schedulers, each with its own purpose  
✅ **Component Reuse**: Both use same Telegram bot, signal cache, and chart generator  
✅ **Different Configs**: Each scheduler uses its own configuration format  
✅ **Run Independently**: Can run one or both at the same time  
✅ **No Code Conflicts**: Changes to one don't affect the other  

## Files

### Created
- ✨ **custom_strategy_scheduler.py** - Dedicated custom strategy scheduler
- 🧪 **tests/test_separate_schedulers.py** - Tests for both schedulers

### Unchanged
- ✅ **live_strategy_scheduler.py** - Original mean reversion scheduler (reverted)
- ✅ **src/bot/telegram_bot.py** - Shared Telegram components
- ✅ **src/bot/signal_cache.py** - Shared signal cache
- ✅ **src/bot/signal_chart_generator.py** - Shared chart generator

## Configuration Files

### Mean Reversion: `assets_config_wr45.json`
```json
{
  "EURUSDX_5m": {
    "symbol": "EURUSDX",
    "ASSET_INFO": {...},
    "bb_window": 20,
    ...
  }
}
```

### Custom Strategies: `assets_config_custom_strategies.json`
```json
{
  "assets": [
    {"symbol": "DE40", "strategy": "session_sweep"}
  ],
  "strategies": {
    "session_sweep": {
      "detector_class": "AsiaSessionSweepDetector",
      "detector_module": "src.bot.custom_scripts.asia_session_sweep_detector",
      "parameters": {...}
    }
  }
}
```

## Usage

### Run Mean Reversion Scheduler
```bash
python live_strategy_scheduler.py
```
- Uses `assets_config_wr45.json`
- Runs Bollinger Bands + VWAP strategy
- 7 symbols configured

### Run Custom Strategy Scheduler
```bash
python custom_strategy_scheduler.py
```
- Uses `assets_config_custom_strategies.json`
- Runs custom detectors (e.g., AsiaSessionSweepDetector)
- 1+ assets configured

### Run Both Simultaneously
```bash
# Terminal 1
python live_strategy_scheduler.py

# Terminal 2
python custom_strategy_scheduler.py
```
Both will share the same Telegram bot and signal cache, preventing duplicate notifications.

## Component Reuse Details

### Telegram Bot
- Both schedulers use `create_telegram_bot_from_env()`
- Same bot token, same chat management
- Notifications go to same Telegram chats

### Signal Cache
- Both use `create_signal_cache()`
- Shared DynamoDB table: `trading-signals-cache`
- Prevents duplicate signals across both schedulers

### Chart Generator
- Both use `SignalChartGenerator()`
- Same chart styling and format
- Charts attached to Telegram notifications

## Testing

All tests pass! ✅

```bash
python tests/test_separate_schedulers.py
```

**Test Results:**
- ✅ Custom Scheduler Initialization
- ✅ Separate Scheduler Instances  
- ✅ Telegram Component Reuse

## Custom Strategy Scheduler Features

### Initialization
- Loads `assets_config_custom_strategies.json`
- Creates custom detectors from config
- Caches detector instances for reuse
- Initializes shared Telegram components

### Analysis Cycle
- Runs every 5 minutes (synchronized)
- Trading hours: 6:00-17:00 UTC
- Fetches data for each asset
- Calls `detector.detect_signals()`
- Sends Telegram notifications

### Signal Format
```
🔧 CUSTOM STRATEGY SIGNAL

🎯 Symbol: DE40
📊 Strategy: session_sweep
📈 Signal: LONG
💰 Entry Price: 20150.50
📊 Session High: 20200.00
📊 Session Low: 20100.00
📝 Reason: Price broke below session low with bullish reversal

⏰ Time: 2025-12-24 08:30:00
```

## Benefits of Separate Schedulers

### 1. **Clear Separation of Concerns**
- Mean reversion logic stays in `live_strategy_scheduler.py`
- Custom strategies have their own dedicated scheduler
- No mixing of different strategy types in one file

### 2. **Independent Development**
- Modify custom strategies without touching mean reversion
- Add new custom detectors easily
- Update one scheduler without affecting the other

### 3. **Flexible Deployment**
- Run only what you need
- Scale independently
- Different trading hours per scheduler if needed

### 4. **Code Maintainability**
- Each scheduler ~600 lines (manageable)
- Clear purpose for each file
- Easy to understand and debug

## Adding New Custom Strategies

1. Create detector in `src/bot/custom_scripts/`
2. Add to `assets_config_custom_strategies.json`
3. Run `python custom_strategy_scheduler.py`

No changes needed to `custom_strategy_scheduler.py` - it automatically loads and creates detectors from config!

## Summary

✅ **Separate schedulers created** - Each with dedicated purpose  
✅ **Telegram components reused** - No duplication, shared notifications  
✅ **Both tested and working** - All tests passing  
✅ **Clean architecture** - Clear separation, easy to maintain  
✅ **Ready for production** - Can run independently or together  

The system now has two independent schedulers:
- `live_strategy_scheduler.py` for mean reversion
- `custom_strategy_scheduler.py` for custom strategies

Both reuse the same Telegram bot infrastructure for notifications!

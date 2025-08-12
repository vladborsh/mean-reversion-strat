# Signal Chart Generation

## Overview

The signal chart generation system creates professional candlestick charts with technical indicators for Telegram notifications. Charts are generated in-memory and sent as images alongside trading signals.

## Architecture

### Core Component
- **[SignalChartGenerator](../src/bot/signal_chart_generator.py)** - Main chart generation class
- **Integration** - Used by [Live Strategy Scheduler](../live_strategy_scheduler.py) → [Telegram Bot](TELEGRAM_BOT_INTEGRATION.md)

### Dependencies
- **mplfinance** - Professional candlestick charting
- **[Indicators](../src/indicators.py)** - BB and VWAP calculations
- **matplotlib** - Chart rendering (Agg backend)

## Chart Features

### Visual Elements
- **Candlesticks** - Green (up) / Red (down) with 5-minute timeframe
- **Bollinger Bands** - Gray dashed upper/lower bands only (no center line)
- **VWAP Bands** - Purple dotted upper/lower bands only (no center line) 
- **Signal Levels**:
  - Entry: Blue solid line (2.5px)
  - Stop Loss: Red dashed line (2px)
  - Take Profit: Green dash-dot line (2px)

### Optimization
- **Context** - Last 100 candles for optimal perspective
- **Y-axis** - Auto-scaled to ensure SL/TP levels are visible
- **Size** - 1200x800px, ~110KB (mobile-optimized)
- **No annotations** - Clean visual-only design

## Technical Implementation

### Indicator Calculations
```python
# Uses proper indicators.py methods
bb_ma, bb_upper, bb_lower = Indicators.bollinger_bands(df, window=20, num_std=2)
vwap, vwap_upper, vwap_lower = Indicators.vwap_daily_reset_forex_compatible(df, num_std=2)
```

### Chart Generation Flow
1. **Data Preparation** - Optimize 100 candles with SL/TP range calculation
2. **Indicator Calculation** - BB and VWAP bands using [indicators.py](../src/indicators.py)
3. **Signal Lines** - Add horizontal entry/SL/TP levels
4. **Rendering** - mplfinance with custom style and y-axis limits
5. **Output** - BytesIO buffer for [Telegram transmission](TELEGRAM_BOT_INTEGRATION.md)

### Integration Points
- **[Live Scheduler](../live_strategy_scheduler.py)** - Calls chart generation on signal detection
- **[Telegram Notifier](../src/bot/telegram_signal_notifier.py)** - Sends charts via `send_photo()`
- **[Strategy Parameters](STRATEGY_DOCUMENTATION.md)** - BB/VWAP window and std dev settings

## Usage

### Basic Generation
```python
from src.bot.signal_chart_generator import SignalChartGenerator

generator = SignalChartGenerator()
chart_buffer = generator.generate_signal_chart(
    data=ohlcv_dataframe,
    signal_data={'signal_type': 'long', 'entry_price': 1.1000, ...},
    strategy_params={'bb_window': 20, 'bb_std': 2, 'vwap_std': 2},
    symbol='EURUSD'
)
```

### Error Handling
- **Fail-fast approach** - Returns None if indicator calculations fail
- **Detailed logging** - Logs specific errors for BB and VWAP calculations
- **Null safety** - Returns None on failure, allows text-only fallback in Telegram

## Configuration

### Chart Settings
- **Candles**: 100 (configurable via `candles_to_show`)
- **Size**: 1200x800px (configurable via `figure_size`)
- **DPI**: 100 (configurable via `dpi`)

### Style Customization
- **Colors**: Professional green/red/gray/purple palette
- **Lines**: Varied styles (solid/dashed/dotted) for clarity
- **Transparency**: Alpha values for visual hierarchy

## Related Documentation
- [Telegram Bot Integration](TELEGRAM_BOT_INTEGRATION.md) - Message sending
- [Strategy Documentation](STRATEGY_DOCUMENTATION.md) - Signal generation  
- [Risk Management](RISK_MANAGEMENT.md) - SL/TP calculation
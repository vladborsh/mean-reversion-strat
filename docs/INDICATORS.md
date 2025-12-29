# Technical Indicators Documentation

Complete guide to technical indicators, divergence detection, and integration patterns.

## Table of Contents

- [RSI Indicator](#rsi-indicator)
- [Divergence Detection](#divergence-detection)
- [RSI Divergence Helper](#rsi-divergence-helper)
- [Integration Patterns](#integration-patterns)
- [Best Practices](#best-practices)

---

## RSI Indicator

### Overview

Relative Strength Index (RSI) measures the magnitude of recent price changes to evaluate overbought or oversold conditions. Values range from 0 to 100.

**Interpretation:**
- RSI > 70: Overbought (potential reversal down)
- RSI < 30: Oversold (potential reversal up)
- RSI = 50: Neutral momentum

### Algorithm

Uses Wilder's smoothing method:

1. Calculate price changes (delta)
2. Separate gains and losses
3. Calculate smoothed average gain and loss
4. Calculate RS (Relative Strength) = avg_gain / avg_loss
5. Calculate RSI = 100 - (100 / (1 + RS))

**Wilder's Smoothing Formula:**
```
new_avg = (prev_avg * (period - 1) + current_value) / period
```

### Usage

```python
from src.indicators import Indicators

# Calculate RSI
rsi = Indicators.rsi(df, period=14, column='close')

# Check current RSI
current_rsi = rsi.iloc[-1]

if current_rsi < 30:
    print("Oversold condition")
elif current_rsi > 70:
    print("Overbought condition")
```

### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `df` | DataFrame | Required | OHLCV data |
| `period` | int | 14 | RSI calculation period |
| `column` | str | 'close' | Column to calculate RSI on |

### Edge Cases

- When avg_loss = 0: RSI = 100
- When avg_gain = 0: RSI = 0
- First `period` values: NaN (insufficient data)

### Returns

`pd.Series` - RSI values (0-100) with datetime index matching input DataFrame

---

## Divergence Detection

### Overview

Divergence occurs when price movement diverges from indicator movement, suggesting potential trend changes or continuations.

**Module:** `src/bot/custom_scripts/divergence_utils.py`

### Divergence Types

#### Regular Divergences (Trend Reversal)

**Bullish Regular:**
- Price: Lower low
- Indicator: Higher low
- Signal: Downtrend weakening, potential upward reversal

**Bearish Regular:**
- Price: Higher high
- Indicator: Lower high
- Signal: Uptrend weakening, potential downward reversal

#### Hidden Divergences (Trend Continuation)

**Bullish Hidden:**
- Price: Higher low
- Indicator: Lower low
- Signal: Uptrend pullback, continuation expected

**Bearish Hidden:**
- Price: Lower high
- Indicator: Higher high
- Signal: Downtrend pullback, continuation expected

### Core Functions

#### find_pivot_lows()

Identifies local minima in a time series.

```python
from src.bot.custom_scripts.divergence_utils import find_pivot_lows

pivot_lows = find_pivot_lows(series, lookback=5, min_periods=2)
```

**Algorithm:**
- Checks if value is lower than all values in surrounding lookback window
- Requires minimum periods before/after for valid pivot

**Parameters:**
| Parameter | Default | Description |
|-----------|---------|-------------|
| `series` | Required | Time series to analyze |
| `lookback` | 5 | Periods to look on each side |
| `min_periods` | 2 | Minimum required periods |

**Returns:** Boolean Series where True = pivot low

#### find_pivot_highs()

Identifies local maxima in a time series.

```python
from src.bot.custom_scripts.divergence_utils import find_pivot_highs

pivot_highs = find_pivot_highs(series, lookback=5, min_periods=2)
```

**Algorithm:** Same as pivot_lows but checks for maximum values

**Returns:** Boolean Series where True = pivot high

#### detect_bullish_divergence()

Detects bullish divergence patterns.

```python
from src.bot.custom_scripts.divergence_utils import detect_bullish_divergence

result = detect_bullish_divergence(
    df, 
    indicator, 
    lookback=14,
    divergence_type='regular'  # or 'hidden'
)
```

**Parameters:**
| Parameter | Default | Description |
|-----------|---------|-------------|
| `df` | Required | DataFrame with OHLCV data |
| `indicator` | Required | Indicator series (RSI, MACD, etc.) |
| `lookback` | 14 | Lookback window for pivots |
| `divergence_type` | 'regular' | 'regular' or 'hidden' |

**Returns Dictionary:**
```python
{
    'detected': bool,                    # Divergence found?
    'current_idx': int,                  # Index of current pivot
    'previous_idx': int,                 # Index of previous pivot
    'price_current': float,              # Current price low
    'price_previous': float,             # Previous price low
    'indicator_current': float,          # Current indicator value
    'indicator_previous': float,         # Previous indicator value
    'divergence_type': str               # 'regular' or 'hidden'
}
```

#### detect_bearish_divergence()

Detects bearish divergence patterns.

```python
result = detect_bearish_divergence(
    df, 
    indicator, 
    lookback=14,
    divergence_type='regular'
)
```

**Parameters:** Same as `detect_bullish_divergence()`

**Returns:** Same structure, but analyzes price highs instead of lows

#### get_divergence_summary()

Generates human-readable divergence summary.

```python
from src.bot.custom_scripts.divergence_utils import get_divergence_summary

bullish = detect_bullish_divergence(df, rsi)
bearish = detect_bearish_divergence(df, rsi)

summary = get_divergence_summary(bullish, bearish)
# Example: "Regular Bullish Divergence: Price 49950.00 → 49800.00, Indicator 32.50 → 35.20"
```

### Generic Design

The divergence utilities work with **ANY indicator**, not just RSI:

```python
# RSI divergence
rsi = Indicators.rsi(df, period=14)
rsi_div = detect_bullish_divergence(df, rsi)

# MACD divergence (if you implement MACD)
macd = calculate_macd(df)
macd_div = detect_bullish_divergence(df, macd)

# Stochastic divergence (if you implement Stochastic)
stoch = calculate_stochastic(df)
stoch_div = detect_bullish_divergence(df, stoch)
```

---

## RSI Divergence Helper

### Overview

`RSIDivergenceHelper` is a **utility class** designed to be used within other detectors as a confirmation filter. It is **NOT a standalone detector**.

**Module:** `src/bot/custom_scripts/rsi_divergence_detector.py`

### Design Philosophy

**RSI Divergence = Confirmation Filter**

Use it to enhance existing strategies:
- ✅ VWAP + RSI divergence
- ✅ Session Sweep + RSI divergence
- ✅ Support/Resistance + RSI divergence
- ❌ RSI divergence alone (not recommended)

### Basic Usage

```python
from src.bot.custom_scripts.rsi_divergence_detector import RSIDivergenceHelper

# Initialize helper
rsi_helper = RSIDivergenceHelper(
    rsi_period=14,
    divergence_lookback=14,
    rsi_oversold=30.0,
    rsi_overbought=70.0
)

# Analyze divergence
divergence = rsi_helper.analyze_divergence(
    df,
    detect_regular=True,   # Detect regular divergences
    detect_hidden=False    # Skip hidden divergences
)

# Check results
if divergence['has_bullish_signal']:
    print(f"Confirmation: {divergence['summary']}")
```

### Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `rsi_period` | 14 | RSI calculation period |
| `divergence_lookback` | 14 | Lookback for pivot detection |
| `rsi_oversold` | 30.0 | Oversold threshold |
| `rsi_overbought` | 70.0 | Overbought threshold |

### analyze_divergence() Method

**Parameters:**
| Parameter | Default | Description |
|-----------|---------|-------------|
| `data` | Required | DataFrame with OHLCV data |
| `detect_regular` | True | Detect regular divergences |
| `detect_hidden` | False | Detect hidden divergences |

**Returns Dictionary:**
```python
{
    'bullish_regular': {...} or None,    # Regular bullish divergence details
    'bearish_regular': {...} or None,    # Regular bearish divergence details
    'bullish_hidden': {...} or None,     # Hidden bullish divergence details
    'bearish_hidden': {...} or None,     # Hidden bearish divergence details
    'rsi_current': 45.2,                 # Current RSI value
    'rsi_oversold': False,               # RSI < oversold threshold?
    'rsi_overbought': False,             # RSI > overbought threshold?
    'has_bullish_signal': True,          # Any bullish divergence?
    'has_bearish_signal': False,         # Any bearish divergence?
    'summary': 'Regular Bullish Divergence | RSI: 45.2'
}
```

---

## Integration Patterns

### Pattern 1: Simple Confirmation

Use RSI divergence to confirm your primary signal.

```python
class MyDetector:
    def __init__(self):
        self.rsi_helper = RSIDivergenceHelper(rsi_period=14)
    
    def detect_signals(self, data):
        # Primary signal logic
        if self._check_entry_condition(data):
            # Add RSI divergence confirmation
            rsi_div = self.rsi_helper.analyze_divergence(data)
            
            if rsi_div['has_bullish_signal']:
                return {
                    'signal_type': 'long',
                    'reason': f'Entry condition + {rsi_div["summary"]}'
                }
        
        return {'signal_type': 'no_signal'}
```

### Pattern 2: VWAP + RSI Divergence

Combine VWAP mean reversion with RSI divergence confirmation.

```python
from src.indicators import Indicators
from src.bot.custom_scripts.rsi_divergence_detector import RSIDivergenceHelper

class VWAPWithRSIDivergenceDetector:
    def __init__(self, num_std=1.0, require_rsi_confirmation=True):
        self.num_std = num_std
        self.require_rsi_confirmation = require_rsi_confirmation
        self.rsi_helper = RSIDivergenceHelper(rsi_period=14)
    
    def detect_signals(self, data, symbol='GOLD'):
        # Step 1: Check VWAP mean reversion
        vwap, upper, lower = Indicators.vwap_daily_reset_forex_compatible(
            data, num_std=self.num_std
        )
        
        current_price = data['close'].iloc[-1]
        
        # Bullish VWAP signal
        if current_price < lower.iloc[-1]:
            if not self.require_rsi_confirmation:
                return {'signal_type': 'long', 'reason': 'VWAP reversal'}
            
            # Step 2: Require RSI divergence confirmation
            rsi_div = self.rsi_helper.analyze_divergence(data)
            
            if rsi_div['has_bullish_signal'] and rsi_div['rsi_oversold']:
                return {
                    'signal_type': 'long',
                    'reason': f'VWAP below band + {rsi_div["summary"]}'
                }
        
        # Bearish VWAP signal
        elif current_price > upper.iloc[-1]:
            if not self.require_rsi_confirmation:
                return {'signal_type': 'short', 'reason': 'VWAP reversal'}
            
            rsi_div = self.rsi_helper.analyze_divergence(data)
            
            if rsi_div['has_bearish_signal'] and rsi_div['rsi_overbought']:
                return {
                    'signal_type': 'short',
                    'reason': f'VWAP above band + {rsi_div["summary"]}'
                }
        
        return {'signal_type': 'no_signal'}
```

### Pattern 3: Multi-Factor Confirmation

Combine multiple confirmation factors.

```python
class MultiFactorDetector:
    def __init__(self):
        self.rsi_helper = RSIDivergenceHelper()
    
    def detect_signals(self, data):
        # Multiple confirmation factors
        rsi_div = self.rsi_helper.analyze_divergence(data)
        
        strong_long_signal = (
            self._price_at_support(data) and          # Factor 1
            self._vwap_below_lower_band(data) and     # Factor 2
            rsi_div['has_bullish_signal'] and         # Factor 3
            rsi_div['rsi_oversold']                   # Factor 4
        )
        
        if strong_long_signal:
            return {
                'signal_type': 'long',
                'confidence': 'high',
                'reason': f'4-factor confirmation: {rsi_div["summary"]}'
            }
        
        # Medium confidence with fewer factors
        medium_long_signal = (
            self._vwap_below_lower_band(data) and
            rsi_div['has_bullish_signal']
        )
        
        if medium_long_signal:
            return {
                'signal_type': 'long',
                'confidence': 'medium',
                'reason': f'2-factor confirmation: {rsi_div["summary"]}'
            }
        
        return {'signal_type': 'no_signal'}
```

### Pattern 4: Optional Confirmation

Make RSI divergence confirmation optional.

```python
class FlexibleDetector:
    def __init__(self, use_rsi_confirmation=True):
        self.use_rsi_confirmation = use_rsi_confirmation
        if use_rsi_confirmation:
            self.rsi_helper = RSIDivergenceHelper()
    
    def detect_signals(self, data):
        # Primary signal
        primary_signal = self._check_primary_conditions(data)
        
        if primary_signal['type'] == 'no_signal':
            return primary_signal
        
        # Optional RSI confirmation
        if self.use_rsi_confirmation:
            rsi_div = self.rsi_helper.analyze_divergence(data)
            
            # Filter out signals without RSI confirmation
            if primary_signal['type'] == 'long':
                if not rsi_div['has_bullish_signal']:
                    return {'signal_type': 'no_signal', 
                            'reason': 'Primary signal but no RSI divergence'}
            elif primary_signal['type'] == 'short':
                if not rsi_div['has_bearish_signal']:
                    return {'signal_type': 'no_signal',
                            'reason': 'Primary signal but no RSI divergence'}
            
            # Add RSI info to signal
            primary_signal['rsi_divergence'] = rsi_div['summary']
        
        return primary_signal
```

### Pattern 5: Divergence Type Selection

Use different divergence types based on market conditions.

```python
class AdaptiveDetector:
    def __init__(self):
        self.rsi_helper = RSIDivergenceHelper()
    
    def detect_signals(self, data):
        # Determine market condition
        is_trending = self._is_market_trending(data)
        
        # Use appropriate divergence type
        if is_trending:
            # Hidden divergences for trend continuation
            rsi_div = self.rsi_helper.analyze_divergence(
                data,
                detect_regular=False,
                detect_hidden=True
            )
        else:
            # Regular divergences for trend reversal
            rsi_div = self.rsi_helper.analyze_divergence(
                data,
                detect_regular=True,
                detect_hidden=False
            )
        
        # Use divergence in your signal logic
        if self._your_entry_condition(data) and rsi_div['has_bullish_signal']:
            return {'signal_type': 'long', 'reason': rsi_div['summary']}
        
        return {'signal_type': 'no_signal'}
```

---

## Best Practices

### DO ✅

1. **Use as Confirmation**
   - Combine with price action, VWAP, support/resistance
   - Don't rely on divergence alone

2. **Check RSI Zones**
   - Regular bullish divergence: Best when RSI < 30
   - Regular bearish divergence: Best when RSI > 70
   - Stronger signals in appropriate zones

3. **Adjust Parameters**
   - Different assets require different settings
   - Higher timeframes → larger lookback periods
   - More volatile assets → adjust RSI thresholds

4. **Select Appropriate Type**
   - Regular divergences: Ranging/choppy markets
   - Hidden divergences: Trending markets
   - Test both to find what works

5. **Multiple Confirmations**
   - Combine multiple factors for stronger signals
   - Higher confidence = better win rate

### DON'T ❌

1. **Standalone Trading**
   - Don't trade RSI divergence alone
   - Always use with primary strategy

2. **Ignore Primary Signals**
   - Don't override strong primary signals
   - Divergence is a filter, not a generator

3. **One-Size-Fits-All**
   - Don't use same parameters everywhere
   - Backtest and optimize per asset

4. **Trade Every Divergence**
   - Not all divergences lead to reversals
   - Require additional confirmation

5. **Forget Market Context**
   - Strong trends can persist despite divergence
   - Consider overall market conditions

### Parameter Guidelines

| Asset Type | RSI Period | Lookback | Notes |
|------------|-----------|----------|-------|
| Forex (5m) | 14 | 14 | Default settings work well |
| Crypto (15m) | 14 | 10-14 | Faster pivots in volatile markets |
| Indices (5m) | 14 | 14-20 | Smoother price action |
| Gold (5m) | 14 | 14 | Standard settings |

| Timeframe | RSI Period | Lookback | RSI Zones |
|-----------|-----------|----------|-----------|
| 5m | 14 | 10-14 | 30/70 |
| 15m | 14 | 14-20 | 30/70 |
| 1h | 14 | 20-30 | 35/65 |
| 4h | 14 | 30-50 | 40/60 |

---

## Configuration

RSI Divergence Helper is listed in `assets_config_custom_strategies.json` under `helper_utilities`:

```json
{
  "helper_utilities": {
    "rsi_divergence": {
      "class": "RSIDivergenceHelper",
      "module": "src.bot.custom_scripts.rsi_divergence_detector",
      "description": "RSI divergence analysis helper",
      "parameters": {
        "rsi_period": 14,
        "divergence_lookback": 14,
        "rsi_oversold": 30.0,
        "rsi_overbought": 70.0
      }
    }
  }
}
```

---

## Complete Example

See `examples/vwap_rsi_divergence_integration.py` for a complete working example of integrating RSI divergence with VWAP mean reversion.

---

## Quick Reference

### Files

| File | Description |
|------|-------------|
| `src/indicators.py` | RSI calculation |
| `src/bot/custom_scripts/divergence_utils.py` | Generic divergence detection |
| `src/bot/custom_scripts/rsi_divergence_detector.py` | RSI divergence helper |
| `examples/vwap_rsi_divergence_integration.py` | Integration example |
| `docs/INDICATORS.md` | This documentation |

### Quick Snippets

**Calculate RSI:**
```python
rsi = Indicators.rsi(df, period=14)
```

**Detect Divergence:**
```python
div = detect_bullish_divergence(df, rsi, lookback=14)
```

**Use Helper:**
```python
helper = RSIDivergenceHelper()
result = helper.analyze_divergence(df)
```

**Integration:**
```python
class MyDetector:
    def __init__(self):
        self.rsi_helper = RSIDivergenceHelper()
    
    def detect_signals(self, data):
        if primary_condition:
            rsi = self.rsi_helper.analyze_divergence(data)
            if rsi['has_bullish_signal']:
                return {'signal_type': 'long'}
```

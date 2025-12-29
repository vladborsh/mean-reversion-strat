"""
Reusable divergence detection utilities for any indicator.

Works with RSI, MACD, Stochastic, or any oscillator to detect bullish/bearish
divergences (regular and hidden).

See docs/INDICATORS.md for comprehensive documentation and usage examples.
"""

import pandas as pd
import numpy as np
from typing import Optional, Tuple, List, Dict


def find_pivot_lows(series: pd.Series, lookback: int = 5, min_periods: int = 2) -> pd.Series:
    """
    Find local minima (pivot lows) in time series.
    
    See docs/INDICATORS.md for details.
    """
    if series.empty or len(series) < (min_periods * 2 + 1):
        return pd.Series(False, index=series.index)
    
    pivot_lows = pd.Series(False, index=series.index)
    
    for i in range(lookback, len(series) - lookback):
        current_value = series.iloc[i]
        
        # Check if current value is minimum in the window
        left_window = series.iloc[i - lookback:i]
        right_window = series.iloc[i + 1:i + lookback + 1]
        
        if (current_value <= left_window.min() and 
            current_value <= right_window.min()):
            pivot_lows.iloc[i] = True
    
    return pivot_lows


def find_pivot_highs(series: pd.Series, lookback: int = 5, min_periods: int = 2) -> pd.Series:
    """
    Find local maxima (pivot highs) in time series.
    
    See docs/INDICATORS.md for details.
    """
    if series.empty or len(series) < (min_periods * 2 + 1):
        return pd.Series(False, index=series.index)
    
    pivot_highs = pd.Series(False, index=series.index)
    
    for i in range(lookback, len(series) - lookback):
        current_value = series.iloc[i]
        
        # Check if current value is maximum in the window
        left_window = series.iloc[i - lookback:i]
        right_window = series.iloc[i + 1:i + lookback + 1]
        
        if (current_value >= left_window.max() and 
            current_value >= right_window.max()):
            pivot_highs.iloc[i] = True
    
    return pivot_highs


def detect_bullish_divergence(
    df: pd.DataFrame,
    indicator: pd.Series,
    lookback: int = 14,
    divergence_type: str = 'regular'
) -> Dict:
    """
    Detect bullish divergence between price and indicator.
    
    Regular: Price lower low + Indicator higher low (reversal signal)
    Hidden: Price higher low + Indicator lower low (continuation signal)
    
    See docs/INDICATORS.md for details.
    """
    result = {
        'detected': False,
        'current_idx': None,
        'previous_idx': None,
        'price_current': None,
        'price_previous': None,
        'indicator_current': None,
        'indicator_previous': None,
        'divergence_type': divergence_type
    }
    
    if df.empty or len(df) < lookback * 2:
        return result
    
    # Find price pivot lows
    price_lows = df['low']
    pivot_lows_mask = find_pivot_lows(price_lows, lookback=lookback)
    pivot_indices = df.index[pivot_lows_mask].tolist()
    
    if len(pivot_indices) < 2:
        return result
    
    # Get the two most recent pivot lows
    current_idx = pivot_indices[-1]
    previous_idx = pivot_indices[-2]
    
    price_current = price_lows.loc[current_idx]
    price_previous = price_lows.loc[previous_idx]
    indicator_current = indicator.loc[current_idx]
    indicator_previous = indicator.loc[previous_idx]
    
    # Check for divergence based on type
    divergence_detected = False
    
    if divergence_type == 'regular':
        # Price lower low + indicator higher low
        if price_current < price_previous and indicator_current > indicator_previous:
            divergence_detected = True
    elif divergence_type == 'hidden':
        # Price higher low + indicator lower low
        if price_current > price_previous and indicator_current < indicator_previous:
            divergence_detected = True
    
    if divergence_detected:
        result.update({
            'detected': True,
            'current_idx': current_idx,
            'previous_idx': previous_idx,
            'price_current': float(price_current),
            'price_previous': float(price_previous),
            'indicator_current': float(indicator_current),
            'indicator_previous': float(indicator_previous)
        })
    
    return result


def detect_bearish_divergence(
    df: pd.DataFrame,
    indicator: pd.Series,
    lookback: int = 14,
    divergence_type: str = 'regular'
) -> Dict:
    """
    Detect bearish divergence between price and indicator.
    
    Regular: Price higher high + Indicator lower high (reversal signal)
    Hidden: Price lower high + Indicator higher high (continuation signal)
    
    See docs/INDICATORS.md for details.
    """
    result = {
        'detected': False,
        'current_idx': None,
        'previous_idx': None,
        'price_current': None,
        'price_previous': None,
        'indicator_current': None,
        'indicator_previous': None,
        'divergence_type': divergence_type
    }
    
    if df.empty or len(df) < lookback * 2:
        return result
    
    # Find price pivot highs
    price_highs = df['high']
    pivot_highs_mask = find_pivot_highs(price_highs, lookback=lookback)
    pivot_indices = df.index[pivot_highs_mask].tolist()
    
    if len(pivot_indices) < 2:
        return result
    
    # Get the two most recent pivot highs
    current_idx = pivot_indices[-1]
    previous_idx = pivot_indices[-2]
    
    price_current = price_highs.loc[current_idx]
    price_previous = price_highs.loc[previous_idx]
    indicator_current = indicator.loc[current_idx]
    indicator_previous = indicator.loc[previous_idx]
    
    # Check for divergence based on type
    divergence_detected = False
    
    if divergence_type == 'regular':
        # Price higher high + indicator lower high
        if price_current > price_previous and indicator_current < indicator_previous:
            divergence_detected = True
    elif divergence_type == 'hidden':
        # Price lower high + indicator higher high
        if price_current < price_previous and indicator_current > indicator_previous:
            divergence_detected = True
    
    if divergence_detected:
        result.update({
            'detected': True,
            'current_idx': current_idx,
            'previous_idx': previous_idx,
            'price_current': float(price_current),
            'price_previous': float(price_previous),
            'indicator_current': float(indicator_current),
            'indicator_previous': float(indicator_previous)
        })
    
    return result


def get_divergence_summary(bullish_div: Dict, bearish_div: Dict) -> str:
    """Generate human-readable divergence summary."""
    summary_parts = []
    
    if bullish_div['detected']:
        div_type = bullish_div['divergence_type'].capitalize()
        summary_parts.append(
            f"{div_type} Bullish Divergence: "
            f"Price {bullish_div['price_previous']:.2f} → {bullish_div['price_current']:.2f}, "
            f"Indicator {bullish_div['indicator_previous']:.2f} → {bullish_div['indicator_current']:.2f}"
        )
    
    if bearish_div['detected']:
        div_type = bearish_div['divergence_type'].capitalize()
        summary_parts.append(
            f"{div_type} Bearish Divergence: "
            f"Price {bearish_div['price_previous']:.2f} → {bearish_div['price_current']:.2f}, "
            f"Indicator {bearish_div['indicator_previous']:.2f} → {bearish_div['indicator_current']:.2f}"
        )
    
    if not summary_parts:
        return "No divergence detected"
    
    return " | ".join(summary_parts)

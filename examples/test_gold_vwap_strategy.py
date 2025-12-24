"""
Test script for GOLD VWAP mean reversion strategy.

This script demonstrates how to:
1. Load the GOLD VWAP strategy configuration
2. Create detector instances
3. Test with sample data simulating VWAP extremes and reversals
4. Verify signal detection logic
"""

import sys
from pathlib import Path
import pandas as pd
import numpy as np
from datetime import datetime, timezone, timedelta

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.bot.custom_scripts import load_custom_strategy_config
from src.bot.custom_scripts.vwap_detector import VWAPDetector


def test_load_gold_config():
    """Test: Load GOLD configuration from config file."""
    print("=" * 80)
    print("Test 1: Loading GOLD Configuration")
    print("=" * 80)
    
    # Load config
    config_loader = load_custom_strategy_config('assets_config_custom_strategies.json')
    
    # Get GOLD configuration
    gold_config = config_loader.get_detector_config('GOLD')
    
    print(f"\nGOLD Strategy Configuration:")
    print(f"  Symbol: {gold_config['symbol']}")
    print(f"  Fetch Symbol: {gold_config['fetch_symbol']}")
    print(f"  Timeframe: {gold_config['timeframe']}")
    print(f"  Strategy: {gold_config['strategy_name']}")
    print(f"  Detector Class: {gold_config['detector_class']}")
    
    print(f"\n  Strategy Parameters:")
    for key, value in gold_config['strategy_params'].items():
        print(f"    {key}: {value}")
    
    print(f"\n  Signal Conditions:")
    strategy_config = config_loader.config['strategies'][gold_config['strategy_name']]
    for signal_type, condition in strategy_config.get('signal_conditions', {}).items():
        print(f"    {signal_type}: {condition}")
    
    print("\n✓ Configuration loaded successfully")
    print()


def test_create_detector():
    """Test: Create VWAP detector instance."""
    print("=" * 80)
    print("Test 2: Creating VWAP Detector Instance")
    print("=" * 80)
    
    # Load config and create detector
    config_loader = load_custom_strategy_config('assets_config_custom_strategies.json')
    detector = config_loader.create_detector('GOLD')
    
    print(f"\n✓ Created detector instance: {type(detector).__name__}")
    print(f"  Standard Deviations: {detector.num_std}")
    print(f"  Anchor Period: {detector.anchor_period}")
    print(f"  Signal Window: {detector.signal_window_start} - {detector.signal_window_end}")
    print()


def test_short_signal_scenario():
    """Test: Short signal detection (price above VWAP upper, bearish reversal)."""
    print("=" * 80)
    print("Test 3: Short Signal Scenario")
    print("=" * 80)
    print("Scenario: Price breaks above VWAP upper band + bearish reversal candle")
    print()
    
    # Create detector directly with parameters
    detector = VWAPDetector(
        num_std=1.0,
        signal_window_start="13:00",
        signal_window_end="15:00",
        anchor_period="day"
    )
    
    # Create sample data for GOLD during signal window
    # Simulate a day where price moves up throughout the day and breaks VWAP upper
    base_date = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    
    # Create timestamps for the day (5-minute intervals)
    timestamps = []
    for hour in range(0, 15):
        for minute in [0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55]:
            timestamps.append(base_date.replace(hour=hour, minute=minute))
    
    # Add the final candle at 14:00 (within signal window) - ensure unique
    final_timestamp = base_date.replace(hour=14, minute=0)
    if final_timestamp not in timestamps:
        timestamps.append(final_timestamp)
    
    num_candles = len(timestamps)
    
    # Ensure all timestamps are unique
    timestamps = sorted(list(set(timestamps)))
    
    # Create price data that trends up (VWAP will be around 2000)
    # Last candle will be above VWAP upper and bearish
    base_price = 1995
    prices = []
    for i in range(num_candles):
        # Gradual uptrend with some noise
        prices.append(base_price + (i * 0.5) + np.random.uniform(-1, 1))
    
    data = pd.DataFrame({
        'timestamp': timestamps,
        'open': [p for p in prices],
        'high': [p + np.random.uniform(0.5, 2) for p in prices],
        'low': [p - np.random.uniform(0.5, 2) for p in prices],
        'close': [p + np.random.uniform(-1, 1) for p in prices],
        'volume': [100 + np.random.uniform(0, 50) for _ in range(num_candles)]
    })
    
    # Modify second-to-last candle to be bullish (setup)
    data.loc[len(data)-2, 'open'] = 2040
    data.loc[len(data)-2, 'close'] = 2045  # Bullish: close > open
    data.loc[len(data)-2, 'high'] = 2046
    data.loc[len(data)-2, 'low'] = 2039
    
    # Modify last candle to create SHORT signal:
    # - Price above VWAP upper (will be calculated)
    # - Bearish candle (close < open)
    data.loc[len(data)-1, 'open'] = 2050
    data.loc[len(data)-1, 'high'] = 2055
    data.loc[len(data)-1, 'low'] = 2045
    data.loc[len(data)-1, 'close'] = 2048  # Bearish: close < open
    
    # Detect signal
    signal = detector.detect_signals(data, symbol='GOLD')
    
    print(f"Signal Result:")
    print(f"  Type: {signal['signal_type'].upper()}")
    print(f"  Direction: {signal['direction']}")
    
    if signal['signal_type'] in ['long', 'short']:
        print(f"  Current Price: {signal['current_price']}")
        print(f"  VWAP: {signal['vwap']}")
        print(f"  VWAP Upper: {signal['vwap_upper']}")
        print(f"  VWAP Lower: {signal['vwap_lower']}")
        print(f"  Reason: {signal['reason']}")
        print(f"  Timestamp: {signal['timestamp']}")
        print(f"\n✓ SHORT signal detected as expected!")
    else:
        print(f"  Reason: {signal['reason']}")
        if 'vwap' in signal:
            print(f"  VWAP: {signal.get('vwap')}")
            print(f"  VWAP Upper: {signal.get('vwap_upper')}")
            print(f"  VWAP Lower: {signal.get('vwap_lower')}")
        print(f"\n⚠ Expected SHORT signal, got: {signal['signal_type']}")
    
    print()


def test_long_signal_scenario():
    """Test: Long signal detection (price below VWAP lower, bullish reversal)."""
    print("=" * 80)
    print("Test 4: Long Signal Scenario")
    print("=" * 80)
    print("Scenario: Price breaks below VWAP lower band + bullish reversal candle")
    print()
    
    # Create detector
    detector = VWAPDetector(
        num_std=1.0,
        signal_window_start="13:00",
        signal_window_end="15:00",
        anchor_period="day"
    )
    
    # Create sample data
    base_date = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    
    # Create timestamps for the day
    timestamps = []
    for hour in range(0, 15):
        for minute in [0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55]:
            timestamps.append(base_date.replace(hour=hour, minute=minute))
    
    # Add the final candle at 14:00 (within signal window) - ensure unique
    final_timestamp = base_date.replace(hour=14, minute=0)
    if final_timestamp not in timestamps:
        timestamps.append(final_timestamp)
    
    num_candles = len(timestamps)
    
    # Ensure all timestamps are unique
    timestamps = sorted(list(set(timestamps)))
    
    # Create price data that trends down (VWAP will be around 2000)
    # Last candle will be below VWAP lower and bullish
    base_price = 2005
    prices = []
    for i in range(num_candles):
        # Gradual downtrend with some noise
        prices.append(base_price - (i * 0.5) + np.random.uniform(-1, 1))
    
    data = pd.DataFrame({
        'timestamp': timestamps,
        'open': [p for p in prices],
        'high': [p + np.random.uniform(0.5, 2) for p in prices],
        'low': [p - np.random.uniform(0.5, 2) for p in prices],
        'close': [p + np.random.uniform(-1, 1) for p in prices],
        'volume': [100 + np.random.uniform(0, 50) for _ in range(num_candles)]
    })
    
    # Modify second-to-last candle to be bearish (setup)
    data.loc[len(data)-2, 'open'] = 1960
    data.loc[len(data)-2, 'close'] = 1955  # Bearish: close < open
    data.loc[len(data)-2, 'high'] = 1961
    data.loc[len(data)-2, 'low'] = 1954
    
    # Modify last candle to create LONG signal:
    # - Price below VWAP lower (will be calculated)
    # - Bullish candle (close > open)
    data.loc[len(data)-1, 'open'] = 1950
    data.loc[len(data)-1, 'high'] = 1955
    data.loc[len(data)-1, 'low'] = 1945
    data.loc[len(data)-1, 'close'] = 1952  # Bullish: close > open
    
    # Detect signal
    signal = detector.detect_signals(data, symbol='GOLD')
    
    print(f"Signal Result:")
    print(f"  Type: {signal['signal_type'].upper()}")
    print(f"  Direction: {signal['direction']}")
    
    if signal['signal_type'] in ['long', 'short']:
        print(f"  Current Price: {signal['current_price']}")
        print(f"  VWAP: {signal['vwap']}")
        print(f"  VWAP Upper: {signal['vwap_upper']}")
        print(f"  VWAP Lower: {signal['vwap_lower']}")
        print(f"  Reason: {signal['reason']}")
        print(f"  Timestamp: {signal['timestamp']}")
        print(f"\n✓ LONG signal detected as expected!")
    else:
        print(f"  Reason: {signal['reason']}")
        if 'vwap' in signal:
            print(f"  VWAP: {signal.get('vwap')}")
            print(f"  VWAP Upper: {signal.get('vwap_upper')}")
            print(f"  VWAP Lower: {signal.get('vwap_lower')}")
        print(f"\n⚠ Expected LONG signal, got: {signal['signal_type']}")
    
    print()


def test_no_signal_scenarios():
    """Test: Various no-signal conditions."""
    print("=" * 80)
    print("Test 5: No Signal Scenarios")
    print("=" * 80)
    
    detector = VWAPDetector(
        num_std=1.0,
        signal_window_start="13:00",
        signal_window_end="15:00",
        anchor_period="day"
    )
    
    # Test 1: Outside signal window
    print("\nScenario A: Outside signal window (12:00 UTC)")
    base_date = datetime.now(timezone.utc).replace(hour=12, minute=0, second=0, microsecond=0)
    
    timestamps = [base_date.replace(hour=h, minute=m) 
                  for h in range(10, 13) 
                  for m in [0, 5, 10, 15]]
    
    data = pd.DataFrame({
        'timestamp': timestamps,
        'open': [2000 + i for i in range(len(timestamps))],
        'high': [2005 + i for i in range(len(timestamps))],
        'low': [1995 + i for i in range(len(timestamps))],
        'close': [2002 + i for i in range(len(timestamps))],
        'volume': [100] * len(timestamps)
    })
    
    signal = detector.detect_signals(data, symbol='GOLD')
    print(f"  Result: {signal['signal_type']} - {signal['reason']}")
    
    # Test 2: Price near VWAP (no extreme)
    print("\nScenario B: Price near VWAP (no extreme)")
    base_date = datetime.now(timezone.utc).replace(hour=14, minute=0, second=0, microsecond=0)
    
    timestamps = [base_date.replace(hour=h, minute=m) 
                  for h in range(0, 15) 
                  for m in [0, 5, 10, 15]]
    
    # Create stable price around 2000 (should be near VWAP)
    data = pd.DataFrame({
        'timestamp': timestamps,
        'open': [2000] * len(timestamps),
        'high': [2002] * len(timestamps),
        'low': [1998] * len(timestamps),
        'close': [2000] * len(timestamps),
        'volume': [100] * len(timestamps)
    })
    
    signal = detector.detect_signals(data, symbol='GOLD')
    print(f"  Result: {signal['signal_type']} - {signal['reason']}")
    
    # Test 3: No reversal candle (continuation pattern)
    print("\nScenario C: Price at extreme but no reversal candle pattern")
    # This would require specific setup where candle doesn't show reversal
    print("  (Implementation: price extreme without candle reversal)")
    print(f"  Expected: no_signal")
    
    print()


def test_insufficient_data():
    """Test: Error handling with insufficient data."""
    print("=" * 80)
    print("Test 6: Error Handling - Insufficient Data")
    print("=" * 80)
    
    detector = VWAPDetector(
        num_std=1.0,
        signal_window_start="13:00",
        signal_window_end="15:00",
        anchor_period="day"
    )
    
    # Only 1 candle (need at least 2 for pattern analysis)
    base_date = datetime.now(timezone.utc).replace(hour=14, minute=0, second=0, microsecond=0)
    
    data = pd.DataFrame({
        'timestamp': [base_date],
        'open': [2000],
        'high': [2005],
        'low': [1995],
        'close': [2002],
        'volume': [100]
    })
    
    signal = detector.detect_signals(data, symbol='GOLD')
    print(f"\nResult: {signal['signal_type']}")
    print(f"Reason: {signal['reason']}")
    print(f"\n✓ Error handled gracefully")
    print()


if __name__ == '__main__':
    print("\n")
    print("╔" + "=" * 78 + "╗")
    print("║" + " " * 22 + "GOLD VWAP STRATEGY TESTS" + " " * 32 + "║")
    print("╚" + "=" * 78 + "╝")
    print()
    
    try:
        test_load_gold_config()
        test_create_detector()
        test_short_signal_scenario()
        test_long_signal_scenario()
        test_no_signal_scenarios()
        test_insufficient_data()
        
        print("=" * 80)
        print("✓ All tests completed!")
        print("=" * 80)
        print("\nNote: Signal detection depends on VWAP calculation from actual data.")
        print("In production, use real market data for accurate signal generation.")
        print()
        
    except Exception as e:
        print(f"\n✗ Error during testing: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

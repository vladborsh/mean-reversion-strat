"""
Example usage of custom session sweep detector with configuration.

This script demonstrates how to:
1. Load a custom strategy configuration
2. Create detector instances from config
3. Use detectors with live or historical data
"""

import sys
from pathlib import Path
import pandas as pd
from datetime import datetime, timezone

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.bot.custom_scripts import load_custom_strategy_config


def example_load_config():
    """Example: Load configuration file."""
    print("=" * 80)
    print("Example 1: Loading Configuration")
    print("=" * 80)
    
    # Load config
    config_loader = load_custom_strategy_config('assets_config_custom_strategies.json')
    
    # Get all assets
    assets = config_loader.get_assets()
    print(f"\nConfigured assets: {len(assets)}")
    for asset in assets:
        print(f"  - {asset['symbol']}: {asset['description']}")
    
    # Get strategy details
    strategies = config_loader.config.get('strategies', {})
    print(f"\nAvailable strategies: {len(strategies)}")
    for name, strategy in strategies.items():
        print(f"  - {name}: {strategy['description']}")
    
    print()


def example_create_detector():
    """Example: Create detector from config."""
    print("=" * 80)
    print("Example 2: Creating Detector from Config")
    print("=" * 80)
    
    # Load config
    config_loader = load_custom_strategy_config('assets_config_custom_strategies.json')
    
    # Get detector configuration for DE40
    detector_config = config_loader.get_detector_config('DE40')
    
    print(f"\nDetector config for DE40:")
    print(f"  Symbol: {detector_config['symbol']}")
    print(f"  Fetch Symbol: {detector_config['fetch_symbol']}")
    print(f"  Timeframe: {detector_config['timeframe']}")
    print(f"  Strategy: {detector_config['strategy_name']}")
    print(f"  Detector Class: {detector_config['detector_class']}")
    print(f"\n  Strategy Parameters:")
    for key, value in detector_config['strategy_params'].items():
        print(f"    {key}: {value}")
    
    # Create detector instance
    detector = config_loader.create_detector('DE40')
    print(f"\n✓ Created detector instance: {type(detector).__name__}")
    
    print()


def example_use_detector():
    """Example: Use detector with sample data."""
    print("=" * 80)
    print("Example 3: Using Detector with Sample Data")
    print("=" * 80)
    
    # Load config and create detector
    config_loader = load_custom_strategy_config('assets_config_custom_strategies.json')
    detector = config_loader.create_detector('DE40')
    
    # Create sample data (simulated DE40 5m candles)
    # This represents a session where price broke above session high
    now = datetime.now(timezone.utc).replace(hour=9, minute=0, second=0, microsecond=0)
    
    timestamps = [now.replace(hour=h, minute=m) for h in range(3, 10) 
                  for m in [0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55]]
    
    # Sample data: Asia session 18350-18400, current price 18420 (bearish candle)
    data = pd.DataFrame({
        'timestamp': timestamps[:100],
        'open': [18350 + (i % 50) for i in range(100)],
        'high': [18360 + (i % 50) for i in range(100)],
        'low': [18340 + (i % 50) for i in range(100)],
        'close': [18355 + (i % 50) for i in range(100)]
    })
    
    # Last candle is at 9:00 AM, above session high, bearish
    data.loc[len(data)-1, 'open'] = 18425
    data.loc[len(data)-1, 'high'] = 18430
    data.loc[len(data)-1, 'low'] = 18415
    data.loc[len(data)-1, 'close'] = 18420  # Bearish: close < open
    
    # Detect signal
    signal = detector.detect_signals(data, symbol='DE40')
    
    print(f"\nSignal Result:")
    print(f"  Type: {signal['signal_type'].upper()}")
    print(f"  Direction: {signal['direction']}")
    
    if signal['signal_type'] in ['long', 'short']:
        print(f"  Current Price: {signal['current_price']}")
        print(f"  Session High: {signal['session_high']}")
        print(f"  Session Low: {signal['session_low']}")
        print(f"  Reason: {signal['reason']}")
        print(f"  Timestamp: {signal['timestamp']}")
    else:
        print(f"  Reason: {signal['reason']}")
    
    print()


def example_multiple_assets():
    """Example: Configure multiple assets with same strategy."""
    print("=" * 80)
    print("Example 4: Multiple Assets with Custom Sessions")
    print("=" * 80)
    
    # This shows how you could extend the config for multiple assets
    example_config = {
        "assets": [
            {
                "symbol": "DE40",
                "fetch_symbol": "DE40",
                "timeframe": "5m",
                "strategy": "session_sweep",
                "description": "DAX - Asia session sweep"
            },
            {
                "symbol": "UK100",
                "fetch_symbol": "FTSE100",
                "timeframe": "5m",
                "strategy": "session_sweep_london",
                "description": "FTSE - London session sweep"
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
            "session_sweep_london": {
                "parameters": {
                    "session_start": "07:00",
                    "session_end": "11:00",
                    "signal_window_start": "12:00",
                    "signal_window_end": "13:00"
                }
            }
        }
    }
    
    print("\nExample configuration for multiple assets:")
    print("\nDE40 (DAX):")
    print(f"  Session: 3:00-7:00 UTC (Asia)")
    print(f"  Signals: 8:30-9:30 UTC (European open)")
    
    print("\nUK100 (FTSE):")
    print(f"  Session: 7:00-11:00 UTC (Early London)")
    print(f"  Signals: 12:00-13:00 UTC (Midday)")
    
    print("\nThis demonstrates how the same detector can be used")
    print("for different assets with different session configurations.")
    print()


if __name__ == '__main__':
    print("\n")
    print("╔" + "=" * 78 + "╗")
    print("║" + " " * 20 + "SESSION SWEEP DETECTOR EXAMPLES" + " " * 27 + "║")
    print("╚" + "=" * 78 + "╝")
    print()
    
    try:
        example_load_config()
        example_create_detector()
        example_use_detector()
        example_multiple_assets()
        
        print("=" * 80)
        print("✓ All examples completed successfully!")
        print("=" * 80)
        print()
        
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()

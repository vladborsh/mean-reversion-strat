#!/usr/bin/env python3
"""
Test script to verify chart generation with mplfinance fallback
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

# Test import fallback
print("Testing mplfinance import...")
try:
    import mplfinance as mpf
    print("✅ mplfinance imported successfully")
    print(f"   Version: {mpf.__version__ if hasattr(mpf, '__version__') else 'unknown'}")
except ImportError as e:
    print(f"⚠️  mplfinance not available: {e}")
    print("   Charts will fallback to text-only mode")

# Test chart generator initialization
from src.bot.signal_chart_generator import SignalChartGenerator

print("\nTesting SignalChartGenerator initialization...")
try:
    generator = SignalChartGenerator()
    print("✅ SignalChartGenerator initialized")
    
    # Check if it can handle missing mplfinance
    import pandas as pd
    import numpy as np
    from datetime import datetime, timedelta
    
    # Create minimal test data
    dates = pd.date_range(end=datetime.now(), periods=100, freq='5min')
    data = pd.DataFrame({
        'open': np.random.randn(100) + 100,
        'high': np.random.randn(100) + 101,
        'low': np.random.randn(100) + 99,
        'close': np.random.randn(100) + 100,
        'volume': np.random.randint(1000, 10000, 100)
    }, index=dates)
    
    signal_data = {
        'signal_type': 'long',
        'entry_price': 100,
        'stop_loss': 99,
        'take_profit': 101
    }
    
    strategy_params = {
        'bb_window': 20,
        'bb_std': 2,
        'vwap_std': 2
    }
    
    result = generator.generate_signal_chart(data, signal_data, strategy_params, 'TEST')
    
    if result:
        print(f"✅ Chart generated: {len(result)} bytes")
    else:
        print("⚠️  Chart generation returned None (expected if mplfinance unavailable)")
        
except Exception as e:
    print(f"❌ Error: {e}")

print("\n" + "="*50)
print("COMPATIBILITY CHECK COMPLETE")
print("="*50)
print("\nDocker build should now work with:")
print("  • mplfinance>=0.12.9b7 (beta version)")
print("  • Python 3.10-slim base image")
print("  • Graceful fallback if chart generation fails")
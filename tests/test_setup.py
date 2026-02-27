#!/usr/bin/env python3
"""
Quick test script to verify the trading strategy setup
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # Add project root to Python path

def test_imports():
    """Test that all required modules can be imported"""
    try:
        import pandas as pd
        import numpy as np
        import matplotlib.pyplot as plt
        import backtrader as bt
        import ccxt
        print("✓ All dependencies imported successfully")
        return True
    except ImportError as e:
        print(f"✗ Import error: {e}")
        return False

def test_data_fetcher():
    """Test data fetching functionality"""
    try:
        from src.data_fetcher import DataFetcher
        fetcher = DataFetcher(source='forex', symbol='EURUSD', timeframe='1d')
        df = fetcher.fetch(years=0.1)  # Just a few days for testing
        print(f"✓ Data fetcher works: {len(df)} rows fetched")
        return True
    except Exception as e:
        print(f"✗ Data fetcher error: {e}")
        return False

def test_indicators():
    """Test indicator calculations"""
    try:
        import pandas as pd
        import numpy as np
        from src.indicators import Indicators
        
        # Create sample data
        dates = pd.date_range('2024-01-01', periods=100, freq='H')
        df = pd.DataFrame({
            'open': np.random.randn(100).cumsum() + 100,
            'high': np.random.randn(100).cumsum() + 102,
            'low': np.random.randn(100).cumsum() + 98,
            'close': np.random.randn(100).cumsum() + 100,
            'volume': np.random.randint(1000, 10000, 100)
        }, index=dates)
        
        bb_ma, bb_upper, bb_lower = Indicators.bollinger_bands(df)
        vwap, vwap_upper, vwap_lower = Indicators.vwap_bands(df)
        print("✓ Indicators calculated successfully")
        return True
    except Exception as e:
        print(f"✗ Indicators error: {e}")
        return False

def run_tests():
    """Run all tests"""
    print("Running setup verification tests...\n")
    
    tests = [
        ("Import Test", test_imports),
        ("Data Fetcher Test", test_data_fetcher),
        ("Indicators Test", test_indicators),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"Running {test_name}...")
        if test_func():
            passed += 1
        print()
    
    print(f"Tests passed: {passed}/{total}")
    
    if passed == total:
        print("🎉 All tests passed! Your trading strategy is ready to run.")
        print("\nNext steps:")
        print("1. Run 'python scripts/run_backtest.py' to execute the full strategy")
        print("2. Check the README.md for detailed usage instructions")
        print("3. Customize parameters in scripts/run_backtest.py as needed")
    else:
        print("❌ Some tests failed. Please check the error messages above.")

if __name__ == '__main__':
    run_tests()

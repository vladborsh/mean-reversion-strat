#!/usr/bin/env python3
"""
Test script for iterative data fetching functionality
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from src.data_fetcher import DataFetcher
from datetime import datetime, timedelta

def test_iterative_fetching():
    """Test the iterative data fetching for a longer period"""
    print("Testing iterative data fetching...")
    
    # Test with a symbol that should have good data availability
    fetcher = DataFetcher('forex', 'EURUSD', timeframe='15m')
    
    try:
        # Try to fetch 6 months of 15-minute data (should trigger iterative fetching)
        print("Attempting to fetch 6 months of 15-minute EUR/USD data...")
        data = fetcher.fetch(years=0.5)  # 6 months
        
        if data is not None and not data.empty:
            print(f"✅ Success! Fetched {len(data)} rows of data")
            print(f"Date range: {data.index[0]} to {data.index[-1]}")
            print(f"Data shape: {data.shape}")
            print(f"Columns: {list(data.columns)}")
            print("\nFirst few rows:")
            print(data.head())
            print("\nLast few rows:")
            print(data.tail())
            return True
        else:
            print("❌ Failed: No data returned")
            return False
            
    except Exception as e:
        print(f"❌ Error during fetch: {e}")
        return False

def test_short_period():
    """Test normal fetching for a short period (should not use iterative)"""
    print("\nTesting normal fetching for short period...")
    
    fetcher = DataFetcher('forex', 'EURUSD', timeframe='1h')
    
    try:
        # Try to fetch just 10 days of hourly data (should work normally)
        print("Attempting to fetch 10 days of hourly EUR/USD data...")
        data = fetcher.fetch(years=10/365)  # About 10 days
        
        if data is not None and not data.empty:
            print(f"✅ Success! Fetched {len(data)} rows of data")
            print(f"Date range: {data.index[0]} to {data.index[-1]}")
            return True
        else:
            print("❌ Failed: No data returned")
            return False
            
    except Exception as e:
        print(f"❌ Error during fetch: {e}")
        return False

if __name__ == "__main__":
    print("Running iterative data fetching tests...\n")
    
    test1_result = test_short_period()
    test2_result = test_iterative_fetching()
    
    print(f"\n{'='*50}")
    print("Test Results:")
    print(f"Short period fetch: {'✅ PASSED' if test1_result else '❌ FAILED'}")
    print(f"Iterative fetch: {'✅ PASSED' if test2_result else '❌ FAILED'}")
    
    if test1_result and test2_result:
        print("\n🎉 All tests passed!")
    else:
        print("\n⚠️  Some tests failed. Check the implementation.")

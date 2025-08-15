#!/usr/bin/env python3
"""
Test script for multi-provider data fetching functionality
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from src.data_fetcher import DataFetcher
from datetime import datetime, timedelta

def test_multi_provider_forex():
    """Test multi-provider fetching for forex data"""
    print("Testing multi-provider forex data fetching...")
    
    # You can set your Alpha Vantage API key here or as environment variable
    # Get free API key from: https://www.alphavantage.co/support/#api-key
    api_key = os.getenv('ALPHA_VANTAGE_API_KEY', 'demo')  # Use 'demo' for testing (limited)
    
    fetcher = DataFetcher('forex', 'EURUSD', timeframe='15m', api_key=api_key)
    
    try:
        # Try to fetch 6 months of 15-minute data using multiple providers
        print("Attempting to fetch 6 months of 15-minute EUR/USD data with multiple providers...")
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

def test_yfinance_only():
    """Test Yahoo Finance only for comparison"""
    print("\nTesting Yahoo Finance only (short period)...")
    
    fetcher = DataFetcher('forex', 'EURUSD', timeframe='15m')
    
    try:
        # Force use of only Yahoo Finance for 30 days
        print("Attempting to fetch 30 days of 15-minute EUR/USD data from Yahoo Finance...")
        data = fetcher._fetch_yfinance(30/365)  # About 30 days
        
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

def test_crypto_ccxt():
    """Test crypto data via CCXT"""
    print("\nTesting crypto data via CCXT...")
    
    fetcher = DataFetcher('crypto', 'BTC/USDT', timeframe='1h', exchange='binance')
    
    try:
        print("Attempting to fetch 3 months of hourly BTC/USDT data...")
        data = fetcher.fetch(years=0.25)  # 3 months
        
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
    print("Running multi-provider data fetching tests...\n")
    print("Note: For Alpha Vantage, set ALPHA_VANTAGE_API_KEY environment variable")
    print("      Get free API key from: https://www.alphavantage.co/support/#api-key\n")
    
    test1_result = test_yfinance_only()
    test2_result = test_multi_provider_forex()  
    test3_result = test_crypto_ccxt()
    
    print(f"\n{'='*60}")
    print("Test Results:")
    print(f"Yahoo Finance (30 days): {'✅ PASSED' if test1_result else '❌ FAILED'}")
    print(f"Multi-provider (6 months): {'✅ PASSED' if test2_result else '❌ FAILED'}")
    print(f"Crypto CCXT (3 months): {'✅ PASSED' if test3_result else '❌ FAILED'}")
    
    passed_tests = sum([test1_result, test2_result, test3_result])
    print(f"\n🎯 {passed_tests}/3 tests passed")
    
    if passed_tests >= 2:
        print("🎉 Most tests passed! Multi-provider system is working.")
    else:
        print("⚠️  Many tests failed. Check API keys and network connectivity.")

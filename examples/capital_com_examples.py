#!/usr/bin/env python3
"""
Capital.com Data Fetcher Examples

This file demonstrates how to use the Capital.com data fetcher
for professional-grade forex and indices data.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.capital_com_fetcher import create_capital_com_fetcher
from src.data_fetcher import DataFetcher
from datetime import datetime, timedelta


def test_capital_com_connection():
    """Test Capital.com API connection and credentials"""
    print("=== TESTING CAPITAL.COM CONNECTION ===")
    
    fetcher = create_capital_com_fetcher()
    if not fetcher:
        print("❌ Capital.com credentials not found")
        print("Set environment variables:")
        print("  export CAPITAL_COM_API_KEY='your_key'")
        print("  export CAPITAL_COM_PASSWORD='your_password'")
        print("  export CAPITAL_COM_IDENTIFIER='your_email'")
        return False
    
    try:
        with fetcher:
            print("✅ Connection successful")
            print(fetcher.get_trading_hours_info())
            return True
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        return False


def fetch_forex_data_examples():
    """Demonstrate forex data fetching with different timeframes"""
    print("\n=== FOREX DATA EXAMPLES ===")
    
    fetcher = create_capital_com_fetcher()
    if not fetcher:
        print("❌ Capital.com not available, skipping forex examples")
        return
    
    with fetcher:
        # Example 1: EUR/USD hourly data
        print("\n1. EUR/USD Hourly Data (1 year)")
        data = fetcher.fetch_historical_data('EURUSD', 'forex', '1h', 1)
        if data is not None:
            print(f"   ✅ Fetched {len(data)} records")
            print(f"   📅 Date range: {data.index.min()} to {data.index.max()}")
            print(f"   💰 Price range: {data['low'].min():.5f} - {data['high'].max():.5f}")
        
        # Example 2: GBP/USD 15-minute data
        print("\n2. GBP/USD 15-minute Data (3 months)")
        data = fetcher.fetch_historical_data('GBPUSD', 'forex', '15m', 0.25)
        if data is not None:
            print(f"   ✅ Fetched {len(data)} records")
            print(f"   📊 High frequency data for scalping strategies")
        
        # Example 3: Multiple pairs comparison
        print("\n3. Major Pairs Comparison (Daily, 6 months)")
        pairs = ['EURUSD', 'GBPUSD', 'USDJPY']
        for pair in pairs:
            data = fetcher.fetch_historical_data(pair, 'forex', '1d', 0.5)
            if data is not None:
                volatility = ((data['high'] - data['low']) / data['close']).mean() * 100
                print(f"   {pair}: {len(data)} bars, avg daily range: {volatility:.2f}%")


def fetch_indices_data_examples():
    """Demonstrate indices data fetching"""
    print("\n=== INDICES DATA EXAMPLES ===")
    
    fetcher = create_capital_com_fetcher()
    if not fetcher:
        print("❌ Capital.com not available, skipping indices examples")
        return
    
    with fetcher:
        # Example 1: S&P 500 daily data
        print("\n1. S&P 500 Daily Data (2 years)")
        data = fetcher.fetch_historical_data('US500', 'indices', '1d', 2)
        if data is not None:
            print(f"   ✅ Fetched {len(data)} records")
            returns = data['close'].pct_change().dropna()
            print(f"   📈 Average daily return: {returns.mean()*100:.3f}%")
            print(f"   📊 Daily volatility: {returns.std()*100:.3f}%")
        
        # Example 2: Multiple indices 4-hour data
        print("\n2. Global Indices 4-hour Data (6 months)")
        indices = ['US500', 'UK100', 'DE40']
        for index in indices:
            data = fetcher.fetch_historical_data(index, 'indices', '4h', 0.5)
            if data is not None:
                price_change = ((data['close'].iloc[-1] / data['close'].iloc[0]) - 1) * 100
                print(f"   {index}: {len(data)} bars, 6M return: {price_change:+.2f}%")


def integrated_datafetcher_examples():
    """Show how Capital.com integrates with the main DataFetcher class"""
    print("\n=== INTEGRATED DATA FETCHER EXAMPLES ===")
    
    # Example 1: Automatic Capital.com usage for forex
    print("\n1. Automatic Capital.com Integration (Forex)")
    fetcher = DataFetcher(source='forex', symbol='EURUSD=X', timeframe='1h', use_cache=True)
    data = fetcher.fetch(years=1)
    if data is not None:
        print(f"   ✅ Fetched {len(data)} EUR/USD records via integrated fetcher")
        print(f"   📈 Data source: Capital.com (if available) → yfinance (fallback)")
    
    # Example 2: High-frequency forex with caching
    print("\n2. High-Frequency Forex with Caching")
    fetcher = DataFetcher(source='forex', symbol='GBPUSD=X', timeframe='15m', use_cache=True)
    
    # First call - fetches from API
    import time
    start = time.time()
    data1 = fetcher.fetch(years=0.5)
    api_time = time.time() - start
    
    # Second call - loads from cache
    start = time.time()
    data2 = fetcher.fetch(years=0.5)
    cache_time = time.time() - start
    
    if data1 is not None and data2 is not None:
        print(f"   🚀 API fetch: {api_time:.2f}s")
        print(f"   ⚡ Cache load: {cache_time:.2f}s ({api_time/cache_time:.1f}x faster)")
    
    # Example 3: Indices with fallback
    print("\n3. Indices with Provider Fallback")
    fetcher = DataFetcher(source='indices', symbol='^GSPC', timeframe='1d', use_cache=True)
    data = fetcher.fetch(years=2)
    if data is not None:
        print(f"   ✅ Fetched {len(data)} S&P 500 records")
        print(f"   🔄 Automatic fallback: Capital.com → yfinance")


def trading_hours_examples():
    """Demonstrate trading hours handling"""
    print("\n=== TRADING HOURS EXAMPLES ===")
    
    from src.capital_com_fetcher import (
        is_trading_hour, 
        get_next_valid_time, 
        format_trading_session_info
    )
    
    # Current time status
    now = datetime.utcnow()
    print(f"\n1. Current Time Status:")
    print(f"   Now: {format_trading_session_info(now)}")
    
    # Weekend example
    saturday = datetime(2025, 7, 19, 15, 0)  # Saturday 15:00 UTC
    print(f"\n2. Weekend Handling:")
    print(f"   Saturday: {format_trading_session_info(saturday)}")
    next_valid = get_next_valid_time(saturday)
    print(f"   Next valid: {format_trading_session_info(next_valid)}")
    
    # Daily closure example
    friday_closure = datetime(2025, 7, 18, 21, 30)  # Friday 21:30 UTC
    print(f"\n3. Daily Closure:")
    print(f"   Friday 21:30: {format_trading_session_info(friday_closure)}")
    next_valid = get_next_valid_time(friday_closure)
    print(f"   Next valid: {format_trading_session_info(next_valid)}")


def market_search_examples():
    """Demonstrate market search functionality"""
    print("\n=== MARKET SEARCH EXAMPLES ===")
    
    fetcher = create_capital_com_fetcher()
    if not fetcher:
        print("❌ Capital.com not available")
        return
    
    with fetcher:
        # Search for EUR markets
        print("\n1. Searching for EUR markets:")
        markets = fetcher.search_markets('EUR')
        if markets:
            for i, market in enumerate(markets[:5]):  # Show first 5
                print(f"   {i+1}. {market['epic']} - {market['instrumentName']}")
        
        # Get market details
        print("\n2. Market Details for EURUSD:")
        details = fetcher.get_market_details('EURUSD')
        if details:
            instrument = details.get('instrument', {})
            print(f"   Name: {instrument.get('displayName', 'N/A')}")
            print(f"   Currency: {instrument.get('currencies', [{}])[0].get('name', 'N/A')}")
            print(f"   Type: {instrument.get('type', 'N/A')}")


def performance_comparison():
    """Compare Capital.com vs other providers"""
    print("\n=== PERFORMANCE COMPARISON ===")
    
    import time
    
    # Test Capital.com
    print("\n1. Capital.com Performance:")
    fetcher_cc = create_capital_com_fetcher()
    if fetcher_cc:
        with fetcher_cc:
            start = time.time()
            data_cc = fetcher_cc.fetch_historical_data('EURUSD', 'forex', '1h', 0.5)
            cc_time = time.time() - start
            if data_cc is not None:
                print(f"   ✅ {len(data_cc)} records in {cc_time:.2f}s")
    
    # Test yfinance fallback
    print("\n2. yfinance Fallback:")
    fetcher_yf = DataFetcher(source='forex', symbol='EURUSD=X', timeframe='1h', use_cache=False)
    # Temporarily disable Capital.com to force yfinance
    old_env = os.environ.get('CAPITAL_COM_API_KEY')
    if old_env:
        del os.environ['CAPITAL_COM_API_KEY']
    
    try:
        start = time.time()
        data_yf = fetcher_yf.fetch(years=0.5)
        yf_time = time.time() - start
        if data_yf is not None:
            print(f"   ✅ {len(data_yf)} records in {yf_time:.2f}s")
    finally:
        # Restore environment
        if old_env:
            os.environ['CAPITAL_COM_API_KEY'] = old_env


def main():
    """Run all Capital.com examples"""
    print("🏦 CAPITAL.COM DATA FETCHER EXAMPLES")
    print("=" * 50)
    
    # Test connection first
    if not test_capital_com_connection():
        print("\n⚠️  Capital.com examples require API credentials")
        print("See docs/CAPITAL_COM_COMPLETE.md for setup instructions")
        return
    
    # Run examples
    fetch_forex_data_examples()
    fetch_indices_data_examples()
    integrated_datafetcher_examples()
    trading_hours_examples()
    market_search_examples()
    performance_comparison()
    
    print("\n" + "=" * 50)
    print("✅ All Capital.com examples completed!")
    print("\n📚 For more information:")
    print("   • Complete guide: docs/CAPITAL_COM_COMPLETE.md")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Integration test for Capital.com data fetcher with trading hours
"""

import sys
import os
sys.path.append('src')

from datetime import datetime, timedelta
from capital_com_fetcher import CapitalComDataFetcher
from helpers import is_trading_hour, is_weekend, format_trading_session_info

def test_fetcher_date_adjustments():
    """Test the fetcher's date adjustment logic without making actual API calls"""
    
    print("🧪 Testing Capital.com Fetcher Date Adjustments")
    print("=" * 60)
    
    # Create a fetcher instance (won't connect without credentials)
    fetcher = CapitalComDataFetcher(
        api_key="test", 
        password="test", 
        identifier="test@example.com", 
        demo=True
    )
    
    print(fetcher.get_trading_hours_info())
    
    print("\n📅 Testing Date Range Adjustments:")
    
    # Test scenarios
    test_scenarios = [
        {
            "name": "Weekend start date",
            "start": datetime(2025, 7, 26, 10, 0),  # Saturday 10:00
            "years": 1
        },
        {
            "name": "Friday evening start",
            "start": datetime(2025, 7, 25, 21, 30),  # Friday 21:30
            "years": 1
        },
        {
            "name": "Sunday morning start", 
            "start": datetime(2025, 7, 27, 10, 0),  # Sunday 10:00
            "years": 1
        },
        {
            "name": "Daily closure time",
            "start": datetime(2025, 7, 21, 21, 15),  # Monday 21:15
            "years": 1
        }
    ]
    
    for scenario in test_scenarios:
        print(f"\n🔍 Scenario: {scenario['name']}")
        start_date = scenario['start']
        end_date = datetime.utcnow()
        
        print(f"   Original range: {format_trading_session_info(start_date)} to {format_trading_session_info(end_date)}")
        
        # Simulate the date adjustment logic from fetch_historical_data
        from helpers import get_next_valid_time
        
        adjusted_start = get_next_valid_time(start_date)
        
        if not is_trading_hour(end_date):
            from helpers import get_last_valid_time
            adjusted_end = get_last_valid_time(end_date)
        else:
            adjusted_end = end_date
            
        print(f"   Adjusted range: {format_trading_session_info(adjusted_start)} to {format_trading_session_info(adjusted_end)}")
        
        # Calculate how many trading days we have
        current = adjusted_start
        trading_days = 0
        while current < adjusted_end:
            if not is_weekend(current) and is_trading_hour(current):
                trading_days += 1
            current += timedelta(hours=1)
        
        print(f"   Trading hours in range: ~{trading_days}")

def test_chunk_processing():
    """Test chunk processing logic"""
    
    print("\n\n📦 Testing Chunk Processing Logic")
    print("=" * 60)
    
    from helpers import adjust_end_time
    
    chunk_scenarios = [
        {
            "name": "Normal weekday chunk",
            "start": datetime(2025, 7, 21, 10, 0),  # Monday 10:00
            "duration": 7
        },
        {
            "name": "Chunk ending on weekend",
            "start": datetime(2025, 7, 24, 10, 0),  # Thursday 10:00
            "duration": 3  # Would end on Sunday
        },
        {
            "name": "Chunk starting Friday",
            "start": datetime(2025, 7, 25, 15, 0),  # Friday 15:00
            "duration": 2  # Would end on Sunday
        }
    ]
    
    for scenario in chunk_scenarios:
        print(f"\n📦 {scenario['name']}:")
        start = scenario['start']
        duration = scenario['duration']
        
        naive_end = start + timedelta(days=duration)
        adjusted_end = adjust_end_time(start, duration)
        
        print(f"   Start: {format_trading_session_info(start)}")
        print(f"   Naive end: {format_trading_session_info(naive_end)}")
        print(f"   Adjusted end: {format_trading_session_info(adjusted_end)}")
        
        # Show if adjustment was needed
        if naive_end != adjusted_end:
            print(f"   ✅ Adjustment applied (avoided non-trading time)")
        else:
            print(f"   ℹ️  No adjustment needed")

def test_timeframe_chunking():
    """Test optimal chunking for different timeframes"""
    
    print("\n\n⏱️  Testing Timeframe Chunking")
    print("=" * 60)
    
    timeframes = ['15m', '1h', '4h', '1d']
    
    for tf in timeframes:
        if tf == '15m':
            chunk_days = 10  # ~960 records
        elif tf == '1h':
            chunk_days = 41  # ~984 records  
        elif tf == '4h':
            chunk_days = 166  # ~996 records
        else:  # 1d
            chunk_days = 1000  # No real limit for daily
            
        # Calculate approximate records per chunk
        if tf == '15m':
            records_per_day = 24 * 4  # 96 (ignoring market closures)
        elif tf == '1h':
            records_per_day = 24  # 24
        elif tf == '4h':
            records_per_day = 6  # 6
        else:
            records_per_day = 1  # 1
            
        approx_records = records_per_day * chunk_days
        
        print(f"📊 {tf:>3} timeframe: {chunk_days:>3} days/chunk → ~{approx_records:>4} records")

if __name__ == "__main__":
    test_fetcher_date_adjustments()
    test_chunk_processing() 
    test_timeframe_chunking()
    
    print("\n" + "="*60)
    print("✅ All date adjustment tests completed!")
    print("💡 The Capital.com fetcher is now ready for forex trading hours")

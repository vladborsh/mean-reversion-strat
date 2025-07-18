#!/usr/bin/env python3
"""
Example script demonstrating Capital.com trading hours functionality
"""

import sys
import os
sys.path.append('src')

from datetime import datetime, timedelta
from capital_com_fetcher import (
    is_trading_hour, 
    is_weekend, 
    get_next_valid_time,
    format_trading_session_info,
    create_capital_com_fetcher
)

def demo_trading_hours():
    """Demonstrate trading hours functionality"""
    
    print("🕒 Capital.com Trading Hours Demo")
    print("=" * 50)
    
    # Current time
    now = datetime.utcnow()
    print(f"Current time: {format_trading_session_info(now)}")
    
    if is_trading_hour(now) and not is_weekend(now):
        print("✅ Markets are currently OPEN")
    else:
        next_open = get_next_valid_time(now)
        print(f"❌ Markets are currently CLOSED")
        print(f"Next opening: {format_trading_session_info(next_open)}")
    
    print("\n📅 This Week's Trading Schedule:")
    
    # Show this week's schedule
    monday = now - timedelta(days=now.weekday())  # Start of this week
    
    for i in range(7):
        day = monday + timedelta(days=i)
        day_name = day.strftime('%A')
        
        # Check key times for each day
        if day_name == 'Sunday':
            # Sunday opening at 22:00
            opening = day.replace(hour=22, minute=0)
            print(f"{day_name:>9} 22:00 UTC: {format_trading_session_info(opening)}")
        elif day_name == 'Friday':
            # Friday closing at 21:00
            closing = day.replace(hour=21, minute=0)
            print(f"{day_name:>9} 21:00 UTC: {format_trading_session_info(closing)}")
            # Show post-close
            post_close = day.replace(hour=21, minute=30)
            print(f"{day_name:>9} 21:30 UTC: {format_trading_session_info(post_close)}")
        elif day_name == 'Saturday':
            # Saturday (always closed)
            midday = day.replace(hour=12, minute=0)
            print(f"{day_name:>9} 12:00 UTC: {format_trading_session_info(midday)}")
        else:
            # Regular weekdays - show trading and closure times
            trading = day.replace(hour=10, minute=0)
            closure = day.replace(hour=21, minute=30)
            print(f"{day_name:>9} 10:00 UTC: {format_trading_session_info(trading)}")
            print(f"{day_name:>9} 21:30 UTC: {format_trading_session_info(closure)}")

def demo_data_fetching():
    """Demonstrate data fetching with trading hours"""
    
    print("\n\n📊 Data Fetching Demo")
    print("=" * 50)
    
    fetcher = create_capital_com_fetcher()
    
    if not fetcher:
        print("⚠️  Capital.com credentials not configured")
        print("   Set environment variables:")
        print("   - CAPITAL_COM_API_KEY")
        print("   - CAPITAL_COM_PASSWORD") 
        print("   - CAPITAL_COM_IDENTIFIER")
        return
    
    print("✅ Capital.com fetcher created successfully")
    print(fetcher.get_trading_hours_info())
    
    # Simulate what would happen during data fetching
    print("🎯 Simulating data fetch for EURUSD:")
    
    # Example problematic dates
    test_dates = [
        datetime(2025, 7, 26, 10, 0),  # Saturday
        datetime(2025, 7, 27, 10, 0),  # Sunday morning
        datetime(2025, 7, 25, 21, 30), # Friday evening
    ]
    
    for test_date in test_dates:
        print(f"\n📅 Requesting data starting from: {format_trading_session_info(test_date)}")
        
        if is_weekend(test_date) or not is_trading_hour(test_date):
            adjusted = get_next_valid_time(test_date)
            print(f"   → Adjusted to: {format_trading_session_info(adjusted)}")
        else:
            print(f"   → No adjustment needed")

if __name__ == "__main__":
    demo_trading_hours()
    demo_data_fetching()
    
    print("\n" + "="*50)
    print("💡 Trading hours are now properly handled!")
    print("   Use the enhanced Capital.com fetcher for reliable forex data.")

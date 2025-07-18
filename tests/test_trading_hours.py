#!/usr/bin/env python3
"""
Test script for Capital.com trading hours adjustments
"""

import sys
import os
sys.path.append('src')

from datetime import datetime, timedelta
from helpers import (
    is_weekend, 
    is_trading_hour, 
    get_next_valid_time, 
    adjust_end_time,
    format_trading_session_info
)

def test_trading_hours():
    """Test trading hours logic with various scenarios"""
    
    print("🧪 Testing Trading Hours Logic")
    print("=" * 50)
    
    # Test cases: [description, datetime, expected_trading_status]
    test_cases = [
        # Weekdays - trading hours
        ("Monday 10:00 UTC", datetime(2025, 7, 21, 10, 0), True),
        ("Wednesday 15:30 UTC", datetime(2025, 7, 23, 15, 30), True),
        ("Friday 20:00 UTC", datetime(2025, 7, 25, 20, 0), True),
        
        # Weekdays - non-trading hours (daily break)
        ("Monday 21:30 UTC", datetime(2025, 7, 21, 21, 30), False),
        ("Tuesday 21:00 UTC", datetime(2025, 7, 22, 21, 0), False),
        
        # Friday close
        ("Friday 21:00 UTC", datetime(2025, 7, 25, 21, 0), False),
        ("Friday 21:30 UTC", datetime(2025, 7, 25, 21, 30), False),
        
        # Weekend
        ("Saturday 10:00 UTC", datetime(2025, 7, 26, 10, 0), False),
        ("Sunday 10:00 UTC", datetime(2025, 7, 27, 10, 0), False),
        ("Sunday 21:30 UTC", datetime(2025, 7, 27, 21, 30), False),
        
        # Sunday open
        ("Sunday 22:00 UTC", datetime(2025, 7, 27, 22, 0), True),
        ("Sunday 23:00 UTC", datetime(2025, 7, 27, 23, 0), True),
    ]
    
    print("\n📊 Trading Hours Tests:")
    for description, test_time, expected in test_cases:
        is_trading = is_trading_hour(test_time) and not is_weekend(test_time)
        status = "✅" if is_trading == expected else "❌"
        print(f"{status} {description}: {format_trading_session_info(test_time)}")
    
    print("\n🔄 Next Valid Time Tests:")
    adjustment_tests = [
        ("Friday 21:30 UTC", datetime(2025, 7, 25, 21, 30)),
        ("Saturday 10:00 UTC", datetime(2025, 7, 26, 10, 0)),
        ("Sunday 10:00 UTC", datetime(2025, 7, 27, 10, 0)),
        ("Monday 21:30 UTC", datetime(2025, 7, 21, 21, 30)),
    ]
    
    for description, test_time in adjustment_tests:
        next_valid = get_next_valid_time(test_time)
        print(f"📅 {description} → {format_trading_session_info(next_valid)}")
    
    print("\n📦 Chunk End Adjustment Tests:")
    chunk_tests = [
        ("Monday start, 7-day chunk", datetime(2025, 7, 21, 10, 0), 7),
        ("Thursday start, 3-day chunk", datetime(2025, 7, 24, 10, 0), 3),
        ("Friday start, 3-day chunk", datetime(2025, 7, 25, 10, 0), 3),
    ]
    
    for description, start_time, duration in chunk_tests:
        end_time = adjust_end_time(start_time, duration)
        print(f"📦 {description}:")
        print(f"   Start: {format_trading_session_info(start_time)}")
        print(f"   End:   {format_trading_session_info(end_time)}")

if __name__ == "__main__":
    test_trading_hours()

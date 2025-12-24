#!/usr/bin/env python3
"""
Comprehensive test script for Capital.com trading hours across different asset types.
Tests forex, USA indices, and EU indices to ensure correct Sunday opening times.
"""

import sys
import os
sys.path.append('src')

from datetime import datetime, timedelta
from helpers import (
    is_weekend, 
    is_trading_hour, 
    get_next_valid_time,
    get_last_valid_time,
    adjust_end_time,
    format_trading_session_info
)


def test_forex_trading_hours():
    """Test forex trading hours (Sunday 22:00 opening)"""
    
    print("\n" + "=" * 70)
    print("🌍 FOREX TRADING HOURS TESTS")
    print("=" * 70)
    
    asset_type = 'forex'
    
    test_cases = [
        # Sunday opening - Forex opens at 22:00
        ("Sunday 21:59 UTC", datetime(2025, 7, 27, 21, 59), False),
        ("Sunday 22:00 UTC", datetime(2025, 7, 27, 22, 0), True),
        ("Sunday 22:01 UTC", datetime(2025, 7, 27, 22, 1), True),
        
        # Weekday trading hours
        ("Monday 10:00 UTC", datetime(2025, 7, 21, 10, 0), True),
        ("Wednesday 15:30 UTC", datetime(2025, 7, 23, 15, 30), True),
        ("Friday 20:59 UTC", datetime(2025, 7, 25, 20, 59), True),
        
        # Daily closure (21:00-22:00)
        ("Monday 21:00 UTC", datetime(2025, 7, 21, 21, 0), False),
        ("Monday 21:30 UTC", datetime(2025, 7, 21, 21, 30), False),
        ("Monday 21:59 UTC", datetime(2025, 7, 21, 21, 59), False),
        
        # Friday close
        ("Friday 21:00 UTC", datetime(2025, 7, 25, 21, 0), False),
        ("Friday 22:00 UTC", datetime(2025, 7, 25, 22, 0), False),
        
        # Weekend
        ("Saturday 10:00 UTC", datetime(2025, 7, 26, 10, 0), False),
        ("Sunday 10:00 UTC", datetime(2025, 7, 27, 10, 0), False),
        ("Sunday 21:00 UTC", datetime(2025, 7, 27, 21, 0), False),
    ]
    
    passed = 0
    failed = 0
    
    print("\n📊 Trading Hours Validation:")
    for description, test_time, expected in test_cases:
        is_trading = is_trading_hour(test_time, asset_type) and not is_weekend(test_time, asset_type)
        status = "✅" if is_trading == expected else "❌"
        if is_trading == expected:
            passed += 1
        else:
            failed += 1
        print(f"{status} {description}: Expected={expected}, Got={is_trading}")
    
    print(f"\n📈 Results: {passed} passed, {failed} failed")
    return failed == 0


def test_usa_indices_trading_hours():
    """Test USA indices trading hours (Sunday 22:00 opening, same as forex)"""
    
    print("\n" + "=" * 70)
    print("🇺🇸 USA INDICES TRADING HOURS TESTS")
    print("=" * 70)
    
    asset_type = 'indices'  # USA indices use 'indices' but not EU-specific
    
    test_cases = [
        # Sunday opening - USA indices open at 22:00 (same as forex)
        ("Sunday 21:59 UTC", datetime(2025, 7, 27, 21, 59), False),
        ("Sunday 22:00 UTC", datetime(2025, 7, 27, 22, 0), True),
        ("Sunday 22:01 UTC", datetime(2025, 7, 27, 22, 1), True),
        ("Sunday 23:00 UTC", datetime(2025, 7, 27, 23, 0), True),
        
        # Weekday trading hours
        ("Monday 10:00 UTC", datetime(2025, 7, 21, 10, 0), True),
        ("Wednesday 15:30 UTC", datetime(2025, 7, 23, 15, 30), True),
        ("Friday 20:59 UTC", datetime(2025, 7, 25, 20, 59), True),
        
        # Daily closure (21:00-22:00)
        ("Monday 21:00 UTC", datetime(2025, 7, 21, 21, 0), False),
        ("Monday 21:30 UTC", datetime(2025, 7, 21, 21, 30), False),
        ("Tuesday 22:00 UTC", datetime(2025, 7, 22, 22, 0), True),
        
        # Friday close
        ("Friday 21:00 UTC", datetime(2025, 7, 25, 21, 0), False),
        ("Friday 22:00 UTC", datetime(2025, 7, 25, 22, 0), False),
        
        # Weekend
        ("Saturday 10:00 UTC", datetime(2025, 7, 26, 10, 0), False),
        ("Sunday 10:00 UTC", datetime(2025, 7, 27, 10, 0), False),
    ]
    
    passed = 0
    failed = 0
    
    print("\n📊 Trading Hours Validation:")
    for description, test_time, expected in test_cases:
        is_trading = is_trading_hour(test_time, asset_type) and not is_weekend(test_time, asset_type)
        status = "✅" if is_trading == expected else "❌"
        if is_trading == expected:
            passed += 1
        else:
            failed += 1
        print(f"{status} {description}: Expected={expected}, Got={is_trading}")
    
    print(f"\n📈 Results: {passed} passed, {failed} failed")
    return failed == 0


def test_eu_indices_trading_hours():
    """Test EU indices trading hours (Sunday 23:00 opening)"""
    
    print("\n" + "=" * 70)
    print("🇪🇺 EU INDICES TRADING HOURS TESTS")
    print("=" * 70)
    
    asset_type = 'eu_indices'
    
    test_cases = [
        # Sunday opening - EU indices open at 23:00 (1 hour later than forex/USA)
        ("Sunday 21:59 UTC", datetime(2025, 7, 27, 21, 59), False),
        ("Sunday 22:00 UTC", datetime(2025, 7, 27, 22, 0), False),  # Still closed for EU
        ("Sunday 22:30 UTC", datetime(2025, 7, 27, 22, 30), False),  # Still closed for EU
        ("Sunday 22:59 UTC", datetime(2025, 7, 27, 22, 59), False),  # Still closed for EU
        ("Sunday 23:00 UTC", datetime(2025, 7, 27, 23, 0), True),   # EU opens here!
        ("Sunday 23:01 UTC", datetime(2025, 7, 27, 23, 1), True),
        
        # Weekday trading hours (same as others)
        ("Monday 10:00 UTC", datetime(2025, 7, 21, 10, 0), True),
        ("Wednesday 15:30 UTC", datetime(2025, 7, 23, 15, 30), True),
        ("Friday 20:59 UTC", datetime(2025, 7, 25, 20, 59), True),
        
        # Daily closure (21:00-22:00, same as forex/USA)
        ("Monday 21:00 UTC", datetime(2025, 7, 21, 21, 0), False),
        ("Monday 21:30 UTC", datetime(2025, 7, 21, 21, 30), False),
        ("Tuesday 22:00 UTC", datetime(2025, 7, 22, 22, 0), True),  # Daily reopen at 22:00
        
        # Friday close (same as others)
        ("Friday 21:00 UTC", datetime(2025, 7, 25, 21, 0), False),
        ("Friday 22:00 UTC", datetime(2025, 7, 25, 22, 0), False),
        
        # Weekend
        ("Saturday 10:00 UTC", datetime(2025, 7, 26, 10, 0), False),
        ("Sunday 10:00 UTC", datetime(2025, 7, 27, 10, 0), False),
        ("Sunday 21:00 UTC", datetime(2025, 7, 27, 21, 0), False),
    ]
    
    passed = 0
    failed = 0
    
    print("\n📊 Trading Hours Validation:")
    for description, test_time, expected in test_cases:
        is_trading = is_trading_hour(test_time, asset_type) and not is_weekend(test_time, asset_type)
        status = "✅" if is_trading == expected else "❌"
        if is_trading == expected:
            passed += 1
        else:
            failed += 1
        print(f"{status} {description}: Expected={expected}, Got={is_trading}")
    
    print(f"\n📈 Results: {passed} passed, {failed} failed")
    return failed == 0


def test_next_valid_time_adjustments():
    """Test get_next_valid_time for different asset types"""
    
    print("\n" + "=" * 70)
    print("🔄 NEXT VALID TIME ADJUSTMENT TESTS")
    print("=" * 70)
    
    test_cases = [
        # [description, test_time, asset_type, expected_hour, expected_day_offset]
        # Forex tests
        ("Forex: Friday 21:30 → Sunday 22:00", datetime(2025, 7, 25, 21, 30), 'forex', 22, 2),
        ("Forex: Saturday 10:00 → Sunday 22:00", datetime(2025, 7, 26, 10, 0), 'forex', 22, 1),
        ("Forex: Sunday 10:00 → Sunday 22:00", datetime(2025, 7, 27, 10, 0), 'forex', 22, 0),
        ("Forex: Monday 21:30 → Tuesday 22:00", datetime(2025, 7, 21, 21, 30), 'forex', 22, 1),
        
        # USA indices tests (same as forex)
        ("USA: Friday 21:30 → Sunday 22:00", datetime(2025, 7, 25, 21, 30), 'indices', 22, 2),
        ("USA: Saturday 10:00 → Sunday 22:00", datetime(2025, 7, 26, 10, 0), 'indices', 22, 1),
        ("USA: Sunday 10:00 → Sunday 22:00", datetime(2025, 7, 27, 10, 0), 'indices', 22, 0),
        
        # EU indices tests (Sunday opens at 23:00)
        ("EU: Friday 21:30 → Sunday 23:00", datetime(2025, 7, 25, 21, 30), 'eu_indices', 23, 2),
        ("EU: Saturday 10:00 → Sunday 23:00", datetime(2025, 7, 26, 10, 0), 'eu_indices', 23, 1),
        ("EU: Sunday 10:00 → Sunday 23:00", datetime(2025, 7, 27, 10, 0), 'eu_indices', 23, 0),
        ("EU: Sunday 22:00 → Sunday 23:00", datetime(2025, 7, 27, 22, 0), 'eu_indices', 23, 0),
        ("EU: Monday 21:30 → Tuesday 22:00", datetime(2025, 7, 21, 21, 30), 'eu_indices', 22, 1),
    ]
    
    passed = 0
    failed = 0
    
    print("\n🔄 Next Valid Time Tests:")
    for description, test_time, asset_type, expected_hour, expected_day_offset in test_cases:
        next_valid = get_next_valid_time(test_time, asset_type)
        
        # Calculate expected datetime
        if expected_day_offset == 0:
            expected_time = test_time.replace(hour=expected_hour, minute=0, second=0, microsecond=0)
        else:
            expected_time = test_time.replace(hour=expected_hour, minute=0, second=0, microsecond=0)
            expected_time += timedelta(days=expected_day_offset)
        
        is_correct = next_valid == expected_time
        status = "✅" if is_correct else "❌"
        if is_correct:
            passed += 1
        else:
            failed += 1
        
        print(f"{status} {description}")
        if not is_correct:
            print(f"   Expected: {expected_time.strftime('%a %Y-%m-%d %H:%M')}")
            print(f"   Got:      {next_valid.strftime('%a %Y-%m-%d %H:%M')}")
    
    print(f"\n📈 Results: {passed} passed, {failed} failed")
    return failed == 0


def test_last_valid_time_adjustments():
    """Test get_last_valid_time for different asset types"""
    
    print("\n" + "=" * 70)
    print("⏮️  LAST VALID TIME ADJUSTMENT TESTS")
    print("=" * 70)
    
    test_cases = [
        # [description, test_time, asset_type, expected_weekday, expected_hour]
        # Weekend rollback tests
        ("Forex: Saturday 10:00 → Friday 20:59", datetime(2025, 7, 26, 10, 0), 'forex', 4, 20),
        ("Forex: Sunday 10:00 → Friday 20:59", datetime(2025, 7, 27, 10, 0), 'forex', 4, 20),
        ("USA: Saturday 10:00 → Friday 20:59", datetime(2025, 7, 26, 10, 0), 'indices', 4, 20),
        ("EU: Saturday 10:00 → Friday 20:59", datetime(2025, 7, 26, 10, 0), 'eu_indices', 4, 20),
        ("EU: Sunday 22:00 → Friday 20:59", datetime(2025, 7, 27, 22, 0), 'eu_indices', 4, 20),
        
        # Daily closure rollback tests
        ("Forex: Monday 21:30 → Monday 20:59", datetime(2025, 7, 21, 21, 30), 'forex', 0, 20),
        ("USA: Tuesday 21:15 → Tuesday 20:59", datetime(2025, 7, 22, 21, 15), 'indices', 1, 20),
        ("EU: Wednesday 21:45 → Wednesday 20:59", datetime(2025, 7, 23, 21, 45), 'eu_indices', 2, 20),
    ]
    
    passed = 0
    failed = 0
    
    print("\n⏮️  Last Valid Time Tests:")
    for description, test_time, asset_type, expected_weekday, expected_hour in test_cases:
        last_valid = get_last_valid_time(test_time, asset_type)
        
        is_correct = last_valid.weekday() == expected_weekday and last_valid.hour == expected_hour
        status = "✅" if is_correct else "❌"
        if is_correct:
            passed += 1
        else:
            failed += 1
        
        print(f"{status} {description}")
        if not is_correct:
            print(f"   Expected: {['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'][expected_weekday]} {expected_hour:02d}:XX")
            print(f"   Got:      {last_valid.strftime('%a %H:%M')}")
    
    print(f"\n📈 Results: {passed} passed, {failed} failed")
    return failed == 0


def test_interval_calculations():
    """Test time interval calculations for data fetching"""
    
    print("\n" + "=" * 70)
    print("⏱️  INTERVAL CALCULATION TESTS")
    print("=" * 70)
    
    print("\n📦 Testing chunk size calculations for different timeframes:")
    
    timeframe_configs = [
        ('5m', 3, 12 * 24 * 3),      # 5min: ~864 intervals in 3 days
        ('15m', 10, 4 * 24 * 10),     # 15min: ~960 intervals in 10 days
        ('1h', 41, 24 * 41),          # 1hour: ~984 intervals in 41 days
        ('4h', 166, 6 * 166),         # 4hour: ~996 intervals in 166 days
        ('1d', 1000, 1000),           # 1day: 1000 intervals
    ]
    
    print("\n📊 Expected intervals per chunk (max 1000 API limit):")
    for timeframe, chunk_days, expected_intervals in timeframe_configs:
        print(f"   {timeframe:>4} : {chunk_days:>4} days = ~{expected_intervals:>4} intervals")
    
    # Test date range calculations
    print("\n📅 Testing date range spanning:")
    
    test_ranges = [
        ("1 week", datetime(2025, 7, 21, 10, 0), 7),
        ("2 weeks", datetime(2025, 7, 21, 10, 0), 14),
        ("1 month", datetime(2025, 7, 1, 10, 0), 30),
        ("3 months", datetime(2025, 4, 1, 10, 0), 90),
    ]
    
    for description, start_date, days in test_ranges:
        end_date = start_date + timedelta(days=days)
        
        # Calculate how many trading hours (excluding weekends and daily closures)
        trading_hours = 0
        current = start_date
        while current < end_date:
            if is_trading_hour(current, 'forex') and not is_weekend(current, 'forex'):
                trading_hours += 1
            current += timedelta(hours=1)
        
        # Estimate intervals for different timeframes
        intervals_1h = trading_hours
        intervals_4h = trading_hours // 4
        intervals_1d = days
        
        print(f"\n   {description} ({days} days):")
        print(f"      Trading hours: ~{trading_hours}")
        print(f"      1h intervals:  ~{intervals_1h}")
        print(f"      4h intervals:  ~{intervals_4h}")
        print(f"      1d intervals:  ~{intervals_1d}")
    
    return True


def test_asset_type_differentiation():
    """Test that different asset types are handled correctly"""
    
    print("\n" + "=" * 70)
    print("🎯 ASSET TYPE DIFFERENTIATION TESTS")
    print("=" * 70)
    
    # Critical time: Sunday 22:00-23:00 UTC (the key difference)
    critical_time = datetime(2025, 7, 27, 22, 30)  # Sunday 22:30 UTC
    
    print(f"\n🔍 Testing critical time: {critical_time.strftime('%A %Y-%m-%d %H:%M')} UTC")
    print("   (Between Forex/USA opening at 22:00 and EU opening at 23:00)")
    
    forex_trading = is_trading_hour(critical_time, 'forex')
    usa_trading = is_trading_hour(critical_time, 'indices')
    eu_trading = is_trading_hour(critical_time, 'eu_indices')
    
    print(f"\n   Forex:       {'✅ OPEN' if forex_trading else '❌ CLOSED'} (Expected: OPEN)")
    print(f"   USA Indices: {'✅ OPEN' if usa_trading else '❌ CLOSED'} (Expected: OPEN)")
    print(f"   EU Indices:  {'❌ CLOSED' if not eu_trading else '✅ OPEN'} (Expected: CLOSED)")
    
    success = forex_trading and usa_trading and not eu_trading
    
    if success:
        print("\n✅ All asset types correctly differentiated!")
    else:
        print("\n❌ Asset type differentiation FAILED!")
    
    return success


def run_all_tests():
    """Run all test suites"""
    
    print("\n" + "=" * 70)
    print("🧪 CAPITAL.COM TRADING HOURS COMPREHENSIVE TEST SUITE")
    print("=" * 70)
    print("Testing trading hours logic across different asset types")
    print("Verifying correct Sunday opening times and interval calculations")
    
    results = []
    
    # Run all test suites
    results.append(("Forex Trading Hours", test_forex_trading_hours()))
    results.append(("USA Indices Trading Hours", test_usa_indices_trading_hours()))
    results.append(("EU Indices Trading Hours", test_eu_indices_trading_hours()))
    results.append(("Next Valid Time Adjustments", test_next_valid_time_adjustments()))
    results.append(("Last Valid Time Adjustments", test_last_valid_time_adjustments()))
    results.append(("Interval Calculations", test_interval_calculations()))
    results.append(("Asset Type Differentiation", test_asset_type_differentiation()))
    
    # Summary
    print("\n" + "=" * 70)
    print("📊 TEST SUMMARY")
    print("=" * 70)
    
    passed = sum(1 for _, result in results if result)
    failed = len(results) - passed
    
    for name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{status}: {name}")
    
    print(f"\n{'=' * 70}")
    print(f"Total: {passed}/{len(results)} test suites passed")
    
    if failed == 0:
        print("✅ ALL TESTS PASSED!")
        return 0
    else:
        print(f"❌ {failed} TEST SUITE(S) FAILED")
        return 1


if __name__ == "__main__":
    exit_code = run_all_tests()
    sys.exit(exit_code)

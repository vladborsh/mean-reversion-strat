#!/usr/bin/env python3
"""
Test script for the enhanced LiveSignalDetector with date range and caching features

This script demonstrates:
1. Using date range parameters to analyze historical periods
2. Caching functionality for improved performance
3. Comparing signals across different time periods
"""

import sys
import os
import json
import pandas as pd
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from src.data_fetcher import DataFetcher
from src.bot.live_signal_detector import LiveSignalDetector


def load_strategy_config(symbol: str, timeframe: str):
    """Load strategy configuration for a symbol"""
    config_file = os.path.join(os.path.dirname(__file__), 'assets_config_wr45.json')

    try:
        with open(config_file, 'r') as f:
            configs = json.load(f)

        # Find config for symbol
        symbol_key = f"{symbol}X_{timeframe}"
        if symbol_key in configs:
            return configs[symbol_key]['config']
        else:
            print(f"⚠️  No config found for {symbol_key}, using default")
            return None
    except Exception as e:
        print(f"❌ Error loading config: {e}")
        return None


def create_strategy_params(config):
    """Create strategy parameters from config"""
    if config is None:
        # Default parameters
        return {
            'bb_window': 20,
            'bb_std': 2.0,
            'vwap_window': 14,
            'vwap_std': 2.0,
            'atr_period': 14,
            'risk_per_position_pct': 1.0,
            'stop_loss_atr_multiplier': 2.0,
            'risk_reward_ratio': 2.0,
            'regime_min_score': 60
        }

    bb_config = config['BOLLINGER_BANDS']
    vwap_config = config['VWAP_BANDS']
    atr_config = config['ATR']
    risk_config = config['RISK_MANAGEMENT']
    strategy_config = config['STRATEGY_BEHAVIOR']

    return {
        'bb_window': bb_config['window'],
        'bb_std': bb_config['std_dev'],
        'vwap_window': vwap_config['window'],
        'vwap_std': vwap_config['std_dev'],
        'atr_period': atr_config['period'],
        'risk_per_position_pct': risk_config['risk_per_position_pct'],
        'stop_loss_atr_multiplier': risk_config['stop_loss_atr_multiplier'],
        'risk_reward_ratio': risk_config['risk_reward_ratio'],
        'regime_min_score': strategy_config['regime_min_score']
    }


def test_date_range_analysis():
    """Test signal detection with specific date ranges"""
    print("\n" + "="*80)
    print("TEST 1: Date Range Analysis")
    print("="*80)

    symbol = 'EURUSD'
    timeframe = '5m'

    # Initialize signal detector with caching
    detector = LiveSignalDetector(use_cache=True, cache_duration_hours=24)

    # Fetch data for the past month
    print(f"\n📊 Fetching {symbol} data...")
    fetcher = DataFetcher(
        source='forex',
        symbol=symbol,
        timeframe=timeframe,
        use_cache=True
    )

    # Get 30 days of data
    data = fetcher.fetch(years=0.1)  # ~36 days
    print(f"✅ Fetched {len(data)} candles")

    # Load strategy configuration
    config = load_strategy_config(symbol, timeframe)
    strategy_params = create_strategy_params(config)

    # Test 1: Analyze last 7 days
    end_date = datetime.now()
    start_date = end_date - timedelta(days=7)

    print(f"\n🔍 Analyzing last 7 days ({start_date.date()} to {end_date.date()})...")
    result1 = detector.analyze_symbol(
        data, strategy_params, symbol,
        start_date=start_date.strftime('%Y-%m-%d'),
        end_date=end_date.strftime('%Y-%m-%d')
    )

    print(f"Result: {result1['signal_type']} - {result1['reason']}")
    if result1['signal_type'] in ['long', 'short']:
        print(f"  Signal: {result1['direction']} @ {result1['entry_price']:.5f}")
        print(f"  SL: {result1['stop_loss']:.5f}, TP: {result1['take_profit']:.5f}")

    # Test 2: Analyze previous week (should use cache on second run)
    end_date = start_date
    start_date = end_date - timedelta(days=7)

    print(f"\n🔍 Analyzing previous week ({start_date.date()} to {end_date.date()})...")
    print("First run (should compute):")
    result2 = detector.analyze_symbol(
        data, strategy_params, symbol,
        start_date=start_date.strftime('%Y-%m-%d'),
        end_date=end_date.strftime('%Y-%m-%d')
    )

    print(f"Result: {result2['signal_type']} - {result2['reason']}")

    print("\nSecond run (should use cache):")
    result3 = detector.analyze_symbol(
        data, strategy_params, symbol,
        start_date=start_date.strftime('%Y-%m-%d'),
        end_date=end_date.strftime('%Y-%m-%d')
    )

    print(f"Result: {result3['signal_type']} - {result3['reason']}")
    print("✅ Cache test complete")


def test_caching_performance():
    """Test caching performance improvements"""
    print("\n" + "="*80)
    print("TEST 2: Caching Performance")
    print("="*80)

    symbol = 'GBPUSD'
    timeframe = '5m'

    # Initialize two detectors - one with cache, one without
    detector_cached = LiveSignalDetector(use_cache=True, cache_duration_hours=1)
    detector_no_cache = LiveSignalDetector(use_cache=False)

    # Fetch data
    print(f"\n📊 Fetching {symbol} data...")
    fetcher = DataFetcher(
        source='forex',
        symbol=symbol,
        timeframe=timeframe,
        use_cache=True
    )
    data = fetcher.fetch(years=0.05)  # ~18 days
    print(f"✅ Fetched {len(data)} candles")

    # Load strategy configuration
    config = load_strategy_config(symbol, timeframe)
    strategy_params = create_strategy_params(config)

    # Test with caching
    import time

    print("\n⏱️  Testing WITH caching:")
    times_cached = []
    for i in range(3):
        start_time = time.time()
        result = detector_cached.analyze_symbol(data, strategy_params, symbol)
        elapsed = time.time() - start_time
        times_cached.append(elapsed)
        print(f"  Run {i+1}: {elapsed:.3f}s - {result['signal_type']}")

    print("\n⏱️  Testing WITHOUT caching:")
    times_no_cache = []
    for i in range(3):
        start_time = time.time()
        result = detector_no_cache.analyze_symbol(data, strategy_params, symbol)
        elapsed = time.time() - start_time
        times_no_cache.append(elapsed)
        print(f"  Run {i+1}: {elapsed:.3f}s - {result['signal_type']}")

    # Compare performance
    avg_cached = sum(times_cached) / len(times_cached)
    avg_no_cache = sum(times_no_cache) / len(times_no_cache)
    speedup = avg_no_cache / avg_cached if avg_cached > 0 else 0

    print(f"\n📊 Performance Summary:")
    print(f"  Average with cache: {avg_cached:.3f}s")
    print(f"  Average without cache: {avg_no_cache:.3f}s")
    print(f"  Speedup: {speedup:.1f}x")


def test_historical_analysis():
    """Test analyzing different historical periods"""
    print("\n" + "="*80)
    print("TEST 3: Historical Period Analysis")
    print("="*80)

    symbol = 'AUDUSD'
    timeframe = '15m'

    # Initialize signal detector
    detector = LiveSignalDetector(use_cache=True, cache_duration_hours=24)

    # Fetch more historical data
    print(f"\n📊 Fetching {symbol} historical data...")
    fetcher = DataFetcher(
        source='forex',
        symbol=symbol,
        timeframe=timeframe,
        use_cache=True
    )
    data = fetcher.fetch(years=0.25)  # ~3 months
    print(f"✅ Fetched {len(data)} candles")

    # Load strategy configuration
    config = load_strategy_config(symbol, timeframe)
    strategy_params = create_strategy_params(config)

    # Analyze different weekly periods
    print("\n📈 Analyzing weekly signals over past month:")

    end_date = datetime.now()
    signals_found = []

    for week in range(4):
        week_end = end_date - timedelta(weeks=week)
        week_start = week_end - timedelta(days=7)

        print(f"\nWeek {week+1}: {week_start.date()} to {week_end.date()}")

        result = detector.analyze_symbol(
            data, strategy_params, symbol,
            start_date=week_start.strftime('%Y-%m-%d'),
            end_date=week_end.strftime('%Y-%m-%d')
        )

        if result['signal_type'] in ['long', 'short']:
            print(f"  ✅ SIGNAL: {result['direction']} @ {result['entry_price']:.5f}")
            print(f"     SL: {result['stop_loss']:.5f}, TP: {result['take_profit']:.5f}")
            signals_found.append({
                'week': week+1,
                'date_range': f"{week_start.date()} to {week_end.date()}",
                'signal': result
            })
        else:
            print(f"  No signal: {result['reason']}")

    # Summary
    print(f"\n📊 Summary: Found {len(signals_found)} signals in 4 weeks")
    for signal_info in signals_found:
        sig = signal_info['signal']
        print(f"  Week {signal_info['week']}: {sig['direction']} @ {sig['entry_price']:.5f}")


def main():
    """Run all tests"""
    print("\n🚀 LIVE SIGNAL DETECTOR - Enhanced Features Test")
    print("=" * 80)
    print("This script demonstrates the new features:")
    print("1. Date range filtering for historical analysis")
    print("2. Signal analysis caching for performance")
    print("3. Support for analyzing specific time periods")

    try:
        # Run tests
        test_date_range_analysis()
        test_caching_performance()
        test_historical_analysis()

        print("\n" + "="*80)
        print("✅ All tests completed successfully!")
        print("="*80)

    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
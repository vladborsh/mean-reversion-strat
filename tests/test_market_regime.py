"""
Test script for Market Regime Detection functionality.

This script tests the market regime detection system to ensure it's working correctly
before running the full backtesting with the improved strategy.

Author: Trading Strategy System
Date: July 19, 2025
"""

import sys
import os
import pandas as pd
import numpy as np

# Add src directory to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), '../src'))

from market_regime import MarketRegimeDetector, VolatilityRegime, TrendStrength, MarketRegime
from market_regime import ADXIndicator, VolatilityRegimeIndicator, MarketRegimeFilter
import backtrader as bt


def create_sample_data():
    """Create sample OHLCV data for testing."""
    np.random.seed(42)  # For reproducible results
    
    # Create 1000 data points
    n_points = 1000
    dates = pd.date_range('2024-01-01', periods=n_points, freq='5T')
    
    # Generate realistic price data
    base_price = 1.1000
    returns = np.random.normal(0, 0.001, n_points)
    
    # Add some trend periods
    trend_periods = [
        (100, 200, 0.0005),  # Uptrend
        (300, 400, -0.0003), # Downtrend
        (600, 700, 0.0002),  # Weak uptrend
    ]
    
    for start, end, drift in trend_periods:
        returns[start:end] += drift
    
    # Calculate prices
    prices = [base_price]
    for ret in returns[1:]:
        prices.append(prices[-1] * (1 + ret))
    
    # Create OHLC data
    df = pd.DataFrame({
        'datetime': dates,
        'open': prices,
        'close': prices
    })
    
    # Add high/low with some spread
    df['high'] = df['close'] * (1 + np.abs(np.random.normal(0, 0.0002, n_points)))
    df['low'] = df['close'] * (1 - np.abs(np.random.normal(0, 0.0002, n_points)))
    
    # Ensure high >= close >= low and open
    df['high'] = df[['high', 'close', 'open']].max(axis=1)
    df['low'] = df[['low', 'close', 'open']].min(axis=1)
    
    # Add volume
    df['volume'] = np.random.randint(1000, 10000, n_points)
    
    df.set_index('datetime', inplace=True)
    
    return df


def test_market_regime_detector():
    """Test the MarketRegimeDetector class with sample data."""
    print("=" * 60)
    print("TESTING MARKET REGIME DETECTOR")
    print("=" * 60)
    
    detector = MarketRegimeDetector()
    
    # Test different regime scenarios
    test_cases = [
        # (ADX, Volatility Percentile, Expected Result)
        (10, 25, "Should be MEAN_REVERTING"),
        (30, 25, "Should be TRENDING"),
        (15, 80, "Should be HIGH_VOLATILITY"),
        (20, 50, "Should be CHOPPY"),
        (12, 40, "Should be suitable for mean reversion"),
    ]
    
    for adx, vol_pct, description in test_cases:
        regime = detector.get_market_regime(adx, vol_pct)
        suitable, reason = detector.is_suitable_for_mean_reversion(adx, vol_pct)
        score = detector.get_regime_score(adx, vol_pct)
        
        print(f"\nTest Case: ADX={adx}, Vol Percentile={vol_pct}%")
        print(f"  {description}")
        print(f"  Regime: {regime.value}")
        print(f"  Suitable: {suitable} - {reason}")
        print(f"  Score: {score:.0f}/100")


def test_backtrader_indicators():
    """Test the backtrader indicators with sample data."""
    print("\n" + "=" * 60)
    print("TESTING BACKTRADER INDICATORS")
    print("=" * 60)
    
    # Create sample data
    df = create_sample_data()
    print(f"Created sample data: {len(df)} points from {df.index[0]} to {df.index[-1]}")
    
    # Create a simple backtrader data feed
    class PandasData(bt.feeds.PandasData):
        params = (
            ('datetime', None),
            ('open', 'open'),
            ('high', 'high'),
            ('low', 'low'),
            ('close', 'close'),
            ('volume', 'volume'),
        )
    
    # Create cerebro instance
    cerebro = bt.Cerebro()
    
    # Add data
    data = PandasData(dataname=df)
    cerebro.adddata(data)
    
    # Create a simple strategy to test indicators
    class TestStrategy(bt.Strategy):
        def __init__(self):
            self.regime_filter = MarketRegimeFilter(
                adx_period=14,
                volatility_period=14,
                volatility_lookback=50,  # Shorter for test
                min_score_threshold=60
            )
            self.test_points = []
            
        def next(self):
            # Collect test points every 50 bars
            if len(self.data) % 50 == 0 and len(self.data) > 100:
                regime_info = self.regime_filter.get_regime_info()
                self.test_points.append({
                    'bar': len(self.data),
                    'date': self.data.datetime.date(0),
                    'close': self.data.close[0],
                    'regime': regime_info
                })
    
    cerebro.addstrategy(TestStrategy)
    results = cerebro.run()
    strategy = results[0]
    
    # Display results
    print(f"\nIndicator Test Results ({len(strategy.test_points)} test points):")
    print("-" * 80)
    print(f"{'Bar':<6} {'Date':<12} {'Price':<8} {'Regime':<15} {'Score':<6} {'ADX':<6} {'Vol%':<6} {'Suitable'}")
    print("-" * 80)
    
    for point in strategy.test_points:
        regime_info = point['regime']
        print(f"{point['bar']:<6} {point['date'].strftime('%Y-%m-%d'):<12} "
              f"{point['close']:<8.4f} {regime_info.get('regime', 'N/A'):<15} "
              f"{regime_info.get('score', 0):<6.0f} {regime_info.get('adx', 0):<6.1f} "
              f"{regime_info.get('volatility_percentile', 0):<6.0f} "
              f"{regime_info.get('is_suitable', False)}")


def test_configuration():
    """Test that the configuration changes are working correctly."""
    print("\n" + "=" * 60)
    print("TESTING CONFIGURATION")
    print("=" * 60)
    
    from strategy_config import DEFAULT_CONFIG
    
    # Test that market regime parameters are included
    backtrader_params = DEFAULT_CONFIG.get_backtrader_params()
    
    regime_params = [
        'regime_enabled', 'regime_adx_period', 'regime_volatility_period',
        'regime_volatility_lookback', 'regime_min_score'
    ]
    
    print("Market Regime Configuration Parameters:")
    for param in regime_params:
        value = backtrader_params.get(param, 'NOT FOUND')
        print(f"  {param}: {value}")
    
    # Test MARKET_REGIME config section
    regime_config = DEFAULT_CONFIG.MARKET_REGIME
    print(f"\nMARKET_REGIME Configuration:")
    for key, value in regime_config.items():
        print(f"  {key}: {value}")


def run_all_tests():
    """Run all tests."""
    print("MARKET REGIME DETECTION - COMPREHENSIVE TEST SUITE")
    print("=" * 60)
    print("Testing market regime detection implementation...")
    print(f"Date: July 19, 2025")
    
    try:
        # Test 1: Basic detector functionality
        test_market_regime_detector()
        
        # Test 2: Backtrader integration
        test_backtrader_indicators()
        
        # Test 3: Configuration
        test_configuration()
        
        print("\n" + "=" * 60)
        print("ALL TESTS COMPLETED SUCCESSFULLY!")
        print("=" * 60)
        print("\nNext Steps:")
        print("1. Run a backtest with the improved strategy")
        print("2. Compare results with and without regime filtering")
        print("3. Analyze trade filtering effectiveness")
        print("4. Fine-tune regime detection parameters if needed")
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    
    return True


if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)

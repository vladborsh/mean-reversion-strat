#!/usr/bin/env python3
"""
Test VWAP with different anchor periods
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # Add project root to Python path

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from src.indicators import Indicators

def create_multi_period_test_data():
    """Create test data spanning multiple weeks/months for testing different anchor periods"""
    # Create 60 days of hourly data (covers multiple weeks and months)
    dates = pd.date_range(start='2024-01-01 00:00:00', end='2024-03-01 23:00:00', freq='1h')
    
    np.random.seed(42)
    base_price = 100.0
    data = []
    
    for i, date in enumerate(dates):
        # Create smooth trending price with some volatility
        daily_trend = 0.01 * np.sin(i / (24 * 7) * 2 * np.pi)  # Weekly trend cycle
        price_change = np.random.normal(daily_trend, 0.15)
        open_price = base_price + price_change
        
        high = open_price + abs(np.random.normal(0, 0.08))
        low = open_price - abs(np.random.normal(0, 0.08))
        close = open_price + np.random.normal(0, 0.08)
        volume = np.random.uniform(1000, 3000)
        
        data.append({
            'open': open_price,
            'high': high,
            'low': low,
            'close': close,
            'volume': volume
        })
        
        base_price = close
    
    return pd.DataFrame(data, index=dates)

def test_anchor_periods():
    """Test VWAP with different anchor periods"""
    print("=== VWAP Anchor Period Test ===")
    
    # Create test data
    df = create_multi_period_test_data()
    print(f"Created test data: {len(df)} rows from {df.index[0].date()} to {df.index[-1].date()}")
    print(f"Data spans {(df.index[-1] - df.index[0]).days} days")
    
    anchor_periods = ['day', 'week', 'month', 'year']
    results = {}
    
    for period in anchor_periods:
        try:
            print(f"\nTesting anchor period: {period}")
            vwap, upper, lower = Indicators.vwap_daily_reset(df, num_std=1.0, anchor_period=period)
            results[period] = {'vwap': vwap, 'upper': upper, 'lower': lower}
            print(f"✓ {period.capitalize()} anchor successful")
            print(f"  VWAP range: {vwap.min():.2f} - {vwap.max():.2f}")
            
            # Count number of resets (by checking where VWAP jumps significantly)
            vwap_diff = vwap.diff().abs()
            reset_threshold = vwap.std() * 0.5  # Threshold for detecting resets
            num_resets = (vwap_diff > reset_threshold).sum()
            print(f"  Estimated resets: {num_resets}")
            
        except Exception as e:
            print(f"✗ {period.capitalize()} anchor failed: {e}")
    
    return results

def analyze_reset_behavior(df, results):
    """Analyze reset behavior for different anchor periods"""
    print(f"\n=== Reset Behavior Analysis ===")
    
    for period, data in results.items():
        vwap = data['vwap']
        
        print(f"\n{period.upper()} Anchor Period:")
        
        # Show first few values to see reset behavior
        print("First 5 values:")
        for i in range(min(5, len(vwap))):
            idx = df.index[i]
            typical_price = (df.loc[idx, 'high'] + df.loc[idx, 'low'] + df.loc[idx, 'close']) / 3
            print(f"  {idx.strftime('%Y-%m-%d %H:%M')}: VWAP = {vwap.iloc[i]:.3f}, TP = {typical_price:.3f}")
        
        # Analyze period boundaries
        if period == 'day':
            # Check daily resets
            df_temp = df.copy()
            df_temp['vwap'] = vwap
            df_temp['date'] = df_temp.index.date
            
            reset_count = 0
            for date, day_data in df_temp.groupby('date'):
                first_vwap = day_data['vwap'].iloc[0]
                first_tp = (day_data['high'].iloc[0] + day_data['low'].iloc[0] + day_data['close'].iloc[0]) / 3
                if abs(first_vwap - first_tp) < 0.001:
                    reset_count += 1
            
            print(f"  Perfect daily resets: {reset_count}/{len(df_temp.groupby('date'))}")
        
        elif period == 'week':
            # Check weekly resets
            df_temp = df.copy()
            df_temp['vwap'] = vwap
            df_temp['week'] = df_temp.index.to_series().apply(
                lambda x: f"{x.isocalendar().year}-W{x.isocalendar().week:02d}"
            )
            
            reset_count = 0
            for week, week_data in df_temp.groupby('week'):
                first_vwap = week_data['vwap'].iloc[0]
                first_tp = (week_data['high'].iloc[0] + week_data['low'].iloc[0] + week_data['close'].iloc[0]) / 3
                if abs(first_vwap - first_tp) < 0.001:
                    reset_count += 1
            
            print(f"  Perfect weekly resets: {reset_count}/{len(df_temp.groupby('week'))}")

def compare_anchor_periods(results):
    """Compare VWAP values across different anchor periods"""
    print(f"\n=== Anchor Period Comparison ===")
    
    # Create comparison table for first 24 hours
    comparison_data = []
    for i in range(min(24, len(next(iter(results.values()))['vwap']))):
        row = {'hour': i}
        for period, data in results.items():
            row[f'{period}_vwap'] = data['vwap'].iloc[i]
        comparison_data.append(row)
    
    comparison_df = pd.DataFrame(comparison_data)
    
    print("VWAP Values for First 24 Hours:")
    print("Hour | Day    | Week   | Month  | Year")
    print("-" * 40)
    for _, row in comparison_df.head(12).iterrows():  # Show first 12 hours
        print(f"{int(row['hour']):4d} | {row['day_vwap']:6.2f} | {row['week_vwap']:6.2f} | {row['month_vwap']:6.2f} | {row['year_vwap']:6.2f}")
    
    # Calculate correlations
    print(f"\nCorrelations between anchor periods:")
    periods = list(results.keys())
    for i, period1 in enumerate(periods):
        for period2 in periods[i+1:]:
            vwap1 = results[period1]['vwap']
            vwap2 = results[period2]['vwap']
            corr = vwap1.corr(vwap2)
            print(f"  {period1} vs {period2}: {corr:.3f}")

def test_invalid_anchor_period():
    """Test error handling for invalid anchor periods"""
    print(f"\n=== Error Handling Test ===")
    
    df = create_multi_period_test_data().head(100)  # Small dataset for quick test
    
    try:
        vwap, upper, lower = Indicators.vwap_daily_reset(df, anchor_period='invalid')
        print("✗ Should have raised ValueError for invalid anchor period")
    except ValueError as e:
        print(f"✓ Correctly raised ValueError: {e}")
    except Exception as e:
        print(f"✗ Unexpected error: {e}")

def main():
    """Run comprehensive anchor period tests"""
    print("Testing VWAP with Different Anchor Periods")
    print("=" * 50)
    
    # Test all anchor periods
    results = test_anchor_periods()
    
    if results:
        # Create test data for analysis
        df = create_multi_period_test_data()
        
        # Analyze reset behavior
        analyze_reset_behavior(df, results)
        
        # Compare anchor periods
        compare_anchor_periods(results)
    
    # Test error handling
    test_invalid_anchor_period()
    
    print("\n" + "=" * 50)
    print("Anchor period test completed!")

if __name__ == "__main__":
    main()

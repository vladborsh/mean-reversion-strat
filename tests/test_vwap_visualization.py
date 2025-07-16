#!/usr/bin/env python3
"""
VWAP Test with Visualization
Compare the old rolling VWAP vs new daily-reset VWAP implementation
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # Add project root to Python path

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime, timedelta
from src.indicators import Indicators

def create_realistic_test_data():
    """Create realistic OHLCV data spanning multiple days with smooth price movement"""
    # Create 5 days of 15-minute data, 24/7 trading (no market hours filtering)
    dates = pd.date_range(start='2024-01-01 00:00:00', end='2024-01-05 23:45:00', freq='15T')
    
    np.random.seed(42)  # For reproducible results
    
    base_price = 150.0
    data = []
    
    for i, date in enumerate(dates):
        # Smooth price movement - no gaps, continuous trading
        # Create smooth price movement with some volatility
        volatility = 0.2 + 0.1 * np.sin(date.hour / 24 * 2 * np.pi)  # Slight daily volatility cycle
        
        price_change = np.random.normal(0, volatility)
        open_price = base_price + price_change
        
        # High and low around open
        high_noise = abs(np.random.exponential(0.15))
        low_noise = abs(np.random.exponential(0.15))
        high = open_price + high_noise
        low = open_price - low_noise
        
        # Close with some trend - smooth continuation
        trend = np.random.normal(0, 0.08)
        close = open_price + trend
        
        # Volume - varies throughout the day but no gaps
        hour_factor = 0.5 + 0.5 * np.sin(date.hour / 24 * 2 * np.pi)  # Daily volume cycle
        base_volume = 1000 + 1500 * hour_factor
        volume = base_volume * (1 + np.random.uniform(-0.2, 0.2))
        
        data.append({
            'open': open_price,
            'high': high,
            'low': low,
            'close': close,
            'volume': volume
        })
        
        base_price = close  # Carry forward the close smoothly - no gaps!
    
    df = pd.DataFrame(data, index=dates)
    return df

def plot_vwap_comparison(df, vwap_old, vwap_new, upper_old, lower_old, upper_new, lower_new):
    """Create comprehensive VWAP visualization"""
    fig, axes = plt.subplots(3, 1, figsize=(15, 12))
    
    # Plot 1: Price with both VWAP implementations
    ax1 = axes[0]
    ax1.plot(df.index, df['close'], label='Close Price', color='black', linewidth=1)
    ax1.plot(df.index, vwap_old, label='VWAP (Rolling Window)', color='blue', alpha=0.7)
    ax1.plot(df.index, vwap_new, label='VWAP (Daily Reset)', color='red', alpha=0.7)
    
    # Add daily vertical lines
    for date in pd.date_range(df.index[0].date(), df.index[-1].date(), freq='D'):
        ax1.axvline(x=date, color='gray', linestyle='--', alpha=0.3)
    
    ax1.set_title('VWAP Comparison: Rolling Window vs Daily Reset')
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    ax1.set_ylabel('Price')
    
    # Plot 2: New VWAP with bands (daily reset)
    ax2 = axes[1]
    ax2.plot(df.index, df['close'], label='Close Price', color='black', linewidth=1)
    ax2.plot(df.index, vwap_new, label='VWAP (Daily Reset)', color='red', linewidth=2)
    ax2.fill_between(df.index, lower_new, upper_new, alpha=0.2, color='red', label='VWAP Bands')
    ax2.plot(df.index, upper_new, color='red', linestyle='--', alpha=0.7, label='Upper Band')
    ax2.plot(df.index, lower_new, color='red', linestyle='--', alpha=0.7, label='Lower Band')
    
    # Add daily vertical lines
    for date in pd.date_range(df.index[0].date(), df.index[-1].date(), freq='D'):
        ax2.axvline(x=date, color='gray', linestyle='--', alpha=0.3)
    
    ax2.set_title('Daily Reset VWAP with Standard Deviation Bands')
    ax2.legend()
    ax2.grid(True, alpha=0.3)
    ax2.set_ylabel('Price')
    
    # Plot 3: Volume
    ax3 = axes[2]
    ax3.bar(df.index, df['volume'], width=0.01, alpha=0.6, color='green')
    ax3.set_title('Volume')
    ax3.set_ylabel('Volume')
    ax3.set_xlabel('Time')
    
    # Format x-axis
    for ax in axes:
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d %H:%M'))
        ax.xaxis.set_major_locator(mdates.HourLocator(interval=6))
        plt.setp(ax.xaxis.get_majorticklabels(), rotation=45)
    
    plt.tight_layout()
    plt.savefig('/Users/Vladyslav_Borsh/Documents/dev/mean-reversion-strat/vwap_comparison.png', 
                dpi=300, bbox_inches='tight')
    plt.show()

def analyze_daily_reset_behavior(df, vwap_new):
    """Analyze how VWAP resets each day"""
    print("\n=== Daily Reset Analysis ===")
    df_analysis = df.copy()
    df_analysis['vwap'] = vwap_new
    df_analysis['typical_price'] = (df['high'] + df['low'] + df['close']) / 3
    df_analysis['date'] = df_analysis.index.date
    
    for date, day_data in df_analysis.groupby('date'):
        first_row = day_data.iloc[0]
        last_row = day_data.iloc[-1]
        
        print(f"\n{date}:")
        print(f"  First candle: VWAP = {first_row['vwap']:.2f}, Typical Price = {first_row['typical_price']:.2f}")
        print(f"  Last candle:  VWAP = {last_row['vwap']:.2f}, Close = {last_row['close']:.2f}")
        print(f"  Daily range:  {day_data['close'].min():.2f} - {day_data['close'].max():.2f}")
        
        # Check if VWAP starts at typical price (indicating proper reset)
        reset_diff = abs(first_row['vwap'] - first_row['typical_price'])
        if reset_diff < 0.001:
            print(f"  ✓ VWAP properly resets (diff: {reset_diff:.6f})")
        else:
            print(f"  ✗ VWAP reset issue (diff: {reset_diff:.6f})")

def test_against_typescript_logic(df):
    """Test specific scenarios that the TypeScript implementation handles"""
    print("\n=== TypeScript Logic Validation ===")
    
    # Test the new implementation
    vwap_new, upper_new, lower_new = Indicators.vwap_daily_reset(df, num_std=1.0)
    
    # Manual calculation for first few points to verify logic
    print("\nManual verification of first few data points:")
    
    cumulative_volume = 0
    cumulative_value = 0
    deviations = []
    
    for i in range(min(5, len(df))):
        row = df.iloc[i]
        typical_price = (row['high'] + row['low'] + row['close']) / 3
        
        # Check if new day (reset logic)
        if i > 0:
            prev_date = df.index[i-1].date()
            curr_date = df.index[i].date()
            if curr_date != prev_date:
                cumulative_volume = 0
                cumulative_value = 0
                deviations = []
                print(f"  --- Day reset at index {i} ---")
        
        cumulative_volume += row['volume']
        cumulative_value += typical_price * row['volume']
        
        manual_vwap = cumulative_value / cumulative_volume
        deviation = typical_price - manual_vwap
        deviations.append(deviation)
        
        manual_std = np.std(deviations, ddof=0) if len(deviations) > 1 else 0
        
        print(f"  {i}: Manual VWAP = {manual_vwap:.3f}, "
              f"Calculated VWAP = {vwap_new.iloc[i]:.3f}, "
              f"Diff = {abs(manual_vwap - vwap_new.iloc[i]):.6f}")

def main():
    """Run comprehensive VWAP test with visualization"""
    print("Creating realistic test data...")
    df = create_realistic_test_data()
    print(f"Generated {len(df)} data points over {(df.index[-1] - df.index[0]).days + 1} days")
    
    print("\nCalculating VWAP indicators...")
    
    # Calculate old implementation (rolling window)
    try:
        vwap_old, upper_old, lower_old = Indicators.vwap_bands(df, window=78, num_std=2)  # ~1 day of 15min data
        print("✓ Old rolling VWAP calculated")
    except Exception as e:
        print(f"✗ Old VWAP failed: {e}")
        return
    
    # Calculate new implementation (daily reset)
    try:
        vwap_new, upper_new, lower_new = Indicators.vwap_daily_reset(df, num_std=2)
        print("✓ New daily-reset VWAP calculated")
    except Exception as e:
        print(f"✗ New VWAP failed: {e}")
        return
    
    # Analyze the results
    analyze_daily_reset_behavior(df, vwap_new)
    test_against_typescript_logic(df)
    
    # Create visualization
    print("\nCreating visualization...")
    plot_vwap_comparison(df, vwap_old, vwap_new, upper_old, lower_old, upper_new, lower_new)
    
    # Summary statistics
    print("\n=== Summary Statistics ===")
    print(f"Price range: {df['close'].min():.2f} - {df['close'].max():.2f}")
    print(f"Old VWAP range: {vwap_old.min():.2f} - {vwap_old.max():.2f}")
    print(f"New VWAP range: {vwap_new.min():.2f} - {vwap_new.max():.2f}")
    print(f"Correlation between implementations: {vwap_old.corr(vwap_new):.3f}")
    
    print(f"\nVisualization saved as 'vwap_comparison.png'")
    print("Test completed successfully!")

if __name__ == "__main__":
    main()

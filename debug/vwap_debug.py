#!/usr/bin/env python3
"""
Debug VWAP calculation to see why it's not showing properly on the chart
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # Add project root to Python path

from src.data_fetcher import DataFetcher
from src.indicators import Indicators
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

def debug_vwap():
    """Debug VWAP calculation step by step"""
    print("=== VWAP Debug Analysis ===")
    
    # Fetch data
    print("1. Fetching data...")
    fetcher = DataFetcher(source='forex', symbol='EURUSD=X', timeframe='1h')
    df = fetcher.fetch(years=1)
    print(f"   Data shape: {df.shape}")
    print(f"   Date range: {df.index[0]} to {df.index[-1]}")
    print(f"   Columns: {df.columns.tolist()}")
    
    # Check data quality
    print("\n2. Data quality check...")
    print(f"   Close price range: {df['close'].min():.6f} to {df['close'].max():.6f}")
    print(f"   Volume range: {df['volume'].min():.0f} to {df['volume'].max():.0f}")
    print(f"   Any NaN values: {df.isna().sum().sum()}")
    
    # Sample data
    print(f"\n3. Sample data (last 5 rows):")
    print(df.tail().to_string())
    
    # Calculate VWAP
    print("\n4. Calculating VWAP...")
    try:
        vwap, vwap_upper, vwap_lower = Indicators.vwap_daily_reset_forex_compatible(df, num_std=2, anchor_period='day')
        print(f"   VWAP calculated successfully")
        print(f"   VWAP shape: {vwap.shape}")
        print(f"   VWAP range: {vwap.min():.6f} to {vwap.max():.6f}")
        print(f"   VWAP NaN count: {vwap.isna().sum()}")
        print(f"   VWAP std dev: {vwap.std():.6f}")
        
        print(f"\n5. VWAP sample values (last 10):")
        sample_data = pd.DataFrame({
            'close': df['close'].tail(10),
            'vwap': vwap.tail(10),
            'vwap_upper': vwap_upper.tail(10),
            'vwap_lower': vwap_lower.tail(10)
        })
        print(sample_data.to_string())
        
        # Check if VWAP is too close to price (making it hard to see)
        price_vwap_diff = abs(df['close'] - vwap).mean()
        print(f"\n6. Average difference between Close and VWAP: {price_vwap_diff:.6f}")
        
        if price_vwap_diff < 0.001:
            print("   WARNING: VWAP is very close to price - might be hard to see on chart!")
        
        # Create a diagnostic plot
        print("\n7. Creating diagnostic plot...")
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(15, 10))
        
        # Plot last 200 points for clarity
        plot_data = df.tail(200)
        plot_vwap = vwap.tail(200)
        plot_vwap_upper = vwap_upper.tail(200)
        plot_vwap_lower = vwap_lower.tail(200)
        
        # Top plot: Price vs VWAP
        ax1.plot(plot_data.index, plot_data['close'], label='Close Price', color='black', linewidth=2)
        ax1.plot(plot_data.index, plot_vwap, label='VWAP', color='red', linewidth=3, alpha=0.8)
        ax1.fill_between(plot_data.index, plot_vwap_lower, plot_vwap_upper, 
                        alpha=0.2, color='red', label='VWAP Bands')
        ax1.plot(plot_data.index, plot_vwap_upper, color='red', linestyle='--', alpha=0.7)
        ax1.plot(plot_data.index, plot_vwap_lower, color='red', linestyle='--', alpha=0.7)
        
        ax1.set_title('Price vs VWAP (Last 200 periods)')
        ax1.legend()
        ax1.grid(True, alpha=0.3)
        ax1.set_ylabel('Price')
        
        # Bottom plot: Difference between Price and VWAP
        diff = plot_data['close'] - plot_vwap
        ax2.plot(plot_data.index, diff, label='Close - VWAP', color='blue')
        ax2.axhline(y=0, color='black', linestyle='-', alpha=0.5)
        ax2.fill_between(plot_data.index, 0, diff, alpha=0.3, color='blue')
        
        ax2.set_title('Difference: Close Price - VWAP')
        ax2.legend()
        ax2.grid(True, alpha=0.3)
        ax2.set_ylabel('Price Difference')
        ax2.set_xlabel('Time')
        
        plt.tight_layout()
        plt.savefig('/Users/Vladyslav_Borsh/Documents/dev/mean-reversion-strat/vwap_debug.png', 
                   dpi=300, bbox_inches='tight')
        print("   Diagnostic plot saved as 'vwap_debug.png'")
        
        return True
        
    except Exception as e:
        print(f"   ERROR calculating VWAP: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = debug_vwap()
    print(f"\nDebug analysis {'completed successfully' if success else 'failed'}")

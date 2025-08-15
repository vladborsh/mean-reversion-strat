#!/usr/bin/env python3
"""
Simple test to check data fetching and basic visualization
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # Add project root to Python path

import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
from src.data_fetcher import DataFetcher
from src.indicators import Indicators

def simple_test():
    """Test data fetching and basic VWAP calculation"""
    print("Testing data fetching...")
    
    try:
        fetcher = DataFetcher(source='forex', symbol='EURUSD', timeframe='1h')
        df = fetcher.fetch(years=1)  # Reduced to 1 year
        print(f"Data fetched successfully: {len(df)} rows")
        print(f"Data range: {df.index[0]} to {df.index[-1]}")
        print(f"Data columns: {df.columns.tolist()}")
        print(f"Sample data:\n{df.head()}")
        
        # Test VWAP calculation
        print("\nTesting VWAP calculation...")
        vwap, vwap_upper, vwap_lower = Indicators.vwap_daily_reset(df, num_std=2)
        print(f"VWAP calculated successfully: {len(vwap)} values")
        print(f"VWAP sample values: {vwap.head()}")
        
        # Test Bollinger Bands
        print("\nTesting Bollinger Bands...")
        bb_ma, bb_upper, bb_lower = Indicators.bollinger_bands(df)
        print(f"BB calculated successfully: {len(bb_ma)} values")
        
        # Simple plot test
        print("\nTesting simple plot...")
        fig, ax = plt.subplots(figsize=(12, 6))
        
        # Plot just last 100 points for clarity
        plot_data = df.tail(100)
        plot_vwap = vwap.tail(100)
        plot_bb_ma = bb_ma.tail(100)
        
        ax.plot(plot_data.index, plot_data['close'], label='Close', color='black')
        ax.plot(plot_data.index, plot_vwap, label='VWAP', color='red', linewidth=2)
        ax.plot(plot_data.index, plot_bb_ma, label='BB MA', color='blue')
        
        ax.legend()
        ax.set_title('Price with VWAP and BB MA (Last 100 periods)')
        ax.grid(True, alpha=0.3)
        
        plt.savefig('/Users/Vladyslav_Borsh/Documents/dev/mean-reversion-strat/simple_test.png', 
                   dpi=150, bbox_inches='tight')
        print("Simple plot saved as 'simple_test.png'")
        
        return True
        
    except Exception as e:
        print(f"Error during test: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = simple_test()
    print(f"\nTest {'PASSED' if success else 'FAILED'}")

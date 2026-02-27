#!/usr/bin/env python3
"""
Debug visualization to see what's happening with VWAP display
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # Add project root to Python path

from src.data_fetcher import DataFetcher
from src.indicators import Indicators
from src.visualization import plot_price_with_indicators
import pandas as pd
import numpy as np

def debug_main_visualization():
    """Debug the exact same code path as scripts/run_backtest.py"""
    print("Fetching EUR/USD data...")
    fetcher = DataFetcher(source='forex', symbol='EURUSD=X', timeframe='1h')
    df = fetcher.fetch(years=2)
    print(f"Data loaded: {len(df)} rows from {df.index[0]} to {df.index[-1]}")
    
    # Calculate indicators exactly like scripts/run_backtest.py
    params = {
        'bb_window': 20, 'bb_std': 2, 'vwap_window': 20, 
        'vwap_std': 2, 'vwap_anchor': 'day', 'stop_loss': 0.02, 'take_profit': 0.04
    }
    
    bb_ma, bb_upper, bb_lower = Indicators.bollinger_bands(df)
    vwap_anchor = params.get('vwap_anchor', 'day')
    vwap, vwap_upper, vwap_lower = Indicators.vwap_daily_reset(
        df, 
        num_std=params.get('vwap_std', 2),
        anchor_period=vwap_anchor
    )
    
    bb = {'ma': bb_ma, 'upper': bb_upper, 'lower': bb_lower}
    vwap_dict = {'vwap': vwap, 'upper': vwap_upper, 'lower': vwap_lower}
    
    # Debug: Check if VWAP data is valid
    print(f"\n=== VWAP Debug Info ===")
    print(f"VWAP shape: {vwap.shape}")
    print(f"VWAP first 5 values: {vwap.head()}")
    print(f"VWAP last 5 values: {vwap.tail()}")
    print(f"VWAP has NaN values: {vwap.isna().sum()}")
    print(f"VWAP range: {vwap.min():.4f} - {vwap.max():.4f}")
    
    print(f"\nVWAP Upper shape: {vwap_upper.shape}")
    print(f"VWAP Upper first 5 values: {vwap_upper.head()}")
    print(f"VWAP Upper has NaN values: {vwap_upper.isna().sum()}")
    
    print(f"\nVWAP Lower shape: {vwap_lower.shape}")
    print(f"VWAP Lower first 5 values: {vwap_lower.head()}")
    print(f"VWAP Lower has NaN values: {vwap_lower.isna().sum()}")
    
    # Use the same subset for both data and indicators
    plot_data = df.tail(500)
    plot_bb = {k: v.tail(500) if hasattr(v, 'tail') else v for k, v in bb.items()}
    plot_vwap = {k: v.tail(500) if hasattr(v, 'tail') else v for k, v in vwap_dict.items()}
    
    print(f"\n=== Plot Data Debug Info ===")
    print(f"Plot data shape: {plot_data.shape}")
    print(f"Plot VWAP shape: {plot_vwap['vwap'].shape}")
    print(f"Plot VWAP first 5 values: {plot_vwap['vwap'].head()}")
    print(f"Plot VWAP last 5 values: {plot_vwap['vwap'].tail()}")
    
    # Try the visualization
    try:
        print("\nAttempting visualization...")
        plot_price_with_indicators(plot_data, plot_bb, plot_vwap)
        print("Visualization completed successfully!")
    except Exception as e:
        print(f"Visualization error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    debug_main_visualization()

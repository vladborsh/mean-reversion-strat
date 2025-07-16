#!/usr/bin/env python3
"""
Debug VWAP calculation to find the issue
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # Add project root to Python path

from src.data_fetcher import DataFetcher
from src.indicators import Indicators
import pandas as pd
import numpy as np

def debug_vwap_calculation():
    """Debug why VWAP is returning NaN values"""
    print("Fetching data...")
    fetcher = DataFetcher(source='forex', symbol='EURUSD=X', timeframe='1h')
    df = fetcher.fetch(years=1)
    print(f"Data shape: {df.shape}")
    
    # Check data quality
    print(f"\nData Quality Check:")
    print(f"Columns: {df.columns.tolist()}")
    print(f"Data types:\n{df.dtypes}")
    print(f"Missing values:\n{df.isnull().sum()}")
    print(f"Zero values in volume: {(df['volume'] == 0).sum()}")
    print(f"Sample data:\n{df.head()}")
    print(f"Volume range: {df['volume'].min()} - {df['volume'].max()}")
    
    # Check if volume has any issues
    if df['volume'].isnull().any():
        print("WARNING: Volume column has NaN values!")
        # Fill NaN volume with 1 (default)
        df['volume'] = df['volume'].fillna(1)
        print("Filled NaN volume values with 1")
    
    if (df['volume'] == 0).any():
        print("WARNING: Volume column has zero values!")
        # Replace zero volume with 1
        df.loc[df['volume'] == 0, 'volume'] = 1
        print("Replaced zero volume values with 1")
    
    # Try VWAP calculation on a small subset first
    print(f"\nTesting VWAP on first 100 rows...")
    test_df = df.head(100).copy()
    
    try:
        vwap, vwap_upper, vwap_lower = Indicators.vwap_daily_reset(test_df, num_std=2)
        print(f"VWAP test successful!")
        print(f"VWAP sample: {vwap.head()}")
        print(f"VWAP upper sample: {vwap_upper.head()}")
        print(f"VWAP lower sample: {vwap_lower.head()}")
        
        # Check for NaN values
        print(f"NaN in VWAP: {vwap.isnull().sum()}")
        print(f"NaN in VWAP upper: {vwap_upper.isnull().sum()}")
        print(f"NaN in VWAP lower: {vwap_lower.isnull().sum()}")
        
    except Exception as e:
        print(f"VWAP calculation failed: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # Try with full dataset
    print(f"\nTesting VWAP on full dataset...")
    try:
        vwap_full, vwap_upper_full, vwap_lower_full = Indicators.vwap_daily_reset(df, num_std=2)
        print(f"Full VWAP calculation successful!")
        print(f"VWAP range: {vwap_full.min()} - {vwap_full.max()}")
        print(f"NaN count: {vwap_full.isnull().sum()}")
        
        # Find first non-NaN value
        first_valid = vwap_full.first_valid_index()
        if first_valid:
            print(f"First valid VWAP value at {first_valid}: {vwap_full.loc[first_valid]}")
        else:
            print("No valid VWAP values found!")
            
    except Exception as e:
        print(f"Full VWAP calculation failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    debug_vwap_calculation()

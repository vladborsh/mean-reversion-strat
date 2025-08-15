#!/usr/bin/env python3
"""
Test VWAP visualization to make sure it's clearly visible
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # Add project root to Python path

from src.data_fetcher import DataFetcher
from src.indicators import Indicators
from src.visualization import plot_price_with_indicators, plot_price_with_vwap_enhanced

def test_vwap_visibility():
    """Test VWAP visibility in charts"""
    print("Fetching EUR/USD data...")
    fetcher = DataFetcher(source='forex', symbol='EURUSD', timeframe='1h')
    df = fetcher.fetch(years=1)
    print(f"Data loaded: {len(df)} rows")
    
    # Calculate indicators
    params = {'bb_window': 20, 'bb_std': 2, 'vwap_std': 2, 'vwap_anchor': 'day'}
    
    print("Calculating Bollinger Bands...")
    bb_ma, bb_upper, bb_lower = Indicators.bollinger_bands(df)
    
    print("Calculating VWAP with daily reset...")
    vwap, vwap_upper, vwap_lower = Indicators.vwap_daily_reset(
        df, num_std=params['vwap_std'], anchor_period=params['vwap_anchor']
    )
    
    bb = {'ma': bb_ma, 'upper': bb_upper, 'lower': bb_lower}
    vwap_dict = {'vwap': vwap, 'upper': vwap_upper, 'lower': vwap_lower}
    
    # Print some VWAP info
    print(f"\nVWAP Information:")
    print(f"VWAP range: {vwap.min():.5f} - {vwap.max():.5f}")
    print(f"Current VWAP: {vwap.iloc[-1]:.5f}")
    print(f"Current Price: {df['close'].iloc[-1]:.5f}")
    print(f"VWAP vs Price difference: {abs(vwap.iloc[-1] - df['close'].iloc[-1]):.5f}")
    
    # Use last 200 points for better visibility
    plot_data = df.tail(200)
    plot_bb = {k: v.tail(200) for k, v in bb.items()}
    plot_vwap = {k: v.tail(200) for k, v in vwap_dict.items()}
    
    print("\nCreating standard visualization...")
    try:
        plot_price_with_indicators(plot_data, plot_bb, plot_vwap)
        print("Standard visualization completed!")
    except Exception as e:
        print(f"Standard visualization error: {e}")
    
    print("\nCreating enhanced visualization...")
    try:
        plot_price_with_vwap_enhanced(plot_data, plot_bb, plot_vwap)
        print("Enhanced visualization completed!")
    except Exception as e:
        print(f"Enhanced visualization error: {e}")

if __name__ == '__main__':
    test_vwap_visibility()

#!/usr/bin/env python3
"""
Test the main visualization with fixed VWAP
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # Add project root to Python path

from src.data_fetcher import DataFetcher
from src.indicators import Indicators
from src.visualization import plot_price_with_indicators

def test_main_viz():
    """Test the main visualization pipeline"""
    print("Testing main visualization with fixed VWAP...")
    
    # Fetch data like scripts/run_backtest.py
    fetcher = DataFetcher(source='forex', symbol='EURUSD', timeframe='1h')
    df = fetcher.fetch(years=2)
    
    # Calculate indicators like scripts/run_backtest.py
    params = {
        'bb_window': 20, 'bb_std': 2, 'vwap_window': 20, 
        'vwap_std': 2, 'vwap_anchor': 'day', 'stop_loss': 0.02, 'take_profit': 0.04
    }
    
    bb_ma, bb_upper, bb_lower = Indicators.bollinger_bands(df)
    vwap_anchor = params.get('vwap_anchor', 'day')
    vwap, vwap_upper, vwap_lower = Indicators.vwap_daily_reset_forex_compatible(
        df, 
        num_std=params.get('vwap_std', 2),
        anchor_period=vwap_anchor
    )
    
    bb = {'ma': bb_ma, 'upper': bb_upper, 'lower': bb_lower}
    vwap_dict = {'vwap': vwap, 'upper': vwap_upper, 'lower': vwap_lower}
    
    # Use the same subset for both data and indicators
    plot_data = df.tail(500)
    plot_bb = {k: v.tail(500) if hasattr(v, 'tail') else v for k, v in bb.items()}
    plot_vwap = {k: v.tail(500) if hasattr(v, 'tail') else v for k, v in vwap_dict.items()}
    
    print(f"Plot data shape: {plot_data.shape}")
    print(f"VWAP values range: {plot_vwap['vwap'].min():.6f} to {plot_vwap['vwap'].max():.6f}")
    print(f"Price values range: {plot_data['close'].min():.6f} to {plot_data['close'].max():.6f}")
    
    # Create visualization
    plot_price_with_indicators(plot_data, plot_bb, plot_vwap)
    print("Visualization completed!")

if __name__ == '__main__':
    test_main_viz()

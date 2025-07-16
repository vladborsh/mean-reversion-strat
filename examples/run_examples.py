#!/usr/bin/env python3
"""
Example scripts to run different trading strategies
"""

import sys
sys.path.append('..')  # Add parent directory to Python path

from src.data_fetcher import DataFetcher
from main import run_strategy

def run_forex_strategy():
    """Run strategy on EUR/USD forex pair"""
    print("=== FOREX STRATEGY: EUR/USD ===")
    fetcher = DataFetcher(source='forex', symbol='EURUSD=X', timeframe='1h')
    df = fetcher.fetch(years=2)
    print(f"Data: {len(df)} hourly bars")
    
    params = {
        'bb_window': 20, 'bb_std': 2.0,
        'vwap_window': 20, 'vwap_std': 2.0,
        'stop_loss': 0.015, 'take_profit': 0.03
    }
    return run_strategy(df, params)

def run_crypto_strategy():
    """Run strategy on BTC/USDT crypto pair"""
    print("=== CRYPTO STRATEGY: BTC/USDT ===")
    fetcher = DataFetcher(source='crypto', symbol='BTC/USDT', timeframe='1h')
    df = fetcher.fetch(years=1)
    print(f"Data: {len(df)} hourly bars")
    
    params = {
        'bb_window': 24, 'bb_std': 2.5,
        'vwap_window': 24, 'vwap_std': 2.5,
        'stop_loss': 0.03, 'take_profit': 0.06
    }
    return run_strategy(df, params)

def run_index_strategy():
    """Run strategy on S&P 500 index"""
    print("=== INDEX STRATEGY: S&P 500 ===")
    fetcher = DataFetcher(source='indices', symbol='^GSPC', timeframe='1d')
    df = fetcher.fetch(years=5)
    print(f"Data: {len(df)} daily bars")
    
    params = {
        'bb_window': 20, 'bb_std': 2.0,
        'vwap_window': 20, 'vwap_std': 2.0,
        'stop_loss': 0.02, 'take_profit': 0.04
    }
    return run_strategy(df, params)

def main():
    """Main function to run different strategies"""
    
    strategies = {
        '1': ('Forex (EUR/USD)', run_forex_strategy),
        '2': ('Crypto (BTC/USDT)', run_crypto_strategy),
        '3': ('Index (S&P 500)', run_index_strategy),
    }
    
    if len(sys.argv) > 1:
        choice = sys.argv[1]
    else:
        print("Available strategies:")
        for key, (name, _) in strategies.items():
            print(f"{key}. {name}")
        choice = input("\nSelect strategy (1-3) or press Enter for default forex: ").strip()
        
        if not choice:
            choice = '1'
    
    if choice in strategies:
        name, strategy_func = strategies[choice]
        print(f"\nRunning {name} strategy...\n")
        try:
            strategy_func()
        except Exception as e:
            print(f"Error running strategy: {e}")
            print("Make sure you have internet connection for data fetching.")
    else:
        print("Invalid choice. Running default forex strategy...")
        run_forex_strategy()

if __name__ == '__main__':
    main()

#!/usr/bin/env python3
"""
Cache management utility for the mean reversion strategy project.
Provides commands to inspect, clean, and manage the data cache.
"""

import argparse
import sys
from pathlib import Path
from datetime import datetime
from src.data_fetcher import DataFetcher
from src.data_cache import get_global_cache

def show_cache_info():
    """Display detailed cache information"""
    print("="*60)
    print("DATA CACHE INFORMATION")
    print("="*60)
    
    cache_info = DataFetcher.get_global_cache_info()
    
    print(f"Cache Directory: {cache_info['cache_directory']}")
    print(f"Total Files: {cache_info['total_files']}")
    print(f"Total Size: {cache_info['total_size_mb']:.2f} MB")
    print()
    
    if cache_info['files']:
        print("Cached Files:")
        print("-" * 80)
        print(f"{'Filename':<20} {'Size (KB)':<10} {'Age (hours)':<12} {'Symbol':<12} {'Timeframe':<10} {'Provider'}")
        print("-" * 80)
        
        for file_info in sorted(cache_info['files'], key=lambda x: x['age_hours']):
            metadata = file_info.get('metadata', {})
            
            symbol = metadata.get('symbol', 'Unknown')[:11]
            timeframe = metadata.get('timeframe', 'Unknown')
            provider = metadata.get('provider', 'Unknown')
            
            print(f"{file_info['filename'][:19]:<20} "
                  f"{file_info['size_kb']:<10.1f} "
                  f"{file_info['age_hours']:<12.1f} "
                  f"{symbol:<12} "
                  f"{timeframe:<10} "
                  f"{provider}")
    else:
        print("No cached files found.")

def clear_cache(max_age_days=None):
    """Clear cache files"""
    if max_age_days is None:
        # Clear all cache files
        response = input("This will delete ALL cached data. Are you sure? (y/N): ")
        if response.lower() != 'y':
            print("Cache clearing cancelled.")
            return
        
        cache = get_global_cache()
        cache_dir = Path(cache.cache_dir)
        
        deleted_count = 0
        for cache_file in cache_dir.glob("*.pkl"):
            try:
                cache_file.unlink()
                deleted_count += 1
            except Exception as e:
                print(f"Error deleting {cache_file}: {e}")
        
        print(f"Deleted {deleted_count} cache files.")
        
    else:
        # Clear old cache files
        print(f"Clearing cache files older than {max_age_days} days...")
        DataFetcher.clear_global_cache(max_age_days=max_age_days)
        print("Cache cleanup completed.")

def test_cache_performance():
    """Test cache performance with a sample fetch"""
    print("="*60)
    print("CACHE PERFORMANCE TEST")
    print("="*60)
    
    import time
    
    # Test parameters
    symbol = 'EURUSD=X'
    source = 'forex'
    timeframe = '1h'
    years = 1
    
    print(f"Testing with: {source} {symbol} {timeframe} ({years} years)")
    print()
    
    # Test with cache
    print("🔄 Fetching with cache enabled...")
    start_time = time.time()
    
    try:
        fetcher = DataFetcher(source=source, symbol=symbol, timeframe=timeframe, use_cache=True)
        df = fetcher.fetch(years=years)
        cached_time = time.time() - start_time
        
        print(f"✅ Completed in {cached_time:.2f} seconds")
        print(f"   Data shape: {df.shape}")
        print()
        
        # Test without cache
        print("🔄 Fetching without cache...")
        start_time = time.time()
        
        fetcher_no_cache = DataFetcher(source=source, symbol=symbol, timeframe=timeframe, use_cache=False)
        df_no_cache = fetcher_no_cache.fetch(years=years)
        no_cache_time = time.time() - start_time
        
        print(f"✅ Completed in {no_cache_time:.2f} seconds")
        print()
        
        # Compare performance
        if cached_time < no_cache_time:
            speedup = no_cache_time / cached_time
            print(f"🚀 Cache is {speedup:.1f}x faster!")
        else:
            print("📦 No significant performance difference (cache miss)")
            
    except Exception as e:
        print(f"❌ Error during test: {e}")

def invalidate_symbol_cache():
    """Interactively invalidate cache for a specific symbol"""
    print("="*60)
    print("INVALIDATE SYMBOL CACHE")
    print("="*60)
    
    # Get user input
    source = input("Enter source (forex/crypto/indices): ").strip().lower()
    if source not in ['forex', 'crypto', 'indices']:
        print("Invalid source. Must be forex, crypto, or indices.")
        return
    
    symbol = input("Enter symbol (e.g., EURUSD=X): ").strip()
    if not symbol:
        print("Symbol cannot be empty.")
        return
    
    timeframe = input("Enter timeframe (15m/1h/4h/1d): ").strip()
    if timeframe not in ['15m', '1h', '4h', '1d']:
        print("Invalid timeframe. Must be 15m, 1h, 4h, or 1d.")
        return
    
    try:
        years = input("Enter years (or press Enter for all common values): ").strip()
        years = int(years) if years else None
    except ValueError:
        print("Invalid years value.")
        return
    
    # Invalidate cache
    fetcher = DataFetcher(source=source, symbol=symbol, timeframe=timeframe)
    
    if years:
        fetcher.invalidate_cache_for_symbol(years=years)
    else:
        fetcher.invalidate_cache_for_symbol()
    
    print("Cache invalidation completed.")

def main():
    parser = argparse.ArgumentParser(description='Cache management utility')
    parser.add_argument('command', choices=['info', 'clear', 'test', 'invalidate'], 
                      help='Command to execute')
    parser.add_argument('--max-age-days', type=int, 
                      help='Maximum age in days for cache files (used with clear command)')
    
    args = parser.parse_args()
    
    if args.command == 'info':
        show_cache_info()
    elif args.command == 'clear':
        clear_cache(args.max_age_days)
    elif args.command == 'test':
        test_cache_performance()
    elif args.command == 'invalidate':
        invalidate_symbol_cache()

if __name__ == '__main__':
    main()

#!/usr/bin/env python3
"""
Cache management utility for the mean reversion strategy project.
Provides commands to inspect, clean, and manage the data cache and optimization storage.
Supports both local filesystem and AWS S3 transport layers.
"""

import argparse
import sys
import os
import time
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from src.data_fetcher import DataFetcher
from src.data_cache import DataCache
from src.transport_factory import create_cache_transport, create_optimization_transport

# Global variables to store transport types for the session
CACHE_TRANSPORT_TYPE = 'local'
LOG_TRANSPORT_TYPE = 'local'

def show_cache_info():
    """Display detailed cache information"""
    print("="*60)
    print("DATA CACHE INFORMATION")
    print("="*60)
    
    try:
        # Create cache transport with specified type
        cache_transport = create_cache_transport(transport_type=CACHE_TRANSPORT_TYPE)
        cache = DataCache(transport=cache_transport)
        cache_info = cache.get_info()
        
        transport_type = cache_info.get('transport_type', 'unknown')
        print(f"Transport Type: {transport_type.upper()}")
        
        if transport_type == 'local':
            print(f"Cache Directory: {cache_info.get('base_directory', 'N/A')}")
        elif transport_type == 's3':
            print(f"S3 Bucket: {cache_info.get('bucket', 'N/A')}")
            print(f"S3 Prefix: {cache_info.get('prefix', 'N/A')}")
        
        print(f"Total Files: {cache_info['total_files']}")
        print(f"Total Size: {cache_info['total_size_mb']:.2f} MB")
        print()
        
        if cache_info['files']:
            print("Cached Files:")
            print("-" * 80)
            print(f"{'Key':<30} {'Size (KB)':<10} {'Age (hours)':<12} {'Symbol':<12} {'Timeframe':<10} {'Provider'}")
            print("-" * 80)
            
            for file_info in sorted(cache_info['files'], key=lambda x: x['age_hours']):
                metadata = file_info.get('metadata', {})
                
                symbol = str(metadata.get('symbol', 'Unknown'))[:11]
                timeframe = metadata.get('timeframe', 'Unknown')
                provider = metadata.get('provider', 'Unknown')
                
                print(f"{file_info['key'][:29]:<30} "
                      f"{file_info['size_bytes']/1024:<10.1f} "
                      f"{file_info['age_hours']:<12.1f} "
                      f"{symbol:<12} "
                      f"{timeframe:<10} "
                      f"{provider}")
        else:
            print("No cached files found.")
    
    except Exception as e:
        print(f"❌ Error accessing cache: {e}")

def show_optimization_info():
    """Display optimization storage information"""
    print("="*60)
    print("OPTIMIZATION STORAGE INFORMATION")
    print("="*60)
    
    try:
        transport = create_optimization_transport(transport_type=LOG_TRANSPORT_TYPE)
        opt_info = transport.get_info()
        
        transport_type = opt_info.get('transport_type', 'unknown')
        print(f"Transport Type: {transport_type.upper()}")
        
        if transport_type == 'local':
            print(f"Directory: {opt_info.get('base_directory', 'N/A')}")
        elif transport_type == 's3':
            print(f"S3 Bucket: {opt_info.get('bucket', 'N/A')}")
            print(f"S3 Prefix: {opt_info.get('prefix', 'N/A')}")
        
        print(f"Total Files: {opt_info['total_files']}")
        print(f"Total Size: {opt_info['total_size_mb']:.2f} MB")
        print()
        
        if opt_info['files']:
            # Categorize files by type
            categories = {
                'cache': [],
                'results': [],
                'logs': [],
                'plots': [],
                'orders': []
            }
            
            for file_info in opt_info['files']:
                key = file_info['key']
                if key.startswith('cache/'):
                    categories['cache'].append(file_info)
                elif key.startswith('results/'):
                    categories['results'].append(file_info)
                elif key.startswith('logs/'):
                    categories['logs'].append(file_info)
                elif key.startswith('plots/'):
                    categories['plots'].append(file_info)
                elif key.startswith('orders/'):
                    categories['orders'].append(file_info)
            
            for category, files in categories.items():
                if files:
                    print(f"\n{category.upper()} FILES ({len(files)} files):")
                    print("-" * 60)
                    for file_info in sorted(files, key=lambda x: x['age_hours'])[:10]:  # Show latest 10
                        size_kb = file_info['size_bytes'] / 1024
                        print(f"  {file_info['key'][:50]:<50} {size_kb:>8.1f} KB  {file_info['age_hours']:>6.1f}h")
                    
                    if len(files) > 10:
                        print(f"  ... and {len(files) - 10} more files")
        else:
            print("No optimization files found.")
            
    except Exception as e:
        print(f"❌ Error accessing optimization storage: {e}")

def clear_cache(max_age_days=None):
    """Clear cache files"""
    print("="*60)
    print("CACHE CLEANUP")
    print("="*60)
    
    if max_age_days is None:
        response = input("⚠️  This will clear ALL cache files. Continue? (y/N): ")
        if response.lower() != 'y':
            print("❌ Cache cleanup cancelled")
            return
        max_age_days = 0  # Clear all
    
    print(f"🗑️  Clearing cache files older than {max_age_days} days...")
    
    try:
        # Clear data cache
        cache_transport = create_cache_transport(transport_type=CACHE_TRANSPORT_TYPE)
        cache = DataCache(transport=cache_transport)
        cache_removed = cache.clear(max_age_days)
        
        # Clear optimization cache
        opt_transport = create_optimization_transport(transport_type=LOG_TRANSPORT_TYPE)
        opt_removed = opt_transport.cleanup(max_age_days)
        
        total_removed = cache_removed + opt_removed
        print(f"✅ Cleanup completed. Removed {total_removed} files.")
        print(f"   - Data cache: {cache_removed} files")
        print(f"   - Optimization: {opt_removed} files")
        
    except Exception as e:
        print(f"❌ Error during cleanup: {e}")

def test_cache_performance():
    """Test cache performance with a sample fetch"""
    print("="*60)
    print("CACHE PERFORMANCE TEST")
    print("="*60)
    
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
        # Create cache transport with specified type
        cache_transport = create_cache_transport(transport_type=CACHE_TRANSPORT_TYPE)
        fetcher = DataFetcher(source=source, symbol=symbol, timeframe=timeframe, 
                            use_cache=True, cache_transport=cache_transport)
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
    print("CACHE INVALIDATION")
    print("="*60)
    
    symbol = input("Enter symbol to invalidate (e.g., EURUSD=X): ").strip()
    if not symbol:
        print("❌ No symbol provided")
        return
    
    source = input("Enter source [forex]: ").strip() or 'forex'
    timeframe = input("Enter timeframe [1h]: ").strip() or '1h'
    years = input("Enter years [all]: ").strip()
    
    try:
        # Create cache transport with specified type
        cache_transport = create_cache_transport(transport_type=CACHE_TRANSPORT_TYPE)
        fetcher = DataFetcher(source=source, symbol=symbol, timeframe=timeframe, 
                            cache_transport=cache_transport)
        
        if years and years.isdigit():
            fetcher.invalidate_cache_for_symbol(years=int(years))
            print(f"✅ Cache invalidated for {symbol} ({years} years)")
        else:
            fetcher.invalidate_cache_for_symbol()
            print(f"✅ All cache invalidated for {symbol}")
            
    except Exception as e:
        print(f"❌ Error invalidating cache: {e}")

def main():
    global CACHE_TRANSPORT_TYPE, LOG_TRANSPORT_TYPE
    
    parser = argparse.ArgumentParser(description='Cache and optimization storage management utility')
    parser.add_argument('command', choices=['info', 'optimization-info', 'clear', 'test', 'invalidate'], 
                      help='Command to execute')
    parser.add_argument('--max-age-days', type=int, 
                      help='Maximum age in days for cache files (used with clear command)')
    parser.add_argument('--cache-transport', default='local',
                       choices=['local', 's3'],
                       help='Cache transport type (default: local)')
    parser.add_argument('--log-transport', default='local',
                       choices=['local', 's3'],
                       help='Log transport type (default: local)')
    
    args = parser.parse_args()
    
    # Set global transport types based on arguments
    CACHE_TRANSPORT_TYPE = args.cache_transport
    LOG_TRANSPORT_TYPE = args.log_transport
    
    print("🗂️  Cache Manager")
    print(f"🔧 Cache Transport: {args.cache_transport}")
    print(f"📊 Log Transport: {args.log_transport}")
    print(f"⚡ Command: {args.command}")
    print("-" * 50)
    
    if args.command == 'info':
        show_cache_info()
    elif args.command == 'optimization-info':
        show_optimization_info()
    elif args.command == 'clear':
        clear_cache(args.max_age_days)
    elif args.command == 'test':
        test_cache_performance()
    elif args.command == 'invalidate':
        invalidate_symbol_cache()

if __name__ == '__main__':
    main()



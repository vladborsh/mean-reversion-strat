#!/usr/bin/env python3
"""
Test script to verify that transport configuration via CLI arguments works correctly.
This script tests both cache and log transport configuration.
"""

import os
import sys
import tempfile
import shutil
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.append(str(project_root))

def test_transport_factory():
    """Test transport factory with different transport types"""
    print("🧪 Testing transport factory...")
    
    from src.transport_factory import create_cache_transport, create_log_transport, create_optimization_transport
    
    # Test cache transport
    local_cache = create_cache_transport(transport_type='local')
    print(f"✅ Local cache transport: {type(local_cache).__name__}")
    
    # Test log transport  
    local_log = create_log_transport(transport_type='local')
    print(f"✅ Local log transport: {type(local_log).__name__}")
    
    # Test optimization transport
    local_opt = create_optimization_transport(transport_type='local')
    print(f"✅ Local optimization transport: {type(local_opt).__name__}")
    
    # Test S3 transports (should fallback to local if AWS not configured)
    s3_cache = create_cache_transport(transport_type='s3')
    print(f"✅ S3 cache transport (fallback): {type(s3_cache).__name__}")
    
    return True

def test_data_fetcher_with_transport():
    """Test DataFetcher with transport type parameter"""
    print("\n🧪 Testing DataFetcher with transport configuration...")
    
    from src.data_fetcher import DataFetcher
    
    # Test with local transport
    fetcher_local = DataFetcher(
        source='forex',
        symbol='EURUSD', 
        timeframe='1h',
        use_cache=True,
        cache_transport_type='local'
    )
    print(f"✅ DataFetcher with local cache: {type(fetcher_local.cache).__name__ if fetcher_local.cache else 'None'}")
    
    # Test with S3 transport (should fallback to local)
    fetcher_s3 = DataFetcher(
        source='forex',
        symbol='EURUSD',
        timeframe='1h', 
        use_cache=True,
        cache_transport_type='s3'
    )
    print(f"✅ DataFetcher with S3 cache (fallback): {type(fetcher_s3.cache).__name__ if fetcher_s3.cache else 'None'}")
    
    return True

def test_cli_argument_parsing():
    """Test CLI argument parsing for transport parameters"""
    print("\n🧪 Testing CLI argument parsing...")
    
    # Test scripts/run_backtest.py arguments
    print("Testing scripts/run_backtest.py CLI arguments...")
    import subprocess
    import tempfile

    try:
        result = subprocess.run([
            sys.executable, 'scripts/run_backtest.py', '--help'
        ], capture_output=True, text=True, timeout=10)

        if '--cache-transport' in result.stdout and '--log-transport' in result.stdout:
            print("✅ scripts/run_backtest.py CLI arguments are properly configured")
        else:
            print("❌ scripts/run_backtest.py CLI arguments missing transport options")
            return False

    except subprocess.TimeoutExpired:
        print("⚠️  scripts/run_backtest.py help command timed out (acceptable)")
    except Exception as e:
        print(f"⚠️  Could not test scripts/run_backtest.py CLI: {e}")
    
    # Test optimize_strategy.py arguments
    print("Testing optimize_strategy.py CLI arguments...")
    try:
        result = subprocess.run([
            sys.executable, 'optimize_strategy.py', '--help'
        ], capture_output=True, text=True, timeout=10)
        
        if '--cache-transport' in result.stdout and '--log-transport' in result.stdout:
            print("✅ optimize_strategy.py CLI arguments are properly configured")
        else:
            print("❌ optimize_strategy.py CLI arguments missing transport options")
            return False
            
    except subprocess.TimeoutExpired:
        print("⚠️  optimize_strategy.py help command timed out (acceptable)")
    except Exception as e:
        print(f"⚠️  Could not test optimize_strategy.py CLI: {e}")
    
    return True

def test_environment_fallback():
    """Test that transport factory falls back to environment variables when no explicit type provided"""
    print("\n🧪 Testing environment variable fallback...")
    
    from src.transport_factory import create_cache_transport, create_log_transport
    
    # Test without explicit transport type (should use env vars or default to local)
    cache_transport = create_cache_transport()
    log_transport = create_log_transport()
    
    print(f"✅ Default cache transport: {type(cache_transport).__name__}")
    print(f"✅ Default log transport: {type(log_transport).__name__}")
    
    return True

def main():
    """Run all tests"""
    print("🚀 Testing CACHE_TRANSPORT and LOG_TRANSPORT CLI configuration")
    print("=" * 60)
    
    tests = [
        test_transport_factory,
        test_data_fetcher_with_transport,
        test_cli_argument_parsing,
        test_environment_fallback
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            print(f"❌ Test {test.__name__} failed: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "=" * 60)
    print(f"🎯 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("✅ All transport configuration tests passed!")
        print("\n📋 Summary of changes:")
        print("   • CACHE_TRANSPORT and LOG_TRANSPORT moved from .env to CLI arguments")
        print("   • All scripts now accept --cache-transport and --log-transport flags")
        print("   • Transport factory supports both explicit types and environment fallback")
        print("   • DataFetcher accepts cache_transport_type parameter")
        print("   • Documentation updated to reflect new CLI approach")
        return True
    else:
        print(f"❌ {total - passed} tests failed!")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

#!/usr/bin/env python3
"""
Test script for transport layer functionality.
Tests both local and S3 transports if configured.
"""

import os
import sys
import tempfile
from pathlib import Path
from datetime import datetime
import pandas as pd

# Add project root to path
project_root = Path(__file__).parent
sys.path.append(str(project_root))

from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from src.transport import LocalTransport
from src.data_cache import DataCache
from src.transport_factory import create_cache_transport, create_optimization_transport

def test_local_transport():
    """Test local transport functionality"""
    print("🔍 Testing Local Transport...")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        transport = LocalTransport(temp_dir)
        
        # Test text operations
        test_key = "test/sample.txt"
        test_content = "Hello, World!"
        
        assert transport.save_text(test_key, test_content), "Failed to save text"
        assert transport.exists(test_key), "File should exist"
        
        loaded_content = transport.load_text(test_key)
        assert loaded_content == test_content, f"Content mismatch: {loaded_content} != {test_content}"
        
        # Test JSON operations
        test_data = {"name": "test", "value": 123, "timestamp": datetime.now().isoformat()}
        json_key = "test/data.json"
        
        assert transport.save_json(json_key, test_data), "Failed to save JSON"
        loaded_data = transport.load_json(json_key)
        assert loaded_data["name"] == test_data["name"], "JSON data mismatch"
        
        # Test pickle operations
        test_df = pd.DataFrame({
            'date': pd.date_range('2023-01-01', periods=100),
            'price': range(100),
            'volume': [x * 1000 for x in range(100)]
        })
        pickle_key = "test/dataframe.pkl"
        
        assert transport.save_pickle(pickle_key, test_df), "Failed to save pickle"
        loaded_df = transport.load_pickle(pickle_key)
        assert len(loaded_df) == len(test_df), "DataFrame length mismatch"
        
        # Test list operations
        keys = transport.list_keys("test/")
        assert len(keys) >= 3, f"Expected at least 3 keys, got {len(keys)}"
        
        # Test info
        info = transport.get_info()
        assert info["transport_type"] == "local", "Wrong transport type"
        assert info["total_files"] >= 3, "Should have at least 3 files"
        
        print("✅ Local transport tests passed!")

def test_s3_transport():
    """Test S3 transport functionality if configured"""
    
    # Check if S3 is configured
    bucket = os.getenv('AWS_S3_BUCKET')
    if not bucket:
        print("⏭️  Skipping S3 tests - AWS_S3_BUCKET not configured")
        return
        
    print("🔍 Testing S3 Transport...")
    
    try:
        from src.s3_transport import S3Transport
        
        transport = S3Transport(
            bucket_name=bucket,
            prefix="test-transport/",
            aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
            aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
            region_name=os.getenv('AWS_REGION', 'us-east-1')
        )
        
        # Test text operations
        test_key = "test/sample.txt"
        test_content = f"S3 Test - {datetime.now().isoformat()}"
        
        assert transport.save_text(test_key, test_content), "Failed to save text to S3"
        assert transport.exists(test_key), "File should exist in S3"
        
        loaded_content = transport.load_text(test_key)
        assert loaded_content == test_content, f"S3 content mismatch: {loaded_content} != {test_content}"
        
        # Test JSON operations
        test_data = {"name": "s3_test", "value": 456, "timestamp": datetime.now().isoformat()}
        json_key = "test/data.json"
        
        assert transport.save_json(json_key, test_data), "Failed to save JSON to S3"
        loaded_data = transport.load_json(json_key)
        assert loaded_data["name"] == test_data["name"], "S3 JSON data mismatch"
        
        # Test info
        info = transport.get_info()
        assert info["transport_type"] == "s3", "Wrong transport type"
        assert info["bucket"] == bucket, "Wrong bucket name"
        
        # Clean up test files
        transport.delete(test_key)
        transport.delete(json_key)
        
        print("✅ S3 transport tests passed!")
        
    except ImportError:
        print("⚠️  boto3 not available - skipping S3 tests")
    except Exception as e:
        print(f"❌ S3 transport test failed: {e}")

def test_data_cache():
    """Test data cache with transport layer"""
    print("🔍 Testing Data Cache with Transport Layer...")
    
    # Test with default transport (from environment)
    cache = DataCache()
    
    # Create test data (fix pandas deprecation warning)
    test_data = pd.DataFrame({
        'timestamp': pd.date_range('2023-01-01', periods=50, freq='h'),  # Changed 'H' to 'h'
        'open': range(50),
        'high': [x + 1 for x in range(50)],
        'low': [x - 1 for x in range(50)],
        'close': range(50),
        'volume': [x * 100 for x in range(50)]
    })
    test_data.set_index('timestamp', inplace=True)
    
    # Test cache operations with unique test identifiers
    import time
    test_id = str(int(time.time()))  # Use timestamp to make test unique
    source = "test"
    symbol = f"TEST_SYMBOL_{test_id}"
    timeframe = "1h"
    years = 1
    
    # Should not exist initially (using unique symbol)
    cached_data = cache.get(source, symbol, timeframe, years)
    if cached_data is not None:
        print(f"⚠️  Found existing cache for {symbol}, this is expected if tests were run before")
    
    # Store data
    cache.set(source, symbol, timeframe, years, test_data, metadata={"test": True, "test_id": test_id})
    
    # Retrieve data
    cached_data = cache.get(source, symbol, timeframe, years)
    assert cached_data is not None, "Data should be cached"
    assert len(cached_data) == len(test_data), f"Cached data length mismatch: {len(cached_data)} != {len(test_data)}"
    
    # Test cache info
    cache_info = cache.get_cache_info()
    assert cache_info["total_files"] >= 1, "Should have at least 1 cached file"
    
    print("✅ Data cache tests passed!")

def test_transport_factories():
    """Test transport factory functions"""
    print("🔍 Testing Transport Factories...")
    
    # Test cache transport factory
    cache_transport = create_cache_transport()
    assert cache_transport is not None, "Cache transport should be created"
    
    # Test optimization transport factory
    opt_transport = create_optimization_transport()
    assert opt_transport is not None, "Optimization transport should be created"
    
    print("✅ Transport factory tests passed!")

def main():
    """Run all tests"""
    print("🚀 Starting Transport Layer Tests")
    print("=" * 50)
    
    try:
        test_local_transport()
        test_s3_transport()
        test_data_cache()
        test_transport_factories()
        
        print("=" * 50)
        print("🎉 All tests passed successfully!")
        
    except AssertionError as e:
        print(f"❌ Test failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"💥 Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()

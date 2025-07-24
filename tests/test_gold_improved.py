#!/usr/bin/env python3
"""
Test the improved Capital.com fetcher with historical gold data
"""

import os
import sys
sys.path.append('/Users/Vladyslav_Borsh/Documents/dev/mean-reversion-strat')

from src.capital_com_fetcher import create_capital_com_fetcher
from datetime import datetime, timedelta

def test_gold_historical_data():
    """Test fetching historical GOLD data with improved error handling"""
    
    # Load environment variables
    from dotenv import load_dotenv
    load_dotenv()
    
    fetcher = create_capital_com_fetcher()
    if not fetcher:
        print("❌ Could not create Capital.com fetcher. Check environment variables.")
        return
    
    try:
        print("🧪 Testing GOLD historical data fetch with improved error handling...")
        
        # Test the original problematic date range (March 2024)
        with fetcher:
            print("\n📊 Test 1: Original problematic date range (March 2024, 5m data)")
            data = fetcher.fetch_historical_data('GOLD', 'commodities', '5m', 1.5)  # ~1.3 years back
            
            if data is not None and not data.empty:
                print(f"✅ Success: Retrieved {len(data)} records")
                print(f"   Date range: {data.index[0]} to {data.index[-1]}")
                print(f"   Columns: {list(data.columns)}")
                print(f"   Sample data:\n{data.head(3)}")
            else:
                print("❌ No data returned")
        
        print("\n" + "="*60)
        
    except Exception as e:
        print(f"❌ Error during testing: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_gold_historical_data()

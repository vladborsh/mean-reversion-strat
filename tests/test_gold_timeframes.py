#!/usr/bin/env python3
"""
Test script to check available timeframes for GOLD symbol on Capital.com
"""

import os
import sys
sys.path.append('/Users/Vladyslav_Borsh/Documents/dev/mean-reversion-strat')

from src.capital_com_fetcher import create_capital_com_fetcher
from datetime import datetime, timedelta

def test_gold_timeframes():
    """Test different timeframes for GOLD symbol"""
    
    # Load environment variables
    from dotenv import load_dotenv
    load_dotenv()
    
    fetcher = create_capital_com_fetcher()
    if not fetcher:
        print("❌ Could not create Capital.com fetcher. Check environment variables.")
        return
    
    try:
        with fetcher:
            print("🔍 Testing GOLD symbol with different timeframes...")
            
            # Get detailed market info first
            details = fetcher.get_market_details('GOLD')
            if details:
                print(f"\n📊 GOLD Market Details:")
                instrument = details.get('instrument', {})
                snapshot = details.get('snapshot', {})
                
                print(f"   Name: {instrument.get('name', 'N/A')}")
                print(f"   Type: {instrument.get('type', 'N/A')}")
                print(f"   Status: {snapshot.get('marketStatus', 'N/A')}")
                print(f"   Current Price: {snapshot.get('bid', 'N/A')}")
                
                # Check dealing rules
                dealing_rules = details.get('dealingRules', {})
                if dealing_rules:
                    print(f"   Min Deal Size: {dealing_rules.get('minDealSize', {}).get('value', 'N/A')}")
                    min_step = dealing_rules.get('minStepDistance', {})
                    if min_step:
                        print(f"   Min Step: {min_step.get('value', 'N/A')} {min_step.get('unit', '')}")
            
            # Test different timeframes
            timeframes = ['5m', '15m', '1h', '4h', '1d']
            
            # Use a small date range for testing (last few days)
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=3)
            
            print(f"\n🧪 Testing timeframes with date range: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
            
            for timeframe in timeframes:
                print(f"\n   Testing {timeframe}:")
                try:
                    # Map timeframe to Capital.com format
                    resolution = fetcher.timeframe_mapping.get(timeframe, 'HOUR')
                    print(f"   Resolution: {resolution}")
                    
                    # Format dates for API
                    from_date = start_date.strftime('%Y-%m-%dT%H:%M:%S')
                    to_date = end_date.strftime('%Y-%m-%dT%H:%M:%S')
                    
                    # Make direct API call
                    headers = fetcher._get_auth_headers()
                    params = {
                        'resolution': resolution,
                        'from': from_date,
                        'to': to_date,
                        'max': 100  # Small limit for testing
                    }
                    
                    response = fetcher._make_request('GET', f'/api/v1/prices/GOLD', 
                                                   headers=headers, params=params)
                    
                    data = response.json()
                    prices = data.get('prices', [])
                    
                    if prices:
                        print(f"   ✅ {timeframe} - Got {len(prices)} price records")
                        # Show first record
                        if prices:
                            first_record = prices[0]
                            print(f"      First record: {first_record}")
                    else:
                        print(f"   ⚠️  {timeframe} - No price data returned")
                        print(f"      Response: {data}")
                        
                except Exception as e:
                    print(f"   ❌ {timeframe} - Error: {e}")
                    if hasattr(e, 'response') and e.response is not None:
                        print(f"      Status: {e.response.status_code}")
                        print(f"      Response: {e.response.text}")
            
    except Exception as e:
        print(f"❌ Error during timeframe testing: {e}")

if __name__ == "__main__":
    test_gold_timeframes()

#!/usr/bin/env python3
"""
Test script to find the correct Capital.com symbol for gold
"""

import os
import sys
sys.path.append('/Users/Vladyslav_Borsh/Documents/dev/mean-reversion-strat')

from src.capital_com_fetcher import create_capital_com_fetcher

def test_gold_symbol():
    """Test different gold symbol mappings to find the correct one"""
    
    # Load environment variables
    from dotenv import load_dotenv
    load_dotenv()
    
    fetcher = create_capital_com_fetcher()
    if not fetcher:
        print("❌ Could not create Capital.com fetcher. Check environment variables.")
        return
    
    try:
        with fetcher:
            print("🔍 Searching for gold-related markets...")
            
            # Search for gold markets
            gold_markets = fetcher.search_markets('gold')
            if gold_markets:
                print(f"\n📋 Found {len(gold_markets)} gold-related markets:")
                for i, market in enumerate(gold_markets[:10]):  # Show first 10
                    epic = market.get('epic', 'N/A')
                    name = market.get('marketName', 'N/A')
                    status = market.get('marketStatus', 'N/A')
                    print(f"   {i+1}. Epic: {epic:<15} Name: {name:<30} Status: {status}")
                    
                    # Show additional details if available
                    if 'dealingRules' in market:
                        rules = market['dealingRules']
                        min_step = rules.get('minStepDistance', {}).get('value', 'N/A')
                        if min_step != 'N/A':
                            print(f"      Min Step: {min_step}")
            
            print(f"\n🔍 Searching for XAU (gold) markets...")
            xau_markets = fetcher.search_markets('XAU')
            if xau_markets:
                print(f"📋 Found {len(xau_markets)} XAU-related markets:")
                for market in xau_markets[:5]:
                    epic = market.get('epic', 'N/A')
                    name = market.get('marketName', 'N/A')
                    print(f"   Epic: {epic:<15} Name: {name}")
            
            # Test specific gold symbols
            test_symbols = ['GOLD', 'XAUUSD', 'XAU_USD', 'GOLD_USD']
            print(f"\n🧪 Testing specific gold symbols:")
            
            for symbol in test_symbols:
                print(f"\n   Testing symbol: {symbol}")
                try:
                    details = fetcher.get_market_details(symbol)
                    if details:
                        name = details.get('instrument', {}).get('name', 'N/A')
                        status = details.get('snapshot', {}).get('marketStatus', 'N/A')
                        print(f"   ✅ {symbol} exists - Name: {name}, Status: {status}")
                        
                        # Check if it supports 5-minute data
                        if 'dealingRules' in details:
                            print(f"   📊 Market supports trading")
                        
                    else:
                        print(f"   ❌ {symbol} not found")
                except Exception as e:
                    print(f"   ❌ {symbol} error: {e}")
            
    except Exception as e:
        print(f"❌ Error during symbol search: {e}")

if __name__ == "__main__":
    test_gold_symbol()

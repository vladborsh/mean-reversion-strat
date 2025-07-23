#!/usr/bin/env python3
"""
Script to test Bitcoin fetching from Capital.com API and find the correct epic symbol.
"""

import os
import sys
from pathlib import Path

# Load environment variables from .env file if it exists
try:
    from dotenv import load_dotenv
    load_dotenv()
    print("✅ Loaded environment variables from .env file")
except ImportError:
    print("⚠️  python-dotenv not installed, trying to load .env manually")
    # Try to load .env file manually
    env_file = Path(__file__).parent / '.env'
    if env_file.exists():
        with open(env_file) as f:
            for line in f:
                if line.strip() and not line.startswith('#'):
                    key, value = line.strip().split('=', 1)
                    os.environ[key] = value.strip('"').strip("'")
        print("✅ Manually loaded environment variables from .env file")

# Add the project root to Python path so we can import from src
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Now we can import from src package
from src.capital_com_fetcher import create_capital_com_fetcher

def test_bitcoin_search():
    """Test searching for Bitcoin markets on Capital.com"""
    
    print("🔍 Testing Bitcoin market search on Capital.com")
    print("=" * 60)
    
    # Create fetcher
    fetcher = create_capital_com_fetcher()
    
    if not fetcher:
        print("❌ Could not create Capital.com fetcher")
        print("   Make sure you have set the following environment variables:")
        print("   - CAPITAL_COM_API_KEY")
        print("   - CAPITAL_COM_PASSWORD") 
        print("   - CAPITAL_COM_IDENTIFIER")
        return
    
    try:
        # Create session
        if not fetcher.create_session():
            print("❌ Failed to create Capital.com session")
            return
            
        print("✅ Capital.com session created successfully")
        print()
        
        # Search terms to try
        search_terms = ['bitcoin', 'BTC', 'BITCOIN', 'crypto', 'cryptocurrency']
        
        for term in search_terms:
            print(f"🔍 Searching for '{term}'...")
            markets = fetcher.search_markets(term)
            
            if markets:
                print(f"   Found {len(markets)} markets:")
                
                # Show relevant cryptocurrency markets
                crypto_markets = []
                for market in markets[:10]:  # Limit to first 10 results
                    epic = market.get('epic', 'N/A')
                    name = market.get('instrumentName', 'N/A')
                    instrument_type = market.get('instrumentType', 'N/A')
                    
                    # Focus on cryptocurrency markets or Bitcoin-related
                    if ('BITCOIN' in epic.upper() or 
                        'BTC' in epic.upper() or 
                        'BITCOIN' in name.upper() or 
                        'BTC' in name.upper() or
                        instrument_type == 'CRYPTOCURRENCIES'):
                        crypto_markets.append((epic, name, instrument_type))
                        
                if crypto_markets:
                    for epic, name, inst_type in crypto_markets:
                        print(f"     Epic: {epic:<15} | Name: {name:<25} | Type: {inst_type}")
                else:
                    print("     No cryptocurrency markets found in results")
            else:
                print("     No markets found")
            
            print()
        
        # Test specific Bitcoin epic variations
        print("🧪 Testing specific Bitcoin epic variations...")
        test_epics = [
            'BITCOIN',
            'BITCOIN_USD',
            'BTCUSD', 
            'BTC_USD',
            'BTCUSD_CFD',
            'BITCOIN=X',
            'BTC=X'
        ]
        
        for epic in test_epics:
            print(f"   Testing epic: {epic}")
            market_details = fetcher.get_market_details(epic)
            if market_details:
                name = market_details.get('instrument', {}).get('name', 'N/A')
                symbol = market_details.get('instrument', {}).get('symbol', 'N/A')
                inst_type = market_details.get('instrument', {}).get('type', 'N/A')
                print(f"     ✅ Found: {name} ({symbol}) - Type: {inst_type}")
            else:
                print(f"     ❌ Not found")
        
        print()
        
    except Exception as e:
        print(f"❌ Error during testing: {e}")
        
    finally:
        fetcher.close_session()
        print("🔒 Session closed")

def test_bitcoin_data_fetch():
    """Test fetching actual Bitcoin price data"""
    
    print("\n📊 Testing Bitcoin data fetching...")
    print("=" * 60)
    
    fetcher = create_capital_com_fetcher()
    if not fetcher:
        print("❌ Could not create fetcher")
        return
        
    # Common Bitcoin epic formats to try
    bitcoin_epics_to_test = [
        'BTCUSD',    # This is the correct one we found
        'BITCOIN',
        'BTC_USD',
        'BITCOIN_USD'
    ]
    
    for epic in bitcoin_epics_to_test:
        print(f"🔄 Trying to fetch data for epic: {epic}")
        
        try:
            # Try to fetch 1 day of 1h data - pass the epic directly to avoid mapping issues
            if epic == 'BTCUSD':
                # Use the correct asset type and pass epic directly
                df = fetcher.fetch_historical_data(
                    symbol='BTCUSD', 
                    asset_type='cryptocurrencies',  # Use full asset type name
                    timeframe='1h',
                    years=0.003  # About 1 day
                )
            else:
                df = fetcher.fetch_historical_data(
                    symbol=epic, 
                    asset_type='crypto',  # Try crypto asset type
                    timeframe='1h',
                    years=0.003  # About 1 day
                )
            
            if df is not None and not df.empty:
                print(f"   ✅ Success! Retrieved {len(df)} rows")
                print(f"   📅 Date range: {df.index[0]} to {df.index[-1]}")
                print(f"   💰 Latest close: {df['close'].iloc[-1]:.2f}")
                break
            else:
                print(f"   ❌ No data returned")
                
        except Exception as e:
            print(f"   ❌ Error: {e}")
    
    else:
        print("\n⚠️  Could not fetch Bitcoin data with any of the tested epics")
        print("   This suggests Bitcoin might not be available or uses a different epic format")

def main():
    """Main function"""
    print("🚀 Capital.com Bitcoin Testing Script")
    print("=" * 60)
    
    # Check if environment variables are set
    required_vars = ['CAPITAL_COM_API_KEY', 'CAPITAL_COM_PASSWORD', 'CAPITAL_COM_IDENTIFIER']
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        print("❌ Missing required environment variables:")
        for var in missing_vars:
            print(f"   - {var}")
        print("\nPlease set these variables and try again.")
        return
    
    print("✅ All required environment variables are set")
    print()
    
    # Run tests
    test_bitcoin_search()
    test_bitcoin_data_fetch()
    
    print("\n" + "=" * 60)
    print("🏁 Testing completed!")

if __name__ == "__main__":
    main()

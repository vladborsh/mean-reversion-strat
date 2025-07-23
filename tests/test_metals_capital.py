#!/usr/bin/env python3
"""
Script to test Gold and Silver fetching from Capital.com API and find the correct epic symbols.
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

def test_metals_search():
    """Test searching for precious metals markets on Capital.com"""
    
    print("🔍 Testing precious metals market search on Capital.com")
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
        search_terms = ['gold', 'silver', 'precious metals', 'commodities', 'metals']
        
        for term in search_terms:
            print(f"🔍 Searching for '{term}'...")
            markets = fetcher.search_markets(term)
            
            if markets:
                print(f"   Found {len(markets)} markets:")
                
                # Show relevant precious metals markets
                metals_markets = []
                for market in markets[:15]:  # Limit to first 15 results
                    epic = market.get('epic', 'N/A')
                    name = market.get('instrumentName', 'N/A')
                    instrument_type = market.get('instrumentType', 'N/A')
                    
                    # Focus on commodities markets or precious metals
                    if ('GOLD' in epic.upper() or 
                        'SILVER' in epic.upper() or 
                        'XAU' in epic.upper() or  # Gold symbol
                        'XAG' in epic.upper() or  # Silver symbol
                        'GOLD' in name.upper() or 
                        'SILVER' in name.upper() or
                        instrument_type == 'COMMODITIES'):
                        metals_markets.append((epic, name, instrument_type))
                        
                if metals_markets:
                    for epic, name, inst_type in metals_markets:
                        print(f"     Epic: {epic:<15} | Name: {name:<25} | Type: {inst_type}")
                else:
                    print("     No precious metals markets found in results")
            else:
                print("     No markets found")
            
            print()
        
        # Test specific precious metals epic variations
        print("🧪 Testing specific precious metals epic variations...")
        metals_epics = [
            # Gold variations
            'GOLD',
            'GOLD_USD',
            'XAUUSD',
            'XAU_USD',
            'GOLD=X',
            'GC=F',
            'XAUUSD_CFD',
            # Silver variations
            'SILVER',
            'SILVER_USD',
            'XAGUSD',
            'XAG_USD',
            'SILVER=X',
            'SI=F',
            'XAGUSD_CFD'
        ]
        
        for epic in metals_epics:
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

def test_metals_data_fetch():
    """Test fetching actual precious metals price data"""
    
    print("\n📊 Testing precious metals data fetching...")
    print("=" * 60)
    
    fetcher = create_capital_com_fetcher()
    if not fetcher:
        print("❌ Could not create fetcher")
        return
        
    # Common precious metals epic formats to test (based on search results)
    metals_epics_to_test = [
        ('GOLD', 'Gold'),
        ('XAUUSD', 'Gold (XAU/USD)'),
        ('SILVER', 'Silver'),
        ('XAGUSD', 'Silver (XAG/USD)')
    ]
    
    successful_fetches = []
    
    for epic, description in metals_epics_to_test:
        print(f"🔄 Trying to fetch data for {description}: {epic}")
        
        try:
            # Try to fetch 1 day of 1h data
            df = fetcher.fetch_historical_data(
                symbol=epic, 
                asset_type='commodities',  # Try commodities asset type
                timeframe='1h',
                years=0.003  # About 1 day
            )
            
            if df is not None and not df.empty:
                print(f"   ✅ Success! Retrieved {len(df)} rows")
                print(f"   📅 Date range: {df.index[0]} to {df.index[-1]}")
                print(f"   💰 Latest close: {df['close'].iloc[-1]:.2f}")
                successful_fetches.append((epic, description))
            else:
                print(f"   ❌ No data returned")
                
        except Exception as e:
            print(f"   ❌ Error: {e}")
    
    if successful_fetches:
        print(f"\n✅ Successfully fetched data for {len(successful_fetches)} precious metals:")
        for epic, description in successful_fetches:
            print(f"   - {description}: {epic}")
    else:
        print("\n⚠️  Could not fetch precious metals data with any of the tested epics")

def main():
    """Main function"""
    print("🚀 Capital.com Precious Metals Testing Script")
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
    test_metals_search()
    test_metals_data_fetch()
    
    print("\n" + "=" * 60)
    print("🏁 Testing completed!")

if __name__ == "__main__":
    main()

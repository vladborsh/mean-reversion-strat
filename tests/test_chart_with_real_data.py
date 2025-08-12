#!/usr/bin/env python3
"""
Test script for chart generation with real Capital.com data
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from src.bot.signal_chart_generator import SignalChartGenerator
from src.capital_com_fetcher import create_capital_com_fetcher
from src.data_fetcher import DataFetcher


def fetch_real_data(symbol='EURUSD', timeframe='5m'):
    """Fetch real data from Capital.com"""
    print(f"Fetching real data for {symbol} ({timeframe})...")
    
    try:
        # Try Capital.com first
        fetcher = create_capital_com_fetcher()
        if fetcher:
            print("Using Capital.com API...")
            with fetcher:
                # Fetch last 999 candles (about 3.5 days for 5m)
                data = fetcher.fetch_data(
                    symbol='EURUSD',  # Capital.com symbol format
                    timeframe=timeframe,
                    limit=999
                )
                
                if data is not None and not data.empty:
                    # Remove the last (incomplete) candle
                    if len(data) > 1:
                        data = data.iloc[:-1]
                    print(f"✅ Fetched {len(data)} candles from Capital.com")
                    print(f"   Date range: {data.index[0]} to {data.index[-1]}")
                    print(f"   Current price: {data['close'].iloc[-1]:.5f}")
                    return data
                else:
                    print("❌ No data returned from Capital.com")
        else:
            print("Capital.com credentials not available")
    except Exception as e:
        print(f"Error with Capital.com: {e}")
    
    # Fallback to DataFetcher (uses yfinance/forex)
    print("Falling back to alternative data source...")
    try:
        fetcher = DataFetcher(
            source='forex',
            symbol='EURUSDX',  # Forex symbol format
            timeframe=timeframe,
            use_cache=False
        )
        
        # Fetch about 3.5 days of 5m data
        data = fetcher.fetch(years=0.01)
        
        if data is not None and not data.empty:
            # Limit to last 999 candles
            if len(data) > 999:
                data = data.tail(999)
            
            # Remove the last (incomplete) candle
            if len(data) > 1:
                data = data.iloc[:-1]
            
            print(f"✅ Fetched {len(data)} candles from alternative source")
            print(f"   Date range: {data.index[0]} to {data.index[-1]}")
            print(f"   Current price: {data['close'].iloc[-1]:.5f}")
            return data
        else:
            print("❌ No data returned from alternative source")
            return None
            
    except Exception as e:
        print(f"Error fetching data: {e}")
        return None


def simulate_signal(data):
    """Generate a simulated signal based on current price"""
    current_price = data['close'].iloc[-1]
    
    # Calculate ATR for realistic stop loss
    high = data['high'].tail(14)
    low = data['low'].tail(14)
    close = data['close'].tail(14)
    
    # Simple ATR calculation
    tr1 = high - low
    tr2 = abs(high - close.shift())
    tr3 = abs(low - close.shift())
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = tr.mean()
    
    # Determine signal direction based on recent price movement
    price_change = (current_price - data['close'].iloc[-20]) / data['close'].iloc[-20]
    
    if price_change < -0.0010:  # Price dropped, potential long signal
        signal_type = 'long'
        direction = 'BUY'
        stop_loss = current_price - (atr * 1.5)  # 1.5 ATR stop loss
        take_profit = current_price + (atr * 3.0)  # 3 ATR take profit (2:1 RR)
    else:  # Price rose, potential short signal
        signal_type = 'short'
        direction = 'SELL'
        stop_loss = current_price + (atr * 1.5)
        take_profit = current_price - (atr * 3.0)
    
    # Calculate position size (example: risk $100)
    risk_amount = 100.0
    risk_per_unit = abs(current_price - stop_loss)
    position_size = risk_amount / risk_per_unit if risk_per_unit > 0 else 1000
    
    signal_data = {
        'signal_type': signal_type,
        'direction': direction,
        'entry_price': current_price,
        'stop_loss': stop_loss,
        'take_profit': take_profit,
        'position_size': round(position_size, 2),
        'risk_amount': risk_amount,
        'atr_value': atr
    }
    
    return signal_data


def test_chart_generation_with_real_data():
    """Test chart generation with real Capital.com data"""
    print("=" * 60)
    print("Chart Generation Test with Real Data")
    print("=" * 60)
    
    # Fetch real data
    data = fetch_real_data(symbol='EURUSD', timeframe='5m')
    
    if data is None:
        print("❌ Failed to fetch data. Cannot proceed with test.")
        return False
    
    # Initialize chart generator
    print("\nInitializing chart generator...")
    chart_generator = SignalChartGenerator()
    
    # Simulate a trading signal
    print("\nSimulating trading signal...")
    signal_data = simulate_signal(data)
    
    print(f"Signal details:")
    print(f"  Type: {signal_data['signal_type'].upper()}")
    print(f"  Direction: {signal_data['direction']}")
    print(f"  Entry: {signal_data['entry_price']:.5f}")
    print(f"  Stop Loss: {signal_data['stop_loss']:.5f}")
    print(f"  Take Profit: {signal_data['take_profit']:.5f}")
    print(f"  Position Size: {signal_data['position_size']:.2f}")
    print(f"  Risk Amount: ${signal_data['risk_amount']:.2f}")
    print(f"  ATR: {signal_data['atr_value']:.5f}")
    
    # Define strategy parameters (typical mean reversion settings)
    strategy_params = {
        'bb_window': 20,
        'bb_std': 2,
        'vwap_window': 20,
        'vwap_std': 2
    }
    
    # Generate chart
    print("\nGenerating chart with indicators...")
    chart_buffer = chart_generator.generate_signal_chart(
        data=data,
        signal_data=signal_data,
        strategy_params=strategy_params,
        symbol='EURUSD'
    )
    
    if chart_buffer:
        print(f"✅ Chart generated successfully! Size: {len(chart_buffer):,} bytes")
        
        # Save to file for visual inspection
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = f'eurusd_chart_{timestamp}.png'
        with open(output_path, 'wb') as f:
            f.write(chart_buffer)
        print(f"📊 Chart saved to: {output_path}")
        
        
        return True
    else:
        print("❌ Chart generation failed!")
        return False


def test_chart_with_different_signals():
    """Test chart generation with both long and short signals"""
    print("\n" + "=" * 60)
    print("Testing Multiple Signal Types")
    print("=" * 60)
    
    # Fetch real data
    data = fetch_real_data(symbol='EURUSD', timeframe='5m')
    
    if data is None:
        print("❌ Failed to fetch data.")
        return False
    
    chart_generator = SignalChartGenerator()
    current_price = data['close'].iloc[-1]
    
    # Test both signal types
    signal_types = [
        {
            'signal_type': 'long',
            'direction': 'BUY',
            'entry_price': current_price,
            'stop_loss': current_price - 0.0010,
            'take_profit': current_price + 0.0020,
            'position_size': 10000,
            'risk_amount': 100
        },
        {
            'signal_type': 'short',
            'direction': 'SELL',
            'entry_price': current_price,
            'stop_loss': current_price + 0.0010,
            'take_profit': current_price - 0.0020,
            'position_size': 10000,
            'risk_amount': 100
        }
    ]
    
    strategy_params = {
        'bb_window': 20,
        'bb_std': 2,
        'vwap_window': 20,
        'vwap_std': 2
    }
    
    success = True
    for signal_data in signal_types:
        print(f"\nGenerating {signal_data['signal_type'].upper()} signal chart...")
        
        chart_buffer = chart_generator.generate_signal_chart(
            data=data,
            signal_data=signal_data,
            strategy_params=strategy_params,
            symbol='EURUSD'
        )
        
        if chart_buffer:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = f"eurusd_{signal_data['signal_type']}_{timestamp}.png"
            with open(output_path, 'wb') as f:
                f.write(chart_buffer)
            print(f"✅ {signal_data['signal_type'].upper()} chart saved to: {output_path}")
        else:
            print(f"❌ Failed to generate {signal_data['signal_type']} chart")
            success = False
    
    return success


if __name__ == "__main__":
    print("\n" + "🚀 " * 20)
    print("REAL-TIME CHART GENERATION TEST")
    print("🚀 " * 20 + "\n")
    
    # Check for Capital.com credentials
    api_key = os.getenv('CAPITAL_COM_API_KEY')
    if api_key:
        print("✅ Capital.com credentials found")
    else:
        print("⚠️  Capital.com credentials not found - will use fallback data source")
    
    # Test with real data
    test1_success = test_chart_generation_with_real_data()
    
    # Test multiple signal types
    test2_success = test_chart_with_different_signals()
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    print(f"Real data chart generation: {'✅ PASSED' if test1_success else '❌ FAILED'}")
    print(f"Multiple signal types: {'✅ PASSED' if test2_success else '❌ FAILED'}")
    
    if test1_success and test2_success:
        print("\n🎉 All tests passed successfully!")
        print("Charts have been saved to the current directory for inspection.")
        sys.exit(0)
    else:
        print("\n⚠️  Some tests failed. Please check the output above.")
        sys.exit(1)
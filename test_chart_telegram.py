#!/usr/bin/env python3
"""
Test script for chart generation and Telegram sending with dark theme

This script:
1. Generates realistic forex OHLCV data
2. Creates mock signal data for both LONG and SHORT signals
3. Tests different strategy types (mean_reversion, vwap, session_sweep)
4. Generates charts with dark color palette
5. Saves charts locally
6. Optionally sends to Telegram for visual verification

Usage:
    python test_chart_telegram.py                    # Generate and save charts locally
    SEND_TO_TELEGRAM=true python test_chart_telegram.py  # Also send to Telegram
"""

import os
import sys
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
import asyncio

# Add src to path
sys.path.append(str(Path(__file__).parent / 'src'))

from bot.signal_chart_generator import SignalChartGenerator
from chart_config import DEFAULT_CHART_CONFIG

# Configuration
SEND_TO_TELEGRAM = os.getenv('SEND_TO_TELEGRAM', 'false').lower() == 'true'
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TEST_CHAT_ID = os.getenv('TEST_CHAT_ID')


def generate_sample_forex_data(symbol='EURUSD', num_candles=200, timeframe='5m', base_price=None):
    """
    Generate realistic-looking forex OHLCV data
    
    Args:
        symbol: Trading symbol
        num_candles: Number of candles to generate
        timeframe: Timeframe (5m, 15m, 1h)
        base_price: Starting price (auto-set based on symbol if None)
        
    Returns:
        DataFrame with OHLCV data
    """
    # Set timeframe frequency
    if timeframe == '5m':
        freq = '5T'
    elif timeframe == '15m':
        freq = '15T'
    elif timeframe == '1h':
        freq = '1H'
    else:
        freq = '5T'
    
    # Set realistic base prices for different symbols
    if base_price is None:
        price_map = {
            'EURUSD': 1.0850,
            'GBPUSD': 1.2650,
            'GOLD': 2050.00,
            'DE40': 17500.00,
            'BTC': 42000.00
        }
        base_price = price_map.get(symbol, 1.0850)
    
    # Generate dates
    end_time = datetime.now()
    dates = pd.date_range(end=end_time, periods=num_candles, freq=freq)
    
    # Generate price movement using random walk with slight trend and volatility clustering
    volatility = 0.0003 if 'USD' in symbol else (0.01 if symbol == 'GOLD' else (50 if symbol == 'BTC' else 15))
    returns = np.random.normal(0, volatility, num_candles)
    
    # Add some volatility clustering
    volatility_factor = np.abs(np.random.normal(1, 0.2, num_candles))
    returns = returns * volatility_factor
    
    # Add slight trend
    trend = np.linspace(-0.0001, 0.0001, num_candles)
    returns = returns + trend
    
    # Generate close prices
    close_prices = base_price * (1 + np.cumsum(returns))
    
    # Generate OHLC from close
    high_offset = np.abs(np.random.normal(0, volatility * 0.7, num_candles))
    low_offset = np.abs(np.random.normal(0, volatility * 0.7, num_candles))
    
    high_prices = close_prices + high_offset * base_price
    low_prices = close_prices - low_offset * base_price
    
    # Open prices (with some randomness between high and low)
    open_prices = np.roll(close_prices, 1)
    open_prices[0] = close_prices[0]
    open_prices = open_prices + np.random.uniform(-volatility, volatility, num_candles) * base_price
    
    # Ensure OHLC relationships are correct
    high_prices = np.maximum.reduce([open_prices, close_prices, high_prices])
    low_prices = np.minimum.reduce([open_prices, close_prices, low_prices])
    
    # Volume (forex doesn't have real volume, use tick volume)
    volume = np.random.randint(1000, 10000, num_candles)
    
    df = pd.DataFrame({
        'open': open_prices,
        'high': high_prices,
        'low': low_prices,
        'close': close_prices,
        'volume': volume
    }, index=dates)
    
    return df


def create_mock_signal(signal_type='long', current_price=1.0850, symbol='EURUSD'):
    """
    Create mock signal data
    
    Args:
        signal_type: 'long' or 'short'
        current_price: Current market price
        symbol: Trading symbol
        
    Returns:
        Dictionary with signal data
    """
    # Calculate pip/point value based on symbol
    if 'JPY' in symbol:
        pip_value = 0.01  # For JPY pairs
    elif 'USD' in symbol:
        pip_value = 0.0001  # Standard forex pip
    elif symbol == 'GOLD':
        pip_value = 0.10  # Gold point
    elif symbol == 'BTC':
        pip_value = 10.0  # Bitcoin point
    else:
        pip_value = 1.0  # Index point
    
    if signal_type == 'long':
        entry = current_price
        stop_loss = current_price - (20 * pip_value)  # 20 pips/points
        take_profit = current_price + (50 * pip_value)  # 50 pips/points (2.5 R:R)
    else:  # short
        entry = current_price
        stop_loss = current_price + (20 * pip_value)
        take_profit = current_price - (50 * pip_value)
    
    # Calculate position size (simplified)
    position_size = 10000 if 'USD' in symbol else (100 if symbol == 'GOLD' else (0.1 if symbol == 'BTC' else 1))
    
    return {
        'signal_type': signal_type,
        'entry_price': entry,
        'stop_loss': stop_loss,
        'take_profit': take_profit,
        'position_size': position_size,
        'risk_reward_ratio': 2.5,
        'timestamp': datetime.now().isoformat()
    }


def create_strategy_params(strategy_name='mean_reversion'):
    """
    Create strategy parameters for different strategies
    
    Args:
        strategy_name: Name of the strategy
        
    Returns:
        Dictionary with strategy parameters
    """
    if strategy_name == 'mean_reversion':
        return {
            'bb_window': 20,
            'bb_std': 2.0,
            'vwap_window': 20,
            'vwap_std': 2.0,
            'atr_period': 14
        }
    elif strategy_name in ['vwap', 'vwap_btc']:
        return {
            'num_std': 1.0,
            'vwap_window': 20,
            'vwap_std': 1.0
        }
    elif strategy_name == 'session_sweep':
        return {
            'session_start': '03:00',
            'session_end': '07:00'
        }
    else:
        return {}


async def send_to_telegram_async(chart_bytes, caption):
    """
    Send chart to Telegram for visual testing
    
    Args:
        chart_bytes: Chart image as bytes
        caption: Caption for the image
        
    Returns:
        True if successful, False otherwise
    """
    from telegram import Bot
    import io
    
    if not TELEGRAM_BOT_TOKEN or not TEST_CHAT_ID:
        print("⚠️  Telegram credentials not configured. Set TELEGRAM_BOT_TOKEN and TEST_CHAT_ID in .env")
        return False
    
    try:
        bot = Bot(token=TELEGRAM_BOT_TOKEN)
        await bot.send_photo(
            chat_id=TEST_CHAT_ID,
            photo=io.BytesIO(chart_bytes),
            caption=caption,
            parse_mode='Markdown'
        )
        print(f"  ✅ Sent to Telegram chat {TEST_CHAT_ID}")
        return True
    except Exception as e:
        print(f"  ❌ Failed to send to Telegram: {e}")
        return False


def test_chart_generation():
    """Main test function"""
    print("=" * 80)
    print("🧪 CHART GENERATION TEST - DARK THEME")
    print("=" * 80)
    print()
    
    # Create output directory
    output_dir = Path('test_charts')
    output_dir.mkdir(exist_ok=True)
    print(f"📁 Output directory: {output_dir.absolute()}")
    print(f"🎨 Theme: {DEFAULT_CHART_CONFIG.get_theme_colors()['mode'].upper()}")
    print()
    
    # Initialize chart generator with dark theme
    print("🔧 Initializing chart generator...")
    generator = SignalChartGenerator()
    print()
    
    # Test cases: different strategies and signal types
    test_cases = [
        {
            'name': 'Mean Reversion Strategy - LONG Signal',
            'symbol': 'EURUSD',
            'signal_type': 'long',
            'strategy_name': 'mean_reversion',
            'custom_strategy': None,
            'filename': '1_mean_reversion_long.png',
            'description': 'Shows both Bollinger Bands (blue) and VWAP bands (purple)'
        },
        {
            'name': 'Mean Reversion Strategy - SHORT Signal',
            'symbol': 'GBPUSD',
            'signal_type': 'short',
            'strategy_name': 'mean_reversion',
            'custom_strategy': None,
            'filename': '2_mean_reversion_short.png',
            'description': 'Shows both Bollinger Bands (blue) and VWAP bands (purple)'
        },
        {
            'name': 'VWAP Strategy - LONG Signal',
            'symbol': 'GOLD',
            'signal_type': 'long',
            'strategy_name': 'custom_strategies',
            'custom_strategy': 'vwap',
            'filename': '3_vwap_long.png',
            'description': 'Shows only VWAP bands (purple), no Bollinger Bands'
        },
        {
            'name': 'Session Sweep Strategy - SHORT Signal',
            'symbol': 'DE40',
            'signal_type': 'short',
            'strategy_name': 'custom_strategies',
            'custom_strategy': 'session_sweep',
            'filename': '4_session_sweep_short.png',
            'description': 'Shows no indicators (session sweep uses session highs/lows)'
        }
    ]
    
    charts_generated = []
    
    for i, test_case in enumerate(test_cases, 1):
        print("─" * 80)
        print(f"[{i}/{len(test_cases)}] {test_case['name']}")
        print("─" * 80)
        
        # Generate sample data
        print(f"  📊 Generating {test_case['symbol']} data...")
        data = generate_sample_forex_data(symbol=test_case['symbol'])
        current_price = data['close'].iloc[-1]
        print(f"      Candles: {len(data)}, Current Price: {current_price:.5f}")
        
        # Create signal
        signal_data = create_mock_signal(test_case['signal_type'], current_price, test_case['symbol'])
        signal_data['symbol'] = test_case['symbol']
        signal_data['strategy_name'] = test_case['strategy_name']
        signal_data['custom_strategy'] = test_case['custom_strategy']
        
        print(f"  🎯 Signal: {signal_data['signal_type'].upper()}")
        print(f"      Entry: {signal_data['entry_price']:.5f}")
        print(f"      Stop Loss: {signal_data['stop_loss']:.5f}")
        print(f"      Take Profit: {signal_data['take_profit']:.5f}")
        print(f"      Risk/Reward: {signal_data['risk_reward_ratio']}:1")
        
        # Create strategy params
        strategy_params = create_strategy_params(test_case['custom_strategy'] or test_case['strategy_name'])
        
        # Show indicator visibility
        visibility = DEFAULT_CHART_CONFIG.get_indicator_visibility(
            test_case['strategy_name'],
            test_case['custom_strategy']
        )
        print(f"  📈 Indicators:")
        print(f"      Bollinger Bands: {'✓ Visible' if visibility['show_bb'] else '✗ Hidden'}")
        print(f"      VWAP Bands: {'✓ Visible' if visibility['show_vwap'] else '✗ Hidden'}")
        
        # Generate chart
        print(f"  🎨 Generating chart...")
        chart_bytes = generator.generate_signal_chart(
            data=data,
            signal_data=signal_data,
            strategy_params=strategy_params,
            symbol=test_case['symbol'],
            strategy_name=test_case['strategy_name'],
            custom_strategy=test_case['custom_strategy']
        )
        
        if chart_bytes:
            # Save to file
            output_path = output_dir / test_case['filename']
            with open(output_path, 'wb') as f:
                f.write(chart_bytes)
            file_size_kb = len(chart_bytes) / 1024
            print(f"  ✅ Chart saved: {output_path.name} ({file_size_kb:.1f} KB)")
            
            charts_generated.append({
                'test_case': test_case,
                'path': output_path,
                'bytes': chart_bytes,
                'signal_data': signal_data,
                'size_kb': file_size_kb
            })
        else:
            print(f"  ❌ Failed to generate chart")
        
        print()
    
    # Summary
    print("=" * 80)
    print("📊 TEST SUMMARY")
    print("=" * 80)
    print(f"✨ Charts generated: {len(charts_generated)}/{len(test_cases)}")
    
    if charts_generated:
        total_size = sum(c['size_kb'] for c in charts_generated)
        avg_size = total_size / len(charts_generated)
        print(f"📏 Total size: {total_size:.1f} KB (avg: {avg_size:.1f} KB per chart)")
        print()
        print("📂 Generated files:")
        for chart in charts_generated:
            print(f"   • {chart['path'].name} - {chart['test_case']['description']}")
    
    # Optional: Send to Telegram
    if SEND_TO_TELEGRAM and charts_generated:
        print()
        print("=" * 80)
        print("📱 SENDING TO TELEGRAM")
        print("=" * 80)
        
        for chart in charts_generated:
            print(f"Sending: {chart['test_case']['name']}...")
            
            # Create formatted caption
            caption = (
                f"*{chart['test_case']['name']}*\n\n"
                f"📊 *Symbol:* `{chart['signal_data']['symbol']}`\n"
                f"🎯 *Signal:* {chart['signal_data']['signal_type'].upper()}\n"
                f"💰 *Entry:* `{chart['signal_data']['entry_price']:.5f}`\n"
                f"🛑 *Stop Loss:* `{chart['signal_data']['stop_loss']:.5f}`\n"
                f"🎯 *Take Profit:* `{chart['signal_data']['take_profit']:.5f}`\n\n"
                f"🔧 *Strategy:* {chart['test_case']['strategy_name']}"
            )
            
            if chart['test_case']['custom_strategy']:
                caption += f" ({chart['test_case']['custom_strategy']})"
            
            caption += f"\n\n_{chart['test_case']['description']}_"
            
            asyncio.run(send_to_telegram_async(chart['bytes'], caption))
        
        print()
        print("✅ Telegram sending completed!")
    elif not SEND_TO_TELEGRAM:
        print()
        print("ℹ️  Telegram sending disabled. Set SEND_TO_TELEGRAM=true to enable.")
        print("   Also ensure TELEGRAM_BOT_TOKEN and TEST_CHAT_ID are set in .env")
    
    print()
    print("=" * 80)
    print("🎉 ALL TESTS COMPLETED!")
    print("=" * 80)
    print(f"📂 Charts saved in: {output_dir.absolute()}")
    print()
    
    return charts_generated


if __name__ == '__main__':
    try:
        test_chart_generation()
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

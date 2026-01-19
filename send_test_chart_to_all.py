#!/usr/bin/env python3
"""
Send Test Chart to All Active Telegram Chats

This script sends a sample dark theme chart to all active Telegram chats
for testing and verification purposes.

Usage:
    python3 send_test_chart_to_all.py
"""

import os
import sys
import asyncio
import pandas as pd
import numpy as np
from datetime import datetime
from pathlib import Path

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv()

# Add src to path
sys.path.append(str(Path(__file__).parent / 'src'))

from bot.signal_chart_generator import SignalChartGenerator
from bot.telegram_chat_manager import TelegramChatManager
from telegram import Bot
import io
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')

if not TELEGRAM_BOT_TOKEN:
    print("❌ Error: TELEGRAM_BOT_TOKEN not found in environment variables")
    print("   Please set it in your .env file or export it")
    sys.exit(1)


def generate_sample_data():
    """Generate sample EURUSD data for test chart"""
    num_candles = 200
    end_time = datetime.now()
    dates = pd.date_range(end=end_time, periods=num_candles, freq='5min')
    
    # Generate realistic forex price movement
    base_price = 1.0850
    returns = np.random.normal(0, 0.0003, num_candles)
    volatility_factor = np.abs(np.random.normal(1, 0.2, num_candles))
    returns = returns * volatility_factor
    
    close_prices = base_price * (1 + np.cumsum(returns))
    
    high_offset = np.abs(np.random.normal(0, 0.0002, num_candles))
    low_offset = np.abs(np.random.normal(0, 0.0002, num_candles))
    
    high_prices = close_prices + high_offset * base_price
    low_prices = close_prices - low_offset * base_price
    
    open_prices = np.roll(close_prices, 1)
    open_prices[0] = close_prices[0]
    
    high_prices = np.maximum.reduce([open_prices, close_prices, high_prices])
    low_prices = np.minimum.reduce([open_prices, close_prices, low_prices])
    
    volume = np.random.randint(1000, 10000, num_candles)
    
    df = pd.DataFrame({
        'open': open_prices,
        'high': high_prices,
        'low': low_prices,
        'close': close_prices,
        'volume': volume
    }, index=dates)
    
    return df


async def send_to_all_chats():
    """Main function to send test chart to all active chats"""
    print("=" * 80)
    print("📱 SENDING TEST CHART TO ALL ACTIVE TELEGRAM CHATS")
    print("=" * 80)
    print()
    
    # Initialize chat manager
    print("🔧 Initializing chat manager...")
    chat_manager = TelegramChatManager(use_dynamodb=True)
    
    # Load chats from storage
    print("📂 Loading active chats from DynamoDB...")
    num_loaded = chat_manager.load_chats_from_storage()
    
    active_chats = chat_manager.get_active_chats()
    
    if not active_chats:
        print("⚠️  No active chats found!")
        print("   Make sure users have started the bot with /start command")
        return
    
    print(f"✅ Found {len(active_chats)} active chat(s)")
    print()
    
    # Generate sample data
    print("📊 Generating sample EURUSD data...")
    data = generate_sample_data()
    current_price = data['close'].iloc[-1]
    print(f"   Candles: {len(data)}, Current Price: {current_price:.5f}")
    print()
    
    # Create signal data
    signal_data = {
        'signal_type': 'long',
        'entry_price': current_price,
        'stop_loss': current_price - 0.0020,
        'take_profit': current_price + 0.0050,
        'position_size': 10000,
        'risk_reward_ratio': 2.5,
        'symbol': 'EURUSD',
        'timestamp': datetime.now().isoformat()
    }
    
    print("🎯 Test Signal Details:")
    print(f"   Symbol: EURUSD")
    print(f"   Type: LONG")
    print(f"   Entry: {signal_data['entry_price']:.5f}")
    print(f"   Stop Loss: {signal_data['stop_loss']:.5f}")
    print(f"   Take Profit: {signal_data['take_profit']:.5f}")
    print()
    
    # Generate chart with dark theme
    print("🎨 Generating chart with dark theme...")
    print("   Strategy: Mean Reversion (shows BB + VWAP bands)")
    
    generator = SignalChartGenerator()
    
    strategy_params = {
        'bb_window': 20,
        'bb_std': 2.0,
        'vwap_window': 20,
        'vwap_std': 2.0,
        'atr_period': 14
    }
    
    chart_bytes = generator.generate_signal_chart(
        data=data,
        signal_data=signal_data,
        strategy_params=strategy_params,
        symbol='EURUSD',
        strategy_name='mean_reversion',
        custom_strategy=None
    )
    
    if not chart_bytes:
        print("❌ Failed to generate chart!")
        return
    
    file_size_kb = len(chart_bytes) / 1024
    print(f"✅ Chart generated successfully ({file_size_kb:.1f} KB)")
    print()
    
    # Create caption
    caption = (
        "🧪 *TEST CHART - NEW DARK THEME*\n\n"
        "This is a test of the new dark color palette for trading charts.\n\n"
        "📊 *Features:*\n"
        "• Dark background for better readability\n"
        "• Bright green/red candles\n"
        "• Light blue Bollinger Bands\n"
        "• Light purple VWAP bands\n"
        "• Gold entry line for high visibility\n\n"
        "📈 *Example Signal:*\n"
        f"Symbol: `EURUSD`\n"
        f"Type: LONG\n"
        f"Entry: `{signal_data['entry_price']:.5f}`\n"
        f"Stop Loss: `{signal_data['stop_loss']:.5f}`\n"
        f"Take Profit: `{signal_data['take_profit']:.5f}`\n\n"
        "_This is a test chart with sample data. Not a real trading signal._"
    )
    
    # Send to all chats
    print("=" * 80)
    print(f"📤 SENDING TO {len(active_chats)} CHAT(S)")
    print("=" * 80)
    print()
    
    bot = Bot(token=TELEGRAM_BOT_TOKEN)
    
    success_count = 0
    failed_count = 0
    
    for i, chat_id in enumerate(active_chats, 1):
        try:
            print(f"[{i}/{len(active_chats)}] Sending to chat {chat_id}...", end=" ")
            
            await bot.send_photo(
                chat_id=chat_id,
                photo=io.BytesIO(chart_bytes),
                caption=caption,
                parse_mode='Markdown'
            )
            
            success_count += 1
            print("✅")
            
            # Small delay to avoid rate limiting
            await asyncio.sleep(0.1)
            
        except Exception as e:
            failed_count += 1
            print(f"❌ Error: {e}")
    
    # Summary
    print()
    print("=" * 80)
    print("📊 SUMMARY")
    print("=" * 80)
    print(f"✅ Successfully sent: {success_count}/{len(active_chats)}")
    if failed_count > 0:
        print(f"❌ Failed: {failed_count}/{len(active_chats)}")
    print()
    print("🎉 Test complete!")
    print()


if __name__ == '__main__':
    try:
        asyncio.run(send_to_all_chats())
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

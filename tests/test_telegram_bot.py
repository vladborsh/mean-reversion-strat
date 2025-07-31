#!/usr/bin/env python3
"""
Telegram Bot Test Script

This script allows you to test the Telegram bot functionality independently
of the trading strategy. It's useful for setting up and testing your bot
before integrating it with the live trading system.

Usage:
    python src/bot/test_telegram_bot.py
"""

import asyncio
import logging
import os
import sys
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add src to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from bot.telegram_bot import create_telegram_bot_from_env, TelegramBotManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


async def test_telegram_bot():
    """Test the Telegram bot functionality"""
    
    print("\n🤖 Mean Reversion Strategy - Telegram Bot Test")
    print("=" * 60)
    
    # Check if bot token is available
    bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
    if not bot_token:
        print("❌ TELEGRAM_BOT_TOKEN not found in environment variables")
        print("Please set it in your .env file or environment")
        print("\nTo get a bot token:")
        print("1. Open Telegram and search for @BotFather")
        print("2. Send /start to @BotFather")
        print("3. Send /newbot and follow the instructions")
        print("4. Copy the bot token and add it to your .env file")
        return False
    
    print(f"✅ Bot token found: ...{bot_token[-10:]}")
    
    # Create bot instance
    bot = create_telegram_bot_from_env()
    if not bot:
        print("❌ Failed to create bot instance")
        return False
    
    print("✅ Bot instance created")
    
    try:
        # Test bot using context manager
        async with TelegramBotManager(bot) as active_bot:
            print("✅ Bot initialized and started")
            print(f"📊 Active chats: {active_bot.get_active_chat_count()}")
            
            print("\n📱 Bot is now running. Try these commands in Telegram:")
            print("   /start - Start receiving notifications")
            print("   /help - Show help message")
            print("   /status - Show bot status")
            print("   /stop - Stop notifications")
            
            print("\nPress Ctrl+C to test sending a signal notification...")
            
            # Wait for user interaction or signal test
            await asyncio.sleep(10)
            
            # Test sending a sample signal
            print("\n🚨 Testing signal notification...")
            
            test_signal = {
                'signal_type': 'long',
                'symbol': 'EURUSD',
                'direction': 'LONG',
                'entry_price': 1.1234,
                'stop_loss': 1.1200,
                'take_profit': 1.1300,
                'position_size': 1.5,
                'risk_amount': 50.0,
                'risk_reward_ratio': 2.0,
                'strategy_params': {
                    'bb_window': 20,
                    'bb_std': 2.0,
                    'vwap_window': 50,
                    'vwap_std': 1.5,
                    'atr_period': 14
                }
            }
            
            if active_bot.get_active_chat_count() > 0:
                result = await active_bot.send_signal_notification(test_signal)
                print(f"📤 Signal sent to {result.get('sent', 0)} chats")
                if result.get('failed', 0) > 0:
                    print(f"❌ Failed to send to {result['failed']} chats")
                    print(f"   Errors: {result.get('errors', [])}")
            else:
                print("⚠️  No active chats - start the bot with /start command first")
            
            # Show statistics
            stats = active_bot.get_bot_statistics()
            print(f"\n📈 Bot Statistics:")
            print(f"   Uptime: {stats['uptime_formatted']}")
            print(f"   Total commands: {stats['total_commands']}")
            print(f"   Active chats: {stats['active_chats']}")
            
            print("\nBot will continue running for 30 more seconds...")
            print("Try sending commands to test the bot functionality.")
            await asyncio.sleep(30)
            
            print("\n✅ Test completed successfully!")
            return True
            
    except KeyboardInterrupt:
        print("\n🛑 Test interrupted by user")
        return True
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        return False


async def interactive_test():
    """Interactive test mode"""
    
    print("\n🔄 Interactive Test Mode")
    print("Available commands:")
    print("  1 - Send test signal")
    print("  2 - Send custom message")
    print("  3 - Show bot statistics")
    print("  q - Quit")
    
    bot = create_telegram_bot_from_env()
    if not bot:
        return False
    
    try:
        async with TelegramBotManager(bot) as active_bot:
            print(f"\n✅ Bot ready! Active chats: {active_bot.get_active_chat_count()}")
            
            while True:
                try:
                    command = input("\nEnter command (1-3, q): ").strip().lower()
                    
                    if command == 'q':
                        break
                    elif command == '1':
                        # Send test signal
                        signal = {
                            'signal_type': 'short',
                            'symbol': 'GBPUSD',
                            'direction': 'SHORT',
                            'entry_price': 1.2650,
                            'stop_loss': 1.2680,
                            'take_profit': 1.2590,
                            'position_size': 2.0,
                            'risk_amount': 75.0,
                            'risk_reward_ratio': 2.0,
                            'strategy_params': {
                                'bb_window': 20,
                                'bb_std': 2.0,
                                'vwap_window': 50,
                                'vwap_std': 1.5,
                                'atr_period': 14
                            }
                        }
                        result = await active_bot.send_signal_notification(signal)
                        print(f"Signal sent to {result.get('sent', 0)} chats")
                        
                    elif command == '2':
                        # Send custom message
                        message = input("Enter custom message: ")
                        result = await active_bot.send_custom_message(message)
                        print(f"Message sent to {result.get('sent', 0)} chats")
                        
                    elif command == '3':
                        # Show statistics
                        stats = active_bot.get_bot_statistics()
                        print(f"\n📊 Statistics:")
                        print(f"   Active chats: {stats['active_chats']}")
                        print(f"   Total commands: {stats['total_commands']}")
                        print(f"   Uptime: {stats['uptime_formatted']}")
                        
                    else:
                        print("Invalid command")
                        
                except KeyboardInterrupt:
                    break
                except Exception as e:
                    print(f"Error: {e}")
            
            return True
            
    except Exception as e:
        logger.error(f"Interactive test failed: {e}")
        return False


def main():
    """Main function"""
    
    print("Select test mode:")
    print("1. Automatic test (recommended for first time)")
    print("2. Interactive test")
    
    try:
        choice = input("Enter choice (1 or 2): ").strip()
        
        if choice == '1':
            success = asyncio.run(test_telegram_bot())
        elif choice == '2':
            success = asyncio.run(interactive_test())
        else:
            print("Invalid choice")
            return
        
        if success:
            print("\n🎉 Test completed successfully!")
            print("\nNext steps:")
            print("1. Make sure your bot token is in the .env file")
            print("2. Start your bot with /start command in Telegram")
            print("3. Run the live strategy scheduler to receive real signals")
        else:
            print("\n❌ Test failed. Check the error messages above.")
            
    except KeyboardInterrupt:
        print("\n🛑 Test interrupted")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")


if __name__ == "__main__":
    main()

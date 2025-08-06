#!/usr/bin/env python3
"""
Telegram Bot Integration

This module provides the main Telegram bot class that handles commands,
manages chats, and integrates with the trading signal system.
"""

import asyncio
import logging
import os
from typing import Dict, Any, Optional
from datetime import datetime

# Telegram imports (will be installed)
try:
    from telegram import Update
    from telegram.ext import (
        Application, ApplicationBuilder, CommandHandler, 
        MessageHandler, ContextTypes, filters
    )
    from telegram.error import Forbidden, BadRequest
    TELEGRAM_AVAILABLE = True
except ImportError:
    TELEGRAM_AVAILABLE = False
    # Create dummy classes for development
    class Update: pass
    class ContextTypes:
        DEFAULT_TYPE = None

from .telegram_chat_manager import TelegramChatManager
from .telegram_message_templates import TelegramMessageTemplates
from .telegram_signal_notifier import TelegramSignalNotifier

logger = logging.getLogger(__name__)


class MeanReversionTelegramBot:
    """Main Telegram bot class for mean reversion strategy notifications"""
    
    def __init__(self, bot_token: str, use_dynamodb: bool = True, 
                 table_name: str = None, region_name: str = None,
                 auto_register_chats: bool = True):
        """
        Initialize the Telegram bot
        
        Args:
            bot_token: Telegram bot token from environment
            use_dynamodb: Whether to use DynamoDB for persistence (default: True)
            table_name: DynamoDB table name (optional)
            region_name: AWS region (optional)
            auto_register_chats: Automatically register new chats on any message (default: True)
        """
        if not TELEGRAM_AVAILABLE:
            raise ImportError("python-telegram-bot library not installed. Run: pip install python-telegram-bot")
        
        self.bot_token = bot_token
        self.application = None
        self.running = False
        self.auto_register_chats = auto_register_chats
        
        # Initialize components
        self.chat_manager = TelegramChatManager(use_dynamodb, table_name, region_name)
        self.templates = TelegramMessageTemplates()
        self.notifier = TelegramSignalNotifier(bot_token, self.chat_manager, self.templates)
        
        # Statistics
        self.start_time = datetime.now()
        self.command_count = 0
        
        logger.info(f"Mean Reversion Telegram Bot initialized (auto-register: {auto_register_chats})")
    
    async def initialize(self):
        """Initialize the Telegram bot application"""
        try:
            # Load existing chats from DynamoDB
            loaded_count = self.chat_manager.load_chats_from_storage()
            if loaded_count > 0:
                logger.info(f"Loaded {loaded_count} active chats from storage")
            
            # Build application
            self.application = ApplicationBuilder().token(self.bot_token).build()
            
            # Add command handlers
            self.application.add_handler(CommandHandler("start", self._handle_start))
            self.application.add_handler(CommandHandler("stop", self._handle_stop))
            self.application.add_handler(CommandHandler("help", self._handle_help))
            self.application.add_handler(CommandHandler("status", self._handle_status))
            
            # Add message handler for auto-registration (before unknown command handler)
            if self.auto_register_chats:
                # This handler will catch all non-command messages
                self.application.add_handler(
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self._handle_message)
                )
            
            # Add unknown command handler (must be last)
            self.application.add_handler(
                MessageHandler(filters.COMMAND, self._handle_unknown_command)
            )
            
            # Test bot connection
            if await self.notifier.test_bot_connection():
                logger.info("✅ Telegram bot initialized successfully")
                return True
            else:
                logger.error("❌ Failed to connect to Telegram bot")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error initializing Telegram bot: {e}")
            return False
    
    async def start_bot(self):
        """Start the Telegram bot (non-blocking)"""
        if not self.application:
            logger.error("Bot not initialized. Call initialize() first.")
            return False
        
        try:
            # Initialize and start the application
            await self.application.initialize()
            await self.application.start()
            await self.application.updater.start_polling()
            
            self.running = True
            logger.info("🤖 Telegram bot started and polling for updates")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error starting Telegram bot: {e}")
            return False
    
    async def stop_bot(self):
        """Stop the Telegram bot"""
        if self.application and self.running:
            try:
                await self.application.updater.stop()
                await self.application.stop()
                await self.application.shutdown()
                
                self.running = False
                logger.info("🛑 Telegram bot stopped")
                
            except Exception as e:
                logger.error(f"❌ Error stopping Telegram bot: {e}")
    
    async def send_signal_notification(self, signal_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Send trading signal notification to all active chats
        
        Args:
            signal_data: Dictionary containing signal information
            
        Returns:
            Dictionary with sending statistics
        """
        return await self.notifier.send_signal_notification(signal_data)
    
    async def send_error_notification(self, error_type: str, error_message: str) -> Dict[str, Any]:
        """Send error notification to active chats"""
        return await self.notifier.send_error_notification(error_type, error_message)
    
    async def send_custom_message(self, message: str) -> Dict[str, Any]:
        """Send custom message to all active chats"""
        return await self.notifier.send_custom_message(message)
    
    async def _auto_register_chat(self, update: Update) -> bool:
        """
        Auto-register a chat if it's not already registered
        
        Args:
            update: Telegram update object
            
        Returns:
            True if chat was newly registered, False if already registered
        """
        chat_id = update.effective_chat.id
        
        # Check if chat is already active
        if self.chat_manager.is_chat_active(chat_id):
            return False
        
        # Extract user info
        user = update.effective_user
        user_info = {
            'username': user.username,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'user_id': user.id,
            'auto_registered': True
        } if user else {'auto_registered': True}
        
        # Add chat to active chats
        was_new = self.chat_manager.add_chat(chat_id, user_info)
        
        if was_new:
            logger.info(f"Auto-registered new chat: {user_info.get('username', 'Unknown')} (ID: {chat_id})")
        
        return was_new
    
    # Command Handlers
    async def _handle_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        try:
            chat_id = update.effective_chat.id
            user = update.effective_user
            
            # Extract user info
            user_info = {
                'username': user.username,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'user_id': user.id
            } if user else {}
            
            # Add chat to active chats
            was_new = self.chat_manager.add_chat(chat_id, user_info)
            
            # Send welcome message
            await self.notifier.send_welcome_message(chat_id)
            
            self.command_count += 1
            
            if was_new:
                logger.info(f"New user started bot: {user_info.get('username', 'Unknown')} (ID: {chat_id})")
            else:
                logger.info(f"Existing user restarted bot: {user_info.get('username', 'Unknown')} (ID: {chat_id})")
                
        except Exception as e:
            logger.error(f"Error handling /start command: {e}")
    
    async def _handle_stop(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /stop command"""
        try:
            chat_id = update.effective_chat.id
            
            # Remove chat from active chats
            was_removed = self.chat_manager.remove_chat(chat_id)
            
            if was_removed:
                # Send stop confirmation
                message_data = self.templates.get_stop_message()
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=message_data['text'],
                    parse_mode=message_data.get('parse_mode', 'Markdown')
                )
                
                logger.info(f"User stopped notifications: {chat_id}")
            else:
                await context.bot.send_message(
                    chat_id=chat_id,
                    text="You weren't receiving notifications. Use /start to begin."
                )
            
            self.command_count += 1
            
        except Exception as e:
            logger.error(f"Error handling /stop command: {e}")
    
    async def _handle_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command"""
        try:
            chat_id = update.effective_chat.id
            await self.notifier.send_help_message(chat_id)
            self.command_count += 1
            
        except Exception as e:
            logger.error(f"Error handling /help command: {e}")
    
    async def _handle_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /status command"""
        try:
            chat_id = update.effective_chat.id
            await self.notifier.send_status_message(chat_id)
            self.command_count += 1
            
        except Exception as e:
            logger.error(f"Error handling /status command: {e}")
    
    async def _handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle regular text messages (for auto-registration)"""
        try:
            # Auto-register chat if needed
            was_new = await self._auto_register_chat(update)
            
            if was_new:
                # Send welcome message for auto-registered users
                await self.notifier.send_welcome_message(update.effective_chat.id)
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text="🎉 You've been automatically registered to receive trading signals!\n\n"
                         "Use /help to see available commands or /stop to unsubscribe."
                )
            else:
                # For existing users, just acknowledge the message
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text="👍 You're already registered for trading signals.\n"
                         "Use /help for available commands."
                )
            
            # Update activity
            self.chat_manager.update_chat_activity(update.effective_chat.id, 'message')
            
        except Exception as e:
            logger.error(f"Error handling message: {e}")
    
    async def _handle_unknown_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle unknown commands"""
        try:
            # Auto-register chat if enabled
            if self.auto_register_chats:
                await self._auto_register_chat(update)
            
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="❓ Sorry, I don't understand that command.\n\nUse /help to see available commands."
            )
            self.command_count += 1
            
        except Exception as e:
            logger.error(f"Error handling unknown command: {e}")
    
    # Utility Methods
    def get_bot_statistics(self) -> Dict[str, Any]:
        """Get bot statistics"""
        uptime = datetime.now() - self.start_time
        
        return {
            'bot_running': self.running,
            'uptime_seconds': uptime.total_seconds(),
            'uptime_formatted': str(uptime).split('.')[0],  # Remove microseconds
            'start_time': self.start_time.isoformat(),
            'total_commands': self.command_count,
            'active_chats': self.chat_manager.get_active_chat_count(),
            'chat_statistics': self.chat_manager.get_chat_statistics(),
            'notification_statistics': self.notifier.get_notification_statistics()
        }
    
    def is_running(self) -> bool:
        """Check if bot is running"""
        return self.running
    
    def get_active_chat_count(self) -> int:
        """Get number of active chats"""
        return self.chat_manager.get_active_chat_count()
    
    async def cleanup_inactive_chats(self, days_threshold: int = 30) -> int:
        """Clean up inactive chats"""
        return self.chat_manager.cleanup_inactive_chats(days_threshold)


# Utility function to create bot instance from environment
def create_telegram_bot_from_env(use_dynamodb: bool = True, 
                                 auto_register_chats: bool = True) -> Optional[MeanReversionTelegramBot]:
    """
    Create Telegram bot instance from environment variables
    
    Args:
        use_dynamodb: Whether to use DynamoDB for persistence (default: True)
        auto_register_chats: Automatically register new chats on any message (default: True)
        
    Returns:
        Bot instance or None if token not available
    """
    bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
    
    if not bot_token:
        logger.error("TELEGRAM_BOT_TOKEN not found in environment variables")
        return None
    
    # Get optional DynamoDB configuration from environment
    table_name = os.getenv('TELEGRAM_CHATS_TABLE')
    region_name = os.getenv('AWS_REGION')
    
    # Check for auto-registration setting in environment
    auto_register = os.getenv('TELEGRAM_AUTO_REGISTER', 'true').lower() == 'true'
    if not auto_register_chats:
        auto_register = False  # Override with parameter if explicitly set to False
    
    try:
        return MeanReversionTelegramBot(
            bot_token=bot_token,
            use_dynamodb=use_dynamodb,
            table_name=table_name,
            region_name=region_name,
            auto_register_chats=auto_register
        )
    except Exception as e:
        logger.error(f"Failed to create Telegram bot: {e}")
        return None


# Context manager for bot lifecycle
class TelegramBotManager:
    """Context manager for Telegram bot lifecycle"""
    
    def __init__(self, bot: MeanReversionTelegramBot):
        self.bot = bot
    
    async def __aenter__(self):
        """Initialize and start bot"""
        if await self.bot.initialize():
            if await self.bot.start_bot():
                return self.bot
            else:
                raise RuntimeError("Failed to start Telegram bot")
        else:
            raise RuntimeError("Failed to initialize Telegram bot")
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Stop bot"""
        await self.bot.stop_bot()


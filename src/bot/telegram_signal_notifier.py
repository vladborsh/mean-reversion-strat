#!/usr/bin/env python3
"""
Telegram Signal Notifier

This module handles sending trading signal notifications to active Telegram chats.
It integrates with the chat manager and message templates to deliver formatted
trading signals to subscribed users.
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from telegram import Bot
from telegram.error import Forbidden, BadRequest, TimedOut, NetworkError

from .telegram_chat_manager import TelegramChatManager
from .telegram_message_templates import TelegramMessageTemplates

logger = logging.getLogger(__name__)


class TelegramSignalNotifier:
    """Class for sending trading signals to Telegram chats"""
    
    def __init__(self, bot_token: str, chat_manager: TelegramChatManager, 
                 templates: TelegramMessageTemplates):
        """
        Initialize the signal notifier
        
        Args:
            bot_token: Telegram bot token
            chat_manager: Chat manager instance
            templates: Message templates instance
        """
        self.bot = Bot(token=bot_token)
        self.chat_manager = chat_manager
        self.templates = templates
        self.last_signal_time = None
        self.signal_count = 0
        self.failed_chats = set()
        
        logger.info("Telegram signal notifier initialized")
    
    async def send_signal_notification(self, signal_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Send trading signal notification to all active chats
        
        Args:
            signal_data: Dictionary containing signal information
            
        Returns:
            Dictionary with sending statistics
        """
        active_chats = self.chat_manager.get_active_chats()
        
        if not active_chats:
            logger.warning("No active chats to send signal notification")
            return {
                'sent': 0,
                'failed': 0,
                'total_chats': 0,
                'errors': []
            }
        
        # Get formatted message
        message_data = self.templates.get_trading_signal_message(signal_data)
        
        logger.info(f"Sending signal notification to {len(active_chats)} chats")
        logger.info(f"Signal: {signal_data.get('signal_type', 'Unknown')} - {signal_data.get('symbol', 'Unknown')}")
        
        # Send to all chats with error handling
        results = await self._send_to_multiple_chats(active_chats, message_data)
        
        # Update statistics
        self.signal_count += 1
        self.last_signal_time = datetime.now()
        
        # Log results
        logger.info(f"Signal notification sent: {results['sent']}/{results['total_chats']} successful")
        if results['failed'] > 0:
            logger.warning(f"Failed to send to {results['failed']} chats")
        
        return results
    
    async def send_error_notification(self, error_type: str, error_message: str) -> Dict[str, Any]:
        """
        Send error notification to all active chats
        
        Args:
            error_type: Type of error
            error_message: Error message details
            
        Returns:
            Dictionary with sending statistics
        """
        active_chats = self.chat_manager.get_active_chats()
        
        if not active_chats:
            return {'sent': 0, 'failed': 0, 'total_chats': 0, 'errors': []}
        
        # Get formatted message
        message_data = self.templates.get_error_message(error_type, error_message)
        
        logger.info(f"Sending error notification to {len(active_chats)} chats")
        
        # Send to all chats
        results = await self._send_to_multiple_chats(active_chats, message_data)
        
        logger.info(f"Error notification sent: {results['sent']}/{results['total_chats']} successful")
        
        return results
    
    async def send_custom_message(self, message_text: str, 
                                 parse_mode: str = 'Markdown') -> Dict[str, Any]:
        """
        Send custom message to all active chats
        
        Args:
            message_text: Message text to send
            parse_mode: Telegram parse mode
            
        Returns:
            Dictionary with sending statistics
        """
        active_chats = self.chat_manager.get_active_chats()
        
        if not active_chats:
            return {'sent': 0, 'failed': 0, 'total_chats': 0, 'errors': []}
        
        message_data = {
            'text': message_text,
            'parse_mode': parse_mode
        }
        
        logger.info(f"Sending custom message to {len(active_chats)} chats")
        
        # Send to all chats
        results = await self._send_to_multiple_chats(active_chats, message_data)
        
        logger.info(f"Custom message sent: {results['sent']}/{results['total_chats']} successful")
        
        return results
    
    async def _send_to_multiple_chats(self, chat_ids: set, message_data: Dict[str, str]) -> Dict[str, Any]:
        """
        Send message to multiple chats with error handling and rate limiting
        
        Args:
            chat_ids: Set of chat IDs to send to
            message_data: Message data with text and parse_mode
            
        Returns:
            Dictionary with sending statistics
        """
        results = {
            'sent': 0,
            'failed': 0,
            'total_chats': len(chat_ids),
            'errors': []
        }
        
        # Send messages with controlled concurrency to avoid rate limits
        semaphore = asyncio.Semaphore(5)  # Limit to 5 concurrent sends
        tasks = []
        
        for chat_id in chat_ids:
            task = self._send_single_message(semaphore, chat_id, message_data, results)
            tasks.append(task)
        
        # Wait for all sends to complete
        await asyncio.gather(*tasks, return_exceptions=True)
        
        return results
    
    async def _send_single_message(self, semaphore: asyncio.Semaphore, 
                                  chat_id: int, message_data: Dict[str, str], 
                                  results: Dict[str, Any]):
        """
        Send message to a single chat with error handling
        
        Args:
            semaphore: Asyncio semaphore for rate limiting
            chat_id: Chat ID to send to
            message_data: Message data
            results: Results dictionary to update
        """
        async with semaphore:
            try:
                await self.bot.send_message(
                    chat_id=chat_id,
                    text=message_data['text'],
                    parse_mode=message_data.get('parse_mode', 'Markdown'),
                    disable_web_page_preview=True
                )
                
                results['sent'] += 1
                
                # Remove from failed chats if it was there
                self.failed_chats.discard(chat_id)
                
                # Update chat activity
                self.chat_manager.update_chat_activity(chat_id, 'signal')
                
                # Small delay to avoid hitting rate limits
                await asyncio.sleep(0.05)
                
            except Forbidden as e:
                # User blocked the bot or chat is no longer accessible
                logger.warning(f"Bot blocked by user {chat_id}: {e}")
                results['failed'] += 1
                results['errors'].append(f"Chat {chat_id}: Bot blocked")
                
                # Remove chat from active chats
                self.chat_manager.remove_chat(chat_id)
                self.failed_chats.add(chat_id)
                
            except BadRequest as e:
                # Bad request (invalid chat_id, message too long, etc.)
                logger.error(f"Bad request for chat {chat_id}: {e}")
                results['failed'] += 1
                results['errors'].append(f"Chat {chat_id}: Bad request - {str(e)}")
                self.failed_chats.add(chat_id)
                
            except (TimedOut, NetworkError) as e:
                # Network issues - retry once
                logger.warning(f"Network error for chat {chat_id}: {e}")
                try:
                    await asyncio.sleep(1)  # Wait before retry
                    await self.bot.send_message(
                        chat_id=chat_id,
                        text=message_data['text'],
                        parse_mode=message_data.get('parse_mode', 'Markdown'),
                    disable_web_page_preview=True
                    )
                    results['sent'] += 1
                    self.failed_chats.discard(chat_id)
                    self.chat_manager.update_chat_activity(chat_id, 'signal')
                except Exception as retry_e:
                    logger.error(f"Retry failed for chat {chat_id}: {retry_e}")
                    results['failed'] += 1
                    results['errors'].append(f"Chat {chat_id}: Network error - {str(e)}")
                    self.failed_chats.add(chat_id)
                    
            except Exception as e:
                # Unexpected error
                logger.error(f"Unexpected error sending to chat {chat_id}: {e}")
                results['failed'] += 1
                results['errors'].append(f"Chat {chat_id}: Unexpected error - {str(e)}")
                self.failed_chats.add(chat_id)
    
    async def test_bot_connection(self) -> bool:
        """
        Test if the bot token is valid and bot is accessible
        
        Returns:
            True if connection successful
        """
        try:
            bot_info = await self.bot.get_me()
            logger.info(f"Bot connection successful: @{bot_info.username} ({bot_info.first_name})")
            return True
        except Exception as e:
            logger.error(f"Bot connection failed: {e}")
            return False
    
    def get_notification_statistics(self) -> Dict[str, Any]:
        """
        Get notification statistics
        
        Returns:
            Dictionary with statistics
        """
        return {
            'total_signals_sent': self.signal_count,
            'last_signal_time': self.last_signal_time.isoformat() if self.last_signal_time else None,
            'active_chats': self.chat_manager.get_active_chat_count(),
            'failed_chats': len(self.failed_chats),
            'failed_chat_ids': list(self.failed_chats)
        }
    
    async def cleanup_failed_chats(self):
        """Remove persistently failed chats from active list"""
        for chat_id in self.failed_chats.copy():
            self.chat_manager.remove_chat(chat_id)
            logger.info(f"Removed persistently failed chat: {chat_id}")
        
        self.failed_chats.clear()
        logger.info("Cleaned up failed chats")
    
    async def send_welcome_message(self, chat_id: int) -> bool:
        """
        Send welcome message to a specific chat
        
        Args:
            chat_id: Chat ID to send welcome message to
            
        Returns:
            True if sent successfully
        """
        try:
            message_data = self.templates.get_welcome_message()
            await self.bot.send_message(
                chat_id=chat_id,
                text=message_data['text'],
                parse_mode=message_data.get('parse_mode', 'Markdown'),
                disable_web_page_preview=True
            )
            
            self.chat_manager.update_chat_activity(chat_id, 'welcome')
            logger.info(f"Sent welcome message to chat {chat_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send welcome message to chat {chat_id}: {e}")
            return False
    
    async def send_help_message(self, chat_id: int) -> bool:
        """
        Send help message to a specific chat
        
        Args:
            chat_id: Chat ID to send help message to
            
        Returns:
            True if sent successfully
        """
        try:
            message_data = self.templates.get_help_message()
            await self.bot.send_message(
                chat_id=chat_id,
                text=message_data['text'],
                parse_mode=message_data.get('parse_mode', 'Markdown'),
                disable_web_page_preview=True
            )
            
            self.chat_manager.update_chat_activity(chat_id, 'help')
            logger.info(f"Sent help message to chat {chat_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send help message to chat {chat_id}: {e}")
            return False
    
    async def send_status_message(self, chat_id: int) -> bool:
        """
        Send status message to a specific chat
        
        Args:
            chat_id: Chat ID to send status message to
            
        Returns:
            True if sent successfully
        """
        try:
            # Gather status information
            status = "Active" if self.chat_manager.get_active_chat_count() > 0 else "No active chats"
            last_signal = self.last_signal_time.strftime('%Y-%m-%d %H:%M UTC') if self.last_signal_time else "None"
            active_chats = self.chat_manager.get_active_chat_count()
            
            # Assuming we have access to symbols count (you might need to pass this)
            symbols_count = "Multiple"  # This should be passed from the strategy scheduler
            
            message_data = self.templates.get_status_message(
                status, last_signal, active_chats, symbols_count
            )
            
            await self.bot.send_message(
                chat_id=chat_id,
                text=message_data['text'],
                parse_mode=message_data.get('parse_mode', 'Markdown'),
                disable_web_page_preview=True
            )
            
            self.chat_manager.update_chat_activity(chat_id, 'status')
            logger.info(f"Sent status message to chat {chat_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send status message to chat {chat_id}: {e}")
            return False

#!/usr/bin/env python3
"""
News Notification Handler

This module handles sending economic news notifications through the existing
Telegram bot infrastructure. It uses the existing bot manager and chat manager
to deliver news to active subscribers.
"""

import logging
import os
import sys
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
import asyncio

# Add parent directory to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from bot.telegram_bot import TelegramBotManager, create_telegram_bot_from_env
from .news_templates import NewsMessageTemplates
from .news_dynamodb_storage import NewsDynamoDBStorage

logger = logging.getLogger(__name__)


class NewsNotifier:
    """Handles sending news notifications through Telegram"""
    
    def __init__(self, bot_manager: Optional[TelegramBotManager] = None,
                 storage: Optional[NewsDynamoDBStorage] = None):
        """
        Initialize news notifier
        
        Args:
            bot_manager: Required existing bot manager instance
            storage: Optional DynamoDB storage instance
        """
        # Use provided bot manager
        if not bot_manager:
            logger.error("Bot manager is required for news notifier")
            raise ValueError("Bot manager must be provided")
        
        self.bot_manager = bot_manager
        logger.info("Using existing bot manager for news notifications")
        
        # Initialize storage
        self.storage = storage or NewsDynamoDBStorage()
        
        # Initialize templates
        self.templates = NewsMessageTemplates()
        
        # Statistics
        self.notifications_sent = 0
        self.last_notification_time = None
        
        logger.info("News notifier initialized")
    
    
    async def send_daily_summary(self, impact_filter: Optional[List[str]] = None, 
                               currency_filter: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Send daily economic calendar summary to all active chats
        
        Args:
            impact_filter: Optional list of impact levels to include
            currency_filter: Optional list of currencies to include
            
        Returns:
            Dictionary with sending statistics
        """
        logger.info("Preparing daily news summary")
        
        # Get today's events from storage with filters
        events = self.storage.get_today_events(
            impact_filter=impact_filter,
            currency_filter=currency_filter
        )
        
        # Get formatted message
        message_data = self.templates.get_daily_summary(events)
        
        # Get active chats
        active_chats = self.bot_manager.chat_manager.get_active_chats()
        
        if not active_chats:
            logger.warning("No active chats to send daily summary")
            return {
                'sent': 0,
                'failed': 0,
                'total_chats': 0,
                'events': len(events)
            }
        
        logger.info(f"Sending daily summary to {len(active_chats)} chats ({len(events)} events)")
        
        # Send to all active chats
        results = await self._broadcast_message(message_data, active_chats)
        
        # Mark events as notified
        if events and results['sent'] > 0:
            notified_count = self.storage.mark_multiple_as_notified(events)
            logger.info(f"Marked {notified_count} events as notified")
        
        # Update statistics
        self.notifications_sent += results['sent']
        self.last_notification_time = datetime.now(timezone.utc)
        
        results['events'] = len(events)
        
        logger.info(f"Daily summary sent: {results['sent']}/{results['total_chats']} successful")
        
        return results
    
    async def send_daily_summary_selective(self, currency_filter: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Send daily news summary with selective impact filtering (Medium+ for USD, High for others)

        Args:
            currency_filter: List of currencies to include

        Returns:
            Dictionary with sending statistics
        """
        logger.info(f"📰 Preparing daily summary with selective impact filtering (currencies: {currency_filter})")

        # Get today's events with selective filtering
        events = self.storage.get_today_events_selective(currency_filter=currency_filter)

        if not events:
            logger.warning("⚠️  No events found for daily summary with selective filtering")
            return {
                'sent': 0,
                'failed': 0,
                'total_chats': 0,
                'events': 0
            }

        logger.info(f"📊 Found {len(events)} events to notify about")

        # Get formatted message
        message_data = self.templates.get_daily_summary(events)

        # Get active chats
        active_chats = self.bot_manager.chat_manager.get_active_chats()

        if not active_chats:
            logger.warning("⚠️  No active chats found - notifications not sent")
            return {
                'sent': 0,
                'failed': 0,
                'total_chats': 0,
                'events': len(events)
            }

        logger.info(f"📱 Sending to {len(active_chats)} active chat(s)")
        
        # Send to all active chats
        sent_count = 0
        failed_count = 0
        
        for chat_id in active_chats:
            try:
                await self.bot_manager.send_message(
                    chat_id=chat_id,
                    message=message_data['message'],
                    parse_mode='Markdown'
                )
                sent_count += 1
                logger.info(f"Sent selective daily summary to chat {chat_id}")
                
            except Exception as e:
                logger.error(f"Failed to send selective daily summary to chat {chat_id}: {e}")
                failed_count += 1
        
        result = {
            'sent': sent_count,
            'failed': failed_count,
            'total_chats': len(active_chats),
            'events': len(events)
        }

        if sent_count > 0:
            logger.info(f"✅ Daily summary sent successfully: {sent_count}/{len(active_chats)} chats, {len(events)} events")
        else:
            logger.warning(f"⚠️  Daily summary not sent: {failed_count} failures")

        return result
    
    async def send_high_impact_alerts(self, hours_ahead: int = 1, 
                                    currency_filter: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Send alerts for upcoming high-impact events
        
        Args:
            hours_ahead: Number of hours to look ahead
            currency_filter: Optional list of currencies to include
            
        Returns:
            Dictionary with sending statistics
        """
        logger.info(f"Checking for high-impact events in next {hours_ahead} hours")
        
        # Get upcoming high-impact events with currency filter
        events = self.storage.get_upcoming_events(
            hours=hours_ahead,
            impact_filter=['High'],
            currency_filter=currency_filter
        )
        
        if not events:
            logger.info("No high-impact events coming up")
            return {
                'sent': 0,
                'failed': 0,
                'total_chats': 0,
                'events': 0
            }
        
        # Get active chats
        active_chats = self.bot_manager.chat_manager.get_active_chats()
        
        if not active_chats:
            logger.warning("No active chats for high-impact alerts")
            return {
                'sent': 0,
                'failed': 0,
                'total_chats': 0,
                'events': len(events)
            }
        
        total_sent = 0
        total_failed = 0
        
        # Send alert for each high-impact event
        for event in events:
            logger.info(f"Sending alert for: {event.get('title')} ({event.get('country')})")
            
            # Get formatted alert message
            message_data = self.templates.get_high_impact_alert(event)
            
            # Send to all chats
            results = await self._broadcast_message(message_data, active_chats)
            
            total_sent += results['sent']
            total_failed += results['failed']
            
            # Mark as notified
            if results['sent'] > 0:
                self.storage.mark_as_notified(event['event_id'], event['event_date'])
            
            # Small delay between alerts
            await asyncio.sleep(1)
        
        # Update statistics
        self.notifications_sent += total_sent
        self.last_notification_time = datetime.now(timezone.utc)
        
        logger.info(f"High-impact alerts sent: {total_sent} successful for {len(events)} events")
        
        return {
            'sent': total_sent,
            'failed': total_failed,
            'total_chats': len(active_chats),
            'events': len(events)
        }
    
    async def send_upcoming_events(self, hours: int = 24) -> Dict[str, Any]:
        """
        Send summary of upcoming events
        
        Args:
            hours: Number of hours to look ahead
            
        Returns:
            Dictionary with sending statistics
        """
        logger.info(f"Preparing upcoming events summary for next {hours} hours")

        # Get upcoming events (Note: impact_filter should be passed from caller)
        events = self.storage.get_upcoming_events(
            hours=hours,
            impact_filter=['High', 'Medium', 'Holiday']  # Default filter
        )
        
        # Get formatted message
        message_data = self.templates.get_upcoming_events(events, hours)
        
        # Get active chats
        active_chats = self.bot_manager.chat_manager.get_active_chats()
        
        if not active_chats:
            logger.warning("No active chats for upcoming events")
            return {
                'sent': 0,
                'failed': 0,
                'total_chats': 0,
                'events': len(events)
            }
        
        # Send to all chats
        results = await self._broadcast_message(message_data, active_chats)
        
        results['events'] = len(events)
        
        logger.info(f"Upcoming events sent: {results['sent']}/{results['total_chats']} successful")
        
        return results
    
    async def send_fetch_summary(self, fetch_result: Dict[str, int]) -> Dict[str, Any]:
        """
        Send summary of weekly fetch operation to admins
        
        Args:
            fetch_result: Fetch operation results
            
        Returns:
            Dictionary with sending statistics
        """
        # Get formatted message
        message_data = self.templates.get_weekly_fetch_summary(fetch_result)
        
        # For now, send to all active chats (could be limited to admins)
        active_chats = self.bot_manager.chat_manager.get_active_chats()
        
        if not active_chats:
            logger.warning("No active chats for fetch summary")
            return {
                'sent': 0,
                'failed': 0,
                'total_chats': 0
            }
        
        # Send summary
        results = await self._broadcast_message(message_data, active_chats)
        
        logger.info(f"Fetch summary sent: {results['sent']}/{results['total_chats']} successful")
        
        return results
    
    async def _broadcast_message(self, message_data: Dict[str, str], 
                                chat_ids: set) -> Dict[str, Any]:
        """
        Broadcast message to multiple chats
        
        Args:
            message_data: Message with text and parse_mode
            chat_ids: Set of chat IDs
            
        Returns:
            Dictionary with statistics
        """
        results = {
            'sent': 0,
            'failed': 0,
            'total_chats': len(chat_ids),
            'errors': []
        }
        
        # Use the signal notifier from bot manager for actual sending
        if hasattr(self.bot_manager, 'signal_notifier'):
            # Reuse existing broadcast logic
            send_results = await self.bot_manager.signal_notifier._send_to_multiple_chats(
                chat_ids, message_data
            )
            results.update(send_results)
        else:
            # Fallback to direct sending
            for chat_id in chat_ids:
                try:
                    await self.bot_manager.bot.send_message(
                        chat_id=chat_id,
                        text=message_data['text'],
                        parse_mode=message_data.get('parse_mode', 'Markdown'),
                        disable_web_page_preview=True
                    )
                    results['sent'] += 1
                    
                    # Update chat activity
                    self.bot_manager.chat_manager.update_chat_activity(chat_id, 'news')
                    
                except Exception as e:
                    logger.error(f"Failed to send to chat {chat_id}: {e}")
                    results['failed'] += 1
                    results['errors'].append(f"Chat {chat_id}: {str(e)}")
                
                # Small delay to avoid rate limiting
                await asyncio.sleep(0.05)
        
        return results
    
    async def send_custom_news_message(self, message: str) -> Dict[str, Any]:
        """
        Send custom news message to all active chats
        
        Args:
            message: Custom message text
            
        Returns:
            Dictionary with statistics
        """
        message_data = {
            'text': message,
            'parse_mode': 'Markdown'
        }
        
        active_chats = self.bot_manager.chat_manager.get_active_chats()
        
        if not active_chats:
            return {
                'sent': 0,
                'failed': 0,
                'total_chats': 0
            }
        
        results = await self._broadcast_message(message_data, active_chats)
        
        logger.info(f"Custom message sent: {results['sent']}/{results['total_chats']} successful")
        
        return results
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get notification statistics
        
        Returns:
            Dictionary with statistics
        """
        storage_stats = self.storage.get_statistics()
        
        return {
            'notifications_sent': self.notifications_sent,
            'last_notification': self.last_notification_time.isoformat() if self.last_notification_time else None,
            'active_chats': self.bot_manager.chat_manager.get_active_chat_count(),
            'storage': storage_stats
        }
    
    async def test_connection(self) -> bool:
        """
        Test bot connection
        
        Returns:
            True if connection successful
        """
        try:
            if hasattr(self.bot_manager, 'signal_notifier'):
                return await self.bot_manager.signal_notifier.test_bot_connection()
            else:
                bot_info = await self.bot_manager.bot.get_me()
                logger.info(f"Bot connection test successful: @{bot_info.username}")
                return True
        except Exception as e:
            logger.error(f"Bot connection test failed: {e}")
            return False
#!/usr/bin/env python3
"""
News Scheduler

Independent scheduler for economic news fetching and notifications.
Runs two main tasks:
1. Weekly news fetch (Sundays)
2. Daily morning notifications
"""

import asyncio
import logging
import os
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, List

from .news_fetcher import NewsFetcher
from .news_notifier import NewsNotifier
from .news_dynamodb_storage import NewsDynamoDBStorage
from .news_config import NewsConfig

logger = logging.getLogger(__name__)


class NewsScheduler:
    """Component for news fetching and notification tasks"""
    
    def __init__(self, bot_manager=None, symbols_config=None, bot_config=None):
        """Initialize the news scheduler component

        Args:
            bot_manager: Existing TelegramBotManager instance
            symbols_config: Dictionary of trading symbols configuration
            bot_config: News configuration from bot_config.json
        """
        # Initialize configuration
        self.config = NewsConfig(symbols_config=symbols_config, bot_config=bot_config)
        
        # Initialize components
        self.storage = NewsDynamoDBStorage()
        self.fetcher = NewsFetcher(storage=self.storage)
        self.notifier = NewsNotifier(bot_manager=bot_manager, storage=self.storage)
        
        # State
        self.last_fetch_date = None
        self.last_notification_date = None
        
        logger.info("News scheduler initialized")
        
        # Log brief today's events summary
        self._log_todays_events_summary()
    
    def _log_todays_events_summary(self):
        """Log brief summary of today's events"""
        try:
            events = self.storage.get_today_events(
                impact_filter=self.config.impact_filter,
                currency_filter=self.config.relevant_currencies
            )

            if events:
                high_count = sum(1 for e in events if e.get('impact') == 'High')
                medium_count = sum(1 for e in events if e.get('impact') == 'Medium')
                holiday_count = sum(1 for e in events if e.get('impact') == 'Holiday')
                logger.info(f"Today's events: {len(events)} total (H:{high_count}, M:{medium_count}, Holidays:{holiday_count})")
            else:
                logger.info("No significant events today")

        except Exception as e:
            logger.debug(f"Could not retrieve today's events: {e}")
    
    
    async def initialize(self) -> bool:
        """
        Initialize news components and check current week status

        Returns:
            True if successful
        """
        try:
            logger.info("News components initialized successfully")

            # Check current week events
            week_info = self.storage.has_current_week_events()
            event_count = week_info.get('event_count', 0)

            if week_info.get('has_events'):
                logger.info(f"✅ Current week has {event_count} events in storage")

                # Check if news is recent (within last 3 days)
                try:
                    stats = self.storage.get_statistics()
                    last_updated = stats.get('last_updated')

                    if last_updated:
                        days_old = (datetime.now(timezone.utc) - last_updated).days
                        if days_old > 3:
                            logger.warning(f"⚠️  News is {days_old} days old - will fetch on next cycle")
                        else:
                            logger.info(f"✅ News is current ({days_old} days old)")
                except Exception as e:
                    logger.debug(f"Could not check news age: {e}")
            else:
                logger.info(f"⚠️  No events for current week (or <20 events) - will fetch on next cycle")

            # Log today's events summary
            self._log_todays_events_summary()

            return True

        except Exception as e:
            logger.error(f"News initialization failed: {e}")
            return False
    
    async def fetch_weekly_news(self) -> Dict[str, Any]:
        """
        Fetch weekly economic calendar
        
        Returns:
            Fetch result statistics
        """
        logger.info("Starting weekly news fetch")
        
        try:
            # Fetch and save news
            result = self.fetcher.fetch_and_save()
            
            # Send summary to users
            await self.notifier.send_fetch_summary(result)
            
            # Update last fetch date
            self.last_fetch_date = datetime.now(timezone.utc).date()
            
            logger.info(f"Weekly fetch complete: {result}")
            return result
            
        except Exception as e:
            logger.error(f"Weekly fetch failed: {e}")
            
            # Send error notification
            try:
                await self.notifier.send_custom_news_message(
                    "⚠️ *Weekly News Fetch Error*\n\n"
                    f"Failed to fetch economic calendar.\n"
                    f"Error: `{str(e)}`\n\n"
                    "_Will retry at next scheduled time._"
                )
            except:
                pass
            
            return {'saved': 0, 'skipped': 0, 'errors': 1, 'total': 0}
    
    async def send_daily_notifications(self) -> Dict[str, Any]:
        """
        Send daily news notifications with selective impact filtering

        Returns:
            Notification statistics
        """
        logger.info("Starting daily news notifications (morning summary only)")

        try:
            # Send daily summary with selective impact filtering (USD: High+Medium, Others: High only)
            result = await self.notifier.send_daily_summary_selective(
                currency_filter=self.config.relevant_currencies
            )

            # Update last notification date
            self.last_notification_date = datetime.now(timezone.utc).date()

            logger.info(f"Daily notifications complete: {result}")
            return result

        except Exception as e:
            logger.error(f"Daily notifications failed: {e}")
            return {'sent': 0, 'failed': 0, 'total_chats': 0, 'events': 0}

    async def run_daily_cycle(self) -> Dict[str, Any]:
        """
        Run daily news cycle at 7am UTC (weekdays only)

        This is the simplified daily execution method called by the orchestrator:
        1. Check if current week has news (threshold: 20 events)
        2. Fetch news if needed (missing or insufficient)
        3. Send daily summary notification

        Returns:
            Execution result with statistics
        """
        now = datetime.now(timezone.utc)
        day_name = now.strftime('%A')

        # Skip weekends
        if day_name in ['Saturday', 'Sunday']:
            logger.info(f"⏭️  Skipping news cycle - weekend ({day_name})")
            return {
                'status': 'skipped_weekend',
                'day': day_name,
                'timestamp': now.isoformat()
            }

        logger.info(f"📰 Running daily news cycle - {day_name} 7:00 UTC")

        try:
            # Check if we need to fetch news
            week_info = self.storage.has_current_week_events()
            event_count = week_info.get('event_count', 0)

            fetch_result = {'saved': 0, 'skipped': 0}

            # Fetch if missing or insufficient events (threshold: 20)
            if not week_info.get('has_events') or event_count < 20:
                logger.info(f"Fetching news - current week has {event_count} events (threshold: 20)")
                fetch_result = self.fetcher.fetch_and_save()
                logger.info(f"Fetch complete: {fetch_result['saved']} new, {fetch_result['skipped']} skipped")
            else:
                logger.info(f"Current week has {event_count} events - skipping fetch")

            # Send daily notifications (selective filtering: USD High+Medium, Others High only)
            notify_result = await self.notifier.send_daily_summary_selective(
                currency_filter=self.config.relevant_currencies
            )

            logger.info(f"📊 Daily notifications: sent={notify_result.get('sent', 0)}, failed={notify_result.get('failed', 0)}, events={notify_result.get('events', 0)}, chats={notify_result.get('total_chats', 0)}")

            # Log tomorrow's events
            tomorrow = now.date() + timedelta(days=1)
            tomorrow_events = self.storage.get_events_for_date(
                tomorrow,
                impact_filter=self.config.impact_filter,
                currency_filter=self.config.relevant_currencies
            )
            if tomorrow_events:
                logger.info(f"📅 Tomorrow's events: {len(tomorrow_events)} scheduled")
            else:
                logger.info("📅 No news events scheduled for tomorrow")

            return {
                'status': 'success',
                'day': day_name,
                'fetch': fetch_result,
                'notifications': notify_result,
                'tomorrow_events': len(tomorrow_events) if tomorrow_events else 0,
                'timestamp': now.isoformat()
            }

        except Exception as e:
            logger.error(f"❌ Daily news cycle failed: {e}", exc_info=True)

            # Try to send error notification
            try:
                if self.notifier and self.notifier.bot_manager:
                    await self.notifier.send_custom_news_message(
                        "⚠️ *Daily News Cycle Error*\n\n"
                        f"Failed to complete daily news cycle.\n"
                        f"Error: `{str(e)}`\n\n"
                        "_Will retry tomorrow at 7am UTC._"
                    )
            except:
                pass

            return {
                'status': 'failed',
                'day': day_name,
                'error': str(e),
                'timestamp': now.isoformat()
            }
    
    def _is_fetch_day(self) -> bool:
        """
        Check if today is the scheduled fetch day
        
        Returns:
            True if today is fetch day
        """
        today = datetime.now(timezone.utc)
        day_name = today.strftime('%A')
        return day_name == self.config.fetch_day
    
    def should_fetch_now(self) -> bool:
        """
        Check if it's time to fetch news
        
        Returns:
            True if should fetch now
        """
        if not self._is_fetch_day():
            return False
        
        now = datetime.now(timezone.utc)
        
        # Check if already fetched today
        if self.last_fetch_date == now.date():
            return False
        
        # Check if it's the right time (within the minute)
        if now.hour == self.config.fetch_hour and now.minute == self.config.fetch_minute:
            return True
        
        return False
    
    def should_notify_now(self) -> bool:
        """
        Check if it's time to send daily notifications
        
        Returns:
            True if should notify now
        """
        now = datetime.now(timezone.utc)
        
        # Check if already notified today
        if self.last_notification_date == now.date():
            return False
        
        # Check if it's the right time (within the minute)
        if now.hour == self.config.notify_hour and now.minute == self.config.notify_minute:
            return True
        
        return False
    
    def _get_next_fetch_time(self) -> datetime:
        """
        Calculate next fetch time
        
        Returns:
            Next fetch datetime
        """
        now = datetime.now(timezone.utc)
        
        # Find next occurrence of fetch day
        days_ahead = 0
        for i in range(7):
            future_date = now + timedelta(days=i)
            if future_date.strftime('%A') == self.config.fetch_day:
                days_ahead = i
                break
        
        # If it's fetch day but time has passed, use next week
        if days_ahead == 0:
            fetch_time = now.replace(hour=self.config.fetch_hour, minute=self.config.fetch_minute, second=0, microsecond=0)
            if fetch_time <= now:
                days_ahead = 7
        
        next_fetch = now + timedelta(days=days_ahead)
        next_fetch = next_fetch.replace(hour=self.config.fetch_hour, minute=self.config.fetch_minute, second=0, microsecond=0)
        
        return next_fetch
    
    def _get_next_notification_time(self) -> datetime:
        """
        Calculate next notification time
        
        Returns:
            Next notification datetime
        """
        now = datetime.now(timezone.utc)
        
        # Today's notification time
        notify_time = now.replace(hour=self.config.notify_hour, minute=self.config.notify_minute, second=0, microsecond=0)
        
        # If already passed, use tomorrow
        if notify_time <= now:
            notify_time += timedelta(days=1)
        
        return notify_time
    
    async def test_components(self):
        """Test all components"""
        logger.info("Testing news scheduler components...")
        
        # Test storage
        try:
            stats = self.storage.get_statistics()
            logger.info(f"✅ Storage: {stats}")
        except Exception as e:
            logger.error(f"❌ Storage test failed: {e}")
        
        # Test fetcher
        try:
            test_events = self.fetcher.get_test_events()
            logger.info(f"✅ Fetcher: Generated {len(test_events)} test events")
        except Exception as e:
            logger.error(f"❌ Fetcher test failed: {e}")
        
        # Test notifier
        try:
            if await self.notifier.test_connection():
                logger.info("✅ Notifier: Bot connection successful")
            else:
                logger.error("❌ Notifier: Bot connection failed")
        except Exception as e:
            logger.error(f"❌ Notifier test failed: {e}")
    
    async def run_once(self, task: str = 'both'):
        """
        Run tasks once for testing
        
        Args:
            task: 'fetch', 'notify', or 'both'
        """
        logger.info(f"Running task once: {task}")
        
        if task in ['fetch', 'both']:
            await self.fetch_weekly_news()
        
        if task in ['notify', 'both']:
            await self.send_daily_notifications()
    
    async def run_scheduler(self):
        """
        Main scheduler loop that runs continuously
        
        Checks every minute for scheduled tasks and executes them
        """
        logger.info("Starting news scheduler loop")
        
        # Log today's events at startup
        self._log_todays_events()
        
        # Log next scheduled times
        next_fetch = self._get_next_fetch_time()
        next_notify = self._get_next_notification_time()
        logger.info(f"Next fetch scheduled for: {next_fetch.strftime('%Y-%m-%d %H:%M UTC')}")
        logger.info(f"Next notification scheduled for: {next_notify.strftime('%Y-%m-%d %H:%M UTC')}")
        
        while True:
            try:
                # Check for fetch task
                if self.should_fetch_now():
                    logger.info("Executing scheduled weekly fetch")
                    await self.fetch_weekly_news()
                    
                    # Log next fetch time
                    next_fetch = self._get_next_fetch_time()
                    logger.info(f"Next fetch scheduled for: {next_fetch.strftime('%Y-%m-%d %H:%M UTC')}")
                
                # Check for notification task
                if self.should_notify_now():
                    logger.info("Executing scheduled daily notification")
                    await self.send_daily_notifications()
                    
                    # Log next notification time
                    next_notify = self._get_next_notification_time()
                    logger.info(f"Next notification scheduled for: {next_notify.strftime('%Y-%m-%d %H:%M UTC')}")
                    
                    # Log tomorrow's events after sending today's notifications
                    logger.info("Checking tomorrow's events...")
                    tomorrow = datetime.now(timezone.utc).date() + timedelta(days=1)
                    tomorrow_events = self.storage.get_events_for_date(
                        tomorrow,
                        impact_filter=self.config.impact_filter,
                        currency_filter=self.config.relevant_currencies
                    )
                    if tomorrow_events:
                        logger.info(f"📅 Tomorrow's events: {len(tomorrow_events)} scheduled")
                    else:
                        logger.info("📅 No news events scheduled for tomorrow")
                
                # Sleep for 60 seconds before next check
                await asyncio.sleep(60)
                
            except asyncio.CancelledError:
                logger.info("Scheduler cancelled")
                break
                
            except Exception as e:
                logger.error(f"Scheduler error: {e}", exc_info=True)
                # Continue running despite errors
                await asyncio.sleep(60)
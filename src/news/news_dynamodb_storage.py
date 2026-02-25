#!/usr/bin/env python3
"""
DynamoDB Storage for Economic News Events

This module provides persistent storage for economic calendar events using AWS DynamoDB.
Events are saved with TTL for automatic cleanup after 2 weeks.
"""

import logging
import os
import hashlib
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone, timedelta
from decimal import Decimal

from boto3.dynamodb.conditions import Key, Attr
from botocore.exceptions import ClientError

import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from bot.dynamodb_base import DynamoDBBase

logger = logging.getLogger(__name__)


class NewsDynamoDBStorage(DynamoDBBase):
    """DynamoDB storage manager for economic news events"""
    
    def __init__(self, table_name: str = None, region_name: str = None):
        """
        Initialize DynamoDB storage for news events
        
        Args:
            table_name: DynamoDB table name (defaults to env var NEWS_TABLE_NAME)
            region_name: AWS region (defaults to env var AWS_REGION or us-east-1)
        """
        # Set table name
        table_name = table_name or os.getenv('NEWS_TABLE_NAME', 'economic-news-events')
        
        # Initialize base class
        super().__init__(table_name=table_name, region_name=region_name)
        
        # Create table if it doesn't exist
        self.create_table_if_not_exists()
    
    def create_table_if_not_exists(self):
        """Create DynamoDB table if it doesn't exist"""
        if not self.table_exists():
            logger.info(f"Creating DynamoDB table: {self.table_name}")
            
            # Create table with event_id as partition key and date as sort key
            return self.create_table(
                table_name=self.table_name,
                key_schema=[
                    {
                        'AttributeName': 'event_id',
                        'KeyType': 'HASH'  # Partition key
                    },
                    {
                        'AttributeName': 'event_date',
                        'KeyType': 'RANGE'  # Sort key
                    }
                ],
                attribute_definitions=[
                    {
                        'AttributeName': 'event_id',
                        'AttributeType': 'S'  # String type for event ID
                    },
                    {
                        'AttributeName': 'event_date',
                        'AttributeType': 'S'  # String type for ISO date
                    }
                ],
                ttl_attribute='ttl',  # Enable TTL for automatic cleanup
                billing_mode='PAY_PER_REQUEST'
            )
        else:
            logger.info(f"Table {self.table_name} already exists")
            # Ensure TTL is enabled
            self.enable_ttl(self.table_name, 'ttl')
            return True
    
    def _generate_event_id(self, event: Dict[str, Any]) -> str:
        """
        Generate unique event ID from event data
        
        Args:
            event: Event dictionary with title, country, and date
            
        Returns:
            Unique event ID hash
        """
        # Create unique identifier from title, country, and date
        unique_string = f"{event.get('title', '')}_{event.get('country', '')}_{event.get('date', '')}"
        return hashlib.md5(unique_string.encode()).hexdigest()
    
    def save_events(self, events: List[Dict[str, Any]]) -> Dict[str, int]:
        """
        Save multiple news events to DynamoDB
        
        Args:
            events: List of event dictionaries from the API
            
        Returns:
            Dictionary with saved and skipped counts
        """
        saved_count = 0
        skipped_count = 0
        error_count = 0
        
        for event in events:
            if self._save_single_event(event):
                saved_count += 1
            elif self._event_exists(event):
                skipped_count += 1
            else:
                error_count += 1
        
        logger.info(f"Events processed: {len(events)} total, {saved_count} saved, {skipped_count} skipped, {error_count} errors")
        
        return {
            'saved': saved_count,
            'skipped': skipped_count,
            'errors': error_count,
            'total': len(events)
        }
    
    def _save_single_event(self, event: Dict[str, Any]) -> bool:
        """Save a single event to DynamoDB"""
        try:
            event_id = self._generate_event_id(event)
            event_date = event.get('date', '')
            ttl_timestamp = int((datetime.now(timezone.utc) + timedelta(weeks=2)).timestamp())
            
            item = {
                'event_id': event_id,
                'event_date': event_date,
                'title': event.get('title', ''),
                'country': event.get('country', ''),
                'impact': event.get('impact', 'Low'),
                'forecast': event.get('forecast', ''),
                'previous': event.get('previous', ''),
                'fetched_at': datetime.now(timezone.utc).isoformat(),
                'notified': False,
                'urgent_notified': False,
                'ttl': ttl_timestamp
            }
            
            return self.put_item(item)
            
        except Exception as e:
            logger.error(f"Failed to save event {event.get('title', '')}: {e}")
            return False
    
    def _event_exists(self, event: Dict[str, Any]) -> bool:
        """Check if an event already exists"""
        try:
            event_id = self._generate_event_id(event)
            event_date = event.get('date', '')
            existing = self.get_item({'event_id': event_id, 'event_date': event_date})
            return existing is not None
        except:
            return False
    
    def get_today_events(self, impact_filter: Optional[List[str]] = None, 
                        currency_filter: Optional[List[str]] = None,
                        selective_filtering: bool = False) -> List[Dict[str, Any]]:
        """
        Get today's events, optionally filtered by impact level and currency
        
        Args:
            impact_filter: List of impact levels to include (e.g., ['High', 'Medium'])
            currency_filter: List of currencies to include (e.g., ['USD', 'EUR'])
            selective_filtering: If True, apply USD=High+Medium, Others=High only filtering
            
        Returns:
            List of today's events
        """
        today = datetime.now(timezone.utc).date()
        return self.get_events_for_date(today, impact_filter, currency_filter, selective_filtering)
    
    def get_today_events_selective(self, currency_filter: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """Get today's events with selective filtering (backward compatibility)"""
        return self.get_today_events(selective_filtering=True, currency_filter=currency_filter)
    
    def get_events_for_date(self, target_date, impact_filter: Optional[List[str]] = None,
                           currency_filter: Optional[List[str]] = None, 
                           selective_filtering: bool = False) -> List[Dict[str, Any]]:
        """
        Get events for a specific date, optionally filtered by impact level and currency
        
        Args:
            target_date: Date to get events for (datetime.date object)
            impact_filter: List of impact levels to include (e.g., ['High', 'Medium'])
            currency_filter: List of currencies to include (e.g., ['USD', 'EUR'])
            selective_filtering: If True, apply USD=High+Medium, Others=High only filtering
            
        Returns:
            List of events for the specified date
        """
        try:
            # Convert target_date to string for comparison
            target_date_str = target_date.isoformat() if hasattr(target_date, 'isoformat') else str(target_date)

            logger.debug(f"get_events_for_date: date={target_date_str}, selective={selective_filtering}, currency_filter={currency_filter}")

            # Scan all items (since we don't have GSI on date alone)
            all_items = self.scan_with_filter()
            
            # Filter events for the target date
            events = []
            matched_events = 0
            total_events = len(all_items)
            
            logger.debug(f"Searching for events on {target_date_str} among {total_events} total events")
            
            for item in all_items:
                event_date_str = item.get('event_date', '')
                if not event_date_str:
                    continue
                
                # Extract date part using simple string parsing (same as get_detailed_statistics)
                try:
                    if 'T' in event_date_str:
                        date_part = event_date_str.split('T')[0]  # Extract YYYY-MM-DD
                    else:
                        date_part = event_date_str.split(' ')[0] if ' ' in event_date_str else event_date_str
                    
                    # Compare date strings directly
                    if date_part != target_date_str:
                        continue
                        
                    matched_events += 1
                    logger.debug(f"Matched event: {item.get('title', 'Unknown')} on {date_part}")
                    
                except (ValueError, AttributeError) as e:
                    logger.debug(f"Could not parse date {event_date_str}: {e}")
                    continue
                
                # Apply filtering
                if selective_filtering:
                    # Apply selective impact filtering: USD=High+Medium, Others=High only
                    currency = item.get('country', '').upper()
                    impact = item.get('impact', 'Low')

                    should_include = False
                    if currency == 'USD' and impact in ['High', 'Medium']:
                        should_include = True
                    elif currency != 'USD' and impact == 'High':
                        should_include = True

                    if not should_include:
                        logger.debug(f"Filtered out by impact: {item.get('title')} (currency={currency}, impact={impact})")
                        continue

                    # Apply currency filter if specified
                    if currency_filter and currency not in currency_filter:
                        logger.debug(f"Filtered out by currency: {item.get('title')} (currency={currency}, filter={currency_filter})")
                        continue
                else:
                    # Apply standard impact filter
                    if impact_filter and item.get('impact') not in impact_filter:
                        continue
                    
                    # Apply currency filter
                    if currency_filter and item.get('country') not in currency_filter:
                        continue
                
                # Convert Decimal types
                item = self.convert_decimal_to_number(item)
                events.append(item)
            
            # Sort by event date/time
            events.sort(key=lambda x: x.get('event_date', ''))
            
            logger.info(f"Found {len(events)} events for {target_date_str} (matched {matched_events} by date, filtered to {len(events)})")
            
            # Log filter details if events were filtered out
            if matched_events > len(events):
                logger.debug(f"Applied filters - Impact: {impact_filter}, Currency: {currency_filter}")
            
            return events
            
        except Exception as e:
            logger.error(f"Failed to get events for date {target_date}: {e}")
            return []
    
    def get_events_in_range(self, start_date, end_date) -> List[Dict[str, Any]]:
        """
        Get all events within a date range
        
        Args:
            start_date: Start date (datetime.date object)
            end_date: End date (datetime.date object)
            
        Returns:
            List of events in the date range
        """
        try:
            # Get all events
            all_events = self.scan_with_filter()
            
            # Convert dates to strings for comparison
            start_str = start_date.isoformat() if hasattr(start_date, 'isoformat') else str(start_date)
            end_str = end_date.isoformat() if hasattr(end_date, 'isoformat') else str(end_date)
            
            # Filter events by date range
            events_in_range = []
            for event in all_events:
                event_date_str = event.get('event_date', '')
                if not event_date_str:
                    continue
                
                # Extract date part
                try:
                    if 'T' in event_date_str:
                        date_part = event_date_str.split('T')[0]
                    else:
                        date_part = event_date_str.split(' ')[0] if ' ' in event_date_str else event_date_str
                    
                    # Check if date is in range
                    if start_str <= date_part <= end_str:
                        events_in_range.append(event)
                        
                except Exception as e:
                    logger.debug(f"Could not parse date {event_date_str}: {e}")
                    continue
            
            logger.debug(f"Found {len(events_in_range)} events between {start_str} and {end_str}")
            return events_in_range
            
        except Exception as e:
            logger.error(f"Failed to get events in range: {e}")
            return []
    
    def get_upcoming_events(self, hours: int = 24, impact_filter: Optional[List[str]] = None, 
                           currency_filter: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """
        Get upcoming events within specified hours
        
        Args:
            hours: Number of hours to look ahead
            impact_filter: List of impact levels to include
            currency_filter: List of currencies to include
            
        Returns:
            List of upcoming events
        """
        now = datetime.now(timezone.utc)
        future = now + timedelta(hours=hours)
        
        now_str = now.isoformat()
        future_str = future.isoformat()
        
        try:
            # Scan table for upcoming events
            filter_expression = Attr('event_date').between(now_str, future_str)
            
            # Add impact filter if specified
            if impact_filter:
                impact_conditions = None
                for impact in impact_filter:
                    condition = Attr('impact').eq(impact)
                    impact_conditions = condition if impact_conditions is None else impact_conditions | condition
                
                if impact_conditions:
                    filter_expression = filter_expression & impact_conditions
            
            # Add currency filter if specified
            if currency_filter:
                currency_conditions = None
                for currency in currency_filter:
                    condition = Attr('country').eq(currency)
                    currency_conditions = condition if currency_conditions is None else currency_conditions | condition
                
                if currency_conditions:
                    filter_expression = filter_expression & currency_conditions
            
            # Add filter to exclude already notified events
            filter_expression = filter_expression & Attr('notified').eq(False)
            
            # Scan with filter
            items = self.scan_with_filter(filter_expression=filter_expression)
            
            # Convert and sort
            events = []
            for item in items:
                item = self.convert_decimal_to_number(item)
                events.append(item)
            
            events.sort(key=lambda x: x.get('event_date', ''))
            
            logger.info(f"Found {len(events)} upcoming events in next {hours} hours")
            return events
            
        except Exception as e:
            logger.error(f"Failed to get upcoming events: {e}")
            return []
    
    def get_upcoming_events_selective(self, hours: int = 24, currency_filter: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """
        Get upcoming events with selective impact filtering: Medium+ for USD, High only for others
        
        Args:
            hours: Number of hours to look ahead
            currency_filter: Optional list of currencies to include
            
        Returns:
            List of upcoming events with selective filtering
        """
        try:
            # Get all upcoming events without impact filtering
            all_upcoming = self.get_upcoming_events(hours=hours, impact_filter=None, currency_filter=currency_filter)
            
            filtered_events = []
            usd_count = 0
            other_count = 0
            
            for event in all_upcoming:
                currency = event.get('country', '').upper()
                impact = event.get('impact', 'Low')
                
                # Apply selective filtering
                should_include = False
                
                if currency == 'USD':
                    # For USD: include High and Medium impact
                    if impact in ['High', 'Medium']:
                        should_include = True
                        usd_count += 1
                else:
                    # For other currencies: include High impact only
                    if impact == 'High':
                        should_include = True
                        other_count += 1
                
                if should_include:
                    filtered_events.append(event)
            
            logger.info(f"Selective filtering for upcoming {hours}h: {len(filtered_events)} events "
                       f"(USD H+M: {usd_count}, Others H: {other_count})")
            
            return filtered_events
            
        except Exception as e:
            logger.error(f"Failed to get upcoming events with selective impact filter: {e}")
            return []
    
    def mark_as_notified(self, event_id: str, event_date: str) -> bool:
        """
        Mark an event as notified
        
        Args:
            event_id: Event ID
            event_date: Event date (sort key)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            return self.update_item(
                key={
                    'event_id': event_id,
                    'event_date': event_date
                },
                update_expression="SET notified = :true, notified_at = :now",
                expression_values={
                    ':true': True,
                    ':now': datetime.now(timezone.utc).isoformat()
                }
            )
        except Exception as e:
            logger.error(f"Failed to mark event {event_id} as notified: {e}")
            return False

    def mark_multiple_as_notified(self, events: List[Dict[str, Any]]) -> int:
        """
        Mark multiple events as notified
        
        Args:
            events: List of event dictionaries with event_id and event_date
            
        Returns:
            Number of successfully marked events
        """
        success_count = 0
        
        for event in events:
            if self.mark_as_notified(event['event_id'], event['event_date']):
                success_count += 1
        
        logger.info(f"Marked {success_count}/{len(events)} events as notified")
        return success_count
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about stored news events
        
        Returns:
            Dictionary with statistics
        """
        try:
            all_events = self.scan_with_filter()
            
            if not all_events:
                logger.info("No events found in database")
                return {
                    'total_events': 0,
                    'date_range': 'No events',
                    'high_impact': 0,
                    'medium_impact': 0,
                    'low_impact': 0,
                    'notified': 0,
                    'pending_notification': 0
                }
            
            # Impact level counts
            high_impact = sum(1 for e in all_events if e.get('impact') == 'High')
            medium_impact = sum(1 for e in all_events if e.get('impact') == 'Medium')
            low_impact = sum(1 for e in all_events if e.get('impact') == 'Low')
            holidays = sum(1 for e in all_events if e.get('impact') == 'Holiday')
            
            # Notification counts
            notified = sum(1 for e in all_events if e.get('notified', False))
            urgent_notified = sum(1 for e in all_events if e.get('urgent_notified', False))
            
            # Date range analysis
            event_dates = []
            for event in all_events:
                try:
                    date_str = event.get('event_date', '')
                    if date_str:
                        event_dates.append(date_str)
                except:
                    continue
            
            earliest_date = min(event_dates) if event_dates else 'Unknown'
            latest_date = max(event_dates) if event_dates else 'Unknown'
            
            # Currency/Country breakdown
            currencies = {}
            for event in all_events:
                country = event.get('country', 'Unknown')
                currencies[country] = currencies.get(country, 0) + 1
            
            # Sort currencies by count
            sorted_currencies = sorted(currencies.items(), key=lambda x: x[1], reverse=True)
            top_currencies = dict(sorted_currencies[:5])  # Top 5 currencies
            
            stats = {
                'total_events': len(all_events),
                'date_range': f"{earliest_date[:10]} to {latest_date[:10]}" if earliest_date != 'Unknown' else 'No events',
                'high_impact': high_impact,
                'medium_impact': medium_impact,
                'low_impact': low_impact,
                'holidays': holidays,
                'notified': notified,
                'urgent_notified': urgent_notified,
                'pending_notification': len(all_events) - notified,
                'currencies': top_currencies,
                'total_currencies': len(currencies)
            }
            
            # Log the statistics
            logger.info(f"📊 Database Statistics:")
            logger.info(f"  Total Events: {stats['total_events']}")
            logger.info(f"  Date Range: {stats['date_range']}")
            logger.info(f"  Impact Levels: High={high_impact}, Medium={medium_impact}, Low={low_impact}, Holidays={holidays}")
            logger.info(f"  Notifications: Sent={notified}, Urgent={urgent_notified}, Pending={stats['pending_notification']}")
            logger.info(f"  Top Currencies: {', '.join([f'{c}({n})' for c, n in top_currencies.items()])}")
            
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get statistics: {e}")
            return {}
    
    
    def has_current_week_events(self) -> Dict[str, Any]:
        """
        Check if we have events for the current week (Monday to Sunday)
        
        Returns:
            Dictionary with week info and event counts
        """
        try:
            now = datetime.now(timezone.utc)
            
            # Calculate current week's Monday (start) and Sunday (end)
            days_since_monday = now.weekday()  # Monday = 0, Sunday = 6
            monday = (now - timedelta(days=days_since_monday)).replace(
                hour=0, minute=0, second=0, microsecond=0
            )
            sunday = monday + timedelta(days=6, hours=23, minutes=59, seconds=59)
            
            # Get all events in database
            all_events = self.scan_with_filter()
            
            # Filter events for current week
            week_events = []
            for event in all_events:
                event_date_str = event.get('event_date', '')
                if not event_date_str:
                    continue
                
                try:
                    # Parse event date
                    if 'T' in event_date_str:
                        if event_date_str.endswith('Z'):
                            event_dt = datetime.fromisoformat(event_date_str.replace('Z', '+00:00'))
                        else:
                            event_dt = datetime.fromisoformat(event_date_str)
                        
                        # Convert to UTC
                        if event_dt.tzinfo is None:
                            event_dt = event_dt.replace(tzinfo=timezone.utc)
                        else:
                            event_dt = event_dt.astimezone(timezone.utc)
                        
                        # Check if in current week
                        if monday <= event_dt <= sunday:
                            week_events.append(event)
                except Exception as e:
                    logger.debug(f"Could not parse date {event_date_str}: {e}")
                    continue
            
            # Get latest fetched_at timestamp from week events
            latest_fetch = None
            for event in week_events:
                fetched_at = event.get('fetched_at')
                if fetched_at:
                    if latest_fetch is None or fetched_at > latest_fetch:
                        latest_fetch = fetched_at
            
            result = {
                'week_start': monday.isoformat(),
                'week_end': sunday.isoformat(),
                'has_events': len(week_events) > 0,
                'event_count': len(week_events),
                'high_impact_count': sum(1 for e in week_events if e.get('impact') == 'High'),
                'latest_fetch': latest_fetch,
                'current_day': now.strftime('%A'),
                'is_past_fetch_day': now.weekday() >= 6  # Sunday or later
            }
            
            logger.info(f"Current week check: {result['event_count']} events found, "
                       f"latest fetch: {latest_fetch or 'Never'}")
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to check current week events: {e}")
            return {
                'has_events': False,
                'event_count': 0,
                'error': str(e)
            }
    
    def get_holidays(self, start_date=None, end_date=None, 
                     currency_filter: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """
        Get bank holidays within a date range
        
        Args:
            start_date: Start date (defaults to today)
            end_date: End date (defaults to 1 week from start)
            currency_filter: List of currencies to include
            
        Returns:
            List of holiday events
        """
        try:
            if start_date is None:
                start_date = datetime.now(timezone.utc).date()
            if end_date is None:
                end_date = start_date + timedelta(days=7)
            
            # Get all events in the date range
            all_events = self.get_events_in_range(start_date, end_date)
            
            # Filter for holidays
            holidays = [e for e in all_events if e.get('impact') == 'Holiday']
            
            # Apply currency filter
            if currency_filter:
                holidays = [e for e in holidays if e.get('country') in currency_filter]
            
            logger.info(f"Found {len(holidays)} bank holidays between {start_date} and {end_date}")
            return holidays
            
        except Exception as e:
            logger.error(f"Failed to get holidays: {e}")
            return []

    def cleanup_old_events(self, days: int = 14) -> int:
        """
        Manually cleanup events older than specified days
        (Backup to TTL in case it's not working)
        
        Args:
            days: Number of days to keep events
            
        Returns:
            Number of deleted events
        """
        cutoff_date = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
        
        try:
            # Find old events
            filter_expression = Attr('event_date').lt(cutoff_date)
            old_events = self.scan_with_filter(filter_expression=filter_expression)
            
            deleted_count = 0
            for event in old_events:
                if self.delete_item({
                    'event_id': event['event_id'],
                    'event_date': event['event_date']
                }):
                    deleted_count += 1
            
            logger.info(f"Cleaned up {deleted_count} old events")
            return deleted_count
            
        except Exception as e:
            logger.error(f"Failed to cleanup old events: {e}")
            return 0
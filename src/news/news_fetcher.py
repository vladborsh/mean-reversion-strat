#!/usr/bin/env python3
"""
Economic Calendar News Fetcher

This module fetches economic calendar events from the FairEconomy API
and saves them to DynamoDB for later notification.
"""

import logging
import os
import json
import requests
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

from .news_dynamodb_storage import NewsDynamoDBStorage

logger = logging.getLogger(__name__)


class NewsFetcher:
    """Fetches and processes economic calendar events"""
    
    def __init__(self, storage: Optional[NewsDynamoDBStorage] = None):
        """
        Initialize the news fetcher
        
        Args:
            storage: Optional DynamoDB storage instance
        """
        self.api_url = os.getenv('NEWS_FETCH_URL', 'https://nfs.faireconomy.media/ff_calendar_thisweek.json')
        self.storage = storage or NewsDynamoDBStorage()
        
        # Setup requests session with retry logic
        self.session = requests.Session()
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        
        logger.info(f"News fetcher initialized with URL: {self.api_url}")
    
    def fetch_weekly_news(self) -> Optional[List[Dict[str, Any]]]:
        """
        Fetch weekly economic calendar events from the API
        
        Returns:
            List of event dictionaries or None if failed
        """
        try:
            logger.info(f"Fetching weekly news from {self.api_url}")
            
            # Make request with timeout
            response = self.session.get(self.api_url, timeout=30)
            response.raise_for_status()
            
            # Parse JSON response
            events = response.json()
            
            if not isinstance(events, list):
                logger.error(f"Unexpected response format: expected list, got {type(events)}")
                return None
            
            logger.info(f"Successfully fetched {len(events)} events")
            
            # Validate and clean events
            valid_events = []
            for event in events:
                if self._validate_event(event):
                    valid_events.append(self._clean_event(event))
                else:
                    logger.warning(f"Skipping invalid event: {event}")
            
            logger.info(f"Validated {len(valid_events)} events out of {len(events)}")
            return valid_events
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed: {e}")
            return None
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error fetching news: {e}")
            return None
    
    def _validate_event(self, event: Dict[str, Any]) -> bool:
        """
        Validate that an event has required fields
        
        Args:
            event: Event dictionary to validate
            
        Returns:
            True if valid, False otherwise
        """
        required_fields = ['title', 'country', 'date', 'impact']
        
        for field in required_fields:
            if field not in event or event[field] is None:
                logger.debug(f"Event missing required field '{field}': {event}")
                return False
        
        # Validate date format
        try:
            datetime.fromisoformat(event['date'].replace('Z', '+00:00'))
        except (ValueError, AttributeError) as e:
            logger.debug(f"Invalid date format in event: {event.get('date')} - {e}")
            return False
        
        # Validate impact level
        valid_impacts = ['Low', 'Medium', 'High', 'Holiday']
        if event['impact'] not in valid_impacts:
            logger.debug(f"Invalid impact level: {event['impact']}")
            return False
        
        return True
    
    def _clean_event(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """
        Clean and normalize event data
        
        Args:
            event: Raw event dictionary
            
        Returns:
            Cleaned event dictionary
        """
        cleaned = {
            'title': str(event.get('title', '')).strip(),
            'country': str(event.get('country', '')).strip().upper(),
            'date': event.get('date', ''),
            'impact': event.get('impact', 'Low'),
            'forecast': str(event.get('forecast', '')).strip(),
            'previous': str(event.get('previous', '')).strip()
        }
        
        # Normalize date to ISO format with timezone
        try:
            # Handle various date formats
            date_str = cleaned['date']
            if 'T' in date_str:
                # Already in ISO-like format
                # Keep the original timezone information (e.g., -04:00 for EDT)
                # Just ensure it's properly formatted
                if 'Z' in date_str:
                    cleaned['date'] = date_str.replace('Z', '+00:00')
                elif not ('+' in date_str[-6:] or '-' in date_str[-6:]):
                    # No timezone, assume UTC
                    cleaned['date'] = date_str + '+00:00'
                else:
                    # Already has timezone, keep as is
                    cleaned['date'] = date_str
            else:
                # Basic date, add time and timezone
                cleaned['date'] = date_str + 'T00:00:00+00:00'
        except Exception as e:
            logger.warning(f"Could not normalize date {cleaned['date']}: {e}")
        
        return cleaned
    
    def fetch_and_save(self) -> Dict[str, int]:
        """
        Fetch weekly news and save to DynamoDB
        
        Returns:
            Dictionary with save statistics
        """
        logger.info("Starting news fetch and save")
        
        # Fetch news
        events = self.fetch_weekly_news()
        
        if not events:
            logger.warning("No events fetched from API")
            return {'saved': 0, 'skipped': 0, 'errors': 0, 'total': 0}
        
        logger.info(f"Fetched {len(events)} events from API")
        
        # Save to DynamoDB
        result = self.storage.save_events(events)
        
        logger.info("News fetch and save complete")
        
        return result
    
    def filter_by_impact(self, events: List[Dict[str, Any]], 
                        impact_levels: List[str]) -> List[Dict[str, Any]]:
        """
        Filter events by impact level
        
        Args:
            events: List of events
            impact_levels: List of impact levels to include (e.g., ['High', 'Medium'])
            
        Returns:
            Filtered list of events
        """
        filtered = [
            event for event in events 
            if event.get('impact') in impact_levels
        ]
        
        logger.info(f"Filtered {len(events)} events to {len(filtered)} with impact levels: {impact_levels}")
        return filtered
    
    def filter_by_currency(self, events: List[Dict[str, Any]], 
                          currencies: List[str]) -> List[Dict[str, Any]]:
        """
        Filter events by currency/country code
        
        Args:
            events: List of events
            currencies: List of currency codes to include (e.g., ['USD', 'EUR'])
            
        Returns:
            Filtered list of events
        """
        filtered = [
            event for event in events 
            if event.get('country') in currencies
        ]
        
        logger.info(f"Filtered {len(events)} events to {len(filtered)} for currencies: {currencies}")
        return filtered
    
    def get_test_events(self) -> List[Dict[str, Any]]:
        """
        Get sample test events for development/testing
        
        Returns:
            List of test event dictionaries
        """
        from datetime import timedelta
        now = datetime.now(timezone.utc)
        
        test_events = [
            {
                'title': 'Test: High Impact Event',
                'country': 'USD',
                'date': (now + timedelta(hours=2)).isoformat(),
                'impact': 'High',
                'forecast': '50.5',
                'previous': '49.8'
            },
            {
                'title': 'Test: Medium Impact Event',
                'country': 'EUR',
                'date': (now + timedelta(hours=4)).isoformat(),
                'impact': 'Medium',
                'forecast': '2.1%',
                'previous': '2.0%'
            },
            {
                'title': 'Test: Low Impact Event',
                'country': 'GBP',
                'date': (now + timedelta(hours=6)).isoformat(),
                'impact': 'Low',
                'forecast': '100K',
                'previous': '95K'
            }
        ]
        
        logger.info(f"Generated {len(test_events)} test events")
        return test_events
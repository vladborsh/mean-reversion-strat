#!/usr/bin/env python3
"""
News Configuration Handler

Centralizes all news scheduler configuration and environment variable handling.
"""

import os
import logging
from typing import List, Dict, Any, Tuple

logger = logging.getLogger(__name__)


class NewsConfig:
    """Centralized configuration for news scheduler"""
    
    def __init__(self, symbols_config: Dict[str, Any] = None):
        """
        Initialize news configuration
        
        Args:
            symbols_config: Optional trading symbols configuration
        """
        # Fetch schedule configuration
        self.fetch_day = os.getenv('NEWS_FETCH_DAY', 'Sunday')
        self.fetch_time = os.getenv('NEWS_FETCH_TIME', '00:00')
        self.notification_time = os.getenv('NEWS_NOTIFICATION_TIME', '08:00')
        
        # Filter configuration
        self.impact_filter = os.getenv('NEWS_IMPACT_FILTER', 'High,Medium').split(',')
        
        # Alert configuration
        self.urgent_alert_enabled = os.getenv('NEWS_URGENT_ALERT_ENABLED', 'true').lower() == 'true'
        self.urgent_alert_minutes = int(os.getenv('NEWS_URGENT_ALERT_MINUTES', '5'))
        
        # Parse times
        self.fetch_hour, self.fetch_minute = self._parse_time(self.fetch_time)
        self.notify_hour, self.notify_minute = self._parse_time(self.notification_time)
        
        # Extract relevant currencies
        self.relevant_currencies = self._extract_currencies_from_symbols(symbols_config or {})
        
        logger.info(f"News config: {self.fetch_day} {self.fetch_time} UTC, notifications {self.notification_time} UTC")
        logger.info(f"Filters: {', '.join(self.impact_filter)}, Currencies: {len(self.relevant_currencies)}")
    
    def _parse_time(self, time_str: str) -> Tuple[int, int]:
        """Parse time string to hour and minute"""
        try:
            parts = time_str.split(':')
            return int(parts[0]), int(parts[1])
        except:
            logger.warning(f"Invalid time format: {time_str}, using 00:00")
            return 0, 0
    
    def _extract_currencies_from_symbols(self, symbols_config: Dict[str, Any]) -> List[str]:
        """Extract relevant currencies from trading symbols configuration"""
        currencies = set()
        
        for _, config in symbols_config.items():
            symbol = config.get('symbol', '')
            clean_symbol = symbol.replace('X', '') if symbol.endswith('X') else symbol
            
            # Extract currencies from forex pairs
            if len(clean_symbol) in [6, 7, 8]:
                if len(clean_symbol) >= 6:
                    currencies.add(clean_symbol[:3].upper())
                    currencies.add(clean_symbol[3:6].upper())
            # Handle commodities
            elif clean_symbol in ['GOLD', 'SILVER', 'BTC', 'ETH']:
                currencies.add('USD')
        
        # Add major currencies
        major_currencies = {'USD', 'EUR', 'GBP', 'JPY', 'AUD', 'NZD', 'CHF', 'CAD'}
        relevant = currencies.intersection(major_currencies) if currencies else major_currencies
        
        return sorted(list(relevant))
#!/usr/bin/env python3
"""
News Configuration Handler

Centralizes all news scheduler configuration from bot_config.json.
Infrastructure settings (API URLs, table names) remain in .env.
"""

import os
import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)


class NewsConfig:
    """Centralized configuration for news scheduler"""

    def __init__(self, symbols_config: Dict[str, Any] = None, bot_config: Dict[str, Any] = None):
        """
        Initialize news configuration

        Args:
            symbols_config: Optional trading symbols configuration
            bot_config: News configuration from bot_config.json
        """
        bot_config = bot_config or {}

        # Filter configuration from bot_config
        self.impact_filter = bot_config.get('impact_filter', ['High', 'Medium', 'Holiday'])

        # Extract relevant currencies from trading symbols
        self.relevant_currencies = self._extract_currencies_from_symbols(symbols_config or {})

        logger.info(f"News config initialized from bot_config.json")
        logger.info(f"Impact filters: {', '.join(self.impact_filter)}")
        logger.info(f"Relevant currencies: {self.relevant_currencies}")
    
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
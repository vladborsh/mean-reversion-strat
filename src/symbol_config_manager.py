#!/usr/bin/env python3
"""
Symbol Configuration Manager

This module provides utilities for loading and managing symbol configurations
for the live trading strategy scheduler. It handles symbol format conversions
and configuration parsing.
"""

import json
import sys
import logging
from typing import Dict, Any

# Configure logging for this module
logger = logging.getLogger(__name__)


class SymbolConfigManager:
    """Manager class for symbol configurations and format conversions"""
    
    @staticmethod
    def convert_symbol_for_fetching(symbol: str) -> str:
        """
        Convert symbol from config format to data fetching format
        
        Args:
            symbol: Symbol from config (e.g., 'AUDUSDX', 'GOLDX', 'SILVERX')
            
        Returns:
            Symbol for data fetching (e.g., 'AUDUSD=X', 'GOLD=X', 'SILVER=X')
        """
        # Special mappings for commodities
        special_mappings = {
            'GOLDX': 'GOLD=X',
            'SILVERX': 'SILVER=X',
            'BTCUSDX': 'BTC=X',
            'ETHUSDX': 'ETH=X'
        }
        
        if symbol in special_mappings:
            return special_mappings[symbol]
        
        # Standard forex conversion (AUDUSDX -> AUDUSD=X)
        if symbol.endswith('X') and len(symbol) == 7:
            return symbol[:-1] + '=X'
        
        # Return as-is if no conversion needed
        return symbol
    
    @staticmethod
    def load_symbol_configs(config_file_path: str) -> Dict[str, Dict[str, Any]]:
        """
        Load optimized configurations for all symbols
        
        Args:
            config_file_path: Path to the configuration file
            
        Returns:
            Dictionary containing symbol configurations
            
        Raises:
            FileNotFoundError: If configuration file is not found
            Exception: For other configuration loading errors
        """
        try:
            with open(config_file_path, 'r') as f:
                configs = json.load(f)
            
            symbols_config = {}
            for symbol_key, config in configs.items():
                # Extract symbol info
                asset_info = config['ASSET_INFO']
                symbol = asset_info['symbol']
                timeframe = asset_info['timeframe']
                
                # Convert symbol format for data fetching with special handling
                fetch_symbol = SymbolConfigManager.convert_symbol_for_fetching(symbol)
                
                symbols_config[symbol_key] = {
                    'symbol': symbol,
                    'fetch_symbol': fetch_symbol,
                    'timeframe': timeframe,
                    'config': config
                }
                
                logger.debug(f"   ✓ {symbol} ({timeframe}) - {fetch_symbol}")
            
            logger.info(f"✅ Loaded configurations for {len(symbols_config)} symbols")
            return symbols_config
            
        except FileNotFoundError:
            logger.error(f"❌ Configuration file not found: {config_file_path}")
            raise
        except Exception as e:
            logger.error(f"❌ Error loading configurations: {e}")
            raise


def load_symbol_configs(config_file_path: str) -> Dict[str, Dict[str, Any]]:
    """
    Convenience function to load symbol configurations
    
    Args:
        config_file_path: Path to the configuration file
        
    Returns:
        Dictionary containing symbol configurations
    """
    return SymbolConfigManager.load_symbol_configs(config_file_path)


def convert_symbol_for_fetching(symbol: str) -> str:
    """
    Convenience function to convert symbol format for data fetching
    
    Args:
        symbol: Symbol from config (e.g., 'AUDUSDX', 'GOLDX', 'SILVERX')
        
    Returns:
        Symbol for data fetching (e.g., 'AUDUSD=X', 'GOLD=X', 'SILVER=X')
    """
    return SymbolConfigManager.convert_symbol_for_fetching(symbol)

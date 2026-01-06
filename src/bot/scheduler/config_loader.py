#!/usr/bin/env python3
"""
Bot Configuration Loader

Loads and validates the master bot_config.json configuration file.
"""

import json
import os
import logging
from typing import Dict, Any, Optional
from pathlib import Path

logger = logging.getLogger(__name__)


class BotConfigLoader:
    """Loads and validates bot configuration"""
    
    def __init__(self, config_path: str = None):
        """
        Initialize config loader
        
        Args:
            config_path: Path to bot_config.json (defaults to project root)
        """
        if config_path is None:
            # Default to bot_config.json in project root
            project_root = Path(__file__).parent.parent.parent.parent
            config_path = project_root / 'bot_config.json'
        
        self.config_path = Path(config_path)
        self.config: Dict[str, Any] = {}
        self._load_config()
        self._validate_config()
    
    def _load_config(self):
        """Load configuration from JSON file"""
        try:
            with open(self.config_path, 'r') as f:
                self.config = json.load(f)
            logger.info(f"✅ Loaded bot configuration from {self.config_path}")
        except FileNotFoundError:
            raise FileNotFoundError(f"Configuration file not found: {self.config_path}")
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in configuration file: {e}")
    
    def _validate_config(self):
        """Validate required configuration fields"""
        required_sections = ['bot', 'trading_hours', 'strategies', 'execution', 'telegram', 'signal_cache']
        
        for section in required_sections:
            if section not in self.config:
                raise ValueError(f"Missing required configuration section: {section}")
        
        # Validate strategies section
        if not self.config['strategies']:
            raise ValueError("No strategies configured")
        
        for strategy_name, strategy_config in self.config['strategies'].items():
            if 'enabled' not in strategy_config:
                raise ValueError(f"Strategy {strategy_name} missing 'enabled' field")
            if 'config_file' not in strategy_config:
                raise ValueError(f"Strategy {strategy_name} missing 'config_file' field")
            if 'executor_class' not in strategy_config:
                raise ValueError(f"Strategy {strategy_name} missing 'executor_class' field")
        
        logger.info("✅ Configuration validation passed")
    
    def get_bot_config(self) -> Dict[str, Any]:
        """Get bot configuration section"""
        return self.config.get('bot', {})
    
    def get_trading_hours(self) -> Dict[str, int]:
        """Get trading hours configuration"""
        return self.config.get('trading_hours', {})
    
    def get_strategies_config(self) -> Dict[str, Any]:
        """Get all strategies configuration"""
        return self.config.get('strategies', {})
    
    def get_enabled_strategies(self) -> Dict[str, Any]:
        """Get only enabled strategies"""
        strategies = self.config.get('strategies', {})
        return {
            name: config 
            for name, config in strategies.items() 
            if config.get('enabled', False)
        }
    
    def is_strategy_enabled(self, strategy_name: str) -> bool:
        """Check if a specific strategy is enabled"""
        strategies = self.config.get('strategies', {})
        if strategy_name not in strategies:
            return False
        return strategies[strategy_name].get('enabled', False)
    
    def get_strategy_config_file(self, strategy_name: str) -> Optional[str]:
        """Get config file path for a strategy"""
        strategies = self.config.get('strategies', {})
        if strategy_name not in strategies:
            return None
        return strategies[strategy_name].get('config_file')
    
    def get_strategy_emoji(self, strategy_name: str) -> str:
        """Get emoji for a strategy (for Telegram notifications)"""
        strategies = self.config.get('strategies', {})
        if strategy_name not in strategies:
            return "🤖"
        return strategies[strategy_name].get('emoji', '🤖')
    
    def get_execution_config(self) -> Dict[str, Any]:
        """Get execution configuration"""
        return self.config.get('execution', {})
    
    def get_telegram_config(self) -> Dict[str, Any]:
        """Get Telegram configuration"""
        return self.config.get('telegram', {})
    
    def get_signal_cache_config(self) -> Dict[str, Any]:
        """Get signal cache configuration"""
        return self.config.get('signal_cache', {})
    
    def get_logging_config(self) -> Dict[str, Any]:
        """Get logging configuration"""
        return self.config.get('logging', {})
    
    def should_continue_on_failure(self) -> bool:
        """Check if bot should continue on strategy failure"""
        execution = self.config.get('execution', {})
        return execution.get('continue_on_failure', True)
    
    def get_run_interval_minutes(self) -> int:
        """Get run interval in minutes"""
        bot_config = self.config.get('bot', {})
        return bot_config.get('run_interval_minutes', 5)
    
    def get_sync_second(self) -> int:
        """Get second within minute to sync execution"""
        bot_config = self.config.get('bot', {})
        return bot_config.get('sync_second', 15)
    
    def is_telegram_enabled(self) -> bool:
        """Check if Telegram notifications are enabled"""
        telegram = self.config.get('telegram', {})
        return telegram.get('enabled', True)
    
    def should_use_dynamodb(self) -> bool:
        """Check if DynamoDB persistence should be used"""
        telegram = self.config.get('telegram', {})
        return telegram.get('use_dynamodb', True)
    
    def should_differentiate_strategies(self) -> bool:
        """Check if strategies should be differentiated in Telegram"""
        telegram = self.config.get('telegram', {})
        return telegram.get('differentiate_strategies', True)
    
    def get_telemetry_config(self) -> Dict[str, Any]:
        """Get telemetry configuration"""
        return self.config.get('telemetry', {})
    
    def is_telemetry_enabled(self) -> bool:
        """Check if telemetry collection is enabled"""
        telemetry = self.config.get('telemetry', {})
        return telemetry.get('enabled', True)
    
    def get_telemetry_persistence_path(self) -> Optional[str]:
        """Get telemetry persistence path"""
        telemetry = self.config.get('telemetry', {})
        persistence = telemetry.get('persistence', {})
        if persistence.get('enabled', False):
            return persistence.get('output_path', 'telemetry_data/')
        return None
    
    def get_tui_monitor_config(self) -> Dict[str, Any]:
        """Get TUI monitor configuration"""
        return self.config.get('tui_monitor', {})


def create_config_loader(config_path: str = None) -> BotConfigLoader:
    """
    Factory function to create a config loader
    
    Args:
        config_path: Path to bot_config.json
        
    Returns:
        BotConfigLoader instance
    """
    return BotConfigLoader(config_path)

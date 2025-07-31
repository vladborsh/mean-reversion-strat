#!/usr/bin/env python3
"""
Telegram Message Template Management

This module provides templates for various types of trading signal notifications
and other bot messages. It includes formatting utilities and predefined templates
for consistent messaging across the trading bot.
"""

from typing import Dict, Any, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class TelegramMessageTemplates:
    """Class for managing Telegram message templates and formatting"""
    
    def __init__(self):
        """Initialize the message templates manager"""
        self.templates = {}
        self._setup_default_templates()
    
    def _setup_default_templates(self):
        """Setup default message templates"""
        self.templates = {
            'welcome': {
                'text': "🤖 *Mean Reversion Strategy Bot*\n\n"
                        "Welcome! You'll receive trading signals when our mean reversion strategy "
                        "detects opportunities.\n\n"
                        "*Trading Hours:* 6:00-17:00 UTC\n"
                        "*Timeframe:* 5-minute candles\n"
                        "*Strategy:* Bollinger Bands + VWAP Mean Reversion\n\n"
                        "Use /help for available commands.",
                'parse_mode': 'Markdown'
            },
            
            'help': {
                'text': "📋 *Available Commands:*\n\n"
                        "• /start - Start receiving signals\n"
                        "• /stop - Stop receiving signals  \n"
                        "• /status - Show bot status\n"
                        "• /help - Show this help message\n\n"
                        "🔔 You'll automatically receive trading signals during market hours.",
                'parse_mode': 'Markdown'
            },
            
            'stop_notifications': {
                'text': "🔕 *Notifications Stopped*\n\n"
                        "You will no longer receive trading signals.\n"
                        "Use /start to resume notifications.",
                'parse_mode': 'Markdown'
            },
            
            'status': {
                'text': "📊 *Bot Status*\n\n"
                        "• Status: {status}\n"
                        "• Trading Hours: 6:00-17:00 UTC\n"
                        "• Last Signal: {last_signal}\n"
                        "• Active Chats: {active_chats}\n"
                        "• Symbols Monitored: {symbols_count}",
                'parse_mode': 'Markdown'
            },
            
            'trading_signal_long': {
                'text': "📈 *LONG SIGNAL*\n\n"
                        "🎯 *Symbol:* `{symbol}`\n"
                        "💰 *Entry Price:* `{entry_price}`\n"
                        "🛑 *Stop Loss:* `{stop_loss}`\n"
                        "🎯 *Take Profit:* `{take_profit}`\n"
                        "📊 *Position Size:* `{position_size}`\n"
                        "💸 *Risk Amount:* `${risk_amount}`\n"
                        "⚖️ *Risk/Reward:* `1:{risk_reward_ratio}`\n\n"
                        "📋 *Strategy Details:*\n"
                        "• BB Period: {bb_window} | Std: {bb_std}\n"
                        "• VWAP Period: {vwap_window} | Std: {vwap_std}\n"
                        "• ATR Period: {atr_period}\n\n"
                        "⏰ *Time:* `{timestamp}`",
                'parse_mode': 'Markdown'
            },
            
            'trading_signal_short': {
                'text': "📉 *SHORT SIGNAL*\n\n"
                        "🎯 *Symbol:* `{symbol}`\n"
                        "💰 *Entry Price:* `{entry_price}`\n"
                        "🛑 *Stop Loss:* `{stop_loss}`\n"
                        "🎯 *Take Profit:* `{take_profit}`\n"
                        "📊 *Position Size:* `{position_size}`\n"
                        "💸 *Risk Amount:* `${risk_amount}`\n"
                        "⚖️ *Risk/Reward:* `1:{risk_reward_ratio}`\n\n"
                        "📋 *Strategy Details:*\n"
                        "• BB Period: {bb_window} | Std: {bb_std}\n"
                        "• VWAP Period: {vwap_window} | Std: {vwap_std}\n"
                        "• ATR Period: {atr_period}\n\n"
                        "⏰ *Time:* `{timestamp}`",
                'parse_mode': 'Markdown'
            },
            
            'error_notification': {
                'text': "⚠️ *System Alert*\n\n"
                        "❌ *Error:* {error_type}\n"
                        "📝 *Details:* `{error_message}`\n"
                        "⏰ *Time:* `{timestamp}`\n\n"
                        "🔄 The system will attempt to recover automatically.",
                'parse_mode': 'Markdown'
            }
        }
    
    def get_welcome_message(self) -> Dict[str, str]:
        """Get welcome message for new users"""
        return self.templates['welcome']
    
    def get_help_message(self) -> Dict[str, str]:
        """Get help message"""
        return self.templates['help']
    
    def get_stop_message(self) -> Dict[str, str]:
        """Get stop notifications message"""
        return self.templates['stop_notifications']
    
    def get_status_message(self, status: str, last_signal: str, active_chats: int, symbols_count: int) -> Dict[str, str]:
        """
        Get formatted status message
        
        Args:
            status: Bot status (e.g., "Active", "Stopped")
            last_signal: Last signal time or "None"
            active_chats: Number of active chats
            symbols_count: Number of symbols being monitored
            
        Returns:
            Formatted status message
        """
        template = self.templates['status'].copy()
        template['text'] = template['text'].format(
            status=status,
            last_signal=last_signal,
            active_chats=active_chats,
            symbols_count=symbols_count
        )
        return template
    
    def get_trading_signal_message(self, signal_data: Dict[str, Any]) -> Dict[str, str]:
        """
        Get formatted trading signal message
        
        Args:
            signal_data: Dictionary containing signal information
            
        Returns:
            Formatted signal message
        """
        signal_type = signal_data.get('signal_type', 'long').lower()
        direction = signal_data.get('direction', 'LONG').upper()
        
        # Choose template based on signal direction
        template_key = 'trading_signal_long' if signal_type == 'long' or direction == 'LONG' else 'trading_signal_short'
        template = self.templates[template_key].copy()
        
        # Format timestamp
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')
        
        # Format message with signal data
        try:
            template['text'] = template['text'].format(
                symbol=signal_data.get('symbol', 'N/A'),
                entry_price=f"{signal_data.get('entry_price', 0):.4f}",
                stop_loss=f"{signal_data.get('stop_loss', 0):.4f}",
                take_profit=f"{signal_data.get('take_profit', 0):.4f}",
                position_size=f"{signal_data.get('position_size', 0):.2f}",
                risk_amount=f"{signal_data.get('risk_amount', 0):.2f}",
                risk_reward_ratio=f"{signal_data.get('risk_reward_ratio', 2):.1f}",
                bb_window=signal_data.get('strategy_params', {}).get('bb_window', 'N/A'),
                bb_std=signal_data.get('strategy_params', {}).get('bb_std', 'N/A'),
                vwap_window=signal_data.get('strategy_params', {}).get('vwap_window', 'N/A'),
                vwap_std=signal_data.get('strategy_params', {}).get('vwap_std', 'N/A'),
                atr_period=signal_data.get('strategy_params', {}).get('atr_period', 'N/A'),
                timestamp=timestamp
            )
        except Exception as e:
            logger.error(f"Error formatting signal message: {e}")
            # Fallback to basic message
            template = {
                'text': f"🚨 *{direction} SIGNAL*\n\n"
                        f"Symbol: {signal_data.get('symbol', 'N/A')}\n"
                        f"Entry: {signal_data.get('entry_price', 0):.4f}\n"
                        f"Time: {timestamp}",
                'parse_mode': 'Markdown'
            }
        
        return template
    
    def get_error_message(self, error_type: str, error_message: str) -> Dict[str, str]:
        """
        Get formatted error notification message
        
        Args:
            error_type: Type of error
            error_message: Error message details
            
        Returns:
            Formatted error message
        """
        template = self.templates['error_notification'].copy()
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')
        
        template['text'] = template['text'].format(
            error_type=error_type,
            error_message=error_message,
            timestamp=timestamp
        )
        return template
    
    def add_custom_template(self, name: str, text: str, parse_mode: str = 'Markdown'):
        """
        Add a custom message template
        
        Args:
            name: Template name
            text: Template text (can include format placeholders)
            parse_mode: Telegram parse mode
        """
        self.templates[name] = {
            'text': text,
            'parse_mode': parse_mode
        }
        logger.info(f"Added custom template: {name}")
    
    def list_templates(self) -> list:
        """Get list of available template names"""
        return list(self.templates.keys())

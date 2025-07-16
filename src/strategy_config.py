"""
Strategy Configuration Module

This module contains all configurable hyperparameters for the mean reversion strategy.
Parameters can be modified here without changing the core strategy logic.
"""

from typing import Dict, Any


class StrategyConfig:
    """
    Configuration class containing all strategy hyperparameters.
    """
    
    # Technical Indicator Parameters
    BOLLINGER_BANDS = {
        'window': 20,
        'std_dev': 2
    }
    
    VWAP = {
        'window': 20,
        'std_dev': 2,
        'anchor': 'day'  # 'day', 'week', 'month', 'year'
    }
    
    # Risk Management Parameters
    RISK_MANAGEMENT = {
        'risk_per_position_pct': 1.0,      # Risk 1% of account per position
        'stop_loss_atr_multiplier': 1.2,   # Stop loss = 1.2 * ATR
        'risk_reward_ratio': 2.5,          # Take profit = 2.5 * risk
        'atr_period': 14,                  # ATR calculation period
        'leverage': 100.0                  # Available leverage (100:1 for forex/CFD)
    }
    
    # Strategy Logic Parameters
    ENTRY_CONDITIONS = {
        'require_reversal_confirmation': True,  # Require price reversal for entry
        'min_volume_threshold': 0,              # Minimum volume for entry (0 = no filter)
        'max_positions': 1                      # Maximum concurrent positions
    }
    
    # Order Lifetime Parameters (in minutes)
    ORDER_LIFETIME = {
        '5m': 360,    # 6 hours for 5-minute timeframe (doubled from 3 hours)
        '15m': 720,   # 12 hours for 15-minute timeframe (doubled from 6 hours)
        '1h': 2880,   # 2 days for 1-hour timeframe (doubled from 1 day)
        'default': 720  # Default to 12 hours (doubled from 6 hours)
    }
    
    # Backtest Parameters
    BACKTEST = {
        'initial_cash': 100000,     # Starting capital
        'commission': 0.001,        # Commission rate (0.1%)
        'slippage': 0.0005         # Slippage rate (0.05%)
    }
    
    @classmethod
    def get_backtrader_params(cls) -> Dict[str, Any]:
        """
        Convert configuration to backtrader strategy parameters format.
        
        Returns:
            Dictionary of parameters for backtrader strategy
        """
        return {
            # Bollinger Bands
            'bb_window': cls.BOLLINGER_BANDS['window'],
            'bb_std': cls.BOLLINGER_BANDS['std_dev'],
            
            # VWAP
            'vwap_window': cls.VWAP['window'],
            'vwap_std': cls.VWAP['std_dev'],
            'vwap_anchor': cls.VWAP['anchor'],
            
            # ATR
            'atr_period': cls.RISK_MANAGEMENT['atr_period'],
            
            # Entry conditions
            'require_reversal': cls.ENTRY_CONDITIONS['require_reversal_confirmation'],
            'min_volume': cls.ENTRY_CONDITIONS['min_volume_threshold'],
            'max_positions': cls.ENTRY_CONDITIONS['max_positions'],
            
            # Order lifetime
            'order_lifetime_minutes': cls.ORDER_LIFETIME
        }
    
    @classmethod
    def get_risk_config(cls) -> Dict[str, Any]:
        """
        Get risk management configuration.
        
        Returns:
            Dictionary of risk management parameters
        """
        return cls.RISK_MANAGEMENT.copy()
    
    @classmethod
    def update_config(cls, **kwargs) -> None:
        """
        Update configuration parameters.
        
        Args:
            **kwargs: Configuration parameters to update
        """
        for key, value in kwargs.items():
            if hasattr(cls, key.upper()):
                section = getattr(cls, key.upper())
                if isinstance(section, dict) and isinstance(value, dict):
                    section.update(value)
                else:
                    setattr(cls, key.upper(), value)
    
    @classmethod
    def get_all_config(cls) -> Dict[str, Any]:
        """
        Get all configuration as a single dictionary.
        
        Returns:
            Complete configuration dictionary
        """
        return {
            'bollinger_bands': cls.BOLLINGER_BANDS,
            'vwap': cls.VWAP,
            'risk_management': cls.RISK_MANAGEMENT,
            'entry_conditions': cls.ENTRY_CONDITIONS,
            'order_lifetime': cls.ORDER_LIFETIME,
            'backtest': cls.BACKTEST
        }


# Alternative configuration for different market conditions or testing
class AggressiveConfig(StrategyConfig):
    """
    More aggressive configuration with tighter stops and higher risk.
    """
    RISK_MANAGEMENT = {
        'risk_per_position_pct': 2.0,      # Risk 2% per position
        'stop_loss_atr_multiplier': 1.0,   # Tighter stop loss
        'risk_reward_ratio': 3.0,          # Higher reward target
        'atr_period': 10,                  # Shorter ATR period
        'leverage': 100.0                  # Available leverage (100:1 for forex/CFD)
    }
    
    BOLLINGER_BANDS = {
        'window': 15,                      # Shorter period
        'std_dev': 1.5                     # Tighter bands
    }


class ConservativeConfig(StrategyConfig):
    """
    More conservative configuration with wider stops and lower risk.
    """
    RISK_MANAGEMENT = {
        'risk_per_position_pct': 0.5,      # Risk 0.5% per position
        'stop_loss_atr_multiplier': 2.0,   # Wider stop loss
        'risk_reward_ratio': 2.0,          # Lower reward target
        'atr_period': 20,                  # Longer ATR period
        'leverage': 100.0                  # Available leverage (100:1 for forex/CFD)
    }
    
    BOLLINGER_BANDS = {
        'window': 25,                      # Longer period
        'std_dev': 2.5                     # Wider bands
    }


# Default configuration to use
DEFAULT_CONFIG = StrategyConfig

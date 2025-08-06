"""
Risk Management Module for Mean Reversion Strategy

This module provides comprehensive risk management functionality including:
- ATR-based stop loss calculation
- Risk-reward ratio management
- Position sizing based on account risk percentage
- Dynamic risk parameters
"""

import backtrader as bt
import pandas as pd
import logging
from typing import Dict, Any, Optional, Tuple

logger = logging.getLogger(__name__)


class RiskManager:
    """
    Risk management class that handles all risk-related calculations and parameters.
    """
    
    def __init__(self, 
                 risk_per_position_pct: float = 1.0,
                 stop_loss_atr_multiplier: float = 1.2,
                 risk_reward_ratio: float = 2.5,
                 atr_period: int = 14,
                 leverage: float = 100.0,
                 ):
        """
        Initialize risk management parameters.
        
        Args:
            risk_per_position_pct: Percentage of account to risk per position (default: 1.0%)
            stop_loss_atr_multiplier: ATR multiplier for stop loss calculation (default: 1.2)
            risk_reward_ratio: Risk-reward ratio for take profit (default: 2.5)
            atr_period: Period for ATR calculation (default: 14)
            leverage: Available leverage for position sizing (default: 100.0)
            # Removed quiet parameter - using logger instead
        """
        self.risk_per_position_pct = risk_per_position_pct
        self.stop_loss_atr_multiplier = stop_loss_atr_multiplier
        self.risk_reward_ratio = risk_reward_ratio
        self.atr_period = atr_period
        self.leverage = leverage
        # Using logger instead of quiet parameter
    
    def calculate_atr_stop_loss(self, current_price: float, atr_value: float, position_type: str) -> float:
        """
        Calculate stop loss based on ATR.
        
        Args:
            current_price: Current market price
            atr_value: Average True Range value
            position_type: 'long' or 'short'
            
        Returns:
            Stop loss price
        """
        atr_distance = atr_value * self.stop_loss_atr_multiplier
        
        if position_type.lower() == 'long':
            return current_price - atr_distance
        elif position_type.lower() == 'short':
            return current_price + atr_distance
        else:
            raise ValueError("position_type must be 'long' or 'short'")
    
    def calculate_take_profit(self, entry_price: float, stop_loss: float, position_type: str) -> float:
        """
        Calculate take profit based on risk-reward ratio.
        
        Args:
            entry_price: Entry price of the position
            stop_loss: Stop loss price
            position_type: 'long' or 'short'
            
        Returns:
            Take profit price
        """
        if position_type.lower() == 'long':
            risk = entry_price - stop_loss
            return entry_price + (risk * self.risk_reward_ratio)
        elif position_type.lower() == 'short':
            risk = stop_loss - entry_price
            return entry_price - (risk * self.risk_reward_ratio)
        else:
            raise ValueError("position_type must be 'long' or 'short'")
    
    def calculate_position_size(self, account_value: float, entry_price: float, stop_loss: float, leverage: float = None) -> int:
        """
        Calculate position size based on risk percentage with leverage support.
        
        Args:
            account_value: Current account value
            entry_price: Entry price of the position
            stop_loss: Stop loss price
            leverage: Available leverage (uses instance leverage if not provided)
            
        Returns:
            Position size (number of shares/units)
        """
        if leverage is None:
            leverage = self.leverage
            
        # Calculate risk amount based on account value (this stays the same for risk management)
        risk_amount = account_value * (self.risk_per_position_pct / 100)
        price_risk = abs(entry_price - stop_loss)
        
        if price_risk == 0:
            return 0
        
        # Position size based on risk management (not limited by account balance)
        position_size = int(risk_amount / price_risk)
        
        # Calculate required margin for this position
        position_value = position_size * entry_price
        required_margin = position_value / leverage
        
        # If required margin exceeds account value, scale down the position
        # This is a safety check - in practice, brokers provide leverage
        if required_margin > account_value * 0.95:  # Keep 5% buffer
            # Calculate maximum position size that fits within margin requirements
            max_position_value = account_value * 0.95 * leverage
            max_position_size = int(max_position_value / entry_price)
            
            # Log the adjustment if significant
            if max_position_size < position_size * 0.8:  # If reduction is more than 20%
                logger.info(f"Position size adjusted due to margin: {position_size} -> {max_position_size}")
                logger.info(f"Required margin: ${required_margin:.2f}, Available: ${account_value:.2f}")
            
            position_size = max_position_size
        
        return max(1, position_size)  # Minimum position size of 1
    
    def calculate_margin_requirements(self, position_size: int, entry_price: float, leverage: float = None) -> Dict[str, float]:
        """
        Calculate margin requirements for a position.
        
        Args:
            position_size: Size of the position in units
            entry_price: Entry price per unit
            leverage: Available leverage (uses instance leverage if not provided)
            
        Returns:
            Dictionary with margin information
        """
        if leverage is None:
            leverage = self.leverage
            
        position_value = position_size * entry_price
        required_margin = position_value / leverage  # Position value divided by leverage ratio
        
        return {
            'position_value': position_value,
            'required_margin': required_margin,
            'leverage': leverage,
            'leverage_ratio': f"1:{int(leverage)}"  # Display as 1:100 format
        }
    
    def validate_margin_requirements(self, account_value: float, position_size: int, entry_price: float, 
                                   leverage: float = None) -> Tuple[bool, str, Dict[str, float]]:
        """
        Validate if account has sufficient margin for a position.
        
        Args:
            account_value: Current account value
            position_size: Size of the position in units
            entry_price: Entry price per unit
            leverage: Available leverage (uses instance leverage if not provided)
            
        Returns:
            Tuple of (is_valid, reason, margin_info)
        """
        margin_info = self.calculate_margin_requirements(position_size, entry_price, leverage)
        
        # Keep a small buffer (5%) for account safety
        available_margin = account_value * 0.95
        required_margin = margin_info['required_margin']
        
        if required_margin <= available_margin:
            return True, "Sufficient margin available", margin_info
        else:
            return False, f"Insufficient margin: Required ${required_margin:.2f}, Available ${available_margin:.2f}", margin_info

    def get_risk_metrics(self, entry_price: float, stop_loss: float, take_profit: float, 
                        position_type: str) -> Dict[str, float]:
        """
        Calculate comprehensive risk metrics for a trade.
        
        Args:
            entry_price: Entry price of the position
            stop_loss: Stop loss price
            take_profit: Take profit price
            position_type: 'long' or 'short'
            
        Returns:
            Dictionary containing risk metrics
        """
        if position_type.lower() == 'long':
            risk = entry_price - stop_loss
            reward = take_profit - entry_price
        elif position_type.lower() == 'short':
            risk = stop_loss - entry_price
            reward = entry_price - take_profit
        else:
            raise ValueError("position_type must be 'long' or 'short'")
        
        rr_ratio = reward / risk if risk > 0 else 0
        win_rate_breakeven = 1 / (1 + rr_ratio) if rr_ratio > 0 else 0
        
        return {
            'risk_amount': risk,
            'reward_amount': reward,
            'risk_reward_ratio': rr_ratio,
            'breakeven_win_rate': win_rate_breakeven,
            'risk_percentage': self.risk_per_position_pct
        }
    
    def validate_trade(self, entry_price: float, stop_loss: float, take_profit: float, 
                      position_type: str) -> Tuple[bool, str]:
        """
        Validate if a trade meets risk management criteria.
        
        Args:
            entry_price: Entry price of the position
            stop_loss: Stop loss price
            take_profit: Take profit price
            position_type: 'long' or 'short'
            
        Returns:
            Tuple of (is_valid, reason)
        """
        try:
            metrics = self.get_risk_metrics(entry_price, stop_loss, take_profit, position_type)
            
            # Check if risk-reward ratio meets minimum requirement
            min_rr = 1.0  # Minimum 1:1 risk-reward ratio
            if metrics['risk_reward_ratio'] < min_rr:
                return False, f"Risk-reward ratio {metrics['risk_reward_ratio']:.2f} below minimum {min_rr}"
            
            # Check if risk amount is reasonable (not too small)
            if metrics['risk_amount'] <= 0:
                return False, "Risk amount must be positive"
            
            # Additional validation can be added here
            
            return True, "Trade passes risk management validation"
            
        except Exception as e:
            return False, f"Validation error: {str(e)}"


class ATRIndicator(bt.Indicator):
    """
    Average True Range (ATR) indicator for Backtrader.
    """
    lines = ('atr',)
    params = (('period', 14),)
    
    def __init__(self):
        # True Range calculation
        h_l = self.data.high - self.data.low
        h_pc = abs(self.data.high - self.data.close(-1))
        l_pc = abs(self.data.low - self.data.close(-1))
        
        # True Range is the maximum of the three values
        true_range = bt.Max(h_l, h_pc, l_pc)
        
        # ATR is the simple moving average of True Range
        self.lines.atr = bt.indicators.SimpleMovingAverage(
            true_range, period=self.params.period
        )


def create_risk_manager(config: Optional[Dict[str, Any]] = None) -> RiskManager:
    """
    Factory function to create a RiskManager with configuration.
    
    Args:
        config: Configuration dictionary with risk parameters
        # Removed quiet parameter - using logger instead
        
    Returns:
        Configured RiskManager instance
    """
    default_config = {
        'risk_per_position_pct': 1.0,
        'stop_loss_atr_multiplier': 1.2,
        'risk_reward_ratio': 2.5,
        'atr_period': 14,
        'leverage': 100.0,  # Default leverage for forex/CFD trading
        # Removed quiet parameter
    }
    
    if config:
        default_config.update(config)
    
    return RiskManager(**default_config)

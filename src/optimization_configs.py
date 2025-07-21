"""
Optimization Configuration Module

This module contains predefined optimization scenarios and parameter grids
for hyperparameter optimization of the mean reversion strategy.
"""

from typing import Dict, List, Union, Tuple


class OptimizationConfigs:
    """Predefined optimization configurations"""
    
    @staticmethod
    def get_quick_test_grid() -> Dict[str, List]:
        """Quick test grid for rapid testing (4-16 combinations)"""
        return {
            'bb_window': [20, 25],
            'bb_std': [2.0, 2.5],
            'risk_per_position_pct': [1.0, 1.5],
            'risk_reward_ratio': [2.5, 3.0],
        }
    
    @staticmethod
    def get_focused_grid() -> Dict[str, List]:
        """Focused grid on most impactful parameters (~100-500 combinations)"""
        return {
            # Technical indicators - key parameters
            'bb_window': [20, 25, 30],
            'bb_std': [2.0, 2.5],
            'vwap_window': [20, 25],
            'vwap_std': [2.0, 2.5],
            
            # Risk management - critical for performance
            'risk_per_position_pct': [1.0, 1.5, 2.0],
            'stop_loss_atr_multiplier': [1.0, 1.2, 1.5],
            'risk_reward_ratio': [2.5, 3.0, 3.5],
            
            # Strategy behavior
            'require_reversal': [False],
            
            # Market regime filtering
            'regime_min_score': [60, 70],
        }
    
    @staticmethod
    def get_comprehensive_grid() -> Dict[str, List]:
        """Comprehensive grid for thorough optimization (~1000+ combinations)"""
        return {
            # Technical indicators
            'bb_window': [15, 20, 25, 30, 35],
            'bb_std': [1.5, 2.0, 2.5, 3.0],
            'vwap_window': [15, 20, 25, 30],
            'vwap_std': [1.5, 2.0, 2.5, 3.0],
            'atr_period': [10, 14, 20],
            
            # Risk management
            'risk_per_position_pct': [0.5, 1.0, 1.5, 2.0, 2.5],
            'stop_loss_atr_multiplier': [1.0, 1.2, 1.5, 2.0],
            'risk_reward_ratio': [2.0, 2.5, 3.0, 3.5, 4.0],
            
            # Strategy behavior
            'require_reversal': [True, False],
            
            # Market regime filtering
            'regime_min_score': [40, 50, 60, 70, 80],
        }
    
    @staticmethod
    def get_risk_management_grid() -> Dict[str, List]:
        """Risk management focused grid"""
        return {
            'risk_per_position_pct': [0.25, 0.5, 0.75, 1.0, 1.25, 1.5, 2.0, 2.5, 3.0],
            'stop_loss_atr_multiplier': [0.5, 0.8, 1.0, 1.2, 1.5, 2.0, 2.5],
            'risk_reward_ratio': [1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 5.0],
        }
    
    @staticmethod
    def get_indicator_grid() -> Dict[str, List]:
        """Technical indicator focused grid"""
        return {
            'bb_window': [10, 15, 20, 25, 30, 35, 40],
            'bb_std': [1.0, 1.5, 2.0, 2.5, 3.0, 3.5],
            'vwap_window': [10, 15, 20, 25, 30, 35, 40],
            'vwap_std': [1.0, 1.5, 2.0, 2.5, 3.0, 3.5],
            'atr_period': [5, 10, 14, 20, 25, 30],
        }
    
    @staticmethod
    def get_market_regime_grid() -> Dict[str, List]:
        """Market regime filtering focused grid"""
        return {
            'regime_min_score': [30, 40, 50, 60, 70, 80, 90],
        }
    
    @staticmethod
    def get_random_search_ranges() -> Dict[str, Union[List, Tuple]]:
        """Parameter ranges for random search optimization"""
        return {
            # Discrete choices
            'bb_window': [10, 15, 20, 25, 30, 35, 40],
            'bb_std': [1.0, 1.5, 2.0, 2.5, 3.0, 3.5],
            'vwap_window': [10, 15, 20, 25, 30, 35, 40],
            'vwap_std': [1.0, 1.5, 2.0, 2.5, 3.0, 3.5],
            'atr_period': [5, 10, 14, 20, 25, 30],
            'require_reversal': [True, False],
            'regime_min_score': [30, 40, 50, 60, 70, 80, 90],
            
            # Continuous ranges (min, max)
            'risk_per_position_pct': (0.25, 3.0),
            'stop_loss_atr_multiplier': (0.5, 3.0),
            'risk_reward_ratio': (1.5, 5.0),
        }
    
    @staticmethod
    def get_balanced_pnl_drawdown_grid() -> Dict[str, List]:
        """Grid optimized for balancing PnL and drawdown"""
        return {
            # Technical indicators - moderate settings
            'bb_window': [20, 25, 30],
            'bb_std': [2.0, 2.5, 3.0],
            'vwap_window': [20, 25, 30],
            'vwap_std': [2.0, 2.5],
            
            # Risk management - critical for drawdown control
            'risk_per_position_pct': [0.5, 0.75, 1.0, 1.25],  # Lower risk values to reduce drawdown
            'stop_loss_atr_multiplier': [0.8, 1.0, 1.2, 1.5],  # Tighter stops to minimize drawdown
            'risk_reward_ratio': [2.0, 2.5, 3.0, 3.5],  # Balanced risk/reward
            
            # Strategy behavior for smoother equity curve
            'require_reversal': [True],  # Require confirmation to reduce false signals
            
            # Market regime filtering to avoid unfavorable conditions
            'regime_min_score': [60, 70, 80],  # Higher filtering to avoid drawdowns
            
            # ATR period
            'atr_period': [10, 14, 20],
        }
    


class OptimizationObjectives:
    """Define different optimization objectives"""
    
    @staticmethod
    def max_final_pnl(result) -> float:
        """Maximize final P&L"""
        return result.final_pnl
    
    @staticmethod
    def max_sharpe_ratio(result) -> float:
        """Maximize Sharpe ratio"""
        return result.sharpe_ratio
    
    @staticmethod
    def max_win_rate(result) -> float:
        """Maximize win rate"""
        return result.win_rate
    
    @staticmethod
    def min_drawdown(result) -> float:
        """Minimize maximum drawdown (return negative for minimization)"""
        return -result.max_drawdown
    
    @staticmethod
    def risk_adjusted_return(result) -> float:
        """Maximize return per unit of risk (PnL / max_drawdown)"""
        if result.max_drawdown == 0:
            return result.final_pnl
        return result.final_pnl / max(result.max_drawdown, 0.01)  # Avoid division by zero
    
    @staticmethod
    def profit_factor(result) -> float:
        """Maximize profit factor (requires trade-level data)"""
        # This would require individual trade P&L data
        # For now, use a proxy based on win rate and average return
        if result.win_rate == 0:
            return 0
        return result.win_rate * result.final_pnl / max(result.total_trades, 1)
    
    @staticmethod
    def balanced_pnl_drawdown(result) -> float:
        """Maximize PnL while minimizing drawdown - balanced approach"""
        if result.max_drawdown == 0:
            return result.final_pnl
        
        # Scale PnL by inverse of drawdown (higher drawdown = lower score)
        # This creates a balance between maximizing PnL and minimizing drawdown
        drawdown_factor = 1 / (result.max_drawdown / 100)  # Convert percentage to decimal
        return result.final_pnl * drawdown_factor


class MarketConditionConfigs:
    """Market condition specific optimization configurations"""
    
    @staticmethod
    def get_trending_market_config() -> Dict[str, List]:
        """Optimized for trending market conditions"""
        return {
            # Wider bands for trending markets
            'bb_std': [2.5, 3.0, 3.5],
            'vwap_std': [2.5, 3.0, 3.5],
            
            # Tighter stops and higher rewards for trends
            'stop_loss_atr_multiplier': [0.8, 1.0, 1.2],
            'risk_reward_ratio': [3.0, 3.5, 4.0],
            
            # Require reversal confirmation in trending markets
            'require_reversal': [True],
            
            # Higher regime score to avoid false signals
            'regime_min_score': [70, 80, 90],
        }
    
    @staticmethod
    def get_ranging_market_config() -> Dict[str, List]:
        """Optimized for ranging market conditions"""
        return {
            # Tighter bands for ranging markets
            'bb_std': [1.5, 2.0, 2.5],
            'vwap_std': [1.5, 2.0, 2.5],
            
            # Wider stops and moderate rewards for ranges
            'stop_loss_atr_multiplier': [1.5, 2.0, 2.5],
            'risk_reward_ratio': [2.0, 2.5, 3.0],
            
            # Lower regime score to capture more opportunities
            'regime_min_score': [40, 50, 60],
        }
    
    @staticmethod
    def get_high_volatility_config() -> Dict[str, List]:
        """Optimized for high volatility conditions"""
        return {
            # Wider bands for high volatility
            'bb_std': [2.5, 3.0, 3.5],
            'vwap_std': [2.5, 3.0, 3.5],
            
            # Lower risk per trade due to high volatility
            'risk_per_position_pct': [0.5, 0.75, 1.0],
            
            # Wider stops to avoid premature exits
            'stop_loss_atr_multiplier': [1.5, 2.0, 2.5],
            
            # Higher rewards to compensate for wider stops
            'risk_reward_ratio': [3.0, 3.5, 4.0, 4.5],
            
            # Higher regime filtering
            'regime_min_score': [70, 80, 90],
        }
    
    @staticmethod
    def get_low_volatility_config() -> Dict[str, List]:
        """Optimized for low volatility conditions"""
        return {
            # Tighter bands for low volatility
            'bb_std': [1.5, 2.0, 2.5],
            'vwap_std': [1.5, 2.0, 2.5],
            
            # Higher risk per trade due to lower volatility
            'risk_per_position_pct': [1.5, 2.0, 2.5],
            
            # Tighter stops in low volatility
            'stop_loss_atr_multiplier': [1.0, 1.2, 1.5],
            
            # Moderate rewards
            'risk_reward_ratio': [2.0, 2.5, 3.0],
            
            # Lower regime filtering to capture opportunities
            'regime_min_score': [40, 50, 60],
        }


class TimeframeConfigs:
    """Timeframe specific optimization configurations"""
    
    @staticmethod
    def get_scalping_config() -> Dict[str, List]:
        """Optimized for scalping timeframes (1m, 5m)"""
        return {
            # Shorter periods for fast reaction
            'bb_window': [10, 15, 20],
            'vwap_window': [10, 15, 20],
            'atr_period': [5, 10, 14],
            
            # Tight stops and quick profits
            'stop_loss_atr_multiplier': [0.5, 0.8, 1.0],
            'risk_reward_ratio': [1.5, 2.0, 2.5],
            
            # Higher risk for frequent trades
            'risk_per_position_pct': [0.25, 0.5, 0.75],
            
            # Quick reversal confirmation
            'require_reversal': [True],
        }
    
    @staticmethod
    def get_swing_trading_config() -> Dict[str, List]:
        """Optimized for swing trading timeframes (1h, 4h, 1d)"""
        return {
            # Longer periods for swing moves
            'bb_window': [20, 25, 30, 35],
            'vwap_window': [20, 25, 30, 35],
            'atr_period': [14, 20, 25],
            
            # Wider stops and higher rewards for swings
            'stop_loss_atr_multiplier': [1.5, 2.0, 2.5, 3.0],
            'risk_reward_ratio': [3.0, 4.0, 5.0],
            
            # Moderate risk for longer-term trades
            'risk_per_position_pct': [1.0, 1.5, 2.0],
            
            # Both reversal strategies
            'require_reversal': [True, False],
        }


# Registry of all available configurations
OPTIMIZATION_CONFIGS = {
    # Standard grids
    'quick': OptimizationConfigs.get_quick_test_grid,
    'focused': OptimizationConfigs.get_focused_grid,
    'comprehensive': OptimizationConfigs.get_comprehensive_grid,
    'risk': OptimizationConfigs.get_risk_management_grid,
    'indicators': OptimizationConfigs.get_indicator_grid,
    'regime': OptimizationConfigs.get_market_regime_grid,
    'balanced': OptimizationConfigs.get_balanced_pnl_drawdown_grid,
    
    # Market condition specific
    'trending': MarketConditionConfigs.get_trending_market_config,
    'ranging': MarketConditionConfigs.get_ranging_market_config,
    'high_vol': MarketConditionConfigs.get_high_volatility_config,
    'low_vol': MarketConditionConfigs.get_low_volatility_config,
    
    # Timeframe specific
    'scalping': TimeframeConfigs.get_scalping_config,
    'swing': TimeframeConfigs.get_swing_trading_config,
}

# Random search ranges
RANDOM_SEARCH_RANGES = OptimizationConfigs.get_random_search_ranges()

# Optimization objectives
OPTIMIZATION_OBJECTIVES = {
    'max_pnl': OptimizationObjectives.max_final_pnl,
    'max_sharpe': OptimizationObjectives.max_sharpe_ratio,
    'max_winrate': OptimizationObjectives.max_win_rate,
    'min_drawdown': OptimizationObjectives.min_drawdown,
    'risk_adjusted': OptimizationObjectives.risk_adjusted_return,
    'profit_factor': OptimizationObjectives.profit_factor,
    'balanced': OptimizationObjectives.balanced_pnl_drawdown,
}

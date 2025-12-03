"""
Unified Strategy Configuration

This is the single source of truth for all strategy configuration.
Modify these settings to adjust the strategy behavior.
"""

from typing import Dict, Any


class Config:
    """
    Main configuration class containing all strategy parameters.
    """

    # ===========================================
    # TECHNICAL INDICATORS
    # ===========================================

    # Bollinger Bands Parameters
    BOLLINGER_BANDS = {
        'window': 20,           # Moving average period
        'std_dev': 2            # Number of standard deviations
    }

    # VWAP (Volume Weighted Average Price) Parameters
    VWAP = {
        'window': 20,           # Lookback period
        'std_dev': 2,           # Standard deviation bands
        'anchor': 'day'         # Anchor period: 'day', 'week', 'month', 'year'
    }

    # ===========================================
    # RISK MANAGEMENT (Per Position)
    # ===========================================

    RISK_MANAGEMENT = {
        'risk_per_position_pct': 1.0,        # Risk 1% of account per position
        'stop_loss_atr_multiplier': 1.2,     # Stop loss = 1.2 * ATR from entry
        'risk_reward_ratio': 2.5,            # Take profit = 2.5 * risk distance
        'atr_period': 14,                    # ATR calculation period
        'leverage': 100.0                    # Available leverage (100:1 for forex/CFD)
    }

    # ===========================================
    # TRAILING STOPS
    # ===========================================

    TRAILING_STOPS = {
        'enabled': False,                      # Enable trailing stop functionality
        'activation_pct': 50.0,                # Activate after reaching 50% of target
        'breakeven_plus_pct': 20.0             # Move stop to breakeven + 20% of target distance
    }

    # ===========================================
    # ENTRY CONDITIONS
    # ===========================================

    ENTRY_CONDITIONS = {
        'min_volume_threshold': 0,            # Minimum volume for entry (0 = no filter)
        'max_positions': 1                    # Max positions per asset
    }

    # ===========================================
    # MARKET REGIME DETECTION
    # ===========================================

    MARKET_REGIME = {
        'enabled': True,                      # Enable market condition filtering
        'adx_period': 14,                    # ADX calculation period
        'volatility_period': 14,             # ATR period for volatility
        'volatility_lookback': 100,          # Lookback for volatility percentile
        'min_regime_score': 60,              # Min score to allow trading (0-100)

        # Trend Detection Thresholds
        'adx_strong_trend_threshold': 25,    # ADX > 25 = strong trend (avoid)
        'adx_moderate_trend_threshold': 20,  # ADX > 20 = moderate trend

        # Volatility Thresholds
        'volatility_high_threshold': 67,     # Vol percentile > 67 = high (avoid)
        'volatility_low_threshold': 33       # Vol percentile < 33 = low (prefer)
    }

    # ===========================================
    # ORDER MANAGEMENT
    # ===========================================

    # Order lifetime by timeframe (in minutes)
    ORDER_LIFETIME = {
        '5m': 360,      # 6 hours for 5-minute timeframe
        '15m': 720,     # 12 hours for 15-minute timeframe
        '1h': 2880,     # 2 days for 1-hour timeframe
        'default': 720  # Default: 12 hours
    }

    # ===========================================
    # BACKTEST SETTINGS
    # ===========================================

    BACKTEST = {
        'initial_cash': 100000,    # Starting capital
        'commission': 0.001,       # Commission rate (0.1%)
        'slippage': 0.0005        # Slippage rate (0.05%)
    }

    # ===========================================
    # TRADING MODE PRESETS
    # ===========================================

    @classmethod
    def set_mode(cls, mode: str) -> None:
        """
        Apply preset configurations for different trading modes.

        Args:
            mode: Trading mode - 'backtest', 'live', or 'conservative'
        """
        if mode == 'backtest':
            # Backtesting mode: Standard settings
            cls.RISK_MANAGEMENT['risk_per_position_pct'] = 1.0

        elif mode == 'live':
            # Live trading: More conservative
            cls.RISK_MANAGEMENT['risk_per_position_pct'] = 0.5
            cls.RISK_MANAGEMENT['stop_loss_atr_multiplier'] = 1.5

        elif mode == 'conservative':
            # Ultra-conservative for testing
            cls.RISK_MANAGEMENT['risk_per_position_pct'] = 0.25
            cls.RISK_MANAGEMENT['stop_loss_atr_multiplier'] = 2.0
            cls.RISK_MANAGEMENT['risk_reward_ratio'] = 2.0

    # ===========================================
    # HELPER METHODS
    # ===========================================

    @classmethod
    def get_backtrader_params(cls) -> Dict[str, Any]:
        """
        Convert configuration to backtrader strategy parameters format.
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
            'min_volume': cls.ENTRY_CONDITIONS['min_volume_threshold'],
            'max_positions': cls.ENTRY_CONDITIONS['max_positions'],

            # Market regime
            'regime_enabled': cls.MARKET_REGIME['enabled'],
            'regime_adx_period': cls.MARKET_REGIME['adx_period'],
            'regime_volatility_period': cls.MARKET_REGIME['volatility_period'],
            'regime_volatility_lookback': cls.MARKET_REGIME['volatility_lookback'],
            'regime_min_score': cls.MARKET_REGIME['min_regime_score'],

            # Order lifetime
            'order_lifetime_minutes': cls.ORDER_LIFETIME
        }

    @classmethod
    def get_risk_config(cls) -> Dict[str, Any]:
        """Get risk management configuration."""
        return cls.RISK_MANAGEMENT.copy()

    @classmethod
    def get_trailing_stop_config(cls) -> Dict[str, Any]:
        """Get trailing stop configuration."""
        return cls.TRAILING_STOPS.copy()

    @classmethod
    def get_market_regime_config(cls) -> Dict[str, Any]:
        """Get market regime detection configuration."""
        return cls.MARKET_REGIME.copy()

    @classmethod
    def update_config(cls, **kwargs) -> None:
        """
        Update configuration parameters dynamically.

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
        """Get all configuration as a single dictionary."""
        return {
            'bollinger_bands': cls.BOLLINGER_BANDS,
            'vwap': cls.VWAP,
            'risk_management': cls.RISK_MANAGEMENT,
            'trailing_stops': cls.TRAILING_STOPS,
            'entry_conditions': cls.ENTRY_CONDITIONS,
            'market_regime': cls.MARKET_REGIME,
            'order_lifetime': cls.ORDER_LIFETIME,
            'backtest': cls.BACKTEST
        }


# Create a single instance for easy import
CONFIG = Config()
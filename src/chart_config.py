"""
Chart Configuration Module

This module contains all configurable settings for chart generation including:
- Color themes (dark/light)
- Indicator visibility per strategy type
- Chart size and resolution settings
"""

from typing import Dict, Any, Optional


class ChartConfig:
    """
    Configuration class for chart visualization settings.
    Provides dark theme color palette and indicator visibility rules.
    """
    
    # Color Theme - Dark Mode
    THEME = {
        'mode': 'dark',
        
        # Background colors
        'background': '#1a1a1a',       # Dark charcoal background
        'face_color': '#1a1a1a',       # Chart face color
        'figure_color': '#1a1a1a',     # Figure background
        'grid_color': '#2d2d2d',       # Subtle grid lines
        'edge_color': '#3a3a3a',       # Border color
        
        # Text colors
        'text_color': '#e0e0e0',       # Light gray for text
        'title_color': '#ffffff',      # White for title
        
        # Candlestick colors - Bright colors for dark background
        'candle_up': '#00e676',        # Bright green for up candles
        'candle_down': '#ff5252',      # Bright red for down candles
        'candle_edge': 'inherit',      # Use body color for edges
        'candle_wick_up': '#00e676',   # Green wicks
        'candle_wick_down': '#ff5252', # Red wicks
        'candle_alpha': 0.9,           # Slight transparency
        
        # Indicator colors - Light colors visible on dark background
        'bb_bands': '#64b5f6',         # Light blue for Bollinger Bands
        'vwap_bands': '#ba68c8',       # Light purple for VWAP bands
        
        # Signal line colors - High contrast for visibility
        'entry_line': '#ffd54f',       # Amber/gold - highly visible
        'stop_loss': '#ff5252',        # Bright red
        'take_profit': '#00e676',      # Bright green
        
        # Line styles for Bollinger Bands
        'bb_linestyle': '--',          # Dashed
        'bb_linewidth': 1.2,
        'bb_alpha': 0.7,
        
        # Line styles for VWAP Bands
        'vwap_linestyle': ':',         # Dotted
        'vwap_linewidth': 1.2,
        'vwap_alpha': 0.7,
        
        # Line styles for Entry
        'entry_linestyle': '-',        # Solid
        'entry_linewidth': 2.5,
        'entry_alpha': 0.9,
        
        # Line styles for Stop Loss
        'sl_linestyle': '--',          # Dashed
        'sl_linewidth': 2.0,
        'sl_alpha': 0.85,
        
        # Line styles for Take Profit
        'tp_linestyle': '-.',          # Dash-dot
        'tp_linewidth': 2.0,
        'tp_alpha': 0.85,
    }
    
    # RSI Configuration
    RSI_CONFIG = {
        'enabled': True,                # Global RSI enable/disable
        'period': 14,                   # RSI calculation period (standard)
        'overbought': 70,               # Overbought threshold
        'oversold': 30,                 # Oversold threshold
        'midline': 50,                  # Midline reference
        'panel_height_ratio': 0.2,      # RSI panel takes 20% of total height (80/20 split)
        
        # RSI Colors for dark theme
        'line_color': '#4fc3f7',        # Bright cyan/light blue for RSI line
        'overbought_color': '#ff5252',  # Light red for overbought level (70)
        'oversold_color': '#00e676',    # Light green for oversold level (30)
        'midline_color': '#757575',     # Gray for midline (50)
        
        # Line styles
        'line_width': 2.0,              # RSI line width
        'level_line_style': '--',       # Dashed for threshold levels
        'level_line_width': 1.0,        # Threshold line width
        'level_alpha': 0.6,             # Transparency for threshold lines
        'fill_overbought': False,       # Fill area above 70 (optional)
        'fill_oversold': False,         # Fill area below 30 (optional)
    }
    
    # Indicator Visibility by Strategy Type
    INDICATOR_VISIBILITY = {
        'mean_reversion': {
            'show_bb': True,
            'show_vwap': True,
            'show_rsi': True,
            'description': 'Show BB, VWAP, and RSI for mean reversion strategy'
        },
        'custom_strategies': {
            # Default for custom strategies (when specific strategy not found)
            'show_bb': False,
            'show_vwap': False,
            'show_rsi': True,
            'description': 'Hide BB/VWAP by default, show RSI for custom strategies'
        },
        'vwap': {
            'show_bb': False,
            'show_vwap': True,
            'show_rsi': True,
            'description': 'VWAP-only strategies with RSI (vwap, vwap_btc)'
        },
        'vwap_btc': {
            'show_bb': False,
            'show_vwap': True,
            'show_rsi': True,
            'description': 'VWAP strategy for Bitcoin with RSI'
        },
        'session_sweep': {
            'show_bb': False,
            'show_vwap': False,
            'show_rsi': True,
            'description': 'Session sweep with RSI indicator'
        }
    }
    
    # Chart Size and Resolution
    CHART_SIZE = {
        'figure_size': (12, 8),        # Size in inches (width, height)
        'dpi': 100,                     # Resolution (dots per inch)
        'candles_to_show': 100          # Number of candles to display
    }
    
    @classmethod
    def get_indicator_visibility(cls, strategy_type: str, custom_strategy_name: Optional[str] = None) -> Dict[str, bool]:
        """
        Get indicator visibility settings based on strategy type.
        
        Args:
            strategy_type: Primary strategy type ('mean_reversion' or 'custom_strategies')
            custom_strategy_name: For custom strategies, the specific strategy name
                                  (e.g., 'vwap', 'session_sweep', 'vwap_btc')
        
        Returns:
            Dictionary with 'show_bb', 'show_vwap', and 'show_rsi' boolean flags
        
        Examples:
            >>> ChartConfig.get_indicator_visibility('mean_reversion')
            {'show_bb': True, 'show_vwap': True, 'show_rsi': True}
            
            >>> ChartConfig.get_indicator_visibility('custom_strategies', 'vwap')
            {'show_bb': False, 'show_vwap': True, 'show_rsi': True}
            
            >>> ChartConfig.get_indicator_visibility('custom_strategies', 'session_sweep')
            {'show_bb': False, 'show_vwap': False, 'show_rsi': False}
        """
        if strategy_type == 'mean_reversion':
            return {
                'show_bb': cls.INDICATOR_VISIBILITY['mean_reversion']['show_bb'],
                'show_vwap': cls.INDICATOR_VISIBILITY['mean_reversion']['show_vwap'],
                'show_rsi': cls.INDICATOR_VISIBILITY['mean_reversion']['show_rsi']
            }
        elif strategy_type == 'custom_strategies':
            # Check if there's a specific config for this custom strategy
            if custom_strategy_name and custom_strategy_name in cls.INDICATOR_VISIBILITY:
                return {
                    'show_bb': cls.INDICATOR_VISIBILITY[custom_strategy_name]['show_bb'],
                    'show_vwap': cls.INDICATOR_VISIBILITY[custom_strategy_name]['show_vwap'],
                    'show_rsi': cls.INDICATOR_VISIBILITY[custom_strategy_name]['show_rsi']
                }
            # Otherwise use default for custom strategies
            return {
                'show_bb': cls.INDICATOR_VISIBILITY['custom_strategies']['show_bb'],
                'show_vwap': cls.INDICATOR_VISIBILITY['custom_strategies']['show_vwap'],
                'show_rsi': cls.INDICATOR_VISIBILITY['custom_strategies']['show_rsi']
            }
        else:
            # Default: show all if strategy type unknown
            return {'show_bb': True, 'show_vwap': True, 'show_rsi': True}
    
    @classmethod
    def get_theme_colors(cls) -> Dict[str, Any]:
        """
        Get current theme colors.
        
        Returns:
            Dictionary containing all theme color settings
        """
        return cls.THEME.copy()
    
    @classmethod
    def update_theme(cls, **kwargs):
        """
        Update specific theme colors dynamically.
        
        Args:
            **kwargs: Color settings to update (e.g., candle_up='#00ff00')
        
        Example:
            >>> ChartConfig.update_theme(candle_up='#00ff00', background='#000000')
        """
        cls.THEME.update(kwargs)
    
    @classmethod
    def get_chart_size(cls) -> Dict[str, Any]:
        """
        Get chart size configuration.
        
        Returns:
            Dictionary with figure_size, dpi, and candles_to_show
        """
        return cls.CHART_SIZE.copy()
    
    @classmethod
    def get_rsi_config(cls) -> Dict[str, Any]:
        """
        Get RSI configuration settings.
        
        Returns:
            Dictionary containing RSI configuration including period, thresholds, colors, and styling
        """
        return cls.RSI_CONFIG.copy()


class LightChartTheme:
    """
    Light theme color palette (original colors).
    Can be used as alternative by passing to SignalChartGenerator.
    """
    
    THEME = {
        'mode': 'light',
        
        # Background colors
        'background': '#ffffff',       # White background
        'face_color': '#ffffff',
        'figure_color': '#ffffff',
        'grid_color': '#e0e0e0',       # Light gray grid
        'edge_color': '#000000',       # Black border
        
        # Text colors
        'text_color': '#000000',       # Black text
        'title_color': '#000000',
        
        # Candlestick colors - Original muted colors
        'candle_up': '#26a69a',        # Teal green
        'candle_down': '#ef5350',      # Red
        'candle_edge': 'inherit',
        'candle_wick_up': '#26a69a',
        'candle_wick_down': '#ef5350',
        'candle_alpha': 0.9,
        
        # Indicator colors
        'bb_bands': '#808080',         # Gray for Bollinger Bands
        'vwap_bands': '#9932cc',       # Dark purple for VWAP
        
        # Signal line colors
        'entry_line': '#1f77b4',       # Blue
        'stop_loss': '#d62728',        # Red
        'take_profit': '#2ca02c',      # Green
        
        # Line styles (same as dark theme)
        'bb_linestyle': '--',
        'bb_linewidth': 1.2,
        'bb_alpha': 0.7,
        
        'vwap_linestyle': ':',
        'vwap_linewidth': 1.2,
        'vwap_alpha': 0.7,
        
        'entry_linestyle': '-',
        'entry_linewidth': 2.5,
        'entry_alpha': 0.9,
        
        'sl_linestyle': '--',
        'sl_linewidth': 2.0,
        'sl_alpha': 0.85,
        
        'tp_linestyle': '-.',
        'tp_linewidth': 2.0,
        'tp_alpha': 0.85,
    }
    
    # Same visibility and size settings as dark theme
    INDICATOR_VISIBILITY = ChartConfig.INDICATOR_VISIBILITY
    CHART_SIZE = ChartConfig.CHART_SIZE
    
    @classmethod
    def get_indicator_visibility(cls, strategy_type: str, custom_strategy_name: Optional[str] = None) -> Dict[str, bool]:
        """Same as ChartConfig.get_indicator_visibility"""
        return ChartConfig.get_indicator_visibility(strategy_type, custom_strategy_name)
    
    @classmethod
    def get_theme_colors(cls) -> Dict[str, Any]:
        """Get light theme colors"""
        return cls.THEME.copy()
    
    @classmethod
    def get_chart_size(cls) -> Dict[str, Any]:
        """Get chart size configuration"""
        return cls.CHART_SIZE.copy()


# Default configuration to use (dark theme)
DEFAULT_CHART_CONFIG = ChartConfig

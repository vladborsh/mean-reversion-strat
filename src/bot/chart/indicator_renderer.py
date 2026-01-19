#!/usr/bin/env python3
"""Indicator Renderer - Renders pre-calculated technical indicators on charts."""

import logging
import pandas as pd
from typing import Dict, Any, List, Optional

try:
    import mplfinance as mpf
    MPLFINANCE_AVAILABLE = True
except ImportError:
    MPLFINANCE_AVAILABLE = False
    mpf = None

logger = logging.getLogger(__name__)


class IndicatorRenderer:
    """Renders pre-calculated indicators on charts (no calculation logic)."""
    
    def __init__(self, chart_config):
        self.chart_config = chart_config
        if not MPLFINANCE_AVAILABLE:
            logger.warning("IndicatorRenderer initialized but mplfinance not available")
    
    def render_indicators(self,
                         plot_data: pd.DataFrame,
                         indicators: Dict[str, pd.DataFrame],
                         strategy_name: str,
                         custom_strategy: Optional[str] = None) -> List:
        """Create mplfinance addplot objects for all visible indicators."""
        if not MPLFINANCE_AVAILABLE:
            return []
        
        additional_plots = []
        theme = self.chart_config.get_theme_colors()
        visibility = self._get_indicator_visibility(strategy_name, custom_strategy)
        
        if visibility['show_bb'] and 'bb' in indicators:
            self._add_bollinger_bands(additional_plots, indicators['bb'], theme)
        
        if visibility['show_vwap'] and 'vwap' in indicators:
            self._add_vwap_bands(additional_plots, indicators['vwap'], theme)
        
        if visibility['show_rsi'] and 'rsi' in indicators:
            rsi_config = self.chart_config.get_rsi_config()
            if rsi_config.get('enabled', True):
                self._add_rsi_panel(additional_plots, indicators['rsi'], plot_data, rsi_config, theme)
        
        return additional_plots
    
    def _add_bollinger_bands(self, additional_plots: List, bb_data: pd.DataFrame, theme: Dict):
        """Add Bollinger Bands upper/lower lines to chart."""
        if not mpf:
            return
        assert mpf is not None
        additional_plots.append(mpf.make_addplot(
            bb_data['upper'], color=theme['bb_bands'], width=theme['bb_linewidth'],
            linestyle=theme['bb_linestyle'], alpha=theme['bb_alpha']
        ))
        additional_plots.append(mpf.make_addplot(
            bb_data['lower'], color=theme['bb_bands'], width=theme['bb_linewidth'],
            linestyle=theme['bb_linestyle'], alpha=theme['bb_alpha']
        ))
    
    def _add_vwap_bands(self, additional_plots: List, vwap_data: pd.DataFrame, theme: Dict):
        """Add VWAP upper/lower bands to chart."""
        if not mpf:
            return
        assert mpf is not None
        additional_plots.append(mpf.make_addplot(
            vwap_data['upper'], color=theme['vwap_bands'], width=theme['vwap_linewidth'],
            linestyle=theme['vwap_linestyle'], alpha=theme['vwap_alpha']
        ))
        additional_plots.append(mpf.make_addplot(
            vwap_data['lower'], color=theme['vwap_bands'], width=theme['vwap_linewidth'],
            linestyle=theme['vwap_linestyle'], alpha=theme['vwap_alpha']
        ))
    
    def _add_rsi_panel(self, additional_plots: List, rsi_data: pd.DataFrame, 
                      plot_data: pd.DataFrame, rsi_config: Dict, theme: Dict):
        """Add RSI indicator to panel 1 with threshold levels."""
        if not mpf:
            return
        assert mpf is not None
        additional_plots.append(mpf.make_addplot(
            rsi_data['rsi'], panel=1, color=rsi_config['line_color'],
            width=rsi_config['line_width'], ylabel='RSI'
        ))
        
        for level, color_key in [
            (rsi_config['overbought'], 'overbought_color'),
            (rsi_config['oversold'], 'oversold_color'),
            (rsi_config['midline'], 'midline_color')
        ]:
            level_series = pd.Series([level] * len(plot_data), index=plot_data.index)
            linestyle = ':' if level == rsi_config['midline'] else rsi_config['level_line_style']
            additional_plots.append(mpf.make_addplot(
                level_series, panel=1, color=rsi_config[color_key],
                width=rsi_config['level_line_width'], linestyle=linestyle,
                alpha=rsi_config['level_alpha']
            ))
    
    def _get_indicator_visibility(self, strategy_name: str, custom_strategy: Optional[str]) -> Dict[str, bool]:
        """Get indicator visibility rules from config."""
        return self.chart_config.get_indicator_visibility(
            strategy_type=strategy_name or 'mean_reversion',
            custom_strategy_name=custom_strategy
        )

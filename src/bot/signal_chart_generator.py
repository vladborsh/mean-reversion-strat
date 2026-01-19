#!/usr/bin/env python3
"""Signal Chart Generator - Orchestrates chart generation using specialized components."""

import logging
import warnings
from typing import Dict, Any, Optional
import pandas as pd

try:
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import mplfinance as mpf
    MPLFINANCE_AVAILABLE = True
except ImportError as e:
    logger = logging.getLogger(__name__)
    logger.warning(f"mplfinance not available: {e}")
    MPLFINANCE_AVAILABLE = False

from .chart import ChartDataPreparer, IndicatorRenderer, ChartRenderer

try:
    from ..indicators import Indicators
    from ..chart_config import DEFAULT_CHART_CONFIG
except ImportError:
    import sys
    import os
    sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
    from indicators import Indicators
    from chart_config import DEFAULT_CHART_CONFIG

logger = logging.getLogger(__name__)


class SignalChartGenerator:
    """Orchestrates chart generation by delegating to specialized components."""
    
    def __init__(self, chart_config=None):
        self.chart_config = chart_config or DEFAULT_CHART_CONFIG
        
        if not MPLFINANCE_AVAILABLE:
            logger.warning("SignalChartGenerator initialized but mplfinance not available")
            return
        
        size_config = self.chart_config.get_chart_size()
        self.data_preparer = ChartDataPreparer(candles_to_show=size_config['candles_to_show'])
        self.indicator_renderer = IndicatorRenderer(self.chart_config)
        self.chart_renderer = ChartRenderer(self.chart_config)
        
        theme = self.chart_config.get_theme_colors()
        logger.info(f"Chart generator initialized with {theme['mode']} theme")
    
    def generate_signal_chart(self, 
                            data: pd.DataFrame,
                            signal_data: Dict[str, Any],
                            strategy_params: Optional[Dict[str, Any]] = None,
                            indicators: Optional[Dict[str, pd.DataFrame]] = None,
                            symbol: str = "",
                            strategy_name: Optional[str] = None,
                            custom_strategy: Optional[str] = None) -> Optional[bytes]:
        """Generate chart image for trading signal. Accepts pre-calculated indicators."""
        if not MPLFINANCE_AVAILABLE:
            return None
        
        try:
            if indicators is None:
                if strategy_params is None:
                    logger.error("Either 'indicators' or 'strategy_params' required")
                    return None
                logger.warning("Calculating indicators internally is deprecated")
                indicators = self.calculate_indicators(data, strategy_params)
                if not indicators:
                    return None
            
            plot_data = self.data_preparer.prepare_chart_data(data, signal_data)
            clean_symbol = self.data_preparer.clean_symbol_name(symbol)
            
            # Align indicators with trimmed plot_data
            indicators = self._align_indicators_with_plot_data(indicators, plot_data)
            
            additional_plots = self.indicator_renderer.render_indicators(
                plot_data, indicators, strategy_name or 'mean_reversion', custom_strategy
            )
            
            self.chart_renderer.add_signal_levels(additional_plots, plot_data, signal_data)
            
            has_rsi = 'rsi' in indicators and indicators['rsi'] is not None
            chart_buffer = self.chart_renderer.render_chart(
                plot_data, additional_plots, signal_data, clean_symbol, has_rsi
            )
            
            if chart_buffer:
                logger.info(f"Chart generated for {symbol} {signal_data.get('signal_type')} signal")
            
            return chart_buffer
            
        except Exception as e:
            logger.error(f"Failed to generate chart for {symbol}: {e}", exc_info=True)
            return None
    
    def calculate_indicators(self, df: pd.DataFrame, strategy_params: Dict[str, Any]) -> Dict[str, pd.DataFrame]:
        """DEPRECATED: Calculate indicators for backward compatibility only."""
        warnings.warn(
            "calculate_indicators() is deprecated. Pass pre-calculated indicators to generate_signal_chart().",
            DeprecationWarning, stacklevel=2
        )
        
        indicators = {}
        
        try:
            bb_window = strategy_params.get('bb_window', 20)
            bb_std = strategy_params.get('bb_std', 2)
            bb_ma, bb_upper, bb_lower = Indicators.bollinger_bands(df, window=bb_window, num_std=bb_std)
            indicators['bb'] = pd.DataFrame({
                'ma': bb_ma, 'upper': bb_upper, 'lower': bb_lower
            }, index=df.index)
        except Exception as e:
            logger.error(f"Error calculating Bollinger Bands: {e}")
            return {}
        
        try:
            vwap_std = strategy_params.get('vwap_std', 2)
            vwap, vwap_upper, vwap_lower = Indicators.vwap_daily_reset_forex_compatible(
                df, num_std=vwap_std, anchor_period='day'
            )
            indicators['vwap'] = pd.DataFrame({
                'vwap': vwap, 'upper': vwap_upper, 'lower': vwap_lower
            }, index=df.index)
        except Exception as e:
            logger.error(f"Error calculating VWAP: {e}")
            return {}
        
        try:
            rsi_config = self.chart_config.get_rsi_config()
            rsi_period = rsi_config.get('period', 14)
            rsi = Indicators.rsi(df, period=rsi_period, column='close')
            indicators['rsi'] = pd.DataFrame({'rsi': rsi}, index=df.index)
        except Exception as e:
            logger.error(f"Error calculating RSI: {e}")
        
        return indicators
    
    def _align_indicators_with_plot_data(self, indicators: Dict[str, pd.DataFrame], 
                                         plot_data: pd.DataFrame) -> Dict[str, pd.DataFrame]:
        """Align indicator DataFrames with trimmed plot_data by matching indices."""
        aligned_indicators = {}
        
        for key, indicator_df in indicators.items():
            if indicator_df is None or indicator_df.empty:
                aligned_indicators[key] = indicator_df
                continue
            
            # Use loc to get only the rows that match plot_data's index
            try:
                aligned_indicators[key] = indicator_df.loc[plot_data.index]
            except KeyError:
                # If indices don't match, try to align by taking the last N rows
                aligned_df = indicator_df.tail(len(plot_data)).copy()
                aligned_df.index = plot_data.index
                aligned_indicators[key] = aligned_df
                logger.warning(f"Indicator '{key}' indices don't match plot_data, using tail() alignment")
        
        return aligned_indicators

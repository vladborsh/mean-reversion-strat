#!/usr/bin/env python3
"""
Signal Chart Generator

This module generates chart images for trading signals with candlesticks and technical indicators.
Charts are created in memory and returned as bytes for sending via Telegram.
"""

import io
import logging
from typing import Dict, Any, Optional, Tuple
import pandas as pd
import numpy as np
import matplotlib
import matplotlib.pyplot as plt
import mplfinance as mpf
from datetime import datetime

# Use non-interactive backend to avoid GUI dependencies
matplotlib.use('Agg')

# Import indicators
try:
    from ..indicators import Indicators
except ImportError:
    import sys
    import os
    sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
    from indicators import Indicators

logger = logging.getLogger(__name__)


class SignalChartGenerator:
    """Generate trading signal charts with indicators for Telegram notifications"""
    
    def __init__(self):
        """Initialize the chart generator with style settings"""
        # Define custom style for professional appearance
        self.chart_style = mpf.make_mpf_style(
            base_mpf_style='charles',
            marketcolors=mpf.make_marketcolors(
                up='#26a69a',      # Green for up candles
                down='#ef5350',    # Red for down candles
                edge='inherit',
                wick={'up': '#26a69a', 'down': '#ef5350'},
                volume='inherit',
                alpha=0.9
            ),
            gridstyle='--',
            gridcolor='#e0e0e0',
            facecolor='#ffffff',
            edgecolor='#000000',
            figcolor='#ffffff',
            y_on_right=True
        )
        
        # Chart settings
        self.candles_to_show = 100  # Show last 100 candles for better context
        self.figure_size = (12, 8)  # Size in inches for good mobile readability
        self.dpi = 100  # Resolution
        
        logger.info("Signal chart generator initialized")
    
    def calculate_indicators(self, df: pd.DataFrame, strategy_params: Dict[str, Any]) -> Dict[str, pd.DataFrame]:
        """
        Calculate technical indicators for the chart using proper indicators from indicators.py
        
        Args:
            df: OHLCV DataFrame
            strategy_params: Strategy parameters containing indicator settings
            
        Returns:
            Dictionary with calculated indicators
        """
        indicators = {}
        
        # Calculate Bollinger Bands using indicators.py
        bb_window = strategy_params.get('bb_window', 20)
        bb_std = strategy_params.get('bb_std', 2)
        
        try:
            bb_ma, bb_upper, bb_lower = Indicators.bollinger_bands(df, window=bb_window, num_std=bb_std)
            
            indicators['bb'] = pd.DataFrame({
                'ma': bb_ma,
                'upper': bb_upper,
                'lower': bb_lower
            }, index=df.index)
            
        except Exception as e:
            logger.error(f"Error calculating Bollinger Bands: {e}")
            return {}
        
        # Calculate VWAP with daily reset for forex compatibility
        vwap_std = strategy_params.get('vwap_std', 2)
        
        try:
            vwap, vwap_upper, vwap_lower = Indicators.vwap_daily_reset_forex_compatible(
                df, 
                num_std=vwap_std, 
                anchor_period='day'
            )
            
            indicators['vwap'] = pd.DataFrame({
                'vwap': vwap,
                'upper': vwap_upper,
                'lower': vwap_lower
            }, index=df.index)
            
        except Exception as e:
            logger.error(f"Error calculating VWAP: {e}")
            return {}
        
        logger.debug("Indicators calculated successfully using indicators.py methods")
        return indicators
    
    def _prepare_chart_data(self, data: pd.DataFrame, signal_data: Dict[str, Any]) -> pd.DataFrame:
        """
        Prepare chart data with optimal range for SL/TP visibility
        
        Args:
            data: Full OHLCV DataFrame
            signal_data: Signal information with entry, stop_loss, take_profit
            
        Returns:
            Optimized DataFrame for chart display
        """
        # Get signal levels
        entry_price = signal_data.get('entry_price', 0)
        stop_loss = signal_data.get('stop_loss', 0)
        take_profit = signal_data.get('take_profit', 0)
        
        # Use last N candles as base
        plot_data = data.tail(self.candles_to_show).copy()
        
        # Calculate optimal y-axis range to include SL/TP with some padding
        if entry_price > 0 and stop_loss > 0 and take_profit > 0:
            # Find min/max of signal levels
            signal_min = min(entry_price, stop_loss, take_profit)
            signal_max = max(entry_price, stop_loss, take_profit)
            
            # Get price range from data
            data_min = plot_data[['low']].min().min()
            data_max = plot_data[['high']].max().max()
            
            # Extend range to ensure SL/TP are visible
            chart_min = min(data_min, signal_min)
            chart_max = max(data_max, signal_max)
            
            # Add padding (5% of range)
            price_range = chart_max - chart_min
            padding = price_range * 0.05
            
            # Store the optimal y-limits for later use
            plot_data.attrs['y_limits'] = (chart_min - padding, chart_max + padding)
            
            logger.debug(f"Chart range optimized for SL/TP visibility: {chart_min - padding:.5f} - {chart_max + padding:.5f}")
        
        return plot_data
    
    def generate_signal_chart(self, 
                            data: pd.DataFrame,
                            signal_data: Dict[str, Any],
                            strategy_params: Dict[str, Any],
                            symbol: str) -> Optional[bytes]:
        """
        Generate a chart image for the trading signal
        
        Args:
            data: OHLCV DataFrame with datetime index
            signal_data: Signal information (entry, stop_loss, take_profit, etc.)
            strategy_params: Strategy parameters for indicators
            symbol: Trading symbol name
            
        Returns:
            Chart image as bytes buffer or None if generation fails
        """
        try:
            # Prepare data with smart selection for better SL/TP visibility
            plot_data = self._prepare_chart_data(data, signal_data)
            
            # Ensure data has proper format for mplfinance
            if not isinstance(plot_data.index, pd.DatetimeIndex):
                plot_data.index = pd.to_datetime(plot_data.index)
            
            # Calculate indicators
            indicators = self.calculate_indicators(plot_data, strategy_params)
            
            # Check if indicators calculation failed
            if not indicators:
                logger.error(f"Indicators calculation failed for {symbol} - cannot generate chart")
                return None
            
            # Prepare additional plot lines for indicators
            additional_plots = []
            
            # Add Bollinger Bands (upper and lower only)
            bb_data = indicators['bb']
            additional_plots.extend([
                mpf.make_addplot(bb_data['upper'], color='#808080', width=1, linestyle='--', alpha=0.7),
                mpf.make_addplot(bb_data['lower'], color='#808080', width=1, linestyle='--', alpha=0.7)
            ])
            
            # Add VWAP bands (upper and lower only)
            vwap_data = indicators['vwap']
            additional_plots.extend([
                mpf.make_addplot(vwap_data['upper'], color='#9932cc', width=1, linestyle=':', alpha=0.6),
                mpf.make_addplot(vwap_data['lower'], color='#9932cc', width=1, linestyle=':', alpha=0.6)
            ])
            
            # Add signal levels (entry, stop loss, take profit) as horizontal lines
            entry_price = signal_data.get('entry_price', 0)
            stop_loss = signal_data.get('stop_loss', 0)
            take_profit = signal_data.get('take_profit', 0)
            
            if entry_price > 0:
                # Create horizontal lines for signal levels with better visibility
                entry_line = pd.Series([entry_price] * len(plot_data), index=plot_data.index)
                additional_plots.append(
                    mpf.make_addplot(entry_line, color='#1f77b4', width=2.5, linestyle='-', alpha=0.9)
                )
            
            if stop_loss > 0:
                sl_line = pd.Series([stop_loss] * len(plot_data), index=plot_data.index)
                additional_plots.append(
                    mpf.make_addplot(sl_line, color='#d62728', width=2, linestyle='--', alpha=0.8)
                )
            
            if take_profit > 0:
                tp_line = pd.Series([take_profit] * len(plot_data), index=plot_data.index)
                additional_plots.append(
                    mpf.make_addplot(tp_line, color='#2ca02c', width=2, linestyle='-.', alpha=0.8)
                )
            
            # Clean symbol name for display
            clean_symbol = symbol
            if clean_symbol and clean_symbol.endswith('X'):
                # Keep X only for indices like 'DAX', 'FTMX'
                if clean_symbol not in ['DAX', 'FTMX', 'SPX', 'NDX']:
                    clean_symbol = clean_symbol[:-1]
            
            # Create the chart with optimized settings
            fig, axes = mpf.plot(
                plot_data,
                type='candle',
                style=self.chart_style,
                addplot=additional_plots,
                figsize=self.figure_size,
                title=dict(
                    title=f'{clean_symbol} - {signal_data.get("signal_type", "").upper()} Signal',
                    fontsize=16,
                    fontweight='bold'
                ),
                returnfig=True,
                volume=False,  # Don't show volume subplot
                tight_layout=True,
                scale_padding={'left': 0.05, 'right': 0.15, 'top': 0.25, 'bottom': 0.05}
            )
            
            # Apply y-axis limits if available for better SL/TP visibility
            if hasattr(plot_data, 'attrs') and 'y_limits' in plot_data.attrs:
                y_min, y_max = plot_data.attrs['y_limits']
                axes[0].set_ylim(y_min, y_max)
                logger.debug(f"Applied y-axis limits: {y_min:.5f} - {y_max:.5f}")
            
            
            # Add timestamp
            timestamp_text = f'Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC")}'
            axes[0].text(0.98, 0.02, timestamp_text,
                        transform=axes[0].transAxes,
                        fontsize=8,
                        horizontalalignment='right',
                        alpha=0.6)
            
            # Save to bytes buffer
            buffer = io.BytesIO()
            fig.savefig(buffer, format='png', dpi=self.dpi, bbox_inches='tight', 
                       facecolor='white', edgecolor='none')
            buffer.seek(0)
            
            # Clean up
            plt.close(fig)
            
            logger.info(f"Chart generated for {symbol} {signal_data.get('signal_type')} signal")
            return buffer.getvalue()
            
        except Exception as e:
            logger.error(f"Failed to generate chart for {symbol}: {e}")
            return None
    

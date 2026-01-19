#!/usr/bin/env python3
"""
Chart Renderer

This module handles pure chart rendering using mplfinance.
Responsible for creating candlestick charts and exporting to image bytes.
"""

import io
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
import pandas as pd

try:
    import matplotlib
    matplotlib.use('Agg')  # Non-interactive backend
    import matplotlib.pyplot as plt
    import mplfinance as mpf
    MPLFINANCE_AVAILABLE = True
except ImportError:
    MPLFINANCE_AVAILABLE = False
    mpf = None
    plt = None

logger = logging.getLogger(__name__)


class ChartRenderer:
    """Pure mplfinance chart rendering and image generation"""
    
    def __init__(self, chart_config):
        """
        Initialize the chart renderer
        
        Args:
            chart_config: ChartConfig instance with theme and size settings
        """
        self.chart_config = chart_config
        
        if not MPLFINANCE_AVAILABLE:
            logger.warning("ChartRenderer initialized but mplfinance not available")
            return
        
        # Get chart configuration
        theme = self.chart_config.get_theme_colors()
        size_config = self.chart_config.get_chart_size()
        
        # Create mplfinance style from theme
        self.chart_style = mpf.make_mpf_style(
            base_mpf_style='charles',
            marketcolors=mpf.make_marketcolors(
                up=theme['candle_up'],
                down=theme['candle_down'],
                edge=theme['candle_edge'],
                wick={'up': theme['candle_wick_up'], 'down': theme['candle_wick_down']},
                volume='inherit',
                alpha=theme['candle_alpha']
            ),
            gridstyle='--',
            gridcolor=theme['grid_color'],
            facecolor=theme['face_color'],
            edgecolor=theme['edge_color'],
            figcolor=theme['figure_color'],
            y_on_right=True,
            rc={
                'axes.labelcolor': theme['text_color'],
                'axes.edgecolor': theme['edge_color'],
                'xtick.color': theme['text_color'],
                'ytick.color': theme['text_color'],
                'text.color': theme['text_color']
            }
        )
        
        self.figure_size = size_config['figure_size']
        self.dpi = size_config['dpi']
        
        logger.debug(f"ChartRenderer initialized with {theme['mode']} theme")
    
    def render_chart(self,
                    plot_data: pd.DataFrame,
                    additional_plots: List,
                    signal_data: Dict[str, Any],
                    symbol: str,
                    has_rsi: bool = False) -> Optional[bytes]:
        """
        Render complete chart and return as PNG bytes
        
        Args:
            plot_data: Prepared chart data with OHLCV
            additional_plots: All mplfinance addplot objects (indicators + signals)
            signal_data: Signal information for title and levels
            symbol: Clean symbol name for display
            has_rsi: Whether RSI panel is present (affects layout)
            
        Returns:
            PNG chart as bytes or None if rendering fails
        """
        if not MPLFINANCE_AVAILABLE:
            logger.debug("Chart rendering skipped - mplfinance not available")
            return None
        
        try:
            # Get theme for styling
            theme = self.chart_config.get_theme_colors()
            
            # Adjust figure size if RSI is enabled (add 25% height for RSI panel)
            if has_rsi:
                figure_size = (self.figure_size[0], self.figure_size[1] * 1.25)
            else:
                figure_size = self.figure_size
            
            # Prepare plot kwargs
            plot_kwargs = {
                'data': plot_data,
                'type': 'candle',
                'style': self.chart_style,
                'addplot': additional_plots,
                'figsize': figure_size,
                'title': dict(
                    title=f'{symbol} - {signal_data.get("signal_type", "").upper()} Signal',
                    fontsize=16,
                    fontweight='bold',
                    color=theme['title_color']
                ),
                'returnfig': True,
                'volume': False,  # Don't show volume subplot
                'tight_layout': True,
                'scale_padding': {'left': 0.05, 'right': 0.15, 'top': 0.25, 'bottom': 0.05}
            }
            
            # Add panel ratios if RSI is shown (4:1 = 80% main chart, 20% RSI)
            if has_rsi:
                plot_kwargs['panel_ratios'] = (4, 1)
            
            # Generate chart
            fig, axes = mpf.plot(**plot_kwargs)
            
            # Apply y-axis limits if available (for SL/TP visibility)
            if hasattr(plot_data, 'attrs') and 'y_limits' in plot_data.attrs:
                y_min, y_max = plot_data.attrs['y_limits']
                axes[0].set_ylim(y_min, y_max)
                logger.debug(f"Applied y-axis limits: {y_min:.5f} - {y_max:.5f}")
            
            # Style RSI panel if present
            if has_rsi and len(axes) > 1:
                self._style_rsi_panel(axes, theme)
            
            # Add timestamp
            self._add_timestamp(axes[0], theme)
            
            # Save to bytes buffer
            chart_bytes = self._save_to_buffer(fig, theme)
            
            # Clean up
            plt.close(fig)
            
            logger.info(f"Chart rendered successfully for {symbol}")
            return chart_bytes
            
        except Exception as e:
            logger.error(f"Failed to render chart: {e}")
            return None
    
    def add_signal_levels(self,
                         additional_plots: List,
                         plot_data: pd.DataFrame,
                         signal_data: Dict[str, Any]):
        """
        Add entry, stop loss, and take profit horizontal lines to chart
        
        Args:
            additional_plots: List to append addplot objects to
            plot_data: Chart data (for creating horizontal series)
            signal_data: Signal information with price levels
        """
        if not MPLFINANCE_AVAILABLE:
            return
        
        theme = self.chart_config.get_theme_colors()
        
        # Extract signal levels
        entry_price = signal_data.get('entry_price', 0)
        stop_loss = signal_data.get('stop_loss', 0)
        take_profit = signal_data.get('take_profit', 0)
        
        # Add entry price line
        if entry_price > 0:
            entry_line = pd.Series([entry_price] * len(plot_data), index=plot_data.index)
            additional_plots.append(
                mpf.make_addplot(
                    entry_line,
                    color=theme['entry_line'],
                    width=theme['entry_linewidth'],
                    linestyle=theme['entry_linestyle'],
                    alpha=theme['entry_alpha']
                )
            )
        
        # Add stop loss line
        if stop_loss > 0:
            sl_line = pd.Series([stop_loss] * len(plot_data), index=plot_data.index)
            additional_plots.append(
                mpf.make_addplot(
                    sl_line,
                    color=theme['stop_loss'],
                    width=theme['sl_linewidth'],
                    linestyle=theme['sl_linestyle'],
                    alpha=theme['sl_alpha']
                )
            )
        
        # Add take profit line
        if take_profit > 0:
            tp_line = pd.Series([take_profit] * len(plot_data), index=plot_data.index)
            additional_plots.append(
                mpf.make_addplot(
                    tp_line,
                    color=theme['take_profit'],
                    width=theme['tp_linewidth'],
                    linestyle=theme['tp_linestyle'],
                    alpha=theme['tp_alpha']
                )
            )
        
        logger.debug(f"Added signal levels: Entry={entry_price}, SL={stop_loss}, TP={take_profit}")
    
    def _style_rsi_panel(self, axes: List, theme: Dict):
        """
        Apply styling to RSI panel (axes[1])
        
        Args:
            axes: List of matplotlib axes
            theme: Theme colors dictionary
        """
        if len(axes) < 2:
            return
        
        rsi_ax = axes[1]
        rsi_config = self.chart_config.get_rsi_config()
        
        # Set RSI y-axis limits (0-100)
        rsi_ax.set_ylim(0, 100)
        
        # Set RSI y-axis label
        rsi_ax.set_ylabel('RSI (14)', fontsize=10, color=theme['text_color'])
        
        # Style RSI panel background and grid
        rsi_ax.set_facecolor(theme['face_color'])
        rsi_ax.grid(True, color=theme['grid_color'], linestyle='--', linewidth=0.5, alpha=0.5)
        
        # Add RSI level labels on the right side
        rsi_ax.text(
            1.01, rsi_config['overbought'] / 100, f"{rsi_config['overbought']}",
            transform=rsi_ax.get_yaxis_transform(),
            fontsize=8, color=rsi_config['overbought_color'],
            va='center', ha='left'
        )
        rsi_ax.text(
            1.01, rsi_config['midline'] / 100, f"{rsi_config['midline']}",
            transform=rsi_ax.get_yaxis_transform(),
            fontsize=8, color=rsi_config['midline_color'],
            va='center', ha='left'
        )
        rsi_ax.text(
            1.01, rsi_config['oversold'] / 100, f"{rsi_config['oversold']}",
            transform=rsi_ax.get_yaxis_transform(),
            fontsize=8, color=rsi_config['oversold_color'],
            va='center', ha='left'
        )
        
        logger.debug("RSI panel styled successfully")
    
    def _add_timestamp(self, ax, theme: Dict):
        """
        Add generation timestamp to chart
        
        Args:
            ax: Main chart axis
            theme: Theme colors dictionary
        """
        timestamp_text = f'Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC")}'
        ax.text(
            0.98, 0.02, timestamp_text,
            transform=ax.transAxes,
            fontsize=8,
            horizontalalignment='right',
            alpha=0.6,
            color=theme['text_color']
        )
    
    def _save_to_buffer(self, fig, theme: Dict) -> bytes:
        """
        Save chart figure to bytes buffer
        
        Args:
            fig: Matplotlib figure
            theme: Theme colors dictionary
            
        Returns:
            PNG image as bytes
        """
        buffer = io.BytesIO()
        fig.savefig(
            buffer,
            format='png',
            dpi=self.dpi,
            bbox_inches='tight',
            facecolor=theme['figure_color'],
            edgecolor='none'
        )
        buffer.seek(0)
        return buffer.getvalue()

#!/usr/bin/env python3
"""Chart Data Preparer - Handles data preparation and formatting for chart display."""

import logging
import pandas as pd
from typing import Dict, Any, Tuple

logger = logging.getLogger(__name__)


class ChartDataPreparer:
    """Prepares and formats data for chart display."""
    
    def __init__(self, candles_to_show: int = 100):
        self.candles_to_show = candles_to_show
    
    def prepare_chart_data(self, data: pd.DataFrame, signal_data: Dict[str, Any]) -> pd.DataFrame:
        """Prepare chart data with optimal range for SL/TP visibility."""
        if not self.validate_dataframe(data):
            raise ValueError("Invalid DataFrame format")
        
        plot_data = data.tail(self.candles_to_show).copy()
        
        if not isinstance(plot_data.index, pd.DatetimeIndex):
            plot_data.index = pd.to_datetime(plot_data.index)
        
        y_limits = self.calculate_y_limits(plot_data, signal_data)
        if y_limits:
            plot_data.attrs['y_limits'] = y_limits
            logger.debug(f"Chart range: {y_limits[0]:.5f} - {y_limits[1]:.5f}")
        
        return plot_data
    
    def calculate_y_limits(self, plot_data: pd.DataFrame, signal_data: Dict[str, Any]) -> Tuple[float, float] | None:
        """Calculate optimal y-axis limits to ensure SL/TP visibility."""
        entry_price = signal_data.get('entry_price', 0)
        stop_loss = signal_data.get('stop_loss', 0)
        take_profit = signal_data.get('take_profit', 0)
        
        if not (entry_price > 0 and stop_loss > 0 and take_profit > 0):
            return None
        
        signal_min = min(entry_price, stop_loss, take_profit)
        signal_max = max(entry_price, stop_loss, take_profit)
        data_min = plot_data['low'].min()
        data_max = plot_data['high'].max()
        
        chart_min = min(data_min, signal_min)
        chart_max = max(data_max, signal_max)
        padding = (chart_max - chart_min) * 0.05
        
        return (chart_min - padding, chart_max + padding)
    
    def create_signal_level_series(self, plot_data: pd.DataFrame, price: float) -> pd.Series:
        """Create a horizontal line series for a price level."""
        return pd.Series([price] * len(plot_data), index=plot_data.index)
    
    @staticmethod
    def clean_symbol_name(symbol: str) -> str:
        """Remove trailing X from forex symbols (except indices like DAX, SPX)."""
        if not symbol or not symbol.endswith('X'):
            return symbol
        if symbol not in ['DAX', 'FTMX', 'SPX', 'NDX']:
            return symbol[:-1]
        return symbol
    
    @staticmethod
    def validate_dataframe(df: pd.DataFrame) -> bool:
        """Validate DataFrame has required format for charting."""
        if df is None or df.empty:
            logger.error("DataFrame is None or empty")
            return False
        
        required_columns = {'open', 'high', 'low', 'close'}
        if not required_columns.issubset(df.columns):
            missing = required_columns - set(df.columns)
            logger.error(f"Missing columns: {missing}")
            return False
        
        if len(df) < 2:
            logger.error("Insufficient data points")
            return False
        
        return True

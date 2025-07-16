"""
Visualization module for the mean reversion trading strategy.

This module provides functions for plotting price data, indicators, and trading orders.
It's been refactored into smaller, focused modules for better maintainability.
"""

# Import from the new modular structure
from .chart_plotters import (
    plot_price_with_indicators,
    plot_price_with_vwap_enhanced,
    plot_equity_curve,
    plot_drawdown
)

from .order_visualization import (
    plot_individual_orders,
    plot_single_order,
    save_order_plots
)

from .plot_utils import PLOTS_DIR

# Legacy compatibility functions
def plot_order_levels(ax, order_time, entry_price, stop_loss, take_profit, is_long):
    """
    Legacy function for backward compatibility.
    Converts old-style parameters to new order format and uses new implementation.
    """
    from .order_visualization import plot_order_levels_on_chart
    
    # Convert to new order format
    order = {
        'time': order_time,
        'entry': entry_price,
        'stop_loss': stop_loss,
        'take_profit': take_profit,
        'is_long': is_long
    }
    
    plot_order_levels_on_chart(ax, order)

print(f"Visualization module loaded. Plots will be saved to: {PLOTS_DIR}")

# Export all public functions for backward compatibility
__all__ = [
    'plot_price_with_indicators',
    'plot_price_with_vwap_enhanced', 
    'plot_equity_curve',
    'plot_drawdown',
    'plot_individual_orders',
    'plot_single_order',
    'save_order_plots',
    'plot_order_levels'  # Legacy compatibility
]

"""
Basic chart plotting functions for price data and indicators.
"""
import matplotlib.pyplot as plt
import pandas as pd
from .plot_utils import COLORS, FIGURE_SIZES

def plot_price_line(ax, df, label='Close', color=None, linewidth=1.5):
    """Plot price line on given axis."""
    color = color or COLORS['price']
    ax.plot(df.index, df['close'], label=label, color=color, linewidth=linewidth)

def plot_bollinger_bands(ax, df, bb, fill_alpha=0.1):
    """Plot Bollinger Bands on given axis."""
    # Fill between bands
    ax.fill_between(df.index, bb['upper'], bb['lower'], 
                   alpha=fill_alpha, color=COLORS['bb_bands'], label='BB Range')
    
    # Plot lines
    ax.plot(df.index, bb['ma'], label='BB MA', color=COLORS['bb_ma'], linewidth=1.5)
    ax.plot(df.index, bb['upper'], color=COLORS['bb_bands'], linestyle='--', alpha=0.7)
    ax.plot(df.index, bb['lower'], color=COLORS['bb_bands'], linestyle='--', alpha=0.7)

def plot_vwap_lines(ax, df, vwap, enhanced=False):
    """Plot VWAP lines on given axis."""
    if enhanced:
        # Enhanced styling with fill
        ax.fill_between(df.index, vwap['upper'], vwap['lower'], 
                       alpha=0.15, color=COLORS['vwap'], label='VWAP Range')
        ax.plot(df.index, vwap['vwap'], label='VWAP', 
               color=COLORS['vwap'], linewidth=4, alpha=0.9)
        ax.plot(df.index, vwap['upper'], color=COLORS['vwap_bands'], 
               linestyle=':', linewidth=2, alpha=0.8, label='VWAP +2σ')
        ax.plot(df.index, vwap['lower'], color=COLORS['vwap_bands'], 
               linestyle=':', linewidth=2, alpha=0.8, label='VWAP -2σ')
    else:
        # Standard styling
        ax.plot(df.index, vwap['vwap'], label='VWAP', 
               color=COLORS['vwap'], linewidth=3, alpha=0.8)
        ax.plot(df.index, vwap['upper'], label='VWAP Upper', 
               color=COLORS['vwap'], linestyle=':', linewidth=2, alpha=0.6)
        ax.plot(df.index, vwap['lower'], label='VWAP Lower', 
               color=COLORS['vwap'], linestyle=':', linewidth=2, alpha=0.6)

def plot_trading_signals(ax, signals):
    """Plot buy/sell signals on given axis."""
    if signals is None:
        return
        
    buys = signals[signals['signal'] == 'buy']
    sells = signals[signals['signal'] == 'sell']
    
    if not buys.empty:
        ax.scatter(buys.index, buys['price'], marker='^', 
                  color=COLORS['buy_signal'], label='Buy Signal', s=150, zorder=5)
    
    if not sells.empty:
        ax.scatter(sells.index, sells['price'], marker='v', 
                  color=COLORS['sell_signal'], label='Sell Signal', s=150, zorder=5)

def plot_volume_bars(ax, df):
    """Plot volume bars on given axis."""
    ax.bar(df.index, df['volume'], alpha=0.6, color=COLORS['volume'])
    ax.set_title('Volume')
    ax.set_ylabel('Volume')

def add_vwap_debug_info(ax, df, vwap):
    """Add debugging info text to chart."""
    if len(vwap['vwap'].dropna()) > 0:
        vwap_current = vwap['vwap'].iloc[-1]
        price_current = df['close'].iloc[-1]
        ax.text(0.02, 0.98, f'Current VWAP: {vwap_current:.5f}\nCurrent Price: {price_current:.5f}', 
                transform=ax.transAxes, verticalalignment='top', 
                bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))

def setup_chart_formatting(ax, title, grid=True):
    """Apply standard formatting to chart."""
    ax.set_title(title)
    ax.legend(loc='upper left')
    if grid:
        ax.grid(True, alpha=0.3)

def plot_price_with_indicators(df, bb, vwap, signals=None, orders=None):
    """Plot price with Bollinger Bands and VWAP indicators."""
    plt.figure(figsize=FIGURE_SIZES['single_chart'])
    ax = plt.gca()
    
    # Plot components
    plot_price_line(ax, df)
    plot_bollinger_bands(ax, df, bb)
    plot_vwap_lines(ax, df, vwap)
    plot_trading_signals(ax, signals)
    
    # Plot order levels if provided
    if orders is not None:
        from .order_visualization import plot_order_levels_on_chart
        for order in orders:
            plot_order_levels_on_chart(ax, order)
    
    setup_chart_formatting(ax, 'Price with Bollinger Bands and VWAP')
    plt.tight_layout()
    plt.show()

def plot_price_with_vwap_enhanced(df, bb, vwap, signals=None, orders=None):
    """Enhanced visualization with more prominent VWAP display and volume."""
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=FIGURE_SIZES['enhanced_chart'], 
                                   height_ratios=[3, 1])
    
    # Main price chart
    plot_price_line(ax1, df, linewidth=2)
    plot_bollinger_bands(ax1, df, bb)
    plot_vwap_lines(ax1, df, vwap, enhanced=True)
    plot_trading_signals(ax1, signals)
    add_vwap_debug_info(ax1, df, vwap)
    
    # Plot order levels if provided
    if orders is not None:
        from .order_visualization import plot_order_levels_on_chart
        for order in orders:
            plot_order_levels_on_chart(ax1, order)
    
    setup_chart_formatting(ax1, 'Price with Bollinger Bands and Enhanced VWAP')
    
    # Volume chart
    plot_volume_bars(ax2, df)
    
    plt.tight_layout()
    plt.show()

def plot_equity_curve(equity_curve, equity_dates=None, save_path=None):
    """Plot portfolio equity curve and save to file."""
    import os
    from datetime import datetime
    import matplotlib.dates as mdates
    from matplotlib.ticker import MaxNLocator
    
    plt.figure(figsize=FIGURE_SIZES['equity'])
    
    # Use dates for x-axis if available, otherwise use indices
    if equity_dates and len(equity_dates) == len(equity_curve):
        plt.plot(equity_dates, equity_curve, color=COLORS['price'], linewidth=2)
        # Format x-axis for better date display with 7-10 ticks maximum
        ax = plt.gca()
        
        # Determine appropriate date format based on data span
        date_span = equity_dates[-1] - equity_dates[0]
        if date_span.days > 30:
            # For longer periods, show only dates
            formatter = mdates.DateFormatter('%Y-%m-%d')
            locator = MaxNLocator(nbins=7)
        elif date_span.days > 1:
            # For multi-day periods, show date and hour
            formatter = mdates.DateFormatter('%m-%d %H:%M')
            locator = MaxNLocator(nbins=8)
        else:
            # For single day or short periods, show time
            formatter = mdates.DateFormatter('%H:%M')
            locator = MaxNLocator(nbins=10)
        
        ax.xaxis.set_major_formatter(formatter)
        ax.xaxis.set_major_locator(locator)
        
        # Reduce tick density and improve readability
        plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha='right')
        plt.xlabel('Date/Time', fontsize=12)
    else:
        plt.plot(equity_curve, color=COLORS['price'], linewidth=2)
        plt.xlabel('Time', fontsize=12)
    
    plt.title('Portfolio Value Over Time', fontsize=14, fontweight='bold')
    plt.ylabel('Portfolio Value ($)', fontsize=12)
    plt.grid(True, alpha=0.3)
    
    # Add some statistics to the plot
    if len(equity_curve) > 1:
        initial_value = equity_curve[0]
        final_value = equity_curve[-1]
        total_return = ((final_value - initial_value) / initial_value) * 100
        plt.text(0.02, 0.98, f'Total Return: {total_return:+.2f}%', 
                transform=plt.gca().transAxes, fontsize=10, 
                verticalalignment='top', bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))
    
    plt.tight_layout()
    
    if save_path:
        # Ensure directory exists
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        print(f"   📈 Equity curve saved: {save_path}")
        plt.close()  # Close to free memory
        return save_path
    else:
        # Fallback to default location
        plots_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'plots')
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        default_path = os.path.join(plots_dir, f'equity_curve_{timestamp}.png')
        os.makedirs(plots_dir, exist_ok=True)
        plt.savefig(default_path, dpi=300, bbox_inches='tight')
        print(f"   📈 Equity curve saved: {default_path}")
        plt.close()
        return default_path

def plot_drawdown(equity_curve):
    """Plot portfolio drawdown."""
    running_max = pd.Series(equity_curve).cummax()
    drawdown = (pd.Series(equity_curve) - running_max) / running_max
    
    plt.figure(figsize=FIGURE_SIZES['drawdown'])
    plt.plot(drawdown, color=COLORS['sell_signal'])
    plt.title('Drawdown Over Time')
    plt.xlabel('Time')
    plt.ylabel('Drawdown')
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.show()

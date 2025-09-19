"""
Order-specific visualization functions.
"""
import matplotlib.pyplot as plt
import pandas as pd
from math import ceil
from PIL import Image
import os
from .plot_utils import (
    COLORS, FIGURE_SIZES, create_timestamped_dir, ORDERS_PLOTS_DIR,
    calculate_risk_reward_ratio, get_order_direction, get_entry_color, 
    get_entry_marker, format_order_info
)

def plot_order_levels_on_chart(ax, order):
    """Plot order levels including entry, stop loss and take profit on existing chart."""
    color = get_entry_color(order)
    
    # Plot horizontal lines for each level
    line_length = pd.Timedelta(minutes=30)  # Adjust based on your timeframe
    ax.hlines(y=order['entry'], xmin=order['time'], xmax=order['time'] + line_length, 
             colors=color, linestyles='solid', label='Entry', linewidth=2)
    ax.hlines(y=order['stop_loss'], xmin=order['time'], xmax=order['time'] + line_length, 
             colors=COLORS['stop_loss'], linestyles=':', label='Stop Loss', linewidth=2)
    ax.hlines(y=order['take_profit'], xmin=order['time'], xmax=order['time'] + line_length, 
             colors=COLORS['take_profit'], linestyles=':', label='Take Profit', linewidth=2)
    
    # Add text labels
    ax.text(order['time'] + line_length, order['entry'], f'Entry: {order["entry"]:.5f}', 
            verticalalignment='bottom')
    ax.text(order['time'] + line_length, order['stop_loss'], f'SL: {order["stop_loss"]:.5f}', 
            verticalalignment='bottom', color=COLORS['stop_loss'])
    ax.text(order['time'] + line_length, order['take_profit'], f'TP: {order["take_profit"]:.5f}', 
            verticalalignment='bottom', color=COLORS['take_profit'])

def get_order_window_data(df, order, window_size):
    """Get data window around an order."""
    try:
        # Try to find the closest timestamp in the dataframe
        order_time = pd.to_datetime(order['time'])

        # Make sure both timestamps have same timezone awareness
        if df.index.tz is not None and order_time.tz is None:
            # Make order_time timezone aware (assuming UTC)
            order_time = order_time.tz_localize('UTC')
        elif df.index.tz is None and order_time.tz is not None:
            # Make order_time timezone naive
            order_time = order_time.tz_localize(None)

        # Find the nearest index if exact match not found
        if order_time in df.index:
            order_idx = df.index.get_loc(order_time)
        else:
            # Get the nearest timestamp
            time_diff = abs(df.index - order_time)
            order_idx = time_diff.argmin()
    except Exception as e:
        # Fallback to middle of data if we can't find the order
        print(f"Warning: Could not locate order time {order['time']}: {e}")
        order_idx = len(df) // 2

    start_idx = max(0, order_idx - window_size)
    end_idx = min(len(df), order_idx + window_size)
    return df.iloc[start_idx:end_idx]

def plot_single_order_chart(ax, df, order, window_size=50):
    """Plot a single order on the given axis - clean version with only price and SL/TP levels."""
    # Get data window around the order
    window_data = get_order_window_data(df, order, window_size)

    # Plot candlesticks
    from matplotlib.patches import Rectangle

    # Define candlestick colors
    up_color = '#00ff88'    # Green for bullish candles
    down_color = '#ff4444'  # Red for bearish candles
    wick_color = '#333333'  # Dark gray for wicks

    # Calculate candle width based on time interval
    if len(window_data) > 1:
        time_delta = window_data.index[1] - window_data.index[0]
        candle_width = time_delta * 0.6  # 60% of time interval
    else:
        candle_width = pd.Timedelta(minutes=3)  # Default width

    for i, (timestamp, row) in enumerate(window_data.iterrows()):
        open_price = row['open']
        high_price = row['high']
        low_price = row['low']
        close_price = row['close']

        # Determine candle color
        color = up_color if close_price >= open_price else down_color

        # Draw the wick (high-low line)
        ax.plot([timestamp, timestamp], [low_price, high_price],
               color=wick_color, linewidth=1, alpha=0.8)

        # Draw the body (open-close rectangle)
        body_bottom = min(open_price, close_price)
        body_height = abs(close_price - open_price)

        # Create rectangle for candle body
        rect = Rectangle((timestamp - candle_width/2, body_bottom),
                        candle_width, body_height,
                        facecolor=color, edgecolor=wick_color,
                        linewidth=0.5, alpha=0.8)
        ax.add_patch(rect)

    # Plot order levels
    entry_color = get_entry_color(order)

    # Plot horizontal lines for levels
    ax.axhline(y=order['entry'], color=entry_color, linestyle='-',
              linewidth=2, alpha=0.8)
    ax.axhline(y=order['stop_loss'], color=COLORS['stop_loss'],
              linestyle='--', linewidth=1.5, alpha=0.7)
    ax.axhline(y=order['take_profit'], color=COLORS['take_profit'],
              linestyle='--', linewidth=1.5, alpha=0.7)

    # Add entry point marker - use the closest available timestamp in the window
    order_time = pd.to_datetime(order['time'])

    # Make sure both timestamps have same timezone awareness
    if window_data.index.tz is not None and order_time.tz is None:
        order_time = order_time.tz_localize('UTC')
    elif window_data.index.tz is None and order_time.tz is not None:
        order_time = order_time.tz_localize(None)

    if order_time in window_data.index:
        marker_time = order_time
    else:
        # Find closest time in window data
        time_diff = abs(window_data.index - order_time)
        marker_time = window_data.index[time_diff.argmin()]

    ax.scatter(marker_time, order['entry'],
              marker=get_entry_marker(order),
              color=entry_color, s=100, zorder=5)

    # Add minimal text labels for levels
    y_pos = ax.get_ylim()[1]
    y_range = ax.get_ylim()[1] - ax.get_ylim()[0]

    # Position labels at the right edge
    x_pos = window_data.index[-1]

    ax.text(x_pos, order['entry'], f' Entry: {order["entry"]:.5f}',
            ha='left', va='center', fontsize=8, color=entry_color)
    ax.text(x_pos, order['stop_loss'], f' SL: {order["stop_loss"]:.5f}',
            ha='left', va='center', fontsize=8, color=COLORS['stop_loss'])
    ax.text(x_pos, order['take_profit'], f' TP: {order["take_profit"]:.5f}',
            ha='left', va='center', fontsize=8, color=COLORS['take_profit'])

    # Add outcome if trade completed
    if 'trade_outcome' in order:
        outcome = order['trade_outcome']
        outcome_type = outcome.get('type', 'unknown')
        pnl = outcome.get('pnl', 0)

        # Create simple outcome text
        if outcome_type == 'take_profit':
            outcome_text = f'✓ TP Hit (+${pnl:.2f})'
            outcome_color = 'green'
        elif outcome_type == 'stop_loss':
            outcome_text = f'✗ SL Hit (${pnl:.2f})'
            outcome_color = 'red'
        else:
            outcome_text = f'Closed (${pnl:.2f})'
            outcome_color = 'gray'

        ax.text(0.02, 0.98, outcome_text,
                transform=ax.transAxes,
                verticalalignment='top',
                fontsize=9, color=outcome_color,
                bbox=dict(boxstyle='round', facecolor='white', alpha=0.7))

    # Set y-axis limits with some padding
    price_range = max(abs(order['take_profit'] - order['entry']),
                     abs(order['stop_loss'] - order['entry']))
    ax.set_ylim(min(window_data['close'].min(), order['stop_loss']) - price_range * 0.2,
               max(window_data['close'].max(), order['take_profit']) + price_range * 0.2)

    return window_data

def plot_individual_orders(df, orders, window_size=50):
    """Plot each order in a separate subplot with detailed price action around entry point."""
    if not orders:
        return
        
    # Calculate subplot layout
    n_orders = len(orders)
    n_cols = 2
    n_rows = ceil(n_orders / n_cols)
    
    # Create figure
    fig = plt.figure(figsize=(FIGURE_SIZES['order_grid'][0], 
                             FIGURE_SIZES['order_grid'][1] * n_rows))
    fig.suptitle('Individual Order Analysis', fontsize=16, y=0.95)
    
    for idx, order in enumerate(orders, 1):
        ax = plt.subplot(n_rows, n_cols, idx)
        
        # Plot order
        plot_single_order_chart(ax, df, order, window_size)
        
        # Format plot
        ax.set_title(f'Order {idx} at {order["time"].strftime("%Y-%m-%d %H:%M")}')
        ax.legend(loc='upper right')
        ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.show()

def plot_single_order(df, order, window_size=50, save_path=None):
    """Create and optionally save a plot for a single order."""
    fig = plt.figure(figsize=FIGURE_SIZES['single_order'])
    ax = plt.gca()
    
    # Plot order
    plot_single_order_chart(ax, df, order, window_size)
    
    # Format plot
    ax.set_title(f'Order at {order["time"].strftime("%Y-%m-%d %H:%M")}')
    ax.legend(loc='upper right')
    ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    
    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches='tight')
        plt.close()
    else:
        plt.show()

def create_combined_order_image(plot_paths, output_dir):
    """Combine individual order plots into a grid image."""
    if not plot_paths:
        return None
        
    print(f"Combining {len(plot_paths)} plots into grid...")
    
    n_cols = 2
    n_rows = ceil(len(plot_paths) / n_cols)
    
    # Open all images
    images = [Image.open(path) for path in plot_paths]
    
    # Get max dimensions
    max_width = max(img.width for img in images)
    max_height = max(img.height for img in images)
    
    # Create combined image
    combined = Image.new('RGB', (max_width * n_cols, max_height * n_rows), 'white')
    
    # Paste images into grid
    for idx, img in enumerate(images):
        row = idx // n_cols
        col = idx % n_cols
        combined.paste(img, (col * max_width, row * max_height))
        img.close()
    
    # Save combined image
    combined_path = os.path.join(output_dir, 'all_orders.png')
    combined.save(combined_path, quality=95)
    combined.close()
    
    return combined_path

def save_order_plots(df, orders, output_dir=None, window_size=50):
    """Save individual plots for each order and create a combined image."""
    print(f"\nStarting save_order_plots with {len(orders)} orders")
    
    if output_dir is None:
        output_dir = ORDERS_PLOTS_DIR
    
    # Create timestamp-based subdirectory to avoid overwriting
    output_dir = create_timestamped_dir(output_dir)
    print(f"Will save plots to: {output_dir}")
    
    # Save individual plots
    plot_paths = []
    print("📊 Generating order plots: ", end="", flush=True)
    for i, order in enumerate(orders, 1):
        # Show progress dots instead of verbose messages
        if i % max(1, len(orders) // 10) == 0 or i == len(orders):
            print("●", end="", flush=True)
        plot_path = os.path.join(output_dir, f'order_{i}.png')
        plot_single_order(df, order, window_size=window_size, save_path=plot_path)
        plot_paths.append(plot_path)
    print(f" [{len(orders)}/{len(orders)}] ✅")
    
    # Combine plots into a grid
    combined_path = create_combined_order_image(plot_paths, output_dir)
    
    if combined_path:
        # Clean up individual files if needed
        for path in plot_paths:
            os.remove(path)
        
        print(f"Order plots saved to: {combined_path}")
        return combined_path
    
    return None

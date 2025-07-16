"""
Plotting utilities and configuration for the visualization module.
"""
import os
from datetime import datetime

# Define default paths for plots
PLOTS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'plots')
ORDERS_PLOTS_DIR = os.path.join(PLOTS_DIR, 'orders')

# Color scheme for consistent styling
COLORS = {
    'price': 'black',
    'bb_ma': 'blue',
    'bb_bands': 'blue',
    'vwap': 'purple',
    'vwap_bands': 'magenta',
    'buy_signal': 'green',
    'sell_signal': 'red',
    'long_entry': 'green',
    'short_entry': 'red',
    'stop_loss': 'red',
    'take_profit': 'blue',
    'volume': 'gray'
}

# Default figure sizes
FIGURE_SIZES = {
    'single_chart': (14, 7),
    'enhanced_chart': (14, 10),
    'order_grid': (15, 5),
    'single_order': (10, 6),
    'equity': (12, 5),
    'drawdown': (12, 4)
}

def create_timestamped_dir(base_dir):
    """Create a timestamped directory to avoid overwriting files."""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_dir = os.path.join(base_dir, timestamp)
    
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    return output_dir

def calculate_risk_reward_ratio(order):
    """Calculate risk/reward ratio for an order."""
    risk = abs(order['entry'] - order['stop_loss'])
    reward = abs(order['take_profit'] - order['entry'])
    return reward / risk if risk != 0 else 0

def get_order_direction(order):
    """Get order direction as string."""
    return 'LONG' if order['is_long'] else 'SHORT'

def get_entry_color(order):
    """Get entry color based on order direction."""
    return COLORS['long_entry'] if order['is_long'] else COLORS['short_entry']

def get_entry_marker(order):
    """Get entry marker based on order direction."""
    return '^' if order['is_long'] else 'v'

def format_order_info(order):
    """Format order information for display, including deposit changes if available."""
    direction = get_order_direction(order)
    rr_ratio = calculate_risk_reward_ratio(order)
    
    info_text = (
        f"{direction} Order\n"
        f"Entry: {order['entry']:.5f}\n"
        f"Stop Loss: {order['stop_loss']:.5f}\n"
        f"Take Profit: {order['take_profit']:.5f}\n"
        f"Risk/Reward: {rr_ratio:.2f}"
    )
    
    # Add position size if available
    if 'position_size' in order:
        info_text += f"\nPosition Size: {order['position_size']:,} units"
    
    # Add risk amount if available
    if 'risk_amount' in order:
        info_text += f"\nRisk Amount: ${order['risk_amount']:.2f}"
    
    # Add account risk percentage if available
    if 'account_risk_pct' in order:
        info_text += f"\nAccount Risk: {order['account_risk_pct']:.1f}%"
    
    # Add trade outcome if available
    if 'trade_outcome' in order:
        outcome = order['trade_outcome']
        if outcome['type'] == 'stop_loss':
            info_text += f"\n\n--- TRADE COMPLETED ---"
            info_text += f"\nResult: STOP LOSS"
            info_text += f"\nExit Price: {outcome['exit_price']:.5f}"
            info_text += f"\nReal P&L: ${outcome['pnl']:.2f}"
            info_text += f"\nDeposit Before: ${outcome['deposit_before']:,.2f}"
            info_text += f"\nDeposit After: ${outcome['deposit_after']:,.2f}"
            info_text += f"\nDeposit Change: ${outcome['deposit_change']:+.2f}"
        elif outcome['type'] == 'take_profit':
            info_text += f"\n\n--- TRADE COMPLETED ---"
            info_text += f"\nResult: TAKE PROFIT"
            info_text += f"\nExit Price: {outcome['exit_price']:.5f}"
            info_text += f"\nReal P&L: ${outcome['pnl']:.2f}"
            info_text += f"\nDeposit Before: ${outcome['deposit_before']:,.2f}"
            info_text += f"\nDeposit After: ${outcome['deposit_after']:,.2f}"
            info_text += f"\nDeposit Change: ${outcome['deposit_change']:+.2f}"
        elif outcome['type'] == 'manual_close':
            info_text += f"\n\n--- TRADE COMPLETED ---"
            info_text += f"\nResult: MANUAL CLOSE"
            info_text += f"\nExit Price: {outcome['exit_price']:.5f}"
            info_text += f"\nReal P&L: ${outcome['pnl']:.2f}"
            info_text += f"\nDeposit Before: ${outcome['deposit_before']:,.2f}"
            info_text += f"\nDeposit After: ${outcome['deposit_after']:,.2f}"
            info_text += f"\nDeposit Change: ${outcome['deposit_change']:+.2f}"
    
    return info_text

print(f"Plot utilities loaded. Plots will be saved to: {PLOTS_DIR}")

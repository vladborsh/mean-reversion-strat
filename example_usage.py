"""
Example usage of different configuration profiles.

Shows how to select appropriate configuration for your trading scenario.
"""

from src.config import Config


def show_config_modes():
    """Display different configuration modes."""

    print("=" * 80)
    print("CONFIGURATION MODES")
    print("=" * 80)

    modes = {
        'backtest': 'Backtesting Mode',
        'live': 'Live Trading Mode',
        'conservative': 'Conservative Mode'
    }

    for mode_key, mode_name in modes.items():
        # Reset to default before applying mode
        Config.__init__ = Config.__init__.__get__(Config, Config.__class__)
        Config.set_mode(mode_key)

        portfolio_config = Config.get_portfolio_config()
        risk_config = Config.get_risk_config()

        print(f"\n{mode_name} (Config.set_mode('{mode_key}')):")
        print("-" * 40)
        print(f"  Portfolio Manager: {'ENABLED' if portfolio_config['enabled'] else 'DISABLED'}")
        print(f"  Trailing Stops: {'ENABLED' if portfolio_config['enable_trailing_stops'] else 'DISABLED'}")
        print(f"  Max Portfolio Risk: {portfolio_config['max_portfolio_risk_pct']}%")
        print(f"  Max Concurrent Positions: {portfolio_config['max_concurrent_positions']}")
        print(f"  Max Drawdown Limit: {portfolio_config['max_drawdown_pct']}%")
        print(f"  Daily Loss Limit: {portfolio_config['daily_loss_limit_pct']}%")
        print(f"  Risk Per Position: {risk_config['risk_per_position_pct']}%")
        print(f"  Stop Loss ATR: {risk_config['stop_loss_atr_multiplier']}x")


def example_single_asset_backtest():
    """Example: Setting up for single asset backtesting."""
    print("\n" + "=" * 80)
    print("EXAMPLE: Single Asset Backtesting Setup")
    print("=" * 80)

    # Import the configuration
    from src.config import Config
    from src.strategy import MeanReversionStrategy

    print("\nUsing Config in backtest mode:")
    print("- Portfolio Manager: ENABLED")
    print("- Trailing Stops: ENABLED")
    print("- Standard risk settings for testing")

    print("\nCode example:")
    print("```python")
    print("from src.config import Config")
    print("from src import strategy")
    print("")
    print("# Set mode for backtesting")
    print("Config.set_mode('backtest')")
    print("")
    print("# Access configuration")
    print("risk_config = Config.get_risk_config()")
    print("portfolio_config = Config.get_portfolio_config()")
    print("# Then run your backtest...")
    print("```")


def example_multi_asset_backtest():
    """Example: Setting up for multi-asset backtesting."""
    print("\n" + "=" * 80)
    print("EXAMPLE: Multi-Asset Backtesting Setup (7 Assets)")
    print("=" * 80)

    print("\nUsing Config for multi-asset backtesting:")
    print("- Portfolio Manager: ENABLED")
    print("- Trailing Stops: ENABLED")
    print("- Max 4 concurrent positions")
    print("- 12% portfolio drawdown circuit breaker")

    print("\nCode example:")
    print("```python")
    print("from src.config import Config")
    print("from src import strategy")
    print("")
    print("# Use backtest mode (default settings)")
    print("Config.set_mode('backtest')")
    print("")
    print("# Or customize specific settings")
    print("Config.PORTFOLIO_LIMITS['max_concurrent_positions'] = 4")
    print("# Run backtest with multiple assets...")
    print("```")


def example_live_trading():
    """Example: Setting up for live trading."""
    print("\n" + "=" * 80)
    print("EXAMPLE: Live Trading Setup")
    print("=" * 80)

    print("\nUsing Config in live mode:")
    print("- Portfolio Manager: ALWAYS ENABLED (safety critical)")
    print("- Trailing Stops: ENABLED")
    print("- More conservative risk settings:")
    print("  - 0.5% risk per position (vs 1% in backtest)")
    print("  - 10% max drawdown (vs 12% in backtest)")
    print("  - 1.5% daily loss limit (vs 2% in backtest)")

    print("\nCode example:")
    print("```python")
    print("from src.config import Config")
    print("")
    print("# Set live trading mode")
    print("Config.set_mode('live')")
    print("")
    print("# Further customize if needed")
    print("Config.PORTFOLIO_LIMITS['max_concurrent_positions'] = 2  # Even safer")
    print("```")


def main():
    """Run all examples."""
    show_config_modes()
    example_single_asset_backtest()
    example_multi_asset_backtest()
    example_live_trading()

    print("\n" + "=" * 80)
    print("KEY TAKEAWAYS")
    print("=" * 80)
    print("""
1. SINGLE CONFIGURATION FILE:
   - All settings in one place: src/config.py
   - Clear, well-documented parameters
   - Easy to understand and modify

2. TRADING MODES:
   - 'backtest': Standard settings for testing
   - 'live': Conservative settings for real trading
   - 'conservative': Ultra-safe settings

3. CUSTOMIZATION:
   - Use Config.set_mode() for presets
   - Directly modify Config.PARAMETER_NAME for fine control
   - All changes are global and immediate

4. USAGE:
   from src.config import Config
   Config.set_mode('live')  # or 'backtest', 'conservative'
   # Access any config:
   risk = Config.RISK_MANAGEMENT['risk_per_position_pct']
    """)


if __name__ == "__main__":
    main()
#!/usr/bin/env python3
import argparse
from dotenv import load_dotenv
import os
import pandas as pd

# Load environment variables from .env file
load_dotenv()

from src.data_fetcher import DataFetcher
from src.indicators import Indicators
from src.strategy import MeanReversionStrategy
from src.backtest import run_backtest
from src.metrics import calculate_metrics
from src.optimize import grid_search
from src.strategy_config import DEFAULT_CONFIG, AggressiveConfig, ConservativeConfig
from src.visualization import (
    plot_price_with_indicators, 
    plot_equity_curve, 
    plot_drawdown,
    save_order_plots
)

# Store transport types globally so they can be accessed by DataFetcher and other components
TRANSPORT_CONFIG = {
    'cache_transport': 'local',
    'log_transport': 'local'
}

def generate_visualizations(df, bb, vwap_dict, equity_curve, equity_dates, order_log):
    """Generate and save all strategy visualizations with minimal console output"""
    try:
        print("📊 Generating visualizations...")
        
        # Use the same subset for both data and indicators
        plot_data = df.tail(500)
        plot_bb = {k: v.tail(500) if hasattr(v, 'tail') else v for k, v in bb.items()}
        plot_vwap = {k: v.tail(500) if hasattr(v, 'tail') else v for k, v in vwap_dict.items()}
        
        # Generate main plots
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        plots_dir = os.path.join(os.path.dirname(__file__), 'plots')
        
        # Save equity curve plot
        if equity_curve and len(equity_curve) > 1:
            equity_path = os.path.join(plots_dir, f'equity_curve_{timestamp}.png')
            plot_equity_curve(equity_curve, equity_dates, save_path=equity_path)
        else:
            print("⚠️  No equity curve data available for plotting")
        
        # plot_price_with_indicators(plot_data, plot_bb, plot_vwap)
        
        # Process and save order plots
        if order_log:
            print(f"💹 Processing {len(order_log)} orders...")
            # Convert order_log to the format expected by save_order_plots
            formatted_orders = []
            for order in order_log:
                try:
                    formatted_order = {
                        'time': pd.to_datetime(f"{order['date']} {order['time']}"),
                        'entry': float(order['entry_price']),
                        'stop_loss': float(order['stop_loss']),
                        'take_profit': float(order['take_profit']),
                        'is_long': order['type'].lower() == 'buy',
                        'position_size': order.get('position_size', 0),
                        'risk_amount': order.get('risk_amount', 0),
                        'account_risk_pct': order.get('account_risk_pct', 0)
                    }
                    
                    # Add trade outcome if available
                    if 'trade_outcome' in order:
                        formatted_order['trade_outcome'] = order['trade_outcome']
                    
                    formatted_orders.append(formatted_order)
                except Exception as e:
                    print(f"⚠️  Warning: Could not format order - {e}")
            
            # Save the order plots
            combined_image_path = save_order_plots(
                df=df,
                orders=formatted_orders,
                window_size=50  # Show 50 candles around each entry
            )
            print(f"✅ Visualizations saved successfully")
            print(f"   📈 Order analysis: {combined_image_path}")
        else:
            print("✅ Visualizations saved (no orders to plot)")
            
    except Exception as e:
        print(f"❌ Visualization error: {e}")
        import traceback
        traceback.print_exc()

def run_strategy(df, config_class=None, timeframe='15m'):
    """Run the complete strategy pipeline with configurable parameters"""
    if config_class is None:
        config_class = DEFAULT_CONFIG
    
    # Get strategy parameters from configuration
    params = config_class.get_backtrader_params()
    risk_config = config_class.get_risk_config()
    
    # Add timeframe to parameters for order lifetime calculation
    params['timeframe'] = timeframe
    
    print(f"\n=== RUNNING STRATEGY: {config_class.__name__.upper()} ===")
    print(f"⏱️  Timeframe: {timeframe} | Risk: {risk_config['risk_per_position_pct']}% | Leverage: {risk_config.get('leverage', 100.0)}:1")
    
    # Calculate indicators
    bb_window = params['bb_window']
    bb_std = params['bb_std']
    vwap_window = params['vwap_window']
    vwap_std = params['vwap_std']
    vwap_anchor = params['vwap_anchor']
    
    bb_ma, bb_upper, bb_lower = Indicators.bollinger_bands(df, window=bb_window, num_std=bb_std)
    # Use the forex-compatible VWAP with configurable anchor period
    vwap, vwap_upper, vwap_lower = Indicators.vwap_daily_reset_forex_compatible(
        df, 
        num_std=vwap_std,
        anchor_period=vwap_anchor
    )
    bb = {'ma': bb_ma, 'upper': bb_upper, 'lower': bb_lower}
    vwap_dict = {'vwap': vwap, 'upper': vwap_upper, 'lower': vwap_lower}

    # Backtest with leverage
    leverage = risk_config.get('leverage', 100.0)  # Default 100:1 leverage for forex
    
    print("🔄 Running backtest...")
    equity_curve, equity_dates, trade_log, order_log = run_backtest(df, MeanReversionStrategy, params, leverage=leverage)

    # Metrics
    metrics = calculate_metrics(trade_log, equity_curve)
    
    # Calculate final balance and PnL
    initial_balance = equity_curve[0] if len(equity_curve) > 0 else 0
    final_balance = equity_curve[-1] if len(equity_curve) > 0 else 0
    final_pnl = final_balance - initial_balance
    
    # Print detailed results
    print("\n=== STRATEGY PERFORMANCE ===")
    print(f"Final Balance: ${final_balance:,.2f}")
    print(f"Final PnL: ${final_pnl:+,.2f}")
    print(f"Win Rate: {metrics.get('win_rate', 0):.2%}")
    print(f"Total Return: {metrics.get('total_return', 0):.2%}")
    print(f"Sharpe Ratio: {metrics.get('sharpe_ratio', 0):.2f}")
    print(f"Max Drawdown: {metrics.get('max_drawdown', 0):.2%}")
    print(f"Avg Return per Trade: ${metrics.get('avg_return_per_trade', 0):.2f}")
    print(f"Volatility: {metrics.get('volatility', 0):.2%}")
    print(f"Total Trades: {len([t for t in trade_log if t.get('type') == 'exit'])}")
    
    # Generate visualizations
    generate_visualizations(df, bb, vwap_dict, equity_curve, equity_dates, order_log)
    
    return equity_curve, trade_log, metrics

# Example usage
if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Mean Reversion Strategy Backtesting',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py
  python main.py --cache-transport s3 --log-transport s3
  python main.py --cache-transport local --log-transport s3 --symbol GBPUSD=X
        """
    )
    
    # Transport configuration
    parser.add_argument('--cache-transport', default='local',
                       choices=['local', 's3'],
                       help='Cache transport type (default: local)')
    parser.add_argument('--log-transport', default='local',
                       choices=['local', 's3'],
                       help='Log transport type (default: local)')
    
    # Trading parameters
    parser.add_argument('--symbol', default='EURUSD=X',
                       help='Trading symbol (default: EURUSD=X)')
    parser.add_argument('--timeframe', default='15m',
                       help='Data timeframe (default: 15m)')
    parser.add_argument('--years', type=int, default=1,
                       help='Years of historical data (default: 1)')
    parser.add_argument('--use-cache', action='store_true', default=False,
                       help='Enable data caching (default: disabled)')
    
    args = parser.parse_args()
    
    # Update global transport configuration
    TRANSPORT_CONFIG['cache_transport'] = args.cache_transport
    TRANSPORT_CONFIG['log_transport'] = args.log_transport
    
    print("📈 Fetching data...")
    print(f"🔧 Cache Transport: {args.cache_transport}")
    print(f"📊 Log Transport: {args.log_transport}")
    
    # Fetch data with specified configuration
    fetcher = DataFetcher(
        source='forex', 
        symbol=args.symbol, 
        timeframe=args.timeframe, 
        use_cache=args.use_cache,
        cache_transport_type=args.cache_transport
    )
    df = fetcher.fetch(years=args.years)
    print(f"✅ Data loaded: {len(df)} rows ({df.index[0].strftime('%Y-%m-%d')} to {df.index[-1].strftime('%Y-%m-%d')})")

    # Run strategy with 1% risk management (default configuration)
    print("\n" + "="*60)
    print("🎯 MEAN REVERSION STRATEGY - 1% RISK MANAGEMENT")
    print("="*60)
    
    try:
        equity_curve, trade_log, metrics = run_strategy(df, DEFAULT_CONFIG, timeframe=args.timeframe)
        
        print(f"\n{'='*20} FINAL RESULTS {'='*20}")
        print(f"Strategy Performance with 1% Risk per Trade:")
        print(f"- Win Rate: {metrics.get('win_rate', 0):.2%}")
        print(f"- Total Return: {metrics.get('total_return', 0):.2%}")
        print(f"- Sharpe Ratio: {metrics.get('sharpe_ratio', 0):.2f}")
        print(f"- Maximum Drawdown: {metrics.get('max_drawdown', 0):.2%}")
        print(f"- Average Return per Trade: ${metrics.get('avg_return_per_trade', 0):.2f}")
        print(f"- Volatility: {metrics.get('volatility', 0):.2%}")
        print(f"- Total Trades: {len([t for t in trade_log if t.get('type') == 'exit'])}")
        
    except Exception as e:
        print(f"❌ Error running strategy: {e}")
        import traceback
        traceback.print_exc()

    # Display cache information
    cache_status = "enabled" if args.use_cache else "disabled"
    print(f"\n💡 Data caching is {cache_status}")
    if not args.use_cache:
        print("   To enable caching for faster subsequent runs, use --use-cache")
    
    print(f"📁 Cache transport: {args.cache_transport}")
    print(f"📊 Log transport: {args.log_transport}")

    # Hyperparameter optimization example (commented out for now)
    # print("\nRunning hyperparameter optimization...")
    # param_grid = {
    #     'bb_window': [15, 20, 25],
    #     'bb_std': [1.5, 2.0, 2.5],
    #     'vwap_window': [15, 20, 25],
    #     'vwap_std': [1.5, 2.0, 2.5],
    #     'atr_period': [10, 14, 20]
    # }
    # best_params, best_metrics = grid_search(param_grid, df, MeanReversionStrategy)
    # print('\nOptimal Parameters:', best_params)
    # print('Optimal Metrics:', best_metrics)

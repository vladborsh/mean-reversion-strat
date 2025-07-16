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

def generate_visualizations(df, bb, vwap_dict, equity_curve, order_log):
    """Generate and save all strategy visualizations with minimal console output"""
    try:
        print("📊 Generating visualizations...")
        
        # Use the same subset for both data and indicators
        plot_data = df.tail(500)
        plot_bb = {k: v.tail(500) if hasattr(v, 'tail') else v for k, v in bb.items()}
        plot_vwap = {k: v.tail(500) if hasattr(v, 'tail') else v for k, v in vwap_dict.items()}
        
        # Generate main plots
        # plot_price_with_indicators(plot_data, plot_bb, plot_vwap)
        # plot_equity_curve(equity_curve)
        # plot_drawdown(equity_curve)
        
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
    equity_curve, trade_log, order_log = run_backtest(df, MeanReversionStrategy, params, leverage=leverage)

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
    generate_visualizations(df, bb, vwap_dict, equity_curve, order_log)
    
    return equity_curve, trade_log, metrics

# Example usage
if __name__ == '__main__':
    print("📈 Fetching EUR/USD data...")
    # Fetch data with caching enabled (default)
    # First run will fetch from API and cache, subsequent runs will use cache
    fetcher = DataFetcher(source='forex', symbol='EURUSD=X', timeframe='15m', use_cache=True)
    df = fetcher.fetch(years=1)
    print(f"✅ Data loaded: {len(df)} rows ({df.index[0].strftime('%Y-%m-%d')} to {df.index[-1].strftime('%Y-%m-%d')})")

    # Show cache information
    cache_info = fetcher.get_cache_info()
    print(f"💾 Cache: {cache_info['total_files']} files, {cache_info['total_size_mb']:.1f} MB")

    # Run strategy with 1% risk management (default configuration)
    print("\n" + "="*60)
    print("🎯 MEAN REVERSION STRATEGY - 1% RISK MANAGEMENT")
    print("="*60)
    
    try:
        equity_curve, trade_log, metrics = run_strategy(df, DEFAULT_CONFIG, timeframe='15m')
        
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

    # Demonstrate cache performance
    print(f"\n💡 Pro tip: Run this script again to see caching in action!")
    
    # Uncomment to clear cache if needed
    # print(f"\n🗑️  Clearing cache...")
    # fetcher.clear_cache()

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

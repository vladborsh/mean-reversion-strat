#!/usr/bin/env python3
"""
Generate PNL charts for optimized configurations

This script loads best configurations from analyze_batch_results.py output,
matches them to order files using parameter comparison, aggregates orders
chronologically, calculates cumulative PNL, and generates equity curve charts.
"""
import pandas as pd
import numpy as np
import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import argparse
from datetime import datetime
import sys

import sys

# Add src to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from src.chart_plotters import plot_equity_curve


class ConfigPNLGenerator:
    """Generate PNL charts for optimized configurations"""
    
    def __init__(self, orders_dir: str = 'optimization/orders', 
                 output_dir: str = 'plots/pnl_curves'):
        self.orders_dir = Path(orders_dir)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
    def match_orders_to_config(self, orders_df: pd.DataFrame, config: Dict, 
                               tolerance: float = 1e-9) -> pd.DataFrame:
        """
        Match orders to a specific config by comparing parameter values
        
        Args:
            orders_df: DataFrame with all orders for an asset
            config: Configuration dict from best_configs
            tolerance: Floating-point comparison tolerance
            
        Returns:
            Filtered DataFrame with only matching orders
        """
        # Extract parameters from config
        bb_window = config['BOLLINGER_BANDS']['window']
        bb_std = config['BOLLINGER_BANDS']['std_dev']
        vwap_window = config['VWAP_BANDS']['window']
        vwap_std = config['VWAP_BANDS']['std_dev']
        risk_per_pos = config['RISK_MANAGEMENT']['risk_per_position_pct']
        stop_loss_atr = config['RISK_MANAGEMENT']['stop_loss_atr_multiplier']
        risk_reward = config['RISK_MANAGEMENT']['risk_reward_ratio']
        require_reversal = config['STRATEGY_BEHAVIOR'].get('require_reversal', False)
        
        # Build filter mask with tolerance for float comparisons
        mask = (
            (orders_df['bb_window'] == bb_window) &
            (np.isclose(orders_df['bb_std'], bb_std, rtol=tolerance)) &
            (orders_df['vwap_window'] == vwap_window) &
            (np.isclose(orders_df['vwap_std'], vwap_std, rtol=tolerance)) &
            (np.isclose(orders_df['risk_per_position_pct'], risk_per_pos, rtol=tolerance)) &
            (np.isclose(orders_df['stop_loss_atr_multiplier'], stop_loss_atr, rtol=tolerance)) &
            (np.isclose(orders_df['risk_reward_ratio_param'], risk_reward, rtol=tolerance)) &
            (orders_df['require_reversal'] == require_reversal)
        )
        
        matched_orders = orders_df[mask].copy()
        
        return matched_orders
    
    def calculate_cumulative_pnl(self, orders: pd.DataFrame) -> Tuple[pd.Series, pd.Series]:
        """
        Calculate cumulative PNL over time from orders
        
        Args:
            orders: DataFrame with orders (must have 'date', 'time', 'pnl' columns)
            
        Returns:
            Tuple of (equity_curve, datetime_series)
        """
        if len(orders) == 0:
            return pd.Series([]), pd.Series([])
        
        # Create datetime column
        orders['datetime'] = pd.to_datetime(orders['date'] + ' ' + orders['time'])
        
        # Sort by datetime
        orders = orders.sort_values('datetime').copy()
        
        # Calculate cumulative PNL
        orders['cumulative_pnl'] = orders['pnl'].cumsum()
        
        # Get initial deposit
        initial_deposit = orders['deposit_before_trade'].iloc[0]
        
        # Calculate equity curve
        equity_curve = initial_deposit + orders['cumulative_pnl']
        
        return equity_curve, orders['datetime']
    
    def plot_config_pnl(self, orders: pd.DataFrame, config: Dict, 
                       save_path: Path, show_plot: bool = False) -> Dict:
        """
        Generate PNL chart for a specific configuration
        
        Args:
            orders: Matched orders for the configuration
            config: Configuration dict
            save_path: Path to save the chart
            show_plot: Whether to display the plot
            
        Returns:
            Dict with statistics about the chart
        """
        if len(orders) == 0:
            print(f"⚠️  No orders found for config")
            return {'status': 'no_orders', 'trades': 0}
        
        # Calculate equity curve
        equity_curve, datetime_series = self.calculate_cumulative_pnl(orders)
        
        if len(equity_curve) == 0:
            print(f"⚠️  Could not calculate equity curve")
            return {'status': 'error', 'trades': len(orders)}
        
        # Generate plot using existing chart_plotters function
        # Convert to list to avoid numpy array boolean ambiguity
        plot_equity_curve(
            equity_curve.values, 
            equity_dates=datetime_series.tolist() if len(datetime_series) > 0 else None,
            save_path=str(save_path)
        )
        
        # Calculate statistics
        initial_balance = equity_curve.iloc[0]
        final_balance = equity_curve.iloc[-1]
        total_return = ((final_balance - initial_balance) / initial_balance) * 100
        max_equity = equity_curve.max()
        drawdowns = (equity_curve - equity_curve.cummax()) / equity_curve.cummax() * 100
        max_drawdown = drawdowns.min()
        
        stats = {
            'status': 'success',
            'trades': len(orders),
            'initial_balance': initial_balance,
            'final_balance': final_balance,
            'total_return_pct': total_return,
            'max_equity': max_equity,
            'max_drawdown_pct': max_drawdown,
            'start_date': datetime_series.iloc[0],
            'end_date': datetime_series.iloc[-1]
        }
        
        return stats
    
    def load_order_file(self, symbol: str, timeframe: str) -> Optional[pd.DataFrame]:
        """
        Load order file for a specific asset/timeframe
        
        Args:
            symbol: Asset symbol
            timeframe: Timeframe (e.g., '5m', '15m')
            
        Returns:
            DataFrame with orders or None if file not found
        """
        # Try different possible naming patterns
        patterns = [
            f"{symbol}_{timeframe}_*_orders.csv",
            f"{symbol}_{timeframe}_orders.csv",
        ]
        
        order_files = []
        for pattern in patterns:
            order_files.extend(list(self.orders_dir.glob(pattern)))
        
        if not order_files:
            print(f"⚠️  No order file found for {symbol}_{timeframe}")
            print(f"   Searched: {self.orders_dir}")
            return None
        
        # Use the most recent file if multiple found
        order_file = sorted(order_files)[-1]
        print(f"📂 Loading orders from {order_file.name}")
        
        try:
            orders_df = pd.read_csv(order_file)
            print(f"   Loaded {len(orders_df)} total orders")
            return orders_df
        except Exception as e:
            print(f"❌ Error loading {order_file}: {e}")
            return None
    
    def generate_single_pnl_chart(self, config: Dict, config_key: str) -> Dict:
        """
        Generate PNL chart for a single configuration
        
        Args:
            config: Configuration dict from best_configs
            config_key: Key identifier for the config (e.g., 'BTCUSDX_5m')
            
        Returns:
            Dict with results and statistics
        """
        symbol = config['ASSET_INFO']['symbol']
        timeframe = config['ASSET_INFO']['timeframe']
        run_id = config['METADATA']['run_id']
        
        print(f"\n{'='*60}")
        print(f"Processing: {config_key} (run_id: {run_id})")
        print(f"{'='*60}")
        
        # Load order file
        orders_df = self.load_order_file(symbol, timeframe)
        if orders_df is None:
            return {'status': 'no_file', 'config_key': config_key}
        
        # Match orders to this configuration
        matched_orders = self.match_orders_to_config(orders_df, config)
        print(f"✅ Matched {len(matched_orders)} orders to configuration")
        
        if len(matched_orders) == 0:
            print(f"⚠️  No matching orders found - check parameter values")
            return {'status': 'no_match', 'config_key': config_key}
        
        # Generate plot
        save_path = self.output_dir / f"{config_key}_run{run_id}_pnl.png"
        stats = self.plot_config_pnl(matched_orders, config, save_path)
        
        if stats['status'] == 'success':
            print(f"📈 Generated PNL chart: {save_path}")
            print(f"   Trades: {stats['trades']}")
            print(f"   Return: {stats['total_return_pct']:.2f}%")
            print(f"   Max DD: {stats['max_drawdown_pct']:.2f}%")
        
        stats['config_key'] = config_key
        stats['run_id'] = run_id
        stats['save_path'] = str(save_path)
        
        return stats
    
    def generate_portfolio_pnl_chart(self, all_orders: List[pd.DataFrame], 
                                    configs: Dict, save_path: Path) -> Dict:
        """
        Generate aggregated portfolio PNL chart from multiple assets
        
        Args:
            all_orders: List of matched order DataFrames
            configs: Dict of all configurations
            save_path: Path to save the chart
            
        Returns:
            Dict with portfolio statistics
        """
        if not all_orders:
            print("⚠️  No orders to aggregate")
            return {'status': 'no_orders'}
        
        # Concatenate all orders
        combined_orders = pd.concat(all_orders, ignore_index=True)
        print(f"📊 Aggregating {len(combined_orders)} orders from {len(all_orders)} assets")
        
        # Create datetime column and sort
        combined_orders['datetime'] = pd.to_datetime(
            combined_orders['date'] + ' ' + combined_orders['time']
        )
        combined_orders = combined_orders.sort_values('datetime').copy()
        
        # Calculate cumulative portfolio PNL
        combined_orders['cumulative_pnl'] = combined_orders['pnl'].cumsum()
        
        # Use the first deposit value as initial balance
        initial_balance = combined_orders['deposit_before_trade'].iloc[0]
        equity_curve = initial_balance + combined_orders['cumulative_pnl']
        
        # Generate plot
        plot_equity_curve(
            equity_curve.values,
            equity_dates=combined_orders['datetime'].tolist() if len(combined_orders) > 0 else None,
            save_path=str(save_path)
        )
        
        # Calculate statistics
        final_balance = equity_curve.iloc[-1]
        total_return = ((final_balance - initial_balance) / initial_balance) * 100
        drawdowns = (equity_curve - equity_curve.cummax()) / equity_curve.cummax() * 100
        max_drawdown = drawdowns.min()
        
        stats = {
            'status': 'success',
            'total_trades': len(combined_orders),
            'num_assets': len(all_orders),
            'initial_balance': initial_balance,
            'final_balance': final_balance,
            'total_return_pct': total_return,
            'max_drawdown_pct': max_drawdown,
            'start_date': combined_orders['datetime'].iloc[0],
            'end_date': combined_orders['datetime'].iloc[-1]
        }
        
        print(f"\n📈 Generated portfolio PNL chart: {save_path}")
        print(f"   Assets: {stats['num_assets']}")
        print(f"   Trades: {stats['total_trades']}")
        print(f"   Return: {stats['total_return_pct']:.2f}%")
        print(f"   Max DD: {stats['max_drawdown_pct']:.2f}%")
        
        return stats
    
    def process_best_configs(self, config_file: Path, 
                            generate_portfolio: bool = True) -> Dict:
        """
        Process all configurations from a best_configs JSON file
        
        Args:
            config_file: Path to best_configs JSON file
            generate_portfolio: Whether to generate aggregated portfolio chart
            
        Returns:
            Dict with processing results and statistics
        """
        print(f"\n🚀 Processing configurations from {config_file.name}")
        
        # Load configurations
        with open(config_file, 'r') as f:
            configs = json.load(f)
        
        print(f"📊 Found {len(configs)} configurations")
        
        results = []
        all_matched_orders = []
        
        # Process each configuration
        for config_key, config in configs.items():
            result = self.generate_single_pnl_chart(config, config_key)
            results.append(result)
            
            # Collect orders for portfolio chart
            if generate_portfolio and result['status'] == 'success':
                symbol = config['ASSET_INFO']['symbol']
                timeframe = config['ASSET_INFO']['timeframe']
                orders_df = self.load_order_file(symbol, timeframe)
                if orders_df is not None:
                    matched = self.match_orders_to_config(orders_df, config)
                    if len(matched) > 0:
                        all_matched_orders.append(matched)
        
        # Generate portfolio chart
        portfolio_stats = None
        if generate_portfolio and all_matched_orders:
            objective = config_file.stem.replace('best_configs_', '')
            portfolio_path = self.output_dir / f"portfolio_{objective}_pnl.png"
            portfolio_stats = self.generate_portfolio_pnl_chart(
                all_matched_orders, configs, portfolio_path
            )
        
        # Summary statistics
        successful = sum(1 for r in results if r['status'] == 'success')
        failed = len(results) - successful
        
        summary = {
            'total_configs': len(configs),
            'successful': successful,
            'failed': failed,
            'results': results,
            'portfolio_stats': portfolio_stats
        }
        
        print(f"\n{'='*60}")
        print(f"SUMMARY")
        print(f"{'='*60}")
        print(f"Total configs: {summary['total_configs']}")
        print(f"✅ Successful: {summary['successful']}")
        print(f"❌ Failed: {summary['failed']}")
        
        return summary


def main():
    """Main function with command-line interface"""
    parser = argparse.ArgumentParser(
        description="Generate PNL charts for optimized configurations"
    )
    parser.add_argument(
        '--config-file',
        type=str,
        default='results/best_configs_balanced.json',
        help='Path to best_configs JSON file (default: results/best_configs_balanced.json)'
    )
    parser.add_argument(
        '--orders-dir',
        type=str,
        default='optimization/orders',
        help='Directory containing order CSV files (default: optimization/orders)'
    )
    parser.add_argument(
        '--output-dir',
        type=str,
        default='plots/pnl_curves',
        help='Output directory for PNL charts (default: plots/pnl_curves)'
    )
    parser.add_argument(
        '--no-portfolio',
        action='store_true',
        help='Skip generating aggregated portfolio chart'
    )
    parser.add_argument(
        '--tolerance',
        type=float,
        default=1e-9,
        help='Floating-point comparison tolerance for parameter matching (default: 1e-9)'
    )
    
    args = parser.parse_args()
    
    # Verify input file exists
    config_file = Path(args.config_file)
    if not config_file.exists():
        print(f"❌ Config file not found: {config_file}")
        print("Run analyze_batch_results.py first to generate best_configs files")
        return 1
    
    # Verify orders directory exists
    orders_dir = Path(args.orders_dir)
    if not orders_dir.exists():
        print(f"❌ Orders directory not found: {orders_dir}")
        return 1
    
    # Create generator
    generator = ConfigPNLGenerator(
        orders_dir=args.orders_dir,
        output_dir=args.output_dir
    )
    
    # Process configurations
    summary = generator.process_best_configs(
        config_file=config_file,
        generate_portfolio=not args.no_portfolio
    )
    
    # Save summary to file
    summary_file = Path(args.output_dir) / f"pnl_generation_summary_{config_file.stem}.json"
    with open(summary_file, 'w') as f:
        # Convert datetime objects to strings for JSON serialization
        def convert_datetime(obj):
            if isinstance(obj, pd.Timestamp):
                return obj.isoformat()
            elif isinstance(obj, dict):
                return {k: convert_datetime(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [convert_datetime(item) for item in obj]
            return obj
        
        json.dump(convert_datetime(summary), f, indent=2)
    
    print(f"\n💾 Summary saved to {summary_file}")
    print(f"\n🎉 PNL chart generation complete!")
    
    return 0 if summary['successful'] > 0 else 1


if __name__ == '__main__':
    exit(main())

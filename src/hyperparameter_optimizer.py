"""
Hyperparameter Optimization Module

This module provides comprehensive hyperparameter optimization for the mean reversion strategy
with caching, intermediate result logging, and CSV output capabilities.

Features:
- Grid search and random search optimization
- Market data caching for consistent testing
- Intermediate results caching to resume optimization
- CSV logging of all results
- Progress tracking and estimated completion time
- Best parameter tracking with multiple objectives
- Parallel execution support (optional)
"""

import os
import sys
import time
import pickle
import hashlib
import itertools
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple, Union
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import dataclass, asdict

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from src.backtest import run_backtest
from src.metrics import calculate_metrics
from src.strategy import MeanReversionStrategy
from src.data_fetcher import DataFetcher
from src.strategy_config import StrategyConfig
from src.chart_plotters import plot_equity_curve
from src.order_visualization import save_order_plots


@dataclass
class OptimizationResult:
    """Container for optimization results"""
    parameters: Dict[str, Any]
    metrics: Dict[str, float]
    final_pnl: float
    total_trades: int
    win_rate: float
    sharpe_ratio: float
    max_drawdown: float
    execution_time: float
    timestamp: str
    

class ParameterGrid:
    """Helper class for defining parameter grids"""
    
    @staticmethod
    def create_default_grid() -> Dict[str, List]:
        """Create a default parameter grid for optimization"""
        return {
            # Bollinger Bands parameters
            'bb_window': [15, 20, 25, 30],
            'bb_std': [1.5, 2.0, 2.5],
            
            # VWAP parameters
            'vwap_window': [15, 20, 25, 30],
            'vwap_std': [1.5, 2.0, 2.5],
            
            # Risk management
            'risk_per_position_pct': [0.5, 1.0, 1.5, 2.0],
            'stop_loss_atr_multiplier': [1.0, 1.2, 1.5, 2.0],
            'risk_reward_ratio': [2.0, 2.5, 3.0, 3.5],
            
            # ATR period
            'atr_period': [10, 14, 20],
            
            # Strategy behavior
            'require_reversal': [True, False],
            
            # Market regime (if enabled)
            'regime_min_score': [40, 50, 60, 70],
            'regime_adx_strong_threshold': [20, 25, 30],
        }
    
    @staticmethod
    def create_focused_grid() -> Dict[str, List]:
        """Create a focused parameter grid for faster optimization"""
        return {
            # Core parameters with proven impact
            'bb_window': [20, 25],
            'bb_std': [2.0, 2.5],
            'vwap_window': [20, 25],
            'risk_per_position_pct': [1.0, 1.5],
            'risk_reward_ratio': [2.5, 3.0],
            'stop_loss_atr_multiplier': [1.0, 1.2],
            'regime_min_score': [60, 70],
        }
    
    @staticmethod
    def create_risk_focused_grid() -> Dict[str, List]:
        """Create a risk management focused parameter grid"""
        return {
            'risk_per_position_pct': [0.5, 0.75, 1.0, 1.25, 1.5, 2.0],
            'stop_loss_atr_multiplier': [0.8, 1.0, 1.2, 1.5, 2.0],
            'risk_reward_ratio': [1.5, 2.0, 2.5, 3.0, 3.5, 4.0],
        }


class HyperparameterOptimizer:
    """
    Main hyperparameter optimization class with comprehensive caching and logging
    """
    
    def __init__(
        self,
        data_source: str = 'forex',
        symbol: str = 'EURUSD=X',
        timeframe: str = '15m',
        years: int = 2,
        optimization_dir: Optional[str] = None,
        plot_equity_curves: bool = False,
        plot_orders: bool = False,
        verbose: bool = True
    ):
        """
        Initialize the optimizer
        
        Args:
            data_source: Data source ('forex', 'stock', etc.)
            symbol: Trading symbol
            timeframe: Data timeframe
            years: Years of historical data
            optimization_dir: Directory to store optimization results
            plot_equity_curves: Whether to save equity curve plots for each run
            plot_orders: Whether to save order plots for each run
            verbose: Enable detailed logging output
        """
        self.data_source = data_source
        self.symbol = symbol
        self.timeframe = timeframe
        self.years = years
        self.plot_equity_curves = plot_equity_curves
        self.plot_orders = plot_orders
        self.verbose = verbose
        
        # Setup directories
        self.project_root = Path(__file__).parent.parent
        self.optimization_dir = Path(optimization_dir) if optimization_dir else self.project_root / 'optimization'
        self.cache_dir = self.optimization_dir / 'cache'
        self.results_dir = self.optimization_dir / 'results'
        self.logs_dir = self.optimization_dir / 'logs'
        self.plots_dir = self.optimization_dir / 'plots' if self.plot_equity_curves else None
        self.orders_dir = self.optimization_dir / 'orders' if self.plot_orders else None
        
        # Create directories
        dirs_to_create = [self.optimization_dir, self.cache_dir, self.results_dir, self.logs_dir]
        if self.plots_dir:
            dirs_to_create.append(self.plots_dir)
        if self.orders_dir:
            dirs_to_create.append(self.orders_dir)
        
        for dir_path in dirs_to_create:
            dir_path.mkdir(parents=True, exist_ok=True)
        
        # Initialize components
        self.data = None
        self.data_hash = None
        self.results = []
        self.best_results = {}
        self.start_time = None
        
        # File paths
        self.results_csv_path = None
        self.progress_file_path = None
        self.best_params_file_path = None
        
    def _get_data_hash(self) -> str:
        """Generate hash for data parameters"""
        data_params = f"{self.data_source}_{self.symbol}_{self.timeframe}_{self.years}"
        return hashlib.md5(data_params.encode()).hexdigest()[:12]
    
    def _load_cached_data(self) -> Optional[pd.DataFrame]:
        """Load cached market data if available"""
        if not self.data_hash:
            self.data_hash = self._get_data_hash()
        
        cache_file = self.cache_dir / f"data_{self.data_hash}.pkl"
        
        if cache_file.exists():
            try:
                print(f"📦 Loading cached data: {cache_file.name}")
                with open(cache_file, 'rb') as f:
                    cached_data = pickle.load(f)
                return cached_data['data']
            except Exception as e:
                print(f"⚠️  Error loading cached data: {e}")
        
        return None
    
    def _cache_data(self, data: pd.DataFrame) -> None:
        """Cache market data"""
        if not self.data_hash:
            self.data_hash = self._get_data_hash()
        
        cache_file = self.cache_dir / f"data_{self.data_hash}.pkl"
        
        try:
            cache_data = {
                'data': data,
                'timestamp': datetime.now(),
                'parameters': {
                    'source': self.data_source,
                    'symbol': self.symbol,
                    'timeframe': self.timeframe,
                    'years': self.years
                }
            }
            
            with open(cache_file, 'wb') as f:
                pickle.dump(cache_data, f)
            
            print(f"💾 Cached data: {cache_file.name}")
        except Exception as e:
            print(f"⚠️  Error caching data: {e}")
    
    def _load_market_data(self) -> pd.DataFrame:
        """Load market data with caching"""
        print(f"🔄 Loading market data: {self.data_source} {self.symbol} {self.timeframe} ({self.years} years)")
        
        # Try to load from cache first
        cached_data = self._load_cached_data()
        if cached_data is not None:
            self.data = cached_data
            return self.data
        
        # Fetch new data
        print("📊 Fetching fresh market data...")
        start_time = time.time()
        
        fetcher = DataFetcher(
            source=self.data_source,
            symbol=self.symbol,
            timeframe=self.timeframe,
            use_cache=True
        )
        
        self.data = fetcher.fetch(years=self.years)
        
        # Cache the data
        self._cache_data(self.data)
        
        elapsed = time.time() - start_time
        print(f"✅ Data loaded in {elapsed:.1f}s - Shape: {self.data.shape}")
        
        return self.data
    
    def _get_param_hash(self, params: Dict[str, Any]) -> str:
        """Generate hash for parameter combination"""
        param_str = str(sorted(params.items()))
        return hashlib.md5(param_str.encode()).hexdigest()[:12]
    
    def _load_cached_result(self, params: Dict[str, Any]) -> Optional[OptimizationResult]:
        """Load cached optimization result if available"""
        param_hash = self._get_param_hash(params)
        cache_file = self.cache_dir / f"result_{self.data_hash}_{param_hash}.pkl"
        
        if cache_file.exists():
            try:
                with open(cache_file, 'rb') as f:
                    return pickle.load(f)
            except Exception as e:
                print(f"⚠️  Error loading cached result: {e}")
        
        return None
    
    def _cache_result(self, result: OptimizationResult) -> None:
        """Cache optimization result"""
        param_hash = self._get_param_hash(result.parameters)
        cache_file = self.cache_dir / f"result_{self.data_hash}_{param_hash}.pkl"
        
        try:
            with open(cache_file, 'wb') as f:
                pickle.dump(result, f)
        except Exception as e:
            print(f"⚠️  Error caching result: {e}")
    
    def _setup_result_files(self, optimization_name: str) -> None:
        """Setup CSV result files and progress tracking"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # CSV results file
        self.results_csv_path = self.results_dir / f"{optimization_name}_{timestamp}.csv"
        
        # Progress tracking file
        self.progress_file_path = self.logs_dir / f"progress_{optimization_name}_{timestamp}.txt"
        
        # Best parameters file
        self.best_params_file_path = self.results_dir / f"best_params_{optimization_name}_{timestamp}.json"
        
        # Write CSV header
        header = [
            'timestamp', 'final_pnl', 'total_trades', 'win_rate', 'sharpe_ratio', 
            'max_drawdown', 'execution_time'
        ]
        
        # Add parameter columns (will be determined from first result)
        with open(self.results_csv_path, 'w') as f:
            f.write(','.join(header) + ',parameters\n')
    
    def _log_result_to_csv(self, result: OptimizationResult) -> None:
        """Log optimization result to CSV"""
        if not self.results_csv_path:
            return
        
        try:
            # Prepare row data
            row_data = [
                result.timestamp,
                result.final_pnl,
                result.total_trades,
                result.win_rate,
                result.sharpe_ratio,
                result.max_drawdown,
                result.execution_time,
                str(result.parameters)
            ]
            
            # Append to CSV
            with open(self.results_csv_path, 'a') as f:
                f.write(','.join(map(str, row_data)) + '\n')
                
        except Exception as e:
            print(f"⚠️  Error logging to CSV: {e}")
    
    def _update_progress(self, completed: int, total: int, current_result: OptimizationResult) -> None:
        """Update progress file with current status"""
        if not self.progress_file_path:
            return
        
        try:
            elapsed_time = time.time() - self.start_time
            progress_pct = (completed / total) * 100
            
            if completed > 0:
                avg_time_per_test = elapsed_time / completed
                remaining_tests = total - completed
                estimated_remaining = remaining_tests * avg_time_per_test
                estimated_completion = datetime.now() + timedelta(seconds=estimated_remaining)
            else:
                estimated_completion = "Unknown"
            
            progress_info = f"""
Optimization Progress Report
===========================
Completed: {completed}/{total} ({progress_pct:.1f}%)
Elapsed Time: {elapsed_time/60:.1f} minutes
Estimated Completion: {estimated_completion}
Current Best PnL: ${max([r.final_pnl for r in self.results]) if self.results else 0:,.2f}
Last Result: PnL=${current_result.final_pnl:,.2f}, Trades={current_result.total_trades}, WinRate={current_result.win_rate:.1f}%
"""
            
            with open(self.progress_file_path, 'w') as f:
                f.write(progress_info)
                
        except Exception as e:
            print(f"⚠️  Error updating progress: {e}")
    
    def _plot_equity_curve(self, params: Dict[str, Any], equity_curve: pd.Series, 
                          equity_dates: pd.DatetimeIndex, final_pnl: float) -> None:
        """Plot and save equity curve for a parameter combination"""
        try:
            # Create a filename based on parameters and performance
            param_str = "_".join([f"{k}{v}" for k, v in params.items()])
            # Limit filename length and sanitize
            param_str = param_str[:50].replace('.', '_').replace('-', '_')
            pnl_str = f"PnL{final_pnl:.0f}".replace('-', 'neg')
            filename = f"equity_{param_str}_{pnl_str}.png"
            
            # Create save path
            save_path = self.plots_dir / filename
            
            # Use the existing visualization function
            plot_equity_curve(
                equity_curve=equity_curve,
                equity_dates=equity_dates,
                save_path=str(save_path)
            )
            
            if self.verbose:
                print(f"📊 Equity curve saved: {filename}")
                
        except Exception as e:
            if self.verbose:
                print(f"⚠️  Error plotting equity curve: {e}")

    def _plot_orders(self, params: Dict[str, Any], order_log: list, final_pnl: float) -> None:
        """Plot and save order analysis for a parameter combination"""
        try:
            # Create a filename based on parameters and performance
            param_str = "_".join([f"{k}{v}" for k, v in params.items()])
            # Limit filename length and sanitize
            param_str = param_str[:50].replace('.', '_').replace('-', '_')
            pnl_str = f"PnL{final_pnl:.0f}".replace('-', 'neg')
            orders_subdir = f"orders_{param_str}_{pnl_str}"
            
            # Create subdirectory for this parameter combination
            orders_run_dir = self.orders_dir / orders_subdir
            orders_run_dir.mkdir(exist_ok=True)
            
            # Use the existing order visualization function
            saved_path = save_order_plots(
                df=self.data,  # Market data for context
                orders=order_log,  # Order information
                output_dir=str(orders_run_dir),
                window_size=50  # Chart window size around each order
            )
            
            if self.verbose and saved_path:
                print(f"📈 Order plots saved: {orders_subdir}/")
                
        except Exception as e:
            if self.verbose:
                print(f"⚠️  Error plotting orders: {e}")

    def _run_single_backtest(self, params: Dict[str, Any]) -> OptimizationResult:
        """Run a single backtest with given parameters"""
        start_time = time.time()
        
        try:
            # Check cache first
            cached_result = self._load_cached_result(params)
            if cached_result is not None:
                return cached_result
            
            # Prepare strategy parameters
            strategy_params = self._prepare_strategy_params(params)
            
            # Run backtest with configurable logging
            equity_curve, equity_dates, trade_log, order_log = run_backtest(
                data=self.data,
                strategy_class=MeanReversionStrategy,
                params=strategy_params,
                verbose=self.verbose
            )
            
            # Calculate metrics
            metrics = calculate_metrics(trade_log, equity_curve)
            
            # Extract key metrics
            final_pnl = metrics.get('final_pnl', 0)
            total_trades = metrics.get('total_trades', 0)
            win_rate = metrics.get('win_rate', 0) * 100  # Convert to percentage
            sharpe_ratio = metrics.get('sharpe_ratio', 0)
            max_drawdown = metrics.get('max_drawdown', 0)
            
            # Plot equity curve if requested
            if self.plot_equity_curves and equity_curve is not None:
                self._plot_equity_curve(params, equity_curve, equity_dates, final_pnl)
            
            # Plot orders if requested
            if self.plot_orders and order_log is not None and len(order_log) > 0:
                self._plot_orders(params, order_log, final_pnl)
            
            # Create result object
            result = OptimizationResult(
                parameters=params.copy(),
                metrics=metrics,
                final_pnl=final_pnl,
                total_trades=total_trades,
                win_rate=win_rate,
                sharpe_ratio=sharpe_ratio,
                max_drawdown=max_drawdown,
                execution_time=time.time() - start_time,
                timestamp=datetime.now().isoformat()
            )
            
            # Cache the result
            self._cache_result(result)
            
            return result
            
        except Exception as e:
            print(f"⚠️  Error in backtest: {e}")
            # Return a failed result
            return OptimizationResult(
                parameters=params.copy(),
                metrics={},
                final_pnl=-999999,
                total_trades=0,
                win_rate=0,
                sharpe_ratio=-999,
                max_drawdown=999,
                execution_time=time.time() - start_time,
                timestamp=datetime.now().isoformat()
            )
    
    def _prepare_strategy_params(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Convert optimization parameters to strategy parameters"""
        # Start with default config
        base_config = StrategyConfig.get_backtrader_params()
        
        # Override with optimization parameters
        param_mapping = {
            'bb_window': 'bb_window',
            'bb_std': 'bb_std',
            'vwap_window': 'vwap_window',
            'vwap_std': 'vwap_std',
            'atr_period': 'atr_period',
            'require_reversal': 'require_reversal',
            'regime_min_score': 'regime_min_score',
            # Risk management parameters - pass directly to strategy
            'risk_per_position_pct': 'risk_per_position_pct',
            'stop_loss_atr_multiplier': 'stop_loss_atr_multiplier',
            'risk_reward_ratio': 'risk_reward_ratio',
        }
        
        strategy_params = base_config.copy()
        
        for opt_param, strategy_param in param_mapping.items():
            if opt_param in params:
                strategy_params[strategy_param] = params[opt_param]
        
        # Add timeframe and verbose setting for optimization
        strategy_params['timeframe'] = self.timeframe
        strategy_params['verbose'] = False  # Reduce strategy console output during optimization
        
        return strategy_params
    
    def grid_search(
        self,
        param_grid: Dict[str, List],
        optimization_name: str = "grid_search",
        max_workers: Optional[int] = None
    ) -> List[OptimizationResult]:
        """
        Perform grid search optimization
        
        Args:
            param_grid: Dictionary of parameter names and value lists
            optimization_name: Name for this optimization run
            max_workers: Number of parallel workers (None for sequential)
        
        Returns:
            List of optimization results sorted by final PnL
        """
        print("="*80)
        print(f"🔍 STARTING GRID SEARCH OPTIMIZATION: {optimization_name}")
        print("="*80)
        
        # Load market data
        self._load_market_data()
        
        # Setup result files
        self._setup_result_files(optimization_name)
        
        # Generate parameter combinations
        keys, values = zip(*param_grid.items())
        param_combinations = list(itertools.product(*values))
        total_combinations = len(param_combinations)
        
        print(f"📊 Parameter grid:")
        for key, value_list in param_grid.items():
            print(f"  {key}: {value_list}")
        print(f"🔢 Total combinations to test: {total_combinations:,}")
        
        self.start_time = time.time()
        self.results = []
        
        if max_workers and max_workers > 1:
            # Parallel execution
            print(f"🚀 Running with {max_workers} parallel workers...")
            self._run_parallel_optimization(param_combinations, keys)
        else:
            # Sequential execution
            print("🔄 Running sequential optimization...")
            self._run_sequential_optimization(param_combinations, keys)
        
        # Sort results by final PnL (descending)
        self.results.sort(key=lambda x: x.final_pnl, reverse=True)
        
        # Save best results
        self._save_best_results()
        
        # Print summary
        self._print_optimization_summary()
        
        return self.results
    
    def _run_sequential_optimization(self, param_combinations: List, keys: List[str]) -> None:
        """Run optimization sequentially"""
        for i, combo in enumerate(param_combinations, 1):
            params = dict(zip(keys, combo))
            
            print(f"\n🔄 [{i}/{len(param_combinations)}] Testing: {params}")
            
            result = self._run_single_backtest(params)
            self.results.append(result)
            
            # Log to CSV
            self._log_result_to_csv(result)
            
            # Update progress
            self._update_progress(i, len(param_combinations), result)
            
            print(f"   💰 PnL: ${result.final_pnl:,.2f} | Trades: {result.total_trades} | WinRate: {result.win_rate:.1f}% | Sharpe: {result.sharpe_ratio:.2f}")
    
    def _run_parallel_optimization(self, param_combinations: List, keys: List[str]) -> None:
        """Run optimization in parallel (placeholder - implementation needed)"""
        # For now, fall back to sequential
        print("⚠️  Parallel execution not implemented yet, running sequentially...")
        self._run_sequential_optimization(param_combinations, keys)
    
    def _save_best_results(self) -> None:
        """Save best results to files"""
        if not self.results:
            return
        
        try:
            # Track best by different metrics
            self.best_results = {
                'best_pnl': self.results[0],  # Already sorted by PnL
                'best_sharpe': max(self.results, key=lambda x: x.sharpe_ratio),
                'best_win_rate': max(self.results, key=lambda x: x.win_rate),
                'lowest_drawdown': min(self.results, key=lambda x: x.max_drawdown)
            }
            
            # Save to JSON
            import json
            best_summary = {}
            for metric_name, result in self.best_results.items():
                best_summary[metric_name] = {
                    'parameters': result.parameters,
                    'final_pnl': result.final_pnl,
                    'sharpe_ratio': result.sharpe_ratio,
                    'win_rate': result.win_rate,
                    'max_drawdown': result.max_drawdown,
                    'total_trades': result.total_trades
                }
            
            with open(self.best_params_file_path, 'w') as f:
                json.dump(best_summary, f, indent=2)
            
            print(f"💾 Best results saved to: {self.best_params_file_path}")
            
        except Exception as e:
            print(f"⚠️  Error saving best results: {e}")
    
    def _print_optimization_summary(self) -> None:
        """Print optimization summary"""
        if not self.results:
            print("❌ No results to display")
            return
        
        total_time = time.time() - self.start_time
        
        print("\n" + "="*80)
        print("📊 OPTIMIZATION COMPLETE")
        print("="*80)
        print(f"⏱️  Total Time: {total_time/60:.1f} minutes")
        print(f"🔢 Total Tests: {len(self.results):,}")
        print(f"📈 Results saved to: {self.results_csv_path}")
        
        if self.best_results:
            print(f"\n🏆 BEST RESULTS:")
            print("-" * 50)
            
            for metric_name, result in self.best_results.items():
                print(f"\n{metric_name.upper()}:")
                print(f"  💰 Final PnL: ${result.final_pnl:,.2f}")
                print(f"  📊 Sharpe Ratio: {result.sharpe_ratio:.2f}")
                print(f"  🎯 Win Rate: {result.win_rate:.1f}%")
                print(f"  📉 Max Drawdown: {result.max_drawdown:.1f}%")
                print(f"  🔢 Total Trades: {result.total_trades}")
                print(f"  ⚙️  Parameters: {result.parameters}")
        
        # Top 5 by PnL
        print(f"\n🥇 TOP 5 BY PnL:")
        print("-" * 50)
        for i, result in enumerate(self.results[:5], 1):
            print(f"{i}. ${result.final_pnl:,.2f} | WR: {result.win_rate:.1f}% | Sharpe: {result.sharpe_ratio:.2f} | {result.parameters}")
    
    def random_search(
        self,
        param_ranges: Dict[str, Union[List, Tuple]],
        n_iterations: int,
        optimization_name: str = "random_search"
    ) -> List[OptimizationResult]:
        """
        Perform random search optimization
        
        Args:
            param_ranges: Dictionary of parameter names and ranges/choices
            n_iterations: Number of random combinations to test
            optimization_name: Name for this optimization run
        
        Returns:
            List of optimization results sorted by final PnL
        """
        print("="*80)
        print(f"🎲 STARTING RANDOM SEARCH OPTIMIZATION: {optimization_name}")
        print("="*80)
        
        # Load market data
        self._load_market_data()
        
        # Setup result files
        self._setup_result_files(optimization_name)
        
        print(f"🔢 Running {n_iterations:,} random parameter combinations")
        
        self.start_time = time.time()
        self.results = []
        
        for i in range(1, n_iterations + 1):
            # Generate random parameters
            params = self._generate_random_params(param_ranges)
            
            print(f"\n🔄 [{i}/{n_iterations}] Testing: {params}")
            
            result = self._run_single_backtest(params)
            self.results.append(result)
            
            # Log to CSV
            self._log_result_to_csv(result)
            
            # Update progress
            self._update_progress(i, n_iterations, result)
            
            print(f"   💰 PnL: ${result.final_pnl:,.2f} | Trades: {result.total_trades} | WinRate: {result.win_rate:.1f}% | Sharpe: {result.sharpe_ratio:.2f}")
        
        # Sort results by final PnL (descending)
        self.results.sort(key=lambda x: x.final_pnl, reverse=True)
        
        # Save best results
        self._save_best_results()
        
        # Print summary
        self._print_optimization_summary()
        
        return self.results
    
    def _generate_random_params(self, param_ranges: Dict[str, Union[List, Tuple]]) -> Dict[str, Any]:
        """Generate random parameter combination"""
        params = {}
        
        for param_name, param_range in param_ranges.items():
            if isinstance(param_range, list):
                # Choose from discrete values
                params[param_name] = np.random.choice(param_range)
            elif isinstance(param_range, tuple) and len(param_range) == 2:
                # Generate from continuous range
                min_val, max_val = param_range
                if isinstance(min_val, int) and isinstance(max_val, int):
                    params[param_name] = np.random.randint(min_val, max_val + 1)
                else:
                    params[param_name] = np.random.uniform(min_val, max_val)
        
        return params


def main():
    """Example usage of the hyperparameter optimizer"""
    
    # Initialize optimizer
    optimizer = HyperparameterOptimizer(
        data_source='forex',
        symbol='EURUSD=X',
        timeframe='15m',
        years=2
    )
    
    # Run grid search with focused parameters
    param_grid = ParameterGrid.create_focused_grid()
    
    results = optimizer.grid_search(
        param_grid=param_grid,
        optimization_name="focused_optimization"
    )
    
    print(f"\n✅ Optimization complete! Best PnL: ${results[0].final_pnl:,.2f}")


if __name__ == "__main__":
    main()

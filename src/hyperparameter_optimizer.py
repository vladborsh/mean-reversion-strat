"""
Hyperparameter Optimization Module

This module provides comprehensive hyperparameter optimization for the mean reversion strategy
with caching, intermediate result logging, and CSV output capabilities with transport layer support.

Features:
- Grid search and random search optimization
- Market data caching for consistent testing (local or S3)
- Intermediate results caching to resume optimization (local or S3)
- CSV logging of all results (local or S3)
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
import json

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

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
from src.transport_factory import create_optimization_transport, create_cache_transport
from src.order_accumulator import create_order_accumulator


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
    with transport layer support for local and cloud storage.
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
        verbose: bool = True,
        cache_transport_type: str = 'local',
        log_transport_type: str = 'local'
    ):
        """
        Initialize the optimizer
        
        Args:
            data_source: Data source ('forex', 'stock', etc.)
            symbol: Trading symbol
            timeframe: Data timeframe
            years: Years of historical data
            optimization_dir: Directory to store optimization results (ignored if using S3)
            plot_equity_curves: Whether to save equity curve plots for each run
            plot_orders: Whether to save order plots for each run
            verbose: Enable detailed logging output
            cache_transport_type: Cache transport type ('local' or 's3')
            log_transport_type: Log transport type ('local' or 's3')
        """
        self.data_source = data_source
        self.symbol = symbol
        self.timeframe = timeframe
        self.years = years
        self.plot_equity_curves = plot_equity_curves
        self.plot_orders = plot_orders
        self.verbose = verbose
        self.cache_transport_type = cache_transport_type
        self.log_transport_type = log_transport_type
        
        # Initialize transport layers
        self.cache_transport = create_cache_transport(transport_type=cache_transport_type)
        self.optimization_transport = create_optimization_transport(optimization_dir, transport_type=log_transport_type)
        
        # Store transport parameters for order accumulator recreation
        self.log_transport_type = log_transport_type
        self.optimization_dir = optimization_dir
        
        # Initialize order accumulator (will be recreated with optimization type)
        self.order_accumulator = create_order_accumulator(
            symbol=symbol,
            timeframe=timeframe,
            transport_type=log_transport_type,
            output_dir=optimization_dir
        )
        
        print(f"💾 Cache transport: {type(self.cache_transport).__name__}")
        print(f"📊 Optimization transport: {type(self.optimization_transport).__name__}")
        print(f"📋 Order accumulator initialized for {symbol}_{timeframe}")
        
        # Initialize components
        self.data = None
        self.data_hash = None
        self.results = []
        self.best_results = {}
        self.start_time = None
        self.backtest_times = []  # Track individual backtest execution times
        self.optimization_run_counter = 0  # Track optimization run number
        
        # File paths (now transport keys)
        self.results_csv_key = None
        self.progress_file_key = None
        self.best_params_file_key = None
    
    @property
    def results_dir(self) -> str:
        """
        Get the results directory path.
        
        Returns:
            str: The directory path where results are stored.
                 For local transport, returns the base directory.
                 For S3 transport, returns a descriptive S3 path.
        """
        if hasattr(self.optimization_transport, 'base_dir'):
            # Local transport
            return str(self.optimization_transport.base_dir)
        elif hasattr(self.optimization_transport, 'bucket_name'):
            # S3 transport
            bucket = self.optimization_transport.bucket_name
            prefix = getattr(self.optimization_transport, 'prefix', '')
            return f"s3://{bucket}/{prefix}"
        else:
            # Fallback
            return "optimization/"
        
    def _get_data_hash(self) -> str:
        """Generate hash for data parameters"""
        data_params = f"{self.data_source}_{self.symbol}_{self.timeframe}_{self.years}"
        return hashlib.md5(data_params.encode()).hexdigest()[:12]
    
    def _get_symbol_identifier(self) -> str:
        """Generate clean symbol identifier for file names"""
        # Clean symbol for file naming (remove special characters, limit length)
        symbol_clean = self.symbol.replace('=', '').replace('/', '').replace('-', '_').upper()
        # Limit to 10 characters to keep file names reasonable
        return symbol_clean[:10]
    
    def _load_cached_data(self) -> Optional[pd.DataFrame]:
        """Load cached market data if available"""
        if not self.data_hash:
            self.data_hash = self._get_data_hash()
        
        symbol_id = self._get_symbol_identifier()
        cache_key = f"cache/{symbol_id}_{self.timeframe}_data_{self.data_hash}.pkl"
        
        try:
            cached_data = self.cache_transport.load_pickle(cache_key)
            if cached_data is not None:
                print(f"📦 Loading cached data: {cache_key}")
                return cached_data['data']
        except Exception as e:
            print(f"⚠️  Error loading cached data: {e}")
        
        return None
    
    def _cache_data(self, data: pd.DataFrame) -> None:
        """Cache market data"""
        if not self.data_hash:
            self.data_hash = self._get_data_hash()
        
        symbol_id = self._get_symbol_identifier()
        cache_key = f"cache/{symbol_id}_{self.timeframe}_data_{self.data_hash}.pkl"
        
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
        
        if self.cache_transport.save_pickle(cache_key, cache_data):
            print(f"💾 Cached data: {cache_key}")
        else:
            print(f"⚠️  Error caching data: {cache_key}")
    
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
            use_cache=True,
            cache_transport_type=self.cache_transport_type
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
        symbol_id = self._get_symbol_identifier()
        cache_key = f"cache/{symbol_id}_{self.timeframe}_result_{self.data_hash}_{param_hash}.pkl"
        
        try:
            result = self.optimization_transport.load_pickle(cache_key)
            if result is not None:
                return result
        except Exception as e:
            if self.verbose:
                print(f"⚠️  Error loading cached result: {e}")
        
        return None
    
    def _cache_result(self, result: OptimizationResult) -> None:
        """Cache optimization result"""
        param_hash = self._get_param_hash(result.parameters)
        symbol_id = self._get_symbol_identifier()
        cache_key = f"cache/{symbol_id}_{self.timeframe}_result_{self.data_hash}_{param_hash}.pkl"
        
        if not self.optimization_transport.save_pickle(cache_key, result):
            if self.verbose:
                print(f"⚠️  Error caching result: {cache_key}")
    
    def _setup_result_files(self, optimization_name: str) -> None:
        """Setup CSV result files and progress tracking"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        symbol_id = self._get_symbol_identifier()
        
        # Set transport keys with symbol information
        self.results_csv_key = f"results/{symbol_id}_{self.timeframe}_{optimization_name}_{timestamp}.csv"
        self.progress_file_key = f"logs/{symbol_id}_{self.timeframe}_progress_{optimization_name}_{timestamp}.txt"
        self.best_params_file_key = f"results/{symbol_id}_{self.timeframe}_best_params_{optimization_name}_{timestamp}.json"
        
        # Write CSV header
        header = [
            'timestamp', 'final_pnl', 'total_trades', 'win_rate', 'sharpe_ratio', 
            'max_drawdown', 'execution_time', 'parameters'
        ]
        
        # Save CSV header
        csv_content = ','.join(header) + '\n'
        self.optimization_transport.save_text(self.results_csv_key, csv_content)
    
    def _setup_order_accumulator(self, optimization_type: str) -> None:
        """Setup order accumulator with optimization type for proper file naming"""
        from .order_accumulator import create_order_accumulator
        
        # Extract optimization type from optimization_name (e.g., "grid_search_focused" -> "focused")
        # Common patterns: grid_search_focused, grid_search_balanced, random_search, etc.
        if 'focused' in optimization_type.lower():
            opt_type = 'focused'
        elif 'balanced' in optimization_type.lower():
            opt_type = 'balanced'
        elif 'risk' in optimization_type.lower():
            opt_type = 'risk'
        else:
            # For other types like "random_search", use the full name
            opt_type = optimization_type
        
        # Recreate order accumulator with optimization type
        self.order_accumulator = create_order_accumulator(
            symbol=self.symbol,
            timeframe=self.timeframe,
            transport_type=self.log_transport_type,
            output_dir=self.optimization_dir,
            optimization_type=opt_type
        )
    
    def _log_result_to_csv(self, result: OptimizationResult) -> None:
        """Log optimization result to CSV"""
        if not self.results_csv_key:
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
            
            # Get current CSV content and append new row
            current_content = self.optimization_transport.load_text(self.results_csv_key) or ""
            new_row = ','.join(map(str, row_data)) + '\n'
            updated_content = current_content + new_row
            
            self.optimization_transport.save_text(self.results_csv_key, updated_content)
                
        except Exception as e:
            if self.verbose:
                print(f"⚠️  Error logging to CSV: {e}")
    
    def _update_progress(self, completed: int, total: int, current_result: OptimizationResult) -> None:
        """Update progress file with current status"""
        if not self.progress_file_key:
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
Current Best PnL/Drawdown Ratio: {max([r.final_pnl/(r.max_drawdown+0.01) for r in self.results]) if self.results else 0:,.2f}
Last Result: PnL=${current_result.final_pnl:,.2f}, DD={current_result.max_drawdown:.1f}%, PnL/DD={(current_result.final_pnl/(current_result.max_drawdown+0.01)):.2f}, Trades={current_result.total_trades}
"""
            
            self.optimization_transport.save_text(self.progress_file_key, progress_info)
                
        except Exception as e:
            if self.verbose:
                print(f"⚠️  Error updating progress: {e}")
    
    def _plot_equity_curve(self, params: Dict[str, Any], equity_curve: pd.Series, 
                          equity_dates: pd.DatetimeIndex, final_pnl: float) -> None:
        """Plot and save equity curve for a parameter combination"""
        if not self.plot_equity_curves:
            return
            
        try:
            # Create a filename based on symbol, timeframe, parameters and performance
            symbol_id = self._get_symbol_identifier()
            param_str = "_".join([f"{k}{v}" for k, v in params.items()])
            # Limit filename length and sanitize
            param_str = param_str[:30].replace('.', '_').replace('-', '_')
            pnl_str = f"PnL{final_pnl:.0f}".replace('-', 'neg')
            plot_key = f"plots/{symbol_id}_{self.timeframe}_equity_{param_str}_{pnl_str}.png"
            
            # Note: For now, equity curves will need to be handled differently with S3
            # This would require either saving locally first, or implementing binary upload
            # TODO: Implement plot upload to transport layer
            
            if self.verbose:
                print(f"📊 Equity curve plotting with transport layer not yet implemented")
                
        except Exception as e:
            if self.verbose:
                print(f"⚠️  Error plotting equity curve: {e}")

    def _plot_orders(self, params: Dict[str, Any], order_log: list, final_pnl: float) -> None:
        """Plot and save order analysis for a parameter combination"""
        if not self.plot_orders:
            return
            
        try:
            # Create a filename based on symbol, timeframe, parameters and performance
            symbol_id = self._get_symbol_identifier()
            param_str = "_".join([f"{k}{v}" for k, v in params.items()])
            # Limit filename length and sanitize
            param_str = param_str[:30].replace('.', '_').replace('-', '_')
            pnl_str = f"PnL{final_pnl:.0f}".replace('-', 'neg')
            orders_subdir = f"{symbol_id}_{self.timeframe}_orders_{param_str}_{pnl_str}"
            
            # Note: For now, order plots will need to be handled differently with S3
            # This would require either saving locally first, or implementing binary upload
            # TODO: Implement order plot upload to transport layer
            
            if self.verbose:
                print(f"📈 Order plotting with transport layer not yet implemented")
            
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
                # For cached results, we don't count execution time in averages
                return cached_result
            
            # Prepare strategy parameters
            strategy_params = self._prepare_strategy_params(params)
            
            # Run backtest with configurable logging
            backtest_start = time.time()
            equity_curve, equity_dates, trade_log, order_log = run_backtest(
                data=self.data,
                strategy_class=MeanReversionStrategy,
                params=strategy_params,
                verbose=self.verbose
            )
            backtest_time = time.time() - backtest_start
            
            # Track backtest execution time for averaging
            self.backtest_times.append(backtest_time)
            
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
            
            # Accumulate orders for CSV export
            if order_log is not None and len(order_log) > 0:
                self.optimization_run_counter += 1
                self.order_accumulator.add_optimization_run(
                    run_number=self.optimization_run_counter,
                    order_log=order_log,
                    optimization_params=params
                )
                # Order accumulator now prints its own message
            
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
        
        # Add timeframe for optimization
        strategy_params['timeframe'] = self.timeframe
        
        return strategy_params
    
    def grid_search(
        self,
        param_grid: Dict[str, List],
        optimization_name: str = "grid_search",
        max_workers: Optional[int] = None,
        sort_objective: str = "balanced"
    ) -> List[OptimizationResult]:
        """
        Perform grid search optimization
        
        Args:
            param_grid: Dictionary of parameter names and value lists
            optimization_name: Name for this optimization run
            max_workers: Number of parallel workers (None for sequential)
            sort_objective: Sorting objective from OPTIMIZATION_OBJECTIVES
        
        Returns:
            List of optimization results sorted by selected objective
        """
        # Import objectives
        from src.optimization_configs import OPTIMIZATION_OBJECTIVES
        
        print("="*80)
        print(f"🔍 STARTING GRID SEARCH OPTIMIZATION: {optimization_name}")
        print("="*80)
        
        # Load market data
        self._load_market_data()
        
        # Setup result files
        self._setup_result_files(optimization_name)
        
        # Setup order accumulator with optimization type
        self._setup_order_accumulator(optimization_name)
        
        # Generate parameter combinations
        keys, values = zip(*param_grid.items())
        param_combinations = list(itertools.product(*values))
        total_combinations = len(param_combinations)
        
        print(f"📊 Parameter grid:")
        for key, value_list in param_grid.items():
            print(f"  {key}: {value_list}")
        print(f"🔢 Total combinations to test: {total_combinations:,}")
        print(f"🎯 Optimization objective: {sort_objective}")
        
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
        
        # Get the sorting function from objectives
        sort_function = OPTIMIZATION_OBJECTIVES.get(sort_objective, OPTIMIZATION_OBJECTIVES['balanced'])
        
        # Sort results by the selected objective (descending)
        self.results.sort(key=sort_function, reverse=True)
        
        # Save best results
        self._save_best_results()
        
        # Save accumulated orders to CSV
        self._save_orders_to_csv()
        
        # Print summary
        self._print_optimization_summary()
        
        return self.results
    
    def _run_sequential_optimization(self, param_combinations: List, keys: List[str]) -> None:
        """Run optimization sequentially"""
        for i, combo in enumerate(param_combinations, 1):
            params = dict(zip(keys, combo))
            
            print(f"\n🔄 [{i}/{len(param_combinations)}] Testing: {params}")
            
            run_start = time.time()
            result = self._run_single_backtest(params)
            run_time = time.time() - run_start
            
            self.results.append(result)
            
            # Log to CSV
            self._log_result_to_csv(result)
            
            # Update progress
            self._update_progress(i, len(param_combinations), result)
            
            # Calculate average backtest time (excluding cached results)
            avg_backtest_time = np.mean(self.backtest_times) if self.backtest_times else 0
            
            # Print results with timing information
            cached_marker = " (cached)" if len(self.backtest_times) < i else ""
            print(f"   💰 PnL: ${result.final_pnl:,.2f} | Trades: {result.total_trades} | WinRate: {result.win_rate:.1f}% | Sharpe: {result.sharpe_ratio:.2f}")
            print(f"   ⏱️  Run time: {run_time:.2f}s | Avg backtest time: {avg_backtest_time:.2f}s{cached_marker}")
    
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
            
            # Prepare best results summary
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
            
            # Save to transport
            if self.optimization_transport.save_json(self.best_params_file_key, best_summary):
                print(f"💾 Best results saved to: {self.best_params_file_key}")
            else:
                print(f"⚠️  Error saving best results to: {self.best_params_file_key}")
            
        except Exception as e:
            print(f"⚠️  Error saving best results: {e}")
    
    def _print_optimization_summary(self) -> None:
        """Print optimization summary"""
        if not self.results:
            print("❌ No results to display")
            return
        
        total_time = time.time() - self.start_time
        avg_backtest_time = np.mean(self.backtest_times) if self.backtest_times else 0
        total_backtests_run = len(self.backtest_times)
        cached_results = len(self.results) - total_backtests_run
        
        print("\n" + "="*80)
        print("📊 OPTIMIZATION COMPLETE")
        print("="*80)
        print(f"⏱️  Total Time: {total_time/60:.1f} minutes")
        print(f"⚡ Average Backtest Time: {avg_backtest_time:.2f}s")
        print(f"🔢 Total Tests: {len(self.results):,}")
        print(f"🆕 New Backtests Run: {total_backtests_run:,}")
        print(f"� Cached Results Used: {cached_results:,}")
        print(f"�📈 Results saved to: {self.results_csv_key}")
        
        if self.best_results:
            print(f"\n🏆 BEST RESULTS:")
            print("-" * 50)
            
            for metric_name, result in self.best_results.items():
                print(f"\n{metric_name.upper()}:")
                print(f"  💰 Final PnL: ${result.final_pnl:,.2f}")
                print(f"  📊 Sharpe Ratio: {result.sharpe_ratio:.2f}")
                print(f"  🎯 Win Rate: {result.win_rate:.1f}%")
                print(f"  📉 Max Drawdown: {result.max_drawdown:.1f}%")
                
                # Calculate the PnL-to-Drawdown ratio (for balanced optimization)
                pnl_drawdown_ratio = result.final_pnl / (result.max_drawdown + 0.01)  # Add small value to avoid div by zero
                print(f"  🏆 PnL/Drawdown Ratio: {pnl_drawdown_ratio:.2f}")
                
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
        optimization_name: str = "random_search",
        sort_objective: str = "balanced"
    ) -> List[OptimizationResult]:
        """
        Perform random search optimization
        
        Args:
            param_ranges: Dictionary of parameter names and ranges/choices
            n_iterations: Number of random combinations to test
            optimization_name: Name for this optimization run
            sort_objective: Sorting objective from OPTIMIZATION_OBJECTIVES
        
        Returns:
            List of optimization results sorted by selected objective
        """
        # Import objectives
        from src.optimization_configs import OPTIMIZATION_OBJECTIVES
        
        print("="*80)
        print(f"🎲 STARTING RANDOM SEARCH OPTIMIZATION: {optimization_name}")
        print("="*80)
        
        # Load market data
        self._load_market_data()
        
        # Setup result files
        self._setup_result_files(optimization_name)
        
        # Setup order accumulator with optimization type
        self._setup_order_accumulator(optimization_name)
        
        print(f"🔢 Running {n_iterations:,} random parameter combinations")
        print(f"🎯 Optimization objective: {sort_objective}")
        
        self.start_time = time.time()
        self.results = []
        
        for i in range(1, n_iterations + 1):
            # Generate random parameters
            params = self._generate_random_params(param_ranges)
            
            print(f"\n🔄 [{i}/{n_iterations}] Testing: {params}")
            
            run_start = time.time()
            result = self._run_single_backtest(params)
            run_time = time.time() - run_start
            
            self.results.append(result)
            
            # Log to CSV
            self._log_result_to_csv(result)
            
            # Update progress
            self._update_progress(i, n_iterations, result)
            
            # Calculate average backtest time (excluding cached results)
            avg_backtest_time = np.mean(self.backtest_times) if self.backtest_times else 0
            
            # Print results with timing information
            cached_marker = " (cached)" if len(self.backtest_times) < i else ""
            print(f"   💰 PnL: ${result.final_pnl:,.2f} | Trades: {result.total_trades} | WinRate: {result.win_rate:.1f}% | Sharpe: {result.sharpe_ratio:.2f}")
            print(f"   ⏱️  Run time: {run_time:.2f}s | Avg backtest time: {avg_backtest_time:.2f}s{cached_marker}")
        
        # Get the sorting function from objectives
        sort_function = OPTIMIZATION_OBJECTIVES.get(sort_objective, OPTIMIZATION_OBJECTIVES['balanced'])
        
        # Sort results by the selected objective (descending)
        self.results.sort(key=sort_function, reverse=True)
        
        # Save best results
        self._save_best_results()
        
        # Save accumulated orders to CSV
        self._save_orders_to_csv()
        
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


    def _save_orders_to_csv(self) -> None:
        """
        Print summary of order saving (orders are saved immediately after each run)
        """
        try:
            csv_info = self.order_accumulator.get_csv_info()
            total_orders = csv_info.get('total_orders', 0)
            session_orders = csv_info.get('session_orders', 0)
            
            if session_orders > 0:
                print(f"\n📋 Order Summary:")
                print(f"   📄 File: {csv_info['csv_key']}")
                print(f"   � Session orders: {session_orders}")
                print(f"   📊 Total orders in file: {total_orders}")
                print(f"   🔄 Optimization runs: {csv_info.get('unique_runs', 0)}")
                print(f"   ✅ Orders saved automatically after each optimization run")
            else:
                print(f"\n📋 No orders generated during optimization")
                
        except Exception as e:
            print(f"❌ Error getting order summary: {e}")


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

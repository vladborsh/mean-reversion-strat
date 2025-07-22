#!/usr/bin/env python3
"""
Hyperparameter Optimization Runner

This script provides a command-line interface to run various hyperparameter
optimization scenarios for the mean reversion strategy.

Usage:
    python optimize_strategy.py --help
    python optimize_strategy.py --grid-search focused
    python optimize_strategy.py --random-search 100
    python optimize_strategy.py --risk-optimization
"""

import argparse
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.append(str(project_root))

from src.hyperparameter_optimizer import HyperparameterOptimizer, ParameterGrid
from src.optimization_configs import OPTIMIZATION_CONFIGS, RANDOM_SEARCH_RANGES


def run_grid_search(optimizer, grid_type='focused', sort_objective='balanced'):
    """Run grid search optimization"""
    print(f"🔍 Running grid search optimization: {grid_type}")
    print(f"🎯 Optimization objective: {sort_objective}")
    
    if grid_type in OPTIMIZATION_CONFIGS:
        param_grid = OPTIMIZATION_CONFIGS[grid_type]()
    else:
        # Fallback to ParameterGrid methods for backward compatibility
        if grid_type == 'default':
            param_grid = ParameterGrid.create_default_grid()
        elif grid_type == 'focused':
            param_grid = ParameterGrid.create_focused_grid()
        elif grid_type == 'risk':
            param_grid = ParameterGrid.create_risk_focused_grid()
        else:
            raise ValueError(f"Unknown grid type: {grid_type}. Available: {list(OPTIMIZATION_CONFIGS.keys())}")
    
    results = optimizer.grid_search(
        param_grid=param_grid,
        optimization_name=f"grid_search_{grid_type}",
        sort_objective=sort_objective
    )
    
    return results


def run_random_search(optimizer, n_iterations=100, sort_objective='balanced'):
    """Run random search optimization"""
    print(f"🎲 Running random search optimization: {n_iterations} iterations")
    print(f"🎯 Optimization objective: {sort_objective}")
    
    # Use the predefined parameter ranges
    param_ranges = RANDOM_SEARCH_RANGES
    
    results = optimizer.random_search(
        param_ranges=param_ranges,
        n_iterations=n_iterations,
        optimization_name=f"random_search_{n_iterations}",
        sort_objective=sort_objective
    )
    
    return results


def run_quick_test(optimizer, sort_objective='balanced'):
    """Run a quick test with a small parameter grid"""
    print("⚡ Running quick test optimization")
    print(f"🎯 Optimization objective: {sort_objective}")
    
    # Use the balanced grid for quick tests when using balanced objective
    if sort_objective == 'balanced':
        param_grid = OPTIMIZATION_CONFIGS['balanced']()
        # Use a subset to make it quicker
        param_grid = {k: v[:2] for k, v in param_grid.items()}
    else:
        param_grid = OPTIMIZATION_CONFIGS['quick']()
    
    results = optimizer.grid_search(
        param_grid=param_grid,
        optimization_name="quick_test",
        sort_objective=sort_objective
    )
    
    return results


def main():
    parser = argparse.ArgumentParser(
        description='Run hyperparameter optimization for mean reversion strategy',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python optimize_strategy.py --quick-test
  python optimize_strategy.py --grid-search focused --plot-equity-curves --plot-orders
  python optimize_strategy.py --grid-search balanced --sort-objective balanced --plot-equity-curves
  python optimize_strategy.py --random-search 50 --sort-objective balanced --quiet
  python optimize_strategy.py --symbol GBPUSD=X --timeframe 1h --plot-equity-curves --plot-orders
        """
    )
    
    # Optimization type (mutually exclusive)
    opt_group = parser.add_mutually_exclusive_group(required=True)
    opt_group.add_argument('--quick-test', action='store_true',
                          help='Run quick test with small parameter grid')
    opt_group.add_argument('--grid-search', 
                          choices=['focused', 'comprehensive', 'risk', 'indicators', 'regime', 
                                 'trending', 'ranging', 'high_vol', 'low_vol', 'scalping', 'swing', 'balanced'],
                          help='Run grid search optimization with specified configuration')
    opt_group.add_argument('--random-search', type=int, metavar='N',
                          help='Run random search with N iterations')
    
    # Data parameters
    parser.add_argument('--symbol', default='EURUSD=X',
                       help='Trading symbol (default: EURUSD=X)')
    parser.add_argument('--source', default='forex',
                       help='Data source (default: forex)')
    parser.add_argument('--timeframe', default='15m',
                       help='Data timeframe (default: 15m)')
    parser.add_argument('--years', type=int, default=2,
                       help='Years of historical data (default: 2)')
    
    # Transport configuration
    parser.add_argument('--cache-transport', default='local',
                       choices=['local', 's3'],
                       help='Cache transport type (default: local)')
    parser.add_argument('--log-transport', default='local',
                       choices=['local', 's3'],
                       help='Log transport type (default: local)')
    
    # Optimization parameters
    parser.add_argument('--sort-objective', default='balanced',
                       choices=['max_pnl', 'max_sharpe', 'max_winrate', 
                               'min_drawdown', 'risk_adjusted', 'profit_factor', 'balanced'],
                       help='Optimization objective to sort results (default: balanced)')
    
    # Output directory
    parser.add_argument('--output-dir', default=None,
                       help='Output directory for results (default: optimization/)')
    
    # Visualization options
    parser.add_argument('--plot-equity-curves', action='store_true',
                       help='Save equity curve plots for each optimization run')
    parser.add_argument('--plot-orders', action='store_true',
                       help='Save order analysis plots for each optimization run')
    parser.add_argument('--quiet', action='store_true',
                       help='Reduce console output during optimization')
    
    args = parser.parse_args()
    
    # Initialize optimizer
    print("🚀 Initializing hyperparameter optimizer...")
    print(f"🔧 Cache Transport: {args.cache_transport}")
    print(f"📊 Log Transport: {args.log_transport}")
    
    optimizer = HyperparameterOptimizer(
        data_source=args.source,
        symbol=args.symbol,
        timeframe=args.timeframe,
        years=args.years,
        optimization_dir=args.output_dir,
        plot_equity_curves=args.plot_equity_curves,
        plot_orders=args.plot_orders,
        verbose=not args.quiet,
        cache_transport_type=args.cache_transport,
        log_transport_type=args.log_transport
    )
    
    # Run optimization based on arguments
    try:
        if args.quick_test:
            results = run_quick_test(optimizer, args.sort_objective)
        elif args.grid_search:
            results = run_grid_search(optimizer, args.grid_search, args.sort_objective)
        elif args.random_search:
            results = run_random_search(optimizer, args.random_search, args.sort_objective)
        
        # Print final summary
        if results:
            print("\n" + "="*80)
            print("🎉 OPTIMIZATION COMPLETED SUCCESSFULLY!")
            print("="*80)
            print(f"🏆 Best Result: ${results[0].final_pnl:,.2f}")
            print(f"📊 Total Tests: {len(results):,}")
            print(f"💾 Results saved in: {optimizer.results_dir}")
        else:
            print("❌ No results generated")
            
    except KeyboardInterrupt:
        print("\n⚠️  Optimization interrupted by user")
        if hasattr(optimizer, 'results') and optimizer.results:
            print(f"📊 Partial results available: {len(optimizer.results)} tests completed")
    except Exception as e:
        print(f"❌ Error during optimization: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

"""
Example Usage of Hyperparameter Optimizer

This script demonstrates how to use the hyperparameter optimizer
with different configurations and scenarios.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.append(str(project_root))

from src.hyperparameter_optimizer import HyperparameterOptimizer
from src.optimization_configs import OPTIMIZATION_CONFIGS


def example_quick_test():
    """Run a quick test optimization (fast execution)"""
    print("🚀 Example: Quick Test Optimization")
    print("="*50)
    
    optimizer = HyperparameterOptimizer(
        data_source='forex',
        symbol='EURUSD=X',
        timeframe='15m',
        years=1  # Use 1 year for faster testing
    )
    
    # Run quick test with small parameter grid
    param_grid = OPTIMIZATION_CONFIGS['quick']()
    print(f"Parameter combinations: {len(list(param_grid.values())[0]) ** len(param_grid)}")
    
    results = optimizer.grid_search(
        param_grid=param_grid,
        optimization_name="example_quick_test"
    )
    
    if results:
        best = results[0]
        print(f"\n🏆 Best Result:")
        print(f"   Final PnL: ${best.final_pnl:,.2f}")
        print(f"   Win Rate: {best.win_rate:.1f}%")
        print(f"   Sharpe: {best.sharpe_ratio:.2f}")
        print(f"   Parameters: {best.parameters}")
    
    return results


def example_focused_optimization():
    """Run focused optimization on key parameters"""
    print("🎯 Example: Focused Optimization")
    print("="*50)
    
    optimizer = HyperparameterOptimizer(
        data_source='forex',
        symbol='EURUSD=X',
        timeframe='15m',
        years=2
    )
    
    # Run focused optimization
    param_grid = OPTIMIZATION_CONFIGS['focused']()
    
    results = optimizer.grid_search(
        param_grid=param_grid,
        optimization_name="example_focused"
    )
    
    return results


def example_risk_optimization():
    """Run risk management focused optimization"""
    print("🛡️ Example: Risk Management Optimization")
    print("="*50)
    
    optimizer = HyperparameterOptimizer(
        data_source='forex',
        symbol='GBPUSD=X',  # Different symbol
        timeframe='1h',      # Different timeframe
        years=2
    )
    
    # Run risk-focused optimization
    param_grid = OPTIMIZATION_CONFIGS['risk']()
    
    results = optimizer.grid_search(
        param_grid=param_grid,
        optimization_name="example_risk_management"
    )
    
    return results


def example_random_search():
    """Run random search optimization"""
    print("🎲 Example: Random Search Optimization")
    print("="*50)
    
    optimizer = HyperparameterOptimizer(
        data_source='forex',
        symbol='EURUSD=X',
        timeframe='15m',
        years=2
    )
    
    # Run random search
    from src.optimization_configs import RANDOM_SEARCH_RANGES
    
    results = optimizer.random_search(
        param_ranges=RANDOM_SEARCH_RANGES,
        n_iterations=25,  # Small number for example
        optimization_name="example_random_search"
    )
    
    return results


def example_compare_configurations():
    """Compare different optimization configurations"""
    print("📊 Example: Compare Different Configurations")
    print("="*50)
    
    optimizer = HyperparameterOptimizer(
        data_source='forex',
        symbol='EURUSD=X',
        timeframe='15m',
        years=1  # Shorter period for faster comparison
    )
    
    # Test different configurations
    configs_to_test = ['quick', 'risk', 'indicators']
    all_results = {}
    
    for config_name in configs_to_test:
        print(f"\n🔄 Testing configuration: {config_name}")
        
        param_grid = OPTIMIZATION_CONFIGS[config_name]()
        
        results = optimizer.grid_search(
            param_grid=param_grid,
            optimization_name=f"compare_{config_name}"
        )
        
        all_results[config_name] = results
        
        if results:
            best = results[0]
            print(f"   Best PnL: ${best.final_pnl:,.2f}")
            print(f"   Best Win Rate: {best.win_rate:.1f}%")
    
    # Compare results
    print(f"\n📈 COMPARISON RESULTS:")
    print("-" * 40)
    for config_name, results in all_results.items():
        if results:
            best = results[0]
            print(f"{config_name:12}: ${best.final_pnl:>8,.0f} | WR: {best.win_rate:>5.1f}%")
    
    return all_results


def main():
    """Run example optimizations"""
    
    print("🔬 HYPERPARAMETER OPTIMIZATION EXAMPLES")
    print("="*60)
    
    examples = [
        ("Quick Test", example_quick_test),
        ("Focused Optimization", example_focused_optimization),
        ("Risk Management", example_risk_optimization),
        ("Random Search", example_random_search),
        ("Compare Configurations", example_compare_configurations),
    ]
    
    # Run interactive menu
    while True:
        print(f"\nSelect an example to run:")
        print("-" * 30)
        for i, (name, _) in enumerate(examples, 1):
            print(f"{i}. {name}")
        print("0. Exit")
        
        try:
            choice = input("\nEnter your choice (0-5): ").strip()
            
            if choice == '0':
                print("👋 Goodbye!")
                break
            elif choice.isdigit() and 1 <= int(choice) <= len(examples):
                idx = int(choice) - 1
                name, func = examples[idx]
                
                print(f"\n{'='*20}")
                print(f"Running: {name}")
                print(f"{'='*20}")
                
                try:
                    results = func()
                    print(f"\n✅ {name} completed successfully!")
                except Exception as e:
                    print(f"\n❌ Error in {name}: {e}")
                
                input("\nPress Enter to continue...")
            else:
                print("❌ Invalid choice. Please enter a number between 0-5.")
                
        except KeyboardInterrupt:
            print("\n👋 Goodbye!")
            break
        except Exception as e:
            print(f"❌ Error: {e}")


if __name__ == "__main__":
    main()

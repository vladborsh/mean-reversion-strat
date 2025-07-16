"""
Example: Using Different Strategy Configurations

This example demonstrates how to use different strategy configurations
and risk management settings for the mean reversion strategy.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.strategy_config import StrategyConfig, AggressiveConfig, ConservativeConfig


def main():
    """Demonstrate different configuration usage"""
    
    print("=== STRATEGY CONFIGURATION EXAMPLES ===\n")
    
    # Default configuration
    print("1. DEFAULT CONFIGURATION:")
    default_config = StrategyConfig.get_all_config()
    print_config(default_config)
    
    # Aggressive configuration
    print("\n2. AGGRESSIVE CONFIGURATION:")
    aggressive_config = AggressiveConfig.get_all_config()
    print_config(aggressive_config)
    
    # Conservative configuration
    print("\n3. CONSERVATIVE CONFIGURATION:")
    conservative_config = ConservativeConfig.get_all_config()
    print_config(conservative_config)
    
    # Custom configuration example
    print("\n4. CUSTOM CONFIGURATION EXAMPLE:")
    custom_config = StrategyConfig()
    custom_config.update_config(
        risk_management={
            'risk_per_position_pct': 1.5,
            'stop_loss_atr_multiplier': 1.5,
            'risk_reward_ratio': 3.0,
            'atr_period': 12
        }
    )
    print_config(custom_config.get_all_config())
    
    # Show backtrader parameters format
    print("\n5. BACKTRADER PARAMETERS FORMAT:")
    bt_params = StrategyConfig.get_backtrader_params()
    for key, value in bt_params.items():
        print(f"  {key}: {value}")


def print_config(config):
    """Print configuration in a readable format"""
    for section, params in config.items():
        print(f"  {section.upper().replace('_', ' ')}:")
        if isinstance(params, dict):
            for key, value in params.items():
                print(f"    {key}: {value}")
        else:
            print(f"    {params}")


if __name__ == "__main__":
    main()

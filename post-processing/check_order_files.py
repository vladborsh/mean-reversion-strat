#!/usr/bin/env python3
"""
Validate that order files exist for all configurations in best_configs

This utility helps diagnose missing order files before running generate_config_pnl.py
"""
import json
import argparse
from pathlib import Path


def check_order_files(config_file: Path, orders_dir: Path):
    """Check which configs have corresponding order files"""
    
    print(f"Checking order files for: {config_file.name}")
    print(f"Orders directory: {orders_dir}")
    print("=" * 60)
    
    # Load configs
    with open(config_file, 'r') as f:
        configs = json.load(f)
    
    print(f"\nFound {len(configs)} configurations\n")
    
    found = []
    missing = []
    
    for config_key, config in configs.items():
        symbol = config['ASSET_INFO']['symbol']
        timeframe = config['ASSET_INFO']['timeframe']
        run_id = config['METADATA']['run_id']
        
        # Search for order files
        patterns = [
            f"{symbol}_{timeframe}_*_orders.csv",
            f"{symbol}_{timeframe}_orders.csv",
        ]
        
        order_files = []
        for pattern in patterns:
            order_files.extend(list(orders_dir.glob(pattern)))
        
        status = "✅" if order_files else "❌"
        print(f"{status} run_id={run_id:2d} | {config_key:20s} | ", end="")
        
        if order_files:
            # Show matched file
            order_file = sorted(order_files)[-1]
            print(f"Found: {order_file.name}")
            found.append(config_key)
        else:
            print(f"Missing order file")
            missing.append(config_key)
    
    print("\n" + "=" * 60)
    print(f"\nSummary:")
    print(f"  ✅ Found: {len(found)}")
    print(f"  ❌ Missing: {len(missing)}")
    
    if missing:
        print(f"\nMissing order files for:")
        for key in missing:
            config = configs[key]
            symbol = config['ASSET_INFO']['symbol']
            timeframe = config['ASSET_INFO']['timeframe']
            print(f"  - {key} (need: {symbol}_{timeframe}_*_orders.csv)")
    
    print()
    
    return len(found), len(missing)


def main():
    parser = argparse.ArgumentParser(
        description="Check if order files exist for all configurations"
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
    
    args = parser.parse_args()
    
    config_file = Path(args.config_file)
    orders_dir = Path(args.orders_dir)
    
    # Validate inputs
    if not config_file.exists():
        print(f"❌ Config file not found: {config_file}")
        return 1
    
    if not orders_dir.exists():
        print(f"❌ Orders directory not found: {orders_dir}")
        return 1
    
    # Check files
    found, missing = check_order_files(config_file, orders_dir)
    
    return 0 if missing == 0 else 1


if __name__ == '__main__':
    exit(main())

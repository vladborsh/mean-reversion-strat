#!/usr/bin/env python3
"""
Analyze batch optimization results and generate per-asset configurations

This script processes all optimization results from batch-analysis folder
and generates optimized configurations for each asset/timeframe combination.
"""
import pandas as pd
import json
import numpy as np
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import ast
import re
import os
import argparse
from datetime import datetime

class BatchResultsAnalyzer:
    """Analyzes batch optimization results and generates configurations"""
    
    def __init__(self, results_dir: str = 'batch-analysis', output_dir: str = 'results'):
        self.results_dir = Path(results_dir)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        
    def extract_metadata_from_filename(self, filename: str) -> Dict[str, str]:
        """Extract symbol, timeframe, and optimization type from filename"""
        # Expected formats:
        # BTCUSDX_5m_grid_search_focused_20250725_144121.csv
        # EURUSDX_15m_best_params_grid_search_focused_20250725_143052.json
        
        parts = filename.replace('.csv', '').replace('.json', '').split('_')
        
        metadata = {
            'symbol': 'Unknown',
            'timeframe': 'Unknown', 
            'optimization_type': 'Unknown',
            'date': 'Unknown'
        }
        
        if len(parts) >= 4:
            # Extract symbol (keep original format)
            metadata['symbol'] = parts[0]
                
            # Extract timeframe
            metadata['timeframe'] = parts[1]
            
            # Extract optimization type (focused, balanced, etc.)
            if len(parts) >= 5:
                metadata['optimization_type'] = parts[3]  # Skip 'grid_search'
            
            # Extract date
            if len(parts) >= 6:
                metadata['date'] = parts[4]
        
        return metadata
        
    def _parse_csv_with_dict_column(self, file_path: Path) -> pd.DataFrame:
        """Parse CSV file that contains dictionary in parameters column"""
        import csv
        import io
        
        with open(file_path, 'r') as f:
            content = f.read()
        
        # Split into lines
        lines = content.strip().split('\n')
        header = lines[0]
        data_lines = lines[1:]
        
        # Parse each line manually to handle dictionary in parameters
        parsed_rows = []
        
        for line in data_lines:
            # Split by comma but respect braces
            parts = []
            current_part = ""
            brace_count = 0
            in_quotes = False
            
            for char in line:
                if char == '"' and (not current_part or current_part[-1] != '\\'):
                    in_quotes = not in_quotes
                elif char == '{' and not in_quotes:
                    brace_count += 1
                elif char == '}' and not in_quotes:
                    brace_count -= 1
                elif char == ',' and brace_count == 0 and not in_quotes:
                    parts.append(current_part.strip())
                    current_part = ""
                    continue
                
                current_part += char
            
            if current_part:
                parts.append(current_part.strip())
            
            # Should have 8 parts for our CSV structure
            if len(parts) == 8:
                parsed_rows.append(parts)
            else:
                print(f"Warning: Line has {len(parts)} parts instead of 8: {line[:100]}...")
        
        # Create DataFrame
        column_names = header.split(',')
        df = pd.DataFrame(parsed_rows, columns=column_names)
        
        return df

    def load_csv_results(self) -> pd.DataFrame:
        """Load all CSV results and combine them"""
        all_results = []
        
        csv_files = list(self.results_dir.glob("*.csv"))
        print(f"Found {len(csv_files)} CSV result files")
        
        for csv_file in csv_files:
            try:
                # Use custom parser to handle dictionary in parameters column
                df = self._parse_csv_with_dict_column(csv_file)
                
                if len(df) == 0:
                    print(f"Warning: Empty file {csv_file.name}")
                    continue
                
                print(f"Debug: {csv_file.name} initial rows: {len(df)}")
                
                # Convert numeric columns to proper types
                numeric_columns = ['final_pnl', 'total_trades', 'win_rate', 'sharpe_ratio', 
                                 'max_drawdown', 'execution_time']
                for col in numeric_columns:
                    if col in df.columns:
                        # Check initial data type
                        original_dtype = df[col].dtype
                        df[col] = pd.to_numeric(df[col], errors='coerce')
                        # Count how many values were converted to NaN
                        nan_count = df[col].isna().sum()
                        if nan_count > 0:
                            print(f"Warning: {col} had {nan_count} non-numeric values (dtype was {original_dtype})")
                
                # Only remove rows where ALL critical columns are NaN
                critical_columns = ['final_pnl', 'total_trades', 'win_rate']
                before_cleaning = len(df)
                df = df.dropna(subset=critical_columns, how='all')
                after_cleaning = len(df)
                
                if before_cleaning != after_cleaning:
                    print(f"Debug: Removed {before_cleaning - after_cleaning} rows with all NaN critical values")
                
                if len(df) == 0:
                    print(f"Warning: No valid data remaining in {csv_file.name}")
                    continue
                
                # Add metadata from filename
                metadata = self.extract_metadata_from_filename(csv_file.name)
                for key, value in metadata.items():
                    df[key] = value
                    
                df['source_file'] = csv_file.name
                all_results.append(df)
                print(f"✅ Loaded {len(df)} results from {csv_file.name} ({metadata['symbol']})")
                
            except Exception as e:
                print(f"❌ Error loading {csv_file}: {e}")
                import traceback
                traceback.print_exc()
                continue
        
        if not all_results:
            raise ValueError("No valid CSV results found!")
        
        combined_df = pd.concat(all_results, ignore_index=True)
        print(f"\n📊 Total results loaded: {len(combined_df)}")
        
        # Debug: show data types
        print("Debug: Final data types:")
        for col in ['final_pnl', 'total_trades', 'win_rate', 'max_drawdown']:
            if col in combined_df.columns:
                print(f"  {col}: {combined_df[col].dtype}, NaN count: {combined_df[col].isna().sum()}")
        
        return combined_df
    
    def parse_parameters(self, param_str) -> Dict:
        """Safely parse parameter string"""
        try:
            if isinstance(param_str, str):
                # Handle string representation of dict
                param_str = param_str.replace('false', 'False').replace('true', 'True')
                return ast.literal_eval(param_str)
            elif isinstance(param_str, dict):
                return param_str
            else:
                return {}
        except Exception as e:
            print(f"Warning: Could not parse parameters: {param_str[:100]}... Error: {e}")
            return {}
    
    def filter_valid_results(self, df: pd.DataFrame, min_trades: int = 10, 
                           min_win_rate: float = 15.0, max_drawdown: float = 50.0) -> pd.DataFrame:
        """Filter results to remove obviously bad configurations"""
        print(f"\n🔍 Filtering results (min_trades={min_trades}, min_win_rate={min_win_rate}%, max_drawdown={max_drawdown}%)")
        
        initial_count = len(df)
        
        # Ensure numeric columns are properly typed
        numeric_columns = ['final_pnl', 'total_trades', 'win_rate', 'sharpe_ratio', 'max_drawdown']
        for col in numeric_columns:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        
        # Remove rows with NaN values in critical columns
        df_clean = df.dropna(subset=['final_pnl', 'total_trades', 'win_rate', 'max_drawdown']).copy()
        
        if len(df_clean) < len(df):
            print(f"🧹 Removed {len(df) - len(df_clean)} rows with missing data")
        
        # Apply filters
        try:
            filtered_df = df_clean[
                (df_clean['total_trades'] >= min_trades) &
                (df_clean['win_rate'] >= min_win_rate) &
                (df_clean['max_drawdown'] <= max_drawdown) &
                (df_clean['final_pnl'] > 0)  # Only profitable strategies
            ].copy()
        except Exception as e:
            print(f"❌ Error applying filters: {e}")
            print("Data types:")
            for col in ['total_trades', 'win_rate', 'max_drawdown', 'final_pnl']:
                if col in df_clean.columns:
                    print(f"  {col}: {df_clean[col].dtype}")
            raise
        
        final_count = len(filtered_df)
        filtered_count = initial_count - final_count
        
        if initial_count > 0:
            print(f"📊 Filtered out {filtered_count} results ({filtered_count/initial_count*100:.1f}%)")
        else:
            print(f"📊 No initial results to filter")
        print(f"📊 Remaining: {final_count} valid results")
        
        return filtered_df
    
    def get_best_configs_by_objective(self, df: pd.DataFrame, objective: str = 'final_pnl') -> Dict:
        """Get best configuration for each asset/timeframe combination by objective"""
        print(f"\n🎯 Finding best configurations by {objective}")
        
        best_configs = {}
        
        # Group by symbol and timeframe
        grouped = df.groupby(['symbol', 'timeframe'])
        
        for (symbol, timeframe), group in grouped:
            if symbol == 'Unknown':
                continue
                
            # Find best result based on objective
            if objective == 'win_rate':
                # For win rate, ensure decent profitability
                valid_group = group[group['final_pnl'] > group['final_pnl'].quantile(0.25)]
                if len(valid_group) == 0:
                    valid_group = group
                best_idx = valid_group[objective].idxmax()
            elif objective == 'max_drawdown':
                # For drawdown, minimize (find minimum)
                best_idx = group[objective].idxmin()
            elif objective == 'balanced':
                # Balanced approach: normalize PnL and drawdown, then combine
                # Higher PnL is better, lower drawdown is better
                pnl_normalized = (group['final_pnl'] - group['final_pnl'].min()) / (group['final_pnl'].max() - group['final_pnl'].min() + 1e-8)
                dd_normalized = 1 - (group['max_drawdown'] - group['max_drawdown'].min()) / (group['max_drawdown'].max() - group['max_drawdown'].min() + 1e-8)
                # Combine with equal weights (can be adjusted)
                balanced_score = 0.6 * pnl_normalized + 0.4 * dd_normalized
                best_idx = balanced_score.idxmax()
            else:
                # For PnL and other metrics, maximize
                best_idx = group[objective].idxmax()
                
            best_result = group.loc[best_idx]
            
            # Parse parameters
            params = self.parse_parameters(best_result['parameters'])
            if not params:
                print(f"Warning: Could not parse parameters for {symbol}_{timeframe}")
                continue
            
            asset_key = f"{symbol}_{timeframe}"
            best_configs[asset_key] = {
                'symbol': symbol,
                'timeframe': timeframe,
                'optimization_type': best_result['optimization_type'],
                'optimization_date': best_result['date'],
                'performance': {
                    'final_pnl': float(best_result['final_pnl']),
                    'total_trades': int(best_result['total_trades']),
                    'win_rate': float(best_result['win_rate']),
                    'sharpe_ratio': float(best_result.get('sharpe_ratio', 0)),
                    'max_drawdown': float(best_result.get('max_drawdown', 0)),
                    'execution_time': float(best_result.get('execution_time', 0))
                },
                'parameters': params,
                'source_file': best_result['source_file'],
                'selected_by': objective
            }
            
            perf = best_configs[asset_key]['performance']
            print(f"{asset_key:20} | PnL: ${perf['final_pnl']:8,.0f} | "
                  f"Trades: {perf['total_trades']:3d} | "
                  f"WR: {perf['win_rate']:5.1f}% | "
                  f"Sharpe: {perf['sharpe_ratio']:5.2f} | "
                  f"DD: {perf['max_drawdown']:5.1f}%")
        
        print(f"\n✅ Found {len(best_configs)} best configurations")
        return best_configs
    
    def generate_strategy_configs(self, best_configs: Dict) -> Dict:
        """Convert optimization results to strategy configuration format"""
        print(f"\n🔧 Generating strategy configurations...")
        
        strategy_configs = {}
        
        for asset_key, config in best_configs.items():
            symbol = config['symbol']
            timeframe = config['timeframe']
            params = config['parameters']
            
            # Map optimization parameters to strategy config format
            strategy_config = {
                'ASSET_INFO': {
                    'symbol': symbol,
                    'timeframe': timeframe,
                    'optimization_type': config['optimization_type'],
                    'optimization_date': config['optimization_date'],
                    'selected_by': config['selected_by']
                },
                'BOLLINGER_BANDS': {
                    'window': params.get('bb_window', 20),
                    'std_dev': params.get('bb_std', 2.0)
                },
                'VWAP_BANDS': {
                    'window': params.get('vwap_window', 20),
                    'std_dev': params.get('vwap_std', 2.0)
                },
                'ATR': {
                    'period': params.get('atr_period', 14)
                },
                'RISK_MANAGEMENT': {
                    'risk_per_position_pct': params.get('risk_per_position_pct', 1.0),
                    'stop_loss_atr_multiplier': params.get('stop_loss_atr_multiplier', 1.2),
                    'risk_reward_ratio': params.get('risk_reward_ratio', 2.5)
                },
                'STRATEGY_BEHAVIOR': {
                    'require_reversal': params.get('require_reversal', False),
                    'regime_min_score': params.get('regime_min_score', 60)
                },
                'PERFORMANCE_METRICS': config['performance'],
                'METADATA': {
                    'source_file': config['source_file'],
                    'generated_at': datetime.now().isoformat()
                }
            }
            
            strategy_configs[asset_key] = strategy_config
        
        return strategy_configs
    
    def save_results(self, strategy_configs: Dict, objective: str):
        """Save configurations and summaries"""
        print(f"\n💾 Saving results for objective: {objective}")
        
        # Save JSON configuration
        config_file = self.output_dir / f'best_configs_{objective}.json'
        with open(config_file, 'w') as f:
            json.dump(strategy_configs, f, indent=2)
        print(f"✅ Strategy configurations saved to {config_file}")
        
        # Save human-readable summary
        summary_file = self.output_dir / f'best_configs_{objective}_summary.txt'
        with open(summary_file, 'w') as f:
            f.write(f"BEST CONFIGURATIONS BY {objective.upper()}\n")
            f.write("="*80 + "\n")
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Total configurations: {len(strategy_configs)}\n\n")
            
            # Sort by performance metric
            if objective == 'max_drawdown':
                sorted_configs = sorted(strategy_configs.items(), 
                                      key=lambda x: x[1]['PERFORMANCE_METRICS']['max_drawdown'])
            elif objective == 'balanced':
                # For balanced, sort by a combination of PnL and drawdown
                def balanced_sort_key(item):
                    perf = item[1]['PERFORMANCE_METRICS']
                    # Normalize and combine (same logic as in selection)
                    return perf['final_pnl'] * 0.6 - perf['max_drawdown'] * 0.4
                sorted_configs = sorted(strategy_configs.items(), 
                                      key=balanced_sort_key, reverse=True)
            else:
                sorted_configs = sorted(strategy_configs.items(), 
                                      key=lambda x: x[1]['PERFORMANCE_METRICS'][objective], 
                                      reverse=True)
            
            for asset_key, config in sorted_configs:
                perf = config['PERFORMANCE_METRICS']
                params = config
                
                f.write(f"Asset: {asset_key}\n")
                f.write(f"  Performance:\n")
                f.write(f"    PnL: ${perf['final_pnl']:,.2f}\n")
                f.write(f"    Win Rate: {perf['win_rate']:.1f}%\n")
                f.write(f"    Sharpe Ratio: {perf['sharpe_ratio']:.2f}\n")
                f.write(f"    Max Drawdown: {perf['max_drawdown']:.1f}%\n")
                f.write(f"    Total Trades: {perf['total_trades']}\n")
                f.write(f"  Parameters:\n")
                f.write(f"    BB Window: {params['BOLLINGER_BANDS']['window']}, ")
                f.write(f"BB Std: {params['BOLLINGER_BANDS']['std_dev']}\n")
                f.write(f"    VWAP Window: {params['VWAP_BANDS']['window']}, ")
                f.write(f"VWAP Std: {params['VWAP_BANDS']['std_dev']}\n")
                f.write(f"    Risk per trade: {params['RISK_MANAGEMENT']['risk_per_position_pct']}%\n")
                f.write(f"    Risk/Reward: {params['RISK_MANAGEMENT']['risk_reward_ratio']}\n")
                f.write(f"    Stop Loss ATR: {params['RISK_MANAGEMENT']['stop_loss_atr_multiplier']}\n")
                f.write(f"    Require Reversal: {params['STRATEGY_BEHAVIOR']['require_reversal']}\n")
                f.write(f"    Regime Min Score: {params['STRATEGY_BEHAVIOR']['regime_min_score']}\n")
                f.write(f"  Source: {config['METADATA']['source_file']}\n")
                f.write("-" * 60 + "\n")
        
        print(f"✅ Human-readable summary saved to {summary_file}")
        
        # Save CSV for easy analysis
        csv_file = self.output_dir / f'best_configs_{objective}.csv'
        csv_data = []
        for asset_key, config in strategy_configs.items():
            row = {
                'asset': asset_key,
                'symbol': config['ASSET_INFO']['symbol'],
                'timeframe': config['ASSET_INFO']['timeframe'],
                'final_pnl': config['PERFORMANCE_METRICS']['final_pnl'],
                'total_trades': config['PERFORMANCE_METRICS']['total_trades'],
                'win_rate': config['PERFORMANCE_METRICS']['win_rate'],
                'sharpe_ratio': config['PERFORMANCE_METRICS']['sharpe_ratio'],
                'max_drawdown': config['PERFORMANCE_METRICS']['max_drawdown'],
                'bb_window': config['BOLLINGER_BANDS']['window'],
                'bb_std': config['BOLLINGER_BANDS']['std_dev'],
                'vwap_window': config['VWAP_BANDS']['window'],
                'vwap_std': config['VWAP_BANDS']['std_dev'],
                'risk_per_position_pct': config['RISK_MANAGEMENT']['risk_per_position_pct'],
                'stop_loss_atr_multiplier': config['RISK_MANAGEMENT']['stop_loss_atr_multiplier'],
                'risk_reward_ratio': config['RISK_MANAGEMENT']['risk_reward_ratio'],
                'require_reversal': config['STRATEGY_BEHAVIOR']['require_reversal'],
                'regime_min_score': config['STRATEGY_BEHAVIOR']['regime_min_score']
            }
            csv_data.append(row)
        
        pd.DataFrame(csv_data).to_csv(csv_file, index=False)
        print(f"✅ CSV export saved to {csv_file}")
    
    def generate_portfolio_summary(self, all_configs: Dict[str, Dict]):
        """Generate overall portfolio summary across all objectives"""
        print(f"\n📊 Generating portfolio summary...")
        
        summary_file = self.output_dir / 'portfolio_summary.txt'
        with open(summary_file, 'w') as f:
            f.write("PORTFOLIO OPTIMIZATION SUMMARY\n")
            f.write("="*80 + "\n")
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            for objective, configs in all_configs.items():
                f.write(f"\n{objective.upper()} OPTIMIZATION\n")
                f.write("-" * 40 + "\n")
                
                if not configs:
                    f.write("No configurations found.\n")
                    continue
                
                # Calculate portfolio metrics
                total_pnl = sum(c['PERFORMANCE_METRICS']['final_pnl'] for c in configs.values())
                avg_win_rate = np.mean([c['PERFORMANCE_METRICS']['win_rate'] for c in configs.values()])
                avg_sharpe = np.mean([c['PERFORMANCE_METRICS']['sharpe_ratio'] for c in configs.values()])
                avg_drawdown = np.mean([c['PERFORMANCE_METRICS']['max_drawdown'] for c in configs.values()])
                total_trades = sum(c['PERFORMANCE_METRICS']['total_trades'] for c in configs.values())
                
                f.write(f"Assets: {len(configs)}\n")
                f.write(f"Total Portfolio PnL: ${total_pnl:,.2f}\n")
                f.write(f"Average Win Rate: {avg_win_rate:.1f}%\n")
                f.write(f"Average Sharpe Ratio: {avg_sharpe:.2f}\n")
                f.write(f"Average Max Drawdown: {avg_drawdown:.1f}%\n")
                f.write(f"Total Trades: {total_trades}\n")
                
                # Top 5 performers
                if objective == 'max_drawdown':
                    sorted_assets = sorted(configs.items(), 
                                         key=lambda x: x[1]['PERFORMANCE_METRICS']['max_drawdown'])
                    f.write(f"\nTop 5 (Lowest Drawdown):\n")
                elif objective == 'balanced':
                    # For balanced, sort by combination score
                    def balanced_sort_key(item):
                        perf = item[1]['PERFORMANCE_METRICS']
                        return perf['final_pnl'] * 0.6 - perf['max_drawdown'] * 0.4
                    sorted_assets = sorted(configs.items(), 
                                         key=balanced_sort_key, reverse=True)
                    f.write(f"\nTop 5 (Best Balanced):\n")
                else:
                    sorted_assets = sorted(configs.items(), 
                                         key=lambda x: x[1]['PERFORMANCE_METRICS'][objective], 
                                         reverse=True)
                    f.write(f"\nTop 5 Performers:\n")
                    
                for i, (asset, config) in enumerate(sorted_assets[:5], 1):
                    perf = config['PERFORMANCE_METRICS']
                    f.write(f"{i}. {asset:15} | PnL: ${perf['final_pnl']:8,.0f} | "
                           f"WR: {perf['win_rate']:5.1f}% | "
                           f"Sharpe: {perf['sharpe_ratio']:5.2f} | "
                           f"DD: {perf['max_drawdown']:5.1f}%\n")
        
        print(f"✅ Portfolio summary saved to {summary_file}")
    
    def run_analysis(self, objectives: List[str] = None, min_trades: int = 10):
        """Run the complete analysis pipeline"""
        if objectives is None:
            objectives = ['final_pnl', 'win_rate', 'max_drawdown', 'balanced']
        
        print("🚀 Starting batch results analysis...")
        print(f"📁 Results directory: {self.results_dir}")
        print(f"📁 Output directory: {self.output_dir}")
        
        # Load all results
        try:
            df = self.load_csv_results()
        except Exception as e:
            print(f"❌ Failed to load results: {e}")
            return False
        
        # Save combined results
        combined_file = self.output_dir / 'combined_batch_results.csv'
        df.to_csv(combined_file, index=False)
        print(f"📊 Combined results saved to {combined_file}")
        
        # Filter valid results
        df_filtered = self.filter_valid_results(df, min_trades=min_trades)
        
        if len(df_filtered) == 0:
            print("❌ No valid results after filtering!")
            return False
        
        # Analyze by each objective
        all_configs = {}
        for objective in objectives:
            print(f"\n{'='*60}")
            print(f"ANALYZING BY {objective.upper()}")
            print('='*60)
            
            try:
                best_configs = self.get_best_configs_by_objective(df_filtered, objective)
                if not best_configs:
                    print(f"No configurations found for {objective}")
                    continue
                    
                strategy_configs = self.generate_strategy_configs(best_configs)
                self.save_results(strategy_configs, objective)
                all_configs[objective] = strategy_configs
                
            except Exception as e:
                print(f"❌ Error analyzing {objective}: {e}")
                continue
        
        # Generate portfolio summary
        if all_configs:
            self.generate_portfolio_summary(all_configs)
        
        print(f"\n🎉 Analysis complete! Check {self.output_dir} for results.")
        return True

def main():
    """Main function with command-line interface"""
    parser = argparse.ArgumentParser(
        description="Analyze batch optimization results and generate asset-specific configurations"
    )
    parser.add_argument(
        '--results-dir', 
        default='batch-analysis',
        help='Directory containing batch optimization results (default: batch-analysis)'
    )
    parser.add_argument(
        '--output-dir',
        default='results', 
        help='Output directory for generated configurations (default: results)'
    )
    parser.add_argument(
        '--objectives',
        nargs='+',
        default=['final_pnl', 'win_rate', 'max_drawdown', 'balanced'],
        help='Optimization objectives to analyze (default: final_pnl, win_rate, max_drawdown, balanced)'
    )
    parser.add_argument(
        '--min-trades',
        type=int,
        default=10,
        help='Minimum number of trades required for valid result (default: 10)'
    )
    
    args = parser.parse_args()
    
    # Verify input directory exists
    if not Path(args.results_dir).exists():
        print(f"❌ Results directory {args.results_dir} not found!")
        print("Make sure to download results first:")
        print("aws s3 sync s3://your-bucket/mean-reversion-strat/optimization/results/ ./batch-analysis/")
        return 1
    
    # Run analysis
    analyzer = BatchResultsAnalyzer(
        results_dir=args.results_dir,
        output_dir=args.output_dir
    )
    
    success = analyzer.run_analysis(
        objectives=args.objectives,
        min_trades=args.min_trades
    )
    
    return 0 if success else 1

if __name__ == '__main__':
    exit(main())

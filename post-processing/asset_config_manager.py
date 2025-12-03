"""
Asset-specific configuration manager using optimization results

This module provides functionality to load and apply optimized configurations
for specific assets and timeframes based on batch optimization results.
"""
import json
from pathlib import Path
from typing import Dict, Optional, List, Tuple
from dataclasses import dataclass
import logging

# Load environment variables
try:
    from dotenv import load_dotenv
    env_path = Path(__file__).parent.parent / '.env'
    if env_path.exists():
        load_dotenv(env_path)
except ImportError:
    pass

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class AssetConfig:
    """Asset-specific configuration with optimized parameters"""
    symbol: str
    timeframe: str
    optimization_type: str
    optimization_date: str
    selected_by: str
    
    # Bollinger Bands
    bb_window: int
    bb_std: float
    
    # VWAP Bands  
    vwap_window: int
    vwap_std: float
    
    # ATR
    atr_period: int
    
    # Risk Management
    risk_per_position_pct: float
    stop_loss_atr_multiplier: float
    risk_reward_ratio: float
    
    # Strategy Behavior
    require_reversal: bool
    regime_min_score: int
    
    # Performance Metrics
    final_pnl: float
    total_trades: int
    win_rate: float
    sharpe_ratio: float
    max_drawdown: float
    
    # Metadata
    source_file: str
    
    @classmethod
    def from_dict(cls, data: Dict, asset_key: str):
        """Create AssetConfig from dictionary data"""
        asset_info = data['ASSET_INFO']
        bb_params = data['BOLLINGER_BANDS']
        vwap_params = data['VWAP_BANDS']
        atr_params = data['ATR']
        risk_params = data['RISK_MANAGEMENT']
        behavior_params = data['STRATEGY_BEHAVIOR']
        performance = data['PERFORMANCE_METRICS']
        metadata = data['METADATA']
        
        return cls(
            symbol=asset_info['symbol'],
            timeframe=asset_info['timeframe'],
            optimization_type=asset_info['optimization_type'],
            optimization_date=asset_info['optimization_date'],
            selected_by=asset_info['selected_by'],
            
            bb_window=bb_params['window'],
            bb_std=bb_params['std_dev'],
            
            vwap_window=vwap_params['window'],
            vwap_std=vwap_params['std_dev'],
            
            atr_period=atr_params['period'],
            
            risk_per_position_pct=risk_params['risk_per_position_pct'],
            stop_loss_atr_multiplier=risk_params['stop_loss_atr_multiplier'],
            risk_reward_ratio=risk_params['risk_reward_ratio'],
            
            require_reversal=behavior_params.get('require_reversal', True),
            regime_min_score=behavior_params.get('regime_min_score', 60),
            
            final_pnl=performance['final_pnl'],
            total_trades=performance['total_trades'],
            win_rate=performance['win_rate'],
            sharpe_ratio=performance['sharpe_ratio'],
            max_drawdown=performance['max_drawdown'],
            
            source_file=metadata['source_file']
        )
    
    def to_strategy_dict(self) -> Dict:
        """Convert to strategy configuration dictionary format"""
        return {
            'BOLLINGER_BANDS': {
                'window': self.bb_window,
                'std_dev': self.bb_std
            },
            'VWAP': {  # Note: it's VWAP not VWAP_BANDS in actual config
                'window': self.vwap_window,
                'std_dev': self.vwap_std
            },
            'RISK_MANAGEMENT': {
                'risk_per_position_pct': self.risk_per_position_pct,
                'stop_loss_atr_multiplier': self.stop_loss_atr_multiplier,
                'risk_reward_ratio': self.risk_reward_ratio,
                'atr_period': self.atr_period
            },
            'ENTRY_CONDITIONS': {
                'require_reversal_confirmation': self.require_reversal
            },
            'MARKET_REGIME': {
                'min_regime_score': self.regime_min_score
            }
        }
    
    def __str__(self) -> str:
        return (f"AssetConfig({self.symbol}_{self.timeframe}: "
                f"PnL=${self.final_pnl:,.0f}, WR={self.win_rate:.1f}%, "
                f"Sharpe={self.sharpe_ratio:.2f})")

class AssetConfigManager:
    """Manages asset-specific configurations from optimization results"""

    def __init__(self, config_dir: str = 'results', 
                 preference: str = 'final_pnl'):
        """
        Initialize configuration manager
        
        Args:
            config_dir: Directory containing configuration files
            preference: Preferred optimization objective ('final_pnl', 'sharpe_ratio', 'win_rate', 'max_drawdown', 'balanced')
        """
        self.config_dir = Path(config_dir)
        self.preference = preference
        self.configs: Dict[str, AssetConfig] = {}
        self.available_objectives: List[str] = []
        
        self._discover_available_configs()
        self._load_configs()
    
    def _discover_available_configs(self):
        """Discover available configuration files"""
        if not self.config_dir.exists():
            logger.warning(f"Config directory {self.config_dir} does not exist")
            return
        
        config_files = list(self.config_dir.glob('best_configs_*.json'))
        self.available_objectives = [
            f.stem.replace('best_configs_', '') for f in config_files
        ]
        
        logger.info(f"Found configurations for objectives: {self.available_objectives}")
    
    def _load_configs(self):
        """Load configurations from JSON file"""
        config_file = self.config_dir / f'best_configs_{self.preference}.json'
        
        if not config_file.exists():
            logger.warning(f"Config file {config_file} not found")
            if self.available_objectives:
                # Fallback to first available objective
                fallback = self.available_objectives[0]
                logger.info(f"Falling back to {fallback} configurations")
                self.preference = fallback
                config_file = self.config_dir / f'best_configs_{fallback}.json'
            else:
                logger.error("No configuration files found")
                return
        
        try:
            with open(config_file, 'r') as f:
                data = json.load(f)
            
            self.configs = {}
            for asset_key, config_data in data.items():
                self.configs[asset_key] = AssetConfig.from_dict(config_data, asset_key)
            
            logger.info(f"Loaded {len(self.configs)} asset-specific configurations from {config_file}")
            
        except Exception as e:
            logger.error(f"Failed to load configurations from {config_file}: {e}")
    
    def get_config(self, symbol: str, timeframe: str) -> Optional[AssetConfig]:
        """Get configuration for specific asset and timeframe"""
        asset_key = f"{symbol}_{timeframe}"
        return self.configs.get(asset_key)
    
    def get_available_assets(self) -> List[str]:
        """Get list of available asset configurations"""
        return list(self.configs.keys())
    
    def get_symbols(self) -> List[str]:
        """Get list of unique symbols"""
        return list(set(config.symbol for config in self.configs.values()))
    
    def get_timeframes(self) -> List[str]:
        """Get list of unique timeframes"""
        return list(set(config.timeframe for config in self.configs.values()))
    
    def get_configs_for_symbol(self, symbol: str) -> List[AssetConfig]:
        """Get all configurations for a specific symbol"""
        return [config for config in self.configs.values() if config.symbol == symbol]
    
    def get_configs_for_timeframe(self, timeframe: str) -> List[AssetConfig]:
        """Get all configurations for a specific timeframe"""
        return [config for config in self.configs.values() if config.timeframe == timeframe]
    
    def switch_objective(self, new_objective: str) -> bool:
        """Switch to different optimization objective"""
        if new_objective not in self.available_objectives:
            logger.error(f"Objective {new_objective} not available. Available: {self.available_objectives}")
            return False
        
        old_preference = self.preference
        self.preference = new_objective
        self._load_configs()
        
        logger.info(f"Switched from {old_preference} to {new_objective} configurations")
        return True
    
    def update_strategy_config(self, symbol: str, timeframe: str, 
                             strategy_config_module=None) -> bool:
        """
        Update global strategy config with asset-specific parameters
        
        Args:
            symbol: Asset symbol
            timeframe: Asset timeframe  
            strategy_config_module: Strategy config module to update (optional)
            
        Returns:
            True if config was updated, False otherwise
        """
        config = self.get_config(symbol, timeframe)
        if not config:
            logger.warning(f"No optimized config found for {symbol}_{timeframe}")
            return False
        
        if strategy_config_module is None:
            try:
                # Try to import the strategy config module
                import sys
                sys.path.append('.')
                from src.strategy_config import StrategyConfig
                strategy_config_module = StrategyConfig
            except ImportError:
                logger.error("Could not import StrategyConfig module")
                return False
        
        # Update global configuration using the correct attribute names
        try:
            # Update Bollinger Bands
            strategy_config_module.BOLLINGER_BANDS['window'] = config.bb_window
            strategy_config_module.BOLLINGER_BANDS['std_dev'] = config.bb_std
            
            # Update VWAP (note: it's VWAP not VWAP_BANDS in the actual config)
            strategy_config_module.VWAP['window'] = config.vwap_window
            strategy_config_module.VWAP['std_dev'] = config.vwap_std
            
            # Update Risk Management
            strategy_config_module.RISK_MANAGEMENT['risk_per_position_pct'] = config.risk_per_position_pct
            strategy_config_module.RISK_MANAGEMENT['stop_loss_atr_multiplier'] = config.stop_loss_atr_multiplier
            strategy_config_module.RISK_MANAGEMENT['risk_reward_ratio'] = config.risk_reward_ratio
            strategy_config_module.RISK_MANAGEMENT['atr_period'] = config.atr_period
            
            # Update Entry Conditions (note: attribute name mapping)
            strategy_config_module.ENTRY_CONDITIONS['require_reversal_confirmation'] = config.require_reversal
            
            # Update Market Regime
            strategy_config_module.MARKET_REGIME['min_regime_score'] = config.regime_min_score
            
        except AttributeError as e:
            logger.error(f"Error updating strategy config: {e}")
            return False
        
        logger.info(f"✅ Updated strategy config for {symbol}_{timeframe}")
        logger.info(f"   Optimization: {config.selected_by} | "
                   f"BB Window: {config.bb_window} | "
                   f"Risk: {config.risk_per_position_pct}% | "
                   f"R/R: {config.risk_reward_ratio}")
        logger.info(f"   Expected Performance: PnL=${config.final_pnl:,.0f}, "
                   f"WR={config.win_rate:.1f}%, Sharpe={config.sharpe_ratio:.2f}")
        
        return True
    
    def get_performance_summary(self) -> Dict:
        """Get portfolio performance summary"""
        if not self.configs:
            return {}
        
        configs = list(self.configs.values())
        
        return {
            'total_assets': len(configs),
            'total_pnl': sum(c.final_pnl for c in configs),
            'avg_win_rate': sum(c.win_rate for c in configs) / len(configs),
            'avg_sharpe_ratio': sum(c.sharpe_ratio for c in configs) / len(configs),
            'avg_max_drawdown': sum(c.max_drawdown for c in configs) / len(configs),
            'total_trades': sum(c.total_trades for c in configs),
            'symbols': len(set(c.symbol for c in configs)),
            'timeframes': len(set(c.timeframe for c in configs)),
            'optimization_preference': self.preference
        }
    
    def get_top_performers(self, n: int = 5, metric: str = 'final_pnl') -> List[Tuple[str, AssetConfig]]:
        """Get top N performing configurations by specified metric"""
        if not self.configs:
            return []
        
        configs_list = list(self.configs.items())
        
        # Sort by metric
        if metric == 'max_drawdown':
            # Drawdown should be minimized
            sorted_configs = sorted(
                configs_list,
                key=lambda x: getattr(x[1], metric),
                reverse=False
            )
        elif metric == 'balanced':
            # For balanced, use combination of PnL and drawdown (same as analyzer)
            def balanced_score(item):
                config = item[1]
                # Simple balanced score: higher PnL is better, lower drawdown is better
                return config.final_pnl * 0.6 - config.max_drawdown * 0.4
            sorted_configs = sorted(configs_list, key=balanced_score, reverse=True)
        else:
            # Other metrics should be maximized
            sorted_configs = sorted(
                configs_list,
                key=lambda x: getattr(x[1], metric),
                reverse=True
            )
        
        return sorted_configs[:n]
    
    def export_to_csv(self, filename: str = None) -> str:
        """Export configurations to CSV file"""
        if filename is None:
            filename = f"asset_configs_{self.preference}.csv"
        
        import pandas as pd
        
        data = []
        for asset_key, config in self.configs.items():
            row = {
                'asset_key': asset_key,
                'symbol': config.symbol,
                'timeframe': config.timeframe,
                'optimization_type': config.optimization_type,
                'selected_by': config.selected_by,
                'final_pnl': config.final_pnl,
                'total_trades': config.total_trades,
                'win_rate': config.win_rate,
                'sharpe_ratio': config.sharpe_ratio,
                'max_drawdown': config.max_drawdown,
                'bb_window': config.bb_window,
                'bb_std': config.bb_std,
                'vwap_window': config.vwap_window,
                'vwap_std': config.vwap_std,
                'atr_period': config.atr_period,
                'risk_per_position_pct': config.risk_per_position_pct,
                'stop_loss_atr_multiplier': config.stop_loss_atr_multiplier,
                'risk_reward_ratio': config.risk_reward_ratio,
                'require_reversal': config.require_reversal,
                'regime_min_score': config.regime_min_score,
                'source_file': config.source_file
            }
            data.append(row)
        
        df = pd.DataFrame(data)
        output_file = self.config_dir / filename
        df.to_csv(output_file, index=False)
        
        logger.info(f"Exported {len(data)} configurations to {output_file}")
        return str(output_file)
    
    def print_summary(self):
        """Print a summary of loaded configurations"""
        if not self.configs:
            print("❌ No configurations loaded")
            return
        
        summary = self.get_performance_summary()
        
        print(f"\n📊 ASSET CONFIGURATION SUMMARY")
        print("="*50)
        print(f"Optimization Preference: {self.preference}")
        print(f"Total Assets: {summary['total_assets']}")
        print(f"Unique Symbols: {summary['symbols']}")
        print(f"Unique Timeframes: {summary['timeframes']}")
        print(f"Expected Portfolio PnL: ${summary['total_pnl']:,.2f}")
        print(f"Average Win Rate: {summary['avg_win_rate']:.1f}%")
        print(f"Average Sharpe Ratio: {summary['avg_sharpe_ratio']:.2f}")
        print(f"Average Max Drawdown: {summary['avg_max_drawdown']:.1f}%")
        print(f"Total Expected Trades: {summary['total_trades']}")
        
        print(f"\n🏆 TOP 5 PERFORMERS ({self.preference}):")
        
        # Handle display for balanced metric
        if self.preference == 'balanced':
            top_performers = self.get_top_performers(5, 'balanced')
        else:
            top_performers = self.get_top_performers(5, self.preference.replace('max_drawdown', 'max_drawdown'))
        
        for i, (asset_key, config) in enumerate(top_performers, 1):
            if self.preference == 'balanced':
                # Show balanced score and components
                balanced_score = config.final_pnl * 0.6 - config.max_drawdown * 0.4
                metric_str = f"Score: {balanced_score:.1f}"
                extra_info = f"PnL: ${config.final_pnl:,.0f}, DD: {config.max_drawdown:.1f}%"
            else:
                metric_value = getattr(config, self.preference)
                if self.preference == 'final_pnl':
                    metric_str = f"${metric_value:,.0f}"
                    extra_info = f"DD: {config.max_drawdown:.1f}%"
                elif self.preference in ['win_rate', 'max_drawdown']:
                    metric_str = f"{metric_value:.1f}%"
                    extra_info = f"PnL: ${config.final_pnl:,.0f}"
                else:
                    metric_str = f"{metric_value:.2f}"
                    extra_info = f"PnL: ${config.final_pnl:,.0f}"
                
            print(f"{i}. {asset_key:15} | {metric_str:>12} | "
                  f"Trades: {config.total_trades:3d} | {extra_info}")
        
        print(f"\n📋 AVAILABLE ASSETS:")
        for asset_key in sorted(self.configs.keys()):
            config = self.configs[asset_key]
            print(f"  {asset_key:20} | PnL: ${config.final_pnl:8,.0f} | "
                  f"WR: {config.win_rate:5.1f}% | Trades: {config.total_trades:3d}")

def main():
    """Example usage and testing"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Asset Configuration Manager")
    parser.add_argument('--config-dir', default='results', 
                       help='Configuration directory')
    parser.add_argument('--preference', default='final_pnl',
                       choices=['final_pnl', 'sharpe_ratio', 'win_rate', 'max_drawdown', 'balanced'],
                       help='Optimization preference')
    parser.add_argument('--symbol', help='Test specific symbol')
    parser.add_argument('--timeframe', help='Test specific timeframe')
    parser.add_argument('--export-csv', action='store_true',
                       help='Export configurations to CSV')
    parser.add_argument('--summary', action='store_true',
                       help='Show configuration summary')
    
    args = parser.parse_args()
    
    # Initialize manager
    manager = AssetConfigManager(args.config_dir, args.preference)
    
    # Print summary by default or if requested
    if not args.symbol or args.summary:
        manager.print_summary()
    
    # Test specific asset if provided
    if args.symbol and args.timeframe:
        print(f"\n🧪 Testing configuration for {args.symbol}_{args.timeframe}")
        config = manager.get_config(args.symbol, args.timeframe)
        if config:
            print(f"✅ Found configuration: {config}")
            success = manager.update_strategy_config(args.symbol, args.timeframe)
            if success:
                print("✅ Strategy configuration updated successfully")
            else:
                print("❌ Failed to update strategy configuration")
        else:
            print(f"❌ No configuration found")
    
    # Export to CSV if requested
    if args.export_csv:
        filename = manager.export_to_csv()
        print(f"\n💾 Configurations exported to {filename}")

if __name__ == '__main__':
    main()

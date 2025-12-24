"""
Configuration loader for custom signal detectors.
"""

import json
import logging
from typing import Dict, Optional, Any

logger = logging.getLogger(__name__)


class CustomStrategyConfigLoader:
    
    def __init__(self, config_path: str):
        self.config_path = config_path
        self.config = self._load_config()
        logger.info(f"Loaded config from {config_path}")
    
    def _load_config(self) -> Dict:
        try:
            with open(self.config_path, 'r') as f:
                config = json.load(f)
            return config
        except Exception as e:
            logger.error(f"Failed to load config from {self.config_path}: {e}")
            raise
    
    def get_assets(self) -> list:
        return self.config.get('assets', [])
    
    def get_asset_by_symbol(self, symbol: str) -> Optional[Dict]:
        for asset in self.get_assets():
            if asset['symbol'] == symbol:
                return asset
        return None
    
    def get_strategy(self, strategy_name: str) -> Optional[Dict]:
        return self.config.get('strategies', {}).get(strategy_name)
    
    def get_asset_details(self, symbol: str) -> Optional[Dict]:
        return self.config.get('asset_details', {}).get(symbol)
    
    def get_detector_config(self, symbol: str) -> Dict[str, Any]:
        asset = self.get_asset_by_symbol(symbol)
        if not asset:
            raise ValueError(f"Asset {symbol} not found in config")
        
        strategy_name = asset.get('strategy')
        if not strategy_name:
            raise ValueError(f"No strategy defined for asset {symbol}")
        
        strategy = self.get_strategy(strategy_name)
        if not strategy:
            raise ValueError(f"Strategy {strategy_name} not found in config")
        
        asset_details = self.get_asset_details(symbol)
        
        return {
            'symbol': symbol,
            'fetch_symbol': asset.get('fetch_symbol', symbol),
            'timeframe': asset.get('timeframe', '5m'),
            'strategy_name': strategy_name,
            'detector_class': strategy.get('detector_class'),
            'detector_module': strategy.get('detector_module'),
            'strategy_params': strategy.get('parameters', {}),
            'asset_details': asset_details or {}
        }
    
    def create_detector(self, symbol: str):
        config = self.get_detector_config(symbol)
        
        detector_module = config['detector_module']
        detector_class = config['detector_class']
        strategy_params = config['strategy_params']
        
        try:
            module = __import__(detector_module, fromlist=[detector_class])
            detector_cls = getattr(module, detector_class)
            detector = detector_cls(**strategy_params)
            
            logger.info(f"Created {detector_class} for {symbol}")
            return detector
        
        except Exception as e:
            logger.error(f"Failed to create detector for {symbol}: {e}", exc_info=True)
            raise ValueError(f"Cannot create detector for {symbol}: {e}")
    
    def get_all_detector_configs(self) -> Dict[str, Dict]:
        configs = {}
        for asset in self.get_assets():
            symbol = asset['symbol']
            try:
                configs[symbol] = self.get_detector_config(symbol)
            except ValueError as e:
                logger.warning(f"Skipping {symbol}: {e}")
        return configs


def load_custom_strategy_config(config_path: str) -> CustomStrategyConfigLoader:
    return CustomStrategyConfigLoader(config_path)

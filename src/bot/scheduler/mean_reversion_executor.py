#!/usr/bin/env python3
"""
Mean Reversion Strategy Executor

Executes the Bollinger Bands + VWAP mean reversion strategy.
"""

import logging
import os
from datetime import datetime, timezone
from typing import Dict, Any, List
import pandas as pd

from .strategy_executor import StrategyExecutor
from src.bot.signal_detector import LiveSignalDetector
from src.symbol_config_manager import SymbolConfigManager

logger = logging.getLogger(__name__)


class MeanReversionExecutor(StrategyExecutor):
    """Executes mean reversion strategy using Bollinger Bands + VWAP"""
    
    def __init__(self, config_file: str):
        """
        Initialize mean reversion executor
        
        Args:
            config_file: Path to mean reversion configuration file
        """
        super().__init__(config_file, 'mean_reversion')
        self.symbols_config = {}
        self.signal_detector = None
    
    def initialize(self) -> bool:
        """Initialize strategy resources"""
        try:
            # Load symbol configurations
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
            config_path = os.path.join(project_root, self.config_file)
            
            self.symbols_config = SymbolConfigManager.load_symbol_configs(config_path)
            logger.info(f"✅ Loaded {len(self.symbols_config)} symbols from {self.config_file}")
            
            # Initialize the live signal detector
            self.signal_detector = LiveSignalDetector()
            logger.info("✅ LiveSignalDetector initialized")
            
            return True
            
        except FileNotFoundError:
            logger.error(f"❌ Configuration file not found: {self.config_file}")
            return False
        except Exception as e:
            logger.error(f"❌ Error initializing mean reversion executor: {e}")
            return False
    
    def get_symbols(self) -> List[Dict[str, Any]]:
        """Get list of symbols to analyze"""
        return [
            {
                'symbol': config['symbol'],
                'fetch_symbol': config['fetch_symbol'],
                'timeframe': config['timeframe'],
                'config': config['config']
            }
            for config in self.symbols_config.values()
        ]
    
    def analyze_symbol(self, symbol_config: Dict[str, Any], data: pd.DataFrame) -> Dict[str, Any]:
        """
        Analyze a single symbol with mean reversion strategy
        
        Args:
            symbol_config: Symbol configuration
            data: OHLCV DataFrame
            
        Returns:
            Analysis results
        """
        symbol = symbol_config['symbol']
        
        try:
            # Create strategy configuration from loaded config
            config = symbol_config['config']
            strategy_params = self._create_strategy_params(config)
            
            # Use the live signal detector to analyze the symbol
            signal_result = self.signal_detector.analyze_symbol(data, strategy_params, symbol)
            
            # Get current market data for analysis
            current_candle = data.iloc[-1]
            current_price = float(current_candle['close'])
            
            # Create analysis result with signal information
            analysis_result = {
                'symbol': symbol,
                'status': 'analyzed',
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'last_candle': str(data.index[-1]),
                'current_price': current_price,
                'data_points': len(data),
                'strategy_params': strategy_params,
                'signal': signal_result,
                'data': data,  # Include data for chart generation
                'strategy_name': 'mean_reversion',  # NEW: Identify strategy type
                'custom_strategy': None,  # NEW: No custom strategy for mean reversion
                'message': f'Analysis completed for {symbol}'
            }
            
            # Log signal if generated
            if signal_result['signal_type'] not in ['no_signal', 'error', 'insufficient_data', 'data_preparation_failed']:
                logger.info(f"    🚨 SIGNAL: {signal_result['signal_type'].upper()} at {current_price:.4f}")
                logger.info(f"       Stop Loss: {signal_result['stop_loss']:.4f}")
                logger.info(f"       Take Profit: {signal_result['take_profit']:.4f}")
                logger.info(f"       Position Size: {signal_result['position_size']:.2f}")
                logger.info(f"       Risk Amount: ${signal_result['risk_amount']:.2f}")
            else:
                logger.info(f"    ✅ Analysis completed: {current_price:.4f} - {signal_result['reason']}")
            
            return analysis_result
            
        except Exception as e:
            logger.error(f"    ❌ Error analyzing {symbol}: {e}")
            return {
                'symbol': symbol,
                'status': 'analysis_failed',
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'error': str(e),
                'message': f'Analysis failed for {symbol}'
            }
    
    def _create_strategy_params(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create strategy parameters from loaded configuration
        
        Args:
            config: Loaded configuration dictionary
            
        Returns:
            Strategy parameters dictionary
        """
        bb_config = config['BOLLINGER_BANDS']
        vwap_config = config['VWAP_BANDS']
        atr_config = config['ATR']
        risk_config = config['RISK_MANAGEMENT']
        strategy_config = config['STRATEGY_BEHAVIOR']
        
        return {
            'bb_window': bb_config['window'],
            'bb_std': bb_config['std_dev'],
            'vwap_window': vwap_config['window'],
            'vwap_std': vwap_config['std_dev'],
            'atr_period': atr_config['period'],
            'risk_per_position_pct': risk_config['risk_per_position_pct'],
            'stop_loss_atr_multiplier': risk_config['stop_loss_atr_multiplier'],
            'risk_reward_ratio': risk_config['risk_reward_ratio'],
            'require_reversal': strategy_config.get('require_reversal', True),
            'regime_min_score': strategy_config.get('regime_min_score', 60)
        }

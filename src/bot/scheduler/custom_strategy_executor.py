#!/usr/bin/env python3
"""
Custom Strategy Executor

Executes custom signal detection strategies (session sweep, VWAP, etc.).
"""

import logging
import os
from datetime import datetime, timezone
from typing import Dict, Any, List
import pandas as pd

from .strategy_executor import StrategyExecutor
from src.bot.custom_scripts import load_custom_strategy_config

logger = logging.getLogger(__name__)


class CustomStrategyExecutor(StrategyExecutor):
    """Executes custom strategy detectors"""
    
    def __init__(self, config_file: str):
        """
        Initialize custom strategy executor
        
        Args:
            config_file: Path to custom strategies configuration file
        """
        super().__init__(config_file, 'custom_strategies')
        self.strategy_loader = None
        self.assets = []
        self.detectors = {}  # Cache for detector instances
    
    def initialize(self) -> bool:
        """Initialize strategy resources"""
        try:
            # Load custom strategy configuration
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
            config_path = os.path.join(project_root, self.config_file)
            
            self.strategy_loader = load_custom_strategy_config(config_path)
            self.assets = self.strategy_loader.get_assets()
            
            logger.info(f"✅ Loaded {len(self.assets)} custom strategy assets from {self.config_file}")
            for asset in self.assets:
                logger.info(f"   - {asset['symbol']}: {asset.get('strategy', 'N/A')}")
            
            return True
            
        except FileNotFoundError:
            logger.error(f"❌ Configuration file not found: {self.config_file}")
            return False
        except Exception as e:
            logger.error(f"❌ Error initializing custom strategy executor: {e}")
            return False
    
    def get_symbols(self) -> List[Dict[str, Any]]:
        """Get list of assets to analyze"""
        return self.assets
    
    def _get_or_create_detector(self, symbol: str):
        """
        Get cached detector or create new one
        
        Args:
            symbol: Trading symbol
            
        Returns:
            Detector instance
        """
        if symbol not in self.detectors:
            detector = self.strategy_loader.create_detector(symbol)
            self.detectors[symbol] = detector
            logger.info(f"    🔧 Created detector for {symbol}")
        return self.detectors[symbol]
    
    def analyze_symbol(self, symbol_config: Dict[str, Any], data: pd.DataFrame) -> Dict[str, Any]:
        """
        Analyze a single symbol with custom detector
        
        Args:
            symbol_config: Symbol configuration
            data: OHLCV DataFrame
            
        Returns:
            Analysis results
        """
        symbol = symbol_config['symbol']
        strategy = symbol_config.get('strategy', 'unknown')
        
        try:
            # Get or create detector
            detector = self._get_or_create_detector(symbol)
            
            # Convert data format for detector (expects 'timestamp' column)
            data_for_detector = data.copy()
            data_for_detector.reset_index(inplace=True)
            if 'index' in data_for_detector.columns:
                data_for_detector.rename(columns={'index': 'timestamp'}, inplace=True)
            elif data_for_detector.index.name:
                data_for_detector['timestamp'] = data_for_detector.index
                data_for_detector.reset_index(drop=True, inplace=True)
            
            # Detect signals
            signal_result = detector.detect_signals(data_for_detector, symbol)
            
            # Get current market data
            current_candle = data.iloc[-1]
            current_price = float(current_candle['close'])
            
            # Create analysis result
            analysis_result = {
                'symbol': symbol,
                'status': 'analyzed',
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'last_candle': str(data.index[-1]),
                'current_price': current_price,
                'data_points': len(data),
                'strategy': strategy,
                'signal': signal_result,
                'data': data,
                'message': f'Analysis completed for {symbol}'
            }
            
            # Log signal if generated
            signal_type = signal_result.get('signal_type', 'no_signal')
            if signal_type in ['long', 'short']:
                logger.info(f"    🚨 SIGNAL: {signal_type.upper()} at {current_price:.4f}")
                logger.info(f"       Reason: {signal_result.get('reason', 'N/A')}")
                
                # Format session high/low only if numeric
                session_high = signal_result.get('session_high', 'N/A')
                session_low = signal_result.get('session_low', 'N/A')
                session_high_str = f"{session_high:.4f}" if isinstance(session_high, (int, float)) else session_high
                session_low_str = f"{session_low:.4f}" if isinstance(session_low, (int, float)) else session_low
                
                logger.info(f"       Session High: {session_high_str}")
                logger.info(f"       Session Low: {session_low_str}")
            else:
                logger.info(f"    ✅ Analysis completed: {current_price:.4f} - {signal_result.get('reason', 'No signal')}")
            
            return analysis_result
            
        except Exception as e:
            logger.error(f"    ❌ Error analyzing {symbol}: {e}", exc_info=True)
            return {
                'symbol': symbol,
                'status': 'analysis_failed',
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'error': str(e),
                'message': f'Analysis failed for {symbol}'
            }

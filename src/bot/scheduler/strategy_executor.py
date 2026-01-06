#!/usr/bin/env python3
"""
Abstract Strategy Executor Interface

Defines the base interface that all strategy executors must implement.
"""

import contextlib
import logging
import os
import sys
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
import pandas as pd

logger = logging.getLogger(__name__)


@contextlib.contextmanager
def suppress_stdout():
    """Context manager to suppress stdout temporarily"""
    with open(os.devnull, "w") as devnull:
        old_stdout = sys.stdout
        sys.stdout = devnull
        try:
            yield
        finally:
            sys.stdout = old_stdout


class StrategyExecutor(ABC):
    """
    Abstract base class for strategy executors
    
    Each strategy executor is responsible for:
    - Loading its own configuration
    - Managing its own symbols/assets
    - Executing analysis for each symbol
    - Returning results in a standardized format
    """
    
    def __init__(self, config_file: str, strategy_name: str):
        """
        Initialize strategy executor
        
        Args:
            config_file: Path to strategy configuration file
            strategy_name: Name of the strategy (for logging/identification)
        """
        self.config_file = config_file
        self.strategy_name = strategy_name
        self.symbols = []
        
        logger.info(f"🔧 Initializing {strategy_name} executor")
        logger.info(f"📁 Config file: {config_file}")
    
    @abstractmethod
    def initialize(self) -> bool:
        """
        Initialize strategy resources (load config, create detectors, etc.)
        
        Returns:
            True if initialization successful, False otherwise
        """
        pass
    
    @abstractmethod
    def get_symbols(self) -> List[Dict[str, Any]]:
        """
        Get list of symbols/assets to analyze
        
        Returns:
            List of symbol configuration dictionaries
        """
        pass
    
    def fetch_symbol_data(self, symbol_config: Dict[str, Any]) -> Optional[pd.DataFrame]:
        """
        Fetch latest candles for a symbol (shared implementation)
        
        Args:
            symbol_config: Symbol configuration dictionary
            
        Returns:
            DataFrame with OHLCV data or None if failed
        """
        from src.data_fetcher import DataFetcher
        
        fetch_symbol = symbol_config.get('fetch_symbol', symbol_config.get('symbol'))
        timeframe = symbol_config.get('timeframe', '5m')
        symbol = symbol_config.get('symbol')
        
        try:
            logger.info(f"    📊 Fetching data for {fetch_symbol} ({timeframe})...")
            
            # Create data fetcher
            fetcher = DataFetcher(
                source='forex',
                symbol=fetch_symbol,
                timeframe=timeframe,
                use_cache=False  # Always fetch fresh data for live trading
            )
            
            # Calculate years needed for ~999 candles
            if timeframe == '5m':
                years = 0.01  # ~3.65 days for ~999 candles
            else:
                years = 0.1  # Default fallback
            
            # Fetch data with suppressed output
            with suppress_stdout():
                data = fetcher.fetch(years=years)
            
            if data is not None and not data.empty:
                # Limit to last 999 candles
                if len(data) > 999:
                    data = data.tail(999)
                
                # Pop the last candle (remove incomplete candle)
                if len(data) > 1:
                    data = data.iloc[:-1]
                
                logger.info(f"      ✅ Fetched {len(data)} candles (last: {data.index[-1]})")
                return data
            else:
                logger.warning(f"      ❌ No data returned for {fetch_symbol}")
                return None
                
        except Exception as e:
            logger.error(f"      ❌ Error fetching data for {fetch_symbol}: {e}")
            return None
    
    @abstractmethod
    def analyze_symbol(self, symbol_config: Dict[str, Any], data: pd.DataFrame) -> Dict[str, Any]:
        """
        Analyze a single symbol and generate trading signals
        
        Args:
            symbol_config: Symbol configuration dictionary
            data: OHLCV DataFrame
            
        Returns:
            Analysis results dictionary with standardized format:
            {
                'symbol': str,
                'status': str ('analyzed', 'data_fetch_failed', 'analysis_failed'),
                'timestamp': str (ISO format),
                'signal': Dict (signal data),
                'data': DataFrame (for chart generation),
                ...
            }
        """
        pass
    
    async def execute_cycle(self) -> Dict[str, Any]:
        """
        Execute complete analysis cycle for all symbols (with error isolation)
        
        Returns:
            Cycle results dictionary with standardized format:
            {
                'strategy': str,
                'status': str ('success', 'partial', 'failed'),
                'results': List[Dict],
                'summary': Dict,
                ...
            }
        """
        cycle_start = datetime.now(timezone.utc)
        results = []
        successful_analyses = 0
        signal_counts = {'long': 0, 'short': 0, 'no_signal': 0, 'error': 0}
        
        logger.info(f"\n{'='*60}")
        logger.info(f"🚀 [{self.strategy_name.upper()}] Cycle Start")
        logger.info(f"{'='*60}")
        
        # Get symbols to analyze
        try:
            symbols = self.get_symbols()
            logger.info(f"📊 Analyzing {len(symbols)} symbols")
        except Exception as e:
            logger.error(f"❌ Failed to get symbols: {e}")
            return {
                'strategy': self.strategy_name,
                'status': 'failed',
                'error': str(e),
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
        
        # Analyze each symbol with error isolation
        for symbol_config in symbols:
            try:
                symbol = symbol_config.get('symbol', 'UNKNOWN')
                logger.info(f"  🔍 Analyzing {symbol}...")
                
                # Fetch data
                data = self.fetch_symbol_data(symbol_config)
                
                if data is None:
                    results.append({
                        'symbol': symbol,
                        'status': 'data_fetch_failed',
                        'timestamp': datetime.now(timezone.utc).isoformat(),
                        'message': 'Failed to fetch data'
                    })
                    signal_counts['error'] += 1
                    continue
                
                # Analyze symbol
                result = self.analyze_symbol(symbol_config, data)
                results.append(result)
                
                if result['status'] == 'analyzed':
                    successful_analyses += 1
                    
                    # Count signals
                    signal_type = result.get('signal', {}).get('signal_type', 'no_signal')
                    if signal_type in signal_counts:
                        signal_counts[signal_type] += 1
                    
            except Exception as e:
                logger.error(f"  ❌ Unexpected error with {symbol_config.get('symbol', 'UNKNOWN')}: {e}")
                results.append({
                    'symbol': symbol_config.get('symbol', 'UNKNOWN'),
                    'status': 'unexpected_error',
                    'timestamp': datetime.now(timezone.utc).isoformat(),
                    'error': str(e)
                })
                signal_counts['error'] += 1
        
        # Cycle summary
        cycle_end = datetime.now(timezone.utc)
        cycle_duration = (cycle_end - cycle_start).total_seconds()
        
        logger.info(f"\n{'='*60}")
        logger.info(f"📊 [{self.strategy_name.upper()}] Cycle Summary:")
        logger.info(f"   Duration: {cycle_duration:.1f} seconds")
        logger.info(f"   Symbols analyzed: {successful_analyses}/{len(symbols)}")
        logger.info(f"   🟢 Long signals: {signal_counts['long']}")
        logger.info(f"   🔴 Short signals: {signal_counts['short']}")
        logger.info(f"   ⚪ No signals: {signal_counts['no_signal']}")
        logger.info(f"   ❌ Errors: {signal_counts['error']}")
        logger.info(f"{'='*60}\n")
        
        # Determine overall status
        if successful_analyses == 0:
            status = 'failed'
        elif successful_analyses < len(symbols):
            status = 'partial'
        else:
            status = 'success'
        
        return {
            'strategy': self.strategy_name,
            'status': status,
            'cycle_start': cycle_start.isoformat(),
            'cycle_end': cycle_end.isoformat(),
            'duration_seconds': cycle_duration,
            'results': results,
            'summary': {
                'total_symbols': len(symbols),
                'successful_analyses': successful_analyses,
                'signal_counts': signal_counts
            }
        }
    
    def get_strategy_name(self) -> str:
        """Get strategy identifier"""
        return self.strategy_name

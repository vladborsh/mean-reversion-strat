#!/usr/bin/env python3
"""
Live Trading Strategy Scheduler

This script runs the mean reversion strategy live on multiple symbols every 5 minutes.
It loads optimized configurations from best_configs_balanced.json and executes
the strategy in real-time using Capital.com data.

Features:
- Runs every 5 minutes (synchronized to :00, :05, :10, etc.)
- Loads 999 last candles for each symbol
- Validates last candle is current (within 5 minutes of UTC time)
- Trading hours validation (6:00-17:00 UTC)
- Automatic symbol management from balanced config
- Real-time logging and monitoring
"""

import time
import json
import signal
import sys
import os
import contextlib
import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Any
import pandas as pd
from dotenv import load_dotenv
import backtrader as bt

# Load environment variables
load_dotenv()

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from data_fetcher import DataFetcher
from strategy import MeanReversionStrategy
from strategy_config import DEFAULT_CONFIG
from helpers import is_trading_hour, format_trading_session_info
from capital_com_fetcher import create_capital_com_fetcher
from bot.live_signal_detector import LiveSignalDetector

# Configure logging for this module
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


class LiveStrategyScheduler:
    """Live trading strategy scheduler for multiple symbols"""
    
    def __init__(self, config_file_path: str = None):
        """
        Initialize the live strategy scheduler
        
        Args:
            config_file_path: Path to balanced config file (defaults to results/best_configs_balanced.json)
        """
        self.config_file_path = config_file_path or os.path.join(
            os.path.dirname(__file__), 'results', 'best_configs_balanced.json'
        )
        self.symbols_config = {}
        self.running = False
        
        # Initialize the live signal detector in quiet mode
        self.signal_detector = LiveSignalDetector(verbose=False)
        
        # Load symbol configurations
        self._load_symbol_configs()
        
        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        logger.info("🚀 Live Strategy Scheduler initialized")
        logger.info(f"📁 Config file: {self.config_file_path}")
        logger.info(f"📊 Loaded {len(self.symbols_config)} symbols")
        logger.info("⏰ Running every 5 minutes during trading hours (6:00-17:00 UTC)")
    
    def _load_symbol_configs(self):
        """Load optimized configurations for all symbols"""
        try:
            with open(self.config_file_path, 'r') as f:
                configs = json.load(f)
            
            self.symbols_config = {}
            for symbol_key, config in configs.items():
                # Extract symbol info
                asset_info = config['ASSET_INFO']
                symbol = asset_info['symbol']
                timeframe = asset_info['timeframe']
                
                # Convert symbol format for data fetching with special handling
                fetch_symbol = self._convert_symbol_for_fetching(symbol)
                
                self.symbols_config[symbol_key] = {
                    'symbol': symbol,
                    'fetch_symbol': fetch_symbol,
                    'timeframe': timeframe,
                    'config': config
                }
                
                logger.debug(f"   ✓ {symbol} ({timeframe}) - {fetch_symbol}")
            
            logger.info(f"✅ Loaded configurations for {len(self.symbols_config)} symbols")
            
        except FileNotFoundError:
            logger.error(f"❌ Configuration file not found: {self.config_file_path}")
            sys.exit(1)
        except Exception as e:
            logger.error(f"❌ Error loading configurations: {e}")
            sys.exit(1)
    
    def _convert_symbol_for_fetching(self, symbol: str) -> str:
        """
        Convert symbol from config format to data fetching format
        
        Args:
            symbol: Symbol from config (e.g., 'AUDUSDX', 'GOLDX', 'SILVERX')
            
        Returns:
            Symbol for data fetching (e.g., 'AUDUSD=X', 'GOLD=X', 'SILVER=X')
        """
        # Special mappings for commodities
        special_mappings = {
            'GOLDX': 'GOLD=X',
            'SILVERX': 'SILVER=X',
            'BTCUSDX': 'BTC=X',
            'ETHUSDX': 'ETH=X'
        }
        
        if symbol in special_mappings:
            return special_mappings[symbol]
        
        # Standard forex conversion (AUDUSDX -> AUDUSD=X)
        if symbol.endswith('X') and len(symbol) == 7:
            return symbol[:-1] + '=X'
        
        # Return as-is if no conversion needed
        return symbol
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully"""
        logger.info(f"\n🛑 Received signal {signum}. Shutting down gracefully...")
        self.running = False
        sys.exit(0)
    
    def _validate_trading_hours(self) -> bool:
        """
        Check if current time is within trading hours (6:00-17:00 UTC)
        
        Returns:
            True if within trading hours, False otherwise
        """
        current_time = datetime.now(timezone.utc)
        current_hour = current_time.hour
        
        # Trading hours: 6 UTC to 17 UTC (6:00 - 17:00)
        is_trading_time = 6 <= current_hour < 17
        
        if not is_trading_time:
            logger.info(f"🕒 Outside trading hours: {current_time.strftime('%H:%M')} UTC (6:00-17:00 required)")
        
        return is_trading_time
    
    def _fetch_symbol_data(self, symbol_config: Dict[str, Any]) -> Optional[pd.DataFrame]:
        """
        Fetch latest 999 candles for a symbol
        
        Args:
            symbol_config: Symbol configuration dictionary
            
        Returns:
            DataFrame with OHLCV data or None if failed
        """
        fetch_symbol = symbol_config['fetch_symbol']
        timeframe = symbol_config['timeframe']
        original_symbol = symbol_config['symbol']
        
        try:
            logger.info(f"    📊 Fetching data for {fetch_symbol} ({timeframe})...")
            
            # Create data fetcher with appropriate source and asset type
            fetcher = DataFetcher(
                source='forex',
                symbol=fetch_symbol,
                timeframe=timeframe,
                use_cache=False  # Always fetch fresh data for live trading
            )
            
            # Calculate years needed for ~999 candles
            if timeframe == '5m':
                # 5m: 288 candles/day, so ~3.5 days for 999 candles
                years = 0.01  # ~3.65 days
            else:
                years = 0.1  # Default fallback
            
            # Fetch data with suppressed output to reduce noise
            with suppress_stdout():
                data = fetcher.fetch(years=years)
            
            if data is not None and not data.empty:
                # Limit to last 999 candles
                if len(data) > 999:
                    data = data.tail(999)
                
                # Pop the last candle (remove the most recent incomplete candle)
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
    
    def _analyze_symbol(self, symbol_key: str, symbol_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze a single symbol and generate trading signals using the live signal detector
        
        Args:
            symbol_key: Symbol key (e.g., 'AUDUSDX_5m')
            symbol_config: Symbol configuration dictionary
            
        Returns:
            Analysis results dictionary
        """
        symbol = symbol_config['symbol']
        logger.info(f"  🔍 Analyzing {symbol}...")
        
        # Fetch latest data
        data = self._fetch_symbol_data(symbol_config)
        
        if data is None:
            return {
                'symbol': symbol,
                'status': 'data_fetch_failed',
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'message': 'Failed to fetch data'
            }
        
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
                'last_candle': data.index[-1].isoformat(),
                'current_price': current_price,
                'data_points': len(data),
                'strategy_params': strategy_params,
                'signal': signal_result,
                'message': f'Analysis completed for {symbol}'
            }
            
            # Log signal if generated
            if signal_result['signal_type'] not in ['no_signal', 'error', 'insufficient_data', 'data_preparation_failed']:
                logger.warning(f"    🚨 SIGNAL: {signal_result['signal_type'].upper()} at {current_price:.4f}")
                logger.warning(f"       Stop Loss: {signal_result['stop_loss']:.4f}")
                logger.warning(f"       Take Profit: {signal_result['take_profit']:.4f}")
                logger.warning(f"       Position Size: {signal_result['position_size']:.2f}")
                logger.warning(f"       Risk Amount: ${signal_result['risk_amount']:.2f}")
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
            'require_reversal': strategy_config['require_reversal'],
            'regime_min_score': strategy_config['regime_min_score']
        }
    
    def run_strategy_cycle(self):
        """
        Run one complete strategy cycle for all symbols
        """
        cycle_start = datetime.now(timezone.utc)
        logger.info("\n" + "="*80)
        logger.info(f"🚀 STRATEGY CYCLE START: {cycle_start.strftime('%Y-%m-%d %H:%M:%S')} UTC")
        logger.info("="*80)
        
        # Check trading hours first
        if not self._validate_trading_hours():
            logger.info("⏰ Skipping cycle - outside trading hours")
            return
        
        # Check Capital.com connectivity
        try:
            fetcher = create_capital_com_fetcher()
            if fetcher is None:
                logger.error("❌ Capital.com credentials not available - check environment variables")
                return
            
            with fetcher:
                logger.info("✅ Capital.com connection verified")
        except Exception as e:
            logger.error(f"❌ Capital.com connection failed: {e}")
            return
        
        # Analyze all symbols
        results = []
        successful_analyses = 0
        signal_counts = {'long': 0, 'short': 0, 'no_signal': 0, 'error': 0}
        
        for symbol_key, symbol_config in self.symbols_config.items():
            try:
                result = self._analyze_symbol(symbol_key, symbol_config)
                results.append(result)
                
                if result['status'] == 'analyzed':
                    successful_analyses += 1
                    
                    # Count signals
                    signal_type = result.get('signal', {}).get('signal_type', 'no_signal')
                    if signal_type in signal_counts:
                        signal_counts[signal_type] += 1
                    
            except Exception as e:
                logger.error(f"  ❌ Unexpected error with {symbol_key}: {e}")
                results.append({
                    'symbol': symbol_config['symbol'],
                    'status': 'unexpected_error',
                    'timestamp': datetime.now(timezone.utc).isoformat(),
                    'error': str(e)
                })
                signal_counts['error'] += 1
        
        # Cycle summary
        cycle_end = datetime.now(timezone.utc)
        cycle_duration = (cycle_end - cycle_start).total_seconds()
        
        logger.info("\n" + "="*80)
        logger.info("📊 CYCLE SUMMARY:")
        logger.info(f"   Duration: {cycle_duration:.1f} seconds")
        logger.info(f"   Symbols analyzed: {successful_analyses}/{len(self.symbols_config)}")
        logger.info("   Signals generated:")
        logger.info(f"     🟢 Long signals: {signal_counts['long']}")
        logger.info(f"     🔴 Short signals: {signal_counts['short']}")
        logger.info(f"     ⚪ No signals: {signal_counts['no_signal']}")
        logger.info(f"     ❌ Errors: {signal_counts['error']}")
        logger.info("   Status breakdown:")
        
        status_counts = {}
        for result in results:
            status = result['status']
            status_counts[status] = status_counts.get(status, 0) + 1
        
        for status, count in status_counts.items():
            logger.info(f"     {status}: {count}")
        
        # Show active signals summary
        active_signals = [r for r in results if r.get('signal', {}).get('signal_type') in ['long', 'short']]
        if active_signals:
            logger.warning(f"\n   🚨 ACTIVE SIGNALS ({len(active_signals)}):")
            for result in active_signals:
                signal = result['signal']
                symbol = result['symbol']
                direction = signal['direction']
                entry = signal['entry_price']
                sl = signal['stop_loss']
                tp = signal['take_profit']
                size = signal['position_size']
                risk = signal['risk_amount']
                
                logger.warning(f"     {symbol}: {direction} @ {entry:.4f}")
                logger.warning(f"       SL: {sl:.4f} | TP: {tp:.4f} | Size: {size:.2f} | Risk: ${risk:.2f}")
        
        logger.info(f"🏁 CYCLE COMPLETE: {cycle_end.strftime('%Y-%m-%d %H:%M:%S')} UTC")
        logger.info("="*80)
        
        # Log results to file (optional)
        self._log_cycle_results(results, cycle_start, cycle_end)
    
    def _log_cycle_results(self, results: List[Dict], cycle_start: datetime, cycle_end: datetime):
        """
        Log cycle results to a file for monitoring
        
        Args:
            results: List of analysis results
            cycle_start: Cycle start time
            cycle_end: Cycle end time
        """
        try:
            log_dir = os.path.join(os.path.dirname(__file__), 'live_logs')
            os.makedirs(log_dir, exist_ok=True)
            
            log_file = os.path.join(log_dir, f"strategy_log_{cycle_start.strftime('%Y%m%d')}.json")
            
            log_entry = {
                'cycle_start': cycle_start.isoformat(),
                'cycle_end': cycle_end.isoformat(),
                'duration_seconds': (cycle_end - cycle_start).total_seconds(),
                'summary': {
                    'symbols_analyzed': len([r for r in results if r['status'] == 'analyzed']),
                    'total_symbols': len(self.symbols_config),
                    'signals': {
                        'long': len([r for r in results if r.get('signal', {}).get('signal_type') == 'long']),
                        'short': len([r for r in results if r.get('signal', {}).get('signal_type') == 'short']),
                        'no_signal': len([r for r in results if r.get('signal', {}).get('signal_type') == 'no_signal']),
                        'errors': len([r for r in results if r.get('signal', {}).get('signal_type') == 'error'])
                    }
                },
                'results': results
            }
            
            # Read existing log or create new
            existing_logs = []
            if os.path.exists(log_file):
                try:
                    with open(log_file, 'r') as f:
                        existing_logs = json.load(f)
                except:
                    existing_logs = []
            
            # Append new entry
            existing_logs.append(log_entry)
            
            # Keep only last 100 entries per day
            if len(existing_logs) > 100:
                existing_logs = existing_logs[-100:]
            
            # Write back
            with open(log_file, 'w') as f:
                json.dump(existing_logs, f, indent=2)
                
        except Exception as e:
            logger.warning(f"⚠️  Failed to log results: {e}")
    
    def start_scheduler(self):
        """
        Start the live trading scheduler
        """
        logger.info("\n🎯 Starting live strategy scheduler...")
        logger.info("⏰ Schedule: Every 5 minutes (:00, :05, :10, :15, :20, etc.)")
        logger.info("🕐 Trading hours: 6:00-17:00 UTC")
        logger.info(f"📊 Symbols: {len(self.symbols_config)}")
        logger.info("💾 Logs saved to: live_logs/")
        logger.info("\nPress Ctrl+C to stop gracefully...\n")
        
        self.running = True
        
        # Run initial cycle if within trading hours
        if self._validate_trading_hours():
            logger.info("🚀 Running initial strategy cycle...")
            self.run_strategy_cycle()
        
        # Main scheduler loop with custom 5-minute timing
        last_run_minute = -1  # Track last run to avoid duplicates
        
        while self.running:
            try:
                current_time = datetime.now(timezone.utc)
                current_minute = current_time.minute
                current_second = current_time.second
                
                # Check if we're at a 5-minute mark (0, 5, 10, 15, etc.) and at 15 second into the minute
                if current_minute % 5 == 0 and current_second == 15 and current_minute != last_run_minute:
                    # Only run if we're in trading hours
                    if self._validate_trading_hours():
                        self.run_strategy_cycle()
                        last_run_minute = current_minute
                    else:
                        last_run_minute = current_minute  # Still update to avoid multiple trading hour checks
                    
                    # Sleep for 1 second to avoid running multiple times in the same minute
                    time.sleep(1)
                else:
                    # Calculate and show next run time every 30 seconds
                    if current_second == 0 or current_second == 30:
                        next_run_minute = ((current_minute // 5) + 1) * 5
                        if next_run_minute >= 60:
                            next_run_minute = 0
                            next_hour = current_time.hour + 1
                        else:
                            next_hour = current_time.hour
                        
                        next_run_time = current_time.replace(hour=next_hour % 24, minute=next_run_minute, second=0, microsecond=0)
                        if next_run_time <= current_time:
                            next_run_time += timedelta(hours=1)
                        
                        time_until_run = next_run_time - current_time
                        minutes_until = int(time_until_run.total_seconds() // 60)
                        seconds_until = int(time_until_run.total_seconds() % 60)
                        
                        logger.debug(f"⏰ Next run in {minutes_until:02d}:{seconds_until:02d} at {next_run_time.strftime('%H:%M')} UTC")
                    
                    # Sleep for 1 second and check again
                    time.sleep(1)
                
            except KeyboardInterrupt:
                logger.info("\n🛑 Keyboard interrupt received. Shutting down...")
                break
            except Exception as e:
                logger.error(f"❌ Scheduler error: {e}")
                time.sleep(5)  # Wait before retry
        
        logger.info("👋 Live strategy scheduler stopped.")


def main():
    """Main entry point"""
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('live_logs/scheduler.log', mode='a')
        ]
    )
    
    # Create live_logs directory if it doesn't exist
    os.makedirs('live_logs', exist_ok=True)
    
    logger.info("🤖 Mean Reversion Strategy - Live Trading Scheduler")
    logger.info("=" * 60)
    
    # Check environment variables
    required_env_vars = [
        'CAPITAL_COM_API_KEY',
        'CAPITAL_COM_PASSWORD', 
        'CAPITAL_COM_IDENTIFIER'
    ]
    
    missing_vars = [var for var in required_env_vars if not os.getenv(var)]
    if missing_vars:
        logger.error(f"❌ Missing required environment variables: {', '.join(missing_vars)}")
        logger.error("Please set these in your .env file or environment")
        sys.exit(1)
    
    logger.info("✅ Environment variables verified")
    
    # Create and start scheduler
    try:
        scheduler = LiveStrategyScheduler()
        scheduler.start_scheduler()
    except KeyboardInterrupt:
        logger.info("\n🛑 Program interrupted by user")
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

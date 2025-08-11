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
- R        logger.info("⏰ Schedule: Every 5 minutes (:00, :05, :10, :15, :20, etc.)")
        logger.info("🕐 Trading hours: 6:00-17:00 UTC")
        logger.info(f"📊 Symbols: {len(self.symbols_config)}")
        logger.info(f"📱 Telegram notifications: {'Enabled' if self.enable_telegram else 'Disabled'}")
        logger.info("\nPress Ctrl+C to stop gracefully...\n")me logging and monitoring
"""

import time
import json
import signal
import sys
import os
import contextlib
import logging
import asyncio
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Any
import pandas as pd
from dotenv import load_dotenv
import backtrader as bt

# Load environment variables
load_dotenv()

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from src.data_fetcher import DataFetcher
from src.strategy import MeanReversionStrategy
from src.strategy_config import DEFAULT_CONFIG
from src.helpers import is_trading_hour, format_trading_session_info
from src.capital_com_fetcher import create_capital_com_fetcher
from src.bot.live_signal_detector import LiveSignalDetector
from src.bot.telegram_bot import create_telegram_bot_from_env, TelegramBotManager
from src.bot.signal_cache import create_signal_cache
from src.symbol_config_manager import SymbolConfigManager

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
    
    def __init__(self, config_file_path: str = None, enable_telegram: bool = True):
        """
        Initialize the live strategy scheduler
        
        Args:
            config_file_path: Path to balanced config file (defaults to results/best_configs_balanced.json)
            enable_telegram: Whether to enable Telegram notifications
        """
        self.config_file_path = config_file_path or os.path.join(
            os.path.dirname(__file__), 'results', 'best_configs_balanced.json'
        )
        self.symbols_config = {}
        self.running = False
        self.enable_telegram = enable_telegram
        
        # Initialize the live signal detector
        self.signal_detector = LiveSignalDetector()
        
        # Initialize signal cache with persistence to prevent duplicate notifications
        # Use DynamoDB for persistence if available, otherwise fall back to in-memory
        use_persistence = os.getenv('USE_PERSISTENT_CACHE', 'true').lower() == 'true'
        self.signal_cache = create_signal_cache(
            use_persistence=use_persistence,
            price_tolerance=0.0005, 
            cache_duration_hours=24
        )
        
        # Initialize Telegram bot if enabled
        self.telegram_bot = None
        if self.enable_telegram:
            try:
                # Create bot with DynamoDB persistence enabled
                self.telegram_bot = create_telegram_bot_from_env(use_dynamodb=True)
                if self.telegram_bot:
                    logger.info("📱 Telegram bot integration enabled with DynamoDB persistence")
                else:
                    logger.warning("⚠️  Telegram bot disabled - TELEGRAM_BOT_TOKEN not found")
                    self.enable_telegram = False
            except Exception as e:
                logger.error(f"❌ Failed to initialize Telegram bot: {e}")
                self.enable_telegram = False
        
        # Load symbol configurations
        try:
            self.symbols_config = SymbolConfigManager.load_symbol_configs(self.config_file_path)
        except FileNotFoundError:
            logger.error(f"❌ Configuration file not found: {self.config_file_path}")
            sys.exit(1)
        except Exception as e:
            logger.error(f"❌ Error loading configurations: {e}")
            sys.exit(1)
        
        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        logger.info("🚀 Live Strategy Scheduler initialized")
        logger.info(f"📁 Config file: {self.config_file_path}")
        logger.info(f"📊 Loaded {len(self.symbols_config)} symbols")
        logger.info(f"📱 Telegram notifications: {'Enabled' if self.enable_telegram else 'Disabled'}")
        logger.info("⏰ Running every 5 minutes during trading hours (6:00-17:00 UTC)")
    
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
        is_trading_time = 6 <= current_hour < 19
        
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
                logger.info(f"    🚨 SIGNAL: {signal_result['signal_type'].upper()} at {current_price:.4f}")
                logger.info(f"       Stop Loss: {signal_result['stop_loss']:.4f}")
                logger.info(f"       Take Profit: {signal_result['take_profit']:.4f}")
                logger.info(f"       Position Size: {signal_result['position_size']:.2f}")
                logger.info(f"       Risk Amount: ${signal_result['risk_amount']:.2f}")

                # Send Telegram notification if enabled
                if self.enable_telegram and self.telegram_bot:
                    asyncio.create_task(self._send_telegram_signal(analysis_result))
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
    
    async def _send_telegram_signal(self, analysis_result: Dict[str, Any]):
        """
        Send Telegram notification for a trading signal
        
        Args:
            analysis_result: Dictionary containing analysis results with signal data
        """
        try:
            if not self.telegram_bot:
                return
            
            signal_data = analysis_result.get('signal', {})
            if signal_data.get('signal_type') in ['long', 'short']:
                # Prepare signal data for Telegram
                telegram_signal_data = {
                    'signal_type': signal_data.get('signal_type'),
                    'symbol': analysis_result.get('symbol'),
                    'direction': signal_data.get('direction', signal_data.get('signal_type', '').upper()),
                    'entry_price': signal_data.get('entry_price'),
                    'stop_loss': signal_data.get('stop_loss'),
                    'take_profit': signal_data.get('take_profit'),
                    'position_size': signal_data.get('position_size'),
                    'risk_amount': signal_data.get('risk_amount'),
                    'risk_reward_ratio': signal_data.get('risk_reward_ratio', 2.0),
                    'strategy_params': analysis_result.get('strategy_params', {})
                }
                
                # Check if this signal is a duplicate
                if self.signal_cache.is_duplicate(telegram_signal_data):
                    return
                
                # Add signal to cache BEFORE sending to prevent race conditions
                cache_success = self.signal_cache.add_signal(telegram_signal_data)
                if cache_success:
                    logger.debug(f"✅ Signal cached for {telegram_signal_data['symbol']} before sending")
                else:
                    logger.warning(f"⚠️ Failed to cache signal for {telegram_signal_data['symbol']} - continuing with send")
                
                # Send notification
                result = await self.telegram_bot.send_signal_notification(telegram_signal_data)
                logger.info(f"📱 Telegram signal sent to {result.get('sent', 0)} chats")
                
                if result.get('sent', 0) == 0:
                    logger.warning(f"⚠️ No chats received signal for {telegram_signal_data['symbol']}")
                
        except Exception as e:
            logger.error(f"❌ Error sending Telegram signal: {e}")
    
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
        
        # Log cache statistics periodically
        cache_stats = self.signal_cache.get_cache_stats()
        
        # Show both local and DynamoDB cache stats
        local_count = cache_stats.get('cached_signals_local', cache_stats.get('cached_signals', 0))
        db_count = cache_stats.get('cached_signals_dynamodb', 0)
        duplicates_prevented = cache_stats.get('duplicates_prevented', 0)
        
        if duplicates_prevented > 0:
            logger.info(f"📊 Signal cache: {duplicates_prevented} duplicates prevented "
                       f"({cache_stats['duplicate_rate']:.1f}% duplicate rate)")
        
        logger.info(f"💾 Cache status: Local={local_count} DynamoDB={db_count} signals")
        
        logger.info(f"🏁 CYCLE COMPLETE: {cycle_end.strftime('%Y-%m-%d %H:%M:%S')} UTC")
        logger.info("="*80)
    
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
        Start the live trading scheduler (synchronous wrapper)
        """
        asyncio.run(self.start_scheduler_async())
    
    async def start_scheduler_async(self):
        """
        Start the live trading scheduler with Telegram integration
        """
        logger.info("\n🎯 Starting live strategy scheduler...")
        logger.info("⏰ Schedule: Every 5 minutes (:00, :05, :10, :15, :20, etc.)")
        logger.info("🕐 Trading hours: 6:00-17:00 UTC")
        logger.info(f"📊 Symbols: {len(self.symbols_config)}")
        logger.info(f"� Telegram notifications: {'Enabled' if self.enable_telegram else 'Disabled'}")
        logger.info("�💾 Logs saved to: live_logs/")
        logger.info("\nPress Ctrl+C to stop gracefully...\n")
        
        # Initialize Telegram bot if enabled
        telegram_task = None
        if self.enable_telegram and self.telegram_bot:
            try:
                if await self.telegram_bot.initialize():
                    telegram_task = asyncio.create_task(self.telegram_bot.start_bot())
                    logger.info("📱 Telegram bot started successfully")
                else:
                    logger.error("❌ Failed to initialize Telegram bot")
                    self.enable_telegram = False
            except Exception as e:
                logger.error(f"❌ Error starting Telegram bot: {e}")
                self.enable_telegram = False
        
        self.running = True
        
        try:
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
                        await asyncio.sleep(1)
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
                        await asyncio.sleep(1)
                    
                except KeyboardInterrupt:
                    logger.info("\n🛑 Keyboard interrupt received. Shutting down...")
                    break
                except Exception as e:
                    logger.error(f"❌ Scheduler error: {e}")
                    await asyncio.sleep(5)  # Wait before retry
        
        finally:
            # Stop Telegram bot if running
            if telegram_task and self.telegram_bot:
                try:
                    await self.telegram_bot.stop_bot()
                    telegram_task.cancel()
                    logger.info("📱 Telegram bot stopped")
                except Exception as e:
                    logger.error(f"❌ Error stopping Telegram bot: {e}")
            
            logger.info("👋 Live strategy scheduler stopped.")


def main():
    """Main entry point"""


def main():
    """Main entry point"""
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler()
        ]
    )
    
    # Suppress telegram bot HTTP polling logs
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("telegram").setLevel(logging.WARNING)
    
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

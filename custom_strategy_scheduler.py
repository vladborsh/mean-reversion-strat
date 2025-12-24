#!/usr/bin/env python3
"""
Custom Strategy Scheduler for Live Trading

This script runs custom signal detection strategies (e.g., AsiaSessionSweepDetector) 
live on multiple symbols every 5 minutes. It operates independently from the mean 
reversion scheduler and uses its own configuration format.

Features:
- Runs every 5 minutes (synchronized to :00, :05, :10, etc.)
- Loads custom detectors from src/bot/custom_scripts/
- Trading hours validation (6:00-17:00 UTC)
- Real-time logging and monitoring
- Telegram notifications for signals (reuses telegram bot components)
- Signal caching to prevent duplicate notifications
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

# Load environment variables
load_dotenv()

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from src.data_fetcher import DataFetcher
from src.capital_com_fetcher import create_capital_com_fetcher
from src.bot.custom_scripts import load_custom_strategy_config
from src.bot.telegram_bot import create_telegram_bot_from_env, TelegramBotManager
from src.bot.signal_cache import create_signal_cache
from src.bot.signal_chart_generator import SignalChartGenerator

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


class CustomStrategyScheduler:
    """Custom strategy scheduler for live trading"""
    
    def __init__(self, config_file_path: str = None, enable_telegram: bool = True):
        """
        Initialize the custom strategy scheduler
        
        Args:
            config_file_path: Path to custom strategy config file (defaults to assets_config_custom_strategies.json)
            enable_telegram: Whether to enable Telegram notifications
        """
        self.config_file_path = config_file_path or os.path.join(
            os.path.dirname(__file__), 'assets_config_custom_strategies.json'
        )
        self.running = False
        self.enable_telegram = enable_telegram
        
        # Initialize the signal chart generator
        self.chart_generator = SignalChartGenerator()
        
        # Initialize signal cache with persistence to prevent duplicate notifications
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
                self.telegram_bot = create_telegram_bot_from_env(use_dynamodb=True)
                if self.telegram_bot:
                    logger.info("📱 Telegram bot integration enabled with DynamoDB persistence")
                else:
                    logger.warning("⚠️  Telegram bot disabled - TELEGRAM_BOT_TOKEN not found")
                    self.enable_telegram = False
            except Exception as e:
                logger.error(f"❌ Failed to initialize Telegram bot: {e}")
                self.enable_telegram = False
        
        # Load custom strategy configuration
        try:
            self.strategy_loader = load_custom_strategy_config(self.config_file_path)
            self.assets = self.strategy_loader.get_assets()
            self.detectors = {}  # Cache for detector instances
            
            logger.info(f"✅ Loaded {len(self.assets)} custom strategy assets")
            for asset in self.assets:
                logger.info(f"   - {asset['symbol']}: {asset.get('strategy', 'N/A')}")
                
        except FileNotFoundError:
            logger.error(f"❌ Configuration file not found: {self.config_file_path}")
            sys.exit(1)
        except Exception as e:
            logger.error(f"❌ Error loading custom strategy configuration: {e}")
            sys.exit(1)
        
        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        logger.info("🚀 Custom Strategy Scheduler initialized")
        logger.info(f"📁 Config file: {self.config_file_path}")
        logger.info(f"📊 Loaded {len(self.assets)} assets")
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
        
        # Trading hours: 6 UTC to 17 UTC
        is_trading_time = 6 <= current_hour < 19
        
        if not is_trading_time:
            logger.info(f"🕒 Outside trading hours: {current_time.strftime('%H:%M')} UTC (6:00-17:00 required)")
        
        return is_trading_time
    
    def _fetch_symbol_data(self, asset: Dict[str, Any]) -> Optional[pd.DataFrame]:
        """
        Fetch latest candles for a symbol
        
        Args:
            asset: Asset configuration dictionary
            
        Returns:
            DataFrame with OHLCV data or None if failed
        """
        fetch_symbol = asset['fetch_symbol']
        timeframe = asset.get('timeframe', '5m')
        symbol = asset['symbol']
        
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
    
    def _analyze_symbol(self, asset: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze a single symbol with custom detector
        
        Args:
            asset: Asset configuration dictionary
            
        Returns:
            Analysis results dictionary
        """
        symbol = asset['symbol']
        strategy = asset.get('strategy', 'unknown')
        logger.info(f"  🔍 Analyzing {symbol} (strategy: {strategy})...")
        
        # Fetch latest data
        data = self._fetch_symbol_data(asset)
        
        if data is None:
            return {
                'symbol': symbol,
                'status': 'data_fetch_failed',
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'message': 'Failed to fetch data'
            }
        
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
                'last_candle': data.index[-1].isoformat(),
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
                
                # Send Telegram notification if enabled
                if self.enable_telegram and self.telegram_bot:
                    asyncio.create_task(self._send_telegram_signal(analysis_result))
            else:
                logger.info(f"    ✅ Analysis completed: {current_price:.4f} - {signal_result.get('reason', 'No signal')}")
            
            return analysis_result
            
        except Exception as e:
            logger.error(f"    ❌ Error analyzing {symbol}: {e}", exc_info=True)
            return {
                'symbol': symbol,
                'status': 'analysis_error',
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'error': str(e),
                'message': f'Analysis failed for {symbol}'
            }
    
    async def _send_telegram_signal(self, analysis_result: Dict[str, Any]):
        """
        Send Telegram notification for custom strategy signal
        
        Args:
            analysis_result: Analysis result with signal
        """
        try:
            signal = analysis_result['signal']
            symbol = analysis_result['symbol']
            strategy = analysis_result.get('strategy', 'custom')
            
            # Check cache to prevent duplicate notifications
            cache_key = f"{symbol}_{signal['signal_type']}_{signal.get('current_price', 0)}"
            if self.signal_cache.is_duplicate(cache_key):
                logger.info(f"    ⏭️  Skipping duplicate signal notification for {symbol}")
                return
            
            # Format signal data
            signal_data = {
                'symbol': symbol,
                'direction': signal.get('direction', 'HOLD'),
                'signal_type': signal['signal_type'],
                'entry_price': signal.get('current_price', analysis_result['current_price']),
                'session_high': signal.get('session_high', 0),
                'session_low': signal.get('session_low', 0),
                'reason': signal.get('reason', ''),
                'timestamp': signal.get('timestamp', datetime.now(timezone.utc)).isoformat() if isinstance(signal.get('timestamp'), datetime) else signal.get('timestamp'),
                'strategy': strategy
            }
            
            # Generate chart if available
            chart_buffer = None
            try:
                if 'data' in analysis_result:
                    chart_buffer = self.chart_generator.generate_signal_chart(
                        data=analysis_result['data'],
                        signal=signal_data,
                        symbol=symbol
                    )
            except Exception as e:
                logger.warning(f"    ⚠️  Failed to generate chart: {e}")
            
            # Send notification
            result = await self.telegram_bot.send_custom_message(
                f"🔧 **CUSTOM STRATEGY SIGNAL**\n\n"
                f"🎯 *Symbol:* `{symbol}`\n"
                f"📊 *Strategy:* `{strategy}`\n"
                f"📈 *Signal:* `{signal['signal_type'].upper()}`\n"
                f"💰 *Entry Price:* `{signal_data['entry_price']:.4f}`\n"
                f"📊 *Session High:* `{signal_data['session_high']:.4f}`\n"
                f"📊 *Session Low:* `{signal_data['session_low']:.4f}`\n"
                f"📝 *Reason:* {signal_data['reason']}\n\n"
                f"⏰ *Time:* `{signal_data['timestamp']}`"
            )
            
            if result.get('sent', 0) > 0:
                logger.info(f"    ✅ Signal notification sent to {result['sent']} chats")
                # Add to cache
                self.signal_cache.add_signal(cache_key, signal_data)
            else:
                logger.warning(f"    ⚠️  Failed to send signal notification")
                
        except Exception as e:
            logger.error(f"    ❌ Error sending Telegram signal: {e}")
    
    def run_strategy_cycle(self):
        """
        Run one complete strategy cycle for all assets
        """
        cycle_start = datetime.now(timezone.utc)
        logger.info("\n" + "="*80)
        logger.info(f"🚀 CUSTOM STRATEGY CYCLE START: {cycle_start.strftime('%Y-%m-%d %H:%M:%S')} UTC")
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
        
        # Analyze all assets
        results = []
        successful_analyses = 0
        signal_counts = {'long': 0, 'short': 0, 'no_signal': 0, 'error': 0}
        
        for asset in self.assets:
            try:
                result = self._analyze_symbol(asset)
                results.append(result)
                
                if result['status'] == 'analyzed':
                    successful_analyses += 1
                    
                    # Count signals
                    signal_type = result.get('signal', {}).get('signal_type', 'no_signal')
                    if signal_type in signal_counts:
                        signal_counts[signal_type] += 1
                    
            except Exception as e:
                logger.error(f"  ❌ Unexpected error with {asset['symbol']}: {e}")
                results.append({
                    'symbol': asset['symbol'],
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
        logger.info(f"   Assets analyzed: {successful_analyses}/{len(self.assets)}")
        logger.info("   Signals generated:")
        logger.info(f"     🟢 Long signals: {signal_counts['long']}")
        logger.info(f"     🔴 Short signals: {signal_counts['short']}")
        logger.info(f"     ⚪ No signals: {signal_counts['no_signal']}")
        logger.info(f"     ❌ Errors: {signal_counts['error']}")
        
        # Show active signals summary
        active_signals = [r for r in results if r.get('signal', {}).get('signal_type') in ['long', 'short']]
        if active_signals:
            logger.warning(f"\n   🚨 ACTIVE SIGNALS ({len(active_signals)}):")
            for result in active_signals:
                signal = result['signal']
                symbol = result['symbol']
                direction = signal['direction']
                price = signal.get('current_price', result['current_price'])
                session_high = signal.get('session_high', 0)
                session_low = signal.get('session_low', 0)
                
                logger.warning(f"     {symbol}: {direction} @ {price:.4f}")
                logger.warning(f"       Session High: {session_high:.4f} | Session Low: {session_low:.4f}")
        
        # Log cache statistics
        cache_stats = self.signal_cache.get_cache_stats()
        duplicates_prevented = cache_stats.get('duplicates_prevented', 0)
        
        if duplicates_prevented > 0:
            logger.info(f"📊 Signal cache: {duplicates_prevented} duplicates prevented")
        
        logger.info(f"🏁 CYCLE COMPLETE: {cycle_end.strftime('%Y-%m-%d %H:%M:%S')} UTC")
        logger.info("="*80)
    
    def start_scheduler(self):
        """
        Start the custom strategy scheduler (synchronous wrapper)
        """
        asyncio.run(self.start_scheduler_async())
    
    async def start_scheduler_async(self):
        """
        Start the custom strategy scheduler with Telegram integration
        """
        logger.info("\n🎯 Starting custom strategy scheduler...")
        logger.info("⏰ Schedule: Every 5 minutes (:00, :05, :10, :15, :20, etc.)")
        logger.info("🕐 Trading hours: 6:00-17:00 UTC")
        logger.info(f"📊 Assets: {len(self.assets)}")
        logger.info(f"📱 Telegram notifications: {'Enabled' if self.enable_telegram else 'Disabled'}")
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
            
            # Main scheduler loop
            last_run_minute = -1
            
            while self.running:
                try:
                    current_time = datetime.now(timezone.utc)
                    current_minute = current_time.minute
                    current_second = current_time.second
                    
                    # Check if at 5-minute mark and 15 seconds in
                    if current_minute % 5 == 0 and current_second == 15 and current_minute != last_run_minute:
                        if self._validate_trading_hours():
                            self.run_strategy_cycle()
                            last_run_minute = current_minute
                        else:
                            last_run_minute = current_minute
                        
                        await asyncio.sleep(1)
                    
                    if current_minute % 5 != 0 or current_second != 15:
                        # Calculate next run time
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
                        
                        await asyncio.sleep(1)
                    
                except KeyboardInterrupt:
                    logger.info("\n🛑 Keyboard interrupt received. Shutting down...")
                    break
                except Exception as e:
                    logger.error(f"❌ Scheduler error: {e}")
                    await asyncio.sleep(5)
        
        finally:
            # Stop Telegram bot if running
            if telegram_task and self.telegram_bot:
                try:
                    await self.telegram_bot.stop_bot()
                    telegram_task.cancel()
                    logger.info("📱 Telegram bot stopped")
                except Exception as e:
                    logger.error(f"❌ Error stopping Telegram bot: {e}")
            
            logger.info("👋 Custom strategy scheduler stopped.")


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
    
    # Suppress HTTP polling logs
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("telegram").setLevel(logging.WARNING)
    
    logger.info("🤖 Custom Strategy Scheduler - Live Trading")
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
        scheduler = CustomStrategyScheduler()
        scheduler.start_scheduler()
    except KeyboardInterrupt:
        logger.info("\n🛑 Program interrupted by user")
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

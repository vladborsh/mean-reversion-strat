#!/usr/bin/env python3
"""
Bot Orchestrator

Orchestrates multiple trading strategies running in parallel with shared infrastructure.
"""

import asyncio
import logging
import os
import signal
import sys
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List, Optional

from .config_loader import BotConfigLoader
from .mean_reversion_executor import MeanReversionExecutor
from .custom_strategy_executor import CustomStrategyExecutor
from src.bot.telegram_bot import create_telegram_bot_from_env
from src.bot.signal_cache import create_signal_cache
from src.bot.signal_chart_generator import SignalChartGenerator
from src.bot.telemetry import TelemetryCollector
from src.capital_com_fetcher import create_capital_com_fetcher

logger = logging.getLogger(__name__)


class BotOrchestrator:
    """
    Orchestrates multiple trading strategies with shared infrastructure
    
    Features:
    - Parallel strategy execution
    - Shared Telegram bot and signal cache
    - Error isolation (one strategy failure doesn't stop others)
    - Configurable enable/disable per strategy
    """
    
    def __init__(self, config_path: str = None):
        """
        Initialize the bot orchestrator
        
        Args:
            config_path: Path to bot_config.json (defaults to project root)
        """
        # Load configuration
        self.config = BotConfigLoader(config_path)
        
        # Shared infrastructure (singletons)
        self.telegram_bot = None
        self.signal_cache = None
        self.chart_generator = None
        self.telemetry = None
        
        # Strategy executors
        self.executors: Dict[str, Any] = {}
        
        # State
        self.running = False
        self.bot_start_time = datetime.now(timezone.utc)
        
        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        logger.info("🚀 Bot Orchestrator initialized")
        logger.info(f"📁 Config: {self.config.config_path}")
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully"""
        logger.info(f"\n🛑 Received signal {signum}. Shutting down gracefully...")
        self.running = False
        sys.exit(0)
    
    def _initialize_shared_infrastructure(self) -> bool:
        """
        Initialize shared infrastructure (Telegram bot, signal cache, chart generator)
        
        Returns:
            True if successful, False otherwise
        """
        try:
            # Initialize signal chart generator
            self.chart_generator = SignalChartGenerator()
            logger.info("✅ Signal chart generator initialized")
            
            # Initialize signal cache
            cache_config = self.config.get_signal_cache_config()
            use_persistence = cache_config.get('use_persistence', True)
            price_tolerance = cache_config.get('price_tolerance', 0.0005)
            cache_duration_hours = cache_config.get('cache_duration_hours', 24)
            
            self.signal_cache = create_signal_cache(
                use_persistence=use_persistence,
                price_tolerance=price_tolerance,
                cache_duration_hours=cache_duration_hours
            )
            logger.info(f"✅ Signal cache initialized (persistence: {use_persistence})")
            
            # Initialize Telegram bot if enabled
            if self.config.is_telegram_enabled():
                try:
                    use_dynamodb = self.config.should_use_dynamodb()
                    self.telegram_bot = create_telegram_bot_from_env(use_dynamodb=use_dynamodb)
                    if self.telegram_bot:
                        logger.info(f"✅ Telegram bot initialized (DynamoDB: {use_dynamodb})")
                    else:
                        logger.warning("⚠️  Telegram bot disabled - TELEGRAM_BOT_TOKEN not found")
                except Exception as e:
                    logger.error(f"❌ Failed to initialize Telegram bot: {e}")
            else:
                logger.info("ℹ️  Telegram notifications disabled in config")
            
            # Initialize telemetry collector
            if self.config.is_telemetry_enabled():
                try:
                    self.telemetry = TelemetryCollector.instance()
                    persistence_path = self.config.get_telemetry_persistence_path()
                    self.telemetry.configure(enabled=True, persistence_path=persistence_path)
                    logger.info(f"✅ Telemetry collector initialized (persistence: {persistence_path is not None})")
                except Exception as e:
                    logger.error(f"❌ Failed to initialize telemetry: {e}")
                    self.telemetry = None
            else:
                logger.info("ℹ️  Telemetry collection disabled in config")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize shared infrastructure: {e}")
            return False
    
    def _initialize_strategy_executors(self) -> bool:
        """
        Initialize all enabled strategy executors
        
        Returns:
            True if at least one executor initialized successfully
        """
        enabled_strategies = self.config.get_enabled_strategies()
        
        if not enabled_strategies:
            logger.error("❌ No strategies enabled in configuration")
            return False
        
        logger.info(f"📊 Initializing {len(enabled_strategies)} enabled strategies")
        
        success_count = 0
        
        for strategy_name, strategy_config in enabled_strategies.items():
            try:
                logger.info(f"\n🔧 Initializing {strategy_name}...")
                
                config_file = strategy_config['config_file']
                executor_class = strategy_config['executor_class']
                
                # Create executor based on class name
                if executor_class == 'MeanReversionExecutor':
                    executor = MeanReversionExecutor(config_file)
                elif executor_class == 'CustomStrategyExecutor':
                    executor = CustomStrategyExecutor(config_file)
                else:
                    logger.error(f"❌ Unknown executor class: {executor_class}")
                    continue
                
                # Initialize executor
                if executor.initialize():
                    self.executors[strategy_name] = executor
                    success_count += 1
                    logger.info(f"✅ {strategy_name} initialized successfully")
                else:
                    logger.error(f"❌ {strategy_name} initialization failed")
                    
            except Exception as e:
                logger.error(f"❌ Error initializing {strategy_name}: {e}")
        
        logger.info(f"\n📊 Initialized {success_count}/{len(enabled_strategies)} strategies")
        
        return success_count > 0
    
    async def initialize(self) -> bool:
        """
        Initialize all bot components
        
        Returns:
            True if initialization successful
        """
        logger.info("\n" + "="*80)
        logger.info("🚀 INITIALIZING UNIFIED TRADING BOT")
        logger.info("="*80)
        
        # Initialize shared infrastructure
        if not self._initialize_shared_infrastructure():
            return False
        
        # Initialize strategy executors
        if not self._initialize_strategy_executors():
            return False
        
        # Initialize Telegram bot async components
        if self.telegram_bot:
            try:
                if await self.telegram_bot.initialize():
                    logger.info("✅ Telegram bot async initialization complete")
                else:
                    logger.warning("⚠️  Telegram bot async initialization failed")
            except Exception as e:
                logger.error(f"❌ Telegram bot async initialization error: {e}")
        
        logger.info("\n✅ Bot initialization complete")
        logger.info("="*80 + "\n")
        
        return True
    
    def _validate_trading_hours(self) -> bool:
        """
        Check if current time is within trading hours
        
        Returns:
            True if within trading hours, False otherwise
        """
        trading_hours = self.config.get_trading_hours()
        start_hour = trading_hours.get('start_hour_utc', 6)
        end_hour = trading_hours.get('end_hour_utc', 19)
        
        current_time = datetime.now(timezone.utc)
        current_hour = current_time.hour
        
        is_trading_time = start_hour <= current_hour < end_hour
        
        if not is_trading_time:
            logger.info(f"🕒 Outside trading hours: {current_time.strftime('%H:%M')} UTC ({start_hour}:00-{end_hour}:00 required)")
        
        return is_trading_time
    
    async def _execute_strategy_safe(self, strategy_name: str, executor: Any) -> Dict[str, Any]:
        """
        Execute a strategy with error isolation
        
        Args:
            strategy_name: Strategy identifier
            executor: Strategy executor instance
            
        Returns:
            Strategy execution results
        """
        try:
            emoji = self.config.get_strategy_emoji(strategy_name)
            logger.info(f"{emoji} Executing {strategy_name}...")
            
            result = await executor.execute_cycle()
            
            if result['status'] == 'success':
                logger.info(f"{emoji} {strategy_name} completed successfully")
            elif result['status'] == 'partial':
                logger.warning(f"{emoji} {strategy_name} completed with some errors")
            else:
                logger.error(f"{emoji} {strategy_name} failed")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Fatal error executing {strategy_name}: {e}")
            return {
                'strategy': strategy_name,
                'status': 'failed',
                'error': str(e),
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
    
    async def _send_telegram_notification(self, analysis_result: Dict[str, Any], strategy_name: str):
        """
        Send Telegram notification for a trading signal
        
        Args:
            analysis_result: Analysis result with signal data
            strategy_name: Name of the strategy that generated the signal
        """
        try:
            if not self.telegram_bot:
                return
            
            signal_data = analysis_result.get('signal', {})
            signal_type = signal_data.get('signal_type')
            
            if signal_type not in ['long', 'short']:
                return
            
            # Add strategy prefix to signal cache key
            cache_key_prefix = f"{strategy_name}_"
            
            # Prepare signal data based on strategy type
            if strategy_name == 'mean_reversion':
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
                    'strategy_params': analysis_result.get('strategy_params', {}),
                    'strategy': strategy_name
                }
            else:  # custom_strategies
                telegram_signal_data = {
                    'signal_type': signal_data.get('signal_type'),
                    'symbol': analysis_result.get('symbol'),
                    'direction': signal_data.get('direction', signal_data.get('signal_type', '').upper()),
                    'entry_price': signal_data.get('current_price', analysis_result.get('current_price')),
                    'session_high': signal_data.get('session_high', 0),
                    'session_low': signal_data.get('session_low', 0),
                    'reason': signal_data.get('reason', ''),
                    'timestamp': signal_data.get('timestamp', datetime.now(timezone.utc)).isoformat() if isinstance(signal_data.get('timestamp'), datetime) else signal_data.get('timestamp'),
                    'strategy': analysis_result.get('strategy', 'custom')
                }
            
            # Check if this signal is a duplicate (with strategy prefix)
            if self.signal_cache and self.signal_cache.is_duplicate(telegram_signal_data):
                logger.info(f"⏭️  Skipping duplicate signal for {telegram_signal_data['symbol']}")
                if self.telemetry:
                    self.telemetry.increment('signals.duplicate', strategy=strategy_name)
                return
            
            # Add signal to cache BEFORE sending
            if self.signal_cache:
                cache_success = self.signal_cache.add_signal(telegram_signal_data)
                if cache_success:
                    logger.debug(f"✅ Signal cached for {telegram_signal_data['symbol']}")
            
            # Record signal in telemetry
            if self.telemetry:
                self.telemetry.record_signal({
                    'strategy': strategy_name,
                    'symbol': telegram_signal_data.get('symbol'),
                    'signal_type': signal_type,
                    'entry_price': telegram_signal_data.get('entry_price')
                })
                self.telemetry.increment(f'signals.{signal_type}', strategy=strategy_name)
            
            # Generate chart
            chart_buffer = None
            try:
                data = analysis_result.get('data')
                if data is not None:
                    chart_buffer = self.chart_generator.generate_signal_chart(
                        data=data,
                        signal_data=signal_data,
                        strategy_params=analysis_result.get('strategy_params', {}),
                        symbol=analysis_result.get('symbol')
                    )
            except Exception as e:
                logger.error(f"❌ Failed to generate chart: {e}")
            
            # Add strategy emoji to notification
            emoji = self.config.get_strategy_emoji(strategy_name)
            telegram_signal_data['strategy_emoji'] = emoji
            
            # Send notification
            result = await self.telegram_bot.send_signal_notification(telegram_signal_data, chart_buffer=chart_buffer)
            logger.info(f"📱 Telegram signal sent to {result.get('sent', 0)} chats")
            
        except Exception as e:
            logger.error(f"❌ Error sending Telegram signal: {e}")
    
    async def run_strategy_cycle(self):
        """Run one complete strategy cycle for all enabled strategies"""
        cycle_start = datetime.now(timezone.utc)
        
        logger.info("\n" + "="*80)
        logger.info(f"🚀 STRATEGY CYCLE START: {cycle_start.strftime('%Y-%m-%d %H:%M:%S')} UTC")
        logger.info("="*80)
        
        # Record cycle start in telemetry
        if self.telemetry:
            self.telemetry.record_event('cycle_start', {'timestamp': cycle_start.isoformat()})
            self.telemetry.increment('cycles.total')
        
        # Check trading hours
        if not self._validate_trading_hours():
            logger.info("⏰ Skipping cycle - outside trading hours")
            if self.telemetry:
                self.telemetry.increment('cycles.skipped_outside_hours')
            return
        
        # Verify Capital.com connectivity
        try:
            fetcher = create_capital_com_fetcher()
            if fetcher is None:
                logger.error("❌ Capital.com credentials not available - check environment variables")
                if self.telemetry:
                    self.telemetry.increment('errors.no_credentials')
                    self.telemetry.record_error('credentials', 'Capital.com credentials not available')
                return
            
            with fetcher:
                logger.info("✅ Capital.com connection verified")
                if self.telemetry:
                    self.telemetry.increment('api.connection_success')
        except Exception as e:
            logger.error(f"❌ Capital.com connection failed: {e}")
            if self.telemetry:
                self.telemetry.increment('errors.api_connection_failed')
                self.telemetry.record_error('api_connection', str(e))
            return
        
        # Execute strategies in parallel with error isolation
        tasks = []
        for strategy_name, executor in self.executors.items():
            tasks.append(self._execute_strategy_safe(strategy_name, executor))
        
        # Run all strategies concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results and send notifications
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"❌ Strategy execution exception: {result}")
                continue
            
            if result.get('status') == 'failed':
                continue
            
            # Send Telegram notifications for signals
            strategy_name = result.get('strategy')
            for analysis_result in result.get('results', []):
                if analysis_result.get('status') == 'analyzed':
                    signal = analysis_result.get('signal', {})
                    if signal.get('signal_type') in ['long', 'short']:
                        await self._send_telegram_notification(analysis_result, strategy_name)
        
        # Aggregate summary
        cycle_end = datetime.now(timezone.utc)
        cycle_duration = (cycle_end - cycle_start).total_seconds()
        
        total_signals = {'long': 0, 'short': 0, 'no_signal': 0, 'error': 0}
        for result in results:
            if isinstance(result, dict) and 'summary' in result:
                counts = result['summary'].get('signal_counts', {})
                for signal_type, count in counts.items():
                    total_signals[signal_type] = total_signals.get(signal_type, 0) + count
        
        # Record telemetry
        if self.telemetry:
            self.telemetry.record_timing('cycle.duration', cycle_duration)
            self.telemetry.increment('signals.long', amount=total_signals['long'])
            self.telemetry.increment('signals.short', amount=total_signals['short'])
            self.telemetry.increment('signals.none', amount=total_signals['no_signal'])
            self.telemetry.increment('signals.errors', amount=total_signals['error'])
            self.telemetry.set_gauge('strategies.active', len(self.executors))
            
            # Record cycle summary
            self.telemetry.record_cycle({
                'duration': cycle_duration,
                'strategies_executed': len(self.executors),
                'signals': total_signals,
                'cycle_start': cycle_start.isoformat(),
                'cycle_end': cycle_end.isoformat()
            })
        
        logger.info("\n" + "="*80)
        logger.info("📊 AGGREGATE CYCLE SUMMARY:")
        logger.info(f"   Duration: {cycle_duration:.1f} seconds")
        logger.info(f"   Strategies executed: {len(self.executors)}")
        logger.info("   Total signals:")
        logger.info(f"     🟢 Long signals: {total_signals['long']}")
        logger.info(f"     🔴 Short signals: {total_signals['short']}")
        logger.info(f"     ⚪ No signals: {total_signals['no_signal']}")
        logger.info(f"     ❌ Errors: {total_signals['error']}")
        
        # Cache statistics
        if self.signal_cache:
            cache_stats = self.signal_cache.get_cache_stats()
            duplicates_prevented = cache_stats.get('duplicates_prevented', 0)
            if duplicates_prevented > 0:
                logger.info(f"📊 Signal cache: {duplicates_prevented} duplicates prevented")
        
        logger.info(f"🏁 CYCLE COMPLETE: {cycle_end.strftime('%Y-%m-%d %H:%M:%S')} UTC")
        logger.info("="*80 + "\n")
        
        # Persist telemetry periodically
        if self.telemetry:
            self.telemetry.persist()
    
    async def start(self):
        """Start the unified trading bot"""
        bot_config = self.config.get_bot_config()
        run_interval = self.config.get_run_interval_minutes()
        sync_second = self.config.get_sync_second()
        trading_hours = self.config.get_trading_hours()
        
        logger.info("\n🎯 Starting unified trading bot...")
        logger.info(f"⏰ Schedule: Every {run_interval} minutes (sync at :{sync_second:02d} seconds)")
        logger.info(f"🕐 Trading hours: {trading_hours['start_hour_utc']}:00-{trading_hours['end_hour_utc']}:00 UTC")
        logger.info(f"📊 Active strategies: {len(self.executors)}")
        logger.info(f"📱 Telegram notifications: {'Enabled' if self.telegram_bot else 'Disabled'}")
        logger.info("\nPress Ctrl+C to stop gracefully...\n")
        
        # Start Telegram bot if enabled
        telegram_task = None
        if self.telegram_bot:
            try:
                telegram_task = asyncio.create_task(self.telegram_bot.start_bot())
                logger.info("📱 Telegram bot started successfully")
            except Exception as e:
                logger.error(f"❌ Error starting Telegram bot: {e}")
        
        self.running = True
        
        try:
            # Run initial cycle if within trading hours
            if self._validate_trading_hours():
                logger.info("🚀 Running initial strategy cycle...")
                await self.run_strategy_cycle()
            
            # Main scheduler loop
            last_run_minute = -1
            
            while self.running:
                try:
                    current_time = datetime.now(timezone.utc)
                    current_minute = current_time.minute
                    current_second = current_time.second
                    
                    # Check if at run interval mark and sync second
                    if current_minute % run_interval == 0 and current_second == sync_second and current_minute != last_run_minute:
                        if self._validate_trading_hours():
                            await self.run_strategy_cycle()
                            last_run_minute = current_minute
                        else:
                            last_run_minute = current_minute
                        
                        await asyncio.sleep(1)
                    
                    if current_minute % run_interval != 0 or current_second != sync_second:
                        # Calculate next run time
                        if current_second == 0 or current_second == 30:
                            next_run_minute = ((current_minute // run_interval) + 1) * run_interval
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
            
            logger.info("👋 Unified trading bot stopped.")

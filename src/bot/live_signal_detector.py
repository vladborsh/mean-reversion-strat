#!/usr/bin/env python3
"""
Live Signal Detector

This module provides functionality to detect trading signals from the MeanReversionStrategy
in real-time using backtrader's cerebro engine. It captures new orders that the strategy
would place at the current time without actually executing trades.

Features:
- Date range filtering for historical analysis
- Signal analysis caching for performance
- Support for both real-time and historical signal detection
"""

import pandas as pd
import backtrader as bt
import logging
import hashlib
import json
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, Union

logger = logging.getLogger(__name__)

try:
    from ..strategy import MeanReversionStrategy
    from ..backtest import LeveragedBroker
except ImportError:
    import sys
    import os
    sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
    from strategy import MeanReversionStrategy
    from backtest import LeveragedBroker


class LiveOrderCapture(MeanReversionStrategy):
    """
    Wrapper strategy that captures orders from MeanReversionStrategy 
    without actually executing trades
    """
    
    def __init__(self):
        super().__init__()
        self.current_time_orders = []
        self.last_order_info = None
        self.previous_order = None  # Track previous order state
        
    def next(self):
        # Call the original strategy's next() method
        super().next()
        
        # Check if we have a NEW order (transition from None to not-None)
        if self.order is not None and self.previous_order is None:
            # Capture the order details that the strategy just created
            self._capture_new_order()
        
        # Update previous order state for next iteration
        self.previous_order = self.order
    
    def _capture_new_order(self):
        """Capture details of the new order that was just placed"""
        if self.order is None:
            return
        
        # Get current real time for comparison
        current_real_time = datetime.now(timezone.utc)
        
        # Check if order is too old (more than 10 minutes from now)
        if hasattr(self, 'order_entry_time'):
            order_time = self.order_entry_time
        else:
            # Fallback to current candle time if order time not available
            order_time = self.datas[0].datetime.datetime(0)
        
        # Make order_time timezone-aware if it's naive (assume UTC)
        if order_time.tzinfo is None:
            order_time = order_time.replace(tzinfo=timezone.utc)
        
        time_diff = (current_real_time - order_time).total_seconds() / 60.0  # Convert to minutes

        logger.info(f"⏰ Order is {time_diff:.1f} minutes old (limit: 10 min)")

        # Reject orders older than 10 minutes
        if time_diff > 10.0:
            logger.info(f"⏰ Rejecting old order: {time_diff:.1f} minutes old (limit: 10 min)")
            logger.debug(f"   Order time: {order_time}, Current time: {current_real_time}")
            return
        
        # Extract order information from the strategy's state
        entry_price = self.dataclose[0]  # Current price (entry)
        stop_loss = getattr(self, 'stop_price', 0.0)
        take_profit = getattr(self, 'take_profit_price', 0.0)
        
        # Get risk metrics if available
        if hasattr(self, 'risk_manager') and hasattr(self, 'atr'):
            try:
                # Determine direction based on actual order or strategy state
                if hasattr(self.order, 'isbuy'):
                    # Use order's isbuy() method if available
                    if self.order.isbuy():
                        direction = 'BUY'
                        signal_type = 'long'
                    else:
                        direction = 'SELL'
                        signal_type = 'short'
                elif hasattr(self.order, 'size'):
                    # Check order size to determine direction
                    if self.order.size > 0:
                        direction = 'BUY'
                        signal_type = 'long'
                    else:
                        direction = 'SELL'
                        signal_type = 'short'
                else:
                    # Fallback: determine from stop loss position relative to entry
                    if stop_loss < entry_price:
                        direction = 'BUY'
                        signal_type = 'long'
                    else:
                        direction = 'SELL'
                        signal_type = 'short'
                
                # Get risk metrics from the risk manager
                risk_metrics = self.risk_manager.get_risk_metrics(
                    entry_price, stop_loss, take_profit, signal_type
                )
                
                # Get position size from order (if available) or calculate
                position_size = getattr(self.order, 'size', 0) if self.order else 0
                if position_size == 0 and hasattr(self, 'risk_manager'):
                    account_value = self.get_account_value_for_risk_management()
                    position_size = self.risk_manager.calculate_position_size(
                        account_value, entry_price, stop_loss
                    )
                
                order_info = {
                    'signal_type': signal_type,
                    'direction': direction,
                    'entry_price': entry_price,
                    'stop_loss': stop_loss,
                    'take_profit': take_profit,
                    'position_size': abs(position_size),
                    'risk_amount': risk_metrics.get('risk_amount', 0.0),
                    'atr_value': self.atr[0] if len(self.atr) > 0 else 0.0,
                    'reason': 'New order detected by MeanReversionStrategy'
                }
                
                self.current_time_orders.append(order_info)
                self.last_order_info = order_info
                
            except Exception as e:
                # Fallback with basic information - detect direction from stop loss
                if stop_loss < entry_price:
                    fallback_direction = 'BUY'
                    fallback_signal_type = 'long'
                else:
                    fallback_direction = 'SELL'
                    fallback_signal_type = 'short'
                    
                self.last_order_info = {
                    'signal_type': fallback_signal_type,
                    'direction': fallback_direction,
                    'entry_price': entry_price,
                    'stop_loss': stop_loss,
                    'take_profit': take_profit,
                    'position_size': 0.0,
                    'risk_amount': 0.0,
                    'atr_value': 0.0,
                    'reason': f'Order detected but details extraction failed: {e}'
                }


class LiveSignalDetector:
    """
    Detects live trading signals by running MeanReversionStrategy through cerebro
    and capturing new orders placed at current time

    Features:
    - Date range filtering for historical analysis
    - Caching of signal analysis results
    - Support for both real-time and historical detection
    """

    def __init__(self, use_cache: bool = True, cache_duration_hours: int = 1):
        """
        Initialize the live signal detector

        Args:
            use_cache: Whether to enable signal analysis caching
            cache_duration_hours: How long to cache analysis results (default 1 hour)
        """
        self.use_cache = use_cache
        self.cache_duration_hours = cache_duration_hours
        self._signal_cache = {}  # In-memory cache for signal analysis
        self._cache_cleanup_counter = 0  # Counter for periodic cleanup

        # Try to use persistent cache if available
        self._persistent_cache = None
        if use_cache:
            try:
                from ..data_cache import DataCache
                from ..transport_factory import create_cache_transport
                transport = create_cache_transport(transport_type='local')
                self._persistent_cache = DataCache(transport=transport)
                logger.info("Persistent cache enabled for signal analysis")
            except Exception as e:
                logger.warning(f"Failed to initialize persistent cache, using in-memory only: {e}")
    
    def prepare_backtrader_data(self, data: pd.DataFrame,
                               start_date: Optional[Union[str, datetime]] = None,
                               end_date: Optional[Union[str, datetime]] = None) -> Optional[pd.DataFrame]:
        """
        Prepare pandas DataFrame for backtrader consumption with optional date filtering

        Args:
            data: Raw OHLCV data
            start_date: Optional start date for filtering (string or datetime)
            end_date: Optional end date for filtering (string or datetime)

        Returns:
            Processed DataFrame ready for backtrader or None if failed
        """
        try:
            # Ensure data has the correct format for backtrader
            if not isinstance(data.index, pd.DatetimeIndex):
                data.index = pd.to_datetime(data.index)

            # Apply date range filtering if specified
            if start_date is not None or end_date is not None:
                # Parse dates
                if start_date is not None:
                    if isinstance(start_date, str):
                        start_date = pd.to_datetime(start_date)
                    data = data[data.index >= start_date]
                    logger.debug(f"Filtered data from {start_date}")

                if end_date is not None:
                    if isinstance(end_date, str):
                        end_date = pd.to_datetime(end_date)
                    data = data[data.index <= end_date]
                    logger.debug(f"Filtered data until {end_date}")

            # Make sure all required columns exist and are properly named
            data = data.copy()
            required_columns = ['open', 'high', 'low', 'close', 'volume']
            for col in required_columns:
                if col not in data.columns:
                    if col == 'volume':
                        # If volume is missing, add a dummy volume column
                        data['volume'] = 1000000
                    else:
                        logger.debug(f"Required column '{col}' not found in data")
                        return None

            # Ensure all data is numeric
            for col in required_columns:
                data[col] = pd.to_numeric(data[col], errors='coerce')

            # Drop any rows with NaN values
            data = data.dropna()

            if data.empty:
                logger.debug("Data is empty after cleaning")
                return None

            return data[required_columns]

        except Exception as e:
            logger.debug(f"Error preparing backtrader data: {e}")
            return None
    
    def detect_signals(self, data: pd.DataFrame, strategy_params: Dict[str, Any], symbol: str) -> Dict[str, Any]:
        """
        Run backtrader cerebro analysis using the existing MeanReversionStrategy
        to detect new trading signals at current time
        
        Args:
            data: Prepared OHLCV data
            strategy_params: Strategy parameters
            symbol: Trading symbol
            
        Returns:
            Signal analysis result
        """
        try:
            # Create cerebro instance
            cerebro = bt.Cerebro()
            
            # Create datafeed with explicit column mapping
            datafeed = bt.feeds.PandasData(
                dataname=data,
                datetime=None,  # Use index as datetime
                open='open',
                high='high', 
                low='low',
                close='close',
                volume='volume',
                openinterest=-1
            )
            
            cerebro.adddata(datafeed)
            
            # Add the strategy with the provided parameters (exactly as configured)
            # Strategy parameters (verbose parameter removed - using logger instead)
            strategy_params_clean = strategy_params.copy()
            
            cerebro.addstrategy(LiveOrderCapture, **strategy_params_clean)
            
            # Set up leveraged broker (matching production environment)
            leveraged_broker = LeveragedBroker(leverage=100.0, actual_cash=100000.0, verbose=False)
            cerebro.setbroker(leveraged_broker)
            leveraged_broker.setcash(100000.0)  # This sets leveraged amount internally
            leveraged_broker.setcommission(commission=0.001)
            
            # Run the analysis
            results = cerebro.run()
            strategy = results[0]
            
            # Extract signal information from captured orders
            if strategy.last_order_info:
                return strategy.last_order_info
            else:
                return {
                    'signal_type': 'no_signal',
                    'direction': 'HOLD',
                    'entry_price': data['close'].iloc[-1],
                    'stop_loss': 0.0,
                    'take_profit': 0.0,
                    'position_size': 0.0,
                    'risk_amount': 0.0,
                    'atr_value': 0.0,
                    'reason': 'No new orders detected by MeanReversionStrategy'
                }
                
        except Exception as e:
            logger.debug(f"Cerebro analysis error: {e}")
            return {
                'signal_type': 'error',
                'direction': 'HOLD',
                'entry_price': 0.0,
                'stop_loss': 0.0,
                'take_profit': 0.0,
                'position_size': 0.0,
                'risk_amount': 0.0,
                'atr_value': 0.0,
                'reason': f'Analysis error: {str(e)}'
            }
    
    def _generate_cache_key(self, symbol: str, strategy_params: Dict[str, Any],
                           start_date: Optional[datetime] = None,
                           end_date: Optional[datetime] = None) -> str:
        """
        Generate a unique cache key for signal analysis

        Args:
            symbol: Trading symbol
            strategy_params: Strategy parameters
            start_date: Optional start date
            end_date: Optional end date

        Returns:
            Unique cache key string
        """
        # Create a stable hash of strategy parameters
        params_str = json.dumps(strategy_params, sort_keys=True)
        params_hash = hashlib.md5(params_str.encode()).hexdigest()[:8]

        # Format dates for cache key
        start_str = start_date.strftime('%Y%m%d') if start_date else 'none'
        end_str = end_date.strftime('%Y%m%d') if end_date else 'none'

        # Combine into cache key
        cache_key = f"signal_{symbol}_{params_hash}_{start_str}_{end_str}"
        return cache_key

    def _get_cached_result(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """
        Get cached analysis result if available

        Args:
            cache_key: Cache key to lookup

        Returns:
            Cached result or None if not found/expired
        """
        # Clean up old cache entries periodically
        self._cache_cleanup_counter += 1
        if self._cache_cleanup_counter >= 100:
            self._cleanup_cache()
            self._cache_cleanup_counter = 0

        # Check in-memory cache first
        if cache_key in self._signal_cache:
            cached_entry = self._signal_cache[cache_key]
            cache_time = datetime.fromisoformat(cached_entry['timestamp'])
            age = (datetime.now() - cache_time).total_seconds() / 3600  # Age in hours

            if age < self.cache_duration_hours:
                logger.debug(f"Cache hit for {cache_key} (age: {age:.1f} hours)")
                return cached_entry['result']
            else:
                # Remove expired entry
                del self._signal_cache[cache_key]

        # Try persistent cache if available
        if self._persistent_cache:
            try:
                # Use the DataCache with signal analysis type
                cached_data = self._persistent_cache.get(
                    source='signal_analysis',
                    symbol=cache_key,
                    timeframe='analysis',
                    years=None,
                    additional_params={'cache_duration': self.cache_duration_hours}
                )
                if cached_data is not None:
                    logger.debug(f"Persistent cache hit for {cache_key}")
                    # Store in memory cache for faster subsequent access
                    self._signal_cache[cache_key] = {
                        'timestamp': datetime.now().isoformat(),
                        'result': cached_data
                    }
                    return cached_data
            except Exception as e:
                logger.warning(f"Failed to retrieve from persistent cache: {e}")

        return None

    def _store_cached_result(self, cache_key: str, result: Dict[str, Any]):
        """
        Store analysis result in cache

        Args:
            cache_key: Cache key
            result: Analysis result to cache
        """
        # Store in in-memory cache
        self._signal_cache[cache_key] = {
            'timestamp': datetime.now().isoformat(),
            'result': result
        }

        # Try to store in persistent cache
        if self._persistent_cache:
            try:
                self._persistent_cache.set(
                    source='signal_analysis',
                    symbol=cache_key,
                    timeframe='analysis',
                    years=None,
                    data=result,
                    metadata={'cache_duration': self.cache_duration_hours}
                )
                logger.debug(f"Stored result in persistent cache: {cache_key}")
            except Exception as e:
                logger.warning(f"Failed to store in persistent cache: {e}")

    def _cleanup_cache(self):
        """Remove expired entries from in-memory cache"""
        current_time = datetime.now()
        expired_keys = []

        for key, entry in self._signal_cache.items():
            cache_time = datetime.fromisoformat(entry['timestamp'])
            age_hours = (current_time - cache_time).total_seconds() / 3600

            if age_hours >= self.cache_duration_hours:
                expired_keys.append(key)

        for key in expired_keys:
            del self._signal_cache[key]

        if expired_keys:
            logger.debug(f"Cleaned up {len(expired_keys)} expired cache entries")

    def analyze_symbol(self, data: pd.DataFrame, strategy_params: Dict[str, Any], symbol: str,
                      start_date: Optional[Union[str, datetime]] = None,
                      end_date: Optional[Union[str, datetime]] = None,
                      use_cache: Optional[bool] = None) -> Dict[str, Any]:
        """
        Complete analysis pipeline: prepare data and detect signals with caching

        Args:
            data: Raw OHLCV data
            strategy_params: Strategy parameters
            symbol: Trading symbol
            start_date: Optional start date for analysis
            end_date: Optional end date for analysis
            use_cache: Override instance cache setting (None = use instance setting)

        Returns:
            Signal analysis result
        """
        # Parse date parameters
        if start_date and isinstance(start_date, str):
            start_date = pd.to_datetime(start_date)
        if end_date and isinstance(end_date, str):
            end_date = pd.to_datetime(end_date)

        # Determine if caching should be used
        use_cache = self.use_cache if use_cache is None else use_cache

        # Check cache if enabled
        cache_key = None
        if use_cache:
            cache_key = self._generate_cache_key(symbol, strategy_params, start_date, end_date)
            cached_result = self._get_cached_result(cache_key)
            if cached_result is not None:
                logger.info(f"Using cached signal analysis for {symbol}")
                return cached_result

        # Validate data quality
        if len(data) < 100:
            result = {
                'signal_type': 'insufficient_data',
                'direction': 'HOLD',
                'entry_price': 0.0,
                'stop_loss': 0.0,
                'take_profit': 0.0,
                'position_size': 0.0,
                'risk_amount': 0.0,
                'atr_value': 0.0,
                'reason': f'Insufficient data points: {len(data)} < 100'
            }
            # Don't cache error results
            return result

        # Prepare data for backtrader with date filtering
        bt_data = self.prepare_backtrader_data(data, start_date, end_date)
        if bt_data is None:
            result = {
                'signal_type': 'data_preparation_failed',
                'direction': 'HOLD',
                'entry_price': 0.0,
                'stop_loss': 0.0,
                'take_profit': 0.0,
                'position_size': 0.0,
                'risk_amount': 0.0,
                'atr_value': 0.0,
                'reason': 'Failed to prepare data for backtrader'
            }
            # Don't cache error results
            return result

        # Log date range being analyzed
        if start_date or end_date:
            date_range = f"from {start_date or 'start'} to {end_date or 'end'}"
            logger.info(f"Analyzing {symbol} {date_range}")

        # Detect signals using cerebro
        result = self.detect_signals(bt_data, strategy_params, symbol)

        # Cache successful results
        if use_cache and cache_key and result['signal_type'] not in ['error', 'data_preparation_failed']:
            self._store_cached_result(cache_key, result)

        return result

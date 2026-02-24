#!/usr/bin/env python3
"""
Signal Detector

This module provides functionality to detect trading signals from the MeanReversionStrategy
using backtrader's cerebro engine. It captures new orders that the strategy would place
without actually executing trades.

Used for both backtesting analysis and live trading signal detection.
"""

import pandas as pd
import backtrader as bt
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional

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
    """
    
    def __init__(self):
        """Initialize the live signal detector"""
        pass
    
    def prepare_backtrader_data(self, data: pd.DataFrame) -> Optional[pd.DataFrame]:
        """
        Prepare pandas DataFrame for backtrader consumption
        
        Args:
            data: Raw OHLCV data
            
        Returns:
            Processed DataFrame ready for backtrader or None if failed
        """
        try:
            # Ensure data has the correct format for backtrader
            if not isinstance(data.index, pd.DatetimeIndex):
                data.index = pd.to_datetime(data.index)
            
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
    
    def analyze_symbol(self, data: pd.DataFrame, strategy_params: Dict[str, Any], symbol: str) -> Dict[str, Any]:
        """
        Complete analysis pipeline: prepare data and detect signals
        
        Args:
            data: Raw OHLCV data
            strategy_params: Strategy parameters
            symbol: Trading symbol
            
        Returns:
            Signal analysis result
        """
        # Validate data quality
        if len(data) < 100:
            return {
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
        
        # Prepare data for backtrader
        bt_data = self.prepare_backtrader_data(data)
        if bt_data is None:
            return {
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
        
        # Detect signals using cerebro
        return self.detect_signals(bt_data, strategy_params, symbol)

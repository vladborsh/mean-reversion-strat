#!/usr/bin/env python3
"""
Live Signal Detector

This module provides functionality to detect trading signals from the MeanReversionStrategy
in real-time using backtrader's cerebro engine. It captures new orders that the strategy
would place at the current time without actually executing trades.
"""

import pandas as pd
import backtrader as bt
from datetime import datetime
from typing import Dict, Any, Optional

try:
    from ..strategy import MeanReversionStrategy
except ImportError:
    import sys
    import os
    sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
    from strategy import MeanReversionStrategy


class LiveOrderCapture(MeanReversionStrategy):
    """
    Wrapper strategy that captures orders from MeanReversionStrategy 
    without actually executing trades
    """
    
    def __init__(self):
        super().__init__()
        self.current_time_orders = []
        self.last_order_info = None
        
    def next(self):
        # Store the order state before calling parent's next()
        had_order_before = self.order is not None
        had_position_before = bool(self.position)
        
        # Call the original strategy's next() method
        super().next()
        
        # Check if this is the current time (last candle) and a new order was created
        current_time = self.datas[0].datetime.datetime(0)
        now = datetime.utcnow()
        current_candle_time = current_time.replace(tzinfo=None) if current_time.tzinfo else current_time
        
        # Allow up to 5 minute tolerance for live data
        time_diff = abs((now - current_candle_time).total_seconds())
        is_current_candle = time_diff <= 300  # 5 minutes
        
        # Check if a new order was created on this current candle
        if (is_current_candle and 
            len(self.datas[0]) == len(self.datas[0].close) and
            not had_order_before and self.order is not None and
            not had_position_before):
            
            # Capture the order details that the strategy just created
            self._capture_new_order()
    
    def _capture_new_order(self):
        """Capture details of the new order that was just placed"""
        if self.order is None:
            return
        
        # Extract order information from the strategy's state
        entry_price = self.dataclose[0]  # Current price (entry)
        stop_loss = getattr(self, 'stop_price', 0.0)
        take_profit = getattr(self, 'take_profit_price', 0.0)
        
        # Get risk metrics if available
        if hasattr(self, 'risk_manager') and hasattr(self, 'atr'):
            try:
                # Determine direction based on order type or position
                direction = 'BUY'  # Default assumption for new orders
                signal_type = 'long'
                
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
                # Fallback with basic information
                self.last_order_info = {
                    'signal_type': 'unknown',
                    'direction': 'BUY',
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
    
    def __init__(self, verbose: bool = False):
        """Initialize the live signal detector
        
        Args:
            verbose: Whether to print detailed messages during analysis
        """
        self.verbose = verbose
    
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
                        if self.verbose:
                            print(f"      ❌ Required column '{col}' not found in data")
                        return None
            
            # Ensure all data is numeric
            for col in required_columns:
                data[col] = pd.to_numeric(data[col], errors='coerce')
            
            # Drop any rows with NaN values
            data = data.dropna()
            
            if data.empty:
                if self.verbose:
                    print(f"      ❌ Data is empty after cleaning")
                return None
            
            return data[required_columns]
            
        except Exception as e:
            if self.verbose:
                print(f"      ❌ Error preparing backtrader data: {e}")
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
            # Set verbose=False to reduce noise during live signal detection
            strategy_params_clean = strategy_params.copy()
            strategy_params_clean['verbose'] = False  # Force verbose mode off for live detection
            
            cerebro.addstrategy(LiveOrderCapture, **strategy_params_clean)
            
            # Set up a minimal broker (not actually trading, just for analysis)
            cerebro.broker.setcash(100000)
            cerebro.broker.setcommission(commission=0.001)
            
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
            if self.verbose:
                print(f"      ❌ Cerebro analysis error: {e}")
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

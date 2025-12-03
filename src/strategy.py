import backtrader as bt
import pandas as pd
import logging
from .indicators import Indicators
from .risk_management import RiskManager, ATRIndicator, create_risk_manager
from .config import Config
from .market_regime import MarketRegimeFilter
from .trailing_stop import TrailingStopManager

logger = logging.getLogger(__name__)

class MeanReversionStrategy(bt.Strategy):
    # Get default params and extend with timeframe and risk management
    base_params = Config.get_backtrader_params()
    base_params['timeframe'] = '15m'  # Default timeframe

    # Add risk management parameters with defaults
    risk_config = Config.get_risk_config()
    base_params['risk_per_position_pct'] = risk_config['risk_per_position_pct']
    base_params['stop_loss_atr_multiplier'] = risk_config['stop_loss_atr_multiplier']
    base_params['risk_reward_ratio'] = risk_config['risk_reward_ratio']
    
    # Add trailing stop configuration
    trailing_stop_config = Config.get_trailing_stop_config()
    base_params['trailing_stop_enabled'] = trailing_stop_config['enabled']
    
    # Removed verbose parameter - using logger instead
    
    # Convert to backtrader params format
    params = tuple(base_params.items())

    def __init__(self):
        self.dataclose = self.datas[0].close
        self.order = None
        self.buyprice = None
        self.buycomm = None
        self.trade_log = []
        self.order_log = []  # New log for all found orders
        
        # Order lifetime tracking
        self.order_entry_time = None
        self.order_lifetime_minutes = None
        
        # Initialize risk manager with strategy parameters if available, otherwise use defaults
        risk_config = Config.get_risk_config()
        
        # Override with strategy parameters if provided
        if hasattr(self.p, 'risk_per_position_pct'):
            risk_config['risk_per_position_pct'] = self.p.risk_per_position_pct
        if hasattr(self.p, 'stop_loss_atr_multiplier'):
            risk_config['stop_loss_atr_multiplier'] = self.p.stop_loss_atr_multiplier
        if hasattr(self.p, 'risk_reward_ratio'):
            risk_config['risk_reward_ratio'] = self.p.risk_reward_ratio
        
        # Initialize risk manager with logger-based output
        logger.info("MeanReversionStrategy initialized")
        
        self.risk_manager = create_risk_manager(risk_config)
        
        # Technical indicators
        self.bb_ma = bt.indicators.SimpleMovingAverage(self.datas[0], period=self.p.bb_window)
        self.bb_std = bt.indicators.StandardDeviation(self.datas[0], period=self.p.bb_window)
        self.bb_upper = self.bb_ma + self.p.bb_std * self.bb_std
        self.bb_lower = self.bb_ma - self.p.bb_std * self.bb_std
        
        self.vwap = bt.indicators.WeightedMovingAverage(self.datas[0], period=self.p.vwap_window, subplot=False)
        self.vwap_std = bt.indicators.StandardDeviation(self.datas[0], period=self.p.vwap_window)
        self.vwap_upper = self.vwap + self.p.vwap_std * self.vwap_std
        self.vwap_lower = self.vwap - self.p.vwap_std * self.vwap_std
        
        # ATR indicator for risk management
        self.atr = ATRIndicator(self.datas[0], period=self.p.atr_period)
        
        # Market regime detection filter
        if getattr(self.p, 'regime_enabled', True):
            self.regime_filter = MarketRegimeFilter(
                adx_period=getattr(self.p, 'regime_adx_period', 14),
                volatility_period=getattr(self.p, 'regime_volatility_period', 14),
                volatility_lookback=getattr(self.p, 'regime_volatility_lookback', 100),
                min_score_threshold=getattr(self.p, 'regime_min_score', 60)
            )
        else:
            self.regime_filter = None
        
        # Risk management variables
        self.stop_price = None
        self.take_profit_price = None
        
        # Deposit tracking for trade outcomes
        self.current_order_id = None
        self.deposit_before_trade = None

        # Equity curve tracking for proper portfolio value history
        self.equity_curve = []
        self.equity_dates = []

        # Initialize trailing stop manager if enabled
        trailing_stop_enabled = getattr(self.p, 'trailing_stop_enabled', False)
        if trailing_stop_enabled:
            trailing_stop_config = Config.get_trailing_stop_config()
            self.trailing_stop_manager = TrailingStopManager(
                activation_pct=trailing_stop_config.get('activation_pct', 50.0),
                breakeven_plus_pct=trailing_stop_config.get('breakeven_plus_pct', 20.0)
            )
            logger.info("Trailing Stop Manager enabled")
        else:
            self.trailing_stop_manager = None
            logger.info("Trailing Stop Manager disabled")
        
        # Set order lifetime based on timeframe
        timeframe = getattr(self.p, 'timeframe', '15m')
        order_lifetime_dict = getattr(self.p, 'order_lifetime_minutes', {
            '5m': 360,    # 6 hours for 5-minute timeframe
            '15m': 720,   # 12 hours for 15-minute timeframe
            '1h': 2880,   # 2 days for 1-hour timeframe
            'default': 720
        })
        self.order_lifetime_minutes = order_lifetime_dict.get(timeframe, order_lifetime_dict.get('default', 720))

    def _is_trading_hours(self):
        """
        Check if current time is within trading hours (6 UTC - 17 UTC).
        Returns True if within trading hours, False otherwise.
        """
        current_time = self.datas[0].datetime.time(0)
        # Get UTC hour (assuming data is already in UTC)
        current_hour = current_time.hour
        
        # Trading hours: 6 UTC to 17 UTC (6:00 - 17:00)
        return 6 <= current_hour < 17

    def next(self):
        # Track portfolio value for equity curve (do this first)
        self._track_portfolio_value()

        # Skip if ATR is not available yet
        if len(self.atr) == 0 or self.atr[0] == 0:
            return
        
        # Check if current position has exceeded order lifetime and force close
        if self.position and self.order_entry_time is not None:
            current_time = self.datas[0].datetime.datetime(0)
            time_elapsed = current_time - self.order_entry_time
            minutes_elapsed = time_elapsed.total_seconds() / 60
            
            if minutes_elapsed >= self.order_lifetime_minutes:
                logger.info(f"FORCE CLOSING position after {minutes_elapsed:.1f} minutes (lifetime: {self.order_lifetime_minutes} minutes)")
                self.close()
                self._record_trade_outcome('lifetime_expired', self.dataclose[0])  # Only for lifetime expiry use market price
                return
        
        if not self.position:
            # Check if we're within trading hours (6 UTC - 17 UTC)
            if not self._is_trading_hours():
                return  # Skip trading outside of allowed hours

            # Long signal - Buy when price breaks below both bands with green candle
            if (self.datas[0].open[0] < self.bb_lower[0] and
                self.datas[0].open[0] < self.vwap_lower[0] and
                self.datas[0].close[0] > self.datas[0].open[0]):  # Green candle confirmation
                # Check market regime conditions if filter is enabled
                regime_suitable = True
                regime_reason = "No regime filter"

                if self.regime_filter is not None:
                    # Check if we have enough data for regime analysis
                    if (len(self.regime_filter.is_suitable) > 0 and
                        len(self.regime_filter.regime_score) > 0):

                        regime_suitable = bool(self.regime_filter.is_suitable[0])
                        regime_info = self.regime_filter.get_regime_info()
                        regime_reason = regime_info.get('reason', 'Unknown regime')

                    else:
                        # Not enough data for regime analysis, be conservative
                        regime_suitable = False
                        regime_reason = "Insufficient data for regime analysis"

                if regime_suitable:
                        # Calculate risk management levels
                        entry_price = self.dataclose[0]
                        stop_loss = self.risk_manager.calculate_atr_stop_loss(
                            entry_price, self.atr[0], 'long'
                        )
                        take_profit = self.risk_manager.calculate_take_profit(
                            entry_price, stop_loss, 'long'
                        )
                        
                        # Validate trade before execution
                        is_valid, reason = self.risk_manager.validate_trade(
                            entry_price, stop_loss, take_profit, 'long'
                        )
                        
                        if is_valid:
                            # Calculate position size based on risk
                            account_value = self.get_account_value_for_risk_management()
                            position_size = self.risk_manager.calculate_position_size(
                                account_value, entry_price, stop_loss
                            )
                            
                            # Store deposit before trade for outcome tracking
                            self.deposit_before_trade = account_value

                            # Get risk metrics before using them
                            risk_metrics = self.risk_manager.get_risk_metrics(
                                entry_price, stop_loss, take_profit, 'long'
                            )

                            # Execute market order immediately
                            self.order = self.buy(size=position_size, exectype=bt.Order.Market)
                            self.stop_price = stop_loss
                            self.take_profit_price = take_profit

                            # Initialize trailing stop if enabled
                            if self.trailing_stop_manager:
                                self.trailing_stop_manager.initialize_position(
                                    entry_price, stop_loss, take_profit, 'long'
                                )

                            # Set position entry time immediately since market orders execute right away
                            self.order_entry_time = self.datas[0].datetime.datetime(0)
                            
                            # Create unique order ID
                            order_id = f"BUY_{self.datas[0].datetime.date(0).isoformat()}_{self.datas[0].datetime.time(0).isoformat().replace(':', '')}"
                            self.current_order_id = order_id
                            
                            # Get regime info for logging
                            regime_info = self.regime_filter.get_regime_info() if self.regime_filter else {}
                            
                            # Log the complete order information including regime data
                            order_info = {
                                'order_id': order_id,
                                'date': self.datas[0].datetime.date(0).isoformat(),
                                'time': self.datas[0].datetime.time(0).isoformat(),
                                'type': 'BUY',
                                'entry_price': entry_price,
                                'stop_loss': stop_loss,
                                'take_profit': take_profit,
                                'position_size': position_size,
                                'atr_value': self.atr[0],
                                'risk_amount': risk_metrics['risk_amount'],
                                'reward_amount': risk_metrics['reward_amount'],
                                'risk_reward_ratio': risk_metrics['risk_reward_ratio'],
                                'account_risk_pct': risk_metrics['risk_percentage'],
                                'deposit_before_trade': account_value,
                                'reason': f'Break below BB/VWAP lower bands with green candle - {regime_reason}',
                                # Market regime information
                                'regime_score': regime_info.get('score', 0),
                                'regime_adx': regime_info.get('adx', 0),
                                'regime_volatility_percentile': regime_info.get('volatility_percentile', 0),
                                'regime_classification': regime_info.get('regime', 'unknown')
                            }
                            self.order_log.append(order_info)
                            
                            logger.info(f"ORDER FOUND - {order_info['date']} {order_info['time']}: "
                                      f"{order_info['type']} {position_size} units at {entry_price:.4f}, "
                                      f"SL: {stop_loss:.4f} ({self.risk_manager.stop_loss_atr_multiplier}*ATR), "
                                      f"TP: {take_profit:.4f} (RR: 1:{risk_metrics['risk_reward_ratio']:.1f}), "
                                      f"Risk: {risk_metrics['risk_percentage']:.1f}% | Regime: {regime_info.get('regime', 'N/A')} "
                                      f"(Score: {regime_info.get('score', 0):.0f}, ADX: {regime_info.get('adx', 0):.1f})")
                            
                            self.trade_log.append({
                                'type': 'buy', 
                                'price': entry_price, 
                                'reason': 'Break below BB/VWAP lower with green candle'
                            })
            
            # Short signal - Sell when price breaks above both bands with red candle
            elif (self.datas[0].open[0] > self.bb_upper[0] and
                  self.datas[0].open[0] > self.vwap_upper[0] and
                  self.datas[0].close[0] < self.datas[0].open[0]):  # Red candle confirmation
                # Check market regime conditions if filter is enabled
                regime_suitable = True
                regime_reason = "No regime filter"

                if self.regime_filter is not None:
                    # Check if we have enough data for regime analysis
                    if (len(self.regime_filter.is_suitable) > 0 and
                        len(self.regime_filter.regime_score) > 0):

                        regime_suitable = bool(self.regime_filter.is_suitable[0])
                        regime_info = self.regime_filter.get_regime_info()
                        regime_reason = regime_info.get('reason', 'Unknown regime')

                    else:
                        # Not enough data for regime analysis, be conservative
                        regime_suitable = False
                        regime_reason = "Insufficient data for regime analysis"

                if regime_suitable:
                        # Calculate risk management levels
                        entry_price = self.dataclose[0]
                        stop_loss = self.risk_manager.calculate_atr_stop_loss(
                            entry_price, self.atr[0], 'short'
                        )
                        take_profit = self.risk_manager.calculate_take_profit(
                            entry_price, stop_loss, 'short'
                        )
                        
                        # Validate trade before execution
                        is_valid, reason = self.risk_manager.validate_trade(
                            entry_price, stop_loss, take_profit, 'short'
                        )
                        
                        if is_valid:
                            # Calculate position size based on risk
                            account_value = self.get_account_value_for_risk_management()
                            position_size = self.risk_manager.calculate_position_size(
                                account_value, entry_price, stop_loss
                            )
                            
                            # Store deposit before trade for outcome tracking
                            self.deposit_before_trade = account_value

                            # Get risk metrics before using them
                            risk_metrics = self.risk_manager.get_risk_metrics(
                                entry_price, stop_loss, take_profit, 'short'
                            )

                            # Execute market order immediately
                            self.order = self.sell(size=position_size, exectype=bt.Order.Market)
                            self.stop_price = stop_loss
                            self.take_profit_price = take_profit

                            # Initialize trailing stop if enabled
                            if self.trailing_stop_manager:
                                self.trailing_stop_manager.initialize_position(
                                    entry_price, stop_loss, take_profit, 'short'
                                )

                            # Set position entry time immediately since market orders execute right away
                            self.order_entry_time = self.datas[0].datetime.datetime(0)
                            
                            # Create unique order ID
                            order_id = f"SELL_{self.datas[0].datetime.date(0).isoformat()}_{self.datas[0].datetime.time(0).isoformat().replace(':', '')}"
                            self.current_order_id = order_id
                            
                            # Get regime info for logging
                            regime_info = self.regime_filter.get_regime_info() if self.regime_filter else {}
                            
                            # Log the complete order information including regime data
                            order_info = {
                                'order_id': order_id,
                                'date': self.datas[0].datetime.date(0).isoformat(),
                                'time': self.datas[0].datetime.time(0).isoformat(),
                                'type': 'SELL',
                                'entry_price': entry_price,
                                'stop_loss': stop_loss,
                                'take_profit': take_profit,
                                'position_size': position_size,
                                'atr_value': self.atr[0],
                                'risk_amount': risk_metrics['risk_amount'],
                                'reward_amount': risk_metrics['reward_amount'],
                                'risk_reward_ratio': risk_metrics['risk_reward_ratio'],
                                'account_risk_pct': risk_metrics['risk_percentage'],
                                'deposit_before_trade': account_value,
                                'reason': f'Break above BB/VWAP upper bands with red candle - {regime_reason}',
                                # Market regime information
                                'regime_score': regime_info.get('score', 0),
                                'regime_adx': regime_info.get('adx', 0),
                                'regime_volatility_percentile': regime_info.get('volatility_percentile', 0),
                                'regime_classification': regime_info.get('regime', 'unknown')
                            }
                            self.order_log.append(order_info)
                            
                            logger.info(f"ORDER FOUND - {order_info['date']} {order_info['time']}: "
                                      f"{order_info['type']} {position_size} units at {entry_price:.4f}, "
                                      f"SL: {stop_loss:.4f} ({self.risk_manager.stop_loss_atr_multiplier}*ATR), "
                                      f"TP: {take_profit:.4f} (RR: 1:{risk_metrics['risk_reward_ratio']:.1f}), "
                                      f"Risk: {risk_metrics['risk_percentage']:.1f}% | Regime: {regime_info.get('regime', 'N/A')} "
                                      f"(Score: {regime_info.get('score', 0):.0f}, ADX: {regime_info.get('adx', 0):.1f})")
                            
                            self.trade_log.append({
                                'type': 'sell', 
                                'price': entry_price, 
                                'reason': 'Break above BB/VWAP upper with red candle'
                            })
        else:
            # Update trailing stop if enabled
            if self.trailing_stop_manager:
                current_price = self.dataclose[0]
                new_stop, was_updated = self.trailing_stop_manager.update(current_price)
                if was_updated:
                    self.stop_price = new_stop
                    logger.debug(f"Trailing stop updated to {new_stop:.4f}")

            # Position management - Exit on stop loss or take profit
            if self.position.size > 0:  # Long position
                # Check if low touched stop loss
                if self.datas[0].low[0] <= self.stop_price:
                    self.close()
                    self._record_trade_outcome('stop_loss', self.stop_price)  # Use exact SL price
                # Check if high touched take profit
                elif self.datas[0].high[0] >= self.take_profit_price:
                    self.close()
                    self._record_trade_outcome('take_profit', self.take_profit_price)  # Use exact TP price
            elif self.position.size < 0:  # Short position
                # Check if high touched stop loss
                if self.datas[0].high[0] >= self.stop_price:
                    self.close()
                    self._record_trade_outcome('stop_loss', self.stop_price)  # Use exact SL price
                # Check if low touched take profit
                elif self.datas[0].low[0] <= self.take_profit_price:
                    self.close()
                    self._record_trade_outcome('take_profit', self.take_profit_price)  # Use exact TP price

    def _record_trade_outcome(self, outcome_type, exit_price):
        """Record trade outcome for visualization"""
        self.trade_log.append({'type': outcome_type, 'price': exit_price})
        
        # Store outcome info for notify_trade method
        self.pending_outcome = {
            'type': outcome_type,
            'exit_price': exit_price,
            'exit_date': self.datas[0].datetime.date(0).isoformat(),
            'exit_time': self.datas[0].datetime.time(0).isoformat()
        }

    def notify_order(self, order):
        if order.status == order.Completed:
            # Market orders execute immediately, so we already set entry time when creating the order
            self.order = None
            logger.info(f"Market Order FILLED at {self.dataclose[0]:.4f} - Position active")
            
        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            # Order was not filled (shouldn't happen with market orders, but handle edge cases)
            if order.status == order.Canceled:
                logger.info(f"Order CANCELLED")
            elif order.status == order.Rejected:
                logger.info(f"Order REJECTED")
            elif order.status == order.Margin:
                logger.info(f"Order FAILED due to margin")
                
            # Reset tracking variables
            self.order = None
            self.order_entry_time = None
            
            # Mark the order as cancelled in the log
            if hasattr(self, 'current_order_id') and self.current_order_id:
                for order_log_entry in self.order_log:
                    if order_log_entry.get('order_id') == self.current_order_id:
                        order_log_entry['trade_outcome'] = {
                            'type': 'order_cancelled',
                            'exit_price': self.dataclose[0],
                            'exit_date': self.datas[0].datetime.date(0).isoformat(),
                            'exit_time': self.datas[0].datetime.time(0).isoformat(),
                            'pnl': 0.0,
                            'deposit_before': order_log_entry.get('deposit_before_trade', 0),
                            'deposit_after': order_log_entry.get('deposit_before_trade', 0),
                            'deposit_change': 0.0
                        }
                        break
                        
                # Reset current order tracking
                self.current_order_id = None
                self.deposit_before_trade = None

    def notify_trade(self, trade):
        if trade.isclosed:
            # Reset trailing stop if enabled
            if self.trailing_stop_manager:
                self.trailing_stop_manager.reset()
            # Calculate P&L using exact exit prices instead of market prices
            calculated_pnl = trade.pnl  # Default fallback
            # If we have pending outcome with exact exit price, recalculate P&L
            if hasattr(self, 'pending_outcome') and hasattr(self, 'current_order_id'):
                # Find the corresponding order to get entry details
                for order in self.order_log:
                    if order.get('order_id') == self.current_order_id:
                        entry_price = order['entry_price']
                        exit_price = self.pending_outcome['exit_price']
                        position_size = order.get('position_size', 0)
                        order_type = order['type']
                        
                        # Calculate exact P&L based on entry and exact exit prices
                        if order_type == 'BUY':  # Long position
                            price_diff = exit_price - entry_price
                        else:  # Short position (SELL)
                            price_diff = entry_price - exit_price
                        
                        calculated_pnl = price_diff * position_size
                        
                        logger.debug(f"P&L Calculation: {order_type} {position_size} units, "
                                  f"Entry: {entry_price:.4f}, Exit: {exit_price:.4f}, "
                                  f"Diff: {price_diff:+.4f}, P&L: {calculated_pnl:+.4f}")
                        break
                    
            # Update broker's actual cash balance with calculated trade P&L
            if hasattr(self.broker, 'add_trade_pnl'):
                self.broker.add_trade_pnl(calculated_pnl)

            self.trade_log.append({'type': 'exit', 'price': trade.price, 'pnl': calculated_pnl})
            
            # Reset order entry time when position is closed
            self.order_entry_time = None
            
            # Update the corresponding order in order_log with trade outcome
            if hasattr(self, 'current_order_id') and self.current_order_id and hasattr(self, 'pending_outcome'):
                deposit_after = self.get_account_value_for_risk_management()
                deposit_before = self.deposit_before_trade if self.deposit_before_trade else deposit_after
                deposit_change = deposit_after - deposit_before
                
                # Find the order in order_log and add outcome
                for order in self.order_log:
                    if order.get('order_id') == self.current_order_id:
                        order['trade_outcome'] = {
                            'type': self.pending_outcome['type'],
                            'exit_price': self.pending_outcome['exit_price'],
                            'exit_date': self.pending_outcome['exit_date'],
                            'exit_time': self.pending_outcome['exit_time'],
                            'pnl': calculated_pnl,  # Use calculated P&L instead of trade.pnl
                            'deposit_before': deposit_before,
                            'deposit_after': deposit_after,
                            'deposit_change': deposit_change
                        }
                        break
                
                # Reset tracking variables
                self.current_order_id = None
                self.deposit_before_trade = None
                if hasattr(self, 'pending_outcome'):
                    delattr(self, 'pending_outcome')

    def stop(self):
        """Called when the strategy stops - ensure all positions are closed and orders have outcomes"""
        # Force close any remaining open position
        if self.position:
            logger.info(f"FORCE CLOSING remaining position at backtest end: {self.position.size} units")
            self.close()
            # Record the forced closure
            self._record_trade_outcome('backtest_end_forced', self.dataclose[0])
            # Let notify_trade handle the outcome recording
        
        # Find all orders without outcomes and add forced closure outcomes
        orders_without_outcomes = [order for order in self.order_log if 'trade_outcome' not in order]
        
        if orders_without_outcomes:
            logger.info(f"FORCING OUTCOMES for {len(orders_without_outcomes)} incomplete orders at backtest end")
            
            current_price = self.dataclose[0]
            current_date = self.datas[0].datetime.date(0).isoformat()
            current_time = self.datas[0].datetime.time(0).isoformat()
            current_deposit = self.get_account_value_for_risk_management()
            
            for order in orders_without_outcomes:
                # Calculate PnL based on entry vs current price for backtest end closures
                entry_price = order['entry_price']
                position_size = order.get('position_size', 0)
                
                if order['type'] == 'BUY':
                    # Long position
                    price_diff = current_price - entry_price
                else:
                    # Short position  
                    price_diff = entry_price - current_price
                
                calculated_pnl = price_diff * position_size
                deposit_before = order.get('deposit_before_trade', current_deposit)
                
                # Update broker's actual cash with the forced closure P&L
                if hasattr(self.broker, 'add_trade_pnl'):
                    self.broker.add_trade_pnl(calculated_pnl)
                
                # Add forced outcome
                order['trade_outcome'] = {
                    'type': 'backtest_end',
                    'exit_price': current_price,
                    'exit_date': current_date,
                    'exit_time': current_time,
                    'pnl': calculated_pnl,
                    'deposit_before': deposit_before,
                    'deposit_after': current_deposit,
                    'deposit_change': current_deposit - deposit_before
                }
                logger.debug(f"  Added forced outcome for {order['order_id']}: backtest_end @ {current_price:.4f}, P&L: {calculated_pnl:+.2f}")
        
        # Reset position tracking
        self.order_entry_time = None
        self.current_order_id = None
        self.deposit_before_trade = None

    def get_order_log(self):
        """Return the complete order log with guaranteed outcomes"""
        return self.order_log
    
    def print_order_summary(self):
        """Print a summary of all found orders with risk management details"""
        if not self.order_log:
            print("No orders found during strategy execution.")
            return
        
        print(f"\n=== STRATEGY ORDER SUMMARY ===")
        print(f"Total orders found: {len(self.order_log)}")
        print(f"Risk Management: {self.risk_manager.risk_per_position_pct}% per position, "
              f"{self.risk_manager.stop_loss_atr_multiplier}x ATR stop loss, "
              f"1:{self.risk_manager.risk_reward_ratio} R:R ratio")
        print(f"Order Lifetime: {self.order_lifetime_minutes} minutes ({self.order_lifetime_minutes/60:.1f} hours)")
        print("-" * 80)
        
        orders_with_outcomes = 0
        for i, order in enumerate(self.order_log, 1):
            print(f"Order #{i}:")
            print(f"  Date/Time: {order['date']} {order['time']}")
            print(f"  Type: {order['type']}")
            print(f"  Position Size: {order.get('position_size', 'N/A')} units")
            print(f"  Entry Price: {order['entry_price']:.4f}")
            print(f"  Stop Loss: {order['stop_loss']:.4f}")
            print(f"  Take Profit: {order['take_profit']:.4f}")
            print(f"  ATR Value: {order.get('atr_value', 'N/A'):.4f}")
            print(f"  Risk Amount: {order.get('risk_amount', 'N/A'):.4f}")
            print(f"  Reward Amount: {order.get('reward_amount', 'N/A'):.4f}")
            print(f"  Risk/Reward Ratio: 1:{order.get('risk_reward_ratio', 'N/A'):.2f}")
            print(f"  Account Risk %: {order.get('account_risk_pct', 'N/A'):.1f}%")
            print(f"  Reason: {order['reason']}")
            
            # Show trade outcome if available
            if 'trade_outcome' in order:
                outcome = order['trade_outcome']
                print(f"  OUTCOME: {outcome['type'].upper()} at {outcome['exit_price']:.4f}")
                print(f"           Exit: {outcome['exit_date']} {outcome['exit_time']}")
                print(f"           PnL: {outcome.get('pnl', 'N/A'):+.4f}")
                print(f"           Deposit Change: {outcome.get('deposit_change', 'N/A'):+.4f}")
                orders_with_outcomes += 1
            else:
                print(f"  OUTCOME: NO OUTCOME RECORDED")
            
            print("-" * 40)
        
        print(f"\nSUMMARY: {orders_with_outcomes}/{len(self.order_log)} orders have recorded outcomes")
        if orders_with_outcomes < len(self.order_log):
            print("WARNING: Some orders are missing outcomes - this should not happen with proper order lifetime management!")

    def get_account_value_for_risk_management(self):
        """
        Get the correct account value for risk management calculations.
        For leveraged brokers, use actual cash instead of leveraged amount.
        """
        if hasattr(self.broker, 'get_actual_cash'):
            # Using leveraged broker - get actual cash for risk management
            return self.broker.get_actual_cash()
        else:
            # Standard broker - use normal getvalue
            return self.broker.getvalue()

    def _track_portfolio_value(self):
        """Track portfolio value for equity curve calculation"""
        current_date = self.datas[0].datetime.datetime(0)
        
        # Calculate current portfolio value
        if hasattr(self.broker, 'get_actual_cash'):
            # For leveraged broker, use actual cash + unrealized P&L
            actual_cash = self.broker.get_actual_cash()
            # Calculate unrealized P&L from open positions
            unrealized_pnl = 0.0
            position = self.broker.getposition(self.datas[0])
            if position.size != 0:
                current_price = self.dataclose[0]
                unrealized_pnl = position.size * (current_price - position.price)
            portfolio_value = actual_cash + unrealized_pnl
        else:
            # Standard broker
            portfolio_value = self.broker.getvalue()
        
        # Store portfolio value and date
        self.equity_curve.append(portfolio_value)
        self.equity_dates.append(current_date)
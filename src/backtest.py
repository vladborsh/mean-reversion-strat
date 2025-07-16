import backtrader as bt
import pandas as pd
from .strategy import MeanReversionStrategy

class PortfolioValueObserver(bt.Observer):
    """Observer to track actual portfolio value over time (not leveraged virtual cash)"""
    lines = ('value',)

    def next(self):
        # Use actual cash if it's a leveraged broker, otherwise use regular getvalue()
        broker = self._owner.broker
        if hasattr(broker, 'get_actual_cash'):
            # For leveraged broker, track actual cash + unrealized P&L
            actual_cash = broker.get_actual_cash()
            # Get unrealized P&L from open positions
            unrealized_pnl = 0.0
            for data in self._owner.datas:
                position = broker.getposition(data)
                if position.size != 0:
                    current_price = data.close[0]
                    unrealized_pnl += position.size * (current_price - position.price)
            self.lines.value[0] = actual_cash + unrealized_pnl
        else:
            self.lines.value[0] = broker.getvalue()

class LeveragedBroker(bt.brokers.BackBroker):
    """
    Custom broker that supports leveraged trading for forex/CFD instruments.
    This broker allows positions larger than account balance using leverage.
    """
    
    def __init__(self, leverage=100.0, actual_cash=100000.0, **kwargs):
        super().__init__(**kwargs)
        self.leverage = leverage
        self.actual_cash = actual_cash  # Real account balance for risk management
        self.initial_actual_cash = actual_cash
        self.completed_trades_pnl = 0.0  # Track only completed trades P&L
        
    def setcash(self, cash):
        # Store the actual cash for risk management
        self.actual_cash = cash
        self.initial_actual_cash = cash
        # Set virtual cash for trading (leveraged amount)
        super().setcash(cash * self.leverage)
    
    def get_actual_cash(self):
        """Get the real account balance (not leveraged)"""
        # Return actual cash which is only updated when trades are completed
        return self.actual_cash
    
    def add_trade_pnl(self, pnl):
        """Called when a trade is completed to update actual cash balance"""
        self.completed_trades_pnl += pnl
        self.actual_cash = self.initial_actual_cash + self.completed_trades_pnl

    def get_available_margin(self):
        """Calculate available margin for new positions"""
        return self.get_actual_cash() * self.leverage
    
    def submit(self, order, check=True, **kwargs):
        """Override submit to allow leveraged trading"""
        # Get position details for logging
        size = abs(order.size)
        price = order.price or order.data.close[0]
        position_value = size * price
        required_margin = position_value
        
        print(f"LEVERAGED ORDER: Size={size:,}, Price={price:.4f}, Position Value=${position_value:,.2f}")
        print(f"Required Margin: ${required_margin:,.2f}, Actual Cash: ${self.get_actual_cash():,.2f}, Leverage: 1:{int(self.leverage)}")
        
        # For leveraged trading, bypass the cash check since we have virtual cash set high enough
        return super().submit(order, check=False, **kwargs)

def run_backtest(data, strategy_class, params, leverage=100.0):
    cerebro = bt.Cerebro()
    
    # Ensure the data has the correct format for backtrader
    if not isinstance(data.index, pd.DatetimeIndex):
        data.index = pd.to_datetime(data.index)
    
    # Make sure all columns are properly named and typed
    data = data.copy()
    required_columns = ['open', 'high', 'low', 'close', 'volume']
    for col in required_columns:
        if col not in data.columns:
            if col == 'volume':
                # If volume is missing, add a dummy volume column
                data['volume'] = 1000000
            else:
                raise ValueError(f"Required column '{col}' not found in data")
    
    # Ensure all data is numeric
    for col in required_columns:
        data[col] = pd.to_numeric(data[col], errors='coerce')
    
    # Drop any rows with NaN values
    data = data.dropna()
    
    print(f"Backtest data shape: {data.shape}")
    
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
    cerebro.addstrategy(strategy_class, **params)
    
    # Set up SINGLE leveraged broker instance
    actual_cash = 100000  # Real account balance
    leveraged_broker = LeveragedBroker(leverage=leverage, actual_cash=actual_cash)
    cerebro.setbroker(leveraged_broker)
    
    # Set the cash - this will automatically set leveraged amount internally
    cerebro.broker.setcash(actual_cash)
    cerebro.broker.setcommission(commission=0.001)
    
    # Configure broker for leveraged trading (forex/CFD style)
    print(f"Configured broker with 1:{int(leverage)} leverage")
    print(f"Actual account balance: ${actual_cash:,.0f}")
    print(f"Virtual buying power: ${actual_cash * leverage:,.0f}")
    
    # Add analyzers and observers
    cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name='trades')
    cerebro.addanalyzer(bt.analyzers.Returns, _name='returns')
    cerebro.addobserver(PortfolioValueObserver)
    
    try:
        results = cerebro.run()
        strat = results[0]
        
        # Get portfolio value history from the observer
        equity_curve = []
        if hasattr(strat, 'observers') and hasattr(strat.observers, 'portfoliovalue'):
            equity_curve = list(strat.observers.portfoliovalue.lines.value.array)
        elif hasattr(strat, '_observers'):
            for obs in strat._observers:
                if hasattr(obs, 'lines') and hasattr(obs.lines, 'value'):
                    equity_curve = list(obs.lines.value.array)
                    break
        
        # Fallback if observer data is not available
        if not equity_curve:
            initial_value = actual_cash  # Use actual cash, not leveraged amount
            # Calculate final value using actual cash + unrealized P&L
            broker = cerebro.broker
            if hasattr(broker, 'get_actual_cash'):
                final_actual_cash = broker.get_actual_cash()
                # Calculate unrealized P&L from open positions
                unrealized_pnl = 0.0
                for data_feed in cerebro.datas:
                    position = broker.getposition(data_feed)
                    if position.size != 0:
                        current_price = data_feed.close[0]
                        unrealized_pnl += position.size * (current_price - position.price)
                final_value = final_actual_cash + unrealized_pnl
            else:
                final_value = broker.getvalue()
            equity_curve = [initial_value, final_value]
            print(f"Using fallback equity curve: [{initial_value}, {final_value}]")
        
        trade_log = getattr(strat, 'trade_log', [])
        order_log = strat.get_order_log() if hasattr(strat, 'get_order_log') else getattr(strat, 'order_log', [])
        
        # Validate that all orders have outcomes
        orders_without_outcomes = [order for order in order_log if 'trade_outcome' not in order]
        if orders_without_outcomes:
            print(f"WARNING: {len(orders_without_outcomes)} orders found without outcomes!")
            for order in orders_without_outcomes:
                print(f"  - {order['order_id']}: {order['date']} {order['time']}")
        
        # Print order summary
        if order_log:
            print(f"\n=== ORDER LOG SUMMARY ===")
            print(f"Total orders found: {len(order_log)}")
            orders_with_outcomes = len([o for o in order_log if 'trade_outcome' in o])
            print(f"Orders with outcomes: {orders_with_outcomes}/{len(order_log)}")
            for i, order in enumerate(order_log, 1):
                outcome_text = ""
                if 'trade_outcome' in order:
                    outcome = order['trade_outcome']
                    outcome_text = f" -> {outcome['type'].upper()}: {outcome.get('pnl', 0):+.4f}"
                print(f"{i}. {order['date']} {order['time']} - {order['type']} @ {order['entry_price']:.4f}{outcome_text}")
                print(f"   SL: {order['stop_loss']:.4f}, TP: {order['take_profit']:.4f}")
                print(f"   Reason: {order['reason']}")
                print()
        else:
            print("No orders found during backtest period.")
        
        return equity_curve, trade_log, order_log
    except Exception as e:
        print(f"Backtest error: {e}")
        import traceback
        traceback.print_exc()
        # Return empty results to allow the script to continue
        return [100000], [], []

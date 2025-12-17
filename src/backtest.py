import backtrader as bt
import pandas as pd
from .strategy import MeanReversionStrategy

# Removed PortfolioValueObserver as it doesn't work reliably
# Portfolio value tracking is now handled directly in the strategy

class LeveragedBroker(bt.brokers.BackBroker):
    """
    Custom broker that supports leveraged trading for forex/CFD instruments.
    This broker allows positions larger than account balance using leverage.
    """
    
    def __init__(self, leverage=100.0, actual_cash=100000.0, verbose=True, **kwargs):
        super().__init__(**kwargs)
        self.leverage = leverage
        self.actual_cash = actual_cash  # Real account balance for risk management
        self.initial_actual_cash = actual_cash
        self.completed_trades_pnl = 0.0  # Track only completed trades P&L
        self.verbose = verbose  # Control console output
        
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

        # For leveraged trading, bypass the cash check since we have virtual cash set high enough
        return super().submit(order, check=False, **kwargs)

def run_backtest(data, strategy_class, params, leverage=100.0, verbose=True):
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
    
    if verbose:
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
    leveraged_broker = LeveragedBroker(leverage=leverage, actual_cash=actual_cash, verbose=verbose)
    cerebro.setbroker(leveraged_broker)
    
    # Set the cash - this will automatically set leveraged amount internally
    cerebro.broker.setcash(actual_cash)
    cerebro.broker.setcommission(commission=0.001)
    
    # Configure broker for leveraged trading (forex/CFD style)
    if verbose:
        print(f"Actual account balance: ${actual_cash:,.0f}")
    
    # Add analyzers (no portfolio observer since it doesn't work reliably)
    cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name='trades')
    cerebro.addanalyzer(bt.analyzers.Returns, _name='returns')
    
    try:
        results = cerebro.run()
        strat = results[0]
        
        # Get portfolio value history directly from the strategy
        equity_curve = getattr(strat, 'equity_curve', [])
        equity_dates = getattr(strat, 'equity_dates', [])
        
        # If no equity curve was tracked by strategy, calculate it from order history
        if not equity_curve:
            if verbose:
                print("No equity curve found in strategy, calculating from broker state...")
            # Calculate portfolio value based on actual cash + unrealized P&L
            broker = cerebro.broker
            if hasattr(broker, 'get_actual_cash'):
                actual_cash = broker.get_actual_cash()
                # Calculate unrealized P&L from open positions
                unrealized_pnl = 0.0
                for data_feed in cerebro.datas:
                    position = broker.getposition(data_feed)
                    if position.size != 0:
                        current_price = data_feed.close[0]
                        unrealized_pnl += position.size * (current_price - position.price)
                final_value = actual_cash + unrealized_pnl
                equity_curve = [actual_cash, final_value]  # Start with initial, end with final
                equity_dates = []  # No dates available in fallback mode
                if verbose:
                    print(f"Calculated equity curve: start=${actual_cash:.2f}, end=${final_value:.2f}")
            else:
                # Fallback for standard broker
                initial_value = actual_cash
                final_value = broker.getvalue()
                equity_curve = [initial_value, final_value]
                equity_dates = []  # No dates available in fallback mode
                if verbose:
                    print(f"Using standard broker fallback: start=${initial_value:.2f}, end=${final_value:.2f}")
        else:
            if verbose:
                print(f"Found equity curve with {len(equity_curve)} data points and {len(equity_dates)} dates")
        
        trade_log = getattr(strat, 'trade_log', [])
        order_log = strat.get_order_log() if hasattr(strat, 'get_order_log') else getattr(strat, 'order_log', [])
        
        # Validate that all orders have outcomes
        orders_without_outcomes = [order for order in order_log if 'trade_outcome' not in order]
        if orders_without_outcomes and verbose:
            print(f"WARNING: {len(orders_without_outcomes)} orders found without outcomes!")
            for order in orders_without_outcomes:
                print(f"  - {order['order_id']}: {order['date']} {order['time']}")
        
        # Print order summary only in verbose mode
        if order_log and verbose:
            print(f"\n=== ORDER LOG SUMMARY ===")
            print(f"Total orders found: {len(order_log)}")
            for i, order in enumerate(order_log, 1):
                outcome_text = ""
                if 'trade_outcome' in order:
                    outcome = order['trade_outcome']
                    outcome_text = f" -> {outcome['type'].upper()}: {outcome.get('pnl', 0):+.4f}"
                print(f"{i}. {order['date']} {order['time']} - {order['type']} @ {order['entry_price']:.4f}{outcome_text}")
        elif not order_log and verbose:
            print("No orders found during backtest period.")
        
        return equity_curve, equity_dates, trade_log, order_log
    except Exception as e:
        print(f"Backtest error: {e}")
        import traceback
        traceback.print_exc()
        # Return empty results to allow the script to continue
        return [100000], [], [], []

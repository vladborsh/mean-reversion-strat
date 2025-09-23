# MeanReversionStrategy Documentation

## Overview

The `MeanReversionStrategy` is a backtrader-based trading strategy that implements a mean reversion approach using technical indicators with comprehensive risk management and order lifecycle tracking.

## Core Strategy Logic

### Entry Signals

**Long Position (Buy)**
- Price breaks below both Bollinger Bands lower band AND VWAP lower band
- Optional reversal confirmation: previous candle below lower bands, current candle showing upward movement
- Risk management validation passes

**Short Position (Sell)**
- Price breaks above both Bollinger Bands upper band AND VWAP upper band
- Optional reversal confirmation: previous candle above upper bands, current candle showing downward movement
- Risk management validation passes

### Exit Signals

**Stop Loss**: ATR-based stop loss (configurable multiplier)
**Take Profit**: Risk/reward ratio based (configurable ratio)
**Time-based Exit**: Force close positions after configurable time limit
**Manual Close**: Force close at backtest end

### Exact P&L Calculation (v2.1)

The strategy implements **exact P&L calculation** to eliminate slippage and ensure precise risk management:

- **Stop Loss exits**: P&L calculated using exact stop loss price, not market price
- **Take Profit exits**: P&L calculated using exact take profit price, not market price
- **Lifetime/Forced exits**: P&L calculated using actual market price (expected behavior)

This ensures that:
- Stop losses result in exactly the calculated risk amount (e.g., -1000 for 1% risk on 100k account)
- Take profits result in exactly the calculated reward amount (e.g., +2500 for 2.5 R:R ratio)
- No slippage from market price fluctuations affects risk management calculations

**Implementation Details:**
- `_record_trade_outcome()` method records exact SL/TP prices as exit prices
- `notify_trade()` method calculates P&L using recorded exact exit prices
- Market price slippage is eliminated for risk-managed exits

## Technical Indicators

| Indicator | Purpose | Configuration | Implementation |
|-----------|---------|---------------|----------------|
| Bollinger Bands | Volatility bands for entry signals | `bb_window`, `bb_std` periods | Simple Moving Average ± (Std Dev × multiplier) |
| VWAP Approximation | Volume-weighted average price with bands | `vwap_window`, `vwap_std` periods | Weighted Moving Average ± (Std Dev × multiplier) |
| ATR | Average True Range for stop loss calculation | `atr_period` | Custom ATRIndicator implementation |

**Note**: The strategy uses WeightedMovingAverage as a VWAP approximation rather than true VWAP calculation.

## Risk Management Features

### Position Sizing
- Risk-based position sizing using ATR stop loss
- Configurable risk percentage per trade
- Account value protection

### Stop Loss & Take Profit
- ATR-based dynamic stop losses
- Fixed risk/reward ratio take profits
- Automatic position closure on risk limits

### Order Lifecycle Management
- Time-based order cancellation (configurable by timeframe)
- Position lifetime limits with forced closure
- Comprehensive order tracking and logging

## Key Parameters

```python
# Technical Indicators
bb_window          # Bollinger Bands period (default: 20)
bb_std             # Bollinger Bands standard deviation multiplier (default: 2.0)
vwap_window        # VWAP approximation calculation period (default: 20)
vwap_std           # VWAP bands standard deviation multiplier (default: 2.0)
vwap_anchor        # VWAP anchor period (default: 'day') - currently not implemented
atr_period         # ATR calculation period (default: 14)

# Risk Management (accessed via risk_manager)
risk_per_position_pct     # Risk percentage per trade (default: 1.0%)
stop_loss_atr_multiplier  # ATR multiplier for stop loss (default: 1.2)
risk_reward_ratio         # Risk to reward ratio (default: 2.5)
leverage                  # Available leverage (default: 100.0)

# Strategy Behavior
min_volume               # Minimum volume threshold (default: 0)
max_positions            # Maximum concurrent positions (default: 1)
timeframe                # Trading timeframe - affects order lifetime (default: '15m')
order_lifetime_minutes   # Maximum order/position lifetime by timeframe

# Order Lifetime by Timeframe (minutes)
'5m': 360     # 6 hours for 5-minute timeframe
'15m': 720    # 12 hours for 15-minute timeframe
'1h': 2880    # 2 days for 1-hour timeframe
'default': 720 # Default fallback
```

## Order Lifecycle Tracking

### Order States
1. **Created**: Order placed with risk management parameters
2. **Filled**: Order executed, position tracking begins
3. **Closed**: Position closed via stop loss, take profit, or time limit
4. **Cancelled**: Order cancelled due to time limits or other factors

### Comprehensive Logging
- All order details with risk metrics
- Trade outcomes with P&L tracking
- Deposit changes before/after trades
- Execution timestamps and reasons

## Key Methods

### Core Strategy Methods
- `__init__()`: Initialize indicators and risk management
- `next()`: Main strategy logic executed on each bar
- `notify_order()`: Handle order status changes
- `notify_trade()`: Handle trade completion
- `stop()`: Cleanup and force close remaining positions

### Utility Methods
- `get_order_log()`: Retrieve complete order history
- `print_order_summary()`: Print detailed order summary  
- `get_account_value_for_risk_management()`: Get correct account value for risk calculations
- `_record_trade_outcome()`: Internal outcome tracking

## Data Structures

### Order Log Entry
```python
{
    'order_id': str,           # Unique order identifier
    'date': str,               # Order date
    'time': str,               # Order time
    'type': str,               # 'BUY' or 'SELL'
    'entry_price': float,      # Entry price
    'stop_loss': float,        # Stop loss price
    'take_profit': float,      # Take profit price
    'position_size': float,    # Position size
    'atr_value': float,        # ATR at order time
    'risk_amount': float,      # Risk amount in currency
    'reward_amount': float,    # Potential reward amount
    'risk_reward_ratio': float, # R:R ratio
    'account_risk_pct': float, # Account risk percentage
    'deposit_before_trade': float, # Account value before trade
    'reason': str,             # Entry reason
    'trade_outcome': {         # Added when trade closes
        'type': str,           # Outcome type: 'stop_loss', 'take_profit', 'lifetime_expired', 'backtest_end'
        'exit_price': float,   # Exit price (exact SL/TP price for risk-managed exits)
        'exit_date': str,      # Exit date
        'exit_time': str,      # Exit time
        'pnl': float,          # Profit/Loss (calculated using exact exit prices)
        'deposit_before': float, # Deposit before trade
        'deposit_after': float,  # Deposit after trade
        'deposit_change': float  # Net deposit change
    }
}
```

## Usage Example

```python
from src.strategy import MeanReversionStrategy
from src.strategy_config import DEFAULT_CONFIG, AggressiveConfig, ConservativeConfig
import backtrader as bt

# Create Cerebro instance
cerebro = bt.Cerebro()

# Option 1: Use default configuration
cerebro.addstrategy(MeanReversionStrategy, timeframe='15m')

# Option 2: Override specific parameters
cerebro.addstrategy(MeanReversionStrategy,
                   bb_window=25,
                   bb_std=2.5,
                   vwap_window=25,
                   timeframe='1h')

# Option 3: Use alternative configuration
# (Note: Requires modifying strategy to use different config)
cerebro.addstrategy(MeanReversionStrategy, timeframe='5m')

# Add data and run
cerebro.adddata(data_feed)
results = cerebro.run()

# Get strategy instance for analysis
strategy = results[0]
strategy.print_order_summary()
order_log = strategy.get_order_log()
```

## Integration Points

- **Risk Management**: Integrates with `RiskManager` class from `src.risk_management`
- **Configuration**: Uses `DEFAULT_CONFIG` from `src.strategy_config` 
- **Indicators**: Uses custom `ATRIndicator` and backtrader built-in indicators
- **Visualization**: Order log compatible with visualization tools in `src.order_visualization`
- **Leverage Support**: Compatible with leveraged brokers via `get_account_value_for_risk_management()`

## Configuration Classes

The strategy supports multiple configuration presets:

- **`StrategyConfig`** (Default): Balanced risk/reward settings
- **`AggressiveConfig`**: Higher risk (2%), tighter stops (1.0x ATR), higher rewards (3.0x)
- **`ConservativeConfig`**: Lower risk (0.5%), wider stops (2.0x ATR), moderate rewards (2.0x)

## Important Implementation Notes

1. **VWAP Implementation**: Currently uses `WeightedMovingAverage` as VWAP approximation, not true VWAP
2. **Market Orders**: Strategy uses immediate market order execution rather than limit orders
3. **Order Lifetime**: Positions are force-closed after time limits to prevent indefinite exposure
4. **Risk Management**: Position sizing based on account value and ATR-based stop losses
5. **Leverage Handling**: Proper account value calculation for leveraged brokers
6. **Exact P&L Calculation**: Stop loss and take profit exits use exact SL/TP prices for P&L calculation, eliminating market price slippage and ensuring precise risk management (1% risk = exactly 1% loss, 2.5 R:R = exactly 2.5x gain)

## Best Practices

1. **Risk Validation**: Always validate risk management settings before live trading
2. **Order Lifetime Monitoring**: Monitor order lifetime settings based on market conditions and volatility
3. **Performance Analysis**: Regular review of order logs for strategy performance analysis
4. **Cleanup Procedures**: Ensure proper cleanup in `stop()` method for accurate backtesting
5. **Configuration Testing**: Test different configuration presets on historical data
6. **Leverage Awareness**: Understand leverage implications when using leveraged brokers
7. **VWAP Limitation**: Be aware that current implementation uses WMA approximation, not true VWAP
8. **Market Hours**: Consider market hours when setting order lifetimes for different timeframes
9. **P&L Verification**: With exact P&L calculation, verify that stop losses result in precise risk amounts and take profits result in precise reward amounts (no slippage)

## Troubleshooting

**Common Issues:**
- Orders without outcomes: Ensure `stop()` method is called properly
- Incorrect position sizing: Verify `get_account_value_for_risk_management()` returns correct value
- Missing trade data: Check that ATR indicator has sufficient data before strategy starts
- Time-based exits not working: Verify `order_entry_time` is set correctly on order execution

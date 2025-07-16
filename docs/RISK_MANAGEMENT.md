# Risk Management System

This document describes the new risk management system that has been separated from the main strategy logic.

## Overview

The risk management system provides:
- **ATR-based stop loss**: Stop loss = 1.2 × ATR (configurable)
- **Risk-reward ratio**: Take profit = 2.5 × risk (configurable)
- **Position sizing**: Risk 1% of account per position (configurable)
- **Comprehensive risk metrics and validation**

## Files

### `src/risk_management.py`
Contains the core risk management functionality:
- `RiskManager`: Main class for risk calculations
- `ATRIndicator`: Backtrader ATR indicator implementation
- `create_risk_manager()`: Factory function for easy setup

### `src/strategy_config.py`
Contains all configurable parameters:
- `StrategyConfig`: Default configuration
- `AggressiveConfig`: Higher risk, tighter stops
- `ConservativeConfig`: Lower risk, wider stops

## Configuration

### Default Configuration
```python
RISK_MANAGEMENT = {
    'risk_per_position_pct': 1.0,      # Risk 1% of account per position
    'stop_loss_atr_multiplier': 1.2,   # Stop loss = 1.2 * ATR
    'risk_reward_ratio': 2.5,          # Take profit = 2.5 * risk
    'atr_period': 14                   # ATR calculation period
}
```

### How to Use Different Configurations

```python
from src.strategy_config import DEFAULT_CONFIG, AggressiveConfig, ConservativeConfig

# Use default configuration
equity_curve, trade_log, metrics = run_strategy(df, DEFAULT_CONFIG)

# Use aggressive configuration (higher risk)
equity_curve, trade_log, metrics = run_strategy(df, AggressiveConfig)

# Use conservative configuration (lower risk)
equity_curve, trade_log, metrics = run_strategy(df, ConservativeConfig)

# Create custom configuration
custom_config = StrategyConfig()
custom_config.update_config(
    risk_management={
        'risk_per_position_pct': 1.5,
        'stop_loss_atr_multiplier': 1.0,
        'risk_reward_ratio': 3.0
    }
)
```

## Risk Management Features

### 1. ATR-Based Stop Loss
- Calculates stop loss based on market volatility
- Default: 1.2 × ATR below entry for long positions
- Automatically adjusts to market conditions

### 2. Risk-Reward Ratio
- Default: 2.5:1 risk-reward ratio
- Take profit = entry + (2.5 × stop loss distance)
- Ensures profitable trades outweigh losses

### 3. Position Sizing
- Calculates position size to risk exactly 1% of account
- Position size = (Account × Risk%) / (Entry - Stop Loss)
- Prevents overexposure on any single trade

### 4. Risk Validation
- Validates trades before execution
- Ensures minimum risk-reward ratio
- Prevents invalid trade setups

## Example Risk Calculation

For a $100,000 account with EUR/USD trade:
- Entry Price: 1.0500
- ATR: 0.0020
- Stop Loss: 1.0500 - (1.2 × 0.0020) = 1.0476
- Take Profit: 1.0500 + (2.5 × 0.0024) = 1.0560
- Risk per unit: 0.0024
- Position Size: $1,000 / 0.0024 = 416,666 units
- Total Risk: $1,000 (1% of account)
- Potential Profit: $2,500 (2.5% of account)

## Order Log Enhancement

The new system provides detailed order logging:
```python
{
    'date': '2024-07-14',
    'time': '10:30:00',
    'type': 'BUY',
    'entry_price': 1.0500,
    'stop_loss': 1.0476,
    'take_profit': 1.0560,
    'position_size': 416666,
    'atr_value': 0.0020,
    'risk_amount': 0.0024,
    'reward_amount': 0.0060,
    'risk_reward_ratio': 2.5,
    'account_risk_pct': 1.0,
    'reason': 'Break below BB/VWAP lower bands with reversal'
}
```

## Configuration Comparison

| Configuration | Risk per Trade | Stop Loss | R:R Ratio | ATR Period |
|---------------|----------------|-----------|-----------|------------|
| Default       | 1.0%          | 1.2×ATR   | 2.5:1     | 14         |
| Aggressive    | 2.0%          | 1.0×ATR   | 3.0:1     | 10         |
| Conservative  | 0.5%          | 2.0×ATR   | 2.0:1     | 20         |

## Benefits

1. **Consistent Risk Management**: Every trade risks exactly the same percentage
2. **Market-Adaptive**: ATR adjusts stop loss to current volatility
3. **Profitable Expectancy**: 2.5:1 R:R means only 29% win rate needed to break even
4. **Configurable**: Easy to test different risk parameters
5. **Comprehensive Logging**: Detailed risk metrics for each trade
6. **Validation**: Prevents bad trades from being executed

## Usage in Main Strategy

The updated strategy automatically uses the risk management system:

```python
# Risk manager is initialized in strategy __init__
self.risk_manager = create_risk_manager(DEFAULT_CONFIG.get_risk_config())

# ATR indicator for stop loss calculation
self.atr = ATRIndicator(self.datas[0], period=self.p.atr_period)

# In next() method, calculate risk levels
stop_loss = self.risk_manager.calculate_atr_stop_loss(entry_price, self.atr[0], 'long')
take_profit = self.risk_manager.calculate_take_profit(entry_price, stop_loss, 'long')
position_size = self.risk_manager.calculate_position_size(account_value, entry_price, stop_loss)
```

This system ensures consistent, professional-grade risk management across all trades.

import numpy as np
import pandas as pd

def calculate_metrics(trade_log, equity_curve):
    trades = pd.DataFrame(trade_log)
    
    # Handle empty trades
    if trades.empty:
        return {
            'win_rate': 0,
            'total_return': 0,
            'sharpe_ratio': 0,
            'max_drawdown': 0,
            'avg_return_per_trade': 0,
            'volatility': 0,
            'final_pnl': 0,
            'total_trades': 0
        }
    
    # Calculate basic metrics
    exit_trades = trades[trades['type'] == 'exit']
    wins = exit_trades['pnl'] > 0 if not exit_trades.empty else pd.Series(dtype=bool)
    win_rate = wins.sum() / len(wins) if len(wins) > 0 else 0
    
    # Calculate final PnL and total trades
    final_pnl = equity_curve[-1] - equity_curve[0] if len(equity_curve) > 1 else 0
    total_trades = len(exit_trades)
    
    # Calculate returns and performance metrics
    total_return = (equity_curve[-1] / equity_curve[0]) - 1 if len(equity_curve) > 1 and equity_curve[0] > 0 else 0
    returns = pd.Series(equity_curve).pct_change().dropna()
    sharpe = returns.mean() / returns.std() * np.sqrt(252) if returns.std() > 0 and len(returns) > 0 else 0
    
    # Calculate drawdown
    running_max = np.maximum.accumulate(equity_curve)
    drawdown = (equity_curve - running_max) / running_max
    max_drawdown = abs(drawdown.min()) * 100  # Convert to percentage
    
    # Other metrics
    avg_return = exit_trades['pnl'].mean() if not exit_trades.empty else 0
    volatility = returns.std() * np.sqrt(252) if len(returns) > 0 else 0
    
    return {
        'win_rate': win_rate,
        'total_return': total_return,
        'sharpe_ratio': sharpe,
        'max_drawdown': max_drawdown,
        'avg_return_per_trade': avg_return,
        'volatility': volatility,
        'final_pnl': final_pnl,
        'total_trades': total_trades
    }

import numpy as np
import pandas as pd

def calculate_metrics(trade_log, equity_curve):
    trades = pd.DataFrame(trade_log)
    if trades.empty:
        return {}
    wins = trades[trades['type'] == 'exit']['pnl'] > 0
    win_rate = wins.sum() / len(wins) if len(wins) > 0 else 0
    total_return = (equity_curve[-1] / equity_curve[0]) - 1 if len(equity_curve) > 1 else 0
    returns = pd.Series(equity_curve).pct_change().dropna()
    sharpe = returns.mean() / returns.std() * np.sqrt(252) if returns.std() > 0 else 0
    running_max = np.maximum.accumulate(equity_curve)
    drawdown = (equity_curve - running_max) / running_max
    max_drawdown = drawdown.min()
    avg_return = trades[trades['type'] == 'exit']['pnl'].mean() if not trades.empty else 0
    volatility = returns.std() * np.sqrt(252)
    return {
        'win_rate': win_rate,
        'total_return': total_return,
        'sharpe_ratio': sharpe,
        'max_drawdown': max_drawdown,
        'avg_return_per_trade': avg_return,
        'volatility': volatility
    }

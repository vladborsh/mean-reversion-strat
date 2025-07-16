import itertools
import numpy as np
from .backtest import run_backtest
from .metrics import calculate_metrics

def grid_search(param_grid, data, strategy_class):
    keys, values = zip(*param_grid.items())
    best_score = -np.inf
    best_params = None
    best_metrics = None
    for combo in itertools.product(*values):
        params = dict(zip(keys, combo))
        equity_curve, trade_log, order_log = run_backtest(data, strategy_class, params)
        metrics = calculate_metrics(trade_log, equity_curve)
        score = metrics.get('sharpe_ratio', 0)
        if score > best_score:
            best_score = score
            best_params = params
            best_metrics = metrics
    return best_params, best_metrics

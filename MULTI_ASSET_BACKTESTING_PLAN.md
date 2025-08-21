# Multi-Asset Backtesting Implementation Plan

## Overview
Transform the current single-asset backtesting system into a comprehensive multi-asset platform that runs simultaneous backtests with combined portfolio PnL and drawdown tracking.

## Current System Analysis

### Strengths of Existing Implementation
The codebase has a solid foundation for multi-asset expansion:

1. **Individual Asset Configurations**: `assets_config_highperf.json` contains optimized parameters for multiple assets
2. **Leveraged Broker Implementation**: `LeveragedBroker` in `src/backtest.py` supports forex/CFD trading
3. **Exact P&L Calculation**: Strategy uses precise SL/TP exit prices for risk management
4. **Comprehensive Metrics**: `src/metrics.py` calculates detailed performance statistics
5. **Asset-Specific Optimization**: Batch optimization results available for 15+ assets

### Current Limitations
- **Sequential Processing**: Each asset backtested individually via `main.py`
- **No Portfolio Correlation**: Assets treated independently
- **Individual Risk Management**: No portfolio-level position sizing
- **Separate P&L Tracking**: No combined portfolio metrics

### Existing Portfolio Data
From `results/portfolio_summary.txt`:
- **15 optimized assets** with proven performance
- **Total Portfolio PnL**: $4,856,710 (if combined theoretically)
- **Top performers**: SILVERX ($1.45M), ETHUSDX ($1.15M), BTCUSDX ($644K)
- **Average metrics**: 42.1% win rate, 0.21 Sharpe, 19.3% max drawdown

## Multi-Asset Implementation Strategy

### Phase 1: Portfolio Backtest Engine (Core)

#### 1.1 Create Portfolio Backtest Runner (`src/portfolio_backtest.py`)
```python
class PortfolioBacktester:
    """Orchestrates multiple simultaneous asset backtests"""
    
    def __init__(self, asset_configs, portfolio_config):
        self.asset_configs = asset_configs  # From assets_config_*.json
        self.portfolio_config = portfolio_config
        self.asset_brokers = {}  # Individual LeveragedBroker per asset
        self.portfolio_equity = []
        
    def run_portfolio_backtest(self):
        """Run synchronized backtests across all assets"""
        # Create individual Cerebro instances per asset
        # Synchronize timesteps across all assets
        # Calculate portfolio-level metrics in real-time
        # Track combined equity curve and drawdown
```

**Key Features**:
- **Synchronized Execution**: All asset strategies run on same timestamps
- **Real-time Portfolio Metrics**: Combined equity curve during backtest
- **Asset Allocation Management**: Position sizing across portfolio
- **Correlation-aware Risk**: Consider asset relationships

#### 1.2 Multi-Asset Strategy Orchestrator (`src/portfolio_strategy.py`)
```python
class PortfolioMeanReversionStrategy:
    """Coordinates individual MeanReversionStrategy instances"""
    
    def __init__(self, asset_strategies, portfolio_risk_manager):
        self.asset_strategies = asset_strategies
        self.portfolio_risk_manager = portfolio_risk_manager
        self.portfolio_positions = {}
        
    def next(self):
        """Portfolio-level strategy logic"""
        # Check portfolio-level risk limits
        # Coordinate cross-asset position sizing
        # Apply portfolio-level filters
        # Track combined performance
```

**Benefits**:
- **Cross-asset Signal Filtering**: Prevent over-concentration
- **Portfolio Position Limits**: Dynamic exposure management
- **Risk Allocation**: Intelligent position sizing across assets

#### 1.3 Enhanced Metrics System (`src/portfolio_metrics.py`)
Extend existing `src/metrics.py` with portfolio-specific calculations:

```python
def calculate_portfolio_metrics(asset_equity_curves, asset_weights):
    """Calculate portfolio-level performance metrics"""
    
    # Combine individual equity curves into portfolio curve
    portfolio_equity = sum(curve * weight for curve, weight in zip(asset_equity_curves, asset_weights))
    
    # Portfolio-level metrics
    portfolio_sharpe = calculate_portfolio_sharpe(portfolio_equity)
    portfolio_drawdown = calculate_portfolio_drawdown(portfolio_equity)
    asset_correlations = calculate_asset_correlations(asset_equity_curves)
    
    return {
        'portfolio_return': portfolio_equity[-1] / portfolio_equity[0] - 1,
        'portfolio_sharpe': portfolio_sharpe,
        'portfolio_max_drawdown': portfolio_drawdown,
        'diversification_ratio': calculate_diversification_ratio(asset_correlations),
        'asset_contributions': calculate_asset_contributions(asset_equity_curves, asset_weights)
    }
```

### Phase 2: Configuration & Asset Management

#### 2.1 Portfolio Configuration System (`src/portfolio_config.py`)
```python
class PortfolioConfig:
    """Portfolio-level configuration and asset allocation"""
    
    ALLOCATION_MODELS = {
        'equal_weight': lambda n_assets: [1/n_assets] * n_assets,
        'risk_parity': lambda asset_vols: calculate_risk_parity_weights(asset_vols),
        'performance_weighted': lambda asset_sharpes: calculate_performance_weights(asset_sharpes)
    }
    
    PORTFOLIO_RISK = {
        'max_portfolio_drawdown': 25.0,  # Stop trading if portfolio DD > 25%
        'max_asset_correlation': 0.8,    # Limit highly correlated assets
        'max_single_asset_weight': 0.3,  # No asset > 30% of portfolio
        'rebalance_frequency': 'monthly' # How often to adjust weights
    }
```

#### 2.2 Asset Universe Definition
Based on existing optimization results, create tiered asset universes:

**Tier 1: High Performance Assets**
- SILVERX_5m: $1.45M PnL, 34.1% WR, 25.7% DD
- ETHUSDX_5m: $1.15M PnL, 28.4% WR, 37.4% DD
- BTCUSDX_5m: $644K PnL, 29.8% WR, 27.1% DD
- GOLDX_5m: $473K PnL, 31.3% WR, 23.5% DD

**Tier 2: Balanced Assets**
- EURGBPX_5m: $318K PnL, 51.9% WR, 10.0% DD
- NZDUSDX_5m: $95K PnL, 61.9% WR, 8.4% DD
- EURCHFX_5m: $70K PnL, 56.6% WR, 8.9% DD

### Phase 3: Portfolio Risk Management

#### 3.1 Portfolio Risk Manager (`src/portfolio_risk_management.py`)
Extend existing `RiskManager` class for portfolio-level controls:

```python
class PortfolioRiskManager(RiskManager):
    """Portfolio-level risk management and position sizing"""
    
    def __init__(self, portfolio_config, asset_configs):
        self.portfolio_config = portfolio_config
        self.asset_configs = asset_configs
        self.portfolio_equity_history = []
        self.current_portfolio_drawdown = 0.0
        
    def calculate_portfolio_position_size(self, asset_signal, current_portfolio_value):
        """Calculate position size considering portfolio context"""
        
        # Get base position size from individual asset risk manager
        base_size = super().calculate_position_size(...)
        
        # Apply portfolio-level adjustments
        portfolio_risk_factor = self.get_portfolio_risk_factor()
        correlation_factor = self.get_correlation_adjustment(asset_signal.symbol)
        drawdown_factor = self.get_drawdown_adjustment()
        
        # Final position size
        portfolio_adjusted_size = base_size * portfolio_risk_factor * correlation_factor * drawdown_factor
        
        return portfolio_adjusted_size
        
    def check_portfolio_limits(self):
        """Check if portfolio risk limits are breached"""
        if self.current_portfolio_drawdown > self.portfolio_config['max_portfolio_drawdown']:
            return False  # Stop all trading
        return True
```

#### 3.2 Real-time Portfolio Monitoring
```python
class PortfolioMonitor:
    """Real-time portfolio metrics during backtest"""
    
    def update_portfolio_metrics(self, timestamp, asset_values):
        """Update portfolio metrics at each timestamp"""
        
        # Calculate current portfolio value
        total_portfolio_value = sum(asset_values.values())
        
        # Update equity curve
        self.portfolio_equity_curve.append(total_portfolio_value)
        
        # Calculate current drawdown
        current_dd = self.calculate_current_drawdown()
        
        # Update maximum drawdown
        self.max_drawdown = max(self.max_drawdown, current_dd)
        
        # Check risk limits
        if not self.portfolio_risk_manager.check_portfolio_limits():
            self.stop_all_trading()
```

### Phase 4: Analysis & Visualization

#### 4.1 Portfolio Analysis Tools (`src/portfolio_analysis.py`)
```python
def analyze_portfolio_performance(portfolio_results):
    """Comprehensive portfolio performance analysis"""
    
    analysis = {
        'performance_attribution': calculate_asset_contributions(portfolio_results),
        'risk_attribution': calculate_risk_contributions(portfolio_results),
        'correlation_analysis': calculate_correlation_matrix(portfolio_results),
        'diversification_benefits': calculate_diversification_benefits(portfolio_results),
        'efficient_frontier': calculate_efficient_frontier(portfolio_results)
    }
    
    return analysis

def calculate_diversification_benefits(portfolio_results):
    """Calculate the benefit of diversification vs single assets"""
    
    # Portfolio metrics
    portfolio_return = portfolio_results['total_return']
    portfolio_volatility = portfolio_results['volatility']
    portfolio_sharpe = portfolio_results['sharpe_ratio']
    
    # Weighted average of individual assets
    avg_individual_return = np.mean([asset['return'] for asset in portfolio_results['assets']])
    avg_individual_volatility = np.mean([asset['volatility'] for asset in portfolio_results['assets']])
    avg_individual_sharpe = np.mean([asset['sharpe'] for asset in portfolio_results['assets']])
    
    return {
        'volatility_reduction': (avg_individual_volatility - portfolio_volatility) / avg_individual_volatility,
        'sharpe_improvement': (portfolio_sharpe - avg_individual_sharpe) / avg_individual_sharpe,
        'diversification_ratio': avg_individual_volatility / portfolio_volatility
    }
```

#### 4.2 Portfolio Visualization (`src/portfolio_visualization.py`)
```python
def plot_portfolio_equity_curve(portfolio_equity, asset_equities, save_path=None):
    """Plot combined portfolio equity curve vs individual assets"""
    
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(15, 10))
    
    # Portfolio equity curve
    ax1.plot(portfolio_equity, label='Portfolio', linewidth=3, color='black')
    
    # Individual asset equity curves
    for asset_name, equity in asset_equities.items():
        ax1.plot(equity, label=asset_name, alpha=0.7)
    
    ax1.set_title('Portfolio vs Individual Asset Performance')
    ax1.legend()
    
    # Portfolio drawdown
    portfolio_dd = calculate_drawdown_series(portfolio_equity)
    ax2.fill_between(range(len(portfolio_dd)), portfolio_dd, alpha=0.3, color='red')
    ax2.set_title('Portfolio Drawdown')
    ax2.set_ylabel('Drawdown %')
    
    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches='tight')

def plot_asset_correlation_heatmap(asset_returns, save_path=None):
    """Plot correlation heatmap between assets"""
    
    correlation_matrix = np.corrcoef([returns for returns in asset_returns.values()])
    
    plt.figure(figsize=(12, 10))
    sns.heatmap(correlation_matrix, 
                xticklabels=asset_returns.keys(),
                yticklabels=asset_returns.keys(),
                annot=True, cmap='coolwarm', center=0)
    plt.title('Asset Correlation Matrix')
    
    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
```

### Phase 5: Implementation Strategy

#### 5.1 Leverage Existing Optimized Configurations
```python
def load_portfolio_from_config(config_preference='balanced'):
    """Load portfolio configuration from existing optimization results"""
    
    # Load optimized configurations
    config_file = f'results/best_configs_{config_preference}.json'
    with open(config_file, 'r') as f:
        asset_configs = json.load(f)
    
    # Create portfolio configuration
    portfolio_config = {
        'assets': list(asset_configs.keys()),
        'allocation_model': 'equal_weight',  # Start simple
        'rebalance_frequency': None,  # Buy and hold initially
        'portfolio_risk': {
            'max_drawdown': 30.0,
            'max_single_asset_weight': 0.25
        }
    }
    
    return asset_configs, portfolio_config
```

#### 5.2 New Portfolio Entry Point (`portfolio_main.py`)
```python
#!/usr/bin/env python3
"""
Portfolio Backtesting Main Script

Run multi-asset mean reversion strategy with combined portfolio metrics.
"""

def main():
    parser = argparse.ArgumentParser(description='Portfolio Mean Reversion Backtesting')
    parser.add_argument('--preference', choices=['balanced', 'pnl', 'drawdown'], 
                       default='balanced', help='Asset selection preference')
    parser.add_argument('--allocation', choices=['equal_weight', 'risk_parity', 'performance_weighted'],
                       default='equal_weight', help='Portfolio allocation method')
    parser.add_argument('--max-assets', type=int, default=10, 
                       help='Maximum number of assets in portfolio')
    parser.add_argument('--timeframe', default='5m', help='Trading timeframe')
    
    args = parser.parse_args()
    
    # Load portfolio configuration
    asset_configs, portfolio_config = load_portfolio_from_config(args.preference)
    
    # Limit number of assets
    top_assets = select_top_assets(asset_configs, args.max_assets)
    
    # Run portfolio backtest
    portfolio_backtest = PortfolioBacktester(top_assets, portfolio_config)
    results = portfolio_backtest.run()
    
    # Display results
    print_portfolio_summary(results)
    generate_portfolio_visualizations(results)

if __name__ == '__main__':
    main()
```

## Expected Benefits

### Combined PnL Analysis
1. **True Portfolio Performance**: Account for timing differences and correlations
2. **Diversification Effects**: Reduced volatility through asset diversification
3. **Risk-Adjusted Returns**: Better Sharpe ratios than individual assets
4. **Smoother Equity Curves**: Less erratic portfolio performance

### Portfolio Drawdown Management
1. **Real Portfolio Drawdown**: Not just sum of individual asset drawdowns
2. **Dynamic Risk Scaling**: Reduce positions during portfolio drawdowns
3. **Correlation-Aware Risk**: Avoid over-concentration in correlated assets
4. **Circuit Breakers**: Stop trading when portfolio limits are hit

### Enhanced Analysis Capabilities
1. **Performance Attribution**: Which assets drive portfolio returns
2. **Risk Decomposition**: Sources of portfolio risk and volatility
3. **Optimal Allocation**: Find best asset weights for risk/return profile
4. **Diversification Benefits**: Quantify the value of multi-asset approach

## Implementation Timeline

### Phase 1: Core Engine (2-3 days)
- [ ] Create `PortfolioBacktester` class
- [ ] Implement synchronized asset backtesting
- [ ] Build portfolio metrics calculation
- [ ] Test with 2-3 assets

### Phase 2: Configuration (1-2 days)
- [ ] Create portfolio configuration system
- [ ] Implement asset selection logic
- [ ] Add allocation models (equal weight, risk parity)
- [ ] Integration with existing asset configs

### Phase 3: Risk Management (1-2 days)
- [ ] Extend `RiskManager` for portfolio context
- [ ] Implement portfolio-level position sizing
- [ ] Add correlation-aware risk controls
- [ ] Create portfolio monitoring system

### Phase 4: Analysis & Visualization (1-2 days)
- [ ] Build portfolio analysis tools
- [ ] Create portfolio visualization functions
- [ ] Add performance attribution analysis
- [ ] Generate comprehensive reports

### Phase 5: Integration & Testing (1 day)
- [ ] Create `portfolio_main.py` entry point
- [ ] Test with full asset universe
- [ ] Validate against individual asset results
- [ ] Documentation and examples

## Potential Portfolio Configurations

### Conservative Portfolio (Low Drawdown Focus)
**Assets**: EURGBPX (10% DD), NZDUSDX (8.4% DD), EURCHFX (8.9% DD)
**Expected**: ~15-20% combined PnL, <12% portfolio drawdown

### Balanced Portfolio (Risk-Adjusted)
**Assets**: Top 7 assets from balanced optimization
**Allocation**: Equal weight or risk parity
**Expected**: ~$1-2M combined PnL, ~18-25% portfolio drawdown

### Aggressive Portfolio (High PnL)
**Assets**: SILVERX, ETHUSDX, BTCUSDX, GOLDX
**Allocation**: Performance-weighted
**Expected**: ~$3-4M combined PnL, ~25-35% portfolio drawdown

This implementation will transform the current system into a professional-grade portfolio backtesting platform while preserving all existing functionality and leveraging the extensive optimization work already completed.
#!/usr/bin/env python3
"""
Live Scheduler Performance Verification CLI Tool

This tool analyzes the performance of the live trading strategy scheduler over a specified
time period, collecting metrics on successful/failed orders, P&L, drawdown, and displaying
results in formatted console tables.

Features:
- Historical performance analysis using strategy replay
- Order success/failure tracking
- P&L and drawdown calculations
- Per-asset breakdown
- Formatted console output with tables and colors
- Export options for CSV/JSON
"""

import argparse
import json
import sys
import os
import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Any, Tuple
import pandas as pd
from dotenv import load_dotenv
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

# Load environment variables
load_dotenv()

# Import project modules
from src.data_fetcher import DataFetcher
from src.symbol_config_manager import SymbolConfigManager
from src.strategy import MeanReversionStrategy
from src.backtest import run_backtest
from src.order_visualization import save_order_plots

# CLI formatting imports
try:
    from tabulate import tabulate
    import colorama
    from colorama import Fore, Back, Style
    colorama.init(autoreset=True)
    FORMATTING_AVAILABLE = True
except ImportError:
    FORMATTING_AVAILABLE = False
    print("Warning: tabulate and/or colorama not available. Install with: pip install tabulate colorama")

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Suppress verbose logging from strategy and other modules during analysis
logging.getLogger('src.strategy').setLevel(logging.WARNING)
logging.getLogger('src.bot.live_signal_detector').setLevel(logging.WARNING)
logging.getLogger('src.risk_management').setLevel(logging.WARNING)


class PerformanceAnalyzer:
    """
    Analyzes live strategy performance by replaying the strategy on historical data
    """

    def __init__(self, config_file_path: str):
        """
        Initialize performance analyzer

        Args:
            config_file_path: Path to asset configuration file
        """
        self.config_file_path = config_file_path
        self.symbols_config = {}

        # Load symbol configurations
        try:
            self.symbols_config = SymbolConfigManager.load_symbol_configs(self.config_file_path)
            logger.info(f"Loaded {len(self.symbols_config)} symbol configurations")
        except FileNotFoundError:
            logger.error(f"Configuration file not found: {self.config_file_path}")
            raise
        except Exception as e:
            logger.error(f"Error loading configurations: {e}")
            raise

    def calculate_date_range(self, period: str) -> Tuple[datetime, datetime]:
        """
        Calculate start and end dates based on period specification

        Args:
            period: Period specification like '3w', '21d', '1m'

        Returns:
            Tuple of (start_date, end_date)
        """
        end_date = datetime.now(timezone.utc)

        # Parse period format
        if period.endswith('w'):
            weeks = int(period[:-1])
            start_date = end_date - timedelta(weeks=weeks)
        elif period.endswith('d'):
            days = int(period[:-1])
            start_date = end_date - timedelta(days=days)
        elif period.endswith('m'):
            months = int(period[:-1])
            start_date = end_date - timedelta(days=months * 30)  # Approximate
        else:
            raise ValueError(f"Invalid period format: {period}. Use format like '3w', '21d', '1m'")

        return start_date, end_date

    def fetch_historical_data(self, symbol_config: Dict[str, Any], start_date: datetime, end_date: datetime) -> Optional[pd.DataFrame]:
        """
        Fetch historical data for a symbol within the specified date range

        Args:
            symbol_config: Symbol configuration dictionary
            start_date: Start date for data fetching
            end_date: End date for data fetching

        Returns:
            DataFrame with historical OHLCV data or None if failed
        """
        fetch_symbol = symbol_config['fetch_symbol']
        timeframe = symbol_config['timeframe']

        try:
            logger.debug(f"Fetching historical data for {fetch_symbol} ({timeframe}) from {start_date.date()} to {end_date.date()}")

            # Create data fetcher - disable cache to avoid stale data issues
            fetcher = DataFetcher(
                source='forex',
                symbol=fetch_symbol,
                timeframe=timeframe,
                use_cache=False  # Disable cache to get fresh data
            )

            # Calculate years needed for the time period
            days_needed = (end_date - start_date).days
            years = days_needed / 365.0

            # Add buffer for technical indicators
            years = max(years * 1.2, 0.1)  # At least 36 days for indicators

            # Fetch data
            data = fetcher.fetch(years=years)

            if data is not None and not data.empty:
                # Filter data to the requested date range - ensure timezone-aware comparison
                if data.index.tz is None:
                    # If data index is timezone-naive, assume UTC
                    data.index = pd.to_datetime(data.index, utc=True)

                # Ensure start_date and end_date are timezone-aware for comparison
                if start_date.tzinfo is None:
                    start_date = start_date.replace(tzinfo=timezone.utc)
                if end_date.tzinfo is None:
                    end_date = end_date.replace(tzinfo=timezone.utc)

                # Filter data to the requested date range
                original_count = len(data)
                data = data[(data.index >= start_date) & (data.index <= end_date)]
                logger.debug(f"Filtered {original_count} -> {len(data)} candles for {fetch_symbol} in date range")
                return data
            else:
                logger.warning(f"No data returned for {fetch_symbol}")
                return None

        except Exception as e:
            error_msg = str(e)
            if "404" in error_msg and "not-found.epic" in error_msg:
                logger.warning(f"Symbol {fetch_symbol} not available on Capital.com - this may be expected for some symbols")
            else:
                logger.error(f"Error fetching data for {fetch_symbol}: {e}")
            return None

    def analyze_symbol_performance(self, symbol_key: str, symbol_config: Dict[str, Any],
                                 start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """
        Analyze performance for a single symbol over the specified period

        Args:
            symbol_key: Symbol key (e.g., 'AUDUSDX_5m')
            symbol_config: Symbol configuration dictionary
            start_date: Analysis start date
            end_date: Analysis end date

        Returns:
            Performance analysis results dictionary
        """
        symbol = symbol_config['symbol']
        logger.info(f"Analyzing performance for {symbol}...")

        # Fetch historical data
        data = self.fetch_historical_data(symbol_config, start_date, end_date)

        if data is None or data.empty:
            return {
                'symbol': symbol,
                'status': 'data_unavailable',
                'error': f'Could not fetch historical data for {symbol_config.get("fetch_symbol", symbol)} - may not be available on Capital.com',
                'signals_generated': 0,
                'successful_orders': 0,
                'failed_orders': 0,
                'total_pnl': 0.0,
                'max_drawdown': 0.0,
                'win_rate': 0.0,
                'trades': []
            }

        try:
            # Create strategy parameters from config
            config = symbol_config['config']
            strategy_params = self._create_strategy_params(config)

            # Run actual backtest using the real MeanReversionStrategy
            logger.debug(f"Running backtest for {symbol} from {start_date.date()} to {end_date.date()}")

            # Run backtest with the exact same strategy used by live scheduler
            equity_curve, equity_dates, trade_log, order_log = run_backtest(
                data=data,
                strategy_class=MeanReversionStrategy,
                params=strategy_params,
                leverage=100.0,  # Same leverage as live scheduler
                verbose=False  # Keep quiet for performance
            )

            # Extract real performance data from backtest results
            initial_balance = equity_curve[0] if equity_curve else 100000.0
            final_balance = equity_curve[-1] if equity_curve else 100000.0
            total_pnl = final_balance - initial_balance

            # Calculate max drawdown from equity curve
            max_drawdown = 0.0
            if len(equity_curve) > 1:
                peak = initial_balance
                for value in equity_curve:
                    peak = max(peak, value)
                    current_drawdown = (peak - value) / peak
                    max_drawdown = max(max_drawdown, current_drawdown)

            # Process order log to extract trade information
            completed_trades = []
            signals_generated = len(order_log)  # All orders placed
            successful_orders = 0
            failed_orders = 0

            for order in order_log:
                if 'trade_outcome' in order:
                    outcome = order['trade_outcome']
                    successful_orders += 1

                    # Create trade record from order outcome
                    trade_record = {
                        'entry_time': f"{order['date']} {order['time']}",
                        'exit_time': outcome.get('exit_date', 'N/A'),
                        'signal_type': order['type'].lower(),
                        'entry_price': order['entry_price'],
                        'exit_price': outcome.get('exit_price', order['entry_price']),
                        'position_size': order.get('position_size', 0),
                        'pnl': outcome.get('pnl', 0),
                        'status': outcome.get('type', 'unknown'),
                        'exit_reason': outcome.get('reason', 'N/A')
                    }
                    completed_trades.append(trade_record)
                else:
                    # Order without outcome (likely cancelled or failed)
                    failed_orders += 1

            # Calculate win rate from completed trades
            winning_trades = [t for t in completed_trades if t['pnl'] > 0]
            win_rate = len(winning_trades) / len(completed_trades) * 100 if completed_trades else 0.0

            logger.debug(f"Backtest completed for {symbol}: {len(completed_trades)} trades, {signals_generated} signals")

            return {
                'symbol': symbol,
                'status': 'analyzed',
                'signals_generated': signals_generated,
                'successful_orders': successful_orders,
                'failed_orders': failed_orders,
                'total_pnl': total_pnl,
                'max_drawdown': max_drawdown * 100,  # Convert to percentage
                'win_rate': win_rate,
                'trades': completed_trades,
                'signals': order_log,  # All orders placed (signals)
                'final_balance': final_balance,
                'total_trades': len(completed_trades),
                'equity_curve': equity_curve,
                'equity_dates': equity_dates,
                'data': data  # Store data for visualization
            }

        except Exception as e:
            logger.error(f"Error analyzing {symbol}: {e}")
            return {
                'symbol': symbol,
                'status': 'analysis_failed',
                'error': str(e),
                'signals_generated': 0,
                'successful_orders': 0,
                'failed_orders': 1,
                'total_pnl': 0.0,
                'max_drawdown': 0.0,
                'win_rate': 0.0,
                'trades': []
            }


    def _create_strategy_params(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create strategy parameters from loaded configuration

        Args:
            config: Loaded configuration dictionary

        Returns:
            Strategy parameters dictionary
        """
        bb_config = config['BOLLINGER_BANDS']
        vwap_config = config['VWAP_BANDS']
        atr_config = config['ATR']
        risk_config = config['RISK_MANAGEMENT']
        strategy_config = config['STRATEGY_BEHAVIOR']

        return {
            'bb_window': bb_config['window'],
            'bb_std': bb_config['std_dev'],
            'vwap_window': vwap_config['window'],
            'vwap_std': vwap_config['std_dev'],
            'atr_period': atr_config['period'],
            'risk_per_position_pct': risk_config['risk_per_position_pct'],
            'stop_loss_atr_multiplier': risk_config['stop_loss_atr_multiplier'],
            'risk_reward_ratio': risk_config['risk_reward_ratio'],
            'require_reversal': strategy_config['require_reversal'],
            'regime_min_score': strategy_config['regime_min_score']
        }

    def analyze_all_symbols(self, period: str, symbols_filter: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Analyze performance for all configured symbols

        Args:
            period: Time period for analysis (e.g., '3w', '21d')
            symbols_filter: Optional list of symbols to analyze (default: all)

        Returns:
            Complete analysis results dictionary
        """
        logger.info(f"Starting performance analysis for period: {period}")

        # Calculate date range
        start_date, end_date = self.calculate_date_range(period)
        logger.info(f"Analysis period: {start_date.date()} to {end_date.date()}")

        # Filter symbols if requested
        symbols_to_analyze = self.symbols_config
        if symbols_filter:
            symbols_to_analyze = {k: v for k, v in self.symbols_config.items()
                                if v['symbol'] in symbols_filter}
            logger.info(f"Analyzing {len(symbols_to_analyze)} filtered symbols")

        # Analyze each symbol
        results = {}
        total_symbols = len(symbols_to_analyze)

        for i, (symbol_key, symbol_config) in enumerate(symbols_to_analyze.items(), 1):
            symbol = symbol_config['symbol']
            logger.info(f"[{i}/{total_symbols}] Analyzing {symbol}...")

            try:
                result = self.analyze_symbol_performance(symbol_key, symbol_config, start_date, end_date)
                results[symbol_key] = result
            except Exception as e:
                logger.error(f"Failed to analyze {symbol}: {e}")
                results[symbol_key] = {
                    'symbol': symbol,
                    'status': 'failed',
                    'error': str(e),
                    'signals_generated': 0,
                    'successful_orders': 0,
                    'failed_orders': 1,
                    'total_pnl': 0.0,
                    'max_drawdown': 0.0,
                    'win_rate': 0.0,
                    'trades': []
                }

        # Compile summary statistics
        summary = self._compile_summary_statistics(results, start_date, end_date, period)

        return {
            'summary': summary,
            'symbol_results': results,
            'analysis_period': {
                'start_date': start_date.isoformat(),
                'end_date': end_date.isoformat(),
                'period': period
            }
        }

    def _compile_summary_statistics(self, results: Dict[str, Dict], start_date: datetime,
                                   end_date: datetime, period: str) -> Dict[str, Any]:
        """
        Compile summary statistics from individual symbol results

        Args:
            results: Dictionary of symbol analysis results
            start_date: Analysis start date
            end_date: Analysis end date
            period: Period specification

        Returns:
            Summary statistics dictionary
        """
        successful_analyses = [r for r in results.values() if r['status'] == 'analyzed']
        failed_analyses = [r for r in results.values() if r['status'] != 'analyzed']

        total_signals = sum([r.get('signals_generated', 0) for r in successful_analyses])
        total_successful_orders = sum([r.get('successful_orders', 0) for r in successful_analyses])
        total_failed_orders = sum([r.get('failed_orders', 0) for r in results.values()])
        total_pnl = sum([r.get('total_pnl', 0) for r in successful_analyses])

        # Calculate overall win rate
        all_trades = []
        for result in successful_analyses:
            all_trades.extend(result.get('trades', []))

        winning_trades = [t for t in all_trades if t['pnl'] > 0]
        overall_win_rate = len(winning_trades) / len(all_trades) * 100 if all_trades else 0.0

        # Calculate average risk/reward ratio for winning trades
        avg_winning_rr_ratio = 0.0
        if winning_trades:
            winning_rr_ratios = []
            for trade in winning_trades:
                # Find the corresponding order with risk/reward info
                for result in successful_analyses:
                    for order in result.get('signals', []):
                        if 'trade_outcome' in order:
                            outcome = order['trade_outcome']
                            # Match trade by comparing PNL and entry details
                            if (abs(outcome.get('pnl', 0) - trade['pnl']) < 0.01 and
                                abs(order['entry_price'] - trade['entry_price']) < 0.00001):
                                # Calculate actual risk/reward achieved
                                entry = order['entry_price']
                                stop_loss = order['stop_loss']
                                exit_price = outcome.get('exit_price', entry)

                                # Determine if long or short trade
                                is_long = order['type'].upper() == 'BUY'

                                if is_long:
                                    risk = abs(entry - stop_loss)
                                    reward = abs(exit_price - entry)
                                else:  # Short trade
                                    risk = abs(stop_loss - entry)
                                    reward = abs(entry - exit_price)

                                if risk > 0:
                                    actual_rr = reward / risk
                                    winning_rr_ratios.append(actual_rr)
                                break

            if winning_rr_ratios:
                avg_winning_rr_ratio = sum(winning_rr_ratios) / len(winning_rr_ratios)

        # Calculate maximum drawdown across all symbols
        max_drawdown = max([r.get('max_drawdown', 0) for r in successful_analyses]) if successful_analyses else 0.0

        return {
            'period': period,
            'start_date': start_date.isoformat(),
            'end_date': end_date.isoformat(),
            'total_symbols_analyzed': len(successful_analyses),
            'total_symbols_failed': len(failed_analyses),
            'total_symbols_configured': len(results),
            'total_signals_generated': total_signals,
            'total_successful_orders': total_successful_orders,
            'total_failed_orders': total_failed_orders,
            'total_trades': len(all_trades),
            'winning_trades': len(winning_trades),
            'losing_trades': len(all_trades) - len(winning_trades),
            'total_pnl': total_pnl,
            'overall_win_rate': overall_win_rate,
            'avg_winning_rr_ratio': avg_winning_rr_ratio,
            'max_drawdown': max_drawdown,
            'success_rate': (total_successful_orders / (total_successful_orders + total_failed_orders) * 100)
                           if (total_successful_orders + total_failed_orders) > 0 else 0.0
        }


def format_currency(amount: float) -> str:
    """Format currency amount with appropriate color coding"""
    if not FORMATTING_AVAILABLE:
        return f"${amount:,.2f}"

    if amount > 0:
        return f"{Fore.GREEN}${amount:,.2f}{Style.RESET_ALL}"
    elif amount < 0:
        return f"{Fore.RED}${amount:,.2f}{Style.RESET_ALL}"
    else:
        return f"${amount:,.2f}"


def format_percentage(pct: float, reverse_colors: bool = False) -> str:
    """Format percentage with appropriate color coding"""
    if not FORMATTING_AVAILABLE:
        return f"{pct:.1f}%"

    # For drawdown, higher values are bad (reverse_colors=True)
    if reverse_colors:
        if pct > 5.0:
            return f"{Fore.RED}{pct:.1f}%{Style.RESET_ALL}"
        elif pct > 2.0:
            return f"{Fore.YELLOW}{pct:.1f}%{Style.RESET_ALL}"
        else:
            return f"{Fore.GREEN}{pct:.1f}%{Style.RESET_ALL}"
    else:
        # For win rate, higher values are good
        if pct >= 60.0:
            return f"{Fore.GREEN}{pct:.1f}%{Style.RESET_ALL}"
        elif pct >= 45.0:
            return f"{Fore.YELLOW}{pct:.1f}%{Style.RESET_ALL}"
        else:
            return f"{Fore.RED}{pct:.1f}%{Style.RESET_ALL}"


def format_status_indicator(status: str) -> str:
    """Format status with appropriate indicators"""
    indicators = {
        'analyzed': '✅' if FORMATTING_AVAILABLE else '[OK]',
        'data_unavailable': '❌' if FORMATTING_AVAILABLE else '[NO DATA]',
        'analysis_failed': '❌' if FORMATTING_AVAILABLE else '[FAILED]',
        'failed': '❌' if FORMATTING_AVAILABLE else '[ERROR]'
    }
    return indicators.get(status, status)


def generate_pnl_curve_chart(analysis_results: Dict[str, Any], period: str) -> Optional[str]:
    """
    Generate PnL curve chart from trade data

    Args:
        analysis_results: Complete analysis results dictionary
        period: Analysis period string for filename

    Returns:
        Path to generated chart file or None if failed
    """
    try:
        # Collect all trades from all symbols and sort chronologically
        all_trades = []
        symbol_results = analysis_results['symbol_results']

        for symbol_key, result in symbol_results.items():
            if result['status'] == 'analyzed' and result.get('trades'):
                symbol = result['symbol']
                for trade in result['trades']:
                    try:
                        entry_datetime = pd.to_datetime(trade['entry_time'])
                    except:
                        entry_datetime = pd.to_datetime('2025-01-01')

                    all_trades.append({
                        'symbol': symbol,
                        'entry_time': entry_datetime,
                        'pnl': trade.get('pnl', 0),
                        'entry_price': trade.get('entry_price', 0),
                        'signal_type': trade.get('signal_type', 'unknown')
                    })

        if not all_trades:
            logger.debug("No trades found for PnL curve chart")
            return None

        # Sort trades by entry time
        all_trades.sort(key=lambda x: x['entry_time'])

        # Calculate cumulative P&L
        cumulative_pnl = [0]  # Start at zero
        trade_numbers = [0]
        trade_dates = [all_trades[0]['entry_time']]

        running_pnl = 0
        for i, trade in enumerate(all_trades, 1):
            running_pnl += trade['pnl']
            cumulative_pnl.append(running_pnl)
            trade_numbers.append(i)
            trade_dates.append(trade['entry_time'])

        # Create the chart
        plt.style.use('default')  # Clean style
        fig, ax = plt.subplots(figsize=(14, 8))

        # Plot the cumulative P&L curve
        line_color = '#2E8B57' if cumulative_pnl[-1] >= 0 else '#DC143C'  # Green if profitable, red if loss
        ax.plot(trade_numbers, cumulative_pnl, linewidth=2.5, color=line_color, label='Cumulative P&L')

        # Fill areas above/below zero
        ax.fill_between(trade_numbers, cumulative_pnl, 0, alpha=0.3,
                       color='green' if cumulative_pnl[-1] >= 0 else 'red')

        # Add zero line
        ax.axhline(y=0, color='black', linestyle='-', alpha=0.3, linewidth=1)

        # Mark significant points
        max_pnl = max(cumulative_pnl)
        min_pnl = min(cumulative_pnl)

        if max_pnl > 0:
            max_idx = cumulative_pnl.index(max_pnl)
            ax.plot(trade_numbers[max_idx], max_pnl, marker='o', markersize=8,
                   color='green', markerfacecolor='lightgreen', markeredgewidth=2,
                   label=f'Peak: ${max_pnl:,.0f}')

        if min_pnl < 0:
            min_idx = cumulative_pnl.index(min_pnl)
            ax.plot(trade_numbers[min_idx], min_pnl, marker='v', markersize=8,
                   color='red', markerfacecolor='lightcoral', markeredgewidth=2,
                   label=f'Trough: ${min_pnl:,.0f}')

        # Formatting
        ax.set_xlabel('Trade Number', fontsize=12, fontweight='bold')
        ax.set_ylabel('Cumulative P&L ($)', fontsize=12, fontweight='bold')
        ax.set_title(f'Portfolio P&L Curve - {period.upper()} Period\n'
                    f'Final P&L: ${cumulative_pnl[-1]:,.2f} | Total Trades: {len(all_trades)}',
                    fontsize=14, fontweight='bold', pad=20)

        # Grid and styling
        ax.grid(True, alpha=0.3, linestyle='--')
        ax.legend(loc='upper left', frameon=True, fancybox=True, shadow=True)

        # Format y-axis to show currency
        ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'${x:,.0f}'))

        # Set background color
        fig.patch.set_facecolor('white')
        ax.set_facecolor('#FAFAFA')

        # Tight layout
        plt.tight_layout()

        # Save the chart
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"pnl_curve_{period}_{timestamp}.png"
        chart_path = os.path.join('plots', filename)

        # Ensure plots directory exists
        os.makedirs('plots', exist_ok=True)

        plt.savefig(chart_path, dpi=300, bbox_inches='tight', facecolor='white')
        plt.close()  # Close to free memory

        logger.info(f"PnL curve chart saved to: {chart_path}")
        return chart_path

    except Exception as e:
        logger.error(f"Error generating PnL curve chart: {e}")
        return None


def display_results(analysis_results: Dict[str, Any], detailed: bool = False, generate_chart: bool = False, save_order_charts: bool = False):
    """
    Display analysis results in formatted console tables

    Args:
        analysis_results: Complete analysis results dictionary
        detailed: Whether to show detailed per-trade information
        generate_chart: Whether to generate PnL curve chart
    """
    summary = analysis_results['summary']
    symbol_results = analysis_results['symbol_results']

    # Print header
    print("\n" + "=" * 80)
    if FORMATTING_AVAILABLE:
        print(f"{Fore.CYAN}{Style.BRIGHT}LIVE STRATEGY PERFORMANCE VERIFICATION REPORT{Style.RESET_ALL}")
    else:
        print("LIVE STRATEGY PERFORMANCE VERIFICATION REPORT")
    print("=" * 80)

    # Analysis period info
    start_date = datetime.fromisoformat(summary['start_date']).strftime('%Y-%m-%d')
    end_date = datetime.fromisoformat(summary['end_date']).strftime('%Y-%m-%d')
    print(f"Analysis Period: {summary['period']} ({start_date} to {end_date})")
    print(f"Configuration: assets_config_wr45.json ({summary['total_symbols_configured']} symbols)")
    print()

    # Summary statistics
    if FORMATTING_AVAILABLE:
        print(f"{Fore.YELLOW}{Style.BRIGHT}SUMMARY METRICS:{Style.RESET_ALL}")
    else:
        print("SUMMARY METRICS:")

    summary_data = [
        ["Total Symbols Analyzed", f"{summary['total_symbols_analyzed']}/{summary['total_symbols_configured']}"],
        ["Total Signals Generated", summary['total_signals_generated']],
        ["Total Trades Executed", summary['total_trades']],
        ["Successful Orders", f"{summary['total_successful_orders']} ({summary['success_rate']:.1f}%)"],
        ["Failed Orders", summary['total_failed_orders']],
        ["Winning Trades", f"{summary['winning_trades']}/{summary['total_trades']}"],
        ["Overall Win Rate", format_percentage(summary['overall_win_rate'])],
        ["Avg Winning R/R Ratio", f"{summary.get('avg_winning_rr_ratio', 0):.2f}:1" if summary.get('avg_winning_rr_ratio', 0) > 0 else "N/A"],
        ["Total P&L", format_currency(summary['total_pnl'])],
        ["Max Drawdown", format_percentage(summary['max_drawdown'], reverse_colors=True)]
    ]

    if FORMATTING_AVAILABLE:
        print(tabulate(summary_data, headers=["Metric", "Value"], tablefmt="grid"))
    else:
        for metric, value in summary_data:
            print(f"{metric:.<25} {value}")

    print()

    # Per-symbol performance table
    if FORMATTING_AVAILABLE:
        print(f"{Fore.YELLOW}{Style.BRIGHT}PER-SYMBOL PERFORMANCE:{Style.RESET_ALL}")
    else:
        print("PER-SYMBOL PERFORMANCE:")

    # Prepare symbol performance data
    symbol_data = []
    for symbol_key, result in symbol_results.items():
        symbol_data.append([
            format_status_indicator(result['status']),
            result['symbol'],
            result.get('signals_generated', 0),
            result.get('total_trades', 0),
            format_percentage(result.get('win_rate', 0)),
            format_currency(result.get('total_pnl', 0)),
            format_percentage(result.get('max_drawdown', 0), reverse_colors=True)
        ])

    # Sort by P&L descending - but put failed symbols at the end
    def sort_key(x):
        if x[0] == '❌' or '[NO DATA]' in str(x[0]) or '[FAILED]' in str(x[0]) or '[ERROR]' in str(x[0]):
            return -999999  # Put failed symbols at the bottom
        try:
            pnl_str = str(x[5])
            if 'Fore' in pnl_str:
                # Extract from colored string
                pnl_str = pnl_str.split('$')[1].split()[0].replace(',', '')
            else:
                pnl_str = pnl_str.replace('$', '').replace(',', '')
            return float(pnl_str)
        except:
            return 0

    symbol_data.sort(key=sort_key, reverse=True)

    headers = ["Status", "Symbol", "Signals", "Trades", "Win Rate", "P&L", "Max DD"]

    if FORMATTING_AVAILABLE:
        print(tabulate(symbol_data, headers=headers, tablefmt="grid"))
    else:
        # Simple text table for fallback
        print(f"{'Status':<8} {'Symbol':<10} {'Signals':<8} {'Trades':<7} {'Win Rate':<9} {'P&L':<12} {'Max DD':<8}")
        print("-" * 70)
        for row in symbol_data:
            print(f"{str(row[0]):<8} {str(row[1]):<10} {row[2]:<8} {row[3]:<7} {str(row[4]):<9} {str(row[5]):<12} {str(row[6]):<8}")

    # Consolidated trades summary table
    print()
    if FORMATTING_AVAILABLE:
        print(f"{Fore.YELLOW}{Style.BRIGHT}ALL EXECUTED TRADES:{Style.RESET_ALL}")
    else:
        print("ALL EXECUTED TRADES:")

    # Collect all trades from all symbols
    all_trades = []
    for symbol_key, result in symbol_results.items():
        if result['status'] == 'analyzed' and result.get('trades'):
            symbol = result['symbol']
            for trade in result['trades']:
                # Parse entry time for sorting
                try:
                    entry_datetime = pd.to_datetime(trade['entry_time'])
                except:
                    entry_datetime = pd.to_datetime('2025-01-01')  # Fallback date

                all_trades.append({
                    'symbol': symbol,
                    'entry_time': trade['entry_time'],
                    'exit_time': trade.get('exit_time', 'N/A'),
                    'signal_type': trade['signal_type'],
                    'entry_price': trade['entry_price'],
                    'exit_price': trade.get('exit_price', 0),
                    'pnl': trade.get('pnl', 0),
                    'status': trade.get('status', 'unknown'),
                    'entry_datetime': entry_datetime
                })

    # Sort trades by entry time
    all_trades.sort(key=lambda x: x['entry_datetime'])

    if all_trades:
        # Calculate summary statistics
        total_pnl = sum(t['pnl'] for t in all_trades)
        winning_trades = [t for t in all_trades if t['pnl'] > 0]
        losing_trades = [t for t in all_trades if t['pnl'] < 0]

        # Show trade outcome statistics
        tp_count = len([t for t in all_trades if 'take_profit' in t.get('status', '')])
        sl_count = len([t for t in all_trades if 'stop_loss' in t.get('status', '')])
        timeout_count = len([t for t in all_trades if 'timeout' in t.get('status', '')])

        print(f"\nTrade Statistics:")
        print(f"  Total Trades: {len(all_trades)}")
        print(f"  Winners: {len(winning_trades)} | Losers: {len(losing_trades)}")
        print(f"  Take Profits: {tp_count} | Stop Losses: {sl_count} | Timeouts: {timeout_count}")
        if winning_trades:
            avg_win = sum(t['pnl'] for t in winning_trades) / len(winning_trades)
            print(f"  Average Win: {format_currency(avg_win)}")
        if losing_trades:
            avg_loss = sum(t['pnl'] for t in losing_trades) / len(losing_trades)
            print(f"  Average Loss: {format_currency(avg_loss)}")
        print(f"  Total P&L: {format_currency(total_pnl)}")
        print()

        # Prepare trade table data
        trade_table_data = []
        for trade in all_trades:
            # Format times
            try:
                entry_time = pd.to_datetime(trade['entry_time']).strftime('%m-%d %H:%M')
            except:
                entry_time = trade['entry_time']

            try:
                exit_time = pd.to_datetime(trade['exit_time']).strftime('%m-%d %H:%M')
            except:
                exit_time = trade['exit_time']

            # Format status/outcome
            status = trade['status']
            if 'take_profit' in status:
                status_display = 'TP' if FORMATTING_AVAILABLE else 'TakeProfit'
            elif 'stop_loss' in status:
                status_display = 'SL' if FORMATTING_AVAILABLE else 'StopLoss'
            elif 'timeout' in status:
                status_display = 'TO' if FORMATTING_AVAILABLE else 'Timeout'
            else:
                status_display = '??' if FORMATTING_AVAILABLE else 'Unknown'

            trade_table_data.append([
                trade['symbol'],
                entry_time,
                exit_time,
                trade['signal_type'].upper(),
                f"{trade['entry_price']:.5f}",
                f"{trade['exit_price']:.5f}",
                format_currency(trade['pnl']),
                status_display
            ])

        headers = ["Symbol", "Entry Time", "Exit Time", "Type", "Entry", "Exit", "P&L", "Outcome"]

        if FORMATTING_AVAILABLE:
            print(tabulate(trade_table_data, headers=headers, tablefmt="grid"))
        else:
            # Simple text table fallback
            print(f"{'Symbol':<10} {'Entry Time':<12} {'Exit Time':<12} {'Type':<5} {'Entry':<8} {'Exit':<8} {'P&L':<12} {'Outcome':<10}")
            print("-" * 95)
            for row in trade_table_data:
                print(f"{row[0]:<10} {row[1]:<12} {row[2]:<12} {row[3]:<5} {row[4]:<8} {row[5]:<8} {str(row[6]):<12} {row[7]:<10}")
    else:
        print("No trades executed during this period.")

    # Show warnings for failed symbols
    failed_symbols = [(result['symbol'], result.get('error', 'Unknown error'))
                     for result in symbol_results.values()
                     if result['status'] in ['data_unavailable', 'analysis_failed', 'failed']]

    if failed_symbols:
        print()
        if FORMATTING_AVAILABLE:
            print(f"{Fore.YELLOW}⚠️  WARNING - Some symbols failed analysis:{Style.RESET_ALL}")
        else:
            print("WARNING - Some symbols failed analysis:")

        for symbol, error in failed_symbols:
            if FORMATTING_AVAILABLE:
                print(f"   • {Fore.RED}{symbol}{Style.RESET_ALL}: {error}")
            else:
                print(f"   • {symbol}: {error}")

    # Detailed trade information if requested
    if detailed:
        print()
        if FORMATTING_AVAILABLE:
            print(f"{Fore.YELLOW}{Style.BRIGHT}DETAILED TRADE ANALYSIS:{Style.RESET_ALL}")
        else:
            print("DETAILED TRADE ANALYSIS:")

        for symbol_key, result in symbol_results.items():
            if result['status'] == 'analyzed' and result.get('trades'):
                print(f"\n{result['symbol']} - {len(result['trades'])} trades:")

                trade_data = []
                for trade in result['trades'][:10]:  # Show only first 10 trades to avoid clutter
                    entry_time = pd.to_datetime(trade['entry_time']).strftime('%m-%d %H:%M')
                    exit_time = pd.to_datetime(trade['exit_time']).strftime('%m-%d %H:%M')
                    trade_data.append([
                        entry_time,
                        exit_time,
                        trade['signal_type'].upper(),
                        f"{trade['entry_price']:.4f}",
                        f"{trade['exit_price']:.4f}",
                        format_currency(trade['pnl'])
                    ])

                if FORMATTING_AVAILABLE:
                    print(tabulate(trade_data,
                                 headers=["Entry Time", "Exit Time", "Type", "Entry", "Exit", "P&L"],
                                 tablefmt="grid"))
                else:
                    print(f"{'Entry Time':<12} {'Exit Time':<12} {'Type':<5} {'Entry':<8} {'Exit':<8} {'P&L':<10}")
                    print("-" * 60)
                    for row in trade_data:
                        print(f"{row[0]:<12} {row[1]:<12} {row[2]:<5} {row[3]:<8} {row[4]:<8} {str(row[5]):<10}")

                if len(result['trades']) > 10:
                    print(f"... and {len(result['trades']) - 10} more trades")

    # Generate PnL curve chart if requested
    if generate_chart:
        print()
        if FORMATTING_AVAILABLE:
            print(f"{Fore.YELLOW}{Style.BRIGHT}GENERATING P&L CURVE CHART:{Style.RESET_ALL}")
        else:
            print("GENERATING P&L CURVE CHART:")

        chart_path = generate_pnl_curve_chart(analysis_results, summary['period'])
        if chart_path:
            print(f"📈 Chart saved: {chart_path}")
            if FORMATTING_AVAILABLE:
                print(f"{Fore.GREEN}✅ P&L curve chart generated successfully!{Style.RESET_ALL}")
            else:
                print("✅ P&L curve chart generated successfully!")
        else:
            if FORMATTING_AVAILABLE:
                print(f"{Fore.YELLOW}⚠️  No trades found - chart not generated{Style.RESET_ALL}")
            else:
                print("⚠️  No trades found - chart not generated")

    # Generate order tracking charts if requested
    if save_order_charts:
        print()
        if FORMATTING_AVAILABLE:
            print(f"{Fore.YELLOW}{Style.BRIGHT}GENERATING ORDER TRACKING CHARTS:{Style.RESET_ALL}")
        else:
            print("GENERATING ORDER TRACKING CHARTS:")

        # Process each symbol that has data and orders
        symbol_results = analysis_results['symbol_results']
        all_chart_paths = []

        for symbol_key, result in symbol_results.items():
            if result['status'] == 'analyzed' and result.get('signals') and result.get('data') is not None:
                symbol = result['symbol']
                data = result['data']
                orders = result.get('signals', [])

                # Format orders for save_order_plots
                formatted_orders = []
                for order in orders:
                    try:
                        formatted_order = {
                            'time': pd.to_datetime(f"{order['date']} {order['time']}"),
                            'entry': float(order['entry_price']),
                            'stop_loss': float(order['stop_loss']),
                            'take_profit': float(order['take_profit']),
                            'is_long': order['type'].lower() == 'buy'
                        }

                        # Add trade outcome if available
                        if 'trade_outcome' in order:
                            formatted_order['trade_outcome'] = order['trade_outcome']

                        formatted_orders.append(formatted_order)
                    except Exception as e:
                        logger.debug(f"Could not format order for {symbol}: {e}")

                if formatted_orders:
                    try:
                        # Generate charts for this symbol
                        print(f"  📊 Generating charts for {symbol}: {len(formatted_orders)} orders")

                        # Create timestamp-based directory for this analysis
                        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                        output_dir = f"plots/orders_{summary['period']}_{timestamp}"
                        os.makedirs(output_dir, exist_ok=True)

                        # Save order plots for this symbol
                        chart_path = save_order_plots(
                            df=data,
                            orders=formatted_orders,
                            output_dir=output_dir,
                            window_size=50  # Show 50 candles around each order
                        )

                        if chart_path:
                            all_chart_paths.append(chart_path)
                            print(f"    ✅ Chart saved: {chart_path}")

                    except Exception as e:
                        logger.error(f"Error generating charts for {symbol}: {e}")
                        if FORMATTING_AVAILABLE:
                            print(f"    {Fore.RED}❌ Error: {e}{Style.RESET_ALL}")
                        else:
                            print(f"    ❌ Error: {e}")

        if all_chart_paths:
            print()
            print(f"📈 Order tracking charts generated successfully!")
            print(f"   Total symbols processed: {len(all_chart_paths)}")
            if FORMATTING_AVAILABLE:
                print(f"{Fore.GREEN}✅ All order charts saved to plots/ directory{Style.RESET_ALL}")
            else:
                print("✅ All order charts saved to plots/ directory")
        else:
            if FORMATTING_AVAILABLE:
                print(f"{Fore.YELLOW}⚠️  No orders with data found - charts not generated{Style.RESET_ALL}")
            else:
                print("⚠️  No orders with data found - charts not generated")


def export_results(analysis_results: Dict[str, Any], export_format: str, filename: str):
    """
    Export analysis results to file

    Args:
        analysis_results: Complete analysis results dictionary
        export_format: Export format ('json' or 'csv')
        filename: Output filename
    """
    try:
        if export_format.lower() == 'json':
            # Export complete results as JSON
            with open(filename, 'w') as f:
                json.dump(analysis_results, f, indent=2, default=str)
            logger.info(f"Results exported to {filename}")

        elif export_format.lower() == 'csv':
            # Export summary table as CSV
            summary_df = pd.DataFrame([analysis_results['summary']])

            # Create per-symbol dataframe
            symbol_data = []
            for symbol_key, result in analysis_results['symbol_results'].items():
                symbol_data.append({
                    'symbol': result['symbol'],
                    'status': result['status'],
                    'signals_generated': result.get('signals_generated', 0),
                    'total_trades': result.get('total_trades', 0),
                    'win_rate': result.get('win_rate', 0),
                    'total_pnl': result.get('total_pnl', 0),
                    'max_drawdown': result.get('max_drawdown', 0)
                })

            symbol_df = pd.DataFrame(symbol_data)

            # Write to CSV with multiple sheets simulation
            base_name = filename.replace('.csv', '')
            summary_df.to_csv(f"{base_name}_summary.csv", index=False)
            symbol_df.to_csv(f"{base_name}_symbols.csv", index=False)

            logger.info(f"Results exported to {base_name}_summary.csv and {base_name}_symbols.csv")

        else:
            raise ValueError(f"Unsupported export format: {export_format}")

    except Exception as e:
        logger.error(f"Error exporting results: {e}")


def main():
    """Main CLI entry point"""

    # Check for Capital.com credentials first
    required_env_vars = [
        'CAPITAL_COM_API_KEY',
        'CAPITAL_COM_PASSWORD',
        'CAPITAL_COM_IDENTIFIER'
    ]

    missing_vars = []
    for var in required_env_vars:
        if not os.getenv(var):
            missing_vars.append(var)

    if missing_vars:
        print(f"❌ Error: Missing required Capital.com credentials in .env file:")
        for var in missing_vars:
            print(f"   - {var}")
        print("\nPlease ensure these environment variables are set in your .env file")
        sys.exit(1)

    parser = argparse.ArgumentParser(
        description="Live Strategy Performance Verification Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                           # Analyze last 3 weeks (default)
  %(prog)s --period 1m               # Analyze last month
  %(prog)s --period 14d              # Analyze last 14 days
  %(prog)s --symbols EURUSD GBPUSD   # Analyze specific symbols only
  %(prog)s --detailed                # Show detailed trade information
  %(prog)s --chart                   # Generate P&L curve chart
  %(prog)s --detailed --chart        # Detailed analysis with chart
  %(prog)s --export json results.json # Export results to JSON
        """
    )

    parser.add_argument(
        '--period', '-p',
        default='3w',
        help='Analysis period (e.g., 3w=3 weeks, 21d=21 days, 1m=1 month). Default: 3w'
    )

    parser.add_argument(
        '--symbols', '-s',
        nargs='*',
        help='Specific symbols to analyze (default: all configured symbols)'
    )

    parser.add_argument(
        '--config',
        default='assets_config_wr45.json',
        help='Path to asset configuration file (default: assets_config_wr45.json)'
    )

    parser.add_argument(
        '--detailed', '-d',
        action='store_true',
        help='Show detailed per-trade analysis'
    )

    parser.add_argument(
        '--chart', '-c',
        action='store_true',
        help='Generate P&L curve chart'
    )

    parser.add_argument(
        '--save-order-charts',
        action='store_true',
        help='Generate combined chart showing all orders with SL/TP levels'
    )

    parser.add_argument(
        '--export',
        choices=['json', 'csv'],
        help='Export results to file format'
    )

    parser.add_argument(
        '--output', '-o',
        help='Output filename for export (auto-generated if not specified)'
    )

    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose logging'
    )

    args = parser.parse_args()

    # Configure logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Validate configuration file path
    config_path = os.path.join(os.path.dirname(__file__), args.config)
    if not os.path.exists(config_path):
        logger.error(f"Configuration file not found: {config_path}")
        sys.exit(1)

    try:
        # Initialize analyzer
        analyzer = PerformanceAnalyzer(config_path)

        # Run analysis
        logger.info("Starting performance analysis...")
        results = analyzer.analyze_all_symbols(args.period, args.symbols)

        # Display results
        display_results(results, detailed=args.detailed, generate_chart=args.chart,
                       save_order_charts=args.save_order_charts)

        # Export if requested
        if args.export:
            if args.output:
                filename = args.output
            else:
                # Generate filename
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                filename = f"performance_analysis_{args.period}_{timestamp}.{args.export}"

            export_results(results, args.export, filename)

        logger.info("Analysis completed successfully!")

    except KeyboardInterrupt:
        logger.info("Analysis interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Analysis failed: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
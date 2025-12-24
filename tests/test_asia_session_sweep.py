"""
Test script for Asia Session Sweep Strategy on DE40 (DAX Index)

This script validates the Asia session sweep detector by:
1. Fetching historical DE40 data from Capital.com for a specified date range
2. Running the detector on each eligible candle (8:30-9:30 UTC)
3. Generating a detailed report with all detected signals
4. Optionally creating charts for visual verification

Usage:
    python tests/test_asia_session_sweep.py --start 2024-12-01 --end 2024-12-20
    python tests/test_asia_session_sweep.py --start 2024-12-01 --end 2024-12-20 --charts
"""

import sys
import os
import argparse
import logging
import json
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Optional
import pandas as pd
from pathlib import Path
from dotenv import load_dotenv

# Add project root to path first
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Load environment variables from .env file in project root
dotenv_path = project_root / '.env'
if dotenv_path.exists():
    load_dotenv(dotenv_path=dotenv_path)
    print(f"✓ Loaded environment from: {dotenv_path}")
else:
    print(f"⚠ Warning: .env file not found at {dotenv_path}")
    load_dotenv()  # Try to load from default locations

from src.bot.custom_scripts.asia_session_sweep_detector import AsiaSessionSweepDetector
from src.capital_com_fetcher import create_capital_com_fetcher
from src.helpers import format_trading_session_info

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class AsiaSessionSweepTester:
    """
    Test harness for Asia Session Sweep strategy.
    """
    
    def __init__(self, strategy_config: dict):
        """
        Initialize tester with strategy config.
        Uses Capital.com credentials from environment variables.
        
        Args:
            strategy_config: Strategy configuration dictionary
        """
        self.fetcher = create_capital_com_fetcher()
        if not self.fetcher:
            raise ValueError("Failed to create Capital.com fetcher. Check credentials in .env")
        
        self.detector = AsiaSessionSweepDetector(
            session_start=strategy_config.get('session_start', '03:00'),
            session_end=strategy_config.get('session_end', '07:00'),
            signal_window_start=strategy_config.get('signal_window_start', '08:30'),
            signal_window_end=strategy_config.get('signal_window_end', '09:30')
        )
        self.signals: List[Dict] = []
        logger.info(f"Tester initialized (demo={self.fetcher.demo})")
    
    def fetch_data(self, symbol: str, start_date: datetime, end_date: datetime) -> pd.DataFrame:
        """
        Fetch historical data from Capital.com.
        
        Args:
            symbol: Trading symbol (e.g., 'GERMANY40')
            start_date: Start date (UTC)
            end_date: End date (UTC)
        
        Returns:
            DataFrame with OHLCV data
        """
        logger.info(f"Fetching {symbol} data from {start_date} to {end_date}")
        
        try:
            # Use fetch_historical_data method
            data = self.fetcher.fetch_historical_data(
                symbol=symbol,
                asset_type='indices',
                timeframe='5m',
                start_date=start_date,
                end_date=end_date
            )
            
            if data is None or data.empty:
                logger.error(f"No data returned for {symbol}")
                return pd.DataFrame()
            
            # Data already comes in standard format with lowercase columns
            df = data.copy()
            
            # Handle timestamp in index or as column
            if 'timestamp' not in df.columns:
                if 'date' in df.columns:
                    df['timestamp'] = df['date']
                elif df.index.name == 'timestamp' or isinstance(df.index, pd.DatetimeIndex):
                    # Timestamp is in the index, reset to column
                    df = df.reset_index()
                    if 'index' in df.columns:
                        df.rename(columns={'index': 'timestamp'}, inplace=True)
            
            # Ensure UTC timezone
            if 'timestamp' in df.columns:
                if df['timestamp'].dt.tz is None:
                    df['timestamp'] = df['timestamp'].dt.tz_localize('UTC')
                else:
                    df['timestamp'] = df['timestamp'].dt.tz_convert('UTC')
            
            logger.info(f"Fetched {len(df)} candles for {symbol}")
            return df.sort_values('timestamp').reset_index(drop=True)
        
        except Exception as e:
            logger.error(f"Error fetching data: {e}", exc_info=True)
            return pd.DataFrame()
    
    def run_backtest(self, data: pd.DataFrame, symbol: str = 'DE40') -> List[Dict]:
        """
        Run the detector on historical data and collect all signals.
        
        Args:
            data: Historical OHLCV data
            symbol: Trading symbol
        
        Returns:
            List of all detected signals
        """
        if data.empty:
            logger.error("Cannot run backtest: empty data")
            return []
        
        self.signals = []
        signal_window_candles = 0
        
        logger.info(f"Running backtest on {len(data)} candles...")
        logger.info(f"Date range: {data['timestamp'].min()} to {data['timestamp'].max()}")
        
        # Iterate through data, simulating real-time analysis
        # We need at least enough data to cover one Asia session
        min_required = 50  # ~4 hours at 5min intervals
        
        for i in range(min_required, len(data)):
            # Get data up to current point (simulating live data)
            current_data = data.iloc[:i+1].copy()
            current_timestamp = current_data.iloc[-1]['timestamp']
            current_time = current_timestamp.time()
            
            # Only analyze during signal window (8:30-9:30 UTC)
            if not (self.detector.signal_window_start <= current_time <= self.detector.signal_window_end):
                continue
            
            signal_window_candles += 1
            
            # Detect signal
            signal = self.detector.detect_signals(current_data, symbol)
            
            # Store all signals (including no_signal for analysis)
            signal['candle_index'] = i
            self.signals.append(signal)
        
        logger.info(f"Backtest complete. Analyzed {signal_window_candles} candles in signal window.")
        logger.info(f"Total signals recorded: {len(self.signals)}")
        
        return self.signals
    
    def generate_report(self) -> str:
        """
        Generate a detailed text report of all signals.
        
        Returns:
            Formatted report string
        """
        if not self.signals:
            return "No signals detected in the test period."
        
        # Separate signals by type
        long_signals = [s for s in self.signals if s['signal_type'] == 'long']
        short_signals = [s for s in self.signals if s['signal_type'] == 'short']
        no_signals = [s for s in self.signals if s['signal_type'] == 'no_signal']
        errors = [s for s in self.signals if s['signal_type'] == 'error']
        
        report = []
        report.append("=" * 80)
        report.append("ASIA SESSION SWEEP STRATEGY - BACKTEST REPORT")
        report.append("=" * 80)
        report.append("")
        
        report.append(f"Test Period: {self.signals[0]['timestamp']} to {self.signals[-1]['timestamp']}")
        report.append(f"Total Candles Analyzed: {len(self.signals)}")
        report.append("")
        
        report.append("SIGNAL SUMMARY")
        report.append("-" * 80)
        report.append(f"Long Signals:     {len(long_signals)}")
        report.append(f"Short Signals:    {len(short_signals)}")
        report.append(f"No Signal:        {len(no_signals)}")
        report.append(f"Errors:           {len(errors)}")
        report.append(f"Total:            {len(self.signals)}")
        report.append("")
        
        # Long signals detail
        if long_signals:
            report.append("LONG SIGNALS")
            report.append("-" * 80)
            for idx, sig in enumerate(long_signals, 1):
                report.append(f"\n{idx}. {sig['timestamp']}")
                report.append(f"   Current Price: {sig['current_price']}")
                report.append(f"   Session High:  {sig['session_high']}")
                report.append(f"   Session Low:   {sig['session_low']}")
                report.append(f"   Reason:        {sig['reason']}")
            report.append("")
        
        # Short signals detail
        if short_signals:
            report.append("SHORT SIGNALS")
            report.append("-" * 80)
            for idx, sig in enumerate(short_signals, 1):
                report.append(f"\n{idx}. {sig['timestamp']}")
                report.append(f"   Current Price: {sig['current_price']}")
                report.append(f"   Session High:  {sig['session_high']}")
                report.append(f"   Session Low:   {sig['session_low']}")
                report.append(f"   Reason:        {sig['reason']}")
            report.append("")
        
        # Errors
        if errors:
            report.append("ERRORS")
            report.append("-" * 80)
            for sig in errors:
                report.append(f"{sig['timestamp']}: {sig['reason']}")
            report.append("")
        
        report.append("=" * 80)
        report.append("END OF REPORT")
        report.append("=" * 80)
        
        return "\n".join(report)
    
    def save_report(self, output_path: str):
        """Save the report to a file."""
        report = self.generate_report()
        
        os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else '.', exist_ok=True)
        
        with open(output_path, 'w') as f:
            f.write(report)
        
        logger.info(f"Report saved to {output_path}")
    
    def export_signals_csv(self, output_path: str):
        """Export signals to CSV for further analysis."""
        if not self.signals:
            logger.warning("No signals to export")
            return
        
        # Filter to actual trade signals
        trade_signals = [s for s in self.signals if s['signal_type'] in ['long', 'short']]
        
        if not trade_signals:
            logger.warning("No trade signals to export")
            return
        
        df = pd.DataFrame(trade_signals)
        
        # Select relevant columns
        columns = [
            'timestamp', 'signal_type', 'direction', 'symbol',
            'current_price', 'session_high', 'session_low', 'reason'
        ]
        df = df[columns]
        
        os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else '.', exist_ok=True)
        df.to_csv(output_path, index=False)
        
        logger.info(f"Signals exported to {output_path}")


def load_config(config_path: str) -> Dict:
    """Load strategy configuration from JSON file."""
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
        logger.info(f"Loaded config from {config_path}")
        return config
    except Exception as e:
        logger.error(f"Failed to load config: {e}")
        raise


def get_asset_config(config: Dict, symbol: str) -> Dict:
    """Get asset-specific configuration."""
    # Find asset in config
    for asset in config.get('assets', []):
        if asset['symbol'] == symbol:
            strategy_name = asset['strategy']
            strategy_config = config['strategies'].get(strategy_name, {})
            asset_details = config.get('asset_details', {}).get(symbol, {})
            
            return {
                'asset': asset,
                'strategy': strategy_config,
                'details': asset_details
            }
    
    raise ValueError(f"Asset {symbol} not found in config")


def main():
    """Main entry point for the test script."""
    parser = argparse.ArgumentParser(
        description='Test Asia Session Sweep Strategy on DE40',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Test for December 2024 (using default config)
  python tests/test_asia_session_sweep.py --start 2024-12-01 --end 2024-12-20
  
  # Test with custom config file
  python tests/test_asia_session_sweep.py --start 2024-12-01 --end 2024-12-20 --config my_config.json
        """
    )
    
    parser.add_argument('--start', required=True, help='Start date (YYYY-MM-DD)')
    parser.add_argument('--end', required=True, help='End date (YYYY-MM-DD)')
    parser.add_argument('--config', default='assets_config_custom_strategies.json', 
                       help='Config file path (default: assets_config_custom_strategies.json)')
    parser.add_argument('--symbol', default='DE40', help='Asset symbol (default: DE40)')
    
    args = parser.parse_args()
    
    # Parse dates
    try:
        start_date = datetime.strptime(args.start, '%Y-%m-%d').replace(tzinfo=timezone.utc)
        end_date = datetime.strptime(args.end, '%Y-%m-%d').replace(tzinfo=timezone.utc)
        
        # Add one day to end_date to include the full day
        end_date = end_date + timedelta(days=1)
    except ValueError as e:
        logger.error(f"Invalid date format: {e}")
        sys.exit(1)
    
    # Load configuration
    try:
        config = load_config(args.config)
        asset_config = get_asset_config(config, args.symbol)
        
        fetch_symbol = asset_config['asset']['fetch_symbol']
        strategy_params = asset_config['strategy'].get('parameters', {})
        
        logger.info(f"Testing {args.symbol} (fetch as {fetch_symbol})")
        logger.info(f"Strategy: {asset_config['asset']['strategy']}")
        logger.info(f"Session: {strategy_params.get('session_start')}-{strategy_params.get('session_end')}")
        logger.info(f"Signal window: {strategy_params.get('signal_window_start')}-{strategy_params.get('signal_window_end')}")
    except Exception as e:
        logger.error(f"Configuration error: {e}")
        sys.exit(1)
    
    # Initialize tester
    try:
        tester = AsiaSessionSweepTester(strategy_config=strategy_params)
        logger.info("Tester initialized")
    except ValueError as e:
        logger.error(str(e))
        sys.exit(1)
    
    # Fetch data
    data = tester.fetch_data(fetch_symbol, start_date, end_date)
    
    if data.empty:
        logger.error("Failed to fetch data. Exiting.")
        sys.exit(1)
    
    # Run backtest
    signals = tester.run_backtest(data, symbol='DE40')
    
    # Print summary to console
    print("\n")
    print(tester.generate_report())
    print("\n")
    
    return 0


if __name__ == '__main__':
    sys.exit(main())

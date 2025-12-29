"""
Unified Test Script for Custom Strategy Detectors

This script validates any custom detector by:
1. Loading the asset configuration to determine strategy and detector
2. Fetching historical data from Capital.com for a specified date range
3. Running the detector on eligible candles
4. Generating a detailed report with all detected signals
5. Optionally exporting signals to CSV and saving reports

Usage:
    # Test any asset from config
    python tests/test_custom_strategy.py --asset GOLD --start 2025-12-15 --end 2025-12-24
    
    # With custom config file
    python tests/test_custom_strategy.py --asset BTC --start 2025-12-01 --end 2025-12-24 --config my_config.json
    
    # Export signals and report
    python tests/test_custom_strategy.py --asset DE40 --start 2024-12-01 --end 2024-12-20 --export signals.csv --report report.txt

Examples:
    python tests/test_custom_strategy.py --asset GOLD --start 2025-12-15 --end 2025-12-24
    python tests/test_custom_strategy.py --asset BTC --start 2025-12-01 --end 2025-12-24 --export btc_signals.csv
    python tests/test_custom_strategy.py --asset DE40 --start 2024-12-01 --end 2024-12-20 --report dax_report.txt
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

from src.bot.custom_scripts import load_custom_strategy_config
from src.capital_com_fetcher import create_capital_com_fetcher

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class CustomStrategyTester:
    """
    Universal test harness for custom strategy detectors.
    """
    
    def __init__(self, asset_symbol: str, config_path: str):
        """
        Initialize tester with asset symbol and config.
        
        Args:
            asset_symbol: Asset symbol (e.g., 'GOLD', 'BTC', 'DE40')
            config_path: Path to configuration file
        """
        # Load configuration
        self.config_loader = load_custom_strategy_config(config_path)
        
        # Get asset config
        self.asset_config = self.config_loader.get_asset_by_symbol(asset_symbol)
        if not self.asset_config:
            raise ValueError(f"Asset {asset_symbol} not found in config {config_path}")
        
        # Get detector config
        self.detector_config = self.config_loader.get_detector_config(asset_symbol)
        
        # Create detector
        self.detector = self.config_loader.create_detector(asset_symbol)
        
        # Create fetcher
        self.fetcher = create_capital_com_fetcher()
        if not self.fetcher:
            raise ValueError("Failed to create Capital.com fetcher. Check credentials in .env")
        
        self.signals: List[Dict] = []
        self.asset_symbol = asset_symbol
        
        logger.info(f"Tester initialized for {asset_symbol} (demo={self.fetcher.demo})")
        logger.info(f"Strategy: {self.asset_config.get('strategy')}")
        logger.info(f"Fetch Symbol: {self.detector_config['fetch_symbol']}")
        logger.info(f"Timeframe: {self.detector_config['timeframe']}")
    
    def fetch_data(self, start_date: datetime, end_date: datetime) -> pd.DataFrame:
        """
        Fetch historical data from Capital.com.
        
        Args:
            start_date: Start date (UTC)
            end_date: End date (UTC)
        
        Returns:
            DataFrame with OHLCV data
        """
        fetch_symbol = self.detector_config['fetch_symbol']
        asset_type = self.detector_config.get('asset_type', 'indices')
        timeframe = self.detector_config['timeframe']
        
        logger.info(f"Fetching {fetch_symbol} ({asset_type}) data from {start_date} to {end_date}")
        
        try:
            # Use fetch_historical_data method
            data = self.fetcher.fetch_historical_data(
                symbol=fetch_symbol,
                asset_type=asset_type,
                timeframe=timeframe,
                start_date=start_date,
                end_date=end_date
            )
            
            if data.empty:
                logger.warning(f"No data returned for {fetch_symbol}")
                return pd.DataFrame()
            
            logger.info(f"Fetched {len(data)} candles")
            logger.info(f"Columns: {list(data.columns)}")
            
            # Ensure timestamp column exists
            if 'timestamp' not in data.columns:
                if 'time' in data.columns:
                    data['timestamp'] = data['time']
                elif 'date' in data.columns:
                    data['timestamp'] = data['date']
                elif data.index.name in ['timestamp', 'time', 'date']:
                    data = data.reset_index()
                    if 'index' in data.columns:
                        data['timestamp'] = data['index']
                else:
                    logger.error(f"No timestamp column found. Available columns: {list(data.columns)}")
                    raise ValueError("Data must contain a 'timestamp', 'time', or 'date' column")
            
            # Remove duplicates if timestamp column exists
            if 'timestamp' in data.columns:
                initial_len = len(data)
                data = data.drop_duplicates(subset=['timestamp'], keep='last')
                if len(data) < initial_len:
                    logger.info(f"Removed {initial_len - len(data)} duplicate timestamps")
                
                # Sort by timestamp
                data = data.sort_values('timestamp').reset_index(drop=True)
                
                # Log date range
                try:
                    logger.info(f"Date range: {data['timestamp'].min()} to {data['timestamp'].max()}")
                except Exception as e:
                    logger.warning(f"Could not log date range: {e}")
            
            return data
        
        except Exception as e:
            logger.error(f"Failed to fetch data: {e}")
            raise
    
    def run_backtest(self, data: pd.DataFrame) -> List[Dict]:
        """
        Run the detector on historical data and collect all signals.
        
        Args:
            data: Historical OHLCV data
        
        Returns:
            List of all detected signals
        """
        if data.empty:
            logger.warning("Cannot run backtest: no data available")
            return []
        
        self.signals = []
        signal_window_candles = 0
        
        logger.info(f"Running backtest on {len(data)} candles...")
        logger.info(f"Date range: {data['timestamp'].min()} to {data['timestamp'].max()}")
        
        # Determine minimum required candles based on strategy
        strategy_name = self.asset_config.get('strategy', '')
        if 'vwap' in strategy_name.lower():
            min_required = 288  # 24 hours at 5min intervals (for daily reset VWAP)
        elif 'session' in strategy_name.lower():
            min_required = 50   # ~4 hours at 5min intervals
        else:
            min_required = 100  # Safe default
        
        logger.info(f"Minimum required candles: {min_required}")
        
        # Iterate through data, simulating real-time analysis
        for i in range(min_required, len(data)):
            # Get historical data up to current point
            historical_data = data.iloc[:i+1].copy()
            current_candle = data.iloc[i]
            
            # Get detector's signal window (if available)
            detector_has_window = hasattr(self.detector, 'is_in_signal_window')
            
            if detector_has_window:
                in_window = self.detector.is_in_signal_window(current_candle['timestamp'])
                if in_window:
                    signal_window_candles += 1
            else:
                signal_window_candles += 1
            
            # Detect signal
            signal = self.detector.detect_signals(historical_data, symbol=self.asset_symbol)
            
            if signal['signal_type'] != 'no_signal' or (detector_has_window and in_window):
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
            return "No signals to report."
        
        # Separate signals by type
        long_signals = [s for s in self.signals if s['signal_type'] == 'long']
        short_signals = [s for s in self.signals if s['signal_type'] == 'short']
        no_signals = [s for s in self.signals if s['signal_type'] == 'no_signal']
        errors = [s for s in self.signals if s['signal_type'] == 'error']
        
        strategy_name = self.asset_config.get('strategy', 'CUSTOM').upper()
        
        report = []
        report.append("=" * 80)
        report.append(f"{self.asset_symbol} - {strategy_name} STRATEGY - BACKTEST REPORT")
        report.append("=" * 80)
        report.append("")
        
        report.append(f"Test Period: {self.signals[0]['timestamp']} to {self.signals[-1]['timestamp']}")
        report.append(f"Total Candles Analyzed: {len(self.signals)}")
        report.append(f"Strategy: {self.asset_config.get('strategy')}")
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
            report.append("LONG SIGNALS DETAIL")
            report.append("-" * 80)
            for idx, sig in enumerate(long_signals, 1):
                report.append(f"\nSignal {idx}:")
                report.append(f"  Timestamp: {sig['timestamp']}")
                report.append(f"  Price: {sig.get('current_price', 'N/A')}")
                
                # Include strategy-specific fields
                for key, value in sig.items():
                    if key not in ['signal_type', 'timestamp', 'current_price', 'direction', 'symbol']:
                        report.append(f"  {key}: {value}")
                
                report.append(f"  Reason: {sig.get('reason', 'N/A')}")
        
        # Short signals detail
        if short_signals:
            report.append("\n\nSHORT SIGNALS DETAIL")
            report.append("-" * 80)
            for idx, sig in enumerate(short_signals, 1):
                report.append(f"\nSignal {idx}:")
                report.append(f"  Timestamp: {sig['timestamp']}")
                report.append(f"  Price: {sig.get('current_price', 'N/A')}")
                
                # Include strategy-specific fields
                for key, value in sig.items():
                    if key not in ['signal_type', 'timestamp', 'current_price', 'direction', 'symbol']:
                        report.append(f"  {key}: {value}")
                
                report.append(f"  Reason: {sig.get('reason', 'N/A')}")
        
        # Errors
        if errors:
            report.append("\n\nERRORS")
            report.append("-" * 80)
            for idx, sig in enumerate(errors, 1):
                report.append(f"Error {idx}: {sig.get('reason', 'Unknown error')}")
        
        report.append("\n" + "=" * 80)
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
            logger.warning("No trade signals (long/short) to export")
            return
        
        df = pd.DataFrame(trade_signals)
        
        # Reorder columns: put common ones first, then rest
        common_columns = ['timestamp', 'signal_type', 'direction', 'symbol', 'current_price', 'reason']
        existing_common = [col for col in common_columns if col in df.columns]
        other_columns = [col for col in df.columns if col not in common_columns]
        ordered_columns = existing_common + sorted(other_columns)
        
        df = df[ordered_columns]
        
        os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else '.', exist_ok=True)
        df.to_csv(output_path, index=False)
        
        logger.info(f"Signals exported to {output_path}")


def main():
    """Main entry point for the test script."""
    parser = argparse.ArgumentParser(
        description='Unified test for custom strategy detectors',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Test GOLD VWAP strategy
  python tests/test_custom_strategy.py --asset GOLD --start 2025-12-01 --end 2025-12-24
  
  # Test BTC VWAP strategy with export
  python tests/test_custom_strategy.py --asset BTC --start 2025-12-01 --end 2025-12-24 --export btc_signals.csv
  
  # Test DE40 Asia Session Sweep with report
  python tests/test_custom_strategy.py --asset DE40 --start 2024-12-01 --end 2024-12-20 --report dax_report.txt
  
  # Test with custom config file
  python tests/test_custom_strategy.py --asset GOLD --start 2025-12-01 --end 2025-12-24 --config my_config.json
        """
    )
    
    parser.add_argument('--asset', required=True, help='Asset symbol (e.g., GOLD, BTC, DE40)')
    parser.add_argument('--start', required=True, help='Start date (YYYY-MM-DD)')
    parser.add_argument('--end', required=True, help='End date (YYYY-MM-DD)')
    parser.add_argument('--config', default='assets_config_custom_strategies.json', 
                       help='Config file path (default: assets_config_custom_strategies.json)')
    parser.add_argument('--export', help='Export signals to CSV file')
    parser.add_argument('--report', help='Save report to file')
    
    args = parser.parse_args()
    
    # Parse dates
    try:
        start_date = datetime.strptime(args.start, '%Y-%m-%d').replace(tzinfo=timezone.utc)
        end_date = datetime.strptime(args.end, '%Y-%m-%d').replace(tzinfo=timezone.utc)
        if start_date >= end_date:
            logger.error("Start date must be before end date")
            return 1
    except ValueError as e:
        logger.error(f"Invalid date format: {e}")
        return 1
    
    # Initialize tester
    try:
        tester = CustomStrategyTester(args.asset, args.config)
    except Exception as e:
        logger.error(f"Failed to initialize tester: {e}")
        return 1
    
    # Fetch data
    try:
        data = tester.fetch_data(start_date, end_date)
    except Exception as e:
        logger.error(f"Failed to fetch data: {e}")
        return 1
    
    if data.empty:
        logger.error("No data available for testing")
        return 1
    
    # Run backtest
    signals = tester.run_backtest(data)
    
    # Print summary to console
    print("\n")
    print(tester.generate_report())
    print("\n")
    
    # Export signals if requested
    if args.export:
        tester.export_signals_csv(args.export)
    
    # Save report if requested
    if args.report:
        tester.save_report(args.report)
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
